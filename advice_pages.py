"""Career advice: the questions job seekers type most, answered plainly and with today's postings (BLOGS_STUDY.md, 15 Nov 2026).

The owner asked which articles of job-site blogs rank first in Google and whether the site needs them. The same topics come up on The
Muse, Coursera, Indeed's Career Guide and the resume builders: "tell me about yourself", strengths and weaknesses, questions to ask,
salary expectations and so on. Their articles give advice and examples; ours give the same, written here, plus figures recounted
from the open postings on every build and a tool on this site that does the job. Nothing is copied from those pages: only the topics.

Each article: a short answer first (for search engines and AI answers), a formula, examples for different kinds of work, a block
of today's figures, mistakes, questions (FAQPage markup), a tool and the next reads. build.py renders them under /guides/<slug>/.
"""

ARTICLES = []


def render(a, ctx, e, P):
    """The body of one article as HTML. ctx: today's figures (build.py advice_ctx)."""
    h = f'<div class="adv-short"><span>Short answer</span><p>{e(a["short"])}</p></div>'
    if a.get("formula"):
        h += f'<h2>{e(a["formula_h"])}</h2><ol class="adv-steps">' + "".join(f"<li><b>{e(t)}</b> {e(x)}</li>" for t, x in a["formula"]) + "</ol>"
    for h2, paras in a.get("before", ()):
        h += f"<h2>{e(h2)}</h2>" + "".join(f"<p>{e(p_)}</p>" for p_ in paras)
    if a.get("data") and a["data"] in DATA:
        h += DATA[a["data"]](ctx, e, P)
    if a.get("links"):
        h += f'<h2>{e(a["links_h"])}</h2><ul class="adv-list">' + "".join(f'<li><a href="{P}/{u}">{e(t)}</a>{" " + e(x) if x else ""}</li>' for u, t, x in a["links"]) + "</ul>"
    if a.get("examples"):
        h += f'<h2>{e(a.get("examples_h", "Examples"))}</h2><div class="adv-ex">' + "".join(
            f'<figure><figcaption>{e(who)}</figcaption><blockquote>{e(txt)}</blockquote></figure>' for who, txt in a["examples"]) + "</div>"
    for h2, paras in a.get("after", ()):
        if all(p_.rstrip().endswith("?") for p_ in paras) or len(paras) > 4:      # a list of questions or of short answers reads better as a list
            h += f'<h2>{e(h2)}</h2><ul class="adv-list">' + "".join(f"<li>{e(p_)}</li>" for p_ in paras) + "</ul>"
        else:
            h += f"<h2>{e(h2)}</h2>" + "".join(f"<p>{e(p_)}</p>" for p_ in paras)
    if a.get("mistakes"):
        h += '<h2>Mistakes to avoid</h2><ul class="crosses">' + "".join(f"<li>{e(m)}</li>" for m in a["mistakes"]) + "</ul>"
    if a.get("tool"):
        u, name, why = a["tool"]
        h += f'<div class="adv-tool"><div><b>{e(name)}</b><p>{e(why)}</p></div><a class="btn primary" href="{P}/{u}">Open it, free</a></div>'
    if a.get("faq"):
        h += '<h2>Questions</h2><dl class="qa">' + "".join(f"<div><dt>{e(q)}</dt><dd>{e(x)}</dd></div>" for q, x in a["faq"]) + "</dl>"
    h += (f'<div class="adv-jobs"><p>Practice is easier with a real posting in front of you.</p><a class="btn ghost" href="{P}/jobs/">'
          f'Find a job to practise on: {ctx["n"]:,} open now</a></div>')
    return h


def faq_ld(a, json):
    if not a.get("faq"): return ""
    return ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": x}} for q, x in a["faq"]]}, ensure_ascii=False).replace("</", "<\\/") + "</script>")


# ---------- today's figures, one block per kind ----------
def _skills(ctx, e, P):
    rows = "".join(f'<li><a href="{P}/skills/{s}/">{e(nm)}</a><span>{pc}% of postings</span></li>' for nm, s, pc in ctx["skills"][:10])
    return (f'<h2>What today’s postings ask for</h2><p>Out of {ctx["n"]:,} open jobs read this hour, these are the skills named most often. '
            f'If one of them is yours, say it by name: screening software and people look for the words of the posting.</p><ol class="adv-figs">{rows}</ol>')


def _soft(ctx, e, P):
    rows = "".join(f'<li><span>{e(nm)}</span><span>{pc}% of postings</span></li>' for nm, pc in ctx["soft"])
    return (f'<h2>The strengths employers write into postings</h2><p>Counted in the text of {ctx["n_desc"]:,} open postings with a full description. '
            f'A strength from this list, backed by one result, is a safe choice.</p><ol class="adv-figs">{rows}</ol>')


def _pay(ctx, e, P):
    return (f'<h2>What today’s postings pay</h2><p>{ctx["paid_pct"]}% of the {ctx["n"]:,} open jobs here state a pay range. The median of the yearly US-dollar '
            f'ranges is <b>{ctx["med"]}</b>; the middle half runs from {ctx["p25"]} to {ctx["p75"]}. For your own number, open the '
            f'<a href="{P}/salaries/">salary page of your role</a>: it is recounted every hour from postings like the one you are applying to.</p>')


def _open(ctx, e, P):
    return (f'<h2>How long postings stay open</h2><p>Of the {ctx["n"]:,} jobs open today, half were posted within the last <b>{ctx["age_med"]} days</b>, and '
            f'{ctx["old_pct"]}% have been open for 90 days or more. A role that stays open that long is often filled slowly, paused, or kept open on purpose. '
            f'The full figures are in <a href="{P}/guides/how-long-jobs-stay-open/">how long jobs stay open</a>.</p>')


def _entry(ctx, e, P):
    return (f'<h2>Jobs for people starting out, today</h2><p>{ctx["entry_n"]:,} of the {ctx["n"]:,} open jobs have a junior or intern title ({ctx["entry_pct"]}%). '
            f'They are listed on <a href="{P}/entry-level/">entry-level jobs</a>, by field and place.</p>')


DATA = {"skills": _skills, "soft": _soft, "pay": _pay, "open": _open, "entry": _entry}


ARTICLES += [
    {"slug": "tell-me-about-yourself", "cat": "Interviews",
     "title": "How to answer “Tell me about yourself”, with 8 examples",
     "desc": "A three-part answer to the first interview question: who you are now, one result that proves it, and why this job is next. With examples for eight kinds of work.",
     "lead": "It is usually the first question, and the one people prepare least. The interviewer is not asking for your life story: they want a one-minute "
             "summary that shows you fit this job. Here is a formula, examples for different kinds of work, and what today’s postings ask for, so you know which words to use.",
     "short": "Answer in 60 to 90 seconds, in three parts: what you do now, one result that shows you do it well, and why this job is the next step. "
              "Leave out your childhood, your personal life and anything negative about your current employer.",
     "formula_h": "The formula: now, proof, next",
     "formula": [("Now:", "your current role or situation in one sentence, with the kind of work and the level. “I’m a data analyst at a logistics company, the one the sales team asks for numbers.”"),
                 ("Proof:", "one or two results with a number. “Last year I built the weekly report that replaced six spreadsheets; it saves the team about a day a week.”"),
                 ("Next:", "why this job, in words from the posting. “You are looking for someone to own reporting for a growing sales team, which is the part of my work I enjoy most.”")],
     "data": "skills",
     "examples_h": "Examples for different kinds of work",
     "examples": [("Software engineer, 4 years", "I’m a backend engineer at a payments company, mostly Go and PostgreSQL. Last year I led the move of our card service to a new database "
                                                    "with no downtime, and response times fell by a third. I’m applying because your team is rebuilding its core API, and that kind of careful migration is what I do best."),
                  ("Sales, account executive", "I sell software to mid-sized retailers and have closed 112% of my target two years running. What works for me is learning a customer’s "
                                               "business before I pitch. Your product serves the same buyers, and I’d like to sell something I can see them use every day."),
                  ("Career changer, teacher to instructional designer", "For eight years I taught science, and for the last three I also built the online lessons for my school, used by 40 teachers. "
                                                                         "I took a course in instructional design to do it properly. Now I want to do it full time, and your role, building training for new hires, is that work."),
                  ("New graduate", "I just finished a degree in economics. In my last year I analysed delivery data for a local bakery chain as a class project, and they now use my model to plan stock. "
                                   "I’m applying for the analyst program because I want to keep doing that: finding the number that changes a decision."),
                  ("Customer support", "I’ve worked in support for three years, the last two on the chat team of an online bank. I keep a satisfaction score above 95% and I write the help articles "
                                       "that answer the questions we get most. I’d like to bring that to a smaller team where one person can still change how support works."),
                  ("Nurse", "I’m a registered nurse with five years on a busy surgical ward. I’m the person new nurses are paired with in their first month. I’m applying to your clinic "
                            "because I want to work with patients over time rather than for a few days, and your role is mostly follow-up care."),
                  ("Product manager", "I’m a product manager at a travel app, responsible for search. We rebuilt the results page last spring and bookings from search rose 18%. "
                                      "Your product is at the stage mine was two years ago, and I’d like to help it through the same growth."),
                  ("Returning after a break", "I spent six years in marketing, then two years at home with my children. During the break I kept my skills current with a course in "
                                              "paid search and ran the campaigns for a local charity. I’m ready to come back full time, and this role is close to what I did before.")],
     "after": [("When they say “Walk me through your resume”", ["It is the same question with a different order: start with the earliest job that matters and move forward, one sentence each, "
                                                               "and spend most of the time on the last two roles. End the same way, with why this job is next."]),
               ("Make it fit the job", ["Read the posting again before the interview and underline the three things it asks for most. Your “proof” should match one of them. "
                                        "Use their words: if the posting says “stakeholders”, say stakeholders, not “people in other teams”."])],
     "mistakes": ["Starting with where you were born or what you studied fifteen years ago.", "Reading your resume aloud line by line.",
                  "Talking for five minutes: stop at about ninety seconds and let them ask.", "Saying anything bad about your current or last employer.",
                  "A memorised speech that sounds memorised: learn the three parts, not the words."],
     "tool": ("tools/elevator-pitch/", "Elevator pitch generator", "Pick “to open an interview”, type what you do, one result and why this role: it builds the now-proof-next answer in its short form and times it."),
     "faq": [("How long should my answer to “Tell me about yourself” be?", "About 60 to 90 seconds, which is roughly 150 to 200 words spoken. Long enough for three parts, short enough that the interviewer asks a follow-up."),
             ("Should I talk about my personal life?", "Only a sentence, if it explains something the interviewer needs to know, such as a move to their city. Hobbies, family and childhood can wait."),
             ("What if I have no work experience?", "Use a project, a course, volunteering or a part-time job as your proof. A result is a result, whoever it was for."),
             ("Is “Tell me about yourself” the same as “Walk me through your resume”?", "Nearly. The second asks for your jobs in order, so go from the oldest relevant role to today, then end with why this job is next.")],
     "more": (("guides/strengths-and-weaknesses/", "Strengths and weaknesses"), ("guides/questions-to-ask-in-an-interview/", "Questions to ask the interviewer"), ("interview-questions/", "Interview questions by role"))},

    {"slug": "strengths-and-weaknesses", "cat": "Interviews",
     "title": "Strengths and weaknesses for interviews: 20 examples",
     "desc": "How to answer “What are your strengths and weaknesses?”: pick strengths the posting asks for, prove them, and name a real weakness with what you do about it. 20 examples.",
     "lead": "The question checks two things: whether you know what you are good at, and whether you can talk about a weakness without panic or a fake answer. "
             "Below: how to choose, ten strengths and ten weaknesses with answers you can adapt, and the strengths employers actually write into today’s postings.",
     "short": "Name a strength the job needs and prove it with one result. Name a real weakness that does not stop you doing this job, and say what you do about it. "
              "Avoid fake weaknesses such as “I’m a perfectionist” said as praise.",
     "formula_h": "How to answer, step by step",
     "formula": [("Pick the strength from the posting.", "Of the things the job asks for, choose one you can prove. A strength the job does not need is a wasted answer."),
                 ("Prove it.", "One example with a number: what you did, and what changed because of it."),
                 ("Pick a real weakness that is not the core of the job.", "A designer who is slow with spreadsheets is fine; a designer who struggles with feedback is not."),
                 ("Say what you do about it.", "The fix is the part the interviewer remembers: a habit, a course, a tool, a person you ask.")],
     "data": "soft",
     "examples_h": "Ten strengths, with the proof",
     "examples": [("Communication", "I explain technical things to people who are not technical. At my last job I wrote the one-page summaries the board read before each release."),
                  ("Reliability", "I do what I say by the date I say. In two years I missed one deadline, and I told my manager a week before, with a new date I then met."),
                  ("Problem solving", "When orders started failing at checkout, I traced it to a rounding rule in one currency and fixed it the same day."),
                  ("Organisation", "I ran the move of our 60-person office to a new building over a weekend; on Monday everyone had a desk, a working laptop and a parking pass."),
                  ("Learning fast", "I was moved to a team that used Python, which I had never written. Within two months I was reviewing other people’s code."),
                  ("Working with others", "Sales and support used to blame each other for lost customers. I set up a weekly 20-minute call between them, and complaints about handovers stopped."),
                  ("Attention to detail", "I found a contract clause that would have doubled our fees after the first year, two days before signing."),
                  ("Leadership", "I led a team of five through a product launch while our manager was on leave; we shipped on the planned date."),
                  ("Customer focus", "I call back every customer whose problem took more than a day, a week later. Most of my best reviews come from those calls."),
                  ("Calm under pressure", "During our biggest outage I kept the status page and the customer emails going every 30 minutes, so engineers could work without interruptions.")],
     "after": [("Ten weaknesses, and what to say about each", [
         "Public speaking: “I get nervous presenting to large groups, so I volunteer to present at our monthly team meeting to practise; it is easier every time.”",
         "Saying no: “I used to accept every request and then work late. Now I ask what it should replace before I take it on.”",
         "Delegating: “I tended to do things myself because it was quicker. Leading a project taught me it does not scale, so I now hand over a task with a short written brief.”",
         "Impatience with slow processes: “I get impatient when decisions take weeks. I have learned to ask early who decides and by when.”",
         "A tool you do not know well: “I haven’t used Salesforce much; I’ve started the free course and I learn tools quickly, as I did with HubSpot last year.”",
         "Too much detail: “My first reports were too long. I now start with a three-line summary and put the detail in an appendix.”",
         "Asking for help late: “I used to struggle alone too long. I now give myself an hour before I ask.”",
         "Writing: “English is my second language, so I have every important email read by a writing tool and I keep a list of my usual mistakes.”",
         "Numbers: “Finance is not my strength; I take a short course each year and I check every budget with our analyst.”",
         "Being self-critical: “I can be hard on myself after a mistake. I now write down what I would do differently and move on the same day.”"])],
     "mistakes": ["“I’m a perfectionist” or “I work too hard” said as praise: interviewers hear it every day.", "A weakness that is the heart of the job, such as a salesperson who dislikes calling people.",
                  "A strength with no example: anyone can say “I’m a good communicator”.", "Ten strengths at once: choose two or three that match the posting.", "Saying you have no weaknesses."],
     "tool": ("tools/interview-answer-builder/", "Interview answer builder", "Pick the question, add your example and result; it shapes the answer for you to say aloud."),
     "faq": [("How many strengths should I mention?", "Two or three that the job needs, each with one short example. More sounds like a list, not a person."),
             ("What is a good weakness to say in an interview?", "A real one that is not central to this job, followed by what you do about it: public speaking for an analyst, a tool you have not used yet, saying no too rarely."),
             ("Can I say perfectionism as a weakness?", "Only if you describe a real cost and a real fix, such as missing deadlines while polishing, and the habit you now use to stop. As a disguised strength it does not work."),
             ("How do I answer “What is your greatest strength?”", "With the strength from the posting you can best prove: name it, give one example with a number, and connect it to the job in one sentence.")],
     "more": (("guides/tell-me-about-yourself/", "Tell me about yourself"), ("guides/star-method/", "The STAR method"), ("interview-questions/", "Interview questions by role"))},

    {"slug": "questions-to-ask-in-an-interview", "cat": "Interviews",
     "title": "Questions to ask at the end of an interview: 25 good ones",
     "desc": "25 questions to ask the interviewer, grouped by what you want to learn: the work, the team, how success is measured, the company and the next steps. Plus what not to ask.",
     "lead": "“Do you have any questions for us?” is not a formality: it is the only part of the interview where you choose the subject. Good questions show you thought about the job, and the answers "
             "tell you whether you want it. Here are 25, grouped by what they find out, and a few that today’s postings make worth asking.",
     "short": "Ask two or three questions the interview has not answered yet: about the work itself, how success is measured, the team, and the next steps. "
              "Do not ask about anything the posting or the website already says.",
     "formula_h": "How to choose",
     "formula": [("Prepare eight to ten.", "Several will be answered during the interview; you need a few left."),
                 ("Ask about the work first.", "What you will do every day and how it is judged matter more than perks."),
                 ("End with the next steps.", "It tells you when to expect an answer and when to follow up.")],
     "data": "open",
     "after": [("About the work", ["What does a normal week in this role look like?", "What would you want the person in this role to have done after three months? After a year?",
                                   "What is the hardest part of this job?", "Which project would I start on?", "How much of the work is new projects, and how much is keeping things running?",
                                   "Is this a new role, or am I replacing someone? What did they move on to?"]),
               ("About success and growth", ["How do you measure success in this role?", "How are reviews and raises decided, and how often?", "What have people in this role gone on to do?",
                                             "Is there a budget or time for courses and conferences?"]),
               ("About the team and the manager", ["Who would I work with most?", "How does the team decide what to work on?", "How do you give feedback, and how often?",
                                                   "How long have people on the team been here?", "What do you like most about working here?"]),
               ("About the company", ["What is the company’s biggest challenge this year?", "How has the team changed in the last year?", "What would make you leave a job like this?",
                                      "How are people working now: in the office, at home, or both? Is that likely to change?"]),
               ("About the next steps", ["What are the next steps, and when should I expect to hear from you?", "Is there anything in my background that makes you hesitate? I’d like the chance to answer it.",
                                         "Who else will I meet in the process?"]),
               ("Questions our figures make worth asking", ["How long has this role been open? Postings that stay open for months are common; the answer tells you whether the role is urgent, hard to fill or paused.",
                                                            "What is the pay range? A growing share of postings state it, and in several US states the employer must tell you.",
                                                            "Is the role open to people in my country? Remote does not always mean from anywhere."])],
     "mistakes": ["Asking nothing: it reads as no interest.", "Opening a first interview with holidays or your own salary number; asking for the role’s pay range is fine.",
                  "Questions answered by the posting or the company’s website.", "Yes-or-no questions that end the conversation.", "Ten questions when there is time for two."],
     "tool": ("tools/thank-you-email/", "Thank-you email", "After the interview: a short note that mentions one thing you talked about. Ready in a minute."),
     "faq": [("How many questions should I ask at the end of an interview?", "Two or three, chosen from eight to ten you prepared, so you still have some after the interview answers the rest."),
             ("Is it OK to ask about salary in an interview?", "In a first interview, ask what the range for the role is rather than naming your number. Many postings state it; if this one does not, it is a fair question once they show interest."),
             ("What is the best question to ask an interviewer?", "“What would you want the person in this role to have done after three months?” It shows you think about results and tells you what the job really is."),
             ("Should I ask questions in every round?", "Yes. Ask different people different things: the manager about the work, a future colleague about the team, the recruiter about the process.")],
     "more": (("guides/tell-me-about-yourself/", "Tell me about yourself"), ("guides/thank-you-email-after-interview/", "Thank-you email after an interview"), ("guides/how-long-jobs-stay-open/", "How long jobs stay open"))},

    {"slug": "salary-expectations", "cat": "Pay",
     "title": "How to answer “What are your salary expectations?”",
     "desc": "Give a researched range, not a single number: how to find the range for your role from live postings, what to say in a first call and in writing, with example answers.",
     "lead": "Say a number too low and you lose money for years; too high and some employers stop there. The way out is a range you can defend with figures. "
             "Below: where to get the figures, what to say at each stage, and examples, with today’s pay figures from the postings on this site.",
     "short": "Give a range based on what postings for the same job pay, with the bottom of the range at a figure you would accept. "
              "If it is early, ask for their range first; if pushed, give yours and say it depends on the whole offer.",
     "formula_h": "How to answer, step by step",
     "formula": [("Find the market range.", "Look up your job title and place on the salary pages: the middle half of advertised pay is a fair range to aim at."),
                 ("Set your floor.", "The lowest figure you would accept for this job. Your range starts at or above it, never below."),
                 ("Ask for theirs first, once.", "“Could you share the range budgeted for this role?” Many employers have one; some must state it."),
                 ("Give your range and the reason.", "“Based on what similar roles in Berlin advertise, I’m looking at €70,000 to €80,000, depending on the rest of the package.”")],
     "data": "pay",
     "examples_h": "Example answers",
     "examples": [("First call with a recruiter", "Before I name a figure, could you share the range for this role? … Thanks. That works for me if the rest of the package is in line; I was aiming for the upper half of it."),
                  ("When they insist on your number", "From what similar roles advertise, I’m looking for $95,000 to $110,000. I’m flexible on how it is split between salary, bonus and equity."),
                  ("When the range is below what you need", "I appreciate you telling me. I was expecting closer to $85,000, given my five years in the role and the figures for this title in Chicago. Is there room to move?"),
                  ("In an application form with a required field", "Enter the bottom of your researched range, or a range if the field allows it. Avoid 0 or 1: some systems sort or filter on it."),
                  ("Changing careers", "I know I’m new to this field, so I looked at what junior roles here pay: $55,000 to $62,000. I’d be comfortable in that range."),
                  ("When you earn more now", "I understand the budget may be lower than my current salary. What matters most to me is the work; could we talk about the total package, including remote days and training?")],
     "mistakes": ["Naming one exact figure: it can only be cut, not raised.", "Telling your current salary when you do not have to: in many US states employers may not ask.",
                  "A range whose bottom you would not accept: they will pick the bottom.", "Guessing instead of checking what postings pay.", "Agreeing on the spot: you can say you will think about it overnight."],
     "tool": ("tools/salary-checker/", "Salary checker", "Type a job title and a place: the range from live postings, so your number has a source."),
     "faq": [("Should I give a range or a number for salary expectations?", "A range of about 10 to 15%, with the bottom at or above the figure you would accept. A single number can only go down."),
             ("Is it OK to say “negotiable”?", "Once, as a first answer, with a question back about their range. If they ask again, give a range: “negotiable” twice sounds like you have not done the research."),
             ("Where do I find the market rate for my job?", "In job postings that state pay for the same title and place. The salary pages here recount them every hour; government statistics and pay surveys are slower but useful."),
             ("Do I have to tell my current salary?", "Not in places that ban the question, which include California, New York and many other US states. Elsewhere you can still answer with what you are looking for rather than what you earn.")],
     "more": (("guides/negotiate-salary/", "How to negotiate a salary"), ("salaries/", "Salaries by job title"), ("tools/negotiation-email/", "Negotiation email"))},
]

ARTICLES += [
    {"slug": "negotiate-salary", "cat": "Pay",
     "title": "How to negotiate a salary offer, with email examples",
     "desc": "When to negotiate, what number to ask for, what to say on a call and in an email, and what else to ask for when the salary will not move. With examples.",
     "lead": "Most first offers leave room: employers expect a counter and rarely withdraw an offer because of a polite one. The work is in the preparation: "
             "a number with a source, a reason, and a calm request. Here is the order to do it in, with words you can use.",
     "short": "Wait for the written offer, thank them, then ask for a specific figure 5 to 10% above it, backed by what postings for the same role pay and by what you bring. "
              "If the salary cannot move, ask for a signing bonus, more paid leave, remote days or an early review instead.",
     "formula_h": "The order that works",
     "formula": [("Wait for the offer.", "Before it, you are a candidate; after it, they have chosen you, and the balance shifts."),
                 ("Thank them and ask for a day.", "“Thank you, I’m excited about this. Could I come back to you tomorrow?” Nobody serious refuses."),
                 ("Bring a figure with a source.", "The range advertised for the same title and place, and one or two things you bring that the role needs."),
                 ("Ask once, clearly, for one number.", "“Could you do $98,000?” A number is easier to say yes to than “more”."),
                 ("If the answer is no, ask about the rest.", "Bonus, start date, leave, remote days, title, training budget, a review in six months.")],
     "data": "pay",
     "examples_h": "What to say",
     "examples": [("On the phone", "Thank you, I’m really pleased. Based on what this role pays in Austin and my experience running the migration you mentioned, I was hoping for $98,000. Is that possible?"),
                  ("By email", "Thank you for the offer for the Data Analyst role. I’m excited to join the team. Having looked at the range advertised for similar roles in Denver ($78,000 to $90,000) "
                               "and given my three years with SQL and Tableau, would you be able to offer $86,000? I’m ready to sign this week if we can agree."),
                  ("When they say the budget is fixed", "I understand. Would a signing bonus of $5,000 or a salary review after six months be possible instead?"),
                  ("When you have another offer", "I have another offer at $92,000, and I’d prefer to join you. Is there any way to close the gap?"),
                  ("Accepting after a counter", "Thank you for meeting me there. I’m happy to accept the offer at $94,000 and a start date of 3 March. I look forward to the paperwork.")],
     "mistakes": ["Negotiating before you have an offer.", "Inventing a competing offer: it can be checked, and the offer withdrawn.",
                  "Asking for “more” without a number.", "Giving reasons about your rent instead of the market and your work.", "Negotiating several times after you said a number would do."],
     "tool": ("tools/negotiation-email/", "Negotiation email", "Enter the offer and your number: a polite, specific email with your reasons, ready to send."),
     "faq": [("How much more should I ask for in a salary negotiation?", "Usually 5 to 10% above the offer, and within the range postings for the same role advertise. A request far above that range needs a strong reason."),
             ("Can a job offer be withdrawn for negotiating?", "It is rare when the request is polite and backed by figures. Offers are withdrawn for invented competing offers or repeated demands, not for one reasonable counter."),
             ("Should I negotiate by email or on the phone?", "Either works. Email gives you time to choose words and leaves a record; a call is faster and warmer. Many people call, then confirm in an email."),
             ("What can I negotiate besides salary?", "A signing bonus, the start date, paid leave, remote days, the job title, a training budget, equipment, and a pay review after six months.")],
     "more": (("guides/salary-expectations/", "Salary expectations"), ("tools/compare-offers/", "Compare two offers"), ("salaries/", "Salaries by job title"))},

    {"slug": "why-do-you-want-to-work-here", "cat": "Interviews",
     "title": "How to answer “Why do you want to work here?”",
     "desc": "Three reasons in one answer: what the company does, what the role lets you do, and what you bring. How to research it in 20 minutes, with examples.",
     "lead": "The question tests whether you chose this job or applied to fifty. A good answer is specific to this company and this role, and it takes about twenty "
             "minutes of reading to prepare. Here is what to read, how to put it together, and examples.",
     "short": "Name something specific about the company (its product, customers or a recent change), what this role lets you do that you want to do, "
              "and what you bring that fits. Avoid answers that would be true of any employer, such as pay or “a great company”.",
     "formula_h": "Three parts",
     "formula": [("The company:", "one specific fact you found: a product you use, the customers it serves, a launch, its growth, how it works."),
                 ("The role:", "the part of the job you want to do, in the posting’s words."),
                 ("You:", "why you will be good at it, with one piece of proof.")],
     "before": [("What to read in 20 minutes", ["The posting, twice: underline what it says most often. The company’s own site: the product, the customers, the news or blog page. "
                                               "The careers page and its other open jobs: a company hiring in many teams is growing. The company’s page on this site shows its open roles, "
                                               "where they are and what they pay, all read from its own careers page."])],
     "examples_h": "Examples",
     "examples": [("Fintech, backend engineer", "I use your app to split bills, and I noticed how fast the transfers are. The role is on the team behind those payments, which is what I’ve worked on for four years. "
                                                  "I’d like to work on a product people use without thinking about it, and I know how to keep a payment system boring in the best way."),
                  ("Hospital, nurse", "Your hospital is known in the area for its stroke unit, and this role is on it. I spent two years on a neurology ward, and I want to specialise. "
                                      "I also like that you train new nurses on the unit rather than in a classroom."),
                  ("Retail, store manager", "Your stores are the busiest in the mall, and you’re opening two more this year. I’ve run a store through an opening before, from hiring the team to the first Christmas."),
                  ("Non-profit, program coordinator", "I’ve followed your literacy program since a friend volunteered with you, and I read your annual report. "
                                                       "The coordinator role is about organising volunteers, which is what I did for the food bank for three years."),
                  ("Startup, first marketing hire", "You’ve grown without any marketing, which tells me the product is good. Being the first marketer means building everything, "
                                                    "and that’s what I did at my last startup, where we went from no site to 40,000 visitors a month in a year.")],
     "mistakes": ["Pay, benefits or the office as the main reason.", "Praise that fits any company: “a great place to work”, “an industry leader”.",
                  "Facts you got wrong: check the product and the news.", "Talking only about what you get, not what you bring."],
     "tool": ("tools/interview-answer-builder/", "Interview answer builder", "Add the company, the role and one result; it drafts the three-part answer."),
     "faq": [("What is the best answer to “Why do you want to work here?”", "One that only fits this company: a specific fact about it, the part of the role you want, and why you will be good at it."),
             ("Can I say I want to work here for the salary?", "Not as the main reason. It is fine to want fair pay, but the answer should be about the work and the company."),
             ("How is this different from “Why should we hire you?”", "“Why here” is about the company and the role; “why you” is about your fit. Use the same research, with the weight on yourself for the second."),
             ("What if I don’t know much about the company?", "Read its site, its open jobs and the posting for twenty minutes before the interview. One true, specific fact is enough.")],
     "more": (("guides/tell-me-about-yourself/", "Tell me about yourself"), ("companies/", "Company pages"), ("guides/questions-to-ask-in-an-interview/", "Questions to ask"))},

    {"slug": "where-do-you-see-yourself-in-5-years", "cat": "Interviews",
     "title": "How to answer “Where do you see yourself in 5 years?”",
     "desc": "Show you want to grow in a direction this job leads to: skills, responsibility and results, not a title elsewhere. With examples and the career ladder from today’s postings.",
     "lead": "The interviewer wants to know two things: will you stay long enough to be worth training, and does the job fit where you are going. "
             "You do not need a five-year plan, only a direction this role is the first step on.",
     "short": "Describe the skills and responsibility you want to grow into, in a direction this job leads to, and connect it to the company. "
              "Avoid naming another employer, a different career, or the interviewer’s own job.",
     "formula_h": "Three parts",
     "formula": [("What you want to be good at:", "a skill or kind of problem, not a title."),
                 ("What responsibility you want:", "leading a project, a team, an area."),
                 ("Why here:", "how this role and company get you there.")],
     "before": [("The ladder, from today’s postings", ["Most kinds of work have three steps that postings name: no level in the title, Senior, and Lead and above (lead, staff, principal, director). "
                                                      "The how-to-become page of each role shows what each step advertises as pay today, so a five-year answer can be concrete: from the role you apply for to the next step up."])],
     "examples_h": "Examples",
     "examples": [("Junior developer", "In five years I’d like to be the person the team trusts with the hardest parts of the system, and to help new developers the way someone will help me here. Your team’s focus on mentoring is one reason I applied."),
                  ("Sales", "I want to be one of the top performers on the team, and to have started managing a few large accounts. This role, with its enterprise customers, is a good way to get there."),
                  ("Nurse", "I’d like to be a specialist in cardiac care, and maybe a nurse educator for new staff. This ward would give me the experience for both."),
                  ("Analyst", "I want to go from producing reports to deciding what we should measure. In five years I’d like to lead the analytics for a product line, and this role is close to the decisions."),
                  ("Unsure about the long term", "Honestly, I’m still finding out which part of marketing I like most. What I know is that I want to be much better at paid search and analytics, and to own a channel. This role would teach me both.")],
     "mistakes": ["“In your chair”: it was funny once.", "Naming a different career or going back to school full time.", "“I don’t know” with nothing after it.",
                  "A title at another company.", "A plan so fixed it sounds like you will leave if it is not met."],
     "tool": ("how-to-become/", "How to become…", "For each kind of work: the skills postings ask for, the levels and what each pays today."),
     "faq": [("What is a good answer to “Where do you see yourself in 5 years?”", "A direction this job leads to: the skills you want to master and the responsibility you want, with one sentence on why this company helps."),
             ("Is it OK to say I don’t know?", "Say what you do know: the skills you want to grow and the kind of work you enjoy. Uncertainty about titles is normal; no direction at all is not."),
             ("Should I mention starting my own business?", "Not in most interviews: it suggests you will leave. If the business is related and far off, it can show ambition, but say how this job fits first."),
             ("How do I answer if I plan to stay only a year or two?", "Talk about what you want to learn and deliver in the role; you do not have to state a date you plan to leave.")],
     "more": (("how-to-become/", "How to become…"), ("guides/job-levels-explained/", "What the level in a title means"), ("guides/tell-me-about-yourself/", "Tell me about yourself"))},

    {"slug": "why-are-you-leaving-your-job", "cat": "Interviews",
     "title": "Reasons for leaving a job: how to answer “Why are you leaving?”",
     "desc": "Keep it short, true and about what you are moving towards. Answers for 12 situations: growth, pay, layoffs, a bad manager, being fired, relocating and more.",
     "lead": "Every reason for leaving can be told well, including being let go. The rule is the same in every case: true, short, and pointed at what you want next, not at what went wrong.",
     "short": "Give a short, true reason that points forward (“I want to lead projects, and my current role has no room for that”), then talk about why this job fits. "
              "Never criticise your employer or manager.",
     "formula_h": "Two sentences",
     "formula": [("The reason, in one neutral sentence.", "What you want that you cannot get where you are."),
                 ("The link to this job.", "Why this role gives you that.")],
     "examples_h": "Answers for different situations",
     "examples": [("You want to grow", "I’ve learned a lot in four years, but the team is small and there is no room to lead projects. This role would let me do that."),
                  ("You want more pay", "My pay has fallen behind what the role pays elsewhere, and there is no budget to change that this year. I’m looking for a role where my work is paid at the market rate."),
                  ("Your company had layoffs", "My role was one of 200 cut when the company closed its European office. It was a business decision, and I’m proud of what my team shipped before it."),
                  ("You were fired", "The role turned out to be a poor fit: it was mostly cold calling, and I do my best work with existing customers. I learned to ask more about the day-to-day before accepting, which is why I asked so much today."),
                  ("A bad manager", "The team’s direction changed a lot this year, and I want a place where priorities are clearer. From what you’ve said, this team plans by the quarter, which suits me."),
                  ("You are relocating", "My partner has taken a job in Denver, so we’re moving in March. I’ve wanted to work for a company like yours for a while, and this was the moment."),
                  ("Your contract ended", "It was a nine-month contract for the launch, and the launch is done. I’m looking for a permanent role."),
                  ("You are changing careers", "I’ve enjoyed teaching, but I want to work on the training side full time. I’ve built courses for three years and completed a certificate in instructional design."),
                  ("You left to care for family", "I took a year off to care for my father. He’s well now, and I’m ready to come back to full-time work."),
                  ("You’ve been there only a few months", "The role was described as product management, but it has become mostly support. I’m looking for a role that is what it says, and I asked about the day-to-day here for that reason.")],
     "mistakes": ["Criticising your employer, manager or colleagues, even when it is deserved.", "A long story: two sentences, then move on.",
                  "Lying about being fired: references and background checks may show it.", "Making pay the only reason, unless it is the honest one and you say it neutrally."],
     "tool": ("tools/interview-answer-builder/", "Interview answer builder", "Choose your situation; it suggests a neutral, two-sentence answer."),
     "faq": [("What is a good reason for leaving a job?", "Wanting to grow, a better fit for your skills, fair pay, relocation, a contract ending, or a company change such as a layoff. Said neutrally, all are fine."),
             ("How do I explain being fired in an interview?", "Briefly and truthfully, with what you learned and why this job is a better fit. Do not blame anyone, and do not hide it if asked directly."),
             ("Should I say I’m leaving for more money?", "You can, neutrally: say your pay is behind the market for the role. Pair it with something about the work so it is not the only reason."),
             ("How do I explain leaving a job after a few months?", "Say what the role turned out to be compared with what was offered, and what you now check before accepting.")],
     "more": (("guides/employment-gap/", "How to explain a gap in your resume"), ("resignation-letters/", "Resignation letters"), ("guides/tell-me-about-yourself/", "Tell me about yourself"))},
]

ARTICLES += [
    {"slug": "employment-gap", "cat": "Resumes and letters",
     "title": "How to explain a gap in your resume, with examples",
     "desc": "What to write on the resume, what to say in the interview, and examples for caregiving, health, layoffs, study, travel, a business that closed and a long job search.",
     "lead": "Gaps are common, and most interviewers care less about the gap than about how you talk about it. Be brief, be honest, and show you are ready now. "
             "Here is what to put on the resume and what to say, for the usual reasons.",
     "short": "Name the gap plainly in one line on the resume (for example “Career break: family care, 2024–2025”), explain it in one or two sentences in the interview, "
              "and move straight to what you did to stay current and why you are ready for this job.",
     "formula_h": "Three steps",
     "formula": [("On the resume, one line.", "Dates and a short reason, like any other entry. An unexplained hole invites guesses; a line closes the question."),
                 ("In the interview, two sentences.", "What happened, and that it is behind you."),
                 ("Then what you did and why you are ready.", "A course, freelance work, volunteering, a project, or simply that you are ready to start.")],
     "data": "entry",
     "examples_h": "What to say",
     "examples": [("Caring for a family member", "I took eighteen months to care for my mother after her surgery. She has recovered, and I’m ready to come back full time; I spent the last three months refreshing my Excel and SQL."),
                  ("Raising children", "I stayed home for three years while my children were small. They are both in school now, and I’ve been doing freelance bookkeeping for two local businesses since spring."),
                  ("Health", "I took time off for a health issue that is now resolved. I’m fully able to do the job, and I’m keen to get back to work."),
                  ("Laid off, long search", "My role was cut in a round of layoffs last year. Since then I’ve been looking carefully for the right role, and I completed the Google Data Analytics certificate."),
                  ("Study", "I left work to finish a master’s in public health, which I completed in June. My thesis was on clinic waiting times, close to what this role does."),
                  ("Travel", "I took a year to travel, which I had planned for a long time. I’m back, settled, and looking for a long-term role."),
                  ("A business that closed", "I ran my own café for two years. It closed in the downturn, but I learned to manage a budget, hire and run a team, which I’d bring to this role."),
                  ("Relocation", "We moved countries for my partner’s job, and it took a few months to get my work permit. I have it now and can start straight away.")],
     "mistakes": ["Hiding the gap by stretching dates: a background check will show it.", "A long explanation, or more personal detail than needed.",
                  "Sounding apologetic: a gap is a fact, not a fault.", "Leaving it with no sign that you are ready now."],
     "tool": ("resume/", "Resume builder", "Add a career break as an entry like any other; the PDF and Word file are free."),
     "faq": [("Should I explain a gap in my resume?", "Yes, in one line with the dates and a short reason. It answers the question before it is asked."),
             ("How long a gap is a problem?", "A few months between jobs is common and rarely asked about. Longer gaps are fine too when you explain them briefly and show you are ready now."),
             ("Do I have to say why I had a health gap?", "No. “A health issue that is now resolved” is enough; you do not have to give details."),
             ("Does a gap matter for entry-level jobs?", "Less than for senior ones. Employers hiring juniors look at what you can do now: a course or a project during the gap helps most.")],
     "more": (("guides/why-are-you-leaving-your-job/", "Why are you leaving your job"), ("resume/", "Resume builder"), ("entry-level/", "Entry-level jobs"))},

    {"slug": "thank-you-email-after-interview", "cat": "Interviews",
     "title": "Thank-you email after an interview: 6 examples",
     "desc": "When to send it, what to put in it, and six short examples: after a first interview, a phone screen, a panel, a final round, when you forgot to say something, and to follow up.",
     "lead": "A short thank-you note the same day is easy, and few people send one, so it is noticed. It also gives you a second chance to say the one thing you forgot.",
     "short": "Send it within 24 hours to each person you met: thank them, mention one thing from the conversation, say again why you want the job, in under 150 words. "
              "Subject line: “Thank you – [job title] interview”.",
     "formula_h": "What goes in it",
     "formula": [("Thanks, in one line.", "For their time, by name."), ("One specific thing you discussed.", "It shows you listened and makes the note yours."),
                 ("Why you fit, in one sentence.", "Or the point you forgot to make."), ("The next step.", "“I look forward to hearing about the next steps.”")],
     "examples_h": "Examples",
     "examples": [("After a first interview", "Hi Maria, thank you for talking with me today about the Operations Analyst role. I enjoyed hearing how your team cut delivery delays last quarter; that kind of problem is exactly what I like working on. "
                                                "I look forward to the next steps. Best, Daniel"),
                  ("After a phone screen with a recruiter", "Hi James, thanks for the call this morning. It was helpful to understand the team’s structure and the timeline. I’m very interested in the role and happy to send anything else you need. Best, Priya"),
                  ("After a panel interview (one to each person)", "Hi Tom, thank you for your questions about our migration project. Your point about testing in production stayed with me. I’d be glad to bring that experience to your team. Kind regards, Ana"),
                  ("After a final round", "Hi Sarah, thank you for the time today and for introducing me to the team. After meeting everyone, I’m even more sure I’d like to join. Please let me know if I can provide anything else. Best, Lee"),
                  ("When you forgot to mention something", "Hi Ben, thank you for the conversation yesterday. One thing I didn’t mention: I led our switch to HubSpot last year, which sounds close to the project you described. Best regards, Omar"),
                  ("Following up a week later", "Hi Maria, I hope your week is going well. I wanted to follow up on my interview for the Operations Analyst role on 4 March. I’m still very interested and would be glad to hear about the next steps. Best, Daniel")],
     "mistakes": ["Waiting several days.", "One email copied to everyone on the panel.", "Repeating your whole resume.", "Typos in the interviewer’s name.", "Following up every two days."],
     "tool": ("tools/thank-you-email/", "Thank-you email", "Enter the role, the interviewer and one thing you discussed; the note is written for you to edit and send."),
     "faq": [("When should I send a thank-you email after an interview?", "The same day or within 24 hours. A note sent later still helps, but less."),
             ("Should I send a thank-you email after a phone interview?", "Yes, a short one to the recruiter or interviewer. It takes two minutes and keeps you in mind."),
             ("How long should a thank-you email be?", "Under 150 words: thanks, one specific point, one line on why you fit, and the next step."),
             ("When should I follow up if I hear nothing?", "If they gave a date, the day after it. If not, about a week after the interview, once, then again a week later at most.")],
     "more": (("guides/how-long-to-hear-back/", "How long to hear back"), ("tools/thank-you-email/", "Thank-you email tool"), ("guides/follow-up-after-applying/", "Following up after applying"))},

    {"slug": "star-method", "cat": "Interviews",
     "title": "The STAR method for interview answers, with examples",
     "desc": "Situation, Task, Action, Result: how to answer behavioural questions (“Tell me about a time when…”) in two minutes, with eight examples and the questions to prepare for.",
     "lead": "Questions that start with “Tell me about a time when…” are asking for a story. STAR gives the story a shape, so you do not ramble and do not forget the part that matters most: the result.",
     "short": "Answer behavioural questions in four parts: the Situation and your Task in two sentences, the Actions you took (most of the answer, in “I”, not “we”), "
              "and the Result, with a number if possible. About two minutes in all.",
     "formula_h": "Four parts",
     "formula": [("Situation:", "where and when, in one sentence."), ("Task:", "what you had to do, in one sentence."),
                 ("Action:", "what you did, step by step: this is most of the answer. Say “I”."), ("Result:", "what changed, with a number, and what you learned.")],
     "before": [("Questions to prepare for", ["Tell me about a time you solved a difficult problem. A time you disagreed with your manager. A time you failed. A time you had too much work. "
                                             "A time you led without being the manager. A time you dealt with an angry customer. A time you changed someone’s mind. A time you learned something fast. "
                                             "Prepare five or six stories; each can answer several of these questions."])],
     "examples_h": "Examples",
     "examples": [("A difficult problem (engineer)", "S: Checkout failures doubled one Friday. T: I was on call and had to find why. A: I compared failing and working orders, saw they all used one currency, found a rounding rule changed that week, "
                                                     "and rolled it back with a test. R: Failures fell to normal within the hour, and the test now runs on every release."),
                  ("A disagreement (analyst)", "S: My manager wanted a monthly report. T: I thought weekly was needed. A: I showed two months of weekly figures where problems appeared and disappeared inside a month. "
                                               "R: We moved to weekly, and the team caught a stock problem three weeks earlier than before."),
                  ("A failure (marketing)", "S: I ran a launch email to 40,000 customers. T: I had to get it out by 9 am. A: I skipped the test send, and the link was broken. I sent a correction within 20 minutes and wrote a checklist. "
                                            "R: The correction got a higher click rate than the original, and we have not sent a broken link since."),
                  ("Too much work (support)", "S: Two colleagues left in the same month. T: I had to keep response times under four hours. A: I sorted tickets by urgency, wrote saved replies for the ten most common, and asked the product team to fix the top bug. "
                                              "R: We kept under four hours, and the bug fix cut tickets by 15%."),
                  ("An angry customer (retail)", "S: A customer’s order arrived broken the day before a party. T: I had to fix it that day. A: I listened, apologised, found the same item in another store and arranged a courier. "
                                                 "R: It arrived by 6 pm, and she left a five-star review naming me."),
                  ("Leading without the title (nurse)", "S: Our ward had frequent handover errors. T: Nobody owned the problem. A: I drafted a one-page handover sheet, tested it on my shifts and asked colleagues for changes. "
                                                         "R: The ward adopted it, and recorded handover errors fell by half in three months.")],
     "mistakes": ["A long Situation and a short Action.", "“We” all the way through: the interviewer is hiring you.", "No Result, or a vague one: give a number, or at least a clear change.",
                  "A story that answers a different question.", "Inventing a story: follow-up questions expose it."],
     "tool": ("tools/interview-answer-builder/", "Interview answer builder", "Fill in the four parts; it turns them into a two-minute answer and flags a missing result."),
     "faq": [("What is the STAR method?", "A way to answer “Tell me about a time when…” questions: Situation, Task, Action, Result. The action and the result are the parts that matter most."),
             ("How long should a STAR answer be?", "About two minutes. Spend one or two sentences on the situation and task, most of the time on the action, and end on the result."),
             ("How many STAR stories should I prepare?", "Five or six strong ones. Each can be adapted to several questions: a problem solved, a conflict, a failure, a heavy workload, leadership."),
             ("What if my story has no number?", "Use what changed: a deadline met, a complaint stopped, a process others adopted. A number is best, a clear change is enough.")],
     "more": (("guides/strengths-and-weaknesses/", "Strengths and weaknesses"), ("interview-questions/", "Interview questions by role"), ("interview-practice/", "Practise out loud"))},

    {"slug": "how-long-to-hear-back", "cat": "Applying",
     "title": "How long does it take to hear back after applying?",
     "desc": "What usually happens after you apply or interview, how long each step takes, when to follow up, and what today’s postings say about how long roles stay open.",
     "lead": "Silence after an application is the most common experience in a job search, and the most stressful. Knowing the usual timeline helps you decide when to follow up and when to move on. "
             "Here are the usual steps, and figures from the postings on this site about how long roles stay open.",
     "short": "After applying, most employers reply within one to two weeks if they are interested; many never reply if they are not. After an interview, expect news within one to two weeks. "
              "Follow up once after a week, and keep applying elsewhere until you have an offer.",
     "formula_h": "The usual timeline",
     "formula": [("Application to first contact:", "a few days to two weeks for interested employers. Some read applications only after the posting closes."),
                 ("First call to interviews:", "one to three weeks, depending on how many rounds."),
                 ("Final interview to offer:", "a few days to two weeks; longer when references or approvals are needed."),
                 ("No answer after three weeks:", "usually means no, or a paused role. Follow up once and move on.")],
     "data": "open",
     "after": [("When and how to follow up", ["After applying: about a week later, if you have a name to write to; one short message saying you applied and why you fit. "
                                             "After an interview: the day after the date they gave, or a week after the interview if they gave none. Never more than twice."]),
               ("Why you may hear nothing", ["Many roles get hundreds of applications, and some employers only reply to the people they invite. Roles also pause: budgets change and hiring managers leave. "
                                            "A posting that has been open for months is more likely to be one of those. That is why this site shows the age of every posting and lets you hide roles open 90 days or more."])],
     "mistakes": ["Waiting for one answer before applying anywhere else.", "Following up every few days.", "Reading silence as a judgment of your worth: it is usually about volume or timing.",
                  "Applying to a posting open for months without checking the company’s own careers page."],
     "tool": ("tools/follow-up-email/", "Follow-up email", "Pick your situation, a week after applying or after an interview with no reply: a short, polite email, with the day to send it."),
     "faq": [("How long does it take to hear back after applying for a job?", "Usually one to two weeks when the employer is interested. Many employers do not reply at all when they are not."),
             ("Is no response after two weeks a rejection?", "Often, but not always: some roles move slowly. Follow up once, then keep applying elsewhere."),
             ("How long after an interview should I hear back?", "Usually within one to two weeks. If they gave a date, follow up the day after it."),
             ("Why do some job postings stay open for months?", "The role may be hard to fill, paused, or kept open to collect applications. This site shows each posting’s age so you can choose fresher ones.")],
     "more": (("guides/follow-up-after-applying/", "Following up after applying"), ("guides/how-long-jobs-stay-open/", "How long jobs stay open"), ("new/", "Jobs posted this week"))},
]


# ---------- second batch (17 Nov 2026): resumes and letters, starting out, pay, offers, phone and video interviews ----------
def _toproles(ctx, e, P):
    rows = "".join(f'<li><a href="{P}/salaries/{s}/">{e(nm)}</a><span>{e(med)} median · {c:,} postings</span></li>' for nm, s, med, c in ctx.get("top_roles", [])[:12])
    if not rows: return ""
    return (f'<h2>The best-paid kinds of work in today’s postings</h2><p>The median of the yearly US-dollar ranges that postings state, for kinds of work with at least 30 such postings. '
            f'Counted from {ctx["n"]:,} open jobs; the list changes as the postings change.</p><ol class="adv-figs">{rows}</ol>')


DATA["toproles"] = _toproles

ARTICLES += [
    {"slug": "how-to-write-a-resume", "cat": "Resumes and letters",
     "title": "How to write a resume: 7 steps and a free template",
     "desc": "What goes on a resume and in what order, how to write bullets with results, how to fit one page, and how to pass screening software. With a free builder.",
     "lead": "A recruiter gives a resume a few seconds on the first pass, and screening software reads it before that. Both look for the same thing: "
             "the words of the posting, and proof that you did the work. Here are the steps, in order, with what today’s postings ask for.",
     "short": "One page, one column, in this order: name and contacts, a two-line summary, skills, experience with results in numbers, education. "
              "Use the words of the posting, start each line with a verb, and save it as a PDF.",
     "formula_h": "Seven steps",
     "formula": [("Contacts.", "Name, city, phone, email, a link to LinkedIn or a portfolio. No photo, age or full address in the US, UK or Canada."),
                 ("Summary.", "Two lines: what you do, how long, and your strongest result. Skip “hardworking team player”."),
                 ("Skills.", "Eight to twelve that the posting names and you really have, in its words."),
                 ("Experience.", "Newest job first. Under each: three to five lines that start with a verb and end with a result."),
                 ("Numbers.", "How many, how much, how fast, how often. “Answered 60 tickets a day” says more than “handled customer requests”."),
                 ("Education and certificates.", "Degree, school, year. Certificates the posting asks for go near the top."),
                 ("Check and save.", "One page if you have under ten years of experience, no typos, file name “Name-Role.pdf”.")],
     "data": "skills",
     "examples_h": "Lines that work, before and after",
     "examples": [("Customer support", "Before: Responsible for answering customer emails. After: Answered 60 customer emails a day with a 96% satisfaction score, and wrote 14 help articles that cut repeat questions by a fifth."),
                  ("Software engineer", "Before: Worked on the checkout page. After: Rebuilt the checkout page in React, cutting load time from 4.1 to 1.6 seconds and raising completed orders by 7%."),
                  ("Sales", "Before: Managed client accounts. After: Managed 45 client accounts worth $2.1M a year and renewed 93% of them."),
                  ("Warehouse", "Before: Picked and packed orders. After: Picked and packed 180 orders a shift with 99.7% accuracy; trained 6 new starters."),
                  ("Teacher", "Before: Taught maths to year 9. After: Taught maths to 120 year 9 students; the share passing the end-of-year exam rose from 71% to 84%."),
                  ("New graduate", "Before: Member of the marketing society. After: Ran the marketing society’s Instagram, growing it from 400 to 2,300 followers in a year.")],
     "after": [("Passing screening software", ["Most large employers store resumes in an applicant tracking system, and recruiters search it by keyword. Use a plain one-column layout with standard headings "
                                              "(Experience, Education, Skills), no text in images, tables or text boxes, and the posting’s own words for skills and job titles."]),
               ("One page or two?", ["One page for under ten years of experience. Two when you have more and every line earns its place. Nobody is rejected for one page; many are skimmed past on three."])],
     "mistakes": ["Duties instead of results.", "One resume sent to every job: change the summary and skills for each.", "Columns, icons and skill bars that screening software reads as noise.",
                  "Typos, and an email address from school days.", "“References available on request”: it is assumed."],
     "tool": ("resume/", "Free resume builder", "Fill in the form and watch the page take shape; five plain templates, PDF and Word, no account and no charge."),
     "faq": [("How long should a resume be?", "One page for most people. Two pages if you have more than ten years of relevant experience. Recruiters read the top third first, so put the strongest things there."),
             ("What is the best resume format?", "Reverse-chronological: newest job first, in one column with standard headings. It is what recruiters expect and what screening software reads best."),
             ("Should I put a photo on my resume?", "Not in the US, UK, Canada, Australia or Ireland, where employers avoid them. In much of continental Europe and Asia a photo is common; follow local custom."),
             ("How far back should a resume go?", "Ten to fifteen years. Older jobs can be one line each, or left out if they are unrelated.")],
     "more": (("resume/examples/", "Resume examples by job"), ("resume-words/", "Stronger words for a resume"), ("guides/how-to-write-a-cover-letter/", "How to write a cover letter"))},

    {"slug": "how-to-write-a-cover-letter", "cat": "Resumes and letters",
     "title": "How to write a cover letter: a 4-paragraph formula",
     "desc": "A cover letter in four short paragraphs: why this job, your best proof, what you would do first, and a close. With examples, length, and when you can skip it.",
     "lead": "A cover letter is not your resume in sentences. It answers one question the resume cannot: why this job, at this company, and why you. "
             "Four short paragraphs do it, and the whole letter fits on half a page.",
     "short": "Four paragraphs, 200 to 300 words: the job and why you want it; your strongest result that matches the posting; what you would bring in the first months; "
              "a close that asks for a conversation. Address it to a person when you can find the name.",
     "formula_h": "The four paragraphs",
     "formula": [("Opening:", "the job you are applying for and one specific reason you want it at this company."),
                 ("Proof:", "one or two results from your experience that match what the posting asks for most, with numbers."),
                 ("What you bring:", "what you would do or improve in the role, in the posting’s words."),
                 ("Close:", "thanks, and a line asking for a conversation. Then your name.")],
     "examples_h": "Examples",
     "examples": [("Marketing coordinator", "Dear Ms Alvarez, I’m applying for the Marketing Coordinator role. I’ve followed your campaigns since the “Open Late” launch, and I’d like to help run the next one. "
                                              "At my current job I manage our email programme: 40,000 subscribers, an open rate up from 18% to 27% in a year. I also coordinate two freelancers and our weekly content calendar. "
                                              "In your team I’d take the calendar and reporting off the manager’s desk from the first week. I’d welcome a conversation. Thank you for your time. Sam Lee"),
                  ("Career changer", "Dear Hiring Manager, I’m applying for the Junior Data Analyst role. After six years as a store manager I have spent the last year learning SQL and Tableau, because the part of my job I liked most was finding out why sales moved. "
                                     "I built the weekly sales dashboard my region now uses, and it cut reporting time from a day to an hour. I would bring the same habit to your team: start from the question the business is asking. "
                                     "I’d be glad to show you the dashboard. Thank you. Priya Shah"),
                  ("No experience", "Dear Mr Okafor, I’m applying for the Customer Support Trainee role. I have just finished school, where I ran the help desk for our student laptop scheme and answered about 20 questions a week. "
                                    "I’m patient, I write clearly, and I like solving the problem in the first reply. I’d be glad to learn your product and start with the simplest tickets. Thank you for considering me. Dana Kim")],
     "after": [("Do I need a cover letter at all?", ["Send one when the posting asks for it, when you are changing careers, when you have a gap to explain, or when you have a real reason for wanting this company. "
                                                    "When the form marks it optional and you have nothing specific to say, a strong resume is enough."]),
               ("How to find the name", ["The posting, the company’s team page, or LinkedIn (“Head of Marketing at …”). If you cannot find it, “Dear Hiring Manager” is fine. “To whom it may concern” reads as a form letter."])],
     "mistakes": ["Repeating the resume line by line.", "“I am writing to apply for…” followed by a paragraph about yourself and nothing about them.", "More than one page.",
                  "The wrong company name, left from the last letter.", "Apologising for what you lack instead of showing what you have."],
     "tool": ("tools/cover-letter/", "Cover letter builder", "Paste the posting and your strongest result: a four-paragraph letter you can edit, free."),
     "faq": [("How long should a cover letter be?", "200 to 300 words, three or four short paragraphs. It should fit on half a page."),
             ("Do employers still read cover letters?", "Many do when deciding between similar candidates, and some postings require one. It matters most for career changers and for jobs with a lot of writing."),
             ("How do I start a cover letter?", "With the job and one specific reason you want it at this company. Avoid opening with your own life story."),
             ("Can I use the same cover letter for every job?", "Keep the structure, change the opening and the proof for each posting. A letter that could go to any company reads that way.")],
     "more": (("cover-letter-examples/", "Cover letter examples by job"), ("guides/how-to-write-a-resume/", "How to write a resume"), ("tools/cover-letter/", "Cover letter builder"))},

    {"slug": "how-to-get-a-job-with-no-experience", "cat": "Applying",
     "title": "How to get a job with no experience: 8 ways that work",
     "desc": "Where the jobs for beginners are, what to put on a resume when you have not worked, and eight ways to get the first job, with today’s count of entry-level postings.",
     "lead": "Every posting seems to ask for experience, and you need a job to get it. The way through is to show proof of the same skills from somewhere else, "
             "and to apply where beginners are actually wanted. Both are easier than they look.",
     "short": "Apply to postings that say junior, trainee, intern or entry-level; show proof from study, projects, volunteering or part-time work; "
              "learn the two or three skills those postings name most; and apply to many, early, because beginner roles fill fast.",
     "formula_h": "Eight ways",
     "formula": [("Search by level, not by dream title.", "Junior, trainee, associate, intern, entry-level, apprentice, graduate."),
                 ("Count what you have done as experience.", "Projects, coursework, volunteering, clubs, family business, part-time jobs: describe them like jobs, with results."),
                 ("Learn what the postings name.", "Read ten postings for the job you want and learn the two skills they repeat."),
                 ("Make one piece of proof.", "A portfolio, a small project, a certificate with a project at the end."),
                 ("Start nearby.", "Support, sales, operations and assistant roles hire beginners and lead into most fields."),
                 ("Use internships and apprenticeships.", "Many turn into offers, and they count as experience either way."),
                 ("Ask people.", "A short, specific message to someone doing the job gets more answers than a hundred cold applications."),
                 ("Apply early and widely.", "Beginner roles get the most applicants; the first week matters.")],
     "data": "entry",
     "examples_h": "What to write on the resume",
     "examples": [("Instead of “no experience”", "Volunteer, community food bank (2025–2026): sorted and packed about 300 parcels a week in a team of 8; trained 5 new volunteers."),
                  ("A course project", "Built a budgeting app in Python for a course project; 3 classmates still use it. Code on GitHub."),
                  ("A part-time job", "Barista, 15 hours a week: served about 200 customers a shift, handled the till, opened the shop alone at weekends."),
                  ("A club or society", "Treasurer, university hiking club: managed a $4,000 yearly budget and cut costs 12% by renegotiating the minibus hire.")],
     "mistakes": ["Applying only to roles that ask for three years, and stopping after ten rejections.", "A resume that lists school subjects and nothing you did.",
                  "Waiting until the course ends to start applying.", "Paying anyone for a job, a “placement” or training with a job promised: real employers do not charge."],
     "tool": ("entry-level/", "Entry-level jobs", "Every open job with a junior or intern title, by field and place, read from employers’ own pages."),
     "faq": [("What jobs can I get with no experience?", "Support, sales, retail, hospitality, warehouse, assistant and trainee roles, plus internships and apprenticeships in almost every field."),
             ("How do I write a resume with no experience?", "Lead with skills and education, then describe projects, volunteering and part-time work as you would a job: what you did and what came of it."),
             ("Is it worth applying if I don’t meet every requirement?", "Yes, if you meet about half and can do the core of the job. Requirements describe an ideal person who rarely applies."),
             ("How long does it take to get a first job?", "Often two to six months of steady applying. Fresher postings answer faster, which is why this site shows each posting’s age.")],
     "more": (("entry-level/", "Entry-level jobs"), ("internships/", "Internships"), ("guides/how-to-write-a-resume/", "How to write a resume"))},

    {"slug": "highest-paying-jobs", "cat": "Pay",
     "title": "Highest-paying jobs right now, from live postings",
     "desc": "The kinds of work with the highest advertised pay today, counted from open postings that state a salary range, and what it takes to get into them.",
     "lead": "Lists of the best-paid jobs are usually a year old and built from surveys. This one is counted from the postings that are open today and state their pay, "
             "so it shows what employers are offering now, not what people remember earning.",
     "short": "The list below is counted from the postings open today that state a yearly pay range: the median for each kind of work, highest first. "
              "Open any line for the range, the places and the skills employers ask for.",
     "data": "toproles",
     "after": [("How to read the list", ["The figure is the median of advertised yearly ranges, so half of the postings for that work offer more and half less. Advertised pay is not the same as pay people get: "
                                        "offers move with experience, place and negotiation. Kinds of work with few postings that state pay are left out."]),
               ("What the best-paid jobs have in common", ["Most ask for several years of experience, a scarce skill, or responsibility for money or people. Few are open to beginners, but each has a path: "
                                                          "the how-to-become pages show the levels and what each one pays today."]),
               ("High pay without a degree", ["Sales, skilled trades, operations and many technical roles hire on proof rather than a diploma. Look at the skills a posting names, not only the degree line: "
                                             "some postings do not ask for a degree at all."])],
     "mistakes": ["Choosing a field only by its top salary: the median for beginners is what you will earn first.", "Comparing pay across countries without the cost of living.",
                  "Trusting a single figure with no date and no source."],
     "tool": ("salaries/explorer/", "Salary explorer", "Pick a role, a place, a skill or a level and see what postings advertise today."),
     "faq": [("What is the highest-paying job right now?", "By advertised pay in today’s postings, the work at the top of the list above. It changes as postings open and close, so the page is recounted on every update."),
             ("Which jobs pay over $100,000?", "Most senior roles in software, data, security, product, finance, law and enterprise sales. The site lists every open job whose stated range starts at $100K or more."),
             ("What high-paying jobs need no degree?", "Sales, many software and IT roles, skilled trades and operations management hire on skills and results. Check the posting: some do not ask for a degree."),
             ("Why do your figures differ from salary surveys?", "Surveys collect what people were paid, from employers’ payroll records or from workers’ own answers; these are the ranges employers advertise today. Both are useful: one is what was paid, the other what is on offer.")],
     "more": (("salaries/", "Salaries by job title"), ("salary/100k/", "Jobs paying $100K or more"), ("guides/negotiate-salary/", "How to negotiate a salary"))},

    {"slug": "accept-or-decline-a-job-offer", "cat": "Pay",
     "title": "How to accept, decline or counter a job offer",
     "desc": "What to check before you say yes, how to ask for time, how to counter, and what to write when you accept or decline, with short email examples.",
     "lead": "An offer is the start of a short conversation, not the end of one. You can ask for it in writing, take a day or two, ask questions, counter, accept or decline, "
             "and each has a polite form that keeps the door open.",
     "short": "Thank them, ask for the offer in writing and for a day or two to read it. Check pay, bonus, start date, hours, place of work, leave and notice. "
              "Then accept in writing, counter once with a figure and a reason, or decline briefly and kindly.",
     "formula_h": "The order",
     "formula": [("Thank them and ask for it in writing.", "“Thank you, I’m delighted. Could you send the offer in writing so I can read the details?”"),
                 ("Ask for time.", "One to three working days is normal. Give a date and keep it."),
                 ("Check the whole package.", "Base pay, bonus and how it is earned, equity, start date, hours, remote days, leave, probation and notice."),
                 ("Decide: accept, counter or decline.", "One counter, with a number and a reason. Then a clear yes or no.")],
     "data": "pay",
     "examples_h": "What to write",
     "examples": [("Asking for time", "Thank you for the offer; I’m excited about the role. Could I have until Thursday to read through the details and come back to you?"),
                  ("Accepting", "I’m pleased to accept the offer for the Operations Analyst role at a salary of $72,000, starting on 3 March. Thank you; I’m looking forward to joining the team. Please let me know the next steps."),
                  ("Countering", "Thank you for the offer. I’m keen to join. Given the range advertised for similar roles here and my four years in the field, would $78,000 be possible? I’m ready to accept at that figure."),
                  ("Declining", "Thank you for the offer and for the time everyone gave me. After careful thought I’ve decided to accept another role that is a closer fit for me right now. I enjoyed meeting the team and hope our paths cross again."),
                  ("Declining after accepting elsewhere", "Thank you for your patience. I have accepted another offer, so I’d like to withdraw from the process. I appreciate your time and wish you well with the search."),
                  ("When your employer counter-offers", "Thank you; I appreciate it. I’ve thought about it and my decision is to move on. I’ll do everything I can to hand over well.")],
     "after": [("Should you take a counter-offer from your current employer?", ["Think about why you looked for a new job. If it was only pay, a counter-offer can solve it. If it was the work, the manager or the lack of growth, "
                                                                              "the same reasons will still be there after the raise."])],
     "mistakes": ["Accepting on the phone before you have seen the offer in writing.", "Resigning before the new contract is signed.", "Countering three times after agreeing a figure.",
                  "Ghosting an employer you have decided to decline.", "Accepting two offers and backing out of one late."],
     "tool": ("tools/job-offer-response/", "Job offer response", "Accept, decline, counter or ask for time: the email written for you to edit and send."),
     "faq": [("How long can I take to answer a job offer?", "One to three working days is usual; up to a week for senior roles or a relocation. Ask, give a date and keep it."),
             ("Can I negotiate after accepting a job offer?", "It is much harder and can damage trust. Raise everything before you accept."),
             ("How do I decline a job offer politely?", "Promptly, briefly and with thanks: say you have decided to take another direction, without a long explanation or criticism."),
             ("Is a verbal job offer binding?", "It depends on the country, and it is hard to prove. Wait for the written offer or contract before you resign from your current job.")],
     "more": (("guides/negotiate-salary/", "How to negotiate a salary"), ("tools/compare-offers/", "Compare two offers"), ("resignation-letters/", "Resignation letters"))},

    {"slug": "job-interview-tips", "cat": "Interviews",
     "title": "Job interview tips: how to prepare, what to wear, what to bring",
     "desc": "How to prepare for a job interview: read the posting, five stories, the common questions, what to wear for each kind of workplace, what to bring, and what to do after.",
     "lead": "Most interviews are decided by the hour of preparation before them. Here is that hour, step by step, with what to wear and what to bring to an interview in person. "
             "Phone and video calls have their own checklist.",
     "short": "Read the posting again and match three of your results to what it asks; prepare short answers to the questions every interview asks; dress a step smarter than the team "
              "dresses day to day; bring copies of your resume, your questions and a pen; arrive ten minutes early; send a thank-you email the same day.",
     "formula_h": "How to prepare, step by step",
     "formula": [("Read the posting twice.", "Mark the skills and duties it names: the questions will test those. Use its words in your answers."),
                 ("Learn the company in twenty minutes.", "What it sells and to whom, one recent piece of news, and the profile of the person you will meet."),
                 ("Prepare five short stories.", "A success, a problem you solved, a disagreement, a mistake you learned from, and a time you helped or led others. Tell each with the STAR method in under two minutes."),
                 ("Prepare the common questions.", "About you, why this job, strengths and weaknesses, why you are leaving, and your pay range. They are linked below, each with examples."),
                 ("Write three questions to ask.", "About the work itself, the team, and what a good first three months look like."),
                 ("Plan the day.", "Route and travel time, clothes ready the night before, the interviewer’s name and a phone number on your phone.")],
     "data": "skills",
     "links_h": "The questions almost every interview asks",
     "links": [("guides/tell-me-about-yourself/", "Tell me about yourself", "(how to open in under two minutes)"),
               ("guides/why-do-you-want-to-work-here/", "Why do you want to work here?", ""),
               ("guides/strengths-and-weaknesses/", "What are your strengths and weaknesses?", "(including how to talk about flaws)"),
               ("guides/why-are-you-leaving-your-job/", "Why are you leaving your job?", "(good reasons for leaving, said well)"),
               ("guides/where-do-you-see-yourself-in-5-years/", "Where do you see yourself in five years?", ""),
               ("guides/salary-expectations/", "What are your salary expectations?", ""),
               ("guides/questions-to-ask-in-an-interview/", "Do you have any questions for us?", "(25 good ones)"),
               ("interview-questions/", "Questions for your own job", "(390 kinds of work, from today’s postings)")],
     "after": [("What to wear to a job interview", [
                    "One step smarter than what the team wears on a normal day. If you are unsure, ask the recruiter what people wear at the office: it is an ordinary question.",
                    "Offices, banks, law and sales: a suit or a blazer with trousers or a skirt, a plain shirt or blouse, polished shoes.",
                    "Tech companies and start-ups: smart casual, such as clean chinos or dark jeans with a plain shirt, polo or sweater.",
                    "Shops, cafés and restaurants: neat clothes close to the shop’s own style, and comfortable closed shoes.",
                    "Warehouses, trades and sites: clean work trousers, a collared shirt and safe closed shoes.",
                    "For every job: clean, ironed and fitting; little perfume; nothing you need to keep adjusting."]),
               ("What to bring", [
                    "Two or three printed copies of your resume.", "The posting, your notes and your questions, in a folder.", "A pen and a notebook.",
                    "ID, and anything the employer asked for: portfolio, certificates, the names of references.",
                    "The address, the interviewer’s name and a phone number to call if you are running late.", "A charged phone, on silent."]),
               ("During the interview", [
                    "Arrive about ten minutes early; if you are earlier, wait nearby.", "Greet everyone politely, the person at the front desk too: they are often asked what they thought.",
                    "Take a second before you answer; a short pause reads as thought, not doubt.", "Answer, then stop: most answers fit in one to two minutes.",
                    "Use numbers where you can: how many, how much, how fast.", "If you do not know something, say so and say how you would find out.",
                    "At the end, ask your questions, then ask what the next step is and when you will hear."])],
     "mistakes": ["Not reading the posting again: most questions come from it.", "Speaking badly of a past employer or manager.", "Answers that run past three minutes.",
                  "Having no questions at the end: it reads as no interest.", "Arriving late without calling ahead.", "Looking at your phone during the interview."],
     "tool": ("interview-practice/", "Interview practice", "The page reads common questions aloud and times your answer; nothing is recorded or sent."),
     "faq": [("How do I prepare for a job interview in one day?", "Read the posting and match three of your results to it, prepare answers to the common questions, learn the basics about the company, "
                                                                 "choose your clothes and plan the route. Two focused hours are enough."),
             ("What should I wear to a job interview?", "A step smarter than the team wears day to day: a suit or blazer for an office, smart casual for most tech companies, neat clothes close to "
                                                        "the shop’s style for retail. If you are unsure, ask the recruiter."),
             ("What should I bring to a job interview?", "Printed copies of your resume, the posting, your questions, a pen and notebook, ID, and anything the employer asked for."),
             ("How early should I arrive for a job interview?", "About ten minutes early. If you are much earlier, wait nearby: thirty minutes early can be awkward for the interviewer."),
             ("How do I talk about my flaws in an interview?", "Name a real weakness that does not block the job, and say what you do about it. There are 20 examples in the guide to strengths and weaknesses."),
             ("What should I do after a job interview?", "Send a short thank-you email the same day, write down what you were asked, and follow up once if you have heard nothing by the date they gave.")],
     "more": (("guides/phone-and-video-interview-tips/", "Phone and video interview tips"), ("guides/star-method/", "The STAR method"), ("guides/thank-you-email-after-interview/", "Thank-you email"))},
    {"slug": "phone-and-video-interview-tips", "cat": "Interviews",
     "title": "Phone and video interview tips: a checklist",
     "desc": "How to prepare for a phone screen and a video interview: what the recruiter checks, the set-up, notes you can keep in front of you, and what to do when the technology fails.",
     "lead": "Most hiring starts with a short call and continues on video. They are easier than a room in one way: your notes can sit in front of you. "
             "And harder in another: without a handshake, your voice, your light and your connection do the first impression.",
     "short": "For a phone screen: a quiet place, the posting and your resume in front of you, three short answers ready (about you, why this job, your pay range). "
              "For video: test the link, camera at eye level, light on your face, look at the lens, and have a phone number ready in case the call drops.",
     "formula_h": "The checklist",
     "formula": [("The day before:", "read the posting again; prepare your now-proof-next answer, a reason for wanting the job, a pay range and two questions."),
                 ("Your place:", "quiet, door closed, phone on silent, others warned. A plain wall behind you."),
                 ("Your set-up for video:", "laptop on books so the camera is at eye level, a window or lamp in front of you, headphones, the app updated and the link tested."),
                 ("In front of you:", "the posting, your resume, three results with numbers, your questions. Notes are fine; reading from them is not."),
                 ("During:", "smile when you say hello, pause before answering, look at the lens when you speak, and stop at about two minutes."),
                 ("After:", "a thank-you note the same day.")],
     "data": "open",
     "after": [("What a phone screen checks", ["A recruiter has fifteen to thirty minutes to confirm four things: you can do the core of the job, your pay expectations fit the budget, you can start in time, "
                                              "and you can explain yourself clearly. Have a short answer ready for each."]),
               ("When the technology fails", ["Say so at once, and suggest the fix: “I’ve lost your video; shall I call you on the phone?” Everyone has been there, and staying calm is itself a good sign. "
                                             "Keep the recruiter’s number and email open on your phone before the call starts."])],
     "mistakes": ["Taking the call while walking or driving.", "Reading answers from the screen: the eyes give it away.", "A window behind you, so your face is a shadow.",
                  "Notifications sounding during the call.", "Not knowing your pay range when the recruiter asks."],
     "tool": ("interview-practice/", "Interview practice", "The page reads each question aloud, listens to your answer and times it; nothing is recorded or sent."),
     "faq": [("How long does a phone interview last?", "Usually fifteen to thirty minutes with a recruiter. A call with the hiring manager can run forty-five."),
             ("What should I wear for a video interview?", "What you would wear to the office for that job, top to bottom in case you need to stand. Plain colours work best on camera."),
             ("Can I use notes in a video interview?", "Yes: a few key points beside the camera. Do not read full answers; glance and then look back at the lens."),
             ("What do I do if my internet drops during an interview?", "Rejoin at once; if that fails, phone or email the interviewer and suggest continuing by phone. It is rarely held against you.")],
     "more": (("guides/job-interview-tips/", "Job interview tips"), ("guides/questions-to-ask-in-an-interview/", "Questions to ask"), ("guides/thank-you-email-after-interview/", "Thank-you email"))},
]
