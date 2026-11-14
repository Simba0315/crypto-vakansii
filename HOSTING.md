# Hosting: job records on our own server

Decided 15 Nov 2026 (the owner: "at Indeed records are pulled up, so we should have records too"; "hypestkey is on Hostinger, decide").

## What changes

| | Now: GitHub Pages | Next: the Hostinger server |
|---|---|---|
| A job page | one HTML file per job, 42,149 files, 547 MiB | one row in `data/jobs.db` (SQLite): 118 MiB for all of them, 141 MiB with the word index; the page is built when it is opened, in 1.3 ms |
| The rest of the site | files, 323 MiB | the same files, 323 MiB: with the records the whole site is 464 MiB instead of 870 |
| Size limit | 1 GB, the build already trims pages to fit | the server's disk, 96 GB, shared with hypestkey |
| Selling | not allowed on GitHub Pages ("not for online business") | allowed: it is our server |
| Who builds | GitHub Actions, every hour | still GitHub Actions; the server only serves |
| Cost | 0 | 0 more: the server is already paid for hypestkey |

This is how large job sites keep postings: Indeed's Docstore keeps each job as a record and the page is put together from it when someone
asks. A record holds the facts of the job (title, company, place, pay, dates, text); the page around it (header, footer, the similar jobs,
the medians of its field) is added at that moment. One record per job is about five times smaller than one page per job, and a new job is one
new row, not one more file to upload.

## The server

Hostinger VPS `srv2127103`, the one hypestkey runs on: 2 vCPU, 8 GB RAM, 96 GB disk, Ubuntu 24.04, nginx 1.24 (from
`~/hypestkey-site/docs/server.md`). Hiring Right Now gets its own user (`hrn`), folder (`/srv/hrn`), service (`hrn-site`, at most 1 GB of memory
and 60% of one processor) and nginx site. It does not touch hypestkey's files, database, PHP or Redis. If the site outgrows the shared
server, the same three files move it to a server of its own.

## The parts

| File | What it does |
|---|---|
| `records.py` | writes `data/jobs.db` (table `jobs`: one row per job; table `ctx`: what every page needs from the whole build) and builds a job page from a row with the same `job_page()` the static build uses |
| `build.py` | `HRN_RECORDS=1`: records and no job pages; `HRN_RECORDS=both`: records and pages (for the test); unset: pages only, as on GitHub Pages today |
| `serve.py` | Python's own web server: `/job/<slug>/` from the records, everything else from `site/`. No packages to install |
| `records.py` search | a word index over every job in the same file (SQLite FTS5: the kind of index Lucene keeps, ranked by BM25 as Lucene does), 23 MiB, a search in 1–250 ms |
| `serve.py` `/api/search` | the search as JSON: `?q=rust remote&limit=20` |
| `serve.py` `/mcp` | a connector for AI assistants (Model Context Protocol): Claude, ChatGPT and others add the address and search our jobs in plain words (`search_jobs`, `get_job`) |
| `records_test.py` | builds every job page from its record and compares it with the file the same build wrote: must end with `0 different` |
| `check.py` | in a site without job files, samples job pages from the records and counts a link to `/job/<slug>/` as good when the record exists |
| `server/hosting/setup.sh` | one-time setup on the server, as root: user, folder, service, nginx site, certificate |
| `server/hosting/hrn-site.service` | the systemd service for `serve.py` |
| `server/hosting/nginx-hrn.conf` | nginx: files from `/srv/hrn/app/site`, `/job/` from `serve.py`, each job page kept 5 minutes |

## Try it on this machine

```
HRN_RECORDS=both python3 build.py && python3 records_test.py     # 0 different
HRN_RECORDS=1 python3 build.py && python3 check.py               # no job files; job pages checked from the records
python3 serve.py                                                 # http://localhost:8790/crypto-vakansii/
```

## Moving the site: the order (owner, 14 Nov: "let's move to the hosting"; Cloudflare allowed if needed)

Who does what: **owner** = only the owner can (money, his accounts, keys); **me** = done from this repository, or on the server
once the owner allows it.

1. **Owner:** buy `jobseveryhour.com`.
2. **Owner:** add the domain to Cloudflare (free plan) and set the two Cloudflare name servers at the registrar. Cloudflare then
   holds the DNS, keeps copies of the pages near visitors, stops floods and bots, and hides the server's address, which hypestkey
   shares. hypestkey is already behind Cloudflare.
3. **Owner, in Cloudflare DNS:** `A @` and `A www` → the server's address, proxied (orange cloud). SSL mode "Full (strict)".
4. **Me, on the server, with the owner's go-ahead:** `DOMAIN=jobseveryhour.com DEPLOY_KEY="<public half of a new key>" bash
   server/hosting/setup.sh` as root: user `hrn`, folder `/srv/hrn`, service `hrn-site`, nginx site, Let's Encrypt certificate,
   Cloudflare's address lists for the real visitor address. Nothing of hypestkey's is touched.
5. **Owner, in GitHub (Settings → Secrets and variables → Actions):** secret `HRN_DEPLOY_KEY` (the private half of that key,
   made for this only: on the server it can do nothing but rsync into `/srv/hrn/app`) and variable `HRN_SERVER` (the server's
   address). Optional variable `HRN_SERVER_HOSTKEY` (the server's line from `ssh-keyscan`) so the first connection is checked too.
   From the next hourly run the workflow builds the records as well and uploads the site to the server (step "Upload to our
   server"); GitHub Pages keeps working the same until the switch.
6. **Me:** check the site on the server (pages, job pages from records, search, the MCP address), then switch:
   `config.json` `base_url` `https://jobseveryhour.com`, `base_path` empty; the workflow builds `HRN_RECORDS=1` (no job pages) and
   GitHub Pages becomes a set of redirects to the new address (one per old page, with a canonical link), so search engines move
   their ranking over.
7. **Owner:** Google Search Console and Bing Webmaster Tools for the new domain; I add the codes they give to `config.json`.

### Email

- **Mailbox (hello@, support@):** Beget mail is fine for a mailbox people write to: MX, SPF and DKIM records go into Cloudflare
  DNS. A free alternative with no new account: Cloudflare Email Routing forwards hello@jobseveryhour.com to an existing inbox
  (receiving only; replies would come from that inbox).
- **Mail the site sends (job alerts, sign-up links):** not from a mailbox. A sending service made for it (Amazon SES, Postmark,
  Resend, Brevo) keeps the letters out of spam with SPF, DKIM and DMARC and counts bounces. Needed only once alerts by email and
  accounts go live; the key is the owner's and goes into the server's settings, not into the repository.
- Beget is a Russian company: the privacy page will name where mail is kept.

## Search: SQLite FTS5 now, Lucene when it pays off

Lucene itself is free (Apache licence), but it is a Java library: on a server it runs inside OpenSearch, Solr or Elasticsearch, a
Java service that wants 1–2 GB of memory of its own on the shared 8 GB server. FTS5 keeps the same kind of index (for every word, the
jobs it is in) and ranks with the same BM25 formula, inside the file the pages already come from, with no service to run. What
Lucene adds: typo-tolerant search, synonyms, facet counts ("Remote 812, Berlin 77") computed with the search, "more like this",
search by distance. Moving later changes only `records.Store.search` and the build step that fills the index; the pages, the
`/api/search` answer and the MCP tools stay the same. The point to move: about a million jobs, or when typo-tolerant search and
facet counts are wanted on the server rather than in the browser.

## Later on the same server

- The accounts and crypto payments API (`server/src/worker.js`) runs on Node 22 with the built-in SQLite, as `server/dev.mjs` already does
  here; it needs a production starter and its secrets (NOWPayments) set on the server, not in the repository.
- More pages from records the same way: companies (115 MiB), locations (195 MiB), roles (109 MiB) are lists of jobs too.
