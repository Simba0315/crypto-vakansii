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

## Done on the server (14 Nov 2026, with the owner's go-ahead)

- `setup.sh` without a domain: user `hrn`, `/srv/hrn/app`, service `hrn-site` (running, 127.0.0.1:8790, about 100 MB), the upload
  key in `/srv/hrn/.ssh/authorized_keys` limited to `rrsync /srv/hrn/app` (checked: it cannot run commands). The key's private
  half is `~/.ssh/hrn_deploy` on the owner's Mac.
- The site and the records uploaded once from the Mac with that key (16 s); every page, job pages from records, `/api/search` and
  `/mcp` answer on the server.
- `opensearch.sh`: OpenSearch 3.9 running, index loaded, search on Lucene. hypestkey's nginx, PHP, MariaDB and Redis were not
  restarted (running since 06:39 UTC that day) and hypestkey answers as before.
- Waiting: the domain's DNS at Cloudflare (then nginx and the certificate: `setup.sh` with `DOMAIN=`), and the three GitHub
  secrets for the hourly upload.

## The parts

| File | What it does |
|---|---|
| `records.py` | writes `data/jobs.db` (table `jobs`: one row per job; table `ctx`: what every page needs from the whole build) and builds a job page from a row with the same `job_page()` the static build uses |
| `build.py` | `HRN_RECORDS=1`: records and no job pages; `HRN_RECORDS=both`: records and pages (for the test); unset: pages only, as on GitHub Pages today |
| `serve.py` | Python's own web server: `/job/<slug>/` from the records, everything else from `site/`. No packages to install |
| `records.py` search | a word index over every job in the same file (SQLite FTS5: the kind of index Lucene keeps, ranked by BM25 as Lucene does), 23 MiB, a search in 1–250 ms |
| `serve.py` `/api/search` | the search as JSON: `?q=rust remote&limit=20` |
| `serve.py` `/mcp` | a connector for AI assistants (Model Context Protocol): Claude, ChatGPT and others add the address and search our jobs in plain words (`search_jobs`, `get_job`) |
| `search_engine.py` | Lucene search through OpenSearch: index settings (synonyms, C++/C#/.NET, light English stemming), the hourly load with an alias swap, the query (exact first, typos forgiven second, facets) |
| `server/hosting/opensearch.sh` | installs and configures OpenSearch from its official repository, the index units, and points the page server at it |
| `server/hosting/hrn-index.path`, `hrn-index.service` | reload the search index whenever a new `data/jobs.db` arrives |
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
5. **GitHub (Settings → Secrets and variables → Actions), three secrets:** `HRN_DEPLOY_KEY` (the private half of that key,
   made for this only: on the server it can do nothing but rsync into `/srv/hrn/app`), `HRN_SERVER` (the server's address; a
   secret so it never shows in the public logs) and `HRN_SERVER_HOSTKEY` (the server's lines from `ssh-keyscan`, so the
   connection is checked).
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

## Search: Lucene (OpenSearch) on the server, SQLite FTS5 as the fallback

The owner, 14 Nov: "why not Lucene right away?" — so it is in place. OpenSearch 3.9 (Lucene 10.5) runs on the server for the page
server only: 127.0.0.1:9200, security plugin off because nothing outside the machine can reach it, 1 GB heap, at most 2 GB of memory
and one processor (`server/hosting/opensearch.sh`). `search_engine.py` loads every job into a new index after each upload
(`hrn-index.path` watches `data/jobs.db`, `hrn-index.service` runs the load, 42,149 jobs in a few seconds, 58 MB) and moves the alias
`jobs` to it in one step. `serve.py` asks Lucene first and falls back to FTS5 in the records file when OpenSearch does not answer.

What Lucene gives here, checked on the server on 14 Nov 2026:
- the words as typed first, honest counts ("solidity" 34 jobs; FTS5's Porter stemming had cut it to "solid" and counted 685);
- typos forgiven when the words as typed find nothing ("pyhton", "product manger", "kubernets");
- synonyms at search time ("k8s" finds Kubernetes, "js" JavaScript), word families ("engineering" finds "engineer");
- counts for the filters with every search (remote, hybrid, level, field, top companies) in the `facets` of `/api/search`;
- answers in 20-60 ms.

## Later on the same server

- The accounts and crypto payments API (`server/src/worker.js`) runs on Node 22 with the built-in SQLite, as `server/dev.mjs` already does
  here; it needs a production starter and its secrets (NOWPayments) set on the server, not in the repository.
- More pages from records the same way: companies (115 MiB), locations (195 MiB), roles (109 MiB) are lists of jobs too.
