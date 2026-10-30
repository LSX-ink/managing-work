// GET /api/owner/drip-preview?step=1..N[&format=text] -> how a follow-up email looks (owner only).
import { handle, err } from "../../_lib/util.js";
import { STEPS, renderStep, siteOf } from "../../_lib/drip.js";

export const onRequestGet = handle(async ({ request, env }) => {
  const step = +new URL(request.url).searchParams.get("step");
  if (!(step >= 1 && step <= STEPS.length)) return err("Pick a step from 1 to " + STEPS.length, 400);
  const site = siteOf(env);
  const m = renderStep(step, site, `${site.base}/api/unsubscribe?token=preview`);
  const text = new URL(request.url).searchParams.get("format") === "text";
  const head = `<p style="font:13px system-ui;background:#fff6d6;margin:0;padding:8px 12px">Preview of follow-up ${step} of ${STEPS.length} · sent on day ${m.day} · Subject: <b>${m.subject.replace(/[<>&]/g, "")}</b></p>`;
  return new Response(text ? `Subject: ${m.subject}\n\n${m.text}` : m.html.replace("<body", "<body data-preview").replace(/(<body[^>]*>)/, `$1${head}`), {
    headers: { "Content-Type": `${text ? "text/plain" : "text/html"}; charset=utf-8`, "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; img-src https: data:; style-src 'unsafe-inline'", "X-Frame-Options": "DENY" }
  });
});
