// Runs the API on this machine for trying the whole flow without Cloudflare:  node --no-warnings server/dev.mjs
// Payments are simulated (PAY_MODE=test): opening the "payment link" marks the order as paid. Data lives in memory unless DB_FILE is set.
// There is no mailbox either: a sign-up answers with confirm_token (send it to POST /api/auth/confirm), a password reset with its token.
// The owner's token for /api/admin/... is "dev-admin".
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import worker from './src/worker.js';
import { D1 } from './test/d1.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8787), SITE = process.env.SITE_URL || 'http://localhost:8765/crypto-vakansii';
const env = {
  DB: new D1(process.env.DB_FILE || ':memory:').applySchema(path.join(here, 'schema.sql')),
  SITE_URL: SITE, SITE_ORIGINS: new URL(SITE).origin, API_URL: 'http://localhost:' + PORT, PAY_MODE: 'test', ADMIN_TOKEN: 'dev-admin', PLUS_LIVE: '0',
};
http.createServer(async (req, res) => {
  const chunks = []; for await (const c of req) chunks.push(c);
  const headers = {}; for (const [k, v] of Object.entries(req.headers)) if (!['host', 'connection', 'content-length'].includes(k)) headers[k] = String(v);
  const hasBody = !['GET', 'HEAD'].includes(req.method) && chunks.length;
  try {
    const r = await worker.fetch(new Request('http://localhost:' + PORT + req.url, { method: req.method, headers, body: hasBody ? Buffer.concat(chunks) : undefined }), env);
    res.writeHead(r.status, Object.fromEntries(r.headers)); res.end(Buffer.from(await r.arrayBuffer()));
  } catch (err) { console.error(err); res.writeHead(500); res.end('dev server error'); }
}).listen(PORT, () => console.log('API (test mode) on http://localhost:' + PORT + ' for site ' + SITE));
setInterval(() => worker.scheduled({}, env).catch(() => {}), 600000).unref();
