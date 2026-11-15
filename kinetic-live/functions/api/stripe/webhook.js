// POST /api/stripe/webhook  — Stripe sends payments and refunds here.
// Set STRIPE_WEBHOOK_SECRET (whsec_...) as a Pages secret. Subscribe the endpoint to:
//   charge.succeeded, charge.pending, charge.failed, charge.refunded, charge.refund.updated,
//   refund.created, refund.updated, refund.failed
// and, for the hosting-and-care plans (owner, 15 Nov 2026: track who unsubscribes so we stop making changes):
//   checkout.session.completed, customer.subscription.created, customer.subscription.updated,
//   customer.subscription.deleted  (rows go in the subscriptions table: kinetic-kit/migrations-subscriptions.sql)
import { json, err } from "../../_lib/util.js";
import { verifyStripeSignature } from "../../_lib/stripe.js";

const MAX_BODY = 512 * 1024;

function chargeRow(c) {
  const status = c.status === "succeeded" ? "succeeded" : c.status === "pending" ? "pending" : "failed";
  return {
    id: c.id, kind: "payment", status, amount: c.amount || 0, currency: String(c.currency || "gbp").toLowerCase(),
    description: c.description || c.calculated_statement_descriptor || c.statement_descriptor || null,
    customer: (c.billing_details && c.billing_details.name) || null, charge_id: null,
    email: String((c.billing_details && c.billing_details.email) || c.receipt_email || "").trim().toLowerCase().slice(0, 200) || null,
    created: (c.created || Math.floor(Date.now() / 1000)) * 1000, livemode: c.livemode ? 1 : 0
  };
}
function refundRow(r, charge) {
  const status = r.status === "succeeded" ? "succeeded" : r.status === "pending" || r.status === "requires_action" ? "pending" : r.status === "canceled" ? "canceled" : "failed";
  const chargeId = typeof r.charge === "string" ? r.charge : r.charge && r.charge.id || (charge && charge.id) || null;
  return {
    id: r.id, kind: "refund", status, amount: r.amount || 0, currency: String(r.currency || (charge && charge.currency) || "gbp").toLowerCase(),
    description: r.reason ? "Refund (" + String(r.reason).replace(/_/g, " ") + ")" : "Refund",
    customer: (charge && charge.billing_details && charge.billing_details.name) || null, charge_id: chargeId, email: null,
    created: (r.created || Math.floor(Date.now() / 1000)) * 1000, livemode: (r.livemode ?? (charge && charge.livemode)) ? 1 : 0
  };
}
function upsert(DB, row) {
  return DB.prepare(
    `INSERT INTO payments (id, kind, status, amount, currency, description, customer, charge_id, created, livemode, updated, email)
     VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, (SELECT customer FROM payments WHERE id = ?)), ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET status = excluded.status, amount = excluded.amount, description = COALESCE(excluded.description, description),
       customer = COALESCE(excluded.customer, customer), email = COALESCE(excluded.email, email), updated = excluded.updated`)
    .bind(row.id, row.kind, row.status, row.amount, row.currency, row.description, row.customer, row.charge_id, row.charge_id, row.created, row.livemode, Date.now(), row.email);
}

const ms = s => (s ? s * 1000 : null);
const clip = (v, n) => (v == null ? null : String(v).trim().slice(0, n) || null);

// A Payment Link's custom field (e.g. "Your website address"), whatever its key is called
function websiteField(session) {
  for (const f of session.custom_fields || []) {
    const v = f.text && f.text.value;
    if (v && /web|site|url|domain/i.test((f.key || "") + " " + ((f.label && f.label.custom) || ""))) return clip(v, 200);
  }
  return null;
}

function subscriptionStmt(DB, s) {
  const item = s.items && s.items.data && s.items.data[0];
  const price = item && item.price;
  const customer = typeof s.customer === "string" ? s.customer : s.customer && s.customer.id;
  return DB.prepare(
    `INSERT INTO subscriptions (id, customer, status, amount, currency, cancel_at, canceled_at, created, updated, livemode)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET status = excluded.status, amount = COALESCE(excluded.amount, amount),
       currency = COALESCE(excluded.currency, currency), cancel_at = excluded.cancel_at,
       canceled_at = excluded.canceled_at, customer = COALESCE(excluded.customer, customer), updated = excluded.updated`)
    .bind(s.id, customer || null, clip(s.status, 30), price && price.unit_amount != null ? price.unit_amount : null,
      clip(price && price.currency, 8), ms(s.cancel_at), ms(s.canceled_at || s.ended_at), ms(s.created) || Date.now(),
      Date.now(), s.livemode ? 1 : 0);
}

function checkoutStmt(DB, c) {
  const sub = typeof c.subscription === "string" ? c.subscription : c.subscription && c.subscription.id;
  if (c.mode !== "subscription" || !sub) return null;
  const d = c.customer_details || {};
  const customer = typeof c.customer === "string" ? c.customer : c.customer && c.customer.id;
  return DB.prepare(
    `INSERT INTO subscriptions (id, customer, email, name, website, status, created, updated, livemode)
     VALUES (?, ?, ?, ?, ?, 'active', ?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET email = COALESCE(excluded.email, email), name = COALESCE(excluded.name, name),
       website = COALESCE(excluded.website, website), customer = COALESCE(excluded.customer, customer), updated = excluded.updated`)
    .bind(sub, customer || null, (clip(d.email, 200) || "").toLowerCase() || null, clip(d.name, 120), websiteField(c),
      ms(c.created) || Date.now(), Date.now(), c.livemode ? 1 : 0);
}

export async function onRequestPost({ request, env }) {
  if (!env.STRIPE_WEBHOOK_SECRET) return err("Stripe isn't connected for this website", 503);
  if (+(request.headers.get("Content-Length") || 0) > MAX_BODY) return err("Too large", 413);
  const payload = await request.text();
  if (payload.length > MAX_BODY) return err("Too large", 413);
  const ok = await verifyStripeSignature(payload, request.headers.get("Stripe-Signature"), env.STRIPE_WEBHOOK_SECRET);
  if (!ok) return err("Bad signature", 400);

  let event; try { event = JSON.parse(payload); } catch { return err("Bad JSON", 400); }
  if (!event || !event.id || !event.type || !event.data || !event.data.object) return err("Not a Stripe event", 400);

  const DB = env.DB, obj = event.data.object, rows = [];
  switch (event.type) {
    case "charge.succeeded": case "charge.pending": case "charge.failed": case "charge.updated":
      rows.push(chargeRow(obj)); break;
    case "charge.refunded":
      rows.push(chargeRow(obj));
      for (const r of (obj.refunds && obj.refunds.data) || []) rows.push(refundRow(r, obj));
      break;
    case "refund.created": case "refund.updated": case "refund.failed": case "charge.refund.updated":
      rows.push(refundRow(obj, null)); break;
    case "checkout.session.completed":
    case "customer.subscription.created": case "customer.subscription.updated": case "customer.subscription.deleted": {
      const stmt = event.type === "checkout.session.completed" ? checkoutStmt(DB, obj) : subscriptionStmt(DB, obj);
      if (!stmt) return json({ received: true, ignored: "not a subscription checkout" });
      await DB.batch([stmt, DB.prepare("INSERT OR IGNORE INTO stripe_events (id, type, received) VALUES (?, ?, ?)")
        .bind(event.id, event.type, Date.now())]);
      return json({ received: true, stored: 1 });
    }
    default:
      return json({ received: true, ignored: event.type });
  }
  // Stripe may resend an event; the upsert makes that harmless, and stripe_events keeps a record.
  await DB.batch([
    ...rows.map(r => upsert(DB, r)),
    DB.prepare("INSERT OR IGNORE INTO stripe_events (id, type, received) VALUES (?, ?, ?)").bind(event.id, event.type, Date.now())
  ]);
  return json({ received: true, stored: rows.length });
}
