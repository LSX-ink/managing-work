// GET /api/owner/account, PATCH /api/owner/account { statements: true|false }
import { handle, json, err, readJson } from "../../_lib/util.js";

const view = u => ({ username: u.username, email: u.email, statements: !u.opted_out, optedOutAt: u.opted_out_at || null });

export const onRequestGet = handle(async ({ env, data }) => {
  const u = await env.DB.prepare("SELECT username, email, opted_out, opted_out_at FROM users WHERE id = ?").bind(data.user.id).first();
  return json(view(u));
});
export const onRequestPatch = handle(async ({ request, env, data }) => {
  const body = await readJson(request, 1024);
  if (typeof body.statements !== "boolean") return err("statements must be true or false");
  await env.DB.prepare("UPDATE users SET opted_out = ?, opted_out_at = ? WHERE id = ?")
    .bind(body.statements ? 0 : 1, body.statements ? null : Date.now(), data.user.id).run();
  const u = await env.DB.prepare("SELECT username, email, opted_out, opted_out_at FROM users WHERE id = ?").bind(data.user.id).first();
  return json(view(u));
});
