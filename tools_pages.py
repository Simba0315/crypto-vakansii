"""Free tools section: the /tools/ hub and one page per tool.

build.py calls build_tools() and passes its own page helpers. The behavior of every tool lives in assets/tools.js
(pure functions tested under Node + page wiring) and the extra styles in assets/tools.css. Nothing here needs a server:
each tool runs in the visitor's browser, and the only data embedded in a page is a small set of salary aggregates.
Two tools read a data file instead: the salary checker loads data/salary-groups.json (1.1 MB of figures); "skills to put on a resume" by job title loads data/role-skills.json, which build.py writes from the day's postings.
"""
import datetime, json
import state_tax                        # state income tax on wages: figures, sources and the sum (take-home pay pages)
from collections import defaultdict
from html import escape as _e

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
MONTHS_LONG = "January February March April May June July August September October November December".split()
EXTRA = ["resume/", "for-you/", "my-jobs/"]                             # the three big tools that live on their own pages: shown first, on the hub and on the home page
DATA_FILES = {}                                                        # data file path -> text, filled by build_tools() and written by build.py
TILES = {}                                                             # page path -> ready tile, filled by build_tools() so the home page can show the same tiles
MIN_SAMPLE = 20                                                       # no salary figure is shown for fewer postings than this
QS = [0, 5, 10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90, 95, 100]      # percentile points embedded for the salary checker
LEVELS = [("", "Any level"), ("Intern", "Intern"), ("Junior", "Junior"), ("none", "No level in the title"), ("Senior", "Senior"), ("Lead", "Lead and above")]


# ---------------------------------------------------------------- figures for the tables printed on tool pages

FED_2026 = {"single": (16100, [(12400, .10), (50400, .12), (105700, .22), (201775, .24), (256225, .32), (640600, .35), (None, .37)], 200000),
            "joint": (32200, [(24800, .10), (100800, .12), (211400, .22), (403550, .24), (512450, .32), (768700, .35), (None, .37)], 250000)}


def take_home_2026(salary, status="single"):
    """(federal income tax, Social Security, Medicare, take-home) for a US salary in 2026, with no pre-tax contributions: the same
    brackets, standard deduction and wage base the take-home pay page states and assets/tools.js uses."""
    std, br, extra_from = FED_2026[status]
    taxable, tax, lo = max(0, salary - std), 0.0, 0
    for hi, rate in br:
        top = taxable if hi is None else min(taxable, hi)
        if top > lo: tax += (top - lo) * rate
        if hi is None or taxable <= hi: break
        lo = hi
    ss = min(salary, 184500) * .062
    med = salary * .0145 + max(0, salary - extra_from) * .009
    return tax, ss, med, salary - tax - ss - med


assert round(take_home_2026(75000)[3]) in (61592, 61593) and round(take_home_2026(100000)[3]) == 79180       # the two answers printed in the page's questions


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


def _area(k, label, rows, ph="", hint="", cls="full", tall=False, show="", ex="", file=False):
    """`ex` is the text the "Show an example" button puts in; without it the placeholder is used when it is itself an example.
    `file`: a button that reads a PDF, Word or text file into the box, in the browser (site.js); the file is never uploaded."""
    return (f'<div class="tl-f{" " + cls if cls else ""}"{show}><label class="tl-l" for="tl-{k}">{label}</label>'
            + (f'<p class="tl-file"><label class="btn ghost sm" style="margin:0 0 8px">Open a PDF or Word file<input type="file" accept=".pdf,.docx,.txt" data-into="tl-{k}" hidden></label> '
               '<span class="tl-fmsg note">Read in your browser; the file is never uploaded.</span></p>' if file else "")
            + f'<textarea id="tl-{k}" data-k="{k}" rows="{rows}"{" class=" + chr(34) + "tl-tall" + chr(34) if tall else ""}' + (f' placeholder="{_e(ph)}"' if ph else "")
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


# What each of the tools added on 17 Nov 2026 gives for its own sample details ("Show an example"), printed in the page text as a worked example.
# tools_test.js reads the built pages, fills the form the way the button does and checks that the tool returns exactly these texts.
EXAMPLE = {
    "follow-up-email": ("Subject: Following up on my application for Senior Backend Engineer\n\n"
                        "Hi Dana,\n\n"
                        "I applied for the Senior Backend Engineer role at Acme on 4 November, and I am writing to make sure my application reached you.\n\n"
                        "I am still very interested in the job. Since we were last in touch, I finished the cloud certificate the posting asks for.\n\n"
                        "Could you tell me when you expect to choose people to interview? If anything is missing from my application, I can send it today.\n\n"
                        "Thank you for your time,\nAlex Morgan"),
    "application-email": ("Subject: Referred by Sam Ortiz: Marketing Manager application\n\n"
                          "Dear Dana Lee,\n\n"
                          "Sam Ortiz suggested I apply for the Marketing Manager role at Acme and told me you are the person to write to. My resume is attached. Examples of my work: alexmorgan.example/work\n\n"
                          "In short: I am a marketing manager with 6 years of experience. Last year I grew newsletter sign-ups from 8,000 to 31,000.\n\n"
                          "I have used your scheduling app with two teams, and I know why people stay with it.\n\n"
                          "I would be glad to talk whenever suits you. You can reach me at alex@example.com.\n\n"
                          "Best regards,\nAlex Morgan"),
    "referral-request": ("Subject: Could you refer me for a role at Acme?\n\n"
                         "Hi Sam,\n\n"
                         "Acme is hiring a Data Analyst, and I am going to apply. Would you be willing to refer me?\n\n"
                         "The posting: acme.example/jobs/data-analyst\n\n"
                         "You know my work from the three years we shared on the billing team at Example Co, so you can judge whether I would fit. I have built sales reports for two retailers, the work this role describes.\n\n"
                         "If you are happy to do it, I will send my resume and a few lines you can paste into the referral form, so it takes you five minutes. The posting closes on Friday, 27 November.\n\n"
                         "And if you would rather not, for any reason, just say so. It will not change anything between us.\n\n"
                         "Thanks,\nAlex Morgan"),
    "linkedin-connection-message": "Hi Dana, I am a product designer with six years in fintech. I saw that you recruit for Acme, and the Senior Product Designer role there fits what I do. I have led design for two payment apps. I would like to connect and send you my resume. Alex",
    "professional-bio": "I am a senior backend engineer at Acme with 8 years of experience in payment systems for online shops. My strongest areas are Python, PostgreSQL and system design. Recently, I rebuilt the checkout for two million shoppers and cut failed payments by 30%.",
    "professional-bio-one": "I am a senior backend engineer at Acme, working on payment systems for online shops.",
    "linkedin-summary": ("I am a senior backend engineer with 8 years of experience. I work with online shops that have outgrown their first payment system.\n\n"
                         "I like to start from the numbers the business already tracks and work back to the code.\n\n"
                         "I am at my best working on Python, PostgreSQL and payment systems.\n\n"
                         "What that has looked like in practice: I rebuilt the checkout for two million shoppers and cut failed payments by 30%. I moved 30 services to a new database with no downtime. I cut the monthly cloud bill from $41,000 to $27,000.\n\n"
                         "I am now looking for senior backend roles at product companies.\n\n"
                         "The quickest way to reach me is alex@example.com."),
    "elevator-pitch": "Hi, I’m Alex Morgan. I’m a data analyst with 4 years of experience. What I do best is turning messy sales data into reports people actually use. Recently I built a weekly report that replaced six spreadsheets and saves the team a day a week. I’m looking for an analyst role on a pricing team, which is why I came over to Acme. What do you look for in people who apply for that?",
    "elevator-pitch-n": "74 words, about 30 seconds at 150 words a minute.",
    "resume-summary": "Data analyst with 4 years of experience in SQL, Excel and Tableau. Cut month-end close from 8 days to 5 by automating reconciliations.",
    "resume-summary-2": "Data analyst who cut month-end close from 8 days to 5 by automating reconciliations. 4 years of experience; strongest in SQL, Excel and Tableau.",
    "recommendation-letter": ("Dear Ms Rivera,\n\n"
                              "I am writing to recommend Priya Shah for the Team Lead role at Acme. I managed her at Example Co for three years, while she worked as a senior support agent.\n\n"
                              "What stands out most is how calm she stays with upset customers. When our payment system failed last March, she answered 140 tickets in a day and kept our satisfaction score above 90%.\n\n"
                              "A second strength is her clear writing. She rewrote 60 help articles, and tickets about refunds fell by a third.\n\n"
                              "I recommend Priya without reservation. If you would like to know more, you can reach me at dana.lee@example.com.\n\n"
                              "Sincerely,\nDana Lee\nHead of Support, Example Co"),
}


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

def build_tools(page, section, crumbs, e, P, FULL, SITE, V, jobs, CAT, role_skills=(), skill_slug=None, every="every hour"):
    """Writes the /tools/ hub and every tool page through page(); returns [(path, name, one_line_description), ...] for linking.
    role_skills: [(role slug, role name, postings, [(skill, postings that name it), …]), …], most postings first; skill_slug(skill) is its page under /skills/."""
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
        "jobs/": ("Open jobs", f"{n_jobs:,} roles from company career pages, re-read {every}."),
        "remote/": ("Remote jobs", "Open roles listed as remote, with the countries or time zones each one accepts."),
        "salaries/": ("Salaries by role, skill and company", "Median advertised pay from live postings, with the number of roles behind each figure."),
        "resume/": ("Resume builder", "A plain one-column resume that screening software reads cleanly. Saves as PDF, nothing uploaded."),
        "for-you/": ("Jobs for you", "Pick your skills or paste your resume and see the open roles that fit, best matches first."),
        "post-a-job/": ("Post a job", "Put your vacancy in front of people who are searching for work right now."),
        "widgets/": ("Jobs widget and live badges", "Show live jobs on your own site with one line of code."),
        "contract/": ("Contract jobs", "Open contract roles, updated hourly."),
        "my-jobs/": ("Application tracker", "Save jobs, mark where each application stands and see which ones have gone quiet."),
    }
    TOOLS = []          # filled below, in the order they appear on the hub

    def tool(slug, group, name, card, title, desc, h1, lead, html, how_title, how, faq, rel, site, ex=None):
        """ex: (heading, html) of one more section shown between the tool and "how it works": a worked example or a table."""
        TOOLS.append(dict(slug=slug, group=group, name=name, card=card, title=title + brand, desc=desc, h1=h1, lead=lead, html=html, how_title=how_title, how=how, faq=faq, rel=rel, site=site, ex=ex))

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
              + _area("resume", "Your resume", 12, "Paste the text of your resume here, or open the file above", cls="", tall=True, ex=EX_RESUME, file=True)
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
         ["resume-match", "resume-skills", "resume-bullet-builder"], ["resume/", "for-you/"])

    # ------------------------------------------------------------ 2. salary checker
    groups = salary_groups(jobs)
    cats = [(s, n) for s, n in CAT.items() if s != "other" and f"{s}||" in groups]
    skills = sorted((k.split("|")[2] for k in groups if k.startswith("||") and k != "||"), key=str.lower)
    sal_data = {"q": QS, "min": MIN_SAMPLE, "date": DATE, "g": groups}
    DATA_FILES["data/salary-groups.json"] = json.dumps(sal_data, ensure_ascii=False, separators=(",", ":"))     # about 1.1 MB: a file the tool fetches, not part of the page
    money = lambda k: f"${k:,}K"
    cols = [lv for lv in ("", "Junior", "none", "Senior", "Lead")]
    def cell(cat, lv):
        g = groups.get(f"{cat}|{lv}|")
        return f'<td class="num"><strong>{money(g[10])}</strong> <span class="note">· {g[0]:,}</span></td>' if g else '<td class="num">—</td>'       # g[10] is the median: 3 leading numbers + index of 50 in QS
    assert QS[7] == 50
    sal_rows = "".join(f"<tr><td>{e(name)}</td>" + "".join(cell(slug, lv) for lv in cols) + "</tr>" for slug, name in [("", "All categories")] + cats)
    sal_table = ('<div class="tablewrap"><table><tr><th>Category</th><th>Any level</th><th>Junior</th><th>No level in the title</th><th>Senior</th><th>Lead and above</th></tr>' + sal_rows + "</table></div>"
                 f'<p class="note">Median advertised salary · number of postings counted. A dash means fewer than {MIN_SAMPLE} postings. Yearly, US dollars, as of {DATE}. '
                 f'<a href="{P}/salaries/">Salaries by skill and company</a></p>')
    tool("salary-checker", "seekers", "Salary checker",
         "See the median and range of advertised salaries for your category, level and skill, and where your pay sits.",
         "Salary Checker: Compare Your Pay With Posted Salaries",
         f"Compare your salary with what open job postings advertise: median and range by category, level and skill, from {n_paid:,} postings with a published range.",
         "Compare your salary with what companies advertise",
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
              ),
         "Where the figures come from",
         f"<p>Every figure is calculated from job postings collected from employers’ own careers pages and re-read {every}. On {DATE} there were {n_jobs:,} open roles; "
         f"{n_paid:,} of them publish a yearly salary range in US dollars. Ranges in other currencies and hourly rates are left out so that all figures can be compared.</p>"
         "<p>Each posting counts once, by the midpoint of its range. The <strong>median</strong> is the middle posting; the <strong>middle half</strong> runs from the 25th to the 75th percentile; "
         "“the typical posting advertises” is the median lower end and the median upper end of the ranges. Your position is found by placing your number between 15 percentile points of the group.</p>"
         f"<p>A group needs at least {MIN_SAMPLE} postings. Below that nothing is shown, because a median of a few postings describes those few companies, not the market. "
         "The level comes from the job title; “no level in the title” means the title has no word such as Senior, Lead or Junior.</p>",
         [("Where does the salary data come from?",
           f"From salary ranges that employers publish in their own job postings. On {DATE} we counted {n_paid:,} open roles with a yearly US-dollar range, out of {n_jobs:,} open roles. Nothing comes from surveys or from numbers submitted by users."),
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
         "Hourly to Salary Calculator: Hourly, Monthly, Yearly Pay",
         "Convert an hourly wage to a yearly salary and back: per hour, day, week, month and year, with your own hours and paid weeks. Table of $10 to $100 an hour. Free, no sign-up.",
         "Hourly to salary calculator: any pay per hour, month and year",
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
         [('$35 an hour is how much a year?', '$72,800 a year before tax at 40 hours a week for 52 weeks (35 × 2,080 hours). That is $6,066.67 a month, $2,800 every two weeks and $1,400 a week. The table on this page gives the same for every rate from $10 to $100 an hour.'),
          ('How much is $60,000 a year per hour?', 'About $28.85 an hour at 40 hours a week for 52 weeks (2,080 hours): divide the yearly figure by 2,080. Monthly it is $5,000 and weekly $1,153.85, before tax.'),
          ('What is a bi-weekly paycheck on $60,000 a year?', '$2,307.69 before tax: there are 26 bi-weekly pay periods in a year. Paid twice a month (semi-monthly, 24 periods) it is $2,500. This calculator works before tax; take-home pay depends on where you live and your deductions.'),
          ('Does this calculator show take-home pay after tax?', 'No: every figure here is before tax, the way job postings state pay. For a US salary after federal tax, Social Security and Medicare, use the take-home pay calculator on this site.'),
          ("How do I convert an hourly rate to a yearly salary?",
           "Multiply the hourly rate by the hours you work in a week and by the weeks you are paid in a year. At 40 hours and 52 weeks that is the hourly rate times 2,080, so $50 an hour is $104,000 a year."),
          ("How many working hours are there in a year?",
           "2,080 if you count 40 hours a week for 52 weeks. A 37.5-hour week gives 1,950 hours and a 35-hour week 1,820. For a salaried employee, paid holidays are already inside these figures."),
          ("Why is a contractor’s hourly rate higher than an employee’s?",
           "Because a contractor is paid only for the hours billed. Holidays, sick days, gaps between contracts, equipment and employer-side taxes all come out of the rate. Lower “paid weeks per year” to see what a rate adds up to, or use the contractor rate calculator."),
          ("Is the result before or after tax?",
           "Before tax. The converter only changes the unit of time. Tax depends on the country, the state and your personal situation, so it is not estimated here.")],
         ["take-home-pay", "overtime-pay", "raise-calculator", "contractor-rate", "compare-offers"], ["salaries/"],
         # Search and AI answers check, 18 Nov 2026 ("hourly to salary calculator"): the first results print a table of common rates
         # (Calculator.net, Omni, The Calculator Site), and "35 an hour is how much a year" is a related search of its own.
         ex=("Hourly to salary table: $10 to $100 an hour",
             "<p>A full-time year of 40 hours a week for 52 weeks is 2,080 paid hours. Before tax:</p>"
             '<div class="tablewrap"><table class="rkt"><tr><th>Per hour</th><th>Per week</th><th>Every two weeks</th><th>Per month</th><th>Per year</th></tr>'
             + "".join(f"<tr><td><strong>${h_}</strong></td><td>${h_ * 40:,}</td><td>${h_ * 80:,}</td><td>${h_ * 2080 / 12:,.0f}</td><td><strong>${h_ * 2080:,}</strong></td></tr>"
                       for h_ in (10, 12, 15, 17, 18, 20, 22, 25, 28, 30, 35, 40, 45, 50, 60, 75, 100))
             + "</table></div>"
             f'<p class="note">Paid for more than 40 hours in some weeks? The <a href="{P}/tools/overtime-pay/">overtime pay calculator</a> adds time and a half. '
             f'What is left after tax: the <a href="{P}/tools/take-home-pay/">take-home pay calculator</a>. Jobs by rate: <a href="{P}/jobs-that-pay/">jobs that pay $15 to $100 an hour</a>.</p>'))

    # ------------------------------------------------------------ 3b. take-home pay ("salary calculator": the first intent on Google is pay after tax,
    # SERP_WORK 35b, 15 Nov 2026). US federal tax and FICA for 2026, figures from the IRS and the SSA; state tax is not estimated.
    ST = state_tax.STATES
    assert state_tax.FED_STD == {k: v[0] for k, v in FED_2026.items()}
    st_data = json.dumps({c: {"n": x["name"], "base": x["base"], "s": x["single"], "j": x["joint"], "pay": x["pay"],
                              **({"exMax": x["ex_max"]} if x.get("ex_max") else {}), **({"pt": 1} if x.get("pretax_taxed") else {}),
                              **({"sp": x["std_phase"]} if x.get("std_phase") else {}), **({"cp": x["credit_phase"]} if x.get("credit_phase") else {}), **({"ao": x["add_over"]} if x.get("add_over") else {}),
                              **({"xs": x["ex_steps"]} if x.get("ex_steps") else {}), **({"fd": x["fed_ded"]} if x.get("fed_ded") else {}),
                              **({"xb": x["ex_by"]} if x.get("ex_by") else {}), **({"ss": x["std_steps"]} if x.get("std_steps") else {}), **({"cm": x["credit_max"]} if x.get("credit_max") else {}),
                              **({"rc": x["recapture"]} if x.get("recapture") else {}), **({"lr": x["local_rate"]} if x.get("local_rate") else {})} for c, x in ST.items()}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    def th_form(code=""):
        """The calculator; on a state's own page that state is chosen when the page opens (tools.js reads data-state)."""
        html_ = wrap("take-home-pay",
                     '<div class="card tl-form"><div class="tl-grid">'
                     + _f("salary", "Yearly salary (US dollars)", "75000")
                     + _sel("status", "Filing status", [("single", "Single", True), ("joint", "Married filing jointly")])
                     + _sel("freq", "Paid", [("biweek", "Every two weeks (26)", True), ("semimonth", "Twice a month (24)"), ("month", "Monthly (12)"), ("week", "Weekly (52)")])
                     + "</div>" + '<div class="tl-grid c2">'
                     + _sel("state", "State", [("", "Federal only", True)] + [(c, x["name"]) for c, x in ST.items()], hint=f"{len(ST)} of 51, counting Washington, DC.")
                     + _f("pretax", "Pre-tax contributions a year (optional)", "0", hint="401(k), HSA and similar amounts taken before income tax.") + "</div>"
                     + '<div class="tl-actions">' + _clear() + "</div></div>"
                     + _private(" The figures are worked out inside your browser and never sent anywhere.")
                     + _board("Your take-home pay", "Enter a yearly salary to see what is left after tax.")
                     + f'<script type="application/json" id="tl-data">{st_data}</script>')
        return html_.replace('data-tool="take-home-pay"', f'data-tool="take-home-pay" data-state="{code}"', 1) if code else html_

    def st_after(code, sal, status="single"):
        tx, ss, med, net = take_home_2026(sal, status)
        r = state_tax.state_tax(code, sal, status, 0, tx)
        r = dict(r, tax=r["tax"] + r["local"])                         # a county tax every resident pays (Maryland) counts as state tax in the tables
        return tx, ss + med, r, net - r["total"] + 1e-6              # half a dollar rounds up, as in the calculator
    st_row = lambda c: (lambda a: f'<tr><td><a href="{P}/tools/take-home-pay/{ST[c]["slug"]}/">{_e(ST[c]["name"])}</a></td><td>${a[2]["tax"]:,.0f}</td><td>${a[2]["pay_total"]:,.0f}</td><td><strong>${a[3]:,.0f}</strong></td><td>${a[3] / 12:,.0f}</td></tr>')(st_after(c, 75000))

    tool("take-home-pay", "seekers", "Take-home pay calculator",
         "A US salary after federal and state tax for 2026: per paycheck, per month and per year.",
         "Take-Home Pay Calculator 2026: Your Paycheck After Tax",
         f"Paycheck calculator for 2026: your US salary after federal income tax, Social Security, Medicare and state tax in {len(ST)} states, per paycheck, month and year. Free, no sign-up.",
         "Salary after tax: your take-home pay in 2026",
         f"Enter a yearly salary and how you file, and choose your state. The calculator takes off federal income tax with the 2026 brackets and standard deduction, Social Security, Medicare and, in {len(ST)} states so far, "
         "the state’s income tax and payroll deductions, and shows what lands in each paycheck.",
         th_form(),
         "How the take-home pay is calculated",
         "<ul><li><strong>Federal income tax</strong> on the salary minus pre-tax contributions minus the 2026 standard deduction ($16,100 single, $32,200 married filing jointly), "
         "with the 2026 brackets: 10%, 12%, 22%, 24%, 32%, 35% and 37% (single: up to $12,400, $50,400, $105,700, $201,775, $256,225, $640,600 and above; "
         "married filing jointly: $24,800, $100,800, $211,400, $403,550, $512,450, $768,700 and above). Source: IRS Revenue Procedure 2025-32.</li>"
         "<li><strong>Social Security</strong>: 6.2% of wages up to $184,500 (the 2026 wage base, Social Security Administration).</li>"
         "<li><strong>Medicare</strong>: 1.45% of all wages, plus 0.9% above $200,000 single or $250,000 married filing jointly.</li>"
         f"<li><strong>State income tax</strong>, if you choose a state: its 2026 brackets, standard deduction, exemption and credit, and the payroll deductions it charges employees. Each state’s page lists its figures and sources, and says so where the state’s own site could not be opened. Still to come: {state_tax.WAITING}.</li></ul>"
         "<p>Not included: city and county taxes, credits (child tax credit and others), itemized deductions, bonuses taxed at a flat rate, and benefits taken from pay "
         "such as health insurance. Your employer’s withholding can differ a little from this year-end figure. This is an estimate, not tax advice.</p>",
         [("How much is $75,000 a year after taxes?", "For a single filer with no pre-tax contributions, $61,593 a year after 2026 federal income tax ($7,670), Social Security ($4,650) "
           "and Medicare ($1,088): about $2,369 every two weeks, before any state tax."),
          ("How much is $100,000 a year after taxes?", "For a single filer with no pre-tax contributions, $79,180 a year after 2026 federal income tax ($13,170), Social Security ($6,200) and Medicare ($1,450), "
           "before state tax: about $3,045 every two weeks."),
          ("Does this include state tax?", f"Yes, for {len(ST)} states so far: choose yours in the form. Alaska, Florida, Nevada, New Hampshire, South Dakota, Tennessee, Texas, Washington and Wyoming have no state income tax on wages. "
           "City and county taxes are not included."),
          ("Why is my paycheck different from this?", "Your employer withholds tax through the year from the W-4 you filled in, and takes off benefits such as health insurance. "
           "This calculator works out the year’s federal tax itself, so the two can differ by a little."),
          ("Do 401(k) contributions lower my taxes?", "Traditional 401(k) contributions lower your income tax, because they are taken off before it; Social Security and Medicare are still due on them. "
           "Enter them as pre-tax contributions to see the difference.")],
         ["salary-converter", "overtime-pay", "raise-calculator"], ["salaries/"],
         # Search and AI answers check, 18 Nov 2026 ("take home pay calculator"): Google's answer walks through the five steps and the
         # first results answer "how much is $X after taxes" for the round salaries; a table gives all of them at once.
         ex=("Take-home pay table for 2026: $40,000 to $200,000",
             "<p>A single filer with no pre-tax contributions, after federal income tax, Social Security and Medicare. State income tax is not taken off.</p>"
             '<div class="tablewrap"><table class="rkt"><tr><th>Salary</th><th>Federal income tax</th><th>Social Security and Medicare</th><th>Take-home a year</th><th>A month</th><th>Every two weeks</th><th>Kept</th></tr>'
             + "".join((lambda t_: f"<tr><td><strong>${sal_:,}</strong></td><td>${t_[0]:,.0f}</td><td>${t_[1] + t_[2]:,.0f}</td><td><strong>${t_[3] + 1e-6:,.0f}</strong></td><td>${t_[3] / 12:,.0f}</td>"
                                   f"<td>${t_[3] / 26:,.0f}</td><td>{100 * t_[3] / sal_:.0f}%</td></tr>")(take_home_2026(sal_))
                       for sal_ in (40000, 50000, 60000, 70000, 75000, 80000, 90000, 100000, 120000, 150000, 175000, 200000))
             + "</table></div>"
             '<p class="note">How it is worked out, in order: the salary, minus pre-tax contributions, minus the standard deduction, taxed by the 2026 brackets; then Social Security (6.2% up to $184,500) '
             "and Medicare (1.45%, plus 0.9% above $200,000). Enter your own figures above for another salary, married filing jointly or pre-tax contributions.</p>"
             f'<h3>$75,000 a year, state by state</h3><p>A single filer with no pre-tax contributions. Each state links to its own paycheck calculator, figures and sources.</p>'
             '<div class="tablewrap"><table class="rkt"><tr><th>State</th><th>State income tax</th><th>State payroll deductions</th><th>Take-home a year</th><th>A month</th></tr>'
             + "".join(st_row(c) for c in ST) + f'</table></div><p class="note">Still to come, once their special rules are built and their figures agree: {state_tax.WAITING}.</p>'))

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
         "<p>The exit multiples are scenarios you choose, not forecasts. Tax is not included. Liquidation preferences, which pay investors back first, are not modeled; they matter most when a company sells for little more than it raised.</p>",
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
         "Cover Letter Generator — Free, No Sign-Up",
         "Build a short, clear cover letter from a few facts about you and the job. Three tones; copy, download or print. Template-based, private, no sign-up.",
         "Cover letter generator: write one without staring at a blank page",
         "The empty page is the slowest part of applying. Fill in a few facts about the job and about you, pick a tone, and you have a short, clean letter to edit. "
         "Paste the job posting and the page fills in the title and company and shows the skills it names. "
         "It is a fill-in template, not AI: every sentence is built from what you type, so nothing is invented for you. Nothing is uploaded.",
         wrap("cover-letter",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-paste">'
              + _area("posting", "Job posting (optional)", 4, "Paste the text of the job posting here", cls="")
              + '<div class="tl-actions"><button class="btn ghost" type="button" id="tl-fill">Read the posting</button><span class="note" id="tl-fill-out" role="status"></span></div>'
              + '<div class="tl-found" id="tl-found" hidden></div></div><div class="tl-grid">'
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
         "No AI is involved and nothing is generated: what you read is what you typed, arranged. Treat it as a first draft and change any sentence that does not sound like you.</p>"
         "<p>A pasted posting is read in your browser by plain rules: the title from its first lines or a “Title:” label, the company from a “Company:” label or “at Acme”, and the skills from this site’s list. "
         "A skill reaches the letter only when you tap it, because the letter must say what is true of you.</p>",
         [('Can it write a cover letter from a job description?', 'It can start one. Paste the posting: the job title and company are filled in and the skills it names appear as buttons. Tap the ones you really have, add one result and one reason for choosing this company, and the letter is ready to edit. Nothing is sent anywhere.'),
          ('Is there a free cover letter generator with no sign-up?', 'This one: fill in a few facts about you and the job, pick a tone, and copy, download or print the letter. No account, no email, and nothing is uploaded.'),
          ('Can I use ChatGPT to write a cover letter?', 'Yes, as a first draft. Then make it yours: replace general claims with your own results and numbers, use the posting’s words and cut it to under 250 words. A letter that could go to any company reads as generated. This generator builds every sentence from the facts you type, so nothing is invented.'),
          ("Is this cover letter written by AI?",
           "No. It is a fill-in template: every sentence is assembled from the fields you complete, in the tone you choose. Nothing is generated, guessed or sent to a server, so the letter contains only facts you typed."),
          ("How long should a cover letter be?",
           "Short: three to five brief paragraphs that fit on one page. The builder shows a word count under the letter and tells you when your answers make it run long."),
          ("What should a cover letter say that a resume does not?",
           "Why this job and this company, and one concrete result that shows you can do the work. The resume lists what you did; the letter connects it to what this employer needs."),
          ("Do I need a different cover letter for every job?",
           "Yes, at least the opening and the reason for choosing the company. Your details stay saved in this browser, so for the next application you change only the job title, the company and the “why” sentence.")],
         ["application-email", "resume-match", "thank-you-email"], ["resume/"])

    # ------------------------------------------------------------ 9. negotiation email
    both = ' data-for="counter raise"'
    tool("negotiation-email", "seekers", "Negotiation email writer",
         "A polite, specific email to counter an offer, ask for a raise or ask for more time. A template, not AI.",
         "Salary Negotiation Email: Template & Generator",
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
         [('Can I lose a job offer for negotiating salary?', 'It is rare when the request is polite and backed by figures: most employers expect a counteroffer. Name one number with a reason (the market range for the role, your experience), and say you are excited about the job.'),
          ('What is a good email format for salary negotiation?', 'Thanks for the offer; that you are excited about the role; the figure you ask for and why, from market data; and a warm close asking if they can meet it. This builder writes it in that order.'),
          ("How do I counter a job offer by email?",
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
         [('How much should I charge as a contractor?', 'Start from the salary you would take as an employee, add what an employer would pay on top (taxes, insurance, paid leave, equipment) and divide by the days you can really bill in a year, not 260. This calculator does it step by step.'),
          ('How do I convert a salary to a contractor day rate?', 'A common rule of thumb is the yearly salary divided by 220 to 230 billable days, plus 20 to 50% for the costs and gaps an employee does not carry. The calculator shows the full working.'),
          ("How do I turn a salary into a contractor day rate?",
           "Add the costs an employer would have covered to the salary, then divide by the days you can actually bill. With a target of $100,000, 25% for employer-side costs, $5,000 of business costs, 35 days off and 80% of working days billed, that is $130,000 ÷ 180 days, about $722 a day."),
          ("How many billable days are there in a year?",
           "Start from 260 weekdays, subtract public holidays, vacation and sick days, then multiply by the share of time you can bill. 260 minus 35 days off is 225 working days; if 80% of them are billable, that is 180 days."),
          ("What extra costs does a contractor pay?",
           "Whatever an employer paid on top of your salary: its share of social security or payroll taxes, health insurance and pension contributions (paid leave is counted in the days off, equipment and software in the business costs). The amounts differ by country, so the calculator asks for your own percentage instead of assuming one."),
          ("Is the result before or after tax?",
           "Before tax. It is the amount to invoice. Income tax and any sales tax or VAT depend on where you live and how your business is set up.")],
         ["salary-converter", "salary-checker", "negotiation-email"], [contract_path])

    # ------------------------------------------------------------ 10. job description checker
    tool("job-description-checker", "employers", "Job description checker",
         "Score a posting for length, missing salary, must-have overload, biased wording, jargon and readability.",
         "Job Description Checker: Bias & Clarity Score",
         "Paste a job description and get a score with fixes: missing salary, too many must-haves, gender-coded and exclusionary words, jargon, readability. Free.",
         "Find what is putting candidates off your job description",
         f"A posting with no salary, fifteen “requirements” and a wall of jargon gets skipped by the people you want to hear from. {100 - sal_pct}% of the {n_jobs:,} open roles we track do not state a salary. "
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
           f"Yes, if you want candidates to be able to tell whether the role fits them. Of the {n_jobs:,} open roles we track, {sal_pct}% state what they pay" + (", so a posting with a clear range also stands out from most of the others." if sal_pct < 40 else ", and candidates who filter by salary never see the rest.")),
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
         "Paste your resume: whether a hiring system can read it, a score out of 10 from six plain checks, and what to fix, each quoting your own line.",
         "Free ATS Resume Checker: Score, Readability and Fixes",
         "Paste your resume to see whether a hiring system can read it, a score out of 10 and what to fix, quoting your own lines. Free, no AI, nothing uploaded.",
         "ATS resume checker: what a hiring system and a recruiter see",
         "A resume is read twice. A hiring system (an ATS) first turns it into fields: contact details, jobs, dates, education, skills. Then a recruiter skims the top of the page, a few bullet points and the dates. "
         "This page checks both. Six checks show whether the software can find what it needs, and six more give a score out of 10 from a formula printed on this page: "
         "the first screen, duty wording, numbers, the skills list, gaps between dates and length. Every fix quotes your own line. It works by rules, not AI, and nothing is uploaded.",
         wrap("resume-review",
              '<div class="card tl-form">'
              + _area("text", "Your resume", 16, "Paste the text of your resume here, with its headings and dates, or open the file above", tall=True, ex=EX_REVIEW, file=True)
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
         "A break in the dates is a question a reader may ask, not a fault.</p>"
         "<p><strong>Can a hiring system read it?</strong> A separate list that does not change the score. It looks for an email address and a phone number; the headings Experience, Education and Skills under their usual names; "
         "at least one date range it can read; three or more lines that look like columns or a table (a tab or three spaces between words, or a line that begins or ends with a vertical bar); and icons, emoji or broken characters. "
         "It sees only the text, so a picture, a text box or a page header in your file shows up here only as something missing. To test a PDF, copy all its text and paste it in.</p>",
         [('Is this an ATS resume checker?', 'Yes, as far as text can show it. It checks that an applicant tracking system can find your email, phone, standard headings and dates, and it looks for columns, tables, icons and broken characters. No public tool can run the software a particular employer uses, so none can promise that a resume will pass.'),
          ('Is 80% a good ATS score?', 'There is no single ATS score. An employer’s applicant tracking system stores resumes and lets recruiters search them; the percentages people quote come from third-party checkers, each with its own formula. On this site the resume match checker scores the keyword overlap with one posting (75 and above is labelled a strong match), and this review scores how well the page reads on a first skim, out of 10.'),
          ('How do I check if my resume is good?', 'Three questions cover most of it: does the top third show your title, years and strongest skills; does every line under a job say what changed, with a number; and does it use the words of the posting you apply to. This review checks the first two; the resume match checker checks the third against a real posting.'),
          ("How is the resume score calculated?",
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
         [('Can I check the text of my current profile?', 'Yes: copy your headline and the About section from LinkedIn and paste them into the two boxes. The check runs right here in your browser and nothing is sent anywhere.'),
          ("How long can a LinkedIn headline be?",
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
         "Check a salary offer against the advertised ranges of open jobs: where it sits for your category and level, the median and the postings behind it. Free.",
         "Check a salary offer against what open postings advertise",
         f"When an offer arrives it is hard to tell whether the figure is fair: {100 - sal_pct}% of the {n_jobs:,} open roles on this site do not state a salary. This check uses the {n_paid:,} that state a yearly range in US dollars. "
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
         "Thank-You Email Generator: Free, Ready in a Minute",
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
         [('How soon should a thank-you email be sent after an interview?', 'Within 24 hours, ideally the same afternoon or the next morning. Send a separate, personal note to each person who interviewed you.'),
          ('Are you supposed to reply to a thank-you email after an interview?', 'The interviewer may not reply, and that says nothing about your chances. If they do, a one-line answer is enough; there is no need to keep the thread going.'),
          ('What should I write in an email after an interview?', 'Thanks for their time, one specific thing you discussed, one sentence on why you fit, and when you are available. Two or three short paragraphs, under 200 words.'),
          ("When should I send a thank-you email after an interview?",
           "The same day or the next morning, while the conversation is still fresh for both of you. If you met several people, send each of them a separate short email and change the detail you mention."),
          ("What should a thank-you email say?",
           "Three things: thanks for the person’s time, one specific point from your conversation, and that you are still interested in the job. The specific point shows that the email was written after this interview and not copied."),
          ("Does a thank-you email improve my chances?",
           "Nobody can promise that, and this page does not. It is a courtesy, it keeps the conversation open, and it gives you a place to add something you forgot to say in the room."),
          ("Is the email written by AI?",
           "No. It is a fill-in template: every sentence is assembled from the fields you complete, in the tone you choose. Nothing is generated or sent to a server.")],
         ["follow-up-email", "interview-answer-builder", "reference-request-email"], ["for-you/"])

    # ------------------------------------------------------------ 17b. answering a job offer (search demand: "job offer acceptance email", "decline job offer email")
    tool("job-offer-response", "seekers", "Job offer response email",
         "Accept an offer, decline it politely or ask for a few more days: a short email from a few fields. A template, not AI.",
         "Job Offer Acceptance, Decline or Extension Email: Templates",
         "Write the email that answers a job offer: accept it, decline it politely or ask for more time to decide. Fill in a few fields, copy the text. Private, free.",
         "Answer a job offer in writing, the right way",
         "An offer deserves a written answer: it confirms what you agreed, or closes the door politely so it can open again later. "
         "Pick what you want to say (accept, decline or ask for time), fill in the role and the names, and the email is ready to copy.",
         wrap("job-offer-response",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("mode", "What do you want to say?", [("accept", "Accept the offer", True), ("decline", "Decline the offer"), ("time", "Ask for more time")])
              + _f("to", "Recruiter’s or manager’s name", "Ms Rivera", mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job title in the offer", "Product Designer", mode="")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("start", "Start date you agreed", "Monday, 4 January", mode="", show=' data-mode="accept"')
              + _f("by", "Answer by", "Friday, 18 December", mode="", show=' data-mode="time"', hint="A specific date. A few working days is a normal request.")
              + _area("terms", "The main terms, to confirm (optional)", 2, "a salary of $95,000 a year and 25 days of paid leave", show=' data-mode="accept"',
                      hint="Finish the sentence “I understand the offer as follows: …”. Leave it empty if the written offer says it all.")
              + _area("reason", "A reason (optional)", 2, "I have accepted a role that is closer to the work I want to do next.", show=' data-mode="decline time"',
                      hint="One sentence. You do not owe a reason; a short one keeps the door open.") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("offer-response.txt") + "</div>"),
         "How the email is put together",
         "<p><strong>Accept</strong> thanks them, says yes in the first lines, confirms the start date and, if you add them, the main terms, so both sides have the same thing in writing. "
         "<strong>Decline</strong> thanks them, says no clearly and leaves the door open. <strong>Ask for time</strong> names a date instead of “a few days”, so nobody has to guess.</p>"
         "<p>It is a fill-in template: each sentence is built from what you type. Nothing is generated or sent anywhere: copy the text into your own email and send it yourself.</p>",
         [("How do I accept a job offer by email?",
           "Thank them, say clearly that you accept, confirm the job title and the start date, and ask what they need from you before the first day. Accept only once the written offer matches what you agreed."),
          ("How do I decline a job offer politely?",
           "Thank them for the offer and their time, say clearly that you will not accept, give a short reason if you want to, and say you hope to stay in touch. Answer soon, so they can offer the job to someone else."),
          ("Can I ask for more time to decide on a job offer?",
           "Yes. Asking for a few more days is a normal request. Name a specific date, say you are interested, and keep to the date you named."),
          ("Should I accept an offer before it is in writing?",
           "Say you are pleased and that you will confirm once you have the written offer. Do not resign from your current job until you have it.")],
         ["offer-check", "negotiation-email", "compare-offers"], ["for-you/"])

    # ------------------------------------------------------------ 18. resignation letter
    tool("resignation-letter", "seekers", "Resignation letter builder",
         "Your last day, your notice period, optional thanks and a handover offer become a short, neutral letter to copy or print.",
         "Resignation Letter Generator: Free, Short and Neutral",
         "Build a short, neutral resignation letter: last working day, notice period, optional thanks and a handover offer. Copy, download or print. Private, no sign-up.",
         "Write a short resignation letter that states the facts",
         "A resignation letter has one job: to put on record that you are leaving and on which day. Anything more, such as reasons or complaints, stays in your file after you have gone. "
         "Enter your last working day and a few details, choose whether to add thanks and a handover offer, and copy or print the letter. "
         "If a contract or company policy sets a notice period, check it before you set the date; in most US jobs two weeks is the custom, not a legal duty.",
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
           "The notice period in your employment contract or company policy. In the US most jobs are at-will and no law sets a notice period for resigning, so two weeks is the custom; elsewhere the law often sets a minimum. This page does not know yours, so check the contract before you set your last day. The last working day calculator on this site counts the date from the day you give notice."),
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
         [('Is a 3% raise really a raise?', 'Only if prices rose by less than 3% over the year. Compare the raise with inflation where you live: the pay raise calculator on this site shows the raise after inflation.'),
          ('How do I ask for a raise politely?', 'Ask for a meeting rather than putting the whole request in one message, bring two or three results with numbers and a figure based on the market, and say you want to keep growing in the role.'),
          ("How do I ask for a raise by email?",
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
         [('Is it okay to ask for a reference by email?', 'Yes, and it is the most common way. Ask early, say which job it is for, remind them what you worked on together, and make it easy to say no.'),
          ('Can I lose a job offer because of a reference?', 'It can happen when a reference contradicts what you said, so pick people who know your work well and tell them what the role needs before the employer calls.'),
          ("Who should I ask to be a reference?",
           "Someone who saw your work closely and can describe it: a former manager first, then a senior colleague, a client or a teacher. Ask before you give their name to an employer."),
          ("When should I ask for a reference?",
           "Before you hand over the person’s name, and with enough time for them to prepare. The email names the date so they can see whether it fits their calendar."),
          ("What should I send with the request?",
           "Your current resume and the job description, plus two or three points that matter for this job. A reference who knows what the employer is looking for can give examples that fit."),
          ("What if the person says no?",
           "Thank them and ask someone else. The template ends with a line that makes declining easy, because you want a reference from someone who is glad to give one.")],
         ["recommendation-letter", "thank-you-email", "resignation-letter"], ["resume/"])

    # ------------------------------------------------------------ 21. LinkedIn headline and About
    tool("linkedin-headline", "seekers", "LinkedIn headline and About builder",
         "Role, years, three strengths and what you want next become three headlines inside the 220-character limit and a short About text.",
         "LinkedIn Headline Generator & About Section, Free",
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
         [('What is a good headline for LinkedIn?', 'Your target role, your strongest skill or specialty, and one proof: “Data Analyst | SQL, Tableau | Cut reporting time 60%”. Up to 220 characters; the first 60 or so show in search.'),
          ("What should my LinkedIn headline be if I don't have a job?", 'The role you want and what you bring, not “unemployed”: “Junior UX Designer | User Research, Figma | Open to work”. Recruiters search headlines by job title and skill.'),
          ("How long can a LinkedIn headline be?",
           "220 characters, including spaces. The builder counts the characters of each variant as you type and keeps every variant inside the limit."),
          ("What should a LinkedIn headline say?",
           "Your role and what you are good at, in words a recruiter would type into search: the job title, two or three skills or fields and, if you are looking, what you are open to. “Open to work” alone says nothing about what you do."),
          ("How long should the About section be?",
           "LinkedIn accepts up to 2,600 characters, but only the opening lines show before a reader has to click “see more”. Put what you do and for whom in the first two sentences; the builder’s paragraph starts with exactly that."),
          ("Will these headlines get me more profile views?",
           "This page cannot promise that. It gives you three clear ways to say what you do inside LinkedIn’s limit. How often a profile is found also depends on your experience, your network and what recruiters search for.")],
         ["linkedin-summary", "linkedin-review", "linkedin-connection-message"], ["resume/"])

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
         ["elevator-pitch", "thank-you-email", "resume-bullet-builder"], ["for-you/"])

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
         ["resume-summary", "resume-review", "resume-match"], ["resume/"])

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
         ["follow-up-email", "resume-review", "resume-match"], ["for-you/", "jobs/"])

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

    # ------------------------------------------------------------ 25b. 401(k) match
    tool("401k-match", "seekers", "401(k) match calculator",
         "Your salary, the share you put in and your employer's match give the free money a year, and how much you leave unclaimed.",
         "401(k) Match Calculator: Free Employer Money",
         "Enter your salary, the share of it you save and the match your employer offers to see the match money a year and what you leave unclaimed. Free.",
         "See how much your employer adds to your 401(k) each year",
         "An offer that says “50% match up to 6%” hides a sum of money that depends on how much you save yourself. Enter your yearly salary, the share of it you put into the plan "
         "and the match as the offer states it. You get the employer’s part in a year, the largest match on offer and what you leave unclaimed. The match is part of what a job pays, "
         "so it belongs next to the salary when you compare offers.",
         wrap("401k-match",
              '<div class="card tl-form"><p class="tl-t">Your pay and your saving</p><div class="tl-grid">'
              + _f("salary", "Yearly salary before tax", "80,000")
              + _f("mine", "Share of your pay you put in, %", "4", hint="Per cent of each paycheck that goes into the plan.")
              + _cur() + '</div><p class="tl-t">The match in the offer</p><div class="tl-grid">'
              + _f("rate", "Employer adds, % of what you put in", "50", hint="“50% match” means 50 cents for every dollar you put in. “Dollar for dollar” is 100.")
              + _f("cap", "Up to, % of your pay", "6", hint="“Up to 6% of pay”: you put in more than that and the employer still adds on the first 6% only.")
              + '</div><div class="tl-actions">' + _clear() + "</div></div>"
              + _board("The employer’s part", "Enter your salary, the share you put in and the match from the offer.")
              + '<p class="note tl-priv"><b>Limits</b>The law caps how much a person may put in each year and the cap changes; this page does not know it. Your plan may also count pay, bonus and years of service in its own way: read its summary.</p>'),
         "How the match is calculated",
         "<ul><li><code>you put in = salary × your share ÷ 100</code></li>"
         "<li><code>employer adds = salary × the smaller of your share and the cap ÷ 100 × match rate ÷ 100</code></li>"
         "<li><code>largest match = salary × cap ÷ 100 × match rate ÷ 100</code>, which you get by putting in at least the cap</li>"
         "<li><code>left unclaimed = largest match − what the employer adds now</code></li></ul>"
         "<p>Example: a salary of 80,000, a match of 50% up to 6%, and you put in 4%. You put in 3,200. The employer adds 50% of 3,200, which is 1,600. "
         "At 6% you would put in 4,800 and the employer would add 2,400, so 800 a year goes unclaimed at 4%.</p>"
         "<p>Plans differ. Some employers add a fixed share of pay whatever you save, some match in two steps (for example 100% of the first 3% and 50% of the next 2%), and some make the employer’s part yours only after a number of years. "
         "This page handles the single-step match, the one most offers state; for the others, work out each step by hand with the same formula. It does not know tax rules or yearly limits.</p>",
         [("What does “50% match up to 6%” mean?",
           "For every dollar you put in, the employer adds 50 cents, but only on the first 6% of your pay. On a salary of 80,000 the most the employer adds is 2,400 a year, and you get it by putting in 4,800, which is 6% of the salary."),
          ("Is the employer’s match really free money?",
           "It is part of your pay that you collect only by saving. The employer’s part may belong to you at once or only after some years in the job, which is called vesting. Ask the employer for the vesting schedule before you count the whole sum."),
          ("How much should I put in?",
           "At least the cap, if you can: below it you give up money that is on offer. Whether to save more than that depends on your other costs and goals, which this page cannot know."),
          ("Does the match count when I compare two job offers?",
           "Yes. Add the largest match you would collect to each offer’s salary. The job offer comparison tool has a field for it.")],
         ["compare-offers", "take-home-pay", "salary-converter"], ["salaries/"])

    # ------------------------------------------------------------ 26. last working day
    # Search Console 24 Nov 2026: "last working day of this month", 10 impressions at 8 for this page. The date is written into the page
    # (built every hour), with the next eleven months below it, Monday to Friday and before public holidays.
    def _last_weekday(y_, m_):
        d_ = (datetime.date(y_ + (m_ == 12), m_ % 12 + 1, 1) - datetime.timedelta(days=1))
        while d_.weekday() >= 5: d_ -= datetime.timedelta(days=1)
        return d_
    _lwd = [_last_weekday(today.year + (today.month - 1 + k) // 12, (today.month - 1 + k) % 12 + 1) for k in range(12)]
    _wd = lambda d_: f"{'Monday Tuesday Wednesday Thursday Friday'.split()[d_.weekday()]}, {MONTHS_LONG[d_.month - 1]} {d_.day}, {d_.year}"
    _lwd_tbl = ('<h3>The last working day of each month</h3><div class="tablewrap"><table><thead><tr><th>Month</th><th>Last Monday-to-Friday</th></tr></thead><tbody>'
                + "".join(f"<tr><td>{MONTHS_LONG[d_.month - 1]} {d_.year}</td><td>{_wd(d_)}</td></tr>" for d_ in _lwd)
                + "</tbody></table></div><p>Public holidays are not taken out: if the last weekday of a month is a holiday where you work, the working day before it is the last one.</p>")
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
         "<ul><li><strong>Weeks and calendar days:</strong> the notice runs for that many days, counting the day it starts as the first. Two weeks given on a Monday, starting the next day, end on the Monday two weeks later.</li>"
         "<li><strong>Months:</strong> the notice ends on the same day of the month, that many months later. If that month is shorter, it ends on its last day: one month from January 31 ends on the last day of February.</li>"
         "<li><strong>Working days:</strong> Mondays to Fridays are counted one by one from the start of the period; Saturdays and Sundays are skipped.</li>"
         "<li><strong>Last working day:</strong> the day the notice ends, or the last Monday-to-Friday before it when it ends on a weekend.</li></ul>"
         "<p><strong>Public holidays are not known to this page.</strong> A holiday inside the period does not change the calendar date for weeks and months, but it shortens the days you actually work, "
         "and with a notice period counted in working days it can push the date later. The “working days left” are Mondays to Fridays with no holidays or vacation taken off. "
         "This is date arithmetic, not legal advice: how notice is counted, and whether it must end on a particular day such as the end of a month, is set by your contract and the law where you work.</p>" + _lwd_tbl,
         [("What is the last working day of this month?",
           f"{_wd(_lwd[0])} is the last Monday-to-Friday of {MONTHS_LONG[_lwd[0].month - 1]} {_lwd[0].year}; next month’s is {_wd(_lwd[1])}. "
           "Public holidays are not taken out, so check that the day is not a holiday where you work. The table on this page lists the next twelve months."),
          ("How do I count two weeks’ notice?",
           "Count 14 calendar days from the start of the notice period. If you give notice on a Monday and the period starts the next day, it ends on the Monday two weeks later, which leaves ten working days."),
          ("Does the day I give notice count?",
           "That depends on your contract and the rules where you work. A common way to count is from the day after notice is given, which is the setting this calculator starts with. Switch it to “the day you give notice” if yours counts that day as day one."),
          ("Are public holidays taken into account?",
           "No. The page does not know which holidays apply where you work. Check a calendar for the period it shows: a holiday reduces the days you work, and with a notice period counted in working days it can move the last day."),
          ("What if my notice ends on a weekend?",
           "The notice still ends on that date, but the last day you work is the Friday before, if you work Monday to Friday. The calculator shows both dates.")],
         ["resignation-letter", "compare-offers", "raise-calculator"], ["jobs/"])

    # ------------------------------------------------------------ 26b. telling a candidate no (search demand: "candidate rejection email")
    tool("candidate-rejection-email", "employers", "Candidate rejection email",
         "Tell an applicant or an interviewed candidate no, kindly and clearly, with optional feedback. A template, not AI.",
         "Candidate Rejection Email Template: After Application or Interview",
         "Write a kind, clear rejection email for a job applicant or an interviewed candidate, with optional feedback and an offer to keep their details. Free template.",
         "Tell candidates no, clearly and kindly",
         "Silence is what job seekers complain about most: the candidate who hears nothing after an interview remembers the company. "
         "Pick the stage they reached, add one line of feedback if you can, and send a short, clear answer.",
         wrap("candidate-rejection-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("stage", "How far did they get?", [("application", "Applied, no interview", True), ("interview", "Had an interview"), ("final", "Reached the final round")])
              + _f("candidate", "Candidate’s name", "Jordan", mode="")
              + _f("role", "Job title", "Account Executive", mode="")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("from", "Your name and title", "Sam Lee, Recruiter", mode="", auto="name")
              + _sel("keep", "Offer to keep their details?", [("no", "No", True), ("yes", "Yes, with their permission")])
              + _area("feedback", "One line of feedback (optional)", 2, "The other candidates had more experience selling to large hospitals.",
                      hint="Specific and about the job’s needs, never about the person. Leave it empty if you cannot give any.") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("rejection-email.txt") + "</div>"),
         "How the email is put together",
         "<p>It thanks the candidate, says no in the second sentence (not at the end of a long paragraph), gives the reason in terms of the role, and wishes them well. "
         "After an interview it acknowledges the time they spent. Keeping their details is offered only with their permission.</p>"
         "<p>It is a fill-in template: each sentence is built from what you type. Nothing is sent anywhere.</p>",
         [("How do you reject a candidate politely?",
           "Thank them, say clearly that you are moving forward with other candidates, give one specific reason about the role if you can, and wish them well. Send it as soon as you have decided."),
          ("Should I give feedback in a rejection email?",
           "A line of specific feedback about the role’s needs is helpful and appreciated. Keep it about the job, not the person, and check your company’s policy first."),
          ("How soon should I tell a candidate they were not selected?",
           "As soon as the decision is made. After an interview, within a few days; candidates who hear nothing remember it.")],
         ["interview-scorecard", "job-description-checker", "cost-per-hire"], ["post-a-job/"])

    # ------------------------------------------------------------ 27. cost per hire
    tool("cost-of-vacancy", "employers", "Cost of vacancy calculator",
         "What each working day without the person costs, from revenue per employee or from the role’s pay, and the total for the days the role has been open.",
         "Cost of Vacancy Calculator: What an Open Role Costs per Day",
         "Calculate the cost of an unfilled job: value per working day from revenue per employee or from the role’s pay, the weekly cost and the total for the days it has been open. Free.",
         "See what an open role costs every day",
         "An empty seat has a price: the work that is not done, the overtime of the people covering it, the projects that wait. "
         "Enter your revenue and headcount, or the yearly pay of the role, and how long it has been open: you get the cost per working day, per week and in total.",
         wrap("cost-of-vacancy",
              '<div class="card tl-form"><p class="tl-t">The value of a day of work</p><div class="tl-grid">'
              + _f("revenue", "Yearly revenue of the company (optional)", "12,000,000", hint="With the headcount, gives revenue per employee.")
              + _f("staff", "Number of employees", "80")
              + _f("salary", "Yearly pay of the role (if no revenue)", "95,000")
              + _f("mult", "Value multiple of the pay", "1.5", hint="How much more the work is worth than its pay. 1 counts the pay only; it is your assumption.")
              + '</div><p class="tl-t">The vacancy</p><div class="tl-grid">'
              + _f("days", "Days the role has been open", "45")
              + _f("extra", "Paid for cover while open (optional)", "6,000", hint="Overtime, contractors, agency staff.")
              + _f("workdays", "Working days in a year", "260") + _cur() + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Cost of the vacancy", "Enter your yearly revenue and headcount, or the yearly pay of the role.")),
         "How the cost of a vacancy is calculated",
         "<ul><li><code>value of a working day = yearly revenue ÷ employees ÷ working days</code>, or, without revenue, <code>yearly pay × value multiple ÷ working days</code></li>"
         "<li><code>working days open = calendar days open × 5 ÷ 7</code></li>"
         "<li><code>total = value of a working day × working days open + what you paid for cover</code></li></ul>"
         "<p>Both ways are estimates. Revenue per employee suits roles that earn money directly, such as sales; for other roles the pay with a value multiple you choose is fairer. "
         "The calculator holds no benchmark: the multiple is your assumption, and the page says which method it used.</p>",
         [("What is the cost of a vacancy?",
           "The value of the work that does not get done while a role is empty, plus what you pay for cover such as overtime or contractors. It grows with every working day the role stays open."),
          ("How do you calculate the cost of a vacancy?",
           "Take the value of one working day of the role, from revenue per employee or from its pay with a multiple, multiply by the working days the role has been open, and add what you paid for cover."),
          ("How long do roles stay open?",
           "It depends on the work. The “How to hire…” guides on this site show, for each kind of work, how long today’s open postings have been up.")],
         ["cost-per-hire", "job-description-checker", "interview-scorecard"], ["post-a-job/"])

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
         [('How do I calculate cost per hire?', "Add the internal costs (recruiters' time, interviews, referral bonuses) and the external costs (ads, agencies, assessments, background checks), then divide by the number of hires in the same period: the same structure as the ANSI/SHRM cost-per-hire standard, and how this calculator adds them up."),
          ('How can I estimate the cost of hiring an employee?', 'Cost per hire covers the hiring itself. The full first-year cost adds salary, benefits and taxes, equipment and the months it takes to be fully productive.'),
          ("How is cost per hire calculated?",
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
           "Give the most weight to what the person will do most of the time, and make the weights add up to 100 so each reads as a percent. Set them before you meet the first candidate; changing them afterwards to fit a favorite defeats the purpose."),
          ("How is the weighted score calculated?",
           "Multiply each rating by the weight of its criterion, add the results and divide by the sum of the weights. Ratings of 4, 5, 3, 4 and 4 with weights of 30, 25, 20, 15 and 10 give 4.05 out of 5.")],
         ["cost-per-hire", "job-description-checker", "boolean-search"], ["post-a-job/"])

    # ============================================================ added 2026-11-17: eleven more tools (letters, short texts, skills by job title, overtime)
    # A field that belongs to one choice of a select carries data-on="<select>:<values>"; tools.js shows it only for those values. A field that
    # exists once per choice is named <field>_<choice> (when_applied, goal_fair): each keeps its own label and example, and tools.js reads the one in use.
    on = lambda spec: f' data-on="{spec}"'
    sample = lambda text: f'<blockquote class="tl-ex">{e(text)}</blockquote>'      # a worked example in the page text: what the tool gives for its own sample details (tools_test.js compares the two)
    no_ai = lambda what: (f"Is the {what} written by AI?", f"No. It is a fill-in template: every sentence is assembled from the fields you complete. Nothing is generated, guessed or sent to a server, so the {what} holds only facts you typed.")

    # ------------------------------------------------------------ 30. follow-up email
    tool("follow-up-email", "seekers", "Follow-up email",
         "Five situations, from a week after applying to a recruiter who went quiet: a short, polite follow-up in two tones, with the day to send it.",
         "Follow-Up Email After Applying or an Interview",
         "Write a follow-up email after applying, after an interview with no reply or after a verbal offer. Five situations, two tones, and when to send each. Free.",
         "Write a follow-up email after applying or after an interview",
         "Follow up once, twice at most, in three or four sentences: say which job and when you were last in touch, that you are still interested, and ask one clear question. "
         "Silence after an application or an interview leaves people either waiting for weeks or writing every few days, and both hurt. "
         "Pick your situation, fill in the names and the dates, and the email is ready to copy, with the day to send it. It is a fill-in template, not AI: each sentence is built from what you type.",
         wrap("follow-up-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("situation", "Situation", [("applied", "A week after applying", True), ("interview", "After an interview, past the date they gave"), ("second", "Second follow-up, no reply to the first"),
                                                ("offer", "After a verbal offer, nothing in writing"), ("recruiter", "To a recruiter who went quiet")], cls="full")
              + _sel("tone", "Tone", [("friendly", "Friendly", True), ("brief", "Brief")])
              + _f("to", "Their first name", "Dana", mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job title", "Senior Backend Engineer", mode="")
              + _f("company", "Company (optional)", "Acme", mode="", auto="organization")
              + _f("when_applied", "When you applied (optional)", "on 4 November", mode="", hint="For example: last Monday, on 4 November.", show=on("situation:applied"))
              + _f("when_interview", "When the interview was (optional)", "on 4 November", mode="", hint="For example: last Monday, on 4 November.", show=on("situation:interview"))
              + _f("promised", "When they said you would hear (optional)", "by Friday, 13 November", mode="", hint="Finish the sentence “You said I would hear back …”.", show=on("situation:interview"))
              + _f("when_second", "When you first wrote (optional)", "last Tuesday", mode="", hint="Finish the sentence “I wrote …”.", show=on("situation:second"))
              + _f("when_offer", "When and how the offer was made (optional)", "on the phone last Thursday", mode="", hint="Finish the sentence “You offered me the job …”.", show=on("situation:offer"))
              + _f("when_recruiter", "When you last spoke (optional)", "two weeks ago", mode="", hint="Finish the sentence “We last spoke …”.", show=on("situation:recruiter"))
              + _area("add", "Something new to add (optional)", 2, "Since we were last in touch, I finished the cloud certificate the posting asks for.",
                      hint="One full sentence: a result, a course or a reference that was not in your application.") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("follow-up-email.txt") + "</div>"),
         "How the follow-up email is put together",
         "<p>Every version does three things in this order: it reminds the reader which job this is about and when you were last in touch, says in one line that you are still interested, "
         "and asks one question that can be answered in a sentence. The first line of the output is the subject.</p>"
         "<ul><li><strong>A week after applying</strong> asks whether the application arrived and when interviews start.</li>"
         "<li><strong>After an interview</strong> names the date you were given and asks for a new one.</li>"
         "<li><strong>The second follow-up</strong> says it is the last one and makes a “no” easy to send.</li>"
         "<li><strong>After a verbal offer</strong> asks for the offer in writing before you give notice.</li>"
         "<li><strong>To a recruiter</strong> asks whether the role is still moving, on hold or closed.</li></ul>"
         "<p>“Friendly” leaves room for the other person’s delays; “brief” is two or three sentences. The line under the email says when to send it. "
         "No AI is involved and nothing is sent anywhere: copy the text into your own email and send it yourself.</p>",
         [("How long should I wait before following up on a job application?",
           "About a week. If the posting gives a closing date, wait until a few days after it, because some employers read applications only once the posting has closed."),
          ("How do I follow up after an interview with no response?",
           "Wait until the working day after the date they gave you, or a week if they gave none. Thank them for the interview, say you are still interested and ask whether there is a new date for the decision."),
          ("How many times can I follow up?",
           "Twice: a first email, then a second one a week later that says it is your last. After that, put your time into other applications. A third message rarely changes anything."),
          ("What should the subject line of a follow-up email say?",
           "The job title and what the email is about, so it can be found later: “Following up on my application for Senior Backend Engineer”. For a second follow-up, reply to your first email so the earlier message sits underneath."),
          ("I got a verbal offer but nothing in writing. Should I follow up?",
           "Yes, after two or three working days. Ask when the written offer will arrive, and do not resign from your current job until you have the salary, the start date and the main terms in writing."),
          ("Is it rude to follow up with a recruiter who stopped replying?",
           "No. Recruiters handle many roles at once and expect to be asked. One clear question (is the role still moving, on hold or closed?) is easy to answer and tells you whether to keep waiting."),
          no_ai("email")],
         ["thank-you-email", "application-email", "job-search-calculator"], ["my-jobs/", "jobs/"],
         ex=("Follow-up email example: a week after applying", "<p>The form filled in with its sample details gives this email, in the friendly tone:</p>" + sample(EXAMPLE["follow-up-email"])))

    # ------------------------------------------------------------ 31. the email that carries a resume
    tool("application-email", "seekers", "Email to send a resume",
         "The short email that carries your resume: to a named person or a general address, with a referral or without, for a posted job or none.",
         "Email to Send a Resume: Template & Generator",
         "Write the short email that goes with your resume: for a posted job or none, to a named person or a general inbox, with a referral or without. Free, private.",
         "Write the email that goes with your resume",
         "Keep it to five or six sentences: which job, that your resume is attached, one result, and how to reach you. "
         "The email is read before the attachment is opened, and “Please find attached my resume” gives the reader no reason to open it. "
         "Choose whether the job is posted, whether you have a name to write to and whether someone referred you, and the email is ready to copy. It is a fill-in template, not AI.",
         wrap("application-email",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("kind", "The job", [("posted", "A posted job", True), ("speculative", "No job is posted")])
              + _f("to", "Their name (optional)", "Dana Lee", mode="", hint="With no name, the email opens “Dear Hiring Team” and asks to be passed on.")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job title", "Marketing Manager", mode="", hint="With no posting: the kind of work you want.")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("source", "Where you saw the job (optional)", SITE, mode="", show=on("kind:posted"))
              + _f("referrer", "Who referred you (optional)", "Sam Ortiz", mode="", hint="Ask them first: the employer may call them.")
              + _f("current", "Your current or latest job title (optional)", "marketing manager", mode="")
              + _f("years", "Years of experience (optional)", "6", mode="text")
              + _f("contact", "Phone or email (optional)", "alex@example.com", mode="", auto="email")
              + _area("proof", "One result (optional)", 2, "Last year I grew newsletter sign-ups from 8,000 to 31,000.", hint="A full sentence starting with “I”, with a number if you have one.")
              + _area("why", "Why this company (optional)", 2, "I have used your scheduling app with two teams, and I know why people stay with it.",
                      hint="One full sentence that could not be said about another employer.")
              + _f("link", "Link to your work (optional)", "alexmorgan.example/work", mode="", cls="full", hint="A portfolio, a code repository or your LinkedIn profile.") + "</div>"
              + '<div class="tl-checks">' + _check("cover", "I am attaching a cover letter too") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("application-email.txt") + "</div>"),
         "How the email is put together",
         "<p>The email has four short parts. The opening says which job it is about and that your resume is attached; with no posting, it says what work you want and that you know nothing is advertised. "
         "Then come one or two sentences on who you are, with one result, then why this company if you add it, and a close that says how to reach you.</p>"
         "<p>A <strong>name</strong> changes the greeting and the close: sent to a general address, the email asks for your resume to be passed to the person who is hiring. "
         "A <strong>referral</strong> moves into the first words and the subject, because it is the reason the email gets opened. "
         "The line under the email suggests a name for the attached file, such as Alex-Morgan-Resume.pdf, so it can be found again among a hundred files called “resume.pdf”.</p>"
         "<p>Fields you leave empty drop their sentences. No AI is involved and nothing is sent anywhere: copy the text into your own email and attach the file yourself.</p>",
         [("What do I write in an email when sending a resume?",
           "Which job you are applying for, that your resume is attached, one or two sentences on who you are with one result, and how to reach you. Five or six sentences are enough: the resume carries the detail."),
          ("What subject line should I use when emailing a resume?",
           "The job title and your name: “Application for Marketing Manager, Alex Morgan”. If someone referred you, put their name first, because it is the reason the email is opened. If the posting asks for a reference number or a set subject, use that."),
          ("Should the resume be a PDF or a Word file?",
           "Send what the posting asks for. If it does not say, a PDF keeps the layout the same on every screen. Name the file with your own name, not “resume.pdf”."),
          ("Is the email the same as a cover letter?",
           "It can stand in for one. If the posting asks for a cover letter, attach it and keep the email to a few lines. If it does not, this short email does the job of a letter."),
          ("Can I email a company that has no job posted?",
           "Yes. Say which kind of work you want, that you know nothing is advertised, and why this company. Ask them to keep your resume or to tell you who to write to. Some roles are filled before they are ever advertised."),
          ("How do I mention a referral in the email?",
           "In the first sentence and in the subject: “Sam Ortiz suggested I apply”. Ask the person first, because the employer may call them to check."),
          no_ai("email")],
         ["cover-letter", "follow-up-email", "referral-request"], ["resume/", "jobs/"],
         ex=("Example of an email to send with a resume", "<p>The form filled in with its sample details, a posted job with a named contact and a referral, gives this email:</p>" + sample(EXAMPLE["application-email"])))

    # ------------------------------------------------------------ 32. asking for a referral
    tool("referral-request", "seekers", "Referral request message",
         "Ask a close colleague, a distant contact or a stranger at the company to refer you: an email or a short LinkedIn message.",
         "Job Referral Request: Email & LinkedIn Message",
         "Ask for a job referral without making it awkward: wording for a close colleague, a distant contact or a stranger, as an email or a short LinkedIn message.",
         "Ask for a job referral, and make it easy to say yes or no",
         "Name the job, say in one line why you fit, offer to do the work of the referral yourself, and make it easy to say no. "
         "Asking a favor of someone you have not spoken to for years, or have never met, is the part people put off until the posting has closed. "
         "Choose how well you know the person and where you are writing, and the message is ready to copy. It is a fill-in template, not AI.",
         wrap("referral-request",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("who", "Who you are asking", [("close", "A close colleague", True), ("distant", "A distant contact"), ("stranger", "Someone I never met")])
              + _sel("channel", "Where you are writing", [("email", "Email", True), ("linkedin", "LinkedIn message")])
              + _f("to", "Their first name", "Sam", mode="")
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job title", "Data Analyst", mode="")
              + _f("company", "Company", "Acme", mode="", auto="organization")
              + _f("link", "Link to the posting (optional)", "acme.example/jobs/data-analyst", mode="", cls="full")
              + _f("by", "When the posting closes (optional)", "on Friday, 27 November", mode="", hint="Finish the sentence “The posting closes …”.", show=on("channel:email"))
              + _area("how_close", "How they know your work", 2, "the three years we shared on the billing team at Example Co", hint="Finish the sentence “You know my work from …”.", show=on("who:close"))
              + _area("how_distant", "Where you know each other from", 2, "the analytics meetup in Leeds last spring", hint="Finish the sentence “We know each other from …”.", show=on("who:distant"))
              + _area("how_stranger", "Why you are writing to this person", 2, "I read your post about how the data team plans its quarters", hint="Finish the sentence “I am writing to you because …”.", show=on("who:stranger"))
              + _area("fit", "Why you fit, in one sentence", 2, "I have built sales reports for two retailers, the work this role describes.", hint="A full sentence starting with “I”.") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("referral-request.txt") + "</div>"),
         "How the referral request is put together",
         "<p>The three versions ask for different things, because the three people can give different things. A <strong>close colleague</strong> is asked for the referral directly, "
         "and you offer to send your resume and a few lines for the referral form. A <strong>distant contact</strong> is asked whether they are comfortable referring you, or who is hiring. "
         "A <strong>stranger</strong> is not asked to vouch for you at all: the message asks for a short call about the team and leaves the referral to them.</p>"
         "<p>Every version makes it easy to decline, because a person who feels cornered writes a weak referral or none. The email has a subject line and room for the closing date of the posting. "
         "The LinkedIn message is one short paragraph, and the line under it shows its length in characters.</p>"
         "<p>No AI is involved and nothing is sent anywhere: copy the text and send it yourself.</p>",
         [("How do I ask someone for a job referral?",
           "Name the exact job, say in one sentence why you fit, offer to send your resume and a few lines they can paste into the referral form, and say that it is fine to decline. Add the link to the posting so they do not have to search for it."),
          ("Can I ask a stranger for a referral?",
           "Not in the first message. A stranger cannot vouch for work they have not seen. Ask for a short call or two questions about the team instead. If the talk goes well, the person may offer the referral themselves."),
          ("Should I ask by email or on LinkedIn?",
           "Use the channel where you already talk to the person. For someone you do not know, LinkedIn is the usual place, and the message must be short. For a former colleague, email leaves room for the link and your resume."),
          ("What should I send with a referral request?",
           "The link to the posting, your current resume and two or three lines about why you fit that the person can copy into the company’s referral form. The less work it is, the more likely it gets done."),
          ("What if they do not answer?",
           "Wait a week and send one short reminder. If there is still no answer, apply without the referral before the posting closes. Silence usually means a full inbox, not a judgment of you."),
          ("Do employees get paid for referring someone?",
           "Many companies pay a bonus to an employee whose referral is hired, so your request is not only a favor. Whether your contact gets one depends on their employer’s rules."),
          no_ai("message")],
         ["linkedin-connection-message", "application-email", "reference-request-email"], ["jobs/"],
         ex=("Referral request example: an email to a close colleague", "<p>The form filled in with its sample details gives this email:</p>" + sample(EXAMPLE["referral-request"])))

    # ------------------------------------------------------------ 33. LinkedIn connection note
    tool("linkedin-connection-message", "seekers", "LinkedIn connection message",
         "A note for a connection request that fits LinkedIn’s limit (200 characters on a free account, 300 with Premium), counted as you type, for five kinds of people.",
         "LinkedIn Connection Request Message Generator",
         "Write a LinkedIn connection request note inside the 300-character limit: to a recruiter, a hiring manager, an alumnus or someone you met. Counted as you type.",
         "Write a LinkedIn connection message that fits in 300 characters",
         "Say who you are, why this person and what you would like, in under 300 characters: that is all the note on a connection request can hold. "
         "A request with no note leaves the other person guessing why you are asking, and LinkedIn stops a long one at the limit. "
         "Pick who you are writing to and fill in a few fields. You get two notes with a character count, and when a note runs over, the least important line is left out for you. These are fill-in templates, not AI.",
         wrap("linkedin-connection-message",
              '<div class="card tl-form"><div class="tl-grid">'
              + _sel("kind", "Who you are writing to", [("recruiter", "A recruiter", True), ("manager", "A hiring manager"), ("alumni", "Someone from my school"), ("event", "Someone from an event"),
                                                        ("role", "Someone in a job I want")])
              + _sel("limit", "Limit", [("300", "300 characters", True), ("200", "200 characters")], hint="Some free accounts get only 200.")
              + _f("to", "Their first name", "Dana", mode="")
              + _f("name", "Your first name (optional)", "Alex", mode="", auto="given-name", hint="Goes at the end if there is room.")
              + _f("me", "What you do, in a few words", "product designer with six years in fintech", mode="", cls="full", hint="Finish the sentence “I am a …”.")
              + _f("company", "Their company (optional)", "Acme", mode="", auto="organization")
              + _f("job", "The job title this is about", "Senior Product Designer", mode="", hint="The role you applied for, are asking about or want.", show=on("kind:recruiter manager role"))
              + _f("school", "The school you both went to", "Leeds University", mode="", show=on("kind:alumni"))
              + _f("event", "Where you met", "the Leeds Design Meetup", mode="", show=on("kind:event"))
              + _area("detail", "One line about you (optional)", 2, "I have led design for two payment apps.", hint="A full sentence. It is the first thing left out when the note is too long.", show=on("kind:recruiter manager alumni role"))
              + _area("detail_event", "Something from your conversation (optional)", 2, "Your point about testing prices with real customers stayed with me.",
                      hint="A full sentence. It is kept as long as the note has room.", show=on("kind:event")) + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _private(" The notes are assembled inside your browser and are never sent to LinkedIn or anywhere else.")
              + _board("Characters used", "Say who you are writing to and what you do to see the note and how much of the limit it uses.")
              + '<div class="tl-out3" aria-live="polite">' + vcard(1, "Note 1") + vcard(2, "Note 2") + "</div>"),
         "How the note is built and kept inside the limit",
         "<p>Each note is built from short parts: the greeting, who you are, why this person, and one request. The two notes say it in different ways: the first states what you want, "
         "the second asks a question that is easy to answer.</p>"
         "<p><strong>The limit.</strong> LinkedIn allows 300 characters in the note on a connection request, spaces included. Some free accounts are given a shorter note of 200 characters, so you can switch the limit. "
         "When a note runs over, the least important parts are left out: your extra line first, then your name at the end, then the line about you. In a note to someone you met, the line about your conversation is kept longest. The count under each note says what was left out. "
         "A note is cut short only when a single field is itself too long, and then at the end of a sentence where it can.</p>"
         "<p>Nothing is sent to LinkedIn or anywhere else: copy the note and paste it into the box that opens when you choose “Add a note”.</p>",
         [("How long can a LinkedIn connection message be?",
           "300 characters with Premium, spaces included; free accounts are limited to 200 characters and a few personalized notes a month. This page counts every character and keeps both notes inside the limit you choose."),
          ("What should I write in a LinkedIn connection request?",
           "Who you are, why you are writing to this person and not to someone else, and one small request. Leave your career story for later: the note only has to get the request accepted."),
          ("Should I send a connection request with a note or without one?",
           "With a note when the person does not know you. Without one they see only your name and headline, and have to guess why you are asking."),
          ("How do I message a recruiter on LinkedIn?",
           "Say what you do in a few words, name the role or the company you saw them recruit for, and offer to send your resume. Use the job title as it appears in the posting, because that is the word a recruiter searches for."),
          ("Is it OK to connect with the hiring manager after I apply?",
           "Yes, once. Say that you applied and for which role, and either leave it there or ask one short question. Do not ask them to look at your application in the note."),
          ("What happens if my note is longer than the limit?",
           "LinkedIn does not let you type past the limit. Here the note is shortened for you: the least important line goes first, usually your extra line, then your name at the end, and the count shows what was left out."),
          ("Does this page send anything to LinkedIn?",
           "No. The notes are assembled in your browser. Copy one and paste it into the box that opens when you choose “Add a note” on LinkedIn.")],
         ["referral-request", "linkedin-headline", "linkedin-summary"], ["jobs/"],
         ex=("LinkedIn connection message example: a note to a recruiter", f'<p>The form filled in with its sample details gives this note, {len(EXAMPLE["linkedin-connection-message"])} characters long:</p>'
             + sample(EXAMPLE["linkedin-connection-message"])))

    # ------------------------------------------------------------ 34. professional bio
    tool("professional-bio", "seekers", "Professional bio generator",
         "A short bio in the first or the third person, in three lengths at once: one line, about 50 words and about 100, for LinkedIn, a company page or a conference.",
         "Professional Bio Generator: Short & Long Bio",
         "Build a professional bio from a few facts: first or third person, one line, about 50 words or about 100, for LinkedIn, a company page or a conference. Free.",
         "Write a short professional bio without sounding like a brochure",
         "A good bio says who you are, what you work on and one thing you did, in that order, and stops. "
         "Writing about yourself is hard: the first draft comes out as a list of job titles, or as praise nobody would say aloud. "
         "Fill in a few facts and choose first or third person. You get the bio in three lengths at once: one line, about 50 words and about 100 words. It is a fill-in template, not AI, so nothing is invented.",
         wrap("professional-bio",
              '<div class="card tl-form"><div class="tl-grid wide">'
              + _sel("place", "Where the bio goes", [("linkedin", "LinkedIn, personal site", True), ("company", "A company “team” page"), ("conference", "A conference program")])
              + _sel("person", "Written in", [("first", "First person: “I am…”", True), ("third", "Third person: “Alex is…”")])
              + _sel("pronoun", "Pronoun", [("she", "She"), ("he", "He"), ("they", "They", True), ("name", "None: repeat the name")], show=on("person:third"))
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name")
              + _f("role", "Job title", "senior backend engineer", mode="")
              + _f("company", "Company (optional)", "Acme", mode="", auto="organization")
              + _f("years", "Years of experience (optional)", "8", mode="text")
              + _f("focus", "What you work on", "payment systems for online shops", mode="", hint="Finish the sentence “I work on …”.")
              + _f("strengths", "Two or three strengths (optional)", "Python, PostgreSQL, system design", mode="", hint="Separate them with commas.")
              + _f("degree", "Degree or certificate (optional)", "a BSc in computer science from the University of Leeds", mode="", cls="full", hint="Finish the sentence “I hold …”.")
              + _area("proof", "One recent result (optional)", 2, "rebuilt the checkout for two million shoppers and cut failed payments by 30%",
                      hint="Finish the sentence “Recently, I …”, starting with a verb in the past tense.")
              + _area("before", "What you did before (optional)", 2, "ran the billing team at Example Co for five years", hint="Finish the sentence “Before that, I …”.")
              + _area("extra_linkedin", "What you are open to (optional)", 2, "senior backend roles and conference talks", hint="Finish the sentence “I am open to …”.", show=on("place:linkedin"))
              + _area("extra_company", "What people come to you for (optional)", 2, "anything about refunds, chargebacks and payment providers",
                      hint="Finish the sentence “Colleagues and customers come to me for …”.", show=on("place:company"))
              + _area("extra_conference", "What your talk is about (optional)", 2, "moving a payment system to a new database without downtime", hint="Finish the sentence “I will talk about …”.", show=on("place:conference"))
              + _f("outside", "Outside work (optional)", "coaching a youth football team", mode="", hint="Finish the sentence “Outside work, you will find me …”.")
              + _f("contact", "Where to reach you (optional)", "alex@example.com", mode="", auto="email") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _private(" The bio is assembled inside your browser and is never sent anywhere.")
              + '<div class="tl-out3" aria-live="polite">' + vcard(1, "One line") + vcard(2, "Short, about 50 words") + vcard(3, "Long, about 100 words") + "</div>"),
         "How the three lengths of the bio are built",
         "<p>All three lengths are built from the same facts, in a fixed order.</p>"
         "<ul><li><strong>One line:</strong> your name or “I”, your job title, your company and what you work on. It fits under a photo or in a list of speakers.</li>"
         "<li><strong>About 50 words:</strong> adds your years of experience, your strengths and one recent result.</li>"
         "<li><strong>About 100 words:</strong> adds what you did before, your degree, one line that depends on where the bio goes, a line about life outside work and how to reach you.</li></ul>"
         "<p><strong>Where the bio goes</strong> changes the text. For LinkedIn the long bio says what you are open to. For a company page it starts from your work at the company and says what people come to you for. "
         "For a conference it puts your talk in the second sentence.</p>"
         "<p><strong>First or third person.</strong> Use “I” where you speak for yourself, such as LinkedIn. Use the third person where someone else introduces you, such as a program or a team page. "
         "In the third person you choose the pronoun, or none: the bio then repeats your first name. The word counts under each text are real counts, so a length comes out shorter when you leave fields empty.</p>",
         [("How do I write a short professional bio?",
           "Start with your name and job title, say what you work on, and add one result that shows you are good at it. Two or three sentences, about 50 words, are enough for most uses."),
          ("Should a bio be in the first or the third person?",
           "First person (“I am…”) on LinkedIn and personal sites, where you speak for yourself. Third person (“Alex is…”) on company pages, in conference programs and in press material, where someone else is presenting you."),
          ("How long should a professional bio be?",
           "One line for a byline or a list of speakers, about 50 words for a team page or a profile, and about 100 words when you are asked for a full bio. Past that, most readers stop."),
          ("What should I leave out of a bio?",
           "Adjectives about yourself (passionate, dynamic, results-driven), a full list of every job you have had, and anything you would not say when introducing yourself in person. A fact and a number say more than praise."),
          ("Can I mention hobbies in a professional bio?",
           "One line at the end is fine and makes the bio easier to remember. Keep it specific, such as coaching a youth team, and leave it out of the shortest version."),
          ("What is a speaker bio?",
           "The short text a conference prints next to your name. It says who you are, where you work and what your talk is about, usually in the third person and in 50 to 100 words."),
          no_ai("bio")],
         ["linkedin-summary", "linkedin-headline", "elevator-pitch"], ["resume/"],
         ex=("Professional bio example in about 50 words", "<p>The form filled in with its sample details gives this short bio, in the first person, for LinkedIn:</p>" + sample(EXAMPLE["professional-bio"])
             + "<p>The same facts in one line:</p>" + sample(EXAMPLE["professional-bio-one"])))

    # ------------------------------------------------------------ 35. LinkedIn About section
    tool("linkedin-summary", "seekers", "LinkedIn summary generator",
         "A few answers become the About section of your profile, in three shapes, counted against LinkedIn’s 2,600 characters.",
         "LinkedIn Summary Generator: About Section",
         "Write the About section of your LinkedIn profile from a few answers: role, years, strengths, results and what you want next. Counted against 2,600 characters.",
         "Write your LinkedIn summary from a few answers",
         "The About section should say what you do, for whom and what you have to show for it, with the main point in the first two lines. "
         "Most are left empty, or filled with words like “passionate” and “results-driven” that tell a recruiter nothing. "
         "Answer a few questions: your role, your years, your strengths, up to three results with a number, and what you want next. "
         "You get the text in the shape you choose, with a count against LinkedIn’s limit of 2,600 characters. It is a fill-in template, not AI.",
         wrap("linkedin-summary",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("style", "Shape", [("story", "Short paragraphs", True), ("list", "A list, easy to skim"), ("short", "One short paragraph")])
              + _f("role", "Your job title", "senior backend engineer", mode="")
              + _f("years", "Years of experience (optional)", "8", mode="text")
              + _f("strengths", "Your three strongest skills or fields", "Python, PostgreSQL, payment systems", mode="", cls="full", hint="Separate them with commas.")
              + _area("who", "Who you work with or for (optional)", 2, "online shops that have outgrown their first payment system", hint="Finish the sentence “I work with …”.")
              + _area("how", "How you work, in your own words (optional)", 2, "I like to start from the numbers the business already tracks and work back to the code.",
                      hint="One or two full sentences. This is the part that sounds like you.")
              + _area("proofs", "Results, one per line (up to three)", 4, "I rebuilt the checkout for two million shoppers and cut failed payments by 30%.\nI moved 30 services to a new database with no downtime.\n"
                      "I cut the monthly cloud bill from $41,000 to $27,000.", hint="Full sentences starting with “I”, each with a number.")
              + _area("next", "What you want next (optional)", 2, "senior backend roles at product companies", hint="Finish the sentence “I am now looking for …”.")
              + _f("contact", "How to reach you (optional)", "alex@example.com", mode="", auto="email", cls="full", hint="Left empty, the text says “a message here on LinkedIn”.") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>"
              + _private(" The text is assembled inside your browser and is never sent to LinkedIn or anywhere else.") + "</div>"
              + paper("linkedin-about.txt") + "</div>"
              + _board("Characters used", "Answer the questions to see the text and how much of LinkedIn’s 2,600 characters it uses.")),
         "How the About section is built and counted",
         "<p>The text is built in a fixed order: who you are and for whom you work, how you work, what you do best, your results, what you want next and how to reach you. "
         "The opening comes first because LinkedIn shows only the first lines of the About section until a reader presses “see more”.</p>"
         "<ul><li><strong>Short paragraphs</strong> reads like a person talking, and suits most profiles.</li>"
         "<li><strong>A list</strong> puts your strengths and your results on separate lines, for readers who skim.</li>"
         "<li><strong>One short paragraph</strong> uses your first result only, for a profile that already says a lot elsewhere.</li></ul>"
         "<p><strong>The limit.</strong> LinkedIn allows 2,600 characters in the About section, spaces and line breaks included. The board shows how many you have used. "
         "If your answers run over, results are left out from the last one, and only then is the text cut at the end of a sentence. "
         "The board also quotes about the first 300 characters, the part this page treats as visible before “see more”; the exact cut depends on the screen.</p>"
         "<p>The page arranges your words and adds no claims of its own. Nothing is sent to LinkedIn or anywhere else: copy the text and paste it into your profile.</p>",
         [("What should I write in my LinkedIn summary?",
           "What you do and for whom, what you are good at, two or three results with a number, and what you want next. Write it in the first person, the way you would say it to someone you have just met."),
          ("How long should a LinkedIn summary be?",
           "LinkedIn allows 2,600 characters, but few people read that much. As a rule of thumb, three to five short paragraphs are enough. Put the main point in the first two lines, because the rest is hidden until the reader presses “see more”."),
          ("Is the LinkedIn summary the same as the About section?",
           "Yes. LinkedIn used to call it the summary and now labels it “About”. It is the free-text box near the top of your profile, under your name and headline."),
          ("Should the About section be in the first person?",
           "Yes. It is your own profile, so “I” reads naturally. The third person suits a company page or a conference program; the professional bio generator on this site writes both."),
          ("What should I put in the About section when I am looking for work?",
           "Say which roles you want in plain words, such as “senior backend roles at product companies”, and how to reach you. Use the job titles and the skills that postings use, because those are the words recruiters search for."),
          ("Do keywords in the About section matter?",
           "They help you get found, because recruiters search profiles by job title and skill. Use the title and the skills a posting would name, where they are true, inside normal sentences. A bare list of keywords reads as stuffing."),
          no_ai("text")],
         ["linkedin-headline", "linkedin-review", "professional-bio"], ["resume/"],
         ex=("LinkedIn summary example for the About section", f'<p>The form filled in with its sample details gives this text in short paragraphs, {len(EXAMPLE["linkedin-summary"]):,} of 2,600 characters:</p>'
             + sample(EXAMPLE["linkedin-summary"])))

    # ------------------------------------------------------------ 36. elevator pitch
    tool("elevator-pitch", "seekers", "Elevator pitch generator",
         "What you do, what you do best and one result become a 30-second pitch of about 75 words, timed at 150 words a minute.",
         "Elevator Pitch Generator: 30 Seconds, Timed",
         "Build a 30-second elevator pitch of about 75 words for a job fair, the start of an interview or a networking event, timed at 150 words a minute. Free, private.",
         "Build a 30-second elevator pitch and see how long it runs",
         "A 30-second pitch is about 75 words: who you are, what you do best, one result, and what you want from this conversation. "
         "Asked “so, what do you do?”, most people either give a job title and stop, or talk for three minutes. "
         "Fill in four short answers and pick where you will say it. The page puts the pitch together, counts the words and estimates the time at 150 words a minute. It is a fill-in template, not AI.",
         wrap("elevator-pitch",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("where", "Where you will say it", [("fair", "At a job fair", True), ("interview", "To open an interview"), ("networking", "At a networking event")])
              + _f("name", "Your name", "Alex Morgan", mode="", auto="name", show=on("where:fair networking"))
              + _f("role", "What you do", "data analyst", mode="", hint="Finish the sentence “I’m a …”.")
              + _f("years", "Years of experience (optional)", "4", mode="text")
              + _f("company", "Company you are talking to (optional)", "Acme", mode="", auto="organization", show=on("where:fair interview"))
              + _f("job", "Job you are interviewing for (optional)", "Senior Data Analyst", mode="", show=on("where:interview"))
              + _area("best", "What you do best", 2, "turning messy sales data into reports people actually use", hint="Finish the sentence “What I do best is …”.")
              + _area("proof", "One recent result", 2, "built a weekly report that replaced six spreadsheets and saves the team a day a week", hint="Finish the sentence “Recently I …”, with a number if you have one.")
              + _area("goal_fair", "What you are looking for", 2, "an analyst role on a pricing team", hint="Finish the sentence “I’m looking for …”.", show=on("where:fair"))
              + _area("goal_interview", "Why this role", 2, "you need someone to own reporting for a growing sales team", hint="Finish the sentence “This role caught my eye because …”.", show=on("where:interview"))
              + _area("goal_networking", "What you are curious about", 2, "how other teams forecast demand", hint="Finish the sentence “Right now I’m curious about …”.", show=on("where:networking")) + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("elevator-pitch.txt") + "</div>"
              + _board("Speaking time", "Say what you do, what you do best and one result to see how long the pitch takes to say.")
              + '<div class="tl-detail" id="tl-detail"></div>'),
         "How the pitch is built and timed",
         "<p>The pitch has four parts in a fixed order: who you are, what you do best, one result, and what you want from this conversation. The last part changes with the place.</p>"
         "<ul><li><strong>At a job fair</strong> it starts with your name, says what role you are looking for and ends with a question for the person at the stand.</li>"
         "<li><strong>To open an interview</strong> it skips your name, connects your result to the role and offers to go deeper. It works as a short answer to “tell me about yourself”.</li>"
         "<li><strong>At a networking event</strong> it is looser, says what you are curious about and hands the conversation back with a question.</li></ul>"
         "<p><strong>Speaking time</strong> = words ÷ 150 × 60 seconds. 150 words a minute is an ordinary speaking pace, so 30 seconds is about 75 words. 25 to 35 seconds passes; "
         "20 to 24 and 36 to 45 seconds are marked to check; under 20 or over 45 seconds is marked to fix, and the page names your longest part. The result is also checked for a number.</p>"
         "<p>The pace and the thresholds are this page’s rules of thumb. Say the pitch aloud once with a timer, then change the words until it sounds like you. A pitch that sounds memorized works against you.</p>",
         [("What is an elevator pitch?",
           "A short spoken introduction, about 30 seconds long, that says who you are, what you are good at and what you are looking for. The name comes from the idea of explaining yourself during a ride in a lift."),
          ("How long should an elevator pitch be?",
           "About 30 seconds, which is roughly 75 words at an ordinary speaking pace of 150 words a minute. At a job fair or a networking event the other person should get a turn within half a minute."),
          ("What should a 30-second pitch include?",
           "Four things: who you are, what you do best, one result with a number, and what you want from this conversation. End with a question, so that it becomes a conversation and not a speech."),
          ("How do I use an elevator pitch in an interview?",
           "As the short answer to “tell me about yourself”: who you are, one result, and why this role. Then stop and let the interviewer choose what to ask about. For a longer answer, the interview answer builder on this site times 60 to 90 seconds."),
          ("How do I keep a pitch from sounding rehearsed?",
           "Learn the four parts, not the sentences. Say it aloud a few times in different words, and use short forms such as “I’m” and “I’d”, as the page does. If you lose your place, the order still carries you."),
          ("What if I have no work experience?",
           "Use a project, a course, volunteering or a part-time job for the result. “I built a stock model for a class project that a local shop now uses” does the same work as a result from a job."),
          no_ai("pitch")],
         ["interview-answer-builder", "professional-bio", "linkedin-connection-message"], ["jobs/"],
         ex=("Elevator pitch example: 30 seconds at a job fair", "<p>The form filled in with its sample details gives this pitch: " + EXAMPLE["elevator-pitch-n"] + "</p>" + sample(EXAMPLE["elevator-pitch"])))

    # ------------------------------------------------------------ 37. resume summary
    tool("resume-summary", "seekers", "Resume summary generator",
         "Job title, skills and one result become a two-to-three line resume summary, worded for your level: no experience, a few years, senior, manager or career changer.",
         "Resume Summary Generator by Experience Level",
         "Write a two-to-three line resume summary for your level: no experience, a few years, senior, manager or career changer. From your title, skills and one result.",
         "Write a resume summary in two or three lines",
         "A resume summary is two or three lines at the top of the page: your job title, your strongest skills and one result with a number. "
         "It is the first thing a recruiter reads, and “hard-working team player seeking a challenging role” could be anyone. "
         "Pick your level and fill in a few fields. You get the summary in two wordings, with the space each takes on the page. It is a fill-in template, not AI: every fact in it is one you typed.",
         wrap("resume-summary",
              '<div class="card tl-form"><div class="tl-grid wide">'
              + _sel("level", "Your level", [("none", "No experience yet"), ("some", "A few years’ experience", True), ("senior", "Senior"), ("manager", "Manager"), ("changer", "Changing career")])
              + _f("role", "Job title you are applying for", "data analyst", mode="")
              + _f("years", "Years of experience", "4", mode="text", show=on("level:some senior manager"))
              + _f("skills", "Your three strongest skills", "SQL, Excel, Tableau", mode="", hint="Separate them with commas. Use the words the posting uses.")
              + _f("study_none", "Degree, course or certificate", "a BSc in Economics (2026)", mode="", hint="Finish the sentence “I have …”.", show=on("level:none"))
              + _f("from_none", "Where your practice comes from (optional)", "a six-month internship at a logistics firm", mode="", hint="An internship, a project, volunteering.", show=on("level:none"))
              + _f("scope", "What you are responsible for (optional)", "pricing analytics for 300 stores", mode="", hint="Finish the sentence “I am responsible for …”.", show=on("level:senior"))
              + _f("team", "The team you lead", "a team of 12 analysts", mode="", hint="Finish the sentence “I lead …”.", show=on("level:manager"))
              + _f("from_changer", "The work you come from", "eight years of teaching mathematics", mode="", hint="Finish the sentence “I bring …”.", show=on("level:changer"))
              + _f("study_changer", "Course or certificate for the new work (optional)", "a nine-month data analytics course", mode="", hint="Finish the sentence “I completed …”.", show=on("level:changer"))
              + _area("result", "One result", 2, "cut month-end close from 8 days to 5 by automating reconciliations", hint="Start with a verb in the past tense and add a number: cut…, built…, grew…") + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _private(" The summary is assembled inside your browser and is never sent anywhere.")
              + '<div class="tl-out3" aria-live="polite">' + vcard(1, "Summary 1") + vcard(2, "Summary 2") + "</div>"),
         "How the summary is worded for each level",
         "<p>The summary is written without “I”, as resumes are, and each level puts a different fact first.</p>"
         "<ul><li><strong>No experience yet:</strong> your degree or course, the skills you can already use, and a result from an internship or a project.</li>"
         "<li><strong>A few years:</strong> your title, your years and your skills, then one result.</li>"
         "<li><strong>Senior:</strong> what you are responsible for comes before the list of skills.</li>"
         "<li><strong>Manager:</strong> the team you lead comes first, and the skills go last.</li>"
         "<li><strong>Changing career:</strong> the work you come from, the course that bridges the gap, and a result that carries over.</li></ul>"
         "<p>You get two wordings of the same facts. Wordings that come out identical are shown once, and the second one needs a result, or for a manager a team. "
         "Under each you see the word count and about how many lines it takes on a one-column resume, at about 100 characters a line. That figure is an estimate: your font and margins change it. "
         "If the result has no number, the line under the summary says so.</p>"
         f'<p>The page arranges your words and adds no claims of its own, so write only what is true. Put the summary under your name in the <a href="{P}/resume/">resume builder</a>.</p>',
         [("What is a resume summary?",
           "Two or three lines at the top of a resume, under your name, that say what you do, what you are best at and one thing you achieved. It replaces the old “objective” line, which said what you wanted and not what you offer."),
          ("How long should a resume summary be?",
           "Two to three lines, about 30 to 50 words. A recruiter reads it in a few seconds, and anything longer pushes your experience down the page."),
          ("How do I write a resume summary with no experience?",
           "Lead with your degree or course and the skills you can already use, then give one result from an internship, a project, volunteering or a part-time job. Say which first role you are looking for."),
          ("What is the difference between a resume summary and an objective?",
           "A summary says what you bring: skills and a result. An objective says what you want. Employers read for the first, so use a summary. Only a career changer or a first-time applicant needs a line about the role they are aiming for."),
          ("Should I write the summary in the first person?",
           "Without a pronoun: “Data analyst with 4 years of experience”, not “I am a data analyst”. That is the convention on resumes, and it saves space."),
          ("Do I need a different summary for every job?",
           "Change the job title and the skills to the words the posting uses, and pick the result closest to what that employer needs. The rest can stay. The resume skills tool on this site shows which skills postings for your job title name most."),
          no_ai("summary")],
         ["resume-skills", "resume-bullet-builder", "resume-review"], ["resume/"],
         ex=("Resume summary example with a few years of experience", "<p>The form filled in with its sample details gives these two wordings:</p>" + sample(EXAMPLE["resume-summary"]) + sample(EXAMPLE["resume-summary-2"])))

    # ------------------------------------------------------------ 38. skills to put on a resume, by job title (from today's postings)
    # build.py counts, for each kind of work that is a job title, the skills its postings name; the same rows go to data/role-skills.json for tools.js.
    RS = list(role_skills)
    pct = lambda k, n_: "under 1%" if 100 * k < n_ else f"{(200 * k + n_) // (2 * n_)}%"      # rounds halves up, as tools.js does
    if RS and skill_slug:
        top_s, top_nm, top_n, top_sk = RS[0]
        low = lambda nm: nm if sum(c.isupper() for c in nm.split()[0]) >= 2 else nm[0].lower() + nm[1:]        # "Data analyst" inside a sentence; "QA engineer" keeps its capitals
        rs_rows = "".join(
            f'<tr><td><a href="{P}/roles/{s_}/">{e(nm_)}</a></td><td class="num">{n_:,}</td><td>'
            + ", ".join(f'<a href="{P}/skills/{skill_slug(t)}/">{e(t)}</a> <span class="note">{pct(k, n_)}</span>' for t, k in sk_[:6])
            + f'</td><td><a href="{P}/tools/resume-skills/?role={s_}">All {len(sk_)}</a></td></tr>' for s_, nm_, n_, sk_ in RS[:10])
        rs_table = ('<div class="tablewrap"><table><tr><th>Job title</th><th>Open postings</th><th>Skills named most, with the share of postings that name each</th><th>In the tool</th></tr>' + rs_rows + "</table></div>"
                    f'<p class="note">Counted on {DATE} from the postings open on this site whose title contains the job title or a close variant. The ten job titles with the most postings are shown; '
                    f'the tool above has all {len(RS)}. <a href="{P}/skills/">All skills</a> · <a href="{P}/categories/">All kinds of work</a></p>')
        rs_first = ", ".join(f"{pct(k, top_n)} name {t}" for t, k in top_sk[:3])
        tool("resume-skills", "seekers", "Resume skills by job title",
             "Pick a job title and see the skills that today’s postings for it name most, with the share of postings, and copy a ready Skills line.",
             "Skills to Put on a Resume, by Job Title",
             f"Skills to put on a resume for {len(RS)} job titles, counted from today’s open postings: the share of postings that name each skill, and a Skills line to copy.",
             "Skills to put on a resume, by job title",
             "List first the skills that postings for your job title name most often, in the words they use. "
             "Lists of “top resume skills” are the same for every job and never say where they come from. "
             f"This page counts the skills named in the postings open on this site today, for {len(RS)} job titles. "
             f"Of the {top_n:,} open {low(top_nm)} postings, for example, {rs_first}. Pick your job title, tick the skills you really have and copy the Skills line.",
             wrap("resume-skills",
                  '<noscript><p class="note">The table further down this page shows the ten most common job titles and works without JavaScript.</p></noscript>'
                  '<div class="card tl-form"><div class="tl-grid">'
                  + _sel("role", "Job title", [(s_, nm_, s_ == top_s) for s_, nm_, _, _ in sorted(RS, key=lambda r: r[1].lower())], hint=f"{len(RS)} job titles whose postings name tools often enough to count.", cls="full")
                  + _sel("top", "Skills in the line", [("5", "The 5 named most"), ("8", "The 8 named most"), ("10", "The 10 named most", True), ("15", "All of them, up to 15")],
                         hint="You can tick and untick single skills below.") + "</div>"
                  + '<div class="tl-actions"><button class="btn ghost sm tl-end" type="button" data-clear>Start again</button></div></div>'
                  + f'<p class="note tl-priv"><b>Today’s postings</b>Counted on {DATE} from the jobs open on this site. A skill here is a tool, a programming language, a certificate, a license or a spoken language that a posting names; '
                    'soft skills such as “communication” are not counted. Your choices stay in your browser.</p>'
                  + _board("Skills employers name", "Loading today’s figures…")
                  + '<div class="tl-detail" id="tl-detail"></div>'),
             "How the skills are counted",
             f"<p>Every posting on this site is read from the employer’s own careers page. Its text is searched for the {n_skills} skills this site tracks: programming languages, tools, platforms, certificates, licenses and spoken languages, "
             "including their usual spellings (“Postgres” counts as PostgreSQL). A posting belongs to a job title when its own title contains that title or a close variant.</p>"
             "<p>For each job title the page counts how many of its postings name each skill. <strong>The percent</strong> is that count divided by the number of postings for the title. "
             "A skill counts once per posting, however often the text repeats it. Up to 15 skills are shown for a title. A skill is left out when fewer than three postings, or fewer than 5% of them, name it.</p>"
             "<p><strong>Which job titles are listed.</strong> A title needs at least 20 open postings, at least three skills that pass that test, and its most named skill in a tenth of its postings or more. "
             "Postings for many sales, legal and office jobs describe duties and rarely name tools, so those titles are left out instead of being shown with thin figures.</p>"
             "<p><strong>What is not counted:</strong> soft skills such as communication or teamwork, which postings word in too many ways to count reliably, and anything outside our list. "
             "So read the result as “which tools, languages and certificates to name”, not as everything the job needs. A skill named in half of the postings is close to expected; one named in 5% is a bonus.</p>"
             "<p>The Skills line joins the skills you tick, most named first. Tick only what you can show in an interview: a recruiter who searches for a skill will ask about it.</p>",
             [("What skills should I put on my resume?",
               "The ones that postings for your job title name, where you really have them, in the posting’s own words. Pick your job title above to see which skills today’s postings name most, and in what share of them."),
              ("How many skills should a resume list?",
               "As a rule of thumb, 8 to 12 in the skills section, the most relevant first. A long list hides the ones that matter, so the page lets you copy a line of 5, 8, 10 or 15."),
              ("Where do these figures come from?",
               f"From the job postings open on this site, read from employers’ own careers pages. On {DATE} the tool covers {len(RS)} job titles. Nothing comes from surveys or from other sites’ lists."),
              ("Why are soft skills like communication not in the list?",
               "Because they cannot be counted reliably: every posting words them differently. Show them through results in your experience section. “Trained 15 new colleagues” says more than the word “leadership”."),
              ("Should I list a skill I am still learning?",
               "Only if you say so: “Python (basic)” is honest and is still found by a search. Listing a skill you cannot use gets you into interviews you cannot pass."),
              ("Where on the resume do the skills go?",
               "In a short Skills section and, more importantly, inside the lines about your jobs, next to what you did with them. A skill that appears only in a list tells the reader nothing about how well you know it."),
              ("Why is my job title not in the list?",
               "A title is listed only when at least 20 postings for it are open and they name tools often enough to count. Postings for many sales, legal and office jobs describe duties instead. "
               "Try a broader title, or paste one posting into the keyword finder on this site to see the skills it names."),
              ("How often do the figures change?",
               "With every update of the site, several times a day, as postings open and close. The date above the result is the day of the count.")],
             ["resume-summary", "job-description-keywords", "resume-match"], ["resume/", "for-you/"],
             ex=("Resume skills for the ten most common job titles", rs_table))

    # ------------------------------------------------------------ 39. letter of recommendation
    tool("recommendation-letter", "seekers", "Letter of recommendation builder",
         "For a manager, a colleague, a teacher or a client: how you know the person, two strengths with an example each and a clear closing, in two tones.",
         "Letter of Recommendation Template & Generator",
         "Write a letter of recommendation for an employee, a student or a contractor: how you know them, two strengths with an example each and a clear closing. Free.",
         "Write a letter of recommendation that says something specific",
         "A useful recommendation says how you know the person, names two strengths and gives one example of each. "
         "Asked to write one, most people produce a page of praise (“hard-working, reliable, a pleasure to work with”) that could describe anyone and convinces nobody. "
         "Choose who you are to the person, add the two strengths and what happened, and pick a tone. The letter is ready to copy or print. It is a fill-in template, not AI: every claim in it is yours.",
         wrap("recommendation-letter",
              '<div class="tl-split"><div class="card tl-form"><div class="tl-grid">'
              + _sel("writer", "You are their", [("manager", "Manager", True), ("colleague", "Colleague"), ("teacher", "Teacher or professor"), ("client", "Client")])
              + _sel("who", "They are", [("employee", "An employee", True), ("student", "A student"), ("contractor", "A contractor")])
              + _sel("tone", "Tone", [("plain", "Plain", True), ("warm", "Warm")])
              + _sel("pronoun", "Pronoun", [("she", "She", True), ("he", "He"), ("they", "They")])
              + _f("cand", "Their full name", "Priya Shah", mode="")
              + _f("role_employee", "Their job title", "senior support agent", mode="", show=on("who:employee"))
              + _f("role_student", "Course or program", "the BSc Economics program", mode="", hint="Finish the sentence “She was a student in …”.", show=on("who:student"))
              + _f("role_contractor", "What they did for you", "web developer", mode="", hint="Finish the sentence “She worked with us as a …”.", show=on("who:contractor"))
              + _f("org", "Your organization", "Example Co", mode="", auto="organization")
              + _f("dur", "How long you have known their work", "three years", mode="", hint="Finish the sentence “… for …”.")
              + _f("purpose", "What the letter is for (optional)", "the Team Lead role at Acme", mode="", hint="Finish the sentence “I recommend her for …”.")
              + _f("to", "Addressed to (optional)", "Ms Rivera", mode="", hint="Left empty, the letter opens “To whom it may concern”.")
              + _area("s1", "First strength", 2, "how calm she stays with upset customers", hint="Finish the sentence “What stands out most is …”.")
              + _area("e1", "An example of it", 3, "When our payment system failed last March, she answered 140 tickets in a day and kept our satisfaction score above 90%.",
                      hint="One or two full sentences: what happened and what came of it.")
              + _area("s2", "Second strength (optional)", 2, "her clear writing", hint="Finish the sentence “A second strength is …”.")
              + _area("e2", "An example of it (optional)", 3, "She rewrote 60 help articles, and tickets about refunds fell by a third.")
              + _f("name", "Your name", "Dana Lee", mode="", auto="name")
              + _f("title", "Your job title (optional)", "Head of Support", mode="")
              + _f("contact", "Your email or phone (optional)", "dana.lee@example.com", mode="", auto="email")
              + _f("date", "Date of the letter", typ="date", mode="") + "</div>"
              + '<div class="tl-actions">' + _clear(True) + "</div>" + mail_note + "</div>"
              + paper("recommendation-letter.txt", '<button class="btn ghost" type="button" data-print>Print</button>') + "</div>"),
         "How the letter of recommendation is put together",
         "<p>The letter has five parts: the opening, which says whom you recommend and for what; how you know the person and for how long; the first strength with its example; "
         "the second strength with its example; and a closing that says how strongly you recommend them and how to reach you.</p>"
         "<p><strong>Who you are</strong> changes the second sentence and the closing: a manager writes “I managed her”, a teacher “I taught her”, a client “I was her client”, a colleague “we worked side by side”. "
         "<strong>Who they are</strong> changes how their role is described: an employee’s job title, a student’s course, a contractor’s work for you.</p>"
         "<p>“Plain” states the facts and suits applications to large employers and universities. “Warm” is more personal and ends with a line such as “I would hire Priya again”. "
         "An example you leave out stays in [brackets] as a reminder, because a strength with no example is only an adjective. The date is written out in full. "
         "Nothing is sent anywhere: copy the letter, or print it and sign it.</p>",
         [("What should a letter of recommendation include?",
           "Who you are and how you know the person, for how long, two or three strengths with a specific example of each, and a clear statement that you recommend them. One page is enough."),
          ("How long should a recommendation letter be?",
           "Three to five short paragraphs on one page, about 200 to 300 words. A reader with a pile of applications wants two concrete examples, not a full history."),
          ("Who should write a letter of recommendation?",
           "Someone who saw the person’s work closely: a manager for an employee, a teacher or supervisor for a student, a client for a contractor. A senior title helps less than real knowledge of the work."),
          ("I was asked to draft my own recommendation letter. Is that normal?",
           "It is common: busy managers and professors often ask for a draft. Write the facts and the examples as they happened, and let the person change the wording and sign it. They must agree with every sentence."),
          ("What is the difference between a recommendation letter and a reference?",
           "A recommendation letter is written in advance, usually for one application, and the candidate can send it. A reference is a person the employer contacts directly. The reference request email on this site asks someone to be one."),
          ("Should the letter mention weaknesses?",
           "Not unless the form asks for them. If it does, name something the person has already improved and say how. A letter that reads as honest carries more weight than one that is all praise."),
          no_ai("letter")],
         ["reference-request-email", "cover-letter", "resignation-letter"], ["resume/"],
         ex=("Letter of recommendation example from a manager", "<p>The form filled in with its sample details gives this letter, in the plain tone. The tool adds today’s date at the top.</p>" + sample(EXAMPLE["recommendation-letter"])))

    # ------------------------------------------------------------ 40. overtime pay
    tool("overtime-pay", "seekers", "Overtime pay calculator",
         "Hourly rate and hours in a week give regular pay, overtime pay at time and a half or double time, the total and your average per hour.",
         "Overtime Pay Calculator: Time and a Half",
         "Work out a week’s pay with overtime: hourly rate, hours worked, the overtime threshold and time and a half or double time. Regular pay, overtime pay and total.",
         "Work out your weekly pay with overtime",
         "Overtime pay is the hours above the threshold, multiplied by your hourly rate and by the overtime multiplier, usually 1.5. "
         "A long week is easy to underpay by mistake, and a payslip rarely shows the sum. "
         "Enter your hourly rate and the hours you worked. The calculator splits them at the threshold, 40 hours a week unless you change it, and shows regular pay, overtime pay, the total and what you earned per hour on average. "
         "Overtime rules differ by country and by state: this is arithmetic, not legal advice.",
         wrap("overtime-pay",
              '<div class="card tl-form"><div class="tl-grid">'
              + _f("rate", "Hourly rate", "20") + _cur()
              + _f("hours", "Hours worked in the week", "46")
              + _f("threshold", "Overtime starts after, hours", val="40", hint="40 a week in United States federal law. Use your own rule.")
              + _sel("mult", "Overtime is paid at", [("1.5", "Time and a half (1.5×)", True), ("2", "Double time (2×)")]) + "</div>"
              + '<div class="tl-actions">' + _clear() + "</div></div>"
              + _board("Your pay for the week", "Enter your hourly rate and the hours you worked in the week.")
              + '<p class="note tl-priv"><b>Not legal advice</b>Who must be paid overtime, from which hour and at what rate depends on the law where you work, on your contract and sometimes on a union agreement. '
                'The page multiplies the numbers you type and does not know those rules. Nothing you type leaves your browser.</p>'),
         "How overtime pay is calculated",
         "<ul><li><code>regular hours = hours worked, up to the threshold</code></li>"
         "<li><code>overtime hours = hours worked − threshold</code>, or zero when you worked no more than the threshold</li>"
         "<li><code>regular pay = regular hours × hourly rate</code></li>"
         "<li><code>overtime pay = overtime hours × hourly rate × multiplier</code></li>"
         "<li><code>total = regular pay + overtime pay</code></li>"
         "<li><code>average per hour = total ÷ hours worked</code></li></ul>"
         "<p>The threshold is 40 hours a week unless you change it, and the multiplier is 1.5 (“time and a half”) or 2 (“double time”). Hours exactly at the threshold are all regular hours. "
         "All figures are before tax and deductions.</p>"
         "<p><strong>What the page does not know.</strong> In the United States, federal law (the Fair Labor Standards Act) sets overtime at one and a half times the regular rate for hours over 40 in a workweek, "
         "for the employees it covers; many salaried jobs are exempt. Some states add their own rules: California, for example, also counts overtime by the day. "
         "Other countries use other thresholds, rates and averaging periods. A bonus or shift pay can also change the “regular rate” that overtime is based on. "
         "Check the rule that applies to you with your employer, your contract or your labor authority.</p>",
         [("How do I calculate overtime pay?",
           "Multiply the hours above the threshold by your hourly rate and by the overtime multiplier. At $20 an hour with 6 overtime hours at time and a half: 6 × $20 × 1.5 = $180, on top of $800 for the first 40 hours."),
          ("What is time and a half?",
           "One and a half times your normal hourly rate. If you earn $20 an hour, time and a half is $30 an hour and double time is $40."),
          ("How much is 46 hours at $20 an hour with overtime?",
           "$980 before tax, when overtime starts after 40 hours and is paid at time and a half: $800 for 40 regular hours plus $180 for 6 overtime hours. That is $21.30 for each hour worked."),
          ("After how many hours does overtime start?",
           "It depends on where you work. United States federal law uses 40 hours in a workweek for the employees it covers; some states also count by the day, and other countries set other limits. Change the threshold in the calculator to match your rule."),
          ("Do salaried employees get overtime?",
           "Some do. In the United States it depends on whether the job is “exempt” under the law, which turns on the duties and the pay and not on the word “salaried”. This page cannot tell you which you are: ask your employer or your labor authority."),
          ("What is my average hourly rate in a week with overtime?",
           "Your total for the week divided by the hours you worked. 46 hours for $980 is $21.30 an hour: more than the $20 base rate, because six of the hours were paid at $30."),
          ("Does the calculator include tax?",
           "No. It shows pay before tax and deductions. The take-home pay calculator on this site works out United States federal tax on a yearly salary.")],
         ["salary-converter", "take-home-pay", "contractor-rate"], ["salaries/"],
         ex=("Overtime pay example: $20 an hour, 46 hours in the week",
             '<div class="tablewrap"><table><tr><th>Part of the week</th><th>Sum</th><th>Pay</th></tr>'
             '<tr><td>Regular hours</td><td>40 × $20.00</td><td class="num">$800.00</td></tr>'
             '<tr><td>Overtime hours at time and a half</td><td>6 × $30.00</td><td class="num">$180.00</td></tr>'
             '<tr class="tl-total"><td>Total for the week</td><td>$800.00 + $180.00</td><td class="num">$980.00</td></tr>'
             '<tr><td>Average per hour worked</td><td>$980.00 ÷ 46</td><td class="num">$21.30</td></tr></table></div>'
             '<p class="note">Overtime starts after 40 hours, so 6 of the 46 hours are overtime, and time and a half of $20 is $30. At double time the same week pays 6 × $40.00 = $240.00 of overtime, $1,040.00 in total. '
             'A week of exactly 40 hours pays 40 × $20.00 = $800.00 and no overtime.</p>'))

    # ------------------------------------------------------------ write the pages
    by_slug = {t["slug"]: t for t in TOOLS}
    org = {"@type": "Organization", "name": SITE, "url": FULL + "/"}

    def crumbs_ld(parts):
        items = [{"@type": "ListItem", "position": 1, "name": "Home", "item": FULL + "/"}]
        items += [{"@type": "ListItem", "position": i + 2, "name": n, **({"item": f"{FULL}/{u}"} if u else {})} for i, (n, u) in enumerate(parts)]
        return _ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items})

    def faq_block(faq):
        html_ = '<div class="tl-faq">' + "".join(f"<div><h3>{e(q)}</h3><p>{e(a)}</p></div>" for q, a in faq) + "</div>"      # two columns on wide screens (DESIGN_STUDY 7)
        ld = _ld({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
        return html_, ld

    def cards(items):
        return '<div class="feats">' + "".join(f'<a class="feat" href="{P}/{u}"><h3>{e(n)}</h3><p>{e(d)}</p></a>' for u, n, d in items) + "</div>"


    # "In plain words" (owner's standard): two sentences, no jargon, for the tools whose subject is a technical or money term.
    PLAIN = {
        "boolean-search": "Recruiters find people by typing a search with the words AND, OR and NOT between the terms. This page writes that search for you, so you only list the job titles and skills.",
        "jobposting-schema": "Google shows jobs in a special box only when the page describes the job in a fixed code format that its robot can read. This page fills that code in from a short form, and you paste the result into your job page.",
        "equity-calculator": "Some companies pay part of your salary in options: the right to buy company shares at a fixed price later. This page turns the numbers in your offer letter into what the shares could be worth and what buying them would cost.",
        "contractor-rate": "A contractor is paid per day or per hour and covers their own holidays, sick days and gaps between jobs. This page works out the rate to ask for so that you end up with the same yearly income as an employee.",
        "job-description-keywords": "Many employers first read applications with a program that searches for the words in the posting. This page lists the words a posting uses most, so you can use the same ones in your resume where they are true.",
        "resume-match": "Many employers first read applications with a program that searches for the words in the posting. This page compares your resume with one posting and shows which of its words your resume does not use yet.",
        "time-zone-overlap": "A remote team can sit in different countries, and the clock is different in each. This page shows which hours of the working day fall inside the working hours of both places.",
        "interview-answer-builder": "STAR is a way to answer “tell me about a time when…”: say the situation, the task, what you did and the result, in that order. This page puts your four parts together and tells you how long the answer takes to say.",
        "interview-scorecard": "A scorecard is one list of what you are looking for, with a weight for each item, that every interviewer fills in for every candidate. This page builds that sheet and adds up the ratings into one score per candidate.",
        "cost-of-vacancy": "A vacancy is a job with nobody in it yet, and the work still has to be done by someone. This page puts a price on each day the job stays empty.",
        "cost-per-hire": "Cost per hire is everything spent on hiring in a period, divided by the number of people hired in that period. This page adds the invoices and the time of your own staff, so that the figure is the full one.",
        "job-description-checker": "A job description is the text of the posting that candidates read before they apply. This page reads yours for the things that make people skip a posting, such as a missing salary or too many requirements, and lists what to change.",
        "compare-offers": "An offer is more than the base salary: bonus, shares, days off and the commute change what you take home. This page puts two or three offers on one scale, so you can see which one is worth more per year.",
        "offer-check": "“Below the lower quarter” means lower than three of every four salaries posted for that work. This page places your offer among the salaries that open postings state, and says how many postings that is.",
        "salary-checker": "The median is the middle figure: half of the postings pay more and half pay less. This page shows the median and the usual range for a kind of work and a level, and where your salary sits among them.",
        "salary-converter": "Pay is quoted per hour, per day, per month or per year, and the figures cannot be compared until they are in one unit. This page converts one of them into all the others, using the hours you actually work.",
        "take-home-pay": "Your salary on the offer is the gross figure, before the government takes its share; take-home pay is what reaches your bank account. This page takes off the main US taxes (income tax, Social Security and Medicare) and shows what is left in each paycheck.",
        "job-search-calculator": "Looking for work is a numbers game: only some applications lead to an interview, and only some interviews lead to an offer. Enter your own two rates and this page shows how many applications one offer takes at that pace.",
        "401k-match": "A 401(k) is a retirement savings plan at work: part of each paycheck goes into it before you see the money. Many employers add money of their own, called a match, but only if you save too. This page shows how much that is.",
        "last-working-day": "The notice period is the time between telling your employer you are leaving and your final day. This page counts it on a calendar, so you can see the date instead of guessing at weekends.",
        "resume-review": "Skimming means looking at the top of the page, the first bullet points and the dates before reading anything closely. This page reads your text in that order and lists the lines a skimmer would pass over, with a fix for each.",
        "remote-work-savings": "Working from home saves the time and money you spend getting to an office, but that cost never shows on a payslip. Enter your own travel and office costs and this page adds them up for a year.",
        "raise-calculator": "A raise is a percent, an amount or a new salary, and people quote it in different ways. Give one of them and this page shows the other two, and what the raise is worth after prices have gone up.",
        "overtime-pay": "Overtime is the hours you work above a set number in a week, usually 40. Those hours are often paid at a higher rate, such as one and a half times your normal rate, and this page adds up the week for you.",
        "resume-skills": "A skill here means a tool, a programming language, a certificate or a spoken language that a job posting names. This page counts which of them today’s postings for one job title name most, so you know what to put first.",
        "elevator-pitch": "An elevator pitch is what you say when someone asks what you do and you have half a minute to answer. This page puts your answer in order and tells you how long it takes to say.",
        "referral-request": "A referral is when someone who works at a company passes your name to the people hiring there. This page writes the message that asks for one, in a way that is easy to say no to.",
    }
    for t in TOOLS:
        path = f"tools/{t['slug']}/"
        faq_html, faq_ld = faq_block(t["faq"])
        related = [(f"tools/{s}/", by_slug[s]["name"], by_slug[s]["card"]) for s in t["rel"] if s in by_slug] + [(u, SITE_PAGES[u][0], SITE_PAGES[u][1]) for u in t["site"]]
        app_ld = _ld({"@context": "https://schema.org", "@type": "WebApplication", "name": t["name"], "url": f"{FULL}/{path}", "description": t["desc"],
                      "applicationCategory": "BusinessApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript", "isAccessibleForFree": True, "inLanguage": "en",
                      "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": org})
        extra = section("Advertised salaries by category and level", sal_table) if t["slug"] == "salary-checker" else section(*t["ex"]) if t["ex"] else ""
        sub = (f'<nav class="tsub" aria-label="{"Tools for people hiring" if t["group"] == "employers" else "Tools for job seekers"}"><a class="all" href="{P}/tools/">All tools</a>'
               + "".join(f'<a href="{P}/tools/{o["slug"]}/"' + (' aria-current="page"' if o is t else "") + f'>{e(o["name"])}</a>' for o in TOOLS if o["group"] == t["group"]) + "</nav>")
        body = (crumbs(("Tools", "tools/"), (t["name"], "")) + sub + f'<h1>{e(t["h1"])}</h1><p class="lead">{e(t["lead"])}</p>' + (f'<p class="plain"><b>In plain words:</b> {e(PLAIN[t["slug"]])}</p>' if t["slug"] in PLAIN else "") + t["html"]
                + '<div class="tl-after">' + extra
                + section(t["how_title"], f'<div class="tl-how">{t["how"]}</div>')
                + section(f"Questions about the {t['name'][0].lower() + t['name'][1:]}", faq_html)
                + section("Related tools", cards(related), ("tools/", "All free tools")) + "</div>")
        page(path, t["title"], t["desc"], body, head=assets + app_ld + faq_ld + crumbs_ld([("Tools", "tools/"), (t["name"], "")]))

    # ------------------------------------------------------------ one paycheck calculator per state ("paycheck calculator texas")
    pc_ = lambda r: f"{r * 100:.3f}".rstrip("0").rstrip(".") + "%"
    th = by_slug["take-home-pay"]
    th_rel = [(f"tools/{s_}/", by_slug[s_]["name"], by_slug[s_]["card"]) for s_ in ("salary-converter", "overtime-pay", "raise-calculator") if s_ in by_slug]
    for code, x in ST.items():
        name, f_ = x["name"], x["single"]
        rates = [r for _, r in f_["b"] if r > 0]
        has_tax = bool(rates)
        says = ("no state income tax on wages" if not has_tax else f"a flat income tax of {pc_(rates[0])}" if len(set(rates)) == 1 else f"income tax rates from {pc_(min(rates))} to {pc_(max(rates))}")
        pays = ", ".join(p[0] for p in x["pay"])
        path = f"tools/take-home-pay/{x['slug']}/"
        a75, a100 = st_after(code, 75000), st_after(code, 100000)
        line = lambda sal, a: (f"A single filer earning ${sal:,} in {name} keeps about ${a[3]:,.0f} a year, or ${a[3] / 26:,.0f} every two weeks, after ${a[0]:,.0f} of federal income tax and ${a[1]:,.0f} of Social Security and Medicare"
                               + (f", ${a[2]['tax']:,.0f} of {name} income tax" if has_tax else "") + (f" and ${a[2]['pay_total']:,.0f} of state payroll deductions" if a[2]["pay"] else "") + ".")
        qa = [(f"How much is $75,000 a year after taxes in {name}?", line(75000, a75)), (f"How much is $100,000 a year after taxes in {name}?", line(100000, a100)),
              (f"Does {name} have a state income tax?", f"{name} has {says}." + (f" The standard deduction is ${f_['d']:,} for a single filer." if f_["d"] else "") + (f" {x['note']}" if x["note"] else "")),
              (f"What comes out of a paycheck in {name}?", "Federal income tax, Social Security and Medicare" + (f", {name} income tax" if has_tax else "") + (f", and {pays}" if pays else "") + "." + (f" {x['local']}" if x["local"] else ""))]
        faq_html, faq_ld = faq_block(qa)
        rows = "".join((lambda a: f"<tr><td><strong>${s_:,}</strong></td><td>${a[0]:,.0f}</td><td>${a[1]:,.0f}</td><td>${a[2]['tax']:,.0f}</td><td>${a[2]['pay_total']:,.0f}</td><td><strong>${a[3]:,.0f}</strong></td><td>${a[3] / 12:,.0f}</td><td>${a[3] / 26:,.0f}</td></tr>")(st_after(code, s_))
                       for s_ in (40000, 50000, 60000, 75000, 90000, 100000, 125000, 150000, 200000))
        band = lambda b: "".join(f"<tr><td>{'Over $' + format(b[i - 1][0], ',') if hi is None else ('Up to $' + format(hi, ',') if i == 0 else '$' + format(b[i - 1][0], ',') + ' to $' + format(hi, ','))}</td><td>{pc_(r)}</td></tr>" if len(b) > 1 else f"<tr><td>All taxable income</td><td>{pc_(r)}</td></tr>" for i, (hi, r) in enumerate(b))
        facts = [("Starts from", "Federal taxable income" if x["base"] == "fed" else "Wages")] if has_tax else []
        for k_, lab in (("d", "Standard deduction"), ("e", "Personal exemption"), ("c", "Credit against the tax")):
            if f_[k_] or x["joint"][k_]: facts.append((lab, f"${f_[k_]:,} single, ${x['joint'][k_]:,} joint"))
        facts += [(p[0], pc_(p[1]) + (f" of wages up to ${p[2]:,}" if p[2] else " of wages") + (f", at most ${p[3]:,} a year" if p[3] else "")) for p in x["pay"]]
        if x.get("local_rate"): facts.append((x["local_rate"][1].split(" (")[0], f"{pc_(x['local_rate'][0])} of {name} taxable income, included in the figures here"))
        if x["local"]: facts.append(("City and county taxes", x["local"] + " Not included here."))
        if x["note"]: facts.append(("Good to know", x["note"]))
        how = (('<div class="st-tabs">' + "".join(f'<div><p class="tl-t">{lab} taxable income</p><div class="tablewrap"><table><tr><th>Taxable income</th><th>Rate</th></tr>{band(x[k_]["b"])}</table></div></div>' for k_, lab in (("single", "Single:"), ("joint", "Married filing jointly:"))) + "</div>") if has_tax else f"<p>{_e(name)} does not tax wages.</p>")
        how += ('<div class="tablewrap"><table class="kv">' + "".join(f"<tr><th>{_e(k_)}</th><td>{_e(v_)}</td></tr>" for k_, v_ in facts) + "</table></div>" if facts else "")
        how += ("<p>The state’s own site could not be opened for this check, so these figures come from excerpts of its official documents and from the Tax Foundation’s table of state tax rates. Compare them with the state’s pages before relying on them.</p>" if x.get("secondary") else "")
        how += f'<p class="note">Tax year {x["year"]}, read {state_tax.READ}. Sources: ' + " · ".join(f'<a href="{_e(u_)}" rel="noopener">{_e(l_)}</a>' for l_, u_ in x["src"]) + ". An estimate, not tax advice.</p>"
        others = '<p class="rel">' + "".join(f'<a href="{P}/tools/take-home-pay/{o["slug"]}/">{_e(o["name"])}</a>' for c_, o in ST.items() if c_ != code) + "</p>"
        lead = (f"{name} has {says}. Enter your salary to see your paycheck after federal income tax, Social Security and Medicare" + (f", {name} income tax" if has_tax else "") + (f" and {pays}" if pays else "")
                + f". On $75,000 a single filer keeps about ${a75[3]:,.0f} a year.")
        title = next(t_ for t_ in (f"{name} Paycheck Calculator 2026: Take-Home Pay After Tax", f"{name} Paycheck Calculator 2026: Take-Home Pay", f"{name} Paycheck Calculator 2026") if len(t_) <= 60 or t_.endswith("2026"))
        body = (crumbs(("Tools", "tools/"), (th["name"], "tools/take-home-pay/"), (name, "")) + f'<h1>{_e(name)} paycheck calculator: take-home pay after tax</h1><p class="lead">{_e(lead)}</p>' + th_form(code)
                + '<div class="tl-after">' + section(f"Take-home pay in {name}: $40,000 to $200,000", '<p>A single filer in 2026 with no pre-tax contributions.</p><div class="tablewrap"><table class="rkt"><tr><th>Salary</th><th>Federal income tax</th><th>Social Security and Medicare</th><th>State income tax</th><th>State payroll</th><th>Take-home a year</th><th>A month</th><th>Every two weeks</th></tr>' + rows + "</table></div>")
                + section(f"How {name} taxes wages", f'<div class="tl-how">{how}</div>')
                + section(f"Questions about paychecks in {name}", faq_html)
                + section("Paycheck calculators for other states", others, ("tools/take-home-pay/", "All states"))
                + section("Related tools", cards(th_rel), ("tools/", "All free tools")) + "</div>")
        page(path, title + brand, f"{name} paycheck calculator for 2026: take-home pay after federal tax, Social Security, Medicare" + (f" and {name} income tax" if has_tax else "") + f". {name} has {says}. Free, no sign-up.",
             body, head=assets + faq_ld + crumbs_ld([("Tools", "tools/"), (th["name"], "tools/take-home-pay/"), (name, "")]))

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
        "cost-of-vacancy": ex + '<span class="big">$577<small>per working day</small></span><span class="ln">45 days open: <b>$18,500</b></span>',
        "job-offer-response": ex + '<span class="ln"><b>Subject:</b> Offer acceptance: Product Designer</span><span class="sk" style="width:90%"></span><span class="ln">“I am delighted to accept.”</span>',
        "candidate-rejection-email": ex + '<span class="ln"><b>Subject:</b> Your application for Account Executive</span><span class="sk" style="width:88%"></span><span class="sk" style="width:60%"></span>',
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
        "401k-match": ex + '<span class="ln">$80,000 salary · 4% saved · 50% match up to 6%</span><span class="big">$1,600<small>from your employer a year</small></span>'
                                '<span class="ln"><b>$800</b> a year left unclaimed below 6%</span>',
        "last-working-day": ex + f'<span class="ln">Notice given Monday, {dshort(monday)} · 2 weeks</span><span class="big">{dshort(leave)}<small>last working day</small></span>'
                                 '<span class="ln"><b>10 working days</b> left · weekends skipped</span>',
        "cost-per-hire": ex + '<span class="big">$6,100<small>per hire</small></span><span class="rw"><span>Agency</span><span class="mt"><i style="width:49%"></i></span><b>49%</b></span>'
                              '<span class="rw"><span>Staff time</span><span class="mt"><i style="width:32%"></i></span><b>32%</b></span>',
        "interview-scorecard": ex + '<span class="ln">Five criteria, weights add up to 100</span><span class="big">4.05<small>out of 5, weighted</small></span>'
                                    '<span class="ln">Candidate A <b>4.05</b> · B <b>4.00</b> · C <b>3.95</b></span>',
    })
    # the tools added on 17 Nov 2026: the figures are those of the worked example on each page (EXAMPLE), counted here so the two cannot drift apart
    note_n, about_n, pitch_n = len(EXAMPLE["linkedin-connection-message"]), len(EXAMPLE["linkedin-summary"]), EXAMPLE["elevator-pitch-n"].split(" words")[0]
    PREV.update({
        "follow-up-email": ex + '<span class="ln"><b>Subject:</b> Following up on my application</span><span class="sk" style="width:92%"></span>'
                                '<span class="ln">“Could you tell me <b>when you expect to choose</b> people to interview?”</span><span class="sk" style="width:38%"></span>',
        "application-email": ex + '<span class="ln"><b>Subject:</b> Application for Marketing Manager</span><span class="sk" style="width:90%"></span><span class="sk h" style="width:64%"></span>'
                                  '<span class="ln">Attached: <b>Alex-Morgan-Resume.pdf</b></span>',
        "referral-request": ex + '<span class="ln"><b>Hi Sam,</b> Acme is hiring a Data Analyst…</span><span class="sk" style="width:88%"></span>'
                                 '<span class="ln">“<b>Would you be willing to refer me?</b>”</span><span class="sk" style="width:52%"></span>',
        "linkedin-connection-message": ex + f'<span class="big">{note_n}<small>of 300 characters</small></span><span class="mt"><i style="width:{round(100 * note_n / 300)}%"></i></span>'
                                            '<span class="ln">“Hi Dana, I am a <b>product designer</b> with six years in fintech…”</span>',
        "professional-bio": ex + '<span class="ln"><b>Alex Morgan</b> is a senior backend engineer at Acme…</span><span class="sk" style="width:94%"></span><span class="sk" style="width:70%"></span>'
                                 '<span class="ln">One line · <b>50 words</b> · <b>100 words</b></span>',
        "linkedin-summary": ex + f'<span class="big">{about_n:,}<small>of 2,600 characters</small></span><span class="mt"><i style="width:{round(100 * about_n / 2600)}%"></i></span>'
                                 '<span class="ln">Role · strengths · <b>three results</b> · what you want next</span>',
        "elevator-pitch": ex + '<span class="big">30 s<small>said aloud</small></span><span class="mt"><i style="left:41.7%;width:16.7%"></i><u style="left:50%"></u></span>'
                               f'<span class="ln"><b>{pitch_n} words</b> at 150 words a minute</span>',
        "resume-summary": ex + '<span class="ln"><b>Data analyst</b> with 4 years of experience in SQL, Excel and Tableau.</span><span class="sk" style="width:90%"></span>'
                               '<span class="ln">Cut month-end close <b>from 8 days to 5</b></span>',
        "recommendation-letter": ex + '<span class="ln"><b>To whom it may concern,</b></span><span class="sk" style="width:95%"></span>'
                                      '<span class="ln">“What stands out most is <b>how calm she stays</b>…”</span><span class="sk" style="width:60%"></span>',
        "overtime-pay": ex + '<span class="ln">$20 an hour · 46 hours in the week</span><span class="big">$980<small>for the week</small></span>'
                             '<span class="ln"><b>$800</b> regular + <b>$180</b> overtime at time and a half</span>',
    })
    if "resume-skills" in by_slug:                              # today's real figures for the job title with the most postings
        PREV["resume-skills"] = (f'<span class="ln">{e(top_nm)} · {top_n:,} postings today</span>'
                                 + "".join(f'<span class="rw"><span>{e(t)}</span><span class="mt"><i style="width:{round(100 * k / top_sk[0][1])}%"></i></span><b>{pct(k, top_n)}</b></span>' for t, k in top_sk[:3]))
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
        "job-offer-response": "Accept, decline or ask for more time",
        "cost-of-vacancy": "$577 per working day, $18,500 in 45 days",
        "candidate-rejection-email": "A clear, kind no, with one line of feedback",
        "follow-up-email": "A week after applying: four short sentences",
        "application-email": "Subject: Application for Marketing Manager",
        "referral-request": "“Would you be willing to refer me?”",
        "linkedin-connection-message": f"{note_n} of 300 characters",
        "professional-bio": "One line, 50 words and 100 words",
        "linkedin-summary": f"{about_n:,} of 2,600 characters",
        "elevator-pitch": f"{pitch_n} words, about 30 seconds",
        "resume-summary": "Two wordings of two lines each",
        "recommendation-letter": "Two strengths, an example of each",
        "overtime-pay": "46 hours at $20 = $980 for the week",
    }
    if "resume-skills" in by_slug:
        RES["resume-skills"] = f"{top_nm}: {top_sk[0][0]} in {pct(top_sk[0][1], top_n)} of postings"
    if len(mids) >= MIN_SAMPLE:
        RES["salary-checker"] = f"Median today {kmoney(q(.5))} across {len(mids):,} roles"

    def wide(path, name, text, slug):
        prev = PREV.get(slug, "")
        return (f'<a class="twide" data-n="{e((name + " " + text).lower())}" href="{P}/{path}"><span class="tprev" aria-hidden="true">{prev}</span>'
                f'<span class="tbody"><b>{e(name)}</b><span>{e(text)}</span><i><u>Open the tool</u></i></span></a>')

    def trow(path, name, text, slug):
        return (f'<li><a href="{P}/{path}"><b><u>{e(name)}</u></b><span class="d">{e(text)}</span>'
                f'<span class="r"><small>Example</small>{e(RES.get(slug, ""))}</span></a></li>')

    # sections review, batch 4 (17 Nov 2026): the hub is 47 tools long, so it gets the hub's parts: a row of its own figures, a box
    # that keeps the tools with the typed words in their name or text, a row of pills to jump to a group, a label above each group
    found = lambda s_: TILES[f"tools/{s_}/"].replace('<a class="tcard" ', f'<a class="tcard" data-n="{e((by_slug[s_]["name"] + " " + by_slug[s_]["card"]).lower())}" ', 1)
    part = lambda title, inner, sid, k: section(f"[[{title}]]", inner, sid=sid, label=f"{k} tool{'s' if k != 1 else ''}").replace("<section ", "<section data-dirg ", 1)

    def group(key):
        return '<div class="tgrid">' + "".join(found(t["slug"]) for t in TOOLS if t["group"] == key) + "</div>"
    # job-seeker tools stand in the order of a search: the resume, applying, the offer, leaving. A tool that is not named here still appears, in a last group.
    HUB = [("Resume and LinkedIn profile", "resume", ["resume-review", "resume-match", "resume-skills", "job-description-keywords", "resume-summary", "resume-bullet-builder", "linkedin-headline", "linkedin-summary", "linkedin-review"]),
           ("Applying and interviews", "applying", ["cover-letter", "application-email", "follow-up-email", "job-search-calculator", "interview-answer-builder", "thank-you-email", "reference-request-email", "recommendation-letter"]),
           ("Networking and introductions", "networking", ["referral-request", "linkedin-connection-message", "elevator-pitch", "professional-bio"]),
           ("Pay and offers", "pay", ["salary-checker", "offer-check", "compare-offers", "negotiation-email", "job-offer-response", "raise-calculator", "raise-request-email", "salary-converter", "overtime-pay", "equity-calculator", "401k-match", "contractor-rate"]),
           ("Remote work and leaving a job", "remote-leaving", ["remote-work-savings", "time-zone-overlap", "resignation-letter", "last-working-day"])]
    named = {s_ for _, _, ss in HUB for s_ in ss}
    rest = [t["slug"] for t in TOOLS if t["group"] == "seekers" and t["slug"] not in named]
    grid = lambda slugs: '<div class="tgrid">' + "".join(found(s_) for s_ in slugs if s_ in by_slug) + "</div>"
    have = lambda slugs: sum(1 for s_ in slugs if s_ in by_slug)
    seekers = "".join(part(h_, grid(ss), sid_, have(ss)) for h_, sid_, ss in HUB if have(ss)) + (part("More for job seekers", grid(rest), "more", len(rest)) if rest else "")
    jump = [("Start here", "start")] + [(h_, sid_) for h_, sid_, ss in HUB if have(ss)] + ([("More for job seekers", "more")] if rest else []) + [("For employers and recruiters", "employers")]
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
    page("tools/", "Free Tools for Job Seekers & Recruiters" + brand, hub_desc,
         crumbs(("Tools", "")) + "<h1>Free tools for a job search and for hiring</h1>"
         f'<p class="lead">{len(TOOLS) + len(EXTRA)} tools, from a resume builder to pay calculators, for things that come up along the way: whether your pay is fair, how well a resume fits a posting, which of two offers is worth more, why a vacancy gets no replies. '
         f"They run in your browser with no account, and the salary figures come from the {n_paid:,} open postings here that publish a pay range.</p>"
         + '<dl class="nums">' + "".join(f"<div><dt>{b_}</dt><dd>{a_}</dd></div>" for a_, b_ in (
             ("Free", "every tool, as often as you like"), (f"{n_seek + len(EXTRA)}", "tools for a job search"), (f"{n_emp}", "tools for employers and recruiters"),
             ("No account", "and nothing you type is uploaded"))) + "</dl>"
         + '<p class="dirfind"><input type="search" id="dirfilter" placeholder="Type what you need, for example salary, cover letter or LinkedIn" aria-label="Find a tool"></p>'
         f'<p class="lead" id="dirnone" hidden>No tool with these words. The <a href="{P}/help/">help page</a> answers questions about this site.</p>'
         + '<div class="pillrow" role="navigation" aria-label="Groups of tools">' + "".join(f'<a href="#{sid_}">{e(h_)}</a>' for h_, sid_ in jump) + "</div>"
         + section("Start here: [[resume, matching, tracking]]", '<div class="twides">' + "".join(wide(*TILE_TEXT[u]) for u in EXTRA) + "</div>", sid="start",
                   label="The three most used").replace("<section ", "<section data-dirg ", 1)
         + seekers
         + part("For employers and recruiters", group("employers"), "employers", n_emp)
         + section("Templates and examples to copy", '<div class="feats">'
                   f'<a class="feat" href="{P}/resume/examples/"><h3>Resume examples</h3><p>A written example for each kind of work, with the skills today’s postings name.</p></a>'
                   f'<a class="feat" href="{P}/cover-letter-examples/"><h3>Cover letter examples</h3><p>A letter for each kind of work that leads with results, ready to copy.</p></a>'
                   f'<a class="feat" href="{P}/resignation-letters/"><h3>Resignation letters</h3><p>Two weeks notice, effective immediately, by email and 15 more situations.</p></a>'
                   f'<a class="feat" href="{P}/resume-words/"><h3>Stronger resume words</h3><p>What to write instead of “managed”, “helped” or “responsible for”.</p></a>'
                   f'<a class="feat" href="{P}/how-to-become/"><h3>How to become…</h3><p>Skills, pay and jobs open to beginners, for people changing careers.</p></a>'
                   f'<a class="feat" href="{P}/interview-questions/"><h3>Interview questions</h3><p>The questions to prepare for each kind of work, and what a good answer shows.</p></a>'
                   f'<a class="feat" href="{P}/job-descriptions/"><h3>Job description templates</h3><p>For employers: a template per role with what today’s postings ask and pay.</p></a>'
                   f'<a class="feat" href="{P}/how-to-hire/"><h3>How to hire…</h3><p>For employers: who else is hiring each role, what they pay, and six steps.</p></a>'
                   f'<a class="feat" href="{P}/map/"><h3>Jobs map</h3><p>Every city with open jobs on one map. Search a skill and see where it is hiring.</p></a>'
                   f'<a class="feat" href="{P}/vs/"><h3>Compared with other job sites</h3><p>Fair, sourced comparisons with Indeed, LinkedIn and others.</p></a></div>')
         + section("How these tools work", '<div class="feats">'
                   '<div class="feat"><h3>Nothing leaves your browser</h3><p>Every calculation and text check runs on your device. Nothing is uploaded, and “Clear” erases what a tool remembers.</p></div>'
                   f'<div class="feat"><h3>The salary figures have a source</h3><p>They come from {n_paid:,} open roles that publish a yearly US-dollar range. No figure is shown for fewer than {MIN_SAMPLE} postings.</p></div>'
                   '<div class="feat"><h3>The method is on the page</h3><p>Arithmetic and fill-in templates, not AI. Under each tool you can read how its result is calculated.</p></div></div>')
         + section("Questions about the tools", faq_html)
         + section("More on this site", cards([(u, SITE_PAGES[u][0], SITE_PAGES[u][1]) for u in ("jobs/", "salaries/", "resume/", "for-you/", "post-a-job/", "widgets/")])),
         head=assets + list_ld + faq_ld + crumbs_ld([("Tools", "")]), cls="hub tlhub")

    return [(f"tools/{t['slug']}/", t["name"], t["card"]) for t in TOOLS]
