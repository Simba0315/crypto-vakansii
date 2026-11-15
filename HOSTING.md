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

## Done on 14 Nov 2026, evening: the domain

- Cloudflare (free plan): `jobseveryhour.com` A → the server, `www` CNAME → `jobseveryhour.com`, both proxied; SSL/TLS
  "Full (strict)"; AI crawlers allowed, Bot Preference Sync off (our robots.txt stays ours). Name servers at GoDaddy changed by
  the owner to `kyree.ns.cloudflare.com` and `nora.ns.cloudflare.com`; the zone is active.
- On the server: `setup.sh` with `DOMAIN=jobseveryhour.com`: Let's Encrypt certificate (renews by itself), nginx site.
  Two fixes on the way: `listen 443 ssl http2` (nginx 1.24 has no `http2 on;`; the refused config was never loaded, and setup.sh
  now takes back any config nginx refuses), and `/srv/hrn` set to 711 so nginx can reach the files.
- https://jobseveryhour.com answers through Cloudflare; www and http send to https://jobseveryhour.com.
- Switched on 14 Nov 2026, 13:40 UTC: the three GitHub secrets are set (the owner signed in to the GitHub CLI on his Mac),
  `config.json` names https://jobseveryhour.com, and the first run (43598608134) built the records site, uploaded it to the
  server and deployed the redirect site to GitHub Pages. Checked from outside: pages, job pages from records, Lucene search,
  `/mcp`, and the old github.io pages pointing at the new address.
- How the switch works, for reference: with the three GitHub secrets set, `config.json` gets `base_url` `https://jobseveryhour.com` and an empty
  `base_path`; the workflow then builds the records site for the server and, from `pages_redirect.py`, a redirect site for the
  old github.io address (one page per old address with a canonical link and a meta refresh; widget scripts and the JSON API kept).

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

**Mailboxes by department (the owner, 15 Nov: "like large companies, for different departments; not hello").** Beget, domain
jobseveryhour.com. Each box is created by the owner, who sets its password; each one forwards a copy to support@ so one inbox
sees everything. All eight created by the owner on 15 Nov 2026; `config.json` `emails` lists the ones the site shows:

| Address | For | Where it appears |
|---|---|---|
| support@ | job seekers' questions, everything else | ✅ exists; footer, about, safety |
| jobs@ | employers: posting a job, a wrong listing, removing a job | post-a-job, terms, about |
| partners@ | Telegram channels, sites with our widget, list sites, API users | partners, about |
| press@ | journalists: data requests, quotes, interviews | media kit, about |
| privacy@ | data requests (GDPR / CCPA: see, export, delete) | privacy, about |
| abuse@ | reports of scam jobs and fake recruiters | safety, about, "Report a problem" on every job page (the subject names the job) |
| adam@ | letters written by a person: outreach to partners and list sites, signed with a name | not on the site |
| security@ | reports of security holes | `/.well-known/security.txt`, about |

Later, with payments: billing@. postmaster@ is kept by Beget for the domain.

Keeping the addresses out of spam lists: Cloudflare's Email Address Obfuscation is on (checked 15 Nov: on /about/ and /safety/
the address is served as `__cf_email__`, so scrapers that read the HTML do not see it, while people do). Beget's spam filter is on
for each box. Keeping our letters out of Gmail's spam: SPF and DMARC are set; DKIM is added when Beget's panel shows it, and then
DMARC moves from `p=none` to `p=quarantine`. An address goes on the site only after its box exists, so no letter bounces.

- **Mailbox (hello@, support@):** Beget mail is fine for a mailbox people write to: MX, SPF and DKIM records go into Cloudflare
  DNS. A free alternative with no new account: Cloudflare Email Routing forwards hello@jobseveryhour.com to an existing inbox
  (receiving only; replies would come from that inbox).
- **Mail the site sends (job alerts, sign-up links):** decided 15 Nov 2026: from support@ through Beget's SMTP server, with a daily cap,
  until the volume needs a sending service made for it (Amazon SES, Postmark, Brevo): see "Mail limits" below. The password is the
  owner's and goes into the server's settings (`api-secret.sh`), not into the repository.
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

## The API on the same server: accounts, job alerts, free employer posting (code of 15 Nov 2026, not installed yet)

The owner, 15 Nov: "we need to collect a database of employers and users". `server/` now runs on this server: `server/prod.mjs` is the
API (Node 22, the database in `/var/lib/hrn-api/api.db`, 127.0.0.1:8787, service `hrn-api`), `server/alerts.mjs` sends the job alerts
every hour (`hrn-alerts.timer`), mail goes out through Beget's SMTP server from support@. Payments stay off. Details: `server/README.md`
("On our own server", "Job alerts", "Claim your company page").

| | Where | Who can read it |
|---|---|---|
| code | `/opt/hrn-api/server` (a copy of the repository's `server/`) | everyone on the machine; owned by root |
| database | `/var/lib/hrn-api/api.db` (SQLite, WAL) | only the user `hrnapi` |
| settings and secrets | `/etc/hrn-api/api.env` | root and `hrnapi` |
| what it reads from the site | `/srv/hrn/app/data/jobs.db`, `/srv/hrn/app/logos.json`, `http://127.0.0.1:8790` | (uploaded every hour) |

Not under `/srv/hrn` (the place first planned for the settings, `/srv/hrn/api.env`): that folder belongs to the user `hrn`, which
runs the page server and `live.py` and receives the hourly upload, and the owner of a folder can rename anything in it, so it could swap
the API's code or settings (and with them the admin token) for its own. Code, settings and database are therefore in places only root
can change.

nginx sends only the API's own addresses to it (`server/hosting/nginx-hrn-api.conf`, included by `nginx-hrn.conf`): `/api/health`,
`/api/auth/…`, `/api/me`, `/api/jobs…`, `/api/orders…`, `/api/placements`, `/api/domain…`, `/api/ai/…`, `/api/sync`, `/api/admin/…`,
`/api/report`, `/api/webhooks/…`, `/api/public/…`, `/api/alerts…`, `/api/claims…`. `/api/` (the page), `/api/v1/*.json` and
`/api/openapi.json` stay files; `/api/search`, `/api/latest` and `/api/check-duplicate` stay with `serve.py`. Checked on 15 Nov with nginx
1.24 and both programs running: each address reaches the right place.

### For the main session (from the accounts session, 15 Nov 2026; it could not message you back)

- `claude/funny-goodall-pvz7kr` is tested and contains all of `main`: `node --no-warnings server/test/run.mjs` 1,159 passed, `fresh_test.js`
  and `tools_test.js` pass, `records_test.py` 0 different, `check.py` passes on builds with and without `api_url`. It fast-forwards onto
  `main`. I did not push it to `main` myself: this session is cleared to push only to its own branch unless its user says otherwise.
  `git fetch origin claude/funny-goodall-pvz7kr && git checkout main && git merge --ff-only FETCH_HEAD && git push origin main`.
- The install paths are `/opt/hrn-api`, `/etc/hrn-api/api.env`, `/var/lib/hrn-api` (not `/srv/hrn`: see above). The owner's password
  command is `sudo bash /opt/hrn-api/server/hosting/api-secret.sh SMTP_PASS`.
- `/account/` comes back only with `"api_url": "https://jobseveryhour.com"` in `config.json`, set once `/api/health` answers through nginx.
  Merging alone does not bring it back.

### Installing it (me, on the server, as root; about 2 minutes)

1. From a checkout of the repository on the server (or `server/` copied there):
   ```
   sudo bash server/hosting/api-setup.sh
   ```
   It installs Node 22 from nodejs.org (checksum checked) if the machine has no Node 22.13+, makes the user `hrnapi` and the folders,
   writes `/etc/hrn-api/api.env` with a random `ADMIN_TOKEN` (never overwritten later), starts `hrn-api` and `hrn-alerts.timer`, adds the
   nginx addresses and reloads nginx. If the API does not answer `/api/health` within 20 seconds the previous code is put back; if nginx
   refuses the new files both are put back and nothing is reloaded. Running it again updates the code the same way.
2. Check:
   ```
   curl -s https://jobseveryhour.com/api/health                    # {"ok":true}
   curl -s https://jobseveryhour.com/api/public/products           # "payments":"off"
   systemctl status hrn-api hrn-alerts.timer --no-pager
   ```

### The mailbox password (the owner; 2 minutes)

Letters go out from support@jobseveryhour.com through `smtp.beget.com:465`. Its password is typed by the owner into a terminal on the
server and goes into `/etc/hrn-api/api.env` and nowhere else: not into the repository, not into a chat, not into a command line. The command:

```
sudo bash /opt/hrn-api/server/hosting/api-secret.sh SMTP_PASS
```

It asks for the value and shows nothing while it is typed: type the password of support@ (the one set in the Beget panel) and press
Enter. The API restarts with mail on. Then a test letter to any address of yours:

```
sudo -u hrnapi /usr/local/bin/node --no-warnings /opt/hrn-api/server/mail-test.mjs your-address@example.com
```

It prints `"sent":true` and the server's answer, or the reason it failed (a wrong password is `535`). The same script writes any other
secret later (`api-secret.sh ADMIN_TOKEN`, the payment keys when the owner switches payments on).

### Switching it on for the site (me; a push)

Only after the steps above work: `config.json` `"api_url": "https://jobseveryhour.com"`. The next hourly build then shows the account
page, the alert forms on the search, category and location pages, and the privacy and terms text for accounts and alerts (they appear in
the same build, never before), and `collect.py` starts reading posted jobs from `/api/public/export.json`. Check after that build: the
run's log has the line `placements: N posted jobs`; if it says `API did not answer`, Cloudflare is stopping GitHub's runner on that
address, and a Cloudflare rule "skip bot checks for `/api/public/export.json`" fixes it.

### Every day (the owner, or me with his go-ahead)

The review queue and the claims of company pages wait for a person: `server/README.md`, "Reviewing held jobs" (the token:
`sudo grep ^ADMIN_TOKEN= /etc/hrn-api/api.env`). How many people signed up: `/api/admin/audience`. Logs: `journalctl -u hrn-api`,
`journalctl -u hrn-alerts`. What the next alert run would send: `sudo -u hrnapi /usr/local/bin/node --no-warnings /opt/hrn-api/server/alerts.mjs --dry`.

### Taking it back

```
sudo systemctl disable --now hrn-api hrn-alerts.timer
sudo rm /etc/nginx/snippets/hrn-api.conf && sudo nginx -t && sudo systemctl reload nginx
```

and `"api_url": ""` in `config.json`: the site is as before (forms and account page gone), the database stays in `/var/lib/hrn-api`.

### Mail limits

Beget publishes no sending limit for a mailbox; `MAIL_DAILY_CAP` (300 a day) keeps us under any sensible one, and job alerts stop at 80%
of it so confirmation links always go. When alerts outgrow it, a sending service (Amazon SES, Postmark, Brevo) needs only `SMTP_HOST`,
`SMTP_USER`, `SMTP_PASS` and a higher cap: the code does not change. DKIM: when Beget's panel shows the record, add it in Cloudflare DNS
and move DMARC to `p=quarantine` (see Email above).

## Later on the same server

- Payments: `PAYMENTS_LIVE=1` and the gateway keys in `/etc/hrn-api/api.env` (the owner, last, when everything else is right).
- More pages from records the same way: companies (115 MiB), locations (195 MiB), roles (109 MiB) are lists of jobs too.
