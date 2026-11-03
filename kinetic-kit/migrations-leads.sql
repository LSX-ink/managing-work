-- Sign-ups (the email gate on the site) and briefs (the "start your website" form).
-- Safe to run again: every statement is IF NOT EXISTS. Also included in schema.sql.
--   npx wrangler d1 execute <db-name> --remote --file migrations-leads.sql

CREATE TABLE IF NOT EXISTS signups (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  email       TEXT NOT NULL UNIQUE COLLATE NOCASE,
  marketing   INTEGER NOT NULL DEFAULT 0,   -- 1 = ticked "send me tips, offers and news"
  created_at  INTEGER NOT NULL,             -- ms epoch, first sign-up
  updated_at  INTEGER NOT NULL,             -- ms epoch, last time they signed up again
  welcomed_at INTEGER,                      -- ms epoch the confirmation email was sent; NULL = not sent
  visitor     TEXT,                         -- daily visitor hash (rate limiting only)
  unsub_token TEXT NOT NULL DEFAULT (lower(hex(randomblob(16))))  -- for the unsubscribe link
);
CREATE INDEX IF NOT EXISTS signups_created ON signups(created_at);
CREATE INDEX IF NOT EXISTS signups_visitor ON signups(visitor, updated_at);

CREATE TABLE IF NOT EXISTS briefs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at  INTEGER NOT NULL,
  name        TEXT NOT NULL,
  business    TEXT NOT NULL,
  email       TEXT NOT NULL,
  phone       TEXT,
  data        TEXT NOT NULL,                -- the whole brief as JSON
  notified_at INTEGER,                      -- ms epoch the owner was emailed; NULL = not sent
  visitor     TEXT
);
CREATE INDEX IF NOT EXISTS briefs_created ON briefs(created_at);
CREATE INDEX IF NOT EXISTS briefs_visitor ON briefs(visitor, created_at);
