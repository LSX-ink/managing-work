// /api/statements/stop?token=<stop token>
// GET shows a one-button page (so email link scanners can't unsubscribe anyone by just opening it);
// POST sets opted_out. POST also serves RFC 8058 one-click unsubscribe from mail apps.
import { esc } from "../../_lib/html.js";
import { siteConfig } from "../../_lib/util.js";

const page = (title, body, status = 200) => new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${esc(title)}</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:34rem;margin:12vh auto;padding:0 16px;color:#11141b;background:#f4f5f7}
button{font:inherit;font-weight:600;padding:10px 16px;border-radius:10px;border:0;background:#2a46d1;color:#fff;cursor:pointer}
@media (prefers-color-scheme:dark){body{background:#0e1015;color:#eceef3}}</style></head><body>${body}</body></html>`,
  { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer" } });

async function findUser(env, token) {
  if (!/^[a-f0-9]{32}$/.test(token || "")) return null;
  return env.DB.prepare("SELECT id, opted_out FROM users WHERE stop_token = ?").bind(token).first();
}

export async function onRequestGet({ request, env }) {
  const token = new URL(request.url).searchParams.get("token");
  const u = await findUser(env, token);
  const name = siteConfig(env).siteName;
  if (!u) return page("Link not recognised", `<h1>That link isn't recognised</h1><p>You can turn statements off in your Owner area under Account.</p>`, 404);
  if (u.opted_out) return page("Statements stopped", `<h1>Statements are already stopped</h1><p>You won't get monthly statement emails for ${esc(name)}.</p>`);
  return page("Stop statements", `<h1>Stop monthly statements?</h1><p>You won't get statement emails for ${esc(name)} any more. You can turn them back on in your Owner area.</p>
<form method="post"><input type="hidden" name="token" value="${esc(token)}"><button type="submit">Stop these emails</button></form>`);
}

export async function onRequestPost({ request, env }) {
  const url = new URL(request.url);
  let token = url.searchParams.get("token");
  if (!token) {
    const ct = request.headers.get("Content-Type") || "";
    if (ct.includes("form")) token = (await request.formData()).get("token");
    else if (ct.includes("json")) token = (await request.json().catch(() => ({}))).token;
  }
  const u = await findUser(env, String(token || ""));
  if (!u) return page("Link not recognised", `<h1>That link isn't recognised</h1>`, 404);
  if (!u.opted_out) await env.DB.prepare("UPDATE users SET opted_out = 1, opted_out_at = ? WHERE id = ?").bind(Date.now(), u.id).run();
  return page("Statements stopped", `<h1>Done, statements stopped</h1><p>You won't get monthly statement emails for ${esc(siteConfig(env).siteName)} any more.</p>`);
}
