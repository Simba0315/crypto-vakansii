# Where job sites get their jobs: Hirify, JobAssist, Telegram, other hiring systems, Indeed for employers

Research done on 13 Nov 2026 at the owner's request ("parse Telegram channels and everything Hirify takes vacancies from; study
indeed.com/hire; look at jobassist.com"). "Fetched" means the page was retrieved and read that day. Requests left from a Vietnam IP,
so some prices were shown in dong and Indeed served its `en_vn` variant. Plans that follow from this file are in `ROADMAP.md`
sections 29 and 30.

## 1. Hirify (hirify.me)

**Sources, as Hirify states them**
- Home page: collects "directly from career pages, including custom career sites", re-reads sources every 2 hours, removes
  duplicates across 960+ Telegram channels (about 90% caught: title + company, contacts, text similarity, AI on disputed pairs).
- `llms.txt`: "more than a thousand Telegram channels and more than 20 thousand company career sites".
- `/plus`: "Hirify Global" is 6,800+ companies and 70,000+ international vacancies. They are listed for everyone, but the company
  name, LinkedIn and the apply link open only with Plus (399 RUB, about $6 a month).
- Home counter that day: 216,845 vacancies in the last month. Many Russian cards carry an "hh" badge (read as HeadHunter).

**Vacancy page**
- AI score 0–100 with reasons, company (or "Company hidden"), title, format, job type, grade, English level, country, skill tags,
  salary with a market-median block, an AI summary, then the original text marked "taken unchanged".
- Source label: "Vacancy from a Telegram channel – name available after login" or "Vacancy from Hirify Global".
- A visitor who is not signed in gets no link to the original post or to the company; contacts are behind a login button.
- JobPosting structured data with `datePosted` and `validThrough` (+28 days).

**Moderation.** `llms.txt` says AI moderates each posting. The terms say Hirify does not verify content, "tries to moderate" and
removes fakes on report. Every page has a scam warning and a Report button.

**Recruiters.** hire.hirify.me has no public page: it redirects to `/login`; registration is by LinkedIn or corporate email.
The only description is in `llms.txt`: a "self-service recruiter cabinet … post vacancies and manage candidates with AI".

**Limit on "repeat Hirify".** Its terms (§3) forbid collecting its vacancies, company names, apply links or source information to
build another product, and `llms.txt` repeats that for AI agents. So: copy the sources, never Hirify's own pages.

## 2. JobAssist (jobassist.com)

- A paid AI auto-apply service; the job catalogue is its search-traffic funnel.
- Its own numbers disagree with each other: home says "24,000,000+ verified job listings", "500,000+ new jobs daily", "7M+ jobs from
  1.3M+ companies"; the About page says "10,000,000+ active listings", "200,000+ daily"; category counts add up to far more than 7M.
- Sources: one help page says "job boards, employer career pages and other sources". Listings carry no source label.
- "Apply with JobAssist" leads to a signup quiz. There is no link to the employer's page.
- Structure: 31 categories → position pages (1,097 addresses in the sitemap) → job pages. Job pages are not in the sitemap and carry
  no JobPosting structured data.
- Job page: rewritten by AI into fixed sections (About, Responsibilities, Requirements, Benefits, About the company).
- Free: browsing and reading. Paid: matching, auto-apply, cover letters, tracker. Prices seen: 7 days ≈ $6.5, first month ≈ $26,
  three months ≈ $55, then ≈ $65 a month (converted from dong).

What we take from it: the guided match by pay and answers (built on `/for-you/`, free, in the browser). What we do not take:
hiding the employer's link, AI-rewritten postings, counts that cannot be checked.

## 3. Telegram channels with jobs in English

About 590 channel names were tried; each one below returned posts at `https://t.me/s/<name>` that day.

**@nodejsjobsfeed** (3.6K subscribers, Russian): relays the Telegram chat @nodejs_jobs, not a website. Its last 20 posts were 20
résumés and 0 vacancies.

**Main finding.** Most high-volume English channels are feeds of websites (RemoteOK, CryptoJobsList, web3.career, JobStash,
DevITjobs, We Work Remotely). The extra value of Telegram is the posts that link straight to a company's hiring system: they give
new company addresses for our existing collector.

| Channel | Subscribers | Vacancies in last 20 posts | Company named | Link goes to | Posts a day |
|---|---|---|---|---|---|
| cryptojobslist | 62.1K | 14 | yes | cryptojobslist.com | 3.0 |
| web3hiring | 61K | 17 digests of ~5 jobs | yes | hashtagweb3.com, then the hiring system | 3.4 |
| remotejobshg | 32.6K | 20 | yes | web3.career, other boards, Ashby, Lever | 3.4 |
| jobstash | 12.6K | 20 | yes | jobstash.xyz | ~60 on weekdays |
| dejob_global | 16.9K | 20 | yes, with company site | Ashby, Greenhouse, Lever, company sites | 0.9 |
| remoteok | 13K | 20 | yes | remoteok.com | 3.8 |
| remotejobss | 162K | 19 | yes | remoteok.com (a mirror) | 3.0 |
| remoteit, gamedevjobs | 52.2K, 22K | 17 | mostly | teletype.in article with an apply link | 2.8 |
| remote_ai_jobs, remote_python_jobs, remote_frontend_jobs and six sister channels | 0.4K–8.6K | 20 each | yes | other boards, sometimes a hiring system | 0.4–0.7 each |
| full_remote_jobs | 552 | 20 | yes | boards plus Recruitee, Breezy, Greenhouse, Lever, BambooHR | 2.4 |
| germantechjobs, devitjobs (UK), devitjobs_nl, devitjobs_us | 3.5K–17.2K | 20 | yes | their own boards through tinyurl | 0.6–1.3 |
| relocateme | 34.7K | about 5 batches | yes | relocate.me, some Ashby | 0.2 |
| gocareers, internfreak, TechUprise_Updates, dot_aware, tech_internships (India, beginners) | 0.4K–78K | 16–20 | yes | employer pages, Workday, some referral links | 0.7–7.3 |

Leave out or handle with care: LaborXWeb3Jobs (small freelance gigs), remoteweb3jobs (forwarded posts, forms), Jobs_global_startups
(links to a recruiter's LinkedIn profile, company often hidden), remotejobs (bot links only), jayatalent (agency marketing),
illuminatiJOBS (mostly job seekers, contact by direct message), Web3_Job (same form in every post, dormant), freshershunt and
jobs_and_internships_updates (clickbait, course ads, referral pushes). No pay-to-apply scam channel was met in this set.

**Page markup** (the same on every channel inspected)
- Message: `div.tgme_widget_message[data-post="channel/ID"]`; skip class `service_message`.
- Text: `div.tgme_widget_message_text.js-message_text`; lines are `<br/>`, `$` arrives as `&#036;`.
- Links: `<a href>` inside the text, `a.tgme_widget_message_inline_button.url_button`, `a.tgme_widget_message_link_preview`.
- Date and permalink: `a.tgme_widget_message_date[href]` > `time[datetime]` (UTC).
- Older posts: `a.tme_messages_more[data-before]` or `/s/<channel>?before=N`.
- No throttling was met in about 650 requests; a missing preview redirects to `t.me/<name>` (this happens for every group chat).

## 4. Other sources that need no key

| Source | Address | Has salary | Notes |
|---|---|---|---|
| Workable | `apply.workable.com/api/v1/widget/accounts/<slug>?details=true` | no | title, city, remote flag, description, date, apply link |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/<Id>/postings` | no | description only in the detail call |
| Recruitee | `<slug>.recruitee.com/api/offers/` | yes | min, max, currency, remote and hybrid flags |
| Teamtailor | `<slug>.teamtailor.com/jobs.json` or `/jobs.rss` | no | JSON carries schema.org job data |
| BambooHR | `<slug>.bamboohr.com/careers/list` (+ `/careers/<id>/detail`) | in detail | undocumented |
| Breezy | `<slug>.breezy.hr/json?verbose=true` | as text | |
| Personio | `<slug>.jobs.personio.de/xml?language=en` | no | only if the company enabled the feed; mostly Germany |
| Workday | POST `<tenant>.wd<N>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs` | no | undocumented; list capped at 2,000 |
| Rippling | `ats.rippling.com/api/v2/board/<slug>/jobs` | in detail | undocumented |
| JazzHR | `app.jazz.co/feeds/export/jobs/<slug>` | no | no posting date |
| Pinpoint | `<slug>.pinpointhq.com/postings.json` | yes | no posting date |
| Comeet | page embeds the data and a public token | no | |
| Remotive | `remotive.com/api/remote-jobs` | as text | must link back and name Remotive; must not be passed to Google Jobs; 4 fetches a day at most |
| RemoteOK | `remoteok.com/api` | partly | must link back with a followed link and name Remote OK |
| Arbeitnow | `arbeitnow.com/api/job-board-api` | no | free, link back appreciated; mostly Germany |
| Jobicy | `jobicy.com/api/v2/remote-jobs` | no | credit and link; once an hour at most |
| We Work Remotely | `weworkremotely.com/remote-jobs.rss` | no | terms page could not be read (bot check) |
| Himalayas | `himalayas.app/jobs/api` | yes | says it may be used to fill a remote job board; terms not read in full |
| Hacker News "Who is hiring" | `hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring` | free text | 234 top-level posts in the November thread |

**Finding company addresses in bulk**
1. Common Crawl index (`index.commoncrawl.org/CC-MAIN-…-index?url=*.<hiring-system-domain>`): one page returned 387 Personio,
   151 Recruitee and 62 Breezy company addresses.
2. Links inside Hacker News hiring threads and Telegram posts: three months of threads gave 211 Ashby, 48 Greenhouse, 32 Lever,
   14 Workable, 10 Rippling and 7 JazzHR addresses.
3. Our own 544 company names tried against each pattern; a wrong address fails cleanly.

## 5. Indeed for employers (indeed.com/hire)

| Group | What Indeed offers | Possible here |
|---|---|---|
| Posting and promotion | free post; sponsored tiers with a budget; "urgently hiring" label; logo and image | partly: submit form, paid featured slot and label, crypto payment (needs the server) |
| Apply | Indeed Apply, integrations with hiring systems | keep sending candidates to the employer's own page |
| Dashboard | candidate tracking, message templates, analytics | partly: clicks per job; no inbox |
| Screening, interviews, résumé database, events | screener questions, fit score, video interviews, 380M profiles | no: all of it needs stored applications or a candidate database |
| Branding | company pages, branded jobs | yes: company pages exist; claim-and-edit needs the server |
| Market data | Hiring Insights reports, salary figures | yes: per role and skill from our own postings |
| Job description templates | about 1,050 pages `/hire/job-description/<role>` with duties, examples, skills, salary, FAQ | yes: one static page per role from our own postings |
| Interview questions | about 350 pages | yes |
| How to hire a role | about 300 pages plus a general guide | yes |
| Articles and templates | about 310 (offer letter, phone-screen template, onboarding checklist, cost of turnover) | yes |
| Hiring cost calculator | not found on Indeed | a small calculator would be an addition |

The template pages carry Article, FAQPage, Occupation and MonetaryAmountDistribution structured data.

## Not opened or not verified

- The Muse API and the We Work Remotely terms page (bot check); workatastartup.com (406); cryptojobslist.com redirect targets (403).
- Indeed's Smart Sourcing, hiring-events and sponsored-jobs pages (404 from Vietnam).
- Reuse terms of Himalayas (read in part), SmartRecruiters, Recruitee, Comeet and Y Combinator.
- Hirify's recruiter cabinet behind login and the names of its Telegram sources (login only).
