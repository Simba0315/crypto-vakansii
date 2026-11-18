# Open lines of the roadmap, audited on 18 Nov 2026

Asked by the owner on 18 Nov 2026: «полностью все … задачи, которые ты забыл выполнить». A helper read every line of `ROADMAP.md` that still
carries a "queued", "partly done" or "waiting" mark (about 225 lines) and looked for evidence in `CHANGELOG.md` and in the code. Read this
as a list of leads: an entry marked "not verified" was not checked in the code, and each entry is checked again before work starts on it.
Section C lists the marks that are stale (the work was done later), so the roadmap can be cleaned.

# ROADMAP.md: promised and not finished (read-only audit, 18 Nov 2026)

Method: all lines with 📋 🟡 ⏳ 🔨 🔄 (about 225) read; each checked with grep in CHANGELOG.md, build.py, collect.py, assets/*.js, server/src/worker.js, serve.py and other modules. "Not verified" means no evidence either way was found by grep. Line numbers are ROADMAP.md lines. Some lines (the long 🟡 server paragraphs) were read only in part; the first 500 characters were used.

Big finding: the site moved to its own domain and server (ROADMAP section 107, line 2251: "Переезд на jobseveryhour.com завершён"), the account server runs on Hostinger (`server/prod.mjs`), mail goes through Beget support@, MCP connector, alerts, claims, free employer posting and /admin/ exist. So most "waits for the server" marks are stale. What really waits is payments, Google/Bing, social accounts, AI key, translations.

---------------------------------------------------------------------------

## A. Still open, can be done now (largest effect for visitors first)

1. More jobs from more sources (ongoing; the biggest lever for traffic). Lines 139, 313, 432, 989, 1224, 1372, 1686, 1922, 1942, 1993, 2137. Wording: «Больше источников вакансий», «20 000+ компаний каждый час», «оставшиеся 194 доски (83 796 вакансий) частями». Exists: ATS readers in collect.py (Workable, Recruitee, Teamtailor, Personio, Workday, SmartRecruiters; `ATS_LIMIT`), 60 big Workday boards released on 18 Nov (CHANGELOG), Telegram channels (`telegram_jobs.py`), `sources_more.json`. Missing: open job-board APIs (Himalayas, RemoteOK, Remotive, Jobicy, Arbeitnow: not in collect.py), Pinpoint, local sources by country, the 194 held Workday boards, hourly run still on GitHub with a 45-minute limit (989). Size: large, ongoing.
2. Search page: "only my country / my city" and a city choice. Lines 308, 1685, 1779, 164. Wording: «выбор своего города и "только моя страна" в поиске (как Indeed)». Exists: checkbox "Hide remote jobs closed to my country" (build.py:2326, assets/app.js:406). Missing: city choice, near-me inside search. Size: medium.
3. Resume database by consent (seeker tick in the builder, employers search it). Lines 42, 862, 885, 1850, 1867. Wording: «галочка и настройки в конструкторе резюме (`assets/resume.js`)». Exists: server `/api/talent/profile|search|requests|sent`, employer side in assets/account.js. Missing: no consent tick or settings in resume.js (grep finds none). Size: medium. (Feeds revenue, needs only site code.)
4. Resume builder, next steps. Lines 1247, 1249, 1780, 739. Wording: «карточки ключевых слов "добавить / пропустить", стартовое окно, несколько резюме, больше шаблонов». Exists: tabs, hints under every line, score, target job, template gallery (assets/resume.js:256), tone picker for the AI request. Missing (not verified): add/skip keyword cards, start window, several resumes. Size: medium.
5. Report a problem on the job page with automatic re-check of the source. Lines 169, 410, 1631. Exists: server `/api/report`; the job page only has a mailto/Telegram link (build.py:1631). Missing: form on the page calling the API, re-check. Size: medium.
6. Employer account gaps found on the walk-through. Lines 1454, 410, 1906. Wording: «смена пароля со старым паролем; новая компания не может загрузить логотип; название компании с личной почты не сохраняется; причины ожидания служебным текстом; My jobs вливаются в чужой аккаунт». Exists: reset password, claims, views/clicks, status labels in account.js. Missing (grep): change-password route, logo upload before first job, resend-confirmation button, report form. Size: medium.
7. Premium products shown on the site: top-three rotation, "Urgent" badge, cover image and logo on branded jobs. Lines 35, 1598, 1607. Wording: «сборка ещё не показывает Premium-ротацию, значок "срочно", обложку и логотип компании (поля уже в export.json)». Exists: server `/api/listings/cover`, product names (build.py:1678). Missing in build (not verified in detail). Size: medium. (Selling it waits for payments, see B.)
8. Collector must accept jobs that a claimed company adds on top of its ATS. Line 1903. Wording: «collect.py не пускает размещённые вакансии компаний, которые мы и так читаем; пропускать компании из списка claimed». Missing: no "claimed" in collect.py. Size: small.
9. Visa-sponsorship history by company from open US data (DOL). Line 137. Exists: perk page /perks/visa-sponsorship/. Missing: the history data. Size: large.
10. Hacker News "Who is hiring" threads as a source. Lines 426, 1923. Exists: Telegram reader only. Missing: HN (grep finds none). Size: medium.
11. Skill × country pages ("Node.js jobs in Vietnam"), now only for big places. Line 309. Not verified in code. Size: medium.
12. Vacancy forecast ("how long such roles stay open, probability still open"). Line 300. Exists: guide how-long-jobs-stay-open and status page. Missing: per-job forecast. Size: medium.
13. Verifiable history: daily fingerprint of the whole list in an open log. Line 298. Missing (grep). Size: medium.
14. Market report for hirers and report with our numbers (closing in 7/30/90 days, entry-level, map). Lines 442, 1137, 2294. Exists: guides and /how-to-hire/. Missing: dedicated report page. Size: medium.
15. More skill tests (Git, Java, Power BI) and a general "ready for an interview" test. Line 1256. Exists: 7 tests (SQL, Excel, Python, JS, Linux, Docker, React). Size: small each.
16. Page "<role> hourly rate" from postings with hourly pay; trust badges for employers. Line 1274. Exists: hourly pay pages `/jobs-that-pay/`, FAQ about hourly rate in build.py:5452. Missing: role hourly-rate pages. Size: small.
17. Technical blog "how we check 45,000 jobs every hour" for links. Lines 1276, 2308 (also 298). Exists: guide /guides/how-we-check-jobs-every-hour/ (CHANGELOG 15 Nov). Missing: engineering-style post. Domain now exists. Size: small.
18. Save the "For you" pick as an alert; share the pick by link. Line 479. Exists: alerts form (`alert_form`), /api/alerts. Size: small.
19. Employer onboarding email chain after sign-up. Line 94. Exists: mail through Beget. Size: small to medium.
20. Weekly free newsletter with a sponsor slot. Line 135. Exists: weekly alerts. Missing: sponsor slot, newsletter list. Size: medium.
21. Check of job markup with Google's test on a live page. Lines 192, 1785. Size: small (browser pane; no Google login needed).
22. Office address on the job page. Lines 1173, 1786. Wording: «адрес офиса на странице вакансии, если работодатель его указал». Size: small to medium.
23. Product screens like Rezi on resume builder, tools, search. Line 936. Exists: six pages rebuilt in dLocal style (CHANGELOG 17 Nov). Size: medium.
24. "Less AI-looking design" next step. Line 2239. Exists: light panels instead of dark (CHANGELOG 17 Nov). Not verified how far. Size: medium.
25. Open gaps of the search and AI answer check. Lines 1380, 1417, 1507, 1711, 1719, 58, 54 (competitor gaps). Wording: «Largest gap still open», «налог штата в калькуляторе зарплаты». Exists: SERP_AI_CHECK.md, 3 batches done, all 54 queries read. Size: medium, ongoing.
26. Missing job fields: animals, fashion, sport, nonprofit, transcription; split gaming from tech. Lines 515, 586. Exists: 23 categories, role "Game developer" (roles_info.py:40). Size: small.
27. Hybrid as an answer in the "For you" quiz; short duties line in search results; checklist per application; feedback form on the site. Lines 560, 561, 565, 588. Size: small each.
28. Salary in the visitor's currency; on-device AI summary of a job; cost-of-living comparison. Lines 547, 731. Exists: take-home tool (tools_pages.py:419, no state tax). Size: medium.
29. Resignation letters by profession; interview-tips articles; 2-3 articles a week. Lines 1058, 1003, 796, 1192 (logos). Exists: 24 situations, glossary 189 terms. Size: small, ongoing.
30. Logos: 18 companies without a logo, ~75 left. Lines 526, 1192. Size: small, manual.
31. Search engines of other countries (Naver, Seznam, Baidu). Line 1042. Size: small (research).
32. Companies by industry in the catalog; company quality score of a posting; company catalog with filters. Lines 804, 1211. Not found in code. Size: medium.
33. "Swipe through jobs" page with match score. Line 1066. Size: medium.
34. Full text of a job on the page. Lines 133, 187. Exists: full texts are now in the jobs database (CHANGELOG 18 Nov). Not verified that pages show all of it. Size: small to medium.
35. Pages for companies, countries, professions served from the records store (performance). Line 1292. Exists: records store, serve.py uses records (CHANGELOG 18 Nov). Not verified. Size: medium.
36. Remaining page-quality checks: company icons without width/height, descriptions under 120 characters. Line 1149. Size: small.
37. Second research pass of competitor reports (Upwork, Fiverr, SEEK, hh.ru, Jooble, Adzuna, Handshake, Wellfound, Teal...). Lines 698, 1234, 866, 871, 906, 1710. Exists: many RESEARCH_*.md files, REPORT_RU.md. Not verified which remain. Size: small.
38. Regular prices: remove `launch_prices` and `was` from config. Line 821. grep finds no `launch_prices` in config.json or build.py, so may be done; not verified. Size: small.
39. Ideas not started: badges also on job page, interview recording analysis (talk time), Chrome extension that fills applications, jobs-app with cards. Lines 2220, 1307. Size: large.
40. Mail auto-reply and `/help/` answers by mail. Lines 1162, 1781. Exists: /help/ (CHANGELOG 13 Nov). Missing: inbound auto-reply (needs mail panel work, see B for DKIM). Size: medium.
41. Privacy and terms texts for the new data (subscriptions, employer accounts). Line 1822. Not verified whether published. Size: small.
42. Trust pack for employers: exact dates, refund rule, click counter. Line 170. Exists: `/api/public/hit`. Not verified. Size: medium.
43. Show claimed-page mark on company pages and employer call on job page. Lines 1906, 759. Exists: claims, views in account.js. Not verified on the public pages. Size: small.
44. Employer gets a "your jobs page" link when posting opens. Line 1123. Not verified. Size: small.

---------------------------------------------------------------------------

## B. Waits for the owner or an outside thing

1. Take payments (Cryptomus / NOWPayments). Lines 29, 30, 32, 36, 468, 708, 709, 1213, 1292, 1598, 1795, 1827, 2257, 83-section 1104. Waits for: merchant account and keys, `PAYMENTS_LIVE=1` (line 1800), owner's "da" after site is finished (line 1101-1108). Includes Plus one-time payment, Hiring Pass, credits, second crypto cashier, cards later.
2. Search Console, Bing, Indexing API, sitemap submit. Lines 69, 190, 191, 2257. Waits for: owner's Google login; decided to do last (line 1112 section 108). Note line 1560s: Googlebot barely knows the domain.
3. Google sign-in (OAuth client) and LinkedIn sign-in (app). Lines 1596, 1597, 666. Button code exists (assets/account.js:152, 175); waits for the OAuth client and LinkedIn app keys.
4. AI in Plus: resume per job, letters, interview coach, AI mentor, deeper roast and LinkedIn review. Lines 40, 581, 582, 583, 600, 690, 691, 856, 1307(tone part done). Waits for: Anthropic API key and the payment/limit decision.
5. Social channels and bot: Telegram channels and bot, X, LinkedIn page, Reddit agent. Lines 338, 340 (share button exists, site.js:887), 608, 610, 612, 747, 1214, 2237. Waits for: owner's accounts, BotFather token typed on the server.
6. Translations and country editions. Lines 70, 329, 330, 333, 1919. Waits for: owner's go (the Russian section was dropped for now, see D).
7. Letters to list sites, catalogs and aggregators; llms.txt and MCP catalog submissions; Trustpilot invitations; Jooble/Adzuna/Talent.com submissions. Lines 614, 889 (pay per click), 1675, 2257, 2295. Feed `/feeds/jobs.xml` exists. Waits for: owner's approval and accounts.
8. Moderation queue reader. Line 415. Waits for: a person (owner). `/admin/` exists.
9. Mailboxes and mail panel: press@ mailbox, DKIM in Beget panel, mail auto-reply. Lines 1781, 2129, 2228. Waits for: owner / Beget panel.
10. WordPress plugin. Line 245. Waits for: owner's wordpress.org account.
11. GitHub public lists (internships, visa, remote). Line 130. Waits for: owner's "yes" for a public repo.
12. Compare Hirify traffic with crypto boards. Lines 1171, 1782. Waits for: Semrush data from owner.
13. Rezi Pro month and cabinet study. Line 2296. Waits for: owner buys and signs in.
14. Ads on competitor brands (RemoteJobsFinder way). Line 1945. Waits for: card for Google Ads, owner's decision.
15. Partner/affiliate program, referral, Plus codes for bloggers. Lines 91, 569, 786, 1066, 1252. Waits for: payments plus owner's share decision.
16. Refund guarantee wording. Line 93 (and 601). Waits for: owner's decision (refunds by crypto are manual).
17. Employer reviews, voting rating, mentors, sponsored articles, company-guide product, universities plan, more ways to earn. Lines 629, 798, 801, 803, 806, 695, 760. Waits for: owner's decision and real people.
18. Contact mail line on site. Line 44. Mailbox support@ now exists (line 2226): the mark is stale, only owner choice of public address remains.
19. Server-side items parked for the owner: employer/job-seeker data collection business plan and revenue stages (lines 2003, 1836 LinkedIn keys). Waits for: keys above.

---------------------------------------------------------------------------

## C. Stale marks: done later (line, task, evidence)

- 31, 1213, 1795, 1798-1822 (server ready, needs Cloudflare login): server runs on Hostinger, `server/prod.mjs`; CHANGELOG 15 Nov "Accounts, job alerts and free employer posting on our own server"; routes in server/src/worker.js (/api/alerts, /api/claims, /api/admin, /api/me/export, /api/domain).
- 34, 114, 443, 1811, 2003, 2140 (free job posting by employers): CHANGELOG 15 Nov (free employer posting) and 18 Nov "Employer account: a company that is new on the site gets its company page the moment it posts its first job", owner tried it; post form in assets/account.js. (Paid part of 443: see B.)
- 39, 92, 115, 171, 359, 1801, 1805 (e-mail alerts): `alert_form` in build.py:1275, /api/alerts, server/src/alerts.js, mail through Beget; CHANGELOG 15 Nov accounts and job alerts. Weekly/daily choice and one-click unsubscribe described at 1805.
- 41 (saved jobs on all devices): `/api/sync`, assets/account.js header "saved jobs on every device".
- 44: support@ mailbox set up, line 2226.
- 57: llms.txt, structured facts; MCP connector `/mcp` in serve.py:13 and nginx-hrn.conf:72 (line 1302 ✅).
- 113: build.py:2444-2451 pages `skills/<t>/new/`, `roles/<r>/new/`, `remote/new/` "posted in the last 3 days".
- 134, 296 (MCP part), 696 (MCP part): same MCP evidence; only catalog submissions remain (B7).
- 136, 1816: "Claim company page": `/api/claims`, assets/account.js company tab.
- 138, 164: "Hide remote jobs closed to my country" (assets/app.js:406), `tz_countries.json`; remote country label done.
- 342: recruiter cabinet: assets/account.js (team, invites, billing, talent).
- 410: work-email hint (account.js:177), "Add your work email" step (:300), statuses waiting/not accepted with reason (:129, :285, :296, :466). (Remaining parts in A6.)
- 428, 2137 (new ATS: Workable, Recruitee, Teamtailor, Personio, SmartRecruiters): collect.py header and `ATS_LIMIT`. Pinpoint not seen.
- 430, 897, 2148: Telegram channel posts: `telegram_jobs.py`, build.py:1590 (channel post label).
- 519: "tech jobs" rewritten for all professions: CHANGELOG 15 Nov "All professions, not only tech (owner's decision)... about 140 places".
- 536: exact posting times: CHANGELOG 13 Nov 09:46 "Exact posting times and an hourly run" and 15 Nov live list.
- 547 (take-home part): take-home pay tool, tools_pages.py:419.
- 633: part-time near me: build.py:8228 `part-time-jobs-near-me/`.
- 635: employer section: /post-a-job/, /pricing/, /how-to-hire/, /job-descriptions/ (CHANGELOG 13-14 Nov).
- 650 (pages for salaries by level, map): CHANGELOG 13 Nov 01:30 pay ladder, 14 Nov /map/.
- 666: LinkedIn button in account.js:175 (shown when keys on), domain check endpoints.
- 673, 1291, 1333, 1334, 1345, 1347 (move to domain, server login, secrets): ROADMAP section 107 (line 2251-2255) "Переезд на jobseveryhour.com завершён".
- 710: self-service purchase is how the server works (line says so).
- 739, 1066 (gallery of templates), 1307 (tone), 1262 partly: assets/resume.js:256 template gallery; tone picker resume.js:73-81; cover letter examples CHANGELOG 14 Nov 12:30; resignation letters 14 Nov 10:40; live score and target job 14 Nov 22:30.
- 89: audience pages: CHANGELOG 17 Nov "/jobs-for/ (53 pages)".
- 169-170 partly: see A5, A42.
- 229, 386, 1174, 1505, 1557, 1626, 1172, 28-line page review: CHANGELOG 17-18 Nov "Review by eye" batches 1 to 5, account end-to-end pass, design pass 15-17 Nov. (Coverage table kept in ROADMAP.)
- 301 (personal radar): partly: "For you" fit shown on every job page (CHANGELOG 14 Nov 15:40) and local notification `hrn-fit` (assets/site.js:1403). Full radar not verified.
- 340 (LinkedIn share button): assets/site.js:887.
- 614 / 846 / 848 (XML feed for aggregators): CHANGELOG 13 Nov 19:30 `/feeds/jobs.xml`; build.py:4492; research in AGGREGATORS_RESEARCH.md. (Submissions: B7.)
- 796 (blog first 9 articles), 1003: /guides/ and does-senior-pay-more (CHANGELOG 14 Nov); cover letter examples; interview questions 391 pages.
- 894: relocation guides: `relocate/` linked in jobs_for_pages.py:1014.
- 900: glossary 68 -> 189 terms (CHANGELOG 18 Nov).
- 922: crypto hub rebuilt: CHANGELOG 13 Nov 15:00.
- 951, 960, 1153: standing rules and process (AGENT_NOTES.md; cloud routine runs in CHANGELOG).
- 969: six new categories: CHANGELOG 13 Nov 21:10 and 16 Nov 00:50.
- 989 (pause on 328 Workday boards): CHANGELOG 17 Nov "74 large Workday boards came off hold", 18 Nov "the 60 largest boards released". Rest in A1.
- 1461: How to become person form: CHANGELOG 17 Nov 16:00 and 18 Nov "Role names: 123 kinds of work... person form".
- 1502: fit_title cut: CHANGELOG 18 Nov "Page titles keep the word people search for".
- 1606: price comparison next to Indeed, LinkedIn, etc.: CHANGELOG 13 Nov 23:20 pricing page "elsewhere" row.
- 1690: installable app: manifest.json (build.py:747, 9175) and sw.js (site.js:1067). Server push not verified.
- 1906: claims, views and apply clicks: account.js:232, :282.
- 2292: `/free-resume-builders/`: CHANGELOG 14 Nov 19:30 and 18 Nov (17 builders).
- 710, 1213: see above.
- 2003: server ready and checked, now live.
- 1380: process; the 3 batches are in CHANGELOG 18 Nov.

---------------------------------------------------------------------------

## D. Dropped

- 1026 (30-50 Russian pages /ru/, then ruble payments): line 2236 "Русский раздел: решение владельца — пока не делаем". (Also 1919 proposal.)
- Telegram mass reading of others' channels was first rejected (line 2233 "Чужие каналы массово не читаем"), then reversed by the owner on 15 Nov ("без спроса, как Hirify", line 2148). Net: done, not dropped.
- NOWPayments, Search Console, Bing: not dropped, postponed to the end by owner (section 108, "только тогда, когда всё супер сделаем"): counted in B.
- No ⛔ mark was found on any of the audited lines.

---------------------------------------------------------------------------

## E. Counts (approximate; grouped by task, not by line)

- Marked lines read: about 225 (rows and bullets with 📋 🟡 ⏳ 🔨 🔄).
- A. Still open, can be done now: 44 grouped tasks (about 75 lines); of them about 12 are "not verified".
- B. Waits for owner or outside: 19 grouped tasks (about 60 lines).
- C. Stale, done later: about 75 lines in about 45 groups (roughly one third of all marks).
- D. Dropped: 1 line (1026), plus 1919 as the same idea.
- Lines whose old mark is purely a status label of an ongoing process (951, 1153, 1380, 1626): counted in C or A25.
