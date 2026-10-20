// Kinetic follow-up email series ("drip") Worker.
// Daily cron: for each sign-up who ticked marketing consent, sends the next due follow-up from
// kinetic-live/functions/_lib/drip.js and records it in D1 (signups.drip_step / drip_last_at).
// Stops for good when the person unsubscribes, sends a brief, pays, or the owner stops them.
// Sends NOTHING unless DRIP_ENABLED is "1"/"true" and RESEND_API_KEY + MAIL_FROM are set.
import { STEPS, renderStep, siteOf } from "../../../kinetic-live/functions/_lib/drip.js";
import { sendMail, mailReady } from "../../../kinetic-live/functions/_lib/mail.js";

const enabled = env => /^(1|true|yes|on)$/i.test(String(env.DRIP_ENABLED || "").trim());
const BATCH = 200;          // most emails per run
const MIN_GAP = 20 * 36e5;  // never two follow-ups to one person within 20 hours

export async function runDrip(env, now = Date.now(), { dryRun = false } = {}) {
  const out = { enabled: enabled(env), mail: mailReady(env), checked: 0, sent: 0, stopped: 0, due: [] };
  const DB = env.DB;
  // People who unsubscribed after starting: close their series.
  await DB.prepare("UPDATE signups SET drip_stopped = 'unsubscribed' WHERE marketing = 0 AND drip_stopped IS NULL AND drip_step > 0").run();
  const { results } = await DB.prepare(
    `SELECT id, email, created_at, drip_step, drip_last_at, unsub_token FROM signups
      WHERE marketing = 1 AND drip_stopped IS NULL AND drip_step < ? ORDER BY created_at LIMIT ?`).bind(STEPS.length, BATCH).all();
  const site = siteOf(env);
  for (const r of results) {
    out.checked++;
    const brief = await DB.prepare("SELECT 1 FROM briefs WHERE lower(email) = lower(?) LIMIT 1").bind(r.email).first();
    const paid = await DB.prepare(
      "SELECT 1 FROM payments WHERE kind = 'payment' AND status = 'succeeded' AND (lower(customer) = lower(?) OR lower(description) LIKE '%' || lower(?) || '%') LIMIT 1")
      .bind(r.email, r.email).first();
    if (brief || paid) {
      if (!dryRun) await DB.prepare("UPDATE signups SET drip_stopped = ? WHERE id = ?").bind(brief ? "brief" : "paid", r.id).run();
      out.stopped++;
      continue;
    }
    const step = r.drip_step + 1;                       // next follow-up, 1-based
    const dueAt = r.created_at + STEPS[step - 1].day * 864e5;
    if (dueAt > now || (r.drip_last_at && now - r.drip_last_at < MIN_GAP)) continue;
    out.due.push({ id: r.id, step });
    if (dryRun || !out.enabled || !out.mail) continue;
    const unsub = `${site.base}/api/unsubscribe?token=${r.unsub_token}`;
    const m = renderStep(step, site, unsub);
    const ok = await sendMail(env, { to: r.email, replyTo: env.NOTIFY_TO, subject: m.subject, text: m.text, html: m.html });
    if (ok) {
      await DB.prepare("UPDATE signups SET drip_step = ?, drip_last_at = ?, drip_stopped = CASE WHEN ? >= ? THEN 'done' ELSE NULL END WHERE id = ?")
        .bind(step, now, step, STEPS.length, r.id).run();
      out.sent++;
    }
  }
  return out;
}

export default {
  async scheduled(event, env, ctx) {
    if (!enabled(env)) { console.log("drip: switched off (DRIP_ENABLED not set)"); return; }
    ctx.waitUntil(runDrip(env, event.scheduledTime || Date.now()).then(r => console.log("drip", JSON.stringify({ ...r, due: r.due.length }))));
  },
  async fetch() {
    return new Response("Not found", { status: 404 });   // no public endpoints
  }
};
