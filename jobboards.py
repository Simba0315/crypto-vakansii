"""Jobs from job sites whose public APIs allow showing their jobs on another job board (terms read 15 Nov 2026, ROADMAP 112).

  Arbeitnow  https://www.arbeitnow.com/api/job-board-api   terms §11: "You also agree to providing a link back to Arbeitnow.com on your platform."
  Jobicy     https://jobicy.com/api/v2/remote-jobs          "Clearly credit Jobicy as the original source"; keep the apply link on Jobicy;
                                                            no more than one pass an hour (we read once a day)
  Remote OK  https://remoteok.com/api                       "link back (with follow, and without nofollow!) to the URL on Remote OK and
                                                            mention Remote OK as a source"; no logo

Each job keeps the link to its page on that site (the apply button goes there), and the job page names the site with a followed
link (build.py, BOARD_SOURCE). These sites are not the employer: when the same opening is on the employer's own board, that record
is shown and this one is listed as "Also listed on" (dedupe.py). Read once a day by portals.py; only English postings are shown.
Not used: Remotive (16 jobs on 15 Nov; no feeds or Google Jobs), Himalayas (a free key is needed for volume; no markup or feeds),
The Muse (behind a Cloudflare check), Hacker News comments (Y Combinator's terms do not allow republishing them; discover_ats.py
only takes the employers' own job board addresses from them).
"""
import datetime, re
from types import SimpleNamespace


def _collect():
    import collect
    return collect


def _job(prefix, src, jid, company, title, url, location, remote, dept, posted, desc, salary="", hint="", posted_at=None):
    c = _collect()
    if not jid or not title or not company or not str(url or "").startswith("https://"): return None
    j = c.norm(str(company).strip(), prefix, jid, title, url, location, remote, dept, posted, c.strip_html(desc), salary, hint, desc, posted_at=posted_at)
    j["id"] = f"{prefix}-{jid}"          # the site's own number: stable if the company's name is written differently
    j["src"] = src
    return j


def arbeitnow():
    c, out = _collect(), []
    for page in range(1, 31):                                        # 300 a page; about 10 pages on 15 Nov
        d = c.get_json(f"https://www.arbeitnow.com/api/job-board-api?page={page}", 60)
        if not isinstance(d, dict) or not isinstance(d.get("data"), list): return None if page == 1 else out
        for x in d["data"]:
            when = datetime.datetime.fromtimestamp(int(x.get("created_at") or 0), datetime.timezone.utc) if str(x.get("created_at") or "").isdigit() else None
            j = _job("arbeitnow", ARBEITNOW.SOURCE, x.get("slug"), x.get("company_name"), x.get("title"), x.get("url"),
                     re.sub(r"^hub\s*-\s*", "", str(x.get("location") or ""), flags=re.I), bool(x.get("remote")), ", ".join(x.get("tags") or [])[:80],
                     when.date().isoformat() if when else "", x.get("description") or "", "", ", ".join(x.get("job_types") or []), when.isoformat() if when else None)
            if j: out.append(j)
        if not (d.get("links") or {}).get("next"): break
    return out


def jobicy():
    c, out, cursor = _collect(), [], ""
    for _ in range(30):                                              # 100 a page; the API holds the last 7 days
        d = c.get_json("https://jobicy.com/api/v2/remote-jobs?count=100" + (f"&cursor={cursor}" if cursor else ""), 60)
        if not isinstance(d, dict) or not isinstance(d.get("jobs"), list): return None if not out else out
        for x in d["jobs"]:
            geo = str(x.get("jobGeo") or "").strip()
            pay = c.pay(x.get("salaryMin"), x.get("salaryMax"), x.get("salaryCurrency"), "" if str(x.get("salaryPeriod") or "").lower() in ("yearly", "annual", "year") else x.get("salaryPeriod"))
            j = _job("jobicy", JOBICY.SOURCE, x.get("id"), x.get("companyName"), x.get("jobTitle"), x.get("url"),
                     "Remote" + (f", {geo}" if geo and geo.lower() not in ("anywhere", "worldwide") else (" (anywhere)" if geo else "")), True,
                     ", ".join(x.get("jobIndustry") or [])[:80], str(x.get("pubDate") or "")[:10], x.get("jobDescription") or "", pay,
                     ", ".join(x.get("jobType") or []), x.get("pubDate"))
            if j: out.append(j)
        cursor = d.get("nextCursor") or ""
        if not d.get("hasMore") or not cursor: break
    return out


# Remote OK writes into each description a line that asks applicants to "mention the word TRUSTWORTHY and tag RM…": the tag is the
# address of the machine that asked the API. It must never reach our pages, so every sentence with it goes.
TAG_LINE = re.compile(r"[^.<>]*(TRUSTWORTHY|tag RM[A-Za-z0-9+/=]+|\bRM[A-Za-z0-9+/]{12,}={0,2})[^.<>]*\.?", re.I)


def remoteok():
    c = _collect()
    d = c.get_json("https://remoteok.com/api", 60)
    if not isinstance(d, list) or len(d) < 2: return None
    out = []
    for x in d[1:]:
        if not isinstance(x, dict): continue
        desc = TAG_LINE.sub("", x.get("description") or "")
        lo, hi = x.get("salary_min") or 0, x.get("salary_max") or 0
        loc = str(x.get("location") or "").strip()
        j = _job("remoteok", REMOTEOK.SOURCE, x.get("id"), x.get("company"), x.get("position"), (x.get("url") or "").replace("https://remoteOK.com", "https://remoteok.com"),
                 "Remote" + (f", {loc}" if loc and loc.lower() not in ("remote", "worldwide", "anywhere") else ""), True, ", ".join(x.get("tags") or [])[:80],
                 str(x.get("date") or "")[:10], desc, c.pay(lo, hi, "USD") if lo and hi else "", "", x.get("date"))
        if j: out.append(j)
    return out


ARBEITNOW = SimpleNamespace(SOURCE="Arbeitnow", fetch=arbeitnow)
JOBICY = SimpleNamespace(SOURCE="Jobicy", fetch=jobicy)
REMOTEOK = SimpleNamespace(SOURCE="Remote OK", fetch=remoteok)
