# More company job boards: candidates report

Run of 13 November 2026. The list is in `sources_candidates.json` (3,852 boards, sorted by open jobs). Nothing else in the project was changed.

## Result

- New tokens found (not in the three sources files): **5,874**
- Checked against the public API: **5,490**
- Verified (API answered and the board has 3 or more open jobs): **3,852**
- Open jobs on the verified boards at the time of the check: **134,467**
- The three sources files hold 741 entries, which are 557 different boards (some companies are in two files). Tokens were compared with those without regard to letter case.

| Hiring system | New tokens | Checked | Verified (3+ jobs) | 0–2 jobs | Not found (404) | Error | Not checked | Open jobs added |
|---|---|---|---|---|---|---|---|---|
| Greenhouse | 3,233 | 2,872 | 1,958 | 366 | 548 | 0 | 361 | 84,635 |
| Lever | 41 | 18 | 13 | 5 | 0 | 0 | 23 | 5,772 |
| Ashby | 2,600 | 2,600 | 1,881 | 435 | 284 | 0 | 0 | 44,060 |
| **Total** | **5,874** | **5,490** | **3,852** | **806** | **832** | **0** | **384** | **134,467** |

Of the boards with 0–2 jobs, 324 were empty and 482 had 1 or 2 jobs; they are not in the list.

## Tokens found per source

"All" counts every valid token seen in that source, including boards the collector already reads; "new" leaves those out. A token seen in several sources is counted in each, so the columns do not add up to the totals above.

| Source | Greenhouse all / new | Lever all / new | Ashby all / new |
|---|---|---|---|
| Hacker News "Who is hiring", last 6 threads | 30 / 21 | 18 / 16 | 101 / 93 |
| Common Crawl CC-MAIN-2026-43 | 2,828 / 2,637 | 0 / 0 | 884 / 791 |
| Common Crawl CC-MAIN-2026-39 | 1,415 / 1,291 | 27 / 25 | 2,489 / 2,320 |

By origin of the new tokens: only Common Crawl 5,744 (3,754 verified), only Hacker News 49 (29 verified), both 81 (69 verified).

Hacker News threads read: November 2026 (355 comments); October 2026 (383 comments); September 2026 (388 comments); August 2026 (369 comments); July 2026 (415 comments); June 2026 (489 comments).

Common Crawl index pages (one page = one index block, asked one at a time):

| Crawl | URL pattern | Pages in index | Pages read | Pages failed | URLs read |
|---|---|---|---|---|---|
| CC-MAIN-2026-43 | job-boards.greenhouse.io/* | 21 | 13 | 8 | 33,523 |
| CC-MAIN-2026-43 | boards.greenhouse.io/* | 6 | 5 | 1 | 13,255 |
| CC-MAIN-2026-43 | jobs.lever.co/* | unknown | 0 | 1 | 0 |
| CC-MAIN-2026-43 | jobs.ashbyhq.com/* | 2 | 2 | 0 | 3,235 |
| CC-MAIN-2026-39 | job-boards.greenhouse.io/* | 24 | 3 | 4 | 6,634 |
| CC-MAIN-2026-39 | boards.greenhouse.io/* | 5 | 4 | 1 | 8,352 |
| CC-MAIN-2026-39 | jobs.lever.co/* | 1 | 1 | 0 | 105 |
| CC-MAIN-2026-39 | jobs.ashbyhq.com/* | 8 | 7 | 1 | 19,714 |

## Board sizes

| Open jobs | Boards | Jobs on them |
|---|---|---|
| 3–9 | 1,446 | 8,211 |
| 10–49 | 1,861 | 40,415 |
| 50–199 | 450 | 40,341 |
| 200+ | 95 | 45,500 |

## The 30 largest boards

| # | Company | Hiring system | Token | Open jobs |
|---|---|---|---|---|
| 1 | Boxlunch | Lever | `boxlunch` | 4,664 |
| 2 | Bjakcareer | Ashby | `bjakcareer` | 3,156 |
| 3 | Anduril Industries | Greenhouse | `andurilindustries` | 2,580 |
| 4 | Private Equity Insights | Greenhouse | `privateequityinsights` | 1,284 |
| 5 | Veterinary Emergency Group (VEG) | Greenhouse | `veterinaryemergencygroupst` | 1,185 |
| 6 | EquipmentShare | Greenhouse | `equipmentsharecom` | 1,071 |
| 7 | Veeva | Lever | `veeva` | 861 |
| 8 | Centria Autism | Greenhouse | `centriaautism` | 833 |
| 9 | Meridial | Greenhouse | `agency` | 827 |
| 10 | ALO | Greenhouse | `aloyoga` | 760 |
| 11 | Speechify | Greenhouse | `speechify` | 738 |
| 12 | Accenture Federal Services | Greenhouse | `accenturefederalservices` | 730 |
| 13 | Capco | Greenhouse | `capco` | 702 |
| 14 | Coupang | Greenhouse | `coupang` | 689 |
| 15 | House Buyers of America | Greenhouse | `housebuyersofamerica` | 636 |
| 16 | Langan Engineering & Environmental Services | Greenhouse | `langanengineeringandenvironmentalservicesllc` | 586 |
| 17 | FeverUp | Greenhouse | `feverup` | 561 |
| 18 | Airapps | Ashby | `airapps` | 498 |
| 19 | Axon | Greenhouse | `axon` | 495 |
| 20 | Esri | Greenhouse | `esri` | 492 |
| 21 | BlueSky Telepsych | Greenhouse | `blueskytelepsych` | 456 |
| 22 | Lilt Production | Ashby | `lilt-production` | 452 |
| 23 | Luminis Health | Greenhouse | `luminishealth` | 451 |
| 24 | Allarahealth | Ashby | `allarahealth` | 437 |
| 25 | DoorDash USA | Greenhouse | `doordashusa` | 433 |
| 26 | Neura Robotics Gmbh | Ashby | `neura-robotics-gmbh` | 427 |
| 27 | Alpacahealth | Ashby | `alpacahealth` | 423 |
| 28 | Morgan & Morgan, P.A. | Greenhouse | `morganmorganjobsapplynow` | 414 |
| 29 | Renuity | Ashby | `Renuity` | 414 |
| 30 | Relativity Space | Greenhouse | `relativity` | 403 |

## What failed or was not checked

**The run.** One run of 2,405 seconds (40 minutes), 13 November 2026, about 19:35–20:15 local time. Requests were spaced at least 0.26 seconds apart across all hosts together (under 4 a second), with a 20-second timeout, one retry and the User-Agent `job-board-collector/1.0`. Requests made: Greenhouse API 4,826, Ashby API 2,606, Lever API 18, Common Crawl index 89, Hacker News search 7. Outside the run: 15 test requests before it (10 to Common Crawl, 4 to the hiring APIs, 1 to Hacker News) and 7 after it (4 Greenhouse names, 3 looks at the largest boards).

**Hiring-system APIs: nothing refused.** No API returned 429 or 503 and no connection was refused. Six Ashby requests timed out at 20 seconds; all six succeeded on the retry. No token ended with an error.

**Common Crawl index: many pages failed.** Of the 89 requests to index.commoncrawl.org, 46 did not return a result (HTTP 504 or 502, two timeouts). Each page got one retry and was then skipped. It never refused a connection and never returned 429 or 503, so the source was not shut off, but the gaps are large:
- October crawl (CC-MAIN-2026-43): `job-boards.greenhouse.io` 8 of 21 pages failed; `boards.greenhouse.io` 1 of 6 failed; for `jobs.lever.co` the page-count request failed twice, so no Lever page of this crawl was read (a test request before the run did return that page, with 524 URLs, so the data exists).
- September crawl (CC-MAIN-2026-39): `job-boards.greenhouse.io` was left after 4 pages failed in a row: 3 of 24 pages read, 17 never asked; `boards.greenhouse.io` 1 of 5 failed; `jobs.ashbyhq.com` 1 of 8 failed.
- Index pages are alphabetical, so a failed page is a missing stretch of the alphabet for that crawl, not a random sample.
- Older crawls (August 2026 and before) were not asked: after the second crawl 4,088 tokens were already waiting, more than could be checked in the time left.

**Not checked: 384 new tokens** (361 Greenhouse, 23 Lever). Time ran out. Tokens were checked newest crawl first and, within a crawl, by how many crawled pages they had, so these are September-crawl tokens with the fewest pages.

**Lever is almost absent.** Only 41 new Lever tokens were found, 18 checked, 13 verified. Common Crawl holds very few Lever pages (105 URLs in the September index). Another source is needed for Lever boards.

**Hacker News is a small source.** All 6 threads (June–November 2026, 2,399 comments) were read without failures and gave 149 tokens, 130 of them new.

**The list is not filtered by industry.** It holds every board that passed the check, whatever the company does. The three largest were opened once more to see what they are:
- `boxlunch` (Lever, 4,664): shop staff for BoxLunch and Hot Topic stores; five titles account for 4,088 postings ("Seasonal Key Holder" 924 times).
- `bjakcareer` (Ashby, 3,156): 341 different titles repeated across 30 locations.
- `privateequityinsights` (Greenhouse, 1,284): 1,125 postings in London; the same roles repeated per language (486 titles contain "speaking", as in "Business Development Manager | Danish speaking") and 169 volunteer roles.

**"Open jobs" is a raw count.** It is the number of postings the API returned at the time of the check, before any of the collector's own filtering or de-duplication. One job listed in several cities counts several times.

**Possible overlap with boards already read.** Only the exact (hiring system, token) pair was compared with the sources files. Looking at names afterwards:
- 14 verified boards (353 jobs) carry the name or token of a company already in the sources files under another system or token, for example `klaviyo` on Greenhouse (146 jobs; already read through Ashby), `Lovable` on Greenhouse (60) and `deliveroo` on Ashby (8). Some are a different company with the same name (`figure`, `current81`).
- 16 names appear on two verified boards each (32 boards), for example `kalshi` on Greenhouse (28) and Ashby (41), `betterhelp` and `betterhelpcom`.

**Names and token spelling.**
- Greenhouse names come from the board endpoint (all 1,958). Four of them were fetched just after the run ended, because the deadline cut them off.
- Lever and Ashby names are made from the token, so some read badly ("Bjakcareer", "Allarahealth").
- 41 Ashby tokens contain a space. In the file the space is written as `%20` (`Flock%20Safety`), the exact form sent to the API, so the address works without change; the name keeps the space.
- 250 tokens contain capital letters and are kept as found.

**Not queried at all.** The European hosts `job-boards.eu.greenhouse.io` and `jobs.eu.lever.co`.

**Working files** (outside the project, in the session scratchpad, may not survive the session): the script, the raw index pages, every checked token with its result, and the 384 unchecked tokens.
