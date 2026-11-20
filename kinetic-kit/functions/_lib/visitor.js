// Cookieless visitor ids. Not a route.
// visitor = sha256(today's random salt + IP + user agent + host). The IP is used only for this
// hash and never stored; salts older than two days are deleted, so ids can't be linked across days.
import { sha256hex, b64url, randomBytes } from "./util.js";

const BOT = /bot|crawl|spider|slurp|facebookexternalhit|embedly|preview|lighthouse|pingdom|uptime|monitor|curl\/|wget|python-|go-http|okhttp|java\//i;

export function isBot(ua) { return !ua || BOT.test(ua); }

export function device(ua) {
  if (/iPad|Tablet|PlayBook|Silk|(Android(?!.*Mobile))/i.test(ua)) return "tablet";
  if (/Mobi|iPhone|iPod|Android|Windows Phone/i.test(ua)) return "phone";
  return "computer";
}

async function todaysSalt(DB, day) {
  let row = await DB.prepare("SELECT salt FROM salts WHERE day = ?").bind(day).first();
  if (row) return row.salt;
  await DB.prepare("INSERT OR IGNORE INTO salts (day, salt) VALUES (?, ?)").bind(day, b64url(randomBytes(24))).run();
  const old = new Date(Date.now() - 2 * 864e5).toISOString().slice(0, 10);
  await DB.prepare("DELETE FROM salts WHERE day < ?").bind(old).run();
  row = await DB.prepare("SELECT salt FROM salts WHERE day = ?").bind(day).first();
  return row.salt;
}

export async function visitorId(env, request) {
  const day = new Date().toISOString().slice(0, 10);
  const salt = await todaysSalt(env.DB, day);
  const ip = request.headers.get("CF-Connecting-IP") || request.headers.get("X-Forwarded-For") || "local";
  const ua = request.headers.get("User-Agent") || "";
  const host = new URL(request.url).host;
  return (await sha256hex(`${salt}|${ip}|${ua}|${host}`)).slice(0, 32);
}

export function cleanPath(p) {
  p = String(p || "/").split(/[?#]/)[0].slice(0, 200);
  return p.startsWith("/") ? p : "/" + p;
}
export function cleanHost(h, ownHost) {
  h = String(h || "").trim().toLowerCase().replace(/^www\./, "");
  if (!h || h.length > 120 || !/^[a-z0-9.-]+(:\d+)?$/.test(h)) return null;
  if (h === String(ownHost).toLowerCase().replace(/^www\./, "")) return null;
  return h;
}
