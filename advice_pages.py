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
     "tool": ("tools/interview-answer-builder/", "Interview answer builder", "Type your role and one result; it builds a now-proof-next answer you can say out loud and adjust."),
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
     "title": "Questions to ask at the end of an interview: 30 good ones",
     "desc": "30 questions to ask the interviewer, grouped by what you want to learn: the work, the team, how success is measured, the company and the next steps. Plus what not to ask.",
     "lead": "“Do you have any questions for us?” is not a formality: it is the only part of the interview where you choose the subject. Good questions show you thought about the job, and the answers "
             "tell you whether you want it. Here are 30, grouped by what they find out, and a few that today’s postings make worth asking.",
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
     "mistakes": ["Asking nothing: it reads as no interest.", "Asking about holidays and pay before you have an offer, in a first interview.",
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
     "title": "How to answer “Why are you leaving your job?”",
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
     "mistakes": ["A long Situation and a short Action.", "“We” all the way through: the interviewer is hiring you.", "No Result, or a result with no number.",
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
     "tool": ("my-jobs/", "My jobs", "Track where you applied and when; follow up on time, and see at a glance which applications have gone quiet."),
     "faq": [("How long does it take to hear back after applying for a job?", "Usually one to two weeks when the employer is interested. Many employers do not reply at all when they are not."),
             ("Is no response after two weeks a rejection?", "Often, but not always: some roles move slowly. Follow up once, then keep applying elsewhere."),
             ("How long after an interview should I hear back?", "Usually within one to two weeks. If they gave a date, follow up the day after it."),
             ("Why do some job postings stay open for months?", "The role may be hard to fill, paused, or kept open to collect applications. This site shows each posting’s age so you can choose fresher ones.")],
     "more": (("guides/follow-up-after-applying/", "Following up after applying"), ("guides/how-long-jobs-stay-open/", "How long jobs stay open"), ("new/", "Jobs posted this week"))},
]
