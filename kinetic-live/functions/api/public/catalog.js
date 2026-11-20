// GET /api/public/catalog -> the website's visible products and text, for kit.js
import { handle, json, siteConfig } from "../../_lib/util.js";
import { loadCatalog } from "../../_lib/catalog.js";

export const onRequestGet = handle(async ({ env }) => {
  const cfg = siteConfig(env);
  const texts = (await env.DB.prepare("SELECT key, value FROM texts").all()).results;
  return json({
    shop: cfg.shop, currency: cfg.currency,
    lists: cfg.shop ? (await loadCatalog(env.DB, { publicOnly: true })).filter(l => l.items.length) : [],
    text: Object.fromEntries(texts.map(t => [t.key, t.value]))
  }, 200, { "Cache-Control": "public, max-age=0, must-revalidate" });
});
