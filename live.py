"""Jobs Every Hour, live: reads employers' boards around the clock on our server and puts a new job on the site within seconds of
seeing it (the owner, 15 Nov 2026: "check 20k+ companies every hour, de-duplicate and publish, ideally within a minute; later every
5 minutes").

How it fits with the hourly build:
- GitHub Actions still reads every board once an hour, builds the site and uploads it with data/jobs.db: the full record.
- Between those uploads this program re-reads the boards on its own schedule. A job it has not seen before goes into the live store
  (HRN_LIVE_DB, outside the uploaded folder) at once, and its page (serve.py), the site's search (OpenSearch) and /api/latest show it
  within seconds. A job that left its board is marked closed the same way.
- When the next upload brings a jobs.db that has the job, the live entry is dropped: the hourly record wins, and if it gave the job
  another address, the live address sends visitors there.

Schedule: every board is read at least once an hour, spread over the hour; a board that changed in the last day every 10 minutes
(on Workday and SmartRecruiters, which take many requests a board, never more than once an hour: SLOW); a board that fails waits
longer each time (up to 6 hours). Duplicates: a job that is already on the site under another source or address (dedupe.py: same
company, same role, same place) is not added twice.

Every hiring system collect.py reads is read here too (collect.fetch). A posting the site already has is not parsed again (skip_known),
and on Workday and SmartRecruiters its text is not asked for again; no more boards of one system are read at once than
collect.ATS_LIMIT allows.

    python3 live.py                 run (on the server: systemd unit server/hosting/hrn-live.service)
    python3 live.py --once 50       read 50 boards once and print what would change, writing nothing (a dry run)
"""
import concurrent.futures as cf
import collections, ctypes, datetime, gc, hashlib, json, os, sqlite3, sys, time
from pathlib import Path

# Memory (18 Nov 2026: this program held 1.9 GB of its 3 GB at 275,000 jobs, and the boards on hold wait for room). Two malloc arenas instead
# of one per thread: answers of many megabytes pass through 24 threads, and each thread's arena kept its high-water mark.
try:
    LIBC = ctypes.CDLL("libc.so.6")
    LIBC.mallopt(-8, 2)                                  # M_ARENA_MAX
except (OSError, AttributeError):
    LIBC = None                                          # not Linux with glibc: nothing to tune


def give_back():
    """Hand memory that is free inside this program back to the system."""
    gc.collect()
    if LIBC: LIBC.malloc_trim(0)

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import build, collect, dedupe, search_engine, texts     # noqa: E402

JOBS_DB = ROOT / "data" / "jobs.db"
LIVE_DB = Path(os.environ.get("HRN_LIVE_DB") or ROOT.parent / "live.db")
HOUR, BUSY = 3600, 600                                   # quiet boards every hour, boards that changed in the last day every 10 minutes
SLOW = collect.SLOW_ATS                                  # one request per 20 or 100 postings plus one per new posting: once an hour at most
# Workday and SmartRecruiters: the text of at most this many postings new to the site per board and read. Their lists are newest first,
# so these are the jobs just published; the backlog of a newly added board is the hourly run's to fill (collect.DETAILS), not ours.
# 15 since 17 Nov 2026 (5 before): GitHub starts the hourly run only 4 or 5 times a day, so the backlog of a newly added board was
# filled mostly from here, 5 texts an hour: a board with 1,000 jobs took a week. 15 an hour is still one request every few minutes
# to an employer's site.
# Full texts for every job page's Google markup (texts.py, 19 Nov 2026). Here every posting keeps its whole text, whenever it was
# published: the 14-day limit (collect.DESC_SINCE) is for the data file of the hourly run on GitHub, not for our server.
collect.DESC_SINCE = ""
# For a job the site has without its text, the text is read on the next read of its board: at most TEXTS_SLOW of them per read on
# Workday, SmartRecruiters and JazzHR (one request each, after the postings new to the site; 891 Workday boards lacked 103,000 texts
# on 19 Nov 2026, at most 905 on one board: a day and a half of hourly reads), at most TEXTS_LIST elsewhere (the text is in the list
# already; only the parsing costs, so a board of thousands is spread over a few reads).
# 15, not 40 as on the first day: a Workday posting's page takes two or three seconds to answer, so with 40 a board took about three
# minutes to read, Workday boards held every thread, and the other boards waited (60 to 70 boards read in five minutes instead of
# about a thousand). LIVE_CAP keeps such systems to two thirds of the threads.
TEXTS_SLOW, TEXTS_LIST = 15, 500
collect.DETAILS = int(os.environ.get("HRN_LIVE_DETAILS") or 15) + TEXTS_SLOW
# 36 threads since 19 Nov 2026 (24 before): the reading is waiting on answers, not work, and the slow systems below now keep a third
# of the threads free for the quick boards.
WORKERS = int(os.environ.get("HRN_LIVE_WORKERS") or 36)
# Boards of these systems read at once here, at most: their reads take long (a request per posting's text), and without a cap they
# can hold every thread while the quick boards of the other systems wait (the loop keeps WORKERS * 2 reads queued, WORKERS run).
LIVE_CAP = {"workday": WORKERS // 2, "smartrecruiters": 2, "jazzhr": 4, "breezy": 4, "bamboohr": 4, "paylocity": 4}
# And these systems together at most HEAVY_MAX of the reads queued, so at most that many threads: a third of the threads is always
# free for the quick boards. (20 Nov 2026: the caps above added up to 40 of 36 threads; the slow boards held every thread, and
# 1,800 Greenhouse and 1,800 Ashby boards were read seven or eight hours late instead of every hour.)
HEAVY = {"workday", "smartrecruiters", "jazzhr", "breezy", "bamboohr", "paylocity", "usajobs"}
HEAVY_MAX = WORKERS * 2 // 3
SCHEMA = """
CREATE TABLE IF NOT EXISTS live (id TEXT PRIMARY KEY, slug TEXT UNIQUE, company TEXT, rec TEXT, descr TEXT, seen_at REAL, closed TEXT DEFAULT '');
-- one company's rows, asked for four times a board read (skip_known, apply). Without it every one of those read the whole table:
-- 450 MB once the live rows carried full texts, 500 MB a second, and the loop handed out 60 to 250 boards in five minutes (20 Nov 2026).
CREATE INDEX IF NOT EXISTS live_company ON live (company, closed);
CREATE TABLE IF NOT EXISTS moved (slug TEXT PRIMARY KEY, to_slug TEXT);
CREATE TABLE IF NOT EXISTS boards (key TEXT PRIMARY KEY, next_due REAL, last_change REAL DEFAULT 0, fails INTEGER DEFAULT 0);
"""


def log(*a):
    print(datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S"), *a, flush=True)


DIRECT_EVERY = 120          # seconds between reads of the jobs employers posted on the site itself


def sources():
    """Every board the hourly collector reads (all sources*.json but the candidate list), each once."""
    seen, out = set(), []
    crypto = {s["name"] for s in json.loads((ROOT / "sources.json").read_text())} if (ROOT / "sources.json").exists() else set()
    for f in sorted(ROOT.glob("sources*.json")):
        if "candidates" in f.name: continue
        for s in json.loads(f.read_text()):
            k = (s.get("ats"), s.get("token"))
            if not s.get("token") or not s.get("name") or k in seen or s["name"] in collect.EXCLUDE or s.get("hold"): continue
            seen.add(k)
            out.append(dict(s, crypto=s["name"] in crypto))
    return out


class Live:
    def __init__(self, write=True):
        self.write = write
        self.con = sqlite3.connect(LIVE_DB if write else ":memory:", isolation_level=None)
        self.con.executescript(SCHEMA)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.execute("PRAGMA synchronous=NORMAL")     # in WAL mode still safe from corruption; a power cut may lose the last few rows, read again
        self.stamp, self.alias, self.idx = None, None, None
        self.known, self.by_co, self.slugs = {}, {}, set()
        self.texts = texts.Keeper(texts.DB if write else ":memory:")
        self.textless, self.pruned = set(), ""                 # open jobs whose text the hourly record lacks; the day texts were last pruned

    # --- the hourly record ---------------------------------------------------------------------------------------------------
    def reload(self):
        """Read data/jobs.db when the upload brought a new one: the ids and addresses we know, the open jobs of each company, and the
        duplicate index. Live entries the hourly record now has are dropped (its address wins)."""
        st = JOBS_DB.stat().st_mtime_ns
        if st == self.stamp: return False
        # The old tables go first: built beside them, the new ones doubled what this program needed at every upload. Nothing reads them
        # meanwhile (apply runs in this same thread), and if reading the file fails the program stops and systemd starts it again.
        self.known, self.by_co, self.slugs, self.idx, self.stamp, self.textless = {}, {}, set(), None, None, set()
        give_back()
        con = sqlite3.connect(f"file:{JOBS_DB}?mode=ro", uri=True)
        known, by_co, slugs, textless = {}, {}, set(), set()
        idx = dedupe.Index(lambda loc: {c for c, _ in build.countries_of(loc)})
        still_open = set()
        fields = ", ".join(f"CASE WHEN active THEN {f} END" for f in dedupe.JOB_FIELDS)
        for jid, slug, company, active, bare, title, location, remote, url in con.execute(
                f"SELECT id, slug, company, active, CASE WHEN active THEN {texts.BYTES}(descr) = 0 END, {fields} FROM jobs"):
            known[jid] = slug
            slugs.add(slug)
            if active:
                still_open.add(jid)
                by_co.setdefault(company, set()).add(jid)
                idx.add(slug, company, title or "", location or "", bool(remote), url or "", {"id": jid})
                if bare: textless.add(jid)
        con.close()
        self.known, self.by_co, self.slugs, self.idx, self.stamp, self.textless = known, by_co, slugs, idx, st, textless
        dropped = 0
        for jid, slug, closed in self.con.execute("SELECT id, slug, closed FROM live").fetchall():
            if jid in known and closed and jid in still_open:
                continue                                         # we saw it close; the hourly record has not yet: keep it closed
            if jid in known:
                if known[jid] != slug: self.con.execute("INSERT OR REPLACE INTO moved VALUES (?, ?)", (slug, known[jid]))
                self.con.execute("DELETE FROM live WHERE id = ?", (jid,))
                dropped += 1
            else:
                r = json.loads(self.con.execute("SELECT rec FROM live WHERE id = ?", (jid,)).fetchone()[0])
                self.slugs.add(slug)
                idx.add(slug, r["company"], r["title"], r.get("location", ""), r.get("remote", False), r.get("url", ""), {"id": jid})
        idx.done()
        if self.write:
            try:
                copied, today = self.texts.take_from(JOBS_DB), datetime.date.today().isoformat()
                if self.pruned != today:
                    gone = self.texts.prune(still_open | {i for (i,) in self.con.execute("SELECT id FROM live WHERE closed = ''")})
                    self.pruned = today
                    if gone: log(f"texts: {gone:,} of jobs closed for {texts.KEEP_CLOSED} days dropped")
                log(f"texts: {copied:,} copied from the hourly record, {self.texts.count():,} kept; {len(textless):,} open jobs lack theirs in the record")
            except sqlite3.Error as ex:
                log(f"texts: {type(ex).__name__}: {ex}")
        del still_open
        give_back()
        log(f"hourly record: {len(known):,} jobs, {idx.size:,} open; {dropped} live entries now in it")
        return True

    def resync_search(self):
        """After the hourly index load moves the search alias to a new index, put the live jobs into it again."""
        if not search_engine.URL or not self.write: return
        try:
            target = next(iter(search_engine.call("GET", f"/_alias/{search_engine.ALIAS}", timeout=5)))
        except Exception:
            return
        if target == self.alias: return
        self.alias = target
        # In batches (OpenSearch's _bulk), not one request a job: one by one, 58,000 live jobs took five minutes after every upload, and
        # this loop read no boards meanwhile (19 Nov 2026).
        batch, failed, n = [], 0, 0
        def flush():
            nonlocal failed
            if not batch: return
            try:
                r = search_engine.call("POST", f"/{target}/_bulk", "".join(batch), timeout=120, ndjson=True)
                failed += sum(1 for it in r.get("items", []) for v in it.values() if v.get("error") and v.get("status") != 404)
            except Exception as ex:
                log(f"search: a batch of {len(batch)} not put back ({type(ex).__name__}: {ex})"); failed += len(batch)
            batch.clear()
        for slug, rec, descr, closed in self.con.execute("SELECT slug, rec, descr, closed FROM live"):    # row by row: the texts are 450 MB
            n += 1
            if closed: batch.append(json.dumps({"delete": {"_id": slug}}) + "\n")
            else: batch.append(json.dumps({"index": {"_id": slug}}) + "\n" + json.dumps(search_engine.doc(json.loads(rec), descr), ensure_ascii=False) + "\n")
            if len(batch) >= 500: flush()
        flush()
        if n: log(f"search index {target}: {n} live jobs put back" + (f", {failed} failed" if failed else ""))

    def search_put(self, rec, descr, closed=""):
        if not search_engine.URL or not self.write: return
        try:
            if closed: search_engine.call("DELETE", f"/{search_engine.ALIAS}/_doc/{rec['slug']}", timeout=5)
            else: search_engine.call("PUT", f"/{search_engine.ALIAS}/_doc/{rec['slug']}", search_engine.doc(rec, descr), timeout=5)
        except Exception as ex:
            if closed and " 404" in str(ex): return                 # already gone from the index (a new index was loaded): nothing to remove
            log(f"search: {rec['slug']}: {type(ex).__name__}: {ex}")

    # --- one board -----------------------------------------------------------------------------------------------------------
    def skip_known(self, src):
        """For collect.fetch (its "reuse"): a posting the site already has, in the hourly record or open in the live store, needs no
        parsing and, on Workday and SmartRecruiters, no request for its text. apply() only needs its id. Made in the main thread,
        because the live store's connection belongs to it.

        The exception is a job whose full text neither the record nor texts.db has (texts.py): a few of those each read (TEXTS_SLOW,
        TEXTS_LIST) are read in full, and apply() keeps their text. Workday's reader asks twice before it reads a posting's page
        (details_from), so such a job gets "nothing kept" twice; a third question means its page was not read this time, and the
        stand-in keeps the job open (a job missing from what a read returns is closed)."""
        known, name = self.known, src["name"]
        live_ids = {jid for (jid,) in self.con.execute("SELECT id FROM live WHERE company = ? AND closed = ''", (name,))}
        need = (self.by_co.get(name, set()) & self.textless) | {jid for (jid,) in self.con.execute(
            f"SELECT id FROM live WHERE company = ? AND closed = '' AND {texts.BYTES}(descr) = 0", (name,))}
        if need: need -= self.texts.have(name)
        budget, asked = TEXTS_SLOW if src.get("ats") in SLOW else TEXTS_LIST, {}

        def reuse(jid, h=None):
            if jid in need:
                n = asked.get(jid, 0)
                if n < 2 and (n or len(asked) < budget):
                    asked[jid] = n + 1
                    return None
            return {"id": jid, "title": "-", "url": "-"} if jid in known or jid in live_ids else None
        return reuse

    def slug_for(self, j):
        base = f"{collect.slugify(j['title'])}-{collect.slugify(j['company'])}"
        slug, i = base, 2
        while slug in self.slugs:
            slug, i = f"{base}-{i}", i + 1
        self.slugs.add(slug)
        return slug

    def apply(self, src, jobs):
        """What one read of a board changes: new jobs in, gone jobs closed. Returns (new, closed, duplicates skipped)."""
        name, now = src["name"], time.time()
        today = datetime.date.today().isoformat()
        live_ids = {jid for (jid,) in self.con.execute("SELECT id FROM live WHERE company = ? AND closed = ''", (name,))}
        shut = {jid for (jid,) in self.con.execute("SELECT id FROM live WHERE company = ? AND closed != ''", (name,))}     # closed on an earlier read
        seen, new, dup, back, keep = set(), 0, 0, [], []        # keep: texts to store, in one transaction at the end
        for j in jobs:
            j.pop("_crypto", None)
            if not j.get("title") or not j.get("url"): continue
            seen.add(j["id"])
            if j["id"] in shut and j["id"] in self.known:
                back.append(j["id"]); continue          # we closed it and the board lists it again
            if j["id"] in self.known or j["id"] in live_ids:
                if j.get("desc"): keep.append((j["id"], name, j["desc"]))      # a text skip_known asked for
                continue
            ats = j["id"].split("-", 1)[0]
            if any(m.get("id") != j["id"] and (m.get("id", "").split("-", 1)[0] != ats or m["why"] == "the same link to apply")
                   for m in self.idx.find(j["company"], j["title"], j["location"], j["remote"], j["url"], limit=3)):
                dup += 1; continue          # the same job from another source (or the same link): two postings on one board are two jobs
            desc = j.pop("desc", "") or ""
            if desc: keep.append((j["id"], name, desc))       # kept beyond the live entry, which the next record replaces
            j.update(slug=self.slug_for(j), crypto=bool(src.get("crypto")), first_seen=today, first_seen_at=collect.utc_now(), last_seen=today,
                     active=True, pinned=False, featured=False, entry=j["level"] in ("Junior", "Intern"), pool=bool(build.POOL_RX.search(j["title"])),
                     usd=build.usd_range(j["salary"]), places=build.places_of(j["location"]) if j["location"] else [], live=True)
            j["t"], j["ts"] = build.exact(j), build.stamp(j)
            if self.write:
                self.con.execute("INSERT OR REPLACE INTO live VALUES (?,?,?,?,?,?, '')",
                                 (j["id"], j["slug"], name, json.dumps(j, ensure_ascii=False), desc, now))
            self.idx.add(j["slug"], name, j["title"], j["location"], j["remote"], j["url"], {"id": j["id"]})
            self.search_put(j, desc)
            new += 1
        if keep and self.write: self.texts.put_many(keep)
        if back: self.reopen(name, back)
        closed = 0
        # without the ones already closed here: after every new hourly record they are "open" in it again until it catches up, and
        # closing them a second time only repeats the work (one board was "closed" 1,548 jobs at a time, three times, on 17 Nov 2026)
        was_open = (self.by_co.get(name, set()) | live_ids) - shut
        if jobs or len(was_open) < 20:                              # a board that suddenly shows nothing waits for the hourly collector
            for jid in was_open - seen:
                slug = self.known.get(jid) or (self.con.execute("SELECT slug FROM live WHERE id = ?", (jid,)).fetchone() or [None])[0]
                if not slug: continue
                if self.write:
                    if self.con.execute("UPDATE live SET closed = ? WHERE id = ?", (today, jid)).rowcount == 0:
                        self.con.execute("INSERT OR REPLACE INTO live VALUES (?,?,?,?,?,?,?)",
                                         (jid, slug, name, json.dumps({"slug": slug, "id": jid, "company": name, "closed_only": True}), "", now, today))
                self.search_put({"slug": slug}, "", today)
                self.by_co.get(name, set()).discard(jid)
                closed += 1
        return new, closed, dup

    def reopen(self, name, ids):
        """Jobs closed here on an earlier read that the board lists again: it had dropped them for one reading, or put them back.
        While the hourly record still has such a job open, its entry there is used again and the search gets the job back.
        (Before 17 Nov 2026 it stayed closed for good: 61 jobs closed on 15 and 16 Nov were still open in the record of the 17th.)"""
        if not self.write or not JOBS_DB.exists(): return
        rec, n = sqlite3.connect(f"file:{JOBS_DB}?mode=ro", uri=True), 0
        for i in range(0, len(ids), 400):
            part = ids[i:i + 400]
            for jid, r_, descr in rec.execute(f"SELECT id, rec, descr FROM jobs WHERE active AND id IN ({','.join('?' * len(part))})", part).fetchall():
                self.con.execute("DELETE FROM live WHERE id = ?", (jid,))
                self.by_co.setdefault(name, set()).add(jid)
                self.search_put(json.loads(r_), descr or "")
                n += 1
        rec.close()
        if n: log(f"{name}: {n} listed again, reopened")

    # --- the loop ------------------------------------------------------------------------------------------------------------
    # --- jobs posted on the site itself --------------------------------------------------------------------------------------------
    def direct(self, indexed):
        """Jobs employers posted in their account (our own API, /api/public/export.json), by company. A job a person has just approved
        is on the site within minutes instead of waiting for the next hourly build. None: no API, or it did not answer (nothing changes)."""
        api = (os.environ.get("HRN_API_URL") or json.loads((ROOT / "config.json").read_text()).get("api_url", "")).rstrip("/")
        if not api: return None
        exp = collect.get_json(api + "/api/public/export.json", 20)
        if not isinstance(exp, dict) or not isinstance(exp.get("jobs"), list): return None
        by = {}
        for d in exp["jobs"]:
            if not isinstance(d, dict): continue
            company = str(d.get("company", "")).strip()
            if not company or company.lower() in indexed: continue      # as in collect.direct_and_paid: a posting may not pass itself off as an indexed company
            j = collect.norm(company, "direct", d.get("id", ""), d.get("title"), d.get("url"), d.get("location"), bool(d.get("remote")), "", d.get("posted"),
                             str(d.get("text") or ""), str(d.get("salary") or ""), str(d.get("etype") or ""))
            if not j["title"] or not str(j["url"]).startswith("https://"): continue
            j["direct"], j["desc"] = True, collect.direct_desc(d.get("text"))
            by.setdefault(company, []).append(j)
        return by

    def due(self, srcs):
        now = time.time()
        rows = {k: (nd, lc, f) for k, nd, lc, f in self.con.execute("SELECT key, next_due, last_change, fails FROM boards")}
        out = []
        for s in srcs:
            k = f"{s['ats']}:{s['token']}"
            if k not in rows:                                       # a board seen for the first time: a place in the coming hour
                nd = now + int(hashlib.md5(k.encode()).hexdigest(), 16) % HOUR
                self.con.execute("INSERT OR IGNORE INTO boards (key, next_due) VALUES (?, ?)", (k, nd))
                rows[k] = (nd, 0, 0)
            if rows[k][0] <= now: out.append((rows[k][0], s))
        self.late = sum(1 for nd, _ in out if nd < now - HOUR)
        # the longest overdue first: in the order of the sources file, the boards at its end waited whenever the threads were short
        return [s for _, s in sorted(out, key=lambda x: x[0])]

    def done(self, src, ok, changed):
        k, now = f"{src['ats']}:{src['token']}", time.time()
        row = self.con.execute("SELECT last_change, fails FROM boards WHERE key = ?", (k,)).fetchone() or (0, 0)
        last_change = now if changed else row[0]
        fails = 0 if ok else row[1] + 1
        wait = min(HOUR * 2 ** fails, 6 * HOUR) if not ok else (BUSY if now - last_change < 86400 and src["ats"] not in SLOW else HOUR)
        # Where every board of a system is on one service (JazzHR, Breezy, BambooHR, Paylocity: one request every collect.ATS_GAP
        # seconds in all), its boards are read no more often than lets their lists take half of those requests; the other half is
        # for the texts of new postings. (20 Nov 2026: 8,000 Paylocity boards read hourly would have taken nine requests in ten.)
        if ok and src["ats"] != "workday":
            wait = max(wait, getattr(self, "per_system", {}).get(src["ats"], 0) * collect.ATS_GAP.get(src["ats"], 0) * 2)
        self.con.execute("UPDATE boards SET next_due = ?, last_change = ?, fails = ? WHERE key = ?", (now + wait, last_change, fails, k))

    def run(self):
        srcs, srcs_at = sources(), time.time()
        self.per_system = collections.Counter(s["ats"] for s in srcs)
        log(f"live: {len(srcs):,} boards, {WORKERS} at a time; store {LIVE_DB}")
        tally, tally_at = [0, 0, 0, 0, 0], time.time()          # boards read, failed, new jobs, closed, duplicates skipped
        took = {}                                               # system: [reads, seconds], for the five-minute line
        direct_at, direct_seen = 0, set()                       # jobs posted on the site itself: read every DIRECT_EVERY seconds
        with cf.ThreadPoolExecutor(WORKERS) as ex:
            running = {}
            while True:
                if time.time() - tally_at >= 300:
                    log(f"last 5 min: {tally[0]} boards read, {tally[1]} did not answer, +{tally[2]} new, {tally[3]} closed, {tally[4]} duplicates skipped;"
                        f" {getattr(self, 'late', 0):,} boards more than an hour late; thread time: {thread_time(took)}")
                    tally, tally_at, took = [0, 0, 0, 0, 0], time.time(), {}
                    give_back()
                if self.reload(): srcs = sources()
                if time.time() - srcs_at > 600: srcs, srcs_at = sources(), time.time()
                self.per_system = collections.Counter(s["ats"] for s in srcs)
                self.resync_search()
                if time.time() - direct_at >= DIRECT_EVERY:
                    direct_at = time.time()
                    try: posted = self.direct({s["name"].lower() for s in srcs})
                    except Exception as err: posted = None; log(f"posted jobs: not read ({type(err).__name__})")
                    if posted is not None:
                        for company in sorted(set(posted) | direct_seen):
                            new, closed, dup = self.apply({"name": company, "crypto": False}, posted.get(company, []))
                            tally = [tally[0], tally[1], tally[2] + new, tally[3] + closed, tally[4] + dup]
                            if new or closed: log(f"{company} (posted here): +{new} new, {closed} closed")
                        direct_seen = set(posted)
                busy = {f"{s['ats']}:{s['token']}" for s in running.values()}
                per_ats = {}
                for s in running.values(): per_ats[s["ats"]] = per_ats.get(s["ats"], 0) + 1
                heavy = sum(n for a, n in per_ats.items() if a in HEAVY)
                for s in self.due(srcs):
                    if len(running) >= WORKERS * 2: break
                    if f"{s['ats']}:{s['token']}" in busy: continue
                    # no more boards of one system than it allows at once: the others would only hold workers while they wait
                    if per_ats.get(s["ats"], 0) >= min(collect.ATS_LIMIT.get(s["ats"], WORKERS * 2), LIVE_CAP.get(s["ats"], WORKERS * 2)): continue
                    if s["ats"] in HEAVY:
                        if heavy >= HEAVY_MAX: continue
                        heavy += 1
                    per_ats[s["ats"]] = per_ats.get(s["ats"], 0) + 1
                    running[ex.submit(timed, s, self.skip_known(s))] = s
                if not running:
                    time.sleep(2); continue
                finished, _ = cf.wait(running, timeout=5, return_when=cf.FIRST_COMPLETED)
                for fut in finished:
                    s = running.pop(fut)
                    (_, jobs), secs = fut.result()
                    t = took.setdefault(s["ats"], [0, 0.0]); t[0] += 1; t[1] += secs
                    if jobs is None:
                        self.done(s, False, False); tally[1] += 1; continue
                    new, closed, dup = self.apply(s, jobs)
                    tally = [tally[0] + 1, tally[1], tally[2] + new, tally[3] + closed, tally[4] + dup]
                    self.done(s, True, bool(new or closed))
                    if new or closed: log(f"{s['name']}: +{new} new, {closed} closed" + (f", {dup} duplicates skipped" if dup else ""))


def timed(src, reuse):
    """collect.fetch, and how many seconds it held its thread."""
    t = time.time()
    return collect.fetch(src, reuse), time.time() - t


def thread_time(took):
    """The systems that held the threads longest in the last five minutes: "workday 61% (80 reads, 41 s each), ..."."""
    total = sum(sec for _, sec in took.values()) or 1
    top = sorted(took.items(), key=lambda x: -x[1][1])[:5]
    return ", ".join(f"{a} {round(100 * sec / total)}% ({n} reads, {sec / n:.0f} s each)" for a, (n, sec) in top) or "none"


def once(n):
    """A dry run: read n boards and say what would change."""
    lv = Live(write=False)
    lv.reload()
    srcs = sources()[:n]
    t0, tot = time.time(), [0, 0, 0]
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        for s, (_, jobs) in zip(srcs, ex.map(collect.fetch, srcs, [lv.skip_known(s) for s in srcs])):
            if jobs is None: print(f"  {s['name']}: did not answer"); continue
            got = lv.apply(s, jobs)
            tot = [a + b for a, b in zip(tot, got)]
            if any(got): print(f"  {s['name']}: +{got[0]} new, {got[1]} closed, {got[2]} duplicates skipped")
    print(f"{len(srcs)} boards in {time.time() - t0:.0f} s: {tot[0]} new, {tot[1]} closed, {tot[2]} duplicates skipped")


CODE = [ROOT / f for f in ("live.py", "collect.py", "net.py", "build.py", "dedupe.py", "search_engine.py", "texts.py")]


def watch(seen):
    """New code arrives with the hourly upload: stop, and systemd starts the program again with it."""
    while True:
        time.sleep(30)
        if [f.stat().st_mtime_ns for f in CODE] != seen:
            log("the code changed: restarting"); os._exit(3)


def test():
    """The scheduler, with boards that answer at once and nothing written: the slow systems together never hold more than HEAVY_MAX
    threads, the quick boards are all read while the slow ones are busy, and the longest overdue board goes first."""
    global sources
    import threading
    srcs = [{"name": f"{a}{i}", "ats": a, "token": f"{a}{i}"} for a, n in (("workday", 60), ("jazzhr", 20), ("breezy", 20), ("paylocity", 20), ("greenhouse", 80))
            for i in range(n)]
    lock, now_heavy, max_heavy, order = threading.Lock(), [0], [0], []

    def fake(src, reuse=None):
        heavy = src["ats"] in HEAVY
        with lock:
            order.append(src["name"])
            if heavy: now_heavy[0] += 1; max_heavy[0] = max(max_heavy[0], now_heavy[0])
        time.sleep(3 if heavy else 0.02)
        with lock:
            if heavy: now_heavy[0] -= 1
        return src["name"], []
    sources, collect.fetch = (lambda: srcs), fake           # for the rest of this process: the loop below never stops

    def go():
        lv = Live(write=False)                                  # sqlite3 objects stay in the thread that made them
        lv.reload = lambda: False; lv.resync_search = lambda: None; lv.direct = lambda idx: None
        lv.apply = lambda s, jobs: (0, 0, 0); lv.skip_known = lambda s: None
        t = time.time()
        for i, s in enumerate(srcs):                            # all overdue; the Greenhouse boards, last in the file, the longest
            late = 7200 + i * 10 if s["ats"] == "greenhouse" else 600 + i
            lv.con.execute("INSERT INTO boards (key, next_due) VALUES (?, ?)", (f"{s['ats']}:{s['token']}", t - late))
        lv.run()
    threading.Thread(target=go, daemon=True).start()
    time.sleep(2.5)
    gh = [n for n in order if n.startswith("greenhouse")]
    assert 0 < max_heavy[0] <= HEAVY_MAX, max_heavy
    assert len(gh) == 80, len(gh)
    assert order[0] == "greenhouse79", order[:3]
    lv = Live(write=False)
    lv.per_system = {"paylocity": 8000, "greenhouse": 8000, "workday": 8000}
    for ats, want in (("paylocity", 8000 * collect.ATS_GAP["paylocity"] * 2), ("greenhouse", BUSY), ("workday", HOUR)):
        lv.con.execute("INSERT INTO boards (key, next_due, last_change) VALUES (?, 0, ?)", (f"{ats}:t", time.time() - 3600 * (1 if ats == "greenhouse" else 48)))
        t = time.time(); lv.done({"ats": ats, "token": "t"}, True, False)
        got = lv.con.execute("SELECT next_due FROM boards WHERE key = ?", (f"{ats}:t",)).fetchone()[0] - t
        assert abs(got - want) < 2, (ats, got, want)
    assert thread_time({"workday": [2, 80.0], "greenhouse": [10, 20.0]}) == "workday 80% (2 reads, 40 s each), greenhouse 20% (10 reads, 2 s each)"
    assert thread_time({}) == "none"
    print(f"live.py: all checks passed (slow reads at once at most {max_heavy[0]} of {WORKERS} threads)")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--test"]:
        test()
        sys.stdout.flush(); os._exit(0)                         # the test's loop never ends: leave without waiting for its threads
    elif sys.argv[1:2] == ["--once"]:
        once(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    else:
        import threading
        if os.environ.get("HRN_WATCH") == "1":
            threading.Thread(target=watch, args=([f.stat().st_mtime_ns for f in CODE],), daemon=True).start()
        Live().run()
