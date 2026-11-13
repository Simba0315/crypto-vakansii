// A stand-in for Cloudflare D1 on top of Node's built-in SQLite, so the worker can run and be tested on any machine with Node 22+.
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
  constructor(file = ':memory:') { this.sqlite = new DatabaseSync(file); }
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
}
