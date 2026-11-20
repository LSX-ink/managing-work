-- Keep the payer's email from Stripe, so paying customers stop getting the follow-up series.
--   npx wrangler d1 execute <db-name> --remote --file migrations-payment-email.sql
ALTER TABLE payments ADD COLUMN email TEXT;
CREATE INDEX IF NOT EXISTS payments_email ON payments(email);
