// The job alert run: sends the letters that are due (src/alerts.js runAlerts) and stops. hrn-alerts.timer starts it every hour, after
// the hourly upload of the job records has usually landed.
//
//   node server/alerts.mjs                  settings from /etc/hrn-api/api.env, records from /srv/hrn/app/data/jobs.db (RECORDS_FILE=...)
//   node server/alerts.mjs --dry            matches and counts, sends nothing, changes nothing
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { readEnvFile, productionEnv } from './src/config.mjs';
import { openRecords } from './src/records.mjs';
import { runAlerts, matches, wordTests } from './src/alerts.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const vars = readEnvFile(process.env.API_ENV || '/etc/hrn-api/api.env');
const env = productionEnv(vars, { serverDir: here });
const records = openRecords(vars.RECORDS_FILE || '/srv/hrn/app/data/jobs.db');
const t0 = Date.now();

if (process.argv.includes('--dry')) {
  const top = records.watermark(), due = (await env.DB.prepare("SELECT * FROM alerts WHERE status = 'active' AND due_at <= ?").bind(Math.floor(Date.now() / 1000)).all()).results;
  const since = due.map((a) => a.seen_through).filter(Boolean).sort()[0] || top;
  const fresh = since ? records.newSince(since) : [];
  console.log(JSON.stringify({ newest_record: top, due: due.length, new_jobs: fresh.length,
    letters_with_jobs: due.filter((a) => { const tests = wordTests(a.q); return fresh.some((j) => j.first_seen_at > (a.seen_through || '') && matches(a, j, tests)); }).length }));
} else {
  if (!env.MAIL) console.log('mail is off (no SMTP_PASS in the settings): nothing can be sent');
  const out = await runAlerts(env, records);
  console.log('alerts: ' + JSON.stringify(out) + ' in ' + Math.round((Date.now() - t0) / 100) / 10 + ' s');
}
env.DB.close();
