// Email through Resend. Not a route. Sends nothing (and reports false) until the
// RESEND_API_KEY secret is set:  npx wrangler pages secret put RESEND_API_KEY --project-name <project>
// MAIL_FROM must be an address on a domain verified in Resend.

export const EMAIL = /^[^\s@<>()",;:]{1,64}@([a-z0-9-]{1,63}\.)+[a-z]{2,24}$/i;

export const mailReady = env => !!(env.RESEND_API_KEY && env.MAIL_FROM);

export async function sendMail(env, { to, subject, text, html, replyTo }) {
  if (!mailReady(env)) return false;
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify({ from: env.MAIL_FROM, to: [to], subject, text, html, ...(replyTo ? { reply_to: replyTo } : {}) })
    });
    if (!res.ok) console.error("Resend", res.status, (await res.text()).slice(0, 300));
    return res.ok;
  } catch (e) {
    console.error("Resend", e && e.message);
    return false;
  }
}

// Email signature ("Clean light"). base = the site's https origin, used for the logo image.
export const SIG = { name: "Kinetic Web Designs", tagline: "Websites for independent businesses", phone: "07769 789011", tel: "07769789011",
  site: "kineticwebdesigns.co.uk", instagram: "https://instagram.com/kineticwebdesigns" };
export function signatureHtml(base) {
  const s = SIG;
  return `<table cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222222;border-collapse:collapse"><tr>
<td style="padding:0 16px 0 0;vertical-align:top"><img src="${base}/email/kinetic-logo-112.png" width="56" height="56" alt="Kinetic" style="display:block;border:0;border-radius:12px"></td>
<td style="border-left:2px solid #2a47d2;padding:0 0 0 16px;line-height:1.6;vertical-align:top">
<div style="font-weight:bold;font-size:16px;color:#111111">${s.name}</div>
<div style="color:#666666">${s.tagline}</div>
<div style="margin-top:6px">M: <a href="tel:${s.tel}" style="color:#222222;text-decoration:none">${s.phone}</a></div>
<div><a href="https://${s.site}" style="color:#2a47d2">${s.site}</a> &middot; <a href="${s.instagram}" style="color:#2a47d2">Instagram</a></div>
</td></tr></table>`;
}
export const signatureText = () => `${SIG.name}\n${SIG.tagline}\nM: ${SIG.phone}\n${SIG.site} · Instagram: @kineticwebdesigns`;

export const escHtml = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
