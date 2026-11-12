# API: accounts, self-serve purchases, crypto checkout

One Cloudflare Worker (`src/worker.js`, no dependencies) and one D1 database (`schema.sql`).
A paid order switches itself on: the gateway confirms the payment, the worker records the placement, asks GitHub to rebuild the
site, and the build reads `/api/public/export.json`. Nobody has to answer an email.

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
4. `npx wrangler deploy`, then put the printed address into `API_URL` in `wrangler.toml` and deploy once more
5. Secrets (each command asks for the value; never commit them):
   `npx wrangler secret put CRYPTOMUS_MERCHANT`, `npx wrangler secret put CRYPTOMUS_API_KEY`, `npx wrangler secret put ADMIN_TOKEN`,
   and optionally `npx wrangler secret put GITHUB_TOKEN` (fine-grained token, this repository only, permission "Actions: read and write")
6. In the Cryptomus merchant settings confirm the site's domain; the webhook address is `<API_URL>/api/webhooks/cryptomus`
   (it is also sent with every invoice).
7. Put the worker address into `"api_url"` in `config.json` and push. The account page and checkout appear on the site.

Without `GITHUB_TOKEN` everything still works; a purchase then shows on the site at the next daily build instead of within minutes.

## Rules

- `PAY_MODE=test` exists only for `dev.mjs`. Never set it on Cloudflare.
- Prices live in `PRODUCTS` in `src/worker.js` and, for display, in `config.json`. Change both together.
- Plus is refused until `PLUS_LIVE = "1"`: do not sell it before its features exist.
