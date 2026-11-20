// POST /api/client/login  { email, password, next }  -> signs a client in with their email and password
import { handle, json, err, readJson, sameOrigin, verifyPassword, DUMMY_HASH, MAX_FAILED, LOCK_MINUTES } from "../../_lib/util.js";
import { createClientSession, clientCookie, safeNext, CLIENT_DAYS } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const body = await readJson(request, 4096);
  const email = String(body.email || "").trim().toLowerCase().slice(0, 200);
  const password = String(body.password || "").slice(0, 200);
  const bad = () => err("That email and password don't match. Try again, or use \"Forgot your password?\".", 401);
  if (!email || !password) return bad();
  const c = await env.DB.prepare("SELECT id, pw_hash, failed, locked_until FROM clients WHERE email = ?").bind(email).first();
  if (!c || !c.pw_hash) { await verifyPassword(password, DUMMY_HASH); return bad(); }
  const now = Date.now();
  if (c.locked_until > now) {
    const mins = Math.ceil((c.locked_until - now) / 6e4);
    return err(`Too many wrong passwords. Try again in ${mins} minute${mins === 1 ? "" : "s"}, or use "Forgot your password?".`, 429);
  }
  if (!(await verifyPassword(password, c.pw_hash))) {
    const failed = (c.locked_until && c.locked_until <= now ? 0 : c.failed) + 1;
    const lock = failed >= MAX_FAILED ? now + LOCK_MINUTES * 6e4 : 0;
    await env.DB.prepare("UPDATE clients SET failed = ?, locked_until = ? WHERE id = ?").bind(lock ? 0 : failed, lock, c.id).run();
    if (lock) return err(`Too many wrong passwords. Try again in ${LOCK_MINUTES} minutes, or use "Forgot your password?".`, 429);
    return bad();
  }
  await env.DB.prepare("UPDATE clients SET failed = 0, locked_until = 0, last_login = ? WHERE id = ?").bind(now, c.id).run();
  const token = await createClientSession(env, c.id);
  return json({ ok: true, next: safeNext(body.next) }, 200, { "Set-Cookie": clientCookie(token, CLIENT_DAYS * 86400) });
});
