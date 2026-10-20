// GET    /api/owner/leads?kind=signups|briefs[&format=csv]  -> list (newest first) or a CSV download
// DELETE /api/owner/leads?kind=signups|briefs&id=<id>        -> remove one row
import { handle, json, err } from "../../_lib/util.js";
import { mailReady } from "../../_lib/mail.js";

const csvCell = v => {
  let s = String(v ?? "");
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s; // stop spreadsheet formula injection
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
const iso = ms => (ms ? new Date(ms).toISOString() : "");

export const onRequestGet = handle(async ({ request, env }) => {
  const u = new URL(request.url);
  const kind = u.searchParams.get("kind") === "briefs" ? "briefs" : "signups";
  const csv = u.searchParams.get("format") === "csv";
  const limit = csv ? 10000 : Math.max(1, Math.min(500, +u.searchParams.get("limit") || 200));

  if (kind === "signups") {
    const { results } = await env.DB.prepare(
      "SELECT id, email, marketing, created_at AS created, updated_at AS updated, welcomed_at AS welcomed FROM signups ORDER BY created_at DESC LIMIT ?").bind(limit).all();
    if (csv) {
      const lines = [["email", "marketing_consent", "signed_up", "last_seen", "welcome_sent"].join(",")]
        .concat(results.map(r => [r.email, r.marketing ? "yes" : "no", iso(r.created), iso(r.updated), iso(r.welcomed)].map(csvCell).join(",")));
      return download(lines, "signups");
    }
    const totals = await env.DB.prepare("SELECT COUNT(*) AS n, COALESCE(SUM(marketing), 0) AS m FROM signups").first();
    return json({ kind, mail: mailReady(env), total: totals.n, marketing: totals.m, rows: results.map(r => ({ ...r, marketing: !!r.marketing })) });
  }

  const { results } = await env.DB.prepare(
    "SELECT id, created_at AS created, name, business, email, phone, data, notified_at AS notified FROM briefs ORDER BY created_at DESC LIMIT ?").bind(limit).all();
  const rows = results.map(r => { let d = {}; try { d = JSON.parse(r.data); } catch {} return { ...r, data: d }; });
  if (csv) {
    const cols = ["name", "business", "email", "phone", "what", "currentSite", "look", "inspiration", "when", "style", "template", "package", "estimate"];
    const lines = [["received", ...cols, "colours"].join(",")]
      .concat(rows.map(r => [iso(r.created), ...cols.map(c => r.data[c] ?? r[c] ?? ""), Object.values(r.data.colours || {}).filter(Boolean).join(" ")].map(csvCell).join(",")));
    return download(lines, "briefs");
  }
  const total = await env.DB.prepare("SELECT COUNT(*) AS n FROM briefs").first();
  return json({ kind, mail: mailReady(env), notify: !!env.NOTIFY_TO, total: total.n, rows });
});

export const onRequestDelete = handle(async ({ request, env }) => {
  const u = new URL(request.url);
  const kind = u.searchParams.get("kind");
  const id = +u.searchParams.get("id");
  if (!["signups", "briefs"].includes(kind) || !(id > 0)) return err("Bad request", 400);
  await env.DB.prepare(`DELETE FROM ${kind} WHERE id = ?`).bind(id).run();
  return json({ ok: true });
});

function download(lines, name) {
  const day = new Date().toISOString().slice(0, 10);
  return new Response("﻿" + lines.join("\r\n") + "\r\n", {
    headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="${name}-${day}.csv"`, "Cache-Control": "no-store" }
  });
}
