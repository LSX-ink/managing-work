// POST /api/client/google  { credential, next }  -> Sign in with Google (Google Identity Services ID token)
import { handle, json, err, readJson, sameOrigin } from "../../_lib/util.js";
import { verifyGoogleIdToken, upsertClient, createClientSession, clientCookie, safeNext, CLIENT_DAYS } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  if (!env.GOOGLE_CLIENT_ID) return err("Google sign-in isn't switched on yet. Use your email instead.", 503);
  const body = await readJson(request, 8192);
  const who = await verifyGoogleIdToken(body.credential, env.GOOGLE_CLIENT_ID);
  if (!who) return err("Google sign-in didn't work. Try again, or use your email instead.", 401);
  const client = await upsertClient(env, who.email, { name: who.name, googleSub: who.sub });
  const token = await createClientSession(env, client.id);
  return json({ ok: true, next: safeNext(body.next) }, 200, { "Set-Cookie": clientCookie(token, CLIENT_DAYS * 86400) });
});
