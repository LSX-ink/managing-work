// POST /api/auth/login  { username, password }  (the email is only for statements, never a login)
import { handle, json, err, readJson, verifyPassword, DUMMY_HASH, createSession, sessionCookie,
  sameOrigin, MAX_FAILED, LOCK_MINUTES, SESSION_DAYS } from "../../_lib/util.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const body = await readJson(request, 4096);
  const username = String(body.username || "").trim().toLowerCase().slice(0, 200);
  const password = String(body.password || "").slice(0, 200);
  const bad = () => err("That username and password don't match. Try again, or ask Kinetic Web Designs to reset it.", 401);
  if (!username || !password) return bad();

  const user = await env.DB.prepare("SELECT id, pw_hash, must_change, failed, locked_until FROM users WHERE username = ?").bind(username).first();
  if (!user) { await verifyPassword(password, DUMMY_HASH); return bad(); }

  const now = Date.now();
  if (user.locked_until > now) {
    const mins = Math.ceil((user.locked_until - now) / 6e4);
    return err(`Too many wrong passwords. Your login is locked for ${mins} more minute${mins === 1 ? "" : "s"}.`, 429, { locked: true });
  }
  if (!(await verifyPassword(password, user.pw_hash))) {
    const failed = (user.locked_until && user.locked_until <= now ? 0 : user.failed) + 1;
    const lock = failed >= MAX_FAILED ? now + LOCK_MINUTES * 6e4 : 0;
    await env.DB.prepare("UPDATE users SET failed = ?, locked_until = ? WHERE id = ?").bind(lock ? 0 : failed, lock, user.id).run();
    if (lock) return err(`Too many wrong passwords. Your login is locked for ${LOCK_MINUTES} minutes.`, 429, { locked: true });
    return bad();
  }
  await env.DB.prepare("UPDATE users SET failed = 0, locked_until = 0 WHERE id = ?").bind(user.id).run();
  const token = await createSession(env, user.id);
  return json({ ok: true, mustChange: !!user.must_change }, 200, { "Set-Cookie": sessionCookie(token, SESSION_DAYS * 86400) });
});
