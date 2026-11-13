"""Generate the static site into ./site from data/jobs.json (+ optional paid.json).

Closed jobs keep their pages forever (archive); only the JobPosting markup and the apply button are removed.
"""
import datetime, hashlib, html, json, os, re, shutil
from urllib.parse import quote
from collections import Counter, defaultdict
from email.utils import format_datetime
from pathlib import Path
from collect import CATS, OTHER, PERKS, SKILLS, slugify
import tools_pages                      # the free tools section: /tools/ and one page per tool
import roles_info
import skills_info                      # what each skill is, in plain words, and its group

ROOT = Path(__file__).parent
OUT = ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
CFG["api_url"] = os.environ.get("HRN_API_URL", CFG.get("api_url", "")).rstrip("/")   # the accounts and checkout API; empty until it is deployed
SITE, BASE, P = CFG["site_name"], CFG["base_url"].rstrip("/"), CFG.get("base_path", "").rstrip("/")
FULL = BASE + P
TODAY = datetime.date.today().isoformat()
e = html.escape
CAT = {s: n for s, n, _ in CATS} | {OTHER[0]: OTHER[1]}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
# ---------------------------------------------------------------- where a job is
# A location line is split into parts ("Berlin; New York, NY"), and each part is read on its own: a country or a US state
# written in the part decides; only when neither is written do well-known city names count. That keeps "Vancouver, Washington"
# in the United States, "Porto Alegre, Brazil" out of Portugal and "Dublin, CA" out of Ireland.
COUNTRIES = [   # (ISO code, name, the country written out, well-known cities)
    ("GB", "United Kingdom", r"united kingdom|\buk\b|\bu\.k\.|(?<!new )england|scotland|\bwales\b|great britain", r"\blondon\b(?!, on\b)|manchester|edinburgh|\bbristol\b|cambridge, uk|\bleeds\b|glasgow|belfast"),
    ("CA", "Canada", r"\bcanada\b|\bontario\b|british columbia|\bquebec\b|\balberta\b", r"toronto|vancouver|montr[eé]al|ottawa|calgary|waterloo"),
    ("DE", "Germany", r"\bgermany\b|deutschland", r"\bberlin\b|munich|münchen|frankfurt|hamburg|cologne|stuttgart|düsseldorf"),
    ("FR", "France", r"\bfrance\b", r"\bparis\b|\blyon\b"), ("IE", "Ireland", r"(?<!northern )\bireland\b", r"\bdublin\b|\bcork\b"),
    ("NL", "Netherlands", r"netherlands|\bholland\b", r"amsterdam|rotterdam|utrecht|eindhoven"), ("ES", "Spain", r"\bspain\b|españa", r"barcelona|\bmadrid\b|valencia"),
    ("PT", "Portugal", r"\bportugal\b", r"lisbon|lisboa|\bporto\b(?! alegre| seguro| velho)"), ("PL", "Poland", r"\bpoland\b", r"warsaw|krak[oó]w|wroc[lł]aw|gda[nń]sk"),
    ("SE", "Sweden", r"\bsweden\b", r"stockholm|gothenburg"), ("CH", "Switzerland", r"switzerland", r"zurich|zürich|\bgeneva\b|\bzug\b|lausanne"),
    ("AT", "Austria", r"\baustria\b", r"\bvienna\b"), ("IT", "Italy", r"\bitaly\b", r"\bmilan\b|\brome\b"), ("DK", "Denmark", r"\bdenmark\b", r"copenhagen"),
    ("NO", "Norway", r"\bnorway\b", r"\boslo\b"), ("FI", "Finland", r"\bfinland\b", r"helsinki"), ("BE", "Belgium", r"\bbelgium\b", r"brussels"),
    ("CZ", "Czechia", r"czech", r"\bprague\b"), ("RO", "Romania", r"\bromania\b", r"bucharest|\bcluj\b"), ("UA", "Ukraine", r"\bukraine\b", r"\bkyiv\b"),
    ("EE", "Estonia", r"\bestonia\b", r"tallinn"), ("LT", "Lithuania", r"lithuania", r"vilnius"), ("GR", "Greece", r"\bgreece\b", r"\bathens\b"),
    ("BG", "Bulgaria", r"\bbulgaria\b", r"\bsofia\b"), ("HU", "Hungary", r"\bhungary\b", r"budapest"), ("RS", "Serbia", r"\bserbia\b", r"belgrade"),
    ("IN", "India", r"\bindia\b", r"bangalore|bengaluru|mumbai|hyderabad|\bpune\b|\bdelhi\b|gurgaon|gurugram|chennai|\bnoida\b"),
    ("SG", "Singapore", r"singapore", r""), ("HK", "Hong Kong", r"hong kong", r""), ("JP", "Japan", r"\bjapan\b", r"\btokyo\b|\bosaka\b"),
    ("KR", "South Korea", r"\bkorea\b", r"\bseoul\b"), ("TW", "Taiwan", r"\btaiwan\b", r"taipei"), ("CN", "China", r"\bchina\b", r"shanghai|beijing|shenzhen"),
    ("AU", "Australia", r"\baustralia\b", r"\bsydney\b|\bmelbourne\b|\bbrisbane\b|\bperth\b"), ("NZ", "New Zealand", r"new zealand", r"auckland|wellington"),
    ("BR", "Brazil", r"\bbrazil\b|\bbrasil\b", r"s[ãa]o paulo|rio de janeiro"), ("MX", "Mexico", r"(?<!new )\bm[eé]xico\b", r"guadalajara|monterrey"),
    ("AR", "Argentina", r"argentina", r"buenos aires"), ("CO", "Colombia", r"\bcolombia\b", r"bogot[aá]|medell[ií]n"), ("CL", "Chile", r"\bchile\b", r"santiago"),
    ("IL", "Israel", r"\bisrael\b", r"tel aviv"), ("AE", "United Arab Emirates", r"\buae\b|united arab emirates", r"\bdubai\b|abu dhabi"),
    ("SA", "Saudi Arabia", r"saudi", r"riyadh|king abdullah|jeddah"), ("TR", "Türkiye", r"\bturkey\b|türkiye", r"istanbul"),
    ("MY", "Malaysia", r"malaysia", r"kuala lumpur"), ("PH", "Philippines", r"philippines", r"\bmanila\b"), ("ID", "Indonesia", r"indonesia", r"jakarta"),
    ("TH", "Thailand", r"thailand", r"bangkok"), ("VN", "Vietnam", r"vietnam", r"ho chi minh|hanoi|da nang"),
    ("ZA", "South Africa", r"south africa", r"cape town|johannesburg"), ("NG", "Nigeria", r"nigeria", r"\blagos\b"), ("KE", "Kenya", r"\bkenya\b", r"nairobi"),
]
US_NAME = r"united states|\busa\b|\bu\.s\.(a\.)?|(?-i:\bUS\b)(?! ?\$)"
US_STATES = (r"alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|\bgeorgia\b|hawaii|idaho|illinois|\bindiana\b|\biowa\b|kansas|kentucky|louisiana|"
             r"\bmaine\b|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|"
             r"\bohio\b|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|\btexas\b|\butah\b|vermont|virginia|\bwashington\b|wisconsin|wyoming|district of columbia")
US_ABBR = re.compile(r"(?:,|-|–|\()\s?(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b")
US_CITY = (r"\bnyc\b|\bsf\b|san francisco|bay area|seattle|boston|chicago|\baustin\b|denver|atlanta|los angeles|\bmiami\b|\bdallas\b|houston|san diego|palo alto|mountain view|san jose|"
           r"sunnyvale|santa clara|philadelphia|pittsburgh|\bphoenix\b|raleigh|salt lake|menlo park|redwood city|brooklyn|manhattan")
CA_PROVINCE = re.compile(r",\s?(ON|BC|QC|AB|MB|SK|NS|NB)\b")
_geo_cache = {}


def countries_of(loc):
    """Every country a location line names: [(ISO code, name), ...] in the order the parts are written."""
    if loc in _geo_cache: return _geo_cache[loc]
    found = []
    for part in re.split(r";|\||/| or | and |•", loc):
        named = [(c, nm) for c, nm, rx, _ in COUNTRIES if re.search(rx, part, re.I)]
        province = bool(CA_PROVINCE.search(part))
        if province and ("CA", "Canada") not in named: named.append(("CA", "Canada"))
        us = bool(re.search(US_NAME, part, re.I) or re.search(US_STATES, part, re.I) or (US_ABBR.search(part) and not province))
        if us: named.append(("US", "United States"))
        if not named:                                           # nothing written out: fall back to cities everyone knows
            named = [(c, nm) for c, nm, _, city in COUNTRIES if city and re.search(city, part, re.I)]
            if re.search(US_CITY, part, re.I): named.append(("US", "United States"))
        found += [x for x in named if x not in found]
    _geo_cache[loc] = found
    return found


def country_of(loc):
    """The single country of a location line, or None when it names none or several."""
    got = countries_of(loc)
    return got[0] if len(got) == 1 else None


REGIONS = {"europe": ({"GB", "DE", "FR", "IE", "NL", "ES", "PT", "PL", "SE", "CH", "AT", "IT", "DK", "NO", "FI", "BE", "CZ", "RO", "UA", "EE", "LT", "GR", "BG", "HU", "RS"}, r"\beurope\b|\bemea\b|\beu\b"),
           "asia-pacific": ({"IN", "SG", "HK", "JP", "KR", "TW", "CN", "AU", "NZ", "MY", "PH", "ID", "TH", "VN"}, r"\bapac\b|\basia\b"),
           "latin-america": ({"BR", "MX", "AR", "CO", "CL"}, r"\blatam\b|latin america"),
           "africa": ({"ZA", "NG", "KE"}, r"\bafrica\b")}
# (name, slug, rule). A rule is a country code, a region key, or (pattern, country the match must agree with).
PLACES = [
    ("the United States", "united-states", "US"), ("Canada", "canada", "CA"), ("London & the UK", "united-kingdom", "GB"), ("Europe", "europe", "region"),
    ("Germany", "germany", "DE"), ("France", "france", "FR"), ("Switzerland", "switzerland", "CH"), ("Austria", "austria", "AT"), ("Poland", "poland", "PL"),
    ("Ireland", "ireland", "IE"), ("the Netherlands", "netherlands", "NL"), ("Spain", "spain", "ES"), ("Portugal", "portugal", "PT"), ("Sweden", "sweden", "SE"), ("Israel", "israel", "IL"),
    ("Asia-Pacific", "asia-pacific", "region"), ("India", "india", "IN"), ("Singapore", "singapore", "SG"), ("Hong Kong", "hong-kong", "HK"), ("Japan", "japan", "JP"),
    ("South Korea", "south-korea", "KR"), ("Taiwan", "taiwan", "TW"), ("Australia", "australia", "AU"), ("Malaysia", "malaysia", "MY"), ("the Philippines", "philippines", "PH"),
    ("Dubai & UAE", "uae", "AE"), ("Turkey", "turkey", "TR"), ("Latin America", "latin-america", "region"), ("Brazil", "brazil", "BR"), ("Mexico", "mexico", "MX"), ("Africa", "africa", "region"),
    # cities and states people search for by name ("tech jobs seattle", "tech jobs in austin")
    ("New York", "new-york", (r"new york|\bnyc\b|brooklyn|manhattan|(?-i:, NY\b)", "US")),
    ("San Francisco Bay Area", "san-francisco", (r"san francisco|bay area|palo alto|san jose|mountain view|sunnyvale|santa clara|menlo park|redwood city|\bsf\b|oakland|san mateo", "US")),
    ("California", "california", (r"california|(?-i:, CA\b)|san francisco|bay area|palo alto|san jose|mountain view|los angeles|san diego|sunnyvale|santa clara|irvine|hawthorne", "US")),
    ("Seattle", "seattle", (r"seattle|bellevue|redmond|kirkland", "US")), ("Austin", "austin", (r"\baustin\b", "US")), ("Chicago", "chicago", (r"\bchicago\b", "US")),
    ("Boston", "boston", (r"\bboston\b|cambridge, ma", "US")), ("Washington, DC", "washington-dc", (r"washington,? ?d\.?c\.?|(?-i:\bDC\b)|arlington, va|mclean|reston", "US")),
    ("Denver", "denver", (r"\bdenver\b|boulder", "US")), ("Los Angeles", "los-angeles", (r"los angeles|santa monica|culver city|el segundo|hawthorne|irvine", "US")),
    ("Dallas", "dallas", (r"\bdallas\b|plano|fort worth", "US")), ("Atlanta", "atlanta", (r"\batlanta\b", "US")), ("San Diego", "san-diego", (r"san diego", "US")),
    ("Pittsburgh", "pittsburgh", (r"pittsburgh", "US")), ("Portland", "portland", (r"\bportland\b", "US")), ("Miami", "miami", (r"\bmiami\b", "US")),
    ("Phoenix", "phoenix", (r"\bphoenix\b|scottsdale|tempe", "US")), ("Raleigh-Durham", "raleigh-durham", (r"raleigh|durham|research triangle", "US")), ("Houston", "houston", (r"\bhouston\b", "US")),
    ("Texas", "texas", (r"\btexas\b|(?-i:, TX\b)|\baustin\b|\bdallas\b|\bhouston\b|san antonio", "US")), ("Florida", "florida", (r"\bflorida\b|(?-i:, FL\b)|\bmiami\b|orlando|\btampa\b", "US")),
    ("Toronto", "toronto", (r"toronto", "CA")), ("Vancouver", "vancouver", (r"vancouver", "CA")), ("Berlin", "berlin", (r"\bberlin\b", "DE")), ("Munich", "munich", (r"munich|münchen", "DE")),
    ("Bangalore", "bangalore", (r"bangalore|bengaluru", "IN")), ("Sydney", "sydney", (r"\bsydney\b", "AU")),
]


PLACES += [(nm, re.sub(r"[^a-z0-9]+", "-", nm.lower()).strip("-"), code) for code, nm, _, _ in COUNTRIES if code not in {r for _, _, r in PLACES if isinstance(r, str)}]


def places_of(loc):
    """Slugs of every place page a location line belongs on."""
    codes = {c for c, _ in countries_of(loc)}
    out = []
    for _, slug, rule in PLACES:
        if rule == "region":
            members, words = REGIONS[slug]
            hit = bool(codes & members) or bool(re.search(words, loc, re.I))
        elif isinstance(rule, str):
            hit = rule in codes
        else:
            hit = bool(re.search(rule[0], loc, re.I)) and (rule[1] in codes or not codes)
        if hit: out.append(slug)
    return out


ROLES = [   # (name, slug, pattern matched against the job title)
    ("Software engineer", "software-engineer", r"software (engineer|developer)|\bswe\b|\bsde\b|member of technical staff"),
    ("Backend engineer", "backend-engineer", r"back[- ]?end"), ("Frontend engineer", "frontend-engineer", r"front[- ]?end|\bui (engineer|developer)"),
    ("Full-stack engineer", "full-stack-engineer", r"full[- ]?stack"), ("Mobile engineer", "mobile-engineer", r"\bios\b|android|mobile (engineer|developer|software)|react native|flutter"),
    ("DevOps engineer", "devops-engineer", r"devops|dev ops|platform engineer|infrastructure engineer|cloud (engineer|architect)"),
    ("Site reliability engineer", "site-reliability-engineer", r"site reliability|\bsre\b"),
    ("Data engineer", "data-engineer", r"data engineer|analytics engineer|data platform"), ("Data scientist", "data-scientist", r"data scien"),
    ("Data analyst", "data-analyst", r"data analyst|business intelligence|\bbi (analyst|developer|engineer)|analytics analyst|product analyst"),
    ("Machine learning engineer", "machine-learning-engineer", r"machine learning|\bml\b|deep learning|\bmle\b|\bai (engineer|researcher|scientist)|(ai|ml|applied|nlp|vision) research|research (scientist|engineer),? (ai|ml|machine|deep|nlp|vision|llm)"),
    ("Cybersecurity", "cybersecurity", r"security (engineer|analyst|architect|researcher|operations)|appsec|infosec|penetration|cyber|threat|detection (and|&) response"),
    ("QA engineer", "qa-engineer", r"\bqa\b|quality assurance|\bsdet\b|software (development )?engineer in test|test automation|automation (test|qa)|software test"),
    ("Embedded engineer", "embedded-engineer", r"embedded (software |systems |firmware |linux |c )?(engineer|developer)|firmware"), ("Blockchain engineer", "blockchain-engineer", r"blockchain|smart contract|solidity|protocol engineer"),
    ("Engineering manager", "engineering-manager", r"engineering manager|head of engineering|director,? (of )?engineering|vp,? (of )?engineering"),
    ("Product manager", "product-manager", r"product manager|product owner|product lead\b|(head of|director,? (of )?|vp,? (of )?)product(?! (design|marketing|security|operations|engineering|sales|analytics|counsel|partnerships))"),
    ("Product designer", "product-designer", r"product designer|ux designer|ui designer|ux/ui|ui/ux|user experience|design lead|interaction designer"),
    ("Program and project manager", "program-manager", r"program manager|\btpm\b|project manager"),
    ("Solutions engineer", "solutions-engineer", r"solutions? (engineer|architect|consultant)|sales engineer|forward deployed|customer engineer"),
    ("IT support", "it-support", r"\bit (support|specialist|technician|administrator|engineer|manager|operations)|help ?desk|desktop support|systems? administrator|sysadmin"),
    ("Account executive", "account-executive", r"account executive|\bae\b"), ("Customer success manager", "customer-success-manager", r"customer success|\bcsm\b"),
    ("Marketing manager", "marketing-manager", r"marketing manager|growth (manager|marketer|lead)|head of marketing|product marketing|demand generation"),
    ("Recruiter", "recruiter", r"recruiter|recruiting|talent acquisition|sourcer|talent (partner|community|coordinator|operations)"),
]
# how each role reads in the plural ("jobs for data engineers"), and titles that belong to another profession even if a role word is in them
ROLE_PLURAL = {"Cybersecurity": "cybersecurity specialists", "IT support": "IT support specialists", "DevOps engineer": "DevOps engineers", "QA engineer": "QA engineers",
               "Program and project manager": "program and project managers"}
ROLE_OTHER = re.compile(r"\b(sales|account executive|counsel|attorney|recruiter|recruiting|marketing|paralegal)\b", re.I)
ROLE_OWN = {"Account executive", "Marketing manager", "Recruiter", "Solutions engineer", "Customer success manager"}       # roles the exclusion must not touch
# The 25 roles above came first and have every combination page. The rest of the directory (categories, more roles, plain lines,
# plurals) is in roles_info.py: add a role there and it gets its page, its place in a category and its text.
ROLE_BASE = {s_ for _, s_, _ in ROLES}
ROLES += [(r[0], r[1], r[2]) for r in roles_info.MORE_ROLES]
ROLE_PLURAL |= {nm: roles_info.INFO[s_][0] for nm, s_, _ in ROLES if s_ in roles_info.INFO}
ROLE_OWN |= {r[0] for r in roles_info.MORE_ROLES}
ROLE_NT = {r[0] for r in roles_info.MORE_ROLES if len(r) > 5}       # fields of work whose word also sits in engineering and sales titles
NOT_TECH = re.compile(roles_info.NOT_TECH, re.I)
ROLE_RX = {nm: re.compile(rx, re.I) for nm, _, rx in ROLES}
role_hit = lambda nm, rx, title: bool(ROLE_RX[nm].search(title)) and (nm in ROLE_OWN or not ROLE_OTHER.search(title)) and not (nm in ROLE_NT and NOT_TECH.search(title))
KEEP_CAP = {"German", "French", "Spanish", "Japanese", "Portuguese", "Chinese", "Italian", "Dutch", "Korean"}


def rlow(nm):
    """A role or category name inside a sentence: lower case unless it starts with an acronym or a proper name."""
    w = nm.split()[0]
    return nm if w in KEEP_CAP or sum(c.isupper() for c in w) >= 2 else nm[0].lower() + nm[1:]


def art(nm):
    w = nm.split()[0]
    if sum(c.isupper() for c in w) >= 2: return "an" if w[0] in "AEFHILMNORSX" else "a"
    return "an" if nm[0].lower() in "aeiou" else "a"
TAG_SLUG = {"C++": "cpp", "C#": "csharp", ".NET": "dotnet", "Node.js": "nodejs", "Next.js": "nextjs", "CI/CD": "ci-cd", "AML/KYC": "aml-kyc"}
URLS = []
ORG_LD = [""]
V = hashlib.md5(b"".join((ROOT / "assets" / f).read_bytes() for f in ("style.css", "site.js", "app.js", "account.js", "tools.js", "tools.css", "resume.js", "widget.js", "widgets.js"))).hexdigest()[:8]   # cache-busting version
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
FACT = {}          # one-paragraph hiring summary per company
CATMED = {}        # median advertised salary per category slug
EST = {}           # median advertised salary per (category slug, level)
PERK_SLUG = {name: slug for name, slug, _ in PERKS}
PERK_OK = set()    # perks with enough jobs to have their own page
PULSE = {}         # company -> (opened in 7 days, closed in 7 days, label)
CLOSE_DAYS = {}    # category slug -> median days a role stayed open (from closed roles)
REPOST = {}        # (company, title, location) -> date an earlier posting of the same role closed
SOURCE_NAME = {"greenhouse": "Greenhouse", "lever": "Lever", "ashby": "Ashby"}     # hiring systems the listings are read from
LONG_OPEN = 90     # days after which a posting is flagged as open unusually long
DESC_TAGS = re.compile(r"</?(?:p|ul|ol|li|h3|strong|em)>")       # the only markup a stored job description may contain
POOL_RX = re.compile(r"talent (pool|community|network|pipeline)|general (application|interest|submission|consideration)|future (opportunit|opening|role|position|consideration)|expression of interest|"
                     r"open application|speculative application|evergreen|don.?t see (a|your|the) (role|fit|position|job)|register your interest|join our talent|(^|\W)pipeline( role| req|:| -| –)|"
                     r"always (hiring|looking)|spontaneous application|unsolicited application|open call", re.I)     # titles that are a standing invitation, not one specific opening
REGION_WORDS = [("Europe", r"europe|\bemea\b|\beu\b"), ("Asia-Pacific", r"\bapac\b|asia"), ("Latin America", r"latam|latin america"), ("the Americas", r"americas"), ("North America", r"north america")]
ETYPE_LD = {"Full-time": "FULL_TIME", "Part-time": "PART_TIME", "Contract": "CONTRACTOR", "Internship": "INTERN"}
MARK = '<rect width="32" height="32" rx="8" fill="#0e0e0c"/><circle cx="16" cy="16" r="6.5" fill="#3ecf5f"/>'
GRAD = ""
LOGO = '<i class="live" aria-hidden="true"></i>'
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
    h = 0                       # same simple hash as in site.js, so avatars get the same colour everywhere
    for ch in name: h = (h * 31 + ord(ch)) % 360
    return h


LOGOS = {f.stem for f in (ROOT / "assets" / "logos").glob("*.png")} if (ROOT / "assets" / "logos").exists() else set()
LOGO_SITE = json.loads((ROOT / "logos.json").read_text()) if (ROOT / "logos.json").exists() else {}     # company -> its own site (checked by hand or by name)


def ava(name, cls=""):
    """Company avatar: the real logo when we have one, with the coloured initial underneath as a fallback."""
    letter = next((c for c in name if c.isalnum()), "?").upper()
    slug = slugify(name)
    img = f'<img src="{P}/logos/{slug}.png" alt="" loading="lazy">' if slug in LOGOS else ""
    return f'<span class="ava{" " + cls if cls else ""}{" has" if img else ""}" style="--h:{hue(name)}" aria-hidden="true">{e(letter)}{img}</span>'


def write(path, content, sitemap=True):
    f = OUT / path / "index.html" if not path.endswith((".html", ".xml", ".txt", ".json", ".svg", ".csv")) else OUT / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    if sitemap:
        URLS.append(path)


def mincss(s):
    """Small, safe stylesheet minifier: comments and layout whitespace go, quoted strings are left untouched."""
    keep = []
    def stash(m_):
        keep.append(m_.group(0)); return f"\x00{len(keep) - 1}\x00"
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r'"[^"]*"', stash, s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s*([{};,>])\s*", r"\1", s)
    s = re.sub(r";}", "}", s).strip()
    return re.sub(r"\x00(\d+)\x00", lambda m_: keep[int(m_.group(1))], s)


def tcase(s):
    """Title case that leaves existing capitals alone: "DevOps engineer" -> "DevOps Engineer"."""
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


def fit_title(t):
    """Keep the key at the start and the brand at the end, but never let a title run long."""
    if len(t) <= 65: return t
    t2 = re.sub(r" \([\d,]+ (?:open|roles?)\)", "", t)
    if len(t2) <= 65: return t2
    if " | " in t2:                                           # shorten the descriptive part, never drop the brand
        left, brand = t2.rsplit(" | ", 1)
        head_ = re.split(r" — |: ", left)[0]
        if len(head_) >= 12: left = head_
        room = 65 - len(brand) - 3
        if len(left) > room: left = left[:room + 1].rsplit(" ", 1)[0].rstrip(" ,-–—:&")
        return f"{left} | {brand}"
    return t2 if len(t2) <= 70 else t2[:68].rsplit(" ", 1)[0].rstrip(" ,-–—:&(")


def fit_desc(d):
    d = " ".join(d.split())
    if len(d) < 110: d = d.rstrip(".") + f". Collected from official company career pages and updated every hour on {SITE}."
    if len(d) > 160: d = d[:157].rsplit(" ", 1)[0].rstrip(",.;:–—") + "…"
    return d


NAV_PLUS = f'<a class="nl" href="{P}/plus/">Plus</a>' if CFG.get("plus", {}).get("live") else f'<a class="nl only-m" href="{P}/plus/">Plus</a>'      # in the top menu only once it can be bought
CRUMB_RX = re.compile(r'<div class="crumbs">(.*?)</div>', re.S)
CRUMB_A = re.compile(r'<a href="([^"]*)">(.*?)</a>')


LD_RX = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def ld_small(m_):
    try: return m_.group(1) + json.dumps(json.loads(m_.group(2)), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + m_.group(3)
    except ValueError: return m_.group(0)


def page(path, title, desc, body, head="", sitemap=True, hero="", compact=False):
    url = f"{FULL}/{path}"
    title, desc = fit_title(title), fit_desc(desc)
    if '"BreadcrumbList"' not in head:                 # every page with a visible trail carries the same trail as markup
        m_ = CRUMB_RX.search(body)
        if m_:
            parts = []
            for bit in m_.group(1).split(" / ")[1:]:
                a_ = CRUMB_A.fullmatch(bit.strip())
                parts.append((html.unescape(a_.group(2)), a_.group(1)[len(P) + 1:]) if a_ else (html.unescape(bit.strip()), ""))
            if parts: head += crumbs_ld(parts)
    head = LD_RX.sub(ld_small, head)
    write(path, f"""<!doctype html>
<html lang="en" data-base="{P}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{e(url)}"><meta property="og:site_name" content="{e(SITE)}">
<meta property="og:image" content="{FULL}/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0e0e0c">
<link rel="icon" type="image/svg+xml" href="{P}/favicon.svg"><link rel="manifest" href="{P}/manifest.json">
<link rel="alternate" type="application/rss+xml" title="{e(SITE)} — latest jobs" href="{P}/feed.xml">
<link rel="preload" href="{P}/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{P}/fonts/bricolage-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{P}/style.css?v={V}"><script>try{{var t=localStorage.getItem("hrn_theme");if(t)document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script><script src="{P}/site.js?v={V}" defer></script>{head}</head><body>
<a class="skip" href="#main">Skip to content</a><header class="site"><div class="wrap"><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><nav id="nav">
<a class="nl" href="{P}/jobs/">Jobs</a><a class="nl" href="{P}/categories/">Categories</a><a class="nl" href="{P}/companies/">Companies</a><a class="nl" href="{P}/salaries/">Salaries</a><a class="nl" href="{P}/resume/">Resume</a><a class="nl" href="{P}/tools/">Tools</a><a class="nl" href="{P}/for-you/">For you</a><a class="nl" href="{P}/my-jobs/">My jobs<span id="saved-n"></span></a><a class="nl only-m" href="{P}/remote/">Remote jobs</a>{NAV_PLUS}<a class="nl only-m" href="{P}/post-a-job/">Post a job</a></nav>
<div class="hact"><button class="icon ic-s" id="palbtn" type="button" aria-label="Quick search (Ctrl K)"></button><button class="icon ic-t" id="theme" type="button" aria-label="Switch between light and dark"></button><a class="btn" href="{P}/post-a-job/">Post a job</a>
<button class="icon ic-m burger" id="menu" type="button" aria-label="Menu" aria-expanded="false"></button></div></div></header>
{hero}<main class="wrap" id="main">{body}</main>
{MINI_FOOT if compact else FULL_FOOT()}
</body></html>""", sitemap)


def FULL_FOOT():
    return f"""<footer><div class="wrap"><div class="fcols">
<div><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><p>Job boards fill up with listings that closed weeks ago. Every role here comes from the company’s own careers page and is re-checked every hour.</p></div>
<div><p class="fhd">Find jobs</p><ul><li><a href="{P}/jobs/">All jobs</a></li><li><a href="{P}/remote/">Remote jobs</a></li><li><a href="{P}/new/">New jobs</a></li><li><a href="{P}/entry-level/">Entry-level</a></li><li><a href="{P}/with-salary/">Salary listed</a></li><li><a href="{P}/crypto/">Crypto &amp; web3 jobs</a></li><li><a href="{P}/for-you/">Jobs for you</a></li><li><a href="{P}/my-jobs/">My jobs</a></li></ul></div>
<div><p class="fhd">Browse</p><ul><li><a href="{P}/categories/">Job categories</a></li><li><a href="{P}/roles/">Roles A to Z</a></li><li><a href="{P}/skills/">Skills</a></li><li><a href="{P}/locations/">Locations</a></li><li><a href="{P}/companies/">Companies</a></li><li><a href="{P}/perks/">Perks</a></li>{FOOT["cats"]}</ul></div>
<div><p class="fhd">Tools and data</p><ul><li><a href="{P}/tools/">Free tools</a></li><li><a href="{P}/resume/">Resume builder</a></li><li><a href="{P}/salaries/">Salaries</a></li><li><a href="{P}/compare/">Compare skills</a></li><li><a href="{P}/trends/">Hiring trends</a></li><li><a href="{P}/reports/">Monthly reports</a></li><li><a href="{P}/insights/">Rankings</a></li><li><a href="{P}/status/">Is the data fresh?</a></li></ul></div>
<div><p class="fhd">Employers and sites</p><ul><li><a href="{P}/post-a-job/">Post a job</a></li><li><a href="{P}/widgets/">Jobs for your website</a></li><li><a href="{P}/api/">Data for developers (API)</a></li><li><a href="{P}/feeds/">Job feeds for channels (RSS)</a></li><li><a href="{P}/partners/">Partners</a></li><li><a href="{P}/media-kit/">Media kit</a></li><li><a href="{P}/plus/">Plus</a></li></ul></div>
<div><p class="fhd">About</p><ul><li><a href="{P}/about/">About</a></li><li><a href="{P}/promise/">Our promise</a></li><li><a href="{P}/ahead/">What is new here</a></li><li><a href="{P}/methodology/">How it works</a></li><li><a href="{P}/glossary/">Glossary</a></li><li><a href="{P}/safety/">Job offer safety</a></li><li><a href="{P}/archive/">Closed jobs archive</a></li><li><a href="{P}/privacy/">Privacy</a></li><li><a href="{P}/terms/">Terms</a></li></ul></div>
</div>{FOOT.get("pop", "")}<p class="fine">© {TODAY[:4]} {e(SITE)}. Listings come from companies' official careers pages. You always apply on the employer's own site.</p></div></footer>"""


def age(iso):
    """Short age label for a posting date: Today, 3d, 2w, 4mo. Second value: is it fresh (2 days or less)?"""
    try:
        days = (datetime.date.today() - datetime.date.fromisoformat(iso[:10])).days
    except Exception:
        return "", False
    days = max(days, 0)
    label = "Today" if days == 0 else f"{days}d" if days < 14 else f"{days // 7}w" if days < 60 else f"{days // 30}mo"
    return label, days <= 2


# Exact posting times. collect.py keeps "posted_at" (UTC, to the second) when the employer's feed gives a time; jobs collected before
# that have none and stay at day precision everywhere. All values here are seconds since 1970.
NOW = int(datetime.datetime.now(datetime.timezone.utc).timestamp())      # the moment of this build
WEEK = 7 * 86400                                                         # exact times are written out only for postings younger than this


def exact(j):
    """The exact posting time of a job, or 0 when only the day is known."""
    try:
        return int(datetime.datetime.fromisoformat(j["posted_at"].replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def stamp(j):
    """When a job was posted, for sorting newest first: the exact time when there is one, otherwise the start of its day."""
    try:
        return exact(j) or int(datetime.datetime.fromisoformat((j["posted"] or j["first_seen"])[:10] + "T00:00:00+00:00").timestamp())
    except Exception:
        return 0


def when(j):
    """What a job's <time> carries. An open job under a week old with an exact time gets the full timestamp and data-t:
    freshen() in site.js turns that into "20 min" or "3 h" while the posting is under a day old. Every other job keeps the day."""
    t = j.get("t") or 0
    return f'datetime="{j["posted_at"]}" data-t="{t}"' if t and j["active"] and NOW - t < WEEK else f'datetime="{j["posted"]}"'


def card(j, extra=0):
    b = []
    if j["featured"]: b.append('<span class="pill acc">Featured</span>')
    if not j["active"]: b.append('<span class="pill">Closed</span>')
    if j["remote"]: b.append('<span class="pill ok">Remote</span>')
    if j["level"]: b.append(f'<span class="pill">{e(j["level"])}</span>')
    b += [f'<span class="pill">{e(t)}</span>' for t in j["tags"][:3]]
    loc = j["location"] if len(j["location"]) <= 60 else j["location"][:57].rstrip(" ,;") + "…"
    sub = e(j["company"]) + (f" · {e(loc)}" if loc else "") + (f" · +{extra} more location{'s' if extra > 1 else ''}" if extra else "")
    label, fresh = age(j["posted"])
    return (f'<li class="job{" feat" if j["featured"] else ""}"><a href="{P}/job/{j["slug"]}/">{ava(j["company"])}'
            f'<span><span class="jt">{e(j["title"])}</span><span class="js">{sub}</span></span>'
            f'<span class="jr"><span class="jp{"" if j["salary"] else " none"}">{e(j["salary"][:28]) if j["salary"] else "—"}</span><span class="pills">{"".join(b)}</span><time {when(j)}{" class=\"new\"" if fresh and j["active"] else ""}>{label}</time></span></a></li>')


def tile(url, name, count, avatar=False):
    return f'<li><a class="tile" href="{P}/{url}">{ava(name, "sm") if avatar else ""}<span class="n">{e(name)}</span><span class="c">{count:,}</span></a></li>'


def section(title, inner, link=None, sid=""):
    more = f'<a href="{P}/{link[0]}">{e(link[1])}</a>' if link else ""
    return f'<section class="sec"{f" id={chr(34)}{sid}{chr(34)}" if sid else ""}><div class="sec-head"><h2>{e(title)}</h2>{more}</div>{inner}</section>'


def order(jobs):
    return sorted(jobs, key=lambda j: (not j.get("pinned"), not j["featured"], -(j.get("ts") or stamp(j))))


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


def collapse(jobs):
    """The same role posted once per city becomes one row: [(job, number of extra postings)]."""
    first, out = {}, []
    for j in jobs:
        k = (j["company"], j["title"])
        if k in first: out[first[k]][1] += 1
        else:
            first[k] = len(out); out.append([j, 0])
    return out


def crumbs_ld(parts):
    items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": FULL + "/"}]
    items += [{"@type": "ListItem", "position": i + 2, "name": n, **({"item": f"{FULL}/{u}"} if u else {})} for i, (n, u) in enumerate(parts)]
    return ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items},
                                                                 ensure_ascii=False).replace("</", "<\\/") + "</script>")


def rel(links):
    """Row of related listing links: [(path, label, count)], biggest first."""
    links = sorted(links, key=lambda x: -x[2])[:14]
    return ('<div class="rel"><span>Related:</span>' + "".join(f'<a href="{P}/{u}">{e(t)}</a>' for u, t, _ in links) + "</div>") if links else ""


def crumbs(*parts):
    items = [f'<a href="{P}/">Home</a>'] + [f'<a href="{P}/{u}">{e(n)}</a>' if u else e(n) for n, u in parts]
    return f'<div class="crumbs">{" / ".join(items)}</div>'


def rss_date(j):
    try: return "<pubDate>" + format_datetime(datetime.datetime.fromisoformat((j["posted"] or j["first_seen"])[:10]).replace(tzinfo=datetime.timezone.utc)) + "</pubDate>"
    except Exception: return ""


def rss(path, title, link, jobs):
    now = format_datetime(datetime.datetime.now(datetime.timezone.utc))
    items = "".join(
        f"<item><title>{e(j['title'])} at {e(j['company'])}</title><link>{FULL}/job/{j['slug']}/</link><guid>{FULL}/job/{j['slug']}/</guid>{rss_date(j)}"
        f"<description>{e(((j['location'] + '. ') if j['location'] else '') + j['excerpt'])}</description></item>" for j in order(jobs)[:100])
    write(path, f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{e(title)}</title><link>{FULL}/{link}</link>'
                f"<description>{e(title)}</description><lastBuildDate>{now}</lastBuildDate>{items}</channel></rss>", sitemap=False)


def faq_for(label, jobs, first=None):
    """Questions people actually ask about a set of jobs, answered from today's data. Returns (html, json-ld)."""
    if len(jobs) < 5: return "", ""
    n_, r = len(jobs), sum(j["remote"] for j in jobs)
    week = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    new7 = sum(1 for j in jobs if (j["posted"] or "") >= week)
    top = Counter(j["company"] for j in jobs).most_common(5)
    mids = sorted((lo + hi) / 2 for j in jobs if j.get("usd") for lo, hi in [j["usd"]])
    cap = label[0].upper() + label[1:]
    n_co = len(set(j["company"] for j in jobs))
    qa = [(f"How many {label} are open right now?",
           f"There are {n_:,} open {label}{f' at {n_co:,} companies' if n_co > 1 else ''} on {SITE} as of {fdate(TODAY)}. {new7:,} of them were posted in the last seven days. The list is rebuilt every hour from the employers' own careers pages.")]
    if first: qa.insert(0, first)
    if len(top) > 1:
        qa.append((f"Which companies have the most {label}?",
                   "Right now the most openings are at " + ", ".join(f"{c} ({k:,})" for c, k in top[:-1]) + f" and {top[-1][0]} ({top[-1][1]:,}). The ranking changes as companies open and close roles."))
    if "remote" in label.lower():
        aw = sum(1 for j in jobs if j.get("anywhere"))
        qa.append((f"Can I do {label} from any country?",
                   (f"Mostly not. {aw:,} of the {n_:,} open {label} are listed as open worldwide; the rest are limited to certain countries or time zones, so check the location line of each job." if aw else
                    f"Mostly not. None of the {n_:,} open {label} is listed as open worldwide today; each is limited to certain countries or time zones, named in its location line.")))
    else:
        qa.append((f"Are there remote {label}?",
                   (f"{r:,} of the {n_:,} open {label} ({100 * r / n_:.0f}%) are listed as remote. Remote roles are often limited to certain countries or time zones, so check the location line of each job."
                    if r else f"None of the {n_:,} open {label} are listed as remote at the moment. Remote roles appear here as soon as employers post them.")))
    if len(mids) >= 15:
        qa.append((f"What do {label} pay?",
                   f"The median advertised salary is {money(median(mids))}, based on {len(mids):,} open roles that publish a yearly US-dollar range. The middle half of those roles advertise between "
                   f"{money(mids[len(mids) // 4])} and {money(mids[min(len(mids) - 1, 3 * len(mids) // 4)])}. These are advertised ranges, not verified pay."))
    qa.append((f"How do I apply for {label}?",
               f"Open a job and press “Apply on company site”. You go straight to the employer's own careers page and apply there. {SITE} needs no account and charges nothing for applying."))
    html_ = '<dl class="qa">' + "".join(f"<div><dt>{e(q)}</dt><dd>{e(a_)}</dd></div>" for q, a_ in qa) + "</dl>"
    ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    return section(f"Questions about {label}", html_), ld


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


CAT_ACCENT = {}                       # sections once had their own colours; the site now keeps one green everywhere
HUB = {"roles": {}, "week": ""}       # role slug -> (name, ids of its jobs); filled in main()


def hub_stats(js):
    """The headline numbers of a set of jobs, as a row of figures."""
    k = len(js)
    if k < 20: return ""
    mids = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in js if j.get("usd"))
    cells = [(f"{k:,}", "open roles"), (f"{sum(1 for j in js if (j['posted'] or '') >= HUB['week']):,}", "posted in the last 7 days"),
             (f"{100 * sum(j['remote'] for j in js) / k:.0f}%", "remote"), (f"{len({j['company'] for j in js}):,}", "companies hiring")]
    if len(mids) >= 30: cells.append((money(median(mids)), f'<a href="{P}/glossary/#median">median</a> advertised salary'))
    return ('<p class="stamp">' + " · ".join(f"<b>{a}</b> {b}" for a, b in cells)
            + f' · <a href="{P}/methodology/">checked {fdate(TODAY, False)} against employer career pages</a></p>')


def hub_sections(label, js, skip=""):
    """Who hires, which skills and roles, where, and what it pays at each level: the same set of jobs seen from five sides."""
    k = len(js)
    if k < 40: return "", ""
    top, out, ids = [], [], {j["id"] for j in js}
    bars = lambda rows_: '<div class="hbars">' + "".join(
        f'<a href="{P}/{u}"><span class="hn">{e(nm)}</span><span class="hb"><i style="width:{max(3, round(100 * c / rows_[0][2]))}%"></i></span><span class="hc">{c:,} · {100 * c / k:.0f}%</span></a>' for u, nm, c in rows_) + "</div>"
    if skip != "skills":
        sk = Counter(t for j in js for t in j["tags"]).most_common(7)
        if len(sk) >= 4: top.append(f'<div><h2 class="h2s">Skills asked for in {e(label)}</h2>' + bars([(f"skills/{TAG_SLUG.get(t, slugify(t))}/", t, c) for t, c in sk]) + "</div>")
    if skip != "roles":
        rl = sorted(((s_, nm, len(ids & rid)) for s_, (nm, rid) in HUB["roles"].items()), key=lambda x: -x[2])
        rl = [x for x in rl if x[2] >= 8][:7]
        if len(rl) >= 3: top.append(f'<div><h2 class="h2s">Job titles in {e(label)}</h2>' + bars([(f"roles/{s_}/", nm, c) for s_, nm, c in rl]) + "</div>")
    co = Counter(j["company"] for j in js).most_common(12)
    if len(co) >= 4: out.append(section(f"Who is hiring for {label}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, n_, True) for c, n_ in co) + "</ul>"))
    if skip != "places":
        pname = {slug: name.removeprefix("the ") for name, slug, _ in PLACES}
        pl = [(p_, c) for p_, c in Counter(p_ for j in js for p_ in j["places"]).most_common(40) if p_ in HUB.get("live", ())][:10]
        if len(pl) >= 4: out.append(section(f"Where {label} are", '<ul class="tiles">' + "".join(tile(f"locations/{p_}/", pname[p_], c) for p_, c in pl) + "</ul>"
                                            + '<p class="note">A role that lists several places is counted in each of them.</p>'))
    lv = defaultdict(list)
    for j in js:
        if j.get("usd"): lv[j["level"] or "No level in the title"].append((j["usd"][0] + j["usd"][1]) / 2)
    pay = [(nm, median(v), len(v)) for nm, v in lv.items() if len(v) >= 15]
    if len(pay) >= 2:
        order_ = {"Intern": 0, "Junior": 1, "No level in the title": 2, "Senior": 3, "Lead": 4}
        out.append(section(f"What {label} pay, by level", '<div class="tablewrap"><table><tr><th>Level in the title</th><th>Median advertised salary</th><th>Roles counted</th></tr>'
                           + "".join(f"<tr><td>{e(nm)}</td><td><strong>{money(md)}</strong></td><td>{c:,}</td></tr>" for nm, md, c in sorted(pay, key=lambda x: order_.get(x[0], 9)))
                           + '</table></div><p class="note">Medians of the midpoints of advertised yearly US-dollar ranges; a level needs at least 15 such roles. Advertised, not verified pay.</p>'))
    glance = (f'<div class="hubgrid">{"".join(top)}</div><p class="note">Bars show the share of these {k:,} roles; one role can count in several rows.</p>' if top else "")
    return glance, "".join(out)


def auto_more(path, h1):
    """The search filters that reproduce a list page, for its "see all in search" link."""
    seg = path.strip("/").split("/")
    q = lambda v: quote(v)
    if seg[0] == "jobs" and len(seg) == 2: return f"cat={seg[1]}"
    if seg == ["remote"]: return "remote=1"
    if seg[0] == "remote" and len(seg) == 2 and seg[1] in CAT: return f"remote=1&cat={seg[1]}"
    if seg == ["crypto"]: return "crypto=1"
    if seg == ["crypto", "remote"]: return "crypto=1&remote=1"
    if seg[0] == "crypto" and len(seg) == 2: return f"crypto=1&cat={seg[1]}"
    if seg == ["with-salary"]: return "salary=1"
    if seg == ["entry-level"]: return "entry=1"
    if seg == ["new"]: return "age=3"
    if seg == ["work-from-anywhere"]: return "any=1&remote=1"
    if seg[0] == "locations" and len(seg) == 2: return f"loc={seg[1]}"
    if seg[0] == "skills" and len(seg) == 2 and h1.endswith(" jobs in tech"): return f"skills={q(h1[:-13])}"
    if seg[0] == "roles" and len(seg) == 2 and h1.endswith(" jobs"): return f"q={q(h1[:-5])}"
    if seg[0] == "perks" and len(seg) == 2: return next((f"perk={q(nm)}" for nm, sl, _ in PERKS if sl == seg[1]), "")
    return {"contract": "etype=Contract", "part-time": "etype=Part-time", "internships": "etype=Internship"}.get(seg[0], "") if len(seg) == 1 else ""


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra="", feed=False, head_html=None, after="", max_pages=None, more=None, faq=None, hub="", accent=None, list_title="", faq_first=None):
    jobs = order(jobs)
    if feed: rss(f"{path}feed.xml", f"{h1} — {SITE}", path, jobs)
    rows = collapse(jobs)
    total = len(rows)
    if max_pages is None and head_html is None: max_pages = 5       # deep pages of a topic list add weight, not visitors; company pages keep everything
    if more is None: more = auto_more(path, h1)       # False: the list has no equivalent in the search filters
    if max_pages: rows = rows[:per * max_pages]
    pages = max(1, -(-len(rows) // per))
    note = ((f'<p class="note">Showing the newest {len(rows):,}. <a href="{P}/jobs/{"?" + more if more else ""}">See all {len(jobs):,} in search</a></p>' if more is not False
             else f'<p class="note">Showing the newest {len(rows):,} of {total:,}. The <a href="{P}/jobs/">search</a> looks through all of them by title, place and pay.</p>')      # no search filter reproduces this list
            if total > len(rows) else "")
    ld = crumbs_ld(list(trail) + [(h1, "")]) if head_html is None else ""
    if accent: ld += f"<style>:root:root:root{{--hl:{accent};--accent-soft:color-mix(in srgb,{accent} 22%,var(--card))}}</style>"      # each section of the site has its own colour
    faq_html, faq_ld = faq_for(faq, jobs, faq_first) if faq else ("", "")
    for n in range(1, pages + 1):
        chunk = rows[(n - 1) * per:n * per]
        top = head_html if head_html is not None else (crumbs(*trail, (h1, "")) + f"<h1>{e(h1)}</h1>" + (f'<p class="lead">{intro}</p>' if intro and n == 1 else ""))
        body = (top + (extra if n == 1 else "") + (f'<div class="sec-head lst"><h2>{e(list_title)}</h2></div>' if list_title and n == 1 and chunk else "")
                + (f'<ul class="jobs">{"".join(card(j, x) for j, x in chunk)}</ul>' if chunk else '<p class="lead">Nothing here today. The list is rebuilt every hour.</p>')
                + pager_html(path, n, pages) + note + ((hub + faq_html + after) if n == 1 else ""))
        if n == 1: page(path, title, desc, body, head=ld + faq_ld)
        else: page(f"{path}{n}/", f"{title.rsplit(' | ', 1)[0]}, page {n} | {SITE}", f"Page {n} of {pages}. {desc}", body, head=ld, sitemap=False)


def intro_for(jobs, pre="", post="", hub=False):
    if not jobs: return ""
    r = sum(j["remote"] for j in jobs)
    names = [c for c, _ in Counter(j["company"] for j in jobs).most_common(5)]
    top = ", ".join(names)
    if hub and len(jobs) >= 20 and len(names) >= 3:
        return f"{e(', '.join(names[:-1]))} and {e(names[-1])} have the most open {pre}roles{post} right now."
    mids = [(lo + hi) / 2 for j in jobs if j.get("usd") for lo, hi in [j["usd"]]]
    who = (e(", ".join(names[:-1])) + " and " + e(names[-1]) + " have the most. ") if len(names) > 1 else (e(top) + " has them all. ")
    bits = ([f"{r:,} {'is' if r == 1 else 'are'} remote"] if 0 < r < len(jobs) else []) + ([f"the median advertised salary is {money(median(mids))}"] if len(mids) >= 15 else [])
    tail = " and ".join(bits)
    return f"{roles(len(jobs), 'open ' + pre + 'role')}{post} as of {fdate(TODAY)}. {who}" + (tail[0].upper() + tail[1:] + "." if tail else "")


def microdata(props):
    """The same facts as the JSON-LD block, written as microdata tags. Used when the description is long: marking up the visible
    text itself keeps the page from carrying the whole description twice."""
    out = []
    for k, v in props.items():
        if k.startswith("@") or k == "description": continue
        if isinstance(v, list): out += [f'<span itemprop="{k}" itemscope itemtype="https://schema.org/{x["@type"]}">{microdata(x)}</span>' for x in v]
        elif isinstance(v, dict): out.append(f'<span itemprop="{k}" itemscope itemtype="https://schema.org/{v["@type"]}">{microdata(v)}</span>')
        elif isinstance(v, bool): out.append(f'<meta itemprop="{k}" content="{"true" if v else "false"}">')
        else: out.append(f'<meta itemprop="{k}" content="{e(str(v))}">')
    return "".join(out)


def job_page(j, active_by_cat):
    canonical = f"{FULL}/job/{j['slug']}/"
    # the full description comes from the collector already reduced to a few plain tags; anything else falls back to the excerpt
    full = j.get("desc") or ""
    # a US-dollar estimate only makes sense for US roles, and intern pay is not comparable with salaried roles
    est_ok = j["level"] != "Intern" and j["cat"] != OTHER[0] and (not j["location"] or any(c == "US" for c, _ in countries_of(j["location"])))
    if full and ("<" in DESC_TAGS.sub("", full) or not j["active"]): full = ""
    comp_url = f'{P}/companies/{slugify(j["company"])}/'
    rows = [("Company", f'<a href="{comp_url}">{e(j["company"])}</a>')]
    if j["location"]: rows.append(("Location", e(j["location"])))
    if j["remote"]:
        lands_r = countries_of(j["location"]) if j["location"] else []
        scope = ("worldwide" if j.get("anywhere") else " or ".join(nm for _, nm in lands_r[:4]) if lands_r else next((nm for nm, rx in REGION_WORDS if re.search(rx, j["location"], re.I)), ""))
        rows.append(("Workplace", f"Remote, {e(scope)}" if scope else 'Remote<br><span class="note">The posting does not say from which countries. Check before you apply.</span>'))
    elif j.get("hybrid"):
        rows.append(("Workplace", "Hybrid: part of the week in the office"))
    if j.get("years"):
        odd = j["entry"] and j["years"] >= 3
        rows.append(("Experience asked", f"{j['years']}+ years" + ('<br><span class="note">An entry-level title that asks for several years of experience.</span>' if odd else "")))
    if j["pool"]: rows.append(("Kind of posting", 'Talent pool<br><span class="note">A standing invitation to apply, not one specific opening.</span>'))
    rows.append(("Category", f'<a href="{P}/jobs/{j["cat"]}/">{e(CAT[j["cat"]])}</a>'))
    if j["level"]: rows.append(("Level", e(j["level"])))
    if j.get("etype"): rows.append(("Type", e(j["etype"])))
    if j["salary"]:
        ctx = ""            # the comparison with the category median is drawn as a bar above the Apply button
        if j.get("usd") and j["usd"][1] >= 2 * j["usd"][0]:
            ctx += f'<br><span class="note">A wide range: the top is {j["usd"][1] / j["usd"][0]:.1f} times the bottom. Ask early where this role sits in it.</span>'
        rows.append(("Salary", e(j["salary"]) + ctx))
    elif j["active"] and est_ok and (EST.get((j["cat"], j["level"])) or CATMED.get(j["cat"])):
        est = EST.get((j["cat"], j["level"])) or CATMED[j["cat"]]
        kind = (j["level"] + " " if EST.get((j["cat"], j["level"])) and j["level"] else "") + CAT[j["cat"]]
        rows.append(("Salary", f'Not listed<br><span class="note">Similar {e(kind)} roles advertise a median of {money(est)}. <a href="{P}/salaries/">Salary data</a></span>'))
    if j["posted"]:
        t = j.get("t") or 0
        # With an exact time from the feed the date carries it, and a posting under a day old gets a second line that freshen() in site.js
        # fills in: "35 minutes ago". It is empty in the file on purpose: a page built an hour ago must not state an age.
        rows.append(("Posted", (f'<time datetime="{j["posted_at"]}">{fdate(j["posted"])}</time>' if t else fdate(j["posted"]))
                     + (f'<br><time {when(j)} data-long></time>' if t and j["active"] and NOW - t < 86400 else "")))
    if j["active"] and j["posted"]:
        try:
            days_open = max(0, (datetime.date.today() - datetime.date.fromisoformat(j["posted"][:10])).days)
            hint = (f'<br><span class="note">Similar {e(CAT[j["cat"]])} roles stayed open for a median of {CLOSE_DAYS[j["cat"]]} days</span>' if j["cat"] in CLOSE_DAYS else "")
            if days_open >= LONG_OPEN:
                hint = ('<br><span class="note">Open much longer than most roles. Some employers keep a posting up all year to collect applications: '
                        "it is fair to ask the recruiter whether this seat is being filled now.</span>")
            rows.append(("Open for", ("Posted today" if days_open == 0 else f"{days_open} day{'s' if days_open != 1 else ''}") + hint))
        except Exception:
            days_open = 0
    else:
        days_open = 0
    again = REPOST.get((j["company"], j["title"].lower(), j["location"].lower())) if j["active"] else None
    if again and again < (j.get("first_seen") or ""): rows.append(("History", f"Posted again: an earlier posting of this role closed on {fdate(again)}"))
    if j["active"] and j.get("last_seen"): rows.append(("Last checked", fdate(j["last_seen"])))
    ats = j["id"].split("-", 1)[0]
    if j["active"]:
        rows.append(("Source", (f"{e(j['company'])}’s own posting, read from {SOURCE_NAME[ats]}, the hiring software it uses" if ats in SOURCE_NAME else "Posted here by the employer; the link was checked" if j.get("direct")
                                else f"{e(j['company'])}’s own posting")))
    meta = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    pills = []
    if not j["active"]: pills.append('<span class="pill">Closed</span>')
    if j["remote"]: pills.append('<span class="pill ok">Remote</span>')
    elif j.get("hybrid"): pills.append('<span class="pill">Hybrid</span>')
    if j["salary"]: pills.append(f'<span class="pill sal">{e(j["salary"])}</span>')
    if days_open >= LONG_OPEN: pills.append(f'<span class="pill warn">Open {days_open} days</span>')
    if j["pool"]: pills.append('<span class="pill warn">Talent pool</span>')
    pills += [(f'<a class="pill perk" href="{P}/perks/{PERK_SLUG[x]}/">{e(x)}</a>' if x in PERK_OK else f'<span class="pill perk">{e(x)}</span>') for x in j.get("perks", []) if x in PERK_SLUG]
    if j["level"]: pills.append(f'<span class="pill">{e(j["level"])}</span>')
    pills += [f'<a class="pill" href="{P}/skills/{TAG_SLUG.get(t, slugify(t))}/">{e(t)}</a>' for t in j["tags"]]
    head = ""
    if j["active"]:
        org = {"@type": "Organization", "name": j["company"]}
        if LOGO_SITE.get(j["company"]): org["sameAs"] = "https://" + LOGO_SITE[j["company"]]
        if slugify(j["company"]) in LOGOS: org["logo"] = f'{FULL}/logos/{slugify(j["company"])}.png'
        ld = {"@context": "https://schema.org", "@type": "JobPosting", "title": j["title"], "description": j["excerpt"] or j["title"],
              "datePosted": j["posted"] or j["first_seen"], "hiringOrganization": org, "identifier": {"@type": "PropertyValue", "name": j["company"], "value": j["id"]},
              "directApply": False, "url": canonical}
        if j.get("usd"):
            ld["baseSalary"] = {"@type": "MonetaryAmount", "currency": "USD",
                                "value": {"@type": "QuantitativeValue", "minValue": int(j["usd"][0]), "maxValue": int(j["usd"][1]), "unitText": "YEAR"}}
        if j["location"]:
            spots = []                                        # one Place per location the posting lists, each with its own country
            for part in [x.strip(" ,-–") for x in re.split(r";|\||•", j["location"]) if x.strip(" ,-–")][:6]:
                here = countries_of(part)
                spots.append({"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": part, **({"addressCountry": here[0][0]} if len(here) == 1 else {})}})
            if spots: ld["jobLocation"] = spots[0] if len(spots) == 1 else spots
        if j["remote"]:
            ld["jobLocationType"] = "TELECOMMUTE"
            lands = countries_of(j["location"]) if j["location"] else []
            if lands: ld["applicantLocationRequirements"] = [{"@type": "Country", "name": nm} for _, nm in lands][:8] if len(lands) > 1 else {"@type": "Country", "name": lands[0][1]}
        if j.get("etype") in ETYPE_LD:
            ld["employmentType"] = ETYPE_LD[j["etype"]]
        if full: head, micro = "", microdata(ld)          # description is marked up in place, see microdata()
        else: head, micro = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>", ""
        host_ = re.sub(r"^www\.", "", re.sub(r"^https?://([^/?#]+).*$", r"\1", j["url"] or "")).lower()
        apply_btn = (f'<a class="btn primary lg" id="apply" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Apply on company site</a>'
                     + (f'<p class="note goes">Opens <b>{e(host_)}</b></p>' if host_ and "/" not in host_ and " " not in host_ else "")
                     + '<p class="note" id="apply-hint" hidden>Applied? Mark it below to keep track of it in My jobs.</p>')
        banner = ""
    else:
        apply_btn = f'<a class="btn lg" href="{P}/jobs/{j["cat"]}/">See open {e(CAT[j["cat"]])} jobs</a>'
        banner = f'<div class="banner">This job closed{" on " + fdate(j["closed"]) if j.get("closed") else ""}. The page stays here for reference; open roles of the same kind are one click away.</div>'
    head += crumbs_ld([(CAT[j["cat"]], f"jobs/{j['cat']}/"), (j["title"], "")])
    same = [x for x in SIM["comp"].get((j["company"], j["cat"]), []) if x["id"] != j["id"]][:1]
    rest = [x for x in SIM["cat"].get(j["cat"], []) if x["id"] != j["id"] and x["company"] != j["company"]][:3 - len(same)]
    similar = same + rest if j["active"] else []   # closed jobs stay light: the archive only grows
    sim = section(f"Similar {CAT[j['cat']]} jobs", f'<ul class="jobs">{"".join(card(x) for x in similar)}</ul>', (f"jobs/{j['cat']}/", f"All {CAT[j['cat']]} jobs")) if similar else ""
    loc_ = j["location"]
    placeless = bool(re.match(r"\s*(remote|hybrid|distributed|anywhere|worldwide|global|in-office|multiple|blank)", loc_, re.I))
    where = ((f" ({e(loc_)})" if placeless else f" in {e(loc_)}") if loc_ else "") + (" (remote)" if j["remote"] and "remote" not in loc_.lower() else " (hybrid)" if j.get("hybrid") and "hybrid" not in loc_.lower() else "")
    kind_ = "" if j["cat"] == OTHER[0] else CAT[j["cat"]] + " "
    if j["active"]:
        pay_line = (f" The posting gives a salary of {e(j['salary'])}." if j["salary"] else
                    f" The posting gives no salary; similar roles in the United States advertise a median of {money(EST.get((j['cat'], j['level'])) or CATMED[j['cat']])}."
                    if est_ok and (EST.get((j["cat"], j["level"])) or CATMED.get(j["cat"])) else "")
        tldr = (f'<p class="tldr"><strong>{e(j["title"])}</strong> is open at {e(j["company"])}{where}.{pay_line}'
                + (f' Posted on {fdate(j["posted"])}' if j["posted"] else " It is")
                + (f'{", and" if j["posted"] else ""} still on {e(j["company"])}’s careers page when we last checked, on {fdate(j["last_seen"])}.' if j.get("last_seen") else (". It is open now." if j["posted"] else " open now.")) + "</p>")
    else:
        tldr = (f'<p class="tldr"><strong>{e(j["title"])}</strong> at {e(j["company"])}{where} is closed. '
                f'{"It closed on " + fdate(j["closed"]) if j.get("closed") else "The employer took it down"} and it no longer takes applications.</p>')
    about = tldr + (f'<div itemscope itemtype="https://schema.org/JobPosting">{micro}<h2>About the role</h2>'
                    f'<div class="prose desc" itemprop="description">{full}</div></div>'
                    f'<p class="note">The employer’s own description, as published on {e(j["company"])}’s careers page.</p>' if full else
                    f'<h2>About the role</h2><div class="prose"><p>{e(j["excerpt"])}</p></div><p class="note">The opening lines of the posting. The rest is on {e(j["company"])}’s careers page.</p>'
                    if j["excerpt"] else "")
    if FACT.get(j["company"]):
        about += f'<h2 class="h2s">Hiring at {e(j["company"])}</h2><div class="prose"><p>{FACT[j["company"]]} <a href="{comp_url}">See all its roles</a></p></div>'
    # Pay at a glance: the range from the posting on a scale, with the median of its category marked
    paybar = ""
    if j["active"] and j.get("usd") and j["cat"] in CATMED and j["cat"] != OTHER[0] and j["usd"][1] >= j["usd"][0] > 0:
        lo_, hi_ = j["usd"]; med_ = CATMED[j["cat"]]
        a_, b_ = min(lo_, med_) * 0.85, max(hi_, med_) * 1.15
        pos_ = lambda v: max(0.0, min(100.0, 100 * (v - a_) / (b_ - a_)))
        mid_ = (lo_ + hi_) / 2
        verdict = "above" if mid_ > med_ * 1.05 else "below" if mid_ < med_ * 0.95 else "close to"
        paybar = (f'<div class="paybar"><p class="pb-h"><b>{e(j["salary"])}</b><span>stated in the posting</span></p>'
                  f'<div class="pb-t" aria-hidden="true"><i style="left:{pos_(lo_):.1f}%;width:{max(1.5, pos_(hi_) - pos_(lo_)):.1f}%"></i><u style="left:{pos_(med_):.1f}%"></u></div>'
                  f'<p class="pb-s">The middle of this range is {verdict} the median for {e(CAT[j["cat"]])} roles, {money(med_)} (the mark on the line).</p></div>')
    data = f'data-slug="{j["slug"]}" data-title="{e(j["title"])}" data-company="{e(j["company"])}"'
    more_roles = OPEN[j["company"]] - (1 if j["active"] else 0)
    glance = (f'<p class="note"><a href="{comp_url}">{roles(more_roles, "more open role")} at {e(j["company"])}</a></p>' if more_roles > 0 else "")
    save_btn = ((f'<div class="sideact"><button class="btn ghost" id="save" type="button" {data}>Save job</button>'
                 f'<button class="btn ghost" id="applied" type="button">Mark as applied</button></div>'
                 f'<p class="note">You apply on the employer’s own page, free.{" This job was posted here by the employer; the link was checked when it was published." if j.get("direct") else ""}</p>'
                 '<p class="share" id="share"></p>'
                 f'<p class="note"><a href="{P}/safety/">How to check that a job offer is real</a>'
                 + (f' · <a href="https://t.me/{e(CFG["contact_telegram"])}" rel="nofollow noopener">Report a problem with this listing</a>' if CFG.get("contact_telegram") else "") + "</p>") if j["active"] else "") + glance
    loc = f" · {e(j['location'])}" if j["location"] else ""
    body = (crumbs((CAT[j["cat"]], f"jobs/{j['cat']}/"), (j["title"], ""))
            + f'<div class="jhead">{ava(j["company"], "lg")}<div><h1>{e(j["title"])}</h1><span class="js"><a href="{comp_url}">{e(j["company"])}</a>{loc}</span>'
            + f'<div class="pills">{"".join(pills)}</div>'
            + (f'<p class="note" id="match" data-tags="{e("|".join(j["tags"]))}" hidden></p>' if j["tags"] and j["active"] else "") + f"</div></div>{banner}"
            + f'<div class="cols"><article>{about}{sim}</article><aside class="side card">{paybar}{apply_btn}{save_btn.split("</div>", 1)[0] + "</div>" if '<div class="sideact">' in save_btn else ""}<dl class="meta">{meta}</dl>{save_btn.split("</div>", 1)[1] if '<div class="sideact">' in save_btn else save_btn}</aside></div>'
            + (f'<div class="mbar"><a class="btn primary" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Apply on company site</a></div>' if j["active"] else ""))
    where = j["location"] or ("Remote" if j["remote"] else "")
    title = f"{j['title']} at {j['company']}"
    place_ = re.split(r";|\||•", j["location"])[0].strip(" ,-–") if j["location"] else ""
    if place_ and place_.lower() not in title.lower() and len(title) + len(place_) + 3 <= 65: title += f" ({place_})"
    if not j["active"]: title += " (closed)"
    desc = (f"{j['title']} at {j['company']}" + (f" — {where}" if where else "") + f". {CAT[j['cat']]} role"
            + (", remote" if j["remote"] else "") + (". This job is closed." if not j["active"] else ". Apply on the company site."))
    page(f"job/{j['slug']}/", title, desc, body, head, compact=True)


def embed_code(spec, label, page_path, limit=6):
    """Copy-paste widget code. The link inside the div is a normal HTML link, so it works without scripts too."""
    return e(f'<div data-hrn-jobs="{spec}" data-limit="{limit}"><a href="{FULL}/{page_path}">{label} on {SITE}</a></div>\n<script src="{FULL}/widget.js" async></script>')


def badge_code(badge_path, label, page_path, markdown=False):
    if markdown:
        return e(f"[![{label} on {SITE}]({FULL}/{badge_path})]({FULL}/{page_path})")
    return e(f'<a href="{FULL}/{page_path}"><img src="{FULL}/{badge_path}" alt="{label} on {SITE}" height="28"></a>')


def cite(path, title):
    url = f"{FULL}/{path}"
    link_html = f'<a href="{url}">{title} — {SITE}</a>'
    return ('<details class="embed"><summary>Cite or link to this page</summary><p class="note">Free to quote with a link back. Pick a format:</p>'
            f'<pre><code>{e(link_html)}</code></pre><pre><code>{e(f"[{title} — {SITE}]({url})")}</code></pre>'
            f'<pre><code>{e(f"Source: {SITE}, “{title}”, {url}")}</code></pre></details>')


def badge_svg(label, value):
    lw, vw = int(34 + 7.7 * len(label)), int(18 + 7.7 * len(value))
    w = lw + vw
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="28" viewBox="0 0 {w} 28" role="img" aria-label="{e(label)}: {e(value)}">'
            f'<rect width="{w}" height="28" rx="6" fill="#0e0e0c"/><rect x="{lw}" width="{vw}" height="28" rx="6" fill="#7ee39a"/><rect x="{lw}" width="8" height="28" fill="#7ee39a"/>'
            f'<circle cx="14" cy="14" r="4" fill="#3ecf5f"/><text x="25" y="18.5" fill="#fff" font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="12" font-weight="bold">{e(label)}</text>'
            f'<text x="{lw + 9}" y="18.5" fill="#06361c" font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="12" font-weight="bold">{e(value)}</text></svg>')


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
    # paid placements bought in the account (written by collect.py from the API): promoted jobs and sponsors
    place_file = ROOT / "data" / "placements.json"
    PAID = json.loads(place_file.read_text()) if place_file.exists() else {}
    boost = defaultdict(dict)
    for b in PAID.get("boosts", []):
        if b.get("until", "") >= TODAY: boost[b.get("slug")][b.get("kind")] = b["until"]
    for j in jobs:
        bought = boost.get(j["slug"], {})
        j["pinned"] = bool(j["active"] and max(j.get("pinned_until", ""), bought.get("pinned", "")) >= TODAY)
        j["featured"] = bool(j["pinned"] or (j["active"] and max(j.get("featured_until", ""), bought.get("featured", "")) >= TODAY))
        if j["location"].lower() in {"n/a", "na", "none", "tbd", "-", "null", "not specified"}: j["location"] = ""
        j["entry"] = j["level"] in ("Junior", "Intern")
        j["pool"] = bool(POOL_RX.search(j["title"]))
        j["usd"] = usd_range(j["salary"])
        j["places"] = places_of(j["location"]) if j["active"] and j["location"] else []
        j["t"], j["ts"] = exact(j), stamp(j)
    active = [j for j in jobs if j["active"]]
    archived = [j for j in jobs if not j["active"]]
    by_cat = defaultdict(list)
    for j in active: by_cat[j["cat"]].append(j)
    companies = defaultdict(list)
    for j in jobs: companies[j["company"]].append(j)
    n, m = len(active), len({j["company"] for j in active})
    NO_ANON = ("Employers can also post a job themselves; such a posting is published only after its link has been checked automatically, and it is labelled as posted by the employer"
               if CFG["api_url"] else "We do not accept anonymous postings")
    N_FEEDS = len({s_["name"] for f_ in ("sources.json", "sources_tech.json") if (ROOT / f_).exists() for s_ in json.loads((ROOT / f_).read_text())})     # employer feeds read in each run
    remote = [j for j in active if j["remote"]]
    SALPCT = round(100 * sum(bool(j["salary"]) for j in active) / max(n, 1))
    WEEKNEW = sum(1 for j in active if (j["posted"] or "")[:10] >= (datetime.date.today() - datetime.timedelta(days=7)).isoformat())
    contact = " or ".join(x for x in [f'Telegram <a href="https://t.me/{e(CFG["contact_telegram"])}">@{e(CFG["contact_telegram"])}</a>' if CFG["contact_telegram"] else "",
                                      f'email <a href="mailto:{e(CFG["contact_email"])}">{e(CFG["contact_email"])}</a>' if CFG["contact_email"] else ""] if x)
    places = [(name, slug, js) for name, slug, rx in PLACES if len(js := [j for j in active if slug in j["places"]]) >= 5]
    OPEN.update(Counter(j["company"] for j in active))
    PERK_OK.update(x for x, k in Counter(x for j in active for x in j.get("perks", [])).items() if k >= 8)
    wk = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    for c, js in companies.items():
        opened = sum(1 for j in js if (j["posted"] or "") >= wk)
        closed_ = sum(1 for j in js if not j["active"] and (j.get("closed") or "") >= wk)
        net, base_ = opened - closed_, max(3, OPEN[c] // 10)
        PULSE[c] = (opened, closed_, "Ramping up" if net >= base_ else "Slowing down" if -net >= base_ else "Steady")
    spans = defaultdict(list)
    for j in archived:
        try:
            d = (datetime.date.fromisoformat(j["closed"][:10]) - datetime.date.fromisoformat(j["posted"][:10])).days
        except Exception:
            continue
        if 0 <= d <= 400: spans[j["cat"]].append(d)
    for cs, ds in spans.items():
        if len(ds) >= 20: CLOSE_DAYS[cs] = int(median(ds))
    for cs in CAT:
        mids = [(lo + hi) / 2 for j in by_cat[cs] if j["usd"] for lo, hi in [j["usd"]]]
        if len(mids) >= 15: CATMED[cs] = median(mids)
        for lv in ("Intern", "Junior", "Senior", "Lead"):
            lm = [(lo + hi) / 2 for j in by_cat[cs] if j["level"] == lv and j["usd"] for lo, hi in [j["usd"]]]
            if len(lm) >= 15: EST[(cs, lv)] = median(lm)
    top_cats = sorted((s for s in CAT if by_cat[s] and s != OTHER[0]), key=lambda s: -len(by_cat[s]))
    FOOT["cats"] = "".join(f'<li><a href="{P}/jobs/{s}/">{e(CAT[s])}</a></li>' for s in top_cats[:4])
    pop_sk = [t for t, _ in Counter(t for j in active for t in j["tags"]).most_common(10)]
    FOOT["pop"] = ('<p class="pop"><span>Popular searches:</span>' + "".join(f'<a href="{P}/skills/{TAG_SLUG.get(t, slugify(t))}/">{e(t)} jobs</a>' for t in pop_sk)
                   + "".join(f'<a href="{P}/locations/{slug}/">Jobs in {e(name.removeprefix("the "))}</a>' for name, slug, _ in sorted(places, key=lambda x: -len(x[2]))[:6]) + "</p>")
    comp_items = sorted(companies.items(), key=lambda kv: -sum(j["active"] for j in kv[1]))
    SPONSORS = [sp for sp in CFG.get("sponsors", []) + PAID.get("sponsors", []) if sp.get("until", "") >= TODAY and sp.get("company") in companies]
    spot_cos = [sp["company"] for sp in SPONSORS if sp.get("slot") in ("home", "spotlight", "companies")]
    def spot_tiles(names):
        return '<div class="spot">' + "".join(f'<a href="{P}/companies/{slugify(c)}/">{ava(c)}<span><b>{e(c)}</b><span class="s">{roles(OPEN[c], "open role")} · featured</span></span></a>' for c in names) + "</div>"
    def sponsor_line(slot):
        cs_ = [sp["company"] for sp in SPONSORS if sp.get("slot") == slot]
        return ('<p class="sponsor">Supported by ' + ", ".join(f'<a href="{P}/companies/{slugify(c)}/">{e(c)}</a> ({roles(OPEN[c], "open role")})' for c in cs_) + "</p>") if cs_ else ""
    for s in CAT:
        SIM["cat"][s] = diverse(order(by_cat[s]), 12)
    by_comp_cat = defaultdict(list)
    for j in order(active):
        if len(by_comp_cat[(j["company"], j["cat"])]) < 4: by_comp_cat[(j["company"], j["cat"])].append(j)
    SIM["comp"] = by_comp_cat
    specific = [j for j in active if not j["pool"]]
    latest = diverse(order(specific), 40)

    # Home
    ROLE_JOBS = {s_: [j for j in active if role_hit(nm, rx, j["title"])] for nm, s_, rx in ROLES}
    by_role = {s_: (nm, ROLE_JOBS[s_]) for nm, s_, _ in ROLES if len(ROLE_JOBS[s_]) >= 20}
    fam_rows = []        # (slug, name, what kind of work, [(role slug, role name, jobs)], every job in the category once)
    for fs, fn, fd, rs in roles_info.FAMILIES:
        live = [(s_, by_role[s_][0], len(by_role[s_][1])) for s_ in rs if s_ in by_role]
        seen_, js_ = set(), []
        for s_, _, _ in live:
            for j in by_role[s_][1]:
                if j["id"] not in seen_: seen_.add(j["id"]); js_.append(j)
        if live: fam_rows.append((fs, fn, fd, live, js_))
    def dir_block(fs, fn, fd, live, js_, top=None, tag="h2"):
        return (f'<div class="dirb"><{tag}><a href="{P}/categories/{fs}/"><u>{e(fn)}</u></a><span>{len(js_):,}</span></{tag}><p>{e(fd[0].upper() + fd[1:])}.</p><ul>'
                + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/roles/{s_}/">{e(nm)}</a><span>{c:,}</span></li>' for s_, nm, c in (live if top is None else live[:top]))
                + (f'<li class="more"><a href="{P}/categories/{fs}/">All {len(live)} in {e(rlow(fn))}</a></li>' if top is not None and len(live) > top else "") + "</ul></div>")
    ROLE_TOP = sorted(((nm, s_, len(ROLE_JOBS[s_])) for nm, s_, _ in ROLES if s_ in ROLE_BASE), key=lambda x: -x[2])
    # Pictures before words (the owner: "I cannot read walls of text: more charts and infographics everywhere").
    # Every picture is counted from the open postings on this build; each has one caption that says what it shows.
    def donut(part, whole, label):
        pc = round(100 * part / max(1, whole))
        return (f'<div class="donut"><svg viewBox="0 0 36 36" role="img" aria-label="{pc}% {e(label)}"><circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--bg2)" stroke-width="3.8"/>'
                f'<circle cx="18" cy="18" r="15.9" fill="none" stroke="var(--ac)" stroke-width="3.8" stroke-dasharray="{pc} {100 - pc}" transform="rotate(-90 18 18)"/>'
                f'<text x="18" y="21" text-anchor="middle">{pc}%</text></svg><span>{e(label)}</span></div>')
    def cols(pairs, hi_=None):                      # [(label under the column, value)]: a column chart
        mx_ = max((v for _, v in pairs), default=1) or 1
        return ('<div class="ccols">' + "".join(f'<div{" class=\"hi\"" if hi_ is not None and i == hi_ else ""} style="height:{max(2, round(100 * v / mx_))}%"><b>{v:,}</b></div>' for i, (_, v) in enumerate(pairs)) + "</div>"
                '<div class="ccx">' + "".join(f"<span>{e(lb)}</span>" for lb, _ in pairs) + "</div>")
    def mini_pics(js):
        """Two pictures for a list of jobs: what they pay (when at least 30 state it) and three rings."""
        if len(js) < 20: return ""
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in js if j["usd"]]
        pay = ""
        if len(mids_) >= 30:
            eg = [(0, 75), (75, 100), (100, 125), (125, 150), (150, 175), (175, 200), (200, 250), (250, 300), (300, 10 ** 6)]
            md_ = median(mids_)
            pay = (f'<figure class="pic"><figcaption><b>What these jobs pay</b>{len(mids_):,} of them state a yearly range in US dollars. The green column holds the median, {money(md_)}.</figcaption>'
                   + cols([(("<$75K" if lo == 0 else f"${lo}K+" if hi > 1000 else f"${lo}K"), sum(1 for v in mids_ if lo * 1000 <= v < hi * 1000)) for lo, hi in eg],
                          next((i for i, (lo, hi) in enumerate(eg) if lo * 1000 <= md_ < hi * 1000), None)) + "</figure>")
        rings = (f'<figure class="pic"><figcaption><b>Three numbers</b>Out of {len(js):,} open jobs in this list.</figcaption><div class="donuts">'
                 + donut(sum(j["remote"] for j in js), len(js), "can be done from home") + donut(sum(bool(j["salary"]) for j in js), len(js), "state the pay")
                 + donut(sum(1 for j in js if j["entry"]), len(js), "are for beginners") + "</div></figure>")
        return f'<div class="pics two">{pay}{rings}</div>'
    fam_top = sorted(fam_rows, key=lambda f: -len(f[4]))[:10]
    pic_fields = '<div class="hbars">' + "".join(
        f'<a href="{P}/categories/{fs}/"><span class="hn">{e(fn)}</span><span class="hb"><i style="width:{max(3, round(100 * len(js_) / len(fam_top[0][4])))}%"></i></span><span class="hc">{len(js_):,}</span></a>' for fs, fn, _, _, js_ in fam_top) + "</div>"
    mids_all = [(j["usd"][0] + j["usd"][1]) / 2 for j in active if j["usd"]]
    edges = [(0, 75), (75, 100), (100, 125), (125, 150), (150, 175), (175, 200), (200, 250), (250, 300), (300, 10 ** 6)]
    pay_cols = [(("<$75K" if lo == 0 else f"${lo}K+" if hi > 1000 else f"${lo}K"), sum(1 for v in mids_all if lo * 1000 <= v < hi * 1000)) for lo, hi in edges]
    med_all = median(mids_all) if mids_all else 0
    med_i = next((i for i, (lo, hi) in enumerate(edges) if lo * 1000 <= med_all < hi * 1000), None)
    days14 = [(datetime.date.today() - datetime.timedelta(days=d)) for d in range(13, -1, -1)]
    by_day = Counter((j["posted"] or "")[:10] for j in active)
    day_cols = [(f"{d.day}", by_day.get(d.isoformat(), 0)) for d in days14]
    n_pay, n_ent = sum(bool(j["salary"]) for j in active), sum(1 for j in active if j["entry"])
    market_pics = ('<div class="pics">'
                   f'<figure class="pic"><figcaption><b>Where the jobs are</b>Open jobs in the ten largest fields. A job can count in two fields.</figcaption>{pic_fields}</figure>'
                   f'<figure class="pic"><figcaption><b>What the postings pay</b>{len(mids_all):,} postings state a yearly range in US dollars. The middle of the range is most often here; the green column holds the median, {money(med_all)}.</figcaption>{cols(pay_cols, med_i)}</figure>'
                   f'<figure class="pic"><figcaption><b>Three numbers about today’s jobs</b>Out of {n:,} open jobs.</figcaption><div class="donuts">'
                   + donut(len(remote), n, "can be done from home") + donut(n_pay, n, "state the pay") + donut(n_ent, n, "are for beginners") + "</div></figure>"
                   f'<figure class="pic"><figcaption><b>New jobs, day by day</b>Open jobs by the day the employer posted them, last 14 days. The numbers under the columns are days of the month.</figcaption>{cols(day_cols)}</figure>'
                   "</div>")
    ROLE_TOP = [x for x in ROLE_TOP if x[2] >= 20][:12]
    TOOLS = tools_pages.build_tools(page, section, crumbs, e, P, FULL, SITE, V, active, CAT)       # [(path, name, one line)]
    cats = "".join(f'<li><a href="{P}/jobs/{s}/"><b><u>{e(CAT[s])}</u></b><span class="c">{len(by_cat[s]):,} jobs</span><span class="d">{e(skills_info.plain_cat(s))}</span></a></li>'
                   for s in sorted((s for s in CAT if by_cat[s]), key=lambda s: (s == OTHER[0], -len(by_cat[s]))))
    place_html = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in places)
    place_top = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in sorted(places, key=lambda x: -len(x[2]))[:28])
    comp_top = "".join(tile(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js), True) for c, js in comp_items[:12])
    fresh3 = sum(1 for j in active if age(j["posted"])[1])
    logo_cos = [(c, js) for c, js in comp_items if slugify(c) in LOGOS][:10]
    # one real, open listing taken apart: what a visitor can read on every job page
    aj = next((j for j in latest if j["salary"] and j["remote"] and j.get("years") and j["location"] and len(j["title"]) <= 46 and j.get("usd") and j["cat"] in CATMED
               and j["id"].split("-", 1)[0] in SOURCE_NAME and slugify(j["company"]) in LOGOS), None)
    anatomy = ""
    if aj:
        lands_a = countries_of(aj["location"])
        scope_a = "worldwide" if aj.get("anywhere") else " or ".join(nm for _, nm in lands_a[:3]) if lands_a else ""
        try: open_a = max(0, (datetime.date.today() - datetime.date.fromisoformat(aj["posted"][:10])).days)
        except Exception: open_a = 0
        rows_a = [("Salary", e(aj["salary"]) + f'<small>Median for {e(CAT[aj["cat"]])} roles: {money(CATMED[aj["cat"]])}</small>'),
                  ("Workplace", "Remote" + (f", {e(scope_a)}" if scope_a else "")),
                  ("Experience asked", f'{aj["years"]}+ years'),
                  ("Open for", "Posted today" if open_a == 0 else f"{open_a} day{'s' if open_a != 1 else ''}"),
                  ("Last checked", fdate(aj.get("last_seen") or TODAY)),
                  ("Source", f'{e(aj["company"])}’s own posting on {SOURCE_NAME[aj["id"].split("-", 1)[0]]}')]
        notes_a = [("Pay, when the employer states it.", "When it does not, you see what similar roles advertise."),
                   ("Where “remote” applies.", "The countries the posting accepts, not just the word."),
                   ("Years of experience asked.", "An “entry-level” title that wants five years stands out."),
                   ("How long it has been open.", "A posting older than 90 days is flagged."),
                   ("When we last checked it", "against the employer’s own page."),
                   ("Where it came from.", "Always the employer’s posting, never another job board.")]
        note_li = lambda i: f'<li><i>{i + 1}</i><span><b>{notes_a[i][0]}</b> {notes_a[i][1]}</span></li>'
        anatomy = ('<section class="sec"><div class="sec-head"><h2>What every listing tells you</h2><a href="' + f'{P}/job/{aj["slug"]}/' + '">Open this job</a></div>'
                   '<div class="anat"><ol class="anat-n">' + "".join(note_li(i) for i in range(3)) + "</ol>"
                   f'<a class="anat-card" href="{P}/job/{aj["slug"]}/"><span class="ac-h">{ava(aj["company"])}<span><b>{e(aj["title"])}</b><span>{e(aj["company"])} · {e(aj["location"][:40])}</span></span></span>'
                   '<span class="ac-rows">' + "".join(f'<span class="ac-r"><i>{i + 1}</i><span class="k">{k}</span><span class="v">{v}</span></span>' for i, (k, v) in enumerate(rows_a)) + "</span>"
                   '<span class="ac-b">Apply on company site</span></a>'
                   '<ol class="anat-n" start="4">' + "".join(note_li(i) for i in range(3, 6)) + "</ol></div>"
                   '<p class="note" style="text-align:center;margin-top:14px">A real listing, open today. The other ' f'{n - 1:,}' ' are laid out the same way.</p></section>')
    # Where the visitor is: the browser's time zone names a country without asking for anything. For each country we know:
    # jobs located there, remote roles whose posting names it, its region; plus remote roles open worldwide.
    live_slugs = {slug for _, slug, _ in places}
    code_slug = {rule: slug for _, slug, rule in PLACES if isinstance(rule, str) and rule != "region"}
    region_of = {c_: r_ for r_, (members, _) in REGIONS.items() for c_ in members}
    named = Counter()
    for j in remote:
        for c_, _ in (countries_of(j["location"]) if j["location"] else []): named[c_] += 1
    place_n = {slug: len(js) for _, slug, js in places}
    geo_c = {"US": ["United States", "united-states", place_n.get("united-states", 0), named["US"], ""]}
    for code_, nm_, _, _ in COUNTRIES:
        slug_ = code_slug.get(code_, "")
        geo_c[code_] = [nm_, slug_ if slug_ in live_slugs else "", place_n.get(slug_, 0), named[code_], region_of.get(code_, "")]
    geo = {"w": sum(1 for j in remote if j.get("anywhere")), "c": geo_c,
           "r": {r_: [next(nm.removeprefix("the ") for nm, sl, _ in PLACES if sl == r_), place_n.get(r_, 0)] for r_ in REGIONS if r_ in live_slugs},
           "tz": json.loads((ROOT / "tz_countries.json").read_text()) if (ROOT / "tz_countries.json").exists() else {}}
    write("data/geo.json", json.dumps(geo, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    new_today_h = sum(1 for j in active if (j["posted"] or "")[:10] == TODAY)
    closed_today_h = sum(1 for j in archived if j.get("closed") == TODAY)
    pulse = (f'<p class="pulse"><b>Today so far</b><span>{sum(1 for j in active if j.get("last_seen") == TODAY):,} roles re-checked</span>'
             f'<span>{new_today_h:,} posted today</span><span>{closed_today_h:,} closed by employers (their pages stay, marked closed)</span><a href="{P}/status/">Data status</a></p>')
    board_rows = "".join(
        f'<a href="{P}/job/{j["slug"]}/"><time class="ba" {when(j)}>{age(j["posted"])[0]}</time><span><span class="bt">{e(j["title"])}</span>'
        f'<span class="bc">{e(j["company"])}{" · " + e(j["location"][:40]) if j["location"] else ""}</span></span>'
        f'<span class="bp">{e(j["salary"][:20]) if j["salary"] else ""}</span></a>' for j in diverse(order(specific), 6, 1))
    hero = (f'<section class="hero"><div class="wrap"><div>'
            f'<p class="stamp">Checked {fdate(TODAY, False)} · <b>{n:,}</b> open roles · <b>{fresh3:,}</b> new in 3 days</p>'
            f'<h1>Stop applying to tech jobs that are <span class="hl">already gone</span></h1>'
            f'<p class="sub">Old listings stay online long after the job is filled. We read {m} company career pages every hour and keep only what is still open.</p>'
            f'<form class="searchbar two" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Job title, skill or company" aria-label="What: job title, skill or company">'
            f'<span class="sb-sep" aria-hidden="true"></span><input type="search" name="where" placeholder="City, country or remote" aria-label="Where: city, country or remote"><button class="btn primary">Search</button></form>'
            f'<p class="popular"><span>Or start with</span><a href="{P}/remote/">remote</a><a href="{P}/new/">new this week</a><a href="{P}/skills/python/">Python</a><a href="{P}/skills/rust/">Rust</a>'
            f'<a href="{P}/perks/visa-sponsorship/">visa sponsorship</a><a href="{P}/entry-level/">entry-level</a><a href="{P}/with-salary/">salary listed</a><a href="{P}/crypto/">crypto</a></p>'
            f'<p class="near" id="near" hidden></p>'
            f'<p class="heroalt">If you would rather not search, <a href="{P}/for-you/">list your skills and see what fits</a>.</p></div>'
            f'<div class="board" aria-label="Newest roles"><div class="board-h"><span>Just posted</span><a href="{P}/board/"><b>Open as a wall</b></a></div>{board_rows}</div></div>'
            f'<div class="wrap0 hero-logos"><p>Read every hour from the career pages of</p><div class="logorow">'
            + "".join(f'<a href="{P}/companies/{slugify(c)}/" title="{e(c)}: {sum(j["active"] for j in js):,} open roles">{ava(c)}<span>{e(c)}</span></a>' for c, js in logo_cos)
            + f'<a class="more" href="{P}/companies/">and {len(companies) - len(logo_cos)} more</a></div></div></section>')
    plus_band = ""
    if CFG.get("plus", {}).get("live"):
        plus_band = (f'<div class="band"><div><h2>Get the email when a matching job appears</h2><p>Plus watches your saved searches and helps with the resume and cover letter for each posting. One payment, nothing renews.</p></div>'
                     f'<a class="btn" href="{P}/plus/">See Plus</a></div>')
    band = (f'<div class="band"><div><h2>Hiring?</h2><p>Your posting sits next to {n:,} others here. A standard listing is free; a featured one stays at the top of the list, from $99, paid in crypto.</p></div>'
            f'<a class="btn" href="{P}/post-a-job/">Post a job</a></div>')
    ORG_LD[0] = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": FULL + "/", "logo": FULL + "/og.jpg"}) + "</script>")
    FAQ = [("Where do the jobs come from?", "Straight from the official careers pages of tech companies. Every listing links to the original posting, and you apply on the employer's own site."),
           ("How often is the site updated?", "Every hour. New roles are added. A role the company has closed keeps its page at the same address, marked as closed, and leaves the lists of open jobs."),
           ("Is it free?", "Yes. Searching, saving jobs, tracking your applications and applying are free. A paid Plus plan with email alerts and AI resume tools is on the way; no job will be held back for it."),
           ("Do I need an account?", "No. Saved jobs, application statuses and saved searches are kept in your browser."),
           ("Can I see salaries?", "Where the employer publishes a range, we show it, let you filter and sort by it, and use it for the salary pages.")]
    faq_html = '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in FAQ) + "</dl>"
    faq_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in FAQ]}) + "</script>")
    top_paid = diverse_pairs(sorted(((j, j["usd"]) for j in active if j["usd"]), key=lambda x: -x[1][1]), 8)
    home = ('<section class="sec" id="home-recent" hidden><div class="sec-head"><h2>Pick up where you left off</h2><a href="' + P + '/my-jobs/">My jobs</a></div><ul class="jobs" id="home-recent-list"></ul></section>'
            + (section("Featured tech employers", spot_tiles(spot_cos), ("post-a-job/", "Feature your company")) if spot_cos else "")
            + section("Latest tech jobs", f'<ul class="jobs">{"".join(card(j) for j in latest[:12])}</ul>', ("jobs/", f"All {n:,} jobs"))
            + section("Browse jobs by category", '<div class="dir">' + "".join(dir_block(*f, top=4, tag="h3") for f in fam_rows) + "</div>", ("categories/", f"All {len(by_role)} kinds of work"))
            + section("The job market today, in four pictures", market_pics, ("insights/", "All rankings and charts"))
            + pulse + anatomy
            + '<div class="inkband">' + section("Highest paid right now", f'<ul class="jobs">{"".join(card(j) for j, _ in top_paid)}</ul>', ("salaries/", "Salary data")) + "</div>"
            + '<section class="sec"><div class="sec-head"><h2>Browse the jobs</h2></div><div class="tabs2">'
              '<input type="radio" name="dir" id="dir-role" checked><label for="dir-role">By role</label>'
              '<input type="radio" name="dir" id="dir-loc"><label for="dir-loc">By location</label>'
              '<input type="radio" name="dir" id="dir-co"><label for="dir-co">By company</label>'
              '<div class="tabp" id="p-role"><ul class="tiles">' + "".join(tile(f"roles/{s_}/", nm, k_) for nm, s_, k_ in ROLE_TOP) + f'</ul><p class="tabmore"><a href="{P}/categories/">All {len(by_role)} roles, by category</a></p></div>'
              + f'<div class="tabp" id="p-loc"><ul class="tiles">{place_top}</ul><p class="tabmore"><a href="{P}/locations/">All {len(places)} locations</a></p></div>'
              + f'<div class="tabp" id="p-co"><ul class="tiles">{comp_top}</ul><p class="tabmore"><a href="{P}/companies/">All {len(companies)} companies</a></p></div></div></section>'
            + plus_band + band
            + section("Free tools", '<div class="tgrid">' + "".join(tools_pages.TILES[u] for u in tools_pages.EXTRA + [u for u, nm, d_ in TOOLS[:3]]) + "</div>",
                      ("tools/", f"All {len(TOOLS) + len(tools_pages.EXTRA)} tools"))
            + section("For your own site", '<div class="feats">'
                      f'<a class="feat" href="{P}/widgets/"><h3>A list of jobs for your site</h3><p>Have a blog, a community or a company site? Put a small list of fresh jobs on it. You paste a short piece of code once and the list keeps itself up to date.</p></a>'
                      f'<a class="feat" href="{P}/widgets/"><h3>A “we’re hiring” picture with a live number</h3><p>A small image that shows how many roles are open today. For a site footer, a blog post or a project page.</p></a>'
                      f'<a class="feat" href="{P}/api/"><h3>For programmers</h3><p>The whole job list in a form that programs can read (an API), refreshed every hour. Free, with nothing to sign up for.</p></a></div>')
            + section("Common questions", faq_html))
    page("", f"Tech Jobs — {roles(n, 'open role')} at {m} companies | {SITE}",
         f"Tired of job listings that closed weeks ago? {roles(n)} at {m} tech companies, checked against their career pages every hour. Remote and salary filters.", home, hero=hero,
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": FULL + "/",
               "potentialAction": {"@type": "SearchAction", "target": FULL + "/jobs/?q={search_term_string}", "query-input": "required name=search_term_string"}}) + "</script>" + faq_ld + ORG_LD[0])
    rss("feed.xml", f"{SITE} — latest tech jobs", "", active)

    # Search page
    opts = "".join(f'<option value="{s}">{e(CAT[s])}</option>' for s in CAT if by_cat[s])
    loc_opts = "".join(f'<option value="{slug}">{e(name.removeprefix("the "))}</option>' for name, slug, _ in places)
    skill_counts = Counter(t for j in active for t in j["tags"])
    top_skills = [t for t, _ in skill_counts.most_common(18)]
    skill_chips = "".join(f'<button class="chipbtn" type="button" data-skill="{e(t)}" aria-pressed="false">{e(t)}</button>' for t in top_skills)
    group = lambda label, inner: f'<div class="fgroup"><span class="flabel">{label}</span>{inner}</div>'
    search = (crumbs(("All jobs", "")) + '<h1 class="h1s">Search tech jobs</h1>'
              f'<form class="searchbar wide" id="qform">{ICON_SEARCH}<input type="search" id="q" list="sugg" placeholder="Job title, skill or company" aria-label="Search jobs" autocomplete="off"><button class="btn primary">Search</button></form>'
              '<button class="btn ghost sm" id="ftoggle" type="button" aria-expanded="false">Filters</button>'
              '<div class="sgrid haspane" id="search"><aside id="fwrap" aria-label="Filters">'
              + group("Posted", '<select id="age" aria-label="Posted"><option value="">Any time</option><option value="1">Last 24 hours</option><option value="3">Last 3 days</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option></select>')
              + group("Category", f'<select id="cat" aria-label="Category"><option value="">All categories</option>{opts}</select>')
              + group("Level", '<select id="lvl" aria-label="Level"><option value="">Any level</option><option>Intern</option><option>Junior</option><option>Senior</option><option>Lead</option></select>')
              + group("Location", f'<select id="loc" aria-label="Location"><option value="">Anywhere</option>{loc_opts}</select>')
              + group("Salary", '<select id="sal" aria-label="Salary"><option value="">Any salary</option><option value="1">Salary listed</option><option value="100000">$100K+</option>'
                                '<option value="120000">$120K+</option><option value="150000">$150K+</option><option value="180000">$180K+</option><option value="200000">$200K+</option>'
                                '<option value="250000">$250K+</option><option value="300000">$300K+</option></select>'
                                '<div class="filters" style="margin-top:8px"><label hidden><input type="checkbox" id="f-nosal"> Also show jobs that do not state pay</label></div>')
              + group("Work style", '<div class="filters"><label><input type="checkbox" id="f-remote"> Remote</label><label><input type="checkbox" id="f-any"> Work from anywhere</label>'
                                    '<label><input type="checkbox" id="f-entry"> Entry-level</label><label><input type="checkbox" id="f-crypto"> Crypto &amp; web3</label></div>')
              + '<details class="morefilters"><summary>More filters</summary><div class="mf">'
              + group("Search in", '<div class="filters"><label><input type="checkbox" id="f-ti"> Job titles only</label></div>')
              + group("Leave out", '<div class="filters"><label><input type="checkbox" id="f-real"> Roles open 90+ days and talent pools</label></div>'
                                   '<input type="text" id="xwords" class="xin" placeholder="Words in the title, e.g. senior, sales" aria-label="Words to leave out of results" autocomplete="off">'
                                   '<div id="xcos" class="xcos"></div>')
              + group("Perk", '<select id="perk" aria-label="Perk"><option value="">Any perk</option>' + "".join(f'<option value="{e(nm)}">{e(nm)}</option>' for nm, _, _ in PERKS) + "</select>")
              + group("Type", '<select id="etype" aria-label="Type"><option value="">Any type</option><option>Full-time</option><option>Contract</option><option>Part-time</option><option>Internship</option></select>')
              + group("Skills", f'<div class="skillbar" id="skills">{skill_chips}</div>')
              + '</div></details><div class="fgroup fclear"><button class="linkbtn" id="fclear" type="button">Clear all filters</button></div></aside>'
              '<div><div class="rbar"><p class="note" id="count">Loading…</p><div class="rtools">'
              '<select id="sort" aria-label="Sort"><option value="new">Newest first</option><option value="rel">Best match</option><option value="sal">Highest salary</option></select>'
              '<button class="btn ghost sm" id="save-search" type="button">Save this search</button></div></div>'
              '<ul class="jobs" id="results"></ul><p><button class="btn" id="more" type="button" hidden>Show more</button></p></div>'
              '<aside class="pane" id="pane" aria-label="Job preview"><p class="pane-empty">Select a job to preview it here.</p></aside></div>'
              + '<datalist id="sugg">' + "".join(f'<option value="{e(x)}">' for x in top_skills + [c for c, _ in comp_items[:200]]) + "</datalist>"
              + f'<noscript><p>Search needs JavaScript. Browse by category instead:</p><ul class="tiles">{cats}</ul></noscript><script src="{P}/app.js?v={V}" defer></script>')
    page("jobs/", f"Search {roles(n, 'Tech Job')} | {SITE}",
         "Search tech jobs by title, skill or company. Filter by level, location, salary and remote, sort by pay, and save your searches.", search,
         head=f'<link rel="preload" href="{P}/data/head.json" as="fetch" crossorigin><link rel="preload" href="{P}/data/index.json" as="fetch" crossorigin>')

    # Long-tail landing pages: skill x remote, skill x place, category x place, place x remote, category x level
    by_tag = defaultdict(list)
    for j in active:
        for t in j["tags"]: by_tag[t].append(j)
    tslug = lambda t: TAG_SLUG.get(t, slugify(t))
    CMP = [t for t, _ in sorted(by_tag.items(), key=lambda kv: -len(kv[1]))[:14]]      # skills that get head-to-head comparison pages
    cmp_path = lambda a, b: "compare/{}-vs-{}/".format(*[tslug(x) for x in sorted((a, b), key=CMP.index)])
    cmp_links = lambda t: ('<p class="note cmpl">Compare ' + e(t) + " with: " + " · ".join(f'<a href="{P}/{cmp_path(t, o)}">{e(o)}</a>' for o in CMP if o != t) + "</p>") if t in CMP else ""
    LEVELS = [("Intern", "intern", "Internship"), ("Junior", "junior", "Junior"), ("Senior", "senior", "Senior"), ("Lead", "lead", "Lead & principal")]
    combos, REL = [], defaultdict(list)
    big_places = [x for x in places if len(x[2]) >= 150]      # combination pages only where a place has enough jobs to fill them
    def add(path, h1, js, trail, qs, pre, post, keys):
        if len(js) < 8: return
        combos.append((path, h1, js, trail, qs, pre, post))
        for k, label in keys: REL[k].append((path, label, len(js)))
    for t, js in by_tag.items():
        add(f"remote/skills/{tslug(t)}/", f"Remote {t} jobs", [j for j in js if j["remote"]], (("Remote", "remote/"),),
            f"remote=1&skills={quote(t)}", "remote ", f" mentioning {e(t)}", [("tag:" + t, f"Remote {t} jobs"), ("remote", f"Remote {t}")])
        for name, slug, _ in big_places:
            short = name.removeprefix("the ")
            add(f"locations/{slug}/skills/{tslug(t)}/", f"{t} jobs in {name}", [j for j in js if slug in j["places"]],
                (("Locations", "locations/"), (short, f"locations/{slug}/")), f"loc={slug}&skills={quote(t)}", "", f" mentioning {e(t)} in {e(name)}",
                [("tag:" + t, f"{t} in {short}"), ("place:" + slug, f"{t} jobs")])
    for name, slug, pj in places:
        short = name.removeprefix("the ")
        add(f"locations/{slug}/remote/", f"Remote tech jobs in {name}", [j for j in pj if j["remote"]], (("Locations", "locations/"), (short, f"locations/{slug}/")),
            f"loc={slug}&remote=1", "remote ", f" in {e(name)}", [("place:" + slug, "Remote"), ("remote", f"Remote in {short}")])
        for cs, cname in CAT.items():
            if cs == OTHER[0]: continue
            add(f"locations/{slug}/{cs}/", f"{cname} jobs in {name}", [j for j in pj if j["cat"] == cs], (("Locations", "locations/"), (short, f"locations/{slug}/")),
                f"loc={slug}&cat={cs}", f"{e(cname)} ", f" in {e(name)}", [("cat:" + cs, f"{cname} in {short}"), ("place:" + slug, cname)])
    HUB["roles"] = {slug: (nm, {j["id"] for j in rj_}) for slug, (nm, rj_) in by_role.items()}
    HUB["week"], HUB["live"] = (datetime.date.today() - datetime.timedelta(days=7)).isoformat(), {slug for _, slug, _ in places}
    for slug_r, (rname, rj) in by_role.items():
        trail_r, low, base_r = (("Categories", "categories/"), (rname, f"roles/{slug_r}/")), rlow(rname), slug_r in ROLE_BASE
        many = ROLE_PLURAL.get(rname, low + "s")
        rem_, ent_ = [j for j in rj if j["remote"]], [j for j in rj if j["entry"]]
        if base_r or len(rem_) >= 20: add(f"roles/{slug_r}/remote/", f"Remote {low} jobs", rem_, trail_r, f"remote=1&q={quote(rname)}", "remote ", f" for {e(many)}", [("role:" + slug_r, "Remote")])
        if base_r or len(ent_) >= 20: add(f"roles/{slug_r}/entry-level/", f"Entry-level {low} jobs", ent_, trail_r, f"entry=1&q={quote(rname)}", "entry-level ", f" for {e(many)}", [("role:" + slug_r, "Entry-level")])
        for name, slug, _ in (big_places if base_r else big_places[:6]):
            here_ = [j for j in rj if slug in j["places"]]
            if base_r or len(here_) >= 25:
                add(f"roles/{slug_r}/{slug}/", f"{rname} jobs in {name}", here_, trail_r, f"loc={slug}&q={quote(rname)}", "", f" for {e(many)} in {e(name)}",
                    [("role:" + slug_r, name.removeprefix("the ")), ("place:" + slug, rname)])
    cut3 = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    for t, js in by_tag.items():
        add(f"skills/{tslug(t)}/new/", f"{t} jobs posted in the last 3 days", [j for j in js if (j["posted"] or "") >= cut3], (("Skills", "skills/"), (t, f"skills/{tslug(t)}/")),
            f"age=3&skills={quote(t)}", "", f" mentioning {e(t)}, posted in the last three days", [("tag:" + t, "Last 3 days")])
    for slug_r, (rname, rj) in by_role.items():
        new_ = [j for j in rj if (j["posted"] or "") >= cut3]
        if slug_r in ROLE_BASE or len(new_) >= 20:
            add(f"roles/{slug_r}/new/", f"{rname} jobs posted in the last 3 days", new_, (("Categories", "categories/"), (rname, f"roles/{slug_r}/")),
                f"age=3&q={quote(rname)}", "", " posted in the last three days", [("role:" + slug_r, "Last 3 days")])
    add("remote/new/", "Remote tech jobs posted in the last 3 days", [j for j in remote if (j["posted"] or "") >= cut3], (("Remote", "remote/"),), "remote=1&age=3", "remote ", " posted in the last three days", [("remote", "Last 3 days")])
    add("remote/entry-level/", "Remote entry-level tech jobs", [j for j in remote if j["entry"]], (("Remote", "remote/"),), "remote=1&entry=1", "remote entry-level ", "", [("remote", "Entry-level")])
    for t, js in by_tag.items():
        add(f"skills/{tslug(t)}/entry-level/", f"Entry-level {t} jobs", [j for j in js if j["entry"]], (("Skills", "skills/"), (t, f"skills/{tslug(t)}/")),
            f"entry=1&skills={quote(t)}", "entry-level ", f" mentioning {e(t)}", [("tag:" + t, "Entry-level")])
    for perk_name, perk_slug in (("Visa sponsorship", "visa-sponsorship"), ("Relocation support", "relocation")):
        pk = [j for j in active if perk_name in j.get("perks", [])]
        add(f"perks/{perk_slug}/remote/", f"Remote tech jobs with {perk_name.lower()}", [j for j in pk if j["remote"]], (("Perks", "perks/"), (perk_name, f"perks/{perk_slug}/")),
            f"remote=1&perk={quote(perk_name)}", "remote ", f" that mention {perk_name.lower()}", [])
        for name, slug, _ in big_places:
            add(f"perks/{perk_slug}/{slug}/", f"Tech jobs with {perk_name.lower()} in {name}", [j for j in pk if slug in j["places"]], (("Perks", "perks/"), (perk_name, f"perks/{perk_slug}/")),
                f"loc={slug}&perk={quote(perk_name)}", "", f" in {e(name)} that mention {perk_name.lower()}", [("place:" + slug, perk_name)])
    for k_ in (100, 150, 200, 250, 300):                       # "jobs that pay 100k": the low end of the advertised range is at least that much
        rich = [j for j in active if j["usd"] and j["usd"][0] >= k_ * 1000]
        add(f"salary/{k_}k/", f"Tech jobs that pay ${k_}K or more", rich, (("Salaries", "salaries/"),), f"sal={k_ * 1000}", "", f" whose advertised range starts at ${k_}K or more", [("pay", f"${k_}K+")])
        add(f"salary/{k_}k/remote/", f"Remote tech jobs that pay ${k_}K or more", [j for j in rich if j["remote"]], (("Salaries", "salaries/"), (f"${k_}K+", f"salary/{k_}k/")),
            f"sal={k_ * 1000}&remote=1", "remote ", f" whose advertised range starts at ${k_}K or more", [("pay", f"Remote ${k_}K+"), ("remote", f"${k_}K+")])
    for cs, cname in CAT.items():
        if cs == OTHER[0]: continue
        for lv, ls, ll in LEVELS:
            add(f"jobs/{cs}/{ls}/", f"{ll} {cname} jobs", [j for j in by_cat[cs] if j["level"] == lv], (("All jobs", "jobs/"), (cname, f"jobs/{cs}/")),
                f"cat={cs}&lvl={lv}", f"{e(ll)} {e(cname)} ", "", [("cat:" + cs, ll)])
    for path, h1, js, trail, qs, pre, post in combos:
        listing(path, h1, f"{h1} ({len(js):,} open) | {SITE}", f"{roles(len(js), 'open role')}: {h1} at tech companies. Updated hourly.",
                js, intro_for(js, pre, post), trail=trail, per=50, max_pages=3, more=qs, faq=h1[0].lower() + h1[1:] if h1.split()[0] in ("Remote", "Senior", "Junior", "Internship", "Lead") else h1)

    # Listings
    for s, name in CAT.items():
        js = by_cat[s]
        if not js: continue
        listing(f"jobs/{s}/", f"{name} jobs in tech", f"{name} Jobs in Tech ({len(js):,} open) | {SITE}",
                f"{roles(len(js), name + ' job')} at tech companies. Remote and on-site roles, updated hourly.",
                js, (f"<strong>{e(name)}</strong>: {e(skills_info.CATEGORIES[s])}. " if s in skills_info.CATEGORIES else "") + intro_for(js, f"{e(name)} ", hub=True), trail=(("All jobs", "jobs/"),), feed=True, extra=sponsor_line("category:" + s) + hub_stats(js) + rel(REL["cat:" + s]) + hub_sections(f"{name} roles", js)[0], faq=f"{name} jobs",
                hub=hub_sections(f"{name} roles", js)[1], accent=CAT_ACCENT.get(s), list_title=f"Newest {name} jobs")
        rj = [j for j in js if j["remote"]]
        if len(rj) >= 5:
            listing(f"remote/{s}/", f"Remote {name} jobs in tech", f"Remote {name} Jobs in Tech ({len(rj):,} open) | {SITE}",
                    f"{roles(len(rj), 'remote ' + name + ' job')} at tech companies. Work from anywhere, updated hourly.",
                    rj, intro_for(rj, f"remote {e(name)} "), trail=(("Remote", "remote/"),))
    rcats = "".join(tile(f"remote/{s}/", CAT[s], c) for s in CAT if (c := sum(j["remote"] for j in by_cat[s])) >= 5)
    # the remote hub also answers "remote jobs in my field", "remote and part-time", "remote and well paid": one link each
    rfams = "".join(tile(f"categories/{fs}/remote/", fn, c) for fs, fn, _, _, js_ in fam_rows if (c := sum(j["remote"] for j in js_)) >= 20)
    rkinds = "".join(f'<li><a href="{P}/{u}">{e(nm)}</a></li>' for u, nm in (
        ("work-from-anywhere/", "Open to any country"), ("remote/new/", "Posted in the last 3 days"), ("remote/entry-level/", "Entry-level"), ("remote/full-time/", "Full-time"),
        ("remote/part-time/", "Part-time"), ("remote/contract/", "Contract"), ("salary/100k/remote/", "Paying $100K or more"), ("salary/200k/remote/", "Paying $200K or more"),
        ("insights/highest-paying-remote-jobs/", "The 40 best paid"), ("insights/companies-hiring-remotely/", "Companies with the most remote roles")))
    remote_more = (section("Remote jobs by field", f'<ul class="tiles">{rfams}</ul>', ("categories/", "All categories")) if rfams else "") + \
        f'<div class="dir"><div class="dirb"><h2><span>Kinds of remote work</span></h2><ul>{rkinds}</ul></div></div>'
    listing("remote/", "Remote tech jobs", f"Remote Tech Jobs — {roles(len(remote), 'open role')} | {SITE}",
            f"{roles(len(remote), 'remote job')} at tech companies: engineering, marketing, support, compliance and more.",
            remote, intro_for(remote, "remote "), extra=f'<ul class="tiles">{rcats}</ul>{rel(REL["remote"])}{remote_more}<div class="sec"><div class="sec-head"><h2>All remote tech jobs</h2></div></div>', feed=True, faq="remote tech jobs")
    crypto = [j for j in active if j.get("crypto")]
    if crypto:
        ccats = "".join(tile(f"crypto/{s}/", CAT[s], c) for s in CAT if (c := sum(1 for j in crypto if j["cat"] == s)) >= 5)
        listing("crypto/", "Crypto & web3 jobs", f"Crypto & Web3 Jobs — {roles(len(crypto), 'open role')} | {SITE}",
                f"{roles(len(crypto))} at crypto and web3 companies: exchanges, wallets, blockchain infrastructure and DeFi. Updated hourly.",
                crypto, intro_for(crypto, "", " at crypto and web3 companies"),
                extra=f'<ul class="tiles">{ccats}</ul><div class="sec"><div class="sec-head"><h2>All crypto &amp; web3 jobs</h2></div></div>', feed=True, faq="crypto and web3 jobs")
        for s, name in CAT.items():
            cj = [j for j in crypto if j["cat"] == s]
            if len(cj) >= 5:
                listing(f"crypto/{s}/", f"{name} jobs in crypto & web3", f"{name} Jobs in Crypto & Web3 ({len(cj):,} open) | {SITE}",
                        f"{roles(len(cj), name + ' job')} at crypto and web3 companies. Remote and on-site roles, updated hourly.",
                        cj, intro_for(cj, f"{e(name)} ", " at crypto and web3 companies"), trail=(("Crypto & web3", "crypto/"),))
        cr = [j for j in crypto if j["remote"]]
        if len(cr) >= 5:
            listing("crypto/remote/", "Remote crypto & web3 jobs", f"Remote Crypto Jobs — {roles(len(cr), 'open role')} | {SITE}",
                    f"{roles(len(cr), 'remote job')} at crypto and web3 companies. Work from anywhere, updated hourly.",
                    cr, intro_for(cr, "remote ", " at crypto and web3 companies"), trail=(("Crypto & web3", "crypto/"),))
    sal = [j for j in active if j["salary"]]
    listing("with-salary/", "Tech jobs with salary listed", f"Tech Jobs With Salary Listed ({len(sal):,}) | {SITE}",
            "Tech jobs where the employer publishes the salary range up front.", sal, intro_for(sal, "", " with a published salary range"))
    jr = [j for j in active if j["entry"]]
    listing("entry-level/", "Entry-level tech jobs & internships", f"Entry-Level Tech Jobs & Internships ({len(jr):,}) | {SITE}",
            "Internships and junior roles at tech companies: a way into the industry without years of experience.", jr,
            intro_for(jr, "entry-level "))
    for t, js in by_tag.items():
        listing(f"skills/{tslug(t)}/", f"{t} jobs in tech", f"{t} Jobs in Tech ({len(js):,} open) | {SITE}",
                f"{roles(len(js))} at tech companies that ask for {t}.", js,
                (f"<strong>{e(t)}</strong>: {e(skills_info.INFO[t][1])}. " if t in skills_info.INFO else "") + intro_for(js, "", f" mentioning {e(t)}", hub=True),
                trail=(("All jobs", "jobs/"),), feed=True, extra=sponsor_line("skill:" + tslug(t)) + hub_stats(js) + rel(REL["tag:" + t]) + cmp_links(t) + hub_sections(f"{t} roles", js, "skills")[0], hub=hub_sections(f"{t} roles", js, "skills")[1], list_title=f"Newest {t} jobs",
                faq=f"{t} jobs", faq_first=((f"What is {t}?", f"{skills_info.plain(t)} {len(js):,} open roles on {SITE} ask for it as of {fdate(TODAY)}.") if t in skills_info.INFO else None),
                after=section(f"Companies hiring for {t}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in js).most_common(12)) + "</ul>",
                              (f"salaries/{tslug(t)}/", f"{t} salaries") if sum(1 for j in js if j["usd"]) >= 30 else None))
    # Which kinds of work sit close to each other: two roles are neighbours when employers ask for the same skills in both.
    BROAD = {"analyst", "coordinator", "director", "executive", "growth", "intern", "staff-engineer", "founding-team", "bilingual", "government", "energy", "payments", "consulting", "operators"}
    role_sk, role_med = {}, {}
    for s_, (nm_, js_) in by_role.items():
        if s_ in BROAD or s_.endswith("-speaking"): continue
        cnt_ = Counter(t for j in js_ for t in j["tags"])
        role_sk[s_] = {t for t, k in cnt_.most_common(12) if k >= max(3, len(js_) * 0.04)}
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in js_ if j["usd"]]
        role_med[s_] = median(mids_) if len(mids_) >= 30 else 0
    def neighbours(slug_r):
        mine = role_sk.get(slug_r) or set()
        if len(mine) < 3: return ""
        cand = sorted(((len(mine & sk_) / len(mine | sk_), o) for o, sk_ in role_sk.items() if o != slug_r and len(mine & sk_) >= 3), reverse=True)[:5]
        if len(cand) < 2: return ""
        rows_ = ""
        for sc, o in cand:
            shared = sorted(mine & role_sk[o], key=lambda t: -skill_counts[t])[:4]
            pay = ""
            if role_med.get(slug_r) and role_med.get(o):
                dlt = role_med[o] - role_med[slug_r]
                pay = f'{money(role_med[o])}, {"about the same" if abs(dlt) < 5000 else money(abs(dlt)) + (" more" if dlt > 0 else " less")}'
            rows_ += (f'<a href="{P}/roles/{o}/"><span class="hn">{e(by_role[o][0])}</span><span class="hb"><i style="width:{round(100 * sc / cand[0][0])}%"></i></span>'
                      f'<span class="hc">{e(", ".join(shared))}{" · " + pay if pay else ""}</span></a>')
        return section("Kinds of work close to this one", '<p class="note">Roles where employers ask for the same skills. The bar shows how much the skill lists overlap; the text names the shared skills'
                       ' and, where 30 postings state pay, the median advertised pay there.</p><div class="hbars moves">' + rows_ + "</div>")
    for slug_r, (rname, rj) in by_role.items():
        paid_r = sum(1 for j in rj if j["usd"])
        low, w_ = rlow(rname), roles_info.INFO.get(slug_r, ("", ""))[1]
        many = ROLE_PLURAL.get(rname, low + "s")
        fams = [(fs, fn) for fs, fn, _, live, _ in fam_rows if any(s_ == slug_r for s_, _, _ in live)]
        fam_line = ('<p class="note cmpl">Part of: ' + " · ".join(f'<a href="{P}/categories/{fs}/">{e(fn)}</a>' for fs, fn in fams) + "</p>") if fams else ""
        secs = hub_sections(f"{low} roles", rj, "roles")
        listing(f"roles/{slug_r}/", f"{rname} jobs", f"{tcase(rname)} Jobs ({len(rj):,} open) | {SITE}",
                f"{roles(len(rj), 'open role')} for {many}, straight from employers’ careers pages." + (f" A person in this job {w_}." if w_ else "") + " Remote filter, salary data, updated hourly.",
                rj, (f"<strong>{e(rname)}</strong>: a person in this job {e(w_)}. " if w_ else "") + intro_for(rj, "", f" with “{e(rname)}” or a close variant in the title", hub=True),
                trail=(("Categories", "categories/"),), feed=True, extra=hub_stats(rj) + mini_pics(rj) + fam_line + rel(REL["role:" + slug_r]) + secs[0], faq=f"{low} jobs",
                faq_first=((f"What is {art(low)} {low} job?", f"In {art(low)} {low} job, a person {w_}. {len(rj):,} such roles are open on {SITE} as of {fdate(TODAY)}.") if w_ else None),
                hub=secs[1], list_title=f"Newest {low} jobs", more=None if slug_r in ROLE_BASE else False,
                after=neighbours(slug_r) + section(f"Companies hiring {many}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in rj).most_common(12)) + "</ul>",
                              (f"salaries/{slug_r}/", f"{rname} salary") if paid_r >= 30 else None))

    # The directory: every category with the kinds of work in it, on one page, and a page with text for each category
    kinds = "".join(f'<li><a href="{P}/{u}">{e(nm)}</a></li>' for u, nm in (
        ("remote/", "Remote jobs"), ("work-from-anywhere/", "Work from anywhere"), ("new/", "New in the last 3 days"), ("entry-level/", "Entry-level jobs"), ("internships/", "Internships"),
        ("contract/", "Contract jobs"), ("part-time/", "Part-time jobs"), ("with-salary/", "Jobs that state pay"), ("salary/200k/", "Jobs that pay $200K or more"), ("perks/visa-sponsorship/", "Jobs with visa sponsorship")))
    dir_tail = (f'<div class="dirb"><h2><a href="{P}/jobs/"><u>By type of work</u></a></h2><p>How and when the work is done.</p><ul>{kinds}</ul></div>'
                f'<div class="dirb"><h2><a href="{P}/skills/"><u>By skill or tool</u></a><span>{len(skill_counts)}</span></h2><p>Jobs that ask for a language, a program or a method by name.</p><ul>'
                + "".join(f'<li data-n="{e(t.lower())}"><a href="{P}/skills/{tslug(t)}/">{e(t)} jobs</a><span>{c:,}</span></li>' for t, c in skill_counts.most_common(14))
                + f'<li class="more"><a href="{P}/skills/">All {len(skill_counts)} skills</a></li></ul></div>')
    dir_html = '<div class="dir" id="dir">' + "".join(dir_block(*f) for f in fam_rows) + dir_tail + "</div>"
    dir_filter = ('<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, lawyer or designer" aria-label="Find a category"></p>'
                  '<p class="lead" id="dirnone" hidden>No category with these words. Try the <a href="' + P + '/jobs/">job search</a>: it looks through every title.</p>')
    dir_qa = [("How are jobs sorted into categories?", "By the job title. Each kind of work has a list of the titles employers use for it, and a posting whose title matches is listed there. A posting can sit in two categories when its title belongs to both, for example a staff backend engineer."),
              ("Are these only technology jobs?", f"No. The employers are mostly technology, finance, health, space and consumer companies, and they hire for every kind of work: {len(fam_rows)} fields here, from software and data to sales, accounting, law, nursing, warehouses and shops."),
              ("Why is a category missing?", "A kind of work gets a page when at least 20 open jobs match it. Smaller ones are still found through the search."),
              ("How often are the lists updated?", "Every time the employers’ careers pages are read again, which is every hour. A job that the employer has closed leaves the lists and moves to the archive.")]
    dir_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in dir_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    dir_faq = section("Questions about the categories", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in dir_qa) + "</dl>")
    page("categories/", f"Job Categories: {len(by_role)} kinds of work in {len(fam_rows)} fields | {SITE}",
         f"Browse {n:,} open jobs by category: {len(fam_rows)} fields and {len(by_role)} kinds of work, from software and data to sales, finance, law, healthcare and the factory floor. Each has its own page.",
         crumbs(("Categories", "")) + '<h1>Browse all job <span class="hl">categories</span></h1>'
         f'<p class="lead">{n:,} open jobs, sorted into {len(fam_rows)} fields and {len(by_role)} kinds of work. Pick a field to read what the work is and see who is hiring, or go straight to a kind of work. '
         'The number next to each name is how many jobs are open today.</p>' + dir_filter + dir_html + dir_faq, head=dir_ld)
    page("roles/", f"Jobs by Role: {len(by_role)} job titles | {SITE}", f"Every kind of work with open jobs, A to Z: {len(by_role)} roles, each with remote, entry-level, city and salary pages.",
         crumbs(("Categories", "categories/"), ("All roles", "")) + '<h1>All roles, A to Z</h1><p class="lead">Job titles differ from company to company, so each role here gathers the variants employers use. '
         f'The same roles grouped by field are on the <a href="{P}/categories/">categories page</a>.</p>'
         '<ul class="tiles">' + "".join(tile(f"roles/{s_}/", nm, len(js_)) for s_, (nm, js_) in sorted(by_role.items(), key=lambda kv: kv[1][0].lower())) + "</ul>")
    for fs, fn, fd, live, js_ in fam_rows:
        low_f, names_ = rlow(fn), [nm for _, nm, _ in live]
        role_list = '<ul class="gloss">' + "".join(f'<li><a href="{P}/roles/{s_}/"><b><u>{e(nm)}</u></b><span class="c">{c:,} jobs</span><span class="d">{e(roles_info.what(s_))}</span></a></li>' for s_, nm, c in live) + "</ul>"
        rank_ = (f'<p class="note cmpl">Ranking: <a href="{P}/insights/companies-hiring-{fs}/">companies hiring for {e(low_f)} jobs</a>, with remote roles and pay</p>'
                 if len({j["company"] for j in js_}) >= 8 else "")
        others = rank_ + '<p class="note cmpl">Other categories: ' + " · ".join(f'<a href="{P}/categories/{o}/">{e(on)}</a>' for o, on, _, _, _ in fam_rows if o != fs) + "</p>"
        secs = hub_sections(low_f, js_, "roles")
        vers = []
        for vslug, vname, vjs in (("remote", "Remote", [j for j in js_ if j["remote"]]), ("entry-level", "Entry-level", [j for j in js_ if j["entry"]])):
            if len(vjs) < 20: continue
            vers.append(f'<a href="{P}/categories/{fs}/{vslug}/">{vname} {e(low_f)} jobs</a> ({len(vjs):,})')
            listing(f"categories/{fs}/{vslug}/", f"{vname} {low_f} jobs", f"{vname} {tcase(fn)} Jobs ({len(vjs):,} open) | {SITE}",
                    f"{len(vjs):,} open {vname.lower()} jobs in {low_f}: {', '.join(rlow(x) for x in names_[:4])} and more. Read from employers’ own careers pages and checked against them.",
                    vjs, f"<strong>{e(fn)}</strong> is {e(fd)}. " + intro_for(vjs, f"{vname.lower()} ", "", hub=True), trail=(("Categories", "categories/"), (fn, f"categories/{fs}/")), per=50, max_pages=2, more=False,
                    extra=hub_stats(vjs), faq=f"{vname.lower()} {low_f} jobs")
        vers_line = ('<p class="note cmpl">Also: ' + " · ".join(vers) + "</p>") if vers else ""
        listing(f"categories/{fs}/", f"{fn} jobs", f"{tcase(fn)} Jobs ({len(js_):,} open) | {SITE}",
                f"{len(js_):,} open jobs in {low_f}: {', '.join(rlow(x) for x in names_[:4])} and more. Read from employers’ own careers pages and checked hourly.",
                js_, f"<strong>{e(fn)}</strong> is {e(fd)}. " + intro_for(js_, "", "", hub=True), trail=(("Categories", "categories/"),), per=50, max_pages=3, more=False, feed=True,
                extra=hub_stats(js_) + mini_pics(js_) + vers_line + section(f"Kinds of work in {low_f}", role_list), list_title=f"Newest {low_f} jobs", faq=f"{low_f} jobs",
                faq_first=(f"Which jobs count as {low_f}?", f"{fd[0].upper() + fd[1:]}. On {SITE} that is {len(live)} kinds of work: {', '.join(names_)}."),
                hub=secs[1], after=section(f"Who is hiring in {low_f}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in js_).most_common(12)) + "</ul>") + others)
    for name, slug, js in places:
        short = name.removeprefix("the ")
        listing(f"locations/{slug}/", f"Tech jobs in {name}", f"Tech Jobs in {short} ({len(js):,} open) | {SITE}",
                f"{roles(len(js), 'tech job')} in {name}. Startups and established tech companies hiring now.",
                js, intro_for(js, "", f" in {e(name)}", hub=True), trail=(("Locations", "locations/"),), extra=hub_stats(js) + rel(REL["place:" + slug]) + hub_sections(f"tech roles in {short}", js, "places")[0], faq=f"tech jobs in {name}", feed=True,
                hub=hub_sections(f"tech roles in {short}", js, "places")[1], list_title=f"Newest tech jobs in {short}")
    page("locations/", f"Tech Jobs by Location | {SITE}", "Browse tech jobs by city, country and region.",
         crumbs(("Locations", "")) + f'<h1>Tech jobs by location</h1><p class="lead">Open roles per place. A job that lists several locations appears in each of them.</p><ul class="tiles">{place_html}</ul>')

    # Companies (+ per-company data for the embeddable widget)
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    fresh_n = {c: sum(1 for j in js if j["active"] and (j.get("posted") or "") >= week_ago) for c, js in comp_items}

    def co_tile(c, js):
        n, w = sum(j["active"] for j in js), fresh_n[c]
        up = f'<span class="up" title="{w:,} posted in the last 7 days">+{w:,}</span>' if w else ""
        return (f'<li data-n="{e(c.lower())}" data-o="{n}" data-w="{w}"><a class="tile" href="{P}/companies/{slugify(c)}/">{ava(c, "sm")}'
                f'<span class="n">{e(c)}</span>{up}<span class="c">{n:,}</span></a></li>')
    grid = "".join(co_tile(c, js) for c, js in comp_items)
    top_open = [(c, sum(j["active"] for j in js)) for c, js in comp_items[:3]]
    top_new = [(c, n) for c, n in sorted(fresh_n.items(), key=lambda kv: -kv[1])[:3] if n]
    names = lambda xs: " and ".join(filter(None, [", ".join(f"{e(c)} ({n:,})" for c, n in xs[:-1]), f"{e(xs[-1][0])} ({xs[-1][1]:,})"])) if xs else ""
    co_lead = f"{len(companies)} employers with open roles today. {names(top_open)} have the most." if len(top_open) > 1 else f"{len(companies)} employers with open roles today."
    if top_new:
        co_lead += (f" {sum(1 for n in fresh_n.values() if n):,} of them posted new roles in the last 7 days, led by {names(top_new)}."
                    ' The <span class="up">+N</span> mark in the list is that weekly number.')
    page("companies/", f"Tech Companies Hiring Now — {len(companies)} employers | {SITE}",
         "Tech companies with open roles: startups, scale-ups and public companies across software, AI, fintech and crypto.",
         crumbs(("Companies", "")) + f'<h1>Tech companies hiring now</h1><p class="lead">{co_lead}</p>'
         '<input type="search" id="cfilter" placeholder="Filter companies by name" aria-label="Filter companies">'
         '<div class="tabs csort" id="csort" role="group" aria-label="Sort companies" hidden>'
         '<button class="tab" type="button" data-s="o" aria-pressed="true">Most open roles</button>'
         '<button class="tab" type="button" data-s="w" aria-pressed="false">Most new this week</button>'
         '<button class="tab" type="button" data-s="n" aria-pressed="false">A–Z</button></div>'
         + (section("Featured employers", spot_tiles(spot_cos)) if spot_cos else "") +
         f'<ul class="tiles" id="clist" style="margin-top:14px">{grid}</ul><p class="note" id="cnone" hidden>No company with that name.</p>')
    STACK = {c: [t for t, _ in Counter(t for j in js if j["active"] for t in j["tags"]).most_common(10)] for c, js in companies.items()}
    PLACE_NAME = {slug: name.removeprefix("the ") for name, slug, _ in PLACES}
    PLACE_LIVE = {slug for _, slug, _ in places}
    PLACE_SLUG = {v: k for k, v in PLACE_NAME.items()}
    for c, js in companies.items():
        slug = slugify(c)
        act, arc = order([j for j in js if j["active"]]), order([j for j in js if not j["active"]])
        write(f"data/companies/{slug}.json", json.dumps({
            "company": c, "site": SITE, "page": f"{FULL}/companies/{slug}/", "total": len(act),
            "jobs": [{"title": j["title"], "url": f"{FULL}/job/{j['slug']}/", "location": j["location"], "remote": j["remote"]} for j in act[:50]],
        }, ensure_ascii=False, separators=(",", ":")), sitemap=False)
        sal_mid = [(lo + hi) / 2 for j in act if j["usd"] for lo, hi in [j["usd"]]]
        top_cats = Counter(CAT[j["cat"]] for j in act).most_common(3)
        rem_c = sum(j["remote"] for j in act)
        facts = [("Open roles", f"{len(act):,}"), ("Remote", f"{rem_c:,}")]
        if len(act) >= 10:
            facts.append(("State the pay", f"{100 * sum(bool(j['salary']) for j in act) / len(act):.0f}%"))
            old_ = sum(1 for j in act if (j["posted"] or j["first_seen"])[:10] <= (datetime.date.today() - datetime.timedelta(days=LONG_OPEN)).isoformat())
            facts.append((f"Open {LONG_OPEN} days or more", f"{100 * old_ / len(act):.0f}%"))
        if len(sal_mid) >= 15: facts.append((f"Median advertised salary, {len(sal_mid)} postings", money(median(sal_mid))))
        op_, cl_, mood = PULSE.get(c, (0, 0, "Steady"))
        facts.append((f"This week · {mood.lower()}", f"+{op_} / −{cl_}"))
        chips = [f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in facts]
        cats_txt = [e(name) for name, _ in top_cats if name != OTHER[1]]
        lead = ((f"{e(c)} has {roles(len(act), 'open role')} right now" + (f", {rem_c:,} of them remote" if rem_c else "") + "."
                 + (f" Most are in {', '.join(cats_txt[:-1]) + ' and ' + cats_txt[-1] if len(cats_txt) > 1 else cats_txt[0]}." if cats_txt else "")
                 + f" Read from its own careers page and checked on {fdate(TODAY, False)}.") if act else "No open roles right now. Past openings are below.")
        closed = section(f"Closed jobs at {c}", f'<ul class="jobs">{"".join(card(j) for j in arc[:200])}</ul>', sid="closed") if arc else ""
        embed = (f'<details class="embed"><summary>Work at {e(c)}? Show these jobs and a live hiring badge on your own site</summary>'
                 f'<p class="note">Jobs widget: paste where the list should appear. It stays in sync automatically.</p><pre><code>{embed_code("company:" + slug, "Jobs at " + c, f"companies/{slug}/")}</code></pre>'
                 f'<p class="note">Live badge with your current number of open roles:</p><p><img src="{P}/badge/companies/{slug}.svg" alt="{e(c)} is hiring" height="28"></p>'
                 f'<pre><code>{badge_code(f"badge/companies/{slug}.svg", c + " is hiring", f"companies/{slug}/")}</code></pre>'
                 f'<p class="note"><a href="{P}/widgets/">More widgets and badges</a></p></details>')
        stack = [t for t, _ in Counter(t for j in act for t in j["tags"]).most_common(10)]
        where = Counter(p_ for j in act for p_ in j["places"] if p_ in PLACE_LIVE).most_common(6)      # only places that have a page
        sim = sorted(((len(set(stack) & set(STACK[o])), OPEN[o], o) for o in STACK if o != c and len(set(stack) & set(STACK[o])) >= 4), reverse=True)[:6]
        overview = ""
        if stack:
            overview += section(f"Tech stack at {c}", sid="stack", inner='<div class="rel">' + "".join(f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a>' for t in stack) + "</div>"
                                '<p class="note">Skills mentioned most often across its open roles.</p>')
        if where:
            overview += section(f"Where {c} is hiring", '<div class="rel">' + "".join(f'<a href="{P}/locations/{p_}/">{e(PLACE_NAME[p_])} · {k}</a>' for p_, k in where) + "</div>", sid="where")
        if sim:
            overview += section(f"Companies like {c}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(o)}/", o, OPEN[o], True) for _, _, o in sim) + "</ul>"
                                '<p class="note">Based on the skills they hire for.</p>', sid="similar")
        head_html = (crumbs(("Companies", "companies/"), (c, ""))
                     + f'<div class="jhead">{ava(c, "lg")}<div><h1>Jobs at {e(c)}</h1><span class="js">{lead}</span>'
                     + f'<p style="margin:12px 0 0"><button class="btn ghost sm" id="follow" type="button" data-slug="{slug}" data-name="{e(c)}" style="margin-top:0">Follow {e(c)}</button> '
                       f'<span class="note">Get a “new roles” count for this company in My jobs.</span></p></div></div>'
                     + (f'<dl class="facts">{"".join(chips)}</dl>' if act else "")
                     + '<nav class="anch" aria-label="On this page">' + (f'<a href="#jobs">Jobs <b>{len(act):,}</b></a>' if act else "")
                     + ('<a href="#stack">Tech stack</a>' if stack else "") + ('<a href="#where">Locations</a>' if where else "") + ('<a href="#similar">Similar companies</a>' if sim else "")
                     + (f'<a href="#closed">Closed <b>{len(arc):,}</b></a>' if arc else "") + '</nav><div id="jobs"></div>')
        listing(f"companies/{slug}/", f"Jobs at {c}", f"{c} Jobs — {roles(len(act), 'open role')} | {SITE}",
                f"All jobs at {c}: {len(act):,} open" + (f" and {len(arc):,} closed" if arc else "") + ". Categories, locations and remote roles.",
                act, head_html=head_html, after=overview + closed + embed, faq=f"jobs at {c}", feed=True)

    # One-paragraph hiring summary per company, shown on each of its job pages
    for c, js in companies.items():
        act = [j for j in js if j["active"]]
        if not act: continue
        tops = [name for name, _ in Counter(CAT[j["cat"]] for j in act if j["cat"] != OTHER[0]).most_common(3)]
        mids = [(lo + hi) / 2 for j in act if j["usd"] for lo, hi in [j["usd"]]]
        rem = sum(j["remote"] for j in act)
        FACT[c] = (f"{e(c)} has {roles(len(act), 'open role')} right now" + (f", {rem:,} of them remote" if rem else "") + "."
                   + (f" Most are in {e(', '.join(tops[:-1]) + ' and ' + tops[-1] if len(tops) > 1 else tops[0])}." if tops else "")
                   + (f" The median advertised salary across its roles with a published range is {money(median(mids))}." if len(mids) >= 15 else ""))

    # Job pages + archive
    for j in archived:
        if j.get("closed"):
            key = (j["company"], j["title"].lower(), j["location"].lower())
            REPOST[key] = max(REPOST.get(key, ""), j["closed"])
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
    def level_table(group, minimum=15):  # pay ladder: median and middle half per seniority level; "" when there is too little data
        rows_ = []
        for lv, name in (("Intern", "Intern"), ("Junior", "Junior"), ("Senior", "Senior"), ("Lead", "Lead and above"), ("", "No level in title")):
            ms = sorted((lo + hi) / 2 for j, (lo, hi) in group if j["level"] == lv)
            if len(ms) >= minimum: rows_.append((lv, name, median(ms), ms[len(ms) // 4], ms[min(len(ms) - 1, len(ms) * 3 // 4)], len(ms)))
        if sum(1 for r in rows_ if r[0]) < 2: return ""
        med = {r[0]: r[2] for r in rows_}
        lo_, hi_ = ("Junior", "Senior") if "Junior" in med and "Senior" in med else ("Senior", "Lead") if "Senior" in med and "Lead" in med else (None, None)
        answer = ""
        if lo_ and med[hi_] > med[lo_]:
            answer = (f"<p>{hi_} roles advertise a median of {money(med[hi_])}, {round((med[hi_] / med[lo_] - 1) * 100)}% more than {lo_.lower()} roles ({money(med[lo_])}). "
                      "The level comes from the job title; titles without a level word are counted separately.</p>")
        body_ = "".join(f'<tr><td>{e(name)}</td><td><strong>{money(m_)}</strong></td><td style="white-space:nowrap">{money(q1)}–{money(q3)}</td><td>{c:,}</td></tr>' for _, name, m_, q1, q3, c in rows_)
        return answer + f'<div class="tablewrap t4"><table><tr><th>Level</th><th>Median salary</th><th>Middle half</th><th>Roles</th></tr>{body_}</table></div>'
    def level_section(title, group):
        t_ = level_table(group)
        return section(title, t_) if t_ else ""
    page("salaries/", f"Tech Salaries From Live Job Postings ({len(paid):,} roles) | {SITE}",
         "Median salaries in tech by role, skill and company, calculated from salary ranges in open job postings. Updated daily.",
         crumbs(("Salaries", "")) + "<h1>Tech salaries from live job postings</h1>"
         f'<p class="lead">{100 - SALPCT}% of open tech postings do not state a salary, which leaves candidates guessing. These figures come from the {len(paid):,} open roles that do publish a yearly US-dollar range. '
         f'Each figure is a <a href="{P}/glossary/#median">median</a>: half of the postings advertise more than it, half less. These are advertised ranges, not what people are actually paid.</p>'
         + section("By category", table(g_cat, lambda k: f"salaries/{cat_slug[k]}/" if len(g_cat[k]) >= 30 and k != OTHER[1] else f"jobs/{cat_slug[k]}/", 10))
         + level_section("Tech salaries by level, intern to lead", paid)
         + section("By skill", table(g_tag, lambda k: f"salaries/{TAG_SLUG.get(k, slugify(k))}/" if len(g_tag[k]) >= 30 else f"skills/{TAG_SLUG.get(k, slugify(k))}/"))
         + section("By company", table(g_comp, lambda k: f"companies/{slugify(k)}/", 8))
         + section("Highest-paying open roles", f'<ul class="jobs">{"".join(card(j) for j, _ in diverse_pairs(best, 30))}</ul>', ("with-salary/", "All jobs with salary")) + cite("salaries/", "Tech salaries from live job postings"))

    def salary_page(slug, label, group, back):
        by_loc = defaultdict(list)
        for j, r in group:
            for ps in j["places"]: by_loc[PLACE_NAME[ps]].append((j, r))
        cut = level_section(f"{label} salary by level", group) + \
              (section(f"{label} salary by location", table(by_loc, lambda k: f"locations/{PLACE_SLUG[k]}/", 15, 20)) if sum(len(v) >= 15 for v in by_loc.values()) >= 2 else "")
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
             + cut + section("Top-paying companies", table(comp, lambda k: f"companies/{slugify(k)}/", 3, 25))
             + section(f"Highest-paying open {label} roles", f'<ul class="jobs">{"".join(card(j) for j, _ in top_jobs)}</ul>', back)
             + cite(f"salaries/{slug}/", f"{label} salaries in tech"))
    for t, group in g_tag.items():
        if len(group) >= 30:
            salary_page(TAG_SLUG.get(t, slugify(t)), t, group, (f"skills/{TAG_SLUG.get(t, slugify(t))}/", f"All {t} jobs"))
    for name, group in g_cat.items():
        if len(group) >= 30 and name != OTHER[1]:
            salary_page(cat_slug[name], name, group, (f"jobs/{cat_slug[name]}/", f"All {name} jobs"))
    for slug_r, (rname, rj) in by_role.items():
        group = [(j, j["usd"]) for j in rj if j["usd"]]
        if len(group) >= 30: salary_page(slug_r, tcase(rname), group, (f"roles/{slug_r}/", f"All {rlow(rname)} jobs"))

    # Hiring trends: one page of live numbers
    week = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    new7 = [j for j in active if (j["posted"] or "") >= week]
    pctf = lambda a, b: f"{100 * a / b:.0f}%" if b else "—"
    def trow(cells): return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"
    def ttable(head, rows_): return ('<div class="tablewrap"><table><tr>' + "".join(f"<th>{h}</th>" for h in head) + "</tr>" + "".join(rows_) + "</table></div>")
    med = lambda js: (money(median([(lo + hi) / 2 for j in js if j["usd"] for lo, hi in [j["usd"]]])) if sum(1 for j in js if j["usd"]) >= 15 else "—")
    top_skill = max((len(js) for js in by_tag.values()), default=1)
    barc = lambda v, mx, label: f'<span class="bar"><i style="width:{max(2, round(100 * v / mx))}%"></i></span>{label}'
    skills_rows = [trow([f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a>', f"{len(js):,}", barc(len(js), top_skill, pctf(len(js), n)), pctf(sum(j["remote"] for j in js), len(js)), med(js)])
                   for t, js in sorted(by_tag.items(), key=lambda kv: -len(kv[1]))[:25]]
    comp_rows = [trow([f'<a href="{P}/companies/{slugify(c)}/">{e(c)}</a>', f"{sum(j['active'] for j in js):,}",
                       pctf(sum(j["remote"] for j in js if j["active"]), sum(j["active"] for j in js)), f"{sum(1 for j in js if j['active'] and (j['posted'] or '') >= week):,}"])
                 for c, js in comp_items[:25]]
    top_cat = max((len(v) for v in by_cat.values()), default=1)
    cat_rows = [trow([f'<a href="{P}/jobs/{cs}/">{e(CAT[cs])}</a>', f"{len(by_cat[cs]):,}", barc(len(by_cat[cs]), top_cat, pctf(len(by_cat[cs]), n)), pctf(sum(j["remote"] for j in by_cat[cs]), len(by_cat[cs])), med(by_cat[cs])])
                for cs in sorted(CAT, key=lambda k: -len(by_cat[k])) if by_cat[cs]]
    place_rows = [trow([f'<a href="{P}/locations/{slug}/">{e(name.removeprefix("the "))}</a>', f"{len(js):,}", barc(len(js), max(len(x[2]) for x in places), pctf(len(js), n))]) for name, slug, js in sorted(places, key=lambda x: -len(x[2]))]
    page("trends/", f"Tech Job Market {TODAY[:4]}: hiring trends from {n:,} open roles | {SITE}",
         "Which skills, companies, roles and cities are hiring in tech right now. Live numbers from open job postings, updated daily.",
         crumbs(("Hiring trends", "")) + "<h1>Tech hiring trends</h1>"
         '<p class="plain"><b>In plain words:</b> the tech job market in numbers, counted from the jobs that are open today: which skills employers ask for, who is hiring, where.</p>'
         f'<p class="lead">Live numbers from {n:,} open roles at {m} tech companies, recalculated every day. Feel free to quote them with a link to this page.</p>'
         f'<div class="statrow"><div class="stat"><b>{n:,}</b><span>open roles</span></div><div class="stat"><b>{len(new7):,}</b><span>posted in the last 7 days</span></div>'
         f'<div class="stat"><b>{pctf(len(remote), n)}</b><span>are remote</span></div><div class="stat"><b>{pctf(sum(bool(j["salary"]) for j in active), n)}</b><span>publish a salary</span></div></div>'
         + section("Most in-demand skills", ttable(["Skill", "Open roles", "Share of all roles", "Remote", "Median salary"], skills_rows))
         + section("Companies hiring the most", ttable(["Company", "Open roles", "Remote", "Posted this week"], comp_rows), ("companies/", "All companies"))
         + section("Roles by category", ttable(["Category", "Open roles", "Share", "Remote", "Median salary"], cat_rows))
         + section("Roles by location", ttable(["Location", "Open roles", "Share"], place_rows), ("locations/", "All locations"))
         + '<p class="note">Salary figures are medians of advertised US-dollar ranges and are shown only where at least 15 roles publish one. A role that lists several locations is counted in each.</p>'
         + f'<p class="note">Download the numbers: <a href="{P}/data/open/skills.csv">skills.csv</a>, <a href="{P}/data/open/companies.csv">companies.csv</a>, '
           f'<a href="{P}/data/open/categories.csv">categories.csv</a>, <a href="{P}/data/open/locations.csv">locations.csv</a>.</p>' + cite("trends/", "Tech hiring trends"))

    # Compare: two skills head to head, from the same live postings. Every number on these pages is ours.
    def skill_facts(t):
        js = by_tag[t]; mids = sorted((lo + hi) / 2 for j in js if j["usd"] for lo, hi in [j["usd"]])
        return {"n": len(js), "remote": sum(j["remote"] for j in js), "entry": sum(j["entry"] for j in js), "senior": sum(j["level"] in ("Senior", "Lead") for j in js),
                "new": sum(1 for j in js if (j["posted"] or "") >= week), "med": median(mids) if len(mids) >= 30 else None, "paid": len(mids),
                "top": Counter(j["company"] for j in js).most_common(5), "co": [x for x, _ in Counter(x for j in js for x in j["tags"] if x != t).most_common(5)], "ids": {j["id"] for j in js}}
    facts = {t: skill_facts(t) for t in CMP}
    times = lambda hi, lo: f"{hi / lo:.1f} times" if hi / lo >= 1.15 else "about"
    for i, a in enumerate(CMP):
        for b in CMP[i + 1:]:
            A, B = facts[a], facts[b]; both = len(A["ids"] & B["ids"]); path = cmp_path(a, b)
            (big, BG), (small, SM) = ((a, A), (b, B)) if A["n"] >= B["n"] else ((b, B), (a, A))
            demand = (f"{big} is asked for in {BG['n']:,} open roles and {small} in {SM['n']:,}, so {big} shows up in {times(BG['n'], SM['n'])} as many postings."
                      if BG["n"] / SM["n"] >= 1.15 else f"{a} and {b} are asked for about equally often: {A['n']:,} and {B['n']:,} open roles.")
            if A["med"] and B["med"]:
                (rich, RM), (poor, PM) = ((a, A["med"]), (b, B["med"])) if A["med"] >= B["med"] else ((b, B["med"]), (a, A["med"]))
                pay = (f"{rich} roles advertise the higher median salary: {money(RM)} against {money(PM)} for {poor}." if RM - PM >= 3000
                       else f"Advertised pay is about the same: a median of {money(A['med'])} for {a} and {money(B['med'])} for {b}.")
            else:
                pay = "Too few of these postings publish a salary range to compare pay fairly."
            ra, rb = 100 * A["remote"] / A["n"], 100 * B["remote"] / B["n"]
            rem = (f"{a if ra > rb else b} roles are remote more often: {max(ra, rb):.0f}% against {min(ra, rb):.0f}% for {b if ra > rb else a}." if abs(ra - rb) >= 3
                   else f"Remote work is equally common: {ra:.0f}% of {a} roles and {rb:.0f}% of {b} roles.")
            together = (f"{both:,} open roles ask for both, which is {100 * both / SM['n']:.0f}% of all {small} roles." if both else f"No open role asks for both {a} and {b} right now.")
            comp = lambda F: ", ".join(f'<a href="{P}/companies/{slugify(c)}/">{e(c)}</a> ({k:,})' for c, k in F["top"])
            mx = max(A["n"], B["n"])
            rows_c = [trow(["Open roles", barc(A["n"], mx, f"{A['n']:,}"), barc(B["n"], mx, f"{B['n']:,}")]),
                      trow(["Share of all open tech roles", pctf(A["n"], n), pctf(B["n"], n)]),
                      trow(["Posted in the last 7 days", f"{A['new']:,}", f"{B['new']:,}"]),
                      trow(["Remote roles", barc(ra, 100, f"{ra:.0f}%"), barc(rb, 100, f"{rb:.0f}%")]),
                      trow(["Entry-level roles", pctf(A["entry"], A["n"]), pctf(B["entry"], B["n"])]),
                      trow(["Senior and lead roles", pctf(A["senior"], A["n"]), pctf(B["senior"], B["n"])]),
                      trow(["Median advertised salary", f"<strong>{money(A['med'])}</strong>" if A["med"] else "too few ranges", f"<strong>{money(B['med'])}</strong>" if B["med"] else "too few ranges"]),
                      trow(["Roles that publish a salary", f"{A['paid']:,}", f"{B['paid']:,}"]),
                      trow(["Most often asked for with", e(", ".join(A["co"])), e(", ".join(B["co"]))]),
                      trow(["Hiring the most", comp(A), comp(B)])]
            qa = [(f"Which has more jobs, {a} or {b}?", demand + f" Counted on {fdate(TODAY)} across {n:,} open roles at {m} tech companies."),
                  (f"Which pays more, {a} or {b}?", pay + " These are advertised ranges from job postings, not verified pay."),
                  (f"Is {a} or {b} better for remote work?", rem),
                  (f"Do employers ask for {a} and {b} together?", together)]
            faq_c = "".join(f"<details class='faq'><summary>{e(q_)}</summary><p>{e(a_)}</p></details>" for q_, a_ in qa)
            ld_c = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
            others = [o for o in CMP if o not in (a, b)][:6]
            page(path, f"{a} vs {b} Jobs — demand, salary, remote | {SITE}",
                 f"{a} vs {b} in live job postings: {A['n']:,} against {B['n']:,} open roles, median advertised salaries, remote share and who is hiring. Updated daily.",
                 crumbs(("Compare skills", "compare/"), (f"{a} vs {b}", "")) + f"<h1>{e(a)} vs {e(b)}: jobs, salaries and remote work</h1>"
                 f'<p class="lead">{e(a)} and {e(b)} side by side in {n:,} live tech job postings on {fdate(TODAY)}: how many roles ask for each, what they pay and how many are remote.</p>'
                 f'<div class="card verdict"><p><strong>Demand.</strong> {e(demand)}</p><p><strong>Pay.</strong> {e(pay)}</p><p><strong>Remote.</strong> {e(rem)}</p><p><strong>Together.</strong> {e(together)}</p></div>'
                 + section(f"{a} and {b} side by side", ttable(["", f'<a href="{P}/skills/{tslug(a)}/">{e(a)}</a>', f'<a href="{P}/skills/{tslug(b)}/">{e(b)}</a>'], rows_c)
                           + f'<p class="note">Source: open roles on {e(SITE)}, collected from companies\' own careers pages and recounted every day. Salary medians need at least 30 published ranges. '
                             f'<a href="{P}/methodology/">How the numbers are made</a>.</p>')
                 + f'<p class="cta2"><a class="btn" href="{P}/skills/{tslug(a)}/">See {e(a)} jobs</a> <a class="btn ghost" style="margin-top:0" href="{P}/skills/{tslug(b)}/">See {e(b)} jobs</a></p>'
                 + section(f"{a} or {b}: questions people ask", faq_c)
                 + section("More skill comparisons", '<ul class="tiles">' + "".join(tile(cmp_path(x, o), f"{x} vs {o}", len(facts[x]["ids"] | facts[o]["ids"])) for x in (a, b) for o in others[:3]) + "</ul>", ("compare/", "All comparisons"))
                 + cite(path, f"{a} vs {b}: jobs, salaries and remote work"), head=ld_c + crumbs_ld([("Compare skills", "compare/"), (f"{a} vs {b}", "")]))
    cmp_opts = "".join(f'<option value="{tslug(t)}">{e(t)}</option>' for t in CMP)
    page("compare/", f"Compare Tech Skills by Jobs, Salary and Remote Share | {SITE}",
         f"Put two tech skills head to head: open roles, median advertised salary, remote share and top employers, counted from {n:,} live job postings every day.",
         crumbs(("Compare skills", "")) + "<h1>Compare tech skills by jobs and pay</h1>"
         '<p class="plain"><b>In plain words:</b> pick two skills, for example Python and Java, and see which one more employers ask for and which one pays more.</p>'
         f'<p class="lead">Pick two skills and see how many open roles ask for each, what those roles pay and how many are remote. Counted from {n:,} live postings, and counted again every day.</p>'
         f'<div class="card"><div class="fbar" style="margin:0;align-items:flex-end"><label class="wl">First skill<select id="cmp-a">{cmp_opts}</select></label>'
         f'<label class="wl">Second skill<select id="cmp-b">{cmp_opts}</select></label><button class="btn" id="cmp-go" type="button">Compare</button></div></div>'
         + section("All skill comparisons", '<ul class="tiles">' + "".join(tile(cmp_path(a, b), f"{a} vs {b}", len(facts[a]["ids"] | facts[b]["ids"])) for i, a in enumerate(CMP) for b in CMP[i + 1:]) + "</ul>")
         + f'<script>(function(){{var o={json.dumps([tslug(t) for t in CMP])},a=document.getElementById("cmp-a"),b=document.getElementById("cmp-b");b.selectedIndex=1;'
           f'document.getElementById("cmp-go").addEventListener("click",function(){{if(a.value===b.value){{b.focus();return;}}var p=[a.value,b.value].sort(function(x,y){{return o.indexOf(x)-o.indexOf(y);}});'
           f'location.href="{P}/compare/"+p[0]+"-vs-"+p[1]+"/";}});}})();</script>')

    # My jobs: tracker kept in the visitor's browser, no account needed
    page("my-jobs/", f"Job Application Tracker — free, no sign-up, no spreadsheet | {SITE}", "A free job application tracker in your browser: save jobs, mark where you applied, add notes, export to CSV. No account and no spreadsheet to maintain.",
         crumbs(("My jobs", "")) + '<h1>My jobs: your application tracker</h1><p class="lead">Saved jobs, applications, notes and searches in one place, so you know what you applied to and who answered. It is all kept in this browser; nothing is uploaded.</p>'
         '<div id="mj-root"><div class="rbar"><div class="tabs" id="mj-tabs"></div><button class="btn ghost sm" id="mj-export" type="button">Export CSV</button></div>'
         '<p class="note" id="mj-nudge" hidden></p>'
         '<ul class="jobs" id="mj-list"></ul><div class="empty" id="mj-empty">Nothing here yet. Open any job and press “Save job” or “Mark as applied”.</div><p class="note" id="mj-hidden" hidden></p>'
         '<section class="sec"><div class="sec-head"><h2>Companies you follow</h2></div><ul class="jobs" id="fc-list"></ul>'
         f'<div class="empty" id="fc-empty">You do not follow any company yet. Open a <a class="inl" href="{P}/companies/">company page</a> and press “Follow”.</div></section>'
         '<section class="sec"><div class="sec-head"><h2>Saved searches</h2></div><ul class="jobs" id="ss-list"></ul>'
         f'<div class="empty" id="ss-empty">No saved searches. Set filters on the <a class="inl" href="{P}/jobs/">search page</a> and press “Save this search”.</div></section>'
         '<section class="sec"><div class="sec-head"><h2>Recently viewed</h2></div><ul class="jobs" id="seen-list"></ul><div class="empty" id="seen-empty">No jobs viewed yet.</div></section>'
         '<section class="sec"><div class="sec-head"><h2>Your data</h2></div><p>Everything on this page is stored in this browser and nowhere else. Keep a copy, move it to another device, or wipe it.</p>'
         '<p class="mjdata"><button class="btn ghost sm" id="mj-backup" type="button">Download a backup</button> <button class="btn ghost sm" id="mj-restore" type="button">Restore from a backup</button> '
         '<button class="btn ghost sm" id="mj-erase" type="button">Erase everything</button><input type="file" id="mj-file" accept="application/json,.json" hidden></p>'
         '<p class="note" id="mj-data-note" role="status"></p></section></div>')

    # Perks, employment type, work from anywhere
    perk_tiles = ""
    for name, slug, _ in PERKS:
        pj = [j for j in active if name in j.get("perks", [])]
        if name not in PERK_OK: continue
        perk_tiles += tile(f"perks/{slug}/", name, len(pj))
        listing(f"perks/{slug}/", f"Tech jobs with {name[0].lower() + name[1:]}", f"Tech Jobs With {name} ({len(pj):,} open) | {SITE}",
                f"{roles(len(pj), 'tech job')} where the posting mentions {name.lower()}. Updated hourly.", pj,
                intro_for(pj, "", f" that mention {e(name.lower())} in the posting") + " We read this from the job text, so check the details with the employer.",
                trail=(("Perks", "perks/"),), feed=True, faq=f"tech jobs with {name[0].lower() + name[1:]}")
    if perk_tiles:
        page("perks/", f"Tech Jobs by Perk — visa sponsorship, equity, 4-day week | {SITE}", "Browse tech jobs by what the employer offers: visa sponsorship, relocation, equity, 4-day week and more.",
             crumbs(("Perks", "")) + f'<h1>Tech jobs by perk</h1><p class="lead">What employers mention in their postings. Detected from the job text, so always confirm with the company.</p><ul class="tiles">{perk_tiles}</ul>')
    for et, path, h1 in (("Contract", "contract/", "Contract tech jobs"), ("Part-time", "part-time/", "Part-time tech jobs"), ("Internship", "internships/", "Tech internships")):
        ej = [j for j in active if j.get("etype") == et]
        if len(ej) >= 8:
            yr = f" {TODAY[:4]}–{int(TODAY[:4]) + 1}" if et == "Internship" else ""
            listing(path, h1, f"{h1}{yr} ({len(ej):,} open) | {SITE}", f"{roles(len(ej), 'open role')}: {h1.lower()}{yr} at tech companies, straight from their careers pages. Updated hourly.", ej,
                    intro_for(ej, f"{et.lower()} "), trail=(("All jobs", "jobs/"),))
    for et, path, h1, what_ in (("Contract", "remote/contract/", "Remote contract jobs", "fixed-term and freelance work done from home"),
                                ("Part-time", "remote/part-time/", "Remote part-time jobs", "work from home for fewer hours than a full week"),
                                ("Full-time", "remote/full-time/", "Remote full-time jobs", "full-week jobs done from home")):
        ej = [j for j in remote if j.get("etype") == et]
        if len(ej) >= 20:
            listing(path, h1, f"{tcase(h1)} ({len(ej):,} open) | {SITE}", f"{roles(len(ej), 'open role')}: {what_}, read from employers’ own careers pages and checked against them.", ej,
                    f"<strong>{e(h1)}</strong>: {e(what_)}. " + intro_for(ej, f"remote {et.lower()} ", "", hub=True), trail=(("Remote", "remote/"),), per=50, max_pages=3, faq=h1[0].lower() + h1[1:],
                    extra=hub_stats(ej))
    aw = [j for j in active if j.get("anywhere") and j["remote"]]
    if len(aw) >= 8:
        listing("work-from-anywhere/", "Work-from-anywhere tech jobs", f"Work From Anywhere Tech Jobs ({len(aw):,} open) | {SITE}",
                f"{roles(len(aw), 'remote tech job')} open to candidates worldwide, with no country restriction in the listing.", aw,
                intro_for(aw, "remote ", " listed as open worldwide"), trail=(("Remote", "remote/"),))

    # Insights: ranked lists recalculated from live data every day
    month = f"{['January','February','March','April','May','June','July','August','September','October','November','December'][int(TODAY[5:7]) - 1]} {TODAY[:4]}"
    INS_PREV = {}
    def ins_points(rows_html, chart):
        pts = []
        for r_ in rows_html[:10]:
            c_ = re.findall(r"<td>(.*?)</td>", r_, re.S)
            if len(c_) <= max(chart): continue
            lab, raw = re.sub(r"<[^>]+>", "", c_[chart[0]]).strip(), re.sub(r"<[^>]+>", "", c_[chart[1]]).strip()
            m_, href = re.search(r"\d[\d,]*\.?\d*", raw), re.search(r'href="([^"]+)"', c_[chart[0]])
            if lab and m_: pts.append((html.unescape(lab), float(m_.group(0).replace(",", "")), html.unescape(raw), href.group(1) if href else ""))
        return pts
    def ins_chart(pts):
        mx_ = max((p_[1] for p_ in pts), default=0)
        if len(pts) < 4 or not mx_: return ""
        return ('<div class="hbars chart">' + "".join(f'<a href="{e(h_) if h_ else "#"}"><span class="hn">{e(lab[:44])}</span><span class="hb"><i style="width:{max(2, round(100 * v / mx_))}%"></i></span><span class="hc">{e(raw[:24])}</span></a>'
                                                     for lab, v, raw, h_ in pts) + "</div>")
    def insight(slug, h1, desc, lead, head, rows_html, more, chart=(1, 2)):
        INS_PREV[f"insights/{slug}/"] = ins_points(rows_html, chart)
        page(f"insights/{slug}/", f"{h1} — {month} | {SITE}", desc,
             crumbs(("Insights", "insights/"), (h1, "")) + f"<h1>{e(h1)}</h1><p class=\"lead\">{lead} Recalculated every day from {n:,} open roles; this is the picture for {month}.</p>"
             + ins_chart(INS_PREV[f"insights/{slug}/"]) + ttable(head, rows_html) + f'<p class="note">Salary figures are medians of advertised US-dollar ranges, not verified pay.</p><p><a class="btn" href="{P}/{more[0]}">{e(more[1])}</a></p>' + cite(f"insights/{slug}/", f"{h1}, {month}"))
        return (f"insights/{slug}/", h1, desc)
    sal_by_tag = sorted(((t, median([(lo + hi) / 2 for _, (lo, hi) in g]), len(g)) for t, g in g_tag.items() if len(g) >= 30), key=lambda x: -x[1])
    remote_co = sorted(((c, sum(j["remote"] for j in js if j["active"]), sum(j["active"] for j in js)) for c, js in companies.items()), key=lambda x: -x[1])
    entry_co = sorted(((c, sum(1 for j in js if j["active"] and j["entry"])) for c, js in companies.items()), key=lambda x: -x[1])
    week_co = sorted(((c, sum(1 for j in js if j["active"] and (j["posted"] or "") >= week), sum(j["active"] for j in js)) for c, js in companies.items()), key=lambda x: -x[1])
    week_tag = sorted(((t, sum(1 for j in js if (j["posted"] or "") >= week), len(js)) for t, js in by_tag.items()), key=lambda x: -x[1])
    rank = lambda i: f"<strong>{i + 1}</strong>"
    cl = lambda c: f'<a href="{P}/companies/{slugify(c)}/">{e(c)}</a>'
    tl = lambda t: f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a>'
    INS = [
        insight("highest-paying-tech-skills", "Highest-paying tech skills", "Which programming languages and tools come with the highest advertised salaries in open tech jobs right now.",
                "The skills attached to the highest advertised salaries.", ["#", "Skill", "Median salary", "Roles with a salary"],
                [trow([rank(i), tl(t), f"<strong>{money(m_)}</strong>", f"{k:,}"]) for i, (t, m_, k) in enumerate(sal_by_tag[:30])], ("salaries/", "All salary data")),
        insight("most-in-demand-tech-skills", "Most in-demand tech skills", "The skills that appear in the most open tech job postings right now, with their share and remote rate.",
                "The skills employers ask for most often.", ["#", "Skill", "Open roles", "Share of all roles", "Posted this week"],
                [trow([rank(i), tl(t), f"{len(js):,}", pctf(len(js), n), f"{sum(1 for j in js if (j['posted'] or '') >= week):,}"]) for i, (t, js) in enumerate(sorted(by_tag.items(), key=lambda kv: -len(kv[1]))[:30])],
                ("skills/", "Browse jobs by skill")),
        insight("companies-hiring-remotely", "Tech companies hiring the most remote workers", "The tech companies with the most open remote roles right now and how remote-friendly each one is.",
                "Companies ranked by the number of open remote roles.", ["#", "Company", "Remote roles", "Share of its roles"],
                [trow([rank(i), cl(c), f"{r_:,}", pctf(r_, a_)]) for i, (c, r_, a_) in enumerate(x for x in remote_co[:30] if x[1])], ("remote/", "All remote jobs")),
        insight("companies-hiring-entry-level", "Tech companies hiring interns and juniors", "The tech companies with the most open internships and junior roles right now.",
                "Companies ranked by open internships and junior roles.", ["#", "Company", "Entry-level roles"],
                [trow([rank(i), cl(c), f"{k:,}"]) for i, (c, k) in enumerate(x for x in entry_co[:30] if x[1])], ("entry-level/", "All entry-level jobs")),
        insight("companies-hiring-this-week", "Tech companies hiring the most this week", "Which tech companies posted the most new roles in the last seven days.",
                "Companies ranked by roles posted in the last seven days.", ["#", "Company", "Posted this week", "Open roles in total"],
                [trow([rank(i), cl(c), f"{k:,}", f"{a_:,}"]) for i, (c, k, a_) in enumerate(x for x in week_co[:30] if x[1])], ("new/", "See new jobs")),
        insight("fastest-growing-tech-skills", "Skills with the most new job postings this week", "The skills that showed up in the most tech job postings published in the last seven days.",
                "Skills ranked by postings published in the last seven days.", ["#", "Skill", "Posted this week", "Open roles in total"],
                [trow([rank(i), tl(t), f"{k:,}", f"{a_:,}"]) for i, (t, k, a_) in enumerate(x for x in week_tag[:30] if x[1])], ("new/", "See new jobs")),
    ]
    def age_days(j):
        try: return (datetime.date.today() - datetime.date.fromisoformat((j["posted"] or j["first_seen"])[:10])).days
        except Exception: return 0
    co_act = {c: [j for j in js if j["active"]] for c, js in companies.items()}
    big = {c: js for c, js in co_act.items() if len(js) >= 20}
    pay_rank = sorted(((c, len(js), sum(bool(j["salary"]) for j in js)) for c, js in big.items()), key=lambda x: (-x[2] / x[1], -x[1]))
    INS.append(insight("pay-transparency", "Pay transparency: which tech companies publish salaries", "Which tech employers state the salary in their job postings and which never do, counted from live openings.",
                       f"{SALPCT}% of open tech roles state a salary where our reader can find it: in the hiring system's pay field or next to a word such as “salary” in the text. "
                       f"These are the employers, among {len(pay_rank)} with 20 or more open roles, that state it most often. A missing salary here can also mean a wording our rules do not recognise.",
                       ["#", "Company", "Open roles", "With a salary", "Share"],
                       [trow([rank(i), cl(c), f"{k_:,}", f"{s_:,}", barc(s_, k_, pctf(s_, k_))]) for i, (c, k_, s_) in enumerate(pay_rank[:50]) if s_],
                       ("with-salary/", "Jobs with the salary listed"), chart=(1, 4)))
    linger = sorted(((c, len(js), sum(age_days(j) >= LONG_OPEN for j in js), int(median([age_days(j) for j in js]))) for c, js in big.items()), key=lambda x: (-x[2] / x[1], -x[1]))
    long_all = sum(age_days(j) >= LONG_OPEN for j in active)
    INS.append(insight("long-open-roles", f"Tech roles open {LONG_OPEN} days or more: where postings linger", "How many tech job postings have been open for three months or longer, and at which companies they pile up.",
                       f"{long_all:,} of {n:,} open roles ({pctf(long_all, n)}) were posted {LONG_OPEN} or more days ago. A posting that stays up for months proves nothing by itself, since some employers hire for the same title all year, "
                       "but it is worth knowing before you spend an evening on an application.",
                       ["#", "Company", "Open roles", f"Open {LONG_OPEN}+ days", "Share", "Median days open"],
                       [trow([rank(i), cl(c), f"{k_:,}", f"{l_:,}", barc(l_, k_, pctf(l_, k_)), f"{md_:,}"]) for i, (c, k_, l_, md_) in enumerate(linger[:50]) if l_],
                       ("new/", "Jobs posted in the last 3 days"), chart=(1, 4)))
    pulse_rank = sorted(((c, *PULSE[c]) for c in PULSE if PULSE[c][0] or PULSE[c][1]), key=lambda x: -(x[1] - x[2]))
    INS.append(insight("hiring-pulse", "Hiring pulse: who is ramping up and who is slowing down", "Which tech companies opened and closed the most roles in the last seven days, from daily snapshots of their careers pages.",
                       "Roles each company opened and closed in the last seven days. Closed counts are tracked from the day we started watching a company.",
                       ["#", "Company", "Opened", "Closed", "Net", "Trend"],
                       [trow([rank(i), cl(c), f"+{o_}", f"−{k_}", f"<strong>{o_ - k_:+d}</strong>", mood]) for i, (c, o_, k_, mood) in enumerate(pulse_rank[:40])], ("companies/", "All companies")))
    # Company against company (the owner pointed at the "compare companies" pages of Indeed and Glassdoor). Theirs rest on reviews;
    # ours on what each employer's own postings show today: how much it hires, how often it states pay, how much of it is remote.
    cfacts = {}
    for c, js in companies.items():
        act_ = [j for j in js if j["active"]]
        if len(act_) < 5: continue
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in act_ if j["usd"]]
        cfacts[slugify(c)] = dict(name=c, n=len(act_), remote=sum(j["remote"] for j in act_), pay=sum(bool(j["salary"]) for j in act_), med=int(median(mids_)) if len(mids_) >= 15 else 0,
                                  week=sum(1 for j in act_ if (j["posted"] or "") >= week), entry=sum(1 for j in act_ if j["entry"]), old=sum(age_days(j) >= LONG_OPEN for j in act_),
                                  fields=[CAT[k] for k, _ in Counter(j["cat"] for j in act_).most_common(3)], skills=[t for t, _ in Counter(t for j in act_ for t in j["tags"]).most_common(6)])
    write("data/compare.json", json.dumps({s_: [f["name"], f["n"], f["remote"], f["pay"], f["med"], f["week"], f["entry"], f["old"], f["fields"], f["skills"]] for s_, f in cfacts.items()},
                                         ensure_ascii=False, separators=(",", ":")), sitemap=False)
    def vs_rows(A, B):
        pc = lambda a_, b_: round(100 * a_ / max(1, b_))
        rows_ = [("Open jobs", A["n"], B["n"], f'{A["n"]:,}', f'{B["n"]:,}'), ("Can be done from home", pc(A["remote"], A["n"]), pc(B["remote"], B["n"]), f'{pc(A["remote"], A["n"])}%', f'{pc(B["remote"], B["n"])}%'),
                 ("State the pay", pc(A["pay"], A["n"]), pc(B["pay"], B["n"]), f'{pc(A["pay"], A["n"])}%', f'{pc(B["pay"], B["n"])}%'),
                 ("Median advertised pay", A["med"], B["med"], money(A["med"]) if A["med"] else "too few postings", money(B["med"]) if B["med"] else "too few postings"),
                 ("Posted in the last 7 days", A["week"], B["week"], f'{A["week"]:,}', f'{B["week"]:,}'), ("For beginners", A["entry"], B["entry"], f'{A["entry"]:,}', f'{B["entry"]:,}'),
                 (f"Open {LONG_OPEN} days or more", pc(A["old"], A["n"]), pc(B["old"], B["n"]), f'{pc(A["old"], A["n"])}%', f'{pc(B["old"], B["n"])}%')]
        out = ""
        for lab, a_, b_, ta, tb in rows_:
            mx_ = max(a_, b_, 1)
            out += (f'<div class="vsr"><span class="vl">{e(lab)}</span><span class="va"><b>{e(ta)}</b><i style="width:{round(100 * a_ / mx_)}%"></i></span>'
                    f'<span class="vb"><i style="width:{round(100 * b_ / mx_)}%"></i><b>{e(tb)}</b></span></div>')
        return out
    def vs_head(A, B, sa, sb):
        return (f'<div class="vsh"><a href="{P}/companies/{sa}/">{ava(A["name"])}<b>{e(A["name"])}</b></a><span>vs</span><a href="{P}/companies/{sb}/"><b>{e(B["name"])}</b>{ava(B["name"])}</a></div>')
    vs_top = [s_ for s_, _ in sorted(cfacts.items(), key=lambda kv: -kv[1]["n"])[:14]]
    vs_pairs = [(a_, b_) for i, a_ in enumerate(vs_top) for b_ in vs_top[i + 1:]]
    vs_path = lambda a_, b_: f"companies/compare/{a_}-vs-{b_}/"
    for sa, sb in vs_pairs:
        A, B = cfacts[sa], cfacts[sb]
        more_, rem_, pay_ = (A, B) if A["n"] >= B["n"] else (B, A), (A, B) if A["remote"] / A["n"] >= B["remote"] / B["n"] else (B, A), (A, B) if A["pay"] / A["n"] >= B["pay"] / B["n"] else (B, A)
        verdict = [f'{more_[0]["name"]} has more open jobs: {more_[0]["n"]:,} against {more_[1]["n"]:,}.',
                   f'{rem_[0]["name"]} has the larger share of remote roles: {round(100 * rem_[0]["remote"] / rem_[0]["n"])}% against {round(100 * rem_[1]["remote"] / rem_[1]["n"])}%.',
                   f'{pay_[0]["name"]} states the pay more often: in {round(100 * pay_[0]["pay"] / pay_[0]["n"])}% of its postings against {round(100 * pay_[1]["pay"] / pay_[1]["n"])}%.']
        if A["med"] and B["med"]:
            hi_, lo_ = (A, B) if A["med"] >= B["med"] else (B, A)
            verdict.append(f'{hi_["name"]} advertises higher pay: a median of {money(hi_["med"])} against {money(lo_["med"])}. The roles differ, so this compares what is on offer, not the same job.')
        qa_ = [(f"Which has more open jobs, {A['name']} or {B['name']}?", verdict[0] + f" Counted on {fdate(TODAY)} from each company’s own careers page."),
               (f"Does {A['name']} or {B['name']} hire more remote workers?", verdict[1]), (f"Which of the two states the pay in its postings?", verdict[2])]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        side = lambda F: (f'<div><p class="flabel">{e(F["name"])} hires most in</p><p>{e(", ".join(F["fields"]))}</p>' + (f'<p class="flabel">Skills it asks for most</p><p>{e(", ".join(F["skills"]))}</p>' if F["skills"] else "") + "</div>")
        others_ = [x for x in vs_top if x not in (sa, sb)][:6]
        page(vs_path(sa, sb), f"{A['name']} vs {B['name']}: jobs, pay and remote work | {SITE}",
             f"{A['name']} against {B['name']} by their own job postings: {A['n']:,} and {B['n']:,} open roles, the share that is remote, how often pay is stated and what is advertised. Counted {fdate(TODAY)}.",
             crumbs(("Companies", "companies/"), ("Compare", "companies/compare/"), (f"{A['name']} vs {B['name']}", "")) + f"<h1>{e(A['name'])} vs {e(B['name'])}: hiring side by side</h1>"
             f'<p class="lead">What each company’s own job postings show on {fdate(TODAY)}: how many roles are open, how many can be done from home, how often the pay is stated and what is advertised.</p>'
             + vs_head(A, B, sa, sb) + f'<div class="vs">{vs_rows(A, B)}</div>'
             + '<div class="card verdict">' + "".join(f"<p>{e(v)}</p>" for v in verdict) + "</div>"
             + f'<div class="vsside">{side(A)}{side(B)}</div>'
             + f'<p class="cta2"><a class="btn" href="{P}/companies/{sa}/">See {e(A["name"])} jobs</a> <a class="btn ghost" style="margin-top:0" href="{P}/companies/{sb}/">See {e(B["name"])} jobs</a></p>'
             + section("Questions", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
             + section("More comparisons", '<ul class="tiles">' + "".join(tile(vs_path(*sorted((x, o), key=vs_top.index)), f"{cfacts[x]['name']} vs {cfacts[o]['name']}", cfacts[x]["n"] + cfacts[o]["n"]) for x in (sa, sb) for o in others_[:3]) + "</ul>",
                       ("companies/compare/", "Compare any two companies"))
             + f'<p class="note">Counted from open roles collected from each company’s own careers page. A median needs at least 15 postings with a yearly range in US dollars. <a href="{P}/methodology/">How the numbers are made</a>.</p>', head=ld_)
    vs_opts = "".join(f'<option value="{s_}">{e(f["name"])}</option>' for s_, f in sorted(cfacts.items(), key=lambda kv: kv[1]["name"].lower()))
    page("companies/compare/", f"Compare Companies by Their Job Postings: {len(cfacts)} employers | {SITE}",
         f"Put any two of {len(cfacts)} employers side by side: open jobs, remote share, how often pay is stated, advertised pay, new roles this week. Counted from their own postings.",
         crumbs(("Companies", "companies/"), ("Compare", "")) + '<h1>Compare two companies by what they are <span class="hl">hiring for</span></h1>'
         f'<p class="lead">Pick any two of {len(cfacts)} employers. The bars show what their own job postings say today: how many roles are open, how many can be done from home, how often the pay is stated.</p>'
         f'<div class="feedpick vspick"><label for="vs-a">First</label><select id="vs-a">{vs_opts}</select><label for="vs-b">Second</label><select id="vs-b">{vs_opts}</select></div>'
         f'<div id="vs-out" data-a="{vs_top[0]}" data-b="{vs_top[1]}" data-long="{LONG_OPEN}">' + vs_head(cfacts[vs_top[0]], cfacts[vs_top[1]], vs_top[0], vs_top[1]) + f'<div class="vs">{vs_rows(cfacts[vs_top[0]], cfacts[vs_top[1]])}</div></div>'
         + section("Comparisons people open most", '<ul class="tiles">' + "".join(tile(vs_path(a_, b_), f"{cfacts[a_]['name']} vs {cfacts[b_]['name']}", cfacts[a_]["n"] + cfacts[b_]["n"]) for a_, b_ in vs_pairs[:24]) + "</ul>")
         + f'<p class="note">Reviews by employees are not part of this: the comparison uses only what employers publish in their postings. <a href="{P}/methodology/">How the numbers are made</a>.</p>')

    # Who is hiring, field by field. The big job sites answer this with hand-written lists ("15 companies hiring for remote nursing
    # jobs"); here the same lists are counted from today's postings, so they cannot go stale.
    INS_FAM = []
    for fs, fn, fd, live, js_ in fam_rows:
        per_co = defaultdict(list)
        for j in js_: per_co[j["company"]].append(j)
        top_ = sorted(per_co.items(), key=lambda kv: -len(kv[1]))[:30]
        if len(per_co) < 8: continue
        low_f = rlow(fn)
        def newest_(v):
            j = max(v, key=lambda x: x["posted"] or x["first_seen"] or "")
            return f'<a href="{P}/job/{j["slug"]}/">{e(j["title"][:64])}</a>'
        def pay_(v):
            mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in v if j["usd"]]
            return f"<strong>{money(median(mids_))}</strong>" if len(mids_) >= 15 else "—"
        insight(f"companies-hiring-{fs}", f"Companies hiring for {low_f} jobs", f"The employers with the most open {low_f} jobs right now: how many roles each has, how many are remote and what they advertise as pay.",
                f"{fd[0].upper() + fd[1:]}: {len(js_):,} open jobs at {len(per_co):,} employers, {sum(j['remote'] for j in js_):,} of them remote. These employers have the most. "
                "Pay is shown where an employer states it in at least 15 of these postings.",
                ["#", "Company", "Open roles", "Remote", "Median advertised pay", "Newest role"],
                [trow([rank(i), cl(c), f"{len(v):,}", f"{sum(j['remote'] for j in v):,}", pay_(v), newest_(v)]) for i, (c, v) in enumerate(top_)], (f"categories/{fs}/", f"All {low_f} jobs"))
        INS_FAM.append((f"insights/companies-hiring-{fs}/", fn, len(js_)))
    rich_remote = diverse_pairs(sorted(((j, j["usd"]) for j in remote if j["usd"]), key=lambda x: -x[1][1]), 40)
    if len(rich_remote) >= 15:
        INS.append(insight("highest-paying-remote-jobs", "Highest-paying remote jobs right now", "The 40 remote jobs with the highest advertised pay among open postings today, at most two per employer.",
                           "Remote roles ranked by the top of the pay range the employer states, at most two from one employer.", ["#", "Role", "Company", "Advertised pay", "Posted"],
                           [trow([rank(i), f'<a href="{P}/job/{j["slug"]}/">{e(j["title"][:70])}</a>', cl(j["company"]), f"<strong>{e(j['salary'][:28])}</strong>", fdate(j["posted"] or j["first_seen"], False)])
                            for i, (j, _) in enumerate(rich_remote)], ("salary/200k/remote/", "Remote jobs that pay $200K or more"), chart=(1, 3)))
    aw_co = Counter(j["company"] for j in active if j.get("anywhere") and j["remote"]).most_common(30)
    if len(aw_co) >= 5:
        rem_n = Counter(j["company"] for j in remote)
        INS.append(insight("work-from-anywhere-companies", "Companies with work-from-anywhere jobs", "Employers whose remote postings name no country: the roles are open to candidates anywhere in the world.",
                           "Most remote jobs are open in some countries only. These employers have postings with no country restriction at all.", ["#", "Company", "Open to any country", "All its remote roles"],
                           [trow([rank(i), cl(c), f"{k:,}", f"{rem_n[c]:,}"]) for i, (c, k) in enumerate(aw_co)], ("work-from-anywhere/", "All work-from-anywhere jobs")))
    f100 = []
    for fs, fn, fd, live, js_ in fam_rows:
        rj_ = [j for j in js_ if j["remote"]]
        paid_ = [j for j in rj_ if j["usd"]]
        if len(paid_) >= 30: f100.append((fs, fn, len(rj_), len(paid_), sum(1 for j in paid_ if j["usd"][0] >= 100000), median([(j["usd"][0] + j["usd"][1]) / 2 for j in paid_])))
    if len(f100) >= 6:
        INS.append(insight("remote-jobs-100k-by-field", "Remote jobs that pay $100K or more, by field", "In which kinds of work remote jobs pay six figures: remote roles per field, how many state pay and how many start at $100K or more.",
                           "A remote job counts here when the bottom of its advertised yearly range is $100,000 or more.", ["Field", "Remote roles", "State pay", "Start at $100K+", "Median advertised pay"],
                           [trow([f'<a href="{P}/categories/{fs}/">{e(fn)}</a>', f"{r_:,}", f"{p_:,}", barc(h_, p_, f"{h_:,}"), f"<strong>{money(md_)}</strong>"]) for fs, fn, r_, p_, h_, md_ in sorted(f100, key=lambda x: -x[4])],
                           ("salary/100k/remote/", "Remote jobs that pay $100K or more"), chart=(0, 3)))
    def icard(u, t, d):
        pts = INS_PREV.get(u, [])[:4]
        mx_ = max((p_[1] for p_ in pts), default=0)
        prev = "".join(f'<span class="rw"><span>{e(lab[:20])}</span><span class="mt"><i style="width:{max(4, round(100 * v / mx_))}%"></i></span><b>{e(raw[:10])}</b></span>' for lab, v, raw, _ in pts) if mx_ else ""
        return (f'<a class="tcard" href="{P}/{u}">' + (f'<span class="tprev wide" aria-hidden="true">{prev}</span>' if prev else "")
                + f'<span class="tbody"><b>{e(t)}</b><span>{e(d)}</span><i><u>Open the list</u></i></span></a>')
    fam_bars = '<div class="hbars">' + "".join(
        f'<a href="{P}/{u}"><span class="hn">{e(fn)}</span><span class="hb"><i style="width:{max(2, round(100 * k / max(x[2] for x in INS_FAM)))}%"></i></span><span class="hc">{k:,} jobs</span></a>'
        for u, fn, k in sorted(INS_FAM, key=lambda x: -x[2])) + "</div>" if INS_FAM else ""
    page("insights/", f"Job Market in Charts: rankings from {n:,} open jobs — {month} | {SITE}",
         "The job market in pictures: where the jobs are, what they pay, who is hiring in each field, which skills pay most. Charts and rankings counted from today’s open postings.",
         crumbs(("Insights", "")) + f'<h1>The job market <span class="hl">in pictures</span></h1>'
         f'<p class="lead">Charts and rankings counted from {n:,} open jobs at {m} employers, redrawn each time the jobs are read again. Every chart links to the list behind it.</p>'
         + market_pics
         + section("Rankings", '<div class="tgrid">' + "".join(icard(u, t, d) for u, t, d in INS)
                   + f'<a class="tcard" href="{P}/trends/"><span class="tbody"><b>Hiring trends dashboard</b><span>The headline numbers on one page: skills, companies, categories and locations.</span><i><u>Open the dashboard</u></i></span></a></div>')
         + (section("Who is hiring, field by field", '<p class="note">Each bar opens the list of employers with the most open jobs in that field, with their remote roles and advertised pay.</p>' + fam_bars) if fam_bars else ""))

    # Feeds: every list as an address a bot can read. Channel owners in Telegram, Slack and Discord plug these into their own bots,
    # and every item links back to the job page here (the owner asked for "Telegram feeds like @nodejsjobsfeed" and for more channels).
    feed_groups = [("The whole site", [("feed.xml", "All new jobs"), ("remote/feed.xml", "Remote jobs"), ("crypto/feed.xml", "Crypto and web3 jobs")]),
                   ("By field", [(f"categories/{fs}/feed.xml", fn) for fs, fn, _, _, _ in fam_rows]),
                   ("By kind of work", [(f"roles/{s_}/feed.xml", nm) for s_, (nm, _) in sorted(by_role.items(), key=lambda kv: kv[1][0].lower())]),
                   ("By skill", [(f"skills/{tslug(t)}/feed.xml", t) for t, _ in skill_counts.most_common(40)])]
    feed_opts = "".join(f'<optgroup label="{e(g_)}">' + "".join(f'<option value="{FULL}/{u}">{e(nm)}</option>' for u, nm in items) + "</optgroup>" for g_, items in feed_groups)
    feed_dir = '<div class="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(g_)}</span><span>{len(items)}</span></h2><ul>' + "".join(f'<li><a href="{P}/{u}">{e(nm)}</a><span>RSS</span></li>' for u, nm in items) + "</ul></div>" for g_, items in feed_groups) + "</div>"
    msg_ = ('<span class="ln"><b>Senior Data Analyst</b> at Example Co</span><span class="ln">Remote · $120K – $150K</span><span class="sk" style="width:70%"></span>')
    feed_cards = [
        ("A Telegram channel", "Add an RSS bot to your channel as an administrator and give it the feed address. Each new job arrives as a post with a link.", '<span class="ex">example</span>' + msg_ + '<span class="ln">posted by the bot, 2 minutes ago</span>'),
        ("A Slack channel", "Install Slack’s RSS app and type the command with the feed address in the channel that should get the jobs.", '<code>/feed subscribe\n' + f'{FULL.split("//")[1][:34]}…/feed.xml</code>'),
        ("A Discord server", "An RSS bot such as MonitoRSS reads the address and posts each new job into the room you pick.", '<span class="ex">example</span><span class="ln"><b>#jobs</b></span>' + msg_),
        ("Your own reader or inbox", "Any feed reader shows new jobs like unread mail. Services such as IFTTT, Zapier or Make can also send each one to your email.", '<span class="rw"><span>Unread</span><span class="mt"><i style="width:100%"></i></span><b>12</b></span><span class="ln">New jobs since yesterday</span><span class="sk" style="width:84%"></span>'),
    ]
    feed_qa = [("Is it free?", "Yes. No key, no account, no limit on how many feeds you use."),
               ("How often does a feed change?", "Each time the employers’ careers pages are read again. A feed holds the 100 newest jobs of its kind."),
               ("May I post these jobs in my channel or on my site?", "Yes, for personal and commercial projects. Keep the link to the job page: people apply through it, on the employer’s own site, free of charge."),
               ("What is in each item?", "The job title and the employer, the place, the first lines of the posting, the date and a link to the job page."),
               ("Is there something more exact than a feed?", "Yes: the free API returns the same lists as data for programs, and the widget shows them on a web page without any code of your own.")]
    feed_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in feed_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    n_feeds = sum(len(items) for _, items in feed_groups)
    page("feeds/", f"Job Feeds (RSS) for Telegram, Slack and Discord: {n_feeds} lists | {SITE}",
         f"Free RSS feeds of new jobs by field, kind of work and skill: {n_feeds} addresses for a Telegram channel, a Slack or Discord room, or a feed reader. No key, no account.",
         crumbs(("Feeds", "")) + '<h1>New jobs, sent to your channel or chat <span class="hl">by themselves</span></h1>'
         '<p class="plain"><b>In plain words:</b> a feed is an address that always returns the newest jobs of one kind. A bot or an app reads it and posts each new job where you want it.</p>'
         f'<p class="lead">{n_feeds} feeds, one for every field, kind of work and skill. Pick one, copy its address, give it to a bot. Every item links to the job page, where people apply on the employer’s own site.</p>'
         '<div class="feedpick"><label for="feedpick">Pick a feed</label><select id="feedpick">' + feed_opts + '</select>'
         f'<input id="feedurl" type="text" readonly value="{FULL}/feed.xml" aria-label="Feed address"><button class="btn" id="feedcopy" type="button">Copy the address</button></div>'
         + section("Where a feed can go", '<div class="tgrid">' + "".join(f'<div class="tcard"><span class="tprev" aria-hidden="true">{scr}</span><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span></span></div>' for t_, d_, scr in feed_cards) + "</div>")
         + section("Every feed", feed_dir)
         + section("Questions", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in feed_qa) + "</dl>")
         + f'<p class="note">For programs: the <a href="{P}/api/">free API</a>. For web pages: the <a href="{P}/widgets/">job widget</a>.</p>', head=feed_ld)

    # Ahead: what this site does that job sites do not do yet (the owner: "implement at least ten things from the future")
    ex_ = '<span class="ex">example</span>'
    ahead_cards = [
        ("Ask the employer yourself, in one click", "On a job page, “Check with the employer right now” makes your own browser ask the employer’s hiring system whether the job is still there. You do not have to take our word for it.", "jobs/",
         ex_ + '<span class="big">Still open<small>14:02</small></span><span class="ln">Confirmed to <b>your browser</b> by the employer’s system</span>'),
        ("Alerts with no email and no account", "Answer the five questions and press “Tell me when new jobs fit”. This browser tells you. Nothing about you is stored anywhere else.", "for-you/",
         ex_ + '<span class="ln"><b>3 new jobs fit your answers</b></span><span class="ln">Data Analyst at Example Co and 2 more</span><span class="sk" style="width:60%"></span>'),
        ("Say it instead of typing it", "The microphone in the search bar listens: “remote design jobs paying over 100 thousand”. The search reads the place, the pay and the level out of plain words.", "jobs/",
         '<span class="ln">“remote data analyst jobs over 100k”</span><span class="rw"><span>Remote</span><span class="mt"><i style="width:100%"></i></span><b>yes</b></span><span class="rw"><span>Pay</span><span class="mt"><i style="width:60%"></i></span><b>$100K+</b></span>'),
        ("Listen to a posting", "“Listen to this posting” reads the job aloud in the browser’s own voice: for the commute, or for anyone who would rather hear than read.", "jobs/",
         '<span class="ln"><b>Reading aloud…</b></span><span class="sk" style="width:92%"></span><span class="sk h" style="width:44%"></span><span class="sk" style="width:70%"></span>'),
        ("A follow-up reminder that needs no app", "“Remind me to follow up in 7 days” saves a calendar file. Open it, and your own calendar reminds you. We never see your calendar.", "my-jobs/",
         ex_ + '<span class="ln"><b>Follow up: Data Analyst at Example Co</b></span><span class="ln">Friday, 9:00 · your own calendar</span>'),
        ("Every skill explained in one line", "“What these skills mean” on a job page turns the jargon of the posting into plain words, one line per skill.", "glossary/",
         '<span class="ln"><b>Kubernetes</b></span><span class="ln">Runs many copies of a program across many servers and adds more when traffic grows</span>'),
        ("Kinds of work next to yours", "Each role page shows the roles where employers ask for the same skills, with what they advertise as pay: a map of where you could move.", "categories/",
         ex_ + '<span class="rw"><span>Data scientist</span><span class="mt"><i style="width:100%"></i></span><b>+$22K</b></span><span class="rw"><span>Analytics eng.</span><span class="mt"><i style="width:74%"></i></span><b>+$9K</b></span>'),
        ("Send your criteria, not your resume", "“Copy a link to these answers” makes a link that opens today’s jobs for your criteria. Send it to a friend who hears of openings, or to a recruiter, without giving away who you are.", "for-you/",
         '<span class="ln"><b>…/for-you/#a=</b>eyJjIjpbImRhdGEi…</span><span class="ln">Opens the same list on any device</span>'),
        ("Your job market as one picture", "“Save the result as a picture” draws your answers and what the market offers for them today: how many jobs fit, what they pay, who is hiring.", "for-you/",
         ex_ + '<span class="big">61<small>jobs fit all 5 answers</small></span><span class="ln">Half pay up to <b>$203K</b> or more</span>'),
        ("A resume that knows what is in demand", "While you type in the resume builder, it shows how many open jobs ask for each skill you mention and how many jobs fit the resume as it stands.", "resume/",
         ex_ + '<span class="rw"><span>Python</span><span class="mt"><i style="width:100%"></i></span><b>8,341</b></span><span class="rw"><span>SQL</span><span class="mt"><i style="width:52%"></i></span><b>4,254</b></span><span class="ln">1,240 jobs ask for three of your skills</span>'),
    ]
    page("ahead/", f"Ten Things This Job Site Does That Others Do Not Yet | {SITE}",
         "Check a job with the employer from your own browser, get alerts with no email and no account, search by voice, listen to a posting, and seven more things job sites do not do yet.",
         crumbs(("Ahead", "")) + '<h1>Ten things here that job sites <span class="hl">do not do yet</span></h1>'
         '<p class="lead">Each of them works in your browser, with no account and nothing sent to us. Open any of them and try.</p>'
         '<div class="tgrid">' + "".join(f'<a class="tcard" href="{P}/{u}"><span class="tprev" aria-hidden="true">{scr}</span><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span><i><u>Try it</u></i></span></a>' for t_, d_, u, scr in ahead_cards) + "</div>"
         f'<p class="note">Some of these depend on what your browser can do: speech recognition and background checks are not in every browser. Where one is missing, its button does not appear.</p>')

    # Data status: what the last run really did. "Updated daily" is easy to write and hard to check; this page lets anyone check.
    stats_file = ROOT / "data" / "stats.json"
    ST = json.loads(stats_file.read_text()) if stats_file.exists() else {}
    if ST.get("date") != TODAY: ST = {}
    rechecked = sum(1 for j in active if j.get("last_seen") == TODAY)
    # "posted today" uses the employer's own date: the day we first saw a job says nothing on the day a company is added
    new_today, closed_today = sum(1 for j in active if (j["posted"] or "")[:10] == TODAY), sum(1 for j in archived if j.get("closed") == TODAY)
    ages = sorted(age_days(j) for j in active)
    feeds = (f'<div class="stat"><b>{ST["sources"] - len(ST["failed"]):,} of {ST["sources"]:,}</b><span>employer feeds answered</span></div>' if ST else "")
    failed_html = (section("Feeds that did not answer in the last run", "<p>" + ", ".join(e(x) for x in ST["failed"]) + ".</p>"
                           '<p class="note">Their listings are left exactly as they were and are read again in the next run. Nothing is marked closed on a failed read.</p>') if ST.get("failed") else "")
    page("status/", f"Data Status — how fresh the job listings are today | {SITE}",
         f"The employers’ career pages are read every hour. What the latest update of {SITE} did: feeds read, roles re-checked, new and closed jobs today.",
         crumbs(("Data status", "")) + "<h1>Data status: how fresh the listings are today</h1>"
         '<p class="plain"><b>In plain words:</b> when we last checked the jobs, and how many were added and closed that day, so you can see for yourself that the list is fresh.</p>'
         '<p class="lead">Every job board says it is updated daily. This page shows what our last update actually did: how many roles were re-checked, how many were added and how many closed.</p>'
         # the schedule as it is set in .github/workflows/update.yml; change the two together
         '<p><b>Schedule:</b> the employers’ career pages are read every hour, at 17 minutes past the hour (UTC). One run, from the first feed to the new pages '
         f'being online, took 9 to 15 minutes when we measured it on {fdate("2026-11-13")}. GitHub, which runs the schedule, sometimes starts a run late; the time of the last update below shows when it really happened.</p>'
         f'<div class="statrow"><div class="stat"><b>{fdate(TODAY)}</b><span>last update{", " + e(ST["time"]) if ST else ""}</span></div>{feeds}'
         f'<div class="stat"><b>{pctf(rechecked, n)}</b><span>of open roles re-checked today</span></div><div class="stat"><b>+{new_today:,}</b><span>posted today</span></div>'
         f'<div class="stat"><b>−{closed_today:,}</b><span>closed today</span></div></div>'
         + failed_html
         + section("How old the open listings are", ttable(["Measure", "Value"], [
             trow(["Open roles", f"{n:,}"]), trow(["Posted in the last 7 days", f"{sum(a <= 7 for a in ages):,} ({pctf(sum(a <= 7 for a in ages), n)})"]),
             trow(["Posted in the last 30 days", f"{sum(a <= 30 for a in ages):,} ({pctf(sum(a <= 30 for a in ages), n)})"]),
             trow([f'Open {LONG_OPEN} days or more (<a href="{P}/insights/long-open-roles/">by company</a>)', f"{long_all:,} ({pctf(long_all, n)})"]),
             trow(["Median days since posting", f"{ages[len(ages) // 2] if ages else 0}"])])
             + '<p class="note">The posting date is the one the employer’s hiring system reports. We do not reset it when we re-check a job.</p>')
         + section("What happens when a role closes", f'<p>When a posting disappears from the employer’s careers page, it is marked closed on the same day and moved to the <a href="{P}/archive/">archive</a>, '
                   f'which holds {len(archived):,} closed roles. A closed job keeps its page and says so at the top. How everything is collected: <a href="{P}/methodology/">methodology</a>.</p>')
         + cite("status/", "Data status"))

    # Monthly hiring report: one snapshot per month, updated daily while the month runs and left untouched afterwards.
    # The snapshots live in data/reports.json, which the workflow keeps on the data branch next to the jobs database.
    rep_file = ROOT / "data" / "reports.json"
    REPORTS = json.loads(rep_file.read_text()) if rep_file.exists() else {}
    ym = TODAY[:7]
    paid_mid = sorted((lo + hi) / 2 for j in active if j["usd"] for lo, hi in [j["usd"]])
    REPORTS[ym] = {"date": TODAY, "open": n, "companies": m, "remote": len(remote), "with_salary": sum(bool(j["salary"]) for j in active), "median_salary": int(median(paid_mid)) if paid_mid else 0,
                   "posted": sum(1 for j in active if (j["posted"] or "")[:7] == ym), "closed": sum(1 for j in archived if (j.get("closed") or "")[:7] == ym), "long_open": long_all,
                   "skills": [[t, len(js)] for t, js in sorted(by_tag.items(), key=lambda kv: -len(kv[1]))[:15]],
                   "categories": [[CAT[s], len(by_cat[s])] for s in sorted(by_cat, key=lambda s: -len(by_cat[s])) if s != OTHER[0]][:12],
                   "employers": [[c, len(js)] for c, js in sorted(co_act.items(), key=lambda kv: -len(kv[1]))[:15]],
                   "places": [[PLACE_NAME[slug], len(js)] for _, slug, js in sorted(places, key=lambda x: -len(x[2]))[:12]],
                   "pay": [[k, int(median([(lo + hi) / 2 for _, (lo, hi) in v])), len(v)] for k, v in sorted(g_cat.items(), key=lambda kv: -len(kv[1])) if len(v) >= 30 and k != OTHER[1]][:10]}
    rep_file.write_text(json.dumps(REPORTS, ensure_ascii=False))
    MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    mlabel = lambda k: f"{MONTH_NAMES[int(k[5:7]) - 1]} {k[:4]}"
    rep_months = sorted(REPORTS, reverse=True)
    for i, k in enumerate(rep_months):
        R, prev_k = REPORTS[k], rep_months[i + 1] if i + 1 < len(rep_months) else None
        prev = REPORTS[prev_k] if prev_k else None
        vs = lambda key: (f' <span class="note">({R[key] - prev[key]:+,} against {mlabel(prev_k)})</span>' if prev and key in prev else "")
        two = lambda rows_, head: ttable(head, [trow([e(str(a)), f"{b:,}", pctf(b, R["open"])]) for a, b in rows_])
        top_skill, top_emp = R["skills"][0], R["employers"][0]
        findings = (f'<ul><li>{R["open"]:,} tech roles were open at {R["companies"]:,} companies{vs("open")}.</li>'
                    f'<li>{pctf(R["remote"], R["open"])} of them were remote and {pctf(R["with_salary"], R["open"])} stated a salary.</li>'
                    + (f'<li>The median advertised salary was {money(R["median_salary"])}.</li>' if R["median_salary"] else "")
                    + f'<li>The most requested skill was {e(top_skill[0])}, named in {top_skill[1]:,} postings ({pctf(top_skill[1], R["open"])}).</li>'
                    f'<li>{e(top_emp[0])} had the most open roles: {top_emp[1]:,}.</li>'
                    f'<li>{pctf(R["long_open"], R["open"])} of open roles had been up for {LONG_OPEN} days or more.</li></ul>')
        state = ("This month is still running: the page is recounted every day and stops changing after the last day of the month." if k == ym
                 else "This report is final: the figures are the last count of that month and will not change.")
        page(f"reports/{k}/", f"Tech Hiring Report, {mlabel(k)}: jobs, pay, skills | {SITE}",
             f"Tech hiring in {mlabel(k)}: {R['open']:,} open roles at {R['companies']:,} companies, remote share, advertised pay, most requested skills and biggest employers.",
             crumbs(("Hiring reports", "reports/"), (mlabel(k), "")) + f"<h1>Tech hiring report: {mlabel(k)}</h1>"
             '<p class="lead">Headlines about the tech job market contradict each other every week. This report counts what employers actually posted on their own careers pages, nothing else.</p>'
             f'<div class="statrow"><div class="stat"><b>{R["open"]:,}</b><span>open roles</span></div><div class="stat"><b>{R["companies"]:,}</b><span>companies</span></div>'
             f'<div class="stat"><b>{pctf(R["remote"], R["open"])}</b><span>remote</span></div><div class="stat"><b>{pctf(R["with_salary"], R["open"])}</b><span>state a salary</span></div>'
             + (f'<div class="stat"><b>{money(R["median_salary"])}</b><span>median advertised salary</span></div>' if R["median_salary"] else "") + "</div>"
             f'<p class="note">Counted on {fdate(R["date"])}. {state}</p>'
             + section(f"What {mlabel(k)} looked like", findings)
             + section("Most requested skills", two(R["skills"], ["Skill", "Open roles", "Share of all roles"]))
             + section("Open roles by category", two(R["categories"], ["Category", "Open roles", "Share of all roles"]))
             + section("Employers with the most open roles", two(R["employers"], ["Company", "Open roles", "Share of all roles"]))
             + section("Where the roles are", two(R["places"], ["Location", "Open roles", "Share of all roles"]) + '<p class="note">A role that lists several places is counted in each of them.</p>')
             + (section("Median advertised salary by category", ttable(["Category", "Median salary", "Roles counted"], [trow([e(a), f"<strong>{money(b)}</strong>", f"{c_:,}"]) for a, b, c_ in R["pay"]])
                        + '<p class="note">Medians of the midpoints of advertised yearly US-dollar ranges. Advertised, not verified pay.</p>') if R["pay"] else "")
             + f'<p class="cta2"><a class="btn" href="{P}/trends/">Today’s live numbers</a> <a class="btn ghost" style="margin-top:0" href="{P}/reports/">All monthly reports</a></p>'
             + cite(f"reports/{k}/", f"Tech hiring report, {mlabel(k)}"))
    page("reports/", f"Tech Hiring Reports by Month — jobs, pay, skills | {SITE}",
         "Monthly tech hiring reports built from live job postings: open roles, remote share, advertised pay, most requested skills and biggest employers. Free to quote.",
         crumbs(("Hiring reports", "")) + "<h1>Tech hiring reports, month by month</h1>"
         '<p class="plain"><b>In plain words:</b> a summary of the tech job market for each month. A finished month never changes, so it can be quoted.</p>'
         '<p class="lead">One page per month. A month’s page stops changing when the month ends, so a figure you quote from it stays where you found it.</p>'
         '<ul class="tiles">' + "".join(tile(f"reports/{k}/", mlabel(k), REPORTS[k]["open"]) for k in rep_months) + "</ul>"
         '<p class="note">The number on each tile is the count of open roles in that month’s report.</p>')

    # Safety: how to tell a real job offer from a fake one, and what this site does about it
    def qa_block(qa):
        html_ = "".join(f"<details class='faq'><summary>{e(q_)}</summary><p>{e(a_)}</p></details>" for q_, a_ in qa)
        return html_, ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    safety_qa = [("Will a real employer ever ask me to pay?", "No. A real employer does not charge for applying, training, equipment, a background check or a visa. A request for money at any stage of hiring is the clearest sign of a scam."),
                 ("Is it safe to do a take-home test?", "Usually, if it comes through the company’s own hiring process. Do not run code or open files from someone you cannot tie to the company’s official site, and never on a machine that holds your wallets, keys or work credentials."),
                 (f"Does {SITE} check employers?", f"Every listing on {SITE} is read from the employer’s own hiring system and links to that posting, and it is re-checked every hour. {NO_ANON}. We cannot vouch for what happens after you leave the site, so the checks on this page still apply."),
                 ("What if the recruiter wants to continue in a messenger?", "Ask to continue by email from the company’s domain or through its hiring system. A recruiter who refuses, or whose address does not match the company’s site, is not acting for that company.")]
    safety_faq, safety_ld = qa_block(safety_qa)
    page("safety/", f"Is This Job Offer Real? A safety checklist for job seekers | {SITE}",
         "How to tell a real job offer from a fake one: seven warning signs, four schemes spreading now, how to check a recruiter, extra checks for crypto hiring, and what to do if you already paid.",
         crumbs(("Safety", "")) + "<h1>How to check that a job offer is real</h1>"
         '<p class="lead">Fake recruiters borrow the names of real companies, hold “interviews” in a chat app and ask for money, documents or wallet access before any contract exists. '
         f'Ten minutes of checking catches most of it. Last reviewed {fdate(TODAY)}.</p>'
         + section("Seven signs that a job offer is a scam", '<ol class="steps">'
                   "<li><b>You are asked to pay.</b> For training, equipment, “verification”, a visa or a deposit. Employers pay you, never the reverse.</li>"
                   "<li><b>Everything happens in a messenger.</b> No video call, no email from the company’s domain, no page on its site.</li>"
                   "<li><b>The address does not match.</b> The recruiter writes from a free mailbox or a look-alike domain.</li>"
                   "<li><b>The offer comes too easily.</b> No real interview, or an offer within hours of the first message.</li>"
                   "<li><b>They want access.</b> Bank login, card details, a seed phrase, or your help moving money or parcels.</li>"
                   "<li><b>They send something to run.</b> A “test task”, an installer or a repository from a source you cannot verify.</li>"
                   "<li><b>The pay is unreal and the deadline is today.</b> Far above the market for little work, with pressure to decide at once.</li></ol>")
         + section("How do I check a recruiter and a posting?", "<ol><li>Find the same role on the company’s own careers page. If it is not there, ask the company through the contact on its site.</li>"
                   "<li>Check the sender’s address against the company’s domain, letter by letter.</li>"
                   "<li>Look the recruiter up: a profile with history at that company, colleagues, older posts.</li>"
                   "<li>Keep the process inside the company’s hiring system or email. Decline to move to a private chat.</li>"
                   "<li>Send no documents beyond a resume until there is a written offer you have verified with the company.</li></ol>")
         + section("Crypto and web3 hiring: what else should I check?", "<ul><li>Never share a seed phrase or a private key, and never “connect a wallet to sign onboarding”. No employer needs either.</li>"
                   "<li>Run test tasks, repositories and “audit this code” requests only in a disposable environment with no wallets or keys on it.</li>"
                   "<li>If pay is in tokens, ask for the terms in writing: amount, vesting, and what happens if the token cannot be sold.</li>"
                   "<li>Confirm the team through the project’s official site and channels, not through links the recruiter sends.</li></ul>")
         + section("Four schemes that are spreading now", '<ol class="steps">'
                   "<li><b>Pay to get paid.</b> You “rate products” or “like videos” for small sums, then are told to deposit money to unlock your earnings. A job that asks you to top up an account is not a job.</li>"
                   "<li><b>The cheque that is too big.</b> You receive a cheque or a transfer for more than agreed and are asked to send the difference back. The first payment later bounces; yours does not.</li>"
                   "<li><b>Forwarding parcels or money.</b> “Receive packages at home and send them on” and “process payments through your account” are how stolen goods and money are moved. The person holding them is the one the police find.</li>"
                   "<li><b>The interview that needs you to install something.</b> A “meeting app”, a “coding test” repository or a script to “fix your microphone” that carries a program stealing passwords and crypto wallets. "
                   "Real companies interview in ordinary video-call tools. Open any test project only on a machine with no wallets and no saved passwords; in an editor such as VS Code keep Restricted Mode on and look for tasks that start by themselves.</li></ol>")
         + section("What this site checks, and what it cannot", "<p><b>Checked every hour:</b> that each job still exists on the employer’s own hiring system, where it came from, and when it was posted. "
                   "The address the Apply button opens is written under the button on every job page, so you can see where you are going before you click.</p>"
                   "<p><b>Not checked:</b> what happens after you leave this site, how an employer treats applicants, and whether a company can pay. "
                   + (f"<b>How we contact people:</b> we do not. Nobody from {e(SITE)} will ever write to you first, offer you a job, or ask for money, documents or wallet access. Our only contact is {contact}.</p>" if contact else
                      f"<b>How we contact people:</b> we do not. Nobody from {e(SITE)} will ever write to you first, offer you a job, or ask for money, documents or wallet access.</p>")
                   + "<p><b>Something looks wrong?</b> Every job page has a “Report a problem with this listing” link. A report about money, an install request or a move to a chat app is looked at first.</p>")
         + section(f"What does {SITE} do to keep fake jobs out?", f"<p>Every listing here is read from the employer’s own hiring system (Greenhouse, Lever or Ashby), links straight to that posting and is checked again every hour; "
                   f"a role that disappears from the employer’s page is marked closed the same day. Each job page names its source and the date of the last check. {NO_ANON}, "
                   f'and we never ask you for money, documents or an account. Details: <a href="{P}/methodology/">how listings are collected</a> and <a href="{P}/status/">today’s data status</a>.</p>')
         + section("What should I do if I already sent money or data?", "<p>Act the same day. Call your bank or card issuer and ask to stop or dispute the payment. Change the passwords of any account you shared, starting with email. "
                   "If a seed phrase or key was exposed, move the funds to a new wallet at once. Then report it: in the United States to "
                   '<a href="https://reportfraud.ftc.gov/" rel="noopener">reportfraud.ftc.gov</a> and <a href="https://www.ic3.gov/" rel="noopener">ic3.gov</a>; in the United Kingdom to '
                   '<a href="https://www.actionfraud.police.uk/" rel="noopener">Action Fraud</a>; elsewhere to your national consumer-protection body or police cyber unit. '
                   "Tell the real company too, so it can warn other candidates.</p>")
         + section("Job offer safety: questions and answers", safety_faq), head=safety_ld)

    # Our side of the deal, in plain words and with a date
    page("promise/", f"What Is Free Here and What We Will Never Do | {SITE}",
         f"What {SITE} offers free with no account, what costs money and for whom, and the things this site will not do: no paid applying, no phone numbers, no data selling, no auto-renewal.",
         crumbs(("Our promise", "")) + "<h1>What is free here, and what we will never do</h1>"
         '<p class="lead">Job sites have taught people to expect the worst: a trial that becomes a yearly charge, a phone number that ends up with call centres, a “new” job that closed months ago. '
         f'This page is our side of the deal, in plain words. Dated {fdate(TODAY)}; if any of it changes, the change will be stated here first.</p>'
         + section("What is free, with no account?", "<ul><li>Searching, every filter, salary data and all rankings.</li><li>Opening any job and applying: you always go to the employer’s own page, and we take nothing for it.</li>"
                   "<li>Saving jobs, tracking applications and saved searches, kept in your browser.</li><li>The resume builder and every tool in the tools section.</li><li>Widgets, badges, the data files and the API.</li></ul>")
         + section("What will this site never do?", "<ul><li>Charge you to apply for a job.</li><li>Ask for your phone number, or call you.</li>"
                   "<li>Sell or pass on personal data. Job seekers have no accounts here, so there is nothing to sell.</li><li>Send you email you did not ask for.</li>"
                   "<li>Hold a job back for paying members. Every listing is public the moment we have it.</li><li>Renew a payment by itself. Anything paid is a single payment for a stated period.</li><li>Show a job as open after we know it is closed, or hide where a listing came from.</li>"
                   "<li>Publish invented reviews, numbers, partners or deadlines.</li></ul>")
         + section("What costs money, and for whom?", f'<p>Employers can pay to place a job or a company more prominently; the prices are public on the <a href="{P}/post-a-job/">employers page</a>. '
                   f'Job seekers pay nothing today. An optional paid set of email alerts and AI resume tools, <a href="{P}/plus/">Plus</a>, is planned; it will not unlock any listing, and what it includes and what it costs will be published in full before anything is sold.</p>')
         + section("How can I check that you keep to this?", f'<p>The <a href="{P}/status/">data status page</a> shows what the latest update did. The <a href="{P}/methodology/">methodology</a> explains every label and number. '
                   f'The <a href="{P}/privacy/">privacy page</a> lists what is stored and where. The site’s code is public.</p>'))

    # Privacy and terms
    page("privacy/", f"Privacy | {SITE}", "What this site stores and what it does not: no accounts, no tracking cookies, your saved jobs stay in your browser.",
         crumbs(("Privacy", "")) + "<h1>Privacy</h1><p class=\"lead\">Short version: we do not ask for an account, we do not set tracking cookies, and your saved jobs never leave your browser.</p>"
         "<h2 class='h2s'>What is stored in your browser</h2><p>Saved jobs, application statuses and notes, saved searches, followed companies, hidden jobs and companies, words you chose to leave out of results, "
         "recently viewed jobs, your skill profile, the resume you typed into the resume builder, what you entered into the free tools, and the light or dark theme. All of it is kept in your browser's local storage on this device and is not sent to us. "
         f'You can download or erase it on the <a href="{P}/my-jobs/">My jobs</a> page; each tool has its own Clear button; clearing your browser data removes everything.</p>'
         "<h2 class='h2s'>Your resume</h2><p>A resume you paste on the “For you” page or into a tool is read by a script in your browser. It is never uploaded. The resume builder and the tools keep what you typed in this browser so that it is still there next time.</p>"
         "<h2 class='h2s'>What we do not do</h2><p>No advertising trackers, no analytics cookies, no selling of data.</p>"
         "<h2 class='h2s'>Third parties</h2><p>The site is served by a hosting provider that, like any web server, sees your IP address when you load a page. Fonts, scripts and images are served from this site, not from other companies. "
         "When you press “Apply”, you go to the employer's own site, which has its own privacy policy.</p>"
         "<h2 class='h2s'>Changes</h2><p>If paid accounts or email alerts are added, this page will be updated before they go live.</p>")
    page("terms/", f"Terms of use | {SITE}", f"The terms for using {SITE}: what the site is, how accurate the listings are, where you apply, how job descriptions are used and how to get a listing removed.",
         crumbs(("Terms", "")) + "<h1>Terms of use</h1>"
         "<h2 class='h2s'>What this site is</h2><p>A search service for job postings published by companies on their own careers pages. We are not the employer and not a recruitment agency, and we take no part in hiring decisions.</p>"
         "<h2 class='h2s'>Accuracy</h2><p>Listings are collected automatically every hour. A job may change or close between updates, and details such as salary, perks and location are read from the posting text. Always check the employer's own page before you rely on them.</p>"
         "<h2 class='h2s'>Applying</h2><p>Applications are made on the employer's site. Viewing jobs and applying is free.</p>"
         "<h2 class='h2s'>Names and trademarks</h2><p>Company names belong to their owners and are used only to identify who is hiring. A listing here does not mean the company endorses this site.</p>"
         "<h2 class='h2s'>Salary and hiring data</h2><p>Figures on the salary, trends and insights pages are calculated from advertised ranges. They are estimates for information, not an offer or a guarantee.</p>"
         "<h2 class='h2s'>Job descriptions</h2><p>Descriptions are the employers’ own text, read from the hiring feeds they publish for display on other sites. They are shown unchanged, with the employer named and a link to the original posting.</p>"
         "<h2 class='h2s'>Removing a listing</h2><p>" + (f"Employers who want a listing or company page removed can write to us: {contact}. It is taken down at the next update." if contact
                                                        else "Employers who want a listing or company page removed can ask through the contact details on the employers page.") + "</p>")

    # For you: five plain questions; the answers stay in the browser and every open job is checked against them
    FY_WORK = [("engineering", "Building software", "developers, testers, DevOps"), ("data-research", "Working with data", "analysts, data scientists, researchers"),
               ("design", "Design", "how a product looks and works"), ("product", "Planning the product", "product and program managers"),
               ("sales-bd", "Sales", "finding customers and partners"), ("marketing", "Marketing", "making a product known"),
               ("support", "Helping customers", "support and customer success"), ("finance", "Finance", "accounting, planning, trading"),
               ("people", "Hiring and HR", "recruiters and people teams"), ("compliance-legal", "Legal and compliance", "lawyers, risk and policy"),
               ("operations", "Operations and IT", "keeping the business running"), ("security", "Security", "protecting systems and data")]
    pct_paid = round(100 * sum(bool(j["salary"]) for j in active) / max(1, n))
    def fy_opt(v, label, hint="", count=None):
        return (f'<button class="opt" type="button" data-v="{e(str(v))}" aria-pressed="false"><b>{e(label)}</b>' + (f"<span>{e(hint)}</span>" if hint else "")
                + (f'<i>{count:,}</i>' if count is not None else "") + "</button>")
    fy_work = "".join(fy_opt(s_, lb, hint, len(by_cat[s_])) for s_, lb, hint in FY_WORK if by_cat[s_])
    fy_exp = (fy_opt(0, "I am starting out", "internships and junior roles") + fy_opt(1, "A few years", "roles with no “senior” in the title")
              + fy_opt(2, "Many years", "senior and staff roles") + fy_opt(3, "I lead people", "lead, manager, director"))
    fy_where = fy_opt("remote", "From home", "remote roles") + fy_opt("office", "At an office", "on site or hybrid") + fy_opt("", "Either", "")
    code_slug_all = {rule: slug for _, slug, rule in PLACES if isinstance(rule, str) and rule != "region"}
    fy_places = "".join(f'<option value="{c_}" data-s="{code_slug_all.get(c_, "")}" data-r="{region_of.get(c_, "")}">{e(nm_)}</option>'
                        for c_, nm_ in sorted([("US", "United States")] + [(c_, nm_) for c_, nm_, _, _ in COUNTRIES if c_ != "US"], key=lambda x: x[1]))
    fy_pay = "".join(fy_opt(v, lb) for v, lb in [(0, "Any pay"), (60000, "$60K"), (80000, "$80K"), (100000, "$100K"), (130000, "$130K"), (160000, "$160K"), (200000, "$200K"), (250000, "$250K")])
    def fy_chip(t):
        tip = skills_info.plain(t)
        return f'<button class="chipbtn" type="button" data-skill="{e(t)}" aria-pressed="false"' + (f' title="{e(tip)}"' if tip else "") + f">{e(t)}</button>"
    fy_top = "".join(fy_chip(t) for t, _ in skill_counts.most_common(18))
    fy_groups = defaultdict(list)
    for t, _ in skill_counts.most_common():
        fy_groups[skills_info.INFO.get(t, ("other", ""))[0]].append(t)
    fy_all = "".join(f'<p class="flabel">{e(gn)} <span>{e(gd.rstrip("."))}</span></p><div class="skillbar">{"".join(fy_chip(t) for t in fy_groups[gk])}</div>'
                     for gk, gn, gd in skills_info.GROUPS + [("other", "Other skills", "")] if fy_groups.get(gk))
    def ask(n_, q_, hint, inner):
        return (f'<div class="ask" role="group" aria-labelledby="ask{n_}"><h2 id="ask{n_}"><span class="ask-n">{n_}</span>{e(q_)}</h2>' + (f'<p class="ask-h">{hint}</p>' if hint else "") + inner + "</div>")
    fy_qa = [("How is the fit worked out?", "Each open job is compared with every question you answered. A job that agrees with an answer gets a tick for it; a job that says nothing on the point, "
              "such as a posting with no pay, gets a question mark; a job that contradicts an answer is left out. Jobs with the most ticks come first."),
             ("Is my resume or any answer sent anywhere?", "No. The answers and the resume text are read by a script inside your browser and kept in this browser only. Clear my answers removes them."),
             ("Why do many jobs carry a question mark for pay?", f"About {pct_paid}% of the open jobs state pay in the posting. The rest are still listed, below the ones that state it, unless you choose to hide them."),
             ("Why is pay in US dollars a year?", "Most postings that state pay give a yearly range in US dollars, so that is what can be compared. A posting that gives pay per hour or in another currency is shown with its own figure and a question mark."),
             ("Does it cost anything?", "No. Matching, searching and applying are free, and applying always happens on the employer’s own page.")]
    fy_faq = '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in fy_qa) + "</dl>"
    fy_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in fy_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("for-you/", f"Tech Jobs That Match Your Skills and Pay | {SITE}",
         f"Say what work you want, your experience, where you live and the pay you need. {n:,} open tech jobs are checked against your answers and the ones that fit are listed first, with the reason.",
         crumbs(("For you", "")) + f'<h1>Answer five questions and see the jobs that <span class="hl">fit you</span></h1>'
         f'<p class="lead">Reading {n:,} postings to find the twenty worth applying to takes days. Say what work you want, how much experience you have, where you live and what you need to earn. '
         'Every open job is checked against your answers, and next to each one you see what fits and what does not.</p>'
         '<p class="plain"><b>In plain words:</b> this page is a short form. Nothing you answer leaves your browser, there is no account, and you can skip any question.</p>'
         '<div id="fy-root" class="fy"><div class="fy-form">'
         + ask(1, "What kind of work do you want?", "Pick one or several. Leave it empty to see every kind.", f'<div class="opts" id="fy-work">{fy_work}</div>')
         + ask(2, "How much experience do you have?", "", f'<div class="opts one" id="fy-exp">{fy_exp}</div>')
         + ask(3, "Where do you want to work?", "", f'<div class="opts one" id="fy-where">{fy_where}</div>'
               f'<label class="ask-l" for="fy-place">Your country</label><select id="fy-place"><option value="">Any country</option>{fy_places}</select>'
               '<p class="ask-h" id="fy-place-note">Remote roles are often open to some countries only, so the country matters for them too.</p>')
         + ask(4, "How much do you need to earn?", "In US dollars a year, before tax. Jobs that pay less are left out.", f'<div class="opts one pay" id="fy-pay">{fy_pay}</div>'
               '<label class="ask-l" for="fy-pay-in">Or type your own figure</label><span class="payin">$<input type="number" id="fy-pay-in" min="0" max="2000000" step="5000" inputmode="numeric" placeholder="120000"> a year</span>'
               '<label class="check"><input type="checkbox" id="fy-nopay"> Hide jobs that do not state pay</label><p class="ask-h" id="fy-pay-note"></p>')
         + ask(5, "What can you do?", "Optional. These are tools and skills that postings ask for by name. If the names mean nothing to you, skip this question.",
               f'<div id="fy-skills"><div class="skillbar">{fy_top}</div>'
               f'<details class="scan"><summary>All {len(skill_counts)} skills, in groups</summary>{fy_all}</details></div>'
               '<details class="scan"><summary>Paste your resume and have the skills found for you</summary>'
               '<textarea id="fy-text" rows="7" placeholder="Paste the text of your resume here" aria-label="Resume text"></textarea>'
               '<p><button class="btn sm" id="fy-scan" type="button">Find my skills</button> <span class="note" id="fy-scan-note"></span></p></details>')
         + '<p class="fy-acts"><button class="btn ghost sm" id="fy-example" type="button">Show an example</button> <button class="btn ghost sm" id="fy-clear" type="button">Clear my answers</button></p>'
         '<p class="fy-acts more"><button class="btn ghost sm" id="fy-alert" type="button">Tell me when new jobs fit</button> <button class="btn ghost sm" id="fy-share" type="button">Copy a link to these answers</button> '
         '<button class="btn ghost sm" id="fy-pic" type="button">Save the result as a picture</button></p><p class="note" id="fy-note" role="status" hidden></p></div>'
         '<div class="fy-out" id="fy-out"><div class="fy-sum" id="fy-count" aria-live="polite"></div><div id="fy-gap" hidden></div>'
         '<ul class="jobs" id="fy-list"></ul><p><button class="btn" id="fy-more" type="button" hidden>Show more</button></p></div></div>'
         '<a class="fy-jump" id="fy-jump" href="#fy-out" hidden></a>'
         + section("Questions about this page", fy_faq), head=fy_ld)
    write("data/skills.json", json.dumps([[n_, rx] for n_, rx in SKILLS if n_ in skill_counts], ensure_ascii=False), sitemap=False)
    write("data/skillinfo.json", json.dumps({t: skills_info.plain(t) for t in skill_counts if skills_info.plain(t)}, ensure_ascii=False, separators=(",", ":")), sitemap=False)

    # Skills hub
    by_group = defaultdict(list)
    for t, c in skill_counts.most_common():
        by_group[skills_info.INFO.get(t, ("other", ""))[0]].append((t, c))
    gloss = lambda rows_: '<ul class="gloss">' + "".join(
        f'<li><a href="{P}/skills/{tslug(t)}/"><b><u>{e(t)}</u></b><span class="c">{c:,} jobs</span>'
        + (f'<span class="d">{e(skills_info.plain(t))}</span>' if skills_info.plain(t) else "") + "</a></li>" for t, c in rows_) + "</ul>"
    groups_ = [(g, nm, d) for g, nm, d in skills_info.GROUPS if by_group.get(g)] + ([("other", "Other skills", "")] if by_group.get("other") else [])
    skills_body = "".join(f'<section class="sec" id="{g}"><div class="sec-head"><h2>{e(nm)}</h2></div>' + (f'<p class="note" style="margin:-4px 0 8px">{e(d)}</p>' if d else "")
                          + gloss(by_group[g]) + "</section>" for g, nm, d in groups_)
    page("skills/", f"Tech Jobs by Skill — {len(skill_counts)} skills explained | {SITE}",
         f"Open tech jobs by skill, with a plain-English line on what each of the {len(skill_counts)} skills is: languages, AI, data, cloud, design and business tools.",
         crumbs(("Skills", "")) + '<h1>Tech jobs by skill</h1>'
         '<p class="lead">Job postings are full of names like Kubernetes or dbt. Here each one comes with a line that says what it is in plain words, '
         'and the number of open roles that ask for it today. Pick one to see the jobs, the pay and who is hiring.</p>'
         '<p class="rel"><span>Jump to:</span>' + "".join(f'<a href="#{g}">{e(nm)}</a>' for g, nm, _ in groups_) + "</p>" + skills_body)

    # Resume builder: stays in the browser, prints to PDF
    page("resume/", f"Free Resume Builder — free PDF and Word download | {SITE}",
         "Build an ATS-friendly resume in your browser: five templates, free PDF and Word download, no account. Nothing is uploaded, and one click matches it to open tech jobs.",
         crumbs(("Resume builder", "")) + '<h1>Free resume builder that screening software can read</h1><p class="lead">Two-column templates with icons look good to people and can turn into scrambled text in applicant tracking systems. '
         'And many builders let you write for free, then charge for the download. Here you get five plain one-column templates that parse cleanly, and the PDF and the Word file are free. '
         'Fill in the form, watch the page update, download. Everything stays in this browser: no account, nothing is uploaded.</p>'
         '<p class="note no-print">“Save as PDF” opens your browser’s print window: choose “Save as PDF” as the printer.</p>'
         '<div id="rb"><div class="rb-actions"><button class="btn" id="rb-print" type="button">Save as PDF</button><button class="btn ghost" id="rb-doc" type="button">Download for Word</button><button class="btn ghost" id="rb-json" type="button" title="The open JSON Resume format, readable by other tools and AI assistants">JSON</button>'
         '<label class="wl rb-tplpick">Template<select id="rb-tpl"><option value="classic">Classic</option><option value="modern">Modern</option><option value="compact">Compact</option>'
         '<option value="developer">Developer</option><option value="executive">Executive</option></select></label>'
         '<button class="btn ghost" id="rb-match" type="button">Match jobs to this resume</button><button class="btn ghost" id="rb-clear" type="button">Start over</button></div>'
         f'<p class="rb-plus no-print"><b>With Plus, AI writes it with you</b><span>bullet points from your notes · a summary · the resume reworded for one posting · a review with a score</span><a href="{P}/plus/">See what Plus adds</a></p>'
         '<div id="rb-demand" class="no-print" aria-live="polite"></div>'
         '<div class="rgrid"><div id="rb-form"></div><div id="rb-preview" aria-live="polite"></div></div></div>'
         + '<section class="sec no-print"><div class="sec-head"><h2>What makes a resume get read</h2></div><div class="feats">'
         '<div class="feat"><h3>One page, plain layout</h3><p>Screening software reads simple single-column text best. That is the layout you get here.</p></div>'
         '<div class="feat"><h3>Results, not duties</h3><p>“Cut page load time from 4s to 1.2s” says more than “responsible for performance”.</p></div>'
         '<div class="feat"><h3>The posting’s own words</h3><p>If the job asks for PostgreSQL and you know it, write PostgreSQL, not “databases”.</p></div></div></section>'
         + f'<script src="{P}/resume.js?v={V}" defer></script>')

    # Glossary: the words of a job search in plain English. Linked from every place where a term could stop a newcomer.
    GLOSS = [
        ("Apply on company site", "The button that takes you to the employer’s own page, where you fill in the application. We never collect applications ourselves."),
        ("Benefits", "What the employer gives on top of pay: health insurance, a pension, paid holidays and the like."),
        ("Category", "The kind of work: engineering, design, sales and so on. We work it out from the job title."),
        ("Closed job", "A job the employer has taken down. Its page stays on this site, marked as closed, so old links keep working."),
        ("Contract", "Work for a fixed period or a single project, usually paid by the hour or the day, without the benefits an employee gets."),
        ("Cover letter", "A short letter sent with a resume that says why you want this particular job."),
        ("Entry-level", "A job for people at the start of a career: internships, graduate roles and junior positions."),
        ("Equity and stock options", "A share in the company, or the right to buy shares later at a price fixed today. What it is worth depends on what the company turns out to be worth."),
        ("Featured job", "A listing an employer paid to show higher in the list. It is always labelled as featured."),
        ("Full-time and part-time", "Full-time is usually about 40 hours a week. Part-time is fewer."),
        ("Hiring system", "The software a company uses to publish its jobs and collect applications; Greenhouse, Lever and Ashby are examples. We read jobs straight from these systems, which is why they are current."),
        ("Hybrid", "Part of the week in the office and part at home."),
        ("Internship", "A short placement, usually paid, for students and recent graduates."),
        ("Last checked", "The date we last saw the job on the employer’s own page."),
        ("Level", "How much experience the job asks for. Junior means little, senior means several years, and lead, staff or principal are the most experienced people in a team. We read the level from the job title."),
        ("Median", "The middle value. Line up all the salaries from lowest to highest and take the one in the middle: half are above it and half below. One very high salary hardly moves it, which is why we use it instead of an average."),
        ("Open for", "How many days have passed since the employer posted the job. A job open for more than 90 days is flagged, because some of those are no longer being filled."),
        ("Perk", "Something the employer offers beyond pay, such as visa sponsorship or a budget for courses. We show a perk only when the posting mentions it."),
        ("Posting", "One job advertisement. Also called a listing."),
        ("Recruiter", "A person whose job is to find candidates for an employer."),
        ("Relocation", "The employer helps pay for your move to another city or country."),
        ("Remote", "Work done from home or from anywhere outside an office. Many remote jobs are still limited to certain countries or time zones; the job page says which."),
        ("Resume", "A one- or two-page summary of your work and education. Also called a CV."),
        ("Salary range", "The lowest and the highest pay the employer says it may offer for the job, before tax."),
        ("Skill", "A tool or a language that the posting mentions, such as Python or Figma. The skills page explains each one in a line."),
        ("Talent pool", "A standing invitation to send a resume, not one specific opening."),
        ("Visa sponsorship", "The employer helps a worker from another country get the permit needed to work there."),
        ("Widget", "A small box with a list of jobs that the owner of a website can place on their own site."),
        ("Work from anywhere", "A remote job whose posting names no country and no region at all."),
    ]
    gslug = lambda t: re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    gl_extra = {"Skill": f' <a href="{P}/skills/">Skills explained</a>.', "Widget": f' <a href="{P}/widgets/">The job widget</a>.', "Median": f' <a href="{P}/salaries/">Salaries</a>.',
                "Remote": f' <a href="{P}/remote/">Remote jobs</a>.', "Entry-level": f' <a href="{P}/entry-level/">Entry-level jobs</a>.', "Resume": f' <a href="{P}/resume/">Resume builder</a>.',
                "Closed job": f' <a href="{P}/archive/">Archive</a>.', "Perk": f' <a href="{P}/perks/">Jobs by perk</a>.'}
    page("glossary/", f"Job Search Words Explained in Plain English | {SITE}",
         f"{len(GLOSS)} words you meet when looking for a job, each explained in one or two plain sentences: remote, hybrid, median salary, equity, visa sponsorship and more.",
         crumbs(("Glossary", "")) + "<h1>Job search words in plain English</h1>"
         f'<p class="lead">{len(GLOSS)} words that come up on this site and in job postings, each explained in a sentence or two. If a word on the site is not here, it should be: tell us and we will add it.</p>'
         '<dl class="qa">' + "".join(f'<div id="{gslug(t)}"><dt>{e(t)}</dt><dd>{e(d)}{gl_extra.get(t, "")}</dd></div>' for t, d in GLOSS) + "</dl>",
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "Job search glossary", "url": f"{FULL}/glossary/",
               "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t, "description": d, "url": f"{FULL}/glossary/#{gslug(t)}"} for t, d in GLOSS]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")

    # Partners
    page("partners/", f"Partner With Us — communities, bootcamps, career services | {SITE}",
         "Ways to work with us: live job widgets and feeds for communities and newsletters, job pages for bootcamps and universities, and offers for career services.",
         crumbs(("Partners", "")) + '<h1>Partner with us</h1><p class="lead">If your readers, students or members ask who is hiring, you can show them a live list from this site instead of keeping one by hand. It is free. Here is what we can set up.</p><div class="feats">'
         f'<a class="feat" href="{P}/widgets/"><h2>Communities and newsletters</h2><p>A live jobs widget, feed or weekly list for your niche: one skill, one city, remote only. Free, with a link back.</p></a>'
         f'<a class="feat" href="{P}/widgets/"><h2>Bootcamps and universities</h2><p>A board of entry-level roles and internships for your students, embedded on your careers page and updated every hour.</p></a>'
         f'<a class="feat" href="{P}/api/"><h2>Developers and bots</h2><p>A free JSON API and RSS for Slack, Discord and Telegram bots or your own project.</p></a>'
         f'<a class="feat" href="{P}/post-a-job/"><h2>Employers and recruiters</h2><p>Featured jobs, a company spotlight, or sponsorship of one skill or category page.</p></a>'
         f'<a class="feat" href="{P}/trends/"><h2>Writers and researchers</h2><p>Hiring and salary data you can quote, with CSV downloads and ready citations.</p></a>'
         '<div class="feat"><h2>Career services</h2><p>Resume review, interview coaching, courses. We plan a page that recommends services visitors find useful; write to us if you run one.</p></div></div>'
         + ('<section class="sec"><div class="sec-head"><h2>Get in touch</h2></div><p>Write to us: ' + contact + ".</p></section>" if contact else
            '<div class="banner" style="margin-top:24px">Contact details will be published here shortly. The widgets, feeds and data above already work without asking anyone.</div>'))

    # Bare page for iframe embeds: /embed/?jobs=skill:python&limit=6&layout=cards&theme=dark&accent=%23ff5500
    write("embed/", f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Jobs widget | {e(SITE)}</title><style>html,body{{margin:0;background:transparent}}body{{padding:2px 8px 8px 2px}}</style></head><body>
<div id="w"><a href="{FULL}/" target="_blank" rel="noopener">Tech jobs on {e(SITE)}</a></div>
<script>(function(){{var p=new URLSearchParams(location.search),el=document.getElementById('w');
el.setAttribute('data-hrn-jobs',p.get('jobs')||'latest');['limit','layout','theme','accent','title','search','company'].forEach(function(k){{if(p.get(k))el.setAttribute('data-'+k,p.get(k));}});
el.setAttribute('data-hrn-base','{P}');}})();</script><script src="{P}/widget.js?v={V}"></script></body></html>""", sitemap=False)

    # The board: a full-screen, auto-rotating wall of the freshest roles (for a second monitor, an office screen, a classroom)
    write("board/", f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Board — live tech jobs wall | {e(SITE)}</title><meta name="description" content="A full-screen live board of the freshest tech jobs, rotating automatically. Put it on a second monitor, an office screen or a classroom wall.">
<link rel="canonical" href="{FULL}/board/"><link rel="icon" type="image/svg+xml" href="{P}/favicon.svg">
<style>@font-face{{font-family:"Inter";font-weight:400 700;font-display:swap;src:url({P}/fonts/inter-latin.woff2) format("woff2")}}
@font-face{{font-family:"JetBrains Mono";font-weight:500 700;font-display:swap;src:url({P}/fonts/jbmono-latin.woff2) format("woff2")}}
html,body{{margin:0;height:100%;background:#0b0b0a;color:#f3f2ec;font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;overflow:hidden}}
.top{{display:flex;justify-content:space-between;align-items:center;padding:2.2vh 3vw;border-bottom:1px solid #2b2b27;font-size:clamp(12px,1.5vw,20px);letter-spacing:.08em;text-transform:uppercase;color:#a5a399}}
.top a{{color:#f3f2ec;text-decoration:none;font-family:Inter,system-ui,sans-serif;font-weight:700;letter-spacing:-.01em;text-transform:none;font-size:clamp(16px,2vw,28px)}}
.top b{{color:#7ee39a;font-weight:500}}.dot{{display:inline-block;width:.6em;height:.6em;border-radius:50%;background:#3ecf5f;margin-right:.6em}}
#rows{{padding:1vh 3vw}}.r{{display:grid;grid-template-columns:7ch minmax(0,1.3fr) minmax(0,.8fr) minmax(0,.7fr);gap:2vw;align-items:baseline;padding:1.55vh 0;border-bottom:1px solid #1f1f1c;animation:in .5s backwards}}
@keyframes in{{from{{opacity:0;transform:translateY(8px)}}}}.a{{color:#7ee39a;font-size:clamp(11px,1.3vw,18px)}}
.t{{font-family:Inter,system-ui,sans-serif;font-weight:700;font-size:clamp(15px,2.1vw,30px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#f3f2ec;text-decoration:none}}
.c,.l{{font-size:clamp(11px,1.4vw,20px);color:#a5a399;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.c{{color:#e9e7de}}
.foot{{position:fixed;left:0;right:0;bottom:0;display:flex;justify-content:space-between;padding:1.6vh 3vw;font-size:clamp(10px,1.1vw,15px);color:#77756c;letter-spacing:.06em;text-transform:uppercase;background:#0b0b0a}}
.foot a{{color:#7ee39a;text-decoration:none}}.foot .m{{color:#e9e7de}}.n{{padding:6vh 0;font-size:clamp(14px,1.8vw,24px);color:#a5a399}}.n a{{color:#7ee39a}}@media(max-width:700px){{.r{{grid-template-columns:5ch minmax(0,1fr)}}.c,.l{{grid-column:2}}}}</style></head><body>
<div class="top"><a href="{P}/"><span class="dot"></span>{e(SITE)}</a><h1 id="what" style="all:unset">Fresh on the board</h1><b id="clock"></b></div><div id="rows"></div>
<div class="foot"><span id="count"></span><a href="{P}/widgets/">Put this board on your screen</a></div>
<script>(function(){{var q=new URLSearchParams(location.search),path=q.get('skill')?'skills/'+q.get('skill'):q.get('company')?'companies/'+q.get('company'):q.get('location')?'locations/'+q.get('location'):q.has('remote')?'remote':'latest';
var rows=document.getElementById('rows'),jobs=[],page=0,per=Math.max(4,Math.floor((innerHeight*0.78)/Math.max(46,innerHeight*0.075)));
function esc(v){{return String(v==null?'':v).replace(/[&<>"]/g,function(c){{return{{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]}})}}
function age(iso){{var p=String(iso||'').split('-');if(p.length<3)return'';var n=new Date(),d=new Date(+p[0],+p[1]-1,+p[2]),k=Math.max(0,Math.round((new Date(n.getFullYear(),n.getMonth(),n.getDate())-d)/864e5));return k===0?'TODAY':k<14?k+'D':Math.floor(k/7)+'W'}}
function draw(){{if(!jobs.length)return;var s=jobs.slice(page*per,page*per+per);if(!s.length){{page=0;s=jobs.slice(0,per)}}
rows.innerHTML=s.map(function(j,i){{return'<div class="r" style="animation-delay:'+i*70+'ms"><span class="a">'+age(j.posted)+'</span><a class="t" href="'+esc(j.url)+'">'+esc(j.title)+'</a><span class="c">'+esc(j.company)+'</span><span class="l">'+esc(j.salary||j.location||(j.remote?'Remote':''))+'</span></div>'}}).join('');page++}}
function tick(){{document.getElementById('clock').textContent=new Date().toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}})}}
var asked=q.get('skill')||q.get('company')||q.get('location')||'',timer;
function note(html){{rows.innerHTML='<p class="n">'+html+'</p>'}}
function show(d,miss){{jobs=d.jobs;page=0;document.getElementById('what').textContent=miss?'Latest roles':d.name;document.getElementById('count').innerHTML=(miss?'<span class="m">No board for “'+esc(asked.slice(0,40))+'” · showing the latest</span> · ':'')+Number(d.total).toLocaleString('en-US')+' open roles · updated every hour';draw();clearInterval(timer);timer=setInterval(draw,9000)}}
function load(p,miss){{return fetch('{P}/api/v1/'+p+'.json').then(function(r){{if(!r.ok)throw 0;return r.json()}}).then(function(d){{if(!d.jobs||!d.jobs.length)throw 0;show(d,miss)}})}}
load(path.toLowerCase().replace(/[^a-z0-9/_.+-]/gi,'-'),false).catch(function(){{if(path==='latest')throw 0;return load('latest',true)}}).catch(function(){{note('The board could not load right now. <a href="{P}/jobs/">Open the job list</a>')}});
tick();setInterval(tick,20000);setTimeout(function(){{location.reload()}},3600000)}})();</script></body></html>""")

    # Widgets, badges, API: ways for other sites to show our jobs and link back
    wb_data = {"site": SITE, "skills": [[tslug(t), t] for t, _ in skill_counts.most_common()], "categories": [[cs, CAT[cs]] for cs in CAT if by_cat[cs]],
               "locations": [[slug, name.removeprefix("the ")] for name, slug, _ in places], "companies": [[slugify(c), c] for c, _ in comp_items if OPEN[c]]}
    wsize = round(len((ROOT / "assets" / "widget.js").read_bytes()) / 1024)
    w_faq = [("Is the job widget free?", "Yes. There is no plan, no account and no limit on page views. The snippet keeps a small link back to this site, which is how the widget stays free."),
             ("Do I need to sign up or get a key?", "No. Choose what to show in the builder on this page, copy the code and paste it into your site."),
             ("How often do the jobs update?", f"Lists from our index are rebuilt every hour from the career pages of {m} companies, so closed roles drop out by themselves. A list of your own company’s jobs is read live from your hiring system every time the page opens."),
             ("Can I show only my own company’s jobs?", "Yes. If you post jobs through Greenhouse, Lever or Ashby, pick that system in the builder and type the name of your board. The widget reads your public board directly, with no account and nothing to keep in sync by hand."),
             ("Does it work with WordPress, Webflow, Wix, Squarespace, Shopify and Framer?", "Yes. Anything that lets you paste HTML works with the script version. Builders that strip scripts, such as Notion, take the iframe version. The table on this page says where to paste the code on each platform."),
             ("Will the widget slow my page down?", f"The script is about {wsize} KB, loads asynchronously and draws inside its own container, so it does not block your page and your styles do not leak into it or out of it."),
             ("Where does a click on a job lead?", "To the job’s page on this site, which shows the salary, the remote rules and the date of the last check, and from there to the employer’s own application page. For your own board the click goes straight to your application page."),
             ("Can I change how it looks?", "Yes: five layouts (list, cards, compact, ticker and a full careers page), a light, dark or automatic theme, your own accent colour, your own heading and an optional search box.")]
    w_faq_html = '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in w_faq) + "</dl>"
    w_ld = ('<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{SITE} job widget", "url": f"{FULL}/widgets/", "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
         "description": "A free embeddable job widget: self-updating tech jobs by skill, city, category or company, or a company’s own jobs read from Greenhouse, Lever or Ashby.",
         "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": {"@type": "Organization", "name": SITE, "url": FULL + "/"}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in w_faq]}],
        ensure_ascii=False).replace("</", "<\\/") + "</script>" + crumbs_ld([("Job widget", "")]))
    wt = lambda head, rows_: ('<div class="tablewrap"><table><tr>' + "".join(f"<th>{h_}</th>" for h_ in head) + "</tr>"
                              + "".join("<tr>" + "".join(f"<td>{c_}</td>" for c_ in r_) + "</tr>" for r_ in rows_) + "</table></div>")
    page("widgets/", f"Free Job Widget for Your Website | {SITE}",
         "A free job widget for any website: one snippet shows self-updating tech jobs by skill or city, or your own company’s jobs from Greenhouse, Lever or Ashby. No sign-up.",
         crumbs(("Job widget", "")) + '<h1>Free job widget for your website</h1>'
         f'<p class="plain"><b>In plain words:</b> a widget is a small box with a list of jobs that sits on your own website or blog. You choose what it shows, copy a short piece of code from this page and paste it into your site. '
         f'After that the list keeps itself up to date. Looking for a job yourself? You do not need this page: <a href="{P}/jobs/">go to the job search</a>.</p>'
         '<p class="lead">It is free and needs no account. The list can show tech jobs from our index, by skill, city, category or company, '
         'or your own company’s jobs, read straight from the hiring software you already use (Greenhouse, Lever or Ashby), so nobody has to type them in.</p>'
         f'<div id="wb" data-full="{FULL}" data-base="{P}"><div class="card"><div class="fbar" style="margin:0">'
         '<label class="wl">What to show<select id="wb-type"><optgroup label="Tech jobs from our index"><option value="skill">Jobs by skill</option><option value="category">Jobs by category</option><option value="location">Jobs by location</option>'
         '<option value="company">Jobs at a company we list</option><option value="remote">Remote jobs</option><option value="latest">Latest jobs</option></optgroup>'
         '<optgroup label="Your own company’s jobs"><option value="greenhouse">From Greenhouse</option><option value="lever">From Lever</option><option value="ashby">From Ashby</option></optgroup></select></label>'
         '<label class="wl">Which one<select id="wb-val"></select></label>'
         '<label class="wl" id="wb-board-l" hidden>Your board’s name<input type="text" id="wb-board" placeholder="acme" autocomplete="off" spellcheck="false"></label>'
         '<label class="wl" id="wb-co-l" hidden>Company name<input type="text" id="wb-co" placeholder="Acme" autocomplete="off"></label>'
         '<label class="wl">How many jobs<select id="wb-limit"><option>4</option><option selected>6</option><option>8</option><option>10</option><option>15</option></select></label>'
         '<label class="wl">How it looks<select id="wb-layout"><option value="list">List</option><option value="cards">Cards</option><option value="compact">Compact (sidebar)</option><option value="ticker">Ticker</option><option value="careers">Careers page (all jobs, with search)</option></select></label>'
         '<label class="wl">Light or dark<select id="wb-theme"><option value="auto">Match the visitor</option><option value="light">Light</option><option value="dark">Dark</option></select></label>'
         '<label class="wl">Colour<input type="color" id="wb-accent" value="#1f9d55" aria-label="Accent colour"></label>'
         '<label class="wl">Kind of code<select id="wb-mode"><option value="script">Standard (works on most sites)</option><option value="iframe">For Notion and builders that block scripts</option></select></label>'
         '<label class="check"><input type="checkbox" id="wb-search"> Search box and “Show more”</label></div>'
         '<p class="note" id="wb-hint" hidden style="margin:12px 0 0">The board name is the last part of your careers page address: boards.greenhouse.io/<b>acme</b>, jobs.lever.co/<b>acme</b> or jobs.ashbyhq.com/<b>acme</b>.</p></div>'
         + section("This is how it will look", '<div id="wb-preview" style="margin-bottom:16px"></div><textarea id="wb-code" rows="4" readonly aria-label="Widget code"></textarea>'
                   '<p><button class="btn sm" type="button" data-copy="wb-code">Copy the code</button> <span class="note">Above is the real widget, working on this page. Below it is the code to copy and paste into your site.</span></p>')
         + '<section class="sec" id="wb-badge-sec"><div class="sec-head"><h2>Live badge</h2></div><p><img id="wb-badge" alt="Live badge preview" height="28"></p><p class="note">The number on the badge is recalculated every day. Good for a README, a footer or a blog post.</p>'
           '<span class="flabel">HTML</span><textarea id="wb-badge-html" rows="2" readonly aria-label="Badge HTML"></textarea><p><button class="btn sm" type="button" data-copy="wb-badge-html">Copy HTML</button></p>'
           '<span class="flabel">Markdown (GitHub README)</span><textarea id="wb-badge-md" rows="2" readonly aria-label="Badge Markdown"></textarea><p><button class="btn sm" type="button" data-copy="wb-badge-md">Copy Markdown</button></p></section>'
         + "</div>"
         + section("How to add the job widget to your site", '<ol class="steps"><li><b>Choose what to show</b> in the builder above: a skill, a city, a category, one company, or your own board.</li>'
                   "<li><b>Copy the code.</b> It is two lines: a container with a normal link inside, and the script.</li>"
                   "<li><b>Paste it where the list should appear</b>, in any block that accepts HTML. The jobs load when the page opens and stay current without you.</li></ol>"
                   '<p class="note">If scripts are blocked, the link inside the container still shows, so the spot never ends up empty.</p>')
         + section("Where to paste it, by platform", wt(["Platform", "Where the code goes"], [
             [f'<a href="{P}/widgets/wordpress/"><strong>WordPress</strong></a>', "Add a Custom HTML block in the editor, or a Custom HTML widget in a sidebar or footer, and paste the script version."],
             [f'<a href="{P}/widgets/webflow/"><strong>Webflow</strong></a>', "Add an Embed element and paste the script version. Scripts do not run in the Designer preview, so publish the page to see it."],
             [f'<a href="{P}/widgets/wix/"><strong>Wix</strong></a>', "Add → Embed code → Embed HTML, then paste the iframe version."],
             [f'<a href="{P}/widgets/squarespace/"><strong>Squarespace</strong></a>', "Add a Code block and paste the script version. Squarespace allows scripts in Code blocks only on some plans; where it does not, use the iframe version in an Embed block."],
             [f'<a href="{P}/widgets/shopify/"><strong>Shopify</strong></a>', "In the theme editor add a Custom Liquid section or block and paste the script version."],
             [f'<a href="{P}/widgets/framer/"><strong>Framer</strong></a>', "Insert → Embed, switch it to HTML and paste the script version."],
             [f'<a href="{P}/widgets/ghost/"><strong>Ghost</strong></a>', "Add an HTML card in the editor and paste the script version."],
             [f'<a href="{P}/widgets/notion/"><strong>Notion</strong></a>', "Notion removes scripts. Take the iframe version and paste the address from its <code>src</code> into an Embed block."],
             ["<strong>Plain HTML</strong>", "Paste the script version anywhere inside <code>&lt;body&gt;</code>."]]))
         + section("Your own company’s jobs, straight from your hiring system",
                   '<p>If your company posts jobs through Greenhouse, Lever or Ashby, the widget can read your public job board directly in the visitor’s browser. '
                   'Pick your system in the builder and type the name of your board. New roles appear and closed ones disappear by themselves, and a click on a job opens your own application page.</p>'
                   '<p>Nothing passes through our servers in this mode, so there is no account, no limit on the number of jobs and nothing to pay. '
                   'A very large board, with thousands of roles, takes a moment longer to load. Add the search box for boards with more than a dozen roles.</p>')
         + section("Options", wt(["Attribute", "What it does", "Default"], [
             ["<code>data-hrn-jobs</code>", "What to show: <code>latest</code>, <code>remote</code>, <code>skill:python</code>, <code>category:engineering</code>, <code>location:london</code>, <code>company:stripe</code>, "
                                           "or your own board: <code>greenhouse:acme</code>, <code>lever:acme</code>, <code>ashby:acme</code>", "<code>latest</code>"],
             ["<code>data-limit</code>", "Rows to show, 1 to 20. With the search box on, rows per page", "6"],
             ["<code>data-layout</code>", "<code>list</code>, <code>cards</code>, <code>compact</code>, <code>ticker</code> or <code>careers</code>", "<code>list</code>"],
             ["<code>data-theme</code>", "<code>auto</code> follows the visitor’s system, or force <code>light</code> or <code>dark</code>", "<code>auto</code>"],
             ["<code>data-accent</code>", "Any hex colour for the hover bar and the link underline", "<code>#1f9d55</code>"],
             ["<code>data-search</code>", "<code>1</code> adds a search box, a team filter where teams exist, and “Show more”", "off"],
             ["<code>data-title</code>", "Your own heading for the widget", "the name of the list"],
             ["<code>data-company</code>", "Your company name, shown in the heading of your own board", "none"]]))
         + section("How it differs from other job widgets", wt(["", "This widget", "Widget builders", "Hiring-system embeds"], [
             ["Where the jobs come from", f"Our index of {n:,} open tech jobs, or your own board", "You type each job in by hand", "Your own board only"],
             ["Jobs from other companies, by skill or city", "Yes", "No", "No"],
             ["Stays up to date by itself", "Yes", "Only when you edit it", "Yes"],
             ["Account", "None", "Required", "You are already a customer"],
             ["Price", "Free", "A free tier with limits, then a monthly fee", "Part of the system’s price"],
             ["Branding", "A small link back", "Removed on paid plans", "The system’s own look"]])
             + '<p class="note">A fair summary of the three kinds of job widget as their own pages describe them in November 2026; individual products differ.</p>')
         + section("Will Google index the jobs in the widget?",
                   '<p>Treat the widget as something for your visitors, not for Google. The list is drawn by a script after your page loads, and Google credits a job to the page that carries the full posting and its JobPosting markup: '
                   'the employer’s own page, or the job’s page on this site. If you want your own vacancies to appear in Google’s job search, mark up each vacancy page on your site. '
                   f'The free <a href="{P}/tools/jobposting-schema/">JobPosting schema generator</a> writes that code for you.</p>')
         + section("Limits and fair use", '<p>The widget reads one small file that changes once an hour, so there is no rate limit to run into. A list for a skill, city or category holds the 30 newest roles; '
                   'a company’s list holds all of its open roles. Keep the link back inside the snippet.</p>')
         + section("Questions", w_faq_html)
         + section("More for developers and writers", '<div class="feats">'
                   f'<a class="feat" href="{P}/api/"><h3>Free jobs API</h3><p>JSON feeds for every skill, category, city and company. No key, no sign-up.</p></a>'
                   f'<a class="feat" href="{P}/trends/"><h3>Hiring data to quote</h3><p>Live numbers on skills, salaries and companies, with ready-made citations and CSV downloads.</p></a>'
                   f'<a class="feat" href="{P}/feed.xml"><h3>RSS feeds</h3><p>Plug any category or skill feed into Slack, Discord or a reader.</p></a></div>')
         + '<script type="application/json" id="wb-data">' + json.dumps(wb_data, ensure_ascii=False).replace("</", "<\\/") + f'</script><script src="{P}/widget.js?v={V}" defer></script><script src="{P}/widgets.js?v={V}" defer></script>',
         head=w_ld)
    # One page per site builder: the same widget, with the steps and the catches of that platform
    snip_script = e(f'<div data-hrn-jobs="latest" data-limit="6"><a href="{FULL}/jobs/">Tech jobs on {SITE}</a></div>\n<script src="{FULL}/widget.js" async></script>')
    snip_iframe = e(f'<iframe src="{FULL}/embed/?jobs=latest&limit=6" title="Tech jobs" loading="lazy" style="width:100%;max-width:720px;height:470px;border:0"></iframe>\n<p><a href="{FULL}/jobs/">Tech jobs on {SITE}</a></p>')
    PLATFORMS = [
        ("wordpress", "WordPress", "script",
         ["Open the page or post in the editor and press the plus sign where the jobs should appear.", "Choose the <b>Custom HTML</b> block and paste the code below.",
          "Press Preview to see the list, then Update or Publish.", "For a sidebar or footer, go to Appearance → Widgets and add a <b>Custom HTML</b> widget with the same code."],
         "No plugin is needed. On WordPress.com plans that remove scripts, and for users who are not allowed to post unfiltered HTML, use the iframe version further down.",
         [("Do I need a plugin to show jobs on WordPress?", "No. The widget is two lines of HTML that go into a Custom HTML block or widget. There is nothing to install or update."),
          ("The block shows only a link. What went wrong?", "WordPress removed the script. That happens on WordPress.com plans without custom code and for user roles that cannot post unfiltered HTML. Use the iframe version instead.")]),
        ("webflow", "Webflow", "script",
         ["In the Designer open the Add panel and drag a <b>Code Embed</b> element to where the jobs should appear.", "Paste the code below and save the embed.",
          "Publish the site. Scripts do not run inside the Designer, so the canvas shows only the link."],
         "Code Embed is part of Webflow’s paid plans. The widget draws inside its own container, so your Webflow classes do not affect it.",
         [("Why does the Webflow Designer show only a link?", "The Designer does not run scripts in embeds. Publish the site and open the live page: the list appears there."),
          ("Can I style the widget with Webflow classes?", "No, and they cannot break it either: the widget is drawn in its own container. Change its look with the accent, theme and layout options in the builder.")]),
        ("wix", "Wix", "iframe",
         ["In the editor press Add Elements, then Embed Code, then <b>Embed HTML</b>.", "Choose “Code”, paste the code below and press Update.",
          "Drag the box to the size you want. Wix shows embedded code inside a frame, so set the height to fit the rows."],
         "Wix places all embedded code in a frame of a fixed size. If the list is cut off, make the box taller or ask for fewer rows in the builder.",
         [("Why is the job list cut off on my Wix page?", "Wix gives embedded code a fixed box. Make the box taller in the editor, or choose fewer rows in the builder."),
          ("Does the widget work on a free Wix site?", "Yes. Embed HTML is available in the Wix editor without an upgrade.")]),
        ("squarespace", "Squarespace", "script",
         ["Edit the page, press the plus sign where the jobs should appear and add a <b>Code</b> block.", "Paste the code below, leave the type as HTML and switch “Display Source” off.",
          "Save. The list shows on the live page; the editor may show a placeholder."],
         "Scripts in Code blocks are a paid feature on Squarespace. On a plan without it, add an Embed block and use the iframe version further down.",
         [("My Squarespace plan does not allow scripts. Can I still show jobs?", "Yes. Add an Embed block and paste the iframe version of the widget. It shows the same list without running a script on your page."),
          ("Why do I see a placeholder in the Squarespace editor?", "Squarespace does not run scripts while you edit. Save and open the page as a visitor would.")]),
        ("shopify", "Shopify", "script",
         ["Open Online Store → Themes and press Customize on your theme.", "Go to the page where the jobs should appear and add a <b>Custom Liquid</b> section or block.",
          "Paste the code below and save."],
         "A careers page on a store works well with the careers layout: pick your own board in the builder to show only your company’s roles.",
         [("Where do I paste the widget in Shopify?", "In the theme editor, in a Custom Liquid section or block. Themes without it accept the same code in a Custom HTML section."),
          ("Can I show only my store’s own vacancies?", "Yes, if you post them through Greenhouse, Lever or Ashby: pick that system in the builder and type the name of your board.")]),
        ("framer", "Framer", "script",
         ["Open Insert, find <b>Embed</b> and place it on the canvas.", "Set its type to HTML and paste the code below.", "Resize the embed to fit the rows and publish."],
         "The preview in Framer runs the widget, so you see the list before you publish.",
         [("Does the widget follow my Framer site’s dark mode?", "With the theme set to “match the visitor” it follows the visitor’s system setting. To follow your site instead, set the theme to light or dark in the builder."),
          ("Can I use it in a Framer CMS page?", "Yes. An Embed with the same code works on any page, including pages built from the CMS.")]),
        ("notion", "Notion", "iframe",
         ["In the builder choose “iframe” as the embed type.", "Copy only the address inside <code>src=\"…\"</code> from the code.", "In Notion type <b>/embed</b>, paste the address and press Embed link. Drag the corner to resize."],
         "Notion removes scripts, so it takes the address of the widget’s own page, not the snippet.",
         [("Why does pasting the snippet into Notion not work?", "Notion does not run scripts or raw HTML. Use an Embed block with the address from the iframe version of the widget."),
          ("Does the list in Notion stay up to date?", "Yes. The embed loads the widget’s page each time the Notion page opens, and that page is rebuilt every hour.")]),
        ("ghost", "Ghost", "script",
         ["In the editor press the plus sign on an empty line and choose the <b>HTML</b> card.", "Paste the code below.", "Preview the post, then publish or update."],
         "The HTML card also works in newsletters sent from Ghost, but email clients do not run scripts: readers of the email see the link, readers on the site see the list.",
         [("Will the widget show in emails sent from Ghost?", "No. Email clients do not run scripts, so the email shows the plain link inside the snippet. The list appears on the web version of the post."),
          ("Can I put it in the sidebar of my Ghost theme?", "Yes. Paste the same two lines into the theme file where the sidebar is, or use Code injection for a site-wide spot.")]),
    ]
    for pslug, pname, best, steps_p, catch, faq_p in PLATFORMS:
        first, second = (("Script version", snip_script), ("iframe version", snip_iframe)) if best == "script" else (("iframe version", snip_iframe), ("Script version", snip_script))
        p_faq = faq_p + [("Is the job widget free on " + pname + "?", "Yes. There is no plan and no account. The snippet keeps a small link back to this site.")]
        p_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in p_faq]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page(f"widgets/{pslug}/", f"Job Widget for {pname}: free, no account | {SITE}",
             f"How to add a free job widget to a {pname} site: where to paste the code, what to watch for, and a live preview. Tech jobs by skill or city, or your own company’s jobs.",
             crumbs(("Job widget", "widgets/"), (pname, "")) + f"<h1>Job widget for {e(pname)}</h1>"
             f'<p class="lead">A self-updating list of open jobs on your {e(pname)} site, in a few clicks. It is the same free widget as on the <a href="{P}/widgets/">job widget page</a>; this page has the steps for {e(pname)}.</p>'
             + section(f"Add it to {pname}", '<ol class="steps">' + "".join(f"<li>{x}</li>" for x in steps_p) + f'</ol><p class="note">{catch}</p>')
             + section("The code", f'<span class="flabel">{first[0]} (use this one on {e(pname)})</span><textarea id="pw-a" rows="3" readonly aria-label="{first[0]}">{first[1]}</textarea>'
                       '<p><button class="btn sm" type="button" data-copy="pw-a">Copy the code</button></p>'
                       f'<span class="flabel">{second[0]}</span><textarea id="pw-b" rows="3" readonly aria-label="{second[0]}">{second[1]}</textarea>'
                       '<p><button class="btn sm ghost" type="button" data-copy="pw-b" style="margin-top:0">Copy the code</button></p>'
                       f'<p>This snippet shows the latest tech jobs. To show one skill, a city, one company or your own board, with your colours and layout, <a href="{P}/widgets/">build your own on the job widget page</a>.</p>')
             + section("What your visitors will see", f'<div data-hrn-jobs="latest" data-limit="5" data-hrn-base="{P}"><a href="{P}/jobs/">Tech jobs on {e(SITE)}</a></div>')
             + section("Questions", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in p_faq) + "</dl>")
             + section("Other platforms", '<p class="rel" style="margin:0">' + "".join(f'<a href="{P}/widgets/{x[0]}/">{e(x[1])}</a>' for x in PLATFORMS if x[0] != pslug) + f'<a href="{P}/widgets/">All options</a></p>')
             + f'<script src="{P}/widget.js?v={V}" defer></script>'
             "<script>document.addEventListener('click',function(ev){var b=ev.target.closest('[data-copy]');if(!b)return;var t=document.getElementById(b.getAttribute('data-copy'));"
             "var done=function(){var x=b.textContent;b.textContent='Copied';setTimeout(function(){b.textContent=x},1500)};"
             "if(navigator.clipboard)navigator.clipboard.writeText(t.value).then(done,function(){t.select()});else{t.select();done()}});</script>",
             head=p_ld)

    sample = json.dumps({"name": "Rust jobs", "url": f"{FULL}/skills/rust/", "site": SITE, "updated": TODAY, "total": 1100,
                         "jobs": [{"title": "Senior Rust Engineer", "company": "Example Co", "location": "Remote", "remote": True, "salary": "$180K - $240K", "posted": TODAY, "url": f"{FULL}/job/…/"}]}, indent=2)
    js_example = f'const feed = await fetch("{FULL}/api/v1/skills/python.json").then(r => r.json());\nconsole.log(feed.total, feed.jobs[0].title);'
    api_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Dataset", "name": f"{SITE}: open tech jobs",
               "description": f"Open tech job postings collected every hour from the official careers pages of {m} companies: title, employer, location, remote flag, advertised salary and posting date, with aggregate counts and salary medians by skill, category, location and company.",
               "url": f"{FULL}/api/", "dateModified": TODAY, "isAccessibleForFree": True, "creator": {"@type": "Organization", "name": SITE, "url": FULL + "/"}, "license": f"{FULL}/terms/",
               "keywords": ["tech jobs", "job postings", "salaries", "remote jobs", "hiring trends"],
               "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{FULL}/api/v1/index.json"}]
                               + [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{FULL}/data/open/{x}.csv"} for x in ("skills", "companies", "categories", "locations")]}) + "</script>")
    page("api/", f"Free Tech Jobs API — JSON feeds, no key | {SITE}",
         "A free JSON API of open tech jobs by skill, category, location and company. No API key, CORS enabled, updated hourly.",
         crumbs(("API", "")) + '<h1>Free tech jobs API</h1>' + f'<p class="plain"><b>In plain words:</b> this page is for programmers. An API is a way for a program to read our list of jobs by itself. To show jobs on a website without programming, use the <a href="{P}/widgets/">job widget</a>. To look for a job, use the <a href="{P}/jobs/">search</a>.</p>' + '<p class="lead">Collecting jobs yourself means hundreds of career pages and a scraper that breaks every week. Here is the finished result as plain JSON you can fetch from anywhere: a bot, a newsletter script, a side project. No key, no sign-up, CORS enabled, refreshed every hour.</p>'
         + section("Endpoints", ttable(["Feed", "Address"], [
             trow(["Everything available", f"<code>{FULL}/api/v1/index.json</code>"]), trow(["Latest jobs", f"<code>{FULL}/api/v1/latest.json</code>"]),
             trow(["Remote jobs", f"<code>{FULL}/api/v1/remote.json</code>"]), trow(["By skill", f"<code>{FULL}/api/v1/skills/rust.json</code>"]),
             trow(["By category", f"<code>{FULL}/api/v1/categories/engineering.json</code>"]), trow(["By location", f"<code>{FULL}/api/v1/locations/europe.json</code>"]),
             trow(["By company", f"<code>{FULL}/api/v1/companies/stripe.json</code>"])]))
         + section("Response", f'<pre><code>{e(sample)}</code></pre><p class="note">Skill, category, location, latest and remote feeds hold the 30 newest matching jobs and the total count; a company feed holds all of that company’s open jobs. The slugs are the same as in the page addresses.</p>')
         + section("Example", f"<pre><code>{e(js_example)}</code></pre>")
         + section("Fair use", '<p>Free for personal and commercial projects. Two requests: link back to the job page or to this site wherever you show the data, and fetch each feed no more than once an hour (it changes once an hour).</p>'
                   f'<p>Also available: <a href="{P}/feed.xml">RSS feeds</a>, CSV downloads on the <a href="{P}/trends/">trends page</a>, and a ready-made <a href="{P}/widgets/">widget</a>.</p>'), head=api_ld)

    # Plus (paid plan for job seekers; one-time payments, no subscription). The page sells the problem first, shows each
    # feature as a small screen (marked as an example), and does the price arithmetic for the visitor.
    plus = CFG.get("plus", {"live": False, "plans": []})
    cta = ('<a class="btn primary lg" href="#pay">Get Plus</a>' if plus.get("live") else '<button class="btn primary lg" type="button" disabled>Available soon</button>')
    def per_day(pl):
        m_ = re.search(r"\d+", pl["price"]); k_ = re.search(r"\d+", pl["name"])
        if not m_ or not k_: return ""
        days_ = {1: 30, 3: 91, 12: 365}.get(int(k_.group(0)), 30 * int(k_.group(0)))
        return f"{round(100 * int(m_.group(0)) / days_)} cents a day"
    plans = "".join(
        f'<div class="plan{" best" if pl.get("best") else ""}">' + (f'<span class="pill acc">{e(pl["note"])}</span>' if pl.get("note") else '<span class="pill ghost">–</span>')
        + f'<p class="pname">{e(pl["name"])}</p><p class="price">{e(pl["price"])}</p><p class="note">{e(pl["per"])} · <b>{per_day(pl)}</b></p>{cta}</div>' for pl in plus["plans"])
    ex_ = '<span class="ex">example</span>'
    pcards = [
        ("Resume review", "A read the way a recruiter reads: twenty seconds, top to bottom. You get a score, what the reader saw, what they could not find, and the lines to rewrite.",
         ex_ + '<span class="big">6<small>out of 10</small></span><span class="mt"><i style="width:60%"></i></span><span class="ln">First result appears on <b>page two</b> · no numbers in 7 of 9 bullets</span>'),
        ("Your resume, reworded for one posting", "The same resume sent everywhere rarely fits. Your own bullet points are reworded against the posting you picked, using only what is already in your resume. You approve each line.",
         ex_ + '<span class="ln">Before: worked on the product catalogue</span><span class="ln"><b>After: cut catalogue load time by 40% by moving rendering to the server</b></span><span class="ln">Matches “performance” in the posting</span>'),
        ("Cover letter for the posting", "A draft built from your resume and the posting: a full letter for email, or four lines for a message to the recruiter. Ready to edit, so a letter stops costing an evening.",
         '<span class="ln"><b>Dear hiring team,</b></span><span class="sk" style="width:94%"></span><span class="sk h" style="width:58%"></span><span class="sk" style="width:88%"></span><span class="sk" style="width:40%"></span>'),
        ("An email when a job fits", f"Nobody can check {m} career pages a day. Answer the five questions once; when an employer posts a job that fits, the email arrives the same day.",
         ex_ + '<span class="ln"><b>3 new jobs fit your answers</b></span><span class="rw"><span>Remote</span><span class="mt"><i style="width:100%"></i></span><b>3 of 3</b></span>'
               '<span class="rw"><span>Pay</span><span class="mt"><i style="width:66%"></i></span><b>2 of 3</b></span><span class="ln">Sent 08:10, the morning they were posted</span>'),
        ("Interview prep for one job", "Likely questions taken from the posting’s own requirements, each with the points from your resume that answer it.",
         ex_ + '<span class="ln"><b>1.</b> Tell us about a migration you led</span><span class="ln"><b>2.</b> How do you measure page speed?</span><span class="ln"><b>3.</b> A release you had to roll back</span><span class="ln">From 6 requirements in the posting</span>'),
        ("Pay check and what to say", "Where an offer sits among the pay ranges employers advertise for the same work, and a short script for asking for more when it sits low.",
         ex_ + '<span class="ln">Offer <b>$118K</b> · median for this work <b>$140K</b></span><span class="mt"><i style="left:22%;width:46%"></i><u style="left:30%"></u></span><span class="ln"><b>16% below the median</b>: worth asking</span>'),
        ("LinkedIn profile review", "What a recruiter sees in search results: the headline and the first three lines. You get the fixes, with the fragment each one refers to.",
         ex_ + '<span class="ln">Headline: <b>“Open to work”</b></span><span class="ln">Says no role and no field</span><span class="sk" style="width:86%"></span><span class="ln">3 fixes · 1 buzzword</span>'),
        ("Your jobs on every device", "Saved jobs, application statuses and notes follow you from the laptop to the phone.",
         ex_ + '<span class="rw"><span>Saved</span><span class="mt"><i style="width:100%"></i></span><b>9</b></span><span class="rw"><span>Applied</span><span class="mt"><i style="width:66%"></i></span><b>6</b></span>'
               '<span class="rw"><span>Interview</span><span class="mt"><i style="width:22%"></i></span><b>2</b></span><span class="ln">Laptop and phone show the same list</span>'),
    ]
    pcard_html = '<div class="tgrid">' + "".join(f'<div class="tcard"><span class="tprev" aria-hidden="true">{scr}</span><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span></span></div>' for t_, d_, scr in pcards) + "</div>"
    free_now = "".join(f'<li><a href="{P}/{u}">{e(t_)}</a><span>free</span></li>' for u, t_ in (
        ("jobs/", "Every job and the link to apply, the moment we have it"), ("for-you/", "Matching by five answers, with the reason next to each job"), ("categories/", f"Browsing by {len(fam_rows)} fields and {len(by_role)} kinds of work"),
        ("salaries/", "Salary data from the pay ranges employers publish"), ("resume/", "Resume builder with Word and PDF"), ("tools/", "Every tool: resume match, pay calculators, letters"), ("my-jobs/", "Application tracker with reminders")))
    rows_cmp = [("Every job and the link to apply", "Yes", "Yes"), ("Search, filters, categories, salary data", "Yes", "Yes"), ("Matching by five answers", "Yes", "Yes, and by email"),
                ("Save jobs and track applications", "On this device", "On every device"), ("New jobs that fit", "On the site, when you visit", "By email, the day they are posted"),
                ("Resume", "Builder and match check", "Reviewed, and reworded for each posting"), ("Cover letters", "Fill-in template", "Draft from your resume and the posting"),
                ("Interview prep", "No", "Questions from the posting, with your answers"), ("Pay", "Salary checker", "Offer check with a script for negotiating"), ("LinkedIn profile", "No", "Reviewed, with fixes")]
    cmp_html = "".join(f"<tr><td>{e(a_)}</td><td>{e(b_)}</td><td><strong>{e(c_)}</strong></td></tr>" for a_, b_, c_ in rows_cmp)
    low_plan = min(plus["plans"], key=lambda pl: int(re.search(r"\d+", per_day(pl) or "999").group(0))) if plus["plans"] else None
    tick = lambda items: '<ul class="ticks">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
    tiers = ('<div class="tiers">'
             '<div class="tier"><p class="tn">Free</p><p class="tp">$0</p><p class="td">Everything you need to find a job and apply. No account, no card.</p>'
             f'<a class="btn ghost" href="{P}/for-you/">Start with five questions</a>'
             + tick(["Every job and the link to apply", "Search, 23 fields of work, salary data", "Matching by five answers, with reasons", "Resume builder: 5 templates, PDF and Word", "Resume review and resume match by rules",
                     "Letter templates: cover, thank-you, resignation", "Application tracker on this device"]) + "</div>"
             '<div class="tier best"><p class="tn">Plus</p>'
             + (f'<p class="tp">{e(low_plan["price"])}<small> for {e(low_plan["name"])} · {per_day(low_plan)}</small></p>' if low_plan else '<p class="tp">Plus</p>')
             + '<p class="td">Everything in Free, plus an AI writer for your resume and letters, and an email when a job fits. One payment, nothing renews.</p>' + cta
             + tick(["AI resume writer: bullet points and summary from your notes", "Resume reworded for each posting, with the keywords it misses", "AI resume review: score, weak points, rewrites",
                     "AI cover letters and resignation letters", "Interview questions for the posting, with your answers", "An email the day a job fits your answers", "Pay check with a script for negotiating",
                     "LinkedIn profile review", "Your jobs and resumes on every device"]) + "</div>"
             '<div class="tier"><p class="tn">Employers</p><p class="tp">Free<small> to post a job</small></p><p class="td">A standard listing costs nothing. A featured one stays at the top of its list.</p>'
             f'<a class="btn ghost" href="{P}/post-a-job/">Post a job</a>'
             + tick(["A standard listing for 30 days", "Featured job from $99", "Pinned job, company spotlight, sponsor of a category", "Paid in crypto, switched on at once", "No calls, no sales manager"]) + "</div></div>")
    yes, no = '<td class="y">Yes</td>', '<td class="n">—</td>'
    cell = lambda v: yes if v is True else no if v is False else f"<td>{e(v)}</td>"
    grid_rows = [("Jobs", None, None), ("Every job and the link to apply", True, True), ("Search, categories, salary data, rankings", True, True), ("Matching by five answers", True, True), ("An email when a job fits", False, True),
                 ("Resume", None, None), ("Resume builder, 5 templates", True, True), ("PDF and Word downloads", "Unlimited", "Unlimited"), ("Resume review", "By rules", "By AI, with rewrites"),
                 ("Match against a posting", "Keywords found and missing", "Bullets reworded for the posting"), ("AI writer for bullet points and summary", False, True),
                 ("Letters", None, None), ("Cover letter", "Fill-in template", "Draft from your resume and the posting"), ("Thank-you, raise and resignation letters", "Templates", "AI drafts"),
                 ("Interview and pay", None, None), ("Interview questions for one posting", False, True), ("Salary checker and offer check", True, True), ("Script for negotiating an offer", False, True),
                 ("Tracking", None, None), ("Application tracker", "On this device", "On every device"), ("LinkedIn profile review", "By rules", "By AI")]
    grid_html = "".join(f'<tr class="grp"><th colspan="3">{e(a_)}</th></tr>' if b_ is None else f"<tr><td>{e(a_)}</td>{cell(b_)}{cell(c_)}</tr>" for a_, b_, c_ in grid_rows)
    soon = "" if plus.get("live") else '<div class="banner">Plus is not on sale yet. This page shows what it will do and what it will cost. Everything in the “free” list works today.</div>'
    plus_qa = [("Is this a subscription?", "No. You pay once for the period you choose. When it ends, nothing is charged and there is nothing to cancel. There is no card on file to charge."),
               ("Do I have to pay to see or apply for jobs?", "No. Every job is public the moment we have it and free to apply to, on the employer’s own page. Plus adds help with applying; it does not unlock listings."),
               ("How do I pay?", "With crypto (USDT, BTC, ETH and other coins) on a checkout page. Plus turns on in your account once the network confirms the payment."),
               ("Is the resume help written by AI?", "Yes, the review, the rewording, the letters and the interview questions are. It works only from your own resume and the posting, adds no experience you do not have, and you approve every line before you use it."),
               ("How much can I use it?", "The AI tools have a monthly allowance, shown before you pay, sized for an active job search: dozens of applications a month."),
               ("When does it launch?", "When payments are connected. Until then the free site works as it does today.")]
    plus_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in plus_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("plus/", f"Plus: resume review, letters and job alerts, one payment | {SITE}",
         "Plus reviews your resume, rewords it for each posting, drafts the cover letter, prepares you for the interview and emails you when a job fits. One payment from 11 cents a day, nothing renews. Every job stays free.",
         crumbs(("Plus", "")) + '<h1>Applications go out and nothing comes back. Plus finds out why and <span class="hl">fixes it</span>, job by job</h1>'
         '<p class="lead">A resume gets one short first read, and nobody tells you why it was put aside: the result is on page two, the bullets list duties, the letter could be for any company. '
         f'Plus reads your resume the way a recruiter does, rewords it for each posting and tells you the day a job fits. One payment, from {min((per_day(pl) for pl in plus["plans"]), key=lambda x: int(x.split()[0])) if plus["plans"] else "a few cents a day"}. Nothing renews.</p>{soon}'
         + tiers
         + section("What Plus adds", pcard_html)
         + section("What it costs", f'<div class="plans">{plans}</div><p class="note">You pay once, in crypto, on a checkout page, and Plus switches on when the payment is confirmed. '
                   'There is no automatic renewal, no card on file and nothing to cancel: when the period ends, Plus simply ends.</p>')
         + section("What stays free, for everyone", f'<div class="dir free"><div class="dirb"><ul>{free_now}</ul></div></div>')
         + section("Free and Plus, line by line", f'<div class="tablewrap"><table class="grid"><tr><th></th><th>Free</th><th>Plus</th></tr>{grid_html}</table></div>')
         + section("Questions", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in plus_qa) + "</dl>"), head=plus_ld)
    # Employers
    rows = "".join(f"<tr><td><strong>{e(p['name'])}</strong></td><td>{e(p['price'])}</td><td>{e(p['what'])}{' <span class=\"note\">Not available yet.</span>' if p.get('soon') else ''}</td></tr>" for p in CFG["prices"])
    app_url = f"{P}/account/" if CFG["api_url"] else ""
    steps = ('<ol class="steps"><li><b>Create an employer account.</b> It takes an email and a password.</li>'
             "<li><b>Paste the job.</b> Title, link to apply, location, description. We open the link to check the job is really there.</li>"
             "<li><b>A standard listing is free.</b> It goes live at the next hourly update. If you want it higher, pick a paid placement and pay at the crypto checkout (USDT, BTC, ETH and other coins).</li>"
             "<li><b>Paid placements switch on by themselves</b> once the network confirms the payment. You can close or renew a job from your account at any time.</li></ol>")
    if app_url:
        pay = (f'<section class="sec"><div class="sec-head"><h2>How to post a job</h2><a href="{e(app_url)}">Open the employer account</a></div>{steps}'
               f'<p><a class="btn primary lg" href="{e(app_url)}">Post a job now</a></p></section>')
    else:
        pay = (f'<section class="sec"><div class="sec-head"><h2>How posting a job will work</h2></div>{steps}'
               '<div class="banner">Self-serve posting is being finished and is not open yet. Nothing can be bought today.'
               + (f" Questions in the meantime: {contact}." if contact else "") + "</div></section>")
    pains = [("Lists are sorted by date", f"{WEEKNEW:,} roles were posted here in the last 7 days, so a job that is not pinned leaves the first page within days."),
             ("Roles without pay get filtered out", f"{100 - SALPCT}% of postings here show no salary. Anyone who filters or sorts by pay never sees them. Adding a range costs nothing."),
             ("Company spotlight", "Your logo and your open roles on the home page and at the top of the companies list.")]
    pain_html = '<div class="feats">' + "".join(f'<div class="feat"><h2>{e(a)}</h2><p>{e(b)}</p></div>' for a, b in pains) + "</div>"
    page("post-a-job/", f"Post a Tech Job — free listing, featured from $99 | {SITE}" if app_url else f"Post a Tech Job — plans and prices for employers | {SITE}",
         ("Post a tech job for free, or feature it from $99 so it stays at the top of the list. Self-serve, paid in crypto at checkout." if app_url else
          "Plans and prices for employers: free standard listings, featured jobs from $99, company spotlight and page sponsorship. Self-serve posting is being finished and is not open yet."),
         crumbs(("For employers", "")) + "<h1>Post a tech job that doesn’t get buried</h1>"
         f'<p class="lead">There are {n:,} open roles from {m:,} companies here, sorted by date. A standard listing is free. '
         'A featured one stays at the top instead of sliding down as new roles arrive.</p>'
         f'{pain_html}' + section("Plans and prices for employers", f'<div class="tablewrap"><table><tr><th>Plan</th><th>Price</th><th>What you get</th></tr>{rows}</table></div>')
         + section("How a company spotlight looks", '<div class="spot"><a href="#">' + ava("Your company") + '<span><b>Your company</b><span class="s">42 open roles · featured</span></span></a></div>'
                   '<p class="note">Shown on the home page and at the top of the companies list.</p>')
         + section("How a featured listing looks", '<ul class="jobs">' + card({"featured": True, "active": True, "remote": True, "salary": "$140K - $180K", "level": "Senior",
                   "tags": ["Python", "AWS"], "location": "Remote, Europe", "company": "Your company", "slug": "", "title": "Senior Backend Engineer", "posted": TODAY})
                   .replace(f'href="{P}/job//"', 'href="#"') + "</ul>") + pay
         + f''
         '<section class="sec"><div class="sec-head"><h2>Questions</h2></div>'
         "<h3>How do I pay?</h3><p>In crypto, on a checkout page: USDT, BTC, ETH and other coins. The placement switches on after the payment is confirmed. We do not take cards or bank transfers yet.</p>"
         "<h3>No careers page of your own?</h3><p>Use your company page here as one. Link your site's Careers button to it, or embed the list with one line of code: "
         f'<a href="{P}/widgets/">badge and widget</a>.</p>'
         "<h3>What happens when the job closes?</h3><p>It moves to the archive and is marked as closed. The page stays online.</p>"
         "<h3>Can I get a refund?</h3><p>A placement switches on the moment the payment is confirmed, so there is nothing to refund before publication. If a paid placement did not run as described, write to us and it will be extended or refunded.</p></section>")
    # Employer account: only exists once the API is deployed, so the site never shows a form that goes nowhere
    if CFG["api_url"]:
        acc_data = {"site": FULL, "skills": wb_data["skills"], "categories": wb_data["categories"], "companies": [c for c, _ in comp_items if OPEN[c]],
                    "what": {p["name"]: p["what"] for p in CFG["prices"]}}
        page("account/", f"Employer Account — post and promote tech jobs | {SITE}",
             "Post a tech job for free or put it in front of candidates. Pay in crypto at checkout: the placement switches on by itself once the payment is confirmed.",
             crumbs(("For employers", "post-a-job/"), ("Account", "")) + "<h1>Employer account</h1>"
             '<p class="lead">Post a job, promote it, or put your company on the home page. What you buy here switches on by itself; there is nobody to wait for.</p>'
             f'<div id="acc" data-api="{e(CFG["api_url"])}"><noscript><div class="banner">The account needs JavaScript.</div></noscript></div>'
             '<script type="application/json" id="acc-data">' + json.dumps(acc_data, ensure_ascii=False).replace("</", "<\\/") + f'</script><script src="{P}/account.js?v={V}" defer></script>',
             head='<meta name="robots" content="noindex">', sitemap=False)
    # Media kit: what the site is, live numbers, brand assets and placements, for press and advertisers
    wordmark = lambda ink, dot: (f'<svg xmlns="http://www.w3.org/2000/svg" width="420" height="80" viewBox="0 0 420 80" role="img" aria-label="{e(SITE)}">'
                                 f'<circle cx="22" cy="40" r="10" fill="{dot}"/><text x="46" y="52" fill="{ink}" font-family="Bricolage Grotesque, Inter, Helvetica, Arial, sans-serif" '
                                 f'font-size="38" font-weight="800" letter-spacing="-1">{e(SITE)}</text></svg>')
    write("brand/logo-mark.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 32 32" role="img" aria-label="{e(SITE)}">{MARK}</svg>', sitemap=False)
    write("brand/logo-wordmark.svg", wordmark("#0e0e0c", "#3ecf5f"), sitemap=False)
    write("brand/logo-wordmark-dark.svg", wordmark("#f3f2ec", "#3ecf5f"), sitemap=False)
    swatch = lambda hexv, name, ink="#0e0e0c": f'<div class="swatch" style="background:{hexv};color:{ink}"><b>{name}</b><span>{hexv}</span></div>'
    short_bp = f"{SITE} is an hourly-updated index of open tech jobs, collected from employers' own careers pages."
    long_bp = (f"{SITE} lists {n:,} open tech jobs from {m} companies and re-checks every one of them against the employer's careers page every hour. Each listing links to the original posting, "
               "closed roles move to a public archive, and salary and hiring data from the postings is free to use with a link back.")
    page("media-kit/", f"Media Kit — brand assets, live numbers, advertising | {SITE}",
         f"{SITE} media kit: what the site is, live numbers, logos and colours to download, ready-to-paste descriptions, and placements for employers and sponsors.",
         crumbs(("Media kit", "")) + f"<h1>{e(SITE)} media kit</h1>"
         '<p class="plain"><b>In plain words:</b> logos, facts and prices for journalists and for companies that want to write about this site or advertise on it. Job seekers do not need this page.</p>'
         '<p class="lead">For journalists, partners and advertisers: what the site is, today’s numbers, logos to download, and what can be bought.</p>'
         f'<div class="statrow"><div class="stat"><b>{n:,}</b><span>open roles today</span></div><div class="stat"><b>{m}</b><span>companies</span></div>'
         f'<div class="stat"><b>{len(remote):,}</b><span>remote roles</span></div><div class="stat"><b>{WEEKNEW:,}</b><span>posted in the last 7 days</span></div></div>'
         f'<p class="note">Counted on {fdate(TODAY)}; these numbers are rebuilt every day. Audience figures are not published yet: measurement starts when the site moves to its own domain, and we do not publish estimates.</p>'
         + section(f"What {SITE} is", f'<p>{e(short_bp)}</p><p>{e(long_bp)}</p><p class="note">Both paragraphs may be quoted as they are. How the data is collected: <a href="{P}/methodology/">methodology</a>.</p>')
         + section("Logos to download", '<div class="brandrow">'
                   f'<a class="brandtile" href="{P}/brand/logo-wordmark.svg" download><img src="{P}/brand/logo-wordmark.svg" alt="{e(SITE)} wordmark on a light background" width="210" height="40"><span>Wordmark, light · SVG</span></a>'
                   f'<a class="brandtile dark" href="{P}/brand/logo-wordmark-dark.svg" download><img src="{P}/brand/logo-wordmark-dark.svg" alt="{e(SITE)} wordmark on a dark background" width="210" height="40"><span>Wordmark, dark · SVG</span></a>'
                   f'<a class="brandtile" href="{P}/brand/logo-mark.svg" download><img src="{P}/brand/logo-mark.svg" alt="{e(SITE)} mark" width="56" height="56"><span>Mark · SVG</span></a>'
                   f'<a class="brandtile" href="{P}/og.jpg" download><img src="{P}/og.jpg" alt="{e(SITE)} share image" width="210" height="110" loading="lazy"><span>Share image · JPG 1200×630</span></a></div>'
                   '<p class="note">Keep the mark and the name together, leave clear space around them, and do not recolour, stretch or redraw them. The wordmark is set in Bricolage Grotesque ExtraBold.</p>')
         + section("Colours and type", '<div class="swatches">' + swatch("#f6f5f0", "Paper") + swatch("#0e0e0c", "Ink", "#f3f2ec") + swatch("#b7eec3", "Marker green") + swatch("#1f9d55", "Line green", "#ffffff") + swatch("#3ecf5f", "Live green") + swatch("#e2dfd5", "Line") + "</div>"
                   '<div class="types"><div><span class="t1">Hiring Right Now</span><small>Headlines: Bricolage Grotesque, 700–800</small></div>'
                   '<div><span class="t2">Every role here comes from the company’s own careers page and is checked again every hour.</span><small>Text: Inter, 400–700</small></div>'
                   f'<div><span class="t3">{n:,} · $196K · {fdate(TODAY, False)}</span><small>Numbers: JetBrains Mono, 500–700</small></div></div>'
                   '<p class="note">All three are open-source typefaces.</p>')
         + section("Placements for employers and sponsors", f'<div class="tablewrap"><table><tr><th>Placement</th><th>Price</th><th>What it is</th></tr>{rows}</table></div>'
                   + ("<p>Every placement is bought and switched on in the employer account, paid in crypto at checkout." if CFG["api_url"] else
                      "<p>Placements will be bought and switched on in a self-serve employer account, paid in crypto at checkout. The account is not open yet, so nothing can be bought today.")
                   + f' Details and examples: <a href="{P}/post-a-job/">for employers</a>.</p>')
         + section("For journalists and researchers", f'<p>Numbers you can quote, each with its method and date: <a href="{P}/trends/">hiring trends</a>, <a href="{P}/salaries/">salaries from live postings</a>, '
                   f'<a href="{P}/insights/">rankings</a>, <a href="{P}/compare/">skill comparisons</a>. Raw data: <a href="{P}/api/">free JSON API</a> and CSV files. Every data page has a “Cite or link to this page” box.</p>'
                   + (f"<p>Questions: {contact}.</p>" if contact else "")),
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": FULL + "/", "logo": f"{FULL}/brand/logo-mark.svg",
               "description": short_bp}) + "</script>")
    # Hiring badges: small live pictures with a count of open roles, for a README, a footer or a post
    top_co = next((c for c, _ in comp_items if OPEN[c]), "")
    top_sk = skill_counts.most_common(1)[0][0] if skill_counts else ""
    badges = [("Tech jobs", "badge/jobs.svg", "jobs/"), ("Remote tech jobs", "badge/remote.svg", "remote/")]
    if top_sk: badges.append((f"{top_sk} jobs", f"badge/skills/{tslug(top_sk)}.svg", f"skills/{tslug(top_sk)}/"))
    if top_co: badges.append((f"{top_co} is hiring", f"badge/companies/{slugify(top_co)}.svg", f"companies/{slugify(top_co)}/"))
    badge_rows = "".join(
        f'<div class="feat"><p><img src="{P}/{img}" alt="{e(lbl)} badge" height="28" loading="lazy"></p>'
        f'<span class="flabel">HTML</span><textarea rows="2" readonly aria-label="HTML for the {e(lbl)} badge">{e(f"""<a href="{FULL}/{pg}"><img src="{FULL}/{img}" alt="{lbl} on {SITE}" height="28"></a>""")}</textarea>'
        f'<span class="flabel">Markdown</span><textarea rows="2" readonly aria-label="Markdown for the {e(lbl)} badge">{e(f"[![{lbl} on {SITE}]({FULL}/{img})]({FULL}/{pg})")}</textarea></div>' for lbl, img, pg in badges)
    hb_faq = [("What is a hiring badge?", "A small picture that says a company or a field is hiring, usually with a number. These badges are live: the number of open roles on each one is recounted every day."),
              ("Where can I use a hiring badge?", "In a GitHub README, a site footer, a blog post, an email signature or a community page: anywhere an image with a link works."),
              ("Is there a badge for my company?", f"If your company is among the {m} whose career pages we read, yes: its badge shows its current number of open roles. Pick it in the widget builder."),
              ("Is it free?", "Yes. Copy the code and use it; the badge links back to the list it counts.")]
    page("hiring-badge/", f"Free Hiring Badge with a Live Count of Open Roles | {SITE}",
         "Free hiring badges for a README, a footer or a post: a small live image with today’s number of open roles for tech jobs, a skill, a city or your company. Copy and paste.",
         crumbs(("Job widget", "widgets/"), ("Hiring badge", "")) + '<h1>Free hiring badge with a live count</h1>'
         '<p class="lead">A “we’re hiring” picture says nothing new after the first week. These badges carry today’s number of open roles and update themselves. '
         f'Copy one below, or <a href="{P}/widgets/">pick any skill, city, category or company in the builder</a>.</p>'
         f'<div class="feats">{badge_rows}</div>'
         + section("Questions", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in hb_faq) + "</dl>"),
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
             {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in hb_faq]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    org_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": FULL + "/",
              "logo": FULL + "/og.jpg", "description": "An hourly-updated index of open tech jobs collected from companies' official careers pages."}) + "</script>")
    page("about/", f"About {SITE} — who we are and how the site works", f"What {SITE} is, where its {n:,} tech job listings come from, how often they are checked and what the site does not do.",
         crumbs(("About", "")) + f"<h1>About {e(SITE)}</h1>"
         f'<p class="lead">{e(SITE)} is an index of open tech jobs. Every hour it reads the public hiring feeds of {N_FEEDS} tech companies, puts their {n:,} open roles into one searchable list and links each one back to the employer.</p>'
         f'<h2 class="h2s">Where {e(SITE)} gets its jobs</h2><p>From the companies\' own careers systems, not from other job boards. Every listing links to the original posting, and you apply there. '
         f'The full process is on the <a href="{P}/methodology/">methodology page</a>.</p>'
         f'<h2 class="h2s">How often {e(SITE)} is updated</h2><p>Every hour. The date of the last check is shown on every job page. Closed jobs are not deleted: they move to the <a href="{P}/archive/">archive</a> and are marked as closed.</p>'
         f'<h2 class="h2s">What {e(SITE)} costs job seekers</h2><p>Nothing. Searching, saving jobs, tracking applications, the resume builder and applying are free and need no account. A paid <a href="{P}/plus/">Plus</a> plan with extra tools is planned.</p>'
         f'<h2 class="h2s">Who runs {e(SITE)}</h2><p>An independent small team. We are not a recruitment agency and take no part in hiring decisions. Company names and logos belong to their owners and are shown only to identify the employer.</p>'
         f'<h2 class="h2s">How to contact {e(SITE)}</h2><p>' + (f"Write to us: {contact}." if contact else "Contact details will be published on this page shortly.")
         + f' For corrections or removal of a listing, see the <a href="{P}/terms/">terms</a>.</p>', head=org_ld)
    page("methodology/", f"How {SITE} Collects and Checks Tech Jobs — methodology", f"How {SITE} collects job listings, detects salary, skills, perks and remote status, calculates salary medians and handles closed jobs.",
         crumbs(("Methodology", "")) + f"<h1>How {e(SITE)} collects and checks jobs</h1>"
         f'<p class="plain"><b>In plain words:</b> where the jobs on this site come from, how we know a job is still open, and what each label and number means. Unfamiliar word? See the <a href="{P}/glossary/">glossary</a>.</p>'
         f'<p class="lead">Last updated {fdate(TODAY)}. This page explains where every number and label on the site comes from, so you can judge how far to trust it.</p>'
         f'<h2 class="h2s">Where do the job listings come from?</h2><p>From the public hiring feeds that companies publish through their applicant tracking systems. We read {N_FEEDS} company feeds every hour. We do not copy listings from other job boards and we do not accept anonymous submissions.</p>'
         '<h2 class="h2s">How do you know a job is still open?</h2><p>A job stays listed as open only while it is present in the employer\'s feed. When it disappears from the feed, it is marked as closed the same day and moved to the archive. '
         'If a company\'s feed cannot be read on a given day, its jobs are left unchanged rather than closed by mistake.</p>'
         '<h2 class="h2s">How are salary, skills, perks and remote status detected?</h2><p>Salary is shown only when the employer publishes a range. We read it from the pay field of the employer\'s hiring system or, failing that, from the posting text when a yearly range stands next to a word such as “salary” or “compensation”. '
         'Hourly and monthly figures are left out, and a salary written in an unusual way can be missed, so “not listed” on this site does not prove the employer hides it. Skills, perks such as visa sponsorship, seniority and employment type are read from the title and text of the posting by fixed rules, not guessed. '
         'A perk is listed only when the posting mentions it, and statements such as “we cannot sponsor visas” are excluded. Rules can miss or misread a posting, so confirm the details on the employer\'s page.</p>'
         '<h2 class="h2s">How are salary medians calculated?</h2><p>From open roles that publish a yearly range in US dollars. For each role we take the midpoint of the range; the median is the middle value of those midpoints. '
         'A median is shown for a list or a company only when at least 15 of its roles publish a yearly range. Rankings and comparisons that set one group against another need 30. '
         'The salary tools, which also show the spread, need 20. These are advertised ranges, not what people are actually paid, and they lean towards companies and regions that publish pay.</p>'
         '<h2 class="h2s">Why is a job listed once when it is open in several cities?</h2><p>Lists show a role once and add “+N more locations”. Each posting still has its own page. Counts on the site are counts of postings.</p>'
         f'<h2 class="h2s">How to report a mistake</h2><p>' + (f"Write to us: {contact}." if contact else "A contact address will be published on the About page shortly.") + "</p>")
    tools_md = "; ".join(f"[{nm}]({FULL}/{u})" for u, nm, _ in TOOLS)
    write("llms.txt", f"""# {SITE}

> {SITE} is an hourly-updated index of {n:,} open tech jobs at {m} companies, collected from the companies' official careers pages. Every listing links to the employer's own posting. Updated {TODAY}.

## Main sections
- [All tech jobs]({FULL}/jobs/): search with filters for level, location, salary, perks and remote
- [Remote tech jobs]({FULL}/remote/)
- [Jobs by skill]({FULL}/skills/)
- [Jobs by location]({FULL}/locations/)
- [Companies hiring]({FULL}/companies/)
- [Jobs by perk]({FULL}/perks/): visa sponsorship, relocation, equity and more
- [Crypto and web3 jobs]({FULL}/crypto/)

## Data
- [Tech salaries from live job postings]({FULL}/salaries/)
- [Tech hiring trends]({FULL}/trends/)
- [Insights and rankings]({FULL}/insights/)
- [Free JSON API]({FULL}/api/): {FULL}/api/v1/index.json
- [Monthly hiring reports]({FULL}/reports/): one dated page per month that stops changing when the month ends
- [Data status]({FULL}/status/): what the latest update did and how old the open listings are
- [Pay transparency ranking]({FULL}/insights/pay-transparency/) and [long-open roles]({FULL}/insights/long-open-roles/)
- [Methodology]({FULL}/methodology/): how listings are collected and how figures are calculated

- [Skill comparisons]({FULL}/compare/): two skills head to head on open roles, pay and remote share
- Open data as CSV: {FULL}/data/open/skills.csv, {FULL}/data/open/companies.csv, {FULL}/data/open/categories.csv, {FULL}/data/open/locations.csv
- API description for agents (OpenAPI): {FULL}/api/openapi.json

## Answering questions about jobs with this site
- "Who is hiring for <skill>?" Read {FULL}/skills/<skill>/ (page) or {FULL}/api/v1/skills/<skill>.json (data). Slugs are lowercase with hyphens: python, rust, machine-learning, react, cpp.
- "What jobs does <company> have open?" {FULL}/companies/<company>/ or {FULL}/api/v1/companies/<company>.json
- "Remote jobs" {FULL}/remote/ or {FULL}/api/v1/remote.json. "Newest jobs" {FULL}/new/ or {FULL}/api/v1/latest.json
- "Jobs in <place>" {FULL}/locations/<place>/ or {FULL}/api/v1/locations/<place>.json. "<category> jobs" {FULL}/jobs/<category>/
- "What does <skill> pay?" {FULL}/salaries/<skill>/ (median of advertised ranges, with the sample size)
- Every job has its own page at {FULL}/job/<slug>/ with the title, employer, location, salary if published, the date it was posted and the date it was last
  checked against the employer's careers page. A job that has closed says so at the top of its page.
- Please link to the job page when you mention a job: applications always go to the employer's own site from there, free of charge.
- The feeds list every address that exists: {FULL}/api/v1/index.json

## Tools
- [Free tools]({FULL}/tools/): {tools_md}
- [Jobs matched to your skills]({FULL}/for-you/)
- [Resume builder]({FULL}/resume/)
- [Job widget and live badges for other sites]({FULL}/widgets/)

## About
- [What is free and what we will never do]({FULL}/promise/) · [Job offer safety checklist]({FULL}/safety/)
- [About]({FULL}/about/) · [Privacy]({FULL}/privacy/) · [Terms]({FULL}/terms/)
""", sitemap=False)
    page("404.html", f"Page not found | {SITE}", "This page does not exist: the address may have changed or the job may have been renamed. Search open tech jobs by title, skill or company instead.",
         f'<h1>Page not found</h1><p class="lead">The address may have changed, or the job may have been renamed. Search for it here:</p>'
         f'<form class="searchbar wide" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Job title, skill or company" aria-label="Search jobs"><button class="btn primary">Search</button></form>'
         f'<p class="note">Or browse <a href="{P}/jobs/">all jobs</a>, <a href="{P}/companies/">companies</a> and <a href="{P}/skills/">skills</a>.</p>', sitemap=False)

    # Data + static files
    comp_list = sorted({j["company"] for j in active}); ci = {c: i for i, c in enumerate(comp_list)}
    tag_list = [t for t, _ in SKILLS]; ti = {t: i for i, t in enumerate(tag_list)}
    place_list = [slug for _, slug, _ in PLACES]; pi = {p_: i for i, p_ in enumerate(place_list)}
    cat_list = list(CAT); lvl_list = ["", "Intern", "Junior", "Senior", "Lead"]
    perk_list = [nm for nm, _, _ in PERKS]; et_list = ["", "Full-time", "Contract", "Part-time", "Internship"]
    def slug_ref(j):
        base = f"{slugify(j['title'])}-{slugify(j['company'])}"
        if j["slug"] == base: return 0
        tail = j["slug"][len(base) + 1:]
        return int(tail) if j["slug"].startswith(base + "-") and tail.isdigit() and tail[0] != "0" else j["slug"]
    rows_ = [[slug_ref(j), j["title"], ci[j["company"]], j["location"], int(j["remote"]) | 2 * int(j["featured"]) | 4 * int(bool(j.get("crypto"))) | 8 * int(bool(j.get("anywhere"))) | 16 * int(j["pool"]),
              cat_list.index(j["cat"]), lvl_list.index(j["level"]) if j["level"] in lvl_list else 0, [ti[t] for t in j["tags"] if t in ti], j["salary"],
              int((j["posted"] or j["first_seen"]).replace("-", "")[:8] or 0), int(j["usd"][1]) if j["usd"] else 0, [pi[p_] for p_ in j["places"]],
              [perk_list.index(x) for x in j.get("perks", []) if x in perk_list], et_list.index(j.get("etype", "")) if j.get("etype", "") in et_list else 0,
              j["t"] // 60 if j["t"] and NOW - j["t"] < WEEK else 0] for j in order(active)]      # last: exact posting time, minutes since 1970 (0: only the day is known, or older than a week)
    idx = {"c": comp_list, "t": tag_list, "p": place_list, "k": cat_list, "l": lvl_list, "x": perk_list, "e": et_list, "g": [int(slugify(c) in LOGOS) for c in comp_list]}
    write("data/index.json", json.dumps({**idx, "r": rows_}, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    # the newest rows on their own: the search page paints from this small file while the full index is still loading
    write("data/head.json", json.dumps({**idx, "n": len(rows_), "r": rows_[:300]}, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    shutil.copy(ROOT / "assets" / "og.jpg", OUT / "og.jpg")
    if LOGOS: shutil.copytree(ROOT / "assets" / "logos", OUT / "logos")

    # Public JSON feeds (used by the widget and documented on /api/)
    api_index = []
    def api(path, name, page_path, js, cap=30):
        jobs_ = [{"title": j["title"], "category": CAT[j["cat"]], "company": j["company"], "location": j["location"], "remote": bool(j["remote"]), "salary": j["salary"], "posted": j["posted"],
                  "url": f"{FULL}/job/{j['slug']}/", "logo": f"{FULL}/logos/{slugify(j['company'])}.png" if slugify(j["company"]) in LOGOS else ""} for j in order(js)[:cap]]
        write(f"api/v1/{path}.json", json.dumps({"name": name, "url": f"{FULL}/{page_path}", "site": SITE, "site_url": FULL + "/", "updated": TODAY, "total": len(js), "jobs": jobs_},
                                                ensure_ascii=False, separators=(",", ":")), sitemap=False)
        api_index.append({"name": name, "feed": f"{FULL}/api/v1/{path}.json", "page": f"{FULL}/{page_path}", "total": len(js)})
    api("latest", "Tech jobs", "jobs/", active); write("badge/jobs.svg", badge_svg("Tech jobs", f"{n:,} open"), sitemap=False)
    api("remote", "Remote tech jobs", "remote/", remote); write("badge/remote.svg", badge_svg("Remote tech jobs", f"{len(remote):,} open"), sitemap=False)
    for t, js in by_tag.items():
        api(f"skills/{tslug(t)}", f"{t} jobs", f"skills/{tslug(t)}/", js); write(f"badge/skills/{tslug(t)}.svg", badge_svg(f"{t} jobs", f"{len(js):,} open"), sitemap=False)
    for cs in CAT:
        if by_cat[cs]:
            api(f"categories/{cs}", f"{CAT[cs]} jobs", f"jobs/{cs}/", by_cat[cs]); write(f"badge/categories/{cs}.svg", badge_svg(f"{CAT[cs]} jobs", f"{len(by_cat[cs]):,} open"), sitemap=False)
    for name, slug, js in places:
        short = name.removeprefix("the ")
        api(f"locations/{slug}", f"Tech jobs in {short}", f"locations/{slug}/", js); write(f"badge/locations/{slug}.svg", badge_svg(f"Tech jobs in {short}", f"{len(js):,} open"), sitemap=False)
    for c, js in companies.items():
        act = [j for j in js if j["active"]]
        api(f"companies/{slugify(c)}", f"Jobs at {c}", f"companies/{slugify(c)}/", act, cap=1500)
        write(f"badge/companies/{slugify(c)}.svg", badge_svg(f"{c} is hiring", roles(len(act), "role")), sitemap=False)
    write("api/v1/index.json", json.dumps({"site": SITE, "updated": TODAY, "feeds": api_index}, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    feed_ref = {"200": {"description": "A list of open jobs, newest first", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Feed"}}}}, "404": {"description": "No such feed"}}
    slug_param = lambda what: [{"name": "slug", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"Lowercase {what} slug as listed in /api/v1/index.json, for example {'python' if what == 'skill' else 'stripe' if what == 'company' else 'engineering' if what == 'category' else 'europe'}"}]
    op = lambda oid, summary, params=None: {"get": {"operationId": oid, "summary": summary, "parameters": params or [], "responses": feed_ref}}
    job_props = {"title": {"type": "string"}, "category": {"type": "string"}, "company": {"type": "string"}, "location": {"type": "string"}, "remote": {"type": "boolean"},
                 "salary": {"type": "string", "description": "Advertised range as published by the employer, empty if none"}, "posted": {"type": "string", "format": "date"},
                 "url": {"type": "string", "format": "uri", "description": "The job's page; the apply button there leads to the employer's own site"}, "logo": {"type": "string"}}
    write("api/openapi.json", json.dumps({"openapi": "3.1.0", "info": {"title": f"{SITE} jobs API", "version": "1", "description":
        f"Open tech jobs collected hourly from employers' official careers pages. Read-only JSON files, no key, CORS enabled. Updated {TODAY}."}, "servers": [{"url": FULL}],
        "paths": {"/api/v1/index.json": {"get": {"operationId": "listFeeds", "summary": "Every feed that exists (skills, categories, locations, companies) with its address and job count",
                                                 "responses": {"200": {"description": "Feed directory", "content": {"application/json": {"schema": {"type": "object"}}}}}}},
                  "/api/v1/latest.json": op("latestJobs", "The newest open tech jobs"), "/api/v1/remote.json": op("remoteJobs", "The newest remote tech jobs"),
                  "/api/v1/skills/{slug}.json": op("jobsBySkill", "Open jobs that ask for a skill", slug_param("skill")),
                  "/api/v1/categories/{slug}.json": op("jobsByCategory", "Open jobs in a category", slug_param("category")),
                  "/api/v1/locations/{slug}.json": op("jobsByLocation", "Open jobs in a country, region or city", slug_param("location")),
                  "/api/v1/companies/{slug}.json": op("jobsByCompany", "Open jobs at one company", slug_param("company"))},
        "components": {"schemas": {"Feed": {"type": "object", "properties": {"name": {"type": "string"}, "url": {"type": "string", "format": "uri"}, "site": {"type": "string"},
                       "updated": {"type": "string", "format": "date"}, "total": {"type": "integer", "description": "All open jobs matching the feed; the list holds the newest ones"},
                       "jobs": {"type": "array", "items": {"type": "object", "properties": job_props}}}}}}}, ensure_ascii=False, indent=1), sitemap=False)

    # Open data as CSV
    csvq = lambda v: '"' + str(v).replace('"', '""') + '"'
    def csv_out(name, header, rows):
        write(f"data/open/{name}.csv", "\n".join([",".join(header)] + [",".join(csvq(v) for v in r) for r in rows]) + "\n", sitemap=False)
    medn = lambda js: (int(median([(lo + hi) / 2 for j in js if j["usd"] for lo, hi in [j["usd"]]])) if sum(1 for j in js if j["usd"]) >= 15 else "")
    csv_out("skills", ["skill", "open_roles", "remote_roles", "median_advertised_salary_usd", "source"],
            [[t, len(js), sum(j["remote"] for j in js), medn(js), f"{FULL}/skills/{tslug(t)}/"] for t, js in sorted(by_tag.items(), key=lambda kv: -len(kv[1]))])
    csv_out("companies", ["company", "open_roles", "remote_roles", "source"],
            [[c, sum(j["active"] for j in js), sum(j["remote"] for j in js if j["active"]), f"{FULL}/companies/{slugify(c)}/"] for c, js in comp_items])
    csv_out("categories", ["category", "open_roles", "remote_roles", "median_advertised_salary_usd", "source"],
            [[CAT[cs], len(by_cat[cs]), sum(j["remote"] for j in by_cat[cs]), medn(by_cat[cs]), f"{FULL}/jobs/{cs}/"] for cs in CAT if by_cat[cs]])
    csv_out("locations", ["location", "open_roles", "source"], [[name.removeprefix("the "), len(js), f"{FULL}/locations/{slug}/"] for name, slug, js in places])
    for f in ("app.js", "embed.js", "site.js", "widget.js", "widgets.js", "resume.js", "account.js"):
        shutil.copy(ROOT / "assets" / f, OUT / f)
    (OUT / "style.css").write_text(mincss((ROOT / "assets" / "style.css").read_text(encoding="utf-8")), encoding="utf-8")
    (OUT / "tools.css").write_text(mincss((ROOT / "assets" / "tools.css").read_text(encoding="utf-8")), encoding="utf-8")
    shutil.copy(ROOT / "assets" / "tools.js", OUT / "tools.js")
    shutil.copytree(ROOT / "assets" / "fonts", OUT / "fonts")
    # service worker: keeps versioned scripts and styles, fonts and logos in the browser, so repeat views skip the network for them
    # Offline page: shown only when a page was never opened before and there is no connection
    page("offline/", f"You are offline | {SITE}", "This page is shown when there is no connection and the page you asked for was not opened before.",
         '<h1>No connection right now</h1><p class="lead">Pages you opened before still work: your saved jobs, the jobs you looked at and the tools. '
         f'<a href="{P}/my-jobs/">Open My jobs</a>. The rest comes back when the connection does.</p>', head='<meta name="robots" content="noindex">', sitemap=False, compact=True)
    # Service worker. Three jobs: (1) versioned scripts and styles, fonts and logos come from the browser's store, so repeat views skip
    # the network for them; (2) every page the visitor opens is kept (the newest 80), so saved jobs and recently read jobs open with no
    # connection; (3) the search data is kept too, so the search page works offline with the last list it loaded.
    (OUT / "sw.js").write_text(f"""var V='{V}',C='hrn-assets-'+V,PG='hrn-pages-1',B='{P}';
self.addEventListener('install',function(e){{e.waitUntil(caches.open(PG).then(function(c){{return c.addAll([B+'/offline/',B+'/my-jobs/']).catch(function(){{}});}}));self.skipWaiting();}});
self.addEventListener('activate',function(e){{e.waitUntil(caches.keys().then(function(ks){{return Promise.all(ks.map(function(k){{return k.indexOf('hrn-assets-')===0&&k!==C?caches.delete(k):null;}}));}}).then(function(){{return self.clients.claim();}}));}});
function trim(c){{return c.keys().then(function(ks){{return ks.length>80?Promise.all(ks.slice(0,ks.length-80).map(function(k){{return c.delete(k);}})):null;}});}}
self.addEventListener('fetch',function(e){{var r=e.request;if(r.method!=='GET')return;var u=new URL(r.url);if(u.origin!==location.origin)return;
if(/\\/(fonts|logos)\\//.test(u.pathname)||/[?&]v=/.test(u.search)){{
e.respondWith(caches.open(C).then(function(c){{return c.match(r).then(function(hit){{return hit||fetch(r).then(function(res){{if(res.ok)c.put(r,res.clone());return res;}});}});}}).catch(function(){{return fetch(r);}}));return;}}
var page=r.mode==='navigate',data=/\\/data\\/(head|index|geo|skills)\\.json$/.test(u.pathname);if(!page&&!data)return;
var key=page?u.origin+u.pathname:r;
e.respondWith(fetch(r).then(function(res){{if(res.ok){{var copy=res.clone();caches.open(PG).then(function(c){{return c.put(key,copy).then(function(){{return trim(c);}});}});}}return res;}})
.catch(function(){{return caches.open(PG).then(function(c){{return c.match(key).then(function(hit){{return hit||(page?c.match(B+'/offline/'):Response.error());}});}});}}));}});
function fit(){{return caches.open('hrn-profile').then(function(c){{return c.match(B+'/__profile').then(function(r){{return r&&r.json();}}).then(function(st){{if(!st)return;
return fetch(B+'/data/head.json',{{cache:'no-store'}}).then(function(r){{return r.json();}}).then(function(d){{var A=st.A||{{}},n=0,first='';
d.r.forEach(function(r){{var t=r[14]||0;if(!t||t*60000<=st.seen)return;if(A.cats&&A.cats.length&&A.cats.indexOf(d.k[r[5]])<0)return;if(A.where==='remote'&&!(r[4]&1))return;if(A.where==='office'&&(r[4]&1))return;
if(A.pay&&!(r[10]>=A.pay))return;if(A.exp==='0'&&r[6]!==1&&r[6]!==2)return;n++;if(!first)first=r[1]+' at '+d.c[r[2]];}});
if(!n)return;st.seen=Date.now();return c.put(B+'/__profile',new Response(JSON.stringify(st))).then(function(){{
return self.registration.showNotification(n+(n===1?' new job fits':' new jobs fit')+' your answers',{{body:first+(n>1?' and '+(n-1)+' more':''),tag:'hrn-fit',data:B+'/for-you/'}});}});}});}});}}).catch(function(){{}});}}
self.addEventListener('periodicsync',function(e){{if(e.tag==='hrn-fit')e.waitUntil(fit());}});
self.addEventListener('notificationclick',function(e){{e.notification.close();e.waitUntil(clients.openWindow(e.notification.data||B+'/'));}});
""", encoding="utf-8")
    write("favicon.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">{MARK}</svg>', sitemap=False)
    write("hiring-badge.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="220" height="48" viewBox="0 0 220 48" role="img" aria-label="We\'re hiring — {e(SITE)}">'
          f'<rect width="220" height="48" rx="10" fill="#0e0e0c"/><circle cx="26" cy="24" r="7" fill="#7ee39a"/>'
          '<text x="46" y="21" fill="#fff" font-family="Inter,system-ui,-apple-system,Segoe UI,sans-serif" font-size="14" font-weight="700">We’re hiring</text>'
          f'<text x="46" y="37" fill="#b9b7ad" font-family="Inter,system-ui,-apple-system,Segoe UI,sans-serif" font-size="11">Open roles on {e(SITE)}</text></svg>', sitemap=False)
    (OUT / ".nojekyll").write_text("")
    write("manifest.json", json.dumps({"name": SITE, "short_name": SITE, "start_url": P + "/", "scope": P + "/", "display": "standalone", "background_color": "#f6f5f0", "theme_color": "#0e0e0c",
                                       "icons": [{"src": P + "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]}), sitemap=False)
    job_mod = {f"job/{j['slug']}/": (j.get("last_seen") if j["active"] else j.get("closed")) or TODAY for j in jobs}      # a closed job's page last changed the day it closed
    urlset = lambda urls: ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                           + "".join(f"<url><loc>{e(FULL + '/' + u)}</loc><lastmod>{job_mod.get(u, TODAY)}</lastmod></url>" for u in urls) + "</urlset>")
    job_urls = [u for u in URLS if u.startswith("job/")]
    parts = [("sitemaps/pages.xml", [u for u in URLS if not u.startswith("job/")])]
    parts += [(f"sitemaps/jobs-{i // 20000 + 1}.xml", job_urls[i:i + 20000]) for i in range(0, len(job_urls), 20000)]
    for name, urls in parts: write(name, urlset(urls), sitemap=False)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<sitemap><loc>{FULL}/{name}</loc><lastmod>{TODAY}</lastmod></sitemap>" for name, _ in parts) + "</sitemapindex>", sitemap=False)
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User", "Google-Extended",
               "Applebot-Extended", "Amazonbot", "meta-externalagent", "CCBot", "DuckAssistBot", "MistralAI-User", "cohere-ai"]
    write("robots.txt", "User-agent: *\nAllow: /\n\n# AI assistants and AI search may read, quote and link to every page. A guide for them: "
          f"{FULL}/llms.txt\n" + "".join(f"User-agent: {b}\n" for b in ai_bots) + f"Allow: /\n\nSitemap: {FULL}/sitemap.xml\n", sitemap=False)
    # IndexNow: the key file, and the list of pages that changed for the workflow to send (Bing, and the assistants that search through it).
    # The site is rebuilt every hour but the list is sent once a day, so it holds yesterday and today: a job first seen at noon is in tomorrow's list.
    if CFG.get("indexnow_key"):
        write(f'{CFG["indexnow_key"]}.txt', CFG["indexnow_key"], sitemap=False)
        YDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        changed = ["", "jobs/", "new/", "remote/", "trends/", "salaries/", "companies/"] + [f"job/{j['slug']}/" for j in jobs if j.get("first_seen") in (YDAY, TODAY) or j.get("closed") in (YDAY, TODAY)]
        (ROOT / "data" / "indexnow.json").write_text(json.dumps({"host": BASE.split("//", 1)[-1], "key": CFG["indexnow_key"], "keyLocation": f'{FULL}/{CFG["indexnow_key"]}.txt',
                                                                 "urlList": [f"{FULL}/{u}" for u in changed[:10000]]}))
    print(f"built {len(URLS)} pages: {n} active jobs, {len(archived)} archived, {len(companies)} companies, {len(places)} locations")


if __name__ == "__main__":
    main()
