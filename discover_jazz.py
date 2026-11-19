"""Find the JazzHR job boards worth reading and write them to sources_jazz.json (19 Nov 2026; the owner: "find more jobs").

    python3 discover_jazz.py                 read JazzHR's sitemaps, check one posting of every board with 3 or more jobs, write the file
    python3 discover_jazz.py --check A B C   read these boards (subdomains) the way the hourly run does and print what came back

JazzHR hosts each customer's board at https://<company>.applytojob.com/apply. robots.txt of app.jazz.co and of the boards allows
everything but /cb to any crawler, and lists five sitemaps (app.jazz.co/feeds/google/xml/0 to 4) with every job JazzHR publishes to
search engines: about 108,000 jobs at about 7,400 companies on 19 Nov 2026. Their dates are all today's, so they say nothing about
what is new; a fifth of the jobs are listed under an older address that now answers "410 Gone" (the board's own list has them under
a short one), and a few jobs a board publishes are not in them. So they are used only here, to find the boards; collect.fetch_jazzhr
reads each board's own list.

A board is kept when it has 3 or more jobs in the sitemaps, its account is still active (the sitemaps also list jobs of closed
accounts), one of its postings (read here) is in English (collect.english), its company is not a recruitment or staffing agency
(discover_ats.AGENCY_RX on the name, AGENCY_TEXT on the posting) nor one of JazzHR's many insurance "agency offices" recruiting
commission-only agents (NOT_EMPLOYER), and it is not a company we already read under another system (dedupe.company_key against the
other sources files). Two boards of one company: the larger stays. The name is the one the posting gives (hiringOrganization), without
legal endings (discover_ats.clean_name).

Polite: one request every half second in all (2 a second), four at a time, with the user agent of net.py. HRN_DISCOVER_LOG=FILE
keeps what was checked (JSON lines), so a second run asks only about the boards not checked yet.
"""
import collections, concurrent.futures as cf, datetime, html, json, os, re, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import collect, dedupe, net                       # noqa: E402
from discover_ats import AGENCY_RX, clean_name   # noqa: E402

OUT = ROOT / "sources_jazz.json"
TODAY = datetime.date.today().isoformat()
SITEMAPS = [f"https://app.jazz.co/feeds/google/xml/{i}" for i in range(5)]
MIN_JOBS = 3
GAP = 0.5
# JazzHR is popular with insurance "agency offices" (American Income Life, Globe Life, Symmetry and the like) that post one
# commission-only sales opening in hundreds of towns; and with demo and test accounts. Neither is an employer's own job list.
NOT_EMPLOYER = re.compile(r"(?-i:\bAO\b)|american income life|globe life|family heritage|symmetry financial|family first life|(?-i:\bAIL\b)|"
                          r"\bdemo\b|\btest(ing)? (account|company)\b|^test\b", re.I)
# Large boards the rules above let through, left out by hand after reading their lists on 19 Nov 2026 (as in discover_ats.py).
NOT_BOARDS = {
    "milehighadjustershoustoninc": "one opening, independent claims adjuster, posted in 3,450 towns by a firm that trains adjusters",
    "intellipro": "a staffing agency (IntelliPro)", "healthforce": "a travel-nurse staffing agency",
    "mentortechnicalgroup": "a technical staffing agency", "brightvisiontechnologies": "an IT staffing and consulting firm",
    "symsstrategicgroup": "an IT staffing firm: one opening posted 147 times",
}
# a posting written by an agency for someone else ("Our client is seeking", "on behalf of our client", "a staffing firm")
AGENCY_TEXT = re.compile(r"\bour client(?:\s(?:is|has|in)\b|,)|on behalf of (?:our|a|one of our) clients?\b|\b(?:staffing|recruiting|recruitment|placement|search) "
                         r"(?:agency|firm)\b", re.I)

_next, _lock = [0.0], threading.Lock()


def get(url, timeout=40):
    """A page, at most one request every GAP seconds across all threads."""
    with _lock:
        now = time.monotonic()
        at = max(now, _next[0])
        _next[0] = at + GAP
    if at > now: time.sleep(at - now)
    return net.get_text(url, timeout, accept="text/html,application/xml", compressed=True)


def boards_in_sitemaps():
    """{subdomain: [job addresses]} from the five sitemaps."""
    by = collections.defaultdict(list)
    for url in SITEMAPS:
        x = get(url, 120)
        if not x: sys.exit(f"{url}: no answer; nothing written")
        for host, path in re.findall(r"<loc>https?://([a-z0-9-]+)\.applytojob\.com(/apply/[^<?]+)", x):
            by[host].append(f"https://{host}.applytojob.com{path}")
        print(f"{url}: {sum(map(len, by.values())):,} jobs so far", flush=True)
    return by


def org_name(page):
    """The company's name on a JazzHR page: the JobPosting's hiringOrganization, else the page's Organization block, else its title."""
    for b in collect.JAZZ_LD.findall(page or ""):
        try: d = json.loads(b, strict=False)
        except ValueError: continue
        if not isinstance(d, dict): continue
        org = d.get("hiringOrganization") if isinstance(d.get("hiringOrganization"), dict) else {}
        n = org.get("name") if d.get("@type") == "JobPosting" else d.get("name") if d.get("@type") == "Organization" else ""
        if n and str(n).strip(): return html.unescape(str(n)).strip()
    m = re.search(r"<title>[^<]*?([^<-]+?)\s*-\s*Career Page\s*</title>", page or "")
    return html.unescape(m.group(1)).strip() if m else ""


def check(sub, urls):
    """(entry, None) or (None, why not) for one board, from one of its postings."""
    short = [u for u in urls if len(u.split("/apply/", 1)[1].split("/", 1)[0]) <= 20]
    if not short:                                    # every address in the sitemaps is an old one: the board's own list has the new ones
        listed = collect.jazz_list(get(f"https://{sub}.applytojob.com/apply"))
        if not listed: return None, "no list"
        short = [x[1] for x in listed]
    page = get(short[0])
    if not page: return None, "no answer"
    if "Inactive Career Page" in page: return None, "inactive account (its jobs are still in the sitemaps)"
    d = collect.jazz_page(page)
    name = clean_name(org_name(page), sub)
    if not name: return None, "no name"
    if not d: return None, "posting not readable"
    text = collect.strip_html(d.get("description") or "")
    if not collect.english(f"{name}\n{text}"): return None, "not in English"
    if AGENCY_TEXT.search(text): return None, "a recruitment or staffing agency (its posting says so)"
    return {"name": name, "ats": "jazzhr", "token": sub, "count": len(urls), "added": TODAY}, None


def main():
    t0 = time.time()
    by = boards_in_sitemaps()
    todo = sorted(((s, u) for s, u in by.items() if len(u) >= MIN_JOBS), key=lambda x: -len(x[1]))
    print(f"{sum(map(len, by.values())):,} jobs at {len(by):,} boards; {len(todo):,} boards with {MIN_JOBS} or more jobs "
          f"({sum(len(u) for _, u in todo):,} jobs)", flush=True)
    log = Path(os.environ["HRN_DISCOVER_LOG"]) if os.environ.get("HRN_DISCOVER_LOG") else None
    earlier = {r["sub"]: r for r in map(json.loads, log.read_text().splitlines()) if r} if log and log.exists() else {}
    results, why, lock, done = [], collections.Counter(), threading.Lock(), [0]
    for sub, urls in todo:
        if sub in earlier:
            r = earlier[sub]
            if r.get("entry"): results.append(dict(r["entry"], count=len(urls)))
            else: why[r["why"]] += 1
    rest = [(s, u) for s, u in todo if s not in earlier]

    def run(item):
        sub, urls = item
        try: entry, no = check(sub, urls)
        except Exception as ex: entry, no = None, f"error {type(ex).__name__}"
        with lock:
            if log:
                with log.open("a") as f: f.write(json.dumps({"sub": sub, "entry": entry, "why": no}, ensure_ascii=False) + "\n")
            done[0] += 1
            if entry: results.append(entry)
            else: why[no] += 1
            if done[0] % 200 == 0: print(f"  {done[0]:,} of {len(rest):,} checked, {len(results):,} kept, {time.time() - t0:.0f} s", flush=True)
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(run, rest))
    others = {dedupe.company_key(s["name"]) for f in sorted(ROOT.glob("sources*.json")) if f.name not in ("sources_candidates.json", OUT.name)
              for s in json.loads(f.read_text())}
    best = {}
    for e in sorted(results, key=lambda e: -e["count"]):
        if e["token"] in NOT_BOARDS: why["left out by hand (NOT_BOARDS)"] += 1; continue
        if AGENCY_RX.search(e["name"]): why["a recruitment or staffing agency"] += 1; continue
        if NOT_EMPLOYER.search(e["name"]): why["insurance agency office, demo or test (name)"] += 1; continue
        k = dedupe.company_key(e["name"])
        if k in others: why["already read under another system"] += 1; continue
        if k in best: why["a second board of the same company"] += 1; continue
        best[k] = e
    keep = sorted(best.values(), key=lambda e: (-e["count"], e["name"].lower()))
    OUT.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in keep) + "\n]\n")
    print(f"kept {len(keep):,} boards with {sum(e['count'] for e in keep):,} jobs in {time.time() - t0:.0f} s; written to {OUT.name}")
    for k, n in why.most_common(): print(f"  not kept, {k}: {n:,}")


def check_boards(subs):
    """Read boards with collect.fetch, as the hourly run does (without a record to reuse), and print what came back."""
    for sub in subs:
        src = {"name": sub, "ats": "jazzhr", "token": sub}
        for e in (json.loads(OUT.read_text()) if OUT.exists() else []):
            if e["token"] == sub: src = dict(e)
        t0 = time.time()
        _, jobs = collect.fetch(src)
        if jobs is None: print(f"{sub}: no answer ({time.time() - t0:.1f} s)"); continue
        listed = collect.jazz_list(net.get_text(f"https://{sub}.applytojob.com/apply", 60, accept="text/html", compressed=True)) or []
        print(f"{src['name']} ({sub}): {len(listed)} jobs on its list, {len(jobs)} records read in {time.time() - t0:.1f} s "
              f"(at most {collect.DETAILS} pages a read), {src.get('not_english', 0)} not in English")
        if jobs:
            j = max(jobs, key=lambda j: (bool(j["salary"]), bool(j["posted"]), len(j["excerpt"])))
            print("  " + json.dumps({k: (v[:200] + "…" if isinstance(v, str) and len(v) > 200 else v) for k, v in j.items()}, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--check"]: check_boards(sys.argv[2:])
    elif sys.argv[1:]: print(__doc__)
    else: main()
