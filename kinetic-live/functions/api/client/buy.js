// GET /api/client/buy?plan=single|five|more -> signed in: on to Stripe with their email filled in.
// Not signed in: to the sign-in page first, which comes back here (owner, 16 Nov 2026: sign in before buying).
import { handle } from "../../_lib/util.js";
import { getClient, PLANS } from "../../_lib/client.js";

const go = (location, extra = {}) => new Response(null, { status: 302, headers: { Location: location, "Cache-Control": "no-store", ...extra } });

export const onRequestGet = handle(async ({ request, env }) => {
  const url = new URL(request.url);
  const plan = url.searchParams.get("plan") || "";
  const p = PLANS[plan];
  if (!p) return go("/#changes");
  const c = await getClient(env, request);
  if (!c) return go("/signin/?plan=" + encodeURIComponent(plan) + "&next=" + encodeURIComponent("/api/client/buy?plan=" + plan));
  const stripe = new URL(p.link);
  stripe.searchParams.set("prefilled_email", c.email);
  stripe.searchParams.set("client_reference_id", "client_" + c.id);
  return go(stripe.toString());
});
