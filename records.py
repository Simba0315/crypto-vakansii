"""Job records: every job is one row in a SQLite file (data/jobs.db) instead of one HTML file, the way large job sites keep postings
(Indeed's Docstore hands out job records from a store and builds the page when someone asks for it).

build.py writes the file when HRN_RECORDS is set: "1" writes the records and no job pages, "both" writes the records and the pages too,
which records_test.py uses to check that a page built from a record is the same page, byte for byte. serve.py and check.py read it.

A page needs more than its own record: the similar jobs, the open roles of the company, the medians of its field. build.py works those
out once per build; they are stored next to the records in the table ctx and loaded once, not per page.
"""
import collections, datetime, html, json, os, re, sqlite3, threading, time
from pathlib import Path

SCHEMA = """
CREATE TABLE jobs (slug TEXT PRIMARY KEY, id TEXT NOT NULL, active INTEGER NOT NULL, company TEXT NOT NULL, cat TEXT NOT NULL,
                   first_seen TEXT NOT NULL, rec TEXT NOT NULL, descr TEXT NOT NULL);
CREATE INDEX jobs_company ON jobs (company);
CREATE INDEX jobs_cat ON jobs (cat, active);
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
        "open": dict(b.OPEN), "fact": b.FACT, "catmed": b.CATMED, "est": {key(k): v for k, v in b.EST.items()},
        "close_days": b.CLOSE_DAYS, "repost": {key(k): v for k, v in b.REPOST.items()}, "perk_ok": sorted(b.PERK_OK),
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


class Store:
    """Reads data/jobs.db and builds job pages from it. When the hourly build puts a new file in place, the next request opens it."""

    def __init__(self, path, b, live=False):
        self.path, self.b, self.live = Path(path), b, live
        self.lock = threading.Lock()
        self.stamp, self.looked, self.con = None, 0.0, None

    def _fresh(self):
        if self.con is not None and time.monotonic() - self.looked < 20: return
        self.looked = time.monotonic()
        st = self.path.stat().st_mtime_ns
        if st == self.stamp: return
        con = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True, check_same_thread=False)
        ctx = {k: json.loads(v) for k, v in con.execute("SELECT k, v FROM ctx")}
        want = {s for xs in ctx["sim_cat"].values() for s in xs} | {s for xs in ctx["sim_comp"].values() for s in xs}
        cards, want = {}, sorted(want)
        for i in range(0, len(want), 900):                      # the similar jobs are shown as cards, which need the record without the text
            part = want[i:i + 900]
            cards.update((s, json.loads(r)) for s, r in con.execute(f"SELECT slug, rec FROM jobs WHERE slug IN ({','.join('?' * len(part))})", part))
        tup = lambda k: tuple(k.split(SEP))
        b = self.b
        b.SIM = {"cat": {c: [cards[s] for s in xs if s in cards] for c, xs in ctx["sim_cat"].items()},
                 "comp": {tup(k): [cards[s] for s in xs if s in cards] for k, xs in ctx["sim_comp"].items()}}
        b.OPEN = collections.Counter(ctx["open"])
        b.FACT, b.CATMED, b.CLOSE_DAYS = ctx["fact"], ctx["catmed"], ctx["close_days"]
        b.EST = {tup(k): v for k, v in ctx["est"].items()}
        b.REPOST = {tup(k): v for k, v in ctx["repost"].items()}
        b.PERK_OK = set(ctx["perk_ok"])
        b.V = ctx["v"]                                           # the stylesheet and scripts the pages link to are the ones built with the records
        if self.con is not None: self.con.close()
        self.con, self.ctx, self.stamp = con, ctx, st
        self.count = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

    def slugs(self):
        with self.lock:
            self._fresh()
            return {s for (s,) in self.con.execute("SELECT slug FROM jobs")}

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
        with self.lock:
            self._fresh()
            total = self.con.execute(f"SELECT COUNT(*) FROM jobs_fts JOIN jobs j ON j.rowid = jobs_fts.rowid WHERE {where}", (match,)).fetchone()[0]
            rows = self.con.execute(f"SELECT j.rec FROM jobs_fts JOIN jobs j ON j.rowid = jobs_fts.rowid WHERE {where} ORDER BY {RANK} LIMIT ? OFFSET ?",
                                    (match, limit, offset)).fetchall()
        return total, [json.loads(r) for (r,) in rows]

    def record(self, slug):
        """One job as stored, with its text, or None."""
        with self.lock:
            self._fresh()
            row = self.con.execute("SELECT rec, descr FROM jobs WHERE slug = ?", (slug,)).fetchone()
        if row is None: return None
        j = json.loads(row[0])
        if row[1]: j["desc"] = row[1]
        return j

    def page(self, slug):
        """The finished HTML of a job page, or None when there is no such job.

        Built as of the build that wrote the records (records_test.py compares it with that build's file), or, for a live server, as of
        now: the age of a posting and "posted 20 minutes ago" are then right when the page is opened, not when the site was built."""
        with self.lock:
            self._fresh()
            row = self.con.execute("SELECT rec, descr FROM jobs WHERE slug = ?", (slug,)).fetchone()
            if row is None: return None
            j = json.loads(row[0])
            if row[1]: j["desc"] = row[1]
            b, out = self.b, {}
            if self.live:
                b.NOW = int(time.time())
                b.TODAY = datetime.date.today().isoformat()
                b.VALID_TO = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
            else:
                b.NOW, b.TODAY = self.ctx["now"], self.ctx["today"]
                b.VALID_TO = (datetime.date.fromisoformat(b.TODAY) + datetime.timedelta(days=30)).isoformat()
            keep = b.write
            b.write = lambda path, content, sitemap=True: out.__setitem__("html", content)       # page() hands the page to write(); keep it instead
            try:
                b.job_page(j, {})
            finally:
                b.write = keep
            return out.get("html")
