/* Job alerts: "Email me new jobs like these". An address and a saved search (words, category, place, remote, least pay), a letter
   daily or weekly with at most ALERT_MAX_JOBS new jobs. The endpoints are in worker.js (/api/alerts...); this file holds what they
   share with the alert job (server/alerts.mjs, run by hrn-alerts.timer):

   - readAlert: what a sign-up may say, cleaned; nothing free-form reaches a letter (the confirmation goes to an address somebody typed,
     so a sign-up form must not become a way to mail a stranger a link or a sentence of one's choosing).
   - Double opt-in: an alert starts "pending" and only a confirmation link mailed to the address makes it "active". Until then the
     address gets that one letter and nothing else; a pending alert is deleted after PENDING_DAYS.
   - Links: confirm and unsubscribe links carry the alert id and an HMAC of it (alertToken), keyed by a random secret kept in the
     database (meta 'alert_key'), so no token is stored and a link cannot be made up. A GET on either link only shows a page with a
     button; the change is made by a POST (the button, or a mail client's one-click unsubscribe, RFC 8058), because mail scanners
     open links in letters by themselves.
   - Every letter carries the unsubscribe link and the List-Unsubscribe headers; no image, no tracking pixel, no counted links.
   - matches: the same rules as the site's own search filters (assets/site.js match()): category slug, place slug from the job's
     places, remote, pay from the job's yearly range in US dollars, and every word in the title, company or skills.
   - runAlerts: the periodic run. Each job is offered once: an alert remembers the newest first_seen_at of the records it was matched
     against (seen_through), and the next run looks only at jobs first seen after it.
   Works on Cloudflare too (Web Crypto, no node: imports); reading data/jobs.db is in records.mjs. */

export const ALERT_MAX_JOBS = 20;          // jobs in one letter at most
export const PENDING_DAYS = 7;             // an alert nobody confirmed is deleted after this
export const ALERTS_PER_EMAIL = 5;         // alerts one address may have
export const CONFIRMS_PER_EMAIL_DAY = 3;   // confirmation letters one address may get in a day, whoever asks
export const SIGNUPS_PER_IP_HOUR = 10;     // sign-ups one visitor's address may send in an hour
const DAY = 86400, SLACK = 1800;           // the next letter is due a little under a day (or a week) later, so the hourly run does not drift
export const PERIOD = { daily: DAY, weekly: 7 * DAY };

const enc = new TextEncoder();
const hex = (buf) => Array.from(new Uint8Array(buf), (b) => b.toString(16).padStart(2, '0')).join('');
export const isoTime = (ts) => new Date(ts * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');

// The categories of the site (CATS in collect.py): slug -> name. A slug that is not here is not taken.
export const CATEGORIES = { security: 'Security', engineering: 'Engineering', product: 'Product', design: 'Design', 'sales-bd': 'Sales & Business Development',
  marketing: 'Marketing & Community', support: 'Customer Support', 'compliance-legal': 'Compliance & Legal', finance: 'Finance & Trading', people: 'People & Recruiting',
  'data-research': 'Data & Research', operations: 'Operations', healthcare: 'Healthcare', manufacturing: 'Manufacturing & Trades', 'supply-chain': 'Supply Chain & Logistics',
  retail: 'Retail & Hospitality', education: 'Education & Training', consulting: 'Consulting & Solutions', other: 'Other' };
// A place slug (/locations/<slug>/) as words: "united-states" -> "United States". The site's own names are longer lists; the slug reads well enough.
const SMALL = new Set(['and', 'of', 'the']);
export const placeName = (slug) => String(slug).split('-').map((w, i) => (SMALL.has(w) && i ? w : w.length <= 2 ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1))).join(' ');

/* ---------------------------------------------------------------- what a sign-up may say */
const STOP = new Set('a an and or not the of in at for to with on job jobs role roles position positions vacancy vacancies opening openings career careers hiring work remote'.split(' '));
const DOTTED = new Set(['.net', 'asp.net', 'node.js', 'vue.js', 'next.js', 'react.js', 'nuxt.js', 'd3.js', 'three.js', 'ember.js']);
// The words of a search, made harmless: letters, digits, + and # only (C++, C#), a dot only inside the few names that have one, at most
// six words. "visit evil.com" becomes "visit evilcom": no address can be planted in a letter.
export function cleanWords(q) {
  const words = [];
  for (let w of String(q || '').toLowerCase().normalize('NFKC').split(/[\s,;/|]+/)) {
    w = w.replace(/^[.\-]+|[.\-]+$/g, '');
    if (!DOTTED.has(w) && !DOTTED.has('.' + w)) w = w.replace(/\./g, '');
    else if (DOTTED.has('.' + w)) w = '.' + w;
    w = w.replace(/[^\p{L}\p{N}+#.\-]/gu, '').slice(0, 30);
    if ((w.match(/\d/g) || []).length >= 5) continue;                  // a phone number, an amount: not a job word (web3, s3, 3d stay)
    if (w && !STOP.has(w) && !words.includes(w)) words.push(w);
    if (words.length === 6) break;
  }
  return words.join(' ').slice(0, 80);
}
export class AlertInputError extends Error { constructor(code, message) { super(message); this.code = code; } }
const truthy = (v) => v === true || v === 1 || ['1', 'true', 'on', 'yes'].includes(String(v == null ? '' : v).toLowerCase());
// From a form or JSON: { q, cat, loc, remote, sal, freq }. The search page's own parameter names are taken too.
export function readAlert(b) {
  const cat = String(b.cat || '').trim(), loc = String(b.loc || '').trim().toLowerCase(), freq = String(b.freq || 'daily');
  if (cat && !Object.hasOwn(CATEGORIES, cat)) throw new AlertInputError('cat', 'Choose a category from the site.');
  if (loc && !/^[a-z0-9]+(?:-[a-z0-9]+){0,5}$/.test(loc)) throw new AlertInputError('loc', 'Choose a place from the site.');
  if (!PERIOD[freq]) throw new AlertInputError('freq', 'Choose daily or weekly.');
  const salRaw = Number(String(b.sal == null ? '' : b.sal).replace(/[^\d.]/g, '')) || 0;
  if (salRaw < 0 || salRaw > 2000000) throw new AlertInputError('sal', 'Enter the least yearly pay in US dollars, or leave it empty.');
  return { q: cleanWords(b.q), cat, loc: loc.slice(0, 60), remote: truthy(b.remote) ? 1 : 0, sal: Math.round(salRaw / 1000) * 1000, freq };
}
// How an alert reads in a letter and on a page: "“python” jobs in Engineering · Berlin · remote only · $100K+ a year"
export function describe(a) {
  const what = a.q ? '“' + a.q + '” jobs' + (a.cat ? ' in ' + CATEGORIES[a.cat] : '') : a.cat ? CATEGORIES[a.cat] + ' jobs' : 'All new jobs';
  return [what, a.loc ? placeName(a.loc) : '', a.remote ? 'remote only' : '', a.sal ? '$' + Math.round(a.sal / 1000) + 'K+ a year' : ''].filter(Boolean).join(' · ');
}
// The same search on the site: /jobs/?q=...&cat=...&loc=...&remote=1&sal=...
export function searchLink(site, a) {
  const p = new URLSearchParams();
  if (a.q) p.set('q', a.q);
  if (a.cat) p.set('cat', a.cat);
  if (a.loc) p.set('loc', a.loc);
  if (a.remote) p.set('remote', '1');
  if (a.sal) p.set('sal', String(a.sal));
  const s = p.toString();
  return site + '/jobs/' + (s ? '?' + s : '');
}

/* ---------------------------------------------------------------- matching a job record */
// words people write for the same thing (a short form of the SYN list in assets/site.js)
const SYN = { js: ['javascript', 'js'], ts: ['typescript', 'ts'], golang: ['golang', 'go'], k8s: ['kubernetes', 'k8s'], py: ['python'], ml: ['machine learning', 'ml'],
  ai: ['ai', 'artificial intelligence', 'llm'], frontend: ['frontend', 'front end', 'front-end'], backend: ['backend', 'back end', 'back-end'], fullstack: ['fullstack', 'full stack', 'full-stack'],
  devops: ['devops', 'site reliability', 'platform engineer'], sre: ['site reliability', 'sre'], swe: ['software engineer', 'swe'], pm: ['product manager', 'project manager', 'pm'],
  ux: ['ux', 'user experience'], qa: ['qa', 'quality assurance', 'test engineer'], hr: ['hr', 'human resources', 'people partner'], dev: ['developer', 'engineer', 'dev'],
  developer: ['developer', 'engineer'], web3: ['web3', 'crypto', 'blockchain', 'defi'], crypto: ['crypto', 'blockchain', 'web3', 'defi'] };
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const stem = (w) => (w.length > 3 && /[a-z]s$/.test(w) && !/ss$/.test(w) ? w.slice(0, -1) : w);
// One test per word: the word, or one of its other spellings, as a whole word with the usual English endings. "engineer" finds
// "Engineering" and "Engineers", "design" finds "Designer"; "java" does not find "JavaScript" and "go" does not find "Google".
const ENDINGS = '(?:s|es|ing|ings|er|ers|ed|ment|ments)?(?![\\p{L}\\p{N}])';
export function wordTests(q) {
  return String(q || '').split(' ').filter(Boolean).map((w) => new RegExp((SYN[w] || [stem(w)]).map((x) => '(?<![\\p{L}\\p{N}])' + escapeRe(x) + (/[\p{L}\p{N}]$/u.test(x) ? ENDINGS : '')).join('|'), 'iu'));
}
export function matches(a, j, tests = wordTests(a.q)) {
  if (!j || j.tg) return false;                                                      // posts read from Telegram channels stay on the site only
  if (a.cat && j.cat !== a.cat) return false;
  if (a.loc && !(Array.isArray(j.places) && j.places.includes(a.loc))) return false;
  if (a.remote && !j.remote) return false;
  if (a.sal && !(Array.isArray(j.usd) && Number(j.usd[1]) >= a.sal)) return false;
  if (!tests.length) return true;
  const hay = [j.title, j.company, ...(Array.isArray(j.tags) ? j.tags : [])].join(' \n ');
  return tests.every((re) => re.test(hay));
}

/* ---------------------------------------------------------------- links in letters */
async function alertKey(env) {
  const fresh = hex(crypto.getRandomValues(new Uint8Array(32)));
  const k = await env.DB.prepare("INSERT INTO meta (k, v) VALUES ('alert_key', ?) ON CONFLICT(k) DO UPDATE SET v = meta.v RETURNING v").bind(fresh).first('v');
  return crypto.subtle.importKey('raw', enc.encode(k), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
}
// purpose: "confirm" | "unsub". 32 hex characters (128 bits) of HMAC-SHA-256 over "<purpose>:<id>".
export async function alertToken(env, purpose, id) {
  return hex(await crypto.subtle.sign('HMAC', await alertKey(env), enc.encode(purpose + ':' + id))).slice(0, 32);
}
export async function tokenOk(env, purpose, id, token) {
  if (!/^a_[a-f0-9]{20}$/.test(String(id)) || !/^[a-f0-9]{32}$/.test(String(token))) return false;
  const want = await alertToken(env, purpose, id);
  let d = 0; for (let i = 0; i < 32; i++) d |= want.charCodeAt(i) ^ token.charCodeAt(i);
  return d === 0;
}
const apiBase = (env) => String(env.API_URL || env.SITE_URL || '').replace(/\/+$/, '');
export const confirmLink = async (env, id) => apiBase(env) + '/api/alerts/confirm?a=' + id + '&t=' + await alertToken(env, 'confirm', id);
export const unsubLink = async (env, id) => apiBase(env) + '/api/alerts/unsubscribe?a=' + id + '&t=' + await alertToken(env, 'unsub', id);
const siteHost = (env) => { try { return new URL(env.SITE_URL).hostname; } catch { return 'localhost'; } };
const siteName = (env) => String(env.SITE_NAME || 'Jobs Every Hour');

/* ---------------------------------------------------------------- the letters */
// The subject leaves out the words of the search: it is what shows in a stranger's list of letters if someone typed their address.
export async function confirmLetter(env, a) {
  return { subject: 'Confirm your job alert' + (a.cat || a.loc || a.remote || a.sal ? ': ' + describe({ ...a, q: '' }).replace(/^All new jobs/, 'Jobs').slice(0, 90) : ''),
    text: 'Someone, we hope you, asked ' + siteName(env) + ' to email new jobs to this address:\n\n  ' + describe(a) + '\n  ' + (a.freq === 'weekly' ? 'Once a week' : 'Once a day') +
      ', at most ' + ALERT_MAX_JOBS + ' jobs in a letter, only when there are new ones.\n\nTo confirm, open this link and press the button on the page:\n' + await confirmLink(env, a.id) +
      '\n\nNothing is sent until you confirm. If you did not ask for this, ignore this letter: the request is deleted in ' + PENDING_DAYS + ' days.\n\n' +
      siteName(env) + ' · ' + env.SITE_URL + '/\n' };
}
const jobLine = (env, j, i) => (i + 1) + '. ' + j.title + ' — ' + j.company + '\n   ' + [j.location || '', j.remote ? 'Remote' : '', j.salary || ''].filter(Boolean).join(' · ') +
  (j.location || j.remote || j.salary ? '\n   ' : '') + env.SITE_URL + '/job/' + j.slug + '/';
export async function alertLetter(env, a, jobs, total) {
  const unsub = await unsubLink(env, a.id), n = jobs.length, since = a.last_sent_at ? new Date(a.last_sent_at * 1000) : new Date(a.confirmed_at * 1000);
  const text = (total === 1 ? '1 new job' : total + ' new jobs') + ' for your alert “' + describe(a) + '” since ' + since.toUTCString().slice(5, 16) + '.' +
    (total > n ? ' The newest ' + n + ' are below.' : '') + '\n\n' + jobs.map((j, i) => jobLine(env, j, i)).join('\n\n') + '\n\n' +
    (total > n ? 'All ' + total + ' and older ones: ' : 'The same search on the site: ') + searchLink(env.SITE_URL, a) + '\n\n' +
    '—\nYou get this letter because this address asked for ' + (a.freq === 'weekly' ? 'weekly' : 'daily') + ' job alerts at ' + siteHost(env) + ' and confirmed it.\n' +
    'Unsubscribe, or get it ' + (a.freq === 'weekly' ? 'daily' : 'weekly') + ' instead: ' + unsub + '\n' +
    siteName(env) + ' reads open jobs from employers’ own careers pages every hour. The letter has no images and its links are not counted.\n';
  return { subject: (total === 1 ? '1 new job: ' : total + ' new jobs: ') + describe(a).slice(0, 80), text,
    headers: { 'List-Unsubscribe': '<' + unsub + '>', 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click', 'List-Id': 'Job alerts <alerts.' + siteHost(env) + '>', Precedence: 'bulk' } };
}

/* ---------------------------------------------------------------- the periodic run (hrn-alerts.timer, every hour)
   records: { watermark(): the newest first_seen_at in the job records ('' when there are none), newSince(iso): the open jobs first seen
   after it, each a record (slug, title, company, location, remote, salary, usd, places, cat, tags, first_seen_at) } (records.mjs).
   For each active alert that is due, in order of due time: the jobs first seen after its seen_through and up to the watermark that
   match it, newest first, one per title and company. None: nothing is sent. Some: one letter with the newest ALERT_MAX_JOBS. Either
   way the alert moves on to the watermark (never back, should an older file turn up) and is due again a day (a week) later.
   When a letter does not go:
   - held back by the daily cap, or a failure of the mail server itself (no connection, our login refused, our sender refused): the run
     ends and nothing moves, so the next run sends it; one bad hour costs nothing and no subscriber pays for it;
   - refused for this address (its mailbox is full, does not exist): the alert waits for its next period with the jobs kept, and is
     deleted after 3 such refusals in a row that were final (5xx), or 7 of any kind;
   - no answer after the letter itself (status "unknown"): it may have arrived, so it counts as sent (no second copy) and the run ends.
   An alert is read again just before its letter goes, so one unsubscribed while the run was under way gets nothing.
   Pending alerts older than PENDING_DAYS are deleted first. */
export async function runAlerts(env, records, { now = Math.floor(Date.now() / 1000), batch = 5000 } = {}) {
  const db = (sql, ...args) => env.DB.prepare(sql).bind(...args), out = { due: 0, sent: 0, empty: 0, failed: 0, capped: false, stopped: '', dropped: 0, expired: 0 };
  out.expired = (await db("DELETE FROM alerts WHERE status = 'pending' AND created_at < ?", now - PENDING_DAYS * DAY).run()).meta.changes;
  const due = (await db("SELECT * FROM alerts WHERE status = 'active' AND due_at <= ? ORDER BY due_at LIMIT ?", now, batch).all()).results;
  out.due = due.length;
  if (!due.length) return out;
  const top = records.watermark();
  if (!top) return out;                                                             // no records yet: try again next hour
  const start = (a) => a.seen_through || isoTime(a.confirmed_at);
  const fresh = records.newSince(due.map(start).sort()[0]).filter((j) => j.first_seen_at && j.first_seen_at <= top)
    .sort((x, y) => (x.first_seen_at < y.first_seen_at ? 1 : x.first_seen_at > y.first_seen_at ? -1 : 0));
  for (const a of due) {
    const from = start(a), upto = top > from ? top : from, tests = wordTests(a.q), seen = new Set(), hits = [];
    for (const j of fresh) {
      if (j.first_seen_at <= from || !matches(a, j, tests)) continue;
      const k = (j.title + '\n' + j.company).toLowerCase();
      if (!seen.has(k)) { seen.add(k); hits.push(j); }
    }
    const next = Math.max(now, a.due_at) + PERIOD[a.freq] - SLACK;
    if (!hits.length) {
      await db("UPDATE alerts SET seen_through = ?, due_at = ? WHERE id = ? AND status = 'active'", upto, next, a.id).run();
      out.empty++; continue;
    }
    if ((await db('SELECT status FROM alerts WHERE id = ?', a.id).first('status')) !== 'active') continue;      // unsubscribed meanwhile
    const l = await alertLetter(env, a, hits.slice(0, ALERT_MAX_JOBS), hits.length);
    const r = env.MAIL && typeof env.MAIL.send === 'function'
      ? await env.MAIL.send({ from: String(env.MAIL_FROM || ''), to: a.email, subject: l.subject, text: l.text, kind: 'alert', bulk: true, headers: l.headers })
      : { sent: false, status: 'no_mail' };
    if (!r || r.sent !== false || r.status === 'unknown') {                         // a mailer that answers nothing has taken it
      await db("UPDATE alerts SET seen_through = ?, due_at = ?, last_sent_at = ?, letters = letters + 1, fails = 0 WHERE id = ? AND status = 'active'", upto, next, now, a.id).run();
      out.sent++;
      if (r && r.status === 'unknown') { out.stopped = 'no answer from the mail server after a letter'; break; }
      continue;
    }
    if (r.status === 'capped' || r.status === 'no_mail') { out.capped = r.status === 'capped'; out.stopped = r.status; break; }   // the rest wait for the next run
    out.failed++;
    if (!r.rejected) { out.stopped = 'the mail server failed'; break; }               // not this address's fault: nothing moves, the next run tries again
    const f = Number(await db("UPDATE alerts SET fails = fails + 1, due_at = ? WHERE id = ? RETURNING fails", next, a.id).first('fails'));
    if ((r.permanent && f >= 3) || f >= 7) { await db('DELETE FROM alerts WHERE id = ?', a.id).run(); out.dropped++; }
  }
  return out;
}
