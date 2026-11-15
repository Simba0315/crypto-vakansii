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


# Company names that are one employer (added with the collector's pass, run() below; each has a test pair in dedupe_test.py)
ALIASES = {"meta platforms": "meta", "facebook": "meta", "alphabet": "google", "amazon web services": "amazon", "aws": "amazon",
           "x corp": "x", "twitter": "x", "bytedance": "tiktok"}


def ascii_lower(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def company_key(name):
    s = ascii_lower(name).replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"^the\s+", "", s)
    s = re.sub(r"\s+(careers|jobs|hiring|recruiting|talent)$", "", s)
    words = [w for w in LEGAL.sub(" ", s).split() if w]
    key = " ".join(words) or s.strip()
    return ALIASES.get(key, key)


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


# ---------------------------------------------------------------- the collector's pass over the whole database (collect.py)
# The same rules, applied to every open record at the end of each run: one opening listed by several sources (the employer's own
# board, a job posted on our site, a public portal, a job site, a channel) is shown once. Two records are one job when the company
# and title rules above agree (the title read without a trailing note of the job's own city: "Product Designer - New York"), the
# places overlap (a city or a country in common, or one side is remote or names no place; "Remote, UK" is not "Remote - Sweden"),
# they were posted within 45 days of each other, and they come from different sources (one board listing a job twice is the
# employer's own business). One record is kept, by the source's rank: the employer's own hiring system first, then a job posted on
# our site, then a public employment service, then a job site, then Telegram; an earlier first sighting breaks a tie. The others
# get "dup_of" (the kept id) and are left out of every page by build.py; the kept one lists them in "seen_on" ("Also listed on").
# Records are taken best source first and attach to a kept record; kept records never merge with each other, so two postings of
# one board stay two even when a job site lists a third copy that matches both. Worked out afresh every run: when the kept record
# closes, the next best comes back by itself.
import datetime                                                     # noqa: E402
from collections import defaultdict                                 # noqa: E402

SOURCE_RANK = {"direct": 1, "trudvsem": 2, "platsbanken": 2, "usajobs": 2, "arbeitnow": 3, "remotive": 3, "himalayas": 3, "jobicy": 3, "remoteok": 3,
               "themuse": 3, "hn": 3, "tg": 4}      # any other id prefix is an employer's own hiring system: 0
DAYS = 45
COUNTRY_WORDS = {"usa": "united states", "us": "united states", "u s": "united states", "united states of america": "united states", "america": "united states",
                 "uk": "united kingdom", "u k": "united kingdom", "england": "united kingdom", "great britain": "united kingdom", "britain": "united kingdom"}


def places(j):
    """Lower-case cities and countries the location names, and '*remote' when the job is remote."""
    out = {p.strip().lower() for p in re.split(r"[,;/|•]| or | and ", j.get("location") or "") if len(p.strip()) >= 2}
    out.discard("remote")
    if j.get("remote"): out.add("*remote")
    return out


def lands(p):
    """The countries among a record's place words ("Remote - Sweden" -> {"sweden"}), US and UK spellings made one."""
    import countries
    names = {n.lower() for n in countries.NAMES.values()} | set(COUNTRY_WORDS.values())
    out = set()
    for x in p:
        x = re.sub(r"\bremote\b|[-–—()\[\]]", " ", x)
        x = re.sub(r"\s+", " ", re.sub(r"\.", " ", x)).strip()
        x = COUNTRY_WORDS.get(x, x)
        if x in names: out.add(x)
    return out


def day(j):
    try: return datetime.date.fromisoformat((j.get("posted") or j.get("first_seen") or "")[:10])
    except ValueError: return None


def prepared(j):
    """What the comparison needs, worked out once per record."""
    t = str(j.get("title") or "")
    for city in {c.strip() for c in re.split(r"[,;/|]", str(j.get("location") or "").lower()) if len(c.strip()) >= 3}:
        t = re.sub(r"\s*[-–—,:|@]\s*" + re.escape(city) + r"\b.*$", "", t, flags=re.I)
    w = title_words(t)
    p = places(j)
    return {"w": w, "s": set(w), "p": p, "c": lands(p), "d": day(j)}


def same(a, b, pa=None, pb=None):
    pa, pb = pa or prepared(a), pb or prepared(b)
    if not same_title(pa["w"], pb["w"]): return False
    xa, xb = pa["p"], pb["p"]
    if pa["c"] and pb["c"] and not pa["c"] & pb["c"]: return False
    if xa and xb and not ("*remote" in xa and "*remote" in xb) and not ((xa - {"*remote"}) & (xb - {"*remote"})) and not (pa["c"] & pb["c"]): return False
    da, dbb = pa["d"], pb["d"]
    return not (da and dbb and abs((da - dbb).days) > DAYS)


def source(j):
    """Where a record comes from: its board or portal, the Telegram channel, or our own posting form."""
    if j.get("tg"): return "tg:" + j["tg"]
    if j.get("direct"): return "direct"
    return j.get("src") or j["id"].split("-", 1)[0] + ":" + j["company"]


def rank(j):
    if j.get("tg"): return SOURCE_RANK["tg"]
    if j.get("direct"): return SOURCE_RANK["direct"]
    return SOURCE_RANK.get(j["id"].split("-", 1)[0], 0)


def run(db, label=lambda j: j["id"].split("-", 1)[0]):
    """Mark the duplicates among the open records of db (in place). Returns how many records were marked."""
    for j in db.values():
        j.pop("dup_of", None); j.pop("seen_on", None)
    by_co = defaultdict(list)
    for j in db.values():
        if j.get("active"): by_co[company_key(j["company"])].append(j)
    marked = 0
    for jobs in by_co.values():
        if len({source(j) for j in jobs}) < 2: continue          # one source only: nothing to compare (almost every company)
        prep = {j["id"]: prepared(j) for j in jobs}
        keepers, by_word = [], defaultdict(list)
        for j in sorted(jobs, key=lambda j: (rank(j), j.get("first_seen_at") or j.get("first_seen") or "9", j["id"])):
            pj, src = prep[j["id"]], source(j)
            best, seen = None, set()
            for w in pj["s"]:
                for k in by_word.get(w, ()):
                    if id(k) in seen: continue
                    seen.add(id(k))
                    if source(k) == src or any(x["src_key"] == src for x in k.get("_dups", ())): continue
                    if same(j, k, pj, prep[k["id"]]) and (best is None or (pj["w"] == prep[k["id"]]["w"]) > (pj["w"] == prep[best["id"]]["w"])):
                        best = k
            if best is None:
                keepers.append(j)
                for w in pj["s"]: by_word[w].append(j)
            else:
                best.setdefault("_dups", []).append({"src_key": src, "job": j})
        for k in keepers:
            dups = k.pop("_dups", None)
            if not dups: continue
            k["seen_on"] = [{"source": label(x["job"]), "url": x["job"]["url"]} for x in dups]
            for x in dups:
                x["job"]["dup_of"] = k["id"]; marked += 1
    return marked



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
