"""Generate the static site into ./site from data/jobs.json (+ optional data/paid.json).

Closed jobs keep their pages forever (archive); only the JobPosting markup and the apply button are removed.
"""
import datetime, html, json, re, shutil
from collections import Counter, defaultdict
from pathlib import Path
from collect import CATS, OTHER, slugify

ROOT = Path(__file__).parent
OUT = ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
SITE, BASE, P = CFG["site_name"], CFG["base_url"].rstrip("/"), CFG.get("base_path", "").rstrip("/")
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


def fdate(iso):
    try:
        y, m, d = (int(x) for x in iso[:10].split("-"))
        return f"{MONTHS[m - 1]} {d}, {y}"
    except Exception:
        return ""


def roles(n, word="job"):
    return f"{n:,} {word}{'' if n == 1 else 's'}"


def write(path, content, sitemap=True):
    f = OUT / path / "index.html" if not path.endswith((".html", ".xml", ".txt", ".json")) else OUT / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    if sitemap:
        URLS.append(path)


def page(path, title, desc, body, head="", sitemap=True):
    url = f"{BASE}{P}/{path}"
    write(path, f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="{e(SITE)}">
<link rel="stylesheet" href="{P}/style.css">{head}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="{P}/">{e(SITE)}</a><nav>
<a href="{P}/jobs/">All jobs</a><a href="{P}/remote/">Remote</a><a href="{P}/companies/">Companies</a>
<a class="btn" href="{P}/post-a-job/">Post a job</a></nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap"><p><a href="{P}/about/">About</a><a href="{P}/locations/">Locations</a><a href="{P}/archive/">Closed jobs archive</a><a href="{P}/post-a-job/">For employers</a></p>
<p>© {TODAY[:4]} {e(SITE)}. Listings come from companies' official careers pages. You apply on the employer's site.</p></div></footer>
</body></html>""", sitemap)


def card(j):
    b = []
    if j["featured"]: b.append('<span class="tag acc">Featured</span>')
    if not j["active"]: b.append('<span class="tag">Closed</span>')
    if j["remote"]: b.append('<span class="tag ok">Remote</span>')
    if j["salary"]: b.append(f'<span class="tag warn">{e(j["salary"])}</span>')
    if j["level"]: b.append(f'<span class="tag">{e(j["level"])}</span>')
    b += [f'<span class="tag">{e(t)}</span>' for t in j["tags"]]
    loc = f' · {e(j["location"])}' if j["location"] else ""
    return (f'<li class="job{" feat" if j["featured"] else ""}"><a class="t" href="{P}/job/{j["slug"]}/">{e(j["title"])}</a>'
            f'<div class="m"><a href="{P}/companies/{slugify(j["company"])}/">{e(j["company"])}</a>{loc}</div>'
            f'<div class="b">{"".join(b)}<time datetime="{j["posted"]}">{fdate(j["posted"])}</time></div></li>')


def order(jobs):
    return sorted(jobs, key=lambda j: (not j["featured"], -int((j["posted"] or j["first_seen"]).replace("-", "") or 0)))


def crumbs(*parts):
    items = [f'<a href="{P}/">Home</a>'] + [f'<a href="{P}/{u}">{e(n)}</a>' if u else e(n) for n, u in parts]
    return f'<div class="crumbs">{" › ".join(items)}</div>'


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra=""):
    jobs = order(jobs)
    pages = max(1, -(-len(jobs) // per))
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
    canonical = f"{BASE}{P}/job/{j['slug']}/"
    rows = [("Company", f'<a href="{P}/companies/{slugify(j["company"])}/">{e(j["company"])}</a>')]
    if j["location"]: rows.append(("Location", e(j["location"])))
    if j["remote"]: rows.append(("Workplace", "Remote"))
    rows.append(("Category", f'<a href="{P}/jobs/{j["cat"]}/">{e(CAT[j["cat"]])}</a>'))
    if j["level"]: rows.append(("Level", e(j["level"])))
    if j["salary"]: rows.append(("Salary", e(j["salary"])))
    if j["posted"]: rows.append(("Posted", fdate(j["posted"])))
    if j["tags"]: rows.append(("Skills", " ".join(f'<a class="tag" href="{P}/skills/{TAG_SLUG.get(t, slugify(t))}/">{e(t)}</a>' for t in j["tags"])))
    meta = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
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
        action = (f'<p class="cta"><a class="btn" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Apply on the company site</a></p>'
                  '<p class="note">The full description and the application form are on the employer\'s official page. We never charge job seekers.</p>')
    else:
        action = f'<div class="banner">This job is closed{" as of " + fdate(j["closed"]) if j.get("closed") else ""}. The company is no longer accepting applications. Similar open roles are listed below.</div>'
    pool = [x for x in active_by_cat[j["cat"]] if x["id"] != j["id"]]
    similar = sorted(pool, key=lambda x: (x["company"] != j["company"], -int((x["posted"] or "0").replace("-", "") or 0)))[:6]
    sim = f'<h2>Similar jobs</h2><ul class="jobs">{"".join(card(x) for x in similar)}</ul>' if similar else ""
    desc_block = f'<h2>About the role</h2><p>{e(j["excerpt"])}</p><p class="note">Excerpt from the original posting.</p>' if j["excerpt"] else ""
    body = (crumbs((CAT[j["cat"]], f"jobs/{j['cat']}/"), (j["title"], "")) + f"<h1>{e(j['title'])}</h1>"
            + (action if not j["active"] else "") + f'<div class="card"><dl class="meta">{meta}</dl></div>' + desc_block
            + (action if j["active"] else "") + sim)
    where = j["location"] or ("Remote" if j["remote"] else "")
    title = f"{j['title']} at {j['company']}" + (" (closed)" if not j["active"] else "")
    desc = (f"{j['title']} at {j['company']}" + (f" — {where}" if where else "") + f". {CAT[j['cat']]} role"
            + (", remote" if j["remote"] else "") + (". This job is closed." if not j["active"] else ". Apply on the company site."))
    page(f"job/{j['slug']}/", title, desc, body, head)


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
    places = [(name, slug, js) for name, slug, rx in PLACES if len(js := [j for j in active if re.search(rx, j["location"], re.I)]) >= 5]

    # Home
    li = lambda url, text, count: f'<li><a href="{P}/{url}">{e(text)}<span>{count:,}</span></a></li>'
    cats = "".join(li(f"jobs/{s}/", CAT[s], len(by_cat[s])) for s in CAT if by_cat[s])
    quick = [("Remote jobs", "remote/", sum(j["remote"] for j in active)), ("Salary listed", "with-salary/", sum(bool(j["salary"]) for j in active)),
             ("Entry-level & internships", "entry-level/", sum(j["entry"] for j in active))]
    quick_html = "".join(li(u, t, c) for t, u, c in quick if c)
    place_html = "".join(li(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in places)
    strip = (f'<div class="card strip"><div><strong>Hiring for a crypto project?</strong><br><span class="note">Standard listings are free, featured from $99. '
             f'Pay in USDT, BTC or ETH.</span></div><a class="btn" href="{P}/post-a-job/">Post a job</a></div>')
    home = (f"<h1>Crypto &amp; Web3 Jobs</h1><p class=\"lead\">{roles(n, 'open role')} at {m} companies: exchanges, wallets, "
            "blockchain infrastructure and DeFi. Pulled from official careers pages and updated every day.</p>"
            f'<form class="search" action="{P}/jobs/" method="get"><input type="search" name="q" placeholder="Job title, skill or company" aria-label="Search jobs"><button class="btn">Search</button></form>'
            f'<h2>Quick filters</h2><ul class="grid">{quick_html}</ul><h2>Categories</h2><ul class="grid">{cats}</ul>'
            f'<h2>Locations</h2><ul class="grid">{place_html}</ul>{strip}'
            f'<h2>Latest jobs</h2><ul class="jobs">{"".join(card(j) for j in order(active)[:40])}</ul>'
            f'<p><a href="{P}/jobs/">Browse all {roles(n)} →</a></p>')
    page("", f"Crypto & Web3 Jobs — {roles(n, 'open role')} at {m} companies | {SITE}",
         f"{roles(n)} at crypto and web3 companies: engineering, marketing, compliance, support and more. Remote filters, salary data, updated daily.", home)

    # Search page
    opts = "".join(f'<option value="{s}">{e(CAT[s])}</option>' for s in CAT if by_cat[s])
    search = (crumbs(("All jobs", "")) + "<h1>All crypto &amp; web3 jobs</h1>"
              f'<div id="search" data-base="{P}"><div class="search"><input type="search" id="q" placeholder="Job title, skill or company" aria-label="Search jobs">'
              f'<select id="cat" aria-label="Category"><option value="">All categories</option>{opts}</select></div>'
              '<div class="filters"><label><input type="checkbox" id="f-remote"> Remote</label><label><input type="checkbox" id="f-entry"> Entry-level</label>'
              '<label><input type="checkbox" id="f-sal"> Salary listed</label></div>'
              '<p class="note" id="count">Loading…</p><ul class="jobs" id="results"></ul><p><button class="btn" id="more" hidden>Show more</button></p></div>'
              f'<noscript><p>Search needs JavaScript. Browse by category instead:</p><ul class="grid">{cats}</ul></noscript><script src="{P}/app.js" defer></script>')
    page("jobs/", f"Search {roles(n, 'Crypto & Web3 Job')} | {SITE}",
         "Search crypto and web3 jobs by title, skill or company. Filter by remote, entry-level and listed salary.", search)

    # Listings
    for s, name in CAT.items():
        js = by_cat[s]
        if not js: continue
        listing(f"jobs/{s}/", f"{name} jobs in crypto & web3", f"{name} Jobs in Crypto & Web3 ({len(js):,} open) | {SITE}",
                f"{roles(len(js), name + ' job')} at crypto and web3 companies. Remote and on-site roles, updated daily.",
                js, intro_for(js, f"{e(name)} "), trail=(("All jobs", "jobs/"),))
        rj = [j for j in js if j["remote"]]
        if len(rj) >= 5:
            listing(f"remote/{s}/", f"Remote {name} jobs in crypto", f"Remote {name} Jobs in Crypto & Web3 ({len(rj):,} open) | {SITE}",
                    f"{roles(len(rj), 'remote ' + name + ' job')} at crypto and web3 companies. Work from anywhere, updated daily.",
                    rj, intro_for(rj, f"remote {e(name)} "), trail=(("Remote", "remote/"),))
    remote = [j for j in active if j["remote"]]
    rcats = "".join(li(f"remote/{s}/", CAT[s], c) for s in CAT if (c := sum(j["remote"] for j in by_cat[s])) >= 5)
    listing("remote/", "Remote crypto & web3 jobs", f"Remote Crypto Jobs — {roles(len(remote), 'open role')} | {SITE}",
            f"{roles(len(remote), 'remote job')} at crypto and web3 companies: engineering, marketing, support, compliance and more.",
            remote, intro_for(remote, "remote "), extra=f'<ul class="grid">{rcats}</ul><h2>All remote jobs</h2>')
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
         crumbs(("Locations", "")) + f'<h1>Crypto jobs by location</h1><p class="lead">Number of open roles per place. A job can appear in more than one.</p><ul class="grid">{place_html}</ul>')

    # Companies
    comp_items = sorted(companies.items(), key=lambda kv: -sum(j["active"] for j in kv[1]))
    grid = "".join(li(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js)) for c, js in comp_items)
    page("companies/", f"Crypto Companies Hiring Now — {len(companies)} employers | {SITE}",
         "Crypto and web3 companies with open roles: exchanges, wallets, infrastructure and DeFi teams.",
         crumbs(("Companies", "")) + f'<h1>Crypto companies hiring now</h1><p class="lead">{len(companies)} employers. The number is their current open roles.</p><ul class="grid">{grid}</ul>')
    for c, js in companies.items():
        act, arc = [j for j in js if j["active"]], [j for j in js if not j["active"]]
        extra = f'<h2>Closed jobs at {e(c)}</h2><ul class="jobs">{"".join(card(j) for j in order(arc)[:200])}</ul>' if arc else ""
        body = (crumbs(("Companies", "companies/"), (c, "")) + f"<h1>Jobs at {e(c)}</h1>"
                + f'<p class="lead">{(roles(len(act), "open role") + " at " + e(c) + ", " + str(sum(j["remote"] for j in act)) + " of them remote. Updated daily.") if act else "No open roles right now. Past openings are below."}</p>'
                + (f'<ul class="jobs">{"".join(card(j) for j in order(act))}</ul>' if act else "") + extra)
        page(f"companies/{slugify(c)}/", f"{c} Jobs — {roles(len(act), 'open role')} | {SITE}",
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
        pay = ("<h2>How to post</h2><ol><li>Send us a link to the job or its text: " + contact + ".</li>"
               "<li>For paid plans, send the amount to one of the addresses below and share the transaction hash.</li>"
               "<li>Your job goes live within 24 hours after the payment is confirmed.</li></ol>"
               '<div class="tablewrap"><table><tr><th>Coin</th><th>Network</th><th>Address</th></tr>'
               + "".join(f"<tr><td>{e(w['coin'])}</td><td>{e(w['network'])}</td><td class=\"addr\">{e(w['address'])}</td></tr>" for w in wallets) + "</table></div>")
    else:
        pay = '<div class="banner">Submissions open in the next few days. Please check this page again soon.</div>'
    page("post-a-job/", f"Post a Crypto Job — pay in USDT, BTC or ETH | {SITE}",
         "Post jobs for crypto and web3 companies. Standard listings are free, featured listings from $99. Pay with crypto.",
         crumbs(("For employers", "")) + "<h1>Post a job</h1>"
         f'<p class="lead">{roles(n)} from {m} crypto companies are listed here. People come to this site looking for work in web3.</p>'
         f'<div class="tablewrap"><table><tr><th>Plan</th><th>Price</th><th>What you get</th></tr>{rows}</table></div>{pay}'
         "<h2>Questions</h2><h3>How do I pay?</h3><p>Crypto only: USDT, BTC or ETH. We do not take cards or bank transfers.</p>"
         "<h3>What happens when the job closes?</h3><p>It moves to the archive and is marked as closed. The page stays online.</p>"
         "<h3>Can I get a refund?</h3><p>Yes, if the job has not been published yet. Published listings are not refundable.</p>")
    page("about/", f"About | {SITE}", "Where the listings come from, how often the site updates and how to get in touch.",
         crumbs(("About", "")) + "<h1>About</h1>"
         f"<p>{e(SITE)} collects open roles from the official careers pages of crypto and web3 companies and puts them in one searchable list.</p>"
         "<h2>Where the jobs come from</h2><p>From the companies' own public hiring feeds. Every job links to the original posting, and you apply there.</p>"
         "<h2>How often it updates</h2><p>Once a day. Closed jobs are not deleted: they move to the archive.</p>"
         "<h2>For job seekers</h2><p>The site is free. We never charge for applying and we do not collect résumés.</p>"
         f'<h2>For employers</h2><p>You can add and feature a job: see <a href="{P}/post-a-job/">posting options</a>.</p>')
    page("404.html", f"Page not found | {SITE}", "Page not found.",
         f'<h1>Page not found</h1><p class="lead">The address may have changed. Try the <a href="{P}/jobs/">job search</a>.</p>', sitemap=False)

    # Data + static files
    idx = [[j["slug"], j["title"], j["company"], j["location"], int(j["remote"]), j["cat"], j["level"], j["tags"], j["salary"], fdate(j["posted"]),
            int(j["entry"]), int(j["featured"])] for j in order(active)]
    write("data/index.json", json.dumps(idx, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    for f in ("style.css", "app.js"):
        shutil.copy(ROOT / "assets" / f, OUT / f)
    (OUT / ".nojekyll").write_text("")
    sm = "".join(f"<url><loc>{e(BASE + P + '/' + u)}</loc><lastmod>{TODAY}</lastmod></url>" for u in URLS)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>', sitemap=False)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {BASE}{P}/sitemap.xml\n", sitemap=False)
    print(f"built {len(URLS)} pages: {n} active jobs, {len(archived)} archived, {len(companies)} companies, {len(places)} locations")


if __name__ == "__main__":
    main()
