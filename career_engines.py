"""Facts for /job-search-engines/: job search engines that read jobs from company career pages, each from its own pages.

Why the page exists (search and AI answer check, 18 Nov 2026): for "a job search engine that reads company career pages and removes
closed jobs" Google's AI answer names HiringCafe and LinkUp, ChatGPT names LinkUp and data services, Perplexity names HiringCafe and
half a dozen small sites and takes its table from an article on another site. This site does exactly that and was in none of them.

Rules the data follows:
- Every cell is something the site's own page said on READ, opened in a browser by us that day. Words in curly quotes are the
  site's own words, copied; the rest is a plain description of what the page shows. Nothing comes from an article about the site.
- A cell the pages we read do not answer is "" and the page shows "Not stated".
- kind: "site" (a job search site for people) or "tool" (a paid tool for developers; it is in the table because answers name it).
- A site that is named in such answers and could not be read that day is in NOT_READ, with the reason, and is not judged.

Run `python3 career_engines.py` to check the data.
"""
READ = "2026-11-18"

COLS = ("reads", "jobs", "refresh", "closed", "price", "apply")
COL_NAMES = {"reads": "What it reads", "jobs": "Open jobs it states", "refresh": "How often", "closed": "A closed job", "price": "Price for a job seeker", "apply": "Where “Apply” leads"}

ENGINES = [
    {"name": "HiringCafe", "url": "https://hiringcafe.com/", "kind": "site",
     "reads": "“We collect jobs directly from company websites in real time and filter out external recruiting agencies and fake consulting firms.”",
     "jobs": "“over 5 million open jobs”",
     "refresh": "“in real time”",
     "closed": "",
     "price": "“free AI tools”; the pages name no price",
     "apply": "",
     "also": "A long row of filters (pay, benefits, security clearance, shifts, company stage and size) and “Talent Agent”, which looks for jobs for you every day.",
     "sources": [("https://hiringcafe.com/", "home page"), ("https://hiringcafe.com/about", "about page")]},
    {"name": "Drivetube", "url": "https://drivetube.ai/", "kind": "site",
     "reads": "“crawled ATS-by-ATS from 140,000+ real company career pages across 50+ ATS platforms”",
     "jobs": "",
     "refresh": "“Nothing older than 3 days, ever, with a 24-hour setting”",
     "closed": "“Jobs are deleted 3 days after their real posting date (sponsorship roles are kept up to 60 days)”",
     "price": "The job board is free; paid services beside it (a human who applies for you: $150)",
     "apply": "“every listing links to the company’s own application page”",
     "also": "A resume profile, resume writing for a fee, visa sponsorship filters, apps for iOS and Android.",
     "sources": [("https://drivetube.ai/", "home page"), ("https://drivetube.ai/docs/overview", "overview page")]},
    {"name": "Spool Job Search", "url": "https://apify.com/spool/job-search", "kind": "tool",
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
    ("LinkUp", "its site asked our browser to prove it was a person, and we do not go past such checks"),
    ("Jobright", "its home page states “Total Jobs 8,000,000+” and “no fake listings” and does not say where the jobs are read from"),
    ("Hidden Roles, JobYap and CrawlJobs", "their pages did not open that day"),
]


def check():
    for x in ENGINES:
        assert x["kind"] in ("site", "tool") and x["url"].startswith("https://") and x["sources"], x["name"]
        for k in COLS + ("also",): assert isinstance(x[k], str) and len(x[k]) < 190, (x["name"], k)
        assert x["reads"], x["name"]
        for u, w in x["sources"]: assert u.startswith("https://") and w, x["name"]
    assert len({x["name"] for x in ENGINES}) == len(ENGINES)
    return len(ENGINES)


if __name__ == "__main__":
    print(f"{check()} job search engines, read {READ}; {sum(1 for x in ENGINES for k in COLS if not x[k])} cells not stated; {len(NOT_READ)} named and not read")
