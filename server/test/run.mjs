// End-to-end tests for the API worker. Run:  node --no-warnings server/test/run.mjs
// Everything outside the worker is faked here: the site, the payment gateway, GitHub and employers' career pages.
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import worker, { md5, phpJson, gatewaySign, webhookSignatureOk, PRODUCTS, companyKey, sendMail, reconcileOrders } from '../src/worker.js';
import { D1 } from './d1.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const KEY = 'test-payment-key', SITE = 'https://site.test', API = 'https://api.test';
let passed = 0, failed = 0;
const ok = (cond, name, extra = '') => { if (cond) passed++; else { failed++; console.log('FAIL', name, extra); } };
const eq = (a, b, name) => ok(JSON.stringify(a) === JSON.stringify(b), name, `got ${JSON.stringify(a)} want ${JSON.stringify(b)}`);

/* ---- the outside world ----
   pages: address -> body (served as an HTML page unless "types" says otherwise); redirects: address -> where it sends you;
   hang: addresses that never answer; fetched: every address the worker opened, in order; asked: the orders the gateway was asked about;
   gatewayDown: the payment service is not answering. */
const world = { invoices: {}, githubCalls: 0, redirects: {}, types: {}, hang: new Set(), fetched: [], signals: [], asked: [], gatewayDown: false, pages: {
  [SITE + '/data/head.json']: JSON.stringify({ c: ['Stripe', 'Harvey', 'Crypto.com'], n: 3, r: [] }),
  [SITE + '/job/staff-engineer-stripe/']: '<html><title>Staff Engineer at Stripe</title><main>Open</main></html>',
  [SITE + '/job/old-role-stripe/']: '<html><title>Old role at Stripe</title><div class="banner">This job is closed as of Nov 1.</div></html>',
  [SITE + '/skills/rust/']: '<html>rust</html>', [SITE + '/jobs/engineering/']: '<html>eng</html>',
  'https://acme.dev/careers/senior-rust-engineer': '<html><h1>Senior Rust Engineer</h1> join Acme</html>',
  'https://acme.dev/careers': '<html>All our teams</html>',
  'https://boards.greenhouse.io/acme/jobs/1': '<html><div id="app"></div></html>',
} };
globalThis.fetch = async (input, init = {}) => {
  let url = typeof input === 'string' ? input : input.url;
  world.fetched.push(url);
  if (url.startsWith('https://api.cryptomus.com/')) {
    if (world.gatewayDown) return new Response('bad gateway', { status: 502 });
    const text = init.body, payload = JSON.parse(text);
    if (init.headers.sign !== gatewaySign(text, KEY) || init.headers.merchant !== 'merchant-1') return new Response('{"state":1}', { status: 401 });
    if (url.endsWith('/v1/payment')) {
      world.invoices[payload.order_id] = { ...payload, uuid: 'uuid-' + payload.order_id, status: 'check' };
      return Response.json({ state: 0, result: { uuid: 'uuid-' + payload.order_id, order_id: payload.order_id, url: 'https://pay.cryptomus.com/pay/uuid-' + payload.order_id, payment_status: 'check' } });
    }
    if (url.endsWith('/v1/payment/info')) {
      const inv = world.invoices[payload.order_id]; world.asked.push(payload.order_id);
      return inv ? Response.json({ state: 0, result: { order_id: payload.order_id, payment_status: inv.status, status: inv.status } }) : new Response('{"state":1}', { status: 422 });
    }
  }
  if (url.startsWith('https://api.github.com/')) { world.githubCalls++; return new Response(null, { status: 204 }); }
  world.signals.push(init.signal || null);
  if (world.hang.has(url)) return new Promise((_, reject) => { if (init.signal) init.signal.addEventListener('abort', () => reject(new Error('timed out'))); });
  for (let hops = 0; url in world.redirects; hops++) {
    // like the real fetch: with redirect "manual" the 3xx answer is handed back, otherwise it is followed without anyone looking
    if (init.redirect === 'manual') return new Response(null, { status: 302, headers: { Location: world.redirects[url] } });
    if (hops > 20) throw new TypeError('redirect count exceeded');
    url = new URL(world.redirects[url], url).href; world.fetched.push(url);
  }
  if (url in world.pages) return new Response(world.pages[url], { status: 200, headers: { 'Content-Type': world.types[url] || (url.endsWith('.json') ? 'application/json' : 'text/html; charset=utf-8') } });
  return new Response('not found', { status: 404, headers: { 'Content-Type': 'text/html' } });
};

/* ---- helpers ---- */
const newEnv = (extra = {}) => ({ DB: new D1().applySchema(path.join(here, '../schema.sql')), SITE_URL: SITE, SITE_ORIGINS: SITE, API_URL: API,
  CRYPTOMUS_MERCHANT: 'merchant-1', CRYPTOMUS_API_KEY: KEY, ADMIN_TOKEN: 'admin-secret', GITHUB_TOKEN: 'gh', GITHUB_REPO: 'o/r', ...extra });
let ipCounter = 0;
async function call(env, method, p, { token, data, ip, raw, origin, isolate = worker, ctx } = {}) {
  const headers = { 'CF-Connecting-IP': ip || '10.0.0.' + (++ipCounter % 250) };
  if (token) headers.Authorization = 'Bearer ' + token;
  if (origin) headers.Origin = origin;
  if (data || raw) headers['Content-Type'] = 'application/json';
  const res = await isolate.fetch(new Request(API + p, { method, headers, body: raw ?? (data ? JSON.stringify(data) : undefined) }), env, ctx);
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
/* ====================================================================================================================================
   Review findings 49-56 and 59. One block per finding; every test name says what must hold.
   ==================================================================================================================================== */
const GOOD = { company: 'Acme Robotics', company_url: 'https://acme.dev', title: 'Senior Rust Engineer', apply_url: 'https://acme.dev/careers/senior-rust-engineer', location: 'Berlin',
  remote: true, salary: '$140K - $170K', etype: 'Full-time', description: 'Build the control software for our warehouse robots. You will own the motion planning service, written in Rust, and work with a team of six.' };
const ATS = { title: 'Platform Engineer', apply_url: 'https://boards.greenhouse.io/acme/jobs/1' };       // another job, on a hiring system
const H1 = '<html><h1>Senior Rust Engineer</h1></html>';                                                   // a page that shows the job in GOOD
const one = async (env, sql, ...args) => { const row = await env.DB.prepare(sql).bind(...args).first(); return row ? Object.values(row)[0] : null; };
const nextDay = (env) => env.DB.exec("UPDATE jobs SET created_at = created_at - 90000; DELETE FROM rate WHERE k LIKE 'jobs:%'");
const newIsolate = async (tag) => (await import('../src/worker.js?isolate=' + tag)).default;               // a fresh copy of the worker, as after Cloudflare recycles it: nothing cached
const hook = (env, id, status = 'paid') => call(env, 'POST', '/api/webhooks/cryptomus', { raw: signedWebhook({ order_id: id, status }) });
async function quiet(run) {                    // runs something that is expected to log an error; returns the lines it logged
  const real = console.error, lines = []; console.error = (...a) => lines.push(a.map(String).join(' '));
  try { await run(); } finally { console.error = real; }
  return lines;
}

/* ---- 9. finding 49: an employer can post a second job, and as many more as they like ---- */
{
  const env = newEnv(), token = await account(env), headWas = world.pages[SITE + '/data/head.json'];
  const post = (over, isolate) => call(env, 'POST', '/api/jobs', { token, isolate, data: { ...GOOD, ...over } });
  let r = await post({}); eq(r.status, 200, 'first job posted');
  // The site is rebuilt, and its list of companies now has the employer's own company on it: the list holds every company with a job,
  // posted here or read from a careers page. A recycled worker reads that list afresh.
  world.pages[SITE + '/data/head.json'] = JSON.stringify({ c: ['Acme Robotics', 'Stripe', 'Harvey', 'Crypto.com'], n: 4, r: [] });
  const later = await newIsolate('49');
  r = await post(ATS, later); eq(r.status, 200, 'second job by the same employer is accepted once the site lists their company');
  r = await call(env, 'PATCH', '/api/jobs/' + (r.body.job || {}).id, { token, isolate: later, data: { salary: '$100K - $120K' } });
  eq(r.status, 200, 'a job can still be edited once the site lists the company');
  r = await post({ company: 'Stripe' }, later); eq([r.status, r.body.error], [409, 'listed'], 'a company listed from its own careers page is still refused');
  r = await post({ ...ATS, title: 'Data Engineer' }, later); eq(r.status, 200, 'third job on the same day');
  r = await post({ ...ATS, title: 'ML Engineer' }, later); eq([r.status, r.body.error], [429, 'limit'], 'the daily limit still holds: a fourth job waits for tomorrow');
  await nextDay(env);
  for (const title of ['ML Engineer', 'QA Engineer', 'Site Reliability Engineer']) r = await post({ ...ATS, title }, later);
  eq(r.status, 200, 'a sixth job is accepted the next day: there is no cap on how many jobs an employer has');
  r = await call(env, 'GET', '/api/public/export.json'); eq(r.body.jobs.length, 6, 'all six jobs are on the site');
  await nextDay(env);
  const burst = await Promise.all([1, 2, 3, 4, 5, 6].map((i) => post({ ...ATS, title: 'Support Engineer ' + i }, later)));
  eq(burst.map((x) => x.status).sort(), [200, 200, 200, 429, 429, 429], 'six posts sent at the same moment: three are published, as the daily limit says');
  world.pages[SITE + '/data/head.json'] = headWas;
}

/* ---- 10. finding 50: one company however it is spelled, and one account per company name ---- */
{
  eq(['Stripe', 'STRIPE', ' stripe ', 'Stripe!', 'Stripe.', 'Stripe  ', 'Stripe?!', 'Ｓｔｒｉｐｅ', 'Stri​pe', 'Stripe ™'].map(companyKey), Array(10).fill('stripe'),
    'company key: case, spaces and punctuation at the end do not make another company');
  eq(['Acme  Robotics', 'Acme Robotics, Inc.', 'Crypto.com', 'Acme & Sons', 'Stripe Inc', '?!'].map(companyKey), ['acme robotics', 'acme robotics, inc', 'crypto.com', 'acme & sons', 'stripe inc', ''],
    'company key: punctuation inside the name and suffixes are kept');
  const env = newEnv(), token = await account(env), rival = await account(env, 'rival@x.dev');
  const post = (who, over) => call(env, 'POST', '/api/jobs', { token: who, data: { ...GOOD, ...over } });
  let r;
  for (const name of ['Stripe!', 'STRIPE', '  stripe  ', 'Stripe...', 'CRYPTO.COM?']) {
    r = await post(token, { company: name }); eq([r.status, r.body.error], [409, 'listed'], 'posting as ' + JSON.stringify(name) + ' is refused: that is a listed company');
  }
  r = await post(token, { company: '?!' }); eq([r.status, r.body.error], [400, 'company'], 'punctuation alone is not a company name');
  r = await post(token, {}); eq([r.status, (r.body.job || {}).company], [200, 'Acme Robotics'], 'a company name is taken by its first job');
  for (const name of ['Acme Robotics', 'ACME ROBOTICS', 'acme  robotics', 'Acme Robotics!', ' Acme Robotics. ']) {
    r = await post(rival, { ...ATS, company: name }); eq([r.status, r.body.error], [409, 'company_taken'], 'another account cannot post as ' + JSON.stringify(name));
  }
  r = await post(rival, { ...ATS, company: 'Acme Robotics Inc' }); eq([r.status, (r.body.job || {}).company], [200, 'Acme Robotics Inc'], 'a longer name is another company: suffixes are not folded');
  const rivalJob = (r.body.job || {}).id;
  r = await post(token, { ...ATS, company: 'ACME ROBOTICS!' }); eq([r.status, (r.body.job || {}).company], [200, 'Acme Robotics'], 'the same account under another spelling: still one company, named as first written');
  eq((await env.DB.prepare("SELECT company, company_key FROM jobs WHERE company_key = 'acme robotics'").all()).results,
    [{ company: 'Acme Robotics', company_key: 'acme robotics' }, { company: 'Acme Robotics', company_key: 'acme robotics' }], 'a job keeps the name as shown and the name as compared');
  eq((await env.DB.prepare('SELECT k, name FROM companies ORDER BY k').all()).results,
    [{ k: 'acme robotics', name: 'Acme Robotics' }, { k: 'acme robotics inc', name: 'Acme Robotics Inc' }], 'each name is held once, with both forms');
  r = await call(env, 'GET', '/api/public/export.json'); eq([...new Set(r.body.jobs.map((j) => j.company))].sort(), ['Acme Robotics', 'Acme Robotics Inc'], 'the site gets one spelling per company');
  r = await call(env, 'PATCH', '/api/jobs/' + rivalJob, { token: rival, data: { company: 'acme robotics' } }); eq([r.status, r.body.error], [409, 'company_taken'], 'an edit cannot move a job under a name another account holds');
  r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'third@x.dev', password: 'longenough', company: 'acme robotics.' } });
  eq([r.status, r.body.error], [409, 'company_taken'], 'signing up under a name another account holds is refused');
  r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'third@x.dev', password: 'longenough', company: 'Stripe' } }); eq(r.status, 200, 'signing up with the name of a listed company is fine: it takes nothing');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'spotlight', target: { company: ' ACME ROBOTICS! ' } } });
  eq([r.status, (r.body.order || {}).label], [200, 'Acme Robotics'], 'a spotlight finds the company under any spelling');
  r = await call(env, 'POST', '/api/orders', { token, data: { product: 'spotlight', target: { company: 'Stripe!' } } }); eq([r.status, (r.body.order || {}).label], [200, 'Stripe'], 'and a listed company too');
  world.pages['https://nova.dev/jobs/rust'] = H1;
  const a = await account(env, 'a@nova.dev'), b = await account(env, 'b@nova.dev'), nova = { company_url: 'https://nova.dev', apply_url: 'https://nova.dev/jobs/rust' };
  const both = await Promise.all([post(a, { ...nova, company: 'Nova Labs' }), post(b, { ...nova, company: 'NOVA LABS.' })]);
  eq(both.map((x) => x.status).sort(), [200, 409], 'two accounts reaching for one name at the same moment: one gets it');
  eq(await one(env, "SELECT COUNT(*) FROM jobs WHERE company_key = 'nova labs'"), 1, 'and only that one has a job under it');
}

/* ---- 11. finding 51: an edit that changes the link, the title, the company or its site is checked like a new job ---- */
{
  const env = newEnv(), token = await account(env);
  let r = await call(env, 'POST', '/api/jobs', { token, data: GOOD });
  const id = r.body.job.id, edit = (data) => call(env, 'PATCH', '/api/jobs/' + id, { token, data }), page = world.pages[GOOD.apply_url];
  const opened = () => world.fetched.filter((u) => u === GOOD.apply_url).length;
  delete world.pages[GOOD.apply_url];                                    // the job page has gone since it was posted
  let before = opened();
  r = await edit({ salary: '$150K - $180K', location: 'Munich' }); eq([r.status, opened() - before], [200, 0], 'an edit that leaves link, title and company alone does not open the link again');
  before = opened();
  r = await edit({ company: 'Acme Robots' }); eq([r.status, opened() - before], [422, 1], 'an edit that changes the company runs the link check');
  r = await edit({ title: 'Senior Rust Developer' }); eq(r.status, 422, 'an edit that changes the title runs the link check');
  world.pages[GOOD.apply_url] = page;
  r = await edit({ company_url: 'https://evil-corp.com' }); eq(r.status, 422, 'an edit that changes the company site runs the link check');
  r = await edit({ apply_url: 'https://t.me/acme_hr' }); eq(r.status, 422, 'an edit that changes the link runs the link check');
  r = await edit({ apply_url: 'https://acme.dev/careers' }); eq(r.status, 422, 'an edit to a link that does not show the job is refused');
  r = await edit({ company: 'Stripe' }); eq([r.status, r.body.error], [409, 'listed'], 'an edit cannot move a job to a listed company');
  r = await edit({ company: 'Stripe!' }); eq([r.status, r.body.error], [409, 'listed'], 'however it is spelled');
  r = await call(env, 'GET', '/api/jobs', { token });
  eq([r.body.jobs[0].company, r.body.jobs[0].apply_url, r.body.jobs[0].company_url, r.body.jobs[0].salary], ['Acme Robotics', GOOD.apply_url, 'https://acme.dev', '$150K - $180K'], 'refused edits change nothing');
  r = await edit({ company: 'Acme Robots' }); eq([r.status, (r.body.job || {}).company], [200, 'Acme Robots'], 'a company change that passes the checks is saved');
  eq([await one(env, 'SELECT company_key FROM jobs WHERE id = ?', id), await one(env, "SELECT COUNT(*) FROM companies WHERE k = 'acme robots'")], ['acme robots', 1], 'with its key, and the new name is held by this account');
}

/* ---- 12. finding 52: activation is all or nothing, and happens once ---- */
{
  const env = newEnv({ PLUS_LIVE: '1' }), token = await account(env), FEATURED = { product: 'featured', target: { job: 'staff-engineer-stripe' } };
  const buy = async (data) => (await call(env, 'POST', '/api/orders', { token, data })).body.order.id;
  const status = (id) => one(env, 'SELECT status FROM orders WHERE id = ?', id), me = async () => (await call(env, 'GET', '/api/me', { token })).body.user;
  const breakWrites = (table, when = '') => env.DB.exec('CREATE TRIGGER boom BEFORE INSERT ON ' + table + ' ' + when + " BEGIN SELECT RAISE(ABORT, 'no room'); END");
  const mendWrites = () => env.DB.exec('DROP TRIGGER boom');
  let r, id = await buy(FEATURED);
  await breakWrites('placements');                 // the second write of an activation fails: a full disk, a lost connection
  await quiet(async () => { r = await hook(env, id); });
  eq(r.status, 500, 'a failed activation is not acknowledged, so the gateway sends the webhook again');
  eq([await status(id), await one(env, 'SELECT COUNT(*) FROM placements')], ['pending', 0], 'a failed activation leaves the order unpaid, not paid with nothing behind it');
  await mendWrites();
  r = await hook(env, id);
  eq([r.status, await status(id), await one(env, 'SELECT COUNT(*) FROM placements WHERE order_id = ?', id)], [200, 'paid', 1], 'the repeated webhook then activates the order in full');

  id = await buy({ product: 'pack5' });
  await breakWrites('credits');
  await quiet(() => hook(env, id));
  eq([await status(id), (await me()).credits], ['pending', 0], 'a pack whose credits could not be written stays unpaid');
  await mendWrites();
  await hook(env, id); eq([await status(id), (await me()).credits], ['paid', 5], 'and is delivered by the next webhook');

  id = await buy({ product: 'pack5' }); await Promise.all(Array.from({ length: 8 }, () => hook(env, id)));
  eq((await me()).credits, 10, 'eight webhooks at the same moment deliver a pack once');
  id = await buy({ product: 'plus1' }); await Promise.all(Array.from({ length: 8 }, () => hook(env, id)));
  eq((await me()).plus_until, new Date(Date.now() + 30 * 86400e3).toISOString().slice(0, 10), 'eight webhooks at the same moment add a month of Plus once');
  id = await buy({ product: 'pinned', target: { job: 'staff-engineer-stripe' } });
  world.invoices[id].status = 'paid'; await env.DB.prepare('UPDATE orders SET created_at = created_at - 600 WHERE id = ?').bind(id).run();
  await Promise.all([hook(env, id), worker.scheduled({}, env), call(env, 'GET', '/api/orders/' + id + '?refresh=1', { token }), reconcileOrders(env), hook(env, id)]);
  eq([await status(id), await one(env, 'SELECT COUNT(*) FROM placements WHERE order_id = ?', id)], ['paid', 1], 'a webhook, the cron and the account page together activate an order once');

  // a pack credit pays for a featured job in the same all-or-nothing step
  await env.DB.exec('UPDATE credits SET remaining = 0; UPDATE credits SET remaining = 1 WHERE rowid = (SELECT MIN(rowid) FROM credits)');
  const spend = () => call(env, 'POST', '/api/orders', { token, data: { ...FEATURED, use_credit: true } });
  await breakWrites('placements');
  await quiet(async () => { r = await spend(); });
  eq([r.status, (await me()).credits], [500, 1], 'a credit is not spent when the listing it pays for could not be recorded');
  await mendWrites();
  const two = await Promise.all([spend(), spend()]);
  eq([two.map((x) => x.status).sort(), (await me()).credits], [[200, 409], 0], 'one credit cannot pay for two listings sent at the same moment');
  eq(await one(env, "SELECT COUNT(*) FROM orders WHERE provider = 'credit' AND status = 'paid'"), 1, 'and exactly one of them is recorded as delivered');

  let refused = false;
  try { await env.DB.prepare("INSERT INTO placements (id, order_id, user_id, kind, target, starts_at, ends_at) SELECT 'p_twice', order_id, user_id, kind, target, starts_at, ends_at FROM placements LIMIT 1").run(); } catch { refused = true; }
  ok(refused, 'the database itself refuses a second placement for one order');
  refused = false;
  try { await env.DB.batch([env.DB.prepare("INSERT INTO meta (k, v) VALUES ('half', 'written')"), env.DB.prepare('INSERT INTO no_such_table (x) VALUES (1)')]); } catch { refused = true; }
  ok(refused && (await one(env, "SELECT COUNT(*) FROM meta WHERE k = 'half'")) === 0, 'the test database rolls a failed batch back as D1 does');
}

/* ---- 13. finding 53: a job that is closed, deleted or taken down is off the site, and so is what was bought for it ---- */
{
  const env = newEnv(), token = await account(env), stranger = await account(env, 'stranger@x.dev');
  const exported = async () => (await call(env, 'GET', '/api/public/export.json')).body;
  const placements = async (who = token) => (await call(env, 'GET', '/api/placements', { token: who })).body.placements.map((p) => p.kind + ':' + p.state).sort();
  const pay = async (who, data) => { const made = await call(env, 'POST', '/api/orders', { token: who, data }); await hook(env, made.body.order.id); };
  let r = await call(env, 'POST', '/api/jobs', { token, data: GOOD }); const first = r.body.job.id;
  r = await call(env, 'POST', '/api/jobs', { token, data: { ...GOOD, ...ATS } }); const second = r.body.job.id;
  await pay(token, { product: 'featured', target: { job_id: first } });
  await pay(token, { product: 'spotlight', target: { company: 'Acme Robotics' } });
  await pay(token, { product: 'spotlight', target: { company: 'Stripe' } });
  let x = await exported();
  eq([x.jobs.length, x.jobs[0].featured_until > '2026', x.sponsors.map((s) => s.company).sort()], [2, true, ['Acme Robotics', 'Stripe']], 'two jobs, a featured placement and two spotlights are on the site');

  r = await call(env, 'POST', '/api/jobs/' + second + '/archive', { token }); eq(r.status, 404, 'an action the API does not have is refused, not quietly treated as an edit');
  r = await call(env, 'DELETE', '/api/jobs/' + second, { token: stranger }); eq(r.status, 404, "someone else's job cannot be deleted");
  r = await call(env, 'POST', '/api/jobs/' + second + '/delete', { token }); eq(r.status, 200, 'the employer deletes a job');
  x = await exported(); eq(x.jobs.map((j) => j.id), [first], 'a deleted job leaves the export');
  r = await call(env, 'GET', '/api/jobs', { token }); eq(r.body.jobs.map((j) => j.id), [first], 'and the list of my jobs');
  r = await call(env, 'POST', '/api/jobs/' + second + '/renew', { token }); eq(r.status, 404, 'a deleted job cannot be published again');

  await call(env, 'POST', '/api/jobs/' + first + '/close', { token });
  x = await exported(); eq([x.jobs.length, x.sponsors.map((s) => s.company)], [0, ['Stripe']], 'a closed job leaves the export and takes the spotlight of its company with it; a listed company keeps its own');
  eq(await placements(), ['featured:paused', 'spotlight:live', 'spotlight:paused'], 'what was bought for a closed job is shown to its owner as paused');
  await call(env, 'POST', '/api/jobs/' + first + '/renew', { token });
  x = await exported(); eq([x.jobs.length, x.jobs[0].featured_until > '2026', x.sponsors.length], [1, true, 2], 'publishing it again brings back the job, its placement and the spotlight');
  r = await call(env, 'DELETE', '/api/jobs/' + first, { token }); eq(r.status, 200, 'DELETE on the job does the same as the delete action');
  x = await exported(); eq([x.jobs.length, x.sponsors.map((s) => s.company)], [0, ['Stripe']], 'the deleted job and the spotlight of its company are off the site');
  eq([await placements(), await one(env, 'SELECT cancelled FROM placements WHERE target = ?', 'direct:' + first)], [['spotlight:live', 'spotlight:paused'], 1], 'the placement bought for a deleted job is switched off for good');
  r = await call(env, 'OPTIONS', '/api/jobs/' + first, { origin: SITE }); ok(String(r.headers.get('Access-Control-Allow-Methods')).includes('DELETE'), 'the site is allowed to send DELETE');

  await nextDay(env);
  r = await call(env, 'POST', '/api/jobs', { token, data: GOOD }); const third = r.body.job.id;
  await pay(token, { product: 'pinned', target: { job_id: third } });
  x = await exported(); eq([x.jobs.length, x.jobs[0].pinned_until > '2026', x.sponsors.length], [1, true, 2], 'a new job, pinned, and the spotlight of its company is back');
  await call(env, 'POST', '/api/admin/jobs/' + third + '/remove', { token: 'admin-secret' });
  x = await exported();
  eq([x.jobs.length, x.sponsors.length, await one(env, 'SELECT cancelled FROM placements WHERE target = ?', 'direct:' + third)], [0, 1, 1], 'a job the owner took down leaves the export and its placement is switched off');
  r = await call(env, 'POST', '/api/jobs/' + third + '/renew', { token }); eq(r.status, 404, 'the employer cannot publish a taken-down job again');
  r = await call(env, 'POST', '/api/jobs', { token, data: { ...GOOD, ...ATS } });
  await env.DB.prepare('UPDATE jobs SET expires_at = 1 WHERE id = ?').bind(r.body.job.id).run();
  x = await exported(); eq(x.jobs.length, 0, 'a job whose 30 days ran out leaves the export');

  const scam = await account(env, 'scam@x.dev');
  world.pages['https://scam-co.com/jobs/rust'] = H1;
  await call(env, 'POST', '/api/jobs', { token: scam, data: { ...GOOD, company: 'Scam Co', company_url: 'https://scam-co.com', apply_url: 'https://scam-co.com/jobs/rust' } });
  await pay(scam, { product: 'featured', target: { job: 'staff-engineer-stripe' } }); await pay(scam, { product: 'spotlight', target: { company: 'Scam Co' } });
  x = await exported(); eq([x.jobs.length, x.boosts.length, x.sponsors.map((s) => s.company).sort()], [1, 1, ['Scam Co', 'Stripe']], 'an account with a job, a promoted job and a spotlight');
  await call(env, 'POST', '/api/admin/users/' + (await one(env, "SELECT id FROM users WHERE email = 'scam@x.dev'")) + '/ban', { token: 'admin-secret' });
  x = await exported(); eq([x.jobs.length, x.boosts.length, x.sponsors.map((s) => s.company)], [0, 0, ['Stripe']], 'after a ban its jobs and everything it bought are off the site');
  eq(await one(env, "SELECT COUNT(*) FROM companies WHERE k = 'scam co'"), 0, 'and the company name it held is free again');
}

/* ---- 14. finding 54: an order whose webhook never came is settled by asking the gateway ---- */
{
  const env = newEnv(), token = await account(env), MIN = 60, HOUR = 3600;
  const status = (id) => one(env, 'SELECT status FROM orders WHERE id = ?', id);
  // an order made `age` seconds ago that stands at `state` with the gateway (null: the gateway does not know it)
  const order = async (age, state, product = 'featured') => {
    await env.DB.exec("DELETE FROM rate WHERE k LIKE 'order:%'");
    const id = (await call(env, 'POST', '/api/orders', { token, data: { product, target: { job: 'staff-engineer-stripe' } } })).body.order.id;
    if (state) world.invoices[id].status = state; else delete world.invoices[id];
    await env.DB.prepare('UPDATE orders SET created_at = created_at - ? WHERE id = ?').bind(age, id).run();
    return id;
  };
  const o = { paid: await order(6 * MIN, 'paid'), young: await order(2 * MIN, 'paid', 'pinned'), cancelled: await order(20 * MIN, 'cancel'), failed: await order(10 * MIN, 'fail'),
    short: await order(10 * MIN, 'wrong_amount'), open: await order(30 * MIN, 'check'), lapsed: await order(80 * MIN, 'check'), confirming: await order(3 * HOUR, 'confirm_check'),
    late: await order(5 * HOUR, 'paid_over'), unknown: await order(3 * HOUR, null), ancient: await order(25 * HOUR, null), stuck: await order(26 * HOUR, 'process') };
  world.asked = [];
  await worker.scheduled({}, env);
  const after = {}; for (const k in o) after[k] = await status(o[k]);
  eq(after.paid, 'paid', 'cron: a paid invoice whose webhook never came is found');
  eq((await call(env, 'GET', '/api/public/export.json')).body.boosts.map((b) => b.kind), ['featured'], 'cron: and what was bought is switched on');
  eq([after.young, world.asked.includes(o.young)], ['pending', false], 'cron: an order of two minutes is left to its webhook');
  eq(after.cancelled, 'expired', 'cron: an invoice the gateway cancelled is closed');
  eq(after.failed, 'failed', 'cron: a failed payment is recorded as failed');
  eq(after.short, 'underpaid', 'cron: an underpayment is recorded');
  eq(after.open, 'pending', 'cron: an unpaid invoice that can still be paid stays open');
  eq(after.lapsed, 'expired', 'cron: an unpaid invoice past its lifetime is closed');
  eq(after.confirming, 'pending', 'cron: a payment still being confirmed is not closed after two hours');
  eq(after.late, 'paid', 'cron: an old invoice is activated, not closed, when the gateway says it was paid');
  eq(after.unknown, 'pending', 'cron: nothing is closed on a guess while the gateway cannot say');
  eq([after.ancient, after.stuck], ['expired', 'expired'], 'cron: after a day an order is given up on');
  world.asked = []; await worker.scheduled({}, env); eq(world.asked, [], 'cron: no invoice is asked about twice within a minute');

  const down = await order(10 * MIN, 'paid');
  world.gatewayDown = true; await worker.scheduled({}, env); world.gatewayDown = false;
  eq(await status(down), 'pending', 'cron: while the gateway is down the order waits');
  await env.DB.exec('UPDATE orders SET checked_at = checked_at - 61'); await worker.scheduled({}, env);
  eq(await status(down), 'paid', 'cron: and it is settled on a later run');

  const blocked = await order(10 * MIN, 'paid', 'pinned'), behind = await order(9 * MIN, 'paid');
  await env.DB.exec("CREATE TRIGGER boom BEFORE INSERT ON placements WHEN NEW.kind = 'pinned' BEGIN SELECT RAISE(ABORT, 'no room'); END");
  const logged = await quiet(() => worker.scheduled({}, env));
  await env.DB.exec('DROP TRIGGER boom');
  eq([await status(blocked), await status(behind), logged.length], ['pending', 'paid', 1], 'cron: an order that cannot be settled does not hold up the ones behind it');
  ok(logged.length === 1 && !logged[0].includes(KEY) && !logged[0].includes('merchant-1'), 'cron: what it logs about the failure carries no secret');

  const uid = await one(env, 'SELECT id FROM users'), t0 = Math.floor(Date.now() / 1000);
  for (let i = 0; i < 25; i++) {
    await env.DB.prepare("INSERT INTO orders (id, user_id, product, target, label, amount_usd, status, provider, created_at) VALUES (?, ?, 'featured', 'job:staff-engineer-stripe', 'x', 99, 'pending', 'cryptomus', ?)").bind('o_bulk' + i, uid, t0 - 600 - i).run();
    world.invoices['o_bulk' + i] = { status: 'check' };
  }
  world.asked = [];
  eq([(await reconcileOrders(env)).checked, new Set(world.asked.filter((id) => id.startsWith('o_bulk'))).size], [20, 20], 'cron: one run asks about twenty invoices, the longest unchecked first');
  await worker.scheduled({}, env);
  eq(new Set(world.asked.filter((id) => id.startsWith('o_bulk'))).size, 25, 'cron: the next run takes the rest');

  // the order page of the account
  await env.DB.exec("DELETE FROM orders WHERE id LIKE 'o_bulk%'; DELETE FROM rate");
  const mine = await order(0, 'check'); world.asked = [];
  const poll = () => call(env, 'GET', '/api/orders/' + mine + '?refresh=1', { token });
  let r = await call(env, 'GET', '/api/orders/' + mine, { token }); eq([r.body.order.status, world.asked.length], ['pending', 0], 'order page: a plain read does not go to the gateway');
  r = await poll(); eq([r.body.order.status, world.asked], ['pending', [mine]], 'order page: a refresh asks the gateway about that one order');
  world.invoices[mine].status = 'paid';
  let polls = await Promise.all([poll(), poll(), poll(), poll(), poll()]);
  eq([polls.map((p) => p.body.order.status).join(), world.asked.length], ['pending,pending,pending,pending,pending', 1], 'order page: polling reaches the gateway at most once in ten seconds');
  await env.DB.prepare('UPDATE orders SET checked_at = checked_at - 11 WHERE id = ?').bind(mine).run();
  polls = await Promise.all([poll(), poll(), poll(), poll(), poll()]);
  eq(world.asked.length, 2, 'order page: five refreshes at the same moment are one question to the gateway');
  r = await call(env, 'GET', '/api/orders/' + mine, { token }); eq(r.body.order.status, 'paid', 'order page: the payment is found without any webhook');
  const next = await order(0, 'paid', 'pinned'); world.asked = [];
  await env.DB.exec("UPDATE rate SET n = 60 WHERE k LIKE 'check:%'");
  r = await call(env, 'GET', '/api/orders/' + next + '?refresh=1', { token }); eq([r.status, r.body.order.status, world.asked.length], [200, 'pending', 0], 'order page: past the limit for one account it answers from what is stored');
  r = await call(env, 'GET', '/api/orders/' + next + '?refresh=1', { token: await account(env, 'other@x.dev') }); eq([r.status, world.asked.length], [404, 0], "order page: someone else's order is neither shown nor checked");

  const found = await order(3 * HOUR, 'paid'), dead = await order(3 * HOUR, 'cancel'); world.asked = [];
  r = await call(env, 'GET', '/api/orders', { token });
  eq([r.body.orders.find((x) => x.id === found).status, r.body.orders.find((x) => x.id === dead).status], ['paid', 'expired'], 'order list: an old invoice is closed only when the gateway says it was not paid');
  ok(world.asked.length <= 3, 'order list: it asks about a few invoices at most');

  const dev = newEnv({ PAY_MODE: 'test', CRYPTOMUS_MERCHANT: '', CRYPTOMUS_API_KEY: '' }), devToken = await account(dev);
  await call(dev, 'POST', '/api/orders', { token: devToken, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } });
  await dev.DB.exec('UPDATE orders SET created_at = created_at - 3 * 3600'); world.asked = [];
  await worker.scheduled({}, dev); eq([await one(dev, 'SELECT status FROM orders'), world.asked.length], ['expired', 0], 'cron: an order with no gateway behind it simply lapses');
}

/* ---- 15. finding 55: requests arriving together cannot get past a rate limit ---- */
{
  const env = newEnv(); await account(env, 'a@b.co');
  const guess = () => call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'wrong-guess' }, ip: '7.7.7.7' });
  const tries = await Promise.all(Array.from({ length: 30 }, guess));
  eq([tries.filter((x) => x.status === 401).length, tries.filter((x) => x.status === 429).length], [10, 20], 'thirty guesses at the same moment: ten are looked at, twenty are turned away');
  eq(await one(env, "SELECT n FROM rate WHERE k LIKE 'login:7.7.7.7:%'"), 30, 'every one of them is counted');
  let r = await call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'correct horse battery' }, ip: '7.7.7.7' }); eq(r.status, 429, 'the right password does not get past a spent limit either');
  await env.DB.exec("UPDATE rate SET reset_at = 1 WHERE k LIKE 'login:%'");
  r = await call(env, 'POST', '/api/auth/login', { data: { email: 'a@b.co', password: 'correct horse battery' }, ip: '7.7.7.7' });
  eq([r.status, await one(env, "SELECT n FROM rate WHERE k LIKE 'login:7.7.7.7:%'")], [200, 1], 'when the window is over the count starts again from one');
  const crowd = await Promise.all(Array.from({ length: 12 }, (_, i) => call(env, 'POST', '/api/auth/signup', { data: { email: 'crowd' + i + '@b.co', password: 'longenough' }, ip: '8.8.4.4' })));
  eq(crowd.filter((x) => x.status === 200).length, 5, 'twelve sign-ups from one address at the same moment: five accounts, as the limit says');
}

/* ---- 16. finding 56: the check of the link to apply does what its comment says ---- */
{
  const env = newEnv(), token = await account(env), JOB = GOOD.apply_url;
  const post = async (over) => { await env.DB.exec('DELETE FROM rate'); return call(env, 'POST', '/api/jobs', { token, data: { ...GOOD, ...over } }); };
  let r; world.fetched = [];
  for (const [url, what] of [['https://boss:secret@acme.dev/careers/senior-rust-engineer', 'a login in it'], ['https://:secret@acme.dev/careers/senior-rust-engineer', 'a password in it'],
    ['https://93.184.216.34/careers/senior-rust-engineer', 'an IP address'], ['https://2130706433/careers', 'an IP address written as one number'], ['https://0x7f.1/careers', 'an IP address written in hex'],
    ['https://[::1]/careers', 'an IPv6 address'], ['https://localhost/careers', 'localhost'], ['https://jobs.acme.local/careers', 'a private zone'], ['https://10.0.0.5.nip.io/careers', 'a name that stands for an address'],
    ['https://acme.dev:8443/careers/senior-rust-engineer', 'another port'], ['https://acme.dev./careers/senior-rust-engineer', 'a dot after the host name'], ['ftp://acme.dev/careers/senior-rust-engineer', 'not https'],
    ['javascript:alert(1)', 'a script'], ['https://acme.dev/careers/' + 'a'.repeat(600), 'more than 500 characters']]) {
    r = await post({ apply_url: url }); eq([r.status, r.body.error], [400, 'apply_url'], 'link refused: ' + what);
  }
  for (const [url, what] of [['https://boss:secret@acme.dev', 'a login in it'], ['https://127.0.0.1', 'an IP address'], ['https://acme.dev:444', 'another port'], ['http://acme.dev', 'plain http'], ['https://intranet', 'a bare name']]) {
    r = await post({ company_url: url }); eq([r.status, r.body.error], [400, 'company_url'], 'company site refused: ' + what);
  }
  eq(world.fetched.filter((u) => !u.startsWith(SITE)), [], 'none of the refused addresses was opened');

  Object.assign(world.redirects, { 'https://acme.dev/go/chat': 'https://t.me/acme_hr', 'https://acme.dev/go/away': 'https://evil-jobs.com/senior-rust-engineer', 'https://acme.dev/go/plain': 'http://acme.dev/careers/senior-rust-engineer',
    'https://acme.dev/go/inside': 'https://169.254.169.254/latest/meta-data', 'https://acme.dev/go/login': 'https://u:p@acme.dev/careers/senior-rust-engineer',
    'https://acme.dev/r1': '/r2', 'https://acme.dev/r2': 'https://www.acme.dev/careers/senior-rust-engineer', 'https://acme.dev/apply/platform': ATS.apply_url,
    'https://acme.dev/loop/a': '/loop/b', 'https://acme.dev/loop/b': '/loop/a', 'https://acme.dev/c0': '/c1', 'https://acme.dev/c1': '/c2', 'https://acme.dev/c2': '/c3', 'https://acme.dev/c3': '/c4', 'https://acme.dev/c4': JOB });
  Object.assign(world.pages, { 'https://t.me/acme_hr': H1, 'https://evil-jobs.com/senior-rust-engineer': H1, 'http://acme.dev/careers/senior-rust-engineer': H1, 'https://169.254.169.254/latest/meta-data': H1,
    'https://u:p@acme.dev/careers/senior-rust-engineer': H1, 'https://www.acme.dev/careers/senior-rust-engineer': H1 });
  for (const [path, what] of [['go/chat', 'a messenger'], ['go/away', 'another site'], ['go/plain', 'plain http'], ['go/inside', 'an IP address'], ['go/login', 'an address with a login']]) {
    r = await post({ apply_url: 'https://acme.dev/' + path }); eq(r.status, 422, 'a link that redirects to ' + what + ' is refused');
  }
  eq(world.fetched.filter((u) => /t\.me|evil-jobs|^http:|169\.254|u:p@/.test(u)), [], 'and what is behind such a redirect is never opened');
  world.signals = [];
  r = await post({ apply_url: 'https://acme.dev/r1' }); eq(r.status, 200, 'redirects inside the company site are followed, relative ones too');
  ok(world.signals.length === 3 && world.signals[0] instanceof AbortSignal && world.signals.every((s) => s === world.signals[0]), 'one time limit covers the link and every redirect after it');
  r = await post({ title: ATS.title, apply_url: 'https://acme.dev/apply/platform' }); eq(r.status, 200, 'a redirect from the company site to its hiring system is fine');
  world.fetched = [];
  r = await post({ apply_url: 'https://acme.dev/loop/a' }); eq([r.status, world.fetched.filter((u) => u.includes('/loop/')).length], [422, 5], 'a redirect loop is given up after four redirects');
  r = await post({ apply_url: 'https://acme.dev/c1' }); eq(r.status, 200, 'four redirects are followed');
  r = await post({ apply_url: 'https://acme.dev/c0' }); eq(r.status, 422, 'a fifth is not');

  const PDF = 'https://acme.dev/careers/senior-rust-engineer.pdf', XHTML = 'https://acme.dev/careers/senior-rust-engineer.xhtml';
  Object.assign(world.pages, { [PDF]: '%PDF-1.7 Senior Rust Engineer', 'https://acme.dev/careers/job.json': '{"title":"Senior Rust Engineer"}', [XHTML]: H1,
    'https://acme.dev/careers/engineers': '<html><h1>Senior Engineer</h1><p>We hire engineers of every kind.</p></html>',
    'https://acme.dev/careers/long-tail': '<html>' + ' '.repeat(700000) + H1, 'https://acme.dev/careers/long-head': H1 + ' '.repeat(3000000) });
  Object.assign(world.types, { [PDF]: 'application/pdf', [XHTML]: 'application/xhtml+xml; charset=utf-8' });
  r = await post({ apply_url: PDF }); eq(r.status, 422, 'a file is not a job page, whatever is written in it');
  r = await post({ apply_url: 'https://acme.dev/careers/job.json' }); eq(r.status, 422, 'neither is a data feed');
  r = await post({ apply_url: XHTML }); eq(r.status, 200, 'an XHTML page is a page');
  r = await post({ apply_url: 'https://acme.dev/careers/engineers' }); eq(r.status, 422, 'a page with only some words of the title is not the page of that job');
  r = await post({ apply_url: 'https://acme.dev/careers/long-tail' }); eq(r.status, 422, 'only the start of a very long page is read');
  r = await post({ apply_url: 'https://acme.dev/careers/long-head' }); eq(r.status, 200, 'a very long page with the job at the top is accepted');

  Object.assign(world.pages, { 'https://evil.co.uk/senior-rust-engineer': H1, 'https://jobs.britworks.co.uk/senior-rust-engineer': H1, 'https://badco.github.io/senior-rust-engineer': H1, 'https://goodco.github.io/jobs/senior-rust-engineer': H1 });
  const brit = { company: 'Brit Works', company_url: 'https://www.britworks.co.uk' }, good = { company: 'Good Co', company_url: 'https://goodco.github.io' };
  r = await post({ ...brit, apply_url: 'https://evil.co.uk/senior-rust-engineer' }); eq(r.status, 422, 'another site under the same country zone is not the company site');
  r = await post({ ...brit, apply_url: 'https://jobs.britworks.co.uk/senior-rust-engineer' }); eq(r.status, 200, 'a subdomain of the company site is');
  r = await post({ ...good, apply_url: 'https://badco.github.io/senior-rust-engineer' }); eq(r.status, 422, 'another tenant of a shared host is not the company site');
  r = await post({ ...good, apply_url: 'https://goodco.github.io/jobs/senior-rust-engineer' }); eq(r.status, 200, "the company's own page on a shared host is");

  const realTimeout = AbortSignal.timeout; let wait = 0;
  // the same deadline, only sooner, so the test does not sit there (and on a timer that keeps Node running until it fires)
  AbortSignal.timeout = (ms) => { wait = ms; const c = new AbortController(); setTimeout(() => c.abort(new DOMException('timed out', 'TimeoutError')), 30); return c.signal; };
  world.hang.add('https://acme.dev/careers/slow');
  r = await post({ apply_url: 'https://acme.dev/careers/slow' }); AbortSignal.timeout = realTimeout;
  eq([r.status, wait > 0 && wait <= 10000], [422, true], 'a page that never answers is given up on after a few seconds');

  await env.DB.exec('DELETE FROM rate');
  for (let i = 0; i < 31; i++) r = await call(env, 'POST', '/api/jobs', { token, data: { ...GOOD, apply_url: 'https://acme.dev/gone' } });
  eq([r.status, r.body.error], [429, 'rate_limited'], 'one account cannot make the service open links without end');
}

/* ---- 17. finding 59: password reset ---- */
{
  const outbox = [], env = newEnv({ MAIL: { send: async (m) => { outbox.push(m); } }, MAIL_FROM: 'no-reply@site.test' }), OLD = 'correct horse battery', NEW = 'a brand new password';
  const token = await account(env), login = (password, e = env) => call(e, 'POST', '/api/auth/login', { data: { email: 'boss@acme.dev', password } });
  const second = (await login(OLD)).body.token;
  const ask = (email, more = {}, e = env) => call(e, 'POST', '/api/auth/reset/request', { data: { email }, ...more });
  const confirm = (tok, password, e = env) => call(e, 'POST', '/api/auth/reset/confirm', { data: { token: tok, password } });
  const tokenIn = (mail) => (/\/account\/#reset=([a-f0-9]{64})\b/.exec(mail.text) || [])[1];
  const sha = (s) => createHash('sha256').update(s).digest('hex');
  let r;
  const logged = await quiet(async () => {
    const known = await ask('Boss@Acme.dev'), unknown = await ask('nobody@acme.dev');
    eq([known.status, known.body], [200, unknown.body], 'a reset request is answered the same for a known and an unknown email');
    eq([unknown.status, Object.keys(known.body).sort()], [200, ['message', 'ok']], 'and outside test mode the answer carries no token');
    eq([outbox.length, outbox[0].to, outbox[0].from], [1, 'boss@acme.dev', 'no-reply@site.test'], 'one mail leaves, to the account that exists');
    const tok = tokenIn(outbox[0]);
    ok(tok && outbox[0].text.includes(SITE + '/account/#reset=' + tok) && outbox[0].text.includes('30 minutes'), 'the mail carries a link to the account page');
    const rows = (await env.DB.prepare('SELECT * FROM resets').all()).results;
    ok(rows.length === 1 && rows[0].token_hash === sha(tok) && !JSON.stringify(rows).includes(tok), 'only the hash of the token is stored');
    eq(rows[0].expires_at - rows[0].created_at, 30 * 60, 'the link works for 30 minutes');

    r = await confirm('f'.repeat(64), NEW); eq([r.status, r.body.error], [400, 'reset'], 'a made-up token is refused');
    r = await confirm('nonsense', NEW); eq([r.status, r.body.error], [400, 'reset'], 'so is something that is not a token at all');
    r = await confirm(tok, 'short'); eq([r.status, r.body.error], [400, 'password'], 'a weak new password is refused');
    r = await call(env, 'GET', '/api/me', { token }); eq(r.status, 200, 'refused attempts leave the account as it was');
    r = await confirm(tok, NEW); eq(r.status, 200, 'the token and a new password are accepted');
    eq([(await call(env, 'GET', '/api/me', { token })).status, (await call(env, 'GET', '/api/me', { token: second })).status], [401, 401], 'every session of the account ends');
    eq([(await login(OLD)).status, (await login(NEW)).status], [401, 200], 'the old password stops working and the new one works');
    r = await confirm(tok, 'yet another password'); eq([r.status, (await login('yet another password')).status], [400, 401], 'a token works once');
    eq(await one(env, 'SELECT COUNT(*) FROM resets'), 0, 'and is gone from the database');

    await ask('boss@acme.dev'); const late = tokenIn(outbox[1]);
    await env.DB.exec('UPDATE resets SET expires_at = strftime(\'%s\', \'now\') - 1');
    r = await confirm(late, 'yet another password'); eq([r.status, r.body.error], [400, 'reset'], 'a link older than 30 minutes is refused');
    await worker.scheduled({}, env); eq(await one(env, 'SELECT COUNT(*) FROM resets'), 0, 'the cron clears links that ran out');

    await ask('boss@acme.dev'); const fourth = await ask('boss@acme.dev');
    eq([outbox.length, fourth.status, fourth.body], [3, 200, known.body], 'a fourth request for one account within the hour sends nothing and answers the same');
    for (let i = 0; i < 5; i++) r = await ask('nobody' + i + '@acme.dev', { ip: '5.5.5.5' });
    eq([r.status, (await ask('nobody@acme.dev', { ip: '5.5.5.5' })).status], [200, 429], 'one address can ask five times an hour');
    for (let i = 0; i < 10; i++) r = await call(env, 'POST', '/api/auth/reset/confirm', { data: { token: 'e'.repeat(64), password: NEW }, ip: '6.6.6.6' });
    eq((await call(env, 'POST', '/api/auth/reset/confirm', { data: { token: 'e'.repeat(64), password: NEW }, ip: '6.6.6.6' })).status, 429, 'and cannot try tokens without end');

    const race = tokenIn(outbox[2]);
    const pair = await Promise.all([confirm(race, 'first of two passwords'), confirm(race, 'second of two passwords')]);
    eq(pair.map((x) => x.status).sort(), [200, 400], 'two uses of one token at the same moment: one sets the password');
    const won = pair[0].status === 200 ? 'first of two passwords' : 'second of two passwords', lost = pair[0].status === 200 ? 'second of two passwords' : 'first of two passwords';
    eq([(await login(won)).status, (await login(lost)).status], [200, 401], 'and it is the password of the one that was accepted');

    const waited = [], uid = await one(env, 'SELECT id FROM users');
    await env.DB.exec('DELETE FROM rate');
    r = await ask('boss@acme.dev', { ctx: { waitUntil: (p) => waited.push(p) } }); await Promise.all(waited);
    eq([waited.length, outbox.length], [1, 4], 'the mail is handed to the runtime, so the answer does not wait for the mail service');
    await call(env, 'POST', '/api/admin/users/' + uid + '/ban', { token: 'admin-secret' });
    eq([await one(env, 'SELECT COUNT(*) FROM resets'), (await confirm(tokenIn(outbox[3]), NEW)).status], [0, 400], 'a ban cancels the links that were out');
    r = await ask('boss@acme.dev'); eq([r.body, outbox.length], [known.body, 4], 'a banned account gets no link, and the answer does not say so');
  });
  ok(!outbox.some((m) => logged.join('\n').includes(tokenIn(m))) && logged.length === 0, 'nothing about a reset is written to the log');

  const plain = newEnv(); await account(plain);                          // no mail binding: the state of things until a mail service is connected
  r = await ask('boss@acme.dev', {}, plain);
  eq([r.status, Object.keys(r.body).sort(), await one(plain, 'SELECT COUNT(*) FROM resets')], [200, ['message', 'ok'], 1], 'without a mail service the request is taken in the same way');
  eq(await sendMail({}, 'a@b.co', 'subject', 'text'), { sent: false }, 'sendMail: no binding, nothing sent, and it says so');
  eq(await sendMail({ MAIL: { send: async () => {} } }, 'a@b.co', 'subject', 'text'), { sent: true }, 'sendMail: with a binding the mail is handed over');
  let said;
  const lines = await quiet(async () => { said = await sendMail({ MAIL: { send: async () => { throw new Error('mail service is down: text was SECRET-LINK'); } } }, 'a@b.co', 'subject', 'SECRET-LINK'); });
  ok(said.sent === false && lines.length === 1 && !lines[0].includes('SECRET-LINK') && !lines[0].includes('a@b.co'), 'sendMail: a failing mail service is reported without the text or the address');

  const dev = newEnv({ PAY_MODE: 'test' }); await account(dev);
  const mineDev = await ask('boss@acme.dev', {}, dev), nobodyDev = await ask('nobody@acme.dev', {}, dev);
  ok(/^[a-f0-9]{64}$/.test(mineDev.body.token) && /^[a-f0-9]{64}$/.test(nobodyDev.body.token) && mineDev.body.message === nobodyDev.body.message, 'test mode: the answer carries a token, in the same shape for an unknown email');
  eq([(await confirm(nobodyDev.body.token, NEW, dev)).status, (await confirm(mineDev.body.token, NEW, dev)).status, (await login(NEW, dev)).status], [400, 200, 200], 'test mode: the token of a real account sets the password, the other opens nothing');
}
ok(Object.values(PRODUCTS).every((p) => p.usd > 0 && p.name), 'every product has a name and a price');

console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
