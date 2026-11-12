/* Hiring Right Now — API. One file, no dependencies. Runs on Cloudflare Workers with a D1 database.

   What it does: accounts, self-serve purchases (featured / pinned jobs, company spotlight, page sponsorship, job packs, Plus),
   crypto checkout through Cryptomus, and automatic activation the moment a payment is confirmed. Nobody has to answer an email.

   Bindings   DB (D1 database)
   Variables  SITE_URL       public address of the site, no trailing slash   (https://example.com)
              SITE_ORIGINS   origins allowed to call the API, comma separated  (https://example.com)
              API_URL        public address of this worker, no trailing slash
              GITHUB_REPO    owner/name of the site repository (optional, for instant rebuilds)
              PLUS_LIVE      "1" once Plus is on sale
              PAY_MODE       "test" ONLY on a developer machine: orders are paid by opening a link. Never set it in production.
   Secrets    CRYPTOMUS_MERCHANT, CRYPTOMUS_API_KEY   payment gateway (merchant id and payment API key)
              ADMIN_TOKEN                             owner-only endpoints
              GITHUB_TOKEN                            optional: fine-grained token with Actions: write on GITHUB_REPO
*/

const DAY = 86400;
const enc = new TextEncoder();
const now = () => Math.floor(Date.now() / 1000);
const hex = (buf) => Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
const unhex = (s) => new Uint8Array(s.match(/../g).map((h) => parseInt(h, 16)));
const rid = (prefix, bytes = 10) => prefix + hex(crypto.getRandomValues(new Uint8Array(bytes)));
const sha256 = async (s) => hex(await crypto.subtle.digest('SHA-256', enc.encode(s)));
const isoDay = (ts) => new Date(ts * 1000).toISOString().slice(0, 10);
const slugify = (s) => (String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, '')) || 'job';

/* Price list. Keep it in step with "prices" and "plus" in the site's config.json (those are what visitors read). */
export const PRODUCTS = {
  featured: { name: 'Featured job', usd: 99, kind: 'featured', days: 14, target: 'job', group: 'employer' },
  pinned: { name: 'Pinned job', usd: 199, kind: 'pinned', days: 7, target: 'job', group: 'employer' },
  pack5: { name: '5-job pack', usd: 399, credits: 5, creditDays: 90, target: 'none', group: 'employer' },
  spotlight: { name: 'Company spotlight', usd: 499, kind: 'spotlight', days: 30, target: 'company', group: 'employer' },
  sponsor: { name: 'Category or skill sponsor', usd: 299, kind: 'sponsor', days: 30, target: 'page', group: 'employer' },
  plus1: { name: 'Plus, 1 month', usd: 9, plusDays: 30, target: 'none', group: 'plus' },
  plus3: { name: 'Plus, 3 months', usd: 19, plusDays: 91, target: 'none', group: 'plus' },
  plus12: { name: 'Plus, 12 months', usd: 39, plusDays: 365, target: 'none', group: 'plus' },
};
const FREE_JOB_DAYS = 30, FREE_JOBS_LIVE = 5, FREE_JOBS_PER_DAY = 3;

class HttpError extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}
const bad = (code, message, status = 400) => new HttpError(status, code, message);

/* ---------------------------------------------------------------- small helpers */
function corsHeaders(env, req, open) {
  const origin = req.headers.get('Origin') || '';
  const allowed = String(env.SITE_ORIGINS || '').split(',').map((s) => s.trim()).filter(Boolean);
  const h = { Vary: 'Origin' };
  if (open) h['Access-Control-Allow-Origin'] = '*';
  else if (allowed.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  if (h['Access-Control-Allow-Origin']) {
    h['Access-Control-Allow-Headers'] = 'Authorization, Content-Type';
    h['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, OPTIONS';
    h['Access-Control-Max-Age'] = '86400';
  }
  return h;
}
const json = (data, status = 200, headers = {}) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers },
});
const db = (env, sql, ...args) => env.DB.prepare(sql).bind(...args);
const line = (v, max, min = 0) => {
  const s = typeof v === 'string' ? v.replace(/\s+/g, ' ').trim() : '';
  return s.length >= min && s.length <= max ? s : null;
};
const prose = (v, max, min = 0) => {            // plain text with line breaks, no markup
  const s = typeof v === 'string' ? v.replace(/<[^>]*>/g, ' ').replace(/[ \t\r]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim() : '';
  return s.length >= min && s.length <= max ? s : null;
};
const publicUrl = (v) => {
  try {
    const u = new URL(String(v || '').trim());
    if (u.protocol !== 'https:' || !u.hostname.includes('.') || /^[\d.]+$/.test(u.hostname) || u.hostname.includes(':') || u.username) return null;
    return u;
  } catch { return null; }
};
const siteDomain = (host) => host.replace(/^www\./, '').split('.').slice(-2).join('.');
async function body(req) {
  const text = await req.text();
  if (text.length > 20000) throw bad('too_large', 'The request is too large.', 413);
  try { const v = JSON.parse(text || '{}'); if (v && typeof v === 'object') return v; } catch {}
  throw bad('bad_json', 'The request body must be JSON.');
}
async function limit(env, key, max, windowSec) {
  const t = now(), row = await db(env, 'SELECT n, reset_at FROM rate WHERE k = ?', key).first();
  if (!row || row.reset_at <= t) { await db(env, 'INSERT OR REPLACE INTO rate (k, n, reset_at) VALUES (?, 1, ?)', key, t + windowSec).run(); return; }
  if (row.n >= max) throw bad('rate_limited', 'Too many attempts. Please wait a few minutes and try again.', 429);
  await db(env, 'UPDATE rate SET n = n + 1 WHERE k = ?', key).run();
}
const clientIp = (req) => req.headers.get('CF-Connecting-IP') || 'local';

/* ---------------------------------------------------------------- MD5 and the gateway's signature
   Cryptomus signs with md5(base64(json) + key), where json is PHP's json_encode output (slashes escaped). */
const MD5_K = Array.from({ length: 64 }, (_, i) => Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296) | 0);
const MD5_S = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21];
export function md5(input) {
  const msg = typeof input === 'string' ? enc.encode(input) : input, n = msg.length;
  const words = new Uint32Array((((n + 8) >>> 6) + 1) * 16);
  for (let i = 0; i < n; i++) words[i >> 2] |= msg[i] << ((i % 4) * 8);
  words[n >> 2] |= 0x80 << ((n % 4) * 8);
  words[words.length - 2] = (n * 8) >>> 0; words[words.length - 1] = Math.floor(n / 0x20000000);
  let a = 0x67452301, b = 0xefcdab89, c = 0x98badcfe, d = 0x10325476;
  for (let o = 0; o < words.length; o += 16) {
    let A = a, B = b, C = c, D = d;
    for (let i = 0; i < 64; i++) {
      const r = i >> 4; let f, g;
      if (r === 0) { f = (B & C) | (~B & D); g = i; }
      else if (r === 1) { f = (D & B) | (~D & C); g = (5 * i + 1) % 16; }
      else if (r === 2) { f = B ^ C ^ D; g = (3 * i + 5) % 16; }
      else { f = C ^ (B | ~D); g = (7 * i) % 16; }
      const x = (A + f + MD5_K[i] + words[o + g]) | 0, s = MD5_S[r * 4 + (i % 4)], t = D;
      D = C; C = B; B = (B + ((x << s) | (x >>> (32 - s)))) | 0; A = t;
    }
    a = (a + A) | 0; b = (b + B) | 0; c = (c + C) | 0; d = (d + D) | 0;
  }
  return [a, b, c, d].map((v) => [0, 8, 16, 24].map((sh) => ((v >>> sh) & 255).toString(16).padStart(2, '0')).join('')).join('');
}
function b64utf8(s) {
  const bytes = enc.encode(s); let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}
export function phpJson(value, unescapedUnicode) {
  let s = JSON.stringify(value).replace(/\//g, '\\/');
  if (!unescapedUnicode) s = s.replace(/[\u0080-￿]/g, (ch) => '\\u' + ch.charCodeAt(0).toString(16).padStart(4, '0'));
  return s;
}
export const gatewaySign = (jsonText, key) => md5(b64utf8(jsonText) + key);
// A webhook is genuine if its "sign" matches the body without that field. The exact re-encoding the gateway used is tried three ways.
export function webhookSignatureOk(raw, key) {
  let data; try { data = JSON.parse(raw); } catch { return false; }
  if (!data || typeof data.sign !== 'string' || !key) return false;
  const sign = data.sign.toLowerCase(), rest = { ...data }; delete rest.sign;
  let stripped = raw;
  const tail = raw.match(/,\s*"sign"\s*:\s*"[^"]*"/), lead = raw.match(/"sign"\s*:\s*"[^"]*"\s*,/);
  if (tail) stripped = raw.replace(tail[0], ''); else if (lead) stripped = raw.replace(lead[0], '');
  return [phpJson(rest, true), phpJson(rest, false), stripped].some((candidate) => gatewaySign(candidate, key) === sign);
}

async function gateway(env, path, payload) {
  const text = phpJson(payload, false);
  const res = await fetch('https://api.cryptomus.com' + path, {
    method: 'POST', body: text,
    headers: { 'Content-Type': 'application/json', merchant: env.CRYPTOMUS_MERCHANT, sign: gatewaySign(text, env.CRYPTOMUS_API_KEY) },
  });
  let data = null; try { data = await res.json(); } catch {}
  if (!res.ok || !data || data.state !== 0 || !data.result) throw bad('gateway_error', 'The payment service did not answer. Please try again in a minute.', 502);
  return data.result;
}

/* ---------------------------------------------------------------- accounts */
async function hashPassword(password, saltHex) {
  const salt = saltHex ? unhex(saltHex) : crypto.getRandomValues(new Uint8Array(16));
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt, iterations: 100000 }, key, 256);
  return { hash: hex(bits), salt: hex(salt) };
}
const sameText = (a, b) => { if (a.length !== b.length) return false; let d = 0; for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i); return d === 0; };
const cleanEmail = (v) => { const s = String(v || '').trim().toLowerCase(); return s.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(s) ? s : null; };
async function openSession(env, userId) {
  const token = rid('', 32), t = now();
  await db(env, 'INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)', await sha256(token), userId, t, t + 30 * DAY).run();
  return token;
}
async function currentUser(env, req, required = true) {
  const m = /^Bearer ([a-f0-9]{64})$/.exec(req.headers.get('Authorization') || '');
  if (m) {
    const row = await db(env, 'SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?', await sha256(m[1]), now()).first();
    if (row && !row.banned) return row;
  }
  if (required) throw bad('sign_in', 'Please sign in.', 401);
  return null;
}
async function userView(env, u) {
  const t = now();
  const credits = await db(env, 'SELECT COALESCE(SUM(remaining), 0) AS n FROM credits WHERE user_id = ? AND expires_at > ? AND remaining > 0', u.id, t).first('n');
  return { id: u.id, email: u.email, company: u.company, plus: u.plus_until > t, plus_until: u.plus_until > t ? isoDay(u.plus_until) : '', credits: Number(credits) || 0 };
}

async function signup(env, req) {
  await limit(env, 'signup:' + clientIp(req), 5, 3600);
  const b = await body(req), email = cleanEmail(b.email), password = typeof b.password === 'string' ? b.password : '';
  if (!email) throw bad('email', 'Enter a valid email address.');
  if (password.length < 8 || password.length > 200) throw bad('password', 'The password must be at least 8 characters long.');
  if (await db(env, 'SELECT 1 AS x FROM users WHERE email = ?', email).first()) throw bad('exists', 'An account with this email already exists. Sign in instead.', 409);
  const id = rid('u_'), p = await hashPassword(password);
  await db(env, 'INSERT INTO users (id, email, pass_hash, pass_salt, company, created_at) VALUES (?, ?, ?, ?, ?, ?)', id, email, p.hash, p.salt, line(b.company, 80) || '', now()).run();
  const user = await db(env, 'SELECT * FROM users WHERE id = ?', id).first();
  return { token: await openSession(env, id), user: await userView(env, user) };
}
async function login(env, req) {
  const b = await body(req), email = cleanEmail(b.email) || '';
  await limit(env, 'login:' + clientIp(req) + ':' + email, 10, 600);
  const user = email ? await db(env, 'SELECT * FROM users WHERE email = ?', email).first() : null;
  const p = await hashPassword(typeof b.password === 'string' ? b.password : '', user ? user.pass_salt : '00'.repeat(16));
  if (!user || user.banned || !sameText(p.hash, user.pass_hash)) throw bad('credentials', 'Wrong email or password.', 401);
  return { token: await openSession(env, user.id), user: await userView(env, user) };
}
async function logout(env, req) {
  const m = /^Bearer ([a-f0-9]{64})$/.exec(req.headers.get('Authorization') || '');
  if (m) await db(env, 'DELETE FROM sessions WHERE token_hash = ?', await sha256(m[1])).run();
  return { ok: true };
}

/* ---------------------------------------------------------------- what the site knows (used to check targets) */
let indexCache = { at: 0, companies: null };
async function indexedCompanies(env) {
  if (indexCache.companies && now() - indexCache.at < 3600) return indexCache.companies;
  try {
    const res = await fetch(env.SITE_URL + '/data/head.json');
    if (res.ok) { const d = await res.json(); indexCache = { at: now(), companies: new Map(d.c.map((c) => [c.toLowerCase(), c])) }; }
  } catch {}
  return indexCache.companies || new Map();
}
async function sitePage(env, path) {
  try { const res = await fetch(env.SITE_URL + path); return res.ok ? await res.text() : null; } catch { return null; }
}
const jobSlugFrom = (v) => { const s = String(v || '').trim(), m = /\/job\/([a-z0-9-]{1,140})\/?(?:[?#].*)?$/.exec(s); return m ? m[1] : /^[a-z0-9-]{1,140}$/.test(s) ? s : null; };

/* Works out what exactly is being bought and refuses anything that could not be shown on the site. */
async function resolveTarget(env, user, product, t) {
  t = t && typeof t === 'object' ? t : {};
  if (product.target === 'none') return { key: '', label: product.name };
  if (product.target === 'job') {
    if (t.job_id) {
      const j = await db(env, 'SELECT id, title, company FROM jobs WHERE id = ? AND user_id = ? AND status = ? AND expires_at > ?', String(t.job_id), user.id, 'live', now()).first();
      if (!j) throw bad('target', 'Pick one of your live jobs.');
      return { key: 'direct:' + j.id, label: j.title + ' at ' + j.company };
    }
    const slug = jobSlugFrom(t.job);
    if (!slug) throw bad('target', 'Paste the link to the job on this site, for example ' + env.SITE_URL + '/job/…/');
    const page = await sitePage(env, '/job/' + slug + '/');
    if (!page) throw bad('target', 'We could not find that job on the site. Check the link.');
    if (/This job is closed/.test(page)) throw bad('target', 'That job is closed, so it cannot be promoted.');
    const title = (/<title>([^<]*)<\/title>/.exec(page) || [])[1] || slug;
    return { key: 'job:' + slug, label: title.replace(/&amp;/g, '&').replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').slice(0, 140) };
  }
  // a company: either one from the index, or one this account has a live job for
  const wanted = line(t.company, 80, 2);
  if (!wanted) throw bad('target', 'Enter the company name exactly as it appears on the site.');
  let company = (await indexedCompanies(env)).get(wanted.toLowerCase());
  if (!company) {
    const own = await db(env, 'SELECT company FROM jobs WHERE user_id = ? AND status = ? AND expires_at > ? AND lower(company) = ?', user.id, 'live', now(), wanted.toLowerCase()).first();
    if (own) company = own.company;
  }
  if (!company) throw bad('target', 'That company has no open jobs on the site yet. Post a job first, or check the spelling.');
  if (product.target === 'company') return { key: 'company:' + company, label: company };
  const m = /^(skill|category):([a-z0-9-]{1,60})$/.exec(String(t.page || ''));
  if (!m) throw bad('target', 'Choose the category or skill page to sponsor.');
  if (!(await sitePage(env, (m[1] === 'skill' ? '/skills/' : '/jobs/') + m[2] + '/'))) throw bad('target', 'That page does not exist on the site.');
  return { key: m[1] + ':' + m[2] + '|' + company, label: company + ' on ' + m[2].replace(/-/g, ' ') + ' jobs' };
}

/* ---------------------------------------------------------------- orders and activation */
const orderView = (o) => ({ id: o.id, product: o.product, name: (PRODUCTS[o.product] || {}).name || o.product, label: o.label, amount_usd: o.amount_usd, status: o.status,
  pay_url: o.status === 'pending' ? o.pay_url : '', created: isoDay(o.created_at), paid: o.paid_at ? isoDay(o.paid_at) : '' });

async function createOrder(env, req, user) {
  await limit(env, 'order:' + user.id, 20, 3600);
  const b = await body(req), product = PRODUCTS[b.product];
  if (!product) throw bad('product', 'Unknown product.');
  if (product.group === 'plus' && env.PLUS_LIVE !== '1') throw bad('not_on_sale', 'Plus is not on sale yet.', 409);
  const target = await resolveTarget(env, user, product, b.target);
  const id = rid('o_'), t = now();
  if (b.use_credit) {                                         // a prepaid featured listing from a pack: no payment step
    if (b.product !== 'featured') throw bad('credit', 'Pack credits are for featured jobs.');
    const credit = await db(env, 'SELECT id FROM credits WHERE user_id = ? AND remaining > 0 AND expires_at > ? ORDER BY expires_at LIMIT 1', user.id, t).first();
    const used = credit ? await db(env, 'UPDATE credits SET remaining = remaining - 1 WHERE id = ? AND remaining > 0', credit.id).run() : null;
    if (!used || !used.meta.changes) throw bad('credit', 'You have no pack credits left.', 409);
    await db(env, 'INSERT INTO orders (id, user_id, product, target, label, amount_usd, status, provider, created_at) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)',
      id, user.id, b.product, target.key, target.label, 'pending', 'credit', t).run();
    await activate(env, id);
    return { order: orderView(await db(env, 'SELECT * FROM orders WHERE id = ?', id).first()) };
  }
  let provider, uuid = '', payUrl;
  if (env.PAY_MODE === 'test') { provider = 'test'; payUrl = env.API_URL + '/api/dev/pay/' + id; }
  else {
    if (!env.CRYPTOMUS_MERCHANT || !env.CRYPTOMUS_API_KEY) throw bad('payments_off', 'Payments are not switched on yet.', 503);
    const invoice = await gateway(env, '/v1/payment', {
      amount: String(product.usd), currency: 'USD', order_id: id, lifetime: 3600, additional_data: b.product,
      url_callback: env.API_URL + '/api/webhooks/cryptomus', url_return: env.SITE_URL + '/account/', url_success: env.SITE_URL + '/account/?order=' + id,
    });
    provider = 'cryptomus'; uuid = String(invoice.uuid || ''); payUrl = String(invoice.url || '');
    if (!payUrl) throw bad('gateway_error', 'The payment service did not return a payment page.', 502);
  }
  await db(env, 'INSERT INTO orders (id, user_id, product, target, label, amount_usd, status, provider, provider_uuid, pay_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    id, user.id, b.product, target.key, target.label, product.usd, 'pending', provider, uuid, payUrl, t).run();
  return { order: orderView(await db(env, 'SELECT * FROM orders WHERE id = ?', id).first()) };
}

/* Turns a paid order into what was bought. Safe to call any number of times: only the first call does anything. */
async function activate(env, orderId) {
  const t = now();
  const first = await db(env, "UPDATE orders SET status = 'paid', paid_at = ? WHERE id = ? AND status IN ('pending', 'expired', 'underpaid', 'failed')", t, orderId).run();
  if (!first.meta.changes) return false;
  const o = await db(env, 'SELECT * FROM orders WHERE id = ?', orderId).first(), p = PRODUCTS[o.product];
  if (p.kind) {
    const busyUntil = await db(env, 'SELECT MAX(ends_at) AS e FROM placements WHERE kind = ? AND target = ? AND cancelled = 0 AND ends_at > ?', p.kind, o.target, t).first('e');
    const start = Math.max(t, Number(busyUntil) || 0);      // buying again while it is running adds time instead of overlapping
    await db(env, 'INSERT INTO placements (id, order_id, user_id, kind, target, label, starts_at, ends_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
      rid('p_'), o.id, o.user_id, p.kind, o.target, o.label, start, start + p.days * DAY).run();
  }
  if (p.credits) await db(env, 'INSERT INTO credits (id, user_id, order_id, remaining, expires_at) VALUES (?, ?, ?, ?, ?)', rid('c_'), o.user_id, o.id, p.credits, t + p.creditDays * DAY).run();
  if (p.plusDays) await db(env, 'UPDATE users SET plus_until = MAX(plus_until, ?) + ? WHERE id = ?', t, p.plusDays * DAY, o.user_id).run();
  if (p.kind) await requestRebuild(env);
  return true;
}
async function settle(env, order, status) {                    // status as the gateway reports it
  if (status === 'paid' || status === 'paid_over') return activate(env, order.id);
  if (order.status !== 'pending') {
    if (status === 'refund_paid' && order.status === 'paid') {
      await env.DB.batch([db(env, "UPDATE orders SET status = 'refunded' WHERE id = ?", order.id), db(env, 'UPDATE placements SET cancelled = 1 WHERE order_id = ?', order.id),
        db(env, 'UPDATE credits SET remaining = 0 WHERE order_id = ?', order.id)]);
      await requestRebuild(env);
    }
    return false;
  }
  const next = status === 'wrong_amount' ? 'underpaid' : status === 'cancel' ? 'expired' : status === 'fail' || status === 'system_fail' ? 'failed' : '';
  if (next) await db(env, 'UPDATE orders SET status = ? WHERE id = ? AND status = ?', next, order.id, 'pending').run();
  return false;
}
// Ask the gateway itself what happened to an invoice (the source of truth; a webhook is only a hint that something changed).
async function refreshOrder(env, order) {
  if (order.provider !== 'cryptomus' || !['pending', 'underpaid', 'expired'].includes(order.status) || now() - order.checked_at < 10) return;
  await db(env, 'UPDATE orders SET checked_at = ? WHERE id = ?', now(), order.id).run();
  const info = await gateway(env, '/v1/payment/info', { order_id: order.id });
  if (String(info.order_id) === order.id) await settle(env, order, String(info.payment_status || info.status || ''));
}
async function cryptomusWebhook(env, req) {
  const raw = await req.text();
  let data; try { data = JSON.parse(raw); } catch { return json({ ok: false }, 400); }
  const order = data && typeof data.order_id === 'string' ? await db(env, 'SELECT * FROM orders WHERE id = ?', data.order_id).first() : null;
  if (!order || order.provider !== 'cryptomus') return json({ ok: true });       // nothing of ours: acknowledge so it is not resent forever
  if (webhookSignatureOk(raw, env.CRYPTOMUS_API_KEY)) await settle(env, order, String(data.status || ''));
  else { try { await refreshOrder(env, order); } catch {} }                      // unsigned or oddly encoded: ignore its content, check with the gateway
  return json({ ok: true });
}

/* ---------------------------------------------------------------- jobs posted here */
const BLOCKED_HOSTS = /(^|\.)(bit\.ly|tinyurl\.com|t\.co|t\.me|telegram\.me|wa\.me|whatsapp\.com|forms\.gle|docs\.google\.com|linktr\.ee|discord\.gg|facebook\.com|instagram\.com)$/;
const HIRING_SYSTEMS = /(^|\.)(greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|smartrecruiters\.com|bamboohr\.com|myworkdayjobs\.com|recruitee\.com|teamtailor\.com|breezy\.hr|jobvite\.com|icims\.com|personio\.com|personio\.de|rippling\.com|pinpointhq\.com|workday\.com|join\.com|notion\.site)$/;
const ETYPES = ['', 'Full-time', 'Contract', 'Part-time', 'Internship'];

/* A posting is accepted only if its link really opens that job on the company's own site or hiring system.
   This is the automatic stand-in for a moderator: it keeps out scam "jobs" that lead to a chat or a form. */
async function checkApplyLink(apply, companyUrl, title) {
  if (BLOCKED_HOSTS.test(apply.hostname)) return 'The link to apply must open the job on your own site or hiring system, not a messenger, form or link shortener.';
  const onSystem = HIRING_SYSTEMS.test(apply.hostname);
  if (!onSystem && siteDomain(apply.hostname) !== siteDomain(companyUrl.hostname)) return 'The link to apply must be on your company site (' + siteDomain(companyUrl.hostname) + ') or on a hiring system such as Greenhouse, Lever or Ashby.';
  let text = '';
  try {
    const res = await fetch(apply.href, { redirect: 'follow', headers: { 'User-Agent': 'Mozilla/5.0 (compatible; job-link-check)' }, signal: AbortSignal.timeout(8000) });
    if (!res.ok) return 'The link to apply does not open (the page answered ' + res.status + ').';
    text = (await res.text()).slice(0, 600000).toLowerCase();
  } catch { return 'The link to apply did not open. Check the address and try again.'; }
  if (onSystem) return '';
  const words = [...new Set(title.toLowerCase().match(/[a-z0-9+#]{3,}/g) || [])].slice(0, 8);
  const hits = words.filter((w) => text.includes(w)).length;
  return words.length && hits / words.length >= 0.6 ? '' : 'We could not find this job at the link. It must open the page of this exact job, with the same title.';
}
async function readJob(env, b, existing) {
  const company = line(b.company, 80, 2), title = line(b.title, 120, 4), companyUrl = publicUrl(b.company_url), apply = publicUrl(b.apply_url);
  const description = prose(b.description, 1500, 80);
  if (!company) throw bad('company', 'Enter the company name.');
  if (!companyUrl) throw bad('company_url', 'Enter the address of the company site, starting with https://');
  if (!title) throw bad('title', 'Enter the job title (4 to 120 characters).');
  if (!apply) throw bad('apply_url', 'Enter the link where people apply, starting with https://');
  if (!description) throw bad('description', 'Describe the role in 80 to 1,500 characters.');
  if ((description.match(/https?:\/\//g) || []).length > 2) throw bad('description', 'Please keep links out of the description: candidates apply through the link above.');
  if ((await indexedCompanies(env)).has(company.toLowerCase())) throw bad('listed', company + ' is already listed here automatically from its careers page. You can promote any of its jobs instead of posting again.', 409);
  const etype = ETYPES.includes(b.etype) ? b.etype : '';
  if (!existing || existing.apply_url !== apply.href || existing.title !== title) {
    const problem = await checkApplyLink(apply, companyUrl, title);
    if (problem) throw bad('apply_url', problem, 422);
  }
  return { company, company_url: companyUrl.origin, title, apply_url: apply.href, location: line(b.location, 120) || '', remote: b.remote ? 1 : 0, salary: line(b.salary, 60) || '', etype, description };
}
const jobView = (j, t) => ({ id: j.id, company: j.company, company_url: j.company_url, title: j.title, apply_url: j.apply_url, location: j.location, remote: !!j.remote, salary: j.salary, etype: j.etype,
  description: j.description, status: j.status === 'live' && j.expires_at <= t ? 'expired' : j.status, posted: isoDay(j.created_at), until: isoDay(j.expires_at),
  page: '/job/' + slugify(j.title) + '-' + slugify(j.company) + '/' });
async function createJob(env, req, user) {
  const t = now(), j = await readJob(env, await body(req), null);
  const live = await db(env, 'SELECT COUNT(*) AS n FROM jobs WHERE user_id = ? AND status = ? AND expires_at > ?', user.id, 'live', t).first('n');
  if (live >= FREE_JOBS_LIVE) throw bad('limit', 'You can have ' + FREE_JOBS_LIVE + ' free jobs live at a time. Close one first.', 409);
  const today = await db(env, 'SELECT COUNT(*) AS n FROM jobs WHERE user_id = ? AND created_at > ?', user.id, t - DAY).first('n');
  if (today >= FREE_JOBS_PER_DAY) throw bad('limit', 'You can post ' + FREE_JOBS_PER_DAY + ' jobs a day. Please come back tomorrow.', 429);
  const id = rid('j_', 6);
  await db(env, 'INSERT INTO jobs (id, user_id, company, company_url, title, apply_url, location, remote, salary, etype, description, status, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    id, user.id, j.company, j.company_url, j.title, j.apply_url, j.location, j.remote, j.salary, j.etype, j.description, 'live', t, t + FREE_JOB_DAYS * DAY).run();
  if (!user.company) await db(env, 'UPDATE users SET company = ? WHERE id = ?', j.company, user.id).run();
  await requestRebuild(env);
  return { job: jobView(await db(env, 'SELECT * FROM jobs WHERE id = ?', id).first(), t) };
}
async function updateJob(env, req, user, id, action) {
  const t = now(), old = await db(env, 'SELECT * FROM jobs WHERE id = ? AND user_id = ?', id, user.id).first();
  if (!old || old.status === 'removed') throw bad('not_found', 'Job not found.', 404);
  if (action === 'close') await db(env, "UPDATE jobs SET status = 'closed' WHERE id = ?", id).run();
  else if (action === 'renew') await db(env, "UPDATE jobs SET status = 'live', expires_at = ? WHERE id = ?", t + FREE_JOB_DAYS * DAY, id).run();
  else {
    const j = await readJob(env, { ...jobView(old, t), ...(await body(req)) }, old);
    await db(env, 'UPDATE jobs SET company = ?, company_url = ?, title = ?, apply_url = ?, location = ?, remote = ?, salary = ?, etype = ?, description = ? WHERE id = ?',
      j.company, j.company_url, j.title, j.apply_url, j.location, j.remote, j.salary, j.etype, j.description, id).run();
  }
  await requestRebuild(env);
  return { job: jobView(await db(env, 'SELECT * FROM jobs WHERE id = ?', id).first(), t) };
}

/* ---------------------------------------------------------------- what the site build reads */
async function exportForSite(env) {
  const t = now();
  // one row per thing that is live now; "ends" covers time bought on top of the running period
  const live = (await db(env, 'SELECT kind, target, MAX(ends_at) AS ends FROM placements WHERE cancelled = 0 AND ends_at > ? GROUP BY kind, target HAVING MIN(starts_at) <= ?', t, t).all()).results;
  const boosts = [], sponsors = [], direct = {};
  for (const p of live) {
    const until = isoDay(p.ends), [type, rest] = [p.target.slice(0, p.target.indexOf(':')), p.target.slice(p.target.indexOf(':') + 1)];
    if (type === 'job') boosts.push({ slug: rest, kind: p.kind, until });
    else if (type === 'direct') (direct[rest] = direct[rest] || {})[p.kind] = until;
    else if (type === 'company') sponsors.push({ company: rest, slot: 'spotlight', until });
    else { const cut = rest.indexOf('|'); sponsors.push({ company: rest.slice(cut + 1), slot: type + ':' + rest.slice(0, cut), until }); }
  }
  const jobs = (await db(env, "SELECT * FROM jobs WHERE status = 'live' AND expires_at > ? ORDER BY created_at", t).all()).results.map((j) => ({
    id: j.id, company: j.company, company_url: j.company_url, title: j.title, url: j.apply_url, location: j.location, remote: !!j.remote, salary: j.salary, etype: j.etype,
    text: j.description, posted: isoDay(j.created_at), featured_until: (direct[j.id] || {}).featured || '', pinned_until: (direct[j.id] || {}).pinned || '' }));
  return { generated: new Date(t * 1000).toISOString(), boosts, sponsors, jobs };
}
/* Ask GitHub to rebuild the site so a change shows up within minutes instead of at the next daily run. At most once in ten minutes. */
async function requestRebuild(env, fromTimer) {
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return;
  const t = now(), last = Number(await db(env, "SELECT v FROM meta WHERE k = 'rebuild_at'").first('v')) || 0;
  if (t - last < 600) { if (!fromTimer) await db(env, "INSERT OR REPLACE INTO meta (k, v) VALUES ('rebuild_wanted', '1')").run(); return; }
  await env.DB.batch([db(env, "INSERT OR REPLACE INTO meta (k, v) VALUES ('rebuild_at', ?)", String(t)), db(env, "INSERT OR REPLACE INTO meta (k, v) VALUES ('rebuild_wanted', '0')")]);
  try {
    await fetch('https://api.github.com/repos/' + env.GITHUB_REPO + '/actions/workflows/update.yml/dispatches', {
      method: 'POST', body: JSON.stringify({ ref: 'main' }),
      headers: { Authorization: 'Bearer ' + env.GITHUB_TOKEN, Accept: 'application/vnd.github+json', 'User-Agent': 'hiring-right-now-api', 'Content-Type': 'application/json' },
    });
  } catch {}
}

/* ---------------------------------------------------------------- router */
async function route(env, req, url) {
  const path = url.pathname.replace(/\/+$/, ''), m = req.method, seg = path.split('/').slice(2);     // /api/<seg...>
  if (path === '/api/health') return { ok: true };
  if (path === '/api/public/export.json' && m === 'GET') return exportForSite(env);
  if (path === '/api/public/products' && m === 'GET') {
    return { products: Object.entries(PRODUCTS).filter(([, p]) => p.group !== 'plus' || env.PLUS_LIVE === '1').map(([id, p]) => ({ id, name: p.name, usd: p.usd, days: p.days || p.plusDays || 0, target: p.target, group: p.group })),
      payments: env.PAY_MODE === 'test' ? 'test' : env.CRYPTOMUS_MERCHANT && env.CRYPTOMUS_API_KEY ? 'on' : 'off' };
  }
  if (path === '/api/auth/signup' && m === 'POST') return signup(env, req);
  if (path === '/api/auth/login' && m === 'POST') return login(env, req);
  if (path === '/api/auth/logout' && m === 'POST') return logout(env, req);
  if (path === '/api/webhooks/cryptomus' && m === 'POST') return cryptomusWebhook(env, req);
  if (seg[0] === 'dev' && seg[1] === 'pay' && env.PAY_MODE === 'test') {                               // developer machines only
    const o = await db(env, "SELECT * FROM orders WHERE id = ? AND provider = 'test'", seg[2] || '').first();
    if (!o) throw bad('not_found', 'Order not found.', 404);
    await activate(env, o.id);
    return Response.redirect(env.SITE_URL + '/account/?order=' + o.id, 302);
  }
  if (seg[0] === 'admin') return admin(env, req, seg, m);

  const user = await currentUser(env, req), t = now();
  if (path === '/api/me' && m === 'GET') return { user: await userView(env, user) };
  if (path === '/api/orders' && m === 'POST') return createOrder(env, req, user);
  if (path === '/api/orders' && m === 'GET') {
    await db(env, "UPDATE orders SET status = 'expired' WHERE user_id = ? AND status = 'pending' AND created_at < ?", user.id, t - 2 * 3600).run();
    return { orders: (await db(env, 'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', user.id).all()).results.map(orderView) };
  }
  if (seg[0] === 'orders' && seg[1] && m === 'GET') {
    let o = await db(env, 'SELECT * FROM orders WHERE id = ? AND user_id = ?', seg[1], user.id).first();
    if (!o) throw bad('not_found', 'Order not found.', 404);
    if (url.searchParams.has('refresh')) { try { await refreshOrder(env, o); } catch {} o = await db(env, 'SELECT * FROM orders WHERE id = ?', o.id).first(); }
    return { order: orderView(o) };
  }
  if (path === '/api/placements' && m === 'GET') {
    const rows = (await db(env, 'SELECT * FROM placements WHERE user_id = ? AND cancelled = 0 ORDER BY ends_at DESC LIMIT 200', user.id).all()).results;
    return { placements: rows.map((p) => ({ id: p.id, kind: p.kind, label: p.label, from: isoDay(p.starts_at), until: isoDay(p.ends_at), state: p.ends_at <= t ? 'ended' : p.starts_at > t ? 'scheduled' : 'live' })) };
  }
  if (path === '/api/jobs' && m === 'POST') return createJob(env, req, user);
  if (path === '/api/jobs' && m === 'GET') return { jobs: (await db(env, "SELECT * FROM jobs WHERE user_id = ? AND status != 'removed' ORDER BY created_at DESC", user.id).all()).results.map((j) => jobView(j, t)) };
  if (seg[0] === 'jobs' && seg[1] && (m === 'PATCH' || m === 'POST')) return updateJob(env, req, user, seg[1], m === 'POST' ? seg[2] : 'edit');
  if (path === '/api/sync') {                                                                          // Plus: the same saved jobs on every device
    if (user.plus_until <= t) throw bad('plus', 'Sync between devices is part of Plus.', 402);
    if (m === 'GET') { const row = await db(env, 'SELECT data, updated_at FROM sync WHERE user_id = ?', user.id).first(); return { data: row ? JSON.parse(row.data) : null, updated: row ? row.updated_at : 0 }; }
    if (m === 'PUT') {
      const text = JSON.stringify((await body(req)).data || {});
      await db(env, 'INSERT OR REPLACE INTO sync (user_id, data, updated_at) VALUES (?, ?, ?)', user.id, text, t).run();
      return { updated: t };
    }
  }
  throw bad('not_found', 'Not found.', 404);
}
async function admin(env, req, seg, m) {
  const given = (req.headers.get('Authorization') || '').replace(/^Bearer /, '');
  if (!env.ADMIN_TOKEN || !sameText(given, env.ADMIN_TOKEN)) throw bad('forbidden', 'Not allowed.', 403);
  if (seg[1] === 'overview' && m === 'GET') {
    const one = (sql) => db(env, sql).first('n');
    return { users: await one('SELECT COUNT(*) AS n FROM users'), paid_orders: await one("SELECT COUNT(*) AS n FROM orders WHERE status = 'paid' AND amount_usd > 0"),
      revenue_usd: await one("SELECT COALESCE(SUM(amount_usd), 0) AS n FROM orders WHERE status = 'paid'"), live_jobs: await one("SELECT COUNT(*) AS n FROM jobs WHERE status = 'live'"),
      recent_orders: (await db(env, 'SELECT id, product, label, amount_usd, status, created_at FROM orders ORDER BY created_at DESC LIMIT 30').all()).results,
      recent_jobs: (await db(env, 'SELECT id, company, title, apply_url, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 30').all()).results };
  }
  if (seg[1] === 'jobs' && seg[3] === 'remove' && m === 'POST') { await db(env, "UPDATE jobs SET status = 'removed' WHERE id = ?", seg[2]).run(); await requestRebuild(env); return { ok: true }; }
  if (seg[1] === 'users' && seg[3] === 'ban' && m === 'POST') {
    await env.DB.batch([db(env, 'UPDATE users SET banned = 1 WHERE id = ?', seg[2]), db(env, 'DELETE FROM sessions WHERE user_id = ?', seg[2]), db(env, "UPDATE jobs SET status = 'removed' WHERE user_id = ?", seg[2])]);
    await requestRebuild(env); return { ok: true };
  }
  throw bad('not_found', 'Not found.', 404);
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url), open = url.pathname.startsWith('/api/public/'), cors = corsHeaders(env, req, open);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    try {
      const out = await route(env, req, url);
      if (out instanceof Response) return out;
      return json(out, 200, open ? { ...cors, 'Cache-Control': 'public, max-age=60' } : cors);
    } catch (err) {
      if (err instanceof HttpError) return json({ error: err.code, message: err.message }, err.status, cors);
      console.error(err && err.stack ? err.stack : err);
      return json({ error: 'server', message: 'Something went wrong on our side. Please try again.' }, 500, cors);
    }
  },
  // every ten minutes: send a rebuild that was held back, and close invoices nobody paid
  async scheduled(event, env) {
    const t = now();
    await db(env, "UPDATE orders SET status = 'expired' WHERE status = 'pending' AND created_at < ?", t - 2 * 3600).run();
    await db(env, 'DELETE FROM sessions WHERE expires_at < ?', t).run();
    await db(env, 'DELETE FROM rate WHERE reset_at < ?', t).run();
    if ((await db(env, "SELECT v FROM meta WHERE k = 'rebuild_wanted'").first('v')) === '1') await requestRebuild(env, true);
  },
};
