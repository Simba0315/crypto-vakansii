"""Drafts, with Claude, the resume example entries that kinds of work still lack, and keeps the ones that pass the module's rules.

Why (owner, 20 Nov 2026): 248 of the 390 pages under /resume/examples/ had no entry of their own in resume_examples.ROLE and showed
the lines of their field (the actuary "ran the yearly budget for 14 departments"); the CV, cover letter and how-to-become pages read
the same entry. The owner had API credit about to expire, so the entries are drafted in one Message Batch (half the price of single
requests) and every line is checked by resume_examples.line_problem() and the rules of its test() before it is kept. Lines that fail
go back once with the reason; what still fails stays out. Kept entries land in resume_examples_more.json, which resume_examples.py
reads; they are read through before they are committed.

The API key is the owner's: it comes from ANTHROPIC_API_KEY in his own terminal, or is asked for without being shown. It is never
written anywhere.

    python3 ai_fill.py resume --dry-run     what would be sent: the number of requests, the estimated cost, the first request
    python3 ai_fill.py resume               send the batch, wait for it, check the answers, write resume_examples_more.json
    python3 ai_fill.py resume --limit 5     the same for the first five kinds of work only
    python3 ai_fill.py interview [--dry-run] [--limit N]
                                            questions of each kind of work's own trade for /interview-questions/<role>/, drafted in one
                                            batch, then read in a second batch that looks only for wrong or doubtful facts; a question
                                            it doubts is left out. Kept sets land in interview_more.json, read by interview_bank.py.

    python3 ai_fill.py glossary [--dry-run] [--limit N]
                                            the long answer ("What is ...?") for the glossary terms that have only two lines, drafted in
                                            one batch and read in a second for wrong or doubtful facts: glossary_more.json.
    python3 ai_fill.py become [--dry-run] [--limit N]
                                            what it takes to enter each kind of work (training, licences, exams, how long) for
                                            /how-to-become/<role>/, drafted and then read for wrong facts: become_more.json.
    python3 ai_fill.py glossary become audit
                                            several jobs one after another, with the key asked once
    python3 ai_fill.py glossary become --retry
                                            once more for what the fact check refused, with its reasons in the request
    python3 ai_fill.py audit [--dry-run] [--limit N]
                                            an expert read of the hand-written pages (glossary, resume words, guides, resignation
                                            letters, comparisons, tools, skills, perks, insights, salary and relocation pages) that
                                            lists only wrong or misleading statements, each with the page's exact words and the
                                            fix: data/ai_audit.json. Nothing on the site changes by itself; the fixes are made in
                                            the source modules by hand.

Interrupted while waiting? Run it again: the batch id is kept in data/ai_fill_state.json and the script picks up the same batch.
"""
import concurrent.futures as cf, getpass, html, json, os, re, sys, time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import glossary_terms as gt, interview_bank as ib, resume_examples as rx, roles_info        # noqa: E402

MODEL = "claude-opus-5-5"
STATE = ROOT / "data" / "ai_fill_state.json"
OUT = rx.MORE_FILE
PAGES = ROOT / "site" / "resume" / "examples"
# Work whose example is laid out for a student or a first job (resume_examples.example says "five years of experience"):
# left out until that layout exists for them, as it does for "intern".
SKIP = {"summer-intern", "engineering-intern", "junior-software-engineer", "phd", "fellowship-residency"}
PRICE = {"batch": (2.0, 10.0), "single": (4.0, 20.0)}     # dollars per million input and output tokens, Claude Opus 5.5
FEW = ["data-analyst", "accounting", "customer-support", "hospitality", "technician"]

SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["title", "plain", "achievements", "entry", "senior", "entry_title", "tech"],
          "properties": {"title": {"type": "string"}, "plain": {"type": "string"},
                         "achievements": {"type": "array", "items": {"type": "string"}},
                         "entry": {"type": "array", "items": {"type": "string"}},
                         "senior": {"type": "array", "items": {"type": "string"}},
                         "entry_title": {"type": "string"}, "tech": {"type": "boolean"}}}


def shown(slug):
    m = rx.ROLE[slug]
    return {"title": m[0], "plain": m[1], "achievements": m[2], "entry": rx.ENTRY[slug], "senior": rx.SENIOR[slug],
            "entry_title": rx.ENTRY_TITLE.get(slug, ""), "tech": slug in rx.TECH}


def system_prompt():
    kinds = "\n".join(f"- {{{k}:...}}: {', '.join(v)}" for k, v in rx.KIND.items())
    office = ", ".join(sorted(rx.OFFICE))
    examples = "\n\n".join(f"Kind of work: {s}\n{json.dumps(shown(s), ensure_ascii=False, indent=1)}" for s in FEW)
    return f"""You write the example resume entries of a US job board (jobseveryhour.com). Each page "<work> resume example" shows an invented person, "Alex Example", with invented employers and invented figures, next to what today's job postings for that work ask for. You write one entry for one kind of work. Your text is published as is, so it must read like a strong real resume of that exact profession, not of a neighbouring one.

The entry has:
- title: the job title the person carries on the resume, as US employers write it, Title Case, at most 40 characters. A person, never a field: "Actuarial Analyst" or "Actuary", not "Actuarial Science".
- plain: 3 to 5 skills of that work in plain words, lower case except names and acronyms, separated by commas, so that it reads well after "my focus is". No software or tool names: tools come from the postings.
- achievements: 4 lines for someone with about five years in the work.
- entry: 3 lines a beginner can honestly have, in this order: a course, degree project, bootcamp or personal project; an internship, placement or first job; volunteer or part-time work. Keep the scale small and believable for a beginner.
- senior: 3 lines for someone years further on, in this order: leading a team; owning a strategy or a large program; hiring and mentoring, or a result reached together with other teams.
- entry_title: the beginner's title, only where it is not simply "Junior" before the title ("Staff Accountant" for a Senior Accountant, "Line Cook" for a Sous Chef, "Actuarial Analyst" for an Actuary). Otherwise an empty string.
- tech: true only for software, data, IT, security or other engineering work where technical skill tags in postings (languages, cloud, databases) describe the person's own job. False for everything else, including sales, marketing, finance, legal, HR, operations, healthcare and trades, even at technology companies.

Every line (achievements, entry, senior):
- Starts with a past-tense verb that says what the person did ("Priced", "Reduced", "Led"). Never "Worked", "Helped", "Responsible", "I", "My", "The".
- Says one result with one number: a count, a percentage, money, time. At least 3 of the 4 achievements and every entry and senior line carry a number. Figures must be plausible for the work and the level.
- Is specific to this exact work: its real tasks, objects and measures (an actuary: reserves, pricing, loss ratios, exams; a welder: joints, codes, rework). A reader from that profession must recognise it.
- At most 140 characters. No full stop at the end. Use ’ (curly), never a straight apostrophe '. No semicolons at the start, no quotation marks.
- Names no real employer, school, client or product. Real professional credentials, exams and laws may be named when they truly exist and fit the US market, spelled exactly ("SOA Exam P", "CPA", "PMP", "OSHA 30", "ASE certification", "HIPAA"). A credential whose name contains a tool from the list below (a cloud or CRM certification) must not be named.
- A software tool or technology may appear ONLY through a typed place written {{kind:default}}: the site puts there the first tool of that kind that today's postings name, or the default when they name none. The kinds and the tools each may hold:
{kinds}
  The default must be one of the tools of that kind. Never write any of these tools outside a typed place: {', '.join(sorted({t for ts in rx.KIND.values() for t in ts}))}, {office}. Use a typed place only where any tool of its kind would make the sentence true ("a dashboard in {{bi:Tableau}}"). Most work outside software needs no typed place at all.
- The ENTRY and SENIOR lines must differ from each other and from the achievements.

Examples of finished entries (from other kinds of work):

{examples}

Answer with the JSON object only."""


def user_prompt(r):
    parts = [f"Kind of work: {r['slug']}", f"Name on the site: {r['name']}"]
    if r["what"]: parts.append(f"What the person does: {r['what']}")
    if r["family"]: parts.append(f"Field: {r['family']}")
    if r["postings"]: parts.append(f"Open postings for this work today: {r['postings']}")
    if r["asked"]: parts.append(f"What today's postings ask for: {r['asked']}")
    return "\n".join(parts) + "\n\nWrite the entry for this kind of work."


def todo():
    fam = {s: name for fs, name, _d, slugs in roles_info.FAMILIES for s in slugs}
    out = []
    for d in sorted(PAGES.iterdir()):
        slug = d.name
        if not d.is_dir() or slug in rx.ROLE or slug in SKIP: continue
        t = (d / "index.html").read_text()
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        name = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).replace(" resume example", "").strip() if h1 else slug.replace("-", " ")
        n = re.search(r"what ([\d,]+) open postings", t)
        top = re.search(r'"What are the top 3 skills for [^"]+","acceptedAnswer":\{"@type":"Answer","text":"([^"]+)"', t)
        asked = html.unescape(top.group(1)).replace("By today’s postings for this work: ", "").rstrip(".") if top else ""
        out.append({"slug": slug, "name": name, "what": roles_info.what(slug, name), "family": fam.get(slug, ""),
                    "postings": n.group(1) if n else "", "asked": asked})
    return out


def problems(slug, e, taken):
    """What is wrong with an answer, [] when it can be kept. `taken`: the ENTRY and SENIOR lines already in use."""
    bad = []
    if not e.get("title") or len(e["title"]) > 40 or not e["title"][0].isupper(): bad.append("title: a job title in Title Case, at most 40 characters")
    plain = [x.strip() for x in (e.get("plain") or "").split(",") if x.strip()]
    if not 3 <= len(plain) <= 6: bad.append("plain: 3 to 5 skills separated by commas")
    tools = {t.lower() for ts in rx.KIND.values() for t in ts} | {t.lower() for t in rx.OFFICE}
    if any(x.lower() in tools for x in plain): bad.append("plain: no tool names")
    for key, n in (("achievements", 4), ("entry", 3), ("senior", 3)):
        lines = e.get(key) or []
        if len(lines) != n: bad.append(f"{key}: exactly {n} lines"); continue
        for ln in lines:
            why = rx.line_problem(ln)
            if not why and (ln.split()[0] in rx.NOT_VERB or not ln.split()[0].isalpha()): why = "start with a past-tense verb"
            if not why and len(ln) > 150: why = "at most 140 characters"
            if not why and key != "achievements" and not re.search(r"\d", ln): why = "carry a number"
            if not why and key != "achievements" and ln in taken: why = "this line is already used by another kind of work"
            if why: bad.append(f"{key} line “{ln}”: {why}")
        if key == "achievements" and sum(bool(re.search(r"\d", ln)) for ln in lines) < 3: bad.append("achievements: at least 3 of the 4 carry a number")
    sub = (e.get("entry") or []) + (e.get("senior") or [])
    if len(sub) != len(set(sub)): bad.append("entry and senior lines must all differ")
    et = e.get("entry_title") or ""
    if et and (et == "Junior " + (e.get("title") or "") or not et[0].isupper()): bad.append("entry_title: empty unless it is not simply Junior + title")
    return bad


def keep(e):
    return {"title": e["title"].strip(), "plain": ", ".join(x.strip() for x in e["plain"].split(",") if x.strip()),
            "lines": e["achievements"], "entry": e["entry"], "senior": e["senior"], "entry_title": (e.get("entry_title") or "").strip(),
            "tech": bool(e.get("tech"))}


def params(system, r, fix=None):
    msgs = [{"role": "user", "content": user_prompt(r)}]
    if fix: msgs = [{"role": "user", "content": user_prompt(r) + "\n\nA first answer was:\n" + json.dumps(fix[0], ensure_ascii=False)
                     + "\n\nIt broke these rules; write the whole entry again, keeping what was good:\n- " + "\n- ".join(fix[1])}]
    return {"model": MODEL, "max_tokens": 16000,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
            "messages": msgs}


def text_of(msg):
    return next((b.text for b in msg.content if b.type == "text"), "")


def cost(usage, kind):
    i, o = PRICE[kind]
    u = lambda k: getattr(usage, k, 0) or 0
    return (u("input_tokens") * i + u("cache_creation_input_tokens") * i * 1.25 + u("cache_read_input_tokens") * i * 0.1 + u("output_tokens") * o) / 1e6


_CLIENT = []


def client():
    if _CLIENT: return _CLIENT[0]
    import anthropic
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip() or getpass.getpass("Вставьте ключ API (его не будет видно) и нажмите Enter: ").strip()
    if not key: sys.exit("Нет ключа, ничего не отправлено.")
    _CLIENT.append(anthropic.Anthropic(api_key=key, max_retries=4))
    return _CLIENT[0]


def resume(argv):
    rows = todo()
    if "--limit" in argv: rows = rows[:int(argv[argv.index("--limit") + 1])]
    system = system_prompt()
    by = {r["slug"]: r for r in rows}
    if "--dry-run" in argv:
        est = len(rows) * ((len(system) / 3.5 * 0.3 + 300) * 2 + 5000 * 10) / 1e6
        print(f"{len(rows)} kinds of work without an entry ({len(SKIP)} student layouts left out); about ${est:.0f} at batch prices "
              f"(the system prompt is about {len(system) / 3.5:,.0f} tokens, cached)")
        print("\n--- system ---\n" + system + "\n\n--- first request ---\n" + user_prompt(rows[0]))
        return 0
    c = client()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    bid = state.get("batch")
    if bid and state.get("slugs") != sorted(by):
        print(f"Предыдущий пакет {bid} был для другого списка, начинаю новый."); bid = None
    if not bid:
        reqs = [{"custom_id": s, "params": params(system, r)} for s, r in by.items()]
        b = c.messages.batches.create(requests=reqs)
        bid = b.id
        STATE.write_text(json.dumps({"batch": bid, "slugs": sorted(by), "sent": time.strftime("%Y-%m-%d %H:%M")}))
        print(f"Отправлено {len(reqs)} запросов одним пакетом ({bid}). Обычно готово за 10–60 минут; окно можно не закрывать.", flush=True)
    else:
        print(f"Жду пакет, отправленный раньше: {bid}", flush=True)
    t0 = time.time()
    while True:
        b = c.messages.batches.retrieve(bid)
        k = b.request_counts
        if b.processing_status == "ended": break
        print(f"  {time.strftime('%H:%M')}: готово {k.succeeded + k.errored + k.canceled + k.expired} из {len(by)}, ждём… ({(time.time() - t0) / 60:.0f} мин)", flush=True)
        time.sleep(60)
    print(f"Пакет готов: {k.succeeded} ответов, ошибок {k.errored}, просрочено {k.expired}.")
    taken = {ln for d in (rx.ENTRY, rx.SENIOR) for lines in d.values() for ln in lines}
    kept = json.loads(OUT.read_text()) if OUT.exists() else {}
    spent, again = 0.0, {}
    for res in c.messages.batches.results(bid):
        s = res.custom_id
        if res.result.type != "succeeded": again[s] = None; continue
        msg = res.result.message
        spent += cost(msg.usage, "batch")
        try: e = json.loads(text_of(msg))
        except ValueError: again[s] = None; continue
        bad = problems(s, e, taken) if msg.stop_reason == "end_turn" else [f"the answer stopped early ({msg.stop_reason})"]
        if bad: again[s] = (e, bad)
        else:
            kept[s] = keep(e); taken |= set(e["entry"] + e["senior"])
    print(f"Прошли проверку с первого раза: {len(by) - len(again)}; переписываю ещё раз: {len(again)}", flush=True)

    def redo(s):
        try:
            m = c.messages.create(**params(system, by[s], again[s]))
            return s, m, json.loads(text_of(m))
        except Exception as ex:
            return s, None, ex
    still = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for s, m, e in ex.map(redo, list(again)):
            if m is None or isinstance(e, Exception): still[s] = [f"{type(e).__name__}"]; continue
            spent += cost(m.usage, "single")
            bad = problems(s, e, taken) if m.stop_reason == "end_turn" else [f"stopped ({m.stop_reason})"]
            if bad: still[s] = bad
            else: kept[s] = keep(e); taken |= set(e["entry"] + e["senior"])
    OUT.write_text(json.dumps(dict(sorted(kept.items())), ensure_ascii=False, indent=1) + "\n")
    (ROOT / "data" / "ai_fill_left.json").write_text(json.dumps(still, ensure_ascii=False, indent=1))
    STATE.unlink(missing_ok=True)
    print(f"\nГотово. Записано {len(kept)} новых примеров в {OUT.name}; не прошли проверку {len(still)} (data/ai_fill_left.json).")
    print(f"Потрачено примерно ${spent:.2f}.")
    return 0


# ---- interview questions -----------------------------------------------------------------------------------------------------

IQ_PAGES = ROOT / "site" / "interview-questions"
IQ_STATE = ROOT / "data" / "ai_fill_interview.json"
IQ_GEN = ROOT / "data" / "ai_interview_drafts.json"
IQ_N = 10
IQ_FEW = [("Statistics questions", 0), ("Statistics questions", 3), ("Customer support questions", 0), ("Trades and technical work questions", 0),
          ("Healthcare and science questions", 0), ("Accounting and finance questions", 0)]
Q_ITEM = {"type": "object", "additionalProperties": False, "required": ["question", "checks", "good", "sample"],
          "properties": {k: {"type": "string"} for k in ("question", "checks", "good", "sample")}}
IQ_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["questions"],
             "properties": {"questions": {"type": "array", "items": Q_ITEM}}}
CHECK_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdicts"],
                "properties": {"verdicts": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["n", "keep", "reason"],
                                                                         "properties": {"n": {"type": "integer"}, "keep": {"type": "boolean"}, "reason": {"type": "string"}}}}}}


def iq_system():
    subj = {h: qs for h, _w, qs in ib.SUBJECTS}
    ex = [dict(zip(("question", "checks", "good", "sample"), subj[h][i])) for h, i in IQ_FEW if h in subj and len(subj[h]) > i]
    return f"""You write interview questions for the pages "<work> interview questions" of a US job board (jobseveryhour.com). The page already has questions about the skills the postings name, general questions ("Tell me about yourself") and questions shared by the whole field of work. You write the questions of this one trade only: what an interviewer who does this exact work asks a candidate, the things a person from a neighbouring job could not answer.

Write {IQ_N} questions. Each has four parts:
- question: as the interviewer says it, ending with ? (or . for a task: "Walk me through ..."). Mix: knowledge of the trade, a practical situation, a judgement call, a mistake or a problem to handle. From easier to harder.
- checks: what the question checks, one short sentence ending with a full stop, at most 110 characters. The page prints it after "What it checks: ", so start with a word that reads well there: "Whether you ...", "How you ...", "Your ...", "The ...".
- good: what a good answer shows, one or two short sentences, at most 180 characters, ending with a full stop.
- sample: a sample answer in the first person, 150 to 400 characters, ending with a full stop. Concrete, as a strong candidate would say it. Names no real employer, client, school or product; figures in a story are invented and plausible.

Facts matter most. Every fact a sample answer or a "good" states (a definition, a rule, a law, a standard, a method, a safe practice) must be exactly right for the US today. Where you are not sure of a fact, choose another question. Do not state current official figures that change (tax rates, legal limits, wage rates, drug doses); describe the method or the rule instead. No advice that would be unsafe if followed.

Style: plain American English, short sentences, no jargon left unexplained in the sample. Never use the long dash (—); use a comma, a colon or a new sentence. Do not repeat or reword the questions the page already has, which are listed in each request.

Examples of finished questions from other pages:
{json.dumps(ex, ensure_ascii=False, indent=1)}

Answer with the JSON object only."""


CHECK_SYSTEM = """You check interview questions with sample answers before they are published on a US job board. Read every question and its parts as an expert in that exact work would, and look only for things that are wrong: a fact, definition, rule, law, standard or safe practice that is incorrect, outdated, misleading or doubtful for the US today; advice that would be unsafe or unlawful if followed; a sample answer that would make an interviewer from this trade frown; a question that does not belong to this work. Style is not your concern.

For each question give n (its number), keep (false if anything in it is wrong or you are not sure it is right; true only when you would sign it as correct) and reason (one short sentence; for a kept question, "correct"). Be strict: a question left out costs little, a wrong answer on the page misleads a job seeker. Answer with the JSON object only."""


def iq_rows(more=False):
    """The interview pages to write for: those without questions of their own, or with `more`, those that have them (a second,
    harder set; the page's own questions count as questions it already has)."""
    fam = {s: (fs, name) for fs, name, _d, slugs in roles_info.FAMILIES for s in slugs}
    own, ib.OWN = dict(ib.OWN), {}
    out = []
    try:
        for d in sorted(IQ_PAGES.iterdir()):
            slug = d.name
            if not d.is_dir() or (slug not in own if more else slug in own): continue
            t = (d / "index.html").read_text()
            h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
            name = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).split(" interview questions")[0].strip() if h1 else slug.replace("-", " ")
            fs, fname = fam.get(slug, ("operations-administration", "Operations and administration"))
            have = [q[0] for _h, qs in ib.pick(slug, fs, {}) for q in qs] + ([q[0] for q in own[slug][1]] if more and slug in own else [])
            focus = rx.ROLE[slug][1] if slug in rx.ROLE else ""
            out.append({"slug": slug, "name": name, "what": roles_info.what(slug, name), "family": fname, "focus": focus, "have": have})
    finally:
        ib.OWN = own
    return out


def iq_user(r):
    parts = [f"Kind of work: {r['slug']}", f"Name on the site: {r['name']}"]
    if r["what"]: parts.append(f"What the person does: {r['what']}")
    parts.append(f"Field: {r['family']}")
    if r["focus"]: parts.append(f"The core of the work: {r['focus']}")
    if r["have"]: parts.append("Questions the page already has (do not repeat them):\n- " + "\n- ".join(r["have"]))
    harder = (" This page already has its first set of this trade's questions (listed above): write a second set that goes deeper, the "
              "questions of a second or final round with a senior person of this work, still with exact facts.") if r.get("more") else ""
    return "\n".join(parts) + f"\n\nWrite the {IQ_N} questions of this trade.{harder}"


def iq_check_user(r, qs):
    body = "\n\n".join(f"{i + 1}. Question: {q[0]}\n   What it checks: {q[1]}\n   A good answer shows: {q[2]}\n   Sample answer: {q[3]}" for i, q in enumerate(qs))
    return f"Kind of work: {r['name']} ({r['family']})\n{('What the person does: ' + r['what']) if r['what'] else ''}\n\nQuestions:\n\n{body}"


def batch_params(system, user, schema):
    return {"model": MODEL, "max_tokens": 16000, "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": schema}}, "messages": [{"role": "user", "content": user}]}


def run_batch(c, label, reqs, state, key):
    """Send reqs as one batch (or pick up the one in state[key]), wait for it; {custom_id: message or None}."""
    bid = state.get(key)
    if not bid:
        bid = c.messages.batches.create(requests=reqs).id
        state[key] = bid; IQ_STATE.write_text(json.dumps(state))
        print(f"{label}: отправлено {len(reqs)} запросов одним пакетом ({bid}). Обычно 10–60 минут.", flush=True)
    else:
        print(f"{label}: жду пакет, отправленный раньше: {bid}", flush=True)
    t0 = time.time()
    while True:
        b = c.messages.batches.retrieve(bid); k = b.request_counts
        if b.processing_status == "ended": break
        print(f"  {time.strftime('%H:%M')}: готово {k.succeeded + k.errored + k.canceled + k.expired} из {len(reqs) or '?'} ({(time.time() - t0) / 60:.0f} мин)", flush=True)
        time.sleep(60)
    out = {}
    for res in c.messages.batches.results(bid):
        out[res.custom_id] = res.result.message if res.result.type == "succeeded" else None
    print(f"{label}: готово, ответов {sum(1 for m in out.values() if m)}, без ответа {sum(1 for m in out.values() if not m)}", flush=True)
    return out


def interview(argv):
    global IQ_STATE
    IQ_STATE = ROOT / "data" / ("ai_fill_interview_more.json" if "--more" in argv else "ai_fill_interview.json")     # another job of the same run may have moved it
    more = "--more" in argv
    rows = [dict(r, more=True) for r in iq_rows(True)] if more else iq_rows()
    if "--limit" in argv: rows = rows[:int(argv[argv.index("--limit") + 1])]
    by = {r["slug"]: r for r in rows}
    system = iq_system()
    if "--dry-run" in argv:
        print(f"{len(rows)} interview pages without questions of their own; about ${len(rows) * 0.09:.0f} for drafting and checking at batch prices")
        print("\n--- system ---\n" + system + "\n\n--- first request ---\n" + iq_user(rows[0]))
        return 0
    c = client()
    state = json.loads(IQ_STATE.read_text()) if IQ_STATE.exists() else {}
    if state.get("slugs") != sorted(by): state = {"slugs": sorted(by)}
    spent = 0.0
    seen = {q[0] for _h, _w, qs in ib.SUBJECTS for q in qs} | {q[0] for _h, qs in ib.OWN.values() for q in qs}
    if IQ_GEN.exists() and state.get("drafted"):
        drafts = json.loads(IQ_GEN.read_text())
    else:
        got = run_batch(c, "Вопросы", [{"custom_id": s, "params": batch_params(system, iq_user(r), IQ_SCHEMA)} for s, r in by.items()], state, "gen")
        drafts = {}
        for s, m in got.items():
            if not m or m.stop_reason != "end_turn": continue
            spent += cost(m.usage, "batch")
            try: qs = json.loads(text_of(m))["questions"]
            except (ValueError, KeyError): continue
            keep_ = []
            for q in qs:
                t = (q["question"].strip(), q["checks"].strip(), q["good"].strip(), q["sample"].strip())
                if ib.problem(t) or t[0] in seen or t[0] in by[s]["have"]: continue
                seen.add(t[0]); keep_.append(t)
            if len(keep_) >= 5: drafts[s] = keep_
        IQ_GEN.write_text(json.dumps(drafts, ensure_ascii=False, indent=1))
        state["drafted"] = True; IQ_STATE.write_text(json.dumps(state))
        print(f"Черновики: {len(drafts)} профессий, {sum(map(len, drafts.values()))} вопросов прошли правила. Примерно ${spent:.2f}.", flush=True)
    got = run_batch(c, "Проверка фактов", [{"custom_id": s, "params": batch_params(CHECK_SYSTEM, iq_check_user(by[s], qs), CHECK_SCHEMA)} for s, qs in drafts.items()], state, "check")
    out = json.loads(ib.OWN_FILE.read_text()) if ib.OWN_FILE.exists() else {}
    dropped = {}
    for s, m in got.items():
        if not m or m.stop_reason != "end_turn": continue
        spent += cost(m.usage, "batch")
        try: verdicts = {v["n"]: v for v in json.loads(text_of(m))["verdicts"]}
        except (ValueError, KeyError): continue
        qs = drafts[s]
        ok = [q for i, q in enumerate(qs) if verdicts.get(i + 1, {}).get("keep") is True]
        dropped[s] = [(q[0], verdicts.get(i + 1, {}).get("reason", "no verdict")) for i, q in enumerate(qs) if q not in ok]
        if more and s in out: out[s]["qs"] = out[s]["qs"] + [list(q) for q in ok]
        elif len(ok) >= 4: out[s] = {"heading": f"{by[s]['name']} questions", "qs": ok}
    ib.OWN_FILE.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=1) + "\n")
    (ROOT / "data" / "ai_interview_dropped.json").write_text(json.dumps(dropped, ensure_ascii=False, indent=1))
    IQ_STATE.unlink(missing_ok=True)
    n_kept = sum(len(v["qs"]) for v in out.values())
    print(f"\nГотово. {len(out)} профессий получили свои вопросы, всего {n_kept}; проверка убрала {sum(map(len, dropped.values()))} (data/ai_interview_dropped.json).")
    print(f"Потрачено примерно ${spent:.2f}.")
    return 0


# ---- an expert read of the hand-written pages ------------------------------------------------------------------------------

AUDIT_SECTIONS = ["glossary", "guides", "resignation-letters", "vs", "tools", "perks", "insights", "salary", "relocate"]      # the pages with most facts first; resume-words and skills are mostly lists and counted figures
AUDIT_STATE = ROOT / "data" / "ai_fill_audit.json"
AUDIT_OUT = ROOT / "data" / "ai_audit.json"
AUDIT_CHARS = 14000
AUDIT_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["findings"],
                "properties": {"findings": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                                       "required": ["quote", "problem", "fix", "confidence"],
                                                                       "properties": {"quote": {"type": "string"}, "problem": {"type": "string"},
                                                                                      "fix": {"type": "string"}, "confidence": {"type": "string", "enum": ["high", "medium"]}}}}}}
AUDIT_SYSTEM = """You are the fact-checker of a US job board (jobseveryhour.com) before its pages are read by job seekers, Google and AI assistants. You get the text of one page. Find only statements that are wrong or would mislead a job seeker:
- a fact, definition, law, rule, regulation, tax or benefit rule, standard practice or how-something-works that is incorrect, outdated or stated too broadly for the US (or for the country the page is about);
- advice that would harm a job seeker if followed (legally risky, against common HR practice, likely to cost them an offer);
- a claim about another company or website that is clearly false;
- a sentence that contradicts another sentence on the same page;
- a broken sentence whose meaning is wrong or unclear (not mere style).

Do not report: figures the site counts from today's job postings (numbers of postings, shares, medians, "as of" dates), invented example people and companies, the site's own features and promises, style preferences, or anything you are not sure is wrong. Report nothing rather than something doubtful.

For each finding give: quote (the page's exact words, copied character for character, at most 200 characters, enough to find the place), problem (one or two sentences: what is wrong and what is true), fix (the corrected wording, ready to replace the quote), confidence ("high" only when you are certain; "medium" when very likely). An empty list is the usual answer for a good page. Answer with the JSON object only."""


def page_text(f):
    t = f.read_text(errors="replace")
    if 'http-equiv="refresh"' in t[:2000]: return ""
    m = re.search(r"<main[^>]*>(.*?)</main>", t, re.S)
    x = m.group(1) if m else t
    x = re.sub(r"<(script|style|nav|header|footer|svg)[^>]*>.*?</\1>", " ", x, flags=re.S)
    x = re.sub(r"</(p|li|h[1-6]|tr|div|dd|dt)>", "\n", x)
    x = re.sub(r"<[^>]+>", " ", x)
    x = html.unescape(x)
    x = "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in x.split("\n"))
    return re.sub(r"\n{2,}", "\n", x).strip()


def audit_rows():
    out = []
    for sec in AUDIT_SECTIONS:
        base = ROOT / "site" / sec
        if not base.exists(): continue
        for f in sorted(base.glob("*/index.html")) + [base / "index.html"]:
            if not f.exists(): continue
            x = page_text(f)
            if len(x) < 400: continue
            rel = str(f.parent.relative_to(ROOT / "site"))
            out.append({"id": re.sub(r"[^A-Za-z0-9_-]", "_", rel)[:64], "url": f"/{rel}/", "text": x[:AUDIT_CHARS]})
    seen, uniq = set(), []
    for r in out:
        if r["id"] in seen: continue
        seen.add(r["id"]); uniq.append(r)
    return uniq


def audit(argv):
    rows = audit_rows()
    if "--limit" in argv: rows = rows[:int(argv[argv.index("--limit") + 1])]
    by = {r["id"]: r for r in rows}
    chars = sum(len(r["text"]) for r in rows)
    if "--dry-run" in argv:
        print(f"{len(rows)} pages, {chars / 3.8 / 1e6:.1f}M tokens of page text; about ${chars / 3.8 / 1e6 * 2 + len(rows) * 4000 * 10 / 1e6:.0f} at batch prices")
        print("\n--- first request ---\n" + rows[0]["url"] + "\n" + rows[0]["text"][:1500])
        return 0
    c = client()
    state = json.loads(AUDIT_STATE.read_text()) if AUDIT_STATE.exists() else {}
    if state.get("ids") != sorted(by): state = {"ids": sorted(by)}
    global IQ_STATE
    IQ_STATE = AUDIT_STATE
    got = run_batch(c, "Проверка страниц", [{"custom_id": i, "params": batch_params(AUDIT_SYSTEM, f"Page: https://jobseveryhour.com{r['url']}\n\n{r['text']}", AUDIT_SCHEMA)}
                                           for i, r in by.items()], state, "audit")
    spent, found = 0.0, []
    for i, m in got.items():
        if not m or m.stop_reason != "end_turn": continue
        spent += cost(m.usage, "batch")
        try: fs = json.loads(text_of(m))["findings"]
        except (ValueError, KeyError): continue
        for f in fs:
            f["url"] = by[i]["url"]
            f["found_on_page"] = f["quote"].strip() in by[i]["text"]
            found.append(f)
    AUDIT_OUT.write_text(json.dumps(found, ensure_ascii=False, indent=1))
    AUDIT_STATE.unlink(missing_ok=True)
    hi = sum(1 for f in found if f["confidence"] == "high")
    print(f"\nГотово. Прочитано {len(got)} страниц; найдено {len(found)} мест ({hi} точно ошибки), список в {AUDIT_OUT.relative_to(ROOT)}.")
    print(f"Потрачено примерно ${spent:.2f}.")
    return 0


# ---- glossary: the long answer for each term --------------------------------------------------------------------------------

GL_STATE = ROOT / "data" / "ai_fill_glossary.json"
GL_DRAFTS = ROOT / "data" / "ai_glossary_drafts.json"
GL_OUT = ROOT / "glossary_more.json"
GL_FEW = ["Applicant tracking system (ATS)", "Notice period", "Vesting"]
GL_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["skip", "title", "sections", "qa", "aliases"],
             "properties": {"skip": {"type": "boolean"}, "title": {"type": "string"},
                            "sections": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["heading", "paragraphs"],
                                                                    "properties": {"heading": {"type": "string"}, "paragraphs": {"type": "array", "items": {"type": "string"}}}}},
                            "qa": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["q", "a"],
                                                              "properties": {"q": {"type": "string"}, "a": {"type": "string"}}}},
                            "aliases": {"type": "array", "items": {"type": "string"}}}}
GL_CHECK_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["keep", "problems"],
                   "properties": {"keep": {"type": "boolean"}, "problems": {"type": "array", "items": {"type": "string"}}}}
gslug = lambda t: re.sub(r"[^a-z0-9]+", "-", re.sub(r"\(.*?\)", "", t.lower())).strip("-")      # build.py's gslug


def gl_system():
    ex = []
    for t in GL_FEW:
        if t not in gt.MORE: continue
        m = gt.MORE[t]
        ex.append({"term": t, "skip": False, "title": m["title"], "sections": [{"heading": h, "paragraphs": xs} for h, xs in m["sections"]],
                   "qa": [{"q": q, "a": a} for q, a in m["qa"]], "aliases": m.get("aliases", [])})
    return f"""You write the long answer of one term in the job-search glossary of a US job board (jobseveryhour.com). The page already shows the term's two-line definition and a tip; your text goes below them, for people who search "what is <term>", "<term> meaning" or a question about it, and for AI assistants that quote clear answers.

Write:
- skip: true only when the term names a feature of this website rather than a word people meet in a job search (for example "Featured job", "Last checked", "Widget", "Open for", "Category"); then leave the other fields empty.
- title: the page title in the searcher's words, 30 to 70 characters, no site name, usually "What Is <Term>? <what the page answers>".
- sections: 2 to 4, each a heading (no full stop at the end) and 2 to 4 paragraphs. Cover what the term means in detail, how it works or why it matters, and what a job seeker (or, for hiring terms, an employer) should do. Each paragraph 1 to 3 plain sentences, 12 to 65 words, ending with a full stop.
- qa: 3 to 5 questions people really ask about the term (as in Google's "People also ask"), each ending with "?", each answer 15 to 75 words, complete on its own, ending with a full stop.
- aliases: 0 to 3 other lowercase-hyphen slugs people type for the term (an abbreviation, a plural, a common spelling), only when truly different from the term's own slug.

Facts matter most. Every rule, law, tax or benefit fact must be exactly right for the US today; where a term or rule differs by state or country, say so plainly instead of generalising (for example, a UK term: say it is used in the UK). Do not state current figures that change every year (contribution limits, wage rates, thresholds); say "a yearly limit set by the IRS" and the like. No invented statistics or percentages. No legal or tax advice for a specific case; say when to ask a lawyer, an accountant or the state labor department. Name no real company as good or bad.

Style: plain American English, short sentences, no jargon left unexplained, no marketing words. Never use the long dash (—). Use ’ for apostrophes.

Finished examples:
{json.dumps(ex, ensure_ascii=False, indent=1)}

Answer with the JSON object only."""


def gl_rows():
    return [{"term": t, "def": d, "tip": tip} for t, d, tip, _ in gt.TERMS if t not in gt.MORE]


def gl_problems(m, slugs, aliases_taken):
    bad = []
    t = m.get("title") or ""
    if not 20 <= len(t) <= 75 or "Jobs Every Hour" in t: bad.append("title: 30 to 70 characters, no site name")
    secs = m.get("sections") or []
    if not 2 <= len(secs) <= 4: bad.append("sections: 2 to 4")
    for sec in secs:
        if not sec["heading"] or sec["heading"].endswith(".") or not sec["paragraphs"]: bad.append(f"section “{sec['heading']}”: a heading without a full stop and paragraphs")
        for x in sec["paragraphs"]:
            if not 4 <= len(x.split()) <= 70 or x[-1] not in ".?”": bad.append(f"paragraph “{x[:60]}…”: 12 to 65 words ending with a full stop")
    qa = m.get("qa") or []
    if not 3 <= len(qa) <= 5 or len({p["q"] for p in qa}) != len(qa): bad.append("qa: 3 to 5 different questions")
    for p in qa:
        if not p["q"].endswith("?") or not 3 <= len(p["a"].split()) <= 80 or p["a"][-1] not in ".”": bad.append(f"qa “{p['q'][:60]}”: a question with ?, an answer of 15 to 75 words with a full stop")
    if "—" in json.dumps(m, ensure_ascii=False): bad.append("no long dashes (—)")
    for al in m.get("aliases") or []:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", al) or al in slugs or al in aliases_taken: bad.append(f"alias {al}: lowercase-hyphen, not used already")
    return bad


def gl_check_user(r, m):
    body = f"Title: {m['title']}\n\n" + "\n\n".join(f"## {sec['heading']}\n" + "\n".join(sec["paragraphs"]) for sec in m["sections"])
    body += "\n\n## Questions\n" + "\n".join(f"Q: {p['q']}\nA: {p['a']}" for p in m["qa"])
    return f"Glossary term: {r['term']}\nShort definition already on the page: {r['def']}\nTip already on the page: {r['tip']}\n\nThe long answer to check:\n\n{body}"


GL_CHECK_SYSTEM = """You check one glossary page of a US job board before it is published. Read it as an employment lawyer, an HR professional and a careful editor together, and look only for things that are wrong: a fact, rule, law, tax or benefit rule, or standard practice that is incorrect, outdated, stated too broadly (true only in some states or countries but written as general), or doubtful; advice that would harm a job seeker or an employer who follows it; a statement that contradicts the short definition or the tip; an invented statistic. Style is not your concern.

keep: true only when you would sign the whole page as correct. problems: each problem in one sentence, quoting the words; empty when keep is true. Be strict: a page left out costs little, a wrong answer misleads people. Answer with the JSON object only."""


def retry_notes(name):
    """{key: [problems]} from the last run's dropped file, for `--retry`: the drafts the check refused, written again with its reasons."""
    f = ROOT / "data" / f"ai_{name}_dropped.json"
    return json.loads(f.read_text()) if f.exists() else {}


def glossary(argv):
    rows = gl_rows()
    notes = retry_notes("glossary") if "--retry" in argv else {}
    if "--retry" in argv: rows = [dict(r, notes=notes[r["term"]]) for r in rows if r["term"] in notes]
    if "--limit" in argv: rows = rows[:int(argv[argv.index("--limit") + 1])]
    by = {gslug(r["term"]): r for r in rows}
    system = gl_system()
    if "--dry-run" in argv:
        print(f"{len(rows)} terms with only two lines; about ${len(rows) * 0.08:.0f} for drafting and checking at batch prices")
        print("\n--- system ---\n" + system[:3000] + "\n...\n\n--- first request ---\n" + gl_user(rows[0]))
        return 0
    c = client()
    global IQ_STATE
    IQ_STATE = GL_STATE
    state = json.loads(GL_STATE.read_text()) if GL_STATE.exists() else {}
    if state.get("ids") != sorted(by): state = {"ids": sorted(by)}
    spent = 0.0
    slugs = {gslug(t[0]) for t in gt.TERMS}
    taken = {al for m in gt.MORE.values() for al in m.get("aliases", [])}
    if GL_DRAFTS.exists() and state.get("drafted"):
        drafts = json.loads(GL_DRAFTS.read_text())
    else:
        got = run_batch(c, "Словарь", [{"custom_id": i, "params": batch_params(system, gl_user(r), GL_SCHEMA)} for i, r in by.items()], state, "gen")
        drafts, skipped, bad_n = {}, 0, 0
        for i, m in got.items():
            if not m or m.stop_reason != "end_turn": continue
            spent += cost(m.usage, "batch")
            try: d = json.loads(text_of(m))
            except ValueError: continue
            if d.get("skip"): skipped += 1; continue
            if gl_problems(d, slugs, taken): bad_n += 1; continue
            taken |= set(d.get("aliases") or []); drafts[i] = d
        GL_DRAFTS.write_text(json.dumps(drafts, ensure_ascii=False, indent=1))
        state["drafted"] = True; GL_STATE.write_text(json.dumps(state))
        print(f"Черновики: {len(drafts)} терминов; пропущено как функции сайта {skipped}, не прошли правила {bad_n}. Примерно ${spent:.2f}.", flush=True)
    got = run_batch(c, "Проверка фактов", [{"custom_id": i, "params": batch_params(GL_CHECK_SYSTEM, gl_check_user(by[i], d), GL_CHECK_SCHEMA)} for i, d in drafts.items()], state, "check")
    out = json.loads(GL_OUT.read_text()) if GL_OUT.exists() else {}
    dropped = {}
    for i, m in got.items():
        if not m or m.stop_reason != "end_turn": continue
        spent += cost(m.usage, "batch")
        try: v = json.loads(text_of(m))
        except ValueError: continue
        d = drafts[i]
        if v.get("keep") is True:
            out[by[i]["term"]] = {"title": d["title"], "sections": [[sec["heading"], sec["paragraphs"]] for sec in d["sections"]],
                                  "qa": [[p["q"], p["a"]] for p in d["qa"]], "aliases": d.get("aliases") or []}
        else:
            dropped[by[i]["term"]] = v.get("problems") or []
    GL_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    (ROOT / "data" / "ai_glossary_dropped.json").write_text(json.dumps(dropped, ensure_ascii=False, indent=1))
    GL_DRAFTS.unlink(missing_ok=True)
    GL_STATE.unlink(missing_ok=True)
    print(f"\nГотово. {len(out)} терминов получили полную страницу; проверка отклонила {len(dropped)} (data/ai_glossary_dropped.json).")
    print(f"Потрачено примерно ${spent:.2f}.")
    return 0


def gl_user(r):
    fix = ("\n\nA first version was refused by the fact check for these reasons; avoid every one of them (narrow the claim, name the state or "
           "country, or leave the point out):\n- " + "\n- ".join(r["notes"])) if r.get("notes") else ""
    return f"Term: {r['term']}\nIts short definition on the page: {r['def']}\nIts tip on the page: {r['tip']}\n\nWrite the long answer for this term.{fix}"


# ---- how to become: training, licences and exams ---------------------------------------------------------------------------

BM_STATE = ROOT / "data" / "ai_fill_become.json"
BM_DRAFTS = ROOT / "data" / "ai_become_drafts.json"
BM_OUT = ROOT / "become_more.json"
BM_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["steps", "qa"],
             "properties": {"steps": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["label", "text"],
                                                                 "properties": {"label": {"type": "string"}, "text": {"type": "string"}}}},
                            "qa": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["q", "a"],
                                                              "properties": {"q": {"type": "string"}, "a": {"type": "string"}}}}}}
BM_SYSTEM = """You write one section of the page "How to become a <person>" on a US job board (jobseveryhour.com): what it really takes to enter this exact kind of work in the US. The page already shows figures counted from today's job postings (skills named, years asked, pay) and five general steps; your section adds what those cannot: the education or training people take, any license, registration or exam the work requires or that employers expect, typical supervised hours or apprenticeship, how long it usually takes, and the usual first job on the way in.

Write:
- steps: 4 to 6 items in the order a person goes through them. Each has a label (2 to 6 words, no full stop, for example "Education", "Apprenticeship", "State license", "Exams", "Time it takes", "First job") and a text of 15 to 60 words, ending with a full stop, specific to this work.
- qa: 2 questions people search about entering this work (for example "Do you need a license to be an electrician?", "How long does it take to become an actuary?"), each ending with "?", each answer 20 to 70 words, complete on its own, ending with a full stop.

Facts matter most. Name real licenses, exams, certifications and bodies only when you are certain they exist and apply in the US, spelled exactly (for example "NCLEX-RN", "SOA", "NABCEP", "EPA Section 608", "state contractor's license", "CPA exam"). Where rules differ by state, say so ("most states require ...", "requirements vary by state"). If the work has no license and no standard path, say that plainly and describe how people actually get in (a degree in a related field, a portfolio, a first job in a related role). Do not state fees, pay, exam pass rates or other figures that change; time ranges ("usually two to four years") are fine when they are well established. Name no school, bootcamp or company. Plain American English, short sentences. Never use the long dash (—); use ’ for apostrophes. Answer with the JSON object only."""
BM_CHECK_SYSTEM = """You check one section of a US job board page "How to become a <person>" before it is published. Read it as an expert in that work and in US licensing, and look only for things that are wrong: a license, exam, certification or body that does not exist, is misnamed or does not apply; a requirement stated as universal that varies by state; a wrong time span or order of steps; outdated rules; anything that would send a career changer down a wrong path. Style is not your concern.

keep: true only when you would sign the whole section as correct. problems: each problem in one sentence, quoting the words; empty when keep is true. Be strict: a section left out costs little, a wrong one misleads people. Answer with the JSON object only."""


def bm_rows():
    out = []
    for d in sorted((ROOT / "site" / "how-to-become").iterdir()):
        if not d.is_dir(): continue
        t = (d / "index.html").read_text()
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        who = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).split(":")[0].replace("How to become ", "").strip() if h1 else d.name
        out.append({"slug": d.name, "who": who, "what": roles_info.what(d.name, who)})
    return out


def bm_user(r):
    fix = ("\n\nA first version was refused by the fact check for these reasons; avoid every one of them (narrow the claim, say it varies by "
           "state, or leave the point out):\n- " + "\n- ".join(r["notes"])) if r.get("notes") else ""
    return f"Kind of work: {r['slug']}\nThe page is: How to become {r['who']}\n" + (f"What the person does: {r['what']}\n" if r["what"] else "") + "\nWrite the section." + fix


def bm_problems(d):
    bad = []
    st = d.get("steps") or []
    if not 4 <= len(st) <= 6: bad.append("steps: 4 to 6")
    for x in st:
        if not x["label"] or len(x["label"].split()) > 7 or x["label"].endswith("."): bad.append(f"label {x['label']}: 2 to 6 words, no full stop")
        if not 10 <= len(x["text"].split()) <= 70 or x["text"][-1] not in ".”": bad.append(f"text “{x['text'][:50]}”: 15 to 60 words ending with a full stop")
    qa = d.get("qa") or []
    if not 1 <= len(qa) <= 3: bad.append("qa: 2 questions")
    for x in qa:
        if not x["q"].endswith("?") or not 10 <= len(x["a"].split()) <= 80 or x["a"][-1] not in ".”": bad.append(f"qa “{x['q'][:50]}”: question with ?, answer 20 to 70 words")
    if "—" in json.dumps(d, ensure_ascii=False): bad.append("no long dashes")
    return bad


def become(argv):
    rows = bm_rows()
    done = json.loads(BM_OUT.read_text()) if BM_OUT.exists() else {}
    notes = retry_notes("become") if "--retry" in argv else {}
    if "--retry" in argv: rows = [dict(r, notes=notes[r["slug"]]) for r in rows if r["slug"] in notes and r["slug"] not in done]
    if "--limit" in argv: rows = rows[:int(argv[argv.index("--limit") + 1])]
    by = {r["slug"]: r for r in rows}
    if "--dry-run" in argv:
        print(f"{len(rows)} how-to-become pages; about ${len(rows) * 0.05:.0f} for drafting and checking at batch prices\n\n--- first request ---\n" + bm_user(rows[0]))
        return 0
    c = client()
    global IQ_STATE
    IQ_STATE = BM_STATE
    state = json.loads(BM_STATE.read_text()) if BM_STATE.exists() else {}
    if state.get("ids") != sorted(by): state = {"ids": sorted(by)}
    spent = 0.0
    if BM_DRAFTS.exists() and state.get("drafted"):
        drafts = json.loads(BM_DRAFTS.read_text())
    else:
        got = run_batch(c, "Как стать", [{"custom_id": s, "params": batch_params(BM_SYSTEM, bm_user(r), BM_SCHEMA)} for s, r in by.items()], state, "gen")
        drafts = {}
        for s, m in got.items():
            if not m or m.stop_reason != "end_turn": continue
            spent += cost(m.usage, "batch")
            try: d = json.loads(text_of(m))
            except ValueError: continue
            if not bm_problems(d): drafts[s] = d
        BM_DRAFTS.write_text(json.dumps(drafts, ensure_ascii=False, indent=1))
        state["drafted"] = True; BM_STATE.write_text(json.dumps(state))
        print(f"Черновики: {len(drafts)} из {len(by)} прошли правила. Примерно ${spent:.2f}.", flush=True)
    check = lambda s, d: (f"The page: How to become {by[s]['who']}\n\n" + "\n".join(f"- {x['label']}: {x['text']}" for x in d["steps"])
                          + "\n\nQuestions:\n" + "\n".join(f"Q: {x['q']}\nA: {x['a']}" for x in d["qa"]))
    got = run_batch(c, "Проверка фактов", [{"custom_id": s, "params": batch_params(BM_CHECK_SYSTEM, check(s, d), GL_CHECK_SCHEMA)} for s, d in drafts.items()], state, "check")
    out = json.loads(BM_OUT.read_text()) if BM_OUT.exists() else {}
    dropped = {}
    for s, m in got.items():
        if not m or m.stop_reason != "end_turn": continue
        spent += cost(m.usage, "batch")
        try: v = json.loads(text_of(m))
        except ValueError: continue
        if v.get("keep") is True:
            d = drafts[s]
            out[s] = {"steps": [[x["label"], x["text"]] for x in d["steps"]], "qa": [[x["q"], x["a"]] for x in d["qa"]]}
        else: dropped[s] = v.get("problems") or []
    BM_OUT.write_text(json.dumps(dict(sorted(out.items())), ensure_ascii=False, indent=1) + "\n")
    (ROOT / "data" / "ai_become_dropped.json").write_text(json.dumps(dropped, ensure_ascii=False, indent=1))
    BM_DRAFTS.unlink(missing_ok=True)
    BM_STATE.unlink(missing_ok=True)
    print(f"\nГотово. {len(out)} страниц «как стать» получили раздел про обучение и лицензии; проверка отклонила {len(dropped)}.")
    print(f"Потрачено примерно ${spent:.2f}.")
    return 0


# ---- page sections drafted and fact-checked the same way: role pages, salary pages, job description templates ---------------------

ITEMS = lambda n_lo, n_hi: {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["label", "text"],
                                                        "properties": {"label": {"type": "string"}, "text": {"type": "string"}}}}
QA_ITEMS = {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["q", "a"], "properties": {"q": {"type": "string"}, "a": {"type": "string"}}}}
STYLE = ("Facts matter most: every rule, license, law or practice you state must be right for the US today; where it varies by state, say so; "
         "no figures that change (pay, fees, rates), no invented statistics, no real company or school names. Plain American English, short "
         "sentences. Never use the long dash (—); use ’ for apostrophes. Answer with the JSON object only.")
SECTIONS = {
    "role": dict(
        pages="roles", out="role_more.json", key="day",
        schema={"type": "object", "additionalProperties": False, "required": ["day", "qa"], "properties": {"day": ITEMS(4, 5), "qa": QA_ITEMS}},
        system="You write one section of the page \"<work> jobs\" on a US job board (jobseveryhour.com): what people in this exact work do. "
               "The page already lists today's open jobs, pay and skills counted from the postings; your section adds the work itself, for job seekers "
               "and for AI assistants that quote clear answers.\n\nWrite:\n- day: 4 or 5 items, each a label (2 to 5 words, no full stop, such as "
               "\"Main duties\", \"A typical day\", \"Who they work with\", \"Tools of the trade\", \"Where they work\", \"How the work is judged\") and a text of "
               "15 to 55 words, ending with a full stop, specific to this work.\n- qa: 2 questions people search about this work (\"What does a <person> do "
               "day to day?\", \"Is <work> a stressful job?\", \"What is the difference between X and Y?\"), each ending with ?, each answer 20 to 70 words, "
               "ending with a full stop.\n\n" + STYLE),
    "salary": dict(
        pages="salaries", out="salary_more.json", key="factors",
        schema={"type": "object", "additionalProperties": False, "required": ["factors", "qa"], "properties": {"factors": ITEMS(4, 5), "qa": QA_ITEMS}},
        system="You write one section of the page \"<work> salary\" on a US job board (jobseveryhour.com). The page already shows the pay advertised "
               "in today's postings (median, ranges, by level, by company); your section explains what moves pay up or down in this exact work, without "
               "any figure.\n\nWrite:\n- factors: 4 or 5 items, each a label (2 to 5 words, no full stop, such as \"Experience\", \"Licenses and "
               "certifications\", \"Location\", \"Industry\", \"Shift and overtime\", \"Specialty\", \"Commission\") and a text of 15 to 55 words, ending with "
               "a full stop, saying how it changes pay in this work and what a person can do about it.\n- qa: 2 questions people search about pay in this "
               "work (\"How can a <person> earn more?\", \"Do <persons> get paid overtime?\", \"Is <work> paid hourly or salary?\"), each ending with ?, "
               "each answer 20 to 70 words, ending with a full stop, with no figures.\n\n" + STYLE),
    "jd": dict(
        pages="job-descriptions", out="jd_more.json", key="duties",
        schema={"type": "object", "additionalProperties": False, "required": ["duties", "must", "nice"],
                "properties": {"duties": {"type": "array", "items": {"type": "string"}}, "must": {"type": "array", "items": {"type": "string"}},
                               "nice": {"type": "array", "items": {"type": "string"}}}},
        system="You write the duties and requirements of a job description template for one kind of work, for employers on a US job board "
               "(jobseveryhour.com). The template already has brackets for the company, the pay, the years of experience and the skills counted from "
               "today's postings; yours are the lines every posting for this work needs.\n\nWrite:\n- duties: 6 lines, each starting with a verb in the "
               "present tense (\"Price new products...\", \"Inspect welds...\"), 6 to 22 words, no full stop, specific to this work.\n- must: 3 or 4 "
               "requirements (education, license or certification where the work needs one, core abilities), 4 to 18 words each, no full stop; say "
               "\"or equivalent experience\" where employers usually accept it; name a license only when the work requires it, noting state rules.\n- "
               "nice: 2 nice-to-have lines, 4 to 18 words each, no full stop.\nNo years of experience and no software names (the template adds those).\n\n" + STYLE),
}
SECTION_CHECK = ("You check one section written for a US job board page before it is published. Read it as an expert in that work and in US "
                 "employment rules, and look only for things that are wrong: a fact, license, law, rule or practice that is incorrect, outdated or "
                 "stated as universal when it varies by state; a duty or requirement that does not belong to this work; advice that would mislead a "
                 "job seeker or an employer. Style is not your concern.\n\nkeep: true only when you would sign the whole section as correct. problems: "
                 "each problem in one sentence, quoting the words; empty when keep is true. Be strict. Answer with the JSON object only.")


def sec_rows(kind):
    base = ROOT / "site" / SECTIONS[kind]["pages"]
    out = []
    for d in sorted(base.iterdir()):
        f = d / "index.html"
        if not d.is_dir() or not f.exists(): continue
        t = f.read_text()
        if 'http-equiv="refresh"' in t[:2000]: continue
        h1 = re.search(r"<h1>(.*?)</h1>", t, re.S)
        name = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).split(":")[0].strip() if h1 else d.name
        for tail in (" job description", " salary", " jobs"):
            if name.lower().endswith(tail): name = name[: -len(tail)].strip()
        out.append({"slug": d.name, "name": name, "what": roles_info.what(d.name, name)})
    return out


def sec_problems(kind, d):
    bad = []
    words = lambda x: len(x.split())
    if kind in ("role", "salary"):
        items = d.get(SECTIONS[kind]["key"]) or []
        if not 4 <= len(items) <= 5: bad.append("4 or 5 items")
        for x in items:
            if not x["label"] or words(x["label"]) > 6 or x["label"].endswith("."): bad.append(f"label {x['label']!r}")
            if not 10 <= words(x["text"]) <= 65 or x["text"][-1] not in ".”": bad.append(f"text {x['text'][:40]!r}")
        if not 1 <= len(d.get("qa") or []) <= 3: bad.append("2 questions")
        for x in d.get("qa") or []:
            if not x["q"].endswith("?") or not 10 <= words(x["a"]) <= 80 or x["a"][-1] not in ".”": bad.append(f"qa {x['q'][:40]!r}")
        if kind == "salary" and re.search(r"\$\s?\d|\d+%|\d{2,},\d{3}", json.dumps(d)): bad.append("no figures")
    else:
        if len(d.get("duties") or []) != 6: bad.append("6 duties")
        if not 3 <= len(d.get("must") or []) <= 4: bad.append("3 or 4 requirements")
        if len(d.get("nice") or []) != 2: bad.append("2 nice-to-haves")
        tools = {t.lower() for ts in rx.KIND.values() for t in ts} | {t.lower() for t in rx.OFFICE}
        for x in (d.get("duties") or []) + (d.get("must") or []) + (d.get("nice") or []):
            if not 3 <= words(x) <= 24 or x.endswith(".") or not x[0].isupper(): bad.append(f"line {x[:40]!r}")
            if any(re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", x.lower()) for t in tools): bad.append(f"a tool named in {x[:40]!r}")
            if re.search(r"\d+\+? years", x): bad.append("no years")
    if "—" in json.dumps(d, ensure_ascii=False): bad.append("no long dashes")
    return bad


def sec_text(kind, d):
    if kind in ("role", "salary"):
        return "\n".join(f"- {x['label']}: {x['text']}" for x in d[SECTIONS[kind]["key"]]) + "\n\nQuestions:\n" + "\n".join(f"Q: {x['q']}\nA: {x['a']}" for x in d["qa"])
    return "Duties:\n" + "\n".join("- " + x for x in d["duties"]) + "\nRequirements:\n" + "\n".join("- " + x for x in d["must"]) + "\nNice to have:\n" + "\n".join("- " + x for x in d["nice"])


def section_job(kind, argv):
    cfg = SECTIONS[kind]
    out_f = ROOT / cfg["out"]
    done = json.loads(out_f.read_text()) if out_f.exists() else {}
    rows = [r for r in sec_rows(kind) if r["slug"] not in done]
    notes = retry_notes(kind) if "--retry" in argv else {}
    if "--retry" in argv: rows = [dict(r, notes=notes[r["slug"]]) for r in rows if r["slug"] in notes]
    if "--limit" in argv: rows = rows[:int(argv[argv.index("--limit") + 1])]
    by = {r["slug"]: r for r in rows}
    user = lambda r: (f"Kind of work: {r['slug']}\nName on the site: {r['name']}\n" + (f"What the person does: {r['what']}\n" if r["what"] else "") + "\nWrite the section."
                      + (("\n\nA first version was refused by the fact check for these reasons; avoid every one of them:\n- " + "\n- ".join(r["notes"])) if r.get("notes") else ""))
    if "--dry-run" in argv:
        print(f"{kind}: {len(rows)} pages; about ${len(rows) * 0.035:.0f} for drafting and checking\n\n--- first request ---\n" + (user(rows[0]) if rows else "")); return 0
    if not rows: print(f"{kind}: nothing to do"); return 0
    c = client()
    global IQ_STATE
    IQ_STATE = ROOT / "data" / f"ai_fill_{kind}.json"
    drafts_f = ROOT / "data" / f"ai_{kind}_drafts.json"
    state = json.loads(IQ_STATE.read_text()) if IQ_STATE.exists() else {}
    if state.get("ids") != sorted(by): state = {"ids": sorted(by)}
    spent = 0.0
    if drafts_f.exists() and state.get("drafted"):
        drafts = json.loads(drafts_f.read_text())
    else:
        got = run_batch(c, f"{kind}: черновики", [{"custom_id": s, "params": batch_params(cfg["system"], user(r), cfg["schema"])} for s, r in by.items()], state, "gen")
        drafts = {}
        for s, m in got.items():
            if not m or m.stop_reason != "end_turn": continue
            spent += cost(m.usage, "batch")
            try: d = json.loads(text_of(m))
            except ValueError: continue
            if not sec_problems(kind, d): drafts[s] = d
        drafts_f.write_text(json.dumps(drafts, ensure_ascii=False, indent=1))
        state["drafted"] = True; IQ_STATE.write_text(json.dumps(state))
        print(f"{kind}: {len(drafts)} из {len(by)} прошли правила. Примерно ${spent:.2f}.", flush=True)
    got = run_batch(c, f"{kind}: проверка фактов", [{"custom_id": s, "params": batch_params(SECTION_CHECK, f"The page: {by[s]['name']} ({cfg['pages']})\n\n" + sec_text(kind, d), GL_CHECK_SCHEMA)}
                                                    for s, d in drafts.items()], state, "check")
    dropped = {}
    for s, m in got.items():
        if not m or m.stop_reason != "end_turn": continue
        spent += cost(m.usage, "batch")
        try: v = json.loads(text_of(m))
        except ValueError: continue
        if v.get("keep") is True: done[s] = drafts[s]
        else: dropped[s] = v.get("problems") or []
    out_f.write_text(json.dumps(dict(sorted(done.items())), ensure_ascii=False, indent=1) + "\n")
    (ROOT / "data" / f"ai_{kind}_dropped.json").write_text(json.dumps(dropped, ensure_ascii=False, indent=1))
    IQ_STATE.unlink(missing_ok=True); drafts_f.unlink(missing_ok=True)
    print(f"\n{kind}: готово, всего {len(done)} страниц с разделом; проверка отклонила {len(dropped)}. Потрачено примерно ${spent:.2f}.", flush=True)
    return 0


JOBS = {"resume": resume, "interview": interview, "glossary": glossary, "become": become, "audit": audit,
        "glossary-retry": lambda a: glossary(a + ["--retry"]), "become-retry": lambda a: become(a + ["--retry"]),
        "role": lambda a: section_job("role", a), "salary": lambda a: section_job("salary", a), "jd": lambda a: section_job("jd", a),
        "role-retry": lambda a: section_job("role", a + ["--retry"]), "salary-retry": lambda a: section_job("salary", a + ["--retry"]),
        "jd-retry": lambda a: section_job("jd", a + ["--retry"]), "interview-more": lambda a: interview(a + ["--more"])}

if __name__ == "__main__":
    names = [a for a in sys.argv[1:] if a in JOBS]
    rest = [a for a in sys.argv[1:] if a not in JOBS]
    if not names: print(__doc__); sys.exit(1)
    for n in names:
        print(f"\n===== {n} =====", flush=True)
        JOBS[n](rest)
    sys.exit(0)
