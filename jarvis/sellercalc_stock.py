"""Reselling stock log: what you bought, where, where it is listed, what it sold for, fees, postage, profit and days to sell.
Stock value and ageing, sell-through, best categories, platform results, a monthly profit chart, slow movers and a returns log.

Results pop up as tables, a chart, sellercalc-bars or sellercalc-result (frontend/popup-sellercalc.js). Data lives in
sellercalc-inventory.json and sellercalc-returns.json in the memory folder. Nothing is posted anywhere.
"""

import csv
import io
from datetime import date, timedelta

import memory
import screen
import sellercalc_store as sc
from config import Settings

NAMES = {"sellercalc_stock"}
ACTIONS = ["add_item", "list_item", "sell_item", "update_item", "show_items", "item_detail", "remove_item", "stock_value",
           "ageing", "sell_through", "best_categories", "monthly_profit", "summary", "slow_movers", "platform_results",
           "speed", "export_csv", "log_return", "returns_list", "resolve_return"]
STATUS_WORDS = {"stock": "in stock", "listed": "listed", "sold": "sold"}
BUCKETS = [(30, "0 to 30 days"), (60, "31 to 60 days"), (90, "61 to 90 days"), (180, "91 to 180 days"), (10**6, "Over 180 days")]


def _day(args: dict, key: str = "date") -> date:
    return sc.parse_date(args.get(key), key) or sc.today()


def _plat(settings: Settings, value) -> tuple[str, dict | None]:
    """A platform's display name and its fee row, or the typed words with no fee row."""
    if not sc.clean(value):
        return "", None
    try:
        rate = sc.platform(settings, value)
        return rate["name"], rate
    except ValueError:
        return sc.clean(value, 40), None


def _money_field(args: dict, key: str, what: str) -> float | None:
    return None if args.get(key) is None else sc.number(args[key], what, allow_zero=True)


def add_item(settings: Settings, args: dict):
    rows = sc.items(settings)
    if len(rows) >= sc.MAX_ROWS:
        raise ValueError("The stock log is full; export it and tidy it before adding more.")
    item = {"id": max([i["id"] for i in rows] + [0]) + 1, "name": sc.need(args.get("name"), "item name", 80),
            "category": sc.clean(args.get("category"), 40).lower() or "other", "source": sc.clean(args.get("source"), 60),
            "bought_for": sc.arg(args, "bought_for", "price you paid", True), "bought_date": _day(args, "bought_date").isoformat(),
            "status": "stock", "notes": sc.clean(args.get("notes"), 200)}
    rows.append(item)
    sc.save_items(settings, rows)
    where = f" from {item['source']}" if item["source"] else ""
    return f"Added item {item['id']}, {item['name']}, bought{where} for {sc.gbp(item['bought_for'])}."


def list_item(settings: Settings, args: dict):
    rows = sc.items(settings)
    item = sc.pick_item(rows, args.get("item"))
    if sc.is_sold(item):
        raise ValueError(f"{item['name']} is already sold.")
    name, rate = _plat(settings, args.get("platform"))
    if not name:
        raise ValueError("Which platform is it listed on?")
    price = sc.arg(args, "price", "listing price")
    item.update({"status": "listed", "listed_on": name, "list_price": price, "listed_date": _day(args).isoformat()})
    sc.save_items(settings, rows)
    text = f"Listed {item['name']} on {name} at {sc.gbp(price)}."
    if rate:
        p = sc.profit_on(rate, price, item["bought_for"], 0.0, sc.arg(args, "ship_cost", "postage you pay", True, 0.0))
        text += f" After fees you'd keep about {sc.gbp(p['net'])}."
    return text


def sell_item(settings: Settings, args: dict):
    rows = sc.items(settings)
    item = sc.pick_item(rows, args.get("item"))
    if sc.is_sold(item):
        raise ValueError(f"{item['name']} is already marked sold.")
    name, rate = _plat(settings, args.get("platform") or item.get("listed_on"))
    price = sc.arg(args, "sold_for", "price it sold for", True)
    charged = sc.arg(args, "postage_charged", "postage the buyer paid", True, 0.0)
    fees = _money_field(args, "fees", "fees")
    guessed = fees is None
    if guessed:
        fees = sc.fee_of(rate, price, charged) if rate else 0.0
    item.update({"status": "sold", "sold_for": price, "sold_on": name, "sold_date": _day(args).isoformat(), "fees": fees,
                 "postage": sc.arg(args, "postage", "postage you paid", True, 0.0), "postage_charged": charged,
                 "other_costs": sc.arg(args, "other_costs", "other costs", True, 0.0)})
    if item.get("listed_on") is None:
        item["listed_on"] = name
    sc.save_items(settings, rows)
    text = f"Sold {item['name']} for {sc.gbp(price)}, profit {sc.gbp(sc.item_profit(item))}."
    days = sc.days_to_sell(item)
    if days is not None:
        text += f" It took {days} days."
    if guessed and rate:
        text += " Fees were worked out from the fee table; tell me the real fees if you know them."
    elif guessed:
        text += " I counted no fees, as I don't know that platform."
    return text


def update_item(settings: Settings, args: dict):
    rows = sc.items(settings)
    item = sc.pick_item(rows, args.get("item"))
    changed = []
    for key, source in (("name", "new_name"), ("category", "category"), ("source", "source"), ("notes", "notes")):
        if args.get(source) is not None:
            text = sc.clean(args[source], 200 if key == "notes" else 80)
            item[key] = text.lower() if key == "category" else text
            changed.append(key)
    for key, source, what in (("bought_for", "bought_for", "price you paid"), ("list_price", "price", "listing price"),
                              ("sold_for", "sold_for", "sold price"), ("fees", "fees", "fees"), ("postage", "postage", "postage"),
                              ("postage_charged", "postage_charged", "postage charged"), ("other_costs", "other_costs", "other costs")):
        if args.get(source) is not None:
            item[key] = sc.number(args[source], what, allow_zero=True)
            changed.append(key)
    if not changed:
        raise ValueError("Say what to change: the new name, category, source, notes or a price.")
    sc.save_items(settings, rows)
    return f"Updated {item['name']}: {', '.join(changed)}."


def _table_row(i: dict) -> list[str]:
    when = i.get("sold_date") if sc.is_sold(i) else i.get("listed_date", "")
    money = sc.gbp(sc.item_profit(i)) if sc.is_sold(i) else (sc.gbp(i["list_price"]) if i.get("list_price") else "")
    return [str(i["id"]), i["name"], STATUS_WORDS.get(i["status"], i["status"]), sc.gbp(i["bought_for"]),
            (i.get("sold_on") if sc.is_sold(i) else i.get("listed_on", "")) or "", money, when or ""]


def show_items(settings: Settings, args: dict):
    rows = sc.items(settings)
    status = {"in stock": "stock", "unsold": "stock"}.get(str(args.get("status", "")).lower(), str(args.get("status", "")).lower())
    for key, field in (("platform", "listed_on"), ("category", "category"), ("query", "name")):
        if args.get(key):
            rows = [i for i in rows if sc.clean(args[key]).lower() in str(i.get(field, "")).lower()]
    if status:
        rows = [i for i in rows if i["status"] == status]
    if not rows:
        raise ValueError("Nothing in your stock log matches. Add an item first.")
    shown = rows[-40:][::-1]
    return screen.Shown(f"{len(rows)} item{'s' if len(rows) != 1 else ''} in your stock log.", screen.card(
        "table", "Reselling stock", "sellercalc-items", columns=["#", "Item", "Status", "Cost", "Platform", "Price or profit", "Date"],
        rows=[_table_row(i) for i in shown], buttons=[{"label": "Stock value", "say": "What is my reselling stock worth?"}]))


def item_detail(settings: Settings, args: dict):
    item = sc.pick_item(sc.items(settings), args.get("item"))
    rows = [("Bought for", sc.gbp(item["bought_for"])), ("Where from", item.get("source") or "not noted"),
            ("Category", item.get("category", "other")), ("Bought on", item.get("bought_date", ""))]
    if item.get("listed_on"):
        rows.append(("Listed", f"{item['listed_on']} at {sc.gbp(item.get('list_price', 0))} on {item.get('listed_date', '')}"))
    if sc.is_sold(item):
        rows += [("Sold", f"{sc.gbp(item['sold_for'])} on {item['sold_on'] or 'unknown'}, {item['sold_date']}"),
                 ("Fees", sc.gbp(item["fees"])), ("Postage paid", sc.gbp(item["postage"])),
                 ("Days to sell", str(sc.days_to_sell(item)))]
        head, sub = sc.gbp(sc.item_profit(item)), "profit"
    else:
        rows.append(("Days held", str(sc.days_held(item))))
        head, sub = STATUS_WORDS.get(item["status"], item["status"]), f"held {sc.days_held(item)} days"
    return sc.result(f"{item['name']}: {head}.", f"#{item['id']} {item['name']}", head, sub, rows,
                     [item["notes"]] if item.get("notes") else [])


def remove_item(settings: Settings, args: dict):
    rows = sc.items(settings)
    item = sc.pick_item(rows, args.get("item"))
    if args.get("confirmed") is not True:
        return f"That removes {item['name']} and its sale record for good. Say yes to confirm."
    sc.save_items(settings, [i for i in rows if i is not item])
    return f"Removed {item['name']} from your stock log."


def stock_value(settings: Settings, args: dict):
    rows = [i for i in sc.items(settings) if not sc.is_sold(i)]
    if not rows:
        raise ValueError("You have no unsold stock logged.")
    cost = sum(i["bought_for"] for i in rows)
    asking = sum(i.get("list_price", 0) for i in rows if i["status"] == "listed")
    by_cat: dict[str, float] = {}
    for i in rows:
        by_cat[i.get("category", "other")] = by_cat.get(i.get("category", "other"), 0) + i["bought_for"]
    top = max(by_cat.values()) or 1
    table = [(c, sc.gbp(v), 100 * v / top, f"{sum(1 for i in rows if i.get('category', 'other') == c)} items")
             for c, v in sorted(by_cat.items(), key=lambda x: -x[1])[:10]]
    return sc.bars(f"You have {len(rows)} unsold items that cost {sc.gbp(cost)}.", "Stock value", table,
                   f"At cost: {sc.gbp(cost)}. Listed asking prices add up to {sc.gbp(asking)} "
                   f"({sum(1 for i in rows if i['status'] == 'listed')} listed). Asking prices are hopes, not money; "
                   "the cost figure is the safer one.")


def ageing(settings: Settings, args: dict):
    rows = [i for i in sc.items(settings) if not sc.is_sold(i)]
    if not rows:
        raise ValueError("You have no unsold stock logged.")
    counts = []
    low = -1
    for top, label in BUCKETS:
        hit = [i for i in rows if low < sc.days_held(i) <= top]
        counts.append((label, hit))
        low = top
    biggest = max(len(h) for _, h in counts) or 1
    table = [(label, f"{len(h)} items", 100 * len(h) / biggest, f"cost {sc.gbp(sum(i['bought_for'] for i in h))}") for label, h in counts]
    old = sum(len(h) for (top, _), (_, h) in zip(BUCKETS, counts) if top in (180, 10**6))
    return sc.bars(f"{old} of your {len(rows)} unsold items have been sitting for over 90 days.", "Stock ageing", table,
                   "Days since you bought each item. Old stock ties up money: consider a lower price, a bundle or a fresh listing.")


def _sold(rows: list[dict]) -> list[dict]:
    return [i for i in rows if sc.is_sold(i)]


def sell_through(settings: Settings, args: dict):
    rows = sc.items(settings)
    days = int(sc.arg(args, "days", "number of days", True, 0.0, top=3650))
    if days:
        cutoff = sc.today() - timedelta(days=days)
        rows = [i for i in rows if (sc.day_of(i.get("bought_date")) or cutoff) >= cutoff]
    if not rows:
        raise ValueError("No items in that time. Add some stock first.")
    sold = _sold(rows)
    rate = round(100 * len(sold) / len(rows), 1)
    by_cat: dict[str, list[int]] = {}
    for i in rows:
        got = by_cat.setdefault(i.get("category", "other"), [0, 0])
        got[0] += 1
        got[1] += sc.is_sold(i)
    table = [(c, f"{round(100 * s / n)}%", 100 * s / n, f"{s} of {n} sold") for c, (n, s) in sorted(by_cat.items(), key=lambda x: -x[1][1] / x[1][0])[:10]]
    span = f"bought in the last {days} days" if days else "in your whole log"
    return sc.bars(f"Sell-through is {rate:g}%: {len(sold)} of {len(rows)} items {span} have sold.", "Sell-through rate", table,
                   "Sell-through is items sold divided by items you've bought. A low figure can mean stock is priced too high or is "
                   "the wrong kind to resell.")


def best_categories(settings: Settings, args: dict):
    sold = _sold(sc.items(settings))
    if not sold:
        raise ValueError("Nothing has sold yet, so there's no best category.")
    by_cat: dict[str, list[dict]] = {}
    for i in sold:
        by_cat.setdefault(i.get("category", "other"), []).append(i)
    ranked = sorted(by_cat.items(), key=lambda x: -sum(sc.item_profit(i) for i in x[1]))[:10]
    top = max(abs(sum(sc.item_profit(i) for i in v)) for _, v in ranked) or 1
    table = []
    for cat, v in ranked:
        total = sum(sc.item_profit(i) for i in v)
        days = [d for d in map(sc.days_to_sell, v) if d is not None]
        avg = f", about {round(sum(days) / len(days))} days to sell" if days else ""
        table.append((cat, sc.gbp(round(total, 2)), 100 * abs(total) / top, f"{len(v)} sold{avg}"))
    return sc.bars(f"{ranked[0][0].title()} is your best category by profit.", "Best-selling categories", table,
                   "Ranked by total profit so far. A few sales is a hint, not proof.")


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def monthly_profit(settings: Settings, args: dict):
    sold = _sold(sc.items(settings))
    if not sold:
        raise ValueError("Nothing has sold yet, so there's no profit to chart.")
    count = int(sc.arg(args, "months", "number of months", True, 6.0, top=36)) or 6
    today = sc.today().replace(day=1)
    keys = []
    for k in range(count - 1, -1, -1):
        m = today.month - k
        keys.append(f"{today.year + (m - 1) // 12}-{(m - 1) % 12 + 1:02d}")
    totals = dict.fromkeys(keys, 0.0)
    for i in sold:
        d = sc.day_of(i.get("sold_date"))
        if d and _month_key(d) in totals:
            totals[_month_key(d)] += sc.item_profit(i)
    values = [round(totals[k], 2) for k in keys]
    labels = [date.fromisoformat(k + "-01").strftime("%b %y") for k in keys]
    return screen.Shown(f"This month's reselling profit is {sc.gbp(values[-1])}; {sc.gbp(round(sum(values), 2))} over {count} months.",
                        screen.card("chart", "Reselling profit per month (£)", "sellercalc-monthly",
                                    chart={"type": "bar", "labels": labels, "values": values, "unit": ""},
                                    text="Profit after what you paid, fees and postage, by the month each item sold."))


def summary(settings: Settings, args: dict):
    rows = sc.items(settings)
    if not rows:
        raise ValueError("Your stock log is empty. Add an item first.")
    sold, unsold = _sold(rows), [i for i in rows if not sc.is_sold(i)]
    month = _month_key(sc.today())
    this = [i for i in sold if str(i.get("sold_date", "")).startswith(month)]
    days = [d for d in map(sc.days_to_sell, sold) if d is not None]
    returns = _returns(settings)
    lines = [("Profit so far", sc.gbp(round(sum(map(sc.item_profit, sold)), 2))),
             ("Profit this month", sc.gbp(round(sum(map(sc.item_profit, this)), 2))), ("Items sold", str(len(sold))),
             ("Items unsold", f"{len(unsold)} (cost {sc.gbp(sum(i['bought_for'] for i in unsold))})"),
             ("Sell-through", f"{round(100 * len(sold) / len(rows))}%"),
             ("Average days to sell", str(round(sum(days) / len(days))) if days else "not enough sales yet"),
             ("Returns logged", str(len(returns)))]
    head = sc.gbp(round(sum(map(sc.item_profit, sold)), 2))
    return sc.result(f"Reselling profit so far is {head} from {len(sold)} sales.", "Reselling summary", head, "profit so far", lines,
                     ["Profit is what you keep after buying cost, fees and postage. It is before any tax; check GOV.UK."])


def slow_movers(settings: Settings, args: dict):
    days = int(sc.arg(args, "days", "number of days", True, 60.0, top=3650))
    rows = sorted((i for i in sc.items(settings) if not sc.is_sold(i) and sc.days_held(i) >= days), key=lambda i: -sc.days_held(i))
    if not rows:
        return f"Nothing has been unsold for {days} days or more. Nice."
    listed = [{"label": f"#{i['id']} {i['name']}: {sc.days_held(i)} days, cost {sc.gbp(i['bought_for'])}",
               "say": f"Show item {i['id']} in my stock log."} for i in rows[:20]]
    return screen.Shown(f"{len(rows)} items have sat unsold for {days} days or more.", screen.card(
        "list", f"Slow movers ({days}+ days)", "sellercalc-slow", items=listed,
        text="Ideas: check the photos and title, drop the price about 10%, add it to a bundle, relist it, or donate it."))


def platform_results(settings: Settings, args: dict):
    sold = _sold(sc.items(settings))
    if not sold:
        raise ValueError("Nothing has sold yet.")
    by: dict[str, list[dict]] = {}
    for i in sold:
        by.setdefault(i.get("sold_on") or "unknown", []).append(i)
    table = []
    for name, v in sorted(by.items(), key=lambda x: -sum(map(sc.item_profit, x[1]))):
        days = [d for d in map(sc.days_to_sell, v) if d is not None]
        table.append([name, str(len(v)), sc.gbp(sum(i["sold_for"] for i in v)), sc.gbp(sum(i["fees"] for i in v)),
                      sc.gbp(round(sum(map(sc.item_profit, v)), 2)), str(round(sum(days) / len(days))) if days else "-"])
    return screen.Shown(f"{table[0][0]} has made you the most profit.", screen.card(
        "table", "Results by platform", "sellercalc-platforms", columns=["Platform", "Sold", "Sales", "Fees", "Profit", "Avg days"],
        rows=table))


def speed(settings: Settings, args: dict):
    sold = _sold(sc.items(settings))
    field = "category" if str(args.get("by", "")).lower().startswith("cat") else "sold_on"
    groups: dict[str, list[int]] = {}
    for i in sold:
        d = sc.days_to_sell(i)
        if d is not None:
            groups.setdefault(i.get(field) or "unknown", []).append(d)
    if not groups:
        raise ValueError("I need some sold items with dates to work out how quickly things sell.")
    ranked = sorted(((k, sum(v) / len(v), len(v)) for k, v in groups.items()), key=lambda x: x[1])
    slowest = max(r[1] for r in ranked) or 1
    table = [(k, f"{round(a)} days", 100 * a / slowest, f"{n} sold") for k, a, n in ranked[:10]]
    return sc.bars(f"{ranked[0][0]} sells fastest, about {round(ranked[0][1])} days.", "Days to sell",
                   table, "Average days from listing (or buying, if never listed) to sale.")


def _csv_cell(value) -> str:
    text = str(value if value is not None else "")
    return "'" + text if text[:1] in "=+-@" else text


def export_csv(settings: Settings, args: dict):
    rows = sc.items(settings)
    if not rows:
        raise ValueError("Your stock log is empty.")
    columns = ["id", "name", "category", "source", "bought_for", "bought_date", "status", "listed_on", "list_price", "listed_date",
               "sold_on", "sold_for", "sold_date", "fees", "postage", "postage_charged", "other_costs"]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(columns + ["profit", "days_to_sell"])
    for i in rows:
        sold = sc.is_sold(i)
        writer.writerow([_csv_cell(i.get(c, "")) for c in columns] + [sc.item_profit(i) if sold else "", sc.days_to_sell(i) if sold else ""])
    folder = memory.root(settings) / "Selling"
    folder.mkdir(parents=True, exist_ok=True)
    path = memory.unique_path(folder / "reselling-stock.csv")
    path.write_text(out.getvalue(), encoding="utf-8")
    return screen.Shown(f"Saved {len(rows)} items to {path.name} in your Selling folder.", screen.file_card(settings, path))


def _returns(settings: Settings) -> list[dict]:
    return [r for r in sc.load(settings, sc.RETURNS, []) if isinstance(r, dict)]


def log_return(settings: Settings, args: dict):
    rows = _returns(settings)
    if len(rows) >= sc.MAX_ROWS:
        raise ValueError("The returns log is full.")
    stock = sc.items(settings)
    label = sc.need(args.get("item") or args.get("name"), "item", 80)
    try:
        item = sc.pick_item(stock, label)
        label = item["name"]
    except ValueError:
        item = None
    entry = {"id": max([r["id"] for r in rows] + [0]) + 1, "item": label, "item_id": item["id"] if item else None,
             "date": _day(args).isoformat(), "reason": sc.clean(args.get("reason"), 120) or "not given",
             "refund": sc.arg(args, "refund", "refund amount", True, 0.0), "postage": sc.arg(args, "postage", "return postage cost", True, 0.0),
             "restocked": bool(args.get("restocked")), "status": "open"}
    rows.append(entry)
    sc.save(settings, sc.RETURNS, rows)
    return f"Logged return {entry['id']} for {label}: {sc.gbp(entry['refund'] + entry['postage'])} out of pocket so far."


def returns_list(settings: Settings, args: dict):
    rows = _returns(settings)
    if not rows:
        raise ValueError("No returns logged. Good.")
    sold = len(_sold(sc.items(settings)))
    lost = sum(r["refund"] + r["postage"] for r in rows)
    text = f"{len(rows)} returns, costing about {sc.gbp(round(lost, 2))}."
    if sold:
        text += f" That's {round(100 * len(rows) / sold, 1)}% of your {sold} sales."
    return screen.Shown(text, screen.card(
        "table", "Returns", "sellercalc-returns", columns=["#", "Date", "Item", "Reason", "Refund", "Postage", "Status"],
        rows=[[str(r["id"]), r["date"], r["item"], r["reason"], sc.gbp(r["refund"]), sc.gbp(r["postage"]),
               r["status"] + (", restocked" if r["restocked"] else "")] for r in rows[-30:][::-1]],
        text="Returns cost is separate from item profit above; refund plus return postage."))


def resolve_return(settings: Settings, args: dict):
    rows = _returns(settings)
    ref = str(args.get("return_id") or args.get("item") or "").lstrip("#")
    hit = next((r for r in rows if str(r["id"]) == ref), None) or next((r for r in reversed(rows) if ref and ref.lower() in r["item"].lower()), None)
    if hit is None:
        raise ValueError("Which return? Say its number.")
    for key, what in (("refund", "refund amount"), ("postage", "return postage")):
        if args.get(key) is not None:
            hit[key] = sc.number(args[key], what, allow_zero=True)
    if args.get("restocked") is not None:
        hit["restocked"] = bool(args["restocked"])
    hit["status"] = "closed"
    sc.save(settings, sc.RETURNS, rows)
    return f"Closed return {hit['id']} for {hit['item']}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "sellercalc_stock",
        "description": "Reselling stock log and results in GBP: add an item bought (where, cost), list it on eBay/Vinted/Etsy/Depop, "
                       "mark sold (fees worked out from the fee table, postage, profit, days to sell), show stock, stock value, "
                       "ageing, sell-through rate, best categories, platform results, monthly profit chart, slow movers, CSV "
                       "export, and a returns log. Set confirmed only after the user agrees to remove_item. Nothing is posted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "item": {"type": "string", "description": "Item number or name (log_return: what came back)."},
                "name": {"type": "string"}, "new_name": {"type": "string"}, "category": {"type": "string"},
                "source": {"type": "string", "description": "Where you bought it: car boot, charity shop..."},
                "bought_for": {"type": "number"}, "bought_date": {"type": "string"},
                "platform": {"type": "string"}, "price": {"type": "number", "description": "Listing price."},
                "sold_for": {"type": "number"}, "fees": {"type": "number", "description": "Real fees; leave out to use the fee table."},
                "postage": {"type": "number", "description": "Postage you paid."}, "postage_charged": {"type": "number"},
                "ship_cost": {"type": "number"}, "other_costs": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD, today or yesterday."},
                "notes": {"type": "string"}, "status": {"type": "string", "enum": ["stock", "listed", "sold", "unsold"]},
                "query": {"type": "string"}, "days": {"type": "number"}, "months": {"type": "number"},
                "by": {"type": "string", "enum": ["platform", "category"]},
                "reason": {"type": "string"}, "refund": {"type": "number"}, "restocked": {"type": "boolean"},
                "return_id": {"type": "string"}, "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {a: globals()[a] for a in ACTIONS}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which stock action? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
