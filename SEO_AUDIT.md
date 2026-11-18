# Pages that compete for one query (first pass, 18 Nov 2026)

Asked by the owner on 18 Nov 2026: «итогово проверяй, чтобы не дай бог у нас не было проблем с каннибализацией». `seo_audit.py` reads the
title, the main heading, the canonical address and the robots tag of every built page except job pages and reports pages whose titles are
about the same words. First run: a local build (41,187 jobs; 11,530 pages read, 11,418 open to search). The live site holds five times the
jobs, so it has more pages of each kind; the patterns are the same. Run it again on the full site before the fixes (part 6 of `PLAN_RU.md`).

    python3 seo_audit.py site --out report.md

## What is clean

- No page without a title or a main heading. No title longer than 65 characters. No canonical address pointing to another page.
- Only one exact duplicate title (it belongs to pattern B below).

## Real conflicts (the same query answered by two pages)

| # | Pattern | Example | Pairs in the local build | Proposed fix (decided in part 6, not done yet) |
|---|---|---|---|---|
| A | Two category systems with the same names: `/jobs/<field>/` (the field each job is filed under) and `/categories/<group>/` (a group of kinds of work) | `/jobs/security/` and `/categories/security/`, both “Security jobs” | 6 (sales, legal, security, education, customer service, HR) | One page per query: `/categories/<group>/` is the fuller page (definition, kinds of work with counts), so `/jobs/<field>/` names it as canonical and links to it; links across the site go to the canonical one |
| A2 | The same for remote | `/remote/security/` and `/categories/security/remote/`, both “Remote security jobs” | 6 | The same rule as A |
| B | A kind of work named like a field | `/roles/consulting/london/` and `/locations/london/consulting/`, both “Consulting jobs in London”; `/roles/supply-chain/` and `/jobs/supply-chain/` | 12 + 2 | Field × place stays the page for “<field> jobs in <place>”; the role × place page of the same name is not built, its address forwards to the field page |
| C | Crypto pages of roles that are crypto by nature | `/crypto/roles/trader/` and `/roles/trader/`, both “Trader jobs”; `/crypto/chains/ethereum/` and `/skills/ethereum/`, both “Ethereum jobs” | 4 + 1 | The crypto page says “at crypto companies” in its title and heading, or names the role page as canonical where nine jobs in ten are the same |
| D | Home and the search page | `/` “Job Search: … Jobs Hiring Now” and `/jobs/` “Search 41,187 Jobs” | 1 | `/jobs/` is titled as the full list with filters (“All jobs: …”), the words “job search” stay with the home page |
| E | Page 2, 3, … of a company's jobs carry the first page's heading | `/companies/spacex/2/` “Jobs at SpaceX” | 33 companies | “Jobs at SpaceX, page 2” in the heading (the titles already differ) |

Fixed on 18 Nov with this pass: the title “Crypto crypto custody and wallet specialist jobs” (a doubled word).

## Not conflicts (the check groups them because it drops numbers and filler words)

- `/jobs-that-pay/20-an-hour/`, `/25-an-hour/`…: different amounts. `/salary/100k/`, `/150k/`…: the same.
- `/resume-words/responsible/` and `/resume-words/responsible-for/`, `/worked-on/` and `/worked-with/`: different phrases people search.
- `/privacy/` (the policy) and `/roles/privacy/` (privacy jobs).

## Still to check in part 6

- Skill pages against role pages with one word in common (“python jobs” and “python developer jobs”): the titles differ, the lists overlap;
  measure the overlap of the job lists, not the titles.
- Place pages: city, metro area, state and country with the same name (New York city and state).
- The question pages (salaries, how to become, job descriptions, interview questions) against the guides and the glossary for the same question.
- Short addresses that are stubs (`/glossary/ats/`, `/vs/indeed-vs-linkedin/`): one canonical address in links and in the sitemap.
