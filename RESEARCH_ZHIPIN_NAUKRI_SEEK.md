# BOSS Zhipin, Naukri, SEEK: what they have, how people pay, what Jobs Every Hour should copy

Researched 2026-11-15 with web search and page fetches only (no browser). Written for Jobs Every Hour (jobseveryhour.com).

How to read this file

- **Opened** means I fetched and read the page myself. **Search only** means the site blocked automated reading (HTTP 403 or a
  loading screen) and the fact comes from search results, help pages, app-store listings, investor documents or the press.
  I did not try to get around any block.
- **Official** means the company's own filing, transcript, terms page or app-store listing. **Third party** means a blog, review
  site or news write-up. **Computed** means my own arithmetic from the numbers next to it. **Not verified** means I could not
  confirm it from a second source or from the company.
- Blocked on 2026-11-15: zhipin.com (job search and company pages show only a loading screen; the home page did open), every
  naukri.com page tried (403, including resume.naukri.com, naukri.com/naukri360, the blog, the FAQ and llms.txt), ambitionbox.com
  (403), seek.com.au, seek.co.nz and au.seek.com home pages (403). SEEK's career-advice page and its employer terms pages did open.
- Exchange rates are approximate and only for scale: US$1 = RMB 6.72 (the rate used in Kanzhun coverage, Aug 2026), US$1 ≈ ₹88,
  A$1 ≈ US$0.65. Check before using them in any price.
- Our side ("we probably do not have") was checked against `README.md`, `AGENT_NOTES.md`, `ROADMAP.md`, `config.json` and the
  `site/` folder as they stood today. "Queued" means it is already in `ROADMAP.md`.

---

## 0. The short version

1. **Employers carry the money everywhere.** Seekers pay about 0.9% of BOSS Zhipin's revenue (2025), about 7% of Naukri's
   recruitment billings (FY26, computed), and nothing at SEEK. BOSS is deliberately shrinking its paid seeker services to protect
   engagement.
2. **The fastest-growing lever at SEEK is price, not volume.** Ad volumes fell (Australia −2%), yet ANZ revenue rose 12% because
   yield rose 14%: prices that move with role, location and demand, plus a new middle ad tier. Premium and Advanced ads went from
   15% to 27% of paid ads in one year.
3. **Freemium with an upsell works for an aggregator-like site.** SEEK's free "Lite" ads in Asia: 11% of hirers bought a paid ad
   within six months of their first free ad, total ads up about 35%, unique hirers up about 30%. SEEK's terms also define
   "Aggregated Ads" (free re-posts from the employer's careers page), which is exactly what we already show for 130,000 jobs.
4. **AI is sold per outcome or as a pass, not hidden.** Naukri sells AI-Rex at ₹3,500 (≈US$40) per role to recruit, a "Live AI
   Interviewer" at ₹749 to ₹999 (≈US$8.5 to 11) to seekers, and a Naukri Pro pass at ₹999 / ₹1,999 / ₹2,999 for 1 / 3 / 6 months.
5. **Credits and prepaid budgets** (BOSS "直豆" coins at ¥1 each, SEEK Ad Budgets that expire, SEEK Talent Search credits) fit a
   crypto-only site well: one top-up, many small purchases.

The 10 ideas most worth copying are in section 5.

---

## 1. BOSS Zhipin (zhipin.com, Kanzhun Ltd, NASDAQ: BZ, HKEX: 2076)

China's largest recruitment app by users. Core idea: "直聊" (direct chat). The button on a job says "立即沟通" (chat now), not
"apply"; the seeker talks straight to the hiring manager or owner. A résumé or phone/WeChat number is exchanged only when both sides
agree. Employers pay; seekers are mostly free.

### 1.1 Site map (home page opened 2026-11-15)

- **Header:** logo with tagline "找工作 BOSS直聘直接谈" (find a job, talk directly); city switcher (全国 = nationwide).
- **Main menu:** 首页 Home · 职位 Jobs · 公司 Companies · 校园 Campus · 海归 Returnees (Chinese graduates of foreign universities) ·
  APP · 有了 "Youle" (purpose not confirmed) · 海外 Overseas · 无障碍专区 Accessibility zone.
- **Two role buttons:** 我要招聘 "I want to hire" and 我要找工作 "I want a job"; log-in by scanning a QR code with the app; WeChat
  one-tap sign-up.
- **Search:** job-type dropdown, a **map search** (地图), search button; 10 hot keywords under the box.
- **Job-type menu:** 28 top categories with sub-categories, including blue-collar ones (技工/普工 skilled/general workers, 餐饮
  catering, 物流/仓储/司机 logistics and drivers, 直播 livestreaming).
- **Hot openings (热招职位):** tabs by sector, cards showing company, city, experience, education.
- **Popular companies (热门企业):** Meituan, Baidu, JD and others. **Hot cities (城市热招):** 25 cities.
- **Floating panel on the right:** 反馈 Feedback · 感兴趣 Interested · 沟通过 Chatted · 已投递 Applied · 面试 Interview (a personal
  application pipeline).
- **Footer, column "企业服务" (services):** Job search · BOSS Zhipin app · Investor relations · Zhipin charity foundation ·
  Job-seeking tips (求职技巧).
- **Footer, column "使用与帮助" (use and help):** Agreements and rules · Privacy policy · **Anti-fraud guide (防骗指南)** · Help centre.
- **Footer, column "联系BOSS直聘" (contact):** company name and address; report e-mail for illegal content and for minors.
- **Footer, hotlines:** enterprise service and **algorithm / minors complaint line** (400 065 5799); **a separate hotline for older
  people** (400 661 6030); hours 8:00 to 22:00 every day.
- **Footer, apps and social:** Weibo, WeChat account, app download, **PC desktop app**.
- **Footer, "友情链接" (partner links):** sister sites 店长直聘 (store-manager hiring, retail/blue-collar), 留学生招聘 (overseas
  students), part-time, Cantonese and traditional-Chinese entry pages ("請人", "搵工"), an English "jobs" page, **OfferToday**
  (Kanzhun's Hong Kong app); 12 "<city> 招聘" city pages; outside sites (Tianyancha company lookup, CSDN and others).
- **Footer, legal:** ICP licence, business licence, police filing, **HR services licence**, **algorithm filing information**,
  local labour-bureau supervision phone.

### 1.2 (a) Features and page types we probably do not have

- **Direct chat with the hiring person instead of an apply button**, with résumé or contact shared only after both agree (core
  product; official app listing, opened).
- **Two-sided recommendation feed:** seekers get suggested jobs, recruiters get suggested candidates ("牛人") who are online now
  (app listing; third-party write-up).
- **Employer verification:** real-person check and on-site visits before a company can hire (official app listing).
- **AI risk calls and alerts to seekers:** more than 50 million risk alerts sent in Q2 2025; 43 police cases, 326 arrests since
  start of 2025 (The Paper, 2025-08-21; company figures quoted).
- **Anti-fraud guide page** linked in the footer (opened).
- **Personal pipeline tracker on every page:** Interested / Chatted / Applied / Interview (opened).
- **Map search for jobs** (opened).
- **Accessibility zone** for disabled job seekers (opened).
- **Returnees zone** (海归) with study-abroad verification and tailored jobs (app listing via search).
- **Campus section** for students and graduates (opened).
- **Overseas section** and the English-language sister app **OfferToday** (Hong Kong; WhatsApp chat with employers, suggested
  opening lines; App Store via search).
- **Live-stream recruiting** (直播招聘) (official app listing).
- **Interview question practice** (面试刷题) and an **AI mock-interview robot** that feeds results back into recommendations
  (app listing; The Paper 2025-08-21).
- **AI search with job-search strategy and résumé advice**, built on DeepSeek-R1 and Kanzhun's own "Nanbeige" (南北阁) models
  (The Paper 2025-08-21).
- **"千岗千面" (a thousand jobs, a thousand faces):** each candidate's strengths are re-ordered for each job before the recruiter
  sees them (The Paper 2025-08-21).
- **Recruiter tools:** AI help writing job posts, team (collaborative) hiring, interview scheduling, weekly hiring reports
  (app listing).
- **Senior hotline and algorithm-complaint channel** in the footer (opened).
- **PC desktop app** (opened).
- **Sister brands for other audiences:** store/retail hiring (店长直聘), overseas students, part-time (opened, footer).
- **Charity foundation page** and **investor relations** link in the footer (opened).
- Not confirmed: what "有了" (Youle) is; the full search filter list (the search page showed only a loading screen).

### 1.3 (b) How job seekers pay

| Product | Price | What it does | Source |
|---|---|---|---|
| 找工作VIP会员 (job-seeker VIP), 30 days | ¥68 (≈US$10) | Job "competitiveness analysis" (how you rank among other applicants), filtering of unwanted messages, more | App Store CN in-app purchases, opened 2026-11-15 (official) |
| The eight VIP rights as described in 2023 | ¥68 a month | Résumé refresh pro (auto refresh daily), competitiveness analysis (3 a day), exclusive résumé templates, priority reminder to the boss, message filtering, personal data report, career personality test, VIP badge | ITHome / Digitaling 2023 (third party) |
| 直豆 (zhidou coins) | ¥1 per coin; packs of 1 and 30 seen | Wallet currency for one-off "props" (道具) | App Store CN, opened (official). The list of props and their prices: **not verified** |

- Scale: "Other services, mainly paid value-added services for job seekers" were **RMB 74.8 m in 2025** (down from 85.7 m in
  2024), about **0.9% of revenue** (computed from the full-year release, figures via a press summary). Q3 2025: RMB 16.4 m, −27%;
  Q2 2026: RMB 14.6 m vs 24.8 m. The company says it "optimised and streamlined some value-added services to enhance stickiness"
  (Bamboo Works Chinese edition via search; Business News Today 2026-08). **Lesson: BOSS chose engagement over charging seekers.**

### 1.4 (c) How employers pay

| Product | Price | Notes | Source |
|---|---|---|---|
| Job post (职位发布), 30 days | ¥30, 60, 78, 88, 98 or 118 (≈US$4.5 to 17.6) | Several price points; which applies depends on the job (see "competitive jobs") | App Store CN in-app purchases (official) |
| VIP account (VIP账号), 30 days | ¥50 (≈US$7.4) | More daily chats and views (exact quotas **not verified**) | App Store CN (official) |
| 直豆 coins | ¥1 each | Used for props such as extra exposure or chats (**not verified** item by item) | App Store CN (official) |
| "竞招职位" competitive jobs | Varies | A role in a city where many employers post the same job and supply is short is automatically marked "competitive" and must be paid for; other roles stay free. Price depends on the package; a yearly package does not give unlimited views of applicants for these jobs | Jiemian (third party, quoting BOSS customer service) |
| Standard position (2023 report) | ¥288 a month | About 20 candidate chats a day | ITHome 2023 (third party) |
| "All rights" spend (2023 report) | About ¥3,600 a month | Résumé viewing, chats and more exposure all cost extra | ITHome 2023 (third party) |
| Annual packages | ¥16,800 to ¥38,800 a year | Said to be about 3× Zhaopin/51job | Substack "theoria137" (third party, **not verified**) |
| Seasonal pricing | Lower, sometimes free, in low season | Posting prices fall or posting becomes free when hiring demand is low | Chinese press summary found by search (**not verified**) |

- Free side: seekers chat free; recruiters can often post free roles and see applicants who contact them (third party).
- Complaints to avoid copying: price hikes at renewal, posts taken down until payment (2022 reports), paid "chat cards" with
  hidden limits (ITHome, Black Cat complaints via search).

### 1.5 (d) Revenue facts

| Fact | Figure | Date / source |
|---|---|---|
| Revenue 2025 | RMB 8,267.5 m (US$1,182.2 m), +12.4% | FY2025 release, 2026-03-18 (official, via syndicated copies) |
| Of which enterprise recruitment | ≈ RMB 8,192.7 m (99.1%) | Computed: total minus "other services" RMB 74.8 m |
| Paid enterprise customers, 12 months to 2025-12-31 | 6.8 m (call: 6.83 m), +11.5% | FY2025 release and Q4 call (call summary via search; transcript page timed out) |
| Revenue per paying enterprise customer, 2025 | ≈ RMB 1,200 a year (≈US$179) | Computed: 8,192.7 / 6.83. Management said ARPPU stayed "broadly stable" (call summary, **not verified**) |
| Average MAU 2025 | 60.7 m, +14.5% | FY2025 release |
| Net income 2025 / adjusted | RMB 2,690.5 m / RMB 3,602.5 m | FY2025 release |
| "达成" matches in 2025 (both sides agree and swap résumé or contacts) | 2.27 bn, +22.4% | Chinese press summary via search |
| Q2 2026 revenue | RMB 2,398.6 m (US$353.5 m), +14.1% | Q2 release 2026-08-25 (via Staffing Industry Analysts, HKEX listing) |
| Q2 2026 enterprise / other services | RMB 2,384.0 m / RMB 14.6 m | Same |
| Paid enterprise customers, 12 months to 2026-06-30 | 7.2 m, +10.8% | Same |
| Average MAU Q2 2026 | 70.2 m, +10.4% (first time above 70 m) | Same |
| Q3 2026 guidance | RMB 2.41 to 2.50 bn (+11.4% to 15.6%) | Same (Q3 2026 results not out on 2026-11-15) |
| Overseas | OfferToday live in Hong Kong since 2024; Brazil, Vietnam, Argentina being prepared; goal about US$100 to 115 m revenue in about five years after entry | Bamboo Works / Sahm Capital 2026-08-28 (third party) |
| Shareholder returns | At least 50% of prior-year adjusted net income returned each year, 2026 to 2028 | FY2025 release |

### 1.6 (e) Five ideas from BOSS Zhipin worth copying

1. **Charge only where demand is crowded ("competitive jobs").** Keep posting free; make the Featured price depend on how many
   employers fight for the same role and place (software engineer, remote, US) and keep quiet categories cheap.
2. **A coin wallet.** One crypto top-up, spent in small pieces (feature, pin, bump, extra days). 1 credit = US$1, like 1 直豆 = ¥1.
3. **Tiny, self-serve prices at huge volume.** BOSS earns about US$179 a year per paying employer from 7.2 m payers; its posts cost
   US$4.5 to 17.6 for 30 days. Add a US$5 to 9 "bump to top" and a 30-day "extend" next to the US$29 Featured.
4. **Show seekers where they stand, free.** A "how you compare" panel on a job (your skills vs the job, and vs other people who
   checked this job with our résumé tool) is BOSS's "competitiveness analysis". BOSS charges for it; we should give the basic
   version free and keep a deeper version in Plus.
5. **Trust stack on every page.** Verified-employer badge, a scam guide linked in the footer, a "report this job" button, and the
   personal pipeline (Interested / Applied / Interview) kept in the browser without an account.

---

## 2. Naukri.com (Info Edge India Ltd, NSE: NAUKRI)

India's largest job site. About 118 million résumés, 25,000 new profiles a day (Q1 FY27 call, Aug 2026). Its money comes mainly
from employers searching that résumé database ("Resdex"); seekers pay for visibility, AI tools and résumé writing.

### 2.1 Site map (every naukri.com page returned 403; search only)

- **Jobs menu:** Popular categories (IT, Sales, Marketing, Data Science, HR, Engineering) · Jobs in demand (Fresher, MNC, Remote,
  Work from home, **Walk-in**, Part-time) · Jobs by location (search snippet of a cached Naukri page).
- **Companies menu:** Explore categories (**Unicorn, MNC, Startup, Product based, Internet**) · Explore collections (top, IT,
  fintech, **sponsored companies**) (same).
- **Browse pages:** Jobs by category, by skill, by location, **by designation** (search snippet).
- **Services menu:** résumé writing, priority applicant, résumé display, Naukri 360 (from app listing and third-party pages; menu
  wording **not verified**).
- **Footer (partly confirmed):** "Connect with us": About us, Careers, Employer home, Sitemap; legal links **Grievances** and
  **Summons and Notice** (older page); fraud pages: security centre, jobseeker fraud alert, trust site trust.naukri.com,
  compliance e-mail. "Credits" and a "Trust & safety" label: **not verified**.
- **Group sites:** NaukriGulf, iimjobs (MBA), hirist (tech), AmbitionBox (company reviews and salaries), JobHai (value/blue-collar),
  Naukri Campus (freshers), Zwayam (ATS), DoSelect (assessments).

### 2.2 (a) Features and page types we probably do not have

- **Recruiter-searchable résumé database (Resdex)**, with opt-in profiles and recruiter search, filters and bulk e-mail
  (Internshala guide 2026-09; queued as "résumé database").
- **Profile performance panel for seekers:** search appearances, recruiter actions, who viewed (official App Store listing).
- **Recruiter job invitations**, including "hidden job invitations" for Pro users (App Store; Editorji).
- **Video profile** for seekers (App Store).
- **AI mock interviews**: used by 1.5 million people a month (Q4 FY26 call, official); a paid **Live AI Interviewer** (App Store).
- **AI résumé generation** powering 3 million profiles a month (Q4 FY26 call).
- **Jobseeker AI agent "Neo"** (Q1 FY27 call, official).
- **Naukri Minis:** short career news and salary insights in the app (App Store; Q1 FY27 call).
- **Walk-in jobs** category and **jobs by designation** pages (search snippets).
- **Company hubs by type:** Unicorn, MNC, Startup, Product-based, Internet, fintech, **sponsored company collections**.
- **Company reviews, salaries and interview questions** (AmbitionBox, a separate Info Edge site linked from company pages).
- **Monthly hiring index "JobSpeak"** quoted by the press (Q4 FY26 call).
- **Fraud centre and trust site** (search).
- **Grievances / legal notices pages** (India-specific).
- **Campus portal with its own test (NCAT)** and free résumé builder for freshers (third party).
- **Premium sub-brands and a premium database (PremiumX)** for high earners, currently free to recruiters (Q1 FY27 call).
- **Upskilling bootcamps** (AI Engineer and Career bootcamps, ₹5,999) and the Coding Ninjas acquisition (App Store; Q1 FY27 call).
- **Salary and talent intelligence for employers** (Talent Pulse, Salary Pulse) (Q1 FY27 call).
- **Up to 5 custom job alerts** in the app (App Store FAQ); e-mail alerts are queued for us.

### 2.3 (b) How job seekers pay

Official (App Store India in-app purchases, opened 2026-11-15):

| Product | Price (INR) | ≈ US$ |
|---|---|---|
| Naukri Pro, 1 month | ₹999 | 11 |
| Naukri Pro, 3 months | ₹1,999 | 23 |
| Naukri Pro, 6 months | ₹2,999 | 34 |
| Live AI Interviewer | ₹749 or ₹999 | 8.5 to 11 |
| AI Engineer Bootcamp / Naukri Career Bootcamp | ₹5,999 each | 68 |
| Résumé writing service | ₹4,699, ₹5,700 or ₹7,099 | 53 to 81 |

Naukri Pro includes the AI résumé maker, profile enhancement, hidden job invitations, AI mock interviews and skills insights
(Editorji; date unclear).

"FastForward" services (HRCabin list, page undated, comments to May 2026; third party, **not verified**; other sources give much
higher prices):

| Service | Price | What it does |
|---|---|---|
| Resume Display | ₹1,335 (3 mo) / ₹1,899 (6 mo) | Featured tag and more visibility to recruiters searching the database |
| Priority Applicant | ₹617 (3 mo) / ₹825 (6 mo) | Applications highlighted to recruiters; up to 2 job SMS a day |
| Jobs for You | ₹890 (3 mo) / ₹1,364 (6 mo) | Hand-picked jobs within 30 minutes of posting; up to 3 job SMS a day |
| Recruiter Connection | ₹587 (5 credits), ₹979 (10), ₹1,661 (20) | Message recruiters directly |
| Resume Critique | ₹712 | Expert review |
| Resume Writing | ₹1,158 (0 to 1 yr) up to ₹4,183 (15+ yrs) | Written by experts by experience band |
| Interview Preparation | ₹1,602 | Mock interview plus 30 min with an HR expert |

- Older receipts: Priority Applicant 1 month ₹495 (Scribd, 2023). A March 2026 blog quotes Resume Display ₹5,900 to ₹7,200 for
  3 months; the sources disagree.
- None of these guarantees interview calls; no refund if calls do not come (third-party guides).
- Scale (official): Naukri Jobseeker Services billings **₹176 crore in FY26** (≈US$20 m), +19%, 57% operating margin; Q4 FY26
  billings ₹53 crore (+33%, 60% margin). Paid users rose from 1.2% to **2.2% of monthly active users** in 15 months (Q4 FY26
  call), then to **2.6%** (Q1 FY27 call). Online self-serve share of seeker revenue went from 27% to 53% in 15 months. Billings
  grew over 35% in Q1 FY27 on AI products (Neo, AI mock interview, AI résumé builder); AI is "closer to 7-8%" of jobseeker revenue
  run-rate (Q1 FY27 call).

### 2.4 (c) How employers pay

| Product | Price | What you get | Source |
|---|---|---|---|
| Classified job post | ₹850 (metro) / ₹400 (non-metro) (≈US$9.7 / 4.5) | 250-character description, up to 3 locations, 30 to 90 days | Internshala guide, updated 2026-09-21 (third party, quoting Naukri's guide) |
| Hot Vacancy job post | ₹1,650 (≈US$19) any city; 3 posts ₹4,950 | Full description, search boost, branding, priority placement, analytics | Same; deepaksood analysis (third party) |
| Resdex Lite | ₹4,000: 1 requirement, 100 CV views; ₹10,500: 3 requirements, 300 CV views (≈US$45 / 119) | Up to 500 search results, candidates active in last 6 months, 10+ filters, 1 user, 90 days | Internshala (third party) |
| Resdex (full) | Custom; one source says ≈₹55,000 for 3 months entry, enterprise far higher (**not verified**) | Unlimited results, 20+ filters, multiple users, bulk e-mail, Boolean search, bulk CV download | Internshala; deepaksood (third party) |
| AI-Rex (agentic AI recruiter) | **₹3,500 per role ("mandate") for companies, ₹2,500 for recruitment agencies** (≈US$40 / 28), launch price | Takes the job, searches, screens and delivers a shortlist, often within 24 hours | Q1 FY27 call, 2026-08-10 (official) |
| Talent Pulse / Salary Pulse | Not public | Salary benchmarking and talent planning data; 600 to 700 paid customers | Q1 FY27 call (official) |
| Employer branding, assisted hiring, assessments | Not public | Sold on top of database access | Q1 FY27 call |

- AI-Rex adoption: live at more than 4,000 enterprise and agency customers by end of June 2026 after free trials; over 10% (about
  400) paid in Q1 and about 300 more in July (official). Earlier: 1,000 clients and 30,000 roles on AI-Rex (Q4 FY26 call).
- Price rises: Resdex and LinkedIn raise prices about 15% (sometimes 25%) a year (Cutshort survey of hiring leaders, 2025-10-10).
- Naukri does not charge separately for most AI; it uses AI to justify renewals and higher prices, and sells AI separately only
  where it is a stand-alone product like AI-Rex (Q1 FY27 call).

### 2.5 (d) Revenue facts

| Fact | Figure | Date / source |
|---|---|---|
| Recruitment billings FY26 (standalone) | ₹2,374 crore (≈US$270 m), +10% | Q4 FY26 call 2026-05-28 (official transcript, opened) |
| Recruitment revenue FY26 (standalone) | ₹2,256 crore, +14%; operating margin 57% | Same |
| Incl. Zwayam and DoSelect | Billings ₹2,461 crore, revenue ₹2,343 crore | Same |
| Info Edge standalone revenue FY26 | ₹3,052 crore, +15% | Same |
| Jobseeker services FY26 | ₹176 crore billings, +19%, 57% margin = **≈7.4% of recruitment billings** | Same; share computed |
| Billings by sector FY26 | IT services 19% of billings; other sectors 29%; GCCs +10%; consultants +6% | Same |
| Q1 FY27 (Apr to Jun 2026) | Recruitment billings +17% (≈15% underlying), revenue +13%, margin 58%; 8 points of growth from higher prices per customer, 4 from more billing customers | Q1 FY27 call 2026-08-10 (official, opened) |
| Q2 FY27 (Jul to Sep 2026) | Recruitment billings ₹613.8 crore (+12.6%), revenue ₹632.3 crore (+13.3%), segment profit ₹373.7 crore (+19.9%), margin 59.1% | Press 2026-10-28/29 (CXO Digital Pulse, Staffing Industry Analysts) |
| AI and data products | ≈₹240 crore annualised run rate, a high-single-digit share of recruitment revenue | Q2 FY27 release coverage, 2026-10-29 |
| Résumé database vs job posts | Résumé database access 68.4%, job listings 9% of recruitment revenue (FY2023-24) | Secondary write-up (yespress.io) only; **not verified** in the annual report |
| Leadership | Founder Sanjeev Bikhchandani returns as CEO; Hitesh Oberoi steps down | Moneylife / Staffing Industry Analysts, Oct 2026 |

### 2.6 (e) Five ideas from Naukri worth copying

1. **Sell AI to seekers as passes and single sessions.** Keep Plus (1/3/12 months, one payment) and add a single "AI mock
   interview" or "AI résumé rewrite for this job" at about US$5 to 9. Naukri's paid share of MAU doubled to 2.6% mostly through
   these self-serve AI products.
2. **A paid shortlist per role (AI-Rex model).** The employer names a role; we send a shortlist from people who opted in through
   our résumé builder. Price per role (Naukri: ≈US$40), free trial first (Naukri: 10% of trials paid).
3. **A small, fixed-price database pack (Resdex Lite model).** "100 profile unlocks for 90 days" at a fixed price, bought online,
   no sales call. Needs the opt-in candidate pool (queued).
4. **Hiring and salary data as a product (Talent Pulse model).** We read 130,000 jobs every hour: sell a monthly "who is hiring
   what, at what pay" dashboard or API tier to employers, agencies and investors.
5. **A named monthly hiring index (JobSpeak model).** One number per month, published on a fixed day, with a short press note.
   It earns press links and AI-search citations for free.

---

## 3. SEEK (seek.com.au, SEEK Ltd, ASX: SEK)

Australia's leading job site (also SEEK NZ, Jobstreet and Jobsdb in Asia, and the aggregator Jora). About 35.5% placement share in
ANZ, 4× its nearest competitor in Australia (FY26 results presentation). seek.com.au now redirects to au.seek.com.

### 3.1 Site map (home pages 403; footer read from au.seek.com/career-advice, opened 2026-11-15)

- **Career advice hub:** Explore careers · Explore salaries · Job hunting · Working life; sections "Latest career advice", "Browse
  careers by industry", "Changing careers", "Getting ready for an interview?", "Job & salary trends", newsletter.
- **Tools on the hub:** résumé template, cover letter template, **job trends explorer**, **transferable skills checklist**,
  **practice interview tool**, **salary calculator**.
- **Footer, Job seekers:** Job search · Profile · **People search** · Saved searches · Saved jobs · Applied jobs · Career advice ·
  Explore careers · Explore salaries · **Companies** · **Recruiters** · **Graduates**; Download apps (Android, iOS); SEEK sites:
  Employer site, SEEK NZ, **Volunteering**, Business.
- **Footer, Employers:** Register for free · Post a job ad · **Products & prices** · Customer service · Hiring advice · **Market
  insights** · **Recruitment software partners**.
- **Footer, About us:** About SEEK · Newsroom · Investors · Careers; International partners: Bdjobs, Jobsdb, Jobstreet, Jora
  (Australia), Jora (Worldwide); **Partner services: SEEK Pass, Sidekicker, GO1, FutureLearn, JobAdder**.
- **Footer, Contact:** Help centre · Contact us · **Product & tech blog** · **SEEK videos**; Facebook, Instagram, Twitter, YouTube.
- **Bottom bar:** Terms & conditions · Security · Privacy.

### 3.2 (a) Features and page types we probably do not have

- **Candidate profile with visibility levels** (Standard, Public, Limited, Hidden/"Applications only") and a separate
  **"approachability" signal** (SEEK profile-privacy pages via search).
- **Verified credentials (SEEK Pass):** right to work, licences, education, IELTS/PTE, work history; >16 m verified credentials;
  >65% of ANZ applications come from candidates with verified credentials; verified applicants 20% more likely to be shortlisted in
  ANZ (FY26 presentation; SEEK Pass pages, company claims).
- **Career feed and AI "career agent"** that recommends roles, gives guidance and updates the profile (FY26 presentation).
- **People search** (footer) and **recruiter directory with ratings and reviews**; recruiters list free, hirers can use "Find a
  Recruiter" with a 90-day money-back promise (SEEK/Sourcr pages via search).
- **Company profiles with reviews** (EVP products require a profile with at least three reviews; product terms, opened).
- **Explore careers role pages** with typical salary and a **job satisfaction rating** per role (opened).
- **Transferable skills checklist, practice interview tool, job trends explorer** (opened). We have a résumé builder, salary pages,
  trends and 30 tools, so these are partial gaps.
- **Graduates hub** and a **volunteering** site (footer).
- **Market insights and SEEK Job Ad Index** for employers and press (footer; FY26 presentation).
- **Recruitment software partners page:** >130 ATS integration partners (footer; FY26 presentation).
- **Sidekicker** on-demand casual staff (footer; part of SEEK revenue).
- **Course partners** GO1 and FutureLearn in the footer (likely affiliate or partner revenue; terms **not verified**).
- **Employer AI tools inside ads:** AI voice pre-screen, reference checks, candidate invitations, "Likely Interested" candidate
  matches, personalised targeting, fit explanation for every candidate, ad performance dashboard with "high-fit" application counts
  (product terms, opened; Jobsdb product page, opened; FY26 presentation).
- **Mandatory login for candidates** (new in FY26; more high-fit applications, smaller drop in visits than feared; FY26
  presentation). We deliberately stay no-account; noted, not recommended.

### 3.3 (b) How job seekers pay

- **Nothing.** SEEK sells no seeker subscription; seeker products (profile, SEEK Pass verification, career tools, career agent) are
  free. Verification through SEEK Pass is free in AU/NZ (SEEK Pass pages via search). Courses go through partners (GO1,
  FutureLearn). Revenue lines in the FY26 results are job ads, ad enhancements and "expanded sourcing solutions and other".

### 3.4 (c) How employers pay (product terms "last updated 2 November 2026", opened)

| Product | Price rule | What it includes |
|---|---|---|
| Lite Ad (Asia; free at SEEK's discretion) | Free | Low exposure; can buy add-ons |
| Aggregated Ad | Free | SEEK re-posts the employer's job from its careers page or other sources, shown like a Lite ad |
| Basic Ad (formerly Classic) | **Variable** | Title and short description in results; 30 days |
| Branded Basic | Variable | + logo, cover image, 3 selling points |
| Advanced Ad (launched H2 FY25 in ANZ) | Variable | + more exposure in search and candidate e-mails; shown on similar ads |
| Branded Advanced | Variable | Advanced + branding |
| Premium Ad | Variable | Branded Advanced + most prominent and frequent placement in search, partner sites (Jora) and e-mails; **exclusive: similar roles are not promoted on a Premium ad**; sent as exclusive recommendations to high-fit candidates |
| Concierge Ad | Fixed (not variable now) | SEEK drafts the ad, then runs it as Premium; paid in full first; select roles |
| **Guaranteed Hire Ad** | Fixed | Concierge + **money back if nobody is hired within 4 weeks after the ad ends** (claim within 28 days, evidence needed; no refund on a repeat ad for 6 months) |
| Add-On Badge | Fixed fee | Visual badge only, no ranking change |
| Assist credits | In paid ads | AI pre-screens and reference checks; valid 180 days |
| Role Insights | Fixed monthly fee | Market data tool; auto-renews up to 6 months |
| EVP products (beta) | Fixed fees | Company Profile Boost, Graduate Booster, Career Feed Spotlight, Graduate EVP Banner, Company Search Carousel, Graduate Landing Page Carousel |
| Display advertising | Campaign | Banners on SEEK sites |
| Ad Budgets (Flexible, Branded, Branded Plus) | Prepaid; discount by committed spend | Pay the whole budget even if unused; unused amount expires at the end of the term; optional overage at the agreed discount |
| Premium Talent Search | Commercial agreement | Credits: **Send Job 25, Send Message 50, Access Profile 200** (credit price not public); "Candidate Matches" free with every ad (talent-search terms, 2026-07-20, opened) |

- **How the variable price is set:** candidate supply and demand, average salary and location; every extra location is a separate
  full-price ad; a public **price checker** exists at au.employer.seek.com/account/ad-price-lookup (needs a free account). Variable
  pricing started on 1 December 2019 for renewing contracts; customer-type discounts (big agencies) were phased out in favour of
  discounts by committed annual spend (ASX release 2019-10-21).
- **Actual dollar prices are not published.** A guide checked in July 2026 lists Ad Budgets of A$3,700 (about 8 to 12 ads),
  A$5,000 (13 to 16) and A$7,500 (21 to 30), i.e. roughly A$250 to 460 (≈US$160 to 300) per ad; single ads cost more
  (100hires, third party, **not verified**).
- **Jora (SEEK's own aggregator, like us):** free basic ads (limit given as 10 to 100 a month depending on the source), paid
  sponsored upgrades "Plus" A$69 and "Max" A$99 (≈US$45 / 64) (third-party listings via search, **not verified**).

### 3.5 (d) Revenue facts (FY26 = year to 30 June 2026; ASX announcement and results presentation 2026-08-12, opened)

| Fact | Figure |
|---|---|
| Net revenue | A$1,199 m (≈US$780 m), +10%; sales revenue A$1,284 m |
| ANZ revenue | A$945.4 m, +12%: core job ads and enhancements A$845 m; expanded sourcing and other A$100 m |
| Asia revenue | A$253.5 m, +3% (+5% constant currency) |
| EBITDA / adjusted profit | A$530 m (+15%, 44% margin) / A$199 m (+28%) |
| Yield (revenue per paid ad) | +18% across APAC, sixth year in a row of double-digit growth; ANZ +14%, Asia +20% |
| ANZ yield growth by year | FY23 8%, FY24 13%, FY25 13%, FY26 14% |
| Volumes | Australia −2%, New Zealand +8%, ANZ −1%; Asia paid ads −12% (freemium shift) |
| **Depth adoption, ANZ (Advanced + Premium as % of paid ads)** | FY23 10%, FY24 10%, FY25 15%, **FY26 27%** |
| ANZ ad mix FY26 (FY25) | Basic 73% (85%), Advanced 17% (5%), Premium 10% (10%) |
| ANZ ad revenue mix FY26 (FY25) | Basic 47% (60%), **depth 42% (28%)**, enhancements 11% (12%) |
| Asia ad mix / revenue | Basic 73% (86%), Advanced 14% (1%), Premium 13% (13%); depth revenue 41% (27%) |
| Why yield grew | More depth ads after the new tiers; value-based pricing tied to customer ROI (more high-fit applications); inflation-linked price rises; fewer volume discounts |
| **Freemium in Asia** | Rolled out PH May 2024 → MY Feb 2026; **11% of hirers bought a paid ad within 6 months of their first free ad**; ≈35% more total ads, ≈30% more unique hirers and visitors; paid ad yield +17% CAGR since; freemium "enabled higher paid ad prices due to a clear link between performance and price" |
| Scale | >60 m candidate profiles, >360k hirer relationships, >130 ATS partners, 91% unaided brand awareness in Australia |
| FY27 guidance | Revenue A$1,210 to 1,280 m; target yield growth at least 10% a year through the cycle |

### 3.6 (e) Five ideas from SEEK worth copying

1. **Add a middle tier and make Premium exclusive.** Free → Featured → Premium, where Premium also e-mails matching seekers and
   shows no competitor jobs on its page. SEEK's middle "Advanced" ad lifted depth ads from 15% to 27% of paid ads in a year.
2. **Variable prices by role and place, with a public price checker.** A "what would it cost to feature this job?" page that
   prices from our own data (how many open jobs in that category and city, average salary).
3. **Claim and upgrade for aggregated jobs.** SEEK shows employers' careers-page jobs free as "Aggregated Ads" and upsells; 11% of
   free hirers pay within six months. We already list 130,000 such jobs: add "Is this your job? Claim it and feature it" on every
   job and company page.
4. **Guarantees and done-for-you.** A "Concierge" option (we write or fix the job post) and a guarantee measured on our own data,
   for example a free re-run if a Featured job gets fewer than N apply clicks in 14 days.
5. **Prepaid budgets and credits.** Annual or 6-month prepaid budgets with a bigger discount for bigger commitments; unused balance
   expires; and per-action credits (send job 25, message 50, unlock profile 200) once a candidate pool exists.

---

## 4. Side by side

| | BOSS Zhipin | Naukri | SEEK |
|---|---|---|---|
| Who pays | Employers (99%) | Employers (≈93%), seekers (≈7%) | Employers (≈100%) |
| Main thing sold | Chat access and job posts, cheap and self-serve | Résumé database access (Resdex), then job posts | Job ads by tier, prices by demand |
| Seeker paid products | VIP ¥68/month, coins; being cut back | Pro ₹999 to 2,999; AI interviewer; visibility boosts; résumé writing | None |
| Free tier for employers | Many roles free; "competitive" roles paid | Free plan with limited visibility (third party) | Lite and Aggregated ads (Asia), Candidate Matches free |
| Price model | Per post, VIP, coins, packages; demand-based for crowded roles | Fixed rate card for posts; database by views and seats; AI per role | Variable by role, location, salary; prepaid budgets; credits |
| AI sold how | Mostly free, to raise matches | AI-Rex per role; Pro and AI interviewer for seekers | Built into tiers (more AI help in higher tiers) |
| Growth driver 2026 | More paying employers (+10.8%) | Higher price per customer (8 of 13 points) | Higher yield (+14% ANZ) with flat volume |

What not to copy: forced payment to keep a post online, renewal price shocks, chat "cards" with hidden limits (BOSS complaints);
paid visibility for seekers that promises nothing and has no refund (Naukri complaints); mandatory login (SEEK).

---

## 5. Top 10 ideas for Jobs Every Hour (free, no account, international, crypto-only, US$1M+ a year)

Ordered by money per unit of work. "Needs" says what must exist first.

| # | Idea | Copied from | Evidence | Needs |
|---|---|---|---|---|
| 1 | **Claim-and-upgrade on every aggregated job and company page** ("Is this your job? Feature it for $29") plus a monthly e-mail to companies we list | SEEK Aggregated/Lite ads | 11% of free hirers bought a paid ad within 6 months; +30% hirers | Checkout live (server), contact e-mails |
| 2 | **Three-tier ladder with an exclusive Premium**: Featured (highlight) → Premium (top, e-mail to matching seekers, no competitor jobs on its page, logo) | SEEK Advanced/Premium | Depth ads 15% → 27% of paid ads; depth revenue 28% → 42% | Matching e-mail (queued) |
| 3 | **Demand-based prices with a public price checker** (cheap in quiet categories, higher for crowded roles like remote software jobs) | SEEK variable pricing; BOSS "competitive jobs" | ANZ yield +14% with volumes −1% | Our own counts of open jobs per category and place (we have them) |
| 4 | **Prepaid crypto credit wallet**: 1 credit = US$1, bonus credits on larger top-ups, expire after 12 months; spend on feature, pin, bump, extend, unlock | BOSS 直豆; SEEK Ad Budgets and Talent Search credits | 7.2 m BOSS payers at ≈US$179 a year each | Server accounts (written, not deployed) |
| 5 | **Cheap self-serve add-ons at volume**: "bump to top" US$5 to 9, "extend 30 days", "urgent" badge | BOSS ¥30 to 118 posts, ¥50 VIP; SEEK Add-On Badge | BOSS ARPPU ≈ RMB 1,200 a year | Same as 4 |
| 6 | **Outcome guarantee and Concierge**: we write or fix the post for a fee; free re-run if a paid job gets fewer than N apply clicks in 14 days | SEEK Guaranteed Hire and Concierge | Refund if no hire in 4 weeks; Premium after drafting | Apply-click counting per job (we redirect, so we can count) |
| 7 | **Seeker AI as single passes next to Plus**: one AI mock interview, one tailored résumé, one offer check, about US$5 to 9 each | Naukri Live AI Interviewer ₹749 to 999; Naukri Pro | Paid users 1.2% → 2.6% of MAU; seeker billings +35% at 57 to 63% margin | AI allowance already designed in `server/` |
| 8 | **Hiring-data subscription and API tier**: "who is hiring what, where, at what pay", competitor hiring alerts, salary benchmarks | Naukri Talent Pulse / Salary Pulse; SEEK Role Insights | 600 to 700 paid customers at Naukri; SEEK sells it as a fixed monthly fee | Our hourly data; paid API keys |
| 9 | **Opt-in candidate pool, sold per unlock or per role shortlist** | Naukri Resdex Lite (₹4,000 for 100 views) and AI-Rex (₹3,500 per role); SEEK Access Profile (200 credits) | Database access is Naukri's main revenue (68% in FY24 per one secondary source, not verified) | Opt-in from the résumé builder; privacy page; queued "résumé database" |
| 10 | **Trust and reach features that cost little**: verified-employer badge, scam guide and report button, visa-sponsorship / right-to-work filters, a named monthly "Jobs Every Hour Hiring Index", and course affiliate links on skill pages | BOSS verification and AI risk alerts; SEEK Pass and Job Ad Index; Naukri JobSpeak; SEEK footer partners GO1/FutureLearn | Verified applicants 20% more likely shortlisted (SEEK claim) | Little; affiliate sign-ups |

Seeker-side warning: keep every job, every apply link and the basic tools free. BOSS cut its paid seeker services because they
hurt engagement; SEEK charges seekers nothing. Seeker money should stay a top-up (Naukri: about 7% of recruitment billings).

---

## 6. What US$1M a year could look like (my illustration, not a forecast)

| Stream | Assumption | Year |
|---|---|---|
| Employers: features, credits, budgets | 2,000 paying employers × US$300 a year (BOSS ≈US$179 per payer; one SEEK ad ≈US$160 to 300) | US$600k |
| Seekers: Plus and single AI passes | 2% of 500,000 monthly users pay (Naukri 2.2 to 2.6%) × US$20 a year | US$200k |
| Hiring data and API | 100 subscribers × US$100 a month | US$120k |
| Affiliates (courses, other tools) | Commissions on skill and career pages | US$80k |
| **Total** | | **≈US$1.0 m** |

At SEEK's free-to-paid rate (11% within six months), 2,000 paying employers need roughly 18,000 employers who post or claim a job
(computed). That is why idea 1 (claim-and-upgrade on jobs we already list) comes first.

---

## 7. Sources (all read or searched 2026-11-15)

BOSS Zhipin / Kanzhun
- https://www.zhipin.com/ — home page, opened (job search and /gongsi/ showed only a loading screen)
- https://apps.apple.com/cn/app/boss%E7%9B%B4%E8%81%98-%E6%8B%9B%E8%81%98%E6%B1%82%E8%81%8C%E6%89%BE%E5%B7%A5%E4%BD%9C%E7%A5%9E%E5%99%A8/id887314963 — App Store CN, features and in-app prices, opened
- https://www.staffingindustry.com/news/global-daily-news/kanzhun-q2-net-income-surges-173-as-users-top-70-million — Q2 2026 figures, opened
- https://business-news-today.com/boss-zhipin-revenue-rises-14-as-kanzhun-margins-expand-and-ai-recruitment-investment-accelerates/ — Q2 2026, seeker services simplified, opened
- https://www.thepaper.cn/newsDetail_forward_31442209 — Q2 2025, AI features, anti-fraud figures, opened
- https://www.ithome.com/0/675/676.htm — 2023 report on VIP ¥68, employer spend, opened
- https://www.woshipm.com/pd/5915256.html — VIP rights, 直豆 = ¥1 (2023-10-07), opened
- https://theoria137.substack.com/p/boss-zhipin — annual package prices, ARPPU view (third party), opened
- https://kanzhun.gcs-web.com/news-releases/news-release-details/kanzhun-limited-announces-fourth-quarter-and-full-year-2025 — FY2025 release (403; figures via search snippets and syndicated copies such as https://www-web.itiger.com/news/2620230181)
- https://www1.hkexnews.hk/listedco/listconews/sehk/2026/0825/2026082501403.pdf — Q2 2026 filing (search snippet)
- https://m.jiemian.com/article/13492516.html — "competitive jobs" must be paid (search snippet)
- https://thebambooworks.com/kanzhun-eyes-brazil-argentina-and-vietnam-as-growth-slows-at-home/ and https://www.sahmcapital.com/news/content/kanzhun-eyes-brazil-argentina-and-vietnam-for-growth-2026-08-28 — overseas plans (403 / search)
- https://apps.apple.com/app/id6477343752 — OfferToday (search snippet)
- https://www.fool.com/earnings/call-transcripts/2026/04/01/kanzhun-bz-q4-2025-earnings-call-transcript/ — Q4 2025 call (timed out; facts via search summary)

Naukri / Info Edge
- https://www.infoedge.in/pdfs/financial_pdfs/f_Earnings/investor-concall-transcript-28May2026.pdf — Q4 FY26 call, opened (text extracted)
- https://www.infoedge.in/pdfs/financial_pdfs/f_Earnings/investor-concall-transcript-14aug26.pdf — Q1 FY27 call (10 Aug 2026), opened (text extracted)
- https://apps.apple.com/in/app/naukri-job-search-careers/id482877505 — App Store India, features and in-app prices, opened
- https://www.hrcabin.com/naukri-fast-forward-services-cost/ — FastForward prices (third party), opened
- https://autoapplyjobs.in/blog/naukri-premium-vs-free-worth-it-or-use-automation — conflicting prices (2026-03-08), opened
- https://www.editorji.com/business-news/naukri-pro-ai-transform-your-resume-1763704476228 — Naukri Pro, opened
- https://internshala.com/blog/naukri-job-posting-price/ — employer prices (updated 2026-09-21), opened
- https://deepaksood619.github.io/education/competitors/job-platforms/naukri-analysis — employer price claims (third party), opened
- https://newsletter.cutshort.io/p/cost-of-recruitment-offerings-and — price-rise survey (2025-10-10), opened
- https://www.cxodigitalpulse.com/?p=64338 — AI products ≈₹240 crore run rate (2026-10-29), opened
- https://www.staffingindustry.com/news/global-daily-news/info-edge-billings-rise-128-in-q2 and https://www.cxodigitalpulse.com/?p=63185 — Q2 FY27 (search snippets)
- https://yespress.io/naukri-com — résumé database 68.4% / job listings 9% claim (search snippet, not verified)
- naukri.com, resume.naukri.com, naukri.com/naukri360, naukri.com/blog, naukri.com/llms.txt, ambitionbox.com — all 403

SEEK
- https://announcements.asx.com.au/asxpdf/20260812/pdf/072nnb0kxq7l1x.pdf — FY26 results announcement, opened (text extracted)
- https://announcements.asx.com.au/asxpdf/20260812/pdf/072nng7ng7kj4j.pdf — FY26 results presentation, opened (text extracted)
- https://au.employer.seek.com/support/productterms — product terms (last updated 2026-11-02), opened
- https://au.employer.seek.com/support/talentsearchofferterms — Candidate Matches and Premium Talent Search (2026-07-20), opened
- https://hk.employer.seek.com/products/article/ai-enhanced-job-ads — Lite/Basic/Advanced/Premium tiers, opened
- https://au.seek.com/career-advice — hub and full footer, opened
- https://au.seek.com/career-advice/explore-salaries — salary pages, opened
- https://abnnewswire.net/press/en/99413/ — 2019 variable pricing and contract change, opened
- https://100hires.com/job-boards-australia.html — Ad Budget prices (July 2026, third party), opened
- https://seekpass.co/about-us, https://www.seek.com.au/profile-privacy — SEEK Pass and profile visibility (search snippets)
- https://help.sourcr.com/en/articles/11324421-the-seek-recruiter-directory, https://talent.seek.com.au/products/find-a-recruiter — recruiter directory (search snippets)
- https://talent.seek.com.au/products/guaranteed-hire — Guaranteed Hire (search snippet)
- Jora Plus A$69 / Max A$99 — third-party listings via search (betterteam.com 403), not verified
- seek.com.au, seek.co.nz, au.seek.com home pages — 403
