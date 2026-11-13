# API: accounts, self-serve purchases, crypto checkout

One Cloudflare Worker (`src/worker.js`, no dependencies) and one D1 database (`schema.sql`).
A paid order switches itself on: the gateway confirms the payment, the worker records the placement, asks GitHub to rebuild the
site, and the build reads `/api/public/export.json`. Nobody has to answer an email.

If the gateway's webhook never arrives, the cron finds the payment anyway: every ten minutes the worker asks the gateway about each
invoice that is still pending after five minutes, switches on the paid ones and closes the ones that were cancelled or ran out.

## Try it on this machine (no Cloudflare, no money)

```
node --no-warnings server/test/run.mjs          # the test suite, must end with "0 failed"
node --no-warnings server/dev.mjs               # API in test mode on http://localhost:8787
HRN_API_URL=http://localhost:8787 python3 build.py   # builds the site with the account page pointing at it
```

## Going live (the owner does these; they need his Cloudflare and Cryptomus logins)

1. `cd server && npx wrangler login`
2. `npx wrangler d1 create hiring-right-now` and paste the printed id into `wrangler.toml`
3. `npx wrangler d1 execute hiring-right-now --remote --file=schema.sql`
   (a database made from an earlier `schema.sql`: see "Database changes" below first)
4. `npx wrangler deploy`, then put the printed address into `API_URL` in `wrangler.toml` and deploy once more.
   The deploy must list the cron trigger `*/10 * * * *` (it is in `wrangler.toml`; keep it). Without it a payment whose webhook
   was lost is never found, old invoices are never closed and held-back rebuilds are never sent.
5. Secrets (each command asks for the value; never commit them):
   `npx wrangler secret put CRYPTOMUS_MERCHANT`, `npx wrangler secret put CRYPTOMUS_API_KEY`, `npx wrangler secret put ADMIN_TOKEN`,
   and optionally `npx wrangler secret put GITHUB_TOKEN` (fine-grained token, this repository only, permission "Actions: read and write")
6. In the Cryptomus merchant settings confirm the site's domain; the webhook address is `<API_URL>/api/webhooks/cryptomus`
   (it is also sent with every invoice).
7. Put the worker address into `"api_url"` in `config.json` and push. The account page and checkout appear on the site.

Without `GITHUB_TOKEN` everything still works; a purchase then shows on the site at the next daily build instead of within minutes.

## Password reset and mail (optional, nothing to set up yet)

`POST /api/auth/reset/request` `{ email }` always answers the same way, whether or not the account exists. For a real account it
stores the hash of a one-time token (30 minutes) and hands a mail with the link `<SITE_URL>/account/#reset=<token>` to `sendMail`.
`POST /api/auth/reset/confirm` `{ token, password }` sets the password and ends every session of the account.

No mail service is connected: `sendMail` in `src/worker.js` is the only place mail leaves from, and until a binding named `MAIL`
exists it sends nothing, so **reset links reach nobody yet**. To switch it on, bind `MAIL` in `wrangler.toml` to anything that has
`send({ from, to, subject, text })` (a service binding to a mail worker, for example) and set the variable `MAIL_FROM`.
The account page also needs a form that reads `#reset=` and calls the two endpoints.
In test mode (`dev.mjs`) the answer to a reset request carries the token itself, because there is no mailbox to read.

## Database changes (after the first draft of `schema.sql`)

New tables `companies` (one company name, one account) and `resets` (password reset links); new columns `jobs.company_key` and
`orders.activation`; new indexes, two of them unique (`placements.order_id`, `credits.order_id`: one order, one placement).
A new database gets all of it from `schema.sql`. Nothing is deployed yet, so there is nothing to migrate. For a local `DB_FILE`
kept from an earlier `dev.mjs`, delete the file; or run the first three lines below, then `schema.sql`, then the last line:

```
ALTER TABLE orders ADD COLUMN activation TEXT NOT NULL DEFAULT '';
ALTER TABLE jobs ADD COLUMN company_key TEXT NOT NULL DEFAULT '';
UPDATE jobs SET company_key = lower(trim(company));
-- now schema.sql (it creates companies, resets and the indexes), and after it:
INSERT OR IGNORE INTO companies (k, name, user_id, created_at) SELECT company_key, company, user_id, MIN(created_at) FROM jobs WHERE status != 'removed' GROUP BY company_key;
```

## Rules

- `PAY_MODE=test` exists only for `dev.mjs`. Never set it on Cloudflare.
- Prices live in `PRODUCTS` in `src/worker.js` and, for display, in `config.json`. Change both together.
- Plus is refused until `PLUS_LIVE = "1"`: do not sell it before its features exist.
- An employer may post any number of jobs, three a day. A company name belongs to the first account that publishes a checked job
  under it; names are compared without case, extra spaces and punctuation at the end ("Acme!" is "acme"), nothing else is folded.
- A job the employer deletes (`DELETE /api/jobs/<id>` or `POST /api/jobs/<id>/delete`), or that the owner takes down, is gone for
  good together with what was bought for it. A closed job can be published again; meanwhile its placements are paused, not lost.
- The link to apply is opened by the worker before a job goes live and again after any edit of the link, title, company or company
  site. What that check does and what it cannot do is written above `checkApplyLink` in `src/worker.js`.
