"""Find company job boards on the hiring systems small and mid-size companies use, and write the good ones to sources_ats.json.

    python3 discover_ats.py                 # every system; reads 3 Common Crawl snapshots
    python3 discover_ats.py workable personio --crawls 2

1. Addresses. Common Crawl (a public archive of the web) publishes an index of every address it saw. Its search server is often
   overloaded, so this reads the index files themselves: cluster.idx says which compressed block holds which addresses, and only the
   blocks for the hiring systems' domains are downloaded (a few MB each). Every company board has its own address there:
   apply.workable.com/<company>, <company>.recruitee.com, <company>.jobs.personio.de, ...
2. Each company not read yet is asked for its jobs through the same public feed collect.py reads every hour (collect.FEEDS).
3. The same rules as sources_more.json: no staffing or recruitment agencies; no board where most jobs are shop, warehouse or clinic
   work; at least one open job. Boards of companies already read from another system are skipped by name.

The result keeps the boards of an earlier run whose system could not be asked this time (a rate limit, a network failure), so one bad
run does not drop them. A summary by system and by country goes to stdout and to data/discover_ats.json.
GitHub Actions runs this file when it changes (.github/workflows/discover.yml) and commits sources_ats.json.
"""
import argparse, bisect, concurrent.futures as cf, json, os, re, subprocess, sys, time, urllib.parse, zlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
os.environ["HRN_DETAILS"] = "0"            # a board is judged from its list of jobs; the text of each job is read later by collect.py
import collect                             # noqa: E402  (after HRN_DETAILS)
# A board is judged on its titles, fields and the start of each text: the skill and perk patterns (most of the 20 ms a posting costs)
# are not needed here, so they are switched off in this script only.
collect.SKILLS, collect.PERKS = [], []
from net import get_json                   # noqa: E402

CC = "https://data.commoncrawl.org/cc-index/collections"
# system -> (index key prefixes, how the company's token is read from an address, words that are not companies)
SYSTEMS = {
    "workable": (["com,workable,apply)/"], r"apply\.workable\.com/([a-z0-9][a-z0-9-]*)", {"j", "api", "careers", "static", "embed", "widget", "assets"}),
    "recruitee": (["com,recruitee,"], r"//([a-z0-9][a-z0-9-]*)\.recruitee\.com", {"www", "api", "app", "docs", "blog", "careers", "support", "status", "help", "partners", "jobs", "cdn"}),
    "smartrecruiters": (["com,smartrecruiters,jobs)/", "com,smartrecruiters,careers)/"], r"(?:jobs|careers)\.smartrecruiters\.com/([A-Za-z0-9][A-Za-z0-9-]*)",
                        {"sr-jobs", "oneclick-ui", "api", "static", "ni", "sr-company-review", "en", "sitemap", "robots"}),
    "teamtailor": (["com,teamtailor,"], r"//([a-z0-9][a-z0-9-]*)\.teamtailor\.com", {"www", "app", "api", "support", "docs", "status", "partner", "partners", "marketplace", "assets", "blog", "community", "go"}),
    "personio": (["de,personio,jobs,", "com,personio,jobs,"], r"//([a-z0-9][a-z0-9-]*)\.jobs\.personio\.(?:de|com)", {"www", "api", "app"}),
    "bamboohr": (["com,bamboohr,"], r"//([a-z0-9][a-z0-9-]*)\.bamboohr\.com", {"www", "app", "api", "help", "marketplace", "partners", "status", "documentation", "go", "resources", "info", "blog", "community"}),
    "breezy": (["hr,breezy,"], r"//([a-z0-9][a-z0-9-]*)\.breezy\.hr", {"www", "app", "api", "help", "developer", "marketplace", "assets", "blog"}),
    "pinpoint": (["com,pinpointhq,"], r"//([a-z0-9][a-z0-9-]*)\.pinpointhq\.com", {"www", "app", "help", "developers", "status", "api", "support"}),
    "rippling": (["com,rippling,ats)/"], r"ats\.rippling\.com/([a-z0-9][a-z0-9-]*)", {"api", "static", "en-gb", "en-us", "_next"}),
    "lever-eu": (["co,lever,eu,jobs)/"], r"jobs\.eu\.lever\.co/([a-z0-9][a-z0-9.-]*)", {"api", "static"}),
    # Greenhouse, Lever and Ashby boards that are not in our lists yet: the fetchers exist, only the addresses were missing
    "greenhouse": (["io,greenhouse,boards)/", "io,greenhouse,job-boards)/", "io,greenhouse,eu,boards)/", "io,greenhouse,eu,job-boards)/"],
                   r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9][a-z0-9]*)", {"embed", "api", "v1", "assets", "static"}),
    "lever": (["co,lever,jobs)/"], r"//jobs\.lever\.co/([a-z0-9][a-z0-9.-]*)", {"api", "static"}),
    "ashby": (["com,ashbyhq,jobs)/"], r"jobs\.ashbyhq\.com/([^/?#\s\"]+)", {"api", "static", "favicon.ico", "robots.txt", "_next"}),
    # large employers: the host gives tenant/wdN; the public career sites are then read from each host's robots.txt (workday_sites)
    "workday": (["com,myworkdayjobs,"], r"//([a-z0-9-]+\.wd\d+)\.myworkdayjobs\.com", {"www"}),
}
AGENCY_NAME = re.compile(r"staffing|recruit|personnel|personal(service|dienst|vermittlung|beratung)|zeitarbeit|arbeitnehmerüberlassung|headhunt|executive search|"
                         r"talent (solutions|partners|acquisition)|placement|uitzend|detacher|bemanning|rekryter|interim|manpower|employment (agency|services)|"
                         r"\bhr services|jobs? agency|search partners|resourcing|outsourcing|reclutamiento|selección de personal|rekrutacj|agenzia per il lavoro|"
                         r"кадров(ое|ое агентство)|hiring solutions|career partners|\btalent$|uitzend|werving|detachering|freelancers?\b|\bflex(work|workers)?\b|"
                         r"workforce solutions|labou?r hire|temp(orary)? (staff|work)|upwork|statistician network|\bsandbox\b|virtual assistant|"
                         r"wing assistant|coupang internal", re.I)
AGENCY_TEXT = re.compile(r"\bour client\b|on behalf of (our|a) client|unser(em|en)? kunde|für unseren kunden|notre client|nuestro cliente|onze opdrachtgever|"
                         r"vår kund|naszego klienta|nasz klient|il nostro cliente|nosso cliente|для нашего клиента|наш клиент|namens onze klant|voor onze klant|"
                         r"im auftrag (unseres|eines) kunden|pour le compte de (notre|nos) client", re.I)
# "All professions" (15 Nov 2026, ROADMAP 113). Wave 1, read like any board: office, professional and remote work, healthcare and
# education included (clinics, hospitals, schools, universities, banks, public bodies). Wave 2, frontline work (shops, warehouses and
# driving, plants and trades): a board that is mostly that is kept, marked "frontline" and read once a day (collect.py) until the
# rotation has room. Before 15 Nov such boards, and clinics, were left out.
BLUE = {"retail", "supply-chain", "manufacturing"}       # frontline work (wave 2)
OFFICE = {"engineering", "product", "design", "sales-bd", "marketing", "support", "compliance-legal", "finance", "people", "data-research",
          "operations", "security", "consulting", "education", "healthcare", "nursing", "administrative"}
MAX_JOBS = 1000         # a board this large is a chain or a big enterprise: the goal here is small and mid-size companies
STAFFING_TEXT = re.compile(r"\bc2c\b|corp[- ]to[- ]corp|\bw-?2 (only|contract|candidates)|h-?1b|\bopt\b|\bcpt\b|\bead\b|contract[- ]to[- ]hire|"
                           r"\b(for|with) (one of )?our (fortune|direct )?clients?\b|immediate (joiner|requirement)|bench sales", re.I)


def cc_crawls(n):
    got = get_json("https://index.commoncrawl.org/collinfo.json", 60)
    if isinstance(got, list) and got: return [c["id"] for c in got[:n]]
    # the index server is down more often than the files: guess the newest names from the files' own listing
    return [f"CC-MAIN-2026-{w}" for w in ("43", "39", "34", "30", "25", "21")][:n]


def cc_addresses(crawl, prefixes, tmp):
    """Every address under the given index key prefixes in one crawl: {prefix: set of URLs}."""
    idx = tmp / f"{crawl}.cluster.idx"
    if not idx.exists() or idx.stat().st_size < 10_000_000:
        subprocess.run(["curl", "-s", "--fail", "--retry", "3", "--max-time", "600", "-o", str(idx), f"{CC}/{crawl}/indexes/cluster.idx"], check=False)
    if not idx.exists(): print(f"{crawl}: no index"); return {}
    lines = idx.read_text(encoding="utf-8", errors="replace").splitlines()
    keys = [l.split(" ", 1)[0] for l in lines]
    out = {}
    for p in prefixes:
        i, urls = max(0, bisect.bisect_left(keys, p) - 1), set()
        while i < len(lines) and (keys[i] <= p or keys[i].startswith(p)):
            f = lines[i].split("\t")
            off, ln = int(f[2]), int(f[3])
            raw = subprocess.run(["curl", "-s", "--fail", "--retry", "3", "--max-time", "120", "-r", f"{off}-{off + ln - 1}", f"{CC}/{crawl}/indexes/{f[1]}"],
                                 capture_output=True).stdout
            try:
                for l in zlib.decompress(raw, 16 + zlib.MAX_WBITS).decode("utf-8", "replace").splitlines():
                    if l.startswith(p):
                        try: urls.add(json.loads(l.split(" ", 2)[2])["url"])
                        except (ValueError, KeyError, IndexError): pass
            except zlib.error:
                print(f"{crawl}: a block of {p} could not be read")
            i += 1
        out[p] = urls
        print(f"{crawl} {p}: {len(urls)} addresses")
    return out


def hn_addresses(months=3):
    """Links in the last few monthly "Ask HN: Who is hiring?" threads (official Algolia HN API). Only the addresses of employers' own
    job boards are taken from them; the comments themselves are never shown (Y Combinator's terms do not allow republishing them)."""
    import html as h
    stories = get_json("https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=20", 30)
    ids = [x["objectID"] for x in (stories or {}).get("hits", []) if "who is hiring" in (x.get("title") or "").lower()][:months]
    urls = set()
    for sid in ids:
        for page in range(10):
            d = get_json(f"https://hn.algolia.com/api/v1/search?tags=comment,story_{sid}&hitsPerPage=500&page={page}", 30)
            if not isinstance(d, dict): break
            for x in d.get("hits", []):
                urls |= set(re.findall(r"https?://[^\s\"'<>]+", h.unescape(x.get("comment_text") or "")))
            if page + 1 >= d.get("nbPages", 0): break
    print(f"Hacker News: {len(urls)} links in {len(ids)} threads")
    return urls


def tokens(system, urls):
    _, rx, skip = SYSTEMS[system]
    out = set()
    for u in urls:
        m = re.search(rx, u)
        if not m: continue
        t = urllib.parse.unquote(m.group(1)).strip()
        if system not in ("smartrecruiters", "ashby"): t = t.lower()
        if t.lower() in skip or len(t) < 2 or t.lower().endswith((".js", ".css", ".png", ".txt", ".xml")): continue
        if not re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?", t): continue      # goes into a web address as it is (no "-" at either end)
        out.add(t)
    return out


def workday_sites(host_tokens):
    """tenant.wdN hosts -> tokens tenant/wdN/site for each public career site its robots.txt allows ("Allow: /External/")."""
    def sites(ht):
        tenant, wd = ht.split(".", 1)
        try:
            txt = subprocess.run(["curl", "-s", "--max-time", "20", "-A", "Mozilla/5.0 (job-board aggregator)", f"https://{tenant}.{wd}.myworkdayjobs.com/robots.txt"],
                                 capture_output=True, timeout=25).stdout.decode("utf-8", "replace")
        except Exception:
            return []
        out = []
        for m in re.finditer(r"(?im)^allow:\s*/([A-Za-z0-9_.-]+)/\s*$", txt):
            site = m.group(1)
            if site.lower() in ("refreshfacet", "private", "wday") or re.fullmatch(r"[a-z]{2}-[A-Z]{2}", site): continue
            out.append(f"{tenant}/{wd}/{site}")
        return out
    with cf.ThreadPoolExecutor(16) as ex:
        return {t for ts in ex.map(sites, sorted(host_tokens)) for t in ts}


def probe_workday(token):
    """One page of a Workday site: (sample of up to 20 jobs, total, the employer's name), or (None, 0, None)."""
    from net import post_json
    tenant, wd, site = token.split("/", 2)
    host = f"https://{tenant}.{wd}.myworkdayjobs.com"
    d = post_json(f"{host}/wday/cxs/{tenant}/{site}/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}, 45)
    if not isinstance(d, dict) or not isinstance(d.get("jobPostings"), list): return None, 0, None
    jobs = [collect.norm(tenant, "workday", p.get("externalPath") or p.get("title"), p.get("title"), host, p.get("locationsText") or "", False, "", "", "")
            for p in d["jobPostings"] if p.get("title")]
    name = None
    if jobs and d["jobPostings"][0].get("externalPath"):
        det = get_json(f"{host}/wday/cxs/{tenant}/{site}{d['jobPostings'][0]['externalPath']}", 30)
        name = workday_name((((det or {}).get("hiringOrganization") or {}).get("name") or "") if isinstance(det, dict) else "")
    return jobs, int(d.get("total") or 0), name or (tenant.upper() if len(tenant) <= 4 else tenant.replace("-", " ").title())


def workday_name(legal):
    """Workday gives the legal entity of the job's country ("APTIV INDIA PRIVATE LIMITED", "USA 3M Company", "0200 Ares Operations LLC"):
    the company's name is what is left without codes, country words and legal forms ("Aptiv", "3M", "Ares Operations")."""
    import countries
    words = re.sub(r"[,.]", " ", str(legal or "")).split()
    lands = {n.lower() for n in countries.NAMES.values()} | {"usa", "us", "uk", "u s", "america", "india", "emea", "apac", "global"}
    legal_w = {"private", "pvt", "limited", "ltd", "llc", "inc", "corp", "corporation", "company", "co", "gmbh", "ag", "sa", "bv", "nv", "plc", "llp", "lp",
               "pte", "pty", "srl", "sas", "kk", "sdn", "bhd", "holdings", "the"}
    kept = [w for i, w in enumerate(words) if not (re.fullmatch(r"\d+", w) and i == 0) and w.lower() not in legal_w and w.lower() not in lands]
    name = " ".join(kept).strip()
    if name.upper() == name and len(name) > 4: name = " ".join(w if len(w) <= 3 else w.title() for w in name.split())
    return workday_tidy(name)


def workday_tidy(name):
    """Entity codes in front ("UK10 AstraZeneca", "6040-Ethicon", "*US AMR-Jones Lang LaSalle", "95-2566122 First American"), brackets
    ("Wawa (210515330)", "UPS (Ohio)") and tails ("_United States", "Legal Entity", "Employment", "S de R L de C V") taken off."""
    n = re.sub(r"\s*\([^)]*\)\s*", " ", str(name or "")).strip()
    n = re.sub(r"_[A-Za-z ]+$", "", n)
    n = re.sub(r"\s+(legal entity|employment|s ?a ?u|s de r ?l de c ?v|opco|of cos|n ?a)$", "", n, flags=re.I)
    for _ in range(3):
        m = re.match(r"^\*?\s*([A-Z0-9]{1,8}[-\s]+)(?=\S)", n)
        if not m: break
        code = m.group(1).strip(" -")
        rest = n[m.end():].strip()
        # a code with a digit, a "*" or a "-" goes; a short letter code only when it abbreviates the name after it ("KDS Kohl's", "COV Covidien")
        lettered = code.isalpha() and code.isupper() and len(code) <= 4 and rest[:1].upper() == code[:1] and m.group(1).strip() == code and len(rest.split()) >= 1
        if (re.search(r"\d", code) or "-" in m.group(1) or n.startswith("*") or lettered) and not re.fullmatch(r"[A-Z0-9]{1,4}", rest):
            n = rest
        else:
            break
    return re.sub(r"\s+", " ", n).strip(" -_*") or str(name or "")


def shown_name(system, token, jobs, feed):
    """The company's name as its own feed writes it, else the token made readable ("acme-labs" -> "Acme Labs")."""
    if isinstance(feed, dict):
        for k in ("name", "company_name"):
            if isinstance(feed.get(k), str) and feed[k].strip(): return feed[k].strip()
    return re.sub(r"[-_.]+", " ", token).strip().title() if token.lower() == token else token


PAGE = {"bamboohr": "https://{t}.bamboohr.com/careers", "personio": "https://{t}.jobs.personio.de/", "pinpoint": "https://{t}.pinpointhq.com/",
        "rippling": "https://ats.rippling.com/{t}/jobs", "lever-eu": "https://jobs.eu.lever.co/{t}", "lever": "https://jobs.lever.co/{t}",
        "ashby": "https://jobs.ashbyhq.com/{t}"}


def page_name(system, token):
    """The company's name from its own careers page (og:site_name, og:title or the title), for feeds that do not carry it:
    "Careers at ARIA" -> "ARIA". '' when the page names only the hiring system."""
    if system not in PAGE: return ""
    try:
        s = subprocess.run(["curl", "-s", "-L", "--max-time", "20", "-A", "Mozilla/5.0 (job-board aggregator)", PAGE[system].format(t=token)],
                           capture_output=True, timeout=25).stdout.decode("utf-8", "replace")
    except Exception:
        return ""
    import html as h
    for rx in (r'property="og:site_name"\s+content="([^"]+)"', r'property="og:title"\s+content="([^"]+)"', r"<title[^>]*>(.*?)</title>"):
        m = re.search(rx, s, re.S | re.I)
        if not m: continue
        n = h.unescape(m.group(1)).strip()
        n = re.sub(r"^(jobs|careers|career|vacancies|open positions|current openings|work) (at|with|bei|chez) ", "", n, flags=re.I)
        n = re.split(r"\s+[|–—-]\s+", n)[0]
        n = re.sub(r"\s+(careers|jobs|career site|job board|vacatures|karriere|stellenangebote)$", "", n, flags=re.I).strip()
        if n and not re.fullmatch(r"bamboohr|personio|pinpoint|rippling|lever|ashby|page not found|not found|jobs|careers|home|error.*", n, re.I) and len(n) <= 80:
            return n
    return ""


def probe(system, token):
    """(jobs, name) for one board, or (None, None) when the feed did not answer."""
    src = {"name": token, "ats": system, "token": token}
    try:
        name, jobs = collect.fetch_feed(src)
    except Exception:
        return None, None
    if jobs is None: return None, None
    feed_name = None
    if jobs:      # the feed's own company name, where it has one
        if system == "workable":
            d = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{token}", 30)
            feed_name = (d or {}).get("name") if isinstance(d, dict) else None
        elif system == "recruitee":
            d = get_json(f"https://{token}.recruitee.com/api/offers/", 30)
            feed_name = ((d or {}).get("offers") or [{}])[0].get("company_name") if isinstance(d, dict) else None
        elif system == "smartrecruiters":
            d = get_json(f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=1", 30)
            feed_name = (((d or {}).get("content") or [{}])[0].get("company") or {}).get("name") if isinstance(d, dict) else None
        elif system == "teamtailor":
            d = get_json(f"https://{token}.teamtailor.com/jobs.json", 30)
            it = ((d or {}).get("items") or [{}])[0] if isinstance(d, dict) else {}
            feed_name = ((it.get("_jobposting") or {}).get("hiringOrganization") or {}).get("name")
        elif system == "breezy":
            d = get_json(f"https://{token}.breezy.hr/json", 30)
            feed_name = ((d or [{}])[0].get("company") or {}).get("name") if isinstance(d, list) and d else None
        elif system == "rippling" and jobs:
            jid = jobs[0]["id"].rsplit("-", 5)[-5:]
            d = get_json(f"https://ats.rippling.com/api/v2/board/{token}/jobs/{'-'.join(jid)}", 30)
            feed_name = ((d or {}).get("board") or {}).get("companyName") if isinstance(d, dict) else None
        elif system == "greenhouse":
            d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}", 30)
            feed_name = (d or {}).get("name") if isinstance(d, dict) else None
    if jobs and not (feed_name or "").strip(): feed_name = page_name(system, token)
    return jobs, (feed_name or "").strip() or shown_name(system, token, jobs, None)


def judge(name, jobs, large=False):
    """Why a board is left out, or '' when it is kept. The rules of sources_more.json (14 Nov 2026), made stricter on 15 Nov after the
    first run let in chains whose titles are not in English (Domino's, Accor, JYSK) and IT staffing firms."""
    n = len(jobs)
    if not n: return "no open jobs"
    if n > MAX_JOBS and not large: return f"over {MAX_JOBS} jobs (a chain or a big enterprise)"
    if AGENCY_NAME.search(name): return "agency (name)"
    if sum(bool(AGENCY_TEXT.search(j["title"] + " " + j["excerpt"])) for j in jobs) >= max(2, 0.3 * n): return "agency (postings)"
    if sum(bool(STAFFING_TEXT.search(j["title"] + " " + j["excerpt"])) for j in jobs) >= max(2, 0.3 * n): return "agency (staffing terms)"
    if sum(collect.english(j) for j in jobs) < n / 2: return "mostly not in English"        # the site is in English (owner, 15 Nov)
    if n >= 60 and not large and len({re.sub(r"\W+", " ", j["title"].lower()).strip() for j in jobs}) < 0.25 * n: return "the same few titles repeated (mass hiring)"
    return ""


def frontline(jobs):
    """Wave 2: most of the board is frontline work, or under 40% is wave-1 work."""
    n = len(jobs) or 1
    return sum(j["cat"] in BLUE for j in jobs) > n / 2 or sum(j["cat"] in OFFICE for j in jobs) < 0.4 * n


def by_country(jobs):
    """Open jobs of a board by country (the first country each location names; jobs that name none are not counted)."""
    import build
    return Counter(code for j in jobs for code, _ in build.countries_of(j["location"] or "")[:1])


def lands(jobs):
    return [k for k, _ in by_country(jobs).most_common(3)]


def examine(st):
    """Ask one board and judge it, in a worker process: (system, token, name, number of jobs, jobs by country, reason left out or '')."""
    s, t = st
    if s == "workday":                 # large employers: judged on the first page of 20, sized by the total the site reports
        jobs, total, name = probe_workday(t)
        if jobs is None: return s, t, None, 0, {}, "no answer", False
        if total >= collect.WD_MAX: return s, t, name, total, {}, f"{collect.WD_MAX} jobs or more (Workday lists no more)", False
        if total > MAX_JOBS: return s, t, name, total, {}, f"over {MAX_JOBS} jobs (a chain or a big enterprise)", False
        return s, t, name, total, {k: round(v * total / max(1, len(jobs))) for k, v in by_country(jobs).items()}, judge(name, jobs, large=True), frontline(jobs)
    jobs, name = probe(s, t)
    if jobs is None: return s, t, None, 0, {}, "no answer", False
    return s, t, name, len(jobs), dict(by_country(jobs)), judge(name, jobs), frontline(jobs)


def save_samples(boards):
    """A trimmed real response for feeds_test.py, for a system whose sample could not be saved from the cloud machine (Workable)."""
    d = ROOT / "feeds_samples"
    if any(d.glob("workable_*.json")): return
    for b in boards:
        if b["ats"] != "workable" or b["count"] < 2: continue
        raw = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{b['token']}?details=true", 60)
        if not isinstance(raw, dict) or len(raw.get("jobs") or []) < 2: continue
        raw["jobs"] = raw["jobs"][:2]
        for j in raw["jobs"]: j["description"] = (j.get("description") or "")[:3000]
        (d / f"workable_{b['token']}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1))
        print("saved a Workable sample:", b["token"]); return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("systems", nargs="*", default=list(SYSTEMS))
    ap.add_argument("--crawls", type=int, default=3)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--max", type=int, default=0, help="at most this many new tokens per system (0: all)")
    ap.add_argument("--samples", action="store_true", help="save a real response of a system that has no test sample yet (feeds_samples/)")
    ap.add_argument("--recheck", action="store_true", help="judge again the boards already in sources_ats.json (no Common Crawl)")
    ap.add_argument("--new-only", action="store_true", help="ask only boards not in sources_ats.json yet and add the good ones (the daily run)")
    a = ap.parse_args()
    tmp = ROOT / "data" / "cc"
    tmp.mkdir(parents=True, exist_ok=True)
    # what we read already, by system and token and by company name
    have, names = set(), set()
    for f in ("sources.json", "sources_tech.json", "sources_more.json", "sources_candidates.json"):   # candidates: judged on 14 Nov, left out or taken
        for s in (json.loads((ROOT / f).read_text()) if (ROOT / f).exists() else []):
            have.add((s["ats"], s["token"].lower())); names.add(collect.co_key(s["name"]))
    prev = json.loads((ROOT / "sources_ats.json").read_text()) if (ROOT / "sources_ats.json").exists() else []
    t0 = time.time()
    found = defaultdict(set)
    for crawl in ([] if a.recheck else cc_crawls(a.crawls)):
        prefixes = [p for s in a.systems for p in SYSTEMS[s][0]]
        got = cc_addresses(crawl, prefixes, tmp)
        for s in a.systems:
            for p in SYSTEMS[s][0]: found[s] |= tokens(s, got.get(p, ()))
    todo = []
    if not a.recheck:            # every day: employers' boards linked from Hacker News hiring threads, on every system we read
        hn = hn_addresses()
        for sys_ in a.systems: found[sys_] |= tokens(sys_, hn)
    if a.recheck:
        for p in prev:
            if p["count"] <= MAX_JOBS: found[p["ats"]].add(p["token"])
        prev = []
    if "workday" in found and found["workday"] and not a.recheck:
        hosts = {t for t in found["workday"] if "/" not in t}
        found["workday"] = (found["workday"] - hosts) | workday_sites(hosts)
        print(f"workday: {len(hosts)} employers, {len(found['workday'])} public career sites")
    if a.new_only:
        have |= {(p["ats"], p["token"].lower()) for p in prev}
        names |= {collect.co_key(p["name"]) for p in prev}
    for s in a.systems:
        new = sorted(t for t in found[s] if (s, t.lower()) not in have)
        if a.max: new = new[:a.max]
        print(f"{s}: {len(found[s])} boards in the crawl, {len(new)} not read yet")
        todo += [(s, t) for t in new]
    kept, why, answered, asked, land_jobs = [], Counter(), Counter(), Counter(), Counter()
    # worker processes, not threads: reading the postings is CPU work (about 20 ms a job), and every core is used
    import multiprocessing
    with cf.ProcessPoolExecutor(a.workers, mp_context=multiprocessing.get_context("fork")) as ex:
        results = list(ex.map(examine, todo, chunksize=8))
        biggest = {}                  # one Workday employer, several public sites ("External", "External-Ada"): its largest one only
        for r in results:
            if r[0] == "workday" and r[5] != "no answer":
                k = r[1].split("/")[0]
                if k not in biggest or r[3] > biggest[k][3]: biggest[k] = r
        for s, t, name, count, countries_n, reason, front in results:
            if s == "workday" and reason != "no answer" and biggest.get(t.split("/")[0], (None, t))[1] != t:
                why[(s, "another public site of the same employer")] += 1; asked[s] += 1; answered[s] += 1; continue
            asked[s] += 1
            if reason == "no answer": why[(s, reason)] += 1; continue
            answered[s] += 1
            if reason: why[(s, reason)] += 1; continue
            k = collect.co_key(name)
            if k in names: why[(s, "company already read elsewhere")] += 1; continue
            names.add(k)
            land_jobs.update(countries_n)
            kept.append({"name": name, "ats": s, "token": t, "count": count, "lands": [c for c, _ in Counter(countries_n).most_common(3)]} | ({"frontline": True} if front else {}))
            if front: why[(s, "kept: mostly frontline work, read once a day (wave 2)")] += 1
    # boards of a system that could not be asked this time stay as they were
    asked_ok = {s for s in a.systems if asked[s] and answered[s] >= 0.2 * asked[s]}
    keep_prev = prev if a.new_only else [p for p in prev if p["ats"] not in asked_ok]
    out_names = {collect.co_key(k["name"]) for k in kept}
    out = kept + [p for p in keep_prev if collect.co_key(p["name"]) not in out_names]
    # one company name, one board: a name used twice gets its system added ("Acme (Personio)"), so collect.py keeps both boards apart
    dup = Counter(o["name"] for o in out)
    for o in out:
        if dup[o["name"]] > 1: o["name"] = f"{o['name']} ({o['ats'].title()})"
    out.sort(key=lambda o: -o["count"])
    (ROOT / "sources_ats.json").write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n")
    by_sys = Counter(o["ats"] for o in out)
    jobs_sys = Counter()
    for o in out: jobs_sys[o["ats"]] += o["count"]
    by_land, jobs_land = Counter(), Counter()
    for o in out:
        if o["lands"]: by_land[o["lands"][0]] += 1; jobs_land[o["lands"][0]] += o["count"]
    summary = {"date": collect.TODAY, "seconds": round(time.time() - t0), "boards": len(out), "jobs": sum(o["count"] for o in out),
               "by_system": {s: [by_sys[s], jobs_sys[s]] for s in sorted(by_sys, key=lambda s: -jobs_sys[s])},
               "by_country": {c: [by_land[c], jobs_land[c]] for c, _ in jobs_land.most_common()},     # boards by their main country: [boards, their jobs]
               "jobs_by_country": dict(land_jobs.most_common()),                                       # every job of the boards found now, by its own country
               "left_out": {f"{s}: {r}": n for (s, r), n in why.most_common()},
               "asked": dict(asked), "answered": dict(answered)}
    (ROOT / "sources_ats_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n")
    if a.samples: save_samples(out)
    print(json.dumps({k: v for k, v in summary.items() if k != "by_country"}, ensure_ascii=False, indent=1))
    print("by country (boards, jobs):", ", ".join(f"{c} {b}/{j}" for c, (b, j) in list(summary["by_country"].items())[:40]))


if __name__ == "__main__":
    main()
