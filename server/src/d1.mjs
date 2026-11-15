// A stand-in for Cloudflare D1 on top of Node's built-in SQLite (node:sqlite, Node 22+), so the worker runs on our own server
// (server/prod.mjs), on a developer machine (server/dev.mjs) and in the tests, with the same SQL.
//
// On a file the database is opened in WAL mode: readers never wait for the writer, and two programs can share it. The API
// (hrn-api.service) and the alert job (hrn-alerts.service) both write to /srv/hrn/api/data/api.db; when one is writing, the other
// waits up to busy_timeout milliseconds instead of failing. Statements run synchronously, so nothing of another request can run in
// the middle of a batch (see batch).
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';

class Statement {
  constructor(sqlite, sql, args = []) { this.sqlite = sqlite; this.sql = sql; this.args = args; }
  bind(...args) { return new Statement(this.sqlite, this.sql, args); }
  async first(column) {
    const row = this.sqlite.prepare(this.sql).get(...this.args);
    if (!row) return null;
    return column ? row[column] : { ...row };
  }
  async all() { return { results: this.sqlite.prepare(this.sql).all(...this.args).map((r) => ({ ...r })), success: true, meta: {} }; }
  runNow() {
    const r = this.sqlite.prepare(this.sql).run(...this.args);
    return { success: true, results: [], meta: { changes: Number(r.changes), last_row_id: Number(r.lastInsertRowid) } };
  }
  async run() { return this.runNow(); }
}

export class D1 {
  // file: ':memory:' or a path. busyMs: how long a write waits for another program's write to finish.
  constructor(file = ':memory:', { busyMs = 5000 } = {}) {
    this.sqlite = new DatabaseSync(file);
    if (file !== ':memory:') this.sqlite.exec('PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA busy_timeout = ' + Math.max(0, Number(busyMs) | 0) + ';');
  }
  prepare(sql) { return new Statement(this.sqlite, sql); }
  // Like D1's batch: one transaction, all of it or none of it. Nothing is awaited between BEGIN and COMMIT, so no other request's
  // statement can run in the middle of it (with an await there, two requests in flight would share one open transaction).
  async batch(statements) {
    this.sqlite.exec('BEGIN IMMEDIATE');
    try { const out = statements.map((s) => s.runNow()); this.sqlite.exec('COMMIT'); return out; }
    catch (err) { this.sqlite.exec('ROLLBACK'); throw err; }
  }
  async exec(sql) { this.sqlite.exec(sql); }
  applySchema(path) { this.sqlite.exec(readFileSync(path, 'utf8')); return this; }
  close() { this.sqlite.close(); }
}
