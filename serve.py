"""The site with job pages built from records: every job page comes from its row in data/jobs.db at the moment it is asked for, the
rest of the site from the files in site/. Nothing to install: Python's own web server and SQLite.

    HRN_RECORDS=1 python3 build.py      # the site without job pages, and data/jobs.db
    python3 serve.py                    # http://localhost:8790/crypto-vakansii/   (PORT=..., HOST=... to change)

On the server nginx hands out the files itself, keeps each job page for a few minutes and asks this program only for /job/...
(server/hosting/nginx-hrn.conf). A job page is built in a few milliseconds; the page of a job that is not in the records is a 404.

Two more addresses, both read-only and public:
  /api/search?q=python+berlin&remote=1&limit=20&offset=0   word search over every open job, as JSON: Lucene (OpenSearch, see
                                                           search_engine.py) when HRN_OPENSEARCH is set, else SQLite FTS5
  /mcp                                                     the connector an AI assistant adds by address (Model Context Protocol):
                                                           tools search_jobs and get_job
"""
import json, os, re, sys, threading, time, urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import build, records, search_engine                     # noqa: E402  (build.py is only read here: its main() does not run)

SITE, P = ROOT / "site", build.P
STORE = records.Store(ROOT / "data" / "jobs.db", build, live=os.environ.get("HRN_LIVE", "1") != "0")
JOB = re.compile(r"^" + re.escape(P) + r"/job/([a-z0-9-]+)(/?)$")
SEARCH, MCP = P + "/api/search", P + "/mcp"
TAG = re.compile(r"<[^>]+>")


def find(q, remote=False, limit=20, offset=0):
    """Search: Lucene (OpenSearch) when it is set up and answers, otherwise SQLite FTS5 in the records file.
    Returns (total, records, facets, engine)."""
    try:
        total, slugs, facets = search_engine.search(q, remote=remote, limit=limit, offset=offset)
        return total, STORE.records(slugs), facets, "lucene"
    except OSError:
        total, js = STORE.search(q, remote=remote, limit=limit, offset=offset)
        return total, js, {}, "sqlite"


def brief(j):
    """A job as the search answer gives it: what a list of results shows, and the address of its page."""
    return {"slug": j["slug"], "title": j["title"], "company": j["company"], "location": j.get("location") or "", "remote": bool(j.get("remote")),
            "salary": j.get("salary") or "", "posted": j.get("posted") or "", "last_checked": j.get("last_seen") or "", "url": f"{build.FULL}/job/{j['slug']}/"}


# ---- MCP: the connector an AI assistant (Claude, ChatGPT and others) adds by its address, then searches our jobs in plain words. ----
# Model Context Protocol over plain HTTP: one POST per JSON-RPC message, the answer in the same response, no session and no stream.
# Read-only and public, like the site: no account and nothing about the person asking is kept.
MCP_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
MCP_TOOLS = [
    {"name": "search_jobs", "title": "Search open jobs",
     "description": "Search the open tech jobs on " + build.SITE + ": every job is read from the employer's own careers page and re-checked every hour. "
                    "Words are matched in the title, company, skills, place and text of each posting, best match first. Add 'remote' for remote jobs only.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "Words to look for, e.g. 'senior python engineer berlin' or 'solidity remote'"},
         "remote_only": {"type": "boolean", "description": "Only remote jobs", "default": False},
         "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10}}, "required": ["query"]},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "get_job", "title": "Read one job",
     "description": "The full posting of one job: the employer's own text, place, pay, when it was posted, when it was last seen open, and the link to apply on the employer's site.",
     "inputSchema": {"type": "object", "properties": {
         "job": {"type": "string", "description": "The job's slug or its page address, as search_jobs gives them"}}, "required": ["job"]},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
]


def mcp_call(name, args):
    if name == "search_jobs":
        q = str(args.get("query") or "")
        total, js, _, _ = find(q, remote=bool(args.get("remote_only")), limit=int(args.get("limit") or 10))
        items = [brief(j) for j in js]
        lines = [f"{total:,} open jobs match “{q}”." + (" The best ones:" if items else " Try fewer or other words.")]
        lines += [f"{i}. {x['title']} — {x['company']}" + (f" · {x['location']}" if x["location"] else "") + (" · remote" if x["remote"] else "")
                  + (f" · {x['salary']}" if x["salary"] else "") + (f" · posted {x['posted']}" if x["posted"] else "") + f"\n   {x['url']}" for i, x in enumerate(items, 1)]
        return "\n".join(lines), {"total": total, "jobs": items}
    if name == "get_job":
        slug = str(args.get("job") or "").strip().rstrip("/").rsplit("/", 1)[-1]
        j = STORE.record(slug) if re.fullmatch(r"[a-z0-9-]+", slug or "-") else None
        if j is None: raise LookupError("No job with that slug or address. Use search_jobs to find one.")
        text = re.sub(r"\s*\n\s*", "\n", build.html.unescape(TAG.sub("\n", j.get("desc") or j.get("excerpt") or ""))).strip()
        x = brief(j) | {"open": bool(j["active"]), "closed_on": j.get("closed") or "", "apply_url": (j.get("url") or "") if j["active"] else "", "text": text[:8000]}
        head = (f"{x['title']} — {x['company']}" + (f" · {x['location']}" if x["location"] else "") + (f" · {x['salary']}" if x["salary"] else "") + "\n"
                + (f"Open: last seen on the employer's careers page on {x['last_checked']}. Apply on the employer's site: {x['apply_url']}" if x["open"]
                   else f"Closed{' on ' + x['closed_on'] if x['closed_on'] else ''}: it no longer takes applications.") + f"\nPage: {x['url']}\n\n")
        return head + (x["text"] or "The posting has no text here; it is on the employer's page."), x
    raise KeyError(name)


def mcp(msg):
    """One JSON-RPC message in, its answer out (None for a notification, which gets no answer)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid request"}}
    mid, method, prm = msg.get("id"), msg["method"], msg.get("params") or {}
    if "id" not in msg: return None
    ok = lambda r: {"jsonrpc": "2.0", "id": mid, "result": r}
    if method == "initialize":
        want = prm.get("protocolVersion")
        return ok({"protocolVersion": want if want in MCP_VERSIONS else MCP_VERSIONS[0], "capabilities": {"tools": {"listChanged": False}},
                   "serverInfo": {"name": "jobs", "title": build.SITE, "version": "1.0"},
                   "instructions": f"Open tech jobs from {build.SITE}, read from employers' own careers pages every hour. search_jobs finds jobs; get_job reads one. "
                                   "Always give the person the job's page or apply link; you apply on the employer's site."})
    if method == "ping": return ok({})
    if method == "tools/list": return ok({"tools": MCP_TOOLS})
    if method == "tools/call":
        try:
            text, data = mcp_call(prm.get("name"), prm.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": text}], "structuredContent": data, "isError": False})
        except KeyError:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Unknown tool: {prm.get('name')}"}}
        except (LookupError, ValueError, TypeError) as err:
            return ok({"content": [{"type": "text", "text": str(err)}], "isError": True})
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


class Handler(SimpleHTTPRequestHandler):
    server_version = "HRN"
    sys_version = ""

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(SITE), **kw)

    def send(self, code, body, kind="text/html; charset=utf-8", extra=()):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        for k, v in extra: self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD": self.wfile.write(data)

    def not_found(self):
        f = SITE / "404.html"
        self.send(404, f.read_text(encoding="utf-8") if f.is_file() else "Not found")

    def send_json(self, code, obj, extra=()):
        self.send(code, json.dumps(obj, ensure_ascii=False, separators=(",", ":")), "application/json; charset=utf-8", extra)

    def do_POST(self):
        if self.path.split("?", 1)[0] != MCP: return self.send(405, "", extra=[("Allow", "GET, HEAD")])
        n = int(self.headers.get("Content-Length") or 0)
        if not 0 < n <= 65536: return self.send_json(413, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Body too large or empty"}})
        try:
            msg = json.loads(self.rfile.read(n))
        except ValueError:
            return self.send_json(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
        out = [r for r in map(mcp, msg) if r] if isinstance(msg, list) else mcp(msg)
        if not out: return self.send(202, "")
        self.send_json(200, out)

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        if path == MCP: return self.send(405, "This is an MCP server: add its address as a connector in your AI assistant.", "text/plain; charset=utf-8", [("Allow", "POST")])
        if path == SEARCH:
            qs = urllib.parse.parse_qs(self.path.partition("?")[2])
            one = lambda k, d="": (qs.get(k) or [d])[0]
            if one("all") == "1":
                # For the site's own search box: every match, best first, as slugs only (up to 5,000); the page applies its
                # filters to them. Lucene only: without it the page keeps its own word matching.
                try:
                    total, slugs, facets = search_engine.search(one("q"), limit=5000, cap=5000, timeout=3)
                except OSError:
                    return self.send_json(503, {"error": "search engine unavailable"})
                return self.send_json(200, {"q": one("q"), "total": total, "slugs": slugs, "fuzzy": bool(facets.get("fuzzy")), "engine": "lucene"},
                                      [("Cache-Control", "public, max-age=120")])
            try:
                total, js, facets, engine = find(one("q"), remote=one("remote") in ("1", "true"), limit=int(one("limit", "20")), offset=int(one("offset", "0")))
            except ValueError:
                return self.send_json(400, {"error": "limit and offset are numbers"})
            return self.send_json(200, {"q": one("q"), "total": total, "jobs": [brief(j) for j in js], "facets": facets, "engine": engine},
                                  [("Cache-Control", "public, max-age=120"), ("Access-Control-Allow-Origin", "*")])
        m = JOB.match(path)
        if m:
            if not m.group(2):                           # /job/<slug> -> /job/<slug>/, as on GitHub Pages
                return self.send(301, "", extra=[("Location", path + "/" + self.path[len(path):])])
            try:
                html = STORE.page(m.group(1))
            except Exception as err:                     # a broken record must not take the server down; nginx serves its last copy
                self.log_error("job page %s: %r", m.group(1), err)
                return self.send(500, "This page could not be built. Try again in a minute.")
            if html is None: return self.not_found()
            return self.send(200, html, extra=[("Cache-Control", "public, max-age=300")])
        if P and not (path == P or path.startswith(P + "/")): return self.not_found()
        self.path = self.path[len(P):] or "/"
        if not os.path.exists(self.translate_path(self.path)): return self.not_found()
        return super().do_HEAD() if self.command == "HEAD" else super().do_GET()

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        if os.environ.get("HRN_QUIET") != "1": super().log_message(fmt, *args)


CODE = [ROOT / f for f in ("build.py", "records.py", "serve.py", "config.json")]


def watch(seen):
    """The hourly upload brings new code now and then. The page code is read once, at start, so when a file of it changes the program
    stops and systemd starts it again (Restart=always): about a second, during which nginx serves the copies it keeps."""
    while True:
        time.sleep(30)
        if [f.stat().st_mtime_ns for f in CODE] != seen:
            print("the page code changed: restarting", flush=True)
            os._exit(3)


def main():
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8790"))
    STORE.page("")                                       # opens the records once, so the first visitor does not wait for it
    print(f"{STORE.count:,} job records; site on http://{host}:{port}{P}/", flush=True)
    if os.environ.get("HRN_WATCH") == "1":
        threading.Thread(target=watch, args=([f.stat().st_mtime_ns for f in CODE],), daemon=True).start()
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
