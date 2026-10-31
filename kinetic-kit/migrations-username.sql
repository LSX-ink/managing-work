-- One-off for a database made before logins used usernames (run once, BEFORE schema.sql):
--   npx wrangler d1 execute <db-name> --remote --file migrations-username.sql
-- Then give the owner a username with tools/owner-password.mjs.
ALTER TABLE users ADD COLUMN username TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(username);
