// Kinetic statements Worker.
//  - scheduled(): on the 1st of each month, emails every opted-in owner last month's real
//    payments and refunds (from the D1 `payments` table the Stripe webhook fills).
//  - email(): receives replies (via Cloudflare Email Routing). A reply saying STOP sets opted_out.
import { sendStatements, handleReply, readRaw } from "./statements.js";

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(sendStatements(env, event.scheduledTime || Date.now()).then(r => console.log("statements", JSON.stringify(r))));
  },
  async email(message, env) {
    const raw = await readRaw(message.raw);
    const r = await handleReply(env, raw, message.from);
    console.log("reply from", message.from, JSON.stringify(r));
    if (!r.stop && env.FORWARD_TO) await message.forward(env.FORWARD_TO);
  }
};
