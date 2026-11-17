"""How many times people opened each company's job pages, from the web server's own log.

    sudo python3 views.py [days] [--json]          # on the server; days defaults to 14

Nothing new is recorded about visitors: this reads the access log nginx already keeps (14 days, then it is deleted by logrotate)
and the job records (data/jobs.db) to learn which company a job page belongs to. Robots are left out by their user agent, and a
visitor who opens the same page several times in a day counts once. The result is for the letter to companies (OUTREACH_DRAFT.md):
a company is told its number only when it is 50 or more. On 16 Nov 2026 the whole site had 94 such opens against 69,599 by robots,
so until search traffic arrives the letter goes without a number.
"""
import datetime, glob, gzip, hashlib, json, os, re, sqlite3, sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("HRN_ROOT") or Path(__file__).resolve().parent)       # HRN_ROOT: the site's folder, when the script is run from elsewhere
LOGS = "/var/log/nginx/hrn.access.log*"
# what calls itself a robot, a library or a preview fetcher; a browser's user agent has none of these words
ROBOT = re.compile(r"bot|spider|crawl|slurp|curl|wget|python|go-http|okhttp|java/|headless|scrapy|gpt|claude|anthropic|perplexity|bytespider|facebookexternal|"
                   r"meta-external|semrush|ahrefs|dataprovider|barkrowler|dotbot|mj12|petal|yandex|bing|duckduck|applebot|preview|monitor|uptime|scan|"
                   r"compatible;|^-?$", re.I)
LINE = re.compile(r'^(\S+) \S+ \S+ \[(\d\d)/(\w{3})/(\d{4}):[^\]]*\] "GET /job/([a-z0-9-]+)/ HTTP/[\d.]+" 200 \d+ "[^"]*" "([^"]*)"')
MONTH = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}


def count(days=14, logs=LOGS, db=ROOT / "data" / "jobs.db"):
    """(opens by company, opens in all, robot requests left out, days the logs cover)"""
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    company = dict(con.execute("SELECT slug, company FROM jobs"))
    con.close()
    since = datetime.date.today() - datetime.timedelta(days=days)
    seen, by, robots, dates = set(), Counter(), 0, set()
    for f in sorted(glob.glob(logs)):
        with (gzip.open(f, "rt", errors="replace") if f.endswith(".gz") else open(f, errors="replace")) as fh:
            for line in fh:
                m = LINE.match(line)
                if not m: continue
                who, d_, mon, y_, slug, agent = m.groups()
                day = datetime.date(int(y_), MONTH.get(mon, 1), int(d_))
                if day < since: continue
                dates.add(day)
                if ROBOT.search(agent): robots += 1; continue
                key = hashlib.sha256(f"{who}|{agent}|{day}|{slug}".encode()).digest()[:10]       # one visitor, one page, one day: once
                if key in seen: continue
                seen.add(key)
                by[company.get(slug, "(not in the record)")] += 1
    return by, sum(by.values()), robots, len(dates)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    by, total, robots, covered = count(int(args[0]) if args else 14)
    if "--json" in sys.argv:
        print(json.dumps({"days_in_logs": covered, "opens_by_people": total, "requests_by_robots": robots, "companies": dict(by.most_common())}, ensure_ascii=False))
    else:
        print(f"{covered} days in the logs: job pages opened {total:,} times by people, {robots:,} requests by robots left out")
        print(f"companies with 50 opens or more: {sum(1 for v in by.values() if v >= 50)}")
        for c, n in by.most_common(25): print(f"{n:>6}  {c}")
