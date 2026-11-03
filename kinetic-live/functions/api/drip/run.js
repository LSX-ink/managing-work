// POST /api/drip/run  (called once a day by the kinetic-drip Worker)
// Header X-Drip-Token must match the DRIP_TOKEN secret. Body {} runs the follow-up series;
// body {"test": N} sends follow-up N to NOTIFY_TO only (no database changes).
import { handle, err, json, readJson, timingSafeEqual } from "../../_lib/util.js";
import { runDrip, renderStep, siteOf, STEPS } from "../../_lib/drip.js";
import { sendMail, mailReady } from "../../_lib/mail.js";

export const onRequestPost = handle(async ({ request, env }) => {
  const token = (request.headers.get("X-Drip-Token") || "").trim();
  const want = String(env.DRIP_TOKEN || "").trim();   // a secret pasted in a terminal can carry a line break
  if (!want || token.length < 32 || !timingSafeEqual(token, want)) return err("Forbidden", 403);
  const b = await readJson(request, 1024);
  if (b.test !== undefined) {
    const step = +b.test;
    if (!(step >= 1 && step <= STEPS.length)) return err("Bad step", 400);
    if (!mailReady(env) || !env.NOTIFY_TO) return err("Email isn't set up", 503);
    const site = siteOf(env);
    const m = renderStep(step, site, `${site.base}/api/unsubscribe?token=test`);
    const ok = await sendMail(env, { to: env.NOTIFY_TO, replyTo: env.NOTIFY_TO, subject: `[TEST ${step}/${STEPS.length}] ${m.subject}`, text: m.text, html: m.html });
    return json({ ok, step });
  }
  return json(await runDrip(env));
});
