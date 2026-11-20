-- Client accounts (owner, 16 Nov 2026: "do a sign up either a Google sign up or sign in with email before allowing
-- people to buy"). Clients sign in with a one-time email link or Google; there are no client passwords.
CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,     -- lower-case
  name TEXT,
  google_sub TEXT,                -- Google account id, when they signed in with Google
  created_at INTEGER NOT NULL,
  last_login INTEGER
);
CREATE TABLE IF NOT EXISTS client_sessions (
  id TEXT PRIMARY KEY,            -- sha256 of the cookie token
  client_id INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS client_sessions_client ON client_sessions (client_id);
CREATE TABLE IF NOT EXISTS client_links (
  id TEXT PRIMARY KEY,            -- sha256 of the emailed token
  email TEXT NOT NULL,
  next TEXT,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  used_at INTEGER
);
CREATE INDEX IF NOT EXISTS client_links_email ON client_links (email, created_at);
