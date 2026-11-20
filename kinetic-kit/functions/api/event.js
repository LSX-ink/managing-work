// POST /api/event { name, p } -> counts a site event such as a sign-up or a quote request.
// Only names listed in the EVENTS variable are accepted.
import { handle, err, readJson, sameOrigin, siteConfig } from "../_lib/util.js";
import { isBot, visitorId, cleanPath } from "../_lib/visitor.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  if (isBot(request.headers.get("User-Agent") || "")) return new Response(null, { status: 204 });
  const b = await readJson(request, 2048);
  const name = String(b.name || "").toLowerCase();
  if (!siteConfig(env).events.some(e => e.name === name)) return err("Unknown event", 400);
  const visitor = await visitorId(env, request);
  const now = Date.now();
  // a double-click or a resubmit within 30 seconds counts once
  const dup = await env.DB.prepare("SELECT 1 FROM events WHERE visitor = ? AND name = ? AND ts > ? LIMIT 1").bind(visitor, name, now - 30000).first();
  if (!dup) await env.DB.prepare("INSERT INTO events (ts, name, path, visitor) VALUES (?, ?, ?, ?)").bind(now, name, cleanPath(b.p), visitor).run();
  return new Response(null, { status: 204 });
});
