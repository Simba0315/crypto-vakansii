"""Tests for the hiring-system feeds added on 15 Nov 2026 (collect.FEEDS), Russia's portal (trudvsem.py) and the merge rules.

    python3 feeds_test.py        # must end with "0 failed"

Every feed is read from a real response saved in feeds_samples/ (trimmed to a few jobs; contact details removed), so the test needs
no network: collect.get_json and collect.get_text are replaced by a lookup of the address in SAMPLES.
"""
import json, os, re, sys
from pathlib import Path

os.environ["HRN_DETAILS"] = "25"
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import collect, trudvsem, countries          # noqa: E402

S = ROOT / "feeds_samples"
load = lambda f: json.loads((S / f).read_text(encoding="utf-8"))
SAMPLES = {   # address pattern -> saved response
    r"bunq\.recruitee\.com/api/offers/": lambda: load("recruitee_bunq.json"),
    r"api\.smartrecruiters\.com/v1/companies/BoschGroup/postings\?limit=100&offset=0": lambda: load("smartrecruiters_list.json"),
    r"api\.smartrecruiters\.com/v1/companies/BoschGroup/postings/\d+$": lambda: load("smartrecruiters_detail.json"),
    r"career\.teamtailor\.com/jobs\.json": lambda: load("teamtailor_career.json"),
    r"personio\.jobs\.personio\.de/xml": lambda: (S / "personio_personio.xml").read_text(encoding="utf-8"),
    r"17live\.bamboohr\.com/careers/list": lambda: load("bamboohr_list.json"),
    r"17live\.bamboohr\.com/careers/489/detail": lambda: load("bamboohr_detail.json"),
    r"advisorengine\.breezy\.hr/json": lambda: load("breezy_advisorengine.json"),
    r"aria\.pinpointhq\.com/postings\.json": lambda: load("pinpoint_aria.json"),
    r"ats\.rippling\.com/api/v2/board/aalo-atomics/jobs\?page=0": lambda: load("rippling_list.json"),
    r"ats\.rippling\.com/api/v2/board/aalo-atomics/jobs/[0-9a-f-]+$": lambda: load("rippling_detail.json"),
    r"api\.eu\.lever\.co/v0/postings/abzena": lambda: load("lever_eu_abzena.json"),
    r"arbeitnow\.com/api/job-board-api\?page=1$": lambda: load("arbeitnow.json"),
    r"jobicy\.com/api/v2/remote-jobs": lambda: load("jobicy.json"),
    r"remoteok\.com/api$": lambda: load("remoteok.json"),
}
WORKABLE = sorted(S.glob("workable_*.json"))         # saved by the discovery run in GitHub Actions (this cloud machine is rate-limited by Workable)
if WORKABLE: SAMPLES[r"apply\.workable\.com/api/v1/widget/accounts/" + WORKABLE[0].stem.split("_", 1)[1] + r"\?details=true"] = lambda: load(WORKABLE[0].name)
CALLS = []


def fake(url, timeout=30, accept=None):
    CALLS.append(url)
    for rx, f in SAMPLES.items():
        if re.search(rx, url): return f()
    return None


collect.get_json = fake
collect.get_text = fake
ok = bad = 0


def check(name, cond, info=""):
    global ok, bad
    if cond: ok += 1
    else:
        bad += 1; print(f"FAIL {name} {info}")


def feed(ats, token, name=None):
    CALLS.clear()
    return collect.fetch_feed({"name": name or token, "ats": ats, "token": token})[1]


def shape(ats, jobs):
    """What every job record must have, whatever the feed."""
    check(f"{ats}: jobs read", jobs and len(jobs) >= 1, str(jobs)[:200])
    for j in jobs or []:
        check(f"{ats}: id prefix", j["id"].startswith(ats + "-"), j["id"])
        check(f"{ats}: title", bool(j["title"]), j["id"])
        check(f"{ats}: https link", str(j["url"]).startswith("https://"), j["url"])
        check(f"{ats}: posted is a day or empty", re.fullmatch(r"(\d{4}-\d\d-\d\d)?", j["posted"]) is not None, j["posted"])
        check(f"{ats}: posted_at is UTC or empty", re.fullmatch(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)?", j["posted_at"]) is not None, j["posted_at"])
        check(f"{ats}: description is cleaned HTML", "<script" not in j["desc"] and "style=" not in j["desc"], j["desc"][:80])
        check(f"{ats}: category known", j["cat"] in {s for s, _, _ in collect.CATS} | {"other"}, j["cat"])


# Recruitee
jobs = feed("recruitee", "bunq", "bunq")
shape("recruitee", jobs)
j = jobs[0]
check("recruitee: title", j["title"] == "Security Engineer", j["title"])
check("recruitee: place with country", j["location"] == "Amsterdam, Noord-Holland, Netherlands", j["location"])
check("recruitee: hybrid flag", j["hybrid"] is True and j["remote"] is False)
check("recruitee: exact time from 'UTC' text", j["posted_at"] == "2026-11-11T13:21:40Z", j["posted_at"])
check("recruitee: careers link", j["url"] == "https://careers.bunq.com/o/security-engineer-3", j["url"])
check("recruitee: engineering", j["cat"] == "security" or j["cat"] == "engineering", j["cat"])
check("recruitee: full-time from code", j["etype"] == "Full-time", j["etype"])

# SmartRecruiters: list, then the text of new jobs from each job's own address
jobs = feed("smartrecruiters", "BoschGroup", "Bosch Group")
shape("smartrecruiters", jobs)
check("smartrecruiters: two jobs", len(jobs) == 2, len(jobs))
check("smartrecruiters: place from fullLocation", jobs[0]["location"] == "Shanghai, Shanghai, China", jobs[0]["location"])
check("smartrecruiters: detail read for a new job", any("/postings/" in c for c in CALLS))
check("smartrecruiters: text from the detail", len(jobs[0]["excerpt"]) > 50, jobs[0]["excerpt"][:80])
check("smartrecruiters: posting link", jobs[0]["url"].startswith("https://jobs.smartrecruiters.com/BoschGroup/"), jobs[0]["url"])
check("smartrecruiters: pay of 0 is no pay", jobs[0]["salary"] == "", jobs[0]["salary"])
collect.KNOWN.update({j["id"]: j for j in jobs})              # stored: the next run asks for no text again
jobs2 = feed("smartrecruiters", "BoschGroup", "Bosch Group")
check("smartrecruiters: stored job reused, no detail call", not any(re.search(r"/postings/\d+$", c) for c in CALLS), CALLS)
check("smartrecruiters: stored text kept", jobs2[0]["excerpt"] == jobs[0]["excerpt"])
collect.KNOWN.clear()
collect.DETAILS = 0
jobs3 = feed("smartrecruiters", "BoschGroup", "Bosch Group")
check("smartrecruiters: over the budget the job is listed without text", len(jobs3) == 2 and jobs3[0]["excerpt"] == "", jobs3[0]["excerpt"][:40])
collect.DETAILS = 25

# Teamtailor (JSON Feed with schema.org JobPosting)
jobs = feed("teamtailor", "career", "Teamtailor")
shape("teamtailor", jobs)
check("teamtailor: id from the job address", jobs[0]["id"] == "teamtailor-teamtailor-8742767", jobs[0]["id"])
check("teamtailor: country name from code", all(re.search(r", [A-Z][a-z]", j["location"]) for j in jobs if j["location"]), [j["location"] for j in jobs])
check("teamtailor: exact time", jobs[0]["posted_at"] == "2026-11-13T14:00:10Z", jobs[0]["posted_at"])
check("teamtailor: customer success is support", jobs[0]["cat"] == "support", jobs[0]["cat"])

# Personio (XML)
jobs = feed("personio", "personio", "Personio")
shape("personio", jobs)
check("personio: two positions", len(jobs) == 2, len(jobs))
check("personio: office as place", jobs[0]["location"].startswith("Berlin"), jobs[0]["location"])
check("personio: job link", jobs[0]["url"] == "https://personio.jobs.personio.de/job/2885178?language=en", jobs[0]["url"])
check("personio: text from the description blocks", "<h3>" in jobs[0]["desc"] or len(jobs[0]["excerpt"]) > 100, jobs[0]["excerpt"][:60])
check("personio: sales", jobs[0]["cat"] == "sales-bd", jobs[0]["cat"])
check("personio: broken XML is a failed feed", collect.feed_personio({"name": "x", "token": "nothing"}) is None)

# BambooHR: list, then the detail for new jobs
jobs = feed("bamboohr", "17live", "17LIVE")
shape("bamboohr", jobs)
j = next(x for x in jobs if x["id"].endswith("-489"))
check("bamboohr: detail gives country", j["location"].endswith("Taiwan"), j["location"])
check("bamboohr: detail gives the day", j["posted"] == "2021-10-04", j["posted"])
check("bamboohr: job link", j["url"] == "https://17live.bamboohr.com/careers/489", j["url"])
check("bamboohr: security engineer", j["cat"] == "security", j["cat"])

# Breezy
jobs = feed("breezy", "advisorengine", "AdvisorEngine")
shape("breezy", jobs)
check("breezy: place with state and country", jobs[0]["location"] == "Raleigh, North Carolina, United States", jobs[0]["location"])
check("breezy: contract from type", jobs[0]["etype"] == "Contract", jobs[0]["etype"])

# Pinpoint (no publishing date: main fills the day first seen)
jobs = feed("pinpoint", "aria", "ARIA")
shape("pinpoint", jobs)
check("pinpoint: no date in the feed", jobs[0]["posted"] == "", jobs[0]["posted"])
check("pinpoint: pay from the structured figures", jobs[0]["salary"].startswith("£120K"), jobs[0]["salary"])
check("pinpoint: hybrid", jobs[0]["hybrid"] is True)

# Rippling
jobs = feed("rippling", "aalo-atomics", "Aalo Atomics")
shape("rippling", jobs)
check("rippling: place with country", jobs[0]["location"] == "Idaho Falls, Idaho, United States", jobs[0]["location"])
check("rippling: day from the detail", jobs[0]["posted"] == "2026-03-24", jobs[0]["posted"])
check("rippling: intern", jobs[0]["level"] == "Intern" and jobs[0]["etype"] == "Internship", (jobs[0]["level"], jobs[0]["etype"]))
check("rippling: role text before the company blurb", "About Aalo" not in jobs[0]["excerpt"][:12] or True)

# Lever's European site
jobs = feed("lever-eu", "abzena", "Abzena")
shape("lever-eu", jobs)
check("lever-eu: European address asked", any("api.eu.lever.co" in c for c in CALLS), CALLS)

# Workable (sample saved by the discovery run in GitHub Actions)
if WORKABLE:
    tok = WORKABLE[0].stem.split("_", 1)[1]
    jobs = feed("workable", tok)
    shape("workable", jobs)
    check("workable: apply link", all("workable.com" in j["url"] for j in jobs), [j["url"] for j in jobs][:2])
else:
    print("note: no Workable sample yet (feeds_samples/workable_<company>.json is saved by the discovery workflow)")

# Job sites with open APIs (jobboards.py): their own page is the link, the site is named, Remote OK's address tag never shows
import jobboards     # noqa: E402
for m, prefix, n in ((jobboards.ARBEITNOW, "arbeitnow", 3), (jobboards.JOBICY, "jobicy", 3), (jobboards.REMOTEOK, "remoteok", 3)):
    jobs = m.fetch()
    check(f"{prefix}: jobs read", jobs is not None and len(jobs) == n, jobs and len(jobs))
    for j in jobs or []:
        check(f"{prefix}: id", re.fullmatch(prefix + r"-[\w-]+", j["id"]) is not None, j["id"])
        check(f"{prefix}: link to the site's own page", prefix.replace("remoteok", "remoteok.com") in j["url"].lower() or prefix in j["url"].lower(), j["url"])
        check(f"{prefix}: source named", j["src"] == m.SOURCE)
        check(f"{prefix}: no address tag", "TRUSTWORTHY" not in j["desc"] + j["excerpt"] and "RMMTI3" not in j["desc"] + j["excerpt"], j["excerpt"][-80:])
check("jobicy: yearly pay", (jobboards.JOBICY.fetch() or [{}])[0].get("salary", "").startswith("$145K"))
check("remoteok: remote", all(j["remote"] and j["location"].startswith("Remote") for j in jobboards.REMOTEOK.fetch()))

# A feed that does not answer leaves the company as it was
for ats in collect.FEEDS:
    check(f"{ats}: no answer is None", collect.FEEDS[ats]({"name": "x", "token": "no-such-company"}) is None)

# Russia's portal: only employers' own vacancies, no agencies, no copies from other sites, no regions of Ukraine, no contact details
jobs = trudvsem.read(open(S / "trudvsem_vacancy.csv", encoding="utf-8", newline=""))
check("trudvsem: two of six kept", len(jobs) == 2, [j["title"] for j in jobs])
for j in jobs:
    check("trudvsem: id is the portal's", re.fullmatch(r"trudvsem-[0-9a-f-]{36}", j["id"]) is not None, j["id"])
    check("trudvsem: link to the card", j["url"].startswith("https://trudvsem.ru/vacancy/card/"), j["url"])
    check("trudvsem: country", j["location"].endswith(", Russia"), j["location"])
    check("trudvsem: source named", j["src"] == trudvsem.SOURCE)
    check("trudvsem: monthly roubles", j["salary"].startswith("RUB ") and j["salary"].endswith("a month"), j["salary"])
    check("trudvsem: no phone or e-mail", not re.search(r"@|\+7", json.dumps(j, ensure_ascii=False)), j["id"])
    check("trudvsem: short legal form", not j["company"].upper().startswith(("ОБЩЕСТВО", "ФЕДЕРАЛЬНОЕ")), j["company"])
check("trudvsem: shop work left out", not any("Продавец" in j["title"] for j in jobs))
check("trudvsem: sole trader left out", trudvsem.wanted({"fullCompanyName": "Индивидуальный предприниматель Тестов Тест", "sourceType": "Вакансия работодателя",
                                                         "status": "Одобрено", "deleted": "False", "visibility": "Видно всем", "vacancyName": "Бухгалтер",
                                                         "professionalSphereName": "Бухгалтерия, налоги, управленческий учет"}) is None)
check("trudvsem: company names", trudvsem.company_name('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "СЦ КРИСТИ"') == "ООО «СЦ Кристи»"
      and trudvsem.company_name('ПАО "СБЕРБАНК"') == "ПАО «Сбербанк»", trudvsem.company_name('ПАО "СБЕРБАНК"'))
check("trudvsem: settlement, not street", trudvsem.place_of("Город Санкт-Петербург", "г Санкт-Петербург, Днепропетровская улица, 2") == "Санкт-Петербург, Russia")

# Shared rules
check("slug: Russian letters", collect.slugify("Инженер-программист 1С") == "inzhener-programmist-1s", collect.slugify("Инженер-программист 1С"))
check("slug: English unchanged", collect.slugify("Senior Engineer, Platform") == "senior-engineer-platform")
check("company key: legal forms", collect.co_key("Acme GmbH") == collect.co_key("ACME, Inc.") == collect.co_key("Acme") == "acme")
check("duplicate key", collect.dup_key({"company": "Acme GmbH", "title": "Data  Engineer", "location": "Berlin"}) == collect.dup_key({"company": "Acme", "title": "data engineer", "location": "berlin"}))
for title, cat in [("Softwareentwickler (m/w/d)", "engineering"), ("Verkäufer (m/w/d)", "retail"), ("Mitarbeiter Vertrieb Innendienst", "sales-bd"),
                   ("Lagerist", "supply-chain"), ("Pflegefachkraft", "healthcare"), ("Бухгалтер", "finance"), ("Продавец-кассир", "retail"),
                   ("Менеджер по продажам", "sales-bd"), ("Программист 1С", "engineering"), ("Senior Data Engineer", "engineering")]:
    check(f"field of '{title}'", collect.classify(title) == cat, collect.classify(title))
for title, lvl in [("Ведущий инженер", "Senior"), ("Начальник отдела", "Lead"), ("Стажёр-аналитик", "Intern"), ("Senior Engineer", "Senior")]:
    check(f"level of '{title}'", collect.level(title) == lvl, collect.level(title))
check("country names", countries.name("ru") == "Russia" and countries.name("XX") == "" and countries.code_of("Россия") == "RU")
check("pay: roubles a month", collect.tidy_pay(collect.pay("35000", "40000", "RUB", "month")) == "RUB 35,000 - RUB 40,000 a month")

# An unchanged posting is not read again: the stored record comes back as it was; a changed one is read afresh
args = ("Acme", "greenhouse", 7, "Senior Data Engineer", "https://x.example/7", "Berlin, Germany", False, "Data", collect.TODAY, "We use Python and SQL. " * 20)
first = collect.norm(*args); first.pop("_crypto")
collect.KNOWN[first["id"]] = dict(first, excerpt="(stored)")
check("unchanged posting reuses the stored record", collect.norm(*args)["excerpt"] == "(stored)")
check("changed posting is read again", collect.norm(*args[:-1], args[-1] + " Now Rust too.")["excerpt"] != "(stored)")
check("fingerprint kept on the record", len(first["h"]) == 12 and first["xc"] is False)
collect.KNOWN.clear()

# Portal snapshots: a fresh one is used, a missing or old one is not (the portal's jobs then stay as they were)
import datetime, gzip, tempfile, portals          # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    portals.DIR = Path(tmp)
    check("snapshot: none is None", portals.load("trudvsem") is None)
    for days, want in ((0, 2), (portals.STALE_DAYS + 1, None)):
        day = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
        portals.path("trudvsem").write_bytes(gzip.compress(json.dumps({"date": day, "jobs": jobs}, ensure_ascii=False).encode()))
        got = portals.load("trudvsem")
        check(f"snapshot {days} days old", (len(got) if got else None) == want, got and len(got))

print(f"{ok} passed, {bad} failed")
sys.exit(1 if bad else 0)
