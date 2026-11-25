"""Other products beside two of this site's tools: AI interview practice tools (/interview-practice/) and cover letter generators
(/tools/cover-letter/).

Why (26 Nov 2026): ChatGPT, asked in a temporary chat "free AI interview practice tool to practice job interview questions out loud" and
"best free AI cover letter generator", answers with a table of tools (free limit, voice, AI feedback, sign-up, PDF or Word). Our pages
had no such table, so an answer had nothing of ours to quote beside them. The products are the ones those answers named.

Rules the data follows:
- Every fact about another product was read on that product's own pages (pricing page, feature page, its own questions), on READ, in a
  real browser. Reviews, "best of" lists and AI answers only found the products; they are never the source.
- A cell a product's pages did not state is "" and the page shows "Not stated". A product with fewer than MIN_FACTS stated cells gets
  no row (test() checks it).
- Where two of a product's own pages disagree, the cell says so and names both, rather than picking one.
- Prices are the ones the pages showed on READ; some sites change them by country or run a sale.
- Facts about our own tools come from the code (assets/site.js, tools_pages.py) and are written in build.py, not here.

Run `python3 compare_tools.py` to check the data.
"""

READ = "2026-11-26"
MIN_FACTS = 4

# AI interview practice. Columns: free use, paid plans, who asks the questions, how you answer, the feedback, follow-up questions,
# and anything else a reader would weigh.
INTERVIEW_COLS = [("free", "Free use"), ("paid", "Paid plans"), ("asks", "Asks the questions"), ("answer", "Your answer"),
                  ("feedback", "Feedback"), ("follow", "Follow-up questions"), ("more", "Also")]
INTERVIEW = [
    {"name": "Huru", "url": "https://huru.ai/",
     "free": "Free for job seekers: every feature, unlimited mock interviews",
     "paid": "None for job seekers; Enterprise for organizations, priced for each one",
     "asks": "A live AI interviewer speaks, or one question at a time; from a role, a pasted job description or your own questions",
     "answer": "Out loud, on video or audio only; the recording is kept for you to watch back",
     "feedback": "An AI score out of 100 (relevance, structure, specificity, impact, articulation), pace, filler words, “I” or “we”",
     "follow": "Yes: the live interviewer follows up on what you said",
     "more": "50,000+ questions, 242+ career roles, 5 languages; iOS app and Chrome extension",
     "sources": [("https://huru.ai/", "home page: what it does, the pricing section and its questions")]},
    {"name": "Yoodli", "url": "https://yoodli.ai/",
     "free": "Starter, $0: 5 roleplays in all (any session over 30 seconds counts); no credit card",
     "paid": "Pro $8 a month (10 roleplays a week), Advanced $20 a month (unlimited), both billed yearly; no refunds on cancellation",
     "asks": "Live AI roleplays, interview practice among them",
     "answer": "Out loud; it also gives feedback on recordings you upload",
     "feedback": "",
     "follow": "",
     "more": "On Starter and Pro, session data may be used to improve the platform; Advanced keeps it out of AI training",
     "sources": [("https://yoodli.ai/pricing", "plans for individuals and the pricing questions")]},
    {"name": "MockIF", "url": "https://mockif.com/",
     "free": "£0, no card: 5 credits, that is 2 skill interviews or 5 quick practices, with a basic report",
     "paid": "£39, £59 or £79 a month (25 to 60 credits, with automatic job applications); credit packs from £25",
     "asks": "An AI interviewer; questions from your CV and the job description, 50+ interview categories",
     "answer": "By voice",
     "feedback": "Scores for clarity, confidence and relevance; STAR structure; pacing, filler words and response time",
     "follow": "Yes",
     "more": "Prices in pounds; “Start free” opens a sign-up form",
     "sources": [("https://mockif.com/", "what it does"), ("https://mockif.com/pricing", "plans, credits and the free plan")]},
    {"name": "GoRehearse", "url": "https://gorehearse.com/",
     "free": "One 5-minute spoken interview with an early-read report; no card",
     "paid": "3 interviews for $7.99 with no subscription; Starter $19 a month (10 interviews), Pro $39 a month (25)",
     "asks": "A live AI voice interviewer for the role you pick",
     "answer": "Out loud, with a live transcript you keep",
     "feedback": "A scored report: competency scores and question-by-question feedback that quotes your words",
     "follow": "Yes: it follows up on what you said",
     "more": "Refund within 7 days of the first charge if no plan interview was used",
     "sources": [("https://gorehearse.com/", "how it works"), ("https://gorehearse.com/pricing", "prices and its questions")]},
    {"name": "Big Interview", "url": "https://www.biginterview.com/",
     "free": "",
     "paid": "$39 for a 30-day subscription, $99 for 3 months, or $299 once for lifetime access; full refund within 30 days",
     "asks": "Questions from your resume or a job description (PracticeAI); 1,000+ questions",
     "answer": "Voice only, like a phone screen",
     "feedback": "AI feedback on delivery and answer quality, with a report",
     "follow": "",
     "more": "Renewal is cancelled from the account page",
     "sources": [("https://www.biginterview.com/pricing/personal", "plans and pricing questions"),
                 ("https://www.biginterview.com/platform/practice-with-interview-simulator", "the interview simulator")]},
    {"name": "Final Round AI", "url": "https://www.finalroundai.com/",
     "free": "$0: set up goals, add your resume and parse a job description; practice interviews are listed under Pro",
     "paid": "Pro from $25 a month; no free trial",
     "asks": "An AI interviewer that knows your role and resume; eight scenarios such as coding, system design, behavioral and salary negotiation",
     "answer": "Out loud",
     "feedback": "An automatic debrief: what worked and what to fix",
     "follow": "",
     "more": "A desktop app for macOS and Windows; its main product suggests answers privately during a real interview, hidden from screen sharing",
     "sources": [("https://www.finalroundai.com/", "the product and the plans (the pricing address opens the home page)")]},
]

# Free cover letter generators. Columns: how the letter is written, what it needs from you, an account, free use, downloads on the
# free plan, paid plans.
COVER_COLS = [("how", "How it writes"), ("needs", "What it needs"), ("account", "Account"), ("free", "Free use"),
              ("download", "Download, free plan"), ("paid", "Paid plans")]
COVER = [
    {"name": "Enhancv", "url": "https://enhancv.com/",
     "how": "AI (OpenAI’s GPT models), three paragraphs on one page",
     "needs": "Your resume as a PDF or DOCX file (2 MB at most) and the job ad",
     "account": "No: no login",
     "free": "Free; “generate as many cover letters as you need”",
     "download": "Text to paste into your editor; a PDF through its cover letter builder",
     "paid": "",
     "sources": [("https://enhancv.com/cover-letter-generator/", "the generator and its questions")]},
    {"name": "Teal", "url": "https://www.tealhq.com/",
     "how": "AI; you pick the length (100 to 400 words), the tone and the AI model",
     "needs": "Your resume and the job post",
     "account": "Yes: a free Teal account",
     "free": "2 AI cover letters on the free plan",
     "download": "Copy the text, or download a PDF",
     "paid": "Teal+ $13 a week (also billed monthly or quarterly): unlimited AI letters",
     "sources": [("https://www.tealhq.com/tool/cover-letter-generator", "the generator and its questions"), ("https://www.tealhq.com/pricing", "Teal+ and the AI credits")]},
    {"name": "Rezi", "url": "https://www.rezi.ai/",
     "how": "AI cover letter writer",
     "needs": "",
     "account": "",
     "free": "Its generator page says “free”, but its pricing table lists the cover letter builder and the AI cover letter writer as not included in the free plan",
     "download": "Free plan: 3 PDF downloads; Word only on paid plans",
     "paid": "$29 a month, $57 every 3 months, or $149 once; a 30-day money-back guarantee",
     "sources": [("https://www.rezi.ai/pricing", "plans and the feature table"), ("https://www.rezi.ai/tools/cover-letter-generator", "the generator page")]},
    {"name": "Kickresume", "url": "https://www.kickresume.com/",
     "how": "AI, from the company name and the job title",
     "needs": "A company name and a job title",
     "account": "",
     "free": "Its AI cover letter page says the letter is “completely free”; its pricing page lists the AI Writer under Premium",
     "download": "",
     "paid": "Premium $19 a month, or $9 a month for 3 months and $4.50 a month for a year (on sale at 57% off that day); 14-day money back",
     "sources": [("https://www.kickresume.com/en/ai-cover-letter-writer/", "the AI cover letter page"), ("https://www.kickresume.com/en/pricing/", "Premium plans")]},
    {"name": "FlowCV", "url": "https://flowcv.com/",
     "how": "Cover letter maker; AI writing tools only in Pro",
     "needs": "",
     "account": "Yes: the free letter is saved in your account",
     "free": "1 cover letter (and 1 resume), free forever",
     "download": "Unlimited PDF downloads, no watermark",
     "paid": "Pro $60 a year ($5 a month), also monthly or quarterly; renews until cancelled; 14-day refund",
     "sources": [("https://flowcv.com/pricing", "free and Pro plans and the pricing questions")]},
    {"name": "Resume.io", "url": "https://resume.io/",
     "how": "AI drafts each section from your details and the job",
     "needs": "Your contact details and the job you want",
     "account": "",
     "free": "1 cover letter (and 1 resume)",
     "download": "Its generator page: a PDF with a free template, Word on a paid plan; its pricing page: the free plan downloads TXT only",
     "paid": "$2.95 for a 7-day trial, then $29.95 every 4 weeks; or $49.95 every 3 months; 7-day money back",
     "sources": [("https://resume.io/cover-letter-generator", "the generator"), ("https://resume.io/pricing", "plans and pricing questions")]},
]

# Pages read on READ that gave no row, and why: shown under the table so a reader who looks for them knows.
NO_ROW = {
    "interview": [("Google Interview Warmup", "https://grow.google/certificates/interview-warmup/", "its address now opens a Google article on interview tips, with no practice tool on it")],
    "cover": [],
}

# What the others do better, and what this site's tool does that they do not, in plain sentences built only on the cells above.
# {n_work} and {n_q} are filled in by build.py from the questions it builds.
THEY_BETTER = {
    "interview": [
        "A live AI interviewer that talks back and asks follow-up questions on what you said: Huru, GoRehearse and MockIF. This page reads fixed questions and does not follow up.",
        "An AI judgement of what your answer says: Huru scores it out of 100, GoRehearse by competency, MockIF for clarity, confidence and relevance. This page checks the length, a number, “I” or “we”, the pace and filler words by fixed rules; it cannot tell a strong story from a weak one.",
        "Questions written from your resume or a job description: Huru, MockIF, Big Interview and Final Round AI. Here the questions are the ones for the kind of work you pick.",
        "Video you can watch back, five languages and an iPhone app: Huru. This page practises in US English, in the browser.",
    ],
    "cover": [
        "A whole letter drafted by AI from your resume and the job ad: Enhancv (with no account), Teal and Resume.io. This builder writes no sentence you did not give it the facts for, so the result and the reason are yours to write.",
        "Designed letters that match a resume template: Kickresume, Resume.io and Enhancv. Teal also lets you set the length and pick the AI model. Here the letter is plain text in three tones.",
    ],
}
WE_DIFFER = {
    "interview": [
        "Free with no limit and no account. Yoodli’s free plan has 5 roleplays in all, MockIF’s 5 credits, GoRehearse’s one 5-minute interview; Big Interview and Final Round AI charge for practice.",
        "This site keeps nothing you say. In Chrome and Edge the browser’s own speech service turns your words into text; there is nothing to install.",
        "{n_q} questions for {n_work} kinds of work, each list next to the answers and the guide for that work.",
    ],
    "cover": [
        "No account and no upload: Teal needs an account, FlowCV keeps the letter in one, and Enhancv reads your resume file.",
        "Word and PDF on the free version. Rezi’s free plan has no Word download, and Resume.io’s pricing page says its free plan downloads TXT only.",
        "Nothing is invented: every sentence comes from what you type, so nothing needs checking for made-up claims.",
    ],
}

# Questions with answers built on the table, shown in the page's questions (with FAQPage markup where the page has it). {date} is READ.
FAQ = {
    "interview": [
        ("What is the best free AI interview practice tool?",
         "It depends on what you want to practise. By their own pages on {date}: Huru is free for job seekers, with a live AI interviewer and a score for every answer; "
         "Yoodli’s free plan gives 5 roleplays in all; MockIF gives 5 free credits; GoRehearse one free 5-minute spoken interview. This page is free with no limit and no account, "
         "but it checks answers by fixed rules, not AI. The table on this page sets {n_tools} of these tools beside it."),
        ("Is there a free interview practice tool that talks back?",
         "Yes. By their own pages on {date}, Huru’s live AI interviewer is free for job seekers and asks follow-up questions on what you said, and GoRehearse gives one free "
         "5-minute spoken interview with follow-ups. This page reads each question aloud and listens, but it does not reply or follow up."),
    ],
    "cover": [
        ("Which cover letter generators are free?",
         "By their own pages on {date}: Enhancv’s AI generator needs no account but reads your resume file; Teal gives 2 free AI letters with a free account; FlowCV keeps 1 free letter "
         "with unlimited PDF downloads; Resume.io’s free plan has 1 letter, and its pricing page says downloads are TXT only. Rezi’s pricing table puts its cover letter tools on paid plans. "
         "This builder is free with no account and saves Word and PDF, but it is a template, not AI."),
    ],
}


def facts(p, cols):
    """The stated cells of a product: a cell is a fact when its text is not empty."""
    return sum(1 for k, _ in cols if p.get(k))


def rows(kind):
    """The products that have enough sourced facts for a row, in the order above."""
    items, cols = (INTERVIEW, INTERVIEW_COLS) if kind == "interview" else (COVER, COVER_COLS)
    return [p for p in items if facts(p, cols) >= MIN_FACTS and p.get("sources")]


def site(url):
    """The address a reader recognizes: "huru.ai", "tealhq.com/pricing"."""
    s = url.split("://", 1)[-1].rstrip("/")
    return s[4:] if s.startswith("www.") else s


def table(kind, ours, e, fdate):
    """The comparison as HTML: one row for this site's tool (`ours`: {"name", "sub", <column>: text}) and one per product with
    enough sourced facts, each with the date and the pages its facts were read on. `e` escapes text, `fdate` writes a date."""
    cols = INTERVIEW_COLS if kind == "interview" else COVER_COLS
    head = '<thead><tr><th scope="col">Tool</th>' + "".join(f'<th scope="col">{e(lab)}</th>' for _, lab in cols) + "</tr></thead>"
    def row(name, sub, cells, us=False):
        return (f'<tr{' class="us"' if us else ""}><th scope="row"><b>{e(name)}</b><span>{sub}</span></th>'
                + "".join(f'<td data-l="{e(lab)}"' + ("" if cells.get(k) else ' class="ns"') + f'>{e(cells.get(k) or "Not stated")}</td>' for k, lab in cols) + "</tr>")
    body = row(ours["name"], e(ours["sub"]), ours, us=True) + "".join(
        row(p["name"], f"As of {fdate(READ)}, from " + ", ".join(f'<a href="{e(u)}" rel="nofollow noopener" title="{e(w)}">{e(site(u))}</a>' for u, w in p["sources"]), p)
        for p in rows(kind))
    return f'<div class="cmpwrap"><table class="cmpt cmpk">{head}<tbody>{body}</tbody></table></div>'


def lists(kind, e, **fill):
    """"Where they are better" and "where this tool differs", as two short lists."""
    li = lambda xs: "".join(f"<li>{e(x.format(**fill))}</li>" for x in xs)
    return ('<div class="cmpbw"><div><p class="flabel">Where they are better</p><ul>' + li(THEY_BETTER[kind]) + "</ul></div>"
            '<div><p class="flabel">Where this one differs</p><ul>' + li(WE_DIFFER[kind]) + "</ul></div></div>")


def faq(kind, fdate, **fill):
    return [(q, a.format(date=fdate(READ), n_tools=len(rows(kind)), **fill)) for q, a in FAQ[kind]]


def test():
    for kind, items, cols in (("interview", INTERVIEW, INTERVIEW_COLS), ("cover", COVER, COVER_COLS)):
        names = [p["name"] for p in items]
        assert len(names) == len(set(names)), kind
        for p in items:
            assert p["url"].startswith("https://"), p["name"]
            for u, what in p["sources"]:
                assert u.startswith("https://") and what, (p["name"], u)
            for k, _ in cols:
                assert k in p, (p["name"], k)
                v = p[k]
                assert v == "" or (v[0].isupper() or v[0] in "$£0123456789“") and not v.endswith("."), (p["name"], k, v)
        assert len(rows(kind)) >= 4, kind
    assert READ[:4] == "2026"
    # every product a sentence names has a row, so a reader finds the fact the sentence rests on
    for kind, items in (("interview", INTERVIEW), ("cover", COVER)):
        shown = {p["name"] for p in rows(kind)}
        for x in THEY_BETTER[kind] + WE_DIFFER[kind] + [a for _, a in FAQ[kind]]:
            for p in items:
                if p["name"] in x: assert p["name"] in shown, (kind, p["name"])
    esc = lambda x: str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    html = table("interview", {"name": "This page", "sub": "x", "free": "Free"}, esc, str)
    assert html.count("<tr") == 1 + 1 + len(rows("interview")) and "Not stated" in html
    assert "{" not in lists("interview", esc, n_q="1,000", n_work="300") and "{" not in faq("cover", str)[0][1]
    return {k: len(rows(k)) for k in ("interview", "cover")}


if __name__ == "__main__":
    print(test())
