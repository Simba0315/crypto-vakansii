-- Jobs Every Hour API: D1 (SQLite) schema. Safe to run more than once.
-- An account. domain: the company domain it is tied to (siteDomain in worker.js), which the company site and the link to apply of
-- every job it posts as an employer must be on; empty for a job seeker or a recruiter on a free mailbox. domain_proof: how the domain
-- was proved: '' (it is the domain of the email, confirmed by a link) | dns (a TXT record) | file (a file on the site).
-- confirmed_at: when the email was confirmed (0: not yet; such an account cannot publish or buy).
-- approved_jobs: jobs of this account, posted as an employer, that a person approved; upheld_reports: reports about its jobs that
-- turned out right. Together with created_at they decide whether the account is trusted (see trusted in worker.js).
-- banned_at: when it was banned (0: never).
-- linkedin_*: the LinkedIn identity attached through Sign In with LinkedIn (OpenID Connect): the subject id LinkedIn gives this
-- application for the member, the member's name, the email LinkedIn says is verified ('' when it gave none) and when it was attached.
-- One identity, one account (the unique index below). An account with one may post for other companies as a recruiter.
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  domain TEXT NOT NULL DEFAULT '',
  domain_proof TEXT NOT NULL DEFAULT '',
  pass_hash TEXT NOT NULL,
  pass_salt TEXT NOT NULL,
  company TEXT NOT NULL DEFAULT '',
  plus_until INTEGER NOT NULL DEFAULT 0,
  banned INTEGER NOT NULL DEFAULT 0,
  banned_at INTEGER NOT NULL DEFAULT 0,
  confirmed_at INTEGER NOT NULL DEFAULT 0,
  approved_jobs INTEGER NOT NULL DEFAULT 0,
  upheld_reports INTEGER NOT NULL DEFAULT 0,
  linkedin_sub TEXT NOT NULL DEFAULT '',
  linkedin_name TEXT NOT NULL DEFAULT '',
  linkedin_email TEXT NOT NULL DEFAULT '',
  linkedin_at INTEGER NOT NULL DEFAULT 0,
  work_email TEXT NOT NULL DEFAULT '',              -- the work address confirmed by a link (domain_proof 'work_email'), for an account on a free mailbox
  created_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS users_linkedin ON users (linkedin_sub) WHERE linkedin_sub != '';   -- one LinkedIn identity, one account: a second attachment fails

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

-- Sign-in links sent by email (no password needed): the same shape as resets. Only the hash is kept; a link works once and for 15 minutes.
CREATE TABLE IF NOT EXISTS signin_links (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS signin_links_user ON signin_links (user_id);

-- Links that confirm the email of a new account: the same shape as resets. Only the hash of the token is kept; a link works once and for 24 hours.
CREATE TABLE IF NOT EXISTS confirms (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS confirms_user ON confirms (user_id);

-- A sign-in with LinkedIn that was started and has not come back yet. Only the hash of the state value is kept, with the account and
-- the session (the hash of its token) that started it: the answer from LinkedIn is taken only from that same session. One use, 15 minutes.
CREATE TABLE IF NOT EXISTS oauth_states (
  state_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  session_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);

-- A domain an account says is its company's and has not proved yet: one at a time per account. token is what the account publishes in
-- a DNS TXT record or a file on the site (it is public by its nature, so it is kept as it is); when a check finds it, users.domain is
-- set and the row goes.
CREATE TABLE IF NOT EXISTS domain_claims (
  user_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  token TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);

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
  activation TEXT NOT NULL DEFAULT '',
  credits INTEGER NOT NULL DEFAULT 0                -- prepaid credits it was paid with (then amount_usd is 0: the money came with the top-up)
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
-- posted_by: '' (the employer itself, from an account tied to the company's domain) | recruiter (an account with a LinkedIn identity,
-- for a company it is not part of: company_url is then the hiring company's site, and the link to apply is tied to that domain).
-- recruiter_name: the recruiter's name as LinkedIn gave it when the job was posted or last edited; the site shows it next to the job.
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
  posted_by TEXT NOT NULL DEFAULT '',
  recruiter_name TEXT NOT NULL DEFAULT '',
  reminded_at INTEGER NOT NULL DEFAULT 0,       -- when the letter "this job leaves the site soon" went out for its present term; 0: not yet
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
-- column: jobs reminded_at INTEGER NOT NULL DEFAULT 0
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

-- What a listing brought: views of the job page and clicks on "Apply", per job posted here and per day (UTC, "2026-11-13").
-- Two counters and nothing else: who the visitors were is not in it.
CREATE TABLE IF NOT EXISTS job_hits (
  job_id TEXT NOT NULL,
  day TEXT NOT NULL,
  views INTEGER NOT NULL DEFAULT 0,
  applies INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (job_id, day)
);
-- Who was already counted today, so that one visitor counts once a day per job for a view and once for a click. kind: view | apply.
-- ip_hash: the salted hash of the address (ipHash in worker.js). It is kept for this and for the rest of the day only: the cron
-- deletes the rows of days gone by.
CREATE TABLE IF NOT EXISTS hit_seen (
  day TEXT NOT NULL,
  job_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  ip_hash TEXT NOT NULL,
  PRIMARY KEY (day, job_id, kind, ip_hash)
);

-- Monthly counters for /api/public/transparency.json. month: "2026-11"; k: screened | screen_rejected | held.
CREATE TABLE IF NOT EXISTS stats (
  month TEXT NOT NULL,
  k TEXT NOT NULL,
  n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (month, k)
);

-- Plus: how many times an account used the AI tools in a calendar month (UTC), per group of tools: resume | letter | interview.
-- month: "2026-11". A new month is a new row, so the count starts again by itself. This is all that is kept of a request to the AI
-- tools: the resume, the posting and the answer are never stored.
CREATE TABLE IF NOT EXISTS ai_usage (
  user_id TEXT NOT NULL,
  month TEXT NOT NULL,
  grp TEXT NOT NULL,
  n INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, month, grp)
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

-- ---------------------------------------------------------------- added 15 Nov 2026: mail, job alerts, claimed company pages

-- Every letter the mailer (src/mail.js) handed to the mail server, or held back: when, to whom, what kind (confirm, reset, device,
-- alert_confirm, alert ...), the result (sent | failed | capped), how many attempts, the server's last answer and the Message-ID.
-- Never the subject or the text. Kept MAIL_LOG_DAYS (30) days; the cron deletes older rows. The daily cap is counted from it.
CREATE TABLE IF NOT EXISTS mail_log (
  id TEXT PRIMARY KEY,
  at INTEGER NOT NULL,
  to_addr TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  code INTEGER NOT NULL DEFAULT 0,
  reply TEXT NOT NULL DEFAULT '',
  message_id TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS mail_log_at ON mail_log (at, status);

-- A job alert: an address and a saved search (src/alerts.js). status: pending (the confirmation link was sent, nothing else is) |
-- active (the address confirmed it). An alert that is unsubscribed is deleted, not kept; a pending one is deleted after 7 days.
-- q: the words (title, company, skills); cat: a category slug (/jobs/<cat>/); loc: a place slug (/locations/<loc>/); remote: 1 = remote
-- jobs only; sal: the least yearly pay in US dollars (0: any; above 0 only jobs that state pay reaching it); freq: daily | weekly.
-- due_at: when it is next looked at; seen_through: the newest first_seen_at (ISO time, UTC) of the job records it was last matched
-- against, so every job is offered once. letters: how many were sent; fails: letters the mail server refused for good in a row
-- (three end the alert). Nothing about the visitor who asked is kept here (the limit on sign-ups per visitor lives in rate).
CREATE TABLE IF NOT EXISTS alerts (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  q TEXT NOT NULL DEFAULT '',
  cat TEXT NOT NULL DEFAULT '',
  loc TEXT NOT NULL DEFAULT '',
  remote INTEGER NOT NULL DEFAULT 0,
  sal INTEGER NOT NULL DEFAULT 0,
  freq TEXT NOT NULL DEFAULT 'daily',
  status TEXT NOT NULL DEFAULT 'pending',
  created_at INTEGER NOT NULL,
  confirmed_at INTEGER NOT NULL DEFAULT 0,
  due_at INTEGER NOT NULL DEFAULT 0,
  seen_through TEXT NOT NULL DEFAULT '',
  last_sent_at INTEGER NOT NULL DEFAULT 0,
  letters INTEGER NOT NULL DEFAULT 0,
  fails INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS alerts_email ON alerts (email);
CREATE INDEX IF NOT EXISTS alerts_due ON alerts (status, due_at);
CREATE UNIQUE INDEX IF NOT EXISTS alerts_same ON alerts (email, q, cat, loc, remote, sal);   -- the same search twice for one address is one alert

-- "Claim your company page": an employer account says a company the site reads from its hiring system is theirs. company_key is the
-- name as compared (companyKey), company the name as the site shows it, domain the company domain the account proved (users.domain).
-- status: pending (a person looks first) | verified | rejected. One verified claim per company (the unique index), any number of
-- pending ones. reason: why it waits (or why it was turned down, for the account to read). site: the company's own site as the site
-- knows it (logos.json), '' when unknown.
CREATE TABLE IF NOT EXISTS company_claims (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  company TEXT NOT NULL,
  company_key TEXT NOT NULL,
  domain TEXT NOT NULL,
  site TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  reason TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  decided_at INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS claims_verified ON company_claims (company_key) WHERE status = 'verified';
CREATE UNIQUE INDEX IF NOT EXISTS claims_mine ON company_claims (user_id, company_key);
CREATE INDEX IF NOT EXISTS claims_status ON company_claims (status, created_at);

-- Views and clicks on "Apply" for the jobs of a claimed company that the site reads from its hiring system, per job page (slug) and
-- day: the same two counters as job_hits, counted the same way (hit_seen, once per visitor and day). Only while the claim is verified.
CREATE TABLE IF NOT EXISTS company_hits (
  company_key TEXT NOT NULL,
  slug TEXT NOT NULL,
  day TEXT NOT NULL,
  views INTEGER NOT NULL DEFAULT 0,
  applies INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (company_key, slug, day)
);

-- ---------------------------------------------------------------- the resume database: opt-in only (15 Nov 2026)
-- A person's resume, stored only after they ticked "Let employers find my resume" (consent_text: the exact line they agreed to, and
-- when). resume: the builder's object as JSON, contact details included, which no employer sees before the person accepts its request.
-- pid: the public id employers see (never the account id). headline, level (entry | mid | senior | lead), years (as the person states
-- them), skills (lower case, one per line), roles (category slugs) and places (place slugs, "remote") are what search reads. show_name,
-- show_employers: what the person chose to show before accepting (both off by default). blocked: company domains that never see it (one
-- per line). paused: hidden from search, kept. Deleting it deletes the row and the requests about it; nothing is kept.
CREATE TABLE IF NOT EXISTS talent (
  user_id TEXT PRIMARY KEY,
  pid TEXT NOT NULL UNIQUE,
  resume TEXT NOT NULL,
  headline TEXT NOT NULL DEFAULT '',
  level TEXT NOT NULL DEFAULT '',
  years INTEGER NOT NULL DEFAULT 0,
  skills TEXT NOT NULL DEFAULT '',
  roles TEXT NOT NULL DEFAULT '',
  places TEXT NOT NULL DEFAULT '',
  show_name INTEGER NOT NULL DEFAULT 0,
  show_employers INTEGER NOT NULL DEFAULT 0,
  blocked TEXT NOT NULL DEFAULT '',
  paused INTEGER NOT NULL DEFAULT 0,
  consent_text TEXT NOT NULL,
  consented_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
-- An employer's request to contact a person in the resume database. status: sent | accepted | declined | expired (no answer in 14 days).
-- One request per employer and person, ever (a decline is final). The employer gets the person's name and email only on "accepted".
CREATE TABLE IF NOT EXISTS talent_requests (
  id TEXT PRIMARY KEY,
  employer_id TEXT NOT NULL,
  candidate_id TEXT NOT NULL,
  company TEXT NOT NULL,
  domain TEXT NOT NULL,
  message TEXT NOT NULL,
  job_url TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'sent',
  created_at INTEGER NOT NULL,
  answered_at INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS talent_requests_once ON talent_requests (employer_id, candidate_id);
CREATE INDEX IF NOT EXISTS talent_requests_candidate ON talent_requests (candidate_id, status);
CREATE INDEX IF NOT EXISTS talent_requests_open ON talent_requests (status, created_at);
-- Contact requests an employer can send: bought as a one-time pack (nothing renews) or given by the owner. A request takes one when it
-- is sent and gives it back when the person declines or does not answer in 14 days: an employer pays only for people who said yes.
CREATE TABLE IF NOT EXISTS talent_credits (
  user_id TEXT PRIMARY KEY,
  n INTEGER NOT NULL DEFAULT 0
);

-- ---------------------------------------------------------------- sign-in with Google, teams, company pages (15 Nov 2026)
-- New tables only, so a database made by an earlier install needs no change.
-- A way to sign in other than the password: provider 'google' and the subject id it gives this application, with the address it
-- verified and the name. One identity, one account; an account has at most one per provider.
CREATE TABLE IF NOT EXISTS identities (
  provider TEXT NOT NULL,
  sub TEXT NOT NULL,
  user_id TEXT NOT NULL,
  email TEXT NOT NULL DEFAULT '',
  name TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  PRIMARY KEY (provider, sub)
);
CREATE UNIQUE INDEX IF NOT EXISTS identities_user ON identities (user_id, provider);
-- A sign-in with Google that was started: the hash of the state and of the secret the page keeps, one use, 15 minutes. The secret is
-- what stops a stranger from signing someone into the stranger's account (login CSRF): only the page that started it holds it.
CREATE TABLE IF NOT EXISTS signin_states (
  state_hash TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  secret_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
-- Colleagues an employer account lets post under its company names: addresses on the same company domain. They post from their own
-- accounts, which go through the same checks (a new account's jobs are looked at by a person).
CREATE TABLE IF NOT EXISTS team_members (
  owner_id TEXT NOT NULL,
  email TEXT NOT NULL,
  added_at INTEGER NOT NULL,
  role TEXT NOT NULL DEFAULT 'member',              -- 'owner': may also manage the team, the company page and buy for the company; 'member': posts under the name
  PRIMARY KEY (owner_id, email)
);
CREATE INDEX IF NOT EXISTS team_email ON team_members (email);
-- What a company that claimed its page says about itself, for the site's company page: a short text and its site.
CREATE TABLE IF NOT EXISTS company_pages (
  company_key TEXT PRIMARY KEY,
  about TEXT NOT NULL DEFAULT '',
  website TEXT NOT NULL DEFAULT '',
  logo TEXT NOT NULL DEFAULT '',                    -- a media id (the company's own logo, uploaded in the account)
  locations TEXT NOT NULL DEFAULT '',               -- where it hires, one place per line, as the company writes them
  updated_by TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

-- ---------------------------------------------------------------- the paid products of 15 Nov 2026 (see PRODUCTS in src/worker.js)
-- Columns added to tables that may already exist in a database made from an earlier schema.sql: applySchema (src/d1.mjs) reads these
-- lines and adds a column that is missing. On Cloudflare D1 run the same as ALTER TABLE ... ADD COLUMN by hand.
-- column: orders credits INTEGER NOT NULL DEFAULT 0
-- column: users work_email TEXT NOT NULL DEFAULT ''
-- column: team_members role TEXT NOT NULL DEFAULT 'member'
-- column: company_pages logo TEXT NOT NULL DEFAULT ''
-- column: company_pages locations TEXT NOT NULL DEFAULT ''

-- Prepaid credits (1 credit = US$1): one lot per top-up, spent oldest-expiring first, each lot good for 12 months. A purchase paid with
-- credits says how many in orders.credits. wallets.version changes with every top-up and every spend, so a spend planned on a balance
-- that changed meanwhile is refused and planned again (see walletPlan in src/worker.js).
CREATE TABLE IF NOT EXISTS wallet_lots (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  order_id TEXT NOT NULL,
  credits INTEGER NOT NULL,
  remaining INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS wallet_lots_order ON wallet_lots (order_id);   -- one top-up, one lot
CREATE INDEX IF NOT EXISTS wallet_lots_user ON wallet_lots (user_id, expires_at);
CREATE TABLE IF NOT EXISTS wallets (
  user_id TEXT PRIMARY KEY,
  version INTEGER NOT NULL DEFAULT 0
);
-- A Hiring Pass: one company, 30 days, Standard boosts of its jobs free while it runs, a number of Premium boosts.
CREATE TABLE IF NOT EXISTS passes (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  order_id TEXT NOT NULL,
  company_key TEXT NOT NULL,
  company TEXT NOT NULL,
  starts_at INTEGER NOT NULL,
  ends_at INTEGER NOT NULL,
  premium_left INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS passes_order ON passes (order_id);
CREATE INDEX IF NOT EXISTS passes_company ON passes (company_key, ends_at);
-- Single AI passes for job seekers: one tailored resume (tailor + cover letter) or one mock interview (questions + feedback).
CREATE TABLE IF NOT EXISTS ai_passes (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  order_id TEXT NOT NULL,
  kind TEXT NOT NULL,                               -- 'resume' | 'interview'
  main_left INTEGER NOT NULL,                       -- tailor / questions
  extra_left INTEGER NOT NULL,                      -- cover letter / feedback on answers
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ai_passes_order ON ai_passes (order_id);
CREATE INDEX IF NOT EXISTS ai_passes_user ON ai_passes (user_id, expires_at);
-- The free re-run: each paid boost is looked at once, 14 days after it started (applies: clicks on Apply counted in those days).
CREATE TABLE IF NOT EXISTS reruns (
  placement_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  applies INTEGER NOT NULL,
  given_order TEXT NOT NULL DEFAULT '',             -- the order of the free run, '' when none was due
  checked_at INTEGER NOT NULL
);
-- Views and clicks on "Apply" of a job read from a hiring system while a boost on it runs (for the buyer's stats and the re-run).
CREATE TABLE IF NOT EXISTS boost_hits (
  slug TEXT NOT NULL,
  day TEXT NOT NULL,
  views INTEGER NOT NULL DEFAULT 0,
  applies INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (slug, day)
);
-- Job invitations: a job seeker who opted in gets at most one letter about one Premium job every few days.
CREATE TABLE IF NOT EXISTS invite_prefs (
  user_id TEXT PRIMARY KEY,
  roles TEXT NOT NULL DEFAULT '',                   -- category slugs, one per line ('' = any)
  places TEXT NOT NULL DEFAULT '',                  -- place slugs, one per line ('' = any)
  remote INTEGER NOT NULL DEFAULT 0,                -- 1: remote jobs count wherever they are
  paused INTEGER NOT NULL DEFAULT 0,
  consent_text TEXT NOT NULL,
  consented_at INTEGER NOT NULL,
  last_at INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS invites (
  placement_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  sent_at INTEGER NOT NULL,
  PRIMARY KEY (placement_id, user_id)
);
CREATE TABLE IF NOT EXISTS invite_runs (
  placement_id TEXT PRIMARY KEY,
  sent INTEGER NOT NULL,
  at INTEGER NOT NULL
);
-- Images an employer uploads: a company logo, a cover for a Premium job. PNG, JPEG or WebP only (never SVG), served by
-- /api/public/media/<id> with their own type.
CREATE TABLE IF NOT EXISTS media (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  kind TEXT NOT NULL,                               -- 'logo' | 'cover'
  type TEXT NOT NULL,                               -- image/png | image/jpeg | image/webp
  data TEXT NOT NULL,                               -- base64
  bytes INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS media_user ON media (user_id);
CREATE TABLE IF NOT EXISTS listing_media (
  target TEXT PRIMARY KEY,                          -- 'direct:<job id>' or 'job:<slug>', as in placements
  user_id TEXT NOT NULL,
  cover TEXT NOT NULL DEFAULT '',                   -- a media id
  updated_at INTEGER NOT NULL
);
-- Resumes kept in the account: several versions, each the builder's object (hrn_resume) with a name the person gives it.
CREATE TABLE IF NOT EXISTS resumes (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS resumes_user ON resumes (user_id, updated_at);

-- A link to a work address, asked for by an account on a free mailbox to be tied to its company's domain (workEmailRequest in
-- src/worker.js); one per account, 24 hours, only the hash of its token is kept.
CREATE TABLE IF NOT EXISTS work_links (
  token_hash TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  email TEXT NOT NULL,
  domain TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS work_links_user ON work_links (user_id);

-- The site's own visit statistics (ev and statsReport in src/worker.js): anonymous, no cookies, no IP address, no user agent.
-- A visit is a random id a browser tab keeps until it is closed; it starts after the first move, scroll, touch or 15 seconds on the page.
CREATE TABLE IF NOT EXISTS visits (
  id TEXT PRIMARY KEY,
  day TEXT NOT NULL,                                -- YYYY-MM-DD, UTC
  ts INTEGER NOT NULL,
  src TEXT NOT NULL DEFAULT '',                     -- where it came from, named for the report (Google, ChatGPT, a site's host, direct)
  ref TEXT NOT NULL DEFAULT '',                     -- the referring host only
  entry TEXT NOT NULL DEFAULT '',                   -- the first page
  country TEXT NOT NULL DEFAULT '',                 -- two letters, from Cloudflare's CF-IPCountry
  device TEXT NOT NULL DEFAULT '',
  os TEXT NOT NULL DEFAULT '',
  app TEXT NOT NULL DEFAULT '',                     -- browser | app (installed) | embed
  lang TEXT NOT NULL DEFAULT '',
  utm TEXT NOT NULL DEFAULT ''                      -- source / medium / campaign
);
CREATE INDEX IF NOT EXISTS visits_day ON visits (day);
CREATE TABLE IF NOT EXISTS events (
  visit TEXT NOT NULL,
  day TEXT NOT NULL,
  ts INTEGER NOT NULL,
  kind TEXT NOT NULL,                               -- pv | apply | search | pick | btn | out | alert | resume
  path TEXT NOT NULL,
  a TEXT NOT NULL DEFAULT '',
  b TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS events_day ON events (day, kind);
CREATE INDEX IF NOT EXISTS events_visit ON events (visit, kind);
