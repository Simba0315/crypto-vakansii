# Rezi research: how it grew, what it sells, what map.rezi.ai is, what we lack

Status: IN PROGRESS (written section by section, research started 2026-11-14).

Already known from the Semrush "top pages" file (analysed earlier, not re-read): the 100 top rezi.ai pages get about 30,600 search visits a month. Home and product pages 44%, resignation letter examples and templates 22%, resume templates and examples 13%, "resume synonyms" pages 8%, cover letter pages 6%, map.rezi.ai 1%.

Founder's own words (owner supplied): nearly 11,000 paying subscribers, $3.2m ARR, 5M users; started 11 years ago at 22 in Korea; first AI features with GPT-3 in 2021; now adding a mobile app and tools that connect candidates with companies. Growth: "use the existing traffic to other sites" and show the app as a recommended resource in popups and emails, with map.rezi.ai as the example.

## 1. Site map of rezi.ai

Source: https://www.rezi.ai/sitemap.xml (fetched 2026-11-14). It is one flat file, not a sitemap index. robots.txt (https://www.rezi.ai/robots.txt) allows everything except `/_status/` and points only to this one sitemap. Other sitemap names (`sitemap_index.xml`, `sitemap-0.xml`, `post-sitemap.xml`) return 404.

**Total: 503 addresses.** That is small. Rezi's search traffic comes from a few hundred well-ranked pages, not from tens of thousands of thin pages. map.rezi.ai is a separate subdomain and is not in this sitemap (see section 3).

| Section | Count | 3 example addresses |
|---|---|---|
| `/posts/` (blog articles) | 227 | /posts/0-to-1-million-users, /posts/how-to-put-freelance-work-on-a-resume, /posts/signs-you-are-getting-fired |
| ...of which "how to" articles | 54 | /posts/how-to-use-the-rezi-resume-builder, /posts/how-to-put-freelance-work-on-a-resume |
| ...of which cover letter articles | 20 | /posts/career-change-cover-letter, /posts/chatgpt-cover-letter, /posts/are-cover-letters-necessary |
| ...of which "Rezi vs X" pages | 12 | /posts/rezi-vs-teal, /posts/rezi-vs-zety, /posts/rezi-vs-chatgpt |
| ...of which other reviews / alternatives / "X vs Y" | about 14 | /posts/teal-review, /posts/kickresume-alternative, /posts/cv-vs-resume |
| ...of which "resume synonyms for X" | 8 | /posts/resume-synonyms-for-assisted, /posts/resume-synonyms-for-collaborate, /posts/resume-synonyms-for-developed |
| ...of which template round-ups | 12 | /posts/basic-resume-templates, /posts/blank-resume-templates, /posts/canva-resume-templates |
| ...of which "best X" lists | 6 | /posts/best-ai-resume-builders, /posts/best-job-boards-for-students, /posts/best-ai-cover-letter-builders |
| ...of which company news / founder posts | about 6 | /posts/0-to-1-million-users, /posts/year-in-review-2025, /posts/rezi-map |
| `/resume-examples/` (one page per job title) + hub | 82 + 1 | /resume-examples/business-analyst, /resume-examples/marketing-lead, /resume-examples/security-operations-center-soc-analyst |
| `/resignation-letter-template/` (one page per situation or job) + hub `/resignation-letter-templates` (3 pages) | 58 + 3 | /resignation-letter-template/10-days-notice-resignation-letter-template, /resignation-letter-template/commuting-distance-resignation-letter, /resignation-letter-template/pharmacist-resignation-letter-template |
| `/rezi-docs/` (help centre / product docs) | 56 + 1 | /rezi-docs/how-to-cancel-your-subscription, /rezi-docs/rezi-chrome-extension, /rezi-docs/ai-interview-practice-tone |
| `/resume-templates/` (category pages) + hub | 4 + 1 | /resume-templates/modern-resume-templates, /resume-templates/simple-resume-templates, /resume-templates/creative-resume-templates |
| `/cover-letter-examples` hub (paginated) | 3 | /cover-letter-examples, /cover-letter-examples/page/2, /cover-letter-examples/page/3 (no separate cover-letter detail section; the items are blog posts) |
| `/tools/` (free tools) + hub | 9 + 1 | /tools/resume-checker, /tools/cover-letter-generator, /tools/job-search |
| `/topics/` (blog categories, with pagination) | 15 | /topics/resume, /topics/cover-letter, /topics/resignation-letter |
| `/blog` (pagination) | 10 | /blog, /blog/page/2, /blog/page/10 |
| `/authors/` | 10 + 1 | /authors/jacob-jacquet, /authors/astley-cervania, /authors/lauren-bedford |
| `/api/` (B2B API landing pages) | 3 | /api/resume-parsing, /api/resume-reformatting, /api/candidate-sourcing |
| `/alternatives/` | 1 | /alternatives/kickresume-review |
| `/employers/` | 1 | /employers/enterprise |
| Top-level product and company pages | 22 | /ai-resume-builder, /ai-apply-app, /rezi-chrome-extension, /resume-mcp, /pricing, /creator-program, /user-reviews, /editorial-process, /ai-llm-info, /rezi-changelog, /free-resume-template, /contact-sales |
| Language versions (`/es/`, `/fr/` and so on) | 0 | none in the sitemap |
| `/vs/` section | 0 | comparisons live under `/posts/rezi-vs-...` instead |

Notes:
- 238 of 503 addresses show `lastmod` in November 2026, so the file is regenerated often (probably whole-site rebuild dates, not real edits).
- Trust pages exist on purpose: `/editorial-process`, `/authors/...`, `/user-reviews`, `/ai-llm-info` (a page written for AI assistants). This matches E-E-A-T and AI-search work.
- Compare with Semrush: resignation letters are 22% of search visits from only about 61 pages; the 8 "resume synonyms" posts bring 8%. Small, sharp page types pay off more than volume.

## 2. Products and tools

Sources: https://www.rezi.ai/tools (navigation and footer), https://www.rezi.ai/pricing, and each product page named below. All fetched 2026-11-14.

**Key finding: Rezi's "free tools" are landing pages, not working tools.** On /tools/resume-checker every main button ("Try for free", "Check my resume", "Customize") goes to `https://app.rezi.ai/signup`. The FAQ says a score "requires a free Rezi account". The score shown is a static picture. So each tool page is an SEO page plus a sign-up funnel. The only things a visitor gets with no account are the Google Docs template and four .docx template downloads.

### Plans (https://www.rezi.ai/pricing)

| Plan | Price | What it gives |
|---|---|---|
| Free | $0, no card | 1 resume, 1 AI interview, 3 PDF downloads, limited Rezi Score and keyword targeting, unlimited cover and resignation letters |
| Pro | $29 a month | Unlimited resumes, interviews, downloads, all templates, Rezi Score, keyword targeting, 1 free expert review a month |
| Lifetime | $149 once | Pro features, without the monthly expert review |
| Enterprise / white label | from $99 a month per 200 users, or custom | Own branding, domain login, SSO, webhooks, team roles, review management |
| Expert resume review | from $8 | Human review |

30-day money-back on Pro and Lifetime. No annual or student plan on the page.

### Rezi products and tools

| Name | Address | What it does (one line) | Free or paid | Account needed |
|---|---|---|---|---|
| AI Resume Builder | /ai-resume-builder → app.rezi.ai | Main product: build an ATS resume with AI writing and scoring | Free plan, Pro $29 | Yes |
| AI Resume Agent | /tools/ai-resume-agent | Chat assistant that writes and rewrites resume sections (v1 August 2025, per year-in-review-2025) | Free plan limited, Pro | Yes |
| Resume Checker (ATS) | /tools/resume-checker | Scores a resume against "23+" ATS checks, with fixes | Free limited | Yes (FAQ says so) |
| Resume Keyword Scanner | /tools/resume-keyword-scanner | Finds keywords from a job ad that the resume lacks | Limited on Free | Yes |
| Resume Bullet Point Writer | /tools/resume-bullet-point-generator | Writes stronger bullet points | Free limited | Yes |
| Resume Summary Generator | /tools/resume-summary-generator | Writes a summary for a role | Free limited | Yes |
| Cover Letter Generator | /tools/cover-letter-generator | Cover letter from resume + job ad | Unlimited on Free | Yes |
| Resignation Letter Generator | /tools/resignation-letter-generator | Resignation letter in a chosen tone | Unlimited on Free | Yes |
| Job Search | /tools/job-search | Job board inside the app: "over 3M jobs", "Updated hourly", "sourced directly from company websites" (Ashby, Greenhouse, Workday, Lever, Jobvite), tracker with saved / applied / interviewing / rejected | Not stated | Yes (buttons go to sign-up) |
| AI Interview | /tools/ai-interview-practice | Mock interview with role questions; scores tone, pace, filler words (see /rezi-docs/ai-interview-practice-*) | 1 free, unlimited on Pro | Yes |
| Rezi Mobile App ("AI Apply App") | /ai-apply-app | iOS and Android. Swipe through jobs, each with a 0-100 match score against your resume; tailor resume; track applications. Jobs "from company career pages" | Free with daily swipe limit, Pro for more | Yes |
| Chrome Extension | /rezi-chrome-extension | Autofills applications on Workday, Greenhouse, Lever and others; tracker; interview questions for the job you are viewing; LinkedIn profile import | Free ("free, forever") | Yes |
| Rezi Resume MCP | /resume-mcp | Connector so Claude, Gemini, Cursor, Codex, Grok, Lovable can edit and tailor your Rezi resume | Not stated | Yes |
| Rezi Map | https://map.rezi.ai | World map of "over 3 million jobs" with natural-language search (section 3) | Free | No |
| Resume templates | /resume-templates (+4 category pages) | Template gallery; "Customize" goes to sign-up; 4 templates downloadable as .docx | Free | No for .docx download |
| Free resume template | /free-resume-template | Google Docs copy link, no sign-up | Free | No |
| Resume / cover letter / resignation letter examples | /resume-examples, /cover-letter-examples, /resignation-letter-templates | Example library, SEO pages | Free to read | No |
| User guides | /rezi-docs | 56 help articles | Free | No |
| Enterprise / white label | /employers/enterprise | Universities, agencies, career sites, non-profits run Rezi under their own brand. Page claims "70%" revenue share to deployment owners and about $986,895 paid out. Named users: Merit America, Hofstra University, BMA Group; logos Kaplan, Goodwill, Resumatic | $99/month per 200 users, or custom | Yes |
| Candidate Sourcing API | /api/candidate-sourcing | Employers search about 4.7M resumes built on Rezi and message candidates through Rezi (no contact data shared unless the candidate replies). $0.50 per search, $5 per first message | Paid | Yes (API key) |
| Resume Parsing API | /api/resume-parsing | Parse resumes to data | Paid | Yes |
| Resume Reformatting API | /api/resume-reformatting | Reformat resumes into a template | Paid | Yes |
| Creator Program | /creator-program | Pays creators $10 per approved short video that reaches 1,000 views in 7 days, plus $1 per 1,000 views (cap $1,200 per video), up to 5 videos a day, cross-posted to TikTok, YouTube Shorts, Instagram Reels, Facebook Reels; $100 per referred creator | Rezi pays out | Application |
| Trust and AI pages | /user-reviews, /editorial-process, /authors, /ai-llm-info, /rezi-changelog | Reviews, editorial policy, author bios, a page written for AI assistants, changelog | Free | No |

Small extras named in year-in-review-2025: open-source "Resume Metadata Standard" (April 2025), "Flappy Resume" game, PharmaCV (pharma version with a partner, September 2025).

### White-label sites in the Rezi family (these are the "other sites")

| Site | What it is | Price | How it links back to Rezi |
|---|---|---|---|
| https://www.resumatic.ai/ | AI resume builder "powered by ChatGPT": ATS checker, templates, cover letters, job search with match scores, interview practice, Chrome extension, ChatGPT app, mobile app | Free to start; prices on a separate page (not shown) | Footer: "Powered by Rezi Enterprise" linking to rezi.ai; app runs on `resumatic.rezi.ai`; support email support@rezi.io; privacy and terms on rezi.ai; "metrics and ratings aggregated with Rezi". Also listed in Rezi's footer under "Browse our products". It is a Rezi Enterprise white-label deployment. |
| https://resumai.com/ | Free AI resume builder "powered by Rezi" | Free; Pro price not shown (30% off code shown) | Footer: "Powered by Rezi" linking to rezi.ai; app on app.resumai.com; listed in Rezi's footer |
| https://socialmediascheduler.ai/ | Social media scheduler for 8 networks (X, LinkedIn, Instagram, Threads, TikTok, YouTube, Facebook, Bluesky), with an AI-agent connector | Starter $23, Pro $39, Studio $79 a month billed yearly; 7-day trial | Not a resume product. Contact email hello@rezi.io; a "Customers" footer link to /customers/rezi; Rezi used as the showcase customer in mock-ups. It does not send users to rezi.ai. |

What this means: the same Rezi engine is sold under several brand names. Each brand ranks for its own searches and sends paid users into the same app. The enterprise page's "70%" commission tells partners they keep most of the money, which is why career sites and agencies push Rezi to their own traffic.

## 3. map.rezi.ai in detail

Sources: the live HTML of https://map.rezi.ai/, /about, /jobs, /jobs/new-york/software-engineer, /jobs/new-york/hiring-near-me, /jobs/company/glg, /jobs/job/43281996/software-engineer-at-glg, /candidates, plus https://map.rezi.ai/robots.txt, /sitemap-index.xml, /sitemap-0.xml and the site's public JavaScript files. Fetched 2026-11-14. The launch post is https://www.rezi.ai/posts/rezi-map (by Jacob Jacquet, published 21 April 2026).

### What it is in one paragraph

A free, no-login job search page where jobs are dots on a world map. You type a query in plain language ("Python or Java AND AWS", a city, a company) and zoom in. A side list shows the jobs in view. Clicking a job opens a full description. "View job posting" sends you to the employer's own page. Next to every job sits a Rezi box: "Tailor my resume" or "Get my score". That box is the whole business point: the map brings job seekers, the box sends them into the paid resume app.

### What the visitor sees

- Top bar: tabs **Jobs** and **Candidates**, light / dark / system theme switch, sign-in.
- Full-screen map (grey style) with job dots. Left or bottom panel: job list, then job detail.
- Search box with natural-language and boolean search (per the launch post). Site search is also exposed to Google through `https://map.rezi.ai/?job-query={search_term_string}` (WebSite SearchAction schema).
- **Filters** (from the page code): Industry (Design, Engineering, Finance, Legal, Marketing, Operations, Product, Recruiting, Sales, Science), Skills (searchable), Workplace type (Remote), sort (Best match / Newest first), "Clear all", "Apply". On the Candidates tab: "All" or "Open to work".
- **Job detail** (example /jobs/job/43281996/software-engineer-at-glg): title, company logo, place, age ("2 weeks ago"), then an AI-structured description in fixed blocks: About the Role, Responsibilities, Requirements, Skills (as tags), Location, Work Type, Experience Level, Salary/Compensations, Benefits. The code fetches this from `api.rezi.ai/v2/search-engine/job-boards/descriptions` (field names `frontend_payload`, `initialAiDescription`), so the descriptions are rewritten into one format by AI, not copied raw.
- **Saved searches**: "Save this search" works without an account ("Saved on this device only"). Signing in (Google, Apple or email; Firebase) syncs them across devices.
- Footer banner on every page: "Job Search. Now mobile. Swipe through new job matches anywhere with Rezi." with App Store and Google Play buttons. Links: About, Browse all cities, Rezi home.

### Where the jobs come from and how many

- /about: "built from official company career pages"; "Every listing comes directly from an employer's official career site"; "Listings updated: Hourly". It also says Rezi focuses on official sources "whenever possible".
- Numbers do not agree across pages: page titles and the launch post say **3M+ jobs**; the /about page says **4M+ jobs indexed** and **1M+ fresh jobs every month**; the rezi.ai Job Search page (https://www.rezi.ai/tools/job-search) says "over 3M jobs" and names ATS sources Ashby, Greenhouse, Workday, Lever, Jobvite; year-in-review-2025 says Job Search launched in Q1 2025 with "over 1.3M" roles. So the job pool grew from about 1.3M (2025) to 3-4M (late 2026).
- Company logos come from Crunchbase's image server (`images.crunchbase.com/...{company_image_id}`), so Rezi matches employers to Crunchbase records.
- Candidates tab: "Search across 1.4M+ candidates" (resumes built on Rezi, from people who chose to be visible). The employer button "Sync your open roles" goes to `app.rezi.ai/auth/signup?source=map`. This is the "connect candidates with companies" part of the founder's post.

### How it is built (useful for copying)

- Framework: Astro, hosted on Netlify behind Cloudflare. Pages are rendered on the server on first request and cached at the edge (`cache-control: public, s-maxage=86400, stale-while-revalidate=604800`).
- Map: MapLibre GL with **PMTiles** vector tiles (Protomaps basemap). All job dots are one pre-built tile file: `pmtiles://https://maps-cdn.rezi.ai/jobs/jobs_v2.pmtiles`; candidates: `.../candidates/candidates.pmtiles`; base map: `.../base/basemap.pmtiles`. This means the map itself needs no database server: the browser reads only the tiles it needs from one static file on a CDN.
- Search and job details use an API (`api.rezi.ai/v1/search-engine/maps/jobs/search` and `/v1/search-engine/maps/jobs/details`). For a static copy, the list can come from the tile data or from per-region JSON files.
- Analytics: Plausible, PostHog and Amplitude (proxied through `t.rezi.ai`). The code tags visits from AI crawlers (OAI-SearchBot, PerplexityBot, Google-Extended, Applebot-Extended) as their own group.
- A/B test on the Rezi box: three versions run at once (`control`, `tailor`, `score`, stored in `window.__REZI_MAPS_AB`), and clicks are logged as "Map job targeted".

### Address patterns and title patterns

| Page type | Address pattern | Title pattern (real example) | In sitemap? |
|---|---|---|---|
| Home (map) | `/` | "Job Search Map – Find 3M+ Jobs Near You \| Rezi" | yes |
| City hub | `/jobs` | "Job Search Map by City & Role \| Rezi" (links to 30 cities × 6 roles, with a short intro per country) | yes |
| City + role | `/jobs/{city}/{role}` e.g. `/jobs/new-york/software-engineer` | "40,000 Software Engineer Jobs in New York \| November 2026 \| Rezi" (job count + current month) | yes |
| City "near me" | `/jobs/{city}/hiring-near-me` | "Jobs Hiring Near You in New York \| October 2026 \| Rezi" (note: month was stale on this page) | yes |
| Company | `/jobs/company/{company-slug}` e.g. `/jobs/company/glg` | "91 Glg Jobs \| November 2026 \| Rezi" | no |
| Job | `/jobs/job/{numeric-id}/{title-slug}-at-{company-slug}` e.g. `/jobs/job/43281996/software-engineer-at-glg` | "Software Engineer at GLG \| NY, US \| Rezi" | no |
| About | `/about` | "About Rezi Map — How the Interactive World Job Map Works \| Rezi" | yes |
| Candidates map | `/candidates` | "Candidate Search Map – Browse 1.4M+ Profiles \| Rezi" | yes |

Slug rule from the code: lower-case, every run of non-letters/digits becomes one hyphen, trim hyphens. The job id is an "obfuscated id", not the employer's id. Old city-only address `/jobs/new-york` returns 404.

### Indexability

- **Sitemap**: https://map.rezi.ai/sitemap-index.xml → `sitemap-0.xml` with **184 addresses only**: home, /about, /candidates, /jobs, and **30 cities × 6 pages** (software-engineer, product-manager, data-scientist, designer, marketing-manager, hiring-near-me). The 30 cities: Amsterdam, Atlanta, Austin, Berlin, Boston, Chicago, Dallas, Denver, Dubai, London, Los Angeles, Miami, Minneapolis, Nashville, New York, Paris, Philadelphia, Phoenix, Portland, Raleigh, Salt Lake City, San Diego, San Francisco, Seattle, Seoul, Singapore, Sydney, Tokyo, Toronto, Washington DC.
- Job and company pages are **not in the sitemap** but are indexable: each has a self `canonical`, no `noindex` tag and no `X-Robots-Tag` header. Google finds them through links: each city + role page is rendered on the server with **100 job links and 100 company links** in plain HTML, plus "Browse by city" and "Related roles" links.
- Job pages carry `JobPosting` JSON-LD (title, hiringOrganization, jobLocation, datePosted, description, url). It lacks `validThrough`, `employmentType` and `baseSalary` even when the page shows a salary, so it is a weak Google Jobs candidate. All pages also carry Organization + WebSite (SearchAction) JSON-LD.
- Company pages render only the title and count on the server ("Jobs at Glg, 91 open roles"); the job list loads in the browser.
- **robots.txt blocks AhrefsBot, SemrushBot, DataForSeoBot, DotBot and Amazonbot** ("no search-referral value"). Everyone else is allowed. Important: this means **Semrush cannot crawl map.rezi.ai**, so the "1% of traffic" figure for the map from the Semrush file is probably an undercount (not verified either way).

### What "apply" does

- "View job posting" opens the employer's original job page (`job_url`) in a new tab. If there is no address, it opens a Google search for "{title} {company}". /about: "Your application goes to the employer's Applicant Tracking System ... not through Rezi."
- Rezi does not take the application. It only takes the visitor.

### How the map promotes Rezi

1. **The "target resume" box on every job** (A/B tested, three versions):
   - control: "Impress employers and recruiters. Choose from hundreds of resume examples." → "Target Resume Now"
   - tailor: "Tailor your resume to this {title} role. Rezi rewrites your resume against {company}'s job description. Free." → "Tailor my resume"
   - score: "Don't guess if your resume is good enough. See how it scores against the {title} posting at {company} — free, in seconds." → "Get my score" (with a picture of a score gauge at 58/100)
   Clicking any of them writes a cookie `target-job={job id}` on `.rezi.ai` (1 year) and opens `https://app.rezi.ai/dashboard` in a new tab. The app reads the cookie, so the user lands in the resume app with that job already loaded. This is the hand-off that turns map visitors into sign-ups.
2. **Mobile app banner** on every page ("Job Search. Now mobile"), with store links.
3. **Sign-in modal** ("Sign in to Rezi ... Keep your searches across every device") when saving searches; login link carries `source=map`.
4. **Employer side**: Candidates tab and "Sync your open roles" → Rezi sign-up `?source=map`.
5. /about has "Build Your Resume" next to "Explore Jobs", and says core resume tools are free and Pro adds more.
6. No pop-up was seen in the server HTML of the map. rezi.ai's own pages (home, a resume example, a blog post, a resignation template, /tools/job-search) do **not** link to map.rezi.ai; only /posts/rezi-map does ("Try the jobs map ... Explore Jobs"). So the map is a separate traffic source that feeds Rezi, not a page that Rezi feeds.

### What a developer needs to build our version (static site, no server)

- One static tile or JSON file of job points (we already have 41,000 jobs with places). At our size a GeoJSON per region, or one PMTiles file built with `tippecanoe`, is enough. MapLibre GL plus a free basemap (Protomaps or OpenFreeMap) runs fully in the browser.
- Server-rendered (pre-built) pages: `/map/`, `/map/{city}/{role}`, with the job count and month in the title, 100 job links in HTML, "Browse by city" and "Related roles" links, `JobPosting` schema with every required field, and a sitemap for the city-role pages.
- On each job: "View job posting" to the employer page, plus our own boxes: "Check your resume against this job" (our /tools/resume-match) and "Build a resume for this job" (our resume builder), passing the job id in the address or localStorage.
- Saved searches in localStorage (no account needed), and an A/B test of the box text with our existing analytics.

## 4. How Rezi grew: timeline

(pending)

## 5. What we lack

(pending)

## What to copy first

(pending)

## Not opened or not verified

(pending)
