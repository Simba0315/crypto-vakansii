/* Mail without packages: a small SMTP client over TLS (node:tls only), and the mailer the API and the alert job hand letters to.

   Where it sends: Beget's mail server for jobseveryhour.com (smtp.beget.com, port 465, TLS from the first byte, AUTH LOGIN), as one
   of the domain's mailboxes. The mailbox password lives in /etc/hrn-api/api.env (SMTP_PASS), typed in by the owner on the server; it is
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
  // stage: the step it failed at (greeting, EHLO, AUTH ..., MAIL FROM, RCPT TO, DATA, end of data); afterData: no answer came after the
  // letter itself was sent, so it may have been delivered
  constructor(message, code = 0, permanent = false, stage = '') { super(message); this.code = code; this.permanent = permanent; this.stage = stage; this.afterData = false; }
}

/* ---------------------------------------------------------------- the letter itself */
const clean = (s) => String(s == null ? '' : s).replace(/[\r\n]+/g, ' ').trim();     // a header value cannot start a new header
const ascii = (s) => /^[\x20-\x7e]*$/.test(s);
// RFC 2047: a header word with letters outside ASCII, as base64 pieces of whole characters, each piece under 75 characters and on a
// line of its own (folded with CRLF and a space), so no header line grows past 76 characters
export function encodeWord(s) {
  s = clean(s);
  if (ascii(s)) return s;
  const pieces = []; let cur = '';
  for (const ch of s) { if (Buffer.byteLength(cur + ch) > 39) { pieces.push(cur); cur = ''; } cur += ch; }
  if (cur) pieces.push(cur);
  return pieces.map((p) => '=?UTF-8?B?' + Buffer.from(p).toString('base64') + '?=').join('\r\n ');
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
   DATA, QUIT. Answers { code, reply }; throws SmtpError with the server's code (permanent for 5xx) and the step it failed at. The
   password goes only into the AUTH step and appears in no error: an error carries the server's answer, never what was sent.
   After the letter itself the server may take its time (content scanning): RFC 5321 asks for 10 minutes there; dataTimeout (5 minutes)
   is used for that one answer, and an error at that point is marked afterData: the letter may have been delivered, so it is not sent again. */
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
export async function smtpSend({ host, port = 465, user, pass, name = 'localhost', ca, timeout = 30000, dataTimeout = 300000 }, { from, to, data }) {
  if (!ascii(from) || !ascii(to) || /[\s<>]/.test(from + to)) throw new SmtpError('addresses outside ASCII are not supported', 0, true, 'address');
  const socket = tls.connect({ host, port, servername: host, ca, minVersion: 'TLSv1.2' });
  const next = replies(socket, timeout);
  let stage = 'connect';
  const step = async (want, line, what) => {
    stage = what;
    if (line != null) socket.write(line + '\r\n');
    const r = await next();
    if (!want.includes(r.code)) throw new SmtpError(what + ': ' + r.code + ' ' + r.text, r.code, r.code >= 500, what);
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
    socket.setTimeout(Math.max(timeout, dataTimeout));                    // the answer to the letter itself may take a while
    // dot-stuffing: a line that starts with "." gets a second one, so it cannot end the letter early
    const done = await step([250], data.replace(/\r?\n/g, '\r\n').replace(/^\./gm, '..') + '\r\n.', 'end of data');
    try { socket.write('QUIT\r\n'); } catch {}
    socket.end();
    return { code: done.code, reply: done.text };
  } catch (err) {
    socket.destroy();
    const e = err instanceof SmtpError ? err : new SmtpError(String(err && err.message || err));
    if (!e.stage) e.stage = stage;
    if (e.stage === 'end of data' && !e.code) e.afterData = true;        // sent, and no answer: it may have arrived
    throw e;
  }
}
// whether a failure is about this one recipient (its address or mailbox), not about our login, our sender or the server
export const recipientFailure = (err) => !!err && (err.stage === 'RCPT TO' || err.stage === 'address' ||
  (err.stage === 'end of data' && err.code >= 400 && /\b[45]\.[12]\.\d/.test(err.message)));

/* ---------------------------------------------------------------- the mailer: what env.MAIL is
   send({ from, to, subject, text, kind, bulk, share, headers }) -> { sent, status, id, permanent, rejected }.
   status: sent | failed | capped | unknown (no answer after the letter itself: it may have arrived; not sent again, counted as sent
   against the cap). permanent: the server said no for good (5xx). rejected: the failure is about this recipient (recipientFailure), not
   about our login or the server. share: the part of the daily cap this kind of letter may fill (bulk letters BULK_SHARE, everything
   else all of it unless told). Bulk letters are tried once: the alert run reschedules them itself, so one slow mailbox cannot hold up
   the rest. It never throws for a letter that could not go: the caller decides. */
const startOfDay = (t) => t - (t % 86400);
export function createMailer({ db, smtp, from, cap = 300, retries = 3, backoffMs = [5000, 30000, 120000], sleep = (ms) => new Promise((r) => setTimeout(r, ms)),
  now = () => Math.floor(Date.now() / 1000), transport = smtpSend } = {}) {
  if (!db || !smtp || !smtp.host || !smtp.user || !smtp.pass) throw new Error('createMailer needs db and smtp { host, user, pass }');
  const log = (row) => db.prepare('INSERT INTO mail_log (id, at, to_addr, kind, status, attempts, code, reply, message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)')
    .bind('m_' + randomBytes(10).toString('hex'), row.at, row.to, row.kind, row.status, row.attempts, row.code || 0, String(row.reply || '').slice(0, 200), row.id || '').run();
  const sentToday = async (t) => Number(await db.prepare("SELECT COUNT(*) AS n FROM mail_log WHERE at >= ? AND status IN ('sent', 'unknown')").bind(startOfDay(t)).first('n')) || 0;
  // the log of a letter that went: a failure to write it must not send the letter again
  const record = async (row) => { try { await log(row); } catch (err) { console.error('mail: the log could not be written: ' + (err && err.message)); } };
  return {
    cap,
    sentToday: () => sentToday(now()),
    async send({ from: fromGiven, to, subject, text, kind = 'mail', bulk = false, share, headers = {} }) {
      const t = now(), sender = parseAddress(fromGiven || from), rcpt = clean(to).toLowerCase();
      const room = Math.floor(cap * Math.min(1, share > 0 ? share : bulk ? BULK_SHARE : 1)), tries = bulk ? 0 : retries;
      if (await sentToday(t) >= room) { await record({ at: t, to: rcpt, kind, status: 'capped', attempts: 0 }); return { sent: false, status: 'capped' }; }
      const msg = buildMessage({ from: fromGiven || from, to: rcpt, subject, text, headers });
      let attempts = 0, last = null, done = null;
      for (;;) {
        attempts++;
        try { done = await transport(smtp, { from: sender.address, to: rcpt, data: msg.data }); break; }
        catch (err) {
          last = err;
          if (err.permanent || err.afterData || attempts > tries) break;
          await sleep(backoffMs[Math.min(attempts - 1, backoffMs.length - 1)]);
        }
      }
      if (done) { await record({ at: now(), to: rcpt, kind, status: 'sent', attempts, code: done.code, reply: done.reply, id: msg.id }); return { sent: true, status: 'sent', id: msg.id }; }
      const status = last.afterData ? 'unknown' : 'failed';
      await record({ at: now(), to: rcpt, kind, status, attempts, code: last.code, reply: last.message, id: msg.id });
      console.error('mail: a letter (' + kind + ') ' + (status === 'unknown' ? 'got no answer after it was sent' : 'could not be sent') + ' after ' + attempts + ' attempt(s): ' + (last.code || '') + ' ' + String(last.message).slice(0, 120));
      return { sent: false, status, permanent: !!last.permanent, rejected: recipientFailure(last) };
    },
  };
}
