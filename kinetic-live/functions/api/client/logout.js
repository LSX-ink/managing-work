// POST /api/client/logout -> ends this device's client session
import { handle, json, err, sameOrigin, getCookie, sha256hex } from "../../_lib/util.js";
import { CLIENT_COOKIE, clientCookie } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const token = getCookie(request, CLIENT_COOKIE);
  if (token && token.length <= 100) {
    await env.DB.prepare("DELETE FROM client_sessions WHERE id = ?").bind(await sha256hex(token)).run();
  }
  return json({ ok: true }, 200, { "Set-Cookie": clientCookie("", 0) });
});
