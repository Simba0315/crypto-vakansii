"""Collect open jobs from public ATS feeds of crypto companies into data/jobs.json.

Closed jobs are never deleted: they stay in the file with active=false (archive).

Hiring systems read (fetch_feed): Greenhouse, Lever and Ashby (sources.json, sources_tech.json, sources_more.json), and since
15 Nov 2026 Workable, Recruitee, Teamtailor, Personio, Workday and SmartRecruiters (sources_ats.json). Each is asked through its own
public job feed, the one its customers' careers pages use, with the user agent in net.py and a pause between requests (ATS_GAP).

A posting that has not changed since the last run is not parsed again: every record keeps a fingerprint of the feed's own data for
it ("h"), and an unchanged posting keeps its record from the last run (reuse in fetch_feed). Parsing was most of the work of a run
(about 40 ms a posting, on one CPU, every posting every hour), so this is what keeps the hourly run short as boards are added. Any
change to this file changes every fingerprint (RULES), so new rules (a skill, a category) reach every job in the next run; what has to
be parsed is parsed in one worker process per CPU (PARSE).
"""
import datetime, email.utils, hashlib, html, json, os, re, sys, threading, time, concurrent.futures as cf
import xml.etree.ElementTree as ET
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from net import get_json, get_text, post_json

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "jobs.json"
TODAY = datetime.date.today().isoformat()
# Full descriptions are stored for postings newer than this. GitHub Pages' size limit is gone (the site is served by our own server),
# but data/jobs.json is pushed to the data branch every hour and every description is about 5 KB, so the old ones are still left out.
DESC_SINCE = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
RULES = hashlib.md5(Path(__file__).read_bytes()).hexdigest()[:8]       # part of every fingerprint: new rules, new records
# Boards read in turn rather than every hour (main): the large lists added once the 1 GB limit of GitHub Pages was gone.
ROTATING = ("sources_more.json", "sources_ats.json")
# Politeness per hiring system: how many of its boards are read at the same time, and the shortest gap in seconds between two of our
# requests to it (across all boards; Workday's tenants each have their own address, so there the gap is per board).
ATS_LIMIT = {"workday": 12, "smartrecruiters": 2, "workable": 4, "recruitee": 6, "teamtailor": 6, "personio": 6}
ATS_GAP = {"workday": 0.3, "smartrecruiters": 0.5, "workable": 0.25, "recruitee": 0.1, "teamtailor": 0.1, "personio": 0.1}
# Workday and SmartRecruiters list a board's postings without their text, which takes one more request per posting. Only new or
# changed postings are asked for, at most this many per board in one read (the newest first); the rest wait for the next read.
DETAILS = int(os.environ.get("HRN_DETAILS") or 40)
LIST_MAX = 1000                     # Workday, SmartRecruiters: the newest this many postings of a board (Workday lists 20 per request)
SLOW_ATS = {"workday", "smartrecruiters"}     # many requests a board: the hourly run reads them half as often as the other rotating boards

# Same-name companies that are not crypto, and trading firms where most roles are not crypto.
EXCLUDE = {"Casa", "Swan", "Sei", "Safe", "Circle", "Compound", "Ramp", "Robinhood Crypto",
           "Cumberland / DRW", "Jump Crypto", "Flow Traders"}
EXCLUDE_TECH = set()  # tech-list names to skip (wrong company behind the feed)
CRYPTO_RE = re.compile(r"crypto|blockchain|bitcoin|web3|defi\b|token|ethereum|stablecoin|digital asset|on-chain|onchain|wallet", re.I)

CATS = [
    ("security", "Security", r"security|pentest|\bsoc\b|threat|infosec|\bappsec\b"),
    ("engineering", "Engineering", r"engineer|developer|devops|\bsre\b|architect|programmer|\bqa\b|sdet|frontend|backend|full.?stack|solidity|\brust\b|tech lead|\bcto\b|member of technical staff|"
                                   r"software|machine learning|firmware|hardware|embedded|robotics|\basic\b|\bfpga\b|\brtl\b|technical program manager|engineering program manager|开发|工程师"),
    ("product", "Product", r"product manager|product owner|product lead|head of product|product director|产品"),
    ("design", "Design", r"\bdesign(er|ers)?\b|\bux\b|\bui\b|creative|illustrat|motion"),
    ("sales-bd", "Sales & Business Development", r"\bsales\b|business development|\bbd\b|partnership|account (executive|manage)|institutional|relationship manager|listing"),
    ("marketing", "Marketing & Community", r"marketing|growth|content|social media|community|brand|\bpr\b|communications|\bseo\b|copywrit|\bkol\b|运营"),
    ("support", "Customer Service & Support", r"support|customer (service|success|experience)|client service|helpdesk"),
    ("compliance-legal", "Compliance & Legal", r"compliance|legal|\baml\b|\bkyc\b|counsel|attorney|\brisk\b|regulatory|fraud|investigat|mlro|audit"),
    ("finance", "Finance & Trading", r"finance|financial|account(ant|ing)|accounts? (payable|receivable)|treasury|controller|\btax\b|payroll|trader|trading|billing|\bfp&a\b"),
    ("people", "HR & Recruiting", r"recruit|talent|people (ops|partner|operations)|\bhr\b|human resources"),
    ("data-research", "Data & Research", r"analyst|\bdata\b|research|quant|scientist|economist|strategy"),
    ("operations", "Operations", r"operations|project manager|program manager|chief of staff|executive assistant|office|administrat"),
    # Added 13 Nov 2026 (the owner asked for the fields other job sites have). They stand after the older ones on purpose:
    # a title that already had a category keeps it, and only what used to fall into "Other" is sorted further.
    ("healthcare", "Healthcare", r"\bnurse|nursing|clinical|clinician|physician|\bmedical\b|therapist|pharmac|\bnp\b|dental|dentist|veterinar|care (manager|coordinator|guide|navigator|advocate)|"
                                 r"health coach|behavioral health|caregiver|\bemt\b|paramedic|optomet"),
    ("manufacturing", "Manufacturing & Trades", r"technician|manufactur|production|welder|machinist|assembl|\boperator\b|inspector|maintenance|electrician|\bmechanic\b|fabricat|tooling|\bcnc\b|"
                                                r"facilities|construction|quality (control|inspector|technician)|painter|plumber|hvac|rigger|crane|installer"),
    ("supply-chain", "Supply Chain & Logistics", r"\bsupply\b|sourcing|procurement|logistics|warehouse|fulfil+ment|\bbuyer\b|\bplanner\b|inventory|shipping|receiving|transport|\bdriver\b|"
                                                 r"materials? (handler|planner|manager|coordinator)|dispatcher|fleet"),
    ("retail", "Retail & Hospitality", r"\bretail\b|\bstore\b|key holder|cashier|barista|\bchef\b|\bcook\b|hospitality|merchandis|shift (lead|supervisor|manager)|restaurant|front desk|concierge|housekeep"),
    ("education", "Education & Training", r"teacher|instructor|\btutor|curriculum|\btrainer\b|learning (designer|specialist|experience|and development|& development)|enablement|professor|lecturer|"
                                          r"education|instructional"),
    ("consulting", "Consulting & Solutions", r"consultant|consulting|implementation|professional services|solutions? (consult|architect|specialist|manager|lead)|deployment strategist|onboarding|"
                                             r"technical account|engagement manager|delivery (manager|lead)|advisor|advisory"),
]
# When the title names no field, the department the employer filed the job under often does ("Sales", "People", "Supply Chain").
DEPT_CATS = [
    ("sales-bd", r"sales|go.to.market|\bgtm\b|revenue|commercial|business development|partnerships?|account (management|development)"),
    ("marketing", r"marketing|growth|brand|communications|community"), ("support", r"customer (success|experience|support|care)|\bsupport\b"),
    ("finance", r"finance|accounting|\bg&a\b|treasury"), ("people", r"people|talent|\bhr\b|human resources|recruit"), ("compliance-legal", r"legal|compliance|\brisk\b|policy"),
    ("supply-chain", r"supply chain|logistics|fulfil+ment|procurement|fleet"), ("manufacturing", r"manufactur|production|\bmfg\b|field service|facilities|data center"),
    ("healthcare", r"medical|clinical|\bhealth\b|care team"), ("retail", r"retail|key holders?|\bstores?\b"), ("data-research", r"\bdata\b|research|analytics"),
    ("security", r"security"), ("product", r"product"), ("design", r"design"), ("engineering", r"engineering|technology|infrastructure|\bit\b|software|hardware"),
    ("operations", r"operations|\bops\b|admin|workplace"),
]
OTHER = ("other", "Other")

SKILLS = [
    ("Solidity", r"solidity"), ("Rust", r"\brust\b"), ("Go", r"golang|\bgoroutines?\b|(?<!to )\bgo[,/)]|[,/(] ?go\b(?![- ](?:to|live)\b)|\b(?:python|rust|java|c\+\+|typescript|javascript|node(?:\.js)?|kotlin|scala|ruby|php|c#|elixir|swift)(?:,| and| or| &) go\b(?![- ](?:to|live|ahead|above)\b)|\bgo (?:and|or|&) (?:python|rust|java|c\+\+|typescript|javascript|node(?:\.js)?|kotlin|scala|ruby|php|c#|elixir|swift)\b|\b(?:in|using|with|know|knows|write|writing|written in) go\b(?=[.;:)]|\s+(?:and|or)\b|$)|\bgo (?:developer|engineer|programmer|programming|microservices?|services|backend|codebase|code|modules?|stdlib|runtime)\b"), ("Python", r"python"),
    ("TypeScript", r"typescript"), ("JavaScript", r"javascript"), ("React", r"(?-i:\bReact\b)(?! to\b)|\breact\.?js\b|\breact native\b"), ("Node.js", r"node\.?js"),
    ("Java", r"\bjava\b"), ("C++", r"c\+\+"), ("Kotlin", r"kotlin"), ("Swift", r"(?-i:\bSwift\b)|\bswiftui\b"), ("SQL", r"\bsql\b"),
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
    ("Spring", r"\bspring (boot|framework|mvc|cloud)\b|springboot"), ("Rails", r"ruby on rails|\brails\b"), ("Laravel", r"laravel"), ("Flask", r"\bflask\b"), ("Svelte", r"svelte"),
    ("Unity", r"unity ?3d|unity engine|\bunity (developer|engineer|programmer)"), ("Unreal Engine", r"unreal engine|\bue[45]\b"), ("CUDA", r"\bcuda\b"), ("LangChain", r"langchain"),
    ("RAG", r"(?-i:\bRAG\b)|retrieval[- ]augmented"), ("Bash", r"\bbash\b"), ("Ansible", r"\bansible\b"), ("Jenkins", r"\bjenkins\b"), ("GitHub Actions", r"github actions"),
    ("Datadog", r"\bdatadog\b"), ("Prometheus", r"\bprometheus\b"), ("Grafana", r"\bgrafana\b"), ("Elasticsearch", r"elasticsearch|opensearch"), ("DynamoDB", r"dynamodb"),
    ("BigQuery", r"bigquery"), ("Redshift", r"\bredshift\b"), ("Databricks", r"\bdatabricks\b"), ("SAP", r"(?-i:\bSAP\b)"), ("MATLAB", r"\bmatlab\b"),
    ("ROS", r"(?-i:\bROS\b)|robot operating system"), ("Verilog", r"verilog"), ("Objective-C", r"objective[- ]c"), ("Perl", r"\bperl\b"), ("Power BI", r"power ?bi\b"),
    ("ClickHouse", r"clickhouse"), ("gRPC", r"\bgrpc\b"), ("WebAssembly", r"webassembly|\bwasm\b"), ("Playwright", r"\bplaywright\b"), ("Selenium", r"\bselenium\b"),
    ("Cypress", r"\bcypress\b(?! semiconductor)"), ("Pandas", r"\bpandas\b"), ("Hadoop", r"\bhadoop\b"), ("OpenTelemetry", r"opentelemetry"), ("Zendesk", r"\bzendesk\b"),
    ("NetSuite", r"netsuite"), ("Workday", r"(?-i:\bWorkday\b)"), ("Shopify", r"\bshopify\b"), ("Solana", r"\bsolana\b"), ("Ethereum", r"\bethereum\b|\bevm\b"),
    ("Zero-knowledge", r"zero[- ]knowledge|zk-?snarks?|\bzkp\b"), ("Embedded C", r"embedded c\b"), ("Computer Vision", r"computer vision"), ("NLP", r"(?-i:\bNLP\b)|natural language processing"),
]
TITLE_ONLY = {"DeFi", "NFT", "Trading", "AML/KYC", "AI", "iOS", "Android", "Salesforce"}  # too common in company boilerplate
PERKS = [   # (name, page slug, pattern) detected in the posting text
    ("Visa sponsorship", "visa-sponsorship", r"visa sponsorship|sponsor (a |your )?(work )?visas?|sponsorship (is )?available|we (can|will|do) sponsor"),
    ("Relocation support", "relocation", r"relocation (assistance|support|package|bonus|allowance)|(help|support) (you )?(to |with )?relocat"),
    ("Equity", "equity", r"stock options|\brsus?\b|equity (grant|package|compensation|awards?|stake|ownership)|(company|meaningful|generous|competitive|plus|salary (and|&)|bonus (and|&|,)) equity"),
    ("4-day week", "4-day-week", r"4[- ]day (work ?)?week|four[- ]day (work ?)?week"),
    ("Unlimited PTO", "unlimited-pto", r"unlimited (pto|paid time off|vacation|holiday|time off)"),
    ("Parental leave", "parental-leave", r"parental leave|maternity leave|paternity leave"),
    ("Learning budget", "learning-budget", r"learning (budget|stipend|allowance)|education (budget|stipend|allowance)|professional development (budget|stipend|allowance)"),
    ("No degree required", "no-degree", r"no (college |university |formal )?degree (is )?(required|needed|necessary)|degree (is )?not (required|needed|necessary)|(with or )?without a (college |university )?degree|or equivalent (practical |work |professional |relevant |industry )?experience|equivalent (practical|work|professional|industry) experience"),
    ("Home office stipend", "home-office-stipend", r"home office (stipend|budget|allowance|setup)|work[- ]from[- ]home (stipend|budget|allowance)|remote (work )?(stipend|allowance)"),
]
NO_VISA = re.compile(r"(not|unable|cannot|can['’]t|can not|no|won['’]t|will not|don['’]t|do not) (\w+ ){0,5}(sponsor|sponsorship)|without (\w+ ){0,3}sponsorship|sponsorship is(n['’]t| not)", re.I)
NO_RELO = re.compile(r"relocation (assistance|support|package|benefits?|bonus|allowance) (is|are|will) not|no relocation|(not|unable to|cannot|can['’]t|don['’]t|do not|won['’]t) (\w+ ){0,4}relocation|without relocation", re.I)


def perks(text):
    out = [name for name, _, rx in PERKS if re.search(rx, text, re.I)]
    if "Visa sponsorship" in out and NO_VISA.search(text): out.remove("Visa sponsorship")
    if "Relocation support" in out and NO_RELO.search(text): out.remove("Relocation support")
    return out


def etype(title, hint=""):
    """Employment type when the feed or the title says so; empty when unknown."""
    h, t = (hint or "").lower().replace(" ", "").replace("-", "").replace("_", ""), title.lower()
    if h in ("intern", "internship") or re.search(r"\bintern(ship)?s?\b|\bco-?op\b", t): return "Internship"
    # "contract" as a kind of job, not as a subject: "Smart Contract Engineer" and "Contracts Manager" are not contract work
    if h in ("contract", "contractor", "temporary", "temp", "fixedterm") or re.search(
            r"\(contract\)|[-–,:] ?contract\b|\bcontract[- ](to[- ]hire|role|position|basis)|\bcontractor\b|\d+[- ]?(month|week)s?[- ]contract|\btemporary\b|\bfreelance\b|fixed[- ]term", t):
        return "Contract"
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


class _Clean(HTMLParser):
    """Turns a posting's HTML into a small safe subset: paragraphs, lists, headings, bold and italic. No attributes, no links, no scripts."""
    BLOCK = {"p", "div", "section", "article", "header", "footer", "table", "tr", "blockquote", "pre"}
    HEAD = {"h1", "h2", "h3", "h4", "h5", "h6"}
    SKIP = {"script", "style", "iframe", "svg", "noscript", "form", "button", "select", "textarea", "head", "title", "video", "audio", "object"}
    INLINE = {"strong": "strong", "b": "strong", "em": "em", "i": "em"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.buf, self.lists, self.inline, self.skip, self.kind, self.in_li, self.auto = [], [], [], [], 0, "p", False, False

    def end_auto(self):            # a list we opened ourselves for a stray <li> ends at the next block
        if self.auto and self.lists and not self.in_li:
            self.emit(); self.out.append(f"</{self.lists.pop()}>"); self.auto = False

    def emit(self):
        raw = "".join(self.buf) + "".join(f"</{t}>" for t in reversed(self.inline))
        text = re.sub(r"\s+", " ", raw).strip()
        plain = re.sub(r"<[^>]+>", "", text).strip()
        if plain:
            if self.lists: self.out.append(f"<li>{text}</li>")              # anything inside a list is an item
            elif self.kind == "h": self.out.append(f"<h3>{plain}</h3>")
            else: self.out.append(f"<p>{text}</p>")
        self.buf = [f"<{t}>" for t in self.inline]

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP: self.skip += 1; return
        if self.skip: return
        if tag in ("ul", "ol"):
            self.emit(); self.out.append(f"<{tag}>"); self.lists.append(tag); self.in_li = False
        elif tag == "li":
            self.emit()
            if not self.lists: self.out.append("<ul>"); self.lists.append("ul"); self.auto = True
            self.in_li = True
        elif tag in ("td", "th"):
            self.buf.append(" ")
        elif tag in self.HEAD:
            self.end_auto(); self.emit(); self.kind = "h"
        elif tag in self.BLOCK or tag == "br":
            if self.in_li: self.buf.append(" ")
            else: self.end_auto(); self.emit(); self.kind = "p"
        elif tag in self.INLINE:
            t = self.INLINE[tag]
            if t not in self.inline: self.inline.append(t); self.buf.append(f"<{t}>")

    def handle_endtag(self, tag):
        if tag in self.SKIP: self.skip = max(0, self.skip - 1); return
        if self.skip: return
        if tag in ("ul", "ol"):
            self.emit()
            if self.lists: self.out.append(f"</{self.lists.pop()}>")
            self.in_li = False
        elif tag == "li":
            self.emit(); self.in_li = False
        elif tag in self.HEAD:
            self.emit(); self.kind = "p"
        elif tag in self.BLOCK:
            if self.in_li: self.buf.append(" ")
            else: self.emit(); self.kind = "p"
        elif tag in self.INLINE and self.inline and self.inline[-1] == self.INLINE[tag]:
            self.inline.pop(); self.buf.append(f"</{self.INLINE[tag]}>")

    def handle_data(self, data):
        if not self.skip: self.buf.append(html.escape(data, quote=False))

    def result(self, limit):
        self.emit()
        while self.lists: self.out.append(f"</{self.lists.pop()}>")
        kept, size, stack = [], 0, []
        for part in self.out:                                   # cut at a block boundary and close whatever list was open
            if size + len(part) > limit and part not in ("</ul>", "</ol>"): break
            kept.append(part); size += len(part)
            if part in ("<ul>", "<ol>"): stack.append(part[1:3])
            elif part in ("</ul>", "</ol>") and stack: stack.pop()
        kept += [f"</{t}>" for t in reversed(stack)]
        return re.sub(r"<(ul|ol)></\1>", "", "".join(kept))


def clean_html(raw, limit=12000):
    """The employer's description as safe, plain HTML (see _Clean), or "" if nothing readable is left."""
    if not raw: return ""
    p = _Clean()
    try:
        p.feed(raw); p.close()
        out = p.result(limit)
    except Exception:
        return ""
    return out if len(re.sub(r"<[^>]+>", "", out)) >= 200 else ""


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


def classify(title, dept=""):
    got = classify_title(title)
    if got != OTHER[0] or not dept: return got
    return next((slug for slug, rx in DEPT_CATS if re.search(rx, dept, re.I)), OTHER[0])


def classify_title(title):
    # what the person does comes before what the product is: "Cybersecurity Sales Specialist" is a sales job, "Senior Counsel, Security" a legal one
    if re.search(r"\b(sales|account executive|business development)\b|account manage", title, re.I) and not re.search(r"engineer|architect", title, re.I): return "sales-bd"
    if re.search(r"\bcounsel\b|\battorney\b|\bparalegal\b", title, re.I): return "compliance-legal"
    if re.search(r"recruit|talent acquisition|\bsourcer\b", title, re.I): return "people"
    if re.search(r"product marketing|marketing manager", title, re.I): return "marketing"
    if re.search(r"\bdata (engineer|scientist|analyst)|research (scientist|engineer)|machine learning|\bml\b", title, re.I) and re.search(r"scientist|analyst", title, re.I): return "data-research"
    for slug, name, rx in CATS:
        if re.search(rx, title, re.I):
            return slug
    return OTHER[0]


def level(title):
    t = title.lower()
    if re.search(r"\bintern(ship)?s?\b|\btrainee\b|\bco-?op\b|\bapprentice", t): return "Intern"
    staff = re.search(r"\bstaff\b", t) and not re.search(r"of (technical )?staff|technical staff|staff (accountant|attorney|nurse|writer|assistant|associate|counsel|auditor)", t)
    if re.search(r"head of|\bdirector\b|\bvp\b|vice president|\bchief\b(?! of staff)|\bprincipal\b|\blead\b", t) or staff: return "Lead"
    if re.search(r"\bsenior\b|\bsr\b\.?", t): return "Senior"
    # "Associate" in front of a role is a junior grade ("Associate Product Manager"); after it, it is a job noun ("Operations Associate")
    if re.search(r"\bjunior\b|\bjr\b\.?|entry[- ]level|new grad|\bgraduate\b|early[- ]career|^associate\b(?! (general counsel|director|creative director|vice president|vp|partner|principal))", t): return "Junior"
    return ""


PAY_SYM = {"US$": "$", "USD": "$", "$": "$", "CA$": "CA$", "C$": "CA$", "CAD": "CA$", "A$": "A$", "AUD": "A$", "£": "£", "GBP": "£", "€": "€", "EUR": "€"}
_CUR = r"US\$|CA\$|C\$|A\$|\$|£|€|USD|CAD|AUD|GBP|EUR"
_AMT = r"\d{2,3}(?:,\d{3})+(?:\.\d+)?|\d{2,3}(?:\.\d+)?\s?[kK]\b"
PAY_RNG = re.compile(rf"({_CUR})\s?({_AMT})\s?(?:USD|CAD|AUD|GBP|EUR)?\s?(?:-|–|—|to|and)\s?(?:{_CUR})?\s?({_AMT})(\s?(?:USD|CAD|AUD|GBP|EUR))?", re.I)
PAY_CTX = re.compile(r"salary|compensation|pay range|base pay|pay scale|base range|annual base|\bpay\b|\bOTE\b|on[- ]target earnings|wage", re.I)
PAY_NOT_YEARLY = re.compile(r"per hour|an hour|/ ?hour|hourly|/ ?hr\b|per month|a month|/ ?month|monthly|per day|/ ?day|daily|per week|weekly", re.I)


def pay_k(sym, lo, hi):
    return f"{sym}{lo / 1000:,.0f}K - {sym}{hi / 1000:,.0f}K"


def pay_from_text(text, location=""):
    """A yearly pay range written in the posting's own text ("The salary range for this role is $180,000 - $240,000"), or "".
    Deliberately strict: the range must sit next to a word about pay, be yearly, and look like a salary."""
    for m in PAY_RNG.finditer(text or ""):
        if not PAY_CTX.search(text[max(0, m.start() - 220):m.end() + 60]) or PAY_NOT_YEARLY.search(text[max(0, m.start() - 50):m.start()] + text[m.end():m.end() + 40]):
            continue
        num = lambda s: float(re.sub(r"[kK\s,]", "", s)) * (1000 if s.strip()[-1] in "kK" else 1)
        lo, hi = num(m.group(2)), num(m.group(3))
        if not (20000 <= lo <= hi <= 2000000 and hi <= 4 * lo): continue
        sym, tail = PAY_SYM[m.group(1).upper()], (m.group(4) or "").strip().upper()
        if sym == "$" and tail in ("CAD", "AUD"): sym = PAY_SYM[tail]
        if sym == "$":                                   # a bare dollar sign outside the US is usually the local dollar
            if re.search(r"canada|toronto|vancouver|montr[eé]al|ontario|ottawa|calgary", location, re.I): sym = "CA$"
            elif re.search(r"australia|sydney|melbourne|brisbane", location, re.I): sym = "A$"
            elif re.search(r"singapore|hong kong|new zealand|auckland", location, re.I): continue
        return pay_k(sym, lo, hi)
    return ""


def pay_from_greenhouse(ranges):
    """Greenhouse's structured pay ranges (several zones are merged into one overall range)."""
    ok = [r for r in (ranges or []) if isinstance(r, dict) and r.get("min_cents") and r.get("max_cents")]
    if not ok: return ""
    cur = ok[0].get("currency_type") or "USD"
    same = [r for r in ok if (r.get("currency_type") or "USD") == cur]
    lo, hi = min(r["min_cents"] for r in same) / 100, max(r["max_cents"] for r in same) / 100
    if hi > 3 * lo: lo, hi = same[0]["min_cents"] / 100, same[0]["max_cents"] / 100     # zones too far apart to be one range: show the first
    return tidy_pay(f"{lo:.0f} - {hi:.0f} {cur}")


YEARS_RX = re.compile(r"(\d{1,2})\s?\+?\s?(?:(?:-|–|to)\s?\d{1,2}\s?\+?\s?)?years?[’']?\s+(?:of\s+)?(?:[\w/&-]+\s+){0,4}?experience", re.I)


def years_asked(text):
    """The lowest number of years of experience the posting asks for ("5+ years of experience"), or 0 when it names none."""
    vals = [int(m.group(1)) for m in YEARS_RX.finditer(text or "") if 0 < int(m.group(1)) <= 20]
    return min(vals) if vals else 0


def tidy_pay(s):
    """One short, consistent pay string from whatever the feed gave: "$152K - $239K" for a year, "$38 - $55 an hour" otherwise.
    Returns "" when the text is not a usable figure (no numbers, an amount too small to be yearly with no unit, an absurd value)."""
    s = re.sub(r"\s+", " ", s or "").split(" • ")[0].strip()
    s = re.sub(r"(?<=\d) (?=\d{3}\b)", "", s)               # "180 000" is 180000
    if not s: return ""
    unit = ("an hour" if re.search(r"hour|/ ?hr\b", s, re.I) else "a month" if re.search(r"month", s, re.I) else "a week" if re.search(r"week", s, re.I)
            else "a day" if re.search(r"\bday\b|daily", s, re.I) else "")
    cur = re.search(r"US\$|CA\$|C\$|A\$|\$|£|€|\b(USD|CAD|AUD|GBP|EUR|SGD|INR|CHF|JPY|BRL|MXN|PLN|SEK|ILS|AED|HKD|NZD)\b", s)
    nums = [float(re.sub(r"[\s,]", "", n)) * (1000 if k else 1) for n, k in re.findall(r"(\d[\d,]*(?:\.\d+)?|\d[\d ]*\d)\s?([kK])?(?![\d%])", s)][:2]
    if not nums or not cur: return ""
    lo, hi = nums[0], nums[-1]
    if hi < lo: return ""
    code = cur.group(0).upper()
    sym = PAY_SYM.get(code, code + " ")
    if unit:
        return (f"{sym}{lo:,.0f} - {sym}{hi:,.0f} {unit}" if hi > lo else f"{sym}{lo:,.0f} {unit}")[:40]
    if lo < 15000 or (lo + hi) / 2 > 900000: return ""        # too small to be a yearly salary with no unit, or not a plausible one
    return (f"{sym}{lo / 1000:,.0f}K - {sym}{hi / 1000:,.0f}K" if hi > lo else f"{sym}{lo / 1000:,.0f}K").replace("  ", " ")


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_iso(v):
    """An exact time from a feed as UTC with seconds, "2026-11-13T09:05:52Z". Takes ISO 8601 text with a time and an offset
    (Greenhouse, Ashby) or milliseconds since 1970 (Lever). Returns "" for a bare date or anything unreadable: no time is better than a guessed one."""
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            t = datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc)
        else:
            s = str(v or "").strip()
            if "T" not in s.upper(): return ""                       # a day without a time
            t = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
            if t.tzinfo is None: return ""                           # a time without an offset cannot be placed
        return t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if t.year >= 2000 else ""
    except Exception:
        return ""


def norm(company, ats, jid, title, url, location, remote, dept, posted, text, salary="", hint="", desc="", hybrid=False, posted_at=None):
    title = re.sub(r"\s+", " ", str(title or "")).strip()
    location = re.sub(r"\s+", " ", str(location or "")).strip()
    hybrid = bool(hybrid) or bool(re.search(r"\bhybrid\b", location, re.I))
    remote = (bool(remote) or bool(re.search(r"\bremote\b", location, re.I))) and not (hybrid and not re.search(r"\bremote\b", location, re.I))
    limited = re.search(r"\b(us|usa|u\.s\.|united states|eu|europe|emea|apac|canada|uk|americas|latam|time ?zone|est|pst|cet)\b|anywhere in", location, re.I)
    if location.lower() in {"n/a", "na", "none", "tbd", "-", "null", "not specified"}: location = ""
    blob = title + "\n" + text
    return {
        "id": f"{ats}-{slugify(company)}-{jid}",
        "company": company, "title": title, "url": url, "location": location,
        "remote": remote, "hybrid": hybrid,
        "dept": (dept or "").strip(), "posted": (posted or "")[:10],
        "posted_at": utc_iso(posted_at),      # the exact publishing time when the feed gives one ("" otherwise); "posted" stays the day
        "excerpt": excerpt(text), "cat": classify(title, dept or ""), "level": level(title),
        "tags": [n for n, rx in SKILLS if re.search(rx, title if n in TITLE_ONLY else blob, re.I) and n.lower() not in company.lower()][:12],     # a company's own name in its postings is not a skill
        "russian": bool(re.search(r"\brussian\b", blob, re.I)),
        "salary": tidy_pay(salary) or pay_from_text(text, location),
        "perks": perks(text), "etype": etype(title, hint), "years": years_asked(text),
        # the full description is kept only for recent postings: that is where it matters most (DESC_SINCE says why not for all)
        "desc": clean_html(desc) if desc and (posted or "")[:10] >= DESC_SINCE else "",
        "anywhere": bool(re.search(r"worldwide|world-wide|\banywhere\b|\bglobal\b|any location", location, re.I)) and not limited,
        "_crypto": bool(CRYPTO_RE.search(blob)),
    }


_gate = {a: threading.Semaphore(n) for a, n in ATS_LIMIT.items()}
_next_at, _next_lock = defaultdict(float), threading.Lock()


def polite(key):
    """Wait until the hiring system (or the Workday board) named by key may be asked again: ATS_GAP apart, across all threads."""
    gap = ATS_GAP.get(key.split(":")[0], 0)
    if not gap: return
    with _next_lock:
        now = time.monotonic()
        at = max(now, _next_at[key])
        _next_at[key] = at + gap
    if at > now: time.sleep(at - now)


def fingerprint(raw):
    """A short fingerprint of what a feed says about one posting, and of these rules (RULES)."""
    return hashlib.md5((RULES + json.dumps(raw, sort_keys=True, ensure_ascii=False, default=str)).encode()).hexdigest()[:12]


PARSE = None        # main() puts a pool of worker processes here: norm() is CPU work, and threads share one CPU


def parse(*a, **k):
    """norm() in one of main()'s worker processes when there are some (the reading threads wait for it), else right here. A run
    after a change to this file parses every posting it reads again; with the processes that takes a quarter of the time on GitHub's
    four CPUs."""
    if PARSE:
        try: return PARSE.submit(norm, *a, **k).result()
        except (cf.process.BrokenProcessPool, RuntimeError): pass      # the pool is gone (a worker died, or it was shut down): parse here
    return norm(*a, **k)


EN_RX = re.compile(r"\b(the|and|you|your|with|our|we|will|are|for|this|of|to)\b", re.I)
NOT_EN_RX = re.compile(r"\b(und|der|die|das|mit|für|wir|sie|ist|eine?|och|att|med|för|vi|som|är|og|til|af|på|het|een|van|voor|wij|zijn|les|des|pour|avec|nous|vous|"
                       r"est|une|los|las|para|con|una|que|del|il|di|che|não|com|uma|dla|oraz|jest|się|ja|ole)\b", re.I)


# German job titles say so even when a posting has no text in the feed (Personio gives none when a job has no English version)
DE_TITLE_RX = re.compile(r"\([mwd]\s*/\s*[wm]\s*/\s*[dmw]\)|\b\w+:in(nen)?\b|\b(für|und|im|zum|zur|mit|bei|als|oder)\b|mitarbeiter|ausbildung|werkstudent|"
                         r"kauf(mann|frau)|fachkraft|sachbearbeiter|praktikum|pflegefach|erzieher|referendar|elektriker|monteur|bürokaufm|helfer", re.I)


def english(text):
    """Is a posting (its title and text) written in English? The short common words of English against those of the languages most
    boards on the newer systems use (German, Dutch, the Nordic languages, French, Spanish, Italian, Portuguese, Polish, Finnish).
    With too few such words to count, yes unless the title is plainly German."""
    t = (text or "")[:4000]
    en, other = len(EN_RX.findall(t)), len(NOT_EN_RX.findall(t))
    if en + other >= 8: return en >= other
    return not DE_TITLE_RX.search(t)


def fetch(src, reuse=None):
    """One board: (name, its postings as records), or (name, None) when the feed did not answer, which leaves the company as it was.
    reuse(id, fingerprint) gives the record of a posting that has not changed since the last read (see fetch_feed)."""
    gate = _gate.get(src.get("ats"))
    try:
        if gate: gate.acquire()
        return fetch_feed(src, reuse)
    except Exception as ex:                                    # an odd value in one feed: leave that company as it was and carry on
        print(f"feed error for {src.get('name')}: {type(ex).__name__}: {ex}")
        return src["name"], None
    finally:
        if gate: gate.release()


def wd_date(s):
    """Workday's "Posted Today", "Posted Yesterday", "Posted 3 Days Ago", "Posted 30+ Days Ago" as a day."""
    s = (s or "").lower()
    n = 0 if "today" in s else 1 if "yesterday" in s else int(m.group(1)) if (m := re.search(r"(\d+)\+? days?", s)) else None
    return (datetime.date.today() - datetime.timedelta(days=n)).isoformat() if n is not None else ""


def per_unit(per):
    """The words tidy_pay understands for a salary period a feed names ("hour", "monthly", "per_year"...)."""
    per = str(per or "").lower()
    return " per hour" if "hour" in per else " per month" if "month" in per else " per week" if "week" in per else " per day" if "day" in per else ""


def fetch_feed(src, reuse=None):
    """Read one board. reuse, when given, is asked for each posting: reuse(id, h) returns the record made from the same feed data
    (fingerprint h) last time, or None; reuse(id) returns the last record whatever changed, used when a posting's text could not be
    read this time. collect.main gives the records of data/jobs.json; live.py gives a stand-in for jobs the site already has."""
    name, ats, tok = src["name"], src["ats"], src["token"]
    out = []
    src["not_english"] = 0             # postings left out as not in English (the newer systems only), for discover_ats.py and the log

    def en(title, text):
        if english(f"{title}\n{text}"): return True
        src["not_english"] += 1
        return False

    def add(jid, raw, make):
        """The record of one posting: last run's when the feed says the same as then, else make() (which may return None)."""
        h = fingerprint(raw)
        rec = reuse(f"{ats}-{slugify(name)}-{jid}", h) if reuse else None
        if rec is None:
            rec = make()
            if rec is None: return
            rec["h"] = h
        out.append(rec)

    def details_from(posts, ident, raw_of, read):
        """Workday and SmartRecruiters: the postings' text costs one request each. Unchanged postings keep last run's record, at most
        DETAILS others are read (the list is newest first), and a posting not read this time keeps its old record if it has one."""
        asked = 0
        for p in posts:
            jid, raw = ident(p), raw_of(p)
            full_id = f"{ats}-{slugify(name)}-{jid}"
            if reuse and (rec := reuse(full_id, fingerprint(raw))) is not None:
                out.append(rec); continue
            rec = None
            if asked < DETAILS:
                asked += 1
                rec = read(p, jid)
                if rec is not None: rec["h"] = fingerprint(raw)
            if rec is None and reuse: rec = reuse(full_id)
            if rec is not None: out.append(rec)

    if ats == "greenhouse":
        d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true&pay_transparency=true", 60)
        if not d or "jobs" not in d: return name, None
        for j in d["jobs"]:
            dept = ", ".join(x.get("name", "") for x in (j.get("departments") or []))
            add(j["id"], j, lambda: parse(name, ats, j["id"], j.get("title"), j.get("absolute_url"), (j.get("location") or {}).get("name"),
                                         False, dept, j.get("first_published") or j.get("updated_at"), strip_html(j.get("content")), pay_from_greenhouse(j.get("pay_input_ranges")), "", html.unescape(j.get("content") or ""),
                                         posted_at=j.get("first_published")))          # the publishing time; "updated_at" moves with every edit, so it is never used as the exact time
    elif ats == "lever":
        d = get_json(f"https://api.lever.co/v0/postings/{tok}?mode=json", 60)
        if not isinstance(d, list): return name, None
        for j in d:
            def make(j=j):
                c = j.get("categories") or {}
                text = "\n".join([j.get("descriptionPlain") or ""] + [f"{l.get('text','')}\n{strip_html(l.get('content'))}" for l in (j.get("lists") or [])])
                posted = datetime.datetime.fromtimestamp(j["createdAt"] / 1000, datetime.timezone.utc).date().isoformat() if j.get("createdAt") else ""
                sr = j.get("salaryRange") or {}
                sal = f"{sr.get('min'):.0f} - {sr.get('max'):.0f} {sr.get('currency', '')}{per_unit(sr.get('interval'))}" if sr.get("min") and sr.get("max") else ""
                return parse(name, ats, j["id"], j.get("text"), j.get("hostedUrl"), c.get("location"), j.get("workplaceType") == "remote",
                            c.get("team") or c.get("department"), posted, text, sal, c.get("commitment") or "",
                            (j.get("description") or "") + "".join(f"<h3>{html.escape(l.get('text', ''))}</h3><ul>{l.get('content', '')}</ul>" for l in (j.get("lists") or [])) + (j.get("additional") or ""),
                            posted_at=j.get("createdAt"))                # milliseconds; the only time Lever's public feed has
            add(j["id"], j, make)
    elif ats == "ashby":
        d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=true", 60)
        if not d or "jobs" not in d: return name, None
        for j in d["jobs"]:
            def make(j=j):
                comp = (j.get("compensation") or {})
                sal = comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary") or ""
                wt = str(j.get("workplaceType") or "").lower()          # Ashby sets isRemote for hybrid roles too, so the workplace type decides
                return parse(name, ats, j["id"], j.get("title"), j.get("jobUrl") or j.get("applyUrl"), j.get("location"), wt == "remote" if wt else j.get("isRemote"),
                            j.get("department") or j.get("team"), j.get("publishedAt"), j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")), sal, j.get("employmentType") or "", j.get("descriptionHtml") or "", wt == "hybrid", posted_at=j.get("publishedAt"))
            add(j["id"], j, make)
    elif ats == "workable":
        # The careers-page widget's feed: every published job with its text in one request (the v3 list would need one more per job).
        polite(ats)
        d = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{tok}?details=true", 60)
        if not isinstance(d, dict) or not isinstance(d.get("jobs"), list): return name, None
        for j in d["jobs"]:
            def make(j=j):
                locs = [l for l in (j.get("locations") or []) if isinstance(l, dict)]
                shown = [l for l in locs if not l.get("hidden")] or locs[:1]
                loc = "; ".join(", ".join(x for x in (l.get("city"), l.get("region"), l.get("country")) if x) for l in shown[:3]) or \
                      ", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x)
                text = strip_html(j.get("description"))
                if not en(j.get("title"), text): return None
                return parse(name, ats, j.get("shortcode"), j.get("title"), j.get("url") or j.get("shortlink"), loc, j.get("telecommuting"), j.get("department") or j.get("function"),
                            j.get("published_on") or j.get("created_at"), text, "", j.get("employment_type") or "", j.get("description") or "")
            if j.get("shortcode"): add(j["shortcode"], j, make)
    elif ats == "recruitee":
        polite(ats)
        d = get_json(f"https://{tok}.recruitee.com/api/offers/", 60)
        if not isinstance(d, dict) or not isinstance(d.get("offers"), list): return name, None
        codes = {"intern": "intern", "parttime": "parttime", "contract": "contract", "freelance": "contract", "temporary": "temporary", "fixed": "fixedterm", "fulltime": "fulltime"}
        for j in d["offers"]:
            if j.get("status") not in (None, "published"): continue
            def make(j=j):
                text = strip_html((j.get("description") or "") + "\n" + (j.get("requirements") or ""))
                if not en(j.get("title"), text): return None
                locs = [l for l in (j.get("locations") or []) if isinstance(l, dict)]
                loc = "; ".join(", ".join(x for x in (l.get("city"), l.get("country")) if x) for l in locs[:3]) if len(locs) > 1 else \
                      j.get("location") or ", ".join(x for x in (j.get("city"), j.get("country")) if x)
                s = j.get("salary") or {}
                sal = f"{s.get('min')} - {s.get('max')} {s.get('currency') or ''}{per_unit(s.get('period'))}" if s.get("min") and s.get("max") else ""
                code = str(j.get("employment_type_code") or "").replace("_", "")
                at = str(j.get("published_at") or j.get("created_at") or "").replace(" UTC", "+00:00").replace(" ", "T", 1)
                desc = (j.get("description") or "") + (f"<h3>Requirements</h3>{j['requirements']}" if j.get("requirements") else "")
                return parse(name, ats, j["id"], j.get("title"), j.get("careers_url"), loc, j.get("remote"), j.get("department"), at[:10], text, sal,
                            next((v for k, v in codes.items() if k in code), ""), desc, j.get("hybrid"), posted_at=at)
            if j.get("id"): add(j["id"], j, make)
    elif ats == "teamtailor":
        # The public RSS feed of the careers site (it has the remote status, the department and the places, which the JSON feed lacks).
        host = tok if "." in tok else f"{tok}.teamtailor.com"
        polite(ats)
        x = get_text(f"https://{host}/jobs.rss", 60, accept="application/rss+xml")
        try: channel = ET.fromstring(x).find("channel") if x else None
        except ET.ParseError: channel = None
        items = channel.findall("item") if channel is not None else None
        if items is None: return name, None
        tt = "{https://teamtailor.com/locations}"
        for it in items:
            link = (it.findtext("link") or "").strip()
            m = re.search(r"/jobs/(\d+)", link)
            if not m: continue
            raw = {c.tag: (c.text or "").strip() for c in it if c.tag != f"{tt}locations"}
            raw["places"] = [[(g.text or "").strip() for g in l] for l in it.iter(f"{tt}location")]
            def make(it=it, link=link, jid=m.group(1)):
                desc = it.findtext("description") or ""
                text = strip_html(desc)
                title = (it.findtext("title") or "").strip()
                if not en(title, text): return None
                places = [", ".join(x for x in (l.findtext(f"{tt}city"), l.findtext(f"{tt}country")) if x) for l in it.iter(f"{tt}location")]
                status = (it.findtext("remoteStatus") or "").lower()          # none, hybrid, temporary or fully
                try: at = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "").isoformat()
                except Exception: at = ""
                return parse(name, ats, jid, title, link, "; ".join(p for p in places[:3] if p), status == "fully", it.findtext(f"{tt}department") or "",
                            at[:10], text, "", "", desc, status == "hybrid", posted_at=at)
            add(m.group(1), raw, make)
    elif ats == "personio":
        host = tok if "." in tok else f"{tok}.jobs.personio.de"
        polite(ats)
        x = get_text(f"https://{host}/xml?language=en", 60, accept="application/xml")
        try: posts = ET.fromstring(x).findall("position") if x else None
        except ET.ParseError: posts = None
        if posts is None: return name, None
        kinds = {"intern": "intern", "trainee": "intern", "working_student": "intern", "freelance": "contract", "temporary": "temporary"}
        for p in posts:
            jid = (p.findtext("id") or "").strip()
            if not jid: continue
            raw = {c.tag: (c.text or "").strip() for c in p if c.tag != "jobDescriptions"}
            raw["d"] = [((d.findtext("name") or ""), (d.findtext("value") or "")) for d in p.iter("jobDescription")]
            raw["o"] = [o.text for o in p.iter("office")]
            def make(p=p, jid=jid, raw=raw):
                desc = "".join(f"<h3>{html.escape(n.strip())}</h3>{v}" for n, v in raw["d"])
                text = strip_html(desc)
                title = (p.findtext("name") or "").strip()
                if not text.strip():                       # asked for English, Personio leaves out the text of a job that has no English version
                    src["not_english"] += 1; return None
                if not en(title, text): return None
                offices = list(dict.fromkeys(o.strip() for o in raw["o"] if o and o.strip()))
                kind = (p.findtext("employmentType") or "").strip()
                hint = kinds.get(kind) or ("parttime" if "part" in (p.findtext("schedule") or "") else "fulltime" if kind == "permanent" else "")
                at = (p.findtext("createdAt") or "").strip()
                return parse(name, ats, jid, title, f"https://{host}/job/{jid}?language=en", "; ".join(offices[:3]), False, p.findtext("department") or "",
                            at[:10], text, "", hint, desc, posted_at=at)
            add(jid, raw, make)
    elif ats == "workday":
        # The JSON the careers site itself reads ("cxs"). The token is "<tenant>.<wdN>/<site>", from <tenant>.<wdN>.myworkdayjobs.com/<site>.
        host, site = tok.split("/", 1)
        base = f"https://{host}.myworkdayjobs.com/wday/cxs/{host.split('.')[0]}/{site}"
        posts, total = [], None
        while len(posts) < LIST_MAX:
            polite(f"workday:{host}")
            d = post_json(base + "/jobs", {"appliedFacets": {}, "limit": 20, "offset": len(posts), "searchText": ""}, 40)
            if not isinstance(d, dict) or not isinstance(d.get("jobPostings"), list):
                return name, None                               # a list cut short would close the jobs on its later pages
            if total is None: total = int(d.get("total") or 0)  # only the first page gives the total
            posts += d["jobPostings"]
            if not d["jobPostings"] or len(posts) >= total: break
        def ident(p):
            tail = str(p.get("externalPath") or "").rstrip("/").rsplit("/", 1)[-1]
            return tail.rsplit("_", 1)[-1] if "_" in tail else slugify(tail)[:40]
        def read(p, jid):
            polite(f"workday:{host}")
            info = (get_json(base + p["externalPath"], 40) or {}).get("jobPostingInfo")
            if not isinstance(info, dict) or not info.get("title"): return None
            text = strip_html(info.get("jobDescription"))
            if not en(info['title'], text): return None
            more = info.get("additionalLocations") if isinstance(info.get("additionalLocations"), list) else []
            loc = "; ".join([info.get("location") or p.get("locationsText") or ""] + [str(x) for x in more[:2]])
            kind = str(info.get("remoteType") or "").lower()
            return parse(name, ats, jid, info["title"], info.get("externalUrl") or f"https://{host}.myworkdayjobs.com/{site}{p['externalPath']}", loc,
                        kind in ("remote", "fully remote", "virtual"), "", info.get("startDate") or wd_date(info.get("postedOn") or p.get("postedOn")), text, "",
                        info.get("timeType") or "", info.get("jobDescription") or "", kind == "hybrid")
        # "postedOn" ("Posted 3 Days Ago") changes every day, so it is not part of a posting's fingerprint
        details_from([p for p in posts if p.get("externalPath") and p.get("title")], ident,
                     lambda p: {k: p.get(k) for k in ("title", "externalPath", "locationsText", "bulletFields")}, read)
    elif ats == "smartrecruiters":
        # The Posting API: a list (100 a request) without the text, then one request per posting for it.
        base = f"https://api.smartrecruiters.com/v1/companies/{tok}/postings"
        posts, total = [], None
        while len(posts) < LIST_MAX:
            polite(ats)
            d = get_json(f"{base}?limit=100&offset={len(posts)}", 40)
            if not isinstance(d, dict) or not isinstance(d.get("content"), list): return name, None
            total = int(d.get("totalFound") or 0)
            posts += d["content"]
            if not d["content"] or len(posts) >= total: break
        def read(p, jid):
            polite(ats)
            full = get_json(f"{base}/{jid}", 40)
            if not isinstance(full, dict): return None
            secs = ((full.get("jobAd") or {}).get("sections") or {})
            parts = [secs.get(k) or {} for k in ("jobDescription", "qualifications", "additionalInformation", "companyDescription")]
            desc = "".join(f"<h3>{html.escape(s.get('title') or '')}</h3>{s.get('text')}" for s in parts if s.get("text"))
            text = strip_html(desc)
            if not en(p.get('name'), text): return None
            l = p.get("location") or {}
            loc = l.get("fullLocation") or ", ".join(x for x in (l.get("city"), l.get("region"), str(l.get("country") or "").upper()) if x)
            return parse(name, ats, jid, p.get("name"), full.get("postingUrl") or f"https://jobs.smartrecruiters.com/{tok}/{jid}", loc, l.get("remote"),
                        (p.get("department") or {}).get("label") or (p.get("function") or {}).get("label") or "", p.get("releasedDate"), text, "",
                        (p.get("typeOfEmployment") or {}).get("label") or "", desc, l.get("hybrid"), posted_at=p.get("releasedDate"))
        english_ones = [p for p in posts if p.get("id") and p.get("name") and str((p.get("language") or {}).get("code") or "en").lower().startswith("en")]
        details_from(english_ones, lambda p: p["id"], lambda p: {k: v for k, v in p.items() if k != "creator"}, read)
    else:
        return name, None
    return name, out


def direct_and_paid(db, used_slugs, indexed, stats):
    """Jobs employers posted in their account, and paid placements, from our own API ("api_url" in config.json).
    A failed call changes nothing: posted jobs stay as they were and the previous placements file is kept."""
    api = (os.environ.get("HRN_API_URL") or json.loads((ROOT / "config.json").read_text()).get("api_url", "")).rstrip("/")
    if not api: return
    exp = None
    for _ in range(3):
        exp = get_json(api + "/api/public/export.json", 30)
        if isinstance(exp, dict) and isinstance(exp.get("jobs"), list): break
        exp = None
    if exp is None:
        print("placements: API did not answer, keeping what we have"); return
    seen = set()
    for d in exp["jobs"]:
        if not isinstance(d, dict) or str(d.get("company", "")).strip().lower() in indexed: continue   # a posting may not pass itself off as an indexed company
        j = norm(str(d.get("company", "")).strip(), "direct", d.get("id", ""), d.get("title"), d.get("url"), d.get("location"), bool(d.get("remote")), "",
                 d.get("posted"), str(d.get("text") or ""), str(d.get("salary") or ""), str(d.get("etype") or ""))
        j.pop("_crypto")
        if not j["title"] or not j["company"] or not str(j["url"]).startswith("https://"): continue
        j.update(crypto=False, direct=True, featured_until=str(d.get("featured_until") or ""), pinned_until=str(d.get("pinned_until") or ""))
        seen.add(j["id"])
        old = db.get(j["id"])
        if old:
            j.update(slug=old["slug"], first_seen=old["first_seen"])
            if old.get("first_seen_at"): j["first_seen_at"] = old["first_seen_at"]
        else:
            base = f"{slugify(j['title'])}-{slugify(j['company'])}"
            slug, i = base, 2
            while slug in used_slugs:
                slug, i = f"{base}-{i}", i + 1
            used_slugs.add(slug)
            j.update(slug=slug, first_seen=TODAY, first_seen_at=utc_now())
            stats["new"] += 1
        j.update(last_seen=TODAY, active=True)
        db[j["id"]] = j
    for jid, old in db.items():
        if old.get("direct") and old["active"] and jid not in seen:
            old.update(active=False, closed=TODAY); stats["closed"] += 1
    keep = lambda rows, keys: [{k: str(r.get(k, "")) for k in keys} for r in rows if isinstance(r, dict)]
    (ROOT / "data" / "placements.json").write_text(json.dumps({"boosts": keep(exp.get("boosts") or [], ("slug", "kind", "until")),
                                                               "sponsors": keep(exp.get("sponsors") or [], ("company", "slot", "until"))}, ensure_ascii=False))
    print(f"placements: {len(seen)} posted jobs, {len(exp.get('boosts') or [])} promoted, {len(exp.get('sponsors') or [])} sponsors")


def main():
    sources = [dict(s, crypto=True) for s in json.loads((ROOT / "sources.json").read_text()) if s["name"] not in EXCLUDE]
    tech_file = ROOT / "sources_tech.json"
    taken = {(s["ats"], s["token"]) for s in sources} | {s["name"].lower() for s in sources}
    for s in (json.loads(tech_file.read_text()) if tech_file.exists() else []):
        if (s["ats"], s["token"]) not in taken and s["name"].lower() not in taken and s["name"] not in EXCLUDE_TECH:
            sources.append(dict(s, crypto=False)); taken |= {(s["ats"], s["token"]), s["name"].lower()}
    # Boards added on 14 Nov 2026, once the site moved to its own server and the 1 GB limit of GitHub Pages was gone
    # (sources_more.json, about 3,000 boards picked from sources_candidates.json: office and tech work, no agencies). Reading
    # them all every hour would not fit in the hour, so each run reads one share of them (HRN_ROTATE shares, 4 by default:
    # every board every 4 hours). A board resting this hour keeps its jobs exactly as they were. The same goes for the boards on the
    # other hiring systems (sources_ats.json, 15 Nov 2026) and the rest of the candidate list, added to sources_more.json that day.
    # Workday and SmartRecruiters boards (SLOW_ATS) take one share in twice as many (every 8 hours by default). live.py on our server
    # reads every board at least once an hour whatever this rotation does.
    resting = set()
    rot = max(1, int(os.environ.get("HRN_ROTATE") or 4))
    hour = datetime.datetime.now(datetime.timezone.utc).hour
    for f in ROTATING:
        for s in (json.loads((ROOT / f).read_text()) if (ROOT / f).exists() else []):
            if s.get("hold"): continue                     # verified, but waiting until the hourly build can take its jobs (ATS_REPORT.md)
            if (s["ats"], s["token"]) in taken or s["name"].lower() in taken or s["name"] in EXCLUDE_TECH: continue
            taken |= {(s["ats"], s["token"]), s["name"].lower()}
            r = rot * 2 if s["ats"] in SLOW_ATS else rot
            if int(hashlib.md5(s["token"].encode()).hexdigest(), 16) % r == hour % r:
                sources.append(dict(s, crypto=False))
            else:
                resting.add(s["name"])
    is_crypto = {s["name"]: s["crypto"] for s in sources}
    # Each hiring system's boards spread evenly through the list, so the systems with a limit on boards read at once (ATS_LIMIT)
    # never hold most of the workers waiting.
    by_ats = defaultdict(list)
    for s in sources: by_ats[s["ats"]].append(s)
    sources = [s for _, s in sorted((((i + 0.5) / len(xs), s) for xs in by_ats.values() for i, s in enumerate(xs)), key=lambda t: t[0])]
    db = json.loads(DATA.read_text()) if DATA.exists() else {}
    used_slugs = {j["slug"] for j in db.values()}
    stats = {"new": 0, "closed": 0, "failed": [], "dropped": [], "emptied": [], "parsed": 0}

    def reuse(jid, h=None):
        """The record of a posting from the last run, ready to be stored again: when the feed says the same as then (h), or (no h)
        whatever changed, for a posting whose text could not be read this time (fetch_feed)."""
        old = db.get(jid)
        if not old or (h is not None and old.get("h") != h): return None
        rec = dict(old, _crypto=True)          # only the boards of sources.json are checked for crypto, and those are always parsed
        if (rec.get("posted") or "") < DESC_SINCE: rec["desc"] = ""
        return rec
    read = lambda s: fetch(s, None if s["crypto"] else reuse)
    t0 = time.time()
    # Reading is waiting for answers, 32 boards at a time (20 before 15 Nov 2026); parsing a posting that changed is CPU work, done in
    # one worker process per CPU (parse). Before 15 Nov a run was mostly parsing, on one CPU, with every posting parsed every hour.
    global PARSE
    import multiprocessing
    PARSE = cf.ProcessPoolExecutor(int(os.environ.get("HRN_PARSERS") or os.cpu_count() or 2), mp_context=multiprocessing.get_context("spawn"))
    try:
        with cf.ThreadPoolExecutor(int(os.environ.get("HRN_WORKERS") or 32)) as ex:
            results = list(ex.map(read, sources))
        # second, gentler pass for feeds that timed out or were rate-limited the first time
        by_name = {s["name"]: s for s in sources}
        retry = [by_name[name] for name, jobs in results if jobs is None]
        if retry:
            with cf.ThreadPoolExecutor(3) as ex:
                again = dict(ex.map(read, retry))
            results = [(name, again.get(name) if jobs is None else jobs) for name, jobs in results]
    finally:
        PARSE.shutdown(); PARSE = None
    read_s = time.time() - t0
    not_en = sum(s.get("not_english", 0) for s in sources)
    seen_at = utc_now()                                     # when this run finished reading the feeds: the "first seen" time of every job that is new in it
    open_by_co = defaultdict(list)                          # the open jobs of each company, found once instead of once per board
    for jid, old in db.items():
        if old["active"] and not old.get("tg"): open_by_co[old["company"]].append(jid)       # a Telegram job is not closed by the company's own board
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
            if not old or old.get("h") != j.get("h"): stats["parsed"] += 1
            if old:
                j.update(slug=old["slug"], first_seen=old["first_seen"])
                if old.get("first_seen_at"): j["first_seen_at"] = old["first_seen_at"]      # jobs first seen before exact times were kept have none
            else:
                base = f"{slugify(j['title'])}-{slugify(name)}"
                slug, i = base, 2
                while slug in used_slugs:
                    slug, i = f"{base}-{i}", i + 1
                used_slugs.add(slug)
                j.update(slug=slug, first_seen=TODAY, first_seen_at=seen_at)
                stats["new"] += 1
            j.update(last_seen=TODAY, active=True)
            j.pop("closed", None)
            db[j["id"]] = j
        gone = [db[jid] for jid in open_by_co.get(name, ()) if db[jid]["active"] and jid not in seen]
        for old in gone:
            old.update(active=False, closed=TODAY); stats["closed"] += 1
        if not jobs and len(gone) >= 20:
            stats["emptied"].append(name)                   # the whole board went empty at once: often a move to another hiring system
    known = {s["name"] for s in sources} | resting             # a company we no longer read cannot keep "open" jobs forever; one resting this hour can
    for old in db.values():
        if old["active"] and not old.get("direct") and not old.get("tg") and old["company"] not in known:
            old.update(active=False, closed=TODAY); stats["closed"] += 1
    DATA.parent.mkdir(exist_ok=True)
    direct_and_paid(db, used_slugs, {s["name"].lower() for s in sources}, stats)
    if os.environ.get("HRN_TELEGRAM", "1") != "0":                 # jobs from public Telegram job channels (telegram_jobs.py)
        try:
            import telegram_jobs
            telegram_jobs.collect(db, used_slugs, {s["name"].lower() for s in sources} | {n.lower() for n in resting}, stats,
                                  norm, slugify, excerpt, classify, level, etype, TODAY, utc_now())
        except Exception as ex:                                     # the channels never stop the hourly update
            print(f"telegram: skipped this run: {type(ex).__name__}: {ex}")
    DATA.write_text(json.dumps(db, ensure_ascii=False, indent=0))
    active = sum(j["active"] for j in db.values())
    print(f"read {len(sources)} boards in {read_s:.0f} s ({len(resting)} resting this hour); {stats['parsed']} postings parsed, the rest unchanged "
          f"since the last run; {not_en} left out as not in English")
    print(f"active {active}, archived {len(db) - active}, new {stats['new']}, closed {stats['closed']}")
    # what this run did, shown on the site's data status page
    (ROOT / "data" / "stats.json").write_text(json.dumps({"date": TODAY, "time": datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC"), "sources": len(sources),
                                                          "failed": stats["failed"], "emptied": stats["emptied"], "new": stats["new"], "closed": stats["closed"], "active": active}, ensure_ascii=False))
    print("failed:", ", ".join(stats["failed"]) or "-")
    print("boards that went empty (check whether the company moved its job board):", ", ".join(stats["emptied"]) or "-")
    print("dropped as not crypto:", ", ".join(stats["dropped"]) or "-")


if __name__ == "__main__":
    main()
