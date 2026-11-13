"""Free tools section: the /tools/ hub and one page per tool.

build.py calls build_tools() and passes its own page helpers. The behaviour of every tool lives in assets/tools.js
(pure functions tested under Node + page wiring) and the extra styles in assets/tools.css. Nothing here needs a server:
each tool runs in the visitor's browser, and the only data embedded in a page is a small set of salary aggregates.
"""
import datetime, json
from collections import defaultdict
from html import escape as _e

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
EXTRA = ["resume/", "for-you/", "my-jobs/"]                             # the three big tools that live on their own pages: shown first, on the hub and on the home page
TILES = {}                                                             # page path -> ready tile, filled by build_tools() so the home page can show the same tiles
MIN_SAMPLE = 20                                                       # no salary figure is shown for fewer postings than this
QS = [0, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 100]      # percentile points embedded for the salary checker
LEVELS = [("", "Any level"), ("Intern", "Intern"), ("Junior", "Junior"), ("none", "No level in the title"), ("Senior", "Senior"), ("Lead", "Lead")]


# ---------------------------------------------------------------- small HTML helpers

def _ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def _f(k, label, ph="", val="", hint="", mode="decimal", cls="", typ="text", auto="off", show="", lid=""):
    """One labelled input. `k` is the key the value is saved under (data-k) and the end of the element id."""
    return (f'<div class="tl-f{" " + cls if cls else ""}"{show}><label class="tl-l" for="tl-{k}"{f" id={chr(34)}{lid}{chr(34)}" if lid else ""}>{label}</label>'
            f'<input class="tl-in" id="tl-{k}" data-k="{k}" type="{typ}"' + (f' inputmode="{mode}"' if mode else "") + f' autocomplete="{auto}"'
            + (f' placeholder="{_e(ph)}"' if ph else "") + (f' value="{_e(val)}"' if val else "") + ">"
            + (f'<p class="tl-h">{hint}</p>' if hint else "") + "</div>")


def _sel(k, label, options, hint="", cls="", attrs="", show=""):
    """A labelled select. options: (value, text) or (value, text, True) for the default."""
    opts = "".join(f'<option value="{_e(o[0])}"{" selected" if len(o) > 2 and o[2] else ""}>{_e(o[1])}</option>' for o in options)
    return (f'<div class="tl-f{" " + cls if cls else ""}"{show}><label class="tl-l" for="tl-{k}">{label}</label><select id="tl-{k}" data-k="{k}"{attrs}>{opts}</select>'
            + (f'<p class="tl-h">{hint}</p>' if hint else "") + "</div>")


def _area(k, label, rows, ph="", hint="", cls="full", tall=False, show="", ex=""):
    """`ex` is the text the "Show an example" button puts in; without it the placeholder is used when it is itself an example."""
    return (f'<div class="tl-f{" " + cls if cls else ""}"{show}><label class="tl-l" for="tl-{k}">{label}</label>'
            f'<textarea id="tl-{k}" data-k="{k}" rows="{rows}"{" class=" + chr(34) + "tl-tall" + chr(34) if tall else ""}' + (f' placeholder="{_e(ph)}"' if ph else "")
            + (f' data-ex="{_e(ex)}"' if ex else "") + "></textarea>"
            + (f'<p class="tl-h">{hint}</p>' if hint else "") + "</div>")


def _check(k, label, checked=False, show=""):
    return f'<label class="check"{show}><input type="checkbox" data-k="{k}"{" checked" if checked else ""}> {label}</label>'


def _cur(k="cur"):
    return _sel(k, "Currency", [("$", "$ dollar"), ("€", "€ euro"), ("£", "£ pound"), ("₹", "₹ rupee"), ("", "No symbol")])


def _board(title, msg):
    """The dark result board. Filled in by tools.js; the text here is what shows before anything is typed."""
    return (f'<div class="tl-board" id="tl-out" aria-live="polite"><div class="tl-board-h"><span>{title}</span><b></b></div>'
            f'<p class="tl-big tl-dim">—</p><p class="tl-sub">{msg}</p></div>')


def _clear(ask=False):
    return ('<button class="btn ghost sm tl-end" type="button" data-example>Show an example</button>'
            f'<button class="btn ghost sm" type="button" data-clear{"=" + chr(34) + "ask" + chr(34) if ask else ""}>Clear</button>')


EX_RESUME = ("Alex Morgan\nSenior Backend Engineer\n\nSummary\nBackend engineer with 8 years of experience building APIs and data pipelines in Python and Go.\n\n"
             "Experience\nSenior Backend Engineer, Example Co, 2021 to now\n- Built a payments API in Python and PostgreSQL that handles 4 million requests a day\n"
             "- Cut p95 latency from 900 ms to 250 ms by adding Redis caching\n- Moved 30 services to Kubernetes on AWS with Terraform\n\n"
             "Backend Engineer, Sample Ltd, 2017 to 2021\n- Wrote REST and GraphQL services in Python (Django)\n- Set up CI/CD with GitHub Actions\n\n"
             "Skills\nPython, Go, PostgreSQL, Redis, Docker, Kubernetes, AWS, Terraform, GraphQL")
EX_JD = ("Senior Backend Engineer\n\nAbout the role\nYou will design and run the services behind our payments platform. We are a team of twelve engineers and we ship every day.\n\n"
         "What you will do\n- Build and operate backend services in Python and Go\n- Design PostgreSQL schemas and keep queries fast\n- Run services on Kubernetes on AWS\n"
         "- Work with Kafka event streams\n\nRequirements\n- 5+ years of backend experience\n- Strong Python and PostgreSQL\n- Experience with Kafka and Terraform\n"
         "- Experience with Kubernetes\n\nSalary: $170,000 - $210,000 a year. Remote in the United States.")


def _private(what):
    return f'<p class="note tl-priv"><b>Private</b>{what} What you type is kept only in this browser so the page remembers it; “Clear” erases it.</p>'


NOSCRIPT = '<noscript><p class="banner">This tool runs in your browser and needs JavaScript to be switched on.</p></noscript>'


def _times(k, label, default, cls=""):
    """Half-hour steps of a day; the value is minutes after midnight."""
    opts = [(str(m), f"{m // 60:02d}:{m % 60:02d}", m == default) for m in range(0, 1440, 30)]
    return _sel(k, label, opts, cls=cls, attrs=" data-time")


def _quant(xs, p):
    """Percentile of a sorted list, with linear interpolation (p = 50 gives the same median as build.median)."""
    if len(xs) == 1: return xs[0]
    i = (len(xs) - 1) * p / 100
    lo = int(i); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def _k(v):
    return round(v / 1000)       # whole thousands, rounded the same way as build.money()


def salary_groups(jobs):
    """{"category|level|skill": [postings, median low, median high, value at each QS point]} in $K, for every group of MIN_SAMPLE or more."""
    rows = defaultdict(list)
    for j in jobs:
        if not j.get("usd"): continue
        lo, hi = j["usd"]
        lvl = j.get("level") or "none"
        for cat in ("", j["cat"]):
            if cat == "other": continue                     # the catch-all category is not offered as a choice
            for lv in ("", lvl):
                for sk in [""] + list(j.get("tags") or []):
                    rows[(cat, lv, sk)].append((lo, hi))
    out = {}
    for (cat, lv, sk), v in rows.items():
        if len(v) < MIN_SAMPLE: continue
        mids = sorted((lo + hi) / 2 for lo, hi in v)
        lows, highs = sorted(lo for lo, _ in v), sorted(hi for _, hi in v)
        out[f"{cat}|{lv}|{sk}"] = [len(v), _k(_quant(lows, 50)), _k(_quant(highs, 50))] + [_k(_quant(mids, q)) for q in QS]
    return out


# ---------------------------------------------------------------- the section

def build_tools(page, section, crumbs, e, P, FULL, SITE, V, jobs, CAT):
    """Writes the /tools/ hub and every tool page through page(); returns [(path, name, one_line_description), ...] for linking."""
    today = datetime.date.today()
    DATE = f"{MONTHS[today.month - 1]} {today.day}, {today.year}"
    n_jobs = len(jobs)
    n_paid = sum(1 for j in jobs if j.get("usd"))
    sal_pct = round(100 * sum(bool(j.get("salary")) for j in jobs) / max(n_jobs, 1))      # same figure as SALPCT in build.py
    n_skills = len({t for j in jobs for t in (j.get("tags") or [])})
    contract_path = "contract/" if sum(1 for j in jobs if j.get("etype") == "Contract") >= 8 else "jobs/"   # build.py writes /contract/ under the same condition
    assets = f'<link rel="stylesheet" href="{P}/tools.css?v={V}"><script src="{P}/tools.js?v={V}" defer></script>'
    brand = f" | {SITE}"

    # site pages a tool can point to: path -> (card title, card text)
    SITE_PAGES = {
        "jobs/": ("Open tech jobs", f"{n_jobs:,} roles from company career pages, re-checked every day."),
        "remote/": ("Remote tech jobs", "Open roles listed as remote, with the countries or time zones each one accepts."),
        "salaries/": ("Salaries by role, skill and company", "Median advertised pay from live postings, with the number of roles behind each figure."),
        "resume/": ("Resume builder", "A plain one-column resume that screening software reads cleanly. Saves as PDF, nothing uploaded."),
        "for-you/": ("Jobs for you", "Pick your skills or paste your resume and see the open roles that fit, best matches first."),
        "post-a-job/": ("Post a job", "Put your vacancy in front of people who are searching for tech roles right now."),
        "widgets/": ("Jobs widget and live badges", "Show live tech jobs on your own site with one line of code."),
        "contract/": ("Contract tech jobs", "Open contract roles at tech companies, updated daily."),
    }
    TOOLS = []          # filled below, in the order they appear on the hub

    def tool(slug, group, name, card, title, desc, h1, lead, html, how_title, how, faq, rel, site):
        TOOLS.append(dict(slug=slug, group=group, name=name, card=card, title=title + brand, desc=desc, h1=h1, lead=lead, html=html, how_title=how_title, how=how, faq=faq, rel=rel, site=site))

    def wrap(slug, inner):
        return f'<div class="tl" data-tool="{slug}">{NOSCRIPT}{inner}</div>'

    # ------------------------------------------------------------ 1. resume vs job description
    tool("resume-match", "seekers", "Resume match checker",
         "Paste your resume and a job description: see the match score, the skills you are missing and what to fix.",
         "Resume vs Job Description Match Checker",
         "Paste your resume and a job description to see a match score, the skills and keywords you are missing, and what to fix. Free, runs in your browser.",
         "Check your resume against the job description before you apply",
         "A recruiter searching for “PostgreSQL” does not find a resume that says “databases”, and a quick skim misses whatever is not in the posting’s own words. "
         "Paste your resume and the job description: you get a match score, the skills and repeated terms you are missing, and a short list of fixes. Nothing is uploaded.",
         wrap("resume-match",
              '<div class="card tl-form"><div class="tl-grid wide">'
              + _area("resume", "Your resume (plain text)", 12, "Paste the text of your resume here", cls="", tall=True, ex=EX_RESUME)
              + _area("jd", "The job description", 12, "Paste the full text of the job posting here", cls="", tall=True, ex=EX_JD) + "</div>"
              + '<div class="tl-grid one">' + _f("title", "Job title in the posting (optional)", "Senior Backend Engineer", mode="", hint="We check that your resume uses the same title.") + "</div>"
              + '<div class="tl-actions"><button class="btn" type="button" id="tl-run">Check the match</button>'
                '<button class="btn ghost" type="button" id="tl-import" hidden>Use my resume from the builder</button>' + _clear(True) + "</div></div>"
              + _private(" Both texts are compared inside your browser and are never sent anywhere.")
              + _board("Match score", "Paste your resume and the job description to see how well they match.")
              + '<div class="tl-detail" id="tl-detail"></div>'),
         "How the match score is calculated",
         f"<p><strong>Skills, 60% of the score.</strong> Both texts are searched for the {n_skills} skills this site tracks in job postings: languages, frameworks, cloud platforms and tools. "
         "This part is the share of the posting’s skills that also appear in your resume.</p>"
         "<p><strong>Repeated terms, 40%.</strong> Words and two-word phrases that the posting uses at least twice, once the words every posting uses (“team”, “experience”, “requirements”) are removed. "
         "A term counts by how often it is repeated, up to five times. Word endings are ignored, so “managed” matches “managing”, and “front end” matches “frontend”.</p>"
         "<p>If the posting names none of the tracked skills, the score is the repeated-terms part alone. 75 and above is labelled a strong match, 50 to 74 partial, below 50 weak. "
         "These cut-offs are ours. The score measures keyword overlap; it does not predict whether you get an interview.</p>",
         [("Is my resume uploaded anywhere?",
           "No. Both texts are compared inside your browser and are never sent to a server. They are kept in this browser’s storage so the page remembers them, and the Clear button erases them."),
          ("What match score should I aim for?",
           "Aim to have every skill you really have written in the posting’s own words, rather than to hit a number. The score only counts overlapping skills and repeated terms; 75 or more means most of what the posting stresses is already in your resume."),
          ("Should I add every missing keyword?",
           "No, add only the ones that are true. Listing skills you do not have gets you into interviews you cannot pass. Where you do have the skill, use the posting’s exact word, because a search for “PostgreSQL” does not find “databases”."),
          ("Does this work like an applicant tracking system?",
           "Not exactly. Applicant tracking systems differ, and this tool does not copy any of them. It checks the part you control: whether the skills and terms the posting stresses appear in your resume, so that a keyword search or a quick read finds them.")],
         ["cover-letter", "salary-checker", "negotiation-email"], ["resume/", "for-you/"])

    # ------------------------------------------------------------ 2. salary checker
    groups = salary_groups(jobs)
    cats = [(s, n) for s, n in CAT.items() if s != "other" and f"{s}||" in groups]
    skills = sorted((k.split("|")[2] for k in groups if k.startswith("||") and k != "||"), key=str.lower)
    sal_data = {"q": QS, "min": MIN_SAMPLE, "date": DATE, "g": groups}
    money = lambda k: f"${k:,}K"
    cols = [lv for lv in ("", "Junior", "none", "Senior", "Lead")]
    def cell(cat, lv):
        g = groups.get(f"{cat}|{lv}|")
        return f'<td class="num"><strong>{money(g[10])}</strong> <span class="note">· {g[0]:,}</span></td>' if g else '<td class="num">—</td>'       # g[10] is the median: 3 leading numbers + index of 50 in QS
    assert QS[7] == 50
    sal_rows = "".join(f"<tr><td>{e(name)}</td>" + "".join(cell(slug, lv) for lv in cols) + "</tr>" for slug, name in [("", "All categories")] + cats)
    sal_table = ('<div class="tablewrap"><table><tr><th>Category</th><th>Any level</th><th>Junior</th><th>No level in title</th><th>Senior</th><th>Lead</th></tr>' + sal_rows + "</table></div>"
                 f'<p class="note">Median advertised salary · number of postings counted. A dash means fewer than {MIN_SAMPLE} postings. Yearly, US dollars, as of {DATE}. '
                 f'<a href="{P}/salaries/">Salaries by skill and company</a></p>')
    tool("salary-checker", "seekers", "Tech salary checker",
         "See the median and range of advertised salaries for your category, level and skill, and where your pay sits.",
         "Tech Salary Checker — Is Your Pay Fair?",
         f"Compare your salary with what open tech job postings advertise: median and range by category, level and skill, from {n_paid:,} postings with a published range.",
         "Is your tech salary in line with what companies advertise?",
         f"{100 - sal_pct}% of the {n_jobs:,} open roles here do not state a salary, so it is hard to tell whether your salary or an offer is fair. "
         f"This checker uses the {n_paid:,} postings that do publish a yearly US-dollar range. Pick a category and a level, add a skill if you like, enter your number, and see the median, the typical range and where you sit.",
         wrap("salary-checker",
              '<div class="card tl-form"><div class="tl-grid">'
              + _sel("cat", "Category", [("", "All categories")] + cats)
              + _sel("lvl", "Level", [(v, n_) for v, n_ in LEVELS if not v or f"|{v}|" in groups], hint="Taken from the job title: Senior, Lead, Junior…")
              + _sel("skill", "Skill (optional)", [("", "Any skill")] + [(s, s) for s in skills])
              + _f("pay", "Your yearly salary, USD (optional)", "150,000", hint="Base pay before tax. You can type 150k.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Advertised salaries", "Loading the figures…")
              + '<p class="note tl-priv"><b>Private</b>Your salary is compared inside your browser and is never sent anywhere. Figures are advertised ranges, not verified pay; bonus and equity are not included.</p>'
              + '<script type="application/json" id="tl-data">' + json.dumps(sal_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"),
         "Where the figures come from",
         f"<p>Every figure is calculated from job postings collected from employers’ own careers pages and re-checked daily. On {DATE} there were {n_jobs:,} open roles; "
         f"{n_paid:,} of them publish a yearly salary range in US dollars. Ranges in other currencies and hourly rates are left out so that all figures can be compared.</p>"
         "<p>Each posting counts once, by the midpoint of its range. The <strong>median</strong> is the middle posting; the <strong>middle half</strong> runs from the 25th to the 75th percentile; "
         "“the typical posting advertises” is the median lower end and the median upper end of the ranges. Your position is found by placing your number between 15 percentile points of the group.</p>"
         f"<p>A group needs at least {MIN_SAMPLE} postings. Below that nothing is shown, because a median of a few postings describes those few companies, not the market. "
         "The level comes from the job title; “no level in the title” means the title has no word such as Senior, Lead or Junior.</p>",
         [("Where does the salary data come from?",
           f"From salary ranges that employers publish in their own job postings. On {DATE} we counted {n_paid:,} open tech roles with a yearly US-dollar range, out of {n_jobs:,} open roles. Nothing comes from surveys or from numbers submitted by users."),
          ("Why is there no figure for my selection?",
           f"Because fewer than {MIN_SAMPLE} open postings match it. A median of a handful of postings says more about those few companies than about the market, so the checker shows nothing instead. Remove the skill or choose “Any level” to widen the sample."),
          ("Is the advertised range what people are actually paid?",
           "Not necessarily. A posted range is what the employer says it is prepared to pay for the role; the final offer can land anywhere in it, and bonus and equity come on top. Use the figures as a reference point in a negotiation, not as proof of what colleagues earn."),
          ("Does it cover salaries outside the United States?",
           "Only where the posting gives a yearly range in US dollars. Ranges in other currencies and hourly rates are left out so that every figure is comparable, so the results mostly reflect roles that are paid in dollars.")],
         ["salary-converter", "raise-calculator", "negotiation-email"], ["salaries/"])

    # ------------------------------------------------------------ 3. salary converter
    tool("salary-converter", "seekers", "Salary converter",
         "Turn an hourly, daily, weekly or monthly rate into a yearly salary and back, with your own working hours.",
         "Salary Converter: Hourly to Yearly Pay",
         "Convert pay between hourly, daily, weekly, monthly and yearly figures. Set your own hours per week and paid weeks per year. Free, instant, no sign-up.",
         "Convert an hourly rate to a yearly salary, and back",
         "One posting says $55 an hour, another $95,000 a year, and a recruiter quotes a day rate. You cannot compare them until they are in the same unit. "
         "Enter any one figure and your working hours: you get the hourly, daily, weekly, monthly and yearly equivalents at once.",
         wrap("salary-converter",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("amount", "Amount", "55")
              + _sel("period", "Paid per", [("hour", "Hour", True), ("day", "Day"), ("week", "Week"), ("month", "Month"), ("year", "Year")])
              + _cur() + '</div><div class="tl-grid c2">'
              + _f("hours", "Hours per week", val="40") + _f("days", "Days per week", val="5")
              + _f("weeks", "Paid weeks per year", val="52", hint="52 with paid leave. Contractors: the weeks you bill.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Your pay in every unit", "Enter an amount to see it per hour, day, week, month and year.")),
         "How the conversion is calculated",
         "<p>Everything goes through the yearly figure:</p><ul>"
         "<li><code>yearly = hourly × hours per week × paid weeks per year</code>. With 40 hours and 52 weeks that is 2,080 paid hours.</li>"
         "<li><code>weekly = yearly ÷ paid weeks</code>, <code>daily = weekly ÷ days per week</code>, <code>hourly = weekly ÷ hours per week</code>.</li>"
         "<li><code>monthly = yearly ÷ 12</code>, an average month.</li></ul>"
         "<p>All figures are before tax. For an employee with paid leave, leave “paid weeks” at 52: holidays are paid, so they are already inside the salary. "
         "For contract work, enter the number of weeks you expect to bill.</p>",
         [("How do I convert an hourly rate to a yearly salary?",
           "Multiply the hourly rate by the hours you work in a week and by the weeks you are paid in a year. At 40 hours and 52 weeks that is the hourly rate times 2,080, so $50 an hour is $104,000 a year."),
          ("How many working hours are there in a year?",
           "2,080 if you count 40 hours a week for 52 weeks. A 37.5-hour week gives 1,950 hours and a 35-hour week 1,820. For a salaried employee, paid holidays are already inside these figures."),
          ("Why is a contractor’s hourly rate higher than an employee’s?",
           "Because a contractor is paid only for the hours billed. Holidays, sick days, gaps between contracts, equipment and employer-side taxes all come out of the rate. Lower “paid weeks per year” to see what a rate adds up to, or use the contractor rate calculator."),
          ("Is the result before or after tax?",
           "Before tax. The converter only changes the unit of time. Tax depends on the country, the state and your personal situation, so it is not estimated here.")],
         ["raise-calculator", "contractor-rate", "compare-offers"], ["salaries/"])

    # ------------------------------------------------------------ 4. raise calculator
    tool("raise-calculator", "seekers", "Pay raise calculator",
         "Percent to amount and back, the new salary, the change in each paycheck, and the raise after inflation.",
         "Pay Raise Calculator: Percent to New Salary",
         "Work out a pay raise: percent, amount and new salary, plus the change in each paycheck and the raise after inflation. Free calculator, no sign-up.",
         "Work out what a pay raise is really worth",
         "“A 4% raise” sounds fine until you see what it adds to each paycheck, or notice that prices rose faster. "
         "Enter your current salary and one of three things: the percent, the amount or the new salary. You get the other two, the change per paycheck, and the raise after inflation if you add it.",
         wrap("raise-calculator",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("current", "Current yearly salary", "60,000") + _cur() + "</div>"
              + '<p class="tl-t">The raise: fill in any one, the other two follow</p><div class="tl-grid c2">'
              + _f("pct", "Raise, %", "5") + _f("amount", "Raise, amount per year", "3,000") + _f("next", "New yearly salary", "63,000") + "</div>"
              + '<input type="hidden" data-k="by" value="pct">'
              + '<div class="tl-grid">'
              + _sel("freq", "Paychecks", [("12", "Monthly (12 a year)", True), ("24", "Twice a month (24)"), ("26", "Every two weeks (26)"), ("52", "Weekly (52)")])
              + _f("infl", "Inflation since your last raise, % (optional)", "3.2", hint="Your country’s published consumer price change for the period.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Your raise", "Enter your current yearly salary, then the raise as a percent, an amount or the new salary.")),
         "How the raise is calculated",
         "<ul><li><code>amount = current salary × percent ÷ 100</code></li>"
         "<li><code>percent = (new salary − current salary) ÷ current salary × 100</code>, shown to two decimal places</li>"
         "<li><code>per paycheck = yearly salary ÷ paychecks a year</code> (12, 24, 26 or 52)</li>"
         "<li><code>real raise = (1 + raise) ÷ (1 + inflation) − 1</code>: what the raise is worth once prices have moved</li></ul>"
         "<p>All figures are before tax and deductions. The inflation figure is yours to enter, from your country’s statistics office, for the time since your pay last changed.</p>",
         [("How do I calculate a raise as a percentage?",
           "Subtract the old salary from the new one, divide by the old salary and multiply by 100. From $72,000 to $80,000 is $8,000 ÷ $72,000 × 100 = 11.11%."),
          ("How much is a 5% raise?",
           "It is your current salary multiplied by 0.05. On $60,000 a 5% raise is $3,000 a year, which is $250 a month, or about $115 on a paycheck every two weeks, before tax."),
          ("What is a real raise after inflation?",
           "It is the raise measured in what your pay can buy. Divide (1 + raise) by (1 + inflation) and subtract 1. A 3% raise while prices rose 4% is a real change of −0.96%: a pay cut in buying power."),
          ("Is the per-paycheck figure what I will take home?",
           "No, it is before tax. Take-home pay depends on tax, pension and other deductions, which differ by country and by person, so the calculator shows gross figures only.")],
         ["salary-checker", "negotiation-email", "salary-converter"], ["salaries/"])

    # ------------------------------------------------------------ 5. offer comparison
    # the placeholders double as the example, so each offer gets its own figures: a comparison of two equal offers shows nothing
    OFFER_EX = {"a": ("120,000", "10% or 12,000", "20,000", "10,000", "4", "3,000", "25", "3", "18"),
                "b": ("135,000", "5% or 6,750", "8,000", "5,000", "3", "2,000", "20", "0", "0"),
                "c": ("110,000", "15% or 16,500", "40,000", "20,000", "6", "4,000", "30", "5", "22")}

    def offer_col(p, letter, hidden=False):
        base, bonus, eq, sign, match, other, pto, cdays, ccost = OFFER_EX[p]
        return (f'<div class="tl-col" id="tl-col-{p}"{" hidden" if hidden else ""}><p class="tl-t">Offer {letter}</p>'
                + _f(f"{p}_name", "Company", f"Offer {letter}", mode="")
                + _f(f"{p}_base", "Base salary per year", base)
                + _f(f"{p}_bonus", "Bonus per year", bonus, mode="text", hint="An amount, or a percent of base.")
                + _f(f"{p}_equity", "Equity vesting per year", eq, hint="Your own estimate of its value.")
                + _f(f"{p}_signon", "Sign-on bonus (paid once)", sign)
                + _f(f"{p}_match", "Retirement match, % of base", match)
                + _f(f"{p}_other", "Other benefits per year", other, hint="Health cover, stipends, meals.")
                + _f(f"{p}_pto", "Paid days off per year", pto, hint="Vacation plus public holidays.")
                + _f(f"{p}_cdays", "Commute days per week", cdays)
                + _f(f"{p}_ccost", "Cost per commute day", ccost) + "</div>")
    tool("compare-offers", "seekers", "Job offer comparison",
         "Put two or three offers side by side: base, bonus, equity, sign-on, benefits, days off and commute.",
         "Job Offer Comparison Calculator (2–3 Offers)",
         "Compare two or three job offers side by side: base, bonus, equity, sign-on, retirement match, days off and commute, as one yearly value. Free, private.",
         "Compare job offers by what they are worth in a year",
         "The offer with the highest base salary is not always the one that pays most. Bonus, equity, a retirement match, extra days off and a daily commute can change which offer comes out on top. "
         "Enter two or three offers and see them side by side: yearly value, first-year value with the sign-on bonus, and pay per day you actually work.",
         wrap("compare-offers",
              '<div class="card tl-form"><div class="tl-grid one">' + _cur() + '</div><input type="hidden" data-k="n" value="2">'
              + '<div class="tl-cols">' + offer_col("a", "A") + offer_col("b", "B") + offer_col("c", "C", True) + "</div>"
              + '<div class="tl-actions"><button class="btn ghost" type="button" id="tl-add">+ Add a third offer</button>' + _clear(True) + "</div></div>"
              + _private(" The figures of your offers are added up inside your browser and are never sent anywhere.")
              + _board("Yearly value", "Enter the base salary of each offer. Add bonus, equity and benefits where you know them; leave the rest empty.")
              + '<div class="tl-detail" id="tl-table"></div>'),
         "How the offers are compared",
         "<ul><li><code>yearly value = base + bonus + equity vesting per year + retirement match + other benefits − commute cost</code></li>"
         "<li><code>first-year value = yearly value + sign-on bonus</code>, because the sign-on bonus is paid once</li>"
         "<li><code>days worked = 260 − paid days off</code> (52 weeks of 5 days)</li>"
         "<li><code>commute cost = commute days per week × cost per day × days worked ÷ 5</code></li>"
         "<li><code>value per day worked = yearly value ÷ days worked</code>: more leave at the same salary shows up here</li></ul>"
         "<p>A bonus typed as “10%” is taken as a percent of base. Everything is before tax. Equity is counted at the value you enter: for a private company that is an estimate, not cash.</p>",
         [("How do I compare two job offers?",
           "Put everything on a yearly basis and add it up: base salary, expected bonus, the equity that vests in a year, the employer’s retirement contribution and other benefits, minus what the commute costs. Then weigh what is not money: the work, the manager, the room to grow."),
          ("How should I value equity in an offer?",
           "Use what vests in one year, at a value you can defend. For a listed company that is shares per year times the share price. For a startup the value is uncertain and the shares cannot be sold freely, so compare the offers both with the equity and with it set to zero."),
          ("Does a sign-on bonus count toward the yearly value?",
           "No. It is paid once, so it is shown on its own line and added only to the first-year value. An offer that wins only because of its sign-on bonus pays less from the second year on."),
          ("How are paid days off taken into account?",
           "They change the pay per day you actually work. The calculator starts from 260 working days a year, subtracts your paid days off and divides the yearly value by the rest, so more leave at the same salary shows up as a higher value per day worked.")],
         ["equity-calculator", "salary-checker", "negotiation-email"], ["jobs/"])

    # ------------------------------------------------------------ 6. stock options
    tool("equity-calculator", "seekers", "Stock options calculator",
         "What startup options are worth on paper today, what has vested, and what an exit could pay after dilution.",
         "Stock Options Calculator for Startup Equity",
         "Estimate what startup stock options are worth: paper value today, vesting, exercise cost and exit scenarios after dilution. Estimates, not financial advice.",
         "See what your startup stock options could be worth",
         "“20,000 options” in an offer letter means nothing until you know the strike price, the share price and how much of the company that is. "
         "Enter the numbers from your offer to see the paper value today, how much has vested, what it costs to exercise, and what you would get at different exit sizes after dilution. "
         "These are estimates before tax, not financial advice.",
         wrap("equity-calculator",
              '<div class="card tl-form"><p class="tl-t">Your grant</p><div class="tl-grid">'
              + _f("options", "Number of options", "20,000") + _f("strike", "Strike price per share", "1.50", hint="What you pay to turn one option into a share.") + _cur() + "</div>"
              + '<p class="tl-t">The company today</p><div class="tl-grid">'
              + _sel("mode", "What you know", [("price", "The latest price per share", True), ("valuation", "The company valuation")])
              + _f("price", "Latest price per share", "6.00", hint="What investors paid in the last round, or the latest fair market value.", show=' data-show="price"')
              + _f("valuation", "Company valuation", "120m", hint="Post-money valuation of the last round. You can type 120m.", show=' data-show="valuation"')
              + _f("fd", "Fully diluted shares", "20,000,000", hint="All shares, options and convertibles together. Needed with a valuation; optional with a price.") + "</div>"
              + '<p class="tl-t">Vesting</p><div class="tl-grid c2">'
              + _f("vestYears", "Vesting period, years", val="4") + _f("cliff", "Cliff, months", val="12") + _f("monthsIn", "Months served (optional)", "18", hint="Since vesting began.") + "</div>"
              + '<p class="tl-t">Before an exit</p><div class="tl-grid c2">'
              + _f("rounds", "Funding rounds still to come", "2") + _f("dilution", "Dilution per round, %", "20", hint="The share of the company sold in each new round.") + "</div>"
              + '<p class="tl-t">Exit scenarios: the company is sold or listed at … times today’s value</p><div class="tl-grid c2">'
              + _f("m1", "Scenario 1, ×", val="1") + _f("m2", "Scenario 2, ×", val="3") + _f("m3", "Scenario 3, ×", val="10") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Paper value today", "Enter the number of options, the strike price and the latest price per share.")
              + '<div class="tl-detail" id="tl-table"></div>'
              + '<p class="note tl-priv"><b>Estimate</b>Arithmetic on the numbers you enter, before tax. Not financial, legal or tax advice. Many startups never reach an exit, and then options pay nothing. Nothing you type leaves your browser.</p>'),
         "How the option value is calculated",
         "<ul><li><code>price per share = valuation ÷ fully diluted shares</code>, when you start from a valuation</li>"
         "<li><code>paper value today = options × (price per share − strike price)</code>, never below zero</li>"
         "<li><code>cost to exercise = options × strike price</code></li>"
         "<li><code>your stake = options ÷ fully diluted shares</code></li>"
         "<li><code>vested = options × months served ÷ months of vesting</code>, rounded down, and zero before the cliff</li>"
         "<li><code>share kept after dilution = (1 − dilution per round) ^ rounds</code></li>"
         "<li><code>exit price per share = today’s price × exit multiple × share kept</code>, and your options are then worth <code>options × (exit price − strike)</code></li></ul>"
         "<p>The exit multiples are scenarios you choose, not forecasts. Tax is not included. Liquidation preferences, which pay investors back first, are not modelled; they matter most when a company sells for little more than it raised.</p>",
         [("How do I work out what my stock options are worth?",
           "Multiply the number of options by the difference between the share price and your strike price. 10,000 options with a $1 strike and a $5 share price are worth 10,000 × ($5 − $1) = $40,000 on paper, before tax and before any future dilution."),
          ("What is a strike price?",
           "It is the fixed price you pay to turn one option into one share. If the shares are later worth more than the strike, the difference is your gain. If they are worth less, the option is not worth exercising."),
          ("How does dilution affect my options?",
           "Each time the company issues new shares, every existing share becomes a smaller slice of the company. If a funding round sells 20% of the company, you keep 80% of your stake; after two such rounds you keep 64%. The number of options you hold does not change, but each share gets a smaller part of any exit price."),
          ("What does “fully diluted” mean?",
           "It is the total number of shares that would exist if every option, warrant and convertible note were turned into shares. Your options divided by the fully diluted share count is the part of the company you would own."),
          ("Is this financial or tax advice?",
           "No. It is arithmetic on the numbers you enter. It leaves out tax, liquidation preferences and the chance that the company never has an exit, so treat the results as rough estimates and speak to a qualified adviser before you exercise options.")],
         ["compare-offers", "negotiation-email", "salary-checker"], ["jobs/"])

    # ------------------------------------------------------------ 7. time zones
    def zone(i, name, start=540, end=1020, hidden=False):
        rm = f'<button class="linkbtn tl-x" type="button" data-rm="{i}">Remove</button>' if i > 2 else '<span class="tl-x"></span>'
        return (f'<div class="tl-zone" data-row="{i}"{" hidden" if hidden else ""}>'
                + _f(f"z{i}_name", "Who", val=name, mode="", cls="z-name")
                + _sel(f"z{i}_tz", "Time zone", [("UTC", "UTC")], cls="z-tz", attrs=" data-tz")
                + _times(f"z{i}_start", "Starts", start) + _times(f"z{i}_end", "Ends", end) + rm + "</div>")
    tool("time-zone-overlap", "seekers", "Time zone overlap",
         "See the working hours you share with a remote team on a 24-hour bar, in everyone’s local time.",
         "Time Zone Overlap Calculator for Remote Teams",
         "Find the working hours you share with a remote team. Pick up to four time zones, set each working day and see the overlap on a 24-hour bar. Free.",
         "Find the working hours you share with a remote team",
         "A remote job that looks perfect can turn out to mean calls at eleven at night. Before you apply, or before you set a meeting, check how many working hours you really share. "
         "Pick your time zone and theirs, set each working day, and see the overlap on a 24-hour bar, in everyone’s local time.",
         wrap("time-zone-overlap",
              '<div class="card tl-form">' + zone(1, "You") + zone(2, "Team") + zone(3, "Person 3", hidden=True) + zone(4, "Person 4", hidden=True)
              + '<input type="hidden" data-k="n" value="2"><div class="tl-grid">'
              + _f("date", "Date (optional)", typ="date", mode="", hint="Offsets change with daylight saving. Empty means today.")
              + _sel("clock", "Clock", [("24", "24-hour", True), ("12", "12-hour (am / pm)")]) + "</div>"
              + '<div class="tl-actions"><button class="btn ghost" type="button" id="tl-add">+ Add a time zone</button>' + _clear() + "</div></div>"
              + _board("Shared working time", "Pick two time zones and working hours to see the overlap.")
              + '<div class="tl-detail"><div class="card" id="tl-day"></div><div id="tl-table"></div></div>'),
         "How the overlap is calculated",
         "<p>Each working day is converted to UTC with the zone’s offset on the chosen date, read from the time zone database built into your browser. That covers daylight saving time and zones with half-hour or "
         "45-minute offsets, such as India (UTC+5:30) and Nepal (UTC+5:45).</p>"
         "<p>The shared time is the part of the 24-hour day that lies inside every working day at once. A working day that ends before it starts is treated as a night shift running past midnight, "
         "and an overlap that crosses midnight is shown as one stretch. The bar is drawn in the first person’s local time; the table gives the same hours in each person’s own time.</p>",
         [("How do I find overlapping working hours between two time zones?",
           "Convert both working days to the same clock and take the part they share. For example, 9:00–17:00 in Berlin and 9:00–17:00 in New York overlap from 15:00 to 17:00 Berlin time, which is 9:00 to 11:00 in New York, while the two cities are six hours apart."),
          ("Does the calculator handle daylight saving time?",
           "Yes. Offsets are read from your browser’s time zone database for the date you choose, so a date in July and a date in January can give different answers. Check again around the clock changes in spring and autumn, when two places can switch on different days."),
          ("What about time zones with half-hour offsets?",
           "They work the same way. India is 5 hours 30 minutes ahead of UTC and Nepal 5 hours 45 minutes, and the overlap is calculated to the minute."),
          ("How many shared hours does a remote team need?",
           "There is no fixed number: it depends on how much of the work is live conversation. Use the result to see what a job would mean for your day, which meetings would fall early or late, and whether that suits you before you apply.")],
         ["compare-offers", "salary-converter", "cover-letter"], ["remote/"])

    # ------------------------------------------------------------ 8. cover letter
    paper = lambda name, extra="": (
        '<div class="tl-side"><div class="tl-actions tl-noprint"><button class="btn" type="button" data-copy="tl-paper">Copy</button>'
        f'<button class="btn ghost" type="button" data-dl="tl-paper" data-name="{name}">Download .txt</button>{extra}</div>'
        '<div class="tl-paper" id="tl-paper"></div><p class="note tl-noprint" id="tl-count" role="status" aria-live="polite"></p></div>')
    tool("cover-letter", "seekers", "Cover letter builder",
         "Fill in a few facts, pick a tone, get a clean letter to edit. Copy, download or print. A template, not AI.",
         "Cover Letter Builder — Free, No Sign-Up",
         "Build a short, clear cover letter from a few facts about you and the job. Three tones; copy, download or print. Template-based, private, no sign-up.",
         "Write a cover letter without staring at a blank page",
         "The empty page is the slowest part of applying. Fill in a few facts about the job and about you, pick a tone, and you have a short, clean letter to edit. "
         "It is a fill-in template, not AI: every sentence is built from what you type, so nothing is invented for you. Nothing is uploaded.",
         wrap("cover-letter",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _f("title", "Job title you are applying for", "Senior Backend Engineer", mode="")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("manager", "Hiring manager’s name (optional)", "Dana Lee", mode="")
              + _f("source", "Where you saw the job (optional)", SITE, mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("current", "Your current or latest job title", "backend engineer", mode="")
              + _f("years", "Years of experience", "8", mode="text")
              + _f("skills", "Your 2–4 strongest skills", "Python, PostgreSQL, Kafka", mode="", hint="Separate them with commas.")
              + _area("achievement", "One result you are proud of", 2, "I cut page load time from 4 s to 1.2 s for two million monthly users.", hint="A full sentence starting with “I”, with a number if you have one.")
              + _area("why", "Why this company", 2, "Your API is the one my team chose after testing four.", hint="One full sentence that could not be said about any other employer.")
              + _f("contact", "Email or phone (optional)", "alex@example.com", mode="", auto="email", hint="Goes into the closing line.")
              + _sel("tone", "Tone", [("direct", "Direct", True), ("warm", "Warm"), ("formal", "Formal")]) + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>"
              + _private(" The letter is assembled inside your browser and is never sent anywhere.") + "</div>"
              + paper("cover-letter.txt", '<button class="btn ghost" type="button" data-print>Print</button>') + "</div>"),
         "How the letter is put together",
         "<p>The letter has up to six short parts: a greeting, the job you are applying for, who you are, one result, why this company, and a closing line with your contact details. "
         "Each part is built from one or two fields. A field you leave empty drops its sentence, and the three things a letter cannot do without (job title, company, your name) appear in [brackets] until you fill them in.</p>"
         "<p>The tone changes the wording, never the facts: “direct” is plain and brief, “warm” is friendlier, “formal” suits banks, law firms and the public sector. "
         "No AI is involved and nothing is generated: what you read is what you typed, arranged. Treat it as a first draft and change any sentence that does not sound like you.</p>",
         [("Is this cover letter written by AI?",
           "No. It is a fill-in template: every sentence is assembled from the fields you complete, in the tone you choose. Nothing is generated, guessed or sent to a server, so the letter contains only facts you typed."),
          ("How long should a cover letter be?",
           "Short: three to five brief paragraphs that fit on one page. The builder shows a word count under the letter and tells you when your answers make it run long."),
          ("What should a cover letter say that a resume does not?",
           "Why this job and this company, and one concrete result that shows you can do the work. The resume lists what you did; the letter connects it to what this employer needs."),
          ("Do I need a different cover letter for every job?",
           "Yes, at least the opening and the reason for choosing the company. Your details stay saved in this browser, so for the next application you change only the job title, the company and the “why” sentence.")],
         ["resume-match", "negotiation-email", "salary-checker"], ["resume/"])

    # ------------------------------------------------------------ 9. negotiation email
    both = ' data-for="counter raise"'
    tool("negotiation-email", "seekers", "Negotiation email writer",
         "A polite, specific email to counter an offer, ask for a raise or ask for more time. A template, not AI.",
         "Salary Negotiation Email Template Builder",
         "Write a salary negotiation or counter-offer email from a few fields: the offer, your figure and your reasons. Three tones. Template-based, private, free.",
         "Write the salary negotiation email you keep putting off",
         "Asking for more money feels awkward, so the reply sits in drafts while the deadline gets closer. Pick the situation, enter the offer and the figure you want, add your reasons, "
         "and you get a polite, specific email to send. It is a fill-in template, not AI: the facts and the final wording are yours.",
         wrap("negotiation-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("scenario", "Situation", [("counter", "Counter a job offer", True), ("raise", "Ask for a raise"), ("time", "Ask for more time to decide")])
              + _sel("tone", "Tone", [("collaborative", "Collaborative", True), ("firm", "Firm"), ("brief", "Brief")])
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("to", "Recipient’s first name", "Dana", mode="")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("title", "Job title", "Staff Engineer", mode="")
              + _f("offer", "Salary they offered", "150,000", show=both, lid="tl-offer-l")
              + _f("target", "Salary you want", "165,000", show=both)
              + _sel("cur", "Currency", [("$", "$ dollar"), ("€", "€ euro"), ("£", "£ pound"), ("₹", "₹ rupee"), ("", "No symbol")], show=both)
              + _f("deadline", "Date you will answer by (optional)", "Friday, 20 November", mode="", lid="tl-date-l")
              + _area("reasons", "Your reasons, one per line", 4, "I led the payments rewrite that cut failed charges by 30%\nSimilar roles are advertised at $160K to $185K\nI have another offer at $170K",
                      hint="Results you delivered, the scope of the role, pay data, another offer. Up to five lines.", show=both) + "</div>"
              + f'<p class="tl-t"{both}>If the salary cannot move, I am open to</p><div class="tl-checks"{both}>'
              + _check("x_signon", "A sign-on bonus", show=' data-for="counter"') + _check("x_once", "A one-time bonus", show=' data-for="raise"')
              + _check("x_equity", "Additional equity") + _check("x_pto", "Extra paid days off") + _check("x_remote", "More remote days")
              + _check("x_review", "An earlier salary review") + _check("x_start", "A later start date", show=' data-for="counter"') + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>"
              + _private(" The email is assembled inside your browser and is never sent anywhere.") + "</div>"
              + paper("negotiation-email.txt") + "</div>"),
         "How the email is put together",
         "<p>Each email follows the same order: thanks and a clear sign that you want the job, the one thing you would like to change with the exact figure, your reasons as a short list, "
         "an alternative if the salary cannot move, and a direct question that is easy to answer. The first line of the output is the subject.</p>"
         "<p>“Collaborative” looks for a way to say yes, “firm” states the figure you would sign at, “brief” says it in a few sentences. If you give no reasons, a line in [brackets] reminds you to add them. "
         "The tool does not suggest a figure: it uses the two numbers you enter and shows the difference in percent under the email. No AI is involved, and nothing is sent anywhere.</p>",
         [("How do I counter a job offer by email?",
           "Thank them, say you want the job, name the one thing you would like to change and the exact figure, give one or two reasons, and end with a direct question. Keep it short and send it to the person who made the offer."),
          ("How much more can I ask for?",
           "Ask for a figure you can back with evidence: what similar roles advertise, another offer, or the scope of the job. This tool does not pick a number for you; the salary checker shows what open postings advertise for your category and level."),
          ("Is it risky to negotiate a job offer?",
           "A polite, reasoned request is a normal part of hiring, and these templates keep the tone respectful. No tool can promise how a particular employer will react, so decide beforehand which figure you would accept."),
          ("Should I negotiate by email or on a call?",
           "Email gives you time to choose your words and leaves a written record; a call is quicker and warmer. You can do both: the collaborative template states your figure in writing and offers to talk it through on a call.")],
         ["salary-checker", "raise-calculator", "compare-offers"], ["salaries/"])

    # ------------------------------------------------------------ 13. contractor rate (added: fits the board's contract roles)
    tool("contractor-rate", "seekers", "Contractor rate calculator",
         "The day and hourly rate a contractor must charge to match a salary, after days off, unbilled time and costs.",
         "Contractor Rate Calculator: Salary to Day Rate",
         "Work out the day rate and hourly rate you need as a contractor or freelancer to match a salary, after days off, unbilled time and your own costs. Free.",
         "Work out the contract rate that really matches a salary",
         "Divide a salary by 2,080 hours and you get a rate that leaves a contractor worse off than the employee: nobody pays for your holidays, your sick days, the weeks between contracts "
         "or the hours spent finding work. Enter the income you want, your days off, the share of time you can bill and the costs an employer used to cover. You get the day rate and the hourly rate to quote.",
         wrap("contractor-rate",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("income", "Yearly income you want, before tax", "100,000", hint="For example the salary of a comparable job.") + _cur()
              + _f("overhead", "Costs an employer would cover, % of income", "25", hint="Payroll taxes, health cover, pension. Your own figure.")
              + _f("costs", "Business costs per year", "5,000", hint="Equipment, software, accountant, insurance.") + '</div><div class="tl-grid c2">'
              + _f("daysOff", "Days off per year", "35", hint="Vacation, public holidays, sick days.")
              + _f("billable", "Working time you can bill, %", "80", hint="The rest goes on finding work and admin. Empty means 100.")
              + _f("hours", "Hours per billable day", val="8") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Rate you need to charge", "Enter the yearly income you want to end up with, before tax.")),
         "How the rate is calculated",
         "<ul><li><code>yearly invoices = income × (1 + employer-side costs %) + business costs</code></li>"
         "<li><code>days worked = 260 − days off</code> (52 weeks of 5 days)</li>"
         "<li><code>billable days = days worked × billable share</code></li>"
         "<li><code>day rate = yearly invoices ÷ billable days</code>, <code>hourly rate = day rate ÷ hours per day</code></li></ul>"
         "<p>The comparison with a salaried job divides the same income by 2,080 paid hours (40 hours × 52 weeks). All figures are before income tax and before any sales tax or VAT. "
         "The percentages are yours to enter, because employer-side costs differ from country to country.</p>",
         [("How do I turn a salary into a contractor day rate?",
           "Add the costs an employer would have covered to the salary, then divide by the days you can actually bill. With a target of $100,000, 25% for employer-side costs, $5,000 of business costs, 35 days off and 80% of working days billed, that is $130,000 ÷ 180 days, about $722 a day."),
          ("How many billable days are there in a year?",
           "Start from 260 weekdays, subtract public holidays, vacation and sick days, then multiply by the share of time you can bill. 260 minus 35 days off is 225 working days; if 80% of them are billable, that is 180 days."),
          ("What extra costs does a contractor pay?",
           "Whatever an employer paid on top of your salary: its share of social security or payroll taxes, health insurance, pension contributions, paid leave, equipment and software. The amounts differ by country, so the calculator asks for your own percentage instead of assuming one."),
          ("Is the result before or after tax?",
           "Before tax. It is the amount to invoice. Income tax and any sales tax or VAT depend on where you live and how your business is set up.")],
         ["salary-converter", "salary-checker", "negotiation-email"], [contract_path])

    # ------------------------------------------------------------ 10. job description checker
    tool("job-description-checker", "employers", "Job description checker",
         "Score a posting for length, missing salary, must-have overload, biased wording, jargon and readability.",
         "Job Description Checker: Bias & Clarity Score",
         "Paste a job description and get a score with fixes: missing salary, too many must-haves, gender-coded and exclusionary words, jargon, readability. Free.",
         "Find what is putting candidates off your job description",
         f"A posting with no salary, fifteen “requirements” and a wall of jargon gets skipped by the people you want to hear from. {100 - sal_pct}% of the {n_jobs:,} open tech roles we track do not state a salary. "
         "Paste your text and the checker scores it and lists what to fix: length, missing salary, must-have overload, gender-coded and exclusionary wording, jargon and readability. The text stays in your browser.",
         wrap("job-description-checker",
              '<div class="card tl-form">'
              + _area("text", "Job description", 14, "Paste the full text of your job posting here, with its headings and bullet points", tall=True, ex=EX_JD)
              + '<div class="tl-actions"><button class="btn" type="button" id="tl-run">Check the description</button>' + _clear(True) + "</div></div>"
              + _private(" The text is checked inside your browser and is never sent anywhere.")
              + _board("Job description score", "Paste a job description to see its score and what to fix.")
              + '<div class="tl-detail" id="tl-detail"></div>'),
         "How the score is calculated",
         "<p>Every posting starts at 100 and loses points for each problem found:</p><ul>"
         "<li><strong>Salary</strong>: no pay figure −20; one figure without a range −6. A figure counts as pay when it stands next to a word such as salary, compensation or “per hour”, and is not a budget, bonus or revenue number.</li>"
         "<li><strong>Length</strong>: under 150 words −15; 150 to 299 −5; 901 to 1,300 −8; over 1,300 −12.</li>"
         "<li><strong>Must-haves</strong>: bullet points under a requirements or qualifications heading. More than 8 costs 8 points, more than 12 costs 14; no requirements at all −5.</li>"
         "<li><strong>Exclusionary terms</strong> such as “ninja”, “digital native” or “native speaker”: −5 each, up to −15.</li>"
         "<li><strong>Gender-coded wording</strong>: −6 when masculine-coded words outnumber feminine-coded ones by two or more.</li>"
         "<li><strong>Buzzwords</strong>: −2 each, up to −10.</li>"
         "<li><strong>Missing information</strong>: where the work happens −6, benefits −5, hiring steps −4.</li>"
         "<li><strong>Readability</strong>: two or more sentences over 30 words −6; Flesch–Kincaid grade above 13 −4; a request for 8 or more years of experience −3.</li>"
         "<li><strong>Point of view</strong>: “we / our” used six times or more, and over one and a half times as often as “you / your”, −3.</li></ul>"
         "<p>85 and above is labelled ready to post, 65 to 84 good with a few fixes, below 65 needs work.</p>"
         "<p>The weights and thresholds are our own rules of thumb, not an industry standard. The gender-coded word list is a short one in the spirit of the research by Gaucher, Friesen and Kay (2011) on gendered wording in job adverts; "
         "readability uses the public Flesch formulas, with each bullet point counted as a sentence.</p>",
         [("What makes a good job description?",
           "One that lets the right person decide quickly: what they will do, what they must already be able to do, what it pays, where the work happens and what the hiring steps are. Everything else can live on the careers page."),
          ("Should a job description include the salary?",
           f"Yes, if you want candidates to be able to tell whether the role fits them. Of the {n_jobs:,} open tech roles we track, {sal_pct}% state what they pay" + (", so a posting with a clear range also stands out from most of the others." if sal_pct < 40 else ", and candidates who filter by salary never see the rest.")),
          ("What is gender-coded language in a job posting?",
           "Words that readers tend to associate more with men (“competitive”, “dominant”) or more with women (“supportive”, “collaborative”). Research by Gaucher, Friesen and Kay (2011) found that adverts loaded with masculine-coded words appealed less to women. The checker counts both kinds from a short word list and tells you which way the text leans."),
          ("How many requirements should a job posting list?",
           "As few as are truly required. The checker starts to warn above eight must-haves and flags more than twelve. These thresholds are our rule of thumb: a long list reads as a reason not to apply."),
          ("Is the text I paste stored or sent anywhere?",
           "No. The check runs in your browser. The text is kept only in this browser’s storage so the page remembers it, and the Clear button erases it.")],
         ["jobposting-schema", "boolean-search", "salary-checker"], ["post-a-job/"])

    # ------------------------------------------------------------ 11. JobPosting structured data
    onsite, remote = ' data-show="onsite"', ' data-show="remote"'
    etypes = [("FULL_TIME", "Full-time"), ("PART_TIME", "Part-time"), ("CONTRACTOR", "Contractor"), ("TEMPORARY", "Temporary"), ("INTERN", "Intern"), ("VOLUNTEER", "Volunteer"), ("PER_DIEM", "Per diem"), ("OTHER", "Other")]
    tool("jobposting-schema", "employers", "JobPosting schema generator",
         "Fill in a form and get valid JobPosting JSON-LD for Google’s job search, with required fields checked.",
         "JobPosting Schema Generator (JSON-LD)",
         "Generate JobPosting structured data (JSON-LD) for Google for Jobs from a simple form. Required and recommended fields are checked as you type. Free.",
         "Generate JobPosting structured data for Google for Jobs",
         "A vacancy without valid JobPosting markup is not eligible for the job search experience on Google, and one missing required field is enough to be left out. "
         "Fill in the form: you get JSON-LD to paste into the job page, with every required and recommended field checked as you type.",
         wrap("jobposting-schema",
              '<div class="card tl-form"><p class="tl-t">The job</p><div class="tl-grid">'
              + _f("title", "Job title", "Senior Backend Engineer", mode="", hint="The title only: no pay, codes or “apply now”.")
              + _f("posted", "Date posted", typ="date", mode="") + _f("through", "Last day to apply", typ="date", mode="")
              + _f("ident", "Your reference number", "ENG-2041", mode="")
              + _sel("direct", "Can people apply on your page?", [("", "Not stated"), ("true", "Yes, without leaving the page"), ("false", "No, they are sent elsewhere")])
              + _area("desc", "Full job description", 8, "What the person will do, what they need, working hours…", hint="Plain text is turned into HTML: a blank line starts a paragraph, a line starting with - becomes a bullet point.") + "</div>"
              + '<p class="tl-t">Employment type</p><div class="tl-checks">' + "".join(_check(f"et_{v}", t, v == "FULL_TIME") for v, t in etypes) + "</div>"
              + '<p class="tl-t">The employer</p><div class="tl-grid">'
              + _f("org", "Company name", "Acme GmbH", mode="", auto="organization", hint="The company that is hiring, not the agency.")
              + _f("orgurl", "Company website", "https://acme.example", mode="url", typ="url") + _f("logo", "Logo image address", "https://acme.example/logo.png", mode="url", typ="url") + "</div>"
              + '<p class="tl-t">Where the work happens</p><div class="tl-grid">'
              + _sel("loc", "Workplace", [("onsite", "On site or hybrid: there is a workplace", True), ("remote", "Fully remote")])
              + _f("street", "Street address", "1 Main Street", mode="", show=onsite) + _f("city", "City", "Berlin", mode="", show=onsite)
              + _f("region", "State or region", "BE", mode="", show=onsite) + _f("postal", "Postal code", "10115", mode="", show=onsite)
              + _f("country", "Country", "DE", mode="", show=onsite, hint="Two-letter code or the name.")
              + _f("remote", "Countries applicants may live in", "USA, Canada", mode="", show=remote, hint="Separate with commas. At least one is required for a remote job.") + "</div>"
              + '<p class="tl-t">Pay</p><div class="tl-grid c2">'
              + _f("scur", "Currency code", val="USD", mode="") + _f("smin", "From", "120,000") + _f("smax", "To", "150,000")
              + _sel("sunit", "Per", [("YEAR", "Year", True), ("MONTH", "Month"), ("WEEK", "Week"), ("DAY", "Day"), ("HOUR", "Hour")]) + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div></div>"
              + _private(" The form is turned into code inside your browser and is never sent anywhere.")
              + _board("Markup check", "Fill in the form to build the code.")
              + '<div class="tl-detail" id="tl-detail"></div>'
              + '<div class="tl-out3"><div class="card"><p class="tl-t">JSON-LD for the job page</p>'
                '<textarea class="tl-code" id="tl-code" rows="16" readonly spellcheck="false" aria-label="JobPosting JSON-LD code"></textarea>'
                '<div class="tl-actions"><span class="note">Paste it into the HTML of the page for this one job.</span><button class="btn" type="button" data-copy="tl-code">Copy code</button></div></div></div>'),
         "How to use the code",
         "<p>Copy the code and paste it into the HTML of the page that shows this one job, in the <code>&lt;head&gt;</code> or the <code>&lt;body&gt;</code>. Use one JobPosting per page, on the page where people read the full description and apply, "
         "not on a list of jobs. What the markup says must match what the page shows.</p>"
         "<p>Then test the page: Google’s <a href=\"https://search.google.com/test/rich-results\" rel=\"noopener\">Rich Results Test</a> reads the markup the way Google Search does. "
         "When the job closes, remove the markup or the page, or let <code>validThrough</code> pass.</p>"
         "<p>Inside the description, the character <code>&lt;</code> is written as <code>\\u003c</code>. That is ordinary JSON: it keeps the text from closing the script tag early, and search engines read it as normal HTML.</p>"
         "<p>The checks follow Google’s published <a href=\"https://developers.google.com/search/docs/appearance/structured-data/job-posting\" rel=\"noopener\">JobPosting documentation</a>: "
         "required are <code>title</code>, <code>description</code>, <code>datePosted</code>, <code>hiringOrganization</code> and <code>jobLocation</code> (or, for a fully remote job, "
         "<code>jobLocationType</code> with <code>applicantLocationRequirements</code>); recommended are <code>baseSalary</code>, <code>employmentType</code>, <code>validThrough</code>, <code>identifier</code> and <code>directApply</code>. "
         "The generator only builds text: it does not publish anything or contact Google.</p>",
         [("What is JobPosting structured data?",
           "It is a block of JSON-LD code in a job page that describes the vacancy in a form search engines can read: title, description, employer, location, dates and pay. Google uses it to show jobs in its job search experience."),
          ("Which JobPosting fields does Google require?",
           "Five: title, description, datePosted, hiringOrganization and jobLocation. For a fully remote job, jobLocation gives way to jobLocationType set to TELECOMMUTE, together with applicantLocationRequirements naming at least one country."),
          ("Where do I put the JSON-LD code?",
           "In the HTML of the page for that single job, inside the head or the body. Use one JobPosting per page, on the page where people can read the full description and apply, not on a page that lists many jobs."),
          ("Does the markup guarantee that my job appears on Google?",
           "No. Valid markup makes the page eligible; Google decides what to show. The page also has to be open to Google’s crawler, the markup has to match what the page displays, and the job has to be open."),
          ("What should I do when the job is filled?",
           "Remove the JobPosting markup or the page, or make sure validThrough is a date in the past. Google’s guidelines for job postings ask that expired jobs are not left marked up as open.")],
         ["job-description-checker", "boolean-search"], ["post-a-job/", "widgets/"])

    # ------------------------------------------------------------ 12. Boolean search
    qcard = lambda i, label, note: (f'<div class="card"><p class="tl-t">{label}</p><pre class="tl-q" id="tl-q{i}"></pre>'
                                    f'<div class="tl-actions"><span class="note" id="tl-n{i}">{note}</span><button class="btn" type="button" data-copy="tl-q{i}">Copy</button></div></div>')
    tool("boolean-search", "employers", "Boolean search builder",
         "Build a Boolean string from titles, must-have and any-of skills and exclusions, with X-ray versions for LinkedIn and GitHub.",
         "Boolean Search String Builder for Recruiters",
         "Build Boolean search strings for sourcing: job titles, must-have and any-of skills, exclusions, plus Google X-ray searches for LinkedIn and GitHub. Free.",
         "Build a Boolean search string without the bracket errors",
         "One missing quote or bracket and a search returns the wrong profiles, or none at all. List the job titles, the skills a candidate must have, the ones where any will do, and what to leave out. "
         "You get a clean Boolean string plus Google X-ray versions for LinkedIn and GitHub, ready to copy.",
         wrap("boolean-search",
              '<div class="card tl-form"><div class="tl-grid wide">'
              + _area("titles", "Job titles (any of these)", 3, "Backend Engineer, Software Engineer", hint="Separate with commas or new lines.", cls="")
              + _area("must", "Must have (all of these)", 3, "Python, PostgreSQL", hint="Every term here has to appear.", cls="")
              + _area("any", "Good to have (any one)", 3, "AWS, GCP, Azure", hint="Alternatives: one of them is enough.", cls="")
              + _area("not", "Exclude", 3, "recruiter, intern", hint="Profiles with these words are left out.", cls="") + '</div><div class="tl-grid one">'
              + _f("place", "Location, for the X-ray searches (optional)", "Berlin", mode="") + "</div>"
              + '<div class="tl-checks">' + _check("variants", "Add common spellings of each title (front-end / frontend, engineer / developer)") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + '<div class="tl-out3" aria-live="polite">'
              + qcard(1, "Boolean string · LinkedIn search, job boards, applicant databases", "")
              + qcard(2, "Google X-ray · public LinkedIn profiles", "")
              + qcard(3, "Google X-ray · GitHub", "") + "</div>"),
         "How the strings are built",
         "<ul><li><strong>Titles</strong> and <strong>good-to-have</strong> skills each become a bracketed group joined by <code>OR</code>: any one of them matches.</li>"
         "<li><strong>Must-have</strong> terms are joined with <code>AND</code>: all of them have to appear.</li>"
         "<li><strong>Exclusions</strong> follow <code>NOT</code> in the Boolean string and get a minus sign in the Google versions, because Google does not read NOT.</li>"
         "<li>Any term with a space or a symbol (“machine learning”, “C++”, “Node.js”) is put in quotes so it is searched as one phrase. Duplicates are dropped.</li>"
         "<li>The X-ray strings start with <code>site:linkedin.com/in</code> or <code>site:github.com</code>, which limits Google to public pages of that site. The location is added there as a quoted phrase.</li></ul>"
         "<p>The GitHub string leaves the job titles out, because GitHub profiles rarely state one, and its results include repositories as well as people. "
         "Search engines cut long queries, so the word count under each X-ray string warns you past 32 words. The tool only builds text; it does not run searches or collect profiles.</p>",
         [("What is a Boolean search string?",
           "It is a search query that combines keywords with the operators AND, OR and NOT, with quotes for exact phrases and brackets for grouping. Recruiters use it to describe a candidate profile precisely to a search engine or a candidate database."),
          ("What is an X-ray search?",
           "It is a search engine query limited to one website with the site: operator, for example site:linkedin.com/in to search public LinkedIn profiles through Google. It finds only pages that are public and that the search engine has indexed."),
          ("Why does my search return too few or too many results?",
           "Too few usually means too many AND terms: move some skills to the good-to-have list. Too many means the string is loose: add a must-have skill, a location or an exclusion. Change one thing at a time so you can see what it does."),
          ("Do AND, OR and NOT have to be in capital letters?",
           "Yes on most platforms, including LinkedIn search and Google’s OR. In lower case they are read as ordinary words. Google does not use NOT at all: it excludes a word with a minus sign in front of it, which is how the X-ray strings here are written.")],
         ["job-description-checker", "jobposting-schema"], ["post-a-job/", "widgets/"])

    # ------------------------------------------------------------ write the pages
    by_slug = {t["slug"]: t for t in TOOLS}
    org = {"@type": "Organization", "name": SITE, "url": FULL + "/"}

    def crumbs_ld(parts):
        items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": FULL + "/"}]
        items += [{"@type": "ListItem", "position": i + 2, "name": n, **({"item": f"{FULL}/{u}"} if u else {})} for i, (n, u) in enumerate(parts)]
        return _ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})

    def faq_block(faq):
        html_ = '<div class="tl-faq">' + "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in faq) + "</div>"
        ld = _ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
        return html_, ld

    def cards(items):
        return '<div class="feats">' + "".join(f'<a class="feat" href="{P}/{u}"><h3>{e(n)}</h3><p>{e(d)}</p></a>' for u, n, d in items) + "</div>"

    for t in TOOLS:
        path = f"tools/{t['slug']}/"
        faq_html, faq_ld = faq_block(t["faq"])
        related = [(f"tools/{s}/", by_slug[s]["name"], by_slug[s]["card"]) for s in t["rel"]] + [(u, SITE_PAGES[u][0], SITE_PAGES[u][1]) for u in t["site"]]
        app_ld = _ld({"@context": "https://schema.org", "@type": "WebApplication", "name": t["name"], "url": f"{FULL}/{path}", "description": t["desc"],
                      "applicationCategory": "BusinessApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript", "isAccessibleForFree": True, "inLanguage": "en",
                      "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": org})
        extra = section("Advertised salaries by category and level", sal_table) if t["slug"] == "salary-checker" else ""
        body = (crumbs(("Tools", "tools/"), (t["name"], "")) + f'<h1>{e(t["h1"])}</h1><p class="lead">{e(t["lead"])}</p>' + t["html"]
                + '<div class="tl-after">' + extra
                + section(t["how_title"], f'<div class="tl-how">{t["how"]}</div>')
                + section("Questions", faq_html)
                + section("Related tools", cards(related), ("tools/", "All free tools")) + "</div>")
        page(path, t["title"], t["desc"], body, head=assets + app_ld + faq_ld + crumbs_ld([("Tools", "tools/"), (t["name"], "")]))

    # ------------------------------------------------------------ tiles
    # Each tile carries a small screen that shows what the tool gives back. The salary screen uses today's real figures;
    # the others are worked examples (the arithmetic in them is exact) and say so.
    mids = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in jobs if j.get("usd"))
    kmoney = lambda v: f"${v / 1000:,.0f}K"
    ex = '<span class="ex">example</span>'
    PREV = {
        "resume-match": ex + '<span class="big">78%<small>match</small></span><span class="mt"><i style="width:78%"></i></span>'
                             '<span class="ln"><b>9 of 12</b> skills from the posting found. Missing: Kafka, Terraform, Go</span>',
        "salary-converter": ex + '<span class="ln">$60 an hour, 40 hours a week</span><span class="big">$124,800<small>a year</small></span>'
                                 '<span class="ln"><b>$10,400</b> a month · <b>$2,400</b> a week</span>',
        "raise-calculator": ex + '<span class="ln">$120,000 with a 7% raise</span><span class="big">$128,400<small>a year</small></span>'
                                 '<span class="ln"><b>+$8,400</b> a year · <b>+$700</b> a month</span>',
        "compare-offers": ex + '<span class="rw"><span>Offer A</span><span class="mt"><i style="width:100%"></i></span><b>$182K</b></span>'
                               '<span class="rw"><span>Offer B</span><span class="mt"><i style="width:94%"></i></span><b>$171K</b></span>'
                               '<span class="ln">Base, bonus, equity and benefits, per year</span>',
        "equity-calculator": ex + '<span class="ln">10,000 options · strike $4.20 · share $10.00</span><span class="big">$58,000<small>on paper</small></span>'
                                  '<span class="mt"><i style="width:50%"></i></span><span class="ln"><b>Half vested</b> after two of four years</span>',
        "time-zone-overlap": ex + '<span class="rw"><span>New York</span><span class="mt"><i style="left:58.3%;width:33.3%"></i></span></span>'
                                  '<span class="rw"><span>London</span><span class="mt"><i style="left:37.5%;width:33.3%"></i></span></span>'
                                  '<span class="rw"><span>Berlin</span><span class="mt"><i style="left:33.3%;width:33.3%"></i></span></span>'
                                  '<span class="ln"><b>2 shared hours</b> a day in winter: 14:00 to 16:00 UTC</span>',
        "cover-letter": '<span class="ln"><b>Dear Hiring Manager,</b></span><span class="sk" style="width:96%"></span><span class="sk h" style="width:62%"></span>'
                        '<span class="sk" style="width:90%"></span><span class="sk" style="width:84%"></span><span class="sk" style="width:38%"></span>',
        "negotiation-email": ex + '<span class="ln"><b>Subject:</b> the offer, a question about salary</span><span class="sk" style="width:92%"></span>'
                                  '<span class="sk" style="width:86%"></span><span class="ln">Asking for <b>$165,000</b> instead of $150,000</span><span class="sk" style="width:44%"></span>',
        "contractor-rate": ex + '<span class="ln">To end up with $100,000 a year</span><span class="big">$722<small>a day</small></span>'
                                '<span class="ln"><b>180</b> billable days · <b>$90</b> an hour</span>',
        "job-description-checker": ex + '<span class="big">64<small>out of 100</small></span><span class="mt"><i style="width:64%"></i></span>'
                                        '<span class="ln">No salary range · 14 must-haves · 2 biased words</span>',
        "jobposting-schema": '<code>{ "@type": <b>"JobPosting"</b>,\n  "title": "Data Engineer",\n  "datePosted": "' + today.isoformat() + '",\n  "hiringOrganization": { … } }</code>',
        "boolean-search": '<code>(<b>"backend engineer"</b> OR "software engineer")\nAND (Python OR Go)\nNOT (recruiter OR intern)</code>',
    }
    if len(mids) >= MIN_SAMPLE:
        q = lambda p: mids[min(len(mids) - 1, int(p * len(mids)))]
        lo, hi = q(.1), q(.9)
        pos = lambda v: max(0, min(100, 100 * (v - lo) / max(hi - lo, 1)))
        PREV["salary-checker"] = (f'<span class="big">{kmoney(q(.5))}<small>median today</small></span>'
                                  f'<span class="mt"><i style="left:{pos(q(.25)):.0f}%;width:{pos(q(.75)) - pos(q(.25)):.0f}%"></i><u style="left:{pos(q(.5)):.0f}%"></u></span>'
                                  f'<span class="ln">Half of postings: <b>{kmoney(q(.25))} to {kmoney(q(.75))}</b> · {len(mids):,} roles</span>')

    def tile(path, name, text, slug=""):
        prev = PREV.get(slug)
        return (f'<a class="tcard" href="{P}/{path}">' + (f'<span class="tprev" aria-hidden="true">{prev}</span>' if prev else "")
                + f'<span class="tbody"><b>{e(name)}</b><span>{e(text)}</span><i><u>Open the tool</u></i></span></a>')

    for t in TOOLS:
        TILES[f"tools/{t['slug']}/"] = tile(f"tools/{t['slug']}/", t["name"], t["card"], t["slug"])
    # the resume builder, the match by answers and the application tracker are tools too; a visitor who opens "Tools" must find them first
    PREV["resume"] = ('<span class="ln"><b>Your name</b> · Data analyst</span><span class="sk" style="width:92%"></span><span class="sk h" style="width:46%"></span>'
                      '<span class="sk" style="width:86%"></span><span class="sk" style="width:74%"></span><span class="ln">Saved as <b>Word</b>, <b>PDF</b> or plain text</span>')
    PREV["for-you"] = ex + '<span class="big">61<small>jobs fit all 5 answers</small></span><span class="mt"><i style="width:100%"></i></span><span class="ln">Work · experience · place · <b>pay</b> · skills</span>'
    PREV["my-jobs"] = (ex + '<span class="rw"><span>Saved</span><span class="mt"><i style="width:100%"></i></span><b>9</b></span><span class="rw"><span>Applied</span><span class="mt"><i style="width:66%"></i></span><b>6</b></span>'
                       '<span class="rw"><span>Interview</span><span class="mt"><i style="width:22%"></i></span><b>2</b></span><span class="ln">A reminder when an application goes quiet</span>')
    TILE_TEXT = {
        "resume/": ("resume/", "Resume builder", "Type your experience once and get a clean one-column resume that screening software reads correctly. Download it as Word or PDF.", "resume"),
        "for-you/": ("for-you/", "Jobs that fit you", "Answer five questions about the work, the place and the pay you want, and see the open jobs that fit, with the reason next to each.", "for-you"),
        "my-jobs/": ("my-jobs/", "Application tracker", "Save jobs, mark where each application stands and keep notes. Kept in your browser, with a backup file you can download.", "my-jobs"),
    }
    TILES["resume/"] = tile("resume/", "Resume builder", "Type your experience once and get a clean one-column resume that screening software reads correctly. Download it as Word or PDF.", "resume")
    TILES["for-you/"] = tile("for-you/", "Jobs that fit you", "Answer five questions about the work, the place and the pay you want, and see the open jobs that fit, with the reason next to each.", "for-you")
    TILES["my-jobs/"] = tile("my-jobs/", "Application tracker", "Save jobs, mark where each application stands and keep notes. Kept in your browser, with a backup file you can download.", "my-jobs")

    # ------------------------------------------------------------ the hub
    # The hub: three wide rows for the tools most visitors want, then a ruled list with a one-line sample result on the right.
    RES = {
        "resume-match": "78% match · 9 of 12 skills found",
        "salary-converter": "$60 an hour = $124,800 a year",
        "raise-calculator": "7% on $120,000 = +$8,400 a year",
        "compare-offers": "Offer A $182K, offer B $171K",
        "equity-calculator": "10,000 options at $10 = $58,000 on paper",
        "time-zone-overlap": "New York and London share 2 hours",
        "cover-letter": "A one-page letter, ready to edit",
        "negotiation-email": "Ask for $165,000 instead of $150,000",
        "contractor-rate": "$100,000 a year = $722 a day",
        "job-description-checker": "64 out of 100: no salary range",
        "jobposting-schema": '{ "@type": "JobPosting", … }',
        "boolean-search": '("backend engineer" OR …) AND Python',
    }
    if len(mids) >= MIN_SAMPLE:
        RES["salary-checker"] = f"Median today {kmoney(q(.5))} across {len(mids):,} roles"

    def wide(path, name, text, slug):
        prev = PREV.get(slug, "")
        return (f'<a class="twide" href="{P}/{path}"><span class="tprev" aria-hidden="true">{prev}</span>'
                f'<span class="tbody"><b>{e(name)}</b><span>{e(text)}</span><i><u>Open the tool</u></i></span></a>')

    def trow(path, name, text, slug):
        return (f'<li><a href="{P}/{path}"><b><u>{e(name)}</u></b><span class="d">{e(text)}</span>'
                f'<span class="r"><small>Example</small>{e(RES.get(slug, ""))}</span></a></li>')

    def group(key):
        return '<ul class="tlist">' + "".join(trow(f"tools/{t['slug']}/", t["name"], t["card"], t["slug"]) for t in TOOLS if t["group"] == key) + "</ul>"
    hub_faq = [("Are these tools free?", "Yes. Every tool on this page is free, needs no account and can be used as often as you like."),
               ("Do the tools store or upload what I type?",
                "No. All calculations and text checks run in your browser. What you type is saved only in this browser’s storage so a tool remembers it next time, and every tool has a Clear button that erases it."),
               ("Do the tools use AI?",
                "No. The calculators are plain arithmetic, the checkers count words and patterns, and the letter writers are fill-in templates. How each result is calculated is explained under the tool."),
               ("Where do the salary figures come from?",
                f"From the salary ranges that employers publish in their own job postings on this site: {n_paid:,} open roles with a yearly US-dollar range as of {DATE}. No surveys and no numbers submitted by users.")]
    faq_html, faq_ld = faq_block(hub_faq)
    n_seek, n_emp = sum(t["group"] == "seekers" for t in TOOLS), sum(t["group"] == "employers" for t in TOOLS)
    hub_desc = "Free tools for a job search and for hiring: resume builder, resume match checker, job matching by answers, application tracker, salary checker, pay calculators, cover letter and more."
    list_ld = _ld({"@context": "https://schema.org", "@type": "ItemList", "name": f"Free tools on {SITE}", "numberOfItems": len(TOOLS),
                   "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": t["name"], "url": f"{FULL}/tools/{t['slug']}/"} for i, t in enumerate(TOOLS)]})
    page("tools/", "Free Tools for Tech Job Seekers & Recruiters" + brand, hub_desc,
         crumbs(("Tools", "")) + "<h1>Free tools for a tech job search and for hiring</h1>"
         f'<p class="lead">{len(TOOLS) + len(EXTRA)} tools, from a resume builder to pay calculators, for things that come up along the way: whether your pay is fair, how well a resume fits a posting, which of two offers is worth more, why a vacancy gets no replies. '
         f"They run in your browser with no account, and the salary figures come from the {n_paid:,} open postings here that publish a pay range.</p>"
         + section("Start here: resume, matching, tracking", '<div class="twides">' + "".join(wide(*TILE_TEXT[u]) for u in EXTRA) + "</div>")
         + section("For job seekers", group("seekers"))
         + section("For employers and recruiters", group("employers"))
         + section("How these tools work", '<div class="feats">'
                   '<div class="feat"><h3>Nothing leaves your browser</h3><p>Every calculation and text check runs on your device. Nothing is uploaded, and “Clear” erases what a tool remembers.</p></div>'
                   f'<div class="feat"><h3>The salary figures have a source</h3><p>They come from {n_paid:,} open roles that publish a yearly US-dollar range. No figure is shown for fewer than {MIN_SAMPLE} postings.</p></div>'
                   '<div class="feat"><h3>The method is on the page</h3><p>Arithmetic and fill-in templates, not AI. Under each tool you can read how its result is calculated.</p></div></div>')
         + section("Questions", faq_html)
         + section("More on this site", cards([(u, SITE_PAGES[u][0], SITE_PAGES[u][1]) for u in ("jobs/", "salaries/", "resume/", "for-you/", "post-a-job/", "widgets/")])),
         head=assets + list_ld + faq_ld + crumbs_ld([("Tools", "")]))

    return [(f"tools/{t['slug']}/", t["name"], t["card"]) for t in TOOLS]
