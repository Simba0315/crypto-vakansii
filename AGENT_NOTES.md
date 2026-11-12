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

## Marketing (owner, 2026-11-12/13: "everything that exists in marketing must be on the site")

- Problem first, proof from our own data, then the offer (rule 10). Free tools as lead magnets (`tools_pages.py`), sharing and
  embeds as distribution, price anchors and a marked best plan, clear guarantees, comparison and landing pages per audience.
- Hard limits: no invented reviews, logos of "customers", countdown timers, fake scarcity or popups that block reading.
- Backlog: `COMPETITOR_GAPS.md` (what other job sites have that we do not, with priorities). Take the highest-priority item that
  is not built yet, build it properly, tick it off in that file.

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
5. Design: the "Signal" identity (warm paper, ink, one lime accent, mono numerals, the board). Keep it consistent, distinctive
   and polished on phone and desktop. No purple gradients, no stock images, no generic "AI look".
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

- Deploy `server/` to Cloudflare (owner's logins needed). Then: Plus (email alerts need an email service, 48-hour early access, AI résumé tools, device sync endpoint already exists).
- More sources: other applicant tracking systems (Workable, SmartRecruiters, Recruitee, Teamtailor).
- Compare page (two skills or two companies side by side), salary by level tables, monthly hiring report page.
- Mobile apps and a browser extension are planned by the owner after the site.
