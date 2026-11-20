"""Company job boards named in Hacker News' monthly "Ask HN: Who is hiring?" threads, added to sources_hn.json (plan item 12).

Why (20 Nov 2026): the posts are companies hiring, each usually with a link to its own careers page on Greenhouse, Lever, Ashby,
Workable and the other systems collect.py reads. The posts themselves are not taken (free text, written for that thread); the boards
they link to are read like every other employer's board, so a job here still comes from the employer's own page. The "Who wants to
be hired?" threads are people's resumes and are never read (owner: resumes are never taken from other sites).

Threads come from the Hacker News search API (hn.algolia.com, the search Hacker News links from its own pages): the stories of the
account "whoishiring" whose title starts "Ask HN: Who is hiring?", each read whole in one request.

    python3 discover_hn.py [MONTHS]     the last MONTHS threads (6 by default); adds the boards that pass the usual check
"""
import collections, concurrent.futures as cf, datetime, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import collect, dedupe, discover_ats as d, net        # noqa: E402

OUT = ROOT / "sources_hn.json"
API = "https://hn.algolia.com/api/v1/"
BOARD_RX = [("greenhouse", re.compile(r"https?://(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]{2,60})", re.I)),
            ("lever", re.compile(r"https?://jobs\.(?:eu\.)?lever\.co/([A-Za-z0-9_.-]{2,60})", re.I)),
            ("ashby", re.compile(r"https?://jobs\.ashbyhq\.com/([A-Za-z0-9_.%-]{2,60})", re.I))]
NOT_TOK = {"embed", "jobs", "job", "api", "v1", "careers", "search"}


def threads(months):
    d_ = net.get_json(API + "search_by_date?tags=story,author_whoishiring&hitsPerPage=40", 30) or {}
    hits = [h for h in d_.get("hits") or [] if str(h.get("title") or "").startswith("Ask HN: Who is hiring?")]
    return [h["objectID"] for h in hits[:months]]


def posts(story):
    """The top-level comments of a thread: (company as the post names it, the post's text with its links)."""
    item = net.get_json(API + f"items/{story}", 60) or {}
    out = []
    for c in item.get("children") or []:
        raw = str(c.get("text") or "")
        if not raw: continue
        text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
        links = " ".join(html.unescape(u) for u in re.findall(r'href="([^"]+)"', raw)) + " " + text
        first = re.split(r"\s*[|\n]\s*", text.strip(), maxsplit=1)[0].strip()
        company = re.sub(r"\s*\(.*?\)\s*$", "", first)[:60].strip(" -–:")
        out.append((company, links))
    return out


def boards(items):
    """{(ats, token): company} for every board link in the posts."""
    found = {}
    for company, links in items:
        for ats, rx in BOARD_RX:
            for tok in rx.findall(links):
                tok = tok.strip(".")
                if tok.lower() not in NOT_TOK: found.setdefault((ats, tok), company)
        for (ats, tok), _ in d.boards_in([links]).items():
            found.setdefault((ats, tok), company)
    return found


def verify(item):
    (ats, tok), company = item
    name = d.clean_name(company, tok) if company and len(company) <= 50 else d.pretty(tok)
    src = {"name": name or d.pretty(tok), "ats": ats, "token": tok}
    try:
        _, jobs = collect.fetch(dict(src))
    except Exception as ex:
        return None, f"error {type(ex).__name__}"
    if jobs is None: return None, "feed not readable"
    if len(jobs) < 3: return None, f"{len(jobs)} English jobs"
    if d.for_clients(jobs): return None, "a recruitment agency (postings for its clients)"
    return dict(src, count=len(jobs), lands=d.lands_of(j["location"] for j in jobs), added=datetime.date.today().isoformat(), via="hn"), None


def main(months=6):
    items = [p for s in threads(months) for p in posts(s)]
    found = boards(items)
    have = [s for f in sorted(ROOT.glob("sources*.json")) if "candidates" not in f.name for s in json.loads(f.read_text())]
    have_keys = {(s["ats"], s["token"].lower()) for s in have}
    have_cos = {dedupe.company_key(s["name"]) for s in have}
    todo = [(k, c) for k, c in found.items() if (k[0], k[1].lower()) not in have_keys and dedupe.company_key(c or k[1]) not in have_cos]
    print(f"{len(items):,} posts, {len(found):,} board links, {len(todo):,} boards not read yet: "
          + ", ".join(f"{a} {n}" for a, n in collections.Counter(k[0] for k, _ in todo).most_common()), flush=True)
    collect.DESC_SINCE = ""
    kept, why = [], collections.Counter()
    with cf.ThreadPoolExecutor(6) as ex:
        for entry, no in ex.map(verify, todo):
            if entry: kept.append(entry)
            else: why[re.sub(r"[0-9]+", "N", no)] += 1
    old = json.loads(OUT.read_text()) if OUT.exists() else []
    seen = {dedupe.company_key(e["name"]) for e in old} | have_cos
    new = []
    for e in sorted(kept, key=lambda e: -e["count"]):
        k = dedupe.company_key(e["name"])
        if k in seen: continue
        seen.add(k); new.append(e)
    OUT.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in old + new) + "\n]\n")
    print(f"kept {len(new)} boards with {sum(e['count'] for e in new):,} open jobs; not kept: {dict(why.most_common())}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
