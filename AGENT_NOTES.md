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

## Local work

```
git fetch origin data && mkdir -p data && git show FETCH_HEAD:jobs.json.gz | gunzip > data/jobs.json   # fast; do not run collect.py locally unless needed
python3 build.py && python3 check.py        # must end with every template OK
python3 -m http.server 8765 --directory <a folder that contains site/ as crypto-vakansii/>   # pages use the /crypto-vakansii prefix
```

Push with the deploy key already configured in this clone (`core.sshCommand`). Always `git pull --rebase origin main` first.

## Rules from the owner (do not break)

1. Every page must pass his "perfect page" standard: SEO, GEO/AIO, AEO, E-E-A-T, mobile. Title: key first, brand last, about 60
   characters. Unique description 110–160 characters. One H1. H2s carry the topic or a real question. Direct answers in the
   first 40–60 words under a question. FAQPage markup only where the FAQ is visible. Dates and sources visible. No invented
   people, credentials, reviews, numbers or partners.
2. English-language market. Payments in crypto only for now (cards later). Never touch wallets; only public receiving addresses
   from the owner go into `config.json`. Do not change prices, wallets or contacts in `config.json` on your own.
3. Closed jobs stay as archive pages.
4. Real company logos only, from the company's own site.
5. Design: the "Signal" identity (warm paper, ink, one lime accent, mono numerals, the board). Keep it consistent, distinctive
   and polished on phone and desktop. No purple gradients, no stock images, no generic "AI look".
6. Do not copy text or designs from other sites. Original features are preferred over imitations.
7. Nothing that needs a server exists yet (accounts, payments, email). Do not fake it: no forms that go nowhere.
8. No spam, no fake accounts, no posting on third-party sites, no contacting companies or people on the owner's behalf.
9. GitHub Pages limit is 1 GB. Check the built size (`du -sh site`) and do not add page types that push it past 800 MB.

## Ideas not done yet

- Server on Cloudflare (owner has an account; he said "later"): accounts, Plus payments, email alerts, 48-hour early access.
- More sources: other applicant tracking systems (Workable, SmartRecruiters, Recruitee, Teamtailor).
- Compare page (two skills or two companies side by side), salary by level tables, monthly hiring report page.
- Mobile apps and a browser extension are planned by the owner after the site.
