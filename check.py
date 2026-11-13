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


def exists(href):
    path = href.split("#")[0].split("?")[0]
    if not path.startswith(P + "/"): return True
    rel = path[len(P) + 1:]
    t = SITE / rel
    return t.is_file() or (t / "index.html").is_file() or rel == ""


pages = [p for p in SITE.rglob("index.html")]
jobs = [p for p in pages if p.relative_to(SITE).parts[0] == "job"]
others = [p for p in pages if p.relative_to(SITE).parts[0] not in ("job", "embed")]
sample = others + random.sample(jobs, min(600, len(jobs)))
fails, counts, broken = defaultdict(Counter), Counter(), Counter()
for f in sample:
    rel = str(f.relative_to(SITE)); t = template(rel); counts[t] += 1
    h = f.read_text(encoding="utf-8", errors="replace")
    title = re.search(r"<title>(.*?)</title>", h, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', h)
    canon = re.search(r'<link rel="canonical" href="([^"]*)"', h)
    h1 = re.findall(r"<h1[\s>]", h)
    if len(h1) != 1: fails[t][f"h1 count {len(h1)}"] += 1
    if not title or not (10 <= len(html.unescape(title.group(1))) <= 75): fails[t]["title length outside 10-75"] += 1
    if not desc or not (70 <= len(html.unescape(desc.group(1))) <= 170): fails[t]["description length outside 70-170"] += 1
    want = FULL + "/" + ("" if rel == "index.html" else rel[:-len("index.html")])
    if not canon or canon.group(1) != want: fails[t]["canonical is not self"] += 1
    if 'lang="en"' not in h[:200]: fails[t]["no lang"] += 1
    heads = [int(x) for x in re.findall(r"<h([1-6])[\s>]", h.split("<footer")[0])]
    if any(b - a > 1 for a, b in zip(heads, heads[1:])): fails[t]["heading level skipped"] += 1
    if re.search(r"<img(?![^>]*\balt=)", h): fails[t]["img without alt"] += 1
    for href in set(re.findall(r'href="(/[^"]*)"', h)):
        if not exists(href):
            fails[t]["broken internal link"] += 1; broken[href] += 1
print(f"checked {len(sample)} pages ({len(others)} non-job pages, {len(sample) - len(others)} job pages sampled)")
for t in sorted(counts):
    bad = fails[t]
    print(f"  {t:16s} {counts[t]:6d} pages   " + ("OK" if not bad else "; ".join(f"{k}: {v}" for k, v in bad.most_common())))
if broken:
    print("broken links (top):", broken.most_common(8))
sys.exit(1 if any(fails.values()) else 0)
