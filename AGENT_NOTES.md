# Hiring Right Now — notes for whoever works on this repo next

Tech job board, English, static site on GitHub Pages. Owner: Simba0315. Live: https://simba0315.github.io/crypto-vakansii/
(the repo name and the address are temporary until a domain is bought).

## The name: Jobs Every Hour (owner, 15 Nov 2026)

The site and the brand are **Jobs Every Hour**, the name of its domain jobseveryhour.com. "Hiring Right Now" was the working name
before the domain was bought and must not appear on the site, in logos, pictures, emails or new copy. The name lives in one place,
`config.json` `site_name`: `build.py` (SITE), `brand.py` (the logo files) and `og.py` (the share picture and the square banner) read
it from there. After a change of name or palette: `python3 brand.py`, `python3 og.py`, `python3 og.py --banners`.

## How it works

- `collect.py` reads public hiring feeds (Greenhouse, Lever, Ashby; since 15 Nov 2026 also Workable, Recruitee, Teamtailor,
  Personio and Workday) listed in `sources.json` (crypto companies), `sources_tech.json` (tech companies), `sources_more.json` and
  `sources_ats.json` (read in turn, see "Sources and hiring systems") and writes `data/jobs.json`. Closed jobs are never deleted:
  `active=false` + `closed` date.
- `build.py` generates the whole site into `site/` from `data/jobs.json`, `config.json`, `assets/`.
- `check.py` checks the built site against the page standard (one H1, title/description length, self-canonical,
  heading order, alt on images, internal links). It must print OK for every template before a push.
  Since 26 Nov 2026 it also runs `standard2()` on every page: duplicate ids, aria-*/label ids that do not exist, buttons, links and
  form fields without a name, an FAQPage question not visible on the page, a bare H2 (`BARE_H2`: "Sources", "About the role",
  "Related tools"... every H2 names the page's key or asks a question), an `<img>` without width and height, the footer's About,
  Contact, Editorial policy, Privacy and Terms links, a top-level Organization without logo and sameAs (`ORG_SAME_AS` in build.py),
  and llms.txt (dated with the build, every page it names exists). New sections: give the heading the page's key.
- `.github/workflows/update.yml` runs daily (03:17 UTC) and on every push: restore the jobs database from the one-commit
  `data` branch, collect, save it back, build, deploy to Pages. `data/` and `site/` are not in `main`.
- `logos.py` finds each company's own site and saves its icon to `assets/logos/`. Only trusted addresses are used
  (hand-checked `OVERRIDE` list or `<name>.com`); a wrong logo is worse than none. Never draw or invent logos.
  When no site works, it takes the logo the company uploaded to its own Greenhouse, Ashby or Lever board (only near-square
  ones; `logos.json` then says `board:<ats>/<token>`, and the build does not use that as the company's site). A name whose
  obvious domain belongs to someone else goes into `NO_SITE` (mesh.com shows Microsoft's logo). Look at every new logo
  before publishing: put them on one page and take a screenshot.
- `logos_official.py` (25 Nov 2026) does the same for the companies with the most open jobs, from the live site's company
  list: the site from `logos.json`, its hand-checked `SITES`, the site the company's own job board links to, or `<name>.com`
  only when the home page names the company and links to our board (or the name is long and not a dictionary word). Icons:
  apple-touch-icon, manifest icons, `<link rel=icon>` (SVG drawn by Quick Look, WebP read by sips), favicon.ico of 64 px or
  more; 48 px at least, square, not blank, not an enlarged favicon; then the square logo on the company's own board. Polite:
  4 companies at a time, 10 s timeouts, our User-Agent, nothing behind a bot check (403, 429, challenge pages are skipped).
  Files: 96 px and 72 px (`s/`), palette PNGs of about 1.5 KB. Progress in `data/logos_official.jsonl`; `--retry` tries the
  failures again, `--dedupe` drops an icon that two different companies share.

## Freshness: exact times and the hourly run

The owner, 2026-11-13: "it must say when a job was added 30 minutes ago or 20 minutes ago, and you need to check often".

- Schedule: `update.yml` runs every hour at :17 UTC and on every push (this replaces "runs daily" in the section above). Measured on
  2026-11-13: a run takes 9 to 15 minutes, 7 to 13 of them reading the feeds. The 03:17 run is also the once-a-day run: `DAILY` is
  true only for it and for a run started by hand, and it guards the monthly report snapshot and the IndexNow ping. Put anything new
  that should happen once a day or less behind `if: env.DAILY == 'true'`. The schedule is stated on `/status/` and in the copy
  ("every hour", "hourly"): change the cron lines, `DAILY` and that text together. Never write "real time".
- Data: `collect.py` keeps `posted_at` (UTC, `2026-11-13T09:05:52Z`) from the feed's publishing time: Greenhouse `first_published`
  (never `updated_at`, which moves with every edit), Lever `createdAt`, Ashby `publishedAt`. `first_seen_at` is the moment our run
  first saw a job; only jobs new since this change have it, and no page shows it yet. `posted` and `first_seen` stay dates.
  A job without `posted_at` (closed before the change, posted through our own API) works everywhere at day precision.
- Pages: `when()` in `build.py` puts the exact time on a job's `<time>` (`datetime` and `data-t`, seconds since 1970) for open jobs
  under a week old. The text in the file stays the day label ("Today", "1d"): a page built an hour ago must not state an age.
  `freshen()` in `site.js` rewrites every `time[data-t]` younger than 24 hours ("now", "20 min", "3 h"; with `data-long`, on the
  job page, "35 minutes ago"), marks it `new` and repeats every minute. `decorate()` calls it, so every list a script renders gets
  it. Row labels must stay within 6 characters: the age column is 44px wide.
- Index: the last field of a row in `data/index.json` is the posting time in minutes since 1970 (0 when unknown or over a week
  old); `expand()` puts it in `j[23]`. `order()` sorts by the exact time, so "newest first" is right within a day.
- `node fresh_test.js` (labels, no negative ages, the refresh) must end with "0 failed".

## Accounts, checkout and automation (`server/`)

- `server/src/worker.js` is the whole API (Cloudflare Worker + D1, no dependencies): accounts, orders, Cryptomus invoices and
  webhooks, automatic activation, free job posting with an automatic link check, export for the build. `server/README.md` has the
  local commands and the go-live steps; `node --no-warnings server/test/run.mjs` must end with "0 failed" before any push that
  touches `server/`.
- It is written and tested but NOT deployed. Since 15 Nov 2026 it is meant for our own server, not Cloudflare (next section but several:
  "Accounts, job alerts and employer posting on our own server"). Until `"api_url"` in
  `config.json` is set, the site has no account page and says plainly that self-serve is not open yet.
- When it is live: `collect.py` (`direct_and_paid`) pulls posted jobs and paid placements from `/api/public/export.json` into
  `data/jobs.json` and `data/placements.json`; `build.py` applies them (pinned, featured, sponsors). A purchase asks GitHub to
  rebuild the site.
- Never sell what does not exist: Plus stays off (`PLUS_LIVE`) until its features are built.
- No job is ever delayed or gated for payment (decided 2026-11-13, the owner left the call to the agent): traffic is what employers
  pay for, and paying to see public jobs is what users of other sites hate most. Plus sells speed and tools only. AI features run
  only for paying accounts and always inside a fixed monthly allowance, so their cost can never exceed what was paid.

## Marketing (owner, 2026-11-12/13: "everything that exists in marketing must be on the site")

- Problem first, proof from our own data, then the offer (rule 10). Free tools as lead magnets (`tools_pages.py`), sharing and
  embeds as distribution, price anchors and a marked best plan, clear guarantees, comparison and landing pages per audience.
- Hard limits: no invented reviews, logos of "customers", countdown timers, fake scarcity or popups that block reading.
- Backlog: `COMPETITOR_GAPS.md` (what other job sites have that we do not, with priorities). Take the highest-priority item that
  is not built yet, build it properly, tick it off in that file.

## Free tools (`tools_pages.py`, `assets/tools.js`, `assets/tools.css`)

- `/tools/` and 13 tool pages (resume match, salary checker, pay converter, raise, offer comparison, stock options, time zones,
  cover letter, negotiation email, contractor rate, job description checker, JobPosting markup, boolean search). Everything runs
  in the browser; the only embedded data is salary aggregates built from the day's jobs.
- Pure logic in `assets/tools.js` is covered by `node tools_test.js assets/tools.js` (must end with "0 failed").
- New tools go into the `TOOLS` list inside `build_tools()`; ideas with search demand are in `ROADMAP.md` section 8.

## Audit backlog (`AUDIT.md`)

An independent review on 2026-11-13 listed 68 findings; most are fixed, the open ones are in the table at the end of that file
(tool logic, a few stale texts, the whole server review). Fix open items before adding new page types.

## Getting into Google's job search (what Google requires)

Checked against Google's own documentation on 2026-11-13: the job details must be visible without login, applying must be free
and possible from the page, the description must be complete, `jobLocation` needs `addressCountry`, remote roles need
`jobLocationType` and `applicantLocationRequirements`, expired jobs must lose their markup. So: never gate a listing or its apply
link, for money or for sign-up. Full descriptions are stored only for postings up to 14 days old because of the hosting size limit
(`DESC_SINCE` in `collect.py`); raise it when the site moves off GitHub Pages. Pages with a full description carry their
JobPosting data as microdata on the visible text (`microdata()` in `build.py`), the others as JSON-LD.
Still needed from the owner: Search Console for the site (his Google account), then the Indexing API.

## What users of job sites complain about (`USER_PAINS.md`)

53 review sources read on 2026-11-13 (Hirify on Product Radar, Trustpilot, Hacker News and others). The top pains are dead and
long-open listings, silence after applying, scams and spam, results that ignore what the person excluded, and paying to look
for work. The file ends with a ranked list of 15 things to build; several are done (see `ROADMAP.md` section 11). Take the next
one from that list when choosing work, and never build the patterns it lists as "do not copy".

Before every push, try these by hand or by script, because broken basics were a top complaint about other sites: the back
button returns to the same place in a list; the count above a list equals the rows it leads to; changing a filter resets
paging; the search page works on a phone-width screen; no console errors on the home, search, job and tools pages.

## Search demand

`python3 keywords.py` collects Google search suggestions into `keywords.json`. Compare the phrases with the pages we have
(`ROADMAP.md` section 8) and build pages or tools for real gaps; skip phrases outside tech hiring.

## Speed (keep it this way)

- Fonts are self-hosted in `assets/fonts/` (latin + latin-ext, variable woff2); Inter and Bricolage are preloaded. No third-party
  requests on any page: do not add external fonts, scripts or trackers.
- `data/index.json` stores a job's address as `0` (derived from title + company), a number (`-N` suffix) or the full string; `site.js`
  `expand()` rebuilds it. `data/head.json` holds the newest 300 rows so the search page paints before the full index arrives.
- `site.js` adds speculation rules (pages are prerendered when a link is hovered; the search page and For you are only prefetched)
  and registers `sw.js`, which caches fonts, logos and `?v=` assets. Anything that changes state on page load must wait for
  `prerenderingchange` (see `markSeen`).
- The stylesheet is minified at build time by `mincss()`; double-quoted strings are safe, do not use single-quoted CSS strings.
- Pages do not load the whole stylesheet (26 Nov 2026): `cut_css()` in `finish_html` gives each page only the rules that can match it.
  Pages of a build link `css/<kind>.css` (kind = first part of the address; `cut_files()` writes them at the end of the build from the
  classes and ids of all the pages of that kind plus every word of the scripts they load); the home page, job pages (serve.py),
  `offline/` and `my-jobs/` carry their rules in a `<style>`; a page with a script that is not ours keeps `style.css`. So: write class
  names whole in scripts (`'ic-' + name` would be cut), keep scripts in `assets/`, and anything that inserts another page's markup must
  add `style.css` first (app.js `wholeCss()` for the search page's preview pane). Long blocks (footer, lists of jobs, tables, FAQ, tiles)
  have `content-visibility:auto` in style.css: only on blocks whose inner margins cannot leak out, or the spacing would change.
- Measuring on this Mac when the PageSpeed API's daily quota is used up: `python3 speedlab.py out.json --runs 3 home=<url> ...` (cold
  loads in headless Chrome as a mid-range phone, Lighthouse-style score; `--mod` rewrites the live pages to try a change first).
  Its numbers move with the Mac's load: compare runs made at the same time, and confirm with PageSpeed when the quota is back.

## Local work

```
git fetch origin data && bash datastore.sh unpack   # fast; do not run collect.py locally unless needed
python3 build.py && python3 check.py        # must end with every template OK
python3 -m http.server 8765 --directory <a folder that contains site/ as crypto-vakansii/>   # pages use the /crypto-vakansii prefix
```

Push with the deploy key already configured in this clone (`core.sshCommand`). Always `git pull --rebase origin main` first.

## Changelog

`CHANGELOG.md` has one line per scheduled improvement run (newest first) and "Ideas for the owner". Read it before picking the next change.

## The plan

`ROADMAP.md` (in Russian, for the owner) lists every request he has made and where it stands. Any new request from him goes
into it at once; when something ships, update its row. He asked for this on 2026-11-13: "add everything to the plan, always".

## Categories and roles (`roles_info.py`, `/categories/`, `/roles/`)

The owner asked for a category directory "like the big job sites", with a page and text for every category, and not only for
tech work. It has two levels: 23 categories (`FAMILIES`, pages `/categories/<slug>/`) and about 160 roles (the 25 in `ROLES` in
`build.py` plus `MORE_ROLES`, pages `/roles/<slug>/`). A role is a pattern matched against job titles; it gets a page at 20 open
jobs. Each role has a plural and one plain line ("a person in this job …") that becomes the page intro, the meta description and
the first FAQ answer, so write it as a verb phrase that an outsider understands. `"nt"` on a role leaves out engineering and
sales titles that only mention the field ("Software Engineer, Tax Platform"). Before adding a role, count it and read a sample of
the titles it catches (the test loop is in the commit that added the file). The first 25 roles have every combination page
(remote, entry-level, each big place); the others only where 20–25 jobs fill the page, to keep the site inside the hosting limit.
Logos: a company without an official logo is shown with no picture at all (`.ava:not(.has)` in `style.css`); never bring the
letter squares back.

A job's field (`cat`) comes from `collect.CATS` (the first generic word of the title wins, then the department, then `CATS_LATE`) and is
mended by `build.job_field()`: `FIELD_FIX` (a trap word and the fields it wrongly sends titles to: "technician" -> Manufacturing for a
Patient Care Technician, "counsel" -> Legal for a counselor) and `TITLE_NOISE` (pay rates, incentives, towns filed again without them).
live.py calls the same function. Mend a field there, never in `collect.CATS`/`RULES` (a change re-reads every posting in the hourly run),
and add the real titles it moves and must leave to the assertions under it. A role pattern that catches another trade gets a leading
`^(?!...)` exclusion in `roles_info.py` (`NOT_ABA`, `NOT_CLINICIAN`), kept JavaScript-compatible: assets/site.js reads the patterns too.

Field pages since 25 Nov 2026 (the owner asked four times for each field to be its own page): `fields_info.py` holds, per field, the words
of its search (title key, heading), the /jobs/<category>/ lists that are the same field (they name the field page as canonical and every
link to them is rewritten to it in `finish_html`, see `CAT_HOME`), the BLS occupation groups and occupations (Occupational Outlook
Handbook, read 25 Nov), what its postings ask for (regexes counted in the build), four steps and its own questions. `field_parts()` in
build.py draws them. `python3 fields_info.py` fails when two fields share a sentence: write new text for each field, never copy one.
The research behind it is the last section of `SERP_AI_CHECK.md`.

Links to the page that keeps a search (26 Nov 2026, the linking pass): `one_page_per_query()` decides which page of a group with the same
title words stays open to search; every link must lead to that page, not to the copy. `same_as(src, dst)` in build.py makes every page
written after the call link `dst` instead of `src` (finish_html), and crosslinks.py leaves the copies out of its blocks. Pairs are named
where their pages are made: the field job lists and their remote lists, a kind of work named like a field's search (`ROLE_FIELD`,
/roles/bilingual/ -> /categories/languages/), the crypto role lists named like the role page, a chain named like a skill page. A pair
found only at the end is mended in one pass over the pages and printed ("links mended after the build, name these where the pages are
made"): add it where the pages are made. A skill named like a field (`SKILL_FIELD`, /skills/ai/) is a different search: its pages say
"Jobs that ask for AI skills" and link the field page, which links them back. Check after a build: `python3 inlinks.py site` (orphans,
pages linked only from the header or footer, links to copies or redirects) and `python3 seo_audit.py site`.

What search engines are asked to index (26 Nov 2026, Bing's webmaster guidelines; numbers in SERP_AI_CHECK.md, "Bing webmaster
guidelines"): a narrow list under `INDEX_MIN` (20) jobs and a company page under `INDEX_MIN_CO` (5) open jobs are `noindex,follow`
and leave the sitemap and the IndexNow list (`THIN`); they stay for visitors, keep their links (crosslinks.py) and come back by
themselves when they have the jobs. A list opts in with `listing(..., index_min=...)`: the long-tail combinations, the crypto lists,
the /new/ lists by skill and kind of work, the company pages. Never pass it for /categories/, the hubs, the guides, the tools or /vs/.
`every_list` leaves out the lists under the line. `DUP_PAGES`: /skills/<s>/new/ and /roles/<r>/new/ name /new/skills/<s>/ and
/new/roles/<r>/ (the same jobs) as canonical. `same_text_jobs()`: an open job page that repeats an earlier one word for word (same
company, title, place and text) gets `dup_of` in its record and names the first as canonical. Sitemap lastmod: a job page its first
day (or `changed`, which collect.py sets when the posting's text changes or it reopens), a closed one its closing day, a list the
first day of its newest job (`PAGE_MOD`), any other page the day its text last changed, figures aside (`page_dates()`, the file
data/lastmod.json, carried between runs in the Actions cache). check.py fails when a sitemap lists a noindex or canonicalised page,
a missing page or an address twice.

## The owner's taste (screenshots of 14 Nov 2026 — follow it in every new block)

He sends what he likes; keep these, and build new blocks the same way:
- **Liked:** the hero (big two-line headline with one highlighted phrase, the "Checked Nov 14 · open jobs · new in 3 days" pill,
  the rounded search bar, chips under it, "Near you" line, four big numbers); the "Latest jobs" window with tabs and a side column
  of cards (fit quiz, resume builder, what jobs pay, free tools); the strip of company logos "Read every hour from the career pages
  of …"; "What every listing tells you" (a real listing in the middle, numbered notes on both sides); category cards with a soft
  icon, count and a short plain description.
- **Disliked:** green fills and blocks (the green "Hiring?" band), green pictures on black, dull charts. Use light cards with a thin
  border, dark text, one accent colour for data (blue `--viz-1`, orange `--viz-2` for the one mark that matters); green stays only
  as a small accent (the live dot, a highlight behind one phrase, links' underline).
- **Free must be said:** where something is free (posting a job, the resume builder, tools), the word "free" is visible and big,
  not buried in a sentence.

## Pictures before words

The owner, looking at the rankings hub on 2026-11-13: "what are these texts, I cannot read at all; more pictures, charts,
infographics everywhere". A page that is a list of headings and sentences counts as unfinished. Helpers in `build.py`:
`market_pics` (four panels: jobs by field, pay histogram with the median column, three rings, postings by day), `cols()` (column
chart), `donut()` (ring), `.hbars` (bars with a link per row), `ins_chart()` (the top ten of a ranking as bars above its table),
`icard()` (a ranking as a card with its top four as a small chart). Every chart is counted from the build's own data and has one
caption that says what it shows; no decorative charts, no invented numbers. When you add a page with numbers, draw them.

## Added on the evening of 2026-11-13 (one long session with the owner)

- Tools: 28 in `tools_pages.py` / `assets/tools.js` (643 tests), plus the resume builder, the match and the tracker shown first.
  The hub groups job-seeker tools under four headings as tiles with a small screen; keep new tools in that form.
- `/companies/compare/` and `companies/compare/<a>-vs-<b>/`: employers side by side from `data/compare.json` (mirrored bars).
- `/feeds/`: an RSS address for every field, role and skill. `post.py` + `channels.json` + `CHANNELS.md`: posting new jobs to the
  owner's own Telegram and X; silent until he lists a channel and adds the secret himself. Never enter or ask for his tokens.
- `/plus/` and `/post-a-job/`: tariffs as three columns with ticks, every feature shown as a small example screen. Plus is not
  on sale; do not remove the banner that says so until the server is live. No invented reviews, user counts or ratings.
- `/ahead/`: ten things that run in the visitor's browser (live check with the employer's hiring system, alerts without an
  account, voice search, listen, calendar reminder, skills in plain words, neighbouring roles, a link that carries the answers,
  the result as a picture, skill demand inside the resume builder). The code is in `jobExtras()` and the "For you" block of
  `assets/site.js`, `assets/resume.js` and the end of `sw.js` in `build.py`.
- Closed jobs keep their pages; the owner objected to the word "archive" on the home page. Say "closed, the page stays".
- `REPORT_RU.md` is the owner's report in Russian; update it when something he asked for ships. He reads the task list pinned in
  the app and this report, not the English files.

## The server, state on 2026-11-13 (`server/`, 948 tests, not deployed)

Accounts, Cryptomus checkout, employer postings with fraud checks, three proofs of identity (company email, DNS or file, LinkedIn
for recruiters), AI endpoints for Plus (`/api/ai/…`, Anthropic Messages API, one model constant, a monthly allowance whose worst
cost is checked by a test against the price of Plus), per-job view and apply counters, admin review. What the site's pages must
do to use each of these is listed in `server/README.md` under "What the site's pages need"; none of it is wired into the pages
yet. Deploying needs the owner's explicit go-ahead for Cloudflare and his own secrets (Cryptomus, mail, LinkedIn, Anthropic):
never enter them, never run the deploy for him.

## Prices (the owner's decision of 2026-11-13)

The owner cut every price to about a third "temporarily" (launch prices). `config.json` holds the current price, the earlier one
in `"was"` (shown crossed out) and `"launch_prices": true` (the green line above the tariffs). Pages read prices through
`price_of()` / `was_of()` in `build.py`; `PRODUCTS` in `server/src/worker.js` must carry the same amounts. Only the owner changes
prices. Never add a countdown or a deadline that is not real.

## Guides, help, the open hiring index (`/guides/`, `/help/`, `/open-hiring-index/`, `/investors/`)

Guides are the blog: each is written once in `build.py` (`guide(...)`) and its figures are recounted from the open postings on
every build. A new guide needs a chart or a list from the data, a lead that states the fact, and links to the lists and tools it
mentions; add it to a category that exists. `/help/` is one page of short answers with a filter (`HELP`): when a feature ships,
add its answer there. The open hiring index scores employers from their own postings (the formula is on the page); do not call it
"best employers". `/investors/` shows counted facts only: no forecasts, no revenue claims.

## "For you": the match by answers (`/for-you/`)

Five plain questions (kind of work, experience, where, pay, skills), answered with buttons; the markup is in `build.py` (`FY_WORK`,
`ask()`), the logic in `assets/site.js` (`judge()`): a job that contradicts an answer is left out, a job that agrees gets a tick,
a posting that is silent on the point gets a question mark and is listed after the full fits. Nothing is sent anywhere; the answers
live in `hrn_profile` in the browser. This page is the free half of the planned paid "Plus" (`ROADMAP.md` section 33), so keep it
free and never put a login in front of it. When the index gains a field, add it to `judge()` and to the reasons shown.

## Where the jobs could also come from (`SOURCES_RESEARCH.md`)

Research of 2026-11-13: what Hirify and JobAssist read, 40 Telegram channels with their formats and the page markup of
`t.me/s/<channel>`, 20 more hiring systems and open feeds with their addresses, ways to find company addresses in bulk, and what
Indeed offers employers. The build order is in `ROADMAP.md` sections 29 and 30. The site promises "read from the employer"; a source
that is not the employer's own hiring system must be labelled as such and kept out of the main lists.

## Who else works on this repository

- A cloud routine (created 2026-11-13, "Hiring Right Now: one improvement every 3 hours", claude.ai/code/routines) makes one
  improvement every 3 hours and pushes to `main`; a scheduled task on the owner's Mac did the same before it. Always
  `git pull --rebase origin main` before starting and before pushing, add a line to `CHANGELOG.md`, and push once per run:
  every push cancels a deploy that is still running.
- **A review of every page family is under way (since 17 Nov 2026; the owner: "not worked through, from the account to everything
  else").** `PAGES_REVIEW.md` is the table: a family is reviewed by eye on a desktop, a phone and in the dark theme, by helpers that
  work on a family for an hour or two in their own branch. On 17 Nov the cloud run and a helper changed the same six places of
  the career families within the same hour and the merge had to be untangled by hand. So, for the cloud run: do NOT restyle or
  restructure a page family (its template in `build.py`, its CSS) while the review is going on; the families already reviewed are
  marked in the table and the rest are next in line. Pick work that does not touch templates: new glossary terms, new guides
  and advice articles, new resume words, new entries of `jobs_for_pages.py`, data fixes in `collect.py`, wrong facts or typos.
  The shared parts to reuse, never to duplicate: the row of figures `nums([...])`, `section(title, inner, label=...)` with a
  two-weight headline, the classes `lp` and `hub` on `<main>`, `act_row()`, `role_kit()`.

## Rules from the owner (do not break)

1. Every page must pass his "perfect page" standard: SEO, GEO/AIO, AEO, E-E-A-T, mobile. Title: key first, brand last, about 60
   characters. Unique description 110–160 characters. One H1. H2s carry the topic or a real question. Direct answers in the
   first 40–60 words under a question. FAQPage markup only where the FAQ is visible. Dates and sources visible. No invented
   people, credentials, reviews, numbers or partners.
2. English-language market. Payments in crypto only for now (cards later), through a payment gateway checkout (the owner named
   Cryptomus, 2026-11-12), not by showing wallet addresses on the site. Never touch wallets, never ask for or enter keys. Do not
   change prices or contacts in `config.json` on your own (the Telegram contact was given by the owner).
3. Closed jobs stay as archive pages.
4. Real company logos only, from the company's own site.
5. Design (the brand of 15 Nov 2026 keeps this green: "Evergreen" in brand.py, see "The brand" at the end): warm paper, ink, hairlines and ONE calm green (tokens in `style.css`: `--hl` green as a fill under text, `--ac`
   green as a line, `--pop` the same green on dark surfaces). History, 2026-11-13: the owner asked to remove the "AI look", said
   he liked the green marker under words and the green underlines on links, then left the colour to us ("decide yourself, maybe
   neutral; what matters is that people like it, it is convenient, simple, clear, and nobody thinks it is AI"). The acid lime on
   black was dropped because that pairing is the stock look of generated landing pages; the marker and the underlines stayed,
   in a natural green that also passes contrast as a line. Do not bring lime or per-section colours back.
   Banned, because they read as a template:
   - offset "sticker" shadows, gradients as decoration, glow, pulsing dots, hover lifts;
   - grids of identical cards that hold only a heading and two lines; use a ruled list (`.feats`, `.gloss`) or a table.
     A card is fine when it shows something real: tool tiles (`.tcard`) carry a small screen of the tool's result;
   - small capital letters in mono with letter-spacing as labels; mono is for numbers only;
   - boxes around everything: lists are flat with hairlines, like a printed index (`.jobs`, `.tiles`, `.hbars`, tables);
   - arrows after every link;
   - (lifted on 17 Nov 2026 by the owner's own reference, dlocal.com: "the design is great, a lot can be taken for different
     pages") a row of large figures under a title, a small label above a section title, framed panels, one pill button with an
     arrow per block and rows that open ARE the site's language now: `nums()`, `section(..., label=)`, `kpanel()`, `khero()`,
     `go()`, `krows()`, `kmore()` in `build.py`. Use them as the reviewed pages do; do not invent a second set. Questions with
     answers stay readable text on content pages (`.qa`); the home page lists its questions as rows that open.
   - Panels are light. A dark panel ("ink") was tried for "Post a job for free" on the home page on 17 Nov 2026; the owner:
     "делай как считаешь нужным, но мне кажется светлая лучше". Dark stays for the footer only.
   Required, from the same day ("the tools page looked like it had no design, I could not tell what was clickable",
   "every page must be worked through", "an ordinary person will not understand many skills"):
   - anything clickable must look clickable: a green underline on the name, a hover state on the whole row or tile;
   - flat does not mean bare: every page needs a designed first screen and a clear visual order;
   - jargon gets a plain line next to it (`skills_info.py` holds one for every skill: add a line when you add a skill).
   Copy: no rhetorical-question headlines ("Tired of…?"), no formula pairs ("X is easy to write and hard to check"),
   no "No X, no Y, no Z" triads, no claim we cannot back with our own data, no repeating the same figures in a sentence
   and in a row of numbers on one page. Say the problem as a plain statement, then the fact, then what the page does.
6. Do not copy text or designs from other sites. Original features are preferred over imitations.
7. Nothing that needs a server exists yet (accounts, payments, email). Do not fake it: no forms that go nowhere.
8. No spam, no fake accounts, no posting on third-party sites, no contacting companies or people on the owner's behalf.
10. Copy sells the problem, not the product (owner, 2026-11-12). Headline and first lines name the visitor's pain, then proof
    from our own data, then what we do about it. Real problems and real numbers only: nothing invented, no fake urgency.
11. Everything must work by itself: no "write to us and we will set it up" flows. A purchase is made in the buyer's account and
    takes effect at once. The contact is a fallback for questions, not a step in any process. Until the server exists, pages say
    plainly that self-serve is not open yet.
9. GitHub Pages limit is 1 GB. Check the built size (`du -sh site`) and do not add page types that push it past 800 MB.

## The look since 13 Nov 2026 (owner's decision; do not go back to the paper look)

- The owner asked many times for the look of the sites he sends (Rezi first): light, large, rounded, the product on show.
  The last block of `assets/style.css` ("The look since 13 Nov 2026") overrides the older paper-and-rules styles: white
  background, Inter for headings, pill buttons (the main button is green), `.jobs`, `.tiles li`, `.dirb`, `.pic`, `.tcard` as
  rounded cards with `--shadow`, `.sec-head` without the black rule and with a pill link.
- Home hero (`.hero.v2`): centred headline, pill search, shortcut chips, `.hstats` (four numbers), `.shot` (a framed window
  with today's jobs and `.scard` doors beside it), logos as pills. Do not put a `<nav>` inside the page body: the mobile
  menu styles catch it.
- New components must follow this look: cards with a 12–16px radius, one green accent, large type, a picture or a product
  view before text. `DESIGN_STUDY.md` describes the earlier direction; where they differ, this section wins.

## Resume examples (`resume_examples.py`, `/resume/examples/`)

- One page per live role (not the broad ones, not "-speaking"), built in `build.py` just before the guides. The example is an
  invented person and the page says so. `data/resume-examples.json` holds every example in the resume builder's own shape;
  `/resume/?example=<role>` loads it (it asks before replacing a resume already in the browser).
- Every role has its own entry in `ROLE`: title, plain skills, four lines. A new role without an entry gets its field's lines
  and the build prints a line about it: write the entry. `python3 resume_examples.py` checks the entries.
- A tool gets into a line only through a typed place (`{lang:Python}`, `{crm:the CRM}`): the first skill of that kind that
  postings for the role name, else the word after the colon. Putting the role's top tags into free places produced lines like
  "designed a housing in Python"; do not go back to that.
- The collector's tags are technical. For roles in `TECH` they lead the skills line and the chart. For other roles a tag
  mostly describes the employer, so only office tools (`OFFICE`) are counted and the page says postings name duties, not tools.

## Ideas not done yet

- Deploy `server/` to Cloudflare (owner's logins needed). Then: Plus (email alerts need an email service; AI resume tailoring, cover letters and interview prep with a monthly allowance per plan; the device sync endpoint already exists).
- More sources: other applicant tracking systems (Workable, SmartRecruiters, Recruitee, Teamtailor).
- Compare page (two skills or two companies side by side), monthly hiring report page.
- Mobile apps and a browser extension are planned by the owner after the site.

## Flags (owner's rule, 13 Nov 2026)

A country name in a list, tile, heading, table or job card is never printed without its flag. In `build.py`: `fl(code)` for an ISO code,
`pfl(slug)` for a place page (a city gets its country's flag, a region a globe), `path_fl(path)` for a link to `locations/…` or
`crypto/in/…`, `loc_flags(location)` for a job's location line. `tile()`, `listing()` headings, the salary `table()` and the crypto
directory add the flag by themselves from the path. In `site.js`: `flag(code)` and `flags(codes)`; row[24] of the job index holds the
country codes. Not in running prose and not in meta titles. Chrome on Windows cannot draw flags: `site.js` turns `i.fl` into a
two-letter badge (`.fl.cc`).

## Categories and icons (13 Nov 2026)

`collect.py` `CATS` has 18 categories plus Other. The six added on 13 Nov 2026 stand after the older ones on purpose, so a title that
already had a category keeps it. `classify(title, dept)` falls back to the employer's department (`DEPT_CATS`) when the title names no
field. Every category and every field on `/categories/` has an icon: `ICON` (drawings) and `SLUG_ICON` (slug to drawing) in `build.py`;
`tile()` and the directory block add it by themselves. A new category or field needs an entry in `SLUG_ICON` and in
`skills_info.CATEGORIES`.

## Hosting limit: gone (15 Nov 2026)

GitHub Pages' 1 GB limit held the site back until 14 Nov 2026 (one job cost about 30 KB of pages). The site is now served by our own
server from the job records (`data/jobs.db`), GitHub Pages only holds the redirects from the old address, and the workflow's step
"Check the site fits the hosting limit" (and its rebuild with `HRN_PAGE_CAP=1`) was removed on 15 Nov 2026. `LIST_PAGES` stays at
one page a list by the owner's choice of 14 Nov, not for size. Every board of `sources_candidates.json` that still answers is now
read: 2,994 in `sources_more.json` since 14 Nov and the remaining 608 since 15 Nov (entries with `"added": "2026-11-15"`; 25 were
left out as companies already read under another board or name).

## Sources and hiring systems (15 Nov 2026)

- `collect.fetch_feed` reads Greenhouse, Lever, Ashby, Workable (the careers widget's feed, one request a board, with the text),
  Recruitee (`/api/offers/`), Teamtailor (`/jobs.rss`), Personio (`/xml?language=en`), Workday (the `cxs` JSON of the careers site:
  20 postings a request, then one request per new posting for its text, at most `DETAILS` a board a read) and SmartRecruiters (the
  Posting API, same two steps). Tokens: Workday `<tenant>.<wdN>/<site>`; Teamtailor and Personio a subdomain or a whole host.
- `sources_ats.json` lists the boards on the newer systems (made by `discover_ats.py`, which verifies each board with the same
  `fetch_feed`; `--names` names Workday and Personio boards again). It and `sources_more.json` are read in turn by the hourly run
  (`collect.ROTATING`, `HRN_ROTATE`: every 4 hours; Workday and SmartRecruiters, `collect.SLOW_ATS`, every 8); `live.py` reads every
  file every hour. A new Workday board enters the hourly record `DETAILS` (40) postings per read, newest first; `live.py` reads the
  text of at most 5 new postings per board and read (`HRN_LIVE_DETAILS`), so it shows fresh jobs and leaves the backlog to the run.
- `"hold": true` on a board: verified but not read by `collect.py` or `live.py`. On 15 Nov 2026 the 328 Workday boards with more
  than 200 jobs (192,000 jobs) were put on hold, except 25 large shift-work employers: the hourly build costs about 3.8 ms per job
  record in GitHub Actions, and with them the run would no longer fit in its 45 minutes. Lift holds once the build runs on the
  server or is incremental (`ATS_REPORT.md`).
- No SmartRecruiters board is listed: `api.smartrecruiters.com/robots.txt` allows only LinkedIn's crawler. The fetcher is there for
  the day SmartRecruiters agrees. Workday boards are kept only where the tenant's robots.txt lets crawlers in.
- Only English postings are kept from the newer systems (`collect.english`, checked before a posting is parsed).
- Speed: a run no longer parses every posting. Each record keeps a fingerprint of the feed's data (`"h"`), and an unchanged posting
  keeps its record (`reuse` in `collect.main`); a change to `collect.py` changes every fingerprint once (`RULES`). What is parsed is
  parsed in one worker process per CPU (`collect.PARSE`). `live.py` skips postings the site already has (`Live.skip_known`).
- Politeness per system: `collect.ATS_LIMIT` (boards at once) and `collect.ATS_GAP` (seconds between requests; per tenant on Workday).

## Job markup rules (14 Nov 2026)

- Every open job's JobPosting has `validThrough` = today + 30 days (`VALID_TO`); the site is rebuilt hourly and a closed job loses
  its markup, so the date is always in the future while the job is open.
- A remote job gets `applicantLocationRequirements` from the countries its location names, or from a region word through
  `REGION_LANDS` ("EMEA", "Europe", "North America", "APAC", "LATAM"). A remote job that names no country and no region
  ("Remote", "Global", "Worldwide") gets NO markup at all (`mark_ok`): never guess a country. Its page is still indexed.
- Location parts like "Remote" or "EMEA" are not written as a Place address (`NOT_A_PLACE`).
- Search Console's JobPosting warnings (22 Nov 2026: postalCode, streetAddress, addressRegion, baseSalary, employmentType) are answered only with
  what the posting states: `pay_ld()` (any stated pay, its currency and unit; never `EST`), `etype_ld()` (the feed, the title, a label in the text,
  or "full-time" with no other kind of work named), `abroad_addr()` ("City, Region, Country"), `us_street_addr()` (a US place written with a ZIP).
  No hiring system's feed gives a street or ZIP, so those two warnings stay on most pages; never fill them from a map or a company's head office.
- No section heading is just "Questions": write what the questions are about (the owner's standard: every H2 carries a key or a
  real question).
- The XML feed for job search engines (`job_feed.py`, 26 Nov 2026, documented on /feeds/#xml) takes its description, places and kind
  of work from the same functions as the job page (`page_desc()`, `job_addresses()`, `etype_ld()`): change those and both change. Files
  of 50,000 jobs (`feeds/jobs-N.xml` and `.xml.gz`), `feeds/index.xml`, and `feeds/jobs.xml` = part 1. On the full record it is several
  GB and a few minutes of the build: keep the per-job work cheap (word tests before patterns) and never build a part in memory.
  `python3 job_feed.py --test` must pass; check.py reads every file back. The build has the full text only of postings of the last
  14 days (collect.DESC_SINCE): 177,665 of 777,901 open jobs on 26 Nov 2026. The rest have their text only in the server's texts.db.



## Accounts, job alerts and employer posting on our own server (15 Nov 2026, `server/`, 1,159 tests, not installed yet)

- The owner: "we need to collect a database of employers and users". `server/prod.mjs` runs `src/worker.js` on Node 22 on the Hostinger
  server (127.0.0.1:8787, service `hrn-api`, user `hrnapi`, code `/opt/hrn-api`, database `/var/lib/hrn-api/api.db`, settings and secrets
  in `/etc/hrn-api/api.env`; never under `/srv/hrn`, which the user `hrn` owns and could swap things in).
  `server/hosting/api-setup.sh` installs or updates it; the steps, the owner's password command and the way back are in `HOSTING.md`
  ("The API on the same server"). It replaces the Cloudflare plan; the worker still runs on Cloudflare if ever wanted.
- Payments stay off until `PAYMENTS_LIVE=1` is in `api.env` (the owner, last). `PAY_MODE=test` is refused on the server.
- Mail: `server/src/mail.js`, an SMTP client written on `node:tls` (no packages) for smtp.beget.com:465 from support@: daily cap
  (`MAIL_DAILY_CAP`, alerts stop at 80%), retries, a log without subjects or texts. The mailbox password is typed by the owner on the
  server (`api-secret.sh SMTP_PASS`); never ask for it, never write it anywhere.
- Job alerts (`server/src/alerts.js`, `server/alerts.mjs`, `hrn-alerts.timer` hourly): double opt-in, at most 20 jobs a letter, one-click
  unsubscribe (RFC 8058 headers), no images or tracking, matching the search page's own filters against `data/jobs.db`. The form is
  `alert_form()` in `build.py` (search, category and location pages) and a small block at the end of `assets/site.js`; it is shown only when
  `config.json` `api_url` is set. Keep the form small: its look belongs to the design work, its rules to `server/`.
- Employers: before a job is posted the worker asks `serve.py`'s `/api/check-duplicate`; a duplicate is refused with where it is and an
  offer to claim the company page. "Claim your company page" (`/api/claims`) verifies at once when `logos.json` knows the company's site
  and it is the account's domain, otherwise the owner decides (`/api/admin/claims`). Claimed companies get views and clicks per job page.
- `/privacy/` and `/terms/` have sections for alerts and accounts that appear in the same build as the forms (`api_on` in `build.py`).
  If the server starts keeping anything new, the privacy page must say it in the same change.
- The resume database (`/api/talent/...`, off until `TALENT_DB=on`): opt-in only, with the exact consent line stored; employers see no
  name or contacts until the person accepts their request; delete is immediate and total. Never fill it from anywhere but the person's
  own tick (no imports from other sites). Its privacy and /promise/ text switch on with `"talent_db": true` in `config.json`.
- The site's pages do not call `/api/public/hit` yet, and the account page has no claim form or stats yet: `server/README.md` lists what
  each page needs.

## Owner's standing rules found by the full message audit (14 Nov 2026, `MESSAGES_AUDIT.md`)

- "Не спрашивай, стоит ли внедрять, просто внедряй" (said 3 times): implement without asking anything that needs no account,
  money, password or message sent in his name.
- He does nothing himself ("ты продаёшь, а не я"): list only the steps that can be done solely in his name, each with minutes.
- One site, not a network of sites, and no other niches until this one earns (his own "не хотел бы распыляться", 12 Nov).
- Most repeated across his 140 messages: the domain (14 times), "do not stop" (11), world-class design (about 11), "take the best
  from every site" (9), first place in Google (7). Read `MESSAGES_AUDIT.md` before planning a run.

## Jobs map (14 Nov 2026)

`/map/` is built in `build.py` (search for "The jobs map"), drawn by `assets/map.js` with MapLibre GL 4.7.1 from unpkg and the free
OpenFreeMap "positron" style. `data/map.json`: `c` = cities `[key, name, country, lat, lng, address of its list]`, `n` = open jobs
per city, `ix` = city of each row of `data/index.json` (same `order(active)`; -1 when the location names no city we know). City
positions live in `geo_cities.py` (run it to check them); ambiguous names (Cambridge, Newark, Lancaster…) are left out on purpose.
The dots appear on `style.load` from `n`; the job index loads after, for search and the city panel. The city list under the map is
plain HTML, so the page is readable without the map.

## Content pages copied from the Rezi study (14 Nov 2026)

- `/resignation-letters/` from `resignation_pages.py` (18 situations) and `/resume-words/` from `resume_words.py` (19 verbs). Both
  modules have a `test()`: run them after any edit. Texts are written for this site; example resume lines are invented, never taken
  from a real resume. New entries need the same fields and must pass the test.
- Job pages link to `/tools/resume-match/?job=<slug>`; the tool reads the posting from the job page in the browser.

## Employer and career-change pages, comparisons (14 Nov 2026)

- `/cover-letter-examples/`, `/job-descriptions/`, `/how-to-become/` are built in `build.py` from `rex_data` (the resume examples) and
  today's postings of each role; every figure on them is counted at build time. Job description templates are written for this
  site; never paste text from a posting into them.
- `/vs/` reads `compare_sites.py`: every fact about another site carries a tagged source `(fact, url, date read)`; a site with fewer
  than 4 sourced rows gets no page. Re-check the facts (prices change) before relying on them; `NOT_SOURCED` lists the gaps.
- `compare_tools.py` (26 Nov 2026) holds the other products beside two of our tools: AI interview practice tools on `/interview-practice/`
  and cover letter generators on `/tools/cover-letter/`. Every cell was read on the product's own pages on `READ` (the page shows the
  date and the addresses under each name); a product with fewer than 4 stated cells gets no row; where a product's own pages
  disagree the cell says both. Our row is written in build.py / tools_pages.py from what our code does. Re-read before relying on it.
- `trade_training.py` (26 Nov 2026): the training route, typical education, license and 2025 median pay of ten trades, from the BLS
  Occupational Outlook Handbook, for the table on `/jobs-that-pay/25-an-hour/`; the open postings and their pay are counted at build.

## Glossary and the checker (14 Nov 2026)

- `/glossary/` is built from `glossary_terms.py` (run it to test). Each term: definition, what to do, links (all must exist on the
  site), and an optional figure from `gfig` in `build.py`. The index keeps the old `#anchor` ids.
- Read the whole output of `check.py`, not only a count of "FAIL": broken internal links are reported per template as
  "broken internal link: N". On 14 Nov 17 of them went out unnoticed for a few hours.
- Anything that runs a regex over the full text of postings must read each posting once (see `iq_hit` in `build.py`): a loop
  of 140 roles x 7,000 descriptions x 20 patterns added 10 minutes to the build.
- `/interview-questions/` and `/how-to-hire/` exist for every role with a resume example and 20 open postings, the same set
  as the job description templates. Role pages link all of them in the "Prepare" row only under that condition.

## Resume builder data, closing statistics, the lifespan study (14 Nov 2026, evening)

- Several resumes: the open one stays in `hrn_resume` (other pages read it); the others wait in `hrn_resume_set`
  (`{cur, items: [{id, label, data, jd}]}`; the current item carries no `data`). An example or an import never replaces a resume in
  progress: it opens as a new item. New sections `proj`, `cert`, `lang` are lists; `fill()` in `assets/resume.js` repairs old or
  damaged values. JSON Resume in and out is `HRNT.toJsonResume` / `HRNT.fromJsonResume` (tested in `tools_test.js`).
- A whole job board that empties in one run is a move to another hiring system, not filled jobs (Shield AI, Lever → Ashby, 13 Nov:
  673 postings). `build.py` (`MOVED`) leaves such closings out of `survival.json` and every closing figure; `collect.py` lists them
  as `emptied` in `data/stats.json` and `/status/` shows them. When one appears, find the company's new board and update the source.
- `/how-long-job-postings-stay-open/` states measured counts first; the estimate's reach grows with the record (`reach`: 30 days
  while the record is under 30 days, 90 under 90, then 180) and says "early" for the first two weeks. Do not show longer horizons
  sooner: on 14 Nov three days of closings projected 2% of postings alive at 180 days while 33% of open jobs were over 90 days old.

## The brand (15 Nov 2026; `brand.py`, `/brand/`, `/brand/directions/`, `/media-kit/`)

- Owner: "a corporate design of our own, like Indeed". Direction in use: **Evergreen** (key `green` in `brand.py`): the site's own
  green. Persimmon (orange-red) was applied for a few hours on 15 Nov and rejected by the owner ("the site is green, why is the brand
  red?"): never bring red or orange back as the brand colour; the orange `--viz-2` stays only in charts. Mark: a clock at 17 past the
  hour (the minute the hourly run reads the careers pages). Type: Schibsted Grotesk (headlines), Public Sans (text and numbers,
  `font-variant-numeric: tabular-nums`), JetBrains Mono only for code (`--code`). Inter stays only for the resume paper and its
  templates. All fonts OFL, self-hosted, from Fontsource. Buttons are ink on light pages and paper on dark pages; green is the
  marker under words, the line under links and the mark, never a large fill or a green block on black.
- `brand.py` holds the directions (Evergreen in use; Persimmon, Berry, Brick and sand as alternatives) and draws every logo file into `assets/brand/` with the
  letters as outlines (`python3 brand.py`, needs `pip install fonttools brotli`; `--test` checks contrast without packages). To
  switch direction: set `"applied"` in `brand.py`, update the tokens in `assets/style.css` (search "--brand"), run `python3 brand.py`
  and `python3 og.py`. The build only copies `assets/brand/`.
- Tokens: `--brand` (the mark), `--ac` (buttons, link lines), `--ac-ink` (text on `--ac`), `--btn` (the dark button; light in dark
  mode), `--hl` (tint under one phrase). No large coloured areas: the brand colour marks the one thing that matters.
- Media kit pictures (`assets/brand/screen-*.jpg`, `banner-*.png`, the 96 px PNG mark for email signatures) are made with
  Playwright from the built site; redo them after a visible change of the home, search or resume builder pages.
- Email addresses: plain `mailto:` links through the department helper in `build.py` (`MAIL`); Cloudflare hides them from scrapers.
- How often pages are read: the boards in `sources.json` and `sources_tech.json` every hour, the ~3,000 in `sources_more.json` every
  four hours (`HRN_ROTATE`). `build.py` counts both (`m_hourly`, `ROTATING`, `EVERY`) and the home page, media kit, widget answer and
  dataset description say it exactly. Other pages that say "every hour" (job pages, methodology, status) need the same care.

## Build speed, company lists, the collector on the server (17 Nov 2026)

- **Where a build's time goes.** `build.py` ends with a line `slowest stages: …` (the `lap()` calls stand before the commented
  blocks of `main()`; a stage runs until the next `lap`). Read it in the GitHub log of a run on the full record (220,000 jobs):
  the local record is a fifth of it and hides what grows with jobs times roles or places. On GitHub the same build varies by up to
  1.7 times between runs (different machines): compare the "Check pages" step of the same run before judging a change.
- **Cheap tests before expensive ones** (all four passes of 17 Nov, the build went from about 10 minutes to 2.5 locally):
  `rx_needs(pattern)` reads a regex and returns the words a text must have for it to match; `role_slugs()` runs a role rule only
  on titles that have them; `rx_skip([regexes])` does the same for regexes that read whole descriptions (`have(text)`, then
  `may[i](have)`); `same_case` / `low_of` say when lower-casing is not safe (ı, ſ, Greek) and then nothing is skipped.
  `by_place(js)` and `by_kind(js)` sort a page's jobs into places and kinds of work in one pass; `HUB["job_roles"]` is job id ->
  role slugs. When adding a page family, never write "for every role: the jobs of this page that are in the role".
- **How such a change is checked:** the result must be the same pages. Keep a fingerprint of every built page except job pages
  with clock times taken out, build again, compare; the few pages that differ should all hold one posting whose age ("6 days ago")
  changed between the two builds. For matching rules, compare with the plain way on every title or description of the record.
- **Company lists** (`/companies/sp-500/`, `/nasdaq-100/`, `/unicorns/`, `/y-combinator/`): who is in a list is in
  `company_lists.json` (from Wikipedia, CC BY-SA 4.0, credited on the page with the date read; matched to our company names by
  hand, name-only look-alikes removed: Co–Star is not CoStar Group, Flex is not Flex Ltd.). A new list is an entry there plus a
  tuple in `CO_LISTS`; a page is built when 5 of its companies have open jobs. Fortune's and Forbes' rankings are their own
  work: do not copy them.
- **Boards on hold** (`"hold": true` in `sources_ats.json`): 254 large Workday boards, 143,733 jobs. 74 well-known ones were
  released on 17 Nov (`"lifted"`). Release more only after reading the stage line of a run on the full record, and watch the
  memory of `hrn-live` on the server (1.9 GB of its 3 GB limit at 216,000 jobs; the server also runs another site).
- **`live.py`**: reads the jobs employers posted in the account every 2 minutes (`direct`), reopens a job it had closed when the
  board lists it again (`reopen`), does not close closed jobs again after a new record, and reads 15 texts a board on each pass
  (Workday, SmartRecruiters). It restarts by itself when the upload brings new code.
- **The workflow**: a push builds from the saved jobs unless they are more than three hours old (`STALE`), then it collects too.
- **Memory of the run** (22 Nov 2026): GitHub's runner has 16 GB. When it runs out, the step ends with exit 143 or "The operation was
  canceled" and no message. At 1.95 GB of `data/jobs.json` the old one-string save in `collect.py` did that every run; `save_db` streams it.
  Never build the whole database as one string or one list of pieces (`json.dumps(db)`) in `collect.py` or `build.py`.
  GitHub starts scheduled runs 4 or 5 times a day whatever the cron lines say. A lasting fix needs a GitHub token on the server
  to start runs from there, and that is a secret only the owner can create and type in.
- **`views.py`** (on the server: `sudo python3 /srv/hrn/app/views.py 14`): how many times people, not robots, opened each
  company's job pages, from the nginx log. Nothing new is recorded about visitors. On 17 Nov: 290 opens by people in 4 days against
  341,813 requests by robots (GPTBot, ClaudeBot, Amazonbot), and Googlebot had only just found the home page: Search Console is
  the owner's decision to do last, do not push it.
- **Tools' result board** is a light card that follows the theme (`.tl-board` in `assets/tools.css`): no green type on black
  anywhere; the owner dislikes it.

## The server on 18 Nov 2026: an outage from outside, and the page service's memory

- 02:55 to 03:17 UTC the site answered 522. The virtual machine was cut off and started again from outside: the journal of the previous
  boot ends mid-work with no shutdown lines and no out-of-memory kill, memory stood at 60% and load at 1 to 2. Every service came back by
  itself. When this happens again: check `uptime`, `last -x | grep boot`, `journalctl -b -1 | tail` before suspecting our own programs.
- `hrn-site` (serve.py) has `MemoryMax=1G`. It held up to four whole records for every company and field (about 100,000 at 225,000 jobs)
  and stood at the limit; systemd killed and restarted it about five times a day, mostly at uploads. Since 18 Nov those records are read
  on demand (`records.Cards`). If the count of jobs doubles, look at its memory again: `systemctl show hrn-site -p MemoryCurrent` and
  `grep -E "^(anon|file) " /sys/fs/cgroup/system.slice/hrn-site.service/memory.stat`.
- `hrn-live` stands at about 1.9 GB of its own memory (limit 3 GB) with 1,479 boards. The server has 7.9 GB and no swap. Lifting the hold
  from more boards must be done in parts with this figure watched.
- Search and AI answers check: the working notes are in `SERP_AI_CHECK.md` (queries, what Google, Bing and Claude's search show, the gap
  for each page). A helper's gap list is a lead, not a fact: several named things our pages already had. Check each against the page.
- For the cloud run: content gaps from `SERP_AI_CHECK.md` that need no template change and suit one run each (check the page first, as always):
  (1) `builders_check.py`: add Teal, Canva, Adobe Express, Zety, MyPerfectResume and Resume-Now, each from its own pricing or help pages, the way
  the first eleven were read; (2) more interview questions with a model answer for the most common roles (SQL, statistics, business cases for
  analysts; the first results carry 50 to 80, we carry 26); (3) resume example variants (junior, senior) for the largest roles.
  Template changes for the other gaps are made in the main session: leave `build.py`'s list, company and place templates alone.

