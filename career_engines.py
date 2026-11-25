"""Facts for /job-search-engines/: job search engines that read jobs from company career pages, each from its own pages.

Why the page exists (search and AI answer check, 18 Nov 2026): for "a job search engine that reads company career pages and removes
closed jobs" Google's AI answer names HiringCafe and LinkUp, ChatGPT names LinkUp and data services, Perplexity names HiringCafe and
half a dozen small sites and takes its table from an article on another site. This site does exactly that and was in none of them.

Rules the data follows:
- Every cell is something the site's own page said on the day in its "read", opened in a browser by us that day. Words in curly quotes are the
  site's own words, copied; the rest is a plain description of what the page shows. Nothing comes from an article about the site.
- A cell the pages we read do not answer is "" and the page shows "Not stated".
- kind: "site" (a job search site for people) or "tool" (a paid tool for developers; it is in the table because answers name it).
- A site that is named in such answers and could not be read that day is in NOT_READ, with the reason, and is not judged.

Run `python3 career_engines.py` to check the data.
"""
READ = "2026-11-25"          # the latest reading; each row has its own date ("read")

COLS = ("reads", "jobs", "refresh", "closed", "price", "apply")
COL_NAMES = {"reads": "What it reads", "jobs": "Open jobs it states", "refresh": "How often", "closed": "A closed job", "price": "Price for a job seeker", "apply": "Where “Apply” leads"}

# 25 Nov 2026: HiringCafe and Drivetube read again (Drivetube now states 160,000+ career pages, was 140,000+, and "Only roles posted in
# the last 3 days"); Jobright, Jobscan's AI Job Match and Google for Jobs added (all three named in AI answers for this question; Jobright's
# and Jobscan's pages now say where their jobs come from). "vs": the address of the site's comparison page here (/vs/<vs>/).
ENGINES = [
    {"name": "HiringCafe", "url": "https://hiringcafe.com/", "kind": "site", "read": "2026-11-25", "vs": "hiringcafe",
     "reads": "“We collect jobs directly from company websites in real time and filter out external recruiting agencies and fake consulting firms.”",
     "jobs": "“over 5 million open jobs”",
     "refresh": "“in real time”",
     "closed": "It says it keeps improving systems that “detect stale postings, duplicate roles”; no rule for a closed job is stated",
     "price": "Free: “Our product is free.”",
     "apply": "“Apply directly on employer's site”",
     "also": "Filters for pay, benefits, security clearance, shifts, company stage and size; a Talent Agent that looks for jobs for you every day; a tracker.",
     "sources": [("https://hiringcafe.com/", "home page"), ("https://hiringcafe.com/about", "about page and its questions"),
                 ("https://hiringcafe.com/job/account-manager-hanoi-booking-com-hanoi-hanoi-ub93wlrsabpkd46d", "a job page")]},
    {"name": "Drivetube", "url": "https://drivetube.ai/", "kind": "site", "read": "2026-11-25", "vs": "drivetube",
     "reads": "“aggregated ATS-by-ATS directly from 160,000+ real company career pages across 50+ ATS platforms”",
     "jobs": "",
     "refresh": "“Only roles posted in the last 3 days”",
     "closed": "A job older than 3 days is not shown, filled or not",
     "price": "The job board is free, “no account required”; a paid community from $39.99 for 3 months, resume writing from $25.99",
     "apply": "“Every listing links to the company's real application page”",
     "also": "A free resume profile employers can find, visa-sponsorship filters for members, resume writing and a managed application program for a fee.",
     "sources": [("https://drivetube.ai/docs/overview", "overview page")]},
    {"name": "Jobright", "url": "https://jobright.ai/", "kind": "site", "read": "2026-11-25", "vs": "jobright",
     "reads": "Listings “aggregated from LinkedIn, Indeed, company career pages, and more”; for remote jobs, “major job boards and 200K+ company career sites”",
     "jobs": "“Total Jobs 8,000,000+”",
     "refresh": "“Updated hourly” (its remote jobs page); “~400,000 fresh listings added every day”",
     "closed": "",
     "price": "A free basic service; Premium “$30/month” by its own blog in June 2025; you sign up to apply",
     "apply": "“Apply on Employer Site” or “Apply With Autofill”; Apply Now asked us to sign up",
     "also": "AI resume tailoring, autofill of applications, insider connections and an H-1B filter; US jobs only.",
     "sources": [("https://jobright.ai/", "home page"), ("https://jobright.ai/blog/is-jobright-legit/", "its own post on how it works"),
                 ("https://jobright.ai/remote-jobs", "remote jobs page"), ("https://jobright.ai/jobs/info/6b06f4902662686ad8e05974", "a job page")]},
    {"name": "Jobscan (AI Job Match)", "url": "https://www.jobscan.co/job-search", "kind": "site", "read": "2026-11-25", "vs": "jobscan",
     "reads": "Jobs “from Greenhouse, Lever, Workable, and 20+ ATS platforms”, ranked by how well they fit your resume",
     "jobs": "",
     "refresh": "",
     "closed": "",
     "price": "Free to start with a sign-up; “Premium unlocks every Top Match job” ($49.95 a month)",
     "apply": "“apply on the company's site”, or Auto Apply after you approve each application",
     "also": "A resume scanner with a match rate for each job, a job tracker and a Chrome extension.",
     "sources": [("https://www.jobscan.co/job-search", "AI Job Match page"), ("https://www.jobscan.co/auto-apply", "Auto Apply page"), ("https://app.jobscan.co/plan", "plans")]},
    {"name": "Google for Jobs", "url": "https://support.google.com/websearch/answer/7498276?hl=en", "kind": "site", "read": "2026-11-25", "vs": "google-for-jobs",
     "reads": "Pages of employers and job sites that carry job posting markup: “Jobs come directly from employers and career sites across the web”",
     "jobs": "",
     "refresh": "When Google crawls a page; it says a new page “may take several days” to be found and crawled",
     "closed": "Left to each site: a closed job “must be expired”, with a past end date or a removal request",
     "price": "Free; listing providers “don't pay Google to appear”",
     "apply": "The site you pick under “Apply”: the employer’s or a job site that carries the job",
     "also": "Part of Google Search: saved jobs and alerts with a Google Account; not available in every country or language.",
     "sources": [("https://support.google.com/websearch/answer/7498276?hl=en", "Google’s help page on job search"),
                 ("https://developers.google.com/search/docs/appearance/structured-data/job-posting", "Google’s rules for job postings")]},
    {"name": "JobDork", "url": "https://jobdork.org/", "kind": "site", "read": "2026-11-25",
     "reads": "“Search Authentic Career Boards, Directly”: the boards of Ashby, Greenhouse and Lever",
     "jobs": "",
     "refresh": "Filters by posting age: 24 hours, 3 days, 7 days or 30 days",
     "closed": "A filter to “Exclude Noise, Closed & Expired Roles”",
     "price": "Free; it calls itself “Open-source”",
     "apply": "",
     "also": "“100% client-side”, with saved search bookmarks; named by ChatGPT for this question on 25 Nov 2026.",
     "sources": [("https://jobdork.org/", "home page")]},
    # Google (gl=us) for "job search engine that pulls jobs directly from company career pages", 25 Nov 2026: SecretJobs, Runway and
    # Career Hound in the first results; each read on its own home page that day.
    {"name": "SecretJobs", "url": "https://www.secretjobs.ai/", "kind": "site", "read": "2026-11-25",
     "reads": "“Sourced straight from the career pages of 400,000+ companies”",
     "jobs": "“8M+ open jobs”",
     "refresh": "“Updated every hour”",
     "closed": "“Ghost jobs filtered out”; how a closed job is handled is not stated",
     "price": "“Free to search · no card needed”",
     "apply": "Its example shows the company’s own application page, filled in for you in one click",
     "also": "Fills in and sends applications for you, screening questions included.",
     "sources": [("https://www.secretjobs.ai/", "home page")]},
    {"name": "Runway", "url": "https://www.joinrunway.io/", "kind": "site", "read": "2026-11-25",
     "reads": "“Runway pulls jobs directly from 200,000+ company career sites” (175,000+ elsewhere on the same page)",
     "jobs": "",
     "refresh": "“the second they're posted”; its own chart says “1 hour”",
     "closed": "",
     "price": "Free to search; $3 a month for match scores, $13 a month with resume tailoring, billed quarterly or yearly",
     "apply": "",
     "also": "For college students and recent graduates: internships and entry-level jobs.",
     "sources": [("https://www.joinrunway.io/", "home page")]},
    {"name": "Career Hound", "url": "https://www.careerhound.io/", "kind": "site", "read": "2026-11-25",
     "reads": "“We find jobs posted on company websites”",
     "jobs": "“4.8 million hidden jobs”",
     "refresh": "",
     "closed": "",
     "price": "A “Free preview”; the paid price is not stated on its home page",
     "apply": "“Apply directly to the hiring team”",
     "also": "“We find jobs from every company we can find.”",
     "sources": [("https://www.careerhound.io/", "home page")]},
    {"name": "Spool Job Search", "url": "https://apify.com/spool/job-search", "kind": "tool", "read": "2026-11-18",
     "reads": "A tool for developers on Apify: “Live Jobs Direct from Company Career Pages”",
     "jobs": "“about 353,000 open roles on any given day”",
     "refresh": "Reads the career pages when you run it",
     "closed": "“A posting that is gone from the career page cannot appear in your results.”",
     "price": "“$3.00 per 1,000 postings”, with an Apify account",
     "apply": "",
     "also": "Filters by category, place, pay, visa sponsorship and technology; results as a file or through an API.",
     "sources": [("https://apify.com/spool/job-search", "its page on Apify")]},
]

# named in the same answers, not in the table
NOT_READ = [
    ("LinkUp", "its site asked our browser to prove it was a person on 18 and 25 Nov 2026, and we do not go past such checks"),
    ("Hidden Roles", "its home page showed only a headline to our reader on 18 and 25 Nov 2026"),
    ("JobYap and CrawlJobs", "their pages did not open on 18 Nov 2026"),
]


def check():
    for x in ENGINES:
        assert x["kind"] in ("site", "tool") and x["url"].startswith("https://") and x["sources"], x["name"]
        for k in COLS + ("also",): assert isinstance(x[k], str) and len(x[k]) < 190, (x["name"], k)
        assert x["reads"], x["name"]
        assert x["read"] in ("2026-11-18", "2026-11-25"), x["name"]
        for u, w in x["sources"]: assert u.startswith("https://") and w, x["name"]
    assert len({x["name"] for x in ENGINES}) == len(ENGINES)
    return len(ENGINES)


if __name__ == "__main__":
    print(f"{check()} job search engines, last read {READ}; {sum(1 for x in ENGINES for k in COLS if not x[k])} cells not stated; {len(NOT_READ)} named and not read")
