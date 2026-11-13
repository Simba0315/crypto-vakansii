// End-to-end tests for the API worker. Run:  node --no-warnings server/test/run.mjs
// Everything outside the worker is faked here: the site, the payment gateway, GitHub and employers' career pages.
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import worker, { md5, phpJson, gatewaySign, webhookSignatureOk, PRODUCTS, companyKey, sendMail, reconcileOrders, siteDomain, freeMail, throwawayMail, hiringSystem, lookalike, brandIn, domainAge, screenPosting,
  recheckLinks } from '../src/worker.js';
import { D1 } from './d1.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const KEY = 'test-payment-key', SITE = 'https://site.test', API = 'https://api.test';
let passed = 0, failed = 0;
const ok = (cond, name, extra = '') => { if (cond) passed++; else { failed++; console.log('FAIL', name, extra); } };
const eq = (a, b, name) => ok(JSON.stringify(a) === JSON.stringify(b), name, `got ${JSON.stringify(a)} want ${JSON.stringify(b)}`);

/* ---- the outside world ----
   pages: address -> body (served as an HTML page unless "types" says otherwise); redirects: address -> where it sends you;
   hang: addresses that never answer; gates: address -> a promise the answer waits for (to hold two requests at the same point);
   fetched: every address the worker opened, in order; asked: the orders the gateway was asked about;
   gatewayDown: the payment service is not answering. */
const world = { invoices: {}, githubCalls: 0, redirects: {}, types: {}, hang: new Set(), gates: {}, fetched: [], signals: [], asked: [], gatewayDown: false, pages: {
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
  if (world.gates[url]) await world.gates[url];
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
async function call(env, method, p, { token, data, ip, raw, origin, isolate = worker, ctx, ua } = {}) {
  const headers = { 'CF-Connecting-IP': ip || '10.0.0.' + (++ipCounter % 250) };
  if (ua) headers['User-Agent'] = ua;
  if (token) headers.Authorization = 'Bearer ' + token;
  if (origin) headers.Origin = origin;
  if (data || raw) headers['Content-Type'] = 'application/json';
  const res = await isolate.fetch(new Request(API + p, { method, headers, body: raw ?? (data ? JSON.stringify(data) : undefined) }), env, ctx);
  let out = null; try { out = await res.clone().json(); } catch {}
  return { status: res.status, body: out, headers: res.headers };
}
const signedWebhook = (fields, key = KEY, unicode = true) => { const text = phpJson(fields, unicode); return phpJson({ ...fields, sign: gatewaySign(text, key) }, unicode); };
// Sections 1 to 17 were written before the fraud checks (sections 18 and on) and are about what an established employer can do: buy,
// post three jobs a day, edit, close. Since then a new account must confirm its email before it can post or buy, and its jobs wait
// for a person until it is trusted (two approved jobs, fourteen days). So this helper makes the account those sections mean: one whose
// email is confirmed and that has earned its trust. It is written straight into the database, because earning it through the API is
// what section 21 tests. A brand-new account is made with fresh() further down.
async function account(env, email = 'boss@acme.dev') {
  const r = await call(env, 'POST', '/api/auth/signup', { data: { email, password: 'correct horse battery' } });
  await env.DB.prepare('UPDATE users SET confirmed_at = created_at, approved_jobs = 2, created_at = created_at - 15 * 86400 WHERE email = ?').bind(email).run();
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
  // the rival signs up on the same email domain: since the fraud checks, the company site and the link to apply of a job must be on the
  // domain of the account's email, so an account on x.dev could not post acme.dev links at all (that rule has its own tests in section 19)
  const env = newEnv(), token = await account(env), rival = await account(env, 'rival@acme.dev');
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
  // the two jobs deleted above have the titles posted next; since the duplicate guard, a removed job blocks the same title and company
  // for 30 days, so this test lets those days pass (the guard itself is tested in section 20)
  await env.DB.exec('UPDATE jobs SET ended_at = ended_at - 31 * 86400');
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

  const scam = await account(env, 'scam@scam-co.com');        // was scam@x.dev: a job must now be on the domain of the account's email
  world.pages['https://scam-co.com/jobs/rust'] = H1;
  await call(env, 'POST', '/api/jobs', { token: scam, data: { ...GOOD, company: 'Scam Co', company_url: 'https://scam-co.com', apply_url: 'https://scam-co.com/jobs/rust' } });
  await pay(scam, { product: 'featured', target: { job: 'staff-engineer-stripe' } }); await pay(scam, { product: 'spotlight', target: { company: 'Scam Co' } });
  x = await exported(); eq([x.jobs.length, x.boosts.length, x.sponsors.map((s) => s.company).sort()], [1, 1, ['Scam Co', 'Stripe']], 'an account with a job, a promoted job and a spotlight');
  await call(env, 'POST', '/api/admin/users/' + (await one(env, "SELECT id FROM users WHERE email = 'scam@scam-co.com'")) + '/ban', { token: 'admin-secret' });
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
  // every call posts the same title and company with another link; since the duplicate guard that is refused while the first one is
  // there, so the jobs table is emptied along with the limits: this section is about the link check alone
  const post = async (over, who = token) => { await env.DB.exec('DELETE FROM rate; DELETE FROM jobs'); return call(env, 'POST', '/api/jobs', { token: who, data: { ...GOOD, ...over } }); };
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
  // these four were posted by boss@acme.dev; the company site must now be on the domain of the account's email, so each company gets an
  // account of its own. What they check is unchanged: where one owner's part of a host name ends.
  const britBoss = await account(env, 'hr@britworks.co.uk'), goodBoss = await account(env, 'hr@goodco.github.io');
  r = await post({ ...brit, apply_url: 'https://evil.co.uk/senior-rust-engineer' }, britBoss); eq(r.status, 422, 'another site under the same country zone is not the company site');
  r = await post({ ...brit, apply_url: 'https://jobs.britworks.co.uk/senior-rust-engineer' }, britBoss); eq(r.status, 200, 'a subdomain of the company site is');
  r = await post({ ...good, apply_url: 'https://badco.github.io/senior-rust-engineer' }, goodBoss); eq(r.status, 422, 'another tenant of a shared host is not the company site');
  r = await post({ ...good, apply_url: 'https://goodco.github.io/jobs/senior-rust-engineer' }, goodBoss); eq(r.status, 200, "the company's own page on a shared host is");

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
  outbox.length = 0;                 // signing up now sends a mail of its own, the link that confirms the email (section 18); this section counts reset mails
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
/* ====================================================================================================================================
   Fraud checks, parts A to F of the owner's instruction: fraud is designed out before employers post by themselves.
   One section per part; every test name starts with the letter of its part and says what must hold.
   ==================================================================================================================================== */
const PASS = 'correct horse battery', ADMIN = 'admin-secret';
const SLACK = 300;                 // seconds two steps of a test may lie apart on a slow or busy machine, where a test compares moments in time
const mailbox = () => { const outbox = []; return { outbox, MAIL: { send: async (m) => { outbox.push(m); } }, MAIL_FROM: 'no-reply@site.test' }; };
// A brand-new account as sign-up leaves it, with only its email confirmed: not trusted, so its jobs wait for review. The confirmation is
// written into the database here; the link itself is what section 18 tests.
async function fresh(env, email) {
  const r = await call(env, 'POST', '/api/auth/signup', { data: { email, password: PASS } });
  await env.DB.prepare('UPDATE users SET confirmed_at = created_at WHERE email = ?').bind(email).run();
  return r.body.token;
}
// the jobs of one employer: the company site and a page per job on its own domain, each page showing the title
const employer = (domain, company) => (title, over = {}) => {
  const apply_url = 'https://' + domain + '/jobs/' + title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  world.pages[apply_url] = '<html><h1>' + title + '</h1></html>';
  return { ...GOOD, company, company_url: 'https://' + domain, title, apply_url, ...over };
};
const statusOf = (env, id) => one(env, 'SELECT status FROM jobs WHERE id = ?', id);
const exportedJobs = async (env) => (await call(env, 'GET', '/api/public/export.json')).body.jobs;

/* ---- 18. A: a work email, tied to its domain, and confirmed before anything is published ---- */
{
  const box = mailbox(), outbox = box.outbox, env = newEnv(box);
  const sign = (email, e = env) => call(e, 'POST', '/api/auth/signup', { data: { email, password: PASS } });
  const confirm = (tok, e = env) => call(e, 'POST', '/api/auth/confirm', { data: { token: tok } });
  const linkIn = (mail) => (/\/account\/#confirm=([a-f0-9]{64})\b/.exec(mail.text) || [])[1];
  const sha = (s) => createHash('sha256').update(s).digest('hex');
  const NOVA = employer('nova.dev', 'Nova Labs')('Senior Rust Engineer');
  let r;
  const logged = await quiet(async () => {
    // a person looking for work has a free mailbox: the account is made (it can buy Plus), has no company domain and cannot post a job
    {
      const box2 = mailbox(), seekers = newEnv(box2);
      for (const host of ['gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.co.uk', 'mail.yahoo.co.jp', 'ymail.com', 'outlook.com', 'hotmail.fr', 'live.com', 'msn.com', 'aol.com', 'icloud.com', 'me.com', 'mac.com',
        'proton.me', 'protonmail.com', 'pm.me', 'gmx.de', 'mail.com', 'yandex.ru', 'mail.ru', 'zoho.com', 'tutanota.com', 'tuta.io', 'fastmail.com', 'hey.com', 'qq.com', 'vip.163.com', '126.com', 'GMAIL.COM']) {
        r = await sign((host === 'GMAIL.COM' ? 'Shouting.Seeker' : 'seeker') + '@' + host, seekers);
        eq([r.status, r.body.user && r.body.user.domain], [200, ''], 'A: a free mailbox gets a job seeker’s account with no company domain: ' + host);
      }
      eq(await one(seekers, "SELECT COUNT(*) FROM users WHERE domain != ''"), 0, 'A: no account on a free mailbox is tied to a domain');
      r = await call(seekers, 'POST', '/api/auth/signup', { data: { email: 'someone@gmail.com', password: PASS, company: 'Acme' } });
      eq([r.status, r.body.user.company], [200, ''], 'A: a job seeker’s account does not take a company name');
      const seeker = r.body.token;
      await seekers.DB.prepare("UPDATE users SET confirmed_at = created_at WHERE email = 'someone@gmail.com'").run();
      r = await call(seekers, 'POST', '/api/jobs/preview', { token: seeker, data: NOVA });
      eq([r.status, r.body.error], [403, 'work_email'], 'A: a job seeker’s account cannot preview a job');
      r = await call(seekers, 'POST', '/api/jobs', { token: seeker, data: NOVA });
      eq([r.status, r.body.error, await one(seekers, 'SELECT COUNT(*) FROM jobs')], [403, 'work_email', 0], 'A: a job seeker’s account cannot post a job, confirmed or not');
      ok(/company’s own domain/.test(r.body.message), "A: the refusal says an address on the company's own domain is needed");
      r = await call(seekers, 'GET', '/api/me', { token: seeker });
      eq([r.status, r.body.user.domain], [200, ''], 'A: the account page is told that this account has no company domain');
    }
    for (const host of ['mailinator.com', 'guerrillamail.com', '10minutemail.com', 'tempmail.com', 'yopmail.com', 'sharklasers.com', 'trashmail.com', 'getnada.com', 'dispostable.com', 'grr.la']) {
      r = await sign('founder@' + host); eq([r.status, r.body.error], [400, 'throwaway_email'], 'A: sign-up with a throwaway mailbox is refused: ' + host);
    }
    eq([await one(env, 'SELECT COUNT(*) FROM users'), outbox.length], [0, 0], 'A: a refused sign-up leaves no account and sends no mail');
    eq(['mailinator.com', 'x.yopmail.com', 'gmail.com', 'acme.dev'].map(throwawayMail), [true, true, false, false], 'A: throwaway mailboxes are told from free ones');
    eq(['gmail.com', 'smtp.gmail.com', 'yahoo.com.au', 'proton.me', 'acme.dev', 'mail.acme.dev', 'proton.ch', 'livepeer.org', 'megmail.com', 'me.io'].map(freeMail), [true, true, true, true, false, false, false, false, false, false],
      'A: free mailboxes are told from company domains by the registrable domain, not by a look at the letters');

    const zones = 'co.uk com.au co.jp com.br co.in com.sg co.nz com.mx co.za com.tr co.kr com.hk com.tw com.ar com.co com.pl com.ua'.split(' ');
    eq(zones.map((z) => siteDomain('careers.eu.acme.' + z)), zones.map((z) => 'acme.' + z), 'A: registrable domain: three labels are kept under each listed country zone');
    eq(['acme.dev', 'www.acme.dev', 'jobs.eu.acme.dev', 'ACME.Dev', 'x.acme.org.uk', 'acme.com.cn', 'goodco.github.io'].map(siteDomain), ['acme.dev', 'acme.dev', 'acme.dev', 'acme.dev', 'acme.org.uk', 'acme.com.cn', 'goodco.github.io'],
      'A: registrable domain: otherwise the last two labels, and one more for other country zones and shared hosts');
    r = await sign('Recruiting@Mail.Brightside.Co.UK');
    eq([r.status, r.body.user.domain, await one(env, "SELECT domain FROM users WHERE email = 'recruiting@mail.brightside.co.uk'")], [200, 'brightside.co.uk', 'brightside.co.uk'], "A: the account stores the registrable domain of its email");

    outbox.length = 0;
    r = await sign('hr@nova.dev'); const token = r.body.token, uid = r.body.user.id;
    eq([r.status, r.body.user.confirmed, r.body.user.trusted, Object.keys(r.body).sort()], [200, false, false, ['token', 'user']], 'A: a new account is unconfirmed, and outside test mode the answer carries no confirmation token');
    eq([outbox.length, outbox[0].to, outbox[0].from, outbox[0].subject], [1, 'hr@nova.dev', 'no-reply@site.test', 'Confirm your email'], 'A: sign-up sends one mail, to the address that signed up');
    const tok = linkIn(outbox[0]);
    ok(tok && tok !== token && outbox[0].text.includes(SITE + '/account/#confirm=' + tok) && outbox[0].text.includes('24 hours'), 'A: the mail carries a link to the account page that confirms the email');
    const rows = (await env.DB.prepare('SELECT * FROM confirms WHERE user_id = ?').bind(uid).all()).results;
    ok(rows.length === 1 && rows[0].token_hash === sha(tok) && !JSON.stringify(rows).includes(tok), 'A: only the hash of the confirmation token is stored');
    eq(rows[0].expires_at - rows[0].created_at, 24 * 3600, 'A: the link works for 24 hours');

    r = await call(env, 'POST', '/api/auth/login', { data: { email: 'hr@nova.dev', password: PASS } }); eq(r.status, 200, 'A: an unconfirmed account can sign in');
    const before = world.fetched.length;
    r = await call(env, 'POST', '/api/jobs', { token, data: NOVA }); eq([r.status, r.body.error], [403, 'confirm_email'], 'A: an unconfirmed account cannot publish a job');
    r = await call(env, 'POST', '/api/orders', { token, data: { product: 'featured', target: { job: 'staff-engineer-stripe' } } }); eq([r.status, r.body.error], [403, 'confirm_email'], 'A: nor buy a placement');
    r = await call(env, 'POST', '/api/orders', { token, data: { product: 'pack5' } }); eq([r.status, r.body.error], [403, 'confirm_email'], 'A: nor a pack of placements');
    r = await call(env, 'POST', '/api/jobs/preview', { token, data: NOVA });
    eq([r.status, r.body.ok, r.body.confirmed, r.body.job.title, await one(env, 'SELECT COUNT(*) FROM jobs')], [200, true, false, NOVA.title, 0], 'A: it can have a draft checked, and nothing is stored');
    ok(!world.fetched.slice(before).includes(NOVA.apply_url), 'A: checking a draft opens no link');
    r = await call(env, 'POST', '/api/jobs/preview', { token, data: { ...NOVA, description: NOVA.description + ' A registration fee of $49 is required before you start.' } });
    eq([r.status, r.body.error, Array.isArray(r.body.reasons)], [422, 'rejected', true], 'A: a draft the screen would reject is told so, with the reasons');
    eq([await one(env, 'SELECT COUNT(*) FROM orders'), await one(env, 'SELECT COUNT(*) FROM stats')], [0, 0], 'A: none of this left an order or a count behind');

    r = await confirm('f'.repeat(64)); eq([r.status, r.body.error], [400, 'confirm'], 'A: a made-up confirmation token is refused');
    r = await confirm('nonsense'); eq([r.status, r.body.error], [400, 'confirm'], 'A: so is something that is not a token at all');
    r = await call(env, 'GET', '/api/me', { token }); eq(r.body.user.confirmed, false, 'A: refused attempts leave the account unconfirmed');
    r = await confirm(tok); eq([r.status, (await call(env, 'GET', '/api/me', { token })).body.user.confirmed], [200, true], 'A: the token from the mail confirms the account');
    r = await confirm(tok); eq([r.status, await one(env, 'SELECT COUNT(*) FROM confirms WHERE user_id = ?', uid)], [400, 0], 'A: a confirmation token works once and is gone from the database');
    r = await call(env, 'POST', '/api/jobs', { token, data: NOVA }); eq(r.status, 200, 'A: a confirmed account can post a job');
    r = await call(env, 'POST', '/api/orders', { token, data: { product: 'pack5' } }); eq(r.status, 200, 'A: and buy');
    r = await call(env, 'POST', '/api/auth/confirm/request', { token }); eq([r.status, r.body.confirmed, outbox.length], [200, true, 1], 'A: asking for a link again when the account is confirmed sends nothing');

    r = await sign('late@orbit.dev'); const late = r.body.token, lateTok = linkIn(outbox[1]);
    await env.DB.exec("UPDATE confirms SET expires_at = strftime('%s', 'now') - 1");
    r = await confirm(lateTok); eq([r.status, r.body.error], [400, 'confirm'], 'A: a link older than 24 hours is refused');
    await worker.scheduled({}, env); eq(await one(env, 'SELECT COUNT(*) FROM confirms'), 0, 'A: the cron clears confirmation links that ran out');
    r = await call(env, 'POST', '/api/auth/confirm/request'); eq(r.status, 401, 'A: asking for a new link needs a session');
    r = await call(env, 'POST', '/api/auth/confirm/request', { token: late });
    eq([r.status, r.body.confirmed, Object.keys(r.body).sort(), outbox.length, outbox[2].to], [200, false, ['confirmed', 'message', 'ok'], 3, 'late@orbit.dev'], 'A: a new link can be asked for, and outside test mode the answer carries no token');
    const pair = await Promise.all([confirm(linkIn(outbox[2])), confirm(linkIn(outbox[2]))]);
    eq(pair.map((x) => x.status).sort(), [200, 400], 'A: two uses of one confirmation token at the same moment: one confirms');
    r = await sign('slow@vega.dev'); const slow = r.body.token;
    for (let i = 0; i < 3; i++) r = await call(env, 'POST', '/api/auth/confirm/request', { token: slow });
    eq([r.status, (await call(env, 'POST', '/api/auth/confirm/request', { token: slow })).status], [200, 429], 'A: an account can ask for three new links an hour');
    for (let i = 0; i < 10; i++) r = await call(env, 'POST', '/api/auth/confirm', { data: { token: 'e'.repeat(64) }, ip: '6.6.6.6' });
    eq((await call(env, 'POST', '/api/auth/confirm', { data: { token: 'e'.repeat(64) }, ip: '6.6.6.6' })).status, 429, 'A: and nobody can try confirmation tokens without end');

    r = await sign('gone@comet.dev'); const goneTok = linkIn(outbox[outbox.length - 1]);
    await call(env, 'POST', '/api/admin/accounts/' + r.body.user.id + '/ban', { token: ADMIN });
    eq([(await confirm(goneTok)).status, await one(env, "SELECT COUNT(*) FROM confirms c JOIN users u ON u.id = c.user_id WHERE u.email = 'gone@comet.dev'")], [400, 0], 'A: a ban cancels the confirmation links that were out');
  });
  ok(logged.length === 0, 'A: nothing about a sign-up or a confirmation is written to the log');

  const dev = newEnv({ PAY_MODE: 'test' }); r = await sign('hr@nova.dev', dev);
  ok(/^[a-f0-9]{64}$/.test(r.body.confirm_token) && r.body.confirm_token !== r.body.token, 'A: test mode: the sign-up answer carries the confirmation token');
  eq([(await confirm(r.body.confirm_token, dev)).status, (await call(dev, 'GET', '/api/me', { token: r.body.token })).body.user.confirmed], [200, true], 'A: test mode: and that token confirms the account');
  r = await sign('second@nova.dev', dev); r = await call(dev, 'POST', '/api/auth/confirm/request', { token: r.body.token });
  eq([/^[a-f0-9]{64}$/.test(r.body.token), (await confirm(r.body.token, dev)).status], [true, 200], 'A: test mode: a new link is answered with its token too');
}

/* ---- 19. B: a job is tied to the domain of the account's email; hiring systems; look-alike names ---- */
{
  const env = newEnv(), token = await account(env, 'hr@nova.dev');          // an established account: the review of new accounts is section 21
  const NOVA = employer('nova.dev', 'Nova Labs')('Senior Rust Engineer'), APP = '<html><div id="app"></div></html>';
  Object.assign(world.pages, { 'https://careers.nova.dev/senior-rust-engineer': H1, 'https://nova.recruitee.com/o/senior-rust-engineer': APP, 'https://nova.myworkdayjobs.com/senior-rust-engineer': H1 });
  // the same title is posted again and again with another link, so the jobs and the limits are emptied before each one (duplicates: section 20)
  const post = async (over, who = token, e = env) => { await e.DB.exec('DELETE FROM rate; DELETE FROM jobs'); return call(e, 'POST', '/api/jobs', { token: who, data: { ...NOVA, ...over } }); };
  const opened = (u) => world.fetched.filter((x) => x === u).length;
  let r, was = opened(GOOD.apply_url);
  r = await post({ apply_url: GOOD.apply_url });
  eq([r.status, r.body.error, opened(GOOD.apply_url) - was], [422, 'apply_url', 0], "B: a link to apply on another company's domain is refused although its page shows the job, and it is not opened");
  r = await post({ company_url: 'https://acme.dev' }); eq([r.status, r.body.error, /nova\.dev/.test(r.body.message)], [422, 'company_url', true], "B: a company site off the account's domain is refused, and the refusal names the domain");
  r = await post({}); eq([r.status, r.body.job.status, await one(env, 'SELECT apply_host FROM jobs')], [200, 'live', 'nova.dev'], "B: a job on the account's own domain is accepted, and the host its link ended on is kept");
  r = await post({ apply_url: 'https://careers.nova.dev/senior-rust-engineer', company_url: 'https://www.nova.dev' }); eq(r.status, 200, "B: a subdomain of the account's domain has the same owner");
  r = await post({ company_url: undefined }); eq([r.status, (r.body.job || {}).company_url], [200, 'https://nova.dev'], "B: the company site may be left out: it is then the account's domain");
  r = await post({ apply_url: 'https://nova.recruitee.com/o/senior-rust-engineer' });
  eq([r.status, r.body.job.status, await one(env, 'SELECT apply_host FROM jobs')], [200, 'live', 'nova.recruitee.com'], 'B: a link on a known hiring system is accepted; for a trusted account the job is live');
  r = await post({ apply_url: 'https://join.com/companies/nova/senior-rust-engineer' }); eq([r.status, r.body.error], [422, 'apply_url'], 'B: a host that is not one of the listed hiring systems is refused');
  r = await post({ apply_url: 'https://nova.myworkdayjobs.com/senior-rust-engineer' }); eq([r.status, await one(env, 'SELECT apply_host FROM jobs')], [200, 'nova.myworkdayjobs.com'], 'B: a tenant of a hiring system sold under contract (Workday) is accepted');
  const novice = await fresh(env, 'new@nova.dev');
  r = await post({ company: 'Nova Research', apply_url: 'https://nova.recruitee.com/o/senior-rust-engineer' }, novice);
  ok(r.status === 200 && r.body.job.status === 'review' && /hiring system \(nova\.recruitee\.com\)/.test(r.body.job.review_reason), 'B: from an account that is not trusted yet, a hiring-system link sends the job to review with that reason',
    JSON.stringify(r.body));

  eq(['boards.greenhouse.io', 'job-boards.greenhouse.io', 'job-boards.eu.greenhouse.io', 'jobs.lever.co', 'jobs.eu.lever.co', 'jobs.ashbyhq.com', 'apply.workable.com', 'jobs.smartrecruiters.com', 'careers.smartrecruiters.com',
    'nova.recruitee.com', 'nova.teamtailor.com', 'nova.bamboohr.com', 'nova.breezy.hr', 'nova.jobs.personio.com', 'nova.jobs.personio.de', 'wellfound.com', 'WWW.Wellfound.com', 'nova.wd5.myworkdayjobs.com', 'careers-nova.icims.com', 'nova.pinpointhq.com', 'jobs.jobvite.com', 'ats.rippling.com'].filter((h) => !hiringSystem(h)), [],
    'B: every listed hiring system is known');
  eq(['greenhouse.io', 'evil-greenhouse.io', 'boards.greenhouse.io.evil.com', 'recruitee.com', 'www.recruitee.com', 'lever.co', 'jobs.lever.co.uk', 'jobs.ashbyhq.com.co', 'personio.de', 'nova.personio.de', 'notion.site',
    'nova.notion.site', 'myworkdayjobs.com', 'icims.com', 'evilmyworkdayjobs.com', 'jobvite.com', 'rippling.com', 'join.com', 'xwellfound.com', 'nova.dev'].filter(hiringSystem), [], 'B: and nothing that only looks like one, nor hosts where anyone can publish a page');

  eq(['stripe.com', 'jobs.stripe.com', 'www.coinbase.com', 'metacareers.com', 'amazon.jobs', 'acme.dev', 'apply.acme.dev', 'beta.io', 'user.com', 'motion.dev', 'strike.me', 'opensea.io', 'nova.dev'].map(lookalike).filter(Boolean), [],
    'B: look-alike guard: an employer on its own domain, and ordinary names, are let be');
  for (const [host, brand, how] of [['stripe.work', 'Stripe', 'the exact name on a domain that is not its own'], ['kraken.co.uk', 'Kraken', 'the exact name under another ending'],
    ['careers.binance.com.evil.io', 'Binance', 'the name as a label of somebody else’s domain'], ['coinbase.github.io', 'Coinbase', 'the name on a shared host'], ['c0inbase.com', 'Coinbase', 'a zero for an o'],
    ['str1pe.com', 'Stripe', 'a one for a letter'], ['rnicrosoft.com', 'Microsoft', 'rn for m'], ['vvellfound-uniswap.org', '', ''], ['coin-base.com', 'Coinbase', 'a hyphen inside the name'],
    ['coinbasse.com', 'Coinbase', 'one letter added'], ['binanc.com', 'Binance', 'one letter dropped'], ['anthropoc.com', 'Anthropic', 'one letter changed'], ['stripe-careers.com', 'Stripe', 'the name plus "careers"'],
    ['binance-jobs.net', 'Binance', 'the name plus "jobs"'], ['hr-okx.io', 'Okx', '"hr" plus the name'], ['coinbasehiring.co', 'Coinbase', 'the name plus "hiring"'], ['openai-talent.com', 'Openai', 'the name plus "talent"'],
    ['kraken-recruit.com', 'Kraken', 'the name plus "recruit"'], ['solanarecruiting.io', 'Solana', 'the name plus "recruiting"'], ['c0inbase-careers.com', 'Coinbase', 'both tricks at once']]) {
    if (brand) ok(lookalike(host).includes(brand), 'B: look-alike guard: ' + how + ' (' + host + ')', lookalike(host));
    else eq(lookalike(host), '', 'B: look-alike guard: a name that only contains a brand among other letters is let be (' + host + ')');
  }
  ok(/punycode/.test(lookalike('xn--cinbase-90a.com')) && /punycode/.test(lookalike('jobs.xn--80ak6aa92e.com')), 'B: look-alike guard: any punycode label is flagged');
  eq(['Coinbase', 'COINBASE Inc.', 'C0inbase', 'Binance Careers', 'Kraken Exchange', 'Acme Robotics', 'Stripe Atlas Fans', 'Metallica'].map(brandIn), ['coinbase', 'coinbase', 'coinbase', 'binance', 'kraken', '', '', ''],
    'B: a company name that claims to be a well-known employer is recognised');

  const mimic = await account(env, 'hr@coinbase-careers.com'), puny = await account(env, 'hr@xn--cinbase-90a.com'), real = await account(env, 'hr@kraken.com');
  Object.assign(world.pages, { 'https://coinbase-careers.com/jobs/rust': H1, 'https://xn--cinbase-90a.com/jobs/rust': H1, 'https://kraken.com/careers/rust': H1 });
  r = await post({ company: 'Blockworks Talent', company_url: 'https://coinbase-careers.com', apply_url: 'https://coinbase-careers.com/jobs/rust' }, mimic);
  ok(r.status === 200 && r.body.job.status === 'review' && /Coinbase with a hiring word/.test(r.body.job.review_reason), 'B: an established account on a look-alike domain: its job waits for a person, with the reason recorded', JSON.stringify(r.body));
  eq((await exportedJobs(env)).length, 0, 'B: and is not on the site');
  r = await post({ company: 'Cinbase Talent', company_url: 'https://xn--cinbase-90a.com', apply_url: 'https://xn--cinbase-90a.com/jobs/rust' }, puny);
  ok(r.status === 200 && r.body.job.status === 'review' && /punycode/.test(r.body.job.review_reason), 'B: the same for an account on a punycode domain', JSON.stringify(r.body));
  r = await post({ company: 'Coinbase' });
  ok(r.status === 200 && r.body.job.status === 'review' && /named “Coinbase”/.test(r.body.job.review_reason), 'B: posting under the name of a well-known employer from another domain waits for a person too', JSON.stringify(r.body));
  r = await post({ company: 'Kraken', company_url: 'https://kraken.com', apply_url: 'https://kraken.com/careers/rust' }, real);
  eq([r.status, (r.body.job || {}).status], [200, 'live'], 'B: the employer itself, on its own domain, is not a look-alike');

  eq([await domainAge({}, 'nova.dev'), await domainAge({ DOMAINS: { age: async (d) => (d === 'nova.dev' ? 12.5 : 900) } }, 'nova.dev'), await domainAge({ DOMAINS: { age: async () => { throw new Error('down'); } } }, 'nova.dev'),
    await domainAge({ DOMAINS: { age: async () => 'soon' } }, 'nova.dev')], [null, 12.5, null, null], 'B: domainAge: null when no lookup service is bound or it fails, its answer otherwise');
  const young = newEnv({ DOMAINS: { age: async () => 5 } }), settled = newEnv({ DOMAINS: { age: async () => 900 } });
  r = await post({}, await account(young, 'hr@nova.dev'), young);
  ok(r.status === 200 && r.body.job.status === 'review' && /nova\.dev was registered 5 days ago/.test(r.body.job.review_reason), 'B: with a lookup service bound, a job from a domain registered days ago waits for a person', JSON.stringify(r.body));
  r = await post({}, await account(settled, 'hr@nova.dev'), settled); eq(r.body.job.status, 'live', 'B: and one from an old domain does not');
}

/* ---- 20. C: the screen of the text and the links, and the same job twice ---- */
{
  const FILL = ' This is a remote position open to everyone and we are waiting for you.';
  const base = { title: 'Operations Associate', company: 'Acme Robotics', applyUrl: 'https://acme.dev/careers/1', accountDomain: 'acme.dev' };
  const screen = (over) => screenPosting({ ...base, ...over }), says = (text, over = {}) => screen({ description: text + FILL, ...over });
  eq(Object.keys(says('We build robots for warehouses and you will help the operations team with planning.')).sort(), ['reasons', 'score', 'verdict'], 'C: screenPosting answers with a verdict, a score and reasons');

  // ordinary postings, with the words that a careless filter trips over
  const CLEAN = {
    'a wallet company that writes about seed phrases, private keys and Telegram as its product': { company: 'Tonkeeper Labs', title: 'Senior Mobile Engineer (Wallet)', salary: '$150K - $190K',
      description: 'Tonkeeper Labs is hiring a senior mobile engineer. We build a self-custody wallet that lives inside Telegram as a mini app, used by millions. You will work on seed phrase backup and recovery flows, private key storage in the secure enclave and WalletConnect sessions, where users connect their wallet to dapps. We will never ask you for money, your seed phrase or a private key at any stage of hiring.' },
    'a security role that mentions malware, .exe payloads and stolen card numbers': { title: 'Malware Analyst', salary: '$120K - $160K',
      description: 'Join the threat research team at Acme Robotics. You will reverse engineer malware samples (droppers, loaders, .exe and .dll payloads) in an isolated lab, write YARA rules and publish reports. Experience with phishing kits that steal seed phrases and card numbers is a plus. You never run samples on your own machine: we provide the lab.' },
    'a support role with Zendesk and Discord community management': { title: 'Customer Support Specialist', salary: '$45K - $60K',
      description: 'You will answer customers in Zendesk and look after our Discord community: moderation, announcements with @everyone used sparingly, and weekly office hours. We work in shifts across time zones. Experience with Telegram and Discord community management is welcome. Start date is flexible; interviews are two video calls with the team.' },
    'a posting that says "we will never ask you for money"': { title: 'Operations Associate', salary: '$70K - $85K',
      description: 'Acme Robotics is looking for an operations associate. A note on safety: we will never ask you for money, there is no application fee and no training fee, and we will never ask you to buy equipment or gift cards. We cover visa fees and relocation, and equipment is provided by us. We will never pay you in gift cards or ask you to forward packages. Never share your private key with anyone, including us.' },
    'a payments engineer: processing payments and fees, check deposit, Zelle, Cash App, gift cards': { title: 'Staff Backend Engineer, Payments', salary: '$210K - $260K',
      description: 'You will own the service processing payments and deposits for two million merchants: card number tokenization, Visa and Mastercard fee schedules, low processing fees, check deposit by photo, and integrations with Zelle and Cash App. Our users can buy gift cards with Bitcoin, and customers upload a passport photo for KYC. Stack: Rust, Postgres, Kafka. We run client workshops every quarter and ship a package registry for partners.' },
    'a junior role with ordinary pay next to large company figures': { title: 'Junior Data Engineer', salary: '$85K - $105K',
      description: 'Work at Acme Robotics on the data platform: pipelines in Python and dbt, review pull requests for our mobile apps team, and rate limiting for the public API. We raised $40M last year and manage $2,000,000,000 in robot leases. Pay is $85,000 to $105,000 per year plus equity. You can start in January; we like products people love.' },
    'a developer advocate: Node.js/TypeScript, sample repositories, Telegram and Discord channels': { title: 'Developer Advocate',
      description: 'You will write tutorials for Node.js/TypeScript and React/Next.js developers, run our Discord and Telegram channels, speak at conferences and maintain sample apps on github.com/acme. Clone-and-run examples matter to us, so you will keep the quickstart working. Reach us any time at jobs@acme.dev with questions about the role.' },
    'a file host hiring for itself, with links to its own site': { company: 'Dropbox', accountDomain: 'dropbox.com', applyUrl: 'https://jobs.dropbox.com/listing/123', title: 'Product Designer',
      description: 'Design the sharing flows of Dropbox, used by 700 million people. See how we work at https://www.dropbox.com/about and bring a portfolio with shipped consumer work. Hybrid, Dublin or remote in the EU.' },
  };
  for (const [what, posting] of Object.entries(CLEAN)) { const v = screen(posting); eq([v.verdict, v.score], ['ok', 0], 'C: clean posting passes: ' + what); }

  // scam postings: each hard reject, then signals that add up
  const SCAMS = [
    ['a Telegram link to apply', /chat app \(t\.me\)/, { applyUrl: 'https://t.me/acme_hr', title: 'Remote Assistant', description: 'Help our managers with daily tasks online. Flexible hours, friendly team, weekly payouts and growth.' + FILL }],
    ['a form in the text', /form builder \(forms\.gle\)/, { title: 'Remote Assistant', description: 'Fill in the form at https://forms.gle/AbCdEf123 and our manager will call you back within one hour with all details.' + FILL }],
    ['a shortened link written without https', /link shortener \(bit\.ly\)/, { title: 'Remote Assistant', description: 'All details and the application are here: bit.ly/3xYzAbC and our manager will call you back within the hour.' + FILL }],
    ['a file host', /file host \(mega\.nz\)/, { title: 'Game Tester', description: 'Test our new play-to-earn game before launch. The build is on https://mega.nz/file/abc123 and you report the bugs you find to us.' + FILL }],
    ['a download on its own site', /download \(\.exe\)/, { title: 'Game Tester', description: 'Test our new play-to-earn game before launch. Get the build at https://acme.dev/files/GameSetup.exe?ref=job and report the bugs you find.' + FILL }],
    ['a registration fee', /asks candidates for money/, { title: 'Data Entry Clerk', description: 'Type documents from home, 2 hours a day. A registration fee of $49 is required to open your work account and it is returned later.' + FILL }],
    ['a refundable equipment deposit', /asks candidates for money/, { title: 'Remote Packer', description: 'We send the materials to your address. You pay a refundable equipment deposit before the first shipment and get it back after a month.' + FILL }],
    ['topping up to unlock orders', /asks candidates for money/, { title: 'Order Processing Agent', description: 'Complete 30 orders a day in our app. When a premium order appears, top up your balance to unlock it and withdraw the commission.' + FILL }],
    ['paying to activate an account', /asks candidates for money/, { title: 'Order Processing Agent', description: 'After training, pay 50 USDT to activate your work account and start receiving orders the same day from our system.' + FILL }],
    ['a cheque to deposit', /move money or parcels/, { title: 'Personal Assistant', description: 'I travel a lot and need help with errands. We will send you a check for supplies; deposit it into your account and keep 400 dollars.' + FILL }],
    ['gift cards', /move money or parcels/, { title: 'Personal Assistant', description: 'Your first errand is simple: purchase gift cards for our clients and send the codes to the manager the same day by mail.' + FILL }],
    ['pay by Zelle or Cash App', /move money or parcels/, { title: 'Virtual Assistant', description: 'Simple admin work for a busy executive. You will be paid weekly via Zelle or Cash App, whichever is easier for you to use.' + FILL }],
    ['reshipping parcels', /move money or parcels/, { title: 'Logistics Coordinator (home based)', description: 'Receive packages at your home address, check the contents, and reship them to our customers abroad with the labels we provide.' + FILL }],
    ['forwarding funds', /move money or parcels/, { title: 'Payment Processing Agent', description: 'Receive payments from our clients into your personal bank account and forward the funds to our suppliers, keeping eight percent.' + FILL }],
    ['a seed phrase', /no employer needs/, { title: 'Wallet Tester', description: 'Test our new wallet app on your phone. To verify compatibility, send us your wallet seed phrase and we will check the balance.' + FILL }],
    ['an SSN and bank details', /no employer needs/, { title: 'Data Entry Clerk', description: 'To be hired today, email your full name, address, SSN and bank details to our HR manager and you get the contract in an hour.' + FILL }],
    ['connecting a wallet', /no employer needs/, { title: 'Airdrop Moderator', description: 'Moderate our community chat two hours a day. To receive your salary, connect your wallet on our payroll page and sign the request.' + FILL }],
    ['a chat handle and a daily sum', /chat app.*\n.*per day or week/, { title: 'Online Promoter', description: 'Promote our brand on social media and earn $300 per day from your phone. Message our manager on Telegram @acme_hr_anna for details.' + FILL }],
    ['tasks, no interview, start today', /“task” scheme.*\n.*without an interview/, { title: 'Part-time Reviewer', description: 'Simply like and subscribe to YouTube videos and get paid for each task. No interview, you can start today and work from home.' + FILL }],
    ['a free mailbox and a guaranteed income', /free mailbox.*\n.*guaranteed income/, { title: 'Sales Agent', description: 'Guaranteed income for everyone who joins this month. Send your CV to acme.recruiting2024@gmail.com and our team answers the same day.' + FILL }],
    ['software to install and absurd pay', /install or run software.*\n.*far above/, { title: 'Junior Blockchain Tester', description: 'During the interview you will download our meeting app and share your screen. The rate is $180 per hour for a few hours of testing.' + FILL }],
    ['another company, kindly, urgent, capitals, emoji', /another company \(Binance\).*\n.*kindly.*\n.*urgent hiring.*\n.*capitals.*\n.*emoji/, { title: 'URGENT HIRING ASSISTANT 🔥', description: 'Binance is hiring remote assistants. Kindly apply now, places are limited and the team is growing quickly this quarter in all regions.' + FILL }],
  ];
  for (const [what, why, posting] of SCAMS) { const v = screen(posting); ok(v.verdict === 'reject' && why.test(v.reasons.join('\n')), 'C: scam posting is rejected with the reason: ' + what, JSON.stringify(v)); }

  // every hard reject by itself
  const text = (s) => 'We are a small team and you will help us every day with whatever comes up. ' + s;
  for (const url of ['https://t.me/acme_hr', 'https://telegram.me/acme_hr', 'https://wa.me/14155550100', 'https://chat.whatsapp.com/AbCd', 'https://discord.gg/abc', 'https://discord.com/invite/abc', 'https://forms.gle/abc',
    'https://docs.google.com/forms/d/e/1/viewform', 'https://acme.typeform.com/to/abc', 'https://tally.so/r/abc', 'https://form.jotform.com/123', 'https://bit.ly/abc', 'https://tinyurl.com/abc', 'https://cutt.ly/abc', 'https://rb.gy/abc',
    'https://t.co/abc', 'https://is.gd/abc', 'https://drive.google.com/file/d/1/view', 'https://www.dropbox.com/s/abc/job.pdf', 'https://mega.nz/file/abc', 'https://wetransfer.com/downloads/abc', 'https://www.mediafire.com/file/abc']) {
    eq([says('Apply and we answer the same day.', { applyUrl: url }).verdict, says('Apply here: ' + url + ' and we answer the same day.').verdict], ['reject', 'reject'], 'C: hard reject: a link to ' + new URL(url).hostname + ', to apply or in the text');
  }
  eq(['https://discord.com/company', 'https://docs.google.com/document/d/1/edit', 'https://acme.dev/blog/why-we-left-t.me/', 'https://pinterest.co/abc', 'https://acme.dev/bit.ly/x'].map((u) => says('Read more at ' + u + ' today.').verdict),
    Array(5).fill('ok'), 'C: links that only resemble those are fine');
  for (const ext of 'exe msi scr bat cmd ps1 vbs js jar dmg pkg apk iso zip rar 7z lnk'.split(' ')) {
    const file = 'https://acme.dev/files/setup.' + ext;
    eq([says('Start here.', { applyUrl: file }).verdict, says('Get it at ' + file + '?v=2 and begin.').verdict, says('Get it at ' + file.toUpperCase().replace('HTTPS', 'https') + ' and begin.').verdict, says('See ' + file + '/notes for the story.').verdict],
      ['reject', 'reject', 'reject', 'ok'], 'C: hard reject: a link to a .' + ext + ' file, at the end of the path or before a query string, not in the middle');
  }
  for (const word of ['registration', 'application', 'training', 'onboarding', 'processing', 'equipment', 'starter kit', 'background check', 'visa']) {
    eq(['fee', 'deposit', 'payment'].map((kind) => says(text('A ' + word + ' ' + kind + ' of $30 is required before the first shift.')).verdict), ['reject', 'reject', 'reject'], 'C: hard reject: a ' + word + ' fee, deposit or payment asked of the candidate');
    eq([says(text('There is no ' + word + ' fee.')).verdict, says(text('We will never ask you to pay a ' + word + ' fee or a deposit.')).verdict, says(text('We cover the ' + word + ' fee for every new hire.')).verdict], ['ok', 'ok', 'ok'],
      'C: saying there is no ' + word + ' fee, or that the company pays it, is fine');
  }
  for (const s of ['Deposit 100 USDT to activate your account.', 'Top up your balance to unlock the next set of orders.', 'You must pay first to withdraw your earnings.', 'Pay a small fee to start working today.',
    'Candidates pay for the kit to start.', 'Recharge your wallet to release the commission.']) eq(says(text(s)).verdict, 'reject', 'C: hard reject: paying to unlock, activate, withdraw or start: ' + s);
  eq(['We pay well and you are free to start whenever you like.', 'We offer direct deposit to start with your first paycheck.', 'You will never have to pay anything to start.'].map((s) => says(text(s)).verdict), ['ok', 'ok', 'ok'],
    'C: ordinary sentences about pay and starting are fine');
  eq([says(text('A registration fee applies.')), says(text('Training fees may apply later.')), says(text('We pay the background check fee.')), says(text('We reimburse flights, hotels and the visa fee.')),
    says(text('Merchants love our low processing fees and fast Visa payments.'))].map((v) => [v.verdict, v.score]), [['review', 40], ['review', 40], ['ok', 0], ['ok', 0], ['ok', 0]],
    'C: a candidate fee that is named but not asked for is for a person to look at; one the company pays, and the fees a payments company charges, are fine');
  for (const s of ['We will send you a cheque to cover supplies and you send back the difference.', 'Deposit the check into your personal account and keep ten percent.', 'A check will be mailed to you for the equipment.',
    'Your salary is sent by money order every Friday.', 'You will be paid in gift cards for the first month.', 'Payment via Western Union every week.', 'Weekly pay through Zelle.', 'Payouts are made to your Cash App every evening.',
    'Buy gift cards at the store and send us the codes.', 'Receive parcels at your home and reship them to the addresses we give you.', 'You repackage the goods and attach a new label.', 'Forward the packages to our warehouse abroad.',
    'Accept transfers into your bank account and forward the funds to our partner.', 'Process client payments through your personal account and forward the payments the same day.'])
    eq(says(text(s)).verdict, 'reject', 'C: hard reject: moving money or parcels: ' + s);
  for (const s of ['Send us your seed phrase so we can whitelist your wallet.', 'Enter your 12-word recovery phrase on our onboarding page.', 'Share your MetaMask private key with the team lead.', 'Provide your SSN to start.',
    'Submit your social security number today.', 'Upload a passport scan before the interview.', 'Email a copy of your passport to the manager.', 'Provide your bank login so payroll can be connected.',
    'Send your bank details and card number with the CVV.', 'Connect your wallet to our payroll page.']) eq(says(text(s)).verdict, 'reject', 'C: hard reject: asking for a secret: ' + s);
  eq(['We will never ask for your seed phrase, private key, SSN or bank details.', 'Never share your private key with anyone, including us.', 'You will design how users enter their card number and CVV at checkout.',
    'Our KYC flow lets customers upload a passport photo in seconds.', 'Share your experience building seed phrase backups with the team.', 'You will provide security reviews of private key management systems.',
    'Our dapp lets users connect their wallet in one tap.'].map((s) => says(text(s)).verdict), Array(7).fill('ok'), 'C: writing about secrets, refusing to ask for them, or building products around them is fine');

  // every signal by itself, and the thresholds
  const points = (s, over) => says(text(s), over).score;
  eq([points('Questions? Telegram: @acme_hr_anna.'), points('WhatsApp +1 415 555 0100 for details.'), points('Message us on Signal for details.'), points('WeChat acme_hr 13800138000.'), points('Discord: @acmerecruiter.')], [40, 40, 40, 40, 40],
    'C: signal +40: a chat-app handle or phone number');
  eq([points('Send your CV to acme.jobs@gmail.com.'), points('Write to hiring@outlook.com.'), points('Write to hiring@acme.dev.')], [40, 40, 0], 'C: signal +40: a free-mail contact address; a company address is none');
  eq([points('Rate hotels online and get paid daily.'), points('Your task: review products on Amazon from home.'), points('Subscribe to channels and earn a commission.'), points('You will review apps for compliance with our policy.')], [40, 40, 40, 0],
    'C: signal +40: task-scam wording; reviewing as a job is none');
  eq([points('Earn $200 per day.'), points('You can make $1,500 a week.'), points('Get paid 500 USDT daily.'), points('We pay a $75 per day meal allowance when you travel.')], [30, 30, 30, 0], 'C: signal +30: a sum of money per day or week');
  eq([points('No interview needed.'), points('Start today.'), points('You can start immediately.'), points('Guaranteed income from the first month.'), points('A guaranteed job after the course.')], [30, 30, 30, 30, 30],
    'C: signal +30: no interview, an immediate start, a guaranteed income or job');
  eq([points('Download our launcher to begin.'), points('Install the client and log in.'), points('Please install our meeting software before the call.'), points('Clone the repository and run it on your machine.'),
    points('Run the package we send you.'), points('You will run client workshops and manage our package registry.')], [40, 40, 40, 40, 40, 0], 'C: signal +40: a request to download, install or run something');
  eq([points('The rate is $150 per hour.', { title: 'Virtual Assistant' }), points('The rate is $149 per hour.', { title: 'Virtual Assistant' }), points('Salary of $400,000 a year.', { title: 'Junior Moderator' }),
    points('Salary of $399,000 a year.', { title: 'Junior Moderator' }), points('Fine.', { title: 'Data Entry Intern', salary: '$450K - $500K' }), points('Fine.', { title: 'QA Tester', salary: '$90K - $110K' }),
    points('The rate is $300 per hour.', { title: 'Staff Engineer' })], [30, 0, 30, 0, 30, 0, 0], 'C: signal +30: pay far above a junior role, from $150 an hour or $400,000 a year');
  eq([says('Join the team at Binance and grow with us.', { company: 'Acme Robotics' }).score, says('Coinbase is hiring assistants.', { company: 'Acme Robotics' }).score, says('Join the team at Acme and grow with us.', { company: 'Acme Robotics' }).score,
    says('You are great at Python and you like Rust.', { company: 'Acme Robotics' }).score], [30, 30, 0, 0], 'C: signal +30: the text clearly names another company than the one on the posting');
  eq([points('Kindly send your CV.'), points('Urgent hiring for our new office.'), points('Fine.', { title: 'SENIOR RUST ENGINEER' }), points('Fine.', { title: 'Senior Rust Engineer 🚀' }), points('Fine.', { title: 'CTO' })], [10, 10, 10, 10, 0],
    'C: signals +10: "kindly", "urgent hiring", a title in capitals, an emoji in the title');
  const at = (s, over) => { const v = says(text(s), over); return [v.score, v.verdict]; };
  eq([at('Kindly send your CV.', { title: 'SENIOR RUST ENGINEER' }), at('Start today.'), at('Start today. Kindly send your CV.', { title: 'SENIOR RUST ENGINEER' }), at('Questions? Telegram: @acme_hr_anna. Kindly send your CV.'),
    at('Questions? Telegram: @acme_hr_anna. Kindly send your CV.', { title: 'SENIOR RUST ENGINEER' }), at('Start today. Earn $200 per day.')],
    [[20, 'ok'], [30, 'review'], [50, 'review'], [50, 'review'], [60, 'reject'], [60, 'reject']], 'C: thresholds: under 25 is fine, 25 to 59 is for a person, 60 and more is a reject');

  // the screen at work: on a new job and on every edit
  const env = newEnv(), token = await account(env, 'hr@nova.dev'), job = employer('nova.dev', 'Nova Labs'), NOVA = job('Senior Rust Engineer');
  const post = (data) => call(env, 'POST', '/api/jobs', { token, data }), edit = (id, data) => call(env, 'PATCH', '/api/jobs/' + id, { token, data });
  const opened = () => world.fetched.filter((u) => u === NOVA.apply_url).length, was = opened();
  let r = await post({ ...NOVA, description: NOVA.description + ' A registration fee of $49 is required to open your work account.' });
  eq([r.status, r.body.error, (r.body.reasons || []).length, /registration fee/.test(r.body.message), await one(env, 'SELECT COUNT(*) FROM jobs'), opened() - was], [422, 'rejected', 1, true, 0, 0],
    'C: a posting the screen rejects is refused with the reason; nothing is stored and its link is not opened');
  r = await post(NOVA); const first = r.body.job.id; eq(r.body.job.status, 'live', 'C: a clean posting of a trusted account goes live');
  r = await post(job('Community Manager', { description: NOVA.description + ' Questions? Message our manager on Telegram @nova_hr_anna.' })); const second = r.body.job.id;
  ok(r.status === 200 && r.body.job.status === 'review' && /chat app/.test(r.body.job.review_reason), 'C: a "review" verdict holds the job even of a trusted account, with the reasons', JSON.stringify(r.body));
  eq((await exportedJobs(env)).map((j) => j.id), [first], 'C: and a held job is not exported');
  r = await edit(first, { description: NOVA.description + ' Send us your seed phrase to get whitelisted.' });
  eq([r.status, r.body.error, await one(env, 'SELECT description FROM jobs WHERE id = ?', first), await statusOf(env, first)], [422, 'rejected', NOVA.description, 'live'], 'C: an edit the screen rejects is refused and changes nothing');
  r = await edit(first, { description: NOVA.description + ' You can start immediately.' });
  eq([r.status, r.body.job.status, (await exportedJobs(env)).length], [200, 'review', 0], 'C: an edit with a "review" verdict takes the live job of a trusted account off the site');
  r = await post(job('Junior QA Tester')); const third = r.body.job.id; eq(r.body.job.status, 'live', 'C: (a third job, live)');
  r = await edit(third, { salary: '$400 per hour' });
  ok(r.status === 200 && r.body.job.status === 'review' && /far above/.test(r.body.job.review_reason), 'C: the screen runs on every edit, also one that leaves the text alone', JSON.stringify(r.body));
  r = await call(env, 'GET', '/api/public/transparency.json');
  eq([r.body.current.jobs_checked, r.body.current.jobs_rejected_by_screen, r.body.current.jobs_held_for_review], [4, 1, 3], 'C: what the screen did is counted: four jobs checked, one rejected, three held');

  // the same job twice
  const twin = newEnv(), boss = await account(twin, 'hr@nova.dev'), limits = () => twin.DB.exec('DELETE FROM rate');
  const send = (over) => call(twin, 'POST', '/api/jobs', { token: boss, data: { ...NOVA, ...over } }), change = (id, data) => call(twin, 'PATCH', '/api/jobs/' + id, { token: boss, data });
  r = await send({}); const one1 = r.body.job.id; eq(r.status, 200, 'C: duplicate guard: the first posting is taken');
  r = await send({}); eq([r.status, r.body.error], [409, 'duplicate'], 'C: duplicate guard: the same title and company again is refused');
  r = await send({ title: 'senior  RUST engineer!!', apply_url: ATS.apply_url }); eq([r.status, r.body.error], [409, 'duplicate'], 'C: duplicate guard: however the title is written, and whatever the link');
  r = await send(ATS); const two = r.body.job.id; eq(r.status, 200, 'C: duplicate guard: another title is another job');
  r = await change(two, { title: 'Senior Rust Engineer' }); eq([r.status, r.body.error], [409, 'duplicate'], 'C: duplicate guard: an edit cannot turn a job into the twin of another');
  r = await change(one1, { location: 'Lisbon' }); eq(r.status, 200, 'C: duplicate guard: a job is not its own duplicate');
  await call(twin, 'POST', '/api/jobs/' + one1 + '/close', { token: boss });
  r = await send({}); eq([r.status, r.body.error], [409, 'duplicate'], 'C: duplicate guard: a closed job is published again, not posted again');
  await call(twin, 'DELETE', '/api/jobs/' + one1, { token: boss });
  r = await send({}); eq([r.status, r.body.error], [409, 'duplicate'], 'C: duplicate guard: a job removed less than 30 days ago still blocks its twin');
  await twin.DB.exec('UPDATE jobs SET ended_at = ended_at - 31 * 86400'); await limits();
  r = await send({}); eq(r.status, 200, 'C: duplicate guard: after 30 days it can be posted again');
  await twin.DB.prepare('UPDATE jobs SET expires_at = 1 WHERE id = ?').bind(r.body.job.id).run(); await limits();
  r = await send({}); eq(r.status, 200, 'C: duplicate guard: a job whose days ran out does not block a new posting');
  await limits();
  // Two requests for the same job, both held at the moment their link is opened: by then each has looked for a twin and found none.
  // Only the test inside the insert itself can stop the second one.
  let letGo; world.gates[ATS.apply_url] = new Promise((done) => { letGo = done; });
  const atGate = () => world.fetched.filter((u) => u === ATS.apply_url).length, start = atGate(), racing = [send({ ...ATS, title: 'Staff Go Engineer' }), send({ ...ATS, title: 'Staff Go Engineer' })];
  for (let i = 0; i < 400 && atGate() - start < 2; i++) await new Promise((tick) => setTimeout(tick, 5));
  eq(atGate() - start, 2, 'C: duplicate guard: (both requests have passed the first test for a twin and wait for the link)');
  delete world.gates[ATS.apply_url]; letGo();
  const both = await Promise.all(racing);
  eq([both.map((x) => x.status).sort(), both.map((x) => x.body.error || '').sort(), await one(twin, "SELECT COUNT(*) FROM jobs WHERE title = 'Staff Go Engineer'")], [[200, 409], ['', 'duplicate'], 1],
    'C: duplicate guard: the same job sent twice at the same moment is stored once');
}

/* ---- 21. D: the review queue, trust, the limits of a new account, held placements, the daily recheck, the owner's endpoints ---- */
{
  const env = newEnv(), admin = (method, p, data, e = env) => call(e, method, '/api/admin/' + p, { token: ADMIN, data });
  const ORBIT = employer('orbit.dev', 'Orbit Labs'), token = await fresh(env, 'hr@orbit.dev'), uid = await one(env, 'SELECT id FROM users');
  const post = (job, who = token) => call(env, 'POST', '/api/jobs', { token: who, data: job }), act = (id, action, who = token) => call(env, 'POST', '/api/jobs/' + id + '/' + action, { token: who });
  const me = async (who = token) => (await call(env, 'GET', '/api/me', { token: who })).body.user, approved = () => one(env, 'SELECT approved_jobs FROM users WHERE id = ?', uid);
  let r = await post(ORBIT('Senior Rust Engineer')); const rust = r.body.job.id;
  ok(r.status === 200 && r.body.job.status === 'review' && /not trusted yet/.test(r.body.job.review_reason), 'D: the first job of a new account is held for review, and says why', JSON.stringify(r.body));
  eq([(await exportedJobs(env)).length, (await call(env, 'GET', '/api/jobs', { token })).body.jobs.map((j) => j.status)], [0, ['review']], 'D: a held job is not exported; its owner sees it as waiting');
  r = await post(ORBIT('Senior Go Engineer')); eq([r.status, r.body.error], [429, 'limit'], 'D: an account that is not trusted yet posts one job a day');

  for (const [who, what] of [[undefined, 'no token'], ['wrong-secret', 'a wrong token'], [token, "an employer's session"], ['admin-secre', 'the secret one letter short'], ['admin-secret2', 'the secret one letter long']]) {
    r = await call(env, 'GET', '/api/admin/review', { token: who }); eq(r.status, 403, 'D: the owner endpoints refuse ' + what);
  }
  const unset = newEnv({ ADMIN_TOKEN: '' }), never = newEnv({ ADMIN_TOKEN: undefined });
  for (const [method, p] of [['GET', 'review'], ['GET', 'reports'], ['GET', 'overview'], ['POST', 'jobs/' + rust + '/approve'], ['POST', 'jobs/' + rust + '/reject'], ['POST', 'accounts/' + uid + '/ban'], ['POST', 'reports/r_1/decide']]) {
    eq([(await call(unset, method, '/api/admin/' + p)).status, (await call(unset, method, '/api/admin/' + p, { token: 'undefined' })).status, (await call(never, method, '/api/admin/' + p, { token: 'undefined' })).status,
      (await call(env, method, '/api/admin/' + p)).status], [403, 403, 403, 403], 'D: with no ADMIN_TOKEN set, and without the token, ' + method + ' /api/admin/' + p.replace(/j_\w+|u_\w+/, '<id>') + ' is refused');
  }
  r = await admin('GET', 'review');
  eq([r.status, r.body.jobs.length, r.body.jobs[0].id, r.body.jobs[0].account.email_domain, r.body.jobs[0].account.age_days, /not trusted yet/.test(r.body.jobs[0].reason)], [200, 1, rust, 'orbit.dev', 0, true],
    'D: the review queue lists the held job with the reason, the domain of the account and its age');
  ok(!JSON.stringify(r.body).includes('hr@orbit.dev'), 'D: the queue carries the domain of the email, not the address');
  r = await admin('POST', 'jobs/' + rust + '/approve');
  eq([r.status, (await exportedJobs(env)).map((j) => j.title), await approved(), (await me()).trusted], [200, ['Senior Rust Engineer'], 1, false], 'D: approval puts the job on the site and counts towards trust');
  r = await admin('POST', 'jobs/' + rust + '/approve'); eq([r.status, await approved()], [404, 1], 'D: a job that is not waiting cannot be approved again, and is counted once');
  r = await admin('POST', 'jobs/j_000000000000/approve'); eq(r.status, 404, 'D: approving a job that does not exist is refused');

  await nextDay(env);
  r = await post(ORBIT('Senior Go Engineer')); const go = r.body.job.id; eq(r.body.job.status, 'review', 'D: the second job waits too');
  await admin('POST', 'jobs/' + go + '/approve');
  eq([await approved(), (await me()).trusted], [2, false], 'D: two approved jobs do not make an account trusted while it is younger than 14 days');
  await nextDay(env);
  r = await post(ORBIT('Data Engineer')); const data = r.body.job.id; eq(r.body.job.status, 'review', 'D: so its third job still waits');
  await nextDay(env);
  r = await post(ORBIT('QA Engineer')); eq([r.status, r.body.error, /3 jobs/.test(r.body.message)], [429, 'limit', true], 'D: an account that is not trusted yet has three jobs on the site or waiting at most');
  await act(rust, 'close');
  r = await post(ORBIT('QA Engineer')); const qa = r.body.job.id; eq([r.status, r.body.job.status], [200, 'review'], 'D: closing one makes room for another');
  r = await act(rust, 'renew'); eq([r.status, r.body.error], [429, 'limit'], 'D: and publishing the closed one again counts against the same cap');
  await admin('POST', 'jobs/' + data + '/approve'); await admin('POST', 'jobs/' + qa + '/approve');
  await env.DB.exec('UPDATE users SET created_at = created_at - 14 * 86400');
  eq((await me()).trusted, true, 'D: two approved jobs, fourteen days and no upheld report: the account is trusted');
  await nextDay(env);
  r = await post(ORBIT('ML Engineer')); eq([r.status, r.body.job.status, r.body.job.review_reason], [200, 'live', ''], 'D: a job of a trusted account goes live without waiting');
  await post(ORBIT('Site Reliability Engineer')); r = await post(ORBIT('Support Engineer')); eq([r.status, (await exportedJobs(env)).length], [200, 6], 'D: a trusted account is not held to three jobs at a time');
  r = await post(ORBIT('Security Engineer')); eq([r.status, r.body.error], [429, 'limit'], 'D: its limit is the three new jobs a day there always was');

  // paying does not skip review: what is bought is held, and starts with the approval
  const COMET = employer('comet.dev', 'Comet Works'), comet = await fresh(env, 'hr@comet.dev'), cometId = await one(env, "SELECT id FROM users WHERE email = 'hr@comet.dev'");
  const buy = async (who, id) => { const made = await call(env, 'POST', '/api/orders', { token: who, data: { product: 'featured', target: { job_id: id } } }); if (made.status === 200) await hook(env, made.body.order.id); return made; };
  const bought = async (id) => (await env.DB.prepare('SELECT held, cancelled, starts_at, ends_at FROM placements WHERE target = ? ORDER BY starts_at').bind('direct:' + id).all()).results, TWO_WEEKS = 14 * 86400;
  r = await post(COMET('Senior Rust Engineer'), comet); const c1 = r.body.job.id;
  r = await buy(comet, c1); eq(r.status, 200, 'D: a placement can be bought for a job that waits for review');
  eq([await bought(c1), await statusOf(env, c1)], [[{ held: 1, cancelled: 0, starts_at: 0, ends_at: TWO_WEEKS }], 'review'], 'D: paying does not skip review: the job still waits, and the placement is held with its 14 days untouched');
  r = await call(env, 'GET', '/api/placements', { token: comet }); eq(r.body.placements.map((x) => [x.kind, x.state, x.days, x.until]), [['featured', 'held', 14, '']], 'D: the buyer sees the placement as held, with its days');
  let x = (await call(env, 'GET', '/api/public/export.json')).body;
  ok(!x.jobs.some((j) => j.id === c1) && !JSON.stringify(x).includes(c1), 'D: neither the held job nor what was bought for it is exported');
  await buy(comet, c1);
  eq((await bought(c1)).map((p) => [p.held, p.starts_at, p.ends_at]), [[1, 0, TWO_WEEKS], [1, TWO_WEEKS, 2 * TWO_WEEKS]], 'D: a second purchase for the held job queues behind the first');
  const t0 = Math.floor(Date.now() / 1000);
  await admin('POST', 'jobs/' + c1 + '/approve');
  let rows = await bought(c1);
  ok(rows.every((p) => p.held === 0) && rows[0].starts_at >= t0 && rows[0].starts_at <= t0 + SLACK && rows[0].ends_at - rows[0].starts_at === TWO_WEEKS && rows[1].starts_at === rows[0].ends_at && rows[1].ends_at - rows[1].starts_at === TWO_WEEKS,
    'D: approval starts the held placements: their days run from the approval, one after the other', JSON.stringify(rows));
  eq((await exportedJobs(env)).find((j) => j.id === c1).featured_until, new Date(Date.now() + 28 * 86400e3).toISOString().slice(0, 10), 'D: and the site gets the job as featured for all the days that were bought');

  r = await call(env, 'PATCH', '/api/jobs/' + c1, { token: comet, data: { location: 'Lisbon' } });
  eq([r.status, r.body.job.status, r.body.job.location, (await exportedJobs(env)).some((j) => j.id === c1)], [200, 'review', 'Lisbon', false], 'D: an edit by an account that is not trusted yet sends its live job back to review');
  rows = await bought(c1);
  ok(rows.every((p) => p.held === 1) && rows[0].starts_at === 0 && rows[1].ends_at <= 2 * TWO_WEEKS && rows[1].ends_at >= 2 * TWO_WEEKS - SLACK, 'D: and what was bought for it is held again, with the days that were left', JSON.stringify(rows));
  await admin('POST', 'jobs/' + c1 + '/approve');
  eq([await statusOf(env, c1), await one(env, 'SELECT approved_jobs FROM users WHERE id = ?', cometId)], ['live', 1], 'D: approving the same job a second time does not count twice towards trust');

  await nextDay(env);
  r = await post(COMET('Senior Go Engineer'), comet); const c2 = r.body.job.id;
  r = await act(c2, 'close', comet); eq(r.body.job.status, 'closed', 'D: (a held job is closed by its owner)');
  r = await act(c2, 'renew', comet); eq([r.body.job.status, (await exportedJobs(env)).some((j) => j.id === c2)], ['review', false], 'D: closing a held job and publishing it again does not get it past review');
  await buy(comet, c2);
  r = await admin('POST', 'jobs/' + c2 + '/reject', {}); eq([r.status, r.body.error], [400, 'reason'], 'D: a rejection needs a reason');
  r = await admin('POST', 'jobs/' + c2 + '/reject', { reason: 'The page behind the link is not a job at Comet Works.' }); eq(r.status, 200, 'D: the owner rejects a held job');
  const seen = (await call(env, 'GET', '/api/jobs', { token: comet })).body.jobs.find((j) => j.id === c2);
  eq([seen.status, seen.reject_reason, (await bought(c2))[0].cancelled], ['rejected', 'The page behind the link is not a job at Comet Works.', 1], 'D: the employer sees that the job was turned down and why; what was bought for it is switched off');
  eq([(await call(env, 'PATCH', '/api/jobs/' + c2, { token: comet, data: { location: 'Porto' } })).status, (await act(c2, 'renew', comet)).status, (await admin('POST', 'jobs/' + c2 + '/approve')).status], [409, 409, 404],
    'D: a rejected job cannot be edited, published again or approved');
  eq(await one(env, "SELECT COUNT(*) FROM companies WHERE k = 'comet works'"), 1, 'D: the company name stays with the account while it has another job under it');
  await nextDay(env);
  r = await post(COMET('Senior Go Engineer'), comet); eq([r.status, (r.body.job || {}).status], [200, 'review'], 'D: a corrected version of a rejected job may be posted: it is not a duplicate');
  r = await call(env, 'DELETE', '/api/jobs/' + c2, { token: comet }); eq(r.status, 200, 'D: and the rejected one can be deleted');

  const pulsar = await fresh(env, 'hr@pulsar.dev'), pulsarId = await one(env, "SELECT id FROM users WHERE email = 'hr@pulsar.dev'");
  r = await post(employer('pulsar.dev', 'Pulsar Labs')('Senior Rust Engineer'), pulsar);
  await admin('POST', 'jobs/' + r.body.job.id + '/reject', { reason: 'Not a real company.' });
  eq(await one(env, "SELECT COUNT(*) FROM companies WHERE k = 'pulsar labs'"), 0, 'D: a company name taken only by a job that was turned down is free again');
  r = await admin('POST', 'accounts/' + pulsarId + '/ban');
  eq([r.status, await one(env, 'SELECT banned FROM users WHERE id = ?', pulsarId), (await call(env, 'GET', '/api/me', { token: pulsar })).status], [200, 1, 401], 'D: the ban endpoint answers under /api/admin/accounts/<id>/ban as well');

  // the daily recheck of the link to apply
  const cron = newEnv(), VEGA = employer('vega.dev', 'Vega Systems')('Senior Rust Engineer'), LINK = VEGA.apply_url, PAGE = world.pages[LINK], vega = await account(cron, 'hr@vega.dev');
  const opened = () => world.fetched.filter((u) => u === LINK).length, aDayLater = () => cron.DB.exec('UPDATE jobs SET checked_at = checked_at - 90000');
  r = await call(cron, 'POST', '/api/jobs', { token: vega, data: VEGA }); const v1 = r.body.job.id;
  eq([r.body.job.status, await one(cron, 'SELECT apply_host FROM jobs')], ['live', 'vega.dev'], 'D: recheck: (a live job; the host its link ends on is kept)');
  r = await call(cron, 'POST', '/api/orders', { token: vega, data: { product: 'pinned', target: { job_id: v1 } } }); await hook(cron, r.body.order.id);
  const pin = () => cron.DB.prepare('SELECT held, ends_at - starts_at AS left FROM placements').first();
  let n = opened(); await worker.scheduled({}, cron); eq(opened() - n, 0, 'D: recheck: a link checked today is not opened again');
  await aDayLater(); n = opened(); await worker.scheduled({}, cron);
  eq([opened() - n, await statusOf(cron, v1)], [1, 'live'], 'D: recheck: a day later the cron opens the link again; a link that ends where it did changes nothing');
  n = opened(); await worker.scheduled({}, cron); eq(opened() - n, 0, 'D: recheck: once a day, not at every run');
  world.redirects[LINK] = ATS.apply_url;                                   // the page now sends people on to another host
  await aDayLater(); await worker.scheduled({}, cron);
  let row = await cron.DB.prepare('SELECT status, review_reason, apply_host FROM jobs WHERE id = ?').bind(v1).first();
  ok(row.status === 'review' && /now leads to boards\.greenhouse\.io \(it led to vega\.dev/.test(row.review_reason) && (await exportedJobs(cron)).length === 0, 'D: recheck: a link that now ends on another host takes the job back to review',
    JSON.stringify(row));
  let pinned = await pin();
  ok(pinned.held === 1 && pinned.left <= 7 * 86400 && pinned.left >= 7 * 86400 - SLACK, 'D: recheck: and what was bought for it stops running, with the days it had left', JSON.stringify(pinned));
  await admin('POST', 'jobs/' + v1 + '/approve', undefined, cron); pinned = await pin();
  ok(pinned.held === 0 && pinned.left >= 7 * 86400 - SLACK, 'D: recheck: until the owner approves the job again', JSON.stringify(pinned));
  await aDayLater(); await worker.scheduled({}, cron);
  eq([await statusOf(cron, v1), await one(cron, 'SELECT apply_host FROM jobs WHERE id = ?', v1)], ['live', 'boards.greenhouse.io'], 'D: recheck: once the owner has approved it, the new host is the one it is compared with');
  delete world.redirects[LINK]; delete world.pages[LINK];                 // the page is gone: nobody knows where the link leads now
  await aDayLater(); n = opened(); await worker.scheduled({}, cron);
  eq([opened() - n, await statusOf(cron, v1)], [1, 'live'], 'D: recheck: a link that does not open changes nothing by itself');
  world.pages[LINK] = PAGE; world.redirects[LINK] = 'https://t.me/vega_hr';
  await aDayLater(); await worker.scheduled({}, cron);
  row = await cron.DB.prepare('SELECT status, review_reason FROM jobs WHERE id = ?').bind(v1).first();
  ok(row.status === 'review' && /now leads to t\.me/.test(row.review_reason) && !world.fetched.includes('https://t.me/vega_hr'), 'D: recheck: a link that now redirects to a chat takes the job back to review, and the chat is not opened',
    JSON.stringify(row));
  delete world.redirects[LINK];

  const busy = newEnv(), many = await account(busy, 'boss@acme.dev');
  for (const title of ['Platform Engineer', 'Data Engineer', 'ML Engineer']) await call(busy, 'POST', '/api/jobs', { token: many, data: { ...GOOD, ...ATS, title } });
  await nextDay(busy);
  for (const title of ['QA Engineer', 'Support Engineer', 'Security Engineer']) await call(busy, 'POST', '/api/jobs', { token: many, data: { ...GOOD, ...ATS, title } });
  await busy.DB.exec('UPDATE jobs SET checked_at = checked_at - 90000');
  eq([await one(busy, "SELECT COUNT(*) FROM jobs WHERE status = 'live'"), (await recheckLinks(busy)).checked, (await recheckLinks(busy)).checked, (await recheckLinks(busy)).checked], [6, 4, 2, 0],
    'D: recheck: one run opens the links of four jobs, the next run takes the rest');
}

/* ---- 22. E: reports from job seekers, and the public numbers ---- */
{
  const env = newEnv(), admin = (method, p, data) => call(env, method, '/api/admin/' + p, { token: ADMIN, data });
  const LYRA = employer('lyra.dev', 'Lyra Labs'), lyra = await account(env, 'hr@lyra.dev'), lyraId = await one(env, 'SELECT id FROM users');
  const post = async (job) => (await call(env, 'POST', '/api/jobs', { token: lyra, data: job })).body.job, report = (job, reason, ip, note) => call(env, 'POST', '/api/report', { data: { job, reason, note }, ip });
  const reportsOf = async (id) => (await env.DB.prepare('SELECT decision FROM reports WHERE job_id = ? ORDER BY created_at, id').bind(id).all()).results.map((x) => x.decision);
  const a = (await post(LYRA('Senior Rust Engineer'))).id, b = (await post(LYRA('Senior Go Engineer'))).id, c = (await post(LYRA('Data Engineer'))).id;
  let r = await call(env, 'POST', '/api/jobs', { token: lyra, data: LYRA('Order Processing Agent', { description: GOOD.description + ' Top up your balance to unlock the premium orders.' }) });
  eq(r.status, 422, 'E: (a posting the screen rejects, for the numbers further down)');
  r = await call(env, 'POST', '/api/orders', { token: lyra, data: { product: 'featured', target: { job_id: a } } }); await hook(env, r.body.order.id);
  const placement = () => env.DB.prepare('SELECT held, starts_at, ends_at FROM placements WHERE target = ?').bind('direct:' + a).first(), running = await placement();

  r = await report(a, 'spam'); eq([r.status, r.body.error], [400, 'reason'], 'E: a report needs one of the six reasons');
  r = await report(a, 'other', undefined, 'x'.repeat(501)); eq([r.status, r.body.error], [400, 'note'], 'E: a note is 500 characters at most');
  r = await report('j_ffffffffffff', 'other'); eq([r.status, r.body.error], [404, 'job'], 'E: a job that does not exist cannot be reported');
  r = await report('no-such-job-anywhere', 'other'); eq([r.status, r.body.error], [404, 'job'], 'E: nor a page the site does not have');
  r = await report(undefined, 'other'); eq(r.status, 404, 'E: nor nothing at all');
  eq(await one(env, 'SELECT COUNT(*) FROM reports'), 0, 'E: a refused report stores nothing');

  r = await report(a, 'job_not_real', '203.0.113.7', 'The careers page of this company has no such role.');
  eq([r.status, r.body.ok, await statusOf(env, a)], [200, true, 'live'], 'E: one report of a mild kind is taken, without an account, and changes nothing yet');
  const kept = await env.DB.prepare('SELECT * FROM reports').first();
  ok(/^[a-f0-9]{32}$/.test(kept.ip_hash) && !JSON.stringify(kept).includes('203.0.113') && kept.note === 'The careers page of this company has no such role.' && kept.job_id === a && kept.reason === 'job_not_real',
    'E: the report keeps the job, the reason, the note and a hash of the address, never the address');
  ok(kept.ip_hash !== createHash('sha256').update('203.0.113.7').digest('hex').slice(0, 32) && (await one(env, "SELECT length(v) FROM meta WHERE k = 'ip_salt'")) === 32, 'E: and the hash is salted with a secret of this database');
  r = await report(a, 'other', '203.0.113.7'); eq([r.status, await one(env, 'SELECT COUNT(*) FROM reports'), await statusOf(env, a)], [200, 1, 'live'], 'E: the same address reporting the same job again is counted once');
  r = await report(a, 'moved_to_chat', '203.0.113.8');
  eq([r.status, await statusOf(env, a), await one(env, 'SELECT review_reason FROM jobs WHERE id = ?', a), (await exportedJobs(env)).some((j) => j.id === a)], [200, 'review', 'reported', false],
    'E: a second report from another address hides the job until a person decides');
  let p = await placement();
  ok(p.held === 1 && p.starts_at === 0 && p.ends_at <= 14 * 86400 && p.ends_at >= 14 * 86400 - SLACK, 'E: what was bought for the job stops running while it is hidden', JSON.stringify(p));
  const mine = (await call(env, 'GET', '/api/jobs', { token: lyra })).body.jobs.find((j) => j.id === a);
  eq([mine.status, mine.review_reason], ['review', 'reported'], 'E: the employer sees that the job was reported and is being looked at');
  r = await report(b, 'asks_for_money', '203.0.113.9'); eq(await statusOf(env, b), 'review', 'E: one report that the job asks for money hides it at once');
  r = await report(SITE + '/job/data-engineer-lyra-labs/', 'asks_to_install', '203.0.113.9'); eq([r.status, await statusOf(env, c)], [200, 'review'], 'E: so does one that it asks to install something; a job can be named by its page on the site');
  r = await report('staff-engineer-stripe', 'asks_for_money', '203.0.113.9', 'They wanted a deposit.');
  eq([r.status, await one(env, "SELECT COUNT(*) FROM reports WHERE slug = 'staff-engineer-stripe' AND job_id = ''"), (await call(env, 'GET', '/api/public/export.json')).body.boosts], [200, 1, []],
    'E: a report about a job read from a hiring system is stored and changes nothing by itself');
  const flood = await Promise.all(Array.from({ length: 12 }, () => report('staff-engineer-stripe', 'other', '203.0.113.50')));
  eq([flood.filter((f) => f.status === 200).length, flood.filter((f) => f.status === 429).length, await one(env, "SELECT COUNT(*) FROM reports WHERE slug = 'staff-engineer-stripe'")], [5, 7, 2],
    'E: twelve reports from one address at the same moment: five are taken, as the limit says, and they are one report');

  r = await call(env, 'GET', '/api/admin/reports'); eq(r.status, 403, 'E: the list of reports is for the owner');
  r = await admin('GET', 'reports');
  eq([r.status, r.body.reports.length, r.body.reports.filter((y) => y.job_id === a).map((y) => y.reason).sort(), r.body.reports.find((y) => y.note === 'They wanted a deposit.').page], [200, 6, ['job_not_real', 'moved_to_chat'], '/job/staff-engineer-stripe/'],
    'E: the owner sees every report with its job, reason and note');
  ok(!/ip_hash|203\.0\.113/.test(JSON.stringify(r.body)), 'E: and nothing about who sent it');
  r = await admin('GET', 'review');
  eq(r.body.jobs.map((j) => [j.title, j.reason, j.open_reports, j.report_reasons.split(',').sort().join()]).sort(), [['Data Engineer', 'reported', 1, 'asks_to_install'], ['Senior Go Engineer', 'reported', 1, 'asks_for_money'],
    ['Senior Rust Engineer', 'reported', 2, 'job_not_real,moved_to_chat']], 'E: reported jobs stand in the review queue with what was said about them');

  await env.DB.prepare('UPDATE reports SET created_at = created_at - 2 * 3600 WHERE job_id = ?').bind(a).run();      // sent two hours ago
  await env.DB.prepare('UPDATE reports SET created_at = created_at - 6 * 3600 WHERE job_id = ?').bind(b).run();      // six hours ago
  await admin('POST', 'jobs/' + a + '/approve'); p = await placement();
  eq([await statusOf(env, a), await reportsOf(a), p.held, Math.abs(p.ends_at - running.ends_at) <= SLACK, (await exportedJobs(env)).find((j) => j.id === a).featured_until > '2026'], ['live', ['dismissed', 'dismissed'], 0, true, true],
    'E: approving a reported job puts it back, dismisses the reports, and its placement goes on with the days it had left');
  r = await report(a, 'other', '203.0.113.20'); eq(await statusOf(env, a), 'live', 'E: dismissed reports do not count again: one new mild report changes nothing');
  await admin('POST', 'jobs/' + b + '/reject', { reason: 'Candidates were asked for a deposit.' });
  eq([await statusOf(env, b), await reportsOf(b), await one(env, 'SELECT upheld_reports FROM users WHERE id = ?', lyraId), (await call(env, 'GET', '/api/me', { token: lyra })).body.user.trusted], ['rejected', ['upheld'], 1, false],
    'E: rejecting a reported job upholds the report, and the account loses its trust');
  await nextDay(env);
  const next = await post(LYRA('QA Engineer'));
  ok(next.status === 'review' && /report about a job of this account was upheld/.test(next.review_reason), 'E: from then on the jobs of that account wait for a person', JSON.stringify(next));
  const lone = (await admin('GET', 'reports')).body.reports.find((y) => y.note === 'They wanted a deposit.').id;
  await env.DB.prepare('UPDATE reports SET created_at = created_at - 4 * 3600 WHERE id = ?').bind(lone).run();       // four hours ago
  r = await admin('POST', 'reports/' + lone + '/decide', { decision: 'maybe' }); eq(r.status, 400, 'E: a report is decided as upheld or dismissed, nothing else');
  r = await admin('POST', 'reports/' + lone + '/decide', { decision: 'upheld' });
  eq([r.status, await one(env, 'SELECT decision FROM reports WHERE id = ?', lone), (await admin('POST', 'reports/' + lone + '/decide', { decision: 'dismissed' })).status], [200, 'upheld', 404],
    'E: a report about a job from a hiring system is decided on its own, once');

  const month = new Date().toISOString().slice(0, 7), before = new Date(Date.UTC(new Date().getUTCFullYear(), new Date().getUTCMonth() - 1, 1)).toISOString().slice(0, 7);
  await env.DB.prepare("INSERT INTO stats (month, k, n) VALUES (?, 'screened', 7)").bind(before).run();
  r = await call(env, 'GET', '/api/public/transparency.json', { origin: 'https://anyone.test' });
  eq([r.status, r.headers.get('Access-Control-Allow-Origin')], [200, '*'], 'E: the numbers are public: any site may read them');
  eq(r.body.current, { month, jobs_checked: 5, jobs_rejected_by_screen: 1, jobs_held_for_review: 4, jobs_removed_after_report: 1, reports_received: 7, accounts_banned: 0, median_hours_report_to_decision: 3 },
    'E: this month: jobs checked and rejected by the screen, held for review, removed after a report, reports received, accounts banned, median hours to a decision');
  eq(r.body.previous, { month: before, jobs_checked: 7, jobs_rejected_by_screen: 0, jobs_held_for_review: 0, jobs_removed_after_report: 0, reports_received: 0, accounts_banned: 0, median_hours_report_to_decision: null },
    'E: the month before is counted apart, and its median is null when nothing was decided');
  ok(!/lyra|203\.0\.113|j_[a-f0-9]{12}/i.test(JSON.stringify(r.body)), 'E: counts only: no job, account or reporter in it');
  await admin('POST', 'accounts/' + lyraId + '/ban');
  r = await call(env, 'GET', '/api/public/transparency.json');
  // open when the account was banned: the report about c and the last one about a. Decided now: 0, 0, 2, 2, 4 and 6 hours after they came, median 2.
  eq([r.body.current.accounts_banned, r.body.current.jobs_removed_after_report, await reportsOf(c), await reportsOf(a), r.body.current.median_hours_report_to_decision], [1, 3, ['upheld'], ['dismissed', 'dismissed', 'upheld'], 2],
    'E: a ban is counted, settles as upheld the reports that were open about the account, and its jobs with such a report count as removed');
}

/* ---- 23. F: a sign-in from a new device is told to the owner of the address ---- */
{
  const box = mailbox(), outbox = box.outbox, env = newEnv(box);
  const MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36', MAC_UPDATED = MAC.replace('Chrome/130.0.0.0', 'Chrome/131.0.6778.86');
  const LINUX = 'Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0', PHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1';
  const login = (ua, password = PASS, email = 'hr@nova.dev', more = {}) => call(env, 'POST', '/api/auth/login', { data: { email, password }, ua, ...more });
  let r;
  const logged = await quiet(async () => {
    r = await call(env, 'POST', '/api/auth/signup', { data: { email: 'hr@nova.dev', password: PASS }, ua: MAC }); const session = r.body.token;
    outbox.length = 0;                                                       // the confirmation mail of the sign-up
    r = await login(MAC); eq([r.status, outbox.length], [200, 0], 'F: signing in from the browser that made the account sends no notice');
    r = await login(MAC_UPDATED); eq([r.status, outbox.length], [200, 0], 'F: an update of the same browser is not a new device');
    r = await login(LINUX); const fromLinux = r.body.token;
    eq([r.status, outbox.length, outbox[0].to, outbox[0].from, outbox[0].subject], [200, 1, 'hr@nova.dev', 'no-reply@site.test', 'A new sign-in to your employer account'], 'F: a sign-in from another browser sends a notice to the address of the account');
    const said = outbox[0].text;
    ok(said.includes(SITE) && /not been used in before/.test(said) && /Forgot password/.test(said), 'F: the notice says what happened and what to do if it was somebody else');
    ok(!said.includes(fromLinux) && !said.includes(session) && !said.includes(PASS) && !/[a-f0-9]{32,}/.test(said) && !said.includes('#'), 'F: the notice carries no token, no password and no link that signs anyone in');
    r = await login(LINUX); eq([r.status, outbox.length], [200, 1], 'F: the second sign-in from that browser sends nothing');
    await call(env, 'POST', '/api/auth/logout', { token: fromLinux }); await env.DB.exec('DELETE FROM sessions');
    r = await login(LINUX); eq([r.status, outbox.length], [200, 1], 'F: a browser stays known after its session has ended');
    r = await login(PHONE, 'not the password'); eq([r.status, outbox.length], [401, 0 + 1], 'F: a failed sign-in sends nothing');
    r = await login(PHONE); eq([r.status, outbox.length], [200, 2], 'F: and does not make its browser known: the first real sign-in from it is told');
    const devices = (await env.DB.prepare('SELECT * FROM devices').all()).results;
    ok(devices.length === 3 && devices.every((d) => /^[a-f0-9]{32}$/.test(d.ua_hash)) && !/Mozilla|Chrome|Firefox|iPhone/.test(JSON.stringify(devices)), 'F: of a browser only a hash is kept');
    await call(env, 'POST', '/api/auth/signup', { data: { email: 'hr@orbit.dev', password: PASS }, ua: MAC });
    r = await login(LINUX, PASS, 'hr@orbit.dev'); eq([r.status, outbox.length, outbox[outbox.length - 1].to, outbox[outbox.length - 1].subject], [200, 4, 'hr@orbit.dev', 'A new sign-in to your employer account'],
      'F: a browser known to one account is new to another');
    const waited = [];
    r = await login('Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge', PASS, 'hr@nova.dev', { ctx: { waitUntil: (w) => waited.push(w) } }); await Promise.all(waited);
    eq([r.status, waited.length, outbox.length], [200, 1, 5], 'F: the notice is handed to the runtime, so signing in does not wait for the mail service');
  });
  ok(logged.length === 0 && !outbox.some((m) => /password: |Bearer/.test(m.text)), 'F: nothing about a sign-in is written to the log');
  const plain = newEnv(); await call(plain, 'POST', '/api/auth/signup', { data: { email: 'hr@nova.dev', password: PASS }, ua: MAC });
  r = await call(plain, 'POST', '/api/auth/login', { data: { email: 'hr@nova.dev', password: PASS }, ua: LINUX }); eq(r.status, 200, 'F: without a mail service a sign-in from a new device still works');
}
ok(Object.values(PRODUCTS).every((p) => p.usd > 0 && p.name), 'every product has a name and a price');

console.log(`${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
