// Client accounts: one-time email links and Google sign-in, no passwords (owner, 16 Nov 2026).
// Not a route. The owner's own login (sessions/users, cookie kk_session) is separate and untouched.
import { b64url, randomBytes, sha256hex, getCookie } from "./util.js";

export const CLIENT_COOKIE = "kc_session";
export const CLIENT_DAYS = 30;
export const LINK_MINUTES = 20;
export const LINKS_PER_15_MIN = 3;

// The plans a signed-in client can buy: Stripe Payment Links (the same ones the site used before sign-in).
export const PLANS = {
  single: { link: "https://buy.stripe.com/8x2eVe3klezJ50Z1vk7wA00", label: "Single page, £20 a month" },
  five: { link: "https://buy.stripe.com/14A7sMg77ajt3WVde27wA01", label: "Up to 5 pages, £25 a month" },
  more: { link: "https://buy.stripe.com/dRm3cwaMNbnx2SRgqe7wA02", label: "More than 5 pages, £30 a month" }
};

// Only paths on this site: never an absolute URL or "//host" (an open redirect).
export function safeNext(next, fallback = "/account/") {
  const n = String(next || "");
  if (!n.startsWith("/") || n.startsWith("//") || n.startsWith("/\\") || n.length > 300) return fallback;
  return n;
}

// Their own website, as a clean https URL (or "" when blank or not a web address)
export function cleanSite(raw) {
  let s = String(raw || "").trim().slice(0, 300);
  if (!s) return "";
  if (!/^https?:\/\//i.test(s)) s = "https://" + s;
  try { const u = new URL(s); return /\./.test(u.hostname) && ["http:", "https:"].includes(u.protocol) ? u.toString() : ""; } catch { return ""; }
}

export function clientCookie(token, maxAge) {
  // Lax, not Strict: the sign-in link is opened from an email app, and the redirect after it must carry the cookie
  return `${CLIENT_COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${maxAge}`;
}

export async function upsertClient(env, email, { name = "", googleSub = "" } = {}) {
  const now = Date.now();
  email = email.toLowerCase();
  await env.DB.prepare(
    `INSERT INTO clients (email, name, google_sub, created_at, last_login) VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(email) DO UPDATE SET last_login = excluded.last_login,
       name = COALESCE(NULLIF(clients.name, ''), excluded.name),
       google_sub = COALESCE(NULLIF(excluded.google_sub, ''), clients.google_sub)`)
    .bind(email, name, googleSub, now, now).run();
  return env.DB.prepare("SELECT id, email, name FROM clients WHERE email = ?").bind(email).first();
}

export async function createClientSession(env, clientId) {
  const token = b64url(randomBytes(32));
  const now = Date.now();
  await env.DB.prepare("INSERT INTO client_sessions (id, client_id, created_at, expires_at) VALUES (?, ?, ?, ?)")
    .bind(await sha256hex(token), clientId, now, now + CLIENT_DAYS * 864e5).run();
  await env.DB.prepare("DELETE FROM client_sessions WHERE expires_at < ?").bind(now).run();
  return token;
}

export async function getClient(env, request) {
  const token = getCookie(request, CLIENT_COOKIE);
  if (!token || token.length > 100) return null;
  const row = await env.DB.prepare(
    `SELECT s.id AS sid, s.expires_at, c.id, c.email, c.name FROM client_sessions s
       JOIN clients c ON c.id = s.client_id WHERE s.id = ?`).bind(await sha256hex(token)).first();
  if (!row || row.expires_at < Date.now()) return null;
  return row;
}

// ---- Google sign-in: verify the ID token Google Identity Services hands the page ----
const unb64url = s => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4)),
  c => c.charCodeAt(0));

export async function verifyGoogleIdToken(credential, clientId, nowSeconds = Math.floor(Date.now() / 1000),
  fetchKeys = fetchGoogleKeys) {
  const parts = String(credential || "").split(".");
  if (parts.length !== 3 || !clientId) return null;
  let header, payload;
  try {
    header = JSON.parse(new TextDecoder().decode(unb64url(parts[0])));
    payload = JSON.parse(new TextDecoder().decode(unb64url(parts[1])));
  } catch { return null; }
  if (header.alg !== "RS256" || !header.kid) return null;
  const jwk = (await fetchKeys()).find(k => k.kid === header.kid);
  if (!jwk) return null;
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, unb64url(parts[2]),
    new TextEncoder().encode(parts[0] + "." + parts[1]));
  if (!ok) return null;
  if (!["accounts.google.com", "https://accounts.google.com"].includes(payload.iss)) return null;
  if (payload.aud !== clientId) return null;
  if (!payload.exp || payload.exp < nowSeconds - 60) return null;
  if (!payload.email || payload.email_verified !== true && payload.email_verified !== "true") return null;
  return { email: String(payload.email).toLowerCase(), name: String(payload.name || ""), sub: String(payload.sub || "") };
}

async function fetchGoogleKeys() {
  const res = await fetch("https://www.googleapis.com/oauth2/v3/certs", { cf: { cacheTtl: 3600 } });
  if (!res.ok) return [];
  return (await res.json()).keys || [];
}
