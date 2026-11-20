// GET /api/client/me -> the signed-in client and their plans (or 401). Also says whether Google sign-in is on.
import { handle, json } from "../../_lib/util.js";
import { getClient } from "../../_lib/client.js";

export const onRequestGet = handle(async ({ request, env }) => {
  const google = env.GOOGLE_CLIENT_ID || "";
  const c = await getClient(env, request);
  const pw = c ? await env.DB.prepare("SELECT pw_hash, website FROM clients WHERE id = ?").bind(c.id).first() : null;
  if (!c) return json({ signedIn: false, googleClientId: google }, 200, { "Cache-Control": "no-store" });
  let plans = [];
  try {
    const r = await env.DB.prepare(
      "SELECT status, amount, currency, website, cancel_at, created FROM subscriptions WHERE lower(email) = ? ORDER BY created DESC")
      .bind(c.email).all();
    plans = r.results || [];
  } catch { /* no subscriptions table yet */ }
  return json({ signedIn: true, email: c.email, name: c.name || "", hasPassword: !!(pw && pw.pw_hash), website: (pw && pw.website) || "", plans, portal: env.STRIPE_PORTAL_LINK || "",
    googleClientId: google }, 200, { "Cache-Control": "no-store" });
});
