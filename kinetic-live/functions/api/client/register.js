// POST /api/client/register  { email, password, name, next }  -> creates a client account and signs them in
import { handle, json, err, readJson, sameOrigin, hashPassword, MIN_PASSWORD } from "../../_lib/util.js";
import { EMAIL } from "../../_lib/mail.js";
import { cleanSite, createClientSession, clientCookie, safeNext, CLIENT_DAYS } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const body = await readJson(request, 4096);
  const email = String(body.email || "").trim().toLowerCase().slice(0, 200);
  const password = String(body.password || "").slice(0, 200);
  const name = String(body.name || "").trim().slice(0, 120);
  const website = cleanSite(body.website);
  if (!EMAIL.test(email)) return err("That doesn't look like an email address. Check it and try again.");
  if (password.length < MIN_PASSWORD) return err(`Choose a password of at least ${MIN_PASSWORD} characters.`);
  const existing = await env.DB.prepare("SELECT id, pw_hash FROM clients WHERE email = ?").bind(email).first();
  if (existing && existing.pw_hash) {
    return err("There's already an account with that email. Sign in instead, or use \"Forgot your password?\".", 409, { exists: true });
  }
  const now = Date.now();
  const hash = await hashPassword(password);
  if (existing) {
    // signed in before with Google or an email link: this adds a password to the same account
    await env.DB.prepare("UPDATE clients SET pw_hash = ?, name = COALESCE(NULLIF(name, ''), ?), website = COALESCE(NULLIF(website, ''), ?), last_login = ? WHERE id = ?")
      .bind(hash, name, website, now, existing.id).run();
  } else {
    await env.DB.prepare("INSERT INTO clients (email, name, website, pw_hash, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?)")
      .bind(email, name, website, hash, now, now).run();
  }
  const c = await env.DB.prepare("SELECT id FROM clients WHERE email = ?").bind(email).first();
  const token = await createClientSession(env, c.id);
  return json({ ok: true, next: safeNext(body.next) }, 200, { "Set-Cookie": clientCookie(token, CLIENT_DAYS * 86400) });
});
