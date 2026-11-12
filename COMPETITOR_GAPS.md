# Competitor gaps: what other job sites have that Hiring Right Now does not

Researched 2026-11-13. Our side was checked against the live site (https://simba0315.github.io/crypto-vakansii/), `AGENT_NOTES.md`,
`ROADMAP.md`, `server/README.md` and `build.py` as they stood that day.

How to read this file

- "Opened" means the competitor's own page was fetched and read. "Search only" means the site blocked automated reading (HTTP 403 or
  a timeout) and the facts come from search results, help pages or third-party write-ups; treat those as weaker.
- Prices and audience numbers are the competitor's own claims on the date above, not checked independently.
- "Not verified" marks anything I could not confirm. "Unsure we lack it" marks features I could not rule out on our side.
- Items already queued in `ROADMAP.md` are still listed (the owner asked for a complete list) and are marked "queued".

What I treated as already built (not listed as gaps): everything in the task brief, plus what `build.py` already generates:
category x level pages (`jobs/<category>/<level>/`), location x skill, location x category, location x remote, remote x skill,
skill-vs-skill comparison pages (`compare/<a>-vs-<b>/`), RSS on category, skill, perk, remote, crypto and new-jobs pages, IndexNow
pings, `llms.txt`, FAQ markup, the "Not interested" button and share links on job pages.

---

## 1. Competitors reviewed

42 sites: 30 opened (Indeed and LinkedIn only partly), 1 answered with a redirect only, 11 search only.

### General and tech boards

| # | Name | URL | What it is | How it makes money (published prices) | How I got the information |
|---|---|---|---|---|---|
| 1 | Indeed | indeed.com | Largest general job search engine; company reviews, salary guide, Hiring Lab research | Free posts plus sponsored jobs; no prices on the page I could open | Partly opened: /career/salaries, /hire/pricing, hiringlab.indeed.com. /companies returned 403. Rest from search |
| 2 | LinkedIn Jobs | linkedin.com/jobs | Jobs inside a professional network | Free single post, paid promotion; Premium for members (one third-party source says $29.99/mo, not verified) | Partly opened: guest jobs page. Rest from search (LinkedIn help page a1492056 on verified job posts) |
| 3 | Glassdoor | glassdoor.com | Company reviews, salaries, interview reports | Hiring inventory tied to Indeed; search results say it merged into Indeed on 2026-07-01 (not verified on an official page) | Search only (403 on site and help centre) |
| 4 | ZipRecruiter | ziprecruiter.com | General job marketplace | Employer subscriptions per job slot; no published price. Third-party estimates $299 to $899/mo (not verified) | Search only (403) |
| 5 | Dice | dice.com | US tech job board with a candidate database | $399 single 30-day slot; Starter $649/mo (3 slots, 250 candidate views); Standard $899/mo (5 slots, 500 views) | Opened: home, /jobs?q=python, /hiring/pricing |
| 6 | Built In | builtin.com | Tech jobs, company profiles, articles, city hubs, "Best Places to Work" | Employer membership sold by demo, job slots; no prices shown | Opened: /jobs, /company/stripe, /salaries, employers.builtin.com/membership |
| 7 | Wellfound | wellfound.com | Startup jobs with profile-based applying | Posts free; job ads from $200 each; sourcing seats $135 and $199/seat/mo; "Autopilot" $500/mo per role plus 10% placement fee | Opened: /jobs, /hiring-data, /recruit/pricing |
| 8 | Welcome to the Jungle (Otta) | welcometothejungle.com | Matching-led job site with rich company profiles | Employer branding and hiring suite (pricing page exists, not opened) | Opened: /en home. Otta details from search |
| 9 | Y Combinator Work at a Startup | ycombinator.com/jobs, workatastartup.com | Jobs at YC companies, one profile for all applications | Free; serves the YC portfolio | Opened: ycombinator.com/jobs (workatastartup.com returned only a title) |
| 10 | Hired | hired.com | Was a "companies apply to you" marketplace | Folded into LHH (Adecco) in June 2024 per its own notice quoted in search | Search only |
| 11 | Levels.fyi | levels.fyi | Verified pay data by company and level, plus jobs | Negotiation coaching $1,250 / $1,250 / $2,450 / $5,000; résumé review; employer benchmarking, talent pool, API | Opened: /jobs, /services/, /companies/stripe/salaries |
| 12 | HN Hiring | hnhiring.com | Index of Hacker News "Who is hiring" threads since 2018 | None seen | Opened |
| 13 | HN Hiring Trends | hntrends.com | Monthly charts of terms in the same threads since 2011 | None seen | Opened |
| 14 | Stack Overflow Jobs | stackoverflowjobs.com | Indeed-powered relaunch (May 2024) of the old board | Through Indeed. One personal site says it closed 2026-04-01 (not verified) | Search only |

### Remote boards

| # | Name | URL | What it is | How it makes money (published prices) | How I got the information |
|---|---|---|---|---|---|
| 15 | We Work Remotely | weworkremotely.com | Large remote board | $299 per 30-day post plus "Good / Better / Best" upgrades (its support page, via search); bundles reported by third parties | Search only (403) |
| 16 | Remote OK | remoteok.com | Remote board with open stats | Post button shows $447 ("starting from $299" in the copy, dynamic pricing); paid add-ons; bundles up to 50% off; job-seeker Premium $14.95/mo and TopAccess $29.95/mo; partner links (résumé builder, health insurance, payroll) | Opened: home, /hire-remotely, /remote-work-statistics, /faq |
| 17 | Remotive | remotive.com | Remote board; most listings behind a paid tier | Employers $299 / $398 / $448 (shown per month); job seekers pay to "unlock all jobs" (price not shown); affiliate programme | Opened: home, /join, /hire |
| 18 | Himalayas | himalayas.app | Remote jobs, company profiles, AI career tools, talent directory | Free; Plus $9 for unlimited AI tools; sponsored rows in the job list; employer pricing not found (404) | Opened: home, /jobs, /companies, /companies/gitlab, /salaries, /api |
| 19 | Working Nomads | workingnomads.com | Curated remote jobs | Premium $17.95/mo, $39.95/quarter, $79.95/yr; employers $199 per post or 10 for $1,690; sponsorship | Opened: /jobs, /premium-subscription, /post-job-options |
| 20 | Remote.co | remote.co | Remote jobs and company Q&A | Not verified (reports of membership prompts) | Search only (timeouts) |
| 21 | FlexJobs | flexjobs.com | Hand-screened remote and flexible jobs behind a membership | Job-seeker membership; third-party figures: $2.95 14-day trial, about $24/mo, about $60 to $71/yr (not verified) | Search only (timeouts) |
| 22 | Arc.dev | arc.dev | Remote developer jobs plus a vetted-talent hiring service | Hiring service (fees on /pricing, not opened) | Opened: /remote-jobs |
| 23 | Jobspresso | jobspresso.co | Hand-reviewed remote jobs | Posts from $299 | Opened: home |

### Crypto and web3 boards

| # | Name | URL | What it is | How it makes money (published prices) | How I got the information |
|---|---|---|---|---|---|
| 24 | web3.career | web3.career | Largest web3 board; salaries, learning directory, company list | Paid posts (base price not shown on the page) with add-ons: sticky +$49 (24 h) to +$299 (30 days), logo +$49, highlight +$99 or +$149, support +$99; in-feed banner slots $1,999 to $4,999/mo | Opened: home, /post-web3-job, /ads, /web3-salaries, /web3-companies, /learn-web3, /web3-jobs-api |
| 25 | CryptoJobsList | cryptojobslist.com | Crypto board with talent profiles, salaries, newsletter, Telegram | "Dynamic pricing" from about $100 (its buy-package page via search); success-fee recruiting | Search only (403) |
| 26 | Crypto.jobs | crypto.jobs | Former crypto board | Now a 301 redirect to cryptojobslist.com | Redirect only |
| 27 | Cryptocurrency Jobs | cryptocurrencyjobs.co | Curated crypto board, weekly newsletter | $299 flat per 30-day post, up to 20% volume discount, crypto accepted; newsletter sponsorship by email | Opened: home, /post-a-job/, /salaries/, /talent-collective/, /newsletter/ |
| 28 | Remote3 | remote3.co | Remote web3 jobs with a developer directory | Posts $199 / $299 / $349 / $399; sticky $99 to $199; email feature $49; "hire developers" $49/mo; affiliate programme | Opened: home, /post-job |
| 29 | UseWeb3 | useweb3.xyz | Was a web3 learning and jobs site | The page now says the project is no longer active | Opened |
| 30 | Talent boards of funds and media (a16z, Paradigm, Bankless) | jobs.a16z.com, paradigm.xyz, bankless.com/jobs | Portfolio job boards with a talent network | Free; serve the portfolio | Opened: jobs.a16z.com (702 companies, 18,767 jobs). Paradigm and Bankless only answered with redirects, not followed |

### Aggregators, job-seeker tools and models

| # | Name | URL | What it is | How it makes money (published prices) | How I got the information |
|---|---|---|---|---|---|
| 31 | Simplify | simplify.jobs | Autofill extension, tracker, résumé tools, internship lists | Employer products; paid tier price not found (/pricing is 404) | Opened: home |
| 32 | Teal | tealhq.com | Résumé builder and job tracker | Teal+ $13/week or $29/mo per third-party reviews (not verified) | Search only (403) |
| 33 | Jobright | jobright.ai | AI job matching, H-1B data, autofill | Job-seeker plans not on the page; employer pricing exists | Opened: home, /h1b-jobs |
| 34 | Huntr | huntr.co | Job tracker, résumé tools, autofill | Pro $40/mo, $90/quarter, $160/half-year | Opened: home, /pricing |
| 35 | Google for Jobs | developers.google.com/search/docs/appearance/structured-data/job-posting | The job box in Google Search; requirements for sites | Free | Opened |
| 36 | Adzuna | adzuna.com | Aggregator with salary statistics and a résumé-value tool | Not confirmed | Search only (403) |
| 37 | Jooble | jooble.org | Aggregator in many countries | Advertiser, partner and affiliate programmes (rates not shown) | Opened |
| 38 | Talent.com | talent.com | Aggregator with tax calculator and salary converter | Enterprise and publisher programmes | Opened (regional redirect) |
| 39 | hh.ru | hh.ru | Mature national job portal | Paid applicant services (hh PRO, ready-made résumé, résumé review, consultations); employers pay for postings, résumé database, advertising. No prices on the pages opened | Opened: home, /services |
| 40 | Hirify | hirify.me | AI job aggregator for IT (Telegram channels plus career sites); the owner's reference model | Plus as a one-time payment: 399 RUB / 1 month (its About page also says $6), 990 RUB / 3 months, 1,990 RUB / year; employer cabinet at hire.hirify.me (prices not visible) | Opened: home, /plus, /mcp-api, /cv-roasting, /friends, /companies, /about, /llms.txt |
| 41 | TrueUp (added) | trueup.io | Tech jobs with company rankings, layoffs tracker, trend pages | "Hire" and sponsorship pages; free membership | Opened: home (inner pages 403) |
| 42 | HiringCafe (added) | hiring.cafe | Search engine over company career pages, the closest model to ours | Reported: promoted listings and an opt-in talent network (not verified) | Search only (403) |

---

## 2. Gap list

Columns: what it is; who has it (with the page where I saw it); what the visitor gets; why it matters to us; how it fits our
constraints; effort (S = hours to a day, M = several days, L = weeks). Sorted by priority, then effort.

### Priority 1: do first (traffic or money, feasible now or as soon as the Worker is live)

| # | Gap | Who has it | What the visitor gets | Why it matters to us | How, within our constraints | Effort |
|---|---|---|---|---|---|---|
| 1 | Complete job markup for Google's job box | Google's rules (developers.google.com/.../job-posting). Remote OK, Remotive, Working Nomads, Remote3 and web3.career all tell employers that paid posts are distributed through Google's job search | Our jobs can appear in the job box inside Google Search | Traffic: the largest free channel for job sites | Static. Today's markup has no country in `jobLocation` (Google requires `addressCountry`), no `validThrough`, no `identifier`, no `applicantLocationRequirements` for remote roles, no company `sameAs`/logo. Add a parsed country to `collect.py`. See also item 6 | S |
| 2 | Dated monthly hiring report with an archive | Indeed Hiring Lab (monthly snapshots, hiringlab.indeed.com), hntrends.com (a write-up per month since 2013), TrueUp (/reports, /job-trend), Levels.fyi (annual pay report /2025/), Remote OK (/remote-work-statistics with a prefilled post per section) | A page per month with numbers that stay put and can be quoted | Backlinks from media and blogs; proof of expertise | Static page `reports/2026-11/` frozen at month end, generated from the snapshots. Queued in ROADMAP | S |
| 3 | Public GitHub repository with daily lists | Simplify (simplify.jobs/internships; its GitHub repository was not opened in this pass, not verified) | A plain list of internships and new-grad roles that students star and share | Backlinks and word of mouth among students; each row links to our job page | The daily workflow writes a README (internships, visa-sponsoring roles, remote roles) to a second public repo. Needs the owner's yes, since it is a new public surface | S |
| 4 | Salary pages by level, location, company and job title | web3.career (/web3-salaries by role, seniority, region, about 45 countries, 60 months of trend), Built In (/salaries/us/<location>/<title>), Wellfound (/hiring-data/r/, /l/, /s/, /i/), Levels.fyi (by title, location, company, level), Himalayas (by country), Cryptocurrency Jobs (/salaries/<title>/) | "What does a senior data engineer in London make", with ranges and the live jobs behind the number | Traffic: salary queries are large and we have real ranges; today we only split by skill and category | Static. Reuse `salary_page()`; publish only groups above a minimum sample (the 15-role rule already exists). Add percentile bands and a month-by-month line once history accumulates | M |
| 5 | More landing-page dimensions | Hirify (about 130 pages: 37 specialisations, 23 industries, 29 stacks, relocation and company-type pages; hirify.me/llms.txt), web3.career (role + remote, about 20 cities, countries), Remotive (career level, employment type, date posted, high-paying by category), YC (role x city, role x remote), Built In (about 70 metro areas), Dice (/jobs/q-<term>-jobs) | A page that matches the exact search: "DevOps engineer jobs", "Rust jobs in Berlin", "senior Python jobs" | Traffic: we have 13 categories and 26 places; competitors cover job titles and cities | Static. Add job-title pages (specialisations parsed from titles), more cities, skill x level, "highest-paying <category>" lists. Keep the existing 8-job minimum and watch the 800 MB ceiling | M |
| 6 | Full job description on the job page | Google requires a complete description for the job box. web3.career's API offers full descriptions (/web3-jobs-api); Hirify's agent tools can read the full original text (/mcp-api). Other sites' job pages were not opened one by one | The whole posting without leaving the page | Traffic (job box eligibility, long-tail search) and usefulness; today we show a short excerpt | Static, about 36,000 pages get heavier, so check size. Owner decision: the text comes from the employers' public feeds, not from competitors, but it is still someone else's text. Alternative with no reuse: item 31 (structured summary) | M |
| 7 | Access for AI assistants (MCP server) | Hirify (MCP, CLI and API inside Plus; /mcp-api), Himalayas (free MCP server; /api), Dice (MCP server announced on its career-advice pages), Levels.fyi (/api-access: API, MCP, CLI), Indeed (app in ChatGPT, search only) | Ask an assistant "find remote Rust jobs over $150K" and get our live data | Traffic from assistants, which the owner's page standard already targets; cheap to run | Worker: a small read-only MCP endpoint over the existing JSON (search jobs, job detail, company stats, salary stats). Add "ask an AI about this site" links in the footer as Hirify does | M |
| 8 | Free weekly email digest with a sponsor slot | Cryptocurrency Jobs (weekly, claims 35,000+ subscribers, sells issue sponsorship; /newsletter/), Remote3 (claims 20,500+; $49 email add-on), Remote OK (sells an "email blast"), Working Nomads (free alerts, 65,000+ claimed), Remotive (daily digest), Dice and Built In (job alerts) | New matching jobs without revisiting the site | Retention, and a second thing to sell to employers | Needs an email service, a domain and the owner. Suggested split: weekly digest free, instant alerts stay in Plus. Partly queued | M |
| 9 | "Add your company" by pasting a careers-board address; claim a company page | Remotive (imports jobs from Greenhouse, Lever, Workable and others; /hire), Wellfound (ATS sync, free unlimited posts), Levels.fyi (free job posting), Himalayas ("claim profile" prompt on company pages), Built In ("Is this your company?") | An employer lists every open role in a minute and keeps it current | Supply grows by itself; each claimed company is a lead for paid placements | Worker: validate the Greenhouse, Lever or Ashby address automatically, add it to the sources, show it after the next build. No moderator needed | M |
| 10 | Visa sponsorship history per company | Jobright (/h1b-jobs: "H1B Sponsored" or "Sponsor Likely" labels and yearly counts from US Department of Labor filings), Levels.fyi (/h1b/ salaries) | Whether this employer has actually sponsored before, not only what the posting says | Traffic ("companies that sponsor H-1B") and trust; fits the English-speaking market | Static. The filings are public; match them to our 540 companies with a hand-checked name table. Show counts with the source and year | M |
| 11 | Remote eligibility: which countries and time zones | Himalayas (rows say "United Kingdom only"; /jobs/timezones), Remotive (two modes: "available from my location" and "explicitly in my location"), Remote OK (regions plus about 190 countries), Arc (time-zone overlap on rows), Hirify ("no country requirement" toggle) | A remote seeker sees only jobs they are allowed to take | Retention: the main pain of remote search; we have 10,000+ remote roles | Parse country and region limits in `collect.py`, add a filter and pages such as "remote jobs open to Europe". Accuracy must be stated in the methodology | M |
| 12 | Many more sources | Hirify (claims 20,000+ career sites and 1,000+ Telegram channels in llms.txt, but "700+ sources" on /about), Himalayas (claims 100,000+ jobs at 70,000+ companies), a16z board (702 companies), HN Hiring (monthly threads), HiringCafe (search only) | More of the market in one place | Traffic and trust: 540 companies is small next to these | Static pipeline. Next feeds: Workable, SmartRecruiters, Recruitee, Teamtailor (already in ROADMAP), then the monthly Hacker News thread through its public API. Page count grows, so move job pages off GitHub Pages before 800 MB | M to L |

### Priority 2: worth doing next

| # | Gap | Who has it | What the visitor gets | Why it matters to us | How, within our constraints | Effort |
|---|---|---|---|---|---|---|
| 13 | Report a job | Remotive (reasons: dead page, wrong location, scam, other), Remote OK (/faq: report scam or "not remote"), CryptoJobsList (its blog, search only) | One click to flag a dead or suspicious listing | Trust, and free quality control with no moderator | Worker endpoint; a report triggers an automatic re-check of the source feed instead of a human review | S |
| 14 | Job-scam guide and a visible "source checked" line | Hirify (/blog/scam-alert), Working Nomads (scam-alert page), CryptoJobsList (blog), LinkedIn (verification badge and filter on job posts, help page a1492056), Himalayas (new employers reviewed by a person) | Confidence that a listing is real | Trust, especially in the crypto section | Static. One guide page; on each job: "Fetched from <company>'s own hiring system on <date>". Unsure we lack the second part: job pages already show "last checked" | S |
| 15 | Many more perk tags | Remote OK (about 25: async, no whiteboard interview, no monitoring, company retreats, profit sharing), web3.career (about 20 benefit pages), Himalayas (about 35 benefit pages) | Filter by what matters personally | Traffic (a page per perk) and stickier filters; we have 8 | Static: more patterns in `PERKS` | S |
| 16 | Crypto section depth | Cryptocurrency Jobs (pages by chain and theme: Ethereum, Solana, Bitcoin, DeFi, NFT, DAO, layer 2, "pays in crypto"), web3.career (/pay-in-crypto-jobs, tag pages), Hirify (currency filter with "Crypto") | Jobs in one ecosystem, or paid in crypto | Traffic for the niche the site started from | Static: ecosystem tags from the text, a "paid in crypto" perk | S |
| 17 | Exclude filters and "hide this company" | Hirify (an exclude switch on most filters; hide jobs or companies) | Remove agencies, a level or a country from results for good | Retention for daily users | In the browser. Unsure we lack all of it: "Not interested" exists per job | S |
| 18 | Plain-language search | Hirify ("AI search", text turned into filters), LinkedIn (search only), Jobright (assistant) | Type "remote senior rust over 150k in europe" and get the filters set | Easier first search, good on phones | In the browser with rules and our own skill and place lists; no AI service needed | S |
| 19 | Tracker extras | Huntr (contacts, interview tracker, metrics, clipper), Himalayas (deadlines, follow-ups, stages), Built In (application tracker), Simplify | Add a job found elsewhere, keep recruiter contacts, interview dates and reminders, see own numbers | Retention: the tracker becomes the daily home | In the browser. Unsure which parts we already have (statuses, notes and CSV exist) | S |
| 20 | Match percentage and the reason on every job row | Himalayas (98% style badges), Jobright, Huntr (match scores), Indeed ("Smart Fit Score", search only) | See at a glance how well a job fits | Retention | In the browser from the skills already saved in "For you". Unsure we lack it outside the "For you" page | S |
| 21 | Company sub-pages and "companies using X" lists | Himalayas (/companies/<name>/salaries, /benefits, /tech-stack; /companies/benefits/<benefit>), HN Hiring (/technologies/<name>) | "Companies that use Rust", "<company> salaries", "<company> benefits" | Traffic on company-name queries | Static from data we already hold; cap by sample size | S |
| 22 | Employer add-ons | Remote OK (logo, brand colour, pin 1 week or 1 month, QR link, geo-lock, renew), web3.career (sticky for 24 h to 30 days, colour highlight, auto-renew), Remote3 (same ladder) | An employer picks exactly the boost wanted | Money: more price points; ours are fixed 7 and 14 days | Worker products. With crypto there is no auto-charge, so offer a renew reminder instead | S |
| 23 | "Hire a <role>" market pages for employers | web3.career (/hire/solidity), Remote3 (/hire/blockchain-developers), Arc (/hire-developers) | An employer searching "hire Rust developers" lands on a page about that market | Money: brings employers, not only candidates | Static, and stronger than theirs with our numbers: open roles competing, median advertised pay, median days open | S |
| 24 | Sponsor slot for non-employers and partner offers | web3.career (four in-feed banner slots at $1,999 to $4,999/mo; /ads), Himalayas ("Sponsored" rows), Remote OK (résumé builder, health insurance and payroll partners), Hirify (/friends: partner discounts), Working Nomads and TrueUp (sponsorship pages) | Relevant offers: courses, tools, relocation help | Money from companies that are not hiring | Static slot plus a Worker product. Real partners only; signing them is the owner's step. Must be labelled as an ad and kept out of the job rows | S |
| 25 | Named rankings with a badge for the winners | We Work Remotely (a /top-remote-companies page exists but was blocked; contents not verified), Built In ("Best Places to Work"), TrueUp ("Hot 200", "AI 50", "Remote 200"), web3.career ("Top Web3 Companies" by month) | A recognisable list | Backlinks: listed companies link to their badge | Static, from measured facts only (roles opened, share with pay shown). Partly there: insights rankings and live badges exist, a dated named list does not | S |
| 26 | RSS for every listing and company page | Remotive (/remote-jobs/rss-feed), Remote OK (tag feeds), Remote3 (/api/rss) | Follow one company or one search in a reader, Slack or Discord | Retention for developers; free | Static. Unsure: feeds exist for categories, skills and perks; I did not find them for companies or locations | S |
| 27 | Telegram channel and alert bot | Hirify (unlimited saved filters delivered by bot), Remote3 (Telegram group, 4,200+ claimed), Remotive (channel), hh.ru (Telegram, Viber and VK bots), CryptoJobsList (search only) | Alerts with no email and no account | Retention for the crypto audience; works before the email service exists | The daily workflow can post to a channel; a Worker webhook can serve personal filters. Needs the owner to create the bot. ROADMAP notes the US audience prefers email, so this is for the crypto section | S to M |
| 28 | Company facts | Himalayas (about, size, founded, CEO, markets, countries, social links), Built In (HQ, size, founded, offices), Wellfound (stage, investors), a16z board (stage, size band), YC (batch, one-line pitch), Hirify (industry tags) | Who the company is before applying | Traffic on "<company> careers"; trust | Static. Sources that keep the "nothing invented" rule: the company's own site description (quoted, with source) and Wikidata for founding year, HQ and industry | M |
| 29 | Industry pages and filters by company size or stage | Hirify (23 industries; startup, corporation, product, outsourcing), TrueUp (sector lists), Built In (industry, company size), a16z board (stage, focus area), Wellfound | "Fintech jobs", "jobs at companies under 200 people" | Traffic and better filtering | Depends on item 28 for the data | M |
| 30 | More parsed requirements | Hirify (English level, posting language), Built In (experience), Google (experience and education fields, beta) | Filter by years of experience, "no degree required", language | Retention; feeds original idea F below | Parse in `collect.py`; state accuracy on the methodology page | M |
| 31 | Structured job summary | Jobspresso ("Quick Brew" AI overview on each job), Hirify (AI-extracted role, stack, grade, pay, format) | Requirements, duties and benefits in a few lines | Usefulness on phones; richer pages | Build-time extraction by rules (no AI cost), or an AI pass through the Worker later | M |
| 32 | Interview-prep and "what postings ask for" pages | Himalayas (/interview-questions), Jobright (interview tool), Dice (interview tips), Glassdoor (search only) | What to prepare for a given role | Traffic; a reason to return between applications | Static and honest version from our data: skills that appear together, typical years asked, pay bands per role. Written Q&A would need careful original writing | M |
| 33 | Apply-click counts, employer statistics and a click guarantee | Remotive (200+ apply clicks or a free repost; /hire), Remote OK ("most viewed", "most applied" sorts) | Employers see what a listing delivered | Money: proof for paid placements | Worker: count outbound apply clicks without cookies. Offer a guarantee only once real numbers support it. Unsure whether the written employer account already shows statistics | M |
| 34 | Paid data products | Levels.fyi (compensation benchmarking for employers, data sets), Adzuna (data API, search only), TrueUp (/hire) | A hiring manager buys a market report for one role: pay bands, competing openings, time to close | Money that does not depend on job-seeker traffic | Worker checkout plus a generated report page; a higher-limit API tier with history | M |
| 35 | Browser push alerts | Jooble and hh.ru (app notifications). Web push itself was not verified on any reviewed site | Alerts with no email and no app | Retention before email exists | Worker sends pushes; the service worker is already there | M |
| 36 | AI résumé tailoring per job and interview practice | Himalayas (résumé, cover letter, mock interviewer, career coach, headshots; Plus $9), Huntr (tailor, review; Pro $40/mo), Jobright, Teal (search only), Hirify ("CV roasting" in Plus) | A résumé adjusted to one posting; a practice interview | Money: gives Plus more to sell | Worker plus a paid AI service; cost per use must be covered by Plus. Review and cover letters are already planned | M |
| 37 | Company-vs-company comparison and audience landing pages | Levels.fyi (company comparisons), web3.career (/web3-salaries/solana-vs-ethereum), Hirify (relocation pages, junior pages) | "Stripe vs Coinbase: roles, pay, remote share"; pages for juniors, relocation, career change | Traffic | Static. Both queued in ROADMAP; skill-vs-skill already exists | M |
| 38 | Résumé database, "let employers find me" | Remote3 (/developers, $49/mo for employers), Himalayas (talent directory, 600,000+ claimed), Cryptocurrency Jobs (private talent collective), Dice (candidate views inside $649 to $899/mo plans), hh.ru (/search/resume), Wellfound, Levels.fyi (talent pool), a16z (TalentPlace) | Be approached instead of applying | Money: the classic paid employer product | Worker and D1, opt-in only, self-serve access for employers. Queued in ROADMAP. Needs a privacy design before any code | L |
| 39 | Career content hub | Dice (/career-advice), Built In (articles, A to Z tech dictionary), Himalayas (résumé samples, cover-letter examples, career guides), Arc (job description templates), Jooble, hh.ru, Remotive, Cryptocurrency Jobs (blogs) | Guides, examples by role, a glossary | Traffic at the top of the funnel | Static; the agents can write it, but each piece must be original, dated and backed by our data, with no invented author | L |
| 40 | Browser extension: autofill and job clipper | Simplify (autofill on 100,000+ career sites claimed), Huntr (clipper, autofill), Jobright (autofill), Built In ("AI assistant" for applications), Dice ("Easy Apply") | Faster applications; save jobs from any site into the tracker | Retention | Already planned after the site | L |

### Priority 3: later, optional, or only with more people

| # | Gap | Who has it | What the visitor gets | Why it matters to us | How, within our constraints | Effort |
|---|---|---|---|---|---|---|
| 41 | Ready-made share text on every statistic | Remote OK (a prefilled post link under each table) | Share one finding in a click | Word of mouth | Static | S |
| 42 | Small shareable tools | Levels.fyi (meeting-cost calculator, /cost/), Hirify (CV roast), TrueUp (/roasted/linkedin), Remote3 (headline and timestamp generators) | Something fun to pass around | Backlinks | In the browser; add to the tools set being built | S |
| 43 | Honest comparison pages and a directory of job boards | TrueUp (/job-boards), Jobright (reviews of rivals on its blog), We Work Remotely (blog round-ups, search only) | "Hiring Right Now vs X" with facts | Traffic on "X alternative" searches | Static; this file is the raw material. Facts only, dated, with sources | S |
| 44 | Per-page share images | Not verified on the reviewed sites (common practice) | A link preview showing the job title, company and pay | Better click-through from chats and social posts | Build-time images are heavy for 36,000 jobs; do companies and lists first, or render in the Worker | M |
| 45 | Sort by most viewed or most applied | Remote OK | See what others find interesting | Minor | Needs the counter from item 33 | M |
| 46 | Salaries submitted by users | Cryptocurrency Jobs (/salaries/share-your-salary/), Himalayas ("Add your salary"), Levels.fyi, Built In ("Recently submitted salaries") | Real pay, not only advertised ranges | More data, but easy to fake | Worker; needs abuse checks nobody is there to run. Keep advertised ranges as the honest source for now | M |
| 47 | Net-pay and tax calculator | Talent.com (/tax-calculator), Levels.fyi (/calculator/) | Take-home pay by country | Traffic | In the browser, but tax tables per country need yearly upkeep | M |
| 48 | Learning and events directories | web3.career (/learn-web3: curated outside resources by topic and level; crypto events), Remote3 (/web3-hackathons), YC (events), hh.ru (webinars) | Where to learn a skill; what to attend | Traffic | Needs curation by someone; the skill-gap hints could link to official documentation only | M |
| 49 | Referral and affiliate programme | Remote3 (affiliate programme), Remotive (/affiliate-program) | Earn by bringing employers or Plus buyers | Growth | Worker; queued in ROADMAP until payments are live | M |
| 50 | Map view of jobs | Huntr (map of target companies) | Jobs near a place | Minor for a mostly remote and big-city audience | In the browser | M |
| 51 | Layoffs tracker | TrueUp (/layoffs) | Which companies are cutting | Traffic and context | Depends on outside news data. Our own-data version is original idea A and G below | M |
| 52 | Company and interview reviews | Glassdoor and Indeed (search only), CryptoJobsList (company review pages, search only), hh.ru (employer rating by survey) | What it is like to work there | Big traffic, but needs moderation and invites fakes | Not now: no moderators, and "nothing fake" cannot be guaranteed. Original idea G is the measurable substitute | L |
| 53 | Community (chat, forum) | web3.career (Discord, 9,000 claimed), Remotive (Slack), Levels.fyi (/community), hh.ru (its own social network) | Peers to ask | Retention, but needs moderators | Not now | L |
| 54 | Skill tests and verification | hh.ru (skill verification with theory and practice) | A badge that proves a skill | Trust for a future résumé database | Large content job; only after item 38 | L |
| 55 | Country and language editions | Jooble (country sites), Arc (/en-de/ style country pages), Talent.com, LinkedIn | The site in the visitor's language | Traffic outside English | Queued in ROADMAP after the domain | L |
| 56 | Mobile apps | Jooble, Levels.fyi (/download), hh.ru | App-store presence, push | Retention | Planned by the owner | L |
| 57 | Human services | Levels.fyi (negotiation coaching from $1,250), hh.ru (ready-made résumé, mentor, psychologist), CryptoJobsList (success-fee recruiting), Wellfound (recruiter at $500/mo plus 10%) | Paid personal help | Money, but it sells people's hours | Not feasible with one owner. A partner referral (item 24) is the only fitting form | L |
| 58 | Built-in applicant tracking for employers | web3.career (free tracking with AI pre-screening), Wellfound, CryptoJobsList (hiring dashboard, search only) | Employers manage applicants on the board | Lock-in | Not recommended: our employers already use Greenhouse, Lever or Ashby, and we send candidates there | L |

---

## 3. What competitors do that we should not copy

| Practice | Where I saw it | Why not |
|---|---|---|
| Hiding job links or company names behind a payment | Remotive ("Unlock All Jobs"; its teaser says free users see "0.4% of available roles"), Working Nomads (Premium promises about 10x more postings), Hirify (Plus unlocks company names and apply links on its international list), FlexJobs (search only) | The job is not ours to sell. Our line "applying is free and happens on the employer's site" is a trust asset others cannot match |
| Countdown discounts | Remotive (/join: a "20% off" timer at 23:59:59) | Fake urgency; ROADMAP section 7 already forbids it. Original idea A gives urgency from real closing data instead |
| "3x views", "6x views" multipliers with no evidence | Remote OK (/hire-remotely), web3.career (/post-web3-job) | Numbers nobody can check. Publish measured results (item 33) or none |
| Auto-renew switched on by default | Remote OK (posts renew at the original price unless turned off). web3.career also sells auto-renew on the same card every 30 days; whether it is on by default was not clear | Leads to refund disputes. Renewal should be a choice |
| Dynamic or undisclosed prices | Remote OK ("dynamic pricing"), CryptoJobsList ("dynamic pricing", search only), Built In and ZipRecruiter (price only by demo or sales) | Our rule is self-serve with a public price list |
| Unattributed testimonials and numbers that disagree with each other | web3.career (two testimonials with first names only; city counts that differ on the same page), Remote3 (Telegram shown as 5,300+ and 3,800+), Remotive (150,000+ and 132,629+ jobs), Hirify (700+ sources on /about, 960+ Telegram channels on the home page, 1,000+ channels and 20,000+ career sites in llms.txt) | One number, dated, with its source. Ours come from the build, so keep them that way |
| Generated text with wrong facts on data pages | web3.career salary page (calls the US the lowest-paid country at $150k), Himalayas salaries (intro contradicts its own table; country averages built on a single salary) | Damages exactly the expertise signal such pages exist for. Keep minimum sample sizes and let the build write the sentences from the numbers |
| Estimated pay shown as if the employer stated it | Google's rules forbid estimates in `baseSalary`; Adzuna predicts pay for ads without it (search only) | Keep "advertised by the employer" and "our median for similar roles" visibly separate, as the job page does now |
| Sign-up wall before applying or saving | web3.career (apply buttons lead to sign-up), Himalayas ("Sign up to save this job"), LinkedIn (guest page) | "No account" is our difference; keep accounts for sync and paid features only |
| Paying to be ranked above other candidates | Remote OK (/faq: Premium at $14.95/mo includes higher placement in candidate lists; TopAccess $29.95/mo) | Sells hope and turns hiring into pay-to-win. Plus should sell speed and tools, never position in front of an employer |
| Trials that renew at a higher price, four-week billing | FlexJobs (search only, not verified) | One-time payments, as planned for Plus |
| Ads that look like job rows | Himalayas ("Sponsored" rows for an AI-apply product inside the list) | Paid placements must be labelled and visually distinct |
| Résumés visible to employers by default | Indeed (a third-party claim, not verified). The good pattern: Hirify keeps agent-made profiles hidden until the user switches them on | A future résumé database must be opt-in |
| "Give to get" walls | Glassdoor (help page blocked, not verified) | Forces low-quality contributions and blocks search engines from the content |
| Charging to hide the salary | CryptoJobsList, per a third-party listing (+$25, not verified) | The opposite of what candidates want; we reward showing pay |
| Mass auto-apply | Not confirmed on any reviewed site (Jobright and Huntr describe autofill, the user still submits) | Floods employers and gets a tool blocked; our extension should fill forms, not send them |

---

## 4. Original ideas none of the reviewed sites showed

All use what only we keep: daily snapshots of every posting, opening and closing dates, pay ranges, skills. "Nearest thing elsewhere"
is the closest feature I saw, so the owner can judge how new each idea is.

| # | Idea | Nearest thing elsewhere | What the visitor gets | Why it matters to us | How, within our constraints | Effort | Priority |
|---|---|---|---|---|---|---|---|
| A | Time-to-close benchmarks and an "apply window" line | Built In shows a "Reposted" badge; nobody showed how long roles stay open | "Roles like this at this company closed after a median of 18 days; this one is on day 11" | Real urgency instead of fake timers; a number employers will quote | Static, from closed jobs. Publish per company, category and level only above a minimum sample | S | 1 |
| B | Pay-transparency index | Sites show a salary filter; none ranks employers by how often and how precisely they state pay | Share of postings with pay and how wide the ranges are, by company, category and place; a badge for the best | Backlinks from companies that score well; a press-ready ranking | Static; add to insights and to the monthly report | S | 1 |
| C | Posting history: what changed | None seen | "Pay range raised on 4 Nov", "location added", "reposted after closing" on the job page; a feed of this week's raises | Trust; nobody else can show it without snapshots | `collect.py` keeps a small change log per job; static output | M | 1 |
| D | Public data-health page | Remote OK publishes market statistics, not pipeline health | Sources checked today, jobs added and closed, feeds that failed, average age of listings | Proof for "updated daily"; strong trust signal | Static, written by the daily workflow | S | 2 |
| E | Same role, different city | Levels.fyi compares pay by location from user reports | When one company posts the same title in several places with pay, show the gap side by side | Shareable; unique to advertised ranges | Static; group by company and normalised title | S | 2 |
| F | "Entry-level in name only" check | None seen | A flag when a junior or intern posting asks for 3+ years; share of such postings by category | Speaks to the most frustrated audience; quotable statistic | Needs the years parser from item 30; static | M | 2 |
| G | Employer scorecard built from facts | Reviews on Glassdoor and Indeed (opinions) | Per company: time to close, share of roles open 90+ days, pay shown, remote share, weekly opened and closed, each against the median | A substitute for reviews that needs no moderator and cannot be faked | Static; combines A, B and the existing hiring pulse | M | 2 |
| H | Apply-timing coach in "My jobs" | Huntr shows personal job-search metrics | "You usually apply on day 20; roles you pick close around day 25. Three saved jobs are past their usual window" | Retention; turns the tracker into advice | In the browser, with the benchmarks from idea A | S | 3 |
| I | Company stack changelog | Himalayas lists a tech stack; none shows change | "This quarter this company started asking for Rust (14 roles) and stopped asking for Ruby" | Insight for candidates and a reason for journalists to link | Static; compare skill counts per company between periods; becomes useful after a few months of history | M | 3 |
| J | Internship opening-date tracker | Simplify lists open internships | "Last year this company opened summer internships on 3 September" with a follow button | Returning student traffic every season | Static, but needs a year of history; start storing first-seen dates for internships now | M | 3 |

---

## 5. What I could not verify

- Glassdoor, ZipRecruiter, We Work Remotely, CryptoJobsList, Teal, Adzuna, HiringCafe: all pages returned 403. Remote.co and FlexJobs
  timed out. Everything about them is from search results and third-party pages.
- Indeed and LinkedIn: only public guest pages opened. Their signed-in features (one-click apply, labels on job rows, résumé
  visibility) are not described here from first-hand reading.
- Prices not found on an official page: web3.career's base post price, Remotive's and Simplify's job-seeker plans, Himalayas' and
  Hirify's employer prices, LinkedIn Premium, ZipRecruiter, FlexJobs, Teal, hh.ru (a third-party source gives postings from 3,900 RUB).
- Whether Stack Overflow Jobs closed on 2026-04-01 and whether Glassdoor merged into Indeed on 2026-07-01: single-source claims.
- Simplify's GitHub repository, web push on competitor sites, per-page share images on competitor sites: not checked.
- Bankless and Paradigm boards: their addresses only returned redirects (to share.hirechain.io and paradigm.xyz/careers), not followed.
- web3.career's interview-questions address returned 404; its learning directory has an "interview" filter but I saw no content.
- Hirify's source counts differ between its own pages, so its size claim is uncertain.
- On our side, marked "unsure" above: exclude filters, match percentage outside "For you", tracker extras, RSS for companies and
  locations, employer statistics in the written account, a "source checked" line on job pages.
- `build.py` was being edited by other work during this review (comparison pages appeared). Anything added after 2026-11-13 is not
  reflected here.
