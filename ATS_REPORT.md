# More hiring systems and the rest of the candidate list: report

Run of 15 November 2026 (the owner: "too few jobs, competitors add far more"). Before it the collector read 3,776 company boards on
Greenhouse, Lever and Ashby (about 130,500 open jobs at the time of their check). After it: 6,609 boards on eight systems.

## Result

| Hiring system | Boards before | Boards after | Open jobs on the added boards (at the check) |
|---|---|---|---|
| Greenhouse | 1,716 | 2,210 | 26,400 |
| Ashby | 1,997 | 2,108 | 8,518 |
| Lever | 63 | 66 | 4,718 |
| Workday | 0 | 986 | 257,696 (at most 1,000 counted per board) |
| Workable | 0 | 944 | 42,321 |
| Personio | 0 | 163 | 1,465 |
| Recruitee | 0 | 78 | 1,392 |
| Teamtailor | 0 | 54 | 1,095 |
| SmartRecruiters | 0 | 0 | (see below) |
| **Total** | **3,776** | **6,609** | **343,605** |

"Open jobs" is what each board's feed listed when it was checked, before the collector's own filters. On the newer systems only
jobs in English are counted (and collected). On Workday a board is counted up to 1,000 jobs, the most the collector reads per board.

## Read now, and on hold

**Update, 18 Nov 2026 (the owner: "почему так мало? можешь собирать больше и не тратить кредиты Claude?").** Where the record stood:
228,337 open jobs from about 6,540 boards on eight hiring systems (Greenhouse, Ashby, Lever, Workable, Workday, Personio, Recruitee,
Teamtailor). Why it grew so slowly after the release of 17 Nov: a released Workday board got 40 texts on each of its reads, its turn
came once in eight hourly runs, and GitHub starts only a few of those a day, so a board of 1,000 jobs needed weeks; the record grew by
about 7,000 jobs in a day instead of the 18,000 planned. Changed that day: 120 texts a read (`DETAILS`); a board released in the last
ten days is read on every run (`FILL_SINCE`); postings the record has never held are read before known ones (`details_from`); and the
60 largest boards still on hold were released (59,937 jobs at the check, `"lifted": "2026-11-18"`): TD Bank, U.S. Bank, HPE, Booz Allen
Hamilton, CarMax, JLL, Maersk, Takeda, Hitachi, UPS, Levi Strauss, Abercrombie & Fitch, J.Crew, Papa John's, Wendy's, Dutch Bros and
others; sixteen got their plain names. 194 boards (83,796 jobs) are still on hold, to be released in parts while the server's memory
is watched (7.9 GB, no swap; the collector there held 1.6 GB, the page service 0.45 GB). None of this uses Claude: the collector is
plain Python that runs on GitHub's machines every hour and on our own server all the time. What can still add jobs, in order of size:
the rest of the hold; more than 1,000 jobs a board on Workday (`LIST_MAX`); new hiring systems (SmartRecruiters is already in the
code and has no boards yet; Oracle, SuccessFactors, iCIMS, BambooHR, UKG, Paylocity and others each need a reader); more boards on the
systems already read (the candidate list is used up: 25 boards left).

**Update, 17 Nov 2026:** 74 of the boards on hold were released: the companies that are in a well-known list (S&P 500, Nasdaq-100,
unicorns, Y Combinator; `company_lists.json`), 48,636 jobs at the check: NVIDIA, Cisco, Intel, Boeing, Pfizer, Visa, Bank of America,
Morgan Stanley, Johnson & Johnson, Adobe and others. They carry `"lifted": "2026-11-17"` in `sources_ats.json`. Their jobs come in
gradually (40 texts a board on each hourly read, 5 a board on each pass of `live.py`), so the record grows by about 18,000 jobs a day
for three days. Nine of them got their plain names instead of a legal entity's (Jabil, AT&T, Motorola Solutions, Humana, General Mills,
The Hartford, Deckers Brands, Northern Trust, The Coca-Cola Company). 254 boards (143,733 jobs) are still on hold. What made room:
the build matches titles to roles about twenty times faster and reads descriptions three times faster (ROADMAP.md, section 122),
and every build now prints its slowest stages.


All 6,609 boards are in the sources files, but 328 large Workday boards (192,369 jobs) carry `"hold": true` and are not read yet:

| | Boards | Open jobs at the check |
|---|---|---|
| Read now, added on 15 Nov | 2,505 | 151,236 |
| of them Workday | 658 | 65,327 |
| On hold (Workday, over 200 jobs each) | 328 | 192,369 |

Why: the hourly build in GitHub Actions takes about 3.8 ms per job record (8.5 minutes for 133,197 records on 15 Nov). With every
Workday board the record would grow to about 470,000 open jobs and the build alone to about 30 minutes, which with collecting
and uploading leaves no room inside the 45-minute limit. With the boards on hold the record grows to about 280,000 open jobs, the
build to about 18 to 22 minutes and the whole run to about 30 to 35 minutes (an estimate from these measurements, to be confirmed on the first
runs after the merge; the step of the build that sorts jobs into roles now tests each distinct title once). Every Workday
board with 200 jobs or fewer is read, and so are the large shift-work employers the owner asked for (Walmart, Target, CVS Health, The
Home Depot, Lowe's, TJX, Nordstrom, Meijer, Hy-Vee, Petco, BJ's Wholesale Club, DICK'S Sporting Goods, Sysco, J.B. Hunt, McKesson,
Cardinal Health, Labcorp, DaVita, Banner Health, Sutter Health, Geisinger, Ochsner Health, First Student, Republic Services,
United Rentals). To read more, remove `"hold": true` from boards in `sources_ats.json`; the build should first move off GitHub
Actions (to our server, where there is no 45-minute limit) or become incremental.

## The rest of `sources_candidates.json` (Greenhouse, Lever, Ashby)

633 of the 3,852 checked boards were in no sources file: on 14 Nov they had been left out as agencies or as mostly store, warehouse or
clinic jobs. All 633 were checked again on 15 Nov and all answered with jobs (40,434). 608 were added to `sources_more.json`
(entries with `"added": "2026-11-15"`, 39,636 jobs): 25 were left out as a company already read under another board (BetterHelp,
Klaviyo, Etched, Lovable, Kalshi, Miro, Deliveroo, Consensys and 16 more), and one as a second board of the same company
(`bluestone-provider`). Three that only shared a name with a company we read were added under their full name (Forward Networks,
Parallel Learning, MERGE World). Among them are large boards with many copies of one job in many places (BoxLunch 4,662, BJAK
3,156, Private Equity Insights 1,284 with volunteer roles and one posting per language); they are in as the task asked.

## Large US employers (27 Nov 2026)

The critics (backlog/critique, 26 Nov) found "nurse, Dallas" at 225 jobs here against 7,393 on HiringCafe, none of them from Baylor
Scott & White, Texas Health Resources, Parkland, UT Southwestern, Methodist, Medical City (HCA) or Children's Health. Each employer's
own careers site was opened to see which hiring system it reads, and each board was read once with the collector's own code
(`collect.fetch`: the list with 120 postings' texts, twice, and the list alone once). Added: 16 boards, 22,952 open jobs at the check.

| Employer | System | Open jobs | Read |
|---|---|---|---|
| Baylor Scott & White Health | Phenom (Taleo behind it) | 2,382 | lifted: every run until filled |
| Children's Health (Dallas) | Phenom (Infor behind it) | 202 | lifted |
| Methodist Health System (Dallas) | Workday | 750 | lifted |
| Parkland Health (Dallas) | Workday, places are buildings: `"where": "Dallas, TX"` | 237 | lifted |
| Texas Instruments (Dallas) | Oracle | 922 | lifted |
| Tenet Healthcare (Dallas) | Oracle | 2,453 | lifted |
| Advocate Health (Atrium, Advocate, Aurora) | Workday (its total stops at 2,000) | 2,000 | every 8 hours |
| Intermountain Health | Workday | 1,511 | every 8 hours |
| Cleveland Clinic | Workday | 2,318 | every 8 hours |
| Providence | Oracle | 2,101 | every 8 hours |
| Mayo Clinic | Oracle | 1,466 | every 8 hours |
| Northwell Health | Oracle | 1,130 | every 8 hours |
| Wells Fargo | Workday | 1,545 | every 8 hours |
| Capital One | Workday | 2,050 | every 8 hours |
| Truist | Workday | 1,313 | every 8 hours |
| Comcast | Workday | 572 | every 8 hours |

A read of the list alone (nothing new) took 3 to 141 seconds a board from a laptop outside the US (Phenom 3 and 8, Oracle 16 to 48,
Workday 12 to 141); a read with 120 texts 122 to 436 seconds. All are on the slow rotation (`SLOW_ATS`); the six Dallas boards carry
`"lifted"` so that they fill in days. On hold (`"hold": true`, with the reason): JPMorgan Chase (Oracle, 6,778 jobs; its firewall
answers robots.txt with "Blocked by WAF4SaaS") and Dollar General (Oracle, 91,239 store postings of a few store jobs).

Not added, and why: Texas Health Resources, Ascension, Kroger and Atrium's old site (their careers hosts did not resolve in DNS that day,
also from Google's resolver); HCA Healthcare / Medical City, Houston Methodist, Verizon, American Airlines and Albertsons (403 to our user
agent: a bot check; Wells Fargo's careers site too, but its Workday board answers and is read); Parkland and JPS answered nothing from outside the US (Parkland's Workday board is read);
Citi and Southwest Airlines (their Workday robots.txt asks crawlers to stay out); UT Southwestern and Kaiser Permanente (Taleo, which
the collector does not read); Walgreens (BrassRing), Starbucks (Eightfold); Amazon (amazon.jobs answers "10,000" for any search, 830 KB a
hundred: it needs its own reader and a decision on the load); Costco and FedEx's US jobs (no public feed found).

## Newer systems: how boards were found and checked

`discover_ats.py` took every board address in Common Crawl's URL index for `apply.workable.com/*`, `*.recruitee.com`,
`*.teamtailor.com`, `*.jobs.personio.de`, `*.jobs.personio.com` and `*.myworkdayjobs.com` in four crawls (CC-MAIN-2026-43, -39, -34,
-30: 123,727 addresses), plus a short list of large retail, logistics and healthcare employers on Workday, and read each board once
through the collector's own code (`collect.fetch_feed`).

| Hiring system | Boards found | Checked | Kept | Fewer than 3 English jobs | Mostly not English | No answer / not a board | robots.txt says no | Duplicate or agency |
|---|---|---|---|---|---|---|---|---|
| Workable | 2,398 | 2,398 | 944 | 1,035 | 14 | 376 | 0 | 29 |
| Personio | 1,970 | 1,970 | 163 | 1,202 | 40 | 550 | 0 | 15 |
| Workday | 1,863 | 1,874 | 986 | 215 | 73 | 184 | 72 | 344 |
| Recruitee | 309 | 309 | 78 | 189 | 13 | 27 | 0 | 2 |
| Teamtailor | 220 | 220 | 54 | 138 | 7 | 18 | 0 | 3 |
| **Total** | **6,760** | **6,771** | **2,225** | **2,779** | **147** | **1,155** | **72** | **393** |

Rules for a board to be kept:
- the feed answers and has 3 or more open jobs in English, and either 15 or more of them or at least 60% of all its jobs (on Workday:
  2 of the first 3 postings read);
- not a company already read under another system or name, and one board per company (the largest); Workday tenants often have
  several sites, which is most of the 344;
- not a recruitment agency or job marketplace (as on 14 Nov): 26 were taken out, among them Kreyco (4,640 postings of 69 titles),
  Huzzle, Clients Blackbox, CXG (mystery-shopper gigs), Hire Resolve and Commonwealth Medical Services;
- on Workday, the tenant's robots.txt lets crawlers read the careers site.

Large shift-work employers now read (Workday): Walmart, Target, CVS Health, The Home Depot, Lowe's, TJX, Nordstrom, Meijer, Hy-Vee,
Petco, BJ's Wholesale Club, DICK'S Sporting Goods, Sysco, J.B. Hunt, McKesson, Cardinal Health, Labcorp, DaVita, Banner Health,
Sutter Health, Geisinger, Ochsner Health, First Student, Republic Services, United Rentals. Not found under the guessed addresses:
Kohl's, Best Buy, Chewy, Kaiser Permanente, Providence, Dollar Tree, Ross, AutoZone, Aramark; US Foods and Mars ask crawlers to stay out.

## SmartRecruiters: not added

The fetcher is written (`collect.fetch_feed`, the public Posting API), but `api.smartrecruiters.com/robots.txt` allows only
LinkedIn's crawler and disallows everyone else. No SmartRecruiters board was searched for or added. To read it, ask SmartRecruiters
(or a company using it) for consent, then add boards to `sources_ats.json` as `{"ats": "smartrecruiters", "token": "<company id>"}`.

## How the systems are read

| System | Request | Text of the job | Notes |
|---|---|---|---|
| Workable | `apply.workable.com/api/v1/widget/accounts/<token>?details=true` | in the same answer | the careers widget's feed: one request a board instead of the v3 list plus one per job |
| Recruitee | `<token>.recruitee.com/api/offers/` | in the same answer | salary, remote and hybrid flags, publishing time |
| Teamtailor | `<token>.teamtailor.com/jobs.rss` | in the same answer | remote status, department, places |
| Personio | `<token>.jobs.personio.de/xml?language=en` | in the same answer | a job without an English version has no text there and is left out |
| Workday | POST `/wday/cxs/<tenant>/<site>/jobs`, 20 a request | one request per new posting | newest 1,000 per board; at most 40 texts per board per read |
| SmartRecruiters | `api.smartrecruiters.com/v1/companies/<id>/postings` | one request per new posting | not used, see above |
| Phenom (27 Nov 2026) | the careers site's sitemap (`/sitemap_index.xml` or `/sitemap.xml`) | the posting's own page (`phApp.ddo`), one request per new posting | careers sites on the employer's domain; its JobPosting `datePosted` is the day of the request, so the page's own date is used |
| Oracle Recruiting Cloud (27 Nov 2026) | `/hcmRestApi/resources/latest/recruitingCEJobRequisitions`, 200 a request | `recruitingCEJobRequisitionDetails`, one request per new posting | the REST resources the Oracle careers site itself reads; no sign-in |

Politeness: the user agent `Mozilla/5.0 (job-board aggregator)`, at most 4 to 12 boards of one system at a time and a pause between
requests (0.1 to 0.3 seconds, per tenant on Workday), no login, no bot check bypassed. The checks made roughly 20,000 requests over
about three hours (Workday about 6 per board, the others 1 or 2); a board whose feed failed is counted as "no answer".

## Test collection (on a laptop, 15 Nov 2026)

Started from a copy of the record with 41,187 open jobs at 732 companies (it predates `sources_more.json`), with the default
rotation (a quarter of the rotating boards an hour, an eighth of the Workday boards):

| Run | Boards read | Postings parsed | Time | Open jobs after |
|---|---|---|---|---|
| 1 (no fingerprints yet, all Workday boards) | 2,133 | 103,961 | 17.5 min | 96,701 |
| 2 (same hour, right after) | 2,127 | 8,512 | 9.5 min (mostly Workday's 40 texts per board) | 97,569 |
| 3 (next rotation share, large Workday boards on hold) | 2,079 | 94,703 | 19.8 min | 139,245 at 3,388 companies |

Open jobs after run 3 by system: Greenhouse 70,990, Ashby 35,436, Workable 15,877, Lever 8,046, Workday 6,673, Personio 869,
Recruitee 792, Teamtailor 562. The laptop was shared with other work (load average about 25 on 8 cores), so the times are upper
bounds; the second run shows what an hour costs once postings carry fingerprints. Then `HRN_RECORDS=both python3 build.py`
(147,186 job pages), `records_test.py` and `check.py` passed.

## Working files

Outside the project (session scratchpad, may not survive): the Common Crawl index pages, the log of every board checked and why it
was or was not kept, and the cache of Workday names.
