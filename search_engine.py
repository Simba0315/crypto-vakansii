"""Search on Lucene: OpenSearch, the open-source search server built on Apache Lucene (the library under Elasticsearch, Solr and
the search of large job sites), running on our own server next to the page server. Nothing to install here: it is spoken to
over HTTP with Python's own urllib.

    python3 search_engine.py index          read data/jobs.db and load every job into a new index, then point the alias at it
    python3 search_engine.py search rust    try a search from the command line
    python3 search_engine.py --test         check the query builder (no server needed)

The address comes from HRN_OPENSEARCH (for example http://127.0.0.1:9200). Without it, or when the server does not answer,
serve.py searches with SQLite FTS5 in the records file, so the site never depends on this service being up.

What Lucene adds over FTS5: search that forgives typos ("pyhton" finds Python), words of the same family ("engineering" finds
"engineer"), synonyms ("k8s" finds Kubernetes), counts for the filters computed with the search ("Remote 812, Senior 230"),
and a phrase in the title ranked first.
"""
import datetime, hashlib, html, json, os, re, sqlite3, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
ALIAS = "jobs"
URL = os.environ.get("HRN_OPENSEARCH", "").rstrip("/")

# Words written differently that mean the same thing in a job search. Applied when searching, so the list can grow without
# loading the jobs again.
SYNONYMS = [
    "k8s, kubernetes", "js, javascript", "ts, typescript", "golang, go", "ml, machine learning", "ai, artificial intelligence",
    "llm, large language model", "nlp, natural language processing", "qa, quality assurance, tester", "sre, site reliability engineer",
    "ux, user experience", "ui, user interface", "pm, product manager", "swe, software engineer", "fe, frontend, front end",
    "be, backend, back end", "fullstack, full stack", "devops, dev ops", "web3, blockchain, crypto", "postgres, postgresql",
    "react, reactjs", "node, nodejs", "vue, vuejs", "dotnet, net", "csharp, c sharp", "cplusplus, c plus plus",
    "remote, work from home, wfh", "intern, internship", "jr, junior", "sr, senior",
]
# C++, C# and .NET lose their signs in a word index: they are written as one word on both sides (as in records.SPELL).
CHAR_MAP = ["c++ => cplusplus", "C++ => cplusplus", "c# => csharp", "C# => csharp", ".net => dotnet", ".NET => dotnet", "f# => fsharp", "F# => fsharp"]

SETTINGS = {
    "settings": {"number_of_shards": 1, "number_of_replicas": 0, "refresh_interval": "-1",
                 "analysis": {
                     "char_filter": {"signs": {"type": "mapping", "mappings": CHAR_MAP}},
                     "filter": {"en_stem": {"type": "stemmer", "language": "light_english"},
                                "job_synonyms": {"type": "synonym_graph", "synonyms": SYNONYMS, "lenient": True}},
                     "analyzer": {"job": {"type": "custom", "char_filter": ["signs"], "tokenizer": "standard",
                                          "filter": ["lowercase", "asciifolding", "en_stem"]},
                                  "job_search": {"type": "custom", "char_filter": ["signs"], "tokenizer": "standard",
                                                 "filter": ["lowercase", "asciifolding", "job_synonyms", "en_stem"]}}}},
    # _meta.v: what the index can answer. 2 (25 Nov 2026): every filter of the search page and the fields a row of results shows, so
    # the page asks the server instead of downloading every job (22 MB). serve.py answers a list only from an index of this version.
    # The text of the posting is searched but not kept in _source: nothing reads it back, and it was most of the index on disk.
    "mappings": {"dynamic": "false", "_meta": {"v": 2}, "_source": {"excludes": ["body"]}, "properties": {
        "slug": {"type": "keyword"}, "active": {"type": "boolean"}, "remote": {"type": "boolean"}, "hybrid": {"type": "boolean"},
        "title": {"type": "text", "analyzer": "job", "search_analyzer": "job_search"},
        "company": {"type": "text", "analyzer": "job", "search_analyzer": "job_search", "fields": {"raw": {"type": "keyword"}}},
        "tags": {"type": "text", "analyzer": "job", "search_analyzer": "job_search", "fields": {"raw": {"type": "keyword"}}},
        "place": {"type": "text", "analyzer": "job", "search_analyzer": "job_search"},
        "body": {"type": "text", "analyzer": "job", "search_analyzer": "job_search"},
        "cat": {"type": "keyword"}, "level": {"type": "keyword"}, "posted": {"type": "date", "ignore_malformed": True},
        "pay_mid": {"type": "float"}, "pay_hi": {"type": "float"}, "has_pay": {"type": "boolean"},
        "places": {"type": "keyword"}, "cc": {"type": "keyword"}, "perks": {"type": "keyword"}, "etype": {"type": "keyword"},
        "crypto": {"type": "boolean"}, "anywhere": {"type": "boolean"}, "pool": {"type": "boolean"}, "exec": {"type": "boolean"},
        "featured": {"type": "boolean"}, "premium": {"type": "boolean"}, "pinned": {"type": "boolean"},
        "ts": {"type": "long"}, "rot": {"type": "keyword"}, "ckey": {"type": "keyword"}}},
}
VERSION = SETTINGS["mappings"]["_meta"]["v"]
FIELDS = ["title^10", "company^5", "tags^4", "place^3", "body"]
TAGS = re.compile(r"<[^>]+>")


def call(method, path, body=None, timeout=10.0, ndjson=False):
    """One request to OpenSearch; the answer as a dict. Raises OSError (urllib's errors are OSError) when it does not answer."""
    data = None
    if body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(URL + path, data=data, method=method,
                                 headers={"Content-Type": "application/x-ndjson" if ndjson else "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as err:
        raise OSError(f"OpenSearch {method} {path}: {err.code} {err.read()[:300]!r}") from None


# "Director and above" in the level filter: the same words as EXEC in assets/site.js
EXEC = re.compile(r"\b(director|vp|svp|evp|vice president|head of|chief|cto|ceo|cfo|coo|cmo|cpo|ciso|cro)\b", re.I)
SEP = "\x1f"


def day_start(day):
    """Seconds since 1970 at the start of a yyyy-mm-dd day (UTC); 0 when it is not a date."""
    try:
        return int(datetime.datetime.fromisoformat(day[:10] + "T00:00:00+00:00").timestamp())
    except (TypeError, ValueError):
        return 0


HOURS = 2080              # working hours in a year: an hourly rate in the pay filter and in "Highest pay" (search page, "$20/h+")
# The store, mall, cinema or town an employer appends to a title it posts at every address: "Seasonal Key Holder - Oak Park Mall" is the
# role "Seasonal Key Holder" (data teardown, 26 Nov 2026: BoxLunch's 924 "Seasonal Sales Associate" postings stood as 16 rows on its
# company page, one per mall). A tail that names the work ("Software Engineer - Backend", "Assistant Manager - Level 2") stays.
ROLE_TAIL = re.compile(r"(?:\s[-–—|@]\s*|\s*[–—|@:,]\s*|\s+at\s+)((?:(?!\s[-–—|@]\s|[–—|@:,]).){2,80})$|\s*[\(\[]([^\)\]]{2,80})[\)\]]\s*(?:seasonal hire)?\s*$", re.I)
PLACEISH = re.compile(r"\b(?:malls?|cent(?:er|re)|outlets?|plaza|village|galleria|square|commons|crossings?|marketplace|mills|promenade|pavilion|shops|shoppes|station|stores?|"
                      r"cinemas?|theat(?:er|re)s?|hospital|campus|clinic|branch|downtown|airport|towne?|city|county|park|parkway|fashion|premium|place|pointe?|landing|"
                      r"district|metro|lodge|resort|hotel|depot|terminal|warehouse|dc|location|#\s?\d+|\d{3,})\b", re.I)
STATE_TAIL = re.compile(r"(?:^|,\s?|\s)(?:A[KLRZ]|C[AOT]|D[CE]|FL|GA|HI|I[ADLN]|K[SY]|LA|M[ADEINOST]|N[CDEHJMVY]|O[HKR]|PA|RI|S[CD]|T[NX]|UT|V[AT]|W[AIVY])\s*$")


def role_key(title, place=""):
    """The role a title names, for one row per role in the lists and the search: lower case, without a store, mall or town at its end."""
    t, low_place = " ".join((title or "").split()), (place or "").lower()
    for _ in range(3):
        m = ROLE_TAIL.search(t)
        if not m: break
        tail = (m.group(1) or m.group(2) or "").strip()
        city = low_place.split(",")[0].strip()
        if not tail or not (PLACEISH.search(tail) or STATE_TAIL.search(tail) or (len(tail) > 3 and tail.lower() in low_place) or (len(city) > 3 and city in tail.lower())) \
                or len(t[:m.start()].strip()) < 3: break
        t = t[:m.start()].strip()
    return re.sub(r"[^\w+#]+", " ", t.lower()).strip()


def doc(rec, descr, codes=None, day=""):
    """The searchable part of one job record, and what a row of results shows. codes: place slug -> country code (build.PLACE_CODE),
    for the flags and "remote open to my country"; day: the build's day, which turns the order of the paid Premium jobs."""
    usd = rec.get("usd")
    if not usd and rec.get("usd_h"):                  # an hourly rate: the pay filter and "Highest pay" read it as a year of 2,080 hours
        usd = [rec["usd_h"][0] * HOURS, rec["usd_h"][1] * HOURS]
    title, company, posted = rec.get("title") or "", rec.get("company") or "", (rec.get("posted") or rec.get("first_seen") or "")[:10]
    places = [p for p in rec.get("places") or [] if isinstance(p, str)]
    premium = bool(rec.get("premium"))
    return {"slug": rec["slug"], "active": bool(rec.get("active")), "remote": bool(rec.get("remote")), "hybrid": bool(rec.get("hybrid")),
            "title": title, "company": company, "tags": rec.get("tags") or [],
            "place": rec.get("location") or "", "body": html.unescape(TAGS.sub(" ", descr or rec.get("excerpt") or "")),
            "cat": rec.get("cat") or "", "level": rec.get("level") or "", "posted": posted or None,
            "pay_mid": (usd[0] + usd[1]) / 2 if usd else None, "pay_hi": float(usd[1]) if usd else None,
            "salary": rec.get("salary") or "", "has_pay": bool(rec.get("salary")),
            "places": places, "cc": list(dict.fromkeys(c for c in ((codes or {}).get(p) for p in places) if c)),
            "perks": [x for x in rec.get("perks") or [] if isinstance(x, str)], "etype": rec.get("etype") or "",
            "crypto": bool(rec.get("crypto")), "anywhere": bool(rec.get("anywhere")), "pool": bool(rec.get("pool")), "exec": bool(EXEC.search(title)),
            "featured": bool(rec.get("featured")), "urgent": bool(rec.get("urgent")), "premium": premium, "pinned": bool(rec.get("pinned")),
            # the order of "Newest first", as build.order(): paid first, then the newest, a bumped job as new as its bump
            "t": int(rec.get("t") or 0), "ts": max(int(rec.get("ts") or 0) or day_start(posted), int(rec.get("bump") or 0)),
            "rot": hashlib.md5(f"{day}-{rec['slug']}".encode()).hexdigest() if premium else "",
            "ckey": (company + SEP + (rec.get("rkey") or role_key(title, rec.get("location") or "")))[:2000]}      # the same role posted once per city is one row with "+N more locations"


def index(db_path=ROOT / "data" / "jobs.db", keep=1):
    """Load every job into a new index, then move the alias to it in one step, so searches never see a half-loaded index."""
    name = f"{ALIAS}-{datetime.datetime.now(datetime.timezone.utc):%Y%m%d%H%M%S}"
    call("PUT", f"/{name}", SETTINGS)
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    t0, n, batch = time.time(), 0, []

    def flush():
        if not batch: return
        r = call("POST", f"/{name}/_bulk", "".join(batch), timeout=120, ndjson=True)
        if r.get("errors"):
            first = next(i for i in r["items"] if i["index"].get("error"))
            raise OSError(f"bulk load failed: {first['index']['error']}")
        batch.clear()

    try:
        import build                                 # the place codes: what the flags and "remote open to my country" read
        codes = build.PLACE_CODE
    except Exception:                                 # never stop the load for them: without them those two show nothing
        codes = {}
    try:
        day = json.loads(con.execute("SELECT v FROM ctx WHERE k = 'today'").fetchone()[0])
    except Exception:
        day = ""
    for slug, rec, descr in con.execute("SELECT slug, rec, descr FROM jobs"):
        batch.append(json.dumps({"index": {"_id": slug}}) + "\n" + json.dumps(doc(json.loads(rec), descr, codes, day), ensure_ascii=False) + "\n")
        n += 1
        if len(batch) >= 1000: flush()
    flush()
    con.close()
    call("PUT", f"/{name}/_settings", {"index": {"refresh_interval": "30s"}})
    call("POST", f"/{name}/_refresh")
    try:
        holders = list(call("GET", f"/_alias/{ALIAS}").keys())         # the index the alias points at now (none on the first run)
    except OSError:
        holders = []
    call("POST", "/_aliases", {"actions": [{"remove": {"index": i, "alias": ALIAS}} for i in holders] + [{"add": {"index": name, "alias": ALIAS}}]})
    older = sorted(x["index"] for x in call("GET", f"/_cat/indices/{ALIAS}-*?format=json&h=index") if x["index"] != name)
    for i in older[:max(0, len(older) - keep)]: call("DELETE", f"/{i}")   # the previous one is kept one round, to go back to if needed
    return name, n, time.time() - t0


WORD = re.compile(r"[^\W_]+(?:[+#]+)?|\.net\b", re.U | re.I)
SKIP = {"a", "an", "and", "or", "not", "the", "of", "in", "at", "for", "to", "with", "on", "job", "jobs", "role", "roles", "position",
        "positions", "vacancy", "vacancies", "opening", "openings", "career", "careers", "hiring", "work"}


def split_words(q):
    """(the words to look for, whether "remote" was one of them): "remote" is the remote filter, words like "jobs" say nothing."""
    words = WORD.findall(q or "")[:12]
    said_remote = any(w.lower() == "remote" for w in words)
    return [w for w in words if w.lower() != "remote" and w.lower() not in SKIP], said_remote


# ---- Places, hours and level in the words typed (data teardown, 26 Nov 2026) ---------------------------------------------------------
# "software engineer new york" looked for the words "new" and "york" anywhere, so "Software Engineer, New Grad" outranked the engineers in
# New York (11 of the first 20 wrong); "part time" matched "full-time" and "part of our team" in 95,590 postings. A place, the hours and
# "entry level" in the words are filters now, as the page's own smart search (assets/app.js, smart()) has made them in the visitor's
# browser since 13 Nov; this does the same for every address that sends words (the API, a shared link, the assistants' connector).
PLACE_ALIAS = {"united-states": ("usa", "united states", "u.s.", "america"), "united-kingdom": ("uk", "britain", "england", "united kingdom"),
               "san-francisco": ("san francisco", "bay area", "sf bay area"), "new-york": ("nyc", "new york city", "new york"), "washington-dc": ("washington dc", "washington d.c."),
               "uae": ("dubai", "uae", "emirates"), "raleigh-durham": ("raleigh", "durham"), "los-angeles": ("los angeles",),
               # the metro areas by the names people give them (27 Nov 2026; every list holds its whole metro area, build.places_of)
               "dallas": ("dfw", "dallas fort worth", "dallas-fort worth", "dallas/fort worth"), "minneapolis": ("minneapolis", "twin cities", "st. paul", "st paul", "saint paul"),
               "philadelphia": ("philly",)}
_GEO = {}


def geo():
    """The place names a query can name ("new york", "dallas", "texas", "uk") with their place pages, the US cities that pages and the jobs
    map know, and the states, read once from build.PLACES and geo_cities (serve.py has both in memory already)."""
    if _GEO: return _GEO
    try:
        import build
        places, place_state, states = build.PLACES, build.PLACE_STATE, build.US_STATE_CODE
    except Exception:                                       # never stop a search for it: without them the words are words
        places, place_state, states = [], {}, {}
    try:
        import geo_cities
        cities = {v[0].lower() for v in geo_cities.CITIES.values() if v[1] == "US"} | {k.lower() for k, v in getattr(geo_cities, "ALIAS", {}).items()
                                                                                         if geo_cities.CITIES.get(v, ("", ""))[1] == "US"}
    except Exception:
        cities = set()
    names, city_slug = {}, {}
    for name, slug, rule in places:
        t = name.lower().removeprefix("the ")
        cands = {t} | {x.strip().removeprefix("the ") for x in t.split(" & ")} | set(PLACE_ALIAS.get(slug, ()))
        m = re.fullmatch(r"(.+?), ([a-z]{2})", t)
        if m and m.group(1) != "washington": cands.add(m.group(1))
        for c in cands:
            if len(c) > 2 or c == "uk": names.setdefault(c, slug)
        if slug in place_state:
            for c in cands:
                if c not in {"texas", "california", "florida"} and "," not in c: city_slug[c] = slug
    by_len = sorted(names, key=len, reverse=True)
    _GEO.update(names=names, city_slug=city_slug, place_state=place_state, states=states, codes=set(states.values()), cities=cities | set(city_slug),
                rx=re.compile(r"(?:\b(?:in|near|at|around)\s+)?(?<![\w-])(?<!new )(" + "|".join(re.escape(n) for n in by_len) + r")(?![\w-])", re.I) if by_len else None,
                state_rx=re.compile(r"(?:,\s*|\s+)(" + "|".join(sorted((re.escape(n) for n in states), key=len, reverse=True)) + r"|[a-z]{2})\s*$", re.I) if states else None,
                name_of={v: k for k, v in states.items()})
    return _GEO


def state_of(word):
    """The two-letter code of a US state written as its code or its name ("tx", "Texas"), or ""."""
    g, w = geo(), (word or "").strip().lower()
    if w.upper() in g["codes"]: return w.upper()
    return g["states"].get(w, "")


def city_clause(city):
    """The filter for a city typed by the visitor, which must agree with its state when one is written: "Dallas, TX" is the Dallas place
    page (its whole metro area: Dallas, Fort Worth, Arlington, Irving, Frisco and the other towns of metros.py, never Dallas, Oregon, or
    "GA - Dallas"), "Albany, NY" an Albany line that names New York; "Irving, TX" the jobs whose own place line names Irving, Texas."""
    g = geo()
    c = " ".join((city or "").lower().replace(",", " , ").split()).strip(" ,")
    name, st = c, ""
    m = g["state_rx"].search(c) if g["state_rx"] else None
    if m and state_of(m.group(1)) and c[:m.start()].strip(" ,"):
        name, st = c[:m.start()].strip(" ,"), state_of(m.group(1))
    slug = g["city_slug"].get(name)
    if slug and (not st or g["place_state"].get(slug) == st): return {"term": {"places": slug}}
    if not st: return {"match_phrase": {"place": name}}
    return {"bool": {"must": [{"match_phrase": {"place": name}}],
                     "should": [{"match": {"place": st.lower()}}, {"match_phrase": {"place": g["name_of"].get(st, st.lower())}}], "minimum_should_match": 1}}


def read_query(q):
    """What the words typed say besides the words: {"words", "remote", "place" (a place page's slug), "city" ("dallas, tx"), "etype"
    ("Part-time", "Full-time"), "entry"}. A place is taken only when other words remain ("new york" alone is still searched as words)."""
    text, out = " " + (q or "").lower() + " ", {"place": "", "city": "", "etype": "", "entry": False}
    for rx, k, v in ((r"\bentry[- ]level\b", "entry", True), (r"\bpart[- ]?time\b", "etype", "Part-time"), (r"\bfull[- ]?time\b", "etype", "Full-time")):
        if re.search(rx, text) and not out[k]: out[k] = v; text = re.sub(rx, " ", text)
    g = geo()
    m = g["state_rx"].search(text.rstrip()) if g["state_rx"] else None
    if m and state_of(m.group(1)):                        # "nurse dallas tx", "teacher in albany, new york": a US city and its state at the end
        head = re.sub(r"\s+(?:in|near|at|around)\s*$", " ", text.rstrip()[:m.start()]).split()
        prep = max((i for i, w in enumerate(head) if w in ("in", "near", "at", "around")), default=-1)
        for k in range(min(3, len(head) - 1), 0, -1):
            # a city the site knows, or the one or two words after "in" ("nurse in albany ny")
            if " ".join(head[-k:]).strip(",") in g["cities"] or (prep >= 1 and len(head) - prep - 1 == k and k <= 2):
                out["city"] = " ".join(head[-k:]).strip(",") + ", " + state_of(m.group(1)).lower()
                text = " " + " ".join(head[:prep if prep >= 1 and len(head) - prep - 1 == k else -k]) + " "
                break
    if not out["city"] and g["rx"]:
        hits = [x for x in g["rx"].finditer(text)]
        if hits:
            h = max(hits, key=lambda x: len(x.group(1)))
            rest = text[:h.start()] + " " + text[h.end():]
            if split_words(rest)[0]: out["place"], text = g["names"][h.group(1).lower()], rest
    out["words"], out["remote"] = split_words(text)
    return out


def must_words(words, fuzzy=False, fields=FIELDS):
    """Every word must be found, in any of the fields; fuzzy forgives a typo (none in C++, C#, .NET)."""
    return [{"multi_match": {"query": w, "fields": fields, "type": "best_fields", "fuzziness": "AUTO:5,9" if fuzzy and w.isalpha() else 0,
                             "prefix_length": 1, "max_expansions": 30}} for w in words]


def rank_words(words):
    """The more of the words in the title, the higher; the whole phrase in the title first."""
    phrase = " ".join(words)
    return [{"match_phrase": {"title": {"query": phrase, "boost": 8}}}, {"match": {"title": {"query": phrase, "operator": "and", "boost": 4}}},
            {"match": {"title": {"query": phrase, "boost": 3}}}]


def query(q, remote=False, limit=20, offset=0, fuzzy=False, cap=50, facets=True):
    """The search request: every word must be found, in any field; the whole phrase in the title ranks first. "remote" in the
    words is the remote filter. fuzzy: forgive a typo (one in a word of 5-8 letters, two from 9), for the second try when the
    words as typed find nothing. facets=False leaves out the counts by field, level and company: the site's own search box
    (/api/search?all=1) does not show them, and on 25 Nov 2026 they took 2.3 to 3.5 of the 3 seconds that request is given
    ("warehouse", "software engineer": 503), against 0.3 to 0.5 s without them. Returns None when there is nothing to look for."""
    words, said_remote = split_words(q)
    if not words: return None
    filt = [{"term": {"active": True}}] + ([{"term": {"remote": True}}] if remote or said_remote else [])
    body = {"size": max(1, min(int(limit), cap)), "from": max(0, min(int(offset), 1000)), "_source": ["slug"], "track_total_hits": True,
            "query": {"bool": {"must": must_words(words, fuzzy), "filter": filt, "should": rank_words(words)}},
            "aggs": {"remote": {"filter": {"term": {"remote": True}}}, "hybrid": {"filter": {"term": {"hybrid": True}}},
                     "cat": {"terms": {"field": "cat", "size": 12}}, "level": {"terms": {"field": "level", "size": 8}},
                     "company": {"terms": {"field": "company.raw", "size": 10}}}}
    if not facets: del body["aggs"]
    return body


FEW = 10          # the words as typed find fewer jobs than this: try them forgiving typos too


def prefer_fuzzy(exact, forgiving):
    """Show the closest spelling instead of the words as typed? Yes when they find nothing, or when they find only a few and the
    forgiving search finds ten times as many (at least 20). Employers misspell too: "manger" stands in 9 postings, so "product
    manger" found 2 jobs as typed while "product manager" has thousands."""
    return exact == 0 or (exact < FEW and forgiving >= max(20, 10 * exact))


def search(q, remote=False, limit=20, offset=0, timeout=1.5, cap=50, facets=True):
    """(total, [slugs], facets) from OpenSearch: the words as typed first; when they find nothing or only a few, the same words
    forgiving typos (facets["fuzzy"] then says so, and facets["exact"] how many jobs the words as typed found). Raises OSError
    when it is not there or does not answer in time."""
    if not URL: raise OSError("HRN_OPENSEARCH is not set")
    body = query(q, remote, limit, offset, cap=cap, facets=facets)
    if body is None: return 0, [], {}
    r, fuzzy = call("POST", f"/{ALIAS}/_search", fit(body), timeout=timeout), False
    exact = r["hits"]["total"]["value"]
    if exact < FEW:
        rf = call("POST", f"/{ALIAS}/_search", fit(query(q, remote, limit, offset, fuzzy=True, cap=cap, facets=facets)), timeout=timeout)
        if prefer_fuzzy(exact, rf["hits"]["total"]["value"]): r, fuzzy = rf, True
    a = r.get("aggregations", {})
    facets = {"fuzzy": fuzzy, "exact": exact if fuzzy else r["hits"]["total"]["value"], "remote": a.get("remote", {}).get("doc_count", 0), "hybrid": a.get("hybrid", {}).get("doc_count", 0)}
    for k in ("cat", "level", "company"):
        facets[k] = [[b["key"], b["doc_count"]] for b in a.get(k, {}).get("buckets", []) if b["key"]]
    return r["hits"]["total"]["value"], [h["_source"]["slug"] for h in r["hits"]["hits"]], facets


# ---- The list of the search page (/api/search?list=1): the words and every filter of /jobs/, answered here -------------------------
# Until 25 Nov 2026 the page downloaded every open job (data/index.json: 22 MB compressed, 100 MB of JSON, 450 MB of a browser's memory)
# and filtered in the browser; a phone took seconds or closed the tab. Now the page sends its address and gets 50 rows back.
LEVELS = ("Intern", "Junior", "Senior", "Lead")
SORTS = ("new", "rel", "sal")
PAGE, DEEPEST = 50, 10000            # rows in one answer; OpenSearch pages no deeper than its max_result_window
BOOLS = ("ti", "nosal", "real", "remote", "hybrid", "entry", "crypto", "any",
         "np", "onsite", "count", "sum")       # the rest are for the site's other lists (assets/site.js): no talent pools, not remote, only
                                               # the number, and a summary of the matches (how many remote, state pay, are new, who hires most)
# what "Nothing fits all of that" offers to drop, one at a time, with the number of jobs left without it
RELAX = ("q", "cat", "lvl", "loc", "city", "sal", "age", "perk", "etype", "remote", "hybrid", "xl", "entry", "crypto", "any", "real", "skills")
SRC = ["slug", "title", "company", "place", "remote", "hybrid", "featured", "crypto", "anywhere", "pool", "urgent", "cat", "level", "tags",
       "salary", "posted", "pay_hi", "places", "perks", "etype", "t", "cc"]
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,199}")
NEWEST = [{"premium": "desc"}, {"rot": "asc"}, {"pinned": "desc"}, {"featured": "desc"}, {"ts": "desc"}, {"slug": "asc"}]   # build.order()
WEEK = 7 * 86400


def params(qs):
    """The list's parameters from a parsed query string ({name: [values]}, as urllib.parse.parse_qs gives it), checked and written one
    way, so the same search asked in another order or case is one answer and one entry in a cache. The names are the page's own
    (assets/app.js, query()), plus xc and xw (companies and title words the visitor hid; repeated), offset, limit and ids."""
    one = lambda k: ((qs.get(k) or [""])[0] or "").strip()
    num = lambda k: int(one(k)) if one(k).isdigit() and len(one(k)) < 9 else 0
    listed = lambda k, n, size: sorted({x.strip() for x in one(k).split(",") if x.strip() and len(x.strip()) <= size})[:n]
    repeated = lambda k, n, size: sorted({x.strip() for x in qs.get(k) or [] if x.strip() and len(x.strip()) <= size})[:n]
    p = {"q": " ".join(one("q").lower().split())[:200]}
    for b in BOOLS: p[b] = one(b).lower() not in ("", "0", "false")
    p["cat"] = listed("cat", 20, 60)
    p["lvl"] = one("lvl") if one("lvl") in LEVELS + ("Exec",) else ""
    p["loc"] = one("loc").lower() if SLUG.fullmatch(one("loc").lower()) else ""
    p["city"] = " ".join(one("city").lower().split())[:60]
    p["rc"] = one("rc").upper() if re.fullmatch(r"[A-Za-z]{2}", one("rc")) else ""
    sal = num("sal"); p["sal"] = 1 if sal == 1 else sal if 1000 <= sal <= 10_000_000 else 0
    p["age"] = min(num("age"), 3650)
    p["xl"] = [x for x in listed("xl", 4, 10) if x in LEVELS]
    p["perk"], p["etype"] = one("perk")[:60], one("etype")[:30]
    p["skills"] = listed("skills", 10, 60)
    p["xc"], p["xw"] = repeated("xc", 50, 120), sorted({w.lower() for w in repeated("xw", 20, 60)})
    p["sort"] = one("sort") if one("sort") in SORTS else "new"
    p["offset"] = min(num("offset"), DEEPEST - 1)
    # from + size must stay within OpenSearch's max_result_window: rows 9,990 to 10,039 used to fail the whole request (503), now the
    # last page ends at row 10,000 (26 Nov 2026)
    p["limit"] = max(1, min(num("limit") or PAGE, PAGE, DEEPEST - p["offset"]))
    p["ids"] = [s for s in listed("ids", 60, 200) if SLUG.fullmatch(s)]
    p["sk"] = listed("sk", 30, 60)                                   # any of these skills (For you), where skills= needs all of them
    p["co"] = one("co")[:120]                                        # one company, by its name as written (companies followed)
    after = num("after"); p["after"] = after if 20000101 <= after <= 30001231 else 0     # posted after this day, yyyymmdd (saved searches)
    return p


def too_deep(qs):
    """Does the list ask for rows the engine cannot list (offset DEEPEST or beyond)? serve.py answers it 400 with what to do, where it
    used to pass it on and answer 503 "search engine unavailable" for OpenSearch's refusal (26 Nov 2026: page 201 of a common search)."""
    v = ((qs.get("offset") or [""])[0] or "").strip()
    return v.isdigit() and int(v) >= DEEPEST


REGION_LANDS = {"europe": {"GB", "DE", "FR", "IE", "NL", "ES", "PT", "PL", "SE", "CH", "AT", "IT", "DK", "NO", "FI", "BE", "CZ", "RO", "UA", "EE", "LT", "GR", "BG", "HU", "RS",
                           "LV", "CY", "ME", "MD"},
                "asia-pacific": {"IN", "SG", "HK", "JP", "KR", "TW", "CN", "AU", "NZ", "MY", "PH", "ID", "TH", "VN", "PK", "BD"},
                "latin-america": {"BR", "MX", "AR", "CO", "CL", "CR", "PR"}, "africa": {"ZA", "NG", "KE", "EG"}}     # build.REGIONS, read without the build


def list_filters(p, today, drop="", said_remote=False, read=None):
    """(filter, must_not) clauses for the page's filters, without the one named drop. The same tests as match() in assets/site.js.
    read: what the words say besides the words (read_query): a place, a city with its state, the hours, entry level."""
    f, no = [{"term": {"active": True}}], []
    on = lambda k: k != drop and p.get(k)
    read = read or {}
    if on("cat"): f.append({"terms": {"cat": p["cat"]}})
    if on("lvl"): f.append({"term": {"exec": True}} if p["lvl"] == "Exec" else {"term": {"level": p["lvl"]}})
    if on("loc"): f.append({"term": {"places": p["loc"]}})
    elif read.get("place") and drop != "q": f.append({"term": {"places": read["place"]}})
    if on("city"): f.append(city_clause(p["city"]))                          # a city typed by the visitor, in the posting's own place line, in its own state
    elif read.get("city") and drop != "q": f.append(city_clause(read["city"]))
    if p.get("rc"):                                                          # remote, but only for other countries
        no.append({"bool": {"filter": [{"term": {"remote": True}}, {"exists": {"field": "cc"}}],
                            "must_not": [{"term": {"anywhere": True}}, {"term": {"cc": p["rc"]}}]}})
        # and remote for a part of the world the country is not in ("Latin America", "EMEA", "APAC"), with no country of its own named
        # (teardown, 26 Nov 2026: with rc=US the list still began with Dhaka, Costa Rica and Latin America)
        far = sorted(r for r, lands in REGION_LANDS.items() if p["rc"] not in lands)
        if far: no.append({"bool": {"filter": [{"term": {"remote": True}}, {"terms": {"places": far}}],
                                    "must_not": [{"term": {"anywhere": True}}, {"term": {"cc": p["rc"]}}]}})
    remote = drop != "remote" and (p.get("remote") or said_remote)
    if remote or on("hybrid"):                                               # both ticked: either kind
        f.append({"bool": {"should": ([{"term": {"remote": True}}] if remote else []) + ([{"term": {"hybrid": True}}] if on("hybrid") else []),
                           "minimum_should_match": 1}})
    if on("xl"): no.append({"terms": {"level": p["xl"]}})
    if on("entry") or (read.get("entry") and drop not in ("q", "entry")): f.append({"terms": {"level": ["Intern", "Junior"]}})
    if on("crypto"): f.append({"term": {"crypto": True}})
    if on("any"): f += [{"term": {"anywhere": True}}, {"term": {"remote": True}}]
    if on("perk"): f.append({"term": {"perks": p["perk"]}})
    if on("etype"): f.append({"term": {"etype": p["etype"]}})
    elif read.get("etype") and drop not in ("q", "etype"): f.append({"term": {"etype": read["etype"]}})
    if on("age"): f.append({"range": {"posted": {"gte": (today - datetime.timedelta(days=p["age"])).isoformat()}}})
    if on("real"):                                                           # fresh openings only: no talent pools, nothing open 90+ days
        f.append({"range": {"posted": {"gte": (today - datetime.timedelta(days=90)).isoformat()}}}); no.append({"term": {"pool": True}})
    if on("sal"):
        if p["sal"] == 1: f.append({"term": {"has_pay": True}})
        else:
            pay = {"range": {"pay_hi": {"gte": p["sal"]}}}                  # "also show jobs that do not state pay" lets the unknowns through
            f.append({"bool": {"should": [pay, {"bool": {"must_not": [{"term": {"has_pay": True}}]}}], "minimum_should_match": 1}} if p.get("nosal") else pay)
    if drop != "skills": f += [{"term": {"tags.raw": s}} for s in p.get("skills") or []]
    if p.get("sk"): f.append({"terms": {"tags.raw": p["sk"]}})
    if p.get("np"): no.append({"term": {"pool": True}})
    if p.get("onsite"): no.append({"term": {"remote": True}})
    if p.get("co"): f.append({"term": {"company.raw": p["co"]}})
    if p.get("after"):
        a = str(p["after"]); f.append({"range": {"posted": {"gt": f"{a[:4]}-{a[4:6]}-{a[6:]}"}}})
    if p.get("xc"): no.append({"terms": {"company.raw": p["xc"]}})
    no += [{"match_phrase": {"title": w}} for w in p.get("xw") or []]
    if p.get("ids"): f.append({"terms": {"slug": p["ids"]}})
    return f, no


TIER = 100            # "Best match": every word in the title or the skills counts this much more than any other match
FRESH = [{"weight": 0.3}, {"exp": {"posted": {"origin": "", "scale": "30d", "offset": "7d", "decay": 0.5}}, "weight": 0.7}]


def in_title(words, fuzzy=False):
    """Every word in the title or the skills: a job about the words, not one whose text mentions them."""
    return {"bool": {"must": must_words(words, fuzzy, ["title^2", "tags"])}}


def list_body(p, today, fuzzy=False, drop="", count=False):
    """The request for one page of the list (count=True: only how many jobs match).
    With words typed (data teardown, 26 Nov 2026), every order lists first the jobs that have every word in the title or the skills:
    "Newest first" for "customer support" began with a Partner Development Manager whose text named the words once. "Best match" ranks
    them first too, and a posting's age counts: a match loses half its weight by 37 days, and keeps at least 30% (postings 90 days old
    and more are already left out by default, real=1)."""
    read = read_query(p["q"]) if drop != "q" else {"words": [], "remote": False}
    words, said_remote = read["words"], read["remote"]
    f, no = list_filters(p, today, drop, said_remote, read)
    q = {"bool": {"filter": f}}
    if no: q["bool"]["must_not"] = no
    fields = ["title"] if p.get("ti") else FIELDS
    if words and p["sort"] == "rel" and not (count or p.get("count") or p.get("ids")):
        q["bool"].update(must=must_words(words, fuzzy, fields), should=rank_words(words) + [{"constant_score": {"filter": in_title(words, fuzzy), "boost": TIER}}])
        fresh = json.loads(json.dumps(FRESH)); fresh[1]["exp"]["posted"]["origin"] = today.isoformat()
        q = {"function_score": {"query": q, "functions": fresh, "score_mode": "sum", "boost_mode": "multiply"}}
    elif words and not (count or p.get("count") or p.get("ids")):
        # the words are a filter; the score is 1 for a job with every word in its title or skills and 0 for the rest
        q["bool"]["filter"] = f + must_words(words, fuzzy, fields)
        q["bool"]["should"] = [{"constant_score": {"filter": in_title(words, fuzzy), "boost": 1}}]
    elif words:
        q["bool"].update(must=must_words(words, fuzzy, fields), should=rank_words(words))
    if count or p.get("count"): return {"size": 0, "track_total_hits": True, "query": q}
    if p.get("ids"): return {"size": len(p["ids"]), "_source": SRC, "query": q}
    sort = (["_score", {"ts": "desc"}, {"slug": "asc"}] if p["sort"] == "rel" and words else
            ["_score", {"pay_hi": {"order": "desc", "missing": "_last"}}] + NEWEST if p["sort"] == "sal" and words else
            [{"pay_hi": {"order": "desc", "missing": "_last"}}] + NEWEST if p["sort"] == "sal" else
            NEWEST[:4] + ["_score"] + NEWEST[4:] if words else NEWEST)
    body = {"size": p["limit"], "from": p["offset"], "_source": SRC, "track_total_hits": True, "query": q, "sort": sort,
            "collapse": {"field": "ckey", "inner_hits": {"name": "same", "size": 0}}}     # one row per role, "+N more locations"
    if p.get("sum") and not p["offset"]:
        body["aggs"] = {"remote": {"filter": {"term": {"remote": True}}}, "pay": {"filter": {"term": {"has_pay": True}}},
                        "fresh": {"filter": {"range": {"posted": {"gte": (today - datetime.timedelta(days=7)).isoformat()}}}},
                        "top": {"terms": {"field": "company.raw", "size": 3}}}
    return body


def msearch(bodies, timeout):
    """Several requests in one round trip; their answers in the same order."""
    out = call("POST", f"/{ALIAS}/_msearch", "".join("{}\n" + json.dumps(fit(b)) + "\n" for b in bodies), timeout=timeout, ndjson=True)["responses"]
    for x in out:
        if "error" in x: raise OSError(f"OpenSearch msearch: {str(x['error'])[:300]}")
    return out


def listing(p, today=None, timeout=2.5):
    """One page of the list: {"total": jobs that match (each posting counted), "hits": [(_source, other postings of the same role)],
    "fuzzy", "exact", "without": {filter: jobs that match without it} when nothing matches, "more": whether a next page exists}.
    Raises OSError when OpenSearch is not there or does not answer in time."""
    if not URL: raise OSError("HRN_OPENSEARCH is not set")
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    r = call("POST", f"/{ALIAS}/_search", fit(list_body(p, today)), timeout=timeout)
    total, fuzzy, exact, without = r["hits"]["total"]["value"], False, 0, {}
    if p["count"]: return {"total": total, "hits": [], "fuzzy": False, "exact": 0, "without": {}, "more": False}
    words = read_query(p["q"])["words"]
    if words and total < FEW and not p["ids"]:
        # Few or none: is it a typo? Decided on the words alone, as the search box always did ("cashier" in Boise is not a typo when
        # thousands of jobs say cashier elsewhere); the list forgiving typos comes in the same round trip.
        alone = params({"q": [p["q"]], "ti": ["1" if p["ti"] else ""]})
        a, b, rf = msearch([list_body(alone, today, count=True), list_body(alone, today, fuzzy=True, count=True), list_body(p, today, fuzzy=True)], timeout)
        if prefer_fuzzy(a["hits"]["total"]["value"], b["hits"]["total"]["value"]) and rf["hits"]["total"]["value"] > total:
            r, fuzzy, exact = rf, True, a["hits"]["total"]["value"]
            total = r["hits"]["total"]["value"]
    if total == 0 and not p["ids"]:
        keys = [k for k in RELAX if p.get(k) or (k == "remote" and read_query(p["q"])["remote"])]
        if keys:
            got = msearch([list_body(p, today, drop=k, count=True) for k in keys], timeout)
            without = {k: x["hits"]["total"]["value"] for k, x in zip(keys, got) if x["hits"]["total"]["value"]}
    hits = [(h["_source"], max(0, ((h.get("inner_hits") or {}).get("same", {}).get("hits", {}).get("total") or {}).get("value", 1) - 1)) for h in r["hits"]["hits"]]
    out = {"total": total, "hits": hits, "fuzzy": fuzzy, "exact": exact, "without": without,
           "more": not p["ids"] and len(hits) == p["limit"] and p["offset"] + p["limit"] < DEEPEST}
    a = r.get("aggregations")
    if a and all(k_ in a for k_ in ("remote", "pay", "fresh", "top")): out["sum"] = {"remote": a["remote"]["doc_count"], "pay": a["pay"]["doc_count"], "fresh": a["fresh"]["doc_count"],
                        "top": [[b["key"], b["doc_count"]] for b in a["top"]["buckets"]]}
    return out


def row(src, extra=0, logo=False, now=None):
    """One row of results as the page reads it (fromApi() in assets/site.js): [slug, title, company, place, flags, field, level, skills,
    pay as written, posted yyyymmdd, top of the pay range in USD, place slugs, perks, type of work, the exact posting time in minutes
    (only in its first week, else 0), country codes, has a logo, other postings of the same role]. flags as in data/index.json:
    1 remote, 2 featured, 4 crypto, 8 anywhere, 16 talent pool, 32 hybrid, 64 urgently hiring."""
    b = lambda k: int(bool(src.get(k)))
    t, now = int(src.get("t") or 0), now or int(time.time())
    posted = (src.get("posted") or "")[:10].replace("-", "")
    return [src["slug"], src.get("title") or "", src.get("company") or "", src.get("place") or "",
            b("remote") | 2 * b("featured") | 4 * b("crypto") | 8 * b("anywhere") | 16 * b("pool") | 32 * b("hybrid") | 64 * b("urgent"),
            src.get("cat") or "", src.get("level") or "", list(src.get("tags") or [])[:8], src.get("salary") or "",
            int(posted) if posted.isdigit() else 0, int(src.get("pay_hi") or 0), list(src.get("places") or []), list(src.get("perks") or []),
            src.get("etype") or "", t // 60 if t and now - t < WEEK else 0, list(src.get("cc") or [])[:3], int(bool(logo)), int(extra)]


_READY = {"at": -1e9, "ok": False, "v": 0, "fields": None}


def ready():
    """Is there an index to answer the list? Asked of OpenSearch at most once a minute.
    27 Nov 2026: a look that fails or takes over 2 seconds (OpenSearch loading the next index after an upload, this program busy) keeps the
    last answer and is tried again in 10 seconds. Until then one slow look turned every list into a 503 "search is being reloaded" for a
    whole minute, again and again (26 Nov 2026, 07:00-07:25 UTC, with no index being loaded at all). And an index of an older version
    (_meta.v) answers too, with the filters it has (fit), for the few minutes until the load that follows the upload replaces it
    (25 Nov 2026: 6.5 minutes of 503 after the version changed)."""
    now = time.monotonic()
    if now - _READY["at"] < 60: return _READY["ok"]
    try:
        m = call("GET", f"/{ALIAS}/_mapping", timeout=2.0)
    except (OSError, ValueError):
        _READY["at"] = now - 50
        return _READY["ok"]
    v, fields = 0, set()
    for x in (m or {}).values():
        mp = x.get("mappings") or {}
        v = max(v, int((mp.get("_meta") or {}).get("v", 0) or 0))
        for k, d in (mp.get("properties") or {}).items():
            fields.add(k); fields.update(f"{k}.{sub}" for sub in ((d or {}).get("fields") or {}))
    _READY.update(at=now, ok=bool(m), v=v, fields=None if v >= VERSION else fields)
    return _READY["ok"]


LEAF = ("term", "terms", "range", "match", "match_phrase", "match_phrase_prefix", "prefix", "wildcard", "fuzzy")


def _fields(x):
    """Every field a part of a request names (a clause, an aggregation, a function)."""
    out = set()
    if isinstance(x, dict):
        for k, v in x.items():
            if k in LEAF and isinstance(v, dict): out.update(f for f in v if f != "boost")
            elif k == "field" and isinstance(v, str): out.add(v)
            elif k == "fields" and isinstance(v, list): out.update(str(f).split("^")[0] for f in v)
            elif k in ("exp", "gauss", "linear") and isinstance(v, dict): out.update(v)
            else: out |= _fields(v)
    elif isinstance(x, list):
        for v in x: out |= _fields(v)
    return out


def _fit(c, known, neg=False):
    """One clause for an older index: itself, a narrower copy, or None to leave it out. A clause on a field the index lacks is left out
    where it filters (the filter is not applied, rather than matching nothing); inside a must_not a bool that would lose one of its
    conditions is left out whole, so an exclusion never grows."""
    if not isinstance(c, dict) or len(c) != 1: return c
    (k, v), = c.items()
    if k in LEAF or k == "exists": return c if all(known(f) for f in _fields(c)) else None
    if k == "multi_match":
        if not v.get("fields"): return c
        fs = [f for f in v["fields"] if known(str(f).split("^")[0])]
        return {k: {**v, "fields": fs}} if fs else None
    if k == "constant_score":
        inner = _fit(v.get("filter"), known, neg)
        return None if inner is None else {k: {**v, "filter": inner}}
    if k == "function_score":
        q = _fit(v.get("query") or {"match_all": {}}, known, neg)
        if q is None: return None
        fns = [fn for fn in v.get("functions") or [] if all(known(f) for f in _fields(fn))]
        return {k: {**v, "query": q, "functions": fns}} if fns else q
    if k == "bool":
        out, lost_should = {}, False
        for part, xs in v.items():
            if part not in ("filter", "must", "should", "must_not"): out[part] = xs; continue
            xs = xs if isinstance(xs, list) else [xs]
            got = [_fit(x, known, not neg if part == "must_not" else neg) for x in xs]
            kept = [x for x in got if x is not None]
            if neg and part in ("filter", "must", "must_not") and len(kept) < len(got): return None
            if part == "should" and xs and not kept: lost_should = True
            if kept: out[part] = kept
        if lost_should:
            if neg and int(v.get("minimum_should_match", 0) or 0) >= 1: return None
            out.pop("minimum_should_match", None)
        return {"bool": out}
    return c


def fit(body):
    """The request as an index of an older version can answer it (ready() keeps the fields of that index); unchanged for an index of the
    current version. Clauses, sorts, collapse and counts on fields the index does not have are left out."""
    fields = _READY.get("fields")
    if not fields or not isinstance(body, dict): return body
    known = lambda f: f in fields or f.startswith("_")
    out = dict(body)
    if "query" in out: out["query"] = _fit(out["query"], known) or {"match_all": {}}
    if "sort" in out:
        out["sort"] = [x for x in out["sort"] if isinstance(x, str) or all(known(f) for f in x)]
        if not out["sort"]: del out["sort"]
    if "collapse" in out and not known(out["collapse"].get("field", "")): del out["collapse"]
    if "aggs" in out and not all(known(f) for f in _fields(out["aggs"])): del out["aggs"]
    return out


def _test():
    assert query("") is None and query("jobs in the") is None
    b = query("Senior pyhton remote", limit=5)
    assert b["size"] == 5 and {"term": {"remote": True}} in b["query"]["bool"]["filter"]
    assert [m["multi_match"]["query"] for m in b["query"]["bool"]["must"]] == ["Senior", "pyhton"]
    assert b["query"]["bool"]["must"][1]["multi_match"]["fuzziness"] == 0
    assert query("Senior pyhton", fuzzy=True)["query"]["bool"]["must"][1]["multi_match"]["fuzziness"] == "AUTO:5,9"
    c = query("c++ developer")
    assert c["query"]["bool"]["must"][0]["multi_match"]["query"] == "c++" and c["query"]["bool"]["must"][0]["multi_match"]["fuzziness"] == 0
    assert query(".NET engineer")["query"]["bool"]["must"][0]["multi_match"]["query"].lower() == ".net"
    assert query("c++", fuzzy=True)["query"]["bool"]["must"][0]["multi_match"]["fuzziness"] == 0      # no typo forgiven in C++, C#, .NET
    assert "aggs" in query("nurse") and "aggs" not in query("nurse", facets=False)          # the site's search box asks without the counts
    d = doc({"slug": "a", "active": True, "title": "T", "usd": [100, 200], "tags": ["Go"], "posted": "2026-11-01"}, "<p>Build &amp; ship</p>")
    assert d["pay_mid"] == 150 and d["body"].strip() == "Build & ship" and d["posted"] == "2026-11-01"
    assert prefer_fuzzy(0, 0) and prefer_fuzzy(2, 6246) and prefer_fuzzy(1, 20)
    assert not prefer_fuzzy(2, 19) and not prefer_fuzzy(9, 89) and not prefer_fuzzy(10, 5000) and not prefer_fuzzy(34, 900)
    # the list of the search page
    from urllib.parse import parse_qs
    P = lambda s: params(parse_qs(s))
    a, b2 = P("q=Nurse%20%20RN&loc=texas&remote=1&sort=rel"), P("sort=rel&remote=1&loc=Texas&q=nurse+rn")
    assert a == b2 and a["q"] == "nurse rn" and a["remote"] and not a["hybrid"] and a["offset"] == 0 and a["limit"] == PAGE   # one search, one key
    assert P("remote=0")["remote"] is False and P("lvl=Boss")["lvl"] == "" and P("loc=../x")["loc"] == "" and P("sal=500")["sal"] == 0
    assert P("sal=1")["sal"] == 1 and P("sal=150000")["sal"] == 150000 and P("offset=99999")["offset"] == DEEPEST - 1 and P("limit=500")["limit"] == PAGE
    # never past the engine's window (max_result_window = DEEPEST): the last page is cut short, rows from DEEPEST on are refused (400)
    assert P("offset=9950")["limit"] == PAGE and P("offset=9990")["limit"] == 10 and P("offset=99999")["limit"] == 1 and P("offset=9990&limit=5")["limit"] == 5
    for o in ("0", "50", "9950", "9951", "9990", "9999", "10000", "99999", "123456789"):
        b_ = list_body(P("q=nurse&offset=" + o), datetime.date(2026, 11, 25))
        assert b_["from"] + b_["size"] <= DEEPEST, o
    assert not too_deep(parse_qs("offset=9950")) and not too_deep(parse_qs("offset=9999")) and not too_deep(parse_qs("q=nurse")) and not too_deep(parse_qs("offset=x"))
    assert too_deep(parse_qs("offset=10000")) and too_deep(parse_qs("q=nurse&offset=12345")) and too_deep(parse_qs("offset=123456789"))
    assert P("xc=Acme%2C%20Inc.&xc=Zeta")["xc"] == ["Acme, Inc.", "Zeta"] and P("skills=Python,Go")["skills"] == ["Go", "Python"]
    assert P("ids=c,BAD!,a-b")["ids"] == ["a-b", "c"] and P("rc=us")["rc"] == "US" and P("xl=Senior,Nope")["xl"] == ["Senior"]
    day = datetime.date(2026, 11, 25)
    flat = lambda body: json.dumps(body)
    f, no = list_filters(P("cat=sales&lvl=Exec&loc=texas&age=7&sal=150000&nosal=1&skills=Go&xc=Acme&xw=senior&real=1"), day)
    s_ = flat(f)
    for want in ('{"terms": {"cat": ["sales"]}}', '{"term": {"exec": true}}', '{"term": {"places": "texas"}}', '"gte": "2026-11-18"',
                 '"gte": "2026-08-27"', '{"range": {"pay_hi": {"gte": 150000}}}', '{"term": {"tags.raw": "Go"}}'):
        assert want in s_, want
    assert '{"terms": {"company.raw": ["Acme"]}}' in flat(no) and '{"match_phrase": {"title": "senior"}}' in flat(no) and '{"term": {"pool": true}}' in flat(no)
    f, no = list_filters(P("remote=1&hybrid=1&rc=DE&entry=1&any=1"), day)
    assert '"minimum_should_match": 1' in flat(f) and '{"terms": {"level": ["Intern", "Junior"]}}' in flat(f) and '{"term": {"cc": "DE"}}' in flat(no)
    f, _ = list_filters(P("loc=texas&remote=1"), day, drop="loc")
    assert "texas" not in flat(f) and '"remote": true' in flat(f)
    body = list_body(P("q=python+remote&sort=rel"), day)
    assert body["sort"][0] == "_score" and body["collapse"]["field"] == "ckey" and '"remote": true' in flat(body["query"])
    assert [m["multi_match"]["query"] for m in body["query"]["function_score"]["query"]["bool"]["must"]] == ["python"]
    assert list_body(P("q=python&ti=1&sort=rel"), day)["query"]["function_score"]["query"]["bool"]["must"][0]["multi_match"]["fields"] == ["title"]
    assert any(m.get("multi_match", {}).get("fields") == ["title"] for m in list_body(P("q=python&ti=1"), day)["query"]["bool"]["filter"])
    assert list_body(P("sort=rel"), day)["sort"] == NEWEST and list_body(P("sort=sal"), day)["sort"][0]["pay_hi"]["order"] == "desc"
    assert list_body(P("loc=texas"), day, count=True)["size"] == 0 and "collapse" not in list_body(P("ids=a"), day)
    assert "texas" not in flat(list_body(P("loc=texas&q=nurse"), day, drop="loc")) and "nurse" not in flat(list_body(P("loc=texas&q=nurse"), day, drop="q"))
    d = doc({"slug": "nurse-acme", "active": True, "title": "Director of Nursing", "company": "Acme", "location": "Austin, TX", "remote": True,
             "usd": [90000, 120000], "salary": "$90K - $120K", "tags": ["Care"], "posted": "2026-11-20", "places": ["texas", "united-states"],
             "perks": ["Relocation support"], "etype": "Full-time", "t": 1795000000, "ts": 1795000000, "bump": 0, "urgent": True, "premium": True},
            "", {"texas": "US", "united-states": "US"}, "2026-11-25")
    assert d["exec"] and d["cc"] == ["US"] and d["pay_hi"] == 120000 and d["has_pay"] and d["ckey"] == "Acme" + SEP + "director of nursing" and len(d["rot"]) == 32
    assert doc({"slug": "x", "title": "Engineer", "posted": "2026-11-20", "ts": 0}, "")["ts"] == day_start("2026-11-20") > 0
    r = row(d, 2, True, now=1795000000 + 3600)
    assert r[:4] == ["nurse-acme", "Director of Nursing", "Acme", "Austin, TX"] and r[4] == 1 | 64 and r[9] == 20261120 and r[10] == 120000
    assert r[14] == 1795000000 // 60 and r[15] == ["US"] and r[16] == 1 and r[17] == 2
    assert row(d, now=1795000000 + 8 * 86400)[14] == 0              # an exact time only in the posting's first week
    f, no = list_filters(P("np=1&onsite=1&sk=Go,Rust&co=Acme&after=20261120"), day)
    assert '{"terms": {"tags.raw": ["Go", "Rust"]}}' in flat(f) and '{"term": {"company.raw": "Acme"}}' in flat(f) and '"gt": "2026-11-20"' in flat(f)
    assert '{"term": {"pool": true}}' in flat(no) and '{"term": {"remote": true}}' in flat(no) and P("after=123")["after"] == 0
    assert list_body(P("count=1&loc=texas"), day)["size"] == 0 and "aggs" in list_body(P("sum=1"), day) and "aggs" not in list_body(P("sum=1&offset=50"), day)
    # ---- the data teardown of 26 Nov 2026, one check per fix ----
    # an hourly rate counts as pay and passes the pay filter at 2,080 hours a year ("$20/h+" is sal=41600)
    h = doc({"slug": "w", "active": True, "title": "Warehouse Associate", "salary": "$20 - $23 an hour", "usd_h": [20, 23], "posted": "2026-11-20"}, "")
    assert h["has_pay"] and h["pay_hi"] == 23 * HOURS and h["pay_mid"] == 21.5 * HOURS
    assert doc({"slug": "w", "active": True, "title": "T", "salary": "$90K - $120K", "usd": [90000, 120000], "usd_h": [1, 2]}, "")["pay_hi"] == 120000
    assert P("sal=41600")["sal"] == 41600 and '{"range": {"pay_hi": {"gte": 31200}}}' in flat(list_filters(P("sal=31200"), day)[0])
    # one row per role: the store, mall, cinema or town at the end of a title is not the role
    for t_, pl_, k_ in (("Seasonal Key Holder - Oak Park Mall", "Overland Park, KS", "seasonal key holder"), ("Seasonal Sales Associate - The Mall at Robinson", "", "seasonal sales associate"),
                        ("Crew Member(Country Club Cinema)", "", "crew member"), ("Sales Associate - Dedham, MA", "Dedham, MA", "sales associate"),
                        ("Part-Time Assistant Manager - Level 2 - Dimond Center", "", "part time assistant manager level 2"), ("Software Engineer - Backend", "", "software engineer backend"),
                        ("Software Engineer, Backend", "", "software engineer backend"), ("Nurse - ICU", "", "nurse icu"), ("Maintenance Technician (Atlanta, GA)", "Atlanta, Georgia", "maintenance technician")):
        assert role_key(t_, pl_) == k_, (t_, role_key(t_, pl_))
    assert doc({"slug": "b", "title": "Seasonal Key Holder - Concord Mills", "company": "Boxlunch"}, "")["ckey"] == doc({"slug": "c", "title": "Seasonal Key Holder", "company": "Boxlunch"}, "")["ckey"]
    if geo()["names"]:                     # the places come from build.py; without it the words stay words (checked below)
        # a place in the words is a filter, not two words ("New" matched "New Grad"); "entry level" and "part time" are filters too
        r_ = read_query("software engineer new york")
        assert r_["words"] == ["software", "engineer"] and r_["place"] == "new-york", r_
        assert read_query("nurse dallas tx")["city"] == "dallas, tx" and read_query("nurse dallas tx")["words"] == ["nurse"]
        assert read_query("nurse in albany ny")["city"] == "albany, ny" and read_query("data analyst in london")["place"] == "london"
        assert read_query("part time cashier") == {"place": "", "city": "", "etype": "Part-time", "entry": False, "words": ["cashier"], "remote": False}
        assert read_query("entry level marketing")["entry"] and read_query("entry level marketing")["words"] == ["marketing"]
        assert read_query("new york")["words"] == ["new", "york"] and not read_query("new york")["place"]     # a place alone is still searched as words
        assert read_query("warehouse new mexico")["place"] == "" and read_query("python developer uk")["place"] == "united-kingdom"
        b_ = flat(list_body(P("q=software+engineer+new+york&sort=rel"), day))
        assert '{"term": {"places": "new-york"}}' in b_ and '"query": "new"' not in b_ and '"query": "york"' not in b_
        assert '{"term": {"etype": "Part-time"}}' in flat(list_body(P("q=part+time+cashier"), day)) and '"query": "time"' not in flat(list_body(P("q=part+time+cashier"), day))
        assert '{"term": {"etype": "Part-time"}}' not in flat(list_body(P("q=part+time+cashier"), day, drop="q"))
        # a typed city agrees with its state: "Dallas, TX" is the Dallas page (never Dallas, Oregon), "Albany, NY" needs New York
        assert city_clause("Dallas, TX") == city_clause("dallas tx") == city_clause("Dallas") == {"term": {"places": "dallas"}}
        # the metro areas: "nurse dallas" and "nurse dfw" are the Dallas list (with Irving, Frisco, Arlington), a suburb keeps its own words
        assert read_query("nurse dallas")["place"] == read_query("nurse dfw")["place"] == read_query("nurse in dallas-fort worth")["place"] == "dallas"
        assert read_query("nurse twin cities")["place"] == read_query("nurse st. paul")["place"] == "minneapolis" and read_query("rn philadelphia")["place"] == "philadelphia"
        assert read_query("teacher san antonio")["place"] == "san-antonio" and read_query("engineer detroit")["place"] == "detroit"
        assert city_clause("San Antonio, TX") == {"term": {"places": "san-antonio"}} and "irving" in flat(city_clause("Irving, TX"))
        a_ = flat(city_clause("Albany, NY"))
        assert '"match_phrase": {"place": "albany"}' in a_ and '{"match": {"place": "ny"}}' in a_ and '"new york"' in a_ and '"minimum_should_match": 1' in a_
        assert flat(city_clause("Portland, ME")).count("maine") == 1 and city_clause("Leeds") == {"match_phrase": {"place": "leeds"}}
        assert '{"term": {"places": "dallas"}}' in flat(list_filters(P("city=Dallas%2C%20TX"), day)[0])
    else:
        assert read_query("software engineer new york")["words"] == ["software", "engineer", "new", "york"]
    # "Best match": every word in the title or the skills first, and freshness weighs
    rb = list_body(P("q=customer+support&sort=rel"), day)["query"]["function_score"]
    assert rb["boost_mode"] == "multiply" and rb["functions"][1]["exp"]["posted"]["origin"] == "2026-11-25" and rb["functions"][0] == {"weight": 0.3}
    assert any(c.get("constant_score", {}).get("boost") == TIER for c in rb["query"]["bool"]["should"])
    # "Newest first" with words: the jobs with the words in the title or the skills come first, then the newest
    nb = list_body(P("q=customer+support"), day)
    assert nb["sort"][:5] == NEWEST[:4] + ["_score"] and nb["query"]["bool"]["should"][0]["constant_score"]["boost"] == 1
    assert [m["multi_match"]["fields"] for m in nb["query"]["bool"]["should"][0]["constant_score"]["filter"]["bool"]["must"]] == [["title^2", "tags"]] * 2
    assert "must" not in nb["query"]["bool"] and list_body(P("q=customer+support&sort=sal"), day)["sort"][0] == "_score"
    assert list_body(P("sort=new"), day)["sort"] == NEWEST and list_body(P("q=nurse"), day, count=True)["size"] == 0
    # remote open to my country: not the remote jobs of another part of the world either (Latin America, EMEA, APAC)
    f, no = list_filters(P("remote=1&rc=US"), day)
    assert '{"terms": {"places": ["africa", "asia-pacific", "europe", "latin-america"]}}' in flat(no)
    f, no = list_filters(P("remote=1&rc=DE"), day)
    assert '"europe"' not in flat(no) and '"latin-america"' in flat(no)
    # an index of an older version (fit): clauses on fields it lacks are left out, an exclusion never grows, the rest is unchanged
    v1 = {k for k in SETTINGS["mappings"]["properties"] if k not in ("cc", "ckey", "etype", "perks", "hybrid")} | {"company.raw", "tags.raw"}
    _READY["fields"] = None
    full = list_body(P("q=nurse&loc=texas&remote=1&rc=DE&etype=Part-time&hybrid=1&sum=1"), day)
    assert fit(full) == full                                      # the current version: untouched
    _READY["fields"] = v1
    try:
        got = fit(full)
        fq = got["query"]["bool"] if "bool" in got["query"] else got["query"]["function_score"]["query"]["bool"]
        assert "collapse" not in got and "aggs" not in got and not {"cc", "etype", "hybrid"} & _fields(got["query"]) and got["_source"] == full["_source"]
        assert {"term": {"places": "texas"}} in fq["filter"] and {"term": {"active": True}} in fq["filter"]
        assert {"bool": {"should": [{"term": {"remote": True}}], "minimum_should_match": 1}} in fq["filter"]   # remote or hybrid: remote kept
        assert "must_not" not in fq                                 # both "remote for other countries" exclusions name cc: left out whole
        assert _fit({"bool": {"must_not": [{"bool": {"filter": [{"term": {"remote": True}}, {"exists": {"field": "cc"}}]}}]}}, lambda f: f in v1) == {"bool": {}}
        assert got["sort"] and all(isinstance(x, str) or set(x) <= v1 | {"_score"} for x in got["sort"])
    finally:
        _READY["fields"] = None
    # ready(): a look that fails keeps the last answer and asks again in 10 s; an older index counts as ready (it answers through fit)
    global call
    real_call, keep_ = call, dict(_READY)
    try:
        def down(*a_, **k_): raise OSError("timed out")
        _READY.update(at=-1e9, ok=True); call = down
        assert ready() is True and time.monotonic() - _READY["at"] > 45
        _READY.update(at=-1e9, ok=False)
        assert ready() is False
        call = lambda *a_, **k_: {"jobs-1": {"mappings": {"_meta": {"v": VERSION - 1}, "properties": {"slug": {"type": "keyword"}, "company": {"type": "text", "fields": {"raw": {}}}}}}}
        _READY.update(at=-1e9)
        assert ready() is True and _READY["fields"] == {"slug", "company", "company.raw"}
        call = lambda *a_, **k_: {"jobs-2": {"mappings": {"_meta": {"v": VERSION}, "properties": {"slug": {"type": "keyword"}}}}}
        _READY.update(at=-1e9)
        assert ready() is True and _READY["fields"] is None
    finally:
        call = real_call; _READY.clear(); _READY.update(keep_)
    print("search_engine: query builder checks passed")


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]: _test()
    elif sys.argv[1:2] == ["index"]:
        name, n, took = index(sys.argv[2] if len(sys.argv) > 2 else ROOT / "data" / "jobs.db")
        print(f"{n:,} jobs loaded into {name} in {took:.0f} s; the alias {ALIAS} points at it")
    elif sys.argv[1:2] == ["search"]:
        total, slugs, facets = search(" ".join(sys.argv[2:]), limit=5)
        print(total, slugs, json.dumps(facets)[:300])
    else: print(__doc__)
