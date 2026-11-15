"""Is this job already on the site? A check that answers in well under a millisecond (the owner, 15 Nov 2026: "check for
duplicates and spam, but mega fast, so it sees at once whether the job is already posted").

One job, many places: a company often publishes the same role on its own careers page, a job board and a Telegram channel, and
under slightly different names ("Sr. Software Engineer (Remote, US)" and "Senior Software Engineer"). Two postings are the same
job when
  - the company is the same once legal endings and punctuation are dropped ("Stripe, Inc." = "Stripe");
  - the titles are the same once abbreviations, gender markers and place notes are normalised, or share at least 85% of their
    words, with the same level words (Senior is never Junior, Engineer II is never Engineer III);
  - and the places overlap: a shared country, or one of them is remote or names no place. The same role in London and in New York
    is two jobs, not one.
The same link to apply is always the same job.

The index holds every open job in memory, grouped by company, so a check reads only that company's jobs.

    python3 dedupe.py --test      the pairs that must and must not be the same job
    python3 dedupe.py --bench     builds the index from data/jobs.db and times 10,000 checks
"""
import json, re, sqlite3, sys, time, unicodedata
from pathlib import Path

LEGAL = re.compile(r"\b(incorporated|inc|llc|l l c|ltd|limited|gmbh|ag|sa|sas|sarl|bv|b v|nv|plc|corp|corporation|co|company|pty|pte|"
                   r"oy|ab|asa|spa|s p a|srl|kk|kg|se|holdings?|group|technologies|technology|labs?)\b")
GENDER = re.compile(r"\(?\b(m|f|w|d|x|h|all)\s*/\s*(m|f|w|d|x|h)(\s*/\s*(m|f|w|d|x|h))?\b\)?|\ball genders\b", re.I)
PLACE_NOTE = re.compile(r"[\(\[][^\)\]]*\b(remote|hybrid|on-?site|office|based|us|usa|uk|eu|emea|apac|latam|anywhere|worldwide|"
                        r"united states|united kingdom|europe|canada|india|germany)\b[^\)\]]*[\)\]]", re.I)
ABBR = [(r"\bsr\b\.?", "senior"), (r"\bjr\b\.?", "junior"), (r"\bmgr\b", "manager"), (r"\beng\b", "engineer"), (r"\bdev\b", "developer"),
        (r"\bswe\b", "software engineer"), (r"\bpm\b", "product manager"), (r"\bvp\b", "vice president"), (r"&", " and "),
        (r"\bi{3}\b", "level3"), (r"\bii\b", "level2"), (r"\biv\b", "level4"), (r"\bi\b", "level1"), (r"\b([1-5])\b", r"level\1")]
LEVEL = {"senior", "junior", "lead", "staff", "principal", "head", "intern", "director", "chief", "vice", "associate", "entry",
         "level1", "level2", "level3", "level4", "level5", "manager"}
DROP = {"remote", "hybrid", "onsite", "on", "site", "the", "a", "an", "of", "for", "to", "in", "at", "and", "with", "full", "time",
        "part", "contract", "permanent", "temporary", "new"}


def ascii_lower(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def company_key(name):
    s = ascii_lower(name).replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\s+(careers|jobs|hiring|recruiting|talent)$", "", s)
    words = [w for w in LEGAL.sub(" ", s).split() if w]
    return " ".join(words) or s.strip()


def title_words(title):
    s = GENDER.sub(" ", title or "")
    s = PLACE_NOTE.sub(" ", s)
    s = re.sub(r"\s[-–—|,]\s*(remote|hybrid|on-?site)\b.*$", " ", s, flags=re.I)
    s = ascii_lower(s)
    for rx, to in ABBR: s = re.sub(rx, to, s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return [w for w in s.split() if w not in DROP]


def title_key(title):
    return " ".join(title_words(title))


def url_key(url):
    u = re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower())
    return re.split(r"[?#]", u, maxsplit=1)[0].rstrip("/")


def same_title(a, b):
    """a, b: word lists. The same role: equal, or 85% shared words with the same level words."""
    if a == b: return True
    sa, sb = set(a), set(b)
    if not sa or not sb or (sa & LEVEL) != (sb & LEVEL): return False
    return len(sa & sb) / max(len(sa), len(sb)) >= 0.85


class Index:
    """Every open job, grouped by company key. countries_of(location) -> set of country codes (the site's own reader)."""

    def __init__(self, countries_of=lambda loc: set()):
        self.by_co, self.by_url, self.countries_of, self.size = {}, {}, countries_of, 0
        self.exact = {}                      # (company key, title key) -> jobs: most checks end here, in one dictionary look-up
        self.by_level = {}                   # (company key, level words) -> jobs: the only ones a near title can match

    def add(self, slug, company, title, location="", remote=False, url="", extra=None):
        words = title_words(title)
        item = {"slug": slug, "company": company, "title": title, "location": location or "", "remote": bool(remote),
                "words": words, "where": frozenset(self.countries_of(location or "")), **(extra or {})}
        ck = company_key(company)
        self.by_co.setdefault(ck, []).append(item)
        self.exact.setdefault((ck, " ".join(words)), []).append(item)
        self.by_level.setdefault((ck, frozenset(set(words) & LEVEL)), []).append(item)
        if url: self.by_url[url_key(url)] = item
        self.size += 1

    def find(self, company, title, location="", remote=False, url="", limit=5):
        """The open jobs that are this one, best first: [{slug, title, company, location, why}]."""
        out = []
        if url and (hit := self.by_url.get(url_key(url))):
            out.append(dict(hit, why="the same link to apply"))
        words, where = title_words(title), frozenset(self.countries_of(location or ""))
        ck, seen = company_key(company), {o["slug"] for o in out}
        exact = self.exact.get((ck, " ".join(words)), [])
        near = [] if len(exact) >= limit else self.by_level.get((ck, frozenset(set(words) & LEVEL)), [])
        for item in exact + near:
            if item["slug"] in seen or not same_title(words, item["words"]): continue
            if where and item["where"] and not (where & item["where"]) and not (remote or item["remote"]): continue
            seen.add(item["slug"])
            out.append(dict(item, why="the same company and role" + (" in the same place" if where & item["where"] else "")))
            if len(out) >= limit: break
        return [{k: v for k, v in o.items() if k not in ("words", "where")} for o in out]


def from_db(path, countries_of=lambda loc: set()):
    """An index of the open jobs in data/jobs.db (records.py)."""
    idx = Index(countries_of)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    for slug, company, rec in con.execute("SELECT slug, company, rec FROM jobs WHERE active = 1"):
        j = json.loads(rec)
        idx.add(slug, company, j.get("title", ""), j.get("location", ""), j.get("remote", False), j.get("url", ""))
    con.close()
    return idx


def _test():
    cc = lambda loc: {c for c, rx in (("US", r"\b(us|usa|united states|new york|san francisco|, ca|, ny)\b"), ("GB", r"london|united kingdom|\buk\b"),
                                      ("DE", r"berlin|germany")) if re.search(rx, loc.lower())}
    idx = Index(cc)
    idx.add("a", "Stripe, Inc.", "Senior Software Engineer", "San Francisco, CA", url="https://boards.greenhouse.io/stripe/jobs/1?gh_src=x")
    idx.add("b", "Acme GmbH", "Data Scientist (m/w/d)", "Berlin, Germany")
    idx.add("c", "Acme GmbH", "Backend Engineer", "Berlin, Germany")
    idx.add("d", "Globex", "Software Engineer II", "London, UK")
    idx.add("e", "Globex", "Product Designer", "", remote=True)
    must = [("Stripe", "Sr. Software Engineer (Remote, US)", "United States", "a"),
            ("Stripe Inc", "Senior Software Engineer", "", "a"),
            ("Anything", "Different title", "", "a", "https://boards.greenhouse.io/stripe/jobs/1"),
            ("ACME", "Data Scientist", "Berlin", "b"),
            ("Globex Ltd.", "Software Engineer 2", "London", "d"),
            ("Globex", "Product Designer", "New York, NY", "e")]
    never = [("Stripe", "Junior Software Engineer", "San Francisco, CA"),
             ("Acme", "Frontend Engineer", "Berlin"),
             ("Globex", "Software Engineer III", "London"),
             ("Globex", "Software Engineer II", "New York, NY"),
             ("Initech", "Senior Software Engineer", "San Francisco, CA")]
    bad = 0
    for row in must:
        co, t, loc, want = row[:4]
        got = [m["slug"] for m in idx.find(co, t, loc, url=row[4] if len(row) > 4 else "")]
        if want not in got: bad += 1; print("MISSED", row, got)
    for co, t, loc in never:
        got = idx.find(co, t, loc)
        if got: bad += 1; print("WRONG MATCH", (co, t, loc), [m["slug"] for m in got])
    print(f"{len(must)} pairs that are one job, {len(never)} that are not: {bad} wrong")
    return bad


def _bench(path):
    t0 = time.perf_counter(); idx = from_db(path); t1 = time.perf_counter()
    items = [i for xs in idx.by_co.values() for i in xs][:10000]
    t2 = time.perf_counter()
    found = sum(bool(idx.find(i["company"], i["title"], i["location"], i["remote"])) for i in items)
    t3 = time.perf_counter()
    print(f"index of {idx.size:,} open jobs built in {t1 - t0:.1f} s; {len(items):,} checks in {(t3 - t2) * 1000:.0f} ms "
          f"({(t3 - t2) / max(len(items), 1) * 1e6:.0f} µs each), {found:,} found themselves")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]: sys.exit(1 if _test() else 0)
    if sys.argv[1:] == ["--bench"]: _bench(Path(__file__).parent / "data" / "jobs.db")
