"""H-1B filings per company, from the US Department of Labor's LCA disclosure data (data/h1b.json).

Source: Office of Foreign Labor Certification, "LCA Programs (H-1B, H-1B1, E-3) Disclosure Data", one xlsx per quarter
(https://www.dol.gov/agencies/eta/foreign-labor/performance). Each quarterly file holds the cases decided in that quarter, about
100 columns and 100,000 to 230,000 H-1B rows; a file is 60 to 145 MB zipped and 400 MB of XML inside. Read on 26 Nov 2026: FY2025
Q1-Q4 and FY2026 Q1-Q4 (FY2026 = October 2025 to September 2026; its four files were posted on 12 Nov 2026).

Standard library only (openpyxl is not on this Mac or on the runner): the sheet is streamed in 4 MB pieces, row by row; only the
shared-strings table is held. Never commit the raw files: they live in a scratch folder.

    python3 -I h1b.py extract FILE.xlsx OUT.tsv            the H-1B rows of one quarterly file, the columns in KEEP
    python3 -I h1b.py build WORKDIR MATCHES.json [OUT]     WORKDIR holds FY2025_Q1.tsv ... FY2026_Q4.tsv; writes data/h1b.json

What is counted: VISA_CLASS "H-1B" with CASE_STATUS "Certified". "Certified - Withdrawn" (certified, then withdrawn by the employer)
is counted apart and not in the main figure; "Withdrawn" and "Denied" are left out. A case found in two quarterly files is counted
once, from its latest decision. Wages: WAGE_RATE_OF_PAY_FROM (the lower end when a filing gives a range), turned into a yearly
figure (hour x 2080, week x 52, bi-weekly x 26, month x 12), full-time positions only, kept between $15,000 and $2,000,000.

Matching (26 Nov 2026; a wrong "files H-1B" is worse than none):
- ALIAS below: the companies with the most open jobs, each DOL employer name checked by hand against the company and the state
  of its head office (SpaceX files as Space Exploration Technologies Corp., Gopuff as GoBrands Inc., Walmart as Wal-Mart
  Associates). Namesakes are left out (HP Hood is not HP, Harvey & Company LLC is not Harvey, the AI company: that one files as
  Harvey AI).
- The rest: the DOL name equals ours once case, punctuation and the legal ending (Inc, LLC, Corp, Ltd, "The") are dropped, and the
  places agree (a state or a city in common with the company's open jobs), or the employer's own trade name (TRADE_NAME_DBA)
  equals ours in a city where we list its jobs. Generic one-word names (Mercury, Motive, Software) and franchisees filing under a
  brand were checked by hand or dropped. MATCHES.json records every decision: slug -> {"keys": [normalised DOL names], "how": ...}.
  data/h1b.json keeps the keys, so the next refresh can reuse them: `build WORKDIR data/h1b.json`.
"""
import datetime, json, re, statistics, sys, zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
PAGE = "https://www.dol.gov/agencies/eta/foreign-labor/performance"
READ = "2026-11-26"
FILES = [  # (file, fiscal year, Last-Modified of the file on dol.gov)
    ("LCA_Disclosure_Data_FY2025_Q1.xlsx", 2025, "2025-02-11"), ("LCA_Disclosure_Data_FY2025_Q2.xlsx", 2025, "2025-12-15"),
    ("LCA_Disclosure_Data_FY2025_Q3.xlsx", 2025, "2025-12-15"), ("LCA_Disclosure_Data_FY2025_Q4.xlsx", 2025, "2025-12-18"),
    ("LCA_Disclosure_Data_FY2026_Q1.xlsx", 2026, "2026-11-12"), ("LCA_Disclosure_Data_FY2026_Q2.xlsx", 2026, "2026-11-12"),
    ("LCA_Disclosure_Data_FY2026_Q3.xlsx", 2026, "2026-11-12"), ("LCA_Disclosure_Data_FY2026_Q4.xlsx", 2026, "2026-11-12")]

# Our slug -> the DOL employer names (normalised by norm()) that are this company. Checked by hand, 26 Nov 2026.
ALIAS = {
    "department-of-veterans-affairs": ["department of veterans affairs", "department of veterans affairs george e wahlen va medical center salt lake city ut"],
    "spacex": ["space exploration technologies"],
    "abercrombie-fitch": ["abercrombie and fitch management", "abercrombie and fitch trading"],
    "takeda": ["takeda development center americas", "takeda pharmaceuticals usa", "takeda pharmaceuticals america", "takeda manufacturing usa", "takeda vaccines"],
    "university-of-miami": ["university of miami"],
    "td-bank": ["td bank national association"],
    "amgen": ["amgen"],
    "applied-materials": ["applied materials"],
    "wvu-medicine": ["west virginia university hospitals", "west virginia university medical"],
    "rochester-regional-health": ["rochester general hospital"],
    "university-of-rochester": ["university of rochester"],
    "bhs-baptist-healthcare": ["baptist healthcare system", "baptist healthcare systems"],
    "bank-of-america": ["bank of america"],
    "veterinary-emergency-group-veg": ["veterinary emergency group"],
    "kbr": ["kbr wyle services", "kbr technical services", "kbr"],
    "gdit": ["general dynamics information technology"],
    "carmax": ["carmax enterprise services", "carmax business services"],
    "nvidia": ["nvidia"],
    "booz-allen-hamilton": ["booz allen hamilton"],
    "micron-technology": ["micron technology"],
    "maersk": ["maersk logistics and services usa", "maersk agency usa", "maersk warehousing and distribution services usa"],
    "mondelez-international": ["mondelez global", "mondelez international service"],
    "papa-john-s": ["papa johns international"],
    "umass-memorial-health": ["umass memorial medical group", "umass memorial medical center", "umass memorial health care"],
    "live-nation-entertainment": ["live nation worldwide"],
    "morgan-stanley": ["morgan stanley services group", "morgan stanley", "morgan stanley smith barney", "morgan stanley investment management",
                       "morgan stanley fund services", "morgan stanley bank", "morgan stanley private bank", "morgan stanley capital group",
                       "morgan stanley institutional investment advisors"],
    "hpe": ["hewlett packard enterprise"],
    "dave-buster-s": ["dave and busters management"],
    "ohio-state-university": ["ohio state university"],
    "parsons": ["parsons transportation group", "parsons services", "parsons technical services", "parsons construction group", "parsons government services"],
    "ivy-rehab": ["ivy rehab physical therapy occupational therapy and speech language pathology"],
    "kla": ["kla", "kla coporation"],
    "lehigh-valley-health-network": ["lehigh valley health network"],
    "j-crew": ["j crew group"],
    "hp": ["hp"],
    "pnc": ["pnc financial services group"],
    "beth-israel-lahey-health": ["beth israel lahey health primary care", "beth israel lahey health"],
    "at-t": ["at and t services", "at and t mobility services", "at and t management services"],
    "greystar": ["greystar management services"],
    "amentum": ["amentum technology", "amentum services"],
    "the-university-of-kansas-health-system": ["university of kansas health system"],
    "lithia-driveway": ["lithia motors support services"],
    "cushman-wakefield": ["cushman and wakefield us", "cushman and wakefield global"],
    "jabil": ["jabil", "jabil procurement services", "jabil us holding"],
    "highmark-health": ["highmark health"],
    "johnson-johnson": ["johnson and johnson services", "johnson and johnson vision care", "johnson and johnson health care systems",
                        "johnson and johnson surgical vision", "johnson and johnson international", "johnson and johnson"],
    "vanderbilt-university-medical-center": ["vanderbilt university medical center"],
    "jefferson-health": ["thomas jefferson university hospital"],
    "boyd-group": ["boyd group us"],
    "visa": ["visa technology and operations", "visa usa"],
    "medtronic": ["medtronic", "medtronic minimed", "medtronic minimed group"],
    "cencora": ["cencora patient services", "cencora global consulting services us"],
    "hitachi": ["hitachi digital services", "hitachi energy usa", "hitachi rail sts usa", "hitachi vantara", "hitachi astemo americas",
                "hitachi global air power us", "hitachi rail honolulu jv", "hitachi construction machinery americas", "hitachi america",
                "hitachi high tech america", "hitachi rail gts usa", "hitachi particle engineering and services", "hitachi digital"],
    "rtx": ["rtx", "rtx bbn technologies", "rtx technology research center a division of rtx", "raytheon"],
    "wawa": ["wawa"],
    "jll": ["jones lang lasalle americas"],
    "openai": ["openai opco", "openai"],
    "databricks": ["databricks"],
    "veeva": ["veeva systems"],
    "leidos": ["leidos", "leidos engineering", "leidos biomedical research"],
    "petco": ["petco animal supplies stores"],
    "levi-strauss-co": ["levi strauss"],
    "caterpillar": ["caterpillar", "caterpillar logistics", "caterpillar financial services", "caterpillar global mining", "caterpillar switchgear americas"],
    "motorola-solutions": ["motorola solutions"],
    "danaher": ["danaher"],
    "intel": ["intel", "intel americas", "intel federal"],
    "bright-horizons": ["bright horizons childrens centers"],
    "little-caesars": ["little caesar enterprises"],
    "essentia-health": ["essentia health"],
    "cisco": ["cisco systems", "cisco systems capital"],
    "ups": ["ups worldwide forwarding", "ups", "ups capital", "ups supply chain solutions"],
    "gartner": ["gartner"],
    "boeing": ["boeing"],
    "3m": ["3m", "3m healthcare latam apac export"],
    "stripe": ["stripe", "stripe payments"],
    "ge-healthcare": ["ge healthcare iits usa", "ge precision healthcare", "ge medical systems", "ge medical systems information technologies",
                      "ge medical systems ultrasound and primary care diagnostics"],
    "analog-devices": ["analog devices"],
    "gopuff": ["gobrands"],
    "bmc": ["boston medical center", "boston medical center brighton", "bmc health system", "bmc affiliated physicians"],
    "speechify": ["speechify"],
    "fidelity-investments": ["fmr", "fidelity investments institutional operations"],
    "guidehouse": ["guidehouse digital", "guidehouse", "guidehouse managed services"],
    "m-t-bank": ["m and t bank"],
    "alo": ["alo"],
    "tyson-foods": ["tyson foods"],
    "valeo": ["valeo north america"],
    "vf-corporation": ["vf services", "vf", "vf outdoor"],
    "mufg": ["mufg bank", "mufg securities americas", "mufg fund services"],
    "cadence": ["cadence design systems"],
    "capco": ["capco consulting services"],
    "pfizer": ["pfizer"],
    "puma": ["puma north america"],
    "shield-ai": ["shield ai"],
    "lseg": ["london stock exchange group holdings", "lsegh"],
    "concentrix": ["concentrix cvg customer management group", "concentrix solutions", "concentrix services us", "concentrix cvg", "concentrix cvg cllc"],
    "coupang": ["coupang global"],
    "memorial-healthcare-system": ["south broward hospital district"],
    "topgolf": ["topgolf callaway brands"],
    "memorial-hermann-health-system": ["memorial hermann health system"],
    "bristol-myers-squibb": ["bristol myers squibb"],
    "northern-trust": ["northern trust"],
    "nexstar-media-group": ["nexstar media"],
    "university-of-southern-california": ["university of southern california"],
    "otis": ["otis elevator"],
    "bridgestone-americas": ["bridgestone americas"],
    "allina-health": ["allina health system"],
    "university-of-arkansas-system": ["university of arkansas system division of agriculture"],
    "washington-university-in-st-louis": ["washington university in st louis"],
    "iqvia": ["iqvia", "iqvia rds", "iqvia digital", "iqvia laboratories"],
    "ace-hardware": ["ace hardware"],
    "anthropic": ["anthropic pbc"],
    "the-university-of-texas-at-austin": ["university of texas at austin"],
    "johnson-controls": ["johnson controls", "johnson controls fire protection", "johnson controls security solutions"],
    "general-motors": ["general motors"],
    "globalfoundries": ["globalfoundries us", "globalfoundries us 2"],
    "nordstrom": ["nordstrom"],
    "gordon-food-service": ["gordon food service"],
    "keybank": ["keybank national association"],
    "abbott": ["abbott laboratories", "abbott diabetes care", "abbott diabetes care sales", "abbott cardiovascular systems", "abbott diagnostics scarborough",
               "abbott molecular", "abbott rapid dx north america", "abbott rapid diagnostics informatics", "abbott point of care"],
    "nationwide-children-s-hospital": ["nationwide childrens hospital"],
    "white-cap": ["white cap"],
    "manulife": ["manulife investment management timberland and agriculture", "manulife investment management forest management"],
    "michael-kors": ["michael kors usa"],
    "goodwill-of-central-northern-arizona": ["goodwill of central and northern arizona"],
    "dpr-construction": ["dpr construction a general partnership"],
    "u-s-bank": ["us bank national association"],
    "hub-international": ["hub international midwest"],
    "langan-engineering-environmental-services": ["langan engineering and environmental services"],
    "entegris": ["entegris"],
    "ge-vernova": ["ge vernova operations", "ge vernova international", "ge vernova electrification software holdings"],
    "baxter": ["baxter healthcare"],
    "albany-med-health-system": ["albany med health system"],
    "ge-aerospace": ["general electric"],
    "coxhealth": ["coxhealth", "lester e cox medical centers"],
    "rocket-lab": ["rocket lab usa"],
    "nvent": ["nvent management", "nvent thermal"],
    "thomson-reuters": ["thomson reuters holdings", "thomson reuters services", "thomson reuters", "thomson reuters applications"],
    "merck-msd": ["merck sharp and dohme", "merck research laboratories massachusetts"],
    "methodist-le-bonheur-healthcare": ["methodist le bonheur healthcare"],
    "oshkosh-corporation": ["oshkosh defense", "oshkosh", "oshkosh transport llc fka oshkosh defense"],
    "cloudflare": ["cloudflare"],
    "flex-flextronics": ["flextronics international usa", "flextronics america", "flextronics automotive usa"],
    "gsk": ["glaxosmithkline"],
    "mckesson": ["mckesson"],
    "dxc-technology": ["dxc technology services"],
    "marathon-health": ["marathon health"],
    "airwallex": ["airwallex us"],
    "ivy-tech": ["ivy tech community college"],
    "lucid-motors": ["lucid usa", "lucid group usa"],
    "hospital-sisters-health-system": ["hospital sisters health system"],
    "moog": ["moog"],
    "cigna": ["cigna evernorth services", "cigna health and life insurance", "cigna health and life ins"],
    "lonza": ["lonza houston", "lonza biologics", "lonza manufacturing", "lonza bend", "lonza walkersville", "lonza tampa", "lonza greenwood"],
    "esri": ["environmental systems research institute"],
    "princess-cruises": ["princess cruise lines"],
    "northeastern-university": ["northeastern university"],
    "adventist-healthcare": ["adventist healthcare"],
    "select-medical": ["select medical"],
    "dewberry": ["dewberry engineers"],
    "heidelberg-materials": ["heidelberg materials us"],
    "axon": ["axon enterprise", "axon enteprise"],
    "aegis-therapies": ["aegis therapies"],
    "concentra": ["concentra health services"],
    "dartmouth-hitchcock-health": ["dartmouth hitchcock clinic"],
    "huntsville-hospital-health-system": ["health care authority of the city of huntsville"],
    "kyndryl": ["kyndryl"],
    "vcu-health": ["vcu health system authority"],
    "novolex": ["novolex holdings"],
    "essen-medical-associates": ["essen medical associates"],
    "ferguson": ["ferguson enterprises"],
    "gundersen-health-system": ["gundersen lutheran administrative services"],
    "centene": ["centene management"],
    "procter-gamble": ["procter and gamble", "procter and gamble us business services", "procter and gamble manufacturing", "procter and gamble manufactruing"],
    "appalachian-regional-healthcare": ["appalachian regional healthcare"],
    "commonspirit-health": ["commonspirit health"],
    "wolters-kluwer": ["wolters kluwer dxg us", "wolters kluwer united states", "wolters kluwer r and d us"],
    "ou-health": ["ou health partners"],
    "broadcom": ["broadcom"],
    "graybar": ["graybar electric"],
    "allstate": ["allstate insurance"],
    "mongodb": ["mongodb"],
    "walmart": ["wal mart associates"],
    "barry-wehmiller": ["barry wehmiller companies"],
    "state-of-oklahoma": ["state of oklahoma"],
    "dh-pace": ["dh pace"],
    "banner-health": ["banner health"],
    "renuity": ["renuity operations"],
    "j-b-hunt": ["jb hunt transport"],
    "westwood-professional-services": ["westwood professional services"],
    "gilead-sciences": ["gilead sciences"],
    "doordash-usa": ["doordash", "doordash essentials"],
    "itw": ["illinois tool works", "itw food equipment group", "itw building components group", "itw gse", "instron a division of illinois tool works"],
    "concord-hospital": ["concord hospital", "concord hospital laconia"],
    "sulzer": ["sulzer ems", "sulzer chemtech usa", "sulzer turbo services houston", "sulzer pumps", "sulzer pumps solutions"],
    "universities-of-wisconsin": ["university of wisconsin system", "university of wisconsin milwaukee", "university of wisconsin whitewater"],
    "unisys": ["unisys"],
    "naphcare": ["naphcare", "naphcare operating llc fka naphcare us"],
    "zscaler": ["zscaler"],
    "loenbro": ["loenbro"],
    "elastic": ["elasticsearch"],
    "pure-storage": ["pure storage"],
    "niagara-bottling": ["niagara bottling"],
    "harvey": ["harvey ai"],
    "datadog": ["datadog"],
    "travelers": ["travelers indemnity"],
    "medical-college-of-wisconsin": ["medical college of wisconsin", "medical college of wisconsin affiliated hospitals"],
    "university-of-chicago": ["university of chicago"],
    "fleetpride": ["fleetpride"],
    "uline": ["uline"],
    "aig": ["aig pc global services", "aig employee services", "aig technical services", "aig global operations", "aig claims", "aig technologies"],
    "convenientmd": ["convenientmd"],
    "snowflake": ["snowflake", "snowflake public sector"],
    "okta": ["okta"],
    "air-products": ["air products and chemicals"],
    "crowdstrike": ["crowdstrike"],
    "rocket-companies": ["rocket limited partnership", "rocket mortgage", "rocket close", "rocket"],
    "nidec": ["nidec motor", "nidec mobility america", "nidec americas holding", "nidec sv probe pte", "nidec minster", "nidec drive technology america",
              "nidec america", "nidec aerospace"],
    "fedex-express": ["federal express"],
    "waymo": ["waymo"],
    "healthpro-heritage": ["healthpro heritage"],
    "iron-mountain": ["iron mountain information management", "iron mountain information management services"],
    "group-1-automotive": ["group 1 automotive"],
    "gilbane-building": ["gilbane building"],
    "lineage": ["lineage logistics", "lineage logistics services"],
    "meijer": ["meijer great lakes limited partnership", "meijer stores limited partnership"],
    "hersha-hospitality-management-lp": ["hersha hospitality management"],
    "verkada": ["verkada"],
    "sargent-lundy": ["sargent and lundy"],
    "braze": ["braze"],
}
# Our names that match a DOL name or trade name but are not that employer (namesakes, franchisees filing under the brand).
NOT_THIS = {"aamco-transmissions-and-total-car-care", "1-800-got-junk", "precision-door-service", "avanta-dental", "mega-saver", "hanover-park",
            "summit-products", "amp-americas", "mercury", "motive", "software", "smartly", "gentex", "hex", "the-paramount", "zebra", "greif",
            "st-luke-s-hospital", "st-lukes-hospital", "nory", "nory-co", "christ-presbyterian-church", "christ-presbyterian-academy", "hansen",
            "community-health-care", "community-health-system", "family-health-care", "signature-health", "community-partners", "sequoia-services", "american-leadership-academy", "compass-health-network",
            "optima", "hyde", "stax", "genesys", "aem", "ais", "swd", "vrx", "stn", "jnd"}

# ---------- reading the xlsx ----------
CELL = re.compile(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
VAL = re.compile(r"<v>(.*?)</v>", re.S)
INL = re.compile(r"<t[^>]*>(.*?)</t>", re.S)
TYP = re.compile(r'\bt="(\w+)"')


def _unesc(s):
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


def _col(letters):
    n = 0
    for ch in letters: n = n * 26 + (ord(ch) - 64)
    return n - 1


def _shared(z):
    out = []
    try: f = z.open("xl/sharedStrings.xml")
    except KeyError: return out
    with f:
        for _, el in ET.iterparse(f, events=("end",)):
            if el.tag == NS + "si":
                out.append("".join(t.text or "" for t in el.iter(NS + "t")))
                el.clear()
    return out


def rows(path):
    """Each row of the first sheet as {column index: value}, read in 4 MB pieces."""
    z = zipfile.ZipFile(path)
    ss = _shared(z)
    with z.open("xl/worksheets/sheet1.xml") as f:
        buf, started = "", False
        while True:
            chunk = f.read(4 << 20)
            if not chunk and not buf: break
            buf += chunk.decode("utf-8") if chunk else ""
            if not started:
                i = buf.find("<sheetData>")
                if i < 0:
                    if not chunk: break
                    continue
                buf, started = buf[i + len("<sheetData>"):], True
            parts = buf.split("</row>")
            buf = parts.pop() if chunk else ""
            for p in parts:
                i = p.find("<row")
                if i < 0: continue
                row = {}
                for m in CELL.finditer(p, i):
                    letters, attrs, inner = m.groups()
                    if inner is None: continue
                    t = TYP.search(attrs)
                    t = t.group(1) if t else ""
                    if t == "s":
                        v = VAL.search(inner); row[_col(letters)] = ss[int(v.group(1))] if v else ""
                    elif t == "inlineStr":
                        row[_col(letters)] = _unesc("".join(INL.findall(inner)))
                    else:
                        v = VAL.search(inner); row[_col(letters)] = _unesc(v.group(1)) if v else ""
                yield row
            if not chunk: break


KEEP = ["CASE_NUMBER", "CASE_STATUS", "RECEIVED_DATE", "DECISION_DATE", "VISA_CLASS", "JOB_TITLE", "SOC_CODE", "SOC_TITLE",
        "FULL_TIME_POSITION", "BEGIN_DATE", "TOTAL_WORKER_POSITIONS", "NEW_EMPLOYMENT", "CONTINUED_EMPLOYMENT",
        "EMPLOYER_NAME", "TRADE_NAME_DBA", "EMPLOYER_CITY", "EMPLOYER_STATE", "EMPLOYER_COUNTRY", "EMPLOYER_FEIN", "NAICS_CODE",
        "WORKSITE_CITY", "WORKSITE_STATE", "WAGE_RATE_OF_PAY_FROM", "WAGE_RATE_OF_PAY_TO", "WAGE_UNIT_OF_PAY", "PW_WAGE_LEVEL",
        "PREVAILING_WAGE", "PW_UNIT_OF_PAY", "H_1B_DEPENDENT", "WILLFUL_VIOLATOR", "AGENT_REPRESENTING_EMPLOYER"]
DATES = {"RECEIVED_DATE", "DECISION_DATE", "BEGIN_DATE"}


def _xl_date(v):
    try: return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(v)))).isoformat()
    except (ValueError, TypeError): return v


def extract(path, out):
    it = rows(path)
    head = next(it)
    hdr = {head[i].strip().upper().replace("-", "_"): i for i in head}      # FY2025 says H-1B_DEPENDENT, FY2026 H_1B_DEPENDENT
    idx = [hdr.get(k) for k in KEEP]
    vc, n, kept = hdr["VISA_CLASS"], 0, 0
    with open(out, "w", encoding="utf-8") as o:
        o.write("\t".join(KEEP) + "\n")
        for r in it:
            n += 1
            if str(r.get(vc, "")).strip() != "H-1B": continue
            kept += 1
            vals = []
            for k, i in zip(KEEP, idx):
                v = "" if i is None else str(r.get(i, ""))
                if k in DATES: v = _xl_date(v)
                vals.append(re.sub(r"[\t\r\n]", " ", v).strip())
            o.write("\t".join(vals) + "\n")
    print(f"{Path(path).name}: {n:,} rows, {kept:,} H-1B")


# ---------- names and wages ----------
SUFFIX = {"inc", "incorporated", "llc", "corp", "corporation", "co", "company", "ltd", "limited", "lp", "llp", "plc", "pllc",
          "pc", "pa", "na", "ltda", "sa", "ag", "gmbh", "bv", "nv", "srl", "pty", "pvt", "lllp", "psc", "dba"}


def norm(name):
    """'Amazon.com Services, LLC' -> 'amazoncom services'; 'The Walt Disney Company' -> 'walt disney'; 'JPMorgan Chase & Co.' -> 'jpmorgan chase'."""
    s = (name or "").lower().replace("&", " and ").replace("+", " and ")
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"['’`]", "", s).replace(".", "")
    out, run = [], False
    for t in re.sub(r"[^a-z0-9]+", " ", s).split():          # "l l c" -> "llc", "u s" -> "us"
        single = len(t) == 1 and t.isalpha()
        if single and run: out[-1] += t
        else: out.append(t)
        run = single
    if "dba" in out[1:]: out = out[:out.index("dba", 1)]
    while out and out[0] == "the": out.pop(0)
    while len(out) > 1 and (out[-1] in SUFFIX or out[-1] == "and"): out.pop()
    return " ".join(out)


UNIT = {"Year": 1, "Hour": 2080, "Week": 52, "Bi-Weekly": 26, "Month": 12}


def annual(v, unit):
    try: x = float(str(v).replace("$", "").replace(",", ""))
    except ValueError: return None
    m = UNIT.get(unit)
    if not m or x <= 0: return None
    a = x * m
    return a if 15000 <= a <= 2000000 else None


ACRO = {"AI", "ML", "QA", "IT", "UI", "UX", "VP", "SVP", "AVP", "EVP", "SAP", "ERP", "CRM", "AWS", "GCP", "SQL", "ETL", "BI", "HR", "R&D",
        "RN", "MD", "PHD", "CAD", "PLC", "SoC", "ASIC", "FPGA", "RF", "DevOps", "SRE", "API", "iOS", "US", "USA", "II", "III", "IV", "VI", "NA", "CFO", "CTO"}
ACRO_L = {a.lower(): a for a in ACRO}


def tidy_title(t):
    """A job title as filed, readable: 'SOFTWARE ENGINEER II' -> 'Software Engineer II'; mixed case is kept."""
    t = re.sub(r"\s+", " ", t).strip(" -,;")
    if t != t.upper(): return t
    return re.sub(r"[A-Za-z][A-Za-z&']*", lambda m: ACRO_L.get(m.group(0).lower(), m.group(0).capitalize()), t)


def _median(xs):
    return statistics.median(xs) if xs else None


# ---------- building data/h1b.json ----------
def build(work, matches_path, out=None):
    work = Path(work)
    prev = json.loads(Path(matches_path).read_text())
    prev = prev.get("companies", prev)
    who = defaultdict(set)                                     # normalised DOL name -> our slugs (one company can have two pages here)
    how, names = {}, {}
    for slug, m in prev.items():
        names[slug] = m.get("name", "")
        if slug in NOT_THIS or slug in ALIAS: continue
        for k in m["keys"]: who[k].add(slug)
        how[slug] = m.get("how", "name")
    for slug, keys in ALIAS.items():
        for k in keys: who[k] = {slug}
        how[slug] = "checked by hand"
    stats = {}
    totals = {}
    for fy in (2025, 2026):
        files = sorted(work.glob(f"FY{fy}_Q*.tsv"))
        best = {}
        for fi, f in enumerate(files):                         # the latest decision of each case
            with open(f, encoding="utf-8") as h:
                head = h.readline().rstrip("\n").split("\t")
                ci, di = head.index("CASE_NUMBER"), head.index("DECISION_DATE")
                for ln, line in enumerate(h):
                    p = line.rstrip("\n").split("\t")
                    key = (p[di], fi, ln)
                    if p[ci] not in best or best[p[ci]] < key: best[p[ci]] = key
        keep = defaultdict(set)
        for _, fi, ln in best.values(): keep[fi].add(ln)
        st = Counter()
        for fi, f in enumerate(files):
            with open(f, encoding="utf-8") as h:
                ix = {k: i for i, k in enumerate(h.readline().rstrip("\n").split("\t"))}
                for ln, line in enumerate(h):
                    if ln not in keep[fi]: continue
                    p = line.rstrip("\n").split("\t")
                    g = lambda k: p[ix[k]]
                    s_ = g("CASE_STATUS"); st[s_] += 1
                    if s_ not in ("Certified", "Certified - Withdrawn"): continue
                    for slug in who.get(norm(g("EMPLOYER_NAME")), ()):
                        c = stats.setdefault(slug, {}).setdefault(fy, {"cert": 0, "wd": 0, "names": Counter(), "titles": defaultdict(list),
                                                                          "tcase": defaultdict(Counter), "ws": Counter()})
                        if s_ == "Certified - Withdrawn": c["wd"] += 1; continue
                        c["cert"] += 1
                        c["names"][g("EMPLOYER_NAME").strip()] += 1
                        t = tidy_title(g("JOB_TITLE"))
                        tk = re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()
                        if tk:
                            c["tcase"][tk][t] += 1
                            c["titles"][tk].append(annual(g("WAGE_RATE_OF_PAY_FROM"), g("WAGE_UNIT_OF_PAY")) if g("FULL_TIME_POSITION") == "Y" else None)
                        city = re.sub(r"\s+", " ", g("WORKSITE_CITY")).strip(" ,.").title()
                        if city: c["ws"][(city, g("WORKSITE_STATE").strip().upper())] += 1
        totals[str(fy)] = {"cases": len(best), "certified": st["Certified"], "certified_withdrawn": st["Certified - Withdrawn"],
                           "withdrawn": st["Withdrawn"], "denied": st["Denied"]}
    comp = {}
    for slug, by in stats.items():
        if not any(v["cert"] for v in by.values()): continue
        rfy = max(fy for fy, v in by.items() if v["cert"])
        r = by[rfy]
        roles = []
        for tk, ws in sorted(r["titles"].items(), key=lambda kv: (-len(kv[1]), kv[0]))[:5]:
            wv = [w for w in ws if w]
            med = _median(wv)
            roles.append([r["tcase"][tk].most_common(1)[0][0], len(ws), round(med / 100) * 100 if med else None])
        allnames = Counter()
        for v in by.values(): allnames.update(v["names"])
        comp[slug] = {"name": names.get(slug, ""), "how": how.get(slug, "name"),
                      "dol": [n for n, _ in allnames.most_common(3)],
                      "keys": sorted(k for k, s in who.items() if slug in s),
                      "fy": {str(fy): [v["cert"], v["wd"]] for fy, v in sorted(by.items())},      # [certified, certified then withdrawn]
                      "rfy": rfy, "roles": roles,
                      "cities": [[c_, s_, n_] for (c_, s_), n_ in r["ws"].most_common(5)]}
    data = {"source": {"title": "LCA Programs (H-1B, H-1B1, E-3) Disclosure Data",
                       "publisher": "U.S. Department of Labor, Employment and Training Administration, Office of Foreign Labor Certification",
                       "page": PAGE, "read": READ, "files": [{"name": n, "fy": fy, "posted": d} for n, fy, d in FILES],
                       "years": {"2025": "October 1, 2024 to September 30, 2025", "2026": "October 1, 2025 to September 30, 2026"},
                       "rule": "VISA_CLASS H-1B, CASE_STATUS Certified; Certified - Withdrawn counted apart; each case once, from its latest decision",
                       "wage": "WAGE_RATE_OF_PAY_FROM made yearly, full-time positions only, median per job title",
                       "totals": totals},
            "companies": dict(sorted(comp.items()))}
    out = Path(out or ROOT / "data" / "h1b.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{out}: {len(comp):,} companies, {out.stat().st_size / 1e6:.2f} MB; DOL totals {totals}")


if __name__ == "__main__":
    if sys.argv[1] == "extract": extract(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "build": build(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else: print(__doc__)
