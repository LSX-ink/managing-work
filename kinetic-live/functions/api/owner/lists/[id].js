// PATCH /api/owner/lists/:id { title }   DELETE /api/owner/lists/:id (only when empty)
import { handle, json, err, readJson, siteConfig, clampStr } from "../../../_lib/util.js";

export const onRequestPatch = handle(async ({ request, env, params }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  const b = await readJson(request, 2048);
  const r = await env.DB.prepare("UPDATE lists SET title = ? WHERE id = ?").bind(clampStr(b.title, 80).trim() || "Untitled", +params.id || 0).run();
  if (!r.meta.changes) return err("List not found", 404);
  return json({ ok: true });
});
export const onRequestDelete = handle(async ({ env, params }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM products WHERE list_id = ?").bind(+params.id || 0).first();
  if (n.n) return err("Remove or move the products in this list first", 409);
  await env.DB.prepare("DELETE FROM lists WHERE id = ?").bind(+params.id || 0).run();
  return json({ ok: true });
});
