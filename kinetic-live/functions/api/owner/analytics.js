// GET /api/owner/analytics?range=minute|hour|day|week|month|year&tz=<minutes east of UTC>
// Everything here is counted from real rows; with no data every figure is zero.
import { handle, json, err, siteConfig } from "../../_lib/util.js";
import { RANGES, bucketSql, buckets, clampOffset } from "../../_lib/stats.js";

export const onRequestGet = handle(async ({ request, env }) => {
  const url = new URL(request.url);
  const range = url.searchParams.get("range") || "day";
  if (!RANGES[range]) return err("Unknown range");
  const off = clampOffset(url.searchParams.get("tz"));
  const cfg = siteConfig(env);
  const now = Date.now();
  const bs = buckets(range, off, now);
  const from = bs[0].start;
  const DB = env.DB;
  const k = col => bucketSql(range, col, off);

  const [views, evs, pay, top, src, dev, v24, vPrev, anyPay] = await DB.batch([
    DB.prepare(`SELECT ${k("ts")} AS k, COUNT(*) AS views, COUNT(DISTINCT visitor) AS visitors FROM pageviews WHERE ts >= ? GROUP BY 1`).bind(from),
    DB.prepare(`SELECT ${k("ts")} AS k, name, COUNT(*) AS n FROM events WHERE ts >= ? GROUP BY 1, 2`).bind(from),
    DB.prepare(`SELECT ${k("created")} AS k, kind, SUM(amount) AS amount, COUNT(*) AS n FROM payments
                 WHERE created >= ? AND status = 'succeeded' AND currency = ? GROUP BY 1, 2`).bind(from, cfg.currency),
    DB.prepare("SELECT path, COUNT(*) AS views FROM pageviews WHERE ts >= ? GROUP BY path ORDER BY views DESC LIMIT 10").bind(from),
    DB.prepare("SELECT ref_host AS host, COUNT(*) AS views FROM pageviews WHERE ts >= ? GROUP BY ref_host ORDER BY views DESC").bind(from),
    DB.prepare("SELECT device, COUNT(*) AS views FROM pageviews WHERE ts >= ? GROUP BY device ORDER BY views DESC").bind(from),
    DB.prepare("SELECT COUNT(DISTINCT visitor) AS n FROM pageviews WHERE ts >= ?").bind(now - 864e5),
    DB.prepare("SELECT COUNT(DISTINCT visitor) AS n FROM pageviews WHERE ts >= ? AND ts < ?").bind(now - 2 * 864e5, now - 864e5),
    DB.prepare("SELECT COUNT(*) AS n FROM payments").bind()
  ]);

  const idx = new Map(bs.map((b, i) => [String(b.key), i]));
  const out = bs.map(b => ({ label: b.label, start: b.start, views: 0, visitors: 0, revenue: 0, refunds: 0, events: {} }));
  const at = key => out[idx.get(String(key))];
  for (const r of views.results) { const o = at(r.k); if (o) { o.views = r.views; o.visitors = r.visitors; } }
  for (const r of evs.results) { const o = at(r.k); if (o) o.events[r.name] = r.n; }
  for (const r of pay.results) { const o = at(r.k); if (o) o[r.kind === "refund" ? "refunds" : "revenue"] = r.amount; }

  const sum = f => out.reduce((a, o) => a + f(o), 0);
  const visitorsRange = await DB.prepare("SELECT COUNT(DISTINCT visitor) AS n FROM pageviews WHERE ts >= ?").bind(from).first();
  const payments = pay.results.filter(r => r.kind === "payment").reduce((a, r) => a + r.n, 0);
  return json({
    range, label: RANGES[range].label, per: RANGES[range].per, currency: cfg.currency,
    stripe: cfg.stripe, hasPayments: anyPay.results[0].n > 0,
    events: cfg.events,
    buckets: out,
    totals: {
      views: sum(o => o.views), visitors: visitorsRange.n,
      visitors24h: v24.results[0].n, visitorsPrev24h: vPrev.results[0].n,
      revenue: sum(o => o.revenue), refunds: sum(o => o.refunds), payments,
      events: Object.fromEntries(cfg.events.map(e => [e.name, sum(o => o.events[e.name] || 0)]))
    },
    topPages: top.results,
    sources: src.results.map(r => ({ host: r.host, views: r.views })),
    devices: dev.results.map(r => ({ device: r.device || "computer", views: r.views }))
  });
});
