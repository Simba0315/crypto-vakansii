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


def doc(rec, descr, codes=None, day=""):
    """The searchable part of one job record, and what a row of results shows. codes: place slug -> country code (build.PLACE_CODE),
    for the flags and "remote open to my country"; day: the build's day, which turns the order of the paid Premium jobs."""
    usd = rec.get("usd")
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
            "ckey": (company + SEP + title)[:2000]}      # the same role posted once per city is one row with "+N more locations"


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
    r, fuzzy = call("POST", f"/{ALIAS}/_search", body, timeout=timeout), False
    exact = r["hits"]["total"]["value"]
    if exact < FEW:
        rf = call("POST", f"/{ALIAS}/_search", query(q, remote, limit, offset, fuzzy=True, cap=cap, facets=facets), timeout=timeout)
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
    p["offset"], p["limit"] = min(num("offset"), DEEPEST - 1), max(1, min(num("limit") or PAGE, PAGE))
    p["ids"] = [s for s in listed("ids", 60, 200) if SLUG.fullmatch(s)]
    p["sk"] = listed("sk", 30, 60)                                   # any of these skills (For you), where skills= needs all of them
    p["co"] = one("co")[:120]                                        # one company, by its name as written (companies followed)
    after = num("after"); p["after"] = after if 20000101 <= after <= 30001231 else 0     # posted after this day, yyyymmdd (saved searches)
    return p


def list_filters(p, today, drop="", said_remote=False):
    """(filter, must_not) clauses for the page's filters, without the one named drop. The same tests as match() in assets/site.js."""
    f, no = [{"term": {"active": True}}], []
    on = lambda k: k != drop and p.get(k)
    if on("cat"): f.append({"terms": {"cat": p["cat"]}})
    if on("lvl"): f.append({"term": {"exec": True}} if p["lvl"] == "Exec" else {"term": {"level": p["lvl"]}})
    if on("loc"): f.append({"term": {"places": p["loc"]}})
    if on("city"): f.append({"match_phrase": {"place": p["city"]}})          # a city typed by the visitor, in the posting's own place line
    if p.get("rc"):                                                          # remote, but only for other countries
        no.append({"bool": {"filter": [{"term": {"remote": True}}, {"exists": {"field": "cc"}}],
                            "must_not": [{"term": {"anywhere": True}}, {"term": {"cc": p["rc"]}}]}})
    remote = drop != "remote" and (p.get("remote") or said_remote)
    if remote or on("hybrid"):                                               # both ticked: either kind
        f.append({"bool": {"should": ([{"term": {"remote": True}}] if remote else []) + ([{"term": {"hybrid": True}}] if on("hybrid") else []),
                           "minimum_should_match": 1}})
    if on("xl"): no.append({"terms": {"level": p["xl"]}})
    if on("entry"): f.append({"terms": {"level": ["Intern", "Junior"]}})
    if on("crypto"): f.append({"term": {"crypto": True}})
    if on("any"): f += [{"term": {"anywhere": True}}, {"term": {"remote": True}}]
    if on("perk"): f.append({"term": {"perks": p["perk"]}})
    if on("etype"): f.append({"term": {"etype": p["etype"]}})
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


def list_body(p, today, fuzzy=False, drop="", count=False):
    """The request for one page of the list (count=True: only how many jobs match)."""
    words, said_remote = split_words(p["q"]) if drop != "q" else ([], False)
    f, no = list_filters(p, today, drop, said_remote)
    q = {"bool": {"filter": f}}
    if no: q["bool"]["must_not"] = no
    if words: q["bool"].update(must=must_words(words, fuzzy, ["title"] if p.get("ti") else FIELDS), should=rank_words(words))
    if count or p.get("count"): return {"size": 0, "track_total_hits": True, "query": q}
    if p.get("ids"): return {"size": len(p["ids"]), "_source": SRC, "query": q}
    sort = (["_score", {"ts": "desc"}, {"slug": "asc"}] if p["sort"] == "rel" and words else
            [{"pay_hi": {"order": "desc", "missing": "_last"}}] + NEWEST if p["sort"] == "sal" else NEWEST)
    body = {"size": p["limit"], "from": p["offset"], "_source": SRC, "track_total_hits": True, "query": q, "sort": sort,
            "collapse": {"field": "ckey", "inner_hits": {"name": "same", "size": 0}}}     # one row per role, "+N more locations"
    if p.get("sum") and not p["offset"]:
        body["aggs"] = {"remote": {"filter": {"term": {"remote": True}}}, "pay": {"filter": {"term": {"has_pay": True}}},
                        "fresh": {"filter": {"range": {"posted": {"gte": (today - datetime.timedelta(days=7)).isoformat()}}}},
                        "top": {"terms": {"field": "company.raw", "size": 3}}}
    return body


def msearch(bodies, timeout):
    """Several requests in one round trip; their answers in the same order."""
    out = call("POST", f"/{ALIAS}/_msearch", "".join("{}\n" + json.dumps(b) + "\n" for b in bodies), timeout=timeout, ndjson=True)["responses"]
    for x in out:
        if "error" in x: raise OSError(f"OpenSearch msearch: {str(x['error'])[:300]}")
    return out


def listing(p, today=None, timeout=2.5):
    """One page of the list: {"total": jobs that match (each posting counted), "hits": [(_source, other postings of the same role)],
    "fuzzy", "exact", "without": {filter: jobs that match without it} when nothing matches, "more": whether a next page exists}.
    Raises OSError when OpenSearch is not there or does not answer in time."""
    if not URL: raise OSError("HRN_OPENSEARCH is not set")
    today = today or datetime.datetime.now(datetime.timezone.utc).date()
    r = call("POST", f"/{ALIAS}/_search", list_body(p, today), timeout=timeout)
    total, fuzzy, exact, without = r["hits"]["total"]["value"], False, 0, {}
    if p["count"]: return {"total": total, "hits": [], "fuzzy": False, "exact": 0, "without": {}, "more": False}
    words, _ = split_words(p["q"])
    if words and total < FEW and not p["ids"]:
        # Few or none: is it a typo? Decided on the words alone, as the search box always did ("cashier" in Boise is not a typo when
        # thousands of jobs say cashier elsewhere); the list forgiving typos comes in the same round trip.
        alone = params({"q": [p["q"]], "ti": ["1" if p["ti"] else ""]})
        a, b, rf = msearch([list_body(alone, today, count=True), list_body(alone, today, fuzzy=True, count=True), list_body(p, today, fuzzy=True)], timeout)
        if prefer_fuzzy(a["hits"]["total"]["value"], b["hits"]["total"]["value"]) and rf["hits"]["total"]["value"] > total:
            r, fuzzy, exact = rf, True, a["hits"]["total"]["value"]
            total = r["hits"]["total"]["value"]
    if total == 0 and not p["ids"]:
        keys = [k for k in RELAX if p.get(k) or (k == "remote" and split_words(p["q"])[1])]
        if keys:
            got = msearch([list_body(p, today, drop=k, count=True) for k in keys], timeout)
            without = {k: x["hits"]["total"]["value"] for k, x in zip(keys, got) if x["hits"]["total"]["value"]}
    hits = [(h["_source"], max(0, ((h.get("inner_hits") or {}).get("same", {}).get("hits", {}).get("total") or {}).get("value", 1) - 1)) for h in r["hits"]["hits"]]
    out = {"total": total, "hits": hits, "fuzzy": fuzzy, "exact": exact, "without": without,
           "more": not p["ids"] and len(hits) == p["limit"] and p["offset"] + p["limit"] < DEEPEST}
    a = r.get("aggregations")
    if a: out["sum"] = {"remote": a["remote"]["doc_count"], "pay": a["pay"]["doc_count"], "fresh": a["fresh"]["doc_count"],
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


_READY = {"at": -1e9, "ok": False}


def ready():
    """Is the index there and new enough (_meta.v) to answer the list? Asked of OpenSearch at most once a minute. When this code
    first arrives the index is still the old one for the few minutes until the load that follows the upload replaces it."""
    if time.monotonic() - _READY["at"] < 60: return _READY["ok"]
    try:
        m = call("GET", f"/{ALIAS}/_mapping", timeout=1.0)
        ok = any(((v.get("mappings") or {}).get("_meta") or {}).get("v", 0) >= VERSION for v in m.values())
    except (OSError, ValueError):
        ok = False
    _READY.update(at=time.monotonic(), ok=ok)
    return ok


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
    assert [m["multi_match"]["query"] for m in body["query"]["bool"]["must"]] == ["python"]
    assert list_body(P("q=python&ti=1"), day)["query"]["bool"]["must"][0]["multi_match"]["fields"] == ["title"]
    assert list_body(P("sort=rel"), day)["sort"] == NEWEST and list_body(P("sort=sal"), day)["sort"][0]["pay_hi"]["order"] == "desc"
    assert list_body(P("loc=texas"), day, count=True)["size"] == 0 and "collapse" not in list_body(P("ids=a"), day)
    assert "texas" not in flat(list_body(P("loc=texas&q=nurse"), day, drop="loc")) and "nurse" not in flat(list_body(P("loc=texas&q=nurse"), day, drop="q"))
    d = doc({"slug": "nurse-acme", "active": True, "title": "Director of Nursing", "company": "Acme", "location": "Austin, TX", "remote": True,
             "usd": [90000, 120000], "salary": "$90K - $120K", "tags": ["Care"], "posted": "2026-11-20", "places": ["texas", "united-states"],
             "perks": ["Relocation support"], "etype": "Full-time", "t": 1795000000, "ts": 1795000000, "bump": 0, "urgent": True, "premium": True},
            "", {"texas": "US", "united-states": "US"}, "2026-11-25")
    assert d["exec"] and d["cc"] == ["US"] and d["pay_hi"] == 120000 and d["has_pay"] and d["ckey"] == "Acme" + SEP + "Director of Nursing" and len(d["rot"]) == 32
    assert doc({"slug": "x", "title": "Engineer", "posted": "2026-11-20", "ts": 0}, "")["ts"] == day_start("2026-11-20") > 0
    r = row(d, 2, True, now=1795000000 + 3600)
    assert r[:4] == ["nurse-acme", "Director of Nursing", "Acme", "Austin, TX"] and r[4] == 1 | 64 and r[9] == 20261120 and r[10] == 120000
    assert r[14] == 1795000000 // 60 and r[15] == ["US"] and r[16] == 1 and r[17] == 2
    assert row(d, now=1795000000 + 8 * 86400)[14] == 0              # an exact time only in the posting's first week
    f, no = list_filters(P("np=1&onsite=1&sk=Go,Rust&co=Acme&after=20261120"), day)
    assert '{"terms": {"tags.raw": ["Go", "Rust"]}}' in flat(f) and '{"term": {"company.raw": "Acme"}}' in flat(f) and '"gt": "2026-11-20"' in flat(f)
    assert '{"term": {"pool": true}}' in flat(no) and '{"term": {"remote": true}}' in flat(no) and P("after=123")["after"] == 0
    assert list_body(P("count=1&loc=texas"), day)["size"] == 0 and "aggs" in list_body(P("sum=1"), day) and "aggs" not in list_body(P("sum=1&offset=50"), day)
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
