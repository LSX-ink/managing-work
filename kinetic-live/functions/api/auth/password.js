// POST /api/auth/password { current?, password }
// On a temporary password (must_change) the current one isn't asked for again: the owner
// has just logged in with it. Otherwise the current password is required.
import { handle, json, err, readJson, getSession, hashPassword, verifyPassword, createSession,
  sessionCookie, sameOrigin, MIN_PASSWORD, SESSION_DAYS } from "../../_lib/util.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const s = await getSession(env, request);
  if (!s) return err("Not logged in", 401);
  const body = await readJson(request, 4096);
  const pw = String(body.password || "");
  const user = await env.DB.prepare("SELECT pw_hash, must_change FROM users WHERE id = ?").bind(s.id).first();
  if (!user.must_change && !(await verifyPassword(String(body.current || ""), user.pw_hash)))
    return err("Your current password isn't right.", 400);
  if (pw.length < MIN_PASSWORD) return err(`Use at least ${MIN_PASSWORD} characters.`, 400);
  if (pw.length > 200) return err("That password is too long.", 400);
  if (await verifyPassword(pw, user.pw_hash)) return err("Choose a new password, not the one you have now.", 400);
  const hash = await hashPassword(pw);
  await env.DB.batch([
    env.DB.prepare("UPDATE users SET pw_hash = ?, must_change = 0, pw_changed_at = ?, failed = 0, locked_until = 0 WHERE id = ?").bind(hash, Date.now(), s.id),
    env.DB.prepare("DELETE FROM sessions WHERE user_id = ?").bind(s.id) // log out everywhere else
  ]);
  const token = await createSession(env, s.id);
  return json({ ok: true }, 200, { "Set-Cookie": sessionCookie(token, SESSION_DAYS * 86400) });
});
