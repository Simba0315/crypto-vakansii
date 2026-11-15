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
import brand                            # the brand: three directions, the logo files, the colours (brand.py, /brand/)
import roles_info
import resume_examples
import skills_info                      # what each skill is, in plain words, and its group
import geo_cities                       # where the cities in postings are, for the jobs map
import resignation_pages                # a resignation letter per situation (/resignation-letters/)
import resume_words                     # stronger words for an overused resume verb (/resume-words/)
import compare_sites                    # sourced facts for "Jobs Every Hour vs <job site>" (/vs/)
import builders_check                   # what a free user of each resume builder can download (/free-resume-builders/)
import quiz_pages                        # skill self-tests (/skill-tests/)
import glossary_terms                   # the glossary, one page per term (/glossary/)
QUIZ_OF = {v["skill"]: (k, len(v["qs"])) for k, v in quiz_pages.QUIZZES.items()}     # skill -> (its test's slug, number of questions)

ROOT = Path(__file__).parent
OUT = ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
CFG["api_url"] = os.environ.get("HRN_API_URL", CFG.get("api_url", "")).rstrip("/")   # the accounts and checkout API; empty until it is deployed
# The opt-in resume database (server/README.md "The resume database"): its privacy and promise text appear once it is on for the site,
# with the API and the resume builder's "Let employers find my resume" (config.json "talent_db": true, or HRN_TALENT_DB=1 for a test build)
CFG["talent_db"] = bool(CFG["api_url"]) and (os.environ.get("HRN_TALENT_DB") == "1" or bool(CFG.get("talent_db")))
SITE, BASE, P = CFG["site_name"], CFG["base_url"].rstrip("/"), CFG.get("base_path", "").rstrip("/")
LVL_NAME = {"Intern": "Intern", "Junior": "Junior", "Senior": "Senior", "Lead": "Lead and above", "": "No level in the title"}   # the one vocabulary for seniority (AUDIT 21); "Lead" covers lead, staff, principal, head of, director
FULL = BASE + P
TODAY = datetime.date.today().isoformat()
e = html.escape
MAIL = {k: v for k, v in (CFG.get("emails") or {}).items() if v}       # one address per department: jobs, partners, press, privacy, abuse, security


def mail_a(kind, subject=""):
    """A department's address as a mail link; support@ when that department has none. Cloudflare hides addresses in the HTML
    from scrapers (Email Address Obfuscation), so they are written plainly here."""
    addr = MAIL.get(kind) or CFG.get("contact_email", "")
    return f'<a href="mailto:{e(addr)}{e("?subject=" + quote(subject)) if subject else ""}">{e(addr)}</a>' if addr else ""
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
    ("BG", "Bulgaria", r"\bbulgaria\b", r"\bsofia\b"), ("HU", "Hungary", r"\bhungary\b", r"budapest"), ("RS", "Serbia", r"\bserbia\b", r"belgrade|novi sad"),
    ("RU", "Russia", r"\brussia\b|russian federation", r"\bmoscow\b|saint petersburg|st\.? petersburg|novosibirsk|yekaterinburg|\bkazan\b|nizhny novgorod|innopolis"),
    ("BY", "Belarus", r"\bbelarus\b", r"\bminsk\b"), ("KZ", "Kazakhstan", r"kazakhstan", r"almaty|astana"),
    ("UZ", "Uzbekistan", r"uzbekistan", r"tashkent"), ("KG", "Kyrgyzstan", r"kyrgyzstan", r"bishkek"), ("AM", "Armenia", r"\barmenia\b", r"yerevan"),
    ("GE", "Georgia (country)", r"georgia \(country\)|sakartvelo", r"tbilisi|batumi"), ("AZ", "Azerbaijan", r"azerbaijan", r"\bbaku\b"),
    ("CY", "Cyprus", r"\bcyprus\b", r"limassol|larnaca|nicosia"), ("ME", "Montenegro", r"montenegro", r"podgorica|budva"),
    ("LV", "Latvia", r"\blatvia\b", r"\briga\b"), ("MD", "Moldova", r"moldova", r"chisinau|chi[șs]in[ăa]u"),
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
US_STATES = (r"alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|\bgeorgia\b(?! \(country\))|hawaii|idaho|illinois|\bindiana\b|\biowa\b|kansas|kentucky|louisiana|"
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


REGIONS = {"europe": ({"GB", "DE", "FR", "IE", "NL", "ES", "PT", "PL", "SE", "CH", "AT", "IT", "DK", "NO", "FI", "BE", "CZ", "RO", "UA", "EE", "LT", "GR", "BG", "HU", "RS", "LV", "CY", "ME", "MD"}, r"\beurope\b|\bemea\b|\beu\b"),
           "asia-pacific": ({"IN", "SG", "HK", "JP", "KR", "TW", "CN", "AU", "NZ", "MY", "PH", "ID", "TH", "VN"}, r"\bapac\b|\basia\b"),
           "latin-america": ({"BR", "MX", "AR", "CO", "CL"}, r"\blatam\b|latin america"),
           "africa": ({"ZA", "NG", "KE"}, r"\bafrica\b")}
# (name, slug, rule). A rule is a country code, a region key, or (pattern, country the match must agree with).
PLACES = [
    ("the United States", "united-states", "US"), ("Canada", "canada", "CA"), ("the United Kingdom", "united-kingdom", "GB"), ("Europe", "europe", "region"),
    ("Germany", "germany", "DE"), ("France", "france", "FR"), ("Switzerland", "switzerland", "CH"), ("Austria", "austria", "AT"), ("Poland", "poland", "PL"),
    ("Ireland", "ireland", "IE"), ("the Netherlands", "netherlands", "NL"), ("Spain", "spain", "ES"), ("Portugal", "portugal", "PT"), ("Sweden", "sweden", "SE"), ("Israel", "israel", "IL"),
    ("Asia-Pacific", "asia-pacific", "region"), ("India", "india", "IN"), ("Singapore", "singapore", "SG"), ("Hong Kong", "hong-kong", "HK"), ("Japan", "japan", "JP"),
    ("South Korea", "south-korea", "KR"), ("Taiwan", "taiwan", "TW"), ("Australia", "australia", "AU"), ("Malaysia", "malaysia", "MY"), ("the Philippines", "philippines", "PH"),
    ("Dubai & UAE", "uae", "AE"), ("Turkey", "turkey", "TR"), ("Latin America", "latin-america", "region"), ("Brazil", "brazil", "BR"), ("Mexico", "mexico", "MX"), ("Africa", "africa", "region"),
    # cities and states people search for by name ("tech jobs seattle", "tech jobs in austin")
    ("New York, NY", "new-york", (r"new york|\bnyc\b|brooklyn|manhattan|(?-i:, NY\b)", "US")),
    ("San Francisco Bay Area", "san-francisco", (r"san francisco|bay area|palo alto|san jose|mountain view|sunnyvale|santa clara|menlo park|redwood city|\bsf\b|oakland|san mateo", "US")),
    ("California", "california", (r"california|(?-i:, CA\b)|san francisco|bay area|palo alto|san jose|mountain view|los angeles|san diego|sunnyvale|santa clara|irvine|hawthorne", "US")),
    ("Seattle, WA", "seattle", (r"seattle|bellevue|redmond|kirkland", "US")), ("Austin, TX", "austin", (r"\baustin\b", "US")), ("Chicago, IL", "chicago", (r"\bchicago\b", "US")),
    ("Boston, MA", "boston", (r"\bboston\b|cambridge, ma", "US")), ("Washington, DC", "washington-dc", (r"washington,? ?d\.?c\.?|(?-i:\bDC\b)|arlington, va|mclean|reston", "US")),
    ("Denver, CO", "denver", (r"\bdenver\b|boulder", "US")), ("Los Angeles, CA", "los-angeles", (r"los angeles|santa monica|culver city|el segundo|hawthorne|irvine", "US")),
    ("Dallas, TX", "dallas", (r"\bdallas\b|plano|fort worth", "US")), ("Atlanta, GA", "atlanta", (r"\batlanta\b", "US")), ("San Diego, CA", "san-diego", (r"san diego", "US")),
    ("Pittsburgh, PA", "pittsburgh", (r"pittsburgh", "US")), ("Portland, OR", "portland", (r"\bportland\b", "US")), ("Miami, FL", "miami", (r"\bmiami\b", "US")),
    ("Phoenix, AZ", "phoenix", (r"\bphoenix\b|scottsdale|tempe", "US")), ("Raleigh-Durham, NC", "raleigh-durham", (r"raleigh|durham|research triangle", "US")), ("Houston, TX", "houston", (r"\bhouston\b", "US")),
    ("Texas", "texas", (r"\btexas\b|(?-i:, TX\b)|\baustin\b|\bdallas\b|\bhouston\b|san antonio", "US")), ("Florida", "florida", (r"\bflorida\b|(?-i:, FL\b)|\bmiami\b|orlando|\btampa\b", "US")),
    ("Toronto", "toronto", (r"toronto", "CA")), ("Vancouver", "vancouver", (r"vancouver", "CA")), ("Berlin", "berlin", (r"\bberlin\b", "DE")), ("Munich", "munich", (r"munich|münchen", "DE")),
    ("Bangalore", "bangalore", (r"bangalore|bengaluru", "IN")), ("Sydney", "sydney", (r"\bsydney\b", "AU")),
    # "python jobs london", "jobs in paris": the city is the query, and a country page mixes every city (SERP_WORK row 8, 15 Nov 2026)
    ("London", "london", (r"\blondon\b(?!, on\b)", "GB")), ("Manchester", "manchester", (r"\bmanchester\b(?!, nh\b)", "GB")), ("Paris", "paris", (r"\bparis\b", "FR")),
    ("Amsterdam", "amsterdam", (r"amsterdam", "NL")), ("Dublin", "dublin", (r"\bdublin\b(?!, (?:ca|oh)\b)", "IE")), ("Madrid", "madrid", (r"\bmadrid\b", "ES")),
    ("Barcelona", "barcelona", (r"barcelona", "ES")), ("Lisbon", "lisbon", (r"lisbon|lisboa", "PT")), ("Zurich", "zurich", (r"z[uü]rich", "CH")),
    ("Stockholm", "stockholm", (r"stockholm", "SE")), ("Warsaw", "warsaw", (r"warsaw|warszawa", "PL")), ("Tel Aviv", "tel-aviv", (r"tel[ -]aviv", "IL")),
    ("Tokyo", "tokyo", (r"\btokyo\b", "JP")), ("Montreal", "montreal", (r"montr[eé]al", "CA")), ("Hyderabad", "hyderabad", (r"hyderabad", "IN")),
    ("Melbourne", "melbourne", (r"\bmelbourne\b(?!, fl\b)", "AU")),
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
KEEP_CAP = {"German", "French", "Spanish", "Japanese", "Portuguese", "Chinese", "Italian", "Dutch", "Korean"} | set(getattr(roles_info, "KEEP_CAP", ()))   # "Java developer", "Arabic speaking" keep their capital


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
V = hashlib.md5(b"".join((ROOT / "assets" / f).read_bytes() for f in ("style.css", "site.js", "app.js", "account.js", "tools.js", "tools.css", "resume.js", "widget.js", "widgets.js", "map.js", "explorer.js"))).hexdigest()[:8]   # cache-busting version
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


def local_mid(s, sym):
    """The midpoint of a yearly pay range stated in pounds (sym "£") or euros ("€"), or None. Hourly, daily and monthly figures are left out."""
    if not s or sym not in s or "$" in s or re.search(r"hour|/hr|hourly|\bday\b|daily|month|/mo\b", s, re.I): return None
    vals = []
    for num, k in SAL_NUM.findall(s):
        try: v = float(re.sub(r"[.,\s](?=\d{3}(?!\d))", "", num).replace(",", "."))
        except ValueError: continue
        vals.append(v * 1000 if k else v)
    if len(vals) < 2: return None
    lo, hi = vals[0], vals[1]
    return (lo + hi) / 2 if 15000 <= lo <= hi <= 1000000 else None


def usd_hourly(s):
    """US-dollar hourly (low, high) from a salary string that states an hourly rate ("$39 - $49 an hour", "$37/hr"), or None."""
    if not s or SAL_BAD.search(s) or ("$" not in s and "USD" not in s.upper()) or not re.search(r"\bhour\b|/\s?hr\b|per hr|hourly", s, re.I):
        return None
    vals = []
    for num, k in SAL_NUM.findall(s):
        if k: return None                                  # "$50k" is not an hourly rate
        try: vals.append(float(num.replace(",", "").replace(" ", "")))
        except ValueError: continue
    if not vals: return None
    lo, hi = vals[0], vals[1] if len(vals) > 1 else vals[0]
    return (lo, hi) if 7 <= lo <= hi <= 500 else None


def money(v):
    return f"${v / 1000:,.0f}K"


def median(xs):
    xs = sorted(xs); n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
FOOT = {"cats": ""}
SIM = {"cat": {}, "comp": {}}
OPEN = Counter()   # open roles per company
FACT = {}          # one-paragraph hiring summary per company
TB = {}            # trust marks per company: [(name, the number behind it)], shown on its page and on each of its job pages
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
BR = brand.DIRECTIONS[brand.APPLIED]
MARK = brand.mark_light()                     # the favicon and every file that carries the mark: the clock-o on a white tile
GRAD = ""
_WM = re.search(r'width="(\d+)" height="(\d+)"', (ROOT / "assets" / "brand" / f"{brand.APPLIED}-logo.svg").read_text())
WM_W, WM_H = (int(_WM.group(1)), int(_WM.group(2))) if _WM else (271, 40)
# the wordmark: light file on light pages, dark file on dark ones (style.css swaps them); the link carries the name
LOGO = (f'<img class="wm-l" src="{P}/brand/{brand.APPLIED}-logo.svg?v=WMV" alt="" width="{WM_W}" height="{WM_H}">'
        f'<img class="wm-d" src="{P}/brand/{brand.APPLIED}-logo-dark.svg?v=WMV" alt="" width="{WM_W}" height="{WM_H}">')
LOGO_DARK = f'<img src="{P}/brand/{brand.APPLIED}-logo-dark.svg?v=WMV" alt="" width="{WM_W}" height="{WM_H}">'
LOGO_V = hashlib.md5((ROOT / "assets" / "brand" / f"{brand.APPLIED}-logo.svg").read_bytes()).hexdigest()[:8]
LOGO, LOGO_DARK = LOGO.replace("WMV", LOGO_V), LOGO_DARK.replace("WMV", LOGO_V)
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
    return f'<span class="ava{" " + cls if cls else ""}{" has" if img else ""}" aria-hidden="true">{e(letter)}{img}</span>'      # no hue: the logo covers the square, and a square without a logo is hidden


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


SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "per", "the", "to", "vs", "via", "with"}


def tcase(s):
    """Title case that leaves existing capitals alone and small words small: "VP of sales" -> "VP of Sales",
    "DevOps engineer" -> "DevOps Engineer". The first word is always capitalised."""
    return " ".join(w if i and w in SMALL_WORDS else w[:1].upper() + w[1:] for i, w in enumerate(s.split()))


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


TOC_FAMILIES = ("how-to-become/", "interview-questions/", "job-descriptions/", "how-to-hire/", "guides/", "insights/", "relocate/",
                "vs/", "compare/", "salaries/", "resignation-letters/", "resume-words/", "glossary/")
SEC_H2 = re.compile(r'<section class="sec"(?: id="([^"]+)")?><div class="sec-head[^"]*"><h2>(.*?)</h2>')
TOC_PAGES = {"safety/", "promise/", "methodology/", "privacy/", "terms/"}      # single long pages that read like documents
H2S = re.compile(r"""<h2 class=["']h2s["'](?: id="([^"]+)")?>(.*?)</h2>""")


def with_toc(path, body):
    """An "On this page" list beside a long article (4 or more sections): sticky on the right on wide screens, hidden on phones.
    Sections without an id get one from their heading, so the links also work as jump links in search results."""
    if not (any(path.startswith(f) and path != f for f in TOC_FAMILIES) or path in TOC_PAGES): return body
    heads = SEC_H2.findall(body)
    used, links = set(), []
    if len(heads) < 4 and path in TOC_PAGES and len(H2S.findall(body)) >= 4:      # a text page: plain headings, read at a comfortable width
        def add_h2s(m_):
            txt = m_.group(2)
            sid = m_.group(1)
            if not sid:
                base = "s-" + (slugify(html.unescape(re.sub(r"<[^>]+>", "", txt)))[:48].strip("-") or "part")
                sid, k = base, 2
                while sid in used: sid, k = f"{base}-{k}", k + 1
            used.add(sid)
            links.append(f'<li><a href="#{sid}">{re.sub(r"<[^>]+>", "", txt)}</a></li>')
            return f'<h2 class="h2s" id="{sid}">{txt}</h2>'
        body = H2S.sub(add_h2s, body)
        return (f'<div class="has-toc doc"><div class="toc-main">{body}</div><aside class="toc" aria-label="On this page"><p>On this page</p>'
                f'<ol>{"".join(links)}</ol><a class="toc-top" href="#main">Back to top</a></aside></div>')
    if len(heads) < 4: return body
    def add_id(m_):
        sid, h2 = m_.group(1), m_.group(2)
        if not sid:
            base = "s-" + (slugify(html.unescape(re.sub(r"<[^>]+>", "", h2)))[:48].strip("-") or "part")
            sid, k = base, 2
            while sid in used: sid, k = f"{base}-{k}", k + 1
        used.add(sid)
        links.append(f'<li><a href="#{sid}">{re.sub(r"<[^>]+>", "", h2)}</a></li>')
        return f'<section class="sec" id="{sid}"><div class="sec-head' + m_.group(0).split('<div class="sec-head', 1)[1]
    body = SEC_H2.sub(add_id, body)
    return (f'<div class="has-toc"><div class="toc-main">{body}</div><aside class="toc" aria-label="On this page"><p>On this page</p>'
            f'<ol>{"".join(links)}</ol><a class="toc-top" href="#main">Back to top</a></aside></div>')


ACCT_HEAD = (f'<a class="hsign" id="hsign" href="{P}/account/" data-api="{e(CFG["api_url"])}">Sign in</a>' if CFG.get("api_url") else "")


def page(path, title, desc, body, head="", sitemap=True, hero="", compact=False):
    url = f"{FULL}/{path}"
    body = with_toc(path, body)
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
<meta property="og:type" content="website">{"" if compact else f'<meta property="og:url" content="{e(url)}">'}<meta property="og:site_name" content="{e(SITE)}">
<meta property="og:image" content="{FULL}/og.jpg"><meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#121110">
<link rel="icon" type="image/svg+xml" href="{P}/favicon.svg"><link rel="apple-touch-icon" href="{P}/brand/apple-touch-icon.png"><link rel="manifest" href="{P}/manifest.json">
{"" if compact else f'<link rel="alternate" type="application/rss+xml" title="{e(SITE)} — latest jobs" href="{P}/feed.xml">'}
<link rel="preload" href="{P}/fonts/publicsans-latin.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{P}/fonts/schibsted-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{P}/style.css?v={V}"><script>try{{var t=localStorage.getItem("hrn_theme");if(t)document.documentElement.setAttribute("data-theme",t)}}catch(e){{}}</script><script src="{P}/site.js?v={V}" defer></script>{head}</head><body>
<a class="skip" href="#main">Skip to content</a><header class="site"><div class="wrap"><a class="logo" href="{P}/" aria-label="{e(SITE)}, home">{LOGO}</a><nav id="nav">
<a class="nl" href="{P}/jobs/">Find jobs</a><a class="nl" href="{P}/companies/">Companies</a><a class="nl" href="{P}/salaries/">Salaries</a><a class="nl" href="{P}/resume/">Resume</a><a class="nl" href="{P}/tools/">Career help</a><a class="nl" href="{P}/pricing/">For employers</a>{NAV_PLUS}<a class="nl only-m" href="{P}/remote/">Remote jobs</a><a class="nl only-m" href="{P}/my-jobs/">My jobs<span id="saved-n"></span></a><a class="nl only-m" href="{P}/post-a-job/">Post a job</a></nav>
<div class="hact"><button class="icon ic-s" id="palbtn" type="button" aria-label="Quick search (Ctrl K)"></button>{ACCT_HEAD}<a class="btn" href="{P}/post-a-job/">Post a job</a>
<button class="icon ic-m burger" id="menu" type="button" aria-label="Menu" aria-expanded="false"></button></div></div></header>
{hero}<main class="wrap" id="main">{body}</main>
{MINI_FOOT if compact else FULL_FOOT()}
</body></html>""", sitemap)


def FULL_FOOT():
    return f"""<footer><div class="wrap"><div class="fcols">
<div><a class="logo" href="{P}/" aria-label="{e(SITE)}, home">{LOGO_DARK}</a><p>Job boards fill up with listings that closed weeks ago. Every role here comes from the company’s own careers page and is re-checked every hour.</p></div>
<div><p class="fhd">Find jobs</p><ul><li><a href="{P}/jobs/">All jobs</a></li><li><a href="{P}/jobs-near-me/">Jobs near me</a></li><li><a href="{P}/map/">Jobs map</a></li><li><a href="{P}/remote/">Remote jobs</a></li><li><a href="{P}/new/">New jobs</a></li><li><a href="{P}/entry-level/">Entry-level</a></li><li><a href="{P}/with-salary/">Salary listed</a></li><li><a href="{P}/jobs-that-pay/">Jobs by hourly pay</a></li><li><a href="{P}/tech/">Tech jobs</a></li><li><a href="{P}/crypto/">Crypto &amp; web3 jobs</a></li><li><a href="{P}/for-you/">Jobs for you</a></li><li><a href="{P}/my-jobs/">My jobs</a></li></ul></div>
<div><p class="fhd">Browse</p><ul><li><a href="{P}/categories/">Job categories</a></li><li><a href="{P}/roles/">Roles A to Z</a></li><li><a href="{P}/skills/">Skills</a></li><li><a href="{P}/locations/">Jobs by country</a></li><li><a href="{P}/companies/">Companies</a></li><li><a href="{P}/perks/">Perks</a></li>{FOOT["cats"]}</ul></div>
<div><p class="fhd">Tools and data</p><ul><li><a href="{P}/tools/">Free tools</a></li><li><a href="{P}/resume/">Resume builder</a></li><li><a href="{P}/resume/examples/">Resume examples</a></li><li><a href="{P}/free-resume-builders/">Free resume builders compared</a></li><li><a href="{P}/how-to-become/">How to become…</a></li><li><a href="{P}/career-quiz/">Career quiz</a></li><li><a href="{P}/cover-letter-examples/">Cover letter examples</a></li><li><a href="{P}/interview-questions/">Interview questions</a></li><li><a href="{P}/resignation-letters/">Resignation letters</a></li><li><a href="{P}/resume-words/">Resume words</a></li><li><a href="{P}/mentors/">Mentors</a></li><li><a href="{P}/salaries/">Salaries</a></li><li><a href="{P}/compare/">Compare skills</a></li><li><a href="{P}/trends/">Hiring trends</a></li><li><a href="{P}/reports/">Monthly reports</a></li><li><a href="{P}/how-long-job-postings-stay-open/">How long jobs stay open</a></li><li><a href="{P}/insights/">Rankings</a></li><li><a href="{P}/open-hiring-index/">Open hiring index</a></li><li><a href="{P}/status/">Is the data fresh?</a></li></ul></div>
<div><p class="fhd">Employers and sites</p><ul><li><a href="{P}/post-a-job/">Post a job</a></li><li><a href="{P}/pricing/">Pricing</a></li><li><a href="{P}/job-descriptions/">Job description templates</a></li><li><a href="{P}/how-to-hire/">How to hire…</a></li><li><a href="{P}/widgets/">Jobs for your website</a></li><li><a href="{P}/api/">Data for developers (API)</a></li><li><a href="{P}/feeds/">Job feeds for channels (RSS)</a></li><li><a href="{P}/partners/">Partners</a></li><li><a href="{P}/media-kit/">Media kit</a></li><li><a href="{P}/investors/">Investors</a></li><li><a href="{P}/plus/">Plus</a></li></ul></div>
<div><p class="fhd">About</p><ul><li><a href="{P}/about/">About</a></li><li><a href="{P}/vs/">Compared with other job sites</a></li><li><a href="{P}/promise/">Our promise</a></li><li><a href="{P}/ahead/">What is new here</a></li><li><a href="{P}/methodology/">How it works</a></li><li><a href="{P}/guides/">Guides</a></li><li><a href="{P}/help/">Help</a></li><li><a href="{P}/glossary/">Glossary</a></li><li><a href="{P}/safety/">Job offer safety</a></li><li><a href="{P}/archive/">Closed jobs archive</a></li><li><a href="{P}/privacy/">Privacy</a></li><li><a href="{P}/terms/">Terms</a></li></ul></div>
</div>{FOOT.get("pop", "")}<p class="fine"><button class="icon ic-t" id="theme" type="button" aria-label="Switch between light and dark"></button> © {TODAY[:4]} {e(SITE)}. Listings come from companies' official careers pages. You always apply on the employer's own site.</p></div></footer>"""


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
    "education-training": "cap", "retail-hospitality": "bag", "languages": "globe", "skilled-trades": "factory", "logistics-transport": "box", "crypto-web3": "hex", "leadership": "crown", "internships-entry-level": "sprout",
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
    if j["remote"]: b.append('<span class="pill ok">Remote, anywhere</span>' if j.get("anywhere") else '<span class="pill ok">Remote</span>')   # how the work is done
    elif j.get("hybrid"): b.append('<span class="pill">Hybrid</span>')
    if j["level"]: b.append(f'<span class="pill">{e(LVL_NAME[j["level"]])}</span>')
    b += [f'<span class="pill">{e(t)}</span>' for t in j["tags"][:3]]
    loc = j["location"] if len(j["location"]) <= 60 else j["location"][:57].rstrip(" ,;") + "…"
    sub = e(j["company"]) + (f" · {loc_flags(j['location'])}{e(loc)}" if loc else "") + (f" · +{extra} more location{'s' if extra > 1 else ''}" if extra else "")
    label, fresh = age(j["posted"])
    return (f'<li class="job{" feat" if j["featured"] else ""}"><a href="{P}/job/{j["slug"]}/">{ava(j["company"])}'
            f'<span><span class="jt">{e(j["title"])}</span><span class="js">{sub}</span></span>'
            f'<span class="jr"><span class="jp{"" if j["salary"] else " none"}">{e(j["salary"][:28]) if j["salary"] else "—"}</span><span class="pills">{"".join(b)}</span><time {when(j)}{" class=\"new\"" if fresh and j["active"] else ""}>{label}</time></span></a></li>')


def eg(html):
    """An example card on a sales page: it must not look or act like a link (a click on `#` only threw the visitor to the top)."""
    return html.replace(f'<a href="{P}/job//">', '<a class="eg">')


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


AI_TAGS = ("AI", "LLM", "Machine Learning", "PyTorch", "TensorFlow", "LangChain", "Computer Vision", "NLP")
ALL_OPEN = [0]          # every open job on the site, set once the jobs are read: "this field is 2.1% of all open jobs"


def faq_for(label, jobs, first=None, extra=()):
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
    qa[1:1] = list(extra)                       # questions only this page can answer (a company's own hiring, say)
    if len(top) > 1:
        qa.append((f"Which companies have the most {label}?",
                   "Right now the most openings are at " + ", ".join(f"{c} ({k:,})" for c, k in top[:-1]) + f" and {top[-1][0]} ({top[-1][1]:,}). The ranking changes as companies open and close roles."))
    if "remote" in label.lower():
        aw = sum(1 for j in jobs if j.get("anywhere"))
        lands_ = Counter(nm for j in jobs for _, nm in countries_of(j["location"] or "")).most_common(5)
        qa.append((f"Which countries are {label} open to?", ", ".join(f"{nm} ({k:,})" for nm, k in lands_) + f": the countries named most in the location lines of the {n_:,} open {label}; "
                   f"{aw:,} say anywhere or worldwide.")) if len(lands_) >= 2 else None
        qa.append((f"Can I do {label} from any country?",
                   (f"Mostly not. {aw:,} of the {n_:,} open {label} are listed as open worldwide; the rest are limited to certain countries or time zones, so check the location line of each job." if aw else
                    f"Mostly not. None of the {n_:,} open {label} is listed as open worldwide today; each is limited to certain countries or time zones, named in its location line.")))
    else:
        qa.append((f"Are there remote {label}?",
                   (f"{r:,} of the {n_:,} open {label} ({100 * r / n_:.0f}%) are listed as remote. Remote roles are often limited to certain countries or time zones, so check the location line of each job."
                    if r else f"None of the {n_:,} open {label} are listed as remote at the moment. Remote roles appear here as soon as employers post them.")))
    for sym_, word_ in (("£", "pounds"), ("€", "euros")):
        lm_ = sorted(m_ for j in jobs if (m_ := local_mid(j.get("salary"), sym_)))
        if len(lm_) >= 10:
            qa.append((f"What do {label} pay in {word_}?", f"{len(lm_):,} of the open postings state a yearly range in {word_}: the median midpoint is {sym_}{median(lm_):,.0f}, and the middle half "
                       f"advertise {sym_}{lm_[len(lm_) // 4]:,.0f} to {sym_}{lm_[3 * len(lm_) // 4]:,.0f}. These are advertised ranges as each employer wrote them, not verified pay."))
    if len(mids) >= 15:
        qa.append((f"What is the median salary of {label}?" if " pay " in f" {label} " else f"What do {label} pay?",
                   f"The median advertised salary is {money(median(mids))}, based on {len(mids):,} open roles that publish a yearly US-dollar range. The middle half of those roles advertise between "
                   f"{money(mids[len(mids) // 4])} and {money(mids[min(len(mids) - 1, 3 * len(mids) // 4)])}. These are advertised ranges, not verified pay. "
                   "Most employers here are technology companies, so the figures run above the wider market for the same work."))
    # What Google's "People also ask" asks about a field (checked 15 Nov 2026 for "data analyst jobs": "Is it hard to get a data analyst
    # job?", "Will AI replace data analysts?", "Is a data analyst still worth it in 2026?"), answered with today's counts, never opinion.
    yrs = sorted(j["years"] for j in jobs if j.get("years"))
    ent = sum(1 for j in jobs if j.get("entry"))
    if n_ >= 20 and (len(yrs) >= 10 or ent):
        one_ = (art(label[:-5]) + " " + label[:-1]) if label.endswith(" jobs") else f"one of the {label}"     # "data analyst jobs" -> "a data analyst job"
        qa.append((f"Is it hard to get {one_}?",
                   f"{ent:,} of the {n_:,} open {label} ({100 * ent / n_:.0f}%) are for beginners: junior roles and internships."
                   + (f" Of the {len(yrs):,} postings that state experience, the median asks for {yrs[len(yrs) // 2]} {'year' if yrs[len(yrs) // 2] == 1 else 'years'}." if len(yrs) >= 10 else "")
                   + f" {n_co:,} {'company is' if n_co == 1 else 'companies are'} hiring and {new7:,} roles were posted in the last seven days. Matching your resume to the skills each posting names helps most; the free resume builder shows the match."))
    ai_ = Counter(t for j in jobs for t in j.get("tags", []) if t in AI_TAGS)
    k_ai = sum(1 for j in jobs if any(t in AI_TAGS for t in j.get("tags", [])))
    if n_ >= 20:
        qa.append((f"How is AI changing {label}?",
                   f"{k_ai:,} of the {n_:,} open {label} ({100 * k_ai / n_:.0f}%) ask for AI or machine-learning skills"
                   + (", most often " + ", ".join(t for t, _ in ai_.most_common(3)) + "." if ai_ else ".")
                   + f" Employers still list {n_:,} such roles today at {n_co:,} {'company' if n_co == 1 else 'companies'}. Counted from the postings' own text on {fdate(TODAY)}."))
    # "What are the 5 skills of customer service?", "What jobs can I get with Python?" (People also ask, 15 Nov 2026)
    sk_ = Counter(t for j in jobs for t in j.get("tags", []))
    if n_ >= 20 and len(sk_) >= 3:
        qa.append((f"What skills do {label} ask for?",
                   "Most often " + ", ".join(f"{t} ({100 * k / n_:.0f}%)" for t, k in sk_.most_common(5)) + f" of the {n_:,} open postings, counted from their own text on {fdate(TODAY)}."))
    ti_ = Counter(re.sub(r"\s+", " ", re.sub(r"\s*[\(\[,|–—-].*$", "", j["title"])).strip() for j in jobs)
    ti_ = [(t, k) for t, k in ti_.most_common(8) if k >= 2 and 3 <= len(t) <= 60][:5]
    if n_ >= 20 and len(ti_) >= 3:
        qa.append((f"Which job titles come up most in {label}?",
                   ", ".join(f"{t} ({k})" for t, k in ti_) + f": the most common titles among the {n_:,} open roles, without the level and place notes in brackets."))
    if n_ >= 20 and ALL_OPEN[0]:
        qa.append((f"Are {label} in demand in {TODAY[:4]}?",
                   f"{n_:,} {label} are open on {SITE} today at {n_co:,} {'company' if n_co == 1 else 'companies'}, {100 * n_ / ALL_OPEN[0]:.1f}% of all {ALL_OPEN[0]:,} open jobs here; "
                   f"{new7:,} were posted in the last seven days." + (f" The median advertised salary is {money(median(mids))}." if len(mids) >= 15 else "")
                   + f" {r:,} ({100 * r / n_:.0f}%) can be done remotely."))
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


def hub_sections(label, js, skip="", min_k=40, drop_tag=""):
    """Who hires, which skills and roles, where, and what it pays at each level: the same set of jobs seen from five sides.
    skip: the sides a page already is ("places" on a London page; several joined by commas). drop_tag: the page's own skill."""
    k = len(js)
    if k < min_k: return "", ""
    plc = label[len("roles in "):] if label.startswith("roles in ") else ""      # a place page: "Job titles in London"
    top, out, ids = [], [], {j["id"] for j in js}
    bars = lambda rows_: '<div class="hbars">' + "".join(
        f'<a href="{P}/{u}"><span class="hn">{e(nm)}</span><span class="hb"><i style="width:{max(3, round(100 * c / rows_[0][2]))}%"></i></span><span class="hc">{c:,} · {100 * c / k:.0f}%</span></a>' for u, nm, c in rows_) + "</div>"
    if "skills" not in skip:
        sk = Counter(t for j in js for t in j["tags"] if t != drop_tag).most_common(7)
        if len(sk) >= 4: top.append(f'<div><h2 class="h2s">Skills asked for in {e(plc or label)}</h2>' + bars([(f"skills/{TAG_SLUG.get(t, slugify(t))}/", t, c) for t, c in sk]) + "</div>")
    if "roles" not in skip:
        rl = sorted(((s_, nm, len(ids & rid)) for s_, (nm, rid) in HUB["roles"].items()), key=lambda x: -x[2])
        rl = [x for x in rl if x[2] >= 8][:7]
        if len(rl) >= 3: top.append(f'<div><h2 class="h2s">Job titles in {e(plc or label)}</h2>' + bars([(f"roles/{s_}/", nm, c) for s_, nm, c in rl]) + "</div>")
    co = Counter(j["company"] for j in js).most_common(12)
    if len(co) >= 4: out.append(section(f"Who is hiring in {plc}" if plc else f"Who is hiring for {label}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, n_, True) for c, n_ in co) + "</ul>"))
    if "places" not in skip:
        pname = {slug: name.removeprefix("the ") for name, slug, _ in PLACES}
        pl = [(p_, c) for p_, c in Counter(p_ for j in js for p_ in j["places"]).most_common(40) if p_ in HUB.get("live", ())][:10]
        if len(pl) >= 4: out.append(section(f"Where the {label} are" if label.startswith("roles ") else f"Where {label} are", '<ul class="tiles">' + "".join(tile(f"locations/{p_}/", pname[p_], c) for p_, c in pl) + "</ul>"
                                            + '<p class="note">A role that lists several places is counted in each of them.</p>'))
    lv = defaultdict(list)
    for j in js:
        if j.get("usd"): lv[LVL_NAME[j["level"]]].append((j["usd"][0] + j["usd"][1]) / 2)
    pay = [(nm, median(v), len(v)) for nm, v in lv.items() if len(v) >= 15]
    if len(pay) >= 2:
        order_ = {LVL_NAME[k]: i for i, k in enumerate(("Intern", "Junior", "", "Senior", "Lead"))}
        out.append(section(f"What jobs in {plc} pay, by level" if plc else f"Pay by level: {label}" if " pay " in f" {label} " else f"What {label} pay, by level", '<div class="tablewrap"><table><tr><th>Level in the title</th><th>Median advertised salary</th><th>Roles counted</th></tr>'
                           + "".join(f"<tr><td>{e(nm)}</td><td><strong>{money(md)}</strong></td><td>{c:,}</td></tr>" for nm, md, c in sorted(pay, key=lambda x: order_.get(x[0], 9)))
                           + '</table></div><p class="note">Medians of the midpoints of advertised yearly US-dollar ranges; a level needs at least 15 such roles. Advertised, not verified pay.</p>'))
    glance = (f'<div class="hubgrid">{"".join(top)}</div><p class="note">Bars show the share of these {k:,} roles; one role can count in several rows.</p>' if top else "")
    return glance, "".join(out)


def job_links(xs, n=8):
    """A few jobs of a set as plain links (title, then company), newest first."""
    return '<ul class="xl">' + "".join(f'<li><a href="{P}/job/{j["slug"]}/">{e(j["title"])}</a> <span>{e(j["company"])}</span></li>' for j in order(xs)[:n]) + "</ul>"


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
    if seg[0] == "skills" and len(seg) == 2 and h1.endswith(" jobs"): return f"skills={q(h1[:-5])}"
    if seg[0] == "roles" and len(seg) == 2 and h1.endswith(" jobs"): return f"q={q(h1[:-5])}"
    if seg[0] == "perks" and len(seg) == 2: return next((f"perk={q(nm)}" for nm, sl, _ in PERKS if sl == seg[1]), "")
    return {"contract": "etype=Contract", "part-time": "etype=Part-time", "internships": "etype=Internship"}.get(seg[0], "") if len(seg) == 1 else ""


# How many pages a topic list may have. The whole site has to fit the hosting limit (the workflow stops above 950 MiB), and a list's
# second and later pages are the first thing to give way as jobs are added: measured on 13 Nov 2026 with 41,187 open jobs, pages 3 to 5
# of all lists weighed 63 MiB and page 2 another 66 MiB. main() sets the number from the count of open jobs; HRN_PAGE_CAP overrides it
# (the workflow builds again with 1 if a build still came out too large).
LIST_PAGES = 2


def act_row(href, label, more=(), note=""):
    """A page's main action right under its opening paragraph, so it is on the first phone screen (SEO_MAP.md): one ink button,
    then at most a couple of plain links and one short line. An href starting with "#" stays on the page."""
    u = lambda h: h if h.startswith(("#", "http")) else f"{P}/{h}"
    return (f'<p class="lact"><a class="btn primary sm" href="{u(href)}">{e(label)}</a>' + "".join(f'<a href="{u(h)}">{e(t)}</a>' for h, t in more)
            + (f"<span>{e(note)}</span>" if note else "") + "</p>")


def list_save(h1, qs, feed_path=""):
    """A list page's main action on the first phone screen: keep the list. It goes into My jobs as the search that gives the same
    jobs, and My jobs counts the jobs posted since the last look (site.js; nothing is sent anywhere). The list's RSS feed beside it."""
    if not qs: return ""
    rss = f'<a href="{P}/{feed_path}feed.xml">RSS feed</a>' if feed_path else ""
    return (f'<p class="lact"><button class="btn primary sm" type="button" data-save-list="{e(qs)}" data-label="{e(h1)}">Save this list</button>{rss}'
            '<span>My jobs then shows how many are new each time you come back. No account, no email.</span></p>')


def alert_form(what, cat="", loc="", search=False):
    """"Email me new jobs like these": the free job alert sign-up (server/src/alerts.js), small and reusable. Shown only once the API is
    on (config.json api_url): a form that goes nowhere is not shown (rule 7). Without a script the form posts itself and the API answers
    with a page; with one, site.js sends it and writes the answer under it. On the search page (search=True) site.js copies the current
    search (words, category, place, remote, least pay) into the hidden fields when it is sent. The field "website" is for programs only."""
    if not CFG["api_url"]: return ""
    uid = "alert-" + re.sub(r"[^a-z0-9-]+", "-", (cat or loc or "search").lower())
    hid = "".join(f'<input type="hidden" name="{k}" value="{e(v)}">' for k, v in (("cat", cat), ("loc", loc)) if v)
    if search: hid = "".join(f'<input type="hidden" name="{k}" value="">' for k in ("q", "cat", "loc", "remote", "sal"))
    return (f'<form class="alertf" method="post" action="{e(CFG["api_url"])}/api/alerts" data-alert{" data-alert-search" if search else ""} aria-labelledby="{uid}-h">'
            f'<h2 id="{uid}-h">Free job alerts: {e(what)}</h2>'
            '<p>New jobs by email, once a day or once a week, at most 20 in a letter. We send a link to confirm first, and every letter can be stopped in one click.</p>'
            f'<div class="alertf-row"><label for="{uid}-e">Your email</label><input id="{uid}-e" type="email" name="email" required autocomplete="email" maxlength="254">'
            f'<label for="{uid}-f">How often</label><select id="{uid}-f" name="freq"><option value="daily">Daily</option><option value="weekly">Weekly</option></select>'
            '<button class="btn primary" type="submit">Email me new jobs</button></div>'
            '<p class="alertf-hp" aria-hidden="true"><label>Leave this empty <input type="text" name="website" tabindex="-1" autocomplete="off"></label></p>'
            f'{hid}<p class="note" role="status" aria-live="polite" data-alert-out></p>'
            f'<p class="note">We keep your address and this search until you unsubscribe, and a note of each letter for 30 days. <a href="{P}/privacy/#alerts">How alerts handle your address</a></p></form>')


def listing(path, h1, title, desc, jobs, intro="", trail=(), per=100, extra="", feed=False, head_html=None, after="", max_pages=None, more=None, faq=None, hub="", accent=None, list_title="", faq_first=None, live="", faq_extra=()):
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
    faq_html, faq_ld = faq_for(faq, jobs, faq_first, faq_extra) if faq else ("", "")
    for n in range(1, pages + 1):
        chunk = rows[(n - 1) * per:n * per]
        top = head_html if head_html is not None else (crumbs(*trail, (h1, "")) + f"<h1>{path_fl(path)}{e(h1)}</h1>" + (f'<p class="lead">{intro}</p>' if intro and n == 1 else "")
                                                       + (list_save(h1, more, path if feed else "") if n == 1 else ""))
        body = (top + (extra if n == 1 else "") + (f'<div class="sec-head lst" id="list"><h2>{e(list_title)}</h2></div>' if list_title and n == 1 and chunk else "")
                + (f'<ul class="jobs"{live if n == 1 else ""}>{"".join(card(j, x) for j, x in chunk)}</ul>' if chunk else '<p class="lead">Nothing here today. The list is rebuilt every hour.</p>')
                + pager_html(path, n, pages) + note + ((hub + after + faq_html) if n == 1 else ""))      # questions last, after what the page shows
        if n == 1:
            # the month in the title, as Upwork and Indeed do on lists that really change: "Data Analyst Jobs (133 open, November 2026)"
            mids_l = sorted((lo + hi) / 2 for j in jobs if j.get("usd") for lo, hi in [j["usd"]])
            pay_l = f", {money(mids_l[len(mids_l) // 4])}–{money(mids_l[3 * len(mids_l) // 4])}" if len(mids_l) >= 15 and "$" not in title else ""
            page(path, re.sub(r"\((\d[\d,]*) open\)", lambda m_: f"({m_.group(1)} open{pay_l or ', ' + MONTH_YEAR})", title, count=1), desc, body, head=ld + faq_ld)
        else: page(f"{path}{n}/", f"{title.rsplit(' | ', 1)[0]}, page {n} | {SITE}", f"Page {n} of {pages}. {desc}", body, head=ld, sitemap=False)


def intern_hub(path, h1, yr, ej):
    """The internships page: the plain meaning of the word, when the openings start, what they pay, who hires interns and where, then the list."""
    k = len(ej)
    top5 = Counter(j["company"] for j in ej).most_common(5)
    n_co = len({j["company"] for j in ej})
    r_ = sum(j["remote"] for j in ej)
    blob = lambda j: j["title"] + " " + (j["excerpt"] or "")
    seasons = [("Summer", r"\bsummer\b", "Roughly May or June to August or September: the usual internship for students, with applications opening the autumn before."),
               ("Fall", r"\b(?:fall|autumn)\b", "A term from about September to December, often next to classes or in a gap term."),
               ("Winter or spring", r"\b(?:winter|spring)\b", "January to May or June; some are co-ops, which last a whole term of full-time work."),
               ("Co-op", r"\bco-?op\b", "A longer placement, usually four to eight months of full-time work, common in the US and Canada.")]
    cnt = [(nm, sum(1 for j in ej if re.search(rx, blob(j), re.I)), what) for nm, rx, what in seasons]
    cnt = [(nm, c, w) for nm, c, w in cnt if c >= 5]
    named = sum(1 for j in ej if re.search(r"\bsummer\b|\bfall\b|\bautumn\b|\bwinter\b|\bspring\b|\bco-?op\b", blob(j), re.I))
    paid = sum(1 for j in ej if j.get("usd"))
    new7 = sum(1 for j in ej if (j["posted"] or "") >= HUB["week"])
    plain = (f"<strong>An internship</strong> is a short job, mostly a few months, where a student or a recent graduate works on real tasks at a company to learn the trade. "
             f"{k:,} are open today, {new7:,} of them posted in the last 7 days. " + intro_for(ej, "internship ", "", hub=True))
    seas = ""
    if cnt:
        seas = section("When the internships start", '<div class="tablewrap"><table><tr><th>Season named in the posting</th><th>Open roles</th><th>What it usually means</th></tr>'
                       + "".join(f"<tr><td><strong>{e(nm)}</strong></td><td>{c:,}</td><td>{e(w)}</td></tr>" for nm, c, w in cnt)
                       + f'</table></div><p class="note">Counted from the words in the job title and text. {named:,} of the {k:,} internships name a season; the others name none. One posting can name two seasons.</p>')
    pay_note = ""
    if paid:
        pay_note = (f'<p class="note">{paid:,} of the {k:,} internships ({round(100 * paid / k)}%) state pay in the posting; the others do not say. '
                    f'Whether an internship pays is worth asking in the first call.</p>')
    glance, tail = hub_sections("internships", ej, skip="roles")
    qa = [("How many internships are open right now?", f"{k:,} at {n_co:,} companies as of {fdate(TODAY)}; {new7:,} were posted in the last seven days. The list is rebuilt every hour from the employers' own careers pages."),
          ("Which companies have the most internships?", "Right now: " + ", ".join(f"{c} ({n_:,})" for c, n_ in top5[:-1]) + f" and {top5[-1][0]} ({top5[-1][1]:,})."),
          ("Are there remote internships?", f"{r_:,} of the {k:,} ({round(100 * r_ / k)}%) are listed as remote; most are done on site, so check the place line of each job."),
          ("Do I need to be a student to apply?", "Many internships ask for a current student or a recent graduate, and the posting says so in its requirements. Some are open to career changers and to people returning to work. The requirements line of each job is the only place that decides it."),
          ("How early should I apply for a summer internship?", "Many large companies open summer roles in the autumn before and fill them over the winter, so applying in September to December gives the most choice. Postings that name a summer are listed in the table above."),
          ("Are internships paid?", f"Only {paid:,} of the {k:,} open internships state a figure in the posting, so for most the answer comes in the first call. Ask before you accept a place, and ask what the pay covers." if paid else "The postings here do not state a figure, so ask in the first call."),
          ("Can an internship turn into a job?", "At some companies, yes, and the posting sometimes says so. We have no figures for how many interns are hired afterwards, so this site gives no percentage.")]
    own = section("Questions about internships", '<dl class="qa">' + "".join(f"<div><dt>{e(q)}</dt><dd>{e(a_)}</dd></div>" for q, a_ in qa) + "</dl>")
    ld_own = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    links = labrow("Also see", [f'<a href="{P}/entry-level/">Entry-level jobs</a>', f'<a href="{P}/crypto/internships/">Crypto internships</a>', f'<a href="{P}/categories/internships-entry-level/">Internships and first jobs</a>',
                                f'<a href="{P}/guides/">Guides</a>', f'<a href="{P}/resume/">Resume builder</a>'])
    ld = crumbs_ld([("All jobs", "jobs/"), (h1, "")])
    top = crumbs(("All jobs", "jobs/"), (h1, "")) + f"<h1>{e(h1)}{e(yr)}</h1>" + f'<p class="lead">{plain}</p>'
    rows = collapse(order(ej))
    per = 100
    shown = rows[:per * LIST_PAGES]
    pages = max(1, -(-len(shown) // per))
    note = (f'<p class="note">Showing the newest {len(shown):,}. <a href="{P}/jobs/?etype=Internship">See all {k:,} in search</a></p>' if len(rows) > len(shown) else "")
    rss(f"{path}feed.xml", f"{h1} — {SITE}", path, order(ej))
    for n in range(1, pages + 1):
        chunk = shown[(n - 1) * per:n * per]
        body = top if n == 1 else crumbs(("All jobs", "jobs/"), (h1, "")) + f"<h1>{e(h1)}</h1>"
        if n == 1: body += hub_stats(ej) + seas + pay_note + glance + links + f'<div class="sec-head lst"><h2>Newest internships</h2></div>'
        body += f'<ul class="jobs">{"".join(card(j, x) for j, x in chunk)}</ul>' + pager_html(path, n, pages) + note + ((tail + own) if n == 1 else "")
        title = f"{h1}{yr} ({k:,} open, {MONTH_YEAR}) | {SITE}"
        desc = (f"{k:,} open internships{yr}: when they start, whether they pay, which companies hire interns and where, straight from employers’ careers pages. Updated hourly.")
        if n == 1: page(path, title, desc, body, head=ld + ld_own)
        else: page(f"{path}{n}/", f"{h1}{yr}, page {n} | {SITE}", f"Page {n} of {pages}. {desc}", body, head=ld, sitemap=False)


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


def job_indexable(j):
    """Every job page goes to search engines: open ones, and closed ones as an archive (the owner, 13 Nov 2026: "every job must be in
    Google, every one"; "keep closed jobs, there may be search traffic on them"). Only posts read from Telegram channels stay out.
    A closed page carries no JobPosting markup (Google's rule for expired jobs), so it can rank as a page without being offered as an
    open job. Pages with only the opening lines of a posting grow into full pages as the collector keeps every open job's full text."""
    return not j.get("tg")


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
    if j["level"]: rows.append(("Level", e(LVL_NAME[j["level"]])))
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
        rows.append(("Source", (f'A post in the public Telegram channel <a href="https://t.me/{e(j["tg"])}" rel="nofollow noopener">@{e(j["tg"])}</a>; not checked with {e(j["company"])}' if j.get("tg") else
                                f"{e(j['company'])}’s own posting, read from {SOURCE_NAME[ats]}, the hiring software it uses" if ats in SOURCE_NAME else "Posted here by the employer; the link was checked" if j.get("direct")
                                else f"{e(j['company'])}’s own posting")))
    meta = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in rows)
    pills = []
    if not j["active"]: pills.append('<span class="pill">Closed</span>')
    if j["remote"]: pills.append('<span class="pill ok">Remote, anywhere</span>' if j.get("anywhere") else '<span class="pill ok">Remote</span>')
    elif j.get("hybrid"): pills.append('<span class="pill">Hybrid</span>')
    if j["salary"]: pills.append(f'<span class="pill sal">{e(j["salary"])}</span>')
    if days_open >= LONG_OPEN: pills.append(f'<span class="pill warn">Open {days_open} days</span>')
    if j["pool"]: pills.append('<span class="pill warn">Talent pool</span>')
    pills += [(f'<a class="pill perk" href="{P}/perks/{PERK_SLUG[x]}/">{e(x)}</a>' if x in PERK_OK else f'<span class="pill perk">{e(x)}</span>') for x in j.get("perks", []) if x in PERK_SLUG]
    if j["level"]: pills.append(f'<span class="pill">{e(LVL_NAME[j["level"]])}</span>')
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
        # Google: the description in JobPosting must be "a complete representation of the job"; an excerpt risks a manual action.
        # A job with only its opening lines keeps its page in search, without the markup, until the collector stores its full text.
        mark_ok = (not j["remote"] or "applicantLocationRequirements" in ld) and ("jobLocation" in ld or "applicantLocationRequirements" in ld) and not j.get("tg") and bool(full)
        if not mark_ok: head, micro = "", ""
        elif full: head, micro = "", microdata(ld)          # description is marked up in place, see microdata()
        else: head, micro = '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>", ""
        host_ = re.sub(r"^www\.", "", re.sub(r"^https?://([^/?#]+).*$", r"\1", j["url"] or "")).lower()
        apply_btn = (f'<a class="btn primary lg" id="apply" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">{"Open the post in Telegram" if j.get("tg") else "Apply on company site"}</a>'
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
        if j.get("tg"):                       # a channel post: no US pay estimate, no "careers page" claim
            pay_line = f" The post gives a salary of {e(j['salary'])}." if j["salary"] else ""
        tldr = (f'<p class="tldr"><strong>{e(j["title"])}</strong> at {e(j["company"])}{where} was posted in the Telegram channel @{e(j["tg"])}'
                + (f' on {fdate(j["posted"])}' if j["posted"] else "") + f'.{pay_line} We read it from the channel’s public page; it was not checked with {e(j["company"])}.</p>') if j.get("tg") else \
               (f'<p class="tldr"><strong>{e(j["title"])}</strong> is open at {e(j["company"])}{where}.{pay_line}'
                + (f' Posted on {fdate(j["posted"])}' if j["posted"] else " It is")
                + (f'{", and" if j["posted"] else ""} still on {e(j["company"])}’s careers page when we last checked, on {fdate(j["last_seen"])}.' if j.get("last_seen") else (". It is open now." if j["posted"] else " open now.")) + "</p>")
    else:
        tldr = (f'<p class="tldr"><strong>{e(j["title"])}</strong> at {e(j["company"])}{where} is closed. '
                f'{"It closed on " + fdate(j["closed"]) if j.get("closed") else "The employer took it down"} and it no longer takes applications.</p>')
    about = tldr + ((f'<div itemscope itemtype="https://schema.org/JobPosting">{micro}<h2>About the role</h2><div class="prose desc" itemprop="description">{full}</div></div>'
                     if micro else f'<h2>About the role</h2><div class="prose desc">{full}</div>')
                    + f'<p class="note">The employer’s own description, as published on {e(j["company"])}’s careers page.</p>' if full else
                    f'<h2>About the role</h2><div class="prose"><p>{e(j["excerpt"])}</p></div><p class="note">'
                    + ("A few lines of the post. The whole post, with the contact to apply, is in the Telegram channel.</p>" if j.get("tg") else f"The opening lines of the posting. The rest is on {e(j['company'])}’s careers page.</p>")
                    if j["excerpt"] else "")
    if FACT.get(j["company"]):
        about += f'<h2 class="h2s">Hiring at {e(j["company"])}</h2><div class="prose"><p>{FACT[j["company"]]} <a href="{comp_url}">See all its roles</a></p></div>'
    if j["active"] and TB.get(j["company"]):        # the employer's marks, the same as on its page: each with its rule and today's number
        about += ('<p class="tbadges">' + "".join(f'<span class="tb" title="{e(why)}"><b>✓ {e(nm)}</b> {e(why)}</span>' for nm, why in TB[j["company"]])
                  + f'<a href="{P}/companies/#marks">What the marks mean</a></p>')
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
                 + (f'<p class="note">You apply through the contact in the channel post, free. The post was read from a public Telegram channel and not checked with the employer.</p>' if j.get("tg") else
                  f'<p class="note">You apply on the employer’s own page, free.{" This job was posted here by the employer; the link was checked when it was published." if j.get("direct") else ""}</p>')
                 + '<p class="share" id="share"></p>'
                 f'<p class="note"><a href="{P}/safety/">How to check that a job offer is real</a>'
                 + (f' · <a href="mailto:{e(MAIL["abuse"])}?subject={e(quote("Listing: " + j["title"] + " at " + j["company"] + " (" + FULL + "/job/" + j["slug"] + "/)"))}" rel="nofollow">Report a problem with this listing</a>' if MAIL.get("abuse")
                    else f' · <a href="https://t.me/{e(CFG["contact_telegram"])}" rel="nofollow noopener">Report a problem with this listing</a>' if CFG.get("contact_telegram") else "") + "</p>") if j["active"] else "") + glance
    loc = f" · {e(j['location'])}" if j["location"] else ""
    body = (crumbs((CAT[j["cat"]], f"jobs/{j['cat']}/"), (j["title"], ""))
            + f'<div class="jhead">{ava(j["company"], "lg")}<div><h1>{e(j["title"])}</h1><span class="js"><a href="{comp_url}">{e(j["company"])}</a>{loc}</span>'
            + f'<div class="pills">{"".join(pills)}</div>'
            + (f'<p class="note" id="match" data-tags="{e("|".join(j["tags"]))}" hidden></p>' if j["tags"] and j["active"] else "") + f"</div></div>{banner}"
            + f'<div class="cols"><article>{about}{sim}</article><aside class="side card">{paybar}{apply_btn}{save_btn.split("</div>", 1)[0] + "</div>" if '<div class="sideact">' in save_btn else ""}<dl class="meta">{meta}</dl>{save_btn.split("</div>", 1)[1] if '<div class="sideact">' in save_btn else save_btn}</aside></div>'
            + (f'<div class="mbar"><a class="btn primary" href="{e(j["url"])}" target="_blank" rel="nofollow noopener">{"Open the post in Telegram" if j.get("tg") else "Apply on company site"}</a></div>' if j["active"] else ""))
    where = j["location"] or ("Remote" if j["remote"] else "")
    title = f"{j['title']} at {j['company']}"
    place_ = re.split(r";|\||•", j["location"])[0].strip(" ,-–") if j["location"] else ""
    if place_ and place_.lower() not in title.lower() and len(title) + len(place_) + 3 <= 65: title += f" ({place_})"
    if not j["active"]: title += " (closed)"
    desc = (f"{j['title']} at {j['company']}" + (f" — {where}" if where else "") + f". {CAT[j['cat']]} role"
            + (", remote" if j["remote"] else "") + (". This job is closed." if not j["active"] else ". Apply through the Telegram post." if j.get("tg") else ". Apply on the company site."))
    # a Telegram post is a few lines of someone else's text: shown to visitors, kept out of search engines and the sitemap
    ok_ = job_indexable(j)
    page(f"job/{j['slug']}/", title, desc, body, head + ("" if ok_ else '<meta name="robots" content="noindex">'), sitemap=ok_, compact=True)


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
# The products of 15 Nov 2026 replaced the launch line (featured, pinned, packs); a page that still asks for the old name gets the new product.
PRICE_ALIAS = {"Featured job": "Standard boost", "Pinned job": "Premium boost"}
price_of = lambda name: PRICE.get(PRICE_ALIAS.get(name, name), {}).get("price", "")
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


def badge_svg(label, value):
    lw, vw = int(34 + 7.7 * len(label)), int(18 + 7.7 * len(value))
    w = lw + vw
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="28" viewBox="0 0 {w} 28" role="img" aria-label="{e(label)}: {e(value)}">'
            f'<rect width="{w}" height="28" rx="6" fill="#121110"/><rect x="{lw}" width="{vw}" height="28" rx="6" fill="#5fd486"/><rect x="{lw}" width="8" height="28" fill="#5fd486"/>'
            f'<circle cx="14" cy="14" r="4" fill="#5fd486"/><text x="25" y="18.5" fill="#fff" font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="12" font-weight="bold">{e(label)}</text>'
            f'<text x="{lw + 9}" y="18.5" fill="#121110" font-family="Verdana,DejaVu Sans,Geneva,sans-serif" font-size="12" font-weight="bold">{e(value)}</text></svg>')


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
    ALL_OPEN[0] = len(active)
    global LIST_PAGES
    LIST_PAGES = int(os.environ.get("HRN_PAGE_CAP") or 1)      # owner, 14 Nov: no Cloudflare yet, so the 70 MiB of second pages goes to more jobs; the search shows the rest
    archived = [j for j in jobs if not j["active"]]
    by_cat = defaultdict(list)
    for j in active: by_cat[j["cat"]].append(j)
    companies = defaultdict(list)
    for j in jobs: companies[j["company"]].append(j)
    n, m = len(active), len({j["company"] for j in active})
    NO_ANON = ("Employers can also post a job themselves; such a posting is published only after its link has been checked automatically, and it is labelled as posted by the employer"
               if CFG["api_url"] else "We do not accept anonymous postings")
    N_FEEDS = len({s_["name"] for f_ in ("sources.json", "sources_tech.json") if (ROOT / f_).exists() for s_ in json.loads((ROOT / f_).read_text())})     # employer feeds read in each run
    # How often a careers page is read: the boards in sources.json and sources_tech.json every hour, those in sources_more.json in
    # turn (HRN_ROTATE in collect.py: every four hours). The copy says exactly that, never "every hour" for all of them.
    HOURLY_SET = {s_["name"] for f_ in ("sources.json", "sources_tech.json") if (ROOT / f_).exists() for s_ in json.loads((ROOT / f_).read_text())}
    ROT_SET = {s_["name"] for s_ in json.loads((ROOT / "sources_more.json").read_text())} if (ROOT / "sources_more.json").exists() else set()
    m_hourly = len({j["company"] for j in active if j["company"] in HOURLY_SET or j["company"] not in ROT_SET})
    # live.py on the server reads every board at least once an hour (config.json "live_collector"), so the four-hour rotation of the
    # hourly build no longer limits how often a company is checked
    ROTATING = m_hourly < len({j["company"] for j in active}) and not CFG.get("live_collector")
    EVERY = "every one to four hours" if ROTATING else "every hour"
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
    fam_show = sorted(fam_rows, key=lambda f: -len(f[4]))      # by open jobs, so the order follows the jobs as sources grow (owner, 15 Nov: "IT first")
    TECH_FAMS = ["software-development", "ai-machine-learning", "data-analytics", "cloud-devops-it", "security", "product-project", "hardware-engineering"]
    # the hero's shortcut chips: among the roles people search for most, the three tech ones with the most open jobs, then two others
    # (the owner, 15 Nov: "IT first: people mostly look for IT"); the order follows the counts
    CHIP_TECH = ["software-engineer", "product-manager", "data-analyst", "data-scientist", "machine-learning-engineer", "devops-engineer", "cloud-engineer",
                 "cybersecurity", "frontend-engineer", "backend-engineer", "product-designer"]
    CHIP_OTHER = ["account-executive", "customer-support", "sales-representative", "marketing-manager", "project-manager", "recruiter", "accounting", "operations-manager"]
    by_n = lambda slugs: sorted((s_ for s_ in slugs if s_ in by_role), key=lambda s_: -len(by_role[s_][1]))
    hero_chips = "".join(f'<a href="{P}/roles/{s_}/">{e(by_role[s_][0][0].upper() + by_role[s_][0][1:])}</a>' for s_ in by_n(CHIP_TECH)[:3] + by_n(CHIP_OTHER)[:2])
    def dir_block(fs, fn, fd, live, js_, top=None, tag="h2"):
        return (f'<div class="dirb"><{tag}><a href="{P}/categories/{fs}/">{icon(fs)}<u>{e(fn)}</u></a><span>{len(js_):,}</span></{tag}><p>{e(fd[0].upper() + fd[1:])}.</p><ul>'
                + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/roles/{s_}/">{e(nm)}</a><span>{c:,}</span></li>' for s_, nm, c in (live if top is None else live[:top]))
                + (f'<li class="more"><a href="{P}/categories/{fs}/">All {len(live)} in {e(rlow(fn))}</a></li>' if top is not None and len(live) > top else "") + "</ul></div>")
    ROLE_TOP = sorted(((nm, s_, len(ROLE_JOBS[s_])) for nm, s_, _ in ROLES if s_ in ROLE_BASE), key=lambda x: -x[2])
    # Pictures before words (the owner: "I cannot read walls of text: more charts and infographics everywhere").
    # Every picture is counted from the open postings on this build; each has one caption that says what it shows.
    # Charts (the owner, 14 Nov: "dumb charts, not necessarily green on black, more modern"): light cards, one blue for magnitude and
    # orange only for the one mark a chart is about, thin columns with rounded ends, a few gridlines, selective labels and a tooltip
    # on every mark (hover or keyboard focus). Colours are tokens (--viz-1, --viz-2) with their own dark-mode steps in style.css.
    def nice_top(v):
        if v <= 0: return 1
        mag = 10 ** (len(str(int(v))) - 1)
        for k in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
            if v <= k * mag: return int(k * mag)
        return int(10 * mag)
    def vcols(points, hi=None, now=None, aria=""):
        """points: [(label under the column, value, tooltip)]. hi: index of the column the chart is about (orange, labelled);
        now: index of a period still filling up (lighter). The tallest column and hi carry their value; every column a tooltip."""
        top = nice_top(max((v for _, v, _ in points), default=0))
        peak = max(range(len(points)), key=lambda i: points[i][1]) if points else None
        grid = "".join(f'<span style="bottom:{100 * t / 2:.0f}%"><em>{fmt_n(top * t // 2)}</em></span>' for t in (1, 2))
        bars = "".join(
            f'<div class="vc-c{" hi" if i == hi else ""}{" now" if i == now else ""}" tabindex="0" data-tip="{e(tip)}" aria-label="{e(tip)}">'
            f'<i style="height:{max(1.5, 100 * v / top):.1f}%">{f"<b>{fmt_n(v)}</b>" if i in (peak, hi) else ""}</i></div>'
            for i, (_, v, tip) in enumerate(points))
        xs = "".join(f"<span>{e(lb)}</span>" for lb, _, _ in points)
        table = ('<table class="sr-only"><tr><th>Period</th><th>Count</th></tr>'
                 + "".join(f"<tr><td>{e(tip.split(' · ')[0])}</td><td>{v:,}</td></tr>" for _, v, tip in points) + "</table>")
        return (f'<div class="vc" role="group" aria-label="{e(aria)}"><div class="vc-plot"><div class="vc-grid">{grid}</div>'
                f'<div class="vc-cols">{bars}</div></div><div class="vc-x">{xs}</div>{table}</div>')
    def fmt_n(v):
        return f"{v / 1000:.1f}K".replace(".0K", "K") if v >= 10000 else f"{v:,}"
    def cols(pairs, hi_=None):                      # the older call: [(label, value)]
        return vcols([(lb, v, f"{lb} · {v:,} jobs") for lb, v in pairs], hi_)
    def meter(part, whole, label):
        """A stat tile: the share as a number, the count it comes from, and a thin bar of the share."""
        pc = round(100 * part / max(1, whole))
        return (f'<div class="st"><span class="st-l">{e(label[0].upper() + label[1:])}</span><b class="st-v">{pc}%</b>'
                f'<span class="st-m" role="img" aria-label="{pc}% {e(label)}"><i style="width:{max(1, pc)}%"></i></span>'
                f'<span class="st-s">{part:,} of {whole:,} jobs</span></div>')
    def donut(part, whole, label):                  # kept name: the three-number pictures are stat tiles now
        return meter(part, whole, label)
    def mini_pics(js):
        """Two pictures for a list of jobs: what they pay (when at least 30 state it) and three rings."""
        if len(js) < 20: return ""
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in js if j["usd"]]
        pay = ""
        if len(mids_) >= 30:
            eg = [(0, 75), (75, 100), (100, 125), (125, 150), (150, 175), (175, 200), (200, 250), (250, 300), (300, 10 ** 6)]
            md_ = median(mids_)
            pay = (f'<figure class="pic"><figcaption><b>What these jobs pay</b>{len(mids_):,} of them state a yearly range in US dollars (bands in thousands). The dark column holds the median, {money(md_)}.</figcaption>'
                   + vcols([(("<75" if lo == 0 else f"{lo}+" if hi > 1000 else f"{lo}"), c_,
                              f"{'under $75K' if lo == 0 else f'${lo}K and more' if hi > 1000 else f'${lo}K to ${hi}K'} · {c_:,} postings")
                             for lo, hi in eg for c_ in [sum(1 for v in mids_ if lo * 1000 <= v < hi * 1000)]],
                            hi=next((i for i, (lo, hi) in enumerate(eg) if lo * 1000 <= md_ < hi * 1000), None), aria="Postings by yearly pay band") + "</figure>")
        rings = (f'<figure class="pic"><figcaption><b>Three numbers</b>Out of {len(js):,} open jobs in this list.</figcaption><div class="stats3">'
                 + donut(sum(j["remote"] for j in js), len(js), "can be done from home") + donut(sum(bool(j["salary"]) for j in js), len(js), "state the pay")
                 + donut(sum(1 for j in js if j["entry"]), len(js), "are for beginners") + "</div></figure>")
        return f'<div class="pics two">{pay}{rings}</div>'
    fam_top = sorted(fam_rows, key=lambda f: -len(f[4]))[:10]
    pic_fields = '<div class="hbars">' + "".join(
        f'<a href="{P}/categories/{fs}/"><span class="hn">{e(fn)}</span><span class="hb"><i style="width:{max(3, round(100 * len(js_) / len(fam_top[0][4])))}%"></i></span><span class="hc">{len(js_):,}</span></a>' for fs, fn, _, _, js_ in fam_top) + "</div>"
    mids_all = [(j["usd"][0] + j["usd"][1]) / 2 for j in active if j["usd"]]
    edges = [(0, 75), (75, 100), (100, 125), (125, 150), (150, 175), (175, 200), (200, 250), (250, 300), (300, 10 ** 6)]
    pay_lb = lambda lo, hi: "<75" if lo == 0 else f"{lo}+" if hi > 1000 else f"{lo}"          # thousands of dollars; the caption says so
    pay_tip = lambda lo, hi: "under $75K" if lo == 0 else f"${lo}K and more" if hi > 1000 else f"${lo}K to ${hi}K"
    med_all = median(mids_all) if mids_all else 0
    q_srt = sorted(mids_all)
    q_lo, q_hi = (q_srt[len(q_srt) // 4], q_srt[(3 * len(q_srt)) // 4]) if q_srt else (0, 0)
    med_i = next((i for i, (lo, hi) in enumerate(edges) if lo * 1000 <= med_all < hi * 1000), None)
    pay_pts = [(pay_lb(lo, hi), c_, f"{pay_tip(lo, hi)} · {c_:,} postings" + (" · the median is here" if i == med_i else ""))
               for i, (lo, hi) in enumerate(edges) for c_ in [sum(1 for v in mids_all if lo * 1000 <= v < hi * 1000)]]
    # New jobs: by day (the last 14 days and today so far) or by week (the last 12 weeks and this one so far). Counted from the
    # jobs still open, by the day the employer posted them; today and this week are drawn lighter because they are still filling.
    today_ = datetime.date.today()
    by_day = Counter((j["posted"] or "")[:10] for j in active)
    days15 = [today_ - datetime.timedelta(days=d) for d in range(14, -1, -1)]
    day_pts = [(f"{d.day}", by_day.get(d.isoformat(), 0), f"{'Today so far' if d == today_ else d.strftime('%a, %b ') + str(d.day)} · {by_day.get(d.isoformat(), 0):,} new jobs") for d in days15]
    wk0 = today_ - datetime.timedelta(days=today_.weekday())
    weeks = [wk0 - datetime.timedelta(weeks=w) for w in range(12, -1, -1)]
    def wk_count(w):
        return sum(by_day.get((w + datetime.timedelta(days=k)).isoformat(), 0) for k in range(7))
    wk_pts = [(f"{w.strftime('%b')} {w.day}" if i % 3 == 0 or w == wk0 else "", wk_count(w),
               f"{'This week so far' if w == wk0 else 'Week of ' + w.strftime('%b ') + str(w.day)} · {wk_count(w):,} new jobs") for i, w in enumerate(weeks)]
    n_pay, n_ent = sum(bool(j["salary"]) for j in active), sum(1 for j in active if j["entry"])
    new_jobs_fig = ('<figure class="pic"><figcaption><b>New jobs</b>Jobs still open, by the day the employer posted them. '
                    'The last column is still filling up.</figcaption>'
                    '<div class="vtabs"><input type="radio" name="nj" id="nj-d" checked><label for="nj-d">By day</label>'
                    '<input type="radio" name="nj" id="nj-w"><label for="nj-w">By week</label>'
                    f'<div class="vtab" id="nj-dp">{vcols(day_pts, now=len(day_pts) - 1, aria="New jobs by day, last 14 days and today")}</div>'
                    f'<div class="vtab" id="nj-wp">{vcols(wk_pts, now=len(wk_pts) - 1, aria="New jobs by week, last 12 weeks and this week")}</div></div></figure>')
    market_pics = ('<div class="pics">'
                   f'<figure class="pic"><figcaption><b>Where the jobs are</b>Open jobs in the ten largest fields. A job can count in two fields.</figcaption>{pic_fields}</figure>'
                   f'<figure class="pic"><figcaption><b>What the postings pay</b>{len(mids_all):,} postings state a yearly range in US dollars: '
                   f'how many sit in each band, by the middle of their range, in thousands of dollars. The dark column holds the median, {money(med_all)}.</figcaption>'
                   f'{vcols(pay_pts, hi=med_i, aria="Postings by yearly pay band")}'
                   + (f'<p class="vc-note"><span><b>{money(med_all)}</b>median</span><span><b>{money(q_lo)}–{money(q_hi)}</b>the middle half of postings</span>'
                      f'<span><b>{sum(1 for v in mids_all if v >= 200000):,}</b>pay $200K or more</span></p>' if mids_all else "") + '</figure>'
                   f'<figure class="pic"><figcaption><b>Three numbers about today’s jobs</b>Out of {n:,} open jobs.</figcaption><div class="stats3">'
                   + meter(len(remote), n, "can be done from home") + meter(n_pay, n, "state the pay") + meter(n_ent, n, "are for beginners") + "</div></figure>"
                   + new_jobs_fig + "</div>")
    ROLE_TOP = [x for x in ROLE_TOP if x[2] >= 20][:12]
    TOOLS = tools_pages.build_tools(page, section, crumbs, e, P, FULL, SITE, V, active, CAT)       # [(path, name, one line)]
    cats = "".join(f'<li><a href="{P}/jobs/{s}/"><b><u>{e(CAT[s])}</u></b><span class="c">{len(by_cat[s]):,} jobs</span><span class="d">{e(skills_info.plain_cat(s))}</span></a></li>'
                   for s in sorted((s for s in CAT if by_cat[s]), key=lambda s: (s == OTHER[0], -len(by_cat[s]))))
    place_html = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in places)
    # the owner, 15 Nov: "United States, then California separately, though that is the US": countries first, then the US
    # states and cities as their own group, cities elsewhere, and parts of the world last
    RULE_ = {slug_: rule_ for _, slug_, rule_ in PLACES}
    p_sorted = sorted(places, key=lambda x: -len(x[2]))
    p_groups = [("Countries", [x for x in p_sorted if isinstance(RULE_[x[1]], str) and RULE_[x[1]] != "region"], 12),
                (f"{fl('US')}United States: states and cities", [x for x in p_sorted if isinstance(RULE_[x[1]], tuple) and RULE_[x[1]][1] == "US"], 8),
                ("Cities in other countries", [x for x in p_sorted if isinstance(RULE_[x[1]], tuple) and RULE_[x[1]][1] != "US"], 6),
                ("Parts of the world", [x for x in p_sorted if RULE_[x[1]] == "region"], 4)]
    place_top = "".join(f'<h3 class="tgroup">{t_}</h3><ul class="tiles">' + "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in xs[:k_]) + "</ul>"
                        for t_, xs, k_ in p_groups if xs)
    comp_top = "".join(tile(f"companies/{slugify(c)}/", c, sum(j["active"] for j in js), True) for c, js in comp_items[:12])
    fresh3 = sum(1 for j in active if age(j["posted"])[1])
    logo_cos = [(c, js) for c, js in comp_items if slugify(c) in LOGOS][:10]
    # one real, open listing taken apart: what a visitor can read on every job page
    aj = next((j for j in latest if not j.get("tg") and j["salary"] and j["remote"] and j.get("years") and j["location"] and len(j["title"]) <= 46 and j.get("usd") and j["cat"] in CATMED
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
    # Survival of a posting (no job site shows it): the daily chance that an open posting of a given age closes, from the closings
    # we have seen since tracking began, per age band and, where there are enough closings, per field. site.js turns it into
    # "still open in 7 days: about N%" on each job page. It gets more exact every day the data grows.
    # A whole job board that empties in one day is a move to another hiring system (Shield AI left Lever for Ashby on 13 Nov 2026, 673
    # postings in one run), not 673 jobs filled: such closings, and those jobs, are left out of every closing figure.
    SURV = {}
    co_open_on, co_closed_on = Counter(), Counter()
    for j in jobs:
        if not j["active"] and j.get("closed"): co_closed_on[(j["company"], j["closed"])] += 1
    for (c_, d_), k_ in list(co_closed_on.items()):
        if k_ >= 20: co_open_on[(c_, d_)] = sum(1 for j in jobs if j["company"] == c_ and j["first_seen"][:10] <= d_ and (j["active"] or (j.get("closed") or "") >= d_))
    MOVED = {cd for cd, k_ in co_closed_on.items() if k_ >= 20 and k_ >= 0.8 * max(1, co_open_on[cd])}
    moved_n = sum(co_closed_on[cd] for cd in MOVED)
    try:
        d0_ = min(datetime.date.fromisoformat(j["first_seen"][:10]) for j in jobs if j.get("first_seen"))
        today_ = datetime.date.fromisoformat(TODAY[:10])
        BANDS = (7, 30, 90, 10 ** 6)                       # upper age (days since posting) of each band
        band = lambda a: next(i for i, u in enumerate(BANDS) if a <= u)
        def hazard(sel):
            ex, ev = [0.0] * len(BANDS), [0] * len(BANDS)
            for j in sel:
                if not j["active"] and (j["company"], j.get("closed")) in MOVED: continue      # a board move, not a closing
                try: posted = datetime.date.fromisoformat((j.get("posted") or j["first_seen"])[:10])
                except (KeyError, ValueError): continue
                start = max(datetime.date.fromisoformat(j["first_seen"][:10]), d0_)
                end = datetime.date.fromisoformat(j["last_seen"][:10]) if not j["active"] else today_
                for k in range(max(1, (end - start).days)):          # each day the posting was watched is a day it could have closed
                    ex[band(max(0, (start - posted).days + k))] += 1
                if not j["active"]: ev[band(max(0, (end - posted).days))] += 1
            return [round(ev[i] / ex[i], 5) if ex[i] >= 200 else None for i in range(len(BANDS))], sum(ev)
        h_all, n_ev = hazard(jobs)
        by_c = defaultdict(list)
        for j in jobs: by_c[j["cat"]].append(j)
        h_cat = {}
        for c_, js_ in by_c.items():
            h_, n_ = hazard(js_)
            if n_ >= 30: h_cat[c_] = h_
        write("data/survival.json", json.dumps({"since": d0_.isoformat(), "closed": n_ev, "bands": BANDS[:-1], "all": h_all, "cat": h_cat}, separators=(",", ":")), sitemap=False)
        h_ent, n_ent_ev = hazard([j for j in jobs if j["level"] in ("Junior", "Intern")])
        SURV = {"since": d0_, "days": (today_ - d0_).days + 1, "closed": n_ev, "all": h_all, "cat": h_cat, "entry": h_ent if n_ent_ev >= 30 else None,
                "entry_closed": n_ent_ev, "moved": moved_n, "moved_cos": sorted({c_ for c_, _ in MOVED})}
    except ValueError:
        pass
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
    shot_panels = "".join(f'<ul class="jobs" data-panel="{i_}"{" data-live=home" if i_ == 0 else " hidden"}>{r_}</ul>' for i_, (_, _, r_) in enumerate(shot_tabs))   # "Latest jobs" takes new jobs live (site.js)
    rem_n = sum(1 for j in active if j["remote"])
    paid_n = sum(1 for j in active if j["salary"])
    hero = (f'<section class="hero v2"><div class="wrap">'
            f'<p class="stamp"><i></i>Jobs hiring now · <b>{n:,}</b> open, checked {fdate(TODAY, False)} <span class="wide-only"> · <b>{fresh3:,}</b> new in 3 days</span></p>'
            f'<h1>Stop applying to jobs that are <span class="hl">already gone</span></h1>'
            f'<p class="sub">Old listings stay online long after the job is filled: ghost jobs. We read {m:,} company career pages' + (f', {m_hourly:,} of them every hour and the rest every four hours,' if ROTATING else ' every hour') + ' and keep only what is still open.</p>'
            f'<form class="searchbar two" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Software engineer, data analyst, customer service…" aria-label="What: job title, skill or company">'
            f'<span class="sb-sep" aria-hidden="true"></span><input type="search" name="where" placeholder="City, country or remote" aria-label="Where: city, country or remote"><button class="btn primary">Search jobs</button></form>'
            f'<p class="popular"><a class="pop-tech" href="{P}/tech/">Tech jobs</a>{hero_chips}<a href="{P}/remote/">Remote</a><a href="{P}/new/">New this week</a><a href="{P}/with-salary/">Salary listed</a>'
            f'<a href="{P}/entry-level/">Entry-level</a><a href="{P}/categories/">All categories</a><a href="{P}/locations/">By country</a></p>'
            f'<p class="near" id="near" hidden></p>'
            f'<div class="hstats"><div><b>{n:,}</b><span>open jobs today</span></div><div><b>{m:,}</b><span>companies, read {EVERY}</span></div>'
            f'<div><b>{rem_n:,}</b><span>can be done from home</span></div><div><b>{len(by_role)}</b><span>kinds of work</span></div></div></div>'
            f'<div class="wrap"><div class="shot"><div class="shot-bar"><span class="dots" aria-hidden="true"><i></i><i></i><i></i></span>'
            f'<div class="shot-tabs" id="shot-tabs">{shot_nav}</div></div>'
            f'<div class="shot-body"><div id="shot-panels">{shot_panels}<p class="shot-more"><a class="btn" id="shot-more" href="{P}/jobs/">See all {n:,} jobs</a></p></div>'
            f'<aside class="shot-side">'
            f'<a class="scard" href="{P}/for-you/"><b>Not sure what to search for?</b><span>Answer five questions and see the jobs that fit you, each with the reasons.</span><em>Find my fit</em></a>'
            f'<a class="scard" href="{P}/resume/"><b>Resume builder</b><span>Five templates, PDF and Word, and an example resume for your kind of work.</span><em>Build a resume</em></a>'
            f'<a class="scard" href="{P}/salaries/"><b>What jobs pay</b><span>{paid_n:,} postings state the pay. See the median for your work.</span><em>Check salaries</em></a>'
            f'<a class="scard" href="{P}/tools/"><b>{len(TOOLS)} free tools</b><span>Resume review, offer check, letters, interview answers.</span><em>Open the tools</em></a>'
            f'</aside></div></div></div>'
            f'<div class="wrap0 hero-logos"><p>Read from the career pages of</p><div class="logorow">'
            + "".join(f'<a href="{P}/companies/{slugify(c)}/" title="{e(c)}: {sum(j["active"] for j in js):,} open roles">{ava(c)}<span>{e(c)}</span></a>' for c, js in logo_cos)
            + f'<a class="more" href="{P}/companies/">and {len(companies) - len(logo_cos)} more</a></div></div></section>')
    plus_band = ""
    if CFG.get("plus", {}).get("live"):
        plus_band = (f'<div class="band"><div><h2>Get the email when a matching job appears</h2><p>Plus watches your saved searches and helps with the resume and cover letter for each posting. One payment, nothing renews.</p></div>'
                     f'<a class="btn" href="{P}/plus/">See Plus</a></div>')
    # The owner, 14 Nov: "the green I do not like, and it must say that it is free". A light card; "free" first and big.
    band = (f'<div class="band"><div><p class="band-k">For employers</p><h2>Post a job for <span class="free">free</span></h2>'
            f'<p>A standard listing costs nothing and sits next to {n:,} open jobs from {m:,} companies. Want it first in its list? A featured listing, from {price_of("Featured job")}, paid in crypto.</p></div>'
            f'<a class="btn primary" href="{P}/post-a-job/">Post a job — free</a></div>')
    ORG_LD[0] = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": FULL + "/", "logo": FULL + "/brand/icon-512.png"}) + "</script>")
    wk_ = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    co_top = Counter(j["company"] for j in active).most_common(10)
    co_new = Counter(j["company"] for j in active if (j.get("first_seen") or "") >= wk_)
    new_today = sum(1 for j in active if j.get("first_seen") == TODAY)
    closed_today = sum(1 for j in jobs if not j["active"] and j.get("closed") == TODAY)
    def age_(j):
        try: return (datetime.date.today() - datetime.date.fromisoformat((j.get("posted") or j.get("first_seen") or TODAY)[:10])).days
        except ValueError: return 0
    old90 = sum(1 for j in active if age_(j) >= LONG_OPEN)
    rem_pay = defaultdict(list)
    for j in active:
        if j["remote"] and j["usd"]: rem_pay[CAT[j["cat"]]].append((j["usd"][0] + j["usd"][1]) / 2)
    rem_rank = sorted(((median(v), k_, len(v)) for k_, v in rem_pay.items() if len(v) >= 15), reverse=True)
    rem_count = Counter(CAT[j["cat"]] for j in active if j["remote"])
    ent_rank = sorted(((sum(1 for j in v if j.get("entry")) / len(v), CAT[c_], sum(1 for j in v if j.get("entry"))) for c_, v in by_cat.items() if len(v) >= 100 and c_ != OTHER[0]), reverse=True)[:3]
    FAQ = [("What company is hiring the most right now?", "On " + fdate(TODAY) + ", by open jobs on " + SITE + ": " + ", ".join(f"{c_} ({k_:,})" for c_, k_ in co_top[:5])
            + ". Counted from each company’s own careers page, re-read " + EVERY + "."),
           ("How do I tell if a job posting is a ghost job?", "Five signs: the job is not on the company’s own careers page; it has been up for months (30, 60, 90 days or more); "
            "it is reposted again and again; the description is vague; or someone asks for money or personal data early. Every job here is read from the employer’s own page "
            f"and leaves the list when it is taken down there ({closed_today:,} today); {old90:,} open jobs posted {LONG_OPEN}+ days ago are marked as such."),
           ("Why are there so many ghost jobs?", "Companies keep postings up to collect applicants for later, to look like they are growing, or because their rules require an outside posting "
            "for a role they will fill inside (the US Congressional Research Service lists these reasons). Job boards that copy listings rarely check whether they are still open."),
           ("What is the best remote job right now?", ("By pay, the remote work with the highest median advertised salary today is " + ", ".join(f"{k_} ({money(m_)}, {c_:,} postings with pay)" for m_, k_, c_ in rem_rank[:3])
            + ". By number of openings: " + ", ".join(f"{k_} ({c_:,})" for k_, c_ in rem_count.most_common(3)) + ".") if rem_rank else "See the remote jobs page: it counts open remote roles by kind of work."),
           ("How can I make $2,000 a week working from home?", ("$2,000 a week is about $104,000 a year. Remote kinds of work whose median advertised salary is above that today: "
            + ", ".join(f"{k_} ({money(m_)})" for m_, k_, c_ in rem_rank if m_ >= 104000)[:300] + ". Postings state pay before tax.") if any(m_ >= 104000 for m_, _, _ in rem_rank) else
            "Few remote postings here state that much; the remote jobs page shows pay by kind of work."),
           ("What’s the easiest job to get right now?", ("The kinds of work with the largest share of junior roles and internships today: " + ", ".join(f"{k_} ({100 * sh_:.0f}%, {c_:,} roles)" for sh_, k_, c_ in ent_rank)
            + ". The entry-level page lists them all.") if ent_rank else "The entry-level page lists junior roles and internships."),
           ("Where do the jobs come from?", "Straight from the official careers pages of companies. Every listing links to the original posting, and you apply on the employer's own site."),
           ("How often is the site updated?", "Every hour. New roles are added. A role the company has closed keeps its page at the same address, marked as closed, and leaves the lists of open jobs."),
           ("Is it free?", "Yes. Searching, saving jobs, tracking your applications and applying are free. A paid Plus plan with email alerts and AI resume tools is on the way; no job will be held back for it."),
           ("Do I need an account?", "No. Saved jobs, application statuses and saved searches are kept in your browser."),
           ("Can I see salaries?", "Where the employer publishes a range, we show it, let you filter and sort by it, and use it for the salary pages.")]
    faq_html = '<div class="faq2">' + "".join(f'<details><summary>{e(q_)}</summary><p>{e(a_)}</p></details>' for q_, a_ in FAQ) + "</div>"
    faq_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in FAQ]}) + "</script>")
    top_paid = diverse_pairs(sorted(((j, j["usd"]) for j in active if j["usd"]), key=lambda x: -x[1][1]), 8)
    pay_max = max((u[1] for _, u in top_paid), default=1) or 1
    paid_board = '<ol class="payrank">' + "".join(
        f'<li><a href="{P}/job/{j["slug"]}/"><span class="pr-n">{i}</span>{ava(j["company"])}'
        f'<span class="pr-t"><b>{e(j["title"])}</b><span>{e(j["company"])}{" · " + loc_flags(j["location"]) + e(j["location"][:48]) if j["location"] else ""}</span></span>'
        f'<span class="pr-p"><b>{e(money(u[0]))}–{e(money(u[1]))}</b><span class="pr-b" aria-hidden="true"><i style="left:{100 * u[0] / pay_max:.1f}%;width:{max(2, 100 * (u[1] - u[0]) / pay_max):.1f}%"></i></span></span></a></li>'
        for i, (j, u) in enumerate(top_paid, 1)) + "</ol>"
    # From the future: what this site does that no job site does yet (the owner: "think 30 years ahead, I do not see it").
    # Defined here so the home page shows them; /ahead/ lists them first, then the earlier ten.
    # The previews show real figures, so they need no "example" label: the 7-day chance for a posting 8 to 30 days old, from the
    # closings we saw, and the skill GPS counted for a resume that names Python and SQL.
    still7 = round(100 * (1 - SURV["all"][1]) ** 7) if SURV and SURV["all"][1] is not None else None
    gps_have, gps_gain = {"Python", "SQL"}, Counter()
    for j in active:
        if len(gps_have & set(j["tags"])) == 1: gps_gain.update(t for t in j["tags"] if t not in gps_have)
    gps_top = gps_gain.most_common(2)
    gps_rows = "".join(f'<span class="rw"><span>{e(t)}</span><span class="mt"><i style="width:{max(8, round(100 * k / gps_top[0][1]))}%"></i></span><b>+{k:,}</b></span>' for t, k in gps_top)
    FUTURE = [
        ("Will it still be open next week?", "Every job page estimates the chance the posting is still open in 7 days, from the closings we see every hour. No job site shows this.", "jobs/",
         (f'<span class="big">{still7}%<small>still open in 7 days</small></span><span class="ln">A posting 8 to 30 days old, from the closings we see every hour</span>' if still7
          else '<span class="ln"><b>Still open in 7 days?</b></span><span class="ln">Counted from the closings we see every hour</span>')),
        ("Skill GPS: the one skill to learn next", "The resume builder counts, across every open job, which single skill would bring the most jobs within your reach, and what they pay.", "resume/",
         gps_rows + '<span class="ln">more open jobs within reach of a resume with Python and SQL</span>'),
        ("Practise the interview out loud", "On every interview questions page the browser reads a question, listens to your answer and checks its length, the numbers and whether you said what you did.", "interview-questions/",
         '<span class="ln"><b>“Walk me through a project where you used SQL.”</b></span><span class="ln">✓ length · ✓ a number · ✓ pace · → more “I”, less “we”</span>'),
        ("Your AI assistant, already briefed", "One click opens ChatGPT, Claude or Perplexity with your resume and the job in a ready request: tailor the resume, write the letter, rehearse the interview.", "resume/",
         '<span class="ln"><b>Tailor it to the target job</b></span><span class="ln">ChatGPT · Claude · Perplexity</span><span class="sk" style="width:70%"></span>'),
        ("A resume that targets one job", "Open a job, press “Tailor my resume to this job”: the builder shows the match in percent and the missing skills, each one button away.", "resume/",
         '<span class="ln"><b>Match with this job</b></span><span class="ln">Add a skill it asks for and watch the match rise</span><span class="sk" style="width:55%"></span>'),
        ("Every job straight from the employer", "Each posting is read from the employer’s own hiring system and re-checked every hour; your own browser can ask that system whether the job is still there.", "jobs/",
         '<span class="ln"><b>✓ Employer’s own posting</b></span><span class="ln">Read from the employer’s hiring system · checked this hour</span>'),
    ]
    GO = {"jobs/": "Open a job", "resume/": "Open the resume builder", "interview-questions/": "Pick a role"}
    future_home = section("Free extras on every job", '<div class="tgrid">' + "".join(
        f'<a class="tcard" href="{P}/{u}"><span class="tprev" aria-hidden="true">{scr}</span><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span><i><u>{GO.get(u, "Open")}</u></i></span></a>' for t_, d_, u, scr in FUTURE[:3]) + "</div>",
        ("ahead/", "Everything else the site does"), sub="No account, nothing sent to us: each one works in your browser.")
    home = ('<section class="sec" id="home-recent" hidden><div class="sec-head"><h2>Pick up where you left off</h2><a href="' + P + '/my-jobs/">My jobs</a></div><ul class="jobs" id="home-recent-list"></ul></section>'
            + (section("Featured employers", spot_tiles(spot_cos), ("post-a-job/", "Feature your company")) if spot_cos else "")

            + section("Browse jobs by category", '<div class="dir">' + "".join(dir_block(*f, top=4, tag="h3") for f in fam_show) + "</div>", ("categories/", f"All {len(by_role)} kinds of work"), sub="Pick the kind of work you do; each group opens its own list of jobs.")
            + section("The job market today", market_pics, ("insights/", "All rankings and charts"), sub="Counted from the open jobs on every update.")
            + pulse + anatomy
            + section("Highest paid right now", paid_board, ("salaries/", "Salary data"), sub="Only jobs that state a yearly pay, converted to US dollars. The bar shows the range against the top one.")
            + '<section class="sec"><div class="sec-head"><h2>Browse the jobs</h2></div><div class="tabs2">'
              '<input type="radio" name="dir" id="dir-role" checked><label for="dir-role">By role</label>'
              '<input type="radio" name="dir" id="dir-loc"><label for="dir-loc">By location</label>'
              '<input type="radio" name="dir" id="dir-co"><label for="dir-co">By company</label>'
              '<div class="tabp" id="p-role"><ul class="tiles">' + "".join(tile(f"roles/{s_}/", nm, k_) for nm, s_, k_ in ROLE_TOP) + f'</ul><p class="tabmore"><a href="{P}/categories/">All {len(by_role)} roles, by category</a></p></div>'
              + f'<div class="tabp" id="p-loc">{place_top}<p class="tabmore"><a href="{P}/locations/">All {len(places)} locations</a></p></div>'
              + f'<div class="tabp" id="p-co"><ul class="tiles">{comp_top}</ul><p class="tabmore"><a href="{P}/companies/">All {len(companies)} companies</a></p></div></div></section>'
            + plus_band + band
            + future_home
            + section("Free tools, no sign-up", '<div class="tgrid">' + "".join(tools_pages.TILES[u] for u in tools_pages.EXTRA + [u for u, nm, d_ in TOOLS[:3]]) + "</div>",
                      ("tools/", f"All {len(TOOLS) + len(tools_pages.EXTRA)} tools"))
            + section("Our jobs on your site, free", '<div class="tgrid own">'
                      f'<a class="tcard" href="{P}/widgets/"><span class="tprev" aria-hidden="true">'
                      '<span class="wl"><b>Senior Data Engineer</b><span>Spotify · Remote</span></span><span class="wl"><b>Product Designer</b><span>Monzo · London</span></span>'
                      '<span class="wl"><b>DevOps Engineer</b><span>GitLab · Remote</span></span></span>'
                      '<span class="tbody"><b>A list of jobs for your site</b><span>For a blog, a community or a company site: paste a short code once and the list stays fresh by itself.</span><i><u>Make yours</u></i></span></a>'
                      f'<a class="tcard" href="{P}/widgets/"><span class="tprev center" aria-hidden="true"><img src="{P}/hiring-badge.svg" alt="" width="220" height="48" loading="lazy"></span>'
                      '<span class="tbody"><b>A “we’re hiring” badge with a live number</b><span>A small picture that shows how many roles are open today, for a footer, a post or a project page.</span><i><u>Get the badge</u></i></span></a>'
                      f'<a class="tcard" href="{P}/board/"><span class="tprev tv" aria-hidden="true"><span class="tvh"><b>Fresh on the board</b><span>2 / 4 · 19:34</span></span>'
                      '<span class="tvr"><em>1D</em>Data Engineer<span>itD Tech</span></span><span class="tvr"><em>1D</em>Account Executive<span>Staffbase</span></span>'
                      '<span class="tvr"><em>2D</em>GTM Specialist<span>ZoomInfo</span></span></span>'
                      '<span class="tbody"><b>A live wall for an office screen</b><span>For a TV in the office, a coworking space or a classroom: fresh jobs fill the screen and turn the page every 9 seconds.</span><i><u>Open the wall</u></i></span></a>'
                      f'<a class="tcard" href="{P}/api/"><span class="tprev" aria-hidden="true"><code>GET /api/v1/latest.json\n{{ "total": {n},\n  "jobs": [{{ "title": "…",\n    "company": "…" }}] }}</code></span>'
                      '<span class="tbody"><b>For programmers</b><span>The whole job list as data that programs can read, refreshed every hour. Free, with nothing to sign up for.</span><i><u>See the API</u></i></span></a>'
                      '</div>')
            + section("Companies hiring the most right now", '<ul class="tiles">' + "".join(
                f'<li><a class="tile" href="{P}/companies/{slugify(c_)}/">{ava(c_, "sm")}<span class="n">{e(c_)}</span><span class="c">{k_:,}{" · " + str(co_new[c_]) + " new" if co_new.get(c_) else ""}</span></a></li>' for c_, k_ in co_top)
                + "</ul>", ("companies/", "All companies"), sub=f"Open jobs at each company on {fdate(TODAY)}, and how many were added in the last seven days.")
            + section("How ghost jobs are kept out", '<ol class="steps">'
                      f'<li><b>Only the employer’s own page.</b> Every job is read from the company’s careers page or hiring system, never copied from another job board.</li>'
                      f'<li><b>Checked {EVERY}.</b> A job the employer takes down leaves the list at the next check: {closed_today:,} so far today. {new_today:,} new jobs were added today.</li>'
                      f'<li><b>Old postings are marked.</b> {old90:,} open jobs were posted {LONG_OPEN} or more days ago; their pages say so.</li>'
                      '<li><b>Reposts are shown.</b> When a company reposts a role it closed, the job page says when the earlier posting closed.</li>'
                      f'<li><b>Scam signs are listed.</b> Requests for money, chat apps or software installs: <a href="{P}/safety/">how to check an offer</a>.</li></ol>')
            + section("What people hate about job sites, and what we do instead", '<div class="feats">'
                      '<div class="feat"><h3>Redirects and second forms</h3><p>“Apply” here opens the employer’s own page, and the button says which address it opens. No middle site, no lead form.</p></div>'
                      '<div class="feat"><h3>Sign-up walls and phone numbers</h3><p>No account and no phone number to search, save or apply: nothing to get locked out of, and nothing to sell to call centres.</p></div>'
                      f'<div class="feat"><h3>Jobs that closed long ago</h3><p>Every job is re-read {EVERY}; a closed one leaves the list, and every job shows how old it is.</p></div>'
                      '<div class="feat"><h3>Trials that turn into a yearly charge</h3><p>Every price is a single payment. Nothing renews by itself, and there is no card on file to cancel.</p></div></div>',
                      ("promise/", "What we will never do"))
            + section("Where the jobs come from and how the site works", faq_html))
    home_desc = f"Job search without ghost jobs: {n:,} jobs hiring now at {m:,} companies, read from their own career pages {EVERY}. {new_today:,} new today. Free, no account."
    if len(home_desc) > 165: home_desc = home_desc.removesuffix(" Remote and salary filters.")
    page("", f"Job Search: {n:,} Jobs Hiring Now, Checked Every Hour | {SITE}",
         home_desc, home, hero=hero,
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": FULL + "/",
               "potentialAction": {"@type": "SearchAction", "target": FULL + "/jobs/?q={search_term_string}", "query-input": "required name=search_term_string"}}) + "</script>" + faq_ld + ORG_LD[0])
    rss("feed.xml", f"{SITE} — latest jobs", "", active)

    # Search page
    opts = "".join(f'<option value="{s}">{e(CAT[s])}</option>' for s in CAT if by_cat[s])
    # places grouped like the home page, each country with its flag (the owner's rule), A to Z inside a group
    rule_l = {sl_: r_ for _, sl_, r_ in PLACES}
    flag_t = lambda cc: "".join(chr(0x1F1E6 + ord(ch) - 65) for ch in cc) + " " if cc and len(cc) == 2 and cc.isalpha() and cc.isupper() else ""
    cc_of = lambda sl_: (rule_l.get(sl_) if isinstance(rule_l.get(sl_), str) and len(rule_l.get(sl_)) == 2 else rule_l.get(sl_)[1] if isinstance(rule_l.get(sl_), tuple) else "")
    grp_l = {"Countries": [], "US states": [], "Cities": [], "Parts of the world": []}
    for name, slug, _ in places:
        r_ = rule_l.get(slug)
        grp_l["Parts of the world" if r_ == "region" else "Countries" if isinstance(r_, str) else
              "US states" if r_[1] == "US" and ", " not in name and slug != "san-francisco" else "Cities"].append((name, slug))
    loc_opts = "".join(f'<optgroup label="{g_}">' + "".join(f'<option value="{sl_}">{flag_t(cc_of(sl_))}{e(nm_.removeprefix("the "))}</option>'
                                                         for nm_, sl_ in sorted(v_, key=lambda x: x[0].removeprefix("the "))) + "</optgroup>" for g_, v_ in grp_l.items() if v_)
    skill_counts = Counter(t for j in active for t in j["tags"])
    top_skills = [t for t, _ in skill_counts.most_common(18)]
    skill_chips = "".join(f'<button class="chipbtn" type="button" data-skill="{e(t)}" aria-pressed="false">{e(t)}</button>' for t in top_skills)
    group = lambda label, inner, cls="": f'<div class="fgroup{" " + cls if cls else ""}"><span class="flabel">{label}</span>{inner}</div>'
    search = (crumbs(("All jobs", "")) + '<h1 class="h1s">Search jobs</h1>'
              f'<form class="searchbar wide" id="qform">{ICON_SEARCH}<input type="search" id="q" list="sugg" placeholder="Customer service, nurse, data analyst…" aria-label="Search jobs" autocomplete="off"><button class="btn primary">Search</button></form>'
              '<button class="btn ghost sm" id="ftoggle" type="button" aria-expanded="false">Filters</button>'
              '<div class="sgrid haspane" id="search"><aside id="fwrap" aria-label="Filters">'
              + group("Posted", '<select id="age" aria-label="Posted"><option value="">Any time</option><option value="1">Last 24 hours</option><option value="3">Last 3 days</option><option value="7">Last 7 days</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option></select>')
              + group("Category", f'<select id="cat" aria-label="Category"><option value="">All categories</option>{opts}</select>')
              + group("Level", '<select id="lvl" aria-label="Level"><option value="">Any level</option><option>Intern</option><option>Junior</option><option>Senior</option><option value="Lead">Lead and above</option><option value="Exec">Director and above</option></select>')
              + group("Location", f'<div class="floc"><select id="loc" aria-label="Location"><option value="">Anywhere</option>{loc_opts}</select>'
                      '<input type="search" id="city" list="city-list" placeholder="Any city, e.g. Leeds" aria-label="City" autocomplete="off"></div>'
                      '<datalist id="city-list"></datalist>'
                      '<label class="check" id="f-rc-w" hidden style="margin-top:8px"><input type="checkbox" id="f-rc"> <span id="f-rc-l">Hide remote jobs closed to my country</span></label>', "f-loc")
              + group("Salary", '<select id="sal" aria-label="Salary"><option value="">Any salary</option><option value="1">Salary listed</option><option value="100000">$100K+</option>'
                                '<option value="120000">$120K+</option><option value="150000">$150K+</option><option value="180000">$180K+</option><option value="200000">$200K+</option>'
                                '<option value="250000">$250K+</option><option value="300000">$300K+</option></select>'
                                '<div class="filters" style="margin-top:8px"><label hidden><input type="checkbox" id="f-nosal"> Also show jobs that do not state pay</label></div>')
              + group("Work style", '<div class="filters"><label><input type="checkbox" id="f-remote"> Remote</label><label><input type="checkbox" id="f-hybrid"> Hybrid</label><label><input type="checkbox" id="f-any"> Work from anywhere</label>'
                                    '<label><input type="checkbox" id="f-entry"> Entry-level</label><label><input type="checkbox" id="f-crypto"> Crypto &amp; web3</label></div>', "f-work")
              + '<details class="morefilters"><summary>More filters</summary><div class="mf">'
              + group("Search in", '<div class="filters"><label><input type="checkbox" id="f-ti"> Job titles only</label></div>')
              + group("Leave out", '<div class="filters"><label><input type="checkbox" id="f-real"> Roles open 90+ days and talent pools</label></div>'
                                   '<div class="filters"><label><input type="checkbox" id="f-ha"> Jobs I already applied to</label></div>'
                                   '<div class="filters xlv"><span class="note">Levels:</span>' + "".join(f'<label><input type="checkbox" class="f-xl" value="{x}"> {LVL_NAME[x]}</label>' for x in ("Intern", "Junior", "Senior", "Lead")) + '</div>'
                                   '<input type="text" id="xwords" class="xin" placeholder="Words in the title, e.g. senior, sales" aria-label="Words to leave out of results" autocomplete="off">'
                                   '<div id="xcos" class="xcos"></div>')
              + group("Perk", '<select id="perk" aria-label="Perk"><option value="">Any perk</option>' + "".join(f'<option value="{e(nm)}">{e(nm)}</option>' for nm, _, _ in PERKS) + "</select>")
              + group("Type", '<select id="etype" aria-label="Type"><option value="">Any type</option><option>Full-time</option><option>Contract</option><option>Part-time</option><option>Internship</option></select>')
              + group("Skills", f'<div class="skillbar" id="skills">{skill_chips}</div>')
              + '</div></details><div class="fgroup fclear"><button class="linkbtn" id="fclear" type="button">Clear all filters</button></div></aside>'
              '<div><p class="note srch-promise">Every job opens on the employer’s own page · no account, no phone number · closed jobs leave the list within the hour · '
              f'<a href="{P}/promise/">what we never do</a></p>'
              '<div class="rbar"><p class="note" id="count">Loading…</p><div class="rtools">'
              '<select id="sort" aria-label="Sort"><option value="new">Newest first</option><option value="rel">Best match</option><option value="sal">Highest salary</option></select>'
              '<button class="btn ghost sm" id="save-search" type="button">Save this search</button></div></div>'
              '<ul class="jobs" id="results"></ul><p><button class="btn" id="more" type="button" hidden>Show more</button></p></div>'
              '<aside class="pane" id="pane" aria-label="Job preview"><p class="pane-empty">Select a job to preview it here.</p></aside></div>'
              + alert_form("new jobs for this search", search=True)
              + '<datalist id="sugg">' + "".join(f'<option value="{e(x)}">' for x in dict.fromkeys(top_skills + [rlow(nm) for nm, s_, _ in ROLES if s_ in by_role] + [c for c, _ in comp_items[:200]])) + "</datalist>"
              + f'<noscript><p>Search needs JavaScript. Browse by category instead:</p><ul class="tiles">{cats}</ul></noscript><script src="{P}/app.js?v={V}" defer></script>')
    page("jobs/", f"Search {roles(n, 'Job')} | {SITE}",
         "Search jobs by title, skill or company. Filter by level, location, salary and remote, sort by pay, and save your searches.", search,
         head=f'<link rel="preload" href="{P}/data/head.json" as="fetch" crossorigin><link rel="preload" href="{P}/data/index.json" as="fetch" crossorigin>')

    # Long-tail landing pages: skill x remote, skill x place, category x place, place x remote, category x level
    by_tag = defaultdict(list)
    for j in active:
        for t in j["tags"]: by_tag[t].append(j)
    tslug = lambda t: TAG_SLUG.get(t, slugify(t))
    CMP = [t for t, _ in sorted(by_tag.items(), key=lambda kv: -len(kv[1]))[:14]]      # skills that get head-to-head comparison pages
    cmp_path = lambda a, b: "compare/{}-vs-{}/".format(*[tslug(x) for x in sorted((a, b), key=CMP.index)])
    cmp_links = lambda t: labrow("Compare with", [f'<a href="{P}/{cmp_path(t, o)}">{e(o)}</a>' for o in CMP if o != t], ("compare/", "Any two skills")) if t in CMP else ""
    LEVELS = [("Intern", "intern", "Internship"), ("Junior", "junior", "Junior"), ("Senior", "senior", "Senior"), ("Lead", "lead", "Lead and above")]
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
        add(f"locations/{slug}/remote/", f"Remote jobs in {name}", [j for j in pj if j["remote"]], (("Locations", "locations/"), (short, f"locations/{slug}/")),
            f"loc={slug}&remote=1", "remote ", f" in {e(name)}", [("place:" + slug, "Remote"), ("remote", f"Remote in {short}")])
        for cs, cname in CAT.items():
            if cs == OTHER[0]: continue
            add(f"locations/{slug}/{cs}/", f"{cname} jobs in {name}", [j for j in pj if j["cat"] == cs], (("Locations", "locations/"), (short, f"locations/{slug}/")),
                f"loc={slug}&cat={cs}", f"{e(cname)} ", f" in {e(name)}", [("cat:" + cs, f"{cname} in {short}"), ("place:" + slug, cname)])
    HUB["roles"] = {slug: (nm, {j["id"] for j in rj_}) for slug, (nm, rj_) in by_role.items()}
    def role_rows(js, k_min=5):
        """[(count, role slug, role name, median advertised pay or 0, the jobs)] for the kinds of work inside a set of jobs, largest first."""
        ids_ = {j["id"] for j in js}
        out_ = []
        for s_, (nm_, rj_) in by_role.items():
            if s_ in ("analyst", "coordinator", "director", "executive", "growth", "intern", "staff-engineer", "founding-team", "bilingual", "government", "energy", "payments", "consulting", "operators"): continue
            hit_ = [j for j in rj_ if j["id"] in ids_]
            if len(hit_) >= k_min:
                pay_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in hit_ if j["usd"]]
                out_.append((len(hit_), s_, nm_, median(pay_) if len(pay_) >= 5 else 0, hit_))
        out_.sort(key=lambda r_: -r_[0])
        return out_
    COMBO_QA, COMBO_AFTER, COMBO_TITLE = {}, {}, {}
    HUB["week"], HUB["live"] = (datetime.date.today() - datetime.timedelta(days=7)).isoformat(), {slug for _, slug, _ in places}
    for slug_r, (rname, rj) in by_role.items():
        trail_r, low, base_r = (("Categories", "categories/"), (rname, f"roles/{slug_r}/")), rlow(rname), slug_r in ROLE_BASE
        many = ROLE_PLURAL.get(rname, low + "s")
        rem_, ent_ = [j for j in rj if j["remote"]], [j for j in rj if j["entry"]]
        if base_r or len(rem_) >= 20: add(f"roles/{slug_r}/remote/", f"Remote {low} jobs", rem_, trail_r, f"remote=1&q={quote(rname)}", "remote ", f" for {e(many)}", [("role:" + slug_r, "Remote")])
        if base_r or len(ent_) >= 20: add(f"roles/{slug_r}/entry-level/", f"Entry-level {low} jobs", ent_, trail_r, f"entry=1&q={quote(rname)}", "entry-level ", f" for {e(many)}", [("role:" + slug_r, "Entry-level")])
        for name, slug, _ in big_places:          # every big place, not only the first six (Wellfound's role x city pages); 25 jobs or more
            here_ = [j for j in rj if slug in j["places"]]
            if base_r or len(here_) >= 25:
                add(f"roles/{slug_r}/{slug}/", f"{rname} jobs in {name}", here_, trail_r, f"loc={slug}&q={quote(rname)}", "", f" for {e(many)} in {e(name)}",
                    [("role:" + slug_r, name.removeprefix("the ")), ("place:" + slug, rname)])
    cut3 = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()        # the last 3 days: today and the two before (the home page counts the same)
    for t, js in by_tag.items():
        add(f"skills/{tslug(t)}/new/", f"{t} jobs posted in the last 3 days", [j for j in js if (j["posted"] or "") >= cut3], (("Skills", "skills/"), (t, f"skills/{tslug(t)}/")),
            f"age=3&skills={quote(t)}", "", f" mentioning {e(t)}, posted in the last three days", [("tag:" + t, "Last 3 days")])
    for slug_r, (rname, rj) in by_role.items():
        new_ = [j for j in rj if (j["posted"] or "") >= cut3]
        if slug_r in ROLE_BASE or len(new_) >= 20:
            add(f"roles/{slug_r}/new/", f"{rname} jobs posted in the last 3 days", new_, (("Categories", "categories/"), (rname, f"roles/{slug_r}/")),
                f"age=3&q={quote(rname)}", "", " posted in the last three days", [("role:" + slug_r, "Last 3 days")])
    add("remote/new/", "Remote jobs posted in the last 3 days", [j for j in remote if (j["posted"] or "") >= cut3], (("Remote", "remote/"),), "remote=1&age=3", "remote ", " posted in the last three days", [("remote", "Last 3 days")])
    add("remote/entry-level/", "Remote entry-level jobs", [j for j in remote if j["entry"]], (("Remote", "remote/"),), "remote=1&entry=1", "remote entry-level ", "", [("remote", "Entry-level")])
    for t, js in by_tag.items():
        add(f"skills/{tslug(t)}/entry-level/", f"Entry-level {t} jobs", [j for j in js if j["entry"]], (("Skills", "skills/"), (t, f"skills/{tslug(t)}/")),
            f"entry=1&skills={quote(t)}", "entry-level ", f" mentioning {e(t)}", [("tag:" + t, "Entry-level")])
    for perk_name, perk_slug in (("Visa sponsorship", "visa-sponsorship"), ("Relocation support", "relocation")):
        pk = [j for j in active if perk_name in j.get("perks", [])]
        add(f"perks/{perk_slug}/remote/", f"Remote jobs with {perk_name.lower()}", [j for j in pk if j["remote"]], (("Perks", "perks/"), (perk_name, f"perks/{perk_slug}/")),
            f"remote=1&perk={quote(perk_name)}", "remote ", f" that mention {perk_name.lower()}", [])
        for name, slug, _ in big_places:
            add(f"perks/{perk_slug}/{slug}/", f"Jobs with {perk_name.lower()} in {name}", [j for j in pk if slug in j["places"]], (("Perks", "perks/"), (perk_name, f"perks/{perk_slug}/")),
                f"loc={slug}&perk={quote(perk_name)}", "", f" in {e(name)} that mention {perk_name.lower()}", [("place:" + slug, perk_name)])
    pay_all_ = [j for j in active if j["usd"]]
    for k_ in (100, 150, 200, 250, 300):                       # "jobs that pay 100k": the low end of the advertised range is at least that much
        rich = [j for j in active if j["usd"] and j["usd"][0] >= k_ * 1000]
        if len(rich) >= 8:
            # what Google shows for "jobs that pay 100k" (15 Nov 2026): numbered lists of job titles with a figure each (Indeed, U.S. News),
            # by field, "without a degree"; People also ask: the easiest one, how rare $100K is, which careers, $100K per hour and month
            p_ = f"salary/{k_}k/"
            rr_ = role_rows(rich, 10)
            nd_ = [j for j in rich if "No degree required" in j.get("perks", [])]
            en_ = [j for j in rich if j.get("entry")]
            blk_ = ""
            if len(rr_) >= 3:
                shr_ = lambda s_: (lambda rp_: f"{100 * sum(1 for j in rp_ if j['usd'][0] >= k_ * 1000) / len(rp_):.0f}%" if len(rp_) >= 10 else "–")([j for j in by_role[s_][1] if j["usd"]])
                blk_ += section(f"{min(25, len(rr_))} job titles with the most openings at ${k_}K or more", f'<div class="tablewrap"><table><tr><th>#</th><th>Kind of work</th><th>Open at ${k_}K+</th><th>Median advertised pay</th><th>Share of its postings with pay that start at ${k_}K+</th></tr>'
                                + "".join(f'<tr><td>{i_ + 1}</td><td><a href="{P}/roles/{s_}/">{e(nm_)}</a></td><td>{c_:,}</td><td>{money(m_) if m_ else "–"}</td><td>{shr_(s_)}</td></tr>' for i_, (c_, s_, nm_, m_, _) in enumerate(rr_[:25]))
                                + f'</table></div><p class="note">Kinds of work matched by job title among the {len(rich):,} open postings whose advertised range starts at ${k_}K or more. Median of the midpoints of those ranges. A job can match two kinds of work.</p>')
            fl_ = Counter(j["cat"] for j in rich if j["cat"] != OTHER[0]).most_common(10)
            if len(fl_) >= 3:
                blk_ += section(f"Jobs that pay ${k_}K or more, by field", '<p class="rel">' + "".join(f'<a href="{P}/jobs/{c_}/">{e(CAT[c_])} · {n_:,}</a>' for c_, n_ in fl_) + "</p>")
            if len(nd_) >= 3:
                blk_ += section(f"Jobs that pay ${k_}K or more without a degree", f"<p>{len(nd_):,} of these postings say no degree is required. The newest:</p>" + job_links(nd_))
            if len(en_) >= 3:
                blk_ += section(f"Entry-level jobs that pay ${k_}K or more", f"<p>{len(en_):,} junior roles and internships start at ${k_}K or more. The newest:</p>" + job_links(en_)
                                + f'<p class="note">All of them: <a href="{P}/entry-level/">entry-level jobs</a>.</p>')
            COMBO_AFTER[p_] = blk_
            easy_ = []
            for c_, s_, nm_, _, h_ in rr_:
                y_ = sorted(j["years"] for j in h_ if j.get("years"))
                if len(y_) >= 10: easy_.append((y_[len(y_) // 2], -c_, nm_, len(y_)))
            qa_ = []
            if easy_:
                y0_, _, nm0_, ny_ = min(easy_)
                qa_.append((f"What's the easiest job that pays ${k_}K a year?", f"Judged by the experience asked: {rlow(nm0_)} roles. Of the {ny_:,} {rlow(nm0_)} postings here that start at ${k_}K or more and state experience, the median asks for {y0_} {'year' if y0_ == 1 else 'years'}. "
                            + f"{len(en_):,} junior roles and internships start at ${k_}K or more today" + (f", and {len(nd_):,} postings say no degree is required." if nd_ else ".")
                            + " How easy a job is also depends on the skills you already have, so compare the skills each posting names."))
            if pay_all_:
                qa_.append((f"How rare is a ${k_}K salary?", f"Among the {len(pay_all_):,} open jobs on {SITE} that state a yearly US-dollar range, {len(rich):,} ({100 * len(rich) / len(pay_all_):.0f}%) start at ${k_}K or more. "
                            f"Most employers here are technology companies, so the share across all US jobs is lower."))
            if len(rr_) >= 3:
                qa_.append((f"What careers make over ${k_},000 a year?", "By open postings today: " + ", ".join(f"{rlow(nm_)} ({c_:,}" + (f", median {money(m_)})" if m_ else ")") for c_, _, nm_, m_, _ in rr_[:6]) + ". The full ranking is in the table above."))
            qa_.append((f"How much is ${k_}K a year per hour and per month?", f"${k_},000 a year is ${k_ * 1000 / 2080:,.2f} an hour at 40 hours a week for 52 weeks, ${k_ * 1000 / 12:,.0f} a month and ${k_ * 1000 / 52:,.0f} a week, before tax."))
            COMBO_QA[p_] = qa_
            COMBO_TITLE[p_] = f"Jobs That Pay ${k_}K+ a Year ({len(rich):,} open) | {SITE}"
        add(f"salary/{k_}k/", f"Jobs that pay ${k_}K or more", rich, (("Salaries", "salaries/"),), f"sal={k_ * 1000}", "", f" whose advertised range starts at ${k_}K or more", [("pay", f"${k_}K+")])
        add(f"salary/{k_}k/remote/", f"Remote jobs that pay ${k_}K or more", [j for j in rich if j["remote"]], (("Salaries", "salaries/"), (f"${k_}K+", f"salary/{k_}k/")),
            f"sal={k_ * 1000}&remote=1", "remote ", f" whose advertised range starts at ${k_}K or more", [("pay", f"Remote ${k_}K+"), ("remote", f"${k_}K+")])
    for cs, cname in CAT.items():
        if cs == OTHER[0]: continue
        for lv, ls, ll in LEVELS:
            add(f"jobs/{cs}/{ls}/", f"{ll} {cname} jobs", [j for j in by_cat[cs] if j["level"] == lv], (("All jobs", "jobs/"), (cname, f"jobs/{cs}/")),
                f"cat={cs}&lvl={lv}", f"{e(ll)} {e(cname)} ", "", [("cat:" + cs, ll)])
    for path, h1, js, trail, qs, pre, post in combos:
        # these lists had the list and nothing else (SERP_WORK rows 10, 11, 13, 14, 17: "only 1 H2"); the views the big pages have
        seg_ = path.strip("/").split("/")
        lab_ = h1[0].lower() + h1[1:] if h1.split()[0] in ("Remote", "Senior", "Junior", "Internship", "Lead", "Jobs", "Entry-level") else h1
        if seg_[0] == "roles" and seg_[1] in by_role: lab_ = rlow(by_role[seg_[1]][0]) + h1[len(by_role[seg_[1]][0]):]
        lab_r = ("roles" + lab_[4:]) if lab_.startswith("jobs ") else lab_.replace(" jobs", " roles", 1)
        skip_ = ",".join(x for x, ok in (("places", (seg_[0] == "locations" and len(seg_) >= 3) or (seg_[0] == "perks" and len(seg_) == 3 and seg_[2] != "remote") or seg_[:2] == ["crypto", "in"]),
                                         ("roles", seg_[0] == "roles" or (seg_[0] == "salary" and len(seg_) == 2))) if ok)
        tag_ = next((t for t in by_tag if tslug(t) == seg_[-1]), "") if "skills" in seg_[:-1] else (next((t for t in by_tag if tslug(t) == seg_[1]), "") if seg_[0] == "skills" else "")
        gl_, tl_ = hub_sections(lab_r, js, skip_, min_k=20, drop_tag=tag_)
        listing(path, h1, COMBO_TITLE.get(path) or f"{h1} ({len(js):,} open) | {SITE}", f"{roles(len(js), 'open role')}: {h1} at companies. Updated hourly.",
                js, intro_for(js, pre, post), trail=trail, per=50, max_pages=3, more=qs, faq=lab_, extra=gl_, hub=tl_, after=COMBO_AFTER.get(path, ""), faq_extra=COMBO_QA.get(path, ()))

    # Listings
    for s, name in CAT.items():
        js = by_cat[s]
        if not js: continue
        mids_c = sorted((lo + hi) / 2 for j in js if j["usd"] for lo, hi in [j["usd"]])
        pay_c = f", {money(mids_c[len(mids_c) // 4])}–{money(mids_c[3 * len(mids_c) // 4])}" if len(mids_c) >= 15 else ""     # the pay range in the title, as the top results show it
        listing(f"jobs/{s}/", f"{name} jobs", f"{name} Jobs ({len(js):,} open{pay_c}) | {SITE}",
                f"{roles(len(js), name + ' job')} at companies. Remote and on-site roles, updated hourly.",
                js, (f"<strong>{e(name)}</strong>: {e(skills_info.CATEGORIES[s])}. " if s in skills_info.CATEGORIES else "") + intro_for(js, f"{e(name)} ", hub=True), trail=(("All jobs", "jobs/"),), feed=True, extra=sponsor_line("category:" + s) + hub_stats(js) + rel(REL["cat:" + s], ("categories/", "All categories")) + hub_sections(f"{name} roles", js)[0], faq=f"{name} jobs",
                hub=hub_sections(f"{name} roles", js)[1], accent=CAT_ACCENT.get(s), list_title=f"Newest {name} jobs", after=alert_form(f"new {name} jobs", cat=s))
        rj = [j for j in js if j["remote"]]
        if len(rj) >= 5:
            listing(f"remote/{s}/", f"Remote {name} jobs", f"Remote {name} Jobs ({len(rj):,} open) | {SITE}",
                    f"{roles(len(rj), 'remote ' + name + ' job')} at companies. Work from anywhere, updated hourly.",
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
    rr_rm = role_rows(remote, 30)
    best_rm = sorted((r_ for r_ in rr_rm if r_[3]), key=lambda r_: -r_[3])[:5]
    n104_ = sum(1 for j in remote if j["usd"] and j["usd"][0] >= 104000)
    n130_ = sum(1 for j in remote if j["usd"] and j["usd"][0] >= 130000)
    cats104_ = [CAT[c_].lower() for c_, _ in Counter(j["cat"] for j in remote if j["usd"] and j["usd"][0] >= 104000 and j["cat"] != OTHER[0]).most_common(3)]
    rm_qa = []
    if best_rm:
        rm_qa.append(("What is the best remote job right now?", "By advertised pay, the remote kinds of work with the highest median today: " + ", ".join(f"{rlow(nm_)} ({money(m_)}, {c_:,} open)" for c_, _, nm_, m_, _ in best_rm)
                      + ". By number of openings: " + ", ".join(f"{rlow(nm_)} ({c_:,})" for c_, _, nm_, _, _ in rr_rm[:3]) + ". The best one is the one your skills already fit, so compare the skills each posting names."))
    rm_qa += [("How can I make $2,000 a week working from home?", f"$2,000 a week is $104,000 a year over 52 weeks. {n104_:,} open remote jobs state a range that starts there or higher"
               + (f", most in {', '.join(cats104_)}." if cats104_ else ".") + " The remote lists of jobs that pay $100K and $150K or more are linked above."),
              ("Can I earn $500 a day working from home?", f"$500 a day over about 260 working days is $130,000 a year. {n130_:,} open remote jobs state a range that starts at that or more."),
              ("Which remote jobs need no experience?", f"{sum(1 for j in remote if j['entry']):,} remote roles are junior roles or internships; the remote entry-level list has them all. Remote roles for beginners are fewer and draw many applicants, so apply early.")]
    listing("remote/", "Remote jobs", f"Remote Jobs: {len(remote):,} Hiring Now, Updated Hourly | {SITE}",
            f"{roles(len(remote), 'remote job')} at companies: engineering, marketing, support, compliance and more.",
            remote, intro_for(remote, "remote "), extra=f'<ul class="tiles">{rcats}</ul>{rel(REL["remote"])}{remote_more}<div class="sec"><div class="sec-head"><h2>All remote jobs</h2></div></div>', feed=True, faq="remote jobs", faq_extra=rm_qa)
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
        # By blockchain ("ethereum jobs", "solana jobs": Cryptocurrency Jobs and Web3.career have a page per chain). A posting counts when
        # its own text names the chain; the patterns avoid ordinary words ("optimism") and other products ("Azure Cosmos DB").
        CHAINS = [("Ethereum", "ethereum", r"\bethereum\b|\bEVM\b|\bsolidity\b", "the largest smart-contract blockchain; its contracts are written in Solidity and run on the EVM"),
                  ("Bitcoin", "bitcoin", r"\bbitcoin\b|\blightning network\b", "the first and largest cryptocurrency network"),
                  ("Solana", "solana", r"\bsolana\b", "a fast, low-fee blockchain whose programs are mostly written in Rust"),
                  ("Arbitrum", "arbitrum", r"\barbitrum\b", "a layer-2 network that runs Ethereum contracts more cheaply"),
                  ("Optimism", "optimism", r"\bOP (?:Stack|Mainnet)\b|\bOptimism (?:Collective|Foundation|network)\b|\bSuperchain\b", "a layer-2 network built on the OP Stack, shared by the Superchain"),
                  ("Polygon", "polygon", r"\bpolygon (?:pos|zkevm|labs|network|chain)\b|\bpolygon\b(?= .{0,40}(?:blockchain|chain|layer))", "a family of networks that scale Ethereum"),
                  ("Base", "base", r"\bBase (?:chain|network|L2|mainnet)\b", "Coinbase's layer-2 network on the OP Stack"),
                  ("Cosmos", "cosmos", r"\bcosmos (?:sdk|hub|ecosystem|network)\b|\bIBC\b|\bcometbft\b|\btendermint\b", "a network of blockchains built with the Cosmos SDK and linked by IBC"),
                  ("Polkadot", "polkadot", r"\bpolkadot\b|\bsubstrate framework\b", "a network of chains built with the Substrate framework"),
                  ("Avalanche", "avalanche", r"\bavalanche (?:network|c-chain|subnet|blockchain)\b|\bAVAX\b", "a smart-contract platform with its own subnets"),
                  ("Aptos", "aptos", r"\baptos\b", "a blockchain whose contracts are written in Move"),
                  ("Sui", "sui", r"\bSui (?:network|blockchain|ecosystem|foundation)\b|\bon Sui\b", "a blockchain whose contracts are written in Move"),
                  ("XRP Ledger", "xrp-ledger", r"\bXRP\b|\bXRPL\b", "the open ledger behind the XRP currency"),
                  ("Cardano", "cardano", r"\bcardano\b", "a proof-of-stake blockchain with contracts in Plutus"),
                  ("TON", "ton", r"\bTON (?:blockchain|network|ecosystem|foundation)\b|\bThe Open Network\b", "the blockchain built around Telegram"),
                  ("Starknet", "starknet", r"\bstarknet\b", "a layer-2 network whose contracts are written in Cairo")]
        cchains = []
        ctext = {j["id"]: " ".join((j["title"], j.get("excerpt") or "", j.get("desc") or "")) for j in crypto}
        for nm_c, sl_c, rx_c, what_c in CHAINS:
            rx_ = re.compile(rx_c, re.I if nm_c not in ("Base", "XRP Ledger", "Sui", "TON", "Optimism") else 0)
            cadd(cchains, f"crypto/chains/{sl_c}/", f"{nm_c} jobs", [j for j in crypto if rx_.search(ctext[j["id"]])],
                 "{n} at crypto and web3 companies whose postings name " + nm_c + ", " + what_c.replace("{", "").replace("}", "") + ".", "", f" that name {e(nm_c)}", least=10, label=nm_c)
        cchains.sort(key=lambda x: -x[2])
        croles.sort(key=lambda x: -x[2]); cplaces.sort(key=lambda x: -x[2])
        cdir = lambda title, rows_: (f'<div class="dirb"><h2><span>{e(title)}</span><span>{len(rows_)}</span></h2><ul>'
                                     + "".join(f'<li><a href="{P}/{u}">{path_fl(u)}{e(nm)}</a><span>{k:,} jobs</span></li>' for u, nm, k in rows_) + "</ul></div>") if rows_ else ""
        ccats = "".join(tile(f"crypto/{s}/", CAT[s], c) for s in CAT if (c := sum(1 for j in crypto if j["cat"] == s)) >= 5)
        chire = "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in crypto).most_common(12))
        eng_pc = round(100 * sum(1 for j in crypto if j["cat"] == "engineering") / len(crypto))
        new7_c = sum(1 for j in crypto if (j["posted"] or "") >= (datetime.date.today() - datetime.timedelta(days=7)).isoformat())
        tok_rx = re.compile(r"paid in (?:crypto|usdc|usdt|stablecoins?|tokens?|btc|eth)|salary in (?:crypto|usdc|usdt|tokens?)|token (?:grants?|allocation|options)|(?:crypto|usdc) (?:salary|payroll)", re.I)
        n_tok = sum(1 for j in crypto if tok_rx.search(" ".join((j.get("salary") or "", j.get("excerpt") or "", j.get("desc") or ""))))
        crypto_qa = [("Are there jobs that pay in crypto?", f"Some: {n_tok:,} of the {len(crypto):,} open crypto jobs here {'mentions' if n_tok == 1 else 'mention'} pay in crypto, stablecoins or token grants in the posting. "
                      "Most pay a normal salary; tokens, when offered, usually come on top, like equity."),
                     ("How do I get a crypto job with no experience?", f"{sum(1 for j in crypto if j['entry']):,} open crypto roles are junior roles or internships, and non-engineering work (support, compliance, marketing, operations) "
                      "is a common way in. Show you know the product: use the exchange or wallet, read the docs, and say so in your letter."),
                     ("Are crypto job offers safe?", "Fake recruiters are common in crypto: a real employer never asks you to pay, to install a wallet or a program for an interview, or to move to a chat app before a proper interview. "
                      "Every job here links to the employer’s own careers page, so you apply where the company itself takes applications.")]
        listing("crypto/", "Crypto jobs", f"Crypto Jobs: {len(crypto):,} Web3 & Blockchain Roles, {new7_c:,} New This Week | {SITE}",
                f"{roles(len(crypto), 'open job')} at crypto, web3 and blockchain companies: exchanges, wallets, infrastructure and DeFi. Remote and on-site, with pay where the employer states it. Updated hourly.",
                crypto, intro_for(crypto, "", " at crypto, web3 and blockchain companies"),
                extra=mini_pics(crypto) + f'<ul class="tiles">{ccats}</ul>'
                + section("Who is hiring in crypto", f'<ul class="tiles">{chire}</ul>', ("companies/", "All companies"))
                + '<div class="dir">' + cdir("Kinds of crypto jobs", ckinds) + cdir("By profession", croles) + cdir("By place", cplaces) + cdir("By blockchain", cchains) + "</div>"
                + '<div class="sec"><div class="sec-head"><h2>All crypto jobs</h2></div></div>', feed=True, faq="crypto jobs", faq_extra=crypto_qa,
                faq_first=("What counts as a crypto job here?", f"A job at a company whose business is crypto, web3 or blockchain: exchanges, wallets, custody, blockchain infrastructure, DeFi and analytics. "
                           f"Of the {len(crypto):,} open today, {eng_pc}% are engineering jobs; the rest are in compliance, marketing, support, finance, design and other fields, so the list is not only for programmers."))
        for s, name in CAT.items():
            cj = [j for j in crypto if j["cat"] == s]
            if len(cj) >= 5:
                listing(f"crypto/{s}/", f"{name} jobs in crypto & web3", f"{name} Jobs in Crypto & Web3 ({len(cj):,} open) | {SITE}",
                        f"{roles(len(cj), name + ' job')} at crypto and web3 companies. Remote and on-site roles, updated hourly.",
                        cj, intro_for(cj, f"{e(name)} ", " at crypto and web3 companies"), trail=ctrail)
    sal = [j for j in active if j["salary"]]
    listing("with-salary/", "Jobs with salary listed", f"Jobs With Salary Listed ({len(sal):,}) | {SITE}",
            "Jobs where the employer publishes the salary range up front.", sal, intro_for(sal, "", " with a published salary range"))
    jr = [j for j in active if j["entry"]]
    intern_e = [j for j in jr if j["level"] == "Intern"]
    gl_e, tl_e = hub_sections("entry-level roles", jr, min_k=20)
    rr_e = role_rows(jr, 10)
    best_e = sorted((r_ for r_ in rr_e if r_[3]), key=lambda r_: -r_[3])[:10]
    nd_e = [j for j in jr if "No degree required" in j.get("perks", [])]
    mids_e = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in jr if j["usd"])
    ent_top = section("Internships or a first full-time job", f'<p>{len(intern_e):,} of the {len(jr):,} are internships and {len(jr) - len(intern_e):,} are junior full-time or part-time roles. '
                      f'<a href="{P}/internships/">All internships</a> · <a href="{P}/remote/entry-level/">Remote entry-level jobs</a> · <a href="{P}/categories/internships-entry-level/">Kinds of work open to beginners</a></p>')
    ent_after = ""
    combo_paths = {c_[0] for c_ in combos}
    if len(best_e) >= 3:
        ent_after += section("Entry-level jobs that pay the most", '<div class="tablewrap"><table><tr><th>Kind of work</th><th>Open entry-level roles</th><th>Median advertised pay</th></tr>'
                             + "".join(f'<tr><td><a href="{P}/roles/{s_}/entry-level/">{e(nm_)}</a></td><td>{c_:,}</td><td>{money(m_)}</td></tr>' if f"roles/{s_}/entry-level/" in combo_paths else
                                       f'<tr><td><a href="{P}/roles/{s_}/">{e(nm_)}</a></td><td>{c_:,}</td><td>{money(m_)}</td></tr>' for c_, s_, nm_, m_, _ in best_e)
                             + '</table></div><p class="note">Median of the midpoints of advertised yearly US-dollar ranges; a kind of work needs 5 entry-level postings with pay.</p>')
    if len(nd_e) >= 3:
        ent_after += section("Entry-level jobs with no degree required", f"<p>{len(nd_e):,} of these postings say no degree is required. The newest:</p>" + job_links(nd_e))
    ent_qa = [("What counts as an entry-level job here?", "A job whose title marks it as an internship or a junior role: intern, junior, graduate, new grad and similar words. Many jobs with no level in the title are open to beginners too "
               "(associate and trainee roles, for example), which is why the kinds of work open to beginners, linked above, count more jobs.")]
    if rr_e:
        ent_qa.append(("What's the easiest entry-level job to get?", "By openings today: " + ", ".join(f"{rlow(nm_)} ({c_:,})" for c_, _, nm_, _, _ in rr_e[:4])
                       + ". More openings means more chances, not fewer applicants; matching the skills a posting names matters most."))
    if len(mids_e) >= 15:
        ent_qa.append(("How much do entry-level jobs pay an hour?", f"The median advertised yearly range midpoint is {money(median(mids_e))}, about ${median(mids_e) / 2080:,.0f} an hour at 40 hours a week. "
                       "Internships are often paid by the hour or month; the hourly pay pages list jobs by the rate they state."))
    listing("entry-level/", "Entry-level jobs & internships", f"Entry-Level Jobs & Internships: {len(jr):,} Open, Updated Hourly | {SITE}",
            "Internships and junior roles at companies: a way into the industry without years of experience.", jr,
            intro_for(jr, "entry-level "), extra=ent_top + gl_e, hub=tl_e, after=ent_after, faq="entry-level jobs", faq_extra=ent_qa)
    def skill_more(t, js):
        """"What jobs can I get with SQL?" (People also ask): the kinds of work that ask for it, with counts and pay; and the skills asked with it."""
        ids_ = {j["id"] for j in js}
        rows_ = []
        for s_, (nm_, rj_) in by_role.items():
            if s_ in BROAD: continue
            hit_ = [j for j in rj_ if j["id"] in ids_]
            if len(hit_) >= 5:
                pay_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in hit_ if j["usd"])
                rows_.append((len(hit_), s_, nm_, median(pay_) if len(pay_) >= 5 else 0))
        rows_.sort(reverse=True)
        out_ = ""
        if len(rows_) >= 3:
            out_ += section(f"Jobs you can get with {t}", '<div class="tablewrap"><table><tr><th>Kind of work</th><th>Open jobs asking for ' + e(t) + '</th><th>Median advertised pay</th></tr>'
                            + "".join(f'<tr><td><a href="{P}/roles/{s_}/">{e(nm_)}</a></td><td>{k_:,}</td><td>{money(m_) if m_ else "–"}</td></tr>' for k_, s_, nm_, m_ in rows_[:8]) + "</table></div>")
        co_ = Counter(x for j in js for x in j["tags"] if x != t).most_common(8)
        if len(co_) >= 4:
            out_ += section(f"Skills asked together with {t}", "<p>" + ", ".join(f'<a href="{P}/skills/{tslug(x)}/">{e(x)}</a> ({100 * k_ / len(js):.0f}%)' for x, k_ in co_)
                            + f" of the {len(js):,} open postings that name {e(t)}.</p>")
        qk_, qn_ = QUIZ_OF.get(t, (None, 0))      # "sql jobs": people also search "SQL certification", "SQL test"
        if qk_:
            out_ += section(f"Test your {t}", f'<p>A free <a href="{P}/skill-tests/{qk_}/">{e(t)} test</a> of {qn_} questions, beginner to advanced, scored by topic in your browser. '
                            f'Then the <a href="{P}/interview-questions/">interview questions</a> for the job you want.</p>')
        return out_
    for t, js in by_tag.items():
        listing(f"skills/{tslug(t)}/", f"{t} jobs", f"{t} Jobs ({len(js):,} open) | {SITE}",
                f"{roles(len(js))} at companies that ask for {t}.", js,
                (f"<strong>{e(t)}</strong>: {e(skills_info.INFO[t][1])}. " if t in skills_info.INFO else "") + intro_for(js, "", f" mentioning {e(t)}", hub=True),
                trail=(("All jobs", "jobs/"),), feed=True, extra=sponsor_line("skill:" + tslug(t)) + hub_stats(js) + rel(REL["tag:" + t], ("skills/", "All skills")) + cmp_links(t) + hub_sections(f"{t} roles", js, "skills")[0], hub=hub_sections(f"{t} roles", js, "skills")[1], list_title=f"Newest {t} jobs",
                faq=f"{t} jobs", faq_first=((f"What is {t}?", f"{skills_info.plain(t)} {len(js):,} open roles on {SITE} ask for it as of {fdate(TODAY)}.") if t in skills_info.INFO else None),
                after=skill_more(t, js) + section(f"Companies hiring for {t}", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in Counter(j["company"] for j in js).most_common(12)) + "</ul>",
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
        mids_r = sorted((lo + hi) / 2 for j in rj if j["usd"] for lo, hi in [j["usd"]])
        pay_r = f", {money(mids_r[len(mids_r) // 4])}–{money(mids_r[3 * len(mids_r) // 4])}" if len(mids_r) >= 15 else ""     # the pay range in the title, as the top results show it
        listing(f"roles/{slug_r}/", f"{rname} jobs", f"{tcase(rname)} Jobs ({len(rj):,} open{pay_r}) | {SITE}",
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
    # The tech hub (/tech/): since 15 Nov 2026 the site covers every profession, so tech gets a page of its own, as crypto has: its
    # categories, its newest jobs, the tech-skill rankings and comparisons.
    tech_fams = [f for f in fam_rows if f[0] in TECH_FAMS]
    tech_seen, tech_js = set(), []
    for f in tech_fams:
        for j in f[4]:
            if j["id"] not in tech_seen: tech_seen.add(j["id"]); tech_js.append(j)
    if tech_js:
        tech_links = labrow("Tech rankings and tools", [f'<a href="{P}/insights/highest-paying-tech-skills/">Highest-paying tech skills</a>',
                                                        f'<a href="{P}/insights/most-in-demand-tech-skills/">Most in-demand tech skills</a>',
                                                        f'<a href="{P}/compare/">Compare two skills</a>', f'<a href="{P}/skills/">Every skill explained</a>',
                                                        f'<a href="{P}/salaries/explorer/">Salary explorer</a>'])
        listing("tech/", "Tech jobs", f"Tech Jobs ({len(tech_js):,} open) | {SITE}",
                f"{len(tech_js):,} open tech jobs in software, AI, data, cloud, security, product and hardware, read from employers’ own careers pages. Pay, skills and rankings.",
                tech_js, f"Software, AI, data, cloud, security, product and hardware: {len(tech_js):,} open jobs in {len(tech_fams)} tech categories, "
                f"{100 * sum(1 for j in tech_js if j['remote']) // max(1, len(tech_js))}% of them remote. The rest of the site covers every other kind of work too.",
                per=50, max_pages=3, more=False, feed=True,
                extra=hub_stats(tech_js) + mini_pics(tech_js) + tech_links + section("Tech categories", '<div class="dir">' + "".join(dir_block(*f, top=6, tag="h3") for f in tech_fams) + "</div>"),
                list_title="Newest tech jobs", faq="tech jobs")
    dir_html = '<div class="dir" id="dir">' + "".join(dir_block(*f) for f in fam_show) + dir_tail + "</div>"
    dir_filter = ('<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, lawyer or designer" aria-label="Find a category"></p>'
                  '<p class="lead" id="dirnone" hidden>No category with these words. Try the <a href="' + P + '/jobs/">job search</a>: it looks through every title.</p>')
    dir_qa = [("How are jobs sorted into categories?", "By the job title. Each kind of work has a list of the titles employers use for it, and a posting whose title matches is listed there. A posting can sit in two categories when its title belongs to both, for example a staff backend engineer."),
              ("Are these only technology jobs?", f"No. The employers are mostly technology, finance, health, space and consumer companies, and they hire for every kind of work: {len(fam_rows)} fields here, from software and data to sales, accounting, law, nursing, warehouses and shops."),
              ("Why is a category missing?", "A kind of work gets a page when at least 20 open jobs match it. Smaller ones are still found through the search."),
              ("How often are the lists updated?", "Every time the employers’ careers pages are read again, which is every hour. A job that the employer has closed leaves the lists and moves to the archive.")]
    fam_tab = []
    for fs, fn, fd, live, js_ in fam_rows:
        ms_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in js_ if j["usd"])
        fam_tab.append((fs, fn, [nm for _, nm, _ in sorted(live, key=lambda x: -x[2])[:4]], len(js_), median(ms_) if len(ms_) >= 20 else None))
    fam_tab.sort(key=lambda r_: -r_[3])
    top_titles = sorted(((len(js_), nm) for s_, (nm, js_) in by_role.items() if s_ not in BROAD), reverse=True)[:10]
    dir_qa = [("What are the main job categories?", f"On this site, {len(fam_rows)} fields: " + ", ".join(fn for _, fn, _, _, _ in fam_tab) + ". The table above gives example job titles, open jobs and the median advertised pay for each.")] + dir_qa
    dir_qa.insert(1, ("What are 10 common job titles?", "By open postings today: " + ", ".join(f"{nm} ({k:,})" for k, nm in top_titles) + "."))
    dir_qa.insert(2, ("What are the different types of jobs?", f"By field (the {len(fam_rows)} categories here), by level (intern, junior, mid-level, senior, lead, manager), by contract (full-time, part-time, contract, internship) "
                      "and by place (on site, hybrid, remote). Every one of these has its own list on this site."))
    fam_tab_html = section("Job categories with example titles and pay", '<div class="tablewrap"><table><tr><th>Category</th><th>Example job titles</th><th>Open jobs</th><th>Median advertised pay</th></tr>'
                           + "".join(f'<tr><td><a href="{P}/categories/{fs}/">{e(fn)}</a></td><td>{e(", ".join(ex_))}</td><td>{k_:,}</td><td>{money(m_) if m_ else "–"}</td></tr>' for fs, fn, ex_, k_, m_ in fam_tab)
                           + '</table></div><p class="note">Median of the midpoints of yearly US-dollar ranges stated in today’s postings; a field needs 20 of them.</p>')
    dir_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in dir_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    dir_faq = section("Questions about the categories", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in dir_qa) + "</dl>")
    page("categories/", f"List of Job Categories: {len(fam_rows)} Fields, {len(by_role)} Job Titles | {SITE}",
         f"Browse {n:,} open jobs by category: {len(fam_rows)} fields and {len(by_role)} kinds of work, from software and data to sales, finance, law, healthcare and the factory floor. Each has its own page.",
         crumbs(("Categories", "")) + '<h1>Browse all job <span class="hl">categories</span></h1>'
         f'<p class="lead">{n:,} open jobs, sorted into {len(fam_rows)} fields and {len(by_role)} kinds of work. Pick a field to read what the work is and see who is hiring, or go straight to a kind of work. '
         'The number next to each name is how many jobs are open today.</p>' + dir_filter + dir_html + fam_tab_html + dir_faq, head=dir_ld)
    page("roles/", f"List of Jobs A to Z: {len(by_role)} Job Titles with Open Roles | {SITE}", f"Every kind of work with open jobs, A to Z: {len(by_role)} job titles, each with remote, entry-level, city and salary pages.",
         crumbs(("Categories", "categories/"), ("All roles", "")) + '<h1>All roles, A to Z</h1><p class="lead">Job titles differ from company to company, so each role here gathers the variants employers use. '
         f'The same roles grouped by field are on the <a href="{P}/categories/">categories page</a>.</p>'
         '<ul class="tiles">' + "".join(tile(f"roles/{s_}/", nm, len(js_)) for s_, (nm, js_) in sorted(by_role.items(), key=lambda kv: kv[1][0].lower())) + "</ul>")
    for fs, fn, fd, live, js_ in fam_rows:
        low_f, names_ = rlow(fn), [nm for _, nm, _ in live]
        role_list = '<ul class="gloss">' + "".join(f'<li><a href="{P}/roles/{s_}/"><b><u>{e(nm)}</u></b><span class="c">{c:,} jobs</span><span class="d">{e(roles_info.what(s_))}</span></a></li>' for s_, nm, c in live) + "</ul>"
        rank_ = (labrow("Ranking", [f'<a href="{P}/insights/companies-hiring-{fs}/">Companies hiring for {e(low_f)} jobs, with remote roles and pay</a>'], ("insights/", "All rankings"))
                 if len({j["company"] for j in js_}) >= 8 else "")
        others = rank_ + labrow("Other categories", [f'<a href="{P}/categories/{o}/">{e(on)}</a>' for o, on, _, _, _ in fam_rows if o != fs], ("categories/", "All categories"))
        secs = hub_sections(f"{low_f} roles", js_, "roles")       # a noun at the end: "Where software development roles are"
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
                hub=secs[1], after=others)
    # Companies hiring in each place (Wellfound's "startups hiring in <city>"): every employer with open jobs there, most jobs first.
    # Written for places with 20 employers or more; the place's own page links to it.
    co_in = {slug: Counter(j["company"] for j in js) for _, slug, js in places}
    co_in = {s_: c_ for s_, c_ in co_in.items() if len(c_) >= 20}
    rule_of = {sl_: r_ for _, sl_, r_ in PLACES}
    for name, slug, js in places:
        short = name.removeprefix("the ")
        r_p = rule_of.get(slug)
        us_p = r_p == "US" or (isinstance(r_p, tuple) and r_p[1] == "US")
        pl_qa = []
        mids_p = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in js if j["usd"])
        if us_p and len(mids_p) >= 30:
            b70 = sum(1 for x in mids_p if x < 70000)
            pl_qa.append((f"Is $70,000 a good salary in {short}?", f"{100 * b70 / len(mids_p):.0f}% of the {len(mids_p):,} open jobs in {name} here that state a yearly range advertise less than $70,000 at the midpoint; "
                          f"the median is {money(median(mids_p))}. Most employers on {SITE} are technology companies, so these figures run above the city’s overall pay, and rent decides how far $70,000 goes."))
        rr_p = role_rows(js, 10)
        if len(rr_p) >= 3:
            pl_qa.append((f"What jobs are in high demand in {short}?", "By open postings today: " + ", ".join(f"{rlow(nm_)} ({c_:,})" for c_, _, nm_, _, _ in rr_p[:6])
                          + f". {sum(1 for j in js if (j['posted'] or '') >= HUB['week']):,} jobs in {name} were posted in the last seven days."))
        co_link = (f'<p class="note"><a href="{P}/locations/{slug}/companies/">All {len(co_in[slug]):,} companies hiring in {e(short)}</a>, most open jobs first.</p>'
                   if slug in co_in else "")
        listing(f"locations/{slug}/", f"Jobs in {name}", f"Jobs in {name} ({len(js):,} open) | {SITE}",
                f"{roles(len(js), 'job')} in {name}. Startups and established companies hiring now.",
                js, intro_for(js, "", f" in {e(name)}", hub=True), trail=(("Locations", "locations/"),), extra=hub_stats(js) + co_link + rel(REL["place:" + slug], ("locations/", "All locations")) + hub_sections(f"roles in {name}", js, "places")[0], faq=f"jobs in {name}", faq_extra=pl_qa, feed=True,
                hub=hub_sections(f"roles in {name}", js, "places")[1], list_title=f"Newest jobs in {name}", after=alert_form(f"new jobs in {short}", loc=slug))
    week7 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    for name, slug, js in places:
        if slug not in co_in: continue
        short = name.removeprefix("the ")
        by_co = defaultdict(list)
        for j in js: by_co[j["company"]].append(j)
        cos_ = sorted(by_co, key=lambda c: (-len(by_co[c]), c.lower()))
        new_ = {c for c in cos_ if any((j["posted"] or "") >= week7 for j in by_co[c])}
        kinds = lambda cj: ", ".join(CAT[k] for k, _ in Counter(j["cat"] for j in cj if j["cat"] != OTHER[0]).most_common(2))
        top_ = ", ".join(f"{c} ({len(by_co[c]):,})" for c in cos_[:5])
        shown_ = cos_[:300]
        rows_ = "".join(f'<tr><td><a href="{P}/companies/{slugify(c)}/">{e(c)}</a></td><td>{len(by_co[c]):,}</td>'
                        f'<td>{sum(1 for j in by_co[c] if (j["posted"] or "") >= week7):,}</td><td>{e(kinds(by_co[c]))}</td></tr>' for c in shown_)
        qa_ = [(f"Which companies are hiring in {short}?", f"The most open jobs in {short} on {SITE} as of {fdate(TODAY)}: {top_}. {len(cos_):,} companies have at least one."),
               (f"How many companies are hiring in {short}?", f"{len(cos_):,} companies have open jobs in {short} as of {fdate(TODAY)}; {len(new_):,} of them posted at least one in the last seven days."),
               ("Where does this list come from?", f"From the employers’ own careers pages, read {EVERY}. A company leaves the list when its last open job in {short} closes.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>"
               + crumbs_ld([("Locations", "locations/"), (short, f"locations/{slug}/"), ("Companies hiring", "")]))
        t_ = f"Companies Hiring in {short}: {len(cos_):,} With Open Jobs ({MONTH_YEAR})"          # the month only where the title still fits
        page(f"locations/{slug}/companies/", t_ if len(t_) <= 65 else t_.rsplit(" (", 1)[0],
             f"{len(cos_):,} companies have open jobs in {name} as of {fdate(TODAY)}, {len(new_):,} of them posted in the last seven days. The most: {', '.join(cos_[:3])}.",
             crumbs(("Locations", "locations/"), (short, f"locations/{slug}/"), ("Companies hiring", "")) + f'<h1>{path_fl(f"locations/{slug}/")}Companies hiring in {e(name)}</h1>'
             f'<p class="lead">{len(cos_):,} employers have open jobs in {e(name)} on {fdate(TODAY)}, and {len(new_):,} of them posted one in the last seven days. '
             f'Most open jobs first; each name opens all of that company’s roles.</p>'
             + act_row(f"locations/{slug}/", f"See all {len(js):,} jobs in {short}")
             + '<div class="tablewrap"><table class="cotab"><tr><th>Company</th><th>Open jobs here</th><th>New in 7 days</th><th>Kinds of work</th></tr>' + rows_ + "</table></div>"
             + (f'<p class="note">The {len(shown_):,} with the most open jobs here; the other {len(cos_) - len(shown_):,} are on the <a href="{P}/companies/">companies page</a>.</p>' if len(cos_) > len(shown_) else "")
             + f'<p class="note">Counted on {fdate(TODAY)} from the employers’ own careers pages; recounted on every update.</p>'
             + section(f"Questions about companies in {short}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>"),
             head=ld_)
    rule_of = {slug: rule for _, slug, rule in PLACES}
    WORLD = (("North America", {"US", "CA"}), ("Europe", REGIONS["europe"][0]), ("Asia-Pacific", REGIONS["asia-pacific"][0]), ("Latin America", REGIONS["latin-america"][0]))
    def world(code): return next((nm for nm, codes in WORLD if code in codes), "Middle East and Africa")
    lrow = lambda name, slug, js: (f'<li data-n="{e(name.lower())}"><a href="{P}/locations/{slug}/">{pfl(slug)}{e(name.removeprefix("the "))}</a><span>{len(js):,} jobs'
                                   + (f' · {sum(j["remote"] for j in js):,} remote' if any(j["remote"] for j in js) else "") + "</span></li>")
    lgroups = defaultdict(list)
    for name, slug, js in places:
        r_ = rule_of.get(slug)
        lgroups[world(r_) if isinstance(r_, str) and r_ != "region" else "Parts of the world" if r_ == "region"
                else "US states and cities" if r_[1] == "US" else "Cities in other countries"].append((name, slug, js))
    lorder = [nm for nm, _ in WORLD] + ["Middle East and Africa", "US states and cities", "Cities in other countries", "Parts of the world"]
    ldir = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(g)}</span><span>{len(lgroups[g])}</span></h2><ul>' + "".join(lrow(*x) for x in sorted(lgroups[g], key=lambda x: -len(x[2]))) + "</ul></div>" for g in lorder if lgroups.get(g)) + "</div>"
    n_ctry = sum(len(lgroups[g]) for g in lorder[:5] if lgroups.get(g))
    ltop = "".join(tile(f"locations/{slug}/", name.removeprefix("the "), len(js)) for name, slug, js in sorted((x for g in lorder[:5] for x in lgroups.get(g, [])), key=lambda x: -len(x[2]))[:8])
    page("locations/", f"Jobs by Country: {n_ctry} Countries and {len(lgroups.get('US states and cities', [])) + len(lgroups.get('Cities in other countries', []))} Cities | {SITE}",
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
    co_lead = f"{len(companies):,} employers with open roles today. {names(top_open)} have the most." if len(top_open) > 1 else f"{len(companies):,} employers with open roles today."
    if top_new:
        co_lead += (f" {sum(1 for n in fresh_n.values() if n):,} of them posted new roles in the last 7 days, led by {names(top_new)}."
                    ' The <span class="up">+N</span> mark in the list is that weekly number.')
    day90 = (datetime.date.today() - datetime.timedelta(days=LONG_OPEN)).isoformat()
    def mk_counts():
        a_ = p_ = f_ = 0
        for c, js in comp_items:
            act_ = [j for j in js if j["active"]]
            if fresh_n[c] >= 3: a_ += 1
            if len(act_) >= 5:
                if sum(bool(j["salary"]) for j in act_) >= len(act_) / 2: p_ += 1
                if sum(1 for j in act_ if (j["posted"] or j["first_seen"])[:10] <= day90) < len(act_) / 4: f_ += 1
        return a_, p_, f_
    mk_a, mk_p, mk_f = mk_counts()
    mk_rows = [("Actively hiring", "Posted at least 3 roles in the last 7 days.", mk_a),
               ("States the pay", "At least half of its open roles state the pay (employers with 5 open roles or more).", mk_p),
               ("Few old postings", f"Fewer than a quarter of its open roles were posted {LONG_OPEN} days ago or more (employers with 5 open roles or more).", mk_f)]
    co_types = []
    co_act = {c: [j for j in js if j["active"]] for c, js in companies.items()}
    co_act = {c: v for c, v in co_act.items() if len(v) >= 10}
    def ctry_n(v): return len({cc for j in v for cc, _ in countries_of(j["location"] or "")})
    TYPES = [("remote-first", "Remote-first companies hiring now", "Remote-First Companies Hiring Now",
              "at least three quarters of their open roles can be done from home", lambda v: sum(1 for j in v if j["remote"]) / len(v) >= 0.75,
              lambda v: f'{100 * sum(1 for j in v if j["remote"]) / len(v):.0f}% remote', "remote"),
             ("hiring-worldwide", "Companies hiring in many countries", "Global Companies Hiring in 8+ Countries",
              "their open roles are spread over eight countries or more", lambda v: ctry_n(v) >= 8, lambda v: f"{ctry_n(v)} countries", "places"),
             ("ai-hiring", "Companies hiring most for AI work", "Companies Hiring for AI Roles Now",
              "at least half of their open roles ask for AI or machine-learning skills", lambda v: sum(1 for j in v if any(t in AI_TAGS for t in j["tags"])) / len(v) >= 0.5,
              lambda v: f'{100 * sum(1 for j in v if any(t in AI_TAGS for t in j["tags"])) / len(v):.0f}% AI roles', "ai"),
             ("beginner-friendly", "Companies hiring beginners", "Companies Hiring Entry-Level Now",
              "at least a quarter of their open roles are junior roles or internships", lambda v: sum(1 for j in v if j["entry"]) / len(v) >= 0.25,
              lambda v: f'{sum(1 for j in v if j["entry"]):,} for beginners', "entry"),
             ("pay-transparent", "Companies that state the pay", "Companies That Show Salary in Every Job",
              "at least four in five of their open roles state the pay", lambda v: sum(1 for j in v if j["salary"]) / len(v) >= 0.8,
              lambda v: f'{100 * sum(1 for j in v if j["salary"]) / len(v):.0f}% state pay', "pay")]
    for ts_, h1_, ttl_, rule_, ok_, metric_, _ in TYPES:
        hits = sorted(((c, v) for c, v in co_act.items() if ok_(v)), key=lambda kv: -len(kv[1]))
        if len(hits) < 5: continue
        n_jobs = sum(len(v) for _, v in hits)
        med_ = lambda v: (lambda m_: money(median(m_)) if len(m_) >= 5 else "–")([(j["usd"][0] + j["usd"][1]) / 2 for j in v if j["usd"]])
        rows_t = "".join(f'<tr><td>{i_ + 1}</td><td><a href="{P}/companies/{slugify(c)}/">{e(c)}</a></td><td>{len(v):,}</td><td>{e(metric_(v))}</td><td>{med_(v)}</td></tr>'
                         for i_, (c, v) in enumerate(hits[:200]))
        qa_t = [(f"Which {h1_[0].lower() + h1_[1:].replace(' hiring now', '').replace('Companies', 'companies')} have the most open jobs?",
                 "Right now: " + ", ".join(f"{c} ({len(v):,})" for c, v in hits[:5]) + f". {len(hits):,} companies with 10 or more open roles qualify today."),
                ("How is this list made?", f"From each company’s own open postings, read every hour: a company is listed when {rule_}, and it has at least 10 open roles. "
                 "Nothing here is a label bought or claimed; it changes as the postings change.")]
        ld_t = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_t]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page(f"companies/{ts_}/", f"{ttl_}: {len(hits):,} Employers ({datetime.date.fromisoformat(TODAY).strftime('%b %Y')}) | {SITE}",
             f"{len(hits):,} companies where {rule_}, with {n_jobs:,} open jobs between them, counted from their own careers pages and updated every hour.",
             crumbs(("Companies", "companies/"), (h1_, "")) + f'<h1>{e(h1_)}: <span class="hl">{len(hits):,} employers</span></h1>'
             f'<p class="lead">Companies where {e(rule_)}, counted today from their own careers pages: {n_jobs:,} open jobs between them. Largest first.</p>'
             + section(h1_, '<div class="tablewrap"><table><tr><th>#</th><th>Company</th><th>Open roles</th><th>Why it is here</th><th>Median advertised pay</th></tr>' + rows_t + "</table></div>")
             + section("Questions about this list", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_t) + "</dl>")
             + '<p class="note cmpl">Other lists: ' + " · ".join(f'<a href="{P}/companies/{o_[0]}/">{e(o_[1])}</a>' for o_ in TYPES if o_[0] != ts_) + "</p>", head=ld_t)
        co_types.append((ts_, h1_, len(hits)))
    CO_SHORT = {"remote-first": "Remote-first", "hiring-worldwide": "Hiring in 8+ countries", "ai-hiring": "Hiring for AI roles",
                "beginner-friendly": "Hiring beginners", "pay-transparent": "State the pay"}
    co_types_html = (section("Companies by type", '<ul class="tiles">' + "".join(tile(f"companies/{t_}/", CO_SHORT.get(t_, h_), k_) for t_, h_, k_ in co_types) + "</ul>"
                             '<p class="note">Counted from each company’s own open postings, so a company moves in and out of a list as it hires.</p>') if co_types else "")
    page("companies/", f"Companies Hiring Now ({MONTH_YEAR}): {len(companies):,} employers | {SITE}",
         "Companies with open roles: startups, scale-ups and public companies across software, AI, fintech and crypto.",
         crumbs(("Companies", "")) + f'<h1>Companies hiring now, {MONTH_YEAR}</h1><p class="lead">{co_lead}</p>{co_types_html}'
         '<input type="search" id="cfilter" placeholder="Filter companies by name" aria-label="Filter companies">'
         '<div class="tabs csort" id="csort" role="group" aria-label="Sort companies" hidden>'
         '<button class="tab" type="button" data-s="o" aria-pressed="true">Most open roles</button>'
         '<button class="tab" type="button" data-s="w" aria-pressed="false">Most new this week</button>'
         '<button class="tab" type="button" data-s="n" aria-pressed="false">A–Z</button></div>'
         + (section("Featured employers", spot_tiles(spot_cos)) if spot_cos else "") +
         labrow("Hiring in", [f'<a href="{P}/locations/{s_}/companies/">{e(nm_.removeprefix("the "))}</a>' for nm_, s_, _ in sorted(places, key=lambda x: -len(co_in.get(x[1], ()))) if s_ in co_in][:14])
         + f'<ul class="tiles" id="clist" style="margin-top:14px">{grid}</ul><p class="note" id="cnone" hidden>No company with that name.</p>'
         + section("What the marks on company pages mean", '<dl class="qa">' + "".join(f"<div><dt>✓ {e(nm)}</dt><dd>{e(rule)} Today: {k_:,} employers.</dd></div>" for nm, rule, k_ in mk_rows) + "</dl>"
                   '<p class="note">Counted on every update from the employer’s own open postings; a mark comes and goes with them. Nobody pays for a mark.</p>', sid="marks"))
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
        # Trust marks (Upwork shows them on clients): each says the rule and the number behind it, counted from the open postings
        tb_ = []
        if fresh_n.get(c, 0) >= 3: tb_.append(("Actively hiring", f"{fresh_n[c]:,} roles posted in the last 7 days"))
        if len(act) >= 5:
            pay_s = sum(bool(j["salary"]) for j in act)
            old5 = sum(1 for j in act if (j["posted"] or j["first_seen"])[:10] <= (datetime.date.today() - datetime.timedelta(days=LONG_OPEN)).isoformat())
            if pay_s >= len(act) / 2: tb_.append(("States the pay", f"{round(100 * pay_s / len(act))}% of its open roles state it"))
            if old5 < len(act) / 4: tb_.append(("Few old postings", f"{round(100 * old5 / len(act))}% open {LONG_OPEN} days or more"))
        TB[c] = tb_
        tbadges = ('<p class="tbadges">' + "".join(f'<span class="tb" title="{e(why)}"><b>✓ {e(nm)}</b> {e(why)}</span>' for nm, why in tb_)
                   + f'<a href="{P}/companies/#marks">What the marks mean</a></p>') if tb_ else ""
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
                     + tbadges + (f'<dl class="facts">{"".join(chips)}</dl>' if act else "")
                     + '<nav class="anch" aria-label="On this page">' + (f'<a href="#jobs">Jobs <b>{len(act):,}</b></a>' if act else "")
                     + ('<a href="#pay">Pay</a>' if pay_rows else "") + ('<a href="#stack">Tech stack</a>' if stack else "") + ('<a href="#where">Locations</a>' if where else "") + ('<a href="#similar">Similar companies</a>' if sim else "")
                     + (f'<a href="#closed">Closed <b>{len(arc):,}</b></a>' if arc else "") + '</nav><div id="jobs"></div>')
        wk7 = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
        new7_ = sum(1 for j in act if (j["posted"] or "") >= wk7)
        shut7_ = sum(1 for j in arc if (j.get("closed") or "") >= wk7)
        yrs_c = sorted(j["years"] for j in act if j.get("years"))
        lv_ = Counter(j["level"] for j in act if j["level"])
        pay_c = sorted((lo + hi) / 2 for j in act if j["usd"] for lo, hi in [j["usd"]])
        interns_ = sum(1 for j in act if j["level"] == "Intern")
        co_qa = []
        if act:
            co_qa.append((f"Is {c} hiring right now?", f"Yes: {len(act):,} open {'job' if len(act) == 1 else 'jobs'} on its own careers page as of {fdate(TODAY)}; {new7_:,} were added in the last seven days"
                          + f" and {shut7_:,} closed." + " We re-read the page " + ("every hour." if CFG.get("live_collector") else "several times a day.")))
            if len(act) >= 10:
                co_qa.append((f"Is it hard to get hired at {c}?", (f"The postings that state experience ask for {yrs_c[len(yrs_c) // 2]} years at the median. " if len(yrs_c) >= 5 else "")
                              + ("Levels named in the titles: " + ", ".join(f"{LVL_NAME.get(k, k)} {v:,}" for k, v in lv_.most_common(4)) + ". " if lv_ else "")
                              + f"{sum(1 for j in act if j.get('entry')):,} of the {len(act):,} open roles are junior roles or internships."))
            if len(pay_c) >= 5:
                co_qa.append((f"Does {c} pay well?", f"{len(pay_c):,} of its {len(act):,} open postings state a yearly US-dollar range, with a median of {money(median(pay_c))}; "
                              f"the middle half advertise {money(pay_c[len(pay_c) // 4])} to {money(pay_c[3 * len(pay_c) // 4])}." + (" Pay by field is in the table above." if pay_rows else "")))
            if where:
                co_qa.append((f"Where are {c}'s jobs located?", ", ".join(f"{PLACE_NAME[p_]} ({k})" for p_, k in where) + f"; {sum(1 for j in act if j['remote']):,} of its open roles are remote."))
            if interns_:
                co_qa.append((f"Does {c} have internships?", f"Yes: {interns_:,} open internship{'s' if interns_ > 1 else ''} as of {fdate(TODAY)}."))
        listing(f"companies/{slug}/", f"Jobs at {c}", f"{c} Careers: {roles(len(act), 'Open Job')}, Pay & Hiring ({datetime.date.fromisoformat(TODAY).strftime('%b %Y')}) | {SITE}",
                f"All jobs at {c}: {len(act):,} open" + (f" and {len(arc):,} closed" if arc else "") + f", {new7_:,} added this week. Pay by field, locations and remote roles, from its own careers page.",
                act, head_html=head_html, after=overview + closed + embed, faq=f"jobs at {c}", feed=True, faq_extra=co_qa)

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
    # Job records (records.py), like the postings of a large job site: HRN_RECORDS=1 stores every job as a row of data/jobs.db and writes no
    # job pages, serve.py builds each page when it is asked for; "both" writes the pages as well, for records_test.py. Unset: pages only.
    rec_mode = os.environ.get("HRN_RECORDS", "")
    if rec_mode:
        import records, sys
        size = records.save(ROOT / "data" / "jobs.db", jobs, sys.modules[__name__])
        print(f"job records: {len(jobs):,} in data/jobs.db, {size / 2**20:.0f} MiB")
    if rec_mode == "1":
        URLS.extend(f"job/{j['slug']}/" for j in jobs if job_indexable(j))        # the pages are not files, but they are in the sitemap all the same (not Telegram posts)
    else:
        for j in jobs: job_page(j, by_cat)
    listing("archive/", "Closed jobs archive", f"Closed Jobs Archive ({len(archived):,}) | {SITE}",
            "Closed jobs at companies: see which roles teams were hiring for and when.", archived,
            "Closed jobs stay here so you can see which roles companies were hiring for in the past.")

    # New jobs
    cutoff = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()      # today and the two days before: "the last 3 days", as on the home page
    fresh = [j for j in active if (j["posted"] or "") >= cutoff]
    day_ = [j for j in fresh if NOW - (j.get("ts") or 0) <= 86400]
    upd_ = datetime.datetime.fromtimestamp(NOW, datetime.timezone.utc).strftime("%H:%M UTC")
    wk_cut = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    per_day_ = sum(1 for j in active if (j["posted"] or "") >= wk_cut) / 7
    life_ = []
    for j in archived:
        try:
            if j.get("closed") and j.get("posted"): life_.append((datetime.date.fromisoformat(j["closed"][:10]) - datetime.date.fromisoformat(j["posted"][:10])).days)
        except ValueError: pass
    wk1_ = sum(1 for d_ in life_ if 0 <= d_ <= 7)
    by_f = Counter(j["cat"] for j in day_ if j["cat"] != OTHER[0]).most_common(8)
    by_c = Counter(nm for j in day_ for _, nm in countries_of(j["location"] or "")[:1]).most_common(8)
    new_top = (f'<p class="note">Updated {upd_}, {fdate(TODAY)}. {len(day_):,} posted in the last 24 hours, about {per_day_:,.0f} a day over the last week.</p>'
               + (labrow("Last 24 hours by field", [f'<a href="{P}/jobs/?age=1&amp;cat={c_}">{e(CAT[c_])} · {k_:,}</a>' for c_, k_ in by_f]) if len(by_f) >= 3 else "")
               + (labrow("Last 24 hours by country", [f'<a href="{P}/jobs/?age=1&amp;where={quote(nm)}">{e(nm)} · {k_:,}</a>' for nm, k_ in by_c]) if len(by_c) >= 3 else ""))
    new_qa = [("Where can I find jobs posted today?", f"Here: {len(day_):,} jobs were posted in the last 24 hours and {len(fresh):,} in the last three days, newest first. The list is rebuilt every hour, "
               "and new jobs found between rebuilds are added at the top of this page as they come in."),
              ("How often are new jobs added?", f"Every hour. Over the last week about {per_day_:,.0f} new jobs a day were posted on the employers' own careers pages and picked up here.")]
    if len(life_) >= 50:
        new_qa.append(("Should I apply on the day a job is posted?", f"Earlier is safer: of the {len(life_):,} closed jobs on this site with both dates known, {100 * wk1_ / len(life_):.0f}% came down within a week of being posted. "
                       "Saving a search in My jobs shows what is new each time you come back."))
    new_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in new_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    listing("new/", "New jobs", (f"New Jobs Posted Today: {len(day_):,} in 24 Hours, {len(fresh):,} in 3 Days" if day_ else f"New Jobs: {len(fresh):,} Posted in the Last 3 Days") + f" | {SITE}",
            f"{len(day_):,} jobs posted in the last 24 hours and {len(fresh):,} in the last three days, from employers’ own careers pages. Updated every hour.",
            fresh, intro_for(fresh, "", " posted in the last three days"), feed=True, extra=new_top,
            after=section("Questions about new jobs", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in new_qa) + "</dl>") + new_ld,
            live=f' data-live="new" data-since="{cutoff}"')       # site.js adds the jobs found since this page was built (/api/latest)

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
        for lv, name in ((k, LVL_NAME[k]) for k in ("Intern", "Junior", "Senior", "Lead", "")):
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
    sal_t = []          # job titles with a salary page of their own (20 postings with pay), highest median first
    for slug_r, (rname, rj) in by_role.items():
        ms_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"])
        if len(ms_) >= 20 and slug_r not in BROAD: sal_t.append((median(ms_), slug_r, rname, len(ms_), len(rj)))
    sal_t.sort(reverse=True)
    all_m = sorted((lo + hi) / 2 for _, (lo, hi) in paid)
    below70 = sum(1 for x in all_m if x < 70000)
    common_t = sorted(sal_t, key=lambda r_: -r_[4])[:10]
    sal_qa = []
    if sal_t:
        sal_qa.append(("What job title pays the most?", "By the median of advertised ranges in today’s postings: " + ", ".join(f"{rlow(nm_)} ({money(m_)})" for m_, _, nm_, _, _ in sal_t[:5])
                       + ". The table above ranks every job title with at least 20 postings that state pay."))
    if all_m:
        sal_qa.append(("Is $70,000 a good yearly salary?", f"Among the {len(all_m):,} open jobs on {SITE} that state a yearly US-dollar range, {100 * below70 / len(all_m):.0f}% advertise less than $70,000 at the midpoint. "
                       "Most employers here are technology companies, so this share runs lower than across all US jobs; whether $70,000 is enough depends mostly on where you live."))
    if common_t:
        sal_qa.append(("What are the most common job titles?", "By open postings today: " + ", ".join(f"{rlow(nm_)} ({k_:,})" for _, _, nm_, _, k_ in common_t) + "."))
    sal_qa.append(("What are the levels of job titles?", "From the bottom: intern, junior or associate, the plain title (mid-level), senior, then lead, staff or principal for experts and manager, "
                   "director and vice president for people who lead teams. The table of salaries by level above shows what each step pays in today’s postings."))
    sal_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in sal_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    sal_rows = "".join(f'<tr><td>{i_ + 1}</td><td><a href="{P}/salaries/{s_}/">{e(nm_)}</a></td><td><strong>{money(m_)}</strong></td><td>{c_:,}</td></tr>' for i_, (m_, s_, nm_, c_, _) in enumerate(sal_t))
    page("salaries/", f"Salary by Job Title: {len(sal_t)} Jobs From Live Postings | {SITE}",
         f"Median salary by job title for {len(sal_t)} jobs, plus by category, level, skill and company, from the pay ranges in {len(paid):,} open job postings. Updated daily.",
         crumbs(("Salaries", "")) + '<h1>Salaries from <span class="hl">live job postings</span></h1>'
         f'<p class="lead">{100 - SALPCT}% of open postings do not state a salary, which leaves candidates guessing. These figures come from the {len(paid):,} open roles that do publish a yearly US-dollar range. '
         f'Each figure is a <a href="{P}/glossary/median/">median</a>: half of the postings advertise more than it, half less. These are advertised ranges, not what people are actually paid.</p>'
         f'<p class="cta2"><a class="btn primary" href="{P}/salaries/explorer/">Open the salary explorer</a> <span class="note">Filter by role, place, skill and level, free.</span></p>'
         + (lambda mids_: f'<div class="statrow"><div class="stat"><b>{money(median(mids_))}</b><span>median advertised salary</span></div>'
                          f'<div class="stat"><b>{money(mids_[len(mids_) // 4])} – {money(mids_[3 * len(mids_) // 4])}</b><span>middle half of roles</span></div>'
                          f'<div class="stat"><b>{SALPCT}%</b><span>of open postings state pay</span></div>'
                          f'<div class="stat"><b>{len(mids_):,}</b><span>roles counted today</span></div></div>')(sorted((lo + hi) / 2 for _, (lo, hi) in paid))
         + (section(f"Salary by job title: {len(sal_t)} jobs, highest first", '<div class="tablewrap"><table><tr><th>#</th><th>Job title</th><th>Median advertised salary</th><th>Postings with pay</th></tr>'
                    + sal_rows + '</table></div><p class="note">A job title needs 20 open postings that state a yearly US-dollar range. Open one for its pay by level and place.</p>') if sal_t else "")
         + section("By category", table(g_cat, lambda k: f"salaries/{cat_slug[k]}/" if len(g_cat[k]) >= 30 and k != OTHER[1] else f"jobs/{cat_slug[k]}/", 10))
         + level_section("Salaries by level, intern to lead", paid)
         + section("By skill", table(g_tag, lambda k: f"salaries/{TAG_SLUG.get(k, slugify(k))}/" if len(g_tag[k]) >= 30 else f"skills/{TAG_SLUG.get(k, slugify(k))}/"))
         + section("By company", table(g_comp, lambda k: f"companies/{slugify(k)}/", 8))
         + section("Highest-paying open roles", f'<ul class="jobs">{"".join(card(j) for j, _ in diverse_pairs(best, 30))}</ul>', ("with-salary/", "All jobs with salary"))
         + cite("salaries/", "Salaries from live job postings",
                f"Job postings that state pay advertise a median of {money(median([(lo + hi) / 2 for _, (lo, hi) in paid]))} a year; {100 - SALPCT}% of open postings state no pay at all. "
                f"Counted from {len(paid):,} open postings, {MONTH_YEAR}.")
         + section("Questions about salaries", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in sal_qa) + "</dl>"), head=sal_ld)

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
        sal_qa = [(f"What is the average {label} salary?", f"{money(mean_)} a year on average and {money(median(mids))} at the median, across {len(mids):,} open {label} postings at companies that state pay "
                   f"({MONTH_YEAR}). The median is the better guide: a few very high offers pull the average up."),
                  ("What is the typical range?", f"The middle half of the postings offer {money(pct(.25))} to {money(pct(.75))} a year. A quarter offer less and a quarter offer more."),
                  ("Where do these figures come from?", "From the pay ranges employers print in their own job postings, read from their careers pages every hour. The midpoint of each range is counted. "
                   "These are advertised ranges for open roles, mostly in the United States and in US dollars, not what people are actually paid.")]
        if best_c:
            sal_qa.insert(2, (f"Which companies advertise the highest {label} pay?", ", ".join(f"{k} ({money(m_)})" for m_, k in best_c) + ", by the median of their open postings that state pay (three postings or more)."))
        # Google's "People also ask" for "<job> salary" (checked 15 Nov 2026): "Is it a high paying job?", "How much can you earn?",
        # "What are the top 3 skills?", and searches "per hour", "per month", "entry level": each answered from the same postings.
        all_mid = median([(lo + hi) / 2 for _, (lo, hi) in paid])
        hourly = lambda v: f"${v / 2080:,.0f}"
        ent_ = sorted((lo + hi) / 2 for j, (lo, hi) in group if j.get("entry"))
        with_t = defaultdict(list)
        for j, (lo, hi) in group:
            for t in j.get("tags", []): with_t[t].append((lo + hi) / 2)
        prem = sorted(((median(v) - median(mids), t, len(v)) for t, v in with_t.items() if len(v) >= max(5, len(mids) // 10) and len(v) < len(mids)), reverse=True)[:5]
        prem = [x for x in prem if x[0] > 0]
        sal_qa[3:3] = [
            (f"Is {art(label.lower())} {label.lower()} a high-paying job?",
             f"The median {label} posting advertises {money(median(mids))} a year, {('more than' if median(mids) > all_mid else 'less than')} the median of all {len(paid):,} job postings with pay on {SITE} ({money(all_mid)})."
             f" That is {abs(round((median(mids) / all_mid - 1) * 100))}% {'above' if median(mids) > all_mid else 'below'} the middle of the market."),
            (f"How much can you earn as {art(label.lower())} {label.lower()}?",
             f"A tenth of the postings offer {money(pct(.9))} a year or more; the highest open {label} role advertises up to {money(max(hi for _, (lo, hi) in group))}. Pay rises with level: see the table by level."),
            (f"What is the {label} salary per hour and per month?",
             f"The median of {money(median(mids))} a year is about {hourly(median(mids))} an hour (2,080 working hours) and ${median(mids) / 12:,.0f} a month before tax. "
             f"The middle half of postings: {hourly(pct(.25))} to {hourly(pct(.75))} an hour."),
        ]
        if len(ent_) >= 5:
            sal_qa.insert(6, (f"What does an entry-level {label.lower()} make?", f"{len(ent_):,} junior and intern {label} postings state pay, with a median of {money(median(ent_))} a year "
                                                                                f"({hourly(median(ent_))} an hour)."))
        if prem:
            sal_qa.insert(6, (f"Which skills pay more for {label} roles?", "Postings that ask for " + ", ".join(f"{t} (+{money(d)}, {k} postings)" for d, t, k in prem[:3])
                              + f" advertise more than the {money(median(mids))} median of all {label} postings with pay."))
        sal_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in sal_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        if role:      # a kind of work, so the page can also be read as an occupation with its pay
            sal_ld += ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Occupation", "name": label,
                "description": f"Advertised pay for {label} roles at companies, from {len(mids):,} open job postings that state a yearly range in US dollars.",
                "mainEntityOfPage": {"@type": "WebPage", "url": f"{FULL}/salaries/{slug}/", "lastReviewed": TODAY},
                "estimatedSalary": [{"@type": "MonetaryAmountDistribution", "name": "base", "currency": "USD", "duration": "P1Y",
                                     "percentile25": round(pct(.25)), "median": round(median(mids)), "percentile75": round(pct(.75))}]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        # the figures are the reason to click, so they stay in the title and the site name gives way (a title holds about 65 characters)
        t_long = f"{label} Salary: {money(mean_)} Average, {money(median(mids))} Median ({datetime.date.fromisoformat(TODAY).strftime('%b %Y')})"
        page(f"salaries/{slug}/", t_long if len(t_long) <= 65 else f"{label} Salary: {money(mean_)} Average, {money(median(mids))} Median",
             f"The average {label} salary at companies is {money(mean_)} a year and the median {money(median(mids))}; the middle half of postings offer {money(pct(.25))} to {money(pct(.75))}. "
             f"Counted from {len(mids):,} open job postings that state pay.",
             crumbs(("Salaries", "salaries/"), (label, "")) + f'<h1>{e(label)} salary: <span class="hl">{money(median(mids))} median</span></h1>'
             f'<p class="lead">The median advertised {e(label)} salary is {money(median(mids))} a year, and the middle half of postings offer {money(pct(.25))} to {money(pct(.75))}: '
             f'counted from {len(mids):,} open roles that publish a yearly US-dollar range: about {hourly(median(mids))} an hour or ${median(mids) / 12:,.0f} a month. '
             f'A tenth of the postings offer {money(pct(.9))} or more. Advertised ranges, not verified pay.</p>'
             + act_row("tools/offer-check/", "Check an offer against these figures", [back] if isinstance(back, tuple) else ()) + f'{stats}'
             + cut + (section(f"Skills that pay more for {label} roles", '<div class="tablewrap"><table><tr><th>Skill</th><th>Median with it</th><th>Above the median</th><th>Postings</th></tr>'
                                + "".join(f'<tr><td><a href="{P}/skills/{TAG_SLUG.get(t, slugify(t))}/">{e(t)}</a></td><td>{money(median(mids) + d)}</td><td>+{money(d)}</td><td>{k:,}</td></tr>' for d, t, k in prem)
                                + "</table></div>") if prem else "")
             + section("Top-paying companies", table(comp, lambda k: f"companies/{slugify(k)}/", 3, 25))
             + section(f"Highest-paying open {label} roles", f'<ul class="jobs">{"".join(card(j) for j, _ in top_jobs)}</ul>', back)
             + section(f"Questions about {label} pay", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in sal_qa) + "</dl>")
             + cite(f"salaries/{slug}/", f"{label} salaries",
                    f"The median advertised salary for {label} roles at companies is {money(median(mids))} a year, and the middle half of postings offer {money(pct(.25))} to {money(pct(.75))}. "
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

    # Salary explorer (owner, 15 Nov: "look at Wellfound's salary calculator, maybe ours lacks something"). One page, filters for
    # role, place, skill, field, level and remote, counted in the browser from data/salary-explorer.json: every open posting that states
    # a yearly US-dollar range. Each figure carries its count; nothing is shown from fewer than 20 postings. No trend by quarter until
    # the record covers 60 days.
    EXP_MIN = 20
    ex_jobs = [j for j in active if j["usd"]]
    ex_roles = [(s_, rn) for s_, (rn, rj) in sorted(by_role.items(), key=lambda kv: kv[1][0]) if sum(1 for j in rj if j["usd"]) >= EXP_MIN]
    ex_role_i = {s_: i for i, (s_, _) in enumerate(ex_roles)}
    ex_role_of = defaultdict(list)
    for s_, _ in ex_roles:
        for j in by_role[s_][1]:
            if j["usd"]: ex_role_of[j["id"]].append(ex_role_i[s_])
    ex_place_n = Counter(p_ for j in ex_jobs for p_ in j["places"] if p_ in PLACE_NAME)
    ex_places = [p_ for p_, k_ in sorted(ex_place_n.items(), key=lambda kv: PLACE_NAME[kv[0]]) if k_ >= EXP_MIN]
    ex_place_i = {p_: i for i, p_ in enumerate(ex_places)}
    ex_skill_n = Counter(t for j in ex_jobs for t in j["tags"])
    ex_skills = sorted(t for t, k_ in ex_skill_n.items() if k_ >= EXP_MIN)
    ex_skill_i = {t: i for i, t in enumerate(ex_skills)}
    ex_cats = [cs for cs in CAT if cs != OTHER[0] and sum(1 for j in ex_jobs if j["cat"] == cs) >= EXP_MIN]
    ex_cat_i = {cs: i for i, cs in enumerate(ex_cats)}
    EX_LV = ["", "Intern", "Junior", "Senior", "Lead"]
    flag_txt = lambda p_: re.sub(r"<[^>]+>", "", pfl(p_))
    ex_link = lambda slug_: f"salaries/{slug_}/" if (OUT / "salaries" / slug_ / "index.html").exists() else ""
    ex_data = {"date": TODAY, "since": SURV["since"].isoformat() if SURV else TODAY, "min": EXP_MIN,
               "roles": [[rn, ex_link(s_)] for s_, rn in ex_roles],
               "places": [[PLACE_NAME[p_], flag_txt(p_), ex_link(p_) or f"locations/{p_}/"] for p_ in ex_places],
               "skills": [[t, ex_link(TAG_SLUG.get(t, slugify(t)))] for t in ex_skills],
               "cats": [[CAT[cs], ex_link(cs)] for cs in ex_cats], "levels": EX_LV,
               "rows": [[round(j["usd"][0] / 1000), round(j["usd"][1] / 1000), ex_cat_i.get(j["cat"], -1), EX_LV.index(j["level"]) if j["level"] in EX_LV else 0,
                         j.get("years") or 0, 1 if j["remote"] else 0, [ex_place_i[p_] for p_ in j["places"] if p_ in ex_place_i],
                         [ex_skill_i[t] for t in j["tags"] if t in ex_skill_i][:8], ex_role_of.get(j["id"], [])] for j in ex_jobs]}
    write("data/salary-explorer.json", json.dumps(ex_data, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    ex_mids = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in ex_jobs)
    ex_q = lambda q: ex_mids[min(len(ex_mids) - 1, int(len(ex_mids) * q))] if ex_mids else 0
    ex_days = SURV["days"] if SURV else 1
    opt = lambda items: "".join(f'<option value="{i}">{e(lbl)}</option>' for i, lbl in items)
    ex_links = lambda title, items: (f'<div class="exl"><p class="flabel">{e(title)}</p><p class="rel">' + "".join(f'<a href="{P}/{u}">{lbl}</a>' for lbl, u in items if u) + "</p></div>")
    ex_qa = [("Where do these salaries come from?", f"From the pay ranges employers print in their own open job postings: {len(ex_jobs):,} of them state a yearly range in US dollars today. "
              "The midpoint of each range is counted. These are advertised ranges for open jobs, not what people are paid."),
             ("What do the bands mean?", "Postings are sorted by the middle of their pay range. Below the middle: the lowest 10% to 25%. The middle half: 25% to 75%. "
              "Top of the market: 75% to 90%. The very highest and lowest tenth are left out of the bands, so one unusual posting cannot stretch them."),
             ("Why is there no trend over time yet?", f"Postings have been recorded since {fdate(ex_data['since'])}, {ex_days} days ago. A trend by quarter needs at least 60 days; "
              "it appears on this page by itself when the record is long enough."),
             ("Why do some filters show no figure?", f"Every figure needs at least {EXP_MIN} postings that state pay. With fewer, a single posting moves the result too much, so the page says how many there are instead.")]
    page("salaries/explorer/", f"Salary Explorer: pay by role, place, skill and level | {SITE}",
         f"Filter {len(ex_jobs):,} open job postings that state pay by role, location, skill, field and level: the median, the pay bands, pay by years of experience asked and the best-paid skills.",
         crumbs(("Salaries", "salaries/"), ("Explorer", "")) + "<h1>Salary explorer</h1>"
         f'<p class="lead">Pick a role, a place, a skill or a level and see what employers advertise: the median, the bands around it and what changes the pay. '
         f'Counted from {len(ex_jobs):,} open postings that state a yearly range in US dollars, on {fdate(TODAY)}. Free, no sign-up.</p>'
         '<form class="exf" id="exf" onsubmit="return false">'
         f'<label>Role<select id="ex-role"><option value="">All roles</option>{opt((i, rn) for i, (_, rn) in enumerate(ex_roles))}</select></label>'
         f'<label>Location<select id="ex-place"><option value="">Anywhere</option>{opt((i, flag_txt(p_) + " " + PLACE_NAME[p_]) for i, p_ in enumerate(ex_places))}</select></label>'
         f'<label>Skill<select id="ex-skill"><option value="">Any skill</option>{opt(enumerate(ex_skills))}</select></label>'
         f'<label>Field<select id="ex-cat"><option value="">All fields</option>{opt((i, CAT[cs]) for i, cs in enumerate(ex_cats))}</select></label>'
         '<label>Level<select id="ex-lvl"><option value="">Any level</option><option value="1">Intern</option><option value="2">Junior</option><option value="0">No level in the title</option>'
         '<option value="3">Senior</option><option value="4">Lead and above</option></select></label>'
         '<label class="exr"><input type="checkbox" id="ex-remote"> Remote only</label><button class="linkbtn" type="button" id="ex-reset">Clear filters</button></form>'
         f'<div id="ex-out" aria-live="polite"><div class="stats3 st4"><div class="st"><span class="st-l">Median</span><b class="st-v">{money(ex_q(.5))}</b><span class="st-s">{len(ex_mids):,} postings</span></div>'
         f'<div class="st"><span class="st-l">Middle half</span><b class="st-v">{money(ex_q(.25))}–{money(ex_q(.75))}</b><span class="st-s">25% to 75%</span></div>'
         f'<div class="st"><span class="st-l">Top of the market</span><b class="st-v">{money(ex_q(.75))}–{money(ex_q(.9))}</b><span class="st-s">75% to 90%</span></div>'
         f'<div class="st"><span class="st-l">Below the middle</span><b class="st-v">{money(ex_q(.1))}–{money(ex_q(.25))}</b><span class="st-s">10% to 25%</span></div></div>'
         '<p class="note">The charts appear when the page has loaded the postings.</p></div>'
         f'<p class="note">No trend by quarter yet: postings have been recorded for {ex_days} days, and a trend needs 60. Each figure needs at least {EXP_MIN} postings.</p>'
         + section("Salaries by role, skill, place and field", ex_links("By role", [(e(rn), u) for rn, u in ex_data["roles"]])
                   + ex_links("By skill", [(e(t), u) for t, u in ex_data["skills"]]) + ex_links("By location", [(pfl(p_) + e(PLACE_NAME[p_]), f"locations/{p_}/") for p_ in ex_places])
                   + ex_links("By field", [(e(n_), u) for n_, u in ex_data["cats"]]))
         + section("How the explorer counts", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in ex_qa) + "</dl>")
         + f'<script src="{P}/explorer.js?v={V}" defer></script>',
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
             {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in ex_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")

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
    page("trends/", f"Job Market {TODAY[:4]}: hiring trends from {n:,} open roles | {SITE}",
         "Which skills, companies, roles and cities are hiring right now. Live numbers from open job postings, updated daily.",
         crumbs(("Hiring trends", "")) + "<h1>Hiring trends</h1>"
         '<p class="plain"><b>In plain words:</b> the job market in numbers, counted from the jobs that are open today: which skills employers ask for, who is hiring, where.</p>'
         f'<p class="lead">Live numbers from {n:,} open roles at {m:,} companies, recalculated every day. Feel free to quote them with a link to this page.</p>'
         f'<div class="statrow"><div class="stat"><b>{n:,}</b><span>open roles</span></div><div class="stat"><b>{len(new7):,}</b><span>posted in the last 7 days</span></div>'
         f'<div class="stat"><b>{pctf(len(remote), n)}</b><span>are remote</span></div><div class="stat"><b>{pctf(sum(bool(j["salary"]) for j in active), n)}</b><span>publish a salary</span></div></div>'
         + section("Most in-demand skills", ttable(["Skill", "Open roles", "Share of all roles", "Remote", "Median salary"], skills_rows))
         + section("Companies hiring the most", ttable(["Company", "Open roles", "Remote", "Posted this week"], comp_rows), ("companies/", "All companies"))
         + section("Roles by category", ttable(["Category", "Open roles", "Share", "Remote", "Median salary"], cat_rows))
         + section("Roles by location", ttable(["Location", "Open roles", "Share"], place_rows), ("locations/", "All locations"))
         + '<p class="note">Salary figures are medians of advertised US-dollar ranges and are shown only where at least 15 roles publish one. A role that lists several locations is counted in each.</p>'
         + f'<p class="note">Download the numbers: <a href="{P}/data/open/skills.csv">skills.csv</a>, <a href="{P}/data/open/companies.csv">companies.csv</a>, '
           f'<a href="{P}/data/open/categories.csv">categories.csv</a>, <a href="{P}/data/open/locations.csv">locations.csv</a>.</p>' + cite("trends/", "Hiring trends"))

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
                      trow(["Share of all open roles", pctf(A["n"], n), pctf(B["n"], n)]),
                      trow(["Posted in the last 7 days", f"{A['new']:,}", f"{B['new']:,}"]),
                      trow(["Remote roles", barc(ra, 100, f"{ra:.0f}%"), barc(rb, 100, f"{rb:.0f}%")]),
                      trow(["Entry-level roles", pctf(A["entry"], A["n"]), pctf(B["entry"], B["n"])]),
                      trow(["Senior and lead roles", pctf(A["senior"], A["n"]), pctf(B["senior"], B["n"])]),
                      trow(["Median advertised salary", f"<strong>{money(A['med'])}</strong>" if A["med"] else "too few ranges", f"<strong>{money(B['med'])}</strong>" if B["med"] else "too few ranges"]),
                      trow(["Roles that publish a salary", f"{A['paid']:,}", f"{B['paid']:,}"]),
                      trow(["Most often asked for with", e(", ".join(A["co"])), e(", ".join(B["co"]))]),
                      trow(["Hiring the most", comp(A), comp(B)])]
            qa = [(f"Which has more jobs, {a} or {b}?", demand + f" Counted on {fdate(TODAY)} across {n:,} open roles at {m:,} companies."),
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
                 f'<p class="lead">{e(a)} and {e(b)} side by side in {n:,} live job postings on {fdate(TODAY)}: how many roles ask for each, what they pay and how many are remote.</p>'
                 f'<div class="card verdict"><p><strong>Demand.</strong> {e(demand)}</p><p><strong>Pay.</strong> {e(pay)}</p><p><strong>Remote.</strong> {e(rem)}</p><p><strong>Together.</strong> {e(together)}</p></div>'
                 + section(f"{a} and {b} side by side", ttable(["", f'<a href="{P}/skills/{tslug(a)}/">{e(a)}</a>', f'<a href="{P}/skills/{tslug(b)}/">{e(b)}</a>'], rows_c)
                           + f'<p class="note">Source: open roles on {e(SITE)}, collected from companies\' own careers pages and recounted every day. Salary medians need at least 30 published ranges. '
                             f'<a href="{P}/methodology/">How the numbers are made</a>.</p>')
                 + f'<p class="cta2"><a class="btn" href="{P}/skills/{tslug(a)}/">See {e(a)} jobs</a> <a class="btn ghost" style="margin-top:0" href="{P}/skills/{tslug(b)}/">See {e(b)} jobs</a></p>'
                 + section(f"{a} or {b}: questions people ask", faq_c)
                 + section("More skill comparisons", '<ul class="tiles">' + "".join(tile(cmp_path(x, o), f"{x} vs {o}", len(facts[x]["ids"] | facts[o]["ids"])) for x in (a, b) for o in others[:3]) + "</ul>", ("compare/", "All comparisons"))
                 + cite(path, f"{a} vs {b}: jobs, salaries and remote work"), head=ld_c + crumbs_ld([("Compare skills", "compare/"), (f"{a} vs {b}", "")]))
    # Role against role. The searches are "data analyst vs data scientist", "product manager vs project manager": Google's answer
    # puts what each does, the tools and the pay side by side; People also ask "which is better", "which pays more", "will AI replace",
    # "is it a dead-end job". Each answer here comes from today's postings for the two roles, matched by job title.
    RVS = [("data-analyst", "data-scientist"), ("data-analyst", "business-analyst"), ("data-scientist", "data-engineer"), ("data-engineer", "analytics-engineer"),
           ("data-scientist", "machine-learning-engineer"), ("machine-learning-engineer", "ai-engineer"), ("research-scientist", "machine-learning-engineer"),
           ("software-engineer", "data-engineer"), ("software-engineer", "web-developer"), ("frontend-engineer", "backend-engineer"), ("backend-engineer", "full-stack-engineer"),
           ("frontend-engineer", "full-stack-engineer"), ("devops-engineer", "site-reliability-engineer"), ("devops-engineer", "cloud-engineer"), ("cloud-engineer", "solutions-architect"),
           ("software-architect", "solutions-architect"), ("solutions-engineer", "sales-engineer"), ("security-engineer", "security-analyst"), ("qa-engineer", "test-engineer"),
           ("qa-engineer", "software-engineer"), ("system-administrator", "devops-engineer"), ("network-engineer", "system-administrator"), ("product-manager", "project-manager"),
           ("product-manager", "program-manager"), ("program-manager", "technical-program-manager"), ("project-manager", "scrum-master"), ("product-manager", "business-analyst"),
           ("product-designer", "ux-researcher"), ("product-designer", "graphic-designer"), ("account-executive", "account-manager"), ("account-manager", "customer-success-manager"),
           ("sales-manager", "account-executive"), ("technical-account-manager", "customer-success-manager"), ("business-development", "account-executive"),
           ("content-writer", "technical-writer"), ("recruiter", "technical-recruiter"), ("financial-analyst", "data-analyst"), ("legal-counsel", "paralegal"),
           ("operations-manager", "project-manager"), ("engineering-manager", "tech-lead"), ("staff-engineer", "engineering-manager"), ("mechanical-engineer", "electrical-engineer"),
           ("hardware-engineer", "embedded-engineer"), ("executive-assistant", "chief-of-staff"), ("ux-researcher", "data-analyst")]
    def role_facts(r_):
        nm_, rj_ = by_role[r_]
        k_ = len(rj_)
        mids_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in rj_ if j["usd"])
        yrs_ = sorted(j["years"] for j in rj_ if j.get("years"))
        tg_ = Counter(t for j in rj_ for t in j["tags"])
        return dict(slug=r_, name=nm_, low=rlow(nm_), n=k_, does=roles_info.INFO.get(r_, ("", ""))[1], med=median(mids_) if len(mids_) >= 15 else None,
                    q1=mids_[len(mids_) // 4] if len(mids_) >= 15 else None, q3=mids_[3 * len(mids_) // 4] if len(mids_) >= 15 else None,
                    rem=100 * sum(1 for j in rj_ if j["remote"]) / k_, ent=100 * sum(1 for j in rj_ if j["entry"]) / k_,
                    sen=100 * sum(1 for j in rj_ if j["level"] in ("Senior", "Lead")) / k_, yrs=yrs_[len(yrs_) // 2] if len(yrs_) >= 10 else None,
                    ai=100 * sum(1 for j in rj_ if any(t in AI_TAGS for t in j["tags"])) / k_, pct={t: 100 * c_ / k_ for t, c_ in tg_.items()},
                    skills=[t for t, _ in tg_.most_common(8)], top=Counter(j["company"] for j in rj_).most_common(5),
                    new=sum(1 for j in rj_ if (j["posted"] or "") >= week))
    rvs_done = []
    for a_, b_ in RVS:
        if a_ not in by_role or b_ not in by_role: continue
        A, B = role_facts(a_), role_facts(b_)
        path = f"compare/{a_}-vs-{b_}/"
        an_, bn_ = tcase(A["name"]), tcase(B["name"])
        art_a, art_b = art(A["low"]), art(B["low"])
        verdict_ = []
        big_, small_ = (A, B) if A["n"] >= B["n"] else (B, A)
        verdict_.append(("Demand", f"{big_['n']:,} open {big_['low']} jobs against {small_['n']:,} for {small_['low']} roles today."))
        if A["med"] and B["med"]:
            hi_, lo_ = (A, B) if A["med"] >= B["med"] else (B, A)
            verdict_.append(("Pay", f"{hi_['name']} roles advertise more: a median of {money(hi_['med'])} against {money(lo_['med'])}." if hi_["med"] - lo_["med"] >= 3000
                             else f"About the same: a median of {money(A['med'])} and {money(B['med'])}."))
        verdict_.append(("Remote", f"{A['rem']:.0f}% of {A['low']} jobs and {B['rem']:.0f}% of {B['low']} jobs can be done from home."))
        verdict_.append(("For beginners", f"{A['ent']:.0f}% of {A['low']} jobs and {B['ent']:.0f}% of {B['low']} jobs are junior roles or internships."))
        gap_ab = sorted(((t, B["pct"][t], A["pct"].get(t, 0)) for t in B["skills"] if B["pct"][t] - A["pct"].get(t, 0) >= 8), key=lambda x: -(x[1] - x[2]))[:6]
        gap_ba = sorted(((t, A["pct"][t], B["pct"].get(t, 0)) for t in A["skills"] if A["pct"][t] - B["pct"].get(t, 0) >= 8), key=lambda x: -(x[1] - x[2]))[:6]
        pct_ = lambda v: f"{v:.0f}%"
        comp_ = lambda F: ", ".join(f'<a href="{P}/companies/{slugify(c)}/">{e(c)}</a> ({k:,})' for c, k in F["top"])
        rows_r = [("What they do", e(A["does"]) or "–", e(B["does"]) or "–"),
                  ("Open jobs today", f"{A['n']:,}", f"{B['n']:,}"), ("Posted in the last 7 days", f"{A['new']:,}", f"{B['new']:,}"),
                  ("Median advertised pay", f"<strong>{money(A['med'])}</strong>" if A["med"] else "too few ranges", f"<strong>{money(B['med'])}</strong>" if B["med"] else "too few ranges"),
                  ("Middle half of advertised pay", f"{money(A['q1'])} to {money(A['q3'])}" if A["q1"] else "–", f"{money(B['q1'])} to {money(B['q3'])}" if B["q1"] else "–"),
                  ("Remote", pct_(A["rem"]), pct_(B["rem"])), ("Junior roles and internships", pct_(A["ent"]), pct_(B["ent"])),
                  ("Senior and lead roles", pct_(A["sen"]), pct_(B["sen"])),
                  ("Experience asked (median)", f"{A['yrs']} years" if A["yrs"] is not None else "–", f"{B['yrs']} years" if B["yrs"] is not None else "–"),
                  ("Ask for AI or machine-learning skills", pct_(A["ai"]), pct_(B["ai"])),
                  ("Skills asked most", e(", ".join(A["skills"][:6])), e(", ".join(B["skills"][:6]))), ("Hiring the most", comp_(A), comp_(B))]
        tbl_ = ('<div class="tablewrap"><table><tr><th></th>' + f'<th><a href="{P}/roles/{a_}/">{e(an_)}</a></th><th><a href="{P}/roles/{b_}/">{e(bn_)}</a></th></tr>'
                + "".join(f"<tr><td>{e(r_)}</td><td>{x_}</td><td>{y_}</td></tr>" for r_, x_, y_ in rows_r) + "</table></div>"
                + f'<p class="note">Counted from today’s open postings on {e(SITE)}, matched to each role by job title; pay medians need 15 yearly US-dollar ranges. <a href="{P}/methodology/">How the numbers are made</a>.</p>')
        gap_html = ""
        if gap_ab:
            gap_html += section(f"From {A['low']} to {B['low']}: skills to add", "<ul class=\"ticks\">" + "".join(f"<li><strong>{e(t)}</strong>: named in {v:.0f}% of {B['low']} postings, {w:.0f}% of {A['low']} postings</li>" for t, v, w in gap_ab) + "</ul>")
        if gap_ba:
            gap_html += section(f"From {B['low']} to {A['low']}: skills to add", "<ul class=\"ticks\">" + "".join(f"<li><strong>{e(t)}</strong>: named in {v:.0f}% of {A['low']} postings, {w:.0f}% of {B['low']} postings</li>" for t, v, w in gap_ba) + "</ul>")
        qa_r = [(f"Which is better, {A['low']} or {B['low']}?", f"It depends on the work you like: {art_a} {A['low']} {A['does'] or 'does the work of the role'}; {art_b} {B['low']} {B['does'] or 'does the work of the role'}. "
                 + " ".join(v for _, v in verdict_[:3]))]
        if A["med"] and B["med"]:
            qa_r.append((f"Which pays more, {A['low']} or {B['low']}?", verdict_[1][1] + " These are advertised ranges from job postings, not verified pay."))
        if gap_ab:
            qa_r.append((f"Can {art_a} {A['low']} become {art_b} {B['low']}?", f"Yes, and the skills to add are the ones {B['low']} postings ask for much more often: " + ", ".join(f"{t} ({v:.0f}% against {w:.0f}%)" for t, v, w in gap_ab[:4]) + "."))
        qa_r.append((f"Will AI replace {A['low']}s?" if not A["low"].endswith("s") else f"Will AI replace {A['low']}?",
                     f"Employers still post {A['n']:,} {A['low']} jobs today, and {A['ai']:.0f}% of them ask for AI or machine-learning skills ({B['ai']:.0f}% of {B['low']} jobs): AI is becoming part of the work rather than replacing it outright, judging by the postings."))
        qa_r.append((f"Is {art_a} {A['low']} a dead-end job?", f"No sign of it in the postings: {A['sen']:.0f}% of open {A['low']} jobs are senior or lead roles, so the path up exists, and the skills above show the way across to {B['low']} work."))
        ld_r = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a2_}} for q_, a2_ in qa_r]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page(path, f"{an_} vs {bn_}: Jobs, Pay & Skills ({TODAY[:4]}) | {SITE}",
             f"{an_} vs {bn_}: what each does, {A['n']:,} and {B['n']:,} open jobs, advertised pay, remote share, entry-level share and the skills to add to switch. Counted from today’s postings.",
             crumbs(("Compare", "compare/"), (f"{an_} vs {bn_}", "")) + f'<h1>{e(an_)} vs {e(bn_)}: <span class="hl">what each does, what it pays</span></h1>'
             f'<p class="lead">{e(art_a[0].upper() + art_a[1:])} {e(A["low"])} {e(A["does"])}. {e(art_b[0].upper() + art_b[1:])} {e(B["low"])} {e(B["does"])}. '
             f'Below, the two side by side in today’s {A["n"] + B["n"]:,} open postings.</p>'
             + '<div class="card verdict">' + "".join(f"<p><strong>{e(k_)}.</strong> {e(v_)}</p>" for k_, v_ in verdict_) + "</div>"
             + section(f"{an_} and {bn_} side by side", tbl_) + gap_html
             + f'<p class="cta2"><a class="btn" href="{P}/roles/{a_}/">See {e(A["low"])} jobs</a> <a class="btn ghost" style="margin-top:0" href="{P}/roles/{b_}/">See {e(B["low"])} jobs</a></p>'
             + section(f"{an_} or {bn_}: questions people ask", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a2_)}</dd></div>" for q_, a2_ in qa_r) + "</dl>")
             + f'<p class="note cmpl">Next: <a href="{P}/how-to-become/">how to become one</a> · <a href="{P}/salaries/">salaries by job</a> · <a href="{P}/interview-questions/">interview questions</a></p>',
             head=ld_r + crumbs_ld([("Compare", "compare/"), (f"{an_} vs {bn_}", "")]))
        rvs_done.append((path, f"{an_} vs {bn_}", A["n"] + B["n"]))
    cmp_opts = "".join(f'<option value="{tslug(t)}">{e(t)}</option>' for t in CMP)
    page("compare/", f"Compare Jobs and Skills: Pay, Demand and Remote Share | {SITE}",
         f"Put two tech skills head to head: open roles, median advertised salary, remote share and top employers, counted from {n:,} live job postings every day.",
         crumbs(("Compare skills", "")) + "<h1>Compare skills by jobs and pay</h1>"
         '<p class="plain"><b>In plain words:</b> pick two skills, for example Python and Java, and see which one more employers ask for and which one pays more.</p>'
         f'<p class="lead">Pick two skills and see how many open roles ask for each, what those roles pay and how many are remote. Counted from {n:,} live postings, and counted again every day.</p>'
         f'<div class="card"><div class="fbar" style="margin:0;align-items:flex-end"><label class="wl">First skill<select id="cmp-a">{cmp_opts}</select></label>'
         f'<label class="wl">Second skill<select id="cmp-b">{cmp_opts}</select></label><button class="btn" id="cmp-go" type="button">Compare</button></div></div>'
         + (section("Compare jobs", '<ul class="tiles">' + "".join(tile(u_, t_, k_) for u_, t_, k_ in rvs_done) + "</ul>") if rvs_done else "")
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

    # acronyms match in capitals only ("OPT", not "opt in"); a bare "TN" would be Tennessee, so only "TN visa" / "TN status" count
    VISA_RX = [("H-1B (US)", re.compile(r"\bH-?1B\b")), ("OPT / STEM OPT (US)", re.compile(r"\b(?:STEM )?OPT\b")),
               ("TN (US, Canada and Mexico)", re.compile(r"\bTN (?:visa|status)\b")), ("E-3 (US, Australians)", re.compile(r"\bE-3\b")),
               ("Green card (US)", re.compile(r"green card", re.I)), ("Skilled Worker (UK)", re.compile(r"skilled worker (?:visa|route|sponsorship)", re.I)),
               ("EU Blue Card", re.compile(r"blue card", re.I)), ("Relocation help", re.compile(r"relocation (?:support|assistance|package)", re.I))]
    def visa_kinds(pj):
        """Which visas the postings name, from the posting text (People also ask: "Which companies will sponsor me?", "What visa…?")."""
        txt_ = [(j, (j.get("desc") or "") + " " + (j.get("excerpt") or "")) for j in pj]
        rows_ = [(sum(1 for _, t_ in txt_ if rx.search(t_)), nm) for nm, rx in VISA_RX]
        rows_ = [(k, nm) for k, nm in rows_ if k]
        cos_ = Counter(j["company"] for j in pj).most_common(10)
        out_ = ""
        if rows_:
            out_ += section("Which visas the postings name", "<p>" + ", ".join(f"{e(nm)}: {k:,}" for k, nm in sorted(rows_, reverse=True))
                            + f". Counted from the text of the {len(pj):,} open postings that mention visa sponsorship; many name no visa type. Always confirm with the employer.</p>")
        if cos_:
            out_ += section("Companies that mention sponsorship most", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(c)}/", c, k, True) for c, k in cos_) + "</ul>")
        return out_
    # Perks, employment type, work from anywhere
    perk_tiles = ""
    for name, slug, _ in PERKS:
        pj = [j for j in active if name in j.get("perks", [])]
        if name not in PERK_OK: continue
        perk_tiles += tile(f"perks/{slug}/", name, len(pj))
        # SERP_WORK row 15 ("jobs with visa sponsorship"): title casing, the five views (who hires, where, which work, pay), and the
        # questions people ask; the visa kinds named in the postings stay first
        gl_p, tl_p = hub_sections(f"roles with {name.lower()}", pj, min_k=20)
        pk_qa = []
        if "visa" in name.lower() and pj:
            rem_v = sum(1 for j in pj if j["remote"])
            top_v = Counter(j["company"] for j in pj).most_common(5)
            pk_qa = [("How can I get a job with visa sponsorship?", f"Start with employers that say they sponsor: {len(pj):,} open postings here mention it. Filter them by the country you want, "
                      "check the official visa rules of that country, say in your resume that you need sponsorship, and ask in the first call which visa they would file. Apply on the employer’s own page."),
                     ("Which companies sponsor visas?", "Among today’s postings, the employers that mention visa sponsorship most are " + ", ".join(f"{c} ({k:,})" for c, k in top_v)
                      + ". A company that does not mention it may still sponsor, so ask."),
                     ("Do remote jobs sponsor visas?", f"Rarely, since a remote job is done from where you already live: {rem_v:,} of the {len(pj):,} postings that mention sponsorship are remote. "
                      "Sponsorship matters when the job is on site or hybrid in another country.")]
        listing(f"perks/{slug}/", f"Jobs with {name[0].lower() + name[1:]}", f"Jobs With {tcase(name)} ({len(pj):,} open) | {SITE}",
                f"{roles(len(pj), 'job')} where the posting mentions {name.lower()}. Updated hourly.", pj,
                intro_for(pj, "", f" that mention {e(name.lower())} in the posting") + " We read this from the job text, so check the details with the employer.",
                trail=(("Perks", "perks/"),), feed=True, faq=f"jobs with {name[0].lower() + name[1:]}", faq_extra=pk_qa, extra=gl_p, hub=tl_p,
                after=visa_kinds(pj) if "visa" in name.lower() else "")
    if perk_tiles:
        page("perks/", f"Jobs by Perk — visa sponsorship, equity, 4-day week | {SITE}", "Browse jobs by what the employer offers: visa sponsorship, relocation, equity, 4-day week and more.",
             crumbs(("Perks", "")) + f'<h1>Jobs by perk</h1><p class="lead">What employers mention in their postings. Detected from the job text, so always confirm with the company.</p><ul class="tiles">{perk_tiles}</ul>')
    for et, path, h1 in (("Contract", "contract/", "Contract jobs"), ("Part-time", "part-time/", "Part-time jobs"), ("Internship", "internships/", "Internships")):
        ej = [j for j in active if j.get("etype") == et]
        if len(ej) >= 8:
            yr = f" {TODAY[:4]}–{int(TODAY[:4]) + 1}" if et == "Internship" else ""
            if et == "Internship" and len(ej) >= 40:
                intern_hub(path, h1, yr, ej)
                continue
            listing(path, h1, f"{h1}{yr} ({len(ej):,} open) | {SITE}", f"{roles(len(ej), 'open role')}: {h1.lower()}{yr} at companies, straight from their careers pages. Updated hourly.", ej,
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
        listing("work-from-anywhere/", "Work-from-anywhere jobs", f"Work From Anywhere Jobs ({len(aw):,} open) | {SITE}",
                f"{roles(len(aw), 'remote job')} open to candidates worldwide, with no country restriction in the listing.", aw,
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
        insight("highest-paying-tech-skills", "Highest-paying tech skills", "Which programming languages and tools come with the highest advertised salaries in open jobs right now.",
                "The skills attached to the highest advertised salaries.", ["#", "Skill", "Median salary", "Roles with a salary"],
                [trow([rank(i), tl(t), f"<strong>{money(m_)}</strong>", f"{k:,}"]) for i, (t, m_, k) in enumerate(sal_by_tag[:30])], ("salaries/", "All salary data")),
        insight("most-in-demand-tech-skills", "Most in-demand tech skills", "The skills that appear in the most open job postings right now, with their share and remote rate.",
                "The skills employers ask for most often.", ["#", "Skill", "Open roles", "Share of all roles", "Posted this week"],
                [trow([rank(i), tl(t), f"{len(js):,}", pctf(len(js), n), f"{sum(1 for j in js if (j['posted'] or '') >= week):,}"]) for i, (t, js) in enumerate(sorted(by_tag.items(), key=lambda kv: -len(kv[1]))[:30])],
                ("skills/", "Browse jobs by skill")),
        insight("companies-hiring-remotely", "Companies hiring the most remote workers", "The companies with the most open remote roles right now and how remote-friendly each one is.",
                "Companies ranked by the number of open remote roles.", ["#", "Company", "Remote roles", "Share of its roles"],
                [trow([rank(i), cl(c), f"{r_:,}", pctf(r_, a_)]) for i, (c, r_, a_) in enumerate(x for x in remote_co[:30] if x[1])], ("remote/", "All remote jobs")),
        insight("companies-hiring-entry-level", "Companies hiring interns and juniors", "The companies with the most open internships and junior roles right now.",
                "Companies ranked by open internships and junior roles.", ["#", "Company", "Entry-level roles"],
                [trow([rank(i), cl(c), f"{k:,}"]) for i, (c, k) in enumerate(x for x in entry_co[:30] if x[1])], ("entry-level/", "All entry-level jobs")),
        insight("companies-hiring-this-week", "Companies hiring the most this week", "Which companies posted the most new roles in the last seven days.",
                "Companies ranked by roles posted in the last seven days.", ["#", "Company", "Posted this week", "Open roles in total"],
                [trow([rank(i), cl(c), f"{k:,}", f"{a_:,}"]) for i, (c, k, a_) in enumerate(x for x in week_co[:30] if x[1])], ("new/", "See new jobs")),
        insight("fastest-growing-tech-skills", "Skills with the most new job postings this week", "The skills that showed up in the most job postings published in the last seven days.",
                "Skills ranked by postings published in the last seven days.", ["#", "Skill", "Posted this week", "Open roles in total"],
                [trow([rank(i), tl(t), f"{k:,}", f"{a_:,}"]) for i, (t, k, a_) in enumerate(x for x in week_tag[:30] if x[1])], ("new/", "See new jobs")),
    ]
    def age_days(j):
        try: return (datetime.date.today() - datetime.date.fromisoformat((j["posted"] or j["first_seen"])[:10])).days
        except Exception: return 0
    co_act = {c: [j for j in js if j["active"]] for c, js in companies.items()}
    big = {c: js for c, js in co_act.items() if len(js) >= 20}
    pay_rank = sorted(((c, len(js), sum(bool(j["salary"]) for j in js)) for c, js in big.items()), key=lambda x: (-x[2] / x[1], -x[1]))
    INS.append(insight("pay-transparency", "Pay transparency: which companies publish salaries", "Which employers state the salary in their job postings and which never do, counted from live openings.",
                       f"{SALPCT}% of open roles state a salary where our reader can find it: in the hiring system's pay field or next to a word such as “salary” in the text. "
                       f"These are the employers, among {len(pay_rank)} with 20 or more open roles, that state it most often. A missing salary here can also mean a wording our rules do not recognise.",
                       ["#", "Company", "Open roles", "With a salary", "Share"],
                       [trow([rank(i), cl(c), f"{k_:,}", f"{s_:,}", barc(s_, k_, pctf(s_, k_))]) for i, (c, k_, s_) in enumerate(pay_rank[:50]) if s_],
                       ("with-salary/", "Jobs with the salary listed"), chart=(1, 4)))
    linger = sorted(((c, len(js), sum(age_days(j) >= LONG_OPEN for j in js), int(median([age_days(j) for j in js]))) for c, js in big.items()), key=lambda x: (-x[2] / x[1], -x[1]))
    long_all = sum(age_days(j) >= LONG_OPEN for j in active)
    INS.append(insight("long-open-roles", f"Roles open {LONG_OPEN} days or more: where postings linger", "How many job postings have been open for three months or longer, and at which companies they pile up.",
                       f"{long_all:,} of {n:,} open roles ({pctf(long_all, n)}) were posted {LONG_OPEN} or more days ago. A posting that stays up for months proves nothing by itself, since some employers hire for the same title all year, "
                       "but it is worth knowing before you spend an evening on an application.",
                       ["#", "Company", "Open roles", f"Open {LONG_OPEN}+ days", "Share", "Median days open"],
                       [trow([rank(i), cl(c), f"{k_:,}", f"{l_:,}", barc(l_, k_, pctf(l_, k_)), f"{md_:,}"]) for i, (c, k_, l_, md_) in enumerate(linger[:50]) if l_],
                       ("new/", "Jobs posted in the last 3 days"), chart=(1, 4)))
    pulse_rank = sorted(((c, *PULSE[c]) for c in PULSE if PULSE[c][0] or PULSE[c][1]), key=lambda x: -(x[1] - x[2]))
    INS.append(insight("hiring-pulse", "Hiring pulse: who is ramping up and who is slowing down", "Which companies opened and closed the most roles in the last seven days, from daily snapshots of their careers pages.",
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
    # rivals people compare (the searches are "stripe vs coinbase", "openai vs anthropic"), in the order people type them; a pair is
    # built when both have five open roles or more. Then each larger employer against the one whose skills overlap its own the most.
    VS_RIVALS = [("OpenAI", "Anthropic"), ("OpenAI", "xAI"), ("Anthropic", "xAI"), ("OpenAI", "Perplexity"), ("Anthropic", "Cohere"), ("OpenAI", "Cohere"),
                 ("Stripe", "Coinbase"), ("Stripe", "Adyen"), ("Stripe", "Block"), ("Stripe", "Plaid"), ("Stripe", "Brex"), ("Ramp", "Brex"), ("Ramp", "Mercury"),
                 ("Brex", "Mercury"), ("Coinbase", "Kraken"), ("Coinbase", "Binance"), ("Binance", "OKX"), ("Coinbase", "OKX"), ("Kraken", "Binance"),
                 ("Coinbase", "Crypto.com"), ("Coinbase", "Gemini"), ("Coinbase", "Robinhood"), ("Ripple", "Coinbase"), ("BitGo", "Anchorage Digital"), ("BitGo", "Fireblocks"),
                 ("Affirm", "SoFi"), ("Chime", "SoFi"), ("Monzo", "Wise"), ("Toast", "Block"), ("Databricks", "Snowflake"), ("Databricks", "MongoDB"),
                 ("Datadog", "New Relic"), ("Datadog", "Elastic"), ("Elastic", "MongoDB"), ("Cloudflare", "Fastly"), ("Vercel", "Supabase"), ("Supabase", "MongoDB"),
                 ("Notion", "Asana"), ("Notion", "Linear"), ("Asana", "Linear"), ("Figma", "Miro"), ("Waymo", "Zoox"), ("Waymo", "Nuro"), ("Zoox", "Nuro"),
                 ("Lyft", "Waymo"), ("SpaceX", "Anduril"), ("Palantir", "Anduril"), ("Pinterest", "Reddit"), ("Reddit", "Discord"), ("Instacart", "DoorDash"),
                 ("Scale AI", "Harvey"), ("Cursor", "Vercel"), ("Gusto", "Rippling"), ("Okta", "Cloudflare"), ("GitLab", "Vercel"), ("Samsara", "Flexport")]
    vs_seen = {frozenset(x) for x in vs_pairs}
    for a_n, b_n in VS_RIVALS:
        a_, b_ = slugify(a_n), slugify(b_n)
        if a_ in cfacts and b_ in cfacts and frozenset((a_, b_)) not in vs_seen: vs_pairs.append((a_, b_)); vs_seen.add(frozenset((a_, b_)))
    big_ = [s_ for s_, _ in sorted(cfacts.items(), key=lambda kv: -kv[1]["n"])[:200]]
    for a_ in big_[:80]:
        mine_ = set(STACK.get(cfacts[a_]["name"], ()))
        best_ = max(((len(mine_ & set(STACK.get(cfacts[b_]["name"], ()))), cfacts[b_]["n"], b_) for b_ in big_ if b_ != a_), default=None)
        if best_ and best_[0] >= 6 and frozenset((a_, best_[2])) not in vs_seen:
            vs_pairs.append((a_, best_[2])); vs_seen.add(frozenset((a_, best_[2])))
    def vs_extra(c):
        """What a pair page shows beyond the bars: office policy, this week, places, levels, pay by field and by level."""
        act_ = [j for j in companies[c] if j["active"]]
        n_ = max(1, len(act_))
        pay_f, pay_l = defaultdict(list), defaultdict(list)
        for j in act_:
            if j["usd"]:
                pay_f[j["cat"]].append((j["usd"][0] + j["usd"][1]) / 2); pay_l[LVL_NAME[j["level"]]].append((j["usd"][0] + j["usd"][1]) / 2)
        yrs_ = sorted(j["years"] for j in act_ if j.get("years"))
        return dict(hyb=sum(1 for j in act_ if j.get("hybrid") and not j["remote"]), rem=sum(1 for j in act_ if j["remote"]), n=len(act_),
                    closed=sum(1 for j in companies[c] if not j["active"] and (j.get("closed") or "") >= week),
                    places=[PLACE_NAME[p_] for p_, _ in Counter(p_ for j in act_ for p_ in j["places"] if p_ in PLACE_LIVE).most_common(3)],
                    levels=Counter(LVL_NAME[j["level"]] for j in act_ if j["level"]), yrs=yrs_[len(yrs_) // 2] if len(yrs_) >= 5 else None,
                    pay_f={k: median(v) for k, v in pay_f.items() if len(v) >= 5}, pay_l={k: median(v) for k, v in pay_l.items() if len(v) >= 5})
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
        XA, XB = vs_extra(A["name"]), vs_extra(B["name"])
        pct_ = lambda a_, b_: f"{round(100 * a_ / max(1, b_))}%"
        office_ = lambda X: f"{pct_(X['rem'], X['n'])} remote, {pct_(X['hyb'], X['n'])} hybrid, {pct_(X['n'] - X['rem'] - X['hyb'], X['n'])} on site"
        both_f = sorted(set(XA["pay_f"]) & set(XB["pay_f"]), key=lambda k: CAT[k])
        both_l = [k for k in ("Intern", "Junior", "No level in the title", "Senior", "Lead and above") if k in XA["pay_l"] and k in XB["pay_l"]]
        side_rows = [("Office policy in the postings", office_(XA), office_(XB)),
                     ("This week", f"+{A['week']:,} posted, −{XA['closed']:,} closed", f"+{B['week']:,} posted, −{XB['closed']:,} closed"),
                     ("Hiring most in", ", ".join(XA["places"]) or "–", ", ".join(XB["places"]) or "–"),
                     ("Levels named in titles", ", ".join(f"{k} {v:,}" for k, v in XA["levels"].most_common(3)) or "–", ", ".join(f"{k} {v:,}" for k, v in XB["levels"].most_common(3)) or "–"),
                     ("Experience asked (median)", f"{XA['yrs']} years" if XA["yrs"] is not None else "too few postings say", f"{XB['yrs']} years" if XB["yrs"] is not None else "too few postings say")]
        side_rows += [(f"Median pay: {CAT[k]}", money(XA["pay_f"][k]), money(XB["pay_f"][k])) for k in both_f[:5]]
        side_rows += [(f"Median pay: {k}", money(XA["pay_l"][k]), money(XB["pay_l"][k])) for k in both_l]
        side_tbl = section(f"{A['name']} and {B['name']} in detail", f'<div class="tablewrap"><table><tr><th></th><th>{e(A["name"])}</th><th>{e(B["name"])}</th></tr>'
                           + "".join(f"<tr><td>{e(r_)}</td><td>{e(a_)}</td><td>{e(b_)}</td></tr>" for r_, a_, b_ in side_rows)
                           + '</table></div><p class="note">From each company’s open postings today. Pay rows need 5 postings with a yearly US-dollar range on each side; levels are the words in the job titles.</p>')
        if A["med"] and B["med"]:
            hi_, lo_ = (A, B) if A["med"] >= B["med"] else (B, A)
            pq_ = f"{hi_['name']} advertises more: a median of {money(hi_['med'])} against {money(lo_['med'])} across all their postings with pay."
        else:
            pq_ = "Too few of their postings state a yearly range to compare the whole company."
        if both_f or both_l:
            pq_ += " Like for like: " + "; ".join(f"{CAT[k] if k in CAT else k}: {money((XA['pay_f'] if k in CAT else XA['pay_l'])[k])} at {A['name']}, {money((XB['pay_f'] if k in CAT else XB['pay_l'])[k])} at {B['name']}" for k in (both_f[:3] + both_l[:2])) + "."
        qa_ += [(f"Which pays more, {A['name']} or {B['name']}?", pq_ + " These are advertised ranges, not offers; stock and bonus are rarely in a posting."),
                (f"Which is hiring more right now, {A['name']} or {B['name']}?", f"In the last seven days {A['name']} posted {A['week']:,} roles and closed {XA['closed']:,}; {B['name']} posted {B['week']:,} and closed {XB['closed']:,}."),
                (f"Is {A['name']} or {B['name']} better to work for?", f"This page does not rate employers. What their postings show: {A['name']} is {office_(XA)} with {pct_(A['old'], A['n'])} of roles open {LONG_OPEN}+ days; "
                 f"{B['name']} is {office_(XB)} with {pct_(B['old'], B['n'])}. Team, manager and pay offer matter more, and employee reviews tell more about them.")]
        if XA["yrs"] is not None and XB["yrs"] is not None:
            qa_.append((f"Is it easier to get hired at {A['name']} or {B['name']}?", f"By what the postings ask: a median of {XA['yrs']} years of experience at {A['name']} and {XB['yrs']} at {B['name']}; "
                        f"{A['entry']:,} and {B['entry']:,} roles are for beginners."))
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        side = lambda F: (f'<div><p class="flabel">{e(F["name"])} hires most in</p><p>{e(", ".join(F["fields"]))}</p>' + (f'<p class="flabel">Skills it asks for most</p><p>{e(", ".join(F["skills"]))}</p>' if F["skills"] else "") + "</div>")
        others_ = [x for x in vs_top if x not in (sa, sb)][:6]
        page(vs_path(sa, sb), f"{A['name']} vs {B['name']}: Jobs, Pay, Remote & Hiring ({datetime.date.fromisoformat(TODAY).strftime('%b %Y')}) | {SITE}",
             f"{A['name']} against {B['name']} by their own job postings: {A['n']:,} and {B['n']:,} open roles, the share that is remote, how often pay is stated and what is advertised. Counted {fdate(TODAY)}.",
             crumbs(("Companies", "companies/"), ("Compare", "companies/compare/"), (f"{A['name']} vs {B['name']}", "")) + f"<h1>{e(A['name'])} vs {e(B['name'])}: hiring side by side</h1>"
             f'<p class="lead">What each company’s own job postings show on {fdate(TODAY)}. {e(A["name"])} has {A["n"]:,} open roles, most in {e(" and ".join(A["fields"][:2]))}'
             + (f', hiring mostly in {e(", ".join(XA["places"][:2]))}' if XA["places"] else "") + f'. {e(B["name"])} has {B["n"]:,}, most in {e(" and ".join(B["fields"][:2]))}'
             + (f', hiring mostly in {e(", ".join(XB["places"][:2]))}' if XB["places"] else "") + '.</p>'
             + vs_head(A, B, sa, sb) + f'<div class="vs">{vs_rows(A, B)}</div>'
             + '<div class="card verdict">' + "".join(f"<p>{e(v)}</p>" for v in verdict) + "</div>"
             + f'<div class="vsside">{side(A)}{side(B)}</div>' + side_tbl
             + f'<p class="cta2"><a class="btn" href="{P}/companies/{sa}/">See {e(A["name"])} jobs</a> <a class="btn ghost" style="margin-top:0" href="{P}/companies/{sb}/">See {e(B["name"])} jobs</a></p>'
             + section(f"Questions about {A['name']} and {B['name']} jobs", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
             + section("More comparisons", '<ul class="tiles">' + "".join(tile(vs_path(a2, b2), f"{cfacts[a2]['name']} vs {cfacts[b2]['name']}", cfacts[a2]["n"] + cfacts[b2]["n"])
                 for a2, b2 in ([x for x in vs_pairs if (sa in x or sb in x) and x != (sa, sb)][:6] or [x for x in vs_pairs if x != (sa, sb)][:6])) + "</ul>",
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
         + section("Rivals side by side", '<ul class="xl">' + "".join(f'<li><a href="{P}/{vs_path(a_, b_)}">{e(cfacts[a_]["name"])} vs {e(cfacts[b_]["name"])}</a></li>' for a_, b_ in vs_pairs[24:]) + "</ul>")
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
         f'<p class="lead">Charts and rankings counted from {n:,} open jobs at {m:,} employers, redrawn each time the jobs are read again. Every chart links to the list behind it.</p>'
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
    ahead_cards = list(FUTURE) + [
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
    page("ahead/", f"From the Future: {len(ahead_cards)} Things This Job Site Does That Others Do Not Yet | {SITE}",
         "The chance a job is still open next week, a skill GPS, interview practice out loud, an AI assistant briefed with your resume, and more things job sites do not do yet.",
         crumbs(("From the future", "")) + f'<h1>From the future: <span class="hl">{len(ahead_cards)} things job sites do not do yet</span></h1>'
         '<p class="lead">Each of them works in your browser, with no account and nothing sent to us. Open any of them and try.</p>'
         '<div class="tgrid">' + "".join(f'<a class="tcard" href="{P}/{u}"><span class="tprev" aria-hidden="true">{scr}</span><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span><i><u>{GO.get(u, "Open it")}</u></i></span></a>' for t_, d_, u, scr in ahead_cards) + "</div>"
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
        named_ = [t for t, _ in top_]
        fill_ = lambda m: next((t for t in named_ if t in resume_examples.KIND.get(m.group(1), ())), m.group(2))
        ent_l = [resume_examples.SLOT.sub(fill_, ln) for ln in getattr(resume_examples, "ENTRY", {}).get(slug_r, [])]
        sen_l = [resume_examples.SLOT.sub(fill_, ln) for ln in getattr(resume_examples, "SENIOR", {}).get(slug_r, [])]
        levels_ = ""
        if len(ent_l) >= 3:
            et_ = getattr(resume_examples, "ENTRY_TITLE", {}).get(slug_r) or f"Junior {d['title']}"
            d_e = dict(d, title=et_, summary=f"{et_} starting out, with project and internship experience in {', '.join(skills_[:3])}.",
                       exp=[{"role": f"{d['title']} Intern", "org": "Example Company", "dates": "Summer 2026", "text": ent_l[0]},
                            {"role": "Projects", "org": "Course and personal projects", "dates": "2025 – 2026", "text": "\n".join(ent_l[1:3])}],
                       edu=[{"what": "Bachelor’s degree", "org": "Example University", "dates": "2022 – 2026"}])
            levels_ += section(f"Entry-level {low} resume example (no experience)", paper(d_e) + '<p class="note">With no job of this kind yet, lead with projects, an internship or part-time work, each with a number.</p>')
        if len(sen_l) >= 3 and slug_r != "intern":
            # "Senior" goes in front only where it reads right: not "Senior Senior Accountant", "Senior Chief of Staff" or "Senior Tech Lead"
            st_ = d["title"] if re.match(r"(?i)(senior|lead|head|chief|principal|director|vp|vice)\b", d["title"]) or slug_r in ("engineering-manager", "tech-lead", "software-architect", "chief-of-staff", "staff-engineer") else f"Senior {d['title']}"
            d_s = dict(d, title=st_, summary=f"{st_} with ten years of experience, leading teams and programs. Strongest in {', '.join(skills_[:3])}.",
                       exp=[{"role": st_, "org": "Example Company", "dates": "2021 – now", "text": "\n".join(sen_l)},
                            {"role": d["title"], "org": "Another Example Ltd", "dates": "2016 – 2021", "text": d["exp"][0]["text"].split("\n")[0] if d["exp"] else ""}])
            levels_ += section(f"Experienced {low} resume example" if st_ == d["title"] else f"Senior {low} resume example", paper(d_s) + '<p class="note">At this level the lines are about people led, budgets owned and results across teams.</p>')
        n_ex = 1 + (len(ent_l) >= 3) + (len(sen_l) >= 3 and slug_r != "intern")
        how_ = section(f"How to write {art(low)} {low} resume", '<ol class="steps">'
                       "<li><b>One column, standard headings.</b> Summary, Skills, Experience, Education: screening software reads these in order; tables, icons and two columns can come out scrambled.</li>"
                       "<li><b>Every line: action, tool, result.</b> “Built a churn dashboard in Tableau from SQL data; weekly reporting went from two days to one hour.” A verb first, the tool the posting names, one number.</li>"
                       + (f"<li><b>Lead the skills line with what postings ask for.</b> For this work today: {', '.join(e(t) for t, _ in top_[:5])}. Only the ones you really have.</li>" if top_ else "")
                       + "<li><b>Send it as a PDF unless the form asks for Word.</b> Name the file with your name and the role.</li></ol>"
                       f'<p class="note">Check it before you send: the <a href="{P}/tools/resume-review/">resume checker</a> and the <a href="{P}/tools/resume-match/">match against a posting</a>.</p>')
        if top_:
            qa_.insert(0, (f"What are the top 3 skills for {art(low)} {low}?", "By today’s postings for this work: " + ", ".join(f"{t} ({pc_(k, len(rj))}%)" for t, k in top_[:3]) + "."))
        qa_.append((f"How do I write {art(low)} {low} resume with no experience?", "Put projects, an internship, volunteer or part-time work where the jobs would go, each with what you did and one number; "
                    "put the skills the postings ask for near the top. The entry-level example on this page is written that way." if len(ent_l) >= 3 else
                    "Put projects, an internship, volunteer or part-time work where the jobs would go, each with what you did and one number, and the skills the postings ask for near the top."))
        if len(mids_) >= 30:
            qa_.append((f"Is {art(low)} {low} a high salary?", f"Today’s {low} postings that state a yearly range advertise a median of {money(median(mids_))}. Most employers here are technology companies, so this runs above the wider market."))
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page(f"resume/examples/{slug_r}/", (f"{tcase(rname)} Resume Examples: Entry-Level, Mid & Senior ({TODAY[:4]})" if n_ex == 3 else f"{tcase(rname)} Resume Example ({TODAY[:4]})") + f" | {SITE}",
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
             + levels_ + how_
             + section(f"Questions about {art(low)} {low} resume", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>")
             + f'<p class="note cmpl">Next: <a href="{P}/roles/{slug_r}/">{len(rj):,} open {e(low)} jobs</a> · <a href="{P}/resume/examples/">all resume examples</a> · <a href="{P}/resume/">the resume builder</a></p>', head=ld_)
    write("data/resume-examples.json", json.dumps(rex_data, ensure_ascii=False, separators=(",", ":")), sitemap=False)
    cv_dir = defaultdict(list)
    for slug_r, d in rex_data.items():
        rname, rj = by_role[slug_r]
        fs, fn = fam_of.get(slug_r, ("operations-administration", "Operations and administration"))
        low = rlow(rname)
        uk_ = [j for j in rj if "united-kingdom" in j["places"]]
        gbp_ = sorted(m_ for j in uk_ if (m_ := local_mid(j.get("salary"), "£")))
        eu_ = [j for j in rj if "europe" in j["places"]]
        d_cv = dict(d, summary=d["summary"].replace("five years of experience", "five years’ experience"))
        paper_cv = paper(d_cv).replace('<p class="pp-h">Summary</p>', '<p class="pp-h">Personal profile</p>').replace('<p class="pp-h">Experience</p>', '<p class="pp-h">Employment history</p>')
        cv_qa = [("What is the difference between a CV and a resume?", "In the UK, Ireland, most of Europe, Australia and New Zealand, “CV” is the usual name for the document you send with a job application; "
                  "in the US and Canada it is called a resume, and “CV” means a long academic record. The content is the same idea: a short profile, your jobs with results, education and skills."),
                 ("How long should a UK CV be?", "Two pages of A4 at most; one page is fine early in a career. Recruiters skim the first half page, so put the profile and your latest job there."),
                 ("Should I put a photo on my CV?", "Not in the UK or Ireland, and leave out age, date of birth and marital status: employers there do not expect them and must not use them. "
                  "Some countries in continental Europe still expect a photo, so check the custom of the country you apply in."),
                 (f"What should a personal profile on {art(low)} {low} CV say?", "Three or four lines: your title and years of experience, two strengths employers in this work ask for, and one result with a number. Write it last, after the jobs.")]
        if len(gbp_) >= 5:
            cv_qa.append((f"What do {low} jobs pay in the UK?", f"{len(gbp_):,} open {low} postings in the United Kingdom state a yearly range in pounds: the median midpoint is £{median(gbp_):,.0f}."))
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in cv_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_cv = [("Open jobs in the UK", f"{len(uk_):,}"), ("Open in Europe", f"{len(eu_):,}")] + ([("Median UK pay stated", f"£{median(gbp_):,.0f}")] if len(gbp_) >= 5 else [])
        cv_dir[fs].append((slug_r, rname, len(uk_)))
        page(f"cv-examples/{slug_r}/", f"{tcase(rname)} CV Example (UK): Template & Guide ({TODAY[:4]}) | {SITE}",
             f"A {low} CV example in UK format: personal profile, employment history with results, no photo. Open it in the free builder; {len(uk_):,} {low} jobs open in the UK today.",
             crumbs(("Resume builder", "resume/"), ("CV examples", "cv-examples/"), (rname, "")) + f"<h1>{e(rname)} CV example <span class=\"hl\">(UK format)</span></h1>"
             f'<p class="lead">The same document Americans call a resume, written the way UK and European employers expect it: a personal profile first, your employment history with results, '
             f'no photo, age or marital status. Below, an example to start from and what {len(rj):,} open {e(low)} postings ask for.</p>'
             '<div class="rexgrid"><div>' + paper_cv + '<p class="note">Example. The person, the employers and the numbers are invented; replace them with yours.</p>'
             f'<p><a class="btn primary" href="{P}/resume/?example={slug_r}">Open this CV in the builder</a> <a class="btn ghost" style="margin-top:0" href="{P}/resume/examples/{slug_r}/">US resume version</a></p></div>'
             '<div class="rexside"><div class="invf">' + "".join(f"<div><b>{e(v_)}</b><span>{e(k_)}</span></div>" for k_, v_ in facts_cv) + "</div>"
             + '<h2>UK CV rules in one minute</h2><ol class="steps"><li><b>Two pages of A4 at most.</b> One is fine early on.</li>'
               '<li><b>Personal profile, not objective.</b> Three or four lines on who you are and one result.</li>'
               '<li><b>Leave out</b> photo, age, date of birth, marital status and national insurance number.</li>'
               '<li><b>British spelling and dates</b> (organised, 03/2024), and pay in pounds if you mention it.</li>'
               '<li><b>“References available on request”</b> can go; employers ask for them at the offer.</li></ol></div></div>'
             + section(f"Questions about {art(low)} {low} CV", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in cv_qa) + "</dl>")
             + f'<p class="note cmpl">Next: <a href="{P}/locations/united-kingdom/">jobs in the United Kingdom</a> · <a href="{P}/cover-letter-examples/{slug_r}/">{e(low)} cover letter</a> · <a href="{P}/cv-examples/">all CV examples</a></p>', head=ld_)
    cv_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(cv_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/cv-examples/{s_}/">{e(nm)}</a><span>{k:,} UK jobs</span></li>' for s_, nm, k in sorted(cv_dir[fs], key=lambda x: -x[2])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if cv_dir.get(fs)) + "</div>"
    page("cv-examples/", f"CV Examples (UK Format) for {sum(len(v) for v in cv_dir.values())} Jobs, Free Template | {SITE}",
         f"CV examples in UK format for {sum(len(v) for v in cv_dir.values())} kinds of work: personal profile, employment history with results, no photo. Free to open in the builder.",
         crumbs(("Resume builder", "resume/"), ("CV examples", "")) + '<h1>CV examples <span class="hl">in UK format</span></h1>'
         '<p class="lead">For jobs in the United Kingdom, Ireland and most of Europe: the same examples as our resume pages, laid out as a CV. Pick your work, open it in the free builder and replace every line with your own.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example accountant or designer" aria-label="Find a CV example"></p>'
         f'<p class="lead" id="dirnone" hidden>No example with these words. The <a href="{P}/resume/">builder</a> works for any job.</p>' + cv_html)
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
        cl_head = "[Your name]\n[Phone] · [Email] · [LinkedIn or portfolio link]\n\n[Date]\n\n[Hiring manager’s name]\n[Company]\n[Company address]\n\n"
        letter_ = (cl_head + "Dear Hiring Manager,\n\n"
                   f"I am applying for the {d['title']} position at [Company]. I have [number] years of experience as {art(low)} {low}, most recently at [Current company], "
                   f"where my focus is {d.get('focus') or resume_examples.ROLE.get(slug_r, (None, 'the core of the role'))[1]}.\n\n"
                   + ("Two results from that work:\n" + "\n".join(f"- {ln}" for ln in lines_) + "\n\n" if lines_ else "")
                   + "[One or two sentences on why this company: a product you use, a goal from the posting, a problem you can help with.] "
                   + (f"I would bring the same focus on measurable results, and hands-on experience with {', '.join(top_[:-1]) + ' and ' + top_[-1] if len(top_) > 1 else top_[0]}, which the posting asks for.\n\n" if tech_ and top_
                      else "I would bring the same focus on measurable results to your team.\n\n")
                   + "I would welcome the chance to talk about how I can help. Thank you for your time.\n\nSincerely,\n[Your name]")
        focus_ = d.get('focus') or resume_examples.ROLE.get(slug_r, (None, 'the core of the role'))[1]
        skl_ = (", ".join(top_[:-1]) + " and " + top_[-1]) if len(top_) > 1 else (top_[0] if top_ else "")
        entry_letter = (cl_head + "Dear Hiring Manager,\n\n"
                        f"I am applying for the {d['title']} position at [Company]. I [recently finished / am finishing] [degree, course or certificate], where I focused on {focus_}.\n\n"
                        "In [a course, bootcamp or personal project] I [what you built, analysed or ran], which [one result with a number]. "
                        + (f"I used {skl_}, which the posting asks for.\n\n" if tech_ and skl_ else "\n\n")
                        + "[One or two sentences on why this company: a product you use, a goal from the posting.] I learn quickly and would welcome the chance to show it.\n\n"
                        "Thank you for your time.\n\nSincerely,\n[Your name]")
        senior_letter = (cl_head + "Dear Hiring Manager,\n\n"
                         f"I am applying for the [Senior / Lead] {d['title']} position at [Company]. I have [number] years of experience as {art(low)} {low}, the last [number] leading [a team of N / the main programme] at [Current company].\n\n"
                         + ("Two results I led:\n" + "\n".join(f"- {ln}" for ln in lines_) + "\n\n" if lines_ else "")
                         + "[One sentence on the problem in the posting you would take on first, and how.] I would bring the same focus on results, and on growing the people around me.\n\n"
                         "I would welcome a conversation. Thank you for your time.\n\nSincerely,\n[Your name]")
        sk_pct = [(t, 100 * cnt_[t] / max(1, len(rj))) for t in top_]
        how_cl = section(f"How to write {art(low)} {low} cover letter, paragraph by paragraph", '<ol class="steps">'
                         f'<li><b>Opening.</b> The role you apply for, your years in {e(low)} work and the two or three tools or skills the posting names first.</li>'
                         '<li><b>One or two results.</b> What changed because of you, with a number: time saved, money, people served, errors cut. Use the posting’s own words for the work.</li>'
                         '<li><b>Why this company.</b> One specific reason: a product you use, a goal in the posting, a problem you can help with. A line that fits any company is skipped.</li>'
                         '<li><b>Close.</b> Say you would welcome a conversation, thank them, sign with your full name. Under 250 words in all.</li></ol>')
        tips_cl = section("Quick tips", '<ul class="ticks">'
                          + (f'<li>Mirror the posting: today’s {len(rj):,} {e(low)} postings name ' + ", ".join(f"{e(t)} ({k:.0f}%)" for t, k in sk_pct) + " most often.</li>" if sk_pct else "")
                          + "<li>Put a number in every result: how many, how much, how fast.</li>"
                          "<li>No experience yet? Lead with a project, a course, an internship or volunteer work, and use the entry-level letter above.</li>"
                          "<li>Send it as a PDF or paste it into the form; name the file with your name and the role.</li></ul>")
        descs_ = [j for j in rj if j.get("desc")]
        ask_cl = sum(1 for j in descs_ if CL_RX.search(j["desc"])) if len(descs_) >= 30 else None
        mids_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in rj if j["usd"]]
        cl_qa = [(f"What should {art(low)} {low} cover letter include?", f"Three things: the role you are applying for, one or two results from your {low} work with numbers, and one specific reason you want this company. "
                  + (f"Name the skills the posting names; for this work the most frequent today are {', '.join(top_)}." if top_ else "Use the words the posting uses for its duties.")),
                 (f"Do {low} jobs ask for a cover letter?", ((f"Only {ask_cl} of the {len(descs_):,} open {low} postings with a full description here mention a cover letter in their text" if ask_cl else f"None of the {len(descs_):,} open {low} postings with a full description here mention a cover letter in their text")
                                                              + " (counted today). The application form often has a separate field for one: when it does, a short letter still helps."
                                                              if ask_cl is not None else "Many postings make it optional. A short letter still helps when the application form has a place for it.")),
                 (f"How long should {art(low)} {low} cover letter be?", "Three short paragraphs, under 250 words: a screen without scrolling. Recruiters read the first lines and the results; everything else is skipped."),
                 ("Can I use ChatGPT to write a cover letter?", "Yes, as a first draft, and many people do. Then make it yours: replace general claims with your own results and numbers, use the posting’s words, "
                  "cut it to under 250 words and read it aloud. A letter that could go to any company reads as generated. The free cover letter builder here fills a template from your own facts."),
                 (f"How do I write {art(low)} {low} cover letter with no experience?", "Lead with what you have done: a course or bootcamp project, an internship, volunteer or part-time work, a certificate. "
                  "Give one result with a number, name the skills the posting asks for, and say why this company. The entry-level letter on this page is written that way.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in cl_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = (f'<dl class="facts"><div><dt>Open {e(low)} jobs today</dt><dd>{len(rj):,}</dd></div><div><dt>Can be done from home</dt><dd>{pc_(sum(j["remote"] for j in rj), len(rj))}%</dd></div>'
                  + (f'<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>' if len(mids_) >= 30 else "") + "</dl>")
        cl_dir[fs].append((slug_r, rname, len(rj)))
        page(f"cover-letter-examples/{slug_r}/", f"{tcase(rname)} Cover Letter: 3 Examples & Template ({TODAY[:4]}) | {SITE}",
             f"A {low} cover letter example built around measured results, with what today’s {len(rj):,} open {low} postings ask for. Copy it and fill in the brackets.",
             crumbs(("Cover letter examples", "cover-letter-examples/"), (rname, "")) + f'<h1>{e(rname)} cover letter example: <span class="hl">results first</span></h1>'
             f'<p class="lead">A cover letter for {e(low)} jobs that leads with what you achieved, not with what you were responsible for. Copy it, replace the parts in [brackets] and use the words of the posting you answer.</p>'
             + facts_
             + f'<div class="rl-paper"><pre id="letter">{e(letter_)}</pre><p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the letter</button> <button class="btn ghost sm" type="button" data-doc="letter" data-name="{slug_r}-cover-letter" style="margin-top:0">Word</button> <button class="btn ghost sm" type="button" data-pdf="letter" data-name="{slug_r}-cover-letter" style="margin-top:0">PDF</button> '
               f'<a class="btn ghost sm" href="{P}/tools/cover-letter/" style="margin-top:0">Write yours with the free builder</a></p></div>'
             + section(f"Entry-level {low} cover letter (no experience)", f'<div class="rl-paper"><pre id="letter2">{e(entry_letter)}</pre><p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter2" data-raw="1" style="margin-top:0">Copy the letter</button> <button class="btn ghost sm" type="button" data-doc="letter2" data-name="{slug_r}-cover-letter-entry-level" style="margin-top:0">Word</button> <button class="btn ghost sm" type="button" data-pdf="letter2" data-name="{slug_r}-cover-letter-entry-level" style="margin-top:0">PDF</button></p></div>')
             + section(f"Senior {low} cover letter", f'<div class="rl-paper"><pre id="letter3">{e(senior_letter)}</pre><p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter3" data-raw="1" style="margin-top:0">Copy the letter</button> <button class="btn ghost sm" type="button" data-doc="letter3" data-name="{slug_r}-cover-letter-senior" style="margin-top:0">Word</button> <button class="btn ghost sm" type="button" data-pdf="letter3" data-name="{slug_r}-cover-letter-senior" style="margin-top:0">PDF</button></p></div>')
             + how_cl + tips_cl
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
    def role_kit(slug_r, low, here):
        """Every page about one kind of work links all the others (Upwork's "Resources to help you hire"); pages that exist only."""
        items = [("roles", f"roles/{slug_r}/", "Open jobs"), ("salary", f"salaries/{slug_r}/", "Salary"), ("resume", f"resume/examples/{slug_r}/", "Resume example"),
                 ("letter", f"cover-letter-examples/{slug_r}/", "Cover letter"), ("iq", f"interview-questions/{slug_r}/", "Interview questions"),
                 ("become", f"how-to-become/{slug_r}/", "How to become one"), ("jd", f"job-descriptions/{slug_r}/", "Job description"), ("hire", f"how-to-hire/{slug_r}/", "How to hire")]
        items = [(k, u, t) for k, u, t in items if k != here and (k != "salary" or (OUT / u / "index.html").exists())]
        return section(f"Everything about {low} work", '<div class="rel">' + "".join(f'<a href="{P}/{u}">{e(t)}</a>' for _, u, t in items) + "</div>")
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
        ent_n = sum(1 for j in rj if j.get("entry"))
        jd_qa += [(f"What does {art(low)} {low} do?", (f"{art(low).capitalize()} {low} {does}. " if does else "") + (f"Postings for this work name {', '.join(t for t, _ in top_[:3])} most often." if top_ else "")),
                  (f"Is {art(low)} {low} an IT job?", f"It sits in {fn.lower()} on {SITE}. " + ("Yes: the work is built around software and data." if fs in ("engineering", "data-research", "security") else
                   "Not in the narrow sense: it is its own field, though most postings here are at technology companies.")),
                  (f"Can I become {art(low)} {low} with no experience?", f"{ent_n:,} of today’s {n_:,} postings ({pc_(ent_n, n_)}%) are junior roles or internships"
                   + (f", and the median posting asks for {y_med} years" if y_med else "") + f". The steps, with today’s figures, are on the how-to-become page for this work."),
                  (f"Can I learn {low} work in three months?", "Enough to start on the skills postings name first" + (f" ({', '.join(t for t, _ in top_[:2])})" if top_ else "")
                   + ", and to build one or two projects to show; most employers still ask for a result you have delivered, so a first junior role or internship is the usual next step.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in jd_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        jd_dir[fs].append((slug_r, rname, n_))
        page(f"job-descriptions/{slug_r}/", f"{tcase(rname)} Job Description: Duties, Skills & Template [{TODAY[:4]}] | {SITE}",
             f"A {low} job description template with the figures from {n_:,} open postings: experience asked, pay, skills and benefits employers name. Copy it and post your job free.",
             crumbs(("For employers", "post-a-job/"), ("Job descriptions", "job-descriptions/"), (rname, "")) + f'<h1>{e(rname)} job description: <span class="hl">template and real figures</span></h1>'
             + (f'<p class="lead"><strong>{e(art(low).capitalize())} {e(low)} {e(does)}.</strong> ' if does else '<p class="lead">')
             + f'A template for hiring {art(low)} {e(low)}, with what employers in today’s {n_:,} open postings for this work ask for and offer. Copy it, fill in the brackets, then post the job free.</p>'
             + act_row("post-a-job/", "Post this job free", [("#letter", "Jump to the template")])
             + facts_
             + f'<div class="rl-paper"><pre id="letter">{e(tpl)}</pre><p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the template</button> <button class="btn ghost sm" type="button" data-doc="letter" data-name="{slug_r}-job-description" style="margin-top:0">Word</button> <button class="btn ghost sm" type="button" data-pdf="letter" data-name="{slug_r}-job-description" style="margin-top:0">PDF</button> '
               f'<a class="btn ghost sm" href="{P}/tools/job-description-checker/" style="margin-top:0">Check your description</a> <a class="btn ghost sm" href="{P}/post-a-job/" style="margin-top:0">Post the job free</a></p></div>'
             + section(f"What today’s {low} postings say", '<div class="tablewrap"><table>' + "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in data_rows) + "</table></div>"
                       f'<p class="note">Counted from the {n_:,} open postings for this work on {fdate(TODAY)}, read from employers’ own careers pages. Recounted on every update.</p>')
             + section(f"Questions about hiring {art(low)} {low}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in jd_qa) + "</dl>")
             + role_kit(slug_r, low, "jd")
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
    PROOF_AT = {"engineering": "Put the code on GitHub with a short read-me: what it does, how to run it, one number that shows it works.",
                "data-research": "Use a public dataset (Kaggle, a government open-data portal), publish the queries or notebook on GitHub and a one-page write-up of what you found.",
                "design": "Show three case studies on Behance, Dribbble or your own site: the problem, the sketches, the result and what changed.",
                "product": "Write up one product decision: the problem, the evidence, what you shipped and the number it moved.",
                "marketing": "Publish samples: a campaign with its results, a post, a landing page, each with the number it moved.",
                "sales-bd": "Keep the numbers: quota reached, deals closed, pipeline built, written as results on the resume.",
                "security": "Write up a lab or capture-the-flag result on GitHub or a blog; a certification helps here more than in most work."}
    CERT_RX = re.compile(r"\b(AWS Certified[\w -]{0,30}|Azure [\w ]{0,20}Certifi\w+|Google (?:Cloud|Data Analytics)[\w ]{0,20}Certifi\w+|PMP|CPA|CFA|CISSP|CISM|Security\+|"
                         r"CompTIA [A-Z][\w+]*|Scrum Master|CSM|Salesforce Certified[\w -]{0,25}|Tableau Certified[\w -]{0,20}|ITIL|SHRM-(?:CP|SCP)|PHR|CKA|Six Sigma)\b")
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
        certs_ = Counter(m.strip() for j in rj for m in set(CERT_RX.findall(j.get("desc") or j.get("excerpt") or "")))
        certs_ = Counter({c: k for c, k in certs_.items() if k >= 2})            # one mention is noise ("CPA" once in a data analyst posting)
        with_text = sum(1 for j in rj if j.get("desc"))
        k_ai = sum(1 for j in rj if any(t in AI_TAGS for t in j["tags"]))
        steps = ("<ol class=\"steps\">"
                 f"<li><b>Know what the work is.</b> {e(art(low).capitalize())} {e(low)} {e(does)}." + (f" Beginner postings today use titles like {e('; '.join(titles_))}." if titles_ else "") + "</li>"
                 + (f"<li><b>Learn the skills employers name first.</b> In today’s {n_:,} postings: " + ", ".join(f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a> ({pc_(k, n_)}%)' for t, k in top_) + ".</li>" if top_ else
                    "<li><b>Learn the duties, not only the tools.</b> Postings for this work describe what you will do more than which software you will use: read ten of them and list the duties that repeat.</li>")
                 + "<li><b>Build proof you can show.</b> Two or three results with a number, from a job, a course project or volunteer work. The kind of line a recruiter looks for: "
                 + (f"“{e(lines_[0])}”." if lines_ else "a result with a number.") + (f" {e(PROOF_AT[fs])}" if fs in PROOF_AT else "")
                 + (f" Certifications the postings name: {e(', '.join(c for c, _ in certs_.most_common(3)))}." if certs_ else "") + "</li>"
                 + f'<li><b>Write the resume and the letter.</b> Start from the <a href="{P}/resume/examples/{slug_r}/">{e(low)} resume example</a> and the <a href="{P}/cover-letter-examples/{slug_r}/">cover letter example</a>, and replace every line with your own.</li>'
                 + f'<li><b>Apply where beginners are hired.</b> {len(begin):,} of today’s {n_:,} open {e(low)} jobs are junior or intern roles or ask for two years of experience or less. '
                 + f'<a href="{P}/roles/{slug_r}/">See the open jobs</a> and check each one with the <a href="{P}/tools/resume-match/">resume match checker</a> before you apply.</li></ol>')
        hb_qa = [(f"How much experience do {low} jobs ask for?", (f"The median in today’s postings is {y_med} years; {low_yrs}% of the postings that name a number ask for two years or less." if y_med is not None
                  else "Most postings for this work do not name a number of years. Read the duties: they tell you more about the level than the title does.")),
                 (f"Do I need a degree to become {art(low)} {low}?", (f"{nodeg}% of today’s {n_:,} postings say no degree is required." if nodeg else f"None of today’s {n_:,} postings say outright that no degree is required.")
                  + " Many others accept equivalent experience: read the requirements of each posting."),
                 (f"How much does a beginner {low} earn?", (f"Junior and intern postings for this work that state pay advertise a median of {money(median(jr_pay))} a year ({len(jr_pay)} postings)." if len(jr_pay) >= 8
                  else (f"Few beginner postings state pay. Across all levels, the median advertised pay is {money(median(all_pay))} a year." if len(all_pay) >= 20 else "Too few postings state pay for a reliable figure."))),
                 (f"What qualifications do you need to become {art(low)} {low}?",
                  "Employers name skills first: " + (", ".join(f"{t} ({pc_(k, n_)}%)" for t, k in top_[:3]) + " of today’s postings. " if top_ else "the duties in the posting. ")
                  + (f"The median posting asks for {y_med} years of experience. " if y_med is not None else "")
                  + (f"{nodeg}% say no degree is required. " if nodeg else "")
                  + (("Certifications named in the full text of " + f"{with_text:,} postings: " + ", ".join(f"{c} ({k})" for c, k in certs_.most_common(3)) + ".") if certs_ else "Few postings ask for a specific certification.")),
                 (f"Is AI replacing {low}s?" if not low.endswith("s") else f"Is AI replacing {low}?",
                  f"Not in today’s postings: {n_:,} {low} jobs are open on {SITE} as of {fdate(TODAY)}, and {pc_(k_ai, n_)}% of them ask for AI or machine-learning skills"
                  + (", alongside " + ", ".join(f"{t} ({pc_(k, n_)}%)" for t, k in top_[:2]) + "." if top_ else "."))]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in hb_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = ('<dl class="facts">' + f"<div><dt>Open jobs today</dt><dd>{n_:,}</dd></div><div><dt>Open to beginners</dt><dd>{len(begin):,}</dd></div>"
                  + (f"<div><dt>Experience asked, median</dt><dd>{y_med} years</dd></div>" if y_med is not None else "")
                  + (f"<div><dt>Beginner pay, median</dt><dd>{money(median(jr_pay))}</dd></div>" if len(jr_pay) >= 8 else "") + "</dl>")
        many = ROLE_PLURAL.get(rname, low + "s")
        lv_pay = defaultdict(list)
        for j in rj:
            if j["usd"]: lv_pay[j["level"]].append((j["usd"][0] + j["usd"][1]) / 2)
        ladder = [(LVL_NAME[k], median(lv_pay[k]), len(lv_pay[k])) for k in ("Intern", "Junior", "", "Senior", "Lead") if len(lv_pay[k]) >= 5]
        tools_ = [(t, k) for t, k in cnt_.most_common(12) if k >= 3][:10]
        extra_hb = ""
        if tools_:
            extra_hb += section(f"Tools and software {many} use", "<p>" + ", ".join(f'<a href="{P}/skills/{tslug(t)}/">{e(t)}</a> ({pc_(k, n_)}%)' for t, k in tools_)
                                + f" of today’s {n_:,} open {e(low)} postings name them. Learn the first three well before the rest.</p>")
        if len(ladder) >= 2:
            extra_hb += section(f"{rname} career path: levels and pay", '<div class="tablewrap"><table><tr><th>Step</th><th>Median advertised pay</th><th>Postings with pay</th></tr>'
                                + "".join(f"<tr><td>{e(nm_)}</td><td><strong>{money(md_)}</strong></td><td>{c_:,}</td></tr>" for nm_, md_, c_ in ladder)
                                + '</table></div><p class="note">The step is the level word in the job title; “No level in the title” is usually the mid-level role. '
                                f'After senior, people move into lead, staff or principal roles, or into managing a team. <a href="{P}/guides/job-levels-explained/">What each level means</a>.</p>')
        goals_ = [f"Get fluent in {top_[0][0]}, the skill today’s postings name most, and prove it with a project you can show." if top_ else "Build one piece of work you can show and talk about in an interview.",
                  (f"Earn a certification employers name in this work: {', '.join(c for c, _ in certs_.most_common(2))}." if certs_ else "Take one short course in the field and finish it with a project, not only a certificate."),
                  "Keep a list of your results with numbers, updated every month: it becomes your resume lines and your interview stories.",
                  "Find one person a few years ahead of you in this work and ask for a 20-minute talk each quarter."]
        extra_hb += section(f"Professional development goals for {art(low)} {low}", '<ul class="ticks">' + "".join(f"<li>{e(g_)}</li>" for g_ in goals_) + "</ul>")
        li_skills = " · ".join(t for t, _ in top_[:3]) if top_ else ""
        extra_hb += section(f"LinkedIn profile tips for {art(low)} {low}", '<ul class="ticks">'
                            + f'<li><b>Headline:</b> the title employers search for, then your strongest skills and one result: “{e(tcase(rname))}' + (f" | {e(li_skills)}" if li_skills else "") + ' | [one result with a number]”.</li>'
                            + "<li><b>About:</b> three short paragraphs: what you do, two results with numbers, what you want next.</li>"
                            + f"<li><b>Skills section:</b> list the skills postings name, in their words" + (f": {e(', '.join(t for t, _ in tools_[:5]))}" if tools_ else "") + ".</li>"
                            + "<li><b>Open to work:</b> set the job titles and places you want; recruiters filter by them.</li></ul>"
                            + f'<p class="note">Write the headline with the <a href="{P}/tools/linkedin-headline/">LinkedIn headline generator</a>.</p>')
        hb_dir[fs].append((slug_r, rname, len(begin)))
        page(f"how-to-become/{slug_r}/", f"How to Become {art(low)} {tcase(rname)}: Skills, Pay and {len(begin):,} Beginner Jobs | {SITE}",
             f"How to become {art(low)} {low}, from today’s {n_:,} open postings: {len(begin):,} are open to beginners. The skills employers name first, the experience they ask for and what juniors earn.",
             crumbs(("How to become…", "how-to-become/"), (rname, "")) + f'<h1>How to become {art(low)} {e(low)}: <span class="hl">{len(begin):,} beginner jobs open today</span></h1>'
             f'<p class="lead">Five steps for people changing careers, with the figures from today’s {n_:,} open {e(low)} postings: what employers ask for first, how much experience, and what beginners are paid.</p>'
             + act_row(f"roles/{slug_r}/", f"See the {n_:,} open {low} jobs", [(f"resume/examples/{slug_r}/", "Resume example")])
             + facts_ + section(f"Five steps to your first {low} job", steps) + extra_hb
             + section(f"Questions about becoming {art(low)} {low}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in hb_qa) + "</dl>")
             + role_kit(slug_r, low, "become")
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
    def iq_li(q, why, good, sample=""):
        return (f'<li><h3>{e(q)}</h3><p class="why">{why}</p>' + (f'<p class="good"><b>A good answer shows:</b> {e(good)}</p>' if good else "")
                + (f'<p class="good"><b>{"Answer" if not good else "Sample answer"}:</b> {e(sample)}</p>' if sample else "") + "</li>")
    import quiz_pages
    QUIZ_BY_SKILL = {v["skill"]: (k, v) for k, v in quiz_pages.QUIZZES.items()}
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
        ex_lines = [ln.strip() for ex in (d.get("exp") or []) for ln in ex["text"].split("\n") if ln.strip()]
        def sample_for(t):
            hit = next((ln for ln in ex_lines if t.lower() in ln.lower()), ex_lines[0] if ex_lines else "")
            first = hit.split()[0] if hit else ""
            hit = (hit[0].lower() + hit[1:]) if first[:1].isupper() and first[1:].islower() else hit      # "Built …" -> "built …", but "SQL …" stays
            return (f"“In my last role I {hit.rstrip('.')}. I did that part myself: I chose how to do it, checked the result and explained it to the team.” "
                    "Then say what you would do differently.") if hit else ""
        sk_items = [(SK_Q[i][0].format(t=t), f"{pc_(k, n_)}% of today’s {n_:,} open {e(low)} postings name {e(t)}.", SK_Q[i][1], sample_for(t)) for i, (t, k) in enumerate(top_)]
        # concrete technical questions with the answer, for the skills this work asks for most that have a skill test on the site
        tech_items = []
        for t, k in cnt_.most_common(10):
            if t in QUIZ_BY_SKILL and k >= max(5, n_ * 0.1) and len(tech_items) < 8:
                qk, qv = QUIZ_BY_SKILL[t]
                for q_, opts, right, why in qv["qs"][:4]:
                    tech_items.append((q_, f'A {e(t)} question ({pc_(k, n_)}% of today’s postings name {e(t)}). More in the <a href="{P}/skill-tests/{qk}/">{e(t)} skill test</a>.',
                                       "", f"{opts[right]}. {why}"))
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
        groups = [(f"Questions about the skills {low} postings name", sk_items), (f"Technical {low} interview questions and answers", tech_items), (f"Questions about the work itself", du_items),
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
                 (f"How do I prepare for {art(low)} {low} interview?",
                  "Prepare three real stories with a number each (a result, a problem you solved, work with other people), practise them out loud for 60 to 90 seconds"
                  + (f", and revise the skills the postings name most: {', '.join(t for t, _ in top_[:3])}" if top_ else "") + ". Read the posting again the day before: the duties it lists are what they will ask about."),
                 (f"Is {art(low)} {low} interview hard?",
                  (f"It depends on the level: today’s {low} postings ask for {sorted(j['years'] for j in rj if j.get('years'))[len([j for j in rj if j.get('years')]) // 2]} years of experience at the median. " if len([j for j in rj if j.get('years')]) >= 10 else "")
                  + "Most interviews mix questions about the skills in the posting with questions about how you work; the technical part is easier with a real example ready for each skill."),
                 (f"What salary should I ask for as {art(low)} {low}?", (f"Today’s {len(mids_):,} {low} postings that state a yearly US-dollar range advertise a median of {money(median(mids_))}. Adjust for your experience and the country, and ask for their range first."
                  if len(mids_) >= 20 else "Look at postings for this work that state pay, adjust for your experience and the country, and ask for their range first."))]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in iq_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = ('<dl class="facts">' + f"<div><dt>Questions to prepare</dt><dd>{n_q}</dd></div><div><dt>Open {e(low)} jobs today</dt><dd>{n_:,}</dd></div>"
                  + (f"<div><dt>Postings read in full</dt><dd>{len(descs_):,}</dd></div>" if own_text else "")
                  + (f"<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>" if len(mids_) >= 20 else "") + "</dl>")
        iq_dir[fs].append((slug_r, rname, n_q))
        page(f"interview-questions/{slug_r}/", f"{n_q} {tcase(rname)} Interview Questions and Answers ({TODAY[:4]}) | {SITE}",
             f"{n_q} {low} interview questions to prepare for, each with why it is likely to come up (from today’s {n_:,} open {low} postings) and what a good answer shows.",
             crumbs(("Interview questions", "interview-questions/"), (rname, "")) + f'<h1>{e(rname)} interview questions: <span class="hl">{n_q} to prepare for</span></h1>'
             f'<p class="lead">Each question says why it is likely to come up, from what today’s {n_:,} open {e(low)} postings ask for, and what a good answer shows. '
             f'Prepare a real example for each, then practise it with the <a href="{P}/tools/interview-answer-builder/">interview answer builder</a>.</p>'
             f'<p class="note">Updated {fdate(TODAY)}, from that day’s open postings.</p>'
             + act_row("#practise", "Practise out loud", note="The page reads each question aloud and checks your answer. This site keeps nothing.")
             + facts_ + body_
             + section("Questions to ask them", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in ask_) + "</dl>")
             + section(f"Questions about {art(low)} {low} interview", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in iq_qa) + "</dl>")
             + section("Prepare with", '<div class="feats">'
                       f'<a class="feat" href="{P}/tools/interview-answer-builder/"><h3>Interview answer builder</h3><p>Turn an example into a 60 to 90 second answer, with checks for a number and for “I”.</p></a>'
                       f'<a class="feat" href="{P}/resume/examples/{slug_r}/"><h3>The {e(low)} resume example</h3><p>The results interviewers ask about, written as resume lines.</p></a>'
                       f'<a class="feat" href="{P}/tools/thank-you-email/"><h3>Thank-you email</h3><p>Send it on the day of the interview, written from four fields.</p></a>'
                       f'<a class="feat" href="{P}/roles/{slug_r}/"><h3>{n_:,} open {e(low)} jobs</h3><p>Read from employers’ own careers pages every hour.</p></a></div>')
             + role_kit(slug_r, low, "iq")
             + f'<p class="note">Counted from the open postings on {fdate(TODAY)}, read from employers’ own careers pages and recounted on every update. The questions are ours; no employer’s interview is copied here.</p>', head=ld_)
    iq_n = sum(len(v) for v in iq_dir.values())
    iq_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(iq_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/interview-questions/{s_}/">{e(nm)}</a><span>{k} questions</span></li>' for s_, nm, k in sorted(iq_dir[fs], key=lambda x: x[1])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if iq_dir.get(fs)) + "</div>"
    page("interview-questions/", f"Interview Questions for {iq_n} Jobs, with What a Good Answer Shows | {SITE}",
         f"Interview questions for {iq_n} kinds of work. Each says why it is likely to come up, from today’s open postings, and what a good answer shows. Free, no sign-up.",
         crumbs(("Interview questions", "")) + f'<h1>Interview questions for <span class="hl">{iq_n} jobs</span></h1>'
         '<p class="lead">Pick your work. Each page lists the questions to prepare for, why each is likely to come up, from the skills and situations today’s open postings name, and what a good answer shows.</p>'
         f'<p class="note">Want to rehearse? <a href="{P}/interview-practice/">Practise out loud</a>: the page reads the questions and times your answers. Or take a <a href="{P}/skill-tests/">skill test</a> on SQL, Excel, Python and more.</p>'
         '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, analyst or designer" aria-label="Find a job"></p>'
         f'<p class="lead" id="dirnone" hidden>No page with these words. The <a href="{P}/tools/interview-answer-builder/">interview answer builder</a> works for any job.</p>' + iq_html)

    ip_html = '<div class="dir" id="dir">' + "".join(
        f'<div class="dirb"><h2><span>{e(fn)}</span><span>{len(iq_dir[fs])}</span></h2><ul>' + "".join(f'<li data-n="{e(nm.lower())}"><a href="{P}/interview-questions/{s_}/#practise">{e(nm)}</a><span>{k} questions</span></li>' for s_, nm, k in sorted(iq_dir[fs], key=lambda x: x[1])) + "</ul></div>"
        for fs, fn, fd, live, js_ in fam_rows if iq_dir.get(fs)) + "</div>"
    ip_qa = [("How can I practice for an interview?", "Pick your job below: the page reads each likely question aloud, listens to your answer in the browser and checks its length, whether it has a number and whether you said what you did. "
              "Practise three real stories out loud for 60 to 90 seconds each, then once more with a friend or a recording."),
             ("What is the STAR method?", "A way to tell a work story: the Situation, the Task you had, the Action you took and the Result, with a number. Keep the action the longest part and say “I”, not “we”."),
             ("What is the 30-60-90 rule in an interview?", "A short plan for your first three months in the job: what you will learn in the first 30 days, what you will start to change by day 60, and what result you will own by day 90. "
              "Interviewers for senior roles often ask for one."),
             ("What are the 5 P’s of interviewing?", "A saying, not a fixed method: “prior preparation prevents poor performance”. In practice: read the posting, research the company, prepare your stories, practise them out loud and prepare your own questions."),
             ("How long should an interview answer be?", "Most answers work best in 60 to 90 seconds; “tell me about yourself” in about a minute. Longer answers lose the listener; the practice mode times each one.")]
    ip_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in ip_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("interview-practice/", f"Free Interview Practice: Questions Read Aloud and Timed | {SITE}",
         f"Practise a job interview out loud for {iq_n} kinds of work: the page reads each question, listens to your answer in the browser and checks it. Free, no sign-up, nothing recorded.",
         crumbs(("Interview questions", "interview-questions/"), ("Practice", "")) + '<h1>Free interview practice: <span class="hl">questions read aloud, answers timed</span></h1>'
         f'<p class="lead">Pick your job. The page reads each likely question aloud, listens to your answer in the browser and checks three things: the length, a number, and whether you said what you did. '
         'No sign-up, and nothing you say is recorded or sent anywhere.</p>'
         + section("Three ways to structure an answer", '<dl class="qa">'
                   "<div><dt>STAR, for “tell me about a time…”</dt><dd>Situation, Task, Action, Result. One sentence each for the first two, most of the time on what you did, and a result with a number.</dd></div>"
                   "<div><dt>“Tell me about yourself”, in about a minute</dt><dd>What you do now, one result you are proud of, and why this job is the next step. Leave your life story out.</dd></div>"
                   "<div><dt>A 30-60-90 day plan, for senior roles</dt><dd>What you will learn by day 30, start to change by day 60 and own by day 90, tied to the goals in the posting.</dd></div></dl>"
                   f'<p class="note">Write the stories first with the <a href="{P}/tools/interview-answer-builder/">interview answer builder</a>, then practise them here.</p>')
         + '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type a job, for example nurse, analyst or designer" aria-label="Find a job"></p>'
         + f'<p class="lead" id="dirnone" hidden>No page with these words. The <a href="{P}/tools/interview-answer-builder/">interview answer builder</a> works for any job.</p>' + ip_html
         + section("Questions about interview practice", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in ip_qa) + "</dl>"), head=ip_ld)

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
        fam_r = [r_ for r_ in next((rs_ for fs2, _, _, rs_ in roles_info.FAMILIES if fs2 == fs), []) if r_ != slug_r and r_ in by_role and len(by_role[r_][1]) >= 20][:5]
        def r_med(r_):
            m_ = [(j["usd"][0] + j["usd"][1]) / 2 for j in by_role[r_][1] if j["usd"]]
            return money(median(m_)) if len(m_) >= 15 else "–"
        which_ = (section("Which role do you need?", f'<p>Close to {e(low)} work, and often confused with it. Pick by the work you need done, then the guide for that role:</p>'
                          '<div class="tablewrap"><table><tr><th>Role</th><th>Open postings</th><th>Median advertised pay</th><th>Guide</th></tr>'
                          + f'<tr><td><strong>{e(rname)}</strong></td><td>{n_:,}</td><td>{money(median(mids_)) if len(mids_) >= 15 else "–"}</td><td>this page</td></tr>'
                          + "".join(f'<tr><td><a href="{P}/roles/{r_}/">{e(by_role[r_][0])}</a></td><td>{len(by_role[r_][1]):,}</td><td>{r_med(r_)}</td>'
                                    + (f'<td><a href="{P}/how-to-hire/{r_}/">How to hire</a></td>' if r_ in rex_data else "<td>–</td>") + "</tr>" for r_ in fam_r)
                          + "</table></div>") if fam_r else "")
        hr_r = sorted(h_[0] for j in rj if (h_ := usd_hourly(j["salary"])))
        con_pct = pc_(sum(1 for j in rj if j.get("etype") == "Contract"), n_)
        task_ = section(f"A take-home task for {art(low)} {low}", '<ul class="ticks">'
                        "<li>Use a real, anonymised task from your own work: the kind of problem the person will meet in the first month.</li>"
                        "<li>Keep it to two or three hours, say so, and pay for anything longer.</li>"
                        "<li>Ask for three things: the result, how they got there, and one recommendation or next step.</li>"
                        + (f"<li>Score every answer on the same points: correctness, clarity, judgement and the use of {', '.join(e(t) for t, _ in top_[:3])}.</li>" if top_ else
                           "<li>Score every answer on the same points: correctness, clarity and judgement.</li>")
                        + "<li>Talk it through in the next interview: how they explain their choices tells as much as the result.</li>"
                        "<li>Not sure yet? A short paid trial project or a contract-to-hire term lets both sides check the fit.</li></ul>")
        hh_more = [(f"Should I hire a freelance {low} or a full-time one?", f"{con_pct}% of today’s {low} postings are contract roles. Freelance suits a defined project with an end date; full-time suits ongoing work and anything that needs "
                    "knowledge of your business. A paid trial project or a contract-to-hire term lets both sides check the fit first."),
                   (f"How much does a freelance {low} cost per hour?", (f"The {len(hr_r):,} postings for this work that state an hourly rate advertise a median of ${hr_r[len(hr_r) // 2]:,.0f} an hour." if len(hr_r) >= 5 else
                    (f"Few postings for this work state an hourly rate. The median yearly pay divided by 2,080 hours is about ${median(mids_) / 2080:,.0f} an hour; contractors usually charge more, since they pay their own taxes, holidays and insurance." if len(mids_) >= 20 else
                     "Few postings for this work state pay by the hour. Ask two or three freelancers for a quote on the same task brief.")))]
        if top_:
            hh_more.append((f"What skills should I test in {art(low)} {low}?", "The ones today’s postings name most: " + ", ".join(f"{t} ({100 * k / n_:.0f}%)" for t, k in top_[:5])
                            + ". Test them on a small task from your own work rather than with trivia questions."))
        hh_qa = [(f"How much does it cost to hire {art(low)} {low}?", (f"The pay is the largest part: today’s {low} postings that state a yearly US-dollar range advertise a median of {money(median(mids_))}. " if len(mids_) >= 20 else "The pay is the largest part. ")
                  + "Add advertising, agency fees if you use one and the hours your team spends interviewing; the cost per hire calculator on this site adds them up. Posting on this site is free."),
                 (f"How long does it take to hire {art(low)} {low}?", (f"Half of today’s open {low} postings have been up more than {age_med} days" + (f", and postings for this work that closed since we started tracking stayed up a median of {cl_med} days" if cl_med is not None else "")
                  + ". A posting can close before the person starts, so plan for a few weeks more." if age_med is not None else "It depends on the level and the market; plan for several weeks from posting to the first day.")),
                 (f"Where can I find {many}?", f"{len(cos_):,} companies are hiring {many} on this site today. Post your job here free, on your own careers page and in communities where {many} meet; "
                  + ("the table on this page lists the countries named most in today’s postings." if len(ctry_) >= 3 else "name the countries you can hire in."))]      # no country names in plain text: a country is shown with its flag
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in hh_qa + hh_more]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
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
             + which_
             + section(f"Six steps to hire {art(low)} {low}", steps)
             + task_
             + section(f"Questions about hiring {many}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in hh_qa + hh_more) + "</dl>")
             + role_kit(slug_r, low, "hire")
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

    # Relocation guides, one per country (Relocate.me lives on guides like these, the owner asked for them): from today's postings in
    # the country, the employers that mention visa sponsorship or help with the move, the kinds of work, the pay, and the official
    # immigration site. Only official sites that answered when checked on 2026-11-14 are linked; no visa rule is restated here.
    OFFICIAL_VISA = {
        "GB": ("GOV.UK: Skilled Worker visa", "https://www.gov.uk/skilled-worker-visa"),
        "SG": ("Ministry of Manpower: passes and permits", "https://www.mom.gov.sg/passes-and-permits"),
        "DE": ("Make it in Germany, the German government’s portal for skilled workers", "https://www.make-it-in-germany.com/en/"),
        "IE": ("Department of Enterprise: employment permits", "https://enterprise.gov.ie/en/what-we-do/workplace-and-skills/employment-permits/"),
        "AU": ("Department of Home Affairs: working in Australia", "https://immi.homeaffairs.gov.au/visas/working-in-australia"),
        "JP": ("Immigration Services Agency of Japan", "https://www.isa.go.jp/en/"),
        "NL": ("IND: residence permits for work", "https://ind.nl/en/residence-permits/work"),
        "KR": ("Hi Korea, the Korean immigration portal", "https://www.hikorea.go.kr/")}
    cname_ = {c: nm for c, nm, _, _ in COUNTRIES}
    cname_["US"] = "United States"
    the_c = lambda c: ("the " if c in {"US", "GB", "NL", "AE", "PH", "CZ"} else "") + cname_.get(c, c)
    rl_rows = []
    for _, slug, rule in PLACES:
        if not (isinstance(rule, str) and len(rule) == 2): continue
        cj = [j for j in active if slug in j["places"]]
        both = [j for j in cj if {"Visa sponsorship", "Relocation support"} & set(j.get("perks", []))]
        if len(cj) < 150 or len(both) < 10: continue
        c, nm = rule, the_c(rule)
        flg = fl(c)
        visa_ = [j for j in both if "Visa sponsorship" in j.get("perks", [])]
        relo_ = [j for j in both if "Relocation support" in j.get("perks", [])]
        cos_ = Counter(j["company"] for j in both).most_common(10)
        ids_ = {j["id"] for j in both}
        roles_ = sorted(((sum(1 for j in rj if j["id"] in ids_), slug_r, rname) for slug_r, (rname, rj) in by_role.items() if slug_r not in BROAD and not slug_r.endswith("-speaking")), reverse=True)
        roles_ = [x for x in roles_ if x[0] >= 2][:8]
        mids_ = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in both if j["usd"])
        rem_ = pc_(sum(1 for j in both if j["remote"]), len(both))
        newest = sorted(both, key=lambda j: j.get("posted") or "", reverse=True)[:12]
        off = OFFICIAL_VISA.get(c)
        lists_ = [(f"perks/visa-sponsorship/{slug}/", f"{len(visa_):,} jobs with visa sponsorship"), (f"perks/relocation/{slug}/", f"{len(relo_):,} jobs with relocation support")]
        lists_ = [(u, t) for u, t in lists_ if (OUT / u / "index.html").exists()]
        facts_ = ('<dl class="facts">' + f"<div><dt>Open jobs in the country</dt><dd>{len(cj):,}</dd></div><div><dt>Mention visa sponsorship</dt><dd>{len(visa_):,}</dd></div>"
                  f"<div><dt>Mention relocation support</dt><dd>{len(relo_):,}</dd></div>"
                  + (f"<div><dt>Median advertised pay</dt><dd>{money(median(mids_))}</dd></div>" if len(mids_) >= 10 else "") + "</dl>")
        steps = ('<ol class="steps">'
                 f'<li><b>Start with employers that already say they help.</b> {len(cos_)} employers below mention visa sponsorship or relocation in today’s postings in {flg}{e(nm)}. A posting that says so is a better bet than one that is silent.</li>'
                 + (f'<li><b>Read the official rules first.</b> Visa routes, salary thresholds and documents are set by the government and change: check them on <a href="{e(off[1])}" rel="nofollow noopener">{e(off[0])}</a>. This page does not restate them.</li>'
                    if off else f'<li><b>Read the official rules first.</b> Visa routes, salary thresholds and documents are set by the government of {flg}{e(nm)} and change: check them on its official immigration website. This page does not restate them.</li>')
                 + "<li><b>Ask in the first call.</b> “Do you sponsor the visa, and what does relocation support include: flights, temporary housing, a lump sum?” The answer saves weeks.</li>"
                 + f'<li><b>Count the cost of the move.</b> Put the offer next to the cost of living and the move itself: the <a href="{P}/tools/compare-offers/">offer comparison</a> and the <a href="{P}/tools/salary-converter/">salary converter</a> help.</li>'
                 + f'<li><b>Say it in your resume.</b> One line under your name, for example “Open to relocating to {e(cname_.get(c, c))}; need visa sponsorship”, answers the recruiter’s first question. The <a href="{P}/resume/">resume builder</a> has a place for it.</li></ol>')
        qa_ = [(f"Which companies sponsor visas in {nm}?", (f"In today’s postings in {nm}, the employers that mention visa sponsorship most are {', '.join(co for co, _ in Counter(j['company'] for j in visa_).most_common(5))}. "
                 if visa_ else "None of today’s postings mention visa sponsorship. ") + "A posting that does not mention it may still sponsor: ask."),
               (f"How many jobs in {nm} offer relocation support?", f"{len(relo_):,} of today’s {len(cj):,} open jobs in {nm} here mention relocation support, and {len(visa_):,} mention visa sponsorship. Counted on {fdate(TODAY)}."),
               (f"Where is the official information about work visas for {nm}?", (f"On {off[0]}: {off[1]}" if off else f"On the official immigration website of the government of {nm}.") + " Rules and salary thresholds change, so check there before you apply.")]
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        flagged = lambda t: e(t).replace(e(nm), flg + e(nm))      # a country is never shown without its flag
        rl_rows.append((slug, c, nm, len(both), len(cj)))
        lang_ = {"DE": "German", "AT": "German", "CH": "German", "NL": "Dutch", "FR": "French", "ES": "Spanish", "IT": "Italian", "PT": "Portuguese", "PL": "Polish", "SE": "Swedish",
                 "DK": "Danish", "NO": "Norwegian", "FI": "Finnish", "CZ": "Czech", "JP": "Japanese", "KR": "Korean", "BR": "Portuguese", "MX": "Spanish", "TW": "Chinese", "IL": "Hebrew"}.get(c)
        txt_ = lambda j: " ".join((j["title"], j.get("excerpt") or "", j.get("desc") or ""))
        n_lang = sum(1 for j in cj if re.search(rf"\b{lang_}\b", txt_(j), re.I)) if lang_ else 0
        cur_ = {"GB": "£"}.get(c) or ("€" if c in {"DE", "AT", "NL", "FR", "ES", "IT", "PT", "IE", "FI", "BE", "LU", "GR", "SK", "SI", "EE", "LV", "LT", "CY", "MT", "HR"} else "")
        lm_ = sorted(m_ for j in cj if (m_ := local_mid(j.get("salary"), cur_))) if cur_ else []
        kind_p = {sl_: r_ for _, sl_, r_ in PLACES}
        cities_ = [(p_, k_) for p_, k_ in Counter(p_ for j in cj for p_ in j["places"] if p_ != slug and isinstance(kind_p.get(p_), tuple) and p_ in PLACE_LIVE).most_common(6)]
        roles_txt = ", ".join(f"{rlow(rn)} ({k})" for k, _, rn in roles_[:5])
        qa_ = [(f"How can a foreigner get a job in {nm}?", f"Start with the {len(both):,} open jobs in {nm} whose postings mention visa sponsorship or relocation help: those employers have said they hire from abroad. "
                f"Check the official visa rules, say in your resume that you need sponsorship, and ask about relocation support in the first call. The five steps are above.")] + qa_
        if roles_txt: qa_.append((f"What jobs are in demand in {nm} for foreigners?", f"Among today’s postings that mention visa sponsorship or relocation: {roles_txt}. Counted by job title on {fdate(TODAY)}."))
        if lang_ and cj:
            qa_.append((f"Can I work in {nm} if I only speak English?", f"Often, in tech and international companies: {len(cj) - n_lang:,} of the {len(cj):,} open postings in {nm} here do not mention {lang_} at all, "
                        f"while {n_lang:,} do, as a requirement or a plus. Read the language line of each posting."))
        if len(lm_) >= 10:
            qa_.append((f"What do jobs in {nm} pay?", f"{len(lm_):,} open postings in {nm} state a yearly range in {'pounds' if cur_ == '£' else 'euros'}: the median midpoint is {cur_}{median(lm_):,.0f}, the middle half {cur_}{lm_[len(lm_) // 4]:,.0f} to {cur_}{lm_[3 * len(lm_) // 4]:,.0f}."
                        + (f" Postings in US dollars: median {money(median(mids_))}." if len(mids_) >= 10 else "")))
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        facts_ = facts_.replace("</dl>", (f"<div><dt>Do not mention {lang_}</dt><dd>{len(cj) - n_lang:,}</dd></div>" if lang_ else "")
                                + (f"<div><dt>Median pay stated in {'pounds' if cur_ == '£' else 'euros'}</dt><dd>{cur_}{median(lm_):,.0f}</dd></div>" if len(lm_) >= 10 else "") + "</dl>")
        city_row = ("<p>" + " · ".join(f'<a href="{P}/locations/{p_}/">{e(PLACE_NAME.get(p_, p_))} · {k_:,} jobs</a>' for p_, k_ in cities_) + "</p>") if cities_ else ""
        page(f"relocate/{slug}/", f"Jobs in {nm[0].upper() + nm[1:]} for Foreigners: {len(both):,} Visa & Relocation Jobs | {SITE}",
             f"Moving to {nm} for a job: {len(visa_):,} open jobs mention visa sponsorship and {len(relo_):,} relocation support today. The employers, the kinds of work, the pay and the official visa site.",
             crumbs(("Relocation guides", "relocate/"), (cname_.get(c, c), "")) + f'<h1>Work and relocate to {flg}{e(nm)}: <span class="hl">{len(both):,} jobs that help you move</span></h1>'
             f'<p class="lead">Today’s open jobs in {flg}{e(nm)} that mention visa sponsorship or help with relocation, counted from employers’ own careers pages: who offers it, for which work, what it pays, and where to read the official rules.</p>'
             + facts_
             + section("Employers that mention visa sponsorship or relocation", '<ul class="tiles">' + "".join(tile(f"companies/{slugify(co)}/", co, k, True) for co, k in cos_) + "</ul>")
             + (section("The kinds of work they hire for", '<div class="hbars">' + "".join(
                 f'<a href="{P}/roles/{sr}/"><span class="hn">{e(rn)}</span><span class="hb"><i style="width:{max(4, round(100 * k / roles_[0][0]))}%"></i></span><span class="hc">{k} jobs</span></a>' for k, sr, rn in roles_) + "</div>") if roles_ else "")
             + (section(f"Cities in {cname_.get(c, c)} with the most open jobs", city_row) if city_row else "")
             + section(f"Five steps to a job in {cname_.get(c, c)}", steps)
             + section("The newest of these jobs", '<ul class="jobs">' + "".join(card(j) for j in newest) + "</ul>"
                       + ("<p>" + " · ".join(f'<a href="{P}/{u}">{e(t)}</a>' for u, t in lists_) + "</p>" if lists_ else ""))
             + section(f"Questions about relocating to {cname_.get(c, c)}", '<dl class="qa">' + "".join(f"<div><dt>{flagged(q_t)}</dt><dd>{flagged(a_t)}</dd></div>" for q_t, a_t in qa_) + "</dl>")
             + f'<p class="note">Counted from the open postings on {fdate(TODAY)}, read from employers’ own careers pages. “Mentions visa sponsorship” means the posting says so; {rem_}% of these jobs can also be done remotely. Not legal advice.</p>', head=ld_)
    if rl_rows:
        page("relocate/", f"Relocation Guides: Jobs with Visa Sponsorship in {len(rl_rows)} Countries | {SITE}",
             f"Jobs that help you move abroad, country by country: {', '.join(cname_.get(c, c) for _, c, _, _, _ in rl_rows[:6])} and more. The employers that sponsor visas, the work they hire for and the official visa sites.",
             crumbs(("Relocation guides", "")) + f'<h1>Relocation guides: <span class="hl">{len(rl_rows)} countries, with today’s jobs</span></h1>'
             '<p class="lead">For people who want to work abroad: pick a country to see which employers mention visa sponsorship or relocation help in today’s postings, the work they hire for, the pay and the official visa site.</p>'
             + '<ul class="tiles">' + "".join(f'<li><a class="tile" href="{P}/relocate/{sl}/"><span class="n">{fl(c)}{e(cname_.get(c, c))}</span><span class="c">{k:,} jobs</span></a></li>' for sl, c, _, k, _ in sorted(rl_rows, key=lambda x: -x[3])) + "</ul>"
             + f'<p class="note">Also: <a href="{P}/perks/visa-sponsorship/">all jobs with visa sponsorship</a> · <a href="{P}/perks/relocation/">all jobs with relocation support</a></p>')

    # "Jobs Every Hour vs <job site>": fair comparisons, every fact about the other site sourced and dated (compare_sites.py).
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
             + act_row("jobs/", f"Search {len(active):,} open jobs here", note="Free, no account needed.")
             + f'<p class="vs-pick"><b>In short:</b> {e(x["pick"])}</p>'
             + section(f"{x['name']} and {ours}, side by side", table_)
             + '<div class="vs-two"><div><h2>Where ' + e(x["name"]) + ' is better</h2><ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in x["them_better"]) + "</ul></div>"
               '<div><h2>Where ' + e(ours) + ' is better</h2><ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in x["us_better"]) + "</ul></div></div>"
             + section(f"Questions about {x['name']} and {ours}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in vs_qa) + "</dl>")
             + section("Sources", vs_src(x) + f'<p class="note">Facts about {e(ours)} are from this site on {fdate(TODAY)}. A fact that is wrong or out of date can be reported from the <a href="{P}/about/">About page</a>; it is corrected or removed.</p>'), head=ld_)
    # "<site> vs <site>" and "<site> alternatives": the owner asked for compare pages "with all websites" (as Indeed's compare pages),
    # and people search these between the big names. Only the facts compare_sites.py holds with a source, side by side; no verdict.
    site_pairs = []
    def strong_(x):        # a site's strengths without the sentences that compare it with this site ("Our self-serve posting is not open yet")
        return [t for t in (" ".join(y for y in re.split(r"(?<=\.)\s+", t0) if not re.search(r"\b(our|we|us)\b", y, re.I)) for t0 in x["them_better"]) if t]
    for i_, a_ in enumerate(VS):
        for b_ in VS[i_ + 1:]:
            ra = {q_: t_ for q_, t_, _ in a_["rows"]}; rb = {q_: t_ for q_, t_, _ in b_["rows"]}; ru = {q_: u_ for q_, _, u_ in a_["rows"] + b_["rows"]}
            common = [q_ for q_, _, _ in a_["rows"] if q_ in rb]
            if len(common) < 3: continue
            sl = f"{a_['slug']}-vs-{b_['slug']}"
            site_pairs.append((sl, a_, b_))
            table_ = ('<div class="tablewrap"><table class="vs-t four"><tr><th></th><th>' + e(a_["name"]) + "</th><th>" + e(b_["name"]) + "</th><th>" + e(compare_sites.OUR_NAME) + "</th></tr>"
                      + "".join(f"<tr><th>{e(q_)}</th><td>{e(ra[q_])}</td><td>{e(rb[q_])}</td><td>{e(ru[q_])}</td></tr>" for q_ in common) + "</table></div>")
            pq = [(f"What is the difference between {a_['name']} and {b_['name']}?", a_["what"] + " " + b_["what"])]
            if "Who pays" in common: pq.append((f"Who pays on {a_['name']} and on {b_['name']}?", f"{a_['name']}: {ra['Who pays']} {b_['name']}: {rb['Who pays']}"))
            if "Where you apply" in common: pq.append((f"Where do you apply on {a_['name']} and on {b_['name']}?", f"{a_['name']}: {ra['Where you apply']} {b_['name']}: {rb['Where you apply']}"))
            sa_, sb_ = strong_(a_), strong_(b_)
            if sa_ and sb_:
                pq.insert(1, (f"Which is better, {a_['name']} or {b_['name']}?", f"It depends on what you need; this page ranks neither. Where {a_['name']} is strong: {sa_[0]} "
                              f"Where {b_['name']} is strong: {sb_[0]} The table above puts the sourced facts side by side."))
            short_ = lambda x_: slugify(re.sub(r"\s+jobs$", "", x_["name"], flags=re.I))
            for al_ in {f"{short_(a_)}-vs-{short_(b_)}", f"{short_(b_)}-vs-{short_(a_)}", f"{b_['slug']}-vs-{a_['slug']}"} - {sl}:
                write(f"vs/{al_}/", f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(a_["name"])} vs {e(b_["name"])}</title><link rel="canonical" href="{FULL}/vs/{sl}/">'
                      f'<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={P}/vs/{sl}/"></head><body><p><a href="{P}/vs/{sl}/">{e(a_["name"])} vs {e(b_["name"])}</a></p></body></html>', sitemap=False)
            ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in pq]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
            src_ = dict(a_); src_["sources"] = a_["sources"] + b_["sources"]
            page(f"vs/{sl}/", f"{a_['name']} vs {b_['name']}: Who Pays, Where You Apply ({fdate(TODAY, False)}) | {SITE}",
                 f"{a_['name']} and {b_['name']} side by side: " + ", ".join(q_.lower() for q_ in common[:4]) + ". Every fact comes with its source and the date it was read.",
                 crumbs(("Compared with other job sites", "vs/"), (f"{a_['name']} vs {b_['name']}", "")) + f'<h1>{e(a_["name"])} vs {e(b_["name"])}: <span class="hl">the facts side by side</span></h1>'
                 f'<p class="lead">{e(a_["what"])} {e(b_["what"])} Below, what each one says about itself, with the source of every fact. The third column shows how {e(compare_sites.OUR_NAME)} works, for reference.</p>'
                 + act_row("jobs/", f"Search {len(active):,} open jobs here", note="Free, no account needed.")
                 + section(f"{a_['name']} and {b_['name']}, side by side", table_)
                 + '<div class="vs-two"><div><h2>Where ' + e(a_["name"]) + ' is strong</h2><ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in strong_(a_)) + "</ul></div>"
                   '<div><h2>Where ' + e(b_["name"]) + ' is strong</h2><ul class="ticks">' + "".join(f"<li>{e(t)}</li>" for t in strong_(b_)) + "</ul></div></div>"
                 + section(f"Questions about {a_['name']} and {b_['name']}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in pq) + "</dl>")
                 + section("Sources", vs_src(src_) + '<p class="note">A fact that is wrong or out of date can be reported from the <a href="' + P + '/about/">About page</a>; it is corrected or removed.</p>')
                 + f'<p class="note cmpl">More: <a href="{P}/vs/{a_["slug"]}/">{e(a_["name"])} vs {e(compare_sites.OUR_NAME)}</a> · <a href="{P}/vs/{b_["slug"]}/">{e(b_["name"])} vs {e(compare_sites.OUR_NAME)}</a> · '
                   f'<a href="{P}/vs/{a_["slug"]}/alternatives/">{e(a_["name"])} alternatives</a> · <a href="{P}/vs/">all comparisons</a></p>', head=ld_)
    for x in VS:
        others = [y for y in VS if y is not x]
        alt_ = "".join(
            f'<div class="feat"><h3>{e(y["name"])}</h3><p>{e(y["what"])}</p>'
            + "".join(f'<p class="note"><b>{e(q_)}:</b> {e(t_)}</p>' for q_, t_, _ in y["rows"] if q_ in ("Who pays", "Where you apply"))
            + "<p>" + " · ".join(f'<a href="{P}/vs/{sl}/">{e(a_["name"])} vs {e(b_["name"])}</a>' for sl, a_, b_ in site_pairs if {a_["slug"], b_["slug"]} == {x["slug"], y["slug"]})
            + f' · <a href="{P}/vs/{y["slug"]}/">{e(y["name"])} vs {e(compare_sites.OUR_NAME)}</a></p></div>' for y in others)
        page(f"vs/{x['slug']}/alternatives/", f"{x['name']} Alternatives: {len(others) + 1} Job Sites Compared, with Sources | {SITE}",
             f"Alternatives to {x['name']}: {', '.join(y['name'] for y in others[:4])} and more, each with who pays and where you apply, from their own pages. Every fact sourced and dated.",
             crumbs(("Compared with other job sites", "vs/"), (f"{x['name']} alternatives", "")) + f'<h1>{e(x["name"])} alternatives: <span class="hl">{len(others) + 1} job sites, with sources</span></h1>'
             f'<p class="lead">Other places to look for work than {e(x["name"])}, each described from its own pages, with who pays and where you apply. Open a pair to see every fact side by side.</p>'
             + act_row("jobs/", f"Search {len(active):,} open jobs here", note="Free, no account needed.")
             + section(f"{compare_sites.OUR_NAME}", f'<div class="feat"><p>Jobs read {EVERY} from the employers’ own careers pages; you apply on the employer’s site; free for job seekers, no account needed. '
                       f'<a href="{P}/vs/{x["slug"]}/">{e(x["name"])} vs {e(compare_sites.OUR_NAME)}</a></p></div>')
             + section(f"Other alternatives to {x['name']}", '<div class="feats">' + alt_ + "</div>")
             + section("Sources", '<p class="note">Every fact on this page comes from the comparison pages linked above, where each one is listed with its source and the date it was read.</p>'))

    page("vs/", f"{SITE} Compared with Other Job Sites: {len(VS)} Fair Comparisons | {SITE}",
         f"{SITE} side by side with {', '.join(x['name'] for x in VS[:-1])} and {VS[-1]['name']}: who pays, prices, where jobs come from and where you apply. Every fact sourced and dated.",
         crumbs(("Compared with other job sites", "")) + f'<h1>{e(SITE)} compared with <span class="hl">{len(VS)} other job sites</span></h1>'
         '<p class="lead">Each comparison puts the facts side by side, says honestly where the other site is better, and links to the source of every fact about it. Pick the one you use now.</p>'
         + section("Choose a site", '<ul class="tiles">' + "".join(f'<li><a class="tile" href="{P}/vs/{x["slug"]}/"><span class="n">{e(x["name"])} vs {e(SITE)}</span><span class="c">{len(x["rows"])} facts</span></a></li>' for x in VS) + "</ul>")
         + section("Job sites compared with each other", '<ul class="tiles">' + "".join(f'<li><a class="tile" href="{P}/vs/{sl}/"><span class="n">{e(a_["name"])} vs {e(b_["name"])}</span></a></li>' for sl, a_, b_ in site_pairs) + "</ul>")
         + section("Alternatives", '<ul class="tiles">' + "".join(f'<li><a class="tile" href="{P}/vs/{x["slug"]}/alternatives/"><span class="n">{e(x["name"])} alternatives</span></a></li>' for x in VS) + "</ul>"))

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
             ("What should I do after the quiz?", "Open “How to become…” for the field you pick: it lists the skills employers name first and the jobs open to beginners today."),
             # "free career quiz" (checked 15 Nov 2026): people also search "for adults", "for students", "no sign up"; top results state questions and minutes
             ("Is this career quiz for adults or for students?", f"Both. The {len(QZ)} questions ask what you enjoy and how you like to work, not your age or degree, so they fit a student choosing a first job "
              "and an adult changing careers alike. The results show jobs open to beginners as well as the rest."),
             ("How long does the career quiz take?", f"About two minutes: {len(QZ)} questions with a few answers each, and the results appear at once."),
             ("How accurate is a career quiz?", "A quiz narrows the choice; it cannot decide for you. That is why each result here comes with today’s open jobs, what they pay and how many take beginners, "
              "so you can check the fit against real postings before you spend time on training.")]
    qz_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_t, "acceptedAnswer": {"@type": "Answer", "text": a_t}} for q_t, a_t in qz_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("career-quiz/", f"Free Career Quiz: {len(QZ)} Questions, 2 Minutes, No Sign-Up | {SITE}",
         "A free career quiz with seven plain questions. It shows the three fields of work that fit you best, with today’s open jobs, jobs open to beginners and median pay. No email, no sign-up.",
         crumbs(("Career quiz", "")) + '<h1>Which job fits me? <span class="hl">A seven-question career quiz</span></h1>'
         '<p class="lead">Seven plain questions about what you enjoy, what you already do well and how you like to work. You get the three fields that fit you best, with how many jobs they have today and how to get in. No email, no sign-up: your answers stay in your browser.</p>'
         f'<form id="qz" class="qz">{qz_html}<p><button class="btn primary" type="submit">Show my best fits</button></p></form>'
         f'<section class="sec qz-out" id="qz-out" aria-live="polite" hidden></section><script type="application/json" id="qz-data">{qz_data}</script>{qz_js}'
         + section("Questions about the career quiz", '<dl class="qa">' + "".join(f"<div><dt>{e(q_t)}</dt><dd>{e(a_t)}</dd></div>" for q_t, a_t in qz_qa) + "</dl>"), head=qz_ld)

    # Skill self-tests: ten questions per skill, scored in the browser. Planned in ROADMAP section 96 (interview tests for traffic).
    SK_N = Counter(t for j in active for t in j["tags"])
    sk_cards, sk_items = [], []
    SQL_SCHEMA = ("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, country TEXT, joined DATE);"
                  "CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL, ordered DATE);"
                  "INSERT INTO customers VALUES (1,'Ana','Spain','2025-01-10'),(2,'Ben','USA','2025-02-03'),(3,'Chloe','France','2025-02-20'),(4,'Dev','India','2025-03-05'),"
                  "(5,'Emma','USA','2025-03-18'),(6,'Farid','UAE','2025-04-01'),(7,'Gia','Spain','2025-04-22');"
                  "INSERT INTO orders VALUES (1,1,120,'2025-02-01'),(2,1,80,'2025-03-15'),(3,2,200,'2025-02-10'),(4,3,45,'2025-03-01'),(5,3,60,'2025-03-20'),"
                  "(6,3,30,'2025-04-02'),(7,5,500,'2025-04-05'),(8,2,150,'2025-04-10'),(9,7,90,'2025-05-01'),(10,5,75,'2025-05-03');")
    SQL_T = [("Beginner", "List the names of customers from the USA, in alphabetical order.", "SELECT name FROM customers WHERE country = 'USA' ORDER BY name;"),
             ("Beginner", "How many orders are there in total? Return one number.", "SELECT COUNT(*) FROM orders;"),
             ("Intermediate", "For each customer who has ordered, show the name and the total amount spent, largest first.",
              "SELECT c.name, SUM(o.amount) AS total FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name ORDER BY total DESC;"),
             ("Intermediate", "List the names of customers who have never placed an order.", "SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id WHERE o.id IS NULL ORDER BY c.name;"),
             ("Intermediate", "Show each country with more than one customer, and how many customers it has.", "SELECT country, COUNT(*) AS n FROM customers GROUP BY country HAVING COUNT(*) > 1 ORDER BY country;"),
             ("Advanced", "For every order, show the order id, the customer’s name and the running total of that customer’s spending up to that order (by date).",
              "SELECT o.id, c.name, SUM(o.amount) OVER (PARTITION BY o.customer_id ORDER BY o.ordered) AS running FROM orders o JOIN customers c ON c.id = o.customer_id ORDER BY o.id;")]
    SQL_TASKS = (section("Write the query: six tasks you can run", '<p>A small shop database runs here in your browser: <code>customers(id, name, country, joined)</code> and '
                         '<code>orders(id, customer_id, amount, ordered)</code>, 7 customers and 10 orders. Write a query, press Run, and the page checks your rows against the expected ones '
                         '(column names may differ; the order of rows counts only where the task asks for one). The database engine is fetched the first time you press Run; nothing you write is sent anywhere.</p>'
                         + "".join(f'<div class="card sqlt" data-i="{i_}" style="margin:12px 0"><p><b>{i_ + 1}. {e(lv_)}.</b> {e(t_)}</p>'
                                   f'<textarea class="sqlq" rows="3" spellcheck="false" style="width:100%;font-family:ui-monospace,Menlo,monospace" aria-label="Your query for task {i_ + 1}">SELECT </textarea>'
                                   f'<p><button class="btn primary sm sqlrun" type="button" style="margin-top:6px">Run</button> <button class="btn ghost sm sqlshow" type="button" style="margin-top:6px">Show a solution</button></p>'
                                   '<div class="sqlout" aria-live="polite"></div></div>' for i_, (lv_, t_, _) in enumerate(SQL_T)))
                 + '<script type="application/json" id="sql-data">' + json.dumps({"schema": SQL_SCHEMA, "sol": [x[2] for x in SQL_T], "ord": [True, False, True, False, False, False]},
                                                                                  ensure_ascii=False).replace("</", "<\\/") + "</script>"
                 + r"""<script>(function(){var D=JSON.parse(document.getElementById('sql-data').textContent),db=null,V='https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/';
var esc=function(x){return String(x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
function load(){return new Promise(function(ok,no){if(db)return ok(db);var s=document.createElement('script');s.src=V+'sql-wasm.js';s.onload=function(){initSqlJs({locateFile:function(f){return V+f;}}).then(function(S){db=new S.Database();db.run(D.schema);ok(db);},no);};s.onerror=no;document.head.appendChild(s);});}
function rows(q){var r=db.exec(q);return r.length?r[r.length-1]:{columns:[],values:[]};}
function table(r){if(!r.columns.length)return '<p class="note">No rows.</p>';return '<div class="tablewrap"><table><tr>'+r.columns.map(function(c){return '<th>'+esc(c)+'</th>';}).join('')+'</tr>'+r.values.slice(0,30).map(function(v){return '<tr>'+v.map(function(x){return '<td>'+esc(x===null?'NULL':x)+'</td>';}).join('')+'</tr>';}).join('')+'</table></div>';}
function key(r,ord){var v=r.values.map(function(x){return JSON.stringify(x.map(function(y){return typeof y==='number'?Math.round(y*100)/100:y;}));});if(!ord)v.sort();return v.join('|');}
document.addEventListener('click',function(ev){var b=ev.target.closest&&ev.target.closest('.sqlrun,.sqlshow');if(!b)return;var box=b.closest('.sqlt'),i=+box.getAttribute('data-i'),out=box.querySelector('.sqlout'),ta=box.querySelector('.sqlq');
if(b.classList.contains('sqlshow')){ta.value=D.sol[i];return;}
out.innerHTML='<p class="note">Running…</p>';load().then(function(){try{var mine=rows(ta.value),want=rows(D.sol[i]),good=key(mine,D.ord[i])===key(want,D.ord[i]);
out.innerHTML=(good?'<p><b>Right.</b> Your rows match the expected result.</p>':'<p><b>Not yet.</b> Your rows differ from the expected '+want.values.length+' row'+(want.values.length===1?'':'s')+'. Compare them below.</p>')+table(mine);}
catch(e){out.innerHTML='<p><b>The query did not run:</b> '+esc(e.message)+'</p>';}},function(){out.innerHTML='<p>The database engine could not be loaded. Check your connection and try again.</p>';});});})();</script>""")
    for qs_, q_ in quiz_pages.QUIZZES.items():
        sk_t = q_["skill"]; sk_slug = TAG_SLUG.get(sk_t, slugify(sk_t)); sk_n = SK_N.get(sk_t, 0)
        sk_med = [(j["usd"][0] + j["usd"][1]) / 2 for j in active if sk_t in j["tags"] and j["usd"]]
        sk_pay = money(median(sk_med)) if len(sk_med) >= 20 else ""
        sk_has = (OUT / "skills" / sk_slug / "index.html").exists()
        n_q = len(q_["qs"]); lv_q = q_.get("levels") or [""] * n_q; tp_q = q_.get("topics") or [""] * n_q
        ihtml = "".join(f'<fieldset class="qz-q"><legend><span>{i + 1}</span>{e(t_)}'
                        + (f' <small class="note" style="font-weight:400;white-space:nowrap">{e(lv_q[i])} · {e(tp_q[i])}</small>' if lv_q[i] else "") + '</legend>' + "".join(
            f'<label><input type="radio" name="q{i}" value="{k}"><span>{e(a_)}</span></label>' for k, a_ in enumerate(o_)) + "</fieldset>" for i, (t_, o_, _, _) in enumerate(q_["qs"]))
        idata = json.dumps({"a": [x[2] for x in q_["qs"]], "w": [x[3] for x in q_["qs"]], "t": tp_q, "n": sk_n, "pay": sk_pay, "name": q_["name"],
                            "skill": f"{P}/skills/{sk_slug}/" if sk_has else "", "jobs": f"{P}/jobs/?skill={quote(sk_t)}"}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        ijs = r"""<script>(function(){var D=JSON.parse(document.getElementById('st-data').textContent),f=document.getElementById('st'),out=document.getElementById('st-out');
var esc=function(x){return String(x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});};
f.addEventListener('submit',function(ev){ev.preventDefault();var ok=0,seen=0,rows='',tp={};
D.a.forEach(function(r,i){var c=f.querySelector('input[name=q'+i+']:checked'),qs=f.querySelectorAll('fieldset')[i],labs=qs.querySelectorAll('label');
labs.forEach(function(l){l.classList.remove('st-ok','st-bad');});labs[r].classList.add('st-ok');
var old=qs.querySelector('.st-why');if(old)old.remove();
var p=document.createElement('p');p.className='st-why';
var tk=(D.t&&D.t[i])||'';if(tk){if(!tp[tk])tp[tk]=[0,0];tp[tk][1]++;if(c&&+c.value===r)tp[tk][0]++;}
if(c){seen++;if(+c.value===r){ok++;p.innerHTML='<b>Right.</b> '+esc(D.w[i]);}else{c.parentNode.classList.add('st-bad');p.innerHTML='<b>Not quite.</b> '+esc(D.w[i]);}}
else{p.innerHTML='<b>Skipped.</b> '+esc(D.w[i]);}
qs.appendChild(p);});
var sh=ok/D.a.length,lv=sh>=0.8?'Ready to be asked about it in an interview':sh>=0.5?'A good base, with some gaps to close':'Worth another week of practice before applying';
var by=Object.keys(tp).map(function(k){return esc(k)+' '+tp[k][0]+'/'+tp[k][1];}).join(' · ');
out.innerHTML='<h2>You got '+ok+' of '+D.a.length+'</h2><p class="lead">'+lv+'. Below each question you can read why the answer is what it is.</p>'+(by?'<p><b>By topic:</b> '+by+'. Study the topics with the fewest right first.</p>':'')+
(D.n?'<p>'+D.n.toLocaleString('en-US')+' open jobs name '+esc(D.name)+' today'+(D.pay?', with a median advertised pay of '+D.pay:'')+'. <a href="'+D.jobs+'">See the jobs</a>'+(D.skill?' · <a href="'+D.skill+'">What employers pair it with</a>':'')+'.</p>':'')+
'<p class="note">This is a self-check of '+D.a.length+' questions, not a certificate. Nothing is sent anywhere.</p><p><button class="btn ghost" type="button" id="st-again">Try again</button></p>';
out.hidden=false;out.scrollIntoView({behavior:'smooth',block:'start'});
document.getElementById('st-again').onclick=function(){f.reset();out.hidden=true;f.querySelectorAll('.st-why').forEach(function(x){x.remove();});f.querySelectorAll('label').forEach(function(l){l.classList.remove('st-ok','st-bad');});window.scrollTo({top:f.offsetTop-80,behavior:'smooth'});};});})();</script>"""
        iqa = [(f"How do I prepare for a {q_['name']} interview?", f"Work through realistic questions, read why each answer is right, then redo the ones you missed. This test has {n_q}, from beginner to advanced, of the kind interviewers commonly ask. Then read the postings: the {sk_n:,} open jobs that name {q_['name']} show what employers expect on top of it." if sk_n else f"Work through realistic questions, read why each answer is right, then redo the ones you missed."),
               (f"Is this {q_['name']} test free?", "Yes. It needs no account and no email, runs in your browser and sends nothing anywhere."),
               ("What does my score mean?", "It is a self-check. 80% or more right means the basics are fresh; half to 80% means a good base with gaps; under half means more practice first. "
                "The result also shows your score by topic, so you know what to study. It is not an official certificate.")] + list(q_.get("qa") or [])
        ild = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": a_, "acceptedAnswer": {"@type": "Answer", "text": b_}} for a_, b_ in iqa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>"
        page(f"skill-tests/{qs_}/", f"{q_['name']} Test: {n_q} Questions with Answers, Beginner to Advanced | {SITE}",
             f"A free {q_['name']} test: {n_q} questions from beginner to advanced that interviewers commonly ask, scored in your browser by topic, with the reason behind every answer. No email, no sign-up.",
             crumbs(("Skill tests", "skill-tests/"), (q_["name"], "")) + f'<h1>{e(q_["name"])} test: <span class="hl">{n_q} questions to check yourself</span></h1>'
             f'<p class="plain"><b>In plain words:</b> {e(q_["plain"])} Answer {n_q} questions, press the button, and see which you got right, why, and your score by topic.</p>'
             + (f'<p class="lead">{sk_n:,} open jobs name {e(q_["name"])} today' + (f', with a median advertised pay of {sk_pay}' if sk_pay else "") + f". {n_q} questions from beginner to advanced, about 10 to 15 minutes, the kind that come up in interviews.</p>" if sk_n else f'<p class="lead">{n_q} questions of the kind that come up in interviews.</p>')
             + f'<form id="st" class="qz">{ihtml}<p><button class="btn primary" type="submit">Check my answers</button></p></form>'
             f'<section class="sec qz-out" id="st-out" aria-live="polite" hidden></section><script type="application/json" id="st-data">{idata}</script>{ijs}'
             + (SQL_TASKS if qs_ == "sql" else "")
             + section("Questions about this test", '<dl class="qa">' + "".join(f"<div><dt>{e(a_)}</dt><dd>{e(b_)}</dd></div>" for a_, b_ in iqa) + "</dl>")
             + '<p class="rel">More tests: ' + " ".join(f'<a href="{P}/skill-tests/{o_}/">{e(quiz_pages.QUIZZES[o_]["name"])}</a>' for o_ in quiz_pages.QUIZZES if o_ != qs_) + f' <a href="{P}/skill-tests/">All tests</a></p>', head=ild)
        sk_cards.append((qs_, q_["name"], q_["plain"], sk_n))
    page("skill-tests/", f"Skill Tests for Job Interviews: SQL, Excel, Python and More | {SITE}",
         "Free tests of 24 questions, beginner to advanced, for the skills employers ask for most: SQL, Excel, Python, JavaScript, React, Linux and Docker. Scored in your browser by topic, with the reason behind each answer.",
         crumbs(("Skill tests", "")) + '<h1>Skill tests: <span class="hl">check yourself before the interview</span></h1>'
         '<p class="plain"><b>In plain words:</b> a skill test is a short quiz. You answer 24 questions about one skill, such as SQL or Excel, and see which answers were right, why, and your score by topic.</p>'
         '<p class="lead">A first interview often starts with questions on the skills listed in the posting. These tests cover the questions that come up most, so you find your gaps at home and not in the call. Free, no sign-up, nothing leaves your browser.</p>'
         '<div class="feats">' + "".join(f'<a class="feat" href="{P}/skill-tests/{s_}/"><h2>{e(nm_)} test</h2><p>{e(pl_)}' + (f" {k_:,} open jobs name it today." if k_ else "") + "</p></a>" for s_, nm_, pl_, k_ in sk_cards) + "</div>"
         f'<p class="note">After the test: <a href="{P}/interview-questions/">interview questions by job</a>, the <a href="{P}/resume/">resume builder</a> and the <a href="{P}/tools/resume-match/">resume match</a>.</p>')

    # Guides: the blog. The owner asked whether the site needs one after looking at the blogs of hh.ru and Indeed. Theirs are written
    # by editors; these are written once and recounted from the open postings on every build, so the figures in them are never old.
    GUIDES = []
    PUBLISHED = "2026-11-13"
    def guide(slug, title, desc, cat, lead, body, prev, more=(), extra_head=""):
        ld_ = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc, "datePublished": PUBLISHED, "dateModified": TODAY,
               "author": {"@type": "Organization", "name": SITE, "url": FULL + "/about/"}, "publisher": {"@type": "Organization", "name": SITE, "logo": {"@type": "ImageObject", "url": FULL + "/og.jpg"}},
               "mainEntityOfPage": f"{FULL}/guides/{slug}/", "image": FULL + "/og.jpg"}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        links = ('<p class="note cmpl">Next: ' + " · ".join(f'<a href="{P}/{u_}">{e(t_)}</a>' for u_, t_ in more) + "</p>") if more else ""
        page(f"guides/{slug}/", f"{title} | {SITE}", desc,
             crumbs(("Guides", "guides/"), (title, "")) + f'<article class="guide"><h1>{e(title)}</h1><p class="stamp">{e(cat)} · figures recounted {fdate(TODAY)} from <b>{n:,}</b> open jobs · <a href="{P}/methodology/">how they are made</a></p>'
             f'<p class="lead">{lead}</p>{body}{links}</article>', head=ld_ + extra_head)
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
          '' + mini([(f["fn"], f["rem"] / f["n"], f'{pc_(f["rem"], f["n"])}%') for f in by_rem]),
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
          '' + mini([(lb, v_, f"{v_:,}") for lb, v_ in age_cols]),
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
          '' + mini([(f["fn"], f["pay"] / f["n"], f'{pc_(f["pay"], f["n"])}%') for f in by_pay]),
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
          '' + mini([(f["fn"], f["ent"], f'{f["ent"]:,}') for f in by_ent]),
          (("entry-level/", "All entry-level jobs"), ("internships/", "Internships"), ("categories/internships-entry-level/", "Internships and first jobs")))

    # 5. skills in demand
    top_sk = skill_counts.most_common(15)
    guide("skills-in-demand", f"The {len(top_sk)} Most In-Demand Job Skills in {TODAY[:4]} (from {n:,} Jobs)",
          f"The 15 skills named in the most open job postings today, each explained in one line: from {top_sk[0][0]} ({top_sk[0][1]:,} jobs) down.", "Skills",
          f"Job postings name tools and methods as if everyone knew them. These are the fifteen named most often in {n:,} open postings, with a plain line for each.",
          "<h2>Asked for in the most postings</h2>" + bars_([(t, k, f"{k:,} jobs · {pc_(k, n)}%", f"skills/{tslug(t)}/") for t, k in top_sk])
          + '<h2>What each one is</h2><dl class="qa">' + "".join(f"<div><dt>{e(t)}</dt><dd>{e(skills_info.plain(t)) or 'No plain description yet.'}</dd></div>" for t, _ in top_sk) + "</dl>"
          + f"<h2>Using this</h2><p>Write the skills you have by the names postings use: screening software looks for the word. The <a href=\"{P}/resume/\">resume builder</a> shows, while you type, how many open jobs ask for each skill it finds in your text.</p>",
          '' + mini([(t, k, f"{k:,}") for t, k in top_sk]),
          (("skills/", "All skills"), ("insights/highest-paying-tech-skills/", "The skills with the highest advertised pay"), ("compare/", "Compare two skills")))

    # 6. levels
    lvl_rows = []
    for lv, lab_, what_ in (("Intern", "Intern", "a placement during studies or straight after, usually for a fixed number of months"), ("Junior", "Junior", "a first full job in the field; the employer expects to teach"),
                            ("", LVL_NAME[""], "most often a mid-level job: able to work alone on ordinary tasks"), ("Senior", "Senior", "years of practice; solves hard problems without being told how, and helps others"),
                            ("Lead", "Lead and above: lead, staff, principal, director", "sets the direction for a team or a large part of the product, with or without managing people")):
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
          '' + mini([(lab_.split(",")[0], md_, money(md_)) for lab_, _, _, md_ in lvl_rows if md_]),
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
    # How the hourly check works: counted from the build's own data, written as a plain account of the method (ROADMAP: engineering-style post).
    ats_name = {"greenhouse": "Greenhouse", "ashby": "Ashby", "lever": "Lever"}
    ats_jobs, ats_cos = Counter(), defaultdict(set)
    for j_ in active:
        k_ = str(j_.get("id", "")).split("-")[0]
        if k_ in ats_name:
            ats_jobs[k_] += 1
            ats_cos[k_].add(j_["company"])
    ats_tab = "".join(f"<tr><td>{ats_name[k_]}</td><td>{ats_cos[k_].__len__():,}</td><td>{v_:,}</td></tr>" for k_, v_ in ats_jobs.most_common())
    n_closed_all = len(archived)
    guide("how-we-check-jobs-every-hour", f"How we check {n:,} job postings every hour",
          f"How the hourly check works: where postings are read, how a closed job is told from an unreadable feed, and what the figures cover. Counted from {n:,} open jobs at {m:,} companies.", "Reading postings",
          f"Every open job on this site is read from the employer’s own hiring system, {m:,} companies in all, " + (f"{m_hourly:,} of them every hour and the rest every four hours." if ROTATING else "each of them every hour.") +
          f" This page describes the check step by step, so you can judge how far to trust what the lists say.",
          '<p class="plain"><b>In plain words:</b> companies publish their open jobs in a hiring system, a program that holds every opening and its application form. '
          "We read what those systems publish, compare it with what we saw the last time and update the lists. Nothing is typed in by hand and nothing is copied from another job site.</p>"
          "<h2>Step 1: read the employer’s own list</h2><p>Three hiring systems cover the companies here. Each publishes a public list of a company’s open jobs, the same list that feeds the “Careers” page of the company.</p>"
          '<div class="tablewrap"><table class="t4"><thead><tr><th>Hiring system</th><th>Companies</th><th>Open jobs</th></tr></thead><tbody>' + ats_tab + "</tbody></table></div>"
          "<h2>Step 2: compare with the last reading</h2><p>A job that is in the list and was not there before is new, and its first-seen time is saved. A job that was in the list and is now missing is closed, and the closing date is saved. "
          f"Closed jobs keep their pages: {n_closed_all:,} closed postings are on file, {closed_today_h:,} of them closed today.</p>"
          "<h2>Step 3: tell a closed job from a list that could not be read</h2><p>If an employer’s list does not load at all, the jobs of that company are left as they were until the next hour. "
          "A job is marked closed only when the list was read and the job was not in it. When a company’s whole list empties at once (20 jobs or more), it is flagged as a probable move to another hiring system rather than as filled jobs, "
          "and those closings stay out of the closing statistics.</p>"
          "<h2>Step 4: read the details by fixed rules</h2><p>Pay, level, skills and remote status are read from the posting by written rules, not guessed. A rule can miss a wording, so “pay not listed” here does not prove the employer hides it. "
          f'The rules are listed on the <a href="{P}/methodology/">methodology page</a>.</p>'
          f"<h2>What the hourly check does not do</h2><p>It does not check that the role is still being filled, only that the employer still lists it. It does not cover companies that hire only through a recruiter or on a site we do not read. "
          f'Of the open postings, {long_all:,} have been listed for {LONG_OPEN} days or more and carry a mark for it; the <a href="{P}/guides/is-this-job-still-open/">guide to old postings</a> says what to do about them.</p>'
          f'<p>The last run, its length and the companies whose lists failed are on the <a href="{P}/status/">data status page</a>.</p>',
          '<span class="ln"><b>Read from the employer</b> · every hour</span>' + skel,
          (("status/", "Is the data fresh?"), ("methodology/", "Methodology"), ("guides/is-this-job-still-open/", "Is this job still open?")))
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
              '' + mini([(f"{d_} days", k, f"{pc_(k, n_od)}%") for d_, k in od_.most_common(4)]),
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
              '' + mini([(lab, k, f"{pc_(k, nd_)}%") for k, lab in th_all[:4]]),
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
              '' + mini([(f"{lb} yrs", k, f"{pc_(k, len(yrs_all))}%") for lb, k in sorted(yb_, key=lambda x: -x[1])[:4]]),
              (("entry-level/", "Entry-level jobs"), ("how-to-become/", "How to become…"), ("guides/job-levels-explained/", "What the level in a title means")))

    # what moving up a level is worth, from advertised pay (the raise guide asked for in the plan)
    pm_ = lambda js__: median([(j["usd"][0] + j["usd"][1]) / 2 for j in js__ if j["usd"]]) if sum(1 for j in js__ if j["usd"]) >= 15 else 0
    fam_js_ = {r_[0]: r_[4] for r_ in fam_rows}
    lad_ = []
    for f_ in big_f:
        js__ = fam_js_.get(f_["fs"], [])
        base_, sen_, lead_ = (pm_([j for j in js__ if j["level"] == lv_]) for lv_ in ("", "Senior", "Lead"))
        if base_ and sen_ and f_["fs"] != OTHER[0] and "Internship" not in f_["fn"]: lad_.append((f_["fn"], f_["fs"], base_, sen_, lead_))
    all_base_, all_sen_ = pm_([j for j in active if j["level"] == ""]), pm_([j for j in active if j["level"] == "Senior"])
    up_ = lambda a_: round(100 * (a_[3] / a_[2] - 1))
    sg_ = lambda a_: (f"+{up_(a_)}%" if up_(a_) > 0 else f"−{-up_(a_)}%" if up_(a_) < 0 else "0%")
    if len(lad_) >= 4 and all_base_ and all_sen_:
        lad_.sort(key=lambda a_: -(a_[3] / a_[2]))
        guide("does-senior-pay-more", "Does a Senior title pay more? Advertised pay by level, field by field",
              f"Senior postings advertise {round(100 * (all_sen_ / all_base_ - 1))}% more than postings with no level in the title overall, but not in every field. The figures by field, to bring when you ask for a raise.", "Pay",
              f"Across all fields, postings that state pay and name Senior in the title advertise a median of {money(all_sen_)} a year, {round(100 * (all_sen_ / all_base_ - 1))}% more than the {money(all_base_)} of postings with no level in the title. "
              f"The step differs by field: {sg_(lad_[0])} in {e(rlow(lad_[0][0]))}, {sg_(lad_[-1])} in {e(rlow(lad_[-1][0]))}. In {sum(1 for a_ in lad_ if a_[3] < a_[2])} of the {len(lad_)} fields counted, Senior postings advertise less than postings with no level.",
              "<h2>How much more a Senior title advertises, by field</h2><p>Each bar is the median pay of postings with Senior in the title as a share of the median of postings that name no level, in fields where both groups have at least 15 postings with a stated yearly range. "
              "</p>"
              + bars_([(a_[0], a_[3] / a_[2], sg_(a_), f"categories/{a_[1]}/") for a_ in lad_])
              + "<h2>The figures behind the bars</h2><div class=\"tablewrap\"><table class=\"t4\"><tr><th>Field</th><th>No level in the title</th><th>Senior</th><th>Lead and above</th></tr>"
              + "".join(f"<tr><td>{e(a_[0])}</td><td>{money(a_[2])}</td><td>{money(a_[3])}</td><td>{money(a_[4]) if a_[4] else '—'}</td></tr>" for a_ in lad_)
              + "</table></div><p class=\"note\">Medians of the middle of each stated range, in US dollars a year. A dash means fewer than 15 postings.</p>"
              "<h2>Using the figures when you ask for a raise</h2><p>A raise request is easier to grant when it names a number and a reason. Employers answer to what the market advertises for the same work, so bring the range for your kind of work and level, "
              "then the results you produced in the last year. Ask in a meeting set for the purpose, not in passing, and ask for a figure inside the range rather than for “more”.</p>"
              f"<p>The <a href=\"{P}/tools/raise-calculator/\">raise calculator</a> shows what a percentage means in money, the <a href=\"{P}/tools/raise-request-email/\">raise request email</a> writes the message, "
              f"and the <a href=\"{P}/salaries/\">salary pages</a> hold the range for your role and level.</p>"
              "<h2>Why Senior does not always pay more</h2><p>A posting with no level in the title can be a manager, a specialist or a mid-level role, and some fields mix very different jobs under one name, so the group with no level can sit above the Senior group. Advertised pay is what an employer offers new hires, not what people already in the job earn. The title is the employer’s word: a Senior at a small company and a Senior at a large one can do very different work.</p>",
              '' + mini([(a_[0], a_[3] / a_[2], sg_(a_)) for a_ in lad_]),
              (("salaries/", "Salary data"), ("guides/job-levels-explained/", "What the level in a title means"), ("tools/raise-calculator/", "Raise calculator")))

    # Career advice: the questions job seekers type most (BLOGS_STUDY.md), each with today's figures, a tool on this site and FAQ markup
    import advice_pages
    adv_desc = [j for j in active if j.get("desc")]
    adv_soft = [("Communication", r"communicat"), ("Working with others", r"collaborat|teamwork|team player"), ("Problem solving", r"problem[- ]solv"),
                ("Attention to detail", r"attention to detail|detail[- ]oriented"), ("Ownership", r"\bownership\b"), ("Self-starter", r"self[- ](?:starter|motivated|directed)"),
                ("Organisation", r"\borgani[sz](?:ed|ational skills)\b"), ("Adaptability", r"adaptab|comfortable with ambiguity"), ("Leadership", r"\bleadership\b"),
                ("Customer focus", r"customer[- ](?:focus|obsess|centric)")]
    adv_soft_n = sorted(((nm_, pc_(sum(1 for j in adv_desc if re.search(rx_, j["desc"], re.I)), len(adv_desc))) for nm_, rx_ in adv_soft), key=lambda x: -x[1])
    adv_mids = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in active if j["usd"])
    adv_ages = sorted(max(0, (datetime.date.fromisoformat(TODAY) - datetime.date.fromisoformat(j["posted"][:10])).days) for j in active if j.get("posted"))
    advice_ctx = {"n": n, "n_desc": len(adv_desc), "soft": adv_soft_n,
                  "skills": [(t_, tslug(t_), pc_(c_, n)) for t_, c_ in skill_counts.most_common(10)],
                  "paid_pct": pc_(sum(bool(j["salary"]) for j in active), n),
                  "med": money(median(adv_mids)) if adv_mids else "–", "p25": money(adv_mids[len(adv_mids) // 4]) if adv_mids else "–", "p75": money(adv_mids[3 * len(adv_mids) // 4]) if adv_mids else "–",
                  "age_med": adv_ages[len(adv_ages) // 2] if adv_ages else 0, "old_pct": pc_(sum(1 for d_ in adv_ages if d_ >= 90), max(1, len(adv_ages))),
                  "entry_n": sum(1 for j in active if j["entry"]), "entry_pct": pc_(sum(1 for j in active if j["entry"]), n)}
    for a_ in advice_pages.ARTICLES:
        guide(a_["slug"], a_["title"], a_["desc"], a_["cat"], a_["lead"], advice_pages.render(a_, advice_ctx, e, P),
              f'<span class="adv-prev">{e(a_["short"][:120].rsplit(" ", 1)[0])}…</span>', a_["more"], extra_head=advice_pages.faq_ld(a_, json))

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
         + section("Where it stands", '<dl class="qa"><div><dt>Built</dt><dd>The site, the hourly collection, the directory of fields and roles, ' + str(len(TOOLS)) + ' tools and a resume builder, rankings and charts, the accounts and payments server with fraud checks and its tests.</dd></div>'
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
    failed_html += (section("Job boards that went empty in the last run", "<p>" + ", ".join(e(x) for x in ST["emptied"]) + ".</p>"
                            '<p class="note">Every posting on these boards disappeared at once. That usually means the employer moved to another hiring system; '
                            'their postings are marked closed and left out of the figures on how long jobs stay open until the new board is added.</p>') if ST.get("emptied") else "")
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
        findings = (f'<ul><li>{R["open"]:,} roles were open at {R["companies"]:,} companies{vs("open")}.</li>'
                    f'<li>{pctf(R["remote"], R["open"])} of them were remote and {pctf(R["with_salary"], R["open"])} stated a salary.</li>'
                    + (f'<li>The median advertised salary was {money(R["median_salary"])}.</li>' if R["median_salary"] else "")
                    + f'<li>The most requested skill was {e(top_skill[0])}, named in {top_skill[1]:,} postings ({pctf(top_skill[1], R["open"])}).</li>'
                    f'<li>{e(top_emp[0])} had the most open roles: {top_emp[1]:,}.</li>'
                    f'<li>{pctf(R["long_open"], R["open"])} of open roles had been up for {LONG_OPEN} days or more.</li></ul>')
        state = ("This month is still running: the page is recounted every day and stops changing after the last day of the month." if k == ym
                 else "This report is final: the figures are the last count of that month and will not change.")
        page(f"reports/{k}/", f"Hiring Report, {mlabel(k)}: jobs, pay, skills | {SITE}",
             f"Hiring in {mlabel(k)}: {R['open']:,} open roles at {R['companies']:,} companies, remote share, advertised pay, most requested skills and biggest employers.",
             crumbs(("Hiring reports", "reports/"), (mlabel(k), "")) + f"<h1>Hiring report: {mlabel(k)}</h1>"
             '<p class="lead">Headlines about the job market contradict each other every week. This report counts what employers actually posted on their own careers pages, nothing else.</p>'
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
             + cite(f"reports/{k}/", f"Hiring report, {mlabel(k)}"))
    page("reports/", f"Hiring Reports by Month — jobs, pay, skills | {SITE}",
         "Monthly hiring reports built from live job postings: open roles, remote share, advertised pay, most requested skills and biggest employers. Free to quote.",
         crumbs(("Hiring reports", "")) + "<h1>Hiring reports, month by month</h1>"
         '<p class="lead">One page per month, with the jobs, the pay, the skills and the employers of that month. A month’s page stops changing when the month ends, '
         'so a figure you quote from it stays where you found it. Free to quote with a link.</p>'
         + (lambda R_, k_: (f'<a class="rep-now" href="{P}/reports/{k_}/"><span class="rep-h"><b>{mlabel(k_)}</b><span>{"so far, updated every hour" if k_ == TODAY[:7] else "final"}</span></span>'
                           '<span class="stats3 st4">'
                           f'<span class="st"><span class="st-l">Open jobs</span><b class="st-v">{R_["open"]:,}</b><span class="st-s">at {R_["companies"]:,} companies</span></span>'
                           f'<span class="st"><span class="st-l">Remote</span><b class="st-v">{round(100 * R_["remote"] / max(1, R_["open"]))}%</b><span class="st-s">{R_["remote"]:,} jobs</span></span>'
                           f'<span class="st"><span class="st-l">State the pay</span><b class="st-v">{round(100 * R_["with_salary"] / max(1, R_["open"]))}%</b><span class="st-s">{R_["with_salary"]:,} jobs</span></span>'
                           f'<span class="st"><span class="st-l">Median advertised pay</span><b class="st-v">{money(R_["median_salary"])}</b><span class="st-s">a year, in US dollars</span></span></span>'
                           + ('<span class="rep-sk"><span class="flabel">Skills asked for most</span>' + "".join(f'<span class="rep-skr"><span>{e(t_)}</span><i style="width:{max(4, round(100 * c_ / R_["skills"][0][1]))}%"></i><b>{c_:,}</b></span>' for t_, c_ in R_["skills"][:6]) + "</span>" if R_.get("skills") else "")
                           + '<u>Read the report</u></a>'))(REPORTS[rep_months[0]], rep_months[0])
         + (section("Earlier months", '<ul class="tiles">' + "".join(tile(f"reports/{k}/", mlabel(k), REPORTS[k]["open"]) for k in rep_months[1:]) + "</ul>"
                    '<p class="note">The number on each tile is the count of open jobs in that month’s report.</p>') if len(rep_months) > 1 else
            '<p class="note">Reports start in November 2026. Each new month gets its own page on the 1st.</p>')
         + section("Studies and tools from the same data", '<div class="tgrid rep-more">'
                   + "".join(f'<a class="tcard" href="{P}/{u}"><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span><i><u>{e(go_)}</u></i></span></a>' for u, t_, d_, go_ in (
                       ("how-long-job-postings-stay-open/", "How long job postings stay open", "Closings seen every hour, open jobs by age, entry-level jobs and the map.", "Read the study"),
                       ("salaries/explorer/", "Salary explorer", "Pay by role, place, skill and level, with the bands and the counts behind them.", "Open the explorer"),
                       ("jobs-that-pay/", "Jobs by hourly pay", "Open jobs from $20 to $100 an hour or more, with each rate a week, a month and a year.", "See the rates"),
                       ("insights/", "Rankings", "Who hires the most, which skills are asked for, where the pay is highest.", "See the rankings")))
                   + "</div>"))

    # Safety: how to tell a real job offer from a fake one, and what this site does about it
    def qa_block(qa):
        html_ = "".join(f"<details class='faq'><summary>{e(q_)}</summary><p>{e(a_)}</p></details>" for q_, a_ in qa)
        return html_, ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    # "how to spot a fake job offer" (checked 15 Nov 2026): Google's answer adds free email addresses, early requests for an SSN or bank
    # details, and the fake-check scheme; People also ask "What are red flags in a job offer?", "Can an offer letter be fake?",
    # "What does a fake job posting look like?"
    safety_qa = [("What are red flags in a job offer?", "Being asked to pay for anything; pay far above the market for simple work; an offer without a live interview; an interview held only by "
                  "text on Telegram or WhatsApp; a recruiter writing from a free email address (Gmail, Outlook, Yahoo) instead of the company’s domain; a request for your Social Security number "
                  "or bank details before a formal offer; a check you are told to deposit and partly send back, or spend on gift cards or equipment."),
                 ("Can an offer letter be fake?", "Yes. Check the sender’s address against the company’s own domain, call the company on the number on its website (not the one in the letter), "
                  "and look for the job on its careers page. A real offer comes after real interviews, and it never asks you to pay."),
                 ("What does a fake job posting look like?", "Vague duties, no company name or address, very high pay for simple tasks, pressure to reply today, and a contact by chat app or a link that "
                  "is not the company’s own site. Every job on this site links to the employer’s own careers page, so you can see where it comes from."),
                 ("Will a real employer ever ask me to pay?", "No. A real employer does not charge for applying, training, equipment, a background check or a visa. A request for money at any stage of hiring is the clearest sign of a scam."),
                 ("Is it safe to do a take-home test?", "Usually, if it comes through the company’s own hiring process. Do not run code or open files from someone you cannot tie to the company’s official site, and never on a machine that holds your wallets, keys or work credentials."),
                 (f"Does {SITE} check employers?", f"Every listing on {SITE} is read from the employer’s own hiring system and links to that posting, and it is re-checked every hour. {NO_ANON}. We cannot vouch for what happens after you leave the site, so the checks on this page still apply."),
                 ("What if the recruiter wants to continue in a messenger?", "Ask to continue by email from the company’s domain or through its hiring system. A recruiter who refuses, or whose address does not match the company’s site, is not acting for that company.")]
    safety_faq, safety_ld = qa_block(safety_qa)
    page("safety/", f"How to Spot a Fake Job Offer: Red Flags and Checks | {SITE}",
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
                   + (f"<b>How we contact people:</b> we do not. Nobody from {e(SITE)} will ever write to you first, offer you a job, or ask for money, documents or wallet access. Our only contacts are {contact}, and {mail_a("abuse")} for reports of scam jobs and fake recruiters.</p>" if contact else
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
         + section("What is free, with no account?", "<ul class=\"ticks\"><li>Searching, every filter, salary data and all rankings.</li><li>Opening any job and applying: you always go to the employer’s own page, and we take nothing for it.</li>"
                   "<li>Saving jobs, tracking applications and saved searches, kept in your browser.</li><li>The resume builder and every tool in the tools section.</li><li>Widgets, badges, the data files and the API.</li></ul>")
         + section("What will this site never do?", "<ul class=\"crosses\"><li>Charge you to apply for a job.</li><li>Ask for your phone number, or call you.</li>"
                   + ("<li>Show your resume to any employer unless you tick “Let employers find my resume”. Even then your name and contact details go to an employer only "
                      "when you accept its request, and one click deletes your resume for good.</li>" if CFG["talent_db"] else "")
                   + ("<li>Sell or pass on personal data. The address you give for job alerts is used for those letters and nothing else.</li>" if CFG["api_url"] else
                      "<li>Sell or pass on personal data. Job seekers have no accounts here, so there is nothing to sell.</li>") + "<li>Send you email you did not ask for.</li>"
                   "<li>Hold a job back for paying members. Every listing is public the moment we have it.</li><li>Renew a payment by itself. Anything paid is a single payment for a stated period.</li><li>Show a job as open after we know it is closed, or hide where a listing came from.</li>"
                   "<li>Publish invented reviews, numbers, partners or deadlines.</li></ul>")
         + section("What costs money, and for whom?", f'<p>Employers can pay to place a job or a company more prominently; the prices are public on the <a href="{P}/post-a-job/">employers page</a>. '
                   f'Job seekers pay nothing today. An optional paid set of email alerts and AI resume tools, <a href="{P}/plus/">Plus</a>, is planned; it will not unlock any listing, and what it includes and what it costs will be published in full before anything is sold.</p>')
         + section("How can I check that you keep to this?", f'<p>The <a href="{P}/status/">data status page</a> shows what the latest update did. The <a href="{P}/methodology/">methodology</a> explains every label and number. '
                   f'The <a href="{P}/privacy/">privacy page</a> lists what is stored and where. The site’s code is public.</p>'))

    # Privacy and terms
    # Privacy. The sections about job alerts and accounts appear in the same build that switches them on (config.json api_url, the server in
    # server/), so the page never describes something that is not running, and is updated before it runs (the promise under "Changes").
    api_on = bool(CFG["api_url"])
    h2p = lambda text, id_="": "<h2 class='h2s'" + (' id="' + id_ + '"' if id_ else "") + ">" + text + "</h2>"
    priv_who = mail_a("privacy") if MAIL.get("privacy") else "the address on the about page"
    priv_server = (
        h2p("Job alerts by email: what we keep", "alerts")
        + "<p>When you ask for job alerts we keep your email address and the search you chose: the words, the category, the place, remote only or not, the least pay, "
          "and daily or weekly. We also keep when you asked and confirmed, when the last letter went, how many letters were sent, and up to which moment jobs were already offered to you (a time, not a list of jobs).</p>"
          "<ul><li><b>Double opt-in.</b> Nothing is sent until you open the confirmation link we mail to the address and press the button on that page. "
          "A request nobody confirms is deleted after 7 days, and one address gets at most three confirmation letters a day, whoever asks for them. "
          "The confirmation letter says what the alert is for, but leaves the words of the search out of its subject line.</li>"
          "<li><b>The letters.</b> Plain text, at most 20 jobs, no images, no tracking pixel, and the links are not counted: we do not know whether you opened a letter or what you clicked in it.</li>"
          "<li><b>Unsubscribing.</b> Every letter has a link that stops it in one click (mail apps that offer an Unsubscribe button use the same link). The alert is then deleted, not kept.</li>"
          "<li><b>What else the address is used for.</b> Nothing. It is not added to any other list, shown to employers, sold or passed on.</li></ul>"
        + h2p("Accounts for employers and job seekers: what we keep")
        + "<p>Searching and applying need no account. If you open one, we keep your email address; your password as a salted hash (PBKDF2), never the password itself; "
          "a company name and the company domain the account is tied to, and how that domain was proved (an email on it, a DNS record or a file); "
          "the name, member id and verified email LinkedIn gives us if you choose to attach a LinkedIn profile; the address, name and account id Google gives us if you sign in with Google; "
          "the saved jobs, statuses and searches you choose to keep in sync between your devices; the colleagues you add to your company’s team; the jobs you post, with the notes of the person who reviewed them; "
          "the company pages you claim; and how many times a month you used paid AI tools, if you have them (counts only, never what you sent).</p>"
          "<p>To keep accounts safe we also keep a hash of the session key while you are signed in (30 days at most), one-time links to confirm an address or set a new password "
          "(only their hash, for 24 hours and 30 minutes), and a hash of the browser description you signed in from, so that a sign-in from a new browser can be reported to you by email.</p>"
        + h2p("Counts, reports and limits")
        + "<p>For jobs posted here and for companies that manage their page here, we count views of a job page and clicks on “Apply”: two numbers per job and day. "
          "To count a visitor once a day, a salted hash of the IP address is kept until the end of that day (UTC), then deleted. "
          "A report about a job keeps its reason, the note you write, and a salted hash of the IP address, so one address counts once. "
          "Limits on how often something can be done (signing in, signing up, asking for a link, posting, reporting) are counters kept under the IP address, "
          "the email address or a hash of them, and are deleted when their time is over: mostly an hour, a day for the limit on confirmation letters to one address. "
          "The web server’s own log (IP address, page, time) is kept for 14 days for security.</p>"
        + h2p("The record of letters we send")
        + "<p>For every letter the site sends (an alert, a confirmation link, a new password link, a sign-in notice) we keep for 30 days: the address, the time, what kind of letter it was, "
          "and the answer of the mail server. Never the subject or the text.</p>"
        + ((h2p("Your resume in the resume database, only if you tick it", "resumes")
            + "<p>The resume builder keeps your resume in your browser. Only if you open an account and tick “Let employers find my resume” is it stored on our server, "
              "with the words you agreed to and when. Employers whose account is tied to their company’s domain can then find it, but without your name, email, phone or links, "
              "without the names of your employers, and with email addresses, phone numbers and web addresses taken out of the text (you may choose to show your name or your employers). "
              "An employer gets your name and contact details only when you accept its request; if you decline or do not answer in 14 days, it learns nothing about you.</p>"
              "<ul><li><b>You decide where it shows:</b> the kinds of work and the places you want, and companies that must never see it (your current employer, say).</li>"
              "<li><b>Pause</b> hides it and keeps it. <b>Delete</b> removes it from our server at once, with every request about it. An employer whose request you accepted keeps what it was given.</li>"
              "<li><b>Letters:</b> you get one when an employer asks; nothing else.</li></ul>") if CFG["talent_db"] else "")
        + h2p("Why we may keep it")
        + "<ul><li><b>Job alerts:</b> your consent, given by confirming the link. You can withdraw it at any time by unsubscribing; letters already sent are not affected.</li>"
          + ("<li><b>The resume database:</b> your consent, given by the tick. You can withdraw it at any time by pausing or deleting your resume.</li>" if CFG["talent_db"] else "")
          + ("<li><b>Accounts and posting jobs:</b> to provide what you asked for when you opened the account.</li>"
          "<li><b>Fraud checks, reports, limits, sign-in notices and the record of letters:</b> our legitimate interest in keeping scams off the site and accounts safe. You can object; we then weigh it case by case.</li>"
          "<li><b>Payments,</b> once they exist: the law, which says how long records of payments are kept. Nothing is sold yet.</li></ul>")
        + h2p("How long it is kept")
        + "<ul><li>A job alert: until you unsubscribe or ask us to delete it. An unconfirmed one: 7 days.</li><li>An account: until you ask us to delete it.</li>"
        + ("<li>A resume in the resume database: until you delete it; a request to contact you: as long as your resume is there.</li>" if CFG["talent_db"] else "")
        + "<li>The record of letters: 30 days. The web server’s log: 14 days.</li><li>Visitor hashes for counting views: until the end of the day. Limit counters: an hour, or a day for confirmation letters.</li>"
          "<li>Sessions: 30 days. Confirmation links: 24 hours. New password links: 30 minutes.</li></ul>"
        + h2p("Who else handles it")
        + "<p>The data is kept on our own server, a virtual server rented from Hostinger. Requests to the site pass through Cloudflare, which protects it from attacks and, "
          "like any network in between, sees your IP address and the address of the page. Letters are sent through the mail servers of Beget (Beget LLC, Russia), which also "
          "keeps the mailboxes you can write to. These companies may process the data outside your country. Fonts, scripts and images are served from this site, not from other companies. "
          "When you press “Apply”, you go to the employer’s own site, which has its own privacy policy.</p>"
        + h2p("Seeing, correcting and deleting your data")
        + f"<p>You can stop any alert yourself from any of its letters. On the account page you can download everything we keep about your account and delete the account yourself. "
          f"For anything else, write to {priv_who} from the address concerned: you can ask what we keep about it, "
          "have it corrected, have it deleted, or object to its use. We answer within 30 days, usually much sooner. Deleting removes the alerts of that address, the record of letters to it, the limit counters kept under it, "
          "and the account with its sessions and company pages; jobs it posted come down. Records of payments, once there are any, are kept as long as the law requires. "
          "You can also complain to the data protection authority where you live.</p>")
    page("privacy/", f"Privacy | {SITE}", ("What this site keeps: no tracking cookies, saved jobs stay in your browser; for job alerts and accounts your email and what you asked for, deleted on request."
                                           if api_on else "What this site stores and what it does not: no accounts, no tracking cookies, your saved jobs stay in your browser."),
         crumbs(("Privacy", "")) + "<h1>Privacy</h1>"
         + ("<p class=\"lead\">Short version: searching and applying need no account, there are no tracking cookies, and your saved jobs never leave your browser. "
            "If you ask for job alerts or open an account, we keep your email address and what you asked for, use them for that and nothing else, and delete them when you ask.</p>" if api_on else
            "<p class=\"lead\">Short version: we do not ask for an account, we do not set tracking cookies, and your saved jobs never leave your browser.</p>")
         + "<h2 class='h2s'>What is stored in your browser</h2><p>Saved jobs, application statuses and notes, saved searches, followed companies, hidden jobs and companies, words you chose to leave out of results, "
         "recently viewed jobs, your skill profile, the resume you typed into the resume builder, what you entered into the free tools, and the light or dark theme. All of it is kept in your browser's local storage on this device and is not sent to us. "
         f'You can download or erase it on the <a href="{P}/my-jobs/">My jobs</a> page; each tool has its own Clear button; clearing your browser data removes everything.</p>'
         "<h2 class='h2s'>Practising out loud</h2><p>On the interview questions pages the page can read a question aloud and listen to your answer. "
         "It uses your browser’s own speech service: in Chrome that service is run by Google and in Edge by Microsoft, so your words go to them to be "
         "turned into text, under their terms. This site receives none of it and keeps nothing. Typing the answer instead sends nothing anywhere.</p>"
         "<h2 class='h2s'>Your resume</h2><p>A resume you paste on the “For you” page or into a tool is read by a script in your browser. It is never uploaded. The resume builder and the tools keep what you typed in this browser so that it is still there next time.</p>"
         + (priv_server if api_on else "")
         + "<h2 class='h2s'>What we do not do</h2><p>No advertising trackers, no analytics cookies, no tracking pixels in letters, no selling of data.</p>"
         + ("" if api_on else "<h2 class='h2s'>Third parties</h2><p>The site is served by a hosting provider that, like any web server, sees your IP address when you load a page. Fonts, scripts and images are served from this site, not from other companies. "
                            "When you press “Apply”, you go to the employer's own site, which has its own privacy policy.</p>"
            + (f"<h2 class='h2s'>Questions and requests about your data</h2><p>Write to {mail_a('privacy')}. As nothing about you is stored on our side, there is usually nothing to see or erase; we answer every request within 30 days.</p>" if MAIL.get("privacy") else ""))
         + ("<h2 class='h2s'>Changes</h2><p>This page was updated when job alerts and accounts were switched on. If anything else is added (payments, paid tools), this page will say so before it goes live.</p>" if api_on else
            "<h2 class='h2s'>Changes</h2><p>If paid accounts or email alerts are added, this page will be updated before they go live.</p>"))
    page("terms/", f"Terms of use | {SITE}", f"The terms for using {SITE}: what the site is, how accurate the listings are, where you apply, how job descriptions are used and how to get a listing removed.",
         crumbs(("Terms", "")) + "<h1>Terms of use</h1>"
         "<h2 class='h2s'>What this site is</h2><p>A search service for job postings published by companies on their own careers pages. We are not the employer and not a recruitment agency, and we take no part in hiring decisions.</p>"
         "<h2 class='h2s'>Accuracy</h2><p>Listings are collected automatically every hour. A job may change or close between updates, and details such as salary, perks and location are read from the posting text. Always check the employer's own page before you rely on them.</p>"
         "<h2 class='h2s'>Applying</h2><p>Applications are made on the employer's site. Viewing jobs and applying is free.</p>"
         + ("<h2 class='h2s'>Listings from Telegram channels</h2><p>Some listings are read from public Telegram job channels. Each one names its channel, "
            "links to the original post and shows only the facts of the job and a few lines of the post. They are not checked with the employer. "
            f"A channel owner who does not want the channel's posts here can write to {mail_a('partners')}; they are taken off at the next update.</p>"
            if any(j_.get("tg") for j_ in active) else "")       # only while channel posts are shown (telegram_jobs.py)
         + (("<h2 class='h2s'>Job alerts</h2><p>Job alerts are free. You ask for one with your email address and confirm it from the letter we send; then you get the new jobs that match it, "
             "daily or weekly, at most 20 in a letter. Every letter can be stopped in one click. We may stop sending to an address whose mail server refuses our letters, and we may change or end "
             "the service; an alert is never turned into anything paid without your new, separate consent.</p>"
             "<h2 class='h2s'>Accounts</h2><p>An account belongs to one person or one company. Keep its password to yourself and give true details. We may suspend or close an account that posts "
             "fraudulent or misleading jobs, impersonates a company, or tries to get around the checks; what it posted then comes down.</p>"
             "<h2 class='h2s'>Posting a job here</h2><p>Posting a job is free. It must be a real, open job at the company named, for which you may hire; the link to apply must be on the company’s own site or "
             "on its hiring system. Every posting is screened automatically, and the first postings of every account, and any that a check flags, are read by a person before they appear. "
             "Before a job is accepted we check whether it is already on the site; if it is, we say where. Charging candidates any fee, asking them to move money or parcels, to install software or "
             "to give up bank, card or identity details is not allowed. A job stays up for 30 days and can be renewed; we may refuse or remove any posting, and say why. "
             "A job posted by a recruiter is marked as such and is always read by a person first.</p>"
             "<h2 class='h2s'>Company pages</h2><p>Companies whose jobs we read from their own hiring systems can claim their page here with an account tied to the company’s domain. "
             "A claim we cannot confirm from our records is checked by a person. A claimed page shows the company how many people viewed its jobs here and clicked “Apply”, and lets it post jobs "
             "its hiring system does not list. We may withdraw a claim that turns out to be wrong.</p>"
             "<h2 class='h2s'>Payments</h2><p>Nothing is sold yet. The terms of paid placements will be published here before anything can be bought.</p>") if CFG["api_url"] else "")
         + "<h2 class='h2s'>Names and trademarks</h2><p>Company names belong to their owners and are used only to identify who is hiring. A listing here does not mean the company endorses this site.</p>"
         "<h2 class='h2s'>Salary and hiring data</h2><p>Figures on the salary, trends and insights pages are calculated from advertised ranges. They are estimates for information, not an offer or a guarantee.</p>"
         "<h2 class='h2s'>Job descriptions</h2><p>Descriptions are the employers’ own text, read from the hiring feeds they publish for display on other sites. They are shown unchanged, with the employer named and a link to the original posting.</p>"
         "<h2 class='h2s'>Removing a listing</h2><p>" + (f"Employers who want a listing or company page removed can write to {mail_a("jobs")}. It is taken down at the next update." if contact
                                                        else "Employers who want a listing or company page removed can ask through the contact details on the employers page.") + "</p>")

    # For you: five plain questions; the answers stay in the browser and every open job is checked against them
    FY_WORK = [("engineering", "Building software", "developers, testers, DevOps"), ("data-research", "Working with data", "analysts, data scientists, researchers"),
               ("design", "Design", "how a product looks and works"), ("product", "Planning the product", "product and program managers"),
               ("sales-bd", "Sales", "finding customers and partners"), ("marketing", "Marketing", "making a product known"),
               ("support", "Helping customers", "support and customer success"), ("finance", "Finance", "accounting, planning, trading"),
               ("people", "Hiring and HR", "recruiters and people teams"), ("compliance-legal", "Legal and compliance", "lawyers, risk and policy"),
               ("operations", "Operations and IT", "keeping the business running"), ("security", "Security", "protecting systems and data"),
               ("healthcare", "Healthcare", "nurses, doctors, care and clinical staff"), ("manufacturing", "Manufacturing", "engineers and technicians in plants"),
               ("supply-chain", "Supply chain and logistics", "buying, warehouses, transport"), ("retail", "Retail and stores", "shops, store managers, merchandising"),
               ("education", "Education", "teachers, trainers, course designers"), ("consulting", "Consulting", "advisers to other companies")]
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
    fy_top = "".join(fy_chip(t) for t, _ in skill_counts.most_common(40))
    # every kind of work with a page, to be picked by typing (owner: "too few, pull them out as a list")
    fy_role_data = [[rn_, ROLE_RX[rn_].pattern, len(rj_)] for _, (rn_, rj_) in sorted(by_role.items(), key=lambda kv: -len(kv[1][1])) if rn_ in ROLE_RX]
    fy_role_json = json.dumps([[r_[0], r_[1]] for r_ in fy_role_data], ensure_ascii=False).replace("</", "<\\/")
    fy_roles_html = ('<label class="ask-l" for="fy-role">Or pick exact job titles, out of ' + f"{len(fy_role_data):,}" + '</label>'
                     '<input type="search" id="fy-role" list="fy-role-list" placeholder="Type a job title, for example data analyst" autocomplete="off">'
                     '<datalist id="fy-role-list">' + "".join(f'<option value="{e(r_[0])}">{r_[2]:,} open</option>' for r_ in fy_role_data) + '</datalist>'
                     '<div class="fy-roles" id="fy-roles"></div><script type="application/json" id="fy-role-data">' + fy_role_json + '</script>')
    fy_skill_find = ('<label class="ask-l" for="fy-skill-q">Or type any skill, out of ' + f"{len(skill_counts):,}" + '</label>'
                     '<input type="search" id="fy-skill-q" list="fy-skill-list" placeholder="Type a skill, for example Excel" autocomplete="off">'
                     '<datalist id="fy-skill-list">' + "".join(f'<option value="{e(t)}">{c_:,} jobs</option>' for t, c_ in skill_counts.most_common()) + '</datalist>')
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
    page("for-you/", f"Jobs That Match Your Skills and Pay | {SITE}",
         f"Say what work you want, your experience, where you live and the pay you need. {n:,} open jobs are checked against your answers and the ones that fit are listed first, with the reason.",
         crumbs(("For you", "")) + f'<h1>Answer five questions and see the jobs that <span class="hl">fit you</span></h1>'
         f'<p class="lead">Reading {n:,} postings to find the twenty worth applying to takes days. Say what work you want, how much experience you have, where you live and what you need to earn. '
         'Every open job is checked against your answers, and next to each one you see what fits and what does not.</p>'
         '<p class="plain"><b>In plain words:</b> this page is a short form. Nothing you answer leaves your browser, there is no account, and you can skip any question.</p>'
         '<div id="fy-root" class="fy"><div class="fy-form">'
         + ask(1, "What kind of work do you want?", "Pick one or several. Leave it empty to see every kind.", f'<div class="opts" id="fy-work">{fy_work}</div>' + fy_roles_html)
         + ask(2, "How much experience do you have?", "", f'<div class="opts one" id="fy-exp">{fy_exp}</div>')
         + ask(3, "Where do you want to work?", "", f'<div class="opts one" id="fy-where">{fy_where}</div>'
               f'<label class="ask-l" for="fy-place">Your country</label><select id="fy-place"><option value="">Any country</option>{fy_places}</select>'
               '<p class="ask-h" id="fy-place-note">Remote roles are often open to some countries only, so the country matters for them too.</p>')
         + ask(4, "How much do you need to earn?", "In US dollars a year, before tax. Jobs that pay less are left out.", f'<div class="opts one pay" id="fy-pay">{fy_pay}</div>'
               '<label class="ask-l" for="fy-pay-in">Or type your own figure</label><span class="payin">$<input type="number" id="fy-pay-in" min="0" max="2000000" step="5000" inputmode="numeric" placeholder="120000"> a year</span>'
               '<label class="check"><input type="checkbox" id="fy-nopay"> Hide jobs that do not state pay</label><p class="ask-h" id="fy-pay-note"></p>')
         + ask(5, "What can you do?", "Optional. These are tools and skills that postings ask for by name. If the names mean nothing to you, skip this question.",
               f'<div id="fy-skills">{fy_skill_find}<div class="skillbar">{fy_top}</div>'
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
    page("skills/", f"Jobs by Skill — {len(skill_counts)} skills explained | {SITE}",
         f"Open jobs by skill, with a plain-English line on what each of the {len(skill_counts)} skills is: languages, AI, data, cloud, design and business tools.",
         crumbs(("Skills", "")) + '<h1>Jobs by skill</h1>'
         '<p class="lead">Job postings are full of names like Kubernetes or dbt. Here each one comes with a line that says what it is in plain words, '
         'and the number of open roles that ask for it today. Pick one to see the jobs, the pay and who is hiring.</p>'
         '<p class="rel"><span>Jump to:</span>' + "".join(f'<a href="#{g}">{e(nm)}</a>' for g, nm, _ in groups_) + "</p>" + skills_body)

    # Resume builder: stays in the browser, prints to PDF
    rb_qa = [("Is there a 100% free resume builder?", f"This one: all five templates, the PDF and the Word download are free, with no account, no trial and no watermark. "
              f"Many builders let you write for free and charge at the download; we read the pricing pages of {len(builders_check.BUILDERS)} of them, and the comparison shows which give a free PDF."),
             ("Can ChatGPT build a resume?", "It can draft and reword lines, but it does not know your results, and it tends to invent numbers and use the same phrases as everyone else. "
              "Use it for wording, check every fact, and put the text into a plain one-column layout that applicant tracking systems read cleanly, such as the templates here."),
             ("Which is the best free resume builder?", "The one that gives you a file employers’ software can read without paying at the end: a one-column layout, a real PDF or Word download, no sign-up. "
              "That is how this builder is made, and the comparison of free builders shows how others handle the download."),
             ("Do I need to sign up to make a resume here?", "No. You type in the form, the page updates as you go, and you download. Nothing leaves your browser; the draft is kept in this browser so you can come back to it."),
             ("Will an applicant tracking system read this resume?", "The templates are single-column text with standard headings and no tables, icons or text boxes, which is what screening software reads best. "
              "Match it to a posting with the resume match checker before you apply.")]
    rb_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in rb_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("resume/", f"Free Resume Builder: Free PDF & Word Download, No Sign-Up | {SITE}",
         "Build an ATS-friendly resume in your browser: five templates, free PDF and Word download, no account. Nothing is uploaded, and one click matches it to open jobs.",
         crumbs(("Resume builder", "")) + '<h1>Free resume builder that screening software can read</h1><p class="lead">Five plain one-column templates that applicant tracking systems read cleanly '
         '(two-column layouts with icons can come out as scrambled text), and the PDF and the Word file are free, where many builders charge for the download. '
         'Fill in the form, watch the page update, download. No account; nothing leaves this browser.</p>'
         + act_row("#rb", "Start your resume", [("resume/examples/", "Examples by job")]) +
         f'<p class="note no-print">Which builders charge for the download? <a href="{P}/free-resume-builders/">We read the pricing pages of {len(builders_check.BUILDERS)} of them</a>.</p>'
         '<p class="note no-print">“Save as PDF” opens your browser’s print window: choose “Save as PDF” as the printer.</p>'
         '<div id="rb"><div class="rb-actions"><button class="btn" id="rb-print" type="button">Save as PDF — free</button><button class="btn ghost" id="rb-doc" type="button">Download for Word</button><button class="btn ghost" id="rb-json" type="button" title="The open JSON Resume format, readable by other tools and AI assistants">JSON</button>'
         '<label class="wl rb-tplpick">Template<select id="rb-tpl"><option value="classic">Classic</option><option value="modern">Modern</option><option value="compact">Compact</option>'
         '<option value="developer">Developer</option><option value="executive">Executive</option><option value="timeline">Timeline</option></select></label>'
         '<button class="btn ghost" id="rb-match" type="button">Match jobs to this resume</button><button class="btn ghost" id="rb-clear" type="button">Start over</button></div>'
         f'<p class="rb-plus no-print"><b>With Plus, AI writes it with you</b><span>bullet points from your notes · a summary · the resume reworded for one posting · a review with a score</span><a href="{P}/plus/">See what Plus adds</a></p>'
         f'<p class="note no-print">Not sure how to start? <a href="{P}/resume/examples/">Open a resume example for your kind of work</a> and replace it line by line.</p>'
         '<div class="rgrid app"><div class="rb-left no-print"><div id="rb-set" class="rb-set"></div><div id="rb-tabs" class="rb-tabs" role="navigation" aria-label="Resume sections"></div><div id="rb-form"></div></div>'
         '<div class="rb-mid"><div id="rb-preview" aria-live="polite"></div></div>'
         '<aside class="rb-side no-print" aria-label="Score and suggestions"><div id="rb-check" class="rbc" aria-live="polite" hidden></div></aside></div>'
         '<div id="rb-demand" class="no-print" aria-live="polite"></div></div>'
         + '<section class="sec no-print"><div class="sec-head"><h2>What makes a resume get read</h2></div><div class="feats">'
         '<div class="feat"><h3>One page, plain layout</h3><p>Screening software reads simple single-column text best. That is the layout you get here.</p></div>'
         '<div class="feat"><h3>Results, not duties</h3><p>“Cut page load time from 4s to 1.2s” says more than “responsible for performance”.</p></div>'
         '<div class="feat"><h3>The posting’s own words</h3><p>If the job asks for PostgreSQL and you know it, write PostgreSQL, not “databases”.</p></div></div></section>'
         + '<div class="no-print">' + section("Questions about this resume builder", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in rb_qa) + "</dl>") + "</div>"
         + f'<script src="{P}/tools.js?v={V}" defer></script><script src="{P}/resume.js?v={V}" defer></script>', head=rb_ld)

    # "Which free resume builders let you download the PDF": the question every "best free resume builder" list argues about (owner,
    # 14 Nov: "be in the top for free resume builder"). Every fact about another builder is read from its own pages (builders_check.py).
    BC = builders_check
    def bc_cell(v, kind=""):
        v = (v or "").strip()
        if not v: return '<span class="fb-u">Not stated</span>'
        head_, _, rest_ = v.partition(":")
        cls_ = {"yes": "fb-y", "no": "fb-n", "trial": "fb-n", "limited": "fb-l"}.get(kind, "")
        return (f'<b class="{cls_}">{e(head_)}</b>' + (f'<span>{e(rest_.strip())}</span>' if rest_.strip() else "")) if cls_ else e(v)
    bc_free = [b for b in BC.BUILDERS if b["pdf"][0] in ("yes", "limited")]
    bc_paid = [b for b in BC.BUILDERS if b["pdf"][0] in ("no", "trial")]
    bc_list = lambda xs: ", ".join(b["name"] for b in xs[:-1]) + (" and " if len(xs) > 1 else "") + (xs[-1]["name"] if xs else "")
    BC_COLS = ["PDF on the free plan", "Watermark", "Word file free", "Account needed", "Free plan limits", "Cheapest paid option"]
    def bc_tds(b):          # data-l: the column's name, shown beside each value when a phone lays the rows out as cards
        cells_ = [bc_cell(b["pdf"][1], b["pdf"][0])] + [bc_cell(b[k_]) for k_ in ("watermark", "docx", "signup", "limits", "paid")]
        return "".join(f'<td data-l="{e(l_)}"><div>{c_}</div></td>' for l_, c_ in zip(BC_COLS, cells_))
    bc_rows = "".join(f'<tr><th><a href="{e(b["url"])}" rel="nofollow noopener">{e(b["name"])}</a></th>{bc_tds(b)}</tr>' for b in BC.BUILDERS)
    bc_rows += f'<tr class="fb-ours"><th>{e(SITE)}<span>this site</span></th>{bc_tds(BC.OURS)}</tr>'
    bc_table = ('<div class="tablewrap fbwrap"><table class="fbt"><thead><tr><th>Builder</th>' + "".join(f"<th>{e(l_)}</th>" for l_ in BC_COLS)
                + '</tr></thead><tbody>' + bc_rows + "</tbody></table></div>")
    bc_when = fdate(BC.CHECKED)
    bc_qa = [
        ("Which resume builders let you download a PDF for free?",
         f"On {bc_when}, the free plans of {bc_list(bc_free)} let you download a PDF without paying"
         + (f"; {bc_list([b for b in bc_free if b['pdf'][0] == 'limited'])} with limits named in the table" if any(b["pdf"][0] == "limited" for b in bc_free) else "")
         + (f". {bc_list(bc_paid)} ask for a paid plan or a paid trial before the PDF." if bc_paid else ".")
         + f" The builder on this site gives the PDF and the Word file free, without an account."),
        ("Why do some free resume builders charge at the download?",
         "Writing the resume is free so that anyone can start; the payment is asked when the resume is finished and needed. "
         "The table shows, for each builder, what its own pages say a free user can download, and what the cheapest paid option costs."),
        ("Can I make a resume for free without signing up?",
         f"Yes, here: the builder on {SITE} runs in your browser, keeps the resume in the browser and downloads it as a PDF or a Word file for free, with no account and no watermark."),
        ("How was this checked?",
         f"We read each builder’s own pricing page, help pages or terms on {bc_when} and wrote down only what they state; a fact a page does not state is shown as “Not stated”. "
         "Reviews and lists by others were not used as a source. Prices are those the pages showed us that day, in US dollars; several builders say prices differ by country. "
         f"{bc_list([{'name': n_} for n_ in BC.LEFT_OUT])} are not in the table: their pages did not open for our reader that day."),
    ]
    bc_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in bc_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    bc_src = '<ul class="vs-src">' + "".join(f'<li><b>{e(b["name"])}:</b> ' + " · ".join(f'<a href="{e(u_)}" rel="nofollow noopener">{e(w_)}</a>' for u_, w_ in b["sources"]) + "</li>" for b in BC.BUILDERS) + "</ul>"
    page("free-resume-builders/", f"Free Resume Builders: Which Let You Download the PDF Free | {SITE}",
         f"We read the pricing pages of {len(BC.BUILDERS)} resume builders on {bc_when}: which give a free PDF, which add a watermark, which ask for a paid trial first.",
         crumbs(("Resume builder", "resume/"), ("Free resume builders compared", ""))
         + f'<h1>Which free resume builders let you <span class="hl">download the PDF</span>?</h1>'
         + f'<p class="tldr"><strong>Checked on {bc_when}:</strong> of {len(BC.BUILDERS)} well-known resume builders, {len(bc_free)} let a free user download a PDF without paying'
         + (f' ({e(bc_list(bc_free))}' + (f'; {sum(b["pdf"][0] == "limited" for b in bc_free)} of them with limits such as a download cap, one page or branding' if any(b["pdf"][0] == "limited" for b in bc_free) else "") + ")" if bc_free else "") + (f'; {len(bc_paid)} ask for a paid plan or a paid trial before the PDF ({e(bc_list(bc_paid))})' if bc_paid else "")
         + f'. The builder on this site gives the PDF and the Word file free, with no account and no watermark.</p>'
         + '<p class="lead">“Free resume builder” often means free to write and paid to download. Below is what each builder’s own pages say a free user gets, '
           'side by side, with a link to every page we read. Nothing here is a ranking: pick the one that fits you.</p>'
         + section(f"Free plans side by side, {bc_when}", bc_table + f'<p class="note">Not in the table: {e(bc_list([{"name": n_} for n_ in BC.LEFT_OUT]))}, whose pages did not open for our reader on {bc_when}. “Not stated” means the builder’s own pages do not say.</p>')
         + section("Questions", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in bc_qa) + "</dl>")
         + section("Make yours here, free", f'<p>Five one-column templates that screening software can read, a score with fixes as you type, your old resume imported from Word or PDF, '
                   f'and a PDF or Word download at the end. Everything stays in your browser.</p><p><a class="btn primary" href="{P}/resume/">Open the resume builder</a> '
                   f'<a class="btn ghost" href="{P}/resume/examples/">See resume examples</a></p>')
         + section("Sources", bc_src + f'<p class="note">Read on {bc_when}. Plans and prices change: if a fact here is out of date, tell us from the <a href="{P}/about/">About page</a> and it is corrected.</p>'),
         head=bc_ld)

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
        GM = glossary_terms.MORE.get(term)          # a full answer for the terms people search most ("what is an ats")
        gqa = [(f"What is {term[0].lower() + term[1:] if not term[:2].isupper() else term}?", d)] + (list(GM["qa"]) if GM else [])
        ld_ = ('<script type="application/ld+json">' + json.dumps([
            {"@context": "https://schema.org", "@type": "DefinedTerm", "name": term, "description": d, "url": f"{FULL}/glossary/{sl}/",
             "inDefinedTermSet": {"@type": "DefinedTermSet", "name": "Job search glossary", "url": f"{FULL}/glossary/"}},
            {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in gqa]}],
            ensure_ascii=False).replace("</", "<\\/") + "</script>")
        g_more = ""
        if GM:
            g_more = ("".join(section(h_, "".join(f"<p>{e(x_)}</p>" for x_ in xs_)) for h_, xs_ in GM["sections"])
                      + section(f"Questions about {term[0].lower() + term[1:] if not term[:2].isupper() else term}", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in GM["qa"]) + "</dl>"))
            for al_ in GM.get("aliases", ()):     # another address people type: a page that hands over to this one (canonical and an immediate refresh)
                write(f"glossary/{al_}/", f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{e(term)}</title><link rel="canonical" href="{FULL}/glossary/{sl}/">'
                      f'<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={P}/glossary/{sl}/"></head><body><p><a href="{P}/glossary/{sl}/">{e(term)}</a></p></body></html>', sitemap=False)
        gt_ = GM["title"] if GM else f"{term}: What It Means in a Job Search"
        if len(gt_) > 65 and "?" in gt_: gt_ = gt_[:gt_.index("?") + 1]          # "What Is an ATS (Applicant Tracking System)?"
        page(f"glossary/{sl}/", gt_ + (f" | {SITE}" if len(gt_) + len(SITE) + 3 <= 65 else ""),
             f"{term}, explained in plain English: {d if len(d.split()[0]) > 1 and d.split()[0].isupper() else d[0].lower() + d[1:]}",
             crumbs(("Glossary", "glossary/"), (term, "")) + f'<h1>{e(GM["title"] if GM else term)}</h1>'
             f'<div class="gl-top"><div class="gl-card"><span class="gl-k">Definition</span>'
             f'<p class="gl-def"><b>{e(term)}</b>: {e(d if len(d.split()[0]) > 1 and d.split()[0].isupper() else d[0].lower() + d[1:])}</p>'
             + (f'<p class="gl-fig"><span class="gl-k">Today’s figure</span>{e(fig)} <span class="note">Counted on {fdate(TODAY)} from open postings.</span></p>' if fig else "")
             + f'</div><div class="gl-card gl-tip"><h2 class="gl-k">What to do about it</h2><p>{e(tip)}</p>'
             + ('<div class="gl-next">' + "".join(f'<a href="{P}/{u}">{e(lbl)}</a>' for u, lbl in links) + "</div>" if links else "") + "</div></div>"
             + g_more
             + f'<div class="gl-pager"><a href="{P}/glossary/{gslug(prev_[0])}/"><small>← Previous term</small>{e(prev_[0])}</a>'
               f'<a href="{P}/glossary/"><small>Glossary</small>All {len(GT)} terms</a>'
               f'<a href="{P}/glossary/{gslug(next_[0])}/"><small>Next term →</small>{e(next_[0])}</a></div>', head=ld_)
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
         + ('<section class="sec"><div class="sec-head"><h2>Get in touch</h2></div><p>Write to ' + mail_a("partners") + ".</p></section>" if MAIL.get("partners") or contact else
            '<div class="banner" style="margin-top:24px">Contact details will be published here shortly. The widgets, feeds and data above already work without asking anyone.</div>'))

    # Bare page for iframe embeds: /embed/?jobs=skill:python&limit=6&layout=cards&theme=dark&accent=%23ff5500
    write("embed/", f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Jobs widget | {e(SITE)}</title><style>html,body{{margin:0;background:transparent}}body{{padding:2px 8px 8px 2px}}</style></head><body>
<div id="w"><a href="{FULL}/" target="_blank" rel="noopener">Jobs on {e(SITE)}</a></div>
<script>(function(){{var p=new URLSearchParams(location.search),el=document.getElementById('w');
el.setAttribute('data-hrn-jobs',p.get('jobs')||'latest');['limit','layout','theme','accent','title','search','company'].forEach(function(k){{if(p.get(k))el.setAttribute('data-'+k,p.get(k));}});
el.setAttribute('data-hrn-base','{P}');}})();</script><script src="{P}/widget.js?v={V}"></script></body></html>""", sitemap=False)

    # The board: a full-screen, auto-rotating wall of the freshest roles (for a second monitor, an office screen, a classroom). The owner
    # found it on 14 Nov with no idea what it was for: it now says so on top, has back / pause / next and a page count, is a plain
    # scrolling list on phones, is no longer linked from the home page (only from /widgets/) and is kept out of search results.
    write("board/", f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Board — live jobs wall | {e(SITE)}</title><meta name="description" content="A full-screen live board of the freshest jobs, rotating automatically. Put it on a second monitor, an office screen or a classroom wall.">
<meta name="robots" content="noindex"><link rel="canonical" href="{FULL}/board/"><link rel="icon" type="image/svg+xml" href="{P}/favicon.svg">
<style>@font-face{{font-family:"Public Sans";font-weight:100 900;font-display:swap;src:url({P}/fonts/publicsans-latin.woff2) format("woff2")}}
@font-face{{font-family:"JetBrains Mono";font-weight:500 700;font-display:swap;src:url({P}/fonts/jbmono-latin.woff2) format("woff2")}}
html,body{{margin:0;height:100%;background:#0b0b0a;color:#f3f2ec;font-family:"JetBrains Mono",ui-monospace,Menlo,monospace;overflow:hidden}}
.top{{display:flex;justify-content:space-between;align-items:center;padding:2.2vh 3vw;border-bottom:1px solid #2b2b27;font-size:clamp(12px,1.5vw,20px);letter-spacing:.08em;text-transform:uppercase;color:#a5a399}}
.top a{{color:#f3f2ec;text-decoration:none;font-family:Inter,system-ui,sans-serif;font-weight:700;letter-spacing:-.01em;text-transform:none;font-size:clamp(16px,2vw,28px)}}
.top b{{color:#5fd486;font-weight:500}}.dot{{display:inline-block;width:.6em;height:.6em;border-radius:50%;background:#1f9d55;margin-right:.6em}}
#rows{{padding:1vh 3vw}}.r{{display:grid;grid-template-columns:7ch minmax(0,1.3fr) minmax(0,.8fr) minmax(0,.7fr);gap:2vw;align-items:baseline;padding:1.55vh 0;border-bottom:1px solid #1f1f1c;animation:in .5s backwards}}
@keyframes in{{from{{opacity:0;transform:translateY(8px)}}}}.a{{color:#5fd486;font-size:clamp(11px,1.3vw,18px)}}
.t{{font-family:Inter,system-ui,sans-serif;font-weight:700;font-size:clamp(15px,2.1vw,30px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#f3f2ec;text-decoration:none}}
.c,.l{{font-size:clamp(11px,1.4vw,20px);color:#a5a399;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.c{{color:#e9e7de}}
.foot{{position:fixed;left:0;right:0;bottom:0;display:flex;justify-content:space-between;padding:1.6vh 3vw;font-size:clamp(10px,1.1vw,15px);color:#77756c;letter-spacing:.06em;text-transform:uppercase;background:#0b0b0a}}
.foot a{{color:#5fd486;text-decoration:none}}
.bar{{display:flex;justify-content:space-between;align-items:center;gap:2vw;padding:1.2vh 3vw;font-family:Inter,system-ui,sans-serif;font-size:clamp(12px,1.1vw,16px);color:#a5a399;border-bottom:1px solid #1f1f1c}}
.ctl{{display:flex;align-items:center;gap:.6em;white-space:nowrap}}.ctl button{{font:inherit;color:#f3f2ec;background:#1a1a17;border:1px solid #2b2b27;border-radius:8px;padding:.35em .8em;cursor:pointer}}
.ctl button:hover{{border-color:#5fd486}}#pg{{font-family:"JetBrains Mono",ui-monospace,monospace;color:#5fd486;min-width:9ch;text-align:right}}.foot .m{{color:#e9e7de}}.n{{padding:6vh 0;font-size:clamp(14px,1.8vw,24px);color:#a5a399}}.n a{{color:#5fd486}}@media(max-width:700px){{html,body{{height:auto;overflow:auto}}.r{{grid-template-columns:5ch minmax(0,1fr)}}.c,.l{{grid-column:2}}.ctl{{display:none}}.foot{{position:static}}.bar{{display:block}}}}</style></head><body>
<div class="top"><a href="{P}/"><span class="dot"></span>{e(SITE)}</a><h1 id="what" style="all:unset">Fresh on the board</h1><b id="clock"></b></div>
<div class="bar"><span>A live wall for an office screen, a TV or a second monitor: a new page of jobs every 9 seconds. Press F11 for full screen. <a href="{P}/widgets/" style="color:#7ee39a">Pick a skill, city or company</a> · <a href="{P}/jobs/" style="color:#7ee39a">Search all jobs</a></span>
<span class="ctl"><button id="prev" type="button" aria-label="Previous page">‹</button><button id="pause" type="button">Pause</button><button id="next" type="button" aria-label="Next page">›</button><span id="pg"></span></span></div><div id="rows"></div>
<div class="foot"><span id="count"></span><a href="{P}/widgets/">Put this board on your screen</a></div>
<script>(function(){{var q=new URLSearchParams(location.search),path=q.get('skill')?'skills/'+q.get('skill'):q.get('company')?'companies/'+q.get('company'):q.get('location')?'locations/'+q.get('location'):q.has('remote')?'remote':'latest';
var rows=document.getElementById('rows'),jobs=[],page=0,phone=innerWidth<=700,per=phone?1e9:Math.max(4,Math.floor((innerHeight*0.7)/Math.max(46,innerHeight*0.075))),run=null;
function esc(v){{return String(v==null?'':v).replace(/[&<>"]/g,function(c){{return{{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]}})}}
function age(iso){{var p=String(iso||'').split('-');if(p.length<3)return'';var n=new Date(),d=new Date(+p[0],+p[1]-1,+p[2]),k=Math.max(0,Math.round((new Date(n.getFullYear(),n.getMonth(),n.getDate())-d)/864e5));return k===0?'TODAY':k<14?k+'D':Math.floor(k/7)+'W'}}
function pages(){{return Math.max(1,Math.ceil(jobs.length/per))}}
function go(d){{page=(page+d+pages())%pages();draw()}}
function play(on){{clearInterval(run);run=on&&!phone?setInterval(function(){{go(1)}},9000):null;document.getElementById('pause').textContent=run?'Pause':'Play'}}
document.getElementById('prev').onclick=function(){{go(-1);play(!!run)}};document.getElementById('next').onclick=function(){{go(1);play(!!run)}};
document.getElementById('pause').onclick=function(){{play(!run)}};
addEventListener('keydown',function(e){{if(e.key==='ArrowRight')document.getElementById('next').click();else if(e.key==='ArrowLeft')document.getElementById('prev').click();else if(e.key===' '){{e.preventDefault();play(!run)}}}});
function draw(){{if(!jobs.length)return;var s=jobs.slice(page*per,page*per+per);if(!s.length){{page=0;s=jobs.slice(0,per)}}document.getElementById('pg').textContent=(page+1)+' / '+pages();
rows.innerHTML=s.map(function(j,i){{return'<div class="r" style="animation-delay:'+i*70+'ms"><span class="a">'+age(j.posted)+'</span><a class="t" href="'+esc(j.url)+'">'+esc(j.title)+'</a><span class="c">'+esc(j.company)+'</span><span class="l">'+esc(j.salary||j.location||(j.remote?'Remote':''))+'</span></div>'}}).join('')}}
function tick(){{document.getElementById('clock').textContent=new Date().toLocaleTimeString([],{{hour:'2-digit',minute:'2-digit'}})}}
var asked=q.get('skill')||q.get('company')||q.get('location')||'',timer;
function note(html){{rows.innerHTML='<p class="n">'+html+'</p>'}}
function show(d,miss){{jobs=d.jobs;page=0;document.getElementById('what').textContent=miss?'Latest roles':d.name;document.getElementById('count').innerHTML=(miss?'<span class="m">No board for “'+esc(asked.slice(0,40))+'” · showing the latest</span> · ':'')+Number(d.total).toLocaleString('en-US')+' open roles · updated every hour';draw();play(true)}}
function load(p,miss){{return fetch('{P}/api/v1/'+p+'.json').then(function(r){{if(!r.ok)throw 0;return r.json()}}).then(function(d){{if(!d.jobs||!d.jobs.length)throw 0;show(d,miss)}})}}
load(path.toLowerCase().replace(/[^a-z0-9/_.+-]/gi,'-'),false).catch(function(){{if(path==='latest')throw 0;return load('latest',true)}}).catch(function(){{note('The board could not load right now. <a href="{P}/jobs/">Open the job list</a>')}});
tick();setInterval(tick,20000);setTimeout(function(){{location.reload()}},3600000)}})();</script></body></html>""", sitemap=False)

    # Widgets, badges, API: ways for other sites to show our jobs and link back
    wb_data = {"site": SITE, "skills": [[tslug(t), t] for t, _ in skill_counts.most_common()], "categories": [[cs, CAT[cs]] for cs in CAT if by_cat[cs]],
               "locations": [[slug, name.removeprefix("the ")] for name, slug, _ in places], "companies": [[slugify(c), c] for c, _ in comp_items if OPEN[c]]}
    wsize = round(len((ROOT / "assets" / "widget.js").read_bytes()) / 1024)
    w_faq = [("Is the job widget free?", "Yes. There is no plan, no account and no limit on page views. The snippet keeps a small link back to this site, which is how the widget stays free."),
             ("Do I need to sign up or get a key?", "No. Choose what to show in the builder on this page, copy the code and paste it into your site."),
             ("How often do the jobs update?", f"Lists from our index are rebuilt every hour from the career pages of {m:,} companies, each read {EVERY}, so closed roles drop out by themselves. A list of your own company’s jobs is read live from your hiring system every time the page opens."),
             ("Can I show only my own company’s jobs?", "Yes. If you post jobs through Greenhouse, Lever or Ashby, pick that system in the builder and type the name of your board. The widget reads your public board directly, with no account and nothing to keep in sync by hand."),
             ("Does it work with WordPress, Webflow, Wix, Squarespace, Shopify and Framer?", "Yes. Anything that lets you paste HTML works with the script version. Builders that strip scripts, such as Notion, take the iframe version. The table on this page says where to paste the code on each platform."),
             ("Will the widget slow my page down?", f"The script is about {wsize} KB, loads asynchronously and draws inside its own container, so it does not block your page and your styles do not leak into it or out of it."),
             ("Where does a click on a job lead?", "To the job’s page on this site, which shows the salary, the remote rules and the date of the last check, and from there to the employer’s own application page. For your own board the click goes straight to your application page."),
             ("Can I change how it looks?", "Yes: five layouts (list, cards, compact, ticker and a full careers page), a light, dark or automatic theme, your own accent colour, your own heading and an optional search box.")]
    w_faq_html = '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in w_faq) + "</dl>"
    w_ld = ('<script type="application/ld+json">' + json.dumps([
        {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{SITE} job widget", "url": f"{FULL}/widgets/", "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
         "description": "A free embeddable job widget: self-updating jobs by skill, city, category or company, or a company’s own jobs read from Greenhouse, Lever or Ashby.",
         "isAccessibleForFree": True, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": {"@type": "Organization", "name": SITE, "url": FULL + "/"}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in w_faq]}],
        ensure_ascii=False).replace("</", "<\\/") + "</script>" + crumbs_ld([("Job widget", "")]))
    wt = lambda head, rows_: ('<div class="tablewrap"><table><tr>' + "".join(f"<th>{h_}</th>" for h_ in head) + "</tr>"
                              + "".join("<tr>" + "".join(f"<td>{c_}</td>" for c_ in r_) + "</tr>" for r_ in rows_) + "</table></div>")
    page("widgets/", f"Free Job Widget for Your Website | {SITE}",
         "A free job widget for any website: one snippet shows self-updating jobs by skill or city, or your own company’s jobs from Greenhouse, Lever or Ashby. No sign-up.",
         crumbs(("Job widget", "")) + '<h1>Free job widget for your website</h1>'
         f'<p class="plain"><b>In plain words:</b> a widget is a small box with a list of jobs that sits on your own website or blog. You choose what it shows, copy a short piece of code from this page and paste it into your site. '
         f'After that the list keeps itself up to date. Looking for a job yourself? You do not need this page: <a href="{P}/jobs/">go to the job search</a>.</p>'
         '<p class="lead">It is free and needs no account. The list can show jobs from our index, by skill, city, category or company, '
         'or your own company’s jobs, read straight from the hiring software you already use (Greenhouse, Lever or Ashby), so nobody has to type them in.</p>'
         f'<div id="wb" data-full="{FULL}" data-base="{P}"><div class="card"><div class="fbar" style="margin:0">'
         '<label class="wl">What to show<select id="wb-type"><optgroup label="Jobs from our index"><option value="skill">Jobs by skill</option><option value="category">Jobs by category</option><option value="location">Jobs by location</option>'
         '<option value="company">Jobs at a company we list</option><option value="remote">Remote jobs</option><option value="latest">Latest jobs</option></optgroup>'
         '<optgroup label="Your own company’s jobs"><option value="greenhouse">From Greenhouse</option><option value="lever">From Lever</option><option value="ashby">From Ashby</option></optgroup></select></label>'
         '<label class="wl">Which one<select id="wb-val"></select></label>'
         '<label class="wl" id="wb-board-l" hidden>Your board’s name<input type="text" id="wb-board" placeholder="acme" autocomplete="off" spellcheck="false"></label>'
         '<label class="wl" id="wb-co-l" hidden>Company name<input type="text" id="wb-co" placeholder="Acme" autocomplete="off"></label>'
         '<label class="wl">How many jobs<select id="wb-limit"><option>4</option><option selected>6</option><option>8</option><option>10</option><option>15</option></select></label>'
         '<label class="wl">How it looks<select id="wb-layout"><option value="list">List</option><option value="cards">Cards</option><option value="compact">Compact (sidebar)</option><option value="ticker">Ticker</option><option value="careers">Careers page (all jobs, with search)</option></select></label>'
         '<label class="wl">Light or dark<select id="wb-theme"><option value="auto">Match the visitor</option><option value="light">Light</option><option value="dark">Dark</option></select></label>'
         '<label class="wl">Colour<input type="color" id="wb-accent" value="#15803d" aria-label="Accent colour"></label>'
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
             ["<code>data-accent</code>", "Any hex colour for the hover bar and the link underline", "<code>#15803d</code>"],
             ["<code>data-search</code>", "<code>1</code> adds a search box, a team filter where teams exist, and “Show more”", "off"],
             ["<code>data-title</code>", "Your own heading for the widget", "the name of the list"],
             ["<code>data-company</code>", "Your company name, shown in the heading of your own board", "none"]]))
         + section("How it differs from other job widgets", wt(["", "This widget", "Widget builders", "Hiring-system embeds"], [
             ["Where the jobs come from", f"Our index of {n:,} open jobs, or your own board", "You type each job in by hand", "Your own board only"],
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
    snip_script = e(f'<div data-hrn-jobs="latest" data-limit="6"><a href="{FULL}/jobs/">Jobs on {SITE}</a></div>\n<script src="{FULL}/widget.js" async></script>')
    snip_iframe = e(f'<iframe src="{FULL}/embed/?jobs=latest&limit=6" title="Jobs" loading="lazy" style="width:100%;max-width:720px;height:470px;border:0"></iframe>\n<p><a href="{FULL}/jobs/">Jobs on {SITE}</a></p>')
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
             f"How to add a free job widget to a {pname} site: where to paste the code, what to watch for, and a live preview. Jobs by skill or city, or your own company’s jobs.",
             crumbs(("Job widget", "widgets/"), (pname, "")) + f"<h1>Job widget for {e(pname)}</h1>"
             f'<p class="lead">A self-updating list of open jobs on your {e(pname)} site, in a few clicks. It is the same free widget as on the <a href="{P}/widgets/">job widget page</a>; this page has the steps for {e(pname)}.</p>'
             + section(f"Add it to {pname}", '<ol class="steps">' + "".join(f"<li>{x}</li>" for x in steps_p) + f'</ol><p class="note">{catch}</p>')
             + section("The code", f'<span class="flabel">{first[0]} (use this one on {e(pname)})</span><textarea id="pw-a" rows="3" readonly aria-label="{first[0]}">{first[1]}</textarea>'
                       '<p><button class="btn sm" type="button" data-copy="pw-a">Copy the code</button></p>'
                       f'<span class="flabel">{second[0]}</span><textarea id="pw-b" rows="3" readonly aria-label="{second[0]}">{second[1]}</textarea>'
                       '<p><button class="btn sm ghost" type="button" data-copy="pw-b" style="margin-top:0">Copy the code</button></p>'
                       f'<p>This snippet shows the latest jobs. To show one skill, a city, one company or your own board, with your colours and layout, <a href="{P}/widgets/">build your own on the job widget page</a>.</p>')
             + section("What your visitors will see", f'<div data-hrn-jobs="latest" data-limit="5" data-hrn-base="{P}"><a href="{P}/jobs/">Jobs on {e(SITE)}</a></div>')
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
    api_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Dataset", "name": f"{SITE}: open jobs",
               "description": f"Open job postings collected from the official careers pages of {m:,} companies, each read {EVERY}: title, employer, location, remote flag, advertised salary and posting date, with aggregate counts and salary medians by skill, category, location and company.",
               "url": f"{FULL}/api/", "dateModified": TODAY, "isAccessibleForFree": True, "creator": {"@type": "Organization", "name": SITE, "url": FULL + "/"}, "license": f"{FULL}/terms/",
               "keywords": ["jobs", "job postings", "salaries", "remote jobs", "hiring trends"],
               "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{FULL}/api/v1/index.json"}]
                               + [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{FULL}/data/open/{x}.csv"} for x in ("skills", "companies", "categories", "locations")]}) + "</script>")
    # "free job listings api" (checked 15 Nov 2026): Google's answer puts first a free API with no key that reads hiring systems
    # directly (Arbeitnow); People also ask "Is there any free API to use?". Ours is the same kind, so the page says so in those words.
    api_qa = [("Is there a free job listings API?", f"Yes: this one is free, needs no API key and no sign-up, and serves {n:,} open jobs as JSON, by skill, category, place and company. "
               "It is fine for personal and commercial projects with a link back."),
              ("Where do the jobs in this API come from?", f"From the careers pages of {m:,} employers, read every hour through their own hiring systems (Greenhouse, Lever, Ashby and others), "
               "not from other job boards, so every job links to the employer’s own page."),
              ("Do I need an API key?", "No. Fetch the JSON address you need; CORS is open, so it works from a web page too. Please fetch each feed at most once an hour: it changes hourly."),
              ("Can I show these jobs on my own site?", "Yes, with a link to the job page or to this site wherever you show them. The ready-made widget does it for you without code.")]
    api_faq = section("Questions about the jobs API", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in api_qa) + "</dl>")
    api_ld = api_ld + ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in api_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("api/", f"Free Job Listings API: JSON, No Key, From Employers | {SITE}",
         "A free JSON API of open jobs by skill, category, location and company. No API key, CORS enabled, updated hourly.",
         crumbs(("API", "")) + '<h1>Free jobs API</h1>' + f'<p class="plain"><b>In plain words:</b> this page is for programmers. An API is a way for a program to read our list of jobs by itself. To show jobs on a website without programming, use the <a href="{P}/widgets/">job widget</a>. To look for a job, use the <a href="{P}/jobs/">search</a>.</p>' + '<p class="lead">Collecting jobs yourself means hundreds of career pages and a scraper that breaks every week. Here is the finished result as plain JSON you can fetch from anywhere: a bot, a newsletter script, a side project. No key, no sign-up, CORS enabled, refreshed every hour.</p>'
         + section("Endpoints", ttable(["Feed", "Address"], [
             trow(["Everything available", f"<code>{FULL}/api/v1/index.json</code>"]), trow(["Latest jobs", f"<code>{FULL}/api/v1/latest.json</code>"]),
             trow(["Remote jobs", f"<code>{FULL}/api/v1/remote.json</code>"]), trow(["By skill", f"<code>{FULL}/api/v1/skills/rust.json</code>"]),
             trow(["By category", f"<code>{FULL}/api/v1/categories/engineering.json</code>"]), trow(["By location", f"<code>{FULL}/api/v1/locations/europe.json</code>"]),
             trow(["By company", f"<code>{FULL}/api/v1/companies/stripe.json</code>"])]))
         + section("Response", f'<pre><code>{e(sample)}</code></pre><p class="note">Skill, category, location, latest and remote feeds hold the 30 newest matching jobs and the total count; a company feed holds all of that company’s open jobs. The slugs are the same as in the page addresses.</p>')
         + section("Example", f"<pre><code>{e(js_example)}</code></pre>")
         + section("Fair use", '<p>Free for personal and commercial projects. Two requests: link back to the job page or to this site wherever you show the data, and fetch each feed no more than once an hour (it changes once an hour).</p>'
                   f'<p>Also available: <a href="{P}/feed.xml">RSS feeds</a>, CSV downloads on the <a href="{P}/trends/">trends page</a>, and a ready-made <a href="{P}/widgets/">widget</a>.</p>') + api_faq, head=api_ld)

    # ---- Prices: /plus/, /post-a-job/ and /pricing/. The product line is the owner's of 15 Nov 2026. Every price is read from config.json
    # ("prices" for employers, "plus" for job seekers), so these pages and the account page name the same products. Every figure about
    # another site comes from a research file (RESEARCH_TEAL_JOBRIGHT_SPONSORED.md, RESEARCH_ZHIPIN_NAUKRI_SEEK.md, PRICING_RESEARCH.md,
    # REVENUE_RESEARCH.md, COMPETITOR_GAPS.md, REVIEWS_STUDY.md, RESEARCH_REZI_BUILDER.md) and is shown with its source, the day it was
    # read and the file's own mark (third-party, secondary, not verified). Re-read the source before changing a figure.
    # The rules (server/README.md and the site): one payment, nothing renews, paid in crypto, switched on by itself; no countdowns, nothing
    # ticked in advance, no crossed-out "regular" price that never applied, no "most popular" (nothing has been sold yet): "Recommended"
    # is our advice and says so.
    plus = CFG.get("plus", {"live": False, "plans": []})
    plans_, passes_ = plus.get("plans", []), plus.get("passes", [])
    api_on = bool(CFG["api_url"])
    app_url = f"{P}/account/" if api_on else ""
    usd = lambda s: float(re.sub(r"[^\d.]", "", s or "") or 0)                         # "$1,000" -> 1000.0
    dol = lambda x: f"${x:,.0f}" if float(x).is_integer() else f"${x:,.2f}"            # 51 -> "$51", 20.99 -> "$20.99"
    def days_of(pl):
        m_ = re.search(r"\d+", pl["name"])
        return int(m_.group(0)) if m_ else 30
    def per_day(pl):
        c_ = round(100 * usd(pl["price"]) / days_of(pl))
        return f"${c_ / 100:.2f} a day" if c_ >= 100 else f"{c_} cents a day"
    low_plan = min(plans_, key=lambda pl: usd(pl["price"]) / days_of(pl)) if plans_ else None
    plan_by, pass_by = {pl["name"]: pl for pl in plans_}, {ps["name"]: ps for ps in passes_}
    best_plan = next((pl for pl in plans_ if pl.get("best")), plans_[0] if plans_ else None)
    pl7, pl30, pl90 = plan_by.get("7 days"), plan_by.get("30 days"), plan_by.get("90 days")
    ps_res, ps_int = pass_by.get("One tailored resume"), pass_by.get("One mock interview")
    tick = lambda items: '<ul class="ticks">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
    trust = lambda items: '<ul class="ptrust">' + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
    fit = lambda rows_: '<div class="pfit">' + "".join(f"<div><b>{e(a)}</b>{e(b)}</div>" for a, b in rows_) + "</div>"
    faq_ld = lambda qa: ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    faq_html = lambda qa: '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa) + "</dl>"
    ai_m = re.search(r"AI_MONTHLY\s*=\s*\{\s*resume:\s*(\d+),\s*letter:\s*(\d+),\s*interview:\s*(\d+)", (ROOT / "server" / "src" / "worker.js").read_text(encoding="utf-8") if (ROOT / "server" / "src" / "worker.js").exists() else "")
    ai_allow = f"{ai_m.group(1)} resume requests, {ai_m.group(2)} letters and {ai_m.group(3)} interview requests" if ai_m else "an allowance shown before you pay"
    # employer products: how long each one runs, by its name in config.json
    TERM = {"Standard listing": "for 30 days", "Standard boost": "for 30 days", "Premium boost": "for 30 days", "Hiring Pass": "for 30 days",
            "Company spotlight": "for 30 days", "Category or skill sponsor": "for 30 days", "Bump to top": "once", "Extend a boost by 30 days": "once per boost",
            "Urgently hiring badge": "for 14 days", "Resume search: 50 contact requests": "for 50 requests"}
    is_credits = lambda name: bool(re.fullmatch(r"[\d,]+ credits", name))
    term = lambda name: TERM.get(name, "one top-up" if is_credits(name) else "")
    credits_ = [p_ for p_ in CFG["prices"] if is_credits(p_["name"])]
    def bonus(p_):
        c_, d_ = usd(p_["name"]), usd(p_["price"])
        return f"+{round(100 * (c_ / d_ - 1))}% bonus" if d_ and c_ > d_ else ""
    pv = lambda name: usd(price_of(name))
    SB, PB, HP, SP, CS, XB, RS = (pv(x) for x in ("Standard boost", "Premium boost", "Hiring Pass", "Company spotlight", "Category or skill sponsor",
                                                   "Extend a boost by 30 days", "Resume search: 50 contact requests"))
    per_contact = dol(round(RS / 50, 2))
    # every product and price in one table (the press page shows it too)
    rows = "".join(f"<tr><td><strong>{e(p['name'])}</strong></td><td><strong>{e(p['price'])}</strong></td><td>{e(p['what'])}</td></tr>" for p in CFG["prices"])
    def pcard(name, price, per, sub, btn, fine="", chip="", best=False, ticks=None):
        return (f'<div class="pcard{" best" if best else ""}">' + ('<span class="pband">Recommended by us</span>' if best else "")
                + f'<p class="pk-n">{e(name)}</p><p class="pk-p"><b>{e(price)}</b><span>{e(per)}</span></p>'
                + '<p class="pk-s">' + (f'<span class="pchip">{e(chip)}</span>' if chip else "") + "</p>"
                + f'<p class="pk-d">{e(sub)}</p>{btn}' + (f'<p class="pk-f">{e(fine)}</p>' if fine else "") + (tick(ticks) if ticks else "") + "</div>")
    def acard(name, price, per, what, chip=""):
        return (f'<div class="pa"><p class="pk-n">{e(name)}</p><p class="pk-p"><b>{e(price)}</b><span>{e(per)}</span></p>'
                + (f'<p class="pk-s"><span class="pchip">{e(chip)}</span></p>' if chip else "") + (f'<p class="pk-d">{e(what)}</p>' if what else "") + "</div>")
    def emp_btn(best, here=False, label="Post a job"):
        kind = "primary" if best else "ghost"
        if app_url: return f'<a class="btn {kind}" href="{e(app_url)}">{e(label)}</a>'
        return f'<button class="btn {kind}" type="button" disabled>Opens soon</button>' if here else f'<a class="btn {kind}" href="{P}/post-a-job/">How posting works</a>'
    def plus_btn(best):
        kind = "primary" if best else "ghost"
        return (f'<a class="btn {kind}" href="{P}/plus/#pay">Get Plus</a>' if plus.get("live") else f'<a class="btn {kind}" href="{P}/plus/">See what Plus does</a>')      # not on sale yet: a dead grey button teaches nothing, the Plus page does
    guarantee = ('<div class="pguar"><p class="pguar-k">Our guarantee: a free re-run</p>'
                 '<p class="pguar-h">Fewer than 10 clicks on Apply in 14 days? The boost runs again, free.</p>'
                 '<p>If a Standard or Premium boost that was paid for gets fewer than 10 clicks on Apply in its first 14 days, it runs for 30 more days at no cost. '
                 'Nothing to claim and nobody to write to: it happens by itself.</p>'
                 '<p class="note">It counts clicks on Apply, which we can measure. It cannot promise applications or a hire.</p></div>')

    # ---- What others charge for the same things. A source: (what it is, its address or None, the day it was read).
    CMP_SRC = {
        "indeed": ("Indeed’s pricing page", "https://www.indeed.com/hire/cs/pricing?co=US", "15 Nov 2026"),
        "indeed_how": ("Indeed: how pricing works", "https://www.indeed.com/hire/resources/howtohub/how-pricing-works-on-indeed", "15 Nov 2026"),
        "indeed_est": ("100hires and Vendr guides", "https://100hires.com/indeed-job-posting-cost.html", "15 Nov 2026"),
        "indeed_free": ("100hires guide, updated 12 Oct 2026", "https://100hires.com/indeed-job-posting-cost.html", "15 Nov 2026"),
        "vendr": ("Vendr guide, Feb 2026", None, "15 Nov 2026"),
        "smart": ("Indeed’s US page as shown in a search summary; 100hires", None, "15 Nov 2026"),
        "brand": ("a quote found by search", None, "15 Nov 2026"),
        "glassdoor": ("Glassdoor’s employer pricing page", "https://www.glassdoor.com/employers/features-and-pricing/", "13 Nov 2026"),
        "glassdoor_in": ("noon.ai", "https://www.noon.ai/blog/articles/346-glassdoor-pricing-2026", "15 Nov 2026"),
        "linkedin": ("LinkedIn’s job posting page", "https://business.linkedin.com/hire/post-jobs", "13 Nov 2026"),
        "li_page": ("LinkedIn Premium’s page", "https://premium.linkedin.com/", "13 Nov 2026"),
        "li_prem": ("activepieces.com, checked by its author on 9 Nov 2026; LinkedIn shows the price only after sign-in", None, "13 Nov 2026"),
        "zip": ("ZipRecruiter’s pricing page showed a bot check; 100hires", "https://www.ziprecruiter.com/pricing", "13 Nov 2026"),
        "zip_sec": ("ZipRecruiter’s Q3 2026 letter to shareholders, filed with the SEC", "https://www.sec.gov/Archives/edgar/data/0001617553/000161755326000055/q32026shareholderletter-.htm", "13 Nov 2026"),
        "teal": ("Teal’s pricing page", "https://www.tealhq.com/pricing", "13 Nov 2026"),
        "teal3": ("reviews on makerstack.co and frontdeskreview.com", "https://makerstack.co/reviews/teal-review/", "15 Nov 2026"),
        "jobright": ("careery.pro and jobstrack.io reviews of its Aug 2026 prices (its own price page did not open)", "https://careery.pro/blog/ai-job-search/jobright-ai-review", "15 Nov 2026"),
        "jobright_emp": ("Jobright’s employer pricing page", "https://jobright.ai/employers/pricing", "15 Nov 2026"),
        "seek": ("SEEK’s product terms of 2 Nov 2026", "https://au.employer.seek.com/support/productterms", "15 Nov 2026"),
        "seek_ts": ("SEEK’s talent search terms", "https://au.employer.seek.com/support/talentsearchofferterms", "15 Nov 2026"),
        "seek_budget": ("100hires", "https://100hires.com/job-boards-australia.html", "15 Nov 2026"),
        "jora": ("listings found by search", None, "15 Nov 2026"),
        "naukri_app": ("the Naukri app on the App Store, India", "https://apps.apple.com/in/app/naukri-job-search-careers/id482877505", "15 Nov 2026"),
        "naukri_emp": ("Internshala guide, updated 21 Sep 2026", "https://internshala.com/blog/naukri-job-posting-price/", "15 Nov 2026"),
        "naukri_ff": ("HRCabin", "https://www.hrcabin.com/naukri-fast-forward-services-cost/", "15 Nov 2026"),
        "boss": ("the BOSS Zhipin app on the App Store, China", "https://apps.apple.com/cn/app/id887314963", "15 Nov 2026"),
        "jiemian": ("Jiemian, citing BOSS Zhipin support", "https://m.jiemian.com/article/13492516.html", "15 Nov 2026"),
        "niche": ("the price pages of 11 job boards that print one", None, "13 Nov 2026"),
        "niche6": ("the price pages of 6 job boards", None, "13 Nov 2026"),
        "seek11": ("the price pages of 11 job-search services", None, "13 Nov 2026"),
        "wwr": ("We Work Remotely’s price pages", "https://weworkremotely.com/remote-jobs/find-your-plan", "13 Nov 2026"),
        "web3": ("web3.career’s posting page", "https://web3.career/post-web3-job", "13 Nov 2026"),
        "web3ads": ("web3.career’s ads page", "https://web3.career/ads", "13 Nov 2026"),
        "remote3": ("Remote3’s posting page", "https://www.remote3.co/post-job", "13 Nov 2026"),
        "remotive": ("Remotive’s hiring page", "https://remotive.com/hire", "13 Nov 2026"),
        "remotive_j": ("Remotive’s home page", "https://remotive.com/", "13 Nov 2026"),
        "wn": ("Working Nomads’ Premium page", "https://www.workingnomads.com/premium-subscription", "13 Nov 2026"),
        "dice": ("Dice’s hiring price page", "https://www.dice.com/hiring/pricing", "13 Nov 2026"),
        "rezi": ("Rezi’s pricing and help pages", "https://www.rezi.ai/pricing", "14 Nov 2026"),
        "trustpilot": ("their Trustpilot pages", None, "15 Nov 2026"),
    }
    def srcs(refs):
        out_ = []
        for k_, mark_ in refs:
            lab_, url_, day_ = CMP_SRC[k_]
            out_.append((f'<a href="{e(url_)}" rel="nofollow noopener">{e(lab_)}</a>' if url_ else e(lab_)) + (f", {e(mark_)}" if mark_ else "") + f", read {day_}")
        return "<small>" + "; ".join(out_) + "</small>"
    def cmp_table(groups):
        """Each product in a row: what it is, our price, what others charge for the same thing (each figure with its source and the day
        it was read) and the difference in plain words. A table on a computer; on a phone every row becomes a card."""
        body_ = ""
        for g_, rows_ in groups:
            body_ += f'<tr class="cmp-g"><th scope="colgroup" colspan="4">{e(g_)}</th></tr>'
            for name_, sub_, here_, here_sub, items_, diff_ in rows_:
                them_ = '<ul class="cmp-l">' + "".join(f"<li><b>{e(s_)}:</b> {e(w_)} {srcs(r_)}</li>" for s_, w_, r_ in items_) + "</ul>"
                body_ += (f'<tr><th scope="row"><b>{e(name_)}</b>' + (f"<span>{e(sub_)}</span>" if sub_ else "") + "</th>"
                          f'<td class="cmp-us"><b>{e(here_)}</b> <span>{e(here_sub)}</span></td><td class="cmp-them">{them_}</td><td class="cmp-d">{e(diff_)}</td></tr>')
        return ('<div class="cmpwrap"><table class="cmpt"><thead><tr><th scope="col">What you get</th><th scope="col">Here</th>'
                f'<th scope="col">Elsewhere, for the same thing</th><th scope="col">The difference</th></tr></thead><tbody>{body_}</tbody></table></div>'
                '<p class="note">Each figure as its source gives it, on the day it was read. “Third-party” means the figure is not from the site itself; “≈” marks an '
                'estimate or a conversion (about ₹88, ¥6.72 or A$1.54 to the US dollar). Prices change: check the source before you rely on one.</p>')

    # employers, product by product
    emp_cmp = cmp_table([
        ("Free here", [
            ("Posting a job", "30 days in the list, its own page in Google’s job box", "Free", "for 30 days", [
                ("Indeed", "free to post, but some jobs must be sponsored", [("indeed", "")]),
                ("Indeed", "3 free posts a month for a company in the US, up to 30 days each", [("indeed_free", "third-party")]),
                ("LinkedIn", "no public price for job posts: it depends on your hiring needs", [("linkedin", "")]),
                ("Niche job boards", "$299 at the median for one 30-day post", [("niche", "")]),
                ("SEEK", "no published price for a Basic ad: it changes with the role and the place. Free “Lite” ads only in Asia, at SEEK’s choice", [("seek", "")]),
                ("Naukri", "₹400–₹850 (≈US$4.5–9.7) for a short classified post", [("naukri_emp", "third-party")]),
                ("BOSS Zhipin", "¥30–¥118 (≈US$4.5–17.6) for a 30-day post; a role that many employers post in one city must be paid for", [("boss", ""), ("jiemian", "third-party")]),
             ], "Free here; $299 for the same 30 days at the median niche board"),
            ("Jobs from your careers page", f"read {EVERY} from {m:,} companies’ own pages", "Free", "nothing to post", [
                ("SEEK", "free “Aggregated ads”: jobs reposted from the employer’s careers page, shown with low visibility", [("seek", "")]),
             ], "Free on both; here the job keeps its full place in the lists"),
        ]),
        ("Boosts for one job", [
            ("Standard boost", "30 days above the free jobs in its lists, a “Featured” mark, views and clicks", price_of("Standard boost"), "for 30 days, once", [
                ("Indeed", "no public price: you set a budget and pay per click or per started application. About $5–$25 a day, ≈$150–$750 for 30 days", [("indeed_est", "third-party estimate")]),
                ("Glassdoor", "no price of its own: jobs are posted on Indeed, and a sponsored Indeed job also shows on Glassdoor", [("glassdoor_in", "seen in a search summary")]),
                ("LinkedIn", "no public price: it appears while you post", [("linkedin", "")]),
                ("ZipRecruiter", "no public price: a third-party guide says its prices are not shown", [("zip", "")]),
                ("Niche job boards", "the top option for one post: about $447 at the median; “Best” at We Work Remotely is $458", [("niche6", ""), ("wwr", "")]),
                ("SEEK", "no published price for an Advanced ad. SEEK’s Jora site: “Plus” A$69, “Max” A$99 (≈US$45 / 64), length not stated", [("seek", ""), ("jora", "third-party, not verified")]),
                ("Naukri", "a “Hot Vacancy” post with a boost in search: ₹1,650 (≈US$19)", [("naukri_emp", "third-party")]),
             ], f"{dol(150 - SB)} to {dol(750 - SB)} less than 30 days of Indeed’s estimate" if SB < 150 else "Against ≈$150–$750 for 30 days at Indeed"),
            ("Premium boost", "a turn in the top 3, “Urgently hiring”, logo and cover, an invitation to up to 50 people", price_of("Premium boost"), "for 30 days, once", [
                ("Indeed", "a Premium sponsored job adds a top-of-page boost, the “Urgently hiring” label, logo and images, and invitations to matching people. "
                           "No public price; Premium always costs more than Standard", [("indeed", ""), ("indeed_how", "")]),
                ("SEEK", "a Premium ad: the most visible place in search and emails to matching candidates; no published price", [("seek", "")]),
                ("We Work Remotely", "“Best”, with a pin: $458 for one post; $617 a post with the 30-day pin, before the bundle discount", [("wwr", "")]),
             ], f"{dol(458 - PB)} less than the top post at We Work Remotely" if PB < 458 else "Against $458 at We Work Remotely"),
            ("Hiring Pass", "every job of one company for 30 days: unlimited Standard boosts, 3 Premium, the spotlight", price_of("Hiring Pass"), "for 30 days, once", [
                ("Indeed", "a typical spend of $500–$2,000 a month for 1–10 roles", [("vendr", "third-party")]),
                ("Jobright", "AI Recruiter: $499 a month for one recruiter, who works one role at a time", [("jobright_emp", "")]),
                ("ZipRecruiter", "no public price. Its average paying employer brought it about $561 a month: revenue per employer, not a price ($1,683 a quarter ÷ 3)", [("zip_sec", "")]),
                ("LinkedIn", "Hiring Pro and job slots: contact sales", [("linkedin", "")]),
                ("SEEK", "Ad Budgets paid in advance, from A$3,700 for about 8–12 ads (≈US$160–300 an ad); what is not used is lost at the end of the term", [("seek", ""), ("seek_budget", "third-party, not verified")]),
             ], f"Every job of one company for {price_of('Hiring Pass')}; a typical month at Indeed starts at $500, and Jobright’s $499 covers one role"),
        ]),
        ("Your company, seen first", [
            ("Company spotlight", "the home page and the top of the companies list, a badge on your page", price_of("Company spotlight"), "for 30 days, once", [
                ("Indeed and Glassdoor", "employer branding is sold by sales: one quoted package was $15,000 a year (21–50 jobs); add-ons about $500–$2,000+ a month", [("brand", "third-party, not verified")]),
                ("Glassdoor", "the paid employer profile: contact sales", [("glassdoor", "")]),
                ("SEEK", "“Company Profile Boost” and other brand products: fixed fees, not published", [("seek", "")]),
             ], f"{dol(1250 - SP)} less than one month of that $15,000 quote ($1,250, our arithmetic)" if SP < 1250 else "Against $1,250 a month in that quote"),
            ("Category or skill sponsor", "your name at the top of one category or skill page", price_of("Category or skill sponsor"), "for 30 days, once", [
                ("web3.career", "a banner slot in its job list: $1,999–$4,999 a month", [("web3ads", "")]),
                ("Indeed and Glassdoor", "brand add-ons: about $500–$2,000+ a month", [("brand", "third-party, not verified")]),
             ], f"{dol(1999 - CS)} less than web3.career’s cheapest slot" if CS < 1999 else "Against $1,999 at web3.career"),
        ]),
        ("Add-ons for one job", [
            ("Bump to top", "back to the top of its date-sorted lists; its real date stays on it", price_of("Bump to top"), "once", [
                ("web3.career", "pinned on top: $49 for 24 hours, $299 for 30 days", [("web3", "")]),
                ("Remote3", "pinned on top: $99 for 7 days", [("remote3", "")]),
                ("BOSS Zhipin", "extra visibility bought with coins at ¥1 each; the price of each item is not verified", [("boss", "")]),
             ], f"{price_of('Bump to top')} once; a day pinned on top is $49 at web3.career"),
            ("Extend a boost by 30 days", "for a boost running, or ended in the last 14 days", price_of("Extend a boost by 30 days"), "once per boost", [
                ("Indeed", "every extra day of a sponsored job is paid from the daily budget again: about $5–$25 a day", [("indeed_est", "third-party estimate")]),
                ("We Work Remotely", "another 30 days is a new post: $299", [("wwr", "")]),
             ], "30 more days for less than two days at Indeed’s low estimate" if XB < 10 else "30 more days, once"),
            ("Urgently hiring badge", "on a job posted here, or a listed job of a company whose page you claimed", price_of("Urgently hiring badge"), "for 14 days", [
                ("Indeed", "the “Urgently hiring” label comes only with a Premium sponsored job, which has no public price", [("indeed", "")]),
                ("SEEK", "an “Add-On Badge”: a fixed fee, not published; it changes how the ad looks, not where it ranks", [("seek", "")]),
             ], "On its own, without buying a Premium budget"),
        ]),
        ("Paying ahead, and finding people", [
            ("Prepaid credits", "1 credit = $1, for every product here; 12 months to spend them",
             (f"{credits_[0]['price']}–{credits_[-1]['price']}" if credits_ else "Credits"), (f"up to {bonus(credits_[-1])}" if credits_ and bonus(credits_[-1]) else "one top-up"), [
                ("SEEK", "Ad Budgets: paid in advance with a discount for size; the whole budget is charged even if unused, and what is left is lost at the end of the term", [("seek", "")]),
                ("We Work Remotely", "bundles from $179 a job, up to 40% off, used within 12 months", [("wwr", "")]),
                ("BOSS Zhipin", "coins at ¥1 each, spent on extras", [("boss", "")]),
                ("Indeed", "a bill on the 1st of each month, or when spending reaches $500", [("indeed", "")]),
             ], "A bonus of up to 20%, and nothing is billed afterwards"),
            ("Resume search", "50 contact requests among people who chose to be found", price_of("Resume search: 50 contact requests"), "for 50 requests", [
                ("Indeed", "Smart Sourcing: $400 a month (or $3,840 a year) for 100 contacts, $4 for each one more; a third-party guide gives $520 a month", [("smart", "sources differ")]),
                ("Naukri", "Resdex Lite: ₹4,000 (≈US$45) for 100 resume views over 90 days", [("naukri_emp", "third-party")]),
                ("Dice", "candidate views inside plans of $649–$899 a month", [("dice", "")]),
                ("SEEK", "talent search credits under a sales agreement; no published price", [("seek_ts", "")]),
             ], f"{per_contact} a contact, counted only when the person says yes; $4.00–$5.20 a contact at Indeed"),
        ]),
        ("If it does not work, and how you pay", [
            ("A free re-run", "a paid boost with fewer than 10 clicks on Apply in its first 14 days runs 30 more days", "Free", "automatic", [
                ("SEEK", "money back if nobody is hired within 4 weeks after the ad ends, only on its top fixed-fee ad, claimed within 28 days with proof", [("seek", "")]),
                ("Remotive", "200+ clicks on Apply or a free repost for another month, on posts from $299 a month", [("remotive", "")]),
                ("Indeed", "no such promise: you pay for each click or started application", [("indeed_how", "")]),
             ], "Nothing to claim: it happens by itself"),
            ("How you pay", "", "Once", "in crypto or credits; nothing renews", [
                ("Indeed", "a bill on the 1st of each month, or when spending reaches $500", [("indeed", "")]),
                ("Reviews", "people reviewing Indeed, LinkedIn, ZipRecruiter and We Work Remotely complain of trials that turned into charges and bills they did not expect", [("trustpilot", "")]),
             ], "No card on file, nothing to cancel"),
        ]),
    ])
    emp_vs = ('<div class="pvs"><div><p class="pvs-l">Elsewhere</p><p class="pvs-n">≈$150–$750</p><p>30 days of a sponsored job at Indeed: a third-party estimate, '
              'because Indeed publishes no price. LinkedIn, ZipRecruiter and Glassdoor publish none either.</p></div>'
              f'<div class="us"><p class="pvs-l">Here</p><p class="pvs-n">{e(price_of("Standard boost"))}</p><p>A Standard boost: 30 days above the free jobs, one payment. Posting itself is free.</p></div>'
              '<p class="pvs-s">Indeed: 100hires and Vendr guides, read 15 Nov 2026. LinkedIn, ZipRecruiter and Glassdoor: their own pages, read 13 Nov 2026.</p></div>')
    emp_sum = (f'<p class="cmp-sum"><b>In short:</b> posting is free here and costs $299 for 30 days at the median niche board. A Standard boost is {e(price_of("Standard boost"))}, '
               f'where 30 days of a sponsored job at Indeed are estimated at $150–$750. Resume search is {e(per_contact)} a contact, where Indeed’s Smart Sourcing works out at $4.00–$5.20. '
               'Every price here is printed, paid once and never renewed.</p>')

    # job seekers, product by product
    acct_word = "with an account, no card" if api_on else "with an account, opening soon"
    seek_rows_plus = [r_ for r_ in (
        ("Plus, 7 days", "every AI tool for a week", pl7["price"], "once", [
            ("Teal+", "$13 every 7 days, renewed until you cancel", [("teal", "")]),
            ("Jobright Turbo", "$17.99 a week", [("jobright", "third-party")]),
         ], f"{dol(13 - usd(pl7['price']))} less than Teal+, {dol(round(17.99 - usd(pl7['price']), 2))} less than Jobright") if pl7 else None,
        ("Plus, 30 days", "every AI tool for a month", pl30["price"], "once", [
            ("Teal+", "$29 every 30 days, renewed until you cancel", [("teal", "")]),
            ("Jobright Turbo", "$39.99 a month", [("jobright", "third-party")]),
            ("LinkedIn Premium Career", "$39.99 a month, or $19.99 a month paid for a year", [("li_prem", "secondary source")]),
            ("Naukri Pro", "₹999 (≈US$11) for a month", [("naukri_app", "")]),
            ("Job-search services", "$29 a month at the median of 11 that sell by the month", [("seek11", "")]),
         ], f"{dol(29 - usd(pl30['price']))} less than Teal+, {dol(round(39.99 - usd(pl30['price']), 2))} less than Jobright Turbo and LinkedIn Premium") if pl30 else None,
        ("Plus, 90 days", "every AI tool for three months", pl90["price"], "once", [
            ("Teal+", "$79 every 90 days, renewed until you cancel", [("teal", "")]),
            ("Jobright Turbo", "$89.99 a quarter", [("jobright", "third-party")]),
            ("Naukri Pro", "₹1,999 (≈US$23) for 3 months", [("naukri_app", "")]),
         ], f"{dol(79 - usd(pl90['price']))} less than Teal+, {dol(round(89.99 - usd(pl90['price']), 2))} less than Jobright Turbo") if pl90 else None) if r_]
    seek_rows_pass = [r_ for r_ in (
        ("One tailored resume", "your resume reworded for one posting, with its cover letter", ps_res["price"], "once, within 30 days", [
            ("Teal", "tailoring to a posting is part of Teal+, from $13 for 7 days", [("teal", "")]),
            ("Jobright", "2 AI-tailored resumes a day on the free plan; more with Turbo, from $17.99 a week", [("jobright", "third-party")]),
            ("Naukri", "an expert’s resume critique: ₹712 (≈US$8)", [("naukri_ff", "third-party, not verified")]),
         ], f"{dol(13 - usd(ps_res['price']))} less than the shortest Teal+; Jobright gives 2 a day free") if ps_res else None,
        ("One mock interview", "questions from one posting, feedback on up to 8 typed answers", ps_int["price"], "once, within 30 days", [
            ("Jobright", "interview packs: $19.99 for one company for 7 days, $39.99 for all companies for 30 days", [("jobright", "third-party")]),
            ("Naukri", "“Live AI Interviewer”: ₹749 or ₹999 (≈US$8.5–11)", [("naukri_app", "")]),
         ], f"{dol(round(19.99 - usd(ps_int['price']), 2))} less than Jobright’s pack for one company") if ps_int else None) if r_]
    seek_cmp = cmp_table([g_ for g_ in (
        ("Free here", [
            ("Every job and the link to apply", f"{n:,} open jobs, applied for on the employer’s own page", "Free", "no account", [
                ("Remotive", "most listings sit behind a paid tier: job seekers pay to unlock all jobs (price not shown)", [("remotive_j", "")]),
                ("Working Nomads", "Premium, $17.95 a month, promises about 10 times more postings", [("wn", "")]),
             ], "Free here; no job is held back for a payment"),
            ("Job alerts by email, saved jobs on every device", "new jobs that fit, by email; your list on the laptop and the phone", "Free", acct_word, [
                ("Jobright", "the free plan has 1 instant job alert and 1 saved filter; Turbo lifts the limits", [("jobright", "third-party")]),
                ("Teal", "tracking jobs is free there too", [("teal3", "third-party")]),
             ], "Free here, not part of Plus"),
            ("Resume builder", "5 templates, PDF and Word, no limit on downloads", "Free", "no account", [
                ("Rezi", "the free plan has 3 PDF downloads; Word files only in Pro, $29 a month", [("rezi", "")]),
                ("Teal", "the free plan has unlimited resumes and 11 templates, with limited AI", [("teal3", "third-party")]),
             ], "Free here; Word files cost $29 a month at Rezi"),
        ]),
        ("Plus: the AI help, one payment", seek_rows_plus),
        ("One task, one payment", seek_rows_pass),
        ("How you pay", [
            ("How you pay", "", "Once", "in crypto or credits; nothing renews", [
                ("Teal+", "renewed every period until you cancel; a cancellation takes effect at the end of the period", [("teal", "")]),
                ("LinkedIn Premium", "starts as a free trial for members who qualify", [("li_page", "")]),
                ("Reviews", "people reviewing LinkedIn and other job sites complain of trials that turned into charges they did not expect", [("trustpilot", "")]),
             ], "No card on file, nothing to cancel"),
        ])) if g_[1]])
    seek_vs = (f'<div class="pvs"><div><p class="pvs-l">Elsewhere</p><p class="pvs-n">$29</p><p>Every 30 days for Teal+, renewed until you cancel. '
               'Jobright Turbo and LinkedIn Premium Career: $39.99 a month.</p></div>'
               f'<div class="us"><p class="pvs-l">Here</p><p class="pvs-n">{e(pl30["price"] if pl30 else "")}</p><p>For 30 days of Plus: one payment that ends by itself. Jobs, alerts and the resume builder cost nothing.</p></div>'
               '<p class="pvs-s">Teal: its pricing page, read 13 Nov 2026. Jobright: third-party reviews of its August 2026 prices, read 15 Nov 2026. '
               'LinkedIn: a secondary source (activepieces.com), read 13 Nov 2026.</p></div>') if pl30 else ""
    seek_sum = ('<p class="cmp-sum"><b>In short:</b> searching, applying, job alerts and the resume builder are free here. '
                + (f'Plus is {e(pl30["price"])} for 30 days, where Teal+ is $29 and Jobright Turbo $39.99' if pl30 else "Plus costs less than Teal+ and Jobright Turbo")
                + (f'; one mock interview is {e(ps_int["price"])}, where Jobright’s pack for one company is $19.99' if ps_int else "")
                + '. Nothing here renews.</p>')

    # ---- /plus/: the AI help for job seekers. Sells the problem first, shows each tool as a small screen (marked as an example), then the prices.
    sale = bool(plus.get("live"))
    cta = '<a class="btn primary lg" href="#pay">Get Plus</a>' if sale else '<button class="btn primary lg" type="button" disabled>Not on sale yet</button>'
    buy_btn = ((lambda lbl: f'<a class="btn primary" href="{e(app_url or P + "/plus/")}">{e(lbl)}</a>') if sale else
               (lambda lbl: '<button class="btn primary" type="button" disabled>Not on sale yet</button>'))
    plans = "".join(
        f'<div class="plan{" best" if pl.get("best") else ""}">' + ('<span class="pill acc">Recommended by us</span>' if pl.get("best") else
                                                                     f'<span class="pill acc">{e(pl["note"])}</span>' if pl.get("note") else '<span class="pill ghost">–</span>')
        + f'<p class="pname">Plus · {e(pl["name"])}</p><p class="price">{e(pl["price"])}</p><p class="note">{e(pl.get("per") or "one payment")} · <b>{per_day(pl)}</b></p>{buy_btn("Get Plus")}</div>' for pl in plans_)
    passes = "".join(f'<div class="plan"><span class="pill ghost">–</span><p class="pname">{e(ps["name"])}</p><p class="price">{e(ps["price"])}</p>'
                     f'<p class="note">One payment</p><p class="pk-d">{e(ps["what"])}</p>{buy_btn("Buy this pass")}</div>' for ps in passes_)
    ex_ = '<span class="ex">example</span>'
    pcards = [
        ("AI resume review", "A read the way a recruiter reads: twenty seconds, top to bottom. You get a score, what the reader saw, what they could not find, and the lines to rewrite.",
         ex_ + '<span class="big">6<small>out of 10</small></span><span class="mt"><i style="width:60%"></i></span><span class="ln">First result appears on <b>page two</b> · no numbers in 7 of 9 bullets</span>'),
        ("Bullet points and a summary from your notes", "Write roughly what you did. The writer turns it into bullet points that start with a verb and a two-line summary, with numbers only where you gave them.",
         ex_ + '<span class="ln">Your notes: moved the catalogue to server rendering, pages got faster</span><span class="ln"><b>Moved catalogue rendering to the server, so pages load faster</b></span><span class="sk" style="width:74%"></span>'),
        ("Your resume, reworded for one posting", "The same resume sent everywhere rarely fits. Your own bullet points are reworded against the posting you picked, using only what is already in your resume, with the keywords it misses. You approve each line.",
         ex_ + '<span class="ln">Before: worked on the product catalogue</span><span class="ln"><b>After: cut catalogue load time by 40% by moving rendering to the server</b></span><span class="ln">Matches “performance” in the posting</span>'),
        ("Cover letter for the posting", "A draft built from your resume and the posting: a full letter for email, or four lines for a message to the recruiter. Ready to edit, so a letter stops costing an evening.",
         '<span class="ln"><b>Dear hiring team,</b></span><span class="sk" style="width:94%"></span><span class="sk h" style="width:58%"></span><span class="sk" style="width:88%"></span><span class="sk" style="width:40%"></span>'),
        ("Interview practice with feedback", "Up to 8 likely questions taken from the posting’s own requirements, each with the points from your resume that answer it. Type an answer and get back what was strong, what was missing and a tighter version in your own words.",
         ex_ + '<span class="ln"><b>1.</b> Tell us about a migration you led</span><span class="ln"><b>Strong:</b> a clear result, in numbers</span><span class="ln"><b>Missing:</b> what you would do differently</span><span class="ln">8 questions from 6 requirements</span>'),
    ]
    pcard_html = '<div class="tgrid">' + "".join(f'<div class="tcard"><span class="tprev" aria-hidden="true">{scr}</span><span class="tbody"><b>{e(t_)}</b><span>{e(d_)}</span></span></div>' for t_, d_, scr in pcards) + "</div>"
    free_now = "".join(f'<li><a href="{P}/{u}">{e(t_)}</a><span>free</span></li>' for u, t_ in (
        ("jobs/", "Every job and the link to apply, the moment we have it"), ("for-you/", "Matching by five answers, with the reason next to each job"), ("categories/", f"Browsing by {len(fam_rows)} fields and {len(by_role)} kinds of work"),
        ("salaries/", "Salary data from the pay ranges employers publish"), ("resume/", "Resume builder with Word and PDF"), ("tools/", "Every tool: resume match, pay calculators, letters, offer check"),
        ("my-jobs/", "Application tracker with reminders")) + ((("account/", "Job alerts by email and saved jobs on every device, with a free account"),) if api_on else ()))
    alerts_free = ("Job alerts by email, with a free account" if api_on else "Alerts in this browser, no account needed")
    saved_free = ("Saved jobs on every device, with a free account" if api_on else "Application tracker in this browser")
    tiers = ('<div class="tiers">'
             '<div class="tier"><p class="tn">Free</p><p class="tp">$0</p><p class="td">Everything you need to find a job and apply. No card.</p>'
             f'<a class="btn ghost" href="{P}/for-you/">Start with five questions</a>'
             + tick(["Every job and the link to apply", f"Search, {len(fam_rows)} fields of work, salary data", "Matching by five answers, with reasons", alerts_free, saved_free,
                     "Resume builder: 5 templates, PDF and Word", "Resume review and resume match by rules", "Letter templates: cover, thank-you, resignation", "Offer check and a letter for negotiating"]) + "</div>"
             '<div class="tier best"><p class="tn">Plus</p>'
             + (f'<p class="tp">{e(best_plan["price"])}<small> for {e(best_plan["name"])} · {per_day(best_plan)}</small></p>' if best_plan else '<p class="tp">Plus</p>')
             + '<p class="td">Everything in Free, plus the AI help: a writer for your resume and letters, rewording for each posting, and interview practice. One payment, nothing renews.</p>' + cta
             + tick(["AI resume writer and editor: bullet points and summary from your notes", "Resume reworded for each posting, with the keywords it misses", "AI resume review: score, weak points, rewrites",
                     "AI cover letters and resignation letters", "Interview practice: questions from the posting and feedback on your answers", f"Each calendar month: {ai_allow}"]
                    + ([f"Or one task: {ps_res['price']} for one tailored resume, {ps_int['price']} for one mock interview"] if ps_res and ps_int else [])
                    + ["One payment: nothing renews, no card on file"]) + "</div>"
             '<div class="tier"><p class="tn">Employers</p><p class="tp">Free<small> to post a job</small></p><p class="td">A standard listing costs nothing. A boost keeps a job above the free ones for 30 days.</p>'
             f'<a class="btn ghost" href="{P}/post-a-job/">Post a job</a>'
             + tick(["A standard listing for 30 days", f"Standard boost {price_of('Standard boost')}, Premium boost {price_of('Premium boost')}, 30 days each",
                     f"Hiring Pass {price_of('Hiring Pass')}: every job of one company", "Paid in crypto or credits, switched on by itself", "No calls, no sales manager"]) + "</div></div>")
    seek_pt = ptable([("Free", "<b>$0</b>", "No card; an account only for alerts and sync", False),
                      ("Plus", (f'from <b>{e(plans_[0]["price"])}</b>' if plans_ else "Plus"), "One payment. Nothing renews", True)], [
        ("Jobs",), ("Every job and the link to apply", True, True), ("Search, filters, categories, salary data", True, True), ("Matching by five answers, with reasons", True, True),
        ("Job alerts by email", "With a free account" if api_on else "~Opening with free accounts", "With a free account" if api_on else "~Opening with free accounts"),
        ("Saved jobs and applications", "On every device, with an account" if api_on else "~In this browser", "On every device, with an account" if api_on else "~In this browser"),
        ("Resume",), ("Resume builder, 5 templates, PDF and Word", True, True), (f"Resume examples for {len(rex_data)} kinds of work", True, True),
        ("Resume review and score", "~By rules", "By AI, with rewrites"), ("Keywords for one posting", "~Found and missing", "Bullets reworded for the posting"),
        ("AI writer for bullet points and summary", False, True),
        ("Letters",), ("Cover letter", "~Fill-in template", "AI draft from your resume and the posting"), ("Resignation letter", "~Template", "AI draft"),
        ("Thank-you and raise letters", "~Templates", "~Templates"),
        ("Interview and pay",), ("Interview questions", "~By role, with an answer builder", "From the posting, with your points"), ("Feedback on your typed answers", False, True),
        ("Salary checker, offer check, a letter for negotiating", True, True),
        ("AI use each calendar month", False, ai_allow),
        ("Payment",), ("How you pay", "~Nothing to pay", "Once, in crypto or credits"), ("Renews by itself", "~Nothing to renew", "Never")])
    soon = "" if sale else ('<div class="banner">Plus and the single passes are not on sale yet: they open when the AI service and payments are switched on. '
                            'This page shows what they will do and what they will cost. Everything in the free list works today.</div>')
    plus_qa = [("Is this a subscription?", "No. You pay once for the period you choose. When it ends, nothing is charged and there is nothing to cancel. There is no card on file to charge."),
               ("Do I have to pay to see or apply for jobs?", "No. Every job is public the moment we have it and free to apply to, on the employer’s own page. Plus adds help with applying; it does not unlock listings."),
               ("Are job alerts part of Plus?", ("No. Job alerts by email and saved jobs on every device come with a free account. " if api_on else
                                                 "No. Job alerts by email and saved jobs on every device will come with a free account. ") + "Plus is only the AI help."),
               ("What is the difference between Plus and a single pass?", (f"A pass is one task, paid once: {ps_res['price']} for one resume reworded for one posting, with its cover letter, "
                                                                           f"or {ps_int['price']} for one mock interview with feedback on up to 8 answers, each used within 30 days. " if ps_res and ps_int else "")
                + "Plus gives every AI tool for the period you choose."),
               ("How do I pay?", "With crypto (USDT, BTC, ETH and other coins) on a checkout page, or with prepaid credits. Plus turns on in your account once the network confirms the payment, at once with credits."),
               ("Is the resume help written by AI?", "Yes, the review, the rewording, the letters and the interview questions are. It works only from your own resume and the posting, adds no experience you do not have, and you approve every line before you use it."),
               ("How much can I use it?", f"Each calendar month: {ai_allow}. It is the same for every Plus plan and shown before you pay, and it is sized for an active job search."),
               ("Why does it cost less than Teal+ or Jobright Turbo?", "Plus is only the AI help: the job search around it is free, and the AI use has a monthly allowance, so what it costs us is known in advance. "
                + (f"30 days are {pl30['price']} here, $29 at Teal+ and $39.99 at Jobright Turbo (their prices as read on 13 and 15 Nov 2026)." if pl30 else "")),
               ("When does it launch?", "When the AI service and payments are switched on. Until then the free site works as it does today" + (", accounts and job alerts included." if api_on else "."))]
    page("plus/", f"Plus: AI resume help from {plans_[0]['price'] if plans_ else '$9'}, nothing renews | {SITE}",
         f"Plus rewords your resume for each posting, reviews it, drafts letters and runs interview practice. From {plans_[0]['price'] if plans_ else '$9'}, paid once; nothing renews.",
         crumbs(("Plus", "")) + '<h1>Applications go out and nothing comes back. Plus finds out why and <span class="hl">fixes it</span>, job by job</h1>'
         '<p class="lead">A resume gets one short first read, and nobody tells you why it was put aside: the result is on page two, the bullets list duties, the letter could be for any company. '
         f'Plus reads your resume the way a recruiter does, rewords it for each posting, drafts the letter and rehearses the interview with you. One payment, from {per_day(low_plan) if low_plan else "a few cents a day"}. Nothing renews.</p>{soon}'
         + tiers
         + section("Free and Plus, side by side", seek_pt + f'<p class="note">Hiring? Employers have their own table on the <a href="{P}/pricing/#employers">pricing page</a>.</p>')
         + section("What Plus adds", pcard_html)
         + section("What it costs", f'<div class="plans">{plans}</div><p class="note">You pay once, in crypto on a checkout page or with credits, and Plus switches on when the payment is confirmed. '
                   'There is no automatic renewal, no card on file and nothing to cancel: when the period ends, Plus simply ends. “Recommended by us” is our advice for an active search, not a count of sales.</p>', sid="pay")
         + (section("Or pay for one task", f'<div class="plans">{passes}</div><p class="note">A pass is the AI help for one posting, paid once and used within 30 days.</p>') if passes_ else "")
         + section("Plus against Teal+, Jobright Turbo and others", seek_vs + seek_sum + seek_cmp)
         + section("What stays free, for everyone", f'<div class="dir free"><div class="dirb"><ul>{free_now}</ul></div></div>')
         + section("Questions about Plus", faq_html(plus_qa)), head=faq_ld(plus_qa))

    # ---- /post-a-job/
    steps = ('<ol class="steps"><li><b>Create an employer account.</b> With your work email, or with Google.</li>'
             "<li><b>Paste the job.</b> Title, link to apply, location, description. We open the link to check the job is really there.</li>"
             "<li><b>A standard listing is free.</b> It goes live after the check, at the next hourly update. To keep it higher, add a boost and pay at the crypto checkout (USDT, BTC, ETH and other coins) or with credits.</li>"
             "<li><b>A boost switches on by itself</b> once the network confirms the payment, at once when paid with credits. When its 30 days end, the job goes back to a standard listing: nothing renews and nothing more is charged.</li></ol>")
    if app_url:
        pay = (f'<section class="sec"><div class="sec-head"><h2>How to post a job</h2><a href="{e(app_url)}">Open the employer account</a></div>{steps}'
               f'<p><a class="btn primary lg" href="{e(app_url)}">Post a job now</a></p></section>')
    else:
        pay = (f'<section class="sec"><div class="sec-head"><h2>How posting a job will work</h2></div>{steps}'
               '<div class="banner">Self-serve posting is being finished and is not open yet. Nothing can be bought today.'
               + (f" Questions in the meantime: {mail_a('jobs')}." if MAIL.get("jobs") or contact else "") + "</div></section>")
    pains = [("Lists are sorted by date", f"{WEEKNEW:,} roles were posted here in the last 7 days, so a job without a boost leaves the first page within days."),
             ("Roles without pay get filtered out", f"{100 - SALPCT}% of postings here show no salary. Anyone who filters or sorts by pay never sees them. Adding a range costs nothing."),
             ("A boost holds the place", "A boosted job stays above the free jobs of its category, role, place and search for 30 days, whatever is posted after it.")]
    pain_html = '<div class="feats">' + "".join(f'<div class="feat"><h3>{e(a)}</h3><p>{e(b)}</p></div>' for a, b in pains) + "</div>"
    etick = tick
    ebtn = emp_btn(False, here=True)
    emp_tiers = ('<div class="tiers">'
                 f'<div class="tier"><p class="tn">Standard</p><p class="tp">Free<small> for 30 days</small></p><p class="td">Your job in the list and in search, like every other job here.</p>{ebtn}'
                 + etick(["30 days in the list and in search", "Its own page, readable by Google’s job box", "A link straight to your application page", "Checked before it goes live", "Close it or post it again yourself, any time"]) + "</div>"
                 f'<div class="tier best"><p class="tn">Standard boost <span class="tchip">Our advice for most roles</span></p><p class="tp">{e(price_of("Standard boost"))}<small> for 30 days</small></p>'
                 f'<p class="td">A highlighted row with a “Featured” mark, above the free jobs in its lists for 30 days.</p>{emp_btn(True, here=True)}'
                 + etick(["Everything in Standard", "Highlighted row with a “Featured” mark", "Above the free jobs in its category, role, place and search lists", "Views and clicks on Apply for the job, in your account",
                          "For a job posted here, or one we list from your careers page", "A free re-run if it gets fewer than 10 clicks on Apply in 14 days"]) + "</div>"
                 f'<div class="tier"><p class="tn">Premium boost</p><p class="tp">{e(price_of("Premium boost"))}<small> for 30 days</small></p><p class="td">A turn in the top 3 of its lists, an “Urgently hiring” badge and an invitation to people who match.</p>{ebtn}'
                 + etick(["Everything in the Standard boost", "Takes turns in the top 3 slots of its lists, hour by hour when more than 3 share a list", "“Urgently hiring” badge for the first 14 days",
                          "Your logo and a cover image on the job page", "One email to up to 50 matching job seekers who asked for job invitations", "Views and clicks day by day",
                          "A job we list from your careers page needs the company page claimed first"]) + "</div></div>")
    emp_pt = ptable([("Standard", "<b>Free</b>", "30 days in the list", False),
                     ("Standard boost", f'<b>{e(price_of("Standard boost"))}</b> once', "30 days above the free jobs", True),
                     ("Premium boost", f'<b>{e(price_of("Premium boost"))}</b> once', "30 days, a turn in the top 3", False)], [
        ("The listing",), ("In the list and in search", "30 days", "30 days", "30 days"), ("Its own page, readable by Google’s job box", True, True, True),
        ("A link straight to your application page", True, True, True), ("Checked before it goes live", True, True, True),
        ("Works for a job we list from your careers page", "~Listed free already", True, "~After you claim the company page"),
        ("Where it stands",), ("Place in its lists: category, role, place, search", "~By date", "Above the free jobs", "Top 3, taking turns"),
        ("Highlighted row with a “Featured” mark", False, True, True), ("“Urgently hiring” badge", False, f"~{price_of('Urgently hiring badge')} extra, 14 days", "First 14 days"),
        ("Your logo and a cover image on the job page", False, False, True),
        ("Reaching people",), ("Invitation email to matching job seekers who opted in", False, False, "Up to 50, once"),
        ("Your account",), ("Views and clicks on Apply", False, "For the job", "Day by day"), ("A free re-run if under 10 clicks on Apply in 14 days", False, True, True),
        ("A receipt for every payment", "~Nothing to pay", True, True),
        ("Payment",), ("How you pay", "~Nothing to pay", "Once, in crypto or credits", "Once, in crypto or credits"),
        ("Starts", "~After the check, at the next hourly update", "When the payment is confirmed", "When the payment is confirmed"), ("Renews by itself", "~Nothing to renew", "Never", "Never")])
    pass_box = ('<div class="ppass">' + pcard("Hiring Pass", price_of("Hiring Pass"), "for 30 days", "Every job of one company, boosted for 30 days.", emp_btn(True, here=True, label="Open the employer account"), "One payment for one company. Nothing renews.")
                + '<div class="pincl"><p class="pk-n">For 30 days, for one company</p>'
                + tick(["Unlimited Standard boosts for its jobs during the 30 days; each boost runs its own 30 days","3 Premium boosts", "The company spotlight for the 30 days", "Views and clicks for every job",
                        "For a company that is yours: you posted a job under its name or claimed its page"])
                + f'<p class="note">Bought one by one, 3 Premium boosts and the spotlight come to {dol(3 * PB + SP)} (3 × {e(price_of("Premium boost"))} + {e(price_of("Company spotlight"))}), '
                  f'before any Standard boost at {e(price_of("Standard boost"))} each.</p></div></div>')
    addon_names = ("Bump to top", "Extend a boost by 30 days", "Urgently hiring badge", "Company spotlight", "Category or skill sponsor")
    addons = '<div class="paddons">' + "".join(acard(x, price_of(x), term(x), PRICE[x]["what"]) for x in addon_names if x in PRICE) + "</div>"
    credit_cards = ('<div class="paddons c4">' + "".join(acard(p_["name"], p_["price"], "one top-up", "", chip=bonus(p_)) for p_ in credits_) + "</div>"
                    + tick(["1 credit = $1", "Credits last 12 months from the top-up", "Spend them on every product here, and on Plus and the passes for job seekers",
                            "A purchase paid with credits switches on at once: no wait for the network", "A top-up is one payment in crypto; nothing renews"])) if credits_ else ""
    rs_box = ('<div class="ppass">' + pcard("Resume search", price_of("Resume search: 50 contact requests"), "for 50 contact requests", "Search the resumes of people who chose to be found.",
                                            emp_btn(False, here=True, label="Open the employer account"), "One payment. Nothing renews.")
              + '<div class="pincl"><p class="pk-n">How it works</p>'
              + tick(["Only resumes people chose to make findable: nobody is in it without saying yes", "Names and contacts stay hidden until the person accepts your request",
                      "A request is used up only when the person accepts", "Declined, or no answer in 14 days: the request comes back to you",
                      f"{per_contact} a contact who said yes"])
              + '<p class="note">Only people who opted in are there, so the database starts small and grows.</p></div></div>') if "Resume search: 50 contact requests" in PRICE else ""
    demo_rows = [dict(j) for j in latest[:3]]
    demo_job = {"featured": True, "active": True, "remote": True, "salary": "$140K - $180K", "level": "", "tags": [], "location": "Remote, Europe", "company": "Your company",
                "slug": "", "title": "Senior Backend Engineer (your Premium boost)", "posted": TODAY}      # few pills: the urgent badge must fit in the row
    urgent = '<span class="pill urg">Urgently hiring</span>'
    prem_row = (eg(card(demo_job)).replace('<li class="job feat">', '<li class="job feat prem">', 1)
                .replace('<span class="pill acc">Featured</span>', '<span class="pill acc">Featured</span>' + urgent, 1))
    demo_html = ('<ul class="jobs demo">' + prem_row + eg(card(dict(demo_job, title="Product Designer (your Standard boost)", salary="", tags=["Figma"], level="")))
                 + "".join(card(j) for j in demo_rows) + "</ul>")
    prem_page = ('<div class="pjob"><div class="pjob-cover" aria-hidden="true"><span class="ex">example</span></div><div class="pjob-head"><span class="pjob-logo" aria-hidden="true">Y</span>'
                 + '<div><b>Senior Backend Engineer</b><span>Your company · Remote, Europe · $140K – $180K</span></div>' + urgent + "</div>"
                 '<div class="pjob-body" aria-hidden="true"><span class="sk" style="width:92%"></span><span class="sk" style="width:78%"></span><span class="sk" style="width:86%"></span></div></div>'
                 '<p class="note">An example: the cover image and logo are yours; the badge goes after 14 days.</p>')
    emp_cab = ('<div class="tgrid">'
               '<div class="tcard"><span class="tprev" aria-hidden="true"><span class="ex">example</span><span class="ln"><b>Senior Backend Engineer</b></span><span class="rw"><span>Boost</span><span class="mt"><i style="width:86%"></i></span><b>26 days left</b></span>'
               '<span class="ln">Live since Nov 13 · <b>Extend</b> · <b>Close</b></span></span><span class="tbody"><b>The boost, switched on</b><span>The moment the network confirms the payment, or at once with credits, the job is marked Featured and the account shows how many days are left. Nothing to send, nobody to wait for.</span></span></div>'
               '<div class="tcard"><span class="tprev" aria-hidden="true"><span class="ex">example</span><span class="rw"><span>Views</span><span class="mt"><i style="width:100%"></i></span><b>1,204</b></span><span class="rw"><span>Clicks on Apply</span><span class="mt"><i style="width:22%"></i></span><b>86</b></span>'
               '<span class="ln">Counted per job, day by day</span></span><span class="tbody"><b>What the listing brought</b><span>Views of the job page and clicks on “Apply” for each job, so you can see what the boost did, and whether the free re-run is due.</span></span></div>'
               f'<div class="tcard"><span class="tprev" aria-hidden="true"><span class="ex">example</span><span class="ln"><b>Receipt</b> · Standard boost · {e(price_of("Standard boost"))}</span><span class="ln">Paid in USDT · confirmed 14:02</span><span class="sk" style="width:70%"></span></span>'
               '<span class="tbody"><b>A receipt and no renewal</b><span>Every payment is a single payment with a receipt in the account. When the 30 days end, the job goes back to a standard listing and nothing is charged.</span></span></div></div>')
    emp_trust = trust(["A standard listing is free", "One payment, nothing renews", "Paid in crypto or credits, no card", "Switches on by itself once paid", "A free re-run if a boost brings under 10 clicks"])
    pj_qa = [("Where can I post a job for free?", f"Here: a standard listing is free, with its own page and 30 days in the list, among {n:,} open roles from {m:,} companies. "
              + ("Post it from the employer account." if app_url else "Self-serve posting is being finished; until it opens, write to " + (MAIL.get("jobs") or "us") + ".")
              + " Several big job boards also have a free tier with limits; the site-by-site comparisons on this site show who charges for what."),
             ("Is posting a job here really free?", "Yes. A standard listing costs nothing and needs no card. A boost only keeps a job higher in its lists; nothing is charged unless you buy one."),
             ("How much does it cost to boost a job?", f"A Standard boost is {price_of('Standard boost')} for 30 days: a highlighted row above the free jobs in its lists. A Premium boost is {price_of('Premium boost')}: "
              "a turn in the top 3, an “Urgently hiring” badge, your logo and cover image, and an invitation to up to 50 matching job seekers. "
              f"A Hiring Pass is {price_of('Hiring Pass')} for every job of one company for 30 days. Each is one payment in crypto or credits; nothing renews."),
             ("What if a boost brings no applicants?", "If a Standard or Premium boost that was paid for gets fewer than 10 clicks on Apply in its first 14 days, it runs for 30 more days at no cost, by itself. "
              "It counts clicks on Apply; it cannot promise a hire."),
             ("Can I boost a job you already list from my careers page?", "Yes. Company pages carry “Is this your job? Boost it”. A Standard boost works on any of your listed jobs; "
              "a Premium boost, a Hiring Pass or an urgent badge on a listed job needs the company page claimed first, with a work email or a DNS record."),
             ("Can I post a job on Google for free?", "Google does not take job posts itself: its job search reads job pages that carry JobPosting structured data. Every open job here with a full description "
              "has its own page with that data, so a free listing here can appear in Google’s job search."),
             ("Can I post a job without registering?", "Self-serve posting asks for an email, so that only you can close the job or buy a boost for it. And if your openings are on a careers page we already read "
              "(Greenhouse, Lever, Ashby and other hiring systems), they appear here by themselves, free and with no account; to have your careers page read, write to " + (MAIL.get("jobs") or "us") + "."),
             ("How do I post a job for free online?", "Write the title, the place of work, the pay range and what the person will do; add the link where people apply; post it on free boards such as this one "
              "and on your own careers page; share it with people who do that work. A posting that states pay and a place gets more of the right applicants.")]
    page("post-a-job/", f"Post a Job for Free, Boost It from {price_of('Standard boost')} | {SITE}" if app_url else f"Post a Job for Free: Listings, Boosts and Prices | {SITE}",
         (f"Post a job for free for 30 days. A boost keeps it above the free jobs for 30 days from {price_of('Standard boost')}, paid once in crypto. Nothing renews." if app_url else
          f"Employer prices: free 30-day listings, boosts from {price_of('Standard boost')}, a Hiring Pass, credits and resume search. Self-serve posting is not open yet."),
         crumbs(("For employers", "")) + "<h1>Post a job that doesn’t get buried</h1>"
         f'<p class="lead">There are {n:,} open roles from {m:,} companies here, sorted by date. A standard listing is free. '
         'A boost keeps a job above the free ones for 30 days instead of letting it slide down as new roles arrive. One payment, in crypto; nothing renews.</p>'
         + emp_trust + emp_tiers
         + section("Standard, Standard boost and Premium boost, side by side", emp_pt + f'<p class="note">“Our advice” is ours, for a role that has to be seen this month; it is not a count of sales. '
                   f'Looking for work, not hiring? Job seekers have their own table on the <a href="{P}/pricing/">pricing page</a>.</p>')
         + section("Hiring Pass: every job of one company", pass_box)
         + section("Add-ons, one payment each", addons)
         + (section("Credits: top up once, spend on anything", credit_cards) if credit_cards else "")
         + (section("Resume search", rs_box) if rs_box else "")
         + section("If a boost brings no one", guarantee)
         + section("Why jobs slide out of sight", pain_html)
         + section("How your job looks in the list", '<p class="note">The first row is an example of a Premium boost, the second of a Standard boost; the others are real listings from today.</p>' + demo_html)
         + section("What a Premium boost adds to the job page", prem_page)
         + section("What appears in your account at once", emp_cab)
         + section("How a company spotlight looks", '<div class="spot"><a class="eg">' + ava("Your company") + '<span><b>Your company</b><span class="s">42 open roles · featured</span></span></a></div>'
                   '<p class="note">Shown on the home page and at the top of the companies list.</p>')
         + section("What the same things cost elsewhere", emp_vs + emp_sum + emp_cmp) + pay
         + '<section class="sec"><div class="sec-head"><h2>Paying, careers pages and refunds</h2></div>'
         "<h3>How do I pay?</h3><p>In crypto, on a checkout page: USDT, BTC, ETH and other coins, or with prepaid credits. A purchase switches on after the payment is confirmed, at once with credits. We do not take cards or bank transfers yet.</p>"
         "<h3>No careers page of your own?</h3><p>Use your company page here as one. Link your site's Careers button to it, or embed the list with one line of code: "
         f'<a href="{P}/widgets/">badge and widget</a>.</p>'
         "<h3>What happens when the job closes?</h3><p>It is marked as closed and its page stays online.</p>"
         "<h3>Can I get a refund?</h3><p>A purchase switches on the moment the payment is confirmed, so there is nothing to refund before it runs. A boost with fewer than 10 clicks on Apply in 14 days runs again for free. "
         "If anything paid did not run as described, write to us and it will be extended or refunded.</p></section>"
         + section("Questions about posting a job for free", faq_html(pj_qa)), head=faq_ld(pj_qa))

    # ---- /pricing/: both sides on one page, each with its own cards and tables. A person looking for work and a company hiring buy
    # different things, so they never share a table (the owner: "for the job seeker and for the employer everything must be different").
    price_qa = [("Do I have to pay to see jobs or to apply?", "No. Every job is public and free to apply to, on the employer’s own page. Plus adds help with applying; it does not unlock listings."),
                ("Are job alerts free?", ("Yes. Job alerts by email and saved jobs on every device come with a free account. " if api_on else
                                          "Yes. Job alerts by email and saved jobs on every device will come with a free account. ") + "Plus is only the AI help."),
                ("How do I pay?", "In crypto, on a checkout page: USDT, BTC, ETH and other coins, or with prepaid credits. Cards and bank transfers are not taken yet."),
                ("Will I be charged again?", "No. Every price here is a single payment. Nothing renews by itself, there is no card on file and nothing to cancel."),
                ("When does a purchase start?", "By itself, once the network confirms the payment, and at once when it is paid with credits. A new job still has to pass the check before it goes live; paying does not skip it."),
                ("Why are the prices lower than at Indeed or Teal?", "Prices here are fixed and printed, paid once, with no sales team and no auction, and the job search around them is free. "
                 f"A Standard boost is {price_of('Standard boost')} for 30 days, where a sponsored job at Indeed is estimated at $150–$750"
                 + (f"; 30 days of Plus are {pl30['price']}, where Teal+ is $29." if pl30 else ".")),
                ("What are credits?", "Prepaid dollars: 1 credit = $1, with a 10% bonus on a $500 top-up and 20% on $1,000. They last 12 months from the top-up and pay for every product here, "
                 "for employers and job seekers; a purchase paid with credits starts at once."),
                ("What if a boost brings no one?", "If a Standard or Premium boost that was paid for gets fewer than 10 clicks on Apply in its first 14 days, it runs for 30 more days at no cost, by itself."),
                ("Can I buy today?", ("Posting a standard listing is open in the employer account, and paid products are bought from the same account. Until crypto payments are switched on, "
                                      "the account says so and nothing can be charged. " if app_url else
                                      "Not yet. Payments are being connected; until then everything in the Free and Standard columns works as it does today. ")
                 + "Plus and the passes open when the AI service and payments are on.")]
    seek_trust = trust(["One payment, nothing renews", "No card kept on file", "Paid in crypto or credits", "Jobs, alerts and the resume builder stay free"])
    seek_cards = ('<div class="pgrid">'
                  + pcard("Free", "$0", "forever", "Everything needed to find a job and apply.", f'<a class="btn ghost" href="{P}/for-you/">Start free</a>', "No card.",
                          ticks=["Every job and the link to apply", f"Search, {len(fam_rows)} fields of work, salary data", alerts_free, saved_free, "Resume builder: 5 templates, PDF and Word",
                                 "Resume examples and letter templates"])
                  + '<div class="pside"><div class="pcards c3">'
                  + "".join(pcard(f"Plus · {pl['name']}", pl["price"], f"for {pl['name']}", " · ".join(x for x in (pl.get("per", ""), per_day(pl)) if x), plus_btn(pl.get("best")),
                                  "One payment. It ends by itself; nothing renews.", chip=pl.get("note", ""), best=bool(pl.get("best"))) for pl in plans_)
                  + '</div><div class="pincl"><p class="pk-n">Every Plus plan includes everything in Free, and</p>'
                  + tick(["AI resume writer and editor", "Resume reworded for each posting, with the keywords it misses", "AI resume review: score and rewrites", "AI cover and resignation letters",
                          "Interview practice: questions from the posting, feedback on your answers", f"Each calendar month: {ai_allow}"]) + "</div></div></div>") if plans_ else ""
    seek_passes = (('<h3 class="cmp-h">Or pay for one task</h3><div class="paddons">'
                    + "".join(acard(ps["name"], ps["price"], "once", ps["what"]) for ps in passes_) + "</div>") if passes_ else "")
    seek_fit = fit([r_ for r_ in (
        (pl7["name"], "A few applications to send this week, with their letters and the interview practice.") if pl7 else None,
        (pl30["name"], "An active search: dozens of applications, each with its own resume and letter. Our advice for most people.") if pl30 else None,
        (pl90["name"], "A long search, or one that has not started yet. The lowest price a day.") if pl90 else None,
        ("One pass", f"One posting that matters: {ps_res['price']} for the resume and letter, {ps_int['price']} for a mock interview.") if ps_res and ps_int else None) if r_])
    emp_cards = ('<div class="pcards c3">'
                 + pcard("Standard", "Free", "for 30 days", "Your job in the list and in search, like every other job here.", emp_btn(False),
                         ticks=["Its own page, readable by Google’s job box", "A link straight to your application page", "Checked before it goes live", "Close it yourself, any time"])
                 + pcard("Standard boost", price_of("Standard boost"), "for 30 days", "A highlighted row above the free jobs in its lists.", emp_btn(True), "One payment per job.", best=True,
                         ticks=["Everything in Standard", "Highlighted row with a “Featured” mark", "Above the free jobs for 30 days", "Views and clicks on Apply in your account", "A free re-run if under 10 clicks"])
                 + pcard("Premium boost", price_of("Premium boost"), "for 30 days", "A turn in the top 3, the urgent badge and an invitation to people who match.", emp_btn(False), "One payment per job.",
                         ticks=["Everything in the Standard boost", "Top 3 of its lists, taking turns", "“Urgently hiring” for the first 14 days", "Your logo and a cover image", "One email to up to 50 matching job seekers"]) + "</div>")
    extra_rows = "".join(f"<tr><td><strong>{e(p_['name'])}</strong></td><td><strong>{e(p_['price'])}</strong> <span class=\"note\">{e(term(p_['name']))}</span></td><td>{e(p_['what'])}</td></tr>"
                         for p_ in CFG["prices"] if p_["name"] not in ("Standard listing", "Standard boost", "Premium boost") and not is_credits(p_["name"]))
    if credits_:      # the four top-ups in one row: the same product at four sizes
        extra_rows += ("<tr><td><strong>Prepaid credits</strong></td><td>" + ", ".join(f"<strong>{e(p_['price'])}</strong>" + (f" for {e(p_['name'])}" if bonus(p_) else "") for p_ in credits_)
                       + '</td><td>1 credit = $1, with a bonus on the two larger top-ups. Credits pay for every product here, for employers and job seekers, and last 12 months '
                         "from the top-up; a purchase paid with credits switches on at once.</td></tr>")
    emp_fit = fit([("Standard", "One role and no hurry. It is in the list and in search like every other job."),
                   ("Standard boost", "A role that must be seen this month. Our advice for most roles."),
                   ("Premium boost", "A hard or urgent hire: the top 3 of its lists, the urgent badge and an invitation to people who match."),
                   ("Hiring Pass", "Several open roles at one company: every job boosted for 30 days, three of them Premium, and the spotlight.")])
    emp_trust_p = trust(["A standard listing is free", "One payment, nothing renews", "On by itself once paid", "Paid in crypto or credits"])
    page("pricing/", f"Pricing: Free Job Search, Plus from {plans_[0]['price'] if plans_ else '$9'}, Boosts from {price_of('Standard boost')} | {SITE}",
         f"What is free and what is paid. Job seekers: every job, alerts and the resume builder are free; AI Plus from {plans_[0]['price'] if plans_ else '$9'}. Employers: posting is free, boosts from {price_of('Standard boost')}.",
         crumbs(("Pricing", "")) + '<h1>Pricing: what is free and <span class="hl">what you pay for</span></h1>'
         '<p class="lead">Two sets of plans, because a person looking for work and a company hiring buy different things. Every price is one payment in crypto; nothing renews. Pick yours.</p>'
         '<p class="tabs pswitch" id="pswitch" hidden><button class="tab" type="button" data-v="s" aria-pressed="true">I’m looking for work</button><button class="tab" type="button" data-v="e" aria-pressed="false">I’m hiring</button></p>'
         + f'<section class="sec" id="for-seekers"><div class="sec-head"><h2>Looking for work</h2><a href="{P}/plus/">What Plus does</a></div>{soon}{seek_trust}{seek_cards}{seek_passes}'
           f'<h3 class="cmp-h">Plus against Teal+ and Jobright Turbo</h3>{seek_vs}<h3 class="cmp-h">Which plan fits</h3>{seek_fit}'
           '<p class="note">“Recommended by us” is our advice for an active search, not a count of sales.</p>'
           f'<h3 class="cmp-h">Free and Plus, line by line</h3>{seek_pt}<h3 class="cmp-h">What the same things cost elsewhere</h3>{seek_sum}{seek_cmp}'
           f'<p><a class="btn primary" href="{P}/for-you/">Start free with five questions</a> <a class="btn ghost" style="margin-top:0" href="{P}/plus/">See Plus</a></p></section>'
         + f'<section class="sec" id="for-employers"><div class="sec-head"><h2>Hiring</h2><a href="{P}/post-a-job/">See how a boost looks</a></div>'
           + ("" if app_url else '<div class="banner">Self-serve posting is being finished and is not open yet. Nothing can be bought today.</div>') + emp_trust_p + emp_cards + emp_vs
           + '<h3 class="cmp-h">Which plan fits</h3>' + emp_fit + '<p class="note">“Recommended by us” is our advice for a role that has to be seen this month, not a count of sales.</p>'
           + '<h3 class="cmp-h">Standard, Standard boost and Premium boost, line by line</h3>' + emp_pt
           + f'<h3 class="cmp-h">Hiring Pass, add-ons, credits and resume search</h3><div class="tablewrap"><table><tr><th>Product</th><th>Price</th><th>What you get</th></tr>{extra_rows}</table></div>'
           + '<h3 class="cmp-h">Our guarantee</h3>' + guarantee
           + '<h3 class="cmp-h">What the same things cost elsewhere</h3>' + emp_sum + emp_cmp
           + f'<p><a class="btn primary" href="{P}/post-a-job/">Post a job</a></p></section>'
         + section("Questions about prices and payment", faq_html(price_qa)), head=faq_ld(price_qa))
    # "Jobs near me" and "part time jobs near me": among the most searched job phrases in every country.
    # The country comes from the device's time zone (nothing is sent anywhere); the nearest city only if the visitor allows location, and it is worked out in the browser.
    CITY_LL = {"new-york": (40.71, -74.01), "san-francisco": (37.77, -122.42), "seattle": (47.61, -122.33), "austin": (30.27, -97.74), "chicago": (41.88, -87.63), "boston": (42.36, -71.06),
               "washington-dc": (38.91, -77.04), "denver": (39.74, -104.99), "los-angeles": (34.05, -118.24), "dallas": (32.78, -96.80), "atlanta": (33.75, -84.39), "san-diego": (32.72, -117.16),
               "pittsburgh": (40.44, -80.00), "portland": (45.52, -122.68), "miami": (25.76, -80.19), "phoenix": (33.45, -112.07), "raleigh-durham": (35.78, -78.64), "houston": (29.76, -95.37),
               "toronto": (43.65, -79.38), "vancouver": (49.28, -123.12), "berlin": (52.52, 13.40), "munich": (48.14, 11.58), "bangalore": (12.97, 77.59), "sydney": (-33.87, 151.21),
               "london": (51.51, -0.13), "manchester": (53.48, -2.24), "paris": (48.86, 2.35), "amsterdam": (52.37, 4.90), "dublin": (53.35, -6.26), "madrid": (40.42, -3.70),
               "barcelona": (41.39, 2.17), "lisbon": (38.72, -9.14), "zurich": (47.38, 8.54), "stockholm": (59.33, 18.07), "warsaw": (52.23, 21.01), "tel-aviv": (32.08, 34.78),
               "tokyo": (35.68, 139.69), "montreal": (45.50, -73.57), "hyderabad": (17.39, 78.49), "melbourne": (-37.81, 144.96),
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
         '<form class="mapform" id="mapform" role="search"><input type="search" id="mapq" name="q" placeholder="A job, a skill or a company, for example nurse or python" aria-label="Search the map">'
         '<button class="btn primary" type="submit">Show on map</button></form>'
         '<div class="mapwrap"><div class="jobmap" id="jobmap" role="region" aria-label="Map of open jobs by city"></div>'
         '<aside class="mappanel" id="mappanel" aria-live="polite" hidden></aside></div><p class="note" id="mapnote">The map needs JavaScript. Every city is listed below.</p>'
         + section("Cities with the most open jobs", f'<ul class="tiles">{map_tiles}</ul>', ("locations/", "Jobs by country"))
         + section("Questions about the jobs map", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in map_qa) + "</dl>")
         + f'<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js" defer></script><script src="{P}/map.js?v={V}" defer></script>', head=map_ld)

    # How long job postings stay open: a study from our own hourly checks (the owner's plan, section 101: a report with our own figures,
    # the kind that brought Rezi links from the press). Every figure is recounted on each build. Measured counts are stated as counts;
    # the share closed within 7 / 30 / 90 days is an estimate from the daily closing rates seen so far, and the page says what it rests on.
    if SURV:
        BND_ = (7, 30, 90, 10 ** 6)
        def curve(hz, upto=400):
            """Share of postings still open d days after posting (d = 0..), from the daily closing chance in each age band; stops at the
            first band without enough data."""
            out, p_ = [1.0], 1.0
            for a in range(upto):
                x = hz[next(i for i, u in enumerate(BND_) if a <= u)] if hz else None
                if x is None: break
                p_ *= 1 - x; out.append(p_)
            return out
        S_all = curve(SURV["all"])
        at = lambda S, d: S[d] if S and d < len(S) else None
        pc = lambda x: f"{round(100 * x)}%"
        since_s, days_s = fdate(SURV["since"].isoformat()), SURV["days"]
        # How far the estimate may reach: a few days of records say little about postings that stay up for months (on 14 Nov 2026,
        # three days of closings projected 2% of postings still open at 180 days, while 33% of the open jobs were already over 90 days old).
        reach = 30 if days_s < 30 else 90 if days_s < 90 else 180
        early = days_s < 14
        c7, c30, c90 = (None if at(S_all, d) is None or d > reach else 1 - at(S_all, d) for d in (7, 30, 90))
        half_d = next((d for d, v in enumerate(S_all) if v <= 0.5 and d <= reach), None)
        cl_real = [j for j in archived if (j["company"], j.get("closed")) not in MOVED and j.get("posted") and j.get("closed")]
        def days_between(a, b):
            try: return max(0, (datetime.date.fromisoformat(b[:10]) - datetime.date.fromisoformat(a[:10])).days)
            except ValueError: return None
        age_cl = sorted(x for x in (days_between(j["posted"], j["closed"]) for j in cl_real) if x is not None)
        med_cl = age_cl[len(age_cl) // 2] if age_cl else 0
        ages_o = [age_days(j) for j in active]
        old90 = sum(1 for a in ages_o if a > 90)
        AGE_B = [(0, 7, "0–7"), (8, 30, "8–30"), (31, 90, "31–90"), (91, 180, "91–180"), (181, 365, "181–365"), (366, 10 ** 6, "366+")]
        age_pts = [(lb, k_, f"{lb} days since posting · {k_:,} open jobs") for lo, hi, lb in AGE_B for k_ in [sum(1 for a in ages_o if lo <= a <= hi)]]
        cl_pts = [(lb, k_, f"{lb} days after posting · {k_:,} closings") for lo, hi, lb in AGE_B for k_ in [sum(1 for a in age_cl if lo <= a <= hi)]]
        # by field: the estimated share closed within 30 days, where the field had enough closings
        fld = []
        for cs, hz in SURV["cat"].items():
            if cs == OTHER[0]: continue
            S_ = curve(hz, 30)
            if at(S_, 30) is not None: fld.append((cs, 1 - S_[30], len(by_cat.get(cs, []))))
        fld.sort(key=lambda x: -x[1])
        fld_bars = ('<div class="hbars">' + "".join(
            f'<a href="{P}/jobs/{cs}/"><span class="hn">{e(CAT[cs])}</span><span class="hb"><i style="width:{max(2, round(100 * v / fld[0][1]))}%"></i></span><span class="hc">{pc(v)}</span></a>'
            for cs, v, _ in fld) + "</div>") if fld else ""
        surv_rows = [(d, at(S_all, d)) for d in (7, 14, 21, 30, 60, 90, 180) if at(S_all, d) is not None and d <= reach]
        surv_bars = ('<div class="hbars">' + "".join(
            f'<div><span class="hn">After {d} days</span><span class="hb"><i style="width:{max(2, round(100 * v))}%"></i></span><span class="hc">{pc(v)} open</span></div>' for d, v in surv_rows) + "</div>")
        # entry-level postings
        ent = [j for j in active if j["entry"]]
        ent_cat = Counter(j["cat"] for j in ent if j["cat"] != OTHER[0]).most_common(8)
        ent_exp2 = sum(1 for j in ent if (j.get("years") or 0) >= 2)
        ent_rem, ent_pay, ent_int = sum(1 for j in ent if j["remote"]), sum(1 for j in ent if j["salary"]), sum(1 for j in ent if j["level"] == "Intern")
        ent_mid = [(j["usd"][0] + j["usd"][1]) / 2 for j in ent if j["usd"] and j["level"] == "Junior"]
        ent_cos = Counter(j["company"] for j in ent).most_common(8)
        S_ent = curve(SURV["entry"], 30) if SURV.get("entry") else None
        e30 = 1 - S_ent[30] if at(S_ent, 30) is not None else None
        ent_bars = '<div class="hbars">' + "".join(
            f'<a href="{P}/jobs/?entry=1&amp;cat={cs}"><span class="hn">{e(CAT[cs])}</span><span class="hb"><i style="width:{max(2, round(100 * k_ / ent_cat[0][1]))}%"></i></span><span class="hc">{k_:,}</span></a>'
            for cs, k_ in ent_cat) + "</div>" if ent_cat else ""
        ent_co = '<div class="hbars">' + "".join(
            f'<a href="{P}/companies/{slugify(c_)}/"><span class="hn">{e(c_)}</span><span class="hb"><i style="width:{max(2, round(100 * k_ / ent_cos[0][1]))}%"></i></span><span class="hc">{k_:,}</span></a>'
            for c_, k_ in ent_cos) + "</div>" if ent_cos else ""
        city_top = map_n.most_common(10)
        city_bars = '<div class="hbars">' + "".join(
            f'<a href="{P}/{map_url(k)}"><span class="hn">{fl(geo_cities.CITIES[k][1])}{e(geo_cities.CITIES[k][0])}</span><span class="hb"><i style="width:{max(2, round(100 * k_ / city_top[0][1]))}%"></i></span><span class="hc">{k_:,}</span></a>'
            for k, k_ in city_top) + "</div>" if city_top else ""
        # a small picture of the map: the 150 cities with the most jobs, placed by longitude and latitude (cropped to where they are),
        # each dot sized by its open jobs; the city with the most is orange
        dots_ = map_n.most_common(150)
        dot_svg = ""
        if dots_:
            xs_ = [geo_cities.CITIES[k][3] for k, _ in dots_]; ys_ = [-geo_cities.CITIES[k][2] for k, _ in dots_]
            x0_, y0_ = min(xs_) - 8, min(ys_) - 8
            w_, h_ = max(xs_) + 8 - x0_, max(ys_) + 8 - y0_
            dot_svg = (f'<svg class="st-dots" viewBox="{x0_:.0f} {y0_:.0f} {w_:.0f} {h_:.0f}" role="img" aria-label="Dots for the {len(dots_)} cities with the most open jobs, placed by longitude and latitude">'
                       + "".join(f'<circle cx="{geo_cities.CITIES[k][3]:.1f}" cy="{-geo_cities.CITIES[k][2]:.1f}" r="{max(0.9, 7 * (k_ / dots_[0][1]) ** 0.5):.1f}"'
                                 f'{" class=" + chr(34) + "top" + chr(34) if i == 0 else ""}/>' for i, (k, k_) in enumerate(dots_)) + "</svg>")
        tile_ = lambda label, value, sub: f'<div class="st"><span class="st-l">{label}</span><b class="st-v">{value}</b><span class="st-s">{sub}</span></div>'
        est_note = (f"{'Early estimate: ' if early else 'Estimate: '}from {SURV['closed']:,} closings seen in {days_s} days of hourly checks (since {since_s}). "
                    f"It reaches {reach} days for now" + (", and the 90-day figure appears once the record covers 30 days" if reach < 90 else "") + ". It will move as the record grows.")
        quote_s = (f"Of {len(active):,} open job postings checked on {fdate(TODAY)}, {pc(old90 / max(1, len(active)))} had been up for more than 90 days; "
                   f"the postings that closed since {since_s} had been open a median of {med_cl} days.")
        lead_s = (f"About {med_cl} days at the median, on employers’ own careers pages. "
                  f"Of the {len(age_cl):,} postings that employers took down since {since_s}, half had been open {med_cl} days or more. "
                  + (f"At the closing rates seen in {'the first ' if early else ''}{days_s} days of records, about {pc(c7)} of new postings close within 7 days and {pc(c30)} within 30" + (f", {pc(c90)} within 90" if c90 is not None else "") + ". " if c7 is not None and c30 is not None else "")
                  + f"{pc(old90 / max(1, len(active)))} of the {len(active):,} jobs open today were posted more than 90 days ago.")
        st_qa = [
            ("How long do job postings stay open?", lead_s),
            ("How many job postings are entry level?", f"{len(ent):,} of {len(active):,} open postings ({pc(len(ent) / max(1, len(active)))}) are marked junior or intern in the title or by the employer: "
             f"{ent_int:,} internships and {len(ent) - ent_int:,} junior roles. {ent_exp2:,} of them ({pc(ent_exp2 / max(1, len(ent)))}) still ask for two years of experience or more."),
            ("Why are some postings open for months?", f"The page does not say why: a posting stays open as long as the employer keeps it on its careers page. "
             f"Some roles are hard to fill, some are kept up to collect applications all year. {old90:,} of today’s open jobs were posted more than 90 days ago; each of their pages says so."),
            ("How are the figures counted?", f"Every hour the careers pages of the employers we follow are read. A posting that is no longer there is counted as closed on that day. "
             f"When a whole job board empties at once, the employer has usually moved to another hiring system, so those postings" + (f" ({SURV['moved']:,} of them)" if SURV["moved"] else "") + " are left out. "
             "The estimated shares multiply the daily chance of closing seen for postings of each age (up to 7 days, 8 to 30, 31 to 90, older); "
             f"while the record is short they reach only {reach} days ahead.")]
        st_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in st_qa]},
            {"@type": "Dataset", "name": "How long job postings stay open", "description": f"Daily closing rates of job postings by age, measured from hourly checks of employers’ careers pages since {since_s}.",
             "url": f"{FULL}/how-long-job-postings-stay-open/", "dateModified": TODAY, "creator": {"@type": "Organization", "name": SITE, "url": FULL + "/"},
             "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
             "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{FULL}/data/survival.json"}]}]},
            ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page("how-long-job-postings-stay-open/", f"How Long Do Job Postings Stay Open? About {med_cl} Days (Hourly Data) | {SITE}",
             f"How long job postings stay open, from hourly checks of {len({j['company'] for j in active}):,} employers’ careers pages: closings, open jobs by age, entry-level jobs, the map.",
             crumbs(("Hiring reports", "reports/"), ("How long postings stay open", "")) + '<h1>How long job postings stay open</h1>'
             f'<p class="lead">{e(lead_s)}</p>'
             f'<p class="note">Counted from the careers pages of the employers we read every hour; updated {fdate(TODAY)}. Free to quote with a link.</p>'
             '<div class="stats3 st4">'
             + tile_("Median age at closing", f"{med_cl} days", f"measured: {len(age_cl):,} closings")
             + tile_("Open more than 90 days", pc(old90 / max(1, len(active))), f"measured: {old90:,} of {len(active):,} open jobs")
             + (tile_("Closed within 7 days", pc(c7), ("early " if early else "") + "estimate, new postings") if c7 is not None else "")
             + (tile_("Closed within 30 days", pc(c30), ("early " if early else "") + "estimate, new postings") if c30 is not None else "")
             + (tile_("Closed within 90 days", pc(c90), "estimate, new postings") if c90 is not None else "")
             + "</div>"
             f'<p class="note">{e(est_note)}' + (f' Half of all postings close within about {half_d} days at these rates.' if half_d else "") + "</p>"
             + section("How long postings stay open", '<div class="pics two">'
                       f'<figure class="pic"><figcaption><b>Still open after…</b>The {"early " if early else ""}estimated share of new postings still on the employer’s page that many days after posting, up to {reach} days.</figcaption>{surv_bars}</figure>'
                       f'<figure class="pic"><figcaption><b>Age at closing</b>The {len(age_cl):,} postings that closed since {since_s}, by how many days they had been up. The median is {med_cl} days.</figcaption>'
                       + vcols(cl_pts, aria="Closed postings by days since posting") + "</figure></div>")
             + section("How old today’s open jobs are", '<div class="pics two">'
                       f'<figure class="pic"><figcaption><b>Open jobs by age</b>All {len(active):,} open postings, by days since the employer posted them.</figcaption>'
                       + vcols(age_pts, hi=next((i for i, (lo, hi, _) in enumerate(AGE_B) if lo > 90), None), aria="Open jobs by days since posting") + "</figure>"
                       + (f'<figure class="pic"><figcaption><b>Closed within 30 days, by field</b>Estimated share of new postings closed within 30 days, in fields with at least 30 closings.</figcaption>{fld_bars}</figure>' if fld_bars else "")
                       + "</div>", ("insights/long-open-roles/", "Employers with long-open roles"))
             + section("Entry-level jobs", f'<p>{len(ent):,} of the {len(active):,} open postings ({pc(len(ent) / max(1, len(active)))}) are for beginners: {ent_int:,} internships and {len(ent) - ent_int:,} junior roles. '
                       f'{ent_rem:,} can be done from home and {ent_pay:,} state the pay' + (f'; junior roles that state a yearly range in US dollars pay {money(median(ent_mid))} at the median' if len(ent_mid) >= 30 else "") + '. '
                       f'{ent_exp2:,} of them ({pc(ent_exp2 / max(1, len(ent)))}) ask for two years of experience or more.'
                       + (f' At the closing rates seen so far, about {pc(e30)} of new entry-level postings close within 30 days, against {pc(c30)} for all postings.' if e30 is not None and c30 is not None else "") + "</p>"
                       + '<div class="pics two">'
                       + (f'<figure class="pic"><figcaption><b>Where the entry-level jobs are</b>Open junior and intern postings by field.</figcaption>{ent_bars}</figure>' if ent_bars else "")
                       + (f'<figure class="pic"><figcaption><b>Who hires the most beginners</b>Employers with the most open junior and intern postings.</figcaption>{ent_co}</figure>' if ent_co else "")
                       + "</div>", ("entry-level/", "All entry-level jobs"))
             + section("Where the jobs are", f'<p>{map_total:,} of the open jobs name a city; they are spread over {len(map_keys):,} cities. The ten with the most:</p>'
                       f'<div class="pics two"><figure class="pic"><figcaption><b>Cities with the most open jobs</b>Open postings that name the city.</figcaption>{city_bars}</figure>'
                       f'<a class="pic st-map" href="{P}/map/">{dot_svg}<b>See every city on the map</b><span>A dot per city, sized by its open jobs. Type a job or a skill and the dots are counted again.</span><u>Open the jobs map</u></a></div>',
                       ("map/", "Jobs map"))
             + section("How these figures are counted", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in st_qa) + "</dl>"
                       + f'<p class="note">The data behind the estimate: <a href="{P}/data/survival.json">survival.json</a> (daily closing chance by age band, overall and by field). '
                       f'How the jobs are collected: <a href="{P}/methodology/">methodology</a>. Today’s run: <a href="{P}/status/">data status</a>.</p>')
             + cite("how-long-job-postings-stay-open/", "How long job postings stay open", quote_s), head=st_ld)

    # Jobs by hourly pay (Upwork has a page per hourly rate; the searches in keywords.json are "jobs that pay 25 an hour" and "salary for
    # 20 dollars an hour"). A job is listed by the lowest pay its posting states: an hourly rate as written, a yearly salary divided by
    # 2,080 hours (40 a week, 52 weeks). US dollars only, as each employer states it.
    dollars = lambda v: f"${v:,.0f}"                # exact dollars: $4,333 a month, not $4K
    HR_BANDS = [(20, 25), (25, 30), (30, 40), (40, 50), (50, 75), (75, 100), (100, None)]
    hr_of = {}
    for j in active:
        h_ = usd_hourly(j["salary"])
        if h_: hr_of[j["id"]] = (h_[0], "h")
        elif j["usd"]: hr_of[j["id"]] = (j["usd"][0] / 2080, "y")
    def hr_band(lo_, hi_):
        return [j for j in active if j["id"] in hr_of and lo_ <= hr_of[j["id"]][0] < (hi_ or 10 ** 6)]
    hr_jobs = {lo_: hr_band(lo_, hi_) for lo_, hi_ in HR_BANDS}
    hr_label = lambda lo_, hi_: f"${lo_} to ${hi_} an hour" if hi_ else f"${lo_} an hour or more"
    hr_chips = lambda cur: '<p class="rel"><span>Other pay:</span>' + "".join(
        f'<a href="{P}/jobs-that-pay/{lo_}-an-hour/"{" aria-current=" + chr(34) + "page" + chr(34) if lo_ == cur else ""}>{e(hr_label(lo_, hi_))}</a>' for lo_, hi_ in HR_BANDS if len(hr_jobs[lo_]) >= 20) + "</p>"
    hr_total = sum(len(v) for v in hr_jobs.values())
    for lo_, hi_ in HR_BANDS:
        js_ = hr_jobs[lo_]
        if len(js_) < 20: continue
        n_h = sum(1 for j in js_ if hr_of[j["id"]][1] == "h")
        cats_ = Counter(CAT[j["cat"]] for j in js_ if j["cat"] != OTHER[0]).most_common(3)
        yr_lo, yr_hi = lo_ * 2080, (hi_ * 2080 if hi_ else None)
        span_ = f"between {dollars(yr_lo)} and {dollars(yr_hi)} a year" if hi_ else f"{dollars(yr_lo)} a year or more"
        lead_ = (f"${lo_} an hour is {dollars(lo_ * 40)} a week, {dollars(yr_lo / 12)} a month and {dollars(yr_lo)} a year for full-time work (40 hours a week, 52 weeks). "
                 f"{len(js_):,} open jobs start their stated pay at {e(hr_label(lo_, hi_))}, or {span_}: {n_h:,} state an hourly rate, {len(js_) - n_h:,} a yearly salary.")
        qa_ = [(f"How much is ${lo_} an hour a year?", f"At 40 hours a week for 52 weeks, ${lo_} an hour is {dollars(yr_lo)} a year, {dollars(yr_lo / 12)} a month or {dollars(lo_ * 40)} a week. "
                f"For other hours, use the pay converter on this site."),
               (f"Which jobs pay ${lo_} an hour?", f"Of the {len(js_):,} open jobs listed here, the most are in " + ", ".join(f"{c_.lower()} ({k_:,})" for c_, k_ in cats_) + ". "
                f"{n_h:,} of them state an hourly rate; the others state a yearly salary that works out to this hourly pay."),
               ("Why is a job listed under this pay?", f"Each job is placed by the lowest pay its posting states, so every job here pays at least ${lo_} an hour"
                + (f" and starts below ${hi_}" if hi_ else "") + "; many ranges go higher. Only pay stated in US dollars is counted.")]
        # what Google shows for "jobs that pay $25 an hour" (15 Nov 2026): $1,000 a week first, jobs without a degree, remote ones, and
        # People also ask "Is $25 an hour decent pay?", "How can I make $25 an hour?", "What jobs pay $30 an hour without education?"
        hrr_ = role_rows(js_, 3)
        hmed_ = lambda xs: median([hr_of[j["id"]][0] for j in xs])
        nd_ = [j for j in js_ if "No degree required" in j.get("perks", [])]
        rm_ = [j for j in js_ if j["remote"]]
        en_ = [j for j in js_ if j.get("entry")]
        all_h = [v for v, _ in hr_of.values()]
        below_ = sum(1 for v in all_h if v < lo_)
        nd_t = Counter(re.sub(r"\s+", " ", re.sub(r"\s*[\(\[,|–—-].*$", "", j["title"])).strip() for j in nd_).most_common(5)
        hr_blk = ""
        if len(hrr_) >= 3:
            hr_blk += section(f"Which jobs pay {hr_label(lo_, hi_)}", '<div class="tablewrap"><table><tr><th>Kind of work</th><th>Open jobs at this pay</th><th>Typical start</th><th>Remote</th></tr>'
                              + "".join(f'<tr><td><a href="{P}/roles/{s_}/">{e(nm_)}</a></td><td>{c_:,}</td><td>${hmed_(h_):,.2f} an hour</td><td>{sum(1 for j in h_ if j["remote"]):,}</td></tr>' for c_, s_, nm_, _, h_ in hrr_[:10])
                              + '</table></div><p class="note">Kinds of work matched by job title. The typical start is the median of the lowest pay each posting states, per hour. A job can match two kinds of work.</p>')
        if len(nd_) >= 3: hr_blk += section(f"Jobs that pay {hr_label(lo_, hi_)} without a degree", f"<p>{len(nd_):,} of the {len(js_):,} postings say no degree is required. The newest:</p>" + job_links(nd_))
        if len(rm_) >= 3: hr_blk += section(f"Remote jobs that pay {hr_label(lo_, hi_)}", f"<p>{len(rm_):,} of them can be done from home. The newest:</p>" + job_links(rm_) + f'<p class="note">All remote work: <a href="{P}/remote/">remote jobs</a>.</p>')
        if len(en_) >= 3: hr_blk += section(f"Entry-level jobs that pay {hr_label(lo_, hi_)}", f"<p>{len(en_):,} junior roles and internships. The newest:</p>" + job_links(en_))
        qa_[1:1] = [(f"Is ${lo_} an hour good pay?", f"Among the {len(all_h):,} open jobs on {SITE} that state pay in US dollars, {100 * below_ / max(1, len(all_h)):.0f}% start below ${lo_} an hour. "
                     f"Most employers here are technology companies, so that share is not the share across all US jobs. For comparison, the US federal minimum wage is $7.25 an hour; many states and cities set a higher one."),
                    (f"How can I make ${lo_} an hour?", f"{len(js_):,} open jobs pay it today, most in " + ", ".join(f"{c_.lower()} ({k_:,})" for c_, k_ in cats_) + f". {len(en_):,} of them are entry-level, "
                     f"{len(rm_):,} are remote and {len(nd_):,} say no degree is required. Each job links to the employer's own page to apply."),
                    (f"What jobs pay ${lo_} an hour without a degree?", (f"{len(nd_):,} open postings at this pay say no degree is required, for example " + ", ".join(f"{t_} ({k_})" for t_, k_ in nd_t) + "." if nd_ and nd_t else
                     f"None of the {len(js_):,} postings at this pay says outright that no degree is required. Many do not ask for one either, so check the requirements line of each job.")),
                    (f"Are there remote jobs that pay ${lo_} an hour?", f"Yes: {len(rm_):,} of the {len(js_):,} open jobs at this pay are listed as remote." if rm_ else f"None of the {len(js_):,} open jobs at this pay is listed as remote today.")]
        qa_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in qa_]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        conv = ('<div class="stats3 st4">'
                + f'<div class="st"><span class="st-l">An hour</span><b class="st-v">${lo_}</b><span class="st-s">{"up to $" + str(hi_) if hi_ else "or more"}</span></div>'
                + f'<div class="st"><span class="st-l">A week</span><b class="st-v">{dollars(lo_ * 40)}</b><span class="st-s">40 hours</span></div>'
                + f'<div class="st"><span class="st-l">A month</span><b class="st-v">{dollars(yr_lo / 12)}</b><span class="st-s">a twelfth of the year</span></div>'
                + f'<div class="st"><span class="st-l">A year</span><b class="st-v">{dollars(yr_lo)}</b><span class="st-s">2,080 hours</span></div></div>')
        listing(f"jobs-that-pay/{lo_}-an-hour/", f"Jobs that pay {hr_label(lo_, hi_)}", f"Jobs That Pay ${lo_} an Hour ({len(js_):,} open) | {SITE}",
                f"{len(js_):,} open jobs whose stated pay starts at {hr_label(lo_, hi_)} ({span_}), from employers’ own careers pages. What ${lo_} an hour is a week, a month, a year.",
                js_, intro=lead_, trail=(("Jobs by hourly pay", "jobs-that-pay/"),), more=False,
                extra=act_row("#list", f"See the {len(js_):,} jobs", [("tools/salary-converter/", "Pay converter")]) + conv + hr_chips(lo_) + f'<p class="note">Work out any other rate with the <a href="{P}/tools/salary-converter/">pay converter</a>, or see <a href="{P}/salaries/">what each job pays</a>.</p>',
                list_title=f"Open jobs from {hr_label(lo_, hi_)}",
                after=hr_blk + section(f"Questions about ${lo_} an hour", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in qa_) + "</dl>") + qa_ld)
    hr_rows = [(lo_, hi_, len(hr_jobs[lo_])) for lo_, hi_ in HR_BANDS if len(hr_jobs[lo_]) >= 20]
    if hr_rows:
        top_n = max(k_ for _, _, k_ in hr_rows)
        hr_bars = '<div class="hbars">' + "".join(
            f'<a href="{P}/jobs-that-pay/{lo_}-an-hour/"><span class="hn">{e(hr_label(lo_, hi_))}</span><span class="hb"><i style="width:{max(2, round(100 * k_ / top_n))}%"></i></span><span class="hc">{k_:,}</span></a>'
            for lo_, hi_, k_ in hr_rows) + "</div>"
        conv_rows = "".join(f"<tr><td>${h_}</td><td>{dollars(h_ * 40)}</td><td>{dollars(h_ * 2080 / 12)}</td><td>{dollars(h_ * 2080)}</td></tr>" for h_ in (15, 18, 20, 22, 25, 30, 35, 40, 50, 75, 100))
        hub_qa = [("How is an hourly rate turned into a yearly salary?", "Multiply it by 2,080: 40 hours a week for 52 weeks. $25 an hour is $52,000 a year; a yearly salary divided by 2,080 gives the hourly rate."),
                  ("Which jobs are listed under each rate?", f"Every open job that states its pay in US dollars: {hr_total:,} today. A job is placed by the lowest pay its posting states, as an hourly rate or as a yearly salary divided by 2,080.")]
        hub_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in hub_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
        page("jobs-that-pay/", f"Jobs by Hourly Pay: $20, $25, $30 an Hour and More | {SITE}",
             f"Open jobs by the hourly pay they state, from $20 to $100 an hour or more ({hr_total:,} today), with what each rate is a week, a month and a year.",
             crumbs(("Jobs by hourly pay", "")) + "<h1>Jobs by hourly pay</h1>"
             f'<p class="lead">{hr_total:,} open jobs state their pay in US dollars. Here they are by the hourly rate they start at: an hourly rate as the employer wrote it, '
             'or a yearly salary divided by 2,080 hours (40 a week, 52 weeks). Pick a rate to see the jobs.</p>'
             + f'<figure class="pic" style="max-width:760px"><figcaption><b>Open jobs by starting hourly pay</b>Each job counted once, by the lowest pay its posting states.</figcaption>{hr_bars}</figure>'
             + section("Hourly pay in a week, a month and a year", '<div class="tablewrap"><table><thead><tr><th>An hour</th><th>A week (40 h)</th><th>A month</th><th>A year (2,080 h)</th></tr></thead><tbody>'
                       + conv_rows + f'</tbody></table></div><p class="note">Any other rate or number of hours: the <a href="{P}/tools/salary-converter/">pay converter</a>.</p>')
             + section("Questions about hourly pay", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in hub_qa) + "</dl>"), head=hub_ld)

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
        page(f"resignation-letters/{x['slug']}/", f"{tcase(x['name'])}: Free Template, Word & PDF ({rl_year}) | {SITE}",
             f"A {low_} you can copy: {x['when'][0].lower() + x['when'][1:]}",
             crumbs(("Resignation letters", "resignation-letters/"), (x["name"], "")) + f'<h1>{e(x["name"])}: <span class="hl">template and example</span></h1>'
             f'<p class="lead">{e(x["when"])} Copy the letter below, replace the parts in [brackets], and send it to your manager.</p>'
             f'<div class="rl-paper"><pre id="letter">{e(x["letter"])}</pre>'
             '<p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the letter</button> <button class="btn ghost sm" type="button" data-doc="letter" data-name="resignation-letter" style="margin-top:0">Word</button> <button class="btn ghost sm" type="button" data-pdf="letter" data-name="resignation-letter" style="margin-top:0">PDF</button> '
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
    rl_qa = list(resignation_pages.HUB_QA) + [x for x in rl_qa if x[0] not in {q_ for q_, _ in resignation_pages.HUB_QA}]
    RS = resignation_pages.STANDARD
    rl_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in rl_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    page("resignation-letters/", f"Resignation Letter Template: {len(RL) + 1} Free Letters, Word & PDF ({rl_year}) | {SITE}",
         f"{len(RL)} resignation letter templates you can copy: two weeks notice, effective immediately, by email, for a new job, relocation, health or family reasons, retirement and more.",
         crumbs(("Resignation letters", "")) + f'<h1>Resignation letter templates: <span class="hl">{len(RL)} examples</span></h1>'
         '<p class="lead">Pick the letter that fits your case. Each one is complete: copy it, replace the parts in [brackets], and send it. '
         f'Or build your own in the <a href="{P}/tools/resignation-letter/">free resignation letter builder</a>.</p>'
         + section(f"{RS['name']}", f'<div class="rl-paper"><pre id="letter">{e(RS["letter"])}</pre>'
                   '<p class="rl-act"><button class="btn primary sm" type="button" data-clip="letter" data-raw="1" style="margin-top:0">Copy the letter</button> <button class="btn ghost sm" type="button" data-doc="letter" data-name="resignation-letter-two-weeks-notice" style="margin-top:0">Word</button> <button class="btn ghost sm" type="button" data-pdf="letter" data-name="resignation-letter-two-weeks-notice" style="margin-top:0">PDF</button> '
                   f'<a class="btn ghost sm" href="{P}/tools/resignation-letter/" style="margin-top:0">Fill it in with the free builder</a></p></div>')
         + section("Choose your situation", f'<ul class="tiles">{"".join(rl_tile(y) for y in RL)}</ul>')
         + section("Tips before you send it", '<ul class="ticks">' + "".join(f"<li>{e(t_)}</li>" for t_ in resignation_pages.HUB_TIPS) + "</ul>"
                   '<p class="note">Notice periods depend on your contract and on the law where you work: two weeks is the custom in the United States, while the UK and most of Europe set minimums by law. This page is general guidance, not legal advice.</p>')
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
             + (section(f"Which word to use instead of “{x['word']}”", '<div class="tablewrap"><table><tr><th>If you…</th><th>Use</th></tr>'
                        + "".join(f"<tr><td>{e(a_)}</td><td><strong>{e(b_)}</strong></td></tr>" for a_, b_ in x.get("pick", ())) + "</table></div>") if x.get("pick") else "")
             + (section("Before and after", '<div class="tablewrap"><table><tr><th>Weak</th><th>Strong</th></tr>'
                        + "".join(f"<tr><td>{e(a_)}</td><td>{e(b_)}</td></tr>" for a_, b_ in x.get("before_after", ())) + "</table></div>") if x.get("before_after") else "")
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
    page("mentors/", f"Career Mentors for Job Seekers: how it will work | {SITE}",
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
        # what each paid product includes and what others charge for the same (figures from the comparison on /post-a-job/, with their sources there)
        ACC_PLANS = {
            "Standard boost": (["30 days above the free jobs in its category, role, place and search lists", "A “Featured” mark on the job", "Views and clicks on Apply, day by day",
                                "A free 30-day rerun if it gets fewer than 10 clicks on Apply in its first 14 days"], "Indeed: about $150–$750 for 30 days of sponsoring"),
            "Premium boost": (["Everything in the Standard boost", "A turn in the top 3 of its lists", "“Urgently hiring” for 14 days", "Your logo and a cover picture on the job",
                               "An invitation to up to 50 matching job seekers who asked for them"], "We Work Remotely’s top post: $458; Indeed Premium: no public price"),
            "Urgently hiring badge": (["“Urgently hiring” on the job for 14 days, in every list and on its page"], ""),
            "Bump to top": (["The job back at the top of its lists, as if posted today"], ""),
            "Extend a boost by 30 days": (["30 more days for a boost that is running"], ""),
            "Company spotlight": (["Your company in “Featured employers” on the home page", "At the top of the companies list", "A badge on your company page"], ""),
            "Hiring Pass": (["Unlimited Standard boosts for every job of your company", "3 Premium boosts", "The company spotlight", "30 days, one payment"],
                            "Indeed: a typical $500–$2,000 a month for 1–10 roles; Jobright: $499 a month for one role"),
            "Category or skill sponsor": (["Your company named at the top of one category or skill page", "For 30 days, seen by everyone browsing that work"], ""),
            "100 credits": (["$100 to spend on anything here", "Valid for 12 months"], ""), "250 credits": (["$250 to spend on anything here", "Valid for 12 months"], ""),
            "550 credits": (["$550 to spend for $500: 10% more", "Valid for 12 months"], ""), "1,200 credits": (["$1,200 to spend for $1,000: 20% more", "Valid for 12 months"], ""),
        }
        acc_data = {"site": FULL, "plans": ACC_PLANS, "skills": wb_data["skills"], "categories": wb_data["categories"], "companies": [c for c, _ in comp_items if OPEN[c]],
                    "what": {p["name"]: p["what"] for p in CFG["prices"]}}
        page("account/", f"Your Account: Alerts, Saved Jobs, Posting | {SITE}",
             "Your free account: job alerts, saved jobs on every device and your resume for employers; for employers, free job posting, company pages, team and receipts.",
             crumbs(("Account", "")) + "<h1>Your account</h1>"
             '<p class="lead">Free for job seekers and employers. Keep your alerts and saved jobs in one place, let employers find your resume if you want to, '
             'or post jobs from your work address. Sign in with your email or with Google.</p>'
             f'<div id="acc" data-api="{e(CFG["api_url"])}"><noscript><div class="banner">The account needs JavaScript.</div></noscript></div>'
             '<script type="application/json" id="acc-data">' + json.dumps(acc_data, ensure_ascii=False).replace("</", "<\\/") + f'</script><script src="{P}/account.js?v={V}" defer></script>',
             head='<meta name="robots" content="noindex">', sitemap=False)
    # The brand (owner, 15 Nov 2026: "a corporate design of our own, like Indeed and other brands"). brand.py defines three
    # directions and draws every logo file; /brand/ is the guide, /brand/directions/ shows all three (not indexed), and the
    # media kit has the files, the colours, the descriptions and today's numbers for press and partners.
    BD = brand.DIRECTIONS
    n_hourly = len({s_["name"] for f_ in ("sources.json", "sources_tech.json") if (ROOT / f_).exists() for s_ in json.loads((ROOT / f_).read_text())})
    n_rot = len(json.loads((ROOT / "sources_more.json").read_text())) if (ROOT / "sources_more.json").exists() else 0
    read_line = (f"{n_hourly:,} employers’ careers pages are read every hour and {n_rot:,} more every four hours" if n_rot else f"{n_hourly:,} employers’ careers pages are read every hour")
    bp50 = (f"{SITE} (jobseveryhour.com) is a free job search site built from employers’ own careers pages. It lists {n:,} open jobs at {m:,} companies today. "
            "A job the employer takes down leaves the list, every listing links to the original posting, and nobody needs an account to search or apply.")
    bp100 = (bp50 + f" {read_line}. Each job page shows the pay when the employer states it, how long the job has been open and when it was last checked. "
             "The salary and hiring figures are counted from the open postings, free to quote.")
    wc = lambda t: len(t.split())
    top_city, top_city_n = ((geo_cities.CITIES[map_n.most_common(1)[0][0]][0], map_n.most_common(1)[0][1]) if map_n else ("London", 0))      # for the example sentence
    def logo_tile(file_, label, dark=False, h=40):
        size_ = f'width="{h}" height="{h}"' if "-mark" in file_ else f'height="{h}"'           # a mark is square; a logo keeps its own width
        return (f'<a class="brandtile{" dark" if dark else ""}" href="{P}/brand/{file_}" download><img src="{P}/brand/{file_}" alt="{e(label)}" {size_} loading="lazy">'
                f'<span>{e(label)} · SVG</span></a>')
    A_ = brand.APPLIED
    swatch = lambda hexv, name, use, ink="#121110": (f'<div class="swatch"><i style="background:{hexv}"></i><b>{name}</b><span>{hexv.upper()}</span><small>{use}</small></div>')
    SWATCHES = (swatch(BD[A_]["mark"], BD[A_]["name"], "The mark, the marker under words and lines under links")
                + swatch(BD[A_]["ui"], BD[A_]["name"] + " deep", "Links and the hover of buttons on white: white text on it passes 4.5:1")
                + swatch(BD[A_]["ui_dark"], BD[A_]["name"] + " light", "The same on dark pages, with dark text on it")
                + swatch(BD[A_]["ink"], "Ink", "Text, the dark button, dark pages")
                + swatch("#FFFFFF", "Paper", "The page")
                + swatch(BD[A_]["paper2"], "Sand", "Quiet panels and table heads")
                + swatch(BD[A_]["tint"], "Tint", "A marker under one phrase, a selected row")
                + swatch(BD[A_]["mark"], "Data green", "Amounts in charts")
                + swatch(BD[A_]["ink"], "Data ink", "The one mark a chart is about"))
    TYPES = ('<div class="types"><div><span class="t1">Jobs that are still open</span><small>Headlines: Schibsted Grotesk, 700–800. The name in the logo: Outfit Bold, lower case, drawn as outlines</small></div>'
             '<div><span class="t2">Every job here comes from the employer’s own careers page. A job the employer takes down leaves the list.</span><small>Text: Public Sans, 400–700</small></div>'
             f'<div><span class="t3">{n:,} open jobs · {money(med_all)} median · 17 past the hour</span><small>Numbers: Public Sans with figures of equal width, so columns line up</small></div>'
             '<div><span class="t4">GET /api/v1/latest.json</span><small>Code only: JetBrains Mono</small></div></div>'
             '<p class="note">All four typefaces are open source (SIL Open Font License) and served from this site.</p>')
    brand_qa = [("What does the logo mean?", "The name is the logo: “jobs every hour” in lower case, and the o of “jobs” is a clock face, because every "
                 "job here is read again from the employer’s own careers page every hour. On its own, the clock-o is the mark: the tab icon and the app icon."),
                ("Why green?", "Green reads as “open”: the job is still open. It is the colour the site has used from the start, for the marker under words "
                 "and the line under links, and it stays small: buttons are ink, and green is never a large fill."),
                ("Can I use the logo?", "Yes, to link to the site or to write about it. Use the files on this page as they are: do not recolour, stretch, outline or "
                 "animate them, and do not put the mark on a photo without a plain plate behind it.")]
    page("brand/", f"Brand Guide — logo, colours, type and voice | {SITE}",
         f"The {SITE} brand in one page: the mark and its meaning, logo files, colours with hex codes, typefaces, charts, pictures and the way we write.",
         crumbs(("Brand", "")) + f'<h1>{e(SITE)} brand guide</h1>'
         '<p class="lead">How the site looks and sounds, in one page: the mark and what it means, the files, the colours, the type, charts, pictures and words. '
         f'Logos and today’s numbers for an article are in the <a href="{P}/media-kit/">media kit</a>.</p>'
         + f'<div class="bmark"><div class="bm-l"><img src="{P}/brand/{A_}-logo.svg" alt="{e(SITE)} logo" height="56"></div><div class="bm-d"><img src="{P}/brand/{A_}-logo-dark.svg" alt="{e(SITE)} logo on a dark background" height="56"></div></div>'
         + section("The mark", f'<div class="bgrid"><div><img class="bbig" src="{P}/brand/{A_}-mark.svg" alt="The mark" width="120" height="120"></div>'
                   '<div><p>The name is the logo: <b>“jobs every hour”</b> in lower case, and the <b>o of “jobs” is a clock face</b>. It says the one thing the site '
                   'promises, that a job here was checked within the hour. On its own the clock-o is the mark: the browser tab, the app icon and the avatar; it still reads as a clock at 16 pixels.</p>'
                   '<ul class="rules"><li>Leave clear space around the mark of at least half its height.</li><li>The smallest mark is 16 px; the smallest logo with the name, 120 px wide.</li>'
                   f'<li>On white use the {BD[A_]["name"].lower()} mark; on dark pages the light one; in one colour, ink or white.</li>'
                   '<li>Do not recolour, stretch, rotate, outline or animate it, do not set the name in another typeface, and keep it in lower case.</li></ul></div></div>')
         + section("Logo files", '<div class="brandrow">' + logo_tile(f"{A_}-logo.svg", "Logo, light") + logo_tile(f"{A_}-logo-dark.svg", "Logo, dark", True)
                   + logo_tile(f"{A_}-logo-mono.svg", "Logo, one colour") + logo_tile(f"{A_}-logo-mono-white.svg", "Logo, white", True)
                   + logo_tile(f"{A_}-mark.svg", "Mark", h=56) + logo_tile(f"{A_}-mark-dark.svg", "Mark, dark", True, h=56) + "</div>"
                   '<p class="note">The letters are outlines, so the files look the same on a computer without the typeface.</p>')
         + section("Colour", f'<div class="swatches">{SWATCHES}</div>'
                   '<p>One brand colour, used sparingly: the mark, the main button, link underlines and the one thing on a page that matters most. '
                   'Large areas are white or ink, never a big green fill, and never green blocks on black. Buttons are ink on light pages and paper on dark ones.</p>')
         + section("Type", TYPES)
         + section("Charts", '<p>Light cards with a thin border. Brand green for amounts and ink for the single mark the chart is about, checked for colour '
                   'blindness in light and dark. Labels only where they help, a tooltip on every mark, and one caption that says what is counted and from where. '
                   'Every figure is counted from the open postings on the day the page is built; no decorative charts.</p>'
                   f'<p class="note">Examples: <a href="{P}/how-long-job-postings-stay-open/">how long postings stay open</a>, <a href="{P}/jobs-that-pay/">jobs by hourly pay</a>, <a href="{P}/insights/">rankings</a>.</p>')
         + section("Pictures", '<ul class="rules"><li><b>The product, not stock photos.</b> Show the site itself: a list of jobs, a chart, the resume builder.</li>'
                   '<li><b>No invented people.</b> No stock models, no AI-made faces or offices, no 3D shapes or glowing gradients.</li>'
                   '<li><b>Company logos only from the company’s own site</b>, and none at all when there is no official one.</li>'
                   f'<li><b>Icons:</b> simple line drawings in ink, with one {BD[A_]["name"].lower()} detail at most.</li></ul>')
         + section("How we write", '<ul class="rules"><li>Plain words. Say the problem, then the fact, then what the page does.</li>'
                   '<li>Every number comes from our own data, with its date and what it counts.</li>'
                   '<li>“Free” is said plainly wherever something is free.</li>'
                   '<li>No hype: no “amazing opportunities”, “revolutionary”, “AI-powered” for its own sake, countdowns or invented reviews.</li></ul>'
                   f'<div class="dodont"><div class="do"><b>Write</b><p>“{top_city_n:,} open jobs in {e(top_city)}, read from the employers’ own pages.”</p></div>'
                   '<div class="dont"><b>Not</b><p>“Thousands of amazing opportunities await you!”</p></div>'
                   '<div class="do"><b>Do</b><p>Orange on the one button or number that matters.</p></div>'
                   '<div class="dont"><b>Not</b><p>Orange behind whole sections, or several colours competing.</p></div></div>')
         + section("Other directions", f'<p>Two more directions were drawn before this one was chosen: Berry and Brick and sand. They are kept, with their files, on '
                   f'<a href="{P}/brand/directions/">the directions page</a>, so the brand can be switched in one place (brand.py).</p>')
         + section("Questions about the brand", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in brand_qa) + "</dl>"),
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
             {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in brand_qa]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    # The three directions side by side, each in light and dark, so the owner can compare and switch later
    def bd_panel(k, dark):
        d = BD[k]
        fam_h, fam_t = brand.FONTS[d["head"]][0], brand.FONTS[d["text"]][0]
        v = (f'--b-bg:{d["dark_bg"] if dark else d["paper"]};--b-card:{d["dark_card"] if dark else "#FFFFFF"};--b-ink:{"#F4F1EC" if dark else d["ink"]};'
             f'--b-muted:{"#ACA69C" if dark else "#5C5852"};--b-line:{"#2C2925" if dark else "#E7E3DC"};--b-ui:{d["ui_dark"] if dark else d["ui"]};'
             f'--b-ui-ink:{d["dark_bg"] if dark else "#FFFFFF"};--b-mark:{d["ui_dark"] if dark else d["mark"]};--b-tint:{d["tint_dark"] if dark else d["tint"]};'
             f"--b-head:'{fam_h}';--b-text:'{fam_t}'")
        bars = [(62, False), (100, True), (78, False), (41, False)]
        top_ = (f'<img src="{P}/brand/{k}-logo{"-dark" if dark else ""}.svg?v={LOGO_V}" alt="{e(SITE)}" height="22" style="height:22px;width:auto">' if d.get("shape") == "clocko" else
                f'<svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">{brand.mark(k, d["ui_dark"] if dark else d["mark"], d["dark_bg"] if dark else "#FFFFFF")}</svg><b>{e(SITE)}</b>')
        return (f'<div class="bd-panel" style="{v}"><div class="bd-top">{top_}<span>Jobs</span><span>Companies</span><span>Salaries</span></div>'
                '<p class="bd-h">Jobs that are <span>still open</span></p><p class="bd-p">Every job here comes from the employer’s own careers page. A job the employer takes down leaves the list.</p>'
                '<p class="bd-b"><span class="bd-btn">Search jobs</span><span class="bd-btn2">Build a resume — free</span><span class="bd-a">See salaries</span></p>'
                '<div class="bd-job"><b>Senior Data Engineer</b><span>Remote · United States</span><em>$150K – $190K</em></div>'
                '<div class="bd-chart">' + "".join(f'<i class="{"hi" if hi else ""}" style="height:{h}%"></i>' for h, hi in bars) + "</div></div>")
    dir_secs = ""
    for k, d in BD.items():
        dir_secs += (f'<section class="sec bd-dir" id="{k}"><div class="sec-head"><h2>{e(d["name"])}{" · in use" if d["applied"] else ""}</h2></div>'
                     f'<p class="bd-idea">{e(d["idea"])}</p><p class="note">Headlines: {e(brand.FONTS[d["head"]][0])}. Text: {e(brand.FONTS[d["text"]][0])}. '
                     f'Colours: {d["mark"]} (mark), {d["ui"]} (buttons), {d["ui_dark"]} (on dark), ink {d["ink"]}.</p>'
                     f'<div class="bd-pair">{bd_panel(k, False)}{bd_panel(k, True)}</div>'
                     f'<p class="bd-files"><a href="{P}/brand/{k}-logo.svg">Logo</a> <a href="{P}/brand/{k}-logo-dark.svg">Logo, dark</a> <a href="{P}/brand/{k}-mark.svg">Mark</a> '
                     f'<a href="{P}/brand/{k}-logo-mono.svg">One colour</a></p></section>')
    page("brand/directions/", f"Brand Directions: three looks for the site | {SITE}",
         f"{len(BD)} brand directions for {SITE}, each with its mark, colours and type in light and dark: " + ", ".join(d["name"] + (" (in use)" if d["applied"] else "") for d in BD.values()) + ".",
         crumbs(("Brand", "brand/"), ("Directions", "")) + f"<h1>{len(BD)} brand directions</h1>"
         f'<p class="lead">The site uses <b>{BD[A_]["name"]}</b>. The others stay here, drawn and ready, so the look can be changed later in one place '
         f'(<code>brand.py</code>). <a href="{P}/brand/">The brand guide</a> explains the one in use.</p>'
         '<style>@font-face{font-family:"Hanken Grotesk";font-weight:100 900;font-display:swap;src:url(' + P + '/fonts/hanken-latin.woff2) format("woff2")}</style>'
         + dir_secs, head='<meta name="robots" content="noindex">', sitemap=False)
    # Media kit: for journalists, partners and advertisers
    shots = [("screen-home.jpg", "The home page"), ("screen-search.jpg", "Search"), ("screen-resume.jpg", "The resume builder")]
    shots = [(f_, l_) for f_, l_ in shots if (ROOT / "assets" / "brand" / f_).exists()]
    banners = [("banner-x.png", "X / Twitter header, 1500 × 500"), ("banner-linkedin.png", "LinkedIn cover, 1584 × 396"), ("banner-square.png", "Square post, 1080 × 1080")]
    banners = [(f_, l_) for f_, l_ in banners if (ROOT / "assets" / "brand" / f_).exists()]
    sig = (f'<table cellpadding="0" cellspacing="0" style="font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#121110"><tr>'
           f'<td style="padding-right:12px;vertical-align:top"><img src="{FULL}/brand/{A_}-mark-96.png" width="40" height="40" alt="{SITE}"></td>'
           f'<td style="vertical-align:top"><b style="font-size:14px">Your Name</b><br>Your role, {SITE}<br>'
           f'<a href="{FULL}/" style="color:#15803D;text-decoration:none">jobseveryhour.com</a></td></tr></table>')
    page("media-kit/", f"Media Kit — logos, numbers and descriptions | {SITE}",
         f"{SITE} media kit: logo files, colours with hex codes, a 50 and a 100-word description, today’s numbers, screenshots, social banners and the press contact.",
         crumbs(("Media kit", "")) + f"<h1>{e(SITE)} media kit</h1>"
         '<p class="lead">Everything needed to write about the site or link to it: the description, today’s numbers, the logo, screenshots and the press contact. '
         f'Free to use. The rules for the logo and colours are in the <a href="{P}/brand/">brand guide</a>.</p>'
         f'<div class="stats3 st4"><div class="st"><span class="st-l">Open jobs</span><b class="st-v">{n:,}</b><span class="st-s">on {fdate(TODAY)}</span></div>'
         f'<div class="st"><span class="st-l">Companies</span><b class="st-v">{m:,}</b><span class="st-s">with open jobs today</span></div>'
         f'<div class="st"><span class="st-l">Remote jobs</span><b class="st-v">{len(remote):,}</b><span class="st-s">can be done from home</span></div>'
         f'<div class="st"><span class="st-l">New this week</span><b class="st-v">{WEEKNEW:,}</b><span class="st-s">posted in the last 7 days</span></div></div>'
         '<p class="note">Counted from the open postings when this page was built. Visitor numbers are not published yet: they will be, once they have been measured for a full month.</p>'
         + section("About the site", f'<p class="flabel">In {wc(bp50)} words</p><blockquote class="bp" id="bp50">{e(bp50)}</blockquote>'
                   f'<p><button class="btn ghost sm" type="button" data-clip="bp50" style="margin-top:0">Copy</button></p>'
                   f'<p class="flabel">In {wc(bp100)} words</p><blockquote class="bp" id="bp100">{e(bp100)}</blockquote>'
                   f'<p><button class="btn ghost sm" type="button" data-clip="bp100" style="margin-top:0">Copy</button></p>'
                   f'<p class="note">The numbers in both are today’s and change every day. How the data is collected: <a href="{P}/methodology/">methodology</a>.</p>')
         + section("Logo", '<div class="brandrow">' + logo_tile(f"{A_}-logo.svg", "Logo, light") + logo_tile(f"{A_}-logo-dark.svg", "Logo, dark", True)
                   + logo_tile(f"{A_}-logo-mono.svg", "Logo, one colour") + logo_tile(f"{A_}-mark.svg", "Mark", h=56) + "</div>"
                   f'<p class="note">More versions and the rules: <a href="{P}/brand/">brand guide</a>.</p>', ("brand/", "Brand guide"))
         + section("Colours", f'<div class="swatches">{SWATCHES}</div>')
         + (section("Screenshots", '<div class="shots">' + "".join(f'<a href="{P}/brand/{f_}" download><img src="{P}/brand/{f_}" alt="{e(l_)}" loading="lazy" width="640" height="400"><span>{e(l_)}</span></a>' for f_, l_ in shots)
                    + "</div>" f'<p class="note">Taken on {fdate(TODAY)} at 1280 × 800. The site changes every hour; open it for a current picture.</p>') if shots else "")
         + section("Social banners and the share picture", '<div class="shots">' + "".join(f'<a href="{P}/brand/{f_}" download><img src="{P}/brand/{f_}" alt="{e(l_)}" loading="lazy"><span>{e(l_)}</span></a>' for f_, l_ in banners)
                   + f'<a href="{P}/og.jpg" download><img src="{P}/og.jpg" alt="Share picture" loading="lazy" width="600" height="315"><span>Share picture, 1200 × 630</span></a></div>'
                   '<p class="note">The share picture is what social networks show when a page of the site is shared: white paper, the logo, one headline with a tinted marker, '
                   'and a dark panel of real job titles. No figures that change daily: networks keep the picture for a long time.</p>')
         + section("Email signature", f'<div class="sigprev">{sig}</div><textarea rows="5" readonly aria-label="Email signature HTML">{e(sig)}</textarea>'
                   '<p class="note">Paste the HTML into the signature settings of your mail app and put in your name and role.</p>')
         + section("Placements for employers and sponsors", f'<div class="tablewrap"><table><tr><th>Placement</th><th>Price</th><th>What it is</th></tr>{rows}</table></div>'
                   + ("<p>Every placement is bought and switched on in the employer account, paid in crypto at checkout." if CFG["api_url"] else
                      "<p>Placements will be bought and switched on in a self-serve employer account, paid in crypto at checkout. The account is not open yet, so nothing can be bought today.")
                   + f' Posting a job is free: <a href="{P}/post-a-job/">for employers</a>.</p>')
         + section("Press contact", f'<p>Email {mail_a("press")}. Numbers you can quote, each with its method and date: <a href="{P}/how-long-job-postings-stay-open/">how long postings stay open</a>, '
                   f'<a href="{P}/trends/">hiring trends</a>, <a href="{P}/salaries/">salaries from open postings</a>, <a href="{P}/reports/">monthly reports</a>. '
                   f'Raw data: the <a href="{P}/api/">free JSON API</a>.</p>'),
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": FULL + "/",
               "logo": f"{FULL}/brand/icon-512.png", "description": bp50}) + "</script>")
    # Hiring badges: small live pictures with a count of open roles, for a README, a footer or a post
    top_co = next((c for c, _ in comp_items if OPEN[c]), "")
    top_sk = skill_counts.most_common(1)[0][0] if skill_counts else ""
    badges = [("Jobs", "badge/jobs.svg", "jobs/"), ("Remote jobs", "badge/remote.svg", "remote/")]
    if top_sk: badges.append((f"{top_sk} jobs", f"badge/skills/{tslug(top_sk)}.svg", f"skills/{tslug(top_sk)}/"))
    if top_co: badges.append((f"{top_co} is hiring", f"badge/companies/{slugify(top_co)}.svg", f"companies/{slugify(top_co)}/"))
    badge_rows = "".join(
        f'<div class="feat"><p><img src="{P}/{img}" alt="{e(lbl)} badge" height="28" loading="lazy"></p>'
        f'<span class="flabel">HTML</span><textarea rows="2" readonly aria-label="HTML for the {e(lbl)} badge">{e(f"""<a href="{FULL}/{pg}"><img src="{FULL}/{img}" alt="{lbl} on {SITE}" height="28"></a>""")}</textarea>'
        f'<span class="flabel">Markdown</span><textarea rows="2" readonly aria-label="Markdown for the {e(lbl)} badge">{e(f"[![{lbl} on {SITE}]({FULL}/{img})]({FULL}/{pg})")}</textarea></div>' for lbl, img, pg in badges)
    hb_faq = [("What is a hiring badge?", "A small picture that says a company or a field is hiring, usually with a number. These badges are live: the number of open roles on each one is recounted every day."),
              ("Where can I use a hiring badge?", "In a GitHub README, a site footer, a blog post, an email signature or a community page: anywhere an image with a link works."),
              ("Is there a badge for my company?", f"If your company is among the {m:,} whose career pages we read, yes: its badge shows its current number of open roles. Pick it in the widget builder."),
              ("Is it free?", "Yes. Copy the code and use it; the badge links back to the list it counts.")]
    page("hiring-badge/", f"Free Hiring Badge with a Live Count of Open Roles | {SITE}",
         "Free hiring badges for a README, a footer or a post: a small live image with today’s number of open roles for jobs, a skill, a city or your company. Copy and paste.",
         crumbs(("Job widget", "widgets/"), ("Hiring badge", "")) + '<h1>Free hiring badge with a live count</h1>'
         '<p class="lead">A “we’re hiring” picture says nothing new after the first week. These badges carry today’s number of open roles and update themselves. '
         f'Copy one below, or <a href="{P}/widgets/">pick any skill, city, category or company in the builder</a>.</p>'
         f'<div class="feats">{badge_rows}</div>'
         + section("Questions about the hiring badge", '<dl class="qa">' + "".join(f"<div><dt>{e(q_)}</dt><dd>{e(a_)}</dd></div>" for q_, a_ in hb_faq) + "</dl>"),
         head='<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
             {"@type": "Question", "name": q_, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q_, a_ in hb_faq]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    org_ld = ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": FULL + "/",
              "logo": FULL + "/brand/icon-512.png", "description": "An hourly-updated index of open jobs collected from companies' official careers pages."}) + "</script>")
    page("about/", f"About {SITE} — who we are and how the site works", f"What {SITE} is, where its {n:,} job listings come from, how often they are checked and what the site does not do.",
         crumbs(("About", "")) + f"<h1>About {e(SITE)}</h1>"
         f'<p class="lead">{e(SITE)} is an index of open jobs. Every hour it reads the public hiring feeds of {N_FEEDS} companies, puts their {n:,} open roles into one searchable list and links each one back to the employer.</p>'
         f'<dl class="facts"><div><dt>Companies read</dt><dd>{N_FEEDS}</dd></div><div><dt>Open jobs today</dt><dd>{n:,}</dd></div>'
         f'<div><dt>Checked</dt><dd>Every hour</dd></div><div><dt>Cost to job seekers</dt><dd>$0</dd></div></dl><div class="about-grid"><div>'
         f'<h2 class="h2s">Where {e(SITE)} gets its jobs</h2><p>From the companies\' own careers systems, not from other job boards. Every listing links to the original posting, and you apply there. '
         f'The full process is on the <a href="{P}/methodology/">methodology page</a>.</p></div><div>'
         f'<h2 class="h2s">How often {e(SITE)} is updated</h2><p>Every hour. The date of the last check is shown on every job page. Closed jobs are not deleted: they move to the <a href="{P}/archive/">archive</a> and are marked as closed.</p></div><div>'
         f'<h2 class="h2s">What {e(SITE)} costs job seekers</h2><p>Nothing. Searching, saving jobs, tracking applications, the resume builder and applying are free and need no account. A paid <a href="{P}/plus/">Plus</a> plan with extra tools is planned.</p></div><div>'
         f'<h2 class="h2s">Who runs {e(SITE)}</h2><p>An independent small team. We are not a recruitment agency and take no part in hiring decisions. Company names and logos belong to their owners and are shown only to identify the employer.</p></div><div>'
         f'<h2 class="h2s">How to contact {e(SITE)}</h2><p>' + (f"Write to us: {contact}." if contact else "Contact details will be published on this page shortly.")
         + f' For corrections or removal of a listing, see the <a href="{P}/terms/">terms</a>.</p></div></div>'
         + ('<div class="tablewrap"><table><tr><th>About</th><th>Address</th></tr>'
            + "".join(f"<tr><td>{what}</td><td>{mail_a(k)}</td></tr>" for k, what in [
                ("jobs", "Posting, correcting or removing a job"), ("partners", "Widgets, the API, job channels and communities"),
                ("press", "Press: data, quotes, interviews"), ("privacy", "Your data"), ("abuse", "A scam job or a fake recruiter"),
                ("security", "A security problem on the site")] if MAIL.get(k))
            + "</table></div>" if MAIL else ""), head=org_ld)
    page("methodology/", f"How {SITE} Collects and Checks Jobs — methodology", f"How {SITE} collects job listings, detects salary, skills, perks and remote status, calculates salary medians and handles closed jobs.",
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

> {SITE} is an hourly-updated index of {n:,} open jobs at {m:,} companies, collected from the companies' official careers pages. Every listing links to the employer's own posting. Updated {TODAY}.

## Main sections
- [All jobs]({FULL}/jobs/): search with filters for level, location, salary, perks and remote
- [Remote jobs]({FULL}/remote/)
- [Jobs by skill]({FULL}/skills/)
- [Jobs by location]({FULL}/locations/)
- [Companies hiring]({FULL}/companies/)
- [Jobs by perk]({FULL}/perks/): visa sponsorship, relocation, equity and more
- [Tech jobs]({FULL}/tech/): software, AI, data, cloud, security, product and hardware
- [Crypto and web3 jobs]({FULL}/crypto/)

## Data
- [Salaries from live job postings]({FULL}/salaries/)
- [Hiring trends]({FULL}/trends/)
- [Insights and rankings]({FULL}/insights/)
- [Free JSON API]({FULL}/api/): {FULL}/api/v1/index.json
- [Monthly hiring reports]({FULL}/reports/): one dated page per month that stops changing when the month ends
- [Jobs by hourly pay]({FULL}/jobs-that-pay/): open jobs by the hourly rate they start at, $20 to $100 an hour or more, with each rate a week, a month and a year
- [How long job postings stay open]({FULL}/how-long-job-postings-stay-open/): closings measured every hour, open jobs by age, entry-level jobs, the jobs map
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
- [Free resume builders compared]({FULL}/free-resume-builders/): what the free plan of each well-known resume builder lets you download, read from its own pages, dated
- [Job widget and live badges for other sites]({FULL}/widgets/)

## About
- [What is free and what we will never do]({FULL}/promise/) · [Job offer safety checklist]({FULL}/safety/)
- [About]({FULL}/about/) · [Privacy]({FULL}/privacy/) · [Terms]({FULL}/terms/)
""", sitemap=False)
    page("404.html", f"Page not found | {SITE}", "This page does not exist: the address may have changed or the job may have been renamed. Search open jobs by title, skill or company instead.",
         f'<div class="nf"><p class="nf-code">404</p><h1>Page not found</h1><p class="lead">The address may have changed, or the job may have been renamed. Search for it here:</p>'
         f'<form class="searchbar wide" action="{P}/jobs/" method="get">{ICON_SEARCH}<input type="search" name="q" placeholder="Customer service, nurse, data analyst…" aria-label="Search jobs"><button class="btn primary">Search</button></form>'
         f'<p class="nf-k">Or start from</p><div class="nf-links">' + "".join(f'<a href="{P}/{u}">{t}</a>' for u, t in (("jobs/", "All jobs"), ("new/", "New this week"),
         ("remote/", "Remote jobs"), ("companies/", "Companies"), ("salaries/", "Salaries"), ("resume/", "Resume builder"), ("help/", "Help"))) + "</div></div>", sitemap=False)

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
    api("latest", "Jobs", "jobs/", active); write("badge/jobs.svg", badge_svg("Jobs", f"{n:,} open"), sitemap=False)
    api("remote", "Remote jobs", "remote/", remote); write("badge/remote.svg", badge_svg("Remote jobs", f"{len(remote):,} open"), sitemap=False)
    for t, js in by_tag.items():
        api(f"skills/{tslug(t)}", f"{t} jobs", f"skills/{tslug(t)}/", js); write(f"badge/skills/{tslug(t)}.svg", badge_svg(f"{t} jobs", f"{len(js):,} open"), sitemap=False)
    for cs in CAT:
        if by_cat[cs]:
            api(f"categories/{cs}", f"{CAT[cs]} jobs", f"jobs/{cs}/", by_cat[cs]); write(f"badge/categories/{cs}.svg", badge_svg(f"{CAT[cs]} jobs", f"{len(by_cat[cs]):,} open"), sitemap=False)
    for name, slug, js in places:
        short = name.removeprefix("the ")
        api(f"locations/{slug}", f"Jobs in {short}", f"locations/{slug}/", js); write(f"badge/locations/{slug}.svg", badge_svg(f"Jobs in {short}", f"{len(js):,} open"), sitemap=False)
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
        f"Open jobs collected hourly from employers' official careers pages. Read-only JSON files, no key, CORS enabled. Updated {TODAY}."}, "servers": [{"url": FULL}],
        "paths": {"/api/v1/index.json": {"get": {"operationId": "listFeeds", "summary": "Every feed that exists (skills, categories, locations, companies) with its address and job count",
                                                 "responses": {"200": {"description": "Feed directory", "content": {"application/json": {"schema": {"type": "object"}}}}}}},
                  "/api/v1/latest.json": op("latestJobs", "The newest open jobs"), "/api/v1/remote.json": op("remoteJobs", "The newest remote jobs"),
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
    for f in ("app.js", "embed.js", "site.js", "widget.js", "widgets.js", "resume.js", "account.js", "map.js", "explorer.js"):
        shutil.copy(ROOT / "assets" / f, OUT / f)
    (OUT / "style.css").write_text(mincss((ROOT / "assets" / "style.css").read_text(encoding="utf-8")), encoding="utf-8")
    (OUT / "tools.css").write_text(mincss((ROOT / "assets" / "tools.css").read_text(encoding="utf-8")), encoding="utf-8")
    shutil.copy(ROOT / "assets" / "tools.js", OUT / "tools.js")
    shutil.copytree(ROOT / "assets" / "fonts", OUT / "fonts")
    shutil.copytree(ROOT / "assets" / "brand", OUT / "brand", dirs_exist_ok=True)
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
          f'<rect width="220" height="48" rx="10" fill="#121110"/><g transform="translate(13 11) scale(.82)">{brand.mark_dark()}</g>'
          '<text x="46" y="21" fill="#fff" font-family="Inter,system-ui,-apple-system,Segoe UI,sans-serif" font-size="14" font-weight="700">We’re hiring</text>'
          f'<text x="46" y="37" fill="#b9b7ad" font-family="Inter,system-ui,-apple-system,Segoe UI,sans-serif" font-size="11">Open roles on {e(SITE)}</text></svg>', sitemap=False)
    (OUT / ".nojekyll").write_text("")
    write("manifest.json", json.dumps({"name": SITE, "short_name": SITE, "start_url": P + "/", "scope": P + "/", "display": "standalone", "background_color": "#ffffff", "theme_color": "#121110",
                                       "icons": [{"src": P + "/favicon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]
                                                + [{"src": f"{P}/brand/icon-{n_}.png", "sizes": f"{n_}x{n_}", "type": "image/png", "purpose": "any maskable"}
                                                   for n_ in (192, 512) if (ROOT / "assets" / "brand" / f"icon-{n_}.png").exists()]}), sitemap=False)
    # every narrow page linked up, down and across (crosslinks.py): long-tail pages must not be orphans
    import crosslinks
    n_x, n_l = crosslinks.run(OUT, [u for u in URLS if u and not u.startswith("job/")])
    print(f"cross-links: {n_x:,} pages got links up, down or across ({n_l:,} narrow-to-broad pairs)")
    job_mod = {f"job/{j['slug']}/": (j.get("last_seen") if j["active"] else j.get("closed")) or TODAY for j in jobs}      # a closed job's page last changed the day it closed
    urlset = lambda urls: ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                           + "".join(f"<url><loc>{e(FULL + '/' + u)}</loc><lastmod>{job_mod.get(u, TODAY)}</lastmod></url>" for u in urls) + "</urlset>")
    job_urls = [u for u in URLS if u.startswith("job/")]
    # the pages the site is built to rank with: the home page, one-level hubs (jobs/, salaries/, remote/ ...), every category, every
    # country and part of the world, every role; listed first and in a file of their own, so they are the first thing to read
    countryish = {slug_ for _, slug_, rule_ in PLACES if isinstance(rule_, str)}
    is_core = lambda u: (u == "" or (u.count("/") == 1 and "." not in u) or re.fullmatch(r"(jobs|roles)/[a-z0-9-]+/", u) is not None
                         or (u.startswith("locations/") and u.count("/") == 2 and u.split("/")[1] in countryish))
    core_urls = [u for u in URLS if not u.startswith("job/") and is_core(u)]
    parts = [("sitemaps/core.xml", core_urls), ("sitemaps/pages.xml", [u for u in URLS if not u.startswith("job/") and not is_core(u)])]
    parts += [(f"sitemaps/jobs-{i // 20000 + 1}.xml", job_urls[i:i + 20000]) for i in range(0, len(job_urls), 20000)]
    for name, urls in parts: write(name, urlset(urls), sitemap=False)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<sitemap><loc>{FULL}/{name}</loc><lastmod>{max([job_mod.get(u, TODAY) for u in urls] or [TODAY])}</lastmod></sitemap>" for name, urls in parts if urls)
          + "</sitemapindex>", sitemap=False)
    print(f"sitemaps: {len(core_urls):,} main pages, {sum(len(u) for n, u in parts[1:2]):,} other pages, {len(job_urls):,} job pages")
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Perplexity-User", "Google-Extended",
               "Applebot-Extended", "Amazonbot", "meta-externalagent", "CCBot", "DuckAssistBot", "MistralAI-User", "cohere-ai"]
    if MAIL.get("security"):
        write(".well-known/security.txt", f"Contact: mailto:{MAIL['security']}\nExpires: {(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=180)).strftime('%Y-%m-%dT00:00:00Z')}\n"
              f"Preferred-Languages: en, ru\nCanonical: {FULL}/.well-known/security.txt\n", sitemap=False)
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
