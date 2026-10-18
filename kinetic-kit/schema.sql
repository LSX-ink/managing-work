-- Kinetic kit: D1 schema for a client site's owner area.
-- Apply with:  npx wrangler d1 execute <db-name> --remote --file schema.sql
-- Safe to run again: every statement is IF NOT EXISTS.

-- Owner logins. Passwords are never stored, only PBKDF2-SHA256 hashes:
--   pbkdf2-sha256$<iterations>$<salt base64>$<hash base64>
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
  pw_hash       TEXT NOT NULL,
  must_change   INTEGER NOT NULL DEFAULT 1,   -- 1 = still on a temporary password
  failed        INTEGER NOT NULL DEFAULT 0,   -- failed logins in a row
  locked_until  INTEGER NOT NULL DEFAULT 0,   -- ms epoch; 0 = not locked
  opted_out     INTEGER NOT NULL DEFAULT 0,   -- 1 = no monthly statement emails
  opted_out_at  INTEGER,
  stop_token    TEXT NOT NULL DEFAULT (lower(hex(randomblob(16)))), -- for the one-click STOP link
  created_at    INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER) * 1000),
  pw_changed_at INTEGER
);

-- Sessions: the cookie holds a random token; only its SHA-256 is stored here.
CREATE TABLE IF NOT EXISTS sessions (
  id          TEXT PRIMARY KEY,               -- sha256(token), hex
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  INTEGER NOT NULL,
  expires_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);

-- Shop: product lists ("New in", "Outerwear") and products.
CREATE TABLE IF NOT EXISTS lists (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  title  TEXT NOT NULL,
  sort   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS products (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  list_id     INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  price_pence INTEGER NOT NULL DEFAULT 0,
  img_key     TEXT,                             -- R2 object key
  in_stock    INTEGER NOT NULL DEFAULT 1,       -- the owner's switch
  visible     INTEGER NOT NULL DEFAULT 1,       -- 0 = hidden from the website
  sizes       TEXT NOT NULL DEFAULT '[]',       -- JSON [{id,label,qty,show}]
  sort        INTEGER NOT NULL DEFAULT 0,
  created_at  INTEGER NOT NULL,
  updated_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS products_list ON products(list_id);

-- Editable website text. Kinetic adds the fields a site has; the owner edits the values.
CREATE TABLE IF NOT EXISTS texts (
  key        TEXT PRIMARY KEY,                -- matches data-kit-text="key" on the site
  label      TEXT NOT NULL,
  value      TEXT NOT NULL DEFAULT '',
  multiline  INTEGER NOT NULL DEFAULT 0,
  sort       INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER
);

-- Analytics. No cookies and no IP addresses: visitor is sha256(daily salt + IP + user agent),
-- and the salt is thrown away after two days, so the same person can't be linked across days.
CREATE TABLE IF NOT EXISTS pageviews (
  id       INTEGER PRIMARY KEY AUTOINCREMENT,
  ts       INTEGER NOT NULL,                  -- ms epoch
  path     TEXT NOT NULL,
  ref_host TEXT,                              -- referrer host only, NULL when direct
  visitor  TEXT NOT NULL,
  device   TEXT                               -- phone / tablet / computer
);
CREATE INDEX IF NOT EXISTS pageviews_ts ON pageviews(ts);

CREATE TABLE IF NOT EXISTS events (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  ts      INTEGER NOT NULL,
  name    TEXT NOT NULL,                      -- e.g. signup, quote
  path    TEXT,
  visitor TEXT
);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS salts (
  day  TEXT PRIMARY KEY,                      -- YYYY-MM-DD (UTC)
  salt TEXT NOT NULL
);

-- Payments and refunds, written only by the Stripe webhook. Amounts in minor units (pence).
CREATE TABLE IF NOT EXISTS payments (
  id          TEXT PRIMARY KEY,               -- Stripe charge id (ch_...) or refund id (re_...)
  kind        TEXT NOT NULL,                  -- payment | refund
  status      TEXT NOT NULL,                  -- succeeded | pending | failed | canceled
  amount      INTEGER NOT NULL,               -- always positive
  currency    TEXT NOT NULL,
  description TEXT,
  customer    TEXT,                           -- billing name, if Stripe has one
  charge_id   TEXT,                           -- for refunds: the charge refunded
  created     INTEGER NOT NULL,               -- ms epoch
  livemode    INTEGER NOT NULL DEFAULT 0,
  updated     INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS payments_created ON payments(created);

-- Stripe event ids already handled (Stripe can deliver an event more than once).
CREATE TABLE IF NOT EXISTS stripe_events (
  id       TEXT PRIMARY KEY,
  type     TEXT NOT NULL,
  received INTEGER NOT NULL
);

-- Monthly statements already sent, so a retried cron never sends twice.
CREATE TABLE IF NOT EXISTS statements_sent (
  user_id  INTEGER NOT NULL,
  month    TEXT NOT NULL,                     -- YYYY-MM
  sent_at  INTEGER NOT NULL,
  PRIMARY KEY (user_id, month)
);
