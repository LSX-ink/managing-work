// GET /api/owner/transactions?filter=all|paid|refund|pending&limit=100&before=<ms>
import { handle, json } from "../../_lib/util.js";

export const onRequestGet = handle(async ({ request, env }) => {
  const u = new URL(request.url);
  const filter = u.searchParams.get("filter") || "all";
  const limit = Math.max(1, Math.min(500, +u.searchParams.get("limit") || 100));
  const before = +u.searchParams.get("before") || 8.64e15;
  const where = { paid: "kind = 'payment' AND status = 'succeeded'", refund: "kind = 'refund'", pending: "status = 'pending'" }[filter] || "1 = 1";
  const { results } = await env.DB.prepare(
    `SELECT id, kind, status, amount, currency, description, customer, charge_id AS chargeId, created, livemode
       FROM payments WHERE ${where} AND created < ? ORDER BY created DESC LIMIT ?`).bind(before, limit).all();
  const total = await env.DB.prepare("SELECT COUNT(*) AS n FROM payments").first();
  return json({ stripe: !!env.STRIPE_WEBHOOK_SECRET, any: total.n > 0, transactions: results.map(r => ({ ...r, livemode: !!r.livemode })) });
});
