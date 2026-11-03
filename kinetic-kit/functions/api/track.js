// POST /api/track { p: path, r: referrer host } -> records one page view. No cookies, no IPs stored.
import { handle, err, readJson, sameOrigin } from "../_lib/util.js";
import { isBot, device, visitorId, cleanPath, cleanHost } from "../_lib/visitor.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const ua = request.headers.get("User-Agent") || "";
  if (isBot(ua)) return new Response(null, { status: 204 });
  const b = await readJson(request, 2048);
  const path = cleanPath(b.p);
  if (path.startsWith("/owner") || path.startsWith("/api/")) return new Response(null, { status: 204 });
  const visitor = await visitorId(env, request);
  const now = Date.now();
  // the same visitor reloading the same page within 5 seconds counts once
  const dup = await env.DB.prepare("SELECT 1 FROM pageviews WHERE visitor = ? AND path = ? AND ts > ? LIMIT 1").bind(visitor, path, now - 5000).first();
  if (!dup) {
    await env.DB.prepare("INSERT INTO pageviews (ts, path, ref_host, visitor, device) VALUES (?, ?, ?, ?, ?)")
      .bind(now, path, cleanHost(b.r, new URL(request.url).host), visitor, device(ua)).run();
  }
  return new Response(null, { status: 204 });
});
