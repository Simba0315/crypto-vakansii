// The API on our own server (Hostinger, next to the page server): the worker of src/worker.js on Node 22, with its database in a file
// (node:sqlite through the D1 stand-in of src/d1.mjs) and mail through the SMTP client of src/mail.js.
//
//   node server/prod.mjs                    settings from /srv/hrn/api.env (API_ENV=... for another file)
//
// It listens on 127.0.0.1:8787 only; nginx hands it the API's own addresses (server/hosting/nginx-hrn-api.conf) and sets
// CF-Connecting-IP to the visitor's address. Payments are off until the owner writes PAYMENTS_LIVE=1 and the keys into the settings
// (src/config.mjs). Every ten minutes it runs the worker's cron. hrn-api.service keeps it running.
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import worker from './src/worker.js';
import { readEnvFile, productionEnv, describeEnv } from './src/config.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const vars = readEnvFile(process.env.API_ENV || '/srv/hrn/api.env');
const HOST = vars.HOST || '127.0.0.1', PORT = Number(vars.PORT) || 8787, MAX_BODY = 65536;
let env;
try { env = productionEnv(vars, { serverDir: here }); } catch (err) { console.error('not started: ' + err.message); process.exit(1); }

// The worker's ctx: a letter is sent after the answer has gone (waitUntil); on shutdown the letters under way are waited for.
const pending = new Set();
const ctx = { waitUntil: (p) => { const done = Promise.resolve(p).catch(() => {}).finally(() => pending.delete(done)); pending.add(done); } };

const server = http.createServer(async (req, res) => {
  const chunks = []; let size = 0;
  try {
    for await (const c of req) { size += c.length; if (size > MAX_BODY) { res.writeHead(413, { 'Content-Type': 'application/json' }); res.end('{"error":"too_large"}'); req.destroy(); return; } chunks.push(c); }
    const headers = {};
    for (const [k, v] of Object.entries(req.headers)) if (!['host', 'connection', 'content-length', 'transfer-encoding'].includes(k)) headers[k] = String(v);
    const hasBody = !['GET', 'HEAD'].includes(req.method) && chunks.length;
    const r = await worker.fetch(new Request(env.API_URL + req.url, { method: req.method, headers, body: hasBody ? Buffer.concat(chunks) : undefined }), env, ctx);
    res.writeHead(r.status, Object.fromEntries(r.headers));
    res.end(req.method === 'HEAD' ? undefined : Buffer.from(await r.arrayBuffer()));
  } catch (err) {
    console.error('request failed: ' + (err && err.stack ? err.stack.split('\n').slice(0, 3).join(' | ') : err));
    if (!res.headersSent) { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end('{"error":"server"}'); }
  }
});
server.requestTimeout = 30000; server.headersTimeout = 15000; server.keepAliveTimeout = 5000;
server.listen(PORT, HOST, () => console.log('API on http://' + HOST + ':' + PORT + ': ' + describeEnv(env)));

// the cron of wrangler.toml ("*/10 * * * *"): settle orders, recheck links of live jobs, tidy up
const cron = async () => { try { await worker.scheduled({}, env); } catch (err) { console.error('cron failed: ' + (err && err.message)); } };
setTimeout(cron, 30000).unref();
setInterval(cron, 600000).unref();

const stop = async (sig) => {
  console.log(sig + ': stopping');
  server.close();
  await Promise.race([Promise.all([...pending]), new Promise((r) => setTimeout(r, 20000))]);
  try { env.DB.close(); } catch {}
  process.exit(0);
};
process.on('SIGTERM', () => stop('SIGTERM'));
process.on('SIGINT', () => stop('SIGINT'));
