"""Pages of the built site that compete for the same search query (cannibalisation), found from titles and headings.

    python3 seo_audit.py [site folder] [--out FILE]        # after a build; job pages (/job/...) are left out

Search engines pick one page of a site for a query. Two pages whose title and main heading say the same thing split the links and the
clicks between them, and the engine may show the weaker one. This reads <title>, <h1>, the canonical address and the robots tag of every
page and reports:

  1. the same title on several pages;
  2. the same main heading on several pages;
  3. titles that are the same once counts, dates, the brand and filler words are taken out (the same words in any order);
  4. pages with no title, no heading, or a canonical address that points to another page;
  5. pairs of sections whose pages share a query key (for example a skill page and a role page that both read "python jobs").

It changes nothing; the report is the work list for the owner's request of 18 Nov 2026 ("чтобы не было проблем с каннибализацией").
"""
import html, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else Path(__file__).resolve().parent / "site"
SKIP = ("job/", "archive/", "embed/", "widget/")                      # job pages are outside this check; embeds are not pages for search
BRAND = re.compile(r"\s*[|·]\s*Jobs Every Hour\s*$", re.I)
FILLER = set("a an the of in for to and or at on with by from is are your you our we now today right new best top free all "
             "hiring open updated checked every hour jobs job 2026 2027".split())
NUM = re.compile(r"[\d][\d,.\$k%+]*")
TITLE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
CANON = re.compile(r'<link rel="canonical" href="([^"]*)"', re.I)
ROBOTS = re.compile(r'<meta name="robots" content="([^"]*)"', re.I)
TAG = re.compile(r"<[^>]+>")


def text(x):
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", x or ""))).strip()


def key(title):
    """The words a title is about: no brand, no counts, no filler, in a fixed order."""
    t = NUM.sub(" ", BRAND.sub("", title).lower())
    words = [w for w in re.findall(r"[a-z][a-z+#.&'-]*", t) if w not in FILLER]
    return " ".join(sorted(set(words)))


def pages(root):
    for dirpath, _, files in os.walk(root):
        if "index.html" not in files: continue
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel = "" if rel == "." else rel + "/"
        if rel.startswith(SKIP): continue
        with open(os.path.join(dirpath, "index.html"), encoding="utf-8", errors="replace") as fh:
            head = fh.read(60000)                                          # title, canonical and the first heading are near the top
        m = TITLE.search(head); h = H1.search(head); c = CANON.search(head); r = ROBOTS.search(head)
        yield "/" + rel, text(m.group(1)) if m else "", text(h.group(1)) if h else "", c.group(1) if c else "", (r.group(1) if r else "").lower()


def section(path):
    return path.strip("/").split("/")[0] or "(home)"


def main():
    out = []
    say = lambda *a: out.append(" ".join(str(x) for x in a))
    rows = [p for p in pages(ROOT)]
    indexed = [p for p in rows if "noindex" not in p[4]]
    say(f"# Pages competing for one query: {len(rows):,} pages read, {len(indexed):,} open to search (job pages left out)\n")

    by_title, by_h1, by_key = defaultdict(list), defaultdict(list), defaultdict(list)
    no_title, no_h1, other_canon = [], [], []
    for path, title, h1, canon, robots in indexed:
        if not title: no_title.append(path)
        if not h1: no_h1.append(path)
        if canon and not canon.rstrip("/").endswith(path.rstrip("/")): other_canon.append((path, canon))
        if canon and not canon.rstrip("/").endswith(path.rstrip("/")): continue          # the page itself says another address is the one to show
        if title: by_title[BRAND.sub("", title)].append(path)
        if h1: by_h1[h1].append(path)
        k = key(title)
        if k: by_key[k].append((path, title))

    dup_t = {t: ps for t, ps in by_title.items() if len(ps) > 1}
    dup_h = {t: ps for t, ps in by_h1.items() if len(ps) > 1}
    near = {k: ps for k, ps in by_key.items() if len(ps) > 1 and len({BRAND.sub("", t) for _, t in ps}) > 1}

    say(f"## 1. The same title on several pages: {len(dup_t):,} titles, {sum(len(v) for v in dup_t.values()):,} pages")
    for t, ps in sorted(dup_t.items(), key=lambda x: -len(x[1]))[:60]: say(f"- {len(ps)}× “{t[:110]}”: " + ", ".join(ps[:5]) + (" …" if len(ps) > 5 else ""))
    say(f"\n## 2. The same main heading on several pages: {len(dup_h):,} headings, {sum(len(v) for v in dup_h.values()):,} pages")
    for t, ps in sorted(dup_h.items(), key=lambda x: -len(x[1]))[:60]: say(f"- {len(ps)}× “{t[:110]}”: " + ", ".join(ps[:5]) + (" …" if len(ps) > 5 else ""))
    say(f"\n## 3. Titles about the same words (counts, dates and filler taken out): {len(near):,} groups")
    pairs = Counter()
    for k, ps in near.items():
        secs = sorted({section(p) for p, _ in ps})
        pairs[" + ".join(secs)] += 1
    say("By sections involved:")
    for s_, n in pairs.most_common(40): say(f"- {n:>5}  {s_}")
    say("\nExamples (up to 80 groups, the groups across different sections first):")
    order = sorted(near.items(), key=lambda x: (-len({section(p) for p, _ in x[1]}), -len(x[1])))
    for k, ps in order[:80]:
        say(f"- [{k[:70]}]")
        for p, t in ps[:4]: say(f"    {p}  ·  {BRAND.sub('', t)[:100]}")
    say(f"\n## 4. Housekeeping\n- no title: {len(no_title)} {no_title[:8]}\n- no main heading: {len(no_h1)} {no_h1[:12]}\n- canonical points elsewhere: {len(other_canon)}")
    for p, c in other_canon[:25]: say(f"    {p} -> {c}")
    say(f"- closed to search (noindex): {len(rows) - len(indexed)}")
    lens = [len(BRAND.sub('', t)) for _, t, *_ in indexed if t]
    say(f"- titles longer than 65 characters: {sum(1 for x in lens if x > 65)}; shorter than 25: {sum(1 for x in lens if x < 25)}")
    sec = Counter(section(p) for p, *_ in indexed)
    say("\n## 5. Pages by section\n" + ", ".join(f"{s_} {n:,}" for s_, n in sec.most_common(60)))

    report = "\n".join(out) + "\n"
    if "--out" in sys.argv: Path(sys.argv[sys.argv.index("--out") + 1]).write_text(report, encoding="utf-8")
    else: print(report)


if __name__ == "__main__":
    main()
