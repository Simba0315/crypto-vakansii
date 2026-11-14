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

## Moving the site (after the domain is bought, with the owner's go-ahead)

1. Domain: an A record for `jobseveryhour.com` and `www` pointing at the server's address (the owner, at the registrar).
2. On the server, as root: `DOMAIN=jobseveryhour.com DEPLOY_KEY="<public half of a new key>" bash server/hosting/setup.sh`.
   The key is made for this only; its private half goes to the repository's secrets as `HRN_DEPLOY_KEY`, the address as the variable
   `HRN_SERVER`. On the server the key can do nothing but rsync into `/srv/hrn/app` (`rrsync`).
3. `config.json`: `base_url` `https://jobseveryhour.com`, `base_path` empty.
4. The workflow builds with `HRN_RECORDS=1` and, after the build, uploads with:

   ```
   rsync -az --delete --delay-updates -e "ssh -i key" \
     --include='/site/***' --include='/data/' --include='/data/jobs.db' --include='/*.py' --include='/*.json' \
     --include='/assets/***' --exclude='*' ./ hrn@$HRN_SERVER:/
   ```

   `--delay-updates` puts all new files in place at the end, so nobody sees half an upload; `jobs.db` is swapped in one step and
   `serve.py` opens the new one within 20 seconds. When the page code changes, `serve.py` restarts itself (about a second; nginx serves
   its kept copies meanwhile).
5. GitHub Pages: the old address sends visitors to the new domain (a page per old address with a canonical link and a redirect),
   so search engines move their ranking over.

## Later on the same server

- The accounts and crypto payments API (`server/src/worker.js`) runs on Node 22 with the built-in SQLite, as `server/dev.mjs` already does
  here; it needs a production starter and its secrets (NOWPayments) set on the server, not in the repository.
- More pages from records the same way: companies (115 MiB), locations (195 MiB), roles (109 MiB) are lists of jobs too.
