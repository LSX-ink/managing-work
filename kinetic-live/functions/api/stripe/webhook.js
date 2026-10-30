// POST /api/stripe/webhook  — Stripe sends payments and refunds here.
// Set STRIPE_WEBHOOK_SECRET (whsec_...) as a Pages secret. Subscribe the endpoint to:
//   charge.succeeded, charge.pending, charge.failed, charge.refunded, charge.refund.updated,
//   refund.created, refund.updated, refund.failed
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
