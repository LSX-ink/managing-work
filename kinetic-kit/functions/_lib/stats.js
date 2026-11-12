// Analytics bucketing and monthly statement maths, shared by the Pages Functions
// and the statements Worker. Exports no onRequest handlers (not a route).

export const RANGES = {
  minute: { n: 60, label: "Last hour", per: "per minute" },
  hour:   { n: 24, label: "Last 24 hours", per: "per hour" },
  day:    { n: 7,  label: "Last 7 days", per: "per day" },
  week:   { n: 12, label: "Last 12 weeks", per: "per week" },
  month:  { n: 12, label: "Last 12 months", per: "per month" },
  year:   { n: 5,  label: "Last 5 years", per: "per year" }
};
const SIZE = { minute: 6e4, hour: 36e5, day: 864e5, week: 6048e5 };
const WEEK_SHIFT = 4 * 864e5; // 1 Jan 1970 was a Thursday; weeks start on Monday
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const p2 = n => String(n).padStart(2, "0");

// SQL expression giving the bucket key for a ms timestamp column. `off` is the viewer's
// UTC offset in ms (already clamped to an integer), so hours and days match their clock.
export function bucketSql(range, col, off) {
  const t = `(${col} + ${off})`;
  if (range === "week") return `CAST((${t} - ${WEEK_SHIFT}) / ${SIZE.week} AS INTEGER)`;
  if (SIZE[range]) return `CAST(${t} / ${SIZE[range]} AS INTEGER)`;
  if (range === "month") return `strftime('%Y-%m', ${t} / 1000, 'unixepoch')`;
  return `strftime('%Y', ${t} / 1000, 'unixepoch')`;
}

// The last n buckets ending now: [{ key, start (ms, UTC), label }]
export function buckets(range, off, nowMs = Date.now()) {
  const { n } = RANGES[range];
  const out = [];
  const local = nowMs + off;
  if (SIZE[range]) {
    const size = SIZE[range], shift = range === "week" ? WEEK_SHIFT : 0;
    const cur = Math.floor((local - shift) / size);
    for (let k = cur - n + 1; k <= cur; k++) {
      const startLocal = k * size + shift, d = new Date(startLocal);
      let label;
      if (range === "minute") label = `${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}`;
      else if (range === "hour") label = `${p2(d.getUTCHours())}:00`;
      else if (range === "day") label = `${DAYS[d.getUTCDay()]} ${d.getUTCDate()}`;
      else label = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
      out.push({ key: k, start: startLocal - off, label });
    }
  } else {
    const d = new Date(local);
    let y = d.getUTCFullYear(), m = d.getUTCMonth();
    for (let i = n - 1; i >= 0; i--) {
      if (range === "month") {
        const mm = ((m - i) % 12 + 12) % 12, yy = y + Math.floor((m - i) / 12);
        out.push({ key: `${yy}-${p2(mm + 1)}`, start: Date.UTC(yy, mm, 1) - off, label: `${MONTHS[mm]}${mm === 0 || i === n - 1 ? " " + String(yy).slice(2) : ""}` });
      } else {
        out.push({ key: String(y - i), start: Date.UTC(y - i, 0, 1) - off, label: String(y - i) });
      }
    }
  }
  return out;
}

export function clampOffset(minutes) {
  const m = Math.round(Number(minutes) || 0);
  return Math.max(-14 * 60, Math.min(14 * 60, m)) * 6e4;
}

// ---------- monthly statements ----------
export function previousMonth(nowMs = Date.now()) {
  const d = new Date(nowMs);
  let y = d.getUTCFullYear(), m = d.getUTCMonth() - 1;
  if (m < 0) { m = 11; y--; }
  return { y, m };
}
export function monthName(y, m) {
  return new Date(Date.UTC(y, m, 1)).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
}

// Real figures for one calendar month (UTC) straight from the payments table.
export async function monthStatement(DB, y, m, currency = "gbp") {
  const from = Date.UTC(y, m, 1), to = Date.UTC(y, m + 1, 1);
  const { results } = await DB.prepare(
    `SELECT id, kind, status, amount, currency, description, customer, created FROM payments
      WHERE created >= ? AND created < ? AND status = 'succeeded' AND currency = ? ORDER BY created`)
    .bind(from, to, currency).all();
  const rows = results || [];
  const sales = rows.filter(r => r.kind === "payment").reduce((a, r) => a + r.amount, 0);
  const refunds = rows.filter(r => r.kind === "refund").reduce((a, r) => a + r.amount, 0);
  return {
    month: `${y}-${p2(m + 1)}`, label: monthName(y, m), currency,
    sales, refunds, net: sales - refunds,
    payments: rows.filter(r => r.kind === "payment").length,
    refundCount: rows.filter(r => r.kind === "refund").length,
    rows
  };
}

export function money(minor, currency = "gbp") {
  try { return new Intl.NumberFormat("en-GB", { style: "currency", currency: currency.toUpperCase() }).format(minor / 100); }
  catch { return (minor / 100).toFixed(2) + " " + currency.toUpperCase(); }
}
