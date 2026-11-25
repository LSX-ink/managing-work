// GET /api/owner/statement?month=YYYY-MM -> the figures that month's statement email would show
import { handle, json, err, siteConfig } from "../../_lib/util.js";
import { monthStatement, previousMonth } from "../../_lib/stats.js";

export const onRequestGet = handle(async ({ request, env }) => {
  const q = new URL(request.url).searchParams.get("month");
  let y, m;
  if (q) { const mt = /^(\d{4})-(\d{2})$/.exec(q); if (!mt) return err("month must be YYYY-MM"); y = +mt[1]; m = +mt[2] - 1; }
  else ({ y, m } = previousMonth());
  const cfg = siteConfig(env);
  const any = await env.DB.prepare("SELECT COUNT(*) AS n FROM payments").first();
  return json({ stripe: cfg.stripe, any: any.n > 0, statement: await monthStatement(env.DB, y, m, cfg.currency) });
});
