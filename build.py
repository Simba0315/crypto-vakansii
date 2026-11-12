"""Generate the static site into ./site from data/jobs.json (+ optional data/paid.json).

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
TAG_SLUG = {"C++": "cpp", "Node.js": "nodejs", "AML/KYC": "aml-kyc"}
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
FOOT = {"cats": ""}
MARK = ('<rect width="32" height="32" rx="9" fill="url(#lg)"/><rect x="8" y="9" width="16" height="3" rx="1.5" fill="#fff"/>'
        '<rect x="8" y="14.5" width="11" height="3" rx="1.5" fill="#fff" opacity=".85"/><rect x="8" y="20" width="7" height="3" rx="1.5" fill="#fff" opacity=".7"/>')
GRAD = '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f46e5"/><stop offset="1" stop-color="#9333ea"/></linearGradient></defs>'
LOGO = f'<svg viewBox="0 0 32 32" aria-hidden="true">{GRAD}{MARK}</svg>'
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


def page(path, title, desc, body, head="", sitemap=True, hero=""):
    url = f"{FULL}/{path}"
    write(path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="{e(SITE)}">
<meta name="twitter:card" content="summary"><meta name="theme-color" content="#4f46e5">
<link rel="icon" type="image/svg+xml" href="{P}/favicon.svg">
<link rel="alternate" type="application/rss+xml" title="{e(SITE)} — latest jobs" href="{P}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{P}/style.css">{head}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><nav>
<a class="nl" href="{P}/jobs/">Jobs</a><a class="nl rm" href="{P}/remote/">Remote</a><a class="nl opt" href="{P}/companies/">Companies</a><a class="nl opt" href="{P}/locations/">Locations</a>
<a class="btn" href="{P}/post-a-job/">Post a job</a></nav></div></header>
{hero}<main class="wrap">{body}</main>
<footer><div class="wrap"><div class="fcols">
<div><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><p>Every open role at crypto and web3 companies, pulled from their official careers pages and refreshed daily.</p></div>
<div><h4>Browse</h4><ul><li><a href="{P}/jobs/">All jobs</a></li><li><a href="{P}/remote/">Remote jobs</a></li><li><a href="{P}/entry-level/">Entry-level</a></li><li><a href="{P}/with-salary/">Salary listed</a></li><li><a href="{P}/companies/">Companies</a></li><li><a href="{P}/locations/">Locations</a></li></ul></div>
<div><h4>Categories</h4><ul>{FOOT["cats"]}</ul></div>
<div><h4>Employers</h4><ul><li><a href="{P}/post-a-job/">Post a job</a></li><li><a href="{P}/hiring-badge/">Hiring badge &amp; widget</a></li><li><a href="{P}/feed.xml">RSS feed</a></li><li><a href="{P}/archive/">Closed jobs archive</a></li><li><a href="{P}/about/">About</a></li></ul></div>
</div><p class="fine">© {TODAY[:4]} {e(SITE)}. Listings come from companies' official careers pages. You always apply on the employer's own site.</p></div></footer>
</body></html>""", sitemap)


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


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra="", feed=False):
    jobs = order(jobs)
    pages = max(1, -(-len(jobs) // per))
    if feed: rss(f"{path}feed.xml", f"{h1} — {SITE}", path, jobs)
    for n in range(1, pages + 1):
        chunk = jobs[(n - 1) * per:n * per]
        pager = ""
        if pages > 1:
            links = [f"<b>{i}</b>" if i == n else f'<a href="{P}/{path}{"" if i == 1 else f"{i}/"}">{i}</a>' for i in range(1, pages + 1)]
            pager = f'<div class="pager">{"".join(links)}</div>'
        body = (crumbs(*trail, (h1, "")) + f"<h1>{e(h1)}</h1>" + (f'<p class="lead">{intro}</p>' if intro and n == 1 else "")
                + (extra if n == 1 else "")
                + (f'<ul class="jobs">{"".join(card(j) for j in chunk)}</ul>' if chunk else '<p class="lead">Nothing here right now. Check back soon: the list is updated every day.</p>')
                + pager)
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
        apply_btn = (f'<a class="btn primary lg" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Apply on company site</a>'
                     '<p class="note">The full description and the application form are on the employer\'s official page. We never charge job seekers.</p>')
        banner = ""
    else:
        apply_btn = f'<a class="btn lg" href="{P}/jobs/{j["cat"]}/">See open {e(CAT[j["cat"]])} jobs</a>'
        banner = f'<div class="banner">This job is closed{" as of " + fdate(j["closed"]) if j.get("closed") else ""}. The company is no longer accepting applications. Similar open roles are listed below.</div>'
    pool = [x for x in active_by_cat[j["cat"]] if x["id"] != j["id"]]
    similar = sorted(pool, key=lambda x: (x["company"] != j["company"], -int((x["posted"] or "0").replace("-", "") or 0)))[:6]
    sim = section("Similar jobs", f'<ul class="jobs">{"".join(card(x) for x in similar)}</ul>', (f"jobs/{j['cat']}/", f"All {CAT[j['cat']]} jobs")) if similar else ""
    about = (f'<h2>About the role</h2><div class="prose"><p>{e(j["excerpt"])}</p></div><p class="note">Excerpt from the original posting.</p>'
             if j["excerpt"] else "")
    loc = f" · {e(j['location'])}" if j["location"] else ""
    body = (crumbs((CAT[j["cat"]], f"jobs/{j['cat']}/"), (j["title"], ""))
            + f'<div class="jhead">{ava(j["company"], "lg")}<div><h1>{e(j["title"])}</h1><span class="js"><a href="{comp_url}">{e(j["company"])}</a>{loc}</span>'
            + f'<div class="pills">{"".join(pills)}</div></div></div>{banner}'
            + f'<div class="cols"><article>{about}{sim}</article><aside class="side card"><dl class="meta">{meta}</dl>{apply_btn}</aside></div>')
    where = j["location"] or ("Remote" if j["remote"] else "")
    title = f"{j['title']} at {j['company']}" + (" (closed)" if not j["active"] else "")
    desc = (f"{j['title']} at {j['company']}" + (f" — {where}" if where else "") + f". {CAT[j['cat']]} role"
            + (", remote" if j["remote"] else "") + (". This job is closed." if not j["active"] else ". Apply on the company site."))
    page(f"job/{j['slug']}/", title, desc, body, head)


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
    paid_file = ROOT / "data" / "paid.json"
    for p in (json.loads(paid_file.read_text()) if paid_file.exists() else []):
        base = f"{slugify(p['title'])}-{slugify(p['company'])}"
        jobs.append({"id": "paid-" + base, "slug": base, "location": "", "remote": False, "dept": "", "excerpt": "", "level": "", "tags": [],
                     "russian": False, "salary": "", "posted": TODAY, "first_seen": TODAY, "cat": OTHER[0],
                     "active": p.get("expires", "9999") >= TODAY, **p})
    for j in jobs:
        j["featured"] = bool(j.get("featured_until", "") >= TODAY and j["active"])
        j["entry"] = j["level"] in ("Junior", "Intern")
    active = [j for j in jobs if j["active"]]
    archived = [j for j in jobs if not j["active"]]
    by_cat = defaultdict(list)
    for j in active: by_cat[j["cat"]].append(j)
    companies = defaultdict(list)
    for j in jobs: companies[j["company"]].append(j)
    n, m = len(active), len({j["company"] for j in active})
    remote = [j for j in active if j["remote"]]
    places = [(name, slug, js) for name, slug, rx in PLACES if len(js := [j for j in active if re.search(rx, j["location"], re.I)]) >= 5]
    top_cats = sorted((s for s in CAT if by_cat[s] and s != OTHER[0]), key=lambda s: -len(by_cat[s]))
    FOOT["cats"] = "".join(f'<li><a href="{P}/jobs/{s}/">{e(CAT[s])}</a></li>' for s in top_cats[:6])
    comp_items = sorted(companies.items(), key=lambda kv: -sum(j["active"] for j in kv[1]))

    # Home
    cats = "".join(tile(f"jobs/{s}/", CAT[s], len(by_cat[s])) for s in CAT if by_cat[s])
    place_html = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in places)
    comp_top = "".join(tile(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js), True) for c, js in comp_items[:12])
    hero = (f'<section class="hero"><div class="wrap"><p class="eyebrow"><i></i>Updated daily from official careers pages</p>'
            f'<h1>Find your next role in <span class="grad">crypto &amp; web3</span></h1>'
            f'<p class="sub">{roles(n, "open role")} at {m} companies — exchanges, wallets, blockchain infrastructure and DeFi. One list, no sign-up.</p>'
            f'<form class="searchbar" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Job title, skill or company" aria-label="Search jobs"><button class="btn primary">Search jobs</button></form>'
            f'<div class="popular"><span>Popular:</span><a href="{P}/remote/">Remote</a><a href="{P}/skills/solidity/">Solidity</a><a href="{P}/skills/rust/">Rust</a>'
            f'<a href="{P}/jobs/compliance-legal/">Compliance</a><a href="{P}/entry-level/">Entry-level</a><a href="{P}/with-salary/">Salary listed</a></div>'
            f'<dl class="stats"><div><dt>{n:,}</dt><dd>open roles</dd></div><div><dt>{m}</dt><dd>companies</dd></div>'
            f'<div><dt>{len(remote):,}</dt><dd>remote</dd></div><div><dt>{sum(bool(j["salary"]) for j in active):,}</dt><dd>with salary</dd></div></dl></div></section>')
    band = (f'<div class="band"><div><h2>Hiring for a crypto project?</h2><p>Standard listings are free. Featured placement starts at $99, paid in USDT, BTC or ETH.</p></div>'
            f'<a class="btn lg" href="{P}/post-a-job/">Post a job</a></div>')
    home = (section("Latest jobs", f'<ul class="jobs">{"".join(card(j) for j in order(active)[:12])}</ul>', ("jobs/", f"Browse all {n:,}"))
            + section("Browse by category", f'<ul class="tiles">{cats}</ul>')
            + section("Top companies hiring", f'<ul class="tiles">{comp_top}</ul>', ("companies/", f"All {len(companies)} companies"))
            + section("Jobs by location", f'<ul class="tiles">{place_html}</ul>', ("locations/", "All locations")) + band
            + section("More recent jobs", f'<ul class="jobs">{"".join(card(j) for j in order(active)[12:40])}</ul>', ("jobs/", f"Browse all {n:,}")))
    page("", f"Crypto & Web3 Jobs — {roles(n, 'open role')} at {m} companies | {SITE}",
         f"{roles(n)} at crypto and web3 companies: engineering, marketing, compliance, support and more. Remote filters, salary data, updated daily.", home, hero=hero)
    rss("feed.xml", f"{SITE} — latest crypto & web3 jobs", "", active)

    # Search page
    opts = "".join(f'<option value="{s}">{e(CAT[s])}</option>' for s in CAT if by_cat[s])
    search = (crumbs(("All jobs", "")) + "<h1>All crypto &amp; web3 jobs</h1>"
              f'<div id="search" data-base="{P}"><div class="search"><input type="search" id="q" placeholder="Job title, skill or company" aria-label="Search jobs">'
              f'<select id="cat" aria-label="Category"><option value="">All categories</option>{opts}</select></div>'
              '<div class="filters"><label><input type="checkbox" id="f-remote"> Remote</label><label><input type="checkbox" id="f-entry"> Entry-level</label>'
              '<label><input type="checkbox" id="f-sal"> Salary listed</label></div>'
              '<p class="note" id="count">Loading…</p><ul class="jobs" id="results"></ul><p><button class="btn" id="more" hidden>Show more</button></p></div>'
              f'<noscript><p>Search needs JavaScript. Browse by category instead:</p><ul class="tiles">{cats}</ul></noscript><script src="{P}/app.js" defer></script>')
    page("jobs/", f"Search {roles(n, 'Crypto & Web3 Job')} | {SITE}",
         "Search crypto and web3 jobs by title, skill or company. Filter by remote, entry-level and listed salary.", search)

    # Listings
    for s, name in CAT.items():
        js = by_cat[s]
        if not js: continue
        listing(f"jobs/{s}/", f"{name} jobs in crypto & web3", f"{name} Jobs in Crypto & Web3 ({len(js):,} open) | {SITE}",
                f"{roles(len(js), name + ' job')} at crypto and web3 companies. Remote and on-site roles, updated daily.",
                js, intro_for(js, f"{e(name)} "), trail=(("All jobs", "jobs/"),), feed=True)
        rj = [j for j in js if j["remote"]]
        if len(rj) >= 5:
            listing(f"remote/{s}/", f"Remote {name} jobs in crypto", f"Remote {name} Jobs in Crypto & Web3 ({len(rj):,} open) | {SITE}",
                    f"{roles(len(rj), 'remote ' + name + ' job')} at crypto and web3 companies. Work from anywhere, updated daily.",
                    rj, intro_for(rj, f"remote {e(name)} "), trail=(("Remote", "remote/"),))
    rcats = "".join(tile(f"remote/{s}/", CAT[s], c) for s in CAT if (c := sum(j["remote"] for j in by_cat[s])) >= 5)
    listing("remote/", "Remote crypto & web3 jobs", f"Remote Crypto Jobs — {roles(len(remote), 'open role')} | {SITE}",
            f"{roles(len(remote), 'remote job')} at crypto and web3 companies: engineering, marketing, support, compliance and more.",
            remote, intro_for(remote, "remote "), extra=f'<ul class="tiles">{rcats}</ul><div class="sec"><div class="sec-head"><h2>All remote jobs</h2></div></div>', feed=True)
    sal = [j for j in active if j["salary"]]
    listing("with-salary/", "Crypto jobs with salary listed", f"Crypto Jobs With Salary Listed ({len(sal):,}) | {SITE}",
            "Crypto and web3 jobs where the employer publishes the salary range up front.", sal, intro_for(sal, "", " with a published salary range"))
    jr = [j for j in active if j["entry"]]
    listing("entry-level/", "Entry-level crypto jobs & internships", f"Entry-Level Crypto Jobs & Internships ({len(jr):,}) | {SITE}",
            "Internships and junior roles at crypto and web3 companies: a way into the industry without years of experience.", jr,
            intro_for(jr, "entry-level "))
    by_tag = defaultdict(list)
    for j in active:
        for t in j["tags"]: by_tag[t].append(j)
    for t, js in by_tag.items():
        listing(f"skills/{TAG_SLUG.get(t, slugify(t))}/", f"{t} jobs in crypto & web3", f"{t} Jobs in Crypto & Web3 ({len(js):,} open) | {SITE}",
                f"{roles(len(js))} at crypto companies that ask for {t}.", js, intro_for(js, "", f" mentioning {e(t)}"))
    for name, slug, js in places:
        short = name.removeprefix("the ")
        listing(f"locations/{slug}/", f"Crypto jobs in {name}", f"Crypto Jobs in {short} ({len(js):,} open) | {SITE}",
                f"{roles(len(js), 'crypto and web3 job')} in {name}. Exchanges, wallets and blockchain companies hiring now.",
                js, intro_for(js, "", f" in {e(name)}"), trail=(("Locations", "locations/"),))
    page("locations/", f"Crypto Jobs by Location | {SITE}", "Browse crypto and web3 jobs by city, country and region.",
         crumbs(("Locations", "")) + f'<h1>Crypto jobs by location</h1><p class="lead">Open roles per place. A job that lists several locations appears in each of them.</p><ul class="tiles">{place_html}</ul>')

    # Companies (+ per-company data for the embeddable widget)
    grid = "".join(tile(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js), True) for c, js in comp_items)
    page("companies/", f"Crypto Companies Hiring Now — {len(companies)} employers | {SITE}",
         "Crypto and web3 companies with open roles: exchanges, wallets, infrastructure and DeFi teams.",
         crumbs(("Companies", "")) + f'<h1>Crypto companies hiring now</h1><p class="lead">{len(companies)} employers. The number is their current open roles.</p><ul class="tiles">{grid}</ul>')
    for c, js in companies.items():
        slug = slugify(c)
        act, arc = order([j for j in js if j["active"]]), order([j for j in js if not j["active"]])
        write(f"data/companies/{slug}.json", json.dumps({
            "company": c, "site": SITE, "page": f"{FULL}/companies/{slug}/", "total": len(act),
            "jobs": [{"title": j["title"], "url": f"{FULL}/job/{j['slug']}/", "location": j["location"], "remote": j["remote"]} for j in act[:50]],
        }, ensure_ascii=False, separators=(",", ":")), sitemap=False)
        lead = (f"{roles(len(act), 'open role')} at {e(c)}, {sum(j['remote'] for j in act):,} of them remote. Updated daily."
                if act else "No open roles right now. Past openings are below.")
        closed = section(f"Closed jobs at {c}", f'<ul class="jobs">{"".join(card(j) for j in arc[:200])}</ul>') if arc else ""
        embed = (f'<details class="embed"><summary>Work at {e(c)}? Show these jobs on your own site</summary>'
                 f'<p class="note">Paste this where the list should appear. It stays in sync automatically.</p><pre><code>{embed_code(slug)}</code></pre>'
                 f'<p class="note">Or add a hiring badge that links here:</p><pre><code>{badge_code(slug)}</code></pre></details>')
        body = (crumbs(("Companies", "companies/"), (c, ""))
                + f'<div class="jhead">{ava(c, "lg")}<div><h1>Jobs at {e(c)}</h1><span class="js">{lead}</span></div></div>'
                + (f'<ul class="jobs">{"".join(card(j) for j in act)}</ul>' if act else "") + closed + embed)
        page(f"companies/{slug}/", f"{c} Jobs — {roles(len(act), 'open role')} | {SITE}",
             f"All jobs at {c}: {len(act):,} open" + (f" and {len(arc):,} closed" if arc else "") + ". Categories, locations and remote roles.", body)

    # Job pages + archive
    for j in jobs: job_page(j, by_cat)
    listing("archive/", "Closed crypto jobs archive", f"Closed Crypto Jobs Archive ({len(archived):,}) | {SITE}",
            "Closed jobs at crypto companies: see which roles teams were hiring for and when.", archived,
            "Closed jobs stay here so you can see which roles companies were hiring for in the past.")

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
    page("post-a-job/", f"Post a Crypto Job — pay in USDT, BTC or ETH | {SITE}",
         "Post jobs for crypto and web3 companies. Standard listings are free, featured listings from $99. Pay with crypto.",
         crumbs(("For employers", "")) + "<h1>Post a job</h1>"
         f'<p class="lead">{roles(n)} from {m} crypto companies are listed here. People come to this site for one thing: work in web3.</p>'
         f'<div class="tablewrap"><table><tr><th>Plan</th><th>Price</th><th>What you get</th></tr>{rows}</table></div>{pay}'
         '<section class="sec"><div class="sec-head"><h2>Questions</h2></div>'
         "<h3>How do I pay?</h3><p>Crypto only: USDT, BTC or ETH. We do not take cards or bank transfers.</p>"
         "<h3>No careers page of your own?</h3><p>Use your company page here as one. Link your site's Careers button to it, or embed the list with one line of code: "
         f'<a href="{P}/hiring-badge/">badge and widget</a>.</p>'
         "<h3>What happens when the job closes?</h3><p>It moves to the archive and is marked as closed. The page stays online.</p>"
         "<h3>Can I get a refund?</h3><p>Yes, if the job has not been published yet. Published listings are not refundable.</p></section>")
    page("hiring-badge/", f"Hiring Badge & Jobs Widget for Your Site | {SITE}",
         "Free hiring badge and embeddable jobs widget for crypto companies. One line of code, always in sync with your open roles.",
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
         f'<p class="lead">{e(SITE)} collects open roles from the official careers pages of crypto and web3 companies and puts them in one searchable list.</p>'
         "<h3>Where the jobs come from</h3><p>From the companies' own public hiring feeds. Every job links to the original posting, and you apply there.</p>"
         "<h3>How often it updates</h3><p>Once a day. Closed jobs are not deleted: they move to the archive.</p>"
         "<h3>For job seekers</h3><p>The site is free. We never charge for applying and we do not collect résumés.</p>"
         f'<h3>For employers</h3><p>You can add and feature a job: see <a href="{P}/post-a-job/">posting options</a>.</p>')
    page("404.html", f"Page not found | {SITE}", "Page not found.",
         f'<h1>Page not found</h1><p class="lead">The address may have changed. Try the <a href="{P}/jobs/">job search</a>.</p>', sitemap=False)

    # Data + static files
    idx = [[j["slug"], j["title"], j["company"], j["location"], int(j["remote"]), j["cat"], j["level"], j["tags"], j["salary"], fdate(j["posted"], False),
            int(j["entry"]), int(j["featured"]), hue(j["company"])] for j in order(active)]
    write("data/index.json", json.dumps(idx, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    for f in ("style.css", "app.js", "embed.js"):
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
