-- Hosting-and-care subscriptions (owner, 15 Nov 2026: "track which websites unsubscribe so we stop making
-- changes for them"). Filled by /api/stripe/webhook from checkout.session.completed and customer.subscription.*.
CREATE TABLE IF NOT EXISTS subscriptions (
  id TEXT PRIMARY KEY,            -- Stripe subscription id (sub_...)
  customer TEXT,                  -- Stripe customer id (cus_...)
  email TEXT,
  name TEXT,
  website TEXT,                   -- from the Payment Link's custom field, when it has one
  status TEXT,                    -- active, trialing, past_due, unpaid, canceled, incomplete, incomplete_expired, paused
  amount INTEGER,                 -- pence per interval
  currency TEXT,
  cancel_at INTEGER,              -- ms; set when they've asked to cancel at the end of the period
  canceled_at INTEGER,            -- ms
  created INTEGER,
  updated INTEGER,
  livemode INTEGER
);
CREATE INDEX IF NOT EXISTS subscriptions_status ON subscriptions (status);
