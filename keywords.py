"""What people type into Google about jobs: collects search suggestions for a list of seed phrases.

    python3 keywords.py            # all seeds, plus an a-z sweep for the main ones (about 5 minutes)
    python3 keywords.py "free job" # one extra seed, with its a-z sweep

Writes keywords.json: every suggestion with the seed that produced it. Read it, group the phrases by what the searcher wants,
and compare with the pages we have (ROADMAP.md, section "Search demand"). Phrases we cannot honestly serve are skipped.
"""
import datetime, json, string, sys, time
from pathlib import Path
from urllib.parse import quote
from net import get_json

ROOT = Path(__file__).parent
SEEDS = [
    "free job", "jobs", "tech jobs", "it jobs", "remote jobs", "remote tech jobs", "work from home jobs", "entry level tech jobs", "software engineer jobs",
    "developer jobs", "ai jobs", "machine learning jobs", "crypto jobs", "web3 jobs", "startup jobs", "jobs hiring", "who is hiring", "companies hiring",
    "job search", "job board", "job sites", "free resume", "resume builder", "resume", "ats resume", "cover letter", "salary", "tech salary",
    "software engineer salary", "job description", "post a job", "free job posting", "job posting", "hiring", "interview questions", "job alerts",
    "visa sponsorship jobs", "jobs with relocation", "4 day work week jobs", "part time tech jobs", "tech internships", "junior developer jobs",
    "how to get a job in tech", "how to find a job", "best jobs", "job offer", "stock options", "job tracker", "job application", "recruiter", "boolean search",
    "python jobs", "rust jobs", "react jobs", "data engineer jobs", "product manager jobs", "devops jobs", "cybersecurity jobs", "tech jobs in",
]
SWEEP = ["free job", "jobs", "tech jobs", "remote jobs", "free resume", "job", "salary", "hiring", "tech jobs for", "jobs that", "jobs for", "jobs with", "jobs without"]


def suggest(q):
    d = get_json("https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q=" + quote(q), 15)
    return [s for s in d[1] if isinstance(s, str)] if isinstance(d, list) and len(d) > 1 and isinstance(d[1], list) else None


def main():
    extra = [a.strip().lower() for a in sys.argv[1:] if a.strip()]
    queries = [s + " " for s in SEEDS + extra] + [f"{s} {ch}" for s in SWEEP + extra for ch in string.ascii_lowercase]
    out_file = ROOT / "keywords.json"
    found = json.loads(out_file.read_text()).get("suggestions", {}) if out_file.exists() else {}
    failed = 0
    for i, q in enumerate(dict.fromkeys(queries)):
        got = suggest(q)
        if got is None:
            failed += 1
            if failed >= 8: print("the suggestion service stopped answering; keeping what was collected"); break
            time.sleep(3); continue
        for s in got:
            found.setdefault(s.strip().lower(), q.strip())
        time.sleep(0.35)
        if i % 60 == 59: print(f"{i + 1} queries, {len(found)} phrases")
    out_file.write_text(json.dumps({"updated": datetime.date.today().isoformat(), "suggestions": dict(sorted(found.items()))}, ensure_ascii=False, indent=0))
    print(f"{len(found)} phrases in keywords.json")


if __name__ == "__main__":
    main()
