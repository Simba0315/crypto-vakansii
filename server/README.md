# API: accounts, self-serve purchases, crypto checkout, fraud checks

One Cloudflare Worker (`src/worker.js`, no dependencies) and one D1 database (`schema.sql`).
A paid order switches itself on: the gateway confirms the payment, the worker records the placement, asks GitHub to rebuild the
site, and the build reads `/api/public/export.json`. Nobody has to answer an email.

If the gateway's webhook never arrives, the cron finds the payment anyway: every ten minutes the worker asks the gateway about each
invoice that is still pending after five minutes, switches on the paid ones and closes the ones that were cancelled or ran out.

Jobs that employers post themselves go through the fraud checks described below before anyone sees them. The one part that is not
automatic is the review queue: the first jobs of every account, and anything the checks find odd, wait until the owner approves them.

## Try it on this machine (no Cloudflare, no money)

```
node --no-warnings server/test/run.mjs          # the test suite, must end with "0 failed"
node --no-warnings server/dev.mjs               # API in test mode on http://localhost:8787
HRN_API_URL=http://localhost:8787 python3 build.py   # builds the site with the account page pointing at it
```

In test mode there is no mailbox, so the answer to a sign-up carries `confirm_token` (send it to `POST /api/auth/confirm`), and
the owner's token is `dev-admin`.

## Going live (the owner does these; they need his Cloudflare and Cryptomus logins)

1. `cd server && npx wrangler login`
2. `npx wrangler d1 create hiring-right-now` and paste the printed id into `wrangler.toml`
3. `npx wrangler d1 execute hiring-right-now --remote --file=schema.sql`
   (a database made from an earlier `schema.sql`: see "Database changes" below first)
4. `npx wrangler deploy`, then put the printed address into `API_URL` in `wrangler.toml` and deploy once more.
   The deploy must list the cron trigger `*/10 * * * *` (it is in `wrangler.toml`; keep it). Without it a payment whose webhook
   was lost is never found, old invoices are never closed, held-back rebuilds are never sent, and the links of live jobs are
   never opened again (see "Cron").
5. Secrets (each command asks for the value; never commit them):
   `npx wrangler secret put CRYPTOMUS_MERCHANT`, `npx wrangler secret put CRYPTOMUS_API_KEY`, `npx wrangler secret put ADMIN_TOKEN`,
   and optionally `npx wrangler secret put GITHUB_TOKEN` (fine-grained token, this repository only, permission "Actions: read and write").
   `ADMIN_TOKEN` is the key to the review queue and to bans: make it long and random (`openssl rand -hex 32`), keep it in a
   password manager. While it is not set, every `/api/admin/...` request is refused.
6. In the Cryptomus merchant settings confirm the site's domain; the webhook address is `<API_URL>/api/webhooks/cryptomus`
   (it is also sent with every invoice).
7. Put the worker address into `"api_url"` in `config.json` and push. The account page and checkout appear on the site.
8. **Connect a mail service before employers are invited** (see "Mail"). An account cannot post or buy until its email is
   confirmed, and the confirmation link travels by mail: without `MAIL` nobody can confirm, so nobody can post.

Without `GITHUB_TOKEN` everything still works; a purchase then shows on the site at the next daily build instead of within minutes.

## Fraud checks: what stands between an employer and the site

A. **A work email, confirmed.** There are two kinds of account. An address on a company's own domain makes an employer account,
   tied to the registrable domain of that address (`users.domain`), and only such an account can post a job. A free mailbox
   (gmail, outlook, proton.me ...: `FREE_MAIL_NAMES`, `FREE_MAIL_DOMAINS`) makes a job seeker's account with an empty domain: it
   can buy Plus and keep saved jobs, and posting or previewing a job answers `work_email`. A throwaway mailbox (mailinator ...:
   `THROWAWAY_NAMES`, `THROWAWAY_DOMAINS`) gets no account: `throwaway_email`.
   That domain is worked out by a rule of thumb, on purpose, without a public-suffix list: the last two labels of the host, or three
   under a listed country zone (`PUBLIC_SECONDS`: co.uk, com.au ...), any other two-letter zone with a generic second level
   (org.uk, com.cn) or a shared host (github.io). Add a zone to `PUBLIC_SECONDS` if one is missing. The account is unconfirmed
   until the link mailed at sign-up is opened (`POST /api/auth/confirm` `{ token }`, 24 hours, one use, only its hash is stored;
   `POST /api/auth/confirm/request` with a session sends a new one). Unconfirmed, it can sign in and have a draft checked
   (`POST /api/jobs/preview`: same checks, nothing stored, no link opened) but cannot publish a job or buy anything for employers.
B. **The job is on the account's domain.** The link to apply must be on `users.domain` or on one of the hiring systems in
   `HIRING_HOSTS` / `HIRING_TENANTS` (exact hosts; anything else is refused). The company site, when given, must be on that domain
   too; left out, it is the domain. Look-alikes of well-known employers (`BRANDS`: "coinbase-careers.com", "c0inbase.com", one letter
   off, any punycode label, or the company named "Coinbase" from another domain) are not refused but always wait for review. The
   comment above `BRANDS` says how to add an employer or let a real namesake through.
C. **The text and the links are screened** (`screenPosting`, on every new job and every edit). Hard rejects, told to the employer:
   links to chats, forms, link shorteners, file hosts or downloads; fees asked of candidates; moving money or parcels; asking for seed
   phrases, keys, ID scans, bank or card details. Softer signals add up: 60 points reject, 25 to 59 send the job to review.
   The same title and company from the same account again is refused while the first is there, and for 30 days after it was removed.
D. **Review and trust.** An account is trusted after 2 jobs the owner approved, 14 days, and no upheld report. Until then every job
   waits for review, and the account may post 1 job a day and have 3 jobs on the site or waiting (afterwards: 3 new jobs a day).
   Anything from B or C that asks for a second look waits for review even from a trusted account. A placement bought for a job that
   waits is held and its days start when the job is approved; if a live job goes back to review, the days it has left are kept.
E. **Reports.** Anyone can report a job (`POST /api/report` `{ job: <job id, page slug or page address>, reason, note? }`, reasons:
   `asks_for_money`, `asks_to_install`, `moved_to_chat`, `impersonation`, `job_not_real`, `other`). One report of the first two
   kinds, or two reports of any kind from different addresses, takes a job posted here off the site until the owner decides. Reports
   about jobs read from hiring systems are only listed. Of the sender nothing is kept but a salted hash of the address.
   `GET /api/public/transparency.json` gives the counts of this month and the last one for the site to print.
F. **Account protection.** A sign-in from a browser the account was not used in before sends a notice to its address.

What it does not do, so nobody assumes it: it does not look up how old a domain is. `domainAge(env, domain)` in `src/worker.js` is
the hook: bind `DOMAINS` in `wrangler.toml` to anything with `age(domain)` returning days (a small worker that asks an RDAP service,
for example) and jobs from a domain younger than 30 days wait for review. With nothing bound it answers `null` and nothing changes.
It also cannot see what the page behind a link says tomorrow: the daily recheck notices a new host, not new words.

## Reviewing held jobs (the owner's routine; once a day is enough to start with)

The token is read from the environment, never typed into a command, so it does not end up in the shell history or the process list:

```
export HRN_API=https://hiring-right-now-api.YOUR-SUBDOMAIN.workers.dev
read -rs HRN_ADMIN_TOKEN && export HRN_ADMIN_TOKEN     # paste the token and press Enter; nothing is shown
hrn() { printf 'header = "Authorization: Bearer %s"\n' "$HRN_ADMIN_TOKEN" | curl -sS -K - "$@"; echo; }

hrn "$HRN_API/api/admin/review"                        # jobs that wait: reason, link, text, the account's email domain and age, open reports
hrn -X POST "$HRN_API/api/admin/jobs/j_0123456789ab/approve"
hrn -X POST -H 'Content-Type: application/json' -d '{"reason":"The link does not open a job at this company."}' \
    "$HRN_API/api/admin/jobs/j_0123456789ab/reject"    # the employer reads the reason on the account page
hrn "$HRN_API/api/admin/reports"                       # every report, open ones first
hrn -X POST -H 'Content-Type: application/json' -d '{"decision":"dismissed"}' "$HRN_API/api/admin/reports/r_0123456789abcdef0123/decide"
hrn -X POST "$HRN_API/api/admin/accounts/u_0123456789abcdef0123/ban"
hrn "$HRN_API/api/admin/overview"
```

How to read the queue. For each job look at `reason` (why it waits), open `apply_url` yourself and check that the page is this job
at this company, and look at `account.email_domain`: is it the company's real domain? Then:

- **approve**: the job goes live for 30 days from now, what was bought for it starts, open reports about it are dismissed, and the
  approval counts towards the account's trust (once per job).
- **reject** (needs a reason): the job is closed for good and the employer sees the reason. What was bought for it is switched off;
  if money was paid, refund it by hand at the gateway. Open reports about it are upheld, which costs the account its trust, and the
  company name is free again if the account has no other job under it. The employer may post a corrected job.
- **ban** (`/api/admin/accounts/<id>/ban`, the same as `/api/admin/users/<id>/ban`): for an account that is plainly fraudulent.
  Everything it has goes at once.
- `reports/<id>/decide` with `upheld` or `dismissed` is for a report that has no job to approve or reject: a job read from a hiring
  system (if the report is right, take the company out of the sources by hand), or one the employer deleted meanwhile.
- `POST /api/admin/jobs/<id>/remove` still exists: it takes a job down without a reason shown to anyone.

A job waits because: the account is not trusted yet; the link is on a hiring system and the account is not trusted yet; the screen
found something ("review" verdict); the domain or the company name looks like a well-known employer; the employer edited a live job
before the account was trusted; the link to apply now ends on another host; or the job was `reported`.

## Cron

The trigger in `wrangler.toml` runs every ten minutes. Besides settling payments and tidying up, each run opens the link to apply
of up to 4 live jobs again (`RECHECK_BATCH`; every job once a day, the longest unchecked first; that is 576 jobs a day, raise the
number when there are more, keeping an eye on the Worker's limit of outgoing requests: a run makes at most 20 gateway requests,
5 per rechecked job and 1 to GitHub). A job whose link now ends on another host than when it was checked goes back to review. A
link that merely does not open changes nothing by itself. Links that confirm an email and ran out are cleared in the same run.

## Mail

`sendMail` in `src/worker.js` is the only place mail leaves from, and until a binding named `MAIL` exists it sends nothing. Three
things depend on it: the link that confirms a new account (**without it nobody can post**), password resets, and the notice of a
sign-in from a new device. To switch it on, bind `MAIL` in `wrangler.toml` to anything that has `send({ from, to, subject, text })`
(a service binding to a mail worker, for example) and set the variable `MAIL_FROM`.

`POST /api/auth/reset/request` `{ email }` always answers the same way, whether or not the account exists. For a real account it
stores the hash of a one-time token (30 minutes) and hands a mail with the link `<SITE_URL>/account/#reset=<token>` to `sendMail`.
`POST /api/auth/reset/confirm` `{ token, password }` sets the password and ends every session of the account.
The confirmation link has the same shape: `<SITE_URL>/account/#confirm=<token>`, 24 hours.
The account page needs forms that read `#reset=` and `#confirm=` and call these endpoints.
In test mode (`dev.mjs`) the answers carry the tokens themselves, because there is no mailbox to read.

## Database changes

Nothing is deployed yet, so there is nothing to migrate: a new database gets everything from `schema.sql`. For a local `DB_FILE`
kept from an earlier `dev.mjs`, delete the file; or run the lines for the step it is missing, then `schema.sql`.

After the first draft of `schema.sql`: tables `companies` and `resets`, columns `jobs.company_key` and `orders.activation`, new
indexes, two of them unique (`placements.order_id`, `credits.order_id`).

```
ALTER TABLE orders ADD COLUMN activation TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN company_key TEXT NOT NULL DEFAULT '';
UPDATE jobs SET company_key = lower(trim(company));
-- now schema.sql (it creates companies, resets and the indexes), and after it:
INSERT OR IGNORE INTO companies (k, name, user_id, created_at) SELECT company_key, company, user_id, MIN(created_at) FROM jobs WHERE status != 'removed' GROUP BY company_key;
```

For the fraud checks: tables `confirms` (links that confirm an email), `devices` (browsers an account signed in from), `reports`,
`stats` (monthly counters); the columns below; indexes `jobs_status`, `jobs_slug`, `reports_once` (unique), `reports_open`.
`jobs.status` has two new values, `review` and `rejected`.

```
ALTER TABLE users ADD COLUMN domain TEXT NOT NULL DEFAULT '';
ALTER TABLE users ADD COLUMN banned_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN confirmed_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN approved_jobs INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN upheld_reports INTEGER NOT NULL DEFAULT 0;
ALTER TABLE placements ADD COLUMN held INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN title_key TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN slug TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN apply_host TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN review_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN reject_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN held_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN approved_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN ended_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN checked_at INTEGER NOT NULL DEFAULT 0;
-- now schema.sql (it creates confirms, devices, reports, stats and the indexes).
```

Rows from before: an account has no `domain` (the worker then works it out from the email each time) and is unconfirmed, so it
cannot post until `UPDATE users SET confirmed_at = created_at` or a new confirmation link; a job has no `title_key`, `slug` or
`apply_host`, so the duplicate guard, reports by page address and the daily recheck do not see it until it is edited.

## Rules

- `PAY_MODE=test` exists only for `dev.mjs`. Never set it on Cloudflare.
- Prices live in `PRODUCTS` in `src/worker.js` and, for display, in `config.json`. Change both together.
- Plus is refused until `PLUS_LIVE = "1"`: do not sell it before its features exist. Job seekers sign up with any mailbox they
  keep (free mailboxes included); such an account cannot post jobs.
- An employer may post any number of jobs: one a day and three at a time until the account is trusted, three a day after that.
  A company name belongs to the first account that posts a checked job under it; names are compared without case, extra spaces
  and punctuation at the end ("Acme!" is "acme"), nothing else is folded.
- A job the employer deletes (`DELETE /api/jobs/<id>` or `POST /api/jobs/<id>/delete`), or that the owner takes down, is gone for
  good together with what was bought for it. A closed job can be published again; meanwhile its placements are paused, not lost.
- The link to apply is opened by the worker before a job is accepted, again after any edit of the link, title, company or company
  site, and once a day while the job is live. What that check does and what it cannot do is written above `checkApplyLink` in
  `src/worker.js`.
- Paying never skips review, and nothing an employer does puts a held job on the site: only `approve` does.
