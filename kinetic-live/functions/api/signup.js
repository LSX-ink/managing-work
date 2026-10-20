// POST /api/signup { email, marketing } -> saves a sign-up from the email gate and, when email
// is set up, sends a one-off welcome. Offers and news go only to people who ticked the box.
import { handle, err, json, readJson, sameOrigin, siteConfig } from "../_lib/util.js";
import { isBot, visitorId } from "../_lib/visitor.js";
import { sendMail, escHtml, EMAIL } from "../_lib/mail.js";

const PER_HOUR = 5;

export const onRequestPost = handle(async ({ request, env, waitUntil }) => {
  if (!sameOrigin(request)) return err("Forbidden", 403);
  if (isBot(request.headers.get("User-Agent") || "")) return new Response(null, { status: 204 });
  const b = await readJson(request, 2048);
  const email = String(b.email || "").trim().toLowerCase();
  if (email.length > 200 || !EMAIL.test(email)) return err("Please check your email address.", 400);
  const marketing = b.marketing === true ? 1 : 0;
  const visitor = await visitorId(env, request);
  const now = Date.now();

  const recent = await env.DB.prepare("SELECT COUNT(*) AS n FROM signups WHERE visitor = ? AND updated_at > ?").bind(visitor, now - 36e5).first();
  if (recent.n >= PER_HOUR) return err("Too many sign-ups from here. Try again later.", 429);

  const existing = await env.DB.prepare("SELECT id, welcomed_at FROM signups WHERE email = ?").bind(email).first();
  if (existing) {
    // Signing up again can opt in, never silently opt out.
    await env.DB.prepare("UPDATE signups SET marketing = MAX(marketing, ?), updated_at = ?, visitor = ? WHERE id = ?").bind(marketing, now, visitor, existing.id).run();
  } else {
    await env.DB.prepare("INSERT INTO signups (email, marketing, created_at, updated_at, visitor) VALUES (?, ?, ?, ?, ?)").bind(email, marketing, now, now, visitor).run();
  }

  if (!existing || !existing.welcomed_at) {
    const row = await env.DB.prepare("SELECT marketing, unsub_token FROM signups WHERE email = ?").bind(email).first();
    const site = siteConfig(env);
    const base = (site.siteUrl || new URL(request.url).origin).replace(/\/+$/, "");
    const unsub = row.marketing ? `${base}/api/unsubscribe?token=${row.unsub_token}` : "";
    waitUntil((async () => {
      const ok = await sendMail(env, {
        to: email,
        replyTo: env.NOTIFY_TO,
        subject: `Welcome to ${site.siteName}`,
        text: welcomeText(site, base, unsub),
        html: welcomeHtml(site, base, unsub)
      });
      if (ok) await env.DB.prepare("UPDATE signups SET welcomed_at = ? WHERE email = ? AND welcomed_at IS NULL").bind(Date.now(), email).run();
    })());
  }
  return json({ ok: true });
});

const host = base => base.replace(/^https?:\/\//, "");

function welcomeText(site, base, unsub) {
  return `Hi there,

Thank you for joining us, and welcome to ${site.siteName}. We're really glad to have you here for the first time.

We're a UK studio building websites for independent businesses: barbers, studios, cafés, beauty brands, trades and more. Every site is built around your brand and your colours, with online booking, payments and your own owner's dashboard, so customers can find you, book you and pay you without the back-and-forth in your DMs.

While you're here, have a look around:
- Find a style you like and try a real mini website
- Test your colours in our colour lab
- See your price up front, from £395, with monthly payments at checkout

Explore the designs: ${base}/#styles

We hope you'll stay with us. If you have any questions, just reply to this email.

The ${site.siteName} team

--
You're receiving this because you signed up at ${host(base)}.
${unsub ? `Unsubscribe from tips, offers and news: ${unsub}` : "This is a one-off welcome. We won't send you marketing emails."}`;
}

function welcomeHtml(site, base, unsub) {
  const n = escHtml(site.siteName), b = escHtml(base);
  return `<!doctype html><html><body style="margin:0;padding:0;background:#f6f1ec">
<div style="max-width:560px;margin:0 auto;padding:24px 18px;font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;font-size:16px;line-height:1.6;color:#1d1a17">
<div style="font-weight:800;font-size:20px;letter-spacing:-.01em;margin:0 0 18px"><span style="display:inline-block;width:26px;height:26px;border-radius:7px;background:#2a47d2;color:#fff;text-align:center;line-height:26px;font-size:15px;margin-right:8px">K</span>${n}</div>
<div style="background:#ffffff;border-radius:14px;padding:22px 20px">
<p style="margin:0 0 14px">Hi there,</p>
<p style="margin:0 0 14px">Thank you for joining us, and welcome to ${n}. We're really glad to have you here for the first time.</p>
<p style="margin:0 0 14px">We're a UK studio building websites for independent businesses: barbers, studios, cafés, beauty brands, trades and more. Every site is built around your brand and your colours, with online booking, payments and your own owner's dashboard, so customers can find you, book you and pay you without the back-and-forth in your DMs.</p>
<p style="margin:0 0 6px">While you're here, have a look around:</p>
<ul style="margin:0 0 18px;padding-left:20px">
<li>Find a style you like and try a real mini website</li>
<li>Test your colours in our colour lab</li>
<li>See your price up front, from £395, with monthly payments at checkout</li>
</ul>
<p style="margin:0 0 18px"><a href="${b}/#styles" style="display:inline-block;background:#2a47d2;color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:9px;font-weight:700">Explore the designs</a></p>
<p style="margin:0 0 14px">We hope you'll stay with us. If you have any questions, just reply to this email.</p>
<p style="margin:0">The ${n} team</p>
</div>
<p style="font-size:12.5px;color:#7a7068;margin:16px 4px 0">You're receiving this because you signed up at ${escHtml(host(base))}.
${unsub ? `<a href="${escHtml(unsub)}" style="color:#7a7068">Unsubscribe</a> from tips, offers and news.` : "This is a one-off welcome. We won't send you marketing emails."}</p>
</div></body></html>`;
}
