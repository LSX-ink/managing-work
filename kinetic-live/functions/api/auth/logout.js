// POST /api/auth/logout
import { handle, json, getCookie, sha256hex, sessionCookie, SESSION_COOKIE, sameOrigin, err } from "../../_lib/util.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const token = getCookie(request, SESSION_COOKIE);
  if (token) await env.DB.prepare("DELETE FROM sessions WHERE id = ?").bind(await sha256hex(token)).run();
  return json({ ok: true }, 200, { "Set-Cookie": sessionCookie("", 0) });
});
