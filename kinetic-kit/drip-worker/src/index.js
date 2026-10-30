// Kinetic follow-up email series: the daily trigger.
// Calls the site's /api/drip/run with the shared DRIP_TOKEN secret. The site does the work
// (it already has the database and the Resend key); this Worker only supplies the schedule.
export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil((async () => {
      const r = await fetch(`${env.SITE_URL.replace(/\/+$/, "")}/api/drip/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Drip-Token": String(env.DRIP_TOKEN || "").trim() },
        body: "{}"
      });
      console.log("drip run", r.status, (await r.text()).slice(0, 300));
    })());
  },
  async fetch() {
    return new Response("Not found", { status: 404 });   // no public endpoints
  }
};
