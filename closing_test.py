"""Checks for how jobs close and what a job page says about the last check, without the network and without the real stores:
boards that no longer exist (collect.board_gone, collect.close_gone), the day live.py last read a board to the end (live.Live.apply,
table read_ok) and the "Last checked" day a job page takes from it (records.live_checked).

    python3 closing_test.py            must end with "0 failed" (about 15 seconds: it imports live.py, which imports build.py)
    python3 closing_test.py --live     also asks the real hiring systems about a few boards (one request each)
"""
import datetime, os, sys, tempfile, time
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="hrn_closing_test_")
os.environ["HRN_LIVE_DB"], os.environ["HRN_TEXTS_DB"] = os.path.join(TMP, "live.db"), os.path.join(TMP, "texts.db")
os.environ.pop("HRN_OPENSEARCH", None)
sys.path.insert(0, str(Path(__file__).parent))
import collect, net                     # noqa: E402

failed = 0


def ok(cond, what):
    global failed
    if not cond:
        failed += 1
        print("FAILED:", what)


# --- board_gone: what counts as "no such board" ------------------------------------------------------------------------------------
answers = {}
asked = []
real_probe = net.probe


def fake_probe(url, timeout=30, data=None):
    asked.append(url)
    return answers.get(url.split("/")[2], None)


net.probe = fake_probe
collect.ATS_GAP = {}                    # no pauses in the test
for ats, tok, host, got, want in [
    ("greenhouse", "acme", "boards-api.greenhouse.io", (404, "https://boards-api.greenhouse.io/v1/boards/acme/jobs", '{"status":404,"error":"Job not found"}'), True),
    ("greenhouse", "acme", "boards-api.greenhouse.io", (200, "https://boards-api.greenhouse.io/v1/boards/acme/jobs", '{"jobs":[]}'), False),
    ("greenhouse", "acme", "boards-api.greenhouse.io", (403, "https://boards-api.greenhouse.io/v1/boards/acme/jobs", "Forbidden"), False),
    ("greenhouse", "acme", "boards-api.greenhouse.io", (500, "https://boards-api.greenhouse.io/v1/boards/acme/jobs", ""), False),
    ("greenhouse", "acme", "boards-api.greenhouse.io", None, False),
    ("greenhouse", "acme", "boards-api.greenhouse.io", (404, "https://elsewhere.example/oops", ""), False),
    ("ashby", "acme", "api.ashbyhq.com", (404, "https://api.ashbyhq.com/posting-api/job-board/acme", "Not Found"), True),
    ("lever", "acme", "api.lever.co", (404, "https://api.lever.co/v0/postings/acme?mode=json&limit=1", '{"ok":false}'), True),
    ("bamboohr", "acme", "acme.bamboohr.com", (200, "https://www.bamboohr.com/", "<html>"), True),
    ("bamboohr", "acme", "acme.bamboohr.com", (200, "https://acme.bamboohr.com/careers/list", '{"result":[]}'), False),
    ("bamboohr", "acme", "acme.bamboohr.com", (404, "https://acme.bamboohr.com/careers/list", ""), False),
    ("bamboohr", "acme", "acme.bamboohr.com", (200, "https://acme.bamboohr.com/settings/account/expired.php", "<html>"), True),
    ("bamboohr", "acme", "acme.bamboohr.com", (200, "https://acme.bamboohr.com/login.php?r=%2Fsettings%2Faccount%2Fsuspended", "<html>"), True),
    ("bamboohr", "acme", "acme.bamboohr.com", (200, "https://acme.bamboohr.com/login.php?r=%2Fcareers", "<html>"), False),
    ("jazzhr", "acme", "acme.applytojob.com", (200, "https://www.jazzhr.com/job-seekers", "<html>"), True),
    ("jazzhr", "acme", "acme.applytojob.com", (200, "https://acme.applytojob.com/apply", "resumator-jobboard"), False),
    ("paylocity", "0000", "recruiting.paylocity.com", (200, "https://recruiting.paylocity.com/Recruiting/jobs/JobNotFound", "<html>"), True),
    ("paylocity", "0000", "recruiting.paylocity.com", (200, "https://recruiting.paylocity.com/recruiting/jobs/All/0000/jobs", "pageData"), False),
    ("trakstar", "acme", "jsapi.recruiterbox.com", (400, "https://jsapi.recruiterbox.com/v1/openings", '{"client_name": "Invalid client name"}'), True),
    ("trakstar", "acme", "jsapi.recruiterbox.com", (400, "https://jsapi.recruiterbox.com/v1/openings", '{"limit": "bad"}'), False),
    ("workday", "acme.wd5/Careers", "acme.wd5.myworkdayjobs.com", (404, "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/jobs",
                                                                  '{"errorCode":"S21","httpStatus":404}'), True),
    ("workday", "acme.wd5/Careers", "acme.wd5.myworkdayjobs.com", (404, "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/jobs", "<html>maintenance"), False),
    ("workday", "acme.wd5/Careers", "acme.wd5.myworkdayjobs.com", (503, "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/jobs", '{"errorCode":"X"}'), False),
    ("icims", "careers-acme", "careers-acme.icims.com", (404, "https://careers-acme.icims.com/sitemap.xml", "<title>gone: careers-acme.icims.com : dc409</title>"), True),
    ("icims", "careers-acme", "careers-acme.icims.com", (404, "https://careers-acme.icims.com/sitemap.xml", "<title>Not found</title>"), False),
    ("rippling", "acme", "api.rippling.com", (404, "https://api.rippling.com/platform/api/ats/v1/board/acme/jobs", '{"error_code":"RESOURCE_NOT_FOUND"}'), True),
    ("gem", "acme", "api.gem.com", (404, "https://api.gem.com/job_board/v0/acme/job_posts/", '{"code":404}'), True),
]:
    answers.clear(); answers[host] = got
    ok(collect.board_gone({"name": "Acme", "ats": ats, "token": tok}) is want, f"board_gone {ats} {got and got[:2]} -> {want}")
asked.clear()
for src in ({"ats": "teamtailor", "token": "careers.acme.com"}, {"ats": "personio", "token": "jobs.acme.de"}, {"ats": "usajobs", "token": "AF"},
            {"ats": "greenhouse", "token": ""}, {"ats": "greenhouse", "token": "a/b"}, {"ats": "nosuch", "token": "x"}, {}):
    ok(collect.board_gone(src) is False, f"board_gone {src} -> False")
ok(not asked, f"no request for boards without a clear answer ({asked})")
net.probe = real_probe

# --- close_gone: which jobs close -------------------------------------------------------------------------------------------------
TODAY = "2026-11-26"


def job(company, n, seen, **kw):
    return {f"x-{company}-{n}": dict({"company": company, "active": True, "last_seen": seen, "id": f"x-{company}-{n}"}, **kw)}


def setup():
    db = {}
    for n in range(3): db.update(job("Gone", n, "2026-11-16"))
    for n in range(2): db.update(job("Recent", n, "2026-11-25"))                 # failed, but read yesterday: not asked yet
    db.update(job("Alive", 0, "2026-11-20"))                                       # failed long, but its system does not say "gone"
    db.update(job("Gone", 9, "2026-11-10", direct=True))                           # posted here: never closed by a board
    db.update(job("NoDate", 0, None))                                              # no last_seen at all: counts as long unseen
    sources = [{"name": n, "ats": "ashby", "token": n.lower()} for n in ("Gone", "Recent", "Alive", "NoDate", "Fine")]
    open_by_co = {}
    for jid, j in db.items(): open_by_co.setdefault(j["company"], []).append(jid)
    return db, sources, open_by_co


db, sources, open_by_co = setup()
stats = {"failed": ["Gone", "Recent", "Alive", "NoDate", "Renamed"], "closed": 7}
asked = []
n = collect.close_gone(db, sources, list(stats["failed"]), open_by_co, stats, gone=lambda s: asked.append(s["name"]) or s["name"] in ("Gone", "NoDate", "Recent"), today=TODAY)
ok(n == 4, f"4 jobs closed, got {n}")
ok(all(not db[f"x-Gone-{i}"]["active"] and db[f"x-Gone-{i}"]["closed"] == TODAY for i in range(3)), "the gone board's jobs are closed today")
ok(db["x-Gone-9"]["active"], "a job posted here stays open")
ok(all(db[f"x-Recent-{i}"]["active"] for i in range(2)), "a board read in the last GONE_DAYS days is not closed")
ok("Recent" not in asked, "a board read in the last GONE_DAYS days is not even asked")
ok(db["x-Alive-0"]["active"], "a failed board that still exists keeps its jobs")
ok(not db["x-NoDate-0"]["active"], "a job without last_seen counts as long unseen")
ok(stats["failed"] == ["Recent", "Alive", "Renamed"], f"gone boards leave the failed list: {stats['failed']}")
ok(stats["gone"] == ["Gone (3)", "NoDate (1)"], f"stats gone: {stats.get('gone')}")
ok(stats["closed"] == 11, f"closed count added: {stats['closed']}")

# a hiring system that says "no such board" for many boards at once: nothing closes
db = {}
sources = [{"name": f"B{i}", "ats": "greenhouse", "token": f"b{i}"} for i in range(20)]
for i in range(20): db.update(job(f"B{i}", 0, "2026-11-01"))
open_by_co = {j["company"]: [jid] for jid, j in db.items()}
stats = {"failed": [f"B{i}" for i in range(6)], "closed": 0}
n = collect.close_gone(db, sources, list(stats["failed"]), open_by_co, stats, gone=lambda s: True, today=TODAY)
ok(n == 0 and all(j["active"] for j in db.values()) and "gone" not in stats, "a storm of 'no such board' closes nothing")
stats = {"failed": ["B1"], "closed": 0}
ok(collect.close_gone(db, sources, ["B1"], open_by_co, stats, gone=lambda s: True, today=TODAY) == 1, "one gone board among many closes")

# empty and missing data never crash
ok(collect.close_gone({}, [], [], {}, {"failed": [], "closed": 0}, gone=lambda s: True, today=TODAY) == 0, "nothing at all")
ok(collect.close_gone({}, [], ["X"], {"X": ["x-1"]}, {"failed": ["X"]}, gone=lambda s: True, today=TODAY) == 0, "ids not in the record")
ok(collect.close_gone({"x-1": {"company": "X", "active": False}}, [{"name": "X", "ats": "ashby", "token": "x"}], ["X"], {"X": ["x-1"]}, {"failed": ["X"]},
                      gone=lambda s: True, today=TODAY) == 0, "already closed jobs")
st = {"failed": ["X"]}
ok(collect.close_gone({"x-1": {"company": "X", "active": True}}, [{"name": "X", "ats": "ashby", "token": "x"}], ["X"], {"X": ["x-1"]}, st,
                      gone=lambda s: True, today=TODAY) == 1 and st["closed"] == 1, "stats without a closed count")

# --- live.py: a board read to the end is noted (read_ok), and a job page's "Last checked" day comes from it ------------------------------
import live, records                    # noqa: E402
ok(str(live.LIVE_DB).startswith(TMP) and str(records.LIVE_DB).startswith(TMP), "the test uses its own live store")
ok(records.live_checked("Acme") == "", "no live store yet: no day")
lv = live.Live(write=True)
lv.known = {"greenhouse-acme-1": "a-1", "greenhouse-acme-2": "a-2"}
lv.by_co = {"Acme": {"greenhouse-acme-1", "greenhouse-acme-2"}, "Big": {f"greenhouse-big-{i}" for i in range(25)}}
lv.known.update({f"greenhouse-big-{i}": f"b-{i}" for i in range(25)})
src = {"name": "Acme", "ats": "greenhouse", "token": "acme"}
got = lv.apply(src, [{"id": "greenhouse-acme-1", "title": "-", "url": "-"}])
ok(got == (0, 1, 0), f"one job left the board and closed: {got}")
row = lv.con.execute("SELECT company, at FROM read_ok").fetchall()
ok(len(row) == 1 and row[0][0] == "Acme" and abs(row[0][1] - time.time()) < 60, f"read_ok noted for Acme: {row}")
ok(records.live_checked("Acme") == datetime.date.today().isoformat(), f"live_checked gives today: {records.live_checked('Acme')!r}")
ok(records.live_checked("Nobody") == "" and records.live_checked(None) == "", "a company never read: no day")
got = lv.apply({"name": "Big", "ats": "greenhouse", "token": "big"}, [])
ok(got == (0, 0, 0) and records.live_checked("Big") == "", "an empty answer from a board of 25 open jobs closes nothing and is not a check")
lv.con.execute("INSERT OR REPLACE INTO read_ok VALUES ('Odd', 'not a time')")
ok(records.live_checked("Odd") == "", "a bad value in the store gives no day")
dry = live.Live(write=False)
dry.known, dry.by_co = {"greenhouse-c-1": "c-1"}, {"C": {"greenhouse-c-1"}}
dry.apply({"name": "C", "ats": "greenhouse", "token": "c"}, [{"id": "greenhouse-c-1", "title": "-", "url": "-"}])
ok(records.live_checked("C") == "", "a dry run (live.py --once) writes nothing")

# --- live.py reload: a closing noted for a job the new hourly record no longer has must not stop the program -------------------------
import json, sqlite3                     # noqa: E402
jdb = os.path.join(TMP, "jobs.db")
con = sqlite3.connect(jdb)
con.execute("CREATE TABLE jobs (slug TEXT PRIMARY KEY, id TEXT, active INTEGER, company TEXT, cat TEXT, first_seen TEXT, rec TEXT, descr TEXT)")
for jid, slug, act in (("greenhouse-acme-1", "a-1", 1), ("greenhouse-acme-2", "a-2", 1), ("greenhouse-acme-3", "a-3", 0)):
    con.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)", (slug, jid, act, "Acme", "engineering", "2026-11-20",
                                                         json.dumps({"title": "Engineer " + slug, "location": "Berlin", "remote": False, "url": "https://x/" + slug}), "<p>t</p>"))
con.commit(); con.close()
live.JOBS_DB = Path(jdb)
lv = live.Live(write=False)
rows = [("greenhouse-old-9", "old-9", "Old", {"slug": "old-9", "id": "greenhouse-old-9", "company": "Old", "closed_only": True}, "2026-11-25"),   # the crash of 25 Nov
        ("greenhouse-acme-2", "a-2", "Acme", {"slug": "a-2", "id": "greenhouse-acme-2", "company": "Acme", "closed_only": True}, "2026-11-25"),  # closed here, open in the record
        ("greenhouse-acme-3", "a-3", "Acme", {"slug": "a-3", "id": "greenhouse-acme-3", "company": "Acme", "closed_only": True}, "2026-11-25"),  # the record closed it too
        ("ashby-new-1", "new-1", "New", {"title": "Designer", "company": "New", "location": "Paris", "remote": True, "url": "https://y/1"}, ""),   # found here
        ("ashby-odd-1", "odd-1", "Odd", "not json", ""), ("ashby-odd-2", "odd-2", "Odd", ["a", "list"], "")]
for jid, slug, co, rec, closed in rows:
    lv.con.execute("INSERT INTO live VALUES (?,?,?,?,?,?,?)", (jid, slug, co, rec if isinstance(rec, str) else json.dumps(rec), "", 0, closed))
try:
    did = lv.reload()
except Exception as ex:
    did = f"{type(ex).__name__}: {ex}"
ok(did is True, f"reload with odd live rows works: {did}")
left = {jid for (jid,) in lv.con.execute("SELECT id FROM live")}
ok(left == {"greenhouse-acme-2", "ashby-new-1"}, f"kept: the closing the record has not caught up with, and the job found here; got {sorted(left)}")
ok("new-1" in lv.slugs and lv.by_co.get("Acme") == {"greenhouse-acme-1", "greenhouse-acme-2"}, "the job found here keeps its address; the record's open jobs are known")
ok(lv.reload() is False, "the same record is not read twice")

if "--live" in sys.argv:
    for src, want in (({"ats": "ashby", "token": "klaviyo"}, True), ({"ats": "greenhouse", "token": "headoutcareers"}, True),
                      ({"ats": "lever", "token": "1inch"}, False), ({"ats": "greenhouse", "token": "anthropic"}, False)):
        got = collect.board_gone(src)
        print(f"live: {src['ats']} {src['token']}: gone={got}")
        ok(got is want, f"live {src} -> {want}")

import shutil
shutil.rmtree(TMP, ignore_errors=True)
print(f"closing_test: {failed} failed")
sys.exit(1 if failed else 0)
