// The follow-up email series. Not a route. Shared by the Pages owner-area preview and the
// kinetic-drip Worker (which sends it on a daily cron).
//
// EDIT THE WORDING HERE. Each step: day (after sign-up), subject, and body paragraphs.
// {name} is the site name, {url} the site address. The HTML and plain-text versions,
// the signature and the unsubscribe footer are added automatically.
// Nothing sends until DRIP_ENABLED is set on the Worker.
import { escHtml, signatureHtml, signatureText } from "./mail.js";

export const STEPS = [
  {
    day: 2,
    subject: "[DRAFT] A quick look at what we build",
    body: [
      "PLACEHOLDER: short intro and two or three example sites (before and after).",
      "PLACEHOLDER: one line on what changed for that business."
    ],
    button: ["See the designs", "/#styles"]
  },
  {
    day: 5,
    subject: "[DRAFT] How it works, and what it costs",
    body: [
      "PLACEHOLDER: the steps from brief to launch.",
      "PLACEHOLDER: prices from £395, half when we start building and half once everything is complete."
    ],
    button: ["See prices", "/#quote"]
  },
  {
    day: 9,
    subject: "[DRAFT] Want a free mock-up of your home page?",
    body: [
      "PLACEHOLDER: offer a free one-page mock-up in their colours.",
      "PLACEHOLDER: how to ask for it (reply to this email or send a brief)."
    ],
    button: ["Start your website", "/#vision"]
  },
  {
    day: 14,
    subject: "[DRAFT] Looking after your site after launch",
    body: [
      "PLACEHOLDER: the monthly care plan (hosting, updates, backups, small changes).",
      "PLACEHOLDER: short FAQ and a friendly last nudge."
    ],
    button: ["See the care plans", "/#care"]
  }
];

const fill = (s, site) => String(s).replace(/\{name\}/g, site.siteName).replace(/\{url\}/g, site.base);

// step: 1-based index into STEPS. unsub: full unsubscribe link.
export function renderStep(step, site, unsub) {
  const s = STEPS[step - 1];
  if (!s) throw new Error("No such step");
  const paras = s.body.map(p => fill(p, site));
  const btnUrl = s.button ? site.base + s.button[1] : "";
  const host = site.base.replace(/^https?:\/\//, "");
  const text = [
    "Hi there,", "",
    ...paras.flatMap(p => [p, ""]),
    s.button ? `${s.button[0]}: ${btnUrl}` : "", "",
    `The ${site.siteName} team`, "",
    signatureText(), "",
    "--",
    `You're receiving this because you signed up at ${host} and asked for tips, offers and news.`,
    `Unsubscribe: ${unsub}`
  ].join("\n");
  const n = escHtml(site.siteName);
  const html = `<!doctype html><html><body style="margin:0;padding:0;background:#f6f1ec">
<div style="max-width:560px;margin:0 auto;padding:24px 18px;font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;font-size:16px;line-height:1.6;color:#1d1a17">
<div style="background:#ffffff;border-radius:14px;padding:22px 20px">
<p style="margin:0 0 14px">Hi there,</p>
${paras.map(p => `<p style="margin:0 0 14px">${escHtml(p)}</p>`).join("\n")}
${s.button ? `<p style="margin:4px 0 18px"><a href="${escHtml(btnUrl)}" style="display:inline-block;background:#2a47d2;color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:9px;font-weight:700">${escHtml(s.button[0])}</a></p>` : ""}
<p style="margin:0 0 18px">The ${n} team</p>
${signatureHtml(escHtml(site.base))}
</div>
<p style="font-size:12.5px;color:#7a7068;margin:16px 4px 0">You're receiving this because you signed up at ${escHtml(host)} and asked for tips, offers and news.
<a href="${escHtml(unsub)}" style="color:#7a7068">Unsubscribe</a>.</p>
</div></body></html>`;
  return { subject: fill(s.subject, site), text, html, day: s.day };
}

export const siteOf = env => ({
  siteName: env.SITE_NAME || "Kinetic Web Designs",
  base: String(env.SITE_URL || "https://kineticwebdesigns.co.uk").replace(/\/+$/, "")
});
