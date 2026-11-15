# Conversion study: why job seekers pay FlexJobs, RemoteJobsFinder and the others, and what Jobs Every Hour does about it

Read on 15 Nov 2026 from public pages only, for the owner's request of the same day: "Study all of them thoroughly so that people buy
from us more than from them. If for some reason they buy there more often, we need to improve that on our site."

Sites: FlexJobs, RemoteJobsFinder, remotejobs.io, Wellfound, Hirify, Jobright, Teal, Rezi, Remote Rocketship, We Work Remotely,
Himalayas, Indeed (job-seeker side).

How it was done:

- Public pages only. No account was created, nothing was paid, no form was filled, no quiz was clicked through, no bot check was
  passed. Pages that robots.txt asks crawlers to skip were not fetched (RemoteJobsFinder `/onboarding/`, Remote Rocketship `/onboard`,
  Jobright `/jobs/` and `/legal/`). A headless browser was not used.
- Tools: a text reader, web search and plain `curl` with default headers. "Page code" means text inside the public HTML or JavaScript of
  a page that was fetched: it shows what a site can display, not the order a visitor sees it in.
- **Not opened on 15 Nov 2026:** FlexJobs (503 or no connection on every page; its help centre is closed), Teal (403), We Work Remotely
  (403), most of Indeed (403 or a security check). For them the facts come from the browser visit of 13 Nov (`PRICING_RESEARCH.md`),
  Trustpilot, app stores and search results, and each such fact is marked "secondary". web.archive.org could not be reached from here.
- Facts about Hirify marked "(sibling session)" were checked by another cloud session on 15 Nov and sent to this one; they were not
  re-read here.
- The full notes per site, with every URL, are the two appendices at the end. The sections before them are the conclusions.
- Every figure about our own site is counted from the build of 15 Nov 2026 (130,727 open jobs, 3,763 companies).

---

## 1. What makes people pay, ranked

Most likely first. Each line: what they do, the evidence, our honest answer, and what was built for it today.

### 1. The free view stops at the moment of action

- **What they do.** The visitor sees a title and the pay, clicks, and finds the company name or the Apply button locked.
  FlexJobs' own help text: free visitors see listings "except for the company name" and only members see "how to apply" (secondary,
  site not opened). remotejobs.io: a lock where the company should be, "Apply Now" goes to `/registration`, "Sign Up to View and Apply to
  This Job". RemoteJobsFinder: both Apply buttons on a job page go to its price page. Hirify: "с Plus открыты названия компаний, Linkedin и
  ссылки для отклика" on about 70,000 international jobs. Remote Rocketship sells "See every job we find".
- **Why it works.** The person has already chosen the job; paying finishes a click they started. It is the strongest lever in this study.
- **Our answer.** We never lock a job, a company name or an apply link (decided 13 Nov, `AGENT_NOTES.md`), and Google's job search
  requires that anyway. Until today the site did not say so where it matters. **Built:** every new landing page and the work-from-home
  hub carry "Company name and apply link always shown, free" in the first screen, and the "How every job here is checked" block says that
  some paid sites hide exactly these. `/pricing/` has a table "What other sites charge for, free here".

### 2. Fear of scams, sold as the cure

- **What they do.** "100% verified jobs" (RemoteJobsFinder), "Every job we post is hand-screened" and "No Ads, Scams, or Junk"
  (FlexJobs, secondary), "Experts verify every listing" (remotejobs.io), "Verified jobs only, no scams, no junk" (Remote Rocketship),
  "Every job is checked for spam and scams" (Himalayas). remotejobs.io adds a strip of scam news headlines; RemoteJobsFinder's quiz says
  "Fake job listings are everywhere" and "80% of all remote job listings aren't active" with no source.
- **Are the claims honest?** Mostly not checkable, and several fail on their own pages. "Verified" is defined nowhere at
  remotejobs.io, RemoteJobsFinder or FlexJobs. remotejobs.io's "Call Center" page opened with nurse and director jobs, its "Entry Level"
  page with on-site nurse jobs, while its terms say "We are not responsible for the accuracy of job postings". Himalayas' data-entry
  page opens with typical bait titles. RemoteJobsFinder's job page titled "data entry" described an AI-training role at "$40/hour" and
  "$81k/yr" at once. The honest example is Remote Rocketship: each job page shows the source ("Posted on X's careers page"), "Checked 1 hour
  ago" and a ghost score with its reason.
- **Our answer.** Our check is real and can be shown: every job is read from the employer's own hiring system, read again every hour
  (769 companies) or every four hours (the rest), and leaves the lists when the employer closes it; each job page already says it was
  "still on the company's careers page when we last checked, on <date>". **Built:** the first screen of the home page now says this in one
  sentence and counts the closed jobs taken off in the last 7 days; every landing page has a three-step "How every job here is checked"
  block and links the safety checklist. We do not use the word "verified" without saying what was checked.

### 3. An ad and a page that match the search word for word

- **What they do.** remotejobs.io: "Remote Online Jobs No Experience - Remote Jobs $22-48/hr". FlexJobs: "Remote Call Center Jobs …
  14-Day Trial". RemoteJobsFinder: "New $20+/hr Jobs Each Hour". Each sends the click to a page for that search: FlexJobs
  `/remote-jobs/call-center`, `/remote-jobs/no-experience`; remotejobs.io `/work-from-home/{category}` (about 58 of them);
  RemoteJobsFinder 220 hubs `/en/remote-jobs/usa/{role}`; Remote Rocketship 2,525 title pages; Himalayas 18,439 keyword pages.
- **Are the promises kept?** Often not. remotejobs.io's own call-center page says "$12 and $18 per hour", not $22-48. RemoteJobsFinder's
  newest data-entry jobs were 2 days old on the day of "Each Hour". These pages are where the visitor decides whether the ad lied.
- **Our answer.** Pages for the same searches, built from our own jobs and recounted every hour, that say plainly what we have and
  what we do not. **Built (figures of 15 Nov):**

  | Search in the ads | Our page | Open today | What it shows |
  |---|---|---|---|
  | work from home jobs, remote online jobs | `/work-from-home-jobs/` | 25,412 remote | every page below with its count, pay and new this week; remote jobs by field |
  | remote customer service jobs | `/remote-customer-service-jobs/` | 357 | middle stated pay $34 an hour (123 state pay), 79 mention phone work |
  | remote call center jobs | `/remote-call-center-jobs/` | 79 | the remote support jobs whose posting mentions phone work |
  | remote data entry jobs | `/remote-data-entry-jobs/` | 248 | says first that employers' own pages list no remote job called data entry today; shows data annotation and AI training (middle pay $40 an hour) |
  | remote jobs no experience | `/remote-jobs-no-experience/` | 1,014 | junior and intern titles, and postings that ask for one year at most, said in the first line |
  | remote jobs $20 an hour | `/remote-jobs-that-pay-20-an-hour/` | 312 | jobs that state an hourly rate of $20 or more; 10,969 more state a yearly salary of $41,600 or more and are one click away |

  Each page: the "checked" pill, a headline with one highlighted phrase, a lead that names the problem then the fact, three promises,
  four numbers, a button "Narrow them to my pay and hours" that opens "For you" with the page's answers filled in, a pay chart per hour
  and a "who hires the most" chart, the list, how the jobs are checked, questions with FAQ markup, links to the sibling pages. A page is
  built only when 20 jobs fill it.

### 4. A cheap first payment that renews at many times the price

- **What they do.** FlexJobs $2.95 for 14 days, then $23.95 every 4 weeks (13 Nov). remotejobs.io a 14-day trial in its terms, about
  $3.40 then $27.40 a month (secondary), a reviewer charged $23.95. We Work Remotely Pro "$2.95 first month" inside a non-refundable
  12-month commitment at $14.95 a month (secondary, from its FAQ and terms). RemoteJobsFinder "50% OFF" with two 10-minute timers, then
  about $52 a month, and a pay button "TRY FOR FREE" that charges at once (13 Nov).
- **Why it works, and what it costs them.** The first price looks like nothing. The complaints are almost all about the renewal:
  FlexJobs 7 of the newest 20 one-star reviews on Trustpilot are about billing and auto-renewal, 5 about refused refunds; We Work Remotely
  sits at 2.9 on Trustpilot with half its newest reviews about the annual lock-in; RemoteJobsFinder's Trustpilot score is hidden "due to a
  breach of our guidelines" and fake reviews were removed.
- **Our answer.** Plus is one payment and nothing renews: $3 for a month, $7 for 3 months, $12 for a year (launch prices, owner's
  decision). That is the same money as FlexJobs' trial, for a month and with nothing after it. **Built:** `/plus/` shows this side by side
  ("A trial elsewhere $2.95 … A month of Plus $3"), with the source and date; `/pricing/` keeps the median of 11 monthly plans ($29).

### 5. Help with applying, after one free try

- **What they do.** The jobs are free and the help is paid on Wellfound, Indeed, Himalayas, Teal and Rezi. The free plan gives one of
  each tool: Himalayas 1 resume, 1 letter, 1 mock interview; Indeed 1 tailored resume and 1 mock interview (Canada, app); Rezi 1 resume and
  3 PDF downloads; Teal a small pool of AI credits; Hirify 3 matches and letters. RemoteJobsFinder and Jobright promise to apply for you
  ("AI sends 50+ applications daily", "1-Click Application Autofill"); reviewers say it often does not happen.
- **Our answer.** Plus already holds this: resume reworded for each posting, review with a score, letters, interview practice, an email
  the morning a job fits. Our free side is larger than theirs (the resume builder with unlimited PDF and Word, all tools by rules).
  AI runs only for paying accounts (rule of 13 Nov), so there is no free AI try today. **Proposal for the owner** in section 4.

### 6. A short quiz that makes the visitor feel there is a plan

- **What they do.** RemoteJobsFinder's quiz has about 50 steps in its page code: work status, how long you have searched, full or part
  time, minimum pay, remote or office, country, work permit, categories (the first two are "Data Entry / Typing Jobs" and "Customer
  Service"), education, years of experience; then fear screens, a "matching" animation, a match count and the price. remotejobs.io:
  "Answer a Few Simple Questions". Himalayas and Wellfound ask for preferences up front. The quiz ends at a sign-up or a price.
- **Our answer.** "For you" asks the same things in five questions, shows the jobs on the same screen, keeps the answers in the
  browser and asks for nothing. **Built:** question 3 now asks the hours too (full-time 45,463, part-time 1,803, contract or freelance
  2,417, internship 3,078 postings say so; 59% do not say and stay in the list with a question mark); question 4 takes pay by the hour
  ($15 to $50 an hour) as well as by the year, and an hourly posting is now compared with an hourly answer instead of getting a question
  mark; the landing pages open "For you" with their answers already filled in; under the result one line says what Plus will add (email
  the morning a job is posted) and that it is not on sale yet.

### 7. Speed: "be first"

- **What they do.** Remote Rocketship: "We find new remote jobs minutes after companies post them". RemoteJobsFinder: "New $20+/hr Jobs
  Each Hour", "50% of these jobs will expire in 48 hours". Himalayas sells daily alerts (weekly are free). Jobright: "Updated hourly".
- **Our answer.** This is our real edge and the brand: careers pages read every hour (769 companies) or every four hours (the rest),
  posting times to the minute on job pages. Plus sells the email the morning a job fits. We do not use invented expiry figures.

### 8. Removing the risk

- **What they do.** Money-back promises: Rezi 30 days, FlexJobs 14 days, Remote Rocketship 14 days after a purchase or renewal,
  Himalayas "100% money-back", Teal 14 days (secondary). Cancel yourself: Remote Rocketship ("No phone calls, no chat queues"), Himalayas.
  Some are real; RemoteJobsFinder's needs screenshots of 100 applications.
- **Our answer.** Nothing renews and there is nothing to cancel. A refund promise is the owner's call (section 4).

### 9. Big numbers and social proof

- **What they do.** RemoteJobsFinder: "1M+ jobs", "10k+ sources", "120k+ users found a job", "Rated 4.8 out of 5 based on 238 reviews"
  with a Trustpilot logo, while its public sitemap lists 3,929 job pages and Trustpilot hides its score; testimonials dated "3 days ago" in
  fixed text. Jobright: "3x interviews landed" while its own blog survey says 50% more. Rezi: "Ranked #1 by Forbes" with no link found.
  Wellfound: animated "Interview booked · just now", "Founder pitched you" notifications with real company names and invented people.
- **Our answer.** We show only counted numbers with the date (the "Checked Nov 15" pill, counts, pay, closings). No reviews until real
  users write them, no user counts, no notification animations. This is a rule, not a gap.

---

## 2. The sites at a glance

| Site | First promise | Locks at | Price for a seeker | Trial / renewal / refund | "Verified"? |
|---|---|---|---|---|---|
| FlexJobs | "#1 Job Site to Find Work From Home Jobs. No Ads, Scams, or Junk" (secondary) | company name and how to apply (secondary) | $23.95 every 4 weeks; $29.85 / 3 months; $71.40 / year | $2.95 for 14 days, renews; refund on request within 14 days | "hand-screened", method not public |
| RemoteJobsFinder | "Find 300k+ Remote, Hybrid & Local Jobs"; ad "Wellfound" | both Apply buttons go to the price page | about $52 a month after a per-day intro price (13 Nov) | timers, "Last Call 60%"; refund needs 100 application screenshots | "100% verified", no method; numbers contradict its sitemap |
| remotejobs.io | "Find Remote Jobs Faster", "Every listing checked by experts" | company (lock) and Apply (registration) | not on the site; about $27.40 a month (secondary) | 14-day trial in terms, renews; marketing consent bundled with sign-up | off-topic jobs on its own category pages |
| Remote Rocketship | "Remote Jobs You Won't Find on LinkedIn" | the full result list | $29 a month, $59 / 3 months, $99 / year | "no free trial", 14-day refund, cancel or pause yourself | shows source page, "Checked 1 hour ago", ghost score |
| Jobright | "No More Solo Job Hunting / Do it with AI" | daily credits (secondary) | about $39.99 a month (secondary) | refund rules dated 29 Jul 2026 (secondary); marketing box ticked in advance | "3x interviews" vs its own survey's 50% |
| Hirify | "Ваша работа мечты здесь" | company name and apply link on ~70,000 international jobs | 399 ₽ a month, 990 / 3 months, 1,990 / year | one payment, no renewal, no refunds except by law | counts "213 000+" are a monthly total |
| Wellfound | "Find work that matters." | an account to apply | free | — | fake notification mock-ups with real company names |
| Teal (not opened) | "Free Forever" vs "$13 per week" (13 Nov) | AI credits | $13 a week, $29 a month, $79 / 90 days | refund within 14 days (secondary) | — |
| Rezi | "Ranked #1 AI Resume Builder by Forbes" | 1 resume, 3 PDF downloads | $29 a month or $149 lifetime | 30-day full refund | Forbes claim not found; "62.18%" used for two things |
| We Work Remotely (not opened) | "largest remote work community" (secondary) | Pro: alerts, "unlimited applications" (secondary) | $14.95 a month in a 12-month commitment (secondary) | first month $2.95, non-refundable year (secondary); Trustpilot 2.9 | — |
| Himalayas | "Get matched with your next remote job. Then land it with AI." | 1 free resume, letter, mock interview; weekly alerts | $9 Plus, $29 Max, monthly | cancel any time, "100% money-back" | "checked for scams" next to bait data-entry titles |
| Indeed (mostly not opened) | "the free job search app" (App Store) | nothing for search; Pro only in Canada on iPhone | CAD 9.99 a month (Pro, secondary) | 7-day trial, non-refundable | terms disclaim job accuracy |

---

## 3. What we never copy

Seen in this study; each is against the owner's rule (no invented reviews, numbers or urgency) or against the site's own rules.

1. Locking the company name or the apply link (FlexJobs, remotejobs.io, RemoteJobsFinder, Hirify).
2. Another brand's name in our ad text (RemoteJobsFinder's ad headline "Wellfound"; a Trustpilot reviewer calls it impersonation).
   Bidding on the word is allowed and is in the plan; the text says only our name.
3. Ads that promise what the page does not have (remotejobs.io "$22-48/hr" against its own "$12 and $18 per hour").
4. Countdowns, "reserved" discounts, exit discounts, "50% of these jobs will expire in 48 hours" (RemoteJobsFinder).
5. A made-up personal result before the price ("We found 8,577 jobs that match your profile", "Get a job in 4-6 weeks").
6. Cheap trials that renew at 8 to 14 times the price, "every 4 weeks" billing, a "$2.95 first month" inside a 12-month contract,
   "TRY FOR FREE" on a button that charges.
7. Refunds that cannot be had (100 application screenshots) and a "100% Money-Back Guarantee" banner over them.
8. Review scores that differ from their source, testimonials with fixed "3 days ago" dates, quotes signed only "Candidate".
9. Notification animations with invented interview invites and real company names (Wellfound).
10. Awards and success rates without a link ("Ranked #1 by Forbes", "3x interviews" against the company's own 50%).
11. Fear statistics with no source; scam headlines used as social proof.
12. Marketing consent ticked in advance (Jobright) or bundled into sign-up (remotejobs.io).
13. "Verified" without saying what was checked and when.
14. Counts that disagree across our own pages. Every number here comes from the build, with its date.

---

## 4. What needs the owner (decisions, not work)

1. **A refund promise for Plus.** 7 of the 14 seeker pricing pages read on 13 Nov had one; it is the honest form of "risk removal" in
   section 1.8. Suggestion: "If Plus does not help, ask within 7 days and get the payment back", done from the account by a button once
   the server is live. With crypto a refund is a transfer back; the owner decides whether to offer it. Not written on the site until he
   says yes.
2. **One free AI try.** Every site in section 1.5 lets a person use each paid tool once for free; the second use sells. Today AI runs
   only for paying accounts. Suggestion: one free AI resume review per browser, inside a fixed monthly budget, so the cost is capped. Owner's
   call, because it spends money before anyone pays.
3. **Google Ads account and payment method** (section 5). About 20 minutes, only in his name.
4. **A Google tag on the landing pages, yes or no** (section 5.2). Recommended: no; count from our own server logs first.
5. When Plus goes on sale: put "Plus" back in the top menu (it is there only on phones until then, `NAV_PLUS`), and switch the line under
   the "For you" result from "not on sale yet" to the offer (it switches by itself with `plus.live`).

---

## 5. Ads plan (written only: no account was created)

Nothing here can start until the owner does two things that only he can do: open a Google Ads account under his own Google login and add a
payment method to it (Google Ads takes cards and bank payments; the site's own crypto checkout is not involved). About 20 minutes. Until
then this is a plan.

### 5.1 What the rules allow

- **Bidding on another brand's name as a keyword is allowed** (Google Ads trademark policy). RemoteJobsFinder does exactly that with
  "Wellfound".
- **Using another brand's name in the ad text can be stopped** once the owner of the trademark files a complaint with Google; the ad is
  then disapproved in the regions the complaint covers. So every ad below says only our own name. RemoteJobsFinder's ad headline
  "Wellfound" is the thing not to copy.
- **Employment ads in the United States and Canada** fall under Google's personalised-advertising rules for housing, employment and
  credit: no targeting by age, gender, parental status, marital status or ZIP code. Target by keyword and country only.
- **Misleading ads are refused** (misrepresentation policy) and they also waste money: a headline must match what the landing page shows
  that day. That is why there is no "Remote Data Entry Jobs" headline (we have almost none) and why every number in an ad is rounded down
  ("300+") and checked against the landing page before the ad goes live.
- **Our own rule:** no invented reviews, user counts, "verified by hand" or urgency in ads either.

### 5.2 Tracking without breaking the site's rules

The site loads no third-party scripts (speed rule in `AGENT_NOTES.md`), and Google's conversion tag is one. Two ways that keep the rule:
1. Count visits per landing page from the ad's `utm_` tags in our own server logs (the site now runs on the owner's server), and count the
   next step (opening "For you", saving a job, pressing Apply) the same way. This is enough to stop keywords that bring no one who stays.
2. When Plus goes on sale: send purchases to Google Ads as offline conversions from our server (an upload, not a script on the page).
Decision for the owner: whether a Google tag may be added to the landing pages only. Recommended: no, start with (1).

### 5.3 Campaigns, ad groups and landing pages

One Search campaign per country group (start with the United States; add the UK, Canada, Australia once the US numbers are known).
Exact and phrase match only at the start. Negative keywords from day one: "indeed", "linkedin", "login", "sign in", "salary of",
"near me" (we answer "near me" elsewhere), "craigslist", "scam" questions about other companies.

| Ad group | Keywords (examples) | Landing page |
|---|---|---|
| Customer service | remote customer service jobs, work from home customer service, customer service jobs from home, chat support jobs remote | `/remote-customer-service-jobs/` |
| Call center | remote call center jobs, work from home call center jobs, call center jobs from home | `/remote-call-center-jobs/` |
| Data work | remote data entry jobs, data entry jobs from home, data annotation jobs, ai training jobs remote | `/remote-data-entry-jobs/` |
| Beginners | remote jobs no experience, entry level remote jobs, online jobs no experience | `/remote-jobs-no-experience/` |
| Hourly pay | remote jobs 20 an hour, work from home jobs 20 dollars an hour, remote jobs that pay 25 an hour | `/remote-jobs-that-pay-20-an-hour/` |
| General | work from home jobs, remote online jobs, legit work from home jobs | `/work-from-home-jobs/` |
| Other brands | flexjobs, flexjobs alternative, is flexjobs worth it, flexjobs free | `/work-from-home-jobs/` (FlexJobs has no comparison page: its site did not open, so its facts are too few) |
| Other brands | remotejobsfinder, remote jobs finder, remotejobsfinder reviews | `/vs/remotejobsfinder/` (new: every fact from its own pages, dated) |
| Other brands | remotejobs io, remotejobs.io reviews | `/vs/remotejobs-io/` (new) |
| Our brand | jobs every hour, jobseveryhour | home page |

### 5.4 Example ads (responsive search ads; headlines up to 30 characters, descriptions up to 90; lengths checked)

**Customer service** (landing `/remote-customer-service-jobs/`)
- Headlines: Remote Customer Service Jobs · Chat, Email and Phone Support · From the Employer's Own Page · Free to See and to Apply ·
  No Account, No Membership · See What Each Job Pays · Closed Jobs Leave the List · Jobs Every Hour
- Descriptions: "Every job is read from the employer's own careers page and checked again within hours." ·
  "Free to see and to apply on the employer's site. No sign-up, no subscription, no trial."

**Call center** (landing `/remote-call-center-jobs/`)
- Headlines: Remote Call Center Jobs · Phone Support From Home · From the Employer's Own Page · Nothing to Pay to Apply · Jobs Every Hour
- Descriptions: "Remote support jobs whose posting mentions phone work, read from the employer's own page." ·
  "Pay shown where the employer states it. Answer five questions to see the jobs that fit."

**Data work** (landing `/remote-data-entry-jobs/`)
- Headlines: Data Annotation Jobs, Remote · AI Training Jobs, Paid Hourly · From the Employer's Own Page · Free to See and to Apply
- Descriptions: "Few jobs are called data entry. Data annotation pays by the hour and is hired from home."

**Beginners** (landing `/remote-jobs-no-experience/`)
- Headlines: Remote Jobs for Beginners · Junior and Intern Remote Jobs · Free to See and to Apply · Jobs Every Hour
- Descriptions: "Jobs with a junior or intern title, or that ask for a year of experience at most."

**Hourly pay** (landing `/remote-jobs-that-pay-20-an-hour/`)
- Headlines: Remote Jobs at $20+ an Hour · Hourly Pay Shown Up Front · From the Employer's Own Page · Pick Hours, Pay and Country
- Descriptions: "Only jobs whose posting states an hourly rate of $20 or more, from the employer's page."

**Other brands** (landing `/vs/remotejobsfinder/`, `/vs/remotejobs-io/` or `/work-from-home-jobs/`; no other brand's name in the text)
- Headlines: Remote Jobs, Free to See · No Trial That Renews · No Account, No Membership · Read From Employers' Sites · Jobs Every Hour
- Descriptions: "Every job here is free to see and to apply, read from the employer's own careers page." ·
  "Free to see and to apply on the employer's site. No sign-up, no subscription, no trial."

Sitelinks (each a real page): "Customer service jobs", "Jobs for beginners",
"$20+ an hour", "Match by 5 answers" (`/for-you/`), "Free resume builder" (`/resume/`).

### 5.5 Budget and when to stop

- Start: 10 to 20 US dollars a day in total, US only, for 14 days. Owner's money, owner's decision; nothing is promised in return.
- Keep a keyword only if visitors from it go on to a second step (open a job, open "For you", press Apply) at least as often as the
  site's search visitors do. Stop it otherwise. Look at the search terms report every 3 days and add negatives.
- Brand words of other sites cost more and convert worse for a free site: run them only after the generic groups have numbers.
- Before Plus is on sale an ad cannot pay for itself in money. Its job is to bring people who come back (saved jobs, "For you" answers,
  alerts). Raise the budget only after Plus can be bought and the first sales are counted.

---

## 6. Who pays job sites at all (from a sibling session, not re-checked here)

Sent on 15 Nov 2026 by the cloud session working on the site's revenue research; its sources are company reports and calls.

- Employers pay almost everywhere. Kanzhun (BOSS Zhipin): 99.1% of revenue from employers, 0.9% from job seekers (2025). Naukri: about 93%
  from employers; paying job seekers rose from 1.2% to 2.2% of monthly active users (FY26 call, 28 May 2026). ZipRecruiter: 73,929 paid
  employers, $1,683 each a quarter (Q3 2026). LinkedIn: Premium (Career and Business together) over $2B of $17.8B, about 11%.
- Who buys seeker plans, by FlexJobs' own surveys (2025/2026): about 70–73% women, Gen X about 45%, 69% changing or thinking of changing
  career, 29% with children at home. Seekers buy more when hiring is weak (Naukri calls it "counter cyclical").
- What that session suggests: sell the employer side first (a flat-fee featured or pinned post for small companies and startups), and the
  seeker plan second, aimed at experienced remote seekers and career changers, expecting 1–2% of active users to buy. This session did not
  act on it: `/post-a-job/` belongs to another session's work, and prices are the owner's.

---

# Appendices: the notes per site, with every source

Written on 15 Nov 2026 by the two research helpers of this session; kept as they wrote them, apart from the heading levels and the two notes marked in the text.

## Appendix A. FlexJobs, RemoteJobsFinder, remotejobs.io, Remote Rocketship, Jobright: the notes per site

For: Jobs Every Hour (jobseveryhour.com), a free job board.
All pages read 15 Nov 2026 unless the line says otherwise.

How I worked:

- Tools: WebFetch (a text reader), WebSearch, and plain `curl` with default headers. No browser, no accounts, no forms, no checkouts, no quiz clicked through.
- "Page code" means text that ships inside the public HTML or JavaScript of a page I fetched. It shows what the site can display; it does not prove the order or the variant a visitor gets.
- "Secondary" means the fact is not from the site itself (search snippet, review site, Trustpilot). Treat it as unverified.
- I respected robots.txt: I did not fetch RemoteJobsFinder `/*/onboarding/*`, Remote Rocketship `/onboard*`, or Jobright `/jobs/*` and `/legal/*` (Jobright blocks ClaudeBot from `/jobs/`).
- Facts already in `PRICING_RESEARCH.md` (13 Nov 2026) and `COMPANIES_RESEARCH.md` are reused only where named.

---

### 1. RemoteJobsFinder (remotejobsfinder.co)

Status: opened with curl. Price page not re-opened (robots.txt asks crawlers to skip `/onboarding/`); figures from 13 Nov are in `PRICING_RESEARCH.md` A.5.

**1. Ad and landing promise**
- Owner's Google ads (15 Nov): headline "Wellfound"; sitelinks "New $20+/hr Jobs Each Hour", "1M+ Jobs, 10k+ Sources", "120k+ Our Users Found Job". A Trustpilot reviewer says the same: "They impersonate Wellfound Remote Jobs (which used to be Angel List) by adding this as their search tittle" (Maya Ospina, 21 Oct 2026, https://www.trustpilot.com/review/remotejobsfinder.co).
- The ad landing page `/.../call-center` with "Set your preferences and let AI do the rest. Job search on autopilot. 100% verified jobs" was **not found**: `https://remotejobsfinder.co/call-center` redirects to `/en/call-center`, which returns 404 to plain curl. It may need ad parameters. Not verified.
- Public role pages (hubs) top block: "Stop searching manually / Get your job 3X faster", one button "Try Now" (https://remotejobsfinder.co/en/remote-jobs/usa/remote-data-entry).
- Page title of the home page: "RemoteJobsFinder: Find [300k]+ Remote, Hybrid & Local Jobs" (https://remotejobsfinder.co/en). The rest of the home page is drawn by JavaScript; the reader saw only a spinner.

**2. Query landing pages**
- Sitemap: https://remotejobsfinder.co/sitemap_index.xml lists two files.
  - `sitemap_remote_hubs.xml`: 220 hubs, all `/en/remote-jobs/usa/{role}`. Query-style ones: `remote-data-entry`, `data-entry-specialist`, `remote-customer-service`, `customer-service-remote`, `customer-service-specialist`, `call-center-manager`. No "no-experience", "$20/hour" or plain "call-center" hub.
  - `sitemap_listings_active.xml`: 3,929 job pages (3,920 `/en/remote-jobs/usa/{title}_{uuid}`, 9 hybrid).
- Hub example `/en/remote-jobs/usa/remote-data-entry`: page title "Remote Remote Data Entry Jobs in the United States (November 2026)" (the word "Remote" twice). Page data holds 20 jobs and `"totalRecords":420`. Company names, employer URLs and pay are in the data. Of the 20, 10 show pay: 7 hourly ($15 to $28/hr), 3 yearly ($35,784 to $43,344). Newest posting date among the 20: 13 Nov 2026.
- The whole USA hub `/en/remote-jobs/usa` reports `"totalRecords":500` (looks like a cap).

**3. What a visitor sees before paying**
- A job page shows the title, company, pay, skills and the full description. Example: https://remotejobsfinder.co/en/remote-jobs/usa/data-entry-operator_09d874c2-ef6d-447b-a3dc-6270e10ab902 shows "Aston Carter", "$81k/yr", full text.
- The same page's title tag says "salary from $40/hour", and the body describes an AI-training reviewer role for healthcare billing staff, not data entry. Title, pay and content do not match.

**4. How free value is limited**
- Both "Apply" buttons on the job page link to `/en/onboarding/64/subscription/5` (the price page), not to the employer. The employer link exists in the hub's page data (`jobUrl`) but is not shown.

**5. Price, renewal, refund, cancel**
- 13 Nov (repo, browser): plans priced per day with "50% OFF" and two 10-minute timers; renews at 1,348,132 VND a month (about $52). Page code also holds "TRY FOR 3 DAYS", "TRY FOR 7 DAYS", "1-Year Plan", "Lifetime plan" variants.
- Refund ("100% Money-Back Guarantee") only if you write within 30 days and send screenshots of at least 100 applications over 14 consecutive days (monthly plans) or 50 over 4 days (weekly). "Meeting the aforementioned criteria is the sole basis for qualifying for a refund." California and Connecticut: 3 business days. EU: 7 days, prorated. Last updated 10 March 2024. https://remotejobsfinder.co/en/legal/money-back-policy
- Cancel: "through your account settings" (page-code FAQ).

**6. Trust claims vs what I can see**
- Jobs: "1,000,000+ remote jobs in one place"; FAQ "We add over 1,000,000 new remote jobs every month"; quiz "Access 750k+ hidden jobs monthly", "We've analyzed 20 million jobs"; title "300k+". Public sitemap: 3,929 job pages. None of the big numbers matches anything visible.
- Sources: ad "10k+ Sources"; plan page "Our AI scans 10,000+ hidden sources"; quiz "1,000+ job sources"; FAQ "checking 1,000+ sites daily". The site disagrees with itself by 10x.
- Users: ad "120k+"; plan page "Join 120,000+ professionals who already found their dream job"; quiz "150,000 users"; "65% of our members find a job within the 1st month"; price page "Get a job in 4-6 weeks", another variant "Job In 3-5 Weeks". No source given.
- "Each Hour": the 20 newest data-entry jobs were dated 15 Oct to 13 Nov. Not supported.
- "Verified" is defined once: "Our team filters out all job scams, ads, and junk, leaving you with 100% verified jobs" (page-code FAQ). No method given.

**7. Social proof**
- Hub pages: "Rated 4.8 out of 5 based on 238 reviews" next to a Trustpilot logo image. Trustpilot today: 584 reviews, 40% five-star, 44% one-star, score hidden: "This company's rating is unavailable due to a breach of our guidelines", and "We've removed a number of fake reviews for this company."
- 15 testimonials: first and last name plus job ("by Megan Foster, Unemployed"), no photo, no link. The date "3 days ago" is fixed text in the page source, so it never changes.
- Page code: "As featured in" press logos, "Our members got jobs at these companies" employer logos; analytics events "review stars submitted" then "review trustpilot link clicked" (an in-app rating step before Trustpilot; whether only high ratings are sent on is not verified).

**8. Onboarding questions (page code; order not verified)**
- About 50 numbered quiz steps. Examples in order of their numbers: current work status; how you approach the search; how long you have been job hunting; "65% of our members find a job within the 1st month"; what you are looking for ("Urgent income for my basic needs" ...); full-time/part-time; minimum salary; remote/hybrid/office; country; "Are you authorized to work in the US?"; job categories (first ones "Data Entry / Typing Jobs", "Customer Service"); education; years of experience; level.
- Fear and reassurance screens: "The job market got brutal", "Fake job listings are everywhere", "80% of all remote job listings aren't active", "75% of all resumes never reach human recruiters", "57% of remote jobs get 300+ applications within 24 hours". No sources.
- Ends with "Matching you with ... remote jobs ... Success! We found ... remote jobs", then the price page.

**9. Email capture**
- Quiz step: "Almost done — set up your account / Enter email to get job offers from our private recruiter group", buttons "CREATE ACCOUNT", "See my matches" (page code).
- 13 Nov (repo): checkout's first field is "Create account: E-mail"; pay button "TRY FOR FREE" while the card is charged at once.

**10. At sign-up (page code)**
- Price page shows "We found {count} verified remote jobs for a {jobTitle}", "50% of these jobs will expire in 48 hours", timeline "Today / Week 2 / Week 4 / Week 6 ... interviews ... job offers".
- If you leave: "Last Call — We want you to find your dream job. Here's your additional discount: 60%", timer "60% discount reserved for: min sec".
- Promise after paying: "AI sends 50+ applications daily", resume and cover letter per job.

**11. Complaints (Trustpilot, 15 Nov)**
- Charges after cancelling and higher second-month charges: "They charge vastly elevated fees on the second month even if you think you have unsubscribed."
- Refund refused under the screenshot rule: title "NO refund without proof of 50 applications" (Leslie Anders).
- Auto-apply not as sold: "No Auto Applying, No Trial-End Notification, No Refunds" (SCW, 24 Oct 2026).
- Brand misuse in search ads (Wellfound quote above).

---

### 2. remotejobs.io

Status: plain curl got 403 on every page except robots.txt; the WebFetch reader returned the pages. Prices are not on the site.

**1. Ad and landing promise**
- Owner's ad: "Remote Online Jobs No Experience - Remote Jobs $22-48/hr … Register, Browse Curated Jobs & Apply".
- Home: headline "Find Remote Jobs Faster"; sub-lines "Every listing checked by experts." and "No scams, just real remote jobs curated for you."; buttons "Get Started" (5 times, all to `/curate-search/how-it-works-2`) and "Find Your Next Remote Job". https://www.remotejobs.io/
- How-it-works page: "Quality Remote Jobs in Just 3 Steps": "Answer a Few Simple Questions", "Easily Apply", "Start Your Remote Work Life"; button "Don't Miss Your Chance to Apply".

**2. Query landing pages**
- Pattern `/work-from-home/{category}`: 5 top (customer-service, developer, virtual-assistant, accounting, data-entry) and about 53 more, including call-center, chat-support, live-chat, typing, transcription, tutoring, entry-level. Also `/search?joblocations=Work%20From%20Anywhere`. Sitemap: 403.
- `/work-from-home/call-center`: "1 to 50 of 2,083 for Call Center". The first 8 titles are mostly not call-centre jobs: "Data Center Services Engineer", "Director of Development, Heart Center and Cardiology", "Nurse Educator, RN" (all Durham, NC).
- `/work-from-home/entry-level`: H1 "Remote Entry Level Jobs - Work from Home & Online", "1 to 50 of 6,354". First results: "Registered Nurse", "Clinic Registered Nurse" in Omaha, NE and Council Bluffs, IA. They look on-site, not remote.
- `/work-from-home/data-entry`: "1 to 50 of 5,917". First titles: "Senior Director, AI-Native Intelligence and Data Insights", "Senior Data Engineer". Not entry-level data entry.
- Pay text on the call-center page FAQ: "$12 and $18 per hour, or about $48,600 to $59,600 per year". The ad says $22-48/hr. My arithmetic: $12-18 x 2,080 hours = $24,960-37,440 a year, so the page contradicts itself too.

**3. What a visitor sees before paying**
- About 50 rows per page: title and location. Pay and posting date mostly not shown.
- Company: on the call-center and entry-level pages the reader saw a lock in place of the company. On the data-entry page it saw company names. Mixed; not checked in a browser.

**4. How free value is limited**
- "Apply Now" links to `/registration`; the job view says "Sign Up to View and Apply to This Job".

**5. Price, trial, renewal, refund, cancel**
- No price anywhere on the site. Terms: "Charges incurred on a periodic basis are charged in advance and shall be subject to automatic renewal"; a "14-day trial subscription term"; "RemoteJobs may provide a full refund to customers who are still within their 14-day trial subscription term"; "Remaining part of the subscription remains active and is not refundable"; cancel "by login to your account", effective at the end of the paid term. https://www.remotejobs.io/terms-of-service
- Seller: Sonaga Tech Limited, Hamilton, Zweigniederlassung Luzern, Hertensteinstrasse 51, 6004 Luzern, Switzerland. "Tripod Jet, LLC may additionally act in our contract as a merchant of record."
- Secondary: $3.40 for 14 days, then $27.40 a month or $6.80 a month yearly (resume.co, 9 Jul 2026, https://resume.co/blog/remotejobs-io-review). A Trustpilot reviewer (10 Nov 2026) was charged "23.95 USD", the same renewal figure as FlexJobs. A shared owner is not verified.

**6. Trust claims vs what I can see**
- "Experts verify every listing", "No ads, ghost jobs, or scam listings", "We've filtered out hundreds of thousands of irrelevant jobs". The same company's terms say "We are not responsible for the accuracy of job postings." The "Job Search Vigilance" page gives no method or numbers.
- The category pages I opened returned off-topic and on-site jobs under "Remote" headings (above), which does not fit "checked by experts".

**7. Social proof**
- No testimonials on the home page. An unlabeled strip of five scary news headlines ("Fake job postings are stealing applicants' money and identities" ...) with outlet logos. It sells fear of free boards and looks like "as seen in".
- "Top Companies Hiring Remotely": YETI, Google, Amazon, DoorDash, Zillow logos with a footnote "does not imply endorsement or affiliation".
- "Millions of professionals are already enjoying a remote job" (no figure, no source).
- Trustpilot: 3.8, 865 reviews, 56% five-star, 16% one-star; invites reviews; claimed June 2024; paid Trustpilot subscription. https://www.trustpilot.com/review/remotejobs.io

**8. Onboarding**
- "Answer a Few Simple Questions" (how-it-works). Secondary (resume.co): target job title, minimum salary, location or remote only; no résumé needed first.

**9. Email capture / 10. At sign-up**
- `/registration`: "Sign up with Google" or email and password, button "Sign up today!". Fine print: by clicking you agree to the terms "and to be added to our mailing list for updates and offers". Marketing consent is bundled, no box.
- Promises "Professional resume review: a resume analyst reviews and validates your resume".
- Secondary: billing page shows status "but no direct cancel button" (resume.co).

**11. Complaints (Trustpilot, 15 Nov)**
- Money taken without clear consent: "They will debit the money without any consent" (9 Nov 2026).
- Partial refund: paid 23.95 USD, got 11 back after complaining (10 Nov 2026).
- No results: "I payed twice and didn't get any job for almost 3 months" (6 Nov 2026); "i am not able to find suitable jobs".
- Auto-renew after a trial people thought was free (secondary: joingerald.com summary).

---

### 3. FlexJobs (flexjobs.com)

Status: **not opened** on 15 Nov. WebFetch got 503 on `/pricing`, `/FAQ`, `/remote-jobs/call-center` and a `/publicjobs/` page; curl could not connect; my tools cannot reach web.archive.org; `flexjobs.zendesk.com` redirects to Zendesk's "help-center-closed" page. Below: the repo's 13 Nov browser visit, Trustpilot (read 15 Nov), and search snippets of FlexJobs pages (secondary).

**1. Ad and landing promise**
- Owner's ad: "Remote Call Center Jobs … 100% Verified Jobs, Resume Help, Career Tools. 14-Day Trial". The ad text shown does not say the trial costs $2.95.
- A home-page variant is indexed at `/homevariant/t18` with the title "The #1 Job Site to Find Work From Home Jobs. No Ads, Scams, or Junk" (search result).

**2. Query landing pages (from search index)**
- `/remote-jobs/{category}`: call-center, call-center-representative, data-entry, entry-level, no-experience. Paginated `?page=N` (call-center to about page 50; entry-level past page 350).
- A second template `/remote-jobs/call-center/t1?page=N` (looks like a test variant for ads).
- `/jobs/{keyword}` (e.g. `/jobs/call-center`, `/jobs/data-entry?sub=1029`) and single public jobs at `/publicjobs/{title}-{uuid}`.
- Title format: "Remote Call Center Jobs - Work From Home & Flexible". Rows show remote/hybrid, schedule, employee/freelance, pay, location and badges such as "FlexJobs Top 100 Remote" and Fortune 500 (search summary).
- Counts in snippets (dates unknown): no-experience about 3,346; entry-level 59,022 to 62,938.

**3. and 4. What a visitor sees; how it is limited (FlexJobs' own text, via search)**
- "Free visitors to the site can view a short version of all current job listings." "Only FlexJobs members see detailed descriptions of the job, including information about the company and how to apply." Not logged in, you see the same details "except for the company name" (FlexJobs tip page). So: title, pay and badges are bait; company and apply link are paid.

**5. Price, trial, renewal, refund, cancel**
- 13 Nov (repo, browser): "$2.95 — 14-DAY FULL ACCESS", then "auto-renews at $23.95 billed every 4 weeks"; 3 months $29.85 up front; a year $71.40 up front. Full refund on request within 14 days of account creation.
- FAQ (search snippet): "cancel and ask for a refund within 14 days of subscribing (by phone, email, or our Client Service virtual chat)". Cancelling online does not by itself start a refund (secondary, joingerald.com). App sign-ups cancel in the app store.
- Seller: BOLD LLC (Puerto Rico) or Auxiliant S.à.r.l (Luxembourg) as merchant of record (`COMPANIES_RESEARCH.md`). A reviewer mentions a different merchant name on the card statement.

**6. Trust claims**
- "Every job we post is hand-screened for legitimacy"; "No Ads, Scams, or Junk"; "Verified Remote and Flexible Jobs" counts of 219,249 and 233,955 with 14,389 and 14,812 companies; "10,000,000+ job seekers served" (search snippets, undated).
- "Verified" is explained as review by a research team that removes scams, commission-only and MLM jobs. A FlexJobs FAQ says it cannot verify companies outside its board. More than 200,000 jobs each read by a person is not verifiable.
- A one-star reviewer (10 Nov 2026) wrote that "all posted 100% remote jobs were incorrectly posted".

**7. Social proof**
- 13 Nov (repo): three counters, review carousel, review-site score, "Thanks for Your Trust" note. No countdown, no crossed-out prices.
- Trustpilot: 4.1, 8,366 reviews, 64% five-star, 8% one-star; invites reviews ("Invited" labels); paid Trustpilot subscription; may use AI-assisted replies. https://www.trustpilot.com/review/www.flexjobs.com

**8. Onboarding / 9. Email capture / 10. At sign-up**
- Not verified. Secondary (2021 review): "Sign Up" form first, then plan choice. After joining: preferences for alerts and a résumé profile (FlexJobs blog).

**11. Complaints (Trustpilot one-star page, 20 reviews, 6 Oct to 13 Nov 2026)**
- Billing and auto-renewal (7 of 20): "I was charged $23.95 I didn't approve"; "Once you sign up, they won't let you stop."
- Refund or cancellation ignored or refused (5): "they refused to issue the remaining $11.95, claiming I contacted them too late".
- Pay before you can judge (4): "You have to pay for a subscription first before u can even search the remote jobs".
- Value (3): "indeed and LinkedIn have more jobs available that flex jobs for free."

---

### 4. Remote Rocketship (remoterocketship.com)

Status: opened with curl. One founder, Lior Neu-ner, named on every page.

**1. Promise**
- Home: "Remote Jobs You Won't Find on LinkedIn"; sub-line "We find new remote jobs minutes after companies post them, so you can apply before the crowd."; button "Find my dream remote job". Badges: "Loved by 10,000+ remote workers", "100% remote", "Verified jobs only", "No scams, no junk". https://www.remoterocketship.com/
- "Browse all remote jobs" on the home page also goes to the quiz (`/onboard/?type=tangent_new_layout`), not to the board. Owner did not show an ad for this site.

**2. Query landing pages**
- Sitemaps (robots.txt lists 20+): 2,525 job-title pages `/jobs/{title}/` (e.g. call-center-agent, call-center-rep, customer-service, entry-level, no-experience, part-time), 199 country pages, 1,766 company pages, job pages per country (worldwide: 1,523), US, Brazil, German and French copies.
- `/jobs/call-center-agent/`: title "Remote Call Center Agent Jobs ($45K)"; "Search 334 work from home call center agent positions."; "334 total jobs", "31 new jobs this week", "10% of this week's jobs are NOT on LinkedIn". Page data: 20 jobs with company, pay and employer URL. First one: "Agente de Call Center", Peru, PEN 1,130 a month.

**3. What a visitor sees before paying**
- Job page (example https://www.remoterocketship.com/us/company/kinpos-corporation/jobs/kinpos-talent-seed-qa-calidad-soporte-datos-pm-innovacion-worldwide-remote/): company, full text, "Ghost score 10%" with the reason, "Posted on KinPOS Corporation's careers page", "Still open on KinPOS Corporation's site. Checked 1 hour ago.", and "Apply Now" linking straight to the employer (bamboohr.com) in the page HTML.

**4. How free value is limited**
- Paid plans add "See every job we find: All results for every search and filter, including salary, visa sponsorship and seniority". Page code has an "Unlock All Jobs" pop-up (scheduled, dismissable) and a "Sign up to apply to this job" pop-up. When each one fires is not verified.

**5. Price, trial, renewal, refund, cancel** (https://www.remoterocketship.com/pricing/ , /help/)
- $29 a month; $59 every 3 months ("$19.60 per month", "Save 32% vs monthly"); $99 a year ("$8.20 per month", "Best value", "Save 72% vs monthly"). Stripe.
- "There's no free trial, and we'd rather say that straight than hide it." Instead: refund if you email "within 14 days of a plan purchase or renewal".
- Cancel yourself on the Account page ("No phone calls, no chat queues"); pause up to two months once a year. The "% off" is explained as the saving against monthly.

**6. Trust claims vs what I can see**
- Jobs: "Lists over 100,000 remote jobs" and "Search our job board for 180,000+ remote jobs" (legit page); live stats "191,886 remote jobs live", "129,673 careers pages watched", "1,714 jobs found in the last 24 hours" (https://www.remoterocketship.com/live-stats/). Roughly consistent; "100,000+ companies" is backed by the live figure.
- "Verified" is defined by what each job page shows: source page, last check time, ghost score. This is the most checkable claim in this study.
- Weak spots: "10,000+ more jobs than other job boards" (which boards?), "Most members hear back within the first week" (no source), "roughly a third of the jobs on our site can't be found on LinkedIn" vs "10%" on the call-centre page (different scopes, not explained).

**7. Social proof**
- Three home testimonials with first names only ("Adam", "Eduardo", "Lacey K."), no photos or links.
- Pricing page: "TrustScore of 4.4 out of 5 from 124 reviews (as of October 2026)". Trustpilot today: 4.5, 148 reviews, 74% five-star, 7% one-star; "hasn't invited customers recently". https://www.trustpilot.com/review/remoterocketship.com
- No countdowns, no fake discounts seen. A founder page "Is Remote Rocketship legit?" admits the main fault: closed jobs still listed.

**8. Onboarding / 9. Email capture / 10. At sign-up**
- Quiz not opened (robots.txt). Pricing page: "Answer a few quick questions and see your first matches before you pay." robots.txt lets Facebook's crawler into the onboarding pages, so paid social ads likely land there (inference).
- Email: "Set Up Email Alert For New Jobs" on listing pages; login by emailed code.

**11. Complaints**
- Few. Trustpilot shows no recent one-star review. Themes: alert emails stopped and slow support (review later raised to 5 stars); applying without replies. Founder lists closed listings as "the most common genuine criticism".
- Repo note (`REVENUE_RESEARCH.md`): its first paywall test cut traffic by 50%.

---

### 5. Jobright (jobright.ai)

Status: opened with curl (home, sign-up, remote-jobs page, blog). `/jobs/*` and `/legal/*` not fetched (robots.txt).

**1. Promise**
- Home: "No More Solo Job Hunting / Do it with AI"; sub-line "Get matched jobs, autofill applications, tailored resume, and recommended insider connections in less than 1 min!"; buttons "Try For Free", "JOIN NOW". https://jobright.ai/
- Owner did not show a Jobright ad.

**2. Query landing pages**
- Sitemaps: 4,548 role pages `/jobs/{role}` (not opened), 17 remote pages `/remote-jobs/{category}/{role}`, `/h1b-jobs`, `/software-engineer-jobs`, `/data-analyst-jobs`, 11 comparison pages, tool pages.
- `/remote-jobs/customer-support-success`: H1 "Top 100% Remote Customer Support & Success Jobs in the U.S."; "Updated hourly from major job boards and 200K+ company career sites."; "288,684 Total Openings", "13,626 New Openings Today"; box "Subscribe To Fresh Remote Alerts". 20 rows with company, level, age ("just now", "1 hour ago") and some pay ("$30/hr - $35/hr", "$7.25/hr - $11.50/hr").

**3. and 4. What a visitor sees; how it is limited**
- Company names and pay are open on list pages; "View" goes to `/jobs/info/{id}` (not opened).
- Free plan with daily credits (secondary, careery.pro, which sells a competing service): 2 tailored résumés, 4 one-click autofills, 2 cover letters, 1 alert, 1 saved filter per day. Paid plan "Turbo" lifts the limits.

**5. Price, refund, cancel**
- No seeker price page: `/pricing` returns 404; the "Pricing" link goes to `/employers/pricing`. Own blog (18 Jun 2025): "Premium plans ($30/month)" (https://jobright.ai/blog/is-jobright-legit/).
- Secondary (Aug to Oct 2026 reports): $17.99 a week, $39.99 a month, $89.99 a quarter. Refund policy dated 29 Jul 2026 (secondary): first monthly/quarterly/6-month purchase within 7 days, first weekly within 24 hours, an unwanted renewal within 3 days, "usage and other eligibility limits apply". Not verified.

**6. Trust claims vs what I can see**
- Home: "3x interviews landed", "80% time saved", "No.1 Choice for 80% of job seekers after their first use". Sign-up page: "2X More Qualified Job Matches", "60% Time Savings", "50% More Interview Invites". Own blog: an internal survey of 2,000+ users "reported a 50% increase in interview invitations on average". The home page "3x" is six times the company's own survey figure.
- Jobs: "8,000,000+" total and "400,000+" new today. 288,684 open remote US customer-support jobs is hard to believe: Remote Rocketship counts 191,886 remote jobs live in all fields worldwide. Not verified either way.
- "No fake listings": one row on the same page is "Customer Service Specialist - REMOTE | No experience required" from a firm that describes itself as "independent Symmetry Financial brokers" (insurance sales). Whether this is commission-only: not verified.
- Users: "3,000,000 trusted users" (home) vs "500,000+ Registered Users" by June 2025 (blog). Growth is possible; not verified.

**7. Social proof**
- Seven home testimonials with first name, initial and job title ("Fred H., Senior Software Engineer"), shown twice in a loop; one named executive quote (Grammarly's Chief People Officer).
- Trustpilot: 4.8, 3,772 reviews, 84% five-star, 1% one-star; invites reviews; paid subscription. `USER_PAINS.md` already noted nearly all reviews are recent and very short.

**8. Onboarding (from robots.txt paths; order inferred)**
- `/onboarding-v3/signup`, then `diagnostics`, `mode-selection`, `career-goals`, `advanced-preferences`, `resume-upload`.

**9. Email capture / 10. At sign-up**
- `/onboarding-v3/signup`: email and password, and a box "I want to receive updates from Jobright about latest job offers" that is **ticked in advance** (`checked` in the HTML).

**11. Complaints**
- Trustpilot one-star, 13 Nov 2026, "Buying premium = Waste of time": "scam calls, fake listings, broken listings".
- Autofill works less often than sold (secondary: one user says about 3.5% of "auto-fillable" jobs filled); duplicate applications (3-star review).
- Trustpilot's own summary: confusing credit system, blank pages.
- Few billing complaints visible, unlike FlexJobs and RemoteJobsFinder.

---

### Why people pay this site — ranked

Across all five, most likely reason first:

1. **The free view ends at the moment of action.** The visitor sees a title and pay, then the company name or the apply button is locked. FlexJobs hides company and how to apply; remotejobs.io locks company and sends "Apply Now" to registration; RemoteJobsFinder sends both "Apply" buttons to its price page. People pay to finish a click they already started.
2. **Fear of scams, sold as the cure.** "No scams, no junk" (Remote Rocketship), "Experts verify every listing" (remotejobs.io), "hand-screened" (FlexJobs), "100% verified jobs" (RemoteJobsFinder), plus scam headlines (remotejobs.io) and "Fake job listings are everywhere" (RemoteJobsFinder quiz). The buyer is often new to remote work ("no experience", call centre, data entry ads).
3. **A cheap first payment.** $2.95 (FlexJobs), about $3.40 (remotejobs.io, secondary), "50% OFF" with a 10-minute timer (RemoteJobsFinder). The renewal ($23.95 every 4 weeks; about $52 a month) is in small print, and the complaints are mostly about it.
4. **A promised shortcut: "we apply for you" or "apply first".** "AI sends 50+ applications daily" (RemoteJobsFinder), "1-Click Application Autofill" (Jobright), "minutes after companies post them" (Remote Rocketship). Complaints show auto-apply often does not happen.
5. **Big numbers and invented progress.** "1M+ jobs", "120k+ found a job", "3x interviews", "Get a job in 4-6 weeks", "We found 8,577 jobs that match your profile". Most cannot be checked; several contradict the same site.

Per site, top reason:

- RemoteJobsFinder: urgency and a personal "result" after a long quiz (timers, "50% of these jobs will expire in 48 hours", invented match count), on top of the locked apply link.
- remotejobs.io: an ad that matches the search ("No Experience", "$22-48/hr") and a cheap trial; companies hidden behind registration.
- FlexJobs: brand trust and "hand-screened, no scams" for people afraid of fake jobs; $2.95 trial; company hidden.
- Remote Rocketship: a real feature (fresh jobs from company pages, ghost score, live stats) and honest terms; paid to see all results.
- Jobright: free tool with daily limits; people upgrade when they hit the limit on tailored résumés and autofill.

### What we must never copy

Each line is a pattern I saw, with where.

1. **Locking the apply link or the company name.** RemoteJobsFinder (Apply goes to the price page), remotejobs.io (lock icon, "Sign Up to View and Apply"), FlexJobs ("except for the company name"). The job is the employer's, not ours to sell.
2. **Another site's name in the ad text.** RemoteJobsFinder's ad headline "Wellfound"; a Trustpilot reviewer calls it impersonation. (Bidding on the word itself is allowed and is in the ads plan, section 5.)
3. **Ad promises the site does not keep.** remotejobs.io "$22-48/hr" vs its own "$12 and $18 per hour"; "No Experience" page full of nurse and senior jobs; "Remote" pages with on-site jobs. RemoteJobsFinder "New $20+/hr Jobs Each Hour" with newest data-entry jobs 2 days old.
4. **Countdowns, "reserved" discounts and exit offers.** RemoteJobsFinder: "50% discount reserved for", "This offer ends in 06:49", "Last Call ... additional discount: 60%", "50% of these jobs will expire in 48 hours".
5. **A fake personal result before the price.** RemoteJobsFinder: "We found 8,577 jobs that match your profile", "Get a job in 4-6 weeks", a profile the visitor never filled in (13 Nov).
6. **Cheap trial, quiet renewal, "every 4 weeks".** FlexJobs $2.95 then $23.95 every 4 weeks; remotejobs.io same $23.95; FlexJobs ad says "14-Day Trial" with no price. A pay button labelled "TRY FOR FREE" that charges at once (RemoteJobsFinder, 13 Nov).
7. **A refund you cannot get.** RemoteJobsFinder: 100 application screenshots over 14 days, "the sole basis". Its banner still says "100% Money-Back Guarantee".
8. **Review scores that do not match the source.** RemoteJobsFinder shows "Rated 4.8 out of 5 based on 238 reviews" with a Trustpilot logo while Trustpilot hides its score for a guidelines breach and removed fake reviews. Fixed "3 days ago" dates on testimonials.
9. **Numbers that disagree with themselves.** RemoteJobsFinder (1,000 vs 10,000 sources; 300k vs 1M vs 20M jobs; 3,929 job pages in its sitemap). Jobright ("3x interviews" vs its own survey's 50%; "2X" and "60%" on the sign-up page vs "3x" and "80%" on the home page).
10. **Fear statistics with no source.** RemoteJobsFinder quiz: "80% of all remote job listings aren't active", "75% of all resumes never reach human recruiters". remotejobs.io scam-headline strip.
11. **Consent ticked or bundled.** Jobright's marketing-email box is ticked in advance; remotejobs.io adds you to its "mailing list for updates and offers" by clicking sign-up.
12. **"Verified" with no definition.** remotejobs.io, RemoteJobsFinder, FlexJobs. Remote Rocketship shows the better way: source page, "Checked 1 hour ago", ghost score with its reason. If we say "verified", we show what was checked and when.

---

### Not opened or not verified

- FlexJobs: every page tried (pricing, FAQ, call-center, a public job page) gave 503 to WebFetch or no connection to curl; help centre closed; Wayback unreachable from my tools. FlexJobs facts are from the repo's 13 Nov visit, Trustpilot and search snippets.
- RemoteJobsFinder ad landing `/.../call-center`: not found. Price page not re-opened (robots.txt). Quiz order not verified; strings come from page code.
- remotejobs.io: price not published; prices are secondary. curl got 403; WebFetch read the pages.
- Remote Rocketship and Jobright quizzes: not opened (robots.txt). Jobright job pages and legal pages: not opened (robots.txt). Jobright prices and refund rules: secondary only.
- Ownership links (remotejobs.io and FlexJobs both renew at $23.95): not verified.
- Google Ads Transparency for these advertisers: not re-checked (needs a browser); RemoteJobsFinder figures are in `COMPANIES_RESEARCH.md`.

---

## Appendix B. Hirify, Wellfound, Teal, Rezi, We Work Remotely, Himalayas, Indeed: the notes per site

For Jobs Every Hour (jobseveryhour.com). Sites: Hirify, Wellfound, Teal, Rezi, We Work Remotely, Himalayas, Indeed.
All reading done on 15 Nov 2026 unless another date is given. Public pages only: no accounts, no payments, no forms,
no onboarding clicked through, no bot checks bypassed. "Secondary" means a search result, review site or third-party
article, not the site itself. "Not verified" means I could not confirm it on the site's own page.

How each site answered (15 Nov 2026):

| Site | Own pages | What I used instead |
|---|---|---|
| Hirify | Opened (home, /plus, /oferta, a landing page, a job page, robots, sitemaps, JS text strings) | Product Radar notes already in `USER_PAINS.md` |
| Wellfound | Opened (home, /jobs, /candidates/overview, /candidates/featured, role and location pages, help centre) | Trustpilot |
| Teal | Not opened: tealhq.com and help.tealhq.com answered 403 (Cloudflare) to curl and WebFetch | `PRICING_RESEARCH.md` A.9 (browser, 13 Nov 2026), search results, Trustpilot |
| Rezi | Opened (home); pricing and tools already in `PRICING_RESEARCH.md` A.12 and `REZI_RESEARCH.md` (14 Nov 2026) | Trustpilot |
| We Work Remotely | Not opened: every weworkremotely.com and support.weworkremotely.com page answered 403. web.archive.org could not be reached from here (connection reset) | Search results quoting its FAQ and terms, two third-party reviews, Trustpilot (2 pages) |
| Himalayas | Opened (home, /pricing, /plus, docs, sitemaps). /jobs pages answered a Cloudflare check ("Just a moment...") to curl; WebFetch read one landing page | Trustpilot |
| Indeed | Mostly not opened: home, job search pages, /about, /career, help on zendesk answered 403 or "Security check". Opened: robots.txt, /legal, two help articles | Search results, Apple App Store, Trustpilot |

---

### 1. Hirify (hirify.me)

Russian-language IT job aggregator (Telegram channels plus company career sites). Seeker pays for "Plus".

1. **Main promise.** Home: title and h1 "Ваша работа мечты здесь" ("Your dream job is here"); sub-line "Хайрифай это джоб-борд и мета-агрегатор лучших вакансий в Айти и Диджитал."; header button "Включить Plus" ("Turn on Plus"); search button "Искать". Plus page h1 "Hirify Plus", sub-line "Международные вакансии, сильное резюме и сопроводы, которые приводят к офферам" ("International jobs, a strong resume and cover letters that lead to offers"), button "Подключить Plus" with "за 399 рублей в месяц". https://hirify.me/ , https://hirify.me/plus , read 15 Nov 2026.
2. **Landing pages.** Sitemap index https://hirify.me/sitemap.xml (read 15 Nov 2026). `main.xml` has 897 landing URLs: 460 grade x specialisation pages (`/junior-backend-dev-jobs`), 340 "remote" variants (`/junior-backend-dev-remote-jobs`), 116 country pages (`/sql-jobs-in-cyprus`; Armenia 19, Cyprus 15, Serbia 14, Israel 11), 63 relocation pages (`/relocation-to-germany`, `/python-relocation-to-serbia`), plus `/cv-roasting`, `/mcp-api`, `/for-hrd`. Job sitemaps: 4 files of 45,000 plus 6,098 (186,098 job URLs), 9,434 Telegram job URLs, 9,153 salary pages (`/salaries/<role>/<region>`), 322 company URLs. No "no experience", "data entry" or "$X/hour" pages: it is IT only. A landing page (https://hirify.me/junior-backend-dev-remote-jobs) shows: h1 "Junior Backend-разработчик вакансии - удалённо", "91 вакансий за месяц", job rows, and a pay box "СНГ $1.3k /мес, $1k - $1.8k, 10 в выборке; International $99k /год, $68k - $127k, 26 в выборке". Meta text promises "обновление каждые 2 часа".
3. **Before any wall.** All jobs are listed with title, tags, pay and age. Telegram-sourced jobs show contacts and are free. International ("Hirify Global") jobs show "Company hidden"; the job page says "Вакансия из Hirify Global, списка международных tech-компаний" and "Для мэтча и отклика нужен Plus" ("Plus is needed to match and apply"). The company name inside the description is replaced with "hirify.global", but the text can still give it away: the sample job (https://hirify.me/jobs/1269615-senior-consumer-lending-manager) says "using FICO Score solutions".
4. **How free value is limited.** From the Plus page "Free vs Plus": Free gets Telegram jobs, "Весь основной функционал", "Мэтчи и сопроводы: 3"; Plus adds "Международные вакансии: без ограничений", "AI прожарка резюме: 6 раз", unlimited matches and cover letters. Plus page: "Вакансии видны всегда, но с Plus открыты названия компаний, Linkedin и ссылки для отклика". So the paywall is: company name plus apply link on about 70,000 jobs.
5. **Price and terms.** 399 RUB / 1 month, 990 RUB / 3 months ("-27%"), 1,990 RUB / year ("-63%"). "Это разовый платёж, не подписка." FAQ: "Plus - это разовый платёж, он не продлевается сам, отменять нечего." Offer (https://hirify.me/oferta, dated 11 June 2025): "399 рублей / 6$ за месяц"; "Возвраты не предусмотрены, за исключением случаев, прямо предусмотренных законом"; access opens within minutes, "не позднее 24 часов". The discount chips do not match the arithmetic (990 is 17% under 3 x 399; 1,990 is 58% under 12 x 399; `PRICING_RESEARCH.md` A.17). The app text still says "Your Plus subscription is now active!" although it is not a subscription (JS bundle, read 15 Nov 2026).
6. **Trust claims.** Home: "213 000+ актуальных вакансий в IT и Digital" next to "213 155 вакансий за месяц" (a monthly count, not jobs open now). "Обновляем каждые 2 часа" on the home page, but the Plus FAQ says the Global list "Обновления происходят каждые 3 часа" and "Проверка происходит каждые 2 часа". "Дедупликация по 960+ Telegram-каналам ... ловит около 90% дублей". `COMPETITOR_GAPS.md` already noted /about says 700+ sources while llms.txt says 1,000+ channels and 20,000+ career sites. Sitemaps hold about 195,500 job URLs, roughly in line with the 213k monthly figure. A scam warning sits on every job page ("Если работодатель просит войти в их систему, используя iCloud/Google ... Это мошенники").
7. **Social proof.** Plus page: "❤️ Уже 3500+ человек подключили Hirify Plus ❤️" (no source). Six testimonials signed only with Telegram handles (@presscancel, @MrOrloff ...), no photos; most praise the resume roast, one says "Благодаря вашему ресурсу я получил оффер". No Trustpilot page (trustpilot.com/review/hirify.me returned 404). No fake notifications or countdowns seen.
8. **Onboarding.** Not seen. Sign-in options from the site's text strings: "Войти через Google", Telegram sign-in, "Зарегистрироваться через Google".
9. **Email capture.** None. The capture is Telegram: "Войдите, чтобы сохранить фильтр и получать уведомления о новых вакансиях"; alerts are free ("Для этого не нужен Plus"). A "login-reminder" pop-up exists in the page styles (text not seen).
10. **At sign-up.** Free account; saved filters go to a Telegram bot. Payment confirmation goes to the email given at payment (offer, section 4).
11. **Free vs paid layout.** A "Сравнить Free/Plus" button in the hero, two check-mark columns, then three plan cards, each "Выбрать". Headline benefit: international jobs with company names and apply links. Partner bonuses as extra value: "3 дня бесплатно" with a career community, "Скидка 10%" on an English school.
12. **Complaints** (Product Radar launch thread, https://productradar.ru/product/hirify/ , via `USER_PAINS.md` section 2, not re-read today): weak moderation, Telegram channel ads posing as jobs, "too early to charge"; empty jobs that only point to another site; mixed Russian and English interface; after the paid launch, profiles could not be edited and the payment provider handled foreign cards badly (founder's own account, https://tproger.ru/articles/uvolili--otlichno--kak-razrabotchik-zapustil-konkurenta-hh-ru---hirify-me-i-nachal-zarabatyvat).

13. **Checked by a sibling session on 15 Nov 2026 (sent to this one, not re-read here).** The home counter "213,154 вакансий за месяц"
    counts every live job; with the period set it shows 106,571 for a month, 31,555 for a week, 13,312 for three days and 1,360 for one day
    (ours today: 130,727 open). About 95% of its jobs come from company careers sites and hiring systems (its sitemaps: 186,098 careers-site
    job pages, 9,434 Telegram ones). 186,667 of 213,179 jobs are in English; the interface is Russian or English, with a filter by posting
    language; job pages switch between an AI rewrite ("Hirify AI") and the original. Its terms (§3.2) forbid building a competing aggregator
    from its data: nothing is taken from it.

**Why people choose or pay Hirify, ranked**
1. To see who the employer is and get the apply link on about 70,000 international jobs: the only thing the paywall hides ("с Plus открыты названия компаний, Linkedin и ссылки для отклика").
2. One search instead of hundreds of Telegram channels and hh.ru, with exclude filters (free; it is what users praise on Product Radar).
3. AI resume "roast" and cover letters, anchored against a human price: "У коучей такой разбор стоит $30-150. В Plus включено 6 разборов."
4. A low, one-time price with nothing to cancel (399 RUB, "не подписка").
5. Supporting a small founder: "Hirify - это стартап без инвестиций. Поддержка Plus - это не только про фичи".

---

### 2. Wellfound (wellfound.com), job-seeker side

Startup job marketplace (formerly AngelList Talent). Seekers never pay; the money comes from employers.

1. **Main promise.** Home h1 "Where great companies meet great people."; sub-line "The startup job search and AI recruiting platform. Apply directly to founders, or post jobs free and hire with AI sourcing agents."; seeker panel "Find your next job. Apply directly to founders and hiring managers at 27,000+ startups building what's next." with "Browse jobs →" and "Sign up to find a job →". Seeker page (https://wellfound.com/candidates/overview) h1 "Find work that matters.", button "Create your profile →". https://wellfound.com/ , read 15 Nov 2026.
2. **Landing pages.** robots.txt allows them; the only sitemap (`basics.xml.gz`) has 86 URLs, so landing pages are found through links. Patterns from the footer and /jobs: `/role/<role>` ("Software Engineer Jobs"), `/role/r/<role>` (remote), `/role/l/<role>/<city>`, `/location/<city>`, `/remote`, `/job-collections/<list>` (e.g. "junior-software-engineer-jobs", "companies-that-hire-coding-bootcamp-graduates"). Each shows "N results total" and pages of companies with jobs, pay and equity ("$40k – $100k • 0.05% – 0.1%"), years of experience, posting age. Counts seen: remote software engineer 1,834; software engineer 4,863; software engineer in New York 787; New York 3,938. Page titles say "2027" already ("Remote Software Engineer Jobs in 2027 | Wellfound", "Software Engineer Jobs in New York, US - 2027").
3. **Before any wall.** Company, size, stage, title, pay, equity, location limits, "Actively Hiring", response-speed badges ("Top 1% of responders", "Responds within a day"). "Apply" and "Save" are buttons that need an account (help: "1. Sign in to your account", https://help.wellfound.com/article/769-how-do-i-apply-to-a-job).
4. **How free value is limited.** It is not: "Creating a profile and applying to jobs on Wellfound is always free for candidates." and "You will never have any fees as a job seeker using Wellfound." (https://help.wellfound.com/article/799-does-angellist-cost-anything-for-job-seekers). The only gate is the account.
5. **Price and terms.** None for seekers. Employer prices in `PRICING_RESEARCH.md` B.8.
6. **Trust claims.** "27,000+ startups", "10M+ candidates", "100K+ hires", "Over 130k remote & local startup jobs" (https://wellfound.com/jobs). Role pages show far fewer (1,834 remote software jobs), so 130k cannot be checked. "Say goodbye to cover letters" on the seeker page, but the help article says the Apply pop-up asks for "a note. A note is akin to a cover letter." "Private by default" for the job search.
7. **Social proof.** Four testimonials signed only "Candidate" or "Recruiter", no names, no photos. **Mock-ups that look like live notifications with interview invites**: "Interview booked · just now", "Founder pitched you: Gabriel at Uthana wants to talk", "Interview confirmed: Zipline · Tuesday, 2:00 PM", "3 pitches this week", "+1 pitch · 2h ago", "You're getting noticed ... Zipline Saved your profile", using real company names (Chime, Lovable, Zipline, Braze, Preset, Monograph) next to invented people (https://wellfound.com/candidates/overview , https://wellfound.com/candidates/featured). Trustpilot 3.9 from 144 reviews, claimed, "No recent history of asking for reviews" (https://www.trustpilot.com/review/wellfound.com).
8. **Onboarding.** Not opened (/onboarding is blocked in robots.txt). Public pages say the profile holds skills, projects, links, "Preferences up front: Set salary, remote, and role expectations once", and an optional recorded "AI interview" sent with every application.
9. **Email capture.** No email field. Every seeker button goes to `/jobs/signup` with a source tag (`source=homepage&source_content=hero`).
10. **At sign-up.** Profile creation; then "Get discovered" spotlight: "Selected profiles go in front of top companies ... Privately, for 8 weeks at a time", "3x More connections when Featured".
11. **Free vs paid.** No paid tier. The draws are free extras: one-click apply, the AI interview ("Applications with your interview attached get seen first"), the spotlight ("It's 100% free").
12. **Complaints** (Trustpilot, read 15 Nov 2026): accounts restricted or banned with no reason ("restricted with zero communication", Sep 2026); slow or no support replies; fake jobs, fraudulent applicants and spam messages ("most jobs look to be fake", Oct 2025); email notifications "quite spammy" that cannot be turned off.

**Why people choose Wellfound, ranked**
1. Pay and equity shown on every row, plus "who's actively hiring, who responds fast": less guessing before applying.
2. One profile, one click to apply, and a promise of reaching founders directly ("not third-party recruiters").
3. Being found without applying: AI sourcing and an 8-week spotlight, all free.
4. Startup-only scope with a strong brand (27,000+ startups claimed).
5. Response-speed signals on companies, aimed at the fear of being ghosted.

---

### 3. Teal (tealhq.com)

Resume builder, job tracker and Chrome extension. Seeker pays for Teal+.

1. **Main promise.** Home page not opened (403 on 15 Nov 2026); headline not verified. Pricing page (browser, 13 Nov 2026, `PRICING_RESEARCH.md` A.9): "Free Forever" against "$13 per week", buttons "Get Started", "No credit card required to start." The About page title in search results is "The people behind Teal, helping you land the job you love" (secondary).
2. **Landing pages.** robots.txt (read 15 Nov 2026) points to https://www.tealhq.com/sitemap-index.xml, which answered 403. Search results show public job pages `/job/<title-slug>_<hash>`, many of them remote entry-level ones: "Entry Level | Customer Support Advisor | Remote", "Entry Level - Customer Service (Work From Home)", "Remote Customer Support Representative" (SkillersZone, $75,000–$120,000), "entry-level-remote-associate" (search, 15 Nov 2026). Teal also publishes blog comparisons (`/post/rezi-review`, `/post/teal-review`, secondary). No city or "$X/hour" pages found. Page types not verified.
3. **Before any wall.** Secondary: "Teal requires you to sign up before you can search its board" (https://simplify.jobs/c/Teal-HQ). Individual job pages are indexed, so they are probably readable; not verified.
4. **How free value is limited.** AI credits: help centre (search snippet of https://help.tealhq.com/en/articles/9530153-teal-vs-teal, not opened): the free version has "a select number of non-renewable AI Generation credits", costing 5 credits per bullet, 2 per summary, 2 per cover letter; Teal+ unlimited. Third-party lists also name keyword matching and the match score as Teal+ only. Teal's own help mentions a way to "trial" Teal+ features inside the free plan (snippet of https://help.tealhq.com/en/articles/9535168-is-there-a-teal-free-trial).
5. **Price and terms.** "$13 Every 7 Days ($1.85 a day)", "$29 Every 30 days ($0.96 a day)", "$79 Every 90 days ($0.87 a day)", recurring (`PRICING_RESEARCH.md` A.9, 13 Nov 2026). Refund: within 14 days of purchase; Teal is "not responsible for recurring charges if a member forgets to cancel"; cancel from Account page, "Teal+ Subscription" tab, "Cancel Subscription" (search snippets of https://help.tealhq.com/en/articles/9451252-what-is-the-cancellation-policy and https://help.tealhq.com/en/articles/9457672-changing-canceling-your-teal-subscription; not opened). The weekly plan is the first one shown and the per-day figures make the price look smaller.
6. **Trust claims.** "4 million" users or professionals in third-party write-ups (https://jobgether.com/blog/teal-vs-jobgether-senior-remote-job-search, `REVENUE_RESEARCH.md`); not verified on Teal's page. Some of its indexed job pages look like typical bait (same "SkillersZone" employer shows $18–25/hour data entry on Himalayas and $75,000–$120,000 here); not verified as scams.
7. **Social proof.** Trustpilot 4.3 from 120 reviews, claimed since Jun 2020, "no recent history of asking for reviews"; 72% five-star, 13% one-star; reviews named, mostly praising the tracker ("Five stars for the keywords alone.") (https://www.trustpilot.com/review/tealhq.com , read 15 Nov 2026). Pricing page: four testimonials (13 Nov 2026). No fake notifications seen (home not opened).
8. **Onboarding.** Secondary only: account first, then a step to "specify your career goals" (https://www.unite.ai/tealhq-review); "prompted to create your core profile" (https://aiindigo.com/tutorials/getting-started-with-teal-build-an-ats-optimized-resume-track-applications). Order not verified.
9. **Email capture.** Not seen (home not opened). One Trustpilot review (16 Jun 2026): "every day a new spam email" and a broken unsubscribe.
10. **At sign-up.** Account required before the app; the Chrome extension saves jobs from other boards into the tracker (secondary).
11. **Free vs paid.** Pricing page opens with a two-column table "Free Forever" vs "$13 per week" and a 17-feature list (13 Nov 2026). Headline paid benefit, per help snippets: unlimited AI writing plus keyword matching and a match score against a job description.
12. **Complaints.** Few on Trustpilot: spam emails; "one month paid plan - not as good as expected" (2-star, Oct 2024, search snippet); wish for more automation in keyword insertion. No billing-trap pattern seen.

**Why people choose or pay Teal, ranked**
1. A free job tracker that replaces a spreadsheet (most reviews praise this; "no cap on how many job listings I can store").
2. Keyword match and score against a specific job description: the main thing behind Teal+.
3. Unlimited AI writing once the small free credit pool runs out.
4. A short weekly plan ($13 for 7 days) for someone who expects a short, intense search.
5. A Chrome extension that pulls jobs from any board into one place.

---

### 4. Rezi (rezi.ai)

AI resume builder; also a job search inside the app and a free job map (map.rezi.ai). Seeker pays for Pro or Lifetime.

1. **Main promise.** Home title "The #1 AI Resume Builder – Forbes' Top Pick. Trusted by 4,785,497+"; h1 "Ranked #1 AI Resume Builder by Forbes"; sub-line "Join 4.8 million job seekers. Build, improve, and tailor your resume with AI. Try it free—no credit card required."; buttons "Try for free", "Upload or drop your resume to get started", "Score my resume". Closing block: "Swipe right on your next job and get hired in weeks, not months." https://www.rezi.ai/ , read 15 Nov 2026. Pricing page title "Rezi Pricing: Plans With a 30-Day Money-Back Guarantee" (`PRICING_RESEARCH.md` A.12).
2. **Landing pages.** rezi.ai sitemap has 503 URLs: 82 `/resume-examples/<job>`, 58 `/resignation-letter-template/<case>`, 227 blog posts incl. 12 "Rezi vs X", `/tools/<tool>` pages (`REZI_RESEARCH.md` section 1, 14 Nov 2026). Job queries are served by map.rezi.ai: `/jobs/<city>/<role>` titled "40,000 Software Engineer Jobs in New York | November 2026 | Rezi" (count plus month), `/jobs/<city>/hiring-near-me`, `/jobs/company/<slug>`, job pages; only 184 URLs in its sitemap (30 cities x 6 roles) (`REZI_RESEARCH.md` section 3). No "no experience" or "$X/hour" pages seen.
3. **Before any wall.** On map.rezi.ai: full job list and descriptions, "View job posting" goes to the employer, no login. On rezi.ai: the "free tools" are landing pages whose buttons go to `app.rezi.ai/signup`; the shown score is a static picture (`REZI_RESEARCH.md` section 2).
4. **How free value is limited.** Free: "1 Resume, 1 AI Interview, 3 PDF Downloads, Standard Format Templates"; limited Rezi Score and keyword targeting; unlimited cover and resignation letters. A Trustpilot review (10 Nov 2026): "You get 3 free downloads and some AI credits to apply suggestions".
5. **Price and terms.** Pro "$29 / month" ("Access to all features plus unlimited AI & free monthly review"); Lifetime "Buy for $149" ("All features, one payment."). "Rezi offers a 100% money-back guarantee on all paid plans (Pro and Lifetime). If you are unsatisfied, you can request a full refund within 30 days of your purchase." Upgrades and downgrades prorated. Home, read 15 Nov 2026.
6. **Trust claims.** "Ranked #1 AI Resume Builder by Forbes": no Forbes link on the page and no Forbes article found by search (not verified). The same "62.18%" appears as "Success ... Interview Rate, Average is ~3%, as of 2025 data" and, lower down, as "62.18% review rate for applicants": two different meanings for one number. "4,785,497+ Total Users" and "job seekers helped since September 2019" (the founder told the owner 5M users, `REZI_RESEARCH.md`). "Helping users land jobs at 1,000+ companies".
7. **Social proof.** Rating shown three ways on one page: "4.6 / 5.0" (hero), "4.7 out of 5 across 274 reviews" (plans), "4.6 / 5.0 274 reviews (View Trustpilot reviews)" (footer), plus "8.23 / 10 Avg. User Review" with no source. Trustpilot (https://www.trustpilot.com/review/rezi.io , read 15 Nov 2026): 4.6, 277 reviews, claimed, and Rezi "invites customers to review"; 82% five-star. Testimonials carry names and country ("Dakota Rubin, United States, Written via ..."), one only a handle ("Kixxx"). A quote from "Ashley Stahl, Career Contributor". Growth used mass giveaways of paid plans (70,000 sign-ups in a day in Oct 2023; 93,000+ lifetime accounts in Sep 2025; `REZI_RESEARCH.md` section 4). Animated mock-ups of an AI interview replay; no fake job-offer notifications seen.
8. **Onboarding.** App not opened. Public start: upload a resume or start from scratch, add a target job description (FAQ). Map sign-in: Google, Apple or email.
9. **Email capture.** No email field on the home page; everything goes through sign-up. On the map, saved searches work without an account; syncing asks for sign-in.
10. **At sign-up.** Free account, no card. Map clicks carry a `target-job` cookie into the app so the chosen job is already loaded (`REZI_RESEARCH.md`).
11. **Free vs paid.** Three cards on the home page (Pro first, then Free, then Lifetime), with a feature table on /pricing. Headline paid benefit: "unlimited AI", unlimited resumes and downloads, and the Rezi Score against a job.
12. **Complaints.** Trustpilot is mostly positive; refunds after unexpected charges are praised as quick ("cancellation and refund done quickly", Oct 2026). Older Reddit posts (r/Rezi, 2023 mirror) about being charged with no reply to refund requests (search result, not verified). One reviewer criticised the company's Reddit account conduct (Oct 2026). AI text "feels generic" and needs editing.

**Why people choose or pay Rezi, ranked**
1. The download limit: 3 PDF downloads and 1 resume on Free, so anyone tailoring resumes per job hits the wall fast.
2. Fear of the ATS filter: "You're not getting ghosted by humans" plus a score and keyword targeting per job.
3. Borrowed authority and big numbers: "#1 by Forbes", 4.8 million users, "62.18%" against "~3%".
4. Low risk: free start, no card, 30-day full refund, and a one-time $149 option for people who hate subscriptions.
5. Free jobs map and app that hand each job straight into the resume tailor.

---

### 5. We Work Remotely (weworkremotely.com), job-seeker side

Large remote job board, paid by employers ($299 per post, `PRICING_RESEARCH.md` B.9). It also sells "WWR Pro" to seekers (a support article about its price existed by Oct 2024).
All weworkremotely.com pages answered 403 on 15 Nov 2026: **not opened**. Everything below is secondary unless marked.

1. **Main promise.** Not verified. Search results list the home page under the title "Free jobs by Toptal" (search, 15 Nov 2026); why Toptal is named was not verified. Its sponsorship page calls it "the largest remote work community in the world" (search snippet of https://weworkremotely.com/sponsorships-at-we-work-remotely).
2. **Landing pages.** robots.txt (read 15 Nov 2026) allows all but account pages and points to /sitemap.xml (403). Search shows `/categories/remote-<category>-jobs` (e.g. "Customer Support Jobs", "View all 81 Customer Support jobs", undated), `/remote-full-time-jobs`, `/remote-jobs/<company>-<title>`, `/remote-jobs/search?categories[]=7`, and weekly "Top 10 Remote Jobs" posts. Location tags such as "USA Only", "Anywhere in the World". No "$X/hour" or "no experience" pages found.
3. **Before any wall.** Secondary: browsing and full descriptions are free with no account; Apply usually goes to the employer's ATS (https://smartremotegigs.com/software/we-work-remotely/ , updated 5 Nov 2026). Not verified.
4. **How free value is limited.** Search snippet of the official FAQ: Pro perks are "unlimited applications, up to five custom alerts, and subscriber-only events". A third party lists the free tier as job feed, resume upload with "one free ATS resume review", saving jobs, following companies, LinkedIn verification, and says "There's no paywall to browse or apply at this level" (https://pitchmeai.com/blog/we-work-remotely-pricing-job-seekers). The "unlimited applications" perk suggests some cap on free applying: not verified.
5. **Price and terms.** Snippet of https://weworkremotely.com/job-seeker-faq : "WWR Pro — $14.95/month (12-month commitment, first month $2.95)". Snippet of https://weworkremotely.com/terms-and-conditions : "The Job Seeker Pro Subscription is a non-refundable annual subscription fee", payable up front or in monthly instalments; cancelling stops the next renewal, not the current 12 months. That is at least 12 x $14.95 = $179.40 a year (my arithmetic; a Trustpilot reviewer says "~$180"). An older support article says $9.99 a month (https://support.weworkremotely.com/how-much-does-the-pro-job-seeker-account-cost , Wayback snapshot of 8 Oct 2024 exists but could not be fetched). The FAQ also lists Pro "Value: $14.95/month" next to "Toptal Marketplace ... Value: $100+/month" (search snippet): a value stack.
6. **Trust claims.** "+6M monthly visitors" (sponsorship page, snippet); older pages say 4.5M. A third party presents the $299 post fee as a filter against scam posts (smartremotegigs). Not checkable here.
7. **Social proof.** Trustpilot 2.9 from 273 reviews: 47% five-star and 43% one-star (https://www.trustpilot.com/review/weworkremotely.com , read 15 Nov 2026). Most five-star reviews thank support for cancelling or refunding ("The refund process was incredibly easy", 12 Nov 2026; "I accidentally signed up for the annual plan instead of the monthly one", 11 Nov 2026), and two name the same agent. That pattern suggests reviews are requested after support tickets (not verified). The company answers one-star reviews with the same template ("apologized, asked user to check inbox").
8. **Onboarding.** Reviews describe "trial period screens" that do not show the annual term: "locks you into an annual subscription which is nowhere on the trial period screens" (17 Oct 2026); "$3 first month led to a yearly plan billed monthly" (8 Oct 2026). Exact questions not verified.
9. **Email capture.** Pro sells "up to five custom alerts"; whether free users get alerts is not verified.
10. **At sign-up.** A Pro offer at a $2.95 (also seen as $3 and $29 in reviews) first month; a free account can be finished without paying (secondary, https://bestjobsearchapps.com/articles/en/is-we-work-remotely-worth-it-in-2026-fees-and-user-reviews).
11. **Free vs paid.** Basic vs Pro (third parties). Headline Pro benefit in the FAQ: "Access to the largest remote job board", plus alerts, events, AI "Job Copilot" (secondary), and a Toptal AI resume builder (smartremotegigs).
12. **Complaints** (Trustpilot pages 1 and 2, read 15 Nov 2026): the small trial is really month one of a 12-month contract ("they hid the fact that it was actually a mandatory 12-month commitment", 3 Oct 2026); no cancel button ("If you see 'Re-enable' instead of a cancel button", 8 Oct 2026); billed after a written cancellation (2 Nov 2026); irrelevant or poor jobs and mobile filters that freeze.

**Why people choose or pay WWR, ranked**
1. Brand and size: "the largest remote work community", millions of visits, and employers paying $299 a post, which reads as "real jobs".
2. A tiny first price ($2.95) that looks like a trial: the main reason people end up paying, judging by the reviews.
3. Fear of missing jobs: "unlimited applications" and five custom alerts are framed as Pro.
4. A bundle that looks worth more than it costs (Toptal Marketplace "Value: $100+/month").

---

### 6. Himalayas (himalayas.app), incl. Plus and Max

Remote job board with AI career tools. Seeker pays for Plus ($9) or Max ($29).

1. **Main promise.** Home h1 "Get matched with your next remote job. Then land it with AI."; sub-line "Your AI agent finds remote roles that fit, tailors your resume, preps you for interviews, and tracks every application — all from one free profile."; buttons "Sign up with Google", "Get started for free", "No credit card required". Plus page: "The best AI job search tools. Land your dream job. Without stress." with "Get started for free". https://himalayas.app/ , https://himalayas.app/plus , read 15 Nov 2026.
2. **Landing pages.** robots.txt lists 28 sitemaps (read 15 Nov 2026). Counted: 18,439 skill or category pages `/jobs/<keyword>` (incl. `/jobs/data-entry`, `/jobs/customer-service`, `/jobs/remote-customer-service-representative`), 3,555 market pages `/jobs/markets/<market>`, 286 country and location pages, 202 time-zone pages `/jobs/timezones/<zone>`, and three files of country x keyword pages `/jobs/countries/<country>/<keyword>` (the first alone has 50,000). Plus company salary, tech-stack and benefit pages, resume and cover-letter examples, interview questions, remote-work statistics. `/jobs/data-entry` (WebFetch, 15 Nov 2026): h1 "Remote Data Entry Jobs", "There are 1,837 open remote Data Entry jobs on Himalayas.", rows with company, country limit, hourly pay ("$18.00 – $25.00 per hour"). curl got a Cloudflare check on /jobs pages the same day.
3. **Before any wall.** Titles, companies, country limits and pay are public. Docs: "Job seekers are never charged to browse or apply"; "You apply directly to companies". Saving needs an account ("Sign up to save this job", `COMPETITOR_GAPS.md`). "Sponsored" rows for an AI-apply product were seen inside the job list earlier (`COMPETITOR_GAPS.md`); none on the data-entry page today.
4. **How free value is limited.** Free: weekly alerts, "1 free resume", "1 free cover letter", "1 free mock interview", "1 free coaching session", no voice interview, headshots "Subscription required". Plus: daily alerts, all unlimited, "Conversational AI interview 30 minutes/month". Max: "4 hours/month". (https://himalayas.app/pricing , https://himalayas.app/docs/himalayas-plus)
5. **Price and terms.** Plus "$9 / month", Max "$29 / month", "Both plans renew monthly. You can cancel at any time and keep access to Plus features until the end of your current billing period." Self-service cancel via "Manage subscription". Refund: "If you're not happy with your purchase, we're happy to refund you. All we ask is that you don't abuse this." and on /plus "we offer a 100% money-back guarantee". FAQ: "Cancel any time—there's no lock-in". The paid plan buttons read "Get started for free".
6. **Trust claims.** "Every job is checked for spam and scams before it's listed, and jobs from new employers are reviewed by a person before they go live" (https://himalayas.app/docs/is-himalayas-legit). Against that: the data-entry page's first rows are typical bait titles ("Remote Data Entry Operator (Entry Level)", "Remote Work From Home Data Entry - Typist - Entry Level"), and one Trustpilot review says "To many scam jobs" (not verified as scams). Numbers disagree: home "Join 1,000,000+ job seekers"; docs "600,000+ job seeker profiles"; pricing "database of 600K+ remote-ready candidates". "100,000+ live remote jobs", "70,000+ company profiles". Employer claim "Over 10x apply clicks" is footnoted with its method (median, 1,000+ jobs, Apr–Oct 2026): a good example.
7. **Social proof.** Five stars "★★★★★" printed next to "Join 1,000,000+ job seekers" with no source. Trustpilot: 3.2 from 7 reviews, unclaimed (https://www.trustpilot.com/review/himalayas.app , read 15 Nov 2026). Mock-ups use invented "98% match" rows with real company names (Linear, Vercel, Stripe) and a resume for "Sarah Johnson ... Google"; these are product illustrations, not notifications. "We contribute 1% of every payment to remove CO₂" (Stripe Climate) as a values signal.
8. **Onboarding** (https://himalayas.app/docs/getting-started-job-seekers): sign up with email (name, email, password, one-time code) or Google; then "Upload your resume (optional)" which pre-fills the profile; then "Explore Himalayas Plus (optional): ... You can subscribe now or skip". Profile: username, location, intro, bio, timezone, photo, experience, education, tech stack.
9. **Email capture.** Sign-up is the capture: "join over 1,000,000+ remote workers who receive personalized job alerts". Free alerts are weekly; daily needs Plus.
10. **At sign-up.** A Plus offer inside onboarding. Docs say "The platform never asks for payment information during signup", but two Trustpilot reviewers say payment was pushed during registration with a hard-to-find skip button (Sep and Aug 2026).
11. **Free vs paid.** Three columns (Free, "Recommended" Plus, Max) with a row-by-row table; the same table in the docs. Headline paid benefit: "unlimited AI tools and daily alerts".
12. **Complaints** (Trustpilot, 7 reviews only): payment pushed in sign-up; a "remote global" job that was really Lithuania only; "To many scam jobs"; slow forms and forced title formats.

**Why people choose or pay Himalayas, ranked**
1. A large free remote board with country and time-zone limits on every row, so people come for free search.
2. AI documents per job: one free resume, cover letter and mock interview, then $9 for unlimited.
3. Speed: daily instead of weekly alerts is a paid feature.
4. Low, cancel-any-time price with a refund promise and no lock-in.
5. Voice mock interviews (Max) for interview anxiety.

---

### 7. Indeed (indeed.com), job-seeker side

Largest general job site; employers pay. A small seeker subscription exists in one market.
Job search pages, home, /about, /career and help on zendesk answered 403 or "Security check" on 15 Nov 2026: **not opened**.

1. **Main promise.** Home not opened. App Store (https://apps.apple.com/us/app/indeed-job-search/id309735670 , read 15 Nov 2026): subtitle "Find Jobs, Build Your Career"; "the free job search app designed to connect you with better work anytime, anywhere"; "Uncover what a job pays before you apply with more than 1.1 billion salaries". Earlier: "the world's #1 job site" (Comscore, March 2026) and "685M Job Seeker Profiles" (https://www.indeed.com/about , 14 Nov 2026, via `compare_sites.py`).
2. **Landing pages.** robots.txt (read 15 Nov 2026) lets search-engine and AI-search bots crawl everything except `/viewjob`, `/job/`, alerts and account paths; AI-training bots (GPTBot, CCBot, anthropic-ai) are blocked from `/q-`, `/l-`, `/jobs`, `/cmp/`, `/career/`, `/career-advice/`. So the indexed query pages follow `/q-<keywords>-jobs.html`, `/q-<keywords>-l-<place>-jobs.html`, `/l-<place>-jobs.html`, plus `/cmp/<company>` and `/career/<title>/salaries`. No sitemap at /sitemap.xml (404). What these pages show was not verified today.
3. **Before any wall.** Not verified. Help: "Some jobs let you apply directly on Indeed. Others take you to the employer's website." and the first step is "Create an account or sign in." (https://www.indeed.com/help/job-seekers/articles/204652920-applying-for-a-job-on-indeed , read 15 Nov 2026).
4. **How free value is limited.** Search and applying are free. Inside the app, non-subscribers get "1 free Tailored Resume and 1 free Mock Interview" (search snippet of Indeed's help centre, indeed.zendesk.com article 33811263593101, not opened).
5. **Price and terms (Indeed Pro).** Terms (https://www.indeed.com/legal , read 15 Nov 2026): "Indeed Pro is a Beta service ... has limited availability, and is available only in certain countries. You may be offered a free trial". Features: "Top Applicant Feed", "Top Choice credits", "Applicant Insights", "Who Viewed My Profile". Paid through Apple, "Your subscription will renew automatically monthly", "Indeed Pro subscriptions are non-refundable, except as required by law", "No refunds will be issued for partial months." Help snippet: 7-day trial, then "CAD 9.99 + tax", "only available in Canada (excluding Quebec)", iOS only, up to three Top Choice marks a month, and Top Choice "doesn't affect the order in which an application appears to employers". The Canadian App Store listing shows in-app items "Indeed Pro $9.99" and "Indeed Pro exclusive offer $2.99" (search snippet). The US App Store page lists no in-app purchases. "Indeed Smart Apply" was not found under that name; the closest are "Apply with Indeed" / "Easily apply" and the employer-side "Smart Screening" with a "Smart Fit Score" (search, 15 Nov 2026).
6. **Trust claims.** Terms disclaim job accuracy: "Indeed cannot guarantee ... the accuracy, completeness, legality, reliability, legitimacy ... of such content" and the identity of employers. Trustpilot reviewers report ghost and fake listings (below).
7. **Social proof.** App Store 4.8 from 4.1M ratings vs Trustpilot 1.8 from 13,112 reviews (claimed, does not invite reviews) (https://www.trustpilot.com/review/www.indeed.com , read 15 Nov 2026). The gap is typical: in-app prompts vs complaint-driven web reviews.
8. **Onboarding.** Account; resume upload or Indeed Resume; "In some cases, you may need to verify your phone number"; employer screener questions; an offer to "Tailor your resume" during applying (help article above).
9. **Email capture.** Job alerts: "You must be signed in to your Indeed account to create job alerts." The search page has an email field at the bottom of the first results page, or "a pop-up to create a job alert instead ... select Activate"; daily or weekly (https://www.indeed.com/help/job-seekers/articles/204488890-starting-stopping-and-managing-job-alerts , read 15 Nov 2026). Indeed can also scan a linked email inbox to update "My jobs" (terms).
10. **At sign-up.** The profile can be shown to employers: by creating a profile or resume "you authorize Indeed to make it available to potential Employers and users of Indeed's Smart Sourcing"; the user picks "Employers can find you" or "Employers can't find you" (terms). Which is the default was not verified. "Indeed may contact you ... on behalf of Employers or Indeed itself."
11. **Free vs paid.** No public comparison page found. The paid tier's headline benefit is signalling: "Top Choice" marks and "Top Applicant" jobs, i.e. a hint of standing out.
12. **Complaints** (Trustpilot, newest 20, Nov 2026): irrelevant matches and spam alerts ("Lots spam and irrelevant jobs"); fake and ghost listings ("There are thousands of fake jobs listed on here", 14 Nov 2026); scam calls after giving a phone number ("they sold it to HEALTH insurance companies", 3 Nov 2026; Indeed replies it does not sell data); "'Apply on Indeed' is not an application. It's a lead form for a second application." (11 Nov 2026).

**Why people choose Indeed (and the few who pay), ranked**
1. Size and habit: the biggest pool of jobs, including local, hourly and entry-level work that niche boards lack.
2. Quick applying with a stored resume ("Easily apply"), and pay shown or estimated before applying.
3. Daily or weekly email alerts once signed in.
4. For Pro (Canada, iOS): a cheap way to feel noticed (Top Choice, "Who Viewed My Profile"), sold through a free trial.

---

### Patterns across these 7 that drive payment

1. **The job is free, the help is paid.** Wellfound, Indeed, Himalayas, Teal and Rezi never charge to see or apply. They charge for unlimited AI resumes, cover letters, scores and mock interviews. The free plan gives exactly one of each (Himalayas: 1 resume, 1 letter, 1 interview, 1 coaching; Indeed: 1 tailored resume, 1 mock interview; Rezi: 1 resume, 3 PDF downloads; Teal: a small non-renewing credit pool; Hirify: 3 matches). One free use proves value; the second use is the paywall.
2. **Hiding the employer.** Hirify is the only one of the seven that sells job access: company name and apply link hidden on 70,000 international jobs. It works because the data looks visible (title, pay, tags) and only the last step is locked.
3. **Per-job tailoring against ATS fear.** Rezi ("You're not getting ghosted by humans"), Teal (keyword match), Himalayas (job-specific resume), Indeed (tailor during apply). The message: your resume is filtered by a machine, pay to beat it.
4. **Speed and volume framed as paid.** Daily vs weekly alerts (Himalayas), five custom alerts and "unlimited applications" (WWR Pro), "unlimited" everything.
5. **Low first price, recurring after.** WWR $2.95 first month into a 12-month contract; Teal $13 a week; Indeed Pro 7-day trial then monthly through Apple. The cheapest-looking entry produces the most complaints (WWR 2.9 on Trustpilot, half the newest reviews about lock-in).
6. **Borrowed authority and big counters.** "Forbes #1" with no link, "4,785,497+", "1,000,000+", "27,000+ startups", "213 000+", star rows with no source, "3500+ already on Plus". Several of these disagree with the same site's other pages.
7. **Risk removers.** "No credit card required", "Cancel any time", money-back guarantees (Rezi 30 days, Himalayas 100%), one-time payments (Hirify, Rezi Lifetime). These are the honest version of point 5.
8. **Being found instead of applying.** Wellfound spotlight and AI sourcing, Indeed searchable profiles, Himalayas talent directory. Free here, but it is why people hand over a full profile.

### What we must never copy

1. **A trial that is really an annual contract** (WWR: "$2.95 first month" inside a non-refundable 12-month term, no cancel button). Any paid plan of ours: price stated in full, nothing renews, nothing to cancel.
2. **Mock notifications with fake interview invites and pitches** using real company names (Wellfound: "Interview booked · just now", "Founder pitched you", "Interview confirmed: Zipline · Tuesday, 2:00 PM"). If we show a product picture, label it as an example and use invented companies.
3. **Unattributed or unsourced ratings and testimonials**: Wellfound's "Candidate"/"Recruiter" quotes, Himalayas' bare "★★★★★", Rezi's "8.23/10" and three different ratings on one page, Hirify's Telegram-handle quotes and "3500+" counter.
4. **Award and success claims without a link**: "Ranked #1 by Forbes", one number with two meanings ("62.18% interview rate" vs "62.18% review rate").
5. **Discount chips that do not match the arithmetic** (Hirify "-27%" and "-63%" vs 17% and 58% real).
6. **Hiding the employer name or apply link behind a payment** (Hirify Plus). It also leaks (the FICO example), so it is both unfair and leaky.
7. **"Checked for scams" claims we cannot back**, next to bait listings (Himalayas data-entry rows; the same "SkillersZone" employer shows $18–25/hour on one site and $75,000–$120,000 on another).
8. **Pushing a payment step inside sign-up**, and "Get started for free" on a paid plan's button (Himalayas).
9. **Years in titles that have not arrived yet** ("Jobs in 2027" in November 2026, Wellfound).
10. **Counts that disagree across our own pages** (Hirify 2 vs 3 hours; Himalayas 1,000,000+ vs 600,000+; Hirify 700+ vs 20,000+ sources). Every number on our site must come from the build, with a date.
11. **Making the profile visible to employers by default, or selling contact data** (the most damaging Indeed complaint, whether true or not). Anything like a talent pool must be opt-in.
12. **Asking for reviews only after a support rescue** and replying to complaints with one template (WWR pattern, not verified as policy).

### Not opened or not verified

- tealhq.com (all pages, help centre), weworkremotely.com (all pages, support), indeed.com job and company pages, indeed.zendesk.com: 403 or bot check on 15 Nov 2026. web.archive.org could not be reached from this machine (connection reset), so no snapshots were read.
- Himalayas /jobs pages gave curl a Cloudflare check; one page was read with WebFetch.
- Not verified: Teal's home headline and onboarding questions; WWR's current home text, Pro checkout screens and whether free applying is capped; the "Free jobs by Toptal" link between WWR and Toptal; Indeed Pro outside Canada; what Indeed's `/q-...-jobs.html` pages show; the Forbes ranking Rezi claims; Wellfound's 130k jobs; whether Indeed profiles are searchable by default.
