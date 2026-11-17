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
import datetime, hashlib, json, os, sqlite3, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import build, collect, dedupe, search_engine            # noqa: E402

JOBS_DB = ROOT / "data" / "jobs.db"
LIVE_DB = Path(os.environ.get("HRN_LIVE_DB") or ROOT.parent / "live.db")
HOUR, BUSY = 3600, 600                                   # quiet boards every hour, boards that changed in the last day every 10 minutes
SLOW = collect.SLOW_ATS                                  # one request per 20 or 100 postings plus one per new posting: once an hour at most
# Workday and SmartRecruiters: the text of at most this many postings new to the site per board and read. Their lists are newest first,
# so these are the jobs just published; the backlog of a newly added board is the hourly run's to fill (collect.DETAILS), not ours.
collect.DETAILS = int(os.environ.get("HRN_LIVE_DETAILS") or 5)
WORKERS = int(os.environ.get("HRN_LIVE_WORKERS") or 24)
SCHEMA = """
CREATE TABLE IF NOT EXISTS live (id TEXT PRIMARY KEY, slug TEXT UNIQUE, company TEXT, rec TEXT, descr TEXT, seen_at REAL, closed TEXT DEFAULT '');
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
        self.stamp, self.alias, self.idx = None, None, None
        self.known, self.by_co, self.slugs = {}, {}, set()

    # --- the hourly record ---------------------------------------------------------------------------------------------------
    def reload(self):
        """Read data/jobs.db when the upload brought a new one: the ids and addresses we know, the open jobs of each company, and the
        duplicate index. Live entries the hourly record now has are dropped (its address wins)."""
        st = JOBS_DB.stat().st_mtime_ns
        if st == self.stamp: return False
        con = sqlite3.connect(f"file:{JOBS_DB}?mode=ro", uri=True)
        known, by_co, slugs = {}, {}, set()
        idx = dedupe.Index(lambda loc: {c for c, _ in build.countries_of(loc)})
        still_open = set()
        for jid, slug, company, active, rec in con.execute("SELECT id, slug, company, active, rec FROM jobs"):
            known[jid] = slug
            if active: still_open.add(jid)
            slugs.add(slug)
            if active:
                by_co.setdefault(company, set()).add(jid)
                r = json.loads(rec)
                idx.add(slug, company, r.get("title", ""), r.get("location", ""), r.get("remote", False), r.get("url", ""), {"id": jid})
        con.close()
        self.known, self.by_co, self.slugs, self.idx, self.stamp = known, by_co, slugs, idx, st
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
        rows = self.con.execute("SELECT slug, rec, descr, closed FROM live").fetchall()
        for slug, rec, descr, closed in rows:
            self.search_put(json.loads(rec), descr, closed)
        if rows: log(f"search index {target}: {len(rows)} live jobs put back")

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
        because the live store's connection belongs to it."""
        known = self.known
        live_ids = {jid for (jid,) in self.con.execute("SELECT id FROM live WHERE company = ? AND closed = ''", (src["name"],))}
        return lambda jid, h=None: {"id": jid, "title": "-", "url": "-"} if jid in known or jid in live_ids else None

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
        seen, new, dup, back = set(), 0, 0, []
        for j in jobs:
            j.pop("_crypto", None)
            if not j.get("title") or not j.get("url"): continue
            seen.add(j["id"])
            if j["id"] in shut and j["id"] in self.known:
                back.append(j["id"]); continue          # we closed it and the board lists it again
            if j["id"] in self.known or j["id"] in live_ids: continue
            ats = j["id"].split("-", 1)[0]
            if any(m.get("id") != j["id"] and (m.get("id", "").split("-", 1)[0] != ats or m["why"] == "the same link to apply")
                   for m in self.idx.find(j["company"], j["title"], j["location"], j["remote"], j["url"], limit=3)):
                dup += 1; continue          # the same job from another source (or the same link): two postings on one board are two jobs
            desc = j.pop("desc", "") or ""
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
            if rows[k][0] <= now: out.append(s)
        return out

    def done(self, src, ok, changed):
        k, now = f"{src['ats']}:{src['token']}", time.time()
        row = self.con.execute("SELECT last_change, fails FROM boards WHERE key = ?", (k,)).fetchone() or (0, 0)
        last_change = now if changed else row[0]
        fails = 0 if ok else row[1] + 1
        wait = min(HOUR * 2 ** fails, 6 * HOUR) if not ok else (BUSY if now - last_change < 86400 and src["ats"] not in SLOW else HOUR)
        self.con.execute("UPDATE boards SET next_due = ?, last_change = ?, fails = ? WHERE key = ?", (now + wait, last_change, fails, k))

    def run(self):
        srcs, srcs_at = sources(), time.time()
        log(f"live: {len(srcs):,} boards, {WORKERS} at a time; store {LIVE_DB}")
        tally, tally_at = [0, 0, 0, 0, 0], time.time()          # boards read, failed, new jobs, closed, duplicates skipped
        direct_at, direct_seen = 0, set()                       # jobs posted on the site itself: read every DIRECT_EVERY seconds
        with cf.ThreadPoolExecutor(WORKERS) as ex:
            running = {}
            while True:
                if time.time() - tally_at >= 300:
                    log(f"last 5 min: {tally[0]} boards read, {tally[1]} did not answer, +{tally[2]} new, {tally[3]} closed, {tally[4]} duplicates skipped")
                    tally, tally_at = [0, 0, 0, 0, 0], time.time()
                if self.reload(): srcs = sources()
                if time.time() - srcs_at > 600: srcs, srcs_at = sources(), time.time()
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
                for s in self.due(srcs):
                    if len(running) >= WORKERS * 2: break
                    if f"{s['ats']}:{s['token']}" in busy: continue
                    # no more boards of one system than it allows at once: the others would only hold workers while they wait
                    if per_ats.get(s["ats"], 0) >= collect.ATS_LIMIT.get(s["ats"], WORKERS * 2): continue
                    per_ats[s["ats"]] = per_ats.get(s["ats"], 0) + 1
                    running[ex.submit(collect.fetch, s, self.skip_known(s))] = s
                if not running:
                    time.sleep(2); continue
                finished, _ = cf.wait(running, timeout=5, return_when=cf.FIRST_COMPLETED)
                for fut in finished:
                    s = running.pop(fut)
                    _, jobs = fut.result()
                    if jobs is None:
                        self.done(s, False, False); tally[1] += 1; continue
                    new, closed, dup = self.apply(s, jobs)
                    tally = [tally[0] + 1, tally[1], tally[2] + new, tally[3] + closed, tally[4] + dup]
                    self.done(s, True, bool(new or closed))
                    if new or closed: log(f"{s['name']}: +{new} new, {closed} closed" + (f", {dup} duplicates skipped" if dup else ""))


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


CODE = [ROOT / f for f in ("live.py", "collect.py", "net.py", "build.py", "dedupe.py", "search_engine.py")]


def watch(seen):
    """New code arrives with the hourly upload: stop, and systemd starts the program again with it."""
    while True:
        time.sleep(30)
        if [f.stat().st_mtime_ns for f in CODE] != seen:
            log("the code changed: restarting"); os._exit(3)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--once"]:
        once(int(sys.argv[2]) if len(sys.argv) > 2 else 30)
    else:
        import threading
        if os.environ.get("HRN_WATCH") == "1":
            threading.Thread(target=watch, args=([f.stat().st_mtime_ns for f in CODE],), daemon=True).start()
        Live().run()
