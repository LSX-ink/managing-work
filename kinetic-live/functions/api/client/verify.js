// GET /api/client/verify?t=<token>  -> the link from the "Forgot your password?" email: signs the client in and
// takes them to choose a new password, then on to where they were going
import { handle, sha256hex } from "../../_lib/util.js";
import { upsertClient, createClientSession, clientCookie, safeNext, CLIENT_DAYS } from "../../_lib/client.js";

const back = (msg) => new Response(null, { status: 302, headers: { Location: "/signin/?e=" + encodeURIComponent(msg) } });

export const onRequestGet = handle(async ({ request, env }) => {
  const t = new URL(request.url).searchParams.get("t") || "";
  if (!t || t.length > 100) return back("That link isn't valid. Sign in below, or use \"Forgot your password?\" again.");
  const id = await sha256hex(t);
  const now = Date.now();
  const row = await env.DB.prepare("SELECT email, next, expires_at, used_at, purpose FROM client_links WHERE id = ?").bind(id).first();
  if (!row) return back("That link isn't valid. Sign in below, or use \"Forgot your password?\" again.");
  if (row.used_at) return back("That link has already been used. Sign in below, or use \"Forgot your password?\" again.");
  if (row.expires_at < now) return back("That link has run out. Sign in below, or use \"Forgot your password?\" again.");
  // single use: only the request that flips used_at wins
  const res = await env.DB.prepare("UPDATE client_links SET used_at = ? WHERE id = ? AND used_at IS NULL").bind(now, id).run();
  if (!res.meta || res.meta.changes !== 1) return back("That link has already been used. Sign in below, or use \"Forgot your password?\" again.");
  const client = await upsertClient(env, row.email);
  const token = await createClientSession(env, client.id);
  return new Response(null, { status: 302, headers: {
    Location: row.purpose === "reset" ? "/account/?reset=1&next=" + encodeURIComponent(safeNext(row.next)) : safeNext(row.next), "Set-Cookie": clientCookie(token, CLIENT_DAYS * 86400), "Cache-Control": "no-store" } });
});
