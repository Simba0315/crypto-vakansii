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
    ("Kubernetes", r"kubernetes|\bk8s\b"), ("AWS", r"\baws\b"), ("DeFi", r"\bdefi\b"), ("Smart contracts", r"smart contract"),
    ("NFT", r"\bnfts?\b"), ("Trading", r"\btrading\b"), ("AML/KYC", r"\baml\b|\bkyc\b"), ("AI", r"\bai\b|machine learning|\bllm"),
]
TITLE_ONLY = {"DeFi", "NFT", "Trading", "AML/KYC", "AI"}  # too common in company boilerplate
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
    if re.search(r"intern|trainee|graduate", t): return "Intern"
    if re.search(r"junior|\bjr\b|associate|entry", t): return "Junior"
    if re.search(r"head of|director|\bvp\b|chief|principal|staff\b|lead\b", t): return "Lead"
    if re.search(r"senior|\bsr\b", t): return "Senior"
    return ""


def norm(company, ats, jid, title, url, location, remote, dept, posted, text, salary=""):
    title = re.sub(r"\s+", " ", title or "").strip()
    location = re.sub(r"\s+", " ", location or "").strip()
    blob = title + "\n" + text
    return {
        "id": f"{ats}-{slugify(company)}-{jid}",
        "company": company, "title": title, "url": url, "location": location,
        "remote": bool(remote) or bool(re.search(r"remote", location, re.I)),
        "dept": (dept or "").strip(), "posted": (posted or "")[:10],
        "excerpt": excerpt(text), "cat": classify(title), "level": level(title),
        "tags": [n for n, rx in SKILLS if re.search(rx, title if n in TITLE_ONLY else blob, re.I)][:6],
        "russian": bool(re.search(r"\brussian\b", blob, re.I)),
        "salary": salary or "",
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
                            c.get("team") or c.get("department"), posted, text, sal))
    else:
        d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=true", 60)
        if not d or "jobs" not in d: return name, None
        for j in d["jobs"]:
            comp = (j.get("compensation") or {})
            sal = comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary") or ""
            out.append(norm(name, ats, j["id"], j.get("title"), j.get("jobUrl") or j.get("applyUrl"), j.get("location"), j.get("isRemote"),
                            j.get("department") or j.get("team"), j.get("publishedAt"), j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")), sal))
    return name, out


def main():
    sources = [s for s in json.loads((ROOT / "sources.json").read_text()) if s["name"] not in EXCLUDE]
    db = json.loads(DATA.read_text()) if DATA.exists() else {}
    used_slugs = {j["slug"] for j in db.values()}
    stats = {"new": 0, "closed": 0, "failed": [], "dropped": []}
    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(fetch, sources))
    for name, jobs in results:
        if jobs is None:
            stats["failed"].append(name); continue          # keep existing records untouched
        if jobs and sum(j["_crypto"] for j in jobs) / len(jobs) < 0.3:
            stats["dropped"].append(name); continue          # same-name company that is not crypto
        seen = set()
        for j in jobs:
            j.pop("_crypto")
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
