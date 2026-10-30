// GET /api/auth/me -> who is logged in (or 401)
import { handle, json, err, getSession } from "../../_lib/util.js";

export const onRequestGet = handle(async ({ request, env }) => {
  const s = await getSession(env, request);
  if (!s) return err("Not logged in", 401);
  return json({ username: s.username, email: s.email, mustChange: !!s.must_change, statements: !s.opted_out, optedOutAt: s.opted_out_at || null });
});
