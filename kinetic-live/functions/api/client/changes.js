// GET  /api/client/changes  -> this client's change requests, newest first
// POST /api/client/changes  { website, kind, details, links }  -> a new change request; emails the owner
// (owner, 16 Nov 2026: "once signed in there's change requests")
import { handle, json, err, readJson, sameOrigin } from "../../_lib/util.js";
import { sendMail, escHtml } from "../../_lib/mail.js";
import { getClient } from "../../_lib/client.js";

const KINDS = ["Wording", "Pictures", "Design", "New page", "Other"];
const PER_DAY = 10;

export const onRequestGet = handle(async ({ request, env }) => {
  const c = await getClient(env, request);
  if (!c) return err("Please sign in first.", 401);
  const r = await env.DB.prepare(
    "SELECT id, website, kind, details, links, status, created_at, updated_at FROM change_requests WHERE client_id = ? ORDER BY created_at DESC LIMIT 50")
    .bind(c.id).all();
  return json({ requests: r.results || [] }, 200, { "Cache-Control": "no-store" });
});

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const c = await getClient(env, request);
  if (!c) return err("Please sign in first.", 401);
  const body = await readJson(request, 16 * 1024);
  const website = String(body.website || "").trim().slice(0, 300);
  const kind = KINDS.includes(body.kind) ? body.kind : "Other";
  const details = String(body.details || "").trim().slice(0, 4000);
  const links = String(body.links || "").trim().slice(0, 1500);
  if (details.length < 5) return err("Tell us what you'd like changed, in a sentence or two.");
  const now = Date.now();
  const today = await env.DB.prepare("SELECT COUNT(*) AS n FROM change_requests WHERE client_id = ? AND created_at > ?")
    .bind(c.id, now - 864e5).first();
  if ((today?.n || 0) >= PER_DAY) return err("That's a lot of requests for one day. Put the rest in one message, or email us.", 429);
  const res = await env.DB.prepare(
    "INSERT INTO change_requests (client_id, email, website, kind, details, links, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'received', ?, ?)")
    .bind(c.id, c.email, website, kind, details, links, now, now).run();
  const id = res.meta && res.meta.last_row_id;
  if (env.NOTIFY_TO) {
    await sendMail(env, {
      to: env.NOTIFY_TO, replyTo: c.email,
      subject: `Change request #${id}: ${kind} for ${website || c.email}`,
      text: `New change request #${id}\n\nFrom: ${c.email}\nWebsite: ${website || "(not given)"}\nType: ${kind}\n\n${details}\n\n${links ? "Links: " + links + "\n" : ""}`,
      html: `<p><b>New change request #${id}</b></p><p>From: ${escHtml(c.email)}<br>Website: ${escHtml(website || "(not given)")}<br>Type: ${escHtml(kind)}</p>
<p style="white-space:pre-wrap">${escHtml(details)}</p>${links ? `<p>Links: ${escHtml(links)}</p>` : ""}<p>Reply to this email to answer the client.</p>`
    });
  }
  return json({ ok: true, id });
});
