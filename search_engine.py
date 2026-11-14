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
import datetime, html, json, os, re, sqlite3, sys, time, urllib.error, urllib.request
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
    "mappings": {"dynamic": "false", "properties": {
        "slug": {"type": "keyword"}, "active": {"type": "boolean"}, "remote": {"type": "boolean"}, "hybrid": {"type": "boolean"},
        "title": {"type": "text", "analyzer": "job", "search_analyzer": "job_search"},
        "company": {"type": "text", "analyzer": "job", "search_analyzer": "job_search", "fields": {"raw": {"type": "keyword"}}},
        "tags": {"type": "text", "analyzer": "job", "search_analyzer": "job_search", "fields": {"raw": {"type": "keyword"}}},
        "place": {"type": "text", "analyzer": "job", "search_analyzer": "job_search"},
        "body": {"type": "text", "analyzer": "job", "search_analyzer": "job_search"},
        "cat": {"type": "keyword"}, "level": {"type": "keyword"}, "posted": {"type": "date", "ignore_malformed": True},
        "pay_mid": {"type": "float"}}},
}
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


def doc(rec, descr):
    """The searchable part of one job record."""
    usd = rec.get("usd")
    return {"slug": rec["slug"], "active": bool(rec.get("active")), "remote": bool(rec.get("remote")), "hybrid": bool(rec.get("hybrid")),
            "title": rec.get("title") or "", "company": rec.get("company") or "", "tags": rec.get("tags") or [],
            "place": rec.get("location") or "", "body": html.unescape(TAGS.sub(" ", descr or rec.get("excerpt") or "")),
            "cat": rec.get("cat") or "", "level": rec.get("level") or "", "posted": (rec.get("posted") or rec.get("first_seen") or "")[:10] or None,
            "pay_mid": (usd[0] + usd[1]) / 2 if usd else None}


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

    for slug, rec, descr in con.execute("SELECT slug, rec, descr FROM jobs"):
        batch.append(json.dumps({"index": {"_id": slug}}) + "\n" + json.dumps(doc(json.loads(rec), descr), ensure_ascii=False) + "\n")
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


def query(q, remote=False, limit=20, offset=0, fuzzy=False):
    """The search request: every word must be found, in any field; the whole phrase in the title ranks first. "remote" in the
    words is the remote filter. fuzzy: forgive a typo (one in a word of 5-8 letters, two from 9), for the second try when the
    words as typed find nothing. Returns None when there is nothing to look for."""
    words = [w for w in WORD.findall(q)][:12]
    if any(w.lower() == "remote" for w in words): remote, words = True, [w for w in words if w.lower() != "remote"]
    words = [w for w in words if w.lower() not in SKIP]
    if not words: return None
    must = [{"multi_match": {"query": w, "fields": FIELDS, "type": "best_fields", "fuzziness": "AUTO:5,9" if fuzzy and w.isalpha() else 0,
                             "prefix_length": 1, "max_expansions": 30}} for w in words]
    filt = [{"term": {"active": True}}] + ([{"term": {"remote": True}}] if remote else [])
    phrase = " ".join(words)
    return {"size": max(1, min(int(limit), 50)), "from": max(0, min(int(offset), 1000)), "_source": ["slug"], "track_total_hits": True,
            "query": {"bool": {"must": must, "filter": filt,
                               "should": [{"match_phrase": {"title": {"query": phrase, "boost": 8}}},
                                          {"match": {"title": {"query": phrase, "operator": "and", "boost": 4}}},
                                          {"match": {"title": {"query": phrase, "boost": 3}}}]}},       # the more of the words in the title, the higher
            "aggs": {"remote": {"filter": {"term": {"remote": True}}}, "hybrid": {"filter": {"term": {"hybrid": True}}},
                     "cat": {"terms": {"field": "cat", "size": 12}}, "level": {"terms": {"field": "level", "size": 8}},
                     "company": {"terms": {"field": "company.raw", "size": 10}}}}


def search(q, remote=False, limit=20, offset=0, timeout=1.5):
    """(total, [slugs], facets) from OpenSearch: the words as typed first, and only when they find nothing, the same words
    forgiving typos (facets["fuzzy"] then says so). Raises OSError when it is not there or does not answer in time."""
    if not URL: raise OSError("HRN_OPENSEARCH is not set")
    body = query(q, remote, limit, offset)
    if body is None: return 0, [], {}
    r, fuzzy = call("POST", f"/{ALIAS}/_search", body, timeout=timeout), False
    if r["hits"]["total"]["value"] == 0:
        r, fuzzy = call("POST", f"/{ALIAS}/_search", query(q, remote, limit, offset, fuzzy=True), timeout=timeout), True
    a = r.get("aggregations", {})
    facets = {"fuzzy": fuzzy, "remote": a.get("remote", {}).get("doc_count", 0), "hybrid": a.get("hybrid", {}).get("doc_count", 0)}
    for k in ("cat", "level", "company"):
        facets[k] = [[b["key"], b["doc_count"]] for b in a.get(k, {}).get("buckets", []) if b["key"]]
    return r["hits"]["total"]["value"], [h["_source"]["slug"] for h in r["hits"]["hits"]], facets


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
    d = doc({"slug": "a", "active": True, "title": "T", "usd": [100, 200], "tags": ["Go"], "posted": "2026-11-01"}, "<p>Build &amp; ship</p>")
    assert d["pay_mid"] == 150 and d["body"].strip() == "Build & ship" and d["posted"] == "2026-11-01"
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
