// POST /api/client/link  { email, next }  -> "Forgot your password?": emails a one-time link that signs them in
// and asks for a new password. Always answers the same way, so it never reveals who has an account.
import { handle, json, err, readJson, sameOrigin, b64url, randomBytes, sha256hex } from "../../_lib/util.js";
import { sendMail, EMAIL, escHtml, signatureHtml, signatureText } from "../../_lib/mail.js";
import { safeNext, LINK_MINUTES, LINKS_PER_15_MIN } from "../../_lib/client.js";

export const onRequestPost = handle(async ({ request, env }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  const body = await readJson(request, 4096);
  const email = String(body.email || "").trim().toLowerCase().slice(0, 200);
  if (!EMAIL.test(email)) return err("That doesn't look like an email address. Check it and try again.");
  const next = safeNext(body.next);
  const now = Date.now();
  const recent = await env.DB.prepare("SELECT COUNT(*) AS n FROM client_links WHERE email = ? AND created_at > ?")
    .bind(email, now - 15 * 6e4).first();
  if ((recent?.n || 0) >= LINKS_PER_15_MIN) {
    return err("We've already sent a few links to that address. Check your inbox (and spam), or try again in 15 minutes.", 429);
  }
  const known = await env.DB.prepare("SELECT id FROM clients WHERE email = ?").bind(email).first();
  if (!known) return json({ ok: true });  // no account: say nothing different, send nothing
  const token = b64url(randomBytes(32));
  await env.DB.prepare("INSERT INTO client_links (id, email, next, created_at, expires_at, purpose) VALUES (?, ?, ?, ?, ?, 'reset')")
    .bind(await sha256hex(token), email, next, now, now + LINK_MINUTES * 6e4).run();
  await env.DB.prepare("DELETE FROM client_links WHERE expires_at < ?").bind(now - 864e5).run();
  const base = new URL(request.url).origin;
  const url = `${base}/api/client/verify?t=${encodeURIComponent(token)}`;
  const sent = await sendMail(env, {
    to: email,
    subject: "Reset your Kinetic Web Designs password",
    text: `Hi,\n\nTap this link to choose a new password for your Kinetic Web Designs account:\n${url}\n\nIt works once and runs out in ${LINK_MINUTES} minutes. If you didn't ask for it, you can ignore this email and your password stays the same.\n\n${signatureText()}`,
    html: `<p>Hi,</p><p>Tap the button to choose a new password for your Kinetic Web Designs account.</p>
<p><a href="${escHtml(url)}" style="display:inline-block;background:#2a46d1;color:#fff;padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:600">Choose a new password</a></p>
<p style="color:#535a69;font-size:14px">It works once and runs out in ${LINK_MINUTES} minutes. If you didn't ask for it, you can ignore this email and your password stays the same.</p>${signatureHtml(base)}`
  });
  if (!sent) return err("We couldn't send the email just now. Please try again in a minute.", 502);
  return json({ ok: true });
});
