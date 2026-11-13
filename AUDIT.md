# Site audit, 2026-11-13: findings and status

An independent review of the live site (157 pages, 42 data files, the whole search index row by row) and of the code.
Status: ✅ fixed · 🟡 fixed in code, shows after the next daily collection · 📋 open. Numbers are the reviewer's finding numbers.
When you fix an open item, move it up and say how you checked it.

## Fixed on 2026-11-13

| # | Finding | What was done |
|---|---|---|
| 1 | "See all N in search" opened an unfiltered search on category, skill, role, location and other lists | `auto_more()` in `build.py` builds the matching search query for every list |
| 2 | "Erase everything" deleted more than it said and left tool data | The confirm names everything; tool keys are erased too |
| 5 | CSV export used the UTC date and downloaded an empty file | Local date, no empty file, formula-safe cells, BOM for Excel |
| 6 | Restore accepted any JSON shape | Only values of the right shape are restored |
| 8 | Privacy page said fonts come from Google and resumes are not saved | Rewritten to match what is stored and where |
| 9 | Terms page pointed to a contact "once published" | Contact is stated; a "Job descriptions" section added |
| 10, 11 | Employers page promised self-serve and "pin from $99" while nothing can be bought | Title, description, steps and refund answer now depend on whether the account is open; "feature from $99" |
| 13, 31 | Hourly and monthly pay shown as salary; three salary formats; a $1.2M outlier; merged pay zones | 🟡 `tidy_pay()` in `collect.py`: one format, the unit is kept ("an hour", "a month"), implausible values dropped, first pay zone when zones are far apart |
| 14 | "cybersecuritys", "IT supports" | `ROLE_PLURAL` |
| 15 | "was a Engineering role", "an open Other role", "in Remote, Global" | Summary sentence rebuilt |
| 16 | 547 feeds on one page, 544 on others | About and methodology use the number of feeds read |
| 17 | API page said every feed holds 30 jobs | Corrected: company feeds hold all jobs |
| 18 | A tool FAQ sentence was false once 53% of postings showed pay | Sentence depends on the share |
| 19 | "We do not accept anonymous postings" would become false with employer posting | Sentence switches when the employer account opens |
| 20 | US-dollar salary estimates on interns and on jobs outside the US | Estimates only for US roles, never for interns or the "Other" category |
| 23 | Hybrid roles labelled Remote: about half of all "remote" jobs | 🟡 Remote only when the employer's workplace type or location says remote; hybrid has its own label |
| 24 | Place pages missed a quarter of US jobs and caught wrong ones (Vancouver WA, Porto Alegre, Belfast, New Mexico) | New location model in `build.py`: each part of the line is read on its own, a written country or US state beats a city name; regions derive from countries |
| 25 | New-grad roles counted as interns; "Operations Associate" as junior; "Chief of Staff" as lead | 🟡 `level()` rewritten |
| 26 | Role pages caught other professions (legal project managers under technical program managers, hardware test under QA) | Tighter rules, an exclusion for sales, legal, recruiting and marketing titles; the role is now "Program and project manager" |
| 27 | Categories: "Trust" matched Rust, security engineers under Engineering, sales under Marketing, 17% in "Other" | 🟡 `classify()` and `CATS` reworked, with tests in this session |
| 28 | "Smart Contract Engineer" typed as contract work; "Internal" as internship | 🟡 `etype()` rewritten |
| 29 | "Anywhere in the United States" listed as work from anywhere | 🟡 Only when the line names no country, region or time zone |
| 30 | Go matched "go-to-market", Swift matched SWIFT payments, React matched the verb; the 8-tag cap dropped real skills | 🟡 Patterns fixed, cap raised to 12 |
| 32 | "We can’t sponsor" with a curly apostrophe, "relocation is not available", "Flexible PTO (20 days)" counted as perks | 🟡 Negations added, flexible PTO is no longer unlimited PTO |
| 34 | Brand dropped from long titles; titles cut mid-word | `fit_title()` shortens the descriptive part and keeps the brand |
| 35 | Footer headings were `h4` right after `h1` | They are plain labelled paragraphs now |
| 36 | Page 2+ of a list repeated page 1's description and sat in the sitemap | "Page N of M" in title and description, out of the sitemap, five pages at most |
| 37 | 404 and terms pages had a filler description | Real descriptions |
| 38 | Job markup: whole location line as one locality, wrong countries, excerpt as description | One Place per listed location with its country; full description for postings up to 14 days old (marked up in place) |
| 39 | `/my-jobs/` missing from the sitemap; the same role in two cities had identical titles | In the sitemap; the place is added to a job title when it fits |
| 41 | Sitemap said every page changed today | Job pages carry the date they were last checked or closed |
| 42 | Feed items had no date | `pubDate` added |
| 43 | Tap targets under 40 px | Header icons, chips, pager, tabs and text buttons enlarged |
| 45 | Low contrast in the footer | Lighter footer text colour |
| 46 | Manifest background colour from the old design | Paper colour |
| 48 | A failed fetch of the data branch could wipe the jobs database | The workflow tells "branch missing" from "cannot reach", and refuses to save a database half the size of the last one |
| 57 | One bad value in a feed stopped the whole daily run; jobs of removed sources never closed | Each feed is read inside its own guard; jobs of sources no longer read are closed |
| 58 | No size check | The workflow prints the size and stops before the hosting limit |
| 60 | `resume.js`, `widget.js`, `widgets.js` were not in the version hash | Added, so returning visitors get new versions |
| 7 | `/board/` with an unknown parameter showed an empty wall | Falls back to the latest roles with a line saying so; a link to the job list if nothing loads |
| 4 | “Clear my profile” left the skill-gap block, the note and the pasted text | The handler now clears all three (`site.js`) |
| 40 | BreadcrumbList markup missing on company, salary, insights, report and tool hub pages | `page()` now writes the markup from the visible trail on every page that has one |
| 3 | Salary checker offered “Intern” and “Junior” levels that never returned a figure | The level list now holds only levels that have at least 20 postings with a yearly range (`tools_pages.py`) |
| 12 | Methodology stated one minimum sample while pages used 3, 8, 10, 15, 20 and 30 | Three thresholds, each stated in the methodology: 15 for a median next to a list or company (company pages used 3), 30 for rankings and comparisons, 20 for the salary tools |
| 44 | Wide tables on phones had no scroll hint | A soft shadow now shows at the edge a table can still be scrolled towards (`.tablewrap`) |
| 49–56, 59 | Server (`server/src/worker.js`, not deployed): second post refused, company identity an exact string, edits skipping the link check, activation not atomic, placements outliving a removed job, pending orders never reconciled, rate limits that could be raced, a weak link check, no password reset | All nine fixed with tests (the suite went from 110 to 300 checks; each new test fails on the old code): company names are owned by one account through a normalised key, any edit of link, title, company or site re-runs the check, activation is one transaction, a deleted job takes its placement down, a cron and the order page ask the gateway about unpaid invoices, counters are a single statement, the link check follows redirects hop by hop, password reset exists (mail goes out only once a `MAIL` binding is set) |

## Open

| # | Finding | Note |
|---|---|---|
| 21 | Level names differ between pill, page title, salary table and tool | one vocabulary |
| 22 | Tool copy slips still open: "a honest" and "Download PDF" no longer appear in visible copy (checked 2026-11-13); contractor rate sentence reworded 2026-11-13 (fixed 2026-11-13: "Found 1 skills", "With prices up -2%", "Inc..") | `tools.js`, `build.py` |
| 33 | 392 groups of identical company, title and location count as separate roles in totals | decide whether totals should collapse them |
| 47 | Phone layout of the time-zone bar and the letter tools | `tools.css`, `tools.js` |
| 61 | Tool logic still open: job description checker misreads some salary formats; boolean search invents a title (fixed 2026-11-13: `num("150.000")`, "founded 15 years ago", 2000% ownership, and Go in running text such as "Python and Go", which also raises the number of jobs tagged Go at the next collection) | `tools.js`, add tests |
| 62–66 | Mixed title casing, "Other" shown as a category name, sample cards linking to `#`, (fixed 2026-11-13: "$440.00" next to "$2,200"; the leftover `/hiring-badge/` stub is now a real hiring badge page) | polish |
| 69 | Left after the server fixes: the account page has no password-reset form and no delete button for a job; `createOrder` creates the gateway invoice before saving the order; “renew” does not re-check the apply link; look-alike letters in company names are not folded | `assets/account.js`, `server/src/worker.js`, before the server is deployed |
| 68 | The contact handle is "@orderbulkreviews" on a site that promises no invented reviews | the owner's call |

## Not covered by the review

Search filters against URL parameters, widgets and embeds in a browser, the full sitemap (43,000 URLs), perk and skill
false positives on full posting text, real payment-gateway behaviour.
