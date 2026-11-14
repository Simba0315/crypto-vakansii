# Hiring Right Now — notes for whoever works on this repo next

Tech job board, English, static site on GitHub Pages. Owner: Simba0315. Live: https://simba0315.github.io/crypto-vakansii/
(the repo name and the address are temporary until a domain is bought).

## How it works

- `collect.py` reads public hiring feeds (Greenhouse, Lever, Ashby) listed in `sources.json` (crypto companies) and
  `sources_tech.json` (tech companies) and writes `data/jobs.json`. Closed jobs are never deleted: `active=false` + `closed` date.
- `build.py` generates the whole site into `site/` from `data/jobs.json`, `config.json`, `assets/`.
- `check.py` checks the built site against the page standard (one H1, title/description length, self-canonical,
  heading order, alt on images, internal links). It must print OK for every template before a push.
- `.github/workflows/update.yml` runs daily (03:17 UTC) and on every push: restore the jobs database from the one-commit
  `data` branch, collect, save it back, build, deploy to Pages. `data/` and `site/` are not in `main`.
- `logos.py` finds each company's own site and saves its icon to `assets/logos/`. Only trusted addresses are used
  (hand-checked `OVERRIDE` list or `<name>.com`); a wrong logo is worse than none. Never draw or invent logos.
  When no site works, it takes the logo the company uploaded to its own Greenhouse, Ashby or Lever board (only near-square
  ones; `logos.json` then says `board:<ats>/<token>`, and the build does not use that as the company's site). A name whose
  obvious domain belongs to someone else goes into `NO_SITE` (mesh.com shows Microsoft's logo). Look at every new logo
  before publishing: put them on one page and take a screenshot.

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
- It is written and tested but NOT deployed (needs the owner's Cloudflare login and Cryptomus keys). Until `"api_url"` in
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

## Local work

```
git fetch origin data && mkdir -p data && git show FETCH_HEAD:jobs.json.gz | gunzip > data/jobs.json   # fast; do not run collect.py locally unless needed
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
5. Design: warm paper, ink, hairlines and ONE calm green (tokens in `style.css`: `--hl` green as a fill under text, `--ac`
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
   - a row of four big numbers in the hero, badge-style kickers above a headline, arrows after every link;
   - accordions for questions: questions and answers are plain text (`.qa`).
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

## Hosting limit (measured 13 Nov 2026, corrected the same evening)

The workflow stops above 950 MiB and GitHub Pages allows 1 GB. Measured on a fresh collection with 41,187 open jobs and 732 companies:
873 MiB. One more job costs about 30 KB all in (its page about 12.4 KB, the rest is its rows in lists and its company's pages), so the
room left is small. An earlier note here said "room for 10,000 more jobs": that was measured on a stale local copy with few full
descriptions and was wrong. `LIST_PAGES` in `build.py` caps topic lists at 2 pages (1 above 43,000 open jobs); the workflow builds
again with `HRN_PAGE_CAP=1` if a build is over 940 MiB. `sources_candidates.json` holds 3,852 more verified company boards (134,467 jobs
at the time): 188 of them were added to `sources_tech.json` on 13 Nov 2026 (entries with `"added"`). Do not add more until job pages
are served by the server (`server/`), which waits for the owner's domain. Measure with a fresh `python3 collect.py` before trusting a
local size.

## Job markup rules (14 Nov 2026)

- Every open job's JobPosting has `validThrough` = today + 30 days (`VALID_TO`); the site is rebuilt hourly and a closed job loses
  its markup, so the date is always in the future while the job is open.
- A remote job gets `applicantLocationRequirements` from the countries its location names, or from a region word through
  `REGION_LANDS` ("EMEA", "Europe", "North America", "APAC", "LATAM"). A remote job that names no country and no region
  ("Remote", "Global", "Worldwide") gets NO markup at all (`mark_ok`): never guess a country. Its page is still indexed.
- Location parts like "Remote" or "EMEA" are not written as a Place address (`NOT_A_PLACE`).
- No section heading is just "Questions": write what the questions are about (the owner's standard: every H2 carries a key or a
  real question).



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

## Glossary and the checker (14 Nov 2026)

- `/glossary/` is built from `glossary_terms.py` (run it to test). Each term: definition, what to do, links (all must exist on the
  site), and an optional figure from `gfig` in `build.py`. The index keeps the old `#anchor` ids.
- Read the whole output of `check.py`, not only a count of "FAIL": broken internal links are reported per template as
  "broken internal link: N". On 14 Nov 17 of them went out unnoticed for a few hours.
- Anything that runs a regex over the full text of postings must read each posting once (see `iq_hit` in `build.py`): a loop
  of 140 roles x 7,000 descriptions x 20 patterns added 10 minutes to the build.
- `/interview-questions/` and `/how-to-hire/` exist for every role with a resume example and 20 open postings, the same set
  as the job description templates. Role pages link all of them in the "Prepare" row only under that condition.
