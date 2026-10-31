// Stripe webhook signature check (no SDK needed). Not a route.
// Header: Stripe-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "<t>.<raw body>">[,v1=...]
import { hex, timingSafeEqual } from "./util.js";

export const TOLERANCE_SECONDS = 300;

export async function signPayload(secret, timestamp, payload) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(`${timestamp}.${payload}`)));
}

export async function verifyStripeSignature(payload, header, secret, nowSeconds = Math.floor(Date.now() / 1000)) {
  if (!header || !secret) return false;
  let t = null; const sigs = [];
  for (const part of header.split(",")) {
    const [k, v] = part.split("=", 2).map(s => s && s.trim());
    if (k === "t") t = v;
    else if (k === "v1" && v) sigs.push(v);
  }
  if (!t || !/^\d+$/.test(t) || !sigs.length) return false;
  if (Math.abs(nowSeconds - +t) > TOLERANCE_SECONDS) return false;
  const want = await signPayload(secret, t, payload);
  return sigs.some(s => timingSafeEqual(s, want));
}
