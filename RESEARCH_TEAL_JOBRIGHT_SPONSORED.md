# Teal, Jobright, Indeed/Glassdoor Sponsored Jobs: what to copy, and a $1M/year plan

Read on **15 Nov 2026** using WebSearch and WebFetch only. No browser tool was used.

**How sure each fact is:**
- **[opened]**: I fetched and read the page.
- **[search]**: the fact comes only from a search-result summary.
- **[3rd]**: a third-party page (review site, tracker, vendor blog) that I opened.
- **[unverified]**: sources conflict, or the number is someone's estimate.

**Pages that blocked me.** I did not try to get around any of these blocks.
- **Teal:** tealhq.com returned HTTP 403 for every page I tried: /pricing, /sitemap.xml, /tools and help.tealhq.com. Instead I used:
  - Teal's help center on intercom.help, which opened;
  - search snippets of Teal pages;
  - reviews, press and the Chrome Web Store.
  - The Teal prices also agree with `PRICING_RESEARCH.md` §A.9, where an earlier session opened tealhq.com/pricing on 13 Nov 2026.
- **Jobright:** jobright.ai/pricing returned 404, so its seeker prices come from third-party reviews.
- **Indeed:**
  - indeed.com/hire/pricing served a Vietnamese page. The US version, /hire/cs/pricing?co=US, opened.
  - /employers/sponsored-jobs and /employers/smart-sourcing returned 404.
- **Business Wire:** returned 403.

**Teal page counts.** The sitemap was blocked, so I could not count Teal's SEO pages. The counts below are Teal's own claims, such as "2,000+ resume examples".

---

## 0. Where we stand (for comparison)

Sources: `SEO_MAP.md`, `config.json` and `assets/site.js`, all read on 15 Nov 2026.

**What we already have:**
- Pages: 166 role pages, 86 location pages, 244 salary pages, 113 skill pages and 734 company pages.
- Per-role page families for about 143 roles: resume examples, cover-letter examples, interview questions, job descriptions, how to become, and how to hire.
- 33 free tools, including resume match, resume review, LinkedIn review, cover letter, offer check, negotiation email and take-home pay.
- Skill tests, a career quiz and a glossary.
- The "My jobs" tracker with five statuses (Saved, Applied, Interviewing, Offer, Not moving forward), notes and a follow-up reminder file (.ics).
- Visa terms detected in the posting text, and a `/perks/visa-sponsorship/` page.

**Money is not switched on.** It cannot come in yet:
- `config.json` has `"plus": {"live": false}` and every wallet address is empty.
- `api_url` is empty, so there are no accounts, no email alerts and no AI features.

**Prices today are launch prices:**
- Plus: $3 for 1 month, $7 for 3 months, $12 for 12 months.
- Employers: featured $29, pinned $59, 5-job pack $119, spotlight $149/month, category sponsor $89/month, branded listing $49.

---

## 1. Teal (tealhq.com)

### 1.1 Facts and numbers
- **Users and team, January 2025:** "over 2 million members", "over 100,000 paying Teal Plus users", 30 employees on a fully remote team, about 30% of members outside the US, and $19M raised in total ($7.5M Series A). Source: Refresh Miami, 22 Jan 2025 [opened]: https://refreshmiami.com/news/teal-raises-7-5m-to-expand-ai-powered-career-platform/
  - New tools announced in the same article: an AI Interview Coach, an Offer Evaluation tool and Negotiation Support.
  - Plans named in the article: "a job board that is not paid for by employers", and AI agents that do career tasks for the user.
- **Members, late 2025:** about 4 million [search, unverified].
- **Revenue, 2024:** $4.2M according to CB Insights [search, estimate].
  - **This does not fit the "100,000 paying" figure.** 100,000 subscribers at $29 a month would be more than $30M a year. So "100,000 paying" is probably everyone who has ever paid, not the number paying today. I could not verify either figure.
- **Acquisitions:**
  - Ramped, on 11 Dec 2025. Its "Autopilot" tool tailors and submits applications, and it is being built into Teal [opened]: https://www.privsource.com/acquisitions/deal/EMS9D2
  - Earlier: Riva (salary-negotiation coaching, 2023) and OwnTrail (date not found) [search].
- **Chrome extension:** about 200,000 users, rated 4.9 from about 3.1K ratings, and named a Chrome Web Store "Favorite of 2023" [search]: https://chromewebstore.google.com/detail/opafjjlpbiaicbbgifbejoochmmeikep
- **Organic traffic:** about 523K organic visits a month from about 724K keywords. This is an AirOps estimate seen only in a search summary [search, unverified]. When I opened the AirOps page itself, it no longer contained Teal data.

### 1.2 Prices
| Plan | Price | What it includes |
|---|---|---|
| Free ("Free Forever") | $0 | Unlimited resumes, unlimited job tracking, 11 templates, limited daily AI credits. The summary generator is limited to 2 AI summaries. |
| Teal+ weekly | **$13 every 7 days** (about $56 a month) | The same features as every Teal+ plan |
| Teal+ monthly | **$29 every 30 days** | Unlimited AI resume and cover-letter text, full keyword matching, tailoring to a specific job, a resume score with ATS feedback |
| Teal+ quarterly | **$79 every 90 days** (about $26.33 a month) | The same |

- There is no annual plan. Payments renew automatically, and cancelling takes effect at the end of the paid period.
- An older Teal blog post quoted "$9 per week".
- Sources:
  - https://frontdeskreview.com/software/resume-builders/teal.md [3rd, checked there 26 Sep 2026]
  - https://makerstack.co/reviews/teal-review/ [3rd, 20 Jul 2026]
  - `PRICING_RESEARCH.md` §A.9 (tealhq.com/pricing opened 13 Nov 2026)

### 1.3 Teal features we likely lack (one line each)
1. **Chrome extension that saves any job from any site** (LinkedIn, Indeed, company careers pages) into the tracker. Our tracker only saves jobs on our own site.
2. **Contact tracker:** recruiters and hiring managers linked to each job, with follow-up dates. Help center: https://intercom.help/tealhq-9a9274919b13/en/
3. **Company tracker:** a list of target companies with notes and status.
4. **LinkedIn profile review that reads the profile directly** through the extension: photo, headline, summary and skills. Our /tools/linkedin-review needs the text pasted in. Source: https://tealhq.helpscoutdocs.com/article/40-reviewing-your-linkedin-profile [search]
5. **"Matching mode" inside the builder:** a specific resume version is scored against a specific saved job, and the missing keywords are shown inline. We have a stand-alone /tools/resume-match that is not linked to My jobs.
6. **Several resume versions per job**, each one tailored to one posting and kept with that job.
7. **AI writing:** achievement bullets, summary, skills, headline, and an email or cover letter tied to one job and one resume. This needs Plus and a server.
8. **AI interview coach:** "Interview Hub", "Mock Mode" (the AI asks follow-up questions, then gives feedback), a "Scenario Library", and questions taken from the job description. Our /interview-practice has no AI feedback. Source: https://help.tealhq.com/en/articles/14435728-how-to-prepare-for-interviews-using-teal [search]
9. **Career goal tracker:** set career goals and track progress against them [search].
10. **Work Styles assessment:** 17 questions based on DISC, plus a **"360" option that invites colleagues to rate you**, which brings new people to the site. Also a career personality test at /tool/career-personality-test [search].
11. **Autopilot:** submits applications for the user (from Ramped). **Do not copy the sending part.** `COMPETITOR_GAPS.md` explains that mass auto-apply floods employers and gets tools blocked. Copy autofill only: the extension fills the form and the user presses submit.
12. **Webinars and virtual events, a newsletter** (Teal cites "500K+" readers [search]), and a "Teal stories" success-story category.
13. **Excitement rating and more stages** (for example Applying and Negotiating) on each tracked job. This is a small addition to our five statuses.

### 1.4 Teal page types (SEO). ✅ = we have it, ⚠️ = partly, ❌ = missing
| Teal URL pattern | What it is | Teal's claimed size | Us |
|---|---|---|---|
| `/resume-examples/{role}`, `/resume-example/{role}` | Example resume per role | "2,000+" | ⚠️ about 143 roles |
| `/resume-templates/{style}` (e.g. /resume-templates/technical) | Template landing pages by style or field | "100+ templates" | ❌ our templates exist only inside the builder |
| `/cover-letter-examples/{role}` | Cover-letter example per role | "1,500+" | ⚠️ about 143 roles |
| `/interview-questions/{role}` | Questions and sample answers per role | not stated | ✅ 144 |
| `/career-paths/{role}` | Career path: steps and years of experience | not stated | ✅ /how-to-become/ (144) |
| `/career-paths/{role}-certifications` and `/certifications/{role}` | Best certifications for a role | not stated | ❌ |
| `/career-paths/{role}-interview-questions` | A second, duplicate interview page | — | not worth copying (duplicate content) |
| `/skills/{role}` (e.g. /skills/software-engineer) | Skills a role needs, for the resume | not stated | ❌ our /skills/ pages go the other way: skill → jobs |
| `/professional-goals/{role}` | Example professional goals per role | not stated | ❌ |
| `/job-titles/{role}` | Job-title guide: levels, similar titles, what the title means | not stated | ⚠️ partly covered on role pages |
| `/best-resume-builders/{role}` | "Best resume builder for {role}" | not stated | ❌ |
| `/tool/{name}` | Single-purpose generators: resume bullet points, summary, headline, skills, career personality test, … | about 15–20 | ⚠️ we have 33 tools; missing are a summary generator, a resume-headline generator, a personality test and a skills generator (we have job-description keywords) |
| `/post/{slug}` + `/category/{resume, interviews, job-search, teal-stories}` | "Career Hub" blog | hundreds of articles (from search results) | ⚠️ we have /guides/ with about 12 |
| `/job/{slug}` | Job pages from Teal's own job board | not stated | ✅ /job/ |
| `/women-led-companies` | Curated list of companies | 1 | ❌ (needs a trustworthy data source) |
| `/careers/{role}` | Teal's own job openings | — | n/a |

Sources for page patterns: search results for site:tealhq.com, for example
- https://tealhq.com/resume-examples
- https://tealhq.com/cover-letter-examples/marine-engineer
- https://tealhq.com/certifications/teacher
- https://tealhq.com/professional-goals/software-engineer
- https://www.tealhq.com/job-titles/director-of-user-experience
- https://www.tealhq.com/best-resume-builders/chief-talent-officer
- https://tealhq.com/tool/resume-summary-generator

All [search].

**How Teal grows** (as far as can be seen without the sitemap):
- Per-role page families. They have about 10 page types per role; we have 6.
- A large blog.
- Free tools that require a free account. A free account then becomes Teal+ when the daily AI credits run out.
- The Chrome extension.
- Buying products that bring their users with them (Riva, OwnTrail, Ramped).

---

## 2. Jobright (jobright.ai)

### 2.1 Facts and numbers
- **Company:** founded 2023 in Santa Clara. Co-founder Eric Cheng was an early engineer at Box. Source: TechCrunch, 25 Jun 2024 [opened]: https://techcrunch.com/2024/06/25/jobright-uses-ai-to-help-foreign-workers-navigate-the-us-job-market
- **Early users:** about 50,000 two months after the April 2024 launch. About 30% were foreign workers, mainly from India and China. **Growth came without marketing spend; the H-1B filter was the main draw** [opened, TechCrunch].
- **Funding:** about $7.7M raised. That is a $4.5M seed round (Lanchi Ventures) plus $3.2M in June 2025 (Translink Capital, with Indeed's venture arm taking part) [search].
- **Revenue:**

| When | Figure | Source |
|---|---|---|
| Dec 2024 or mid-2025 (sources disagree) | $1M ARR | ARR Club / Latka |
| 28 Feb 2026 | **"$430K+ MRR" with 9 people** | Henry Shi's newsletter [opened]: https://henrythe9th.substack.com/p/how-jobright-hit-5m-arr-with-9-people |
| Jun 2026 | $7M ARR | ARR Club |
| 2 Oct 2026 | $8M ARR | ARR Club |
| **13 Oct 2026** | **$10M ARR** | Co-founder's LinkedIn post, as quoted by ARR Club [opened]: https://www.arr.club/signal/jobright-arr-hit-10m-up-from-1m-in-10-months — the LinkedIn post itself was not opened |

- **Users:** "3,000,000" users claimed on the home page [opened]. ARR Club also cites "2M job seekers globally".
- **How they run growth:** "Almost all growth was organic" in the $1M phase, driven by referrals. Every step of the funnel has one owner metric. Cost per new customer is tracked by channel, and channels that miss the payback target get throttled. Experiments must ship or be killed within 7 days [opened, newsletter].

### 2.2 Prices
**Job seekers.** These prices are from August 2026 reports, because jobright.ai/pricing returned 404:

| Plan | Price | 2025 price |
|---|---|---|
| Free | $0 | |
| Turbo weekly | **$17.99** | was $14.99 |
| Turbo monthly | **$39.99** | was $29.99 |
| Turbo quarterly | **$89.99** | was $69.99 |

- A 6-month plan is named in the refund policy, but its price is not known.
- **.edu sign-ups got Turbo "for half the price"** (founder AMA, 2025) [3rd].
- **Free-plan daily limits:**
  - 2 AI-tailored resumes;
  - 4 one-click autofills;
  - 2 AI cover letters;
  - 2 email-finder lookups;
  - 1 instant job alert;
  - 1 saved filter.
  - Orion chat is unlimited. Turbo makes the other limits unlimited, and the limits reset at midnight [3rd].
- **Interview-question packs are sold separately:** **$19.99 for one company for 7 days**, or **$39.99 for all companies for 30 days** [3rd].
- Sources:
  - https://careery.pro/blog/ai-job-search/jobright-ai-review [3rd, Oct 2026, quoting FavTutor 21 Aug 2026 and Jobity 31 Aug 2026]
  - https://jobstrack.io/blog/jobright-review-2026 [3rd, 15 Oct 2026]

**Employers** [opened]: https://jobright.ai/employers/pricing
- **AI Recruiter: $499 per recruiter per month.**
  - One recruiter works on one active role at a time.
  - It sources and checks candidates, contacts them, and delivers "10 to 20 interview-ready candidates every week", synced to the employer's ATS (applicant tracking system).
  - Two-week free trial with no card.
- An annual plan with several roles at once is priced only on request.
- Jobright claims a 15% reply rate against 4–5% for cold outreach, and "120+ companies hired" [opened, ARR Club].

### 2.3 Jobright features we likely lack (one line each)
1. **A match score on every job card, with the reason** (we have matching only on /for-you/). Source: https://jobright.ai/jobs/h1b-visa-sponsored-software-engineer-jobs-in-united-states [opened]
2. **Signals on each job card:** "Early applicant", applicant count, "H1B Sponsor Likely", "Unicorn", "Top Investors", "Culture & Values", "Comp. & Benefits" [opened].
3. **H-1B sponsorship history per company,** from US Department of Labor data, with yearly counts and job fields. The "Sponsor Likely" label means the company sponsored similar roles in the last 3 years [opened]: https://jobright.ai/h1b-jobs
4. **One-click autofill extension** for the major applicant-tracking systems. About 200K users and 4.7★ per a tracker [3rd, unverified]: https://jobright.ai/job-autofill
5. **"Tailor my resume to this job" in about 6 seconds,** straight from the job card [opened].
6. **Insider Connections:** the user connects LinkedIn; Jobright suggests alumni and past colleagues on the hiring team, finds their email addresses, and writes the outreach message [opened]: https://jobright.ai/job-referral
7. **Orion:** an AI career chat for resume help, interview prep and company insights [opened]: https://jobright.ai/orion-copilot
8. **AI Agent that applies for the user,** launched June 2025. Free users get a waitlist; it is tied to Turbo [opened / 3rd]: https://jobright.ai/ai-agent. Copy autofill only, not the sending.
9. **Job tabs: Recommended, Liked, Applied, External,** and "early alerts" [opened].
10. **TNT (Top Talent Network):** a private profile that hiring teams review. Claims: "200,000+" talents and "150+" AI startups [opened]: https://jobright.ai/tnt
11. **For employers:** fake-candidate detection (/fake-candidate-detection) and the AI Recruiter [opened].
12. **Live career coaching** (charged per session in one test) [3rd].

### 2.4 Jobright page types
| Pattern | What it is | Us |
|---|---|---|
| `/jobs/info/{id}` | Job page | ✅ |
| `/jobs/h1b-visa-sponsored-{role}-jobs-in-{city-state}` and `...-in-united-states` | Lists of H-1B jobs by role, and by role plus city [opened] | ❌ |
| `/h1b-jobs` (+ `/blog/category/h1b/`) | H-1B hub with sponsor history | ❌ (we have /perks/visa-sponsorship/, based on posting text only) |
| `/entry-level-jobs`, `/remote-jobs` | Topic hubs, updated hourly, with an alert signup | ✅ (/entry-level/, /remote/) |
| `/tools/{tool}`: ai-job-assistant, cover-letter-generator, resume-helper, job-tracker, ai-job-apply, resume-tailor | Tool landing pages | ⚠️ we lack "resume tailor" and "AI job assistant" |
| Feature landing pages: /ai-resume-builder, /ai-job-match, /job-referral, /orion-copilot, /job-autofill, /interview-landing, /ai-agent | One page per feature, each with an FAQ | ⚠️ |
| `/blog/` incl. "Is Jobright legit?" and success stories | Blog, trust pages, rival reviews | ⚠️ |
| `/employers`, `/employers/pricing`, `/tnt`, `/partners` | Employer side | ⚠️ |
| Company pages | **Not found.** Company names on job cards are plain text, not links [unverified] | ✅ we have 734 (an advantage) |

### 2.5 How Jobright gets users (copyable)
- **A niche nobody served:** the H-1B filter brought in foreign workers and international students [opened, TechCrunch].
- **37 GitHub repositories with job lists updated daily,** for example:
  - "2026-Software-Engineer-New-Grad": 504★
  - "Daily-H1B-Jobs-In-Tech": 326★
  - "2026-Data-Analysis-Internship": 223★
  - internship lists by field (HR, legal, marketing and others), updated 15 Nov 2026
  - Source [opened]: https://github.com/jobright-ai
- **Sister sites:** intern-list.com, entrylevel-jobs.com and careerin.ai, all linked from /entry-level-jobs. Also custom GPTs in ChatGPT [opened].
- **Referrals and word of mouth,** a student discount, a Product Hunt launch, a "featured by OpenAI" badge, and accounts on TikTok, Instagram and YouTube [opened home page].

---

## 3. Indeed and Glassdoor: Sponsored Jobs and Premium Sponsored Jobs

### 3.1 How it works
**Pricing page** [opened]: https://www.indeed.com/hire/cs/pricing?co=US

**Tiers and what each adds:**
| Tier | What it adds | Indeed's claim |
|---|---|---|
| Free | Shown in search results, candidates managed on Indeed. "Some jobs must be sponsored." | — |
| Standard | Visibility boost, email advertising, a place in the job-seeker feed, automatic messages to candidates | "3X more applications than free" |
| **Premium** | First-page boost and priority over similar posts; advanced matching; **"Urgently hiring" label**; brand promotion (logo and images); **matched-candidate invitations ("invite to apply")**; SMS messages; targeting by skills, certifications, licences, degrees and location; promotion across Indeed's media network | "2X as often in top search results", "90% more quality applications" (Indeed's own US data) |
| **Premium Plus** (beta) | Automatic invites, **application scores and summaries**, gathering of licences and certifications, AI follow-up questions | — |

**How Indeed charges:**
- **Two billing models:**
  - **Pay per click (PPC):** "You may be charged when someone clicks to view your job post". Used with a daily budget.
  - **Pay per started application (PPSA):** charged when someone clicks to apply or starts an application. It depends on the account and market.
  - Source [opened]: https://www.indeed.com/hire/resources/howtohub/how-pricing-works-on-indeed
  - Pay per application, where an employer could reject an application within 72 hours and not pay, **ended 18 Dec 2023** [3rd].
- **The price is a live auction.**
  - Indeed recommends a budget from the job title, location and description.
  - The Premium price is always set above the Standard price.
  - The employer can set a custom amount above a minimum, and that minimum is different for each job [opened].
- **Budget and billing:**
  - The daily budget is an average. A job can spend up to 7.5× its daily budget in a week [3rd].
  - An invoice is sent on the 1st of the month or when spending reaches $500, whichever comes first.
  - First-time sponsors may get a $25 invoice to check the payment method.
  - **New US accounts get a $75 credit** for their first sponsored job [opened].
- **Free posts:** 3 free direct posts a month per US company, each live for up to 30 days [3rd]: https://100hires.com/indeed-job-posting-cost.html (updated 12 Oct 2026)

### 3.2 Prices
Indeed publishes no list price.

**Sponsored Jobs:**
- **Cost per click:** about $0.25–$5, most often $0.50–$3 (Vendr guide, Feb 2026) [3rd].
- **Starting point:** some guides say "$5 a day or $150 a month". 100hires says "there is no universal $5-a-day minimum"; one job needed $12 a day [3rd, unverified].
- **Typical spend:** Vendr's median is about $15,000 a year. Monthly bands are about $500–$2,000 for 1–10 roles and $8,000–$25,000+ for 50 or more roles [3rd].

**Smart Sourcing (résumé search):**
- Professional: **$400 a month or $3,840 a year for 100 contacts**, with extra contacts at $4 each (US page, as quoted in a search summary).
- 100hires instead gives $520 a month.
- Standard: $120 a month for 30 contacts.
- 14-day trial [search / 3rd, conflicting].

**Other employer products:**
- Hiring events: from $500 per event [3rd].
- Employer branding (Glassdoor Enhanced Profile plus Indeed Company Pages): **priced only on request**. One reported quote was **$15,000 a year** for a bundle covering 21–50 jobs; add-ons run about $500–$2,000+ a month [3rd, unverified].

### 3.3 Glassdoor
- Glassdoor's operations were folded into Indeed (announced July 2025).
- **Job posts now start on Indeed** and appear on Glassdoor either organically or as sponsored jobs. A sponsored Indeed job is shown on Glassdoor automatically.
- There is no separate Glassdoor price for job posts [search]: https://www.noon.ai/blog/articles/346-glassdoor-pricing-2026

### 3.4 Revenue facts (Recruit Holdings)
**Source:** "Full-Year 2025" release, dated 15 May 2026 [opened]: https://recruit-holdings.com/en/ir/library/upload/Recruit_202603Q4_summary_en.html

The fiscal year FY2025 runs from April 2025 to March 2026.

**HR Technology segment, FY2025:**
- Revenue: ¥1,458.4bn (+6.3%), or **US$9.674bn (+7.6%)**.
- EBITDA+S margin: **37.7%**, a record.

**US, FY2025:**
- Revenue: **$5.31bn (+8.8%)**.
- **Revenue per job in the US (Recruit calls it ARPJ): +17%.** This is the "+17%" figure.

**Q4 FY2025:**
- US revenue +19% to $1.41bn.
- US revenue per job **+25%**.

**FY2026 guidance:**
- US revenue $6.03bn (+13.6%), "based on an 18% increase" in US revenue per job.
- Growth expected from "further growth of Premium Sponsored Jobs".

**What this means:** Indeed's revenue grows mostly by charging **more per job** (the Premium tier, better matching), not by selling more jobs.

### 3.5 What a small board can copy with one-time crypto payments and no automatic billing
| Indeed feature | Our version (one payment, no auto-renew) |
|---|---|
| Sponsoring any job, including jobs Indeed found itself | **"Boost this job" on every job we already list** (about 130,000 from employers' careers pages). The company proves it owns the job (company email or DNS, already in `server/`) and pays once. We already hold the stock; nobody has to post anything. |
| Standard vs Premium | **Two fixed-price boosts, each for 30 days:** Standard (highlighted row, above free jobs in its lists, included in alert emails) and Premium (see the next rows). |
| Top-3 placement, "2X as often in top results" | Premium boosts rotate through the first 3 slots of matching search results, category, role and location pages. |
| "Urgently hiring" label | An "Urgently hiring" badge that the employer declares and that switches off by itself after 14 days. |
| Branding (logo, images) | Logo is already shown; add a cover image and a "why work here" block (the branded listing, $49 today, marked "soon"). |
| Invite matched candidates | One email per job to seekers who **opted in** and match it (role, place, pay), capped at for example 50 per job. Needs accounts and email. |
| Recommended budget | **Recommended tier per job**, from our data: how many similar open jobs exist in that role and place. |
| $75 credit for new accounts | First boost at half price, or the first 7 days free, for companies already listed with us. |
| Daily budget / pay per click | **Prepaid credit balance in crypto:** spent per day while the boost runs, unused credit kept, never charged automatically. Do it later; fixed 30-day boosts are simpler to sell first. |
| Premium Plus: application scores and summaries | Later: AI summary of each application for jobs posted on our site. |
| Performance report | Views and apply clicks per job (the counters already exist in `server/`), plus a public "proof of reach" number on /post-a-job/. |
| Smart Sourcing (résumé search) | Opt-in résumé search (ROADMAP §119): **contacts only with the candidate's consent**. Slow to build up, so it comes last. |
| **Not copyable** | Auction prices with monthly invoices (needs card billing); Indeed's media network. |

---

## 4. Revenue plan to reach US$1M+ a year

**Target:** $1,000,000 a year ≈ **$83,400 a month** ≈ $2,740 a day.

### 4.1 What the three companies charge (benchmarks)
| Product type | Benchmark |
|---|---|
| Seeker, per week | Teal $13 · Jobright $17.99 |
| Seeker, per month | Teal $29 · Jobright $39.99 |
| Seeker, per 3 months | Teal $79 · Jobright $89.99 |
| Interview pack | Jobright $19.99 for one company for 7 days · $39.99 for everything for 30 days |
| One sponsored job for 30 days | Indeed ≈ $5–$25 a day ≈ **$150–$750** · niche remote boards $299 (`REVENUE_RESEARCH.md`) |
| Small employer, monthly | Indeed $500–$2,000 for 1–10 roles · Jobright AI Recruiter **$499 per role** |
| Résumé search | Indeed $400–$520 a month for 100 contacts |
| Employer branding | Indeed/Glassdoor quote about $15,000 a year |

**Our launch prices are 3–13× below these benchmarks:**
- Plus at $3 a month is 1/10 of Teal's $29 and less than 1/13 of Jobright's $39.99.
- A featured job at $29 is a fraction of $150–$750.

At today's prices, $1M a year would need about **27,800 Plus purchases a month**. The plan below goes back to roughly the old "was" prices, still below Teal and Jobright.

### 4.2 Paid products, ranked by how fast they can bring money
| Rank | Product (one payment, no auto-renew) | Price | Why this price | Buyers per month for the target | Revenue a month |
|---|---|---|---|---|---|
| 1 | **Boost on an existing or posted job: Standard, 30 days** | **$99** | Below Indeed's ≈$150–$750 for 30 days and below niche boards' $299 | 200 | $19,800 |
| 1 | **Premium boost, 30 days** (top-3 slot, "Urgently hiring", cover image, invites to matched seekers, stats) | **$249** | Indeed's Premium is priced above Standard; still below WWR's top tier ($458) | 100 | $24,900 |
| 2 | **Hiring Pass, 30 days** (unlimited Standard boosts for one company, 3 Premium boosts, spotlight, stats) | **$499** | Same as Jobright's $499 per role per month; at the bottom of Indeed's $500–$2,000 a month | 40 | $19,960 |
| 3 | **Plus pass for seekers:** 7 days $9 · 30 days $19 · 90 days $39 (AI tailoring, cover letters, unlimited alerts, match score, interview feedback) | **average about $20** | 30–50% below Teal and Jobright, because there is no auto-renew and the cards ask for crypto | 800 | $16,000 |
| 4 | **Interview pack for one company** (questions, the company's pay and openings, practice) | **$9** (included in Plus) | Half of Jobright's $19.99 | 150 | $1,350 |
| 5 | **Company spotlight / category or skill sponsor, 30 days** | **$299 / $199** | Indeed and Glassdoor branding costs $500–$2,000+ a month | 10 + 10 | $4,980 |
| 6 | **Opt-in résumé search, 30 days, 50 contacts** | **$199** | About half of Indeed's $400–$520 for 100 contacts | 20 | $3,980 |
| | **Total** | | | | **≈ $91,000 a month ≈ $1.09M a year** |

**Arithmetic:**
- Boosts: 200 × $99 = $19,800 and 100 × $249 = $24,900.
- Hiring Pass: 40 × $499 = $19,960.
- Plus: 800 × $20 = $16,000.
- Interview packs: 150 × $9 = $1,350.
- Spotlight and sponsor: 10 × $299 + 10 × $199 = $4,980.
- Résumé search: 20 × $199 = $3,980.
- Sum: $90,970 a month × 12 = **$1,091,640 a year**.

**What these numbers require:**
- **Employers (ranks 1–2):** 340 purchases a month, about 11 a day.
  - We already list jobs from thousands of companies, so the buyers are known and can be contacted by email. Letters need the owner's go-ahead.
  - Evidence from small boards is sobering: Remote Rocketship sold one post at 60,000 visitors a month (`REVENUE_RESEARCH.md`). Employers pay once they can see applications coming from us. So **show apply-click numbers per company first**, and sell boosts with those numbers in the letter.
- **Seekers (rank 3):** 800 buyers a month.
  - At 0.3% of monthly visitors buying (crypto only, my assumption) that needs about 270,000 visitors a month.
  - At 1% (if cards were possible) it needs about 80,000.
  - Teal reached "100,000 paying" from 2M+ members (≈5%, probably counted since launch).
- **Fallback if seekers will not pay in crypto:** employers alone at 450 boosts (average $150) + 50 Hiring Passes = $67,500 + $24,950 = $92,450 a month ≈ $1.11M a year.

**Rough check against Teal and Jobright:**
- Teal: about $4.2M a year (2024 estimate) from about 523K organic visits a month ≈ $0.67 per visit (estimates only).
- At that rate, $1M a year needs about 125,000 visits a month. That is Teal's rate, with cards and auto-renewing subscriptions; ours will be lower.
- Jobright made $10M a year from about 3M users ≈ $3.3 per user per year.

**Biggest risks, stated plainly:**
1. **No payment can be taken today:** wallets are empty, Plus has `live: false`, and `api_url` is empty. Revenue is $0 until checkout and automatic activation run in production.
2. **Paying only in crypto** will cut seeker conversion hard, because most US job seekers do not hold crypto. Employers in tech and crypto are likelier to pay this way. That is one reason the plan leans on employers.
3. **No auto-renew** means every buyer has to be won again each month. Email reminders before a pass runs out partly make up for this.

---

## 5. The 10 things to build first
1. **Make money possible:** a live crypto checkout with automatic activation for boosts, passes and Plus. This needs wallet addresses or merchant keys from the owner; the code is in `server/`.
2. **"Boost this job" on every listed job, plus an employer claim flow** (proof by company email or DNS, which already exists): Standard $99 and Premium $249 for 30 days, a recommended tier per job, and the first boost at half price. This sells to companies whose jobs we already show.
3. **Premium boost features copied from Indeed:**
   - a rotating top-3 slot;
   - an "Urgently hiring" badge that expires after 14 days;
   - a cover image and logo;
   - an invite-to-apply email to opted-in matched seekers;
   - a stats page per job (views and apply clicks).
4. **Hiring Pass at $499 for 30 days** (one company, unlimited boosts, spotlight, stats; one payment). Matches Jobright's $499 and the bottom of Indeed's $500–$2,000.
5. **Plus passes at $9 / $19 / $39 with AI:**
   - one-click "tailor my resume to this job";
   - AI bullets, summary and cover letter;
   - match score with the missing keywords on every job;
   - AI feedback in interview practice;
   - Jobright-style free daily limits (2 tailored resumes and 2 cover letters a day) so that free users meet the paywall.
6. **Accounts and email job alerts:** a daily digest, at most one email a day, and a reminder before a pass ends. Teal and Jobright both rely on coming back by email, and this is also how Premium invites get delivered.
7. **Browser extension:** save a job from any site into My jobs, plus autofill of application forms where the user still presses submit (no mass auto-apply). Teal's extension has about 200K users and Jobright's about 200K.
8. **H-1B and visa sponsorship history per company** from Department of Labor data:
   - a "Sponsor likely" badge on job cards;
   - pages at `/h1b/{role}-jobs-in-{city}/`;
   - a daily public GitHub list (new grad, internships, H-1B) copied from Jobright's 37 repositories, which act as a free acquisition channel.
9. **My jobs upgrade, copied from Teal**, all kept in the browser:
   - a contacts tracker (recruiter, follow-up date, outreach templates);
   - a company tracker;
   - excitement rating and extra stages;
   - a career-goals page;
   - a "work style" quiz with a "360" link that invites colleagues to rate you (brings new visitors).
10. **The page families Teal has and we lack:**
    - `/certifications/{role}/`
    - `/skills-for/{role}/` (resume skills per role)
    - `/resume-templates/{style}/`
    - `/professional-goals/{role}/`
    - `/job-titles/{role}/`
    - Also take resume and cover-letter examples from about 143 roles to 500+. Size the pages first against the hosting budget.

---

## 6. What I could not verify
- **Teal:** current pricing-page text (403 today; the 13 Nov 2026 session saw it); the sitemap and per-type page counts; the 4M-member figure; real 2024–2026 revenue (the CB Insights $4.2M conflicts with "100,000 paying"); the Autopilot price.
- **Jobright:** official seeker prices (pricing page 404; third-party prices from August 2026); whether company pages exist; the extension's user count (tracker data only); the $10M ARR claim (the LinkedIn post was not opened).
- **Indeed:**
  - any list price for Standard or Premium;
  - the "$5 a day" minimum (contradicted by 100hires);
  - the current US Smart Sourcing price ($400 vs $520);
  - Glassdoor and Indeed branding prices (quotes only).
- **Our own estimates:** the visitor-to-buyer rates in §4 (0.3% with crypto only, 1% with cards) are my assumptions, not measured figures.

## 7. Sources (read 15 Nov 2026)
**Teal:**
- https://refreshmiami.com/news/teal-raises-7-5m-to-expand-ai-powered-career-platform/ [opened]
- https://frontdeskreview.com/software/resume-builders/teal.md [opened]
- https://makerstack.co/reviews/teal-review/ [opened]
- https://intercom.help/tealhq-9a9274919b13/en/ [opened]
- https://www.privsource.com/acquisitions/deal/EMS9D2 [opened]
- https://chromewebstore.google.com/detail/opafjjlpbiaicbbgifbejoochmmeikep [search]
- tealhq.com page patterns [search]

**Jobright:**
- https://jobright.ai/ [opened]
- https://jobright.ai/employers/pricing [opened]
- https://jobright.ai/ai-agent [opened]
- https://jobright.ai/h1b-jobs [opened]
- https://jobright.ai/jobs/h1b-visa-sponsored-software-engineer-jobs-in-united-states [opened]
- https://jobright.ai/entry-level-jobs [opened]
- https://jobright.ai/tools [opened]
- https://jobright.ai/tnt [opened]
- https://jobright.ai/job-referral [opened]
- https://jobright.ai/orion-copilot [opened]
- https://github.com/jobright-ai [opened]
- https://techcrunch.com/2024/06/25/jobright-uses-ai-to-help-foreign-workers-navigate-the-us-job-market [opened]
- https://henrythe9th.substack.com/p/how-jobright-hit-5m-arr-with-9-people [opened, partly paywalled]
- https://www.arr.club/jobright/jobright-arr-hit-7m-with-fewer-than-10-employees-and-2m-job-seekers-globally [opened]
- https://www.arr.club/jobright/jobright-arr-hit-8m-amid-rapid-team-growth [opened]
- https://www.arr.club/signal/jobright-arr-hit-10m-up-from-1m-in-10-months [opened]
- https://careery.pro/blog/ai-job-search/jobright-ai-review [opened]
- https://jobstrack.io/blog/jobright-review-2026 [opened]

**Indeed, Glassdoor and Recruit:**
- https://www.indeed.com/hire/cs/pricing?co=US [opened]
- https://www.indeed.com/hire/resources/howtohub/how-pricing-works-on-indeed [opened]
- https://100hires.com/indeed-job-posting-cost.html [opened, 3rd]
- https://recruit-holdings.com/en/ir/library/upload/Recruit_202603Q4_summary_en.html [opened]
- https://www.noon.ai/blog/articles/346-glassdoor-pricing-2026 [search]
- Indeed Smart Sourcing figures [search]

**Our own files:** `PRICING_RESEARCH.md`, `REVENUE_RESEARCH.md`, `COMPETITOR_GAPS.md`, `SEO_MAP.md` and `config.json` (read, not edited).
