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


pages = [p for p in SITE.rglob("index.html")]
jobs = [str(p.relative_to(SITE)) for p in pages if p.relative_to(SITE).parts[0] == "job"] or [f"job/{s}/index.html" for s in sorted(REC)]
others = [str(p.relative_to(SITE)) for p in pages if p.relative_to(SITE).parts[0] not in ("job", "embed")]
sample = others + random.sample(jobs, min(600, len(jobs)))
fails, counts, broken = defaultdict(Counter), Counter(), Counter()
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
    if not canon: fails[t]["canonical is not self"] += 1
    elif canon.group(1) != want:
        other = SITE / canon.group(1)[len(FULL) + 1:] / "index.html" if canon.group(1).startswith(FULL + "/") else None
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
    for href in set(re.findall(r'href="(/[^"]*)"', h)):
        if not exists(href):
            fails[t]["broken internal link"] += 1; broken[href] += 1
# every script the pages load must parse (20 Nov 2026: a stray "//" in assets/site.js left every script of the live site dead)
import shutil, subprocess                     # noqa: E402
if shutil.which("node"):
    for js in sorted(SITE.glob("*.js")):
        counts["scripts"] += 1
        if subprocess.run(["node", "--check", str(js)], capture_output=True).returncode: fails["scripts"][f"{js.name} does not parse"] += 1
# the XML feed for job search engines (job_feed.py, 26 Nov 2026): every file read back with a streaming parser, the fields of every
# job, no control characters, and the .gz copy unpacked and compared with the file
if (SITE / "feeds" / "index.xml").is_file():
    import job_feed
    counts["job feed"] = len(list((SITE / "feeds").glob("jobs-*.xml")))
    for p_ in job_feed.check(SITE / "feeds", FULL)[:20]: fails["job feed"][p_] += 1
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
print(f"checked {len(sample)} pages ({len(others)} non-job pages, {len(sample) - len(others)} job pages sampled" + (", built from records" if STORE else "") + ")")
for t in sorted(counts):
    bad = fails[t]
    print(f"  {t:16s} {counts[t]:6d} pages   " + ("OK" if not bad else "; ".join(f"{k}: {v}" for k, v in bad.most_common())))
if broken:
    print("broken links (top):", broken.most_common(8))
sys.exit(1 if any(fails.values()) else 0)
