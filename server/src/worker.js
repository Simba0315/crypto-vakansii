/* Hiring Right Now — API. One file, no dependencies. Runs on Cloudflare Workers with a D1 database.

   What it does: accounts, self-serve purchases (featured / pinned jobs, company spotlight, page sponsorship, job packs, Plus),
   crypto checkout through Cryptomus, and automatic activation the moment a payment is confirmed. Nobody has to answer an email.

   Bindings   DB (D1 database)
              MAIL           optional: anything with send({ from, to, subject, text }). Until it is bound no email leaves (see sendMail).
   Variables  SITE_URL       public address of the site, no trailing slash   (https://example.com)
              SITE_ORIGINS   origins allowed to call the API, comma separated  (https://example.com)
              API_URL        public address of this worker, no trailing slash
              GITHUB_REPO    owner/name of the site repository (optional, for instant rebuilds)
              PLUS_LIVE      "1" once Plus is on sale
              MAIL_FROM      optional: the sender address handed to MAIL
              PAY_MODE       "test" ONLY on a developer machine: orders are paid by opening a link and a password reset answers with its
                             token instead of mailing it. Never set it in production.
   Secrets    CRYPTOMUS_MERCHANT, CRYPTOMUS_API_KEY   payment gateway (merchant id and payment API key)
              ADMIN_TOKEN                             owner-only endpoints
              GITHUB_TOKEN                            optional: fine-grained token with Actions: write on GITHUB_REPO
   Cron       every ten minutes (wrangler.toml): asks the gateway about invoices whose webhook never came, tidies up, sends held-back rebuilds.
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
const FREE_JOB_DAYS = 30, FREE_JOBS_PER_DAY = 3, LINK_CHECKS_PER_HOUR = 30;
const INVOICE_LIFETIME = 3600;            // seconds an invoice can be paid, as told to the gateway
const ORDER_GRACE = 900;                  // an unpaid invoice is closed this long after its lifetime ran out
const ORDER_GIVE_UP = DAY;                // ... or this long after it was made, when the gateway cannot say or the money is still on its way
const RECONCILE_AFTER = 300;              // the cron leaves an order alone for its first minutes: the webhook normally settles it
const RECONCILE_BATCH = 20;               // invoices asked about in one cron run (a Worker has a budget of outgoing requests)
const RESET_MINUTES = 30;                 // how long a password reset link works

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
    h['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS';
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
/* An address this service is willing to store and to open: https on the default port, no login in it, a public host name.
   IP addresses in any spelling (the URL parser turns 2130706433 and 0x7f.1 into 127.0.0.1), IPv6, single-label names, private and
   special-use zones and the "any address as a name" services are refused. Where a public name resolves cannot be seen from here. */
const PRIVATE_HOSTS = /(^|\.)(localhost|local|localdomain|internal|intranet|lan|home|corp|arpa|test|invalid|example|onion|nip\.io|sslip\.io|xip\.io|localtest\.me|lvh\.me)$/;
const publicUrl = (v, max = 500) => {
  try {
    const s = String(v || '').trim(), u = new URL(s), host = u.hostname;
    if (s.length > max || u.protocol !== 'https:' || u.username || u.password || u.port) return null;
    if (!host.includes('.') || host.endsWith('.') || host.includes(':') || /^[\d.]+$/.test(host) || PRIVATE_HOSTS.test(host)) return null;
    return u;
  } catch { return null; }
};
/* The part of a host name that has one owner: "jobs.acme.co.uk" -> "acme.co.uk". There is no public-suffix list here, so it is a rule of
   thumb: country zones with a generic second level, and hosts where anyone can get a subdomain, keep one more label. */
const SHARED_HOSTS = /^(github\.io|gitlab\.io|pages\.dev|workers\.dev|vercel\.app|netlify\.app|web\.app|firebaseapp\.com|herokuapp\.com|onrender\.com|webflow\.io|wixsite\.com|wordpress\.com|blogspot\.com|framer\.website|framer\.app|carrd\.co|substack\.com|azurewebsites\.net|cloudfront\.net)$/;
const siteDomain = (host) => {
  const parts = host.replace(/^www\./, '').split('.'), two = parts.slice(-2).join('.');
  return parts.slice(parts.length > 2 && (/^(co|com|org|net|gov|edu|ac)\.[a-z]{2}$/.test(two) || SHARED_HOSTS.test(two)) ? -3 : -2).join('.');
};
/* What makes two spellings the same company: case, spaces around and repeated inside, and punctuation at the end. So "Acme", "ACME ",
   "Acme  " and "Acme!" share one key. Nothing else is folded, on purpose: "Acme Inc" and "Acme" stay two companies. */
export const companyKey = (name) => {
  const tidy = (s) => s.replace(/[​-‏⁠﻿]/g, '').replace(/\s+/g, ' ').replace(/[\s\p{P}\p{S}]+$/u, '').trim();
  return tidy(tidy(String(name || '')).normalize('NFKC').toLowerCase());
};
async function body(req) {
  const text = await req.text();
  if (text.length > 20000) throw bad('too_large', 'The request is too large.', 413);
  try { const v = JSON.parse(text || '{}'); if (v && typeof v === 'object') return v; } catch {}
  throw bad('bad_json', 'The request body must be JSON.');
}
/* Counts one attempt and says whether it is still within the limit. It is a single statement: the counter is created or raised and its
   new value comes back from the same write, so requests arriving together cannot all read "not yet" before any of them writes. */
async function allowed(env, key, max, windowSec) {
  const t = now();
  const n = await db(env, 'INSERT INTO rate (k, n, reset_at) VALUES (?, 1, ?) ON CONFLICT(k) DO UPDATE SET n = CASE WHEN rate.reset_at <= ? THEN 1 ELSE rate.n + 1 END, ' +
    'reset_at = CASE WHEN rate.reset_at <= ? THEN excluded.reset_at ELSE rate.reset_at END RETURNING n', key, t + windowSec, t, t).first('n');
  return Number(n) <= max;
}
async function limit(env, key, max, windowSec) {
  if (!(await allowed(env, key, max, windowSec))) throw bad('rate_limited', 'Too many attempts. Please wait a few minutes and try again.', 429);
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
  return [phpJson(rest, true), phpJson(rest, false), stripped].some((candidate) => sameText(gatewaySign(candidate, key), sign));
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
  const b = await body(req), email = cleanEmail(b.email), password = typeof b.password === 'string' ? b.password : '', company = line(b.company, 80) || '';
  if (!email) throw bad('email', 'Enter a valid email address.');
  if (password.length < 8 || password.length > 200) throw bad('password', 'The password must be at least 8 characters long.');
  if (await db(env, 'SELECT 1 AS x FROM users WHERE email = ?', email).first()) throw bad('exists', 'An account with this email already exists. Sign in instead.', 409);
  // the name on an account is only a label (a name is taken by posting a checked job, see claimCompany), but it may not be one another account holds
  if (company && await db(env, 'SELECT 1 AS x FROM companies WHERE k = ?', companyKey(company)).first()) throw bad('company_taken', COMPANY_TAKEN, 409);
  const id = rid('u_'), p = await hashPassword(password);
  await db(env, 'INSERT INTO users (id, email, pass_hash, pass_salt, company, created_at) VALUES (?, ?, ?, ?, ?, ?)', id, email, p.hash, p.salt, company, now()).run();
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

/* The one place mail leaves from. No mail service is connected yet: bind MAIL to anything with send({ from, to, subject, text })
   (a service binding to a mail worker, for example) and password resets start arriving. Until then nothing is sent and it says so.
   The text is never logged: it carries the reset link. */
export async function sendMail(env, to, subject, text) {
  if (!env.MAIL || typeof env.MAIL.send !== 'function') return { sent: false };
  try { await env.MAIL.send({ from: String(env.MAIL_FROM || ''), to, subject, text }); return { sent: true }; }
  catch { console.error('mail: sending failed'); return { sent: false }; }
}
/* Password reset, step one. The answer is the same whether or not there is such an account, so it cannot be used to find out who has one.
   The link carries a random token; only its hash is stored, it works once and for RESET_MINUTES. */
async function resetRequest(env, req, ctx) {
  await limit(env, 'reset-ip:' + clientIp(req), 5, 3600);
  const b = await body(req), email = cleanEmail(b.email);
  if (!email) throw bad('email', 'Enter a valid email address.');
  const out = { ok: true, message: 'If there is an account with this email, a link to set a new password is on its way. It works for ' + RESET_MINUTES + ' minutes.' };
  const token = rid('', 32), hash = await sha256(token), t = now();
  const within = await allowed(env, 'reset:' + email, 3, 3600);                    // per account; over the limit the request is quietly dropped
  const user = within ? await db(env, 'SELECT id FROM users WHERE email = ? AND banned = 0', email).first() : null;
  if (user) {
    await db(env, 'INSERT INTO resets (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)', hash, user.id, t, t + RESET_MINUTES * 60).run();
    const mail = sendMail(env, email, 'Set a new password', 'Someone asked to set a new password for your account at ' + env.SITE_URL + '.\n\n' +
      'Open this link within ' + RESET_MINUTES + ' minutes to choose one:\n' + env.SITE_URL + '/account/#reset=' + token + '\n\nIf it was not you, ignore this message: your password stays as it is.\n');
    if (ctx && typeof ctx.waitUntil === 'function') ctx.waitUntil(mail); else await mail;      // the answer does not wait for the mail service
  }
  if (env.PAY_MODE === 'test') out.token = token;      // developer machines only: there is no mailbox to read the link from (for an unknown email it opens nothing)
  return out;
}
/* Step two: the token and a new password. One batch, so it is all or nothing and the token cannot be used twice even by two requests
   at once: the batch that runs first deletes the token, the other one finds nothing. Every session of the account ends. */
async function resetConfirm(env, req) {
  await limit(env, 'reset-try:' + clientIp(req), 10, 600);
  const b = await body(req), token = typeof b.token === 'string' && /^[a-f0-9]{64}$/.test(b.token) ? b.token : '', password = typeof b.password === 'string' ? b.password : '';
  if (password.length < 8 || password.length > 200) throw bad('password', 'The password must be at least 8 characters long.');
  const t = now(), hash = token ? await sha256(token) : '', stale = bad('reset', 'This link does not work any more. Ask for a new one.');
  const live = 'SELECT r.user_id FROM resets r JOIN users u ON u.id = r.user_id WHERE r.token_hash = ? AND r.expires_at > ? AND u.banned = 0';
  if (!hash || !(await db(env, live, hash, t).first())) throw stale;
  const p = await hashPassword(password);
  const done = await env.DB.batch([
    db(env, 'UPDATE users SET pass_hash = ?, pass_salt = ? WHERE id = (' + live + ')', p.hash, p.salt, hash, t),
    db(env, 'DELETE FROM sessions WHERE user_id = (' + live + ')', hash, t),
    db(env, 'DELETE FROM resets WHERE user_id = (' + live + ')', hash, t),
  ]);
  if (!done[0].meta.changes) throw stale;
  return { ok: true };
}

/* ---------------------------------------------------------------- what the site knows (used to check targets) */
let indexCache = { at: 0, companies: null };
async function indexedCompanies(env) {
  if (indexCache.companies && now() - indexCache.at < 3600) return indexCache.companies;
  try {
    const res = await fetch(env.SITE_URL + '/data/head.json');
    if (res.ok) { const d = await res.json(); indexCache = { at: now(), companies: new Map(d.c.map((c) => [companyKey(c), c])) }; }
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
  let company = (await indexedCompanies(env)).get(companyKey(wanted));
  if (!company) {
    const own = await db(env, 'SELECT company FROM jobs WHERE user_id = ? AND status = ? AND expires_at > ? AND company_key = ?', user.id, 'live', now(), companyKey(wanted)).first();
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
    const noCredit = bad('credit', 'You have no pack credits left.', 409);
    const credit = await db(env, 'SELECT id FROM credits WHERE user_id = ? AND remaining > 0 AND expires_at > ? ORDER BY expires_at LIMIT 1', user.id, t).first();
    if (!credit) throw noCredit;
    await db(env, 'INSERT INTO orders (id, user_id, product, target, label, amount_usd, status, provider, created_at) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)',
      id, user.id, b.product, target.key, target.label, 'pending', 'credit', t).run();
    if (!(await activate(env, id, credit.id))) {               // the credit went to a request that arrived at the same moment
      await db(env, "UPDATE orders SET status = 'failed' WHERE id = ? AND status = 'pending'", id).run();
      throw noCredit;
    }
    return { order: orderView(await db(env, 'SELECT * FROM orders WHERE id = ?', id).first()) };
  }
  let provider, uuid = '', payUrl;
  if (env.PAY_MODE === 'test') { provider = 'test'; payUrl = env.API_URL + '/api/dev/pay/' + id; }
  else {
    if (!env.CRYPTOMUS_MERCHANT || !env.CRYPTOMUS_API_KEY) throw bad('payments_off', 'Payments are not switched on yet.', 503);
    const invoice = await gateway(env, '/v1/payment', {
      amount: String(product.usd), currency: 'USD', order_id: id, lifetime: INVOICE_LIFETIME, additional_data: b.product,
      url_callback: env.API_URL + '/api/webhooks/cryptomus', url_return: env.SITE_URL + '/account/', url_success: env.SITE_URL + '/account/?order=' + id,
    });
    provider = 'cryptomus'; uuid = String(invoice.uuid || ''); payUrl = String(invoice.url || '');
    if (!payUrl) throw bad('gateway_error', 'The payment service did not return a payment page.', 502);
  }
  await db(env, 'INSERT INTO orders (id, user_id, product, target, label, amount_usd, status, provider, provider_uuid, pay_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    id, user.id, b.product, target.key, target.label, product.usd, 'pending', provider, uuid, payUrl, t).run();
  return { order: orderView(await db(env, 'SELECT * FROM orders WHERE id = ?', id).first()) };
}

/* Turns a paid order into what was bought: all of it or none of it, and only once however many times it is called.
   Everything is one batch, which D1 runs as a single transaction. Its first statement marks the order paid and stamps it with a mark only
   this call knows; every other statement writes only where that mark is on the order. A repeated or parallel call (a webhook sent twice,
   the cron and a webhook together) finds the order already paid, stamps nothing, and so writes nothing. If any statement fails, the order
   stays unpaid and the next webhook or cron run does the whole thing again. creditId: the pack credit that pays for this order, spent in
   the same batch. One order gives at most one placement and one row of credits; the unique indexes in schema.sql back that up. */
async function activate(env, orderId, creditId = '') {
  const o = await db(env, 'SELECT * FROM orders WHERE id = ?', orderId).first(), p = o && PRODUCTS[o.product];
  if (!o || !['pending', 'expired', 'underpaid', 'failed'].includes(o.status)) return false;
  if (!p) { console.error('activate: order ' + o.id + ' is for a product that is not in the price list'); return false; }
  const t = now(), mark = rid('a_'), mine = 'EXISTS (SELECT 1 FROM orders WHERE id = ? AND activation = ?)';
  const steps = [creditId
    ? db(env, "UPDATE orders SET status = 'paid', paid_at = ?, activation = ? WHERE id = ? AND status IN ('pending', 'expired', 'underpaid', 'failed') " +
        'AND EXISTS (SELECT 1 FROM credits WHERE id = ? AND user_id = orders.user_id AND remaining > 0 AND expires_at > ?)', t, mark, o.id, creditId, t)
    : db(env, "UPDATE orders SET status = 'paid', paid_at = ?, activation = ? WHERE id = ? AND status IN ('pending', 'expired', 'underpaid', 'failed')", t, mark, o.id)];
  if (creditId) steps.push(db(env, 'UPDATE credits SET remaining = remaining - 1 WHERE id = ? AND remaining > 0 AND ' + mine, creditId, o.id, mark));
  if (p.kind) steps.push(db(env,                          // buying again while it is running adds time instead of overlapping
    'INSERT INTO placements (id, order_id, user_id, kind, target, label, starts_at, ends_at) SELECT ?, id, user_id, ?, target, label, start, start + ? FROM (' +
    'SELECT o.id, o.user_id, o.target, o.label, MAX(?, COALESCE((SELECT MAX(p.ends_at) FROM placements p WHERE p.kind = ? AND p.target = o.target AND p.cancelled = 0 AND p.ends_at > ?), 0)) AS start ' +
    'FROM orders o WHERE o.id = ? AND o.activation = ?)', rid('p_'), p.kind, p.days * DAY, t, p.kind, t, o.id, mark));
  if (p.credits) steps.push(db(env, 'INSERT INTO credits (id, user_id, order_id, remaining, expires_at) SELECT ?, user_id, id, ?, ? FROM orders WHERE id = ? AND activation = ?',
    rid('c_'), p.credits, t + p.creditDays * DAY, o.id, mark));
  if (p.plusDays) steps.push(db(env, 'UPDATE users SET plus_until = MAX(plus_until, ?) + ? WHERE id = ? AND ' + mine, t, p.plusDays * DAY, o.user_id, o.id, mark));
  const done = await env.DB.batch(steps);
  if (!done[0].meta.changes) return false;
  if (p.kind) { try { await requestRebuild(env); } catch {} }     // what was bought is recorded; a rebuild that could not be asked for is picked up by the daily build
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
/* Ask the gateway itself what happened to one invoice (the source of truth; a webhook is only a hint that something changed) and bring
   the order in line: a paid one is activated, a cancelled or failed one is closed, and an unpaid one is closed once its lifetime is over.
   While the gateway reports money on its way, or does not answer, the order is left open, for a day at most; a payment that turns up
   after an order was closed is still honoured by the webhook or by a check on demand.
   Returns the order's status afterwards, or '' when the gateway was not asked: not a gateway order, already settled, or asked less than
   minGap seconds ago. That last test and the note of the time are one statement, so two callers cannot both get through. */
const MONEY_ON_ITS_WAY = ['process', 'confirm_check', 'wrong_amount_waiting', 'locked'];
async function reconcileOrder(env, order, minGap) {
  if (order.provider !== 'cryptomus' || !['pending', 'underpaid', 'expired'].includes(order.status)) return '';
  const t = now(), mine = await db(env, 'UPDATE orders SET checked_at = ? WHERE id = ? AND checked_at <= ?', t, order.id, t - minGap).run();
  if (!mine.meta.changes) return '';
  let status = null;
  try {
    const info = await gateway(env, '/v1/payment/info', { order_id: order.id });
    if (String(info.order_id) === order.id) status = String(info.payment_status || info.status || '');
  } catch {}
  if (status !== null) await settle(env, order, status);
  const age = t - order.created_at, waiting = status === null || MONEY_ON_ITS_WAY.includes(status);
  if (age > (waiting ? ORDER_GIVE_UP : INVOICE_LIFETIME + ORDER_GRACE)) await db(env, "UPDATE orders SET status = 'expired' WHERE id = ? AND status = 'pending'", order.id).run();
  return String(await db(env, 'SELECT status FROM orders WHERE id = ?', order.id).first('status'));
}
/* Settles orders that are still pending although their webhook should have come long ago: without this a paid invoice whose webhook was
   lost would stay pending for ever. Run by the cron for everybody (the longest unchecked first, RECONCILE_BATCH at a time), and for one
   account when it opens its list of orders. Orders with no gateway behind them (test mode, pack credits) simply lapse. */
export async function reconcileOrders(env, userId = '') {
  const t = now(), who = userId ? ' AND user_id = ?' : '', whose = userId ? [userId] : [], seen = { checked: 0, paid: 0, expired: 0 };
  await db(env, "UPDATE orders SET status = 'expired' WHERE status = 'pending' AND provider != 'cryptomus' AND created_at < ?" + who, t - 2 * INVOICE_LIFETIME, ...whose).run();
  const due = (await db(env, "SELECT * FROM orders WHERE status = 'pending' AND provider = 'cryptomus' AND created_at <= ? AND checked_at <= ?" + who +
    ' ORDER BY checked_at, created_at LIMIT ' + (userId ? 3 : RECONCILE_BATCH), t - RECONCILE_AFTER, t - 60, ...whose).all()).results;
  for (const o of due) {
    try {
      const status = await reconcileOrder(env, o, 60);
      if (status) { seen.checked++; if (status === 'paid' || status === 'expired') seen[status]++; }
    } catch (err) { console.error('reconcile: order ' + o.id + ' failed: ' + (err && err.message)); }     // one bad order does not hold up the rest
  }
  return seen;
}
async function cryptomusWebhook(env, req) {
  const raw = await req.text();
  let data; try { data = JSON.parse(raw); } catch { return json({ ok: false }, 400); }
  const order = data && typeof data.order_id === 'string' ? await db(env, 'SELECT * FROM orders WHERE id = ?', data.order_id).first() : null;
  if (!order || order.provider !== 'cryptomus') return json({ ok: true });       // nothing of ours: acknowledge so it is not resent forever
  if (webhookSignatureOk(raw, env.CRYPTOMUS_API_KEY)) await settle(env, order, String(data.status || ''));
  else { try { await reconcileOrder(env, order, 10); } catch {} }                // unsigned or oddly encoded: ignore its content, check with the gateway
  return json({ ok: true });
}

/* ---------------------------------------------------------------- jobs posted here */
const BLOCKED_HOSTS = /(^|\.)(bit\.ly|tinyurl\.com|t\.co|t\.me|telegram\.me|wa\.me|whatsapp\.com|forms\.gle|docs\.google\.com|linktr\.ee|discord\.gg|facebook\.com|instagram\.com)$/;
const HIRING_SYSTEMS = /(^|\.)(greenhouse\.io|lever\.co|ashbyhq\.com|workable\.com|smartrecruiters\.com|bamboohr\.com|myworkdayjobs\.com|recruitee\.com|teamtailor\.com|breezy\.hr|jobvite\.com|icims\.com|personio\.com|personio\.de|rippling\.com|pinpointhq\.com|workday\.com|join\.com|notion\.site)$/;
const ETYPES = ['', 'Full-time', 'Contract', 'Part-time', 'Internship'];

const LINK_TIMEOUT = 8000, LINK_HOPS = 4, LINK_BYTES = 600000;
async function readStart(res, max) {            // the first max bytes of a page as text, however long the page is
  if (!res.body) return (await res.text()).slice(0, max);
  const reader = res.body.getReader(), dec = new TextDecoder();
  let text = '', got = 0;
  while (got < max) { const { done, value } = await reader.read(); if (done) break; got += value.length; text += dec.decode(value, { stream: true }); }
  try { await reader.cancel(); } catch {}
  return text.slice(0, max);
}
/* A posting is accepted only if its link opens a page of that job on the company's own site or on a known hiring system.
   This is the automatic stand-in for a moderator: it keeps out scam "jobs" that lead to a chat or a form. What it checks:
   - the link and every redirect after it (LINK_HOPS at most, followed here one by one, never by fetch itself) must be an address publicUrl
     accepts: https, default port, no login, a public host name and not an IP address, localhost or a private zone; must not be a messenger,
     a form or a link shortener; and must be on the company's site (see siteDomain) or on a hiring system;
   - the whole walk has LINK_TIMEOUT ms; the last answer must be 2xx and an HTML page; only its first LINK_BYTES are read;
   - on the company's own site that page must contain every word of the job title (the first eight words of three letters or more).
   What it cannot do from a Worker, so nobody expects it: see which address a host name resolves to (a Worker's requests do not reach
   private networks, that is the real barrier), and read the title on a hiring system, since most of them draw the page in the browser:
   there, a page that opens is accepted. A page that lists several jobs and happens to contain all the words also passes. */
async function checkApplyLink(apply, companyUrl, title) {
  const home = siteDomain(companyUrl.hostname), signal = AbortSignal.timeout(LINK_TIMEOUT);
  const refused = (u, hop) => {
    if (!u) return 'The link to apply redirects to an address we cannot open. It must stay on https and on a public site.';
    if (BLOCKED_HOSTS.test(u.hostname)) return 'The link to apply must open the job on your own site or hiring system, not a messenger, form or link shortener.';
    if (!HIRING_SYSTEMS.test(u.hostname) && siteDomain(u.hostname) !== home) return 'The link to apply must ' + (hop ? 'stay' : 'be') + ' on your company site (' + home + ') or on a hiring system such as Greenhouse, Lever or Ashby.';
    return '';
  };
  let url = apply, text = '';
  try {
    for (let hop = 0; ; hop++) {
      const problem = refused(url, hop);
      if (problem) return problem;
      const res = await fetch(url.href, { redirect: 'manual', headers: { 'User-Agent': 'Mozilla/5.0 (compatible; job-link-check)', Accept: 'text/html,application/xhtml+xml' }, signal });
      const next = res.status >= 300 && res.status < 400 ? res.headers.get('Location') : null;
      if (next) {
        try { if (res.body) await res.body.cancel(); } catch {}
        if (hop >= LINK_HOPS) return 'The link to apply redirects too many times. Give the address of the job page itself.';
        url = publicUrl(new URL(next, url.href).href, 2000);
        continue;
      }
      if (!res.ok) return 'The link to apply does not open (the page answered ' + res.status + ').';
      if (!/^\s*(text\/html|application\/xhtml\+xml)\s*(;|$)/i.test(res.headers.get('Content-Type') || '')) return 'The link to apply must open a web page, not a file or a download.';
      text = (await readStart(res, LINK_BYTES)).toLowerCase();
      break;
    }
  } catch { return 'The link to apply did not open. Check the address and try again.'; }
  if (HIRING_SYSTEMS.test(url.hostname)) return '';
  const words = [...new Set(title.toLowerCase().match(/[\p{L}\p{N}+#]{3,}/gu) || [])].slice(0, 8);
  return words.length && words.every((w) => text.includes(w)) ? '' : 'We could not find this job at the link. It must open the page of this exact job, with the same title.';
}
/* One company name, one account. A name is taken by the first account that publishes a checked job under it; signing up with a name
   takes nothing. Names are compared by companyKey, both the name as first written and the key are kept, and later jobs of the same
   account are stored under the name as first written, so the site sees one company, not one per spelling. */
const COMPANY_TAKEN = 'Another account already posts jobs under this company name. Sign in to that account, or use the exact name of your own company.';
async function claimCompany(env, user, name, key) {
  await db(env, 'INSERT INTO companies (k, name, user_id, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(k) DO NOTHING', key, name, user.id, now()).run();
  const held = await db(env, 'SELECT name, user_id FROM companies WHERE k = ?', key).first();
  if (!held || held.user_id !== user.id) throw bad('company_taken', COMPANY_TAKEN, 409);     // two accounts at the same moment: the insert let only one in
  return held.name;
}
/* Checks a job as sent, for a new one and for an edit alike. An edit goes through the same checks as a new job; the only thing it may
   skip is opening the link again, and only when nothing the link check depends on (link, title, company, company site) has changed. */
async function readJob(env, user, b, existing) {
  const company = line(b.company, 80, 2), title = line(b.title, 120, 4), companyUrl = publicUrl(b.company_url, 200), apply = publicUrl(b.apply_url);
  const description = prose(b.description, 1500, 80), key = companyKey(company);
  if (!company || !key || key.length > 100) throw bad('company', 'Enter the company name.');
  if (!companyUrl) throw bad('company_url', 'Enter the address of the company site, starting with https://');
  if (!title) throw bad('title', 'Enter the job title (4 to 120 characters).');
  if (!apply) throw bad('apply_url', 'Enter the link where people apply, starting with https://');
  if (!description) throw bad('description', 'Describe the role in 80 to 1,500 characters.');
  if ((description.match(/https?:\/\//g) || []).length > 2) throw bad('description', 'Please keep links out of the description: candidates apply through the link above.');
  const held = await db(env, 'SELECT name, user_id FROM companies WHERE k = ?', key).first();
  if (held && held.user_id !== user.id) throw bad('company_taken', COMPANY_TAKEN, 409);
  // The site's list of companies also holds the ones that got there through jobs posted here, so a company this account already posts
  // under is on it after the first job. That is this account's own company, not one "listed automatically", and must not stop a second job.
  if (!held && (await indexedCompanies(env)).has(key)) throw bad('listed', company + ' is already listed here automatically from its careers page. You can promote any of its jobs instead of posting again.', 409);
  const etype = ETYPES.includes(b.etype) ? b.etype : '';
  if (!existing || existing.apply_url !== apply.href || existing.title !== title || existing.company_key !== key || existing.company_url !== companyUrl.origin) {
    await limit(env, 'linkcheck:' + user.id, LINK_CHECKS_PER_HOUR, 3600);      // each check makes this service open an address someone typed
    const problem = await checkApplyLink(apply, companyUrl, title);
    if (problem) throw bad('apply_url', problem, 422);
  }
  return { company: held ? held.name : company, company_key: key, company_url: companyUrl.origin, title, apply_url: apply.href, location: line(b.location, 120) || '', remote: b.remote ? 1 : 0,
    salary: line(b.salary, 60) || '', etype, description };
}
const jobView = (j, t) => ({ id: j.id, company: j.company, company_url: j.company_url, title: j.title, apply_url: j.apply_url, location: j.location, remote: !!j.remote, salary: j.salary, etype: j.etype,
  description: j.description, status: j.status === 'live' && j.expires_at <= t ? 'expired' : j.status, posted: isoDay(j.created_at), until: isoDay(j.expires_at),
  page: '/job/' + slugify(j.title) + '-' + slugify(j.company) + '/' });
/* An employer may post any number of jobs. The one brake is how many a day: counted in a single statement (see allowed), and only for
   jobs that passed every check, so a typo does not use up the day. */
async function createJob(env, req, user) {
  const t = now(), j = await readJob(env, user, await body(req), null);
  if (!(await allowed(env, 'jobs:' + user.id, FREE_JOBS_PER_DAY, DAY))) throw bad('limit', 'You can post ' + FREE_JOBS_PER_DAY + ' jobs a day. Please come back tomorrow.', 429);
  j.company = await claimCompany(env, user, j.company, j.company_key);
  const id = rid('j_', 6);
  await db(env, 'INSERT INTO jobs (id, user_id, company, company_key, company_url, title, apply_url, location, remote, salary, etype, description, status, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
    id, user.id, j.company, j.company_key, j.company_url, j.title, j.apply_url, j.location, j.remote, j.salary, j.etype, j.description, 'live', t, t + FREE_JOB_DAYS * DAY).run();
  if (!user.company) await db(env, 'UPDATE users SET company = ? WHERE id = ?', j.company, user.id).run();
  await requestRebuild(env);
  return { job: jobView(await db(env, 'SELECT * FROM jobs WHERE id = ?', id).first(), t) };
}
/* Takes jobs off the site for good and switches off what was bought for them: a featured or pinned placement must not outlive its job. */
const takeDown = (env, where, arg) => [db(env, "UPDATE placements SET cancelled = 1 WHERE target IN (SELECT 'direct:' || id FROM jobs WHERE " + where + ')', arg),
  db(env, "UPDATE jobs SET status = 'removed' WHERE " + where, arg)];
async function updateJob(env, req, user, id, action) {
  const t = now(), old = await db(env, 'SELECT * FROM jobs WHERE id = ? AND user_id = ?', id, user.id).first();
  if (!old || old.status === 'removed' || !['edit', 'close', 'renew', 'delete'].includes(action)) throw bad('not_found', 'Job not found.', 404);
  if (action === 'close') await db(env, "UPDATE jobs SET status = 'closed' WHERE id = ?", id).run();
  else if (action === 'renew') await db(env, "UPDATE jobs SET status = 'live', expires_at = ? WHERE id = ?", t + FREE_JOB_DAYS * DAY, id).run();
  else if (action === 'delete') await env.DB.batch(takeDown(env, 'id = ?', id));
  else {
    const j = await readJob(env, user, { ...jobView(old, t), ...(await body(req)) }, old);
    if (j.company_key !== old.company_key) j.company = await claimCompany(env, user, j.company, j.company_key);
    await db(env, 'UPDATE jobs SET company = ?, company_key = ?, company_url = ?, title = ?, apply_url = ?, location = ?, remote = ?, salary = ?, etype = ?, description = ? WHERE id = ?',
      j.company, j.company_key, j.company_url, j.title, j.apply_url, j.location, j.remote, j.salary, j.etype, j.description, id).run();
  }
  await requestRebuild(env);
  if (action === 'delete') return { ok: true };
  return { job: jobView(await db(env, 'SELECT * FROM jobs WHERE id = ?', id).first(), t) };
}

/* ---------------------------------------------------------------- what the site build reads */
/* Says, for the target of a placement, whether it may be shown now. Only jobs that are live count: a closed, deleted, taken-down or
   run-out job takes with it what was bought for it, and a company that is on the site only through jobs posted here is promoted only
   while one of them is live. Placements on jobs and companies from the index are left to the site, which knows whether those are open. */
async function shownNow(env, t, liveJobs) {
  const rows = liveJobs || (await db(env, "SELECT id, company_key FROM jobs WHERE status = 'live' AND expires_at > ?", t).all()).results;
  const ids = new Set(rows.map((j) => j.id)), liveHere = new Set(rows.map((j) => j.company_key)), postedHere = new Set((await db(env, 'SELECT k FROM companies').all()).results.map((c) => c.k));
  return (target) => {
    const cut = target.indexOf(':'), type = target.slice(0, cut), rest = target.slice(cut + 1);
    if (type === 'job') return true;
    if (type === 'direct') return ids.has(rest);
    const k = companyKey(type === 'company' ? rest : rest.slice(rest.indexOf('|') + 1));
    return !postedHere.has(k) || liveHere.has(k);
  };
}
async function exportForSite(env) {
  const t = now();
  // one row per thing that is live now; "ends" covers time bought on top of the running period
  const live = (await db(env, 'SELECT kind, target, MAX(ends_at) AS ends FROM placements WHERE cancelled = 0 AND ends_at > ? GROUP BY kind, target HAVING MIN(starts_at) <= ?', t, t).all()).results;
  // only jobs that are live now leave this service: closed, deleted, taken-down and run-out ones are not in the list
  const rows = (await db(env, "SELECT * FROM jobs WHERE status = 'live' AND expires_at > ? ORDER BY created_at", t).all()).results, shown = await shownNow(env, t, rows);
  const boosts = [], sponsors = [], direct = {};
  for (const p of live) {
    if (!shown(p.target)) continue;
    const until = isoDay(p.ends), [type, rest] = [p.target.slice(0, p.target.indexOf(':')), p.target.slice(p.target.indexOf(':') + 1)];
    if (type === 'job') boosts.push({ slug: rest, kind: p.kind, until });
    else if (type === 'direct') (direct[rest] = direct[rest] || {})[p.kind] = until;
    else if (type === 'company') sponsors.push({ company: rest, slot: 'spotlight', until });
    else { const cut = rest.indexOf('|'); sponsors.push({ company: rest.slice(cut + 1), slot: type + ':' + rest.slice(0, cut), until }); }
  }
  const jobs = rows.map((j) => ({
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
async function route(env, req, url, ctx) {
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
  if (path === '/api/auth/reset/request' && m === 'POST') return resetRequest(env, req, ctx);
  if (path === '/api/auth/reset/confirm' && m === 'POST') return resetConfirm(env, req);
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
    try { await reconcileOrders(env, user.id); } catch {}      // an old invoice is closed only after the gateway was asked whether it was paid
    return { orders: (await db(env, 'SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 100', user.id).all()).results.map(orderView) };
  }
  if (seg[0] === 'orders' && seg[1] && m === 'GET') {
    let o = await db(env, 'SELECT * FROM orders WHERE id = ? AND user_id = ?', seg[1], user.id).first();
    if (!o) throw bad('not_found', 'Order not found.', 404);
    // the account page polls this after checkout: one order is checked with the gateway on demand, at most once in ten seconds per order
    // (reconcileOrder) and a bounded number of times per account, whatever the page or a script does
    if (url.searchParams.has('refresh') && await allowed(env, 'check:' + user.id, 60, 600)) {
      try { await reconcileOrder(env, o, 10); } catch {}
      o = await db(env, 'SELECT * FROM orders WHERE id = ?', o.id).first();
    }
    return { order: orderView(o) };
  }
  if (path === '/api/placements' && m === 'GET') {
    const rows = (await db(env, 'SELECT * FROM placements WHERE user_id = ? AND cancelled = 0 ORDER BY ends_at DESC LIMIT 200', user.id).all()).results;
    const shown = await shownNow(env, t);                  // paused: paid for and running, but its job is closed or ran out, so the site does not show it
    return { placements: rows.map((p) => ({ id: p.id, kind: p.kind, label: p.label, from: isoDay(p.starts_at), until: isoDay(p.ends_at),
      state: p.ends_at <= t ? 'ended' : !shown(p.target) ? 'paused' : p.starts_at > t ? 'scheduled' : 'live' })) };
  }
  if (path === '/api/jobs' && m === 'POST') return createJob(env, req, user);
  if (path === '/api/jobs' && m === 'GET') return { jobs: (await db(env, "SELECT * FROM jobs WHERE user_id = ? AND status != 'removed' ORDER BY created_at DESC", user.id).all()).results.map((j) => jobView(j, t)) };
  if (seg[0] === 'jobs' && seg[1] && (m === 'PATCH' || m === 'POST' || m === 'DELETE')) return updateJob(env, req, user, seg[1], m === 'DELETE' ? 'delete' : m === 'PATCH' ? 'edit' : seg[2] || 'edit');
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
  if (seg[1] === 'jobs' && seg[3] === 'remove' && m === 'POST') { await env.DB.batch(takeDown(env, 'id = ?', seg[2])); await requestRebuild(env); return { ok: true }; }
  if (seg[1] === 'users' && seg[3] === 'ban' && m === 'POST') {            // everything of this account goes: sessions, reset links, jobs, what it bought, the company names it held
    await env.DB.batch([db(env, 'UPDATE users SET banned = 1 WHERE id = ?', seg[2]), db(env, 'DELETE FROM sessions WHERE user_id = ?', seg[2]), db(env, 'DELETE FROM resets WHERE user_id = ?', seg[2]),
      ...takeDown(env, 'user_id = ?', seg[2]), db(env, 'UPDATE placements SET cancelled = 1 WHERE user_id = ?', seg[2]), db(env, 'DELETE FROM companies WHERE user_id = ?', seg[2])]);
    await requestRebuild(env); return { ok: true };
  }
  throw bad('not_found', 'Not found.', 404);
}

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url), open = url.pathname.startsWith('/api/public/'), cors = corsHeaders(env, req, open);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    try {
      const out = await route(env, req, url, ctx);
      if (out instanceof Response) return out;
      return json(out, 200, open ? { ...cors, 'Cache-Control': 'public, max-age=60' } : cors);
    } catch (err) {
      if (err instanceof HttpError) return json({ error: err.code, message: err.message }, err.status, cors);
      console.error(err && err.stack ? err.stack : err);
      return json({ error: 'server', message: 'Something went wrong on our side. Please try again.' }, 500, cors);
    }
  },
  // every ten minutes: settle invoices whose webhook never came (paid ones are switched on, unpaid ones closed), clear out what has
  // run out, and send a rebuild that was held back. Each step stands alone: one that fails does not stop the others.
  async scheduled(event, env) {
    const t = now(), step = async (name, run) => { try { await run(); } catch (err) { console.error('cron: ' + name + ' failed: ' + (err && err.message)); } };
    await step('orders', () => reconcileOrders(env));
    await step('sessions', () => db(env, 'DELETE FROM sessions WHERE expires_at < ?', t).run());
    await step('resets', () => db(env, 'DELETE FROM resets WHERE expires_at < ?', t).run());
    await step('rate', () => db(env, 'DELETE FROM rate WHERE reset_at < ?', t).run());
    await step('rebuild', async () => { if ((await db(env, "SELECT v FROM meta WHERE k = 'rebuild_wanted'").first('v')) === '1') await requestRebuild(env, true); });
  },
};
