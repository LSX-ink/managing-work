// Everything under /api/owner/* needs a logged-in owner who has replaced the temporary password.
import { err, getSession, sameOrigin } from "../../_lib/util.js";

export async function onRequest(ctx) {
  const { request, env } = ctx;
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const s = await getSession(env, request);
  if (!s) return err("Not logged in", 401);
  if (s.must_change) return err("Choose your own password first", 403, { mustChange: true });
  ctx.data.user = s;
  const res = await ctx.next();
  const out = new Response(res.body, res);
  out.headers.set("Cache-Control", "no-store");
  return out;
}
