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
from net import get_bytes, get_json, get_text, post_json
import jobsdb

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "jobs.json"
TODAY = datetime.date.today().isoformat()
# Full descriptions are stored for postings newer than this. GitHub Pages' size limit is gone (the site is served by our own server),
# but data/jobs.json is pushed to the data branch every hour and every description is about 5 KB, so the old ones are still left out.
DESC_SINCE = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
# RULES is part of every fingerprint: new rules, new records. It is made from this file WITHOUT the parts between the marks
# "# >>> not rules" and "# <<< not rules": how fast and how many boards are read, the jobs posted in the account, and main().
# Before 18 Nov 2026 it was made from the whole file, so every edit of those parts made each run parse every posting again
# (107,909 postings and 47 minutes a run on that day, after five such edits). A change to how a posting is read still counts.
def _rules_text():
    return re.sub(r"(?ms)^# >>> not rules.*?^# <<< not rules[^\n]*\n", "", Path(__file__).read_text(encoding="utf-8"))


RULES = hashlib.md5(_rules_text().encode()).hexdigest()[:8]
# >>> not rules (how the boards are read, not what a record says)
# Boards read in turn rather than every hour (main): the large lists added once the 1 GB limit of GitHub Pages was gone.
ROTATING = ("sources_more.json", "sources_ats.json", "sources_gov.json", "sources_jazz.json", "sources_breezy.json", "sources_bamboo.json",
            "sources_paylocity.json", "sources_pinpoint.json", "sources_gem.json", "sources_trakstar.json", "sources_rippling.json",
            "sources_icims.json", "sources_hn.json")
# Politeness per hiring system: how many of its boards are read at the same time, and the shortest gap in seconds between two of our
# requests to it (across all boards; Workday's tenants each have their own address, so there the gap is per board).
# Workday: 48 boards at a time since 18 Nov 2026 (12 before). Each tenant has its own address and still gets one request every 0.3 s.
# With 134 released boards read on every run (a list of up to 50 pages and 120 texts each, at about a second and a half a request),
# 12 at a time took 54 minutes of a run and 24 at a time about 25; the run's limit is 55.
# JazzHR (19 Nov 2026): every customer's board is a subdomain of applytojob.com, one service, so 4 boards at a time and at most four
# requests a second in all; its pages take a second or two to answer, so in practice it is two or three a second.
# Breezy and BambooHR (19 Nov 2026): one service each as well (every board a subdomain), so the same care as JazzHR.
# Paylocity (20 Nov 2026): every board on one address (recruiting.paylocity.com), its pages a second or so: the same.
# BambooHR and Paylocity 8 at a time since 20 Nov 2026: about 4,000 boards each, a read 23 to 32 s of waiting for their answers, so
# 4 at a time came round to a board every 7 to 9 hours. The gap between two requests (ATS_GAP) still caps the rate at 3 and 2.5 a second.
# Pinpoint (20 Nov 2026): every board a subdomain of pinpointhq.com, the whole board with its texts in one request: 4 at a time.
# Gem and Trakstar (20 Nov 2026): one API each for all their boards, the texts in the list: the same. Rippling the same, with one
# request a posting for its text.
ATS_LIMIT = {"usajobs": 2, "workday": 48, "smartrecruiters": 2, "workable": 4, "recruitee": 6, "teamtailor": 6, "personio": 6, "jazzhr": 4,
             "breezy": 4, "bamboohr": 8, "paylocity": 8, "pinpoint": 4, "gem": 4, "trakstar": 4, "rippling": 4, "icims": 4}
ATS_GAP = {"usajobs": 0.5, "workday": 0.3, "smartrecruiters": 0.5, "workable": 0.25, "recruitee": 0.1, "teamtailor": 0.1, "personio": 0.1, "jazzhr": 0.5,
           "breezy": 0.3, "bamboohr": 0.3, "paylocity": 0.4, "pinpoint": 0.3, "gem": 0.3, "trakstar": 0.3, "rippling": 0.3, "icims": 0.5}
# Workday and SmartRecruiters list a board's postings without their text, which takes one more request per posting. Only new or
# changed postings are asked for, at most this many per board in one read (the newest first); the rest wait for the next read.
# 120 since 18 Nov 2026 (40 before): a board of 1,000 jobs released from hold got 40 texts on each of its reads, and its turn comes
# once in eight hourly runs, of which GitHub starts only a few a day, so the board needed weeks to fill and the record grew by a
# few thousand jobs a day instead of the 18,000 planned. At one request every 0.3 s to a board that is 36 seconds of reading.
DETAILS = int(os.environ.get("HRN_DETAILS") or 120)
# A board released from hold in the last ten days ("lifted" in the sources file) is read on every run, not only on its turn, until
# its backlog is in.
FILL_SINCE = (datetime.date.today() - datetime.timedelta(days=10)).isoformat()
# Workday, SmartRecruiters: the newest this many postings of a board (Workday lists 20 per request). 3,000 since 20 Nov 2026 (1,000
# before): 25 Workday boards stood at the limit (NVIDIA, Micron, Morgan Stanley, Northrop Grumman, the State of Georgia...); Workday
# gives their later pages too, every posting once (Morgan Stanley: 1,154 of 1,154 distinct), and a board's total (NVIDIA shows 2,000,
# Micron 2,897) ends the reading as before.
LIST_MAX = 3000
SLOW_ATS = {"workday", "smartrecruiters"}     # many requests a board: the hourly run reads them half as often as the other rotating boards
# JazzHR too: its list is one request a board, but there are thousands of boards on one service, each new posting is a page of its
# own, and live.py would otherwise read a board that changed in the last day every 10 minutes. Every 8 hours here, hourly in live.py.
SLOW_ATS |= {"jazzhr", "breezy", "bamboohr", "paylocity", "rippling", "icims"}
# <<< not rules

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
# Added 16 Nov 2026 (AUDIT 62-66: "Other" held one open job in twelve, 12,575 of them). Tried last, after the title rules above and the
# department: a job that already had a category keeps it. Every pattern comes from a count of the titles that were left in "Other".
CATS_LATE = [
    ("healthcare", "Healthcare", r"surgeon|anesthesi|pathologist|psycholog|psychiatr|social worker|medication aide|respiratory|radiolog|physician|dermatolog|cardiolog|pediatric|"
                                 r"oncolog|\bcna\b|nurse aide|patient (care|access|service)|animal care|speech[- ](language )?(pathol|therap)|occupational therap|physical therap|"
                                 r"health information|\bdoctor\b|\bdentist|dental hygienist|pharmacy|phlebotom|sonograph|caregiver|home health"),
    ("retail", "Retail & Hospitality", r"\bbaker\b|\bserver\b|wait ?staff|stocker|grocery|bartender|dishwasher|\bkitchen\b(?! install)|\bhostess\b|\bdeli\b|\bbutcher|line cook|food service"),
    ("manufacturing", "Manufacturing & Trades", r"janitor|groundskeeper|custodia|landscap|\blaborer\b|install(ation)? helper|\bsuperintendent\b|\bhelper\b|\bwarehouse\b|housekeeping|\bpainter\b|roofing|carpent"),
    ("sales-bd", "Sales & Business Development", r"\bcomercial\b|\bcommerciale\b|\bcommercial (manager|executive|director|associate)|\bcanvass|vendas|\bventas\b|\bvendedor"),
    ("support", "Customer Service & Support", r"atendimento|atenci[oó]n al cliente|customer care|client care|\bcall cent(er|re)\b|servicio al cliente"),
    ("marketing", "Marketing & Community", r"paid (social|search|media)|media (activation|planner|buyer|manager)|\bcampaign|\beditor\b|\bwriter\b|journalist|\bproducer\b|public relations|\bpublicist|videograph|photograph|\bsocial\b"),
    ("education", "Education & Training", r"\bteaching\b|paraprofessional|\bschool\b|teacher|\bstudent (ambassador|success|services|affairs)|\bacademic\b|training specialist"),
    ("finance", "Finance & Trading", r"portfolio manager|\bwealth\b|valuations?|estate planning|private client|\bequit(y|ies)\b|investment|\bunderwrit|\bloan\b|\bcredit (analyst|manager|officer)|\bactuar"),
    ("operations", "Operations", r"project (coordinator|director|assistant)|(?<!technical )programme (manager|coordinator)|\bscheduler\b|general manager|office (manager|assistant)|\bexecutive assistant|\badmin\b|\bassistant manager\b"),
]
_LANGS = (r"english|german|french|spanish|portuguese|italian|dutch|japanese|korean|mandarin|chinese|cantonese|arabic|hebrew|hindi|russian|ukrainian|polish|"
          r"turkish|swedish|norwegian|danish|finnish|greek|czech|romanian|hungarian|vietnamese|thai|indonesian|malay|tagalog|bahasa")


def _spoken(lang, extra=""):
    """A spoken language the posting asks for: "fluent in German", "German (C1)", "German is a plus", "German-speaking"; never the
    bare word, which is also a nationality, a market or a place ("German law", "our German entity" are left out)."""
    L = f"(?:{lang})"
    return (rf"\b(?:fluen(?:t|cy)|proficien(?:t|cy)|bilingual|native|business[- ]level|business[- ]fluent|working proficiency|professional proficiency|"
            rf"full professional proficiency|mastery|command|speak|speaks|speaking|(?:read|write|speak)(?:s|ing)?,? (?:and )?(?:read|write|speak)(?:s|ing)?) "
            rf"(?:(?:in|of) )?(?:(?:both )?(?:{_LANGS}) ?(?:and|&|or|/) ?)?(?:the )?{L}\b(?! (?:law|market|entity|entities|subsidiar|gaap|tax|company|companies|office))"
            rf"|\b{L}(?: language)?(?: skills| fluency| proficiency| speakers?|[- ]speaking| (?:is |are )?(?:required|mandatory|essential|preferred|a must|a plus|"
            rf"a big plus|a strong plus|an advantage|a bonus|highly desirable|desirable|nice to have|beneficial))\b"
            rf"|\b{L} ?\((?:native|fluent|fluency|c1|c2|b2|business|professional|required|mandatory|written|spoken|bilingual|full professional)"
            rf"|\b{L} ?[:–-] ?(?:native|fluent|c1|c2|b2|business level)\b" + (f"|{extra}" if extra else ""))


SKILLS = [
    ("Solidity", r"solidity"), ("Rust", r"\brust\b"), ("Go", r"golang|\bgoroutines?\b|(?<!to )\bgo[,/)]|[,/(] ?go\b(?![- ](?:to|live)\b)|\b(?:python|rust|java|c\+\+|typescript|javascript|node(?:\.js)?|kotlin|scala|ruby|php|c#|elixir|swift)(?:,| and| or| &) go\b(?![- ](?:to|live|ahead|above)\b)|\bgo (?:and|or|&) (?:python|rust|java|c\+\+|typescript|javascript|node(?:\.js)?|kotlin|scala|ruby|php|c#|elixir|swift)\b|\b(?:in|using|with|know|knows|write|writing|written in) go\b(?=[.;:)]|\s+(?:and|or)\b|$)|\bgo (?:developer|engineer|programmer|programming|microservices?|services|backend|codebase|code|modules?|stdlib|runtime)\b"), ("Python", r"python"),
    ("TypeScript", r"typescript"), ("JavaScript", r"javascript"), ("React", r"(?-i:\bReact\b)(?! to\b)|\breact\.?js\b|\breact native\b"), ("Node.js", r"node\.?js"),
    ("Java", r"\bjava\b"), ("C++", r"c\+\+"), ("Kotlin", r"kotlin"), ("Swift", r"(?-i:\bSwift\b)|\bswiftui\b"), ("SQL", r"\bsql\b"),
    ("Ruby", r"\bruby\b"), ("PHP", r"\bphp\b"), ("C#", r"\bc#"), (".NET", r"(?<![\w@.-])\.net\b|\b(?:asp|vb|ado)\.net\b|\bdotnet\b"), ("Scala", r"\bscala\b"), ("Elixir", r"\belixir\b"),
    ("PostgreSQL", r"postgres"), ("Docker", r"\bdocker\b"), ("Terraform", r"terraform"), ("GCP", r"\bgcp\b|google cloud"), ("Azure", r"\bazure\b"),
    ("Machine Learning", r"machine learning"), ("LLM", r"\bllms?\b|large language model"), ("iOS", r"\bios\b"), ("Android", r"\bandroid\b"),
    ("Figma", r"\bfigma\b"), ("Salesforce", r"salesforce"),
    ("Next.js", r"next\.?js"), ("Vue", r"\bvue(\.js|js)?\b"), ("Angular", r"\bangular\b"), ("React Native", r"react native"), ("Flutter", r"\bflutter\b(?=[^.]{0,80}\b(?:dart|mobile|ios|android|apps?|widgets?|cross[- ]platform|react native)\b)|\b(?:dart|mobile|ios|android|react native|cross[- ]platform)\b[^.]{0,80}\bflutter\b|\bflutter (?:developer|engineer|framework|sdk)\b"),
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
    ("NetSuite", r"netsuite"), ("Workday", r"(?-i:\bWorkday\b)(?= (?:HCM|HRIS|Financials?|Payroll|Recruiting|Studio|Integrations?|Reporting|Adaptive|Prism|Extend|implementation|configuration|security|reports?|system|experience|certification|certified|modules?|administrat\w*|consultant|analyst))|(?:HRIS|experience with|experience in|knowledge of|proficien\w* (?:in|with)|systems? (?:such as|like|including)|e\.g\.,?|SAP|Oracle|ADP|UKG|PeopleSoft|SuccessFactors|NetSuite)\W{1,4}(?:\w+\W{1,3}){0,3}(?-i:\bWorkday\b)(?! (?:careers?|site|portal|account|application|profile|candidate)\b)"), ("Shopify", r"\bshopify\b"), ("Solana", r"\bsolana\b"), ("Ethereum", r"\bethereum\b|\bevm\b"),
    ("Zero-knowledge", r"zero[- ]knowledge|zk-?snarks?|\bzkp\b"), ("Embedded C", r"embedded c\b"), ("Computer Vision", r"computer vision"), ("NLP", r"(?-i:\bNLP\b)|natural language processing"),
    # added 15 Nov 2026. Certificates, licenses and spoken languages come first among the new skills: when a posting names more than MAX_TAGS,
    # the later ones are left out, and a required certificate or language says more than one more tool.
    # certificates and licenses
    ("Security clearance", r"\bsecurity clearance\b|\bts/sci\b|\b(?:top secret|secret|ts|dod|government|federal|active|current|nv[12]|baseline|sc|dv) clearances?\b"),
    ("Driver's license", r"\bvalid (?:\w+ )?driver['’]?s['’]? licen[cs]e\b|\bdriving licen[cs]e\b|\bclean driving record\b|\bdriver['’]?s licen[cs]e (?:and|with) (?:a )?(?:clean|good)\b|\bown (?:reliable )?(?:transportation|vehicle)\b"),
    ("CPA", r"\bcertified public accountant\b|\bcpa (?:licen[cs]e|certification|certificate|designation|qualification|credential|exam|candidate|eligible|required|preferred|a plus|strongly preferred|or equivalent)\b|\b(?:active|licensed|current|qualified|valid) cpa\b|\bcpa(?:,| or| and| /) ?(?:cma|cfa|acca|ca|cia|cisa|mba|chartered|aca)\b|\b(?:cma|cfa|acca|cia|cisa|mba),? (?:and |or |/)?cpa\b|\bcpa\b(?= \(|\)|/ca\b)|\bchartered professional accountant\b"),
    ("PMP", r"\bpmp\b|\bproject management professional\b|\bcapm\b|\bpgmp\b|\bpmi-acp\b|\bpmi\b(?= certif)"), ("CISSP", r"\bcissp\b|\bccsp\b|\bsscp\b|\b\(isc\)2\b|\bisc2\b"),
    ("CISM", r"\bcism\b|\bcrisc\b|\bcgeit\b|\bisaca\b"), ("CFA", r"\bcfa\b(?! institute)|\bchartered financial analyst\b"),
    ("GIAC", r"\bgiac\b|\bgcih\b|\bgcia\b|\bgpen\b|\bgsec\b|\bgcfa\b|\bgrem\b|\bgnfa\b|\bgwapt\b|\bsans\b(?= certifi|,| training| courses?)"),
    ("CISA", r"\bcisa\b(?= certif|,? (?:cism|cissp|crisc|cpa|cia|cgrc)\b| or (?:equivalent|similar))|\b(?:cissp|cism|crisc|cpa|cia|cgeit),? (?:and |or |/)?cisa\b|\bcertified information systems auditor\b"),
    ("Security+", r"\bsecurity\+|\bsec\+|\bcomptia security\b|\bcysa\+|\bcasp\+|\bpentest\+"),
    ("Six Sigma certification", r"\b(?:lean )?six sigma (?:green|black|yellow) belt\b|\b(?:green|black) belt certifi|\bcssbb\b|\bcssgb\b|\basq\b|\bcqe\b|\bcqa\b(?=,| certif)"),
    ("CCNA", r"\bccna\b|\bccnp\b|\bccie\b|\bcisco certifi(?:ed|cation)\b|\bjncia\b|\bjncis\b|\bjncip\b"), ("ITIL", r"\bitil\b"),
    ("APICS", r"\bapics\b|\bcpim\b|\bcscp\b|\bcltd\b|\bcpsm\b|\bcips\b|\bascm\b"),
    ("AWS Certified", r"\baws certifi(?:ed|cation|cations)\b|\baws (?:certified )?(?:solutions architect|developer|sysops administrator|devops engineer|security|machine learning|data engineer|cloud practitioner|advanced networking)(?: -| –)? (?:associate|professional|specialty)\b|\baws certs?\b|\baws-(?:saa|sap|dva|soa|dop|scs)\b"),
    ("CompTIA A+", r"\bcomptia a\+|\ba\+ certifi|\bcomptia (?:a|network)\b|\bnetwork\+|\bcomptia\b(?! security)|\bserver\+|\blinux\+"),
    ("ACCA", r"\bacca\b|\bcima (?:qualified|member|certif\w*)\b|\bacca/cima\b|\bcima/acca\b|\bicaew\b|\bchartered accountants?\b|\bca\b(?= qualified|,? acca)|\bqualified accountant\b|\bcpa australia\b"),
    ("CCSK", r"\bccsk\b|\bcloud\+|\bcomptia cloud\b|\bccsp\b"),
    ("PE license", r"\bprofessional engineer(?:ing)? licen[cs](?:e|ure)\b|\b(?:licensed |registered )professional engineer\b|\bp\.e\.(?= licen| \(|,| required| preferred)|\bpe licen[cs](?:e|ure)\b|\beit\b|\bengineer[- ]in[- ]training\b|\bfe exam\b|\bpe (?:certification|stamp|registration)\b|\bchartered engineer\b|\bceng\b"),
    ("OSCP", r"\boscp\b|\boswe\b|\bosep\b|\boscp\+\b|\boffsec\b|\bcrto\b|\bpnpt\b"),
    ("CAMS", r"\bcams\b(?= certif|,? (?:cfe|ica|cgss|cpa)\b| or (?:equivalent|similar))|\b(?:cfe|ica|cgss),? (?:and |or |/)?cams\b|\bcertified anti-money laundering specialist\b|\bcertified fraud examiner\b"),
    ("CIPP", r"\bcipp(?:/(?:e|us|c|a))?\b|\bcipm\b|\bcipt\b|\biapp\b"),
    ("Salesforce certification", r"\bsalesforce certifi(?:ed|cation|cations)\b|\bcertified salesforce\b|\bsalesforce (?:administrator|admin|platform developer|consultant|architect) certif|\bsalesforce certified\b"),
    ("CKA", r"\bcka\b|\bckad\b|\bcks\b|\bcertified kubernetes\b"),
    ("Azure certification", r"\bazure certifi(?:ed|cation|cations)\b|\baz-\d{3}\b|\bdp-\d{3}\b|\bai-\d{3}\b|\bmicrosoft certified\b|\bazure (?:administrator|solutions architect|developer|data engineer|fundamentals|security engineer) (?:associate|expert)\b|\bmcse\b|\bmcsa\b"),
    ("CEH", r"\bceh\b|\bcertified ethical hacker\b"), ("FRM", r"\bfrm\b|\bcaia\b"),
    ("SHRM certification", r"\bshrm-?(?:cp|scp)\b|\bshrm certifi|\b(?:s?phr|gphr|aphr)\b|\bcipd\b|\bcebs\b|\bccp\b(?= certif|,)"),
    ("Scrum Master certification", r"\bcertified scrum ?master\b|\bpsm ?(?:i|ii|iii|1|2|3)\b|\bprofessional scrum master\b|\bscrum master certifi(?:ed|cation)\b|\bcsm certifi|\bcspo\b|\bpspo\b|\bcertified scrum product owner\b|\bsafe (?:agilist|scrum master|spc|popm)\b"),
    ("Google Cloud certification", r"\b(?:google cloud|gcp) certifi(?:ed|cation|cations)\b|\bgoogle cloud (?:professional|associate) [a-z]+\b|\bprofessional cloud (?:architect|engineer|developer|data engineer|security engineer)\b|\bgcp certs?\b"),
    # spoken languages: only when the posting asks for the language ("fluent in German", "German (C1)"), never the bare word, which is also a nationality or a place
    ("English", _spoken(r"english")),
    ("German", _spoken(r"german", r"\bdeutschkenntnisse\b|\bflie(?:ß|ss)end(?:e|es)? deutsch\b|\bverhandlungssicher(?:e|es)? deutsch\b|\bsehr gute deutsch")),
    ("Spanish", _spoken(r"spanish", r"\bespa[nñ]ol (?:nativo|fluido|avanzado)\b|\bdominio del espa[nñ]ol\b")),
    ("Mandarin", _spoken(r"mandarin(?: chinese)?|chinese(?: \(mandarin\)| mandarin)?|putonghua", r"\bhsk ?[4-6]\b")),
    ("French", _spoken(r"french", r"\bfran[cç]ais courant\b|\bma[iî]trise du fran[cç]ais\b|\bparfaitement bilingue\b")),
    ("Japanese", _spoken(r"japanese", r"\bjlpt n[12]\b|\bbusiness japanese\b")),
    ("Portuguese", _spoken(r"portuguese|brazilian portuguese", r"\bportugu[eê]s fluente\b|\bflu[eê]ncia em portugu[eê]s\b")), ("Dutch", _spoken(r"dutch|flemish")),
    ("Arabic", _spoken(r"arabic")), ("Italian", _spoken(r"italian")), ("Korean", _spoken(r"korean", r"\btopik\b")),
    ("Polish", r"\b(?:fluen(?:t|cy)|proficien(?:t|cy)|bilingual|native|business[- ]level|speak|speaks|speaking) (?:(?:in|of) )?(?:(?:both )?english ?(?:and|&|or|/) ?)?polish\b|\bpolish(?: language)?(?: skills| fluency| speakers?|[- ]speaking| (?:is |are )?(?:a must|a plus|an advantage|mandatory|essential))\b|\bpolish ?\((?:native|fluent|c1|c2|b2)"),
    ("Swedish", _spoken(r"swedish")), ("Hebrew", _spoken(r"hebrew")), ("Thai", _spoken(r"thai")),
    # programming languages
    ("C", r"\bc ?/ ?c\+\+|\bc (?:and|or|&) c\+\+|\bc\+\+ (?:and|or|&) c\b(?![+#-])|\bc programming\b|\bprogramming in c\b(?![+#-])|\bansi c\b|\bin c\b(?= (?:and|or) (?:c\+\+|assembly|rust|python|go)\b)|\b(?:python|rust|java|assembly|go|golang|zig|fortran), c\b(?![+#\w-])|\bc, (?:python|rust|go|java|assembly|zig)\b"),
    ("R", r"\brstudio\b|\btidyverse\b|\bggplot2?\b|\b(?:python|sql|sas|stata|matlab|julia|spss),? (?:and|or|&|/) r\b(?![&'’.-]\w)|\b(?:python|sql|sas|stata|matlab) ?/ ?r\b(?![&'’.-]\w)|\br ?/ ?(?:python|sql|sas|stata)\b|\br,? (?:and|or|&) (?:python|sql|sas|stata|matlab)\b|\b(?:python|sql|sas|stata), r(?=,| (?:and|or)\b)|\br programming\b|\br (?:language|packages|shiny)\b"),
    ("PowerShell", r"\bpowershell\b"), ("Shell scripting", r"\bshell script(?:s|ing)?\b|\bunix shell\b"), ("Lua", r"\blua\b"), ("VBA", r"\bvba\b|\bvisual basic for applications\b"),
    ("Groovy", r"\bgroovy\b"), ("Haskell", r"\bhaskell\b"), ("Clojure", r"\bclojure(?:script)?\b"),
    # websites and apps
    ("REST APIs", r"\brest(?:ful)? (?:apis?|services|web services|endpoints|interfaces)\b|\brestful\b|\brest ?/ ?graphql\b|\bgraphql ?/ ?rest\b|\brest (?:and|or) graphql\b|\bgraphql (?:and|or) rest\b"),
    ("Microservices", r"\bmicro-?services?\b"), ("HTML", r"\bhtml5?\b"), ("CSS", r"\bcss3?\b(?!-[a-z])(?! (?:patient|billing|accounting|department|dept|unit)\b)|\bcss-in-js\b"), ("WebSockets", r"\bweb ?sockets?\b"), ("Protobuf", r"\bprotobufs?\b|\bprotocol buffers\b"),
    ("Redux", r"\bredux\b"), ("Tailwind CSS", r"\btailwind(?:css| css)?\b"), ("SwiftUI", r"\bswiftui\b"), ("Jetpack Compose", r"\bjetpack compose\b|\bcompose multiplatform\b"),
    ("Webpack", r"\bwebpack\b"), ("NestJS", r"\bnest\.?js\b"), ("WebGL", r"\bwebgl\b|\bwebgpu\b"),
    ("Vite", r"\bvite\b(?=,| or| and|/|\)| (?:build|config|plugin|dev))|\b(?:webpack|rollup|esbuild|turbopack),? (?:and |or |/)?vite\b"), ("UIKit", r"\buikit\b"),
    ("Hibernate", r"\bhibernate\b"), ("OpenGL", r"\bopengl\b"), ("Three.js", r"\bthree\.?js\b"), ("Storybook", r"\bstorybook\b"), ("Drupal", r"\bdrupal\b"), ("Vulkan", r"\bvulkan\b"),
    ("Kotlin Multiplatform", r"\bkotlin multiplatform\b|\bkmp\b|\bkmm\b"),
    # AI
    ("AI agents", r"\b(?:build(?:s|ing)?|develop(?:s|ing)?|design(?:s|ing)?|deploy(?:s|ing)?|orchestrat(?:e|es|ing)|ship(?:s|ping)?|creat(?:e|es|ing)|experience with|experience building|evaluat(?:e|ing)) (?:\w+ ){0,3}?(?:ai|llm|autonomous|coding) agents\b|\bagent(?:ic)? (?:frameworks?|orchestration|architectures?|tool ?use|evaluations?|harness(?:es)?)\b|\bagentic (?:workflows|systems|applications|ai systems|pipelines)\b|\bmulti-agent (?:systems|workflows|orchestration)\b|\bcrewai\b|\bautogen\b|\bmodel context protocol\b|\bmcp servers?\b"),
    ("Generative AI", r"\bgenerative ai\b|\bgen ?ai\b"),
    ("LLM evaluation", r"\bllm eval(?:uation)?s?\b|\bmodel evaluations?\b|\bevals\b|\bevaluation (?:frameworks?|harness(?:es)?|pipelines?) for (?:llms?|models?|ai)\b"),
    ("Prompt engineering", r"\bprompt engineering\b|\bprompt design\b|\bprompting techniques\b"),
    ("Vector databases", r"\bvector (?:databases?|dbs?|stores?|search|indexes|indices)\b|\bpinecone\b|\bweaviate\b|\bpgvector\b|\bqdrant\b|\bmilvus\b|\bchromadb\b|\bfaiss\b"),
    ("Reinforcement learning", r"\breinforcement learning\b|\brlhf\b|\brlaif\b"), ("Deep learning", r"\bdeep learning\b|\bdeep neural networks?\b"),
    ("MLOps", r"\bmlops\b|\bllmops\b|\bml ops\b"), ("LangGraph", r"\blanggraph\b"), ("Distributed training", r"\bdistributed training\b|\bdeepspeed\b|\bmegatron\b|\bfsdp\b"),
    ("Recommender systems", r"\brecommend(?:er|ation) (?:systems?|engines?|models?|algorithms?)\b|\brecsys\b"), ("JAX", r"\bjax\b"),
    ("OpenAI API", r"\bopenai(?:['’]s)? (?:api|apis|sdk|assistants|agents sdk|models|platform|realtime)\b|\b(?:openai|anthropic|claude|gemini|mistral)(?:,| and| or| /) ?(?:openai|anthropic|claude|gemini|mistral)(?: apis?| models?)\b|\bgpt-?(?:3\.5|4o?|4\.1|5)\b"),
    ("Fine-tuning", r"\bfine-?tun(?:e|ed|ing) (?:of )?(?:llms?|models?|large language models|language models|transformers|foundation models|open-source models|ai models)\b|\b(?:llm|model) fine-?tuning\b|\blora\b(?= ,|,| and| or| fine)|\bqlora\b|\bpeft\b"),
    ("vLLM", r"\bvllm\b|\bsglang\b|\btgi\b(?= ,|,| and| or)"), ("scikit-learn", r"\bscikit-?learn\b|\bsklearn\b"), ("MLflow", r"\bmlflow\b"),
    ("Speech AI", r"\bspeech recognition\b|\bspeech-to-text\b|\btext-to-speech\b|\bautomatic speech recognition\b|\bspeech synthesis\b"), ("TensorRT", r"\btensorrt\b"),
    ("AWS Bedrock", r"\b(?:aws|amazon) bedrock\b|\bbedrock(?:,| and| or| /) ?(?:sagemaker|vertex|openai|azure openai|anthropic)\b|\b(?:sagemaker|vertex ai|openai|azure openai|anthropic),? (?:and |or |/)?bedrock\b"),
    ("NumPy", r"\bnumpy\b"), ("Vertex AI", r"\bvertex ai\b(?! platforms before)|\bvertex\b(?= pipelines| endpoints)"), ("LlamaIndex", r"\bllama ?index\b"),
    ("Hugging Face", r"\bhugging ?face (?:transformers|hub|datasets|models?|libraries|ecosystem|tokenizers|accelerate|trl|peft|spaces|inference)\b|\b(?:pytorch|tensorflow|jax|langchain|vllm|transformers),? (?:and |or |/)?hugging ?face\b|\bhugging ?face,? (?:and |or |/)?(?:pytorch|tensorflow|jax|langchain|vllm|transformers|openai|scikit)\b|\b(?:e\.g\.,?|such as) hugging ?face\b"),
    ("SageMaker", r"\bsage ?maker\b"), ("Diffusion models", r"\bdiffusion models?\b|\bstable diffusion\b|\blatent diffusion\b"), ("XGBoost", r"\bxgboost\b|\blightgbm\b|\bcatboost\b"),
    ("ONNX", r"\bonnx\b"), ("SciPy", r"\bscipy\b"), ("Kubeflow", r"\bkubeflow\b"), ("Keras", r"\bkeras\b"),
    ("Triton", r"\btriton (?:inference server|kernels?|language)\b|\bopenai triton\b|\bnvidia triton\b|\bcuda,? (?:and|or|/) triton\b|\btriton,? (?:and|or|/) cuda\b"),
    ("OpenCV", r"\bopencv\b"),
    # data
    ("Data quality", r"\bdata quality\b|\bdata observability\b|\bgreat expectations\b|\bmonte carlo\b(?= ,|,| and| or| data)"),
    ("Data modeling", r"\bdata model(?:l)?ing\b|\bdimensional model(?:l)?ing\b|\bstar schemas?\b|\bkimball\b"), ("Data warehousing", r"\bdata warehous(?:e|es|ing)\b|\bdata lakehouses?\b"),
    ("Data governance", r"\bdata governance\b|\bdata stewardship\b|\bdata catalogs?\b|\bcollibra\b|\balation\b|\batlan\b"),
    ("A/B testing", r"\ba/b test(?:s|ing|ed)?\b|\bab testing\b|\bsplit testing\b|\bmultivariate testing\b|\bcontrolled experiments\b"),
    ("ETL", r"\betl\b|\belt (?:pipelines?|processes|tools|workflows)\b|\bextract,? transform,? (?:and )?load\b"), ("Google Sheets", r"\bgoogle sheets\b|\bgsheets\b"),
    ("SQL queries", r"\bwrit(?:e|ing) (?:complex |advanced |efficient )?sql\b|\bsql quer(?:y|ies)\b|\badvanced sql\b|\bcomplex sql\b|\bwindow functions\b|\bctes?\b(?= ,|,| and)"),
    ("Quantitative analysis", r"\bquantitative (?:analysis|research|modell?ing|methods|finance|strategies|trading)\b|\bstochastic calculus\b|\bmonte carlo simulations?\b"),
    ("Causal inference", r"\bcausal inference\b|\bcausal (?:modell?ing|analysis|methods)\b|\bdifference[- ]in[- ]differences\b"), ("Flink", r"\bflink\b"),
    ("Time series", r"\btime[- ]series\b"), ("Pivot tables", r"\bpivot ?tables?\b|\bv-?lookups?\b|\bxlookups?\b|\bindex[/ -]match\b"),
    ("Trino", r"\btrino\b|\bpresto(?:db)?\b|\bstarburst\b"),
    ("Iceberg", r"\bapache iceberg\b|\biceberg (?:tables?|format|catalogs?)\b|\b(?:delta lake|delta|hudi|parquet),? (?:and |or |/)?iceberg\b|\biceberg,? (?:and |or |/)?(?:delta|hudi|parquet)\b"),
    ("Delta Lake", r"\bdelta lake\b|\bdelta tables?\b|\bdelta live tables\b"), ("Pub/Sub", r"\bpub ?/ ?sub\b|\bpubsub\b"),
    ("Amplitude", r"\bamplitude\b(?! (?:of|and phase|modulation|signals?))"), ("Hex", r"\bhex\b(?= notebooks?|,| and| or| /|\))(?! (?:key|keys|codes?|values?|string))|\bhex\.tech\b"),
    ("Kinesis", r"\bkinesis\b"), ("Dagster", r"\bdagster\b"), ("Fivetran", r"\bfivetran\b"), ("Hightouch", r"\bhightouch\b|\bcensus\b(?=,| and| or|/)(?<! the census)|\breverse etl\b"),
    ("Pendo", r"\bpendo\b|\bfullstory\b|\bhotjar\b|\bsession replays?\b|\bheatmaps?\b"), ("Mixpanel", r"\bmixpanel\b"), ("Metabase", r"\bmetabase\b"),
    ("Sigma Computing", r"(?<!\bat )\bsigma computing\b|\bsigma (?:bi|dashboards?|workbooks?)\b|\b(?:looker|tableau|mode|hex),? (?:and |or |/)?sigma\b|\bsigma,? (?:and |or |/)?(?:looker|tableau|mode|hex)\b"),
    ("Prefect", r"\bprefect\b"),
    ("Ray", r"\bray (?:serve|tune|train|data|cluster|core|rllib)\b|\banyscale\b|\b(?:spark|dask|kubernetes),? (?:and|or|/) ray\b|\bray,? (?:and|or|/) (?:spark|dask|kubernetes)\b"),
    ("Jupyter", r"\bjupyter(?:lab| notebooks?)?\b|\bipython\b"), ("Parquet", r"\bparquet\b(?! floor)"), ("Matplotlib", r"\bmatplotlib\b|\bplotly\b"),
    ("Hive", r"\bapache hive\b|\bhiveql\b|\bhive metastore\b|\b(?:hadoop|spark|presto|hdfs|impala|pig),? (?:and |or |/)?hive\b|\bhive,? (?:and |or |/)?(?:hadoop|spark|presto|hdfs|impala|pig)\b"),
    ("Mode", r"\bmode analytics\b|\b(?:looker|tableau|metabase|periscope|hex),? (?:and |or |/)?mode\b(?! (?:of|for|to)\b)|\bmode,? (?:and |or |/)?(?:looker|tableau|metabase|periscope|hex)\b"),
    ("Informatica", r"\binformatica\b"), ("Power Query", r"\bpower ?query\b"), ("Apache Beam", r"\bapache beam\b|\bbeam pipelines?\b|\bgoogle (?:cloud )?dataflow\b|\bcloud dataflow\b"),
    ("Superset", r"\bapache superset\b|\bsuperset(?:,| and| or| /) ?(?:metabase|tableau|looker|grafana|redash)\b|\b(?:metabase|tableau|looker|grafana|redash),? (?:and |or |/)?superset\b"),
    ("Qlik", r"\bqlik(?: ?sense| ?view)?\b"),
    # databases
    ("NoSQL", r"\bnosql\b"), ("Database administration", r"\bdatabase administration\b|\bdba\b(?! (?:name|as)\b)|\bdatabase tuning\b|\bquery optimi[sz]ation\b"),
    ("SQL Server", r"\bsql server\b|\bmssql\b|\bms sql\b|\bt-?sql\b"), ("Cassandra", r"\bcassandra\b"),
    ("Oracle Database", r"\boracle (?:database|db|dbs|sql|rac|exadata|11g|12c|19c)\b|\bpl/?sql\b|\boracle(?:,| and| or| /) ?(?:sql server|mysql|postgres(?:ql)?|db2|teradata)\b|\b(?:sql server|mysql|postgres(?:ql)?|db2|teradata|mssql),? (?:and |or |/)?oracle\b"),
    ("Graph databases", r"\bgraph databases?\b|\bgraph dbs?\b|\bneptune\b(?=,| and| or|/)"), ("Firebase", r"\bfirebase\b|\bfirestore\b"),
    ("TimescaleDB", r"\btimescale(?:db)?\b|\binfluxdb\b|\btime[- ]series databases?\b|\bquestdb\b"), ("CockroachDB", r"\bcockroach ?db\b"),
    ("Druid", r"\bapache druid\b|\bdruid\b(?=,| and| or|/)|\bapache pinot\b|\bpinot\b(?=,| and| or|/)"), ("Memcached", r"\bmemcached?\b"),
    ("Aurora", r"\b(?:amazon|aws|rds) aurora\b|\baurora (?:postgres(?:ql)?|mysql|serverless|db)\b"), ("Neo4j", r"\bneo4j\b|\bcypher queries\b"), ("Teradata", r"\bteradata\b"),
    ("Bigtable", r"\bbigtable\b"),
    # cloud and operations
    ("Infrastructure as code", r"\binfrastructure[- ]as[- ]code\b|\biac\b"),
    ("Observability", r"\bobservability (?:tools|tooling|stack|platforms?|practices|pipelines?|systems|solutions)\b|\b(?:monitoring|logging|metrics|alerting),? (?:and |& )?observability\b|\bobservability,? (?:and|&) (?:monitoring|alerting|logging)\b|\b(?:experience|expertise) (?:with|in) observability\b"),
    ("Git", r"\bgit\b(?![-.]?(?:hub|lab|ops))"), ("Serverless", r"\bserverless\b"), ("Load balancing", r"\bload[- ]balanc(?:ers?|ing)\b|\bf5 big-?ip\b|\bf5\b(?= ,|,| and| or| load)"),
    ("EKS", r"\beks\b"), ("GitOps", r"\bgitops\b|\bflux ?cd\b"), ("Istio", r"\bistio\b|\blinkerd\b|\bservice mesh(?:es)?\b|\benvoy proxy\b|\benvoy\b(?=,| and| or|/)"),
    ("S3", r"\b(?:aws |amazon )?s3\b(?= buckets?|,| and| or|\)| /|/| storage| api)"),
    ("Message queues", r"\bmessage (?:queues?|brokers?|queuing|queueing|bus)\b|\bevent[- ]driven architecture\b|\bevent streaming\b"), ("GitLab", r"\bgitlab\b"),
    ("CDN", r"\bcdns?\b(?!\.\w)|\bcontent delivery networks?\b|\bfastly\b|\bakamai\b|\bcloudfront\b"), ("Argo CD", r"\bargo ?cd\b|\bargo (?:workflows|rollouts|events)\b|\bargoproj\b"),
    ("ELK stack", r"\belk(?: stack)?\b|\bkibana\b|\blogstash\b|\bfluentd\b|\bfluent ?bit\b"), ("Gradle", r"\bgradle\b"),
    ("Feature flags", r"\bfeature flags?\b|\bfeature toggles?\b|\blaunchdarkly\b|\bstatsig\b|\bgrowthbook\b|\boptimizely\b"), ("Bazel", r"\bbazel\b|\bbuck2\b|\bpants build\b"),
    ("Helm", r"\bhelm charts?\b|\bhelm(?:,| and| or| /) ?(?:kubernetes|k8s|argo ?cd|terraform|kustomize|docker)\b|\b(?:kubernetes|k8s|argo ?cd|terraform|kustomize|docker),? (?:and |or |/)?helm\b"),
    ("Puppet", r"\bpuppet\b"), ("CloudFormation", r"\bcloud ?formation\b"), ("Pulumi", r"\bpulumi\b"), ("API gateways", r"\bapi gateways?\b|\bkong (?:gateway|konnect|mesh)\b|\bapigee\b"),
    ("RabbitMQ", r"\brabbitmq\b|\bactivemq\b|\bamqp\b"), ("SQS", r"\bsqs\b|\bsns\b(?=,| and| or|/|\))"), ("EC2", r"\bec2\b"),
    ("AWS Lambda", r"\baws lambda\b|\blambda functions?\b|\blambda(?:,| and| /) ?(?:dynamodb|s3|api gateway|sqs|sns|step functions|ecs|ec2)\b|\b(?:s3|ec2|dynamodb|sqs|sns|ecs|api gateway|step functions)(?:,| and| /) ?lambda\b"),
    ("ECS", r"\becs\b(?=,| and| or|/|\)| fargate| clusters?| services?| tasks?)|\bfargate\b"), ("Jaeger", r"\bjaeger\b|\bzipkin\b|\bdistributed tracing\b"), ("Buildkite", r"\bbuildkite\b"),
    ("GKE", r"\bgke\b|\bgoogle kubernetes engine\b"), ("CircleCI", r"\bcircle ?ci\b"), ("Loki", r"\bloki\b|\bmimir\b"),
    ("Maven", r"\bmaven\b(?=,| or| and| /|/|\)| build| central| repositor)|\b(?:gradle|ant|sbt|npm),? (?:and |or |/)?maven\b"), ("Nginx", r"\bnginx\b|\bhaproxy\b"),
    ("CloudWatch", r"\bcloudwatch\b"), ("OpenShift", r"\bopenshift\b|\brancher\b"),
    ("Cloudflare", r"\bcloudflare (?:workers|waf|dns|cdn|tunnels?|zero trust|access|r2|pages|warp|gateway)\b|\bcloudflare(?:,| or| and| /) ?(?:akamai|fastly|cloudfront|aws|gcp|azure|vercel|netlify)\b|\b(?:akamai|fastly|cloudfront|aws|gcp|azure|vercel|netlify),? (?:and |or |/)?cloudflare\b|\b(?:experience|familiarity) (?:with|using) (?:\w+ ){0,3}?cloudflare\b"),
    ("Chef", r"\b(?:puppet|saltstack|salt|ansible),? (?:and |or |/)?chef\b|\bchef(?:,| and| or| /) ?(?:ansible|puppet|salt(?:stack)?|terraform)\b|\bchef (?:cookbooks?|infra|recipes|inspec)\b"),
    ("AKS", r"\baks\b|\bazure kubernetes service\b"), ("Sentry", r"\bsentry\b"), ("PagerDuty", r"\bpagerduty\b|\bopsgenie\b"), ("New Relic", r"\bnew ?relic\b"),
    ("Azure DevOps", r"\bazure devops\b|\bazure pipelines\b|\bvsts\b|\btfs\b"),
    ("AWS CDK", r"\baws cdk\b|\bcdk(?:,| and| or| /) ?(?:terraform|cloudformation|pulumi)\b|\b(?:terraform|cloudformation|pulumi),? (?:and |or |/)?cdk\b|\bcdktf\b"),
    ("Bitbucket", r"\bbitbucket\b"), ("SaltStack", r"\bsalt ?stack\b|\b(?:puppet|chef|ansible),? (?:and |or |/)?salt\b|\bsalt(?:,| and| or| /) ?(?:ansible|puppet|chef)\b"),
    ("Honeycomb", r"(?<!of )\bhoneycomb(?:\.io)?\b(?! (?:structure|panel|core)|,? (?:and )?foam)"),
    # IT and networks
    ("Network engineering", r"\bnetwork(?:ing)? (?:engineering|protocols|infrastructure|administration|architecture|design|troubleshooting)\b|\blan/wan\b|\bwan/lan\b|\bvlans?\b"),
    ("DNS", r"\bdns\b"),
    ("Data centers", r"\bdata cent(?:er|re) (?:operations|infrastructure|hardware|design|facilities|environments?)\b|\brack(?:ing)? and stack(?:ing)?\b|\bstructured cabling\b"),
    ("Google Workspace", r"\bg ?suite\b|\bgoogle workspace\b"), ("TCP/IP", r"\btcp/?ip\b|\btcp/udp\b|\bosi model\b"),
    ("Windows", r"\bwindows (?:10|11|os|desktop|environments?|administration|endpoints?|devices?|pcs?)\b|\bmicrosoft windows\b|\bwindows(?:,| and| or| /) ?(?:mac ?os|linux|unix|mac)\b|\b(?:mac ?os|linux|unix|mac),? (?:and |or |/)?windows\b"),
    ("macOS", r"\bmac ?os(?: x)?\b|\bos x\b"), ("VPN", r"\bvpns?\b|\bipsec\b|\bwireguard\b"),
    ("Help desk", r"\bhelp ?desk\b|\bservice desk\b|\bdesktop support\b|\btier [12] support\b|\bl[12] support\b"), ("ServiceNow", r"\bservicenow\b(?! ventures)|\bservice now\b"),
    ("Active Directory", r"\bactive directory\b|\bentra id\b|\bazure ad\b|\bazure active directory\b|\bldap\b"), ("Unix", r"\bunix\b"), ("BGP", r"\bbgp\b|\bospf\b|\bmpls (?:networks?|vpns?|circuits?|routing|backbone|l[23] ?vpn|te)\b"),
    ("SD-WAN", r"\bsd-?wan\b|\bsase\b"), ("Microsoft 365", r"\b(?:microsoft|office|ms|o) ?365\b|\bm365\b|\bexchange online\b"),
    ("Linux administration", r"\blinux (?:administration|system administration|sysadmin|admin|servers?)\b|\bred hat\b|\brhel\b|\bcentos\b|\bubuntu\b|\bdebian\b"),
    ("Cisco", r"\bcisco (?:ios|nx-os|asa|meraki|routers?|switches|catalyst|nexus|ise|networking|certifi\w*|equipment|webex|cimc|ucs)\b|\bmeraki\b|\bcisco,? (?:and |or |/)?(?:juniper|arista|palo alto|fortinet)\b|\b(?:juniper|arista|palo alto|fortinet),? (?:and |or |/)?cisco\b"),
    ("Jamf", r"\bjamf\b|\bkandji\b"), ("Intune", r"\bintune\b|\bsccm\b|\bmecm\b|\bendpoint manager\b"), ("VMware", r"\bvmware\b|\bvsphere\b|\besxi\b|\bvcenter\b"),
    ("ITSM", r"\bitsm\b|\bit service management\b"),
    ("Juniper", r"\bjuniper (?:networks|routers?|switches|srx|mx|junos)\b|\bjunos\b|\b(?:cisco|arista|palo alto),? (?:and |or |/)?juniper\b|\bjuniper,? (?:and |or |/)?(?:cisco|arista|palo alto)\b"),
    ("Windows Server", r"\bwindows server\b|\bhyper-?v\b"),
    ("Mobile device management", r"\bmobile device management\b|\bmdm (?:solutions?|platforms?|tools?|software|policies)\b|\b(?:intune|jamf|kandji|workspace one),? (?:and |or |/)?mdm\b"),
    ("Arista", r"\barista\b(?! (?:coffee|barista))"),
    ("Wi-Fi", r"\bwi-?fi (?:networks?|design|surveys?|infrastructure|standards|6e?|7)\b|\bwireless (?:networking|networks|lan)\b|\bwlan\b|\b802\.11"),
    # security
    ("Incident response", r"\bincident response\b|\bdfir\b|\bincident handling\b"),
    ("IAM", r"\biam\b|\bidentity and access management\b|\bidentity governance\b|\bprivileged access\b|\bpam\b(?= solutions?|,| and| or|/| tools?)|\bcyberark\b|\bsailpoint\b"),
    ("Application security", r"\bappsec\b|\bapplication security\b|\bproduct security\b|\bsecure code review\b|\bsecure coding\b|\bsecure sdlc\b"),
    ("Cloud security", r"\bcloud security\b|\bcspm\b|\bcnapp\b|\bcwpp\b"), ("SOC 2", r"\bsoc ?2\b|\bsoc ii\b|\bsoc 1\b"), ("SSO", r"\bsso\b|\bsingle sign-?on\b|\bsaml\b|\bscim\b"),
    ("Zero trust", r"\bzero[- ]trust\b"), ("OAuth", r"\boauth ?2?(?:\.0)?\b|\bopenid connect\b|\boidc\b"), ("ISO 27001", r"\biso[/ ]?(?:iec )?27001\b|\biso 27k\b|\biso/iec 27\d\d\d\b"),
    ("Vulnerability management", r"\bvulnerability (?:management|assessments?|scanning|remediation)\b|\bnessus\b|\btenable\b|\bqualys\b|\brapid7\b"),
    ("Threat intelligence", r"\bthreat intel(?:ligence)?\b|\bthreat hunting\b|\bcti\b(?=,| and| or|/| team| analyst)"), ("SIEM", r"\bsiem\b|\bsecurity information and event management\b"),
    ("Threat modeling", r"\bthreat model(?:l)?ing\b|\bthreat models?\b"), ("NIST", r"\bnist\b"), ("Firewalls", r"\bfirewalls?\b"),
    ("FedRAMP", r"\bfedramp\b|\bcmmc\b|\bstateramp\b|\bil[245]\b(?= authori|,| and)"),
    ("EDR", r"\bedr\b|\bxdr\b|\bendpoint detection\b|\bendpoint security\b|\bendpoint protection\b|\bmicrosoft defender\b|\bdefender for (?:endpoint|cloud|office)\b|\bsentinel ?one\b"),
    ("SAST/DAST", r"\bsast\b|\bdast\b|\bsca\b(?= tools?|,| and|/)|\bstatic (?:application security|code analysis)\b|\bsnyk\b|\bsemgrep\b|\bsonarqube\b|\bcheckmarx\b|\bveracode\b"),
    ("Penetration testing", r"\bpen(?:etration)?[- ]?test(?:s|ing|ers?)?\b|\bpentest(?:s|ing|ers?)?\b|\bred team(?:ing)?\b|\bethical hacking\b"), ("Okta", r"\bokta\b"),
    ("Cryptography", r"\bcryptograph(?:y|ic|ers?)\b|\bapplied crypto\b"), ("Splunk", r"\bsplunk\b"),
    ("PCI DSS", r"\bpci[- ]?dss\b|\bpci (?:compliance|compliant|standards?|requirements|scope|audits?|level 1)\b"), ("PKI", r"\bpki\b|\bpublic key infrastructure\b|\bx\.509\b|\bhsms?\b"),
    ("OWASP", r"\bowasp\b"), ("DLP", r"\bdlp\b|\bdata loss prevention\b"),
    ("Palo Alto Networks", r"\bpalo alto networks\b|\bpan-?os\b|\bpalo alto (?:firewalls?|ngfw|panorama|prisma)\b|\bprisma (?:cloud|access|sase)\b|\b(?:fortinet|fortigate|checkpoint|check point|cisco asa),? (?:and |or |/)?palo alto\b|\bpalo alto,? (?:and |or |/)?(?:fortinet|fortigate|checkpoint|check point|cisco)\b"),
    ("MITRE ATT&CK", r"\bmitre att&ck\b|\bmitre attack\b|\batt&ck\b|\bmitre\b(?= framework)"), ("CrowdStrike", r"\bcrowdstrike\b|\bfalcon (?:edr|insight|complete)\b"),
    ("SOAR", r"\bsoar (?:platforms?|playbooks?|tools?|solutions?)\b|\bsiem(?:,| and| or| /) ?soar\b|\bsoar(?:,| and| or| /) ?(?:siem|edr|xdr)\b"),
    ("Digital forensics", r"\bdigital forensics\b|\bcomputer forensics\b|\bforensic (?:analysis|investigations?) of (?:systems|devices|computers)\b|\bencase\b|\bcellebrite\b"),
    ("Wiz", r"\bwiz\b(?=,| and| or|/|\))(?<!\bexcel wiz)|\bwiz\.io\b"), ("Metasploit", r"\bmetasploit\b|\bnmap\b|\bwireshark\b|\bkali(?: linux)?\b"),
    ("Malware analysis", r"\bmalware analysis\b|\breverse engineering (?:of )?malware\b|\bmalware reverse\b|\bghidra\b|\bida pro\b"), ("Burp Suite", r"\bburp(?: suite)?\b"),
    ("HashiCorp Vault", r"\bhashicorp vault\b|\bvault(?:,| and| or| /) ?(?:consul|terraform|nomad|kubernetes|packer)\b|\b(?:consul|terraform|nomad|packer|hashicorp),? (?:and |or |/)?vault\b"),
    # testing
    ("Test planning", r"\bmanual (?:testing|tests|qa)\b|\bexploratory testing\b|\bregression testing\b|\btest cases?\b|\btest plans?\b"),
    ("Load testing", r"\b(?:load|performance|stress|soak) test(?:s|ing)\b|\bk6\b|\bjmeter\b|\bgatling\b|\bloadrunner\b|\blocust\b(?=,| and| or|/|\))"),
    ("Postman", r"\bpostman\b|\binsomnia\b(?=,| and| or|/)|\bsoapui\b"), ("TDD", r"\btdd\b|\btest[- ]driven development\b|\btest[- ]driven\b"), ("pytest", r"\bpytest\b|\bunittest\b"),
    ("Jest", r"\bjest\b"), ("JUnit", r"\bjunit\b|\btestng\b|\bmockito\b"),
    # design
    ("Design systems", r"\bdesign systems?\b|\bcomponent librar(?:y|ies)\b|\bdesign tokens?\b"),
    ("User research", r"\buser research\b|\bux research\b|\buser interviews?\b|\bcustomer interviews?\b|\bethnographic\b|\bdiary studies\b"),
    ("Visual design", r"\bvisual design\b|\bgraphic design\b|\blayout and composition\b"),
    ("Brand design", r"\bbrand (?:identity|guidelines|design|systems?)\b|\bvisual identity\b|\blogo design\b"),
    ("Interaction design", r"\binteraction design\b|\bixd\b|\bmicro-?interactions?\b"), ("Typography", r"\btypography\b|\btypesetting\b"),
    ("Adobe Creative Cloud", r"\badobe (?:creative )?(?:suite|cloud)\b|\bcreative (?:suite|cloud)\b|\badobe cc\b"),
    ("Usability testing", r"\busability (?:test(?:s|ing)?|studies|research)\b|\buser testing\b|\busertesting\b"),
    ("Video editing", r"\bvideo editing\b|\bedit(?:ing)? video\b|\bvideo production\b|\bpost-production\b"), ("Motion design", r"\bmotion (?:design|graphics)\b|\banimation principles\b"),
    ("Information architecture", r"\binformation architecture\b|\bcard sorting\b|\btree testing\b"), ("Wireframing", r"\bwirefram(?:e|es|ing)\b"), ("Photoshop", r"\bphotoshop\b"),
    ("WCAG", r"\bwcag\b|\bweb accessibility\b|\baccessibility standards\b|\bsection 508\b|\ba11y\b|\baria\b(?= attributes| roles| labels)"),
    ("Design thinking", r"\bdesign thinking\b|\bhuman[- ]centered design\b|\bhuman[- ]centred design\b"),
    ("3D modeling", r"\b3d model(?:l)?(?:ing|ers?)\b|\b3d art\b|\b3d assets\b|\bhard[- ]surface model"), ("After Effects", r"\bafter effects\b"),
    ("Illustration", r"\billustrations?\b(?! (?:of|purposes))|\bdigital painting\b|\bprocreate\b"),
    ("Illustrator", r"\badobe illustrator\b|\billustrator(?:,| and| or| /) ?(?:photoshop|indesign|after effects|figma|premiere|sketch|xd)\b|\b(?:photoshop|indesign|after effects|figma|premiere(?: pro)?|sketch|xd),? (?:and |or |/|&)?illustrator\b"),
    ("Photography", r"\bphotography\b|\bphoto shoots?\b|\bphoto editing\b|\blightroom\b"),
    ("Premiere Pro", r"\bpremiere pro\b|\badobe premiere\b|\bpremiere(?:,| and| or| /) ?(?:after effects|final cut|davinci)\b|\b(?:after effects|final cut(?: pro)?|davinci(?: resolve)?|photoshop),? (?:and |or |/)?premiere\b"),
    ("Blender", r"\bblender\b(?! (?:bottles?|cups?))"),
    ("Canva", r"\bcanva(?:,| or| and| /) ?(?:figma|adobe|photoshop|illustrator|capcut|premiere|indesign|google slides|powerpoint|miro)\b|\b(?:figma|adobe|photoshop|illustrator|capcut|premiere|indesign|google slides|powerpoint|miro)(?: \w+)?,? (?:and |or |/)?canva\b|\b(?:experience|proficien\w+|skills?|familiarity) (?:with|in|using) (?:\w+ ){0,3}?canva\b|\bcanva (?:pro|designs?|templates?)\b"),
    ("InDesign", r"\bindesign\b"),
    ("Maya", r"\bautodesk maya\b|\bmaya(?:,| and| or| /) ?(?:blender|houdini|3ds max|zbrush|unreal|unity|cinema 4d|substance|nuke|motionbuilder)\b|\b(?:blender|houdini|3ds max|zbrush|cinema 4d|substance painter|nuke),? (?:and |or |/)?maya\b"),
    ("Lottie", r"\blottie\b|\brive\b(?=,| and| or|/)"),
    # project management and office tools
    ("Slack", r"\b(?:jira|confluence|notion|zoom|microsoft teams|teams|asana|trello|google workspace|g ?suite|github|gitlab|linear|loom|figma|discord|email|e-mail|gmail|clickup|monday\.com|airtable|hubspot|outlook|salesforce|dropbox|excel|zendesk|intercom|sharepoint|office 365|microsoft office|google docs)\s?(?:,|/|and|or|&)\s?(?:[a-z.]+\s?(?:,|/|and|or|&)\s?)?slack\b|\bslack\s?(?:,|/|and|or|&)\s?(?:jira|confluence|notion|zoom|microsoft teams|teams|asana|trello|google|github|gitlab|linear|loom|figma|discord|email|e-mail|clickup|airtable|hubspot|outlook|salesforce|dropbox|excel|zendesk|intercom|sharepoint|office|monday)\b|\bslack (?:channels?|workspaces?|apps?|bots?|integrations?|api|messages?|communities|community)\b|\b(?:via|over|using|on|through|in) slack\b(?! (?:time|off|season|period|tide)\b)"), ("PRDs", r"\bprds?\b|\bproduct requirements? documents?\b|\buser stories\b|\bacceptance criteria\b"),
    ("PowerPoint", r"\bpowerpoint\b|\bkeynote\b(?=,| and| or|/)|\bgoogle slides\b"),
    ("Microsoft Word", r"\b(?:microsoft|ms) word\b|\bword(?:,| and| /) ?(?:excel|powerpoint|outlook)\b|\b(?:excel|powerpoint|outlook),? (?:and |/)?word\b|\bgoogle docs\b"),
    ("Confluence", r"\bconfluence\b"), ("Low-code tools", r"\blow-code\b|\bno-code\b|\bretool\b|\bbubble\.io\b|\bappsmith\b"),
    ("Outlook", r"\b(?:microsoft|ms) outlook\b|\boutlook(?:,| and| or| /) ?(?:word|excel|powerpoint|teams)\b|\b(?:word|excel|powerpoint|teams),? (?:and |or |/)?outlook\b"),
    ("Technical writing", r"\btechnical writing\b|\bapi documentation\b|\bdocs-as-code\b|\bdocumentation sites?\b|\bmadcap flare\b|\bdita\b"), ("OKRs", r"\bokrs?\b"),
    ("Scrum", r"\bscrum\b"), ("Asana", r"(?<![./])\basana\b(?!\.com)"), ("Smartsheet", r"\bsmartsheets?\b"),
    ("Notion", r"\bnotion(?:,| and| or| /) ?(?:jira|confluence|asana|linear|slack|google|airtable|coda|clickup|figma|miro|loom)\b|\b(?:jira|confluence|asana|linear|slack|google docs|airtable|coda|clickup|figma|miro|loom|gsuite),? (?:and |or |/|&)?notion\b|\bnotion (?:docs|databases?|workspace|ai|pages?)\b"),
    ("Zapier", r"\bzapier\b|\bmake\.com\b|\btray\.io\b"), ("MS Project", r"\b(?:microsoft|ms) project\b|\bprimavera\b|\bp6\b(?= ,|,| scheduling| and)"),
    ("SharePoint", r"\bsharepoint\b(?!\.\w)|\bonedrive\b"), ("Visio", r"\bvisio\b|\blucid ?chart\b|\bdraw\.io\b"), ("Airtable", r"\bairtable\b"),
    ("Miro", r"\bmiro\b|\bfigjam\b|\bmural\b(?=,| and| or|/)"), ("Kanban", r"\bkanban\b"), ("Monday.com", r"\bmonday\.com\b|\bmonday (?:work os|crm)\b"), ("PRINCE2", r"\bprince ?2\b"),
    ("Power Automate", r"\bpower automate\b|\bmicrosoft flow\b|\bpower platform\b"), ("Microsoft Teams", r"(?<!via )(?<!on )(?<!over )(?<!through )\b(?:microsoft|ms) teams\b"),
    ("Linear", r"\b(?:jira|asana),? (?:or |and |/)?linear\b(?! (?:algebra|regression|models?|programming|systems?|actuators?|motors?|equations?|time|scale))|\blinear(?:,| or| and| /) ?(?:jira|asana)\b|\blinear\.app\b|\blinear (?:tickets|issues)\b"),
    # sales
    ("Pipeline management", r"\bpipeline management\b|\bmanag(?:e|ing) (?:a |your |the )?(?:sales )?pipeline\b|\bsales forecasting\b|\bforecast accuracy\b"),
    ("Solution selling", r"\bsolution selling\b|\bvalue[- ]based selling\b|\bvalue selling\b|\bconsultative sell(?:ing|er)\b|\bconsultative sales\b"),
    ("MEDDIC", r"\bmeddic\b|\bmeddicc\b|\bmeddpicc\b|\bmeddpic\b"),
    ("Contract negotiation", r"\bcontract negotiations?\b|\bnegotiat(?:e|ing) contracts\b|\bdeal negotiations?\b|\bcommercial negotiations?\b"),
    ("Sales methodologies", r"\bspin selling\b|\bsandler\b|\bcommand of the message\b|\bmiller heiman\b|\bvalue selling framework\b|\bforce management\b"), ("Gong", r"\bgong(?:\.io)?\b"),
    ("ZoomInfo", r"\bzoom ?info\b"),
    ("Salesforce administration", r"\bsalesforce (?:admin|administration|administrator|development|developer|flows?|apex|lightning|reports? and dashboards|cpq|service cloud|sales cloud|experience cloud|health cloud|marketing cloud|data cloud|einstein)\b|\bapex\b(?= ,|,| triggers?| classes| code| and)|\blwc\b|\blightning web components\b|\bsoql\b|\bsales cloud\b"),
    ("Sales Navigator", r"\bsales navigator\b"),
    ("Outreach", r"\boutreach\.io\b|\boutreach(?:,| and| or| /) ?(?:salesloft|gong|apollo|zoominfo|salesforce|hubspot|linkedin sales navigator|sales navigator|clari|seamless)\b|\b(?:salesloft|gong|apollo(?:\.io)?|zoominfo|sales navigator|clari),? (?:and |or |/)?outreach\b(?! (?:to|efforts?|campaigns?|activities|and|strategies|programs?|initiatives)\b)"),
    ("CPQ", r"\bcpq\b|\bconfigure,? price,? quote\b"), ("Clari", r"\bclari\b"), ("6sense", r"\b6sense\b|\bdemandbase\b|\bbombora\b|\bintent data\b"), ("Salesloft", r"\bsalesloft\b"),
    ("Challenger Sale", r"\bchallenger (?:sale|selling|methodology|model|sales)\b"),
    ("Clay", r"\bclay(?:\.com)?(?:,| and| or| /) ?(?:apollo|zoominfo|outreach|hubspot|salesforce|n8n|zapier)\b|\b(?:apollo|zoominfo|outreach|hubspot|salesforce|n8n|zapier),? (?:and |or |/)?clay\b|\bclay\.com\b|\bclay tables?\b"),
    ("Highspot", r"\bhighspot\b|\bseismic(?:,| and| or| /) ?(?:highspot|showpad|gong|salesforce)\b|\bshowpad\b"),
    ("Apollo.io", r"\bapollo\.io\b|\bapollo(?:,| and| or| /) ?(?:zoominfo|outreach|salesloft|clay|sales navigator|lusha|seamless)\b|\b(?:zoominfo|outreach|salesloft|clay|sales navigator|lusha|seamless(?:\.ai)?),? (?:and |or |/)?apollo\b"),
    ("DocuSign", r"\b(?:docusign|pandadoc|adobe sign)(?:,| and| or| /) ?(?:salesforce|ironclad|pandadoc|docusign|hubspot|cpq|gong)\b|\b(?:salesforce|ironclad|pandadoc|hubspot|cpq|gong|clm),? (?:and |or |/)?(?:docusign|pandadoc)\b|\bdocusign (?:clm|cpq|admin|integration)\b|\bpandadoc\b"),
    # marketing
    ("Performance marketing", r"\bperformance marketing\b|\bgrowth marketing\b|\buser acquisition\b|\bpaid acquisition\b|\bpaid media\b|\bpaid channels?\b"),
    ("Event marketing", r"\bevent marketing\b|\btrade shows?\b|\bfield marketing\b|\bconferences and events\b|\bexperiential marketing\b"),
    ("Product marketing", r"\bproduct marketing (?:experience|background|skills|expertise)\b|\b(?:experience|background|years) in (?:b2b |saas |technical )?product marketing\b|\bpositioning (?:and|&) messaging\b|\bmessaging (?:and|&) positioning\b|\bproduct positioning\b|\bcompetitive intelligence\b"),
    ("Marketing automation", r"\bmarketing automation\b"), ("Content marketing", r"\bcontent (?:marketing|strategy|calendar)\b|\beditorial calendar\b"),
    ("Account-based marketing", r"\baccount[- ]based (?:marketing|experience)\b|\babm\b"),
    ("Marketing attribution", r"\b(?:multi-touch )?attribution model(?:l)?(?:ing|s)?\b|\bmarketing mix model(?:l)?ing\b|\bmarketing attribution\b|\bincrementality\b|\bmmm\b"),
    ("Marketo", r"\bmarketo\b"), ("Influencer marketing", r"\binfluencer (?:marketing|partnerships|campaigns|relations|programs?)\b|\bcreator (?:partnerships|marketing|programs?)\b"),
    ("Lifecycle marketing", r"\blifecycle marketing\b|\bcrm marketing\b|\bretention marketing\b"),
    ("Copywriting", r"\bcopywriting\b|\bcopy ?editing\b|\bwriting copy\b|\bad copy\b|\bux writing\b|\bux copy\b|\bmicrocopy\b"),
    ("CMS", r"\bcontent management systems?\b|\b(?:hubspot|wordpress|headless|drupal|webflow) cms\b|\bcms (?:platforms?|tools?|experience)\b"),
    ("Google Analytics", r"\bgoogle analytics\b|\bga4\b|\buniversal analytics\b"),
    ("Email marketing", r"\bemail (?:marketing|campaigns?|automation|nurture)\b|\bnurture (?:campaigns?|streams|programs)\b|\bdrip campaigns?\b"),
    ("Paid social", r"\bpaid social\b|\bsocial ads\b|\bsocial media advertising\b"),
    ("Social media marketing", r"\bsocial media (?:marketing|management|strategy|campaigns?|content)\b|\borganic social\b"),
    ("Contentful", r"\bcontentful\b|\bsanity\.io\b|\bstrapi\b|\bheadless cms\b|\bstoryblok\b"), ("PPC", r"\bppc\b|\bpay[- ]per[- ]click\b|\bpaid search\b|\bsearch engine marketing\b"),
    ("Braze", r"\bbraze\b"), ("Google Ads", r"\bgoogle ads\b|\badwords\b|\bgoogle ad manager\b|\bsearch ads 360\b"),
    ("AppsFlyer", r"\bappsflyer\b|\bkochava\b|\bbranch\.io\b|\bsingular\b(?= ,|,| and| or|/)|\b(?:appsflyer|kochava|branch|singular),? (?:and |or |/)?adjust\b|\bmobile measurement partners?\b|\bmmps?\b"),
    ("Iterable", r"\biterable\b(?! (?:objects?|protocol))"),
    ("Affiliate marketing", r"\baffiliate (?:marketing|programs?|networks?|partnerships|channels?)\b|\bimpact\.com\b|\bpartnerize\b|\bcj affiliate\b|\brakuten advertising\b"),
    ("Programmatic advertising", r"\bprogrammatic (?:advertising|ads|media|buying|display|campaigns|channels|video)\b|\bdv360\b|\bthe trade desk\b"),
    ("Google Tag Manager", r"\bgoogle tag manager\b|\btag management\b|\btealium\b"), ("WordPress", r"\bwordpress\b"),
    ("Meta Ads", r"\b(?:meta|facebook|fb|instagram) ads\b|\bmeta ads manager\b|\bmeta business (?:manager|suite)\b|\bfacebook (?:and|&) instagram ads\b|\bmeta advertising\b|\bfacebook advertising\b"),
    ("Customer.io", r"\bcustomer\.io\b|\bonesignal\b|\bairship\b(?=,| and| or|/)|\bmoengage\b|\bclevertap\b"),
    ("Salesforce Marketing Cloud", r"\bsalesforce marketing cloud\b|\bmarketing cloud\b(?!-native)|\bsfmc\b|\bexacttarget\b"),
    ("Segment", r"\bsegment(?:\.io|\.com| cdp)\b|\btwilio segment\b|\bsegment(?:,| and| or| /) ?(?:amplitude|mixpanel|braze|rudderstack|hightouch|census|mparticle|heap|snowplow)\b|\b(?:amplitude|mixpanel|braze|rudderstack|hightouch|census|mparticle|heap|snowplow|google analytics),? (?:and |or |/)?segment\b(?! (?:of|the|our|your|by|level|growth|strategy|leads?|owners?|marketing))"),
    ("LinkedIn Ads", r"\blinkedin ads\b|\blinkedin campaign manager\b|\blinkedin advertising\b"), ("Semrush", r"\bsem ?rush\b|\bahrefs\b|\bmoz\b|\bscreaming frog\b|\bsimilarweb\b"),
    ("Google Search Console", r"\b(?:google )?search console\b|\bwebmaster tools\b"), ("Hootsuite", r"\bhootsuite\b|\bsprinklr\b|\bbrandwatch\b|\btalkwalker\b"),
    ("Adobe Analytics", r"\badobe analytics\b|\bomniture\b|\badobe experience (?:platform|cloud)\b|\badobe target\b"),
    ("App store optimization", r"\bapp store optimi[sz]ation\b|\baso\b(?= (?:strategy|experience|operational|operations|assets?|campaigns|tools?|specialist|manager))|\b(?:ua|seo),? (?:and |or |/)?aso\b|\baso,? (?:and |or |/)?(?:ua|seo)\b"),
    ("Conversion rate optimization", r"\bconversion rate optimi[sz]ation\b|\blanding page optimi[sz]ation\b"),
    # customer support
    ("Customer onboarding", r"\bcustomer onboarding\b|\bclient onboarding\b|\bonboarding (?:new )?(?:customers|clients|accounts)\b"),
    ("CSAT", r"\bcsat\b|\bnps\b|\bnet promoter\b|\bcustomer satisfaction scores?\b|\bces\b(?=,| and| or|/)"),
    ("Ticketing systems", r"\bticketing (?:systems?|tools?|software)\b|\bticket management\b"),
    ("Escalation management", r"\bescalation management\b|\bhandl(?:e|ing) escalations\b|\bescalated (?:issues|cases|tickets)\b"),
    ("Gainsight", r"\bgainsight\b|\bchurnzero\b|\btotango\b|\bvitally\b|\bplanhat\b"),
    ("Contact center software", r"\bfive9\b|\btalkdesk\b|\bgenesys\b|\bnice (?:incontact|cxone)\b|\baircall\b|\bdialpad\b|\bringcentral\b|\bamazon connect\b|\bcontact cent(?:er|re) (?:software|platforms?|technology)\b|\bccaas\b"),
    ("Salesforce Service Cloud", r"\bservice cloud\b"), ("Jira Service Management", r"\bjira service (?:management|desk)\b|\bjsm\b"), ("Intercom", r"\bintercom\b(?! systems?)"),
    # business systems
    ("ERP", r"\berps?\b|\benterprise resource planning\b"),
    ("E-commerce", r"\b(?:experience|background) (?:in|with) (?:\w+ ){0,2}?e-?commerce\b|\be-?commerce (?:experience|platforms?|operations|marketing|analytics|management|merchandising|brands)\b|\bdtc\b|\bd2c\b"),
    ("SAP S/4HANA", r"\bs/?4 ?hana\b|\bsap hana\b|\bsap (?:fico|fi/co|mm|sd|pp|wm|ewm|basis|abap|bw|ecc|successfactors|ariba|concur|fiori|btp|crm|scm|ibp|hcm|qm|pm)\b|\babap\b"),
    ("Oracle NetSuite", r"\bnetsuite (?:erp|administrator|admin|suitescript|saved searches|implementation|oneworld)\b|\bsuitescript\b|\bsuiteflow\b|\bsaved searches\b"),
    # finance and accounting
    ("Reconciliations", r"(?<!medication )(?<!medicine )(?<!med )(?<!drug )(?<!allergy )\breconciliations?\b(?! loops?)|\breconcil(?:e|ing) accounts\b"),
    ("Audit", r"\b(?:external|internal|financial|statutory|it) audits?\b|\baudit (?:experience|procedures|standards|readiness|support)\b|\bpcaob\b"),
    ("Financial modeling", r"\bfinancial model(?:l)?(?:ing|s)?\b|\bexcel model(?:l)?ing\b|\b(?:three|3)[- ]statement models?\b"),
    ("FP&A", r"\bfp&a\b|\bfinancial planning (?:and|&) analysis\b|\bbudgeting (?:and|&) forecasting\b|\bvariance analysis\b"),
    ("Month-end close", r"\bmonth[- ]end close\b|\bmonth[- ]end closing\b|\bmonth[- ]end\b|\bclose process\b|\bfinancial close\b|\byear[- ]end close\b"),
    ("Card payments", r"\bcard (?:payments?|issuing|processing|networks?|schemes?)\b|\b(?:visa|mastercard) (?:and|&|/) (?:mastercard|visa)\b|\binterchange (?:fees|rates)\b|\bchargebacks?\b|\bpayment processing\b"),
    ("M&A", r"\bm&a\b|\bmergers (?:and|&) acquisitions\b|\bcorporate development\b"), ("Internal controls", r"\binternal controls?\b|\bicfr\b|\bcoso\b"), ("GAAP", r"\bgaap\b"),
    ("Revenue recognition", r"\brevenue recognition\b|\basc ?606\b|\bifrs ?15\b"),
    ("Tax compliance", r"\btax (?:compliance|returns?|filings?|provisions?|planning|research)\b|\bindirect tax\b|\bsales (?:and use )?tax\b|\bvat\b|\bgst\b(?=,| and| or|/| returns?| compliance)|\basc ?740\b"),
    ("Big Four", r"\bbig (?:4|four)\b"), ("Underwriting", r"\bunderwriting\b|\bcredit (?:analysis|decisioning|underwriting|memos?)\b"), ("Derivatives", r"\bderivatives\b"),
    ("Accounts payable", r"\baccounts payable\b|\b(?<!\w)a/p\b|\bvendor payments\b|\binvoice processing\b|\bthree-way match\b|\b3-way match\b"),
    ("Treasury", r"\btreasury (?:management|operations|systems?)\b|\bcash management\b|\bkyriba\b|\bfx hedging\b|\bliquidity management\b"),
    ("Payroll", r"\bpayroll (?:processing|operations|administration|systems?|experience|compliance|tax(?:es)?|software|platforms?|providers?|cycles?|reconciliations?)\b|\b(?:process|run|running|processing) payroll\b|\bmulti-country payroll\b|\bglobal payroll\b"),
    ("Investor relations", r"\binvestor relations\b|\bearnings calls?\b|\bboard materials\b|\binvestor (?:reporting|updates|presentations)\b"),
    ("Accounts receivable", r"\baccounts receivable\b|\b(?<!\w)a/r\b|\bcash application\b|\bcredit control\b|\bcollections (?:process|operations|team|specialist|management)\b"),
    ("Fixed income", r"\bfixed income\b|\bbonds? markets?\b|\bcredit markets\b|\binterest rate products\b"), ("Coupa", r"\bcoupa\b|\bariba\b|\bjaggaer\b|\bzip\b(?= procurement)"),
    ("Consolidation", r"\bfinancial consolidation\b|\bconsolidations? (?:of|and) (?:financial|entities|subsidiaries)\b|\bintercompany (?:transactions|eliminations|accounting|reconciliations?)\b|\bmulti-entity (?:consolidation|accounting|close)\b|\bconsolidation (?:modules?|process|accounting)\b"),
    ("HFT", r"\bhft\b|\bhigh[- ]frequency trading\b|\balgorithmic trading\b|\balgo trading\b|\bsystematic trading\b"),
    ("ACH", r"\bach\b(?= (?:payments?|transfers?|transactions?|files?|network|returns|processing|debits?|credits?|rails?)|,| and| or|/|\))|\bnacha\b|\bfedwire\b|\bwire transfers?\b"),
    ("IFRS", r"\bifrs\b|\binternational financial reporting standards\b"),
    ("Oracle ERP", r"\boracle (?:fusion|ebs|e-business suite|erp|cloud erp|financials|hcm|scm|epm|cloud|r12|jd edwards)\b|\bjd edwards\b|\bpeoplesoft\b"), ("Anaplan", r"\banaplan\b"),
    ("Concur", r"\bconcur\b|\bexpensify\b|\bnavan\b"), ("Adaptive Planning", r"\badaptive (?:insights|planning)\b|\bworkday adaptive\b|\bpigment\b(?=,| and| or|/)|\bplanful\b|\bvena\b"),
    ("Transfer pricing", r"\btransfer pricing\b"), ("Lease accounting", r"\basc ?842\b|\bifrs ?16\b|\blease accounting\b"), ("QuickBooks", r"\bquick ?books\b|\bqbo\b"),
    ("Carta", r"\bcarta\b|\bpulley\b(?=,| and| or|/)|\bcap tables?\b"),
    ("DCF", r"\bdcf\b|\bdiscounted cash flows?\b|\bvaluation (?:methods|methodologies|models?|analysis)\b|\blbo models?\b"), ("Avalara", r"\bavalara\b|\bvertex\b(?= tax| o series|,| and)"),
    ("BlackLine", r"\bblackline\b|\bfloqast\b"), ("Xero", r"\bxero\b"), ("Sage Intacct", r"\bsage intacct\b|\bintacct\b|\bsage (?:50|100|200|300|x3|accounting)\b"),
    ("SEPA", r"\bsepa\b|\bfaster payments\b|\bbacs\b|\bchaps\b"), ("OneStream", r"\bonestream\b|\bhyperion\b|\boracle epm\b|\bessbase\b|\btagetik\b"),
    ("SWIFT payments", r"\bswift (?:payments?|messages?|messaging|network|mt\d*|mx|codes?|gpi|transfers?)\b|\bswift ?/ ?(?:sepa|ach|iso ?20022)\b|\b(?:sepa|ach|fedwire|iso ?20022),? (?:and |or |/)?swift\b|\biso ?20022\b"),
    # HR and recruiting
    ("Performance management", r"(?<!application )\bperformance management\b(?! (?:tools|platforms?|software|solutions))"),
    ("HRIS", r"\bhris\b|\bhcm (?:systems?|platforms?|software)\b|\bhr (?:systems?|technology|tech)\b"),
    ("Workforce planning", r"\bworkforce planning\b|\bheadcount planning\b|\borg design\b|\borganizational design\b|\borganisational design\b"),
    ("Employee relations", r"\bemployee relations\b|\bworkplace investigations?\b"),
    ("Full-cycle recruiting", r"\bfull[- ]cycle recruit(?:ing|ment|er)\b|\b(?:full|end)[- ]to[- ]end recruit(?:ing|ment)\b|\b360 recruit"),
    ("Compensation", r"\bcompensation (?:design|planning|analysis|analytics|benchmarking|modell?ing|strategy|reviews?|cycles?)\b|\bsalary benchmarking\b|\bjob level(?:l)?ing\b|\bjob architecture\b|\bequity administration\b|\bstock (?:plan )?administration\b"),
    ("Greenhouse", r"\b(?:experience|familiarity|proficiency|knowledge|expertise) (?:with|in|using|of) (?:\w+(?:,| or| and|/) ?){0,4}?greenhouse\b|\bgreenhouse(?:,| or| and| /|/) ?(?:lever|ashby|workday|icims|gem|linkedin|bamboohr|rippling|smartrecruiters|jobvite|modernloop|goodtime)\b|\b(?:lever|ashby|workday|icims|gem|bamboohr|rippling|smartrecruiters|jobvite|successfactors),? (?:and |or |/)?greenhouse\b|\b(?:ats|applicant tracking systems?)(?: platforms?| tools?)?,? (?:such as|like|e\.g\.,?|including) (?:\w+,? (?:or |and )?){0,3}?greenhouse\b|\bats: greenhouse\b|\bgreenhouse (?:ats|admin\w*|recruiting|reports?|reporting)\b"),
    ("Applicant tracking systems", r"(?<!our )(?<!its )(?<!through )\bapplicant tracking systems?\b|\b(?:recruiting|recruitment|hiring|sourcing|candidates?|talent)\b[^.\n]{0,60}(?<!our )\bats\b(?!/)|(?<!our )\bats\b(?!/)[^.\n]{0,60}\b(?:recruiting|recruitment|hiring|sourcing|candidates?|talent)\b"),
    ("LinkedIn Recruiter", r"\blinkedin recruiter\b|\blinkedin talent\b|\bsourcing tools\b|\bgem\b(?= ,|,| and| or|/)|\bseekout\b|\bhireez\b"),
    ("Technical recruiting", r"\btechnical recruit(?:ing|ment)\b|\btech(?:nical)? hiring\b|\bengineering (?:hiring|recruiting)\b"),
    ("Deel", r"\bdeel\b|\bremote\.com\b|\boyster hr\b|\bvelocity global\b|\bemployer of record\b|\beor\b(?=,| and| or|/| providers?| partners?| services?)"),
    ("Employment law", r"\b(?:knowledge|understanding|experience|expertise|familiarity) (?:of|with|in) (?:\w+ ){0,4}?(?:employment|labou?r) laws?\b|\bemployment law (?:experience|expertise|knowledge|matters|issues|compliance|advice)\b|\bwage and hour (?:laws?|compliance|claims)\b"),
    ("Benefits administration", r"\bbenefits administration\b|\bbenefits? (?:program|plan) (?:design|management|administration)\b|\bopen enrollment (?:process|administration|period)\b|\bleave (?:administration|management)\b|\bcobra administration\b|\b401\(k\) administration\b"),
    ("Boolean search", r"\bboolean (?:search|strings?|sourcing|logic)\b|\bx-ray search"),
    ("ADP", r"\badp (?:workforce now|payroll|vantage|celergo|globalview|run)\b|\b(?:rippling|workday|gusto|paylocity|paycom|paychex|ukg|ceridian|dayforce|bamboohr),? (?:and |or |/)?adp\b|\badp,? (?:and |or |/)?(?:rippling|workday|gusto|paylocity|paycom|paychex|ukg|ceridian|dayforce|bamboohr|successfactors)\b"),
    ("Ashby", r"\bashby(?:hq)?(?:,| and| or| /) ?(?:greenhouse|lever|workday|icims|gem)\b|\b(?:greenhouse|lever|workday|icims|gem),? (?:and |or |/)?ashby\b|\bashby (?:ats|recruiting)\b"),
    ("UKG", r"\bukg\b|\bultipro\b|\bkronos\b|\bdayforce\b|\bceridian\b|\bpaycom\b|\bpaychex\b"),
    ("Lever", r"\blever(?:,| and| or| /) ?(?:greenhouse|ashby|workday|icims|gem|smartrecruiters|workable)\b|\b(?:greenhouse|ashby|workday|icims|gem|smartrecruiters|workable),? (?:and |or |/)?lever\b(?!age)"),
    ("BambooHR", r"\bbamboo ?hr\b|\bhibob\b|\bpersonio\b"), ("SuccessFactors", r"\bsuccess ?factors\b"),
    # legal and compliance
    ("Regulatory compliance", r"\bregulatory (?:compliance|frameworks?|reporting|change|filings|submissions|affairs|examinations?|exams?)\b|\bcompliance (?:monitoring|testing)\b"),
    ("SOX", r"\bsox\b|\bsarbanes[- ]oxley\b|\bj-?sox\b"), ("HIPAA", r"\bhipaa\b"),
    ("KYC", r"\bkyc\b(?= (?:procedures|processes|checks|reviews|requirements|policies|operations|onboarding|refresh|analyst|verification|programs?|documentation)|/|,| and)|\bknow your customer\b|\bcustomer due diligence\b|\bcdd\b|\benhanced due diligence\b|\bedd\b"),
    ("Fraud prevention", r"\bfraud (?:prevention|investigations?|analytics|operations|risk|monitoring|models?|strategy|rules)\b|\banti-fraud\b|\bfraud detection (?:models?|systems?|rules)\b"),
    ("GRC", r"\bgrc\b|\bgovernance,? risk,? (?:and|&) compliance\b"),
    ("Law degree", r"\bjuris doctor(?:ate)?\b|\bj\.d\.(?= |,|\))|\bjd (?:degree|from|or|required)\b|\b(?:jd|j\.d\.|llb|ll\.b\.?|llm|ll\.m\.?) (?:or|and|/) (?:jd|llb|llm|j\.d\.|ll\.b|ll\.m)\b|\blaw degree\b|\bllb\b|\bll\.b\b|\bqualified (?:lawyer|solicitor|attorney)\b"),
    ("Contract management", r"\bcontract (?:lifecycle )?management\b|\bclm\b|\bironclad\b|\bicertis\b|\bconga\b(?=,| and| or|/)|\bagiloft\b"),
    ("GDPR", r"\b(?:knowledge|understanding|experience|familiarity|expertise|working knowledge|compliance) (?:of|with|in|under) (?:\w+ ){0,5}?gdpr\b|\bgdpr(?:,| and| or| /) ?(?:ccpa|hipaa|soc ?2|iso ?27001|pci|cpra|lgpd|dpa|eprivacy|uk gdpr)\b|\b(?:ccpa|hipaa|soc ?2|iso ?27001|pci[- ]?dss|cpra|lgpd|data protection|privacy),? (?:and |or |/)?gdpr\b|\bgdpr (?:compliance|requirements|frameworks?|programs?|audits?|expertise|knowledge)\b"),
    ("BSA/AML", r"\bbank secrecy act\b|\bbsa\b(?=/aml|,? (?:and|&) aml| compliance| officer| regulations?| requirements)|\bbsa/aml\b|\banti[- ]money laundering\b|\btransaction monitoring\b|\bsuspicious activity reports?\b|\bsars?\b(?= filings?| reports?| filing)|\bctrs?\b(?= filings?)"),
    ("Litigation", r"\blitigation\b|\bdisputes? resolution\b"),
    ("Data privacy", r"\bdata privacy (?:laws?|regulations|compliance|programs?|engineering|frameworks|requirements|expertise|experience)\b|\b(?:knowledge|understanding|experience|expertise|familiarity) (?:of|with|in) (?:\w+ ){0,3}?(?:data )?privacy (?:laws?|regulations)\b|\bprivacy (?:programs?|compliance|by design|impact assessments?|engineering|counsel)\b|\bdpias?\b|\bdata protection (?:impact|officer)\b"),
    ("Bar admission", r"\b(?:admitted|admission|licensed) to (?:practi[cs]e (?:law )?in |the )?(?:[a-z]+ ){0,3}?bar\b|\bbar (?:admission|membership|licen[cs]e)\b|\bactive (?:\w+ ){0,3}?bar (?:membership|licen[cs]e|status|admission)\b|\bmember (?:in good standing )?of (?:the|a) (?:\w+ ){0,3}?bar\b|\bin good standing (?:with|of|in) (?:the|a|at least one) (?:\w+ ){0,3}?bar\b|\bstate bar\b"),
    ("CCPA", r"\bccpa(?:,| and| or| /) ?(?:gdpr|hipaa|lgpd)\b|\b(?:gdpr|hipaa|lgpd|privacy laws? such as),? (?:and |or |/)?ccpa\b"),
    ("Contract drafting", r"\bdraft(?:ing)?,? (?:review(?:ing)?,? )?(?:and )?negotiat(?:e|ing) (?:\w+ ){0,3}?(?:contracts|agreements)\b|\bcontract drafting\b|\bdrafting (?:and reviewing )?(?:contracts|agreements)\b|\b(?:draft|review) (?:and (?:draft|review|negotiate) )?(?:commercial )?contracts\b"),
    ("Sanctions screening", r"\bofac\b|\bsanctions (?:screening|compliance|regimes?|programs?|lists?|regulations|risk|laws?)\b"),
    ("MiCA", r"\bmica\b|\bmarkets in crypto-?assets\b|\btravel rule\b|\bvasps?\b|\bcasps?\b"),
    ("Corporate governance", r"\bcorporate governance\b|\bboard governance\b|\bcorporate secretar(?:y|ial)\b|\bentity management\b|\bboard minutes\b"),
    ("SEC regulations", r"\bsec (?:regulations|rules|reporting|filings|compliance|registered|registration)\b|(?<!\$)\b10-k\b|(?<!\$)\b10-q\b|\binvestment advisers act\b|\bexchange act\b|\breg (?:bi|nms|sho)\b"),
    ("FINRA", r"\bfinra\b|\bseries (?:7|24|57|63|65|66|79|82|99)\b|\bsie (?:exam|licen[cs]e)\b"),
    ("Intellectual property", r"\bintellectual property (?:law|rights|matters|portfolio|strategy|protection|counsel|litigation|licensing)\b|\bpatent (?:law|prosecution|filings?|portfolio|litigation|applications?)\b|\btrademark (?:law|prosecution|portfolio|filings|clearance)\b|\bip (?:law|portfolio|strategy|counsel|protection|licensing)\b"),
    ("Employment contracts", r"\bemployment (?:contracts|agreements|documentation)\b|\boffer letters\b"),
    ("eDiscovery", r"\be-?discovery\b|\brelativity\b(?= ,|,| and| or|/| review| one)|\blitigation support\b|\blegal holds?\b"),
    ("FCA regulations", r"\bfca\b|\bfinancial conduct authority\b|\bconsumer duty\b|\bsm&cr\b|\bprudential regulation authority\b"),
    ("Export controls", r"\b(?:knowledge|understanding|experience|familiarity|expertise) (?:of|with|in) (?:\w+ ){0,4}?(?:export controls?|itar|ear)\b|\beccns?\b|\bexport classification\b|\bexport licen[cs]ing\b"),
    ("CFTC", r"\bcftc\b|\bcommodity futures trading commission\b|\bnfa\b(?= rules|,| and)"),
    ("Legal research", r"\blegal research\b|\bwestlaw\b|\blexis ?nexis\b|\blexis\+?\b|\bpractical law\b"),
    ("Anti-bribery", r"\bfcpa\b|\bforeign corrupt practices act\b|\banti[- ](?:bribery|corruption)\b|\buk bribery act\b"),
    ("Licensing", r"\bmoney transmitter licen[cs](?:e|es|ing)\b|\bregulatory licen[cs](?:e|es|ing)\b|\be-?money licen[cs]e\b|\bemi licen[cs]e\b"),
    # crypto
    ("Crypto custody", r"\b(?:digital asset|crypto(?:currency)?) custody\b|\bcustody (?:solutions?|platforms?|wallets?|operations|technology)\b|\bhot wallets?\b|\bfireblocks\b|\bself-custody\b"),
    ("Staking", r"\bstaking\b|\bvalidators?\b(?= nodes?| operations| infrastructure|,| and)|\bliquid staking\b|\brestaking\b"),
    ("On-chain analytics", r"\bon-?chain (?:analytics|analysis|data|metrics|investigations?)\b|\bdune(?: analytics)?\b(?=,| and| or|/|\))|\bnansen\b|\bblockchain analytics\b|\bchainalysis\b|\belliptic\b|\btrm labs\b|\bthe graph\b|\bsubgraphs?\b"),
    ("DEX", r"\bdexs?\b|\bdecentrali[sz]ed exchanges?\b|\bamms?\b|\bautomated market makers?\b|\buniswap\b|\bperps?\b(?= dex|,| and| exchanges?| trading)|\bperpetual (?:futures|swaps|contracts)\b"),
    ("Market making", r"\bmarket[- ]making\b|\bliquidity provi(?:sion|ders?|ding)\b"),
    ("Wallets", r"\bwallet (?:development|infrastructure|integrations?|sdks?|security|apps?)\b|\bnon-custodial wallets?\b|\bsmart wallets?\b|\bembedded wallets?\b|\bmetamask\b|\bwalletconnect\b"),
    ("MPC", r"\bmpc\b|\bmulti-?party computation\b|\bthreshold signatures?\b|\btss\b(?=,| and| wallets?)"),
    ("Rollups", r"\brollups?\b|\blayer[- ]?2 (?:scaling|networks?|solutions?|chains?|protocols?|blockchains?|ecosystems?)\b|\bl2 (?:chains?|networks?|scaling|rollups?|solutions?|blockchains?|ecosystems?)\b|\bzk-?evm\b"),
    ("Arbitrum", r"\barbitrum\b|\boptimism\b(?= (?:superchain|stack|network|mainnet|collective)|,)|\bop stack\b|\bbase chain\b|\bzksync\b|\bstarknet\b|\bpolygon (?:pos|zkevm|cdk|network|chain|labs)\b|\bscroll\b(?= zkevm)"),
    ("Tokenomics", r"\btokenomics\b|\btoken (?:design|launches|listings?|generation event)\b|\btge\b|\bairdrops?\b"),
    ("Smart contract auditing", r"\bsmart contract (?:audit(?:s|ing|ors?)?|security|vulnerabilit(?:y|ies)|reviews?)\b|\bsecurity audits? of smart contracts\b|\bslither\b|\bechidna\b|\bcertora\b"),
    ("Web3", r"\bweb ?3\b(?!\.js|js|\.py)"), ("Blockchain", r"\bblockchains?\b"),
    # hardware and robotics
    ("Control systems", r"(?<!version )(?<!source )(?<!revision )\bcontrol (?:systems|theory|loops?|algorithms|engineering)\b|\bpid (?:control|controllers?|loops?|tuning)\b|\bkalman filters?\b|\bstate estimation\b|\bmpc\b(?= control)|\bmodel predictive control\b"),
    ("Firmware", r"\bfirmware\b|\bbootloaders?\b"), ("Mechatronics", r"\bmechatronics?\b|\belectromechanical\b|\bactuators?\b|\bsensors and actuators\b|\bstepper motors?\b|\bbldc\b"),
    ("Hardware testing", r"\bhardware (?:testing|validation|verification|bring-?up|debugging|test)\b|\bhil\b|\bhardware[- ]in[- ]the[- ]loop\b|\bdvt\b|\bevt\b|\bpvt\b|\bemc (?:testing|compliance)\b|\bemi/emc\b|\bemc/emi\b"),
    ("Test equipment", r"\boscilloscopes?\b|\bspectrum analy[sz]ers?\b|\blogic analy[sz]ers?\b|\bnetwork analy[sz]ers?\b|\bfunction generators?\b|\btest equipment\b|\blab equipment\b"),
    ("High-performance computing", r"\bhpc\b|\bhigh[- ]performance computing\b|\bslurm\b|\bmpi\b|\binfiniband\b|\brdma\b|\bnccl\b"),
    ("Storage systems", r"\bstorage systems?\b|\bdistributed storage\b|\bobject storage\b|\bblock storage\b|\bceph\b|\bnvme\b|\bfile systems? (?:development|design|internals)\b"),
    ("Hardware interfaces", r"\bi2c\b|\bspi\b(?=,| and| or|/| bus)|\buart\b|\busb\b(?=,| and| or|/| protocols?)|\bpcie\b|\bethernet\b(?=,| and| or|/| phy)|\bjtag\b|\bgpio\b|\bmipi\b|\bddr\d?\b"),
    ("PCB design", r"\bpcbs?\b|\bprinted circuit boards?\b|\baltium\b|\bkicad\b|\borcad\b|\ballegro\b(?= pcb|,| and)|\bpads\b(?= layout|,)|\bmentor (?:graphics|xpedition)\b|\bboard (?:design|layout|bring-?up)\b"),
    ("Operating systems", r"\boperating systems? (?:internals|development|design|concepts|kernels?)\b|\bos internals\b|\bkernel internals\b|\bsystems programming\b|\bmemory management\b|\bvirtual memory\b|\bschedulers?\b(?= and| ,|,)"),
    ("Optics", r"\boptical (?:design|engineering|systems|components|metrology|testing|alignment)\b|\bphotonics\b|\bzemax\b|\bcode v\b|\boptics (?:design|engineering|experience)\b|\b(?:lasers?|optics),? (?:and|&) (?:optics|lasers?|photonics)\b"),
    ("RF engineering", r"\brf (?:design|engineering|circuits?|systems|testing|front[- ]end|hardware|ic)\b|\bradio frequency\b|\bantennas?\b|\bmicrowave\b(?= engineering| circuits| design|,)|\bbluetooth low energy\b|\bble\b|\blora\b(?=wan|,| and)|\bzigbee\b|\b5g nr\b|\blte\b"),
    ("Robotics", r"\brobotics (?:experience|software|engineering|systems|stack|background|middleware|research|frameworks?)\b|\b(?:experience|background) (?:in|with) robotics\b|\bmotion planning\b|\bpath planning\b|\binverse kinematics\b|\bgazebo\b|\bmoveit\b|\bisaac sim\b|\bmujoco\b|\brobot(?:ic)? (?:arms?|manipulators?|manipulation)\b"),
    ("Networking protocols", r"\bnetworking (?:stack|protocols)\b|\bnetwork stack\b|\bquic\b|\bhttp/?[23]\b|\bdpdk\b|\bebpf\b|\bxdp\b|\bsmartnics?\b|\btcp\b(?= ,|,| stack| and udp)"),
    ("Analog design", r"\banalog (?:design|circuits?|ic|electronics|mixed[- ]signal|front[- ]end)\b|\bmixed[- ]signal\b|\bpower electronics\b|\bpmics?\b|\bdc-dc\b"),
    ("Compilers", r"\bcompilers?\b|\bllvm\b|\bmlir\b|\bgcc\b(?=,| or| and| /|/|\))|\bclang\b|\bjit compil\w+"),
    ("ASIC", r"\basics?\b|\bsoc design\b|\bsystem[- ]on[- ]chip\b|\btape-?out\b|\bsilicon (?:validation|bring-?up|design)\b"),
    ("Computer architecture", r"\bcomputer architecture\b|\bcpu (?:architecture|design|microarchitecture)\b|\barm architecture\b|\brisc-?v\b|\bx86(?:-64)?\b|\bcache coherence\b|\binstruction sets?\b"),
    ("Embedded Linux", r"\bembedded linux\b|\byocto\b|\bbuildroot\b|\blinux kernel\b|\bkernel (?:development|drivers?|modules?)\b|\bdevice drivers?\b|\bdevice tree\b|\bu-?boot\b"),
    ("FPGA", r"\bfpgas?\b|\bxilinx\b|\bvivado\b|\bquartus\b|\bintel psg\b|\baltera\b"),
    ("RTL design", r"\brtl\b|\bregister transfer level\b|\bmicroarchitecture\b|\bstatic timing analysis\b"),
    ("AUTOSAR", r"\bautosar\b|\biso ?26262\b|\baspice\b|\bfunctional safety\b|\bmisra\b|\basil\b"),
    ("Microcontrollers", r"\bmicrocontrollers?\b|\bmcus?\b|\bstm32\b|\barm cortex(?:-m)?\b|\besp32\b|\bnrf52\b|\barduino\b|\braspberry pi\b|\bpic\d+\b|\bavr\b"),
    ("DSP", r"\bdigital signal processing\b|\bsignal processing\b|\bdsp (?:algorithms|firmware|programming|cores?|processors?|blocks|engineers?)\b"),
    ("GPU programming", r"\bgpu (?:programming|kernels?|architecture|computing|optimi[sz]ation|performance)\b|\bopencl\b|\brocm\b|\bhip\b(?= ,|,| kernels?| and)|\bmetal shaders?\b|\bcutlass\b"),
    ("Lidar", r"\blidars?\b|\bpoint clouds?\b"), ("RTOS", r"\brtos\b|\bfreertos\b|\bzephyr\b|\bthreadx\b|\bvxworks\b|\bqnx\b|\breal-?time operating systems?\b"),
    ("CAN bus", r"\bcan bus\b|\bcan-?fd\b|\bcanopen\b|\bj1939\b|\blin bus\b|\bautomotive ethernet\b|\bflexray\b|\bcanoe\b|\bcanalyzer\b|\bvector tools\b"),
    ("Sensor fusion", r"\bsensor fusion\b|\bvisual (?:slam|odometry)\b|\bslam (?:algorithms|systems|pipelines)\b|\bsimultaneous locali[sz]ation and mapping\b"),
    ("SystemVerilog", r"\bsystemverilog\b|\bsystem verilog\b"),
    ("Cadence", r"\bcadence (?:virtuoso|innovus|genus|xcelium|spectre|allegro|tools|design systems)\b|\bsynopsys\b|\bvirtuoso\b|\bdesign compiler\b|\bprimetime\b|\bmentor (?:questa|calibre)\b|\bcalibre\b(?= drc|,| and)"),
    ("LabVIEW", r"\blabview\b|\bteststand\b|\bnational instruments\b|\bni daq\b"), ("SPICE", r"\bspice\b(?= simulations?|,| models?| and| or)|\bltspice\b|\bhspice\b|\bpspice\b|\bspectre\b"),
    ("Simulink", r"\bsimulink\b|\bstateflow\b"), ("UVM", r"\buvm\b|\buniversal verification methodology\b"), ("VHDL", r"\bvhdl\b"),
    # manufacturing, trades and logistics
    ("CAD", r"(?<![0-9] )(?<![0-9])(?<!hour )(?<!year )(?<!month )(?<!annum )\bcad\b(?! ?\$| ?\d| (?:dollars?|currency|per|salary|annually|pay|plus|base)\b|,? plus|\.? salary)|\bcomputer[- ]aided design\b"),
    ("Procurement", r"\bprocurement (?:experience|operations|processes|process|policies|systems|software|tools|strategy|strategies|best practices|function|teams?|professionals?)\b|\bstrategic sourcing\b|\bsourcing (?:and|&) procurement\b|\bprocure-to-pay\b|\bsupplier (?:negotiations?|qualification|selection|development|evaluation|onboarding)\b|\bcategory management\b"),
    ("Inventory management", r"\binventory (?:management|control|planning|accuracy|optimi[sz]ation|levels|counts?)\b|\bcycle counts?\b|\bcycle counting\b|\bstock control\b"),
    ("Aviation", r"\ba&p licen[cs]e\b|\bairframe and powerplant\b|\bfaa (?:regulations|certificates?|certification|licen[cs]e|part \d+)\b|\bpart (?:121|135|145|91)\b|\bfaa\b|\beasa\b|\bavionics\b|\baircraft maintenance\b"),
    ("Forklift", r"\bforklifts?\b|\bpower(?:ed)? industrial trucks?\b|\breach trucks?\b|\bpallet jacks?\b|\border pickers?\b(?= ,|,| and| or| equipment)|\bscissor lifts?\b|\baerial lifts?\b|\bboom lifts?\b"),
    ("Mechanical assembly", r"\bmechanical assembly\b|\belectro-?mechanical assembly\b|\bassembly (?:line|instructions|drawings|procedures)\b|\bhand tools\b|\bpower tools\b|\btorque (?:tools|wrenches?|specs?)\b"),
    ("CNC machining", r"\bcnc\b|\bg-?code\b|\bmastercam\b|\bcam programming\b|\bmachining\b|\blathes?\b|\bmills?\b(?= ,|,| and| or)|\bhaas\b|\bmazak\b|\bfanuc\b|\bokuma\b"),
    ("GD&T", r"\bgd&t\b|\bgeometric dimensioning\b|\btolerance (?:analysis|stack)"),
    ("Lean manufacturing", r"\blean (?:manufacturing|principles|methodolog(?:y|ies)|six sigma|tools|practices|production|management|thinking|operations|enterprise|processes)\b|\bkaizen\b|\b5s\b|\bvalue stream mapping\b|\bkanban systems?\b|\btoyota production system\b|\bpoka[- ]yoke\b|\bgemba\b"),
    ("Electrical troubleshooting", r"\belectrical (?:troubleshooting|schematics|diagrams|drawings)\b|\btroubleshoot(?:ing)? electrical\b|\bmultimeters?\b|\bmegger\b|\bthree[- ]phase\b|\b3[- ]phase\b|\b480v\b"),
    ("Six Sigma", r"\bsix sigma\b|\b6 ?sigma\b|\bdmaic\b|\b(?:green|black|yellow) belt\b"),
    ("Blueprint reading", r"\b(?:read(?:ing)?|interpret(?:ing)?|understand(?:ing)?) (?:and interpret(?:ing)? )?(?:blueprints|schematics|technical drawings|engineering drawings|mechanical drawings|drawings|wiring diagrams)\b|\bblueprint reading\b"),
    ("Soldering", r"\bsolder(?:ing)?\b|\bipc-?a?-?6\d\d\b|\bj-std-001\b|\brework stations?\b|\bthrough[- ]hole\b|\bsmt\b|\bsurface mount\b"),
    ("Preventive maintenance", r"\bpreventive maintenance\b|\bpreventative maintenance\b|\bpredictive maintenance\b|\bcmms\b|\bmaximo\b"),
    ("FEA", r"\bfea\b|\bfinite element\b|\bansys\b|\babaqus\b|\bcomsol\b|\bnastran\b"), ("FMEA", r"\bp?d?fmea\b|\bfailure modes? and effects?\b"),
    ("HVAC", r"\bhvac(?:/?r)?\b|\bheating,? ventilation\b|\bchillers?\b|\brooftop units?\b|\bboilers?\b(?= ,|,| and| or)"),
    ("Welding", r"\bwelding\b|\bmig\b|\btig\b|\bsmaw\b|\bgmaw\b|\bgtaw\b|\bfcaw\b|\baws d1\.\d\b|\bbrazing\b"),
    ("SPC", r"\bspc\b|\bstatistical process control\b|\bcpk\b|\bmsa\b(?=,| and| or| studies| \()|\bgauge r&r\b|\bppap\b|\bapqp\b"),
    ("Hydraulics", r"\bhydraulics?\b|\bpneumatics?\b|\bhydraulic (?:systems|equipment|presses)\b"),
    ("Siemens NX", r"\bsiemens nx\b|\bunigraphics\b|\bnx cad\b|\bteamcenter\b|\bnx(?:,| and| or| /) ?(?:catia|creo|solidworks)\b|\b(?:catia|creo|solidworks),? (?:and |or |/)?nx\b"),
    ("Construction management", r"\bconstruction (?:management|scheduling|documents|drawings|safety|administration)\b|\bprocore\b|\bbluebeam\b|\bpunch lists?\b"),
    ("SolidWorks", r"\bsolid ?works\b"),
    ("Industrial automation", r"\bindustrial automation\b|\bindustrial controls?\b|\bcontrols engineering\b|\bmotion control\b|\bservo (?:drives?|motors?|systems)\b|\bvfds?\b|\bvariable frequency drives?\b"),
    ("Quality inspection", r"\bquality inspections?\b|\bfirst article inspections?\b|\bfai\b(?=,| and| or|/| reports?)|\bincoming inspection\b|\bcmm\b|\bcoordinate measuring\b|\bcalipers?\b|\bmicrometers?\b|\bheight gauges?\b"),
    ("Facilities management", r"\bfacilities management\b|\bfacility management\b|\bbuilding management systems?\b|\bbuilding automation\b|\bbms\b(?=/epms| and epms|,? scada)"),
    ("PLC", r"\bplcs?\b|\bprogrammable logic controllers?\b|\bladder logic\b|\ballen[- ]bradley\b|\brockwell (?:automation|studio)\b|\bstudio ?5000\b|\bsiemens (?:s7|tia portal|step 7)\b|\btia portal\b"),
    ("OSHA", r"\bosha\b"), ("ISO 9001", r"\biso ?9001\b|\bas ?9100\b|\biatf ?16949\b|\biso ?14001\b|\biso ?45001\b"), ("MRP", r"\bmrp\b|\bmaterial requirements planning\b"),
    ("Low voltage", r"\blow[- ]voltage\b|\bcctv\b|\bfire alarm (?:systems?|panels?|install\w*|technicians?|wiring|devices)\b|\bstructured wiring\b|\bfiber optic\b|\bfibre optic\b"), ("AutoCAD", r"\bauto ?cad\b"),
    ("NFPA 70E", r"\bnfpa ?70e\b|\barc flash\b|\blockout/?tagout\b|\bloto\b|\block-?out,? tag-?out\b"),
    ("National Electrical Code", r"\bnational electric(?:al)? code\b|\bnec\b(?= code|,| and| standards| requirements| compliance)|\bjourneyman (?:electrician|licen[cs]e)\b|\bmaster electrician\b|\belectrical licen[cs]e\b"),
    ("Demand planning", r"\bdemand (?:planning|forecasting|planners?)\b|\bsupply planning\b|\bs&op\b|\bsales and operations planning\b|\bibp\b(?=,| and| process)|\bkinaxis\b|\bsap ibp\b|\bsap apo\b"),
    ("Quality management systems", r"\bqms\b|\bquality management systems?\b|\biso ?13485\b|\biso ?14971\b|\biec ?62304\b"),
    ("SCADA", r"\bscada\b|\bhmi\b|\bdcs\b(?= systems?|,| and)|\bignition\b(?= scada|,| and| or)|\bwonderware\b|\bfactorytalk\b"), ("CATIA", r"\bcatia\b|\b3dexperience\b"),
    ("CFD", r"\bcfd\b|\bcomputational fluid dynamics\b|\bstar-?ccm\b|\bopenfoam\b|\bfluent\b(?= ,|,| and| or|/| cfd)"),
    ("Hazmat", r"\bhaz ?mat\b|(?<!bio )(?<!bio-)\bhazardous (?:materials?|waste|goods)\b|\bdangerous goods\b|\biata dgr\b|\bdot hazmat\b"),
    ("Revit", r"\brevit\b|\bbim\b(?= ,|,| and| or| modell?ing| models?| software| 360| coordination)|\bbuilding information model"),
    ("Additive manufacturing", r"\badditive manufacturing\b|\b3d printing\b"),
    ("Freight", r"\bfreight (?:forwarding|brokerage|operations|logistics|audit|management|experience)\b|\bltl\b|\bftl\b|\bdrayage\b|\bintermodal\b|\b(?:ocean|air) freight\b"),
    ("WMS", r"\bwms\b|\bwarehouse management systems?\b|\bmanhattan (?:associates|scale|active|wms)\b|\bblue yonder\b|\bjda\b|\bhighjump\b|\bkorber\b|\bkörber\b"),
    ("Last-mile delivery", r"\blast[- ]mile\b|\broute planning\b|\broute optimi[sz]ation\b|\bdispatching\b"),
    ("Composites", r"\bcomposites?\b(?= manufacturing|,| layup| materials| fabrication| repair)|\bcarbon fib(?:er|re)\b|\blay-?up\b|\bautoclave\b|\bprepreg\b"),
    ("Creo", r"\bcreo\b|\bptc creo\b|\bpro/?engineer\b|\bwindchill\b"),
    ("Cost estimating", r"\bcost estimat(?:ing|es|ion)\b|\bconstruction estimating\b|\bquantity takeoffs?\b|\bestimating (?:software|experience)\b|\bbid estimat\w+"),
    ("GMP", r"\bc?gmp\b|\bgood manufacturing practices?\b|\bglp\b(?!-)|\bgxp\b"),
    ("Customs compliance", r"\bcustoms (?:clearance|brokerage|compliance|regulations|documentation|entries|declarations)\b|\bhts codes?\b|\btariff classification\b|\bimport/export\b|\bimport and export\b"),
    ("RF scanners", r"\brf (?:scanners?|guns?)\b|\bhandheld scanners?\b|\bbarcode scanners?\b|\bscanning equipment\b"),
    ("DOT regulations", r"\bdot (?:regulations|compliance|physical|medical card|requirements|drug test(?:ing)?)\b|\bdepartment of transportation\b|\bfmcsa\b|\bhours of service\b|\beld\b"),
    ("Onshape", r"\bonshape\b|\bfusion ?360\b|\bautodesk inventor\b"),
    ("TMS", r"\btransportation management systems?\b|\btms\b(?= systems?| software|,| and| or|/| platforms?)|\bmcleod\b|\bmercurygate\b|\boracle otm\b"),
    ("CDL", r"\bcdl\b|\bcommercial driver['’]?s licen[cs]e\b|\bclass [ab] licen[cs]e\b"),
    # healthcare
    ("Clinical trials", r"\bclinical (?:trials?|research|studies|development|operations)\b|\bgood clinical practice\b|\bich[- ]gcp\b|\bctms\b|\bedc\b(?= systems?|,| and)|\bmedidata\b|\bveeva\b"),
    ("Medical devices", r"\bmedical devices?\b|\bmedtech\b|\bdevice (?:design|development|regulations)\b"),
    ("Behavioral health", r"\bbehaviou?ral health (?:clinicians?|settings?|services|care|treatment|providers?|experience|conditions)\b|\bcognitive behaviou?ral therapy\b|\btrauma-informed\b|\bpsychotherapy\b|\baba therapy\b|\bapplied behaviou?r analysis\b|\bsubstance use disorders?\b"),
    ("CPR", r"\bcpr\b|\bfirst aid\b"),
    ("EHR", r"\behrs?\b|\belectronic (?:health|medical|patient) records?\b|\bemrs? (?:systems?|software|platforms?|experience|integrations?)\b|\b(?:athena|epic|cerner|ehr/)emr\b|\bemr/ehr\b"),
    ("Board certification", r"\bboard[- ]certified\b|\bboard certification\b|\bboard[- ]eligible\b|\babim\b|\babfm\b|\bancc\b|\baanp\b"),
    ("FDA regulations", r"\b21 cfr\b|\bfda (?:regulations|regulatory|requirements|guidelines|guidance|submissions|compliance|approvals?|clearance|inspections?|audits)\b|\b510\(k\)|\bpma\b(?= submissions?|,)|\bde novo\b(?= submissions?|,)|\bsamd\b|\bmdr\b(?=,| and| compliance)"),
    ("Pharmacy", r"\bpharmacy (?:licen[cs]e|technician|operations|benefits?)\b|\bpharmd\b|\bptcb\b|\bcpht\b|\bpbm\b|\bformular(?:y|ies)\b"),
    ("Medicare and Medicaid", r"\bmedicare\b|\bmedicaid\b|\bcms (?:guidelines|regulations|requirements|rules)\b"),
    ("Revenue cycle management", r"\brevenue cycle\b|\bmedical billing\b|\bclaims? (?:submission|denials?|scrubbing)\b|\bdenials? management\b|\brcm (?:collections|operations|specialist|team|and ehr)\b"),
    ("RN license", r"\b(?:rn|registered nurse|nursing) licen[cs](?:e|ure)\b|\blicen[cs]ed (?:as an? )?(?:rn|registered nurse)\b|\bactive (?:\w+ ){0,3}?(?:rn|registered nurse|nursing) licen[cs]e\b|\bcompact (?:rn |nursing |multi-?state )?licen[cs]e\b|\bnlc\b|\bmulti-?state licen[cs]e\b|\bunencumbered (?:\w+ ){0,3}?licen[cs]e\b"),
    ("BLS", r"\bbls\b(?= certif|,| and| or| /|/|\)| card| required| \()|\bbasic life support\b"), ("HL7 FHIR", r"\bfhir\b|\bhl7\b|\bdicom\b"),
    ("Medical coding", r"\bmedical coding\b|\bicd-?10(?:-cm)?\b|\bcpt(?:-4)? cod(?:es|ing)\b|\bcpt,? (?:and |/)?(?:icd|hcpcs)\b|\b(?:icd-?10(?:-cm)?|hcpcs),? (?:and |/)?cpt\b|\bhcpcs\b|\bcertified professional coder\b|\bms-drgs?\b"),
    ("Prior authorization", r"\bprior auth(?:ori[sz]ations?)?\b|\bpre-?authori[sz]ations?\b|\bbenefits? verification\b|\binsurance verification\b"),
    # retail and hospitality
    ("POS systems", r"\bpos (?:systems?|software|terminals?|hardware)\b|\bpoint[- ]of[- ]sale\b|\bsquare pos\b|\btoast pos\b|\bcash registers?\b"),
    ("Cash handling", r"\bcash handling\b|\bhandl(?:e|ing) cash\b|\bcounting cash\b|\bbalancing (?:the )?(?:cash )?drawers?\b|\bopening and closing tills\b"),
    ("Food safety", r"\bfood safety\b|\bservsafe\b|\bfood handler['’]?s?\b|\bhaccp\b|\bsqf\b|\bbrcgs?\b|\bfood hygiene\b"),
    ("Visual merchandising", r"\bvisual merchandising\b|\bplanograms?\b|\bstore displays?\b|\bmerchandising standards\b"),
    # teaching
    ("Instructional design", r"\binstructional design\b|\baddie\b|\blearning design\b|\bcurriculum (?:design|development)\b|\bblended learning\b|\be-?learning (?:design|development|modules|courses|content)\b"),
    ("LMS", r"\blearning management systems?\b|\blms (?:platforms?|administration|content|tools?)\b|\bmoodle\b|\bdocebo\b|\btalentlms\b|\bcornerstone ondemand\b|\bworkday learning\b"),
    ("Articulate 360", r"\barticulate(?: 360| storyline| rise)\b|\bstoryline 360\b|\badobe captivate\b|\bcamtasia\b|\bscorm\b"),
    # broad skills last: when a posting names more than MAX_TAGS, these are the ones left out, and job cards show the first three
    ("CRM", r"\bcrms?\b|\bcustomer relationship management\b"), ("Project management", r"\bproject management\b|\bproject planning\b|\bgantt\b"),
    ("Prospecting", r"\bprospecting\b|\blead generation\b|\boutbound sales\b"), ("Customer service", r"\bcustomer service\b"),
    ("Root cause analysis", r"\broot[- ]cause analysis\b|\brca\b|\b8d\b(?= problem|,| reports?| methodology)|\b5 whys\b|\bishikawa\b|\bfishbone\b|\bcapa\b"),
    ("Risk management", r"\brisk management\b|\brisk models?\b|\bmarket risk\b|\bcredit risk\b|\bvar\b(?= models?|,| and| calculations?)|\bvalue at risk\b"),
    ("Microsoft Office", r"\b(?:microsoft|ms) office\b|\bms office\b|\boffice suite\b|\bmicrosoft (?:word|excel|powerpoint|outlook)\b"),
    ("Statistics", r"\bstatistical (?:analysis|modell?ing|methods|techniques|inference|significance|tests|testing|models|programming)\b|\bstatistics\b"),
    ("Change management", r"\bchange management\b|\borgani[sz]ational change\b|\bprosci\b|\badkar\b"),
    ("Test automation", r"\btest automation\b|\bautomated (?:testing|tests|test suites?)\b|\bautomation testing\b|\btest frameworks?\b"),
    ("Cold calling", r"\bcold[- ]call(?:s|ing)?\b|\bcold outreach\b|\bcold email(?:s|ing)?\b"), ("Data visualization", r"\bdata visuali[sz]ations?\b|\bdata viz\b|\bvisuali[sz]ing data\b"),
    ("Spreadsheets", r"\bspreadsheets?\b"), ("Bilingual", r"\bbilingual\b"), ("Unit testing", r"\bunit test(?:s|ing)?\b"),
    ("Patient care", r"\bpatient care\b|\bdirect care\b|\bbedside\b|\bpatient education\b|\bcare coordination\b|\bcare plans?\b|\bdischarge planning\b"),
]
TITLE_ONLY = {"DeFi", "NFT", "Trading", "AML/KYC", "AI", "iOS", "Android", "Salesforce", "Blockchain", "Web3"}  # too common in company boilerplate
MAX_TAGS = 25       # was 12 with 113 skills; with 700 and more a long posting names more, and the first ones in SKILLS are kept

# Skill matching, fast and exact. Every run checks some 40,000 postings against every skill; one re.search per skill per posting
# took about 0.2 s a posting with 500 skills. Two shortcuts give exactly the same answers some ten times faster:
# - needles: plain strings read from the pattern itself, one of which every match contains ("kafka" for r"\bkafka\b"). When none
#   of them is in the lower-cased posting, the pattern cannot match and is not run;
# - windows: a pattern whose matches are at most w characters long, with lookarounds of at most a, is run only on the
#   characters around each needle found, not on the whole posting.
try:
    from re import _parser as _rp, _constants as _rc
except ImportError:                                 # Python before 3.11
    import sre_parse as _rp, sre_constants as _rc
_KNOWN = {_rc.LITERAL, _rc.NOT_LITERAL, _rc.ANY, _rc.IN, _rc.AT, _rc.SUBPATTERN, _rc.BRANCH, _rc.MAX_REPEAT, _rc.MIN_REPEAT, _rc.ASSERT, _rc.ASSERT_NOT}


def _needles(items):
    """A set of lower-case strings at least one of which is in every match of this parsed pattern; None when it cannot be told."""
    key = lambda s: (min(4, min(map(len, s))), -len(s))         # four letters are rare enough; then the fewer the better
    best, run = None, ""
    pick = lambda a, b: b if a is None or (b is not None and key(b) > key(a)) else a
    for op, av in items:
        if op is _rc.LITERAL:
            run += chr(av).lower(); continue
        alts = av[1] if op is _rc.BRANCH else av[-1][0][1][1] if op is _rc.SUBPATTERN and av[-1] and av[-1][0][0] is _rc.BRANCH else None
        if run and alts:                            # "c(?:pa|ertified)": the start the parser took out of the alternatives goes back in
            lead = []
            for a in alts:
                s = ""
                for op2, av2 in a:
                    if op2 is not _rc.LITERAL: break
                    s += chr(av2).lower()
                lead.append(run + s)
            if min(map(len, lead)) >= 3: best = pick(best, set(lead))
        if len(run) >= 2: best = pick(best, {run})
        run = ""
        if op is _rc.SUBPATTERN: best = pick(best, _needles(av[-1]))
        elif op is _rc.BRANCH:
            got = [_needles(a) for a in av[1]]
            if all(got): best = pick(best, set().union(*got))
        elif op in (_rc.MAX_REPEAT, _rc.MIN_REPEAT) and av[0] >= 1: best = pick(best, _needles(av[2]))
    return pick(best, {run}) if len(run) >= 2 else best


def _reach(items):
    """How far past a position the lookarounds of this pattern can look (None when unbounded or when the pattern has a construct
    this does not know)."""
    out = 0
    for op, av in items:
        if op not in _KNOWN: return None
        subs = [av[1]] if op in (_rc.ASSERT, _rc.ASSERT_NOT) else [av[-1]] if op is _rc.SUBPATTERN else av[1] if op is _rc.BRANCH else [av[2]] if op in (_rc.MAX_REPEAT, _rc.MIN_REPEAT) else []
        for s in subs:
            inner = _reach(s)
            if inner is None: return None
            if op in (_rc.ASSERT, _rc.ASSERT_NOT): inner += s.getwidth()[1]
            out = max(out, inner)
    return out if out <= 500 else None


class _Skill:
    def __init__(self, name, rx):
        self.name, self.title_only = name, name in TITLE_ONLY
        self.own = re.compile(r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])")   # the company's own name, as a whole word
        self.low = not re.search(r"(?<!\\)[A-Z]|\(\?-i", rx)   # no capital letter and no case-sensitive part: run on the lower-cased text
        self.rx = re.compile(rx) if self.low else re.compile(rx, re.I)
        tree = _rp.parse(rx, re.I)
        self.needles, w, a = _needles(tree), tree.getwidth()[1], _reach(tree)
        self.win = (w, a) if self.low and self.needles and w <= 500 and a is not None else None

    def found(self, text, low):
        if self.needles is None: return bool(self.rx.search(low if self.low else text))
        if self.win is None: return any(x in low for x in self.needles) and bool(self.rx.search(low if self.low else text))
        (w, a), n, search = self.win, len(low), self.rx.search
        for x in self.needles:
            i, k = low.find(x), 0
            while i >= 0:
                m = search(low, max(0, i + len(x) - w), min(n, i + w + a + 1))
                if m and m.start() <= i: return True       # a match that holds this needle; one starting later is checked at its own needle
                k += 1
                if k > 40: return bool(search(low))      # a needle this common: one search of the whole text is cheaper
                i = low.find(x, i + 1)
        return False


_SKILL_M = [_Skill(n, rx) for n, rx in SKILLS]


# What a posting says that is not about the work (data teardown, 26 Nov 2026: 10 of 91 open jobs showed a skill they do not ask for):
# e-mail and web addresses (".NET" from "MemorialTalent@mhs.net") and the equal-opportunity paragraph ("WCAG" from "an ADA compliant
# agency") are left out before the skills are read.
NOT_WORK = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\bhttps?://\S+|\bwww\.\S+", re.I)
EEO = re.compile(r"\bequal (?:employment )?opportunit|\baffirmative action\b|\breasonable accommodations?\b|\bwithout regard to\b|\bamericans with disabilities\b|"
                 r"\bada compliant\b|\be-?verify\b|\bdrug[- ]free workplace\b", re.I)
EEO_KEYS = ("opportunit", "affirmative", "accommodat", "without regard", "disabilities", "ada compliant", "verify", "drug")
SENTENCE = re.compile(r"(?<=[.!?\n])\s+")
EEO_NEAR = re.compile(r"[^.!?\n]{0,150}(?:" + EEO.pattern + r")[^.!?\n]{0,150}", re.I)


def work_text(blob):
    """The posting without its addresses and the sentences of its equal-opportunity paragraph."""
    blob = NOT_WORK.sub(" ", blob or "")
    low = blob.lower()
    if not any(k in low for k in EEO_KEYS): return blob
    out = []
    for x in SENTENCE.split(blob):                     # a long run without full stops loses only the words around the statement
        if not EEO.search(x): out.append(x)
        elif len(x) > 400: out.append(EEO_NEAR.sub(" ", x))
    return " ".join(out)
# Skills a kind of work does not use, whatever its text says: a nurse's "PHP" is a partial hospitalization program, a medical assistant's
# "Soldering" a word in the clinic's list of duties, a software engineer's "Accounts payable" the product's own advertising.
CLINICAL_TITLE = re.compile(r"\b(?:nurs\w*|rn|lpn|lvn|cna|medical assistant|patient|clinical|clinician|physician|therap\w*|dental|dentist|pharmac\w*|caregiver|"
                            r"phlebotom\w*|surgical|sonograph\w*|radiolog\w*|counsel+or|psychiatr\w*|psycholog\w*|social worker|home health|hospice|behavior technician|"
                            r"direct support|dsp|medication|med tech|respiratory|paramedic|emt|midwife|doula|optometr\w*|veterinar\w*|vet tech)\b", re.I)
TECH_ONLY = {"PHP", "Soldering", "Hardware testing", "Control systems", "Flutter", "Go", "CSS", "HTML", ".NET", "BGP", "Low voltage", "WCAG", "Rust", "Ruby", "Scala",
             "Elixir", "Slack", "Firmware", "Mechatronics", "Robotics", "Reconciliations", "Accounts payable", "Workday", "Data quality"}
SOFTWARE_TITLE = re.compile(r"\b(?:software|full[- ]?stack|back[- ]?end|front[- ]?end|web|mobile|ios|android|devops|platform|data|ml|machine learning|site reliability|sre)\b.*"
                            r"\b(?:engineer|developer|programmer|architect)s?\b|\b(?:developer|programmer)\b", re.I)
NOT_SOFTWARE = {"Accounts payable", "Reconciliations", "Soldering", "Low voltage", "Hazmat", "Forklift", "Cash handling"}


def tags_of(title, blob, company):
    """The skills a posting names, in the order of SKILLS, at most MAX_TAGS. A company's own name in its postings is not a skill
    ("Gong" at Gong), and it is a whole word: the letter C inside "Coinbase" no longer hides the skill C, nor "go" in "Google" Go."""
    blob = work_text(blob)
    drop = TECH_ONLY if CLINICAL_TITLE.search(title or "") else NOT_SOFTWARE if SOFTWARE_TITLE.search(title or "") else ()
    co, out, tl, bl = company.lower(), [], title.lower(), blob.lower()
    for s in _SKILL_M:
        if s.name in drop: continue
        if s.found(*((title, tl) if s.title_only else (blob, bl))) and not s.own.search(co):
            out.append(s.name)
            if len(out) == MAX_TAGS: break
    return out


# the data teardown's false skills (26 Nov 2026), each from the text that gave it: none of them may come back
for _t, _b, _no in (("Policy Analyst Supervisor", "Policy Analyst, MPLS FRB. Supervises analysts.", "BGP"),
                    ("Dentist - Kenai Alaska", "We are an equal opportunity employer and an ADA compliant agency.", "WCAG"),
                    ("Medication Technician (Med Tech)", "Respond to fire alarms, evacuations and emergencies.", "Low voltage"),
                    ("SOS Operations Manager", "Track rework, scrap and on-time delivery.", "Soldering"),
                    ("Senior Software Engineer - Robotic Controls", "Model friction, cogging, stiffness, slack and backlash in actuators.", "Slack"),
                    ("Loads & Dynamics Engineering Intern", "Analyse aeroelastic effects such as flutter and buffet.", "Flutter"),
                    ("Physical Therapy Assistant (PT) - Days", "Send your resume to MemorialTalent@mhs.net today.", ".NET"),
                    ("Physical Therapy Assistant (PT) - Days", "Dispose of bio hazardous waste.", "Hazmat"),
                    ("Insurance Follow Up Representative", "Department: CSS-Patient Accounting", "CSS"),
                    ("Software Engineer, Full-Stack", "Experience with Git or other version control systems.", "Control systems"),
                    ("Software Engineer, Full-Stack", "Our AI agents automate invoice processing for finance teams.", "Accounts payable"),
                    ("Registered Nurse", "Our PHP and IOP programs serve adolescents.", "PHP"),
                    ("Registered Nurse - ICU", "Complete medication reconciliation at admission.", "Reconciliations"),
                    ("Nurse Extern", "Apply on Workday. Create your Workday candidate profile.", "Workday")):
    assert _no not in tags_of(_t, _t + "\n" + _b, "Acme"), (_t, _no, tags_of(_t, _t + "\n" + _b, "Acme"))
for _t, _b, _yes in (("Network Engineer", "Configure BGP and OSPF on MPLS networks.", "BGP"), ("Frontend Engineer", "Build accessible UIs to WCAG 2.1 AA.", "WCAG"),
                     ("Mobile Engineer", "Ship our Flutter app on iOS and Android with Dart.", "Flutter"), ("Backend Engineer", "Services in C# on ASP.NET Core.", ".NET"),
                     ("Operations Coordinator", "Tools: Jira, Confluence and Slack.", "Slack"), ("HRIS Analyst", "Hands-on Workday HCM configuration.", "Workday"),
                     ("Controls Engineer", "Design control systems and PID loops.", "Control systems"), ("Electronics Technician", "Through-hole and SMT soldering.", "Soldering"),
                     ("Web Developer", "HTML, CSS and JavaScript.", "CSS"), ("Accounts Payable Specialist", "Process invoices; accounts payable experience.", "Accounts payable")):
    assert _yes in tags_of(_t, _t + "\n" + _b, "Acme"), (_t, _yes, tags_of(_t, _t + "\n" + _b, "Acme"))
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
    if got != OTHER[0] or not dept: got_ = got
    else: got_ = next((slug for slug, rx in DEPT_CATS if re.search(rx, dept, re.I)), OTHER[0])
    if got_ != OTHER[0]: return got_
    return next((slug for slug, name, rx in CATS_LATE if re.search(rx, title, re.I)), OTHER[0])


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
# "Hiring Range", "Pay Details", "Pay Band", "Pay Rate", "starting pay" (data teardown, 26 Nov 2026: 12 of 44 postings that state pay
# in their text showed "Not listed", 8 of them by the hour)
PAY_CTX = re.compile(r"salary|compensation|pay range|base pay|pay scale|base range|annual base|\bpay\b|\bOTE\b|on[- ]target earnings|wage|hiring range|pay band|"
                     r"pay rate|rate of pay|hourly rate|starting (?:at|rate)|\bearn\b", re.I)
PAY_NOT_YEARLY = re.compile(r"per hour|an hour|/ ?hour|hourly|/ ?hr\b|per month|a month|/ ?month|monthly|per day|/ ?day|daily|per week|weekly", re.I)
_HR = r"\d{1,3}(?:\.\d{1,2})?"
_HR_UNIT = r"\s*(?:usd\s*)?(?:/\s*(?:hour|hr|h)\b|per\s+(?:hour|hr)\b|an\s+hour\b|a\s+hour\b|hourly\b|p/h\b|/hr\b)"
# an hourly range or rate: "$20.00-$23.00 Hourly", "$18.00/hr – $21", "$30 - $50/hr", "USD $19.17/hr", "$156.00/hour"
PAY_HR = re.compile(rf"(US\$|\$|USD\s?\$?)\s?({_HR})(?:{_HR_UNIT})?\s*(?:-|–|—|to)\s*(?:US\$|\$|USD\s?\$?)?\s?({_HR})(?!\d|,\d|\s?[kK]\b)({_HR_UNIT})?|(US\$|\$|USD\s?\$?)\s?({_HR})(?!\d|,\d|\s?[kK]\b)({_HR_UNIT})?", re.I)
# what a small dollar amount near pay words is when it is not a wage: a bonus, a stipend, a discount, a sum per month or per year
PAY_HR_NOT = re.compile(r"^\s*(?:\+|plus\b|k\b|,\d|million|billion|bn\b|m\b|in\b|of\b|off\b|bonus|sign|stipend|allowance|gift|referral|credit|reimburs|discount|"
                        r"per (?:month|week|day|year|mile|visit|session|shift|diem|unit|case|delivery)|a (?:month|week|day|year)|/ ?(?:month|mo|week|wk|day|year|yr|mile)\b|"
                        r"monthly|weekly|daily|annual|yearly|tips?\b|toward|towards|match|fee|deposit|cash)", re.I)
PAY_HR_BEFORE_NOT = re.compile(r"(?:bonus|stipend|allowance|referral|reimburs\w*|up to|discount|credit|fee|tuition|deposit|gift card|incentive|differential|premium|shift diff\w*)\W{0,12}$", re.I)
PAY_MINMAX = re.compile(rf"\bmin(?:imum)?\b\W{{0,12}}(?:usd\s*)?({_CUR})\s?(\d{{2,3}}(?:,\d{{3}})+(?:\.\d+)?)[^$€£]{{0,60}}?\bmax(?:imum)?\b\W{{0,12}}(?:usd\s*)?(?:{_CUR})?\s?(\d{{2,3}}(?:,\d{{3}})+(?:\.\d+)?)", re.I)
PAY_ONE = re.compile(rf"({_CUR})\s?(\d{{2,3}},\d{{3}}(?:\.\d{{2}})?)(?!,?\d)(?!\s?(?:-|–|—|to)\s?(?:{_CUR})?\s?\d)\s?(USD|CAD|AUD|GBP|EUR)?", re.I)
PAY_ONE_NOT = re.compile(r"^\s*(?:\+|plus|bonus|sign|relocation|stipend|tuition|401|match|revenue|billion|million|in (?:funding|revenue|sales|assets)|per (?:month|week)|a month|monthly|"
                         r"/ ?mo\b|toward|of (?:funding|revenue)|signing|referral|annual bonus|budget|grant|award|loan|in )", re.I)


def pay_k(sym, lo, hi):
    return f"{sym}{lo / 1000:,.0f}K - {sym}{hi / 1000:,.0f}K"


def _cents(v):
    return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"


def _sym_for(sym, tail, location):
    """The currency of a bare dollar sign: the local dollar outside the US; None where it cannot be told."""
    if sym == "$" and tail in ("CAD", "AUD"): sym = PAY_SYM[tail]
    if sym == "$":                                       # a bare dollar sign outside the US is usually the local dollar
        if re.search(r"canada|toronto|vancouver|montr[eé]al|ontario|ottawa|calgary|waterloo|, ?(?:ON|BC|QC|AB|MB|SK|NS|NB)\b", location, re.I): sym = "CA$"
        elif re.search(r"australia|sydney|melbourne|brisbane", location, re.I): sym = "A$"
        elif re.search(r"singapore|hong kong|new zealand|auckland|mexico|philippines|argentina|colombia|chile|taiwan", location, re.I): return None
    return sym


def pay_from_text(text, location=""):
    """The pay written in the posting's own text, or "": a yearly range ("The salary range for this role is $180,000 - $240,000"),
    a yearly minimum and maximum ("Pay Band Min USD $86,450 ... Max USD $..."), a yearly figure ("Salary: $38,328.16"), then an
    hourly range or rate in US dollars ("$20.00-$23.00 Hourly", "Pay Rate: USD $19.54", "starting base pay ... is $17.00 per hour").
    Strict: the figure must sit next to a word about pay and look like one person's wage."""
    text = text or ""
    for m in PAY_RNG.finditer(text):
        # the 30 characters before the range ("hourly rate: $"), not 50: "In-Office Lunch (5 days per week) Compensation Base salary: $82,000 -
        # $107,000" is a yearly range
        if not PAY_CTX.search(text[max(0, m.start() - 220):m.end() + 60]) or PAY_NOT_YEARLY.search(text[max(0, m.start() - 30):m.start()] + text[m.end():m.end() + 40]):
            continue
        num = lambda s: float(re.sub(r"[kK\s,]", "", s)) * (1000 if s.strip()[-1] in "kK" else 1)
        lo, hi = num(m.group(2)), num(m.group(3))
        if not (20000 <= lo <= hi <= 2000000 and hi <= 4 * lo): continue
        sym = _sym_for(PAY_SYM[m.group(1).upper()], (m.group(4) or "").strip().upper(), location)
        if sym: return pay_k(sym, lo, hi)
    for m in PAY_MINMAX.finditer(text):
        if not PAY_CTX.search(text[max(0, m.start() - 160):m.start() + 20]): continue
        lo, hi = float(m.group(2).replace(",", "")), float(m.group(3).replace(",", ""))
        sym = _sym_for(PAY_SYM.get(m.group(1).upper(), "$"), "", location)
        if sym and 20000 <= lo <= hi <= 900000 and hi <= 3 * lo: return pay_k(sym, lo, hi)
    for m in PAY_ONE.finditer(text):
        before, after = text[max(0, m.start() - 70):m.start()], text[m.end():m.end() + 30]
        if not PAY_CTX.search(before) or PAY_HR_BEFORE_NOT.search(before) or PAY_ONE_NOT.search(after) or PAY_NOT_YEARLY.search(after[:20]): continue
        if re.search(r"\d\s*(?:-|–|—|to)\s*$", before): continue            # the top of a range the rules above did not take
        v = float(m.group(2).replace(",", ""))
        sym = _sym_for(PAY_SYM[m.group(1).upper()], (m.group(3) or "").strip().upper(), location)
        if sym and 20000 <= v <= 900000: return f"{sym}{v / 1000:,.0f}K"
    for m in PAY_HR.finditer(text):
        rng = m.group(2) is not None
        lo = float(m.group(2) if rng else m.group(6)); hi = float(m.group(3)) if rng else lo
        unit = (m.group(4) if rng else m.group(7)) or (re.search(_HR_UNIT, text[m.start():m.start() + 40], re.I) and "hour" if rng else None)
        before, after = text[max(0, m.start() - 90):m.start()], text[m.end():m.end() + 30]
        if PAY_HR_BEFORE_NOT.search(before) or (not unit and PAY_HR_NOT.search(after)) or re.match(r"\s*(?:k\b|,\d{3})", after): continue
        # without "an hour" written, a dollar figure with cents or under $150 right after a word about pay is a wage by the hour
        if not unit and not (PAY_CTX.search(before[-70:]) and (("." in m.group(0)) or hi <= 150) and re.search(r"\bpay\b|wage|rate|hourly|compensation|salary|range|earn", before[-70:], re.I)):
            continue
        if not unit and re.search(r"\b(?:salary|annual|per year|a year|yearly)\b", before[-40:], re.I): continue
        if not (7 <= lo <= hi <= 500 and hi <= 3 * lo): continue
        if re.search(r"canada|australia|new zealand|mexico|philippines|singapore|hong kong|, ?(?:ON|BC|QC|AB)\b", location, re.I) and "US" not in m.group(0).upper(): continue
        return f"${_cents(lo)} - ${_cents(hi)} an hour" if hi > lo else f"${_cents(lo)} an hour"
    return ""


for _t, _w in (("Salary Range: USD $19.17/hr The salary range above reflects", "$19.17 an hour"), ("Pay Details: $25.75 - $38.50 per hour", "$25.75 - $38.50 an hour"),
               ("Hours: 40 Pay Details: $25.75 - $38.50 The pay", "$25.75 - $38.50 an hour"), ("Compensation Range: $38.05- $75", "$38.05 - $75 an hour"),
               ("Denver, CO Pay Rate: USD $19.54 The salary range above reflects", "$19.54 an hour"), ("Starting pay range is $30 - $50/hr", "$30 - $50 an hour"),
               ("The anticipated starting base pay for this position is $17.00 per hour.", "$17 an hour"), ("The pay range for this role is $18.00/hr – $21.00/hr", "$18 - $21 an hour"),
               ("Pay: $20.00-$23.00 Hourly", "$20 - $23 an hour"), ("Rate: $156.00/hour", "$156 an hour"), ("Annual Salary: $38,328.16", "$38K"),
               ("Pay Band Min USD $86,450 Max USD $129,700", "$86K - $130K"), ("The salary range for this role is $180,000 - $240,000.", "$180K - $240K"),
               ("We offer a $500 sign-on bonus and competitive pay", ""), ("Paid volunteer hours & charity donation matching up to $2000/year", ""),
               ("revenues of more than $3 billion", ""), ("A $100 referral bonus. Competitive pay.", ""), ("Pay: $25 gift card for applying", ""),
               ("Shift differential: $2.00 per hour for nights", ""), ("Salary: competitive. Raised $25,000,000 in funding", ""),
               ("Base pay for this role is $55,000 CAD per year", "CA$55K"), ("In-Office Lunch (5 days per week) Compensation Base salary: $82,000 - $107,000 (before equity)", "$82K - $107K"),
               ("Hourly rate: $95,000 - $120,000", "")):
    assert pay_from_text(_t) == _w, (_t, pay_from_text(_t), _w)
assert pay_from_text("Hiring Range: $55,062.53 – $68,828.16", "Waterloo, Ontario, Canada") == "CA$55K - CA$69K"


def pay_from_greenhouse(ranges, location=""):
    """Greenhouse's structured pay ranges (several zones are merged into one overall range). A posting with a US and a Canadian range
    shows the one of its place: a New York role read "CA$140K - CA$220K" because the Canadian range came first (data teardown, 26 Nov 2026)."""
    ok = [r for r in (ranges or []) if isinstance(r, dict) and r.get("min_cents") and r.get("max_cents")]
    if not ok: return ""
    curs = [(r.get("currency_type") or "USD").upper() for r in ok]
    canada = bool(re.search(r"canada|toronto|vancouver|montr[eé]al|ontario|ottawa|calgary|, ?(?:ON|BC|QC|AB)\b", location or "", re.I))
    cur = "CAD" if canada and "CAD" in curs else "USD" if "USD" in curs and not canada else ok[0].get("currency_type") or "USD"
    same = [r for r in ok if (r.get("currency_type") or "USD").upper() == cur.upper()]
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


# A posting the hiring system marks remote that says in its own text that it is hybrid (data teardown, 26 Nov 2026: 4 of 17 "remote" jobs
# opened, e.g. "This is a hybrid role requiring Tuesdays and Thursdays in-office in Fenton, Missouri"). Only an obligation to be in the
# office counts: "hybrid cloud", "a remote or hybrid role" and an office the company also has do not.
HYBRID_TEXT = re.compile(
    r"\bthis (?:is an? |role is an? |position is an? |job is an? )hybrid (?:role|position|job|opportunity|schedule)\b|\bhybrid (?:schedule|work schedule|work model|working model|"
    r"work arrangement|work environment|working environment)\b(?!s? (?:for|across) (?:some|other|many|most) )|\bhybrid\s*[-–:]\s*on-?site\b|\b(?:\d|one|two|three|four)\s*\+?\s*days? "
    r"(?:a|per|each|every) week (?:in|at|on)[- ](?:the |our )?(?:office|site|person|campus|location)\b|\b(?:minimum|at least) (?:of )?(?:\d|one|two|three|four) days? "
    r"(?:a week |per week |weekly |each week )?(?:in|at|on)[- ](?:the |our )?(?:office|site)\b|\b(?:\d|one|two|three|four) days? in[- ](?:the[- ])?office\b|\bmandatory in[- ]office\b|"
    r"\bin[- ]office (?:days|requirement|attendance|presence)\b|(?-i:#?\bLI-Hybrid\b)|\b(?:mondays?|tuesdays?|wednesdays?|thursdays?|fridays?)\b[^.]{0,40}\bin[- ](?:the[- ])?office\b", re.I)
FULLY_REMOTE = re.compile(r"\b(?:fully|100%|completely|entirely|permanently) remote\b|\bremote[- ]first\b|\bno (?:office|in-office) (?:attendance|requirement)", re.I)


def says_hybrid(text):
    """Does the text of a posting ask for days in the office?"""
    return bool(text) and bool(HYBRID_TEXT.search(text)) and not FULLY_REMOTE.search(text)


for _t in ("This is a hybrid role requiring Tuesdays and Thursdays in-office in Fenton, Missouri.", "Tuesdays, Wednesdays, and Thursdays being mandatory in-office days",
           "Location: Hybrid - Onsite minimum of 2 days a week", "We offer a hybrid work environment, a flexible work schedule. #LI-Hybrid"):
    assert says_hybrid(_t), _t
for _t in ("Support our Companies in a remote or hybrid role.", "Experience with hybrid cloud environments.", "This role is fully remote; our offices use a hybrid work model.", ""):
    assert not says_hybrid(_t), _t


def norm(company, ats, jid, title, url, location, remote, dept, posted, text, salary="", hint="", desc="", hybrid=False, posted_at=None):
    title = re.sub(r"\s+", " ", str(title or "")).strip()
    location = re.sub(r"\s+", " ", str(location or "")).strip()
    hybrid = bool(hybrid) or bool(re.search(r"\bhybrid\b", location, re.I))
    remote = (bool(remote) or bool(re.search(r"\bremote\b", location, re.I))) and not (hybrid and not re.search(r"\bremote\b", location, re.I))
    if remote and says_hybrid(text): remote, hybrid = False, True
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
        "tags": tags_of(title, blob, company),
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


def raw_hash(raw):
    """The fingerprint of the feed's entry alone, without the rules: it changes only when the employer changes the posting."""
    return hashlib.md5(json.dumps(raw, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:12]


REREAD = os.environ.get("HRN_REREAD") == "1"        # read the text of every Workday and SmartRecruiters posting again, whatever the record holds


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
        asked, wait = 0, []
        for p in posts:
            jid, raw = ident(p), raw_of(p)
            full_id = f"{ats}-{slugify(name)}-{jid}"
            if reuse and (rec := reuse(full_id, fingerprint(raw))) is not None:
                out.append(rec); continue
            old, rh = (reuse(full_id) if reuse else None), raw_hash(raw)
            # The feed says about this posting what it said when its text was read ("rh", the fingerprint of the feed's entry alone), and
            # only the rules of this file changed: the record is kept as it is. Reading it again costs a request, and after every edit of
            # this file that was a request for every posting of every Workday board (on 18 Nov 2026 a run spent over 20 minutes on it).
            # A record made before "rh" existed is taken as unchanged once. HRN_REREAD=1 reads everything again.
            if old is not None and old.get("rh", rh) == rh and not REREAD:
                old["rh"] = rh; out.append(old); continue
            wait.append((old is not None, p, jid, raw, full_id, rh))
        # Postings the record has never held are read first (the backlog of a board just added), then those whose entry in the feed
        # changed. Before 18 Nov 2026 the order was simply newest first. The sort is stable: newest first in each.
        for _, p, jid, raw, full_id, rh in sorted(wait, key=lambda w: w[0]):
            rec = None
            if asked < DETAILS:
                asked += 1
                rec = read(p, jid)
                if rec is not None: rec["h"], rec["rh"] = fingerprint(raw), rh
            if rec is None and reuse: rec = reuse(full_id)
            if rec is not None: out.append(rec)

    if ats == "greenhouse":
        d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true&pay_transparency=true", 60)
        if not d or "jobs" not in d: return name, None
        for j in d["jobs"]:
            dept = ", ".join(x.get("name", "") for x in (j.get("departments") or []))
            add(j["id"], j, lambda: parse(name, ats, j["id"], j.get("title"), j.get("absolute_url"), (j.get("location") or {}).get("name"),
                                         False, dept, j.get("first_published") or j.get("updated_at"), strip_html(j.get("content")), pay_from_greenhouse(j.get("pay_input_ranges"), (j.get("location") or {}).get("name") or ""), "", html.unescape(j.get("content") or ""),
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


def direct_desc(text):
    """The description an employer typed in the account (plain text), as paragraphs for the job page."""
    return "".join(f"<p>{html.escape(p_.strip())}</p>" for p_ in str(text or "").split("\n") if p_.strip())


# >>> not rules (jobs posted in the account, placements, and the run itself: to the end of the file)
# US federal jobs (19 Nov 2026, the owner: "find more jobs; I think USAJOBS has an open API"). USAJOBS is the federal government's own
# hiring site, so a federal job read from it is read from the employer, as everywhere else on this site. Its Historic JOA endpoint
# needs no key and its robots.txt allows it; it gives every announcement with its dates, pay, places and schedule, but not the text,
# so the record's text is written from those fields. One board per department (sources_gov.json, "token": the department code); an
# announcement counts while USAJOBS says it is accepting applications and its closing date has not passed.
USAJOBS = "https://data.usajobs.gov"
USAJOBS_JUNK = re.compile(r"\btest\b.*\b(?:expire|reminder|ignore)\b|do not apply|don.t apply", re.I)


def gov_title(t):
    """Many announcements are titled in capitals ("AIRCRAFT ENGINE MECHANIC (Title 32)"): capitalised normally, short words and
    known abbreviations kept."""
    t = re.sub(r"\s+", " ", t or "").strip()
    if sum(c.isupper() for c in t) < 0.6 * max(1, sum(c.isalpha() for c in t)): return t
    small = {"of", "and", "or", "the", "for", "in", "on", "at", "to", "a", "an", "with"}
    keep = {"IT", "HR", "US", "U.S.", "VA", "DOD", "GS", "WG", "RN", "LPN", "EMT", "ICU", "OR", "ER", "TSA", "FBI", "IRS", "NASA", "II", "III", "IV", "MD", "PA", "NP"}
    out = []
    for i, w in enumerate(t.split(" ")):
        core = w.strip("()[],/-")
        if core.upper() in keep: out.append(w.upper() if core.isalpha() else w)
        elif i and core.lower() in small: out.append(w.lower())
        else: out.append("-".join(x[:1].upper() + x[1:].lower() for x in w.split("-")))
    return " ".join(out)


def fetch_usajobs(src, reuse=None):
    name, tok = src["name"], src["token"]
    today = datetime.date.today().isoformat()
    url, rows, pages = f"{USAJOBS}/api/historicjoa?HiringDepartmentCodes={tok}&StartPositionCloseDate={today}", [], 0
    while url and pages < 60:
        polite("usajobs")
        d = get_json(url, 60)
        if not isinstance(d, dict) or not isinstance(d.get("data"), list): return name, None      # a failed page: the department stays as it was
        rows += d["data"]; pages += 1
        nxt = (d.get("paging") or {}).get("next")
        url = USAJOBS + nxt if nxt else None
    out = []
    for r in rows:
        if r.get("positionOpeningStatus") != "Accepting applications" or (r.get("positionCloseDate") or "") < today: continue
        title = gov_title(r.get("positionTitle"))
        if not title or USAJOBS_JUNK.search(title): continue
        jid = str(r.get("usajobsControlNumber") or "")
        if not jid: continue
        h = fingerprint({k: v for k, v in r.items() if k != "positionOpeningStatus"})
        rec = reuse(f"usajobs-{slugify(name)}-{jid}", h) if reuse else None
        if rec is None:
            locs = [", ".join(x for x in (l.get("positionLocationCity"), l.get("positionLocationState")) if x) or (l.get("positionLocationCountry") or "")
                    for l in (r.get("positionlocations") or [])]
            loc = "; ".join(dict.fromkeys(x for x in locs if x))[:300]
            per = (r.get("salaryType") or "").lower()
            lo, hi = r.get("minimumSalary"), r.get("maximumSalary")
            pay = ""
            if lo and hi and "hour" in per: pay = f"${lo:,.2f} – ${hi:,.2f} an hour"
            elif lo and hi and "year" in per and lo >= 10000: pay = f"${lo:,.0f} – ${hi:,.0f} a year"
            agency = (r.get("hiringAgencyName") or "").strip()
            paths = ", ".join(x.get("hiringPath") for x in (r.get("hiringpaths") or []) if x.get("hiringPath"))
            if not pay and paths in ("", "Custom announcement"): continue          # internal test and placeholder announcements ("PD Prod Deploy 0426")
            facts = [f"{agency}, {r.get('hiringDepartmentName') or name}." if agency else "",
                     f"{r.get('workSchedule') or ''} {(r.get('appointmentType') or '').lower()} position".strip().capitalize() + ".",
                     f"Pay grade {r.get('payScale')} {r.get('minimumGrade')}" + (f" to {r.get('maximumGrade')}" if r.get('maximumGrade') not in (None, r.get('minimumGrade')) else "") + "." if r.get("payScale") else "",
                     f"Open to: {paths}." if paths else "",
                     f"Security clearance: {r.get('securityClearance')}." if r.get("securityClearanceRequired") == "Y" and r.get("securityClearance") else "",
                     f"Travel: {r.get('travelRequirement')}." if r.get("travelRequirement") else "",
                     "Telework eligible." if r.get("teleworkEligible") == "Y" else "",
                     f"Openings: {r.get('totalOpenings')}." if str(r.get("totalOpenings") or "").isdigit() else "",
                     f"Applications close on {r.get('positionCloseDate')}. The full announcement, duties and how to apply are on USAJOBS, the federal government's hiring site."]
            text = " ".join(x for x in facts if x)
            # the agency goes into the text, not the department field: words such as "Revenue" in an agency's name would steer the category
            rec = parse(name, "usajobs", jid, title, f"https://www.usajobs.gov/job/{jid}", loc, False, "", r.get("positionOpenDate") or "", text, pay,
                        f"{r.get('workSchedule') or ''} {r.get('appointmentType') or ''}", "<p>" + html.escape(text) + "</p>")
            if rec is None: continue
            rec["h"] = h
        out.append(rec)
    return name, out


# JazzHR (19 Nov 2026, the owner: "find more jobs"). Small and mid-sized US employers' own job boards, each at
# https://<company>.applytojob.com/apply (sources_jazz.json, "token": the subdomain; discover_jazz.py finds them). robots.txt of
# app.jazz.co and of every board allows everything but /cb to any crawler. A board is read the way its careers page shows it: the
# list page gives every open job with its address, title, place and department in one request (JazzHR's five sitemaps, which
# discover_jazz.py reads, miss some jobs and give a fifth of the rest under an older address that answers "410 Gone"). Each job
# new to the record costs one more request, its own page, for the text: the JobPosting data in it (date, type, pay, text) when
# the employer publishes it to search engines, else the page itself. At most DETAILS such pages per board in one read (120 here,
# 15 in live.py), postings the record has never held first; the rest wait for the next read, as on Workday.
import net as _net                        # noqa: E402  (net.get_text itself: discover_ats.py swaps collect.get_text for a cache)

JAZZ_JOB = re.compile(r"""https?://([a-z0-9-]+)\.applytojob\.com/apply/([A-Za-z0-9]{6,20})/([^"'?#<\s]*)""")
JAZZ_LD = re.compile(r"""<script[^>]*application/ld\+json[^>]*>(.*?)</script>""", re.S)
_jazz_skip = set()                         # postings found not in English since this process started (live.py): not asked for again


def jazz_list(page):
    """The jobs on a JazzHR board's list page: [(id, address, title, place, department)], or None when it is not a board's list."""
    if page and "This account is no longer active" in page: return []       # the company left JazzHR: its jobs are closed
    if not page or "resumator-jobboard" not in page: return None
    found = list(JAZZ_JOB.finditer(page))
    out, seen = [], set()
    for i, m in enumerate(found):
        jid = m.group(2)
        if jid in seen: continue
        end = found[i + 1].start() if i + 1 < len(found) else len(page)
        seg = page[m.end():end]
        seg = seg[:seg.find("</ul>")] if "</ul>" in seg else seg              # the job's own line of facts, not what follows the list
        t = re.match(r"""[^>]*>(.*?)</a>""", seg, re.S)
        title = html.unescape(re.sub(r"<[^>]+>|\s+", " ", t.group(1))).strip() if t else ""
        if not title: continue
        seen.add(jid)
        def field(icon):
            f = re.search(rf"""<i class=['"]fa {icon}['"]></i>([^<]*)""", seg)
            return re.sub(r"\s+", " ", html.unescape(f.group(1))).strip() if f else ""
        place = ", ".join(dict.fromkeys(p.strip() for p in field("fa-map-marker").split(",") if p.strip()))   # "Singapore, Singapore, Singapore"
        out.append((jid, f"https://{m.group(1)}.applytojob.com/apply/{jid}/{m.group(3)}", title, place, field("fa-sitemap")))
    return out


def jazz_page(page):
    """What a JazzHR job page says: its JobPosting data when it has some, else the description and attributes of the page itself."""
    for b in JAZZ_LD.findall(page or ""):
        try: d = json.loads(b, strict=False)
        except ValueError: continue
        if isinstance(d, dict) and d.get("@type") == "JobPosting" and d.get("description"): return d
    m = re.search(r"""id=["']job-description["'][^>]*>(.*?)(?:<div[^>]*resumator-mobile-apply-wrapper|<div[^>]*id=["']job-application-form-container)""", page or "", re.S)
    if not m: return {}
    def attr(name):
        a = re.search(rf"""title=["']{name}["'][^>]*>\s*(?:<i[^>]*></i>)?([^<]*)""", page)
        return re.sub(r"\s+", " ", html.unescape(a.group(1))).strip() if a else ""
    return {"description": re.sub(r"(?:\s*</div>)+\s*$", "", m.group(1)), "employmentType": attr("Type"), "department": attr("Department")}


def jazz_pay(d):
    """baseSalary of a JobPosting as text tidy_pay reads ("100000 - 120000 USD", "18 - 22 USD per hour"), or ""."""
    s = d.get("baseSalary") if isinstance(d.get("baseSalary"), dict) else {}
    v = s.get("value") if isinstance(s.get("value"), dict) else {"value": s.get("value")}
    try:
        lo, hi = float(v.get("minValue") or v.get("value") or 0), float(v.get("maxValue") or v.get("value") or 0)
    except (TypeError, ValueError):
        return ""
    if lo <= 0 or hi < lo: return ""
    num = lambda x: f"{x:.2f}" if x < 1000 else f"{x:.0f}"           # hourly pay keeps its cents
    return (f"{num(lo)} - {num(hi)}" if hi > lo else num(lo)) + f" {s.get('currency') or v.get('currency') or 'USD'}{per_unit(v.get('unitText'))}"


def fetch_jazzhr(src, reuse=None):
    name, tok = src["name"], src["token"]
    src["not_english"] = 0
    polite("jazzhr")
    jobs = jazz_list(_net.get_text(f"https://{tok}.applytojob.com/apply", 60, accept="text/html", compressed=True))
    if jobs is None: return name, None                     # no answer, or not a board: the company stays as it was
    out, wait = [], []
    for jid, url, title, place, dept in jobs:
        raw = {"url": url, "title": title, "place": place, "dept": dept}
        full_id = f"jazzhr-{slugify(name)}-{jid}"
        if reuse and (rec := reuse(full_id, fingerprint(raw))) is not None:
            out.append(rec); continue
        old, rh = (reuse(full_id) if reuse else None), raw_hash(raw)
        # unchanged on the list and only these rules changed: keep the record rather than ask for the page again (as on Workday)
        if old is not None and old.get("rh", rh) == rh and not REREAD:
            old["rh"] = rh; out.append(old); continue
        wait.append((old is not None, jid, url, title, place, dept, raw, rh, full_id))
    asked = 0
    for _, jid, url, title, place, dept, raw, rh, full_id in sorted(wait, key=lambda w: w[0]):
        rec = None
        if asked < DETAILS and full_id not in _jazz_skip:
            asked += 1
            polite("jazzhr")
            d = jazz_page(_net.get_text(url, 40, accept="text/html", compressed=True))
            desc = str(d.get("description") or "")
            if "<" not in desc and "&lt;" in desc: desc = html.unescape(desc)        # markup written as text inside the JSON
            text = strip_html(desc)
            if not d:
                pass                                       # gone since the list was read, or no answer: asked again next time
            elif not english(f"{title}\n{text}"):
                src["not_english"] += 1; _jazz_skip.add(full_id)
            else:
                lt = d.get("jobLocationType")
                remote = "TELECOMMUTE" in (lt if isinstance(lt, list) else [lt])
                if not place:                              # the list names no place: the JobPosting's addresses, if any
                    locs = d.get("jobLocation") if isinstance(d.get("jobLocation"), list) else [d.get("jobLocation")]
                    addrs = [l["address"] for l in locs if isinstance(l, dict) and isinstance(l.get("address"), dict)]
                    parts = [", ".join(str(a[k]).strip() for k in ("addressLocality", "addressRegion", "addressCountry") if str(a.get(k) or "").strip())
                             for a in addrs[:3]]
                    place = "; ".join(dict.fromkeys(p for p in parts if p))
                kind = d.get("employmentType")
                kind = " ".join(kind) if isinstance(kind, list) else str(kind or "")
                rec = parse(name, "jazzhr", jid, title, url, place, remote, dept or d.get("department") or "", str(d.get("datePosted") or "")[:10],
                            text, jazz_pay(d), kind, desc)
                if rec is not None: rec["h"], rec["rh"] = fingerprint(raw), rh
        if rec is None and reuse: rec = reuse(full_id)
        if rec is not None: out.append(rec)
    return name, out


def detail_board(src, reuse, ats, items, read):
    """A board whose list names its postings and whose text costs one request a posting (Breezy, BambooHR), read as fetch_jazzhr
    reads JazzHR: an unchanged posting keeps its record, at most DETAILS others are read (those the record has never held first),
    and the rest wait for the next read. items: [(id, what the list says of it)]; read(id, raw) gives the record, or None."""
    name, out, wait = src["name"], [], []
    src["not_english"] = 0
    for jid, raw in items:
        full_id = f"{ats}-{slugify(name)}-{jid}"
        if reuse and (rec := reuse(full_id, fingerprint(raw))) is not None:
            out.append(rec); continue
        old, rh = (reuse(full_id) if reuse else None), raw_hash(raw)
        if old is not None and old.get("rh", rh) == rh and not REREAD:
            old["rh"] = rh; out.append(old); continue
        wait.append((old is not None, jid, raw, rh, full_id))
    asked = 0
    for _, jid, raw, rh, full_id in sorted(wait, key=lambda w: w[0]):
        rec = None
        if asked < DETAILS and full_id not in _jazz_skip:
            asked += 1
            polite(ats)
            rec = read(jid, raw)
            if rec == "not english":
                src["not_english"] += 1; _jazz_skip.add(full_id); rec = None
            elif rec is not None:
                rec["h"], rec["rh"] = fingerprint(raw), rh
        if rec is None and reuse: rec = reuse(full_id)
        if rec is not None: out.append(rec)
    return name, out


# Breezy HR (https://<company>.breezy.hr, sources_breezy.json, "token": the subdomain; discover_ats.py finds them). /json is the list
# its careers page reads: every published position with its place, remote flag, type, date and pay. The text is on the position's
# own page, in the JobPosting data it publishes for search engines. robots.txt of a board (19 Nov 2026) keeps crawlers out of
# /css, /fonts, /stylesheets and /javascripts only.
def _nm(x):
    """A field Breezy gives either as {"name": ...} or as plain text."""
    return str((x.get("name") if isinstance(x, dict) else x) or "").strip()


def breezy_place(loc):
    loc = loc if isinstance(loc, dict) else {}
    parts = [_nm(loc.get("city")), _nm(loc.get("state")), _nm(loc.get("country"))]
    return ", ".join(dict.fromkeys(p for p in parts if p)) or str(loc.get("name") or "").strip()


def fetch_breezy(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("breezy")
    d = get_json(f"https://{tok}.breezy.hr/json", 60)
    if not isinstance(d, list): return name, None
    items = []
    for p in d:
        if not isinstance(p, dict) or not p.get("id") or not p.get("name") or not p.get("url"): continue
        locs = [l for l in (p.get("locations") or [p.get("location")]) if isinstance(l, dict)]
        rd = [str((l.get("remote_details") if isinstance(l.get("remote_details"), dict) else {}).get("value") or "") for l in locs]
        items.append((p["id"], {"url": p["url"], "title": p["name"], "place": "; ".join(dict.fromkeys(x for x in map(breezy_place, locs[:4]) if x)),
                                "remote": any(l.get("is_remote") for l in locs) and "hybrid" not in rd, "hybrid": "hybrid" in rd,
                                "type": _nm(p.get("type")), "dept": _nm(p.get("department")),
                                "posted": str(p.get("published_date") or ""), "pay": str(p.get("salary") or "")}))

    def read(jid, raw):
        d = jazz_page(_net.get_text(raw["url"], 40, accept="text/html", compressed=True))
        desc = str(d.get("description") or "")
        if not d or not desc: return None
        text = strip_html(desc)
        if not english(f"{raw['title']}\n{text}"): return "not english"
        # the day and the time from the same field: the list's published_date moves when a posting is published again, the page's
        # datePosted keeps the first day (teardown, 26 Nov 2026: a posting of 27 Feb read "3 h" from the list's time; build.exact)
        at = str(d.get("datePosted") or raw["posted"] or "")
        return parse(name, "breezy", jid, raw["title"], raw["url"], raw["place"], raw["remote"], raw["dept"], at[:10],
                     text, raw["pay"] or jazz_pay(d), raw["type"], desc, raw["hybrid"], posted_at=at or None)
    return detail_board(src, reuse, "breezy", items, read)


# BambooHR (https://<company>.bamboohr.com/careers, sources_bamboo.json, "token": the subdomain). /careers/list is the list its
# careers page reads; /careers/<id>/detail gives one opening with its text, date, pay and address. robots.txt of a board
# (19 Nov 2026): "Disallow:" with nothing after it, so everything may be read.
BAMBOO_TYPE = {"1": "remote", "2": "hybrid"}            # locationType of an opening; anything else is on site


def bamboo_place(loc, ats_loc=None):
    loc, al = (loc if isinstance(loc, dict) else {}), (ats_loc if isinstance(ats_loc, dict) else {})
    parts = [loc.get("city") or al.get("city"), loc.get("state") or al.get("state") or al.get("province"), loc.get("addressCountry") or al.get("country")]
    return ", ".join(dict.fromkeys(str(p).strip() for p in parts if p and str(p).strip()))


def fetch_bamboohr(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("bamboohr")
    d = get_json(f"https://{tok}.bamboohr.com/careers/list", 60)
    if not isinstance(d, dict) or not isinstance(d.get("result"), list): return name, None
    items = []
    for p in d["result"]:
        if not isinstance(p, dict) or not p.get("id") or not p.get("jobOpeningName"): continue
        kind = BAMBOO_TYPE.get(str(p.get("locationType") or ""), "")
        items.append((str(p["id"]), {"title": p["jobOpeningName"], "place": bamboo_place(p.get("location"), p.get("atsLocation")),
                                     "remote": bool(p.get("isRemote")) or kind == "remote", "hybrid": kind == "hybrid",
                                     "type": str(p.get("employmentStatusLabel") or ""), "dept": str(p.get("departmentLabel") or "")}))

    def read(jid, raw):
        x = (get_json(f"https://{tok}.bamboohr.com/careers/{jid}/detail", 40) or {}).get("result") or {}
        o = x.get("jobOpening") if isinstance(x, dict) else None
        if not isinstance(o, dict) or not o.get("description"): return None
        desc, url = str(o["description"]), str(o.get("jobOpeningShareUrl") or f"https://{tok}.bamboohr.com/careers/{jid}")
        text = strip_html(desc)
        if not english(f"{raw['title']}\n{text}"): return "not english"
        kind = BAMBOO_TYPE.get(str(o.get("locationType") or ""), "")
        return parse(name, "bamboohr", jid, raw["title"], url, bamboo_place(o.get("location"), o.get("atsLocation")) or raw["place"],
                     raw["remote"] or kind == "remote", raw["dept"], str(o.get("datePosted") or "")[:10], text, str(o.get("compensation") or "").strip(),
                     str(o.get("employmentStatusLabel") or raw["type"]), desc, raw["hybrid"] or kind == "hybrid")
    return detail_board(src, reuse, "bamboohr", items, read)


# Paylocity (https://recruiting.paylocity.com/recruiting/jobs/All/<company id>/<name>, sources_paylocity.json, "token": the company
# id, a GUID; discover_ats.py finds them in Common Crawl's index). The board's page carries its list in window.pageData: every open
# posting with its place, remote flag, department and date; internal postings (for the company's own staff) are left out. The text
# is on the posting's page (/Recruiting/Jobs/Details/<id>), in the JobPosting data it publishes for search engines.
# recruiting.paylocity.com has no robots.txt (20 Nov 2026: 404), so nothing is asked to stay out. IndeedRemoteType is 2 on nearly
# every posting, on site or not (a sample of 187 on 20 Nov 2026), so only IsRemote says remote.
PAYLOCITY = "https://recruiting.paylocity.com/recruiting/jobs/All/"
PL_DATA = re.compile(r"window\.pageData\s*=\s*(\{.*?\});\s*</script>", re.S)


def paylocity_list(page):
    """The postings in a Paylocity board's page, or None when the page is not one."""
    m = PL_DATA.search(page or "")
    if not m: return None
    try: d = json.loads(m.group(1))
    except ValueError: return None
    return d.get("Jobs") if isinstance(d, dict) and isinstance(d.get("Jobs"), list) else None


def fetch_paylocity(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("paylocity")
    jobs = paylocity_list(get_text(f"{PAYLOCITY}{tok}/jobs", 60, accept="text/html"))
    if jobs is None: return name, None
    items = []
    for p in jobs:
        if not isinstance(p, dict) or not p.get("JobId") or not str(p.get("JobTitle") or "").strip() or p.get("IsInternal"): continue
        loc = p.get("JobLocation") if isinstance(p.get("JobLocation"), dict) else {}
        place = ", ".join(dict.fromkeys(str(x).strip() for x in (loc.get("City"), loc.get("State"), loc.get("Country")) if x and str(x).strip()))
        items.append((str(p["JobId"]), {"title": str(p["JobTitle"]).strip(), "place": place, "remote": p.get("IsRemote") is True,
                                        "dept": str(p.get("HiringDepartment") or ""), "posted": str(p.get("PublishedDate") or "")}))

    def read(jid, raw):
        url = f"https://recruiting.paylocity.com/Recruiting/Jobs/Details/{jid}"
        d = jazz_page(_net.get_text(url, 40, accept="text/html", compressed=True))
        desc = str(d.get("description") or "")
        if not desc: return None
        text = strip_html(desc)
        if not english(f"{raw['title']}\n{text}"): return "not english"
        at = str(d.get("datePosted") or raw["posted"] or "")       # day and time from one field (fetch_breezy says why)
        return parse(name, "paylocity", jid, raw["title"], url, raw["place"], raw["remote"], raw["dept"], at[:10],
                     text, jazz_pay(d), str(d.get("employmentType") or ""), desc, False, posted_at=at or None)
    return detail_board(src, reuse, "paylocity", items, read)


# Pinpoint (https://<company>.pinpointhq.com, sources_pinpoint.json, "token": the subdomain; discover_ats.py finds them in Common
# Crawl's index). /postings.json is the list its careers page reads: every open posting with its whole text (in up to four parts, each
# with its heading), place, kind of workplace (remote, hybrid, onsite), employment type and, where the employer shows it, the pay.
# It gives no date of publishing: the record's date is the day we first read the posting. robots.txt of a board (19 Nov 2026) keeps
# crawlers out of /mydata, /admin and /companies only.
PINPOINT_PARTS = (("description", ""), ("key_responsibilities", "key_responsibilities_header"),
                  ("skills_knowledge_expertise", "skills_knowledge_expertise_header"), ("benefits", "benefits_header"))
PIN_FREQ = {"year": "a year", "annum": "a year", "month": "a month", "week": "a week", "day": "a day", "hour": "an hour"}


def pinpoint_place(loc):
    loc = loc if isinstance(loc, dict) else {}
    parts = [loc.get("city"), loc.get("province")]
    name = str(loc.get("name") or "").strip()
    if not any(parts) and name and not re.fullmatch(r"(?i)remote|hybrid|on-?site|office|anywhere", name): parts = [name]
    return ", ".join(dict.fromkeys(str(x).strip() for x in parts if x and str(x).strip()))


def pinpoint_pay(p):
    if not p.get("compensation_visible"): return ""
    lo, hi, cur = p.get("compensation_minimum"), p.get("compensation_maximum"), str(p.get("compensation_currency") or "").upper()
    if not lo and not hi: return str(p.get("compensation") or "").strip()
    fmt = lambda v: f"{int(float(v)):,}" if float(v) >= 1000 else f"{float(v):g}"
    sign = {"USD": "$", "GBP": "£", "EUR": "€", "CAD": "CA$", "AUD": "A$"}.get(cur, cur + " " if cur else "")
    rng = f"{sign}{fmt(lo)} - {sign}{fmt(hi)}" if lo and hi and float(lo) != float(hi) else f"{sign}{fmt(lo or hi)}"
    freq = str(p.get("compensation_frequency") or "").lower()
    return rng + next((" " + v for k, v in PIN_FREQ.items() if k in freq), "")


def fetch_pinpoint(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("pinpoint")
    d = get_json(f"https://{tok}.pinpointhq.com/postings.json", 60)
    if not isinstance(d, dict) or not isinstance(d.get("data"), list): return name, None
    out, src["not_english"] = [], 0
    for p in d["data"]:
        if not isinstance(p, dict) or not p.get("id") or not str(p.get("title") or "").strip() or not p.get("url"): continue
        jid, kind = str(p["id"]), str(p.get("workplace_type") or "").lower()
        job = p.get("job") if isinstance(p.get("job"), dict) else {}
        dept = str((job.get("department") or {}).get("name") or "") if isinstance(job.get("department"), dict) else ""
        desc = "".join((f"<h3>{html.escape(str(p.get(h) or '').strip())}</h3>" if h and str(p.get(h) or "").strip() else "") + str(p.get(k) or "")
                       for k, h in PINPOINT_PARTS if str(p.get(k) or "").strip())
        raw = {"title": str(p["title"]).strip(), "url": str(p["url"]), "place": pinpoint_place(p.get("location")), "kind": kind,
               "type": str(p.get("employment_type_text") or ""), "dept": dept, "pay": pinpoint_pay(p), "desc": desc}
        full_id = f"pinpoint-{slugify(name)}-{jid}"
        if reuse and (rec := reuse(full_id, fingerprint(raw))) is not None:
            out.append(rec); continue
        text = strip_html(desc)
        if not text or not english(f"{raw['title']}\n{text}"):
            src["not_english"] += 1 if text else 0
            continue
        rec = parse(name, "pinpoint", jid, raw["title"], raw["url"], raw["place"], kind == "remote", dept, "", text, raw["pay"], raw["type"], desc, kind == "hybrid")
        rec["h"], rec["rh"] = fingerprint(raw), raw_hash(raw)
        out.append(rec)
    return name, out


def list_board(src, reuse, ats, items):
    """A board whose list holds every posting's text (Pinpoint, Gem, Trakstar): an unchanged posting keeps its record, the others are
    parsed from what the list says; nothing more is asked. items: [(id, raw, (title, url, place, remote, dept, posted, text, pay, type,
    html text, hybrid[, exact time of publishing]))], norm's arguments after the id."""
    name, out = src["name"], []
    src["not_english"] = 0
    for jid, raw, args in items:
        full_id = f"{ats}-{slugify(name)}-{jid}"
        if reuse and (rec := reuse(full_id, fingerprint(raw))) is not None:
            out.append(rec); continue
        title, text = args[0], args[6]
        if not text: continue
        if not english(f"{title}\n{text}"):
            src["not_english"] += 1; continue
        rec = parse(name, ats, jid, *args[:11], **({"posted_at": args[11]} if len(args) > 11 and args[11] else {}))
        rec["h"], rec["rh"] = fingerprint(raw), raw_hash(raw)
        out.append(rec)
    return name, out


# Gem (https://jobs.gem.com/<board>, sources_gem.json, "token": the board's name in its address). Gem's Job Board API, which it
# documents for building one's own careers page (api.gem.com/job_board/v0/<board>/job_posts/), lists every published posting with its
# text, place, kind of workplace (remote, hybrid, in office), department and the time it was first published. api.gem.com answers
# robots.txt with 403 (20 Nov 2026), which under RFC 9309 leaves nothing out of bounds.
def fetch_gem(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("gem")
    d = get_json(f"https://api.gem.com/job_board/v0/{tok}/job_posts/", 60)
    if not isinstance(d, list): return name, None
    items = []
    for p in d:
        if not isinstance(p, dict) or not p.get("id") or not str(p.get("title") or "").strip() or not p.get("absolute_url"): continue
        kind = str(p.get("location_type") or "").lower()
        place = str((p.get("location") or {}).get("name") or "") if isinstance(p.get("location"), dict) else ""
        dept = ", ".join(str(x.get("name") or "") for x in (p.get("departments") or []) if isinstance(x, dict) and x.get("name"))
        desc = str(p.get("content") or "")
        posted = str(p.get("first_published_at") or p.get("created_at") or "")
        raw = {"title": str(p["title"]).strip(), "url": str(p["absolute_url"]), "place": place, "kind": kind, "dept": dept, "desc": desc,
               "type": str(p.get("employment_type") or ""), "posted": posted}
        items.append((str(p["id"]), raw, (raw["title"], raw["url"], place, kind == "remote", dept, posted[:10], strip_html(desc), "",
                                          raw["type"].replace("_", " "), desc, kind == "hybrid", posted or None)))
    return list_board(src, reuse, "gem", items)


# Trakstar Hire, once Recruiterbox (https://<company>.hire.trakstar.com, sources_trakstar.json, "token": the company's name there).
# Its self-service openings API (jsapi.recruiterbox.com/v1/openings?client_name=<company>), which Trakstar offers for careers pages
# of one's own, gives every published opening with its text, address, whether it allows remote work, the type and the team, 10 a
# request: it breaks off any answer longer than about 350 KB (20 Nov 2026: 50 or 100 openings of 8 KB each broke off, over HTTP/2 and
# HTTP/1.1 alike). A board whose pages do not all answer is left as it was: a posting missing from a read would be closed. No date of
# publishing: a posting's date is the day we first read it. robots.txt of the API (19 Nov 2026) allows all but /prepare.
TRAK_TYPE = {"full_time": "Full-time", "part_time": "Part-time", "contract": "Contract", "internship": "Internship", "temporary": "Temporary"}
TRAK_PAGE = 10


def fetch_trakstar(src, reuse=None):
    name, tok = src["name"], src["token"]
    rows, offset, total = [], 0, None
    while offset < 2000 and (total is None or offset < total):
        polite("trakstar")
        d = get_json(f"https://jsapi.recruiterbox.com/v1/openings?client_name={tok}&limit={TRAK_PAGE}&offset={offset}", 60)
        if not isinstance(d, dict) or not isinstance(d.get("objects"), list): return name, None
        rows += d["objects"]
        total = int((d.get("meta") or {}).get("total") or 0)
        offset += TRAK_PAGE
        if not d["objects"]: break
    items = []
    for p in rows:
        if not isinstance(p, dict) or not p.get("id") or not str(p.get("title") or "").strip() or not p.get("hosted_url"): continue
        loc = p.get("location") if isinstance(p.get("location"), dict) else {}
        place = ", ".join(dict.fromkeys(str(x).strip() for x in (loc.get("city"), loc.get("state"), loc.get("country")) if x and str(x).strip()))
        desc = str(p.get("description") or "")
        kind = str(p.get("position_type") or "")
        raw = {"title": str(p["title"]).strip(), "url": str(p["hosted_url"]), "place": place, "remote": bool(p.get("allows_remote")),
               "dept": str(p.get("team") or ""), "type": kind, "desc": desc}
        items.append((str(p["id"]), raw, (raw["title"], raw["url"], place, raw["remote"], raw["dept"], "", strip_html(desc), "",
                                          TRAK_TYPE.get(kind, kind.replace("_", " ")), desc, False)))
    return list_board(src, reuse, "trakstar", items)


# Rippling (https://ats.rippling.com/<board>/jobs, sources_rippling.json, "token": the board's name). The JSON its careers pages read
# (api.rippling.com/platform/api/ats/v1/board/<board>/jobs) lists every open job once for each of its places; the job's own entry
# (.../jobs/<id>) holds the text (the role, then the company), the company's name, the day it was created, the employment type, every
# place and the pay range where one is given. A job its employer keeps out of search (unlistedFromSearch) is left out.
# api.rippling.com has no robots.txt (404, 19 Nov 2026) and ats.rippling.com keeps crawlers out of /internal/ only.
RIPPLING = "https://api.rippling.com/platform/api/ats/v1/board/"
RIP_TYPE = {"SALARIED_FT": "Full-time", "HOURLY_FT": "Full-time", "SALARIED_PT": "Part-time", "HOURLY_PT": "Part-time",
            "CONTRACTOR": "Contract", "CONTRACT": "Contract", "INTERN": "Internship", "TEMP": "Temporary", "SEASONAL": "Temporary"}
RIP_FREQ = {"YEAR": "a year", "MONTH": "a month", "WEEK": "a week", "DAY": "a day", "HOUR": "an hour"}
# a place given as a US state's two letters alone ("CT"): Rippling's boards are American, so the state
US_STATE_NAME = dict(zip("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA "
                         "WA WV WI WY DC".split(),
                         ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
                          "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
                          "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
                          "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
                          "Utah", "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia"]))


def rippling_pay(rows):
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or not (r.get("rangeStart") or r.get("rangeEnd")): continue
        lo, hi, cur = r.get("rangeStart") or r.get("rangeEnd"), r.get("rangeEnd") or r.get("rangeStart"), str(r.get("currency") or "").upper()
        sign = {"USD": "$", "GBP": "£", "EUR": "€", "CAD": "CA$", "AUD": "A$"}.get(cur, cur + " " if cur else "")
        fmt = lambda v: f"{int(float(v)):,}" if float(v) >= 1000 else f"{float(v):g}"
        rng = f"{sign}{fmt(lo)} - {sign}{fmt(hi)}" if float(lo) != float(hi) else f"{sign}{fmt(lo)}"
        return rng + (" " + RIP_FREQ[str(r.get("frequency") or "").upper()] if str(r.get("frequency") or "").upper() in RIP_FREQ else "")
    return ""


def fetch_rippling(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("rippling")
    d = get_json(f"{RIPPLING}{tok}/jobs", 60)
    if not isinstance(d, list): return name, None
    jobs = {}
    for p in d:
        if not isinstance(p, dict) or not p.get("uuid") or not str(p.get("name") or "").strip(): continue
        wl = p.get("workLocation") if isinstance(p.get("workLocation"), dict) else {}
        dp = p.get("department") if isinstance(p.get("department"), dict) else {}
        j = jobs.setdefault(str(p["uuid"]), {"title": str(p["name"]).strip(), "url": str(p.get("url") or f"https://ats.rippling.com/{tok}/jobs/{p['uuid']}"),
                                              "places": [], "dept": str(dp.get("label") or "")})
        if wl.get("label") and str(wl["label"]) not in j["places"]: j["places"].append(str(wl["label"]))
    place_of = lambda ls: "; ".join((f"{US_STATE_NAME[x]}, United States" if x in US_STATE_NAME else x) for x in ls[:6])

    def read(jid, raw):
        x = get_json(f"{RIPPLING}{tok}/jobs/{jid}", 40)
        if not isinstance(x, dict) or not isinstance(x.get("description"), dict): return None
        if x.get("unlistedFromSearch"):
            _jazz_skip.add(f"rippling-{slugify(name)}-{jid}"); return None          # kept out of search by its employer
        parts = x["description"]
        desc = str(parts.get("role") or "") + (f"<h3>About {html.escape(str(x.get('companyName') or name))}</h3>" + str(parts["company"]) if parts.get("company") else "")
        text = strip_html(desc)
        if not text: return None
        if not english(f"{raw['title']}\n{text}"): return "not english"
        places = [str(l) for l in (x.get("workLocations") or []) if isinstance(l, str) and l.strip()] or raw["places"]
        et = x.get("employmentType") if isinstance(x.get("employmentType"), dict) else {}
        made = str(x.get("createdOn") or "")
        return parse(name, "rippling", jid, raw["title"], raw["url"], place_of(places), False, raw["dept"], made[:10], text,
                     rippling_pay(x.get("payRangeDetails")), RIP_TYPE.get(str(et.get("label") or ""), ""), desc, False, posted_at=made or None)
    return detail_board(src, reuse, "rippling", list(jobs.items()), read)


# iCIMS (https://<site>.icims.com, sources_icims.json, "token": the site's subdomain, such as careers-usu). Each careers site
# publishes a sitemap of its open postings (/sitemap.xml, named in its robots.txt), every one with the time it last changed; a
# posting's page, in the form the careers site frames (?in_iframe=1), carries its JobPosting data for search engines: the whole
# text, the date, the type and the full address. robots.txt (19 and 20 Nov 2026) keeps crawlers out of referral, login, candidate
# and "connect" pages only. A posting's text is one request, so iCIMS is read with the slow systems.
ICIMS_JOB = re.compile(r"<loc>(https://[a-z0-9-]+\.icims\.com/jobs/(\d+)/[^<]*?/job)</loc>\s*(?:<lastmod>([^<]*)</lastmod>)?", re.I)
ICIMS_TYPE = {"FULL_TIME": "Full-time", "PART_TIME": "Part-time", "CONTRACTOR": "Contract", "TEMPORARY": "Temporary", "INTERN": "Internship"}


def icims_place(d):
    locs = d.get("jobLocation") if isinstance(d.get("jobLocation"), list) else [d.get("jobLocation")]
    out = []
    for l in locs[:4]:
        a = (l or {}).get("address") if isinstance(l, dict) else None
        if not isinstance(a, dict): continue
        cc = a.get("addressCountry")
        cc = cc.get("name") if isinstance(cc, dict) else cc
        out.append(", ".join(dict.fromkeys(str(x).strip() for x in (a.get("addressLocality"), a.get("addressRegion"), cc) if x and str(x).strip())))
    return "; ".join(dict.fromkeys(x for x in out if x))


def fetch_icims(src, reuse=None):
    name, tok = src["name"], src["token"]
    polite("icims")
    xml = get_text(f"https://{tok}.icims.com/sitemap.xml", 60, accept="application/xml")
    if not xml or "<urlset" not in xml: return name, None
    items = [(jid, {"url": url, "mod": mod or ""}) for url, jid, mod in ICIMS_JOB.findall(xml)]

    def read(jid, raw):
        d = jazz_page(_net.get_text(raw["url"] + "?in_iframe=1", 40, accept="text/html", compressed=True))
        desc, title = str(d.get("description") or ""), str(d.get("title") or "").strip()
        if not desc or not title: return None
        text = strip_html(desc)
        if not english(f"{title}\n{text}"): return "not english"
        et = d.get("employmentType")
        et = (et[0] if isinstance(et, list) and et else et) or ""
        remote = str(d.get("jobLocationType") or "").upper() == "TELECOMMUTE"
        posted = str(d.get("datePosted") or "")
        return parse(name, "icims", jid, title, raw["url"], icims_place(d), remote, "", posted[:10], text, jazz_pay(d),
                     ICIMS_TYPE.get(str(et).upper(), ""), desc, False, posted_at=posted or None)
    return detail_board(src, reuse, "icims", items, read)


_fetch_any = fetch
READERS = {"usajobs": fetch_usajobs, "jazzhr": fetch_jazzhr, "breezy": fetch_breezy, "bamboohr": fetch_bamboohr, "paylocity": fetch_paylocity,
           "pinpoint": fetch_pinpoint, "gem": fetch_gem, "trakstar": fetch_trakstar, "rippling": fetch_rippling, "icims": fetch_icims}      # the systems read outside fetch_feed


def fetch(src, reuse=None):              # noqa: F811  (the hiring systems above, plus USAJOBS and JazzHR)
    read = READERS.get(src.get("ats"))
    if read:
        gate = _gate.get(src.get("ats"))
        try:
            if gate: gate.acquire()
            return read(src, reuse)
        except Exception as ex:
            print(f"feed error for {src.get('name')}: {type(ex).__name__}: {ex}")
            return src["name"], None
        finally:
            if gate: gate.release()
    return _fetch_any(src, reuse)


def rename_records(db, files=None):
    """A company renamed in its sources file keeps its old name in "was" (20 Nov 2026: names given in capitals, "ARC OF CARROLL
    COUNTY" -> "ARC of Carroll County"). Every record of the old name takes the new one before anything is compared, so its jobs keep
    their ids and addresses (both in lower case) and the postings gone from the board still close. Taken from every sources file, not
    only the boards read this hour: the records of a board resting this hour would otherwise belong to no company read and be closed.
    Returns how many were renamed."""
    to = {}
    for f in files or sorted(ROOT.glob("sources*.json")):
        if "candidates" in Path(f).name: continue
        to.update((s["was"], s["name"]) for s in json.loads(Path(f).read_text()) if s.get("was") and s["was"] != s["name"])
    n = 0
    for j in db.values() if to else ():
        if j.get("company") in to: j["company"] = to[j["company"]]; n += 1
    return n


NOT_WORD_EDGE = "\"'.,;:!?()[]{}*•·–—-/“”‘’«»"


def not_words(text):
    """True when the text of a job posted in the account is mostly not words, so it is held back from the site (owner's test job of
    18 Nov 2026, "312 л3л 12л3 13 123 1312 3 e 12e 12e ...", was live as an open job a week later because the server still listed it).
    A word is letters only, two or more, with a vowel unless it is in capitals (SQL, CRM) or not in Latin letters; fewer than half
    of the text's pieces being words means a person should look at it first. The server's own check (screenPosting) says the same."""
    toks = [t.strip(NOT_WORD_EDGE) for t in str(text or "").split()]
    toks = [t for t in toks if t]
    if not toks: return False
    word = lambda t: (len(t) >= 2 and re.fullmatch(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", t) is not None
                      and (re.search(r"[aeiouyAEIOUYà-ÿÀ-ß]", t) is not None or t.isupper() or re.search(r"[^\x00-\x7f]", t) is not None))
    return sum(1 for t in toks if word(t)) < len(toks) / 2


assert not_words("312 л3л 12л3 13 123 1312 3 e 12e 12e 12e 12e 12le 1l2e mkl21em 21lke kl21le k12mkl e2 1e") and not not_words("")
assert not not_words("We are hiring a barista for our café. You will make coffee, serve guests and keep the bar clean. SQL, CRM and B2B are a plus.")
assert not not_words("Мы ищем бариста в кофейню: смены по выходным, обучение за наш счёт.")


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
    seen, junk = set(), set()
    for d in exp["jobs"]:
        if not isinstance(d, dict) or str(d.get("company", "")).strip().lower() in indexed: continue   # a posting may not pass itself off as an indexed company
        if not_words(d.get("text")):                 # held back, and its page taken down below like a deleted one (25 Nov 2026)
            junk.add(str(d.get("id", ""))); continue
        j = norm(str(d.get("company", "")).strip(), "direct", d.get("id", ""), d.get("title"), d.get("url"), d.get("location"), bool(d.get("remote")), "",
                 d.get("posted"), str(d.get("text") or ""), str(d.get("salary") or ""), str(d.get("etype") or ""), hybrid=bool(d.get("hybrid")))   # hybrid: set by a moderator (26 Nov 2026)
        j["desc"] = direct_desc(d.get("text"))      # the employer's own words, whole and escaped: short texts are kept too (clean_html drops anything under 200 characters)
        j.pop("_crypto")
        if not j["title"] or not j["company"] or not str(j["url"]).startswith("https://"): continue
        # what the account sold for this job (server: exportForSite): a Standard boost, a Premium boost (with its cover picture), the
        # "Urgently hiring" badge, and a bump, which says when it was bought. Until 18 Nov 2026 only featured_until was read here, so
        # Premium, the badge and the bump could be bought and showed nowhere.
        j.update(crypto=False, direct=True, featured_until=str(d.get("featured_until") or ""), premium_until=str(d.get("premium_until") or ""),
                 urgent_until=str(d.get("urgent_until") or ""), bumped=str(d.get("bumped") or ""), cover=str(d.get("cover") or ""))
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
    # A job its owner deleted for good, or a moderator took down, leaves the site altogether: no page marked "closed" is kept for
    # it (the owner deleted his own test job on 18 Nov 2026 and expected it gone). The API names such jobs in "gone" for 45 days.
    gone = {str(x) for x in exp.get("gone") or [] if isinstance(x, str) and x} | {x for x in junk if x}
    if junk: print(f"posted jobs: {len(junk)} held back, their text is mostly not words")
    for jid in [k for k, old in db.items() if old.get("direct") and any(k.endswith("-" + g) for g in gone)]:
        used_slugs.discard(db[jid].get("slug")); del db[jid]
    keep = lambda rows, keys: [{k: str(r.get(k, "")) for k in keys} for r in rows if isinstance(r, dict)]
    # company pages kept by the companies themselves (a verified claim): the text, the site, the places, and the logo, which is saved
    # as data/logos/<company>.png so that every page shows it the way it shows the logos we hold ourselves (build.LOGOS)
    claimed = [{"company": str(c.get("company") or ""), "since": str(c.get("since") or ""), "about": str(c.get("about") or ""), "website": str(c.get("website") or ""),
                "locations": [str(x) for x in (c.get("locations") or []) if isinstance(x, str)][:12]} for c in exp.get("claimed") or [] if isinstance(c, dict) and c.get("company")]
    logos = ROOT / "data" / "logos"
    logos.mkdir(parents=True, exist_ok=True)
    held = set()
    for c in exp.get("claimed") or []:
        url, slug = (str(c.get("logo") or ""), slugify(str(c.get("company") or ""))) if isinstance(c, dict) else ("", "")
        if not slug or not url.startswith(api + "/"): continue                       # a logo is taken only from our own API
        held.add(slug)
        pic = get_bytes(url, 20)
        if pic and len(pic) <= 600_000 and pic[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"\xff\xd8\xff\xdb", b"RIFF"): (logos / f"{slug}.png").write_bytes(pic)
    for f in logos.glob("*.png"):
        if f.stem not in held: f.unlink()                                               # the claim ended or the logo was removed
    (ROOT / "data" / "placements.json").write_text(json.dumps({"boosts": keep(exp.get("boosts") or [], ("slug", "kind", "until", "at", "cover")),
                                                               "sponsors": keep(exp.get("sponsors") or [], ("company", "slot", "until")), "claimed": claimed}, ensure_ascii=False))
    print(f"placements: {len(seen)} posted jobs, {len(exp.get('boosts') or [])} promoted, {len(exp.get('sponsors') or [])} sponsors, {len(claimed)} company pages, {len(held)} logos")


# A whole hiring system that suddenly answers with empty lists (its API changed, or it is down) must not close its jobs. A reader's
# remark under the vc.ru article on Rekru (read 19 Nov 2026): a parser can "quietly collect zero for two months", and a run that
# succeeds says nothing about whether the catalogue was updated; watch for a sharp drop per source. One board going empty is normal
# (the company stopped hiring or moved its board, and its jobs close); many boards of one system at once is not.
DOWN_MIN, DOWN_SHARE = 5, 0.1

# Boards that no longer exist (26 Nov 2026 audit of the live site). A reader gives None both when a board's list did not answer and
# when the hiring system says there is no such board (the company left that system or renamed its board), and None keeps every job of
# the company open, with an Apply button that leads to a "page not found". On 26 Nov 2026 Klaviyo's Ashby board had answered 404
# since 16 Nov and its 149 jobs were still listed as open; Headout (19, since 17 Nov), Norm Ai (28), Kunai, SHEIN, Oso, AI Squared and
# others the same. A board that failed is now asked once more, plainly, whether it exists (board_gone), but only when none of the
# company's open jobs was seen on a read in the last GONE_DAYS days. When its hiring system answers that the board does not exist, its
# jobs close. Any other answer (a timeout, a 403, a 500, a page that is not a list) changes nothing, as before; so does a hiring system
# that says "no such board" for many boards in one run (DOWN_MIN, DOWN_SHARE: a fault on its side).
GONE_DAYS = 2


def board_gone(src):
    """True only when the board's hiring system answers that the board does not exist: HTTP 404 from its list (Workday: 404 with its own
    error code), or the address sent on to the hiring system's own home or "not found" page (BambooHR, JazzHR, Paylocity; BambooHR also to
    the page of a suspended or expired account), or Trakstar's "Invalid client name". False on every other answer, on no answer, and for systems without a clear "no such board"."""
    ats, tok = src.get("ats"), str(src.get("token") or "")
    if not tok or ("/" in tok and ats != "workday"): return False
    data, key = None, ats
    if ats == "greenhouse": url = f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs"
    elif ats == "lever": url = f"https://api.lever.co/v0/postings/{tok}?mode=json&limit=1"
    elif ats == "ashby": url = f"https://api.ashbyhq.com/posting-api/job-board/{tok}"
    elif ats == "workable": url = f"https://apply.workable.com/api/v1/widget/accounts/{tok}"
    elif ats == "recruitee" and "." not in tok: url = f"https://{tok}.recruitee.com/api/offers/"
    elif ats == "teamtailor" and "." not in tok: url = f"https://{tok}.teamtailor.com/jobs.rss"
    elif ats == "personio" and "." not in tok: url = f"https://{tok}.jobs.personio.de/xml?language=en"
    elif ats == "breezy": url = f"https://{tok}.breezy.hr/json"
    elif ats == "pinpoint": url = f"https://{tok}.pinpointhq.com/postings.json"
    elif ats == "gem": url = f"https://api.gem.com/job_board/v0/{tok}/job_posts/"
    elif ats == "rippling": url = f"{RIPPLING}{tok}/jobs"
    elif ats == "icims": url = f"https://{tok}.icims.com/sitemap.xml"
    elif ats == "bamboohr": url = f"https://{tok}.bamboohr.com/careers/list"
    elif ats == "jazzhr": url = f"https://{tok}.applytojob.com/apply"
    elif ats == "paylocity": url = f"{PAYLOCITY}{tok}/jobs"
    elif ats == "trakstar": url = f"https://jsapi.recruiterbox.com/v1/openings?client_name={tok}&limit=1&offset=0"
    elif ats == "workday" and "/" in tok:
        host, site = tok.split("/", 1)
        url, key = f"https://{host}.myworkdayjobs.com/wday/cxs/{host.split('.')[0]}/{site}/jobs", f"workday:{host}"
        data = {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""}
    else:
        return False
    polite(key)
    got = _net.probe(url, 20, data)
    if not got: return False
    code, final, text = got
    import urllib.parse
    asked, landed = url.split("/")[2].lower(), (final.split("/")[2].lower() if final.count("/") >= 2 else "")
    if ats == "bamboohr": return landed in ("www.bamboohr.com", "bamboohr.com") or (landed == asked and re.search(r"/settings/account/(suspended|expired)", urllib.parse.unquote(final)) is not None)
    if ats == "jazzhr": return landed in ("www.jazzhr.com", "jazzhr.com")
    if ats == "paylocity": return landed == asked and "/jobs/jobnotfound" in final.lower()
    if ats == "trakstar": return code == 400 and "invalid client name" in text.lower()
    if ats == "workday": return code == 404 and '"errorCode"' in text
    if ats == "icims": return code == 404 and landed == asked and "gone:" in text.lower()
    return code == 404 and landed == asked


def close_gone(db, sources, failed, open_by_co, stats, gone=board_gone, today=None):
    """Closes the open jobs of boards that failed this run, have shown none of those jobs on a read for GONE_DAYS days and that their
    hiring system says no longer exist (gone). Moves such a board from stats["failed"] to stats["gone"] ("name (jobs closed)").
    Returns how many jobs it closed."""
    today = today or TODAY
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=GONE_DAYS)).isoformat()
    by_name = {s["name"]: s for s in sources}
    ask = []
    for name in dict.fromkeys(failed):
        ids = [jid for jid in open_by_co.get(name, ()) if (db.get(jid) or {}).get("active") and not db[jid].get("direct") and not db[jid].get("tg")]
        if not ids or name not in by_name: continue
        if max(str(db[jid].get("last_seen") or "") for jid in ids) > cutoff: continue       # read in the last GONE_DAYS days: a failure, not yet a sign
        ask.append((by_name[name], ids))
    if not ask: return 0
    with cf.ThreadPoolExecutor(4) as ex:
        said = list(ex.map(lambda a: bool(gone(a[0])), ask))
    found = [(s, ids) for (s, ids), g in zip(ask, said) if g]
    per, boards = defaultdict(int), defaultdict(int)
    for s, _ in found: per[s.get("ats", "")] += 1
    for s in sources:
        if open_by_co.get(s["name"]): boards[s.get("ats", "")] += 1
    held = {a for a, n in per.items() if n >= DOWN_MIN and n >= DOWN_SHARE * boards[a]}
    if held: print("HIRING SYSTEMS THAT SAY MANY BOARDS DO NOT EXIST (nothing closed for them):", ", ".join(f"{a} ({per[a]} boards)" for a in sorted(held)))
    closed = 0
    for s, ids in found:
        if s.get("ats", "") in held: continue
        for jid in ids: db[jid].update(active=False, closed=today)
        closed += len(ids)
        stats.setdefault("gone", []).append(f"{s['name']} ({len(ids)})")
        if s["name"] in stats.get("failed", []): stats["failed"].remove(s["name"])
    stats["closed"] = stats.get("closed", 0) + closed
    if stats.get("gone"): print("boards that no longer exist (their jobs closed):", ", ".join(stats["gone"]))
    return closed


def guard_systems(results, sources, open_by_co, late, stats):
    """Boards with at least 5 open jobs that came back empty, counted per hiring system. When one system has DOWN_MIN or more such
    boards and they are DOWN_SHARE or more of its boards with open jobs, its empty answers count as "did not answer" this run: the
    jobs stay open and the status page names the system. Returns the results with those answers replaced by None."""
    ats_of = {s["name"]: s.get("ats", "") for s in sources}
    had, went = defaultdict(int), defaultdict(int)
    for name, jobs in results:
        if name in late or jobs is None or len(open_by_co.get(name, ())) < 5: continue
        had[ats_of.get(name, "")] += 1
        if not jobs: went[ats_of.get(name, "")] += 1
    down = sorted(a for a, n in went.items() if n >= DOWN_MIN and n >= DOWN_SHARE * had[a])
    if not down: return results
    stats["down"] = [f"{a} ({went[a]} of {had[a]} boards empty)" for a in down]
    print("HIRING SYSTEMS THAT LOOK BROKEN (many boards empty at once; their jobs are kept open):", "; ".join(stats["down"]))
    return [(name, None if jobs is not None and not jobs and ats_of.get(name) in down else jobs) for name, jobs in results]


def save_db(db):
    """Writes data/jobs.json one record at a time, byte for byte what json.dumps(db, ensure_ascii=False, indent=0) wrote before.
    The whole file in one string took several times its size in memory (a list of every small piece, then the joined text, then its
    bytes); at 1.95 GB (645,000 open jobs, 22 Nov 2026) the runner ran out of memory and every run died at the end of "Collect jobs",
    two or three minutes after the 40 minutes of reading. A temporary file and a rename: a run that dies here leaves the old file whole."""
    tmp = DATA.with_name(DATA.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("{")
        for i, (k, v) in enumerate(db.items()):
            f.write(("," if i else "") + "\n" + json.dumps(k, ensure_ascii=False) + ": " + json.dumps(v, ensure_ascii=False, indent=0))
        f.write("\n}" if db else "}")
    os.replace(tmp, DATA)


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
    core_names = {s["name"] for s in sources}
    rot = max(1, int(os.environ.get("HRN_ROTATE") or 4))
    hour = datetime.datetime.now(datetime.timezone.utc).hour
    for f in ROTATING:
        for s in (json.loads((ROOT / f).read_text()) if (ROOT / f).exists() else []):
            if s.get("hold"): continue                     # verified, but waiting until the hourly build can take its jobs (ATS_REPORT.md)
            if (s["ats"], s["token"]) in taken or s["name"].lower() in taken or s["name"] in EXCLUDE_TECH: continue
            taken |= {(s["ats"], s["token"]), s["name"].lower()}
            r = rot * 2 if s["ats"] in SLOW_ATS else rot
            if (s.get("lifted") or "") >= FILL_SINCE or int(hashlib.md5(s["token"].encode()).hexdigest(), 16) % r == hour % r:
                sources.append(dict(s, crypto=False))
            else:
                resting.add(s["name"])
    is_crypto = {s["name"]: s["crypto"] for s in sources}
    # The boards read every hour stand first; the others in an order that changes every hour, so that the boards a run has no time
    # for are not always the same ones.
    import random
    hourly = {s["name"] for s in sources if s["name"] in core_names}
    rest = [s for s in sources if s["name"] not in hourly]
    random.Random(int(time.time() // 3600)).shuffle(rest)
    sources = [s for s in sources if s["name"] in hourly] + rest
    db = jobsdb.load(DATA) if DATA.exists() else {}      # one record at a time: the plain read needed 4x the 2 GB file (jobsdb.py)
    renamed = rename_records(db)
    if renamed: print(f"{renamed:,} records took their company's new name")
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
    # A run has a budget for reading (18 Nov 2026: with 184 boards filling, reading took 90 to 105 minutes, the run reached its limit while
    # building, and the site stayed at 287,730 jobs while 338,970 were already collected). After it no new board outside the hourly list is
    # started: such a board keeps its jobs as they are, like one resting this hour, and has its turn in a later run.
    t0 = time.time()
    stop_at, late = t0 + float(os.environ.get("HRN_COLLECT_MINUTES") or 40) * 60, set()
    def read(s):
        if s["name"] not in hourly and time.time() > stop_at:
            late.add(s["name"]); return s["name"], None
        return fetch(s, None if s["crypto"] else reuse)
    # Reading is waiting for answers, 32 boards at a time (20 before 15 Nov 2026); parsing a posting that changed is CPU work, done in
    # one worker process per CPU (parse). Before 15 Nov a run was mostly parsing, on one CPU, with every posting parsed every hour.
    global PARSE
    import multiprocessing
    PARSE = cf.ProcessPoolExecutor(int(os.environ.get("HRN_PARSERS") or os.cpu_count() or 2), mp_context=multiprocessing.get_context("spawn"))
    try:
        # Each hiring system with a limit (ATS_LIMIT) gets a pool of exactly that size. In one shared pool the workers stood waiting for the
        # busiest system's turn while the others had nothing to do. The pools make the gates in fetch() needless here.
        _gate.clear()
        groups = defaultdict(list)
        for s in sources: groups[s["ats"] if s["ats"] in ATS_LIMIT else ""].append(s)
        def run_group(item):
            ats, xs = item
            with cf.ThreadPoolExecutor(ATS_LIMIT.get(ats) or int(os.environ.get("HRN_WORKERS") or 72)) as ex:
                return list(ex.map(read, xs))
        with cf.ThreadPoolExecutor(len(groups) or 1) as ex:
            results = [r for rows in ex.map(run_group, groups.items()) for r in rows]
        # second, gentler pass for feeds that timed out or were rate-limited the first time
        by_name = {s["name"]: s for s in sources}
        retry = [by_name[name] for name, jobs in results if jobs is None and name not in late]
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
    results = guard_systems(results, sources, open_by_co, late, stats)
    for name, jobs in results:
        if name in late: continue                           # no time for it in this run: it stays as it was
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
                # the day the job's page last changed, for the sitemap's lastmod (build.py, 26 Nov 2026): the posting's text changed, or it opened again
                ch_ = TODAY if (old.get("h") and j.get("h") and old["h"] != j["h"]) or not old.get("active") else old.get("changed")
                if ch_: j["changed"] = ch_
            else:
                base = f"{slugify(j['title'])}-{slugify(name)}"
                slug, i = base, 2
                while slug in used_slugs:
                    slug, i = f"{base}-{i}", i + 1
                used_slugs.add(slug)
                j.update(slug=slug, first_seen=TODAY, first_seen_at=seen_at)
                stats["new"] += 1
            # checked_at: when this run read the job on the employer's list; the job page shows it as "checked 12 minutes ago" and the
            # site's freshness figure counts it (build.FACTS; teardown 26 Nov 2026: "re-checked every hour" was never measured)
            j.update(last_seen=TODAY, checked_at=seen_at, active=True)
            j.pop("closed", None)
            db[j["id"]] = j
        gone = [db[jid] for jid in open_by_co.get(name, ()) if db[jid]["active"] and jid not in seen]
        for old in gone:
            old.update(active=False, closed=TODAY); stats["closed"] += 1
        if not jobs and len(gone) >= 20:
            stats["emptied"].append(name)                   # the whole board went empty at once: often a move to another hiring system
    try:                                                    # boards whose hiring system says they no longer exist (close_gone)
        close_gone(db, sources, list(stats["failed"]), open_by_co, stats)
    except Exception as ex:                                 # never a reason to stop the hourly run: they stay as they were
        print(f"gone boards: not checked this run: {type(ex).__name__}: {ex}")
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
    save_db(db)
    active = sum(j["active"] for j in db.values())
    print(f"read {len(sources) - len(late)} boards in {read_s:.0f} s ({len(resting)} resting this hour, {len(late)} left for a later run); {stats['parsed']} postings parsed, the rest unchanged "
          f"since the last run; {not_en} left out as not in English")
    print(f"active {active}, archived {len(db) - active}, new {stats['new']}, closed {stats['closed']}")
    # what this run did, shown on the site's data status page
    (ROOT / "data" / "stats.json").write_text(json.dumps({"date": TODAY, "time": datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M UTC"), "sources": len(sources),
                                                          "failed": stats["failed"], "emptied": stats["emptied"], "down": stats.get("down", []), "gone": stats.get("gone", []),
                                                          "new": stats["new"], "closed": stats["closed"], "active": active}, ensure_ascii=False))
    print("failed:", ", ".join(stats["failed"]) or "-")
    print("boards that went empty (check whether the company moved its job board):", ", ".join(stats["emptied"]) or "-")
    print("dropped as not crypto:", ", ".join(stats["dropped"]) or "-")


if __name__ == "__main__":
    main()
# <<< not rules
