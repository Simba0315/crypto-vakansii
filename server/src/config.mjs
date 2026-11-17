// The settings of the API on our own server, read from one file (/etc/hrn-api/api.env), and the env object the worker gets from them.
// Used by server/prod.mjs (the API) and server/alerts.mjs (the alert job), so both see the same database, mail and site.
//
// The file is KEY=value lines (# starts a comment, quotes around a value are taken off), owned by root and readable by the service's
// user only. Secrets (SMTP_PASS, ADMIN_TOKEN, later the payment keys) live there and nowhere else: never in this repository, never in
// a command line, never in a log. HOSTING.md has the commands that write it.
import { readFileSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { D1 } from './d1.mjs';
import { createMailer } from './mail.js';

export function readEnvFile(file) {
  const out = {};
  if (!file || !existsSync(file)) return out;
  for (const raw of readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = /^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(raw);
    if (!m || /^\s*#/.test(raw)) continue;
    let v = m[2];
    if (/^"(.*)"$/.test(v) || /^'(.*)'$/.test(v)) v = v.slice(1, -1);
    else v = v.replace(/\s+#.*$/, '');
    out[m[1]] = v;
  }
  return out;
}

// company name -> its own site, from logos.json (uploaded with the site every hour); read again when the file changes
function companySites(file) {
  let stamp = -1, map = {};
  return (company) => {
    try {
      const st = statSync(file).mtimeMs;
      if (st !== stamp) { map = JSON.parse(readFileSync(file, 'utf8')); stamp = st; }
    } catch { return ''; }
    return Object.hasOwn(map, company) ? map[company] : '';
  };
}

/* What the worker gets. Payments stay off unless PAYMENTS_LIVE=1 is in the file (the owner switches them on last): without it the
   payment keys are dropped even if they are written there, Plus is not for sale, and /api/orders answers "payments_off". PAY_MODE=test
   (the developer's fake checkout) is refused outright. Mail is on when SMTP_PASS is set. */
export function productionEnv(vars, { serverDir }) {
  if (vars.PAY_MODE) throw new Error('PAY_MODE must not be set on the server (it is for server/dev.mjs only)');
  const site = String(vars.SITE_URL || 'https://jobseveryhour.com').replace(/\/+$/, '');
  const internal = String(vars.SITE_INTERNAL || 'http://127.0.0.1:8790').replace(/\/+$/, '');
  const dbFile = vars.DB_FILE || '/var/lib/hrn-api/api.db';
  const DB = new D1(dbFile).applySchema(path.join(serverDir, 'schema.sql'));
  const env = {
    DB, SITE_URL: site, SITE_ORIGINS: vars.SITE_ORIGINS || new URL(site).origin, API_URL: String(vars.API_URL || site).replace(/\/+$/, ''), SITE_NAME: vars.SITE_NAME || 'Jobs Every Hour',
    SITE_INTERNAL: internal, DUPLICATE_URL: vars.DUPLICATE_URL === 'off' ? '' : vars.DUPLICATE_URL || internal + '/api/check-duplicate',
    COMPANY_SITES: companySites(vars.COMPANY_SITES_FILE || '/srv/hrn/app/logos.json'),
    PLUS_LIVE: '0',
  };
  for (const k of ['ADMIN_TOKEN', 'ADMIN_EMAILS', 'GITHUB_TOKEN', 'GITHUB_REPO', 'LINKEDIN_CLIENT_ID', 'LINKEDIN_CLIENT_SECRET', 'LINKEDIN_REDIRECT_URL', 'ANTHROPIC_API_KEY', 'TALENT_DB', 'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URL']) if (vars[k]) env[k] = vars[k];
  if (vars.PAYMENTS_LIVE === '1') {
    for (const k of ['CRYPTOMUS_MERCHANT', 'CRYPTOMUS_API_KEY']) if (vars[k]) env[k] = vars[k];
    if (vars.PLUS_LIVE === '1') env.PLUS_LIVE = '1';
  }
  if (vars.SMTP_PASS) {
    const user = vars.SMTP_USER || 'support@jobseveryhour.com';
    env.MAIL_FROM = vars.MAIL_FROM || (env.SITE_NAME + ' <' + user + '>');
    env.MAIL = createMailer({ db: DB, from: env.MAIL_FROM, cap: Number(vars.MAIL_DAILY_CAP) || 300,
      smtp: { host: vars.SMTP_HOST || 'smtp.beget.com', port: Number(vars.SMTP_PORT) || 465, user, pass: vars.SMTP_PASS, name: vars.SMTP_HELO || os.hostname() } });
  }
  return env;
}

// One line about the settings for the log: what is on, never a value of a secret.
export const describeEnv = (env) => 'site ' + env.SITE_URL + '; mail ' + (env.MAIL ? 'on (' + env.MAIL_FROM.replace(/^.*</, '<') + ', ' + env.MAIL.cap + ' a day)' : 'off (no SMTP_PASS)') +
  '; payments ' + (env.CRYPTOMUS_MERCHANT && env.CRYPTOMUS_API_KEY ? 'ON' : 'off') + '; admin ' + (env.ADMIN_TOKEN ? 'on' : 'off (no ADMIN_TOKEN)') + '; moderators ' + String(env.ADMIN_EMAILS || '').split(/[\s,;]+/).filter(Boolean).length +
  '; duplicate check ' + (env.DUPLICATE_URL ? 'on' : 'off');
