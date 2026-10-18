// GET /api/owner/products -> lists with every product (hidden ones too)
// POST /api/owner/products { listId, name?, price?, sizes? } -> new product
import { handle, json, err, readJson, siteConfig, clampStr } from "../../../_lib/util.js";
import { loadCatalog, cleanSizes, ownerProduct } from "../../../_lib/catalog.js";

export const onRequestGet = handle(async ({ env }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  return json({ lists: await loadCatalog(env.DB) });
});
export const onRequestPost = handle(async ({ request, env }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  const b = await readJson(request);
  const list = await env.DB.prepare("SELECT id FROM lists WHERE id = ?").bind(+b.listId || 0).first();
  if (!list) return err("That list doesn't exist");
  const now = Date.now();
  const min = await env.DB.prepare("SELECT COALESCE(MIN(sort), 0) AS m FROM products WHERE list_id = ?").bind(list.id).first();
  const row = await env.DB.prepare(
    `INSERT INTO products (list_id, name, price_pence, in_stock, visible, sizes, sort, created_at, updated_at)
     VALUES (?, ?, ?, 1, 1, ?, ?, ?, ?) RETURNING *`)
    .bind(list.id, clampStr(b.name || "New product", 120), Math.max(0, Math.round(+b.price || 0)),
      JSON.stringify(b.sizes ? cleanSizes(b.sizes) : []), min.m - 1, now, now).first();
  return json({ product: ownerProduct(row) }, 201);
});
