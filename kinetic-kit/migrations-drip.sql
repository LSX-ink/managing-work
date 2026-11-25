-- Follow-up email series ("drip") for sign-ups who ticked marketing consent.
-- Run once on a database made before the series existed:
--   npx wrangler d1 execute <db-name> --remote --file migrations-drip.sql
ALTER TABLE signups ADD COLUMN drip_step INTEGER NOT NULL DEFAULT 0;   -- last follow-up sent (0 = only the welcome)
ALTER TABLE signups ADD COLUMN drip_last_at INTEGER;                   -- ms epoch of the last follow-up
ALTER TABLE signups ADD COLUMN drip_stopped TEXT;                      -- why the series stopped: unsubscribed | brief | paid | owner | done
