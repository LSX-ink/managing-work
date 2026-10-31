// /api/unsubscribe?token=<unsub token> for people on the sign-up list.
// GET shows a one-button page (so email link scanners can't unsubscribe anyone by just opening it);
// POST turns marketing off. The sign-up itself stays on the list.
import { esc } from "../_lib/html.js";
import { siteConfig } from "../_lib/util.js";

const page = (title, body, status = 200) => new Response(`<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>${esc(title)}</title>
<style>body{font:16px/1.5 system-ui,sans-serif;max-width:34rem;margin:12vh auto;padding:0 16px;color:#11141b;background:#f4f5f7}
button{font:inherit;font-weight:600;padding:10px 16px;border-radius:10px;border:0;background:#2a46d1;color:#fff;cursor:pointer}
@media (prefers-color-scheme:dark){body{background:#0e1015;color:#eceef3}}</style></head><body>${body}</body></html>`,
  { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer" } });

async function find(env, token) {
  if (!/^[a-f0-9]{32}$/.test(token || "")) return null;
  return env.DB.prepare("SELECT id, marketing FROM signups WHERE unsub_token = ?").bind(token).first();
}

export async function onRequestGet({ request, env }) {
  const token = new URL(request.url).searchParams.get("token");
  const s = await find(env, token);
  const name = siteConfig(env).siteName;
  if (!s) return page("Link not recognised", `<h1>That link isn't recognised</h1><p>Reply "unsubscribe" to any email from ${esc(name)} and we'll take you off the list.</p>`, 404);
  if (!s.marketing) return page("Unsubscribed", `<h1>You're already unsubscribed</h1><p>You won't get tips, offers or news from ${esc(name)}.</p>`);
  return page("Unsubscribe", `<h1>Stop tips, offers and news?</h1><p>You won't get marketing emails from ${esc(name)} any more.</p>
<form method="post"><input type="hidden" name="token" value="${esc(token)}"><button type="submit">Unsubscribe</button></form>`);
}

export async function onRequestPost({ request, env }) {
  let token = new URL(request.url).searchParams.get("token");
  if (!token) {
    const ct = request.headers.get("Content-Type") || "";
    if (ct.includes("form")) token = (await request.formData()).get("token");
    else if (ct.includes("json")) token = (await request.json().catch(() => ({}))).token;
  }
  const s = await find(env, String(token || ""));
  if (!s) return page("Link not recognised", `<h1>That link isn't recognised</h1>`, 404);
  if (s.marketing) await env.DB.prepare("UPDATE signups SET marketing = 0 WHERE id = ?").bind(s.id).run();
  return page("Unsubscribed", `<h1>Done, you're unsubscribed</h1><p>You won't get tips, offers or news from ${esc(siteConfig(env).siteName)} any more.</p>`);
}
