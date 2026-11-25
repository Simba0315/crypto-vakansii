"""“Jobs for …” pages: the kinds of work that fit an audience or follow from a degree, counted from today’s postings (/jobs-for/).

People search "jobs for introverts", "jobs without a degree", "what can you do with a psychology degree". The articles that answer
(Indeed, The Muse, FlexJobs) list job titles from memory. Each page here names 8 to 14 kinds of work that exist on this site as role
pages and shows, for each, what the build counts today: open jobs, median advertised pay, the share that is remote and the openings
for beginners. The reason a kind of work fits is written once; every figure is recounted on every build.

Each entry: slug, group ("who" or "degree"), name (the breadcrumb), tile (the hub), title (60 characters or fewer), desc (with {n}
open jobs and {k} kinds of work), h1, lead (two sentences), roles [(role slug, why it fits)], check (what to check before applying),
faq [(question, answer)], more [(path, label)], and optionally note (a plain caveat shown first) and extra (more columns: EXTRA).
An answer may hold {TOP}, {PAY}, {REMOTE}, {ENTRY}, {EXTRA}, {N} and {K}: sentences and numbers written from the day's figures
(an empty string when the day has no such figure), so no number in an answer is typed by hand.

Rules: a kind of work is shown only when its role page exists today (it is in by_role), a page is built only when MIN_ROLES of them
do, a related link is shown only when its page exists. No page makes a health claim or singles out a protected characteristic.
Degree pages say first that postings rarely name a degree subject. Run `python3 jobs_for_pages.py` after any edit: it tests the entries.

build.py calls figures() for every entry, then render() and head_ld() for each page that has figures, and hub() for /jobs-for/.
"""
import re

PUBLISHED = "2026-11-17"
MIN_ROLES = 5        # a page needs this many of its kinds of work to have a role page today
PAY_MIN = 15         # postings that state a yearly US-dollar range before a median is shown (5 gave odd medians: $277K from 6 postings)
TEXT_MIN = 20        # postings held in full before a share of them is shown

GROUPS = (("who", "By person or situation", "By situation", "The number on a tile is the jobs open today in the kinds of work on that page."),
          ("degree", "By degree", "By degree", "Postings rarely name a degree subject, so each page lists the kinds of work graduates commonly move into."))
HUB_TITLE = "Jobs for…: Lists by Situation and by Degree, Counted Today"
HUB_DESC = "{k} lists of jobs by situation and by degree, counted from {n} open postings: kinds of work that fit, open jobs, median pay and remote share."
HUB_H1 = "Jobs for…"
HUB_LEAD = ("Articles that answer “jobs for introverts” or “what can you do with a history degree” list job titles from memory and never say whether anyone is hiring. "
            "Each list here is counted from today’s open postings: the kinds of work that fit, how many jobs are open in each, the median advertised pay, "
            "the share that is remote and the openings for beginners.")

# More columns for the pages that need one. A counted column tests each posting; a share column reads the full text of the postings
# that have one (each posting once, one pattern) and shows a share only when TEXT_MIN of them do.
EXTRA = {
    "nodegree": {"th": "Say no degree is needed", "test": lambda j, ctx: "No degree required" in j.get("perks", []),
                 "sum": "say in the posting that a degree is not required or that equivalent experience counts",
                 "note": "Say no degree is needed: the posting says a degree is not required, or accepts equivalent experience in its place."},
    "parttime": {"th": "Part-time", "test": lambda j, ctx: j.get("etype") == "Part-time",
                 "sum": "are marked part-time by the employer",
                 "note": "Part-time: postings the employer marks as part-time. Many postings do not state the hours, so the real number may be higher."},
    "anywhere": {"th": "Open to any country", "test": lambda j, ctx: bool(j.get("anywhere") and j.get("remote")),
                 "sum": "are remote and name no country or region",
                 "note": "Open to any country: remote postings that name no country or region."},
    "night": {"th": "Evening or night shifts", "needs": "night", "test": lambda j, ctx: j["id"] in ctx["night"],
              "sum": "name an evening or night shift",
              "note": "Evening or night shifts: the title or the summary of the posting names a night, overnight, evening, second or third shift."},
    "oncall": {"th": "Mention on-call or quotas", "rx": re.compile(r"\bon[- ]call\b|\bquotas?\b", re.I),
               "sum": "mention on-call duty or a quota",
               "note": f"Mention on-call or quotas: the share of postings held here in full whose text has the words “on-call” or “quota”, whatever it says about them; a dash means fewer than {TEXT_MIN} are held in full."},
    "travel": {"th": "Mention travel", "rx": re.compile(r"\btravel", re.I),
               "sum": "mention travel",
               "note": f"Mention travel: the share of postings held here in full whose text has the word “travel”, whatever it says about it; a dash means fewer than {TEXT_MIN} are held in full."},
}
TOKENS = ("{TOP}", "{PAY}", "{REMOTE}", "{ENTRY}", "{EXTRA}", "{N}", "{K}")
# What the postings of a page ask for (plan item 1.31, 20 Nov 2026: the pages said why each kind of work fits and had no list of the
# qualities it needs). Not written from memory: the skills employers name most in these postings, and the share of the postings held
# in full that use the usual words for each workplace quality.
QUALITIES = (("Clear communication", re.compile(r"communication skills|written and verbal|verbal and written|communicat(?:e|es|ing) (?:clearly|effectively)", re.I)),
             ("Working in a team", re.compile(r"collaborat|teamwork|team player", re.I)),
             ("Solving problems", re.compile(r"problem[- ]solv", re.I)),
             ("Attention to detail", re.compile(r"attention to detail|detail[- ]oriented", re.I)),
             ("Serving customers", re.compile(r"customer service", re.I)),
             ("Organizing your own time", re.compile(r"time management|prioriti[sz]|self[- ]starter|independently", re.I)),
             ("Leading others", re.compile(r"leadership", re.I)),
             ("Coping with pace and change", re.compile(r"fast[- ]paced|adaptab", re.I)))

ENTRIES = []


def _and(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


_BIT = {}


def _hit(rx, j):
    """Does a posting's full text match rx? Remembered on the posting as two bit masks (checked, matched), one bit per pattern: the 53
    pages share kinds of work, so the same pattern ran over the same long texts again and again ("Jobs for" was the slowest stage of
    the build, 32 s of the local sample; 24 Nov 2026)."""
    b = _BIT.setdefault(rx.pattern, 1 << len(_BIT))
    if not j.get("_rxc", 0) & b:
        j["_rxc"] = j.get("_rxc", 0) | b
        if rx.search(j["desc"]): j["_rxh"] = j.get("_rxh", 0) | b
    return bool(j.get("_rxh", 0) & b)


def figures(a, by_role, money, median, rlow=lambda s: s, ctx=None):
    """Today's numbers for one entry, or None when fewer than MIN_ROLES of its kinds of work have a role page today.
    by_role: {role slug: (name, [open jobs])} from build.py; ctx: {"night": ids of the jobs on the night-shift list}."""
    ctx = ctx or {}
    extras = [k for k in a.get("extra", ()) if not EXTRA[k].get("needs") or ctx.get(EXTRA[k]["needs"])]
    mid = lambda j: (j["usd"][0] + j["usd"][1]) / 2
    def count(k, js):                                   # (postings that match, postings that could be read)
        x = EXTRA[k]
        if "rx" in x:
            full = [j for j in js if j.get("desc")]
            return sum(1 for j in full if _hit(x["rx"], j)), len(full)
        return sum(1 for j in js if x["test"](j, ctx)), len(js)
    cell = lambda k, hit, of: (f"{round(100 * hit / of)}%" if of >= TEXT_MIN else "–") if "rx" in EXTRA[k] else f"{hit:,}"
    rows, seen, union = [], set(), []
    for slug, why in a["roles"]:
        if slug not in by_role: continue
        name, js = by_role[slug]
        if not js: continue
        mids = [mid(j) for j in js if j.get("usd")]
        med = median(mids) if len(mids) >= PAY_MIN else None
        rows.append({"slug": slug, "name": name, "why": why, "n": len(js), "med": med, "pay": money(med) if med is not None else "–",
                     "remote": round(100 * sum(1 for j in js if j.get("remote")) / len(js)), "entry": sum(1 for j in js if j.get("entry")),
                     "cells": [cell(k, *count(k, js)) for k in extras]})
        for j in js:                                    # a posting can sit in two kinds of work: the totals count it once
            if j["id"] not in seen: seen.add(j["id"]); union.append(j)
    if len(rows) < MIN_ROLES: return None
    rows.sort(key=lambda r: (-r["n"], r["name"]))
    n, mids = len(union), [mid(j) for j in union if j.get("usd")]
    remote, entry = round(100 * sum(1 for j in union if j.get("remote")) / n), sum(1 for j in union if j.get("entry"))
    line = f"{n:,} jobs are open today in these {len(rows)} kinds of work. {remote}% of them are remote and {entry:,} have a junior or intern title."
    # the same figures for the row of numbers of the page (sections review, batch 4): the count stays a sentence, the rest stand in the row
    head = f"{n:,} jobs are open today in these {len(rows)} kinds of work."
    cells = [(f"{remote}%", "of them are remote"), (f"{entry:,}", "have a junior or intern title")]
    if len(mids) >= PAY_MIN:
        cells.append((money(median(mids)), f"median advertised pay, from the {len(mids):,} that state a yearly range in US dollars"))
        line += f" The {len(mids):,} that state a yearly range in US dollars advertise a median of {money(median(mids))}."
    more = []
    for k in extras:
        hit, of = count(k, union)
        if "rx" in EXTRA[k]:
            if of: more.append(f"Of the {of:,} of these postings held here in full, {hit:,} ({round(100 * hit / of)}%) {EXTRA[k]['sum']}.")
        else:
            more.append(f"{hit:,} of the {n:,} open jobs {EXTRA[k]['sum']}.")
    paid = [r for r in rows if r["med"] is not None]
    best = max(paid, key=lambda r: r["med"]) if paid else None
    rem, ent = max(rows, key=lambda r: r["remote"]), max(rows, key=lambda r: r["entry"])
    tokens = {"{N}": f"{n:,}", "{K}": str(len(rows)),
              "{TOP}": "By open jobs today the largest are " + _and(f"{rlow(r['name'])} ({r['n']:,})" for r in rows[:3]) + ".",
              "{PAY}": f"The highest median advertised pay among them today is {best['pay']}, for {rlow(best['name'])} postings." if best else "",
              "{REMOTE}": f"The largest remote share today is {rem['remote']}%, in {rlow(rem['name'])} postings." if rem["remote"] else "",
              "{ENTRY}": f"The most openings with a junior or intern title today are in {rlow(ent['name'])} ({ent['entry']:,})." if ent["entry"] else "",
              "{EXTRA}": " ".join(more)}
    tags = {}
    for j in union:
        for t in j.get("tags") or ():
            tags[t] = tags.get(t, 0) + 1
    skills = [(t, k) for t, k in sorted(tags.items(), key=lambda x: (-x[1], x[0]))[:10] if k >= 5]
    full = [j for j in union if j.get("desc")]
    quals = sorted(((nm, round(100 * sum(1 for j in full if _hit(rx, j)) / len(full))) for nm, rx in QUALITIES), key=lambda x: -x[1]) if len(full) >= TEXT_MIN else []
    return {"rows": rows, "k": len(rows), "n": n, "line": line + ("" if not more else " " + " ".join(more)), "extras": extras, "tokens": tokens,
            "head": head + ("" if not more else " " + " ".join(more)), "cells": cells, "skills": skills, "quals": [q for q in quals if q[1] >= 5][:6], "full": len(full)}


def fill(text, fig):
    """A text with its tokens replaced by the day's sentences and numbers."""
    for k, v in fig["tokens"].items(): text = text.replace(k, v)
    return " ".join(text.split())


def desc(a, fig):
    return a["desc"].replace("{n}", f"{fig['n']:,}").replace("{k}", str(fig["k"]))


def faq(a, fig):
    return [(q, fill(x, fig)) for q, x in a["faq"]]


def note_of(a):
    if a.get("note"): return a["note"]
    if a["group"] == "degree":
        return (f"Postings rarely name a degree subject, so this is not a list of jobs that require {a['about']}. "
                "It lists kinds of work that graduates of this subject commonly move into; the figures are for the work, whatever degree the people doing it hold.")
    return ""


def render(a, fig, e, P, when, have, n_all, nums=None):
    """The page below the breadcrumb. when: the build's date in words; have: the addresses that exist; n_all: every open job;
    nums: build.py's row of numbers (without it the figures stay one paragraph, as they were before the sections review)."""
    label = next(g[2] for g in GROUPS if g[0] == a["group"])
    h = (f'<article class="guide"><h1>{e(a["h1"])}{"" if a["h1"].endswith("?") else ":"} <span class="hl">{fig["k"]} kinds of work open today</span></h1>'
         f'<p class="stamp">{label} · figures recounted {when} from <b>{n_all:,}</b> open jobs · <a href="{P}/methodology/">how they are made</a></p>'
         f'<p class="lead"><b>Short answer:</b> {e(short_answer(a, fig))}</p><p class="lead">{e(a["lead"])}</p>')
    if note_of(a): h += f'<div class="adv-short"><p>{e(note_of(a))}</p></div>'
    # 26 Nov 2026, ChatGPT (temporary chat, search on) "best jobs for introverts that pay well": its table is the national median of each
    # job (BLS, May 2025), and it names this site among the places to search. The government median beside the advertised one, where
    # this site matches the kind of work to an occupation the BLS counts.
    import bls_wages
    gov = lambda slug: (bls_wages.OCC.get(bls_wages.ROLE.get(slug, "")) or (None, 0, 0, None))[3]
    has_gov = sum(1 for r in fig["rows"] if gov(r["slug"])) >= 3
    ths = ["Open jobs", "Median advertised pay"] + (["US median pay (government)"] if has_gov else []) + ["Remote", "For beginners"] + [EXTRA[k]["th"] for k in fig["extras"]]
    top = fig["rows"][0]["n"]
    def tr(r):
        cells = ([f'<span class="bar"><i style="width:{max(3, round(100 * r["n"] / top))}%"></i></span>{r["n"]:,}', r["pay"]] + ([f'${gov(r["slug"]):,}' if gov(r["slug"]) else "–"] if has_gov else [])
                 + [f'{r["remote"]}%', f'{r["entry"]:,}'] + r["cells"])
        return (f'<tr><th scope="row"><a href="{P}/roles/{r["slug"]}/">{e(r["name"])}</a><span>{e(r["why"])}</span></th>'
                + "".join(f'<td data-l="{t}">{c}</td>' for t, c in zip(ths, cells)) + "</tr>")
    h += (f'<h2>{"Kinds of work graduates move into" if a["group"] == "degree" else "Kinds of work that fit"}, with what is open today</h2>'
          + (f'<p>{e(fig["head"])}</p>' + nums(fig["cells"], src=False) if nums else f'<p>{e(fig["line"])}</p>') +
          '<div class="tablewrap jfwrap"><table class="jft"><thead><tr><th>Kind of work</th>' + "".join(f"<th>{t}</th>" for t in ths) + "</tr></thead><tbody>"
          + "".join(tr(r) for r in fig["rows"]) + "</tbody></table></div>"
          '<p class="note">Open jobs: postings open today whose title matches that kind of work; a posting can match two, and the total above counts it once. '
          f'Median advertised pay: the median of the middle of each stated yearly US-dollar range, shown when at least {PAY_MIN} postings state one; a dash means fewer do. '
          + (f'US median pay: the US Bureau of Labor Statistics median for the occupation it counts this work under ({bls_wages.PERIOD}, all employers); a dash means it has no matching occupation. ' if has_gov else "")
          + 'Remote: the share of the postings marked remote. For beginners: postings with a junior or intern title. '
          + "".join(e(EXTRA[k]["note"]) + " " for k in fig["extras"]) + f'Counted {when} from employers’ own careers pages and recounted on every update.</p>')
    h += cuts(a, fig, e, P)
    if fig.get("skills") or fig.get("quals"):
        h += '<h2>What these postings ask for</h2>'
        if fig.get("quals"):
            h += (f'<p>In the {fig["full"]:,} of these postings held here in full, the share that names each quality in the usual words:</p><ul class="ticks">'
                  + "".join(f"<li><b>{e(nm)}</b>: {pc}% of postings</li>" for nm, pc in fig["quals"]) + "</ul>")
        if fig.get("skills"):
            h += ('<p>The skills named most often across all of them:</p><p class="rel chips">'
                  + "".join(f'<span>{e(t)} · {k:,}</span>' for t, k in fig["skills"]) + "</p>")
        h += '<p class="note">Counted from today’s postings for these kinds of work, not from a list of traits: a posting that asks for a quality in other words is not counted.</p>'
    h += '<h2>What to check before you apply</h2><ul class="ticks">' + "".join(f"<li>{e(c)}</li>" for c in a["check"]) + "</ul>"
    h += f'<h2>Questions about {e(a["about"])}</h2><dl class="qa">' + "".join(f"<div><dt>{e(q)}</dt><dd>{e(x)}</dd></div>" for q, x in faq(a, fig)) + "</dl>"
    links = [(u, t) for u, t in a["more"] if u in have] + [("jobs-for/", "All lists by situation and by degree")]
    h += '<p class="rel chips">' + "".join(f'<a href="{P}/{u}">{e(t)}</a>' for u, t in links) + "</p>"
    h += f'<div class="adv-jobs"><p>None of these is your kind of work? Search by title, skill or place.</p><a class="btn ghost" href="{P}/jobs/">Search all open jobs</a></div>'
    return h + "</article>"


def short_answer(a, fig):
    """The answer in one sentence, from the day's figures: the kinds of work with the most openings, each with its count.
    (Search and AI answers check, 18 Nov 2026: Google's and Bing's answers to "jobs for introverts" open with the names of the jobs;
    the page opened with a remark about other lists.)"""
    low = lambda nm: nm if nm[:2].isupper() else nm[0].lower() + nm[1:]             # "QA engineer" keeps its capitals
    names = _and(f"{low(r['name'])} ({r['n']:,} open" + (f", {r['pay']} median" if r["med"] is not None else "") + ")" for r in fig["rows"][:5])
    if a["group"] == "degree": return f"the kinds of work graduates of this subject commonly move into, with the most openings today, are {names}."
    return f"the kinds of work that fit and have the most openings today are {names}."


def cuts(a, fig, e, P):
    """The same kinds of work ranked three ways, the way people narrow the search ("... that pay well", "remote ...", "... with no
    experience" are related searches of nearly every "jobs for" query). Each list is shown only when it has three rows to rank."""
    rows = fig["rows"]
    li = lambda r, val: f'<li><a href="{P}/roles/{r["slug"]}/">{e(r["name"])}</a><b>{val}</b></li>'
    out = []
    paid = sorted((r for r in rows if r["med"] is not None), key=lambda r: -r["med"])[:5]
    if len(paid) >= 3:
        out.append(("That pay the most", "Median advertised pay, from postings that state a yearly range in US dollars.", "".join(li(r, r["pay"]) for r in paid)))
    rem = sorted((r for r in rows if r["remote"] and r["n"] >= 20), key=lambda r: -r["remote"])[:5]
    if len(rem) >= 3:
        out.append(("That are remote most often", "The share of today’s postings marked remote.", "".join(li(r, f'{r["remote"]}%') for r in rem)))
    ent = sorted((r for r in rows if r["entry"]), key=lambda r: -r["entry"])[:5]
    if len(ent) >= 3:
        out.append(("With the most openings for beginners", "Postings with a junior or intern title, open today.", "".join(li(r, f'{r["entry"]:,}') for r in ent)))
    if not out: return ""
    return ('<h2>The same kinds of work, ranked three ways</h2><div class="jfcuts">'
            + "".join(f'<div class="jfcut"><h3>{t}</h3><p>{d}</p><ol>{lis}</ol></div>' for t, d, lis in out) + "</div>")


def page_title(a, fig):
    """The title with the count of kinds of work in front, as the first results write it ("24 Fulfilling Jobs for Introverts",
    "12 best jobs for introverts"). Degree pages keep their question."""
    t = a["title"]
    return t if a["group"] == "degree" or t[0].isdigit() or t.startswith(("What ", "How ")) else f"{fig['k']} {t}"


def head_ld(a, fig, json, site, full, today):
    """Article and FAQPage markup for one page; the questions are the ones shown on it, word for word."""
    dump = lambda d: '<script type="application/ld+json">' + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + "</script>"
    url = f"{full}/jobs-for/{a['slug']}/"
    return (dump({"@context": "https://schema.org", "@type": "Article", "headline": page_title(a, fig), "description": desc(a, fig), "datePublished": PUBLISHED, "dateModified": today,
                  "author": {"@type": "Organization", "name": site, "url": full + "/about/"},
                  "publisher": {"@type": "Organization", "name": site, "logo": {"@type": "ImageObject", "url": full + "/og.jpg"}},
                  "mainEntityOfPage": url, "image": full + "/og.jpg"})
            + dump({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": x}} for q, x in faq(a, fig)]}))


def hub(figs, tile, section, e, P, when, n_all, nums=None):
    """/jobs-for/ below the breadcrumb: both groups as tiles, each with the jobs open today in its kinds of work."""
    k = len(figs)
    h = (f'<h1>{e(HUB_H1)} <span class="hl">{k} lists, counted from today’s postings</span></h1><p class="lead">{e(HUB_LEAD)}</p>')
    if nums:
        big = max(figs, key=lambda s: figs[s]["n"])
        h += nums([(str(sum(1 for a in ENTRIES if a["group"] == g and a["slug"] in figs)), e("lists " + title[0].lower() + title[1:])) for g, title, _, _ in GROUPS]
                  + [(f"{n_all:,}", "open jobs the lists are counted from"),
                     (f"{figs[big]['n']:,}", "jobs in the largest list: " + e(next(a["tile"] for a in ENTRIES if a["slug"] == big)).lower())])
    for g, title, _, sub in GROUPS:
        items = [a for a in ENTRIES if a["group"] == g and a["slug"] in figs]
        if g == "degree": items.sort(key=lambda a: a["tile"])
        if items:
            two = f"By [[{title[3:]}]]" if nums and title.startswith("By ") else title      # the two-weight headline of a labelled section
            h += section(two, '<ul class="tiles">' + "".join(tile(f"jobs-for/{a['slug']}/", a["tile"], figs[a["slug"]]["n"]) for a in items) + "</ul>", sub=sub,
                         **({"label": f"{len(items)} lists"} if nums else {}))
    return h + (f'<p class="note">Counted {when} from {n_all:,} open jobs read from employers’ own careers pages. A list appears only when at least {MIN_ROLES} of its kinds of work '
                f'have open jobs today. Not sure where you fit: take the <a href="{P}/career-quiz/">career quiz</a>, or browse every kind of work in the '
                f'<a href="{P}/categories/">categories</a>.</p>')


def _who(slug, name, title, desc_, h1, lead, roles, check, faq_, more, **kw):
    ENTRIES.append({"slug": slug, "group": "who", "name": name, "tile": name, "title": title, "desc": desc_, "h1": h1, "about": h1[0].lower() + h1[1:],
                    "lead": lead, "roles": roles, "check": check, "faq": faq_, "more": more, **kw})


def _degree(slug, subject, lead, roles, check, faq_, more, an=False):
    """A degree page. The title, the headline, the description and the caveat follow one pattern; the subject and the content differ."""
    art, cap = ("an" if an else "a"), subject.title()
    title = f"What Can You Do With {art} {cap} Degree? Jobs Open Today"
    if len(title) > 60: title = f"What Can You Do With {art} {cap} Degree?"
    start = f"What you can do with {art} {subject} degree: "
    for tail in ("{k} kinds of work graduates commonly move into, with {n} jobs open today, median advertised pay and remote share.",
                 "{k} kinds of work graduates move into, {n} jobs open today, with median advertised pay and remote share.",
                 "{k} kinds of work graduates move into, with {n} jobs open today, pay and remote share."):
        if len((start + tail).replace("{k}", "14").replace("{n}", "123,456")) <= 158: break
    ENTRIES.append({"slug": slug, "group": "degree", "name": f"{subject[0].upper() + subject[1:]} degree", "tile": subject[0].upper() + subject[1:], "title": title,
                    "desc": start + tail, "h1": f"What can you do with {art} {subject} degree?", "about": f"{art} {subject} degree",
                    "lead": lead, "roles": roles, "check": check, "faq": faq_, "more": more})


# ---------------------------------------------------------------- by person or situation ----------------------------------------------------------------
_who("introverts", "Introverts", "Jobs for Introverts: Kinds of Work, Pay and Openings Today",
     "Jobs for introverts, counted from {n} open postings: {k} kinds of work with long stretches of focused time, each with today’s openings, pay and remote share.",
     "Jobs for introverts",
     "Lists of jobs for introverts are usually written from memory and never say whether anyone is hiring. "
     "This one names kinds of work where most of the day goes to a task rather than to conversation, and counts what is open in each today.",
     [("software-engineer", "Long blocks of writing and reading code; most discussion happens in written reviews and a short daily check-in."),
      ("backend-engineer", "Work on servers and databases that users never see, so there is little contact with clients."),
      ("data-engineer", "Building and repairing data pipelines is detailed, solitary work for a small group of colleagues."),
      ("data-analyst", "Most of the day goes to queries, spreadsheets and charts; the talking is a short readout of what you found."),
      ("qa-engineer", "Testing rewards patience and attention, and findings are filed in writing as bug reports."),
      ("technical-writer", "Documentation is written alone, after short interviews with the people who built the product."),
      ("content-writer", "Research and drafting fill most of the week; feedback usually arrives as comments on the text."),
      ("accounting", "Reconciling accounts and closing the books is quiet, rule-based work, with busy weeks at month end."),
      ("financial-analyst", "Models and forecasts are built alone and presented a few times a month."),
      ("graphic-designer", "Design is done heads-down from a written brief, with reviews at set points."),
      ("research-scientist", "Experiments, reading and writing papers: deep work is the normal mode."),
      ("system-administrator", "Keeping servers and accounts running is work with systems; requests arrive as tickets."),
      ("lab-technician", "Bench work that follows a protocol, with a small team nearby."),
      ("paralegal", "Document review, filing and research for lawyers, most of it done at a desk on your own.")],
     ["Count the words “client-facing”, “stakeholders” and “cross-functional” in the posting: the more of them, the more of the week is meetings.",
      "Remote is not the same as quiet. Some remote teams spend the day on video calls, so ask how many hours of meetings a normal week has.",
      "Ask how work is handed over: in writing, or in meetings. The answer tells you more than the job title.",
      "Every one of these jobs still asks you to speak up sometimes: a review, a question, a readout. Check that the amount in the posting is one you can live with."],
     [("What jobs are good for introverts?", "Work where most of the day goes to a task and results are shared in writing: programming, analysis, testing, writing, accounting, design and lab work. {TOP}"),
      ("Which jobs for introverts pay the most?", "Advertised pay follows the kind of work and the level, not how quiet the job is. {PAY} The table shows a median for every kind of work where at least five postings state a yearly range."),
      ("Can introverts work remotely?", "Yes, and several of these kinds of work are often remote. {REMOTE} Remote teams still meet by video, so ask how many hours of calls a normal week has."),
      ("Are there jobs for introverts with no experience?", "Some. {ENTRY} Postings with a junior or intern title are counted in the For beginners column, and the entry-level list holds every such job on the site."),
      ("Do introverts have to avoid sales and support jobs?", "No. Many quiet people do well in written support, or in account work with a few long-term customers. This page only picks kinds of work where talking is a small part of the day.")],
     (("jobs-for/working-alone/", "Jobs for people who like working alone"), ("remote/", "Remote jobs"), ("career-quiz/", "Career quiz: which kind of work fits you"),
      ("guides/how-to-read-a-job-posting/", "How to read a job posting")))

_who("extroverts", "Extroverts", "Jobs for Extroverts: Kinds of Work, Pay and Openings Today",
     "Jobs for extroverts, counted from {n} open postings: {k} kinds of work built on talking with people, each with today’s openings, pay and remote share.",
     "Jobs for extroverts",
     "A job that keeps you alone at a screen all day wears some people down. "
     "These are kinds of work where talking with customers, candidates or a room is the job itself, with what is open in each today.",
     [("account-executive", "The day is calls, demos and negotiations with buyers, and the result is a signed deal."),
      ("sales-development", "Dozens of first conversations a week with people who have not heard of the product yet."),
      ("sales-representative", "Selling directly to customers, by phone, online or in person."),
      ("account-manager", "Long relationships with existing customers: regular calls, visits and renewals."),
      ("customer-success-manager", "You are the customer’s main contact after the sale and talk with them every week."),
      ("business-development", "Meeting other companies and working out deals with them."),
      ("partner-manager", "Keeping partner companies close: joint plans, calls and events."),
      ("recruiter", "Calls and interviews with candidates all day, and constant talk with the managers who hire."),
      ("events", "Running conferences and meetups, where the work happens in a crowd."),
      ("field-marketing", "Marketing done in person: local events, dinners and trade-show stands."),
      ("community-manager", "Keeping a product’s users talking, online and at events."),
      ("training", "Teaching groups of employees or customers, in a room or on a call."),
      ("communications", "Speaking for the company to journalists, staff and the public."),
      ("retail-sales-associate", "On the shop floor, helping one customer after another.")],
     ["Much of this work is paid partly by results. Read the posting for “OTE”, “commission” or “quota” and ask what share of the pay is fixed.",
      "Remote sales and success jobs replace rooms with video calls. If you want people around you, look at the place and the office days, not only the title.",
      "Ask how many customers or candidates one person looks after: it decides whether the talking is deep or rushed.",
      "Travel is common in field sales, events and partner work. The posting usually says how much."],
     [("What jobs are good for extroverts?", "Work where conversation is the job: sales, account management, customer success, recruiting, events, training and communications. {TOP}"),
      ("Which jobs for extroverts pay the most?", "In sales, part of the pay depends on results, so a posted range may be pay at target. {PAY} Check which of the two a posting states."),
      ("Are there remote jobs for extroverts?", "Yes. {REMOTE} In a remote sales or success job the contact is by video and phone, so the day is still full of people, only not in the same room."),
      ("What entry-level jobs suit extroverts?", "Sales development is the usual first step into sales, and retail and recruiting coordination take beginners too. {ENTRY}")],
     (("jobs-for/helping-others/", "Jobs for people who like helping others"), ("categories/sales/", "Sales jobs by kind of work"), ("career-quiz/", "Career quiz: which kind of work fits you"),
      ("guides/tell-me-about-yourself/", "How to answer “Tell me about yourself”")))

_who("working-alone", "People who like working alone", "Jobs Where You Work Alone: Kinds of Work Open Today",
     "Jobs where you work alone, counted from {n} open postings: {k} kinds of work done on your own, at a desk, a bench or on the road, with pay and openings.",
     "Jobs where you work alone",
     "Some people do their best work when nobody is waiting for them in a meeting. "
     "These are kinds of work where one person owns a task from start to finish, with what is open in each today.",
     [("backend-engineer", "A task is taken, built and tested by one person; contact with others is mostly written review."),
      ("data-engineer", "Pipelines are built and repaired alone, often with nobody watching until the data is late."),
      ("penetration-tester", "You are given a system and a deadline, and find the weak points yourself."),
      ("technical-writer", "One writer usually owns a whole set of documents."),
      ("content-writer", "An article is researched and written by one person."),
      ("localization", "Translating and adapting text is solitary work measured by the finished page."),
      ("video-editor", "Editing is hours alone with the footage before anyone sees a cut."),
      ("field-service", "You travel to the customer’s site and fix the equipment yourself."),
      ("maintenance-technician", "Rounds, inspections and repairs are often done alone, from a work order."),
      ("machinist", "One person, one machine and one drawing until the part is right."),
      ("welder", "Under the hood there is only you and the joint."),
      ("quality-inspector", "Measuring and checking parts against a standard, one at a time."),
      ("driver-chauffeur", "Most of the shift is spent alone on the road."),
      ("delivery-driver", "A route, a vehicle and a list of stops, with short contact at each door.")],
     ["Alone does not mean unsupervised. Ask how the work is assigned and checked: tickets, work orders, a daily stand-up.",
      "Field and driving jobs are alone but not at home. The posting states the area you cover and the hours.",
      "For remote desk work, ask how many meetings a normal week has before you assume the job is solitary.",
      "Working alone also means nobody catches your mistakes early. Look for postings that describe reviews or a second check."],
     [("What jobs let you work alone?", "Jobs where one person owns a task from start to finish: backend and data engineering, security testing, writing, translation, editing, field repair, machining, welding, inspection and driving. {TOP}"),
      ("Which jobs where you work alone pay well?", "Pay follows the kind of work, not whether it is done alone. {PAY} The table shows a median wherever at least five postings state a yearly range."),
      ("Can I work alone from home?", "The desk jobs here are often remote. {REMOTE} The trades and driving jobs are done alone but on site or on the road."),
      ("Do jobs where you work alone need experience?", "Most ask for a skill you can already show, because nobody stands next to you. {ENTRY}")],
     (("jobs-for/introverts/", "Jobs for introverts"), ("remote/", "Remote jobs"), ("categories/skilled-trades/", "Skilled trades"), ("night-shift/", "Night shift jobs")))

_who("helping-others", "People who like helping others", "Jobs for People Who Like Helping Others, Open Today",
     "Jobs for people who like helping others, counted from {n} open postings: {k} kinds of work where someone is better off at the end of your day, with pay.",
     "Jobs for people who like helping others",
     "Wanting to help people is a real reason to choose a job, and it is not limited to hospitals and schools. "
     "These are kinds of work where the result of your day is a person whose problem is solved, with what is open in each today.",
     [("customer-support", "People arrive with a problem and leave with it solved."),
      ("customer-success-manager", "Your job is to make sure a customer gets what they paid for."),
      ("implementation", "You set a new customer up and teach their people to use the product."),
      ("it-support", "Colleagues come to you when their computer or account stops working."),
      ("help-desk", "The first person people call when something technical breaks."),
      ("nursing", "Caring for patients, in person or by video, and coordinating their treatment."),
      ("nurse-practitioner", "Examining and treating patients, with an advanced nursing license."),
      ("care-coordinator", "Guiding patients through appointments, insurance and follow-ups."),
      ("healthcare", "Treating patients or supporting those who do, at clinics and health companies."),
      ("mental-health", "Therapists and counselors who work with clients, often online; these roles need a license."),
      ("education", "Teaching, tutoring and building lessons that other people learn from."),
      ("corporate-trainer", "Teaching employees new skills in workshops and courses."),
      ("human-resources", "Employees bring you their questions about contracts, leave and disputes."),
      ("recruiter", "Helping a person find a job and a team find a colleague.")],
     ["Clinical and counseling roles need a license, and the posting names it. Check it against the state or country you are licensed in.",
      "Helping all day is tiring. Ask about caseload, ticket volume or patients per shift before you accept.",
      "Support and care jobs often run in shifts, including evenings and weekends. The posting usually states the schedule.",
      "Look at how the work is measured. A support team judged only on speed helps differently from one judged on whether the problem stayed solved."],
     [("What jobs are there for people who like helping others?", "Support, customer success, IT help, nursing and care coordination, counseling, teaching, training, HR and recruiting. {TOP}"),
      ("Which helping jobs do not need a medical degree?", "Customer support, customer success, implementation, IT support, help desk, training, HR and recruiting do not. Nursing, nurse practitioner and therapy roles need a license, which the posting names."),
      ("Do jobs that help people pay well?", "It depends on the kind of work more than on the helping. {PAY} The table shows a median wherever at least five postings state a yearly range."),
      ("Can I help people in a remote job?", "Yes. Support, success and care coordination are often done by phone, chat and video. {REMOTE}"),
      ("What helping jobs take beginners?", "Customer support and help desk are common first jobs. {ENTRY}")],
     (("jobs-for/extroverts/", "Jobs for extroverts"), ("categories/customer-service/", "Customer service jobs"), ("categories/science-healthcare/", "Science and healthcare jobs"),
      ("career-quiz/", "Career quiz: which kind of work fits you")))

_who("people-who-like-math", "People who like math", "Jobs for People Who Like Math: Pay and Openings Today",
     "Jobs for people who like math, counted from {n} open postings: {k} kinds of work where the day is numbers and models, with today’s openings and pay.",
     "Jobs for people who like math",
     "Liking math at school rarely comes with advice on what to do with it besides teaching. "
     "These are kinds of work where calculating, modeling and proving things with numbers is the daily job, with what is open in each today.",
     [("data-scientist", "Statistics and models used to answer a business question with data."),
      ("data-analyst", "Counting, comparing and charting until the numbers say something clear."),
      ("statistician", "Designing studies and judging what a sample can and cannot prove."),
      ("actuary", "Pricing risk with probability, and passing professional exams along the way."),
      ("quant", "Math and code used to test trading strategies or price risk."),
      ("machine-learning-engineer", "Linear algebra, probability and optimization turned into working software."),
      ("financial-analyst", "Forecasts and budgets built in models, checked against what really happened."),
      ("pricing", "Working out what to charge and how demand reacts."),
      ("economist", "Measuring how prices, wages and policies move behavior."),
      ("experimentation", "Running tests and proving that a change caused the result."),
      ("analytics-engineer", "Turning raw tables into clean, trusted numbers for everyone else."),
      ("risk-manager", "Estimating what could go wrong and how much it would cost."),
      ("simulation-engineer", "Building numerical models of machines before anything is built."),
      ("cryptographer", "Applied number theory: designing and checking the math that keeps data secret.")],
     ["Check which math the posting names: statistics, probability, linear algebra and optimization lead to different jobs.",
      "Most of these roles ask for code next to the math, usually SQL and Python. The skills list in the posting tells you which.",
      "Actuarial and some quantitative roles expect exams or a graduate degree. The posting says so near the top of its requirements.",
      "Ask what share of the week is modeling and what share is cleaning data and explaining results."],
     [("What jobs can I get if I like math?", "Data science and analysis, statistics, actuarial work, quantitative research, machine learning, financial analysis, pricing and risk. {TOP}"),
      ("Which math jobs pay the most?", "Pay differs by kind of work and by level. {PAY} Research and quantitative roles often ask for a graduate degree, so read the requirements together with the pay."),
      ("Do I need a math degree for these jobs?", "Postings more often ask for a quantitative degree in general, or for the skills themselves: statistics, SQL, Python. Actuaries also need professional exams."),
      ("Are there entry-level jobs for people who like math?", "Yes. Analyst roles are the usual first job, and the For beginners column counts the postings with a junior or intern title. {ENTRY}"),
      ("Can math jobs be done remotely?", "Many can, because the work is done on a computer. {REMOTE}")],
     (("jobs-for/mathematics-degree/", "What can you do with a mathematics degree?"), ("categories/data-analytics/", "Data and analytics jobs"), ("guides/highest-paying-jobs/", "The highest-paying jobs"),
      ("guides/skills-in-demand/", "Skills in demand")))

_who("people-who-like-writing", "People who like writing", "Jobs for People Who Like Writing: Openings and Pay Today",
     "Jobs for people who like writing, counted from {n} open postings: {k} kinds of work where the product is text, with today’s openings, pay and remote share.",
     "Jobs for people who like writing",
     "Advice for people who like writing usually ends at “become an author”. "
     "Companies hire writers under many other names, and these are the kinds of work where the thing you produce is text, with what is open in each today.",
     [("content-writer", "Articles, guides and web pages, written and edited to a brief."),
      ("technical-writer", "Explaining how a product works in instructions people can follow."),
      ("content-designer", "The words inside an app: buttons, errors and help text."),
      ("communications", "Statements, announcements and speeches in the company’s voice."),
      ("public-relations", "Press releases and pitches written for journalists."),
      ("internal-communications", "News and explanations written for the company’s own staff."),
      ("social-media", "Short posts written every day, in a voice people recognize."),
      ("product-marketing", "Describing what a product does and why it matters, on pages and in launch notes."),
      ("seo", "Writing and editing pages so that people searching can find them."),
      ("proposal-manager", "Long written bids for contracts, built to a strict format."),
      ("medical-writer", "Study reports and regulatory documents, written to scientific standards."),
      ("localization", "Rewriting text so it reads naturally in another language."),
      ("instructional-designer", "Writing courses and lessons that teach a skill step by step."),
      ("policy", "Position papers and letters to regulators, where each word is weighed.")],
     ["Postings for writers nearly always ask for samples. Have three pieces ready that match the kind of writing in the posting.",
      "Check what the writing is measured by: search traffic, sign-ups, support tickets avoided, bids won.",
      "Look for who edits and approves the text. A writer with five approvers writes differently from one with an editor.",
      "Medical, legal and policy writing ask for knowledge of the subject as well as style. The posting lists it."],
     [("What jobs are there for people who like writing?", "Content and technical writing, the text inside products, communications and press work, social media, marketing copy, proposals, courses and translation. {TOP}"),
      ("Which writing jobs pay the most?", "It depends on the subject and on the kind of writing. {PAY} Postings that ask for knowledge of a field, such as medicine or software, say so in their requirements."),
      ("Can I get a writing job without experience?", "A portfolio counts for more than years. {ENTRY} Three good samples that match the posting are the usual way in."),
      ("Are writing jobs remote?", "Often, since the work is a document that can be written and reviewed from anywhere. {REMOTE}"),
      ("Do writing jobs need an English degree?", "Postings rarely name one. They ask for samples, and for knowledge of the subject you would write about.")],
     (("jobs-for/english-degree/", "What can you do with an English degree?"), ("categories/writing-translation/", "Writing, editing and translation jobs"), ("guides/how-to-write-a-cover-letter/", "How to write a cover letter"),
      ("jobs-for/creative-people/", "Jobs for creative people")))

_who("working-with-your-hands", "People who like working with their hands", "Jobs Working With Your Hands: Pay and Openings Today",
     "Jobs working with your hands, counted from {n} open postings: {k} kinds of work where you build, repair or make things, with today’s openings and pay.",
     "Jobs working with your hands",
     "Not everyone wants to spend the day at a screen, and job advice written by office workers tends to forget it. "
     "These are kinds of work where you build, repair or make something you can touch, with what is open in each today.",
     [("technician", "Building, installing and repairing equipment by hand."),
      ("maintenance-technician", "Keeping machines and buildings running: inspections, repairs, replacements."),
      ("field-service", "Installing and repairing equipment at the customer’s site."),
      ("mechanic", "Diagnosing and repairing vehicles and engines."),
      ("mechanical-technician", "Assembling and testing mechanical parts from drawings."),
      ("electrical-technician", "Wiring, soldering and testing electrical assemblies."),
      ("electrician", "Installing and repairing wiring and power systems."),
      ("hvac-technician", "Installing and servicing heating, cooling and ventilation."),
      ("welder", "Joining metal to a specification that an inspector will check."),
      ("machinist", "Cutting metal parts to tight tolerances on mills and lathes."),
      ("fabrication-technician", "Cutting, forming and assembling parts in a shop."),
      ("production-worker", "Running machines and assembling products on a line."),
      ("harness-engineer", "Building the cable bundles that carry power through a vehicle or machine."),
      ("chef-cook", "Cooking to order in a kitchen, a shift at a time.")],
     ["Trades often need a license, a certificate or a completed apprenticeship. The posting names the one it wants.",
      "Check the shift. Production, maintenance and kitchen work often run evenings, nights or weekends.",
      "Many of these postings state pay by the hour, which the yearly median in the table does not count. Open the role page to see the hourly ones.",
      "Look for the physical requirements: lifting, standing, working outside or in a clean room."],
     [("What jobs let you work with your hands?", "Technician and maintenance work, field service, the trades (electrician, welder, machinist, mechanic, HVAC), production and kitchen work. {TOP}"),
      ("Which hands-on jobs pay well?", "It depends on the trade, the license and the equipment. {PAY} Hourly rates are not in this median, so open a role page to see them."),
      ("Do hands-on jobs need a degree?", "Rarely. They ask for a license, a certificate, an apprenticeship or years on the tools."),
      ("Can I start a hands-on job with no experience?", "Production work and apprenticeships take beginners and train on the job. {ENTRY}")],
     (("categories/skilled-trades/", "Skilled trades"), ("jobs-for/people-without-a-degree/", "Jobs for people without a degree"), ("perks/no-degree/", "Jobs that say no degree is required"),
      ("night-shift/", "Night shift jobs")))

_who("creative-people", "Creative people", "Jobs for Creative People: Kinds of Work and Pay Today",
     "Jobs for creative people, counted from {n} open postings: {k} kinds of work where you design, draw, film or write for a living, with openings and pay.",
     "Jobs for creative people",
     "“Do something creative” is common advice, and it does not say who will pay for it. "
     "These are kinds of work that companies pay for every day, where the job is to make something new that people see or hear, with what is open in each today.",
     [("graphic-designer", "Layouts, illustrations and brand materials, made to a brief."),
      ("brand-designer", "The look of a company: logo, colors, type and how they are used."),
      ("product-designer", "Deciding how an app looks and works, screen by screen."),
      ("ux-designer", "Working out how people move through a product, then drawing it."),
      ("motion-designer", "Animation and moving graphics for video and apps."),
      ("video-editor", "Shaping raw footage into a finished video."),
      ("art-director", "Setting the visual direction that other designers follow."),
      ("creative-director", "Leading the ideas behind campaigns and brands."),
      ("game-designer", "Inventing the rules, levels and feel of a game."),
      ("game-artist", "Drawing the characters and worlds of a game."),
      ("3d-artist", "Modeling objects, characters and scenes in three dimensions."),
      ("content-writer", "Ideas turned into articles and stories."),
      ("social-media", "A steady flow of posts, pictures and short video."),
      ("audio", "Sound design, music and recording.")],
     ["Creative postings ask for a portfolio. Put the work that matches the posting first, and say what each piece was for.",
      "Check which tools the posting names (Figma, Adobe apps, Blender and so on): the skills list is usually specific.",
      "Ask how much of the work is new ideas and how much is producing variations to a template.",
      "Agency and studio jobs come with client deadlines. In-house jobs come with one brand. The posting tells you which this is."],
     [("What jobs are there for creative people?", "Graphic, brand and product design, motion and video, art direction, game design and art, 3D, writing, social media and sound. {TOP}"),
      ("Which creative jobs pay the most?", "Pay differs by kind of work and by level. {PAY} Titles such as art director and creative director are reached after years of practice."),
      ("Can creative people work remotely?", "Often: the work travels as files, and reviews can happen on a call. {REMOTE}"),
      ("How do I get a creative job without experience?", "With a portfolio. {ENTRY} Self-started projects count if they show the kind of work the posting asks for."),
      ("Do creative jobs need an art degree?", "Postings seldom insist on one. They ask to see the work.")],
     (("jobs-for/graphic-design-degree/", "What can you do with a graphic design degree?"), ("categories/design-creative/", "Design and creative jobs"), ("jobs-for/people-who-like-writing/", "Jobs for people who like writing"),
      ("resume/examples/", "Resume examples by kind of work")))

_who("career-changers", "Career changers", "Jobs for Career Changers: Kinds of Work Open Today",
     "Jobs for career changers, counted from {n} open postings: {k} kinds of work that people enter from other fields, with today’s openings and pay.",
     "Jobs for career changers",
     "Changing careers usually means being told you lack experience in the new field. "
     "These are kinds of work that people commonly enter from somewhere else, because they lean on skills learned in any job, with what is open in each today.",
     [("sales-development", "A first sales job that hires for persistence and clear speech more than for a past title."),
      ("customer-success-manager", "Knowing an industry from the inside helps when the customers work in it."),
      ("account-manager", "Looking after customers rests on reliability and follow-up, which any client-facing job teaches."),
      ("customer-support", "The product is taught in the first weeks; patience and clear writing you bring with you."),
      ("recruiter", "People move into recruiting from sales, teaching and hospitality, and often recruit for the field they left."),
      ("project-manager", "Planning, deadlines and budgets are the same skill in any industry."),
      ("implementation", "Setting up customers suits people who know how the customer’s business runs."),
      ("operations-analyst", "Fixing a team’s daily processes draws on having worked inside one."),
      ("business-analyst", "Translating between the people who need something and the people who build it."),
      ("data-analyst", "SQL and spreadsheets can be learned in months and shown with a project."),
      ("qa-engineer", "Testing is a common first technical job for people with an eye for detail."),
      ("it-support", "Certificates and practice on your own equipment count here."),
      ("technical-writer", "Subject knowledge from a first career, plus clear writing."),
      ("ux-designer", "A portfolio of case studies is judged ahead of a design degree.")],
     ["Read the years of experience a posting asks for as “in this kind of work or a related one”, and say in your first lines which part of your past is related.",
      "Look for postings that name your old industry. A nurse applying to a health software company is not starting from zero.",
      "Entry pay in a new field can be lower than what you earn now. Compare the stated range with your budget before you apply.",
      "A project you can show beats a course certificate. Check which skills the posting names and build one small thing with them."],
     [("What are good jobs for a career change?", "Kinds of work that lean on skills from any job: sales development, customer success, support, recruiting, project management, analysis, testing and IT support. {TOP}"),
      ("Which career-change jobs pay well?", "Pay depends on the kind of work and on how much of your past counts as relevant. {PAY} A first job in a new field often sits at the low end of the posted range."),
      ("Can I change careers without going back to school?", "Often yes. Postings in these kinds of work ask for skills and examples of work more than for a specific degree. A short course and one finished project are the usual proof."),
      ("How many career-change jobs are open to beginners?", "{ENTRY} The For beginners column counts postings with a junior or intern title; many others accept experience from another field if you explain how it applies."),
      ("How do I explain a career change in an application?", "In two sentences at the top of the resume: what you did, and which part of it is the work this posting describes. Use the posting’s own words for the skills you share.")],
     (("how-to-become/", "How to become…: steps into each kind of work"), ("guides/how-to-get-a-job-with-no-experience/", "How to get a job with no experience"), ("career-quiz/", "Career quiz: which kind of work fits you"),
      ("jobs-for/former-teachers/", "Jobs for former teachers"), ("tools/resume-match/", "Check your resume against a posting")))

_who("former-teachers", "Former teachers", "Jobs for Former Teachers: Kinds of Work Open Today",
     "Jobs for former teachers, counted from {n} open postings: {k} kinds of work that use classroom skills outside a school, with today’s openings and pay.",
     "Jobs for former teachers",
     "Teachers who leave the classroom are often told that their experience does not count elsewhere. "
     "These are kinds of work that hire for what teachers already do, explaining, planning and managing a room, with what is open in each today.",
     [("instructional-designer", "Building courses and lessons, for adults and usually online."),
      ("corporate-trainer", "Teaching employees in workshops: the classroom, with a different audience."),
      ("training", "Planning how a company’s people learn, and running the programs."),
      ("customer-education", "Teaching customers to use a product through courses and webinars."),
      ("education", "Teaching, tutoring and curriculum work at education companies."),
      ("education-program-manager", "Running learning programs: content, partners, schedules and results."),
      ("sales-enablement", "Training salespeople and writing the materials they learn from."),
      ("customer-success-manager", "Guiding customers step by step toward a goal, and noticing who is falling behind."),
      ("implementation", "Onboarding new customers: explaining, training, checking they can do it alone."),
      ("project-manager", "A school year is a long project with fixed deadlines and many people to coordinate."),
      ("content-writer", "Explaining a subject clearly in writing."),
      ("technical-writer", "Instructions that a beginner can follow without asking."),
      ("human-resources", "Policies, hard conversations and paperwork, handled with care for the person."),
      ("recruiter", "Reading people, asking good questions and keeping many conversations moving.")],
     ["Translate your experience into the posting’s words: “curriculum” becomes “learning programs”, “lesson plans” become “training materials”.",
      "Instructional design postings ask for a portfolio and name the authoring tools they use. One sample course is enough to start.",
      "Check whether the role teaches children, adults or customers; the title “trainer” covers all three.",
      "Compare the yearly pay and the days off with your current contract: most company jobs have no summer break."],
     [("What jobs can former teachers do?", "Instructional design, corporate training, customer education, education programs, customer success, onboarding, project management, writing, HR and recruiting. {TOP}"),
      ("Which jobs for former teachers pay more than teaching?", "We do not know what you earn now, so compare for yourself. {PAY} The table shows a median for every kind of work where at least five postings state a yearly range."),
      ("Do I need a new degree to leave teaching?", "Usually not. These kinds of work ask for examples: a sample course, a writing sample, a project you ran. A short course in the tools a posting names is often enough."),
      ("Can former teachers work from home?", "Instructional design, customer education and writing are often remote. {REMOTE}"),
      ("How do I write a resume after teaching?", "Lead with results in numbers: how many learners, what improved, what you built. Replace school terms with the posting’s terms, and put the tools you used near the top.")],
     (("jobs-for/education-degree/", "What can you do with an education degree?"), ("jobs-for/career-changers/", "Jobs for career changers"), ("how-to-become/", "How to become…: steps into each kind of work"),
      ("categories/education-training/", "Education and training jobs"), ("tools/resume-match/", "Check your resume against a posting")))

_who("nurses-leaving-bedside", "Nurses leaving bedside care", "Non-Bedside Nursing Jobs: Kinds of Work Open Today",
     "Jobs for nurses leaving bedside care, counted from {n} open postings: {k} kinds of work that use a nursing background away from the ward, with pay.",
     "Jobs for nurses leaving bedside care",
     "Nurses who want to leave the ward are rarely shown where else their training is wanted. "
     "These are kinds of work that use clinical knowledge away from the bedside, several of them by phone or video, with what is open in each today.",
     [("care-coordinator", "Guiding patients through appointments, insurance and follow-ups, usually by phone."),
      ("nursing", "Not every nursing posting is a ward shift: telehealth, triage and case review are posted under the same name."),
      ("healthcare", "Clinical roles at health companies, where the patient is often on a screen."),
      ("nurse-practitioner", "With an advanced license you examine and treat patients, in clinics or online."),
      ("clinical-research", "Running the studies that test whether a treatment works and is safe."),
      ("clinical-research-coordinator", "Looking after the patients and the paperwork of a clinical study."),
      ("clinical-informatics", "Shaping the software clinicians use, and checking that it is safe."),
      ("medical-coder", "Turning clinical notes into the codes that insurers pay on."),
      ("healthcare-administrator", "Running the business side of a clinic or health service."),
      ("medical-writer", "Study reports and patient materials that have to be clinically right."),
      ("medical-science-liaison", "Discussing the evidence for a medicine with doctors; usually asks for an advanced degree."),
      ("insurance", "Claims work at insurers, where clinical knowledge helps to judge a case."),
      ("health-coach", "Helping people change habits to manage their health."),
      ("regulatory-affairs", "At health companies, dealing with the regulators that license their products.")],
     ["Some of these roles need an active nursing license and some do not. The posting says which, and for which states.",
      "Telehealth roles are licensed by the state where the patient is. Check the states the posting lists against yours.",
      "Compare total pay, not base pay: ward work often includes shift differentials that a desk job does not.",
      "Ask about the schedule and on-call duty. Leaving the bedside does not always mean leaving evenings and weekends."],
     [("What jobs can nurses do away from the bedside?", "Care coordination, telehealth and triage, clinical research, clinical informatics, medical coding, healthcare administration, medical writing and insurance review. {TOP}"),
      ("Which non-bedside nursing jobs are remote?", "Care coordination, telehealth nursing and case review are often done from home. {REMOTE}"),
      ("Do non-bedside nursing jobs pay less?", "It varies by role, and we do not know your current pay. {PAY} Compare the posted range with your total pay, shift differentials included."),
      ("Do I need a nursing license for non-clinical jobs?", "For telehealth, triage and case management, yes, and often in more than one state. For coding, writing, research coordination and administration, postings ask for clinical knowledge and may not require an active license.")],
     (("jobs-for/nursing-degree/", "What can you do with a nursing degree?"), ("categories/science-healthcare/", "Science and healthcare jobs"), ("remote/", "Remote jobs"),
      ("jobs-for/career-changers/", "Jobs for career changers")))

_who("veterans", "Veterans", "Jobs for Veterans: Kinds of Work, Pay and Openings Today",
     "Jobs for veterans, counted from {n} open postings: {k} kinds of work where military training is put to use, with today’s openings and pay.",
     "Jobs for veterans",
     "Military experience is hard for a civilian recruiter to read, and veterans are often pointed only at guard jobs. "
     "These are kinds of work where planning, logistics, maintenance and working under rules are the job, with what is open in each today.",
     [("government", "Selling to, building for or working with governments and the armed forces; some roles need a clearance."),
      ("defense", "Products and services for the armed forces, where knowing the customer from the inside counts."),
      ("industrial-security", "Handling clearances and classified information at contractors."),
      ("operations-manager", "Keeping people, processes and supplies running day to day."),
      ("program-manager", "Planning work that involves many teams and keeping it on schedule."),
      ("supply-chain", "Getting parts and products made, stored and delivered on time."),
      ("logistics-coordinator", "Moving goods and tracking them, with paperwork that has to be right."),
      ("fleet-manager", "Vehicles, maintenance, drivers and safety."),
      ("maintenance-technician", "Inspecting and repairing equipment to a schedule and a checklist."),
      ("field-service", "Repairing equipment at the customer’s site, often alone and far from the office."),
      ("cybersecurity", "Protecting systems and responding to attacks; signals and intelligence training carries over."),
      ("physical-security", "Protecting buildings, people and events."),
      ("mission-operations", "Flying satellites and spacecraft from a control room, by procedure and in shifts."),
      ("ehs", "Workplace safety: inspections, training and incident reports.")],
     ["Postings that need a security clearance say which level and whether it must be active. An active clearance belongs in the first line of your resume.",
      "Rewrite ranks and unit names as what you did: how many people, what equipment, what budget, what result.",
      "Many employers write in the posting that veterans are encouraged to apply. It is an invitation, not a guarantee, and it is not counted here.",
      "Check the certificates a posting names. Military training often covers the material, but the certificate is asked for by name."],
     [("What jobs are good for veterans?", "Work that runs on planning, logistics, maintenance, security and rules: government and defense roles, operations and program management, supply chain, field service, cybersecurity and safety. {TOP}"),
      ("Which jobs for veterans pay the most?", "Pay follows the kind of work and the level you enter at. {PAY}"),
      ("Do jobs for veterans need a security clearance?", "Some government, defense and industrial security roles do, and the posting names the level. Most operations, logistics and maintenance roles do not."),
      ("Can veterans get these jobs without a degree?", "Many postings accept experience in place of a degree, and say so. Technician, maintenance, logistics and security roles ask for training and years of practice more than for a diploma."),
      ("Are there remote jobs for veterans?", "Cybersecurity, program management and government sales are sometimes remote; hands-on work is not. {REMOTE}")],
     (("perks/no-degree/", "Jobs that say no degree is required"), ("categories/security/", "Security jobs"), ("categories/logistics-transport/", "Logistics, warehouse and transport jobs"),
      ("guides/how-to-write-a-resume/", "How to write a resume"), ("jobs-for/career-changers/", "Jobs for career changers")),
     note="No posting here is reserved for veterans, and we cannot see whom an employer prefers. The list picks kinds of work where military training and habits are commonly put to use.")

_who("college-students", "College students", "Jobs for College Students: Kinds of Work Open Today",
     "Jobs for college students, counted from {n} open postings: {k} kinds of work that fit around classes, from internships to shop and campus jobs, with pay.",
     "Jobs for college students",
     "A student needs either a job that fits around classes or one that leads to work after graduation, and most lists mix the two. "
     "These are the kinds of work that do one or the other, with what is open in each today.",
     [("intern", "Fixed-term placements during studies, with training on the job."),
      ("summer-intern", "Internships that run through the summer break."),
      ("engineering-intern", "Internships for engineering and computer science students."),
      ("retail-sales-associate", "Shop work in shifts, which can be set around a timetable."),
      ("grocery-associate", "Stocking shelves and serving customers, with evening and weekend shifts."),
      ("barista", "Shift work behind a counter, often early mornings or weekends."),
      ("hospitality", "Kitchens, restaurants and guest services, with evening hours."),
      ("warehouse-associate", "Picking and packing in shifts, nights and weekends included."),
      ("brand-ambassador", "Representing a brand on campus or at events, a few hours at a time."),
      ("chat-support", "Answering customers in writing, sometimes from home and in the evening."),
      ("call-center", "Phone support in shifts, with training provided."),
      ("marketing-coordinator", "Marketing assistant and intern roles: posts, emails, events."),
      ("delivery-driver", "Deliveries by van, car or bike, with shifts through the day and evening.")],
     ["Internship postings state the term (summer, fall, spring) and the year of study they want. Apply for the term you are free in.",
      "Check the hours before the pay. The Part-time column counts only postings the employer marks as part-time; many shift jobs do not say.",
      "International students should check the work rules of their visa before applying; a posting rarely mentions them.",
      "Large employers open summer internships many months ahead. A posting dated last fall may be for next summer."],
     [("What are good jobs for college students?", "Internships in your field, and shift work that fits around classes: retail, grocery, coffee shops, warehouses, campus brand work and written support. {TOP}"),
      ("How many jobs for college students are part-time?", "{EXTRA} Employers do not always state the hours, so shift jobs in shops, kitchens and warehouses are part-time more often than the count shows."),
      ("Do internships for college students pay?", "Many state a rate, usually by the hour or month, which the yearly median here does not count. {ENTRY} Open the internships list to see what each posting pays."),
      ("Can college students work remotely?", "Written support and some internships are remote; shop and warehouse work is not. {REMOTE}"),
      ("When should college students apply for summer internships?", "As soon as the posting appears. Each posting carries the date the employer published it, and the internships list shows the newest first.")],
     (("internships/", "Internships"), ("part-time/", "Part-time jobs"), ("entry-level/", "Entry-level jobs"), ("jobs-for/recent-graduates/", "Jobs for recent graduates"), ("summer/", "Summer jobs and internships")),
     extra=("parttime",))

_who("recent-graduates", "Recent graduates", "Jobs for Recent Graduates: Kinds of Work Open Today",
     "Jobs for recent graduates, counted from {n} open postings: {k} kinds of work that hire people straight from college, with today’s openings and pay.",
     "Jobs for recent graduates",
     "Most postings ask for experience that a new graduate cannot have. "
     "These are kinds of work where employers hire people in their first year out of college and train them, with what is open in each today.",
     [("intern", "Graduate programs and new-grad roles are posted under this name along with internships."),
      ("junior-software-engineer", "First engineering jobs, with a senior engineer reviewing your work."),
      ("associate-product-manager", "Programs that train product managers from graduation."),
      ("sales-development", "The usual first job in sales, hired for energy and trained on the product."),
      ("analyst", "A first role studying the numbers of one area: finance, risk, operations or data."),
      ("business-analyst", "Gathering what a team needs and writing it down for the people who build it."),
      ("operations-analyst", "Keeping a team’s daily processes running and finding what to fix."),
      ("data-analyst", "SQL, spreadsheets and charts, with the questions set by someone senior."),
      ("financial-analyst", "Budgets and forecasts, a common first job for finance and economics graduates."),
      ("marketing-coordinator", "Supporting a marketing team’s campaigns, posts and events."),
      ("recruiting-coordinator", "Scheduling interviews and keeping candidates informed."),
      ("customer-success-specialist", "Helping many smaller customers by email, webinar and quick calls."),
      ("consulting", "Advising clients; firms hire graduates into analyst and associate roles."),
      ("investment-banking", "Analyst classes hired from campus, with long hours and structured training.")],
     ["Look for “new grad”, “graduate program”, “associate” or a graduation year in the posting: these are opened for people with no full-time experience.",
      "Graduate programs have application windows. Check the date of the posting and apply early.",
      "“1 to 2 years of experience” often includes internships, projects and part-time work. Say so in your first lines.",
      "If you need visa sponsorship, check the posting for it before you spend an evening on the application."],
     [("What jobs can recent graduates get?", "Graduate programs, junior engineering, analyst roles, sales development, coordinator roles in marketing and recruiting, and consulting. {TOP}"),
      ("Which jobs for recent graduates pay the most?", "Advertised pay differs more by kind of work than by level. {PAY} Check whether a range is for the graduate role or for the whole job family."),
      ("How many jobs for recent graduates are open now?", "{N} jobs are open in the {K} kinds of work on this page, though not all of them are for beginners. {ENTRY}"),
      ("Do recent graduates need experience?", "Internships, projects and part-time work count as experience in a first application. Postings titled junior, graduate or associate expect little more."),
      ("Can recent graduates work remotely?", "Some first jobs are remote, though many employers want new hires near the team. {REMOTE}")],
     (("entry-level/", "Entry-level jobs"), ("internships/", "Internships"), ("guides/entry-level-jobs/", "Entry-level jobs: what the postings show"),
      ("guides/how-to-get-a-job-with-no-experience/", "How to get a job with no experience"), ("jobs-for/college-students/", "Jobs for college students")))

_who("people-with-no-experience", "People with no experience", "Jobs for People With No Experience, Open Today",
     "Jobs for people with no experience, counted from {n} open postings: {k} kinds of work that train on the job, with today’s openings, pay and remote share.",
     "Jobs for people with no experience",
     "Every posting seems to ask for experience, including the ones meant for beginners. "
     "These are kinds of work where employers commonly train new people on the job, with what is open in each today.",
     [("sales-development", "Hired for persistence and clear speech; the product and the method are taught."),
      ("customer-support", "Product training comes first; patience and clear writing are what you bring."),
      ("chat-support", "Answering customers in writing, from scripts and a knowledge base at first."),
      ("call-center", "Phone support with training before the first call."),
      ("retail-sales-associate", "Shop work learned in the first weeks."),
      ("grocery-associate", "Stocking, counters and checkout, learned on shift."),
      ("warehouse-associate", "Picking, packing and shipping, taught on site."),
      ("production-worker", "Line work with training on each machine."),
      ("barista", "Coffee and customers, taught behind the counter."),
      ("hospitality", "Kitchen and service jobs that start with the simple tasks."),
      ("delivery-driver", "A license and a clean driving record are the usual requirements."),
      ("coordinator", "Schedules, orders and paperwork: often a first office job."),
      ("apprentice", "Paid training in a trade or profession, often alongside school."),
      ("intern", "Placements built for people who have not worked in the field yet.")],
     ["“No experience” rarely means no requirements: look for a driving license, a language, a background check or the ability to lift.",
      "Check how long the training lasts and whether it is paid.",
      "Read the hours. Jobs that train beginners often run in shifts, evenings and weekends.",
      "A posting that asks you to pay for training, equipment or a background check is not a job offer. Real employers do not charge candidates."],
     [("What jobs can I get with no experience?", "Jobs that train on the job: sales development, customer support, call centers, shop and grocery work, warehouses, production lines, coffee shops, deliveries, coordinator roles and apprenticeships. {TOP}"),
      ("Which no-experience jobs pay the most?", "Pay differs by kind of work. {PAY} Many shift jobs state pay by the hour, which this yearly median does not count, so open a role page to see the hourly rates."),
      ("Are there remote jobs with no experience?", "Written support and some sales development jobs are remote; shop, warehouse and kitchen work is not. {REMOTE}"),
      ("How many jobs for beginners are open today?", "{ENTRY} That counts only postings with a junior or intern title. Many postings in these kinds of work carry no level in the title and still take beginners, so read the requirements, not only the title."),
      ("How do I apply with no experience?", "Put school projects, volunteering and any paid work, however short, where experience would go, each with one result. The guide on getting a job with no experience shows the steps.")],
     (("guides/how-to-get-a-job-with-no-experience/", "How to get a job with no experience"), ("entry-level/", "Entry-level jobs"), ("perks/no-degree/", "Jobs that say no degree is required"),
      ("jobs-for/people-without-a-degree/", "Jobs without a degree"), ("how-to-become/", "How to become…: steps into each kind of work")))

_who("people-without-a-degree", "People without a degree", "Jobs Without a Degree: Kinds of Work and Pay Today",
     "Jobs without a degree, counted from {n} open postings: {k} kinds of work and, for each, how many postings say a degree is not required, with pay.",
     "Jobs without a degree",
     "Lists of jobs without a degree name occupations, but it is the posting that decides whether a degree is asked for. "
     "This page counts, in each kind of work, the open postings that say in their own words that a degree is not required.",
     [("sales-development", "Hired on how you speak and follow up."),
      ("account-executive", "A record of closed deals is what gets you hired."),
      ("customer-support", "The product is taught; clear writing and patience are the requirements."),
      ("it-support", "Certificates and hands-on practice are what postings ask about."),
      ("help-desk", "A first IT job where troubleshooting skill is tested directly."),
      ("software-engineer", "Many postings accept equivalent experience in place of a degree; the last column shows how many say so today."),
      ("technician", "Trained on the equipment; a trade school certificate helps."),
      ("maintenance-technician", "Years on the tools and the right certificates."),
      ("field-service", "Mechanical or electrical skill, a driving license and readiness to travel."),
      ("mechanic", "Trade training and certifications rather than college."),
      ("electrician", "Licensed through an apprenticeship, not a university."),
      ("warehouse-associate", "The work is taught on site."),
      ("retail-sales-associate", "The work is learned on the shop floor."),
      ("store-manager", "Usually reached by promotion from the shop floor.")],
     ["Look for “or equivalent experience” after the degree line: it means the degree is one way in, not the only one.",
      "When a posting does not ask for a degree, the skills and the years of experience it lists are the real filter.",
      "Licenses and certificates still apply: an electrician needs a license, a driver the right class of license.",
      "Put skills and results at the top of your resume and education at the bottom."],
     [("What jobs can I get without a degree?", "Sales, customer support, IT support, technician and trade work, warehouse and retail jobs, and a share of software jobs. {TOP}"),
      ("How many jobs say no degree is required?", "{EXTRA} The count covers only postings that say so in their text; the site’s list of jobs with no degree required holds every one of them."),
      ("Which jobs without a degree pay the most?", "Pay follows the kind of work, with or without a degree. {PAY} That median covers every posting in the kind of work, not only the ones that waive the degree."),
      ("Can I get a remote job without a degree?", "Yes: support, sales and software postings are often remote, with or without a degree. {REMOTE}"),
      ("Do employers really hire without a degree?", "When the posting says so, yes: it is the employer’s own statement. Where it says nothing, apply if you meet the skills and experience it lists.")],
     (("perks/no-degree/", "Jobs that say no degree is required"), ("jobs-for/people-with-no-experience/", "Jobs for people with no experience"), ("jobs-for/working-with-your-hands/", "Jobs working with your hands"),
      ("guides/how-to-read-a-job-posting/", "How to read a job posting"), ("categories/skilled-trades/", "Skilled trades")),
     note="The column “Say no degree is needed” counts postings that say so in their own text. A posting that is silent about a degree may still take you: the skills and the years of experience it lists decide.",
     extra=("nodegree",))

_who("stay-at-home-parents", "Stay-at-home parents", "Jobs for Stay-at-Home Parents: Remote and Part-Time Work",
     "Jobs for stay-at-home parents, counted from {n} open postings: {k} kinds of work that are often remote, with the part-time openings and pay for each.",
     "Jobs for stay-at-home parents",
     "A parent at home needs work that can be done from the house and, often, in fewer hours than a full week. "
     "These are kinds of work that are frequently remote, with the remote share and the part-time openings counted in each today.",
     [("customer-support", "Support by phone, chat and email, often from home and in shifts."),
      ("chat-support", "Written support, which does not need a silent room."),
      ("content-writer", "Writing to a deadline rather than to a clock."),
      ("social-media", "Scheduling posts and answering comments from a laptop."),
      ("community-manager", "Looking after an online community, often across time zones."),
      ("recruiter", "Calls and messages with candidates, commonly from home."),
      ("sourcer", "Searching for candidates online, with few fixed meetings."),
      ("payroll", "Regular, rule-based work on a monthly cycle."),
      ("billing-specialist", "Invoices and billing questions, handled by email."),
      ("accounts-receivable", "Following up on payments, by email and phone."),
      ("care-coordinator", "Guiding patients through their care by phone and video."),
      ("medical-coder", "Coding and billing from clinical notes, measured by output rather than hours at a desk."),
      ("ai-trainer", "Checking and writing examples for AI models; often contract work done from home."),
      ("education", "Online teaching and tutoring, in scheduled sessions.")],
     ["Remote does not mean flexible. Look for the words “shift”, “core hours” or a time zone in the posting.",
      "The Part-time column counts only postings marked part-time. Others may agree to fewer hours, but you have to ask.",
      "Contract and hourly work is common here; check whether the posting is for an employee or a contractor.",
      "Remote postings name the states or countries they hire in. Check that yours is on the list.",
      "An offer that asks you to pay for equipment or training is a scam. Real employers do not charge candidates."],
     [("What jobs can stay-at-home parents do?", "Remote support, writing, social media, recruiting, payroll and billing, care coordination, medical coding and online teaching. {TOP}"),
      ("Which jobs for stay-at-home parents are remote?", "All of these kinds of work have remote postings, in different shares. {REMOTE} The Remote column shows the share for each."),
      ("Are there part-time jobs for stay-at-home parents?", "{EXTRA} Many postings do not state the hours, so it is worth asking whether fewer hours are possible."),
      ("Do jobs for stay-at-home parents need experience?", "Support and data-labeling work take beginners; payroll, billing and coding ask for training or a certificate. {ENTRY}"),
      ("How do I explain years at home on a resume?", "State the dates plainly and add anything from that time that used work skills: volunteering, a course, freelance jobs. The guide on employment gaps has wording you can use.")],
     (("remote/", "Remote jobs"), ("part-time/", "Part-time jobs"), ("guides/employment-gap/", "How to explain an employment gap"), ("jobs-for/returning-to-work/", "Jobs for returning to work after a gap"),
      ("work-from-anywhere/", "Work-from-anywhere jobs")),
     extra=("parttime",))

_who("retirees", "Retirees and people over 50", "Jobs for Retirees and People Over 50, Open Today",
     "Jobs for retirees and people over 50, counted from {n} open postings: {k} kinds of work built on long experience or shorter hours, with part-time openings.",
     "Jobs for retirees and people over 50",
     "People late in a career usually want one of two things: to keep using what they know, or to work fewer hours. "
     "These are kinds of work that offer one or the other, with what is open in each today.",
     [("consulting", "Advising customers as an outside expert: a long career is what is being sold."),
      ("technology-consultant", "Helping clients choose and set up systems you have worked with for years."),
      ("corporate-trainer", "Teaching employees skills you have practiced yourself."),
      ("education", "Teaching and tutoring, often online and in scheduled sessions."),
      ("project-manager", "Having seen how projects go wrong is the qualification."),
      ("proposal-manager", "Writing bids, where knowing the industry and its buyers counts."),
      ("accounting", "Steady, rule-based work with a monthly rhythm."),
      ("tax", "Seasonal peaks, and knowledge that builds over decades."),
      ("technical-writer", "Deep knowledge of a subject, written down for others."),
      ("recruiter", "A wide circle of contacts and good judgment of people."),
      ("customer-support", "Patience and plain speech, with the product taught on the job."),
      ("retail-sales-associate", "Shop work in shifts, with part-time openings."),
      ("grocery-associate", "Store work with a choice of shifts."),
      ("driver-chauffeur", "Driving people or goods on a set route or schedule.")],
     ["If you want fewer hours, look at the Part-time column and at contract postings; most postings assume a full week unless they say otherwise.",
      "Describe the last ten to fifteen years in detail on the resume and sum up the rest in one line.",
      "Check the tools a posting names. Being current in two or three of them answers a question the recruiter will not ask aloud.",
      "If you draw a pension or Social Security, check how earnings affect it before you accept; the rules depend on your age and country."],
     [("What are good jobs for retirees?", "Work that uses long experience, such as consulting, training, project and proposal work, accounting and tax, or work with shorter shifts, such as shop, support and driving jobs. {TOP}"),
      ("Are there part-time jobs for retirees and people over 50?", "{EXTRA} Many postings do not state the hours, and contract work is another way to work part of the year."),
      ("Can people over 50 get hired for these jobs?", "Postings do not set an age, and in most countries employers may not select by it. What a posting does set is skills and recent experience, so show both near the top of the resume."),
      ("Which jobs for retirees can be done from home?", "Consulting, writing, tutoring and support are often remote. {REMOTE}"),
      ("Do jobs for retirees pay well?", "Pay follows the kind of work. {PAY} Shift jobs often state an hourly rate, which this yearly median does not count.")],
     (("part-time/", "Part-time jobs"), ("contract/", "Contract jobs"), ("remote/", "Remote jobs"), ("guides/employment-gap/", "How to explain an employment gap"),
      ("jobs-for/returning-to-work/", "Jobs for returning to work after a gap")),
     note="Employers may not choose or refuse candidates by age, and no posting here is reserved for an age group. The list picks kinds of work that draw on long experience, or that are often part-time or by contract.",
     extra=("parttime",))

_who("night-owls", "Night owls", "Jobs for Night Owls: Kinds of Work With Night Shifts",
     "Jobs for night owls, counted from {n} open postings: {k} kinds of work that run around the clock, with pay and the postings that name a night shift.",
     "Jobs for night owls",
     "If you work best after dark, a nine-to-five wastes your best hours. "
     "These are kinds of work that run around the clock, where somebody has to be awake at night, with what is open in each today.",
     [("data-center", "Servers run all night, and someone has to be in the building."),
      ("soc-analyst", "Security alerts are watched around the clock, in shifts."),
      ("security-analyst", "Incidents do not wait for morning; teams staff nights or rotate on call."),
      ("site-reliability-engineer", "Keeping systems up at all hours, with night work mostly as on-call duty."),
      ("support-engineer", "Customers in other time zones need answers during your night."),
      ("customer-support", "Support lines that promise an answer at any hour staff evenings and nights."),
      ("chat-support", "Written support, with late shifts for customers elsewhere in the world."),
      ("nursing", "Care continues overnight, in hospitals and on telehealth lines."),
      ("physical-security", "Guard and control-room work, much of it at night."),
      ("warehouse-associate", "Goods are picked and loaded overnight for morning delivery."),
      ("production-worker", "Factories run second and third shifts."),
      ("maintenance-technician", "Repairs are done while the line or the building is quiet."),
      ("mission-operations", "Satellites pass overhead at all hours, and control rooms are staffed for them."),
      ("hospitality", "Kitchens and restaurants work late.")],
     ["The shift is in the posting: look for “night”, “overnight”, “second shift”, “third shift” or “swing”.",
      "Ask whether nights are fixed or rotate with days.",
      "Night work often comes with a shift differential. Check whether the posted rate includes it.",
      "On-call is not a night shift: you are paid to be reachable, not to be awake. The posting says which it is."],
     [("What jobs are good for night owls?", "Work that runs around the clock: data centers, security operations, support for other time zones, nursing, guarding, warehouses, factories, maintenance and hospitality. {TOP}"),
      ("How many jobs name a night shift today?", "Postings name the shift in the title or the summary, and the night shift list on this site holds every posting that does. {EXTRA}"),
      ("Do night shift jobs pay more?", "Often a shift differential is added to the base rate, and the posting says so when it is. {PAY} Hourly rates are not in this yearly median."),
      ("Can night owls work from home?", "Support and security monitoring for other time zones can be remote night work. {REMOTE}")],
     (("night-shift/", "Night shift jobs"), ("weekend/", "Weekend jobs"), ("part-time/", "Part-time jobs"), ("jobs-for/working-alone/", "Jobs where you work alone")),
     extra=("night",))

_who("people-who-want-to-travel", "People who want to travel", "Jobs for People Who Want to Travel, Open Today",
     "Jobs for people who want to travel, counted from {n} open postings: {k} kinds of work done at customers’ sites, with pay and how many mention travel.",
     "Jobs for people who want to travel",
     "Travel jobs are usually imagined as pilots and tour guides, yet most paid travel is ordinary business done somewhere else. "
     "These are kinds of work where going to the customer is part of the job, with what is open in each today.",
     [("field-service", "Installing and repairing equipment where it is used, which can be anywhere."),
      ("consulting", "Advising clients at their own offices."),
      ("technology-consultant", "Setting up systems on the client’s site."),
      ("professional-services", "Fitting a product to a customer’s needs, partly on site."),
      ("implementation", "Getting a new customer started, with visits for training and launch."),
      ("solutions-engineer", "Showing a product to buyers and answering their technical questions in person."),
      ("sales-engineer", "The technical half of a sales team that visits customers."),
      ("enterprise-account-executive", "Large deals are closed face to face, across a region or a country."),
      ("territory-sales", "You own the sales of one area and visit the customers in it."),
      ("field-sales", "Selling in person, at customers’ offices and shops."),
      ("channel-sales", "Visiting the partners and resellers who sell for you."),
      ("events", "Conferences and trade shows, in one city after another."),
      ("field-marketing", "Local events and dinners across a region."),
      ("supplier-quality", "Visiting and auditing suppliers, wherever their factories are.")],
     ["Postings state travel as a share of time, such as “up to 50%”. Read it as a normal month, not as a ceiling that is never reached.",
      "Check where the travel goes: one region, one country or worldwide.",
      "Ask how travel is booked and paid: a company card, or your own money repaid later.",
      "A job with travel still has a home base. The posting names where you must live."],
     [("What jobs let you travel?", "Jobs done at the customer’s place: field service, consulting, implementation, solutions and sales engineering, field and territory sales, events and supplier audits. {TOP}"),
      ("How many of these jobs mention travel?", "A posting that mentions travel usually also says how much, as a share of working time. {EXTRA}"),
      ("Which travel jobs pay the most?", "Sales roles often post pay at target, which includes commission. {PAY}"),
      ("Do travel jobs need experience?", "Most send you to customers on your own, so they ask for experience first. {ENTRY}"),
      ("Is a remote job the same as a job with travel?", "No. A remote job lets you work from home, usually inside one country. A job with travel sends you where the customer is. {REMOTE}")],
     (("relocate/", "Relocation guides by country"), ("work-from-anywhere/", "Work-from-anywhere jobs"), ("categories/sales/", "Sales jobs by kind of work"),
      ("jobs-for/work-from-anywhere/", "Jobs for people who want to work from anywhere"), ("perks/relocation/", "Jobs with relocation support")),
     extra=("travel",))

_who("low-stress", "Low-stress work", "Low-Stress Jobs: What Postings Can and Cannot Tell You",
     "Low-stress jobs without the guesswork: {k} kinds of work and what {n} open postings say about remote work, part-time hours, on-call duty and quotas.",
     "Low-stress jobs",
     "Lists of low-stress jobs rank occupations by somebody’s impression. "
     "This page picks kinds of work whose day is usually planned in advance rather than driven by a sales target or a night alert, and shows what today’s postings say.",
     [("technical-writer", "Work planned by release dates, with no sales target."),
      ("content-writer", "Deadlines known in advance, and work that can be finished."),
      ("localization", "Text arrives in batches with agreed dates."),
      ("instructional-designer", "Courses are built over weeks, to a plan."),
      ("data-analyst", "Questions come as requests, and answers are due in days rather than minutes."),
      ("research-analyst", "Reports are written over days or weeks."),
      ("accounting", "The calendar is known a year ahead, with busy weeks at each close."),
      ("payroll", "The same cycle every month, with fixed cut-off dates."),
      ("accounts-payable", "Invoices are checked and paid on a schedule."),
      ("billing-specialist", "Routine billing work, with questions answered by email."),
      ("hris", "Keeping HR systems and reports in order."),
      ("gis", "Map and location data work, done at a desk to a plan."),
      ("cad-designer", "Drawings produced from engineers’ designs, one job after another."),
      ("lab-technician", "Bench work that follows a written protocol.")],
     ["Read the posting for “on-call”, “quota”, “targets”, “fast-paced” and “tight deadlines”. They are the employer’s own description of the pressure.",
      "Ask about the busy periods. Accounting and payroll are calm for three weeks and tense in the fourth.",
      "The same kind of work differs between employers more than between occupations. Ask the team what a bad week looks like.",
      "Fewer hours do not always mean less pressure: check whether a part-time role carries a full-time workload."],
     [("What are low-stress jobs?", "Nobody can say for certain, because stress depends on the employer and the person. Kinds of work with planned days and no sales target include writing, translation, course design, analysis, accounting, payroll and lab work. {TOP}"),
      ("How many low-stress jobs mention on-call duty or quotas?", "A posting that uses these words is at least telling you about them; one that does not may simply be silent. {EXTRA}"),
      ("Which low-stress jobs pay well?", "Pay follows the kind of work, not how calm it is. {PAY}"),
      ("Are low-stress jobs remote?", "Many of these kinds of work can be done from home, which removes the commute but not the deadlines. {REMOTE}"),
      ("How can I tell from a posting whether a job is stressful?", "Look at what it demands: on-call rotations, quotas, travel, “fast-paced”, the number of people you answer to. Then ask in the interview how often people work late, and why.")],
     (("part-time/", "Part-time jobs"), ("remote/", "Remote jobs"), ("guides/how-to-read-a-job-posting/", "How to read a job posting"),
      ("guides/what-postings-ask-besides-skills/", "What postings ask for besides skills"), ("jobs-for/introverts/", "Jobs for introverts")),
     note="“Low stress” is an opinion: no posting measures it, and neither can we. What can be counted is shown instead: how much of the work is remote, how many postings are part-time, and how many mention on-call duty or a quota.",
     extra=("parttime", "oncall"))

_who("high-pay-without-managing-people", "High pay without managing people", "Jobs That Pay Well Without Managing People, Open Today",
     "Jobs that pay well without managing people, counted from {n} open postings: {k} senior specialist kinds of work, with the median advertised pay of each.",
     "Jobs that pay well without managing people",
     "In many companies the only visible way to earn more is to become a manager. "
     "These are kinds of work where senior specialists are paid for what they know and build, with the median advertised pay of each counted today.",
     [("staff-engineer", "The senior engineering track without a team: you set technical direction and solve the hardest problems."),
      ("software-architect", "Deciding how a large system fits together, as an individual expert."),
      ("solutions-architect", "Designing how a product fits into a customer’s systems."),
      ("machine-learning-engineer", "Specialist engineering where depth is what is paid for."),
      ("research-scientist", "Paid for research results, usually with an advanced degree."),
      ("data-scientist", "Senior individual work with models and experiments."),
      ("site-reliability-engineer", "Keeping large systems running, with pay that reflects the responsibility."),
      ("security-architect", "Designing how a company’s systems are defended as a whole."),
      ("asic-engineer", "Chip design, a narrow skill that takes years to build."),
      ("quant", "Math and code applied to trading, paid by results."),
      ("actuary", "Pay rises with each professional exam, without a team to manage."),
      ("enterprise-account-executive", "Selling large deals, with pay tied to what you close."),
      ("sales-engineer", "The technical expert on a sales team, paid partly on results."),
      ("commercial-counsel", "Lawyers who negotiate contracts as individual experts.")],
     ["Titles do not say everything: some staff and architect roles lead people in practice. Look for “manage”, “direct reports” or “lead a team” in the posting.",
      "For sales roles the posted figure is often pay at target. Ask what the base is.",
      "The median here is advertised pay, from postings that state a yearly range. It is what employers offer new hires, not what people already in the job earn.",
      "These roles ask for years of depth in one field. Check the years and the skills list before the pay."],
     [("What jobs pay well without managing people?", "Senior specialist roles: staff and principal engineers, architects, machine learning and research roles, security architects, chip designers, actuaries, quantitative researchers, enterprise sales and commercial lawyers. {TOP}"),
      ("Which of these specialist jobs advertises the most?", "{PAY} Each median is counted from postings that state a yearly range in US dollars, and is shown only when at least five do."),
      ("Can you earn more as a specialist than as a manager?", "It depends on the company. The table shows what postings for specialist roles advertise today; the salary pages on this site show manager roles, so you can compare the two."),
      ("Do high-paying specialist jobs need a degree?", "Research, actuarial and legal roles do. Engineering and sales postings sometimes accept experience in place of one, and say so when they do."),
      ("Are high-paying jobs without management remote?", "Some are, mostly in engineering and sales, and the posting names the countries it hires in. {REMOTE}")],
     (("guides/highest-paying-jobs/", "The highest-paying jobs"), ("salaries/", "Salary data by job title"), ("guides/does-senior-pay-more/", "Does a senior title pay more?"),
      ("guides/job-levels-explained/", "What the level in a title means"), ("with-salary/", "Jobs that state the pay")))

_who("work-from-anywhere", "Working from anywhere", "Work From Anywhere Jobs: Kinds of Work Open Today",
     "Work-from-anywhere jobs, counted from {n} open postings: {k} kinds of work, the remote share of each and how many postings are open to any country.",
     "Jobs for people who want to work from anywhere",
     "Most remote postings are tied to one country or time zone, and few can be done from anywhere. "
     "These are kinds of work with a large remote share, counted today, so you can see where the search is worth your time.",
     [("backend-engineer", "The work is code and reviews, which travel anywhere with a connection."),
      ("frontend-engineer", "Building interfaces from designs, with work handed over in writing."),
      ("full-stack-engineer", "Small remote teams hire people who can build a whole feature alone."),
      ("devops-engineer", "Infrastructure is managed through a terminal, from wherever you are."),
      ("blockchain-engineer", "Crypto teams are often spread across many countries."),
      ("smart-contract-engineer", "Code published on a public network, written by teams with no single office."),
      ("penetration-tester", "Testing is done remotely, against systems anywhere."),
      ("developer-advocate", "Writing, speaking and community work for developers around the world."),
      ("community-manager", "Online communities are awake in every time zone."),
      ("product-designer", "Design files and written feedback do not need an office."),
      ("content-writer", "Text can be written anywhere and delivered by a deadline."),
      ("customer-support", "Support teams hire across time zones to cover the clock."),
      ("support-engineer", "Technical support for customers in other time zones."),
      ("technical-account-manager", "Looking after customers by video and message.")],
     ["Look for the list of countries or time zones in the posting. “Remote (US)” means you must live in the US and have the right to work there.",
      "A posting open to any country may hire you as a contractor, not an employee. Check which, because taxes and benefits differ.",
      "Ask which hours must overlap with the team. Four hours of overlap from the other side of the world can mean working at night.",
      "Pay may be set by where you live. If the posting gives one range for everyone, it usually says so."],
     [("What jobs can you do from anywhere?", "Work delivered through a screen: software engineering, infrastructure, crypto engineering, security testing, design, writing, community work and support across time zones. {TOP}"),
      ("How many remote jobs are open to any country?", "Most remote postings name a country, a region or a time zone you must be in. {EXTRA}"),
      ("Which work-from-anywhere jobs pay the most?", "Pay follows the kind of work. {PAY} Check whether the range depends on where you live."),
      ("Which kind of work has the largest remote share?", "{REMOTE} The Remote column shows the share for every kind of work on this page."),
      ("Can I work from anywhere as an employee?", "Sometimes. Many companies employ people only in countries where they have a legal entity, and take contractors elsewhere. The posting, or the recruiter, will tell you which applies to you.")],
     (("work-from-anywhere/", "Work-from-anywhere jobs"), ("remote/", "Remote jobs"), ("tools/time-zone-overlap/", "Time zone overlap calculator"),
      ("guides/remote-jobs-by-field/", "Remote jobs by field"), ("jobs-for/people-who-want-to-travel/", "Jobs for people who want to travel")),
     note="Remote does not mean anywhere. Most remote postings name a country, a region or a time zone; the last column counts the ones that name none.",
     extra=("anywhere",))

_who("bilingual-people", "Bilingual people", "Jobs for Bilingual People: Openings by Language Today",
     "Jobs for bilingual people, counted from {n} open postings: {k} languages and kinds of work where a second language is asked for, with pay and remote share.",
     "Jobs for bilingual people",
     "A second language is often treated as a line at the bottom of a resume. "
     "In these kinds of work it is the requirement itself, and each is counted from the postings that name the language or its market today.",
     [("bilingual", "Postings that ask for a second language besides English, most often in sales or support."),
      ("spanish-speaking", "Work in Spanish, or for customers in Spain and Latin America."),
      ("german-speaking", "Work in German, or for customers in Germany, Austria and Switzerland."),
      ("french-speaking", "Work in French, or for customers in France and other French-speaking markets."),
      ("japanese-speaking", "Work in Japanese, or for customers in Japan."),
      ("portuguese-speaking", "Work in Portuguese, or for customers in Brazil and Portugal."),
      ("chinese-speaking", "Work in Mandarin or Cantonese, or for Chinese-speaking customers."),
      ("italian-speaking", "Work in Italian, or for customers in Italy."),
      ("dutch-speaking", "Work in Dutch, or for customers in the Netherlands and Belgium."),
      ("korean-speaking", "Work in Korean, or for customers in South Korea."),
      ("arabic-speaking", "Work in Arabic, or for customers in the Gulf, the Middle East and North Africa."),
      ("nordic-speaking", "Work in Swedish, Norwegian, Danish or Finnish, or for customers in the Nordic countries."),
      ("localization", "Adapting a product and its texts to other languages."),
      ("customer-support", "Support teams hire by the languages their customers write in.")],
     ["The posting states the level: “fluent”, “native” or “business level”. Expect part of the interview in that language.",
      "Many of these roles are based in the country of the language, or in a regional hub. Check the place before the title.",
      "Put the language and your level in the first lines of the resume, not in a list at the end.",
      "Translation and localization ask for writing skill in the target language, which is more than speaking it."],
     [("What jobs are there for bilingual people?", "Sales, support, account management and operations for customers who speak another language, plus translation and localization. {TOP}"),
      ("Which bilingual jobs have the most openings?", "{TOP} Each count reads job titles that name the language or its market, so a posting that asks for the language only in its text is not included."),
      ("Do bilingual jobs pay more?", "A posting seldom says how much the language adds. {PAY} Compare the range with the same kind of work on its own role page."),
      ("Can bilingual jobs be done remotely?", "Support and sales in another language are often remote within a country or region. {REMOTE}"),
      ("Do I need a certificate to prove a language?", "Rarely. Employers test it in the interview, part of which is usually held in that language. A certificate helps most when the posting names a level such as C1.")],
     (("categories/languages/", "Jobs by language"), ("relocate/", "Relocation guides by country"), ("perks/visa-sponsorship/", "Jobs with visa sponsorship"),
      ("jobs-for/work-from-anywhere/", "Jobs for people who want to work from anywhere"), ("categories/writing-translation/", "Writing, editing and translation jobs")))

_who("returning-to-work", "Returning to work after a gap", "Jobs for Returning to Work After a Career Gap",
     "Jobs for returning to work after a gap, counted from {n} open postings: {k} kinds of work that train new hires and value steady skills, with pay.",
     "Jobs for returning to work after a gap",
     "After a few years away, the gap on the resume feels larger than the career before it. "
     "These are kinds of work where the first weeks are training and where skills from before the break still count, with what is open in each today.",
     [("customer-support", "New hires are trained on the product, whatever they did before."),
      ("customer-success-manager", "Looking after customers rests on judgment and follow-up, which do not expire."),
      ("sales-development", "Hired for persistence and clear speech, and trained from the first day."),
      ("recruiter", "Reading people and keeping many conversations moving."),
      ("coordinator", "Schedules, orders and paperwork: an organized person is useful at once."),
      ("executive-assistant", "Calendars, travel and meetings, where reliability is the skill."),
      ("office-manager", "Running an office day to day."),
      ("project-manager", "Planning and deadlines work the way they did before the break."),
      ("operations-analyst", "Keeping daily processes running and spotting what to fix."),
      ("accounting", "The rules change slowly, and a short refresher brings you up to date."),
      ("human-resources", "Contracts, policies and conversations with employees."),
      ("content-writer", "Judged on samples, which can be written during the break."),
      ("implementation", "Explaining a product to new customers and setting them up.")],
     ["Look for the words “returnship” or “return to work program”: some large employers run paid programs for people coming back after a break.",
      "Check the tools the posting names and refresh the two or three you used before. Recent practice answers the question about the gap.",
      "State the dates plainly on the resume. A gap explained in one line raises fewer questions than one that is hidden.",
      "Part-time or contract work can be a first step back. The posting says which it is."],
     [("What jobs are good for returning to work after a gap?", "Work where new hires are trained and where earlier skills still apply: support, customer success, sales development, recruiting, coordination, office and project management, accounting and HR. {TOP}"),
      ("How do I explain a career gap to an employer?", "In one plain line with dates, then move to what you can do now. The guide on employment gaps has wording for the resume, the cover letter and the interview."),
      ("Do I have to start at entry level after a career gap?", "Not necessarily. Apply at the level of your last role if your skills are current; a refresher course or recent freelance work helps show it. {ENTRY}"),
      ("Can I return to work in a remote job?", "Yes, many of these kinds of work have remote postings. {REMOTE}"),
      ("Which jobs for returning to work pay well?", "Pay follows the kind of work and the level you come back at. {PAY}")],
     (("guides/employment-gap/", "How to explain an employment gap"), ("jobs-for/stay-at-home-parents/", "Jobs for stay-at-home parents"), ("jobs-for/career-changers/", "Jobs for career changers"),
      ("part-time/", "Part-time jobs"), ("tools/resume-match/", "Check your resume against a posting")))

# ---------------------------------------------------------------- by degree ----------------------------------------------------------------

_degree("psychology-degree", "psychology",
        "A psychology degree is usually pictured as a path to therapy, which needs graduate school and a license. "
        "The bachelor’s degree is also used in work about people and how they behave, and these are the kinds graduates commonly move into, with what is open in each today.",
        [("human-resources", "Motivation and conflict are the daily material of HR."),
         ("people-operations", "The processes of employment, run with an eye on how people experience them."),
         ("recruiter", "Interviewing and judging fit draw directly on the degree."),
         ("employee-experience", "Surveys, onboarding and culture programs, built on how people behave at work."),
         ("ux-researcher", "Interviews, observation and study design are methods taught in the degree."),
         ("research-analyst", "Survey design and statistics, applied to markets."),
         ("data-analyst", "The statistics courses carry over to analysis once SQL is added."),
         ("marketing-manager", "Campaigns rest on what people notice, believe and choose."),
         ("customer-success-manager", "Reading what a customer needs and keeping the relationship working."),
         ("customer-experience", "Measuring how customers feel about each contact with a company."),
         ("training", "Learning theory from the degree, applied to teaching adults."),
         ("care-coordinator", "Guiding patients through their care; the posting says whether a license is needed."),
         ("mental-health", "Therapist and counselor roles, which need a graduate degree and a license."),
         ("sales-development", "A common first job for graduates of any subject who are good with people.")],
        ["Therapist, counselor and psychologist postings name a license. A bachelor’s degree alone does not meet it.",
         "Research roles ask for methods by name: surveys, interviews, statistics, sometimes R or Python. Say which you used, and on what.",
         "HR and recruiting postings that ask for a degree seldom name the subject. The skills list is what you are matched on.",
         "Put a research project from your degree on the resume as work: the question, the method, the sample and the result."],
        [("What jobs can you get with a psychology degree?", "With a bachelor’s degree: HR, recruiting, user research, market research, data analysis, marketing, customer success and training. With a graduate degree and a license: therapy and counseling. {TOP}"),
         ("Do you need a master’s degree to work in psychology?", "To practice as a therapist, counselor or psychologist, yes, plus a license. The other kinds of work on this page hire with a bachelor’s degree."),
         ("How much do jobs for psychology graduates pay?", "Postings advertise pay for the work, not for the degree. {PAY} The table shows a median for every kind of work where at least five postings state a yearly range."),
         ("Can you work remotely with a psychology degree?", "Recruiting, research and customer success are often remote, and therapy is often done by video. {REMOTE}"),
         ("Is a psychology degree useful outside therapy?", "Yes. Research methods, statistics and an understanding of behavior are what HR, user research and marketing postings describe, usually without naming the degree.")],
        (("jobs-for/helping-others/", "Jobs for people who like helping others"), ("categories/hr-recruiting/", "HR and recruiting jobs"), ("how-to-become/", "How to become…: steps into each kind of work"),
         ("entry-level/", "Entry-level jobs"), ("jobs-for/sociology-degree/", "What can you do with a sociology degree?")))

_degree("business-degree", "business",
        "A business degree is broad, which makes it hard to say what job it leads to. "
        "These are the kinds of work its graduates commonly move into, from analysis to sales and operations, with what is open in each today.",
        [("business-analyst", "Working out what a team needs and writing it down for the people who build it."),
         ("operations-analyst", "Finding in the numbers what to fix in a team’s daily work."),
         ("operations-manager", "Running people, processes, suppliers and costs."),
         ("business-operations", "Strategy and planning questions that belong to no single team."),
         ("project-manager", "Plans, budgets and deadlines, taught in most business programs."),
         ("financial-analyst", "Budgets and forecasts, built on the finance and accounting courses."),
         ("account-executive", "Selling to companies, where knowing how a business buys helps."),
         ("account-manager", "Looking after customers and renewing their contracts."),
         ("sales-development", "The usual first job in sales for business graduates."),
         ("business-development", "Finding partner companies and negotiating deals with them."),
         ("marketing-manager", "Campaigns, budgets and results, from the marketing courses."),
         ("human-resources", "Contracts, policies and how people are managed."),
         ("consulting", "Advising clients on how to solve a business problem."),
         ("supply-chain", "Getting products made, stored and delivered on time.")],
        ["Use your concentration (finance, marketing, operations) to choose among these; a posting’s skills list will match one of them.",
         "Analyst postings ask for Excel and often SQL. Name the tools and what you built with them.",
         "Sales roles state pay at target. Ask what share of it is base pay.",
         "Internships count as experience in a first application. Lead with them."],
        [("What jobs can you get with a business degree?", "Analyst roles, operations, project management, sales and account management, marketing, HR, consulting and supply chain. {TOP}"),
         ("What is the highest-paying job with a business degree?", "{PAY} That is advertised pay for the kind of work as a whole, senior roles included, so a first job will sit lower in the range."),
         ("Are there entry-level jobs for business graduates?", "Yes. Sales development, analyst and coordinator roles are the usual first jobs. {ENTRY}"),
         ("Do business jobs ask for an MBA?", "Some strategy, consulting and finance postings prefer one, and say so when they do. Others ask for a bachelor’s degree, or for experience in its place."),
         ("Can business graduates work remotely?", "Sales, account management and analysis are often remote; operations and supply chain less so. {REMOTE}")],
        (("categories/operations-administration/", "Operations and administration jobs"), ("categories/sales/", "Sales jobs by kind of work"), ("entry-level/", "Entry-level jobs"),
         ("guides/entry-level-jobs/", "Entry-level jobs: what the postings show"), ("jobs-for/recent-graduates/", "Jobs for recent graduates")))

_degree("english-degree", "English",
        "An English degree teaches close reading and clear writing, and no posting lists those two things as a job title. "
        "These are the kinds of work where they are the job, and that graduates commonly move into, with what is open in each today.",
        [("content-writer", "Writing and editing for a company’s readers: the degree’s main skill, at work."),
         ("technical-writer", "Turning complicated material into instructions people can follow."),
         ("content-designer", "Choosing the few words inside an app, where each one is argued over."),
         ("communications", "Announcements and statements, where tone and precision are the job."),
         ("public-relations", "Stories pitched to journalists in their own language."),
         ("internal-communications", "Explaining a company’s news to its own staff."),
         ("social-media", "Short writing with a voice, every day."),
         ("seo", "Editing pages so that readers who search can find them."),
         ("proposal-manager", "Long, structured documents that have to persuade."),
         ("marketing-coordinator", "A first marketing job with a lot of writing in it."),
         ("paralegal", "Close reading, research and careful drafting for lawyers."),
         ("instructional-designer", "Lessons that build from one idea to the next."),
         ("education", "Teaching and tutoring, in schools or for education companies."),
         ("localization", "Editing translated text until it reads as if it was written in English.")],
        ["Writing postings ask for samples. Choose three that match the kind of text in the posting, not your best essays.",
         "Teaching in public schools needs a state license in addition to the degree.",
         "Postings often want a writer who already knows the subject: health, finance, software. Say which subjects you know.",
         "Say what your writing did: readers reached, sign-ups, questions answered."],
        [("What jobs can you get with an English degree?", "Content and technical writing, the words inside products, communications and PR, social media, marketing, proposals, paralegal work and teaching. {TOP}"),
         ("Is an English degree useful for getting a job?", "Its skills are: postings in these kinds of work describe writing, editing and research. Few name the degree, so samples of your writing do the persuading."),
         ("How much do jobs for English graduates pay?", "It depends on the kind of writing and the subject. {PAY}"),
         ("Can you work from home with an English degree?", "Writing and editing are often remote, since the work is a document. {REMOTE}"),
         ("Do English graduates have to become teachers?", "No. Teaching is one of the {K} kinds of work in the table, and in public schools it needs a license on top of the degree. The others hire on writing samples.")],
        (("jobs-for/people-who-like-writing/", "Jobs for people who like writing"), ("categories/writing-translation/", "Writing, editing and translation jobs"),
         ("guides/how-to-write-a-cover-letter/", "How to write a cover letter"), ("jobs-for/journalism-degree/", "What can you do with a journalism degree?"),
         ("jobs-for/communications-degree/", "What can you do with a communications degree?")), an=True)

_degree("communications-degree", "communications",
        "A communications degree covers writing, media and persuasion, and its graduates are spread across many job titles. "
        "These are the kinds of work they commonly move into, with what is open in each today.",
        [("communications", "What a company says in public and to its staff: the degree’s home ground."),
         ("public-relations", "Getting covered by journalists and answering the press."),
         ("internal-communications", "Keeping staff informed through newsletters, meetings and messages from leaders."),
         ("social-media", "Planning and writing a company’s posts and answering its audience."),
         ("content-writer", "Articles and web pages for a company’s readers."),
         ("marketing-manager", "Campaigns that carry one message across many channels."),
         ("marketing-coordinator", "A first marketing job: schedules, emails, events."),
         ("brand-marketing", "What people think and feel about a brand, shaped through campaigns."),
         ("influencer-marketing", "Finding creators and running campaigns with them."),
         ("events", "Conferences and meetups, planned and run."),
         ("field-marketing", "Local events and campaigns in one region."),
         ("community-manager", "Keeping a product’s users talking, and heard."),
         ("account-manager", "Client relationships, at agencies and in-house."),
         ("recruiter", "Persuasion and clear conversation, applied to hiring.")],
        ["Bring a portfolio: press releases, campaigns, posts, a newsletter. Student media and internships count.",
         "Check whether the role is at an agency, with several clients, or in-house, with one.",
         "Postings name tools for scheduling posts, email and analytics. Learn the ones that recur.",
         "Look at how results are measured: coverage, reach, sign-ups or attendance."],
        [("What jobs can you get with a communications degree?", "Communications and PR, social media, content, marketing, events, community management, account management and recruiting. {TOP}"),
         ("What does a communications major do in a first job?", "Usually a coordinator or assistant role: scheduling posts, drafting announcements, organizing events and reporting results. {ENTRY}"),
         ("How much do communications degree jobs pay?", "Advertised pay differs by kind of work and level. {PAY}"),
         ("Are communications jobs remote?", "Content, social media and community work are often remote; events are not. {REMOTE}"),
         ("Is a communications degree the same as a marketing degree for employers?", "For many postings, yes: they ask for a degree in marketing, communications or a related field, and then list the skills that decide.")],
        (("categories/marketing-communications/", "Marketing and communications jobs"), ("jobs-for/marketing-degree/", "What can you do with a marketing degree?"),
         ("jobs-for/journalism-degree/", "What can you do with a journalism degree?"), ("jobs-for/extroverts/", "Jobs for extroverts"), ("entry-level/", "Entry-level jobs")))

_degree("biology-degree", "biology",
        "Biology graduates are told the choice is medical school or the lab bench. "
        "Both exist, and so do kinds of work around research, regulation and health that use the degree, listed here with what is open in each today.",
        [("lab-technician", "Running experiments and instruments: the usual first job in a lab."),
         ("life-sciences", "Laboratory research roles at biotech and research companies."),
         ("biologist", "Work on cells, genes and organisms, mostly through experiments."),
         ("research-scientist", "Leading research, usually after a graduate degree."),
         ("bioinformatics", "Analyzing DNA and protein data with code."),
         ("clinical-research", "Running the studies that test whether a treatment works."),
         ("clinical-research-coordinator", "Looking after the patients and records of a study."),
         ("process-development", "Turning a lab method into one that works at scale."),
         ("regulatory-affairs", "At biotech and health companies, preparing what regulators need to approve a product."),
         ("medical-writer", "Writing study reports and scientific documents."),
         ("medical-science-liaison", "Discussing the evidence for a medicine with doctors; usually needs an advanced degree."),
         ("environmental-engineer", "Field studies, permits and clean-up work on air, water and land."),
         ("ehs", "Workplace and environmental safety: inspections, permits, training."),
         ("healthcare", "Clinical and support roles at health companies.")],
        ["Lab postings list techniques by name, such as PCR or cell culture. Match them to what you did in your courses and projects.",
         "Scientist titles usually ask for a master’s degree or a PhD; associate and technician titles hire with a bachelor’s degree.",
         "Lab work is on site. Check the place before the title.",
         "Regulatory and clinical research roles value care with documents. Mention any work done under a written protocol."],
        [("What jobs can you get with a biology degree?", "Lab technician and research associate roles, clinical research, bioinformatics, regulatory affairs, medical writing, environmental work and safety. {TOP}"),
         ("Can you get a job with a bachelor’s degree in biology?", "Yes: technician, research associate, clinical research coordinator and safety roles hire with one. Scientist roles usually ask for a graduate degree. {ENTRY}"),
         ("How much do biology degree jobs pay?", "{PAY} Postings that ask for a graduate degree tend to sit higher in the range, so read the requirements together with the pay."),
         ("Are there remote jobs for biology graduates?", "Bioinformatics, medical writing and regulatory work can be remote; lab work cannot. {REMOTE}"),
         ("Do biology jobs need lab experience?", "Lab roles do, and course labs, a thesis project or an internship count. Writing, regulatory and data roles ask for the science and for care with documents.")],
        (("categories/science-healthcare/", "Science and healthcare jobs"), ("jobs-for/chemistry-degree/", "What can you do with a chemistry degree?"),
         ("jobs-for/public-health-degree/", "What can you do with a public health degree?"), ("entry-level/", "Entry-level jobs")))

_degree("computer-science-degree", "computer science",
        "A computer science degree leads to more job titles than “software engineer”, and the titles mean different work. "
        "These are the kinds graduates commonly move into, with what is open in each today.",
        [("software-engineer", "Designing, writing and maintaining software: the most common first job."),
         ("junior-software-engineer", "Entry roles where a senior engineer reviews your code."),
         ("backend-engineer", "Servers, databases and the logic behind an app."),
         ("frontend-engineer", "The part of an app that people see and click."),
         ("full-stack-engineer", "Both sides of an app, often at smaller companies."),
         ("mobile-engineer", "Apps for iPhone and Android."),
         ("data-engineer", "The pipelines that move and clean a company’s data."),
         ("machine-learning-engineer", "Training models and putting them into products; some postings ask for a graduate degree."),
         ("data-scientist", "Statistics and models applied to business questions."),
         ("devops-engineer", "Automating how software is built, shipped and run."),
         ("site-reliability-engineer", "Keeping large systems fast and available."),
         ("cybersecurity", "Protecting systems and finding their weak points."),
         ("qa-engineer", "Writing the tests that prove software works."),
         ("embedded-engineer", "Software that runs inside devices, close to the hardware.")],
        ["Postings name languages and frameworks. Apply where two or three of yours appear, and show a project in each.",
         "New-grad roles open on a yearly cycle and close when filled. Check the date of the posting.",
         "Expect a coding interview. The interview questions pages on this site list what is asked, by role.",
         "Postings often accept equivalent experience in place of the degree, so projects and internships are read as closely as the diploma."],
        [("What jobs can you get with a computer science degree?", "Software engineering across backend, frontend, mobile and data, machine learning, DevOps and reliability, security, testing and embedded work. {TOP}"),
         ("What is the highest-paying computer science job?", "{PAY} That median covers every level, so a first job will sit lower in the range."),
         ("Are there entry-level jobs for computer science graduates?", "Yes: new-grad, junior and intern roles are posted by title. {ENTRY}"),
         ("Do software jobs require a computer science degree?", "Many postings ask for the degree “or equivalent experience”. Where a posting says that, working software you have built is accepted in place of the diploma."),
         ("Can computer science graduates work remotely?", "Yes, software work is often remote. {REMOTE} The Remote column shows the share for each kind of work.")],
        (("categories/software-development/", "Software development jobs"), ("interview-questions/", "Interview questions by role"), ("skill-tests/", "Skill self-tests"),
         ("entry-level/", "Entry-level jobs"), ("jobs-for/information-technology-degree/", "What can you do with an information technology degree?")))

_degree("mathematics-degree", "mathematics",
        "A mathematics degree proves you can reason, and then leaves you to find out who pays for that. "
        "These are the kinds of work graduates commonly move into, most of them built on statistics, modeling or code, with what is open in each today.",
        [("data-scientist", "Probability and statistics from the degree, applied with code."),
         ("data-analyst", "A common first job: counting, and explaining what the numbers show."),
         ("statistician", "Study design and inference, straight from the statistics courses."),
         ("actuary", "Probability applied to insurance, with professional exams after the degree."),
         ("quant", "Stochastic models and code, used to price and to trade."),
         ("machine-learning-engineer", "Linear algebra and optimization are the theory under every model."),
         ("research-scientist", "Research roles in AI and science, usually after a graduate degree."),
         ("financial-analyst", "Forecasts and models for a company’s money."),
         ("risk-manager", "Measuring, in numbers, what could go wrong."),
         ("pricing", "Models of how a change in price changes demand."),
         ("analytics-engineer", "Building the clean tables that analysis depends on."),
         ("experimentation", "Designing tests that separate cause from coincidence."),
         ("cryptographer", "Number theory and algebra, applied to keeping data secret."),
         ("software-engineer", "Programming rewards the same habit of exact reasoning.")],
        ["Most postings want math plus a tool: SQL, Python or R. Name the tool and a project done with it.",
         "Actuarial postings ask how many exams you have passed. One or two before applying helps.",
         "Quantitative research and machine learning research usually ask for a master’s degree or a PhD.",
         "Translate course names into skills: “real analysis” means little to a recruiter, “probability and statistical modeling” means a lot."],
        [("What jobs can you get with a mathematics degree?", "Data science and analysis, statistics, actuarial work, quantitative research, machine learning, financial analysis, risk, pricing and software. {TOP}"),
         ("What is the highest-paying job for a math major?", "{PAY} Research and quantitative roles often ask for a graduate degree, so check the requirements together with the pay."),
         ("Do math graduates need to learn programming?", "For nearly all of this work, yes. Postings in these kinds of work name tools such as SQL, Python and R next to the math."),
         ("Are there entry-level jobs for math majors?", "Analyst and actuarial trainee roles are the usual start. {ENTRY}"),
         ("Can math majors work remotely?", "Analysis and modeling are done on a computer, so remote postings are common. {REMOTE}")],
        (("jobs-for/people-who-like-math/", "Jobs for people who like math"), ("categories/data-analytics/", "Data and analytics jobs"), ("jobs-for/physics-degree/", "What can you do with a physics degree?"),
         ("jobs-for/economics-degree/", "What can you do with an economics degree?"), ("guides/skills-in-demand/", "Skills in demand")))

_degree("economics-degree", "economics",
        "An economics degree does not make you an economist: that title usually asks for a graduate degree. "
        "The bachelor’s degree is used in analysis, finance and policy, and these are the kinds of work graduates commonly move into, with what is open in each today.",
        [("financial-analyst", "Forecasts and budgets, a common first job."),
         ("analyst", "Analyst roles across finance, risk, operations and data."),
         ("data-analyst", "Econometrics becomes data analysis once SQL is added."),
         ("business-analyst", "Working out what a business needs and what it would cost."),
         ("economist", "Studying markets and policy; usually asks for a graduate degree."),
         ("pricing", "What to charge and how demand reacts: applied microeconomics."),
         ("research-analyst", "Studying markets and companies, and writing up the findings."),
         ("consulting", "Advising clients, with analyst roles for graduates."),
         ("investment-banking", "Building the financial models behind deals."),
         ("investment", "Deciding where money is invested."),
         ("credit-analyst", "Judging whether a borrower will repay."),
         ("risk-manager", "Measuring market and credit risk."),
         ("policy", "Following laws and regulation on a company’s behalf."),
         ("business-operations", "Strategy questions answered with numbers.")],
        ["Analyst postings ask for Excel and SQL, and research roles for Python, R or Stata. Name what you used in your econometrics courses.",
         "Banking and consulting recruit on a calendar, often a year ahead. Check the dates of postings.",
         "Say what your thesis or project found, in one sentence with a number.",
         "Policy roles ask for writing. Have a short paper ready as a sample."],
        [("What jobs can you get with an economics degree?", "Financial and data analysis, business analysis, pricing, market research, consulting, banking, investment, credit and risk, and policy work. {TOP}"),
         ("Do you need a master’s degree to be an economist?", "Postings with that title usually ask for a graduate degree, and research roles for a PhD. The other kinds of work on this page hire with a bachelor’s degree."),
         ("How much do economics degree jobs pay?", "{PAY} Banking and investment postings often state a base range and pay a bonus on top, which the median does not include."),
         ("Is economics a good degree for finance jobs?", "Finance postings commonly ask for a degree in finance, economics, accounting or a related field, so economics qualifies. The skills list, usually modeling and Excel, decides the rest."),
         ("Can economics graduates work in tech?", "Yes: pricing, analytics, experimentation and business operations teams at software companies hire for economic reasoning and skill with data.")],
        (("categories/accounting-finance/", "Accounting and finance jobs"), ("categories/data-analytics/", "Data and analytics jobs"), ("jobs-for/finance-degree/", "What can you do with a finance degree?"),
         ("jobs-for/mathematics-degree/", "What can you do with a mathematics degree?"), ("entry-level/", "Entry-level jobs")), an=True)

_degree("finance-degree", "finance",
        "A finance degree points at banks, but nearly every company of any size has a finance team. "
        "These are the kinds of work graduates commonly move into, inside banks and outside them, with what is open in each today.",
        [("financial-analyst", "Budgets, forecasts and the model behind each decision."),
         ("finance-manager", "Running the numbers of a business unit, usually after some years as an analyst."),
         ("accounting", "Recording and reporting what a company earns and owes."),
         ("treasury", "Managing a company’s cash and its currency and interest risk."),
         ("investment-banking", "Models and documents for raising money and buying companies."),
         ("investment", "Choosing where money is invested, at funds and inside companies."),
         ("credit-analyst", "Deciding whether to lend, and on what terms."),
         ("underwriter", "Deciding whether to insure or lend, and at what price."),
         ("lending", "Preparing loans and looking after them until they are repaid."),
         ("risk-manager", "Setting limits on what could cost the company money."),
         ("audit", "Checking that the numbers and the controls can be trusted."),
         ("tax", "Working out and filing what a company owes."),
         ("trader", "Buying and selling assets for a firm or its clients."),
         ("wealth-management", "Planning and managing clients’ money.")],
        ["Postings name certificates: the CFA for investment roles, the CPA for accounting. Check whether it is required or “a plus”.",
         "Excel modeling is tested in interviews. Have one model that you built and can explain.",
         "Bank and fund postings often state base pay only; the bonus is not in the range.",
         "Roles that advise clients may need a license, which the employer usually sponsors after hiring."],
        [("What jobs can you get with a finance degree?", "Financial analysis, accounting, treasury, banking, investment, credit and lending, underwriting, risk, audit, tax, trading and wealth management. {TOP}"),
         ("What is the highest-paying finance degree job?", "{PAY} Bonuses, common in banking and investment, are not part of advertised base ranges."),
         ("Are there entry-level finance jobs?", "Analyst roles are the standard first job. {ENTRY}"),
         ("Do finance jobs require the CFA or a CPA license?", "Some require one and others list it as preferred. The wording tells you: “required” is a filter, “a plus” is not."),
         ("Can you work remotely in finance?", "Corporate finance and accounting roles are sometimes remote; banking and trading rarely. {REMOTE}")],
        (("categories/accounting-finance/", "Accounting and finance jobs"), ("jobs-for/accounting-degree/", "What can you do with an accounting degree?"),
         ("jobs-for/economics-degree/", "What can you do with an economics degree?"), ("salaries/", "Salary data by job title"), ("entry-level/", "Entry-level jobs")))

_degree("marketing-degree", "marketing",
        "Marketing is a dozen different jobs under one word, and a marketing degree does not say which one you can do. "
        "These are the kinds of work graduates commonly move into, with what is open in each today.",
        [("marketing-coordinator", "The usual first job: scheduling, emails, events and campaign materials."),
         ("marketing-manager", "Planning campaigns and answering for their results."),
         ("digital-marketing", "Website, search, social media, email and ads together."),
         ("social-media", "A company’s posts and its conversation with followers."),
         ("content-writer", "Articles and pages that bring readers to a company."),
         ("seo", "Making pages findable in search."),
         ("performance-marketing", "Buying online ads and tuning them for results."),
         ("growth-marketing", "Testing channels and measuring what each returns."),
         ("lifecycle-marketing", "Email and in-app messages timed to each stage of a customer’s life."),
         ("demand-generation", "Campaigns that turn interest into sales leads."),
         ("product-marketing", "Explaining what a product is for, and launching it."),
         ("brand-marketing", "What people think and feel about a brand."),
         ("marketing-analyst", "Measuring which campaigns bring customers."),
         ("events", "Conferences and trade shows, planned and run.")],
        ["Postings name platforms such as Google Ads, Meta Ads, HubSpot and Google Analytics. The vendors’ own certificates are worth having.",
         "Show numbers from any campaign you ran, even for a student club: reach, clicks, sign-ups, cost.",
         "Decide between the writing side and the numbers side; postings split along that line.",
         "Agency roles mean several clients at once. In-house roles mean one brand."],
        [("What jobs can you get with a marketing degree?", "Coordinator and manager roles, digital and social media marketing, content and SEO, paid ads, lifecycle email, demand generation, product and brand marketing, analysis and events. {TOP}"),
         ("What entry-level jobs are there for marketing majors?", "Marketing coordinator, assistant and specialist roles, and social media roles. {ENTRY}"),
         ("Which marketing jobs pay the most?", "Pay differs by specialty and by level. {PAY} The table shows the median for each kind of work."),
         ("Do marketing jobs need a marketing degree?", "Postings usually say “marketing, communications, business or a related field”, and then list tools and results. A portfolio of campaigns counts for as much."),
         ("Are marketing jobs remote?", "Digital, content and lifecycle roles are often remote; events are not. {REMOTE}")],
        (("categories/marketing-communications/", "Marketing and communications jobs"), ("jobs-for/communications-degree/", "What can you do with a communications degree?"),
         ("jobs-for/creative-people/", "Jobs for creative people"), ("entry-level/", "Entry-level jobs"), ("guides/skills-in-demand/", "Skills in demand")))

_degree("political-science-degree", "political science",
        "A political science degree is assumed to lead to politics or to law school. "
        "It also trains research, argument and a sense of how rules are made, and these are the kinds of work graduates commonly move into, with what is open in each today.",
        [("policy", "Following new laws and speaking to regulators for a company: the degree’s subject, applied."),
         ("policy-analyst", "Studying proposed rules and writing the position on them."),
         ("government", "Roles that sell to, build for or deal with governments."),
         ("public-sector-sales", "Selling to public agencies, by their buying rules and tenders."),
         ("public-administration", "Running programs and services for a public body."),
         ("compliance", "Making sure a company follows the rules that apply to it."),
         ("trust-safety", "Writing and applying a platform’s rules on content and conduct."),
         ("paralegal", "Research, drafting and filing for lawyers, without law school."),
         ("communications", "Statements and announcements, weighed word by word."),
         ("public-relations", "Dealing with journalists and answering the press."),
         ("research-analyst", "Studying a market or a field and writing up the findings."),
         ("fundraising-grants", "Raising money for a cause and reporting on its use."),
         ("intelligence-analyst", "Assessing information about threats and events for decision makers."),
         ("program-manager", "Keeping work that involves many teams on schedule.")],
        ["Government and defense postings may require citizenship or a security clearance. It is stated near the top.",
         "Policy roles ask for writing samples: a brief, a memo, a short analysis.",
         "Paralegal postings sometimes ask for a certificate and sometimes train on the job. The posting says which.",
         "Campaign work, internships and student government are experience. Describe them by results."],
        [("What jobs can you get with a political science degree?", "Policy and government affairs, public sector roles, compliance, trust and safety, paralegal work, communications, research and program management. {TOP}"),
         ("Do political science majors have to go to law school?", "No. Lawyer roles need it, but policy, compliance, paralegal, communications and research roles hire with a bachelor’s degree."),
         ("How much do political science degree jobs pay?", "It depends on whether the work is in a company, a public body or a nonprofit. {PAY}"),
         ("Can political science majors work in tech?", "Yes: technology companies hire for public policy, trust and safety, compliance and government sales."),
         ("Are there remote jobs for political science graduates?", "Policy, compliance and research work is sometimes remote. {REMOTE}")],
        (("categories/legal-compliance/", "Legal and compliance jobs"), ("jobs-for/history-degree/", "What can you do with a history degree?"),
         ("jobs-for/criminal-justice-degree/", "What can you do with a criminal justice degree?"), ("jobs-for/philosophy-degree/", "What can you do with a philosophy degree?"), ("entry-level/", "Entry-level jobs")))

_degree("history-degree", "history",
        "History graduates hear that the degree leads only to teaching or to a museum. "
        "What it trains, finding sources, weighing evidence and writing a clear account, is asked for under other names in the kinds of work listed here, with what is open in each today.",
        [("research-analyst", "Gathering sources and writing up what they show."),
         ("paralegal", "Document research and careful summaries for lawyers."),
         ("investigations", "Collecting evidence and writing an account of what happened."),
         ("compliance", "Reading rules closely and checking that they are followed."),
         ("policy", "Tracing how a law came about and what it will change."),
         ("content-writer", "Researched articles on subjects you had to learn first."),
         ("technical-writer", "Turning a mass of detail into an ordered explanation."),
         ("communications", "Clear public writing for a company."),
         ("proposal-manager", "Long documents assembled from many sources, to a deadline."),
         ("education", "Teaching and tutoring, in schools or for education companies."),
         ("government", "Roles that work with governments and public bodies."),
         ("public-administration", "Programs and services run for the public."),
         ("recruiter", "Research into people, and judgment of what their record shows."),
         ("project-manager", "Keeping many strands of work in order.")],
        ["Describe your thesis as a project: the question, the sources, the method and the finding.",
         "Teaching in public schools needs a state license on top of the degree.",
         "Research and compliance postings name their tools, usually spreadsheets and a database. Learn the basics.",
         "Bring a writing sample of two pages, not twenty."],
        [("What jobs can you get with a history degree?", "Research, paralegal work, investigations, compliance, policy, writing, communications, proposals, teaching and public sector roles. {TOP}"),
         ("Is a history degree worth it for getting a job?", "We can only say what postings show: research, analysis and writing are asked for in many kinds of work, and few postings name a degree subject. How you present those skills decides."),
         ("How much do history degree jobs pay?", "{PAY} That figure is for the kind of work, at all levels; no posting prices the degree itself."),
         ("Do history majors need a graduate degree?", "For archives, museums and university teaching, usually yes. For the kinds of work in the table, a bachelor’s degree and evidence of research and writing are what postings ask for."),
         ("Can history graduates work remotely?", "Research and writing work is often remote. {REMOTE}")],
        (("jobs-for/political-science-degree/", "What can you do with a political science degree?"), ("jobs-for/english-degree/", "What can you do with an English degree?"),
         ("jobs-for/liberal-arts-degree/", "What can you do with a liberal arts degree?"), ("categories/legal-compliance/", "Legal and compliance jobs"), ("guides/how-to-write-a-resume/", "How to write a resume")))

_degree("sociology-degree", "sociology",
        "Sociology studies how groups behave, which is what companies try to understand about their employees and their customers. "
        "These are the kinds of work graduates commonly move into, with what is open in each today.",
        [("human-resources", "How organizations treat people, in practice."),
         ("people-operations", "Running the processes of employment fairly and consistently."),
         ("employee-relations", "Handling complaints and conflicts at work."),
         ("recruiter", "Interviewing and assessing people."),
         ("ux-researcher", "Interviews and field observation: the degree’s qualitative methods."),
         ("research-analyst", "Surveys and data about markets and groups."),
         ("marketing-analyst", "Measuring how different groups of customers respond."),
         ("data-analyst", "The statistics from the degree, with SQL added."),
         ("policy", "How rules affect groups of people, argued on a company’s behalf."),
         ("trust-safety", "Deciding what conduct a platform allows, and applying it."),
         ("community-manager", "Looking after a group of users and its norms."),
         ("care-coordinator", "Guiding people through health and social services."),
         ("public-administration", "Programs and services run by public bodies."),
         ("fundraising-grants", "Raising and granting money for social causes.")],
        ["Name your methods: survey design, interviews, coding of responses, statistics, and the software you used.",
         "Social work and counseling roles need a license and usually a graduate degree. The posting names it.",
         "User research postings ask for a portfolio of studies. A course project written up as a case study counts.",
         "Nonprofit and public roles often post pay by grade or band. Read it as a range."],
        [("What jobs can you get with a sociology degree?", "HR and employee relations, recruiting, user and market research, data analysis, policy, trust and safety, community work, care coordination and public programs. {TOP}"),
         ("What do sociology majors do in business?", "They work where a company needs to understand groups: its employees, in HR, and its customers, in research and marketing analysis."),
         ("How much do sociology degree jobs pay?", "It varies widely between research at a software company and work in a public program. {PAY}"),
         ("Do sociology graduates need a master’s degree?", "For licensed social work and for academic research, yes. The kinds of work in the table hire with a bachelor’s degree and evidence of research skills."),
         ("Are there remote jobs for sociology graduates?", "Research, recruiting and community work are often remote. {REMOTE}")],
        (("jobs-for/psychology-degree/", "What can you do with a psychology degree?"), ("categories/hr-recruiting/", "HR and recruiting jobs"), ("jobs-for/helping-others/", "Jobs for people who like helping others"),
         ("jobs-for/political-science-degree/", "What can you do with a political science degree?"), ("entry-level/", "Entry-level jobs")))

_degree("chemistry-degree", "chemistry",
        "A chemistry degree is hands-on, and the work it leads to is mostly on site: labs, plants and test facilities. "
        "These are the kinds of work graduates commonly move into, with what is open in each today.",
        [("chemist", "Making and analyzing compounds and materials."),
         ("lab-technician", "Running experiments and instruments: the usual first job."),
         ("life-sciences", "Laboratory research at biotech and research companies."),
         ("research-scientist", "Leading research, usually after a graduate degree."),
         ("materials-engineer", "Choosing what a product is made of and how it is processed."),
         ("battery-engineer", "Electrochemistry, applied to cells and packs."),
         ("semiconductor-fab", "Deposition, etching and cleaning steps are applied chemistry."),
         ("process-development", "Scaling a lab recipe into a reliable process."),
         ("quality-engineer", "Setting the tests a product must pass."),
         ("quality-inspector", "Measuring and testing samples against a specification."),
         ("manufacturing", "Turning a design into products made in numbers, and checking each one."),
         ("regulatory-affairs", "At chemical and health companies, the documents that regulators ask for."),
         ("ehs", "Safe handling of chemicals, permits and incident reports."),
         ("environmental-engineer", "Sampling, treatment and clean-up of air, water and soil.")],
        ["Postings list instruments and methods by name, such as HPLC, GC-MS or NMR. Match them to your lab courses.",
         "Almost all of this work is on site. Check the place and the shift.",
         "Scientist titles usually ask for a graduate degree; technician, associate and quality roles hire with a bachelor’s degree.",
         "Mention any work under safety or quality rules (GLP, GMP, ISO): regulated labs look for it."],
        [("What jobs can you get with a chemistry degree?", "Chemist and lab roles, materials and battery work, chip manufacturing, process development, quality, regulatory affairs, and environmental and safety work. {TOP}"),
         ("Can you get a job with a bachelor’s degree in chemistry?", "Yes: lab technician, quality and manufacturing roles hire with one. {ENTRY}"),
         ("How much do chemistry degree jobs pay?", "{PAY} Technician roles often state hourly pay, which this yearly median does not count."),
         ("Are chemistry jobs remote?", "Rarely, because the work needs a lab or a plant. Regulatory and documentation roles are the exception. {REMOTE}"),
         ("Do chemistry jobs need a PhD?", "Research scientist roles usually do. Analytical, quality, process and safety roles do not.")],
        (("jobs-for/biology-degree/", "What can you do with a biology degree?"), ("jobs-for/physics-degree/", "What can you do with a physics degree?"), ("categories/science-healthcare/", "Science and healthcare jobs"),
         ("categories/hardware-engineering/", "Hardware and engineering jobs"), ("entry-level/", "Entry-level jobs")))

_degree("physics-degree", "physics",
        "“Physicist” is rarely a job title outside research, yet physics graduates are hired across engineering and data. "
        "These are the kinds of work they commonly move into, with what is open in each today.",
        [("research-scientist", "Research in AI, materials and devices, usually after a graduate degree."),
         ("optics", "Lenses, lasers and sensors: the optics courses, applied."),
         ("quantum", "Quantum computers and their algorithms; mostly graduate-level roles."),
         ("semiconductor-fab", "The processes that turn wafers into chips rest on solid-state physics."),
         ("rf-engineer", "Antennas, radio links and radar: electromagnetism at work."),
         ("thermal-engineer", "Heat and fluid flow in machines."),
         ("simulation-engineer", "Numerical models of physical systems."),
         ("test-engineer", "Designing the experiment that proves hardware works."),
         ("systems-engineer", "Making the parts of a complex product work together."),
         ("hardware-engineer", "Electronics and devices, from circuit to product."),
         ("data-scientist", "Modeling and statistics, carried over from experimental work."),
         ("machine-learning-engineer", "The math of physics is the math of models."),
         ("quant", "Modeling skills from physics, applied to markets."),
         ("software-engineer", "Programming learned for simulations and data analysis, used full time.")],
        ["Postings name tools: Python, MATLAB, a simulation package, lab instruments. List the ones you used, and for what.",
         "Research and quantum roles usually ask for a PhD. Engineering and data roles hire with a bachelor’s or master’s degree.",
         "Aerospace and defense postings may require citizenship or a clearance.",
         "Describe lab work as engineering: what you built, measured and concluded."],
        [("What jobs can you get with a physics degree?", "Research, optics and photonics, chip manufacturing, radio and thermal engineering, simulation, test and systems engineering, data science and software. {TOP}"),
         ("Can physics majors become engineers?", "Yes. Test, systems, optics, RF and simulation postings often ask for a degree in engineering, physics or a related field."),
         ("What is the highest-paying job for a physics graduate?", "{PAY} The roles at the top of the range often ask for a graduate degree."),
         ("Do physics jobs require a PhD?", "Research scientist and quantum roles usually do. Engineering, data and software roles ask for skills that a bachelor’s degree and projects can show."),
         ("Can physics graduates work remotely?", "Data, simulation and software work can be remote; lab and hardware work cannot. {REMOTE}")],
        (("jobs-for/mathematics-degree/", "What can you do with a mathematics degree?"), ("jobs-for/engineering-degree/", "What can you do with an engineering degree?"),
         ("categories/hardware-engineering/", "Hardware and engineering jobs"), ("categories/data-analytics/", "Data and analytics jobs"), ("jobs-for/chemistry-degree/", "What can you do with a chemistry degree?")))

_degree("engineering-degree", "engineering",
        "An engineering degree, whatever the branch, is read by employers as proof that you can solve technical problems to a standard. "
        "These are the kinds of work that graduates of general and mixed engineering programs commonly move into, with what is open in each today.",
        [("mechanical-engineer", "Designing machines and parts."),
         ("electrical-engineer", "Designing circuits and power systems."),
         ("systems-engineer", "Making the parts of a complex product work as one."),
         ("manufacturing-engineer", "Designing how a product is built in numbers."),
         ("quality-engineer", "Setting the tests, and fixing the causes of defects."),
         ("test-engineer", "Proving that hardware works as designed."),
         ("controls-engineer", "Programming the controllers that run lines and plants."),
         ("hardware-engineer", "Electronics and devices, from circuit to product."),
         ("robotics", "Machines that sense, decide and move."),
         ("aerospace", "Aircraft, rockets and satellites."),
         ("civil-engineer", "Roads, sites and structures."),
         ("field-service", "Installing and repairing equipment at customer sites."),
         ("sales-engineer", "The technical expert in a sales team."),
         ("technical-program-manager", "Running technical projects across teams.")],
        ["Postings name the branch and the tools: CAD packages, simulation, programming languages. Match two or three.",
         "Civil and some power roles ask for the FE exam or a PE license. The posting says so.",
         "Aerospace and defense roles may require citizenship or a clearance.",
         "Senior design projects, internships and student teams count as experience. Describe what you built and tested."],
        [("What jobs can you get with an engineering degree?", "Design roles in mechanical, electrical and civil engineering, systems, manufacturing, quality and test engineering, controls, robotics, field service, sales engineering and technical program management. {TOP}"),
         ("Which engineering jobs pay the most?", "{PAY} The table shows a median for every kind of work where at least five postings state a yearly range."),
         ("Are there entry-level engineering jobs?", "Yes. Graduate, junior and intern roles are posted by title. {ENTRY}"),
         ("Do engineers need a PE license?", "For work that is signed off for public use, such as civil and some power engineering, yes. Most product, manufacturing and test roles do not ask for it."),
         ("Can engineers work remotely?", "Simulation, software and sales engineering can be remote; work with hardware is on site. {REMOTE}")],
        (("jobs-for/mechanical-engineering-degree/", "What can you do with a mechanical engineering degree?"), ("jobs-for/electrical-engineering-degree/", "What can you do with an electrical engineering degree?"),
         ("categories/hardware-engineering/", "Hardware and engineering jobs"), ("entry-level/", "Entry-level jobs"), ("internships/", "Internships")), an=True)

_degree("mechanical-engineering-degree", "mechanical engineering",
        "Mechanical engineering is the broadest engineering degree, and postings split it into narrower jobs. "
        "These are the kinds of work its graduates commonly move into, with what is open in each today.",
        [("mechanical-engineer", "Designing machines and parts: the degree’s own title."),
         ("mechanical-design", "Parts and mechanisms drawn in CAD and taken through prototypes."),
         ("manufacturing-engineer", "Designing the process and the tools that build the product."),
         ("tooling-engineer", "Molds, dies and fixtures for making parts in numbers."),
         ("thermal-engineer", "Heat transfer and fluid flow, straight from the core courses."),
         ("structural-engineer", "Loads, stress and fatigue."),
         ("simulation-engineer", "FEA and CFD models that test a design before it is built."),
         ("test-engineer", "Rigs and procedures that prove hardware works."),
         ("quality-engineer", "Finding the cause of defects and removing it."),
         ("supplier-quality", "Auditing suppliers so that their parts meet the specification."),
         ("controls-engineer", "Controllers for lines, plants and machines."),
         ("robotics", "Mechanisms, actuators and their control."),
         ("propulsion-engineer", "Engines for rockets and aircraft."),
         ("automotive-engineer", "Vehicles: body, chassis and powertrain.")],
        ["Postings name the CAD package (SolidWorks, NX, Creo, CATIA) and the simulation tools. Say which you used, and for what part.",
         "Look for GD&T and design for manufacturing in the requirements; both come up in interviews.",
         "Aerospace and defense employers may require citizenship or a clearance.",
         "Bring a project: a drawing, the analysis and what the test showed."],
        [("What jobs can you get with a mechanical engineering degree?", "Mechanical design, manufacturing and tooling, thermal and structural analysis, simulation, test and quality, controls, robotics, propulsion and automotive engineering. {TOP}"),
         ("Which mechanical engineering jobs pay the most?", "{PAY} Pay also differs by industry, which the employer’s name on the posting tells you."),
         ("Are there entry-level mechanical engineering jobs?", "Yes: graduate and junior roles, and internships during the degree. {ENTRY}"),
         ("Can mechanical engineers work remotely?", "Analysis and simulation sometimes; design, test and manufacturing are done where the hardware is. {REMOTE}"),
         ("What software should a mechanical engineering graduate know?", "The CAD and simulation packages that postings name. Read the skills lists of ten postings you like and learn the two that recur.")],
        (("jobs-for/engineering-degree/", "What can you do with an engineering degree?"), ("jobs-for/electrical-engineering-degree/", "What can you do with an electrical engineering degree?"),
         ("categories/hardware-engineering/", "Hardware and engineering jobs"), ("entry-level/", "Entry-level jobs"), ("how-to-become/mechanical-engineer/", "How to become a mechanical engineer")))

_degree("electrical-engineering-degree", "electrical engineering",
        "Electrical engineering covers everything from chips to the power grid, and nobody works on all of it. "
        "These are the kinds of work its graduates commonly move into, each a specialty of its own, with what is open in each today.",
        [("electrical-engineer", "Circuits and electrical systems: the degree’s own title."),
         ("hardware-engineer", "Boards and devices, from schematic to product."),
         ("pcb-engineer", "Laying out circuit boards and bringing up the first ones."),
         ("analog-engineer", "Circuits for radio, power, sensors and high-speed links."),
         ("asic-engineer", "The logic and layout of chips."),
         ("design-verification", "Testing a chip design in simulation before it is made."),
         ("fpga-engineer", "Logic for reprogrammable chips, written in Verilog or VHDL."),
         ("embedded-engineer", "Software that runs inside devices."),
         ("firmware-engineer", "Low-level code that starts a device and drives its hardware."),
         ("rf-engineer", "Antennas, transmitters and radio links."),
         ("power-electronics", "Converters, inverters and motor drives."),
         ("power-systems", "Generation, substations and the grid."),
         ("controls-engineer", "Controllers for factory lines and plants."),
         ("avionics", "The electronics that fly an aircraft or a rocket.")],
        ["Postings name tools: Altium or Cadence for boards, Verilog or VHDL for logic, SPICE for circuits. Match yours.",
         "Chip design roles often ask for a master’s degree. Board, test and power roles hire with a bachelor’s degree.",
         "Power and utility roles may ask for the FE exam or a PE license.",
         "Bring a project you can explain end to end: the schematic, the board, the test."],
        [("What jobs can you get with an electrical engineering degree?", "Hardware and board design, analog and chip design, verification, FPGA work, embedded software and firmware, RF, power electronics, power systems, controls and avionics. {TOP}"),
         ("Which electrical engineering jobs pay the most?", "{PAY} Check the degree level a posting asks for together with its pay."),
         ("Are there entry-level electrical engineering jobs?", "Yes. Graduate programs, junior roles and internships are posted by title. {ENTRY}"),
         ("Can electrical engineers work remotely?", "Chip design and verification are sometimes remote; lab, board and power work is on site. {REMOTE}"),
         ("Can electrical engineers become software engineers?", "Yes. Embedded and firmware roles sit between the two, and postings for them ask for C or C++ next to knowledge of hardware.")],
        (("jobs-for/engineering-degree/", "What can you do with an engineering degree?"), ("jobs-for/mechanical-engineering-degree/", "What can you do with a mechanical engineering degree?"),
         ("jobs-for/computer-science-degree/", "What can you do with a computer science degree?"), ("categories/hardware-engineering/", "Hardware and engineering jobs"), ("entry-level/", "Entry-level jobs")), an=True)

_degree("nursing-degree", "nursing",
        "A nursing degree leads first to patient care, and a nursing license opens more doors than the ward. "
        "These are the kinds of work nursing graduates commonly move into, at the bedside and away from it, with what is open in each today.",
        [("nursing", "Registered nurse roles, in person and by video."),
         ("nurse-practitioner", "Advanced practice, after a graduate degree and certification."),
         ("healthcare", "Clinical roles at health companies and clinics."),
         ("care-coordinator", "Managing patients’ appointments, follow-ups and services."),
         ("mental-health", "Psychiatric and behavioral health roles, with the matching license."),
         ("clinical-research", "Studies of new treatments, where nurses look after the participants."),
         ("clinical-research-coordinator", "The daily running of a study site."),
         ("clinical-informatics", "Clinical knowledge applied to the software clinicians use."),
         ("healthcare-administrator", "Managing a clinic or a service: staff, schedules, budgets."),
         ("public-health", "Health programs for whole populations."),
         ("health-coach", "Helping patients change habits over months."),
         ("insurance", "Claims work at insurers, where a clinical background is used to judge cases."),
         ("medical-writer", "Clinical documents and patient materials."),
         ("medical-science-liaison", "Explaining clinical evidence to doctors; usually asks for an advanced degree.")],
        ["Every clinical posting names the license and the states it must be valid in. Check both first.",
         "Hospital postings state the unit and the shift. Read them before the pay.",
         "Many nursing postings state pay by the hour, which the yearly median here does not count.",
         "New graduates should look for “new grad” or “residency” in the title: those roles include supervised training."],
        [("What jobs can you get with a nursing degree?", "Registered nurse roles first, then care coordination, clinical research, informatics, administration, public health, coaching, insurance review and medical writing. {TOP}"),
         ("Can you work from home with a nursing degree?", "Telehealth, triage and case management are done from home, with a license for the states you serve. {REMOTE}"),
         ("How much do nursing degree jobs pay?", "{PAY} Hospital roles usually state hourly pay and shift differentials, which this yearly median leaves out."),
         ("Do all jobs for nursing graduates need a license?", "Clinical ones do. Research coordination, writing, informatics and administration ask for clinical knowledge, and some postings accept it without an active license."),
         ("Are there jobs for new nursing graduates?", "Yes, often titled new grad or nurse residency. {ENTRY}")],
        (("jobs-for/nurses-leaving-bedside/", "Jobs for nurses leaving bedside care"), ("categories/science-healthcare/", "Science and healthcare jobs"),
         ("jobs-for/public-health-degree/", "What can you do with a public health degree?"), ("jobs-for/helping-others/", "Jobs for people who like helping others")))

_degree("education-degree", "education",
        "An education degree is built for the classroom, and most of what it teaches works outside one. "
        "These are the kinds of work graduates commonly move into, in schools and in companies, with what is open in each today.",
        [("education", "Teaching and tutoring, in schools and at education companies."),
         ("instructional-designer", "Designing courses and lessons, most often for adults."),
         ("corporate-trainer", "Teaching employees new skills and processes."),
         ("training", "Planning and running a company’s learning programs."),
         ("customer-education", "Courses and webinars that teach customers a product."),
         ("education-program-manager", "Running learning programs: content, partners and results."),
         ("program-coordinator", "The day-to-day of a training or community program."),
         ("sales-enablement", "Training materials and sessions for salespeople."),
         ("human-resources", "Onboarding, policies and the development of staff."),
         ("recruiter", "Assessing people and guiding them through hiring."),
         ("customer-success-manager", "Teaching customers to reach their goal with a product."),
         ("content-writer", "Explaining subjects in writing, for learners and readers."),
         ("coordinator", "Organizing schedules, people and paperwork.")],
        ["Public school teaching needs a state license, and postings name the grade and the subject.",
         "Company training roles ask about adult learners: say what you taught adults, parents or colleagues, and how you measured it.",
         "Instructional design postings name authoring tools. A sample module built in one of them is the usual proof.",
         "School jobs follow the school year; company jobs are posted all year round."],
        [("What jobs can you get with an education degree?", "Teaching, instructional design, corporate training, customer education, learning programs, HR, recruiting and customer success. {TOP}"),
         ("What can you do with an education degree besides teach?", "Design courses, train employees or customers, run learning programs, or move into HR and customer success, where explaining and assessing are the daily work."),
         ("How much do education degree jobs pay?", "{PAY} School salaries are usually set by a public scale and are in these figures only when a posting states them."),
         ("Can you work remotely with an education degree?", "Online teaching, instructional design and customer education are often remote. {REMOTE}"),
         ("Do corporate training jobs need a teaching license?", "No. They ask for experience of teaching and for examples of training you designed.")],
        (("jobs-for/former-teachers/", "Jobs for former teachers"), ("categories/education-training/", "Education and training jobs"), ("jobs-for/helping-others/", "Jobs for people who like helping others"),
         ("entry-level/", "Entry-level jobs")), an=True)

_degree("criminal-justice-degree", "criminal justice",
        "A criminal justice degree is linked with policing, but companies also hire people who can investigate, apply rules and write up evidence. "
        "These are the kinds of work graduates commonly move into, with what is open in each today.",
        [("investigations", "Looking into fraud and misconduct, and writing up what happened."),
         ("fraud-analyst", "Spotting stolen cards, fake accounts and scams."),
         ("fraud-risk", "Measuring fraud and setting the rules that stop it."),
         ("aml-kyc", "Checking who customers are and watching for money laundering."),
         ("compliance", "Making sure a company follows the laws that apply to it."),
         ("compliance-officer", "Training staff on the rules and reporting problems to regulators."),
         ("trust-safety", "Reviewing reports of abuse on a platform and enforcing its rules."),
         ("threat-intelligence", "Following criminal groups and scams, and warning what is coming."),
         ("physical-security", "Protecting buildings, people and events."),
         ("industrial-security", "Clearances and classified information at contractors."),
         ("law-enforcement", "Policing and public safety, or a company’s contact with police and courts."),
         ("intelligence-analyst", "Assessing threats, people and events for decision makers."),
         ("paralegal", "Case research and documents for lawyers."),
         ("government", "Roles that work with government and public agencies.")],
        ["Financial crime roles name certificates such as CAMS or CFE. They are usually “preferred”, and can be earned after hiring.",
         "Police and federal roles have their own tests, age limits and background checks, set by the agency.",
         "Background checks are standard in this work. The posting says what is checked.",
         "Describe any casework: what you investigated, how, and what the outcome was."],
        [("What jobs can you get with a criminal justice degree?", "Investigations, fraud and financial crime analysis, compliance, trust and safety, threat intelligence, security, law enforcement and paralegal work. {TOP}"),
         ("What can you do with a criminal justice degree besides policing?", "Work for banks, payment firms and online platforms: investigating fraud, checking customers against money laundering rules, and enforcing platform rules."),
         ("How much do criminal justice degree jobs pay?", "{PAY} Public agencies pay by a published scale, which is in these figures only when a posting states it."),
         ("Are there remote jobs for criminal justice graduates?", "Fraud, compliance and trust and safety analysis are often remote; security and policing are not. {REMOTE}"),
         ("Are there entry-level criminal justice jobs?", "Analyst roles in fraud, compliance and trust and safety take graduates. {ENTRY}")],
        (("categories/security/", "Security jobs"), ("categories/legal-compliance/", "Legal and compliance jobs"), ("jobs-for/political-science-degree/", "What can you do with a political science degree?"),
         ("jobs-for/veterans/", "Jobs for veterans"), ("entry-level/", "Entry-level jobs")))

_degree("graphic-design-degree", "graphic design",
        "A graphic design degree gives you a portfolio, and the portfolio is what gets read. "
        "These are the kinds of work graduates commonly move into, from brand and print to software, with what is open in each today.",
        [("graphic-designer", "Layouts, illustrations and marketing materials."),
         ("brand-designer", "Identity systems: logo, color, type and their rules."),
         ("ui-designer", "How screens look: layout, type, color and icons."),
         ("ux-designer", "How people move through a product."),
         ("product-designer", "Look and behavior together, for a software product."),
         ("design-systems", "The shared library of buttons and patterns for a product."),
         ("motion-designer", "Animation and moving graphics."),
         ("video-editor", "Cutting footage into a finished video."),
         ("art-director", "Setting the visual direction for a team."),
         ("creative-director", "Leading the ideas behind campaigns; reached after years of practice."),
         ("3d-artist", "Models, scenes and renders in three dimensions."),
         ("game-artist", "Characters and worlds for games."),
         ("web-developer", "For designers who also build the site."),
         ("social-media", "A daily stream of images and short video.")],
        ["The portfolio is read before the resume. Put five strong projects in it, each with the brief and the result.",
         "Postings name tools: Figma for product work, Adobe apps for brand and print, After Effects or Blender for motion and 3D.",
         "Product design roles ask for process, not only finished screens: research, sketches, versions.",
         "Check whether the job is in-house or at an agency, and how many people approve the work."],
        [("What jobs can you get with a graphic design degree?", "Graphic and brand design, UI, UX and product design, design systems, motion, video, art direction, 3D and game art. {TOP}"),
         ("Which graphic design degree jobs pay the most?", "{PAY} Roles in software products ask for interaction and research skills on top of visual design."),
         ("Can graphic designers work remotely?", "Often, because the work is delivered as files. {REMOTE}"),
         ("Do you need a degree to be a graphic designer?", "Postings ask for a portfolio first. Some also ask for a degree in design or a related field, and some accept experience in its place."),
         ("How do graphic design graduates move into UX?", "By adding interaction work to the portfolio: a flow of screens, the reasoning behind it and what testing showed. UI designer roles are the usual bridge.")],
        (("jobs-for/creative-people/", "Jobs for creative people"), ("categories/design-creative/", "Design and creative jobs"), ("resume/examples/", "Resume examples by kind of work"),
         ("entry-level/", "Entry-level jobs")))

_degree("journalism-degree", "journalism",
        "A journalism degree trains reporting, interviewing and writing to a deadline, and newsrooms are not the only places that pay for them. "
        "These are the kinds of work graduates commonly move into, with what is open in each today.",
        [("content-writer", "Reported, edited articles for a company’s readers."),
         ("communications", "The other side of the press release."),
         ("public-relations", "Pitching stories to journalists, knowing what they need."),
         ("internal-communications", "A company’s own newsroom, for its staff."),
         ("social-media", "Fast, accurate posts and replies."),
         ("content-designer", "Short, exact text inside products."),
         ("technical-writer", "Interviewing experts and explaining what they said."),
         ("video-editor", "Telling a story by cutting video."),
         ("producer", "Keeping a show, a podcast or a video series on schedule."),
         ("seo", "Headlines and pages built to be found."),
         ("research-analyst", "Digging into a market and reporting what you found."),
         ("investigations", "Gathering evidence and writing the account, as in reporting."),
         ("community-manager", "Moderating and informing an audience."),
         ("policy", "Explaining laws and regulation in plain language.")],
        ["Clips matter most. Choose samples that match the posting: explanatory pieces for content roles, short items for social media.",
         "Company writing is edited by more people than a news story. Ask who approves the text.",
         "Say what your pieces did: readers, shares, replies, corrections avoided.",
         "If independence from sales goals matters to you, read how the role is measured before you apply."],
        [("What jobs can you get with a journalism degree?", "Content writing, communications and PR, social media, the text inside products, technical writing, video and audio production, research and investigations. {TOP}"),
         ("What can journalists do besides journalism?", "Write and edit for companies, handle their press and social media, produce video and podcasts, or research and investigate for a bank or a platform."),
         ("How much do journalism degree jobs pay?", "It depends on the kind of work more than on the degree. {PAY}"),
         ("Are journalism degree jobs remote?", "Writing, editing and social media work is often remote. {REMOTE}"),
         ("Do content jobs want a journalism degree?", "Postings usually ask for journalism, communications, English or a related field, and always for samples.")],
        (("jobs-for/people-who-like-writing/", "Jobs for people who like writing"), ("jobs-for/communications-degree/", "What can you do with a communications degree?"),
         ("jobs-for/english-degree/", "What can you do with an English degree?"), ("categories/writing-translation/", "Writing, editing and translation jobs")))

_degree("philosophy-degree", "philosophy",
        "Philosophy has no profession attached to it, which is the usual joke about the degree. "
        "It trains argument, careful reading and thinking about rules, and these are the kinds of work where graduates commonly use them, with what is open in each today.",
        [("policy", "Arguing what a rule should be, and why."),
         ("paralegal", "Reading closely and reasoning from texts, for lawyers."),
         ("compliance", "Applying rules to cases that the rules did not foresee."),
         ("privacy", "What may be done with personal data, in law and in practice."),
         ("trust-safety", "Writing a platform’s rules and deciding the hard cases."),
         ("ai-safety", "How AI models should behave; the roles also ask for technical or research skills."),
         ("research-analyst", "Studying a question and writing a clear answer."),
         ("ux-researcher", "Asking good questions and drawing careful conclusions."),
         ("business-analyst", "Defining a problem exactly before anyone builds a solution."),
         ("consulting", "Structured reasoning about a client’s problem."),
         ("content-writer", "Clear writing about difficult subjects."),
         ("technical-writer", "Exact definitions, and steps in the right order."),
         ("communications", "Arguments made in public, in plain words."),
         ("recruiter", "Judging people and explaining the decision.")],
        ["Translate the degree into skills on the resume: analysis, writing, argument, logic. Postings use those words.",
         "Add one practical skill that postings name: SQL, a research method, a privacy certificate, a writing portfolio.",
         "Lawyer roles need law school; paralegal, compliance and privacy analyst roles do not.",
         "Bring a short writing sample that explains something hard in two pages."],
        [("What jobs can you get with a philosophy degree?", "Policy, paralegal work, compliance, privacy, trust and safety, research, business analysis, consulting and writing. {TOP}"),
         ("Is a philosophy degree useless for getting a job?", "Postings do not ask for it by name, and they do ask for what it trains: analysis, writing and reasoning about rules. A practical skill added to it makes the match visible."),
         ("How much do philosophy degree jobs pay?", "{PAY} The figure belongs to the kind of work; no posting prices the degree."),
         ("Do philosophy majors go to law school?", "Some do, and lawyer roles require it. Policy, compliance, privacy and paralegal roles are open without it."),
         ("Can philosophy graduates work in AI?", "Policy, trust and safety, and some AI safety roles hire people who reason well about rules and behavior. The postings usually ask for research or technical experience as well.")],
        (("jobs-for/political-science-degree/", "What can you do with a political science degree?"), ("jobs-for/history-degree/", "What can you do with a history degree?"),
         ("jobs-for/liberal-arts-degree/", "What can you do with a liberal arts degree?"), ("categories/legal-compliance/", "Legal and compliance jobs"), ("guides/how-to-write-a-resume/", "How to write a resume")))

_degree("liberal-arts-degree", "liberal arts",
        "A liberal arts degree teaches no single trade, so its graduates are told it leads nowhere. "
        "It leads to work that hires for writing, organization and dealing with people, and these are the kinds graduates commonly move into, with what is open in each today.",
        [("coordinator", "Schedules, orders and paperwork: often a first office job."),
         ("executive-assistant", "Organizing an executive’s or a team’s work."),
         ("sales-development", "A first sales job that hires on how you speak and write."),
         ("account-manager", "Looking after customers over time."),
         ("customer-success-manager", "Making sure customers get what they bought."),
         ("customer-support", "Solving customers’ problems, in writing and by phone."),
         ("recruiter", "Finding and assessing people."),
         ("human-resources", "Policies, contracts and employees’ questions."),
         ("project-manager", "Plans, deadlines and many people to keep informed."),
         ("operations-analyst", "Keeping a team’s daily processes running."),
         ("marketing-coordinator", "Supporting campaigns, posts and events."),
         ("content-writer", "Writing for a company’s readers."),
         ("communications", "What a company says, in public and inside."),
         ("social-media", "Posts and replies in a company’s voice.")],
        ["Lead with what you can do, not with the name of the degree: writing, research, organizing, a language.",
         "Add one skill that postings name, such as Excel, a CRM or a design tool, and say where you used it.",
         "Internships, campus jobs and volunteering are your experience. Give each one a result.",
         "Coordinator and assistant roles are a common first step. Ask in the interview what people in the role moved on to."],
        [("What jobs can you get with a liberal arts degree?", "Coordinator and assistant roles, sales development, account management, customer success and support, recruiting, HR, project management, marketing and writing. {TOP}"),
         ("Do employers hire liberal arts graduates?", "Postings in these kinds of work often ask for a bachelor’s degree without naming a subject, or for skills alone. Writing and organization are what they describe."),
         ("How much do liberal arts degree jobs pay?", "{PAY} That is the median for a whole kind of work; first jobs sit lower in the range."),
         ("What entry-level jobs suit a liberal arts graduate?", "Coordinator, assistant, sales development and support roles. {ENTRY}"),
         ("Can liberal arts graduates work remotely?", "Support, sales, recruiting and writing are often remote. {REMOTE}")],
        (("jobs-for/recent-graduates/", "Jobs for recent graduates"), ("jobs-for/english-degree/", "What can you do with an English degree?"), ("jobs-for/history-degree/", "What can you do with a history degree?"),
         ("entry-level/", "Entry-level jobs"), ("guides/how-to-get-a-job-with-no-experience/", "How to get a job with no experience")))

_degree("accounting-degree", "accounting",
        "Accounting is a degree with a clear first job and many specialties after it. "
        "These are the kinds of work its graduates commonly move into, from the first staff role to the specialties, with what is open in each today.",
        [("accounting", "Recording and reporting a company’s money: the degree’s own field."),
         ("senior-accountant", "Journal entries, reconciliations and the monthly close."),
         ("accounts-payable", "Checking and paying supplier invoices."),
         ("accounts-receivable", "Invoicing customers and collecting payment."),
         ("billing-specialist", "Getting customers’ bills right."),
         ("payroll", "Paying employees correctly and on time, with the taxes withheld."),
         ("bookkeeper", "Recording every transaction and keeping the accounts balanced."),
         ("cost-accountant", "Working out what each product really costs."),
         ("revenue-accountant", "Deciding when sales count as revenue under the rules."),
         ("financial-reporting", "Preparing the official financial statements."),
         ("audit", "Checking that the numbers and the controls can be relied on."),
         ("internal-controls", "Designing and testing the checks that prevent errors and fraud."),
         ("tax", "Working out what is owed and filing the returns."),
         ("controller", "Running the accounting function; reached after years of practice.")],
        ["The CPA license is separate from the degree, with its own exam and experience rules set by each state. Postings say “CPA required” or “CPA preferred”.",
         "Postings name the system: NetSuite, SAP, Oracle, QuickBooks. Say which you have used.",
         "Month end and year end are busy. Ask how long the close takes.",
         "Public accounting and company accounting are different first jobs: one audits many clients, the other keeps one set of books."],
        [("What jobs can you get with an accounting degree?", "Staff and senior accountant roles, payables, receivables and billing, payroll, cost and revenue accounting, financial reporting, audit, controls and tax. {TOP}"),
         ("Do you need a CPA license to work in accounting?", "Not for every role. Payables, receivables, payroll and staff accounting postings often do not ask for it; audit and senior reporting roles often do, and the posting says which."),
         ("How much do accounting degree jobs pay?", "{PAY} The table shows a median for every kind of work where at least five postings state a yearly range."),
         ("Are accounting jobs remote?", "Company accounting roles are sometimes remote or hybrid; audit work can involve visits to clients. {REMOTE}"),
         ("Are there entry-level accounting jobs?", "Staff accountant, accounts payable and accounts receivable roles are the usual first jobs. {ENTRY}")],
        (("jobs-for/finance-degree/", "What can you do with a finance degree?"), ("categories/accounting-finance/", "Accounting and finance jobs"), ("salaries/", "Salary data by job title"),
         ("entry-level/", "Entry-level jobs"), ("how-to-become/accounting/", "How to become an accountant")), an=True)

_degree("information-technology-degree", "information technology",
        "An information technology degree is about running systems rather than writing them, and the job titles reflect it. "
        "These are the kinds of work graduates commonly move into, from the help desk to the cloud, with what is open in each today.",
        [("it-support", "Fixing colleagues’ computers, accounts and software: the usual first job."),
         ("help-desk", "First-line support by phone, chat and ticket."),
         ("system-administrator", "Servers, accounts and the software a company runs on."),
         ("network-engineer", "The networks that connect offices and data centers."),
         ("cloud-engineer", "Running software on rented servers at the large cloud providers."),
         ("devops-engineer", "Automating how software is deployed and run."),
         ("database-administrator", "Keeping databases fast, backed up and safe."),
         ("data-center", "Installing and repairing the servers themselves."),
         ("cybersecurity", "Protecting systems and responding to attacks."),
         ("security-analyst", "Watching alerts and investigating incidents."),
         ("identity-access-management", "Deciding who can log in to what."),
         ("endpoint-engineer", "Setting up and securing every laptop and phone from one place."),
         ("business-systems", "Running the business software a company works in every day."),
         ("it-manager", "Leading an IT team; reached after years in the roles above.")],
        ["Postings name certificates: CompTIA A+, Network+ and Security+, CCNA, AWS or Azure. One that matches the role is worth more than three that do not.",
         "Support and data center roles can run in shifts or include on-call duty. The posting says so.",
         "Describe your own equipment and projects: a home network, a server, a script that saved time.",
         "Check whether the role serves one office or a whole company working remotely; the tools differ."],
        [("What jobs can you get with an information technology degree?", "IT support and help desk, system and network administration, cloud and DevOps, databases, data center work, security and identity, and business systems. {TOP}"),
         ("What is the difference between IT jobs and computer science jobs?", "IT work runs and secures systems; computer science work mostly builds software. Postings overlap in cloud, DevOps and security roles."),
         ("How much do information technology degree jobs pay?", "{PAY} The table has the median for each kind of work, and a first job in support will sit lower in its range."),
         ("Are there entry-level IT jobs?", "Help desk and IT support are the standard first jobs. {ENTRY}"),
         ("Can IT jobs be done remotely?", "Cloud, security and system administration often can; work on hardware cannot. {REMOTE}")],
        (("jobs-for/computer-science-degree/", "What can you do with a computer science degree?"), ("categories/cloud-devops-it/", "Cloud, DevOps and IT jobs"), ("categories/security/", "Security jobs"),
         ("skill-tests/", "Skill self-tests"), ("entry-level/", "Entry-level jobs")), an=True)

_degree("public-health-degree", "public health",
        "Public health is about the health of groups rather than of single patients, so its jobs are in programs, data and rules. "
        "These are the kinds of work graduates commonly move into, with what is open in each today.",
        [("public-health", "Studying the health of populations, to guide programs and policy."),
         ("healthcare", "Clinical and support roles at health companies."),
         ("healthcare-administrator", "Running a clinic or a health service: staff, budgets and rules."),
         ("care-coordinator", "Guiding patients to the services they need."),
         ("clinical-research", "Studies that test whether treatments work."),
         ("clinical-research-coordinator", "Recruiting participants and keeping a study’s records."),
         ("statistician", "Study design and biostatistics."),
         ("data-analyst", "Health data turned into counts, rates and trends."),
         ("research-analyst", "Gathering evidence and writing up what it shows."),
         ("policy", "Health law and regulation, followed for an organization."),
         ("policy-analyst", "Studying proposed rules and their effects."),
         ("ehs", "Occupational health and safety: inspections, training, incident reports."),
         ("regulatory-affairs", "At health companies, dealing with the agencies that approve their products."),
         ("program-manager", "Planning health programs and keeping them on schedule.")],
        ["Many public health roles ask for a master’s degree (MPH). The posting says “required” or “preferred”.",
         "Data roles name tools: SAS, R, Stata, SQL. Say which you used in your coursework.",
         "Government and nonprofit postings often depend on grant funding and state an end date.",
         "Fieldwork, internships and a capstone project count as experience. Describe the population, the method and the result."],
        [("What jobs can you get with a public health degree?", "Program and policy work, health data analysis and biostatistics, clinical research, care coordination, healthcare administration, occupational safety and regulatory affairs. {TOP}"),
         ("Do public health jobs require a master’s degree?", "Epidemiology and senior program roles usually do. Coordinator, analyst and safety roles hire with a bachelor’s degree."),
         ("How much do public health degree jobs pay?", "{PAY} Public and nonprofit employers pay by a published scale, which is in these figures only when the posting states it."),
         ("Are there remote public health jobs?", "Data, policy and research work can be remote; program and field work is local. {REMOTE}"),
         ("Are there entry-level public health jobs?", "Coordinator and analyst roles are the usual start. {ENTRY}")],
        (("jobs-for/nursing-degree/", "What can you do with a nursing degree?"), ("jobs-for/biology-degree/", "What can you do with a biology degree?"), ("categories/science-healthcare/", "Science and healthcare jobs"),
         ("entry-level/", "Entry-level jobs")))


def test(valid=None, site=None):
    """Checks every entry. valid: the role slugs of the site (read from build.py when not given); site: a built site folder, to check the related links."""
    if valid is None:
        import build
        valid = {s for _, s, _ in build.ROLES}
    bad, seen = [], {k: {} for k in ("slug", "name", "title", "h1", "desc", "lead", "question")}
    def once(kind, value, where):
        if value in seen[kind]: bad.append(f"{where}: {kind} repeated from {seen[kind][value]}: {value[:60]}")
        seen[kind][value] = where
    slugs = {a["slug"] for a in ENTRIES}
    if len(HUB_TITLE) > 60: bad.append(f"the hub's title is {len(HUB_TITLE)} characters")
    bad += [f"the hub's description is {len(d)} characters" for n_ in ("312", "1,234,567") if not 125 <= len(d := HUB_DESC.format(k=len(ENTRIES), n=n_)) <= 160]
    for a in ENTRIES:
        w = a["slug"]
        for k in ("slug", "name", "title", "h1", "desc", "lead"): once(k, a[k], w)
        if a["group"] not in ("who", "degree"): bad.append(f"{w}: group {a['group']}")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", w): bad.append(f"{w}: slug")
        if not 20 <= len(a["title"]) <= 60: bad.append(f"{w}: title is {len(a['title'])} characters")
        for n_, k_ in (("312", "8"), ("123,456", "14")):
            d = a["desc"].replace("{n}", n_).replace("{k}", k_)
            if not 125 <= len(d) <= 160: bad.append(f"{w}: description is {len(d)} characters with {n_} jobs")
        if "{n}" not in a["desc"]: bad.append(f"{w}: description without the live count")
        if a["lead"].count(". ") + a["lead"].count("? ") != 1 or not a["lead"].endswith("."): bad.append(f"{w}: the lead is not two sentences")
        rs = [s for s, _ in a["roles"]]
        if not 8 <= len(rs) <= 14: bad.append(f"{w}: {len(rs)} kinds of work")
        if len(set(rs)) != len(rs): bad.append(f"{w}: a kind of work twice")
        bad += [f"{w}: unknown role {s}" for s in rs if s not in valid]
        bad += [f"{w}: a reason that is not one line: {y[:50]}" for _, y in a["roles"] if not 25 <= len(y) <= 140 or not y.endswith(".")]
        if not 3 <= len(a["check"]) <= 5: bad.append(f"{w}: {len(a['check'])} things to check")
        if not 4 <= len(a["faq"]) <= 5: bad.append(f"{w}: {len(a['faq'])} questions")
        for q, x in a["faq"]:
            once("question", q, w)
            if not q.endswith("?"): bad.append(f"{w}: not a question: {q}")
            plain = x
            for t in TOKENS: plain = plain.replace(t, "")
            if "{" in plain or "}" in plain: bad.append(f"{w}: unknown token in the answer to: {q}")
            if len(plain.strip()) < 40: bad.append(f"{w}: the answer says nothing without the day's figures: {q}")
        if not 3 <= len(a["more"]) <= 5: bad.append(f"{w}: {len(a['more'])} related links")
        for u, t in a["more"]:
            if u.startswith("/") or not u.endswith("/"): bad.append(f"{w}: link {u}")
            if u.startswith("jobs-for/") and u != "jobs-for/" and u[9:-1] not in slugs: bad.append(f"{w}: link to a page that is not here: {u}")
            if u == f"jobs-for/{w}/": bad.append(f"{w}: links to itself")
            if site is not None and not u.startswith("jobs-for/") and not (site / u / "index.html").is_file(): bad.append(f"{w}: no such page on the built site: {u}")
        bad += [f"{w}: unknown extra column {k}" for k in a.get("extra", ()) if k not in EXTRA]
        text = " ".join([a["title"], a["desc"], a["h1"], a["lead"], a.get("note", ""), note_of(a)] + [y for _, y in a["roles"]] + a["check"] + [q + " " + x for q, x in a["faq"]] + [t for _, t in a["more"]])
        for rx, why in ((r"—", "an em dash"), (r"['\"]", "a straight quote"), (r"\b(adhd|anxiety|depress\w*|autis\w*|disorder|disabilit\w*|dyslexi\w*|bipolar)\b", "a health word"),
                        (r"\b((?:organ|special|recogn|custom|summar|priorit|optim|emphas|apolog|minim|maxim)is(?:e|es|ed|ing|ation)|analys(?:e|ed|ing)|colour\w*|favour\w*|behaviour\w*|centre|programme|licence|labour|catalogue|defence|practise|modelling|travelling|counsell\w+|grey|judgement|enrol|fulfil|skilful)\b", "British spelling")):
            m = re.search(rx, text, re.I)
            if m: bad.append(f"{w}: {why}: …{text[max(0, m.start() - 30):m.end() + 20]}…")
    return bad


if __name__ == "__main__":
    import sys
    from pathlib import Path
    site_ = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    problems = test(site=site_)
    print("\n".join(problems) if problems else
          f"OK: {len(ENTRIES)} pages ({sum(1 for a in ENTRIES if a['group'] == 'who')} by situation, {sum(1 for a in ENTRIES if a['group'] == 'degree')} by degree), "
          f"{len({s for a in ENTRIES for s, _ in a['roles']})} kinds of work used" + (", related links checked against the built site" if site_ else ""))
    sys.exit(1 if problems else 0)
