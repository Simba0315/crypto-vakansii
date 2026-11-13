-- Hiring Right Now API: D1 (SQLite) schema. Safe to run more than once.
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  pass_hash TEXT NOT NULL,
  pass_salt TEXT NOT NULL,
  company TEXT NOT NULL DEFAULT '',
  plus_until INTEGER NOT NULL DEFAULT 0,
  banned INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions (user_id);

-- Password reset links. Only the hash of the token is kept; a link works once (its row is deleted when it is used) and for 30 minutes.
CREATE TABLE IF NOT EXISTS resets (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS resets_user ON resets (user_id);

-- A purchase. status: pending -> paid | expired | failed | underpaid | refunded
-- activation: the mark of the one call that switched the order on (see activate in worker.js); empty until it is paid.
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  product TEXT NOT NULL,
  target TEXT NOT NULL DEFAULT '{}',
  label TEXT NOT NULL DEFAULT '',
  amount_usd INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  provider TEXT NOT NULL DEFAULT '',
  provider_uuid TEXT NOT NULL DEFAULT '',
  pay_url TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  paid_at INTEGER NOT NULL DEFAULT 0,
  checked_at INTEGER NOT NULL DEFAULT 0,
  activation TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS orders_user ON orders (user_id, created_at);
CREATE INDEX IF NOT EXISTS orders_open ON orders (status, created_at);

-- What a paid order switched on. kind: featured | pinned | spotlight | sponsor
-- target: "job:<slug>" (a job from the index), "direct:<job id>" (posted here), "company:<name>", "skill:<slug>|<company>", "category:<slug>|<company>"
CREATE TABLE IF NOT EXISTS placements (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  target TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  starts_at INTEGER NOT NULL,
  ends_at INTEGER NOT NULL,
  cancelled INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS placements_user ON placements (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS placements_order ON placements (order_id);   -- one order, one placement: a second write fails instead of doubling
CREATE INDEX IF NOT EXISTS placements_live ON placements (ends_at);

-- Prepaid featured listings from a pack.
CREATE TABLE IF NOT EXISTS credits (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  order_id TEXT NOT NULL,
  remaining INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS credits_user ON credits (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS credits_order ON credits (order_id);         -- one pack order, one row of credits

-- Company names taken by accounts that post jobs here: one name, one account. k is the name as compared (companyKey in worker.js:
-- lower case, single spaces, no punctuation at the end), name is the name as first written, which every job of that company carries.
CREATE TABLE IF NOT EXISTS companies (
  k TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  user_id TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS companies_user ON companies (user_id);

-- Jobs posted here by employers whose careers page is not in the index. status: live | closed | removed (deleted by the employer or taken down)
-- company is the name as shown, company_key the name as compared (companies.k).
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  company TEXT NOT NULL,
  company_key TEXT NOT NULL DEFAULT '',
  company_url TEXT NOT NULL,
  title TEXT NOT NULL,
  apply_url TEXT NOT NULL,
  location TEXT NOT NULL DEFAULT '',
  remote INTEGER NOT NULL DEFAULT 0,
  salary TEXT NOT NULL DEFAULT '',
  etype TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'live',
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_user ON jobs (user_id);
CREATE INDEX IF NOT EXISTS jobs_company ON jobs (company_key);

-- Plus: saved jobs, statuses, notes and searches synced between devices.
CREATE TABLE IF NOT EXISTS sync (
  user_id TEXT PRIMARY KEY,
  data TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rate (
  k TEXT PRIMARY KEY,
  n INTEGER NOT NULL,
  reset_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
