"""One job, many places: find the same opening listed by several sources and keep one record.

The owner, 15 Nov 2026: "one company can advertise in 20 places; make sure jobs don't repeat". collect.py calls run(db) at the end of
every run. Two open records are the same job when
  - the company is the same once normalised ("Acme, Inc." = "ACME" = "Acme GmbH"; a few known aliases),
  - the titles are the same once normalised ("Sr. Data Engineer (m/w/d) - Remote" = "senior data engineer"), or share at least
    90% of their words (token-set similarity, as fuzzywuzzy's token_set_ratio),
  - the places overlap (a city or a country in common, or one side is remote or names no place),
  - and they were posted within 45 days of each other,
  - and they come from different sources (one board listing a job twice is the employer's own business).
One record is kept, by the source's rank: the employer's own hiring system first, then a job posted on our site, then a public
employment service, then a job-board API, then Telegram (an earlier first sighting breaks a tie). The others get "dup_of" (the kept
id) and are left out of every page and count by build.py; the kept one lists them in "seen_on", shown as "Also listed on" on its page.
A record whose twin closed comes back by itself in the next run, because the clusters are worked out afresh each time.
"""
import datetime, re
from collections import defaultdict
from difflib import SequenceMatcher

LEGAL = re.compile(r"\b(inc|incorporated|llc|l\.l\.c|ltd|limited|gmbh|ag|se|s\.a|sa|sas|sarl|srl|bv|b\.v|nv|ab|oy|oyj|as|a/s|aps|plc|pty|corp|corporation|"
                   r"co|company|kg|ug|spa|s\.p\.a|group|holding|holdings|the)\b\.?", re.I)
ALIASES = {"meta platforms": "meta", "facebook": "meta", "alphabet": "google", "amazon web services": "amazon", "aws": "amazon",
           "x corp": "x", "twitter": "x", "bytedance": "tiktok", "block": "square"}
TITLE_ABBR = [(r"\bsr\b\.?", "senior"), (r"\bjr\b\.?", "junior"), (r"\bmgr\b\.?", "manager"), (r"\beng\b\.?", "engineer"), (r"\bdev\b", "developer"),
              (r"\bvp\b", "vice president"), (r"\bswe\b", "software engineer"), (r"&", " and ")]
SOURCE_RANK = {"direct": 1, "trudvsem": 2, "platsbanken": 2, "arbeitnow": 3, "remotive": 3, "himalayas": 3, "jobicy": 3, "remoteok": 3, "themuse": 3,
               "hn": 3, "usajobs": 2, "tg": 4}      # any other id prefix is an employer's own hiring system: 0
DAYS = 45
NOISE = re.compile(r"(100% )?(remote|hybrid|on-?site|in[- ]office|contract|contractor|full[- ]?time|part[- ]?time|permanent|temporary|freelance|fixed[- ]term|"
                   r"all genders?|gn\*?|remote[- ]first|anywhere|worldwide|usa?|uk|eu|emea|europe|apac|latam|[a-z]{2,3} only)", re.I)


def company_key(name):
    s = re.sub(r"[“”\"«»'’()]", " ", str(name or "").lower())
    s = re.sub(r"\s+", " ", LEGAL.sub(" ", s)).strip(" ,.-")
    s = ALIASES.get(s, s)
    return re.sub(r"[^\w]+", "", s)


def title_key(title, location=""):
    """Lower case, abbreviations written out, gender marks, brackets and a trailing place or "remote" taken off."""
    t = str(title or "").lower()
    t = re.sub(r"\((?:[mwfdhx]\s*/\s*){1,3}[mwfdhx]\)|\(all genders?\)|\(gn\*?\)", " ", t)
    cities = {c.strip() for c in re.split(r"[,;/|]", str(location or "").lower()) if len(c.strip()) >= 3}
    def bracket(m):       # "(Remote)", "(Contract)", "[Berlin]" say nothing about the job itself; "(DACH)" or "(Payments)" do
        inner = m.group(1).strip()
        return " " if NOISE.fullmatch(inner) or inner in cities else " " + inner + " "
    t = re.sub(r"[(\[]([^)\]]*)[)\]]", bracket, t)
    for city in cities: t = re.sub(r"[-–—,:|@]\s*" + re.escape(city) + r"\b.*$", " ", t)
    t = re.sub(r"[-–—,:|]\s*(remote|hybrid|on-?site|anywhere|worldwide|us|uk|eu|emea|europe|usa|united states)\b.*$", " ", t)
    for rx, full in TITLE_ABBR: t = re.sub(rx, full, t)
    return re.sub(r"\s+", " ", re.sub(r"[^\w+#]+", " ", t)).strip()


def token_set_ratio(a, b):
    """0..1: each title's set of words, shared words first, compared as text (word order and repeats do not count).
    Unlike fuzzywuzzy's token_set_ratio, a title inside a longer one does not score 1: "Product Manager" is not
    "Product Marketing Manager", and "Engineer" is not "Senior Engineer"."""
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb: return 0.0
    inter = " ".join(sorted(ta & tb))
    s1 = (inter + " " + " ".join(sorted(ta - tb))).strip()
    s2 = (inter + " " + " ".join(sorted(tb - ta))).strip()
    return SequenceMatcher(None, s1, s2).ratio()


def places(j):
    """Lower-case cities and countries the location names; 'remote' when the job is remote."""
    out = {p.strip().lower() for p in re.split(r"[,;/|•]| or | and ", j.get("location") or "") if len(p.strip()) >= 2}
    out.discard("remote")
    if j.get("remote"): out.add("*remote")
    return out


def overlap(a, b):
    pa, pb = places(a), places(b)
    if not pa or not pb or "*remote" in pa and "*remote" in pb: return True
    return bool((pa - {"*remote"}) & (pb - {"*remote"}))


def day(j):
    try: return datetime.date.fromisoformat((j.get("posted") or j.get("first_seen") or "")[:10])
    except ValueError: return None


def same(a, b):
    ta, tb = title_key(a["title"], a.get("location")), title_key(b["title"], b.get("location"))
    if ta != tb and token_set_ratio(ta, tb) < 0.9: return False
    if not overlap(a, b): return False
    da, dbb = day(a), day(b)
    return not (da and dbb and abs((da - dbb).days) > DAYS)


def source(j):
    """Where a record comes from, as one key: its board or portal, the Telegram channel, or our own posting form."""
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
        parent = {j["id"]: j["id"] for j in jobs}
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]; x = parent[x]
            return x
        by_src = defaultdict(list)
        for j in jobs: by_src[source(j)].append(j)
        srcs = list(by_src)
        for i, s1 in enumerate(srcs):
            for s2 in srcs[i + 1:]:
                for a in by_src[s1]:
                    for b in by_src[s2]:
                        if find(a["id"]) != find(b["id"]) and same(a, b): parent[find(a["id"])] = find(b["id"])
        clusters = defaultdict(list)
        for j in jobs: clusters[find(j["id"])].append(j)
        for cl in clusters.values():
            if len(cl) < 2: continue
            keep = min(cl, key=lambda j: (rank(j), j.get("first_seen_at") or j.get("first_seen") or "9", j["id"]))
            keep["seen_on"] = [{"source": label(j), "url": j["url"]} for j in cl if j is not keep]
            for j in cl:
                if j is not keep: j["dup_of"] = keep["id"]; marked += 1
    return marked
