// End-to-end tests for the API worker. Run:  node --no-warnings server/test/run.mjs
// Everything outside the worker is faked here: the site, the payment gateway, GitHub and employers' career pages.
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import worker, { md5, phpJson, gatewaySign, webhookSignatureOk, PRODUCTS } from '../src/worker.js';
import { D1 } from './d1.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const KEY = 'test-payment-key', SITE = 'https://site.test', API = 'https://api.test';
let passed = 0, failed = 0;
const ok = (cond, name, extra = '') => { if (cond) passed++; else { failed++; console.log('FAIL', name, extra); } };
const eq = (a, b, name) => ok(JSON.stringify(a) === JSON.stringify(b), name, `got ${JSON.stringify(a)} want ${JSON.stringify(b)}`);

/* ---- the outside world ---- */
const world = { invoices: {}, githubCalls: 0, pages: {
  [SITE + '/data/head.json']: JSON.stringify({ c: ['Stripe', 'Harvey', 'Crypto.com'], n: 3, r: [] }),
  [SITE + '/job/staff-engineer-stripe/']: '<html><title>Staff Engineer at Stripe</title><main>Open</main></html>',
  [SITE + '/job/old-role-stripe/']: '<html><title>Old role at Stripe</title><div class="banner">This job is closed as of Nov 1.</div></html>',
  [SITE + '/skills/rust/']: '<html>rust</html>', [SITE + '/jobs/engineering/']: '<html>eng</html>',
  'https://acme.dev/careers/senior-rust-engineer': '<html><h1>Senior Rust Engineer</h1> join Acme</html>',
  'https://acme.dev/careers': '<html>All our teams</html>',
  'https://boards.greenhouse.io/acme/jobs/1': '<html><div id="app"></div></html>',
} };
globalThis.fetch = async (input, init = {}) => {
  const url = typeof input === 'string' ? input : input.url;
  if (url.startsWith('https://api.cryptomus.com/')) {
    const text = init.body, payload = JSON.parse(text);
    if (init.headers.sign !== gatewaySign(text, KEY) || init.headers.merchant !== 'merchant-1') return new Response('{"state":1}', { status: 401 });
    if (url.endsWith('/v1/payment')) {
      world.invoices[payload.order_id] = { ...payload, uuid: 'uuid-' + payload.order_id, status: 'check' };
      return Response.json({ state: 0, result: { uuid: 'uuid-' + payload.order_id, order_id: payload.order_id, url: 'https://pay.cryptomus.com/pay/uuid-' + payload.order_id, payment_status: 'check' } });
    }
    if (url.endsWith('/v1/payment/info')) {
      const inv = world.invoices[payload.order_id];
      return inv ? Response.json({ state: 0, result: { order_id: payload.order_id, payment_status: inv.status, status: inv.status } }) : new Response('{"state":1}', { status: 422 });
    }
  }
  if (url.startsWith('https://api.github.com/')) { world.githubCalls++; return new Response(null, { status: 204 }); }
  if (url in world.pages) return new Response(world.pages[url], { status: 200 });
  return new Response('not found', { status: 404 });
};

/* ---- helpers ---- */
const newEnv = (extra = {}) => ({ DB: new D1().applySchema(path.join(here, '../schema.sql')), SITE_URL: SITE, SITE_ORIGINS: SITE, API_URL: API,
  CRYPTOMUS_MERCHANT: 'merchant-1', CRYPTOMUS_API_KEY: KEY, ADMIN_TOKEN: 'admin-secret', GITHUB_TOKEN: 'gh', GITHUB_REPO: 'o/r', ...extra });
let ipCounter = 0;
async function call(env, method, p, { token, data, ip, raw, origin } = {}) {
  const headers = { 'CF-Connecting-IP': ip || '10.0.0.' + (++ipCounter % 250) };
  if (token) headers.Authorization = 'Bearer ' + token;
  if (origin) headers.Origin = origin;
  if (data || raw) headers['Content-Type'] = 'application/json';
  const res = await worker.fetch(new Request(API + p, { method, headers, body: raw ?? (data ? JSON.stringify(data) : undefined) }), env);
  let out = null; try { out = await res.clone().json(); } catch {}
  return { status: res.status, body: out, headers: res.headers };
}
const signedWebhook = (fields, key = KEY, unicode = true) => { const text = phpJson(fields, unicode); return phpJson({ ...fields, sign: gatewaySign(text, key) }, unicode); };
async function account(env, email = 'boss@acme.dev') {
  const r = await call(env, 'POST', '/api/auth/signup', { data: { email, password: 'correct horse battery' } });
  return r.body.token;
}

/* ---- 1. signature maths ---- */
for (const s of ['', 'a', 'abc', 'message digest', 'x'.repeat(55), 'x'.repeat(56), 'x'.repeat(64), 'x'.repeat(1000), 'héllo — ünïcode ✓', '{"url":"https:\\/\\/a.b\\/c"}'])
  eq(md5(s), createHash('md5').update(s, 'utf8').digest('hex'), 'md5 of ' + JSON.stringify(s.slice(0, 12)) + ' (' + s.length + ')');
eq(phpJson({ u: 'https://a.b/c', t: 'é' }, false), '{"u":"https:\\/\\/a.b\\/c","t":"\\u00e9"}', 'php-style json, escaped unicode');
eq(phpJson({ u: 'https://a.b/c', t: 'é' }, true), '{"u":"https:\\/\\/a.b\\/c","t":"é"}', 'php-style json, plain unicode');
{
  const fields = { type: 'payment', uuid: 'u1', order_id: 'o_1', amount: '99.00', is_final: true, status: 'paid', url: 'https://x.y/z', note: 'café' };
  ok(webhookSignatureOk(signedWebhook(fields), KEY), 'webhook signature accepted');
  ok(webhookSignatureOk(signedWebhook(fields, KEY, false), KEY), 'webhook signature accepted with escaped unicode');
  ok(!webhookSignatureOk(signedWebhook(fields, 'other-key'), KEY), 'webhook signed with another key refused');
  ok(!webhookSignatureOk(signedWebhook(fields).replace('"paid"', '"paid_over"'), KEY), 'tampered webhook refused');
  ok(!webhookSignatureOk('{"order_id":"o_1","status":"paid"}', KEY), 'unsigned webhook refused');
  // a body whose number formatting would not survive re-encoding still verifies through the raw text
  const odd = '{"order_id":"o_1","amount":10.50,"status":"paid"}', sign = gatewaySign(odd, KEY);
  ok(webhookSignatureOk(odd.replace('}', ',"sign":"' + sign + '"}'), KEY), 'webhook verified from raw text');
}

/* ---- 2. accounts ---- */
{
  const env = newEnv();
  let r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'bad', password: 'longenough' } }); eq(r.status, 400, 'bad email refused');
  r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'a@b.co', password: 'short' } }); eq(r.status, 400, 'short password refused');
  r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'A@B.co', password: 'longenough' } }); eq(r.status, 200, 'signup works');
  const token = r.body.token; ok(/^[a-f0-9]{64}$/.test(token), 'session token issued');
  eq(r.body.user.email, 'a@b.co', 'email is lowercased');
  r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'a@b.co', password: 'longenough' } }); eq(r.status, 409, 'duplicate email refused');
  r = await call(env, 'GET', '/api/me', { token }); eq([r.status, r.body.user.plus, r.body.user.credits], [200, false, 0], 'me returns the account');
  r = await call(env, 'GET', '/api/me'); eq(r.status, 401, 'no token, no account');
  r = await call(env, 'GET', '/api/me', { token: 'f'.repeat(64) }); eq(r.status, 401, 'unknown token refused');
  r = await call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'wrong-password' } }); eq(r.status, 401, 'wrong password refused');
  r = await call(env, 'POST', '/api/auth/login', { data: { email: 'nobody@b.co', password: 'longenough' } }); eq(r.status, 401, 'unknown email refused the same way');
  r = await call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'longenough' } }); eq(r.status, 200, 'login works');
  const second = r.body.token;
  r = await call(env, 'POST', '/api/auth/logout', { token: second }); r = await call(env, 'GET', '/api/me', { token: second }); eq(r.status, 401, 'logout ends the session');
  const stored = await env.DB.prepare('SELECT pass_hash, pass_salt FROM users').first();
  ok(!JSON.stringify(stored).includes('longenough') && stored.pass_hash.length === 64, 'password is stored hashed');
  for (let i = 0; i < 10; i++) await call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'nope-nope' }, ip: '9.9.9.9' });
  r = await call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'longenough' }, ip: '9.9.9.9' }); eq(r.status, 429, 'password guessing is rate limited');
  r = await call(env, 'OPTIONS', '/api/me', { origin: SITE }); eq([r.status, r.headers.get('Access-Control-Allow-Origin')], [204, SITE], 'CORS allows the site');
  r = await call(env, 'OPTIONS', '/api/me', { origin: 'https://evil.test' }); eq(r.headers.get('Access-Control-Allow-Origin'), null, 'CORS refuses other sites');
}

/* ---- 3. buying a featured job, paid by webhook ---- */
{
  const env = newEnv(), token = await account(env);
  let r = await call(env, 'POST', '/api/orders', { token, data: { product: 'nope' } }); eq(r.status, 400, 'unknown product refused');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: SITE + '/job/missing/' } } }); eq(r.status, 400, 'job that is not on the site refused');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: SITE + '/job/old-role-stripe/' } } }); eq(r.status, 400, 'closed job refused');
  r = await call(env, 'POST', '/api/orders', { data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } }); eq(r.status, 401, 'buying needs an account');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: SITE + '/job/staff-engineer-stripe/?utm=1' } } });
  eq([r.status, r.body.order.status, r.body.order.amount_usd, r.body.order.label], [200, 'pending', 99, 'Staff Engineer at Stripe'], 'order created');
  const id = r.body.order.id, inv = world.invoices[id];
  ok(r.body.order.pay_url.startsWith('https://pay.cryptomus.com/'), 'checkout link returned');
  eq([inv.amount, inv.currency, inv.url_callback, inv.url_success], ['99', 'USD', API + '/api/webhooks/cryptomus', SITE + '/account/?order=' + id], 'invoice sent to the gateway correctly');
  r = await call(env, 'GET', '/api/public/export.json'); eq(r.body.boosts, [], 'nothing is live before payment');

  // forged webhook: wrong signature, and the gateway says the invoice is unpaid
  r = await call(env, 'POST', '/api/webhooks/cryptomus', { raw: JSON.stringify({ order_id: id, status: 'paid', sign: 'f'.repeat(32) }) });
  r = await call(env, 'GET', '/api/orders/' + id, { token }); eq(r.body.order.status, 'pending', 'forged webhook does not activate anything');

  const before = world.githubCalls;
  r = await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ type: 'payment', uuid: inv.uuid, order_id: id, amount: '99.00', status: 'paid', is_final: true }) });
  eq(r.status, 200, 'webhook acknowledged');
  r = await call(env, 'GET', '/api/orders/' + id, { token }); eq([r.body.order.status, r.body.order.pay_url], ['paid', ''], 'order is paid');
  r = await call(env, 'GET', '/api/public/export.json');
  eq(r.body.boosts.map((b) => [b.slug, b.kind]), [['staff-engineer-stripe', 'featured']], 'featured job is exported to the site');
  const until = r.body.boosts[0].until, want = new Date(Date.now() + 14 * 86400e3).toISOString().slice(0, 10);
  eq(until, want, 'featured for 14 days');
  eq(world.githubCalls, before + 1, 'site rebuild requested once');
  r = await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: id, status: 'paid', is_final: true }) });
  r = await call(env, 'GET', '/api/placements', { token }); eq(r.body.placements.length, 1, 'a repeated webhook does not double the placement');
  eq(r.body.placements[0].state, 'live', 'placement is live');

  // buying the same thing again extends it rather than overlapping
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } });
  await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: r.body.order.id, status: 'paid_over' }) });
  r = await call(env, 'GET', '/api/public/export.json');
  eq(r.body.boosts[0].until, new Date(Date.now() + 28 * 86400e3).toISOString().slice(0, 10), 'second purchase adds 14 more days');
  eq(world.githubCalls, before + 1, 'rebuilds are not sent more than once in ten minutes');
  await worker.scheduled({}, env);
  eq(world.githubCalls, before + 1, 'held-back rebuild waits for the ten minutes to pass');
  await env.DB.prepare("UPDATE meta SET v = '0' WHERE k = 'rebuild_at'").run();
  await worker.scheduled({}, env);
  eq(world.githubCalls, before + 2, 'held-back rebuild is sent by the timer');

  // refund switches it off
  await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: id, status: 'refund_paid' }) });
  r = await call(env, 'GET', '/api/orders/' + id, { token }); eq(r.body.order.status, 'refunded', 'refund recorded');

  // another account cannot see this order
  const other = await account(env, 'other@x.dev');
  r = await call(env, 'GET', '/api/orders/' + id, { token: other }); eq(r.status, 404, "someone else's order is hidden");
}

/* ---- 4. webhook lost: the status is fetched from the gateway; underpayment; expiry ---- */
{
  const env = newEnv(), token = await account(env);
  let r = await call(env, 'POST', '/api/orders', { token, data: { product: 'pinned', target: { job: 'staff-engineer-stripe' } } });
  const id = r.body.order.id; world.invoices[id].status = 'paid';
  r = await call(env, 'GET', '/api/orders/' + id + '?refresh=1', { token }); eq(r.body.order.status, 'paid', 'payment found by asking the gateway');
  r = await call(env, 'GET', '/api/public/export.json'); eq(r.body.boosts.map((b) => b.kind), ['pinned'], 'pinned job exported');

  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } });
  await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: r.body.order.id, status: 'wrong_amount' }) });
  r = await call(env, 'GET', '/api/orders/' + r.body.order.id, { token }); eq(r.body.order.status, 'underpaid', 'underpayment does not activate');

  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } });
  const stale = r.body.order.id;
  await env.DB.prepare('UPDATE orders SET created_at = created_at - 3 * 3600 WHERE id = ?').bind(stale).run();
  r = await call(env, 'GET', '/api/orders', { token }); eq(r.body.orders.find((o) => o.id === stale).status, 'expired', 'unpaid invoice expires');
  // ... and a late payment for it still counts
  await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: stale, status: 'paid' }) });
  r = await call(env, 'GET', '/api/orders/' + stale, { token }); eq(r.body.order.status, 'paid', 'late payment is honoured');
}

/* ---- 5. spotlight, sponsorship, packs ---- */
{
  const env = newEnv(), token = await account(env);
  const pay = async (data) => { const r = await call(env, 'POST', '/api/orders', { token, data }); if (r.status === 200) await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: r.body.order.id, status: 'paid' }) }); return r; };
  let r = await pay({ product: 'spotlight', target: { company: 'Nobody Inc' } }); eq(r.status, 400, 'spotlight for an unknown company refused');
  r = await pay({ product: 'spotlight', target: { company: 'stripe' } }); eq([r.status, r.body.order.label, r.body.order.amount_usd], [200, 'Stripe', 499], 'spotlight ordered, name normalised');
  r = await pay({ product: 'sponsor', target: { company: 'Harvey', page: 'skill:cobol-9000' } }); eq(r.status, 400, 'sponsoring a page that does not exist refused');
  r = await pay({ product: 'sponsor', target: { company: 'Harvey', page: 'skill:rust' } }); eq(r.status, 200, 'skill page sponsorship ordered');
  r = await pay({ product: 'sponsor', target: { company: 'Harvey', page: 'category:engineering' } }); eq(r.status, 200, 'category sponsorship ordered');
  r = await call(env, 'GET', '/api/public/export.json');
  eq(r.body.sponsors.map((s) => s.company + '/' + s.slot).sort(), ['Harvey/category:engineering', 'Harvey/skill:rust', 'Stripe/spotlight'], 'sponsors exported in the format the site build expects');

  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: 'staff-engineer-stripe' }, use_credit: true } }); eq(r.status, 409, 'no credits, no free listing');
  r = await pay({ product: 'pack5' }); eq(r.body.order.amount_usd, 399, 'pack ordered');
  r = await call(env, 'GET', '/api/me', { token }); eq(r.body.user.credits, 5, 'pack gives five credits');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: 'staff-engineer-stripe' }, use_credit: true } });
  eq([r.status, r.body.order.status, r.body.order.amount_usd], [200, 'paid', 0], 'credit turns into a featured job at once');
  r = await call(env, 'GET', '/api/me', { token }); eq(r.body.user.credits, 4, 'one credit used');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'pinned', target: { job: 'staff-engineer-stripe' }, use_credit: true } }); eq(r.status, 400, 'credits only buy featured jobs');
}

/* ---- 6. Plus ---- */
{
  let env = newEnv(), token = await account(env);
  let r = await call(env, 'POST', '/api/orders', { token, data: { product: 'plus3' } }); eq(r.status, 409, 'Plus cannot be bought before it is on sale');
  r = await call(env, 'GET', '/api/public/products'); ok(!r.body.products.some((p) => p.group === 'plus') && r.body.payments === 'on', 'Plus is not listed before it is on sale');
  r = await call(env, 'PUT', '/api/sync', { token, data: { data: { a: 1 } } }); eq(r.status, 402, 'sync needs Plus');
  env = newEnv({ PLUS_LIVE: '1' }); token = await account(env);
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'plus3' } });
  await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: r.body.order.id, status: 'paid' }) });
  r = await call(env, 'GET', '/api/me', { token });
  eq([r.body.user.plus, r.body.user.plus_until], [true, new Date(Date.now() + 91 * 86400e3).toISOString().slice(0, 10)], 'Plus switched on for 3 months');
  r = await call(env, 'PUT', '/api/sync', { token, data: { data: { jobs: { x: 1 } } } }); eq(r.status, 200, 'sync saved');
  r = await call(env, 'GET', '/api/sync', { token }); eq(r.body.data, { jobs: { x: 1 } }, 'sync read back');
}

/* ---- 7. posting a job ---- */
{
  const env = newEnv(), token = await account(env);
  const good = { company: 'Acme Robotics', company_url: 'https://acme.dev', title: 'Senior Rust Engineer', apply_url: 'https://acme.dev/careers/senior-rust-engineer', location: 'Berlin',
    remote: true, salary: '$140K - $170K', etype: 'Full-time', description: 'Build the control software for our warehouse robots. You will own the motion planning service, written in Rust, and work with a team of six.' };
  const post = (over) => call(env, 'POST', '/api/jobs', { token, data: { ...good, ...over } });
  let r = await post({ company: 'Stripe' }); eq(r.status, 409, 'cannot post under a company that is already indexed');
  r = await post({ apply_url: 'https://t.me/acme_hr' }); eq(r.status, 422, 'messenger link refused');
  r = await post({ apply_url: 'https://other-site.com/job' }); eq(r.status, 422, 'link on an unrelated site refused');
  r = await post({ apply_url: 'https://acme.dev/careers' }); eq(r.status, 422, 'link that does not show this job refused');
  r = await post({ apply_url: 'https://acme.dev/gone' }); eq(r.status, 422, 'dead link refused');
  r = await post({ apply_url: 'http://acme.dev/careers/senior-rust-engineer' }); eq(r.status, 400, 'plain http refused');
  r = await post({ description: 'too short' }); eq(r.status, 400, 'thin description refused');
  r = await post({ description: good.description + ' https://a.b https://c.d https://e.f' }); eq(r.status, 400, 'link-stuffed description refused');
  r = await post({}); eq([r.status, r.body.job.status, r.body.job.page], [200, 'live', '/job/senior-rust-engineer-acme-robotics/'], 'job posted and live');
  const jobId = r.body.job.id;
  r = await post({ title: 'Platform Engineer', apply_url: 'https://boards.greenhouse.io/acme/jobs/1' }); eq(r.status, 200, 'job on a known hiring system accepted');
  r = await call(env, 'GET', '/api/public/export.json');
  eq(r.body.jobs.map((j) => [j.company, j.title, j.remote, j.featured_until]), [['Acme Robotics', 'Senior Rust Engineer', true, ''], ['Acme Robotics', 'Platform Engineer', true, '']], 'posted jobs exported');
  ok(!('user_id' in r.body.jobs[0]) && !JSON.stringify(r.body).includes('boss@acme.dev'), 'export carries no account data');

  // promote a job posted here, then spotlight the company it belongs to
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job_id: jobId } } });
  await call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: r.body.order.id, status: 'paid' }) });
  r = await call(env, 'GET', '/api/public/export.json'); ok(r.body.jobs[0].featured_until > '2026', 'own job becomes featured');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'spotlight', target: { company: 'acme robotics' } } }); eq(r.status, 200, 'spotlight allowed for a company with a live posted job');
  const stranger = await account(env, 'stranger@x.dev');
  r = await call(env, 'POST', '/api/orders', { token: stranger, data: { product: 'featured', target: { job_id: jobId } } }); eq(r.status, 400, "cannot promote someone else's posted job by id");

  r = await call(env, 'PATCH', '/api/jobs/' + jobId, { token, data: { salary: '$150K - $180K' } }); eq([r.status, r.body.job.salary], [200, '$150K - $180K'], 'job edited');
  r = await call(env, 'PATCH', '/api/jobs/' + jobId, { token: stranger, data: { salary: '$1' } }); eq(r.status, 404, "cannot edit someone else's job");
  r = await call(env, 'POST', '/api/jobs/' + jobId + '/close', { token }); eq(r.body.job.status, 'closed', 'job closed');
  r = await call(env, 'GET', '/api/public/export.json'); eq(r.body.jobs.length, 1, 'closed job leaves the export');
  r = await call(env, 'POST', '/api/jobs/' + jobId + '/renew', { token }); eq(r.body.job.status, 'live', 'job renewed');
  r = await post({ title: 'Data Engineer', apply_url: 'https://boards.greenhouse.io/acme/jobs/1' });
  r = await post({ title: 'ML Engineer', apply_url: 'https://boards.greenhouse.io/acme/jobs/1' }); eq(r.status, 429, 'daily posting limit');
  r = await call(env, 'GET', '/api/jobs', { token }); eq(r.body.jobs.length, 3, 'my jobs listed');
}

/* ---- 8. owner endpoints, test mode ---- */
{
  const env = newEnv(), token = await account(env);
  let r = await call(env, 'GET', '/api/admin/overview', { token }); eq(r.status, 403, 'a normal account is not the owner');
  r = await call(env, 'GET', '/api/admin/overview', { token: 'admin-secret' }); eq([r.status, r.body.users], [200, 1], 'owner overview');
  r = await call(env, 'GET', '/api/dev/pay/o_x'); eq(r.status, 401, 'test payments are not reachable in production');
  const dev = newEnv({ PAY_MODE: 'test', CRYPTOMUS_MERCHANT: '', CRYPTOMUS_API_KEY: '' }), t2 = await account(dev);
  r = await call(dev, 'POST', '/api/orders', { token: t2, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } });
  ok(r.body.order.pay_url.startsWith(API + '/api/dev/pay/'), 'test mode gives a local payment link');
  r = await call(dev, 'GET', new URL(r.body.order.pay_url).pathname); eq(r.status, 302, 'test payment redirects back to the account');
  r = await call(dev, 'GET', '/api/public/export.json'); eq(r.body.boosts.length, 1, 'test payment activates the order');
  const off = newEnv({ CRYPTOMUS_MERCHANT: '', CRYPTOMUS_API_KEY: '' }), t3 = await account(off);
  r = await call(off, 'POST', '/api/orders', { token: t3, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } }); eq(r.status, 503, 'no gateway keys: orders are refused, nothing is faked');
}
ok(Object.values(PRODUCTS).every((p) => p.usd > 0 && p.name), 'every product has a name and a price');

console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
