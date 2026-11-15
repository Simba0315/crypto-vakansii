// Sends one test letter through the mail settings of /etc/hrn-api/api.env, to see that the mailbox password and the mail server work:
//   sudo -u hrnapi /usr/local/bin/node --no-warnings /opt/hrn-api/server/mail-test.mjs you@example.com
// It prints the result and the server's answer; it is logged in the mail log as kind "test" and counts towards the daily cap.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readEnvFile, productionEnv } from './src/config.mjs';

const to = String(process.argv[2] || '');
if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(to)) { console.log('give an address: mail-test.mjs you@example.com'); process.exit(1); }
const env = productionEnv(readEnvFile(process.env.API_ENV || '/etc/hrn-api/api.env'), { serverDir: path.dirname(fileURLToPath(import.meta.url)) });
if (!env.MAIL) { console.log('mail is off: there is no SMTP_PASS in the settings'); process.exit(1); }
const r = await env.MAIL.send({ to, subject: 'Test letter from ' + env.SITE_NAME, kind: 'test',
  text: 'This is a test of the mail settings of ' + env.SITE_URL + '/.\n\nIf it arrived, letters that confirm accounts and job alerts will arrive too.\n' });
const row = await env.DB.prepare("SELECT status, attempts, code, reply FROM mail_log WHERE kind = 'test' ORDER BY at DESC LIMIT 1").first();
console.log(JSON.stringify({ sent: r.sent, status: r.status, ...row }));
env.DB.close();
process.exit(r.sent ? 0 : 1);
