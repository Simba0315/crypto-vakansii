/* Hiring Right Now — API. One file, no dependencies. Runs on Cloudflare Workers with a D1 database.

   What it does: accounts, self-serve purchases (featured / pinned jobs, company spotlight, page sponsorship, job packs, Plus),
   crypto checkout through Cryptomus, and automatic activation the moment a payment is confirmed. Nobody has to answer an email.

   Jobs posted here pass a set of fraud checks before anyone sees them: a work email that was confirmed, a link to apply on the
   account's own domain, a screen of the text (screenPosting), a person's look at the first jobs of every account (the review queue),
   and reports from job seekers. The rules are written above each part; the owner's side of it is in README.md.

   Bindings   DB (D1 database)
              MAIL           optional: anything with send({ from, to, subject, text }). Until it is bound no email leaves (see sendMail).
              DOMAINS        optional: anything with age(domain) -> days since the domain was registered (see domainAge). Not bound: not checked.
   Variables  SITE_URL       public address of the site, no trailing slash   (https://example.com)
              SITE_ORIGINS   origins allowed to call the API, comma separated  (https://example.com)
              API_URL        public address of this worker, no trailing slash
              GITHUB_REPO    owner/name of the site repository (optional, for instant rebuilds)
              PLUS_LIVE      "1" once Plus is on sale
              MAIL_FROM      optional: the sender address handed to MAIL
              PAY_MODE       "test" ONLY on a developer machine: orders are paid by opening a link, and a password reset or a sign-up
                             answers with its token instead of only mailing it. Never set it in production.
   Secrets    CRYPTOMUS_MERCHANT, CRYPTOMUS_API_KEY   payment gateway (merchant id and payment API key)
              ADMIN_TOKEN                             owner-only endpoints (/api/admin/...). Not set: every one of them is refused.
              GITHUB_TOKEN                            optional: fine-grained token with Actions: write on GITHUB_REPO
   Cron       every ten minutes (wrangler.toml): asks the gateway about invoices whose webhook never came, opens the link to apply of a
              few live jobs again (each job once a day, see recheckLinks), tidies up, sends held-back rebuilds.
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
const CONFIRM_HOURS = 24;                 // how long the link that confirms an email works
const TRUST_JOBS = 2, TRUST_DAYS = 14;    // an account is trusted after this many jobs a person approved and this many days (see trusted)
const NEW_JOBS_PER_DAY = 1, NEW_LIVE_JOBS = 3;      // what an account may do until then: new jobs a day, jobs on the site or waiting at a time
const POSTS_PER_HOUR = 60;                // attempts to post, whatever comes of them
const DUPLICATE_DAYS = 30;                // a removed job blocks the same title and company from the same account this long
const RECHECK_BATCH = 4;                  // live jobs whose link is opened again in one cron run (each takes up to LINK_HOPS + 1 requests)
const REPORTS_PER_HOUR = 5;               // reports one address may send
const YOUNG_DOMAIN_DAYS = 30;             // a domain registered more recently than this sends a job to review, when its age can be known

class HttpError extends Error {
  constructor(status, code, message, extra) { super(message); this.status = status; this.code = code; this.extra = extra; }
}
const bad = (code, message, status = 400, extra) => new HttpError(status, code, message, extra);

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
/* The registrable domain: the part of a host name that has one owner, "jobs.acme.co.uk" -> "acme.co.uk". It is what an account is tied
   to (users.domain, from its email) and what the company site and the link to apply are compared with.
   A deliberate simplification: there is no public-suffix list here. It is the last two labels, or the last three when the last two are
   one of PUBLIC_SECONDS (add a line there when a country zone is missing), any other country zone with a generic second level
   (org.uk, com.cn ...: kept from the first version of the link check, which was stricter than the list alone), or a host where anyone
   can get a subdomain. Where it errs, it errs towards the longer name, so two owners are never taken for one. */
const PUBLIC_SECONDS = new Set('co.uk com.au co.jp com.br co.in com.sg co.nz com.mx co.za com.tr co.kr com.hk com.tw com.ar com.co com.pl com.ua'.split(' '));
const GENERIC_SECOND = /^(co|com|org|net|gov|edu|ac)\.[a-z]{2}$/;
const SHARED_HOSTS = /^(github\.io|gitlab\.io|pages\.dev|workers\.dev|vercel\.app|netlify\.app|web\.app|firebaseapp\.com|herokuapp\.com|onrender\.com|webflow\.io|wixsite\.com|wordpress\.com|blogspot\.com|framer\.website|framer\.app|carrd\.co|substack\.com|azurewebsites\.net|cloudfront\.net)$/;
export const siteDomain = (host) => {
  const parts = String(host || '').toLowerCase().replace(/^www\./, '').split('.'), two = parts.slice(-2).join('.');
  return parts.slice(parts.length > 2 && (PUBLIC_SECONDS.has(two) || GENERIC_SECOND.test(two) || SHARED_HOSTS.test(two)) ? -3 : -2).join('.');
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
/* What is kept of a job seeker's address: a hash of it with a salt that exists only in this database (made on first use by a single
   statement, so two requests cannot make two salts). Enough to count one address once and to limit it; not enough to say whose it was. */
async function ipHash(env, req) {
  const salt = await db(env, "INSERT INTO meta (k, v) VALUES ('ip_salt', ?) ON CONFLICT(k) DO UPDATE SET v = meta.v RETURNING v", rid('', 16)).first('v');
  return (await sha256(salt + ':' + clientIp(req))).slice(0, 32);
}
/* The counters behind /api/public/transparency.json: one row per month and name, raised by a single statement. */
const monthOf = (ts) => new Date(ts * 1000).toISOString().slice(0, 7);
const bump = (env, k, t = now()) => db(env, 'INSERT INTO stats (month, k, n) VALUES (?, ?, 1) ON CONFLICT(month, k) DO UPDATE SET n = n + 1', monthOf(t), k);
const clip = (s, max) => (s.length > max ? s.slice(0, max - 1) + '…' : s);

/* ---------------------------------------------------------------- who is posting: work email, hiring systems, look-alike names */
/* A mailbox anyone can open in a minute says nothing about who the employer is. Checked against the registrable domain of the address:
   the NAMES lists match under every ending (yahoo.com, yahoo.co.uk ...), the DOMAINS lists only as written (proton.me is a free
   mailbox, proton.ch is the company).
   Two kinds of account follow from it. A person looking for work signs up with whatever mailbox they have (gmail and the like): that
   account can buy Plus and keep its saved jobs, and it can never post a job. An employer signs up with an address on the company's own
   domain, and only such an account can post. A throwaway mailbox gets no account at all. */
const THROWAWAY_NAMES = 'mailinator guerrillamail guerrillamailblock 10minutemail tempmail temp-mail tempmailo yopmail sharklasers trashmail getnada dispostable maildrop throwawaymail mailnesia fakeinbox mohmal moakt'.split(' ');
const THROWAWAY_DOMAINS = 'grr.la nada.email'.split(' ');
const FREE_MAIL_NAMES = new Set('gmail googlemail yahoo ymail rocketmail outlook hotmail live msn aol icloud protonmail gmx yandex zoho zohomail tutanota tuta tutamail fastmail'.split(' ').concat(THROWAWAY_NAMES));
const FREE_MAIL_DOMAINS = new Set('me.com mac.com proton.me pm.me mail.com email.com mail.ru bk.ru list.ru inbox.ru ya.ru hey.com qq.com foxmail.com 163.com 126.com yeah.net'.split(' ').concat(THROWAWAY_DOMAINS));
export const freeMail = (host) => { const d = siteDomain(host); return FREE_MAIL_NAMES.has(d.split('.')[0]) || FREE_MAIL_DOMAINS.has(d); };
export const throwawayMail = (host) => { const d = siteDomain(host); return THROWAWAY_NAMES.includes(d.split('.')[0]) || THROWAWAY_DOMAINS.includes(d); };
const WORK_EMAIL = 'Jobs can be posted only from an account whose email is on the company’s own domain (you@yourcompany.com). An account on a free mailbox such as gmail.com cannot post jobs. Sign up with your work address to post.';
const THROWAWAY = 'This address is a throwaway mailbox. Sign up with an address you keep: the confirmation link and your receipts go to it.';

/* Hiring systems: the only places a link to apply may be on when it is not on the account's own domain. These exact hosts and no
   others; a HIRING_TENANTS entry stands for "<employer>." in front of it (acme.recruitee.com, acme.jobs.personio.de). */
const HIRING_HOSTS = new Set(['boards.greenhouse.io', 'job-boards.greenhouse.io', 'job-boards.eu.greenhouse.io', 'jobs.lever.co', 'jobs.eu.lever.co', 'jobs.ashbyhq.com', 'apply.workable.com',
  'jobs.smartrecruiters.com', 'careers.smartrecruiters.com', 'wellfound.com', 'jobs.jobvite.com', 'ats.rippling.com']);
// Workday, iCIMS and Pinpoint are sold to companies under contract, so a tenant there is a real employer. Left out on purpose: hosts
// where anyone can publish a page in a minute (join.com, notion.site, forms, link shorteners).
const HIRING_TENANTS = ['recruitee.com', 'teamtailor.com', 'bamboohr.com', 'breezy.hr', 'personio.com', 'jobs.personio.de', 'myworkdayjobs.com', 'icims.com', 'pinpointhq.com'];
export const hiringSystem = (host) => { const h = String(host || '').toLowerCase().replace(/^www\./, ''); return HIRING_HOSTS.has(h) || HIRING_TENANTS.some((w) => h.endsWith('.' + w)); };

/* Names scammers borrow: well-known employers, each with the domains that really are its own. A host is a look-alike when
   - a label of it, written plainly (lower case, 0 -> o, 1 -> l, rn -> m, vv -> w, hyphens dropped), is such a name, on a domain that is
     not that employer's ("stripe.work", "coinbase.evil.com", "c0inbase.com");
   - a label is the name with a hiring word in front or behind ("coinbase-careers.com");
   - the label that was registered is one letter away from a name ("coinbasse.com");
   - any label is punycode (xn--), where letters of another alphabet cannot be told from Latin ones.
   A look-alike is not refused: every job of that account waits for a person, with the reason written on it.
   To extend: add `name: ['its-own-domain.com', ...]`, the name in lower case as it stands in the domain. To let a real namesake through
   (Circle the community platform at circle.so), add its domain to that name's list. An ordinary word that is one letter away from a
   name (beta, user, apply) goes into NEAR_WORDS. */
const BRANDS = { google: ['google.com', 'withgoogle.com'], microsoft: ['microsoft.com'], apple: ['apple.com'], amazon: ['amazon.com', 'amazon.jobs'], meta: ['meta.com', 'metacareers.com'],
  netflix: ['netflix.com'], stripe: ['stripe.com'], openai: ['openai.com'], anthropic: ['anthropic.com'], coinbase: ['coinbase.com'], binance: ['binance.com'], kraken: ['kraken.com'],
  okx: ['okx.com'], bybit: ['bybit.com'], ripple: ['ripple.com'], circle: ['circle.com'], consensys: ['consensys.io', 'consensys.com', 'consensys.net'], chainalysis: ['chainalysis.com'],
  uniswap: ['uniswap.org'], solana: ['solana.com', 'solana.org'], ethereum: ['ethereum.org'], polygon: ['polygon.technology'], databricks: ['databricks.com'], snowflake: ['snowflake.com'],
  cloudflare: ['cloudflare.com'], nvidia: ['nvidia.com'], tesla: ['tesla.com'], spacex: ['spacex.com'], airbnb: ['airbnb.com'], uber: ['uber.com'], shopify: ['shopify.com'],
  atlassian: ['atlassian.com'], gitlab: ['gitlab.com'], github: ['github.com'], figma: ['figma.com'], notion: ['notion.so', 'notion.com', 'makenotion.com'], linear: ['linear.app'],
  vercel: ['vercel.com'], datadog: ['datadoghq.com', 'datadog.com'] };
const HIRING_WORDS = ['careers', 'jobs', 'hr', 'hiring', 'talent', 'recruit', 'recruiting'];
const COMPANY_WORDS = ['inc', 'llc', 'ltd', 'corp', 'labs', 'global', 'group', 'exchange', 'foundation', 'technologies', 'hq', 'official', ...HIRING_WORDS];
const NEAR_WORDS = new Set('beta mega metal mesa user tuber apply ample sigma motion nation potion lotion liner finance strip stripes strike circles goggle solano'.split(' '));
const plain = (label) => String(label).toLowerCase().replace(/-/g, '').replace(/0/g, 'o').replace(/1/g, 'l').replace(/rn/g, 'm').replace(/vv/g, 'w');
const oneAway = (a, b) => {                      // exactly one letter changed, added or dropped
  if (a === b || Math.abs(a.length - b.length) > 1) return false;
  let i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++;
  return a.length === b.length ? a.slice(i + 1) === b.slice(i + 1) : a.length > b.length ? a.slice(i + 1) === b.slice(i) : a.slice(i) === b.slice(i + 1);
};
const BRAND_LIST = Object.keys(BRANDS).map((name) => ({ name, flat: plain(name), shown: name[0].toUpperCase() + name.slice(1), own: BRANDS[name] }));
export function lookalike(host) {                // why this host looks like somebody else's, or ''
  const h = String(host || '').toLowerCase().replace(/\.$/, ''), domain = siteDomain(h);
  if (BRAND_LIST.some((b) => b.own.includes(domain))) return '';
  const labels = h.split('.').slice(0, 1 - domain.split('.').length || undefined), registered = domain.split('.')[0];      // every label but the ending
  for (const label of labels) {
    if (label.startsWith('xn--')) return domain + ' is written in punycode (xn--), where look-alike letters cannot be told apart';
    const flat = plain(label);
    for (const b of BRAND_LIST) {
      if (flat === b.flat) return label === b.name ? domain + ' carries the name of ' + b.shown + ' but is not one of its domains' : '"' + label + '" in ' + domain + ' reads like ' + b.shown;
      if (HIRING_WORDS.some((w) => flat === b.flat + w || flat === w + b.flat)) return '"' + label + '" in ' + domain + ' is the name of ' + b.shown + ' with a hiring word added';
      if (label === registered && !NEAR_WORDS.has(label) && oneAway(flat, b.flat)) return '"' + label + '" in ' + domain + ' is one letter away from ' + b.shown;
    }
  }
  return '';
}
/* The well-known employer a company name claims to be ("Coinbase", "COINBASE Inc.", "Binance Careers"), or ''. Posting under such a name
   from a domain that is not that employer's is the plainest impersonation there is; it waits for a person too. */
export function brandIn(company) {
  const flat = plain(String(company || '').normalize('NFKC').replace(/[^\p{L}\p{N}]+/gu, ''));
  const b = BRAND_LIST.find((x) => flat === x.flat || COMPANY_WORDS.some((w) => flat === x.flat + w));
  return b ? b.name : '';
}
/* How many days ago a domain was registered: a scam site is usually days old. Finding out takes a WHOIS or RDAP lookup, which this
   worker does not make by itself (no key for one, and a small budget of outgoing requests). Bind DOMAINS to anything with age(domain)
   and jobs from a domain younger than YOUNG_DOMAIN_DAYS wait for a person. With nothing bound the answer is null: nothing is assumed. */
export async function domainAge(env, domain) {
  if (!env.DOMAINS || typeof env.DOMAINS.age !== 'function') return null;
  try { const days = Number(await env.DOMAINS.age(domain)); return Number.isFinite(days) && days >= 0 ? days : null; } catch { return null; }
}
/* Trust is earned, not claimed: a person approved TRUST_JOBS jobs of the account, it is TRUST_DAYS old, and no report about it was
   upheld. Until then every job waits for a person and the account's limits are the small ones (NEW_JOBS_PER_DAY, NEW_LIVE_JOBS). */
const trusted = (u, t) => u.approved_jobs >= TRUST_JOBS && u.created_at <= t - TRUST_DAYS * DAY && !u.upheld_reports;
// the company domain of an account; empty for a job seeker's account on a free mailbox, which cannot post
const domainOf = (u) => { if (u.domain) return u.domain; const host = u.email.slice(u.email.lastIndexOf('@') + 1); return freeMail(host) ? '' : siteDomain(host); };

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
  return { id: u.id, email: u.email, company: u.company, plus: u.plus_until > t, plus_until: u.plus_until > t ? isoDay(u.plus_until) : '', credits: Number(credits) || 0,
    domain: domainOf(u), confirmed: u.confirmed_at > 0, trusted: trusted(u, t) };
}
/* The browser a sign-in comes from, as far as it shows: a hash of the account and the User-Agent with the version numbers taken out, so
   an update of the same browser is still the same device. The row is written by one statement that also says whether it was new. */
async function knownDevice(env, req, userId) {
  const ua = (req.headers.get('User-Agent') || '').slice(0, 400).replace(/[\d._]+/g, '');
  const made = await db(env, 'INSERT INTO devices (user_id, ua_hash, first_seen) VALUES (?, ?, ?) ON CONFLICT(user_id, ua_hash) DO NOTHING', userId, (await sha256('ua:' + userId + ':' + ua)).slice(0, 32), now()).run();
  return !made.meta.changes;
}
const later = (ctx, work) => (ctx && typeof ctx.waitUntil === 'function' ? ctx.waitUntil(work) : work);      // the answer does not wait for the mail service

/* Sign-up ties an account on a work email to the registrable domain of that address: users.domain is what the company site and the
   link to apply of every job must be on. An account on a free mailbox (see freeMail) has no domain: it is a job seeker's account and
   readJob refuses to post from it. A throwaway mailbox is refused here. The account starts unconfirmed: it can sign in and fill in a job
   (POST /api/jobs/preview checks it and saves nothing), but it cannot publish a job or buy anything for an employer until the
   address is confirmed (confirmEmail). */
async function signup(env, req, ctx) {
  await limit(env, 'signup:' + clientIp(req), 5, 3600);
  const b = await body(req), email = cleanEmail(b.email), password = typeof b.password === 'string' ? b.password : '', company = line(b.company, 80) || '';
  if (!email) throw bad('email', 'Enter a valid email address.');
  const host = email.slice(email.lastIndexOf('@') + 1);
  if (throwawayMail(host)) throw bad('throwaway_email', THROWAWAY);
  const personal = freeMail(host);
  if (password.length < 8 || password.length > 200) throw bad('password', 'The password must be at least 8 characters long.');
  const exists = bad('exists', 'An account with this email already exists. Sign in instead.', 409);
  if (await db(env, 'SELECT 1 AS x FROM users WHERE email = ?', email).first()) throw exists;
  // the name on an account is only a label (a name is taken by posting a checked job, see claimCompany), but it may not be one another account holds
  if (company && !personal && await db(env, 'SELECT 1 AS x FROM companies WHERE k = ?', companyKey(company)).first()) throw bad('company_taken', COMPANY_TAKEN, 409);
  const id = rid('u_'), p = await hashPassword(password), t = now(), confirm = rid('', 32);
  try {
    await env.DB.batch([
      db(env, 'INSERT INTO users (id, email, domain, pass_hash, pass_salt, company, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)', id, email, personal ? '' : siteDomain(host), p.hash, p.salt, personal ? '' : company, t),
      db(env, 'INSERT INTO confirms (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)', await sha256(confirm), id, t, t + CONFIRM_HOURS * 3600),
    ]);
  } catch (err) { if (/UNIQUE/i.test(String(err && err.message))) throw exists; throw err; }      // the same email signing up twice at the same moment
  await knownDevice(env, req, id);                    // the browser that made the account is not a new device later
  await later(ctx, sendMail(env, email, 'Confirm your email', confirmText(env, confirm)));
  const user = await db(env, 'SELECT * FROM users WHERE id = ?', id).first(), out = { token: await openSession(env, id), user: await userView(env, user) };
  if (env.PAY_MODE === 'test') out.confirm_token = confirm;      // developer machines only: there is no mailbox to read the link from
  return out;
}
/* Signing in. From a browser this account has not been used in before, the owner of the address is told: a stolen password is then
   noticed the day it is used. The notice says when and nothing else: no token, no password, no link that signs anyone in. */
async function login(env, req, ctx) {
  const b = await body(req), email = cleanEmail(b.email) || '';
  await limit(env, 'login:' + clientIp(req) + ':' + email, 10, 600);
  const user = email ? await db(env, 'SELECT * FROM users WHERE email = ?', email).first() : null;
  const p = await hashPassword(typeof b.password === 'string' ? b.password : '', user ? user.pass_salt : '00'.repeat(16));
  if (!user || user.banned || !sameText(p.hash, user.pass_hash)) throw bad('credentials', 'Wrong email or password.', 401);
  if (!(await knownDevice(env, req, user.id))) {
    await later(ctx, sendMail(env, user.email, 'A new sign-in to your employer account', 'Your employer account at ' + env.SITE_URL + ' was just signed in to from a browser it has not been used in before (' +
      new Date().toISOString().slice(0, 16).replace('T', ' ') + ' UTC).\n\nIf that was you, there is nothing to do.\n\nIf it was not, open ' + env.SITE_URL + '/account/ and choose "Forgot password" to set a new one: ' +
      'that signs out every browser.\n'));
  }
  return { token: await openSession(env, user.id), user: await userView(env, user) };
}
async function logout(env, req) {
  const m = /^Bearer ([a-f0-9]{64})$/.exec(req.headers.get('Authorization') || '');
  if (m) await db(env, 'DELETE FROM sessions WHERE token_hash = ?', await sha256(m[1])).run();
  return { ok: true };
}

/* The one place mail leaves from. No mail service is connected yet: bind MAIL to anything with send({ from, to, subject, text })
   (a service binding to a mail worker, for example) and the links that confirm an email, password resets and notices of a new sign-in
   start arriving. Until then nothing is sent and it says so. The text is never logged: it may carry a link that opens an account. */
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
/* Confirming the email of an account: the same shape as the password reset. Sign-up stores the hash of a random token and mails the
   link; the link works once and for CONFIRM_HOURS. Until it is used the account cannot publish a job or buy a placement. */
const CONFIRM_FIRST = 'Confirm your email first: open the link we sent to your address, or ask for a new one on the account page.';
const confirmText = (env, token) => 'Thank you for opening an employer account at ' + env.SITE_URL + '.\n\nOpen this link within ' + CONFIRM_HOURS + ' hours to confirm your email:\n' +
  env.SITE_URL + '/account/#confirm=' + token + '\n\nUntil then you can sign in and prepare a job, but not publish it.\n\nIf you did not open an account, ignore this message.\n';
async function confirmRequest(env, user, ctx) {      // a new link for the account that is signed in
  if (user.confirmed_at) return { ok: true, confirmed: true };
  await limit(env, 'confirm:' + user.id, 3, 3600);
  const token = rid('', 32), t = now();
  await db(env, 'INSERT INTO confirms (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)', await sha256(token), user.id, t, t + CONFIRM_HOURS * 3600).run();
  await later(ctx, sendMail(env, user.email, 'Confirm your email', confirmText(env, token)));
  const out = { ok: true, confirmed: false, message: 'A link to confirm your email is on its way. It works for ' + CONFIRM_HOURS + ' hours.' };
  if (env.PAY_MODE === 'test') out.token = token;      // developer machines only
  return out;
}
/* The link is the proof, so no session is needed: it may be opened in another browser than the one that signed up. One batch, as in
   resetConfirm: the token cannot be used twice, and using it ends every other link of that account. */
async function confirmEmail(env, req) {
  await limit(env, 'confirm-try:' + clientIp(req), 10, 600);
  const b = await body(req), token = typeof b.token === 'string' && /^[a-f0-9]{64}$/.test(b.token) ? b.token : '';
  const t = now(), hash = token ? await sha256(token) : '', stale = bad('confirm', 'This link does not work any more. Sign in and ask for a new one.');
  const live = 'SELECT c.user_id FROM confirms c JOIN users u ON u.id = c.user_id WHERE c.token_hash = ? AND c.expires_at > ? AND u.banned = 0';
  if (!hash) throw stale;
  const done = await env.DB.batch([
    db(env, 'UPDATE users SET confirmed_at = ? WHERE id = (' + live + ')', t, hash, t),
    db(env, 'DELETE FROM confirms WHERE user_id = (' + live + ')', hash, t),
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
    if (t.job_id) {         // a job waiting for review can be bought for too: what is bought is held until the job is approved (see activate)
      const j = await db(env, "SELECT id, title, company FROM jobs WHERE id = ? AND user_id = ? AND status IN ('live', 'review') AND expires_at > ?", String(t.job_id), user.id, now()).first();
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
  if (product.group === 'employer' && !user.confirmed_at) throw bad('confirm_email', CONFIRM_FIRST, 403);      // nothing is sold to an address nobody has confirmed
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
  // Buying again while it is running adds time instead of overlapping. Paying never skips review: for a job that is waiting for a person
  // the placement is written as held (held = 1, its time counted from zero instead of from now), in the same statement that looks at the
  // job, and its days start to run when the job is approved (see holdPlacements and releasePlacements).
  if (p.kind) steps.push(db(env,
    'INSERT INTO placements (id, order_id, user_id, kind, target, label, starts_at, ends_at, held) SELECT ?, id, user_id, ?, target, label, start, start + ?, held FROM (' +
    'SELECT x.id, x.user_id, x.target, x.label, x.held, MAX(CASE WHEN x.held = 1 THEN 0 ELSE ? END, COALESCE((SELECT MAX(p.ends_at) FROM placements p ' +
    'WHERE p.kind = ? AND p.target = x.target AND p.cancelled = 0 AND p.held = x.held AND (x.held = 1 OR p.ends_at > ?)), 0)) AS start FROM (' +
    "SELECT o.id, o.user_id, o.target, o.label, EXISTS (SELECT 1 FROM jobs j WHERE o.target = 'direct:' || j.id AND j.status = 'review') AS held " +
    'FROM orders o WHERE o.id = ? AND o.activation = ?) x)', rid('p_'), p.kind, p.days * DAY, t, p.kind, t, o.id, mark));
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

/* ---------------------------------------------------------------- the screen: what a posting says and where it sends people
   screenPosting is a pure function of the posting: no database, no network. It runs on every new job and on every edit.
   - Hard rejects: one is enough, and the employer is told which. They are things no real posting contains: a link to a chat, a form,
     a link shortener, a file host or a download; a fee asked of the candidate; moving money or parcels for somebody; asking for a seed
     phrase, a private key, an ID scan or bank and card details.
   - Signals add up: 60 or more is a reject, 25 to 59 sends the job to a person, less is fine. Besides the ones the owner listed there
     is one more, worth 40: a candidate fee that is named without being asked for (see FEE_NAMED).
   The patterns look for what is asked of the reader, not for a word: a wallet company may write about seed phrases, a payments company
   about processing fees, anyone may write "we will never ask you for money". So most of them need the request itself ("send us your
   ...", "a registration fee of $49", "you will be paid via ..."), and a sentence that refuses or promises to pay ("we never ask ...",
   "no application fee", "we cover visa fees") is let through. That leaves room for a careful liar; the review queue is for him. */
const BAD_LINKS = [                                 // [what it is, host and everything under it, start of the path when only part of the site]
  ['a chat app', 't.me'], ['a chat app', 'telegram.me'], ['a chat app', 'wa.me'], ['a chat app', 'whatsapp.com'], ['a chat app', 'discord.gg'], ['a chat app', 'discord.com', '/invite'],
  ['a chat app', 'discordapp.com', '/invite'],
  ['a form builder', 'forms.gle'], ['a form builder', 'docs.google.com', '/forms'], ['a form builder', 'typeform.com'], ['a form builder', 'tally.so'], ['a form builder', 'jotform.com'],
  ['a link shortener', 'bit.ly'], ['a link shortener', 'tinyurl.com'], ['a link shortener', 'cutt.ly'], ['a link shortener', 'rb.gy'], ['a link shortener', 't.co'], ['a link shortener', 'is.gd'],
  ['a file host', 'drive.google.com'], ['a file host', 'dropbox.com'], ['a file host', 'mega.nz'], ['a file host', 'wetransfer.com'], ['a file host', 'mediafire.com'],
];
const DOWNLOADS = /\.(exe|msi|scr|bat|cmd|ps1|vbs|js|jar|dmg|pkg|apk|iso|zip|rar|7z|lnk)$/i;      // the end of the path: the query string is not part of it
const badLink = (u, ownDomain) => {                 // what kind of place a link leads to, or '' when there is nothing wrong with it
  const host = u.hostname.toLowerCase().replace(/^www\./, ''), path = u.pathname.toLowerCase();
  if (ownDomain && siteDomain(host) === ownDomain) return '';            // a file host may link to itself: it is the employer
  const hit = BAD_LINKS.find(([, h, p]) => (host === h || host.endsWith('.' + h)) && (!p || path.startsWith(p)));
  return hit ? hit[0] : '';
};
const linksIn = (text) => {                         // [address, written out in full or not]: "https://t.me/x" and a bare "t.me/x" alike
  const out = [];
  for (const m of text.matchAll(/\bhttps?:\/\/[^\s<>"'`]+|\b(?:[a-z0-9-]{1,63}\.){1,6}[a-z]{2,24}\/[^\s<>"'`]+/gi)) {      // bounded, so a text made of dots costs nothing
    const raw = m[0].replace(/[).,;:!?\]]+$/, ''), full = /^https?:/i.test(raw);
    try { out.push([new URL(full ? raw : 'https://' + raw), full]); } catch {}
  }
  return out;
};

const MONEY = '(?:[$€£]\\s?\\d|\\d[\\d,.]*\\s?(?:usd|usdt|usdc|eur|euros?|dollars|bucks)\\b)';
const FEE = '(?:registration|application|training|onboarding|processing|equipment|starter[\\s-]?kit|background[\\s-]?check|visa)\\s+(?:fee|deposit|payment)s?\\b';
const FEES = [                                      // a fee asked of the candidate
  new RegExp('\\b' + FEE + '(?=\\s*(?:of|is|are|was|:|-|–|=|\\()?\\s*(?:only\\s+|just\\s+)?' + MONEY + ')', 'gi'),                                    // "registration fee of $49"
  new RegExp(MONEY + '[\\d,.]*\\s*(?:usd|usdt|usdc|dollars)?\\s+(?:one[- ]time\\s+|refundable\\s+)?' + FEE, 'gi'),                                    // "a $49 registration fee"
  new RegExp('\\b(?:refundable|non-?refundable|one[- ]time|upfront|up-front|small|mandatory|compulsory|required)\\s+(?:[\\w-]+\\s+)?' + FEE, 'gi'),     // "a refundable equipment deposit"
  new RegExp('\\b(?:you|candidates?|applicants?|trainees?|new\\s+hires?|workers?|members?)\\s+(?:[\\w\'’-]+\\s+){0,5}?(?:pay|cover|purchase|buy|send|deposit|transfer|bear)\\s+(?:[\\w\'’$-]+\\s+){0,4}?' + FEE, 'gi'),
  new RegExp('\\b' + FEE + '\\s+(?:is|are|must\\s+be|has\\s+to\\s+be|should\\s+be|will\\s+be|to\\s+be)\\s+(?:required|payable|paid|deducted|due|sent|transferred|needed)\\b', 'gi'),
  /\b(?<!direct\s)(?:deposit|top[\s-]?up|recharge)\b[^.!?\n]{0,60}?\bto\s+(?:unlock|activate|withdraw|start|release)\b/gi,                           // "top up your balance to unlock ..."
  /\b(?:you|candidates?|applicants?|members?)\s+(?:[\w'’-]+\s+){0,4}?pay\b[^.!?\n]{0,60}?\bto\s+(?:unlock|activate|withdraw|start)\b/gi,
  new RegExp('\\bpay\\s+(?:(?:a|an|the|only|just|your|small|one[- ]time|refundable)\\s+)*(?:' + MONEY + '|fee\\b|deposit\\b)[^.!?\\n]{0,60}?\\bto\\s+(?:unlock|activate|withdraw|start)\\b', 'gi'),
];
// A fee of that kind named without the request around it ("a registration fee applies"): not enough to refuse, enough for a person to look.
// "processing" and "payment" are left out here: "processing fees" and "Visa payments" are what payment companies write about themselves.
const FEE_NAMED = [/\b(?:registration|application|training|onboarding|equipment|starter[\s-]?kit|background[\s-]?check|visa)\s+(?:fee|deposit)s?\b/gi];
const RAILS = '(?:gift\\s?cards?|western\\s+union|zelle|cash\\s?app|money\\s+orders?|moneygram)\\b';
const THINGS = '(?:parcels?|packages?|items|goods|shipments?|orders|products|merchandise|electronics)';
const MOVES = [                                     // money or parcels moved for somebody, pay by a route no employer uses
  new RegExp('\\b(?:you(?:[\'’]ll|\\s+will|\\s+are|\\s+get)?\\s+(?:be\\s+|get\\s+)?paid|your\\s+(?:pay|payments?|salary|wages?|earnings|commission|funds)|(?:weekly|daily|instant|same[- ]day)\\s+(?:pay|payments?|payouts?)|' +
    '(?:pay|payments?|payouts?|salary|wages?)\\s+(?:is|are|will\\s+be|sent|made|issued))\\b[^.!?\\n]{0,50}?\\b' + RAILS, 'gi'),
  new RegExp('\\b(?:paid|pay|payments?|payouts?)\\s+(?:is\\s+|are\\s+)?(?:via|by|through|thru|in)\\s+(?:[\\w\'’-]+\\s+){0,2}?' + RAILS, 'gi'),
  /\b(?:buy|purchase|pick\s+up|get)\b[^.!?\n]{0,30}?\bgift\s?cards?\b[^.!?\n]{0,60}?\b(?:send|share|scratch|text|email|give|provide|forward)\b[^.!?\n]{0,30}?\b(?:codes?|pins?|numbers?|photos?|pictures?|them|us|me)\b/gi,
  /\b(?:we|i|the\s+company|our\s+(?:client|accountant|finance\s+team|accounting\s+team))\s+(?:will\s+|shall\s+|would\s+|can\s+)?(?:send|mail|issue|post|email)\s+you\s+(?:[\w'’-]+\s+){0,3}?che(?:ck|que)s?\b(?![\s-]?(?:in|ins|list|up|out)\b)/gi,
  /\bche(?:ck|que)s?\s+(?:will\s+be\s+|is\s+|are\s+|gets\s+)?(?:mailed|sent|issued|emailed)\s+to\s+you\b/gi,
  /\b(?:deposit|cash)\s+(?:(?:the|this|these|a|our|client|each)\s+)*che(?:ck|que)s?\b[^.!?\n]{0,40}?\byour\b/gi,
  /\bche(?:ck|que)s?\b[^.!?\n]{0,60}?\b(?:deposit|cash)\s+(?:it|them)\b/gi,
  new RegExp('\\bre-?ship\\w*\\b[^.!?\\n]{0,40}?\\b(?:' + THINGS + '|them)\\b|\\b' + THINGS + '\\b[^.!?\\n]{0,40}?\\bre-?ship\\w*\\b|\\bre-?shipping\\s+(?:agent|coordinator|assistant|clerk|specialist|manager)\\b', 'gi'),
  /\bre-?pack(?:ag)?\w*\s+(?:[\w'’-]+\s+){0,3}?(?:parcels?|items|goods|shipments?|orders|products|merchandise|electronics)\b/gi,
  /\bforward(?:ing|s|ed)?\s+(?:(?:the|these|those|all|any|received|incoming|client|customer|our|their)\s+){0,3}(?:parcels?|packages?|funds|money|shipments?)\b/gi,
  /\bforward(?:ing|s|ed)?\s+(?:(?:the|these|those|all|any|received|incoming|client|customer|our|their)\s+){1,3}payments?\b/gi,
  /\b(?:receive|accept|collect)\s+(?:and\s+\w+\s+)?(?:parcels?|packages?|shipments?)\s+(?:at|to|in)\s+(?:your\s+)?(?:home|house|address|residence)\b/gi,
  /\b(?:receive|accept|process)\b[^.!?\n]{0,30}?\b(?:payments?|funds|transfers?|money)\b[^.!?\n]{0,30}?\b(?:in|into|to|on|through|using|via)\s+your\s+(?:(?:own|personal|private)\s+)*(?:bank\s+)?(?:account|card|paypal|wallet)\b/gi,
];
const KEYS = '(?:seed\\s+phrases?|recovery\\s+phrases?|secret\\s+phrases?|mnemonic(?:\\s+phrases?)?|private\\s+keys?)';
const PAPERS = '(?:ssn|social\\s+security(?:\\s+number)?|passport\\s+(?:scan|copy|photo)|(?:scan|copy|photo)\\s+of\\s+(?:your\\s+)?passport|bank\\s+(?:log-?in|details|credentials|account\\s+(?:number|details|log-?in))|' +
  '(?:credit\\s+|debit\\s+)?card\\s+(?:number|details)|cvv|cvc)';
// a word that may stand between "your" and the secret ("your full name, address, SSN"): not the start of "your experience with ..." or "your work on ..."
const LISTED = '(?:(?!(?:of|on|about|in|with|for|to|into|around|regarding|over|at|experience|knowledge|expertise|thoughts|ideas|passion|work|background|understanding|opinion|research|approach|skills|love|interest|' +
  'views|insights|code|design|review|team)\\b)(?![\\w\'’-]*ing\\b)[\\w\'’-]+,?\\s+(?:and\\s+|or\\s+)?)';
const SECRETS = [                                   // something no employer needs from a candidate
  new RegExp('\\b(?:send|share|provide|enter|submit|give|upload|email|type|input|confirm|verify|tell)\\b[^.!?\\n]{0,25}?\\b(?:your|ur)\\s+' + LISTED + '{0,8}?(?:' + KEYS + '|' + PAPERS + ')\\b', 'gi'),
  new RegExp('(?<!\\b(?:users?|customers?|clients?|they|people|merchants?|members?|who|that)\\s+(?:can\\s+|could\\s+|may\\s+|must\\s+|will\\s+|to\\s+)?)\\b(?:send|submit|provide|upload|email)\\s+' +
    '(?:(?:us|me|a|an|the|clear|valid|copy\\s+of|scan\\s+of)\\s+){0,4}' + PAPERS + '\\b(?!\\s+(?:management|storage|security|handling|tokeni[sz]ation|vault|encryption|verification|validation|scanning|ocr|flows?|systems?|features?))', 'gi'),
  /\bconnect(?:ing)?\s+(?:your|ur)\s+(?:[\w'’-]+\s+)?wallet\b/gi,
];
/* "We will never ask you to send ...", "no application fee", "we cover visa fees": the words are there and the request is not. */
const REFUSED = /^[\s\S]*(?:\b(?:never|not|cannot|without|nobody|no\s+one)|n['’]t)\s+(?:(?:ever|be|have\s+to|need\s+to|going\s+to)\s+)*(?:ask|request|requir|need|charg|shar|send|giv|provid|enter|pay|disclos|reveal|submit|connect|deposit|buy|purchas|collect|tak|demand|expect|forward|transfer|wir|install|download|cash|reship|repack)\w*\b([^.!?\n;,]*)$/i;
const NONE_OF = /\b(?:no|without(?:\s+any)?|free\s+of(?:\s+any)?|zero)\s+(?:[\w-]+\s+){0,2}$/i;
const WE_PAY = /^[\s\S]*\b(?:we|company|employer)\s+(?:(?:will|also|fully|can|do)\s+)*(?:(?:cover|reimburse|sponsor|take\s+care\s+of)\w*\b|pay\s+(?:for\s+)?(?=(?:[\w'’-]+\s+){0,2}$))([^.!?\n;]*)$/i;      // "we cover a, b and the visa fee", "we pay your visa fee"
const PAID_FOR = /\b(?:covered|waived|on\s+us|at\s+our\s+(?:cost|expense)|paid\s+(?:for\s+)?by\s+(?:us|the\s+company|the\s+employer|your\s+employer))\b/i;
const near = (found, words) => !!found && found[1].trim().split(/\s+/).length <= words && !/\b(?:but|just|only|simply|then|instead|however)\b/i.test(found[1]);      // the refusal governs what follows it, not the rest of a long sentence
function asked(text, patterns, fee) {               // the first place one of the patterns is really asked of the reader, as written; '' when there is none
  for (const sentence of text.split(/(?<=[.!?])\s+|\n+/)) {
    for (const re of patterns) {
      for (const m of sentence.matchAll(re)) {
        const before = sentence.slice(0, m.index);
        if (near(REFUSED.exec(before + m[0].split(/\s+/)[0]), 12) || near(REFUSED.exec(m[0]), 12) || NONE_OF.test(before)) continue;      // refused before the request, or inside it
        if (fee && (near(WE_PAY.exec(before), 10) || PAID_FOR.test(sentence))) continue;
        return m[0].replace(/\s+/g, ' ').trim().slice(0, 80);
      }
    }
  }
  return '';
}

const APPS = '(?:telegram|whats\\s?app|signal|wechat|discord)';
const CHAT = new RegExp('\\b' + APPS + '\\b[^\\n]{0,30}?(?:(?<![\\w.@])@(?!everyone\\b|here\\b)[a-z0-9_]{4,}|\\+\\d[\\d\\s().-]{7,}\\d|\\(\\d{3}\\)\\s?\\d{3}[\\s.-]?\\d{4}|\\b\\d{3}[\\s.-]\\d{3}[\\s.-]\\d{4}\\b|\\b\\d{10,13}\\b)|' +
  '\\b(?:contact|message|text|dm|reach|write\\s+to|ping|add)\\s+(?:(?:us|me|hr|the\\s+\\w+|our\\s+\\w+)\\s+)?(?:directly\\s+)?(?:on|via|through|at|in)\\s+' + APPS + '\\b', 'i');
const TASK = /(?:\b(?:rate|review|subscribe\s+to)|(?:^|[,;:]\s*|\b(?:to|and|just|simply|will|must|should|only)\s+)like)(?:\s+(?:and|or|,)\s*(?:like|rate|review|subscribe\s+to|share|comment\s+on|follow))?\s+(?:(?:youtube|tiktok|instagram|short|online|amazon|google|mobile|the|our|some|a\s+few|\d+)\s+){0,2}(?:videos|products|apps|hotels|channels|merchants)\b/i;
const TASK_PAY = /\b(?:earn\w*|paid|pay|commission|per\s+(?:task|video|review|like|order)|tasks?|simple|easy|from\s+(?:your\s+)?(?:phone|home))\b|[$€£]\s?\d/i;
const EARN = /\b(?:earn|make|get\s+paid|income\s+of|profit\s+of)\b[^.!?\n]{0,25}?(?:[$€£]\s?\d[\d,.]*k?|\b\d[\d,.]*k?\s?(?:usd|usdt|usdc|dollars|bucks))(?:\s*(?:-|–|to)\s*[$€£]?\s?\d[\d,.]*k?)?\s*\+?\s*(?:\/\s?|per\s+|a\s+|an\s+|each\s+|every\s+)?(?:day|daily|week|weekly)\b/i;
const HURRY = /\bno\s+interviews?\b|\bwithout\s+(?:an?\s+|any\s+)?interviews?\b|\bstart\s+(?:work(?:ing)?\s+|earning\s+)?(?:today|immediately|right\s+away)\b|\b(?:immediate|instant)\s+start\b|\bguaranteed\s+(?:income|jobs?|earnings|salary|pay|payouts?|profits?)\b/i;
// "client" is also a customer: after download and install it is software unless a customer word follows; after run and clone only when software clearly follows or the phrase ends
const TOOL = '\\s+(?:and\\s+(?:run|install|open|launch|test)\\s+)?(?:the|our|this|a|an|my)\\s+(?:[\\w-]+\\s+){0,2}?(?:launcher|installer|meeting\\s+(?:app|software|tool)|repo(?:sitory)?\\b|package\\b(?!\\s+(?:manager|management|registry|delivery|design))|';
const INSTALL = new RegExp('\\b(?:download|install)' + TOOL + 'client\\b(?![-/])(?!\\s+(?:success|services?|relationships?|accounts?|meetings?|calls?|workshops?|onboarding|portfolio|base|work|projects?|engagements?|teams?|events?|training|support|data)\\b))|' +
  '\\b(?:run|clone)' + TOOL + 'client(?=\\s*(?:app|application|software|build)\\b|\\s*[.,;:!)]|\\s+(?:to|on|from|before|so)\\b|\\s*$))', 'i');
const JUNIOR = /\b(?:assistant|tester|data[\s-]?entry|moderator|intern(?:ship)?|junior)\b/i;
const FIGURE = /(?:[$]|\busd\s?)(\d[\d,]*(?:\.\d+)?)\s?(k|m)?\b|\b(\d[\d,]*(?:\.\d+)?)\s?(k|m)?\s?(?:usd|usdt|usdc|dollars)\b/gi;
const PER = /^\s*(?:(?:-|–|to)\s*[$]?\s?(\d[\d,]*(?:\.\d+)?)\s?(k|m)?\b)?\s*(?:usd)?\s*\+?\s*(?:(?:\/\s?|per\s+|an?\s+|each\s+)?(hr|hour|hourly|h)\b|(?:\/\s?|per\s+|an?\s+|each\s+)?(yr|year|yearly|annum|annually)\b|(?:\/\s?|per\s+|an?\s+|each\s+)?(day|daily|week|weekly|month|monthly|mo|task|project)\b)?/i;
function payOutlier(text, isPay) {                  // "$150 an hour" or more, "$400,000 a year" or more; isPay: every figure in the text is pay (the salary field)
  const amount = (n, unit) => Number(String(n).replace(/,/g, '')) * (/k/i.test(unit || '') ? 1e3 : /m/i.test(unit || '') ? 1e6 : 1);
  for (const m of text.matchAll(FIGURE)) {
    const after = PER.exec(text.slice(m.index + m[0].length, m.index + m[0].length + 40)) || [], top = Math.max(amount(m[1] || m[3], m[2] || m[4]), after[1] ? amount(after[1], after[2]) : 0);
    if (after[3] && top >= 150) return true;
    if (after[5] || after[3]) continue;
    if (top >= 400000 && (after[4] || isPay || /\b(?:salary|salaries|pay|paid|compensation|earn\w*|income|package|ote|base)\b[^.!?\n]{0,30}$/i.test(text.slice(0, m.index)))) return true;
  }
  return false;
}
const NAMED = /\b(?:[Hh]ere|[Ww]e|us|[Tt]eam|[Rr]ole|[Pp]osition|[Jj]obs?|[Cc]areers?|[Oo]pportunity|[Oo]pening|[Ww]ork|[Ww]orking)\s+at\s+([A-Z][\w&.'’-]*(?:\s+(?:[A-Z][\w&.'’-]*|&))*)|\b([A-Z][\w&.'’-]*(?:\s+(?:[A-Z][\w&.'’-]*|&))*)\s+is\s+(?:(?:now|currently|actively|urgently)\s+)?(?:hiring|recruiting|looking\s+for|seeking)\b/g;
const NO_NAME = new Set(('a an the this that it we our us you your who he she they everyone someone team company startup group department office studio lab labs engineering product design data marketing sales support ' +
  'security platform growth finance operations research technology technical enterprise solutions director manager senior staff principal lead head level series seed stage scale home remote web3 defi crypto ' +
  'here now today inc llc ltd gmbh corp co').split(' '));
/* The company the text says it is, when it clearly says so ("the team at X", "X is hiring") in its first 300 characters and X is not
   the company the job is posted for. It errs towards saying nothing: a name that shares a word with the company, is part of it or
   contains it ("Nu" and Nubank, "Bird Canada" and MessageBird), or is its initials (VGS), is the same company. */
function otherCompany(text, company) {
  const flat = (s) => String(s).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ''), words = (s) => String(s).toLowerCase().split(/[^\p{L}\p{N}]+/u).filter((w) => w.length > 1 && !NO_NAME.has(w));
  const mine = words(company), whole = flat(company), initials = String(company).split(/[^\p{L}\p{N}]+/u).map((w) => w[0] || '').join('').toLowerCase();
  for (const m of String(text).matchAll(NAMED)) {
    if (m.index >= 300) break;
    const name = (m[1] || m[2]).replace(/(?:['’]s)?[.'’-]*$/, ''), theirs = words(name), all = flat(name);
    if (!theirs.length || !whole || all === initials || whole.includes(all) || all.includes(whole)) continue;
    if (theirs.some((w) => w.length > 2 && whole.includes(w)) || mine.some((w) => w.length > 2 && all.includes(w))) continue;
    return name;
  }
  return '';
}
export function screenPosting({ title, description, company, applyUrl, accountDomain, salary }) {
  const head = String(title || ''), pay = String(salary || ''), text = [head, String(description || ''), pay].join('\n'), own = String(accountDomain || '').toLowerCase();
  let apply = null; try { apply = new URL(String(applyUrl || '')); } catch {}
  const links = [...(apply ? [[apply, true, 'The link to apply']] : []), ...linksIn(text).map(([u, full]) => [u, full, 'A link in the text'])], hard = [];
  const place = links.find(([u]) => badLink(u, own)), file = links.find(([u, full]) => full && DOWNLOADS.test(u.pathname));
  if (place) hard.push(place[2] + ' leads to ' + badLink(place[0], own) + ' (' + place[0].hostname + '). People apply on the company’s own site or its hiring system.');
  if (file) hard.push(file[2] + ' is a download (' + file[0].pathname.slice(file[0].pathname.lastIndexOf('.')) + '). A job posting has nothing to download or run.');
  const fee = asked(text, FEES, true), move = asked(text, MOVES), secret = asked(text, SECRETS);
  if (fee) hard.push('It asks candidates for money (“' + fee + '”). An employer pays people and never charges them.');
  if (move) hard.push('It has candidates move money or parcels for someone else, or pays them in a way no employer does (“' + move + '”).');
  if (secret) hard.push('It asks for something no employer needs from a candidate (“' + secret + '”).');
  if (hard.length) return { verdict: 'reject', score: 100, reasons: hard };

  const signals = [], add = (points, reason) => signals.push([points, reason]), named = asked(text, FEE_NAMED, true);
  if (named) add(40, 'It speaks of a fee or deposit of the kind that is asked of candidates (“' + named + '”).');
  if (CHAT.test(text)) add(40, 'It moves people to a chat app (a handle or a phone number for Telegram, WhatsApp, Signal, WeChat or Discord).');
  if ([...text.matchAll(/[a-z0-9._%+-]+@((?:[a-z0-9-]+\.)+[a-z]{2,})/gi)].some((m) => freeMail(m[1]))) add(40, 'The contact address is a free mailbox, not one on the company’s domain.');
  if (text.split(/(?<=[.!?])\s+|\n+/).some((s) => TASK.test(s) && TASK_PAY.test(s))) add(40, 'It reads like a “task” scheme (liking, rating or reviewing things for pay).');
  if (EARN.test(text)) add(30, 'It promises a sum of money per day or week.');
  if (HURRY.test(text)) add(30, 'It promises a job without an interview, an immediate start or a guaranteed income.');
  if (INSTALL.test(text)) add(40, 'It asks people to download, install or run software.');
  if (JUNIOR.test(head) && (payOutlier(String(description || ''), false) || payOutlier(pay, true))) add(30, 'The pay is far above anything such a role is paid.');
  const other = otherCompany(description, company);
  if (other) add(30, 'The text speaks of another company (' + other + ') than the one the job is posted for.');
  if (/\bkindly\b/i.test(text)) add(10, 'Wording: “kindly”.');
  if (/\burgent(?:ly)?\s+(?:hiring|requirement|recruitment|vacancy|opening)\b/i.test(text)) add(10, 'Wording: “urgent hiring”.');
  if (!/\p{Ll}/u.test(head) && (head.match(/\p{Lu}/gu) || []).length >= 8) add(10, 'The title is all in capitals.');
  if (/\p{Extended_Pictographic}/u.test(head.replace(/[©®™]/g, ''))) add(10, 'There is an emoji in the title.');
  const score = signals.reduce((sum, s) => sum + s[0], 0);
  return { verdict: score >= 60 ? 'reject' : score >= 25 ? 'review' : 'ok', score, reasons: signals.map((s) => s[1]) };
}

/* ---------------------------------------------------------------- jobs posted here */
const BLOCKED_HOSTS = /(^|\.)(bit\.ly|tinyurl\.com|t\.co|t\.me|telegram\.me|wa\.me|whatsapp\.com|forms\.gle|docs\.google\.com|linktr\.ee|discord\.gg|facebook\.com|instagram\.com)$/;
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
/* A posting is accepted only if its link opens a page of that job on the account's own domain or on a known hiring system.
   home is the registrable domain of the account's email (users.domain): the link is tied to the address the employer proved to own,
   not to a company site anyone could type in. What it checks:
   - the link and every redirect after it (LINK_HOPS at most, followed here one by one, never by fetch itself) must be an address publicUrl
     accepts: https, default port, no login, a public host name and not an IP address, localhost or a private zone; must not be a messenger,
     a form, a link shortener or a file host; and must be on home (see siteDomain) or on a hiring system (see hiringSystem);
   - the whole walk has LINK_TIMEOUT ms; the last answer must be 2xx and an HTML page; only its first LINK_BYTES are read;
   - on the company's own site that page must contain every word of the job title (the first eight words of three letters or more).
   What it cannot do from a Worker, so nobody expects it: see which address a host name resolves to (a Worker's requests do not reach
   private networks, that is the real barrier), and read the title on a hiring system, since most of them draw the page in the browser:
   there, a page that opens is accepted. A page that lists several jobs and happens to contain all the words also passes.
   The answer is { problem, host }. problem is '' when all is well. host is where the walk ended: the host of the page that opened, or
   of the address a redirect was refused for; '' when it is not known where the link leads now (it did not open, it timed out). The
   host is kept with the job (jobs.apply_host) and the daily recheck compares with it. */
async function checkApplyLink(apply, home, title) {
  const signal = AbortSignal.timeout(LINK_TIMEOUT);
  const refused = (u, hop) => {
    if (!u) return 'The link to apply redirects to an address we cannot open. It must stay on https and on a public site.';
    if ((BLOCKED_HOSTS.test(u.hostname) && siteDomain(u.hostname) !== home) || badLink(u, home)) return 'The link to apply must open the job on your own site or hiring system, not a messenger, form or link shortener.';
    if (!hiringSystem(u.hostname) && siteDomain(u.hostname) !== home) return 'The link to apply must ' + (hop ? 'stay' : 'be') + ' on your company site (' + home + ') or on a hiring system such as Greenhouse, Lever or Ashby.';
    return '';
  };
  let url = apply, text = '';
  try {
    for (let hop = 0; ; hop++) {
      const problem = refused(url, hop);
      if (problem) return { problem, host: url ? url.hostname : 'an address that cannot be opened' };
      const res = await fetch(url.href, { redirect: 'manual', headers: { 'User-Agent': 'Mozilla/5.0 (compatible; job-link-check)', Accept: 'text/html,application/xhtml+xml' }, signal });
      const next = res.status >= 300 && res.status < 400 ? res.headers.get('Location') : null;
      if (next) {
        try { if (res.body) await res.body.cancel(); } catch {}
        if (hop >= LINK_HOPS) return { problem: 'The link to apply redirects too many times. Give the address of the job page itself.', host: '' };
        url = publicUrl(new URL(next, url.href).href, 2000);
        continue;
      }
      if (!res.ok) return { problem: 'The link to apply does not open (the page answered ' + res.status + ').', host: '' };
      if (!/^\s*(text\/html|application\/xhtml\+xml)\s*(;|$)/i.test(res.headers.get('Content-Type') || '')) return { problem: 'The link to apply must open a web page, not a file or a download.', host: '' };
      text = (await readStart(res, LINK_BYTES)).toLowerCase();
      break;
    }
  } catch { return { problem: 'The link to apply did not open. Check the address and try again.', host: '' }; }
  const host = url.hostname;
  if (hiringSystem(host)) return { problem: '', host };
  const words = [...new Set(title.toLowerCase().match(/[\p{L}\p{N}+#]{3,}/gu) || [])].slice(0, 8);
  return { problem: words.length && words.every((w) => text.includes(w)) ? '' : 'We could not find this job at the link. It must open the page of this exact job, with the same title.', host };
}
/* One company name, one account. A name is taken by the first account that posts a checked job under it (a job a person then turns
   down gives the name back, see the reject endpoint); signing up with a name takes nothing. Names are compared by companyKey, both the
   name as first written and the key are kept, and later jobs of the same account are stored under the name as first written, so the
   site sees one company, not one per spelling. */
const COMPANY_TAKEN = 'Another account already posts jobs under this company name. Sign in to that account, or use the exact name of your own company.';
async function claimCompany(env, user, name, key) {
  await db(env, 'INSERT INTO companies (k, name, user_id, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(k) DO NOTHING', key, name, user.id, now()).run();
  const held = await db(env, 'SELECT name, user_id FROM companies WHERE k = ?', key).first();
  if (!held || held.user_id !== user.id) throw bad('company_taken', COMPANY_TAKEN, 409);     // two accounts at the same moment: the insert let only one in
  return held.name;
}
/* The same job twice: the same account, the same company and the same title (compared without case and punctuation), while the first
   one is on the site, waiting for review or closed but not run out, or was removed in the last DUPLICATE_DAYS days. A job a person
   turned down does not count: its corrected version may be posted. */
const titleKey = (title) => companyKey(title).replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const jobSlug = (title, company) => slugify(title) + '-' + slugify(company);
const DUPLICATE = "d.user_id = ? AND d.company_key = ? AND d.title_key = ? AND d.id != ? AND ((d.status IN ('live', 'review', 'closed') AND d.expires_at > ?) OR (d.status = 'removed' AND d.ended_at > ?))";
const duplicateOf = (userId, j, selfId, t) => [userId, j.company_key, j.title_key, selfId, t, t - DUPLICATE_DAYS * DAY];
const SAME_JOB = 'You have already posted this job. Edit or renew that one instead of posting it again.';
const ROOM = "(SELECT COUNT(*) FROM jobs c WHERE c.user_id = ? AND c.status IN ('live', 'review') AND c.expires_at > ?) < ?";      // jobs on the site or waiting, against a cap
const NO_ROOM = 'A new account can have ' + NEW_LIVE_JOBS + ' jobs on the site at a time. Close one, or wait until the account is trusted: after ' + TRUST_JOBS + ' approved jobs and ' + TRUST_DAYS + ' days.';
/* Checks a job as sent, for a new one and for an edit alike, in this order: the fields; the company name (one account per name, not a
   company the site lists by itself); the company site, which must be on the account's domain; the screen of the text and the links
   (screenPosting, on every edit too); the link to apply, which must be on the account's domain or a hiring system; the same job posted
   twice; and then the link is opened (checkApplyLink). An edit may skip only that last step, and only when nothing the link check
   depends on (link, title, company, company site) has changed. dry: the preview of a draft, which opens nothing and counts nothing.
   It answers with the job as it will be stored and with reasons: why a person has to look at it before it is shown (none: it may go
   live at once). A reject by the screen never gets that far. */
async function readJob(env, user, b, existing, dry) {
  const domain = domainOf(user), company = line(b.company, 80, 2), title = line(b.title, 120, 4), apply = publicUrl(b.apply_url);
  if (!domain) throw bad('work_email', WORK_EMAIL, 403);
  const companyUrl = publicUrl(b.company_url == null || b.company_url === '' ? 'https://' + domain : b.company_url, 200);      // not given: the account's own domain
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
  if (siteDomain(companyUrl.hostname) !== domain) throw bad('company_url', 'The company site must be on the domain of your account’s email (' + domain + ').', 422);
  const etype = ETYPES.includes(b.etype) ? b.etype : '', salary = line(b.salary, 60) || '', t = now();
  const j = { company: held ? held.name : company, company_key: key, company_url: companyUrl.origin, title, title_key: titleKey(title), apply_url: apply.href, apply_host: existing ? existing.apply_host : '',
    location: line(b.location, 120) || '', remote: b.remote ? 1 : 0, salary, etype, description, reasons: [] };
  const screen = screenPosting({ title, description, company, applyUrl: apply.href, accountDomain: domain, salary });
  if (!existing && !dry) await bump(env, 'screened', t).run();
  if (screen.verdict === 'reject') {
    if (!existing && !dry) await bump(env, 'screen_rejected', t).run();
    throw bad('rejected', 'This posting cannot be published. ' + screen.reasons.join(' '), 422, { reasons: screen.reasons });
  }
  if (!hiringSystem(apply.hostname) && siteDomain(apply.hostname) !== domain) throw bad('apply_url', 'The link to apply must be on your company site (' + domain + ') or on a hiring system such as Greenhouse, Lever or Ashby.', 422);
  if (await db(env, 'SELECT 1 AS x FROM jobs d WHERE ' + DUPLICATE, ...duplicateOf(user.id, j, existing ? existing.id : '', t)).first()) throw bad('duplicate', SAME_JOB, 409);
  if (!dry && (!existing || existing.apply_url !== apply.href || existing.title !== title || existing.company_key !== key || existing.company_url !== companyUrl.origin)) {
    await limit(env, 'linkcheck:' + user.id, LINK_CHECKS_PER_HOUR, 3600);      // each check makes this service open an address someone typed
    const link = await checkApplyLink(apply, domain, title);
    if (link.problem) throw bad('apply_url', link.problem, 422);
    j.apply_host = clip(link.host, 255);
  }
  // why a person has to look before it is shown
  if (screen.verdict === 'review') j.reasons.push(...screen.reasons);
  const odd = lookalike(domain) || (hiringSystem(apply.hostname) ? '' : lookalike(apply.hostname)) || lookalike(companyUrl.hostname), brand = brandIn(company);
  if (odd) j.reasons.push(odd);
  if (brand && !BRANDS[brand].includes(domain)) j.reasons.push('the company is named “' + company + '”, and the account is not on a domain of ' + brand[0].toUpperCase() + brand.slice(1));
  if (!trusted(user, t)) {
    j.reasons.push(user.upheld_reports ? 'a report about a job of this account was upheld' : 'the account is not trusted yet: its first jobs are looked at by a person');
    const ats = hiringSystem(apply.hostname) ? apply.hostname : hiringSystem(j.apply_host) ? j.apply_host : '';
    if (ats) j.reasons.push('the link to apply is on a hiring system (' + ats + '), which cannot be tied to ' + domain);
  }
  const age = dry ? null : await domainAge(env, domain);
  if (age !== null && age < YOUNG_DOMAIN_DAYS) j.reasons.push(domain + ' was registered ' + Math.floor(age) + ' days ago');
  return j;
}
const jobView = (j, t) => ({ id: j.id, company: j.company, company_url: j.company_url, title: j.title, apply_url: j.apply_url, location: j.location, remote: !!j.remote, salary: j.salary, etype: j.etype,
  description: j.description, status: j.status === 'live' && j.expires_at <= t ? 'expired' : j.status, posted: isoDay(j.created_at), until: isoDay(j.expires_at),
  page: '/job/' + jobSlug(j.title, j.company) + '/', review_reason: j.status === 'review' ? j.review_reason : '', reject_reason: j.status === 'rejected' ? j.reject_reason : '' });
/* What an account that has not confirmed its email can do with a job: have it checked as a draft. The fields, the company name, the
   domain rules and the screen run as for a real posting; nothing is stored, no link is opened, and the draft itself stays in the browser. */
async function previewJob(env, req, user) {
  await limit(env, 'preview:' + user.id, POSTS_PER_HOUR, 3600);
  const j = await readJob(env, user, await body(req), null, true);
  return { ok: true, confirmed: user.confirmed_at > 0, review: j.reasons.length > 0, reasons: j.reasons,
    job: { company: j.company, company_url: j.company_url, title: j.title, apply_url: j.apply_url, location: j.location, remote: !!j.remote, salary: j.salary, etype: j.etype, description: j.description } };
}
/* A job goes live at once only for a trusted account (see trusted) and only when nothing about it asks for a person's look; any other
   job is stored as "review" with the reasons, shown to nobody, and waits for the owner (the admin endpoints below).
   The brakes: a trusted account posts FREE_JOBS_PER_DAY jobs a day; one that is not trusted yet posts NEW_JOBS_PER_DAY a day and has at
   most NEW_LIVE_JOBS on the site or waiting. The daily count is a single statement (see allowed) and counts only jobs that passed every
   check, so a typo does not use up the day. The cap and the duplicate rule are tested again inside the insert itself, so requests
   arriving together cannot get past them. */
async function createJob(env, req, user) {
  if (!user.confirmed_at) throw bad('confirm_email', CONFIRM_FIRST, 403);
  await limit(env, 'post:' + user.id, POSTS_PER_HOUR, 3600);
  const t = now(), j = await readJob(env, user, await body(req), null), fresh = !trusted(user, t), perDay = fresh ? NEW_JOBS_PER_DAY : FREE_JOBS_PER_DAY, cap = fresh ? NEW_LIVE_JOBS : 1e9;
  if (!(await db(env, 'SELECT ' + ROOM + ' AS ok', user.id, t, cap).first('ok'))) throw bad('limit', NO_ROOM, 429);
  if (!(await allowed(env, 'jobs:' + user.id, perDay, DAY))) throw bad('limit', 'You can post ' + perDay + (perDay === 1 ? ' job a day until your account is trusted' : ' jobs a day') + '. Please come back tomorrow.', 429);
  j.company = await claimCompany(env, user, j.company, j.company_key);
  const id = rid('j_', 6), status = j.reasons.length ? 'review' : 'live';
  const made = await db(env, 'INSERT INTO jobs (id, user_id, company, company_key, company_url, title, title_key, slug, apply_url, apply_host, location, remote, salary, etype, description, status, review_reason, ' +
    'held_at, approved_at, checked_at, created_at, expires_at) SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM jobs d WHERE ' + DUPLICATE + ') AND ' + ROOM,
    id, user.id, j.company, j.company_key, j.company_url, j.title, j.title_key, jobSlug(j.title, j.company), j.apply_url, j.apply_host, j.location, j.remote, j.salary, j.etype, j.description, status,
    clip(j.reasons.join('; '), 500), status === 'review' ? t : 0, status === 'live' ? t : 0, t, t, t + FREE_JOB_DAYS * DAY, ...duplicateOf(user.id, j, '', t), user.id, t, cap).run();
  if (!made.meta.changes) throw (await db(env, 'SELECT 1 AS x FROM jobs d WHERE ' + DUPLICATE, ...duplicateOf(user.id, j, '', t)).first()) ? bad('duplicate', SAME_JOB, 409) : bad('limit', NO_ROOM, 429);
  if (!user.company) await db(env, 'UPDATE users SET company = ? WHERE id = ?', j.company, user.id).run();
  if (status === 'review') await bump(env, 'held', t).run(); else await requestRebuild(env);
  return { job: jobView(await db(env, 'SELECT * FROM jobs WHERE id = ?', id).first(), t) };
}
/* Takes jobs off the site for good and switches off what was bought for them: a featured or pinned placement must not outlive its job. */
const takeDown = (env, where, arg, t = now()) => [db(env, "UPDATE placements SET cancelled = 1 WHERE target IN (SELECT 'direct:' || id FROM jobs WHERE " + where + ')', arg),
  db(env, "UPDATE jobs SET status = 'removed', ended_at = ? WHERE status != 'removed' AND " + where, t, arg)];
/* Review never eats paid days. A placement of a job that is waiting for a person is held: held = 1, and its two times are no longer
   moments but seconds counted from zero (what is left of it, and where it stands in the row of placements bought one after another).
   Approval adds the moment of approval back, so the days start then. Both are single statements that look at the job themselves, so
   they do the right thing whichever request gets there first, and doing either twice changes nothing. */
const holdPlacements = (env, id, t) => db(env, "UPDATE placements SET held = 1, starts_at = MAX(starts_at - ?, 0), ends_at = ends_at - ? WHERE target = 'direct:' || ? AND cancelled = 0 AND held = 0 AND ends_at > ? " +
  "AND EXISTS (SELECT 1 FROM jobs WHERE id = ? AND status = 'review')", t, t, id, t, id);
const releasePlacements = (env, id, t) => db(env, "UPDATE placements SET held = 0, starts_at = starts_at + ?, ends_at = ends_at + ? WHERE target = 'direct:' || ? AND cancelled = 0 AND held = 1 " +
  "AND EXISTS (SELECT 1 FROM jobs WHERE id = ? AND status = 'review')", t, t, id, id);
/* Takes a live job off the site until a person has looked at it: one batch, the job and what was bought for it together. */
const hold = (env, id, reason, t) => [db(env, "UPDATE jobs SET status = 'review', review_reason = ?, held_at = ? WHERE id = ? AND status = 'live'", clip(reason, 500), t, id), holdPlacements(env, id, t)];
/* What the employer may do with a job. A job that waits for review can be edited, closed or deleted, but nothing the employer does
   puts it on the site: closing and renewing it brings it back to the queue (its review_reason stays until a person approves it), and
   an edit that gives a reason for review takes a live job off the site until it is approved again. A job a person turned down can
   only be deleted. */
async function updateJob(env, req, user, id, action) {
  const t = now(), old = await db(env, 'SELECT * FROM jobs WHERE id = ? AND user_id = ?', id, user.id).first();
  if (!old || old.status === 'removed' || !['edit', 'close', 'renew', 'delete'].includes(action)) throw bad('not_found', 'Job not found.', 404);
  if (old.status === 'rejected' && action !== 'delete') throw bad('rejected', 'This job was not accepted, so it cannot be changed or published. Delete it and post a corrected one.', 409);
  if (action === 'close') await db(env, "UPDATE jobs SET status = 'closed' WHERE id = ? AND status IN ('live', 'review', 'closed')", id).run();
  else if (action === 'renew') {
    // a job that comes back to the site or to the queue counts against the cap of an account that is not trusted yet; the count is
    // part of the statement that brings it back, so two renewals sent together cannot both get in
    const back = (old.status !== 'live' && old.status !== 'review') || old.expires_at <= t, cap = back && !trusted(user, t) ? NEW_LIVE_JOBS : 1e9;
    const done = await db(env, "UPDATE jobs SET held_at = CASE WHEN review_reason != '' AND status != 'review' THEN ? ELSE held_at END, status = CASE WHEN review_reason != '' THEN 'review' ELSE 'live' END, expires_at = ? " +
      "WHERE id = ? AND status IN ('live', 'review', 'closed') AND (SELECT COUNT(*) FROM jobs c WHERE c.user_id = ? AND c.id != ? AND c.status IN ('live', 'review') AND c.expires_at > ?) < ?",
      t, t + FREE_JOB_DAYS * DAY, id, user.id, id, t, cap).run();
    if (!done.meta.changes) throw bad('limit', NO_ROOM, 429);
  } else if (action === 'delete') await env.DB.batch(takeDown(env, 'id = ?', id, t));
  else {
    const j = await readJob(env, user, { ...jobView(old, t), ...(await body(req)) }, old), why = j.reasons.length ? 1 : 0;
    if (j.company_key !== old.company_key) j.company = await claimCompany(env, user, j.company, j.company_key);
    await env.DB.batch([db(env, 'UPDATE jobs SET company = ?, company_key = ?, company_url = ?, title = ?, title_key = ?, slug = ?, apply_url = ?, apply_host = ?, location = ?, remote = ?, salary = ?, etype = ?, description = ?, ' +
      "held_at = CASE WHEN ? = 1 AND status = 'live' THEN ? ELSE held_at END, status = CASE WHEN ? = 1 AND status = 'live' THEN 'review' ELSE status END, review_reason = CASE WHEN ? = 1 THEN ? ELSE review_reason END " +
      "WHERE id = ? AND status IN ('live', 'review', 'closed')", j.company, j.company_key, j.company_url, j.title, j.title_key, jobSlug(j.title, j.company), j.apply_url, j.apply_host, j.location, j.remote, j.salary, j.etype,
      j.description, why, t, why, why, clip(j.reasons.join('; '), 500), id), holdPlacements(env, id, t)]);
  }
  await requestRebuild(env);
  if (action === 'delete') return { ok: true };
  const row = await db(env, 'SELECT * FROM jobs WHERE id = ?', id).first();
  if (old.status === 'live' && row.status === 'review') await bump(env, 'held', t).run();
  return { job: jobView(row, t) };
}
/* Once a day the link to apply of every live job is opened again, RECHECK_BATCH jobs in one cron run, the longest unchecked first.
   A link that now ends on another host than the one it ended on when the job was checked (a redirect put in after approval, a page
   moved to a form or a chat) takes the job off the site until a person has looked: one batch, with what was bought for it held.
   A link that does not open any more changes nothing here: where it leads is then not known, and a site that is down for an hour is
   not fraud. The note of the time and the test for it are one statement, so two runs cannot both take the same job. */
export async function recheckLinks(env) {
  const t = now(), seen = { checked: 0, held: 0 };
  const due = (await db(env, "SELECT j.id, j.title, j.apply_url, j.apply_host, u.domain, u.email FROM jobs j JOIN users u ON u.id = j.user_id WHERE j.status = 'live' AND j.expires_at > ? AND j.checked_at <= ? " +
    'ORDER BY j.checked_at LIMIT ' + RECHECK_BATCH, t, t - DAY).all()).results;
  for (const j of due) {
    try {
      if (!(await db(env, 'UPDATE jobs SET checked_at = ? WHERE id = ? AND checked_at <= ?', t, j.id, t - DAY).run()).meta.changes) continue;
      const apply = publicUrl(j.apply_url), link = apply ? await checkApplyLink(apply, domainOf(j), j.title) : { host: '' };
      seen.checked++;
      if (!link.host || !j.apply_host || link.host === j.apply_host) continue;
      // the new host is written down with the hold: if the owner approves the job as it now is, that is the host it is compared with from then on
      const done = await env.DB.batch([...hold(env, j.id, 'the link to apply now leads to ' + link.host + ' (it led to ' + j.apply_host + ' when the job was checked)', t),
        db(env, "UPDATE jobs SET apply_host = ? WHERE id = ? AND status = 'review' AND held_at = ?", clip(link.host, 255), j.id, t)]);
      if (done[0].meta.changes) { seen.held++; await bump(env, 'held', t).run(); }
    } catch (err) { console.error('recheck: job ' + j.id + ' failed: ' + (err && err.message)); }      // one bad job does not hold up the rest
  }
  if (seen.held) await requestRebuild(env);
  return seen;
}

/* ---------------------------------------------------------------- reports from job seekers, and the numbers anyone can read */
/* Anyone can report a job, without an account. What is kept: the job, one of six reasons, an optional note, and a salted hash of
   the sender's address (see ipHash), which serves two things only: one address counts once per job, and sends REPORTS_PER_HOUR an hour.
   A job posted here is taken off the site until a person has decided (state "review", reason "reported") by one report that says it
   asks for money or asks to install something, or by two reports of any kind from different addresses. The report, the test and the
   job change are one batch. Reports about jobs read from hiring systems are kept for the owner and change nothing by themselves. */
const REPORT_REASONS = ['asks_for_money', 'asks_to_install', 'moved_to_chat', 'impersonation', 'job_not_real', 'other'];
async function report(env, req) {
  const who = await ipHash(env, req);
  await limit(env, 'report:' + who, REPORTS_PER_HOUR, 3600);
  const b = await body(req), reason = REPORT_REASONS.includes(b.reason) ? b.reason : '', note = b.note == null || b.note === '' ? '' : prose(b.note, 500);
  if (!reason) throw bad('reason', 'Choose what is wrong with this job.');
  if (note === null) throw bad('note', 'Keep the note under 500 characters.');
  const ref = typeof b.job === 'string' ? b.job.trim().slice(0, 300) : '';
  let job = /^j_[a-f0-9]{12}$/.test(ref) ? await db(env, "SELECT id FROM jobs WHERE id = ? AND status != 'removed'", ref).first() : null;
  const slug = job ? '' : jobSlugFrom(ref);
  if (!job && slug) job = await db(env, "SELECT id FROM jobs WHERE slug = ? AND status IN ('live', 'review') ORDER BY created_at DESC LIMIT 1", slug).first();
  if (!job && (!slug || !(await sitePage(env, '/job/' + slug + '/')))) throw bad('job', 'We could not find that job.', 404);
  const t = now(), steps = [db(env, 'INSERT INTO reports (id, job_id, slug, reason, note, ip_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(job_id, slug, ip_hash) DO NOTHING',
    rid('r_'), job ? job.id : '', job ? '' : slug, reason, note, who, t)];
  if (job) steps.push(db(env, "UPDATE jobs SET status = 'review', review_reason = 'reported', held_at = ? WHERE id = ? AND status = 'live' AND (" +
    "EXISTS (SELECT 1 FROM reports r WHERE r.job_id = jobs.id AND r.decided_at = 0 AND r.reason IN ('asks_for_money', 'asks_to_install')) " +
    'OR (SELECT COUNT(DISTINCT r.ip_hash) FROM reports r WHERE r.job_id = jobs.id AND r.decided_at = 0) >= 2)', t, job.id), holdPlacements(env, job.id, t));
  const done = await env.DB.batch(steps);
  if (job && done[1].meta.changes) { await bump(env, 'held', t).run(); await requestRebuild(env); }
  return { ok: true, message: 'Thank you. A person will look at this job.' };      // the same answer for a repeated report: it is counted once
}
/* The numbers of this month and of the one before, for the site to print: how much was checked, turned away, held, removed and how
   fast reports are decided. Counts only: nothing in it points at a job, an account or a reporter. */
async function transparency(env) {
  const t = now(), d = new Date(t * 1000), start = (months) => Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + months, 1) / 1000);
  const month = async (from, to) => {
    const stat = async (k) => Number(await db(env, 'SELECT n FROM stats WHERE month = ? AND k = ?', monthOf(from), k).first('n')) || 0, count = async (sql) => Number(await db(env, sql, from, to).first('n')) || 0;
    const decided = await count('SELECT COUNT(*) AS n FROM reports WHERE decided_at >= ? AND decided_at < ?');
    const middle = decided ? (await db(env, 'SELECT decided_at - created_at AS s FROM reports WHERE decided_at >= ? AND decided_at < ? ORDER BY s LIMIT ? OFFSET ?', from, to, 2 - (decided % 2), (decided - 1) >> 1).all()).results : [];
    return { month: monthOf(from), jobs_checked: await stat('screened'), jobs_rejected_by_screen: await stat('screen_rejected'), jobs_held_for_review: await stat('held'),
      jobs_removed_after_report: await count("SELECT COUNT(*) AS n FROM jobs j WHERE j.status IN ('removed', 'rejected') AND j.ended_at >= ? AND j.ended_at < ? AND EXISTS (SELECT 1 FROM reports r WHERE r.job_id = j.id AND r.decision = 'upheld')"),
      reports_received: await count('SELECT COUNT(*) AS n FROM reports WHERE created_at >= ? AND created_at < ?'),
      accounts_banned: await count('SELECT COUNT(*) AS n FROM users WHERE banned = 1 AND banned_at >= ? AND banned_at < ?'),
      median_hours_report_to_decision: middle.length ? Math.round(middle.reduce((sum, r) => sum + r.s, 0) / middle.length / 360) / 10 : null };
  };
  return { generated: new Date(t * 1000).toISOString(), current: await month(start(0), start(1)), previous: await month(start(-1), start(0)) };
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
  // one row per thing that is live now; "ends" covers time bought on top of the running period; a held placement (its job waits for review) is not running
  const live = (await db(env, 'SELECT kind, target, MAX(ends_at) AS ends FROM placements WHERE cancelled = 0 AND held = 0 AND ends_at > ? GROUP BY kind, target HAVING MIN(starts_at) <= ?', t, t).all()).results;
  // only jobs that are live now leave this service: closed, deleted, taken-down and run-out ones are not in the list, nor is any job
  // that waits for review or was turned down
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
  if (path === '/api/public/transparency.json' && m === 'GET') return transparency(env);
  if (path === '/api/report' && m === 'POST') return report(env, req);
  if (path === '/api/public/products' && m === 'GET') {
    return { products: Object.entries(PRODUCTS).filter(([, p]) => p.group !== 'plus' || env.PLUS_LIVE === '1').map(([id, p]) => ({ id, name: p.name, usd: p.usd, days: p.days || p.plusDays || 0, target: p.target, group: p.group })),
      payments: env.PAY_MODE === 'test' ? 'test' : env.CRYPTOMUS_MERCHANT && env.CRYPTOMUS_API_KEY ? 'on' : 'off' };
  }
  if (path === '/api/auth/signup' && m === 'POST') return signup(env, req, ctx);
  if (path === '/api/auth/login' && m === 'POST') return login(env, req, ctx);
  if (path === '/api/auth/logout' && m === 'POST') return logout(env, req);
  if (path === '/api/auth/confirm' && m === 'POST') return confirmEmail(env, req);
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
  if (path === '/api/auth/confirm/request' && m === 'POST') return confirmRequest(env, user, ctx);
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
    // held: paid for, and its days have not started (or have stopped) because the job waits for review; it has days left, not dates
    return { placements: rows.map((p) => (p.held ? { id: p.id, kind: p.kind, label: p.label, from: '', until: '', days: Math.ceil((p.ends_at - p.starts_at) / DAY), state: 'held' }
      : { id: p.id, kind: p.kind, label: p.label, from: isoDay(p.starts_at), until: isoDay(p.ends_at),
        state: p.ends_at <= t ? 'ended' : !shown(p.target) ? 'paused' : p.starts_at > t ? 'scheduled' : 'live' })) };
  }
  if (path === '/api/jobs/preview' && m === 'POST') return previewJob(env, req, user);
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
/* The owner's side. Every request needs "Authorization: Bearer <ADMIN_TOKEN>"; with the secret not set, nothing here answers. The two
   are compared as hashes, so the comparison takes the same time whatever was sent and says nothing about the length of the secret.
   The review queue: GET review lists the jobs that wait with the reasons, the domain and age of the account; approve puts a job on
   the site, reject turns it down with a reason the employer reads. Each is one batch: the job, the account's counters, what was
   bought for the job and the reports about it change together or not at all. */
const settleReports = (env, id, t) => [             // a job taken off the site for good: the open reports about it were right, and the account loses its trust
  db(env, 'UPDATE users SET upheld_reports = upheld_reports + 1 WHERE id = (SELECT user_id FROM jobs WHERE id = ?) AND EXISTS (SELECT 1 FROM reports WHERE job_id = ? AND decided_at = 0)', id, id),
  db(env, "UPDATE reports SET decision = 'upheld', decided_at = ? WHERE job_id = ? AND decided_at = 0", t, id)];
async function admin(env, req, seg, m) {
  const given = (req.headers.get('Authorization') || '').replace(/^Bearer /, '');
  if (!env.ADMIN_TOKEN || !sameText(await sha256(given), await sha256(String(env.ADMIN_TOKEN)))) throw bad('forbidden', 'Not allowed.', 403);
  const t = now(), id = seg[2] || '';
  if (seg[1] === 'review' && m === 'GET') {
    const rows = (await db(env, 'SELECT j.*, u.domain, u.email, u.created_at AS account_created, u.confirmed_at, u.approved_jobs, u.upheld_reports, ' +
      '(SELECT COUNT(*) FROM reports r WHERE r.job_id = j.id AND r.decided_at = 0) AS open_reports, (SELECT GROUP_CONCAT(DISTINCT r.reason) FROM reports r WHERE r.job_id = j.id AND r.decided_at = 0) AS report_reasons, ' +
      "(SELECT COUNT(*) FROM placements p WHERE p.target = 'direct:' || j.id AND p.held = 1 AND p.cancelled = 0) AS held_placements " +
      "FROM jobs j JOIN users u ON u.id = j.user_id WHERE j.status = 'review' ORDER BY j.held_at, j.created_at LIMIT 200").all()).results;
    return { jobs: rows.map((j) => ({ id: j.id, company: j.company, company_url: j.company_url, title: j.title, apply_url: j.apply_url, apply_host: j.apply_host, location: j.location, salary: j.salary,
      description: j.description, reason: j.review_reason, posted: isoDay(j.created_at), held: isoDay(j.held_at || j.created_at), open_reports: j.open_reports, report_reasons: j.report_reasons || '',
      held_placements: j.held_placements, account: { id: j.user_id, email_domain: domainOf(j), age_days: Math.floor((t - j.account_created) / DAY), confirmed: j.confirmed_at > 0,
        approved_jobs: j.approved_jobs, upheld_reports: j.upheld_reports } })) };
  }
  if (seg[1] === 'jobs' && seg[3] === 'approve' && m === 'POST') {          // counted towards the account's trust once per job; the job's 30 days and the days of what was bought for it start now
    const done = await env.DB.batch([
      db(env, "UPDATE users SET approved_jobs = approved_jobs + 1 WHERE id = (SELECT user_id FROM jobs WHERE id = ? AND status = 'review' AND approved_at = 0)", id),
      db(env, "UPDATE reports SET decision = 'dismissed', decided_at = ? WHERE job_id = ? AND decided_at = 0 AND EXISTS (SELECT 1 FROM jobs WHERE id = ? AND status = 'review')", t, id, id),
      releasePlacements(env, id, t),
      db(env, "UPDATE jobs SET status = 'live', review_reason = '', approved_at = CASE WHEN approved_at = 0 THEN ? ELSE approved_at END, checked_at = ?, expires_at = ? WHERE id = ? AND status = 'review'",
        t, t, t + FREE_JOB_DAYS * DAY, id)]);
    if (!done[3].meta.changes) throw bad('not_found', 'No job with this id is waiting for review.', 404);
    await requestRebuild(env); return { ok: true };
  }
  if (seg[1] === 'jobs' && seg[3] === 'reject' && m === 'POST') {           // the employer sees the reason; what was bought for the job is switched off (a refund is made by hand at the gateway)
    const reason = line((await body(req)).reason, 300, 3);
    if (!reason) throw bad('reason', 'Give the reason in 3 to 300 characters: the employer reads it.');
    if (!(await db(env, "SELECT 1 AS x FROM jobs WHERE id = ? AND status IN ('review', 'live')", id).first())) throw bad('not_found', 'No job with this id is live or waiting for review.', 404);
    await env.DB.batch([...settleReports(env, id, t),
      db(env, "UPDATE placements SET cancelled = 1 WHERE target = 'direct:' || ?", id),
      // the company name goes back when this account has no other job under it: a name must not be held by a job nobody ever saw
      db(env, 'DELETE FROM companies WHERE user_id = (SELECT user_id FROM jobs WHERE id = ?) AND k = (SELECT company_key FROM jobs WHERE id = ?) AND NOT EXISTS (SELECT 1 FROM jobs o WHERE o.id != ? ' +
        "AND o.user_id = companies.user_id AND o.company_key = companies.k AND o.status NOT IN ('removed', 'rejected'))", id, id, id),
      db(env, "UPDATE jobs SET status = 'rejected', reject_reason = ?, ended_at = ? WHERE id = ? AND status IN ('review', 'live')", reason, t, id)]);
    await requestRebuild(env); return { ok: true };
  }
  if (seg[1] === 'reports' && !id && m === 'GET') {
    const rows = (await db(env, 'SELECT r.id, r.job_id, r.slug, r.reason, r.note, r.created_at, r.decision, r.decided_at, j.title, j.company, j.status AS job_status FROM reports r LEFT JOIN jobs j ON j.id = r.job_id ' +
      'ORDER BY r.decided_at != 0, r.created_at DESC LIMIT 200').all()).results;
    return { reports: rows.map((r) => ({ id: r.id, job_id: r.job_id, page: r.job_id ? '' : '/job/' + r.slug + '/', title: r.title || '', company: r.company || '', job_status: r.job_status || '', reason: r.reason, note: r.note,
      received: new Date(r.created_at * 1000).toISOString(), decision: r.decision, decided: r.decided_at ? new Date(r.decided_at * 1000).toISOString() : '' })) };
  }
  // One report on its own: for a job read from a hiring system (there is no job here to approve or reject), or one whose job the
  // employer deleted meanwhile. It changes no job; "upheld" still costs the account of a job posted here its trust.
  if (seg[1] === 'reports' && seg[3] === 'decide' && m === 'POST') {
    const decision = (await body(req)).decision;
    if (decision !== 'upheld' && decision !== 'dismissed') throw bad('decision', 'The decision is "upheld" or "dismissed".');
    const done = await env.DB.batch([
      db(env, "UPDATE users SET upheld_reports = upheld_reports + 1 WHERE ? = 'upheld' AND id = (SELECT j.user_id FROM reports r JOIN jobs j ON j.id = r.job_id WHERE r.id = ? AND r.decided_at = 0)", decision, id),
      db(env, 'UPDATE reports SET decision = ?, decided_at = ? WHERE id = ? AND decided_at = 0', decision, t, id)]);
    if (!done[1].meta.changes) throw bad('not_found', 'No open report with this id.', 404);
    return { ok: true };
  }
  if (seg[1] === 'overview' && m === 'GET') {
    const one = (sql) => db(env, sql).first('n');
    return { users: await one('SELECT COUNT(*) AS n FROM users'), paid_orders: await one("SELECT COUNT(*) AS n FROM orders WHERE status = 'paid' AND amount_usd > 0"),
      revenue_usd: await one("SELECT COALESCE(SUM(amount_usd), 0) AS n FROM orders WHERE status = 'paid'"), live_jobs: await one("SELECT COUNT(*) AS n FROM jobs WHERE status = 'live'"),
      recent_orders: (await db(env, 'SELECT id, product, label, amount_usd, status, created_at FROM orders ORDER BY created_at DESC LIMIT 30').all()).results,
      recent_jobs: (await db(env, 'SELECT id, company, title, apply_url, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 30').all()).results };
  }
  if (seg[1] === 'jobs' && seg[3] === 'remove' && m === 'POST') { await env.DB.batch([...settleReports(env, id, t), ...takeDown(env, 'id = ?', id, t)]); await requestRebuild(env); return { ok: true }; }
  // everything of this account goes: sessions, reset and confirmation links, the browsers it was known by, jobs, what it bought, the
  // company names it held; the reports about its jobs are settled as upheld. /api/admin/accounts/<id>/ban is the same endpoint.
  if ((seg[1] === 'users' || seg[1] === 'accounts') && seg[3] === 'ban' && m === 'POST') {
    await env.DB.batch([db(env, 'UPDATE users SET banned_at = CASE WHEN banned = 0 THEN ? ELSE banned_at END, banned = 1 WHERE id = ?', t, id), db(env, 'DELETE FROM sessions WHERE user_id = ?', id),
      db(env, 'DELETE FROM resets WHERE user_id = ?', id), db(env, 'DELETE FROM confirms WHERE user_id = ?', id), db(env, 'DELETE FROM devices WHERE user_id = ?', id),
      db(env, "UPDATE reports SET decision = 'upheld', decided_at = ? WHERE decided_at = 0 AND job_id IN (SELECT id FROM jobs WHERE user_id = ?)", t, id),
      ...takeDown(env, 'user_id = ?', id, t), db(env, 'UPDATE placements SET cancelled = 1 WHERE user_id = ?', id), db(env, 'DELETE FROM companies WHERE user_id = ?', id)]);
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
      if (err instanceof HttpError) return json({ error: err.code, message: err.message, ...(err.extra || {}) }, err.status, cors);
      console.error(err && err.stack ? err.stack : err);
      return json({ error: 'server', message: 'Something went wrong on our side. Please try again.' }, 500, cors);
    }
  },
  // every ten minutes: settle invoices whose webhook never came (paid ones are switched on, unpaid ones closed), open the link to apply
  // of a few live jobs again (each job once a day), clear out what has run out, and send a rebuild that was held back. Each step stands
  // alone: one that fails does not stop the others.
  async scheduled(event, env) {
    const t = now(), step = async (name, run) => { try { await run(); } catch (err) { console.error('cron: ' + name + ' failed: ' + (err && err.message)); } };
    await step('orders', () => reconcileOrders(env));
    await step('links', () => recheckLinks(env));
    await step('sessions', () => db(env, 'DELETE FROM sessions WHERE expires_at < ?', t).run());
    await step('resets', () => db(env, 'DELETE FROM resets WHERE expires_at < ?', t).run());
    await step('confirms', () => db(env, 'DELETE FROM confirms WHERE expires_at < ?', t).run());
    await step('rate', () => db(env, 'DELETE FROM rate WHERE reset_at < ?', t).run());
    await step('rebuild', async () => { if ((await db(env, "SELECT v FROM meta WHERE k = 'rebuild_wanted'").first('v')) === '1') await requestRebuild(env, true); });
  },
};
