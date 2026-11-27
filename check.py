"""Check the built site against the page standard: one H1, title and description lengths, canonical, heading order, internal links;
and (part 2, 26 Nov 2026) accessible names, form labels, duplicate ids, the FAQ markup a reader can see, keyed H2s, picture sizes,
the footer's trust links, the Organization markup and llms.txt.

Run after build.py. Checks every listing-type page and a random sample of job pages; prints a table by template.
"""
import html, json, random, re, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
SITE = ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
P, FULL = CFG.get("base_path", "").rstrip("/"), CFG["base_url"].rstrip("/") + CFG.get("base_path", "").rstrip("/")
random.seed(7)


def template(rel):
    parts = rel.split("/")
    if rel == "index.html": return "home"
    if parts[0] == "job": return "job"
    if parts[0] == "companies": return "company" if len(parts) > 2 else "companies index"
    if parts[0] in ("jobs", "remote", "skills", "locations", "crypto", "perks", "new", "entry-level", "with-salary", "contract", "part-time", "internships", "work-from-anywhere", "archive", "new-grad"):
        return "search" if rel == "jobs/index.html" else "listing"
    if parts[0] in ("salaries", "insights", "trends"): return "data"
    return "static"


# A site built with HRN_RECORDS=1 has no job pages as files: they are rows of data/jobs.db (records.py), and the sample is built from them.
STORE, REC = None, set()
if not (SITE / "job").is_dir() and (ROOT / "data" / "jobs.db").is_file():
    import build, records
    STORE = records.Store(ROOT / "data" / "jobs.db", build)
    REC = STORE.slugs()


def exists(href):
    path = href.split("#")[0].split("?")[0]
    if not path.startswith(P + "/"): return True
    rel = path[len(P) + 1:]
    t = SITE / rel
    if STORE and rel.startswith("job/"): return rel[4:].rstrip("/") in REC
    return t.is_file() or (t / "index.html").is_file() or rel == ""


# The perfect-page standard, part 2 (26 Nov 2026): what the first checks above did not test, found on the live site in a sample of
# 479 pages: accessible names, form labels, duplicate ids, ids that labels and controls point to, the FAQ markup a reader cannot see,
# headings with no key ("Sources", "About the role", "Related tools"), pictures without both sizes, the footer's trust links, and the
# Organization markup. Plain patterns, so the run over every page stays quick.
NOSCRIPT = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.S)
ID_RX = re.compile(r'<[a-zA-Z][^>]*?\sid="([^"]+)"')
REF_RX = re.compile(r'\s(aria-labelledby|aria-describedby|aria-controls)="([^"]+)"')
FOR_RX = re.compile(r'<label\b[^>]*\sfor="([^"]+)"')
BTN_RX = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.S)
A_RX = re.compile(r"<a\b([^>]*\shref=[^>]*)>(.*?)</a>", re.S)
CTRL_RX = re.compile(r"<(input|select|textarea)\b([^>]*)>")
NAMED = re.compile(r'\s(?:aria-label|title)="[^"]*\S[^"]*"|\saria-labelledby="[^"]+"')
INNER_NAMED = re.compile(r'<img\b[^>]*\salt="[^"]*\S|<svg\b[^>]*\saria-label="[^"]*\S|<title>\s*\S')
H2_RX = re.compile(r"<h2\b[^>]*>(.*?)</h2>", re.S)
LD_RX = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
TAGS = re.compile(r"<[^>]+>")
HAS_TEXT = re.compile(r"(?:^|>)[^<]*?[^<\s]")          # some text outside the tags: the quick test before the slower ones
FLAGS = re.compile(r'<i class="fl">.*?</i>')
IMG_NO_W, IMG_NO_H = re.compile(r"<img\b(?![^>]*\swidth=)[^>]*>"), re.compile(r"<img\b(?![^>]*\sheight=)[^>]*>")
# a heading that names nothing: the page's key or a real question belongs in every H2 (owner's page standard)
BARE_H2 = {"faq", "faqs", "frequently asked questions", "questions", "latest", "more", "related", "sources", "overview", "details", "summary",
           "about", "about the role", "related tools", "related salaries", "top-paying companies", "more comparisons", "more skill comparisons",
           "quick tips", "use it with", "make it yours", "the code", "options", "examples", "example", "mistakes to avoid", "what to do about it",
           "before and after", "after you resign", "other platforms", "more ways to use it", "endpoints", "response", "fair use", "logo", "colors",
           "color", "screenshots", "charts", "pictures", "the mark", "type", "the newest of these jobs", "what you compete with",
           "kinds of work close to this one", "titles employers use", "what employers ask for", "other employers of about this size"}
FOOT_LINKS = (("About", f'{P}/about/"'), ("Contact", f'{P}/about/#contact"'), ("Editorial policy", f'{P}/methodology/#editorial-policy"'),
              ("Privacy", f'{P}/privacy/"'), ("Terms", f'{P}/terms/"'))


def plain(s_):
    return re.sub(r"\s+", " ", html.unescape(TAGS.sub(" ", s_))).strip()


def ld_items(o, top=True):
    """(item, top-level?) for every typed object of a JSON-LD block, @graph and nested objects included."""
    if isinstance(o, list):
        for x in o: yield from ld_items(x, top)
    elif isinstance(o, dict):
        if "@graph" in o: yield from ld_items(o["@graph"], True)
        if "@type" in o: yield o, top
        for k_, v_ in o.items():
            if k_ != "@graph" and isinstance(v_, (dict, list)): yield from ld_items(v_, False)


def standard2(h):
    """The names of the rules of part 2 that page h breaks."""
    bad = []
    body = NOSCRIPT.sub("", h)
    ids = Counter(ID_RX.findall(body))
    if any(k_ > 1 for k_ in ids.values()): bad.append("duplicate id")
    labels_for = set(FOR_RX.findall(body))
    if any(r_ not in ids for _, refs in REF_RX.findall(body) for r_ in refs.split()) or any(f_ not in ids for f_ in labels_for):
        bad.append("aria-* or label for= points to a missing id")
    if any(not HAS_TEXT.search(t_) and not NAMED.search(a_) and not INNER_NAMED.search(t_) for a_, t_ in BTN_RX.findall(body)): bad.append("button without a name")
    if any(not HAS_TEXT.search(t_) and not NAMED.search(a_) and not INNER_NAMED.search(t_) for a_, t_ in A_RX.findall(body)): bad.append("link without a name")
    for m_ in CTRL_RX.finditer(body):
        tag_, at_ = m_.groups()
        ty_ = (re.search(r'\stype="([^"]+)"', at_) or [None, "text"])[1]
        if tag_ == "input" and ty_ in ("hidden", "submit", "button", "reset", "image"): continue
        id_ = (re.search(r'\sid="([^"]+)"', at_) or [None, ""])[1]
        if NAMED.search(at_) or (id_ and id_ in labels_for) or body.rfind("<label", 0, m_.start()) > body.rfind("</label>", 0, m_.start()): continue
        bad.append("form field without a label"); break
    for t_ in H2_RX.findall(body):
        if re.sub(r"[\d,]+$", "", plain(t_)).strip(" .:?").lower() in BARE_H2: bad.append("H2 without the page's key (a bare heading)"); break
    if IMG_NO_W.search(body) or IMG_NO_H.search(body): bad.append("img without width and height")
    if "<footer" in body:
        foot_ = body[body.rfind("<footer"):]
        miss_ = [n_ for n_, href_ in FOOT_LINKS if href_ not in foot_]
        if miss_: bad.append("footer without " + ", ".join(miss_))
    seen_ = None
    for blk in LD_RX.findall(h):
        try:
            o_ = json.loads(blk)
        except ValueError:
            bad.append("JSON-LD that does not parse"); continue
        for it, top in ld_items(o_):
            ty_ = it.get("@type")
            if ty_ == "FAQPage":
                if seen_ is None: seen_ = re.sub(r"\s+", " ", html.unescape(TAGS.sub(" ", FLAGS.sub("", body.split("<main", 1)[-1])))).lower()
                for q_ in it.get("mainEntity") or []:
                    nm_ = re.sub(r"\s+", " ", html.unescape(str(q_.get("name") or ""))).strip().lower() if isinstance(q_, dict) else ""
                    if not nm_ or nm_ not in seen_: bad.append("FAQPage question not visible on the page"); break
            elif ty_ == "Organization" and top and not (it.get("logo") and it.get("sameAs")): bad.append("Organization without logo or sameAs")
    return bad


# Jobs first on the lists people reach from search engines (track "one button", 26 Nov 2026: the first job stood at 1,064 to 5,736 px,
# under a paragraph, four big numbers, charts and cards of definitions). On the first page of a list, nothing comes before the first
# job card but the trail, the H1, the one line under it, the ways to narrow the list, the alert line (with Save this list or Follow) and
# the list's own heading.
LIST_FIRST = re.compile(r"^(?:(?:locations|categories|roles|skills|companies|jobs|remote|crypto|perks|new)/[^/]+/(?:[a-z][^/]*/)?|"
                        r"(?:remote|entry-level|new|part-time|internships|with-salary|contract|hybrid|work-from-anywhere|tech)/|internships/[a-z0-9-]+/|new-grad/(?:[a-z0-9-]+/)?)index\.html$")
BEFORE_OK = [re.compile(x_, re.S) for x_ in (r'<div class="crumbs">.*?</div>', r"<h1[\s>].*?</h1>", r'<p class="lline">.*?</p>', r'<div class="sec-head lst"[^>]*>.*?</div>',
             r'<span class="lsave-n">.*?</span>',
             r'<div class="pillrow lnarrow".*?</div>', r'<form class="alertf alert1".*?</form>', r'<button[^>]*(?:data-save-list|id="follow")[^>]*>.*?</button>',
             r'<span class="ava[^"]*"[^>]*>.*?</span>', r"<!--.*?-->")]


def jobs_first(h):
    """False when a block other than the allowed ones stands between the start of <main> and the first job card of a list page."""
    main_ = h.split('id="main">', 1)[-1]
    at = main_.find('<li class="job')
    if at < 0: return True
    pre = main_[:at]
    for rx_ in BEFORE_OK: pre = rx_.sub(" ", pre)
    return not re.search(r"<(?:section|h2|h3|dl|table|figure|article|aside|p)\b", pre) and not plain(pre)


pages = [p for p in SITE.rglob("index.html")]
jobs = [str(p.relative_to(SITE)) for p in pages if p.relative_to(SITE).parts[0] == "job"] or [f"job/{s}/index.html" for s in sorted(REC)]
others = [str(p.relative_to(SITE)) for p in pages if p.relative_to(SITE).parts[0] not in ("job", "embed")]
sample = others + random.sample(jobs, min(600, len(jobs)))
fails, counts, broken = defaultdict(Counter), Counter(), Counter()
not_for_map = set()          # pages a sitemap must not list: noindex, or a canonical that names another page (Bing: "only canonical URLs")
for rel in sample:
    t = template(rel); counts[t] += 1
    h = STORE.page(rel.split("/")[1]) if STORE and t == "job" else (SITE / rel).read_text(encoding="utf-8", errors="replace")
    if 'http-equiv="refresh"' in h[:600] and 'name="robots" content="noindex"' in h[:600]: counts[t] -= 1; continue      # another address for a page (/glossary/ats/): it hands over, it is not a page
    title = re.search(r"<title>(.*?)</title>", h, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', h)
    canon = re.search(r'<link rel="canonical" href="([^"]*)"', h)
    h1 = re.findall(r"<h1[\s>]", h)
    if len(h1) != 1: fails[t][f"h1 count {len(h1)}"] += 1
    if not title or not (10 <= len(html.unescape(title.group(1))) <= 75): fails[t]["title length outside 10-75"] += 1
    if not desc or not (70 <= len(html.unescape(desc.group(1))) <= 170): fails[t]["description length outside 70-170"] += 1
    want = FULL + "/" + ("" if rel == "index.html" else rel[:-len("index.html")])
    # A list page may name a fuller page with the same words in its title as canonical (build.one_page_per_query): that is allowed
    # when the page it names exists and names itself. Anything else is a mistake.
    if re.search(r'<meta name="robots" content="[^"]*noindex', h[:8000]) or (canon and canon.group(1) != want): not_for_map.add(want[len(FULL) + 1:])
    if not canon: fails[t]["canonical is not self"] += 1
    elif canon.group(1) != want:
        other = SITE / canon.group(1)[len(FULL) + 1:] / "index.html" if canon.group(1).startswith(FULL + "/") else None
        # a job page that repeats an earlier one names that one (build.same_text_jobs); on a site built from records it is a record, not a file
        rec_ = canon.group(1)[len(FULL) + 1:] if STORE and canon.group(1).startswith(FULL + "/job/") else ""
        if rec_ and not (other and other.exists()):
            ok_ = f'<link rel="canonical" href="{canon.group(1)}"' in (STORE.page(rec_.split("/")[1]) or "")[:6000]
        else:
            ok_ = bool(other and other.exists() and f'<link rel="canonical" href="{canon.group(1)}"' in other.read_text(encoding="utf-8", errors="replace")[:6000])
        if not ok_: fails[t]["canonical is not self"] += 1
    if 'lang="en"' not in h[:200]: fails[t]["no lang"] += 1
    heads = [int(x) for x in re.findall(r"<h([1-6])[\s>]", h.split("<footer")[0])]
    if any(b - a > 1 for a, b in zip(heads, heads[1:])): fails[t]["heading level skipped"] += 1
    if re.search(r"<img(?![^>]*\balt=)", h): fails[t]["img without alt"] += 1
    # empty alt="" too (24 Nov 2026): Bing Site Scan reports it as "Alt attribute for images is missing", and the owner wants every image named
    if re.search(r'<img[^>]*\balt=""', h): fails[t]["img with empty alt"] += 1
    if re.search(r"<img(?![^>]*\btitle=)", h): fails[t]["img without title"] += 1
    # code that reached the page as text: an f-string without its "f" printed "{fdate(TODAY)}" on 4,626 pages of a local build (24 Nov 2026)
    if re.search(r"\{(?:fdate|money|e|len|round|art|tcase|rlow|TODAY|SITE|P)\b[^}]{0,40}\}", re.sub(r"<script.*?</script>|<style.*?</style>", "", h, flags=re.S)):
        fails[t]["code printed as text ({...})"] += 1
    for b_ in standard2(h): fails[t][b_] += 1
    if LIST_FIRST.match(rel) and not jobs_first(h): fails[t]["a block before the first job of a list"] += 1
    for href in set(re.findall(r'href="(/[^"]*)"', h)):
        if not exists(href):
            fails[t]["broken internal link"] += 1; broken[href] += 1
# the sitemaps list only pages that exist, are offered to search engines and name themselves as canonical (Bing's webmaster
# guidelines, 26 Nov 2026), each once: every non-job address in them, and the job pages of the sample
if (SITE / "sitemap.xml").is_file():
    counts["sitemaps"] = 0
    listed_, in_sample_ = Counter(), set(sample)
    for sm_ in sorted((SITE / "sitemaps").glob("*.xml")):
        counts["sitemaps"] += 1
        for u_ in re.findall(r"<loc>([^<]+)</loc>", sm_.read_text(encoding="utf-8", errors="replace")):
            rel_ = html.unescape(u_)[len(FULL) + 1:]
            listed_[rel_] += 1
            if rel_.startswith("job/") and f"{rel_}index.html" not in in_sample_: continue
            if rel_ in not_for_map: fails["sitemaps"]["lists a noindex or canonicalised page"] += 1
            elif not rel_.startswith("job/") and not exists(f"{P}/{rel_}"): fails["sitemaps"]["lists a page that does not exist"] += 1
    if any(k_ > 1 for k_ in listed_.values()): fails["sitemaps"]["lists an address twice"] += sum(1 for k_ in listed_.values() if k_ > 1)
    # robots.txt (27 Nov 2026: the query addresses of the tool and search pages are disallowed for "User-agent: *"): no sitemap names an
    # address it disallows, the pages themselves stay open, and the AI assistants' group allows everything, as Google reads the rules
    # (the longest matching rule wins, Allow on a tie; "*" is any characters, "$" the end)
    if (SITE / "robots.txt").is_file():
        groups_, cur_, fresh_ = {}, [], True
        for ln_ in (SITE / "robots.txt").read_text(encoding="utf-8").splitlines():
            ln_ = ln_.split("#", 1)[0].strip()
            if not ln_ or ":" not in ln_: continue
            k_, v_ = (x_.strip() for x_ in ln_.split(":", 1))
            if k_.lower() == "user-agent":
                if not fresh_: cur_ = []
                fresh_ = True
                groups_.setdefault(v_.lower(), cur_)
            elif k_.lower() in ("allow", "disallow"):
                fresh_ = False
                cur_.append((k_.lower(), v_))
        def rule_rx_(pat_):
            end_ = pat_.endswith("$")
            return re.compile(re.escape(pat_[:-1] if end_ else pat_).replace(r"\*", ".*") + ("$" if end_ else ""))
        def blocked_(path_, rules_):
            best_ = (-1, "allow")
            for kind_, pat_ in rules_:
                if pat_ and rule_rx_(pat_).match(path_) and (len(pat_) > best_[0] or (len(pat_) == best_[0] and kind_ == "allow")): best_ = (len(pat_), kind_)
            return best_[1] == "disallow"
        assert blocked_("/resume/?job=a", [("disallow", "/resume/?")]) and not blocked_("/resume/", [("disallow", "/resume/?")])
        assert blocked_("/tools/cover-letter/?job=a", [("disallow", "/tools/*?job=")]) and not blocked_("/tools/cover-letter/", [("disallow", "/tools/*?job=")])
        counts["robots.txt"] = 1
        star_ = groups_.get("*", [])
        bad_ = [r_ for r_ in listed_ if blocked_(f"{P}/{r_}", star_)]
        if bad_: fails["robots.txt"][f"a sitemap lists an address it disallows ({bad_[0]})"] += len(bad_)
        for open_ in ("/", "/jobs/", "/resume/", "/tools/resume-match/", "/tools/cover-letter/", "/job/x/", "/remote/", "/companies/x/"):
            if blocked_(P + open_, star_): fails["robots.txt"][f"disallows {open_}"] += 1
        for bot_ in ("gptbot", "claudebot", "perplexitybot", "google-extended"):
            if bot_ not in groups_ or any(k_ == "disallow" and v_ for k_, v_ in groups_[bot_]): fails["robots.txt"][f"does not allow everything for {bot_}"] += 1
    # every job page the sitemaps list, not only the sample (27 Nov 2026): an open job, offered to search engines (no noindex), naming itself
    # as canonical. Closed jobs left the sitemaps that day; their pages stay. On a site built from records the record says it (open, a
    # Telegram post, a repeat of another page), read by SQLite without building 800,000 pages; on a site of files the page's own head.
    job_listed_ = [r_[4:].rstrip("/") for r_ in listed_ if r_.startswith("job/")]
    counts["sitemap job pages"] = len(job_listed_)
    if STORE:
        with STORE.reading() as con_:
            facts_ = {sl_: (a_, t_, d_) for sl_, a_, t_, d_ in con_.execute("SELECT slug, active, json_extract(rec, '$.tg'), json_extract(rec, '$.dup_of') FROM jobs")}
        for sl_ in job_listed_:
            a_, t_, d_ = facts_.get(sl_, (None, None, None))
            if a_ is None: fails["sitemaps"]["lists a job with no record"] += 1
            elif not a_: fails["sitemaps"]["lists a closed job"] += 1
            elif t_ or d_: fails["sitemaps"]["lists a noindex or canonicalised job page"] += 1
    else:
        for sl_ in job_listed_:
            f_ = SITE / "job" / sl_ / "index.html"
            if not f_.is_file(): fails["sitemaps"]["lists a page that does not exist"] += 1; continue
            with f_.open(encoding="utf-8", errors="replace") as fh_: h_ = fh_.read(12000)
            c_ = re.search(r'<link rel="canonical" href="([^"]*)"', h_)
            if re.search(r'<meta name="robots" content="[^"]*noindex', h_) or not c_ or c_.group(1) != f"{FULL}/job/{sl_}/": fails["sitemaps"]["lists a noindex or canonicalised job page"] += 1
            elif re.search(r"<title>[^<]*\(closed\)", h_): fails["sitemaps"]["lists a closed job"] += 1
# every script the pages load must parse (20 Nov 2026: a stray "//" in assets/site.js left every script of the live site dead)
import shutil, subprocess                     # noqa: E402
if shutil.which("node"):
    for js in sorted(SITE.glob("*.js")):
        counts["scripts"] += 1
        if subprocess.run(["node", "--check", str(js)], capture_output=True).returncode: fails["scripts"][f"{js.name} does not parse"] += 1
# the account page (26 Nov 2026): its HTML has one H1, the page's own in #acc-hd, and account.js draws every screen (sign-in, each part
# of the job seeker's and the employer's account) with a headline of its own; two H1s stood in the page once it had loaded. account.js
# keeps one (oneH1: the page's own goes once a screen draws its own, and only the open part's headline is an H1)
if (SITE / "account" / "index.html").is_file():
    counts["account"] += 1
    acc_ = (SITE / "account" / "index.html").read_text(encoding="utf-8", errors="replace")
    if len(re.findall(r"<h1[\s>]", acc_)) != 1 or not re.search(r'<div id="acc-hd"><h1[\s>]', acc_): fails["account"]["the one H1 of the HTML is not the page's own in #acc-hd"] += 1
    acc_js = (SITE / "account.js").read_text(encoding="utf-8", errors="replace") if (SITE / "account.js").is_file() else ""
    if "function oneH1()" not in acc_js or "MutationObserver(oneH1)" not in acc_js: fails["account"]["account.js does not keep one H1 per screen (oneH1)"] += 1
# the XML feed for job search engines (job_feed.py, 26 Nov 2026): every file read back with a streaming parser, the fields of every
# job, no control characters, and the .gz copy unpacked and compared with the file
if (SITE / "feeds" / "index.xml").is_file():
    import job_feed
    counts["job feed"] = len(list((SITE / "feeds").glob("jobs-*.xml")))
    for p_ in job_feed.check(SITE / "feeds", FULL)[:20]: fails["job feed"][p_] += 1
# company pages that sift() left without a record (27 Nov 2026, owner's rule: never remove a page): each address still answers, with the
# page of the H-1B filings held for the name (an H1, the filings, no job and no noindex) or an immediate hand-over to /companies/; and
# every hand-over page under companies/ points to a page that exists
gone_f = ROOT / "data" / "companies_gone.json"
counts["gone companies"] = 0
for sl_, v_ in (json.loads(gone_f.read_text(encoding="utf-8")) if gone_f.is_file() else {}).items():
    counts["gone companies"] += 1
    f_ = SITE / "companies" / sl_ / "index.html"
    if not f_.is_file(): fails["gone companies"][f"companies/{sl_}/ answers 404"] += 1; continue
    h_ = f_.read_text(encoding="utf-8", errors="replace")
    if v_.get("page") == "h1b":
        if 'id="h1b"' not in h_ or len(re.findall(r"<h1[\s>]", h_)) != 1 or '<li class="job' in h_ or 'content="noindex' in h_[:8000]:
            fails["gone companies"][f"companies/{sl_}/ is not a page of its H-1B filings alone"] += 1
    elif f'http-equiv="refresh" content="0; url={P}/companies/"' not in h_ or f'<link rel="canonical" href="{FULL}/companies/">' not in h_:
        fails["gone companies"][f"companies/{sl_}/ does not hand over to /companies/"] += 1
for f_ in (SITE / "companies").glob("*/index.html") if (SITE / "companies").is_dir() else ():
    with f_.open(encoding="utf-8", errors="replace") as fh_: h_ = fh_.read(1200)
    m_ = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', h_)
    if m_ and not exists(m_.group(1)): fails["gone companies"][f"{f_.parent.name} hands over to a page that does not exist"] += 1
# The season and class pages (build.season_sets, 27 Nov 2026): each set of 20 or more fresh postings has its page, a real list (not a
# hand-over) in a sitemap, with no stale posting on it (a talent pool, or an employer's date 90+ days old: build.stale), so the first job
# is a fresh one; every season address with no page this build hands over to a page that exists, so none answers 404.
season_f = ROOT / "data" / "season_pages.json"
if season_f.is_file():
    import datetime
    sp_ = json.loads(season_f.read_text(encoding="utf-8"))
    stale_day_ = (datetime.date.fromisoformat(sp_.get("day") or str(datetime.date.today())) - datetime.timedelta(days=90)).isoformat()
    in_map_ = set(listed_) if (SITE / "sitemap.xml").is_file() else set()
    counts["season pages"] = 0
    for rel_, n_ in sp_.get("pages", {}).items():
        if n_ < sp_.get("min", 20): continue
        counts["season pages"] += 1
        f_ = SITE / rel_ / "index.html"
        if not f_.is_file(): fails["season pages"][f"{rel_} ({n_} jobs) has no page"] += 1; continue
        h_ = f_.read_text(encoding="utf-8", errors="replace")
        if 'http-equiv="refresh"' in h_[:600] or '<li class="job' not in h_: fails["season pages"][f"{rel_} is not a list of jobs"] += 1; continue
        if rel_ not in in_map_: fails["season pages"][f"{rel_} is not in a sitemap"] += 1
        cards_ = re.findall(r'<li class="job[^"]*">.*?<span class="jt">(.*?)</span>.*?<time datetime="([^"]*)"', h_.split('id="main">', 1)[-1], re.S)
        if not cards_: fails["season pages"][f"{rel_}: no job cards read"] += 1
        old_ = [bool((d_ and d_[:10] < stale_day_) or re.search(r"talent (pool|community|network)|general application|future opportunit", t_, re.I)) for t_, d_ in cards_]
        if old_ and old_[0]: fails["season pages"][f"{rel_}: the first job is stale ({plain(cards_[0][0])[:60]})"] += 1
        elif any(old_): fails["season pages"][f"{rel_}: {sum(old_)} stale jobs on the page"] += 1
    for rel_, to_ in sp_.get("gone", {}).items():
        counts["season pages"] += 1
        f_ = SITE / rel_ / "index.html"
        if not f_.is_file(): fails["season pages"][f"{rel_} answers 404"] += 1; continue
        h_ = f_.read_text(encoding="utf-8", errors="replace")[:1500]
        m_ = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', h_)
        if not m_ or not exists(m_.group(1)) or f'<link rel="canonical" href="{FULL}/{to_}">' not in h_: fails["season pages"][f"{rel_} does not hand over to a page that exists"] += 1
        if rel_ in in_map_: fails["season pages"][f"{rel_} hands over and is in a sitemap"] += 1
# llms.txt (perfect-page standard: present and current): dated with the build's day, and every page it names exists
llms = SITE / "llms.txt"
counts["llms.txt"] = 1
if not llms.is_file(): fails["llms.txt"]["missing"] += 1
else:
    lt_ = llms.read_text(encoding="utf-8")
    newest_ = max(re.findall(r"<lastmod>(\d{4}-\d\d-\d\d)</lastmod>", (SITE / "sitemap.xml").read_text(encoding="utf-8")) or [""]) if (SITE / "sitemap.xml").is_file() else ""
    if newest_ and f"Updated {newest_}" not in lt_: fails["llms.txt"][f"not dated {newest_}"] += 1
    for u_ in set(re.findall(re.escape(FULL) + r"(/[^\s)<>\]]*/)(?=[\s)\].,;#]|$)", lt_)):
        if "<" not in u_ and not exists(P + u_): fails["llms.txt"]["names a page that does not exist"] += 1; broken[u_] += 1
# One set of figures (teardown, 26 Nov 2026: the media kit, /methodology/ and /status/ gave three different accounts of how often jobs are
# checked). The pages that state it say build.FACTS' line with the same number, and none of them claims "every hour" in its own text
# (the brand's name, its quoted logo words and the guide's address excepted; the header and the footer are checked below).
FACT_RX = re.compile(r"(\d+)% of open jobs were re-checked on the employer’s own list in the last 24 hours")
HOURLY_RX = re.compile(r"(?<!Jobs )(?<!“jobs )every hour(?!”)(?!/)", re.I)
fact_pages = ["about/index.html", "methodology/index.html", "media-kit/index.html", "guides/how-we-check-jobs-every-hour/index.html", "safety/index.html", "llms.txt"]
counts["one set of figures"] = 0
seen_pct = set()
for rel_ in fact_pages:
    f_ = SITE / rel_
    if not f_.is_file(): continue
    counts["one set of figures"] += 1
    t_ = f_.read_text(encoding="utf-8", errors="replace")
    body_ = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", NOSCRIPT.sub(" ", t_.split("<footer")[0]))))
    got_ = set(FACT_RX.findall(body_))
    if not got_: fails["one set of figures"][f"{rel_}: no re-checked figure"] += 1
    seen_pct |= got_
    if HOURLY_RX.search(body_.replace("how-we-check-jobs-every-hour", "")): fails["one set of figures"][f"{rel_}: says every hour"] += 1
if len(seen_pct) > 1: fails["one set of figures"][f"different re-checked figures: {sorted(seen_pct)}"] += 1
# The header and the footer say it the same way (27 Nov 2026: on every page the footer said "re-checked every hour" and the header's
# Find jobs menu "Checked every hour", while the pages above them said what was measured). Their text on the fact pages and the home
# page, and the script that draws the header's menus, may not claim "every hour"; the footer gives the same re-checked figure.
counts["header and footer"] = 0
for rel_ in fact_pages[:-1] + ["index.html"]:
    f_ = SITE / rel_
    if not f_.is_file(): continue
    counts["header and footer"] += 1
    t_ = f_.read_text(encoding="utf-8", errors="replace")
    for where_, part_ in (("header", t_[t_.find("<header"):t_.find("</header>")] if "<header" in t_ else ""), ("footer", t_[t_.rfind("<footer"):] if "<footer" in t_ else "")):
        txt_ = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", part_)))
        if HOURLY_RX.search(txt_): fails["header and footer"][f"{rel_}: the {where_} says every hour"] += 1
        if where_ == "footer" and seen_pct and (m_ := re.search(r"re-checked around the clock: (\d+)% of open jobs", txt_)) and m_.group(1) not in seen_pct:
            fails["header and footer"][f"{rel_}: the footer's re-checked figure differs from the page's"] += 1
for js_ in ("site.js",):
    f_ = SITE / js_
    if not f_.is_file(): continue
    counts["header and footer"] += 1
    if HOURLY_RX.search(f_.read_text(encoding="utf-8", errors="replace")): fails["header and footer"][f"{js_} (the header's menus) says every hour"] += 1
# The Ghost Jobs Index as a dataset (27 Nov 2026: Google Dataset Search listed 14 other "ghost job index" datasets, not ours). The Dataset
# markup of /ghost-jobs/ parses and has the fields of Google's guide (developers.google.com/search/docs/appearance/structured-data/dataset):
# a name, a description of 50 to 5,000 characters, the page's address, a creator with an address, a license, free access, keywords, the
# dates from the start of the record to the day of the build, real countries, the measures and the method; and both CSV files, named,
# typed text/csv and present in the build.
gj_f = SITE / "ghost-jobs" / "index.html"
counts["ghost jobs dataset"] = 1
if not gj_f.is_file(): fails["ghost jobs dataset"]["ghost-jobs/ was not built"] += 1
else:
    ds_ = []
    for blk in LD_RX.findall(gj_f.read_text(encoding="utf-8", errors="replace")):
        try: ds_ += [it for it, _ in ld_items(json.loads(blk)) if it.get("@type") == "Dataset"]
        except ValueError: fails["ghost jobs dataset"]["JSON-LD that does not parse"] += 1
    if len(ds_) != 1: fails["ghost jobs dataset"][f"{len(ds_)} Dataset blocks, not one"] += 1
    for d_ in ds_[:1]:
        miss_ = [k_ for k_ in ("name", "description", "url", "creator", "license", "isAccessibleForFree", "keywords", "temporalCoverage", "spatialCoverage",
                               "variableMeasured", "measurementTechnique", "distribution", "dateModified", "version") if not d_.get(k_)]
        if miss_: fails["ghost jobs dataset"]["missing " + ", ".join(miss_)] += 1
        if not 50 <= len(str(d_.get("description") or "")) <= 5000: fails["ghost jobs dataset"]["description not 50 to 5,000 characters"] += 1
        if d_.get("url") != f"{FULL}/ghost-jobs/": fails["ghost jobs dataset"]["url is not the page's own"] += 1
        cr_ = d_.get("creator") or {}
        if not (isinstance(cr_, dict) and cr_.get("@type") == "Organization" and cr_.get("name") and str(cr_.get("url") or "").startswith("https://")):
            fails["ghost jobs dataset"]["creator is not an Organization with a name and url"] += 1
        if d_.get("isAccessibleForFree") is not True: fails["ghost jobs dataset"]["isAccessibleForFree is not true"] += 1
        tc_ = re.fullmatch(r"(\d{4}-\d\d-\d\d)/(\d{4}-\d\d-\d\d)", str(d_.get("temporalCoverage") or ""))
        if not tc_ or tc_.group(1) > tc_.group(2) or tc_.group(2) != str(d_.get("dateModified")):
            fails["ghost jobs dataset"]["temporalCoverage is not start/day of the build"] += 1
        sc_ = d_.get("spatialCoverage") if isinstance(d_.get("spatialCoverage"), list) else [d_.get("spatialCoverage")]
        if not sc_ or any(not isinstance(x_, dict) or not x_.get("name") or x_["name"] == "Worldwide" for x_ in sc_):
            fails["ghost jobs dataset"]["spatialCoverage is not named countries"] += 1
        got_ = {}
        for x_ in d_.get("distribution") or []:
            if isinstance(x_, dict) and x_.get("@type") == "DataDownload" and x_.get("encodingFormat") == "text/csv" and x_.get("name"): got_[x_.get("contentUrl")] = x_
        for csv_ in ("ghost-jobs.csv", "ghost-jobs-employers.csv"):
            if f"{FULL}/data/{csv_}" not in got_: fails["ghost jobs dataset"][f"no named text/csv DataDownload for {csv_}"] += 1
            if not (SITE / "data" / csv_).is_file(): fails["ghost jobs dataset"][f"data/{csv_} was not built"] += 1
# The Android app (27 Nov 2026): the app com.jobseveryhour.app opens the site without the browser's address bar only while
# /.well-known/assetlinks.json names it and its certificate (config.json "android_app"), and the store listing and Chrome's install sheet
# read the manifest's id, description, categories, shortcuts and screenshots. None of it may quietly disappear.
counts["android app"] = 1
aa_cfg = CFG.get("android_app") or {}
if not (aa_cfg.get("package") and aa_cfg.get("sha256")): fails["android app"]["config.json has no android_app package and sha256"] += 1
al_f = SITE / ".well-known" / "assetlinks.json"
if not al_f.is_file(): fails["android app"][".well-known/assetlinks.json was not built"] += 1
else:
    try: al_ = json.loads(al_f.read_text(encoding="utf-8"))
    except ValueError: al_ = None; fails["android app"]["assetlinks.json does not parse"] += 1
    ok_ = [x_ for x_ in (al_ if isinstance(al_, list) else []) if isinstance(x_, dict)
           and "delegate_permission/common.handle_all_urls" in (x_.get("relation") or [])
           and (x_.get("target") or {}).get("namespace") == "android_app" and (x_.get("target") or {}).get("package_name") == aa_cfg.get("package")]
    if not ok_: fails["android app"]["assetlinks.json does not delegate handle_all_urls to the app's package"] += 1
    fps_ = [f_ for x_ in ok_ for f_ in (x_["target"].get("sha256_cert_fingerprints") or [])]
    if not fps_ or any(not re.fullmatch(r"(?:[0-9A-F]{2}:){31}[0-9A-F]{2}", f_) for f_ in fps_): fails["android app"]["assetlinks.json fingerprints missing or not SHA-256 AA:BB:..."] += 1
    if set(fps_) != set(aa_cfg.get("sha256") or []): fails["android app"]["assetlinks.json fingerprints differ from config.json"] += 1
mf_f = SITE / "manifest.json"
try: mf_ = json.loads(mf_f.read_text(encoding="utf-8")) if mf_f.is_file() else {}
except ValueError: mf_ = {}; fails["android app"]["manifest.json does not parse"] += 1
for k_ in ("name", "short_name", "start_url", "scope", "display", "background_color", "theme_color", "icons", "id", "description", "categories", "shortcuts", "screenshots"):
    if not mf_.get(k_): fails["android app"][f"manifest.json has no {k_}"] += 1
if mf_ and not {"business", "productivity"} <= set(mf_.get("categories") or []): fails["android app"]["manifest.json categories lack business and productivity"] += 1
if mf_ and not any(i_.get("sizes") == "512x512" and i_.get("type") == "image/png" for i_ in mf_.get("icons") or []): fails["android app"]["manifest.json has no 512x512 PNG icon"] += 1
sc_urls_ = [s_.get("url", "") for s_ in mf_.get("shortcuts") or []]
for want_ in ("/remote/", "/jobs-near-me/", "/new/", "/resume/"):
    if P + want_ not in sc_urls_: fails["android app"][f"manifest.json has no shortcut to {want_}"] += 1
for s_ in mf_.get("shortcuts") or []:
    if not (s_.get("name") and s_.get("icons")): fails["android app"]["a manifest shortcut without a name or an icon (Android skips it)"] += 1
    if not exists(s_.get("url", "")): fails["android app"][f"a manifest shortcut points to a page that was not built ({s_.get('url')})"] += 1
    for i_ in s_.get("icons") or []:
        if not exists(i_.get("src", "")): fails["android app"]["a shortcut icon that was not built"] += 1
shots_ = mf_.get("screenshots") or []
if mf_ and len([x_ for x_ in shots_ if x_.get("form_factor") == "narrow"]) < 4: fails["android app"]["manifest.json has fewer than 4 narrow screenshots"] += 1
for x_ in shots_:
    if not exists(x_.get("src", "")) or not re.fullmatch(r"\d+x\d+", x_.get("sizes", "")) or not x_.get("type"): fails["android app"][f"a manifest screenshot not built or without sizes/type ({x_.get('src')})"] += 1
# /privacy/ says what the MCP connector receives and keeps (27 Nov 2026, asked for by a connector directory review)
counts["privacy"] = 1
pv_f = SITE / "privacy" / "index.html"
pv_ = pv_f.read_text(encoding="utf-8", errors="replace") if pv_f.is_file() else ""
if 'id="mcp"' not in pv_ or "MCP connector" not in pv_: fails["privacy"]["no section on the MCP connector"] += 1
elif not all(w_ in pv_ for w_ in ("do not store those words", "read-only", "14 days")): fails["privacy"]["the MCP section lost what it receives, keeps or can do"] += 1
print(f"checked {len(sample)} pages ({len(others)} non-job pages, {len(sample) - len(others)} job pages sampled" + (", built from records" if STORE else "") + ")")
for t in sorted(counts):
    bad = fails[t]
    print(f"  {t:16s} {counts[t]:6d} pages   " + ("OK" if not bad else "; ".join(f"{k}: {v}" for k, v in bad.most_common())))
if broken:
    print("broken links (top):", broken.most_common(8))
sys.exit(1 if any(fails.values()) else 0)
