// POST /api/owner/lists { title } -> new product list
import { handle, json, err, readJson, siteConfig, clampStr } from "../../../_lib/util.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!siteConfig(env).shop) return err("This website has no shop", 404);
  const b = await readJson(request, 2048);
  const max = await env.DB.prepare("SELECT COALESCE(MAX(sort), 0) AS m FROM lists").first();
  const row = await env.DB.prepare("INSERT INTO lists (title, sort) VALUES (?, ?) RETURNING id, title")
    .bind(clampStr(b.title || "New list", 80).trim() || "New list", max.m + 1).first();
  return json({ list: { ...row, items: [] } }, 201);
});
