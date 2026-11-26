"""Job records: every job is one row in a SQLite file (data/jobs.db) instead of one HTML file, the way large job sites keep postings
(Indeed's Docstore hands out job records from a store and builds the page when someone asks for it).

build.py writes the file when HRN_RECORDS is set: "1" writes the records and no job pages, "both" writes the records and the pages too,
which records_test.py uses to check that a page built from a record is the same page, byte for byte. serve.py and check.py read it.

A page needs more than its own record: the similar jobs, the open roles of the company, the medians of its field. build.py works those
out once per build; they are stored next to the records in the table ctx and loaded once, not per page.
"""
import collections, contextlib, datetime, faulthandler, html, json, os, re, sqlite3, sys, threading, time
from pathlib import Path

import texts

SCHEMA = """
CREATE TABLE jobs (slug TEXT PRIMARY KEY, id TEXT NOT NULL, active INTEGER NOT NULL, company TEXT NOT NULL, cat TEXT NOT NULL,
                   first_seen TEXT NOT NULL, rec TEXT NOT NULL, descr TEXT NOT NULL);
CREATE INDEX jobs_company ON jobs (company);
CREATE INDEX jobs_cat ON jobs (cat, active);
-- the newest open jobs (Store.latest, /api/latest). Without it that query read and sorted the whole file, 3.7 GB on 25 Nov 2026: over
-- 60 seconds with the store's lock held, so the home page's live list never arrived and job pages waited behind it.
CREATE INDEX jobs_new ON jobs (active, first_seen);
CREATE TABLE ctx (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE VIRTUAL TABLE jobs_fts USING fts5 (title, company, place, tags, body, content='', tokenize='porter unicode61 remove_diacritics 2');
"""
# Word search over every job, the kind of index Lucene keeps (Lucene is what Elasticsearch, Solr and the search of large job sites are
# built on): for each word, the jobs it is in. SQLite's FTS5 keeps one inside the same file, ranks by BM25 as Lucene does, and costs
# nothing. "content=''" stores only the index, not a second copy of the text; a hit is joined to its job by rowid.
# Weights for the rank: a word in the title counts most, then the company, the skills, the place, then the text of the posting.
RANK = "bm25(jobs_fts, 10.0, 5.0, 3.0, 4.0, 1.0)"
TAGS = re.compile(r"<[^>]+>")
WORD = re.compile(r"[^\W_]+(?:[+#]+|\.(?=net\b))?", re.U)
# The tokenizer drops "+" and "#", so C++ and C# would both be "c": they are written as one word on both sides, in the index and in a query.
SPELL = [(re.compile(r"(?<![\w.])c\+\+", re.I), " cplusplus "), (re.compile(r"(?<![\w.])c#", re.I), " csharp "), (re.compile(r"(?<![\w])\.net\b", re.I), " dotnet "),
         (re.compile(r"(?<![\w.])f#", re.I), " fsharp ")]
SKIP = {"a", "an", "and", "or", "not", "the", "of", "in", "at", "for", "to", "with", "on", "job", "jobs", "role", "roles", "position", "positions",
        "vacancy", "vacancies", "opening", "openings", "career", "careers", "hiring", "work"}       # words that say nothing about which job


def spell(t):
    for rx, to in SPELL: t = rx.sub(to, t)
    return t
SEP = "\x1f"        # joins the parts of a tuple key, (company, field) and the like, so the shared data can be stored as JSON


def _plain(v):
    if isinstance(v, (set, frozenset)): return sorted(v)
    raise TypeError(f"cannot store {type(v).__name__} in a job record")


def save(path, jobs, b):
    """Write every job and the shared data its page needs into a new file, then put it in place of the old one in one step, so a
    server reading the old file never sees half a file. b is the build module, whose globals job_page() reads."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA)
    dumps = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"), default=_plain)
    # A slug shared by two jobs gets the later one, as the files do: the later page is written over the earlier one.
    con.executemany("INSERT OR REPLACE INTO jobs VALUES (?,?,?,?,?,?,?,?)",
                    ((j["slug"], j["id"], int(bool(j["active"])), j["company"], j["cat"], j.get("first_seen") or "",
                      dumps({k: v for k, v in j.items() if k != "desc"}), j.get("desc") or "") for j in jobs))
    index(con)
    key = lambda k: SEP.join(k)
    ctx = {
        "now": b.NOW, "today": b.TODAY, "v": b.V,
        "sim_cat": {c: [x["slug"] for x in xs] for c, xs in b.SIM["cat"].items()},
        "sim_comp": {key(k): [x["slug"] for x in xs] for k, xs in b.SIM["comp"].items()},
        "open": dict(b.OPEN), "fact": b.FACT, "tb": b.TB, "catmed": b.CATMED, "est": {key(k): v for k, v in b.EST.items()},
        "close_days": b.CLOSE_DAYS, "co_close": b.CO_CLOSE, "repost": {key(k): v for k, v in b.REPOST.items()}, "perk_ok": sorted(b.PERK_OK),
        # 25 Nov 2026 (records_test found them): the count of open jobs the header's jobs menu shows (nav data-n) and the median
        # hourly pay per field the hourly pay line compares with; pages built from records had neither
        "all_open": b.ALL_OPEN[0], "hmed": b.HMED,
        # 26 Nov 2026 (data teardown): the pay of the same work (build.FAM), which the salary estimate of a job page without pay reads
        "fam": getattr(b, "FAM", {}),
        # 26 Nov 2026 (records_test): the pages that keep a search (build.same_as, CAT_HOME): the built job page links its field's page
        # (/categories/product-project/) where a page built from a record linked /jobs/product/, which gives its search to that page
        "cat_home": dict(getattr(b, "CAT_HOME", {}) or {}),
    }
    con.executemany("INSERT INTO ctx VALUES (?, ?)", ((k, dumps(v)) for k, v in ctx.items()))
    con.commit()
    con.close()
    os.replace(tmp, path)
    return path.stat().st_size


def index(con):
    """Fill the word index from the jobs table (the text without its few tags)."""
    con.execute("DELETE FROM jobs_fts")
    con.executemany("INSERT INTO jobs_fts (rowid, title, company, place, tags, body) VALUES (?,?,?,?,?,?)",
                    ((rid, spell(r["title"]), company, r.get("location") or "", spell(" ".join(r.get("tags") or [])), spell(html.unescape(TAGS.sub(" ", body))))
                     for rid, company, rec, body in con.execute("SELECT rowid, company, rec, descr FROM jobs").fetchall() for r in [json.loads(rec)]))
    con.execute("INSERT INTO jobs_fts (jobs_fts) VALUES ('optimize')")


LIVE_DB = Path(os.environ.get("HRN_LIVE_DB") or Path(__file__).parent.parent / "live.db")     # live.py: jobs seen since the last upload


def live_row(sql, args):
    """One query against the live store (live.py), or None when there is none yet."""
    if not LIVE_DB.exists(): return None
    try:
        con = sqlite3.connect(f"file:{LIVE_DB}?mode=ro", uri=True)
    except sqlite3.Error:            # 26 Nov 2026, 06:58 UTC: "unable to open database file" when serve.py had no file left: no live row, not a 500
        return None
    try:
        return con.execute(sql, args).fetchall()
    except sqlite3.Error:
        return None
    finally:
        con.close()


def live_checked_at(company):
    """When live.py last read the company's board to the end (live.py, table read_ok), in seconds since 1970, or 0 when it has not, or
    there is no live store."""
    got = live_row("SELECT at FROM read_ok WHERE company = ?", (company or "",))
    try:
        return float(got[0][0]) if got and got[0][0] else 0
    except (TypeError, ValueError):
        return 0


def live_checked(company):
    """The day live.py last read the company's board to the end, or "" (live_checked_at)."""
    try:
        at = live_checked_at(company)
        return datetime.date.fromtimestamp(at).isoformat() if at else ""
    except (ValueError, OverflowError, OSError):
        return ""


class Cards:
    """The other open jobs of the same company in the same field, for the "similar jobs" block of a job page: read from the records
    when a page asks for them. (18 Nov 2026: they were held in memory as whole records, up to four for every company and field, about
    100,000 records at 225,000 jobs. That was most of the page service's 900 MB, and every upload loaded a second set beside the old
    one, so the service hit its 1 GB limit and was killed several times a day.) job_page() asks with .get() while Store.page() holds
    the store's lock, so the connection of the file these slugs came from is used as it is, by one page at a time."""

    def __init__(self, con, slugs):
        self.con, self.slugs = con, slugs                   # {(company, category): [slug, ...]}

    def get(self, key, default=()):
        xs = self.slugs.get(key)
        if not xs: return default
        got = {s_: json.loads(r) for s_, r in self.con.execute(f"SELECT slug, rec FROM jobs WHERE slug IN ({','.join('?' * len(xs))})", xs)}
        return [got[s_] for s_ in xs if s_ in got]


class Busy(RuntimeError):
    """The store's lock stayed taken for WAIT seconds: the request is answered at once instead of joining the queue."""


class Guard:
    """The lock a job page is drawn under, taken for at most WAIT seconds. 26 Nov 2026, 06:57-08:09 UTC: one request held the plain lock and
    every other job page and search queued behind it, one thread and one socket each, until serve.py reached its 1,024 open files and
    answered 500 to everything but the static pages. Now a request that cannot have the lock in WAIT seconds fails fast (Busy), and a
    watchdog writes every thread's stack to the log once when the lock has been held for STUCK seconds, so the cause can be read the next
    time. Since 27 Nov only the drawing of a page takes it (a few milliseconds): reading rows, a search and the records a search names do
    not (Store.reading), and serve.py lets at most a few dozen requests in at once, so a queue here is short by construction."""
    WAIT, STUCK = 5, 30

    def __init__(self):
        self.lock, self.since, self.told = threading.Lock(), 0.0, False
        threading.Thread(target=self.watch, daemon=True).start()

    def __enter__(self):
        if not self.lock.acquire(timeout=self.WAIT): raise Busy("the job store is busy")
        self.since, self.told = time.monotonic(), False
        return self

    def __exit__(self, *exc):
        self.since = 0.0
        self.lock.release()

    def watch(self):
        while True:
            time.sleep(5)
            t = self.since
            if t and not self.told and time.monotonic() - t > self.STUCK:
                self.told = True
                print(f"records: the store's lock is held for {time.monotonic() - t:.0f} s; every thread:", file=sys.stderr, flush=True)
                faulthandler.dump_traceback(file=sys.stderr, all_threads=True)


class Readers:
    """Read-only connections to one records file, lent to the requests that only read rows: a search, the records it names, the row of a
    job page, the newest jobs. SQLite lets any number of readers in at once, so none of them waits for a page being drawn (26 Nov 2026:
    /api/search waited behind the job pages' lock and failed with them). A few connections are kept for the next request; when the
    hourly upload brings a new file, the set of the old one is retired and each of its connections closes when it is given back."""
    KEEP = 6

    def __init__(self, path):
        self.path, self.free, self.lock, self.retired = path, [], threading.Lock(), False

    @contextlib.contextmanager
    def borrow(self):
        with self.lock:
            con = self.free.pop() if self.free else None
        if con is None:
            con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
            con.execute("PRAGMA cache_size = -512")      # 512 KB of pages each (SQLite's default is 2 MB): serve.py lives under a 1 GB limit
        try:
            yield con
        finally:
            with self.lock:
                if not self.retired and len(self.free) < self.KEEP: self.free.append(con); con = None
            if con is not None: con.close()

    def retire(self):
        with self.lock:
            self.retired, old, self.free = True, self.free, []
        for c in old: c.close()


class Pages:
    """Finished job pages, kept TTL seconds and at most MAX bytes in all, by slug and the records file they were drawn from: a crawler that
    comes back, our own checks and a link shared in a chat ask for the same page within minutes, and nginx keeps a copy only per exact
    address (a page asked with ?utm_source=... or any other query is drawn again). The oldest go first when it is full."""
    TTL, MAX = 90, 24 << 20

    def __init__(self):
        self.d, self.size, self.lock, self.hits, self.misses = collections.OrderedDict(), 0, threading.Lock(), 0, 0

    def get(self, key):
        with self.lock:
            hit = self.d.get(key)
            if hit and time.monotonic() - hit[0] < self.TTL:
                self.d.move_to_end(key); self.hits += 1
                return hit[1]
            if hit:
                del self.d[key]; self.size -= len(hit[1])
            self.misses += 1
            return None

    def put(self, key, data):
        if len(data) > self.MAX // 16: return               # a page over 1.5 MB is not kept: it would push out a hundred others
        with self.lock:
            old = self.d.pop(key, None)
            if old: self.size -= len(old[1])
            self.d[key] = (time.monotonic(), data); self.size += len(data)
            while self.size > self.MAX:
                _, (_, gone) = self.d.popitem(last=False); self.size -= len(gone)


class Store:
    """Reads data/jobs.db and builds job pages from it. When the hourly build puts a new file in place, the store reads it in the
    background while the old one keeps answering (Store._load), then swaps the two in a moment."""

    def __init__(self, path, b, live=False):
        self.path, self.b, self.live = Path(path), b, live
        self.lock = Guard()                      # the drawing of a page: job_page() reads and sets the build module's globals
        self.loading = threading.Lock()          # one reading of a new file at a time
        self.stamp, self.looked, self.con, self.readers, self.when = None, 0.0, None, None, {}
        self.pages = Pages()

    def _fresh(self):
        if self.con is not None and time.monotonic() - self.looked < 20: return
        self.looked = time.monotonic()
        try:
            st = self.path.stat().st_mtime_ns
        except OSError:
            if self.con is not None: return      # the file is being put in place: the one already open answers
            raise
        if st == self.stamp: return
        if self.con is None:                     # the first opening: every request waits for it
            with self.loading:
                if self.con is None: self._load(st)
            return
        if not self.loading.acquire(blocking=False): return     # another request is reading the new file; the old one answers meanwhile
        try:
            if st != self.stamp: self._load(st)
        finally:
            self.loading.release()

    def _load(self, st):
        """Read a new records file (its shared data and the cards of the similar jobs) without the page lock, then put it in place of
        the old one under the lock, in well under a millisecond. Until 27 Nov 2026 the reading itself held the lock: every job page
        and search waited for it after each hourly upload."""
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        ctx = {k: json.loads(v) for k, v in con.execute("SELECT k, v FROM ctx")}
        tup = lambda k: tuple(k.split(SEP))
        want = sorted({s for xs in ctx["sim_cat"].values() for s in xs})        # a dozen jobs for each field: these few stay in memory
        cards = {}
        for i in range(0, len(want), 900):                      # the similar jobs are shown as cards, which need the record without the text
            part = want[i:i + 900]
            cards.update((s, json.loads(r)) for s, r in con.execute(f"SELECT slug, rec FROM jobs WHERE slug IN ({','.join('?' * len(part))})", part))
        new = {"SIM": {"cat": {c: [cards[s] for s in xs if s in cards] for c, xs in ctx["sim_cat"].items()},
                       "comp": Cards(con, {tup(k): xs for k, xs in ctx.pop("sim_comp").items()})},
               "OPEN": collections.Counter(ctx["open"]), "FACT": ctx["fact"], "CATMED": ctx["catmed"], "CLOSE_DAYS": ctx["close_days"],
               "CO_CLOSE": {c: tuple(v) for c, v in ctx.get("co_close", {}).items()},   # how long each employer's closed roles stayed open (absent before 21 Nov)
               "TB": ctx.get("tb", {}),                 # the employers' trust marks (absent in a store built before 15 Nov)
               "EST": {tup(k): v for k, v in ctx["est"].items()},
               "REPOST": {tup(k): v for k, v in ctx["repost"].items()},
               "PERK_OK": set(ctx["perk_ok"]),
               "V": ctx["v"],                           # the stylesheet and scripts the pages link to are the ones built with the records
               "HMED": ctx.get("hmed", {})}
        count = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        when = {"now": ctx["now"], "today": ctx["today"]}       # only these are read later; the rest of ctx is let go here
        b = self.b
        try:
            guard = self.lock if self.con is not None else contextlib.nullcontext()
            with guard:
                for k, v in new.items(): setattr(b, k, v)
                b.ALL_OPEN[0] = ctx.get("all_open", 0)          # absent in a store built before 25 Nov 2026
                if hasattr(b, "FAM"):                            # absent in a store built before 26 Nov 2026: no estimate rather than the old one
                    b.FAM.clear(); b.FAM.update(ctx.get("fam") or {})
                if hasattr(b, "same_as"):                        # the links to the page that keeps each search, as the build had them
                    b.CAT_HOME.clear(); b.CAT_HOME_RX[0] = None; b.CAT_HOME_PRE[0] = ()     # absent in a store built before 26 Nov 2026: none
                    for src_, dst_ in sorted((ctx.get("cat_home") or {}).items()):
                        if src_ and dst_: b.same_as(src_, dst_)
                old, old_readers = self.con, self.readers
                self.con, self.when, self.stamp, self.count, self.readers = con, when, st, count, Readers(self.path)
        except Busy:                                             # pages are being drawn without pause: try again at the next request
            con.close(); self.looked = 0.0
            return
        if old_readers is not None: old_readers.retire()
        if old is not None: old.close()

    @contextlib.contextmanager
    def reading(self):
        """A read-only connection to the current records file, without the page lock."""
        self._fresh()
        with self.readers.borrow() as con:
            yield con

    def slugs(self):
        with self.reading() as con:
            return {s for (s,) in con.execute("SELECT slug FROM jobs")}

    def search(self, q, remote=False, limit=20, offset=0):
        """Open jobs that have every word of q, best first: the title counts most, the text of the posting least. The last word also
        matches as the start of a word, so "devo" finds "DevOps" while it is being typed. Returns (total, [records])."""
        words = WORD.findall(spell(q).lower())[:12]
        if "remote" in words:                                   # "kubernetes remote": the remote filter, not a word to find in the text
            remote, words = True, [w for w in words if w != "remote"]
        words = [w for w in words if w not in SKIP]
        if not words: return 0, []
        last = words[-1]
        match = " ".join(f'"{w}"' for w in words) + ("*" if last.isalpha() and len(last) >= 3 else "")
        where = "jobs_fts MATCH ? AND j.active = 1" + (" AND json_extract(j.rec, '$.remote')" if remote else "")
        limit, offset = max(1, min(int(limit), 50)), max(0, min(int(offset), 1000))
        with self.reading() as con:
            total = con.execute(f"SELECT COUNT(*) FROM jobs_fts JOIN jobs j ON j.rowid = jobs_fts.rowid WHERE {where}", (match,)).fetchone()[0]
            rows = con.execute(f"SELECT j.rec FROM jobs_fts JOIN jobs j ON j.rowid = jobs_fts.rowid WHERE {where} ORDER BY {RANK} LIMIT ? OFFSET ?",
                               (match, limit, offset)).fetchall()
        return total, [json.loads(r) for (r,) in rows]

    def records(self, slugs):
        """The stored records of these jobs, in the order given (a slug with no record is skipped)."""
        if not slugs: return []
        with self.reading() as con:
            got = {s: json.loads(r) for s, r in con.execute(f"SELECT slug, rec FROM jobs WHERE slug IN ({','.join('?' * len(slugs))})", list(slugs))}
        return [got[s] for s in slugs if s in got]

    def moved(self, slug):
        """The address the hourly record gave a job first published live under this one, or None."""
        got = live_row("SELECT to_slug FROM moved WHERE slug = ?", (slug,))
        return got[0][0] if got else None

    def latest(self, limit=30):
        """The newest open jobs, those found live first: [record], newest first by the time we first saw them."""
        rows = [json.loads(r) for (r,) in (live_row("SELECT rec FROM live WHERE closed = '' ORDER BY seen_at DESC LIMIT ?", (limit,)) or [])]
        rows = [r for r in rows if not r.get("closed_only")]
        with self.reading() as con:
            rows += [json.loads(r) for (r,) in con.execute("SELECT rec FROM jobs WHERE active = 1 ORDER BY first_seen DESC, rowid DESC LIMIT ?", (limit,))]
        rows.sort(key=lambda r: (r.get("ts") or 0, r.get("first_seen_at") or ""), reverse=True)    # newest posting first; a job we only now noticed but posted in August is not "new"
        seen, out = set(), []
        for r in rows:
            if r["slug"] not in seen: seen.add(r["slug"]); out.append(r)
        return out[:limit]

    def record(self, slug):
        """One job as stored, with its text, or None."""
        with self.reading() as con:
            row = con.execute("SELECT rec, descr FROM jobs WHERE slug = ?", (slug,)).fetchone()
        if row is None: return None
        j = json.loads(row[0])
        text = row[1] or (texts.get(j.get("id")) if self.live else "")
        if text: j["desc"] = text
        return j

    def page_bytes(self, slug):
        """page() as UTF-8, kept for a moment (Pages): (bytes or None, whether it came from the copy kept, milliseconds it took to draw)."""
        self._fresh()
        key = (slug, self.stamp)
        got = self.pages.get(key)
        if got is not None: return got, True, 0.0
        t0 = time.perf_counter()
        html_ = self.page(slug)
        ms = (time.perf_counter() - t0) * 1000
        if html_ is None: return None, False, ms
        data = html_.encode("utf-8")
        self.pages.put(key, data)
        return data, False, ms

    def page(self, slug):
        """The finished HTML of a job page, or None when there is no such job.

        Built as of the build that wrote the records (records_test.py compares it with that build's file), or, for a live server, as of
        now: the age of a posting and "posted 20 minutes ago" are then right when the page is opened, not when the site was built.
        Everything that is read (the record, the live store, the kept text) is read before the page lock is taken; only the drawing
        holds it."""
        live = live_row("SELECT rec, descr, closed FROM live WHERE slug = ?", (slug,)) if slug else None
        with self.reading() as con:
            row = con.execute("SELECT rec, descr FROM jobs WHERE slug = ?", (slug,)).fetchone()
        if row is None and live and not json.loads(live[0][0]).get("closed_only"):
            row = live[0][:2]                           # a job live.py found after the last upload
        if row is None: return None
        j = json.loads(row[0])
        # the record's own text, else on our server the one texts.py kept (the record keeps texts of recent postings only)
        text = row[1] or (texts.get(j.get("id")) if self.live else "")
        if text: j["desc"] = text
        if live and live[0][2] and j.get("active"):      # live.py saw it leave its board: closed now, not at the next upload
            j.update(active=False, closed=live[0][2])
        if self.live and j.get("active") and not j.get("tg"):
            # live.py read the company's whole board later than the hourly record did, and this job was on it (one that had left it
            # would be closed just above): "Last checked" is that day, not the day of the last full rebuild
            at = live_checked_at(j.get("company"))
            try:
                day = datetime.date.fromtimestamp(at).isoformat() if at else ""
            except (ValueError, OverflowError, OSError):
                day = ""
            if day > str(j.get("last_seen") or ""): j["last_seen"] = day
            # and the time of that reading, which the page shows as "checked 12 minutes ago" (teardown, 26 Nov 2026)
            if at and datetime.datetime.fromtimestamp(at, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") > str(j.get("checked_at") or ""):
                j["checked_at"] = datetime.datetime.fromtimestamp(at, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.lock:
            b, out = self.b, {}
            if self.live:
                b.NOW = int(time.time())
                b.TODAY = datetime.date.today().isoformat()
                b.VALID_TO = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
            else:
                b.NOW, b.TODAY = self.when["now"], self.when["today"]
                b.VALID_TO = (datetime.date.fromisoformat(b.TODAY) + datetime.timedelta(days=30)).isoformat()
            if hasattr(b, "STALE_DAY"):                  # "Hiring now" or "Posted Jan 2023" as of the day the page is drawn (build.stale)
                b.STALE_DAY = (datetime.date.fromisoformat(b.TODAY) - datetime.timedelta(days=b.LONG_OPEN)).isoformat()
            keep = b.write
            b.write = lambda path, content, sitemap=True: out.__setitem__("html", b.finish_html(content) if hasattr(b, "finish_html") else content)       # page() hands the page to write(); keep it instead, with the same last touches
            try:
                b.job_page(j, {})
            finally:
                b.write = keep
            return out.get("html")
