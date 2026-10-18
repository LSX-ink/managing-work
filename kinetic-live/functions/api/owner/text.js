// GET /api/owner/text, PUT /api/owner/text { values: { key: "text" } }
// Kinetic decides which text fields a site has (rows in `texts`); the owner edits their values.
import { handle, json, err, readJson } from "../../_lib/util.js";

export const onRequestGet = handle(async ({ env }) => {
  const { results } = await env.DB.prepare("SELECT key, label, value, multiline FROM texts ORDER BY sort, key").all();
  return json({ fields: results.map(r => ({ ...r, multiline: !!r.multiline })) });
});
export const onRequestPut = handle(async ({ request, env }) => {
  const body = await readJson(request, 256 * 1024);
  const values = body.values && typeof body.values === "object" ? body.values : null;
  if (!values) return err("values missing");
  const now = Date.now();
  const stmts = Object.entries(values).slice(0, 200).map(([k, v]) =>
    env.DB.prepare("UPDATE texts SET value = ?, updated_at = ? WHERE key = ?").bind(String(v ?? "").slice(0, 20000), now, String(k).slice(0, 100)));
  if (stmts.length) await env.DB.batch(stmts);
  return json({ ok: true });
});
