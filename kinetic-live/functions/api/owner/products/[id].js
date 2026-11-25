// PATCH /api/owner/products/:id { name?, price?, inStock?, visible?, sizes?, listId? }
// DELETE /api/owner/products/:id
import { handle, json, err, readJson, siteConfig, clampStr } from "../../../_lib/util.js";
import { cleanSizes, ownerProduct } from "../../../_lib/catalog.js";

async function find(env, id) {
  return env.DB.prepare("SELECT * FROM products WHERE id = ?").bind(+id || 0).first();
}
export const onRequestPatch = handle(async ({ request, env, params }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  const p = await find(env, params.id);
  if (!p) return err("Product not found", 404);
  const b = await readJson(request);
  const set = {};
  if ("name" in b) set.name = clampStr(b.name, 120).trim() || "Untitled";
  if ("price" in b) { const v = Math.round(Number(b.price)); if (!(v >= 0 && v <= 1e8)) return err("Price must be 0 or more"); set.price_pence = v; }
  if ("inStock" in b) set.in_stock = b.inStock ? 1 : 0;
  if ("visible" in b) set.visible = b.visible ? 1 : 0;
  if ("sizes" in b) set.sizes = JSON.stringify(cleanSizes(b.sizes));
  if ("listId" in b) {
    const l = await env.DB.prepare("SELECT id FROM lists WHERE id = ?").bind(+b.listId || 0).first();
    if (!l) return err("That list doesn't exist"); set.list_id = l.id;
  }
  const keys = Object.keys(set);
  if (keys.length) {
    set.updated_at = Date.now(); keys.push("updated_at");
    await env.DB.prepare(`UPDATE products SET ${keys.map(k => k + " = ?").join(", ")} WHERE id = ?`).bind(...keys.map(k => set[k]), p.id).run();
  }
  return json({ product: ownerProduct(await find(env, p.id)) });
});
export const onRequestDelete = handle(async ({ env, params }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  const p = await find(env, params.id);
  if (!p) return err("Product not found", 404);
  await env.DB.prepare("DELETE FROM products WHERE id = ?").bind(p.id).run();
  if (p.img_key && env.PHOTOS) await env.PHOTOS.delete(p.img_key);
  return json({ ok: true });
});
