"""Internal links of the built site, counted per page: orphans, weak pages, links that lead to a copy or a redirect.

    python3 inlinks.py [site folder] [--new PREFIX ...] [--show PATH ...] [--out FILE] [--job-sample N]

Reads every page of site/ except job pages as a source of links (a job page links to its company, role and place pages, which is
not a choice anyone made for those pages, so it does not count), and every page as a target. For each target it counts the source
pages that link to it: anywhere on the page, and inside <main> only (the header and footer are the same on every page, so a link
there says nothing about the page's place in the site). Reports:

  1. per kind of page (the first part of the address): pages, orphans (no source page links to them), pages linked only from the
     header or footer, the median number of linking pages;
  2. links that lead to a page whose canonical address is another page, or to a redirect page (meta refresh), or to an address
     the server forwards (nginx-hrn.conf); a link should name the page that is meant to rank;
  3. links to pages that do not exist;
  4. for the pages under each --new prefix: how many pages link to them from their main content, the weak ones (fewer than 3);
  5. --show PATH: who links to that page.

It changes nothing. Written for the linking pass of 26 Nov 2026 (owner: "весь сайт должен усиливаться максимально за счёт перелинковки").
"""
import html, json, os, random, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
args = sys.argv[1:]
SITE = Path(args[0]) if args and not args[0].startswith("--") else ROOT / "site"
CFG = json.loads((ROOT / "config.json").read_text())
P = CFG.get("base_path", "").rstrip("/")
FULL = CFG["base_url"].rstrip("/") + P


def opt(name):
    out, on = [], False
    for a in args:
        if a.startswith("--"): on = a == name; continue
        if on: out.append(a)
    return out


HREF = re.compile(r'<a\s[^>]*?href="([^"#?]*)[^"]*"')
CANON = re.compile(r'<link rel="canonical" href="([^"]*)"')
REFRESH = re.compile(r'http-equiv="refresh" content="\d+;\s*url=([^"]*)"', re.I)
ROBOTS = re.compile(r'<meta name="robots" content="([^"]*)"')
SKIP_SRC = ("job/",)
NGINX_301 = {}                      # address -> where the server forwards it
conf = ROOT / "server" / "hosting" / "nginx-hrn.conf"
if conf.exists():
    for m in re.finditer(r"location = (/\S*) \{ return 301 (/\S*?)(?:\$is_args\$args)?; \}", conf.read_text()):
        NGINX_301[m.group(1).lstrip("/")] = m.group(2).lstrip("/")


def rel_of(href):
    """The site path a link leads to ("roles/bilingual/"), or None for links off the site."""
    if href.startswith(FULL + "/"): h = href[len(FULL):]
    elif href.startswith("/") and not href.startswith("//"): h = href
    else: return None
    if P and h.startswith(P + "/"): h = h[len(P):]
    h = html.unescape(h).lstrip("/")
    return h


def target_file(rel):
    if rel == "": return SITE / "index.html"
    t = SITE / rel
    if rel.endswith("/"): return t / "index.html"
    return t if t.suffix else t / "index.html"


def kind(rel):
    p = rel.strip("/").split("/")
    if rel == "": return "(home)"
    if p[0] == "categories" and len(p) >= 2: return "categories/<field>" + ("/" + "/".join("<x>" for _ in p[2:]) if len(p) > 2 else "")
    return p[0] + ("/*" if len(p) > 1 else "")


def main():
    pages = {}                       # rel -> (canonical rel or None, refresh rel or None, noindex)
    files = []
    for dirpath, dirs, fs in os.walk(SITE):
        rel = os.path.relpath(dirpath, SITE).replace(os.sep, "/")
        rel = "" if rel == "." else rel + "/"
        if "index.html" in fs: files.append(rel)
    job_pages = [r for r in files if r.startswith(SKIP_SRC)]
    src_pages = [r for r in files if not r.startswith(SKIP_SRC)]
    inb_all, inb_main = defaultdict(set), defaultdict(set)
    bad = defaultdict(lambda: defaultdict(set))       # problem -> target -> sources
    link_n = 0

    def head_info(rel, t):
        c = CANON.search(t[:20000]); r = REFRESH.search(t[:20000]); rb = ROBOTS.search(t[:20000])
        return (rel_of(c.group(1)) if c else None, rel_of(r.group(1)) if r else None, "noindex" in (rb.group(1) if rb else ""))

    def read(rel):
        return (SITE / rel / "index.html").read_text(encoding="utf-8", errors="replace") if rel else (SITE / "index.html").read_text(encoding="utf-8", errors="replace")

    texts = {}
    for rel in src_pages:
        t = read(rel)
        pages[rel] = head_info(rel, t)
        texts[rel] = t
    n_jobs = int(opt("--job-sample")[0]) if opt("--job-sample") else 3000
    random.seed(1)
    job_sample = random.sample(job_pages, min(n_jobs, len(job_pages)))
    info_cache = {}

    def info(rel):
        if rel in pages: return pages[rel]
        if rel not in info_cache:
            f = target_file(rel)
            if f.exists() and f.suffix == ".html":
                info_cache[rel] = head_info(rel, f.read_text(encoding="utf-8", errors="replace")[:20000])
            else:
                info_cache[rel] = (rel, None, False) if f.exists() else None
        return info_cache[rel]

    def scan(rel, t, count):
        nonlocal link_n
        a = t.find("<main"); b = t.rfind("</main>")
        for m in HREF.finditer(t):
            tr = rel_of(m.group(1))
            if tr is None: continue
            if tr and not tr.endswith("/") and "." not in tr.rsplit("/", 1)[-1]: tr += "/"
            link_n += 1
            if tr in NGINX_301: bad["server forwards it (301)"][tr].add(rel)
            inf = info(tr)
            if inf is None:
                bad["page does not exist"][tr].add(rel); continue
            canon, refresh, noindex = inf
            if refresh is not None: bad["redirect page (meta refresh)"][tr + " -> " + refresh].add(rel)
            elif canon is not None and canon != tr: bad["canonical is another page"][tr + " -> " + canon].add(rel)
            if count and tr != rel:
                inb_all[tr].add(rel)
                if a <= m.start() < b: inb_main[tr].add(rel)

    for rel in src_pages: scan(rel, texts[rel], True)
    for rel in job_sample: scan(rel, read(rel), False)

    out = []
    say = lambda *x: out.append(" ".join(str(y) for y in x))
    say(f"# Internal links: {len(src_pages):,} pages read as sources (job pages left out), {len(job_pages):,} job pages, "
        f"{len(job_sample):,} of them read for wrong links; {link_n:,} links\n")
    # 1. by kind
    open_pages = [r for r in src_pages if pages[r][1] is None and not pages[r][2] and (pages[r][0] in (None, r))]
    by = defaultdict(list)
    for r in open_pages: by[kind(r)].append(r)
    say("## 1. Pages open to search (self-canonical, not noindex, not a redirect), by kind")
    say("| kind | pages | orphans | only header/footer | median linking pages (main) |")
    say("|---|---:|---:|---:|---:|")
    orph, foot_only = [], []
    for k in sorted(by, key=lambda k: -len(by[k])):
        rs = by[k]
        o = [r for r in rs if r != "" and not inb_all.get(r)]
        f = [r for r in rs if r != "" and inb_all.get(r) and not inb_main.get(r)]
        orph += o; foot_only += f
        say(f"| {k} | {len(rs):,} | {len(o):,} | {len(f):,} | {statistics.median([len(inb_main.get(r, ())) for r in rs]):g} |")
    say(f"\nOrphans in all: {len(orph):,}; linked only from the header or footer: {len(foot_only):,}")
    for r in orph[:80]: say(f"- orphan: /{r}")
    for r in foot_only[:40]: say(f"- header/footer only: /{r}")
    # 2-3. wrong links
    say("\n## 2-3. Links that do not lead to the page meant to rank")
    totals = {}
    for prob in ("canonical is another page", "redirect page (meta refresh)", "server forwards it (301)", "page does not exist"):
        tg = bad.get(prob, {})
        n_src = sum(len(s) for s in tg.values())
        totals[prob] = (len(tg), n_src)
        say(f"\n### {prob}: {len(tg):,} addresses, {n_src:,} linking pages (job pages: a sample)")
        for t_, s in sorted(tg.items(), key=lambda x: -len(x[1]))[:60]:
            ex = sorted(s)[:4]
            say(f"- /{t_}  ← {len(s):,}: " + ", ".join("/" + x for x in ex) + (" …" if len(s) > 4 else ""))
    # 4. new pages
    news = opt("--new")
    if news:
        say("\n## 4. New pages: linking pages from main content (weak: fewer than 3)")
        weak = []
        for pre in news:
            rs = sorted(r for r in src_pages if r.startswith(pre.strip("/") + "/") or r == pre.strip("/") + "/")
            for r in rs:
                n = len(inb_main.get(r, ())); na = len(inb_all.get(r, ()))
                canon = pages[r][0]
                tag = "" if canon in (None, r) else f" (canonical /{canon})"
                if n < 3 and not tag: weak.append(r)
                say(f"- /{r}: {n} main, {na} anywhere{tag}{'  WEAK' if n < 3 and not tag else ''}")
        own_ = [len(inb_main.get(r, ())) for pre in news for r in src_pages if (r.startswith(pre.strip("/") + "/")) and pages[r][0] in (None, r) and pages[r][1] is None]
        say(f"\nWeak new pages: {len(weak)}; of {len(own_)} pages open to search, the fewest linking pages is {min(own_, default=0)}, {sum(1 for x in own_ if x < 5)} have fewer than 5")
        totals["weak new"] = (len(weak), 0)
    for s_ in opt("--show"):
        r = s_.strip("/") + "/"
        say(f"\n## Who links to /{r}: {len(inb_main.get(r, ()))} in main, {len(inb_all.get(r, ()))} anywhere")
        for x in sorted(inb_main.get(r, ()))[:60]: say(f"- /{x}")
    say("\n## Summary")
    say(f"- orphans: {len(orph)}; header/footer only: {len(foot_only)}")
    for k, (a, b) in totals.items(): say(f"- {k}: {a} addresses" + (f", {b} linking pages" if b else ""))
    rep = "\n".join(out) + "\n"
    if opt("--out"): Path(opt("--out")[0]).write_text(rep, encoding="utf-8"); print("\n".join(out[-12:]))
    else: print(rep)


if __name__ == "__main__":
    main()
