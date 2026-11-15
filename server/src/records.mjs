// The job records (data/jobs.db, written by records.py in every hourly build) as the alert job reads them: read-only, opened for one
// run and closed, so the hourly upload can put a new file in place at any time.
import { DatabaseSync } from 'node:sqlite';
import { existsSync } from 'node:fs';

const FIELDS = ['slug', 'title', 'company', 'location', 'remote', 'salary', 'usd', 'places', 'cat', 'tags', 'first_seen_at', 'tg'];

export function openRecords(path) {
  const open = () => (existsSync(path) ? new DatabaseSync(path, { readOnly: true }) : null);
  return {
    // the newest first_seen_at among the records ('' when there are none); first_seen is the day of it, so only the last day is read
    watermark() {
      const db = open(); if (!db) return '';
      try {
        const row = db.prepare("SELECT MAX(json_extract(rec, '$.first_seen_at')) AS t FROM jobs WHERE first_seen = (SELECT MAX(first_seen) FROM jobs)").get();
        return (row && row.t) || '';
      } finally { db.close(); }
    },
    // the open jobs first seen after a moment (ISO time, UTC): the day is narrowed in SQL, the moment here
    newSince(iso) {
      const db = open(); if (!db) return [];
      try {
        const out = [];
        for (const { rec } of db.prepare('SELECT rec FROM jobs WHERE active = 1 AND first_seen >= ?').all(String(iso).slice(0, 10))) {
          let j; try { j = JSON.parse(rec); } catch { continue; }
          if (!j.first_seen_at || j.first_seen_at <= iso) continue;
          out.push(Object.fromEntries(FIELDS.map((k) => [k, j[k]])));
        }
        return out;
      } finally { db.close(); }
    },
  };
}
