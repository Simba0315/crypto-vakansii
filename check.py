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
    if parts[0] in ("jobs", "remote", "skills", "locations", "crypto", "perks", "new", "entry-level", "with-salary", "contract", "part-time", "internships", "work-from-anywhere", "archive"):
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
                        r"(?:remote|entry-level|new|part-time|internships|with-salary|contract|hybrid|work-from-anywhere|tech)/)index\.html$")
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
# (the brand's name, its quoted logo words and the guide's address excepted; the footer is left to its own template).
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
print(f"checked {len(sample)} pages ({len(others)} non-job pages, {len(sample) - len(others)} job pages sampled" + (", built from records" if STORE else "") + ")")
for t in sorted(counts):
    bad = fails[t]
    print(f"  {t:16s} {counts[t]:6d} pages   " + ("OK" if not bad else "; ".join(f"{k}: {v}" for k, v in bad.most_common())))
if broken:
    print("broken links (top):", broken.most_common(8))
sys.exit(1 if any(fails.values()) else 0)
