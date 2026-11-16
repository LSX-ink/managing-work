-- Change requests from signed-in clients (owner, 16 Nov 2026: "once signed in there's change requests").
CREATE TABLE IF NOT EXISTS change_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id INTEGER NOT NULL,
  email TEXT NOT NULL,
  website TEXT,
  kind TEXT,                      -- wording, pictures, design, new page, other
  details TEXT NOT NULL,
  links TEXT,                     -- links to photos or examples they want used
  status TEXT NOT NULL DEFAULT 'received',   -- received, in progress, done
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS change_requests_client ON change_requests (client_id, created_at);
CREATE INDEX IF NOT EXISTS change_requests_status ON change_requests (status, created_at);
