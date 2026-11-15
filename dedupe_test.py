"""Pairs of records that must and must not be taken for one job (dedupe.py).   python3 dedupe_test.py   -> "0 failed"."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import dedupe     # noqa: E402

ok = bad = 0


def check(name, cond, info=""):
    global ok, bad
    if cond: ok += 1
    else:
        bad += 1; print("FAIL", name, info)


def rec(i, company, title, location="", remote=False, posted="2026-11-10", **kw):
    return dict(id=i, company=company, title=title, location=location, remote=remote, posted=posted, first_seen=posted, active=True,
                url=f"https://example.org/{i}", **kw)


SAME = [   # (a, b): one opening listed twice
    (rec("greenhouse-acme-1", "Acme", "Senior Data Engineer", "Berlin, Germany"), rec("remotive-acme-9", "Acme GmbH", "Sr. Data Engineer (m/w/d)", "Berlin")),
    (rec("lever-stripe-1", "Stripe", "Software Engineer, Payments", "Remote", True), rec("remoteok-stripe-2", "Stripe, Inc.", "Software Engineer - Payments - Remote", "", True)),
    (rec("ashby-ramp-1", "Ramp", "Product Designer", "New York, NY"), rec("arbeitnow-ramp-3", "RAMP", "Product Designer - New York", "New York, NY, United States")),
    (rec("workable-blue-1", "Blueground", "Jr. Backend Developer", "Athens, Greece"), rec("jobicy-blue-4", "Blueground", "Junior Backend Developer", "Athens")),
    (rec("greenhouse-meta-1", "Meta", "Research Scientist, AI", "Menlo Park, CA"), rec("hn-meta-5", "Meta Platforms", "Research Scientist AI", "Menlo Park, CA")),
    (rec("recruitee-bunq-1", "bunq", "Security Engineer", "Amsterdam, Netherlands"), rec("tg-x-1", "bunq", "Security Engineer", "Amsterdam", tg="itjobs")),
    (rec("personio-x-1", "Example Labs", "Head of Sales DACH", "Munich"), rec("himalayas-x-2", "Example Labs AG", "Head of Sales (DACH)", "")),
]
DIFFERENT = [   # (a, b): two openings, or not the same company
    (rec("greenhouse-acme-1", "Acme", "Senior Data Engineer", "Berlin, Germany"), rec("remotive-acme-9", "Acme", "Senior Data Analyst", "Berlin")),
    (rec("greenhouse-acme-1", "Acme", "Senior Data Engineer", "Berlin, Germany"), rec("remotive-acme-9", "Acme", "Senior Data Engineer", "Toronto, Canada")),
    (rec("greenhouse-acme-1", "Acme", "Senior Data Engineer", "Berlin, Germany"), rec("remotive-acme-9", "Acme Robotics", "Senior Data Engineer", "Berlin")),
    (rec("greenhouse-acme-1", "Acme", "Senior Data Engineer", "Berlin", posted="2026-08-01"), rec("remotive-acme-9", "Acme", "Senior Data Engineer", "Berlin", posted="2026-11-10")),
    (rec("lever-x-1", "Example", "Engineering Manager, Platform", "London, UK"), rec("jobicy-x-2", "Example", "Engineering Manager, Payments", "London, UK")),
    (rec("lever-x-1", "Example", "Account Executive", "Paris, France"), rec("lever-x-2", "Example", "Account Executive", "Paris, France")),   # one board, twice
    (rec("ashby-t-1", "Tandem Health", "Product Manager", "Stockholm"), rec("platsbanken-1", "Tandem Health AB", "Product Marketing Manager", "Stockholm, Sweden", src="Platsbanken")),
    (rec("ashby-t-1", "Tandem Health", "Software Engineer", "Stockholm"), rec("platsbanken-2", "Tandem Health AB", "Senior Software Engineer", "Stockholm", src="Platsbanken")),
    (rec("greenhouse-n-1", "Nebius", "Staff Machine Learning Engineer, LLM", "London, UK"), rec("arbeitnow-n-2", "Nebius", "Senior Machine Learning Engineer, LLM", "London")),
    (rec("greenhouse-d-1", "Databricks", "Lead Solutions Architect - GenAI", "Remote - Sweden", True), rec("jobicy-d-2", "Databricks", "Lead Solutions Architect - GenAI", "Remote, UK", True)),
]

for a, b in SAME:
    db = {a["id"]: dict(a), b["id"]: dict(b)}
    n = dedupe.run(db)
    kept = [j for j in db.values() if not j.get("dup_of")]
    check(f"same: {a['title']} / {b['title']}", n == 1 and len(kept) == 1, (dedupe.title_key(a["title"], a["location"]), dedupe.title_key(b["title"], b["location"])))
    if len(kept) == 1:
        check(f"kept the employer's own record: {a['id']}", kept[0]["id"] == a["id"], kept[0]["id"])
        check("the other source is named on it", kept[0]["seen_on"] and kept[0]["seen_on"][0]["url"] == b["url"], kept[0].get("seen_on"))

for a, b in DIFFERENT:
    db = {a["id"]: dict(a), b["id"]: dict(b)}
    check(f"different: {a['title']} ({a['location']}) / {b['title']} ({b['location']})", dedupe.run(db) == 0)

# two postings of one board never merge, even through a third listing that matches both
db = {x["id"]: x for x in (rec("ashby-h-1", "Horizon3.ai", "Enterprise Account Executive", "Norway", True), rec("ashby-h-2", "Horizon3.ai", "Enterprise Account Executive", "Belgium", True),
                            rec("jobicy-h-3", "Horizon3.ai", "Enterprise Account Executive", "Remote", True))}
dedupe.run(db)
check("one board's two postings stay two", not db["ashby-h-1"].get("dup_of") and not db["ashby-h-2"].get("dup_of") and db["jobicy-h-3"].get("dup_of") == "ashby-h-1",
      [(j["id"], j.get("dup_of")) for j in db.values()])
check("remote US spellings agree", dedupe.lands({"usa", "*remote"}) == dedupe.lands({"united states (remote)"}) == {"united states"})

# a job posted on our site ranks above a job board, below the employer's own system
db = {x["id"]: x for x in (rec("direct-acme-1", "Acme", "QA Engineer", "Remote", True, direct=True), rec("remotive-acme-2", "Acme", "QA Engineer", "Remote", True),
                            rec("greenhouse-acme-3", "Acme", "QA Engineer", "Remote", True))}
dedupe.run(db)
check("three sources, one kept: the hiring system", [j["id"] for j in db.values() if not j.get("dup_of")] == ["greenhouse-acme-3"])
check("both others listed", len(db["greenhouse-acme-3"]["seen_on"]) == 2)
del db["greenhouse-acme-3"]
dedupe.run(db)
check("the twin closed: the next best comes back", [j["id"] for j in db.values() if not j.get("dup_of")] == ["direct-acme-1"])

# normalising
check("title key", dedupe.title_key("Sr. Software Eng. (f/m/d) – Remote") == "senior software engineer", dedupe.title_key("Sr. Software Eng. (f/m/d) – Remote"))
check("company key", dedupe.company_key("The Acme Company, Inc.") == dedupe.company_key("ACME") == "acme")
check("alias", dedupe.company_key("Meta Platforms, Inc.") == dedupe.company_key("Meta"))
check("token set", dedupe.token_set_ratio("senior data engineer", "data engineer senior") == 1.0)
check("a title inside a longer one is not the same", dedupe.token_set_ratio("product manager", "product marketing manager") < 0.9)
check("one word more in a long title is", dedupe.token_set_ratio("senior backend engineer payments platform team", "senior backend engineer payments platform") >= 0.9)

print(f"{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)
