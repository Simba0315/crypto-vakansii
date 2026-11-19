"""The full text of every open job, kept on our server (texts.db, beside live.db), so that every job page can carry Google's job markup.

Why (owner, 19 Nov 2026: "every job should have the markup"): Google shows a job in its job search only when the page's JobPosting
markup holds the whole description, "a complete representation of the job"; build.job_page() leaves the markup out when it has only
the opening lines. The hourly collection on GitHub keeps the text only of postings published in the last 14 days (collect.DESC_SINCE),
because with every text data/jobs.json would pass GitHub's limit of 100 MB for one file. On 19 Nov 2026 that left 271,724 of the
398,621 open jobs on the server without their text, so without the markup.

So the server keeps the texts itself, and nothing about the hourly collection changes:
- every text the hourly record brings is copied here before it can drop out of the record (Keeper.take_from, at each upload);
- live.py reads the same boards around the clock. For a job the site has whose text is not here, it reads the text too and keeps it
  here: on Greenhouse, Ashby, Lever, Workable, Recruitee, Teamtailor and Personio the text comes with the board's list (no extra
  request); on Workday and SmartRecruiters it costs one request a posting, so only a few each read of a board (live.TEXTS_SLOW);
- records.Store builds a job page with the text from here when its record has none.
A text is stored compressed (zlib, about a quarter of its size). The texts of jobs closed more than KEEP_CLOSED days ago are dropped.

    python3 texts.py --test          checks this file on a temporary database
"""
import datetime, os, sqlite3, sys, threading, zlib
from pathlib import Path

ROOT = Path(__file__).parent
DB = Path(os.environ.get("HRN_TEXTS_DB") or ROOT.parent / "texts.db")
KEEP_CLOSED = 60
# octet_length() gives the length of a stored value without reading the value (SQLite 3.43 and later; our server has 3.45)
BYTES = "octet_length" if sqlite3.sqlite_version_info >= (3, 43) else "length"
SCHEMA = """
CREATE TABLE IF NOT EXISTS texts (id TEXT PRIMARY KEY, company TEXT NOT NULL, body BLOB NOT NULL, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS texts_company ON texts (company);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
"""

_lock, _con = threading.Lock(), None


def get(jid, db=None):
    """The kept text of one job, or "" (also where no texts are kept: a build on GitHub, a laptop). db: another file, for the test."""
    global _con
    path = db or DB
    if not jid or not path.exists(): return ""
    if db:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try: row = con.execute("SELECT body FROM texts WHERE id = ?", (jid,)).fetchone()
        finally: con.close()
    else:
        with _lock:
            try:
                if _con is None: _con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
                row = _con.execute("SELECT body FROM texts WHERE id = ?", (jid,)).fetchone()
            except sqlite3.Error:
                _con = None
                return ""
    return zlib.decompress(row[0]).decode() if row else ""


class Keeper:
    """The writing side, used by live.py (one thread)."""

    def __init__(self, path=None):
        self.con = sqlite3.connect(str(path or DB), isolation_level=None)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(SCHEMA)

    def have(self, company):
        """The ids of one company's jobs whose text is kept."""
        return {i for (i,) in self.con.execute("SELECT id FROM texts WHERE company = ?", (company,))}

    def put(self, jid, company, text):
        if not jid or not text: return
        self.con.execute("INSERT OR REPLACE INTO texts VALUES (?, ?, ?, ?)",
                         (jid, company, zlib.compress(text.encode(), 6), datetime.date.today().isoformat()))

    def take_from(self, jobs_db):
        """Copy the texts an hourly record (data/jobs.db) holds and this store does not yet. The first time every text; then only those
        of jobs first seen in the last three days, the only ones that can be new (reading every text of the record takes a minute).
        Returns how many were copied."""
        since = self.con.execute("SELECT v FROM meta WHERE k = 'copied'").fetchone()
        since = (datetime.date.fromisoformat(since[0]) - datetime.timedelta(days=3)).isoformat() if since else ""
        src = sqlite3.connect(f"file:{jobs_db}?mode=ro", uri=True)
        try:
            rows = src.execute(f"SELECT slug, id FROM jobs WHERE first_seen >= ? AND {BYTES}(descr) > 0", (since,)).fetchall()
            n = 0
            for i in range(0, len(rows), 500):
                part = rows[i:i + 500]
                have = {x for (x,) in self.con.execute(f"SELECT id FROM texts WHERE id IN ({','.join('?' * len(part))})", [jid for _, jid in part])}
                want = [slug for slug, jid in part if jid not in have]
                if not want: continue
                self.con.execute("BEGIN")
                for jid, company, descr in src.execute(f"SELECT id, company, descr FROM jobs WHERE slug IN ({','.join('?' * len(want))})", want):
                    self.put(jid, company, descr); n += 1
                self.con.execute("COMMIT")
        finally:
            src.close()
        self.con.execute("INSERT OR REPLACE INTO meta VALUES ('copied', ?)", (datetime.date.today().isoformat(),))
        return n

    def prune(self, open_ids):
        """Once a day: the texts of jobs still open (open_ids: the record's and the live store's) are marked as seen today, and those of
        jobs not seen open for KEEP_CLOSED days are dropped. Returns how many were dropped."""
        today = datetime.date.today().isoformat()
        ids = list(open_ids)
        self.con.execute("BEGIN")
        for i in range(0, len(ids), 500):
            part = ids[i:i + 500]
            self.con.execute(f"UPDATE texts SET at = ? WHERE at < ? AND id IN ({','.join('?' * len(part))})", [today, today] + part)
        self.con.execute("COMMIT")
        old = (datetime.date.today() - datetime.timedelta(days=KEEP_CLOSED)).isoformat()
        return self.con.execute("DELETE FROM texts WHERE at < ?", (old,)).rowcount

    def count(self):
        return self.con.execute("SELECT count(*) FROM texts").fetchone()[0]


def test():
    import tempfile
    d = Path(tempfile.mkdtemp())
    jobs = sqlite3.connect(d / "jobs.db")
    jobs.executescript("CREATE TABLE jobs (slug TEXT PRIMARY KEY, id TEXT NOT NULL, active INTEGER NOT NULL, company TEXT NOT NULL, cat TEXT NOT NULL,"
                       " first_seen TEXT NOT NULL, rec TEXT NOT NULL, descr TEXT NOT NULL)")
    jobs.executemany("INSERT INTO jobs VALUES (?, ?, 1, ?, 'x', ?, '{}', ?)",
                     [("a-acme", "greenhouse-acme-1", "Acme", "2026-11-01", "<p>Build things.</p>" * 50),
                      ("b-acme", "greenhouse-acme-2", "Acme", "2026-11-18", ""),
                      ("c-beta", "lever-beta-3", "Beta", "2026-11-18", "<p>Sell things.</p>")])
    jobs.commit(); jobs.close()
    k = Keeper(d / "texts.db")
    assert k.take_from(d / "jobs.db") == 2 and k.take_from(d / "jobs.db") == 0
    assert k.have("Acme") == {"greenhouse-acme-1"}
    k.put("greenhouse-acme-2", "Acme", "<p>Test things.</p>")
    assert get("greenhouse-acme-2", d / "texts.db") == "<p>Test things.</p>"
    assert get("greenhouse-acme-1", d / "texts.db") == "<p>Build things.</p>" * 50
    assert get("nope", d / "texts.db") == "" and get("x", d / "none.db") == ""
    k.con.execute("UPDATE texts SET at = '2020-01-01'")
    assert k.prune({"lever-beta-3", "greenhouse-acme-2"}) == 1 and k.count() == 2 and get("greenhouse-acme-1", d / "texts.db") == ""
    print("texts.py: all checks passed")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--test"]: test()
    else: print(f"{Keeper().count():,} texts in {DB}")
