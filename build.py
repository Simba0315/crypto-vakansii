"""Generate the static site into ./site from data/jobs.json (+ optional paid.json).

Closed jobs keep their pages forever (archive); only the JobPosting markup and the apply button are removed.
"""
import datetime, hashlib, html, json, re, shutil
from collections import Counter, defaultdict
from email.utils import format_datetime
from pathlib import Path
from collect import CATS, OTHER, slugify

ROOT = Path(__file__).parent
OUT = ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
SITE, BASE, P = CFG["site_name"], CFG["base_url"].rstrip("/"), CFG.get("base_path", "").rstrip("/")
FULL = BASE + P
TODAY = datetime.date.today().isoformat()
e = html.escape
CAT = {s: n for s, n, _ in CATS} | {OTHER[0]: OTHER[1]}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
TAG_SLUG = {"C++": "cpp", "C#": "csharp", ".NET": "dotnet", "Node.js": "nodejs", "AML/KYC": "aml-kyc"}
EUROPE = (r"europe|\bemea\b|\beu\b|london|united kingdom|\buk\b|paris|france|berlin|germany|vienna|austria|zurich|switzerland|\bzug\b|amsterdam|"
          r"netherlands|lisbon|portugal|madrid|barcelona|spain|dublin|ireland|warsaw|poland|vilnius|lithuania|malta|cyprus|italy|milan|prague|"
          r"czech|romania|bucharest|sweden|stockholm|luxembourg|belgium|brussels|estonia|tallinn|denmark|copenhagen")
PLACES = [
    ("Singapore", "singapore", r"singapore"), ("Hong Kong", "hong-kong", r"hong kong"),
    ("Dubai & UAE", "uae", r"dubai|abu dhabi|\buae\b|united arab emirates"),
    ("London & the UK", "united-kingdom", r"london|united kingdom|\buk\b|england"),
    ("New York", "new-york", r"new york|\bnyc\b"),
    ("San Francisco Bay Area", "san-francisco", r"san francisco|bay area|palo alto|san jose|mountain view"),
    ("the United States", "united-states", r"united states|\busa?\b|new york|san francisco|california|chicago|miami|texas|boston|seattle"),
    ("Canada", "canada", r"canada|toronto|vancouver"), ("Europe", "europe", EUROPE),
    ("Germany", "germany", r"germany|berlin|munich|frankfurt|hamburg"), ("France", "france", r"france|paris"),
    ("Switzerland", "switzerland", r"switzerland|zurich|\bzug\b|geneva"), ("Austria", "austria", r"austria|vienna"),
    ("Poland", "poland", r"poland|warsaw|krakow"), ("Malaysia", "malaysia", r"malaysia|kuala lumpur"),
    ("the Philippines", "philippines", r"philippines|manila"), ("India", "india", r"\bindia\b|bangalore|bengaluru|mumbai|hyderabad"),
    ("Japan", "japan", r"japan|tokyo"), ("South Korea", "south-korea", r"korea|seoul"), ("Taiwan", "taiwan", r"taiwan|taipei"),
    ("Australia", "australia", r"australia|sydney|melbourne"),
    ("Asia-Pacific", "asia-pacific", r"\bapac\b|asia|singapore|hong kong|malaysia|philippines|taiwan|japan|korea|india|vietnam|thailand|indonesia|australia"),
    ("Latin America", "latin-america", r"latam|latin america|brazil|mexico|argentina|colombia|chile"),
    ("Brazil", "brazil", r"brazil|s[ãa]o paulo"), ("Turkey", "turkey", r"turkey|türkiye|istanbul"),
    ("Africa", "africa", r"africa|nigeria|kenya|lagos|nairobi"),
]
URLS = []
V = hashlib.md5(b"".join((ROOT / "assets" / f).read_bytes() for f in ("style.css", "site.js", "app.js"))).hexdigest()[:8]   # cache-busting version
MINI_FOOT = (f'<footer class="mini"><div class="wrap"><p class="fine">© {TODAY[:4]} {e(SITE)} · <a href="{P}/jobs/">All jobs</a> · <a href="{P}/remote/">Remote</a> · '
             f'<a href="{P}/companies/">Companies</a> · <a href="{P}/salaries/">Salaries</a> · <a href="{P}/post-a-job/">Post a job</a> · <a href="{P}/about/">About</a></p></div></footer>')
SAL_BAD = re.compile(r"CA\$|C\$|A\$|AU\$|S\$|SG\$|HK\$|NZ\$|CAD|AUD|SGD|EUR|GBP|CHF|JPY|INR|€|£|¥|₹", re.I)
SAL_NUM = re.compile(r"(\d[\d,\. ]*\d|\d)\s?([kK])?")


def usd_range(s):
    """Annual USD (low, high) from a salary string, or None if it is not a plain US-dollar yearly range."""
    if not s or SAL_BAD.search(s) or ("$" not in s and "USD" not in s.upper()) or re.search(r"hour|/hr|per hr|hourly", s, re.I):
        return None
    vals = []
    for num, k in SAL_NUM.findall(s):
        try:
            v = float(num.replace(",", "").replace(" ", ""))
        except ValueError:
            continue
        vals.append(v * 1000 if k else v)
    if len(vals) < 2: return None
    lo, hi = vals[0], vals[1]
    return (lo, hi) if 30000 <= lo <= hi <= 1500000 else None


def money(v):
    return f"${v / 1000:,.0f}K"


def median(xs):
    xs = sorted(xs); n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
FOOT = {"cats": ""}
SIM = {"cat": {}, "comp": {}}
OPEN = Counter()   # open roles per company
MARK = ('<rect width="32" height="32" rx="9" fill="url(#lg)"/><rect x="8" y="9" width="16" height="3" rx="1.5" fill="#fff"/>'
        '<rect x="8" y="14.5" width="11" height="3" rx="1.5" fill="#fff" opacity=".85"/><rect x="8" y="20" width="7" height="3" rx="1.5" fill="#fff" opacity=".7"/>')
GRAD = '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#9333ea"/></linearGradient></defs>'
LOGO = f'<svg viewBox="0 0 32 32" aria-hidden="true">{GRAD}{MARK}</svg>'
ICON_THEME = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 0 0 16z" fill="currentColor" stroke="none"/></svg>'
ICON_MENU = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
ICON_SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'


def fdate(iso, year=True):
    try:
        y, m, d = (int(x) for x in iso[:10].split("-"))
        return f"{MONTHS[m - 1]} {d}, {y}" if year else f"{MONTHS[m - 1]} {d}"
    except Exception:
        return ""


def roles(n, word="job"):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def hue(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:6], 16) % 360


def ava(name, cls=""):
    letter = next((c for c in name if c.isalnum()), "?").upper()
    return f'<span class="ava{" " + cls if cls else ""}" style="--h:{hue(name)}" aria-hidden="true">{e(letter)}</span>'


def write(path, content, sitemap=True):
    f = OUT / path / "index.html" if not path.endswith((".html", ".xml", ".txt", ".json", ".svg")) else OUT / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    if sitemap:
        URLS.append(path)


def page(path, title, desc, body, head="", sitemap=True, hero="", compact=False):
    url = f"{FULL}/{path}"
    write(path, f"""<!doctype html>
<html lang="en" data-base="{P}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="{e(SITE)}">
<meta name="twitter:card" content="summary"><meta name="theme-color" content="#4f46e5">
<link rel="icon" type="image/svg+xml" href="{P}/favicon.svg">
<link rel="alternate" type="application/rss+xml" title="{e(SITE)} — latest jobs" href="{P}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{P}/style.css?v={V}"><script>try{{var t=localStorage.getItem("hrn_theme");if(t)document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script><script src="{P}/site.js?v={V}" defer></script>{head}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><nav id="nav">
<a class="nl" href="{P}/jobs/">Jobs</a><a class="nl" href="{P}/remote/">Remote</a><a class="nl" href="{P}/new/">New</a><a class="nl" href="{P}/companies/">Companies</a><a class="nl" href="{P}/salaries/">Salaries</a><a class="nl" href="{P}/my-jobs/">My jobs<span id="saved-n"></span></a><a class="nl plus" href="{P}/plus/">Plus</a><a class="nl only-m" href="{P}/post-a-job/">Post a job</a></nav>
<div class="hact"><button class="icon" id="theme" type="button" aria-label="Switch between light and dark">{ICON_THEME}</button><a class="btn" href="{P}/post-a-job/">Post a job</a>
<button class="icon burger" id="menu" type="button" aria-label="Menu" aria-expanded="false">{ICON_MENU}</button></div></div></header>
{hero}<main class="wrap">{body}</main>
{MINI_FOOT if compact else FULL_FOOT()}
</body></html>""", sitemap)


def FULL_FOOT():
    return f"""<footer><div class="wrap"><div class="fcols">
<div><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><p>Every open role at tech companies, pulled from their official careers pages and refreshed daily.</p></div>
<div><h4>Browse</h4><ul><li><a href="{P}/jobs/">All jobs</a></li><li><a href="{P}/remote/">Remote jobs</a></li><li><a href="{P}/entry-level/">Entry-level</a></li><li><a href="{P}/new/">New this week</a></li><li><a href="{P}/my-jobs/">My jobs</a></li><li><a href="{P}/plus/">Plus</a></li><li><a href="{P}/with-salary/">Salary listed</a></li><li><a href="{P}/salaries/">Salaries</a></li><li><a href="{P}/crypto/">Crypto &amp; web3 jobs</a></li><li><a href="{P}/companies/">Companies</a></li><li><a href="{P}/locations/">Locations</a></li></ul></div>
<div><h4>Categories</h4><ul>{FOOT["cats"]}</ul></div>
<div><h4>Employers</h4><ul><li><a href="{P}/post-a-job/">Post a job</a></li><li><a href="{P}/hiring-badge/">Hiring badge &amp; widget</a></li><li><a href="{P}/feed.xml">RSS feed</a></li><li><a href="{P}/archive/">Closed jobs archive</a></li><li><a href="{P}/about/">About</a></li></ul></div>
</div><p class="fine">© {TODAY[:4]} {e(SITE)}. Listings come from companies' official careers pages. You always apply on the employer's own site.</p></div></footer>"""


def card(j):
    b = []
    if j["featured"]: b.append('<span class="pill acc">Featured</span>')
    if not j["active"]: b.append('<span class="pill">Closed</span>')
    if j["remote"]: b.append('<span class="pill ok">Remote</span>')
    if j["salary"]: b.append(f'<span class="pill sal">{e(j["salary"][:28])}</span>')
    if j["level"]: b.append(f'<span class="pill">{e(j["level"])}</span>')
    b += [f'<span class="pill">{e(t)}</span>' for t in j["tags"][:3]]
    loc = j["location"] if len(j["location"]) <= 60 else j["location"][:57].rstrip(" ,;") + "…"
    sub = e(j["company"]) + (f" · {e(loc)}" if loc else "")
    return (f'<li class="job{" feat" if j["featured"] else ""}"><a href="{P}/job/{j["slug"]}/">{ava(j["company"])}'
            f'<span><span class="jt">{e(j["title"])}</span><span class="js">{sub}</span></span>'
            f'<span class="jr"><span class="pills">{"".join(b)}</span><time datetime="{j["posted"]}">{fdate(j["posted"], False)}</time></span></a></li>')


def tile(url, name, count, avatar=False):
    return f'<li><a class="tile" href="{P}/{url}">{ava(name, "sm") if avatar else ""}<span class="n">{e(name)}</span><span class="c">{count:,}</span></a></li>'


def section(title, inner, link=None):
    more = f'<a href="{P}/{link[0]}">{e(link[1])} →</a>' if link else ""
    return f'<section class="sec"><div class="sec-head"><h2>{e(title)}</h2>{more}</div>{inner}</section>'


def order(jobs):
    return sorted(jobs, key=lambda j: (not j["featured"], -int((j["posted"] or j["first_seen"]).replace("-", "") or 0)))


def diverse(jobs, k, per=2):
    """First k jobs with at most `per` from the same company, so one big employer does not fill a list."""
    seen, out = Counter(), []
    for j in jobs:
        if seen[j["company"]] < per:
            seen[j["company"]] += 1; out.append(j)
            if len(out) == k: break
    return out


def diverse_pairs(pairs, k, per=2):
    seen, out = Counter(), []
    for j, r in pairs:
        if seen[j["company"]] < per:
            seen[j["company"]] += 1; out.append((j, r))
            if len(out) == k: break
    return out


def crumbs(*parts):
    items = [f'<a href="{P}/">Home</a>'] + [f'<a href="{P}/{u}">{e(n)}</a>' if u else e(n) for n, u in parts]
    return f'<div class="crumbs">{" / ".join(items)}</div>'


def rss(path, title, link, jobs):
    now = format_datetime(datetime.datetime.now(datetime.timezone.utc))
    items = "".join(
        f"<item><title>{e(j['title'])} at {e(j['company'])}</title><link>{FULL}/job/{j['slug']}/</link><guid>{FULL}/job/{j['slug']}/</guid>"
        f"<description>{e(((j['location'] + '. ') if j['location'] else '') + j['excerpt'])}</description></item>" for j in order(jobs)[:100])
    write(path, f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{e(title)}</title><link>{FULL}/{link}</link>'
                f"<description>{e(title)}</description><lastBuildDate>{now}</lastBuildDate>{items}</channel></rss>", sitemap=False)


def pager_html(path, n, pages):
    if pages <= 1: return ""
    url = lambda i: f'{P}/{path}{"" if i == 1 else f"{i}/"}'
    keep = sorted({1, pages} | {i for i in range(n - 2, n + 3) if 1 <= i <= pages})
    out, prev = [], 0
    if n > 1: out.append(f'<a rel="prev" href="{url(n - 1)}">← Prev</a>')
    for i in keep:
        if i - prev > 1: out.append("<span>…</span>")
        out.append(f"<b>{i}</b>" if i == n else f'<a href="{url(i)}">{i}</a>')
        prev = i
    if n < pages: out.append(f'<a rel="next" href="{url(n + 1)}">Next →</a>')
    return f'<div class="pager">{"".join(out)}</div>'


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra="", feed=False, head_html=None, after=""):
    jobs = order(jobs)
    pages = max(1, -(-len(jobs) // per))
    if feed: rss(f"{path}feed.xml", f"{h1} — {SITE}", path, jobs)
    for n in range(1, pages + 1):
        chunk = jobs[(n - 1) * per:n * per]
        top = head_html if head_html is not None else (crumbs(*trail, (h1, "")) + f"<h1>{e(h1)}</h1>" + (f'<p class="lead">{intro}</p>' if intro and n == 1 else ""))
        body = (top + (extra if n == 1 else "")
                + (f'<ul class="jobs">{"".join(card(j) for j in chunk)}</ul>' if chunk else '<p class="lead">Nothing here right now. Check back soon: the list is updated every day.</p>')
                + pager_html(path, n, pages) + (after if n == 1 else ""))
        page(path if n == 1 else f"{path}{n}/", title if n == 1 else f"{title} — page {n}", desc, body)


def intro_for(jobs, pre="", post=""):
    if not jobs: return ""
    r = sum(j["remote"] for j in jobs)
    top = ", ".join(c for c, _ in Counter(j["company"] for j in jobs).most_common(5))
    return (f"{roles(len(jobs), 'open ' + pre + 'role')}{post}. Hiring the most right now: {e(top)}. "
            + (f"{r:,} of them {'is' if r == 1 else 'are'} remote. " if 0 < r < len(jobs) else "") + "Updated daily.")


def job_page(j, active_by_cat):
    canonical = f"{FULL}/job/{j['slug']}/"
    comp_url = f'{P}/companies/{slugify(j["company"])}/'
    rows = [("Company", f'<a href="{comp_url}">{e(j["company"])}</a>')]
    if j["location"]: rows.append(("Location", e(j["location"])))
    if j["remote"]: rows.append(("Workplace", "Remote"))
    rows.append(("Category", f'<a href="{P}/jobs/{j["cat"]}/">{e(CAT[j["cat"]])}</a>'))
    if j["level"]: rows.append(("Level", e(j["level"])))
    if j["salary"]: rows.append(("Salary", e(j["salary"])))
    if j["posted"]: rows.append(("Posted", fdate(j["posted"])))
    meta = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    pills = []
    if not j["active"]: pills.append('<span class="pill">Closed</span>')
    if j["remote"]: pills.append('<span class="pill ok">Remote</span>')
    if j["salary"]: pills.append(f'<span class="pill sal">{e(j["salary"])}</span>')
    if j["level"]: pills.append(f'<span class="pill">{e(j["level"])}</span>')
    pills += [f'<a class="pill" href="{P}/skills/{TAG_SLUG.get(t, slugify(t))}/">{e(t)}</a>' for t in j["tags"]]
    head = ""
    if j["active"]:
        ld = {"@context": "https://schema.org", "@type": "JobPosting", "title": j["title"], "description": j["excerpt"] or j["title"],
              "datePosted": j["posted"] or j["first_seen"], "hiringOrganization": {"@type": "Organization", "name": j["company"]},
              "directApply": False, "url": canonical}
        if j["location"]:
            ld["jobLocation"] = {"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": j["location"]}}
        if j["remote"]:
            ld["jobLocationType"] = "TELECOMMUTE"
        head = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>"
        apply_btn = (f'<a class="btn primary lg" id="apply" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Apply on company site</a>'
                     '<p class="note" id="apply-hint" hidden>Applied? Mark it below to keep track of it in My jobs.</p>')
        banner = ""
    else:
        apply_btn = f'<a class="btn lg" href="{P}/jobs/{j["cat"]}/">See open {e(CAT[j["cat"]])} jobs</a>'
        banner = f'<div class="banner">This job is closed{" as of " + fdate(j["closed"]) if j.get("closed") else ""}. The company is no longer accepting applications. Use the button on this page to see open roles in the same category.</div>'
    same = [x for x in SIM["comp"].get((j["company"], j["cat"]), []) if x["id"] != j["id"]][:2]
    rest = [x for x in SIM["cat"].get(j["cat"], []) if x["id"] != j["id"] and x["company"] != j["company"]][:4 - len(same)]
    similar = same + rest if j["active"] else []   # closed jobs stay light: the archive only grows
    sim = section("Similar jobs", f'<ul class="jobs">{"".join(card(x) for x in similar)}</ul>', (f"jobs/{j['cat']}/", f"All {CAT[j['cat']]} jobs")) if similar else ""
    about = (f'<h2>About the role</h2><div class="prose"><p>{e(j["excerpt"])}</p></div><p class="note">Excerpt from the original posting.</p>'
             if j["excerpt"] else "")
    data = f'data-slug="{j["slug"]}" data-title="{e(j["title"])}" data-company="{e(j["company"])}"'
    more_roles = OPEN[j["company"]] - (1 if j["active"] else 0)
    glance = (f'<p class="note"><a href="{comp_url}">{roles(more_roles, "more open role")} at {e(j["company"])} →</a></p>' if more_roles > 0 else "")
    save_btn = ((f'<div class="sideact"><button class="btn ghost" id="save" type="button" {data}>Save job</button>'
                 f'<button class="btn ghost" id="applied" type="button">Mark as applied</button></div>'
                 f'<p class="note">Applying is free and happens on the employer\'s own page. <button class="linkbtn" id="copy" type="button">Copy link</button></p>') if j["active"] else "") + glance
    loc = f" · {e(j['location'])}" if j["location"] else ""
    body = (crumbs((CAT[j["cat"]], f"jobs/{j['cat']}/"), (j["title"], ""))
            + f'<div class="jhead">{ava(j["company"], "lg")}<div><h1>{e(j["title"])}</h1><span class="js"><a href="{comp_url}">{e(j["company"])}</a>{loc}</span>'
            + f'<div class="pills">{"".join(pills)}</div></div></div>{banner}'
            + f'<div class="cols"><article>{about}{sim}</article><aside class="side card"><dl class="meta">{meta}</dl>{apply_btn}{save_btn}</aside></div>')
    where = j["location"] or ("Remote" if j["remote"] else "")
    title = f"{j['title']} at {j['company']}" + (" (closed)" if not j["active"] else "")
    desc = (f"{j['title']} at {j['company']}" + (f" — {where}" if where else "") + f". {CAT[j['cat']]} role"
            + (", remote" if j["remote"] else "") + (". This job is closed." if not j["active"] else ". Apply on the company site."))
    page(f"job/{j['slug']}/", title, desc, body, head, compact=True)


def embed_code(slug):
    return e(f'<script src="{FULL}/embed.js" data-company="{slug}" async></script>')


def badge_code(slug=None):
    url = f"{FULL}/companies/{slug}/" if slug else f"{FULL}/"
    return e(f'<a href="{url}"><img src="{FULL}/hiring-badge.svg" alt="We\'re hiring — see our open roles on {SITE}" width="220" height="48"></a>')


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    db = json.loads((ROOT / "data" / "jobs.json").read_text())
    jobs = list(db.values())
    paid_file = ROOT / "paid.json"  # employer-submitted listings, kept in the main branch
    for p in (json.loads(paid_file.read_text()) if paid_file.exists() else []):
        base = f"{slugify(p['title'])}-{slugify(p['company'])}"
        jobs.append({"id": "paid-" + base, "slug": base, "location": "", "remote": False, "dept": "", "excerpt": "", "level": "", "tags": [],
                     "russian": False, "salary": "", "posted": TODAY, "first_seen": TODAY, "cat": OTHER[0],
                     "active": p.get("expires", "9999") >= TODAY, **p})
    for j in jobs:
        j["featured"] = bool(j.get("featured_until", "") >= TODAY and j["active"])
        if j["location"].lower() in {"n/a", "na", "none", "tbd", "-", "null", "not specified"}: j["location"] = ""
        j["entry"] = j["level"] in ("Junior", "Intern")
        j["usd"] = usd_range(j["salary"])
        j["places"] = [slug for _, slug, rx in PLACES if re.search(rx, j["location"], re.I)] if j["active"] else []
    active = [j for j in jobs if j["active"]]
    archived = [j for j in jobs if not j["active"]]
    by_cat = defaultdict(list)
    for j in active: by_cat[j["cat"]].append(j)
    companies = defaultdict(list)
    for j in jobs: companies[j["company"]].append(j)
    n, m = len(active), len({j["company"] for j in active})
    remote = [j for j in active if j["remote"]]
    places = [(name, slug, js) for name, slug, rx in PLACES if len(js := [j for j in active if slug in j["places"]]) >= 5]
    OPEN.update(Counter(j["company"] for j in active))
    top_cats = sorted((s for s in CAT if by_cat[s] and s != OTHER[0]), key=lambda s: -len(by_cat[s]))
    FOOT["cats"] = "".join(f'<li><a href="{P}/jobs/{s}/">{e(CAT[s])}</a></li>' for s in top_cats[:6])
    comp_items = sorted(companies.items(), key=lambda kv: -sum(j["active"] for j in kv[1]))
    for s in CAT:
        SIM["cat"][s] = diverse(order(by_cat[s]), 12)
    by_comp_cat = defaultdict(list)
    for j in order(active):
        if len(by_comp_cat[(j["company"], j["cat"])]) < 4: by_comp_cat[(j["company"], j["cat"])].append(j)
    SIM["comp"] = by_comp_cat
    latest = diverse(order(active), 40)

    # Home
    cats = "".join(tile(f"jobs/{s}/", CAT[s], len(by_cat[s])) for s in CAT if by_cat[s])
    place_html = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in places)
    comp_top = "".join(tile(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js), True) for c, js in comp_items[:12])
    hero = (f'<section class="hero"><div class="wrap"><p class="eyebrow"><i></i>Updated daily from official careers pages</p>'
            f'<h1>Find your next role in <span class="grad">tech</span></h1>'
            f'<p class="sub">{roles(n, "open role")} at {m} companies — software, AI, fintech, crypto and more. Straight from company career pages, no sign-up.</p>'
            f'<form class="searchbar" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Job title, skill or company" aria-label="Search jobs"><button class="btn primary">Search jobs</button></form>'
            f'<div class="popular"><span>Popular:</span><a href="{P}/remote/">Remote</a><a href="{P}/skills/python/">Python</a><a href="{P}/skills/rust/">Rust</a><a href="{P}/crypto/">Crypto</a>'
            f'<a href="{P}/entry-level/">Entry-level</a><a href="{P}/with-salary/">Salary listed</a></div>'
            f'<dl class="stats"><div><dt>{n:,}</dt><dd>open roles</dd></div><div><dt>{m}</dt><dd>companies</dd></div>'
            f'<div><dt>{len(remote):,}</dt><dd>remote</dd></div><div><dt>{sum(bool(j["salary"]) for j in active):,}</dt><dd>with salary</dd></div></dl></div></section>')
    plus_band = (f'<div class="band alt"><div><h2>Looking for a job right now?</h2><p>Plus will show you new roles 48 hours early, email you matches instantly and review your résumé. One payment, no subscription.</p></div>'
                 f'<a class="btn lg" href="{P}/plus/">See Plus</a></div>')
    band = (f'<div class="band"><div><h2>Hiring for your team?</h2><p>Standard listings are free. Featured placement starts at $99, paid in USDT, BTC or ETH.</p></div>'
            f'<a class="btn lg" href="{P}/post-a-job/">Post a job</a></div>')
    home = (section("Latest jobs", f'<ul class="jobs">{"".join(card(j) for j in latest[:12])}</ul>', ("jobs/", f"Browse all {n:,}"))
            + section("Browse by category", f'<ul class="tiles">{cats}</ul>')
            + section("Top companies hiring", f'<ul class="tiles">{comp_top}</ul>', ("companies/", f"All {len(companies)} companies")) + plus_band
            + section("Jobs by location", f'<ul class="tiles">{place_html}</ul>', ("locations/", "All locations")) + band
            + section("More recent jobs", f'<ul class="jobs">{"".join(card(j) for j in latest[12:40])}</ul>', ("jobs/", f"Browse all {n:,}")))
    page("", f"Tech Jobs — {roles(n, 'open role')} at {m} companies | {SITE}",
         f"{roles(n)} at tech companies: engineering, marketing, compliance, support and more. Remote filters, salary data, updated daily.", home, hero=hero)
    rss("feed.xml", f"{SITE} — latest tech jobs", "", active)

    # Search page
    opts = "".join(f'<option value="{s}">{e(CAT[s])}</option>' for s in CAT if by_cat[s])
    loc_opts = "".join(f'<option value="{slug}">{e(name.removeprefix("the "))}</option>' for name, slug, _ in places)
    top_skills = [t for t, _ in Counter(t for j in active for t in j["tags"]).most_common(18)]
    skill_chips = "".join(f'<button class="chipbtn" type="button" data-skill="{e(t)}" aria-pressed="false">{e(t)}</button>' for t in top_skills)
    search = (crumbs(("All jobs", "")) + "<h1>Search tech jobs</h1>"
              f'<div id="search"><form class="searchbar wide" id="qform">{ICON_SEARCH}<input type="search" id="q" placeholder="Job title, skill or company" aria-label="Search jobs" autocomplete="off"><button class="btn primary">Search</button></form>'
              f'<div class="fbar"><select id="cat" aria-label="Category"><option value="">All categories</option>{opts}</select>'
              '<select id="lvl" aria-label="Level"><option value="">Any level</option><option>Intern</option><option>Junior</option><option>Senior</option><option>Lead</option></select>'
              f'<select id="loc" aria-label="Location"><option value="">Anywhere</option>{loc_opts}</select>'
              '<select id="sal" aria-label="Salary"><option value="">Any salary</option><option value="1">Salary listed</option><option value="100000">$100K+</option>'
              '<option value="150000">$150K+</option><option value="200000">$200K+</option><option value="300000">$300K+</option></select>'
              '<select id="sort" aria-label="Sort"><option value="new">Newest first</option><option value="sal">Highest salary</option></select></div>'
              '<div class="filters"><label><input type="checkbox" id="f-remote"> Remote</label><label><input type="checkbox" id="f-entry"> Entry-level</label>'
              '<label><input type="checkbox" id="f-crypto"> Crypto &amp; web3</label></div>'
              f'<div class="skillbar" id="skills">{skill_chips}</div>'
              '<div class="rbar"><p class="note" id="count">Loading…</p><button class="btn ghost sm" id="save-search" type="button">Save this search</button></div>'
              '<ul class="jobs" id="results"></ul><p><button class="btn" id="more" type="button" hidden>Show more</button></p></div>'
              f'<noscript><p>Search needs JavaScript. Browse by category instead:</p><ul class="tiles">{cats}</ul></noscript><script src="{P}/app.js?v={V}" defer></script>')
    page("jobs/", f"Search {roles(n, 'Tech Job')} | {SITE}",
         "Search tech jobs by title, skill or company. Filter by level, location, salary and remote, sort by pay, and save your searches.", search)

    # Listings
    for s, name in CAT.items():
        js = by_cat[s]
        if not js: continue
        listing(f"jobs/{s}/", f"{name} jobs in tech", f"{name} Jobs in Tech ({len(js):,} open) | {SITE}",
                f"{roles(len(js), name + ' job')} at tech companies. Remote and on-site roles, updated daily.",
                js, intro_for(js, f"{e(name)} "), trail=(("All jobs", "jobs/"),), feed=True)
        rj = [j for j in js if j["remote"]]
        if len(rj) >= 5:
            listing(f"remote/{s}/", f"Remote {name} jobs in tech", f"Remote {name} Jobs in Tech ({len(rj):,} open) | {SITE}",
                    f"{roles(len(rj), 'remote ' + name + ' job')} at tech companies. Work from anywhere, updated daily.",
                    rj, intro_for(rj, f"remote {e(name)} "), trail=(("Remote", "remote/"),))
    rcats = "".join(tile(f"remote/{s}/", CAT[s], c) for s in CAT if (c := sum(j["remote"] for j in by_cat[s])) >= 5)
    listing("remote/", "Remote tech jobs", f"Remote Tech Jobs — {roles(len(remote), 'open role')} | {SITE}",
            f"{roles(len(remote), 'remote job')} at tech companies: engineering, marketing, support, compliance and more.",
            remote, intro_for(remote, "remote "), extra=f'<ul class="tiles">{rcats}</ul><div class="sec"><div class="sec-head"><h2>All remote jobs</h2></div></div>', feed=True)
    crypto = [j for j in active if j.get("crypto")]
    if crypto:
        ccats = "".join(tile(f"crypto/{s}/", CAT[s], c) for s in CAT if (c := sum(1 for j in crypto if j["cat"] == s)) >= 5)
        listing("crypto/", "Crypto & web3 jobs", f"Crypto & Web3 Jobs — {roles(len(crypto), 'open role')} | {SITE}",
                f"{roles(len(crypto))} at crypto and web3 companies: exchanges, wallets, blockchain infrastructure and DeFi. Updated daily.",
                crypto, intro_for(crypto, "", " at crypto and web3 companies"),
                extra=f'<ul class="tiles">{ccats}</ul><div class="sec"><div class="sec-head"><h2>All crypto &amp; web3 jobs</h2></div></div>', feed=True)
        for s, name in CAT.items():
            cj = [j for j in crypto if j["cat"] == s]
            if len(cj) >= 5:
                listing(f"crypto/{s}/", f"{name} jobs in crypto & web3", f"{name} Jobs in Crypto & Web3 ({len(cj):,} open) | {SITE}",
                        f"{roles(len(cj), name + ' job')} at crypto and web3 companies. Remote and on-site roles, updated daily.",
                        cj, intro_for(cj, f"{e(name)} ", " at crypto and web3 companies"), trail=(("Crypto & web3", "crypto/"),))
        cr = [j for j in crypto if j["remote"]]
        if len(cr) >= 5:
            listing("crypto/remote/", "Remote crypto & web3 jobs", f"Remote Crypto Jobs — {roles(len(cr), 'open role')} | {SITE}",
                    f"{roles(len(cr), 'remote job')} at crypto and web3 companies. Work from anywhere, updated daily.",
                    cr, intro_for(cr, "remote ", " at crypto and web3 companies"), trail=(("Crypto & web3", "crypto/"),))
    sal = [j for j in active if j["salary"]]
    listing("with-salary/", "Tech jobs with salary listed", f"Tech Jobs With Salary Listed ({len(sal):,}) | {SITE}",
            "Tech jobs where the employer publishes the salary range up front.", sal, intro_for(sal, "", " with a published salary range"))
    jr = [j for j in active if j["entry"]]
    listing("entry-level/", "Entry-level tech jobs & internships", f"Entry-Level Tech Jobs & Internships ({len(jr):,}) | {SITE}",
            "Internships and junior roles at tech companies: a way into the industry without years of experience.", jr,
            intro_for(jr, "entry-level "))
    by_tag = defaultdict(list)
    for j in active:
        for t in j["tags"]: by_tag[t].append(j)
    for t, js in by_tag.items():
        listing(f"skills/{TAG_SLUG.get(t, slugify(t))}/", f"{t} jobs in tech", f"{t} Jobs in Tech ({len(js):,} open) | {SITE}",
                f"{roles(len(js))} at tech companies that ask for {t}.", js, intro_for(js, "", f" mentioning {e(t)}"))
    for name, slug, js in places:
        short = name.removeprefix("the ")
        listing(f"locations/{slug}/", f"Tech jobs in {name}", f"Tech Jobs in {short} ({len(js):,} open) | {SITE}",
                f"{roles(len(js), 'tech job')} in {name}. Startups and established tech companies hiring now.",
                js, intro_for(js, "", f" in {e(name)}"), trail=(("Locations", "locations/"),))
    page("locations/", f"Tech Jobs by Location | {SITE}", "Browse tech jobs by city, country and region.",
         crumbs(("Locations", "")) + f'<h1>Tech jobs by location</h1><p class="lead">Open roles per place. A job that lists several locations appears in each of them.</p><ul class="tiles">{place_html}</ul>')

    # Companies (+ per-company data for the embeddable widget)
    grid = "".join(tile(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js), True) for c, js in comp_items)
    page("companies/", f"Tech Companies Hiring Now — {len(companies)} employers | {SITE}",
         "Tech companies with open roles: startups, scale-ups and public companies across software, AI, fintech and crypto.",
         crumbs(("Companies", "")) + f'<h1>Tech companies hiring now</h1><p class="lead">{len(companies)} employers. The number is their current open roles.</p><ul class="tiles">{grid}</ul>')
    for c, js in companies.items():
        slug = slugify(c)
        act, arc = order([j for j in js if j["active"]]), order([j for j in js if not j["active"]])
        write(f"data/companies/{slug}.json", json.dumps({
            "company": c, "site": SITE, "page": f"{FULL}/companies/{slug}/", "total": len(act),
            "jobs": [{"title": j["title"], "url": f"{FULL}/job/{j['slug']}/", "location": j["location"], "remote": j["remote"]} for j in act[:50]],
        }, ensure_ascii=False, separators=(",", ":")), sitemap=False)
        sal_mid = [(lo + hi) / 2 for j in act if j["usd"] for lo, hi in [j["usd"]]]
        top_cats = Counter(CAT[j["cat"]] for j in act).most_common(3)
        chips = [f"<span class='chip'><b>{len(act):,}</b> open roles</span>", f"<span class='chip'><b>{sum(j['remote'] for j in act):,}</b> remote</span>"]
        if len(sal_mid) >= 3: chips.append(f"<span class='chip'><b>{money(median(sal_mid))}</b> median advertised salary</span>")
        chips += [f"<span class='chip'><b>{k}</b> {e(name)}</span>" for name, k in top_cats]
        lead = (f"{roles(len(act), 'open role')} at {e(c)}, updated daily." if act else "No open roles right now. Past openings are below.")
        closed = section(f"Closed jobs at {c}", f'<ul class="jobs">{"".join(card(j) for j in arc[:200])}</ul>') if arc else ""
        embed = (f'<details class="embed"><summary>Work at {e(c)}? Show these jobs on your own site</summary>'
                 f'<p class="note">Paste this where the list should appear. It stays in sync automatically.</p><pre><code>{embed_code(slug)}</code></pre>'
                 f'<p class="note">Or add a hiring badge that links here:</p><pre><code>{badge_code(slug)}</code></pre></details>')
        head_html = (crumbs(("Companies", "companies/"), (c, ""))
                     + f'<div class="jhead">{ava(c, "lg")}<div><h1>Jobs at {e(c)}</h1><span class="js">{lead}</span>'
                     + (f'<div class="chips">{"".join(chips)}</div>' if act else "") + "</div></div>")
        listing(f"companies/{slug}/", f"Jobs at {c}", f"{c} Jobs — {roles(len(act), 'open role')} | {SITE}",
                f"All jobs at {c}: {len(act):,} open" + (f" and {len(arc):,} closed" if arc else "") + ". Categories, locations and remote roles.",
                act, head_html=head_html, after=closed + embed)

    # Job pages + archive
    for j in jobs: job_page(j, by_cat)
    listing("archive/", "Closed tech jobs archive", f"Closed Tech Jobs Archive ({len(archived):,}) | {SITE}",
            "Closed jobs at tech companies: see which roles teams were hiring for and when.", archived,
            "Closed jobs stay here so you can see which roles companies were hiring for in the past.")

    # New jobs
    cutoff = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    fresh = [j for j in active if (j["posted"] or "") >= cutoff]
    listing("new/", "New tech jobs", f"New Tech Jobs — {roles(len(fresh), 'role')} posted in the last 3 days | {SITE}",
            f"{roles(len(fresh), 'tech job')} posted in the last three days. Be among the first to apply.",
            fresh, intro_for(fresh, "", " posted in the last three days"), feed=True)

    # Salaries
    paid = [(j, j["usd"]) for j in active if j["usd"]]
    def table(groups, link=None, minimum=15, top=40):  # median salary per group
        rows_ = sorted(((k, median([(lo + hi) / 2 for _, (lo, hi) in v]), len(v)) for k, v in groups.items() if len(v) >= minimum), key=lambda r: -r[1])[:top]
        name = lambda k: ('<a href="' + P + "/" + link(k) + '">' + e(k) + "</a>") if link else e(k)
        body_ = "".join(f"<tr><td>{name(k)}</td><td><strong>{money(m_)}</strong></td><td>{c:,}</td></tr>" for k, m_, c in rows_)
        return f'<div class="tablewrap"><table><tr><th>Name</th><th>Median salary</th><th>Roles counted</th></tr>{body_}</table></div>'
    g_cat, g_tag, g_comp = defaultdict(list), defaultdict(list), defaultdict(list)
    for j, r in paid:
        g_cat[CAT[j["cat"]]].append((j, r)); g_comp[j["company"]].append((j, r))
        for t in j["tags"]: g_tag[t].append((j, r))
    cat_slug = {v: k for k, v in CAT.items()}
    best = sorted(paid, key=lambda x: -x[1][1])
    page("salaries/", f"Tech Salaries From Live Job Postings ({len(paid):,} roles) | {SITE}",
         "Median salaries in tech by role, skill and company, calculated from salary ranges in open job postings. Updated daily.",
         crumbs(("Salaries", "")) + "<h1>Tech salaries from live job postings</h1>"
         f'<p class="lead">Based on {len(paid):,} open roles that publish a yearly US-dollar range. Each figure is the median of the range midpoints. These are advertised ranges, not verified pay.</p>'
         + section("By category", table(g_cat, lambda k: f"salaries/{cat_slug[k]}/" if len(g_cat[k]) >= 30 and k != OTHER[1] else f"jobs/{cat_slug[k]}/", 10))
         + section("By skill", table(g_tag, lambda k: f"salaries/{TAG_SLUG.get(k, slugify(k))}/" if len(g_tag[k]) >= 30 else f"skills/{TAG_SLUG.get(k, slugify(k))}/"))
         + section("By company", table(g_comp, lambda k: f"companies/{slugify(k)}/", 8))
         + section("Highest-paying open roles", f'<ul class="jobs">{"".join(card(j) for j, _ in diverse_pairs(best, 30))}</ul>', ("with-salary/", "All jobs with salary")))

    def salary_page(slug, label, group, back):
        mids = sorted((lo + hi) / 2 for _, (lo, hi) in group)
        pct = lambda q: mids[min(len(mids) - 1, int(len(mids) * q))]
        comp = defaultdict(list)
        for j, r in group: comp[j["company"]].append((j, r))
        stats = (f'<div class="statrow"><div class="stat"><b>{money(median(mids))}</b><span>median advertised salary</span></div>'
                 f'<div class="stat"><b>{money(pct(.25))} – {money(pct(.75))}</b><span>middle half of roles</span></div>'
                 f'<div class="stat"><b>{money(mids[-1])}</b><span>highest midpoint</span></div><div class="stat"><b>{len(mids):,}</b><span>roles counted</span></div></div>')
        top_jobs = diverse_pairs(sorted(group, key=lambda x: -x[1][1]), 20)
        page(f"salaries/{slug}/", f"{label} Salaries in Tech — median {money(median(mids))} ({len(mids):,} roles) | {SITE}",
             f"What {label} roles pay at tech companies: median, typical range and top-paying employers, from {len(mids):,} open job postings.",
             crumbs(("Salaries", "salaries/"), (label, "")) + f"<h1>{e(label)} salaries in tech</h1>"
             f'<p class="lead">From {len(mids):,} open roles that publish a yearly US-dollar range. Advertised ranges, not verified pay.</p>{stats}'
             + section("Top-paying companies", table(comp, lambda k: f"companies/{slugify(k)}/", 3, 25))
             + section(f"Highest-paying open {label} roles", f'<ul class="jobs">{"".join(card(j) for j, _ in top_jobs)}</ul>', back))
    for t, group in g_tag.items():
        if len(group) >= 30:
            salary_page(TAG_SLUG.get(t, slugify(t)), t, group, (f"skills/{TAG_SLUG.get(t, slugify(t))}/", f"All {t} jobs"))
    for name, group in g_cat.items():
        if len(group) >= 30 and name != OTHER[1]:
            salary_page(cat_slug[name], name, group, (f"jobs/{cat_slug[name]}/", f"All {name} jobs"))

    # My jobs: tracker kept in the visitor's browser, no account needed
    page("my-jobs/", f"My jobs — saved jobs and application tracker | {SITE}", "Track the jobs you saved and applied to, add notes, and keep your saved searches.",
         crumbs(("My jobs", "")) + '<h1>My jobs</h1><p class="lead">Your saved jobs, applications and searches. Kept in this browser only: no account, nothing is uploaded.</p>'
         '<div id="mj-root"><div class="rbar"><div class="tabs" id="mj-tabs"></div><button class="btn ghost sm" id="mj-export" type="button">Export CSV</button></div>'
         '<ul class="jobs" id="mj-list"></ul><div class="empty" id="mj-empty">Nothing here yet. Open any job and press “Save job” or “Mark as applied”.</div>'
         '<section class="sec"><div class="sec-head"><h2>Saved searches</h2></div><ul class="jobs" id="ss-list"></ul>'
         f'<div class="empty" id="ss-empty">No saved searches. Set filters on the <a class="inl" href="{P}/jobs/">search page</a> and press “Save this search”.</div></section>'
         '<section class="sec"><div class="sec-head"><h2>Recently viewed</h2></div><ul class="jobs" id="seen-list"></ul><div class="empty" id="seen-empty">No jobs viewed yet.</div></section></div>', sitemap=False)

    # Plus (paid plan for job seekers; one-time payments, no subscription)
    plus = CFG.get("plus", {"live": False, "plans": []})
    cta = ('<a class="btn primary lg" href="#pay">Get Plus</a>' if plus.get("live") else '<button class="btn primary lg" type="button" disabled>Available soon</button>')
    plans = "".join(
        f'<div class="plan{" best" if pl.get("best") else ""}">' + (f'<span class="pill acc">{e(pl["note"])}</span>' if pl.get("note") else '<span class="pill">&nbsp;</span>')
        + f'<h3>{e(pl["name"])}</h3><p class="price">{e(pl["price"])}</p><p class="note">{e(pl["per"])}</p>{cta}</div>' for pl in plus["plans"])
    feats = [("See jobs 48 hours early", "New roles reach Plus members two days before they appear on the public site. Recruiters fill their shortlists from the first applicants."),
             ("Instant email alerts", "Save a search and get an email the moment a matching job is posted, instead of checking back."),
             ("AI résumé review", "Line-by-line feedback on your résumé against the roles you are aiming for, with wording you can paste in."),
             ("Tailored cover letters", "A draft cover letter for any job in one click, built from your résumé and the posting."),
             ("My jobs on every device", "Your saved jobs, application statuses and notes follow you from laptop to phone.")]
    feat_html = "".join(f'<div class="feat"><h3>{e(a)}</h3><p>{e(b)}</p></div>' for a, b in feats)
    rows_cmp = [("Search, filters and salary data", "✓", "✓"), ("Save jobs and track applications", "This device", "Every device"), ("New jobs", "After 48 hours", "Immediately"),
                ("Alerts for saved searches", "On the site", "By email, instantly"), ("AI résumé review", "—", "✓"), ("Cover letter drafts", "—", "✓")]
    cmp_html = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td><strong>{e(c_)}</strong></td></tr>" for a, b, c_ in rows_cmp)
    soon = "" if plus.get("live") else '<div class="banner">Plus is not available yet. This page shows what we are building and what it will cost. Nothing can be bought today.</div>'
    page("plus/", f"{SITE} Plus — get to new jobs first | {SITE}",
         "Plus gives job seekers early access to new tech jobs, instant email alerts, AI résumé review and cover letters. One payment, no subscription.",
         crumbs(("Plus", "")) + f'<h1>Get to new jobs before everyone else</h1>'
         f'<p class="lead">{e(SITE)} Plus is for people who are actively looking. One payment, no subscription, nothing renews by itself.</p>{soon}'
         f'<div class="feats">{feat_html}</div>'
         + section("Pick how long you need it", f'<div class="plans">{plans}</div><p class="note">One-time payment in USDT, BTC or ETH. Card payments will follow. Searching and applying stay free for everyone.</p>')
         + section("Free and Plus side by side", f'<div class="tablewrap"><table><tr><th>Feature</th><th>Free</th><th>Plus</th></tr>{cmp_html}</table></div>')
         + '<section class="sec"><div class="sec-head"><h2>Questions</h2></div>'
         "<h3>Is this a subscription?</h3><p>No. You pay once for the period you choose. When it ends, nothing is charged and there is nothing to cancel.</p>"
         "<h3>Do I have to pay to apply for jobs?</h3><p>Never. Every job on the site is free to view and apply to. Plus adds speed and tools.</p>"
         "<h3>How do I pay?</h3><p>With crypto: USDT, BTC or ETH. Card payments are planned.</p>"
         "<h3>When does it launch?</h3><p>We are finishing it now. Until then every feature of the free site keeps working as it does today.</p></section>")
    # Employers
    rows = "".join(f"<tr><td><strong>{e(p['name'])}</strong></td><td>{e(p['price'])}</td><td>{e(p['what'])}</td></tr>" for p in CFG["prices"])
    wallets = [w for w in CFG["wallets"] if w["address"]]
    contact = " or ".join(x for x in [f'Telegram <a href="https://t.me/{e(CFG["contact_telegram"])}">@{e(CFG["contact_telegram"])}</a>' if CFG["contact_telegram"] else "",
                                      f'email <a href="mailto:{e(CFG["contact_email"])}">{e(CFG["contact_email"])}</a>' if CFG["contact_email"] else ""] if x)
    if wallets and contact:
        pay = ('<section class="sec"><div class="sec-head"><h2>How to post</h2></div><ol><li>Send us a link to the job or its text: ' + contact + ".</li>"
               "<li>For paid plans, send the amount to one of the addresses below and share the transaction hash.</li>"
               "<li>Your job goes live within 24 hours after the payment is confirmed.</li></ol>"
               '<div class="tablewrap"><table><tr><th>Coin</th><th>Network</th><th>Address</th></tr>'
               + "".join(f"<tr><td>{e(w['coin'])}</td><td>{e(w['network'])}</td><td class=\"addr\">{e(w['address'])}</td></tr>" for w in wallets) + "</table></div></section>")
    else:
        pay = '<div class="banner" style="margin-top:22px">Submissions open in the next few days. Please check this page again soon.</div>'
    page("post-a-job/", f"Post a Tech Job — pay in USDT, BTC or ETH | {SITE}",
         "Post jobs for tech and crypto companies. Standard listings are free, featured listings from $99. Pay with crypto.",
         crumbs(("For employers", "")) + "<h1>Post a job</h1>"
         f'<p class="lead">{roles(n)} from {m:,} tech companies are listed here. People come to this site for one thing: a job in tech.</p>'
         f'<div class="tablewrap"><table><tr><th>Plan</th><th>Price</th><th>What you get</th></tr>{rows}</table></div>{pay}'
         '<section class="sec"><div class="sec-head"><h2>Questions</h2></div>'
         "<h3>How do I pay?</h3><p>Crypto only: USDT, BTC or ETH. We do not take cards or bank transfers.</p>"
         "<h3>No careers page of your own?</h3><p>Use your company page here as one. Link your site's Careers button to it, or embed the list with one line of code: "
         f'<a href="{P}/hiring-badge/">badge and widget</a>.</p>'
         "<h3>What happens when the job closes?</h3><p>It moves to the archive and is marked as closed. The page stays online.</p>"
         "<h3>Can I get a refund?</h3><p>Yes, if the job has not been published yet. Published listings are not refundable.</p></section>")
    page("hiring-badge/", f"Hiring Badge & Jobs Widget for Your Site | {SITE}",
         "Free hiring badge and embeddable jobs widget for tech companies. One line of code, always in sync with your open roles.",
         crumbs(("Hiring badge & widget", "")) + "<h1>Hiring badge &amp; jobs widget</h1>"
         '<p class="lead">Two free ways to show your open roles on your own site. Both stay in sync with your careers feed, so there is nothing to maintain.</p>'
         f'<section class="sec"><div class="sec-head"><h2>Hiring badge</h2></div><p><img src="{P}/hiring-badge.svg" alt="We\'re hiring badge" width="220" height="48"></p>'
         f'<p>Put it in your footer or on your About page. Replace the link with your company page from the <a href="{P}/companies/">companies list</a>.</p><pre><code>{badge_code()}</code></pre></section>'
         '<section class="sec"><div class="sec-head"><h2>Jobs widget</h2></div><p>A live list of your open roles. Open your company page, expand “Show these jobs on your own site”, and copy the snippet. It looks like this:</p>'
         f'<pre><code>{embed_code("your-company")}</code></pre><p class="note">Optional: add <code>data-limit="5"</code> to change how many jobs are shown.</p></section>'
         f'<section class="sec"><div class="sec-head"><h2>RSS feeds</h2></div><p>Every category has a feed you can plug into Telegram, Discord or a reader: '
         f'<a href="{P}/feed.xml">all jobs</a>, <a href="{P}/remote/feed.xml">remote jobs</a>, or add <code>feed.xml</code> to any category address.</p></section>')
    page("about/", f"About | {SITE}", "Where the listings come from, how often the site updates and how to get in touch.",
         crumbs(("About", "")) + "<h1>About</h1>"
         f'<p class="lead">{e(SITE)} collects open roles from the official careers pages of tech companies and puts them in one searchable list.</p>'
         "<h3>Where the jobs come from</h3><p>From the companies' own public hiring feeds. Every job links to the original posting, and you apply there.</p>"
         "<h3>How often it updates</h3><p>Once a day. Closed jobs are not deleted: they move to the archive.</p>"
         "<h3>For job seekers</h3><p>The site is free. We never charge for applying and we do not collect résumés.</p>"
         f'<h3>For employers</h3><p>You can add and feature a job: see <a href="{P}/post-a-job/">posting options</a>.</p>')
    page("404.html", f"Page not found | {SITE}", "Page not found.",
         f'<h1>Page not found</h1><p class="lead">The address may have changed. Try the <a href="{P}/jobs/">job search</a>.</p>', sitemap=False)

    # Data + static files
    idx = [[j["slug"], j["title"], j["company"], j["location"], int(j["remote"]), j["cat"], j["level"], j["tags"], j["salary"], fdate(j["posted"], False),
            int(j["entry"]), int(j["featured"]), hue(j["company"]), int(j["usd"][1]) if j["usd"] else 0, j["places"], int(bool(j.get("crypto"))),
            int((j["posted"] or j["first_seen"]).replace("-", "")[:8] or 0)] for j in order(active)]
    write("data/index.json", json.dumps(idx, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    for f in ("style.css", "app.js", "embed.js", "site.js"):
        shutil.copy(ROOT / "assets" / f, OUT / f)
    write("favicon.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{GRAD}{MARK}</svg>', sitemap=False)
    write("hiring-badge.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="48" viewBox="0 0 220 48" role="img" aria-label="We\'re hiring — {e(SITE)}">'
          f'{GRAD}<rect width="220" height="48" rx="12" fill="#0b0d12"/><g transform="translate(10 8)">{MARK}</g>'
          '<text x="52" y="21" fill="#fff" font-family="Inter,system-ui,-apple-system,Segoe UI,sans-serif" font-size="14" font-weight="700">We’re hiring</text>'
          f'<text x="52" y="37" fill="#aab1c5" font-family="Inter,system-ui,-apple-system,Segoe UI,sans-serif" font-size="11">Open roles on {e(SITE)}</text></svg>', sitemap=False)
    (OUT / ".nojekyll").write_text("")
    sm = "".join(f"<url><loc>{e(FULL + '/' + u)}</loc><lastmod>{TODAY}</lastmod></url>" for u in URLS)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>', sitemap=False)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {FULL}/sitemap.xml\n", sitemap=False)
    print(f"built {len(URLS)} pages: {n} active jobs, {len(archived)} archived, {len(companies)} companies, {len(places)} locations")


if __name__ == "__main__":
    main()
