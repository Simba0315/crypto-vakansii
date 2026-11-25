"""How people get into work that pays about $25 an hour or more without a college degree: the training route of each, read from the
US Bureau of Labor Statistics' Occupational Outlook Handbook ("How to Become One" and the quick facts of each occupation's page).

Why (26 Nov 2026): ChatGPT, asked in a temporary chat "jobs that pay $25 an hour without a degree", answers with jobs and the training
each needs (an apprenticeship, a CDL, a license); /jobs-that-pay/25-an-hour/ had the jobs and the pay but no route into them.

Each row: the occupation as the Handbook names it, the Handbook page (read on READ in a real browser), its 2025 median pay as that page
shows it (yearly and hourly; the Handbook gives May 2025 wages), the typical education to enter, the training, and the license or
certificate where the page names one ("" where it names none). `rx` finds today's postings for the work by their title; `out` drops
titles of the same words that are not this work (an HVAC design engineer is not an HVAC technician). The open postings and their pay
are counted in build.py on every build, never written here.

Run `python3 trade_training.py` to check the data.
"""
import re

READ = "2026-11-26"
SOURCE = "https://www.bls.gov/ooh/"
OUT = r"engineer|design|manager|director|instructor|teacher|recruit|sales|estimator|analyst|scientist|planner|coordinator|inspector|intern\b"

ROUTES = [
    {"name": "Electrician", "role": "electrician", "ooh": "https://www.bls.gov/ooh/construction-and-extraction/electricians.htm#tab-4",
     "year": 63190, "hour": 30.38, "edu": "High school diploma or equivalent",
     "route": "An apprenticeship of 4 or 5 years: about 2,000 hours of paid training on the job each year, plus classes",
     "license": "Most states require a license: a test on the National Electrical Code and local codes",
     "rx": r"electrician|wireman"},
    {"name": "Plumber, pipefitter or steamfitter", "role": "plumber-pipefitter", "ooh": "https://www.bls.gov/ooh/construction-and-extraction/plumbers-pipefitters-and-steamfitters.htm#tab-4",
     "year": 63800, "hour": 30.67, "edu": "High school diploma or equivalent",
     "route": "An apprenticeship of 4 or 5 years, 2,000 paid hours a year plus classes; some start as helpers or in a pre-apprenticeship",
     "license": "Most states and some localities license plumbers, often after 2 to 5 years of experience and an exam",
     "rx": r"plumb(er|ing)|pipe ?fitter|steamfitter"},
    {"name": "HVAC technician", "role": "hvac-technician", "ooh": "https://www.bls.gov/ooh/installation-maintenance-and-repair/heating-air-conditioning-and-refrigeration-mechanics-and-installers.htm#tab-4",
     "year": 61010, "hour": 29.33, "edu": "A certificate from a trade school or community college (some employers hire from high school)",
     "route": "A program of 6 months to 2 years, or an apprenticeship of several years; then long on-the-job training",
     "license": "EPA certification to handle refrigerants, needed by nearly all; some states and localities license",
     "rx": r"\bhvac\b|refrigeration (tech|mech)|air conditioning (tech|mech|install)"},
    {"name": "Heavy truck driver", "role": "", "ooh": "https://www.bls.gov/ooh/transportation-and-material-moving/heavy-and-tractor-trailer-truck-drivers.htm#tab-4",
     "year": 58640, "hour": 28.19, "edu": "High school diploma, then a truck-driving school certificate",
     "route": "A truck-driving school of 3 to 6 months, then several weeks driving beside a mentor",
     "license": "A commercial driver’s license (CDL): a knowledge test and a driving test; a medical exam every two years",
     "rx": r"truck driver|\bcdl\b|tractor[- ]trailer|class a driver"},
    {"name": "Welder", "role": "welder", "ooh": "https://www.bls.gov/ooh/production/welders-cutters-solderers-and-brazers.htm#tab-4",
     "year": 53750, "hour": 25.84, "edu": "High school diploma or equivalent, with technical training",
     "route": "Classes at a vocational school or community college, or an employer apprenticeship; then several months on the job",
     "license": "Some states and localities license welders",
     "rx": r"\bwelder\b|\bwelding (tech|operator|specialist)"},
    {"name": "Machinist", "role": "machinist", "ooh": "https://www.bls.gov/ooh/production/machinists-and-tool-and-die-makers.htm#tab-4",
     "year": 59620, "hour": 28.66, "edu": "High school diploma (tool and die makers may need college courses)",
     "route": "Training on the job or an apprenticeship of several years; short certificate programs at community colleges",
     "license": "Optional certificates, for example in CNC machine operation",
     "rx": r"machinist|\bcnc (operator|machinist|programmer|setup|set-up)"},
    {"name": "Diesel technician", "role": "", "ooh": "https://www.bls.gov/ooh/installation-maintenance-and-repair/diesel-service-technicians-and-mechanics.htm#tab-4",
     "year": 61770, "hour": 29.70, "edu": "High school diploma or equivalent",
     "route": "Long training on the job; some employers prefer a certificate program in diesel repair",
     "license": "Industry certification, which some employers require",
     "rx": r"diesel (tech|mech)|heavy (duty|equipment) (tech|mech)|fleet (tech|mech)"},
    {"name": "Industrial machinery mechanic or millwright", "role": "", "ooh": "https://www.bls.gov/ooh/installation-maintenance-and-repair/industrial-machinery-mechanics-and-maintenance-workers-and-millwrights.htm#tab-4",
     "year": 64100, "hour": 30.82, "edu": "High school diploma or equivalent",
     "route": "A year or more of training on the job; millwrights a 3- or 4-year apprenticeship",
     "license": "",
     "rx": r"industrial (maintenance|mechanic|machinery)|maintenance mechanic|millwright"},
    {"name": "Power-line installer", "role": "", "ooh": "https://www.bls.gov/ooh/installation-maintenance-and-repair/line-installers-and-repairers.htm#tab-4",
     "year": 95320, "hour": 45.83, "edu": "High school diploma or equivalent",
     "route": "An apprenticeship or employer training of up to 3 years; some take a 1-year certificate first",
     "license": "Certification is optional; those who drive heavy vehicles usually need a CDL",
     "rx": r"\bline ?(wo)?man\b|lineworker|line worker|power[- ]line|line (installer|repairer)"},
    {"name": "Licensed practical nurse (LPN)", "role": "", "ooh": "https://www.bls.gov/ooh/healthcare/licensed-practical-and-licensed-vocational-nurses.htm#tab-4",
     "year": 64400, "hour": 30.96, "edu": "A state-approved certificate or diploma program, about 1 year",
     "route": "The program at a community college or technical school, with supervised clinical practice",
     "license": "A state license: an exam after the program",
     "rx": r"\blpn\b|\blvn\b|licensed (practical|vocational) nurse"},
]


def matcher(r):
    """A function title -> True for postings of this work."""
    hit, out = re.compile(r["rx"], re.I), re.compile(OUT, re.I)
    return lambda t: bool(hit.search(t or "")) and not out.search(t or "")


def test():
    names = [r["name"] for r in ROUTES]
    assert len(names) == len(set(names))
    for r in ROUTES:
        assert r["ooh"].startswith(SOURCE) and "#tab-4" in r["ooh"], r["name"]
        assert abs(r["year"] / 2080 - r["hour"]) < 0.01, r["name"]        # the Handbook's hourly figure is the yearly one over 2,080 hours
        assert r["hour"] >= 25, r["name"]                                    # the table answers "$25 an hour without a degree"
        assert r["edu"] and r["route"] and not r["route"].endswith("."), r["name"]
        m = matcher(r)
        assert not m("HVAC Design Engineer") and not m("Sales Manager"), r["name"]
    assert matcher(ROUTES[0])("Journeyman Electrician") and matcher(ROUTES[3])("Class A CDL Driver") and not matcher(ROUTES[8])("End of Line Technician")
    return len(ROUTES)


if __name__ == "__main__":
    print(test(), "routes")
