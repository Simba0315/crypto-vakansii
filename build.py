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
import resume_examples
import skills_info                      # what each skill is, in plain words, and its group
import geo_cities                       # where the cities in postings are, for the jobs map
import resignation_pages                # a resignation letter per situation (/resignation-letters/)
import resume_words                     # stronger words for an overused resume verb (/resume-words/)
import compare_sites                    # sourced facts for "Hiring Right Now vs <job site>" (/vs/)
import glossary_terms                   # the glossary, one page per term (/glossary/)

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


def flag_of(code):
    """'US' -> its flag: the two letters as regional-indicator symbols, which every phone and Mac draws as the flag."""
    return "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in code) if len(code) == 2 and code.isascii() and code.isalpha() and code.isupper() else ""


def fl(code):
    """The flag as a small icon in front of a country name. Chrome on Windows has no flag pictures: site.js turns the icon into a two-letter badge there."""
    f = flag_of(code)
    return f'<i class="fl">{f}</i>' if f else ""


def loc_flags(loc, limit=3):
    """Flags of the countries a location line names (the owner's rule: a country is never shown without its flag)."""
    return "".join(fl(c) for c, _ in countries_of(loc)[:limit]) if loc else ""


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
PLACE_CODE = {slug: ("" if rule == "region" else rule if isinstance(rule, str) else rule[1]) for _, slug, rule in PLACES}      # a city or state carries its country's flag
REGION_FLAG = {"europe": "\U0001F1EA\U0001F1FA", "asia-pacific": "\U0001F30F", "latin-america": "\U0001F30E", "africa": "\U0001F30D"}
PATH_PLACE = re.compile(r"^(?:locations|crypto/in)/([a-z0-9-]+)/")


def pfl(slug):
    """Flag icon for a place page: the country's flag, the flag of a city's country, a globe for a part of the world."""
    return f'<i class="fl">{REGION_FLAG[slug]}</i>' if slug in REGION_FLAG else fl(PLACE_CODE.get(slug, ""))


def path_fl(path):
    m = PATH_PLACE.match(path)
    return pfl(m.group(1)) if m else ""


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
V = hashlib.md5(b"".join((ROOT / "assets" / f).read_bytes() for f in ("style.css", "site.js", "app.js", "account.js", "tools.js", "tools.css", "resume.js", "widget.js", "widgets.js", "map.js"))).hexdigest()[:8]   # cache-busting version
MINI_FOOT = (f'<footer class="mini"><div class="wrap"><p class="fine">© {TODAY[:4]} {e(SITE)} · <a href="{P}/jobs/">All jobs</a> · <a href="{P}/remote/">Remote</a> · '
             f'<a href="{P}/companies/">Companies</a> · <a href="{P}/salaries/">Salaries</a> · <a href="{P}/post-a-job/">Post a job</a> · <a href="{P}/about/">About</a> · '
             f'<a href="{P}/methodology/">How it works</a> · <a href="{P}/privacy/">Privacy</a> · <a href="{P}/terms/">Terms</a></p></div></footer>')
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
# A remote posting that names a part of the world instead of countries ("Remote - EMEA", "North America"): the countries Google needs.
_EU = ["GB", "DE", "FR", "IE", "NL", "ES", "PT", "PL", "SE", "CH", "AT", "IT", "DK", "NO", "FI", "BE", "CZ", "RO", "UA", "EE", "LT", "GR", "BG", "HU", "RS"]
REGION_LANDS = [(r"north america|\bnamer\b|\bamer\b|\bnoram\b", ["US", "CA"]), (r"\bamericas\b", ["US", "CA", "MX", "BR", "AR", "CO", "CL"]),
                (r"\bemea\b", _EU + ["IL", "AE", "SA", "TR", "ZA", "NG", "KE"]), (r"\beurope\b|\beu\b|\beea\b", _EU),
                (r"\bapac\b|asia[- ]pacific", ["IN", "SG", "HK", "JP", "KR", "TW", "AU", "NZ", "MY", "PH", "ID", "TH", "VN"]),
                (r"\blatam\b|latin america|south america", ["BR", "MX", "AR", "CO", "CL"])]
NOT_A_PLACE = re.compile(r"^(fully |100% )?(remote|remoto|global|worldwide|anywhere|international|multiple locations|hybrid|emea|apac|amer|americas|namer|latam|europe|north america|"
                         r"remote[ ,/–-]+\w+( \w+)?|\w+( \w+)?[ ,/–-]+remote)$", re.I)
VALID_TO = (datetime.date.fromisoformat(TODAY) + datetime.timedelta(days=30)).isoformat()      # the site is rebuilt hourly; a closed job loses its markup at once


def region_lands(loc):
    names = {"US": "United States", **{c: nm for c, nm, _, _ in COUNTRIES}}
    for rx, codes in REGION_LANDS:
        if re.search(rx, loc or "", re.I): return [(c, names[c]) for c in codes if c in names]
    return []
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
LOGO_SITE = {k: v for k, v in LOGO_SITE.items() if not v.startswith("board:")}      # "board:<ats>/<token>": the logo came from the job board, the site is unknown


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
    pg = re.search(r", page \d+(?= \| |$)", t)        # page 2, 3 of a list: the number must survive, or the pages share one title
    if pg and len(t) > 65:
        rest = t[:pg.start()] + t[pg.end():]
        left, brand = rest.rsplit(" | ", 1) if " | " in rest else (rest, "")
        left = re.sub(r" \([\d,]+ (?:open|roles?)\)", "", left)
        room = 65 - len(pg.group(0)) - (len(brand) + 3 if brand else 0)
        if len(left) > room and len(left) + len(pg.group(0)) <= 65: return left + pg.group(0)      # the brand gives way before the words do
        if len(left) > room:
            head_ = re.split(r" — |: ", left)[0]
            left = head_ if 12 <= len(head_) <= room else left[:room + 1].rsplit(" ", 1)[0]
            left = re.sub(r"(?: (?:and|at|in|of|for|the|with|to|a|&))+$", "", left.rstrip(" ,-–—:&("))
        return left + pg.group(0) + (" | " + brand if brand else "")
    if len(t) <= 65: return t
    t2 = re.sub(r" \([\d,]+ (?:open|roles?)\)", "", t)
    if len(t2) <= 65: return t2
    if " | " in t2:                                           # shorten the descriptive part, never drop the brand
        left, brand = t2.rsplit(" | ", 1)
        if len(left) <= 65: return left           # a title that names a place or a figure keeps it; the brand gives way first
        head_ = re.split(r" — |: ", left)[0]
        if len(head_) >= 12: left = head_
        room = 65 - len(brand) - 3
        if len(left) > room: left = left[:room + 1].rsplit(" ", 1)[0].rstrip(" ,-–—:&")
        return f"{left} | {brand}"
    return t2 if len(t2) <= 70 else t2[:68].rsplit(" ", 1)[0].rstrip(" ,-–—:&(")


def fit_desc(d):
    d = " ".join(d.split())
    if len(d) < 125: d = d.rstrip(".") + f". Collected from official company career pages and updated every hour on {SITE}."
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
    if path == "":      # search-engine ownership tags (config.json "verify"): the owner pastes the code each webmaster tool gives him
        vf = CFG.get("verify") or {}
        head += "".join(f'<meta name="{n_}" content="{e(vf[k_])}">' for k_, n_ in (("google", "google-site-verification"), ("bing", "msvalidate.01"), ("yandex", "yandex-verification")) if vf.get(k_))
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
<a class="nl" href="{P}/jobs/">Jobs</a><a class="nl" href="{P}/categories/">Categories</a><a class="nl" href="{P}/companies/">Companies</a><a class="nl" href="{P}/salaries/">Salaries</a><a class="nl" href="{P}/resume/">Resume</a><a class="nl" href="{P}/tools/">Tools</a><a class="nl" href="{P}/for-you/">For you</a><a class="nl" href="{P}/my-jobs/">My jobs<span id="saved-n"></span></a><a class="nl only-m" href="{P}/remote/">Remote jobs</a><a class="nl" href="{P}/pricing/">Pricing</a>{NAV_PLUS}<a class="nl only-m" href="{P}/post-a-job/">Post a job</a></nav>
<div class="hact"><button class="icon ic-s" id="palbtn" type="button" aria-label="Quick search (Ctrl K)"></button><button class="icon ic-t" id="theme" type="button" aria-label="Switch between light and dark"></button><a class="btn" href="{P}/post-a-job/">Post a job</a>
<button class="icon ic-m burger" id="menu" type="button" aria-label="Menu" aria-expanded="false"></button></div></div></header>
{hero}<main class="wrap" id="main">{body}</main>
{MINI_FOOT if compact else FULL_FOOT()}
</body></html>""", sitemap)


def FULL_FOOT():
    return f"""<footer><div class="wrap"><div class="fcols">
<div><a class="logo" href="{P}/">{LOGO}<span>{e(SITE)}</span></a><p>Job boards fill up with listings that closed weeks ago. Every role here comes from the company’s own careers page and is re-checked every hour.</p></div>
<div><p class="fhd">Find jobs</p><ul><li><a href="{P}/jobs/">All jobs</a></li><li><a href="{P}/jobs-near-me/">Jobs near me</a></li><li><a href="{P}/map/">Jobs map</a></li><li><a href="{P}/remote/">Remote jobs</a></li><li><a href="{P}/new/">New jobs</a></li><li><a href="{P}/entry-level/">Entry-level</a></li><li><a href="{P}/with-salary/">Salary listed</a></li><li><a href="{P}/crypto/">Crypto &amp; web3 jobs</a></li><li><a href="{P}/for-you/">Jobs for you</a></li><li><a href="{P}/my-jobs/">My jobs</a></li></ul></div>
<div><p class="fhd">Browse</p><ul><li><a href="{P}/categories/">Job categories</a></li><li><a href="{P}/roles/">Roles A to Z</a></li><li><a href="{P}/skills/">Skills</a></li><li><a href="{P}/locations/">Jobs by country</a></li><li><a href="{P}/companies/">Companies</a></li><li><a href="{P}/perks/">Perks</a></li>{FOOT["cats"]}</ul></div>
<div><p class="fhd">Tools and data</p><ul><li><a href="{P}/tools/">Free tools</a></li><li><a href="{P}/resume/">Resume builder</a></li><li><a href="{P}/resume/examples/">Resume examples</a></li><li><a href="{P}/how-to-become/">How to become…</a></li><li><a href="{P}/career-quiz/">Career quiz</a></li><li><a href="{P}/cover-letter-examples/">Cover letter examples</a></li><li><a href="{P}/interview-questions/">Interview questions</a></li><li><a href="{P}/resignation-letters/">Resignation letters</a></li><li><a href="{P}/resume-words/">Resume words</a></li><li><a href="{P}/mentors/">Mentors</a></li><li><a href="{P}/salaries/">Salaries</a></li><li><a href="{P}/compare/">Compare skills</a></li><li><a href="{P}/trends/">Hiring trends</a></li><li><a href="{P}/reports/">Monthly reports</a></li><li><a href="{P}/insights/">Rankings</a></li><li><a href="{P}/open-hiring-index/">Open hiring index</a></li><li><a href="{P}/status/">Is the data fresh?</a></li></ul></div>
<div><p class="fhd">Employers and sites</p><ul><li><a href="{P}/post-a-job/">Post a job</a></li><li><a href="{P}/pricing/">Pricing</a></li><li><a href="{P}/job-descriptions/">Job description templates</a></li><li><a href="{P}/how-to-hire/">How to hire…</a></li><li><a href="{P}/widgets/">Jobs for your website</a></li><li><a href="{P}/api/">Data for developers (API)</a></li><li><a href="{P}/feeds/">Job feeds for channels (RSS)</a></li><li><a href="{P}/partners/">Partners</a></li><li><a href="{P}/media-kit/">Media kit</a></li><li><a href="{P}/investors/">Investors</a></li><li><a href="{P}/plus/">Plus</a></li></ul></div>
<div><p class="fhd">About</p><ul><li><a href="{P}/about/">About</a></li><li><a href="{P}/vs/">Compared with other job sites</a></li><li><a href="{P}/promise/">Our promise</a></li><li><a href="{P}/ahead/">What is new here</a></li><li><a href="{P}/methodology/">How it works</a></li><li><a href="{P}/guides/">Guides</a></li><li><a href="{P}/help/">Help</a></li><li><a href="{P}/glossary/">Glossary</a></li><li><a href="{P}/safety/">Job offer safety</a></li><li><a href="{P}/archive/">Closed jobs archive</a></li><li><a href="{P}/privacy/">Privacy</a></li><li><a href="{P}/terms/">Terms</a></li></ul></div>
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


# Line icons for the fields of work, drawn for this site (24x24, stroke only). One per field, so a list of fields is read by shape before it is read by word.
ICON = {
    "code": '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5"/>',
    "spark": '<circle cx="12" cy="12" r="2.5"/><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/>',
    "chart": '<path d="M2 20h20M5 20V11M10 20V5M15 20v-7M20 20V8"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .6-8A6 6 0 0 0 6.1 9.5 4.3 4.3 0 0 0 7 18z"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.5-3.2 7.9-8 9-4.8-1.1-8-4.5-8-9V6l8-3z"/><path d="M9 12l2 2 4-4"/>',
    "board": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16M15 4v10"/>',
    "pen": '<path d="M4 20l4-1L19 8l-3-3L5 16l-1 4z"/><path d="M14 7l3 3"/>',
    "megaphone": '<path d="M4 10v4h3l8 4V6L7 10H4z"/><path d="M18 9a4 4 0 0 1 0 6"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "headset": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="2.5" y="13" width="4" height="6" rx="1.5"/><rect x="17.5" y="13" width="4" height="6" rx="1.5"/>',
    "coin": '<circle cx="12" cy="12" r="9"/><path d="M14.5 9.5C14 8.6 13.1 8 12 8c-1.5 0-2.5.8-2.5 2s1 1.7 2.5 2 2.500.8 2.5 2-1 2-2.5 2c-1.1 0-2-.5-2.5-1.4M12 6.5V8M12 16v1.5"/>',
    "scales": '<path d="M12 4v16M7 20h10M5 7h14M5 7l-3 7a3 3 0 0 0 6 0L5 7zM19 7l-3 7a3 3 0 0 0 6 0l-3-7z"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "chip": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
    "text": '<path d="M4 6h16M4 11h16M4 16h9"/>',
    "heart": '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    "cap": '<path d="M2 9l10-5 10 5-10 5L2 9z"/><path d="M6 11.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-4.5"/>',
    "bag": '<path d="M5 8h14l-1 12H6L5 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
    "hex": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M12 8l3.5 4-3.5 4-3.5-4L12 8z"/>',
    "crown": '<path d="M4 18h16M4 18L3 8l5 4 4-6 4 6 5-4-1 10"/>',
    "sprout": '<path d="M12 21v-9"/><path d="M12 12c0-3.5-2.5-6-7-6 0 3.5 2.5 6 7 6z"/><path d="M12 14c0-3 2.2-5 7-5 0 3-2.2 5-7 5z"/>',
    "factory": '<path d="M3 20V10l6 4v-4l6 4V6h6v14H3z"/>',
    "box": '<path d="M3 8l9-5 9 5v8l-9 5-9-5V8z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
    "case": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    "dots": '<circle cx="6" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="18" cy="12" r="1.5"/>',
}
SLUG_ICON = {   # fields on /categories/ and the categories of job lists
    "software-development": "code", "ai-machine-learning": "spark", "data-analytics": "chart", "cloud-devops-it": "cloud", "security": "shield", "product-project": "board",
    "design-creative": "pen", "marketing-communications": "megaphone", "sales": "trend", "customer-service": "headset", "accounting-finance": "coin", "legal-compliance": "scales",
    "hr-recruiting": "users", "operations-administration": "sliders", "hardware-engineering": "chip", "writing-translation": "text", "science-healthcare": "heart",
    "education-training": "cap", "retail-hospitality": "bag", "languages": "globe", "crypto-web3": "hex", "leadership": "crown", "internships-entry-level": "sprout",
    "engineering": "code", "product": "board", "design": "pen", "sales-bd": "trend", "marketing": "megaphone", "support": "headset", "compliance-legal": "scales", "finance": "coin",
    "people": "users", "data-research": "chart", "operations": "sliders", "healthcare": "heart", "manufacturing": "factory", "supply-chain": "box", "retail": "bag",
    "education": "cap", "consulting": "case", "other": "dots",
}
PATH_FIELD = re.compile(r"^(?:jobs|crypto|categories|salaries)/([a-z0-9-]+)/$")


def icon(slug):
    """The field's icon in a soft square, or nothing when the slug is not a field."""
    name = SLUG_ICON.get(slug)
    return f'<span class="fic"><svg viewBox="0 0 24 24" aria-hidden="true">{ICON[name]}</svg></span>' if name else ""


def path_icon(path):
    m = PATH_FIELD.match(path)
    return icon(m.group(1)) if m else ""


def card(j, extra=0):
    b = []
    if j["featured"]: b.append('<span class="pill acc">Featured</span>')
    if not j["active"]: b.append('<span class="pill">Closed</span>')
    if j["remote"]: b.append('<span class="pill ok">Remote</span>')
    if j["level"]: b.append(f'<span class="pill">{e(j["level"])}</span>')
    b += [f'<span class="pill">{e(t)}</span>' for t in j["tags"][:3]]
    loc = j["location"] if len(j["location"]) <= 60 else j["location"][:57].rstrip(" ,;") + "…"
    sub = e(j["company"]) + (f" · {loc_flags(j['location'])}{e(loc)}" if loc else "") + (f" · +{extra} more location{'s' if extra > 1 else ''}" if extra else "")
    label, fresh = age(j["posted"])
    return (f'<li class="job{" feat" if j["featured"] else ""}"><a href="{P}/job/{j["slug"]}/">{ava(j["company"])}'
            f'<span><span class="jt">{e(j["title"])}</span><span class="js">{sub}</span></span>'
            f'<span class="jr"><span class="jp{"" if j["salary"] else " none"}">{e(j["salary"][:28]) if j["salary"] else "—"}</span><span class="pills">{"".join(b)}</span><time {when(j)}{" class=\"new\"" if fresh and j["active"] else ""}>{label}</time></span></a></li>')


def tile(url, name, count, avatar=False):
    return f'<li><a class="tile" href="{P}/{url}">{ava(name, "sm") if avatar else ""}{path_icon(url)}<span class="n">{path_fl(url)}{e(name)}</span><span class="c">{count:,}</span></a></li>'


def section(title, inner, link=None, sid="", sub=""):
    """A titled block. `sub` is one plain sentence beside the heading (heading left, sentence and the link right)."""
    more = f'<a href="{P}/{link[0]}">{e(link[1])}</a>' if link else ""
    sb = f'<p class="sec-sub">{e(sub)}</p>' if sub else ""
    return f'<section class="sec"{f" id={chr(34)}{sid}{chr(34)}" if sid else ""}><div class="sec-head{" has-sub" if sub else ""}"><h2>{e(title)}</h2>{sb}{more}</div>{inner}</section>'


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


def labrow(label, items, more=None):
    """A labelled row: the label on the left, the links on the right, an optional "More" link last."""
    if not items: return ""
    tail = f'<a class="more" href="{P}/{more[0]}">{e(more[1])}</a>' if more else ""
    return f'<div class="lrow"><b>{e(label)}</b><div>{"".join(items)}{tail}</div></div>'


def rel(links, more=None):
    """Row of related listing links: [(path, label, count)], biggest first; `more` = (path, label) of the full directory."""
    links = sorted(links, key=lambda x: -x[2])[:14]
    return labrow("Related", [f'<a href="{P}/{u}">{e(t)}</a>' for u, t, _ in links], more)


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
    if len(mids) >= 30: cells.append((money(median(mids)), f'<a href="{P}/glossary/median/">median</a> advertised salary'))
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


# How many pages a topic list may have. The whole site has to fit the hosting limit (the workflow stops above 950 MiB), and a list's
# second and later pages are the first thing to give way as jobs are added: measured on 13 Nov 2026 with 41,187 open jobs, pages 3 to 5
# of all lists weighed 63 MiB and page 2 another 66 MiB. main() sets the number from the count of open jobs; HRN_PAGE_CAP overrides it
# (the workflow builds again with 1 if a build still came out too large).
LIST_PAGES = 2


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra="", feed=False, head_html=None, after="", max_pages=None, more=None, faq=None, hub="", accent=None, list_title="", faq_first=None):
    jobs = order(jobs)
    if feed: rss(f"{path}feed.xml", f"{h1} — {SITE}", path, jobs)
    rows = collapse(jobs)
    total = len(rows)
    # deep pages of a topic list add weight, not visitors (the search shows the rest); company pages keep everything
    if max_pages is None and head_html is None: max_pages = LIST_PAGES
    elif max_pages: max_pages = min(max_pages, LIST_PAGES)
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
        top = head_html if head_html is not None else (crumbs(*trail, (h1, "")) + f"<h1>{path_fl(path)}{e(h1)}</h1>" + (f'<p class="lead">{intro}</p>' if intro and n == 1 else ""))
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
    if j["location"]: rows.append(("Location", loc_flags(j["location"], 6) + e(j["location"])))
    if j["remote"]:
        lands_r = countries_of(j["location"]) if j["location"] else []
        scope = ("worldwide" if j.get("anywhere") else " or ".join(fl(c_) + e(nm) for c_, nm in lands_r[:4]) if lands_r else e(next((nm for nm, rx in REGION_WORDS if re.search(rx, j["location"], re.I)), "")))
        rows.append(("Workplace", f"Remote, {scope}" if scope else 'Remote<br><span class="note">The posting does not say from which countries. Check before you apply.</span>'))
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
    head, micro = "", ""
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
                if not here and NOT_A_PLACE.match(part): continue       # "Remote", "EMEA": not an address
                spots.append({"@type": "Place", "address": {"@type": "PostalAddress", "addressLocality": part, **({"addressCountry": here[0][0]} if len(here) == 1 else {})}})
            if spots: ld["jobLocation"] = spots[0] if len(spots) == 1 else spots
        if j["remote"]:
            ld["jobLocationType"] = "TELECOMMUTE"
            lands = (countries_of(j["location"]) or region_lands(j["location"])) if j["location"] else []
            if lands: ld["applicantLocationRequirements"] = [{"@type": "Country", "name": nm} for _, nm in lands][:32] if len(lands) > 1 else {"@type": "Country", "name": lands[0][1]}
        if j.get("etype") in ETYPE_LD:
            ld["employmentType"] = ETYPE_LD[j["etype"]]
        ld["validThrough"] = VALID_TO
        # Google reads a remote posting only with the countries it is open to. A remote job that names none ("Remote", "Global")
        # gets no markup at all rather than a guessed country; its page is still found by ordinary search.
        mark_ok = (not j["remote"] or "applicantLocationRequirements" in ld) and ("jobLocation" in ld or "applicantLocationRequirements" in ld)
        if not mark_ok: head, micro = "", ""
        elif full: head, micro = "", microdata(ld)          # description is marked up in place, see microdata()
        else: head, micro = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>", ""
        host_ = re.sub(r"^www\.", "", re.sub(r"^https?://([^/?#]+).*$", r"\1", j["url"] or "")).lower()
        apply_btn = (f'<a class="btn primary lg" id="apply" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">Apply on company site</a>'
                     + (f'<p class="note goes">Opens <b>{e(host_)}</b></p>' if host_ and "/" not in host_ and " " not in host_ else "")
                     + '<p class="note" id="apply-hint" hidden>Applied? Mark it below to keep track of it in My jobs.</p>'
                     # Rezi's best-converting box, done our way: no account, the posting goes straight into the checker
                     + f'<a class="rmbox" href="{P}/tools/resume-match/?job={j["slug"]}"><b>Check my resume for this job</b><span>See which of its words your resume is missing</span></a>')
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
    about = tldr + ((f'<div itemscope itemtype="https://schema.org/JobPosting">{micro}<h2>About the role</h2><div class="prose desc" itemprop="description">{full}</div></div>'
                     if micro else f'<h2>About the role</h2><div class="prose desc">{full}</div>')
                    + f'<p class="note">The employer’s own description, as published on {e(j["company"])}’s careers page.</p>' if full else
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


def cite(path, title, quote=""):
    """Formats for linking to a page. With `quote`: a sentence with the page's main figure, ready to paste into an article.
    Writers cite a figure they can copy whole: a tenth of the links to the largest job site point at its salary figures and labour-market counts."""
    url = f"{FULL}/{path}"
    link_html = f'<a href="{url}">{title} — {SITE}</a>'
    ready = (f'<div class="quotable"><p class="flabel">Writing about this? A sentence you can quote</p><blockquote id="quote">{e(quote)} <cite>Source: {e(SITE)}, {e(url)}</cite></blockquote>'
             '<p><button class="btn ghost sm" type="button" data-clip="quote" style="margin-top:0">Copy the sentence</button> <span class="note">Free to use with the link.</span></p></div>') if quote else ""
    return (ready + '<details class="embed"><summary>Cite or link to this page</summary><p class="note">Free to quote with a link back. Pick a format:</p>'
            f'<pre><code>{e(link_html)}</code></pre><pre><code>{e(f"[{title} — {SITE}]({url})")}</code></pre>'
            f'<pre><code>{e(f"Source: {SITE}, “{title}”, {url}")}</code></pre></details>')


MONTH_YEAR = datetime.date.fromisoformat(TODAY).strftime("%B %Y")
PRICE = {p_["name"]: p_ for p_ in CFG.get("prices", [])}
price_of = lambda name: PRICE.get(name, {}).get("price", "")
was_of = lambda name: (f'<s class="was">{e(PRICE[name]["was"])}</s> ' if PRICE.get(name, {}).get("was") else "")
def ptable(cols, rows):
    """Plans side by side, the way pricing pages show them: a column per plan with its price on top, features in groups, a tick,
    a cross or a few words in every cell. cols: (name, price as HTML, note, best). rows: (group,) or (feature, cell, cell...);
    a cell is True, False, words (shown with a tick) or "~words" (shown plainly: the plan has it in a smaller form)."""
    def cell(v, best):
        b = ' class="best"' if best else ""
        if v is True: return f'<td{b}><span class="pv ok"><span class="vh">Yes</span></span></td>'
        if v is False: return f'<td{b}><span class="pv no"><span class="vh">No</span></span></td>'
        return f'<td{b}><span class="pv lim">{e(v[1:])}</span></td>' if v.startswith("~") else f'<td{b}><span class="pv ok">{e(v)}</span></td>'
    head = '<tr><th class="pf"></th>' + "".join(f'<th scope="col" class="pc{" best" if b else ""}"><b>{e(n_)}</b><span class="pp">{pr}</span><span class="pn">{e(nt)}</span></th>' for n_, pr, nt, b in cols) + "</tr>"
    body = "".join(f'<tr class="pg"><th scope="colgroup" colspan="{len(cols) + 1}">{e(r[0])}</th></tr>' if len(r) == 1 else
                   f'<tr><th scope="row">{e(r[0])}</th>' + "".join(cell(v, cols[i][3]) for i, v in enumerate(r[1:])) + "</tr>" for r in rows)
    return f'<div class="ptwrap"><table class="pt c{len(cols)}"><thead>{head}</thead><tbody>{body}</tbody></table></div>'


LAUNCH = ('<p class="launch"><b>Launch prices.</b> Every price here is about a third of the regular one while the paid plans are new. The regular price is the one crossed out.</p>'
          if CFG.get("launch_prices") else "")


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
    global LIST_PAGES
    LIST_PAGES = int(os.environ.get("HRN_PAGE_CAP") or (2 if len(active) <= 43000 else 1))
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
                   + "".join(f'<a href="{P}/locations/{slug}/">{pfl(slug)}Jobs in {e(name.removeprefix("the "))}</a>' for name, slug, _ in sorted(places, key=lambda x: -len(x[2]))[:6]) + "</p>")
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
        return (f'<div class="dirb"><{tag}><a href="{P}/categories/{fs}/">{icon(fs)}<u>{e(fn)}</u></a><span>{len(js_):,}</span></{tag}><p>{e(fd[0].upper() + fd[1:])}.</p><ul>'
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
    # The hero shows the product instead of describing it: the search, four numbers, then a framed window with today's jobs and
    # three doors beside it (the owner asked, many times, for the look of the sites he sends: light, large, the product on show).
    shot_rows = "".join(card(j) for j in diverse(order(specific), 7, 1))
    # Tabs over the same window: each tab is a real link (works without scripts) and a script swaps the list in place.
    SHOT_MORE = {"remote": "See all remote jobs", "with-salary": "See all jobs with pay listed", "entry-level": "See all entry-level jobs"}
    shot_tabs = [("Latest jobs", "jobs", shot_rows)]
    for lab_, href_, pool_ in (("Remote", "remote", [j for j in specific if j["remote"]]),
                               ("With salary", "with-salary", [j for j in specific if j["salary"]]),
                               ("Entry-level", "entry-level", [j for j in specific if j["entry"]])):
        if len(pool_) >= 7:
            shot_tabs.append((lab_, href_, "".join(card(j) for j in diverse(order(pool_), 7, 1))))
    shot_nav = "".join(f'<a{" class=on" if i_ == 0 else ""} href="{P}/{h_}/" data-tab="{i_}" data-more="{SHOT_MORE.get(h_, "")}">{l_}</a>' for i_, (l_, h_, _) in enumerate(shot_tabs))
    shot_panels = "".join(f'<ul class="jobs" data-panel="{i_}"{"" if i_ == 0 else " hidden"}>{r_}</ul>' for i_, (_, _, r_) in enumerate(shot_tabs))
    rem_n = sum(1 for j in active if j["remote"])
    paid_n = sum(1 for j in active if j["salary"])
    hero = (f'<section class="hero v2"><div class="wrap">'
            f'<p class="stamp"><i></i>Checked {fdate(TODAY, False)} · <b>{n:,}</b> open jobs <span class="wide-only"> · <b>{fresh3:,}</b> new in 3 days</span></p>'
            f'<h1>Stop applying to jobs that are <span class="hl">already gone</span></h1>'
            f'<p class="sub">Old listings stay online long after the job is filled. We read {m} company career pages every hour and keep only what is still open.</p>'
            f'<form class="searchbar two" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Job title, skill or company" aria-label="What: job title, skill or company">'
            f'<span class="sb-sep" aria-hidden="true"></span><input type="search" name="where" placeholder="City, country or remote" aria-label="Where: city, country or remote"><button class="btn primary">Search jobs</button></form>'
            f'<p class="popular"><a href="{P}/remote/">Remote</a><a href="{P}/new/">New this week</a><a href="{P}/with-salary/">Salary listed</a><a href="{P}/entry-level/">Entry-level</a>'
            f'<a href="{P}/perks/visa-sponsorship/">Visa sponsorship</a><a href="{P}/crypto/">Crypto</a><a href="{P}/categories/">All categories</a><a href="{P}/locations/">By country</a></p>'
            f'<p class="near" id="near" hidden></p>'
            f'<div class="hstats"><div><b>{n:,}</b><span>open jobs today</span></div><div><b>{m:,}</b><span>companies, read every hour</span></div>'
            f'<div><b>{rem_n:,}</b><span>can be done from home</span></div><div><b>{len(by_role)}</b><span>kinds of work</span></div></div></div>'
            f'<div class="wrap"><div class="shot"><div class="shot-bar"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>'
            f'<div class="shot-tabs" id="shot-tabs">{shot_nav}<a href="{P}/board/">Live wall</a></div></div>'
            f'<div class="shot-body"><div id="shot-panels">{shot_panels}<p class="shot-more"><a class="btn" id="shot-more" href="{P}/jobs/">See all {n:,} jobs</a></p></div>'
            f'<aside class="shot-side">'
            f'<a class="scard" href="{P}/for-you/"><b>Not sure what to search for?</b><span>Answer five questions and see the jobs that fit you, each with the reasons.</span><em>Find my fit</em></a>'
            f'<a class="scard" href="{P}/resume/"><b>Resume builder</b><span>Five templates, PDF and Word, and an example resume for your kind of work.</span><em>Build a resume</em></a>'
            f'<a class="scard" href="{P}/salaries/"><b>What jobs pay</b><span>{paid_n:,} postings state the pay. See the median for your work.</span><em>Check salaries</em></a>'
            f'<a class="scard" href="{P}/tools/"><b>28 free tools</b><span>Resume review, offer check, letters, interview answers.</span><em>Open the tools</em></a>'
            f'</aside></div></div></div>'
            f'<div class="wrap0 hero-logos"><p>Read every hour from the career pages of</p><div class="logorow">'
            + "".join(f'<a href="{P}/companies/{slugify(c)}/" title="{e(c)}: {sum(j["active"] for j in js):,} open roles">{ava(c)}<span>{e(c)}</span></a>' for c, js in logo_cos)
            + f'<a class="more" href="{P}/companies/">and {len(companies) - len(logo_cos)} more</a></div></div></section>')
    plus_band = ""
    if CFG.get("plus", {}).get("live"):
        plus_band = (f'<div class="band"><div><h2>Get the email when a matching job appears</h2><p>Plus watches your saved searches and helps with the resume and cover letter for each posting. One payment, nothing renews.</p></div>'
                     f'<a class="btn" href="{P}/plus/">See Plus</a></div>')
    band = (f'<div class="band"><div><h2>Hiring?</h2><p>Your posting sits next to {n:,} others here. A standard listing is free; a featured one stays at the top of the list, from {price_of("Featured job")}, paid in crypto.</p></div>'
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

            + section("Browse jobs by category", '<div class="dir">' + "".join(dir_block(*f, top=4, tag="h3") for f in fam_rows) + "</div>", ("categories/", f"All {len(by_role)} kinds of work"), sub="Pick the kind of work you do; each group opens its own list of jobs.")
            + section("The job market today, in four pictures", market_pics, ("insights/", "All rankings and charts"), sub="Counted from today’s open jobs, redone on every update.")
            + pulse + anatomy
            + '<div class="inkband">' + section("Highest paid right now", f'<ul class="jobs">{"".join(card(j) for j, _ in top_paid)}</ul>', ("salaries/", "Salary data"), sub="Only jobs that state a yearly pay, converted to US dollars.") + "</div>"
            + '<section class="sec"><div class="sec-head"><h2>Browse the jobs</h2></div><div class="tabs2">'
              '<input type="radio" name="dir" id="dir-role" checked><label for="dir-role">By role</label>'
              '<input type="radio" name="dir" id="dir-loc"><label for="dir-loc">By location</label>'
              '<input type="radio" name="dir" id="dir-co"><label for="dir-co">By company</label>'
              '<div class="tabp" id="p-role"><ul class="tiles">' + "".join(tile(f"roles/{s_}/", nm, k_) for nm, s_, k_ in ROLE_TOP) + f'</ul><p class="tabmore"><a href="{P}/categories/">All {len(by_role)} roles, by category</a></p></div>'
              + f'<div class="tabp" id="p-loc"><ul class="tiles">{place_top}</ul><p class="tabmore"><a href="{P}/locations/">All {len(places)} locations</a></p></div>'
              + f'<div class="tabp" id="p-co"><ul class="tiles">{comp_top}</ul><p class="tabmore"><a href="{P}/companies/">All {len(companies)} companies</a></p></div></div></section>'
            + plus_band + band
            + section("Free tools", '<div class="tgrid">' + "".join(tools_pages.TILES[u] for u in tools_pages.EXTRA + [u for u, nm, d_ in TOOLS[:3]]) + "</div>",
                      ("tools/", f"All {len(TOOLS) + len(tools_pages.EXTRA)} tools"), sub="Each one opens with a worked example, free and without sign-up.")
            + section("For your own site", '<div class="feats">'
                      f'<a class="feat" href="{P}/widgets/"><h3>A list of jobs for your site</h3><p>Have a blog, a community or a company site? Put a small list of fresh jobs on it. You paste a short piece of code once and the list keeps itself up to date.</p></a>'
                      f'<a class="feat" href="{P}/widgets/"><h3>A “we’re hiring” picture with a live number</h3><p>A small image that shows how many roles are open today. For a site footer, a blog post or a project page.</p></a>'
                      f'<a class="feat" href="{P}/api/"><h3>For programmers</h3><p>The whole job list in a form that programs can read (an API), refreshed every hour. Free, with nothing to sign up for.</p></a></div>')
            + section("Common questions", faq_html, sub="Short answers about where the jobs come from and how to use the site."))
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
              + group("Work style", '<div class="filters"><label><input type="checkbox" id="f-remote"> Remote</label><label><input type="checkbox" id="f-hybrid"> Hybrid</label><label><input type="checkbox" id="f-any"> Work from anywhere</label>'
                                    '<label><input type="checkbox" id="f-entry"> Entry-level</label><label><input type="checkbox" id="f-crypto"> Crypto &amp; web3</label></div>')
              + '<details class="morefilters"><summary>More filters</summary><div class="mf">'
              + group("Search in", '<div class="filters"><label><input type="checkbox" id="f-ti"> Job titles only</label></div>')
              + group("Leave out", '<div class="filters"><label><input type="checkbox" id="f-real"> Roles open 90+ days and talent pools</label></div>'
                                   '<div class="filters xlv"><span class="note">Levels:</span>' + "".join(f'<label><input type="checkbox" class="f-xl" value="{x}"> {x}</label>' for x in ("Intern", "Junior", "Senior", "Lead")) + '</div>'
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
    cmp_links = lambda t: labrow("Compare with", [f'<a href="{P}/{cmp_path(t, o)}">{e(o)}</a>' for o in CMP if o != t], ("compare/", "Any two skills")) if t in CMP else ""
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
                js, (f"<strong>{e(name)}</strong>: {e(skills_info.CATEGORIES[s])}. " if s in skills_info.CATEGORIES else "") + intro_for(js, f"{e(name)} ", hub=True), trail=(("All jobs", "jobs/"),), feed=True, extra=sponsor_line("category:" + s) + hub_stats(js) + rel(REL["cat:" + s], ("categories/", "All categories")) + hub_sections(f"{name} roles", js)[0], faq=f"{name} jobs",
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
    BROAD = {"analyst", "coordinator", "director", "executive", "growth", "intern", "staff-engineer", "founding-team", "bilingual", "government", "energy", "payments", "consulting", "operators"}
    # Crypto: the hub answers the search "crypto jobs" (and "web3 jobs", "blockchain jobs"), so it shows what these jobs pay, who
    # hires, and links to every narrower list people search for by name: by kind, by profession, by place.
    crypto = [j for j in active if j.get("crypto")]
    if crypto:
        ctrail = (("Crypto jobs", "crypto/"),)
        ckinds, croles, cplaces = [], [], []
        def cadd(bucket, path, h1, js, desc, pre="", post=" at crypto and web3 companies", least=5, label=None):
            if len(js) < least: return
            listing(path, h1, f"{h1} ({len(js):,} open) | {SITE}", desc.format(n=roles(len(js), "open job")), js, intro_for(js, pre, post), trail=ctrail, max_pages=3, more=False,
                    faq=h1[0].lower() + h1[1:])
            bucket.append((path, label or h1, len(js)))
        cadd(ckinds, "crypto/remote/", "Remote crypto jobs", [j for j in crypto if j["remote"]], "{n} at crypto and web3 companies that can be done from home. Updated hourly.", "remote ")
        cadd(ckinds, "crypto/new/", "New crypto jobs", [j for j in crypto if (j["posted"] or "") >= cut3], "{n} at crypto and web3 companies posted in the last three days.", "", " at crypto and web3 companies posted in the last 3 days")
        cadd(ckinds, "crypto/with-salary/", "Crypto jobs with salary", [j for j in crypto if j["salary"]], "{n} at crypto and web3 companies where the employer states the pay.", "", " at crypto and web3 companies with a published salary range")
        cadd(ckinds, "crypto/entry-level/", "Entry-level crypto jobs", [j for j in crypto if j["entry"]], "{n} at crypto and web3 companies that ask for little or no experience.", "entry-level ")
        cadd(ckinds, "crypto/internships/", "Crypto internships", [j for j in crypto if j.get("etype") == "Internship"], "{n}: internships at crypto and web3 companies.", "internship ")
        cadd(ckinds, "crypto/work-from-anywhere/", "Crypto jobs open to any country", [j for j in crypto if j.get("anywhere")], "{n} at crypto and web3 companies that do not tie the job to one country.", "", " at crypto and web3 companies open to any country")
        for s_, (nm, rj) in by_role.items():
            if s_ in BROAD or s_.endswith("-speaking"): continue
            own = s_ in ("blockchain-engineer", "smart-contract-engineer", "trader")       # the name already says crypto
            cadd(croles, f"crypto/roles/{s_}/", (f"{nm} jobs" if own else f"Crypto {rlow(nm)} jobs"), [j for j in rj if j.get("crypto")],
                 "{n} for " + rlow(nm).replace("{", "").replace("}", "") + " work at crypto and web3 companies: exchanges, wallets, infrastructure and DeFi.", f"{e(rlow(nm))} ", least=10, label=nm)
        for name, slug, pj in places:
            short = name.removeprefix("the ")
            cadd(cplaces, f"crypto/in/{slug}/", f"Crypto jobs in {short}", [j for j in pj if j.get("crypto")], "{n} at crypto and web3 companies in " + name + ".", "", f" at crypto and web3 companies in {e(name)}", least=10, label=short)
        croles.sort(key=lambda x: -x[2]); cplaces.sort(key=lambda x: -x[2])
        cdir = lambda title, rows_: (f'<div class="dirb"><h2><span>{e(title)}</span><span>{len(rows_)}</span></h2><ul>'
                                     + "".join(f'<li><a href="{P}/{u}">{path_fl(u)}{e(nm)}</a><span>{k:,} jobs</span></li>' for u, nm, k in rows_) + "</ul></div>") if rows_ else ""
        ccats = "".join(tile(f"crypto/{s}/", CAT[s], c) for s in CAT if (c := sum(1 for j in crypto if j["cat"] == s)) >= 5)
        chire = "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in crypto).most_common(12))
        eng_pc = round(100 * sum(1 for j in crypto if j["cat"] == "engineering") / len(crypto))
        listing("crypto/", "Crypto jobs", f"Crypto Jobs: {len(crypto):,} Open Web3 and Blockchain Roles | {SITE}",
                f"{roles(len(crypto), 'open job')} at crypto, web3 and blockchain companies: exchanges, wallets, infrastructure and DeFi. Remote and on-site, with pay where the employer states it. Updated hourly.",
                crypto, intro_for(crypto, "", " at crypto, web3 and blockchain companies"),
                extra=mini_pics(crypto) + f'<ul class="tiles">{ccats}</ul>'
                + section("Who is hiring in crypto", f'<ul class="tiles">{chire}</ul>', ("companies/", "All companies"))
                + '<div class="dir">' + cdir("Kinds of crypto jobs", ckinds) + cdir("By profession", croles) + cdir("By place", cplaces) + "</div>"
                + '<div class="sec"><div class="sec-head"><h2>All crypto jobs</h2></div></div>', feed=True, faq="crypto jobs",
                faq_first=("What counts as a crypto job here?", f"A job at a company whose business is crypto, web3 or blockchain: exchanges, wallets, custody, blockchain infrastructure, DeFi and analytics. "
                           f"Of the {len(crypto):,} open today, {eng_pc}% are engineering jobs; the rest are in compliance, marketing, support, finance, design and other fields, so the list is not only for programmers."))
        for s, name in CAT.items():
            cj = [j for j in crypto if j["cat"] == s]
            if len(cj) >= 5:
                listing(f"crypto/{s}/", f"{name} jobs in crypto & web3", f"{name} Jobs in Crypto & Web3 ({len(cj):,} open) | {SITE}",
                        f"{roles(len(cj), name + ' job')} at crypto and web3 companies. Remote and on-site roles, updated hourly.",
                        cj, intro_for(cj, f"{e(name)} ", " at crypto and web3 companies"), trail=ctrail)
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
                trail=(("All jobs", "jobs/"),), feed=True, extra=sponsor_line("skill:" + tslug(t)) + hub_stats(js) + rel(REL["tag:" + t], ("skills/", "All skills")) + cmp_links(t) + hub_sections(f"{t} roles", js, "skills")[0], hub=hub_sections(f"{t} roles", js, "skills")[1], list_title=f"Newest {t} jobs",
                faq=f"{t} jobs", faq_first=((f"What is {t}?", f"{skills_info.plain(t)} {len(js):,} open roles on {SITE} ask for it as of {fdate(TODAY)}.") if t in skills_info.INFO else None),
                after=section(f"Companies hiring for {t}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in js).most_common(12)) + "</ul>",
                              (f"salaries/{tslug(t)}/", f"{t} salaries") if sum(1 for j in js if j["usd"]) >= 30 else None))
    # Which kinds of work sit close to each other: two roles are neighbours when employers ask for the same skills in both.
    has_rex = lambda s_: (s_ == "intern" or s_ not in BROAD) and not s_.endswith("-speaking")
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
        fam_line = (labrow("Part of", [f'<a href="{P}/categories/{fs}/">{e(fn)}</a>' for fs, fn in fams])
                    + (labrow("Resume", [f'<a href="{P}/resume/examples/{slug_r}/">An example for this work</a>'], ("resume/examples/", "All examples")) if has_rex(slug_r) else "")
                    + (labrow("Prepare", [f'<a href="{P}/interview-questions/{slug_r}/">Interview questions</a>', f'<a href="{P}/cover-letter-examples/{slug_r}/">Cover letter example</a>',
                                          f'<a href="{P}/how-to-become/{slug_r}/">How to become one</a>']) if has_rex(slug_r) and len(rj) >= 20 else "")) if fams else ""
        secs = hub_sections(f"{low} roles", rj, "roles")
        listing(f"roles/{slug_r}/", f"{rname} jobs", f"{tcase(rname)} Jobs ({len(rj):,} open) | {SITE}",
                f"{roles(len(rj), 'open role')} for {many}, straight from employers’ careers pages." + (f" A person in this job {w_}." if w_ else "") + " Remote filter, salary data, updated hourly.",
                rj, (f"<strong>{e(rname)}</strong>: a person in this job {e(w_)}. " if w_ else "") + intro_for(rj, "", f" with “{e(rname)}” or a close variant in the title", hub=True),
                trail=(("Categories", "categories/"),), feed=True, extra=hub_stats(rj) + mini_pics(rj) + fam_line + rel(REL["role:" + slug_r], ("roles/", "All roles")) + secs[0], faq=f"{low} jobs",
                faq_first=((f"What is {art(low)} {low} job?", f"In {art(low)} {low} job, a person {w_}. {len(rj):,} such roles are open on {SITE} as of {fdate(TODAY)}.") if w_ else None),
                hub=secs[1], list_title=f"Newest {low} jobs", more=None if slug_r in ROLE_BASE else False,
                after=neighbours(slug_r) + section(f"Companies hiring {many}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in rj).most_common(12)) + "</ul>",
                              (f"salaries/{slug_r}/", f"{rname} salary") if paid_r >= 20 else None))

    # Lists by when the work is done. People search these by the hours, not by the profession: "night shift jobs", "weekend jobs", "summer jobs".
    HOURS = [(p_, h_, w_, js_) for p_, h_, rx_, w_ in (
        ("night-shift/", "Night shift jobs", r"night shift|overnight|3rd shift|third shift|graveyard|\bnights\b|2nd shift|second shift|swing shift|evening shift", "evening or night shifts"),
        ("weekend/", "Weekend jobs", r"weekend", "weekend work"),
        ("summer/", "Summer jobs and internships", r"\bsummer\b", "the summer months"),
        ("temporary/", "Temporary and seasonal jobs", r"seasonal|temporary|\btemp\b|fixed[- ]term", "a fixed term or a season"))
        if len(js_ := [j for j in active if re.search(rx_, j["title"] + " " + (j["excerpt"] or ""), re.I)]) >= 20]
    for p_, h_, w_, js_ in HOURS:
        listing(p_, h_, f"{h_} ({len(js_):,} open) | {SITE}", f"{roles(len(js_), 'open job')} whose posting names {w_}, straight from employers’ careers pages. Updated hourly.", js_,
                intro_for(js_, "", f" whose posting names {w_}"), trail=(("All jobs", "jobs/"),))
    # Hybrid: some days at home, some in the office (FlexJobs shows it as its own kind of work; the search has the same filter)
    hyb_ = [j for j in active if j.get("hybrid")]
    if len(hyb_) >= 20:
        listing("hybrid/", "Hybrid jobs", f"Hybrid Jobs ({len(hyb_):,} open) | {SITE}",
                f"{roles(len(hyb_), 'open job')} that mix days at home with days in the office, straight from employers’ careers pages. Updated hourly.", hyb_,
                intro_for(hyb_, "", " that mix days at home with days in the office"), trail=(("All jobs", "jobs/"),))
    # The directory: every category with the kinds of work in it, on one page, and a page with text for each category
    kinds = "".join(f'<li><a href="{P}/{u}">{e(nm)}</a></li>' for u, nm in (
        ("remote/", "Remote jobs"), ("hybrid/", "Hybrid jobs"), ("work-from-anywhere/", "Work from anywhere"), ("new/", "New in the last 3 days"), ("entry-level/", "Entry-level jobs"), ("internships/", "Internships"),
        ("contract/", "Contract jobs"), ("part-time/", "Part-time jobs"), ("with-salary/", "Jobs that state pay"), ("salary/200k/", "Jobs that pay $200K or more"), ("perks/visa-sponsorship/", "Jobs with visa sponsorship"),
        ("jobs-near-me/", "Jobs near me")) + tuple((p_, h_) for p_, h_, _, _ in HOURS))
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
        rank_ = (labrow("Ranking", [f'<a href="{P}/insights/companies-hiring-{fs}/">Companies hiring for {e(low_f)} jobs, with remote roles and pay</a>'], ("insights/", "All rankings"))
                 if len({j["company"] for j in js_}) >= 8 else "")
        others = rank_ + labrow("Other categories", [f'<a href="{P}/categories/{o}/">{e(on)}</a>' for o, on, _, _, _ in fam_rows if o != fs], ("categories/", "All categories"))
        secs = hub_sections(low_f, js_, "roles")
        vers = []
        for vslug, vname, vjs in (("remote", "Remote", [j for j in js_ if j["remote"]]), ("entry-level", "Entry-level", [j for j in js_ if j["entry"]])):
            if len(vjs) < 20: continue
            vers.append(f'<a href="{P}/categories/{fs}/{vslug}/">{vname} {e(low_f)} jobs ({len(vjs):,})</a>')
            listing(f"categories/{fs}/{vslug}/", f"{vname} {low_f} jobs", f"{vname} {tcase(fn)} Jobs ({len(vjs):,} open) | {SITE}",
                    f"{len(vjs):,} open {vname.lower()} jobs in {low_f}: {', '.join(rlow(x) for x in names_[:4])} and more. Read from employers’ own careers pages and checked against them.",
                    vjs, f"<strong>{e(fn)}</strong> is {e(fd)}. " + intro_for(vjs, f"{vname.lower()} ", "", hub=True), trail=(("Categories", "categories/"), (fn, f"categories/{fs}/")), per=50, max_pages=2, more=False,
                    extra=hub_stats(vjs), faq=f"{vname.lower()} {low_f} jobs")
        vers_line = labrow("Narrower lists", vers)
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
                js, intro_for(js, "", f" in {e(name)}", hub=True), trail=(("Locations", "locations/"),), extra=hub_stats(js) + rel(REL["place:" + slug], ("locations/", "All locations")) + hub_sections(f"tech roles in {short}", js, "places")[0], faq=f"tech jobs in {name}", feed=True,
                hub=hub_sections(f"tech roles in {short}", js, "places")[1], list_title=f"Newest tech jobs in {short}")
    rule_of = {slug: rule for _, slug, rule in PLACES}
    WORLD = (("North America", {"US", "CA"}), ("Europe", REGIONS["europe"][0]), ("Asia-Pacific", REGIONS["asia-pacific"][0]), ("Latin America", REGIONS["latin-america"][0]))
    def world(code): return next((nm for nm, codes in WORLD if code in codes), "Middle East and Africa")
    lrow = lambda name, slug, js: (f'<li data-n="{e(name.lower())}"><a href="{P}/locations/{slug}/">{pfl(slug)}{e(name.removeprefix("the "))}</a><span>{len(js):,} jobs'
                                   + (f' · {sum(j["remote"] for j in js):,} remote' if any(j["remote"] for j in js) else "") + "</span></li>")
    lgroups = defaultdict(list)
    for name, slug, js in places:
        r_ = rule_of.get(slug)
        lgroups[world(r_) if isinstance(r_, str) and r_ != "region" else "Parts of the world" if r_ == "region" else "Cities and states"].append((name, slug, js))
    lorder = [nm for nm, _ in WORLD] + ["Middle East and Africa", "Parts of the world", "Cities and states"]
    ldir = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(g)}</span><span>{len(lgroups[g])}</span></h2><ul>' + "".join(lrow(*x) for x in sorted(lgroups[g], key=lambda x: -len(x[2]))) + "</ul></div>" for g in lorder if lgroups.get(g)) + "</div>"
    n_ctry = sum(len(lgroups[g]) for g in lorder[:5] if lgroups.get(g))
    ltop = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in sorted((x for g in lorder[:5] for x in lgroups.get(g, [])), key=lambda x: -len(x[2]))[:8])
    page("locations/", f"Jobs by Country: {n_ctry} Countries and {len(lgroups.get('Cities and states', []))} Cities | {SITE}",
         f"Choose a country: open jobs in {n_ctry} countries, each with the number that can be done from home. Also by part of the world and by city.",
         crumbs(("Locations", "")) + f'<h1>Jobs by country: <span class="hl">choose yours</span></h1>'
         f'<p class="lead">Open jobs in {n_ctry} countries, counted today. A job that lists several places appears in each of them. Jobs that are not tied to one country are under <a href="{P}/work-from-anywhere/">work from anywhere</a>.</p>'
         f'<ul class="tiles">{ltop}</ul>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a country or a city, for example Germany or Austin" aria-label="Find a place"></p>'
         f'<p class="lead" id="dirnone" hidden>No such place in today’s jobs. Try <a href="{P}/remote/">remote jobs</a> or the <a href="{P}/jobs/">search</a>.</p>' + ldir)

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
        careers_link = f'<a href="{FULL}/companies/{slug}/">Open roles at {c}</a>'
        embed = (f'<details class="embed"><summary>Work at {e(c)}? Link your careers page to this list</summary>'
                 '<p class="note">Three ways, simplest first. Each one stays up to date by itself, because this page is re-read from your careers page every hour.</p>'
                 f'<p class="flabel">1. A plain link for a “Careers” or “We’re hiring” menu item</p><pre><code>{e(careers_link)}</code></pre>'
                 f'<p class="flabel">2. A badge with today’s number of open roles</p><p><img src="{P}/badge/companies/{slug}.svg" alt="{e(c)} is hiring" height="28"></p>'
                 f'<pre><code>{badge_code(f"badge/companies/{slug}.svg", c + " is hiring", f"companies/{slug}/")}</code></pre>'
                 f'<p class="flabel">3. The list of jobs itself, shown on your page</p><pre><code>{embed_code("company:" + slug, "Jobs at " + c, f"companies/{slug}/")}</code></pre>'
                 f'<p class="note"><a href="{P}/widgets/">More widgets and badges</a></p></details>')
        stack = [t for t, _ in Counter(t for j in act for t in j["tags"]).most_common(10)]
        where = Counter(p_ for j in act for p_ in j["places"] if p_ in PLACE_LIVE).most_common(6)      # only places that have a page
        sim = sorted(((len(set(stack) & set(STACK[o])), OPEN[o], o) for o in STACK if o != c and len(set(stack) & set(STACK[o])) >= 4), reverse=True)[:6]
        overview = ""
        pay_by = {}
        for j in act:
            if j["usd"]: pay_by.setdefault(j["cat"], []).append(j["usd"])
        pay_rows = sorted(((k, v) for k, v in pay_by.items() if len(v) >= 3 and k != OTHER[0]), key=lambda kv: -len(kv[1]))[:8]
        if pay_rows:
            lo_all = min(lo for _, v in pay_rows for lo, _ in v); hi_all = max(hi for _, v in pay_rows for _, hi in v); span_ = max(1, hi_all - lo_all)
            def pay_row(k, v):
                lo_, hi_ = min(lo for lo, _ in v), max(hi for _, hi in v)
                mid_ = median([(a + b) / 2 for a, b in v]) if len(v) >= 15 else None
                bar = (f'<span class="prange"><i style="left:{100 * (lo_ - lo_all) / span_:.1f}%;width:{max(2, 100 * (hi_ - lo_) / span_):.1f}%"></i>'
                       + (f'<b style="left:{100 * (mid_ - lo_all) / span_:.1f}%"></b>' if mid_ else "") + "</span>")
                return (f'<tr><td><a href="{P}/jobs/{k}/">{e(CAT[k])}</a></td><td>{len(v)}</td><td>{money(lo_)} to {money(hi_)}</td>'
                        f'<td>{money(mid_) if mid_ else "—"}</td><td class="pcell">{bar}</td></tr>')
            overview += section(f"Pay by field at {c}", sid="pay", inner='<div class="tablewrap"><table><tr><th>Field</th><th>Postings with pay</th><th>Lowest to highest advertised</th><th>Median</th><th>Spread</th></tr>'
                                + "".join(pay_row(k, v) for k, v in pay_rows) + "</table></div>"
                                f'<p class="note">Pay ranges that {e(c)} printed in its open postings, converted to US dollars. A field needs 3 postings with pay to appear and 15 for a median. The line shows where the range sits; the tick marks the median.</p>')
        if stack:
            overview += section(f"Tech stack at {c}", sid="stack", inner='<div class="rel">' + "".join(f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a>' for t in stack) + "</div>"
                                '<p class="note">Skills mentioned most often across its open roles.</p>')
        if where:
            overview += section(f"Where {c} is hiring", '<div class="rel">' + "".join(f'<a href="{P}/locations/{p_}/">{pfl(p_)}{e(PLACE_NAME[p_])} · {k}</a>' for p_, k in where) + "</div>", sid="where")
        if sim:
            overview += section(f"Companies like {c}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(o)}/", o, OPEN[o], True) for _, _, o in sim) + "</ul>"
                                '<p class="note">Based on the skills they hire for.</p>', sid="similar")
        head_html = (crumbs(("Companies", "companies/"), (c, ""))
                     + f'<div class="jhead">{ava(c, "lg")}<div><h1>Jobs at {e(c)}</h1><span class="js">{lead}</span>'
                     + f'<p style="margin:12px 0 0"><button class="btn ghost sm" id="follow" type="button" data-slug="{slug}" data-name="{e(c)}" style="margin-top:0">Follow {e(c)}</button> '
                       f'<span class="note">Get a “new roles” count for this company in My jobs.</span></p></div></div>'
                     + (f'<dl class="facts">{"".join(chips)}</dl>' if act else "")
                     + '<nav class="anch" aria-label="On this page">' + (f'<a href="#jobs">Jobs <b>{len(act):,}</b></a>' if act else "")
                     + ('<a href="#pay">Pay</a>' if pay_rows else "") + ('<a href="#stack">Tech stack</a>' if stack else "") + ('<a href="#where">Locations</a>' if where else "") + ('<a href="#similar">Similar companies</a>' if sim else "")
                     + (f'<a href="#closed">Closed <b>{len(arc):,}</b></a>' if arc else "") + '</nav><div id="jobs"></div>')
        listing(f"companies/{slug}/", f"Jobs at {c}", f"{c} Careers: {roles(len(act), 'open job')} today | {SITE}",
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
        name = lambda k: (path_icon(link(k)) + '<a href="' + P + "/" + link(k) + '">' + path_fl(link(k)) + e(k) + "</a>") if link else e(k)
        mx_ = max((r[1] for r in rows_), default=1) or 1
        body_ = "".join(f'<tr><td>{name(k)}</td><td class="salbar"><strong>{money(m_)}</strong><span class="bar"><i style="width:{max(4, round(100 * m_ / mx_))}%"></i></span></td><td>{c:,}</td></tr>' for k, m_, c in rows_)
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
         crumbs(("Salaries", "")) + '<h1>Tech salaries from <span class="hl">live job postings</span></h1>'
         f'<p class="lead">{100 - SALPCT}% of open tech postings do not state a salary, which leaves candidates guessing. These figures come from the {len(paid):,} open roles that do publish a yearly US-dollar range. '
         f'Each figure is a <a href="{P}/glossary/median/">median</a>: half of the postings advertise more than it, half less. These are advertised ranges, not what people are actually paid.</p>'
         + (lambda mids_: f'<div class="statrow"><div class="stat"><b>{money(median(mids_))}</b><span>median advertised salary</span></div>'
                          f'<div class="stat"><b>{money(mids_[len(mids_) // 4])} – {money(mids_[3 * len(mids_) // 4])}</b><span>middle half of roles</span></div>'
                          f'<div class="stat"><b>{SALPCT}%</b><span>of open postings state pay</span></div>'
                          f'<div class="stat"><b>{len(mids_):,}</b><span>roles counted today</span></div></div>')(sorted((lo + hi) / 2 for _, (lo, hi) in paid))
         + section("By category", table(g_cat, lambda k: f"salaries/{cat_slug[k]}/" if len(g_cat[k]) >= 30 and k != OTHER[1] else f"jobs/{cat_slug[k]}/", 10))
         + level_section("Tech salaries by level, intern to lead", paid)
         + section("By skill", table(g_tag, lambda k: f"salaries/{TAG_SLUG.get(k, slugify(k))}/" if len(g_tag[k]) >= 30 else f"skills/{TAG_SLUG.get(k, slugify(k))}/"))
         + section("By company", table(g_comp, lambda k: f"companies/{slugify(k)}/", 8))
         + section("Highest-paying open roles", f'<ul class="jobs">{"".join(card(j) for j, _ in diverse_pairs(best, 30))}</ul>', ("with-salary/", "All jobs with salary"))
         + cite("salaries/", "Tech salaries from live job postings",
                f"Tech job postings that state pay advertise a median of {money(median([(lo + hi) / 2 for _, (lo, hi) in paid]))} a year; {100 - SALPCT}% of open postings state no pay at all. "
                f"Counted from {len(paid):,} open postings, {MONTH_YEAR}."))

    def salary_page(slug, label, group, back, role=False):
        by_loc = defaultdict(list)
        for j, r in group:
            for ps in j["places"]: by_loc[PLACE_NAME[ps]].append((j, r))
        cut = level_section(f"{label} salary by level", group) + \
              (section(f"{label} salary by location", table(by_loc, lambda k: f"locations/{PLACE_SLUG[k]}/", 15, 20)) if sum(len(v) >= 15 for v in by_loc.values()) >= 2 else "")
        mids = sorted((lo + hi) / 2 for _, (lo, hi) in group)
        mean_ = sum(mids) / len(mids)
        pct = lambda q: mids[min(len(mids) - 1, int(len(mids) * q))]
        comp = defaultdict(list)
        for j, r in group: comp[j["company"]].append((j, r))
        stats = (f'<div class="statrow"><div class="stat"><b>{money(median(mids))}</b><span>median advertised salary</span></div>'
                 f'<div class="stat"><b>{money(pct(.25))} – {money(pct(.75))}</b><span>middle half of roles</span></div>'
                 f'<div class="stat"><b>{money(mean_)}</b><span>average advertised salary</span></div><div class="stat"><b>{len(mids):,}</b><span>roles counted</span></div></div>')
        top_jobs = diverse_pairs(sorted(group, key=lambda x: -x[1][1]), 20)
        # People type "average <job> salary" and writers quote the answer: the page states it in words, as questions, and for search engines.
        best_c = sorted(((median([(lo + hi) / 2 for _, (lo, hi) in v]), k) for k, v in comp.items() if len(v) >= 3), reverse=True)[:3]
        sal_qa = [(f"What is the average {label} salary?", f"{money(mean_)} a year on average and {money(median(mids))} at the median, across {len(mids):,} open {label} postings at tech companies that state pay "
                   f"({MONTH_YEAR}). The median is the better guide: a few very high offers pull the average up."),
                  ("What is the typical range?", f"The middle half of the postings offer {money(pct(.25))} to {money(pct(.75))} a year. A quarter offer less and a quarter offer more."),
                  ("Where do these figures come from?", "From the pay ranges employers print in their own job postings, read from their careers pages every hour. The midpoint of each range is counted. "
                   "These are advertised ranges for open roles, mostly in the United States and in US dollars, not what people are actually paid.")]
        if best_c:
            sal_qa.insert(2, (f"Which companies advertise the highest {label} pay?", ", ".join(f"{k} ({money(m_)})" for m_, k in best_c) + ", by the median of their open postings that state pay (three postings or more)."))
        sal_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in sal_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        if role:      # a kind of work, so the page can also be read as an occupation with its pay
            sal_ld += ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Occupation", "name": label,
                "description": f"Advertised pay for {label} roles at tech companies, from {len(mids):,} open job postings that state a yearly range in US dollars.",
                "mainEntityOfPage": {"@type": "WebPage", "url": f"{FULL}/salaries/{slug}/", "lastReviewed": TODAY},
                "estimatedSalary": [{"@type": "MonetaryAmountDistribution", "name": "base", "currency": "USD", "duration": "P1Y",
                                     "percentile25": round(pct(.25)), "median": round(median(mids)), "percentile75": round(pct(.75))}]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        # the figures are the reason to click, so they stay in the title and the site name gives way (a title holds about 65 characters)
        t_long = f"{label} Salary: {money(mean_)} Average, {money(median(mids))} Median ({datetime.date.fromisoformat(TODAY).strftime('%b %Y')})"
        page(f"salaries/{slug}/", t_long if len(t_long) <= 65 else f"{label} Salary: {money(mean_)} Average, {money(median(mids))} Median",
             f"The average {label} salary at tech companies is {money(mean_)} a year and the median {money(median(mids))}; the middle half of postings offer {money(pct(.25))} to {money(pct(.75))}. "
             f"Counted from {len(mids):,} open job postings that state pay.",
             crumbs(("Salaries", "salaries/"), (label, "")) + f'<h1>{e(label)} salary: <span class="hl">{money(median(mids))} median</span></h1>'
             f'<p class="lead">From {len(mids):,} open roles that publish a yearly US-dollar range. Advertised ranges, not verified pay.</p>{stats}'
             + cut + section("Top-paying companies", table(comp, lambda k: f"companies/{slugify(k)}/", 3, 25))
             + section(f"Highest-paying open {label} roles", f'<ul class="jobs">{"".join(card(j) for j, _ in top_jobs)}</ul>', back)
             + section(f"Questions about {label} pay", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in sal_qa) + "</dl>")
             + cite(f"salaries/{slug}/", f"{label} salaries in tech",
                    f"The median advertised salary for {label} roles at tech companies is {money(median(mids))} a year, and the middle half of postings offer {money(pct(.25))} to {money(pct(.75))}. "
                    f"Counted from {len(mids):,} open job postings that state pay, {MONTH_YEAR}."), head=sal_ld)
    for t, group in g_tag.items():
        if len(group) >= 30:
            salary_page(TAG_SLUG.get(t, slugify(t)), t, group, (f"skills/{TAG_SLUG.get(t, slugify(t))}/", f"All {t} jobs"))
    for name, group in g_cat.items():
        if len(group) >= 30 and name != OTHER[1]:
            salary_page(cat_slug[name], name, group, (f"jobs/{cat_slug[name]}/", f"All {name} jobs"))
    for slug_r, (rname, rj) in by_role.items():
        group = [(j, j["usd"]) for j in rj if j["usd"]]
        if len(group) >= 20: salary_page(slug_r, tcase(rname), group, (f"roles/{slug_r}/", f"All {rlow(rname)} jobs"), role=True)      # 20 postings with pay is enough for a median; the page states the count

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
    place_rows = [trow([f'<a href="{P}/locations/{slug}/">{pfl(slug)}{e(name.removeprefix("the "))}</a>', f"{len(js):,}", barc(len(js), max(len(x[2]) for x in places), pctf(len(js), n))]) for name, slug, js in sorted(places, key=lambda x: -len(x[2]))]
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
             + section(f"Questions about {A['name']} and {B['name']} jobs", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
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
         + section("For job search engines", f'<p>One XML file with the jobs posted in the last 30 days, the newest first: <a href="{P}/feeds/jobs.xml"><code>{FULL}/feeds/jobs.xml</code></a>. '
                   'Each job carries its number, title, employer, place, country, date, pay where stated, the opening lines and the address of its page here. It is rebuilt every hour. '
                   'Job search engines may read it once an hour and must link each job to its page on this site.</p>')
         + section("Every feed", feed_dir)
         + section("Questions about job feeds", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in feed_qa) + "</dl>")
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

    pc_ = lambda a_, b_: round(100 * a_ / max(1, b_))
    def bars_(rows_, unit=""):                     # [(label, value, shown text, link)]
        mx_ = max((r_[1] for r_ in rows_), default=0) or 1
        return '<div class="hbars chart">' + "".join(
            f'<a href="{P}/{u_}"><span class="hn">{e(lab)}</span><span class="hb"><i style="width:{max(2, round(100 * v_ / mx_))}%"></i></span><span class="hc">{e(txt)}</span></a>' for lab, v_, txt, u_ in rows_) + "</div>"
    # Resume examples: one page per kind of work, with the skills employers name in today's postings for it and an invented
    # example that opens in the builder. See resume_examples.py.
    rex_data, rex_dir = {}, defaultdict(list)
    fam_of = {}
    for fs, fn, fd, live, js_ in fam_rows:
        for s_, _, _ in live: fam_of.setdefault(s_, (fs, fn))
    def paper(d):
        return ('<div class="paper"><p class="pp-name">' + e(d["name"]) + '</p><p class="pp-title">' + e(d["title"]) + '</p><p class="pp-contact">' + e(d["place"]) + " · " + e(d["email"]) + "</p>"
                '<p class="pp-h">Summary</p><p>' + e(d["summary"]) + '</p><p class="pp-h">Skills</p><p>' + e(d["skills"]) + '</p><p class="pp-h">Experience</p>'
                + "".join(f'<p class="pp-job"><b>{e(x["role"])}</b>, {e(x["org"])} <span>{e(x["dates"])}</span></p><ul>' + "".join(f"<li>{e(ln)}</li>" for ln in x["text"].split("\n")) + "</ul>" for x in d["exp"])
                + '<p class="pp-h">Education</p>' + "".join(f'<p class="pp-job"><b>{e(x["what"])}</b>, {e(x["org"])} <span>{e(x["dates"])}</span></p>' for x in d["edu"]) + "</div>")
    for slug_r, (rname, rj) in by_role.items():
        if not has_rex(slug_r): continue
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low = rlow(rname)
        cnt_ = Counter(t for j in rj for t in j["tags"])
        top_ = resume_examples.asked(slug_r, cnt_.most_common(), len(rj))
        tech_ = slug_r in resume_examples.TECH
        d = resume_examples.example(slug_r, rname, fs, top_, rlow(fn))
        skills_ = d["skills"].split(", ")
        if slug_r not in resume_examples.ROLE: print(f"  resume example: no entry of its own for {slug_r}, the lines of its field are used")
        rex_data[slug_r] = d
        rex_dir[fs].append((slug_r, rname, len(rj)))
        titles_ = [t for t, _ in Counter(j["title"] for j in rj).most_common(40) if len(t) <= 60][:6]
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"]]
        facts_ = [("Open jobs today", f"{len(rj):,}"), ("Can be done from home", f"{pc_(sum(j['remote'] for j in rj), len(rj))}%")] + ([("Median advertised pay", money(median(mids_)))] if len(mids_) >= 30 else [])
        chart_ = bars_([(t, k, f"{k:,} jobs · {pc_(k, len(rj))}%", f"skills/{tslug(t)}/") for t, k in top_]) if top_ else ""
        if tech_ and top_:
            ask_ = "<h2>What employers ask for</h2><p>The skills named most often in today’s postings for this work. Name the ones you have, by these words: screening software looks for the word.</p>" + chart_
        elif len(top_) >= 2:
            ask_ = ("<h2>Tools employers name</h2><p>Postings for this work describe duties more than tools. These are the tools they do name; put on the resume the ones you have used.</p>" + chart_)
        else:
            ask_ = "<h2>What employers ask for</h2><p>Postings for this work rarely name tools. They describe duties, so show results in the same words the posting uses for its duties.</p>"
        qa_ = [(f"Which skills should {art(low)} {low} resume list?",
                (f"The ones employers name most in open postings: {', '.join(t for t, _ in top_[:6])}. List those you really have, in these words." if tech_ and top_ else
                 f"What the work consists of: {', '.join(skills_[:5])}. Postings for this work describe duties more than tools, so use the posting’s own words for each duty and put a result next to it.")),
               ("How long should it be?", "One page for up to ten years of experience, two at most. The first third of the first page decides whether the rest is read."),
               ("Is this example a real person?", "No. The name, the employers and the numbers are invented to show the form: a verb first, one result, one number. Replace every line with your own.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        w_ = roles_info.INFO.get(slug_r, ("", ""))[1]
        page(f"resume/examples/{slug_r}/", f"{tcase(rname)} Resume Example | {SITE}",
             (f"{art(low).capitalize()} {low} resume example with the skills employers name in {len(rj):,} open postings today: {', '.join(t for t, _ in top_[:5])}. Open it in the free builder and make it yours." if tech_ and top_ else
              f"{art(low).capitalize()} {low} resume example with measured results, next to what {len(rj):,} open postings for this work offer today. Open it in the free builder and make it yours."),
             crumbs(("Resume builder", "resume/"), ("Examples", "resume/examples/"), (rname, "")) + f"<h1>{e(rname)} resume example</h1>"
             f'<p class="lead">' + (f"A person in this job {e(w_)}. " if w_ else "") + f"Below: an example to start from, and what {len(rj):,} open postings for this work ask for today.</p>"
             '<div class="rexgrid"><div>' + paper(d) + '<p class="note">Example. The person, the employers and the numbers are invented; replace them with yours.</p>'
             f'<p><a class="btn primary" href="{P}/resume/?example={slug_r}">Open this example in the builder</a> <a class="btn ghost" style="margin-top:0" href="{P}/tools/resume-review/">Check your own resume</a></p></div>'
             '<div class="rexside"><div class="invf">' + "".join(f"<div><b>{e(v_)}</b><span>{e(k_)}</span></div>" for k_, v_ in facts_) + "</div>" + ask_
             + ("<h2>Titles employers use</h2><p>" + e("; ".join(titles_)) + ".</p>" if titles_ else "")
             + '<h2>Make it yours</h2><ol class="steps"><li><b>Keep the form, change every fact.</b> A verb first, what changed, one number.</li>'
               f'<li><b>Use the posting’s words.</b> The <a href="{P}/tools/resume-match/">match checker</a> shows which of them your resume lacks.</li>'
               f'<li><b>Put the strongest result first.</b> The <a href="{P}/tools/resume-review/">resume review</a> tells you what a first read finds.</li></ol></div></div>'
             + section(f"Questions about {art(low)} {low} resume", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
             + f'<p class="note cmpl">Next: <a href="{P}/roles/{slug_r}/">{len(rj):,} open {e(low)} jobs</a> · <a href="{P}/resume/examples/">all resume examples</a> · <a href="{P}/resume/">the resume builder</a></p>', head=ld_)
    write("data/resume-examples.json", json.dumps(rex_data, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    rex_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(rex_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/resume/examples/{s_}/">{e(nm)}</a><span>{k:,} jobs</span></li>' for s_, nm, k in rex_dir[fs]) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if rex_dir.get(fs)) + "</div>"
    page("resume/examples/", f"Resume Examples for {len(rex_data)} Kinds of Work | {SITE}",
         f"{len(rex_data)} resume examples, each with the skills employers name in today’s open postings for that work. Open any of them in the free resume builder.",
         crumbs(("Resume builder", "resume/"), ("Examples", "")) + f'<h1>Resume examples for <span class="hl">{len(rex_data)} kinds of work</span></h1>'
         '<p class="lead">Each example comes with the skills employers name for that work in today’s open postings, counted again at every update. Pick your work, open the example in the builder and replace it line by line.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, accountant or designer" aria-label="Find an example"></p>'
         f'<p class="lead" id="dirnone" hidden>No example with these words. The <a href="{P}/resume/">resume builder</a> works for any job.</p>' + rex_html)

    # Cover letter examples, one per kind of work (the Rezi study: cover letter pages bring that site 6% of its search visits).
    # Each letter is built from the results in that work's resume example, so the two match; the page adds what today's postings say.
    CL_RX = re.compile(r"cover[\s-]*letter", re.I)
    cl_dir = defaultdict(list)
    for slug_r, d in rex_data.items():
        rname, rj = by_role[slug_r]
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low = rlow(rname)
        lines_ = [ln.strip() for ln in (d["exp"][0]["text"] if d["exp"] else "").split("\n") if ln.strip()][:2]
        cnt_ = Counter(t for j in rj for t in j["tags"])
        top_ = [t for t, _ in resume_examples.asked(slug_r, cnt_.most_common(), len(rj))][:3]
        tech_ = slug_r in resume_examples.TECH
        letter_ = ("Dear Hiring Manager,\n\n"
                   f"I am applying for the {d['title']} position at [Company]. I have [number] years of experience as {art(low)} {low}, most recently at [Current company], "
                   f"where my focus is {d.get('focus') or resume_examples.ROLE.get(slug_r, (None, 'the core of the role'))[1]}.\n\n"
                   + ("Two results from that work:\n" + "\n".join(f"- {ln}" for ln in lines_) + "\n\n" if lines_ else "")
                   + "[One or two sentences on why this company: a product you use, a goal from the posting, a problem you can help with.] "
                   + (f"I would bring the same focus on measurable results, and hands-on experience with {', '.join(top_[:-1]) + ' and ' + top_[-1] if len(top_) > 1 else top_[0]}, which the posting asks for.\n\n" if tech_ and top_
                      else "I would bring the same focus on measurable results to your team.\n\n")
                   + "I would welcome the chance to talk about how I can help. Thank you for your time.\n\nSincerely,\n[Your name]")
        descs_ = [j for j in rj if j.get("desc")]
        ask_cl = sum(1 for j in descs_ if CL_RX.search(j["desc"])) if len(descs_) >= 30 else None
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"]]
        cl_qa = [(f"What should {art(low)} {low} cover letter include?", f"Three things: the role you are applying for, one or two results from your {low} work with numbers, and one specific reason you want this company. "
                  + (f"Name the skills the posting names; for this work the most frequent today are {', '.join(top_)}." if top_ else "Use the words the posting uses for its duties.")),
                 (f"Do {low} jobs ask for a cover letter?", ((f"Only {ask_cl} of the {len(descs_):,} open {low} postings with a full description here mention a cover letter in their text" if ask_cl else f"None of the {len(descs_):,} open {low} postings with a full description here mention a cover letter in their text")
                                                              + " (counted today). The application form often has a separate field for one: when it does, a short letter still helps."
                                                              if ask_cl is not None else "Many postings make it optional. A short letter still helps when the application form has a place for it.")),
                 (f"How long should {art(low)} {low} cover letter be?", "Three short paragraphs, under 250 words: a screen without scrolling. Recruiters read the first lines and the results; everything else is skipped.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in cl_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = (f'<dl class="facts"><div><dt>Open {e(low)} jobs today</dt><dd>{len(rj):,}</dd></div><div><dt>Can be done from home</dt><dd>{pc_(sum(j["remote"] for j in rj), len(rj))}%</dd></div>'
                  + (f'<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>' if len(mids_) >= 30 else "") + "</dl>")
        cl_dir[fs].append((slug_r, rname, len(rj)))
        page(f"cover-letter-examples/{slug_r}/", f"{tcase(rname)} Cover Letter Example ({TODAY[:4]}) | {SITE}",
             f"A {low} cover letter example built around measured results, with what today’s {len(rj):,} open {low} postings ask for. Copy it and fill in the brackets.",
             crumbs(("Cover letter examples", "cover-letter-examples/"), (rname, "")) + f'<h1>{e(rname)} cover letter example: <span class="hl">results first</span></h1>'
             f'<p class="lead">A cover letter for {e(low)} jobs that leads with what you achieved, not with what you were responsible for. Copy it, replace the parts in [brackets] and use the words of the posting you answer.</p>'
             + facts_
             + f'<div class="rl-paper"><pre id="letter">{e(letter_)}</pre><p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the letter</button> '
               f'<a class="btn ghost sm" href="{P}/tools/cover-letter/" style="margin-top:0">Write yours with the free builder</a></p></div>'
             + section(f"Questions about {art(low)} {low} cover letter", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in cl_qa) + "</dl>")
             + section("Use it with", '<div class="feats">'
                       f'<a class="feat" href="{P}/resume/examples/{slug_r}/"><h3>The {e(low)} resume example</h3><p>The same results, laid out as a one-page resume you can open in the builder.</p></a>'
                       f'<a class="feat" href="{P}/tools/resume-match/"><h3>Check against a posting</h3><p>See which of the posting’s words your resume and letter are missing.</p></a>'
                       f'<a class="feat" href="{P}/roles/{slug_r}/"><h3>{len(rj):,} open {e(low)} jobs</h3><p>Read from employers’ own careers pages every hour.</p></a></div>'), head=ld_)
    cl_n = sum(len(v) for v in cl_dir.values())
    cl_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(cl_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/cover-letter-examples/{s_}/">{e(nm)}</a><span>{k:,} jobs</span></li>' for s_, nm, k in sorted(cl_dir[fs], key=lambda x: -x[2])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if cl_dir.get(fs)) + "</div>"
    page("cover-letter-examples/", f"Cover Letter Examples for {cl_n} Kinds of Work ({TODAY[:4]}) | {SITE}",
         f"{cl_n} cover letter examples, one for each kind of work, built around measured results and the skills today’s open postings ask for. Copy one or write yours in the free builder.",
         crumbs(("Cover letter examples", "")) + f'<h1>Cover letter examples for <span class="hl">{cl_n} kinds of work</span></h1>'
         f'<p class="lead">Each letter leads with two results from that work and names the skills employers ask for in today’s open postings. Pick your work, copy the letter and fill in the brackets, or write your own in the <a href="{P}/tools/cover-letter/">cover letter builder</a>.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, accountant or designer" aria-label="Find an example"></p>'
         f'<p class="lead" id="dirnone" hidden>No example with these words. The <a href="{P}/tools/cover-letter/">cover letter builder</a> works for any job.</p>' + cl_html)

    # Job description templates for employers, one per kind of work (the Careerist/PeopleForce study: PeopleForce has none, and
    # employers search for them). Every figure is counted from today's open postings for that work; the text is a template with
    # brackets, written for this site, never copied from a posting.
    jd_dir = defaultdict(list)
    for slug_r, d in rex_data.items():
        rname, rj = by_role[slug_r]
        if len(rj) < 20: continue
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low, n_ = rlow(rname), len(rj)
        does = (roles_info.INFO.get(slug_r) or (None, ""))[1]
        focus = [x.strip() for x in (resume_examples.ROLE.get(slug_r, (None, ""))[1] or "").split(",") if x.strip()][:4]
        yrs = sorted(j["years"] for j in rj if j.get("years"))
        y_med = yrs[len(yrs) // 2] if len(yrs) >= 10 else None
        mids_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"])
        paid_pct = pc_(sum(1 for j in rj if j["salary"]), n_)
        q_ = lambda q: mids_[min(len(mids_) - 1, int(len(mids_) * q))]
        cnt_ = Counter(t for j in rj for t in j["tags"])
        top_ = [(t, k) for t, k in resume_examples.asked(slug_r, cnt_.most_common(), n_)][:4]
        perk_ = Counter(x for j in rj for x in j.get("perks", []) if x != "No degree required").most_common(3)      # a requirement, not a benefit
        rem_pct = pc_(sum(1 for j in rj if j["remote"]), n_)
        lvl_ = Counter(j["level"] for j in rj if j["level"]).most_common(1)
        titles_ = [t for t, _ in Counter(j["title"] for j in rj).most_common(60) if len(t) <= 50][:6]
        tpl = (f"{d['title']}\n[Company] · [City, or Remote and the countries it is open to] · [Full-time]\n\n"
               "About us\n[Two sentences: what the company does, for whom, and one number that shows where it is now.]\n\n"
               + (f"About the role\nOur {d['title']} {does}. " if does else "About the role\n[What this person is hired to do, in one sentence.] ") + "You will report to [manager’s title] and work with [team].\n\n"
               "What you will do\n- [The most important result of the first year, with a number]\n"
               + "".join(f"- {x[0].upper() + x[1:]}: [what this means in your team]\n" for x in focus)
               + "- [One more duty that is specific to this job]\n\n"
               "What we are looking for\n"
               + (f"- [{y_med}]+ years of experience as {art(low)} {low}\n" if y_med else f"- [Number]+ years of experience as {art(low)} {low}\n")
               + "".join(f"- Experience with {t}\n" for t, _ in top_)
               + "- [One or two must-haves that are specific to this job]\n\n"
               "Pay and benefits\n- Pay range: $[lowest] – $[highest] a year, [plus equity or bonus if any]\n"
               + "".join(f"- {x}\n" for x, _ in perk_)
               + "- [Paid time off, health cover and the rest of your benefits]\n\n"
               "How to apply\n[What to send, the interview steps and how long they take. Name the date you will reply by.]")
        facts_ = ('<dl class="facts">' + f"<div><dt>Open postings today</dt><dd>{n_:,}</dd></div>"
                  + (f"<div><dt>Experience asked, median</dt><dd>{y_med} years</dd></div>" if y_med else "")
                  + f"<div><dt>Postings that state pay</dt><dd>{paid_pct}%</dd></div>"
                  + (f"<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>" if len(mids_) >= 20 else "")
                  + f"<div><dt>Open to remote work</dt><dd>{rem_pct}%</dd></div></dl>")
        data_rows = ([("Experience asked", f"Median {y_med} years; the middle half ask {yrs[len(yrs) // 4]}–{yrs[3 * len(yrs) // 4]} years ({len(yrs):,} postings name a number)")] if y_med else []) + \
                    ([("Pay advertised", f"{money(q_(.25))} – {money(q_(.75))} for the middle half; median {money(median(mids_))} ({len(mids_):,} postings with a yearly US-dollar range)")] if len(mids_) >= 20 else []) + \
                    ([("Skills named most", ", ".join(f"{t} ({pc_(k, n_)}%)" for t, k in top_))] if top_ else []) + \
                    ([("Benefits named most", ", ".join(f"{x} ({pc_(k, n_)}%)" for x, k in perk_))] if perk_ else []) + \
                    ([("Most common level", f"{lvl_[0][0]} ({pc_(lvl_[0][1], n_)}% of postings)")] if lvl_ else []) + \
                    ([("Titles employers use", ", ".join(titles_))] if titles_ else [])
        jd_qa = [(f"What should {art(low)} {low} job description include?", "What the person will achieve in the first year, the duties, the must-have experience, the pay range and how the hiring steps work. "
                  + (f"For this work, today’s postings name {', '.join(t for t, _ in top_[:3])} most often." if top_ else "Use the words candidates search for, not internal team names.")),
                 (f"Should {art(low)} {low} job posting show the salary?", f"Yes, if you can: {paid_pct}% of today’s {n_:,} open {low} postings here do. A range filters out people who would turn the offer down, and several US states and EU countries now require it."),
                 (f"How many years of experience should I ask for?", (f"The median in today’s {low} postings is {y_med} years. Ask for what the work needs: every extra year you require shrinks the pool of applicants." if y_med
                  else "As few as the work really needs: every extra year you require shrinks the pool of applicants."))]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in jd_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        jd_dir[fs].append((slug_r, rname, n_))
        page(f"job-descriptions/{slug_r}/", f"{tcase(rname)} Job Description Template ({TODAY[:4]}) | {SITE}",
             f"A {low} job description template with the figures from {n_:,} open postings: experience asked, pay, skills and benefits employers name. Copy it and post your job free.",
             crumbs(("For employers", "post-a-job/"), ("Job descriptions", "job-descriptions/"), (rname, "")) + f'<h1>{e(rname)} job description: <span class="hl">template and real figures</span></h1>'
             f'<p class="lead">A template for hiring {art(low)} {e(low)}, with what employers in today’s {n_:,} open postings for this work ask for and offer. Copy it, fill in the brackets, then post the job free.</p>'
             + facts_
             + f'<div class="rl-paper"><pre id="letter">{e(tpl)}</pre><p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the template</button> '
               f'<a class="btn ghost sm" href="{P}/tools/job-description-checker/" style="margin-top:0">Check your description</a> <a class="btn ghost sm" href="{P}/post-a-job/" style="margin-top:0">Post the job free</a></p></div>'
             + section(f"What today’s {low} postings say", '<div class="tablewrap"><table>' + "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in data_rows) + "</table></div>"
                       f'<p class="note">Counted from the {n_:,} open postings for this work on {fdate(TODAY)}, read from employers’ own careers pages. Recounted on every update.</p>')
             + section(f"Questions about hiring {art(low)} {low}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in jd_qa) + "</dl>")
             + f'<p class="note cmpl">See also: <a href="{P}/roles/{slug_r}/">{n_:,} open {e(low)} jobs</a> · '
             + (f'<a href="{P}/salaries/{slug_r}/">{e(low)} pay</a> · ' if (OUT / "salaries" / slug_r / "index.html").exists() else "")      # a salary page exists only from 20 postings with pay
             + f'<a href="{P}/how-to-hire/{slug_r}/">how to hire {art(low)} {e(low)}</a> · <a href="{P}/job-descriptions/">all job description templates</a></p>', head=ld_)
    jd_n = sum(len(v) for v in jd_dir.values())
    jd_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(jd_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/job-descriptions/{s_}/">{e(nm)}</a><span>{k:,} postings</span></li>' for s_, nm, k in sorted(jd_dir[fs], key=lambda x: -x[2])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if jd_dir.get(fs)) + "</div>"
    page("job-descriptions/", f"Job Description Templates for {jd_n} Roles, with Real Pay and Skills Data | {SITE}",
         f"{jd_n} job description templates for employers, each with the experience, pay, skills and benefits named in today’s open postings for that work. Copy one and post your job free.",
         crumbs(("For employers", "post-a-job/"), ("Job descriptions", "")) + f'<h1>Job description templates for <span class="hl">{jd_n} roles</span></h1>'
         '<p class="lead">Each template comes with the figures from today’s open postings for that work: how many years employers ask for, what they pay, which skills and benefits they name. '
         f'Copy one, fill in the brackets, check it with the <a href="{P}/tools/job-description-checker/">job description checker</a> and post it free.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a role, for example nurse, accountant or designer" aria-label="Find a template"></p>'
         f'<p class="lead" id="dirnone" hidden>No template with these words. The <a href="{P}/tools/job-description-checker/">checker</a> works for any job description.</p>' + jd_html)

    # "How to become a <work>" for people changing careers (the Careerist study: that topic carries their whole blog). The steps are
    # the same advice for every work; what makes each page useful is counted from today's postings: how many are open to beginners,
    # how many years employers ask, the skills they name first, whether a degree is required, what juniors are paid.
    hb_dir = defaultdict(list)
    for slug_r, d in rex_data.items():
        rname, rj = by_role[slug_r]
        if len(rj) < 20: continue
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low, n_ = rlow(rname), len(rj)
        does = (roles_info.INFO.get(slug_r) or (None, ""))[1]
        begin = [j for j in rj if j["entry"] or (j.get("years") and j["years"] <= 2)]
        yrs = sorted(j["years"] for j in rj if j.get("years"))
        y_med = yrs[len(yrs) // 2] if len(yrs) >= 10 else None
        low_yrs = pc_(sum(1 for y in yrs if y <= 2), len(yrs)) if len(yrs) >= 10 else None
        nodeg = pc_(sum(1 for j in rj if "No degree required" in j.get("perks", [])), n_)
        jr_pay = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in begin if j["usd"])
        all_pay = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"])
        cnt_ = Counter(t for j in rj for t in j["tags"])
        top_ = resume_examples.asked(slug_r, cnt_.most_common(), n_)[:5]
        titles_ = [t for t, _ in Counter(j["title"] for j in begin).most_common(30) if len(t) <= 50][:5]
        lines_ = [ln.strip() for ln in (d["exp"][0]["text"] if d["exp"] else "").split("\n") if ln.strip()][:2]
        steps = ("<ol class=\"steps\">"
                 f"<li><b>Know what the work is.</b> {e(art(low).capitalize())} {e(low)} {e(does)}." + (f" Beginner postings today use titles like {e('; '.join(titles_))}." if titles_ else "") + "</li>"
                 + (f"<li><b>Learn the skills employers name first.</b> In today’s {n_:,} postings: " + ", ".join(f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a> ({pc_(k, n_)}%)' for t, k in top_) + ".</li>" if top_ else
                    "<li><b>Learn the duties, not only the tools.</b> Postings for this work describe what you will do more than which software you will use: read ten of them and list the duties that repeat.</li>")
                 + "<li><b>Build proof you can show.</b> Two or three results with a number, from a job, a course project or volunteer work. The kind of line a recruiter looks for: "
                 + (f"“{e(lines_[0])}”." if lines_ else "a result with a number.") + "</li>"
                 + f'<li><b>Write the resume and the letter.</b> Start from the <a href="{P}/resume/examples/{slug_r}/">{e(low)} resume example</a> and the <a href="{P}/cover-letter-examples/{slug_r}/">cover letter example</a>, and replace every line with your own.</li>'
                 + f'<li><b>Apply where beginners are hired.</b> {len(begin):,} of today’s {n_:,} open {e(low)} jobs are junior or intern roles or ask for two years of experience or less. '
                 + f'<a href="{P}/roles/{slug_r}/">See the open jobs</a> and check each one with the <a href="{P}/tools/resume-match/">resume match checker</a> before you apply.</li></ol>')
        hb_qa = [(f"How much experience do {low} jobs ask for?", (f"The median in today’s postings is {y_med} years; {low_yrs}% of the postings that name a number ask for two years or less." if y_med is not None
                  else "Most postings for this work do not name a number of years. Read the duties: they tell you more about the level than the title does.")),
                 (f"Do I need a degree to become {art(low)} {low}?", (f"{nodeg}% of today’s {n_:,} postings say no degree is required." if nodeg else f"None of today’s {n_:,} postings say outright that no degree is required.")
                  + " Many others accept equivalent experience: read the requirements of each posting."),
                 (f"How much does a beginner {low} earn?", (f"Junior and intern postings for this work that state pay advertise a median of {money(median(jr_pay))} a year ({len(jr_pay)} postings)." if len(jr_pay) >= 8
                  else (f"Few beginner postings state pay. Across all levels, the median advertised pay is {money(median(all_pay))} a year." if len(all_pay) >= 20 else "Too few postings state pay for a reliable figure.")))]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in hb_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = ('<dl class="facts">' + f"<div><dt>Open jobs today</dt><dd>{n_:,}</dd></div><div><dt>Open to beginners</dt><dd>{len(begin):,}</dd></div>"
                  + (f"<div><dt>Experience asked, median</dt><dd>{y_med} years</dd></div>" if y_med is not None else "")
                  + (f"<div><dt>Beginner pay, median</dt><dd>{money(median(jr_pay))}</dd></div>" if len(jr_pay) >= 8 else "") + "</dl>")
        hb_dir[fs].append((slug_r, rname, len(begin)))
        page(f"how-to-become/{slug_r}/", f"How to Become {art(low)} {tcase(rname)}: Skills, Pay and {len(begin):,} Beginner Jobs | {SITE}",
             f"How to become {art(low)} {low}, from today’s {n_:,} open postings: {len(begin):,} are open to beginners. The skills employers name first, the experience they ask for and what juniors earn.",
             crumbs(("How to become…", "how-to-become/"), (rname, "")) + f'<h1>How to become {art(low)} {e(low)}: <span class="hl">{len(begin):,} beginner jobs open today</span></h1>'
             f'<p class="lead">Five steps for people changing careers, with the figures from today’s {n_:,} open {e(low)} postings: what employers ask for first, how much experience, and what beginners are paid.</p>'
             + facts_ + section(f"Five steps to your first {low} job", steps)
             + section(f"Questions about becoming {art(low)} {low}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in hb_qa) + "</dl>")
             + f'<p class="note">Counted from the open postings on {fdate(TODAY)}, read from employers’ own careers pages and recounted on every update. Beginner jobs: junior and intern titles, and postings that ask for two years of experience or less.</p>', head=ld_)
    hb_n = sum(len(v) for v in hb_dir.values())
    hb_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(hb_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/how-to-become/{s_}/">{e(nm)}</a><span>{k:,} for beginners</span></li>' for s_, nm, k in sorted(hb_dir[fs], key=lambda x: -x[2])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if hb_dir.get(fs)) + "</div>"
    page("how-to-become/", f"How to Become…: {hb_n} Careers with Skills, Pay and Beginner Jobs | {SITE}",
         f"How to become one of {hb_n} kinds of professional, from today’s open postings: the jobs open to beginners, the skills employers name first, the experience they ask for and what juniors earn.",
         crumbs(("How to become…", "")) + f'<h1>How to become… <span class="hl">{hb_n} careers, with today’s figures</span></h1>'
         '<p class="lead">For people changing careers: pick the work you want. Each page counts, from today’s open postings, how many jobs take beginners, which skills employers name first and what juniors are paid, then gives five steps to the first job.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, analyst or designer" aria-label="Find a career"></p>'
         f'<p class="lead" id="dirnone" hidden>No career with these words. <a href="{P}/entry-level/">Entry-level jobs</a> lists every job open to beginners.</p>' + hb_html)

    # Interview questions, one page per kind of work (Indeed's "<role> interview questions" pages are among its biggest search
    # entries). Nothing here is a claim about what a given employer asks: every question says why it is likely to come up, from
    # today's postings for that work (the skills they name, the situations their full text describes), and what a good answer shows.
    IQ_THEMES = [   # (regex over the full text of a posting, what the postings do, the question, what a good answer shows)
        (r"stakeholder", "mention stakeholders", "Tell me about a time you had to win over people outside your team who disagreed with you.",
         "Who they were, what each side wanted, what you did to reach agreement and how it ended."),
        (r"cross[- ]functional", "ask for work across teams", "Describe a project you delivered with people from other teams. What was your part?",
         "Your own part, how you kept the teams in step and the result."),
        (r"\bownership\b|\bend[- ]to[- ]end\b", "ask for ownership or end-to-end work", "Tell me about something you owned from the first idea to the result.",
         "That you saw it through when it got hard, with a number for the result."),
        (r"prioriti[sz]", "ask you to set priorities", "You have three urgent requests and time for one. How do you choose?",
         "A rule you really use (impact, deadline, who is blocked) and how you tell the people who have to wait."),
        (r"ambigu", "mention ambiguity", "Tell me about a time the goal was unclear. What did you do first?",
         "That you asked the right questions or took a small first step instead of waiting for clarity."),
        (r"fast[- ]paced|changing priorities|rapidly changing", "describe a fast-paced place", "Tell me about a time plans changed at short notice. How did you adjust?",
         "A quick new plan, what you dropped on purpose and how you kept others informed."),
        (r"\bkpis?\b|\bmetrics\b", "mention KPIs or metrics", "Which numbers did you watch in your last job, and what did you change because of one?",
         "One number, the change you made because of it and the effect."),
        (r"\bpresent(ing|ations?)\b|present (findings|results|to)", "ask for presenting", "Tell me about a presentation you gave. What changed because of it?",
         "Who the audience was, how you made it simple and the decision that followed."),
        (r"\bmentor", "mention mentoring", "Have you helped someone else get better at their work? What did you do?",
         "A specific person and skill, how you taught it and how they did afterwards."),
        (r"customer[- ]facing|client[- ]facing|with (our )?(customers|clients)", "ask for work with customers", "Tell me about a difficult conversation with a customer and how it ended.",
         "That you listened, kept your promise and what the customer did next."),
        (r"\bcomplian|\bregulat", "mention compliance or regulation", "Tell me about a time a rule or regulation slowed your work down. What did you do?",
         "That you followed it and still delivered, not that you went around it."),
        (r"\bbudgets?\b", "mention budgets", "Have you managed a budget? How large was it, and what did you change in it?",
         "The size, one decision you made and the money it saved or earned."),
        (r"deadline", "mention deadlines", "Tell me about a deadline you nearly missed. What happened?",
         "What you did when you saw the risk, whom you told and what you changed afterwards."),
        (r"data[- ]driven|data[- ]informed", "ask for decisions based on data", "Tell me about a decision you changed because of data.",
         "What you believed, what the data showed and what you did differently."),
        (r"\bai tools\b|\bllms?\b|copilot|chatgpt|generative ai", "mention AI tools", "Which AI tools do you use in your work, and where do you not trust them?",
         "Real, specific use, and that you check what the tool produces."),
        (r"on[- ]call", "mention on-call duty", "Have you been on call? Tell me about an incident you handled.",
         "How you found the cause, how fast it was fixed and what you changed so it would not happen again."),
        (r"\btravel", "mention travel", "How much are you able to travel for work?",
         "An honest number of days or share of time, so there are no surprises after the offer."),
        (r"\bshifts?\b|\bweekends?\b|\bovernight\b|\bnight\b", "mention shifts, nights or weekends", "Can you work the shifts, nights or weekends this job needs?",
         "A clear yes, or your exact limits, said early."),
        (r"\bquotas?\b", "mention a quota", "What was your quota, and how often did you meet it?",
         "Exact figures for the last few quarters and how you got there."),
        (r"written communication|writing skills|excellent written", "ask for good writing", "How do you keep people informed in writing?",
         "An example: a status update, a document or a message that saved a meeting."),
        (r"asynchronous|\basync\b|across time zones|distributed team", "mention working across time zones", "How do you work with a team that is mostly in other time zones?",
         "Clear written updates, the overlap hours you keep and decisions that do not wait for a call."),
    ]
    IQ_RX = [(re.compile(rx, re.I), a, b, c) for rx, a, b, c in IQ_THEMES]
    IQ_SHORT = ["Stakeholders", "Work across teams", "End-to-end ownership", "Setting priorities", "Ambiguity", "A fast pace", "KPIs and metrics", "Presenting",
                "Mentoring", "Work with customers", "Compliance and regulation", "Budgets", "Deadlines", "Decisions from data", "AI tools", "On-call duty", "Travel",
                "Night and weekend shifts", "A sales quota", "Good writing", "Time zones"]      # the same themes in two or three words
    assert len(IQ_SHORT) == len(IQ_RX)
    all_desc = [j for j in active if j.get("desc")]
    iq_hit = {j["id"]: [bool(rx.search(j["desc"])) for rx, _, _, _ in IQ_RX] for j in all_desc}      # each posting is read once
    def iq_li(q, why, good):
        return f'<li><h3>{e(q)}</h3><p class="why">{why}</p><p class="good"><b>A good answer shows:</b> {e(good)}</p></li>'
    def iq_ol(items, start):
        return f'<ol class="iq" style="counter-reset:iq {start}">' + "".join(iq_li(*x) for x in items) + "</ol>"
    SK_Q = [("Walk me through a recent project where you used {t}. What did you do yourself?", "Your own hands-on part, the choices you made and a number for the result."),
            ("What is a mistake people often make with {t}, and how do you avoid it?", "That you have used it long enough to know where it goes wrong."),
            ("How would you explain {t} to someone who has never used it?", "That you understand it well enough to make it simple."),
            ("Tell me about a problem with {t} that took you a long time to solve.", "How you narrowed the problem down, and what you would do faster next time.")]
    DU_Q = [("How do you approach {x}? Walk me through an example from your last job.", "A real example: what you did yourself, the steps in order and the result with a number."),
            ("What is the hardest part of {x} for you, and how do you handle it?", "An honest difficulty and the habit or method that makes it work.")]
    iq_dir = defaultdict(list)
    for slug_r, d in rex_data.items():
        rname, rj = by_role[slug_r]
        if len(rj) < 20: continue
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low, n_ = rlow(rname), len(rj)
        cnt_ = Counter(t for j in rj for t in j["tags"])
        top_ = resume_examples.asked(slug_r, cnt_.most_common(), n_)[:4]
        focus = [x.strip() for x in resume_examples.ROLE[slug_r][1].split(",") if x.strip()][:2] if slug_r in resume_examples.ROLE else []
        descs_ = [j for j in rj if j.get("desc")]
        own_text = len(descs_) >= 20
        pool_ = descs_ if own_text else all_desc
        th_ = sorted(((sum(1 for j in pool_ if iq_hit[j["id"]][i_]), a, b, c, IQ_SHORT[i_]) for i_, (rx, a, b, c) in enumerate(IQ_RX)), key=lambda x: -x[0])
        th_ = [x for x in th_ if x[0] >= max(4, len(pool_) * 0.15)][:6]
        mids_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"])
        paid_pct = pc_(sum(1 for j in rj if j["salary"]), n_)
        rem_pct = pc_(sum(1 for j in rj if j["remote"]), n_)
        sk_items = [(SK_Q[i][0].format(t=t), f"{pc_(k, n_)}% of today’s {n_:,} open {e(low)} postings name {e(t)}.", SK_Q[i][1]) for i, (t, k) in enumerate(top_)]
        du_items = [(DU_Q[i][0].format(x=x), f"One of the core duties of {e(low)} work.", DU_Q[i][1]) for i, x in enumerate(focus)]
        whose = f"today’s {len(pool_):,} open {e(low)} postings with a full description" if own_text else f"all {len(pool_):,} open postings with a full description"
        th_items = [(b, f"{pc_(k, len(pool_))}% of {whose} {e(a)}.", c) for k, a, b, c, _ in th_]
        th_note = "" if own_text else f'<p class="note">Too few {e(low)} postings have a full description to count on their own, so these shares are from all {len(pool_):,} postings with one.</p>'
        pay_good = (f"A range you can defend. Today’s {len(mids_):,} {low} postings that state a yearly US-dollar range advertise a median of {money(median(mids_))}; the middle half {money(mids_[len(mids_) // 4])} to {money(mids_[3 * len(mids_) // 4])}. Ask for their range first if you can."
                    if len(mids_) >= 20 else "A range you can defend, based on postings that state pay and on your experience. Ask for their range first if you can.")
        gen_items = [("Tell me about yourself.", "Almost every interview opens with it.",
                      f"Under a minute: your current work as {art(low)} {low}, one result with a number and why this job is the next step. Not your whole resume."),
                     ("Why do you want to work here?", "It tests whether you read about the company.", "Something specific: a product, a goal from the posting or a problem you can help with."),
                     ("Why are you leaving your current job?", "It checks for problems you might bring along.", "What you are moving towards, said briefly, with no criticism of your employer."),
                     ("What are your salary expectations?", (f"Only {paid_pct}% of today’s {e(low)} postings state pay, so be ready to name a figure." if paid_pct < 60 else f"{paid_pct}% of today’s {e(low)} postings state pay; know where you stand in the range."), pay_good),
                     ("What is one of your weaknesses?", "A classic, still asked.", "A real weakness that does not block this job, and what you do about it."),
                     ("Do you have any questions for us?", "The last question of almost every interview.", "Two or three questions you prepared; the list below has some.")]
        groups = [(f"Questions about the skills {low} postings name", sk_items), (f"Questions about the work itself", du_items),
                  (f"Questions about how you work", th_items), ("Questions almost every interview has", gen_items)]
        groups = [(h, xs) for h, xs in groups if xs]
        n_q, body_, k_ = sum(len(xs) for _, xs in groups), "", 0
        for h, xs in groups:
            body_ += section(h, (th_note if xs is th_items else "") + iq_ol(xs, k_)); k_ += len(xs)
        ask_ = [("What would make someone in this role successful in the first six months?", "It shows you think about results, and the answer tells you what the job really is."),
                ("Why is this role open?", "A new role, growth or someone leaving: each tells you something different.")]
        if rem_pct >= 25: ask_.append(("Which countries and time zones can this role be done from?", f"{rem_pct}% of today’s {low} postings are remote, and many of them still limit the countries."))
        if paid_pct < 60: ask_.append(("What is the pay range for this role?", f"Only {paid_pct}% of today’s {low} postings state one; asking is normal."))
        ask_ += [("How will my work be measured, and how often will we review it?", "You learn what matters to your manager before you start."),
                 ("What are the next steps, and when will you decide?", "You know when to follow up, and you can plan around other offers.")]
        iq_qa = [(f"What questions are asked in {art(low)} {low} interview?",
                  (f"Questions about the skills the postings name ({', '.join(t for t, _ in top_[:3])})" if top_ else "Questions about the duties of the job")
                  + (f", about how you work ({', '.join(x[4].lower() for x in th_[:3])})" if th_ else "")
                  + " and the questions almost every interview has, such as “Tell me about yourself” and your salary expectations."),
                 (f"How should I answer {low} interview questions?", "With a real example: the situation, what you had to do, what you did yourself and the result, with a number. "
                  "This is the STAR method; aim for 60 to 90 seconds an answer."),
                 (f"What salary should I ask for as {art(low)} {low}?", (f"Today’s {len(mids_):,} {low} postings that state a yearly US-dollar range advertise a median of {money(median(mids_))}. Adjust for your experience and the country, and ask for their range first."
                  if len(mids_) >= 20 else "Look at postings for this work that state pay, adjust for your experience and the country, and ask for their range first."))]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in iq_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = ('<dl class="facts">' + f"<div><dt>Questions to prepare</dt><dd>{n_q}</dd></div><div><dt>Open {e(low)} jobs today</dt><dd>{n_:,}</dd></div>"
                  + (f"<div><dt>Postings read in full</dt><dd>{len(descs_):,}</dd></div>" if own_text else "")
                  + (f"<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>" if len(mids_) >= 20 else "") + "</dl>")
        iq_dir[fs].append((slug_r, rname, n_q))
        page(f"interview-questions/{slug_r}/", f"{tcase(rname)} Interview Questions ({TODAY[:4]}): {n_q} to Prepare, with What a Good Answer Shows | {SITE}",
             f"{n_q} {low} interview questions to prepare for, each with why it is likely to come up (from today’s {n_:,} open {low} postings) and what a good answer shows.",
             crumbs(("Interview questions", "interview-questions/"), (rname, "")) + f'<h1>{e(rname)} interview questions: <span class="hl">{n_q} to prepare for</span></h1>'
             f'<p class="lead">Each question says why it is likely to come up, from what today’s {n_:,} open {e(low)} postings ask for, and what a good answer shows. '
             f'Prepare a real example for each, then practise it with the <a href="{P}/tools/interview-answer-builder/">interview answer builder</a>.</p>'
             + facts_ + body_
             + section("Questions to ask them", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in ask_) + "</dl>")
             + section(f"Questions about {art(low)} {low} interview", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in iq_qa) + "</dl>")
             + section("Prepare with", '<div class="feats">'
                       f'<a class="feat" href="{P}/tools/interview-answer-builder/"><h3>Interview answer builder</h3><p>Turn an example into a 60 to 90 second answer, with checks for a number and for “I”.</p></a>'
                       f'<a class="feat" href="{P}/resume/examples/{slug_r}/"><h3>The {e(low)} resume example</h3><p>The results interviewers ask about, written as resume lines.</p></a>'
                       f'<a class="feat" href="{P}/tools/thank-you-email/"><h3>Thank-you email</h3><p>Send it on the day of the interview, written from four fields.</p></a>'
                       f'<a class="feat" href="{P}/roles/{slug_r}/"><h3>{n_:,} open {e(low)} jobs</h3><p>Read from employers’ own careers pages every hour.</p></a></div>')
             + f'<p class="note">Counted from the open postings on {fdate(TODAY)}, read from employers’ own careers pages and recounted on every update. The questions are ours; no employer’s interview is copied here.</p>', head=ld_)
    iq_n = sum(len(v) for v in iq_dir.values())
    iq_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(iq_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/interview-questions/{s_}/">{e(nm)}</a><span>{k} questions</span></li>' for s_, nm, k in sorted(iq_dir[fs], key=lambda x: x[1])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if iq_dir.get(fs)) + "</div>"
    page("interview-questions/", f"Interview Questions for {iq_n} Jobs, with What a Good Answer Shows | {SITE}",
         f"Interview questions for {iq_n} kinds of work. Each says why it is likely to come up, from today’s open postings, and what a good answer shows. Free, no sign-up.",
         crumbs(("Interview questions", "")) + f'<h1>Interview questions for <span class="hl">{iq_n} jobs</span></h1>'
         '<p class="lead">Pick your work. Each page lists the questions to prepare for, why each is likely to come up, from the skills and situations today’s open postings name, and what a good answer shows.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, analyst or designer" aria-label="Find a job"></p>'
         f'<p class="lead" id="dirnone" hidden>No page with these words. The <a href="{P}/tools/interview-answer-builder/">interview answer builder</a> works for any job.</p>' + iq_html)

    # "How to hire a <work>" for employers (Indeed and Workable rank with such guides). The steps are the same for every work; what makes
    # a page worth reading is counted from today's postings: who else is hiring this work, where, what they pay and offer, how long
    # postings stay up. Each step links the tool or template that does it.
    def days_up(j, until=None):
        try: return (datetime.date.fromisoformat((until or TODAY)[:10]) - datetime.date.fromisoformat(j["posted"][:10])).days
        except (KeyError, TypeError, ValueError): return None
    hh_dir = defaultdict(list)
    for slug_r, d in rex_data.items():
        rname, rj = by_role[slug_r]
        if len(rj) < 20: continue
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low, n_ = rlow(rname), len(rj)
        many = ROLE_PLURAL.get(rname, low + "s")
        cos_ = Counter(j["company"] for j in rj)
        ctry_ = Counter(c for j in rj for c in {x for x, _ in countries_of(j.get("location") or "")})
        names_ = {c: nm for c, nm, _, _ in COUNTRIES}
        names_["US"] = "United States"
        mids_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"])
        paid_pct = pc_(sum(1 for j in rj if j["salary"]), n_)
        rem_pct, hyb_pct = pc_(sum(1 for j in rj if j["remote"]), n_), pc_(sum(1 for j in rj if j.get("hybrid")), n_)
        yrs = sorted(j["years"] for j in rj if j.get("years"))
        y_med = yrs[len(yrs) // 2] if len(yrs) >= 10 else None
        cnt_ = Counter(t for j in rj for t in j["tags"])
        top_ = resume_examples.asked(slug_r, cnt_.most_common(), n_)[:5]
        perk_ = Counter(x for j in rj for x in j.get("perks", []) if x != "No degree required").most_common(4)
        ages_ = sorted(x for x in (days_up(j) for j in rj) if x is not None and 0 <= x <= 730)
        age_med = ages_[len(ages_) // 2] if len(ages_) >= 15 else None
        closed_ = [x for x in (days_up(j, j.get("last_seen")) for j in jobs if not j["active"] and role_hit(rname, None, j["title"])) if x is not None and 0 <= x <= 730]
        closed_.sort()
        cl_med = closed_[len(closed_) // 2] if len(closed_) >= 15 else None
        has_sal = (OUT / "salaries" / slug_r / "index.html").exists()
        rows_ = ([("Companies hiring this work now", f"{len(cos_):,}: " + ", ".join(f'<a href="{P}/companies/{slugify(c)}/">{e(c)}</a> ({k})' for c, k in cos_.most_common(6)))]
                 + ([("Countries named most", ", ".join(f"{fl(c)}{e(names_.get(c, c))} ({k:,})" for c, k in ctry_.most_common(5)))] if ctry_ else [])
                 + ([("Pay advertised", f"{money(mids_[len(mids_) // 4])} – {money(mids_[3 * len(mids_) // 4])} for the middle half; median {money(median(mids_))} ({len(mids_):,} postings with a yearly US-dollar range)")] if len(mids_) >= 20 else [])
                 + [("Postings that state pay", f"{paid_pct}%"), ("Where the work is done", f"Remote {rem_pct}% · hybrid {hyb_pct}% · on site or not stated {max(0, 100 - rem_pct - hyb_pct)}%")]
                 + ([("Experience asked", f"Median {y_med} years")] if y_med else [])
                 + ([("Skills named most", ", ".join(f"{e(t)} ({pc_(k, n_)}%)" for t, k in top_))] if top_ else [])
                 + ([("Benefits named most", ", ".join(f"{e(x)} ({pc_(k, n_)}%)" for x, k in perk_))] if perk_ else [])
                 + ([("How long postings stay up", f"Half of today’s open postings have been up more than {age_med} days" + (f"; postings that closed since we started tracking stayed up a median of {cl_med} days" if cl_med is not None else ""))] if age_med is not None else []))
        pay_step = ((f"Today’s {len(mids_):,} {e(low)} postings that state a yearly US-dollar range offer {money(mids_[len(mids_) // 4])} to {money(mids_[3 * len(mids_) // 4])} for the middle half. "
                     f"Three quarters of them offer more than the lower figure.") if len(mids_) >= 20 else
                    "Few postings for this work state pay, so look at what similar roles near you advertise and at what your own team earns.")
        steps = ('<ol class="steps">'
                 f'<li><b>Set the pay range first.</b> {pay_step} {paid_pct}% of the postings state pay; in several US states and EU countries the law requires it.'
                 + (f' <a href="{P}/salaries/{slug_r}/">See {e(low)} pay in detail</a>.' if has_sal else "") + "</li>"
                 f'<li><b>Write the description.</b> Start from the <a href="{P}/job-descriptions/{slug_r}/">{e(low)} job description template</a>, then check it with the <a href="{P}/tools/job-description-checker/">job description checker</a>: '
                 "the pay, the place of work and the must-haves should be clear before the second paragraph.</li>"
                 f'<li><b>Decide where the person can work.</b> {rem_pct}% of today’s {e(low)} postings are remote and {hyb_pct}% hybrid. '
                 "If yours is remote, name the countries or time zones; “remote” alone brings applications you cannot accept.</li>"
                 f'<li><b>Post it where people look.</b> <a href="{P}/post-a-job/">Post the job free</a> on this site, add it to your own careers page and send it to people you know who do this work.</li>'
                 + (f'<li><b>Screen for the skills that matter.</b> Today’s postings name {", ".join(e(t) for t, _ in top_[:3])} most often: check them in the work, not only in the resume. '
                    if top_ else "<li><b>Screen for the work, not the titles.</b> Ask each candidate to describe a result from similar work, with a number. ")
                 + f'Score every candidate on the same points with the <a href="{P}/tools/interview-scorecard/">interview scorecard</a>; the <a href="{P}/interview-questions/{slug_r}/">{e(low)} interview questions</a> show what good candidates prepare for.</li>'
                 + "<li><b>Decide quickly.</b> "
                 + (f"Half of today’s open {e(low)} postings have been up more than {age_med} days: a candidate who waits for your answer may be talking to other employers meanwhile. " if age_med is not None else "A candidate who waits for your answer may accept another offer meanwhile. ")
                 + "Tell every candidate when you will decide, and keep to it.</li></ol>")
        hh_qa = [(f"How much does it cost to hire {art(low)} {low}?", (f"The pay is the largest part: today’s {low} postings that state a yearly US-dollar range advertise a median of {money(median(mids_))}. " if len(mids_) >= 20 else "The pay is the largest part. ")
                  + "Add advertising, agency fees if you use one and the hours your team spends interviewing; the cost per hire calculator on this site adds them up. Posting on this site is free."),
                 (f"How long does it take to hire {art(low)} {low}?", (f"Half of today’s open {low} postings have been up more than {age_med} days" + (f", and postings for this work that closed since we started tracking stayed up a median of {cl_med} days" if cl_med is not None else "")
                  + ". A posting can close before the person starts, so plan for a few weeks more." if age_med is not None else "It depends on the level and the market; plan for several weeks from posting to the first day.")),
                 (f"Where can I find {many}?", f"{len(cos_):,} companies are hiring {many} on this site today. Post your job here free, on your own careers page and in communities where {many} meet; "
                  + ("the table on this page lists the countries named most in today’s postings." if len(ctry_) >= 3 else "name the countries you can hire in."))]      # no country names in plain text: a country is shown with its flag
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in hh_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = ('<dl class="facts">' + f"<div><dt>Companies hiring now</dt><dd>{len(cos_):,}</dd></div><div><dt>Open postings</dt><dd>{n_:,}</dd></div>"
                  + (f"<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>" if len(mids_) >= 20 else "")
                  + f"<div><dt>Remote</dt><dd>{rem_pct}%</dd></div>"
                  + (f"<div><dt>Half are open for over</dt><dd>{age_med} days</dd></div>" if age_med is not None else "") + "</dl>")
        hh_dir[fs].append((slug_r, rname, len(cos_)))
        page(f"how-to-hire/{slug_r}/", f"How to Hire {art(low)} {tcase(rname)} ({TODAY[:4]}): Pay, Competition and Six Steps | {SITE}",
             f"How to hire {art(low)} {low}: {len(cos_):,} companies are hiring this work today. What they pay and offer, where, how long postings stay up, and six steps with free templates and tools.",
             crumbs(("For employers", "post-a-job/"), ("How to hire…", "how-to-hire/"), (rname, "")) + f'<h1>How to hire {art(low)} {e(low)}: <span class="hl">{len(cos_):,} companies are hiring now</span></h1>'
             f'<p class="lead">What you compete with, counted from today’s {n_:,} open {e(low)} postings: who is hiring, where, what they pay and how long postings stay up. Then six steps, each with a free template or tool.</p>'
             + facts_
             + section("What you compete with", '<div class="tablewrap"><table>' + "".join(f"<tr><th>{e(k)}</th><td>{v}</td></tr>" for k, v in rows_) + "</table></div>"
                       f'<p class="note">Counted from the {n_:,} open postings for this work on {fdate(TODAY)}, read from employers’ own careers pages and recounted on every update.</p>')
             + section(f"Six steps to hire {art(low)} {low}", steps)
             + section(f"Questions about hiring {many}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in hh_qa) + "</dl>")
             + f'<p class="note cmpl">See also: <a href="{P}/job-descriptions/{slug_r}/">{e(low)} job description template</a> · <a href="{P}/roles/{slug_r}/">{n_:,} open {e(low)} jobs</a> · '
             + f'<a href="{P}/tools/cost-per-hire/">cost per hire calculator</a> · <a href="{P}/how-to-hire/">all hiring guides</a></p>', head=ld_)
    hh_n = sum(len(v) for v in hh_dir.values())
    hh_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(hh_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/how-to-hire/{s_}/">{e(nm)}</a><span>{k:,} hiring</span></li>' for s_, nm, k in sorted(hh_dir[fs], key=lambda x: -x[2])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if hh_dir.get(fs)) + "</div>"
    page("how-to-hire/", f"How to Hire…: Guides for {hh_n} Roles with Pay and Competition Data | {SITE}",
         f"Hiring guides for {hh_n} kinds of work: who else is hiring, where, what they pay and offer, how long postings stay up, and six steps with free templates and tools.",
         crumbs(("For employers", "post-a-job/"), ("How to hire…", "")) + f'<h1>How to hire… <span class="hl">{hh_n} roles, with today’s competition</span></h1>'
         '<p class="lead">For employers: pick the work you are hiring for. Each guide counts, from today’s open postings, how many companies want the same people, what they pay and offer and how long postings stay up, then gives six steps with a free template or tool for each.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a role, for example nurse, accountant or designer" aria-label="Find a guide"></p>'
         f'<p class="lead" id="dirnone" hidden>No guide with these words. The <a href="{P}/job-descriptions/">job description templates</a> cover the same roles.</p>' + hh_html)

    # "Hiring Right Now vs <job site>": fair comparisons, every fact about the other site sourced and dated (compare_sites.py).
    # A site with fewer than 4 sourced rows gets no page: a comparison with gaps would not be fair.
    VS = [x for x in compare_sites.SITES if len(x["rows"]) >= 4]
    def vs_src(x):
        seen_, out_ = set(), []
        for fact, url, date in x["sources"]:
            if url in seen_: continue
            seen_.add(url)
            out_.append(f'<li><a href="{e(url)}" rel="nofollow noopener">{e(re.sub(r"^https?://(www\.)?", "", url).rstrip("/")[:70])}</a>, read {fdate(date)}</li>')
        return '<ul class="vs-src">' + "".join(out_) + "</ul>"
    for x in VS:
        ours = compare_sites.OUR_NAME
        table_ = ('<div class="tablewrap"><table class="vs-t"><tr><th></th><th>' + e(x["name"]) + "</th><th>" + e(ours) + "</th></tr>"
                  + "".join(f"<tr><th>{e(q_)}</th><td>{e(a_)}</td><td>{e(b_)}</td></tr>" for q_, a_, b_ in x["rows"]) + "</table></div>")
        vs_qa = [(f"Is {ours} better than {x['name']}?", x["pick"]), (f"Where is {x['name']} better?", " ".join(x["them_better"])), (f"Where is {ours} better?", " ".join(x["us_better"]))]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in vs_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page(f"vs/{x['slug']}/", f"{x['name']} vs {ours}: a Fair Comparison ({fdate(TODAY, False)}) | {SITE}",
             f"{x['name']} and {ours} side by side: who pays, prices, where the jobs come from, where you apply and how fresh the listings are. Every fact about {x['name']} comes with its source.",
             crumbs(("Compared with other job sites", "vs/"), (x["name"], "")) + f'<h1>{e(x["name"])} vs {e(ours)}: <span class="hl">a fair comparison</span></h1>'
             f'<p class="lead">{e(x["what"])} Below, the two side by side. Every fact about {e(x["name"])} comes from its own pages or a named source, read on the date shown; where we could not check a fact, the row is left out.</p>'
             + f'<p class="vs-pick"><b>In short:</b> {e(x["pick"])}</p>'
             + section(f"{x['name']} and {ours}, side by side", table_)
             + '<div class="vs-two"><div><h2>Where ' + e(x["name"]) + ' is better</h2><ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in x["them_better"]) + "</ul></div>"
               '<div><h2>Where ' + e(ours) + ' is better</h2><ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in x["us_better"]) + "</ul></div></div>"
             + section(f"Questions about {x['name']} and {ours}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in vs_qa) + "</dl>")
             + section("Sources", vs_src(x) + f'<p class="note">Facts about {e(ours)} are from this site on {fdate(TODAY)}. A fact that is wrong or out of date can be reported from the <a href="{P}/about/">About page</a>; it is corrected or removed.</p>'), head=ld_)
    page("vs/", f"{SITE} Compared with Other Job Sites: {len(VS)} Fair Comparisons | {SITE}",
         f"{SITE} side by side with {', '.join(x['name'] for x in VS[:-1])} and {VS[-1]['name']}: who pays, prices, where jobs come from and where you apply. Every fact sourced and dated.",
         crumbs(("Compared with other job sites", "")) + f'<h1>{e(SITE)} compared with <span class="hl">{len(VS)} other job sites</span></h1>'
         '<p class="lead">Each comparison puts the facts side by side, says honestly where the other site is better, and links to the source of every fact about it. Pick the one you use now.</p>'
         + section("Choose a site", '<ul class="tiles">' + "".join(f'<li><a class="tile" href="{P}/vs/{x["slug"]}/"><span class="n">{e(x["name"])} vs {e(SITE)}</span><span class="c">{len(x["rows"])} facts</span></a></li>' for x in VS) + "</ul>"))

    # Career quiz: "which kind of work fits me?" (the Careerist study: its lead magnet, but theirs asks for a phone number). Seven plain
    # questions add points to fields of work; the result shows the three best fields with today's figures and the way in. All in the
    # browser, nothing is stored on a server. QZ maps each answer to fields and points.
    QZ = [
        ("What do you enjoy most?", [
            ("Building things that work", {"software-development": 3, "hardware-engineering": 2, "cloud-devops-it": 2, "ai-machine-learning": 1}),
            ("Finding answers in numbers", {"data-analytics": 3, "accounting-finance": 2, "ai-machine-learning": 2}),
            ("Making things look and feel right", {"design-creative": 3, "marketing-communications": 1, "product-project": 1}),
            ("Talking with people and persuading them", {"sales": 3, "marketing-communications": 2, "hr-recruiting": 1}),
            ("Organising and keeping things running", {"operations-administration": 3, "product-project": 2, "accounting-finance": 1}),
            ("Helping people solve their problems", {"customer-service": 3, "hr-recruiting": 1, "science-healthcare": 1}),
            ("Explaining and teaching", {"education-training": 3, "writing-translation": 2, "customer-service": 1}),
            ("Looking after people’s health", {"science-healthcare": 3})]),
        ("Which school subject did you like best?", [
            ("Maths", {"data-analytics": 2, "software-development": 1, "accounting-finance": 2, "ai-machine-learning": 1}),
            ("Physics or technology", {"hardware-engineering": 3, "software-development": 1, "cloud-devops-it": 1}),
            ("Biology or chemistry", {"science-healthcare": 3}),
            ("Art or design", {"design-creative": 3}),
            ("Languages or writing", {"writing-translation": 3, "marketing-communications": 1}),
            ("Economics or business", {"sales": 1, "accounting-finance": 2, "product-project": 1, "operations-administration": 1}),
            ("Law or social studies", {"legal-compliance": 3, "hr-recruiting": 1})]),
        ("What would you rather work with all day?", [
            ("A computer, with long stretches of focus", {"software-development": 2, "data-analytics": 2, "security": 1, "ai-machine-learning": 1}),
            ("People: calls, meetings, conversations", {"sales": 2, "hr-recruiting": 2, "customer-service": 2}),
            ("A mix of both", {"product-project": 2, "marketing-communications": 1, "operations-administration": 1}),
            ("Physical things: machines, tools, equipment", {"hardware-engineering": 3, "retail-hospitality": 1}),
            ("Rules, documents and checks", {"legal-compliance": 3, "accounting-finance": 1, "security": 1})]),
        ("What matters most to you in a job?", [
            ("High pay", {"software-development": 1, "ai-machine-learning": 2, "sales": 1, "security": 1}),
            ("Helping others", {"science-healthcare": 2, "customer-service": 1, "education-training": 2}),
            ("Creative freedom", {"design-creative": 2, "marketing-communications": 1, "writing-translation": 1}),
            ("Stability and clear rules", {"accounting-finance": 1, "legal-compliance": 1, "operations-administration": 2}),
            ("Working from home", {"software-development": 1, "customer-service": 1, "writing-translation": 1, "data-analytics": 1})]),
        ("How do you like to work?", [
            ("Alone, on a hard problem", {"software-development": 2, "security": 2, "data-analytics": 1}),
            ("In a team, on a shared goal", {"product-project": 1, "design-creative": 1, "operations-administration": 1}),
            ("Leading and deciding", {"product-project": 3, "sales": 1}),
            ("Face to face with customers", {"sales": 2, "customer-service": 2, "retail-hospitality": 2})]),
        ("Which of these are you comfortable with already?", [
            ("Writing code, even a little", {"software-development": 3, "cloud-devops-it": 1, "ai-machine-learning": 1}),
            ("Spreadsheets and formulas", {"data-analytics": 2, "accounting-finance": 2, "operations-administration": 1}),
            ("Drawing or design tools", {"design-creative": 3}),
            ("Phone calls and presenting", {"sales": 2, "marketing-communications": 1}),
            ("Contracts, policies and paperwork", {"legal-compliance": 2, "hr-recruiting": 1, "operations-administration": 1}),
            ("None of these yet", {"customer-service": 1, "retail-hospitality": 1, "operations-administration": 1})]),
        ("Where are you now?", [
            ("At school or university", {}), ("Working, in another field", {}), ("Several years in an office job", {}), ("Already working in tech", {})]),
    ]
    qz_fields = {}
    for fs, fn, fd, live, js_ in fam_rows:
        if fs not in {k for _, opts in QZ for _, w in opts for k in w}: continue
        beg = [j for j in js_ if j["entry"] or (j.get("years") and j["years"] <= 2)]
        mids_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in js_ if j["usd"])
        top_r = [s_ for s_, _, _ in sorted(live, key=lambda x: -x[2]) if (OUT / "how-to-become" / s_ / "index.html").exists()][:2]
        qz_fields[fs] = {"n": fn, "d": fd, "jobs": len(js_), "beg": len(beg), "pay": money(median(mids_)) if len(mids_) >= 20 else "", "rem": pc_(sum(1 for j in js_ if j["remote"]), len(js_)),
                         "roles": [[s_, next(nm for x, nm, _ in live if x == s_)] for s_ in top_r]}
    qz_html = "".join(f'<fieldset class="qz-q"><legend><span>{i + 1}</span>{e(q)}</legend>' + "".join(
        f'<label><input type="radio" name="q{i}" value="{k}"><span>{e(a)}</span></label>' for k, (a, _) in enumerate(opts)) + "</fieldset>" for i, (q, opts) in enumerate(QZ))
    qz_data = json.dumps({"w": [[w for _, w in opts] for _, opts in QZ], "f": qz_fields}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    qz_js = r"""<script>(function(){var D=JSON.parse(document.getElementById('qz-data').textContent),f=document.getElementById('qz'),out=document.getElementById('qz-out'),P=document.documentElement.getAttribute('data-base')||'';
var esc=function(x){return String(x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
f.addEventListener('submit',function(ev){ev.preventDefault();var sc={},n=0;D.w.forEach(function(opts,i){var c=f.querySelector('input[name=q'+i+']:checked');if(!c)return;n++;var w=opts[+c.value];for(var k in w)sc[k]=(sc[k]||0)+w[k];});
var exp=f.querySelector('input[name=q'+(D.w.length-1)+']:checked'),newbie=exp&&+exp.value<2;
if(n<4){out.innerHTML='<p class="banner">Answer at least four questions for a result.</p>';out.hidden=false;return;}
var top=Object.keys(sc).filter(function(k){return D.f[k];}).sort(function(a,b){return sc[b]-sc[a];}).slice(0,3),best=sc[top[0]]||1;
out.innerHTML='<h2>Your best fits</h2><ol class="qz-res">'+top.map(function(k){var x=D.f[k];return '<li><div class="qz-h"><b>'+esc(x.n)+'</b><span class="pill">'+Math.round(100*sc[k]/best)+'% fit</span></div><p>'+esc(x.d.charAt(0).toUpperCase()+x.d.slice(1))+'.</p>'+
'<p class="qz-fig">'+x.jobs.toLocaleString('en-US')+' open jobs · '+x.beg.toLocaleString('en-US')+' open to beginners'+(x.pay?' · median pay '+x.pay:'')+' · '+x.rem+'% remote</p>'+
'<p>'+x.roles.map(function(r){return '<a class="btn ghost sm" href="'+P+'/how-to-become/'+r[0]+'/">How to become '+esc(r[1].toLowerCase())+'</a>';}).join(' ')+' <a class="btn ghost sm" href="'+P+'/categories/'+k+'/">See the jobs</a></p></li>';}).join('')+'</ol>'+
'<p class="note">'+(newbie?'Starting out? Look at the jobs open to beginners first, and build one piece of proof for the field you pick.':'Changing field? Start with roles that reuse what you already do well.')+' The figures are from today’s open postings.</p>';
out.hidden=false;out.scrollIntoView({behavior:'smooth',block:'start'});});})();</script>"""
    qz_qa = [("Which job is right for me?", "The one that matches what you enjoy, what you are already good at and how you like to work. This quiz scores fields of work on those three, then shows how many jobs each field has today and how many take beginners."),
             ("Is the career quiz free?", "Yes, and it needs no account, no email and no phone number. Your answers stay in your browser."),
             ("What should I do after the quiz?", "Open “How to become…” for the field you pick: it lists the skills employers name first and the jobs open to beginners today.")]
    qz_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in qz_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("career-quiz/", f"Career Quiz: Which Job Fits Me? Free, No Sign-Up | {SITE}",
         "A free career quiz with seven plain questions. It shows the three fields of work that fit you best, with today’s open jobs, jobs open to beginners and median pay. No email, no sign-up.",
         crumbs(("Career quiz", "")) + '<h1>Which job fits me? <span class="hl">A seven-question career quiz</span></h1>'
         '<p class="lead">Seven plain questions about what you enjoy, what you already do well and how you like to work. You get the three fields that fit you best, with how many jobs they have today and how to get in. No email, no sign-up: your answers stay in your browser.</p>'
         f'<form id="qz" class="qz">{qz_html}<p><button class="btn primary" type="submit">Show my best fits</button></p></form>'
         f'<section class="sec qz-out" id="qz-out" aria-live="polite" hidden></section><script type="application/json" id="qz-data">{qz_data}</script>{qz_js}'
         + section("Questions about the career quiz", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in qz_qa) + "</dl>"), head=qz_ld)

    # Guides: the blog. The owner asked whether the site needs one after looking at the blogs of hh.ru and Indeed. Theirs are written
    # by editors; these are written once and recounted from the open postings on every build, so the figures in them are never old.
    GUIDES = []
    PUBLISHED = "2026-11-13"
    def guide(slug, title, desc, cat, lead, body, prev, more=()):
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc, "datePublished": PUBLISHED, "dateModified": TODAY,
               "author": {"@type": "Organization", "name": SITE, "url": FULL + "/about/"}, "publisher": {"@type": "Organization", "name": SITE, "logo": {"@type": "ImageObject", "url": FULL + "/og.jpg"}},
               "mainEntityOfPage": f"{FULL}/guides/{slug}/", "image": FULL + "/og.jpg"}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        links = ('<p class="note cmpl">Next: ' + " · ".join(f'<a href="{P}/{u_}">{e(t_)}</a>' for u_, t_ in more) + "</p>") if more else ""
        page(f"guides/{slug}/", f"{title} | {SITE}", desc,
             crumbs(("Guides", "guides/"), (title, "")) + f'<article class="guide"><h1>{e(title)}</h1><p class="stamp">{e(cat)} · figures recounted {fdate(TODAY)} from <b>{n:,}</b> open jobs · <a href="{P}/methodology/">how they are made</a></p>'
             f'<p class="lead">{lead}</p>{body}{links}</article>', head=ld_)
        GUIDES.append((slug, title, desc, cat, prev))
    fam_stats = []
    for fs, fn, fd, live, js_ in fam_rows:
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in js_ if j["usd"]]
        rmids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in js_ if j["usd"] and j["remote"]]
        fam_stats.append(dict(fs=fs, fn=fn, n=len(js_), rem=sum(j["remote"] for j in js_), pay=sum(bool(j["salary"]) for j in js_), ent=sum(1 for j in js_ if j["entry"]),
                              med=median(mids_) if len(mids_) >= 30 else 0, rmed=median(rmids_) if len(rmids_) >= 30 else 0))
    big_f = [f for f in fam_stats if f["n"] >= 100]
    mini = lambda rows_: "".join(f'<span class="rw"><span>{e(lab[:20])}</span><span class="mt"><i style="width:{max(4, round(100 * v_ / max(r_[1] for r_ in rows_)))}%"></i></span><b>{e(txt)}</b></span>' for lab, v_, txt in rows_[:4])
    skel = '<span class="sk" style="width:92%"></span><span class="sk h" style="width:54%"></span><span class="sk" style="width:80%"></span><span class="sk" style="width:66%"></span>'

    # 1. remote work by field
    by_rem = sorted(big_f, key=lambda f: -f["rem"] / f["n"])
    rem_pay = sorted((f for f in big_f if f["rmed"]), key=lambda f: -f["rmed"])
    guide("remote-jobs-by-field", "Which jobs can be done from home, and what they pay",
          f"{pc_(len(remote), n)}% of {n:,} open jobs can be done from home. The share by field, what remote jobs advertise as pay, and how many are open to any country.", "Remote work",
          f"Out of {n:,} open jobs, {len(remote):,} can be done from home: {pc_(len(remote), n)}%. The share is highest in {e(rlow(by_rem[0]['fn']))} ({pc_(by_rem[0]['rem'], by_rem[0]['n'])}%) "
          f"and lowest in {e(rlow(by_rem[-1]['fn']))} ({pc_(by_rem[-1]['rem'], by_rem[-1]['n'])}%).",
          "<h2>Remote jobs, field by field</h2><p>The bar is the share of a field’s open jobs that can be done from home. Each bar opens the remote jobs of that field.</p>"
          + bars_([(f["fn"], f["rem"] / f["n"], f'{pc_(f["rem"], f["n"])}% · {f["rem"]:,} jobs', f'categories/{f["fs"]}/remote/' if f["rem"] >= 20 else f'categories/{f["fs"]}/') for f in by_rem])
          + ("<h2>What remote jobs advertise as pay</h2><p>The median of the yearly ranges stated in remote postings, where at least 30 postings in the field state one.</p>"
             + bars_([(f["fn"], f["rmed"], money(f["rmed"]), f'categories/{f["fs"]}/remote/') for f in rem_pay]) if rem_pay else "")
          + f"<h2>Remote does not mean “from any country”</h2><p>Most remote jobs are open in some countries only: the employer must be able to hire you where you live. Of the {len(remote):,} remote jobs here, "
            f"{len(aw):,} name no country at all. Those are on the <a href=\"{P}/work-from-anywhere/\">work-from-anywhere list</a>. For the rest, the <a href=\"{P}/for-you/\">match by five answers</a> asks for your country and leaves out the jobs that do not hire there.</p>",
          '<span class="ex">today</span>' + mini([(f["fn"], f["rem"] / f["n"], f'{pc_(f["rem"], f["n"])}%') for f in by_rem]),
          (("remote/", "All remote jobs"), ("insights/highest-paying-remote-jobs/", "The 40 best paid remote jobs"), ("guides/who-states-the-pay/", "Who states the pay")))

    # 2. how long postings stay open
    ages = [age_days(j) for j in active]
    age_cols = [("0–7 d", sum(a_ <= 7 for a_ in ages)), ("8–30", sum(7 < a_ <= 30 for a_ in ages)), ("31–60", sum(30 < a_ <= 60 for a_ in ages)), ("61–90", sum(60 < a_ <= 90 for a_ in ages)),
                ("91–180", sum(90 < a_ <= 180 for a_ in ages)), ("180+", sum(a_ > 180 for a_ in ages))]
    guide("how-long-jobs-stay-open", "How long a job posting stays open, and what an old one means",
          f"Half of open postings are younger than {int(median(ages))} days; {pc_(long_all, n)}% have been open {LONG_OPEN} days or more. What an old posting tells you and how to check it.", "Reading postings",
          f"Half of the {n:,} open postings are younger than {int(median(ages))} days. {long_all:,} of them, {pc_(long_all, n)}%, have been open for {LONG_OPEN} days or more. An old posting is not always a dead one, and the difference can be checked.",
          '<h2>Open postings by age</h2><p>How many postings are this old today, counted from the date the employer posted them.</p><div class="pics two"><figure class="pic">' + cols(age_cols, 0) + "</figure></div>"
          f"<h2>Why some postings never close</h2><p>Three reasons account for most of them. Some employers hire for the same title all year and keep one posting for it. Some postings are an invitation to send a resume for the future, "
          f"with no opening behind it; we mark those “talent pool”. And some are simply forgotten. A posting that is {LONG_OPEN} days old carries a mark on this site so you can decide before spending an evening on it.</p>"
          f"<h2>How to check one</h2><p>Open the job page and press “Check with the employer right now”. Your browser asks the employer’s own hiring system whether the job is still there and shows the answer. "
          f"Today {closed_today_h:,} postings were closed by employers; their pages stay online, marked as closed.</p>",
          '<span class="ex">today</span>' + mini([(lb, v_, f"{v_:,}") for lb, v_ in age_cols]),
          (("insights/long-open-roles/", "Where postings linger"), ("new/", "Jobs posted in the last 3 days"), ("guides/is-this-job-still-open/", "Is this job still open?")))

    # 3. who states the pay
    by_pay = sorted(big_f, key=lambda f: -f["pay"] / f["n"])
    guide("who-states-the-pay", "Who states the pay in a job posting",
          f"{SALPCT}% of {n:,} open postings state what the job pays. The share by field, which employers always state it, and what to do when a posting is silent.", "Pay",
          f"{SALPCT}% of the {n:,} open postings state what the job pays. In {e(rlow(by_pay[0]['fn']))} it is {pc_(by_pay[0]['pay'], by_pay[0]['n'])}%; in {e(rlow(by_pay[-1]['fn']))}, {pc_(by_pay[-1]['pay'], by_pay[-1]['n'])}%.",
          "<h2>Postings that state the pay, field by field</h2><p>The bar is the share of a field’s postings in which a pay range can be found.</p>"
          + bars_([(f["fn"], f["pay"] / f["n"], f'{pc_(f["pay"], f["n"])}%', f'categories/{f["fs"]}/') for f in by_pay])
          + f"<h2>Why the share differs</h2><p>Some US states require a pay range in a job posting; elsewhere it is the employer’s choice. So the same company often states pay for a role in New York and stays silent for the same role in another country. "
            f"A missing figure here can also mean a wording our reader does not recognise.</p>"
            f"<h2>When a posting is silent</h2><p>Look at what the same kind of work pays where it is stated: the <a href=\"{P}/tools/salary-checker/\">salary checker</a> shows the range for a role and level from postings that publish it, "
            f"and the <a href=\"{P}/tools/offer-check/\">offer check</a> places a figure you were offered among them. The list of <a href=\"{P}/with-salary/\">jobs that state pay</a> leaves the silent ones out.</p>",
          '<span class="ex">today</span>' + mini([(f["fn"], f["pay"] / f["n"], f'{pc_(f["pay"], f["n"])}%') for f in by_pay]),
          (("insights/pay-transparency/", "Employers that state pay most often"), ("salaries/", "Salary data"), ("guides/job-levels-explained/", "What the level in a title means")))

    # 4. entry level
    by_ent = sorted((f for f in big_f if f["ent"]), key=lambda f: -f["ent"])
    n_ent_all = sum(1 for j in active if j["entry"])
    guide("entry-level-jobs", "Where beginners are hired: entry-level jobs by field",
          f"{n_ent_all:,} of {n:,} open jobs are internships or junior roles. Which fields have them, which employers hire the most beginners, and how to find the rest.", "First job",
          f"{n_ent_all:,} of the {n:,} open jobs are internships or junior roles: {pc_(n_ent_all, n)}%. Most titles do not name a level at all, so the real number of jobs a beginner can get is larger than the label suggests.",
          "<h2>Internships and junior roles, field by field</h2><p>The number of open jobs whose title says intern, junior, graduate or the like.</p>"
          + bars_([(f["fn"], f["ent"], f'{f["ent"]:,} jobs', f'categories/{f["fs"]}/entry-level/' if f["ent"] >= 20 else f'categories/{f["fs"]}/') for f in by_ent])
          + "<h2>Employers with the most entry-level jobs</h2>" + bars_([(c, k, f"{k:,} jobs", f"companies/{slugify(c)}/") for c, k in entry_co[:10] if k])
          + f"<h2>Jobs that do not say “junior”</h2><p>A posting with no level in the title is usually a mid-level one, but not always: read how many years it asks for. In the <a href=\"{P}/for-you/\">match by five answers</a>, “I am starting out” lists the entry-level jobs first "
            f"and then the ones that name no level, each marked as such. Kinds of work that often take beginners: sales development, customer support, and AI training and data annotation.</p>",
          '<span class="ex">today</span>' + mini([(f["fn"], f["ent"], f'{f["ent"]:,}') for f in by_ent]),
          (("entry-level/", "All entry-level jobs"), ("internships/", "Internships"), ("categories/internships-entry-level/", "Internships and first jobs")))

    # 5. skills in demand
    top_sk = skill_counts.most_common(15)
    guide("skills-in-demand", "The skills employers ask for most, in plain words",
          f"The 15 skills named in the most open job postings today, each explained in one line: from {top_sk[0][0]} ({top_sk[0][1]:,} jobs) down.", "Skills",
          f"Job postings name tools and methods as if everyone knew them. These are the fifteen named most often in {n:,} open postings, with a plain line for each.",
          "<h2>Asked for in the most postings</h2>" + bars_([(t, k, f"{k:,} jobs · {pc_(k, n)}%", f"skills/{tslug(t)}/") for t, k in top_sk])
          + '<h2>What each one is</h2><dl class="qa">' + "".join(f"<div><dt>{e(t)}</dt><dd>{e(skills_info.plain(t)) or 'No plain description yet.'}</dd></div>" for t, _ in top_sk) + "</dl>"
          + f"<h2>Using this</h2><p>Write the skills you have by the names postings use: screening software looks for the word. The <a href=\"{P}/resume/\">resume builder</a> shows, while you type, how many open jobs ask for each skill it finds in your text.</p>",
          '<span class="ex">today</span>' + mini([(t, k, f"{k:,}") for t, k in top_sk]),
          (("skills/", "All skills"), ("insights/highest-paying-tech-skills/", "The skills with the highest advertised pay"), ("compare/", "Compare two skills")))

    # 6. levels
    lvl_rows = []
    for lv, lab_, what_ in (("Intern", "Intern", "a placement during studies or straight after, usually for a fixed number of months"), ("Junior", "Junior", "a first full job in the field; the employer expects to teach"),
                            ("", "No level in the title", "most often a mid-level job: able to work alone on ordinary tasks"), ("Senior", "Senior", "years of practice; solves hard problems without being told how, and helps others"),
                            ("Lead", "Lead, staff, principal, manager", "sets the direction for a team or a large part of the product, with or without managing people")):
        js_ = [j for j in active if j["level"] == lv]
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in js_ if j["usd"]]
        lvl_rows.append((lab_, what_, len(js_), median(mids_) if len(mids_) >= 30 else 0))
    guide("job-levels-explained", "Intern, junior, senior, lead: what the level in a job title means",
          "What each level in a job title means in plain words, how many open jobs carry it and what they advertise as pay, counted from today’s postings.", "Reading postings",
          f"A level in a title is the employer’s shorthand for how much experience it wants. Half of the postings do not use one. This is what each means, with today’s counts and pay.",
          "<h2>Advertised pay by level</h2><p>The median of the yearly ranges stated in postings of each level.</p>"
          + bars_([(lab_, md_, money(md_), "salaries/") for lab_, _, _, md_ in lvl_rows if md_])
          + '<h2>What each level means</h2><dl class="qa">' + "".join(f"<div><dt>{e(lab_)} · {k:,} open jobs</dt><dd>{e(what_[0].upper() + what_[1:])}.</dd></div>" for lab_, what_, k, _ in lvl_rows) + "</dl>"
          + f"<h2>Titles differ between companies</h2><p>A “senior” at one company is a “staff” at another, and banks call most people “vice president”. Read the years of experience and the tasks in the posting, not only the word. "
            f"The <a href=\"{P}/salaries/\">salary pages</a> show the pay ladder for each kind of work.</p>",
          '<span class="ex">today</span>' + mini([(lab_.split(",")[0], md_, money(md_)) for lab_, _, _, md_ in lvl_rows if md_]),
          (("salaries/", "Salary data by role and level"), ("guides/entry-level-jobs/", "Where beginners are hired"), ("glossary/", "Glossary of job-search terms")))

    # 7–9. how-to guides
    guide("is-this-job-still-open", "How to tell whether a job posting is still open",
          "Four checks that take a minute: the date, the employer’s own page, the wording of the posting and how long it has been open.", "Reading postings",
          "Job sites copy postings from each other and keep them after the employer has closed them. Four checks tell you in a minute whether a posting is worth an evening.",
          '<ol class="steps"><li><b>Look at the date the employer posted it.</b> Not the date a job site found it. Here both are on the job page.</li>'
          "<li><b>Ask the employer’s own page.</b> If the posting is gone there, it is closed, whatever a job site says. On this site the button “Check with the employer right now” does it from your browser.</li>"
          "<li><b>Read the first lines for an invitation.</b> “Join our talent community”, “general application”, “future opportunities” mean there is no opening today.</li>"
          f"<li><b>Count the days.</b> A posting open for {LONG_OPEN} days or more may still be real, and it is fair to ask the recruiter whether the role is being filled now.</li></ol>"
          f"<h2>What this site does about it</h2><p>Every posting is read from the employer’s own hiring system each hour. When one disappears there, it leaves the lists here and its page is marked closed. Today that happened to {closed_today_h:,} postings; "
          f"{long_all:,} open ones carry the “open {LONG_OPEN} days or more” mark.</p>",
          '<span class="ln"><b>Still open</b> · confirmed 14:02</span>' + skel,
          (("guides/how-long-jobs-stay-open/", "How long postings stay open"), ("safety/", "How to check that an offer is real"), ("status/", "Is the data fresh?")))
    guide("how-to-read-a-job-posting", "How to read a job posting: what each part tells you",
          "The six parts of a job posting and what to look for in each: the title, the place, the pay, what you must have, what is nice to have, and how to apply.", "Reading postings",
          "A posting is written by a busy person from a template. Knowing what each part usually means saves you from applying to the wrong jobs and from skipping the right ones.",
          '<dl class="qa"><div><dt>The title</dt><dd>It names the work and often the level. The same work has many titles, so search by the kind of work, not one title.</dd></div>'
          "<div><dt>The place</dt><dd>“Remote” with a country means you must live there. “Hybrid” means some days in the office: ask how many. No country at all usually means anywhere.</dd></div>"
          "<div><dt>The pay</dt><dd>A range is what the employer may pay, not what it will. The bottom is for someone who meets the minimum; the top is rarely offered at once.</dd></div>"
          "<div><dt>What you must have</dt><dd>Usually five to eight lines. If you meet most of them, apply: the list describes an ideal person, and those are rare.</dd></div>"
          "<div><dt>What is nice to have</dt><dd>Extras. They matter when two candidates are otherwise equal.</dd></div>"
          "<div><dt>How to apply</dt><dd>A real employer asks you to apply on its own site or hiring system and never asks for money, a copy of a passport or a wallet before a contract.</dd></div></dl>"
          f"<h2>See it on a real posting</h2><p>The home page takes one of today’s postings apart, part by part. The <a href=\"{P}/tools/resume-match/\">resume match checker</a> compares the “must have” lines with your resume, "
          f"and the <a href=\"{P}/glossary/\">glossary</a> explains the terms.</p>",
          '<span class="ln"><b>Senior Data Analyst</b></span><span class="ln">Remote, Germany · $120K – $150K</span>' + skel,
          (("guides/job-levels-explained/", "What the level in a title means"), ("guides/who-states-the-pay/", "Who states the pay"), ("safety/", "Job offer safety")))
    guide("follow-up-after-applying", "When and how to follow up after applying for a job",
          "Wait a week, write three sentences, send it once. A short guide with the reminder and the letter ready to use.", "Applying",
          "Most applications get no answer, and silence does not always mean no. One short follow-up after a week is normal and sometimes moves an application to the top of the pile.",
          '<ol class="steps"><li><b>Wait seven days</b> after applying, or after the date the posting gave for answers.</li>'
          "<li><b>Write to a person if you can find one</b>: the recruiter named in the posting or on the company’s page. Otherwise reply to the confirmation email.</li>"
          "<li><b>Three sentences are enough.</b> Which job you applied for and when; one line on why you fit; that you are glad to send anything else they need.</li>"
          "<li><b>Send it once.</b> A second message a week later is the limit. After that, move on and keep the application marked as open.</li></ol>"
          f"<h2>The tools for it</h2><p>On a job page, “Remind me to follow up in 7 days” saves a calendar file with the reminder. The <a href=\"{P}/my-jobs/\">application tracker</a> shows which applications have gone quiet. "
          f"After an interview, the <a href=\"{P}/tools/thank-you-email/\">thank-you email</a> tool writes the letter from four fields.</p>",
          '<span class="ln"><b>Follow up: Data Analyst</b></span><span class="ln">Friday, 9:00 · your own calendar</span>' + skel,
          (("my-jobs/", "Application tracker"), ("tools/job-search-calculator/", "How many applications one offer takes"), ("tools/", "All tools")))

    # 10. office days in hybrid jobs: read from the full text of postings (a range "2 to 3 days" counts as its lower figure)
    OD_W = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
    OD_N = r"([1-5]|one|two|three|four|five)"
    OD_RX = [re.compile(OD_N + r"(?:\s*(?:-|–|to|or)\s*(?:[1-5]|two|three|four|five))?\+?\s+(?:full\s+)?days?\s+(?:a|per|each|every|of the)\s+week\s+(?:in|at|from|on)[- ](?:the\s+|our\s+|an?\s+|one of our\s+)?(?:office|site|on-?site|hub|studio|headquarters|hq|location)", re.I),
             re.compile(r"(?:in|at)\s+(?:the|our)\s+(?:office|hub|studio)\s+(?:at least\s+|a minimum of\s+)?" + OD_N + r"\s+days?\s+(?:a|per|each)\s+week", re.I),
             re.compile(r"office\s+" + OD_N + r"\s+days?\s+(?:a|per|each)\s+week", re.I),
             re.compile(OD_N + r"\s+days?\s+(?:in|at)[- ](?:the\s+)?office", re.I),
             re.compile(r"(?:in[- ]office|on[- ]?site|in[- ]person)\s+" + OD_N + r"\s+days?\s+(?:a|per|each)\s+week", re.I)]
    od_ = Counter()
    for j in all_desc:
        for rx_ in OD_RX:
            m_ = rx_.search(j["desc"])
            if m_:
                od_[int(OD_W.get(m_.group(1).lower(), m_.group(1)))] += 1
                break
    n_od = sum(od_.values())
    if n_od >= 50:
        top_d = od_.most_common(1)[0]
        hy_c = Counter(c for j in hyb_ for c in {x for x, _ in countries_of(j.get("location") or "")})
        cnames_ = {c: nm for c, nm, _, _ in COUNTRIES}
        cnames_["US"] = "United States"
        dw_ = lambda d_: f"{d_} day{'s' if d_ > 1 else ''}"
        guide("office-days-in-hybrid-jobs", "How many days in the office: what hybrid job postings ask for",
              f"{n_od:,} open postings say how many days a week to be in the office, and {pc_(top_d[1], n_od)}% of them ask for {dw_(top_d[0])}. The full count, where hybrid jobs are and what to ask before you apply.", "Remote work",
              f"{len(hyb_):,} of the {n:,} open jobs here are hybrid: some days at home, some in the office. {n_od:,} of the {len(all_desc):,} postings with a full description say how many office days a week they expect, and {pc_(top_d[1], n_od)}% of those ask for {dw_(top_d[0])}.",
              "<h2>Office days a week, as postings state them</h2><p>Each column counts the postings that name that many days. Where a posting gives a range, such as “2 to 3 days”, the lower figure is counted.</p>"
              '<div class="pics two"><figure class="pic">' + cols([(f"{d_} day{'s' if d_ > 1 else ''}", od_.get(d_, 0)) for d_ in range(1, 6)], top_d[0] - 1) + "</figure></div>"
              + f"<p>{od_.get(5, 0):,} of them ({pc_(od_.get(5, 0), n_od)}%) ask for five days a week in the office: whatever the posting calls it, that is an office job.</p>"
              + ("<h2>Where the hybrid jobs are</h2><p>The countries named most often in the locations of today’s hybrid jobs: "
                 + ", ".join(f"{fl(c)}{e(cnames_.get(c, c))} ({k:,})" for c, k in hy_c.most_common(6)) + f". The <a href=\"{P}/hybrid/\">list of hybrid jobs</a> has all of them.</p>" if hy_c else "")
              + "<h2>What to ask before you apply</h2><ol class=\"steps\">"
                "<li><b>Which days?</b> Fixed days for the whole team, or days you choose. Fixed days mean you meet your team; chosen days can mean an empty office.</li>"
                "<li><b>Is it in the contract?</b> A policy can change next year; a term in your contract is harder to change.</li>"
                "<li><b>What does the commute cost?</b> Count the time and the fare for the days asked, and ask whether the employer pays any of it.</li>"
                "<li><b>What if you move?</b> Ask whether the role could become remote later, and what happens if it cannot.</li></ol>"
              + f"<p>The <a href=\"{P}/tools/remote-work-savings/\">remote work savings</a> tool puts a figure on the days you would commute.</p>",
              '<span class="ex">today</span>' + mini([(f"{d_} days", k, f"{pc_(k, n_od)}%") for d_, k in od_.most_common(4)]),
              (("hybrid/", "All hybrid jobs"), ("remote/", "Remote jobs"), ("glossary/hybrid/", "Hybrid, explained")))

    # 11. what postings ask for besides tools: the situations of the interview question pages, counted over every full description
    assert len(IQ_SHORT) == len(IQ_RX)
    if len(all_desc) >= 500:
        th_all = sorted(((sum(1 for j in all_desc if iq_hit[j["id"]][i_]), IQ_SHORT[i_]) for i_ in range(len(IQ_RX))), key=lambda x: -x[0])
        nd_ = len(all_desc)
        ai_k = sum(1 for j in all_desc if iq_hit[j["id"]][IQ_SHORT.index("AI tools")])
        top3_ = ", ".join(f"{lab.lower()} ({pc_(k, nd_)}%)" for k, lab in th_all[:3])
        guide("what-postings-ask-besides-skills", "Beyond the tools: the work habits job postings ask for most",
              f"Counted in {nd_:,} open postings with a full description: {top3_}. What each means and how to show it in a resume and an interview.", "Reading postings",
              f"Postings name tools, and they also describe how the person should work. In today’s {nd_:,} open postings with a full description, the three named most are {e(top3_)}.",
              "<h2>What postings ask for, besides tools</h2><p>The share of postings whose text names each habit or situation. A posting can name several.</p>"
              + bars_([(lab, k, f"{pc_(k, nd_)}% · {k:,}", "interview-questions/") for k, lab in th_all])
              + f"<h2>AI tools are named in {pc_(ai_k, nd_)}% of postings</h2><p>{ai_k:,} postings mention AI tools, language models or assistants such as Copilot or ChatGPT. "
                "Be ready to say which ones you use and where you do not trust them: name real uses, and say how you check the output.</p>"
                "<h2>How to use this</h2><ol class=\"steps\">"
                "<li><b>Read the postings you want.</b> Note which of these habits they name, and which come up in several of them.</li>"
                "<li><b>Use their words.</b> If a posting says “stakeholders”, a resume line that says “worked with other departments” is found less often by a recruiter’s search.</li>"
                f"<li><b>Prepare one real example for each.</b> A situation, what you did and a result with a number. The <a href=\"{P}/tools/interview-answer-builder/\">interview answer builder</a> shapes it into a 60 to 90 second answer.</li>"
                f"<li><b>Check a posting in seconds.</b> The <a href=\"{P}/tools/job-description-keywords/\">keyword finder</a> lists the terms a posting repeats.</li></ol>",
              '<span class="ex">today</span>' + mini([(lab, k, f"{pc_(k, nd_)}%") for k, lab in th_all[:4]]),
              (("interview-questions/", "Interview questions by job"), ("guides/skills-in-demand/", "The skills asked for most"), ("tools/job-description-keywords/", "Keyword finder")))

    # 12. years of experience: what postings ask, by level and by field
    yrs_all = sorted(j["years"] for j in active if j.get("years"))
    if len(yrs_all) >= 500:
        y_band = [("1", lambda y: y <= 1), ("2", lambda y: y == 2), ("3", lambda y: y == 3), ("4", lambda y: y == 4), ("5", lambda y: y == 5),
                  ("6–7", lambda y: 6 <= y <= 7), ("8–9", lambda y: 8 <= y <= 9), ("10+", lambda y: y >= 10)]
        yb_ = [(lb, sum(1 for y in yrs_all if f_(y))) for lb, f_ in y_band]
        y_mode = max(range(len(yb_)), key=lambda i: yb_[i][1])
        lvl_rows = []
        for lv in ("Intern", "Junior", "Senior", "Lead"):
            ys_ = sorted(j["years"] for j in active if j.get("years") and j.get("level") == lv)
            if len(ys_) >= 20: lvl_rows.append((lv, ys_[len(ys_) // 2], len(ys_), sum(1 for y in ys_ if y >= 3)))
        jr_ = [j for j in active if j.get("years") and j.get("level") in ("Intern", "Junior")]
        jr3 = sum(1 for j in jr_ if j["years"] >= 3)
        fy_ = []
        for fs, fn, fd, live, js_ in fam_rows:
            ys_ = sorted(j["years"] for j in js_ if j.get("years"))
            if len(ys_) >= 50: fy_.append((fn, ys_[len(ys_) // 2], fs))
        fy_.sort(key=lambda x: -x[1])
        guide("years-of-experience", "How many years of experience jobs really ask for",
              f"{len(yrs_all):,} open postings name a number of years. The median is {yrs_all[len(yrs_all) // 2]}; junior postings ask for {next((m for lv, m, _, _ in lvl_rows if lv == 'Junior'), 2)}. By level, by field, and what to do when you have fewer.", "First job",
              f"{len(yrs_all):,} of the {n:,} open postings name how many years of experience they want. "
              + (f"The median, and the most common request, is {yb_[y_mode][0]} years." if yb_[y_mode][0] == str(yrs_all[len(yrs_all) // 2])
                 else f"The median is {yrs_all[len(yrs_all) // 2]} years, and the most common request is {yb_[y_mode][0]} years.")
              + (f" Even among junior and intern postings, {jr3:,} of {len(jr_):,} ask for three years or more." if len(jr_) >= 30 else ""),
              "<h2>Years asked, across all open postings</h2><p>Each column counts the postings that ask for that many years. A range such as “3 to 5 years” counts as its lower figure.</p>"
              '<div class="pics two"><figure class="pic">' + cols(yb_, y_mode) + "</figure></div>"
              + ("<h2>By the level in the title</h2><div class=\"tablewrap\"><table><tr><th>Level in the title</th><th>Median years asked</th><th>Postings that name a number</th><th>Ask for 3 years or more</th></tr>"
                 + "".join(f"<tr><td>{e(lv)}</td><td>{m}</td><td>{k:,}</td><td>{pc_(k3, k)}%</td></tr>" for lv, m, k, k3 in lvl_rows) + "</table></div>" if lvl_rows else "")
              + ("<h2>By field</h2><p>The median number of years asked, in fields where at least 50 postings name one.</p>"
                 + bars_([(fn, m, f"{m} years", f"categories/{fs}/") for fn, m, fs in fy_]) if fy_ else "")
              + "<h2>When you have fewer years than asked</h2><p>The number is a filter the employer chose, not a test. If you can do the duties the posting lists, "
                "apply, and put the evidence first: results with numbers from work, projects or study that match those duties. "
                f"The <a href=\"{P}/entry-level/\">entry-level list</a> and the “How to become…” pages show where beginners are hired today.</p>",
              '<span class="ex">today</span>' + mini([(f"{lb} yrs", k, f"{pc_(k, len(yrs_all))}%") for lb, k in sorted(yb_, key=lambda x: -x[1])[:4]]),
              (("entry-level/", "Entry-level jobs"), ("how-to-become/", "How to become…"), ("guides/job-levels-explained/", "What the level in a title means")))

    gcats = []
    for g_ in GUIDES:
        if g_[3] not in gcats: gcats.append(g_[3])
    gcard = lambda g_: (f'<a class="tcard" href="{P}/guides/{g_[0]}/"><span class="tprev wide" aria-hidden="true">{g_[4]}</span><span class="tbody"><b>{e(g_[1])}</b><span>{e(g_[2])}</span><i><u>Read</u></i></span></a>')
    page("guides/", f"Guides: the job market explained with today’s numbers | {SITE}",
         f"{len(GUIDES)} guides to finding work, each with figures recounted from {n:,} open jobs: remote work by field, who states the pay, how long postings stay open, entry-level jobs, skills in demand.",
         crumbs(("Guides", "")) + '<h1>Guides, with <span class="hl">today’s numbers</span> in them</h1>'
         f'<p class="lead">Advice about job search goes out of date, and the figures in it faster. Every guide here is recounted from the {n:,} open jobs each time they are read again, so a number you see is today’s.</p>'
         + "".join(section(c_, '<div class="tgrid">' + "".join(gcard(g_) for g_ in GUIDES if g_[3] == c_) + "</div>") for c_ in gcats)
         + f'<p class="note">More to read: the <a href="{P}/glossary/">glossary</a>, the <a href="{P}/safety/">job offer safety checklist</a>, the <a href="{P}/insights/">charts and rankings</a>.</p>')

    # Help: one page that answers what people would otherwise write to ask (the owner looked at the knowledge base of hh.ru and wants
    # nobody to have to write to support). Every answer is plain text on the page, findable by the filter and by search engines.
    HELP = [("Looking for a job", [
                ("Do I need an account?", "No. Searching, saving jobs, the tracker, the resume builder and every tool work without one. What you save is kept in your browser."),
                ("How do I apply for a job?", "Open the job and press “Apply on company site”. You apply on the employer’s own page; this site takes no part in it and charges nothing."),
                ("Why did a job I saved disappear from the lists?", "The employer closed it. Its page stays at the same address, marked as closed, and stays in “My jobs” so your notes are not lost."),
                ("How fresh are the jobs?", "The employers’ careers pages are read again every hour. Fresh postings show how many minutes or hours ago the employer posted them."),
                ("How can I be told about new jobs?", "On the “For you” page answer the five questions and press “Tell me when new jobs fit”. Your browser will notify you. No email is needed."),
                ("Can I search by voice or by plain words?", "Yes. Type or say something like “remote design jobs paying over 100 thousand”: the search reads the place, the pay and the level out of it."),
                ("Where is my data kept, and how do I delete it?", "In this browser only. “My jobs” has a button that erases everything, and another that saves a backup file.")]),
            ("Resume and tools", [
                ("Is the resume builder free?", "Yes, including the PDF and the Word file, with no limit on downloads."),
                ("Is my resume uploaded anywhere?", "No. The builder, the resume review and the match checker read the text inside your browser."),
                ("What does the resume review check?", "Six things a recruiter notices on a first read: what the first screen holds, duties instead of results, numbers, the skills list, gaps between dates and length. The formula for the score is on the tool’s page."),
                ("Do the tools use AI?", "The free tools do not: calculators are arithmetic, checkers count words and patterns, letter writers are templates. AI writing is part of the paid plan, Plus.")]),
            ("Plus and payments", [
                ("What is Plus?", "A paid plan for job seekers: an AI writer for the resume and letters, a resume reworded for each posting, interview questions for a posting, and an email when a job fits."),
                ("Is Plus a subscription?", "No. It is one payment for one, three or twelve months. When the period ends nothing is charged and there is nothing to cancel."),
                ("How do I pay?", "In crypto (USDT, BTC, ETH and other coins) on a checkout page. The plan switches on by itself when the network confirms the payment."),
                ("Do I have to pay to see or apply for jobs?", "No, never. Every job and its link to apply are free for everyone.")]),
            ("Employers", [
                ("How do I post a job?", "Create an employer account with an address on your company’s domain, paste the job and the link where people apply. A standard listing is free."),
                ("Why must I use a company email?", "So that nobody can post in your company’s name. A recruiter without such an address signs in with LinkedIn; such a job is marked “posted by a recruiter, not verified by the employer” and is read by a person before it appears. A domain can also be proved with a record in its DNS or a file on the site."),
                ("How fast does a paid placement start?", "At once after the payment is confirmed. The job is marked Featured or Pinned automatically; there is nobody to write to."),
                ("Our jobs are listed here although we never posted them. Why?", "They are read from the public feed of your hiring system and link to your own page. To correct or remove a listing, write to the contact on the employers page; it is done at the next update."),
                ("Can I see what a listing brought?", "The employer account shows views of the job page and clicks on “Apply” for each job.")]),
            ("Safety and trust", [
                ("How do I know a job is real?", "Every listing is read from the employer’s own hiring system and links to it. On the job page, “Check with the employer right now” lets your own browser confirm it."),
                ("Someone asked me for money or documents. What now?", "Stop and do not pay. A real employer never charges a candidate. The safety page lists the common schemes and what to do if you already paid."),
                ("How do I report a problem with a listing?", "Use the link “Report a problem with this listing” on the job page."),
                ("Where do the salary figures come from?", "Only from pay ranges that employers publish in their own postings. No surveys and no numbers sent in by users.")])]
    help_n = sum(len(qs) for _, qs in HELP)
    help_html = "".join(f'<div class="dirb helpb"><h2><span>{e(g_)}</span><span>{len(qs)}</span></h2><dl class="qa one">' + "".join(f'<div data-n="{e((q_ + " " + a_).lower())}"><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>' for q_, a_ in qs) + "</dl></div>" for g_, qs in HELP)
    help_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for _, qs in HELP for q_, a_ in qs]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("help/", f"Help: {help_n} answers for job seekers and employers | {SITE}",
         f"{help_n} short answers: how to apply, where your data is kept, how alerts work without email, what Plus is and how payment works, how employers post a job and what a paid placement does.",
         crumbs(("Help", "")) + '<h1>Help: the answer is probably <span class="hl">already here</span></h1>'
         f'<p class="lead">{help_n} short answers for job seekers and employers. Type a word to find yours.</p>'
         '<p class="dirfind"><input type="search" id="helpfilter" placeholder="Type a word, for example payment, resume or closed" aria-label="Find an answer"></p>'
         f'<p class="lead" id="helpnone" hidden>No answer with these words. ' + (f"Write to us: {contact}." if contact else "The contact is on the employers page.") + "</p>"
         f'<div id="help">{help_html}</div>'
         f'<p class="note">Longer explanations: <a href="{P}/guides/">guides</a>, <a href="{P}/methodology/">how the site works</a>, <a href="{P}/privacy/">privacy</a>, <a href="{P}/safety/">job offer safety</a>.</p>', head=help_ld)

    # The open hiring index: employers ranked by how openly they hire, from their own postings, once a quarter by name but recounted
    # daily. (hh.ru runs a vote for "best employers"; a vote needs a server and can be gamed, so the first edition counts what can be
    # counted. A vote can be added on top once accounts exist.)
    qtr = f"Q{(int(TODAY[5:7]) - 1) // 3 + 1} {TODAY[:4]}"
    ohi = []
    for s_, f in cfacts.items():
        if f["n"] < 20: continue
        pay_, fresh_, act_, ent_ = f["pay"] / f["n"], 1 - f["old"] / f["n"], min(1, 5 * f["week"] / f["n"]), min(1, 10 * f["entry"] / f["n"])
        ohi.append((round(40 * pay_ + 30 * fresh_ + 20 * act_ + 10 * ent_), s_, f, pay_, fresh_, act_, ent_))
    ohi.sort(key=lambda x: (-x[0], -x[2]["n"]))
    for i, (sc, s_, f, *_r) in enumerate(ohi[:50]):
        write(f"badge/open-hiring/{s_}.svg", badge_svg(f"Open hiring index {qtr}", f"#{i + 1} · {sc}/100"), sitemap=False)
    ohi_rows = "".join(trow([rank(i), cl(f["name"]), f"<strong>{sc}</strong>", f"{round(100 * pay_)}%", f"{round(100 * fresh_)}%", f"{f['week']:,}", f"{f['entry']:,}", f"{f['n']:,}"]) for i, (sc, s_, f, pay_, fresh_, act_, ent_) in enumerate(ohi[:50]))
    top1 = ohi[0] if ohi else None
    page("open-hiring-index/", f"Open Hiring Index {qtr}: employers ranked by how openly they hire | {SITE}",
         f"{len(ohi)} employers with 20 or more open jobs, ranked by what their own postings show: how often they state pay, how few postings they leave open for months, how much they hire now and for beginners.",
         crumbs(("Open hiring index", "")) + f'<h1>Open hiring index, {qtr}</h1>'
         '<p class="plain"><b>In plain words:</b> a score from 0 to 100 for how openly an employer hires. It is counted from the employer’s own job postings, not from votes or reviews.</p>'
         f'<p class="lead">{len(ohi)} employers with 20 or more open jobs. An employer scores high when it states the pay, does not leave postings open for months, is hiring this week and takes beginners.</p>'
         + bars_([(f["name"], sc, f"{sc} of 100", f"companies/{s_}/") for sc, s_, f, *_r in ohi[:12]])
         + ttable(["#", "Employer", "Score", "State the pay", f"Not open {LONG_OPEN}+ days", "Posted this week", "For beginners", "Open jobs"], [ohi_rows])
         + section("How the score is made", '<dl class="qa"><div><dt>States the pay: up to 40 points</dt><dd>The share of the employer’s open postings in which a pay range can be found.</dd></div>'
                   f'<div><dt>Does not let postings linger: up to 30 points</dt><dd>The share of its postings that are younger than {LONG_OPEN} days.</dd></div>'
                   "<div><dt>Is hiring now: up to 20 points</dt><dd>The share of its postings published in the last seven days; a fifth or more gives all 20.</dd></div>"
                   "<div><dt>Takes beginners: up to 10 points</dt><dd>The share of internships and junior roles; a tenth or more gives all 10.</dd></div></dl>"
                   "<p class=\"note\">The score says nothing about what it is like to work there: it measures the postings, and a missing pay figure can also be a wording our reader does not recognise. "
                   f"The table is recounted with every update; the name of the quarter changes four times a year.</p>")
         + (section("For employers on the list", f'<p>The 50 highest have a badge that shows their place today. Put it on a careers page or in a post:</p><pre><code>{e(f"<a href=\"{FULL}/open-hiring-index/\"><img src=\"{FULL}/badge/open-hiring/{top1[1]}.svg\" alt=\"Open hiring index {qtr}\"></a>")}</code></pre>'
                    f'<p class="note">This is the badge of {e(top1[2]["name"])}. For another employer replace <code>{e(top1[1])}</code> with the last part of the address of its page on this site.</p>'
                    f'<p><img src="{P}/badge/open-hiring/{top1[1]}.svg" alt="Open hiring index badge" height="28"></p>') if top1 else "")
         + f'<p class="note">Compare any two employers: <a href="{P}/companies/compare/">company against company</a>. Pay transparency alone: <a href="{P}/insights/pay-transparency/">the ranking</a>.</p>')

    # Facts for investors and partners: what exists, in numbers counted on this build. No forecasts, no revenue claims.
    n_pages_ = len(URLS)
    inv_facts = [("Open jobs", f"{n:,}"), ("Employers read every hour", f"{m:,}"), ("Pages", f"{n_pages_:,}"), ("Fields and kinds of work", f"{len(fam_rows)} / {len(by_role)}"), ("Free tools", f"{len(TOOLS) + len(tools_pages.EXTRA)}"), ("People on the payroll", "0")]
    page("investors/", f"For Investors and Partners: the facts | {SITE}",
         f"{SITE} in numbers counted today: {n:,} open jobs from {m:,} employers, {n_pages_:,} pages, how it is built, how it will earn and what stage it is at.",
         crumbs(("For investors and partners", "")) + '<h1>For investors and partners: <span class="hl">the facts</span></h1>'
         '<p class="lead">A job site that reads employers’ own hiring systems every hour, shows only what is still open and runs without staff. The numbers below are counted on this page’s build, not written by hand.</p>'
         '<div class="invf">' + "".join(f'<div><b>{e(v_)}</b><span>{e(k_)}</span></div>' for k_, v_ in inv_facts) + "</div>"
         + market_pics
         + section("How it earns", '<dl class="qa"><div><dt>Job seekers</dt><dd>Plus: one payment for one, three or twelve months for an AI resume writer, letters, interview preparation and alerts. Jobs and applying stay free.</dd></div>'
                   "<div><dt>Employers</dt><dd>A standard listing is free; featured and pinned listings, a company spotlight and sponsorship of a field are paid, self-serve, and start the moment the payment is confirmed.</dd></div>"
                   "<div><dt>Sites and partners</dt><dd>Widgets, feeds and an API bring the listings to other sites and channels with a link back; unbranded and extended versions are planned as paid.</dd></div></dl>")
         + section("Where it stands", '<dl class="qa"><div><dt>Built</dt><dd>The site, the hourly collection, the directory of fields and roles, 28 tools and a resume builder, rankings and charts, the accounts and payments server with fraud checks and its tests.</dd></div>'
                   "<div><dt>Not yet</dt><dd>Payments are not switched on, so there is no revenue to report. The site is on a temporary address; its own domain comes next.</dd></div>"
                   "<div><dt>Costs</dt><dd>Hosting and collection run on free tiers; the site is built and maintained by automation, with nobody on the payroll.</dd></div></dl>")
         + f'<p class="note">Data and method: <a href="{P}/methodology/">how the numbers are made</a>, <a href="{P}/status/">what the last update did</a>, <a href="{P}/insights/">charts</a>. ' + (f"To talk: {contact}." if contact else "") + "</p>")

    # One XML file for job search engines (Careerjet, Adzuna, Trovit and others take a feed of this shape: source/job with
    # referencenumber, title, url, company, city, country, date, description). It holds the jobs posted in the last 30 days, the
    # newest first, 10,000 at most: we keep only the opening lines of a posting, and the link leads to our page of the job.
    # Who takes such a feed and on what terms: AGGREGATORS_RESEARCH.md.
    cd_ = lambda v: "<![CDATA[" + str(v).replace("]]>", "]]]]><![CDATA[>") + "]]>"
    month_ago = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    feed_jobs = [j for j in order(active) if (j["posted"] or "") >= month_ago and j["excerpt"] and not j.get("pool")][:10000]
    JT = {"Full-time": "fulltime", "Part-time": "parttime", "Contract": "contract", "Internship": "internship"}
    feed_items = "".join(
        "<job>" + f"<title>{cd_(j['title'])}</title><date>{cd_((j['posted'] or TODAY)[:10] + 'T00:00:00Z')}</date><referencenumber>{cd_(j['id'])}</referencenumber>"
        f"<url>{cd_(FULL + '/job/' + j['slug'] + '/')}</url><company>{cd_(j['company'])}</company><city>{cd_(j['location'] or '')}</city><country>{cd_((country_of(j['location'] or '') or ('',))[0])}</country>"
        f"<remotetype>{cd_('Fully remote' if j['remote'] else '')}</remotetype><description>{cd_(e(j['excerpt']) + ' … The full posting and the link to apply are on the page of the job.')}</description>"
        f"<salary>{cd_(j['salary'] or '')}</salary><jobtype>{cd_(JT.get(j.get('etype') or '', ''))}</jobtype><category>{cd_(CAT.get(j['cat'], ''))}</category></job>" for j in feed_jobs)
    write("feeds/jobs.xml", f'<?xml version="1.0" encoding="UTF-8"?><source><publisher>{e(SITE)}</publisher><publisherurl>{FULL}/</publisherurl>'
                            f"<lastBuildDate>{format_datetime(datetime.datetime.now(datetime.timezone.utc))}</lastBuildDate>{feed_items}</source>", sitemap=False)

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
    fy_places = "".join(f'<option value="{c_}" data-s="{code_slug_all.get(c_, "")}" data-r="{region_of.get(c_, "")}">{flag_of(c_)} {e(nm_)}</option>'
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
         f'<p class="note no-print">Not sure how to start? <a href="{P}/resume/examples/">Open a resume example for your kind of work</a> and replace it line by line.</p>'
         '<div id="rb-demand" class="no-print" aria-live="polite"></div>'
         '<div class="rgrid"><div id="rb-form"></div><div id="rb-preview" aria-live="polite"></div></div></div>'
         + '<section class="sec no-print"><div class="sec-head"><h2>What makes a resume get read</h2></div><div class="feats">'
         '<div class="feat"><h3>One page, plain layout</h3><p>Screening software reads simple single-column text best. That is the layout you get here.</p></div>'
         '<div class="feat"><h3>Results, not duties</h3><p>“Cut page load time from 4s to 1.2s” says more than “responsible for performance”.</p></div>'
         '<div class="feat"><h3>The posting’s own words</h3><p>If the job asks for PostgreSQL and you know it, write PostgreSQL, not “databases”.</p></div></div></section>'
         + f'<script src="{P}/resume.js?v={V}" defer></script>')

    # Glossary: the words of a job search in plain English, one page per term (glossary_terms.py) and an index with the old anchors,
    # so links to /glossary/#remote keep working. PeopleForce's glossary is its main free asset; ours adds what to do and a figure.
    GT = glossary_terms.TERMS
    gslug = lambda t: re.sub(r"[^a-z0-9]+", "-", re.sub(r"\(.*?\)", "", t.lower())).strip("-")
    n_act = len(active)
    descs_ = [j for j in active if j.get("desc")]
    paid_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in active if j["usd"])
    perk_n = Counter(x for j in active for x in j.get("perks", []))
    et_n = Counter(j.get("etype", "") for j in active)
    gfig = {   # a figure counted from today's postings, where the term has one
        "Remote": f"{sum(1 for j in active if j['remote']):,} of the {n_act:,} open jobs here are remote ({pc_(sum(1 for j in active if j['remote']), n_act)}%).",
        "Hybrid": f"{sum(1 for j in active if j.get('hybrid')):,} of the {n_act:,} open jobs here are hybrid.",
        "Contract": f"{et_n.get('Contract', 0):,} of today’s open jobs are marked as contract work.",
        "Internship": f"{et_n.get('Internship', 0):,} internships are open today.",
        "Full-time and part-time": f"{et_n.get('Full-time', 0):,} open jobs are marked full-time and {et_n.get('Part-time', 0):,} part-time; the rest do not say.",
        "Visa sponsorship": f"{perk_n.get('Visa sponsorship', 0):,} of today’s open jobs mention visa sponsorship.",
        "Relocation": f"{perk_n.get('Relocation support', 0):,} of today’s open jobs mention help with relocation.",
        "Equity and stock options": f"{perk_n.get('Equity', 0):,} of today’s open jobs mention equity.",
        "Salary range": f"{pc_(sum(1 for j in active if j['salary']), n_act)}% of today’s open jobs state a pay range.",
        "Pay transparency": f"{pc_(sum(1 for j in active if j['salary']), n_act)}% of today’s open jobs state a pay range.",
        "Entry-level": f"{sum(1 for j in active if j['entry']):,} of today’s open jobs have a junior or intern title.",
        "Work from anywhere": f"{sum(1 for j in active if j.get('anywhere')):,} of today’s remote jobs name no country or region.",
        "Talent pool": f"{sum(1 for j in active if j['pool']):,} of today’s listings are talent pools rather than openings.",
        "Cover letter": (f"Only {sum(1 for j in descs_ if re.search(r'cover[ -]*letter', j['desc'], re.I)):,} of the {len(descs_):,} open postings here with a full description mention a cover letter in their text." if len(descs_) >= 100 else ""),
        "Median": (f"The median advertised pay of today’s open jobs that state a yearly US-dollar range is {money(median(paid_))}." if len(paid_) >= 50 else ""),
        "Base salary": (f"The middle half of today’s postings that state pay offer {money(paid_[len(paid_) // 4])} to {money(paid_[3 * len(paid_) // 4])} a year." if len(paid_) >= 50 else ""),
    }
    for i, (term, d, tip, links) in enumerate(GT):
        sl = gslug(term)
        fig = gfig.get(term, "")
        prev_, next_ = GT[i - 1], GT[(i + 1) % len(GT)]
        ld_ = ('<script type="application/ld+json">' + json.dumps([
            {"@context": "https://schema.org", "@type": "DefinedTerm", "name": term, "description": d, "url": f"{FULL}/glossary/{sl}/",
             "inDefinedTermSet": {"@type": "DefinedTermSet", "name": "Job search glossary", "url": f"{FULL}/glossary/"}},
            {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": f"What is {term[0].lower() + term[1:] if not term[:2].isupper() else term}?",
                                                                              "acceptedAnswer": {"@type": "Answer", "text": d}}]}], ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page(f"glossary/{sl}/", f"{term}: What It Means in a Job Search | {SITE}",
             f"{term}, explained in plain English: {d[0].lower() + d[1:] if not d[:2].isupper() else d}",
             crumbs(("Glossary", "glossary/"), (term, "")) + f'<h1>{e(term)}</h1>'
             f'<p class="lead gl-def">{e(d)}</p>'
             + (f'<p class="gl-fig">{e(fig)} <span class="note">Counted on {fdate(TODAY)}.</span></p>' if fig else "")
             + section("What to do about it", f"<p>{e(tip)}</p>")
             + section("Useful next", '<div class="rel">' + "".join(f'<a href="{P}/{u}">{e(lbl)}</a>' for u, lbl in links) + "</div>")
             + f'<p class="note cmpl">Other terms: <a href="{P}/glossary/{gslug(prev_[0])}/">{e(prev_[0])}</a> · <a href="{P}/glossary/{gslug(next_[0])}/">{e(next_[0])}</a> · <a href="{P}/glossary/">all {len(GT)} terms</a></p>', head=ld_)
    gl_rows = "".join(f'<div id="{gslug(t)}"><dt><a href="{P}/glossary/{gslug(t)}/">{e(t)}</a></dt><dd>{e(d)}</dd></div>' for t, d, _, _ in sorted(GT, key=lambda x: x[0].lower()))
    page("glossary/", f"Job Search Glossary: {len(GT)} Hiring Terms Explained in Plain English | {SITE}",
         f"{len(GT)} words you meet when looking for a job or hiring, each explained in plain English with what to do about it: ATS, OTE, vesting, notice period, remote, hybrid, visa sponsorship and more.",
         crumbs(("Glossary", "")) + f'<h1>Job search glossary: <span class="hl">{len(GT)} terms in plain English</span></h1>'
         f'<p class="lead">The words that come up in job postings, interviews and offers, each explained in a sentence or two. Open a term for what to do about it and, where there is one, a figure from today’s {n_act:,} open postings.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a word, for example vesting or hybrid" aria-label="Find a term"></p>'
         '<dl class="qa gl-index" id="dir">' + gl_rows + "</dl>",
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "Job search glossary", "url": f"{FULL}/glossary/",
               "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t, "description": d, "url": f"{FULL}/glossary/{gslug(t)}/"} for t, d, _, _ in GT]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")

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
         + section("Questions about the job widget", w_faq_html)
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
             + section(f"Questions about the job widget for {pname}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in p_faq) + "</dl>")
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
    was_span = lambda pl: (f'<s class="was">{e(pl["was"])}</s> ' if pl.get("was") else "")
    def per_day(pl):
        m_ = re.search(r"\d+", pl["price"]); k_ = re.search(r"\d+", pl["name"])
        if not m_ or not k_: return ""
        days_ = {1: 30, 3: 91, 12: 365}.get(int(k_.group(0)), 30 * int(k_.group(0)))
        return f"{round(100 * int(m_.group(0)) / days_)} cents a day"
    plans = "".join(
        f'<div class="plan{" best" if pl.get("best") else ""}">' + (f'<span class="pill acc">{e(pl["note"])}</span>' if pl.get("note") else '<span class="pill ghost">–</span>')
        + f'<p class="pname">{e(pl["name"])}</p><p class="price">{was_span(pl)}{e(pl["price"])}</p><p class="note">{e(pl["per"])} · <b>{per_day(pl)}</b></p>{cta}</div>' for pl in plus["plans"])
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
             + (f'<p class="tp">{was_span(low_plan)}{e(low_plan["price"])}<small> for {e(low_plan["name"])} · {per_day(low_plan)}</small></p>' if low_plan else '<p class="tp">Plus</p>')
             + '<p class="td">Everything in Free, plus an AI writer for your resume and letters, and an email when a job fits. One payment, nothing renews.</p>' + cta
             + tick(["AI resume writer and editor: bullet points and summary from your notes", "Resume reworded for each posting, with the keywords it misses", "AI resume review: score, weak points, rewrites",
                     "AI cover letters, thank-you and resignation letters", "Interview practice: questions for the posting and feedback on your answers", "An email the day a job fits your answers",
                     "Pay check with a script for negotiating", "AI review of your LinkedIn profile", "As many resumes as you like, all five templates", "Your jobs and resumes on every device",
                     "One payment: nothing renews, no card on file"]) + "</div>"
             '<div class="tier"><p class="tn">Employers</p><p class="tp">Free<small> to post a job</small></p><p class="td">A standard listing costs nothing. A featured one stays at the top of its list.</p>'
             f'<a class="btn ghost" href="{P}/post-a-job/">Post a job</a>'
             + tick(["A standard listing for 30 days", f"Featured job from {price_of('Featured job')}", "Pinned job, company spotlight, sponsor of a category", "Paid in crypto, switched on at once", "No calls, no sales manager"]) + "</div></div>")
    ai_m = re.search(r"AI_MONTHLY\s*=\s*\{\s*resume:\s*(\d+),\s*letter:\s*(\d+),\s*interview:\s*(\d+)", (ROOT / "server" / "src" / "worker.js").read_text(encoding="utf-8") if (ROOT / "server" / "src" / "worker.js").exists() else "")
    ai_allow = f"{ai_m.group(1)} resume tasks, {ai_m.group(2)} letters, {ai_m.group(3)} interview sessions" if ai_m else "Shown before you pay"
    plus_price = " · ".join(f'{was_span(pl)}<b>{e(pl["price"])}</b> for {e(pl["name"])}' for pl in plus["plans"]) or "Plus"
    seek_pt = ptable([("Free", "<b>$0</b>", "No account, no card", False), ("Plus", (f'from {was_span(plus["plans"][0])}<b>{e(plus["plans"][0]["price"])}</b>' if plus["plans"] else "Plus"), "One payment. Nothing renews", True)], [
        ("Resume",), ("Resume builder", "All 5 templates", "All 5 templates"), ("Resumes kept", "~1, in this browser", "Unlimited, on every device"), ("PDF and Word downloads", "Unlimited", "Unlimited"),
        (f"Resume examples for {len(rex_data)} kinds of work", True, True),
        ("AI writer",), ("AI writer for bullet points and summary", False, True), ("Keywords for one posting", "~Found and missing", "Bullets reworded for the posting"),
        ("Resume review and score", "~By rules", "By AI, with rewrites"), ("LinkedIn profile review", "~By rules", "By AI"), ("AI use each month", False, ai_allow),
        ("Letters",), ("Cover letter", "~Fill-in template", "AI draft from your resume and the posting"), ("Thank-you, raise and resignation letters", "~Templates", "AI drafts"),
        ("Interview and pay",), ("Interview questions for one posting, with feedback on your answers", False, True), ("Salary checker and offer check", True, True), ("Script for negotiating an offer", False, True),
        ("Jobs",), ("Every job and the link to apply", True, True), ("Matching by five answers, with reasons", True, True), ("An email the day a job fits", False, True),
        ("Application tracker", "~On this device", "On every device"),
        ("Payment",), ("How you pay", "~Nothing to pay", "Once, in crypto"), ("Renews by itself", "~Nothing to renew", "Never")])
    yes, no = '<td class="y">Yes</td>', '<td class="n">—</td>'
    cell = lambda v: yes if v is True else no if v is False else f"<td>{e(v)}</td>"
    grid_rows = [("Jobs", None, None), ("Every job and the link to apply", True, True), ("Search, categories, salary data, rankings", True, True), ("Matching by five answers", True, True), ("An email when a job fits", False, True),
                 ("Resume", None, None), ("Resume builder, 5 templates", True, True), ("PDF and Word downloads", "Unlimited", "Unlimited"), ("Resume review", "By rules", "By AI, with rewrites"),
                 ("Match against a posting", "Keywords found and missing", "Bullets reworded for the posting"), ("AI writer for bullet points and summary", False, True),
                 ("Letters", None, None), ("Cover letter", "Fill-in template", "Draft from your resume and the posting"), ("Thank-you, raise and resignation letters", "Templates", "AI drafts"),
                 ("Interview and pay", None, None), ("Interview questions for one posting", False, True), ("Salary checker and offer check", True, True), ("Script for negotiating an offer", False, True),
                 ("Tracking", None, None), ("Application tracker", "On this device", "On every device"), ("LinkedIn profile review", "By rules", "By AI")]
    grid_html = "".join(f'<tr class="grp"><th colspan="3">{e(a_)}</th></tr>' if b_ is None else f"<tr><td>{e(a_)}</td>{cell(b_)}{cell(c_)}</tr>" for a_, b_, c_ in grid_rows)
    # what the same things cost elsewhere: the plans other services publish, read on their own pricing pages on the date given
    else_rows = [("AI resume writer and editor, resume score, keywords for a job", "Plus", "Rezi Pro: $29 a month"),
                 ("Resume review and LinkedIn review", "Free by rules; by AI in Plus", "RocketHunt Pro: 290 ₽ a month"),
                 ("Match with a job, skill by skill", "Free", "RocketHunt Pro: 290 ₽ a month"),
                 ("What a role pays and whether an offer is fair", "Free", "RocketHunt Pro: 290 ₽ a month"),
                 ("Cover letters without a limit", "Template free; AI drafts in Plus", "hh PRO: 999 ₽ a month"),
                 ("Resume downloads as PDF and Word", "Free, no limit", "Rezi Free: 3 PDF files; Word only in Pro"),
                 ("Interview practice with AI", "Plus", "Rezi Free: 1 interview; more in Pro"),
                 ("How the payment works", "One payment, ends by itself", "Monthly, renewed automatically")]
    else_html = ('<div class="tablewrap"><table class="grid"><tr><th>What you get</th><th>Here</th><th>Elsewhere</th></tr>'
                 + "".join(f"<tr><td>{e(a_)}</td><td class=\"y2\"><strong>{e(b_)}</strong></td><td>{e(c_)}</td></tr>" for a_, b_, c_ in else_rows)
                 + '</table></div><p class="note">The right-hand column is what each service published on its own pricing page on November 13, 2026. Prices change; check theirs before you compare.</p>')
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
         "Plus reviews your resume, rewords it for each posting, drafts the cover letter, prepares you for the interview and emails you when a job fits. One payment, a few cents a day, nothing renews. Every job stays free.",
         crumbs(("Plus", "")) + '<h1>Applications go out and nothing comes back. Plus finds out why and <span class="hl">fixes it</span>, job by job</h1>'
         '<p class="lead">A resume gets one short first read, and nobody tells you why it was put aside: the result is on page two, the bullets list duties, the letter could be for any company. '
         f'Plus reads your resume the way a recruiter does, rewords it for each posting and tells you the day a job fits. One payment, from {min((per_day(pl) for pl in plus["plans"]), key=lambda x: int(x.split()[0])) if plus["plans"] else "a few cents a day"}. Nothing renews.</p>{soon}'
         + LAUNCH + tiers
         + section("Free and Plus, side by side", seek_pt + f'<p class="note">Hiring? Employers have their own table on the <a href="{P}/pricing/#employers">pricing page</a>.</p>')
         + section("What Plus adds", pcard_html)
         + section("What it costs", f'<div class="plans">{plans}</div><p class="note">You pay once, in crypto, on a checkout page, and Plus switches on when the payment is confirmed. '
                   'There is no automatic renewal, no card on file and nothing to cancel: when the period ends, Plus simply ends.</p>')
         + section("What the same things cost elsewhere", else_html)
         + section("What stays free, for everyone", f'<div class="dir free"><div class="dirb"><ul>{free_now}</ul></div></div>')
         + section("Questions about Plus", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in plus_qa) + "</dl>"), head=plus_ld)
    # Employers
    rows = "".join(f"<tr><td><strong>{e(p['name'])}</strong></td><td>{was_of(p['name'])}<strong>{e(p['price'])}</strong></td><td>{e(p['what'])}{' <span class=\"note\">Not available yet.</span>' if p.get('soon') else ''}</td></tr>" for p in CFG["prices"])
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
    # What an employer gets the moment the payment is confirmed, shown rather than described (the owner: "show what they get at once:
    # how the listing is highlighted, what appears in the account").
    etick = lambda items: '<ul class="ticks">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
    ebtn = (f'<a class="btn ghost" href="{e(app_url)}">Post a job</a>' if app_url else '<button class="btn ghost" type="button" disabled>Opens soon</button>')
    emp_tiers = ('<div class="tiers">'
                 f'<div class="tier"><p class="tn">Standard</p><p class="tp">Free</p><p class="td">Your job in the list and in search, like every other job here.</p>{ebtn}'
                 + etick(["In the main list for 30 days", "Its own page, readable by Google’s job box", "A link straight to your application page", "Checked before it goes live", "Close or renew it yourself, any time"]) + "</div>"
                 f'<div class="tier best"><p class="tn">Featured</p><p class="tp">{was_of("Featured job")}{price_of("Featured job")}<small> for 14 days</small></p><p class="td">A highlighted row that stays above the regular listings of its category.</p>{ebtn}'
                 + etick(["Everything in Standard", "Highlighted row with a “Featured” mark", "Above regular listings in its category for 14 days", "On as soon as the payment is confirmed: nobody to write to", "Views and clicks to apply in your account"]) + "</div>"
                 f'<div class="tier"><p class="tn">Pinned</p><p class="tp">{was_of("Pinned job")}{price_of("Pinned job")}<small> for 7 days</small></p><p class="td">The first row on the home page and in its category.</p>{ebtn}'
                 + etick(["Everything in Featured", "First row of the home page for 7 days", "First row of its category", "Included in the feeds other sites and channels read"]) + "</div></div>")
    emp_pt = ptable([("Standard", "<b>Free</b>", "30 days in the list", False),
                     ("Featured", f'{was_of("Featured job")}<b>{price_of("Featured job")}</b> once', "14 days above regular jobs", True),
                     ("Pinned", f'{was_of("Pinned job")}<b>{price_of("Pinned job")}</b> once', "7 days in the first row", False)], [
        ("The listing",), ("In the list and in search", "30 days", "30 days", "30 days"), ("Its own page, readable by Google’s job box", True, True, True),
        ("A link straight to your application page", True, True, True), ("Checked before it goes live", True, True, True), ("Close or renew it yourself, any time", True, True, True),
        ("Where it stands",), ("Place in its category", "~By date", "Above regular jobs, 14 days", "First row, 7 days"), ("Highlighted row with a “Featured” mark", False, True, True),
        ("First row of the home page", False, False, "7 days"),
        ("Your account",), ("Starts", "~At the next hourly update", "Within the hour after payment", "Within the hour after payment"), ("Views and clicks to apply, per job", False, True, True),
        ("A receipt for every payment", "~Nothing to pay", True, True),
        ("Payment",), ("How you pay", "~Nothing to pay", "Once, in crypto", "Once, in crypto"), ("Renews by itself", "~Nothing to renew", "Never", "Never")])
    demo_rows = [dict(j) for j in latest[:4]]
    demo_job = {"featured": True, "active": True, "remote": True, "salary": "$140K - $180K", "level": "Senior", "tags": ["Python", "AWS"], "location": "Remote, Europe", "company": "Your company",
                "slug": "", "title": "Senior Backend Engineer (your job)", "posted": TODAY}
    demo_html = ('<ul class="jobs demo">' + card(demo_job).replace(f'href="{P}/job//"', 'href="#"') + "".join(card(j) for j in demo_rows[:2])
                 + card(dict(demo_job, title="Product Designer (your second job)", salary="", tags=["Figma"], level="")).replace(f'href="{P}/job//"', 'href="#"') + "".join(card(j) for j in demo_rows[2:4]) + "</ul>")
    emp_cab = ('<div class="tgrid">'
               '<div class="tcard"><span class="tprev" aria-hidden="true"><span class="ex">example</span><span class="ln"><b>Senior Backend Engineer</b></span><span class="rw"><span>Featured</span><span class="mt"><i style="width:64%"></i></span><b>9 days left</b></span>'
               '<span class="ln">Live since Nov 13 · <b>Renew</b> · <b>Close</b></span></span><span class="tbody"><b>The placement, switched on</b><span>The moment the network confirms the payment, the job is marked Featured and the account shows how many days are left. Nothing to send, nobody to wait for.</span></span></div>'
               '<div class="tcard"><span class="tprev" aria-hidden="true"><span class="ex">example</span><span class="rw"><span>Views</span><span class="mt"><i style="width:100%"></i></span><b>1,204</b></span><span class="rw"><span>Clicks to apply</span><span class="mt"><i style="width:22%"></i></span><b>86</b></span>'
               '<span class="ln">Counted per job, day by day</span></span><span class="tbody"><b>What the listing brought</b><span>Views of the job page and clicks on “Apply” for each job, so you can see what the placement did.</span></span></div>'
               '<div class="tcard"><span class="tprev" aria-hidden="true"><span class="ex">example</span><span class="ln"><b>Receipt</b> · Featured job · ' + price_of("Featured job") + '</span><span class="ln">Paid in USDT · confirmed 14:02</span><span class="sk" style="width:70%"></span></span>'
               '<span class="tbody"><b>A receipt and no renewal</b><span>Every payment is a single payment with a receipt in the account. When the period ends, the job goes back to a standard listing and nothing is charged.</span></span></div></div>')
    page("post-a-job/", f"Post a Tech Job — free listing, featured from {price_of('Featured job')} | {SITE}" if app_url else f"Post a Tech Job — plans and prices for employers | {SITE}",
         (f"Post a tech job for free, or feature it from {price_of('Featured job')} so it stays at the top of the list. Self-serve, paid in crypto at checkout." if app_url else
          f"Plans and prices for employers: free standard listings, featured jobs from {price_of('Featured job')}, company spotlight and page sponsorship. Self-serve posting is being finished and is not open yet."),
         crumbs(("For employers", "")) + "<h1>Post a tech job that doesn’t get buried</h1>"
         f'<p class="lead">There are {n:,} open roles from {m:,} companies here, sorted by date. A standard listing is free. '
         'A featured one stays at the top instead of sliding down as new roles arrive.</p>'
         + LAUNCH + emp_tiers
         + section("Standard, Featured and Pinned, side by side", emp_pt + f'<p class="note">Looking for work, not hiring? Job seekers have their own table on the <a href="{P}/pricing/">pricing page</a>.</p>')
         + section("How your job looks in the list", '<p class="note">The two highlighted rows are examples of featured jobs; the others are real listings from today.</p>' + demo_html)
         + section("What appears in your account at once", emp_cab)
         + f'{pain_html}' + section("Every plan and price", f'<div class="tablewrap"><table><tr><th>Plan</th><th>Price</th><th>What you get</th></tr>{rows}</table></div>')
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
    # Pricing: both sides on one page, each with its own table. A person looking for work and a company hiring buy different
    # things, so they never share a table (the owner: "for the job seeker and for the employer everything must be different").
    price_qa = [("Do I have to pay to see jobs or to apply?", "No. Every job is public and free to apply to, on the employer’s own page. Plus adds help with applying; it does not unlock listings."),
                ("How do I pay?", "In crypto, on a checkout page: USDT, BTC, ETH and other coins. Cards and bank transfers are not taken yet."),
                ("Will I be charged again?", "No. Every price here is a single payment. Nothing renews by itself, there is no card on file and nothing to cancel."),
                ("Why are the prices so low?", "They are launch prices, about a third of the regular ones, while the paid plans are new. The regular price is the one crossed out."),
                ("Can I buy today?", "Not yet. Payments are being connected; until then everything in the Free and Standard columns works as it does today.")]
    price_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in price_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    extra_rows = "".join(f"<tr><td><strong>{e(p_['name'])}</strong></td><td>{was_of(p_['name'])}<strong>{e(p_['price'])}</strong></td><td>{e(p_['what'])}</td></tr>"
                         for p_ in CFG["prices"] if p_["name"] not in ("Standard listing", "Featured job", "Pinned job"))
    low_day = min((per_day(pl) for pl in plus["plans"]), key=lambda x: int(x.split()[0])) if plus["plans"] else ""
    # Plan cards first (plan, price, button: how every pricing page that sells is read), the line-by-line tables under them.
    # "Recommended" is our advice, said as such; "most popular" would be a claim about sales that have not happened.
    def pcard(name, price, per, sub, btn, fine="", chip="", was="", best=False, ticks=None):
        return (f'<div class="pcard{" best" if best else ""}">' + ('<span class="pband">Recommended</span>' if best else "")
                + f'<p class="pk-n">{e(name)}</p><p class="pk-p"><b>{e(price)}</b><span>{e(per)}</span></p>'
                + '<p class="pk-s">' + (f"<s>{e(was)}</s>" if was else "") + (f'<span class="pchip">{e(chip)}</span>' if chip else "") + "</p>"
                + f'<p class="pk-d">{e(sub)}</p>{btn}' + (f'<p class="pk-f">{e(fine)}</p>' if fine else "") + (tick(ticks) if ticks else "") + "</div>")
    def plus_btn(best):
        kind = "primary" if best else "ghost"
        return (f'<a class="btn {kind}" href="{P}/plus/#pay">Get Plus</a>' if plus.get("live") else f'<a class="btn {kind}" href="{P}/plus/">See what Plus does</a>')      # not on sale yet: a dead grey button teaches nothing, the Plus page does
    seek_cards = ('<div class="pgrid">'
                  + pcard("Free", "$0", "forever", "Everything needed to find a job and apply.", f'<a class="btn ghost" href="{P}/for-you/">Start free</a>', "No account, no card.",
                          ticks=["Every job and the link to apply", "Search, 23 fields of work, salary data", "Resume builder: 5 templates, PDF and Word", "Resume examples and letter templates", "Application tracker on this device"])
                  + '<div class="pside"><div class="pcards c3">'
                  + "".join(pcard(f"Plus · {pl['name']}", pl["price"], f"for {pl['name']}", " · ".join(x for x in (pl.get("per", ""), per_day(pl)) if x), plus_btn(pl.get("best")),
                                  "One payment. It ends by itself; nothing renews.", chip=pl.get("note", ""), was=pl.get("was", ""), best=bool(pl.get("best"))) for pl in plus["plans"])
                  + '</div><div class="pincl"><p class="pk-n">Every Plus plan includes everything in Free, and</p>'
                  + tick(["AI resume writer and editor", "Resume reworded for each posting", "AI resume review: score and rewrites", "AI cover, thank-you and resignation letters", "Interview practice for the posting",
                          "An email the day a job fits", "Pay check with a negotiating script", "Your jobs and resumes on every device"]) + "</div></div></div>") if plus["plans"] else ""
    def emp_btn(best):
        kind = "primary" if best else "ghost"
        return f'<a class="btn {kind}" href="{e(app_url)}">Post a job</a>' if app_url else f'<a class="btn {kind}" href="{P}/post-a-job/">How posting works</a>'
    emp_cards = ('<div class="pcards c3">'
                 + pcard("Standard", "Free", "for 30 days", "Your job in the list and in search, like every other job here.", emp_btn(False),
                         ticks=["Its own page, readable by Google’s job box", "A link straight to your application page", "Checked before it goes live", "Close or renew it yourself"])
                 + pcard("Featured", price_of("Featured job"), "for 14 days", "A highlighted row that stays above the regular listings of its category.", emp_btn(True), "One payment per job.",
                         was=PRICE.get("Featured job", {}).get("was", ""), best=True,
                         ticks=["Everything in Standard", "Highlighted row with a “Featured” mark", "Above regular listings for 14 days", "Views and clicks to apply in your account"])
                 + pcard("Pinned", price_of("Pinned job"), "for 7 days", "The first row on the home page and in its category.", emp_btn(False), "One payment per job.",
                         was=PRICE.get("Pinned job", {}).get("was", ""),
                         ticks=["Everything in Featured", "First row of the home page for 7 days", "First row of its category", "Included in the feeds other sites read"]) + "</div>")
    # What pricing pages of other job sites have in common, taken into this one (PRICING_RESEARCH.md, 44 sites): three choices, a marked
    # middle one, short promises above the cards, "which plan fits", a comparison table and questions under them. Not taken: cheap trials
    # that renew at a higher price, countdowns, extras ticked in advance.
    # The figures below were read from the sites' own public price pages on MARKET["date"]. Re-read those pages before changing one.
    MARKET = {"date": "13 Nov 2026", "seeker_month": 29,
              "seeker_sites": ["Enhancv", "Himalayas", "Kickresume", "FlexJobs", "Zety", "Teal", "Rezi", "Resume.io", "Simplify", "Huntr", "Jobscan"],
              "post": 299, "post_sites": ["Jobicy", "Working Nomads", "Remote3", "We Work Remotely", "Remote OK", "Remotive", "Cryptocurrency Jobs", "Dice"]}
    trust = lambda items: '<ul class="ptrust">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
    def pvs(them_big, them_txt, us_big, us_txt, src):
        return (f'<div class="pvs"><div><p class="pvs-l">Elsewhere</p><p class="pvs-n">{e(them_big)}</p><p>{e(them_txt)}</p></div>'
                f'<div class="us"><p class="pvs-l">Here</p><p class="pvs-n">{e(us_big)}</p><p>{e(us_txt)}</p></div><p class="pvs-s">{e(src)}</p></div>')
    fit = lambda rows: '<div class="pfit">' + "".join(f"<div><b>{e(a)}</b>{e(b)}</div>" for a, b in rows) + "</div>"
    seek_trust = trust(["One payment, nothing renews", "No card kept on file", "Paid in crypto", "The free part stays free"])
    seek_vs = pvs(f"${MARKET['seeker_month']} a month", f"The median price of {len(MARKET['seeker_sites'])} job-search services that sell by the month. Almost all of them renew by themselves.",
                  f"{plus['plans'][0]['price']} for a month", "One payment that ends by itself. Longer plans cost less per month.",
                  f"Prices on the public pages of {', '.join(MARKET['seeker_sites'])}, read on {MARKET['date']}.") if plus["plans"] else ""
    seek_fit = fit([("1 month", "You are already interviewing and want the letters and the interview practice for these weeks."),
                    ("3 months", "You are starting a search and do not know how long it will take. This is the one we recommend."),
                    ("12 months", "You change jobs or take contracts through the year, or want the lowest price per month.")])
    emp_trust = trust(["A standard listing is free", "No subscription", "On within the hour after payment", "Paid in crypto"])
    emp_vs = pvs(f"${MARKET['post']}", f"The median price of one 30-day job post on {len(MARKET['post_sites'])} job boards that print a price.",
                 "Free", f"For a standard 30-day listing. {price_of('Featured job')} puts it above the regular ones for 14 days.",
                 f"Prices on the public pages of {', '.join(MARKET['post_sites'])}, read on {MARKET['date']}.")
    emp_fit = fit([("Standard", "One role and no hurry. It is in the list and in search like every other job."),
                   ("Featured", "A role that must be seen this fortnight. This is the one we recommend."),
                   ("Pinned", "A launch or an urgent hire: the first row of the home page for a week.")])
    page("pricing/", f"Pricing: free for job seekers, Plus from {plus['plans'][0]['price'] if plus['plans'] else ''}, featured jobs from {price_of('Featured job')} | {SITE}",
         f"What is free and what is paid, side by side. Job seekers: every job and the resume builder are free, Plus adds an AI writer from {low_day}. Employers: a standard listing is free, a featured job is {price_of('Featured job')}.",
         crumbs(("Pricing", "")) + '<h1>Pricing: what is free and <span class="hl">what you pay for</span></h1>'
         '<p class="lead">Two sets of plans, because a person looking for work and a company hiring buy different things. Pick yours.</p>'
         '<p class="tabs pswitch" id="pswitch" hidden><button class="tab" type="button" data-v="s" aria-pressed="true">I’m looking for work</button><button class="tab" type="button" data-v="e" aria-pressed="false">I’m hiring</button></p>'
         + LAUNCH
         + f'<section class="sec" id="for-seekers"><div class="sec-head"><h2>Looking for work</h2><a href="{P}/plus/">What Plus does</a></div>{soon}{seek_trust}{seek_cards}{seek_vs}<h3 class="cmp-h">Which plan fits</h3>{seek_fit}<h3 class="cmp-h">Free and Plus, line by line</h3>{seek_pt}'
           f'<p><a class="btn primary" href="{P}/for-you/">Start free with five questions</a> <a class="btn ghost" style="margin-top:0" href="{P}/plus/">See Plus</a></p></section>'
         + f'<section class="sec" id="for-employers"><div class="sec-head"><h2>Hiring</h2><a href="{P}/post-a-job/">See a featured job</a></div>'
           + ("" if app_url else '<div class="banner">Self-serve posting is being finished and is not open yet. Nothing can be bought today.</div>') + emp_trust + emp_cards + emp_vs + '<h3 class="cmp-h">Which plan fits</h3>' + emp_fit + '<h3 class="cmp-h">Standard, Featured and Pinned, line by line</h3>' + emp_pt
           + f'<h3>More ways to be seen</h3><div class="tablewrap"><table><tr><th>Placement</th><th>Price</th><th>What you get</th></tr>{extra_rows}</table></div>'
           f'<p><a class="btn primary" href="{P}/post-a-job/">Post a job</a></p></section>'
         + section("Questions about prices and payment", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in price_qa) + "</dl>"), head=price_ld)
    # "Jobs near me" and "part time jobs near me": among the most searched job phrases in every country.
    # The country comes from the device's time zone (nothing is sent anywhere); the nearest city only if the visitor allows location, and it is worked out in the browser.
    CITY_LL = {"new-york": (40.71, -74.01), "san-francisco": (37.77, -122.42), "seattle": (47.61, -122.33), "austin": (30.27, -97.74), "chicago": (41.88, -87.63), "boston": (42.36, -71.06),
               "washington-dc": (38.91, -77.04), "denver": (39.74, -104.99), "los-angeles": (34.05, -118.24), "dallas": (32.78, -96.80), "atlanta": (33.75, -84.39), "san-diego": (32.72, -117.16),
               "pittsburgh": (40.44, -80.00), "portland": (45.52, -122.68), "miami": (25.76, -80.19), "phoenix": (33.45, -112.07), "raleigh-durham": (35.78, -78.64), "houston": (29.76, -95.37),
               "toronto": (43.65, -79.38), "vancouver": (49.28, -123.12), "berlin": (52.52, 13.40), "munich": (48.14, 11.58), "bangalore": (12.97, 77.59), "sydney": (-33.87, 151.21),
               "united-kingdom": (51.51, -0.13), "singapore": (1.35, 103.82), "hong-kong": (22.32, 114.17), "uae": (25.20, 55.27), "ireland": (53.35, -6.26), "france": (48.86, 2.35),
               "netherlands": (52.37, 4.90), "japan": (35.68, 139.69), "israel": (32.08, 34.78), "poland": (52.23, 21.01), "spain": (40.42, -3.70), "portugal": (38.72, -9.14),
               "sweden": (59.33, 18.07), "switzerland": (47.38, 8.54), "brazil": (-23.55, -46.63), "mexico": (19.43, -99.13), "south-korea": (37.57, 126.98), "taiwan": (25.03, 121.57)}
    def near_page(path, et, h1, title, desc, lead):
        nj = lambda js: [j for j in js if not et or j.get("etype") == et]
        rows_ = sorted(((name.removeprefix("the "), slug, nj(js)) for name, slug, js in places), key=lambda x: -len(x[2]))
        rows_ = [r for r in rows_ if r[2]]
        ntile = lambda name, slug, js: (f'<li><a class="tile" href="{P}/' + (f"jobs/?loc={slug}&amp;etype={quote(et)}" if et else f"locations/{slug}/") + f'" data-place="{slug}" data-name="{e(name)}"'
                                        + (f' data-ll="{CITY_LL[slug][0]},{CITY_LL[slug][1]}"' if slug in CITY_LL else "") + f'><span class="n">{pfl(slug)}{e(name)}</span><span class="c">{len(js):,}</span></a></li>')
        is_city = lambda slug: not isinstance(rule_of.get(slug), str)
        cities = "".join(ntile(*r) for r in rows_ if is_city(r[1]))
        lands = "".join(ntile(*r) for r in rows_ if not is_city(r[1]))
        allj = nj(active)
        word = (et.lower() + " ") if et else ""
        qa = [(f"How does this page know which {word}jobs are near me?", "It reads the time zone your device is set to and takes the country from it. Nothing is sent anywhere and nothing is stored on a server. "
               "For the nearest city, press “Use my location”: your browser asks first, and the distance is worked out on your device."),
              ("What if my city is not in the list?", f"Cities get their own list when enough employers hire there. Until then your country’s list holds those jobs, and the search finds a city by name. There are {len(rows_)} places today."),
              (f"Are there remote {word}jobs I can do from here?", "Yes. A remote job names the countries it can be done from, and those jobs are in your country’s list. Jobs open to any country are under “work from anywhere”."),
              ("How fresh are the jobs?", "Every job is read from the employer’s own careers page every hour. When the employer closes it, it leaves the list within the hour.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        static_list = (section(f"Newest {word}jobs, everywhere", f'<ul class="jobs">{"".join(card(j) for j in diverse(order(allj), 30, 2))}</ul>',
                               (("part-time/", "All part-time jobs") if et == "Part-time" else ("jobs/?etype=Full-time", "All full-time jobs") if et == "Full-time" else ("new/", "All new jobs"))) if allj else "")
        page(path, title, desc,
             crumbs((h1, "")) + f'<h1>{e(h1.rsplit(" ", 2)[0])} <span class="hl">near me</span></h1><p class="lead">{lead}</p>'
             f'<p class="near" id="near" hidden></p>'
             f'<section class="sec nearme" id="nearme" data-etype="{e(et)}" hidden><div class="sec-head"><h2 id="nearme-h"></h2><span id="nearme-more"></span></div><ul class="jobs" id="nearme-list"></ul>'
             '<p><button class="btn ghost sm" type="button" id="nearme-geo" hidden style="margin-top:0">Use my location for the nearest city</button> '
             '<span class="note" id="nearme-note">The country is taken from your device’s time zone. Nothing is sent anywhere.</span></p></section>'
             + (section("Pick a city", f'<ul class="tiles">{cities}</ul>') if cities else "")
             + section("Pick a country or a part of the world", f'<ul class="tiles">{lands}</ul>', ("locations/", "All places"))
             + section("Or work from home", '<div class="feats">'
                       f'<a class="feat" href="{P}/remote/"><h3>Remote jobs</h3><p>{sum(1 for j in active if j["remote"]):,} jobs done from home. Each one says which countries it is open to.</p></a>'
                       f'<a class="feat" href="{P}/work-from-anywhere/"><h3>Work from anywhere</h3><p>{sum(1 for j in active if j.get("anywhere")):,} remote jobs open to any country.</p></a>'
                       f'<a class="feat" href="{P}/part-time/"><h3>Part-time jobs</h3><p>{sum(1 for j in active if j.get("etype") == "Part-time"):,} jobs for fewer hours than a full week.</p></a>'
                       f'<a class="feat" href="{P}/map/"><h3>Jobs on a map</h3><p>Every city with open jobs as a dot on a world map. Search a skill and see where it is hiring.</p></a></div>')
             + static_list
             + section(f"Questions about {word}jobs near you", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa) + "</dl>"), head=ld_)
    near_page("jobs-near-me/", "", "Jobs near me", f"Jobs Near Me: {len(active):,} open jobs in {len(places)} cities and countries | {SITE}",
              f"Jobs near you, hiring now: {len(active):,} open jobs in {len(places)} cities and countries, read from employers’ own pages every hour. Your country is found from the time zone; pick a city or allow location for the nearest one.",
              f"{len(active):,} open jobs in {len(places)} cities and countries, each read from the employer’s own page within the last hour. Your country is found by itself; the nearest city if you allow it.")
    ft_n = sum(1 for j in active if j.get("etype") == "Full-time")
    if ft_n >= 20:
        near_page("full-time-jobs-near-me/", "Full-time", "Full-time jobs near me", f"Full-Time Jobs Near Me: {ft_n:,} open today | {SITE}",
                  f"Full-time jobs near you, hiring now: {ft_n:,} open full-week jobs by city and country, read from employers’ own pages every hour.",
                  f"{ft_n:,} open jobs that the employer marks as full-time, each read from the employer’s own page within the last hour. Your country is found by itself; the nearest city if you allow it.")
    pt_n = sum(1 for j in active if j.get("etype") == "Part-time")
    if pt_n >= 20:
        near_page("part-time-jobs-near-me/", "Part-time", "Part-time jobs near me", f"Part-Time Jobs Near Me: {pt_n:,} open today | {SITE}",
                  f"Part-time jobs near you, hiring now: {pt_n:,} open jobs for fewer hours than a full week, by city and country, read from employers’ own pages every hour.",
                  f"{pt_n:,} open part-time jobs, each read from the employer’s own page within the last hour. Your country is found by itself; the nearest city if you allow it.")

    # The jobs map (the owner asked for one like map.rezi.ai): a dot per city, sized by its open jobs. The map draws in the browser from
    # data/map.json; the city list below the map is plain HTML, so the page reads and ranks without the map. See assets/map.js, geo_cities.py.
    map_rows = order(active)                      # the same order as data/index.json, so ix[k] belongs to row k there
    map_keys, map_ix, map_n = {}, [], Counter()
    for j in map_rows:
        ck = geo_cities.city_of(j["location"] or "")
        if ck and ck not in map_keys: map_keys[ck] = len(map_keys)
        map_ix.append(map_keys[ck] if ck else -1)
        if ck: map_n[ck] += 1
    live_place = {slug for _, slug, _ in places}
    map_url = lambda k: f"locations/{k}/" if k in live_place else f"jobs/?q={quote(geo_cities.CITIES[k][0])}"
    map_c = [[k, geo_cities.CITIES[k][0], geo_cities.CITIES[k][1], geo_cities.CITIES[k][2], geo_cities.CITIES[k][3], map_url(k)] for k in map_keys]
    write("data/map.json", json.dumps({"c": map_c, "n": [map_n[k] for k in map_keys], "ix": map_ix}, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    map_total = sum(map_n.values())
    map_tiles = "".join(f'<li><a class="tile" href="{P}/{map_url(k)}" data-city="{map_keys[k]}"><span class="n">{fl(geo_cities.CITIES[k][1])}{e(geo_cities.CITIES[k][0])}</span><span class="c">{n_:,}</span></a></li>'
                        for k, n_ in map_n.most_common(60))
    map_qa = [("Where do the jobs on the map come from?", f"From the careers pages of {len(OPEN_C) if 'OPEN_C' in dir() else len({j['company'] for j in active}):,} employers, read every hour. Each dot is a city named in the postings; its size is the number of open jobs there."),
              ("Why are some jobs not on the map?", f"{len(active) - map_total:,} of the {len(active):,} open jobs name no city: most are remote jobs that only name a country or a region. They are all in the search and on the remote jobs page."),
              ("Can I search the map?", "Yes. Type a job, a skill or a company, for example “python” or “nurse”: the dots are counted again for that word, in your browser, and the map moves to where those jobs are."),
              ("Do I apply on this site?", "No. Every job links to the employer’s own posting, and you apply there. This site never stands between you and the employer.")]
    map_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in map_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>"
        '<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">')
    page("map/", f"Jobs Map: {map_total:,} Open Jobs in {len(map_keys)} Cities | {SITE}",
         f"A world map of {map_total:,} open jobs in {len(map_keys)} cities, read from employers’ own careers pages every hour. Search a job or a skill and see where it is hiring; no account needed.",
         crumbs(("Jobs map", "")) + '<h1>Jobs on a map: <span class="hl">see where they are hiring</span></h1>'
         f'<p class="lead">{map_total:,} open jobs in {len(map_keys)} cities, each read from the employer’s own careers page within the last hour. '
         'Type a job or a skill to count the dots again; click a dot for the newest jobs there.</p>'
         '<form class="mapform" id="mapform" role="search"><input type="search" id="mapq" name="q" placeholder="A job, a skill or a company, for example python" aria-label="Search the map">'
         '<button class="btn primary" type="submit">Show on map</button></form>'
         '<div class="mapwrap"><div class="jobmap" id="jobmap" role="region" aria-label="Map of open jobs by city"></div>'
         '<aside class="mappanel" id="mappanel" aria-live="polite" hidden></aside></div><p class="note" id="mapnote">The map needs JavaScript. Every city is listed below.</p>'
         + section("Cities with the most open jobs", f'<ul class="tiles">{map_tiles}</ul>', ("locations/", "Jobs by country"))
         + section("Questions about the jobs map", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in map_qa) + "</dl>")
         + f'<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js" defer></script><script src="{P}/map.js?v={V}" defer></script>', head=map_ld)

    # Resignation letters, one page per situation. In the Rezi study these pages bring that site about a fifth of its search visits.
    RL = resignation_pages.LETTERS
    rl_year = TODAY[:4]
    rl_tile = lambda x: f'<li><a class="tile" href="{P}/resignation-letters/{x["slug"]}/"><span class="n">{e(x["name"])}</span><span class="c">{e(x["short"])}</span></a></li>'
    for x in RL:
        low_ = x["name"][0].lower() + x["name"][1:]
        qa_ = x["qa"]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        others_ = [y for y in RL if y["slug"] != x["slug"]]
        page(f"resignation-letters/{x['slug']}/", f"{tcase(x['name'])}: Template and Example ({rl_year}) | {SITE}",
             f"A {low_} you can copy: {x['when'][0].lower() + x['when'][1:]}",
             crumbs(("Resignation letters", "resignation-letters/"), (x["name"], "")) + f'<h1>{e(x["name"])}: <span class="hl">template and example</span></h1>'
             f'<p class="lead">{e(x["when"])} Copy the letter below, replace the parts in [brackets], and send it to your manager.</p>'
             f'<div class="rl-paper"><pre id="letter">{e(x["letter"])}</pre>'
             '<p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the letter</button> '
             f'<a class="btn ghost sm" href="{P}/tools/resignation-letter/" style="margin-top:0">Fill it in with the free builder</a></p></div>'
             + section(f"What to put in a {low_}", '<ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in x["include"]) + "</ul>"
                       '<p class="note">Notice periods depend on your contract and on the law where you work. This page is general guidance, not legal advice.</p>')
             + section(f"Questions about a {low_}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
             + section("Other resignation letters", f'<ul class="tiles">{"".join(rl_tile(y) for y in others_[:9])}</ul>', ("resignation-letters/", f"All {len(RL)} letters"))
             + section("After you resign", '<div class="feats">'
                       f'<a class="feat" href="{P}/tools/last-working-day/"><h3>Last working day calculator</h3><p>Count the notice period from the day you hand in the letter.</p></a>'
                       f'<a class="feat" href="{P}/resume/"><h3>Update your resume</h3><p>Add this job while the results are fresh. Free, no account.</p></a>'
                       f'<a class="feat" href="{P}/jobs/"><h3>Find the next job</h3><p>{len(active):,} open jobs, read from employers’ own pages every hour.</p></a></div>'), head=ld_)
    rl_qa = [("How do I write a resignation letter?", "Say that you are resigning, from which position and company, and give your last working day as a date. Add one sentence of thanks and what you will hand over. Keep it short and leave complaints out."),
             ("How much notice should I give?", "What your contract asks for. In the United States two weeks is the custom; elsewhere a month or more is common. Check the contract before you write the date."),
             ("Should I resign in person or in writing?", "Both: tell your manager in a short conversation, then send the letter or email the same day so the date is on record.")]
    rl_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in rl_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("resignation-letters/", f"Resignation Letter Templates: {len(RL)} Examples for Every Situation ({rl_year}) | {SITE}",
         f"{len(RL)} resignation letter templates you can copy: two weeks notice, effective immediately, by email, for a new job, relocation, health or family reasons, retirement and more.",
         crumbs(("Resignation letters", "")) + f'<h1>Resignation letter templates: <span class="hl">{len(RL)} examples</span></h1>'
         '<p class="lead">Pick the letter that fits your case. Each one is complete: copy it, replace the parts in [brackets], and send it. '
         f'Or build your own in the <a href="{P}/tools/resignation-letter/">free resignation letter builder</a>.</p>'
         + section("Choose your situation", f'<ul class="tiles">{"".join(rl_tile(y) for y in RL)}</ul>')
         + section("Questions about resignation letters", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in rl_qa) + "</dl>"), head=rl_ld)

    # Stronger resume words, one page per overused verb ("another word for managed on a resume"). In the Rezi study 8 such pages bring
    # that site 8% of its search visits. Each page groups the words by what was actually done and shows a resume line for each group.
    RW = resume_words.WORDS
    rw_tile = lambda x: f'<li><a class="tile" href="{P}/resume-words/{x["slug"]}/"><span class="n">Instead of “{e(x["word"])}”</span><span class="c">{sum(len(g[1]) for g in x["groups"])} words</span></a></li>'
    for x in RW:
        n_ = sum(len(g[1]) for g in x["groups"])
        qa_ = x["qa"]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        groups_ = "".join(f'<div class="rw-g"><h3>{e(what)}</h3><p class="rw-w">' + "".join(f"<span>{e(w)}</span>" for w in words) + "</p>"
                          f'<p class="rw-ex"><span>Example</span>{e(line)}</p></div>' for what, words, line in x["groups"])
        page(f"resume-words/{x['slug']}/", f"Another Word for “{tcase(x['word'])}” on a Resume: {n_} Synonyms with Examples | {SITE}",
             f"{n_} stronger words to use instead of “{x['word']}” on a resume, grouped by what you actually did, each group with an example line that shows a result.",
             crumbs(("Resume words", "resume-words/"), (f"Instead of “{x['word']}”", "")) + f'<h1>Another word for “{e(x["word"])}” on a resume: <span class="hl">{n_} synonyms</span></h1>'
             f'<p class="lead">{e(x["why"])} The words below are grouped by what you did; each group has an example line with a number, the way a recruiter wants to read it.</p>'
             + f'<section class="sec"><div class="sec-head"><h2>Words to use instead of “{e(x["word"])}”, by what you did</h2></div><div class="rw-grid">{groups_}</div></section>'
             + section("Turn your own line into a strong one", '<p>Start with the verb that names the action, add what you did it to, and end with a number: how many, how much, how fast. '
                       f'The <a href="{P}/tools/resume-bullet-builder/">resume bullet builder</a> puts the three parts together for you, and the <a href="{P}/resume/">resume builder</a> lays out the whole page. Both are free and need no account.</p>')
             + section(f"Questions about replacing “{x['word']}”", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
             + section("Other overused resume words", f'<ul class="tiles">{"".join(rw_tile(y) for y in RW if y["slug"] != x["slug"])}</ul>', ("resume-words/", f"All {len(RW)}")), head=ld_)
    page("resume-words/", f"Resume Synonyms: Stronger Words for {len(RW)} Overused Verbs | {SITE}",
         f"Stronger words for the {len(RW)} most overused resume verbs, from “managed” and “led” to “responsible for” and “helped”, grouped by what you did, with example lines.",
         crumbs(("Resume words", "")) + f'<h1>Resume synonyms: <span class="hl">stronger words for {len(RW)} tired verbs</span></h1>'
         '<p class="lead">Recruiters read “managed”, “responsible for” and “helped” in almost every resume, and those words do not say what changed because of you. '
         'Pick the word you keep repeating: each page lists better ones by what you actually did, with an example line that has a number.</p>'
         + section("Pick the word you overuse", f'<ul class="tiles">{"".join(rw_tile(y) for y in RW)}</ul>')
         + section("Write the whole line", f'<p>A strong resume line has three parts: an action verb, what you did it to, and a result with a number. '
                   f'The free <a href="{P}/tools/resume-bullet-builder/">resume bullet builder</a> helps you write one, and <a href="{P}/resume/examples/">resume examples for {len(rex_data)} kinds of work</a> show whole resumes written this way.</p>'))

    # Mentors: what it will be and an application for real people. No mentor is listed until a real one is checked; nobody is invented.
    tg = CFG.get("contact_telegram", "")
    men_qa = [("Are the mentors real people?", "Yes, or there are none. A mentor is listed only under a real name, with a public profile we have checked and the companies they worked at. No mentor is invented, and software is never shown as a person."),
              ("Can I book a session today?", "No. The first mentors are being selected, so nobody is listed yet and nothing can be booked or paid for."),
              ("What will a session cost?", "Each mentor sets a price, shown before you book. Nothing is charged for looking, and there is no subscription for mentoring."),
              ("Is there an AI mentor?", "Plus has an AI writer for resumes and letters. It is labelled as AI everywhere and is not called a mentor."),
              ("What can I use until mentors are listed?", "The resume builder, a resume example for your kind of work, the free tools and the guides. All of them are free and need no account.")]
    men_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in men_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    men_apply = ("Mentor application\nName:\nCurrent role and company:\nYears in this kind of work:\nLinkedIn or GitHub profile:\nWhat I can help with (resume, interviews, changing field, pay talks):\n"
                 "Languages:\nTime zone and hours I can offer a week:")
    page("mentors/", f"Career Mentors for Tech Job Seekers: how it will work | {SITE}",
         "One-to-one sessions with people who do the job you want: a resume read, a mock interview, a plan for changing field. The first mentors are being selected; applications are open.",
         crumbs(("Mentors", "")) + '<h1>A mentor who has done <span class="hl">the job you want</span></h1>'
         '<p class="lead">One hour with a person who hires for your kind of role, or was hired for it recently, saves weeks of guessing. That is what this page will offer.</p>'
         '<div class="banner">Not open yet. The first mentors are being selected, so nobody is listed and nothing can be booked or paid for today. Mentors can apply below.</div>'
         + section("What a session is", '<div class="feats">'
                   '<div class="feat"><h3>Resume read</h3><p>30 minutes. The mentor reads your resume the way a hiring manager does and says what to cut, what to move up and which numbers are missing.</p></div>'
                   '<div class="feat"><h3>Mock interview</h3><p>45 minutes. Questions asked for your role at their kind of company, then plain feedback on each answer.</p></div>'
                   '<div class="feat"><h3>Changing field</h3><p>45 minutes. What from your past work counts, what to learn first, which job titles to apply for in the first three months.</p></div>'
                   '<div class="feat"><h3>Offer and pay</h3><p>30 minutes. How to read an offer, what the advertised ranges for the role are, how to ask for more without losing the offer.</p></div></div>')
         + section("How it will work", '<ol class="steps"><li><b>Pick a mentor</b> by role, level and the kind of company they worked at.</li>'
                   '<li><b>Pick a time</b> from the hours the mentor has opened.</li><li><b>Talk by video.</b> You send your resume or the job posting beforehand.</li>'
                   '<li><b>Get notes in writing</b> after the session, so nothing has to be remembered.</li></ol>')
         + section("Who can be a mentor", '<ul><li>At least three years in the role you mentor for, or hiring for it.</li><li>A public profile (LinkedIn or GitHub) that shows it. We check every one before listing.</li>'
                   '<li>A real name and a real photo. No stage names, no stock photos.</li><li>You set your own price and hours.</li></ul>'
                   + (f'<p class="flabel">Send this, filled in, on Telegram</p><pre id="men-apply">{e(men_apply)}</pre>'
                      f'<p><button class="btn ghost sm" type="button" data-clip="men-apply" data-raw="1" style="margin-top:0">Copy the form</button> '
                      f'<a class="btn primary sm" href="https://t.me/{e(tg)}" rel="nofollow noopener">Apply on Telegram</a></p>' if tg else ""), sid="apply")
         + section("Until mentors are listed", '<div class="feats">'
                   f'<a class="feat" href="{P}/resume/examples/"><h3>Resume examples</h3><p>A written example for each kind of work, with the skills today’s postings ask for.</p></a>'
                   f'<a class="feat" href="{P}/resume/"><h3>Resume builder</h3><p>One page, plain layout, Word and PDF. Free, nothing to sign up for.</p></a>'
                   f'<a class="feat" href="{P}/tools/"><h3>Free tools</h3><p>Match a resume to a posting, pay calculators, letters, an application tracker.</p></a>'
                   f'<a class="feat" href="{P}/guides/"><h3>Guides</h3><p>Short articles with figures recounted from today’s postings.</p></a></div>')
         + section("Questions about mentors", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in men_qa) + "</dl>"), head=men_ld)
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
         + section("Questions about the hiring badge", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in hb_faq) + "</dl>"),
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
    rows_ = [[slug_ref(j), j["title"], ci[j["company"]], j["location"], int(j["remote"]) | 2 * int(j["featured"]) | 4 * int(bool(j.get("crypto"))) | 8 * int(bool(j.get("anywhere"))) | 16 * int(j["pool"]) | 32 * int(bool(j.get("hybrid"))),
              cat_list.index(j["cat"]), lvl_list.index(j["level"]) if j["level"] in lvl_list else 0, [ti[t] for t in j["tags"] if t in ti], j["salary"],
              int((j["posted"] or j["first_seen"]).replace("-", "")[:8] or 0), int(j["usd"][1]) if j["usd"] else 0, [pi[p_] for p_ in j["places"]],
              [perk_list.index(x) for x in j.get("perks", []) if x in perk_list], et_list.index(j.get("etype", "")) if j.get("etype", "") in et_list else 0,
              j["t"] // 60 if j["t"] and NOW - j["t"] < WEEK else 0] for j in order(active)]      # last: exact posting time, minutes since 1970 (0: only the day is known, or older than a week)
    idx = {"c": comp_list, "t": tag_list, "p": place_list, "f": [PLACE_CODE.get(p_, "") for p_ in place_list], "k": cat_list, "l": lvl_list, "x": perk_list, "e": et_list, "g": [int(slugify(c) in LOGOS) for c in comp_list]}
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
    for f in ("app.js", "embed.js", "site.js", "widget.js", "widgets.js", "resume.js", "account.js", "map.js"):
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
