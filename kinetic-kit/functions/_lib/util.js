// Shared helpers for the Kinetic kit Pages Functions. This file exports no onRequest
// handlers, so Pages does not turn it into a route.

export const ITERATIONS = 100000; // Cloudflare Workers' WebCrypto caps PBKDF2 at 100,000
export const SESSION_COOKIE = "kk_session";
export const SESSION_DAYS = 14;
export const MAX_FAILED = 5;              // wrong passwords in a row before a lockout
export const LOCK_MINUTES = 15;
export const MIN_PASSWORD = 10;

const enc = new TextEncoder();

export function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers }
  });
}
export const err = (message, status = 400, extra = {}) => json({ error: message, ...extra }, status);

export async function readJson(request, max = 64 * 1024) {
  const len = +(request.headers.get("Content-Length") || 0);
  if (len > max) throw new HttpError("Too much data", 413);
  const text = await request.text();
  if (text.length > max) throw new HttpError("Too much data", 413);
  try { return text ? JSON.parse(text) : {}; } catch { throw new HttpError("Bad JSON", 400); }
}

export class HttpError extends Error {
  constructor(message, status = 400) { super(message); this.status = status; }
}
export function handle(fn) {
  return async ctx => {
    try { return await fn(ctx); }
    catch (e) {
      if (e instanceof HttpError) return err(e.message, e.status);
      console.error(e && e.stack || e);
      return err("Something went wrong", 500);
    }
  };
}

// ---------- encoding ----------
export const b64 = buf => btoa(String.fromCharCode(...new Uint8Array(buf)));
export const unb64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
export const hex = buf => [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
export const b64url = buf => b64(buf).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
export const randomBytes = n => crypto.getRandomValues(new Uint8Array(n));
export const sha256hex = async s => hex(await crypto.subtle.digest("SHA-256", typeof s === "string" ? enc.encode(s) : s));

export function timingSafeEqual(a, b) {
  if (typeof a === "string") a = enc.encode(a);
  if (typeof b === "string") b = enc.encode(b);
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0;
}

// ---------- passwords (PBKDF2-SHA256, per-user random salt) ----------
async function pbkdf2(password, salt, iterations) {
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations }, key, 256));
}
export async function hashPassword(password) {
  const salt = randomBytes(16);
  const h = await pbkdf2(password, salt, ITERATIONS);
  return `pbkdf2-sha256$${ITERATIONS}$${b64(salt)}$${b64(h)}`;
}
export async function verifyPassword(password, stored) {
  const parts = String(stored || "").split("$");
  if (parts.length !== 4 || parts[0] !== "pbkdf2-sha256") return false;
  const iterations = parseInt(parts[1], 10);
  if (!(iterations > 0 && iterations <= ITERATIONS)) return false;
  let salt, want;
  try { salt = unb64(parts[2]); want = unb64(parts[3]); } catch { return false; }
  const h = await pbkdf2(password, salt, iterations);
  return timingSafeEqual(h, want);
}
// Burns the same time as a real check, so unknown emails can't be told apart by timing.
export const DUMMY_HASH = "pbkdf2-sha256$100000$AAAAAAAAAAAAAAAAAAAAAA==$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=";

// ---------- sessions ----------
export function getCookie(request, name) {
  const c = request.headers.get("Cookie") || "";
  for (const part of c.split(/;\s*/)) {
    const i = part.indexOf("=");
    if (i > 0 && part.slice(0, i) === name) return decodeURIComponent(part.slice(i + 1));
  }
  return null;
}
export function sessionCookie(token, maxAge) {
  return `${SESSION_COOKIE}=${token}; Path=/api; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAge}`;
}
export async function createSession(env, userId) {
  const token = b64url(randomBytes(32));
  const now = Date.now();
  await env.DB.prepare("INSERT INTO sessions (id, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)")
    .bind(await sha256hex(token), userId, now, now + SESSION_DAYS * 864e5).run();
  // tidy expired sessions now and then
  await env.DB.prepare("DELETE FROM sessions WHERE expires_at < ?").bind(now).run();
  return token;
}
export async function getSession(env, request) {
  const token = getCookie(request, SESSION_COOKIE);
  if (!token || token.length > 100) return null;
  const id = await sha256hex(token);
  const row = await env.DB.prepare(
    `SELECT s.id AS sid, s.expires_at, u.id, u.email, u.must_change, u.opted_out, u.opted_out_at
       FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = ?`).bind(id).first();
  if (!row || row.expires_at < Date.now()) return null;
  return row;
}

// Blocks cross-site form posts: a state-changing request must come from this site.
export function sameOrigin(request) {
  if (["GET", "HEAD", "OPTIONS"].includes(request.method)) return true;
  const origin = request.headers.get("Origin");
  const host = new URL(request.url).host;
  if (origin) { try { return new URL(origin).host === host; } catch { return false; } }
  const site = request.headers.get("Sec-Fetch-Site");
  return !site || site === "same-origin" || site === "none";
}

// ---------- site config (wrangler.toml [vars]) ----------
export const flag = v => /^(1|true|yes|on)$/i.test(String(v ?? "").trim());
export function siteConfig(env) {
  const events = String(env.EVENTS || "").split(",").map(s => s.trim()).filter(Boolean).map(s => {
    const [name, label] = s.split(":");
    return { name: name.trim().toLowerCase(), label: (label || name).trim() };
  }).filter(e => /^[a-z0-9_-]{1,32}$/.test(e.name));
  return {
    siteName: env.SITE_NAME || "Your website",
    siteUrl: env.SITE_URL || "",
    shop: flag(env.SHOP),
    text: flag(env.TEXT),
    events,
    currency: (env.CURRENCY || "gbp").toLowerCase(),
    stripe: !!env.STRIPE_WEBHOOK_SECRET,
    photos: !!env.PHOTOS
  };
}

export const clampStr = (s, n) => String(s ?? "").slice(0, n);
export const now = () => Date.now();
