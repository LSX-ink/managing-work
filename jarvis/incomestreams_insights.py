"""Income streams part 2: the dashboard and the numbers behind it, worked out from what the user logged.

Stacked month-by-month dashboard, passive vs active share, best and worst stream, growth, money per hour, a
diversification score and a "too reliant on one stream" warning. All of it looks backwards at logged money: the run
rate is an average of the past, not a forecast, and nothing here promises income.
"""

import homestore as hs
import incomestreams_store as st
import screen
from config import Settings

NAMES = {"income_insights"}
ACTIONS = ["dashboard", "month_table", "monthly_chart", "passive_share", "stream_share", "best_worst", "growth", "per_hour",
           "diversification", "reliance_check", "compare_months", "run_rate", "yearly_summary", "net_profit",
           "missing_months"]
RELIANCE = 60
MAX_STACK = 8


def _months(args: dict, default: int = 6) -> list[str]:
    return st.months_back(int(hs.number(args.get("months") or default, "number of months", 1, 24)))


def _setup(settings: Settings):
    data = st.load(settings)
    st.need_streams(data)
    return data, st.entries(settings, data)


def _totals(data: dict, rows: list, months) -> list[tuple[dict, float]]:
    out = [(s, st.total(rows, s["id"], set(months))) for s in data["streams"]]
    return sorted(out, key=lambda x: -x[1])


def _pct(part: float, whole: float) -> int:
    return round(part / whole * 100) if whole else 0


def dashboard(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    ranked = [(s, t) for s, t in _totals(data, rows, months) if t > 0]
    grand = sum(t for _, t in ranked)
    if not ranked:
        raise ValueError("Nothing is logged for those months yet. Tell me what you earned from a stream.")
    streams = [{"name": s["name"], "type": s["type"], "values": [st.total(rows, s["id"], {m}) for m in months]}
               for s, _ in ranked[:MAX_STACK]]
    rest = ranked[MAX_STACK:]
    if rest:
        streams.append({"name": "Other", "type": "mixed", "values": [sum(st.total(rows, s["id"], {m}) for s, _ in rest) for m in months]})
    passive = sum(st.WEIGHT[s["type"]] * t for s, t in ranked)
    best = ranked[0]
    summary = [f"Total {st.gbp(grand)} over {len(months)} months", f"Leaning passive: {_pct(passive, grand)}%",
               f"Biggest: {best[0]['name']} ({_pct(best[1], grand)}%)"]
    return screen.Shown(f"Income over the last {len(months)} months: {st.gbp(grand)}, biggest stream {best[0]['name']}. " + st.HONEST,
                        screen.card(st.DASH_KIND, "Income dashboard", "incomestreams-dashboard", data={
                            "months": [st.month_label(m) for m in months], "streams": streams,
                            "totals": [round(sum(x["values"][i] for x in streams), 2) for i in range(len(months))],
                            "summary": summary, "note": st.HONEST},
                                    buttons=[{"label": "Best and worst", "say": "Which income stream is best and worst?"},
                                             {"label": "Am I too reliant?", "say": "Am I too reliant on one income stream?"},
                                             {"label": "Goals", "say": "How am I doing against my income goals?"}]))


def month_table(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    table = [[s["name"]] + [st.gbp(st.total(rows, s["id"], {m})) if st.total(rows, s["id"], {m}) else "-" for m in months]
             for s, _ in _totals(data, rows, months)]
    table.append(["Total"] + [st.gbp(st.total(rows, None, {m})) for m in months])
    return screen.Shown(f"Money in by stream for {len(months)} months. " + st.HONEST,
                        screen.card("table", "Income by month", "incomestreams-months",
                                    columns=["Stream"] + [st.month_label(m) for m in months][-7:], rows=[r[:1] + r[1:][-7:] for r in table]))


def monthly_chart(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args, 12)
    values = [st.total(rows, None, {m}) for m in months]
    return screen.Shown(f"Total extra income per month over {len(months)} months, from {st.gbp(min(values))} to {st.gbp(max(values))}.",
                        screen.card("chart", "Extra income per month", "incomestreams-chart",
                                    chart={"type": "line", "labels": [st.month_label(m) for m in months], "values": values, "unit": "£"}))


def passive_share(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    by = {t: sum(v for s, v in _totals(data, rows, months) if s["type"] == t) for t in st.TYPES}
    grand = sum(by.values())
    if not grand:
        raise ValueError("Nothing is logged for those months yet.")
    bars = [{"label": st.type_word(t).capitalize(), "value": by[t], "max": grand, "text": f"{st.gbp(by[t])} ({_pct(by[t], grand)}%)"}
            for t in st.TYPES]
    lean = _pct(sum(st.WEIGHT[t] * by[t] for t in st.TYPES), grand)
    return screen.Shown(f"About {_pct(by['passive'], grand)}% of the last {len(months)} months came from passive-ish streams "
                        f"({lean}% if part-active ones count as half). Passive-ish usually still needs some work.",
                        screen.card(st.BARS_KIND, "Active vs passive share", "incomestreams-passive", data={
                            "rows": bars, "note": "Passive-ish streams still take set-up and upkeep, and can dry up."}))


def stream_share(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    ranked = [(s, t) for s, t in _totals(data, rows, months) if t > 0]
    grand = sum(t for _, t in ranked)
    if not grand:
        raise ValueError("Nothing is logged for those months yet.")
    bars = [{"label": s["name"], "value": t, "max": grand, "text": f"{st.gbp(t)} ({_pct(t, grand)}%)",
             "say": f"Show my {s['name']} income stream."} for s, t in ranked]
    return screen.Shown(f"{ranked[0][0]['name']} is the biggest at {_pct(ranked[0][1], grand)}% of {st.gbp(grand)}.",
                        screen.card(st.BARS_KIND, "Share by stream", "incomestreams-share", data={"rows": bars[:20], "note": ""}))


def best_worst(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    live = [(s, t) for s, t in _totals(data, rows, months) if s["status"] != "ended"]
    earning = [(s, t) for s, t in live if t > 0]
    if not earning:
        raise ValueError("Nothing is logged for those months yet.")
    best, worst = earning[0], earning[-1]
    silent = [s["name"] for s, t in live if t == 0]
    table = [["Best", best[0]["name"], st.gbp(best[1])], ["Lowest earner", worst[0]["name"], st.gbp(worst[1])]]
    table += [["Nothing logged", n, "£0"] for n in silent]
    said = f"Best: {best[0]['name']} at {st.gbp(best[1])}. Lowest earner: {worst[0]['name']} at {st.gbp(worst[1])}."
    if len(earning) == 1:
        said = f"Only {best[0]['name']} has money logged, {st.gbp(best[1])}."
    return screen.Shown(said + " Money alone isn't everything: check hours too.",
                        screen.card("table", f"Best and worst ({len(months)} months)", "incomestreams-bestworst",
                                    columns=["", "Stream", "Money in"], rows=table,
                                    buttons=[{"label": "Money per hour", "say": "Which income stream pays best per hour?"}]))


def _avg(rows: list, sid, months: list[str]) -> float:
    return st.total(rows, sid, set(months)) / len(months)


def growth(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    end = st.add_months(st.month_of(hs.today()), -1)
    recent, prior = st.months_back(3, end), st.months_back(3, st.add_months(end, -3))
    table = []
    for s, _ in _totals(data, rows, recent + prior):
        a, b = _avg(rows, s["id"], prior), _avg(rows, s["id"], recent)
        if not a and not b:
            continue
        change = "new" if not a else f"{(b - a) / a * 100:+.0f}%"
        table.append([s["name"], st.gbp(a), st.gbp(b), change])
    a, b = _avg(rows, None, prior), _avg(rows, None, recent)
    table.append(["All streams", st.gbp(a), st.gbp(b), "new" if not a else f"{(b - a) / a * 100:+.0f}%"])
    said = ("Not enough history yet to compare." if not a and not b else
            f"Average per month: {st.gbp(a)} before, {st.gbp(b)} in the last three full months.")
    return screen.Shown(said + " Past months only, not a forecast.",
                        screen.card("table", "Growth: last 3 full months vs the 3 before", "incomestreams-growth",
                                    columns=["Stream", "Before (avg/mo)", "Recent (avg/mo)", "Change"], rows=table))


def per_hour(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    ranked, none = [], []
    for s in data["streams"]:
        hours = st.hours_total(data, s["id"], set(months))
        net = st.total(rows, s["id"], set(months)) - st.total(rows, s["id"], set(months), field="costs")
        if hours:
            ranked.append((s, hours, net, round(net / hours, 2)))
        elif net > 0:
            none.append(s["name"])
    if not ranked:
        raise ValueError("Log some hours per stream first, for example: I spent 3 hours on reselling.")
    ranked.sort(key=lambda r: -r[3])
    table = [[s["name"], f"{h:g}", st.gbp(n), st.gbp(p)] for s, h, n, p in ranked]
    table += [[n, "-", "", "no hours logged"] for n in none]
    return screen.Shown(f"Best pay per hour: {ranked[0][0]['name']} at {st.gbp(ranked[0][3])} an hour; lowest "
                        f"{ranked[-1][0]['name']} at {st.gbp(ranked[-1][3])}. Only counts hours you logged.",
                        screen.card("table", f"Money per hour ({len(months)} months)", "incomestreams-perhour",
                                    columns=["Stream", "Hours", "Money after costs", "Per hour"], rows=table))


def _shares(data: dict, rows: list, months) -> list[tuple[dict, float, float]]:
    ranked = [(s, t) for s, t in _totals(data, rows, months) if t > 0]
    grand = sum(t for _, t in ranked)
    return [(s, t, t / grand) for s, t in ranked] if grand else []


def _score(shares: list) -> tuple[int, float]:
    hhi = sum(p * p for _, _, p in shares)
    effective = 1 / hhi if hhi else 0
    return min(100, round((effective - 1) / 3 * 100)), effective


def diversification(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    shares = _shares(data, rows, _months(args))
    if not shares:
        raise ValueError("Nothing is logged for those months yet.")
    score, effective = _score(shares)
    band = "well spread" if score >= 70 else "fairly spread" if score >= 40 else "leaning on one or two streams"
    top = shares[0]
    bars = [{"label": s["name"], "value": p * 100, "max": 100, "text": f"{p * 100:.0f}%", "warn": p * 100 >= RELIANCE}
            for s, _, p in shares]
    return screen.Shown(f"Diversification score {score} out of 100: {band}. Your income behaves like about {effective:.1f} equal streams; "
                        f"{top[0]['name']} is {top[2] * 100:.0f}% of it.",
                        screen.card(st.BARS_KIND, f"Diversification score: {score}/100", "incomestreams-diversification", data={
                            "rows": bars, "note": "100 means income spread like four or more equal streams. It is a simple guide, "
                                                  "not financial advice."},
                                    buttons=[{"label": "Am I too reliant?", "say": "Am I too reliant on one income stream?"}]))


def reliance_check(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    limit = hs.number(args.get("threshold") or RELIANCE, "percentage", 10, 100)
    months = _months(args)
    shares = _shares(data, rows, months)
    if not shares:
        raise ValueError("Nothing is logged for those months yet.")
    over = [(s, t, p) for s, t, p in shares if p * 100 >= limit]
    if not over:
        return screen.Shown(f"No single stream is {limit:.0f}% or more of your income, so you're not leaning on just one.",
                            screen.card("list", "Reliance check", "incomestreams-reliance",
                                        items=[f"{s['name']}: {p * 100:.0f}%" for s, _, p in shares]))
    s, t, p = over[0]
    monthly = st.total(rows, None, set(months)) / len(months)
    left = monthly - t / len(months)
    items = [f"Warning: {s['name']} is {p * 100:.0f}% of your extra income.",
             f"If it stopped, you'd be down about {st.gbp(t / len(months))} a month, leaving about {st.gbp(left)}.",
             "Ideas: build a second stream, or a small buffer in savings. Nothing is guaranteed either way."]
    return screen.Shown(f"Careful: {s['name']} is {p * 100:.0f}% of your extra income, over your {limit:.0f}% line. "
                        "Too reliant on one stream can hurt if it stops.",
                        screen.card("list", "Too reliant on one stream", "incomestreams-reliance", items=items,
                                    buttons=[{"label": "Stream kinds", "say": "Show me kinds of income streams."}]))


def compare_months(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    b = st.parse_month(args.get("month_b") or "this month")
    a = st.parse_month(args.get("month_a") or st.add_months(b, -1))
    table = []
    for s, _ in _totals(data, rows, {a, b}):
        x, y = st.total(rows, s["id"], {a}), st.total(rows, s["id"], {b})
        if x or y:
            table.append([s["name"], st.gbp(x), st.gbp(y), st.gbp(y - x)])
    ta, tb = st.total(rows, None, {a}), st.total(rows, None, {b})
    table.append(["Total", st.gbp(ta), st.gbp(tb), st.gbp(tb - ta)])
    return screen.Shown(f"{st.month_long(b)} is {st.gbp(tb)} against {st.gbp(ta)} in {st.month_long(a)}.",
                        screen.card("table", f"{st.month_label(a)} vs {st.month_label(b)}", "incomestreams-compare",
                                    columns=["Stream", st.month_label(a), st.month_label(b), "Difference"], rows=table))


def run_rate(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = st.months_back(3, st.add_months(st.month_of(hs.today()), -1))
    monthly = st.total(rows, None, set(months)) / 3
    table = [["Average last 3 full months", st.gbp(monthly)], ["Times 12", st.gbp(monthly * 12)]]
    return screen.Shown(f"Your last three full months averaged {st.gbp(monthly)} a month. That is a look back, not a forecast: "
                        "income can rise, fall or stop.",
                        screen.card("table", "Run rate (looking back)", "incomestreams-runrate", columns=["", "Amount"], rows=table))


def yearly_summary(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    year = int(hs.number(args.get("year") or hs.today().year, "year", 2000, 2100))
    since, until = f"{year}-01-01", f"{year}-12-31"
    table = []
    for s in data["streams"]:
        g, c = st.total(rows, s["id"], since=since, until=until), st.total(rows, s["id"], since=since, until=until, field="costs")
        if g or c:
            table.append([s["name"], st.gbp(g), st.gbp(c), st.gbp(g - c)])
    g, c = st.total(rows, None, since=since, until=until), st.total(rows, None, since=since, until=until, field="costs")
    table.append(["Total", st.gbp(g), st.gbp(c), st.gbp(g - c)])
    return screen.Shown(f"In {year} you logged {st.gbp(g)} in and {st.gbp(c)} in costs. For tax years use the UK tax summary.",
                        screen.card("table", f"Calendar year {year}", "incomestreams-year",
                                    columns=["Stream", "In", "Costs", "Left"], rows=table))


def net_profit(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = set(_months(args))
    table = []
    for s in data["streams"]:
        g, c = st.total(rows, s["id"], months), st.total(rows, s["id"], months, field="costs")
        if g or c:
            table.append([s["name"], st.gbp(g), st.gbp(c), st.gbp(g - c)])
    g, c = st.total(rows, None, months), st.total(rows, None, months, field="costs")
    table.append(["Total", st.gbp(g), st.gbp(c), st.gbp(g - c)])
    return screen.Shown(f"After costs you kept {st.gbp(g - c)} of {st.gbp(g)} over {len(months)} months (before any tax).",
                        screen.card("table", "Money in after costs", "incomestreams-net", columns=["Stream", "In", "Costs", "Left"],
                                    rows=table))


def missing_months(settings: Settings, args: dict) -> screen.Shown:
    data, rows = _setup(settings)
    months = _months(args)
    items = []
    for s in data["streams"]:
        if s["status"] != "active":
            continue
        gaps = [st.month_label(m) for m in months if not st.total(rows, s["id"], {m})]
        if gaps:
            items.append({"label": f"{s['name']}: nothing in {', '.join(gaps[:6])}",
                          "say": f"I earned some money from {s['name']}."})
    if not items:
        return screen.Shown("Every active stream has something logged in each of those months.",
                            screen.card("list", "Gaps in my log", "incomestreams-gaps", items=["No gaps."]))
    return screen.Shown(f"{hs.plural(len(items), 'stream')} with empty months. Either it earned nothing or it hasn't been logged.",
                        screen.card("list", "Months with nothing logged", "incomestreams-gaps", items=items))


def tool_definitions() -> list[dict]:
    return [{
        "name": "income_insights",
        "description": "Overview of ALL the user's extra income from what they logged: dashboard pop-up (stacked by stream, "
                       "month by month), income by month, passive vs active share, best and worst stream, growth trends, money "
                       "per hour, diversification score, too-reliant-on-one-stream warning. Looks back only; never promises "
                       "income. action: dashboard / month_table / monthly_chart / passive_share / stream_share / best_worst / "
                       "growth / per_hour / diversification / reliance_check (threshold percent, default 60) / compare_months "
                       "(month_a, month_b) / run_rate / yearly_summary (year) / net_profit / missing_months. months = how "
                       "many recent months (default 6).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "months": {"type": "integer", "description": "How many recent months, 1 to 24."},
                "month_a": {"type": "string", "description": "YYYY-MM."},
                "month_b": {"type": "string", "description": "YYYY-MM."},
                "year": {"type": "integer"},
                "threshold": {"type": "number", "description": "Percent share that counts as too reliant."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"dashboard": dashboard, "month_table": month_table, "monthly_chart": monthly_chart,
             "passive_share": passive_share, "stream_share": stream_share, "best_worst": best_worst, "growth": growth,
             "per_hour": per_hour, "diversification": diversification, "reliance_check": reliance_check,
             "compare_months": compare_months, "run_rate": run_rate, "yearly_summary": yearly_summary,
             "net_profit": net_profit, "missing_months": missing_months}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
