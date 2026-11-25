// The follow-up email series ("drip"). Not a route. Used by the owner-area preview and by
// /api/drip/run, which the kinetic-drip Worker calls once a day.
//
// EDIT THE WORDING HERE. Each step: day (after sign-up), subject, body, buttons.
// A body item is a paragraph (string) or a numbered list ({ list: [...] }).
// The greeting, sign-off, signature and unsubscribe footer are added automatically.
// Nothing sends unless DRIP_ENABLED is "1" on the site.
import { escHtml, signatureHtml, signatureText, sendMail, mailReady } from "./mail.js";

export const STEPS = [
  {
    day: 2,
    subject: "Is your website losing you customers?",
    body: [
      "Quick question: when someone finds your business online at 10pm, can they see your prices, book, or pay right there?",
      "If the answer is \"they have to DM me\", you're losing people to whoever makes it easier. Most customers won't wait for a reply.",
      "Every Kinetic website is built so customers can find what they need and act on it straight away: clear prices, booking, and payments, all working on a phone."
    ],
    buttons: [["See example sites", "/#styles"]]
  },
  {
    day: 5,
    subject: "How it works (and what it costs)",
    body: [
      "No surprises, here's exactly how it works:",
      { list: ["Tell us about your business in the short brief on our site.", "Pick your colours and style.",
               "We build it and you check every page.", "It goes live on your own web address."] },
      "Prices: Starter £395, Business £895, Online shop £1,595. You pay half when we start building, and half once everything's complete.",
      "Every site also comes with your own owner's log-in, where you can update products, text and prices, and see your visitors and payments."
    ],
    buttons: [["Start your brief", "/#vision"]]
  },
  {
    day: 9,
    subject: "I'll design your home page for free",
    body: [
      "This week I'm offering a free home page mock-up to a few businesses on our list.",
      "Reply with your business name (and your current website or Instagram, if you have one) and I'll send you a design of what your new home page could look like. No cost, no obligation."
    ],
    buttons: []
  },
  {
    day: 14,
    subject: "After it's live, we look after it",
    body: [
      "A website isn't \"set and forget\". With our monthly hosting and care plan (from £20 a month) we handle your hosting, your web address, backups, updates and text changes, so you can get on with running your business.",
      "You own your website and your web address, always.",
      "If now's the right time, start your brief below. If not, no problem. This is the last email in this series."
    ],
    buttons: [["See the care plans", "/#care"], ["Start your brief", "/#vision"]]
  }
];

const fill = (s, site) => String(s).replace(/\{name\}/g, site.siteName).replace(/\{url\}/g, site.base);

// step: 1-based index into STEPS. unsub: full unsubscribe link. first: first name or "".
export function renderStep(step, site, unsub, first = "") {
  const s = STEPS[step - 1];
  if (!s) throw new Error("No such step");
  const hi = first ? `Hi ${first},` : "Hi there,";
  const host = site.base.replace(/^https?:\/\//, "");
  const buttons = (s.buttons || []).map(([label, path]) => [label, site.base + path]);
  const textBody = s.body.flatMap(p => typeof p === "string" ? [fill(p, site), ""] : [...p.list.map((x, i) => `${i + 1}. ${fill(x, site)}`), ""]);
  const footer = "You're getting this because you asked for tips and offers from Kinetic Web Designs.";
  const text = [
    hi, "", ...textBody,
    ...buttons.map(([l, u]) => `${l}: ${u}`), buttons.length ? "" : null,
    `Alfred, ${site.siteName}`, "",
    signatureText(), "",
    "--", footer, `Unsubscribe in one click: ${unsub}`
  ].filter(x => x !== null).join("\n");
  const n = escHtml(site.siteName);
  const htmlBody = s.body.map(p => typeof p === "string"
    ? `<p style="margin:0 0 14px">${escHtml(fill(p, site))}</p>`
    : `<ol style="margin:0 0 14px;padding-left:22px">${p.list.map(x => `<li style="margin:0 0 4px">${escHtml(fill(x, site))}</li>`).join("")}</ol>`).join("\n");
  const btn = (l, u, primary) => `<a href="${escHtml(u)}" style="display:inline-block;margin:0 8px 8px 0;background:${primary ? "#2a47d2" : "#ffffff"};color:${primary ? "#ffffff" : "#2a47d2"};border:2px solid #2a47d2;text-decoration:none;padding:10px 18px;border-radius:9px;font-weight:700">${escHtml(l)}</a>`;
  const html = `<!doctype html><html><body style="margin:0;padding:0;background:#f6f1ec">
<div style="max-width:560px;margin:0 auto;padding:24px 18px;font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;font-size:16px;line-height:1.6;color:#1d1a17">
<div style="background:#ffffff;border-radius:14px;padding:22px 20px">
<p style="margin:0 0 14px">${escHtml(hi)}</p>
${htmlBody}
${buttons.length ? `<p style="margin:4px 0 10px">${buttons.map(([l, u], i) => btn(l, u, i === buttons.length - 1)).join("")}</p>` : ""}
<p style="margin:0 0 18px">Alfred, ${n}</p>
${signatureHtml(escHtml(site.base))}
</div>
<p style="font-size:12.5px;color:#7a7068;margin:16px 4px 0">${escHtml(footer)}
<a href="${escHtml(unsub)}" style="color:#7a7068">Unsubscribe in one click</a>.</p>
</div></body></html>`;
  return { subject: fill(s.subject, site), text, html, day: s.day };
}

export const siteOf = env => ({
  siteName: env.SITE_NAME || "Kinetic Web Designs",
  base: String(env.SITE_URL || "https://kineticwebdesigns.co.uk").replace(/\/+$/, "")
});

export const dripEnabled = env => /^(1|true|yes|on)$/i.test(String(env.DRIP_ENABLED || "").trim());
const BATCH = 200;          // most emails per run
const MIN_GAP = 20 * 36e5;  // never two follow-ups to one person within 20 hours

// Sends every due follow-up. Stops a person's series for good on unsubscribe, a brief,
// a payment matching their email, the owner's Stop button, or after the last step.
export async function runDrip(env, now = Date.now(), { dryRun = false } = {}) {
  const out = { enabled: dripEnabled(env), mail: mailReady(env), checked: 0, sent: 0, stopped: 0, due: 0 };
  const DB = env.DB;
  await DB.prepare("UPDATE signups SET drip_stopped = 'unsubscribed' WHERE marketing = 0 AND drip_stopped IS NULL AND drip_step > 0").run();
  const { results } = await DB.prepare(
    `SELECT id, email, created_at, drip_step, drip_last_at, unsub_token FROM signups
      WHERE marketing = 1 AND drip_stopped IS NULL AND drip_step < ? ORDER BY created_at LIMIT ?`).bind(STEPS.length, BATCH).all();
  const site = siteOf(env);
  for (const r of results) {
    out.checked++;
    const brief = await DB.prepare("SELECT 1 FROM briefs WHERE lower(email) = lower(?) LIMIT 1").bind(r.email).first();
    const paid = await DB.prepare(
      "SELECT 1 FROM payments WHERE kind = 'payment' AND status = 'succeeded' AND (email = lower(?) OR lower(description) LIKE '%' || lower(?) || '%') LIMIT 1")
      .bind(r.email, r.email).first();
    if (brief || paid) {
      if (!dryRun) await DB.prepare("UPDATE signups SET drip_stopped = ? WHERE id = ?").bind(brief ? "brief" : "paid", r.id).run();
      out.stopped++;
      continue;
    }
    const step = r.drip_step + 1;
    if (r.created_at + STEPS[step - 1].day * 864e5 > now || (r.drip_last_at && now - r.drip_last_at < MIN_GAP)) continue;
    out.due++;
    if (dryRun || !out.enabled || !out.mail) continue;
    const m = renderStep(step, site, `${site.base}/api/unsubscribe?token=${r.unsub_token}`);
    if (await sendMail(env, { to: r.email, replyTo: env.NOTIFY_TO, subject: m.subject, text: m.text, html: m.html })) {
      await DB.prepare("UPDATE signups SET drip_step = ?, drip_last_at = ?, drip_stopped = CASE WHEN ? >= ? THEN 'done' ELSE NULL END WHERE id = ?")
        .bind(step, now, step, STEPS.length, r.id).run();
      out.sent++;
    }
  }
  return out;
}
