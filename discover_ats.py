"""Find and verify company job boards on Workable, Recruitee, Teamtailor, Personio, Workday, Breezy, BambooHR and Paylocity, and add the ones with English jobs to
sources_ats.json (15 Nov 2026; the owner: "too few jobs, competitors add far more").

    python3 discover_ats.py --cc DIR CRAWL[,CRAWL...]   read Common Crawl's URL index for the systems' addresses into DIR (one file a page;
                                                       HRN_CC_HOSTS=breezy,bamboohr reads only those systems)
    python3 discover_ats.py --cc-files DIR CRAWL[,...]  the same for the systems in CC_SURT, read from the index's files instead of its
                                                       server (for hosts on which the server answers 502 or 504)
    python3 discover_ats.py FILE_OR_DIR [...]          take every board address in these files (URLs, one a line: Common Crawl's index,
                                                       sitemaps, lists), verify the boards and add the good ones to sources_ats.json
                                                       (HRN_DISCOVER_LOG=FILE keeps what was checked, so a second run skips it)
    python3 discover_ats.py --names                    name the Workday and Personio boards in sources_ats.json again, drop duplicates
    python3 discover_ats.py --from-log LOG              the boards a run still going has kept so far (its HRN_DISCOVER_LOG) into the file

A board is kept when its feed answers through collect.fetch_feed (the same code the hourly run uses), has 3 or more open jobs in
English, either 15 or more of them or at least 60% of all its jobs (collect.english: collect.py leaves the others out, cheaply, as
the language is checked before a posting is parsed), and is not a company we already read under another system or name
(dedupe.company_key), nor a recruitment agency (AGENCY_RX). On Workday, where every posting's text is a request of its own, 2 of
the first 3 postings must be in English, and the tenant's robots.txt must let crawlers read the careers site's data.
SmartRecruiters is left out on purpose: the robots.txt of its API allows only LinkedIn's crawler, so its boards wait for consent.
A board marked "hold": true in sources_ats.json is verified but not read yet (collect.py, live.py): see ATS_REPORT.md.

Polite: the gaps between requests and the boards read at once per system come from collect.ATS_GAP and collect.ATS_LIMIT, with the
user agent of net.py. Common Crawl's index is asked one page at a time, 2 seconds apart.
"""
import collections, concurrent.futures as cf, datetime, html, json, os, re, subprocess, sys, threading, time, urllib.parse, urllib.robotparser, zlib
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import collect, dedupe, net          # noqa: E402

OUT = Path(os.environ.get("HRN_DISCOVER_OUT") or ROOT / "sources_ats.json")       # HRN_DISCOVER_OUT=sources_breezy.json: another file
TODAY = datetime.date.today().isoformat()
CC_HOSTS = {"workable": "apply.workable.com/*", "recruitee": "*.recruitee.com", "teamtailor": "*.teamtailor.com",
            "personio_de": "*.jobs.personio.de", "personio_com": "*.jobs.personio.com", "workday": "*.myworkdayjobs.com",
            "breezy": "*.breezy.hr", "bamboohr": "*.bamboohr.com"}
# BambooHR's subdomains are every customer's whole account (sign-in, staff pages): only addresses of its careers pages are asked for
CC_FILTER = {"bamboohr": "~url:/careers"}
# Common Crawl's index server answered 502 or 504 on BambooHR at every page (19 and 20 Nov 2026), although its part of the index is
# four blocks. The same index is published as files: cluster.idx holds the first address of every block of about 3,000 addresses and
# where the block lies in cdx-NNNNN.gz, each block gzipped on its own. So one domain's blocks are read straight from the files by byte
# ranges: about 12 requests to find the place in cluster.idx (100 MB, sorted), then one a block. Addresses as SURT keys: "com,bamboohr,".
CC_FILES = "https://data.commoncrawl.org/cc-index/collections/{crawl}/indexes/"
CC_SURT = {"bamboohr": "com,bamboohr,", "breezy": "hr,breezy,", "paylocity": "com,paylocity,recruiting)/recruiting/jobs/all/"}
# addresses on these hosts that are the system's own pages, not a company's board
NOT_BOARDS = {"www", "app", "api", "help", "support", "status", "blog", "docs", "developer", "developers", "partner", "partners", "academy",
              "marketplace", "cdn", "assets", "static", "tt", "career-site", "login", "signup", "j", "jobs", "careers-page", "oauth", "_next",
              "embed", "widget", "events", "community", "go", "info", "mail", "email", "media", "press", "investors", "assets-cdn", "resources",
              "marketing", "partners-portal", "integrations", "sandbox", "demo", "test"}
URL_RX = [
    ("workable", re.compile(r"https?://apply\.workable\.com/([A-Za-z0-9][A-Za-z0-9_-]{1,60})(?:[/?#]|$)")),
    ("recruitee", re.compile(r"https?://([a-z0-9][a-z0-9-]{1,60})\.recruitee\.com(?:[/:?#]|$)", re.I)),
    ("teamtailor", re.compile(r"https?://([a-z0-9][a-z0-9-]{1,60})\.teamtailor\.com(?:[/:?#]|$)", re.I)),
    ("personio", re.compile(r"https?://([a-z0-9][a-z0-9-]{1,60}\.jobs\.personio\.(?:de|com))(?:[/:?#]|$)", re.I)),
    ("breezy", re.compile(r"https?://([a-z0-9][a-z0-9-]{1,60})\.breezy\.hr(?:[/:?#]|$)", re.I)),
    ("bamboohr", re.compile(r"https?://([a-z0-9][a-z0-9-]{1,60})\.bamboohr\.com/(?:careers|jobs)(?:[/?#]|$)", re.I)),
    ("paylocity", re.compile(r"https?://recruiting\.paylocity\.com/recruiting/jobs/all/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)),
    ("workday", re.compile(r"https?://([a-z0-9][a-z0-9-]{0,60}\.wd\d{1,3})\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9][A-Za-z0-9_-]{1,80})(?:[/?#]|$)")),
]
# Recruitment agencies and job marketplaces post other companies' jobs, often the same one many times: left out, as in sources_more.json.
# The name catches most; the large ones it does not (Kreyco, Huzzle, Clients Blackbox, CXG, Commonwealth Medical Services) were taken
# out of sources_ats.json by hand on 15 Nov 2026 after reading their boards.
AGENCY_RX = re.compile(r"recruit|staffing|\btalents?\b|\bhire\b|headhunt|executive search|personnel|placement|outsourcing|resourcing|\bcareers\b", re.I)
WD_NOT_SITES ={"wday", "robots", "robots.txt", "job", "jobs", "favicon.ico", "sitemap.xml", "siteMap", "en-US", "login", "refreshFacet"}


# --- 1. addresses -----------------------------------------------------------------------------------------------------------------
def read_cc(out_dir, crawls):
    """Common Crawl's URL index for every host in CC_HOSTS, one file per index page (skipped when already there)."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)

    def get(url, timeout=120):
        for i in range(4):
            body = net.get_text(url, timeout, accept="*/*")
            if body is not None: return body
            time.sleep(10 * (i + 1))
        return None
    for crawl in crawls:
        for name, pat in CC_HOSTS.items():
            if os.environ.get("HRN_CC_HOSTS") and name not in os.environ["HRN_CC_HOSTS"].split(","): continue     # HRN_CC_HOSTS=breezy,bamboohr
            base = f"https://index.commoncrawl.org/{crawl}-index?url={urllib.parse.quote(pat, safe='*/')}"
            if name in CC_FILTER: base += "&filter=" + urllib.parse.quote(CC_FILTER[name], safe="~:/")
            try: pages = json.loads(get(base + "&showNumPages=true", 60) or "")["pages"]
            except Exception: print(f"{crawl} {name}: the index did not say how many pages", flush=True); continue
            time.sleep(2)
            for p in range(pages):
                f = out_dir / f"{crawl}__{name}__{p}.txt"
                if f.exists() and f.stat().st_size: continue
                body = get(base + f"&output=json&fl=url&page={p}")
                time.sleep(2)
                if body is None: print(f"{crawl} {name} page {p}: failed", flush=True); continue
                urls = []
                for l in body.splitlines():
                    if not l.startswith("{"): continue
                    try: urls.append(json.loads(l).get("url", ""))
                    except ValueError: pass                 # a line cut short when the index answered in part
                f.write_text("\n".join(urls))
                print(f"{crawl} {name} page {p + 1}/{pages}: {len(urls)} addresses", flush=True)


def _range(url, a, b, timeout=90):
    """Bytes a to b of a file, or None."""
    for i in range(3):
        try:
            r = subprocess.run(["curl", "-s", "-4", "--fail", "--max-time", str(timeout), "-r", f"{a}-{b}", "-A", net.UA, url], capture_output=True, timeout=timeout + 5)
            if r.returncode == 0 and r.stdout: return r.stdout
        except Exception: pass
        time.sleep(5 * (i + 1))
    return None


def cc_files(crawl, prefix):
    """The addresses under one SURT prefix in one crawl, read from the index's files (see CC_FILES). None when a request failed."""
    base = CC_FILES.format(crawl=crawl)
    head = subprocess_head(base + "cluster.idx")
    if not head: return None

    def first_key(pos):
        raw = _range(base + "cluster.idx", pos, pos + 8191)
        if raw is None: raise IOError("cluster.idx")
        lines = raw.decode("utf-8", "replace").split("\n")[1 if pos else 0:]
        return lines[0].split(" ")[0] if lines and lines[0] else None
    try:
        lo, hi = 0, head
        while hi - lo > 65536:                                  # the last place whose line sorts before the prefix
            mid = (lo + hi) // 2
            k = first_key(mid)
            if k is None or k >= prefix: hi = mid
            else: lo = mid
    except IOError:
        return None
    raw = _range(base + "cluster.idx", lo, lo + 262143)
    if raw is None: return None
    rows = [l.split("\t") for l in raw.decode("utf-8", "replace").split("\n")[1 if lo else 0:] if l.count("\t") >= 4]
    urls = []
    for i, r in enumerate(rows):
        start, nxt = r[0].split(" ")[0], (rows[i + 1][0].split(" ")[0] if i + 1 < len(rows) else "~")
        if nxt < prefix: continue
        if start > prefix + "~": break
        data = _range(base + r[1], int(r[2]), int(r[2]) + int(r[3]) - 1)
        if data is None: return None
        for line in zlib.decompress(data, 16 + zlib.MAX_WBITS).decode("utf-8", "replace").splitlines():
            surt, _, rest = line.partition(" ")
            if not surt.startswith(prefix): continue
            m = re.search(r'"url": "([^"]+)"', rest)
            if m: urls.append(m.group(1))
        time.sleep(1)
    return urls


def subprocess_head(url):
    """The size of a file from its headers, or None."""
    try:
        out = subprocess.run(["curl", "-sI", "-4", "--max-time", "30", "-A", net.UA, url], capture_output=True, text=True, timeout=35).stdout
        return int(next(l.split(":", 1)[1] for l in out.lower().splitlines() if l.startswith("content-length")))
    except Exception:
        return None


def read_cc_files(out_dir, crawls):
    """read_cc for the systems in CC_SURT, from the index's files: one file a crawl and system."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for crawl in crawls:
        for name, prefix in CC_SURT.items():
            if os.environ.get("HRN_CC_HOSTS") and name not in os.environ["HRN_CC_HOSTS"].split(","): continue
            f = out_dir / f"{crawl}__{name}__files.txt"
            if f.exists() and f.stat().st_size: continue
            urls = cc_files(crawl, prefix)
            if urls is None: print(f"{crawl} {name}: the index files did not answer", flush=True); continue
            if name in CC_FILTER: urls = [u for u in urls if "/careers" in u or "/jobs" in u]
            f.write_text("\n".join(urls))
            print(f"{crawl} {name}: {len(urls)} addresses", flush=True)


def boards_in(lines):
    """{(ats, token): times seen} for every board address in these lines. Workable and Workday names are not case-sensitive
    ("External" and "external" are one site): each board is counted once, under the spelling seen first."""
    found, spelled = collections.Counter(), {}
    for line in lines:
        for ats, rx in URL_RX:
            m = rx.search(line)
            if not m: continue
            if ats == "workday":
                host, site = m.group(1).lower(), m.group(2)
                if site in WD_NOT_SITES or site.lower() in NOT_BOARDS or re.fullmatch(r"[a-z]{2}(-[A-Za-z]{2})?", site): continue   # "es", "fr-CA": a language
                tok = f"{host}/{site}"
            else:
                tok = m.group(1)
                if ats != "workable": tok = tok.lower()
                if tok.split(".")[0].lower() in NOT_BOARDS: continue
                if ats == "personio" and tok.endswith(".jobs.personio.de"): tok = tok.split(".")[0]
            found[spelled.setdefault((ats, tok.lower()), (ats, tok))] += 1
    return found


# --- 2. verification --------------------------------------------------------------------------------------------------------------
_cache, _real = {}, (collect.get_json, collect.get_text, collect.post_json)


def _get_json(url, timeout=30):
    if url in _cache:
        try: return json.loads(_cache.pop(url))
        except Exception: return None
    return _real[0](url, timeout)


def _get_text(url, timeout=30, accept="application/json", data=None):
    return _cache.pop(url) if url in _cache else _real[1](url, timeout, accept, data)


collect.get_json, collect.get_text = _get_json, _get_text      # fetch_feed reads the answer verify() already has, instead of asking twice


def pretty(tok):
    """A readable company name from an address, when the feed names none ("acme-gmbh" -> "Acme GmbH")."""
    words = re.split(r"[-_.]+", tok.split(".")[0])
    fix = {"gmbh": "GmbH", "ag": "AG", "se": "SE", "bv": "BV", "ab": "AB", "as": "AS", "oy": "Oy", "ltd": "Ltd", "inc": "Inc", "llc": "LLC", "io": "IO", "ai": "AI"}
    return " ".join(fix.get(w.lower(), w[:1].upper() + w[1:]) for w in words if w)


LEGAL_END = re.compile(r"[,\s]+(inc|incorporated|llc|l\.l\.c|ltd|limited|corp|corporation|company|co|n\.a|national association|plc|gmbh|"
                       r"gmbh & co\. kg|kg|ag|s\.a|s\.p\.a|se|b\.v|bv|lp|l\.p|llp|pty|pte|holdings?|group)\.?$", re.I)
# codes in front of an employing entity on Workday: "1010", "94-1687665", "USA", "R551US", "LE102", "HC1327", "CO_AFRINVSAR"
CODE_LEAD = re.compile(r"^(?:\d[\d-]*|(?i:usa|us|uk)|[A-Z]{1,3}\d+[A-Za-z]{0,3}|[A-Z]{2,}_[A-Z_]+)\s+")
PLACE_END = re.compile(r"\s+(?:usa|us|uk|canada|india|ireland|germany|mexico|brasil|brazil)$", re.I)
TAIL = re.compile(r"\s*(?:\([^)]*\)|/.*|\b(?:careers?|jobs)\b)$", re.I)      # "(Enterprise)", " / Ashe DC", " Careers"


def alnum(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("&", "and"))


def clean_name(n, tenant=""):
    """A company name without legal endings and the codes some systems put around it ("1010 United Rentals, Inc." -> "United
    Rentals"; "USA 3M Company" -> "3M"); a leading code stays when the address starts with it too ("2020 Companies")."""
    n = html.unescape(n or "").strip(" ,.-&:;")
    while True:
        m = n if tenant and alnum(n).startswith(alnum(tenant)) else CODE_LEAD.sub("", n)
        m = PLACE_END.sub("", LEGAL_END.sub("", TAIL.sub("", m))).strip(" ,.-&:;")
        # "db Group" is not "db": a short lower-case rest is not a name (20 Nov 2026, BambooHR)
        if m == n or not m or (len(m) <= 3 and m.islower()): return n
        n = m


def name_in(text, tenant):
    """The company's name where a careers site's own text says it ("Founded in 1997, United Rentals is ..."): a run of capitalised
    words that is the address's name, else has it as initials, else is the shortest run starting with it. "" when none is."""
    t = alnum(tenant)
    if len(t) < 2: return ""
    best = {}
    for ph in re.findall(r"[A-Z0-9][\w&'’.-]*(?:\s+(?:&|and|of|[A-Z0-9][\w&'’.-]*))*", text or ""):
        words = ph.split()
        for i in range(len(words)):
            for k in range(i + 1, min(len(words), i + 5) + 1):
                cand = " ".join(words[i:k]).strip(" ,.-")
                if not cand or cand.split()[-1].lower() in ("and", "of", "&"): continue
                a, initials = alnum(cand), "".join(w[0].lower() for w in words[i:k] if w[0].isalnum())
                kind = 0 if a == t else 1 if (k - i > 1 and initials == t) else 2 if (len(t) >= 4 and a.startswith(t)) else None
                if kind == 0:               # the address is often the short name: "Monarch" of "Monarch Healthcare", "Granite" of "Granite Construction"
                    more = words[k:k + 2]
                    while more and (more[-1] in NOT_NAME or more[-1] in words[i:k] or more[-1].lower() in ("and", "of", "&")): more = more[:-1]
                    if more and not any(w in NOT_NAME or w in words[i:k] for w in more): cand = " ".join(words[i:k] + more).strip(" ,.-")
                if kind is not None and kind not in best: best[kind] = cand
    return clean_name(best[min(best)], tenant) if best else ""


NOT_NAME = {"We", "Our", "The", "Is", "Are", "At", "In", "For", "And", "Has", "Have", "Was", "With", "To", "Of", "A", "An", "Careers", "Jobs", "Team",
            "Is", "Inc", "I", "You", "Your", "It", "This", "Join", "Who", "What", "Why", "How", "As", "By", "On", "Since", "From", "All"}


def feed(ats, tok):
    """The address fetch_feed asks, and the type it asks for."""
    if ats == "workable": return f"https://apply.workable.com/api/v1/widget/accounts/{tok}?details=true", "json"
    if ats == "recruitee": return f"https://{tok}.recruitee.com/api/offers/", "json"
    if ats == "teamtailor": return f"https://{tok if '.' in tok else tok + '.teamtailor.com'}/jobs.rss", "application/rss+xml"
    return f"https://{tok if '.' in tok else tok + '.jobs.personio.de'}/xml?language=en", "application/xml"


def name_of(ats, tok, body):
    try:
        if ats == "workable": return (json.loads(body).get("name") or "").strip()
        if ats == "recruitee":
            offers = json.loads(body).get("offers") or []
            return collections.Counter((o.get("company_name") or "").strip() for o in offers).most_common(1)[0][0] if offers else ""
        if ats == "teamtailor":
            m = re.search(r"<channel>\s*<title>([^<]+)</title>", body)
            return html.unescape(m.group(1)).strip() if m else ""
        if ats == "personio":                    # the legal entity of each job, when the company names one: "KNIME GmbH", "KNIME Inc."
            subs = collections.Counter(clean_name(s) for s in re.findall(r"<subcompany>([^<]+)</subcompany>", body))
            top = subs.most_common(1)
            return top[0][0] if top and top[0][1] >= 0.6 * sum(subs.values()) else ""
    except Exception:
        return ""
    return ""


def lands_of(locations):
    import build                                      # the site's own reader of places (slow to import, so only here)
    c = collections.Counter(code for l in locations for code, _ in build.countries_of(l or ""))
    return [code for code, _ in c.most_common(3)]


def verify(ats, tok):
    """(entry for sources_ats.json, None) or (None, why not)."""
    if ats == "workday": return verify_workday(tok)
    if ats in ("breezy", "bamboohr", "paylocity"): return verify_detail(ats, tok)
    url, accept = feed(ats, tok)
    collect.polite(ats)
    body = net.get_text(url, 60, accept="application/json" if accept == "json" else accept)
    if not body: return None, "no answer"
    name = name_of(ats, tok, body) or pretty(tok)
    if ats == "personio" and not name_of(ats, tok, body):            # the careers page's title names the company
        collect.polite(ats)
        page = net.get_text(f"https://{tok if '.' in tok else tok + '.jobs.personio.de'}/?language=en", 30, accept="text/html") or ""
        m = re.search(r"<title>\s*(?:Jobs at|Jobs bei|Careers at)\s+([^<|–]{2,60}?)\s*(?:[|–][^<]*)?</title>", page, re.I)    # often just "Jobs at "
        if m and not re.search(r"not found|personio", m.group(1), re.I): name = clean_name(m.group(1))
    _cache[url] = body
    src = {"name": name, "ats": ats, "token": tok}
    _, jobs = collect.fetch_feed(src)
    _cache.pop(url, None)
    if jobs is None: return None, "feed not readable"
    total = len(jobs) + src.get("not_english", 0)
    if len(jobs) < 3: return None, f"{len(jobs)} English jobs of {total}"
    if len(jobs) < 0.6 * total and len(jobs) < 15: return None, f"mostly not English ({len(jobs)} of {total})"
    return {"name": name, "ats": ats, "token": tok, "count": len(jobs), "lands": lands_of(j["location"] for j in jobs), "added": TODAY}, None


def verify_detail(ats, tok):
    """Breezy, BambooHR and Paylocity: the list in one request, then the text of the first postings (collect.DETAILS, 3 while
    discovering): kept with 3 or more open jobs of which 2 of those read are in English."""
    list_url = {"breezy": f"https://{tok}.breezy.hr/json", "bamboohr": f"https://{tok}.bamboohr.com/careers/list",
                "paylocity": f"{collect.PAYLOCITY}{tok}/jobs"}[ats]
    collect.polite(ats)
    body = net.get_text(list_url, 60, accept="text/html" if ats == "paylocity" else "application/json")
    if not body: return None, "no answer"
    if ats == "paylocity":
        posts = [p for p in collect.paylocity_list(body) or [] if isinstance(p, dict) and not p.get("IsInternal")]
        if collect.paylocity_list(body) is None: return None, "feed not readable"
    else:
        try: d = json.loads(body)
        except ValueError: return None, "feed not readable"
        posts = d if ats == "breezy" else (d.get("result") if isinstance(d, dict) else None)
    if not isinstance(posts, list): return None, "feed not readable"
    if len(posts) < 3: return None, f"{len(posts)} jobs"
    if ats == "paylocity":                                # the page's title: "<company> - Job Opportunities"
        m = re.search(r"<title>\s*(.*?)\s*-\s*Job Opportunities\s*</title>", body, re.S | re.I)
        name = clean_name(html.unescape(m.group(1)), tok) if m else ""
    elif ats == "breezy":
        name = clean_name(collect._nm((posts[0] if isinstance(posts[0], dict) else {}).get("company")), tok)
    else:
        collect.polite(ats)
        info = net.get_json(f"https://{tok}.bamboohr.com/careers/company-info", 30) or {}
        name = clean_name(str((info.get("result") or {}).get("name") or ""), tok) if isinstance(info, dict) else ""
    name = name or pretty(tok)
    _cache[list_url] = body
    src = {"name": name, "ats": ats, "token": tok}
    _, jobs = collect.READERS[ats](src)                  # not collect.fetch: main() already holds this system's gate
    _cache.pop(list_url, None)
    if jobs is None: return None, "feed not readable"
    read = len(jobs) + src.get("not_english", 0)
    if not read: return None, "no text readable"
    if len(jobs) < min(2, read): return None, f"mostly not English ({len(jobs)} of {read} read)"
    title = lambda p: (p.get("name") if ats == "breezy" else p.get("jobOpeningName") if ats == "bamboohr" else p.get("JobTitle")) if isinstance(p, dict) else ""
    return {"name": name, "ats": ats, "token": tok, "count": len(posts), "titles": few_titles(title(p) for p in posts),
            "lands": lands_of(j["location"] for j in jobs), "added": TODAY}, None


def few_titles(titles):
    """How many different jobs a board lists: titles without what follows a dash, bracket or bar, in lower case."""
    return len({re.sub(r"\s*[-–(|].*$", "", str(t or "")).strip().lower() for t in titles})


# A board of 150 jobs or more that is a handful of jobs posted in every place (Taco Bell's franchisee: 2,233 postings, 5 titles,
# 81 towns) is held like the franchise boards of JazzHR and Breezy: thousands of pages that say the same thing, for search engines
# thin copies of one another. Held, not dropped: "hold" with the reason, released by hand when it is worth it.
def same_jobs_everywhere(e):
    return e.get("count", 0) >= 150 and e.get("titles") is not None and e["titles"] <= max(25, e["count"] // 12)


def verify_workday(tok):
    host, site = tok.split("/", 1)
    tenant, origin = host.split(".")[0], f"https://{host}.myworkdayjobs.com"
    base = f"{origin}/wday/cxs/{tenant}/{site}"
    key = f"workday:{host}"
    collect.polite(key)
    robots = net.get_text(f"{origin}/robots.txt", 20, accept="text/plain") or ""
    if robots.lstrip().startswith(("User-agent", "user-agent", "Sitemap", "#", "Disallow", "Allow")):
        rp = urllib.robotparser.RobotFileParser(); rp.parse(robots.splitlines())
        if not (rp.can_fetch("*", f"{base}/jobs") and rp.can_fetch("*", f"{origin}/{site}/")):
            return None, "robots.txt asks crawlers to stay out"
    collect.polite(key)
    d = net.post_json(base + "/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}, 40)
    if not isinstance(d, dict) or not isinstance(d.get("jobPostings"), list): return None, "no answer"
    total, posts = int(d.get("total") or 0), [p for p in d["jobPostings"] if p.get("externalPath")]
    if total < 3 or not posts: return None, f"{total} jobs"
    ok, orgs = 0, []
    for p in posts[:3]:
        collect.polite(key)
        d = net.get_json(base + p["externalPath"], 40) or {}
        info = d.get("jobPostingInfo") or {}
        ok += bool(info.get("title")) and collect.english(f"{info.get('title')}\n{collect.strip_html(info.get('jobDescription'))}")
        orgs.append(((d.get("hiringOrganization") or {}).get("name") or "").strip())
    if ok < min(2, len(posts)): return None, f"mostly not English ({ok} of {min(3, len(posts))} read)"
    return {"name": workday_name(tok, orgs), "ats": "workday", "token": tok, "count": min(total, collect.LIST_MAX),
            "lands": lands_of(p.get("locationsText") for p in posts), "added": TODAY}, None


def workday_name(tok, orgs=None):
    """A Workday careers site names its company nowhere plainly: the text beside the jobs usually does ("At 3M we ..."), the employing
    entity of a job nearly always does ("1010 United Rentals, Inc."), and the address is the last resort."""
    host, site = tok.split("/", 1)
    tenant = host.split(".")[0]
    seen = _names_cache.get(tok) or {}               # HRN_NAMES_CACHE: what an earlier run read, so naming can be redone without asking
    text = seen.get("text")
    if text is None:
        collect.polite(f"workday:{host}")
        side = net.get_json(f"https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/sidebar", 30)
        text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(x.get("text") or ""))) for x in side if isinstance(x, dict)) if isinstance(side, list) else ""
    found = name_in(text, tenant)
    orgs = list(orgs) if orgs is not None else seen.get("orgs")
    if not found and orgs is None:                      # --names: read two jobs for their employing entity
        base = f"https://{host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
        collect.polite(f"workday:{host}")
        d = net.post_json(base + "/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}, 40) or {}
        orgs = []
        for p in (d.get("jobPostings") or [])[:2]:
            collect.polite(f"workday:{host}")
            orgs.append((((net.get_json(base + str(p.get("externalPath")), 40) or {}).get("hiringOrganization") or {}).get("name") or "").strip())
    _names_cache[tok] = {"text": text, "orgs": orgs}
    if not found:                                       # the entity's own words for the address ("JCrew Stores / ..." -> "JCrew"), else all of it
        found = next((n for o in orgs or () if (n := name_in(o, tenant))), "")
    if not found:
        named = collections.Counter(clean_name(o, tenant) for o in orgs or () if o)
        found = named.most_common(1)[0][0] if named else ""
    name = found or pretty(tenant)
    return " ".join(w if len(w) <= 4 or re.search(r"[.&]", w) else w[:1] + w[1:].lower() for w in name.split()) if name.isupper() and len(name) > 5 else name   # "DICK’S SPORTING GOODS"


_names_cache = {}


def main(paths):
    lines = []
    for p in map(Path, paths):
        for f in (sorted(p.glob("*.txt")) if p.is_dir() else [p]):
            lines += f.read_text(errors="replace").splitlines()
    found = boards_in(lines)
    collect.DETAILS = 3                                 # Breezy, BambooHR: three texts are enough to see the language
    have = [s for f in sorted(ROOT.glob("sources*.json")) if "candidates" not in f.name for s in json.loads(f.read_text())]
    have_keys = {(s["ats"], s["token"].lower()) for s in have}
    have_cos = {dedupe.company_key(s["name"]) for s in have}
    # HRN_DISCOVER_LOG: a file of every board checked and what came of it (JSON lines), so a later run does not ask again
    log = Path(os.environ["HRN_DISCOVER_LOG"]) if os.environ.get("HRN_DISCOVER_LOG") else None
    earlier = [json.loads(l) for l in log.read_text().splitlines() if l.strip()] if log and log.exists() else []
    checked = {tuple(r["key"]) for r in earlier}
    todo = [k for k, _ in found.most_common() if (k[0], k[1].lower()) not in have_keys and k not in checked]
    print(f"{len(lines):,} addresses, {len(found):,} boards in them, {len(todo):,} not read yet: " +
          ", ".join(f"{a} {n:,}" for a, n in collections.Counter(a for a, _ in todo).most_common()), flush=True)
    # each system's boards spread evenly through the queue, so that every system has as many boards being read as collect.ATS_LIMIT
    # allows, instead of all the workers waiting on the one system at the head of the queue
    by_ats = collections.defaultdict(list)
    for k in todo: by_ats[k[0]].append(k)
    todo = [k for _, k in sorted((((i + 0.5) / len(ks), k) for ks in by_ats.values() for i, k in enumerate(ks)), key=lambda t: t[0])]
    # boards kept by an earlier run that stopped before writing sources_ats.json
    results = [r["entry"] for r in earlier if r.get("entry") and (r["entry"]["ats"], r["entry"]["token"].lower()) not in have_keys]
    why, lock = collections.Counter(), threading.Lock()
    done = [0]

    def run(item):
        ats, tok = item
        gate = collect._gate.get(ats)
        with gate:
            try: entry, no = verify(ats, tok)
            except Exception as ex: entry, no = None, f"error {type(ex).__name__}"
        with lock:
            if log:
                with log.open("a") as f: f.write(json.dumps({"key": [ats, tok], "entry": entry, "why": no}, ensure_ascii=False) + "\n")
            done[0] += 1
            if entry: results.append(entry)
            else: why[f"{ats}: {re.sub(r'[0-9]+', 'N', no)}"] += 1
            if done[0] % 200 == 0: print(f"  {done[0]:,} of {len(todo):,} checked, {len(results):,} kept", flush=True)
    # HRN_DISCOVER_AT_ONCE=8: boards checked at once on each system (collect.ATS_LIMIT otherwise). The gap between two requests to a
    # system stays collect.ATS_GAP, so this only helps where its answers are slow (BambooHR: two or three seconds a posting's page).
    if os.environ.get("HRN_DISCOVER_AT_ONCE"):
        collect._gate.update({a: threading.Semaphore(int(os.environ["HRN_DISCOVER_AT_ONCE"])) for a in collect._gate})
    import multiprocessing
    collect.PARSE = cf.ProcessPoolExecutor(os.cpu_count() or 2, mp_context=multiprocessing.get_context("spawn"))     # parsing, as in collect.main
    try:
        with cf.ThreadPoolExecutor(sum(collect._gate[a]._value for a in collect._gate)) as ex:
            list(ex.map(run, todo))
    finally:
        collect.PARSE.shutdown(); collect.PARSE = None
    write_kept(results, have_cos, why)


def write_kept(results, have_cos, why):
    """One board per company into OUT: not one we already read, not an agency, the largest when a company has several."""
    best = {}
    for e in sorted(results, key=lambda e: -e["count"]):
        if AGENCY_RX.search(e["name"]): why[f"{e['ats']}: a recruitment agency"] += 1; continue
        k = dedupe.company_key(e["name"])
        if k in have_cos: why[f"{e['ats']}: already read under another system or name"] += 1; continue
        if k in best: why[f"{e['ats']}: a second board of the same company"] += 1; continue
        if same_jobs_everywhere(e):
            e = dict(e, hold=True, why=f"the same {e['titles']} jobs posted in many places"); why[f"{e['ats']}: held, the same few jobs in many places"] += 1
        best[k] = e
    old = json.loads(OUT.read_text()) if OUT.exists() else []
    merged = old + sorted(best.values(), key=lambda e: (-e["count"], e["name"].lower()))
    OUT.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in merged) + "\n]\n")
    print(f"kept {len(best):,} boards with {sum(e['count'] for e in best.values()):,} open jobs: " +
          ", ".join(f"{a} {n:,}" for a, n in collections.Counter(e["ats"] for e in best.values()).most_common()))
    for k, n in sorted(why.items()): print(f"  not kept, {k}: {n:,}")


def from_log(path):
    """The boards an unfinished run has kept so far (its HRN_DISCOVER_LOG) into OUT, so they are read while it goes on. A later run
    with the same log skips them: they are in a sources file by then."""
    have = [s for f in sorted(ROOT.glob("sources*.json")) if "candidates" not in f.name for s in json.loads(f.read_text())]
    have_keys = {(s["ats"], s["token"].lower()) for s in have}
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    results = [r["entry"] for r in rows if r.get("entry") and (r["entry"]["ats"], r["entry"]["token"].lower()) not in have_keys]
    write_kept(results, {dedupe.company_key(s["name"]) for s in have}, collections.Counter())


def names():
    """Name the Workday and Personio boards of sources_ats.json again, then leave out any board that turns out to be a company
    already read from another file, or a second board of one company (the larger stays)."""
    boards = json.loads(OUT.read_text())
    cache = Path(os.environ["HRN_NAMES_CACHE"]) if os.environ.get("HRN_NAMES_CACHE") else None
    if cache and cache.exists(): _names_cache.update(json.loads(cache.read_text()))

    def one(e):
        if e["ats"] in ("workday", "personio"):
            with collect._gate[e["ats"]]:
                try:
                    if e["ats"] == "workday": e["name"] = workday_name(e["token"])
                    else:
                        url, accept = feed("personio", e["token"])
                        collect.polite("personio")
                        e["name"] = name_of("personio", e["token"], net.get_text(url, 60, accept=accept) or "") or clean_name(pretty(e["token"]))
                except Exception: pass
        return e
    with cf.ThreadPoolExecutor(collect.ATS_LIMIT["workday"] + collect.ATS_LIMIT["personio"]) as ex:
        boards = list(ex.map(one, boards))
    if cache: cache.write_text(json.dumps(_names_cache, ensure_ascii=False))
    others = {dedupe.company_key(s["name"]) for f in sorted(ROOT.glob("sources*.json")) if f.name not in ("sources_candidates.json", OUT.name)
              for s in json.loads(f.read_text())}
    keep, seen, dropped = [], set(), []
    for e in sorted(boards, key=lambda e: -e["count"]):
        k = dedupe.company_key(e["name"])
        if k in others or k in seen: dropped.append(e["name"]); continue
        seen.add(k); keep.append(e)
    OUT.write_text(json.dumps(keep, ensure_ascii=False, indent=0) + "\n")
    print(f"{len(keep):,} boards kept; left out as a company already read or a second board: {', '.join(dropped) or '-'}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--cc"]: read_cc(sys.argv[2], sys.argv[3].split(","))
    elif sys.argv[1:2] == ["--cc-files"]: read_cc_files(sys.argv[2], sys.argv[3].split(","))
    elif sys.argv[1:2] == ["--from-log"]: from_log(sys.argv[2])
    elif sys.argv[1:2] == ["--names"]: names()
    elif sys.argv[1:]: main(sys.argv[1:])
    else: print(__doc__)
