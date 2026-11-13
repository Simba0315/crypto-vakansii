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

## Ideas not done yet

- Deploy `server/` to Cloudflare (owner's logins needed). Then: Plus (email alerts need an email service; AI resume tailoring, cover letters and interview prep with a monthly allowance per plan; the device sync endpoint already exists).
- More sources: other applicant tracking systems (Workable, SmartRecruiters, Recruitee, Teamtailor).
- Compare page (two skills or two companies side by side), monthly hiring report page.
- Mobile apps and a browser extension are planned by the owner after the site.
