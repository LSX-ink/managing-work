// Kinetic statements Worker: the logic (index.js holds only the handlers, as Workers require).
//  - scheduled(): on the 1st of each month, emails every opted-in owner last month's real
//    payments and refunds (from the D1 `payments` table the Stripe webhook fills).
//  - email(): receives replies (via Cloudflare Email Routing). A reply saying STOP sets opted_out.
import { monthStatement, previousMonth, money } from "../../functions/_lib/stats.js";
import { esc } from "../../functions/_lib/html.js";
import { makeSender } from "./sender.js";

export const STOP_LINE = "Reply STOP to stop these emails";

export function buildEmail(env, user, st) {
  const site = env.SITE_NAME || "Your website";
  const base = String(env.SITE_URL || "").replace(/\/$/, "");
  const stopUrl = base ? `${base}/api/statements/stop?token=${user.stop_token}` : "";
  const c = st.currency;
  const lines = st.rows.map(r => {
    const when = new Date(r.created).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
    const amt = (r.kind === "refund" ? "-" : "") + money(r.amount, c);
    return { when, what: r.kind === "refund" ? (r.description || "Refund") : (r.description || "Card payment"), who: r.customer || "", amt };
  });
  const subject = `${site}: your ${st.label} statement`;
  const empty = st.rows.length === 0;
  const text = [
    `Hi,`, ``,
    empty ? `Your website took no card payments in ${st.label}.` : `Here's what your website took in ${st.label}.`, ``,
    `Payments (${st.payments}): ${money(st.sales, c)}`,
    `Refunds (${st.refundCount}): -${money(st.refunds, c)}`,
    `Total after refunds: ${money(st.net, c)}`,
    `(Stripe's card fees aren't included; your Stripe dashboard shows them.)`, ``,
    ...(empty ? [] : [`Every payment and refund:`, ...lines.map(l => `${l.when}  ${l.what}${l.who ? " (" + l.who + ")" : ""}  ${l.amt}`), ``]),
    base ? `The full list is in your Owner area: ${base}/owner` : ``, ``,
    `--`,
    `You get this email because card payments are connected to ${site}.`,
    `${STOP_LINE}.` + (stopUrl ? ` Or stop them here: ${stopUrl}` : "")
  ].join("\n");
  const td = 'style="padding:6px 0;border-bottom:1px solid #e3e5ea"';
  const html = `<!doctype html><html><body style="margin:0;background:#f4f5f7;font:15px/1.55 -apple-system,Segoe UI,sans-serif;color:#11141b">
<div style="max-width:600px;margin:0 auto;padding:24px 16px"><div style="background:#fff;border:1px solid #d9dce3;border-radius:12px;padding:22px">
<p style="margin:0 0 12px">Hi,</p>
<p>${empty ? `Your website took no card payments in ${esc(st.label)}.` : `Here's what your website took in ${esc(st.label)}.`}</p>
<table style="width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums">
<tr><td ${td}>Payments (${st.payments})</td><td ${td} align="right">${esc(money(st.sales, c))}</td></tr>
<tr><td ${td}>Refunds (${st.refundCount})</td><td ${td} align="right">-${esc(money(st.refunds, c))}</td></tr>
<tr><td style="padding:8px 0"><b>Total after refunds</b></td><td style="padding:8px 0" align="right"><b>${esc(money(st.net, c))}</b></td></tr></table>
<p style="color:#596173;font-size:13px">Stripe's card fees aren't included; your Stripe dashboard shows them.</p>
${empty ? "" : `<p style="margin:18px 0 6px"><b>Every payment and refund</b></p><table style="width:100%;border-collapse:collapse;font-size:14px">${lines.map(l =>
  `<tr><td ${td}>${esc(l.when)}</td><td ${td}>${esc(l.what)}${l.who ? ` <span style="color:#596173">(${esc(l.who)})</span>` : ""}</td><td ${td} align="right">${esc(l.amt)}</td></tr>`).join("")}</table>`}
${base ? `<p>The full list is in your <a href="${esc(base)}/owner">Owner area</a>.</p>` : ""}
<p style="margin-top:20px;padding-top:12px;border-top:1px solid #d9dce3;color:#596173;font-size:13px">You get this email because card payments are connected to ${esc(site)}.<br>
<b>${STOP_LINE}.</b>${stopUrl ? ` Or <a href="${esc(stopUrl)}">stop them here</a>.` : ""}</p>
</div></div></body></html>`;
  const headers = {};
  const lu = [stopUrl && `<${stopUrl}>`, env.STATEMENT_REPLY_TO && `<mailto:${env.STATEMENT_REPLY_TO}?subject=STOP>`].filter(Boolean);
  if (lu.length) headers["List-Unsubscribe"] = lu.join(", ");
  if (stopUrl) headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click";
  return { subject, text, html, headers };
}

export async function sendStatements(env, nowMs = Date.now()) {
  const { y, m } = previousMonth(nowMs);
  const any = await env.DB.prepare("SELECT COUNT(*) AS n FROM payments").first();
  if (!any.n) return { skipped: "no payments recorded yet (Stripe not connected)", sent: 0 };
  const sender = makeSender(env);
  if (!sender) return { skipped: "no email sender configured (RESEND_API_KEY)", sent: 0 };
  const st = await monthStatement(env.DB, y, m, (env.CURRENCY || "gbp").toLowerCase());
  const { results: users } = await env.DB.prepare(
    `SELECT id, email, stop_token FROM users WHERE opted_out = 0
       AND id NOT IN (SELECT user_id FROM statements_sent WHERE month = ?)`).bind(st.month).all();
  let sent = 0; const failed = [];
  for (const u of users) {
    const mail = buildEmail(env, u, st);
    try {
      await sender.send({ from: env.STATEMENT_FROM, to: u.email, replyTo: env.STATEMENT_REPLY_TO || undefined, ...mail });
      await env.DB.prepare("INSERT OR IGNORE INTO statements_sent (user_id, month, sent_at) VALUES (?, ?, ?)").bind(u.id, st.month, Date.now()).run();
      sent++;
    } catch (e) { failed.push(u.email); console.error("statement to", u.email, "failed:", e.message); }
  }
  return { month: st.month, sent, failed };
}

// ---------- inbound replies ----------
export async function readRaw(stream, max = 128 * 1024) {
  const reader = stream.getReader(); const chunks = []; let n = 0;
  while (n < max) { const { done, value } = await reader.read(); if (done) break; chunks.push(value); n += value.length; }
  try { reader.cancel(); } catch {}
  const all = new Uint8Array(n); let o = 0; for (const c of chunks) { all.set(c.subarray(0, Math.min(c.length, n - o)), o); o += c.length; if (o >= n) break; }
  return new TextDecoder().decode(all);
}
function splitHeaders(raw) {
  const i = raw.search(/\r?\n\r?\n/);
  const head = i < 0 ? raw : raw.slice(0, i), body = i < 0 ? "" : raw.slice(i).replace(/^\r?\n\r?\n/, "");
  const unfolded = head.replace(/\r?\n[ \t]+/g, " ");
  const h = {};
  for (const line of unfolded.split(/\r?\n/)) { const k = line.indexOf(":"); if (k > 0) h[line.slice(0, k).trim().toLowerCase()] = line.slice(k + 1).trim(); }
  return { h, body };
}
// The reply's own text: the first text/plain part, without the quoted original.
export function replyText(raw) {
  let { h, body } = splitHeaders(raw);
  for (let depth = 0; depth < 4; depth++) {
    const ct = h["content-type"] || "text/plain";
    const b = /boundary="?([^";]+)"?/i.exec(ct);
    if (!/^multipart\//i.test(ct) || !b) break;
    const parts = body.split("--" + b[1]).slice(1).filter(p => !p.startsWith("--")).map(p => splitHeaders(p.replace(/^\r?\n/, "")));
    const pick = parts.find(p => /^text\/plain/i.test(p.h["content-type"] || "text/plain")) || parts.find(p => /^multipart\//i.test(p.h["content-type"] || "")) || parts[0];
    if (!pick) return "";
    ({ h, body } = pick);
  }
  const cte = (h["content-transfer-encoding"] || "").toLowerCase();
  if (cte === "base64") { try { body = new TextDecoder().decode(Uint8Array.from(atob(body.replace(/\s+/g, "")), c => c.charCodeAt(0))); } catch {} }
  else if (cte === "quoted-printable") body = body.replace(/=\r?\n/g, "").replace(/=([0-9A-F]{2})/gi, (_, x) => String.fromCharCode(parseInt(x, 16)));
  if (/^text\/html/i.test(h["content-type"] || "")) body = body.replace(/<br\s*\/?>|<\/p>|<\/div>/gi, "\n").replace(/<[^>]+>/g, "").replace(/&nbsp;/g, " ");
  const keep = [];
  for (const line of body.split(/\r?\n/)) {
    if (/^\s*>/.test(line) || /^On .+wrote:\s*$/.test(line) || /^-{2,}\s*Original Message/i.test(line) || /^From:\s/.test(line)) break;
    keep.push(line);
  }
  return keep.join("\n").trim();
}
export function isStop(raw) {
  const { h } = splitHeaders(raw);
  const subj = (h["subject"] || "").replace(/^(re|fwd?):\s*/gi, "").trim();
  if (/^(stop|unsubscribe)\b/i.test(subj)) return true;
  const first = replyText(raw).split(/\r?\n/).map(s => s.trim()).find(Boolean) || "";
  return /^(stop|unsubscribe)\b[.!]*$/i.test(first) || /^stop\b/i.test(first) && first.length <= 40;
}
export function senderAddress(raw, envelopeFrom) {
  const { h } = splitHeaders(raw);
  const from = h["from"] || "";
  const m = /<([^>]+)>/.exec(from) || /([^\s<>"]+@[^\s<>"]+)/.exec(from);
  return [envelopeFrom, m && m[1]].filter(Boolean).map(s => s.trim().toLowerCase());
}

export async function handleReply(env, raw, envelopeFrom) {
  if (!isStop(raw)) return { stop: false };
  const addrs = [...new Set(senderAddress(raw, envelopeFrom))];
  let changed = 0;
  for (const a of addrs) {
    const r = await env.DB.prepare("UPDATE users SET opted_out = 1, opted_out_at = ? WHERE email = ? AND opted_out = 0").bind(Date.now(), a).run();
    changed += r.meta.changes || 0;
  }
  return { stop: true, changed };
}

