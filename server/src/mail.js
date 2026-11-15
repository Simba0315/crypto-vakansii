/* Mail without packages: a small SMTP client over TLS (node:tls only), and the mailer the API and the alert job hand letters to.

   Where it sends: Beget's mail server for jobseveryhour.com (smtp.beget.com, port 465, TLS from the first byte, AUTH LOGIN), as one
   of the domain's mailboxes. The mailbox password lives in /srv/hrn/api.env (SMTP_PASS), typed in by the owner on the server; it is
   never in this repository and never in a log. Any other SMTP service that takes TLS on 465 and AUTH LOGIN works the same way.

   What the mailer adds around a single send:
   - a daily cap (MAIL_DAILY_CAP, counted per UTC day over both programs, since they share the database): over it nothing is sent
     and the letter is logged as "capped". Bulk letters (job alerts) stop earlier, at BULK_SHARE of the cap, so the links that
     confirm an address or reset a password always have room;
   - retries with backoff for failures that may pass (no connection, a time-out, a 4xx answer); a 5xx answer is final;
   - a log of every letter in mail_log: when, to whom, what kind (confirm, reset, alert ...), the result, the number of attempts,
     the server's last answer and the Message-ID. Never the subject line or the text: a letter can carry a link that opens an
     account. The cron deletes rows older than MAIL_LOG_DAYS (see worker.js).
   - headers: Date, Message-ID, MIME, quoted-printable text, Auto-Submitted (so out-of-office robots do not answer), and for bulk
     letters the ones the sender passes: List-Unsubscribe with List-Unsubscribe-Post (RFC 8058, the one-click unsubscribe Gmail
     and Yahoo ask of bulk senders), List-Id and Precedence. */
import tls from 'node:tls';
import { randomBytes } from 'node:crypto';

export const BULK_SHARE = 0.8;                   // the share of the daily cap bulk letters may use
export const MAIL_LOG_DAYS = 30;

export class SmtpError extends Error {
  constructor(message, code = 0, permanent = false) { super(message); this.code = code; this.permanent = permanent; }
}

/* ---------------------------------------------------------------- the letter itself */
const clean = (s) => String(s == null ? '' : s).replace(/[\r\n]+/g, ' ').trim();     // a header value cannot start a new header
const ascii = (s) => /^[\x20-\x7e]*$/.test(s);
// RFC 2047: a header word with letters outside ASCII, as base64 pieces of whole characters, each piece under 75 characters
export function encodeWord(s) {
  s = clean(s);
  if (ascii(s)) return s;
  const pieces = []; let cur = '';
  for (const ch of s) { if (Buffer.byteLength(cur + ch) > 45) { pieces.push(cur); cur = ''; } cur += ch; }
  if (cur) pieces.push(cur);
  return pieces.map((p) => '=?UTF-8?B?' + Buffer.from(p).toString('base64') + '?=').join(' ');
}
// "Jobs Every Hour <support@jobseveryhour.com>" -> { name, address }
export function parseAddress(v) {
  const s = clean(v), m = /^(.*?)\s*<([^<>\s]+@[^<>\s]+)>$/.exec(s);
  return m ? { name: m[1].replace(/^"|"$/g, '').trim(), address: m[2] } : { name: '', address: s };
}
const formatAddress = ({ name, address }) => (name ? (ascii(name) ? '"' + name.replace(/["\\]/g, '') + '"' : encodeWord(name)) + ' <' + address + '>' : address);
// Quoted-printable (RFC 2045): plain text stays readable in the raw letter; lines of at most 76 characters, CRLF between them.
export function quotedPrintable(text) {
  const out = [];
  for (const line of String(text).replace(/\r\n?/g, '\n').split('\n')) {
    const bytes = Buffer.from(line, 'utf8');
    let cur = '';
    bytes.forEach((b, i) => {
      const last = i === bytes.length - 1;
      const piece = (b >= 33 && b <= 126 && b !== 61) || ((b === 32 || b === 9) && !last) ? String.fromCharCode(b) : '=' + b.toString(16).toUpperCase().padStart(2, '0');
      if (cur.length + piece.length > 75) { out.push(cur + '='); cur = ''; }
      cur += piece;
    });
    out.push(cur);
  }
  return out.join('\r\n');
}
const rfcDate = (d) => d.toUTCString().replace(/GMT$/, '+0000');
// The whole message as it goes after DATA (before dot-stuffing). headers: extra headers, name -> value.
export function buildMessage({ from, to, subject, text, headers = {}, date = new Date(), messageId }) {
  const f = parseAddress(from), domain = f.address.slice(f.address.lastIndexOf('@') + 1) || 'localhost';
  const id = messageId || '<' + randomBytes(12).toString('hex') + '@' + domain + '>';
  const head = [['From', formatAddress(f)], ['To', clean(to)], ['Subject', encodeWord(subject)], ['Date', rfcDate(date)], ['Message-ID', id], ['MIME-Version', '1.0'],
    ['Content-Type', 'text/plain; charset=utf-8'], ['Content-Transfer-Encoding', 'quoted-printable'], ['Auto-Submitted', 'auto-generated'],
    ...Object.entries(headers).filter(([k, v]) => /^[A-Za-z][A-Za-z0-9-]{0,60}$/.test(k) && v != null && clean(v)).map(([k, v]) => [k, clean(v)])];
  return { id, data: head.map(([k, v]) => k + ': ' + v).join('\r\n') + '\r\n\r\n' + quotedPrintable(text) };
}

/* ---------------------------------------------------------------- one SMTP conversation
   TLS from the first byte (port 465), the server's certificate checked against its name, EHLO, AUTH LOGIN, MAIL FROM, RCPT TO,
   DATA, QUIT. Answers { code, reply, messageId }; throws SmtpError with the server's code (permanent for 5xx). The password goes
   only into the AUTH step and appears in no error: an error carries the server's answer, never what was sent. */
function replies(socket, timeout) {
  let buf = '', current = [], failed = null;
  const queue = [], waiters = [];
  const fail = (err) => { if (failed) return; failed = err; while (waiters.length) waiters.shift().reject(err); };
  socket.setEncoding('utf8');
  socket.setTimeout(timeout, () => { fail(new SmtpError('the mail server did not answer in time')); socket.destroy(); });
  socket.on('error', (err) => fail(new SmtpError('connection failed: ' + (err.code || err.message))));
  socket.on('close', () => fail(new SmtpError('the mail server closed the connection')));
  socket.on('data', (d) => {
    buf += d;
    if (buf.length > 65536) { fail(new SmtpError('the mail server sent too much')); socket.destroy(); return; }
    let i;
    while ((i = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, i).replace(/\r$/, ''); buf = buf.slice(i + 1);
      current.push(line);
      if (/^\d{3}-/.test(line)) continue;
      const reply = { code: Number(line.slice(0, 3)) || 0, text: current.map((l) => l.slice(4)).join(' ').slice(0, 300) };
      current = [];
      if (waiters.length) waiters.shift().resolve(reply); else queue.push(reply);
    }
  });
  return () => new Promise((resolve, reject) => {
    if (queue.length) return resolve(queue.shift());
    if (failed) return reject(failed);
    waiters.push({ resolve, reject });
  });
}
export async function smtpSend({ host, port = 465, user, pass, name = 'localhost', ca, timeout = 30000 }, { from, to, data }) {
  if (!ascii(from) || !ascii(to) || /[\s<>]/.test(from + to)) throw new SmtpError('addresses outside ASCII are not supported', 0, true);
  const socket = tls.connect({ host, port, servername: host, ca, minVersion: 'TLSv1.2' });
  const next = replies(socket, timeout);
  const step = async (want, line, what) => {
    if (line != null) socket.write(line + '\r\n');
    const r = await next();
    if (!want.includes(r.code)) throw new SmtpError(what + ': ' + r.code + ' ' + r.text, r.code, r.code >= 500);
    return r;
  };
  try {
    await step([220], null, 'greeting');
    await step([250], 'EHLO ' + name, 'EHLO');
    await step([334], 'AUTH LOGIN', 'AUTH');
    await step([334], Buffer.from(user).toString('base64'), 'AUTH user');
    await step([235], Buffer.from(pass).toString('base64'), 'AUTH password');
    await step([250], 'MAIL FROM:<' + from + '>', 'MAIL FROM');
    await step([250, 251], 'RCPT TO:<' + to + '>', 'RCPT TO');
    await step([354], 'DATA', 'DATA');
    // dot-stuffing: a line that starts with "." gets a second one, so it cannot end the letter early
    const done = await step([250], data.replace(/\r?\n/g, '\r\n').replace(/^\./gm, '..') + '\r\n.', 'end of data');
    try { socket.write('QUIT\r\n'); } catch {}
    socket.end();
    return { code: done.code, reply: done.text };
  } catch (err) {
    socket.destroy();
    throw err instanceof SmtpError ? err : new SmtpError(String(err && err.message || err));
  }
}

/* ---------------------------------------------------------------- the mailer: what env.MAIL is
   send({ from, to, subject, text, kind, bulk, headers }) -> { sent, status, id, permanent }. status: sent | failed | capped; permanent:
   the server refused the letter for good (5xx). It never throws for
   a letter that could not go: the caller decides (the alert job tries again in its next run, a sign-up says "ask for a new link"). */
const startOfDay = (t) => t - (t % 86400);
export function createMailer({ db, smtp, from, cap = 300, retries = 3, backoffMs = [5000, 30000, 120000], sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
  now = () => Math.floor(Date.now() / 1000), transport = smtpSend } = {}) {
  if (!db || !smtp || !smtp.host || !smtp.user || !smtp.pass) throw new Error('createMailer needs db and smtp { host, user, pass }');
  const log = (row) => db.prepare('INSERT INTO mail_log (id, at, to_addr, kind, status, attempts, code, reply, message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)')
    .bind('m_' + randomBytes(10).toString('hex'), row.at, row.to, row.kind, row.status, row.attempts, row.code || 0, String(row.reply || '').slice(0, 200), row.id || '').run();
  const sentToday = async (t) => Number(await db.prepare("SELECT COUNT(*) AS n FROM mail_log WHERE at >= ? AND status = 'sent'").bind(startOfDay(t)).first('n')) || 0;
  return {
    cap,
    sentToday: () => sentToday(now()),
    async send({ from: fromGiven, to, subject, text, kind = 'mail', bulk = false, headers = {} }) {
      const t = now(), sender = parseAddress(fromGiven || from), rcpt = clean(to).toLowerCase();
      const room = bulk ? Math.floor(cap * BULK_SHARE) : cap;
      if (await sentToday(t) >= room) { await log({ at: t, to: rcpt, kind, status: 'capped', attempts: 0 }); return { sent: false, status: 'capped' }; }
      const msg = buildMessage({ from: fromGiven || from, to: rcpt, subject, text, headers });
      let attempts = 0, last = null;
      for (;;) {
        attempts++;
        try {
          const r = await transport(smtp, { from: sender.address, to: rcpt, data: msg.data });
          await log({ at: now(), to: rcpt, kind, status: 'sent', attempts, code: r.code, reply: r.reply, id: msg.id });
          return { sent: true, status: 'sent', id: msg.id };
        } catch (err) {
          last = err;
          if (err.permanent || attempts > retries) break;
          await sleep(backoffMs[Math.min(attempts - 1, backoffMs.length - 1)]);
        }
      }
      await log({ at: now(), to: rcpt, kind, status: 'failed', attempts, code: last.code, reply: last.message, id: msg.id });
      console.error('mail: a letter (' + kind + ') could not be sent after ' + attempts + ' attempt(s): ' + (last.code || '') + ' ' + String(last.message).slice(0, 120));
      return { sent: false, status: 'failed', permanent: !!last.permanent };
    },
  };
}
