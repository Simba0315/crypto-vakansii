"""The glossary: job-search and hiring words in plain English, one page per term (/glossary/<slug>/) and an index (/glossary/).

TERMS: (term, definition, what to do with it, [links: (path on this site, label)]). The definition is one or two plain sentences;
the second text says what the reader should do about it, so a page is useful on its own. Written for this site.
build.py adds a figure counted from today's postings where one exists (COUNT_KEYS there).

MORE: {term: dict(title=..., sections=[...], qa=[...], aliases=[...])}, the long answer for the terms people search as
"what is <term>" or "<term> meaning". The key is the exact term string from TERMS (TERMS stays a list of 4-tuples).
  title     the page title in the searcher's words, e.g. "What Is an ATS (Applicant Tracking System)? ...", no site name, about 70 characters at most;
  sections  2-4 tuples (heading, [strings]): what the term is in detail, how it works or why it matters, what to do. Each string is
            plain text of 1-3 sentences, shown as a paragraph or a bullet;
  qa        3-5 (question, answer) pairs in the style of Google's "People also ask" (good for an FAQ block and FAQPage markup);
  aliases   optional: other lowercase-hyphen slugs people use for the term (e.g. "ats"); never equal to a TERMS slug.
No invented statistics: where a number appears it is a rule or a worked example, not a measured figure.
Run this file to check TERMS and MORE (test() and test_more()).
"""

TERMS = [
    ("Applicant tracking system (ATS)", "The software a company uses to publish jobs and keep track of applications. Greenhouse, Lever, Ashby and Workday are examples.",
     "Write your resume as plain text in one column, with the posting’s own words: an ATS reads text, and recruiters search it by keyword.", [("tools/resume-match/", "Resume match checker")]),
    ("Apply on company site", "The button that takes you to the employer’s own page, where you fill in the application. This site never collects applications.",
     "Check the address bar before you type anything: it should be the employer’s domain or its hiring system’s.", [("safety/", "Job offer safety")]),
    ("At-will employment", "In most US states, either side can end the job at any time, without notice and without a reason, unless a contract says otherwise.",
     "Read your offer for a notice period or a severance clause; without one, two weeks of notice is a custom, not a duty.", [("resignation-letters/two-weeks-notice/", "Two weeks notice letter")]),
    ("Background check", "A check of what you said about yourself, run after an offer: past employers, degrees and sometimes a criminal record.",
     "Make sure the dates and titles on your resume match what past employers will confirm.", [("resume/", "Resume builder")]),
    ("Base salary", "The fixed pay for the job, before bonuses, commission and equity.",
     "Compare offers on base salary first: it is the part you get for certain, and raises are usually a percentage of it.", [("tools/offer-check/", "Offer check")]),
    ("Benefits", "What the employer gives on top of pay: health insurance, a pension, paid holidays and the like.",
     "Ask for the benefits summary before you accept: in the US, health cover alone can be worth thousands of dollars a year.", [("tools/compare-offers/", "Compare two offers")]),
    ("Bonus", "Extra pay on top of salary, either fixed (a sign-on bonus) or tied to results (a yearly bonus).",
     "Ask how the bonus was paid out in the last two years: a target is not a promise.", [("tools/offer-check/", "Offer check")]),
    ("Category", "The kind of work: engineering, design, sales and so on. This site works it out from the job title and the employer’s department.",
     "If a job you expect is missing from a category, search by its title: titles name the work better than categories do.", [("categories/", "All categories")]),
    ("Closed job", "A job the employer has taken down. Its page stays on this site, marked as closed, so old links keep working.",
     "Do not apply to a closed job; the page links to open jobs of the same kind.", [("archive/", "Closed jobs archive")]),
    ("Contract", "Work for a fixed period or a single project, usually paid by the hour or the day, without the benefits an employee gets.",
     "Price a contract above the matching salary: you pay your own taxes, holidays and insurance.", [("tools/contractor-rate/", "Contractor rate calculator"), ("contract/", "Contract jobs")]),
    ("Counteroffer", "An offer from your current employer to make you stay after you resign: usually more pay or a new title.",
     "Decide before you resign whether any counteroffer would change your mind; if you have signed elsewhere, decline it politely.", [("resignation-letters/new-job/", "Resignation letter for a new job")]),
    ("Cover letter", "A short letter sent with a resume that says why you want this particular job.",
     "Keep it under 250 words and lead with two results; most postings make it optional, but a short one still helps.", [("cover-letter-examples/", "Cover letter examples")]),
    ("Culture fit", "Whether a person suits how a team works. It is often a stand-in for “people like us”, so good employers test values, not likeness.",
     "Prepare one story about how you work with others and one about a disagreement you solved.", [("tools/interview-answer-builder/", "Interview answer builder")]),
    ("Entry-level", "A job for people at the start of a career: internships, graduate roles and junior positions.",
     "Apply even when a posting asks for a year or two of experience: course projects and volunteer work count as proof.", [("entry-level/", "Entry-level jobs"), ("how-to-become/", "How to become…")]),
    ("Equity and stock options", "A share in the company, or the right to buy shares later at a price fixed today. What it is worth depends on what the company turns out to be worth.",
     "Ask for the number of shares, the strike price, the latest valuation and the vesting schedule, then value it at zero until it is sold.", [("tools/equity-calculator/", "Stock options calculator")]),
    ("Exempt and non-exempt", "In the US, exempt staff are paid a salary with no overtime; non-exempt staff must be paid extra for hours over 40 a week.",
     "If a job lists long hours, check which you are: it decides whether overtime is paid.", [("tools/salary-converter/", "Salary converter")]),
    ("Exit interview", "A conversation with HR after you resign about why you are leaving.",
     "Give one or two concrete reasons calmly; this is not the place to settle scores.", [("resignation-letters/", "Resignation letters")]),
    ("Featured job", "A listing an employer paid to show higher in the list. It is always labelled as featured on this site.",
     "Judge a featured job like any other: the label says who paid, not that it is better.", [("pricing/", "Prices for employers")]),
    ("Full-time and part-time", "Full-time is usually about 40 hours a week. Part-time is fewer, often with fewer benefits.",
     "For part-time work, ask whether the hours are fixed or change week to week.", [("part-time/", "Part-time jobs"), ("part-time-jobs-near-me/", "Part-time jobs near me")]),
    ("Garden leave", "A notice period in which you are still employed and paid but told not to work or come in.",
     "You usually cannot start a new job until it ends; check the contract before you set a start date.", [("tools/last-working-day/", "Last working day calculator")]),
    ("Ghost job", "A posting for a role the employer is not actively filling: an old ad left up, or one kept to collect resumes.",
     "Check how long a job has been open and whether it is still on the employer’s own site before you spend an hour on it.", [("methodology/", "How this site checks jobs")]),
    ("Gross and net pay", "Gross pay is before tax and deductions; net pay is what reaches your account.",
     "Salaries in postings are gross. Work out net pay for your country before you compare offers across borders.", [("tools/salary-converter/", "Salary converter")]),
    ("Headcount", "The number of people a team or company is allowed to employ. An “approved headcount” is a role with a budget behind it.",
     "A role marked as backfill or approved headcount is more likely to be filled soon than a speculative one.", [("companies/", "Companies hiring now")]),
    ("Hiring manager", "The person who will be your boss and makes the final hiring decision, as opposed to the recruiter who runs the process.",
     "Write your cover letter and interview answers for the hiring manager: they care about the work, not the keywords.", [("cover-letter-examples/", "Cover letter examples")]),
    ("Hiring system", "Another name for an applicant tracking system: the software that publishes jobs and collects applications.",
     "This site reads jobs straight from these systems, which is why the listings are current.", [("methodology/", "How it works")]),
    ("Hybrid", "Part of the week in the office and part at home.",
     "Ask how many office days are required and whether the team keeps the same days.", [("hybrid/", "Hybrid jobs"), ("jobs-near-me/", "Jobs near me")]),
    ("Internship", "A short placement, usually paid, for students and recent graduates.",
     "Apply early: many summer internships open in the autumn of the year before.", [("internships/", "Internships"), ("summer/", "Summer jobs and internships")]),
    ("Job description", "The text of a posting: what the job is, what it asks for and what it offers.",
     "Read it twice: once for the duties, once for the words to reuse in your resume.", [("job-descriptions/", "Job description templates")]),
    ("Job offer", "The employer’s formal proposal: title, pay, start date and terms. A verbal offer should be followed by a written one.",
     "Do not resign until you have the offer in writing and any checks are complete.", [("tools/offer-check/", "Offer check")]),
    ("Last checked", "The date this site last saw the job on the employer’s own page.",
     "A job checked today is open today; this site re-reads employers’ pages every hour.", [("status/", "Is the data fresh?")]),
    ("Level", "How much experience the job asks for. Junior means little, senior means several years, and lead, staff or principal are the most experienced people in a team.",
     "Levels differ between companies: compare the duties and the years asked, not only the word in the title.", [("salaries/", "Pay by level")]),
    ("LinkedIn Easy Apply", "Applying through LinkedIn with your profile instead of on the employer’s site.",
     "It is fast, so each posting gets many applications; a tailored application on the company site stands out more.", [("tools/linkedin-review/", "LinkedIn profile review")]),
    ("Median", "The middle value. Line up all the salaries from lowest to highest and take the one in the middle: half are above it and half below.",
     "Use the median, not the average, to judge a pay offer: one very high salary hardly moves it.", [("salaries/", "Salaries")]),
    ("Negotiation", "Asking for better terms after an offer: more pay, equity, a sign-on bonus or a later start date.",
     "Ask once, with a number and a reason, in writing; most offers have some room.", [("tools/negotiation-email/", "Negotiation email")]),
    ("Non-compete", "A clause that bars you from working for a competitor for a time after you leave.",
     "Ask how it is defined and how long it lasts before you sign; the law on it differs by country and state.", [("tools/offer-check/", "Offer check")]),
    ("Notice period", "How long you must keep working after you resign, as set by your contract or the custom where you work.",
     "Count it from the day your manager gets your letter, and write the last day as a date.", [("tools/last-working-day/", "Last working day calculator"), ("resignation-letters/", "Resignation letters")]),
    ("On-site", "Work done at the employer’s office or site every day.",
     "Count the commute in time and money when you compare on-site and remote offers.", [("tools/remote-work-savings/", "Remote work savings")]),
    ("Onboarding", "How a new employee is brought in: accounts, training, first tasks and introductions.",
     "Ask what the first 30 days look like; a clear answer is a good sign about the team.", [("tools/interview-scorecard/", "Interview scorecard")]),
    ("Open for", "How many days have passed since the employer posted the job. A job open for more than 90 days is flagged.",
     "A job open for months may be hard to fill or no longer active: check it on the employer’s site.", [("new/", "Jobs posted in the last 3 days")]),
    ("OTE (on-target earnings)", "In sales jobs, base salary plus the commission you earn if you hit your target.",
     "Ask what share of the team hit target last year: OTE assumes you will.", [("roles/account-executive/", "Account executive jobs")]),
    ("Pay transparency", "Laws and practices that require employers to state a pay range in the posting.",
     "Use the stated range to decide whether to apply, and anchor your ask inside it.", [("insights/pay-transparency/", "Employers that state pay")]),
    ("Perk", "Something the employer offers beyond pay, such as visa sponsorship or a budget for courses. This site shows a perk only when the posting mentions it.",
     "Treat perks as a tie-breaker between similar offers, not a reason to take less pay.", [("perks/", "Jobs by perk")]),
    ("Portfolio", "A collection of your work that proves your skills: designs, code, writing or case studies.",
     "Show three pieces with the problem, what you did and the result; quality beats quantity.", [("resume/examples/", "Resume examples")]),
    ("Posting", "One job advertisement, with the duties, the requirements and how to apply. Also called a listing or a job ad.",
     "Save postings you apply to: they are often taken down, and you will want the text before the interview.", [("my-jobs/", "My jobs")]),
    ("Probation period", "The first weeks or months of a job, when either side can end it with short notice.",
     "Use it to check the job matches what was promised, and ask for feedback before it ends.", [("resignation-letters/short-time/", "Leaving after a short time")]),
    ("Recruiter", "A person whose job is to find candidates for an employer. In-house recruiters work for the company; agency recruiters are paid a fee per hire.",
     "Tell a recruiter your pay range early: it saves both of you time.", [("roles/recruiter/", "Recruiter jobs")]),
    ("Reference", "A former manager or colleague who confirms your work to a new employer.",
     "Ask before you give someone’s name, and tell them which job it is for.", [("tools/reference-request-email/", "Reference request email")]),
    ("Referral", "Being recommended for a job by someone who works at the company.",
     "Ask people you know at the company, and send them the posting and a two-line summary of why you fit.", [("companies/", "Companies hiring now")]),
    ("Relocation", "The employer helps pay for your move to another city or country.",
     "Ask whether the help is a fixed sum or paid costs, and whether you must repay it if you leave early.", [("perks/relocation/", "Jobs with relocation support")]),
    ("Remote", "Work done from home or from anywhere outside an office. Many remote jobs are still limited to certain countries or time zones.",
     "Read which countries the job is open to before you apply; this site shows it on every job page.", [("remote/", "Remote jobs"), ("work-from-anywhere/", "Work from anywhere")]),
    ("Requisition (req)", "The internal approval to hire for a role, with its own number in the hiring system.",
     "A recruiter who mentions an open req has a real budget to fill the role.", [("job-descriptions/", "Job description templates")]),
    ("Resignation letter", "A short letter or email that tells your employer you are leaving and on which day.",
     "Give the last day as a date, thank them briefly and offer a handover; leave complaints out.", [("resignation-letters/", "Resignation letter templates")]),
    ("Resume", "A one- or two-page summary of your work and education. Also called a CV.",
     "Lead each line with a verb and end it with a number; cut duties that show no result.", [("resume/", "Resume builder"), ("resume-words/", "Stronger resume words")]),
    ("Salary range", "The lowest and the highest pay the employer says it may offer for the job, before tax.",
     "Expect offers near the middle of the range unless you exceed what the posting asks for.", [("with-salary/", "Jobs that state pay")]),
    ("Screening call", "A short first call, usually with a recruiter, to check basics: interest, pay expectations, work rights and start date.",
     "Have your pay range and notice period ready, and ask what the next steps are.", [("tools/interview-answer-builder/", "Interview answer builder")]),
    ("Severance", "Pay given when an employer ends your job, often tied to years of service.",
     "Read what you are asked to sign in return for severance before you sign it.", [("tools/offer-check/", "Offer check")]),
    ("Sign-on bonus", "A one-time payment for joining, often to make up for a bonus you lose by leaving your old job.",
     "Check whether you must repay it if you leave within a year.", [("tools/negotiation-email/", "Negotiation email")]),
    ("Skill", "A tool or a language that a posting mentions, such as Python or Figma.",
     "List the skills you really have in the posting’s own words; the skills page explains each one in a line.", [("skills/", "Skills explained")]),
    ("STAR method", "A way to answer interview questions with a story: Situation, Task, Action, Result.",
     "Keep it under two minutes and spend most of it on what you did and the result, with a number.", [("tools/interview-answer-builder/", "Interview answer builder")]),
    ("Take-home assignment", "A task to do at home as part of an interview, such as a small project or a case study.",
     "Ask how long it should take and whether it is paid; stop at the time they suggest and explain what you would do next.", [("tools/interview-scorecard/", "Interview scorecard")]),
    ("Talent pool", "A standing invitation to send a resume, not one specific opening.",
     "Apply to real openings first; a talent pool rarely leads to an interview soon.", [("jobs/", "Open jobs")]),
    ("Time to hire", "The days from a posting going up to an offer being accepted.",
     "Expect three to six weeks for most office jobs; follow up after a week of silence.", [("tools/job-search-calculator/", "Job search calculator")]),
    ("Total compensation", "Everything a job pays in a year: base salary, bonus, equity and the value of benefits.",
     "Compare offers on total compensation, but count equity only at a value you believe.", [("tools/compare-offers/", "Compare two offers")]),
    ("Behavioral interview", "An interview built on questions about what you did in past situations, such as “Tell me about a time you missed a deadline”.",
     "Prepare five short stories with a result and a number; most behavioral questions can be answered with one of them.", [("tools/interview-answer-builder/", "Interview answer builder")]),
    ("Career change", "Moving into a different kind of work, often by reusing skills from the old one.",
     "Start with roles that use what you already know, and show proof of the new skills: a course project counts.", [("how-to-become/", "How to become…")]),
    ("Case interview", "An interview where you work through a business problem out loud, common in consulting, product and analyst roles.",
     "Say your assumptions, structure the problem before you calculate, and finish with a recommendation.", [("tools/interview-scorecard/", "Interview scorecard")]),
    ("Commission", "Pay tied to what you sell, usually a percentage of each deal, on top of a base salary.",
     "Ask how commission is calculated, when it is paid and whether it has a cap.", [("glossary/ote/", "OTE explained")]),
    ("Contract-to-hire", "A job that starts as a fixed-term contract and may turn into a permanent one.",
     "Ask how many contractors were hired permanently last year and when the decision is made.", [("contract/", "Contract jobs")]),
    ("Cost of living", "How much it costs to live in a place: rent, food, transport and taxes.",
     "Compare offers in different cities on what is left after costs, not on the salary figure alone.", [("tools/salary-converter/", "Salary converter")]),
    ("Day rate", "A contractor’s price for one day of work.",
     "Set it from the salary you want plus your own costs, divided by the days you will really bill.", [("tools/contractor-rate/", "Contractor rate calculator")]),
    ("Diversity statement", "A paragraph in a posting about the employer’s commitment to equal opportunity, or an essay some employers ask candidates to write.",
     "If an application asks for one, write about concrete things you did, not general values.", [("cover-letter-examples/", "Cover letter examples")]),
    ("Employee referral bonus", "Money an employer pays a staff member who recommends someone it then hires.",
     "This is why people are often glad to refer you: ask them directly and make it easy with a short summary.", [("glossary/referral/", "Referral explained")]),
    ("Employer of record", "A company that legally employs a worker on behalf of another company, often in another country, handling payroll and taxes.",
     "If a remote offer comes through one, you are an employee with local benefits, not a contractor.", [("remote/", "Remote jobs")]),
    ("Fixed-term contract", "Employment for a set period, such as 12 months, with an end date in the contract.",
     "Ask whether it is likely to be extended and whether the notice period still applies.", [("contract/", "Contract jobs")]),
    ("Freelance", "Working for several clients on your own account rather than as an employee.",
     "Agree the scope, the price and the payment date in writing before you start.", [("tools/contractor-rate/", "Contractor rate calculator")]),
    ("Headhunter", "An agency recruiter who looks for candidates for a specific role, usually senior, and is paid by the employer.",
     "You never pay a headhunter; anyone who asks you for money is not one.", [("safety/", "Job offer safety")]),
    ("Job board", "A website that lists job openings from many employers.",
     "Prefer boards that show where each job comes from and when it was last checked, so you do not apply to closed jobs.", [("vs/", "Job sites compared")]),
    ("Job title", "The name of a role, such as “Senior Data Analyst”. The same work can have different titles at different companies.",
     "Search under several titles for the same work; the roles pages list the titles employers use.", [("roles/", "Roles A to Z")]),
    ("Overqualified", "Having much more experience than a role asks for, which some employers fear will make you leave soon.",
     "Say plainly why you want this role now and how long you plan to stay.", [("tools/interview-answer-builder/", "Interview answer builder")]),
    ("Panel interview", "An interview with several interviewers at once, each usually asking about a different area.",
     "Answer the person who asked, but look at everyone; ask for their names and roles at the start.", [("tools/interview-scorecard/", "Interview scorecard")]),
    ("Performance review", "A regular meeting, often yearly, where your manager rates your work and decides on raises and promotions.",
     "Keep a list of results with numbers through the year: it is your evidence at review time.", [("tools/raise-calculator/", "Raise calculator")]),
    ("Promotion", "A move to a higher level or title, usually with more pay and responsibility.",
     "Ask your manager what the next level requires, in writing, and track your progress against it.", [("salaries/", "Pay by level")]),
    ("Raise", "An increase in pay for the same job.",
     "Ask with a number, the results that justify it and what the market pays for the role.", [("tools/raise-request-email/", "Raise request email"), ("tools/raise-calculator/", "Raise calculator")]),
    ("Technical interview", "An interview that tests the skills of the job directly: coding, a design problem or a work sample.",
     "Practise out loud, explain your thinking as you go, and ask questions before you start.", [("tools/interview-scorecard/", "Interview scorecard")]),
    ("Timezone overlap", "The hours in a day when you and your team are all working.",
     "For remote jobs, ask how many overlap hours the team expects and when meetings are held.", [("tools/time-zone-overlap/", "Time zone overlap")]),
    ("Vesting", "How stock options or shares become yours over time, often over four years with nothing until the first year (the cliff).",
     "Note the cliff date: leaving the day before it can mean leaving with nothing.", [("tools/equity-calculator/", "Stock options calculator")]),
    ("Visa sponsorship", "The employer helps a worker from another country get the permit needed to work there.",
     "Search for postings that say so outright; many that do not mention it will not sponsor.", [("perks/visa-sponsorship/", "Jobs with visa sponsorship"), ("relocate/", "Relocation guides by country")]),
    ("Widget", "A small box with a list of jobs that the owner of a website can place on their own site.",
     "Communities and career pages use one to show fresh jobs without updating anything by hand.", [("widgets/", "The job widget")]),
    ("Work authorization", "The legal right to work in a country: citizenship, residence or a work visa.",
     "Answer the question in applications honestly; jobs that require it will not move forward without it.", [("perks/visa-sponsorship/", "Jobs with visa sponsorship")]),
    ("Work from anywhere", "A remote job whose posting names no country and no region at all.",
     "Still ask about time zones and how you will be paid: “anywhere” rarely means every country in practice.", [("work-from-anywhere/", "Work from anywhere jobs")]),
    # 14 Nov, evening: hiring tools, pay and benefits, interviews
    ("Boolean search", "A search that combines words with AND, OR and NOT, and phrases in quotes, to find exactly the jobs or people you mean.",
     "Start with the job title in quotes, add one must-have skill with AND and leave out what you do not want with NOT.", [("tools/boolean-search/", "Boolean search builder"), ("jobs/", "Search jobs")]),
    ("Cost per hire", "Everything a company spends to fill one job, divided by the number of hires: ads, agency fees, tools and staff time.",
     "Count the hours your team spends interviewing too; leaving them out makes hiring look cheaper than it is.", [("tools/cost-per-hire/", "Cost per hire calculator"), ("how-to-hire/", "How to hire…")]),
    ("Interview scorecard", "A form on which every interviewer rates each candidate on the same points, agreed before the interviews start.",
     "Write down what a good answer looks like before the first interview, and score right after each one.", [("tools/interview-scorecard/", "Interview scorecard"), ("how-to-hire/", "How to hire…")]),
    ("JobPosting markup", "Hidden structured data on a job page that lets Google show the job in its job search, with the pay and the place.",
     "Include the pay range, the countries a remote job is open to and a closing date, or Google may leave the job out.", [("tools/jobposting-schema/", "JobPosting markup generator"), ("post-a-job/", "Post a job")]),
    ("Thank-you email", "A short email to the people who interviewed you, sent the same day, thanking them and repeating your interest.",
     "Mention one specific thing from the conversation, so it is clear the email was written after this interview.", [("tools/thank-you-email/", "Thank-you email writer"), ("interview-questions/", "Interview questions")]),
    ("Salary expectations", "The pay you name when an employer asks what you want to earn.",
     "Give a range based on what postings for the same work advertise, and ask for their range first if you can.", [("salaries/", "Salaries"), ("tools/salary-checker/", "Salary checker")]),
    ("Elevator pitch", "A summary of who you are and what you want, short enough to say in 30 to 60 seconds.",
     "Say your current work, one result with a number and the job you want next; practise it out loud.", [("tools/interview-answer-builder/", "Interview answer builder"), ("interview-questions/", "Interview questions")]),
    ("Employment gap", "A period between two jobs that a resume does not account for.",
     "Add one line for what you did in that time, such as study, care or freelance work; a gap is not a fault.", [("tools/resume-review/", "Resume review"), ("resume/", "Resume builder")]),
    ("Resume keywords", "The skills, tools and job titles a recruiter searches for in an applicant tracking system.",
     "Take them from the posting itself and use its exact words, but only for skills you really have.", [("tools/job-description-keywords/", "Job description keyword finder"), ("tools/resume-match/", "Resume match checker")]),
    ("Hiring freeze", "A pause in new hiring, usually to save money, while the people already employed stay.",
     "If an employer you applied to announces one, keep in touch with the recruiter and keep applying elsewhere.", [("trends/", "Hiring trends"), ("jobs/", "Search jobs")]),
    ("Layoff", "When an employer ends jobs for business reasons rather than because of the person’s work.",
     "Ask about severance, the last pay date, health cover and a reference before you sign anything.", [("tools/last-working-day/", "Last working day calculator"), ("jobs/", "Search jobs")]),
    ("Two weeks notice", "Telling your employer you are leaving two weeks before your last day: the usual minimum where the contract says nothing else.",
     "Check your contract first; many contracts and countries require a month or more.", [("tools/resignation-letter/", "Resignation letter builder"), ("tools/last-working-day/", "Last working day calculator")]),
    ("RSU (restricted stock units)", "Company shares promised to you as part of your pay, which become yours step by step as they vest.",
     "Ask how many units you get, the vesting schedule and the share price used, then work out the value per year.", [("tools/equity-calculator/", "Stock options calculator"), ("perks/equity/", "Jobs with equity")]),
    ("Paid time off (PTO)", "Days off with pay: vacation, public holidays and sick days, counted together or apart.",
     "Ask how many days you get in the first year and whether unused days carry over or are paid out.", [("perks/unlimited-pto/", "Jobs with unlimited time off")]),
    ("Unlimited PTO", "A policy with no fixed number of paid days off: you take time off when your manager agrees.",
     "Ask how many days people on the team really took last year; the answer tells you more than the policy.", [("perks/unlimited-pto/", "Jobs with unlimited time off")]),
    ("Parental leave", "Time off when a child is born or adopted, paid in full, in part or not at all.",
     "Ask how many weeks are paid at full salary and whether it applies from your first day.", [("perks/parental-leave/", "Jobs with parental leave")]),
    ("Learning budget", "Money the employer gives each year for courses, books and conferences.",
     "Ask how much it is and whether you choose the courses or your manager does.", [("perks/learning-budget/", "Jobs with a learning budget")]),
    ("Home office stipend", "Money from the employer for a desk, a chair or internet when you work from home.",
     "Ask whether it is paid once or every year, and whether the equipment stays yours if you leave.", [("perks/home-office-stipend/", "Jobs with a home office stipend"), ("remote/", "Remote jobs")]),
    ("Individual contributor (IC)", "Someone who does the work themselves rather than managing people; senior ones are often called staff or principal.",
     "If you do not want to manage people, ask whether the company has a senior path for individual contributors.", [("roles/", "All kinds of work")]),
    ("Remote-first", "A company where working from home is the normal way of working and the office, if there is one, is optional.",
     "Ask whether the leaders work remotely too; if they sit in an office, decisions may still happen there.", [("remote/", "Remote jobs"), ("work-from-anywhere/", "Work from anywhere jobs")]),
    ("Shortlist", "The few candidates chosen for interviews after a first look at all the applications.",
     "To get on it, make the first lines of your resume match the posting’s title and must-have skills.", [("tools/resume-match/", "Resume match checker")]),
    ("Job alert", "An email or message that tells you when a new job matching your search is posted.",
     "Keep the search narrow enough that every alert is worth opening, or you will stop reading them.", [("for-you/", "Jobs for you")]),
    ("No degree required", "A posting that says outright that a university degree is not needed for the job.",
     "Show the skill with results instead: projects, certificates or past work with numbers.", [("perks/no-degree/", "Jobs with no degree required")]),
    ("Mock interview", "A practice interview with someone playing the interviewer, followed by feedback.",
     "Record it or ask for notes, then practise again the questions you found hardest.", [("interview-questions/", "Interview questions"), ("mentors/", "Mentors")]),
    ("Interview loop", "The set of interviews a candidate goes through for one job, often on the same day.",
     "Ask in advance how many interviews there are, with whom, and what each one tests.", [("interview-questions/", "Interview questions")]),
    ("Contingent offer", "A job offer that becomes final only after checks pass, such as references, a background check or a work permit.",
     "Do not resign from your current job until every condition in the offer has been met in writing.", [("tools/offer-check/", "Offer check")]),
    ("Verbal offer", "A job offer made in a call or a meeting before anything is written down.",
     "Thank them, ask when the written offer will arrive and wait for it before you accept or resign.", [("tools/offer-check/", "Offer check"), ("tools/negotiation-email/", "Negotiation email")]),
    ("Clawback", "A rule that you must pay back a bonus, often a sign-on or relocation payment, if you leave within a set time.",
     "Find the period and the amount in the contract, and count it when you compare offers.", [("tools/compare-offers/", "Compare offers")]),
    ("Salary band", "The pay range a company sets for one level of one job; everyone at that level is paid inside it.",
     "Ask for the band, not only the offer: it tells you how much room there is to grow without a promotion.", [("salaries/", "Salaries"), ("tools/salary-checker/", "Salary checker")]),
    ("Cost-of-living adjustment (COLA)", "A raise meant to keep pay in step with rising prices, not a reward for performance.",
     "Compare it with the price rise where you live: a smaller adjustment is a pay cut in real terms.", [("tools/raise-calculator/", "Raise calculator")]),
    ("Geographic pay", "Pay that depends on where the employee lives, common for remote jobs at large companies.",
     "Ask whether pay changes if you move, and which city or region your pay is set for.", [("remote/", "Remote jobs"), ("tools/salary-converter/", "Salary converter")]),
    ("Hourly rate", "Pay for each hour worked, usual for part-time, shift and contract work.",
     "To compare with a yearly salary, multiply by the hours you will really work, not the hours you hope for.", [("tools/salary-converter/", "Salary converter"), ("part-time/", "Part-time jobs")]),
    ("Gig work", "Short paid tasks or jobs found through apps or platforms, without an employment contract.",
     "Count what is left after fees, unpaid waiting time and your own costs before comparing it with a job.", [("contract/", "Contract jobs"), ("part-time/", "Part-time jobs")]),
    ("Seasonal work", "A job for a few weeks or months of the year, such as the holiday season or the summer.",
     "Apply early, often two or three months before the season starts, and ask whether it can turn into a longer job.", [("temporary/", "Temporary and seasonal jobs"), ("summer/", "Summer jobs")]),
    ("Night shift", "Work that takes place mostly between evening and morning, often paid at a higher rate.",
     "Ask whether the extra pay is written into the contract and how the rota changes from week to week.", [("night-shift/", "Night shift jobs")]),
    ("Graduate program", "A structured first job for recent graduates, often moving through several teams over one or two years.",
     "Most open a year in advance with fixed deadlines: note them in a calendar when the season starts.", [("entry-level/", "Entry-level jobs"), ("internships/", "Internships")]),
    ("Apprenticeship", "A paid job with training, where you learn a trade or a profession while doing the work.",
     "Check what qualification you finish with and whether the employer usually keeps apprentices afterwards.", [("entry-level/", "Entry-level jobs"), ("how-to-become/", "How to become…")]),
    ("Upskilling", "Learning new skills for the kind of work you already do.",
     "Pick the skill that today’s postings for your work name most often and you do not have yet.", [("skills/", "Skills in demand")]),
    ("Reskilling", "Learning the skills for a different kind of work, usually to change careers.",
     "Start from a field that reuses what you already do well, and build one piece of proof before applying.", [("how-to-become/", "How to become…"), ("career-quiz/", "Career quiz")]),
    ("Transferable skills", "Skills that are useful in many kinds of work: writing, planning, handling numbers, dealing with people.",
     "Name them in the words of the new field’s postings, with a result from your old work as proof.", [("career-quiz/", "Career quiz"), ("how-to-become/", "How to become…")]),
    ("Soft skills", "Habits of working with people and tasks: communicating, setting priorities, handling change.",
     "Show them with a short story and a result, not with adjectives such as “excellent communicator”.", [("guides/what-postings-ask-besides-skills/", "What postings ask for besides tools")]),
    ("Hard skills", "Skills that can be tested directly: a language, a program, a method or a licence.",
     "List the ones the posting names, in its exact words, and show where you used each.", [("skills/", "Skills in demand"), ("tools/resume-match/", "Resume match checker")]),
    ("Resume summary", "Two or three lines at the top of a resume that say who you are, what you are best at and what you want next.",
     "Write it last, for the job you are applying to, and include one result with a number.", [("resume/", "Resume builder"), ("tools/resume-review/", "Resume review")]),
    ("Informational interview", "A short conversation with someone who does a job you are curious about, to learn about the work rather than to ask for a job.",
     "Ask for 20 minutes, prepare three questions and send a thank-you note the same day.", [("mentors/", "Mentors"), ("how-to-become/", "How to become…")]),
    ("Return to office (RTO)", "An employer’s rule bringing staff who worked from home back to the office for some or all days.",
     "Ask how many days are required now and whether the rule has changed in the past year.", [("guides/office-days-in-hybrid-jobs/", "Office days in hybrid jobs"), ("hybrid/", "Hybrid jobs")]),
    ("Offer deadline", "The date by which an employer wants your answer to a job offer.",
     "Asking for a few more days to decide is normal; say when you will answer and keep to it.", [("tools/offer-check/", "Offer check"), ("tools/compare-offers/", "Compare offers")]),
    ("Exploding offer", "A job offer that expires very quickly, often within a day or two, which leaves little time to compare.",
     "Ask for the deadline to be moved; an employer that refuses a reasonable request is telling you something.", [("tools/compare-offers/", "Compare offers")]),
    ("Hiring committee", "A group that reads the interview feedback and decides on an offer, instead of one manager alone.",
     "Every interviewer’s notes reach the committee, so treat each interview as if it decided the outcome.", [("interview-questions/", "Interview questions"), ("tools/interview-scorecard/", "Interview scorecard")]),
    ("Moonlighting", "Doing a second paid job alongside your main one.",
     "Read your contract for rules on outside work and conflicts of interest before you start.", [("part-time/", "Part-time jobs"), ("contract/", "Contract jobs")]),
    ("Bootcamp", "A short, intensive course that teaches a job skill, such as coding or design, in weeks or months.",
     "Before paying, ask how many graduates found work in the field and at what pay, with proof.", [("how-to-become/", "How to become…"), ("entry-level/", "Entry-level jobs")]),
    ("Certification", "A credential from a test set by a vendor or a professional body, such as a cloud or accounting certificate.",
     "Take one when the postings you want name it; otherwise put the time into a project you can show.", [("skills/", "Skills in demand")]),
    ("CV", "The word many countries use for a resume; in research and teaching, a longer record of all your work and publications.",
     "Use the word the posting uses, and keep a business CV to two pages at most.", [("resume/", "Resume builder"), ("resume/examples/", "Resume examples")]),
    ("Job hopping", "Changing jobs often, for example every year or less.",
     "Give each move one line of reason and one result, so the pattern reads as growth, not restlessness.", [("resume/", "Resume builder")]),
    ("Ghosting", "When an employer or a candidate stops answering without saying why.",
     "Follow up once, a week after the last contact, then move on and keep applying elsewhere.", [("guides/follow-up-after-applying/", "Follow up after applying")]),
    ("Pay in lieu of notice", "Pay for the notice period instead of working it, when the employer wants the person to leave at once.",
     "Check that it includes everything you would have earned in that time, such as bonus and benefits.", [("tools/last-working-day/", "Last working day calculator")]),
    ("Overtime", "Hours worked beyond the normal week; in many jobs paid at a higher rate.",
     "Ask whether overtime is paid, given back as time off or expected without pay.", [("tools/salary-converter/", "Salary converter")]),
    ("Shift differential", "Extra pay per hour for working nights, weekends or holidays.",
     "Compare the base rate plus the differential, not the base rate alone, when you choose between shift jobs.", [("night-shift/", "Night shift jobs"), ("weekend/", "Weekend jobs")]),
    ("Stipend", "A fixed sum paid for a purpose, such as an internship or a home office, rather than a salary.",
     "Ask whether it is taxed and whether it is paid monthly or once.", [("internships/", "Internships"), ("perks/home-office-stipend/", "Jobs with a home office stipend")]),
    ("Return offer", "An offer of a permanent job made to an intern at the end of the internship.",
     "Ask early in the internship how return offers are decided and what share of interns get one.", [("internships/", "Internships")]),
    ("New grad", "A role meant for people who finished their degree within the last year or so.",
     "Start looking in the autumn before you graduate, and note each employer’s own dates.", [("entry-level/", "Entry-level jobs"), ("internships/", "Internships")]),
    ("Sourcer", "A recruiter who finds and approaches people for a job before they apply.",
     "Keep your public profile current with your title and skills: that is what sourcers search.", [("tools/boolean-search/", "Boolean search builder"), ("tools/linkedin-headline/", "LinkedIn headline")]),
    ("401(k) match", "A US retirement plan at work where you save part of your pay before tax and the employer adds money too, usually a share of what you put in up to a limit.",
     "Ask what the match is and whether it vests, meaning you keep it only after some time; put in at least enough to get all of it, because unclaimed match is lost pay.", [("tools/compare-offers/", "Compare two offers"), ("tools/offer-check/", "Offer check")]),
    ("W-2 employee", "A US worker on the employer’s payroll: the employer withholds income tax from each paycheck, pays part of the payroll taxes and usually offers benefits and paid leave.",
     "If an offer calls you a contractor but sets your hours and tools, ask why it is not an employee role, because the two have different taxes and protections.", [("tools/contractor-rate/", "Contractor rate calculator"), ("contract/", "Contract jobs")]),
    ("Independent contractor (1099)", "A US worker paid per project or per hour who runs their own business: no tax is withheld, no benefits are provided, and a Form 1099 is issued at year end instead of a W-2.",
     "Price your rate above a salaried equivalent to cover your own taxes, insurance and unpaid days, and keep money aside for tax payments.", [("tools/contractor-rate/", "Contractor rate calculator"), ("contract/", "Contract jobs")]),
    ("Non-disclosure agreement (NDA)", "A signed promise not to share the employer’s private information, such as customers, plans or code. Many employers ask for one on the first day, and some before an interview.",
     "Read what counts as confidential and for how long, and keep your own pre-existing work and general skills out of its reach before you sign.", [("safety/", "Job offer safety")]),
    ("Performance improvement plan (PIP)", "A written plan, usually 30 to 90 days long, that lists what a worker must change to keep their job. It can end in recovery, but it often comes before a dismissal.",
     "Ask what exactly will be measured and who decides, put your own answers in writing, and start looking quietly if the goals are vague or unreachable.", [("resignation-letters/", "Resignation letters"), ("tools/last-working-day/", "Last working day calculator")]),
    ("Career ladder", "A company’s list of levels for a kind of work, from junior to senior and beyond, with what is expected at each step and usually a pay band for each.",
     "Ask which level the offer is for and what the next level needs; two jobs with the same title can sit on different rungs and pay differently.", [("salaries/", "Salary data by role and level"), ("tools/salary-checker/", "Salary checker")]),
    ("Staffing agency", "A firm that finds workers for other companies. Either it places you for a fee paid by the employer, or it employs you itself and sends you to work at the client’s site.",
     "Ask who pays you, who your employer is on paper and what happens when the assignment ends; never pay an agency to find you a job.", [("contract/", "Contract jobs"), ("safety/", "Job offer safety")]),
    ("Direct hire", "A job where the company that needs the work employs you itself from the first day, as opposed to hiring through an agency first.",
     "When a posting says direct hire, check that the employer named in the offer is the company you will work for.", [("jobs/", "All open jobs"), ("contract/", "Contract jobs")]),
    ("Four-day week", "A schedule where the working week is four days instead of five, either at the same pay for fewer hours or at the same hours packed into four longer days.",
     "Ask which kind it is, because four ten-hour days is not less work, and whether the schedule is written into your contract or only a trial.", [("perks/4-day-week/", "Jobs with a four-day week"), ("perks/", "All perks")]),
    ("Flextime", "A schedule where you choose when the working day starts and ends, often around a block of hours when everyone is online, as long as the total hours are met.",
     "Ask for the core hours and whether the flexibility is a rule or a favour your manager can withdraw.", [("remote/", "Remote jobs"), ("tools/time-zone-overlap/", "Time zone overlap")]),
    ("Sabbatical", "A long paid or unpaid break from work, from a few weeks to a year, after which you return to the same employer.",
     "Look for the rule in the handbook: how many years of service it needs, whether it is paid and whether your job is guaranteed on return.", [("perks/", "Perks in job postings")]),
    ("Job scam", "A fake job offer made to take money, personal data or access. Typical signs are pay far above the market, hiring by chat without any call, and a request to pay or to cash a cheque first.",
     "Never pay to get a job or send a passport or bank details before a signed offer, and check that the apply link is on the employer’s own domain.", [("safety/", "Job offer safety"), ("methodology/", "How we check jobs")]),
    ("Health savings account (HSA)", "A US savings account for medical costs that you can open next to a high-deductible health plan; the money goes in before tax, grows tax-free and stays yours when you change jobs.",
     "If an employer adds money to it, count that sum as part of your pay when you compare offers.", [("tools/compare-offers/", "Compare two offers"), ("tools/offer-check/", "Offer check")]),
    ("Equal opportunity employer", "A statement that the employer does not choose or reject people because of race, sex, religion, age, disability or similar traits. In the US, most employers must follow the law whether or not they print it.",
     "Treat the line as a minimum, not a sign of a good workplace; the posting’s pay range, benefits and clear duties say more.", [("jobs/", "All open jobs")]),
    ("Vesting cliff", "The waiting period at the start of a stock grant during which none of it is yours yet. A common cliff is one year; if you leave before it ends, you keep nothing.",
     "Ask for the cliff and the full vesting schedule in writing, and note the date your cliff ends before you plan a move.", [("tools/equity-calculator/", "Equity calculator"), ("tools/compare-offers/", "Compare two offers")]),
    ("Equity refresh", "An extra stock grant an employer gives a current employee, usually after a good review or a promotion, on top of the grant in the first offer.",
     "Ask whether refreshes exist and how often they are given; without them, your stock pay falls once the first grant is fully vested.", [("tools/equity-calculator/", "Equity calculator")]),
    ("Backfill", "A job opened to replace someone who left, as opposed to a new job created for growth.",
     "Ask in the interview why the job is open; a backfill tells you what the last person did and how long they stayed.", [("interview-questions/", "Interview questions")]),
    ("Skills-based hiring", "Choosing people by what they can do, shown through tests, work samples or past projects, instead of by a degree or a list of past employers.",
     "Put proof of the skill, such as a project or a result, above your education on the resume.", [("resume/", "Resume builder"), ("skills/", "Skills in demand")]),
    ("Knockout question", "A yes or no question in an application form, such as work authorization or years of experience, that rejects the application at once if it is answered the wrong way.",
     "Answer truthfully, and read each one before you start the form, so you do not spend an hour on a job that cannot take you.", [("jobs/", "All open jobs")]),
    ("Reduction in force (RIF)", "The formal name for a layoff where an employer cuts jobs, not people for poor work. The roles disappear, so the people are not blamed.",
     "Ask in writing for the end date, pay for unused leave, severance and how long your health cover lasts.", [("resignation-letters/", "Resignation letters"), ("tools/last-working-day/", "Last working day calculator")]),
    ("Rolling basis", "A way of hiring where applications are read as they arrive and the job closes when someone is chosen, not on a fixed date.",
     "Apply in the first days: late applications may never be read once the place is filled.", [("jobs/", "All open jobs")]),
    ("Talent acquisition", "The employer’s hiring department. The word covers finding people, running interviews and making offers, and it often replaces the older name “human resources” for this part of the work.",
     "Write to the talent acquisition contact named in the posting for questions about the process, and to the hiring manager only about the work.", [("interview-questions/", "Interview questions")]),
    ("Bar raiser", "An interviewer from outside the hiring team whose job is to keep the standard of new hires high. At some large companies this person can stop an offer.",
     "Expect broad questions about how you work and decide; prepare stories that do not depend on one team’s tools.", [("tools/interview-answer-builder/", "Interview answer builder")]),
    ("Salary history ban", "A law, in force in a number of US states and cities, that forbids an employer to ask what you were paid before.",
     "If asked anyway, say what range you are looking for and why; you are not required to name your old pay where the ban applies.", [("tools/negotiation-email/", "Negotiation email"), ("salaries/", "Salaries")]),
    ("On-call", "Time outside your normal hours when you must be ready to answer an urgent problem, for example a server that stops working at night.",
     "Ask how often you are on call, what it pays and whether you get time off after a night call.", [("tools/offer-check/", "Offer check")]),
    ("Open enrollment", "The short yearly period in which you may choose or change your health insurance and other benefits. Outside it, you can change only after a life event such as a new job.",
     "Note the deadline in your first week, because a missed one can leave you without cover until the next period.", [("tools/compare-offers/", "Compare two offers")]),
    ("Furlough", "A period of unpaid time off that an employer orders, usually to save money, with the promise that the job is still there afterwards. It is not a layoff, but it carries no guarantee either.",
     "Ask in writing how long it lasts, whether benefits continue and whether you may take other work meanwhile.", [("salaries/", "What jobs pay")]),
    ("Retention bonus", "Extra money an employer promises if you stay until a set date, often during a sale of the company or a big project.",
     "Get the date and the amount in a signed letter, and ask what happens to it if the company lets you go before that date.", [("tools/offer-check/", "Offer check")]),
    ("Sick leave", "Paid or unpaid time off when you are ill. Whether it is paid, and for how many days, depends on the country, the state and the employer.",
     "Read the leave section of your offer before you accept, and ask whether sick days are separate from holiday days.", [("tools/compare-offers/", "Compare two offers")]),
    ("Career fair", "An event, in person or online, where several employers meet job seekers in one place and take resumes or hold short first conversations.",
     "Pick three employers beforehand, read their open jobs and bring one specific question for each; it makes you easy to remember.", [("entry-level/", "Entry-level jobs")]),
    ("Job shadowing", "Spending a day or more beside someone who does a job, to watch how the work really goes. You do not do the work yourself and are usually not paid.",
     "Use it to test a career before you retrain: ask what the worst part of the week is, not only the best.", [("internships/", "Internships")]),
    ("Pre-employment assessment", "A test an employer gives candidates before or between interviews: a skills test, a short work task, a personality questionnaire or a typing test.",
     "Ask what it covers and how long it takes, and set aside a quiet hour; many of them cannot be paused once started.", [("tools/resume-match/", "Resume match checker")]),
    ("Minimum wage", "The lowest hourly pay an employer may legally offer. It is set by law and differs by country, and in some countries by state or city.",
     "If a posting’s pay is near the minimum, look up your own city’s figure on the government’s labour site; where two levels apply, the higher one counts.", [("salaries/", "What jobs pay")]),
    ("Pay stub", "The statement that comes with each payment and shows your gross pay, every deduction and your net pay. It is also called a payslip.",
     "Keep your stubs: lenders, landlords and visa offices often ask for the last few as proof of income.", [("tools/offer-check/", "Offer check")]),
    ("Employment verification", "A check in which a new employer, a lender or a landlord asks your current or former employer to confirm that you worked there, with dates and title.",
     "Make sure your resume matches the dates and title your former employer will confirm, and tell your references before the check starts.", [("resume/", "Resume builder")]),
    ("Cold outreach", "A first message to someone who does not know you, such as a hiring manager or an employee, to ask about a job or a conversation.",
     "Keep it to four sentences: who you are, why this person, one clear ask and an easy way to say no.", [("tools/negotiation-email/", "Negotiation email")]),
    ("Lateral move", "A change to a job at the same level, in a new team or company, with about the same pay. People make one to learn a new skill or to leave a bad manager.",
     "Ask what you will own in the first year and which skill you will gain; if the answer is vague, it is a sideways step with nothing gained.", [("for-you/", "Jobs matched to you")]),
    ("Annual leave", "The paid days off you earn each year for holidays and rest. It is the term used in the UK and many other countries; in the US it is usually called vacation or PTO.",
     "Check how many days you get, whether unused days carry over and whether public holidays are counted inside that number.", [("tools/compare-offers/", "Compare two offers")]),
]


# MORE: the long answer for the terms people search as “what is …” or “… meaning”. Keyed by the exact term string in TERMS.
# title: the page title in the searcher’s words (no site name); sections: (heading, [paragraphs or bullets]);
# qa: (question, answer) pairs in the style of Google’s “People also ask”; aliases: other slugs people use for the term.
MORE = {
    "Applicant tracking system (ATS)": dict(
        title="What Is an ATS (Applicant Tracking System)? How It Reads Your Resume",
        aliases=["ats"],
        sections=[
            ("What an applicant tracking system does", [
                "An ATS is the software behind a company’s careers page. It publishes each opening on the company’s site and often on job boards, collects every application in one database and moves candidates through stages such as screen, interview and offer.",
                "Recruiters use it to search applicants by keyword, read answers to screening questions, schedule interviews, collect interviewer feedback and send emails. Greenhouse, Lever, Ashby, Workday, iCIMS, SmartRecruiters and Taleo are common names.",
                "Large employers and most growing companies use one, because a single opening can draw more applications than anyone could sort by hand.",
            ]),
            ("How an ATS reads your resume", [
                "When you upload a resume, the ATS parses it: it pulls out the text and tries to fill fields such as name, contact details, job titles, employers, dates, education and skills.",
                "Parsing works best on plain text in one column. Tables, text boxes, several columns, headers and footers, images and icons can scramble the order or hide words, so the recruiter sees a garbled profile.",
                "Most systems do not reject people on their own. Rejections come from knock-out questions the employer set, such as work authorization, location or a required licence, or from a recruiter who searched for keywords and did not find yours.",
            ]),
            ("How to make your resume ATS-friendly", [
                "Use one column, standard headings (Summary, Experience, Education, Skills) and a common font, and put your contact details in the body, not in the page header.",
                "Save it as .docx or as a text-based PDF exported from a word processor, never a scan or an image. If you can select and copy the text in the PDF, an ATS can read it.",
                "Use the posting’s own words for skills and job titles where they are true for you, and spell out an acronym once, such as “search engine optimization (SEO)”.",
                "Answer the screening questions carefully: a wrong answer to a knock-out question ends the application before anyone reads the resume.",
            ]),
        ],
        qa=[
            ("What is ATS in a CV?", "It means the CV will be read by an applicant tracking system before a person sees it. An “ATS-friendly CV” is one the software can parse cleanly: one column, plain headings, real text rather than images, and the words the posting uses."),
            ("Is a 70% ATS score good?", "There is no universal ATS score. Employers’ systems do not give you a percentage; match scores come from third-party resume checkers, each with its own formula, that compare the words in your resume with one posting. Treat a score as a hint about missing keywords, add the ones that are true for you, and do not chase the number."),
            ("What is the difference between an ATS and a CRM?", "An ATS handles people who have applied to a specific job, from application to hire. A recruiting CRM handles people before they apply: sourced candidates, talent pools and email campaigns. Many products now do both."),
            ("How do I know if my CV is ATS-friendly?", "Copy all the text from your file and paste it into a plain text editor: if it comes out in the right order with nothing missing, a parser can read it. Then compare it with the posting for the key skills and titles, for example with a resume match checker."),
            ("Do all companies use an ATS?", "Most large and mid-sized employers do, and many small ones use the hiring tools built into job boards or HR software. If the application page’s address contains greenhouse.io, lever.co, ashbyhq.com or myworkdayjobs.com, you are applying through an ATS."),
        ],
    ),
    "Ghost job": dict(
        title="What Is a Ghost Job? Why Companies Post Them and How to Spot One",
        aliases=["ghost-jobs", "ghost-job-posting"],
        sections=[
            ("What a ghost job is", [
                "A ghost job is a posting that looks open but has no active plan to hire behind it. Some are old ads nobody took down; others are kept up on purpose.",
                "It is not the same as a scam: the employer is real and the role may even exist, but your application is unlikely to lead to an interview soon.",
            ]),
            ("Why companies post ghost jobs", [
                "To collect resumes for a role that may be approved later, so a pipeline of candidates is ready.",
                "Because the role was filled, often internally, and nobody removed the listing, or because a rule requires a public posting even when an internal candidate has already been chosen.",
                "To look as if the company is growing, or to gauge how many people with a skill are available and what they expect to be paid.",
            ]),
            ("How to spot one", [
                "The posting has been up for months, or it disappears and comes back with a new date while the text stays the same.",
                "The description is vague, names no team or manager, and gives no pay range or start date.",
                "The job is missing from the company’s own careers page, or the company has just announced layoffs or a hiring freeze.",
                "On this site every job shows how many days it has been open and when it was last seen on the employer’s own page, and jobs open for more than 90 days are flagged.",
            ]),
        ],
        qa=[
            ("Are ghost jobs illegal?", "In most places, no: there is no general law against leaving up a posting that is not being filled. Lawmakers in some places have proposed rules against misleading job ads, so this may change."),
            ("How common are ghost jobs?", "Studies of job boards and surveys of hiring managers suggest a real share of postings are not tied to an active hire, but the estimates vary widely with the method. Assume any posting older than a few weeks may be stale and check before you invest time."),
            ("How can I tell if a job posting is real?", "Find the same job on the employer’s own careers page, check when it was posted, and look for a named team, a pay range and a start date. A short message to the recruiter or someone on the team asking whether the role is still open settles it fastest."),
            ("Should I still apply to a job that might be a ghost job?", "If it takes a few minutes, yes, but put your real effort into postings that are recent, specific and on the company’s own site. Do not write a long custom cover letter for a listing that has been up for months."),
        ],
    ),
    "At-will employment": dict(
        title="What Is At-Will Employment? Meaning, Exceptions and Your Rights",
        aliases=["at-will"],
        sections=[
            ("What at-will employment means", [
                "Under at-will employment, an employer can end your job at any time, for any reason or for no reason, without notice, as long as the reason is not illegal. You can also quit at any time without notice.",
                "It is the default rule in the United States. Montana is the exception: after a probation period, employers there need good cause to dismiss most employees. Most other countries require notice or a fair reason by law.",
            ]),
            ("Exceptions that limit it", [
                "Discrimination: firing someone because of race, sex, religion, national origin, age, disability or another protected trait is illegal.",
                "Retaliation: an employer cannot fire you for reporting harassment, discrimination, unsafe conditions or fraud, or for taking leave you are entitled to.",
                "Public policy: many states protect you if you are fired for refusing to break the law, serving on a jury or filing a workers’ compensation claim.",
                "Contracts: a written employment contract, a union agreement or, in some states, promises in an employee handbook can require a reason or notice.",
            ]),
            ("What it means for you", [
                "Read your offer letter: most US offers say employment is at-will, so spoken promises of job security carry little weight unless they are in writing.",
                "Two weeks of notice is a courtesy, not a legal duty, but it protects your reference. Keep copies of your reviews and key emails in case you ever need to show why you were let go.",
            ]),
        ],
        qa=[
            ("Can I be fired for no reason in an at-will state?", "Yes, an employer does not have to give a reason. It cannot fire you for an illegal reason, such as discrimination or retaliation, and the real reason matters if you claim one of those."),
            ("Which states are not at-will?", "Montana is the only state where, after a probation period, employers need good cause to dismiss most employees. Every other state starts from at-will and adds its own exceptions."),
            ("Do I have to give two weeks notice in an at-will job?", "No law requires it, but it is the custom, and some employers will not rehire you or will not pay out unused PTO if you leave without it. Check your handbook before you decide."),
            ("Is at-will employment good or bad for employees?", "It lets you leave a job at once without penalty, but it also gives you little job security. That is why severance terms, notice clauses and your own savings matter more in at-will jobs."),
        ],
    ),
    "Background check": dict(
        title="What Is a Job Background Check? What It Shows and How Long It Takes",
        aliases=["employment-background-check", "pre-employment-check"],
        sections=[
            ("What a background check covers", [
                "A background check verifies what you told the employer. It is usually run after a conditional offer, often by a specialist screening company.",
                "Common parts are identity, past employers and dates, degrees and criminal records; some jobs add a driving record, a credit report, professional licences or a drug test. The employer decides which parts to order.",
                "Employment verification normally confirms job titles and dates rather than why you left.",
            ]),
            ("How it works and how long it takes", [
                "In the US, an employer that uses a screening company must tell you in writing and get your permission first. Before it withdraws an offer because of the report, it must send you a copy and a summary of your rights, so you can correct mistakes.",
                "Most checks take a few business days. Checks that need court records from several places, or answers from schools and employers abroad, can take a few weeks.",
                "Other countries have their own rules on what may be checked, such as which criminal records an employer can consider, so the scope depends on where the job is.",
            ]),
            ("How to prepare", [
                "Make the titles, employers and dates on your resume match what past employers will confirm, and keep old contracts or payslips for employers that have closed.",
                "Tell the recruiter early about anything that may show up and give the context; a surprise looks worse than a known fact.",
                "If you are turned down, ask for a copy of the report and dispute any errors with the screening company: mixed-up identities and outdated records do happen.",
            ]),
        ],
        qa=[
            ("What shows up on a background check for a job?", "Whatever the employer orders: usually identity, employment history and education, and often criminal records. Credit reports, driving records and drug tests are added for jobs that handle money, involve driving or are safety-sensitive."),
            ("How long does a background check take?", "Usually a few business days. It takes longer when records are held in several places, when a past employer or school is slow to answer, or when the check covers other countries."),
            ("Can a job offer be withdrawn after a background check?", "Yes, most offers are conditional on the check. In the US the employer must give you a copy of the report and a chance to respond before the decision is final."),
            ("Do background checks show your past salary?", "Usually not. Many US states and cities bar employers from asking about pay history, and employment verification normally confirms only titles and dates."),
        ],
    ),
    "Base salary": dict(
        title="What Is Base Salary? Meaning and What It Does Not Include",
        aliases=["base-pay", "basic-salary"],
        sections=[
            ("What base salary means", [
                "Base salary is the fixed amount an employer pays you for the job, stated per year, month or hour, before tax and before any variable pay.",
                "It does not include bonuses, commission, overtime, tips, equity, shift premiums or benefits. Those come on top and are often not guaranteed.",
            ]),
            ("Why base salary matters most", [
                "It is the part of your pay you get for certain, and it is the figure lenders and landlords usually look at.",
                "Raises, bonus targets, overtime rates and often retirement contributions are calculated as a percentage of it, so a higher base keeps paying for years.",
                "When someone quotes a salary, ask whether it is base or base plus bonus; comparing one person’s base with another’s total is a common mistake in offer talks.",
            ]),
            ("How to use it", [
                "Compare offers on base salary first, then add the parts that are likely to be paid, such as a bonus that was paid in full in recent years.",
                "If an employer cannot move on base, ask for a sign-on bonus, more equity or an earlier salary review, but remember these do not compound the way base does.",
            ]),
        ],
        qa=[
            ("Does base salary include bonus?", "No. Base salary is the fixed pay only; bonuses, commission and overtime are paid on top of it."),
            ("Is base salary before or after tax?", "Before tax. What reaches your bank account is net pay, after income tax, social security and deductions such as health insurance or a pension."),
            ("What is the difference between base salary and total compensation?", "Base salary is the fixed part; total compensation adds bonus, commission, equity and the value of benefits. Two jobs with the same base can differ a lot in total compensation."),
            ("Is base salary the same as gross salary?", "Not always. Gross pay is everything you earned in a period before deductions, which can include overtime and bonuses; base salary is only the fixed part."),
        ],
    ),
    "Benefits": dict(
        title="What Are Employee Benefits? What a Benefits Package Includes",
        aliases=["employee-benefits", "benefits-package"],
        sections=[
            ("What counts as benefits", [
                "Benefits are what an employer provides on top of pay. The usual core is health, dental and vision insurance, a retirement plan with an employer contribution, paid time off, parental leave, and life and disability insurance.",
                "Many employers add smaller ones: a learning budget, a home office stipend, wellness or gym money, commuter benefits or an employee stock purchase plan.",
                "Some benefits are required by law and others are optional, and what is required differs a lot by country. In the US most health cover comes through employers, while many other countries provide it publicly.",
            ]),
            ("How to value a benefits package", [
                "Ask for the benefits summary and look at what you would pay yourself: your share of health premiums, the deductible, and how much the employer adds to your retirement plan.",
                "Check when each benefit starts; some begin on day one, others after a waiting period or probation.",
                "Turn the benefits into a yearly amount and add it to salary when you compare two offers.",
            ]),
        ],
        qa=[
            ("What are the most common employee benefits?", "Health insurance, a retirement plan, paid time off and parental leave are the core in most countries. Insurance and retirement matter most in the US, where they are tied to the job."),
            ("Are benefits part of salary?", "No, they are separate from salary but part of total compensation. They are worth real money, so count them when you compare offers."),
            ("Can you negotiate benefits?", "Some of them. Standard insurance plans rarely change for one person, but extra paid time off, a later start date, a learning budget, remote work or relocation help often can."),
            ("What does “benefits eligible” mean?", "It means the job qualifies for the employer’s benefits plan. Part-time, temporary and contract roles are often not benefits eligible, so ask before you accept."),
        ],
    ),
    "Bonus": dict(
        title="What Is a Bonus at Work? Types of Bonuses and How They Are Paid",
        aliases=["annual-bonus", "performance-bonus"],
        sections=[
            ("What a bonus is", [
                "A bonus is pay on top of base salary. Some are fixed and promised, like a sign-on bonus; most are variable and depend on your results, your team’s or the company’s.",
                "Common types are the annual or performance bonus, the sign-on bonus, the retention bonus, the referral bonus, the spot bonus for one piece of work and, in some countries, a holiday or 13th-month payment.",
            ]),
            ("How bonuses are set and paid", [
                "An annual bonus is usually stated as a target, a percentage of base salary, then scaled up or down by company and personal performance. A target is what you may get, not what you will get.",
                "Bonuses are taxed as income. In the US, employers often withhold a flat federal rate on them, so the withholding can look higher than on a normal paycheck even though the final tax is settled on your return.",
                "Many plans require you to be employed on the payout date; if you resign before then, you may get nothing for the year.",
            ]),
            ("What to ask before you count on it", [
                "Is the bonus guaranteed or discretionary, and what share of the target was paid out in each of the last two or three years?",
                "When is it paid, and is the first year pro-rated if you join mid-year?",
                "Does any part have to be repaid if you leave within a set time?",
            ]),
        ],
        qa=[
            ("Is a bonus part of your salary?", "No. Salary is the fixed pay; a bonus is extra and usually variable. It counts toward total compensation but not toward base salary."),
            ("How are bonuses taxed?", "As ordinary income, the same as salary. In the US they are often withheld at a flat federal rate for supplemental wages, which is why a bonus can look heavily taxed; the real tax is settled when you file."),
            ("What is a discretionary bonus?", "A bonus the employer decides on each year with no promised formula or amount. It can be zero, so value it at zero or at what was actually paid in recent years."),
            ("Do you get your bonus if you quit?", "Often not. Many plans pay only people still employed on the payout date, so read the plan rules and time your resignation if the amount matters."),
        ],
    ),
    "Contract": dict(
        title="What Is a Contract Job? Contract vs Permanent Work Explained",
        aliases=["contract-job", "contract-work", "contractor"],
        sections=[
            ("What a contract job is", [
                "A contract job is work for a fixed period or a single project. You may be paid by the hour, the day or a set fee, and the work ends on a date or when the project is done.",
                "There are two main kinds: you work as an independent contractor through your own business and invoice the client, or you are employed by an agency, or directly on a fixed-term contract, for the length of the project.",
                "Independent contractors usually get no employer benefits, no paid leave and no employer pension contributions, and they pay their own taxes and insurance.",
            ]),
            ("Contract vs permanent work", [
                "Contract work usually pays more per hour, because the rate has to cover taxes, benefits, holidays and the gaps between contracts.",
                "Permanent jobs give more security, benefits and a clearer path to promotion; contracts give flexibility, variety and often a faster start.",
                "Labour law looks at how you actually work, not the label. If a client sets your hours, supervises you like staff and you work only for them, you may legally be an employee; treating you as a contractor then is called misclassification.",
            ]),
            ("Before you sign a contract", [
                "Work out the rate you need: take the salary you would accept, add the cost of benefits, taxes and unpaid days, and divide by the days you will really bill.",
                "Check the length, the notice to end it early, the payment terms, who owns your work and whether a clause stops you from working for the client’s competitors or customers.",
            ]),
        ],
        qa=[
            ("Is a contract job worth it?", "It can be, if the rate covers what an employee would get in benefits and paid time off and you have savings for the gaps. It is also a common way into a company that later hires permanently."),
            ("Do contract workers get benefits?", "Independent contractors usually do not. Contractors employed through an agency or an employer of record may get some benefits from that company, so ask who your legal employer is."),
            ("What is the difference between a W-2 and a 1099 contractor?", "In the US, a W-2 contractor is employed, often by an agency, which withholds taxes. A 1099 contractor is self-employed, is paid in full and pays their own taxes, including both halves of social security and Medicare."),
            ("Can a contract job become permanent?", "Yes, often. Some roles are listed as contract-to-hire from the start; in others, good work and telling the manager you would like to stay is enough to start the conversation."),
        ],
    ),
    "Counteroffer": dict(
        title="What Is a Counteroffer? Should You Accept One From Your Employer?",
        aliases=["counter-offer"],
        sections=[
            ("What a counteroffer is", [
                "A counteroffer is what your current employer offers to keep you after you say you are leaving: usually a raise, sometimes a new title, a promotion date, more flexibility or a retention bonus.",
                "The word is also used the other way round: the terms you send back to an employer after it makes you an offer, asking for more pay or better terms.",
            ]),
            ("Why many people regret accepting one", [
                "The reasons you started looking, such as the manager, the work or the lack of growth, usually stay the same; only the pay changes.",
                "Your employer now knows you were ready to leave, which can affect trust, and the raise may simply bring forward money you would have got at your next review.",
                "You also go back on your word to the new employer, which can close that door for good.",
            ]),
            ("How to handle it", [
                "Before you resign, write down what would make you stay. If nothing realistic would, decide in advance to say no.",
                "If you do consider it, ask for every term in writing, including the date of any promised promotion, and compare it with the new offer on total compensation and growth, not salary alone.",
                "If you decline, thank them, say your decision is final and keep the conversation short and friendly.",
            ]),
        ],
        qa=[
            ("Should you accept a counteroffer?", "Only if money was your only reason for leaving and the new terms are in writing. If you were leaving because of the work, the manager or the lack of growth, a raise will not change that."),
            ("How do you decline a counteroffer politely?", "Thank your manager for the offer, say you have committed to the new role and that your decision is final, and move straight on to your handover plan."),
            ("Is it bad to use another offer to get a raise?", "It can work, but it is risky: your employer may let you go, and you may lose the other offer. Use it only if you would really take the other job."),
            ("What is a counteroffer in a job negotiation?", "It is your reply to an employer’s offer with the terms you want instead, such as a higher base salary, more equity or a later start date. Back it with market data and keep it to the few points that matter most."),
        ],
    ),
    "Cover letter": dict(
        title="What Is a Cover Letter? What to Write and Do You Still Need One",
        aliases=["covering-letter", "application-letter"],
        sections=[
            ("What a cover letter is for", [
                "A cover letter is a short letter sent with your resume that explains why you want this job and why you fit it. The resume lists what you did; the letter connects it to this employer’s needs.",
                "It matters most when you are changing careers, explaining a gap or a move, applying to a small company, or when the posting asks for one.",
            ]),
            ("What to put in it", [
                "Open with the job you are applying for and one sentence on why this company.",
                "Give two short examples of results that match the posting’s main requirements, with numbers where you have them.",
                "Close by saying what you would like next, such as a conversation. Keep the whole letter under 250 words, in three or four short paragraphs.",
            ]),
            ("Mistakes to avoid", [
                "Repeating your resume line by line, or sending a letter that would fit any employer.",
                "Getting the company’s or the manager’s name wrong; check it twice.",
                "Writing only about what you want from the job without saying what you will do for the team.",
            ]),
        ],
        qa=[
            ("Is a cover letter still necessary?", "Not always: many postings make it optional and some recruiters skip them. A short, specific one still helps when the job is competitive, when you are changing fields or when it is required."),
            ("How long should a cover letter be?", "Short: under 250 words in three or four paragraphs is enough for most jobs, and never more than one page."),
            ("What should a cover letter include?", "The job title, why this company, two results that match the posting, and a closing line asking for a conversation. Address it to a named person when you can find one."),
            ("Should I write a cover letter if it is optional?", "Yes, if you have something the resume cannot say, such as a career change, a move to the city or a personal link to the product. Otherwise a strong resume and well-answered screening questions matter more."),
        ],
    ),
    "Equity and stock options": dict(
        title="What Are Equity and Stock Options? How Startup Equity Works",
        aliases=["stock-options", "equity", "startup-equity", "employee-stock-options"],
        sections=[
            ("What equity means in a job offer", [
                "Equity is part ownership of the company given as part of your pay. It usually comes as stock options, the right to buy shares later at a fixed price, or as RSUs, shares given to you as they vest.",
                "Startups favour options because they have little cash; public companies more often give RSUs because their shares have a market price.",
            ]),
            ("How stock options work", [
                "Each option lets you buy one share at the strike price, which is set when the options are granted. If the shares later become worth more, the difference is your gain; if not, the options are worth nothing.",
                "Options vest over time, often over four years with a one-year cliff. Once they vest you must exercise them, that is pay the strike price, to own the shares, and after you leave you usually have only a limited window to do so.",
                "In a private company you usually cannot sell the shares until the company is sold, goes public or allows a sale, so the value can stay on paper for years.",
            ]),
            ("What to ask before you accept", [
                "The number of options or shares, the strike price, the latest valuation per share and the total number of shares outstanding, so you can work out your percentage.",
                "The vesting schedule, the cliff, the exercise window after you leave and what happens if the company is acquired.",
                "In the US, whether the options are ISOs or NSOs, since they are taxed differently. Then value the equity at zero when you compare offers and treat any payout as a bonus.",
            ]),
        ],
        qa=[
            ("Are stock options worth it?", "They can be worth a lot or nothing, depending on what the company is worth when you are able to sell. Compare offers on cash first and treat options as a possible upside, not as pay you can count on."),
            ("What is the difference between equity and stock options?", "Equity is ownership in general; stock options are one way to receive it, as the right to buy shares at a set price. RSUs and direct share grants are other forms."),
            ("What happens to my stock options if I leave the company?", "Unvested options are usually lost. Vested options normally have to be exercised within a set window after you leave, often a few months, or they expire; some companies give longer."),
            ("How do I know what percentage of the company I own?", "Divide your number of shares by the total fully diluted shares outstanding. Companies do not always volunteer that total, but it is a fair question to ask before you accept."),
        ],
    ),
    "Exempt and non-exempt": dict(
        title="Exempt vs Non-Exempt Employees: What It Means for Overtime",
        aliases=["exempt-employee", "non-exempt-employee", "exempt-vs-non-exempt"],
        sections=[
            ("What exempt and non-exempt mean", [
                "In the US, the Fair Labor Standards Act requires overtime at one and a half times the regular rate for hours over 40 in a workweek. Non-exempt employees are covered by that rule; exempt employees are not.",
                "Being paid a salary does not make you exempt by itself: a salaried employee can still be non-exempt and owed overtime.",
            ]),
            ("How a job becomes exempt", [
                "Most exemptions need three things: a fixed salary, a salary at or above the federal minimum ($684 a week under the rule in force in 2026), and duties that are mainly executive, administrative or professional.",
                "Some states set a higher salary floor or stricter duties tests, and the stricter rule applies. Some jobs, such as outside sales and certain computer roles, have their own rules.",
                "Job titles do not decide it; what you actually do does.",
            ]),
            ("What to check in an offer", [
                "Ask whether the role is exempt or non-exempt and how hours are tracked. If you are non-exempt, keep your own record of the hours you work.",
                "If a salaried job expects long weeks, work out your real hourly pay and compare it with a non-exempt role that pays overtime.",
            ]),
        ],
        qa=[
            ("Do exempt employees get paid overtime?", "Not under federal law. Some employers pay it anyway or give time off instead, and some states have their own overtime rules, so check your contract and your state."),
            ("Can a salaried employee be non-exempt?", "Yes. If the salary is below the threshold or the duties do not meet an exemption test, the employee is non-exempt and must be paid overtime, even though they are on a salary."),
            ("Is it better to be exempt or non-exempt?", "Exempt roles are usually more senior and more flexible, but long hours are unpaid. Non-exempt roles pay for every extra hour. Which is better depends on the hours the job really demands."),
            ("What is the salary threshold for exempt employees?", "Under the federal rule in force in 2026 it is $684 a week, or $35,568 a year, for most exemptions, with a higher threshold for highly paid employees. Several states, such as California, New York and Washington, set a higher floor."),
        ],
    ),
    "Garden leave": dict(
        title="What Is Garden Leave? Meaning, Pay and What You Can Do During It",
        aliases=["gardening-leave"],
        sections=[
            ("What garden leave means", [
                "Garden leave, or gardening leave, is when your employer keeps you on the payroll during your notice period but tells you not to work, not to come in and not to contact clients or colleagues.",
                "You are still employed: you get your normal salary and benefits, and you still owe your employer loyalty and confidentiality until your last day.",
                "It is common in the UK, in finance and in sales, and in other jobs where people leave for competitors with clients or sensitive information.",
            ]),
            ("Why employers use it", [
                "To keep you away from clients, deals and confidential information while your knowledge goes out of date, and to give your replacement time to take over your relationships.",
                "It works like a short, paid non-compete, and courts often look on it more kindly than on a non-compete that applies after you leave.",
            ]),
            ("What you can and cannot do", [
                "You usually cannot start a new job, work for yourself or help a competitor until garden leave ends, because you are still employed.",
                "You can usually look for jobs, rest, study and plan. Read your contract for a garden leave clause and any restrictions that run after it.",
                "Ask whether time on garden leave counts against any non-compete period that follows; it often does, and the contract may say so.",
            ]),
        ],
        qa=[
            ("Do you get paid on garden leave?", "Yes. You are still an employee, so you get your normal salary and usually your benefits until your employment ends."),
            ("Can I work for another company during garden leave?", "Usually not: you are still employed, and starting elsewhere would normally breach your contract. Ask your employer to agree an earlier release if you want to start sooner."),
            ("Can my employer put me on garden leave without a clause in my contract?", "In the UK, employers generally need a contractual right to stop you working; without one, garden leave can be challenged. Rules differ by country, so check your contract and local law."),
            ("What is the difference between garden leave and pay in lieu of notice?", "On garden leave you stay employed until the end of the notice period. With pay in lieu of notice your employment ends at once and you are paid for the notice period instead."),
        ],
    ),
    "Gross and net pay": dict(
        title="Gross vs Net Pay: What’s the Difference and How to Work It Out",
        aliases=["gross-pay", "net-pay", "take-home-pay"],
        sections=[
            ("Gross pay and net pay explained", [
                "Gross pay is what you earn before anything is taken off: your salary or hourly pay plus any overtime, bonus and commission for the period.",
                "Net pay, or take-home pay, is what reaches your bank account after income tax, social security and other deductions.",
                "Job postings, offers and salary surveys almost always quote gross pay, usually per year.",
            ]),
            ("What comes out of gross pay", [
                "Taxes: income tax and social security contributions, plus state or local taxes where they apply.",
                "Your share of benefits, such as health insurance premiums or pension contributions, and any other deductions you agreed to.",
                "Some deductions, like pre-tax retirement contributions, lower your taxable income, so your net pay falls by less than the amount you put in.",
            ]),
            ("How to estimate your take-home pay", [
                "Use your country’s official tax calculator or a payroll calculator with your gross salary, location and tax situation, then subtract benefit premiums.",
                "Check your first payslip line by line; mistakes in tax codes or benefit choices are common and easier to fix early.",
            ]),
        ],
        qa=[
            ("Is salary quoted gross or net?", "Almost always gross, before tax. A few countries and some industries quote net figures, so ask if a posting does not say."),
            ("How do I calculate net pay from gross?", "Subtract income tax, social security and your benefit and pension deductions from gross pay. A payroll calculator for your country does it in a minute."),
            ("Is gross income the same as taxable income?", "Not quite. Taxable income is gross income minus the deductions and allowances the tax rules let you subtract, such as some retirement contributions."),
            ("Why is my net pay lower than expected?", "Usually because of benefit premiums, pension contributions, a wrong tax code or withholding setting, or a bonus withheld at a higher rate. Your payslip lists each deduction."),
        ],
    ),
    "Hybrid": dict(
        title="What Is Hybrid Work? How Hybrid Jobs Work and What to Ask",
        aliases=["hybrid-work", "hybrid-job"],
        sections=[
            ("What hybrid work means", [
                "A hybrid job splits the week between the office and home. The split varies: a fixed number of office days, set days for the whole team, or office time only for meetings and events.",
                "Hybrid means you must live within commuting distance of an office, which is the main difference from a remote job.",
            ]),
            ("Common hybrid models", [
                "Fixed days: everyone is in on the same days, such as Tuesday to Thursday.",
                "Minimum days: a set number of office days a week or a month, chosen by you or your team.",
                "Office-first or remote-first: the office or home is the default, and the other is the exception.",
            ]),
            ("What to ask before you accept", [
                "How many days in the office, which days, and whether that is a firm rule that is checked or a guideline.",
                "Which office, how long the commute is, and whether the company pays for travel or for a home setup.",
                "Whether the policy has changed recently or is expected to; some companies have moved hybrid staff back to the office full-time.",
            ]),
        ],
        qa=[
            ("What is the difference between hybrid and remote work?", "Remote work needs no regular office visits; hybrid work needs you in an office on some days, so you must live near one."),
            ("How many days a week is hybrid?", "There is no standard: each employer sets its own policy, from one day a month to most of the week. Always ask for the exact number and whether it is enforced."),
            ("Can I negotiate a hybrid schedule?", "Often, before you accept. Ask for fewer office days or specific days in writing, especially if you have a long commute or caring duties."),
            ("Are hybrid jobs better than remote jobs?", "It depends on you: hybrid gives in-person time for learning and relationships, remote saves commuting and widens where you can live. Many people decide by the commute."),
        ],
    ),
    "Job offer": dict(
        title="What Is a Job Offer? What an Offer Letter Includes and What to Check",
        aliases=["offer-letter", "job-offer-letter"],
        sections=[
            ("What a job offer includes", [
                "A job offer is the employer’s formal proposal to hire you. It is often made first by phone, then in an offer letter you sign.",
                "A complete offer letter names the job title, the manager or team, the start date, base salary and how often it is paid, bonus, equity, benefits, location or remote terms, and whether the job is full-time, part-time or fixed-term.",
                "It may also list conditions, such as a background check, references or proof of work authorization, and refer to other documents you must sign, like a confidentiality or non-compete agreement.",
            ]),
            ("How offers work", [
                "A verbal offer is a promise to send a written one. Do not resign until you have the written offer and its conditions are cleared.",
                "Most offers come with a deadline. You can ask for more time, and you can negotiate before you sign; asking politely rarely gets an offer withdrawn.",
                "In the US, most offer letters say employment is at-will, which means the employer can end it, and in some cases withdraw the offer, even after you accept.",
            ]),
            ("What to check before you sign", [
                "That every number agreed on the phone is in the letter, including bonus terms, equity details and any sign-on bonus with its repayment rules.",
                "The start date, notice period, probation period and any restrictive clauses, such as a non-compete or non-solicit.",
                "Ask your questions in writing, and keep a copy of the signed letter and everything it refers to.",
            ]),
        ],
        qa=[
            ("What is the difference between a job offer and an offer letter?", "The offer is the proposal itself, which can be made by phone; the offer letter is the written version with the terms. Only the written version gives you something to rely on."),
            ("Can a job offer be withdrawn after I accept?", "Yes, it can happen, especially if a condition such as a background check fails or the company cuts its budget. That is why you should not resign until the conditions are cleared and the start date is fixed."),
            ("How long do I have to accept a job offer?", "Usually a few days to a week, but it varies. If you need more time, ask for a specific date and give a reason, such as waiting for another process to finish."),
            ("Should I negotiate a job offer?", "Usually yes, as long as you are polite and specific. Ask for one or two changes backed by market data, and be ready to accept if they are met."),
        ],
    ),
    "Non-compete": dict(
        title="What Is a Non-Compete Agreement? Is It Enforceable?",
        aliases=["non-compete-agreement", "noncompete", "non-compete-clause"],
        sections=[
            ("What a non-compete is", [
                "A non-compete is a clause in an employment contract, or a separate agreement, that stops you from working for a competitor or starting a competing business for a time after you leave, usually within an area or a market.",
                "It is different from a non-solicit clause, which stops you from approaching the employer’s clients or staff, and from a confidentiality clause, which protects its information. Those two are enforced far more often.",
            ]),
            ("Are non-competes enforceable?", [
                "In the US it depends on the state. California, Minnesota, North Dakota and Oklahoma ban almost all employee non-competes; many other states enforce them only if they are reasonable in time, place and scope, and some only above a salary threshold.",
                "A federal rule that would have banned most non-competes was set aside by a court in 2024 and later withdrawn, so state law decides. Federal regulators still challenge especially broad ones case by case.",
                "Outside the US the rules differ: in many countries a non-compete must be limited and reasonable, and some require the employer to pay you during the restricted period.",
            ]),
            ("What to do about one", [
                "Read it before you sign the offer: note how long it lasts, where it applies, which companies or roles it covers and whether it still applies if you are laid off.",
                "Ask to narrow it, for example to named competitors or a shorter period, or to drop it for junior roles; employers often agree.",
                "If you are already bound by one and have a new offer, tell the new employer and get advice from an employment lawyer where you work before you resign.",
            ]),
        ],
        qa=[
            ("Are non-competes legal?", "In most US states they are legal but enforced only if reasonable; in California, Minnesota, North Dakota and Oklahoma they are void for almost all employees. Other countries set their own limits."),
            ("Can I be sued for breaking a non-compete?", "Yes, an employer can sue, usually to stop you working for the competitor and sometimes for damages. Whether it wins depends on the clause and the law where you work."),
            ("How long does a non-compete last?", "Commonly six months to two years after you leave. Courts are less likely to enforce long or broad ones."),
            ("Does a non-compete apply if I get laid off?", "It depends on the clause and the law. Some states limit enforcement against people dismissed without cause, so read the wording and check local law."),
        ],
    ),
    "Notice period": dict(
        title="What Is a Notice Period? How Long It Is and How It Works",
        aliases=[],
        sections=[
            ("What a notice period is", [
                "A notice period is the time between saying you are leaving and your last day of work. It applies both ways: the notice you must give when you resign, and the notice the employer must give if it ends your job.",
                "Its length is set by your contract, the law where you work or local custom; where the law sets a minimum, a contract cannot go below it.",
            ]),
            ("How long notice periods usually are", [
                "In the US most jobs are at-will and no notice is legally required, but two weeks is the custom.",
                "In the UK, the legal minimum an employee must give after a month in the job is one week, but contracts often say one or three months. Many European countries set notice periods by law that grow with years of service.",
                "Senior and client-facing roles often have longer notice periods, sometimes spent on garden leave.",
            ]),
            ("What happens during your notice", [
                "You keep working and getting paid as normal, hand over your work, and use up or are paid for remaining leave as your contract says.",
                "Your employer may let you go early, put you on garden leave or pay you in lieu of notice. You can ask to leave early, but it does not have to agree.",
                "Give notice in writing and state your last day as a date, so nobody has to count.",
            ]),
        ],
        qa=[
            ("Can I leave before my notice period ends?", "Only if your employer agrees, unless you are in an at-will US job. Leaving early without agreement can breach your contract and may cost you pay, a payout for unused leave or a good reference."),
            ("Do I get paid during my notice period?", "Yes, you are still employed and paid as normal, including while on garden leave."),
            ("Does the notice period include weekends?", "Usually yes: notice runs in calendar days, weeks or months from the day you give it, unless your contract says working days."),
            ("Can I take holiday during my notice period?", "Often yes, with your employer’s agreement; some employers ask you to use remaining leave, others pay it out at the end."),
        ],
    ),
    "OTE (on-target earnings)": dict(
        title="What Does OTE Mean? On-Target Earnings in Sales Jobs Explained",
        aliases=["on-target-earnings"],
        sections=[
            ("What OTE means", [
                "OTE stands for on-target earnings: your base salary plus the commission or bonus you earn if you hit exactly 100% of your sales target for the year.",
                "It is the number most sales job ads lead with, but only the base part is guaranteed. If you sell less than target you earn less than OTE; if you sell more, you may earn more.",
            ]),
            ("How OTE is split", [
                "The split between base and variable pay is often written as a ratio, such as 50/50 or 70/30. A $100,000 OTE on a 60/40 split means a $60,000 base and $40,000 of variable pay at target.",
                "Roles that close deals usually carry more variable pay; roles that support sales usually have more base.",
                "Commission can be capped, so you cannot earn above a ceiling, or uncapped. Accelerators pay a higher rate once you pass your target.",
            ]),
            ("What to ask about an OTE", [
                "What share of the team hit target last year, and what a typical rep actually earned.",
                "How the quota is set, when commission is paid, whether there is a ramp-up period for new starters and whether part of the variable pay is guaranteed during it.",
                "What happens to commission on deals that close after you leave.",
            ]),
        ],
        qa=[
            ("Is OTE guaranteed?", "No. Only the base salary is guaranteed; the rest depends on hitting your target. Some companies guarantee part of the commission for the first few months while you build a pipeline."),
            ("Does OTE include base salary?", "Yes. OTE is base salary plus target commission or bonus, so a job listed at $120,000 OTE pays less than that in base."),
            ("What is a good OTE split?", "There is no single right split; it depends on the role and how much you control the sale. What matters more is whether the target is realistic, so ask how many people reach it."),
            ("What does “uncapped OTE” mean?", "It usually means commission is uncapped: there is no ceiling on what you can earn above target. OTE itself is still the figure at 100% of target."),
        ],
    ),
    "Probation period": dict(
        title="What Is a Probation Period at a New Job? Rules and How to Pass",
        aliases=["probation", "probationary-period"],
        sections=[
            ("What a probation period is", [
                "A probation period is a trial at the start of a job, often three to six months, when the employer checks that you fit the role and you check that the job fits you.",
                "During probation, notice periods are usually shorter on both sides, and some benefits, bonuses or paid leave may start only once it ends.",
                "Whether there is a probation, how long it lasts and what it changes are set by your contract and the law where you work.",
            ]),
            ("Your rights during probation", [
                "You can be let go more easily during probation, but not for an illegal reason such as discrimination, pregnancy or reporting wrongdoing.",
                "In the US most jobs are at-will anyway, so probation mainly affects benefits and reviews. In countries where dismissal needs a reason or long notice, probation is when those rules are lighter.",
                "Employers can often extend probation if the contract allows it; ask for the reasons and the goals in writing.",
            ]),
            ("How to pass probation", [
                "In your first week, ask your manager what success looks like at the end of probation, and agree two or three concrete goals.",
                "Ask for feedback every few weeks rather than waiting for the final review, and fix small problems early.",
                "Keep a short record of what you delivered, so the review is based on facts.",
            ]),
        ],
        qa=[
            ("Can you be fired during a probation period?", "Yes, usually with short notice and without the process that applies later. It is still unlawful to dismiss you for a discriminatory or retaliatory reason."),
            ("How long is a probation period?", "Commonly three to six months, sometimes longer for senior roles, and some countries set a legal maximum. Your contract states the exact length."),
            ("Can I quit during probation?", "Yes. Notice during probation is usually short, often a week or whatever the contract says, and in at-will US jobs none is legally required."),
            ("Do you get benefits during probation?", "It depends on the employer: some benefits start on day one, others after a waiting period. Check the benefits summary for start dates."),
        ],
    ),
    "Recruiter": dict(
        title="What Is a Recruiter? What Recruiters Do and How to Work With One",
        aliases=["in-house-recruiter", "agency-recruiter"],
        sections=[
            ("What a recruiter does", [
                "A recruiter finds, screens and guides candidates through hiring for an employer. They post the job, search for people, run the first call, schedule interviews, collect feedback and usually deliver the offer.",
                "The recruiter runs the process; the hiring manager, who will be your boss, usually decides who gets the job.",
            ]),
            ("Types of recruiters", [
                "In-house or corporate recruiters work for the employer, often in a team called talent acquisition, and hire only for that company.",
                "Agency recruiters work for a recruitment firm and are paid by the employer when one of their candidates is hired, often a share of the first-year salary. You should never pay a recruiter to find you a job.",
                "Headhunters and executive search firms are agency recruiters who approach people for senior or hard-to-fill roles. Sourcers find and contact candidates before they apply.",
            ]),
            ("How to work with a recruiter", [
                "Be clear about what you want: role, level, location, pay range and timing. A recruiter can only match you to what you tell them.",
                "Ask the recruiter about the team, the interview steps, the pay range and the timeline; answering is part of their job.",
                "Ask an agency recruiter to name the employer before sending your resume, so you are not put forward twice to the same company.",
            ]),
        ],
        qa=[
            ("Do recruiters charge job seekers?", "Legitimate recruiters do not; the employer pays them. Anyone asking you for money to get a job is a red flag."),
            ("What is the difference between a recruiter and a hiring manager?", "The recruiter manages the hiring process and screens candidates; the hiring manager is the future boss who makes the final decision."),
            ("Should I tell a recruiter my salary expectations?", "Give a researched range for the role rather than your current pay, and ask for the employer’s range first. A number of US states and cities require employers to share a pay range."),
            ("How do I get recruiters to contact me?", "Keep your LinkedIn or other public profile current with your exact job title, skills and location, and use the setting that tells recruiters you are open to work."),
        ],
    ),
    "Reference": dict(
        title="What Is a Job Reference? Reference Checks and Who to Ask",
        aliases=["reference-check", "job-reference", "references"],
        sections=[
            ("What a reference is", [
                "A reference is a person, usually a former manager or colleague, who confirms your work to a new employer. A reference check is the call, email or online form in which the employer asks them about you.",
                "Reference checks usually come near the end, after the final interview and before or just after an offer, which is why many offers are conditional on them.",
            ]),
            ("What employers ask", [
                "How the referee knows you and for how long, what you did, your strengths, what you could improve and whether they would hire or work with you again.",
                "Many HR departments will only confirm your title and dates; the personal view comes from the managers and colleagues you name.",
            ]),
            ("How to choose and prepare references", [
                "Pick two or three people who saw your work closely and recently, ideally including a manager, and ask them before you give their names.",
                "Send each one the job description and remind them of the projects they saw, so their answers fit the role.",
                "You do not have to name your current manager; most employers accept a former manager or a senior colleague until you have an offer.",
                "Leave “references available on request” off your resume: it takes space and is assumed.",
            ]),
        ],
        qa=[
            ("Who should I use as a reference?", "Former managers first, then senior colleagues or clients who saw your work closely. Friends and family do not count."),
            ("What can a former employer say about you?", "In many places anything that is true, but many companies limit official references to dates and title for legal reasons. Managers you name may speak more freely."),
            ("Do employers always check references?", "Not always, but many do before a final offer, especially for senior roles. Prepare your references as if they will be called."),
            ("What happens if a reference is bad?", "The employer may not make an offer or may withdraw one. Choose people you trust and ask them directly whether they can give you a positive reference."),
        ],
    ),
    "Referral": dict(
        title="What Is a Job Referral? How Employee Referrals Work and How to Ask",
        aliases=["employee-referral", "job-referral"],
        sections=[
            ("What a referral is", [
                "A referral is when someone who works at a company recommends you for a job there, usually by submitting your resume through the company’s hiring system with their name attached.",
                "Employers like referrals because a current employee is vouching for you, and many pay the employee a referral bonus if you are hired.",
            ]),
            ("Why referrals help", [
                "A referred application usually reaches a recruiter quickly instead of waiting in the pile, and comes with someone the company already trusts who can answer questions about you.",
                "A referral does not guarantee an interview or an offer; you still go through the same interviews as everyone else.",
            ]),
            ("How to ask for a referral", [
                "Start with people who know your work: former colleagues, classmates, people from communities you take part in. A stranger’s referral counts for less.",
                "Send a short message with the exact job link, two lines on why you fit and your resume, so the person can submit you in a few minutes.",
                "Ask whether they would be comfortable referring you, thank them either way and tell them how it went.",
            ]),
        ],
        qa=[
            ("Does a referral guarantee a job?", "No. It usually gets your application read sooner, but you still have to pass the same interviews."),
            ("How do I ask someone for a referral?", "Send a short, specific message: the job link, two sentences on why you fit, and your resume. Make it easy to say yes and easy to say no."),
            ("Can I ask a stranger on LinkedIn for a referral?", "You can, but start with a question about their team or the role rather than the referral itself; people refer those they have at least spoken to."),
            ("What is an employee referral bonus?", "Money a company pays an employee when someone they referred is hired and stays for a set time. It goes to the employee, not to you."),
        ],
    ),
    "Remote": dict(
        title="What Is a Remote Job? Meaning, Types and How to Find Real Ones",
        aliases=["remote-work", "remote-job", "work-from-home"],
        sections=[
            ("What a remote job is", [
                "A remote job is one you do away from the employer’s office, usually from home, with no regular office attendance required.",
                "Remote does not mean work from anywhere: most remote jobs are limited to certain countries, states or time zones because of tax, payroll and employment law, and many set core hours for meetings.",
            ]),
            ("Types of remote jobs", [
                "Remote within one country: you must live in that country and have the right to work there.",
                "Remote within a region or a range of time zones, such as Europe or the Americas, so working hours overlap.",
                "Work from anywhere: the posting names no country at all; these are the rarest.",
                "Remote-first or remote-friendly: remote-first companies run everything online, while remote-friendly ones allow it but the office stays the centre.",
            ]),
            ("How to find and get a remote job", [
                "Filter by the countries or time zones you can actually work from, and read each posting’s location line before you apply.",
                "Show you can work without supervision: clear writing, measurable results and experience with remote tools.",
                "Be wary of remote jobs that ask for money, payment for equipment or personal documents before a real interview; these are common scam patterns.",
            ]),
        ],
        qa=[
            ("What does remote mean in a job posting?", "That the work can be done away from the office, usually from home. Check the location line for the countries, states or time zones you must be in."),
            ("Can I work a remote job from another country?", "Only if the employer allows that country. Working from a country you were not hired in can create tax and legal problems for you and the employer, so ask before you move."),
            ("Are remote jobs paid less?", "Some employers adjust pay to where you live; others pay one rate for everyone. Ask whether pay is location-based before you negotiate."),
            ("How do I spot a fake remote job?", "Warning signs are interviews only by chat, an offer without a real interview, requests to buy equipment or pay fees, and a recruiter using a free email address. Apply on the employer’s own website."),
        ],
    ),
    "Salary range": dict(
        title="What Is a Salary Range? How to Read One in a Job Posting",
        aliases=["pay-range"],
        sections=[
            ("What a salary range is", [
                "A salary range is the lowest and highest base pay the employer says it may offer for the job, usually per year and before tax.",
                "It often comes from the company’s salary band for that level. Where you land depends on your experience, skills and location, and sometimes on how hard the role is to fill.",
                "A number of US states and cities require employers to state a range in postings, and the EU pay transparency directive requires employers to give candidates pay information before the interview.",
            ]),
            ("How to read a salary range", [
                "Most offers land around the middle unless you clearly exceed the requirements; the top is usually for people who could almost do the next level.",
                "A very wide range often covers more than one level or more than one location. Ask which level and location the role is tied to.",
                "Check whether the range is base only or includes bonus or commission (OTE), and whether equity comes on top.",
            ]),
            ("How to use it to negotiate", [
                "Compare the range with market data for the same title, level and location, then aim for the point your experience justifies, not simply the top.",
                "When asked for your expectations, you can say the posted range works for you and that you expect to be in its upper part because of specific skills or results.",
            ]),
        ],
        qa=[
            ("Should I ask for the top of the salary range?", "Only if you meet every requirement and bring something extra; otherwise aim a little above the middle and explain why. Asking above the top rarely works unless you fit a higher level."),
            ("Is the salary range before or after tax?", "Before tax. It is gross pay, usually base salary per year."),
            ("Why are some salary ranges so wide?", "Because one posting covers several levels or locations, or the employer wants room to negotiate. Ask the recruiter what the range is for your level."),
            ("Can you negotiate above the salary range?", "It is possible but uncommon; going above the band usually means hiring you at a higher level. If base is capped, negotiate a sign-on bonus or more equity instead."),
        ],
    ),
    "Severance": dict(
        title="What Is Severance Pay? Who Gets It and How to Negotiate It",
        aliases=["severance-pay", "severance-package"],
        sections=[
            ("What severance is", [
                "Severance is pay, and sometimes other help, that an employer gives when it ends your job, typically in a layoff, a restructuring or a negotiated exit.",
                "A severance package can include weeks of pay, continued health insurance, payment for unused leave, a pro-rated bonus, extra time to exercise stock options, outplacement help and an agreed reference.",
            ]),
            ("Who gets severance and how much", [
                "In the US no federal law requires severance; it comes from your contract, company policy or a union agreement, or is offered in exchange for a release of claims.",
                "For many mass layoffs, the US WARN Act requires 60 days’ notice, and an employer that skips it can owe pay for that period. Many other countries set a legal minimum redundancy payment based on years of service.",
                "A common formula is a number of weeks of pay for each year worked, often with a minimum; ask for the policy in writing.",
            ]),
            ("Before you sign a severance agreement", [
                "Most agreements ask you to give up the right to sue. Read what you are waiving, any non-compete, non-disparagement or confidentiality terms, and the deadline to sign.",
                "In the US, workers aged 40 or over must be given time to consider an agreement that waives age discrimination claims, and a period to change their mind after signing.",
                "You can negotiate: ask for more weeks, continued health cover, the bonus you were on track for or faster vesting, and consider a lawyer’s review when the amount is large.",
            ]),
        ],
        qa=[
            ("Is severance pay required by law?", "Not in the US in general; it depends on your contract or company policy. Many other countries require a statutory redundancy payment."),
            ("How is severance calculated?", "Usually by years of service, such as a set number of weeks of pay per year worked, sometimes with a minimum and a cap. Your employer’s policy or your contract sets the formula."),
            ("Can I negotiate my severance package?", "Often yes, especially when you are asked to sign a release. Ask in writing, be specific, and point to your length of service, any bonus or vesting you are about to lose, and how long a job search in your field takes."),
            ("Do you get severance if you quit?", "Usually not. Severance is normally paid when the employer ends the job, not when you resign."),
            ("Is severance taxable?", "Yes, in most countries it is taxed as income, though some exempt part of a redundancy payment. Check your local rules."),
        ],
    ),
    "Sign-on bonus": dict(
        title="What Is a Sign-On Bonus? How It Works and When You Repay It",
        aliases=["signing-bonus", "joining-bonus"],
        sections=[
            ("What a sign-on bonus is", [
                "A sign-on bonus, or signing bonus, is a one-time payment for accepting a job. Employers use it to win a candidate, to make up for a bonus or equity you lose by leaving, or to close a gap when base salary cannot move.",
                "It is paid once, often with the first or second paycheck, or split into parts paid over the first year.",
            ]),
            ("Repayment and taxes", [
                "Most sign-on bonuses come with a clawback: if you leave within a set time, often a year, you must repay all or part of it. Read the exact terms before you sign.",
                "It is taxed as income, so the amount you receive is lower than the figure in the offer.",
            ]),
            ("How to ask for one", [
                "Ask when the employer cannot raise base salary, or when you leave behind a bonus, unvested equity or a retention payment; name the amount and what it replaces.",
                "Ask for repayment to be pro-rated by months worked, and for no repayment if the company lets you go.",
            ]),
        ],
        qa=[
            ("Do you have to pay back a sign-on bonus?", "Only if your agreement says so and you leave before the set period ends, which is a common condition. Check whether repayment is full or pro-rated and whether it applies if you are laid off."),
            ("When is a sign-on bonus paid?", "Usually in your first paycheck or within the first month or two; some are split into instalments."),
            ("How is a sign-on bonus taxed?", "As income, like any bonus. In the US it is often withheld at the flat supplemental rate, so the payment arrives smaller than the gross figure."),
            ("Can I negotiate a sign-on bonus?", "Yes, it is one of the easier things to negotiate because it is a one-time cost for the employer. It works best when tied to something specific you give up by leaving."),
        ],
    ),
    "STAR method": dict(
        title="What Is the STAR Method? How to Answer Interview Questions",
        aliases=["star-interview-method", "star-technique"],
        sections=[
            ("What the STAR method is", [
                "STAR is a way to answer behavioral interview questions, the ones that start with “Tell me about a time when…”. It stands for Situation, Task, Action, Result.",
                "Situation: where and when, in one or two sentences. Task: what you were responsible for. Action: what you did, step by step. Result: what changed, with a number if you have one, and what you learned.",
                "Spend most of the time on Action and Result; the setup only needs to be clear enough to follow.",
            ]),
            ("How to prepare STAR answers", [
                "Read the job description and list the skills it stresses, such as leading, handling conflict, solving problems or meeting deadlines.",
                "Write six to eight stories from your work that show those skills, including one failure and one disagreement. One good story can answer several questions.",
                "Say “I”, not “we”, in the Action part: the interviewer is assessing what you did.",
                "Practise each answer out loud until it takes about two minutes.",
            ]),
            ("Mistakes to avoid", [
                "Spending a minute on background and running out of time before the result.",
                "Answering with what you would do instead of what you did; the question asks for a real example.",
                "Ending without a result. If the outcome was bad, say what you learned and what you do differently now.",
            ]),
        ],
        qa=[
            ("What is an example of a STAR answer?", "“Our release was two weeks late (Situation). I had to get it out before a client launch (Task). I cut the scope to the three features the client needed, moved two engineers to testing and set a daily check-in (Action). We shipped on time and the client renewed (Result).”"),
            ("How long should a STAR answer be?", "About one to two minutes. If the interviewer wants more detail, they will ask."),
            ("What questions use the STAR method?", "Any question about past behaviour: “Tell me about a time…”, “Give an example of…”, “Describe a situation where…”. It also works for “What is your greatest achievement?”."),
            ("What if I don’t have work experience for a STAR answer?", "Use your studies, volunteering, a part-time job or a personal project. The format works the same way; what matters is that you acted and got a result."),
        ],
    ),
    "Total compensation": dict(
        title="What Is Total Compensation? How to Calculate Your Total Pay",
        aliases=["total-comp"],
        sections=[
            ("What total compensation includes", [
                "Total compensation is everything a job pays you in a year, not just salary: base salary, bonus or commission, equity and the value of benefits.",
                "Benefits include the employer’s share of health insurance, retirement contributions, paid time off and smaller items such as a learning budget or a home office stipend.",
                "Some employers send a yearly total rewards statement that puts a value on each part.",
            ]),
            ("How to calculate it", [
                "Start with base salary. Add the bonus you are likely to get, based on what was actually paid in recent years, not the maximum.",
                "Add equity per year: for RSUs at a public company, the grant value divided by the years it vests over; for options at a private company, note it separately and treat it as uncertain.",
                "Add the employer’s retirement contributions and health premiums, and spread one-time payments such as a sign-on bonus over the years you expect to stay.",
            ]),
            ("Using it to compare offers", [
                "Compare offers on total compensation, but weight each part by how certain it is: base is certain, a bonus is likely, private-company equity is a lottery ticket.",
                "Look at the second year and later too: sign-on bonuses end, new equity grants vary, and raises are a percentage of base.",
            ]),
        ],
        qa=[
            ("Does total compensation include benefits?", "In most definitions yes, it includes the value of benefits such as health insurance and retirement contributions, though some salary sites count only salary, bonus and equity."),
            ("What is the difference between salary and total compensation?", "Salary is the fixed pay. Total compensation adds everything else the job pays: bonus, commission, equity and benefits."),
            ("Is total compensation before taxes?", "Yes, it is quoted before tax, like salary."),
            ("What does TC mean in job offers?", "TC is short for total compensation, used especially in tech for base salary plus bonus plus equity per year."),
        ],
    ),
    "Contract-to-hire": dict(
        title="What Is Contract-to-Hire? How It Works and Is It Worth It",
        aliases=["temp-to-hire", "contract-to-perm"],
        sections=[
            ("What contract-to-hire means", [
                "A contract-to-hire job starts as a contract for a set period, often a few months, and may turn into a permanent job if both sides want it.",
                "During the contract you are usually employed by a staffing agency or work as a contractor, so you may not get the company’s benefits, and the company can end it more easily than a permanent job.",
            ]),
            ("Why employers use it and what it means for you", [
                "Employers use it to try a person in the real job, to hire quickly, or when the budget for a permanent role is not yet approved.",
                "For you, it is a way into a company and a chance to judge the team before committing; the risk is that the conversion never comes.",
            ]),
            ("What to ask before you accept", [
                "How many contract-to-hire people in this team were made permanent, and what decides it.",
                "The contract length, the expected permanent salary and benefits, and whether the permanent offer is negotiable.",
                "Who your legal employer is during the contract, and whether an agency fee or clause affects your joining the company directly.",
            ]),
        ],
        qa=[
            ("Is contract-to-hire a good idea?", "It can be, if you need a way into a company or a field and the contract pay is fair for the risk. Treat conversion as a possibility, not a promise, and keep looking if it stalls."),
            ("Do contract-to-hire employees get benefits?", "Sometimes from the staffing agency, rarely from the client company until you convert. Ask for the agency’s benefits in writing."),
            ("How long is a contract-to-hire period?", "Often a few months, commonly three to six, but it varies; the contract states the length."),
            ("Can I negotiate salary when converting to full-time?", "Yes. Your work during the contract is your strongest argument, and the permanent offer is a new offer like any other."),
        ],
    ),
    "Employer of record": dict(
        title="What Is an Employer of Record (EOR)? What It Means for Workers",
        aliases=["eor"],
        sections=[
            ("What an employer of record is", [
                "An employer of record, or EOR, is a company that legally employs you on behalf of another company. The other company directs your daily work; the EOR signs your employment contract, runs payroll, withholds taxes and provides the benefits required where you live.",
                "Companies use an EOR to hire in a country where they have no local company of their own, which is common for remote jobs across borders.",
            ]),
            ("EOR vs PEO vs contractor", [
                "An EOR is the only legal employer. A professional employer organization, or PEO, shares employer duties with a company that already has its own entity in the country, mainly in the US.",
                "Being hired through an EOR makes you an employee with local rights and benefits, which an independent contractor does not get.",
            ]),
            ("What to check if you are hired through an EOR", [
                "Which company is named on your contract, which country’s law governs it, and who you contact about pay, leave and benefits.",
                "That your salary, notice period, paid leave and any equity in the client company are written down; the EOR’s standard contract may not mention equity.",
                "What happens if the client company ends its contract with the EOR, and what notice and severance local law then gives you.",
            ]),
        ],
        qa=[
            ("Is an EOR my real employer?", "Legally, yes: the EOR is your employer on paper and is responsible for your contract, pay and local rights. The client company decides your work and, in practice, whether you keep the job."),
            ("What is the difference between an EOR and a PEO?", "An EOR is the only legal employer and lets a company hire where it has no entity; a PEO co-employs staff with a company that already has one."),
            ("Is it better to be hired through an EOR or as a contractor?", "For most people an EOR is safer: you get an employment contract, benefits and protection under local law. Contracting can pay more per day but leaves taxes, insurance and gaps to you."),
            ("Can I get stock options through an EOR?", "Usually yes, but the options come from the client company under its own plan, not from the EOR. Ask for the grant in writing separately from the EOR contract."),
        ],
    ),
    "Headhunter": dict(
        title="What Is a Headhunter? Headhunter vs Recruiter Explained",
        aliases=["executive-recruiter", "head-hunter"],
        sections=[
            ("What a headhunter does", [
                "A headhunter is a recruiter, usually from an outside firm, who looks for people to fill a specific role, often senior or hard to fill, and approaches them directly, even if they are not looking for a job.",
                "The employer pays the headhunter: a fee when the hire is made, often a share of first-year pay, or a retainer paid in stages for senior searches. The candidate never pays.",
            ]),
            ("Headhunter vs recruiter", [
                "Every headhunter is a recruiter, but not every recruiter is a headhunter. In-house recruiters hire for their own company and fill many roles from people who apply.",
                "Headhunters work for several client companies, focus on a few roles at a time and spend most of their effort approaching people who did not apply.",
            ]),
            ("How to work with headhunters", [
                "Make yourself easy to find: a current public profile with your exact title, industry and results.",
                "When one calls, ask which company, the role’s level and pay range, and why they think you fit, and ask them to check with you before sending your resume anywhere.",
                "Be honest about what you want; a headhunter who understands you will call again for the next role.",
            ]),
        ],
        qa=[
            ("How do headhunters get paid?", "By the employer, usually a percentage of the hire’s first-year salary or a retainer. A headhunter who asks you for money is not a real headhunter."),
            ("How do I get noticed by headhunters?", "Keep your public profile current, be visible in your field and stay in touch with recruiters who specialise in it. A clear track record in a well-defined role is what they search for."),
            ("Should I respond to a headhunter even if I’m happy in my job?", "Usually yes: a short call costs little and tells you what the market pays. You can always say no to the role."),
            ("Is a headhunter the same as a recruitment agency?", "Close: a recruitment agency may fill many roles from a database of applicants, while a headhunter or executive search firm approaches specific people for specific, often senior, roles."),
        ],
    ),
    "Vesting": dict(
        title="What Is Vesting? Vesting Schedules and Cliffs Explained",
        aliases=["vesting-schedule"],
        sections=[
            ("What vesting means", [
                "Vesting is how something promised to you, such as stock options, RSUs or the employer’s retirement contributions, becomes fully yours over time. Until it vests, you lose it if you leave.",
                "A vesting schedule says how much vests and when. A common one for startup equity is four years with a one-year cliff.",
            ]),
            ("How a cliff and monthly vesting work", [
                "With a one-year cliff, nothing vests in your first year; on your first anniversary a quarter of the grant vests at once. After that the rest usually vests monthly or quarterly until the end of year four.",
                "If you leave before the cliff, you get nothing from the grant. If you leave after two years of a four-year schedule, about half is yours and the rest is lost.",
                "Some grants vest unevenly, with more in later years, and some companies give new grants every year so that equity keeps vesting.",
            ]),
            ("What to check", [
                "The vesting start date, the cliff, how often it vests and whether vesting speeds up if the company is sold and you lose your job, known as acceleration.",
                "For options, how long you have to exercise vested options after you leave; for retirement plans, how long until the employer’s contributions are fully yours.",
            ]),
        ],
        qa=[
            ("What does fully vested mean?", "That everything in the grant, or all the employer’s contributions, is now yours and stays yours if you leave."),
            ("What is a vesting cliff?", "A period at the start, often one year, during which nothing vests. When it ends, the vesting for that whole period happens at once."),
            ("What happens to unvested shares when I quit?", "They are usually forfeited and go back to the company. Vested options usually have to be exercised within a set window."),
            ("What is single-trigger and double-trigger acceleration?", "Single-trigger means unvested equity vests early when the company is sold. Double-trigger means it vests early only if the company is sold and you also lose your job or your role is cut."),
        ],
    ),
    "Visa sponsorship": dict(
        title="What Is Visa Sponsorship? How Employer Sponsorship Works",
        aliases=["work-visa-sponsorship", "sponsorship"],
        sections=[
            ("What visa sponsorship means", [
                "Visa sponsorship means an employer supports your application for the permit you need to work in its country: it files or backs the paperwork, shows that the job meets the rules and usually pays most of the employer-side costs.",
                "Each country has its own system. In the US, work visas such as the H-1B are filed by the employer; in the UK, an employer needs a sponsor licence to hire on a Skilled Worker visa; many other countries have similar employer-led routes.",
            ]),
            ("What sponsorship involves", [
                "The job usually has to meet a skill level and a minimum salary, and the employer may have to show it pays the going rate for the role.",
                "It takes time and money, which is why many employers say they cannot sponsor, or sponsor only for hard-to-fill roles.",
                "Your permission to stay is often tied to that employer, so changing jobs can mean a new application.",
            ]),
            ("How to find sponsored jobs", [
                "Filter for jobs that mention visa sponsorship, and check which employers have sponsored before; the US and UK governments publish data on sponsoring employers.",
                "Say up front, in the application or the first call, what work status you have and what you would need, so neither side wastes time.",
                "Ask who pays the legal and government fees and whether the employer will support permanent residence later.",
            ]),
        ],
        qa=[
            ("What does “will not sponsor” mean in a job posting?", "That the employer will only hire people who already have the right to work in that country without its help."),
            ("Do I have to pay for my visa sponsorship?", "It depends on the country. Employers usually pay most costs, and in some programmes the law requires the employer to pay certain fees; ask and get it in writing."),
            ("How do I find companies that sponsor visas?", "Use job filters for sponsorship, check government lists of licensed or past sponsors, and target larger employers in fields that are short of skilled people."),
            ("Can I change jobs on a sponsored visa?", "Usually yes, but the new employer often has to sponsor you again or file a transfer before you start. Do not resign until the new paperwork is accepted."),
        ],
    ),
    "Two weeks notice": dict(
        title="What Is Two Weeks Notice? Is It Required and How to Give It",
        aliases=["2-weeks-notice"],
        sections=[
            ("What two weeks notice means", [
                "Giving two weeks notice means telling your employer you are resigning and that your last day will be two weeks later.",
                "In the US it is a custom, not a legal requirement, for most at-will jobs. If your contract or company policy sets a different period, that applies instead.",
                "In many other countries notice periods are set by contract and law and are often longer, such as one or three months.",
            ]),
            ("How to give two weeks notice", [
                "Tell your manager first, in person or on a call, then send a short written resignation that states your last working day as a date.",
                "Offer a handover plan and keep working normally until your last day.",
                "Keep the letter short and positive: you do not have to explain why you are leaving.",
            ]),
            ("What can happen during the notice", [
                "Your employer may accept the notice and ask you to leave at once. In an at-will job it may not have to pay you for the two weeks unless its policy or your contract says otherwise.",
                "You may get a counteroffer; decide beforehand whether anything would change your mind.",
            ]),
        ],
        qa=[
            ("Is two weeks notice required by law?", "Not in most US jobs: at-will employment lets you leave at any time. Your contract, a union agreement or company policy can still require it, and some policies tie the payout of unused PTO to giving notice."),
            ("Can my employer fire me after I give two weeks notice?", "In an at-will job, yes, it can end your employment right away. Some employers pay the two weeks anyway; have some savings in case yours does not."),
            ("Do I have to work my two weeks notice?", "Not legally in most US jobs, but leaving without it can cost you a reference and the chance to be rehired. Outside the US, your contractual notice is usually binding."),
            ("Is two weeks notice 10 working days?", "Usually it means two calendar weeks, which for a Monday-to-Friday job is about ten working days. State your exact last day in the letter to avoid confusion."),
        ],
    ),
    "RSU (restricted stock units)": dict(
        title="What Are RSUs (Restricted Stock Units)? How They Vest and Are Taxed",
        aliases=["restricted-stock-units", "rsus"],
        sections=[
            ("What RSUs are", [
                "Restricted stock units are a promise from your employer to give you company shares in the future, once they vest. You do not pay anything for them.",
                "They are usually granted as a value or a number of shares when you join, then vest over several years, often with a one-year cliff, with new grants later as refreshers or for promotions.",
                "Public companies use them widely. At private companies, RSUs often vest only when two conditions are met: time served and an event such as an IPO or a sale of the company.",
            ]),
            ("How RSUs are taxed", [
                "In the US, RSUs are not taxed when granted; when they vest, their market value counts as ordinary income, like salary, whether or not you sell.",
                "Employers usually cover the tax by keeping or selling some of the vesting shares. The default withholding can be lower than your real tax rate, so check whether you will owe more when you file.",
                "When you later sell, any gain or loss since vesting is a capital gain or loss.",
            ]),
            ("RSUs vs stock options", [
                "RSUs are worth something as long as the share price is above zero; options are worth something only if the price rises above the strike price.",
                "Options let you choose when to buy and can be taxed more favourably in some cases; RSUs are simpler and less risky but taxed at vesting whether you like it or not.",
                "To value an RSU grant, multiply the shares vesting each year by a cautious share price, and remember the price can fall before they vest.",
            ]),
        ],
        qa=[
            ("Are RSUs worth it?", "At a public company they are close to pay in shares, though the price can move. At a private company their value depends on a future sale or IPO."),
            ("Should I sell RSUs when they vest?", "There is no single answer. Since tax is already charged at vesting, keeping the shares is much like buying them with that cash; many people sell some so that their job and their savings do not depend on the same company."),
            ("What happens to RSUs when you leave a company?", "Vested RSUs are yours; unvested RSUs are usually forfeited. Check the plan for exceptions such as layoffs or retirement."),
            ("What does RSU refresh mean?", "A new RSU grant given to existing employees, often yearly, so that equity keeps vesting after the first grant runs out."),
        ],
    ),
    "Paid time off (PTO)": dict(
        title="What Is PTO (Paid Time Off)? How It Works and What to Ask",
        aliases=["pto"],
        sections=[
            ("What PTO means", [
                "PTO stands for paid time off: days you are paid for but do not work. Some employers put vacation, sick days and personal days in one PTO bank; others keep separate allowances.",
                "Public holidays may or may not count as PTO; ask how many days you get on top of them.",
            ]),
            ("How PTO works", [
                "PTO may be given at the start of the year or accrued, building up with each pay period or hour worked. Some employers let you carry unused days into the next year; others cap it or apply a use-it-or-lose-it rule where the law allows.",
                "The US has no federal law requiring paid vacation, so it depends on the employer and on state or city rules, mainly for sick leave. Many other countries set a legal minimum: the UK gives full-time workers 5.6 weeks a year including public holidays, and EU law sets at least four weeks.",
                "When you leave, unused PTO is paid out in some US states and under some company policies, and lost in others.",
            ]),
            ("What to ask before you accept", [
                "How many days you get, whether holidays and sick days are separate, and whether new hires accrue from day one.",
                "Whether unused days carry over or are paid out when you leave.",
                "How much time people actually take; with unlimited PTO, the honest answer matters more than the policy.",
            ]),
        ],
        qa=[
            ("What does PTO stand for?", "Paid time off: vacation, sick and personal days for which you are still paid."),
            ("Is PTO required by law?", "In the US, paid vacation is not required by federal law, though some states and cities require paid sick leave. In the UK, the EU and many other countries, a minimum amount of paid leave is a legal right."),
            ("Does unused PTO get paid out when you quit?", "It depends on state law and company policy. Some US states, such as California, require payout of earned vacation; elsewhere the policy decides, so read the handbook."),
            ("What is the difference between PTO and vacation?", "Vacation is time off for rest; PTO is often a combined bank that covers vacation, sick days and personal days."),
        ],
    ),
    "Pay in lieu of notice": dict(
        title="What Is Pay in Lieu of Notice? Meaning and How It Is Paid",
        aliases=["pilon", "payment-in-lieu-of-notice"],
        sections=[
            ("What pay in lieu of notice means", [
                "Pay in lieu of notice, often shortened to PILON, is a payment for the notice period instead of working it. Your employment ends straight away, and you receive the pay you would have earned during the notice.",
                "Employers use it when they want someone to leave at once, for example in a dismissal, a layoff or when a person resigns to join a competitor.",
            ]),
            ("What it should include", [
                "At least the basic pay for the notice period. Depending on your contract and local law, it may also have to cover benefits, pension contributions, commission or bonus you would have earned in that time.",
                "Holiday you have earned but not taken is usually paid separately, on top.",
                "It is usually taxed as employment income, like salary.",
            ]),
            ("PILON vs garden leave", [
                "With pay in lieu of notice your job ends now and you are free to start a new one at once, though any restrictions in your contract that apply after you leave still apply.",
                "On garden leave you stay employed until the end of the notice, so you cannot start elsewhere yet.",
                "If your contract has no PILON clause, an employer that ends your job without notice may owe you damages equal to the notice pay instead; rules differ by country.",
            ]),
        ],
        qa=[
            ("Is pay in lieu of notice taxable?", "Usually yes, as employment income. Check your local rules, since other parts of a termination payment can be treated differently."),
            ("Can my employer pay me in lieu of notice without my agreement?", "If your contract has a PILON clause, generally yes. Without one, ending your job early can still happen but may be a breach of contract; rules differ by country."),
            ("Does pay in lieu of notice include holiday pay?", "Holiday you have already earned is normally paid in addition. Whether you keep earning holiday during the notice depends on whether you are paid in lieu or kept on garden leave."),
            ("Can I start a new job straight away after pay in lieu of notice?", "Usually yes, because your employment has ended. Any non-compete or non-solicit clause in your contract still applies."),
        ],
    ),
    "CV": dict(
        title="What Is a CV? CV Meaning and CV vs Resume Explained",
        aliases=["curriculum-vitae"],
        sections=[
            ("What CV means", [
                "CV stands for curriculum vitae, Latin for “course of life”. In the UK, Ireland, most of Europe and much of the world it is the usual word for the document you send to apply for a job.",
                "In the US and Canada the same document is called a resume, and a CV means a longer academic record used for research, teaching and medical jobs.",
            ]),
            ("CV vs resume", [
                "A business CV outside North America and a US resume do the same job: a summary of your experience, skills and education, usually one or two pages, tailored to the role.",
                "An academic CV is different: it lists everything, including publications, grants, talks, teaching and awards, and can run to many pages.",
                "Customs differ by country: in some a photo, date of birth or nationality is expected, while in the US and UK they are left out to avoid bias.",
            ]),
            ("How to write a good CV", [
                "Put your contact details and a short profile at the top, then experience in reverse order with results, then education and skills.",
                "Use one column and standard headings so applicant tracking systems can read it, and use the words of the posting.",
                "Keep a business CV to two pages at most, and send it as a text-based PDF or a .docx, whichever the employer asks for.",
            ]),
        ],
        qa=[
            ("What is the difference between a CV and a resume?", "Outside North America they mean the same thing. In the US and Canada, a resume is a short document for job applications and a CV is a long academic record."),
            ("What does CV stand for?", "Curriculum vitae, Latin for “course of life”."),
            ("How long should a CV be?", "One to two pages for most jobs; academic CVs are longer because they list publications and teaching."),
            ("Should I put a photo on my CV?", "Not for jobs in the US, UK or Ireland; in some European and Asian countries a photo is still common. Follow the custom of the country where the job is."),
        ],
    ),
    "Layoff": dict(
        title="What Is a Layoff? Laid Off vs Fired and What to Do Next",
        aliases=["laid-off", "layoffs"],
        sections=[
            ("What a layoff is", [
                "A layoff is when an employer ends jobs for business reasons, such as cutting costs, closing an office or restructuring, rather than because of the employee’s performance or conduct.",
                "In the UK and many other countries it is called redundancy; there, a temporary layoff can also mean being sent home without work for a while.",
            ]),
            ("Laid off vs fired", [
                "Being fired means your job ended because of your performance or conduct; being laid off means the role was cut. Both are involuntary.",
                "Laid-off workers in the US are generally eligible for unemployment benefits if they meet their state’s rules; people fired for misconduct may be refused them.",
                "In an interview, a layoff needs only a short, factual explanation, such as “my role was cut in a restructuring”.",
            ]),
            ("What to do after a layoff", [
                "Read any severance agreement and note its deadline before you sign; ask questions and negotiate if you can.",
                "File for unemployment benefits right away and, in the US, compare COBRA with marketplace health plans before your cover ends.",
                "Before you lose access, ask for a reference, save your performance reviews and check when any vested stock options must be exercised.",
                "Update your resume and tell your network; employers are used to seeing layoffs on resumes.",
            ]),
        ],
        qa=[
            ("Is it better to be laid off or fired?", "A layoff is easier to explain and usually keeps you eligible for unemployment benefits and severance. Being fired for cause can affect both."),
            ("Do you get paid when you are laid off?", "You get pay for the time worked and, depending on the law and policy, for unused leave. Severance is not required in the US but is often offered; many other countries require redundancy pay."),
            ("Can you get unemployment if you are laid off?", "Usually yes in the US, if you meet your state’s earnings and job-search rules. Apply as soon as your job ends, because benefits are generally counted from when you file."),
            ("How do you explain a layoff in an interview?", "Say it plainly and briefly, mention that it affected a team or many roles if true, and move on to what you achieved and what you want next."),
            ("What is the WARN Act?", "A US federal law that requires many larger employers to give 60 days’ notice of a mass layoff or plant closing. Some states have their own stricter versions."),
        ],
    ),
}


def test():
    names = [t[0] for t in TERMS]
    assert len(names) == len(set(names)) >= 90, len(names)
    for term, d, tip, links in TERMS:
        assert 8 <= len(d.split()) <= 45 and 8 <= len(tip.split()) <= 40 and links, term
        assert d.endswith(".") and tip.endswith("."), term
    print(f"glossary_terms: {len(TERMS)} terms, all checks passed")


def test_more():
    import re
    slug = lambda t: re.sub(r"[^a-z0-9]+", "-", re.sub(r"\(.*?\)", "", t.lower())).strip("-")   # same rule as gslug in build.py
    names = {t[0] for t in TERMS}
    slugs = {slug(n) for n in names}
    seen = set()
    assert len(MORE) >= 40, len(MORE)
    for term, m in MORE.items():
        assert term in names, f"MORE key not in TERMS: {term}"
        assert isinstance(m, dict) and set(m) <= {"title", "sections", "qa", "aliases"} and {"title", "sections", "qa"} <= set(m), term
        t = m["title"]
        assert isinstance(t, str) and 20 <= len(t) <= 75 and "Jobs Every Hour" not in t, (term, len(t))
        secs = m["sections"]
        assert isinstance(secs, list) and 2 <= len(secs) <= 4, term
        for sec in secs:
            assert isinstance(sec, tuple) and len(sec) == 2, (term, sec)
            head, paras = sec
            assert isinstance(head, str) and head and not head.endswith("."), (term, head)
            assert isinstance(paras, list) and paras, (term, head)
            for p in paras:
                assert isinstance(p, str) and 4 <= len(p.split()) <= 70 and p[-1] in ".?”", (term, p)
        qa = m["qa"]
        assert isinstance(qa, list) and 3 <= len(qa) <= 5, term
        for pair in qa:
            assert isinstance(pair, tuple) and len(pair) == 2, (term, pair)
            q, a = pair
            assert isinstance(q, str) and q.endswith("?"), (term, q)
            assert isinstance(a, str) and 3 <= len(a.split()) <= 80 and a[-1] in ".”", (term, a)
        assert len({q for q, _ in qa}) == len(qa), term
        for al in m.get("aliases", []):
            assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", al), (term, al)
            assert al not in slugs and al not in seen, (term, al)
            seen.add(al)
    print(f"glossary_terms: MORE covers {len(MORE)} terms with {len(seen)} aliases, all checks passed")


if __name__ == "__main__":
    test()
    test_more()
