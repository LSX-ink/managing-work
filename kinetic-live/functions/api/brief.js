// POST /api/brief {...} -> saves a website brief from the "start your website" form and, when
// email is set up, emails it to the owner (NOTIFY_TO) with Reply-To set to the client.
import { handle, err, json, readJson, sameOrigin, clampStr } from "../_lib/util.js";
import { isBot, visitorId } from "../_lib/visitor.js";
import { sendMail, escHtml, EMAIL } from "../_lib/mail.js";

const PER_HOUR = 5;
const FIELDS = [
  ["name", "Name", 120], ["business", "Business", 160], ["email", "Email", 200], ["phone", "Phone", 40],
  ["what", "What they do", 1000], ["currentSite", "Current website", 300], ["look", "Look and feel", 2000],
  ["inspiration", "Sites they like", 1000], ["when", "When", 120], ["style", "Style", 80],
  ["template", "Template", 120], ["package", "Package", 160], ["estimate", "Estimate", 60]
];
const HEX = /^#[0-9a-f]{3,8}$/i;

export const onRequestPost = handle(async ({ request, env, waitUntil }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  if (isBot(request.headers.get("User-Agent") || "")) return new Response(null, { status: 204 });
  const b = await readJson(request, 16 * 1024);
  const brief = {};
  for (const [k, , max] of FIELDS) brief[k] = clampStr(b[k], max).trim();
  brief.email = brief.email.toLowerCase();
  const c = b.colours || {};
  brief.colours = Object.fromEntries(["main", "background", "accent"].map(k => [k, HEX.test(String(c[k] || "")) ? String(c[k]) : ""]));
  if (!brief.name || !brief.business || !brief.look) return err("Please add your name, business name and how you'd like it to look.", 400);
  if (!EMAIL.test(brief.email)) return err("Please check your email address.", 400);

  const visitor = await visitorId(env, request);
  const now = Date.now();
  const recent = await env.DB.prepare("SELECT COUNT(*) AS n FROM briefs WHERE visitor = ? AND created_at > ?").bind(visitor, now - 36e5).first();
  if (recent.n >= PER_HOUR) return err("Too many briefs from here. Try again later, or email us.", 429);

  const ins = await env.DB.prepare("INSERT INTO briefs (created_at, name, business, email, phone, data, visitor) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .bind(now, brief.name, brief.business, brief.email, brief.phone || null, JSON.stringify(brief), visitor).run();
  const id = ins.meta && ins.meta.last_row_id;

  if (env.NOTIFY_TO) {
    waitUntil((async () => {
      const ok = await sendMail(env, {
        to: env.NOTIFY_TO,
        replyTo: brief.email,
        subject: `New website brief: ${brief.business}`,
        text: briefText(brief),
        html: briefHtml(brief)
      });
      if (ok && id) await env.DB.prepare("UPDATE briefs SET notified_at = ? WHERE id = ?").bind(Date.now(), id).run();
    })());
  }
  return json({ ok: true });
});

const rows = brief => [...FIELDS.map(([k, label]) => [label, brief[k]]),
  ["Colours", [brief.colours.main, brief.colours.background, brief.colours.accent].filter(Boolean).join(", ")]];

function briefText(brief) {
  return `New website brief\n\n${rows(brief).map(([l, v]) => `${l}: ${v || "-"}`).join("\n")}\n\nReply to this email to answer ${brief.name} directly. All briefs are in your Owner area under "Sign-ups & briefs".`;
}
function briefHtml(brief) {
  return `<div style="font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;font-size:15px;line-height:1.55;color:#1d1a17;max-width:600px">
<p style="font-size:18px;font-weight:700;margin:0 0 12px">New website brief: ${escHtml(brief.business)}</p>
<table style="border-collapse:collapse;width:100%">${rows(brief).map(([l, v]) =>
  `<tr><td style="padding:6px 10px 6px 0;color:#6b625a;vertical-align:top;white-space:nowrap">${escHtml(l)}</td><td style="padding:6px 0;white-space:pre-wrap">${escHtml(v || "-")}</td></tr>`).join("")}</table>
<p style="color:#6b625a">Reply to this email to answer ${escHtml(brief.name)} directly. All briefs are in your Owner area under &ldquo;Sign-ups &amp; briefs&rdquo;.</p></div>`;
}
