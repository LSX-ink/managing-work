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

export const escHtml = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
