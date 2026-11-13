-- Hiring Right Now API: D1 (SQLite) schema. Safe to run more than once.
-- An employer account. domain: the registrable domain of the email (siteDomain in worker.js), which the company site and the link to
-- apply of every job must be on. confirmed_at: when the email was confirmed (0: not yet; such an account cannot publish or buy).
-- approved_jobs: jobs of this account a person approved; upheld_reports: reports about its jobs that turned out right. Together with
-- created_at they decide whether the account is trusted (see trusted in worker.js). banned_at: when it was banned (0: never).
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  domain TEXT NOT NULL DEFAULT '',
  pass_hash TEXT NOT NULL,
  pass_salt TEXT NOT NULL,
  company TEXT NOT NULL DEFAULT '',
  plus_until INTEGER NOT NULL DEFAULT 0,
  banned INTEGER NOT NULL DEFAULT 0,
  banned_at INTEGER NOT NULL DEFAULT 0,
  confirmed_at INTEGER NOT NULL DEFAULT 0,
  approved_jobs INTEGER NOT NULL DEFAULT 0,
  upheld_reports INTEGER NOT NULL DEFAULT 0,
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

-- Links that confirm the email of a new account: the same shape as resets. Only the hash of the token is kept; a link works once and for 24 hours.
CREATE TABLE IF NOT EXISTS confirms (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS confirms_user ON confirms (user_id);

-- The browsers an account has signed in from: a hash of the account and the User-Agent (version numbers left out), nothing else.
-- A sign-in that adds a row here is "a new device" and the owner of the address is told.
CREATE TABLE IF NOT EXISTS devices (
  user_id TEXT NOT NULL,
  ua_hash TEXT NOT NULL,
  first_seen INTEGER NOT NULL,
  PRIMARY KEY (user_id, ua_hash)
);

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
-- held = 1: bought for a job that waits for review. Its days do not run: starts_at and ends_at are then seconds counted from zero
-- (where it stands and what is left), and become moments again when the job is approved (holdPlacements, releasePlacements in worker.js).
CREATE TABLE IF NOT EXISTS placements (
  id TEXT PRIMARY KEY,
  order_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  target TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  starts_at INTEGER NOT NULL,
  ends_at INTEGER NOT NULL,
  cancelled INTEGER NOT NULL DEFAULT 0,
  held INTEGER NOT NULL DEFAULT 0
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

-- Jobs posted here by employers whose careers page is not in the index.
-- status: live | review (held until a person has looked; not exported, not on the site) | closed | rejected (a person turned it down) |
--         removed (deleted by the employer or taken down). Only "live" leaves this service.
-- company is the name as shown, company_key the name as compared (companies.k); title_key the title as compared (the same job twice);
-- slug the page of the job on the site (reports name a job by it); apply_host where the link to apply ended when it was last checked.
-- review_reason: why it waits for a person (kept while it waits, also on a job closed meanwhile; emptied by approval).
-- reject_reason: what the owner told the employer. held_at: when it last went to review; approved_at: when it first went live;
-- ended_at: when it was removed or rejected; checked_at: when the link was last opened (the daily recheck).
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
  title_key TEXT NOT NULL DEFAULT '',
  slug TEXT NOT NULL DEFAULT '',
  apply_host TEXT NOT NULL DEFAULT '',
  review_reason TEXT NOT NULL DEFAULT '',
  reject_reason TEXT NOT NULL DEFAULT '',
  held_at INTEGER NOT NULL DEFAULT 0,
  approved_at INTEGER NOT NULL DEFAULT 0,
  ended_at INTEGER NOT NULL DEFAULT 0,
  checked_at INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_user ON jobs (user_id);
CREATE INDEX IF NOT EXISTS jobs_company ON jobs (company_key);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status, checked_at);
CREATE INDEX IF NOT EXISTS jobs_slug ON jobs (slug);

-- Reports from job seekers (no account). job_id: a job posted here, or '' with slug: the page of a job read from a hiring system.
-- reason: asks_for_money | asks_to_install | moved_to_chat | impersonation | job_not_real | other. note: up to 500 characters.
-- ip_hash: a salted hash of the sender's address, kept only so that one address counts once per job and can be rate limited.
-- decision: '' (open) | upheld | dismissed, with the time it was made.
CREATE TABLE IF NOT EXISTS reports (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL DEFAULT '',
  slug TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  ip_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  decision TEXT NOT NULL DEFAULT '',
  decided_at INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS reports_once ON reports (job_id, slug, ip_hash);   -- one address, one report per job: a second one changes nothing
CREATE INDEX IF NOT EXISTS reports_open ON reports (decided_at, created_at);

-- Monthly counters for /api/public/transparency.json. month: "2026-11"; k: screened | screen_rejected | held.
CREATE TABLE IF NOT EXISTS stats (
  month TEXT NOT NULL,
  k TEXT NOT NULL,
  n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (month, k)
);

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
