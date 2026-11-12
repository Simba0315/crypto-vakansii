# User pains: what job seekers and employers complain about on job sites

Researched 2026-11-13 from reviews, comment threads and community discussions, not from marketing pages. Our side was checked
against `build.py`, `assets/site.js`, `AGENT_NOTES.md`, `ROADMAP.md`, `COMPETITOR_GAPS.md` and the live home page as they stood that day.

How to read this file

- "Opened" means the page itself was loaded and read. "Snippets only" means the site refused automated reading and the facts come
  from search-result summaries; treat those as weaker.
- Apart from the Product Radar page (read as raw text in the browser), pages were read through a fetch tool that returns a
  review-by-review digest. So wording below is paraphrased, not quoted. There is exactly one verbatim quote in this file (section 2).
  Every point carries a link so the original wording can be checked.
- Frequency = in how many of the sources I read the pain appears, with ties broken by how many individual reviews raise it. This is
  a count over what I read, not a statistical sample. Trustpilot shows only the newest 20 to 24 reviews per page; for the large
  sites most of those are dated August to November 2026.
- Reviewer roles (job seeker or employer) are mostly inferred from the review text.
- Some reviews tell the reader to do something (avoid a site, use another one, withhold a phone number). Those lines were recorded as
  sentiment and not followed.
- Effort: S = hours to a day, M = several days, L = weeks (same scale as `COMPETITOR_GAPS.md`).

---

## 1. Sources

53 pages opened, 51 of them with content. About 750 reviews and comments were read individually (as review-by-review digests, see
above), plus about 1,280 Hacker News comments read as thread digests.

### Opened and read

| # | Site reviewed | Where the reviews are | URL | Read | Notes |
|---|---|---|---|---|---|
| 1 | Hirify | Product Radar product page | [link][pr] | 96 comments (all; about half are the founder's replies) | Raw text, in Russian |
| 2 | Hirify | Product Radar maker profile | [link][pr-user] | 0 | No reviews on it; no other Hirify pages linked |
| 3 | Hirify, hh.ru | Habr article comments (an AI helper for hh.ru search) | [link][habr-hh] | 22 comments (7 about Hirify) | |
| 4 | Hirify | Tproger interview with the founder | [link][tproger] | Article, no comments shown | The founder's own account |
| 5 | Indeed | Trustpilot (score 1.8, 13,107 reviews) | [newest][tp-indeed], [low-star][tp-indeed-1], [five-star][tp-indeed-5] | About 64 | About 14 from employers |
| 6 | ZipRecruiter | Trustpilot (4.4, 12,955) | [newest][tp-zip], [low-star][tp-zip-low] | 43 | Most five-star reviews praise a named support agent |
| 7 | FlexJobs | Trustpilot (4.1, 8,344) | [newest][tp-flex], [low-star][tp-flex-low] | 44 | Most reviews are marked "Invited" |
| 8 | LinkedIn | Trustpilot (1.1, 4,010) | [link][tp-linkedin] | 20 (5 about jobs or hiring) | |
| 9 | Glassdoor | Trustpilot (1.1, 1,106) | [link][tp-glassdoor] | 20 | |
| 10 | Monster | Trustpilot (4.1, 26,603) | [newest][tp-monster], [low-star][tp-monster-low] | 44 | Mostly about its resume builder |
| 11 | Dice | Trustpilot (1.8, 17) | [link][tp-dice] | 17 (all) | 4 from employers |
| 12 | Wellfound | Trustpilot (3.9, 144) | [link][tp-wellfound] | 24 | |
| 13 | We Work Remotely | Trustpilot (2.9, 271) | [link][tp-wwr] | 20 | |
| 14 | Remote OK | Trustpilot | [link][tp-remoteok] | 0 | Profile removed by Trustpilot; reason not stated |
| 15 | Remotive | Trustpilot (4 reviews) | [link][tp-remotive] | 4 (all) | |
| 16 | Himalayas | Trustpilot (7 reviews) | [link][tp-himalayas] | 7 (all) | |
| 17 | Jobright | Trustpilot (4.8, 3,763) | [link][tp-jobright] | 24 | Nearly all reviews are from the last 12 months and very short |
| 18 | Teal | Trustpilot (4.3, 120) | [link][tp-teal] | 22 | |
| 19 | Simplify | Trustpilot (2.7, 22) | [link][tp-simplify] | 20 | |
| 20 | Huntr | Trustpilot (4.6, 22) | [link][tp-huntr] | 20 | |
| 21 | web3.career | Trustpilot (1 review) | [link][tp-web3] | 1 (all) | Single review |
| 22 | CryptoJobsList | Trustpilot (4.7, 28) | [link][tp-cjl] | 21 | None from the last 12 months |
| 23 | Hired | Trustpilot (4.5, 1,978) | [link][tp-hired] | 24 | None from the last 12 months |
| 24 | Otta | Trustpilot (3.5, 1,063) | [link][tp-otta] | 23 | |
| 25 | Welcome to the Jungle | Trustpilot (2.2, 148) | [link][tp-wttj] | 14 | |
| 26 | HiringCafe | Trustpilot (3 reviews) | [link][tp-hc] | 3 (all) | |
| 27 | hh.ru | Trustpilot | [link][tp-hh] | 2 of 35 | New reviews closed for Russian companies |
| 28 | ZipRecruiter | SmartCustomer (Sitejabber now redirects there) | [link][sc-zip] | 20 | 10 from employers |
| 29 | LinkedIn | SmartCustomer | [link][sc-linkedin] | 20 (8 about jobs) | |
| 30 | Dice | SmartCustomer | [link][sc-dice] | 2 | |
| 31 | Indeed app | App Store | [link][as-indeed] | 10 | |
| 32 | ZipRecruiter app | App Store | [link][as-zip] | 10 | |
| 33 | LinkedIn app | App Store | [link][as-linkedin] | 10 (6 about job search) | |
| 34 | hh.ru | T-Bank review catalogue | [link][tbank] | 20 | 2 are about an unrelated business |
| 35 | hh.ru | T—Zh community post on silence after applying | [link][tj-hh] | 50 of 78 comments | |
| 36 | hh.ru | T—Zh question on automatic rejections | [link][tj-drop] | 3 comments | |
| 37 | Russian job market | Finance Mail.ru news item on a complaint analysis | [link][mailru] | Article | Analysis by a communications agency; sample size not given |
| 38 | Habr Career | Its own blog post on reading employer reviews | [link][habr-career] | Article | No user complaints about the site in it |
| 39 | Job postings in general | Hacker News: 28% of postings on career sites open over 90 days | [link][hn-90] | About 330 of 364 comments | Digest |
| 40 | Job postings in general | Hacker News: proposal to ban ghost jobs | [link][hn-ban] | About 200 of 253 | Digest |
| 41 | Job postings in general | Hacker News: paper on ghost jobs | [link][hn-ghost] | About 150 of 567 | Mostly about visa rules |
| 42 | Job postings in general | Hacker News: you can't hire because you don't post salary ranges | [link][hn-salary] | About 150 of 523 | Digest |
| 43 | A remote job aggregator | Hacker News: Show HN, best-paying remote engineering jobs | [link][hn-swe] | About 140 of 143 | Closest to feedback on a site like ours |
| 44 | Remote boards | Hacker News: where to find worldwide remote jobs | [link][hn-remote] | 52 | |
| 45 | HiringCafe | Hacker News thread | [link][hn-hc] | 15 | |
| 46 | "Verified" job board idea | Hacker News: would you use a board where every listing is verified | [link][hn-verified] | 92 | |
| 47 | Job search in general | Hacker News: advice after 450 applications | [link][hn-450] | About 150 of 180 | |
| 48 | r/recruitinghell, second-hand | Truffle report on 20,973 posts, January to June 2026 | [link][truffle] | Report | Keyword counts over posts, by a company that sells screening software |
| 49 | Reddit opinions of job boards, second-hand | GummySearch round-up | [link][gummy] | 17 brands, one-line opinions | No dates given |
| 50 | Applying in general | Product Hunt discussion | [link][ph] | 3 replies | |
| 51 | Indeed, employer side | Recruiting Headlines article (May 2026) | [link][rh] | Article | Based on a Facebook group of HR people |
| 52 | Indeed, employer side | SHRM article on pay-per-application pricing (2023) | [link][shrm] | Article | |
| 53 | Crypto job scams | Cointelegraph Magazine first-person account (June 2026) | [link][ct] | Article | |

### Snippets only (blocked or empty)

| Site | What happened | What I used |
|---|---|---|
| Reddit (r/jobs, r/recruitinghell, r/cscareerquestions, r/remotework, r/jobsearchhacks, r/recruiting, r/hiringcafe) | Reddit refuses this tool for both search and reading | Rows 48 and 49 above and search summaries of third-party articles. No thread was read |
| G2 (Indeed, LinkedIn Recruiter) | HTTP 403 | Search summaries |
| Capterra (Indeed for Employers, ZipRecruiter, LinkedIn Recruiter) | HTTP 403 | Search summaries |
| TrustRadius, Software Advice (Indeed) | HTTP 403 | Search summaries |
| otzovik.com and irecommend.ru (hh.ru) | HTTP 507 and 521 | Nothing usable |
| Google Play (LinkedIn) | Page returned no reviews | Nothing |
| Product Hunt product review pages (Hirify, Teal) | HTTP 404 | Nothing |
| Habr Career user reviews | Not found as a page | Search summary of a product manager's replies to users |
| Wellfound and Workable on G2 | Nothing returned | Nothing |
| Crypto recruiting scams (security blogs) | Not opened | Search summaries, plus row 53 |

---

## 2. Hirify: what its users say

Almost everything below is from the Product Radar discussion ([link][pr]); names are the commenters' names on that page. It was the
launch thread (filed in the category where makers ask for harsh feedback, 692 supporters), so the audience is friendly founders and early users, and the tone
is far warmer than on any review platform in section 1. No independent review of the paid Plus tier was found anywhere.

### What people praise

| Point | Who | URL |
|---|---|---|
| Calm, pleasant interface that is still functional; one visitor says he stayed for about 40 minutes | Irina Glazkova, Egor Ivin, Boris Glen, Nikolay Sukonny, Georgy K. | [pr][pr] |
| Filters, and in particular the ability to exclude values. Even the harshest critic lists this as the plus | Ivan Ivanov, Irina Glazkova, Darya Rusina | [pr][pr] |
| One search instead of a folder of Telegram job channels, hh and LinkedIn; saves hours | Vitaly Simonov, Dmitry Volkov, Dmitry Doe | [pr][pr] |
| Many direct recruiter contacts | Dmitry Doe | [pr][pr] |
| The original source is named on every vacancy | Nikolay Grigoryev | [pr][pr] |
| New matches arrive at once in a bot | Dmitry Volkov | [pr][pr] |
| Volume: React Native jobs almost at hh level; another user is impressed by the sheer number of vacancies | Georgy K., Oleg Labunin | [pr][pr] |
| Results: one user found a job, another is in talks, a third now uses mostly Hirify. The one quote in this file: it «помог мне найти работу без унижения через hh» (it helped her find a job without the humiliation of going through hh) | Maria Tsarkova, Daniil Konozakov, Darya Rusina | [pr][pr] |
| The founder answers every comment, fixes reported bugs within days, runs a support chat | Seen throughout; Larisa Razorenova names creator and support | [pr][pr] |
| Tiredness with hh.ru is itself a reason to support it | Oleg R, Mark Stramousov, Aleksandr A. | [pr][pr] |
| A recruiter who posts for free: candidates do come for remote roles | Larisa Razorenova | [pr][pr] |
| Outside view: it seems to cover nearly every popular source and may push other aggregators aside | Pcturl | [habr][habr-hh] |

### What people complain about

| Point | Who | The founder's answer | URL |
|---|---|---|---|
| Weak moderation: adverts for unrelated Telegram channels dressed up as vacancies; product called raw, too early to charge | Ivan Ivanov | Sources are vetted, posts pass phrase bans and an AI filter, spam is removed when reported; source text is left unedited on purpose | [pr][pr] |
| Empty vacancies that only send you to another site | Nikolay Grigoryev | Will not remove them: it is an aggregator | [pr][pr] |
| Mixed languages: with Russian chosen, some buttons, dates, skills, footer links and page titles stay English | Georgy K., Nikolay Grigoryev | Partly promised, partly declined | [pr][pr] |
| Adding a filter while on page 4 left an empty page although matches existed | Roman Yushkov | Fixed | [pr][pr] |
| Back does not return to the same place in the list when infinite scroll is on | Roman Yushkov, Darya Rusina | Could not reproduce; suggested the pagination setting | [pr][pr] |
| Saved jobs: the in-site back button jumps to the home page; no sorting; no mark on jobs that went to the archive; no pages | Darya Rusina | Redesign planned, not a priority | [pr][pr] |
| A job opens in the same tab, so the list is lost | Roman Yushkov | Use middle click; kept for mobile | [pr][pr] |
| Not every vacancy brings many candidates | Larisa Razorenova (recruiter) | Working on it | [pr][pr] |
| Where Russian users' data is stored | Nikolay Grigoryev | Says storage in Russia is prepared | [pr][pr] |
| Doubt that hh can be moved at all; calling the product the best job board is seen as bold | Maksim Rachitsky, Aleksey Semenov | | [pr][pr] |
| Even with Hirify you still have to work with hh | The founder himself | | [habr][habr-hh] |
| After the paid launch, a profile could be created but not edited and hundreds of users wrote in; the payment provider handled foreign cards badly | The founder's own account | | [tproger][tproger] |

### What people ask for

| Request | Who | URL |
|---|---|---|
| A rating of employers by candidates: do they answer, how many interview rounds | Yury Kupriyanov (founder: postponed, maybe as tags) | [pr][pr] |
| Sorting of saved jobs, an "archived" mark, pages in the saved list | Darya Rusina | [pr][pr] |
| Open a job in a new tab by default | Roman Yushkov | [pr][pr] |
| Stricter intake: do not collect empty postings | Nikolay Grigoryev | [pr][pr] |
| Something for employers; direct contact between hiring manager and candidate without an HR layer | Tatyana Urusova, Mikhail Tseytlin | [pr][pr] |
| Short paid gigs or a freelance section | Aleksey Semenov | [pr][pr] |
| Monetisation ideas offered by commenters: partner offers, charging employers, keeping resumes on file | Anton Ross, Ivan Kotsky | [pr][pr] |
| From the founder's own user survey: international vacancies and AI help with the resume and cover letter (both became Plus) | Founder's account | [tproger][tproger] |

Not seen in any user comment: complaints about Plus hiding company names and apply links on international jobs (noted in
`COMPETITOR_GAPS.md` section 3). A search result title suggests some Hirify job titles are visible only after login; not opened.

---

## 3. Job seekers' pains, most frequent first

### J1. Listings that are no longer real openings (22 sources)

- **How people put it.** Ghost listings persist and reporting them changes nothing ([Indeed][tp-indeed]); the Jobs tab keeps serving
  the same weeks-old, fake and repeated postings ([LinkedIn][tp-linkedin]); the site feels like a graveyard because companies stop
  updating ([Wellfound][tp-wellfound]); a lot of time went into roles that had already expired ([Otta][tp-otta]); candidates turned up
  to interviews for jobs already filled ([ZipRecruiter][sc-zip]); a posting turned out to be nine months old and the careers system
  hid its date; one commenter says ghost jobs cost him half a year and he would pay well for a fix ([HN][hn-90]). In Russia, an agency
  analysis attributes 52.3% of negative posts about job search to dead vacancies ([Mail.ru][mailru], single source).
- **Counter-view worth keeping.** Hiring managers reply that long-open postings are often backfill or continuous hiring, or simply
  forgotten ([HN][hn-90]); in a keyword count of r/recruitinghell, ghost jobs are only 2.0% of posts, far behind rejection and silence
  ([Truffle][truffle]).
- **Said about.** Indeed, LinkedIn, Wellfound, Otta, We Work Remotely, FlexJobs, Teal, ZipRecruiter, Remotive, Dice, Welcome to the
  Jungle, company career sites in general.
- **Our site today.** This is our core promise. Daily check against the employer's own system; closed roles leave the lists and go to
  the archive; each job shows "Posted", "Open for N days" with the median for similar roles, "Last checked" and "Source"; roles open
  90+ days get a warning pill and a note; a role posted again after closing gets a "History" line. Gaps: long-open roles still sit in
  normal results (the home page shows ages up to 17 months); no way to hide them; nothing at company level; we cannot know whether a
  seat is really being filled.
- **Could build.** (a) "Hide roles open 90+ days" switch and an age band in search, remembered in the browser: in the browser, S.
  (b) "Talent pool" label when the posting text itself says it is a general or future-openings application: static, S. (c) Company
  hiring-facts card: median days to close, share of roles open 90+ days, reposts in 12 months: static, M. (d) Public data-health page
  (sources checked today, added, closed, failed): static, S.

### J2. Applying and hearing nothing (19 sources)

- **How people put it.** Fifty applications and silence; rejections that arrive within seconds; template refusals; many commenters
  call silence the default ([T—Zh][tj-hh]). About half of the companies never answered ([HN][hn-90]). The worst part is not knowing
  whether anyone opened a carefully tailored application ([Product Hunt][ph]). Years of applications with almost no callbacks
  ([Indeed][tp-indeed-1]); forty-plus applications answered by rejection or silence, and a wish to flag rejected roles
  ([Otta][tp-otta]). How a rejection is delivered is the single largest theme in r/recruitinghell: rejection 15.5%, no response 9.5%,
  applications vanishing into the employer's system 6.6% of posts ([Truffle][truffle]). In Russia, 45.3% of negative posts are about refusals without a reason
  ([Mail.ru][mailru], single source).
- **Said about.** Indeed, LinkedIn Easy Apply, Otta, FlexJobs, Hired, We Work Remotely, Wellfound, Teal's job list, web3.career, hh.ru,
  Workday-style application systems.
- **Our site today.** Nothing direct: we do not carry applications. Indirect help only: "Mark as applied" and the tracker with five
  statuses and notes; the job page says how long similar roles stay open.
- **Could build.** (a) In "My jobs": days since applied, a follow-up nudge after a period the user picks, a follow-up email template:
  in the browser, S. (b) Anonymous one-click "heard back / nothing after 30 days" sent from the tracker, shown per company only above
  a minimum sample: needs the API, M to L, with real abuse risk and no moderator (see section 6, item 15).

### J3. Scams, fake recruiters and personal data misuse (17 sources)

- **How people put it.** After entering a phone number, the calls that came were insurance sales and scams ([Indeed][tp-indeed],
  [Indeed][tp-indeed-1]); the only callbacks are scam calls ([Monster][tp-monster-low]); a belief that the site sells contact data
  ([ZipRecruiter][sc-zip]); a fake-cheque attempt and jobs that differ from the advert ([ZipRecruiter app][as-zip]); too many scam
  jobs, please moderate ([Himalayas][tp-himalayas]); only scammers replied, a reported fake advert stayed up, and one "employer" asked
  to install an app ([web3.career][tp-web3], single review); adverts for Telegram channels posing as vacancies ([Hirify][pr]). A
  first-person account of a crypto job advert that led to a fast reply, an unfamiliar meeting app and an installer file
  ([Cointelegraph][ct]). Fake listings exist to harvest data from people who apply under their real identity ([HN][hn-verified]).
- **Said about.** Indeed, ZipRecruiter, Monster, Himalayas, web3.career, Wellfound (spam messages), LinkedIn, Dice (contact after
  account deletion), Glassdoor (phone number demanded), Hirify, crypto hiring in general.
- **Our site today.** Strong by construction, weak in words. Every job comes from the careers system of a hand-listed company and
  links to it; no sign-up, no resume upload, no phone number, no third-party requests. But there is no safety page, no "report" button,
  and the planned free employer posting (automatic link check only) will open the first door for fakes, most of all in the crypto
  section.
- **Could build.** (a) A safety page: how listings get here, what we never ask for, a short checklist for crypto roles (unknown
  meeting apps, code to run, wallets), linked from every job: static, S. (b) For self-serve posting: accept only apply links on the
  employer's own domain or a known careers system, no messenger handles as contact, label such jobs clearly (the label exists): needs
  the API, S, plus an owner decision on holding first-time domains. (c) "Report a problem" that triggers an automatic re-check of the
  source rather than a human review: needs the API, S.

### J4. Irrelevant results and filters that do not hold (16 sources)

- **How people put it.** Preferences are ignored and unwanted job types keep coming back, even after pressing the button meant to
  hide them; matches for jobs needing a licence or trade the person does not have; a set distance is not respected
  ([Indeed][tp-indeed], [Indeed][tp-indeed-1]). Searches return driving and fast-food work ([ZipRecruiter][sc-zip]); recommendations
  cannot be steered ([ZipRecruiter app][as-zip]). Filters do not work and alerts ignore an exclusion ([Dice][tp-dice]). An update
  removed search history and several filters; search insists on a job title ([LinkedIn app][as-linkedin]). One title per search and no
  custom filters ([Otta][tp-otta]); a request for tighter title filtering and a pay filter ([FlexJobs][tp-flex]); alerts for relevant
  vacancies cannot be tuned ([hh.ru][tbank]).
- **Said about.** Indeed (the most reviews of any pain on its page), ZipRecruiter, Dice, LinkedIn, Otta, Welcome to the Jungle,
  Simplify, FlexJobs, Monster, hh.ru, Jobright, Himalayas.
- **Our site today.** Filters for posting age, category, level, location, pay threshold, work style, perk, contract type and skills;
  three sort orders; "Not interested" on a single job; skill matching in "For you". Missing: any way to exclude (a company, a word in
  the title, a level), and "hide this company".
- **Could build.** (a) Exclusions stored in the browser and applied to search, "For you", saved searches and lists: company, title
  word, level: in the browser, S. (b) "Hide this company" on job and company pages: in the browser, S. (c) Plain-language search that
  only fills the visible filters (gap 18 in `COMPETITOR_GAPS.md`): in the browser, S.

### J5. Paying to look for work: paywalls, trials that turn into subscriptions, refunds refused (11 sources)

- **How people put it.** A cheap trial became a twelve-month commitment of about $180, and billing went on after a confirmed
  cancellation; half of the 20 newest reviews are about this ([We Work Remotely][tp-wwr]). Charged twice, charged after cancelling,
  full refund only on the same day, a lower price offered only when you try to leave, and the same jobs are on free sites
  ([FlexJobs][tp-flex], [FlexJobs][tp-flex-low]). A monthly fee just to apply ([Remotive][tp-remotive]); payment asked during
  registration with a small skip button ([Himalayas][tp-himalayas]); refund refused after a same-day cancel, an offer that was not what
  it said ([Simplify][tp-simplify]); the resume cannot be downloaded without paying, or even after ([Monster][tp-monster-low]); money
  taken monthly with no clear reason ([hh.ru][tbank]).
- **Said about.** We Work Remotely, FlexJobs, Remotive, Himalayas, Simplify, Monster, hh.ru, LinkedIn Premium.
- **Our site today.** Everything is free, there is no account and no card anywhere; applying is always on the employer's page; Plus is
  not sold. The plan for Plus is a one-time payment, which removes renewal traps. One planned item cuts against this pain: "jobs 48
  hours earlier" for payers (see section 6, flags).
- **Could build.** A short page of promises with dates: what is free and stays free, one-time payments only, nothing renews, refund
  rule: static, S, needs the owner for the refund terms.

### J6. Things that break: back button, lost place, wrong counts, slow pages (11 sources)

- **How people put it.** Returning from a job loses the place in the list; a filter change leaves an empty page; saved jobs cannot be
  sorted ([Hirify][pr]). The back button breaks and the counter shows more results than the list ([HiringCafe][hn-hc]); the design is
  hard to learn ([HiringCafe][tp-hc]). A big table lags on a phone and an animation froze the tab ([HN][hn-swe]). Downloads fail and
  the site is glitchy ([Monster][tp-monster-low]); search stayed broken for weeks ([Dice][tp-dice]); a redesign around an AI feature
  drove regulars away ([Welcome to the Jungle][tp-wttj]); application forms fail with errors ([Indeed][tp-indeed-1]).
- **Said about.** Hirify, HiringCafe, Monster, Glassdoor, Dice, Welcome to the Jungle, Himalayas, LinkedIn, Indeed.
- **Our site today.** Search keeps filters in the address, previews a job beside the list, and "Apply" opens a new tab. Not tested in
  this pass: whether back restores scroll and the loaded "Show more" pages, whether the count always equals the rows, speed of the
  36,000-row search on a mid-range phone.
- **Could build.** A fixed regression checklist run before each push (back and scroll, count equals rows, filter change resets
  paging, phone timing), with fixes for whatever fails: in the browser, S.

### J7. Sign-up and personal-data walls, lockouts (10 sources)

- **How people put it.** Reading anything now needs a login, a linked second account and a phone number; several call it data
  collection ([Glassdoor][tp-glassdoor]). Too much information demanded for mediocre leads; a review must be written before reviews can
  be read ([Indeed][tp-indeed-1]). Applying requires an account and the verification email never comes ([Dice][tp-dice]). Accounts
  restricted right after sign-up with no reason ([Wellfound][tp-wellfound]). Weariness with registering at one more HR service per
  application ([HN][hn-90]). An account that the user cannot delete himself ([HiringCafe][tp-hc]).
- **Said about.** Glassdoor, Indeed, Dice, Wellfound, LinkedIn, Welcome to the Jungle, ZipRecruiter, HiringCafe.
- **Our site today.** Fully covered: no account, nothing uploaded, tracker and resume builder live in the browser.
- **Could build.** (a) Say it with specifics on the home and About pages: no email, no phone, no resume upload: static, S. (b) "Your
  data on this device" page with one button to save everything to a file, one to restore, one to erase: in the browser, S.

### J8. Pay missing, or a range too wide to mean anything (9 sources)

- **How people put it.** Many skip a posting with no pay and read the silence as concealment; a very wide range tells nothing
  ([HN][hn-salary], [HN][hn-90]). Listings lack ranges even where a pay-transparency law requires them ([Dice][tp-dice],
  [LinkedIn][sc-linkedin]). Requests for mandatory ranges and a pay filter ([ZipRecruiter app][as-zip], [FlexJobs][tp-flex]). Pay
  offered differs from pay advertised ([Indeed app][as-indeed]). On an aggregator, a total figure lower than the base figure was
  spotted at once ([HN][hn-swe]).
- **Said about.** Job boards in general, Dice, LinkedIn, ZipRecruiter, FlexJobs, Indeed.
- **Our site today.** Mostly covered: pay shown where the employer states it, "Salary listed" and threshold filters, sort by pay,
  medians labelled as medians, salary pages. Missing: any signal about range width, and pay openness per company.
- **Could build.** (a) A note when the top of a range is far above the bottom, and a "narrow ranges only" option: static plus in the
  browser, S. (b) Share of a company's postings that state pay, on its page (idea B in `COMPETITOR_GAPS.md`): static, S.

### J9. "Remote" that is not remote, or not open to where I live (9 sources)

- **How people put it.** Everything marked remote turned out not to be; many roles need on-site work; most are for US residents only
  ([FlexJobs][tp-flex-low]). US-only roles shown as remote in the UK ([Otta][tp-otta]); a remote job limited to one small country
  ([Himalayas][tp-himalayas]); roles shown that the person cannot apply to because of location ([Wellfound][tp-wellfound]). Remote
  usually means one country, becomes hybrid once a recruiter calls, and boards do not let you filter remote by country
  ([HN][hn-remote]); a hybrid role listed as remote was the first error readers found on a new aggregator ([HN][hn-swe]).
- **Said about.** FlexJobs, Otta, Himalayas, Wellfound, Welcome to the Jungle, Levels.fyi, Dice, Jobright, remote boards generally.
- **Our site today.** A "Remote" tag, a "Work from anywhere" filter and a worldwide page; the employer's location text is shown as
  written. No normalised "open to" label, no country or time-zone filter for remote roles, no hybrid flag.
- **Could build.** Parse eligibility and hybrid wording at collection time; show "Remote · US only", "Remote · Europe", "Hybrid" in
  rows; add "remote I can take from <country>"; state the accuracy on the methodology page (gap 11): static plus in the browser, M.

### J10. Email and notification spam, unsubscribe that does not work (9 sources)

- **How people put it.** Notification volume is extreme and some cannot be switched off ([Wellfound][tp-wellfound]); a new unwanted
  email every day and an unsubscribe that does not work ([Teal][tp-teal]); irrelevant emails continue after being disabled
  ([ZipRecruiter app][as-zip]); daily emails with jobs already rejected ([Indeed][tp-indeed]); emails to people who never signed up
  ([Welcome to the Jungle][tp-wttj], [Otta][tp-otta]).
- **Said about.** Wellfound, Teal, ZipRecruiter, Indeed, LinkedIn, Welcome to the Jungle, Otta.
- **Our site today.** We send nothing, so nothing to complain about, and nothing to bring people back either.
- **Could build.** When alerts launch: confirmed opt-in, a frequency choice, one-click unsubscribe in every message, only jobs that
  match the saved search, the address used for nothing else: needs email and the owner, M.

### J11. AI features that make searching worse (9 sources)

- **How people put it.** The new AI job search is called a step backwards ([LinkedIn][tp-linkedin]); AI matching suggests jobs the
  person has never done ([Indeed][tp-indeed], [ZipRecruiter][tp-zip-low]); a plain request to remove the AI ([Monster][tp-monster-low]);
  generated cover letters need heavy editing ([Teal][tp-teal]). The opposite also shows up: AI that tailors the user's own resume to a
  posting is praised ([Jobright][tp-jobright], [Huntr][tp-huntr]).
- **Said about.** LinkedIn, Indeed, ZipRecruiter, Monster, Welcome to the Jungle, Teal, Simplify; AI screening by employers on hh.ru
  ([T—Zh][tj-hh]) and Indeed ([app][as-indeed]).
- **Our site today.** No AI in search; filters are deterministic. Resume-to-posting match runs in the browser.
- **Could build.** Nothing new. Keep any future AI as a helper on the user's own documents, never as a replacement for filters.

### J12. Duplicates, reposts and agency copies (8 sources)

- **How people put it.** Many copies of one listing from the same company; mostly agencies and few direct employers
  ([Indeed][tp-indeed], [Indeed][tp-indeed-1]); recommended "jobs" that are adverts for other agencies ([Monster][tp-monster-low]);
  reposts by recruiting firms under vague names, the same roles again and again ([HN][hn-90]).
- **Said about.** Indeed, LinkedIn, Monster, FlexJobs (same jobs as on free sites), boards that accept agency postings.
- **Our site today.** Covered: one source per company (its own system), no agencies, the same role in several cities is one row, a
  repost shows its history, visited jobs are dimmed.
- **Could build.** A small "posted again" mark in list rows, not only on the job page: static, S.

### J13. Hundreds of applicants within hours: applying feels like a lottery (8 sources)

- **How people put it.** Three hundred applicants in two days, most of them machine-written ([HN][hn-450]); most jobs have 500+
  candidates ([HN][hn-remote]); 1,200 and 1,800 applications reported by hiring managers ([HN][hn-90], [HN][hn-verified]); one-tap
  applying floods employers ([Indeed app][as-indeed]). What people say works: applying early through a filter for recent postings
  ([HiringCafe][tp-hc]) and referrals ([HN][hn-remote]).
- **Said about.** LinkedIn, Indeed, remote roles everywhere, any widely seen posting.
- **Our site today.** "Posted" filter (24 hours, 3, 7, 30 days), a "New" list, saved searches and "Follow company" in the browser, RSS
  for the main list, categories and skills. No alerts of any kind.
- **Could build.** (a) "New since your last visit" counts on saved searches and followed companies: in the browser, S. (b) An RSS
  address for every company, location and saved search: static, S. (c) Browser push: needs the API, M. (d) Email alerts: see J10.

### J14. No human to reach; cannot delete the account or the data (8 sources)

- **How people put it.** Timely help is nearly impossible ([Indeed][tp-indeed]); answers are templates ([LinkedIn][tp-linkedin]);
  account deletion means writing to the founder ([HiringCafe][tp-hc]); recruiters keep making contact after deletion
  ([Dice][tp-dice]). The mirror image: most recent five-star reviews of ZipRecruiter and We Work Remotely praise a support person
  who sorted out a billing problem ([ZipRecruiter][tp-zip], [We Work Remotely][tp-wwr]).
- **Said about.** Indeed, LinkedIn, Dice, HiringCafe, ZipRecruiter, Simplify, Wellfound, Huntr.
- **Our site today.** No accounts, so nothing to delete. The only contact is a Telegram handle; no email yet; no support staff.
- **Could build.** The erase button from J7; a "how to report a mistake" block with an honest reply time: static, S, needs the owner.
  When accounts exist: self-serve delete and export: needs the API, S.

### J15. Application forms: retyping the resume, long multi-step systems (7 sources)

- **How people put it.** Re-entering the same data for every application; Workday named as the worst, to the point of skipping any
  job that uses it ([HN][hn-90], [HN][hn-450], [Truffle][truffle]). "Apply" on the board turned out not to be the application: the
  employer wanted a second one elsewhere ([Indeed][tp-indeed]). Autofill tools fill fields wrongly or leave blanks
  ([Simplify][tp-simplify]). One commenter singles out Greenhouse and Ashby forms as the light ones ([HN][hn-90], single comment).
- **Said about.** Workday and Taleo forms, Indeed, FlexJobs, Simplify, Huntr.
- **Our site today.** We send people straight to the employer's form, and our three sources are the lighter systems. The "Source" line
  names the system.
- **Could build.** Keep the system name visible and filterable once heavier systems are added as sources: static, S. Autofill
  extension: already planned, L.

### J16. Thin coverage outside the United States (7 sources)

- **How people put it.** Mostly useful to US residents; weak for Canada ([FlexJobs][tp-flex-low]); features mostly did not work for a
  European user ([Simplify][tp-simplify]); requests for India and for European pay data ([HN][hn-swe]).
- **Said about.** FlexJobs, Simplify, Jobright, Monster (Canada), Welcome to the Jungle (other EU markets), CryptoJobsList (Asia).
- **Our site today.** 58 location pages, visa pages, several currencies; the company list is US-heavy.
- **Could build.** J9's eligibility labels; sources common in Europe (Recruitee, Teamtailor, Personio): static pipeline, M to L.

### J17. Requirements that do not match the label (6 sources)

- **How people put it.** Descriptions are inaccurate or padded; senior skills asked at junior pay ([HN][hn-90], [HN][hn-ban]);
  unrealistic requirements are 3.2% of r/recruitinghell posts ([Truffle][truffle]); a wish for roles without daunting expectations
  ([HN][hn-swe]).
- **Said about.** Postings in general rather than a particular board; Indeed ([app][as-indeed]).
- **Our site today.** Level tags and an entry-level page; no check of what the posting actually asks.
- **Could build.** Years-of-experience parser, a filter by years, and a flag when a junior or intern posting asks for 3+ years (idea F):
  static, M.

### J18. Reviews that cannot be trusted; wish for facts about how employers behave (5 sources)

- **How people put it.** Negative reviews are removed or blocked, and you must contribute to read ([Glassdoor][tp-glassdoor]); a
  factual review was rejected ([Indeed][tp-indeed-1]). Wishes: rate employers on whether they answer ([Hirify][pr]); profile how an
  employer posts ([HN][hn-ban]); show hires and response times measured by a third party ([HN][hn-verified]).
- **Said about.** Glassdoor, Indeed company reviews; the wish for an employer rating was voiced about hh.ru on the Hirify thread.
- **Our site today.** No reviews, by decision. Company pages show hiring numbers.
- **Could build.** The facts card from J1 (c); later the response signal from J2 (b).

---

## 4. Employers' and recruiters' pains, most frequent first

Employer evidence is thinner than job-seeker evidence: G2, Capterra and TrustRadius were blocked, and r/recruiting was not readable.

### E1. Unpredictable cost and surprise charges (6 sources, about 25 reviews)

- **How people put it.** Hundreds of dollars for a posting that ran two days; a "free trial" that billed anyway; daily budgets that
  now run out faster; a charge for a sponsored posting that was flagged and brought nothing ([Indeed][tp-indeed]). Charged after
  closing a posting; a plan they did not knowingly accept; access cut unless an extra monthly fee is paid ([ZipRecruiter][tp-zip-low],
  [ZipRecruiter][sc-zip]). Three days billed for a one-day promotion ([LinkedIn][tp-linkedin]). An expected $100 that became a $1,000
  bill under pay-per-application ([SHRM][shrm]). Rising cost for less return ([Recruiting Headlines][rh]).
- **Said about.** Indeed, ZipRecruiter, LinkedIn job promotion.
- **Our side today.** Public fixed prices and one-time crypto checkout are written but not deployed; no card is ever stored, so
  nothing can renew or overrun.
- **Could build.** On the order page and receipt: exactly what is bought, start and end dates, "does not renew": needs the API, S.

### E2. Hard to cancel, auto-renewal, contracts, refunds refused (6 sources, about 18 reviews)

- **How people put it.** Twelve-month contracts that renew by themselves and collection threats after a cancel request
  ([Dice][tp-dice]); cancelling means phoning support; refund given only as account credit ([ZipRecruiter][tp-zip-low]); no cancel
  button for a subscription ([Welcome to the Jungle][tp-wttj]).
- **Said about.** Dice, ZipRecruiter, Welcome to the Jungle, Indeed.
- **Our side today.** No subscriptions exist. Refund terms are not written yet (queued in `ROADMAP.md`).
- **Could build.** A short written refund rule shown before payment: static, S, needs the owner.

### E3. Paying and getting unqualified or no applicants (5 sources, about 15 reviews)

- **How people put it.** Two paid adverts and nobody who met the requirements; tradespeople answering an advert for chefs; over $500
  for one qualified candidate for a technical role ([Indeed][tp-indeed]). $2,000 for thirteen mostly unqualified applicants
  ([ZipRecruiter][tp-zip-low]).
- **Said about.** Indeed, ZipRecruiter.
- **Our side today.** We do not handle applicants and promise no results.
- **Could build.** Cookie-free counts of clicks on "Apply" per paid placement, visible in the employer account; no multiplier claims;
  optionally a credit if a placement gets under a stated number of clicks: needs the API, M, the credit rule needs the owner.

### E4. No human support; postings or accounts blocked without a reason (6 sources, about 11 reviews)

- **How people put it.** Sponsored jobs went dead with no warning and no route to appeal; a business number rejected with no way to
  prove ownership ([Indeed][tp-indeed-1], [Indeed][tp-indeed]). An account suspended without explanation after fake applicants flooded
  the postings ([Wellfound][tp-wellfound]). A chatbot, slow replies, no weekend cover ([Otta][tp-otta]).
- **Said about.** Indeed, Wellfound, Otta, ZipRecruiter, LinkedIn.
- **Our side today.** A real risk for us too: everything is automatic and there is no support staff.
- **Could build.** Every automatic refusal states the exact reason and how to fix it; a status line per posting in the account;
  a published reply time for the fallback contact: needs the API, S, plus the owner.

### E5. Floods of low-effort, machine-written or fake applications (6 sources)

- **How people put it.** Over a thousand applications in days; resumes that all look alike; stand-ins for coding tests and invented
  identities ([HN][hn-90], [HN][hn-verified], [HN][hn-ban], [HN][hn-450]). A recruiter in one thread blames one-tap applying
  ([HN][hn-450]); an employer reports fraudulent applicants flooding postings ([Wellfound][tp-wellfound]).
- **Said about.** LinkedIn and any board with one-tap apply, remote roles, Wellfound.
- **Our side today.** We have no one-tap apply; candidates go through the employer's own form and screening questions.
- **Could build.** Say this plainly on the employer page as a reason to list with us; never add mass-apply: static, S.

### E6. Paid advert hidden or tool not working (3 sources)

- **How people put it.** An advert hidden over a formatting detail; a paid advert not found in search ([Recruiting Headlines][rh]); a
  paid recruiter tool taking minutes to load ([LinkedIn][tp-linkedin]).
- **Said about.** Indeed, LinkedIn Recruiter.
- **Our side today.** Placements are applied by the build, so a paid one cannot be silently dropped; the buyer has no way to see that yet.
- **Could build.** A "see your placement live" link and the dates it ran, in the account: needs the API, S.

### E7. Wrong audience for the role or region (3 sources, single reviews)

- **How people put it.** Applicants mostly from the US and Europe when hiring in Asia ([CryptoJobsList][tp-cjl]); few local
  candidates ([ZipRecruiter][tp-zip-low]).
- **Our side today.** No audience numbers yet (the media kit says so).
- **Could build.** Publish real visitor geography once cookie-free analytics exist: static, S, after the domain.

### E8. Wanting a cheap or free posting that simply works (3 sources)

- **How people put it.** A free posting that drew 80 applicants in two days and a hire ([Indeed][tp-indeed-5]); a recruiter happy to
  post for free on Hirify ([Hirify][pr]); HR people listing flat-fee and free alternatives ([Recruiting Headlines][rh]).
- **Said about.** Indeed (praise), Hirify (praise), Indeed's paid model (complaint).
- **Our side today.** Free posting with an automatic link check is written, not deployed.
- **Could build.** Nothing new: deploy what is written (owner's Cloudflare step), with the intake rules from J3 (b).

### E9. Being called a ghost employer for a legitimate long-open role (2 sources)

- **How people put it.** Large teams always have openings for backfill; a long-open posting is not proof of bad faith ([HN][hn-90],
  [HN][hn-ban]).
- **Our side today.** We flag every role at 90 days with the same warning.
- **Could build.** Use the "Talent pool" label from J1 (b) when the posting says so, and keep the warning wording neutral: static, S.

### E10. Review sites that cannot be answered or are gamed (1 source)

- **How people put it.** Reviews posted by people who never worked there, with no way to close the profile ([Glassdoor][tp-glassdoor]).
- **Said about.** Glassdoor.
- **Our side today.** No reviews. A facts card built from the employer's own postings avoids this problem.
- **Could build.** With the facts card (section 6, item 7): show how each number is computed, so an employer can check it: static, S.

---

## 5. What users praise and would miss

| What | Where it is praised | Our status |
|---|---|---|
| Filters that really narrow, including exclusions | [Hirify][pr], [HiringCafe][tp-hc], [Wellfound][tp-wellfound] | Have filters; exclusions missing. Adopt |
| One place instead of many sources | [Hirify][pr] | Have, for 540 companies |
| A visible source and a direct link to the original posting | [Hirify][pr] | Have. Keep |
| Jobs that are not on the big boards, not seen many times already | [HiringCafe][tp-hc], [Otta][tp-otta], [Wellfound][tp-wellfound] | Have in part (employer systems directly) |
| A "recent postings" filter; fresh listings | [HiringCafe][tp-hc], [Otta][tp-otta] | Have. Keep prominent |
| Clean page with no clutter and no adverts | [Hirify][pr], [Otta][tp-otta], [Teal][tp-teal] | Have. Keep paid placements labelled and apart |
| Pay and equity shown | [Wellfound][tp-wellfound], [HN][hn-salary] | Have where published |
| A tracker that replaces the spreadsheet: stages, notes, contacts, follow-up reminders | [Teal][tp-teal], [Huntr][tp-huntr], [Simplify][tp-simplify], [Otta][tp-otta] | Have stages, notes, CSV. Reminders and contacts missing. Adopt |
| Resume-to-posting keyword match and tailoring | [Teal][tp-teal], [Huntr][tp-huntr], [Jobright][tp-jobright], [Monster][tp-monster] | Have the match tool in the browser |
| Autofill of application forms | [Jobright][tp-jobright]; mixed on [Simplify][tp-simplify] | Planned as an extension |
| Instant alerts in a messenger or by email | [Hirify][pr], [Indeed][tp-indeed-5], [LinkedIn][sc-linkedin] | Missing |
| Direct contact with the hiring side | [Hirify][pr], [Hired][tp-hired], [Wellfound][tp-wellfound] | Not possible for collected jobs; possible for employer-posted ones |
| Being told when an application was viewed | [CryptoJobsList][tp-cjl], [ZipRecruiter app][as-zip] | Not possible for us; do not imitate |
| A free tier that is not capped | [Teal][tp-teal], [Jobright][tp-jobright] | Have |
| Companies approaching candidates | [Hired][tp-hired] | Resume database is queued; opt-in only |
| Rich company information | [Otta][tp-otta], [Welcome to the Jungle][tp-wttj] | Have hiring facts; little else |
| A human who answers fast and refunds without a fight | [ZipRecruiter][tp-zip], [We Work Remotely][tp-wwr], [FlexJobs][tp-flex] | Cannot staff this; the substitute is nothing to refund and clear automatic messages |
| A founder who answers and fixes within days | [Hirify][pr] | Owner's choice; a public changelog would be the low-effort form |
| Free posting for employers | [Hirify][pr], [Indeed][tp-indeed-5] | Written, not deployed |

---

## 6. The 15 most valuable things to build or change

Ranked by how often the pain appears and how cheaply we can answer it. Items 1 to 11 need no server and no moderator.

| # | What | Answers | How | Effort |
|---|---|---|---|---|
| 1 | Exclusion filters and "hide this company": company, title word, level, applied everywhere and remembered | J4, J12 | In the browser | S |
| 2 | Long-open and repost controls: "hide roles open 90+ days", an age band, a "Talent pool" label taken from the posting's own words, a "posted again" mark in rows | J1, J12, E9 | Static plus in the browser | S |
| 3 | Remote eligibility: "Remote · US only / Europe / worldwide", "Hybrid", and "remote I can take from <country>" | J9, J16 | Static plus in the browser | M |
| 4 | Safety page and a crypto hiring checklist, linked from every job, stating how listings get here and what we never ask for | J3 | Static | S |
| 5 | Tracker upgrades: days since applied, follow-up nudge and template, mark when the employer closed the role, sorting, save and restore to a file, erase everything | J2, J6, J7, J14, Hirify requests | In the browser | S to M |
| 6 | New jobs first, without email: "new since your last visit" on saved searches and followed companies; an RSS address for every company, location and saved search | J13 | Static plus in the browser | S |
| 7 | Company hiring-facts card: median days to close, share open 90+ days, reposts, share of postings with pay | J1, J8, J18, E10 | Static | M |
| 8 | Pay honesty: a note on very wide ranges and a "narrow ranges only" option | J8 | Static plus in the browser | S |
| 9 | Regression checklist before every push: back and scroll, count equals rows, filter resets paging, phone speed | J6 | In the browser | S |
| 10 | A dated "what is free and what we will never do" page: no sign-up to search or apply, no phone, no selling of data, one-time payments, nothing renews; and keep job visibility ungated | J5, J7, J10 | Static; owner decision on Plus early access | S |
| 11 | Entry-level honesty: years-of-experience parser, filter by years, flag on junior postings that ask for 3+ years | J17 | Static | M |
| 12 | "Report a problem" that triggers an automatic re-check of the source | J1, J3, E4 | Needs the API | S |
| 13 | Employer trust pack: exact dates and "does not renew" at checkout, written refund rule, "see it live" link, apply-click counts, reasons on every automatic refusal | E1, E2, E3, E4, E6 | Needs the API and the owner | M |
| 14 | Email alerts with manners: confirmed opt-in, frequency choice, one-click unsubscribe, matches only; a free weekly digest | J13, J10 | Needs email and the owner | M |
| 15 | Anonymous "heard back / no reply" signal from the tracker, shown per company above a minimum sample | J2, J18 | Needs the API; open to abuse with no moderator, so rate limits and a high threshold first | M to L |

### Flags: patterns users of other sites put up with that we should not copy

| Pattern | Seen in | Why not |
|---|---|---|
| Paid early access to jobs that are public on the employer's site (our planned "48 hours earlier" in Plus) | Our `ROADMAP.md`; the complaint pattern is in J5 | It delays public information for non-payers and sits badly with our own home-page promise about not applying to jobs that are already gone. Sell alerts, sync and tools instead. Owner's call |
| Trial that becomes a long commitment; renewal switched on by default; discount shown only at cancellation | [We Work Remotely][tp-wwr], [FlexJobs][tp-flex-low], [LinkedIn][tp-linkedin], [Dice][tp-dice] | The largest single source of one-star reviews on those pages |
| Paying to see or apply to jobs that are free elsewhere | [FlexJobs][tp-flex-low], [Remotive][tp-remotive] | The job is not ours to sell |
| Payment or a phone number asked during sign-up, with a small skip link | [Himalayas][tp-himalayas], [Glassdoor][tp-glassdoor] | Read by users as data collection |
| "Contribute to read" walls | [Glassdoor][tp-glassdoor], [Indeed][tp-indeed-1] | Forces low-quality content and blocks reading |
| "Your application was viewed" and applicant counters we cannot actually measure | Praised on [CryptoJobsList][tp-cjl] | We never see the application; any such number would be invented |
| One-tap or mass apply | [Indeed app][as-indeed], [HN][hn-450] | Feeds the flood both sides complain about |
| Alerts that cannot be switched off; email to people who did not sign up | [Wellfound][tp-wellfound], [Teal][tp-teal], [Otta][tp-otta] | Spam |
| Sponsored or promoted rows that are stale or look like ordinary jobs | [HN][hn-hc] | Paid placements must be labelled and still pass the daily check |
| Asking only happy users for reviews, or pushing every user to review | [FlexJobs][tp-flex] (one reviewer objects to being asked) | Inflated ratings; conflicts with "nothing fake" |
| Publishing a user's support messages as testimonials | [Simplify][tp-simplify] (single review) | Consent |

---

## 7. What I could not verify

- **Reddit was not read at all.** The site refuses this tool for search and for page loads. All Reddit-based statements come from
  two second-hand pages (rows 48 and 49) and search summaries. The Truffle figures are keyword counts by a vendor and cover posts,
  not comments.
- **G2, Capterra, TrustRadius, Software Advice** returned 403. Employer-side statements about LinkedIn Recruiter (cost, message reply
  rates) and ZipRecruiter on Capterra (irrelevant emails, cancelling by phone) are search summaries only and are not used in section 4
  as evidence. Nothing was found for Wellfound or Workable as employer tools.
- **Russian review sites.** otzovik.com and irecommend.ru failed to load. For hh.ru I read a bank's review catalogue, two T—Zh
  threads and a news item; for Habr Career I found no user reviews, only a search summary saying its product manager acknowledges
  complaints about silence after test tasks.
- **Hirify outside Product Radar.** One Habr thread and the founder's interview. No Telegram discussion was readable, no review of
  Plus was found, and the revenue and audience numbers in the interview are the founder's own.
- **Google Play and Product Hunt review pages** returned nothing; the Remote OK Trustpilot profile has been removed.
- **Depth.** Only the newest page of each Trustpilot profile was read (20 to 24 of up to 26,000 reviews). Profiles where the company
  invites reviews (FlexJobs, Jobright, Monster) skew positive; unclaimed ones (Indeed, LinkedIn, Glassdoor, Dice) skew negative.
  Scores are not comparable across sites.
- **Reading method.** Except for Product Radar, I read digests produced by the fetch tool, not raw pages. Individual wordings, dates
  and reviewer roles may contain extraction errors. Hacker News threads were read as theme digests and three were cut off before the
  end.
- **Single-source claims** are marked in the text: the web3.career review, the 52.3% and 45.3% figures for Russia, the remark about
  Greenhouse and Ashby forms, the Simplify testimonial complaint. The report behind the Hacker News thread on postings open over 90
  days (row 39) was not opened.
- **Our own site.** Judged from the code and the home page, not by using it. Not checked: back-button and scroll behaviour, count
  accuracy, phone speed, whether saved jobs show that the employer closed the role, whether tracker data can be restored from a file,
  how the location text looks for remote roles in list rows.

[pr]: https://productradar.ru/product/hirify/
[pr-user]: https://productradar.ru/user/igoralentyev/
[habr-hh]: https://habr.com/en/articles/1010852/comments
[tproger]: https://tproger.ru/articles/uvolili--otlichno--kak-razrabotchik-zapustil-konkurenta-hh-ru---hirify-me-i-nachal-zarabatyvat
[tp-indeed]: https://www.trustpilot.com/review/www.indeed.com
[tp-indeed-1]: https://www.trustpilot.com/review/www.indeed.com?stars=1&page=2
[tp-indeed-5]: https://www.trustpilot.com/review/www.indeed.com?stars=5
[tp-zip]: https://www.trustpilot.com/review/www.ziprecruiter.com
[tp-zip-low]: https://www.trustpilot.com/review/www.ziprecruiter.com?stars=1&stars=2
[tp-flex]: https://www.trustpilot.com/review/www.flexjobs.com
[tp-flex-low]: https://www.trustpilot.com/review/www.flexjobs.com?stars=1&stars=2
[tp-linkedin]: https://www.trustpilot.com/review/www.linkedin.com
[tp-glassdoor]: https://www.trustpilot.com/review/www.glassdoor.com
[tp-monster]: https://www.trustpilot.com/review/www.monster.com
[tp-monster-low]: https://www.trustpilot.com/review/www.monster.com?stars=1&stars=2
[tp-dice]: https://www.trustpilot.com/review/www.dice.com
[tp-wellfound]: https://www.trustpilot.com/review/wellfound.com
[tp-wwr]: https://www.trustpilot.com/review/weworkremotely.com
[tp-remoteok]: https://www.trustpilot.com/review/remoteok.com
[tp-remotive]: https://www.trustpilot.com/review/remotive.com
[tp-himalayas]: https://www.trustpilot.com/review/himalayas.app
[tp-jobright]: https://www.trustpilot.com/review/jobright.ai
[tp-teal]: https://www.trustpilot.com/review/tealhq.com
[tp-simplify]: https://www.trustpilot.com/review/simplify.jobs
[tp-huntr]: https://www.trustpilot.com/review/huntr.co
[tp-web3]: https://www.trustpilot.com/review/web3.career
[tp-cjl]: https://www.trustpilot.com/review/cryptojobslist.com
[tp-hired]: https://www.trustpilot.com/review/hired.com
[tp-otta]: https://www.trustpilot.com/review/otta.com
[tp-wttj]: https://www.trustpilot.com/review/welcometothejungle.com
[tp-hc]: https://www.trustpilot.com/review/hiring.cafe
[tp-hh]: https://www.trustpilot.com/review/hh.ru
[sc-zip]: https://www.smartcustomer.com/reviews/ziprecruiter.com
[sc-linkedin]: https://www.smartcustomer.com/reviews/linkedin.com
[sc-dice]: https://www.smartcustomer.com/reviews/dice.com
[as-indeed]: https://apps.apple.com/us/app/indeed-job-search/id309735670?see-all=reviews
[as-zip]: https://apps.apple.com/us/app/ziprecruiter-job-search/id541933937?see-all=reviews
[as-linkedin]: https://apps.apple.com/us/app/linkedin-network-job-finder/id288429040?see-all=reviews
[tbank]: https://www.tbank.ru/reviews/company/headhunter/12105
[tj-hh]: https://t-j.ru/hr-ne-otvechaet-i-na-hh-otkazy/
[tj-drop]: https://t-j.ru/hh-auto-drop/
[mailru]: https://finance.mail.ru/article/rossiyane-massovo-zhaluyutsya-na-prizrachnyie-i-mertvyie-vakansii-69212623/
[habr-career]: https://habr.com/ru/articles/815549
[hn-90]: https://news.ycombinator.com/item?id=49818698
[hn-ban]: https://news.ycombinator.com/item?id=45028785
[hn-ghost]: https://news.ycombinator.com/item?id=42136469
[hn-salary]: https://news.ycombinator.com/item?id=32181619
[hn-swe]: https://news.ycombinator.com/item?id=44025484
[hn-remote]: https://news.ycombinator.com/item?id=43629732
[hn-hc]: https://news.ycombinator.com/item?id=42803304
[hn-verified]: https://news.ycombinator.com/item?id=47291699
[hn-450]: https://news.ycombinator.com/item?id=45073589
[truffle]: https://hiretruffle.com/reports/recruiting-complaints-2026
[gummy]: https://gummysearch.com/tools/best-products/job-boards/
[ph]: https://www.producthunt.com/p/resumeup-ai/what-s-the-most-frustrating-part-of-the-modern-job-application-process
[rh]: https://recruitingheadlines.com/?p=650784
[shrm]: https://www.shrm.org/topics-tools/news/talent-acquisition/indeed-pauses-required-pay-results-pricing-for-now
[ct]: https://cointelegraph.com/magazine/fake-crypto-job-interview-malware
