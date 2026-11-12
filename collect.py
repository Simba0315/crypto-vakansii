"""Collect open jobs from public ATS feeds of crypto companies into data/jobs.json.

Closed jobs are never deleted: they stay in the file with active=false (archive).
"""
import datetime, html, json, re, sys, concurrent.futures as cf
from pathlib import Path
from net import get_json

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "jobs.json"
TODAY = datetime.date.today().isoformat()

# Same-name companies that are not crypto, and trading firms where most roles are not crypto.
EXCLUDE = {"Casa", "Swan", "Sei", "Safe", "Circle", "Compound", "Ramp", "Robinhood Crypto",
           "Cumberland / DRW", "Jump Crypto", "Flow Traders"}
EXCLUDE_TECH = set()  # tech-list names to skip (wrong company behind the feed)
CRYPTO_RE = re.compile(r"crypto|blockchain|bitcoin|web3|defi\b|token|ethereum|stablecoin|digital asset|on-chain|onchain|wallet", re.I)

CATS = [
    ("engineering", "Engineering", r"engineer|developer|devops|sre\b|architect|programmer|\bqa\b|sdet|frontend|backend|full.?stack|solidity|rust\b|tech lead|cto\b|开发|工程师"),
    ("security", "Security", r"security|auditor|pentest|soc\b|threat|infosec"),
    ("product", "Product", r"product manager|product owner|product lead|head of product|product director|产品"),
    ("design", "Design", r"design|\bux\b|\bui\b|creative|illustrat|motion"),
    ("marketing", "Marketing & Community", r"marketing|growth|content|social media|community|brand|\bpr\b|communications|seo\b|copywrit|kol\b|运营"),
    ("sales-bd", "Sales & Business Development", r"sales|business development|\bbd\b|partnership|account (executive|manager)|institutional|relationship manager|listing"),
    ("data-research", "Data & Research", r"analyst|data\b|research|quant|scientist|economist|strategy"),
    ("support", "Customer Support", r"support|customer (service|success|experience)|client service|helpdesk"),
    ("compliance-legal", "Compliance & Legal", r"compliance|legal|\baml\b|\bkyc\b|counsel|risk|regulatory|fraud|investigat|mlro|audit"),
    ("finance", "Finance & Trading", r"finance|financial|account(ant|ing)|treasury|controller|tax\b|payroll|trader|trading"),
    ("people", "People & Recruiting", r"recruit|talent|people (ops|partner|operations)|\bhr\b|human resources"),
    ("operations", "Operations", r"operations|project manager|program manager|chief of staff|executive assistant|office|administrat"),
]
OTHER = ("other", "Other")

SKILLS = [
    ("Solidity", r"solidity"), ("Rust", r"\brust\b"), ("Go", r"golang|\bgo[,/)]|[,/(] ?go\b"), ("Python", r"python"),
    ("TypeScript", r"typescript"), ("JavaScript", r"javascript"), ("React", r"\breact\b"), ("Node.js", r"node\.?js"),
    ("Java", r"\bjava\b"), ("C++", r"c\+\+"), ("Kotlin", r"kotlin"), ("Swift", r"\bswift\b"), ("SQL", r"\bsql\b"),
    ("Ruby", r"\bruby\b"), ("PHP", r"\bphp\b"), ("C#", r"\bc#"), (".NET", r"\.net\b"), ("Scala", r"\bscala\b"), ("Elixir", r"\belixir\b"),
    ("PostgreSQL", r"postgres"), ("Docker", r"\bdocker\b"), ("Terraform", r"terraform"), ("GCP", r"\bgcp\b|google cloud"), ("Azure", r"\bazure\b"),
    ("Machine Learning", r"machine learning"), ("LLM", r"\bllms?\b|large language model"), ("iOS", r"\bios\b"), ("Android", r"\bandroid\b"),
    ("Figma", r"\bfigma\b"), ("Salesforce", r"salesforce"),
    ("Next.js", r"next\.?js"), ("Vue", r"\bvue(\.js|js)?\b"), ("Angular", r"\bangular\b"), ("React Native", r"react native"), ("Flutter", r"\bflutter\b"),
    ("Django", r"\bdjango\b"), ("FastAPI", r"fastapi"), ("GraphQL", r"graphql"), ("PyTorch", r"pytorch"), ("TensorFlow", r"tensorflow"),
    ("Kafka", r"\bkafka\b"), ("Spark", r"apache spark|pyspark|spark sql"), ("Airflow", r"\bairflow\b"), ("dbt", r"\bdbt\b"), ("Snowflake", r"\bsnowflake\b"),
    ("Redis", r"\bredis\b"), ("MongoDB", r"mongodb"), ("MySQL", r"mysql"), ("Linux", r"\blinux\b"), ("CI/CD", r"ci/cd|ci cd"),
    ("Tableau", r"\btableau\b"), ("Looker", r"\blooker\b"), ("Excel", r"(microsoft|ms|advanced|proficien\w+ (in|with)) excel|excel (skills|modell?ing|models|spreadsheets)"),
    ("HubSpot", r"hubspot"), ("SEO", r"\bseo\b"), ("Jira", r"\bjira\b"), ("Agile", r"\bagile\b|\bscrum\b"),
    ("Kubernetes", r"kubernetes|\bk8s\b"), ("AWS", r"\baws\b"), ("DeFi", r"\bdefi\b"), ("Smart contracts", r"smart contract"),
    ("NFT", r"\bnfts?\b"), ("Trading", r"\btrading\b"), ("AML/KYC", r"\baml\b|\bkyc\b"), ("AI", r"\bai\b|machine learning|\bllm"),
]
TITLE_ONLY = {"DeFi", "NFT", "Trading", "AML/KYC", "AI", "iOS", "Android", "Salesforce"}  # too common in company boilerplate
PERKS = [   # (name, page slug, pattern) detected in the posting text
    ("Visa sponsorship", "visa-sponsorship", r"visa sponsorship|sponsor (a |your )?(work )?visas?|sponsorship (is )?available|we (can|will|do) sponsor"),
    ("Relocation support", "relocation", r"relocation (assistance|support|package|bonus|allowance)|(help|support) (you )?(to |with )?relocat"),
    ("Equity", "equity", r"stock options|\brsus?\b|equity (grant|package|compensation|awards?|stake|ownership)|(company|meaningful|generous|competitive|plus|salary (and|&)|bonus (and|&|,)) equity"),
    ("4-day week", "4-day-week", r"4[- ]day (work ?)?week|four[- ]day (work ?)?week"),
    ("Unlimited PTO", "unlimited-pto", r"unlimited (pto|paid time off|vacation|holiday)|flexible (pto|paid time off)"),
    ("Parental leave", "parental-leave", r"parental leave|maternity leave|paternity leave"),
    ("Learning budget", "learning-budget", r"learning (budget|stipend|allowance)|education (budget|stipend|allowance)|professional development (budget|stipend|allowance)"),
    ("Home office stipend", "home-office-stipend", r"home office (stipend|budget|allowance|setup)|work[- ]from[- ]home (stipend|budget|allowance)|remote (work )?(stipend|allowance)"),
]
NO_VISA = re.compile(r"(not|unable|cannot|can't|can not|no|won't|will not|don't|do not) (\w+ ){0,5}(sponsor|sponsorship)|without (\w+ ){0,3}sponsorship|sponsorship is(n't| not)", re.I)


def perks(text):
    out = [name for name, _, rx in PERKS if re.search(rx, text, re.I)]
    if "Visa sponsorship" in out and NO_VISA.search(text): out.remove("Visa sponsorship")
    return out


def etype(title, hint=""):
    """Employment type when the feed or the title says so; empty when unknown."""
    h, t = (hint or "").lower().replace(" ", "").replace("-", "").replace("_", ""), title.lower()
    if "intern" in h or re.search(r"\bintern(ship)?\b", t): return "Internship"
    if "contract" in h or "temporary" in h or re.search(r"\bcontract(or)?\b|\btemporary\b|\bfreelance\b|fixed[- ]term", t): return "Contract"
    if "parttime" in h or re.search(r"part[- ]time", t): return "Part-time"
    if "fulltime" in h or "permanent" in h: return "Full-time"
    return ""


ROLE_MARKERS = re.compile(
    r"(what you.ll (do|be doing)|responsibilities|about the (role|job|position|opportunity)|the role|role overview|"
    r"job description|your mission|in this role|what you will do|position overview|the opportunity|key duties|job summary)\s*:?",
    re.I)


def strip_html(s):
    s = html.unescape(s or "")
    s = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"[ \t\xa0]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def excerpt(text, n=420):
    m = ROLE_MARKERS.search(text)
    body = text[m.end():] if m and len(text) - m.end() > 200 else text
    body = re.sub(r"\s+", " ", body).strip(" :-•\n")
    if len(body) <= n:
        return body
    cut = body[:n]
    return cut[:cut.rfind(" ")].rstrip(",.;:") + "…"


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60].strip("-") or "job"


def classify(title):
    for slug, name, rx in CATS:
        if re.search(rx, title, re.I):
            return slug
    return OTHER[0]


def level(title):
    t = title.lower()
    if re.search(r"\bintern(ship)?s?\b|\btrainee\b|\bnew grad|\bgraduate program", t): return "Intern"
    if re.search(r"head of|\bdirector\b|\bvp\b|vice president|\bchief\b|\bprincipal\b|\bstaff\b|\blead\b", t): return "Lead"
    if re.search(r"\bsenior\b|\bsr\b\.?", t): return "Senior"
    if re.search(r"\bjunior\b|\bjr\b\.?|entry[- ]level|\bassociate\b", t): return "Junior"
    return ""


def norm(company, ats, jid, title, url, location, remote, dept, posted, text, salary="", hint=""):
    title = re.sub(r"\s+", " ", title or "").strip()
    location = re.sub(r"\s+", " ", location or "").strip()
    if location.lower() in {"n/a", "na", "none", "tbd", "-", "null", "not specified"}: location = ""
    blob = title + "\n" + text
    return {
        "id": f"{ats}-{slugify(company)}-{jid}",
        "company": company, "title": title, "url": url, "location": location,
        "remote": bool(remote) or bool(re.search(r"remote", location, re.I)),
        "dept": (dept or "").strip(), "posted": (posted or "")[:10],
        "excerpt": excerpt(text), "cat": classify(title), "level": level(title),
        "tags": [n for n, rx in SKILLS if re.search(rx, title if n in TITLE_ONLY else blob, re.I)][:8],
        "russian": bool(re.search(r"\brussian\b", blob, re.I)),
        "salary": salary or "",
        "perks": perks(text), "etype": etype(title, hint),
        "anywhere": bool(re.search(r"worldwide|world-wide|anywhere|global|any location", location, re.I)),
        "_crypto": bool(CRYPTO_RE.search(blob)),
    }


def fetch(src):
    name, ats, tok = src["name"], src["ats"], src["token"]
    out = []
    if ats == "greenhouse":
        d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true", 60)
        if not d or "jobs" not in d: return name, None
        for j in d["jobs"]:
            dept = ", ".join(x.get("name", "") for x in (j.get("departments") or []))
            out.append(norm(name, ats, j["id"], j.get("title"), j.get("absolute_url"), (j.get("location") or {}).get("name"),
                            False, dept, j.get("first_published") or j.get("updated_at"), strip_html(j.get("content"))))
    elif ats == "lever":
        d = get_json(f"https://api.lever.co/v0/postings/{tok}?mode=json", 60)
        if not isinstance(d, list): return name, None
        for j in d:
            c = j.get("categories") or {}
            text = "\n".join([j.get("descriptionPlain") or ""] + [f"{l.get('text','')}\n{strip_html(l.get('content'))}" for l in (j.get("lists") or [])])
            posted = datetime.datetime.fromtimestamp(j["createdAt"] / 1000, datetime.timezone.utc).date().isoformat() if j.get("createdAt") else ""
            sr = j.get("salaryRange") or {}
            sal = f"{sr.get('min'):,.0f}–{sr.get('max'):,.0f} {sr.get('currency','')}".replace(",", " ") if sr.get("min") and sr.get("max") else ""
            out.append(norm(name, ats, j["id"], j.get("text"), j.get("hostedUrl"), c.get("location"), j.get("workplaceType") == "remote",
                            c.get("team") or c.get("department"), posted, text, sal, c.get("commitment") or ""))
    else:
        d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=true", 60)
        if not d or "jobs" not in d: return name, None
        for j in d["jobs"]:
            comp = (j.get("compensation") or {})
            sal = comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary") or ""
            out.append(norm(name, ats, j["id"], j.get("title"), j.get("jobUrl") or j.get("applyUrl"), j.get("location"), j.get("isRemote"),
                            j.get("department") or j.get("team"), j.get("publishedAt"), j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")), sal, j.get("employmentType") or ""))
    return name, out


def main():
    sources = [dict(s, crypto=True) for s in json.loads((ROOT / "sources.json").read_text()) if s["name"] not in EXCLUDE]
    tech_file = ROOT / "sources_tech.json"
    taken = {(s["ats"], s["token"]) for s in sources} | {s["name"].lower() for s in sources}
    for s in (json.loads(tech_file.read_text()) if tech_file.exists() else []):
        if (s["ats"], s["token"]) not in taken and s["name"].lower() not in taken and s["name"] not in EXCLUDE_TECH:
            sources.append(dict(s, crypto=False)); taken |= {(s["ats"], s["token"]), s["name"].lower()}
    is_crypto = {s["name"]: s["crypto"] for s in sources}
    db = json.loads(DATA.read_text()) if DATA.exists() else {}
    used_slugs = {j["slug"] for j in db.values()}
    stats = {"new": 0, "closed": 0, "failed": [], "dropped": []}
    with cf.ThreadPoolExecutor(12) as ex:
        results = list(ex.map(fetch, sources))
    # second, gentler pass for feeds that timed out or were rate-limited the first time
    by_name = {s["name"]: s for s in sources}
    retry = [by_name[name] for name, jobs in results if jobs is None]
    if retry:
        with cf.ThreadPoolExecutor(3) as ex:
            again = dict(ex.map(fetch, retry))
        results = [(name, again.get(name) if jobs is None else jobs) for name, jobs in results]
    for name, jobs in results:
        if jobs is None:
            stats["failed"].append(name); continue          # keep existing records untouched
        if is_crypto[name] and jobs and sum(j["_crypto"] for j in jobs) / len(jobs) < 0.3:
            stats["dropped"].append(name); continue          # same-name company that is not crypto
        seen = set()
        for j in jobs:
            j.pop("_crypto")
            j["crypto"] = is_crypto[name]
            if not j["title"] or not j["url"]: continue
            seen.add(j["id"])
            old = db.get(j["id"])
            if old:
                j.update(slug=old["slug"], first_seen=old["first_seen"])
            else:
                base = f"{slugify(j['title'])}-{slugify(name)}"
                slug, i = base, 2
                while slug in used_slugs:
                    slug, i = f"{base}-{i}", i + 1
                used_slugs.add(slug)
                j.update(slug=slug, first_seen=TODAY)
                stats["new"] += 1
            j.update(last_seen=TODAY, active=True)
            j.pop("closed", None)
            db[j["id"]] = j
        for jid, old in db.items():
            if old["company"] == name and old["active"] and jid not in seen:
                old.update(active=False, closed=TODAY); stats["closed"] += 1
    DATA.parent.mkdir(exist_ok=True)
    DATA.write_text(json.dumps(db, ensure_ascii=False, indent=0))
    active = sum(j["active"] for j in db.values())
    print(f"active {active}, archived {len(db) - active}, new {stats['new']}, closed {stats['closed']}")
    print("failed:", ", ".join(stats["failed"]) or "-")
    print("dropped as not crypto:", ", ".join(stats["dropped"]) or "-")


if __name__ == "__main__":
    main()
