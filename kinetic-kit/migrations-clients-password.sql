-- Client passwords (owner, 16 Nov 2026: "their email and password is what will take them into the account to finish
-- paying"). The emailed one-time link stays for "Forgot your password?".
ALTER TABLE clients ADD COLUMN pw_hash TEXT;
ALTER TABLE clients ADD COLUMN failed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE clients ADD COLUMN locked_until INTEGER NOT NULL DEFAULT 0;
ALTER TABLE client_links ADD COLUMN purpose TEXT;  -- 'reset' for a forgotten password
