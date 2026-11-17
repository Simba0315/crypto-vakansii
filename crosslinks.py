"""Links that let every narrow page be found (the owner, 15 Nov 2026: "check the internal linking, so the site grows for every query").

A link-graph check of the built site found the long-tail pages nearly unlinked: of 2,095 "<skill> jobs in <place>" pages, 696 could not
be reached from the home page at all and 1,952 had one link or none pointing at them; the same for "<role> jobs in <place>", "<kind of
work> jobs in <place>", "entry-level <skill> jobs" and the rest. Those pages are the ones that answer long searches ("python jobs in
london"), and a page nothing links to is one search engines rarely crawl and barely trust.

So, after the build has written every page, this adds two blocks:
  - on a broad page (London jobs, Python jobs, Data analyst jobs ...): "Narrow down London jobs", its narrower pages grouped by skill,
    kind of work, role, level, with their open-job counts, largest first;
  - on a narrow page (Python jobs in London): "More like Python jobs in London", links up to each broader page (All London jobs, All
    Python jobs) and across to the nearest neighbours.
Pages are matched by their addresses, and the link text is each page's own H1, so a link says exactly what it opens.

    crosslinks.run(site_dir, urls)      urls: the site's own page addresses ("locations/london/skills/python/"), job pages left out
"""
import html, re
from collections import defaultdict
from pathlib import Path

H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
COUNT = re.compile(r"\((\d[\d,]*) open")
TAG = re.compile(r"<[^>]+>")
FLAG = re.compile("[\U0001F1E6-\U0001F1FF]{2}")

GROUP = {"skills": "By skill", "kind": "By kind of work", "roles": "By role", "level": "By level", "places": "By place", "pages": "More pages",
         "remote": "Remote", "chains": "By blockchain"}
LEVELS = {"intern", "junior", "senior", "lead", "entry-level", "new"}


def low(title):
    """A page's heading inside a sentence: "Narrow down jobs in London", not "Narrow down Jobs in London"."""
    return title[0].lower() + title[1:] if title.split(" ", 1)[0] in ("Jobs", "Remote", "Entry-level", "Companies") else title


def parents(u, have):
    """[(broader page, group the narrower one belongs to on it)] for a page address, only pages that exist."""
    p = u.strip("/").split("/")
    out = []
    add = lambda parent, group: out.append((parent, group)) if parent in have and parent != u else None
    if p[0] == "locations" and len(p) == 4 and p[2] == "skills":           # locations/london/skills/python/
        add(f"locations/{p[1]}/", "skills"); add(f"skills/{p[3]}/", "places")
    elif p[0] == "locations" and len(p) == 3:                              # locations/london/finance/  or  .../remote/
        add(f"locations/{p[1]}/", "remote" if p[2] == "remote" else "kind")
        add("remote/" if p[2] == "remote" else f"jobs/{p[2]}/", "places")
    elif p[0] == "roles" and len(p) == 3:                                  # roles/data-analyst/london/  or  .../remote/
        add(f"roles/{p[1]}/", "remote" if p[2] == "remote" else "places")
        add("remote/" if p[2] == "remote" else f"locations/{p[2]}/", "roles")
    elif p[0] == "skills" and len(p) == 3:                                 # skills/sql/entry-level/
        add(f"skills/{p[1]}/", "level")
    elif p[0] == "jobs" and len(p) == 3:                                   # jobs/design/senior/
        add(f"jobs/{p[1]}/", "level")
    elif p[0] == "perks" and len(p) == 3:                                  # perks/visa-sponsorship/texas/
        add(f"perks/{p[1]}/", "places"); add(f"locations/{p[2]}/", "pages")
    elif p[0] == "remote" and len(p) == 3 and p[1] == "skills":            # remote/skills/kubernetes/
        add("remote/", "skills"); add(f"skills/{p[2]}/", "remote")
    elif p[0] == "crypto" and len(p) == 3 and p[1] == "chains":             # crypto/chains/ethereum/
        add("crypto/", "chains")
    elif p[0] == "crypto" and len(p) == 3:                                 # crypto/in/chicago/, crypto/roles/backend-engineer/
        add("crypto/", "places" if p[1] == "in" else "roles")
        add(f"locations/{p[2]}/" if p[1] == "in" else f"roles/{p[2]}/", "pages")
    elif p[0] == "salary" and len(p) == 3:                                 # salary/100k/remote/
        add(f"salary/{p[1]}/", "remote")
    elif p[0] == "salary" and len(p) == 2:
        add("salaries/", "pages")
    elif p[0] == "relocate" and len(p) == 2:
        add("relocate/", "places"); add(f"locations/{p[1]}/", "pages")
    elif p[0] == "compare" and len(p) == 2 and "-vs-" in p[1]:             # compare/data-analyst-vs-data-scientist/, compare/python-vs-sql/
        for x_ in p[1].split("-vs-", 1):
            add(f"roles/{x_}/" if f"roles/{x_}/" in have else f"skills/{x_}/", "pages")
    elif p[0] == "companies" and len(p) == 3 and p[2].isdigit():           # companies/cloudflare/3/  (later pages of a company's jobs)
        add(f"companies/{p[1]}/", "pages")
    elif p[0] == "companies" and len(p) == 3 and p[1] == "compare" and "-vs-" in p[2]:    # companies/compare/shield-ai-vs-cloudflare/
        a_, b_ = p[2].split("-vs-", 1)
        add(f"companies/{a_}/", "pages"); add(f"companies/{b_}/", "pages")
    return out


def run(site, urls):
    site = Path(site)
    have = set(urls)
    info = {}

    def meta(u):
        if u not in info:
            f = site / u / "index.html"
            t = f.read_text(encoding="utf-8") if f.exists() else ""
            m = H1.search(t)
            name = html.unescape(FLAG.sub("", TAG.sub("", m.group(1)))).strip() if m else u
            c = COUNT.search(t[:3000])
            info[u] = (re.sub(r"\s+", " ", name), int(c.group(1).replace(",", "")) if c else 0)
        return info[u]

    up = {u: parents(u, have) for u in urls}
    down = defaultdict(lambda: defaultdict(list))
    for u, ps in up.items():
        for parent, group in ps:
            down[parent][group].append(u)
    a = lambda u: f'<a href="/{u}">{html.escape(meta(u)[0])}</a>' + (f' <span>{meta(u)[1]:,}</span>' if meta(u)[1] else "")
    blocks = defaultdict(str)
    for parent, groups in down.items():                 # broad page: its narrower pages
        title = meta(parent)[0]
        body = ""
        for g in ("skills", "kind", "roles", "places", "chains", "level", "remote", "pages"):
            xs = sorted(groups.get(g, ()), key=lambda u: -meta(u)[1])[:60]
            if xs: body += f'<h3>{GROUP[g]}</h3><ul class="xl">' + "".join(f"<li>{a(u)}</li>" for u in xs) + "</ul>"
        if body: blocks[parent] += f'<section class="sec xlinks"><div class="sec-head"><h2>Narrow down {html.escape(low(title))}</h2></div>{body}</section>'
    for u, ps in up.items():                            # narrow page: up to its broader pages, across to its neighbours
        if not ps: continue
        ups = [p for p, _ in ps]
        first, group = ps[0]
        sib = sorted((x for x in down[first][group] if x != u), key=lambda x: -meta(x)[1])[:12]
        body = '<ul class="xl">' + "".join(f"<li>{a(p)}</li>" for p in ups) + "</ul>"
        if sib: body += f'<h3>Next to it</h3><ul class="xl">' + "".join(f"<li>{a(x)}</li>" for x in sib) + "</ul>"
        blocks[u] += f'<section class="sec xlinks"><div class="sec-head"><h2>More like {html.escape(meta(u)[0])}</h2></div>{body}</section>'
    done = 0
    for u, block in blocks.items():
        f = site / u / "index.html"
        if not f.exists(): continue
        t = f.read_text(encoding="utf-8")
        i = t.rfind("<footer")
        if i < 0 or 'class="sec xlinks"' in t: continue
        j = t.rfind("</main>", 0, i)                     # inside the page's main content when there is a <main>
        at = j if j >= 0 else i
        f.write_text(t[:at] + block + t[at:], encoding="utf-8")
        done += 1
    return done, sum(len(ps) for ps in up.values())
