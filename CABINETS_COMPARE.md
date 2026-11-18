# Account areas of other job sites against ours (read 18 Nov 2026)

Asked by the owner on 18 Nov 2026: «Проверить все личные кабинеты других сайтов вакансий, тот же hh.ru и другие сайты вакансий, все которые мы
знаем, американские и т. д.» Two helpers read the public help and product pages of 22 sites (no sign-ups, no logins). Pages opened in full:
hh.ru, Indeed, LinkedIn, Djinni. The rest was read from search summaries of the sites' own help pages and is marked (S) or [S] below: check
such a line on the site itself before building on it. A "?" in a matrix means "not found", not "absent".

## What ours has (checked in `assets/account.js` and `server/src/worker.js`, 18 Nov)

Employer: jobs with draft, pause, renew and close; preview before posting; views and apply clicks per job; company page (logo, text,
places); team; candidate search and contact requests; orders, receipts; settings. Job seeker: saved jobs with an "applied" mark, resumes,
job alerts with a frequency, the profile employers can find, export and deletion of the data. Sign-in: email, Google, LinkedIn.

## What others have and ours lacks (the work list; each is checked on the source site before it is built)

| # | Side | Feature | Who has it | Ours |
|---|---|---|---|---|
| 1 | Seeker | Hide the resume from named companies; link-only visibility | hh.ru | visibility on/off only |
| 2 | Seeker | Who viewed or opened my resume | Naukri, hh.ru | none |
| 3 | Seeker | Recommended jobs in the account, from the resume and saved jobs | ZipRecruiter, Dice, Reed, Naukri, Built In | none in the account (the site has "similar jobs") |
| 4 | Seeker | "Looking / not looking" status seen by employers only | LinkedIn, Wellfound, Djinni | none |
| 5 | Seeker | Tracker in four columns: saved, applied, interviews, archived, with a manual "move to applied" | Indeed | an "applied" mark, no board |
| 6 | Employer | Download of a job's numbers; comparison with similar jobs | hh.ru, Indeed, SEEK | numbers on the page only |
| 7 | Employer | Letter before a job ends ("3 days left, renew?") | Remote OK and others | none |
| 8 | Employer | "Post a similar job" in one click | most | none |
| 9 | Employer | Payment link to forward to the finance team | Remote OK | none |
| 10 | Both | Second step at sign-in | several | none |
| 11 | Both | The confirmation letter thanks every new account "for opening an employer account" | - | to fix |
| 12 | Owner | Moderation page: block an account, edit a job in place | - | links and the accounts table were added on 18 Nov |

Left out on purpose: collecting applications on our site. Every Apply button leads to the company's own page; that is the site's promise.

---

# Part 1. Employer side, as the helper wrote it

# Employer account areas of other job sites: factual survey

Read date for every source: 2026-11-18. Public pages only. No sign-up, no login.

## Method and honesty notes

- Tools: WebSearch and WebFetch only.
- "(F)" after a URL = I fetched the page and the facts come from its text. "(S)" = the fact comes from a WebSearch result that summarised that official page and I did NOT open the page. Treat (S) facts as a lead to double-check.
- Third-party pages (review blogs, ATS vendor help) were ignored. Where only a third-party page mentioned something, it is written as "not found on official pages".
- Several official pages are old (the tool reported ages from about 90 to 3000+ days). Menu names and prices may have changed.
- Prices differ between pages on several sites. Those conflicts are noted.
- Blocked or not opened: ziprecruiter.com/employer (403), glassdoor help article (403), WWR support article (403), SEEK help article (redirected, not followed again). Not covered at all: Otta (merged into WTTJ, only WTTJ searched), StepStone (only Totaljobs searched). Rabota.ru, Habr Career, SuperJob, Work.ua, Djinni covered only through search summaries (S), except Djinni job-posting guide (F).
- Sites with the thinnest coverage: ZipRecruiter, Glassdoor, Monster, Naukri, Built In, SuperJob, Habr Career, Rabota.ru, Work.ua, Reed, Totaljobs, SEEK (all search summaries only).

---

## 1. hh.ru (HeadHunter) — read 2026-11-18

Sources: https://hh.ru/employer (F), https://feedback.hh.ru/knowledge-base/article/3705 (F), https://feedback.hh.ru/knowledge-base/article/1288 (F), https://feedback.hh.ru/knowledge-base/article/0933 (F), https://feedback.hh.ru/knowledge-base/article/0044689 (F), https://feedback.hh.ru/knowledge-base/article/1599 (S), https://feedback.hh.ru/knowledge-base/article/5721 (S)

- **Posting a job:** Create from the "Вакансии" section ("Вакансия+" / "Создать вакансию"); start from a template, a saved draft or from scratch (https://hh.ru/employer). Tabs in the vacancy list: Active, Pending (waiting for payment, activation or scheduled publication), Drafts (kept indefinitely), Archive, Templates (own or colleagues') (https://feedback.hh.ru/knowledge-base/article/3705). Duplicate is in the three-dot menu; archived vacancy is republished via "Отредактировать и разместить", counted as a new paid publication (same article). Required fields, bulk upload, XML feed, preview: not found on official pages I read.
- **Moderation and status:** Public for 30 days, then auto-archived; email alerts 5 days before expiry and on archive day. Prolong: schedule or cancel auto-prolongation (+30 days); regular auto-raise can be set. "Скрыть из поиска" hides the vacancy from everyone. Manual archive counts the paid service as used. Sort by the "Истекает" column. Before archiving the system suggests writing to candidates with unviewed responses; unviewed responses of the last 30 days lower the company's "индекс вежливости" (politeness index) (https://feedback.hh.ru/knowledge-base/article/3705 (F); https://feedback.hh.ru/knowledge-base/article/1599 (S)). Moderation rules: not found on pages I read.
- **Applicants:** Own response system. Opened from the "Отклики" column (blue = total, green = unviewed). Funnel: All unreviewed, Consider, Initial contact, Test assignment, Interview, Job offer, Start date; rejection with substatuses; custom substatuses. Bulk actions on several resumes; "one-click transfer" moves response to a status and sends a message automatically. Message templates sent on status change (message mandatory for rejection). SMS notification with fixed text linking to chat. Three-dot menu: interview reminder with date/time, mark no-show, "missed your call" notice, report a response to moderators. Auto-sorting (авторазбор) by criteria, talent-database chatbot, list of candidates who viewed the vacancy (https://feedback.hh.ru/knowledge-base/article/1288 (F)). Export, notes, ratings, tags, interview calendar: not described in that article. Share a vacancy with a hiring manager (https://feedback.hh.ru/knowledge-base/article/3705).
- **Candidate search:** Paid access to the resume database; filters by education, experience, salary expectation; contacts stay open until the access period ends. Omsk-region employers can pay per contact view (https://hh.ru/employer (F)). Saved searches, limits: not found on official pages I read.
- **Statistics:** Per vacancy: views, responses, candidates in progress, matching resumes shown as list columns (https://feedback.hh.ru/knowledge-base/article/3705 (F)). Chart of views and responses per day, also for archived vacancies, via "Мои вакансии" -> "Статистика" or "Здоровье вакансии" (https://feedback.hh.ru/knowledge-base/article/5721 (S)). Paid "hh PRO" vacancy statistics: anonymised data on applicants (30-day activity, salary range, age/gender ranges, experience buckets, top-5 regions, education, languages, up to 20 skills) (https://feedback.hh.ru/knowledge-base/article/0933 (F)). Company reports: extended report, per-recruiter evaluation (admins or users with company-statistics access), "Индекс вежливости компании" and "Стоимость подбора" in "Аналитика подбора" (https://feedback.hh.ru/knowledge-base/article/5721 (S) and https://hh.ru/article/26702 (S, snippet only)). Export: not found.
- **Company page / employer brand:** "О компании" description plus vacancies; "Проверенный работодатель" badge, status shown under "Управление и автоматизация"; "Бренд работодателя" section manages employee ratings and reviews (Dream Job) shown on vacancies and company page (https://feedback.hh.ru/knowledge-base/article/0044689 (F)).
- **Team:** "Менеджеры" subsection under "Управление и автоматизация"; "Квоты" cap how many vacancies each manager can publish; admins see other managers' tabs; vacancy can be transferred to another manager (https://feedback.hh.ru/knowledge-base/article/0044689, .../3705 (F)). Managers see only own vacancies unless granted more (https://feedback.hh.ru/knowledge-base/article/5721 (S)). Activity log: not found.
- **Billing:** Pay per publication from balance; plans Стандарт, Стандарт плюс, Оптимум, Премиум (https://hh.ru/employer (F)). Buying more responses via a promotion page; "raise" uses a publication or buys promotion (https://feedback.hh.ru/knowledge-base/article/3705). Documents section exists under management menu (S). Invoices/refunds/payment methods: not found.
- **Notifications:** Email at 5 days before expiry (https://hh.ru/employer). Email on new responses and messages configurable per vacancy (https://feedback.hh.ru/knowledge-base/article/1288). Personal settings control notifications (https://feedback.hh.ru/knowledge-base/article/0044689).
- **Trust and safety:** Verified-employer badge (above). New-account limits: not found.
- **Onboarding:** not found on official pages.
- **Unusual worth copying:** (1) politeness index penalising unanswered responses; (2) prompt to message unviewed applicants before archive; (3) one-click status+message transfer; (4) vacancy "health" page; (5) per-manager publication quotas.

## 2. Indeed — read 2026-11-18

Sources: https://www.indeed.com/hire/resources/howtohub/how-to-close-or-pause-jobs-on-indeed (F), https://www.indeed.com/hire/resources/howtohub/how-to-manage-candidates-on-indeed (F), https://www.indeed.com/help/employers/articles/users-and-permissions-overview?hl=en&co=US (F), https://www.indeed.com/hire/resources/howtohub/employer-dashboard-frequently-asked-questions (S, title only)

- **Posting a job:** not found on official pages I read (only third-party guides).
- **Moderation and status:** Three job statuses: Open, Paused (hidden, spend stops, applicants still accessible), Closed (removed from search, archived, applicants still viewable and messageable). Change via Jobs dashboard Status dropdown or three-dot menu; only Admin or Jobs permission can pause/close; reopen via "Open"; jobs flagged by Indeed cannot be reopened until they meet posting standards. Expiry and reposting not covered; Indeed does not auto-remove filled jobs (https://www.indeed.com/hire/resources/howtohub/how-to-close-or-pause-jobs-on-indeed).
- **Applicants:** Statuses New, Reviewing, Contacting, Interviewing, Hired, Rejected; viewing moves New to Reviewing. Filters: location, screener-question status, yes/maybe/no indicator, application date, across open/paused/closed jobs; applicants failing required screener criteria are marked Rejected. Templated emails (virtual interview, status update, rejection); rejected applicants are not notified unless a template is sent. Private notes. Forward Resume to colleagues. Bulk: select all and export candidates (only bulk action described). No built-in scheduler described; Indeed Interview guest links give screen share/chat/blur (https://www.indeed.com/hire/resources/howtohub/how-to-manage-candidates-on-indeed (F)).
- **Candidate search:** "Smart Sourcing subscription" exists with contact sharing (role list below); details not found on pages I read.
- **Statistics:** Analytics permission "overview and all reports" exists (https://www.indeed.com/help/employers/articles/users-and-permissions-overview). Per-job numbers: not found.
- **Company page:** Company page and reply to reviews are separate permissions (same URL).
- **Team:** Presets Basic, Limited, Standard, Advanced, Admin; custom permission sets: User Management (grant only equal or lower access), Candidates (all jobs or limited to certain jobs), Jobs (post/manage, or also sponsor), Company page, Hiring Events, Smart Sourcing, Billing (payments and billing details), Analytics (https://www.indeed.com/help/employers/articles/users-and-permissions-overview (F)). Activity log: not found.
- **Billing:** Sponsored Jobs have a budget; admins manage budgets and billing; billing permission can be separate so an accountant sees invoices (same URL (F) and S summary). Rest: not found.
- **Notifications, trust and safety, onboarding:** not found on official pages I read.
- **Unusual worth copying:** (1) pause vs close as two distinct states; (2) permissions combinable per area with "only grant up to your own level"; (3) candidate access limited to assigned jobs; (4) rejection email is opt-in via template.

## 3. LinkedIn — read 2026-11-18

Sources: https://www.linkedin.com/help/linkedin/answer/a517777 (F), https://www.linkedin.com/help/linkedin/answer/a520582 (F), https://www.linkedin.com/help/linkedin/answer/a518551 (S), https://www.linkedin.com/help/linkedin/answer/a522249 (S), https://www.linkedin.com/help/linkedin/answer/a520455 (S)

- **Posting a job:** Jobs icon -> Post a free job -> job title -> description (own, or drafted by AI with LinkedIn Hiring Pro) -> job settings -> promote or not. Fields: title, description, details, screening questions, rejection settings (auto-reject on must-have answers), email for applicant updates, #Hiring frame. Free job must be associated with the company's LinkedIn Page (https://www.linkedin.com/help/linkedin/answer/a517777 (F)). Repost a closed or expired job as a new post (https://www.linkedin.com/help/linkedin/answer/a522249 (S)). Drafts, templates, bulk/feed: not found.
- **Moderation and status:** Free post active up to 14 days, then paused; if not promoted, auto-closes after 30 days. Free posts have an application cap (typically 10 to 30); when reached the post is paused. One free job active at a time; limited number of free jobs per 30 days (number not given) (https://www.linkedin.com/help/linkedin/answer/a517777 (F)). Close via Manage job posts -> More -> Close job; posts auto-close after 6 months; closed cannot be reopened, only reposted; posts cannot be deleted; applicant list of a closed job visible only if applications were collected on LinkedIn (https://www.linkedin.com/help/linkedin/answer/a518551 (S)).
- **Applicants:** Applications can be collected on LinkedIn or sent to an external site/ATS. Job page has Job Information, Settings and View applicants; sort by relevance, location, years of experience, applicant fit rating; settings filter applicants outside the country or failing screening qualifications (https://www.linkedin.com/help/linkedin/answer/a520582 (F)). Rating applicants (S, https://www.linkedin.com/help/linkedin/answer/a520582 summary). Pipeline, notes, export: not found. Promoting unlocks paid Hiring Pro features such as unlimited application evaluations and InMails (https://www.linkedin.com/help/linkedin/answer/a517777).
- **Candidate search:** Recruiter Lite pages not read: not found on official pages.
- **Statistics:** Job Information tab shows view counts; Job Analytics only for jobs posted after July 2021 (https://www.linkedin.com/help/linkedin/answer/a520582 (F)).
- **Company page:** Free job tied to a LinkedIn Page (above). Rest not found.
- **Team, billing details, notifications, onboarding:** not found. Billing: promoted jobs are paid (a517777); model not detailed.
- **Trust and safety:** No verification step on the free-post page; limits for free posts above.
- **Unusual worth copying:** (1) auto-reject rules for must-have screening answers; (2) hard cap on applications for free posts that pauses the job; (3) "closed jobs cannot be deleted or reopened, only reposted" keeps history clean.

## 4. ZipRecruiter — read 2026-11-18

Sources: https://support.ziprecruiter.com/s/article/How-to-Rate-Your-Candidates (S), https://www.ziprecruiter.com/plans (S). https://www.ziprecruiter.com/employer returned 403 (blocked).

- **Posting a job:** Official source said to distribute to 100+ sites incl. Google for Jobs (S, https://www.ziprecruiter.com/post-a-job). Otherwise not found on official pages.
- **Moderation and status:** Matching and notifying candidates continue until you close the ad (S, https://www.ziprecruiter.com/plans). Other: not found.
- **Applicants:** Candidates page lists applicants; rate from a Rating column or profile; ratings visible only to account users and feed matching (S, https://support.ziprecruiter.com/s/article/How-to-Rate-Your-Candidates; article is ~3200 days old).
- **Candidate search / statistics / company page / team / billing details / notifications / trust / onboarding:** not found on official pages.
- **Support:** live chat via Help Center (S, https://www.ziprecruiter.com/enterprise_faq).
- **Unusual:** candidate ratings used to train matching.

## 5. Glassdoor — read 2026-11-18

Sources: https://www.glassdoor.com/blog/quick-start-guide-glassdoor-free-employer-profile/ (S), https://www.glassdoor.com/employers/resources/glassdoor-reviews-a-step-by-step-guide-for-employers/ (S), https://help.glassdoor.com/s/article/Choosing-a-featured-review?language=en_US (S), https://help.glassdoor.com/s/article/I-m-an-employer-What-can-I-do-about-negative-reviews-on-Glassdoor?language=en_US (S). Employer Center help page https://help.glassdoor.com/article/employer/Employer-Center-tabs-overview/en_US returned 403.

- **Posting a job:** job posting is free after claiming an account (S, https://www.glassdoor.com/employers/how-it-works/). Steps: not found.
- **Moderation, applicants, candidate search, statistics (Analytics tile exists), team, billing, notifications, trust:** not found on pages I could read. Employer Center has tiles Employer Profile, Community Reviews, Analytics, Employer Tools (S, quick-start guide).
- **Company page / employer brand:** Free profile pre-populated from the website; review website, HQ, logo, mission; company updates emailed to followers, can target country profiles; free account can post an official response up to 5,000 characters to company, interview and benefit reviews, from the Employer Center, the public profile or the Benefits tab; branded page can feature one review under 12 months old; reviews cannot be bought off, same moderation for clients (URLs above, S).
- **Onboarding:** after login a new account lands in the Employer Center (S, quick-start guide).
- **Unusual:** pre-populating the profile from the company website; public employer replies to reviews.

## 6. Wellfound — read 2026-11-18

Sources: https://wellfound.com/recruit/pricing (S), https://wellfound.com/recruit/all-features/post-a-job (S), https://help.wellfound.com/article/719-employers-how-much-does-it-cost (S), https://help.wellfound.com/article/1075-how-do-i-recruit-with-wellfound-for-free (S), https://help.wellfound.com/article/721-curated-cost (S)

- **Posting:** unlimited free job posts with built-in ATS and applicant management (pricing/overview pages). An older help article said a job must include compensation to post free; current pages do not mention it.
- **Billing:** promoting a listing is a paid add-on from about $200 per job; AI sourcing "Reach" $135/seat/month, $199 tier with more contact reveals and ATS integration; "Autopilot" managed recruiting $500/month per open role plus 10% hire fee; "Curated" (older article) $499/seat/month plus 20% success fee.
- **Other headings:** not found on official pages.
- **Unusual:** success-fee options alongside free posting.

## 7. Monster — read 2026-11-18

Sources (all S): https://hiring.monster.com/products/post-a-job/, https://hiring.monster.com/help-center/job-postings/managing-your-jobs-and-applicants/applicant-management-with-monster/, https://hiring.monster.com/employer-resources/monster-training/products/power-resume-search-aggregate/, https://hiring.monster.com/help-center/additional-resources/candidate-search/search-for-a-specific-candidate/

- **Posting:** form covers title, location, salary, benefits, responsibilities, qualifications; shared with partner boards.
- **Status/Applicants:** applicants in a folder per job; default "Awaiting Review", changes to "Reviewed" on any action; statuses Contacting, Interviewed, Hired, Rejected; share resumes with team/hiring managers; notes; rate candidates; message from Manage Candidates.
- **Candidate search:** Resume Search not on base tier, included in Pro; filters job titles, skills, veteran status, experience; Power Resume Search offers Semantic or Classic (Boolean); saved searches send email when new matches appear.
- **Billing:** Standard = pay when candidates view or apply; Pro $299/month or $2,990/year; 1 credit = $1; credits used on clicks and resume views. Pages disagree, check live.
- **Other headings:** not found on official pages.

## 8. Dice — read 2026-11-18

Sources (S): https://www.dice.com/hiring/pricing, https://www.dice.com/support/employer-help/posting-a-job/how-to-post-a-new-job-and-best-practices.html, https://www.dice.com/support/employer-experience/most-frequently-asked-questions.html, https://www.dice.com/hiring/find-candidates

- **Posting:** Jobs -> Post a Job; applications "Via Dice plus Email" (built-in ATS) or "Via URL" (external); screener questions (multiple choice, yes/no, free-form); title tip about 20 characters.
- **Status:** single job slot active 30 days.
- **Candidate search:** IntelliSearch (paste job description or resume), keyword/Boolean, left-side filters, tech-specific filters, time zone/remote sourcing, last-active sort.
- **Billing:** Single Job Slot $399 (30 days); Starter $649/month ($549 annual; 3 job slots/month, 1 user, 250 candidate views/month); Standard $899/month ($749 annual). Older page: $395 single ad. Prices subject to change, new customers only.
- **Other headings:** not found on official pages.

## 9. SEEK — read 2026-11-18

Sources (S): https://help.seek.com.au/employer/s/article/How-do-I-filter-or-manage-my-candidates (fetch redirected to https://help.au.employer.seek.com/s/article/... not followed), https://talent.seek.com.au/partners/whats-possible/seek-job-posting, https://help.seek.com.au/employer/s/article/What-are-the-benefits-of-using-SEEK

- **Posting/status:** each ad 30 days; value-based pricing; ad budgets with year-long discount; partner/integration job-posting page exists (ATS integrations).
- **Applicants:** free cloud candidate management with every ad: statuses (e.g. shortlist, not suitable), sort/filter, notes and documents, email one or more candidates; "Not Suitable" candidates get a notification 48 hours later.
- **Candidate search:** paid ads include invitations to matched candidates; Talent Search is a separate premium product.
- **Other headings:** not found on official pages.
- **Unusual:** delayed 48h rejection notice.

## 10. Reed.co.uk — read 2026-11-18

Sources (S): https://www.reed.co.uk/recruiter/help, https://plans.reed.co.uk/, https://www.reed.co.uk/recruiter/cv-search?directjob=recruiter, https://www.reed.co.uk/recruiter/post-a-job

- **Posting:** "Post a Job Advert" button from homepage or Jobs & applications; goes live after payment, or immediately if credits were pre-bought. Premium credit from GBP 89+VAT for new customers, live up to 6 weeks; Boost Bronze GBP 225+VAT, Silver GBP 599+VAT. Most edits free, but changing title, location, end date or advert type after the first application costs a credit (one credit for several changes together).
- **Candidate search:** CV Search by period (1 week GBP 99+VAT new customer, 1 day GBP 175+VAT, 1 month GBP 625+VAT); up to 100 CVs/day; profile preview without a credit.
- **Billing:** single adverts, advert credits, subscriptions Starter GBP 125+VAT/month, Growth 315, Scale 450 (job slots plus monthly CV credits; Starter 5 CV credits/month, spent only on download). CV database size quoted as 10.1M, 14.1M and 16.7M on different pages.
- **Other headings:** not found on official pages.

## 11. Totaljobs (StepStone not read) — read 2026-11-18

Sources (S): https://www.totaljobs.com/recruiter-advice/recruiter-resources/user-guide-using-the-totaljobs-candidate-management-system/, https://www.totaljobs.com/recruiter-advice/hiring-people/user-guide-using-the-totaljobs-cv-database/, https://www.totaljobs.com/recruiters/post-a-job-ad/, https://www.totaljobs.com/recruiter-products/cv-database-product/

- **Posting:** standard (7-day), featured and premium (6-week) ads; first-job promotion GBP 69.
- **Applicants:** Candidate Management System via Job ads -> view applicants; mark rejected, shortlisted, invited to interview, hired; moving between folders does not notify the candidate; bulk actions on desktop (guide about 460 days old).
- **Candidate search:** CV Database keyword/Boolean; filters recent activity, work eligibility, minimum education; free searches and previews; unlocking a full CV uses a credit.
- **Other headings:** not found on official pages.

## 12. Naukri — read 2026-11-18

Sources (S): https://www.naukri.com/recruit/resume-database-access-resdex, https://recruiterzone.naukri.com/introducing-resdex-enterprise/, https://recruiterfaq.naukri.com/category/resdex-database/

- **Posting:** FAQ says descriptive fields have a 254-character limit and matching CVs are sent to two email IDs.
- **Candidate search:** Resdex resume database (size claims 50M, 69M, 80M+ on different pages), filters, keyword search, AI recommendations; resume search only from sub-user accounts; super-user does admin tasks and sees MIS usage. PremiumX (curated pool, verified profile details); Resdex Enterprise (AI highlights, "Hidden Gems" tags, usage reports, SSO).
- **Team:** super-user and sub-user model.
- **Notifications:** recruiter mobile app gives real-time applications and Resdex search (not Resdex for super-users).
- **Other headings:** not found on official pages.

## 13. Welcome to the Jungle (Otta not read separately) — read 2026-11-18

Sources (S): https://solutions.welcometothejungle.com/en/pricing, https://help.welcometothejungle.com/en/how-to-create-and-set-up-a-job-offer-in-welcome-to-the-jungle-solutions-ats-%EF%B8%8F, https://support.welcometothejungle.com/en/articles/7178536-can-you-connect-with-my-ats, https://help.welcometothejungle.com/en/how-does-your-careers-page-work-on-welcome-ats

- **Posting:** if an ATS is connected, roles import automatically (Greenhouse, Lever, Workable, Ashby plus others); otherwise create under Jobs tab; goes through quality review, no more than one working day; save as draft and share with other recruiters; choose where it appears (profile, career site, partner boards); AI drafts descriptions and screening criteria in Welcome ATS; publishing to LinkedIn help page exists.
- **Company page:** profile (introduction, location, key figures, links); separate careers page showing only "Published" jobs.
- **Billing:** subscription bundle (Welcome Hiring Suite), job packages by number of roles plus top-ups, quote-based, no public prices.
- **Other headings:** not found on official pages.

## 14. Built In — read 2026-11-18

Sources (S): https://builtin.com/job-slots, https://employers.builtin.com/packages/, https://employers.builtin.com/free-jobs-faq/

- **Posting/billing:** free job posting in minutes with basic company profile and free ATS integration that cross-posts; annual packages Basic, Core, Enterprise; Enterprise: enhanced profile, analytics dashboard, candidate viewer, unlimited postings, "Brand Boost" placement. No public prices. "Free Jobs" scraped from the internet get limited distribution; employers can claim them (FAQ about 1,400 days old).
- **Other headings:** not found on official pages.

## 15. We Work Remotely and Remote OK — read 2026-11-18

WWR (S): https://support.weworkremotely.com/how-much-does-it-cost-to-post-at-we-work-remotely, https://support.weworkremotely.com/how-to-post-a-job-at-we-work-remotely, https://support.weworkremotely.com/how-long-does-my-job-listing-stay-live-for (fetch 403), https://support.weworkremotely.com/how-can-i-get-a-job-bundle, https://weworkremotely.com/post-a-remote-job
Remote OK (S): https://remoteok.com/hire-remotely, https://remoteok.com/buy-bundle

- **WWR posting/billing:** $299 per 30-day listing (some pages say "per month"); auto-renews, can be turned off in dashboard, reminder email 5 days before renewal; optional Better/Best (Best has a 7-day pin); Boost one-time $199; filtering service $199, auto-renews; GeoLock $99 per listing, locks once live; Mega Placement by custom quote; bundles of 36, 72, 120, 180+; no subscription or Pro account needed; guest posting exists.
- **Remote OK posting/billing:** from about $299 for 30 days (hire page also shows $447), dynamic pricing; non-refundable; auto-renews, reminder 7 days before; renewal at same price (bundle price if bundled); sticky posts max 2 per company; add-ons: logo, email blast to remote candidates, highlight, pin 1 week/1 month, QR short link, geolock; bundle 25 posts valid 24 months; pay now or send payment link to finance for approval; listing live after payment clears; company-domain match gets a "Verified" tag.
- **What the poster gets after paying (applicants, stats):** not found on official pages.

## 16. SuperJob, Habr Career, Rabota.ru, Djinni, Work.ua — read 2026-11-18

**SuperJob** (S): https://russia.superjob.ru/registration.html, https://www.superjob.ru/pro/6629/, http://public.superjob.ru/pdf/reestr/technical_description.pdf, https://api.superjob.ru/client/
- Free posting; CIS employers get up to 100 free vacancies a year (press release, about 2025). Registration page says resume base access is "pay only for result" (marketing wording). Contacts in resume base visible only with active tariff; otherwise a "Показать контакты" button leads to tariffs. Cabinet sections: Тарифы, Мои вакансии, Рекламный кабинет, Работа с базой резюме, Отклики; up to 500 users per cabinet. Tariff types via API: unlimited, basic, demo, turbo-vacancy and others. Paid employer API.

**Habr Career** (S): https://habr.com/ru/companies/habr_career/news/922634/, https://career.habr.com/info/help_hr, https://habr.com/ru/companies/habr_career/articles/981488/
- For small and medium companies posting is free and the employer pays 300 RUB per opened response (post is older, recheck); a curator is notified, response data and contacts hidden until paid; not available to companies of 1000+ staff or with active subscription. Help page has sections on cost, formats, tariffs, resume base. AI scoring of responses only for pay-per-response vacancies.

**Rabota.ru** (S): https://www.rabota.ru/hr/, https://pro.rabota.ru/otkliki, https://pro.rabota.ru/how-to-choose-tarif, https://www.rabota.ru/info/
- Two price models on different pages (single vacancy tiers Standard/Optimal/Premium for 30 days from 1,475 RUB; subscription from 770 RUB; resume base from 4,000 RUB/month): conflicting, recheck. Responses: "Мои вакансии" shows per-vacancy counts of responses, calls, auto-matched resumes; "Отклики" table shows applied, auto-matched, invited; responses older than a month auto-archived; call tracking in every tariff. Rules: vacancies and resumes are post-moderated; resume contacts only for companies that passed moderation.

**Djinni** (job-posting guide F: https://guide.djinni.co/job-posting; others S: https://guide.djinni.co/pricing, https://guide.djinni.co/first-steps)
- Unlimited free postings. Fields: title, brief description, full description (no external links), optional YouTube video, primary role/keywords, remote/office, up to 5 countries, relocation, target candidate region, private salary range (required, used for matching) and optional public range, experience, English level, company type. Vacancy is emailed to matching candidates and published. Applications arrive in Inbox and by email; employers can filter the Candidates page and send the job. Success fee: 20% of monthly salary expectation (Ukraine) or 50% (others), 30-day warranty, no fee for juniors under 700 USD/month (pages inconsistent). Statuses, moderation, stats: not found.

**Work.ua** (S): https://www.work.ua/en/services/, https://www.work.ua/en/employer/register/, https://www.work.ua/en/help/98/
- Registration free; 1 free vacancy and 10 candidate contacts per month after registration. Publications unused are kept indefinitely. Plans: Стандарт 1,090 UAH/month, СтандартПлюс 3,290 UAH/month (weekly raise), Гаряча вакансія 8,990 UAH/week, Анонімна публікація 6,590 UAH/month (company name hidden), Корпоративний дизайн 59,900 UAH/month. Resume base sold separately or in packages (Лайт, Смарт, Преміум).

---

# A) Feature matrix

Columns: hh = hh.ru, In = Indeed, LI = LinkedIn, ZR = ZipRecruiter, GD = Glassdoor, WF = Wellfound, Mo = Monster, Di = Dice, SK = SEEK, Re = Reed, TJ = Totaljobs, Nk = Naukri, WJ = Welcome to the Jungle, BI = Built In, WW = WWR, RO = Remote OK, SJ = SuperJob, HC = Habr Career, Rb = Rabota.ru, Dj = Djinni, WU = Work.ua.
"yes" = stated on a page listed above. "paid" = stated and paid/extra. "no" = page says it is absent or not offered. "?" = not found on official pages I read (not the same as "no").

| Feature | hh | In | LI | ZR | GD | WF | Mo | Di | SK | Re | TJ | Nk | WJ | BI | WW | RO | SJ | HC | Rb | Dj | WU |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Free posting available | no | ? | yes | ? | yes | yes | ? | ? | ? | no | no | ? | no | yes | no | no | yes | yes | ? | yes | yes (1) |
| Drafts saved | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? |
| Vacancy templates | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Duplicate / repost | yes | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| ATS / feed integration | ? | ? | ? | ? | ? | yes | ? | ? | yes | ? | ? | ? | yes | yes | ? | ? | paid (API) | ? | ? | ? | ? |
| Pre-publication review | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes | ? | ? | ? | ? | ? | no (post-mod) | ? | ? |
| Pause / hide job | yes | yes | yes (auto at 14d / cap) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Fixed posting life shown | yes 30d | ? | yes 14d free / 6mo | ? | ? | ? | ? | yes 30d | yes 30d | yes 6wk | yes 7d / 6wk | ? | ? | ? | yes 30d | yes 30d | ? | ? | yes 30d | ? | ? |
| Auto-renew | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes | yes | ? | ? | ? | ? | ? |
| Expiry reminder email | yes (5d) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes (5d) | yes (7d) | ? | ? | ? | ? | ? |
| Own applicant list | yes | yes | yes (or external) | yes | ? | yes | yes | yes (or URL) | yes | ? | yes | ? | yes | ? | ? | ? | yes | yes | yes | yes | ? |
| Stage pipeline / statuses | yes | yes | ? | ? | ? | ? | yes | ? | yes | ? | yes | ? | ? | ? | ? | ? | ? | ? | yes (invited) | ? | ? |
| Candidate notes | ? | yes | ? | ? | ? | ? | yes | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Candidate ratings | ? | yes (yes/maybe/no) | yes (fit rating) | yes | ? | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Bulk actions on applicants | yes | export only | ? | ? | ? | ? | ? | ? | yes (email several) | ? | yes (desktop) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Message templates | yes | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Applicant export | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Interview helpers | reminder only | guest link | ? | ? | ? | ? | ? | ? | ? | ? | yes (stage) | ? | ? | ? | ? | ? | ? | ? | yes (invited) | ? | ? |
| Screening questions | ? | yes | yes | ? | ? | ? | ? | yes | ? | ? | ? | ? | yes (AI criteria) | ? | ? | ? | ? | ? | ? | ? | ? |
| Resume / CV database | paid | ? | ? | ? | ? | paid (Reach) | paid | paid | paid | paid | paid | paid | ? | paid (Ent.) | no | no | paid | ? | paid | yes (free) | paid |
| Saved search alerts | ? | ? | ? | ? | ? | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Invite candidates to apply | ? | ? | ? | yes | ? | ? | ? | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes | ? |
| Per-job views / responses | yes | ? | yes (views) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | paid | ? | ? | ? | ? | yes | ? | ? |
| Market / applicant stats | paid (hh PRO) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Company page editing | yes | yes | yes | ? | yes | ? | ? | ? | ? | ? | ? | ? | yes | yes | ? | ? | ? | ? | ? | ? | ? |
| Company reviews + reply | yes | yes | ? | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Verified / badge | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes (domain) | ? | ? | yes (moderated cos. for contacts) | ? | ? |
| Multi-user + roles | yes | yes | ? | ? | ? | ? | ? | yes (plan seats) | ? | ? | ? | yes | ? | ? | ? | ? | yes (500) | ? | ? | ? | ? |
| Pay per result (view/apply/response/hire) | partly (Omsk) | ? | ? | ? | ? | yes (hire fee) | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes (claimed) | yes | ? | yes (hire fee) | ? |
| Credits | ? | ? | ? | ? | ? | ? | yes | ? | ? | yes | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Subscription plans | yes | ? | ? | ? | ? | yes | yes | yes | ? | yes | ? | yes | yes | yes | no | no | yes | ? | yes | no | yes |
| Post bundles / multi-post discount | ? | ? | ? | ? | ? | ? | ? | ? | yes (budgets) | ? | ? | ? | yes (packages) | ? | yes | yes | ? | ? | ? | ? | ? |
| Paid promotion / boost | yes | yes (sponsored) | yes | ? | ? | yes | ? | ? | ? | yes | yes | ? | ? | yes | yes | yes | yes (turbo) | ? | yes | ? | yes |
| Anonymous employer posting | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes (candidate side) | yes |
| Mobile recruiter app | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | yes | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Notes: Indeed "paid promotion" = Sponsored Jobs with budget. Djinni "anonymous" means candidates search anonymously, not the employer.

# B) Ten features that appear on most sites

Counts are only of "yes/paid" cells above, so they undercount features that exist but were not found on official pages. Ranked:

1. Own applicant list in the cabinet — 15 sites (hh, Indeed, LinkedIn, ZipRecruiter, Wellfound, Monster, Dice, SEEK, Totaljobs, WTTJ, SuperJob, Habr, Rabota, Djinni and more).
2. Paid promotion / boost of a posting — about 14 sites (hh raise, Indeed, LinkedIn, Wellfound, Reed, Totaljobs, Built In, WWR, Remote OK, SuperJob, Rabota, Work.ua, ...).
3. Paid resume/CV database access — about 12 sites (hh, Wellfound, Monster, Dice, SEEK, Reed, Totaljobs, Naukri, Built In, SuperJob, Rabota, Work.ua); Djinni gives it free.
4. Subscription plans — about 12 sites.
5. Fixed posting lifetime stated (14 days to 6 months, mostly 30 days) — about 10 sites (hh, LinkedIn, Dice, SEEK, Reed, Totaljobs, WWR, Remote OK, Rabota).
6. Applicant statuses/stages — about 6 sites (hh, Indeed, Monster, SEEK, Totaljobs, Rabota).
7. Company page editable by employer — about 7 sites (hh, Indeed, LinkedIn, Glassdoor, WTTJ, Built In).
8. Screening questions — 5 sites (Indeed, LinkedIn, Dice, WTTJ criteria, plus hh auto-sorting by criteria as a related feature).
9. Multi-user accounts with roles — 6 sites (hh, Indeed, Dice, Naukri, SuperJob, plus seat-based plans).
10. Free posting tier — 9 sites (LinkedIn, Glassdoor, Wellfound, Built In, SuperJob, Habr, Djinni, Work.ua (1 job)).

(Order by count is approximate; rows 6 to 10 are within one or two sites of each other.)

# C) Ten features only one or two sites have that look valuable

1. Politeness index that scores the employer on unanswered responses — hh.ru. https://feedback.hh.ru/knowledge-base/article/5721 (S)
2. Prompt to message unviewed applicants before a vacancy is archived — hh.ru. https://feedback.hh.ru/knowledge-base/article/1599 (S)
3. One-click status change that also sends the template message — hh.ru. https://feedback.hh.ru/knowledge-base/article/1288 (F)
4. Per-manager quotas on how many vacancies each manager can publish — hh.ru. https://feedback.hh.ru/knowledge-base/article/0044689 (F)
5. Combinable permission areas (Jobs, Candidates, Billing, Analytics, Company page), "grant only up to your own level", candidate access limited to assigned jobs — Indeed. https://www.indeed.com/help/employers/articles/users-and-permissions-overview?hl=en&co=US (F)
6. Pause as a separate state from Close (stops spend, keeps applicants) — Indeed. https://www.indeed.com/hire/resources/howtohub/how-to-close-or-pause-jobs-on-indeed (F)
7. Auto-reject rules on must-have screening answers, plus an application cap that pauses a free job — LinkedIn. https://www.linkedin.com/help/linkedin/answer/a517777 (F)
8. Pay-per-opened-response for small companies, with response data hidden until paid — Habr Career. https://habr.com/ru/companies/habr_career/news/922634/ (S)
9. Private salary range required for matching plus optional public range, vacancy emailed to matching candidates, success-fee only — Djinni. https://guide.djinni.co/job-posting (F)
10. Payment link sent to finance for approval instead of paying immediately; "Verified" tag for company-domain match; renewal reminder email — Remote OK. https://remoteok.com/hire-remotely (S)

Also noted: delayed 48-hour "Not Suitable" notification — SEEK https://help.seek.com.au/employer/s/article/How-do-I-filter-or-manage-my-candidates (S); anonymous employer publication as a paid option — Work.ua https://www.work.ua/en/services/ (S); edits after first application cost a credit — Reed https://www.reed.co.uk/recruiter/help (S).


---

# Part 2. Job seeker side, as the helper wrote it

# Job seeker account areas of other job sites (public pages only)

Read date for every source: 2026-11-18. No sign-up, no login.

**Method caveat.** Pages marked [F] were fetched directly. Pages marked [S] were only seen through a web-search result summary for that URL (the full page was not opened). Treat [S] facts as medium confidence. Many help articles are 1-5 years old; menu names may have changed. Anything not stated with a URL is "not found on official pages".

**Sites read:** hh.ru, Indeed, LinkedIn, ZipRecruiter, Glassdoor, Wellfound, Monster, Dice, SEEK, Reed, Totaljobs, Naukri, Welcome to the Jungle, Built In, FlexJobs, Djinni, SuperJob, Habr Career, Work.ua.
**Not read (no search attempted or nothing useful):** We Work Remotely, Remote OK, Rabota.ru, StepStone, Otta (merged into WTTJ; only WTTJ covered). SuperJob only had API docs and old forum threads, no seeker help.

---

## 1. hh.ru (HeadHunter)
- **Sign-up and profile:** not found on official pages (help index lists only resume creation, moderation, visibility, password recovery) [F] https://feedback.hh.ru/
- **Resume / CV:** Five visibility modes: all registered employers (default); only selected employers; hidden from selected employers (stop list by company name or ID); link only; nobody. Applying to a vacancy switches the resume to "selected employers" and adds that company automatically; a stop-listed company is removed from the list when you respond to it. Separate "anonymous resume" setting hides personal details, photo, contacts and work history, and lets you replace the current employer's name with a generic description ("IT company") [F] https://feedback.hh.ru/knowledge-base/article/1897 . Resume moderation with block reasons exists [F] https://feedback.hh.ru/knowledge-base/article/6537 . Builder: article "how to create a resume" exists, contents not read [F] https://feedback.hh.ru/knowledge-base/article/1628
- **Saved jobs and searches:** "Autosearch" tracks new vacancies for a saved query; subscriptions can be renamed, disabled, deleted; web: "Автопоиски" on home page; mobile app: Favorites > Subscriptions [S] https://feedback.hh.ru/knowledge-base/article/1617 and https://feedback.hh.ru/knowledge-base/article/0048 . Subscribe to a company's vacancies, notifications by email or messenger [S] https://feedback.hh.ru/knowledge-base/article/0274
- **Applications:** Applicant sees simplified statuses: "Отклик доставлен" (not opened), "Отклик просмотрено" (viewed or moved to a stage), "Отказ" with a message from the employer (except the "not responding" status); page "Отклики и приглашения" [S] https://feedback.hh.ru/knowledge-base/article/1288
- **Messages:** not found on official pages (invitations exist as a page name only).
- **Recommendations:** not found on official pages.
- **Privacy and safety:** password recovery article only [F] https://feedback.hh.ru/knowledge-base/article/3046 ; deletion/export/blocking not found.
- **Paid extras:** not found on official pages.
- **Notifications settings:** mobile: Settings > Notifications > Job search, push and email toggles [S] https://feedback.hh.ru/knowledge-base/article/0048
- **Mobile app specifics:** autosearch managed under Favorites > Subscriptions [S] same URL.
- **Onboarding:** not found.
- **Unusual:** auto-add of the company you reply to into the allowed list (visibility follows the application); stop list removes a company when you apply to it.

## 2. Indeed
- **Sign-up and profile:** Profile settings menu controls whether employers can find you; default and opt-in wording differ between pages; once you choose opt-in/opt-out you cannot return to "unspecified" [S] https://support.indeed.com/hc/en-us/articles/204524164-Make-my-resume-Public-Private and https://www.indeed.com/legal/privacyfaq
- **Resume / CV:** Resume edit menu > privacy > public or private; "delete resume" link there. Applying shares the resume with that employer regardless of privacy [S] same URLs.
- **Saved jobs and searches:** Bookmark Save icon; Saved tab; apply from Saved; jobs saved over 6 months are removed; no stated cap [F] https://www.indeed.com/help/job-seekers/articles/14087165677837-my-jobs-saving-a-job . Alerts managed in My Subscriptions: edit, pause, delete [S] search result set (https://support.indeed.com/hc/en-ca/articles/360051197532).
- **Applications:** My jobs has four tabs: Saved, Applied, Interviews, Archived; statuses = tabs, moved manually; applications on employer sites are not tracked automatically ("Move to Applied" in the three-dot menu); list shows 6 months at a time; older history via personal-data request. Interview tab supports Indeed Interview setup test [F] https://www.indeed.com/help/job-seekers/articles/205332490-what-is-my-jobs . No dedicated notes feature on that page.
- **Messages:** Indeed Interview mentioned only [F] same page; rest not found.
- **Recommendations:** one third-party FAQ says Recommended Jobs was discontinued (not official) - not stated.
- **Privacy and safety:** "Close my account" is permanent and separate from data deletion; Personal Data Request form to delete or get a copy (about a month); Glassdoor account linked must be deleted separately [S] https://www.indeed.com/help/job-seekers/articles/10652026126605-requesting-or-deleting-your-data ; employers cannot see search history, alerts or saved jobs [S].
- **Paid extras / Notifications / Mobile / Onboarding:** not found on official pages.
- **Unusual:** Kanban-like four-tab tracker usable for off-site applications; data export via personal-data request.

## 3. LinkedIn
- **Sign-up and profile:** photo, location, education and contact info recommended; #OpenToWork signal [F] https://www.linkedin.com/help/linkedin/answer/110912
- **Resume / CV:** upload a default resume and save up to four more for different job descriptions [F] same URL.
- **Saved jobs and searches:** save jobs; alerts based on searches, preferences, specific companies, remote [F] same URL. Alerts daily/weekly by email, app notification or both [S] https://www.linkedin.com/help/linkedin/answer/a416410/manage-your-job-post-email-notifications
- **Applications:** view applications for Easy Apply jobs only; company-site applications not listed [F] https://www.linkedin.com/help/linkedin/answer/110912
- **Messages:** InMail to job posters when available [F] same URL.
- **Recommendations:** describe the job you want in your own words; Premium extra insights on fit [F] same URL.
- **Privacy and safety:** Open to Work can be limited to LinkedIn Recruiter users; recruiters at your current company are excluded via the "currently working here" position, not guaranteed; delete turns it off, preferences are not saved when re-enabled [S] https://www.linkedin.com/help/linkedin/answer/a507508 . Close account: Settings > Account management > Close account, permanent; Premium can be cancelled to keep Basic [S] https://www.linkedin.com/help/linkedin/answer/a1379064 . Report posts, scam guidance [F] https://www.linkedin.com/help/linkedin/answer/110912
- **Paid extras:** Premium job insights (price not read) [F] same URL.
- **Onboarding:** a printable Job Search Checklist PDF [F] same URL.
- **Others:** not found.
- **Unusual:** "recruiters only" visibility of Open to Work.

## 4. ZipRecruiter
- **Resume / CV:** unless profile is private, employers and recruiters may see it; private means not added to the Resume Database; opting out removes it from the database [S] https://ziprecruiter.com/terms
- **Saved jobs and searches:** daily alert emails, also SMS alerts; unsubscribe in account or from email link [S] https://support.ziprecruiter.com/candidate/s/topic/0TO0f000000saw2GAA/managing-job-alerts-email-or-text . Alerts built from profile, searches, clicks and applications [S] https://support.ziprecruiter.com/candidate/s/article/Why-do-I-receive-Job-Alerts-from-other-States
- **Applications:** "view jobs you have applied for" article exists [S] https://support.ziprecruiter.com/candidate/s/article/How-to-View-Jobs-You-Have-Applied-For ; resume shared with employer on apply [S] terms.
- Other headings: not found on official pages. Unusual: SMS job alerts.

## 5. Glassdoor
- **Sign-up and profile:** profile edit on desktop/mobile [S] https://help.glassdoor.com/s/article/How-to-set-up-and-edit-your-Glassdoor-profile ; one login with Indeed [S] https://www.glassdoor.com/about/onelogin/
- **Resume / CV:** upload resume, used to autofill applications; visibility to employers only for synced profiles and only if you opt in [S] https://help.glassdoor.com/s/article/Resume-Upload-and-Management
- **Saved jobs and searches:** Save button; alerts: up to 10 created per day, need title/keyword, location and frequency daily or weekly [S] https://help.glassdoor.com/articles/en_US/Article/Job-Alerts-on-Glassdoor
- **Privacy and safety:** profile hidden unless you make it visible; anonymous reviews/salary posts kept separate from profile [S] https://help.glassdoor.com/s/article/Who-can-view-my-Glassdoor-profile
- Other headings: not found. Unusual: anonymous contribution identity kept separate from the job profile.

## 6. Wellfound
- **Profile / visibility:** status options "Ready to Interview", "Open to Offers", "Closed to Offers" (hides profile and applications from startups); change from the avatar dropdown or preferences [S] https://help.wellfound.com/article/1029-how-do-i-adjust-my-profile-status . Marking current job as "Currently Employed" hides the jobs profile from the current employer [S] https://help.wellfound.com/article/761-how-can-i-prevent-a-current-employer-from-seeing-that-i-am-looking-for-a-new-job . Job profile vs public profile distinction [S] https://help.wellfound.com/article/829-how-do-profiles-work-what-is-the-difference-between-a-job-profile-and-public-profile
- **Preferences:** salary, remote, role expectations set once; search private by default [S] https://wellfound.com/candidates/overview
- Other headings: not found. Unusual: employer-hiding by current-employment flag.

## 7. Monster
- **Resume / CV:** three visibility settings: visible, confidential (recruiters see resume without name/contact), hidden (not searchable, can still apply) [S] https://www.monster.com/career-advice/article/monster-resume-privacy-settings and https://www.monster.com/inside/security-center/resume-security
- **Saved jobs and searches:** job alerts by email [S] https://www.monster.com/ ; saved jobs help article not found.
- Others: not found. Unusual: "confidential" middle mode.

## 8. Dice
- **Profile:** visibility toggle on dashboard/profile; off = employers cannot find you but you can still search, apply and get alerts [S] https://www.dice.com/support/candidate/candidate-profile/profile---make-my-profile-unsearchable.html ; "complete profile up to 7x more likely to appear in recruiter searches" per Dice page [S] https://www.dice.com/support/candidate-help/managing-your-candidate-account/set-up-my-profile.html
- **Saved jobs and searches:** My Jobs > Saved tab (default); alerts: recommended (IntelliSearch, profile based) and keyword/filter alerts; daily or weekly email; pause toggle, rename, delete [S] https://www.dice.com/support/candidate-help/notifications--preferences/manage-my-job-alerts.html
- **Applications:** "view the jobs I've applied to" article exists [S] https://www.dice.com/support/candidate-help/finding-a-job/view-the-jobs-ive-applied-to.html
- **Privacy:** delete-account article exists [S] https://www.dice.com/support/candidate-help/managing-your-candidate-account/delete-my-account.html
- Others: not found.

## 9. SEEK
- **Profile / visibility:** public profile findable by employers; only employers see full profile, resume and contact details [S] https://www.seek.com.au/career-advice/article/getting-the-most-out-of-seek-profile ; SEEK Pass verification with consent; choose which details to include [S] https://talent.seek.com.au/privacy
- **Saved searches/alerts:** saved searches deliver daily email [S] https://www.seek.com.au/JobMail ; profile can trigger alerts [S].
- **Privacy and safety:** Job Seeker Security Hub, advice to limit public contact details [S] https://www.seek.com.au/safe-job-searching
- Others not found (help centre https://help.seek.com.au/s/ lists articles; contents not read).

## 10. Reed.co.uk
- **Resume / Profile:** Profile & CV visibility switch ON/OFF; hide or deactivate account [S] https://www.reed.co.uk/help/profile
- **Saved jobs and searches:** shortlist jobs, email yourself a list; synced across devices when signed in; up to ten saved searches with daily or weekly email alerts [S] https://www.reed.co.uk/help/searching
- **Applications / mobile:** recruiters see profile plus CV; app gives live updates when the hiring manager has seen the application; app syncs with profile [S] https://www.reed.co.uk/recruiter-advice/were-making-the-reed-co-uk-jobseeker-app-even-better/
- Others: not found.

## 11. Totaljobs (StepStone not read)
- **CV:** view, download, replace uploaded CV in profile [S] https://help.totaljobs.com/s/article/How-do-I-retrieve-my-CV-totaljobs
- **Visibility:** profile not searchable by default; can be made searchable in settings; choose whether recruiters see application history [S] https://www.totaljobs.com/about/terms-and-conditions/
- **Saved/alerts:** register to save vacancies and set alerts [S] https://help.totaljobs.com/s/article/Looking-for-a-job-totaljobs
- Others not found. Unusual: choice to hide application history from recruiters.

## 12. Naukri
- **Profile:** each field weighted for a completion %; advice to keep above 90%; photo said to raise recruiter contact 40%; resume headline; key skills; summary [S] https://www.naukri.com/faq/job-seeker-create-naukri-profile and https://www.naukri.com/blog/how-to-set-your-naukri-profile/
- **Profile Performance:** shows "Profile Viewed", "Resume Downloaded", "Contacted by Email", "Resume Viewed" by recruiters; views from search separate from application views [S] https://www.naukri.com/faq/job-seeker-getting-around-naukri
- **Onboarding:** blog "3 things to do after creating a profile" [S] https://www.naukri.com/blog/onboarding-3-things-to-do-after-creating-naukri-profile/
- Others not found. Unusual: recruiter-action counters (who downloaded the resume).

## 13. Welcome to the Jungle (Otta not separately read)
- **Dashboard:** application count, saved jobs and articles, saved searches, suggestions [S] https://help.welcometothejungle.com/en/understanding-your-candidate-space-%EF%B8%8F
- **Visibility:** recruiters see profile from CV library only for status "Actively job hunting" or "Open to opportunities"; "Not available" = no contact [S] https://help.welcometothejungle.com/en/how-to-receive-opportunities-from-recruiters
- **Alerts / saved:** "Create an alert" on search; alerts page toggles; daily frequency fixed; follow companies; saved jobs in Application tracker > Saved column [S] https://help.welcometothejungle.com/en/how-to-optimize-your-job-search-by-activating-alerts and https://help.welcometothejungle.com/en/how-to-effectively-track-your-applications-on-welcome-to-the-jungle
- **Recommendations:** "suggested jobs" can be activated [S] https://help.welcometothejungle.com/en/activate-suggested-jobs-on-your-candidate-space
- Note: a migration notice says saved jobs do not carry over [S] https://go.welcometothejungle.com/candidate-migration-live

## 14. Built In / FlexJobs (WWR, Remote OK not read)
- **Built In:** heart-save into Kanban "Saved" column, history filter 14/30/90 days/6 months [S] https://builtin.com/articles/built-in-job-tracker-kanban-list ; Job Match email alerts daily or weekly [S] https://builtin.com/articles/finding-job-built-in-match-mode ; creating an account lists you in a job-seeker database searchable by premium employers, opt-out and deletion by email [S] https://builtin.com/privacy-policy
- **FlexJobs (paid):** $2.95 14-day trial then $23.95 per 4 weeks; $9.95/month 3-month; $5.95/month annual; refund within 14 days; 170-200+ skills tests; daily alert emails; webinars, company directory, ExpertApply [S] https://www.flexjobs.com/pricing and https://www.flexjobs.com/faq . Prices as shown in search results; verify.

## 15. Others
- **Djinni:** profiles anonymous, employer sees contacts only after candidate confirms; active vs passive search; unanswered proposals deleted after 30 days; salary hint on jobs with private range; profile salary editable up to 10 times a day [S] https://guide.djinni.co/first-steps , https://guide.djinni.co/active-search , https://djinni.co/updates/2026-10-21-private-salary-range-hint-061a3/
- **Habr Career:** contact visibility choices (authorized users; friends and curators of companies; curators of vacancies you responded to; nobody); profile visibility levels from a 2020 Habr article, may be outdated [S] https://career.habr.com/info/help_user and https://habr.com/ru/companies/habr/articles/499740/ ; deletion page https://career.habr.com/success/user_remove
- **Work.ua:** visibility: publish / hide / keep with private data; hidden resume is visible to employers you respond to; one switch hides personal data across all resumes; anonymous response no longer possible; employer sees a mark when you only phoned instead of applying (old news, verify); employer gets the response in the "Responses" section plus email [S] https://www.work.ua/en/help/36/ , https://www.work.ua/en/help/47/ , https://www.work.ua/en/news/site/1963/ , https://www.work.ua/en/news/site/2502/
- **SuperJob:** visibility modes (all, hidden from selected companies, link, closed) and auto-switch to link after apply, per search summary of an interface/API description [S] http://public.superjob.ru/pdf/reestr/technical_description.pdf ; seeker help not found. Low confidence.
- **Rabota.ru:** not read.

---

## A) Feature matrix
y = yes (seen on official page), no = not seen, p = paid, ? = not found. "no" is never asserted; absence is "?".
Sites: hh, Ind, LI, Zip, Gla, Wel, Mon, Dic, SEEK, Reed, Tot, Nau, WTTJ, BuiltIn, Flex, Dji, Habr, WorkUa

| Feature | hh | Ind | LI | Zip | Gla | Wel | Mon | Dic | SEEK | Reed | Tot | Nau | WTTJ | BuiltIn | Flex | Dji | Habr | WorkUa |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Resume upload | ? | ? | y | ? | y | ? | y | ? | ? | ? | y | ? | ? | ? | ? | ? | ? | y |
| Several resumes | ? | ? | y(5) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y |
| Visibility on/off | y | y | y | y | y | y | y | y | y | y | y | ? | y | y(opt-out email) | ? | y | y | y |
| Hidden from named companies | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Link-only resume | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Anonymous / confidential mode | y | ? | ? | ? | y | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | y | y(contacts) | y |
| Hide from current employer by flag | ? | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y | ? | ? |
| Recruiters-only visibility | ? | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Availability status (open/closed) | ? | ? | y | ? | ? | y | ? | ? | ? | ? | ? | ? | y | ? | ? | y | ? | ? |
| Profile completeness meter/%| ? | ? | ? | ? | ? | ? | ? | y(claim) | ? | ? | ? | y | ? | ? | ? | ? | ? | ? |
| Resume views stats for seeker | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y | ? | ? | ? | ? | ? | ? |
| Saved jobs | ? | y | y | ? | y | ? | ? | y | ? | y | y | ? | y | y | ? | ? | ? | ? |
| Saved searches/alerts | y | y | y | y | y | ? | y | y | y | y | y | ? | y | y | y | ? | ? | ? |
| Alert frequency choice | ? | ? | y | ? | y | no(daily) | ? | y | no(daily) | y | ? | ? | no(daily) | y | ? | ? | ? | ? |
| Push alerts | y(app) | ? | y | ? | ? | ? | ? | ? | ? | ? | y | ? | ? | ? | ? | ? | ? | ? |
| SMS alerts | ? | ? | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Follow company | y | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | y | ? | ? | ? | ? | ? |
| Application history list | y | y | y(Easy Apply) | y | ? | ? | ? | y | ? | ? | ? | ? | y | y(tracker) | ? | ? | ? | ? |
| Status seen/rejected shown | y | ? | ? | ? | ? | ? | ? | ? | ? | y(seen) | ? | ? | ? | ? | ? | ? | ? | ? |
| Manual tracker incl. off-site apps | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y | ? | ? | ? | ? |
| Employer-page apply tracked | ? | no(manual) | no | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Hide application history from recruiters | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y | ? | ? | ? | ? | ? | ? | ? |
| Chat / InMail | ? | ? | y(InMail) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y(proposals) | y | y(notice center) |
| Recommended jobs | ? | ? | ? | y | ? | y | ? | y | ? | y(matches) | ? | y | y | y | y | ? | ? | ? |
| Skills tests | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | p | ? | ? | ? |
| Salary hint | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | y | ? | ? |
| Delete account help | ? | y | y | ? | ? | ? | ? | y | ? | y(deactivate) | ? | ? | ? | y(email) | ? | ? | y | ? |
| Data export | ? | y(request) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Scam/safety guidance | ? | ? | y | ? | ? | ? | ? | ? | y | ? | ? | ? | ? | ? | ? | ? | ? | ? |
| Paid seeker plan | ? | ? | p | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | p | ? | ? | ? |
| Mobile app | y | ? | ? | ? | ? | ? | ? | ? | ? | y | y | ? | ? | ? | ? | ? | ? | ? |
| Single login across sites | ? | ? | ? | ? | y(Indeed) | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |

Matrix is sparse because most help pages were only partly read; "?" means "not seen", not "absent".

## B) Ten features on most sites (by count of "y" in the matrix)
1. Saved searches / email job alerts (hh, Indeed, LinkedIn, Zip, Glassdoor, Monster, Dice, SEEK, Reed, Totaljobs, BuiltIn, WTTJ, FlexJobs) - e.g. https://support.indeed.com/hc/en-ca/articles/360051197532
2. Resume/profile visibility on/off (about 16 sites) - e.g. https://www.reed.co.uk/help/profile
3. Saved jobs (Indeed, LinkedIn, Glassdoor, Dice, Reed, WTTJ, BuiltIn, Totaljobs) - https://www.indeed.com/help/job-seekers/articles/14087165677837-my-jobs-saving-a-job
4. Application history list (hh, Indeed, LinkedIn, Zip, Dice, WTTJ, BuiltIn)
5. Recommended / suggested jobs from profile (Zip, WTTJ, Dice, Naukri, Reed, BuiltIn, FlexJobs)
6. Alert frequency choice daily/weekly (LinkedIn, Glassdoor, Dice, Reed, BuiltIn)
7. Anonymous/confidential or personal-data hiding (hh, Glassdoor, Monster, Djinni, Habr, Work.ua)
8. Resume upload used to autofill applications (LinkedIn, Glassdoor, Monster, Totaljobs, Work.ua)
9. Account close/deletion help (Indeed, LinkedIn, Dice, Reed, Habr, BuiltIn by email)
10. Availability/open-to-work status (LinkedIn, Wellfound, WTTJ, Djinni)

## C) Ten valuable features on only one or two sites
1. Hide resume from named companies + link-only mode + auto-add of companies you reply to - hh.ru https://feedback.hh.ru/knowledge-base/article/1897 (SuperJob similar, low confidence)
2. Recruiter-only Open to Work, current-employer excluded - LinkedIn https://www.linkedin.com/help/linkedin/answer/a507508
3. Four-tab tracker (Saved/Applied/Interviews/Archived) with manual "Move to Applied" for off-site applications - Indeed https://www.indeed.com/help/job-seekers/articles/205332490-what-is-my-jobs
4. Profile Performance: who viewed/downloaded resume/emailed - Naukri https://www.naukri.com/faq/job-seeker-getting-around-naukri
5. Hide job search from current employer by marking "Currently Employed" - Wellfound https://help.wellfound.com/article/761-how-can-i-prevent-a-current-employer-from-seeing-that-i-am-looking-for-a-new-job
6. Choose whether recruiters see your application history - Totaljobs https://www.totaljobs.com/about/terms-and-conditions/
7. Salary hint for jobs with a hidden range, matched to your profile salary - Djinni https://djinni.co/updates/2026-10-21-private-salary-range-hint-061a3/
8. Confidential middle visibility mode (resume without name and contact) - Monster https://www.monster.com/career-advice/article/monster-resume-privacy-settings
9. Contact-info audience selector (authorised users / friends and curators / vacancies you responded to / nobody) - Habr Career https://career.habr.com/info/help_user
10. Employer sees a mark if you only phoned instead of applying; one switch hides personal data in all resumes - Work.ua https://www.work.ua/en/news/site/2502/ and https://www.work.ua/en/news/site/1963/
