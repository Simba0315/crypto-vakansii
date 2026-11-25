"""Check the built site against the page standard: one H1, title and description lengths, canonical, heading order, internal links.

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
print(f"checked {len(sample)} pages ({len(others)} non-job pages, {len(sample) - len(others)} job pages sampled" + (", built from records" if STORE else "") + ")")
for t in sorted(counts):
    bad = fails[t]
    print(f"  {t:16s} {counts[t]:6d} pages   " + ("OK" if not bad else "; ".join(f"{k}: {v}" for k, v in bad.most_common())))
if broken:
    print("broken links (top):", broken.most_common(8))
sys.exit(1 if any(fails.values()) else 0)
