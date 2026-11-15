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


LEVELS = {"intern", "internship", "junior", "senior", "staff", "principal", "lead", "head", "director", "chief", "vice", "i", "ii", "iii", "iv", "entry"}
COUNTRY_WORDS = {"usa": "united states", "us": "united states", "u s": "united states", "united states of america": "united states", "america": "united states",
                 "uk": "united kingdom", "u k": "united kingdom", "england": "united kingdom", "great britain": "united kingdom", "britain": "united kingdom"}


def lands(p):
    """The countries among a record's place words ("Remote - Sweden" -> {"sweden"}), US and UK spellings made one."""
    import countries
    names = {n.lower() for n in countries.NAMES.values()} | set(COUNTRY_WORDS.values())
    out = set()
    for x in p:
        x = re.sub(r"\bremote\b|[-–—()\[\]]", " ", x).strip()
        x = re.sub(r"\s+", " ", re.sub(r"\.", " ", x)).strip()
        x = COUNTRY_WORDS.get(x, x)
        if x in names: out.add(x)
    return out


def prepared(j):
    """What the comparison needs, worked out once per record (a company with 2,000 jobs on its board and 50 on a job site
    means 100,000 pairs)."""
    t = title_key(j["title"], j.get("location"))
    w = set(t.split())
    p = places(j)
    return {"t": t, "w": w, "lv": w & LEVELS, "p": p, "c": lands(p), "d": day(j)}


def same(a, b, pa=None, pb=None):
    pa, pb = pa or prepared(a), pb or prepared(b)
    if pa["t"] != pb["t"]:
        wa, wb = pa["w"], pb["w"]
        if not wa or not wb or len(wa & wb) < 0.75 * max(len(wa), len(wb)): return False      # far apart: no need for the slow comparison
        if pa["lv"] != pb["lv"]: return False                                    # "Senior …" and "Staff …" are two openings
        if token_set_ratio(pa["t"], pb["t"]) < 0.9: return False
    xa, xb = pa["p"], pb["p"]
    if pa["c"] and pb["c"] and not pa["c"] & pb["c"]: return False             # "Remote, UK" and "Remote - Sweden"
    if xa and xb and not ("*remote" in xa and "*remote" in xb) and not ((xa - {"*remote"}) & (xb - {"*remote"})) and not (pa["c"] & pb["c"]): return False
    da, dbb = pa["d"], pb["d"]
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
        prep = {j["id"]: prepared(j) for j in jobs}
        # Records are taken best source first. Each either matches a record already kept from another source and is attached to it,
        # or is kept itself. Kept records never merge with each other, so two postings of one board ("Account Executive, Norway"
        # and "…, Belgium") stay two even when a job site lists a third copy that matches both.
        keepers, by_word = [], defaultdict(list)
        for j in sorted(jobs, key=lambda j: (rank(j), j.get("first_seen_at") or j.get("first_seen") or "9", j["id"])):
            pj, src = prep[j["id"]], source(j)
            best, seen = None, set()
            for w in pj["w"]:
                for k in by_word.get(w, ()):
                    if id(k) in seen: continue
                    seen.add(id(k))
                    if source(k) == src or any(x["src_key"] == src for x in k.get("_dups", ())): continue
                    if same(j, k, pj, prep[k["id"]]) and (best is None or (pj["t"] == prep[k["id"]]["t"]) > (pj["t"] == prep[best["id"]]["t"])):
                        best = k
            if best is None:
                keepers.append(j)
                for w in pj["w"]: by_word[w].append(j)
            else:
                best.setdefault("_dups", []).append({"src_key": src, "job": j})
        for k in keepers:
            dups = k.pop("_dups", None)
            if not dups: continue
            k["seen_on"] = [{"source": label(x["job"]), "url": x["job"]["url"]} for x in dups]
            for x in dups:
                x["job"]["dup_of"] = k["id"]; marked += 1
    return marked
