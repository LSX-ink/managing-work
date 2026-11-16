// POST /api/client/password  { password }  -> a signed-in client sets a new password (after "Forgot your password?")
import { handle, json, err, readJson, sameOrigin, hashPassword, MIN_PASSWORD } from "../../_lib/util.js";
import { getClient } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const c = await getClient(env, request);
  if (!c) return err("Please sign in first.", 401);
  const body = await readJson(request, 4096);
  const password = String(body.password || "").slice(0, 200);
  if (password.length < MIN_PASSWORD) return err(`Choose a password of at least ${MIN_PASSWORD} characters.`);
  await env.DB.prepare("UPDATE clients SET pw_hash = ?, failed = 0, locked_until = 0 WHERE id = ?")
    .bind(await hashPassword(password), c.id).run();
  // every other device is signed out; this one stays signed in
  await env.DB.prepare("DELETE FROM client_sessions WHERE client_id = ? AND id != ?").bind(c.id, c.sid).run();
  return json({ ok: true });
});
