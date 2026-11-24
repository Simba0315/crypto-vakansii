"""US government wage figures shown beside the pay advertised in job postings (/salaries/<role>/).

Search check, 18 Nov 2026 ("data analyst salary"): the first results and the AI answers quote the Bureau of Labor Statistics, and our page
showed only advertised pay. Each row is (occupation title, people employed, 10th percentile, median, 90th percentile), yearly US dollars, read
from the BLS public data service (Occupational Employment and Wage Statistics, national, all industries; series OEUN0000000000000<code><type>,
types 01, 11, 13, 15). Titles are the ones in the BLS national table. ROLE says which occupation is the closest one to a kind of work on this
site; a role with no honest match is left out rather than forced into one.

Run `python3 bls_wages.py` to check the data.
"""
PERIOD = "May 2025"
READ = "2026-11-19"
SOURCE = "https://www.bls.gov/oes/tables.htm"

OCC = {
    "11-1021": ("General and Operations Managers", 3503020, 50090, 105770, 253390),
    "11-2021": ("Marketing Managers", 395240, 90260, 166790, 293610),
    "11-2022": ("Sales Managers", 637080, 73170, 148270, 290540),
    "11-3021": ("Computer and Information Systems Managers", 670570, 107550, 175140, 297510),
    "11-3031": ("Financial Managers", 841710, 94310, 166570, 323270),
    "11-3121": ("Human Resources Managers", 220660, 88200, 149280, 267810),
    "11-9021": ("Construction Managers", 380360, 69690, 114990, 189440),
    "13-1020": ("Buyers and Purchasing Agents", 491430, 48380, 77710, 128870),
    "13-1041": ("Compliance Officers", 417070, 48220, 80730, 133720),
    "13-1071": ("Human Resources Specialists", 912430, 47180, 75940, 128720),
    "13-1081": ("Logisticians", 251040, 50890, 82320, 133160),
    "13-1082": ("Project Management Specialists", 1066670, 61580, 102320, 167970),
    "13-1111": ("Management Analysts", 898280, 60640, 101860, 171640),
    "13-1141": ("Compensation, Benefits, and Job Analysis Specialists", 112380, 49480, 78210, 128920),
    "13-1151": ("Training and Development Specialists", 458300, 38760, 69280, 123250),
    "13-1161": ("Market Research Analysts and Marketing Specialists", 899580, 43390, 78760, 155480),
    "13-2011": ("Accountants and Auditors", 1449500, 56020, 83680, 144090),
    "13-2051": ("Financial and Investment Analysts", 361980, 63720, 102740, 180860),
    "15-1212": ("Information Security Analysts", 190650, 75090, 129180, 199850),
    "15-1232": ("Computer User Support Specialists", 717190, 40980, 61860, 100540),
    "15-1241": ("Computer Network Architects", 179740, 79900, 134050, 202680),
    "15-1243": ("Database Architects", 67140, 86240, 139500, 204000),
    "15-1244": ("Network and Computer Systems Administrators", 314340, 62640, 99130, 155050),
    "15-1251": ("Computer Programmers", 92230, 57710, 100390, 160460),
    "15-1252": ("Software Developers", 1687890, 82460, 135980, 214670),
    "15-1253": ("Software Quality Assurance Analysts and Testers", 186740, 61440, 104300, 167010),
    "15-1254": ("Web Developers", 70190, 48100, 92650, 162290),
    "15-1255": ("Web and Digital Interface Designers", 113330, 53750, 104000, 201550),
    "15-2011": ("Actuaries", 26670, 78570, 130000, 215100),
    "15-2051": ("Data Scientists", 262440, 67240, 120230, 199130),
    "17-2051": ("Civil Engineers", 367840, 68240, 100840, 163220),
    "17-2061": ("Computer Hardware Engineers", 76660, 92940, 161740, 225330),
    "17-2071": ("Electrical Engineers", 198750, 76550, 120630, 184300),
    "17-2112": ("Industrial Engineers", 365740, 74370, 102440, 159860),
    "17-2131": ("Materials Engineers", 22770, 72300, 112860, 175720),
    "17-2141": ("Mechanical Engineers", 296810, 73990, 104110, 164340),
    "23-1011": ("Lawyers", 754500, 78360, 159670, 351600),
    "23-2011": ("Paralegals and Legal Assistants", 392880, 44740, 62890, 101500),
    "27-1024": ("Graphic Designers", 197830, 39520, 62960, 104910),
    "27-3043": ("Writers and Authors", 47940, 44310, 76910, 139870),
    "41-3091": ("Sales Representatives of Services", 1256010, 37980, 69990, 148840),
    "41-9031": ("Sales Engineers", 51790, 73870, 124900, 195270),
    "43-3031": ("Bookkeeping, Accounting, and Auditing Clerks", 1373680, 36000, 50670, 74550),
    "43-3051": ("Payroll and Timekeeping Clerks", 153140, 39500, 58260, 81350),
    "43-4051": ("Customer Service Representatives", 2595750, 31750, 44770, 63590),
    "43-5061": ("Production, Planning, and Expediting Clerks", 390160, 40080, 59650, 86000),
    "43-6011": ("Executive Secretaries and Executive Administrative Assistants", 459910, 50560, 76590, 109850),
    "51-1011": ("First-Line Supervisors of Production and Operating Workers", 673430, 47130, 74450, 108750),
}

ROLE = {
    "general-manager": "11-1021",
    "operations-manager": "11-1021",
    "marketing-manager": "11-2021",
    "sales-manager": "11-2022",
    "engineering-manager": "11-3021",
    "controller": "11-3031",
    "finance-manager": "11-3031",
    "hr-director": "11-3121",
    "construction-manager": "11-9021",
    "procurement": "13-1020",
    "strategic-sourcing": "13-1020",
    "compliance-officer": "13-1041",
    "hr-business-partner": "13-1071",
    "recruiter": "13-1071",
    "technical-recruiter": "13-1071",
    "supply-chain-planner": "13-1081",
    "program-manager": "13-1082",
    "project-manager": "13-1082",
    "business-analyst": "13-1111",
    "compensation-benefits": "13-1141",
    "corporate-trainer": "13-1151",
    "marketing-analyst": "13-1161",
    "senior-accountant": "13-2011",
    "financial-analyst": "13-2051",
    "security-analyst": "15-1212",
    "security-engineer": "15-1212",
    "soc-analyst": "15-1212",
    "help-desk": "15-1232",
    "it-support": "15-1232",
    "network-engineer": "15-1241",
    "data-engineer": "15-1243",
    "system-administrator": "15-1244",
    "programmer": "15-1251",
    "android-developer": "15-1252",
    "backend-engineer": "15-1252",
    "cpp-developer": "15-1252",
    "full-stack-engineer": "15-1252",
    "game-programmer": "15-1252",
    "ios-developer": "15-1252",
    "mobile-engineer": "15-1252",
    "python-developer": "15-1252",
    "software-engineer": "15-1252",
    "qa-engineer": "15-1253",
    "test-engineer": "15-1253",
    "frontend-engineer": "15-1254",
    "web-developer": "15-1254",
    "product-designer": "15-1255",
    "ux-designer": "15-1255",
    "actuary": "15-2011",
    "bi-developer": "15-2051",
    "data-analyst": "15-2051",
    "data-scientist": "15-2051",
    "structural-engineer": "17-2051",
    "hardware-engineer": "17-2061",
    "electrical-engineer": "17-2071",
    "manufacturing-engineer": "17-2112",
    "materials-engineer": "17-2131",
    "mechanical-engineer": "17-2141",
    "commercial-counsel": "23-1011",
    "employment-counsel": "23-1011",
    "legal-counsel": "23-1011",
    "paralegal": "23-2011",
    "graphic-designer": "27-1024",
    "content-writer": "27-3043",
    "account-executive": "41-3091",
    "sales-representative": "41-3091",
    "sales-engineer": "41-9031",
    "accounts-payable": "43-3031",
    "accounts-receivable": "43-3031",
    "payroll": "43-3051",
    "chat-support": "43-4051",
    "customer-support": "43-4051",
    "production-planner": "43-5061",
    "executive-assistant": "43-6011",
    "production-supervisor": "51-1011",
    # 24 Nov 2026: kinds of work that got example pages of their own; each is counted inside one of the categories above
    "nodejs-developer": "15-1252", "dotnet-developer": "15-1252", "ruby-developer": "15-1252", "kotlin-developer": "15-1252",
    "cross-platform-mobile": "15-1252", "desktop-developer": "15-1252", "junior-software-engineer": "15-1252", "compiler-engineer": "15-1252",
    "react-developer": "15-1254", "javascript-developer": "15-1254", "angular-vue-developer": "15-1254",
    "sql-developer": "15-1243", "reporting-analyst": "15-2051",
    "bookkeeper": "43-3031", "cost-accountant": "13-2011", "fund-accountant": "13-2011",
    "benefits-specialist": "13-1141", "employee-relations": "13-1071",
    "vulnerability-management": "15-1212", "ciso": "11-3021", "coo": "11-1021",
}

# what a reader must know about the match
NOTE = {
    "data-analyst": "The government has no separate category for data analysts; business intelligence analysts are counted under this one.",
    "bi-developer": "Business intelligence work is counted under this category.",
    "account-executive": "The category covers people who sell services, in every industry except advertising, insurance, financial services and travel.",
    "sales-representative": "The category covers people who sell services, in every industry except advertising, insurance, financial services and travel.",
    "structural-engineer": "Structural engineers are counted among civil engineers.",
    "manufacturing-engineer": "Manufacturing engineers are counted among industrial engineers.",
    "reporting-analyst": "The government has no separate category for reporting analysts; business intelligence work is counted under this one.",
    "sql-developer": "The government counts database developers with database architects.",
    "ciso": "Chief information security officers are counted among computer and information systems managers.",
    "coo": "Chief operating officers are counted among general and operations managers; chief executives are a separate category.",
}


def check():
    for c, (t, emp, lo, med, hi) in OCC.items():
        assert t and emp > 0 and 0 < lo < med < hi, c
    for s, c in ROLE.items(): assert c in OCC, s
    for s in NOTE: assert s in ROLE, s
    return len(OCC), len(ROLE)


if __name__ == "__main__":
    print("%d occupations, %d roles matched, %s" % (*check(), PERIOD))
