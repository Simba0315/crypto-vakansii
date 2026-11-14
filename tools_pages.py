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


# An invented resume with the faults the review looks for: a long "About me", a long skills list ahead of the jobs, duty wording, few numbers, a gap, one over-long line.
EX_REVIEW = ("Jordan Example\nSoftware Developer\njordan@example.com · Springfield\n\n"
             "About me\nI am a passionate and hard-working developer who loves technology and is always eager to learn new things. I have worked in many different teams and on many "
             "different projects over the years, and I believe that communication and teamwork are the key to success. I am looking for a company where I can grow, take on new "
             "challenges and make a real difference with my skills.\n\n"
             "Skills\nPython, Django, JavaScript, React, PostgreSQL, MySQL, MongoDB, Redis, Docker, Kubernetes, AWS, Terraform, Jenkins, Git, Linux, Kafka, GraphQL, Elasticsearch, TypeScript, Go, Rust, PHP\n\n"
             "Experience\nSoftware Developer, Example Shop Ltd\n03/2022 - present\n- Responsible for the backend of the online store\n- Worked on the checkout and the payment pages\n"
             "- Built a Python service that sends order emails and cut failed deliveries from 4% to 1%\n- Participated in code reviews and daily meetings\n\n"
             "Junior Developer, Sample Agency\nJan 2019 – Feb 2021\n- Helped with websites for clients of the agency\n"
             "- Duties included fixing bugs, writing tests and updating old pages when clients asked for changes to their content or their design, and talking to clients on the phone about "
             "what they wanted to change, which often took most of the day\n- Moved 12 client sites from PHP to Django\n\n"
             "Education\nBSc Computer Science, Example University\n2015 – 2018")
EX_STAR = {"situation": "Last year our support team at Example Co was answering about 900 tickets a week, and a third of them were the same question about failed card payments. Replies were taking two days.",
           "task": "As the team lead, I was asked to bring the reply time under one day without hiring more people.",
           "action": "I read 200 of the payment tickets and grouped them by cause. I found that most came from one unclear error message, so I wrote a clearer message and asked the product team to ship it. "
                     "I also wrote a help article and a saved reply for my team, and I checked the numbers every Monday for six weeks.",
           "result": "Payment tickets fell from about 300 to 90 a week, and our average reply time dropped from two days to nine hours.",
           "learned": "It taught me to look for the cause of a problem before asking for more people."}
EX_LI_HEAD = "OPEN TO WORK 🚀🚀🚀 | Passionate, results-driven guru | Dream big!"
EX_LI_ABOUT = ("PASSIONATE ABOUT TECHNOLOGY!!! Jordan is a hard-working team player and a true thought leader with a proven track record. "
               "Jordan thinks outside the box and always gives everything. Jordan has worked in many companies and loves new challenges.")


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
        "jobs/": ("Open tech jobs", f"{n_jobs:,} roles from company career pages, re-checked every hour."),
        "remote/": ("Remote tech jobs", "Open roles listed as remote, with the countries or time zones each one accepts."),
        "salaries/": ("Salaries by role, skill and company", "Median advertised pay from live postings, with the number of roles behind each figure."),
        "resume/": ("Resume builder", "A plain one-column resume that screening software reads cleanly. Saves as PDF, nothing uploaded."),
        "for-you/": ("Jobs for you", "Pick your skills or paste your resume and see the open roles that fit, best matches first."),
        "post-a-job/": ("Post a job", "Put your vacancy in front of people who are searching for tech roles right now."),
        "widgets/": ("Jobs widget and live badges", "Show live tech jobs on your own site with one line of code."),
        "contract/": ("Contract tech jobs", "Open contract roles at tech companies, updated hourly."),
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
         ["resume-review", "resume-bullet-builder", "cover-letter"], ["resume/", "for-you/"])

    # ------------------------------------------------------------ 1b. keywords of a job description (the Careerist study: one tool page per search phrase)
    tool("job-description-keywords", "seekers", "Job description keyword finder",
         "Paste a job description: see the skills and the terms it stresses, and get a skills line to copy into your resume.",
         "Job Description Keyword Finder: Skills and ATS Keywords",
         "Paste a job description to see the skills and repeated terms it stresses, ranked, and copy a ready skills line for your resume. Free, runs in your browser.",
         "Find the keywords in a job description",
         "Recruiters search their applicant tracking system for the words the posting uses. Paste the posting: you get the skills it names, the terms it repeats "
         "and a skills line in its own words, ready for your resume. Nothing is uploaded.",
         wrap("job-description-keywords",
              '<div class="card tl-form"><div class="tl-grid one">'
              + _area("jd", "The job description", 14, "Paste the full text of the job posting here", cls="", tall=True, ex=EX_JD) + "</div>"
              + '<div class="tl-actions"><button class="btn" type="button" id="tl-run">Find the keywords</button>' + _clear(True) + "</div></div>"
              + _private(" The text is read inside your browser and never sent anywhere.")
              + _board("Keywords", "Paste a job description to see the keywords it stresses.")
              + '<div class="tl-detail" id="tl-detail"></div>'),
         "How the keywords are found",
         f"<p><strong>Skills.</strong> The text is searched for the {n_skills} skills this site tracks in job postings: languages, frameworks, cloud platforms and tools, "
         "including their usual spellings (“Postgres” is PostgreSQL).</p>"
         "<p><strong>Repeated terms.</strong> Words and two-word phrases the posting uses at least twice, once the words every posting uses (“team”, “experience”, “requirements”) "
         "are left out. The more often a term is repeated, the higher it is listed.</p>"
         "<p>The skills line joins the skills found, in the posting’s order. Copy only the ones you really have.</p>",
         [("What are ATS keywords?",
           "The words a recruiter types when searching applications in an applicant tracking system: usually the skills, tools and job title the posting names. A resume that uses the same words is found more often."),
          ("Should I copy every keyword into my resume?",
           "No: only the ones that are true for you. Where you have a skill, use the posting’s exact word, in the skills line and in the job where you used it."),
          ("Is the job description uploaded anywhere?",
           "No. It is read inside your browser and kept only in this browser’s storage so the page remembers it; the Clear button erases it.")],
         ["resume-match", "resume-bullet-builder", "cover-letter"], ["resume/", "for-you/"])

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
         f"<p>Every figure is calculated from job postings collected from employers’ own careers pages and re-checked every hour. On {DATE} there were {n_jobs:,} open roles; "
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
         ["offer-check", "salary-converter", "raise-calculator"], ["salaries/"])

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
         ["raise-request-email", "salary-checker", "negotiation-email"], ["salaries/"])

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
         ["offer-check", "equity-calculator", "negotiation-email"], ["jobs/"])

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
         ["remote-work-savings", "compare-offers", "salary-converter"], ["remote/"])

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
         ["resume-match", "thank-you-email", "interview-answer-builder"], ["resume/"])

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
         ["offer-check", "raise-request-email", "salary-checker"], ["salaries/"])

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
         ["jobposting-schema", "interview-scorecard", "boolean-search"], ["post-a-job/"])

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
         ["job-description-checker", "jobposting-schema", "cost-per-hire"], ["post-a-job/", "widgets/"])

    # ============================================================ added 2026-11-13: reviews, letters, builders, calculators
    mail_note = _private(" The text is assembled inside your browser and is never sent anywhere.")
    run_btn = lambda label: f'<button class="btn" type="button" id="tl-run">{label}</button>'
    # one text result with its own counter and Copy button; tools.js fills the three ids
    vcard = lambda i, label: (f'<div class="card" id="tl-c{i}"><p class="tl-t" id="tl-k{i}">{label}</p><pre class="tl-q txt" id="tl-q{i}"></pre>'
                              f'<div class="tl-actions"><span class="note" id="tl-n{i}" role="status"></span><button class="btn" type="button" data-copy="tl-q{i}">Copy</button></div></div>')

    # ------------------------------------------------------------ 14. resume review
    tool("resume-review", "seekers", "Resume review",
         "Paste your resume: a score out of 10 from six plain checks, with strengths, weaknesses and what to fix, each quoting your own line.",
         "Resume Review: Free Score Out of 10 and Fixes",
         "Paste your resume for a rule-based review: a score out of 10 from six checks, strengths, weaknesses and what to fix, quoting your own lines. No AI, private.",
         "Get your resume reviewed the way a recruiter skims it",
         "A recruiter’s first pass over a resume is a skim: the top of the page, a few bullet points, the dates. This review reads your text the same way with six plain checks: "
         "what the first screen holds, duty wording, numbers, the skills list, gaps between dates and length. You get a score out of 10 from a formula printed on this page, "
         "strengths, weaknesses and a list of fixes, each quoting your own line. It works by rules, not AI, and nothing is uploaded.",
         wrap("resume-review",
              '<div class="card tl-form">'
              + _area("text", "Your resume (plain text)", 16, "Paste the text of your resume here, with its headings and dates", tall=True, ex=EX_REVIEW)
              + '<div class="tl-actions">' + run_btn("Review the resume") + _clear(True) + "</div></div>"
              + _private(" The text is read inside your browser and is never sent anywhere.")
              + _board("Resume review", "Paste the text of your resume to see its score and what to fix.")
              + '<div class="tl-detail" id="tl-detail"></div>'
              + f'<p class="note tl-priv"><b>What it cannot judge</b>Whether the content is true, how the page is designed, and how well you fit a particular job. For the fit, use the '
                f'<a href="{P}/tools/resume-match/">resume match checker</a> with the job description; for the layout, the <a href="{P}/resume/">resume builder</a>.</p>'),
         "How the score is calculated",
         "<p>The score is the sum of six checks, 10 points in all:</p><ul>"
         "<li><strong>First screen, 2 points.</strong> The review estimates the first 12 lines of the page; a pasted line of more than 100 characters counts as several. One point is lost for each of these: "
         "your first job starts after line 12; the summary is longer than 60 words; more than 10 skills are listed before any job. If no job with dates is found, the check gives 0.</li>"
         "<li><strong>Wording, 2 points.</strong> Lines under your jobs that contain “responsible for”, “duties included”, “tasked with”, “in charge of”, “helped with”, “helped to”, “worked on”, "
         "“assisted with”, “participated in”, “involved in” or “was part of”. None: 2 points. One or two lines: 1. Three or more: 0.</li>"
         "<li><strong>Numbers, 2 points.</strong> The share of bullet points under your jobs that contain a number that is not a year. Half or more: 2 points. A quarter or more: 1. Fewer: 0. "
         "Bullet points are lines that start with a dash or a dot; if there are none, lines of eight or more words under a job are used.</li>"
         "<li><strong>Skills, 1.5 points.</strong> Each entry of your skills list is searched for in the text of your jobs. Up to a third missing: 1 point. Up to two thirds: 0.5. More: 0. "
         "A list of 20 entries or fewer adds 0.5. With no skills list the check gives 0.5.</li>"
         "<li><strong>Gaps, 1 point.</strong> Date ranges such as “Jan 2021 – Mar 2023”, “2019–2021” and “03/2020 – present” are read wherever they stand, education included. "
         "No break of more than six months: 1 point. One break: 0.5. Two or more: 0. If no dates can be read, the check says so and gives 0.5. A range given in years only is counted from January of "
         "the first year to December of the last, and the time since your last entry counts as a break when it is longer than six months.</li>"
         "<li><strong>Length, 1.5 points.</strong> 250 to 1,300 words: 1 point (up to 650 words is about one page, up to 1,300 about two). 150 to 249 words: 0.5. Otherwise 0. "
         "No line under your jobs longer than 200 characters, about two lines of the page: 0.5.</li></ul>"
         "<p>8.5 and above is labelled “reads well on a first skim”, 6.5 to 8 “solid”, 4.5 to 6 “readable”, anything lower “hard to skim”. The points and thresholds are our own rules of thumb, "
         "written down so that you can check them; they are not an industry standard. The review cannot tell whether what you wrote is true, how the page looks or whether you fit a particular job. "
         "A break in the dates is a question a reader may ask, not a fault.</p>",
         [("How is the resume score calculated?",
           "It is the sum of six checks worth 10 points in all: first screen 2, wording 2, numbers 2, skills 1.5, gaps 1 and length 1.5. The exact rule for each check is under “How the score is calculated”, so the same text always gets the same score."),
          ("Is the review done by AI?",
           "No. The page counts words, lines, numbers and dates, and looks for a short list of phrases. That is why every finding can quote the line it is about, and why the review cannot judge things that need understanding, such as whether a result is impressive."),
          ("Is my resume uploaded anywhere?",
           "No. The text is read inside your browser and never sent to a server. It is kept in this browser’s storage so the page remembers it, and the Clear button erases it."),
          ("Why does the review say my dates could not be read?",
           "It reads ranges written as “Jan 2021 – Mar 2023”, “2019–2021”, “03/2020 – present” and close variants. Dates in other forms, such as “Spring 2021” or a single year, are skipped; gaps are then not checked, and the page says so."),
          ("What does the review not check?",
           "Whether the content is true, the design of the page, spelling, and how well the resume fits a specific job. For the fit, paste the resume and the job description into the resume match checker on this site.")],
         ["resume-match", "resume-bullet-builder", "linkedin-review"], ["resume/", "for-you/"])

    # ------------------------------------------------------------ 15. LinkedIn profile review
    tool("linkedin-review", "seekers", "LinkedIn profile review",
         "Paste your headline and About text: length against LinkedIn’s limits, a clear role, the opening lines, numbers and buzzwords, with fixes.",
         "LinkedIn Profile Review: Headline and About",
         "Paste your LinkedIn headline and About text for a rule-based check: length, role, opening lines, numbers, buzzwords and capitals, with each fragment quoted.",
         "Check your LinkedIn headline and About text",
         "Two parts of a LinkedIn profile are written entirely by you: the headline under your name and the About text. A headline that says only “open to work”, or an About that opens with a slogan, "
         "tells a searcher nothing about what you do. Paste both. The page checks the length against LinkedIn’s limits, whether the headline names a role and a field and what the opening of the About says, "
         "and it flags buzzwords, capitals and emoji. Each point quotes the part of your text it is about. It works by rules, not AI.",
         wrap("linkedin-review",
              '<div class="card tl-form">'
              + _area("headline", "Your headline", 2, "Paste the line that stands under your name on LinkedIn", hint="LinkedIn allows 220 characters.", ex=EX_LI_HEAD)
              + _area("about", "Your About text", 10, "Paste your About section", tall=True, ex=EX_LI_ABOUT)
              + '<div class="tl-actions">' + run_btn("Check the profile") + _clear(True) + "</div></div>"
              + _private(" Both texts are checked inside your browser and are never sent to LinkedIn or anywhere else.")
              + _board("Profile review", "Paste your headline and your About text to see what to fix.")
              + '<div class="tl-detail" id="tl-detail"></div>'),
         "What is checked",
         "<p><strong>Headline.</strong> Its length against LinkedIn’s limit of 220 characters; whether it contains a job title (a word such as engineer, designer, manager or nurse, from a list of common titles) "
         "and at least one more word that says what kind of work it is; whether it says only that you are looking, as in “open to work”; buzzwords; a headline written mostly in capital letters; more than two emoji.</p>"
         "<p><strong>About.</strong> Its length against the limit of 2,600 characters, and whether it is under 300. The first 300 characters are treated as the opening that is read before “see more”; "
         "LinkedIn shows roughly that much, less on a phone. The opening should say what you do (a job title, or “I” followed by a verb such as build, help or manage) and for whom "
         "(words such as clients, teams, companies, patients). Then: first person (“I”, “my”), a number that is not a year, a way to reach you or a clear ask (contact, message, email, “open to”, a link), "
         "buzzwords, a phrase of three or more words in capitals, and more than five emoji.</p>"
         "<p>The buzzword list is short and ours: passionate, results-driven, guru, ninja, rockstar, wizard, synergy, thought leader, visionary, team player, self-starter, motivated, innovative, "
         "proven track record, outside the box and a few more. Points marked “Fix” and “Check” are counted as things to fix; “Note” is a smaller suggestion. "
         "The page reads words and patterns. It cannot judge your photo, your experience entries or whether a claim is true, and an unusual job title may not be on its list.</p>",
         [("How long can a LinkedIn headline be?",
           "220 characters, including spaces. There is no need to fill them: a job title, a field and two or three skills are enough. The check flags a headline over the limit and notes one under 30 characters."),
          ("What is “the opening” of the About section?",
           "LinkedIn shows only the first lines of the About text until a reader clicks “see more”. This page treats the first 300 characters as that opening and checks that they say what you do and for whom, because a reader may never see the rest."),
          ("Which words count as buzzwords?",
           "A short list of words that fit any profile and so say little: passionate, results-driven, guru, ninja, synergy, thought leader, team player, proven track record and similar. The fix is the fact behind the word: what you did, for whom, with what result."),
          ("Is my profile text sent to LinkedIn or anywhere else?",
           "No. The check runs in your browser on the text you paste. Nothing is uploaded, the page does not connect to LinkedIn, and the Clear button erases what the page remembers.")],
         ["linkedin-headline", "resume-review", "resume-match"], ["resume/"])

    # ------------------------------------------------------------ 16. offer check (same embedded aggregates as the salary checker, without the per-skill groups)
    offer_data = {"q": QS, "min": MIN_SAMPLE, "date": DATE, "g": {k: v for k, v in groups.items() if k.endswith("|")}}
    tool("offer-check", "seekers", "Offer check",
         "Enter an offered salary and pick the category and level: see where it sits among advertised ranges and how far it is from the median.",
         "Job Offer Check: Salary vs Advertised Ranges",
         "Check a salary offer against the advertised ranges of open tech jobs: where it sits for your category and level, the median and the postings behind it. Free.",
         "Check a salary offer against what open postings advertise",
         f"When an offer arrives it is hard to tell whether the figure is fair: {100 - sal_pct}% of the {n_jobs:,} open roles on this site do not state a salary. This check uses the {n_paid:,} that do. "
         "Enter the yearly pay you were offered in US dollars and pick the category and level. You see whether the offer is below the lower quarter, in the middle half or above the upper quarter "
         "of advertised ranges, how far it is from the median, and how many postings stand behind the comparison.",
         wrap("offer-check",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("pay", "Yearly pay you were offered, USD", "135,000", hint="Base pay before tax. You can type 135k.")
              + _sel("cat", "Category", [("", "All categories")] + cats)
              + _sel("lvl", "Level", [(v, n_) for v, n_ in LEVELS if not v or f"|{v}|" in groups], hint="As it stands in the job title: Senior, Lead, Junior…") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Your offer against advertised pay", "Enter the yearly pay you were offered, in US dollars.")
              + '<p class="note tl-priv"><b>Private</b>The offer is compared inside your browser and is never sent anywhere. Figures are advertised ranges, not verified pay; bonus and equity are not included.</p>'
              + '<script type="application/json" id="tl-data">' + json.dumps(offer_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>"),
         "How the offer is compared",
         f"<p>The comparison uses the same figures as the salary checker. On {DATE}, {n_paid:,} of the {n_jobs:,} open roles here publish a yearly salary range in US dollars. Each posting counts once, by the midpoint of its range.</p>"
         "<ul><li><strong>Median:</strong> the middle posting of the group you picked.</li>"
         "<li><strong>Lower and upper quarter:</strong> the 25th and the 75th percentile. Below the first, three out of four postings advertise more; above the second, three out of four advertise less; between them lies the middle half.</li>"
         "<li><strong>Percent against the median:</strong> <code>(offer − median) ÷ median × 100</code>, rounded to a whole percent.</li></ul>"
         "<p>The sentence under the figure follows fixed rules. Below the lower quarter it reads “worth asking for more”; inside the middle half and more than 5% under the median, “there is room to ask”; "
         f"within 5% of the median, “close to the median”. A group needs at least {MIN_SAMPLE} postings. If the category and level you picked have fewer, the page says so and compares with the next wider group: "
         "every category at the same level, then the same category at any level, then all postings. A wider group mixes categories or levels, so it is only a rough guide: the page says so, and gives the position without the advice.</p>"
         "<p>Advertised ranges are what employers say they are prepared to pay, not what people were paid. Bonus, equity and benefits are not in them, and ranges in other currencies are left out. "
         "Treat the result as one reference point in a negotiation, not as a verdict on the offer.</p>",
         [("How do I know if a salary offer is fair?",
           "Compare it with what employers advertise for the same kind of role and level. This check places your offer among the advertised ranges on this site and shows the median, the middle half and the number of postings behind them. An offer below the lower quarter is low by that measure."),
          ("What does “below the lower quarter” mean?",
           "Three out of four postings in the group advertise a range with a higher midpoint than your offer. “In the middle half” means the offer lies between the 25th and the 75th percentile, where half of all postings are."),
          ("Why is my offer compared with a wider group?",
           f"Because fewer than {MIN_SAMPLE} open postings with a published salary match the category and level you picked. A median of a handful of postings says little, so the page widens the group and tells you which one it used."),
          ("Should I ask for more if the offer is below the median?",
           "The figures give you a reason to ask, not a guarantee of the answer. Ask for a figure you can back up, state it once and clearly, and decide beforehand what you would accept. The negotiation email writer on this site builds the message.")],
         ["salary-checker", "negotiation-email", "compare-offers"], ["salaries/"])

    # ------------------------------------------------------------ 17. thank-you email
    tool("thank-you-email", "seekers", "Thank-you email after an interview",
         "Who you met, the role and one thing you discussed become a short thank-you email in one of three tones. A template, not AI.",
         "Thank-You Email After an Interview: Template",
         "Write a thank-you email after a job interview from a few fields: who you met, the role and one thing you discussed. Three tones. Template-based, private, free.",
         "Write the thank-you email on the day of the interview",
         "A thank-you email is four or five sentences, and it still sits unsent when the wording feels awkward. A generic note says nothing about the conversation you had. "
         "Enter who you spoke to, the role and one thing you talked about, pick a tone, and the email is ready to copy. It is a fill-in template, not AI: each sentence is built from what you type.",
         wrap("thank-you-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _f("to", "Interviewer’s first name", "Dana", mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job you interviewed for", "Senior Backend Engineer", mode="")
              + _f("company", "Company (optional)", "Acme", mode="", auto="organization")
              + _f("when", "When you spoke (optional)", "this morning", mode="", hint="For example: yesterday, on Tuesday.")
              + _sel("tone", "Tone", [("short", "Short", True), ("warm", "Warm"), ("formal", "Formal")])
              + _area("topic", "One thing you discussed", 2, "the move from monthly releases to weekly ones", hint="Finish the sentence “I enjoyed hearing about …”.")
              + _area("add", "Something you want to add (optional)", 2, "It is the kind of change I led in my last job, so I would be glad to help with it.",
                      hint="One full sentence: a point you forgot to make, or why the topic matters to you.") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("thank-you-email.txt") + "</div>"),
         "How the email is put together",
         "<p>Every version has the same three parts: thanks for the person’s time, one specific point from the conversation, and a clear line that you still want the job. The first line of the output is the subject.</p>"
         "<p>“Short” is one paragraph, “warm” is friendlier and a little longer, “formal” suits banks, law firms and the public sector. The one thing you discussed cannot come from a template, "
         "so it stays in [brackets] until you fill it in. The tone changes the wording, never the facts. No AI is involved and nothing is sent anywhere: copy the text into your own email and send it yourself.</p>",
         [("When should I send a thank-you email after an interview?",
           "The same day or the next morning, while the conversation is still fresh for both of you. If you met several people, send each of them a separate short email and change the detail you mention."),
          ("What should a thank-you email say?",
           "Three things: thanks for the person’s time, one specific point from your conversation, and that you are still interested in the job. The specific point shows that the email was written after this interview and not copied."),
          ("Does a thank-you email improve my chances?",
           "Nobody can promise that, and this page does not. It is a courtesy, it keeps the conversation open, and it gives you a place to add something you forgot to say in the room."),
          ("Is the email written by AI?",
           "No. It is a fill-in template: every sentence is assembled from the fields you complete, in the tone you choose. Nothing is generated or sent to a server.")],
         ["interview-answer-builder", "reference-request-email", "negotiation-email"], ["for-you/"])

    # ------------------------------------------------------------ 18. resignation letter
    tool("resignation-letter", "seekers", "Resignation letter builder",
         "Your last day, your notice period, optional thanks and a handover offer become a short, neutral letter to copy or print.",
         "Resignation Letter Template: Short and Neutral",
         "Build a short, neutral resignation letter: last working day, notice period, optional thanks and a handover offer. Copy, download or print. Private, no sign-up.",
         "Write a short resignation letter that states the facts",
         "A resignation letter has one job: to put on record that you are leaving and on which day. Anything more, such as reasons or complaints, stays in your file after you have gone. "
         "Enter your last working day and a few details, choose whether to add thanks and a handover offer, and copy or print the letter. "
         "Check your contract for the notice period you owe before you set the date.",
         wrap("resignation-letter",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("to", "Manager’s name", "Dana Lee", mode="")
              + _f("title", "Your job title", "Senior Backend Engineer", mode="")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("lastDay", "Your last working day", typ="date", mode="",
                   hint=f'Count it from the notice period in your contract. The <a href="{P}/tools/last-working-day/">last working day calculator</a> works out the date.')
              + _f("notice", "Notice period in your contract (optional)", "two weeks", mode="", hint="In words: two weeks, one month.")
              + _f("date", "Date of the letter", typ="date", mode="")
              + _sel("format", "Format", [("email", "Email, with a subject line", True), ("letter", "Printed letter, with the date")]) + "</div>"
              + '<div class="tl-checks">' + _check("thanks", "Add a line of thanks", True) + _check("handover", "Offer to hand over my work", True) + "</div>"
              + _area("thanksFor", "What you are thankful for (optional)", 2, "the chance to lead the payments project", hint="Finish the sentence “…and in particular for …”.", show=' data-if="thanks"')
              + _area("handoverWhat", "What you can do before you leave (optional)", 2, "finish the release notes and write a handover guide for the billing work",
                      hint="Finish the sentence “Before my last day I can …”.", show=' data-if="handover"')
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("resignation-letter.txt", '<button class="btn ghost" type="button" data-print>Print</button>') + "</div>"),
         "How the letter is put together",
         "<p>The letter has up to five parts: the greeting, one sentence that says which job you are resigning from and gives your last working day, an optional line of thanks, an optional handover offer, and the sign-off. "
         "No reason for leaving is given: the letter is there to record the date, not to explain the decision.</p>"
         "<p>Dates are written out in full (“Monday, November 30, 2026”) so that the day cannot be misread. If you enter both the date of the letter and your last day, the line under the letter counts the days between them, "
         "so you can compare that with your notice period. The page does not know your contract or the rules where you work: the notice period you owe is the one in your contract, and it decides the date.</p>"
         "<p>Nothing is generated and nothing is sent. The text is assembled in your browser from the fields. Send it from your own email, or print and sign it if your employer asks for a letter on paper.</p>",
         [("What should a resignation letter include?",
           "That you are resigning, the job you are leaving and your last working day. A line of thanks and an offer to hand over your work are optional. Keep it to a few sentences: it is a record, not an explanation."),
          ("How much notice do I have to give?",
           "The notice period written in your employment contract, or the legal minimum where you work if the contract says nothing. This page does not know either, so check the contract before you set your last day. The last working day calculator on this site counts the date from the day you give notice."),
          ("Do I have to give a reason for resigning?",
           "This template leaves the reason out: it states the fact and the date. If your contract or your employer’s process asks for more, follow that, and say the rest in person."),
          ("Should I send the resignation by email or on paper?",
           "Follow what your contract or your employer’s process says; some ask for a signed letter. The builder gives you both forms: an email with a subject line, and a letter with the date at the top that you can print and sign.")],
         ["last-working-day", "reference-request-email", "compare-offers"], ["jobs/"])

    # ------------------------------------------------------------ 19. raise request email
    tool("raise-request-email", "seekers", "Raise request email",
         "Your pay now, the pay you want and two or three results become a clear email, with the raise shown in percent and per month.",
         "Ask for a Raise Email: Template Builder",
         "Write an email asking for a raise: current pay, the figure you want, your results and a market figure. Shows the raise in percent and per month. Private, free.",
         "Ask for a raise in writing, with the numbers worked out",
         "A request that says “I feel I deserve more” gives a manager nothing to take to the person who approves the budget. Enter your pay now, the pay you are asking for, two or three results and, "
         "if you have one, a market figure. You get an email that states the percent, and a board that shows what the raise comes to per month. It is a fill-in template, not AI.",
         wrap("raise-request-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _f("to", "Manager’s first name", "Dana", mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("title", "Your job title (optional)", "Support Team Lead", mode="")
              + _f("since", "When your pay last changed (optional)", "18 months ago", mode="", hint="For example: in March 2025, two years ago.")
              + _f("current", "Your pay now", "80,000")
              + _f("target", "The pay you are asking for", "88,000")
              + _sel("period", "Pay is per", [("year", "Year", True), ("month", "Month")])
              + _cur()
              + _area("achievements", "Two or three results, one per line", 4,
                      "Cut the average reply time from two days to nine hours\nTrained four new team members\nWrote the help articles that removed 200 tickets a week",
                      hint="What you delivered since your pay last changed, with a number where you have one.")
              + _f("market", "Market figure (optional)", "$85,000 to $92,000", mode="", hint="What similar jobs advertise: a number or a range.")
              + _f("source", "Where the figure comes from (optional)", f"advertised salaries for this role on {SITE}", mode="") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("raise-request-email.txt") + "</div>"
              + _board("The raise you are asking for", "Enter your current pay and the pay you are asking for to see the difference in percent and per month.")),
         "How the email and the figures are worked out",
         "<ul><li><code>raise in percent = (pay asked for − pay now) ÷ pay now × 100</code>, shown to one decimal place</li>"
         "<li><code>more per month = difference per year ÷ 12</code>, or the difference itself when you enter monthly pay</li></ul>"
         "<p>The email follows one order: the request, what you have delivered as a short list, the two figures with the percent, the market figure if you gave one, and a question that is easy to answer. "
         "If you list no results, a reminder in [brackets] takes their place. The tool does not suggest how much to ask for and does not know what your employer can pay: the figures and the final wording are yours. All amounts are before tax.</p>",
         [("How do I ask for a raise by email?",
           "State the request in the first line, list two or three results since your pay last changed, give your pay now and the figure you are asking for, and end by asking for a time to talk. Keep it short enough to read in a minute."),
          ("How much of a raise should I ask for?",
           "A figure you can back with evidence: your results, a job that has grown since you were hired, or what similar roles advertise. This tool works out the percent for the figure you enter; it does not pick the figure. The salary checker on this site shows what open postings advertise."),
          ("Should I mention what other companies pay?",
           "Yes, if you have a figure and can say where it comes from. One line with the market figure and its source is enough. The email puts it after your own results, so the request rests on your work first."),
          ("Is it better to ask in person?",
           "You can do both. The email puts the facts and the figure in writing and asks for a time to talk, so the request cannot be misremembered later.")],
         ["raise-calculator", "salary-checker", "negotiation-email"], ["salaries/"])

    # ------------------------------------------------------------ 20. reference request email
    tool("reference-request-email", "seekers", "Reference request email",
         "Ask a former manager or colleague to be your reference: how you worked together, the role and the date, in one of three tones.",
         "Reference Request Email Template Builder",
         "Write an email asking someone to be your job reference: how you worked together, the role you are applying for and the date. Three tones. Private, free.",
         "Ask someone to be your reference, and make it easy to say yes",
         "A reference who is called by an employer without warning has to answer from memory. Asking first, with the role and the date, lets the person prepare and gives them a polite way to decline. "
         "Enter who you are writing to, how you worked together, the job and the deadline, and you get an email in the tone you choose. It is a fill-in template, not AI.",
         wrap("reference-request-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _f("to", "Their first name", "Sam", mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job you are applying for (optional)", "Senior Backend Engineer", mode="")
              + _f("company", "Company (optional)", "Acme", mode="", auto="organization")
              + _sel("how", "What the employer asks for", [("call", "A phone call or an email", True), ("letter", "A written reference"), ("form", "An online form"), ("linkedin", "A LinkedIn recommendation")])
              + _f("by", "By when (optional)", "the end of next week", mode="", hint="For example: Friday, the 20th.")
              + _sel("tone", "Tone", [("warm", "Warm", True), ("formal", "Formal"), ("short", "Short")])
              + _area("relation", "How you worked together", 2, "you managed me on the payments team at Example Co from 2021 to 2023", hint="Finish the sentence “We worked together when …”.")
              + _area("points", "Points you would like them to mention (optional)", 3, "The payments rewrite I led in 2022\nHow I worked with the support team", hint="One per line, up to four.") + "</div>"
              + '<div class="tl-checks">' + _check("attach", "I will attach my resume and the job description", True) + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("reference-request-email.txt") + "</div>"),
         "How the email is put together",
         "<p>The email has the same order in every tone: what you are applying for and the request, how you know each other, what the employer will ask of the person and by when, "
         "optional points that matter for this job, and a sentence that makes it easy to decline. The first line of the output is the subject.</p>"
         "<p>“Warm” suits someone you know well, “formal” a former manager you have not spoken to for a while or a professor, “short” a close colleague. Fields you leave empty drop their sentences. "
         "The text is assembled in your browser, and you send it yourself.</p>",
         [("Who should I ask to be a reference?",
           "Someone who saw your work closely and can describe it: a former manager first, then a senior colleague, a client or a teacher. Ask before you give their name to an employer."),
          ("When should I ask for a reference?",
           "Before you hand over the person’s name, and with enough time for them to prepare. The email names the date so they can see whether it fits their calendar."),
          ("What should I send with the request?",
           "Your current resume and the job description, plus two or three points that matter for this job. A reference who knows what the employer is looking for can give examples that fit."),
          ("What if the person says no?",
           "Thank them and ask someone else. The template ends with a line that makes declining easy, because you want a reference from someone who is glad to give one.")],
         ["thank-you-email", "resignation-letter", "cover-letter"], ["resume/"])

    # ------------------------------------------------------------ 21. LinkedIn headline and About
    tool("linkedin-headline", "seekers", "LinkedIn headline and About builder",
         "Role, years, three strengths and what you want next become three headlines inside the 220-character limit and a short About text.",
         "LinkedIn Headline & About Section Builder",
         "Build three LinkedIn headlines within the 220-character limit and a short About paragraph from your role, years, strengths and goal. Live character count.",
         "Write a LinkedIn headline that says what you do",
         "The headline is the line that appears next to your name in LinkedIn search results, comments and messages, and LinkedIn cuts it at 220 characters. Left alone, it repeats your current job title. "
         "Enter your role, your years of experience, three strengths and what you want next. You get three headlines with a character count that updates as you type, and a short About paragraph to edit. "
         "These are fill-in templates, not AI.",
         wrap("linkedin-headline",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("role", "Your job title", "Senior Backend Engineer", mode="")
              + _f("years", "Years of experience (optional)", "8", mode="text")
              + _f("strengths", "Your three strongest skills or fields", "Python, PostgreSQL, payments", mode="", hint="Separate them with commas.")
              + _f("next", "What you want next (optional)", "senior backend roles at product companies", mode="", hint="Finish the sentence “I am now looking for …”.")
              + _area("result", "One result you are proud of (optional)", 2, "I cut page load time from 4 s to 1.2 s for two million monthly users.", hint="A full sentence starting with “I”. It goes into the About text.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _private(" The texts are assembled inside your browser and are never sent to LinkedIn or anywhere else.")
              + '<div class="tl-out3" aria-live="polite">' + vcard(1, "Headline 1") + vcard(2, "Headline 2") + vcard(3, "Headline 3") + vcard(4, "About paragraph") + "</div>"),
         "How the headlines and the About text are built",
         "<ul><li><strong>Keywords:</strong> your title and your strengths separated by bars, the form that is quickest to scan in a list of search results.</li>"
         "<li><strong>One sentence:</strong> your title, your years of experience and your strengths as a plain sentence.</li>"
         "<li><strong>What you want next:</strong> your title, your strengths and “Open to …” with the goal you typed.</li></ul>"
         "<p>LinkedIn allows 220 characters in a headline and 2,600 in the About section. The count under each text updates as you type. A headline that would run over the limit loses strengths from the end until it fits, "
         "and is cut at a word only as a last resort. Variants that come out identical are shown once.</p>"
         "<p>The About paragraph is built from the same fields in a fixed order: who you are, your strengths, one result, what you are looking for, how to reach you. It is a starting point of a few sentences, "
         "so add the story only you can tell. No AI is involved, and nothing is sent to LinkedIn or anywhere else.</p>",
         [("How long can a LinkedIn headline be?",
           "220 characters, including spaces. The builder counts the characters of each variant as you type and keeps every variant inside the limit."),
          ("What should a LinkedIn headline say?",
           "Your role and what you are good at, in words a recruiter would type into search: the job title, two or three skills or fields and, if you are looking, what you are open to. “Open to work” alone says nothing about what you do."),
          ("How long should the About section be?",
           "LinkedIn accepts up to 2,600 characters, but only the opening lines show before a reader has to click “see more”. Put what you do and for whom in the first two sentences; the builder’s paragraph starts with exactly that."),
          ("Will these headlines get me more profile views?",
           "This page cannot promise that. It gives you three clear ways to say what you do inside LinkedIn’s limit. How often a profile is found also depends on your experience, your network and what recruiters search for.")],
         ["linkedin-review", "resume-bullet-builder", "cover-letter"], ["resume/"])

    # ------------------------------------------------------------ 22. interview answer (STAR)
    star = lambda k, label, rows, ph, hint: _area(k, label, rows, ph, hint=hint, ex=EX_STAR[k])
    tool("interview-answer-builder", "seekers", "Interview answer builder",
         "Situation, task, action, result: build a 60 to 90 second answer and check its length, its numbers and whether it says “I”.",
         "STAR Interview Answer Builder with Timing",
         "Build an interview answer with the STAR method: situation, task, action, result. See the speaking time and checks for a number and for “I”. Free, private.",
         "Build an interview answer that takes 60 to 90 seconds",
         "“Tell me about a time when…” invites a long story, and a long story can lose the listener before it reaches the result. The STAR method keeps it in order: situation, task, action, result. "
         "Type each part. The page puts the answer together, estimates how long it takes to say at 140 words a minute, and checks that the result has a number and that the action says what you did yourself.",
         wrap("interview-answer-builder",
              '<div class="tl-split"><div class="card tl-form">'
              + _f("question", "The question (optional)", "Tell me about a time you solved a problem", mode="")
              + star("situation", "Situation: where and when", 3, "Where you were and what was going on", "Two or three sentences of background.")
              + star("task", "Task: what was yours to do", 2, "What you were asked to do, or the problem you had to solve", "One sentence.")
              + star("action", "Action: what you did", 5, "What you did yourself, step by step", "The longest part. Say “I”, not “we”.")
              + star("result", "Result: what changed", 2, "What was different afterwards", "With a number if you have one.")
              + star("learned", "What you learned (optional)", 2, "One sentence, if it adds something", "")
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("interview-answer.txt") + "</div>"
              + _board("Speaking time", "Describe the situation, the task, what you did and the result to see how long the answer takes to say.")
              + '<div class="tl-detail" id="tl-detail"></div>'),
         "How the answer is built and checked",
         "<p>The answer is your four parts in order, each as its own short paragraph: <strong>situation</strong> (where and when), <strong>task</strong> (what was yours to solve), "
         "<strong>action</strong> (what you did) and <strong>result</strong> (what changed). A fifth line, what you learned, is optional. The page does not rewrite your sentences.</p>"
         "<ul><li><strong>Speaking time</strong> = words ÷ 140 × 60 seconds. 140 words a minute is a calm speaking pace; yours may be faster or slower, so time yourself once.</li>"
         "<li><strong>Length:</strong> 60 to 90 seconds passes. 45 to 59 and 91 to 120 seconds are marked to check; under 45 or over 120 seconds is marked to fix.</li>"
         "<li><strong>A number in the result:</strong> the result must contain a digit or a number word such as “half” or “twice”.</li>"
         "<li><strong>“I” in the action:</strong> the action must say “I” at least once, and “we” must not appear more often than “I”.</li>"
         "<li><strong>Balance:</strong> the situation and the task together should not be longer than the action.</li></ul>"
         "<p>The 60 to 90 second target and the other thresholds are this page’s rules of thumb, not a standard. Some questions deserve a longer answer: you can ask the interviewer whether they would like more detail.</p>",
         [("What is the STAR method?",
           "A way to answer interview questions that start with “Tell me about a time when…”. STAR stands for situation, task, action and result: you describe where you were, what you had to do, what you did yourself and what changed because of it."),
          ("How long should a STAR answer be?",
           "This page aims for 60 to 90 seconds, which is about 140 to 210 words at a calm speaking pace. That is a rule of thumb: long enough for the detail, short enough to leave room for follow-up questions."),
          ("Why does the checker ask for “I” instead of “we”?",
           "Because the interviewer is trying to learn what you did. “We shipped the project” leaves your part unclear; “I wrote the plan and ran the weekly review” does not. Keep “we” for the situation and use “I” for the action."),
          ("What if my result has no number?",
           "Then say what was different afterwards in a way someone could check: a deadline met, a complaint that stopped, a process other teams copied. A number is the easiest proof to remember, but it is not the only one.")],
         ["thank-you-email", "resume-bullet-builder", "cover-letter"], ["for-you/"])

    # ------------------------------------------------------------ 23. resume bullet point
    tool("resume-bullet-builder", "seekers", "Resume bullet point builder",
         "A verb, what you did and the result become one resume line in up to three variants, checked for a strong verb, a number and length.",
         "Resume Bullet Point Builder: Verb + Result",
         "Turn a verb, what you did and the result into resume bullet points. Checks for a strong action verb, a number, length and “responsible for”. Free, private.",
         "Turn “responsible for” into a resume line that shows a result",
         "“Responsible for the checkout page” tells a recruiter what your job was, not what you did in it. A bullet point that starts with an action and ends with a result says both in one line. "
         "Enter the verb, what you did and what changed. You get the line in up to three variants, each with its length, and a check for a strong verb, a number and duty wording.",
         wrap("resume-bullet-builder",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("verb", "Action verb, in the past tense", "Rebuilt", mode="", hint="For example: Built, Led, Cut, Launched, Negotiated.")
              + _f("what", "What you did", "the checkout flow in React", mode="", hint="What you built, led, changed or sold.")
              + _f("result", "The result", "cut failed payments by 30%", mode="", hint="Start with a past-tense verb and add a number: cut…, saved…, raised…, won…") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Bullet point check", "Type a verb, what you did and the result to build the line.")
              + '<div class="tl-out3" aria-live="polite">' + vcard(1, "Variant 1") + vcard(2, "Variant 2") + vcard(3, "Variant 3") + "</div>"
              + '<div class="tl-detail" id="tl-detail"></div>'
              + '<div class="tl-out3"><div class="card"><p class="tl-t">Verbs this page counts as strong</p><p class="note" id="tl-verbs"></p></div></div>'),
         "How the line is built and checked",
         "<p>The line is built as <code>verb + what you did + result</code>. When the result starts with a past-tense verb (“cut failed payments by 30%”), you get three variants: action first (“…, which cut…”), "
         "short (“… and cut…”) and result first (“Cut … by rebuilding …”). The “-ing” form for the result-first variant comes from a list for irregular verbs (built, building) and from the ending for regular ones. "
         "A result written another way is joined with a colon or a semicolon.</p>"
         "<p>The checks are run on the first variant:</p><ul>"
         "<li><strong>Strong verb:</strong> the first word is on our list of past-tense action verbs, shown under the tool. “Responsible”, “helped”, “worked” and similar openers are marked to fix. A verb that is on neither list is left to your judgment.</li>"
         "<li><strong>Number:</strong> the line contains a digit or a number word such as “half” or “doubled”.</li>"
         "<li><strong>Length:</strong> 40 to 200 characters. We count about 100 characters to one line of a one-column resume, so 200 is two lines. That figure is an estimate; your font and margins change it.</li>"
         "<li><strong>Duty wording:</strong> “responsible for”, “duties included”, “tasked with”, “in charge of”, “helped with”, “worked on”, “assisted with”, “participated in” and “involved in” must not appear.</li></ul>"
         "<p>The verb list and the thresholds are ours, not an industry standard. The page arranges your words. It does not invent results, so write only what is true.</p>",
         [("What makes a good resume bullet point?",
           "It starts with a verb that says what you did, names the thing you worked on, and ends with what changed, with a number where you have one. One to two lines is enough."),
          ("What can I write instead of “responsible for”?",
           "The action itself. “Responsible for the checkout page” becomes “Rebuilt the checkout page” or “Ran the checkout page for 2 million users”. If you led people, write “Led” or “Managed” and give the size of the team."),
          ("What if I have no numbers?",
           "Use a count you do know: the size of the team, the number of customers, how often something happened, how long it took. If nothing was measured, describe the change: what people could do afterwards that they could not do before."),
          ("How many bullet points should each job have?",
           "As a rule of thumb, three to five for recent jobs and one or two for older ones. Put the line with the strongest result first: a reader who skims sees the first line under each job title.")],
         ["resume-review", "resume-match", "linkedin-headline"], ["resume/"])

    # ------------------------------------------------------------ 24. job search funnel
    tool("job-search-calculator", "seekers", "Job search calculator",
         "Applications a week and your own reply and offer rates give the interviews and offers to expect, and the applications one offer takes.",
         "Job Search Calculator: Applications per Offer",
         "Enter applications a week and your own reply and offer rates to see expected interviews and offers, and how many applications one offer takes. Free, private.",
         "See how many applications one job offer takes at your rates",
         "A job search works like a funnel: many applications go in, fewer turn into interviews, fewer still into offers. Without the numbers it is hard to tell whether to send more applications "
         "or to change what you send. Enter how many you send a week and your own two rates: how often an application leads to an interview, and how often an interview leads to an offer. "
         "You see the interviews and offers to expect and how many applications one offer takes. The rates are yours; this page has no statistics about other people’s searches.",
         wrap("job-search-calculator",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("perWeek", "Applications you send a week", "10")
              + _f("weeks", "Weeks to look ahead", val="8")
              + _f("reply", "Applications that lead to an interview", "3 of 40", mode="text", hint="A percent, or your own count so far: “3 of 40”.")
              + _f("offer", "Interviews that lead to an offer", "1 of 5", mode="text", hint="A percent, or your own count: “1 of 5”. Count first interviews.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Applications for one offer", "Enter how many applications you send a week and your own two rates.")
              + '<p class="note tl-priv"><b>Your own rates</b>The result is arithmetic on the numbers you type. It is not a statistic about the job market and not a forecast of your search. Nothing you type leaves your browser.</p>'),
         "How the figures are calculated",
         "<ul><li><code>interviews = applications × share that lead to an interview</code></li>"
         "<li><code>offers = interviews × share that lead to an offer</code></li>"
         "<li><code>applications for one offer = 1 ÷ (first share × second share)</code></li>"
         "<li><code>weeks to one offer = applications for one offer ÷ applications a week</code></li>"
         "<li><code>chance of at least one offer = 1 − (1 − first share × second share) ^ applications</code>, which treats every application as having the same odds, independent of the others</li></ul>"
         "<p>A rate typed as “3 of 40” is turned into a percent: 3 ÷ 40 = 7.5%. The results are averages: an expected 1.2 offers means that many searches at these rates would average 1.2, not that you will get exactly one. "
         "Rates worked out from a handful of applications are rough, and they move when you change your resume or the jobs you pick, so update them as you go. "
         "The page uses only the numbers you type; it holds no data about typical reply rates.</p>",
         [("How many applications does it take to get a job offer?",
           "It depends on two rates that differ from person to person: how many of your applications lead to an interview, and how many of your interviews lead to an offer. Divide 1 by the product of the two. At 7.5% and 20% that is 1 ÷ (0.075 × 0.2), about 67 applications."),
          ("How do I find my own rates?",
           "Count what has happened so far. Interviews divided by applications is the first rate; offers divided by first interviews is the second. You can type the counts directly, for example “3 of 40”. With fewer than about 20 applications the figure is rough."),
          ("Should I just send more applications?",
           "More applications bring more interviews only if the rate stays the same. If very few of your applications get a reply, look at the resume and at which jobs you pick as well: doubling the reply rate has the same effect on the result as doubling the number of applications."),
          ("Is this a prediction of my job search?",
           "No. It is arithmetic on your own numbers, and it assumes the future looks like your past. It cannot know the job market, the season or how well each job fits you.")],
         ["resume-review", "resume-match", "interview-answer-builder"], ["for-you/", "jobs/"])

    # ------------------------------------------------------------ 25. remote work savings
    tool("remote-work-savings", "seekers", "Remote work savings calculator",
         "Your commute, what an office day costs and how many days you go in give the hours and money a year that working from home saves.",
         "Remote Work Savings Calculator (Time & Money)",
         "Work out the hours and money a year you save by working from home: commute time, travel cost, lunches and office days a week. Your own figures. Free.",
         "Count the hours and money a year that working from home saves",
         "Each day at the office costs travel time and money that never appear on a payslip. Over a year that adds up, which matters when you compare a remote job with an office job, "
         "or when an employer asks you to come in more often. Enter your travel time one way, what an office day costs and how many days you go in now and after the change. "
         "You get the hours and the money per year. Every figure is your own; the page assumes no prices.",
         wrap("remote-work-savings",
              '<div class="card tl-form"><p class="tl-t">A day at the office</p><div class="tl-grid">'
              + _f("minutes", "Travel one way, minutes", "45")
              + _f("cost", "Travel cost per office day", "12", hint="Tickets, fuel and parking, there and back.")
              + _f("lunch", "Lunch and coffee per office day", "14")
              + _cur() + '</div><p class="tl-t">A day at home</p><div class="tl-grid">'
              + _f("lunchHome", "Lunch at home per day (optional)", "5")
              + _f("home", "Extra cost of a day at home (optional)", "2", hint="Heating, electricity, a larger internet plan.")
              + _f("hourly", "What an hour of your time is worth (optional)", "30", hint="For example your hourly pay. Used only to put a price on the travel time.")
              + '</div><p class="tl-t">How often</p><div class="tl-grid c2">'
              + _f("daysNow", "Office days a week now", val="5") + _f("daysNew", "Office days a week after the change", val="0")
              + _f("weeks", "Working weeks a year", val="46", hint="52 minus your vacation and public holidays.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Saved by working from home", "Enter your commute and what a day at the office costs you.")),
         "How the saving is calculated",
         "<ul><li><code>office days avoided a year = (office days a week now − office days a week after) × working weeks a year</code></li>"
         "<li><code>hours saved = office days avoided × minutes one way × 2 ÷ 60</code></li>"
         "<li><code>money saved = office days avoided × (travel cost + lunch at the office − lunch at home − extra cost of a day at home)</code></li>"
         "<li><code>travel time in money = hours saved × what an hour of your time is worth</code>, shown only if you enter that figure</li></ul>"
         "<p>The 46 working weeks in the form are a starting value, 52 weeks minus six weeks of vacation and public holidays: change it to your own. If the office days go up instead of down, "
         "the same arithmetic shows what the change costs. Tax is not part of the calculation; in some countries commuting or home-office costs can be deducted, which this page does not know about.</p>",
         [("How much time does working from home save?",
           "Your travel time there and back, multiplied by the office days you no longer have. A 45-minute commute each way, five days a week for 46 weeks, is 345 hours a year, more than eight working weeks of 40 hours."),
          ("How much money does working from home save?",
           "What each office day costs you, minus what a day at home costs. Travel and bought lunches are on one side; heating and electricity at home are on the other. The calculator uses your own figure for each."),
          ("Can I use this to compare a remote job with an office job?",
           "Yes. Work out the yearly saving, then count it in when you compare the two offers. The job offer comparison tool on this site has a field for commute cost."),
          ("Does it work for a return to the office?",
           "Yes. Enter the smaller number of office days under “now” and the larger one under “after the change”. The result then shows the extra hours and money per year that the change costs you.")],
         ["compare-offers", "time-zone-overlap", "salary-converter"], ["remote/"])

    # ------------------------------------------------------------ 26. last working day
    tool("last-working-day", "seekers", "Last working day calculator",
         "The day you give notice and your notice period in weeks, months or working days give your last working day, with weekends skipped.",
         "Last Working Day Calculator by Notice Period",
         "Enter the day you give notice and your notice period in weeks, months or working days to get your last working day. Weekends skipped; holidays are not known.",
         "Find your last working day from your notice period",
         "“Two weeks’ notice” sounds simple until you count it on a calendar: the day you hand it in, the weekends and the way your contract counts can each move the date. "
         "Enter the day you give notice and the length of the notice period. You get the day the notice ends and the last Monday-to-Friday on or before it. "
         "Public holidays are not known to this page, and your contract decides how notice is counted.",
         wrap("last-working-day",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("date", "Day you give notice", typ="date", mode="")
              + _f("amount", "Notice period", "2")
              + _sel("unit", "Counted in", [("weeks", "Weeks", True), ("months", "Months"), ("workdays", "Working days (Monday to Friday)"), ("days", "Calendar days")])
              + _sel("from", "The period starts", [("next", "The day after you give notice", True), ("same", "The day you give notice")], hint="Contracts differ. If yours does not say, ask.") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Your last working day", "Enter the length of your notice period.")
              + '<p class="note tl-priv"><b>Holidays</b>Public holidays are not known to this page, because they differ by country, region and employer. Check a calendar for the period shown. This is date arithmetic, not legal advice.</p>'),
         "How the date is counted",
         "<ul><li><strong>Weeks and calendar days:</strong> the notice ends that many days after it starts. Two weeks from a Monday, starting the next day, end on the Monday two weeks later.</li>"
         "<li><strong>Months:</strong> the notice ends on the same day of the month, that many months later. If that month is shorter, it ends on its last day: one month from January 31 ends on the last day of February.</li>"
         "<li><strong>Working days:</strong> Mondays to Fridays are counted one by one from the start of the period; Saturdays and Sundays are skipped.</li>"
         "<li><strong>Last working day:</strong> the day the notice ends, or the last Monday-to-Friday before it when it ends on a weekend.</li></ul>"
         "<p><strong>Public holidays are not known to this page.</strong> A holiday inside the period does not change the calendar date for weeks and months, but it shortens the days you actually work, "
         "and with a notice period counted in working days it can push the date later. The “working days left” are Mondays to Fridays with no holidays or vacation taken off. "
         "This is date arithmetic, not legal advice: how notice is counted, and whether it must end on a particular day such as the end of a month, is set by your contract and the law where you work.</p>",
         [("How do I count two weeks’ notice?",
           "Count 14 calendar days from the start of the notice period. If you give notice on a Monday and the period starts the next day, it ends on the Monday two weeks later, which leaves ten working days."),
          ("Does the day I give notice count?",
           "That depends on your contract and the rules where you work. A common way to count is from the day after notice is given, which is the setting this calculator starts with. Switch it to “the day you give notice” if yours counts that day as day one."),
          ("Are public holidays taken into account?",
           "No. The page does not know which holidays apply where you work. Check a calendar for the period it shows: a holiday reduces the days you work, and with a notice period counted in working days it can move the last day."),
          ("What if my notice ends on a weekend?",
           "The notice still ends on that date, but the last day you work is the Friday before, if you work Monday to Friday. The calculator shows both dates.")],
         ["resignation-letter", "compare-offers", "raise-calculator"], ["jobs/"])

    # ------------------------------------------------------------ 27. cost per hire
    tool("cost-per-hire", "employers", "Cost per hire calculator",
         "Advertising, agency fees, recruiter and interviewer hours, tools and the number of hires give the cost per hire and the share of each part.",
         "Cost per Hire Calculator with Cost Breakdown",
         "Calculate cost per hire: advertising, agency fees, recruiter and interviewer time, tools and other costs divided by hires, with the share of each part. Free.",
         "Work out what each hire costs, staff time included",
         "The invoice from a job board or an agency is the visible part of hiring. The hours your recruiters and interviewers spend have a cost too, and leaving them out makes each hire look cheaper than it was. "
         "Enter what you paid, the hours spent with what an hour of that time costs, and the number of people hired. You get the cost per hire and the share of each part.",
         wrap("cost-per-hire",
              '<div class="card tl-form"><p class="tl-t">Paid to others</p><div class="tl-grid">'
              + _f("ads", "Job advertising", "3,000", hint="Job boards, sponsored posts, social ads.")
              + _f("agency", "Agency and recruiter fees", "18,000")
              + _f("tools", "Tools and software", "2,400", hint="Hiring software, skills tests, video interviews.")
              + _f("other", "Other costs", "1,500", hint="Referral bonuses, background checks, travel, relocation.")
              + '</div><p class="tl-t">Your staff’s time</p><div class="tl-grid c2">'
              + _f("recHours", "Recruiter hours", "120") + _f("recRate", "Cost of a recruiter hour", "45")
              + _f("intHours", "Interviewer hours", "90") + _f("intRate", "Cost of an interviewer hour", "70")
              + '</div><p class="tl-t">The result</p><div class="tl-grid">'
              + _f("hires", "People hired", "6", hint="In the same period as the costs.") + _cur() + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Cost per hire", "Enter what the hiring cost and how many people were hired.")
              + '<div class="tl-detail" id="tl-table"></div>'),
         "How cost per hire is calculated",
         "<ul><li><code>cost per hire = total cost ÷ people hired</code></li>"
         "<li><code>total cost = advertising + agency fees + tools + other costs + recruiter hours × hourly cost + interviewer hours × hourly cost</code></li>"
         "<li><code>share of a part = that part ÷ total cost × 100</code></li></ul>"
         "<p>Use one period for everything, for example a quarter or a year: the costs of that period and the people hired in it. For the hourly cost of staff time, take salary plus employer-side costs "
         "and divide by the hours worked in a year; the salary converter on this site does that division. Hours entered without an hourly cost are not counted, and the page says so. "
         "The calculator holds no benchmark: what a hire costs depends on the role, the country and how you hire, so compare the result with your own earlier periods.</p>",
         [("How is cost per hire calculated?",
           "Add up everything spent on hiring in a period, both money paid to others and the time of your own staff, and divide by the number of people hired in that period. $36,600 spent to hire six people is $6,100 per hire."),
          ("Which costs belong in cost per hire?",
           "Money paid to others: job advertising, agency fees, software, background checks, referral bonuses, travel and relocation. And the time of your own people: recruiters, hiring managers and everyone who interviews, each at what an hour of their time costs the company."),
          ("How do I put a price on interviewers’ time?",
           "Take the yearly cost of the person, salary plus employer-side costs, and divide by the hours worked in a year (2,080 at 40 hours a week). Multiply by the hours spent on screening calls, interviews and debriefs."),
          ("What is a good cost per hire?",
           "There is no single figure, and this page does not quote one: it depends on the role, the seniority, the country and whether you use agencies. Compare with your own previous quarters, and look at the parts: the breakdown shows where the money goes.")],
         ["interview-scorecard", "job-description-checker", "boolean-search"], ["post-a-job/"])

    # ------------------------------------------------------------ 28. interview scorecard
    crit_ex = [("Technical skills", "30"), ("Problem solving", "25"), ("Communication", "20"), ("Teamwork", "15"), ("Motivation for the role", "10"), ("e.g. Leadership", "")]
    rate_ex = {"a": ["4", "5", "3", "4", "4", ""], "b": ["5", "3", "4", "3", "5", ""], "c": ["3", "4", "5", "5", "3", ""]}
    crit_rows = "".join('<div class="tl-pair">' + _f(f"c{i}", f"Criterion {i}", n_, mode="") + _f(f"w{i}", "Weight", w_) + "</div>" for i, (n_, w_) in enumerate(crit_ex, 1))
    def cand(p, letter):
        return (f'<div class="tl-col"><p class="tl-t">Candidate {letter}</p>' + _f(f"{p}_name", "Name", f"Candidate {letter}", mode="")
                + "".join(_f(f"{p}_r{i}", f"Criterion {i}", rate_ex[p][i - 1]) for i in range(1, 7)) + "</div>")
    tool("interview-scorecard", "employers", "Interview scorecard builder",
         "Name four to six criteria with weights: get a scorecard to print for each interviewer and a weighted score for up to three candidates.",
         "Interview Scorecard Builder: Weighted Scores",
         "Build an interview scorecard: four to six criteria with weights, a printable rating sheet and a weighted score for up to three candidates. Free, private.",
         "Score every candidate on the same criteria",
         "When each interviewer keeps their own notes, the debrief compares impressions that were never measured against the same list. A scorecard fixes the criteria and their weights before the first interview. "
         "Name four to six criteria for the role and give each a weight. You get a sheet to print for every interviewer, and a calculator that turns the ratings into one weighted score per candidate.",
         wrap("interview-scorecard",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("role", "Role you are hiring for", "Senior Backend Engineer", mode="")
              + _sel("max", "Rating scale", [("5", "1 to 5", True), ("4", "1 to 4, no middle"), ("10", "1 to 10")]) + "</div>"
              + '<p class="tl-t">Criteria and weights: the weights should add up to 100</p>' + crit_rows
              + '<p class="tl-t">Ratings for up to three candidates</p><div class="tl-cols">' + cand("a", "A") + cand("b", "B") + cand("c", "C") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div></div>"
              + _private(" Names and ratings are added up inside your browser and are never sent anywhere.")
              + '<div class="tl-noprint">' + _board("Weighted score", "Name four to six criteria, give each a weight, then rate each candidate.") + '<div class="tl-detail" id="tl-table"></div></div>'
              + '<div class="tl-out3"><div class="card tl-sheet"><div id="tl-sheet"></div><pre id="tl-text" hidden></pre>'
                '<div class="tl-actions tl-noprint"><span class="note">Print one sheet per interviewer and candidate.</span><span><button class="btn" type="button" data-print>Print the scorecard</button> '
                '<button class="btn ghost" type="button" data-copy="tl-text">Copy as text</button></span></div></div></div>'),
         "How the weighted score is calculated",
         "<ul><li><code>weighted score = sum of (rating × weight) ÷ sum of weights</code></li>"
         "<li>With weights of 30, 25, 20, 15 and 10 and ratings of 4, 5, 3, 4 and 4, that is (120 + 125 + 60 + 60 + 40) ÷ 100 = 4.05 out of 5.</li>"
         "<li>Weights that do not add up to 100 still work: each counts as its share of the total. With no weights at all, every criterion counts the same.</li>"
         "<li>A candidate’s score is final once every weighted criterion has a rating; until then it is shown as “so far”. Ratings outside the scale are left out, and a note says how many.</li></ul>"
         "<p>The scale on the printed sheet reads: 1 is well below what the role needs, the middle value meets it, the top value is well above. The four-point scale has no middle on purpose, so the interviewer has to lean one way. "
         "A scorecard puts everyone’s ratings on the same footing; it does not replace the discussion. Agree what a 3 and a 5 look like for each criterion before the first interview, "
         "and have each interviewer fill in the sheet before the debrief.</p>",
         [("What is an interview scorecard?",
           "A one-page sheet that lists the criteria a role is judged on, each with a weight and a rating scale. Every interviewer rates every candidate on the same list, so the debrief compares like with like."),
          ("How many criteria should a scorecard have?",
           "Four to six is what this builder is made for: enough to cover skills, the way of working and motivation, few enough that an interviewer can rate each one with evidence. If a criterion is not something you would turn a candidate down for, leave it out."),
          ("How do I choose the weights?",
           "Give the most weight to what the person will do most of the time, and make the weights add up to 100 so each reads as a percent. Set them before you meet the first candidate; changing them afterwards to fit a favourite defeats the purpose."),
          ("How is the weighted score calculated?",
           "Multiply each rating by the weight of its criterion, add the results and divide by the sum of the weights. Ratings of 4, 5, 3, 4 and 4 with weights of 30, 25, 20, 15 and 10 give 4.05 out of 5.")],
         ["cost-per-hire", "job-description-checker", "boolean-search"], ["post-a-job/"])

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
        sub = (f'<nav class="tsub" aria-label="{"Tools for people hiring" if t["group"] == "employers" else "Tools for job seekers"}"><a class="all" href="{P}/tools/">All tools</a>'
               + "".join(f'<a href="{P}/tools/{o["slug"]}/"' + (' aria-current="page"' if o is t else "") + f'>{e(o["name"])}</a>' for o in TOOLS if o["group"] == t["group"]) + "</nav>")
        body = (crumbs(("Tools", "tools/"), (t["name"], "")) + sub + f'<h1>{e(t["h1"])}</h1><p class="lead">{e(t["lead"])}</p>' + t["html"]
                + '<div class="tl-after">' + extra
                + section(t["how_title"], f'<div class="tl-how">{t["how"]}</div>')
                + section(f"Questions about the {t['name'][0].lower() + t['name'][1:]}", faq_html)
                + section("Related tools", cards(related), ("tools/", "All free tools")) + "</div>")
        page(path, t["title"], t["desc"], body, head=assets + app_ld + faq_ld + crumbs_ld([("Tools", "tools/"), (t["name"], "")]))

    # ------------------------------------------------------------ tiles
    # Each tile carries a small screen that shows what the tool gives back. The salary screen uses today's real figures;
    # the others are worked examples (the arithmetic in them is exact) and say so.
    mids = sorted((j["usd"][0] + j["usd"][1]) / 2 for j in jobs if j.get("usd"))
    kmoney = lambda v: f"${v / 1000:,.0f}K"
    ex = '<span class="ex">example</span>'
    PREV = {
        "job-description-keywords": ex + '<span class="big">14<small>keywords</small></span><span class="ln"><b>Python, SQL, Airflow</b> · “data pipelines” ×4</span>',
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
    # worked examples for the tools added later; each repeats the figures its own "Show an example" button gives (tools_test.js checks them)
    monday = today + datetime.timedelta(days=(7 - today.weekday()) % 7 or 7)             # the next Monday, so the dated examples never look stale
    dshort = lambda d: f"{MONTHS[d.month - 1]} {d.day}"
    leave = monday + datetime.timedelta(days=14)
    li_head = "Senior Backend Engineer | Python | PostgreSQL | payments"
    PREV.update({
        "resume-review": ex + '<span class="big">2<small>out of 10</small></span><span class="mt"><i style="width:20%"></i></span>'
                              '<span class="ln">5 lines describe duties: “<b>Responsible for</b> the backend…”</span>',
        "linkedin-review": ex + '<span class="ln">“<b>OPEN TO WORK</b> | Passionate, results-driven guru”</span><span class="big">10<small>things to fix</small></span>'
                                '<span class="ln">Says only that you are looking · 3 buzzwords · no contact line</span>',
        "thank-you-email": ex + '<span class="ln"><b>Subject:</b> Thank you for the interview</span><span class="sk" style="width:94%"></span>'
                                '<span class="ln">“I enjoyed hearing about <b>the move to weekly releases</b>”</span><span class="sk" style="width:52%"></span>',
        "resignation-letter": ex + '<span class="ln"><b>Dear Dana,</b></span><span class="sk" style="width:95%"></span>'
                                   f'<span class="ln">My last working day will be <b>Monday, {dshort(leave)}</b></span><span class="sk" style="width:72%"></span><span class="sk" style="width:34%"></span>',
        "raise-request-email": ex + '<span class="ln"><b>Subject:</b> Request to review my pay</span><span class="sk" style="width:88%"></span>'
                                    '<span class="ln">$80,000 to $88,000: <b>+10%</b>, about <b>$667</b> more a month</span><span class="sk" style="width:46%"></span>',
        "reference-request-email": ex + '<span class="ln"><b>Subject:</b> Could you be a reference for me?</span><span class="sk" style="width:92%"></span><span class="sk h" style="width:58%"></span>'
                                        '<span class="ln">The employer may contact you <b>before the end of next week</b></span>',
        "linkedin-headline": ex + f'<span class="ln"><b>{li_head}</b></span><span class="mt"><i style="width:{round(100 * len(li_head) / 220)}%"></i></span>'
                                  f'<span class="ln"><b>{len(li_head)}</b> of 220 characters</span>',
        "interview-answer-builder": ex + '<span class="big">1 min 4 s<small>said aloud</small></span><span class="mt"><i style="left:40%;width:20%"></i><u style="left:43%"></u></span>'
                                         '<span class="ln"><b>149 words</b> · a number in the result · “I” in the action</span>',
        "resume-bullet-builder": ex + '<span class="ln"><b>Rebuilt</b> the checkout flow in React, which <b>cut failed payments by 30%</b></span><span class="mt"><i style="width:100%"></i></span>'
                                      '<span class="ln"><b>4 of 4</b> checks: strong verb, number, length, wording</span>',
        "job-search-calculator": ex + '<span class="ln">10 applications a week · 3 of 40 lead to an interview</span><span class="big">67<small>applications per offer</small></span>'
                                      '<span class="ln"><b>6 interviews</b> and <b>1.2 offers</b> expected in 8 weeks</span>',
        "remote-work-savings": ex + '<span class="ln">45 minutes each way · 5 office days a week</span><span class="big">345<small>hours a year</small></span>'
                                    '<span class="ln"><b>$4,370</b> a year kept on travel and lunches</span>',
        "last-working-day": ex + f'<span class="ln">Notice given Monday, {dshort(monday)} · 2 weeks</span><span class="big">{dshort(leave)}<small>last working day</small></span>'
                                 '<span class="ln"><b>10 working days</b> left · weekends skipped</span>',
        "cost-per-hire": ex + '<span class="big">$6,100<small>per hire</small></span><span class="rw"><span>Agency</span><span class="mt"><i style="width:49%"></i></span><b>49%</b></span>'
                              '<span class="rw"><span>Staff time</span><span class="mt"><i style="width:32%"></i></span><b>32%</b></span>',
        "interview-scorecard": ex + '<span class="ln">Five criteria, weights add up to 100</span><span class="big">4.05<small>out of 5, weighted</small></span>'
                                    '<span class="ln">Candidate A <b>4.05</b> · B <b>4.00</b> · C <b>3.95</b></span>',
    })
    g_all = groups.get("||")
    if g_all:                                                   # the market figures are today's; only the offer is made up
        med, p25, p75, p10, p90 = (g_all[3 + QS.index(q_)] for q_ in (50, 25, 75, 10, 90))
        offer = round(med * 0.84)
        at = lambda v: max(0, min(100, 100 * (v - p10) / max(p90 - p10, 1)))
        PREV["offer-check"] = (ex + f'<span class="ln">An offer of ${offer}K against {g_all[0]:,} postings</span>'
                               f'<span class="big">−{round((med - offer) / med * 100)}%<small>against the median</small></span>'
                               f'<span class="mt"><i style="left:{at(p25):.0f}%;width:{at(p75) - at(p25):.0f}%"></i><u style="left:{at(offer):.0f}%"></u></span>'
                               f'<span class="ln">Median <b>${med}K</b> · middle half ${p25}K to ${p75}K</span>')
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
        "job-description-keywords": "14 keywords · Python, SQL, Airflow",
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
        return '<div class="tgrid">' + "".join(TILES[f"tools/{t['slug']}/"] for t in TOOLS if t["group"] == key) + "</div>"
    # job-seeker tools stand in the order of a search: the resume, applying, the offer, leaving. A tool that is not named here still appears, in a last group.
    HUB = [("Resume and LinkedIn profile", ["resume-review", "resume-match", "job-description-keywords", "resume-bullet-builder", "linkedin-headline", "linkedin-review"]),
           ("Applying and interviews", ["cover-letter", "job-search-calculator", "interview-answer-builder", "thank-you-email", "reference-request-email"]),
           ("Pay and offers", ["salary-checker", "offer-check", "compare-offers", "negotiation-email", "raise-calculator", "raise-request-email", "salary-converter", "equity-calculator", "contractor-rate"]),
           ("Remote work and leaving a job", ["remote-work-savings", "time-zone-overlap", "resignation-letter", "last-working-day"])]
    named = {s_ for _, ss in HUB for s_ in ss}
    rest = [t["slug"] for t in TOOLS if t["group"] == "seekers" and t["slug"] not in named]
    grid = lambda slugs: '<div class="tgrid">' + "".join(TILES[f"tools/{s_}/"] for s_ in slugs if s_ in by_slug) + "</div>"
    seekers = "".join(section(h_, grid(ss)) for h_, ss in HUB) + (section("More for job seekers", grid(rest)) if rest else "")
    hub_faq = [("Are these tools free?", "Yes. Every tool on this page is free, needs no account and can be used as often as you like."),
               ("Do the tools store or upload what I type?",
                "No. All calculations and text checks run in your browser. What you type is saved only in this browser’s storage so a tool remembers it next time, and every tool has a Clear button that erases it."),
               ("Do the tools use AI?",
                "No. The calculators are plain arithmetic, the checkers count words and patterns, and the letter writers are fill-in templates. How each result is calculated is explained under the tool."),
               ("Where do the salary figures come from?",
                f"From the salary ranges that employers publish in their own job postings on this site: {n_paid:,} open roles with a yearly US-dollar range as of {DATE}. No surveys and no numbers submitted by users.")]
    faq_html, faq_ld = faq_block(hub_faq)
    n_seek, n_emp = sum(t["group"] == "seekers" for t in TOOLS), sum(t["group"] == "employers" for t in TOOLS)
    hub_desc = "Free tools for a job search and for hiring: resume builder and review, job matching, application tracker, salary and offer checks, letters, interview answers."
    list_ld = _ld({"@context": "https://schema.org", "@type": "ItemList", "name": f"Free tools on {SITE}", "numberOfItems": len(TOOLS),
                   "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": t["name"], "url": f"{FULL}/tools/{t['slug']}/"} for i, t in enumerate(TOOLS)]})
    page("tools/", "Free Tools for Tech Job Seekers & Recruiters" + brand, hub_desc,
         crumbs(("Tools", "")) + "<h1>Free tools for a tech job search and for hiring</h1>"
         f'<p class="lead">{len(TOOLS) + len(EXTRA)} tools, from a resume builder to pay calculators, for things that come up along the way: whether your pay is fair, how well a resume fits a posting, which of two offers is worth more, why a vacancy gets no replies. '
         f"They run in your browser with no account, and the salary figures come from the {n_paid:,} open postings here that publish a pay range.</p>"
         + section("Start here: resume, matching, tracking", '<div class="twides">' + "".join(wide(*TILE_TEXT[u]) for u in EXTRA) + "</div>")
         + section("Templates and examples to copy", '<div class="feats">'
                   f'<a class="feat" href="{P}/resume/examples/"><h3>Resume examples</h3><p>A written example for each kind of work, with the skills today’s postings name.</p></a>'
                   f'<a class="feat" href="{P}/cover-letter-examples/"><h3>Cover letter examples</h3><p>A letter for each kind of work that leads with results, ready to copy.</p></a>'
                   f'<a class="feat" href="{P}/resignation-letters/"><h3>Resignation letters</h3><p>Two weeks notice, effective immediately, by email and 15 more situations.</p></a>'
                   f'<a class="feat" href="{P}/resume-words/"><h3>Stronger resume words</h3><p>What to write instead of “managed”, “helped” or “responsible for”.</p></a>'
                   f'<a class="feat" href="{P}/how-to-become/"><h3>How to become…</h3><p>Skills, pay and jobs open to beginners, for people changing careers.</p></a>'
                   f'<a class="feat" href="{P}/job-descriptions/"><h3>Job description templates</h3><p>For employers: a template per role with what today’s postings ask and pay.</p></a>'
                   f'<a class="feat" href="{P}/map/"><h3>Jobs map</h3><p>Every city with open jobs on one map. Search a skill and see where it is hiring.</p></a>'
                   f'<a class="feat" href="{P}/vs/"><h3>Compared with other job sites</h3><p>Fair, sourced comparisons with Indeed, LinkedIn and others.</p></a></div>')
         + seekers
         + section("For employers and recruiters", group("employers"))
         + section("How these tools work", '<div class="feats">'
                   '<div class="feat"><h3>Nothing leaves your browser</h3><p>Every calculation and text check runs on your device. Nothing is uploaded, and “Clear” erases what a tool remembers.</p></div>'
                   f'<div class="feat"><h3>The salary figures have a source</h3><p>They come from {n_paid:,} open roles that publish a yearly US-dollar range. No figure is shown for fewer than {MIN_SAMPLE} postings.</p></div>'
                   '<div class="feat"><h3>The method is on the page</h3><p>Arithmetic and fill-in templates, not AI. Under each tool you can read how its result is calculated.</p></div></div>')
         + section("Questions about the tools", faq_html)
         + section("More on this site", cards([(u, SITE_PAGES[u][0], SITE_PAGES[u][1]) for u in ("jobs/", "salaries/", "resume/", "for-you/", "post-a-job/", "widgets/")])),
         head=assets + list_ld + faq_ld + crumbs_ld([("Tools", "")]))

    return [(f"tools/{t['slug']}/", t["name"], t["card"]) for t in TOOLS]
