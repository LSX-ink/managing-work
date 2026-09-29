"""Honest side-hustle numbers: effective hourly rate, break-even, startup costs, pricing (cost-plus and target-hourly),
weekly hours per hustle, and a simple log of hours, income and costs with your real hourly rate per hustle.

Results pop up as "sidehustle-calc" or "sidehustle-hours" (frontend/popup-sidehustle.js). All maths uses the numbers you
give; nothing is a promise of income, and UK tax notes are general guidance (check GOV.UK). Data: sidehustle-log.json.
"""

import math
from datetime import date, timedelta

import screen
import sidehustle_store as st
from config import Settings

NAMES = {"sidehustle_money"}
ACTIONS = ["hourly_rate", "break_even", "startup_cost", "price_cost_plus", "price_target_hourly", "log_hours", "log_income",
           "log_expense", "hours_week", "hustle_summary", "compare_rates", "sales_needed", "entries"]
CONTINGENCY = 0.10
LONGER = 0.25


def _n(args: dict, key: str, what: str, zero: bool = False, default=None) -> float:
    if args.get(key) is None:
        if default is not None:
            return default
        raise ValueError(f"Tell me the {what}.")
    return st.number(args[key], what, allow_zero=zero)


def _slower(rate) -> list[str]:
    if rate is None or rate >= st.WAGE:
        return []
    return [f"That is below about {st.gbp(st.WAGE)} an hour (the National Living Wage from April 2026; check GOV.UK for the "
            "current rate). Worth asking whether prices, costs or time can change."]


def hourly_rate(settings: Settings, args: dict):
    if args.get("income") is None and args.get("hustle"):
        return hustle_summary(settings, args)
    income, costs, hours = _n(args, "income", "income", True), _n(args, "costs", "costs", True, 0.0), _n(args, "hours", "hours worked")
    profit = income - costs
    rate = profit / hours
    return st.calc(f"After costs that works out at {st.gbp(round(rate, 2))} an hour. {st.HONEST}", "Effective hourly rate",
                   f"{st.gbp(round(rate, 2))} an hour", "income minus costs, divided by hours",
                   [("Income", st.gbp(income)), ("Costs", st.gbp(costs)), ("Profit", st.gbp(round(profit, 2))),
                    ("Hours", st.num(hours))], _slower(rate) + ["Count every hour: prep, travel, messages and admin."])


def break_even(settings: Settings, args: dict):
    fixed, price = _n(args, "fixed_costs", "startup or fixed costs"), _n(args, "price", "selling price")
    unit = _n(args, "unit_cost", "cost per sale", True, 0.0)
    margin = price - unit
    if margin <= 0:
        raise ValueError("Each sale costs you as much as you charge, so you'd never break even. Raise the price or cut the cost.")
    units = math.ceil(fixed / margin)
    rows = [("Startup or fixed costs", st.gbp(fixed)), ("Price", st.gbp(price)), ("Cost per sale", st.gbp(unit)),
            ("Left per sale", st.gbp(round(margin, 2)))]
    notes = [st.HONEST]
    weeks = 0
    if args.get("per_week"):
        weeks = math.ceil(units / st.number(args["per_week"], "sales per week"))
        rows.append(("Sales per week", st.num(float(args["per_week"]))))
        notes.insert(0, f"At {st.num(float(args['per_week']))} sales a week, that is about {weeks} weeks.")
    return st.calc(f"You break even after {units} sales{' (about ' + str(weeks) + ' weeks)' if args.get('per_week') else ''}. {st.HONEST}", "Break-even", f"{units} sales",
                   "before you make any profit", rows, notes)


def startup_cost(settings: Settings, args: dict):
    items = [i for i in args.get("items") or [] if isinstance(i, dict) and i.get("item")]
    if not items:
        raise ValueError("List the things you'd need to buy, each with a cost.")
    rows = [(st.clean(i["item"], 60), st.gbp(st.number(i.get("cost"), "cost", allow_zero=True))) for i in items[:30]]
    total = sum(st.number(i.get("cost"), "cost", allow_zero=True) for i in items[:30])
    spare = round(total * CONTINGENCY, 2)
    rows += [("Spare 10% for surprises", st.gbp(spare)), ("Total to start", st.gbp(round(total + spare, 2)))]
    notes = ["Only spend money you could afford to lose.", st.HONEST]
    if args.get("budget") is not None:
        room = st.number(args["budget"], "budget", allow_zero=True) - total - spare
        notes.insert(0, f"That is {st.gbp(abs(round(room, 2)))} {'under' if room >= 0 else 'over'} your budget.")
    return st.calc(f"Starting would cost about {st.gbp(round(total + spare, 2))} including a 10% spare. {st.HONEST}", "Startup costs",
                   st.gbp(round(total + spare, 2)), f"{len(items)} items plus a 10% spare", rows, notes)


def _grossed(price: float, fee: float) -> tuple[float, float]:
    return round(price / (1 - fee / 100), 2), round(price / (1 - fee / 100) - price, 2)


def price_cost_plus(settings: Settings, args: dict):
    materials = _n(args, "materials", "materials cost", True, 0.0)
    hours, pay = _n(args, "hours", "hours per item", True, 0.0), _n(args, "hourly_pay", "hourly pay you want", True, 0.0)
    overhead = _n(args, "overhead", "overhead per item", True, 0.0)
    base = materials + hours * pay + overhead
    if base <= 0:
        raise ValueError("Give at least the materials, or your hours and the hourly pay you want.")
    markup, fee = st.pct(args.get("markup_pct", 0)), st.pct(args.get("fee_pct", 0), "fee percentage")
    price, fee_cost = _grossed(base * (1 + markup / 100), fee)
    rows = [("Materials", st.gbp(materials)), ("Your time", f"{st.num(hours)} h x {st.gbp(pay)} = {st.gbp(round(hours * pay, 2))}"),
            ("Overhead", st.gbp(overhead)), (f"Markup {st.num(markup)}%", st.gbp(round(base * markup / 100, 2))),
            (f"Platform or payment fee {st.num(fee)}%", st.gbp(fee_cost))]
    return st.calc(f"To cover costs and pay yourself, charge at least {st.gbp(price)}. {st.HONEST}", "Cost-plus price",
                   st.gbp(price), "the lowest sensible price, not what buyers will pay", rows,
                   ["Check what similar sellers charge; the market may pay more or less.", st.HONEST])


def price_target_hourly(settings: Settings, args: dict):
    target = _n(args, "target_hourly", "hourly rate you want")
    hours = _n(args, "hours_per_job", "hours per job")
    unpaid = _n(args, "unpaid_hours", "unpaid hours", True, 0.0)
    costs = _n(args, "costs_per_job", "costs per job", True, 0.0)
    fee = st.pct(args.get("fee_pct", 0), "fee percentage")
    total_hours = hours + unpaid
    price, fee_cost = _grossed(total_hours * target + costs, fee)
    slow, _ = _grossed(total_hours * (1 + LONGER) * target + costs, fee)
    rows = [("Target per hour", st.gbp(target)), ("Hours (with unpaid time)", st.num(total_hours)), ("Costs", st.gbp(costs)),
            ("Fees", st.gbp(fee_cost)), (f"If it takes {int(LONGER * 100)}% longer", f"{st.gbp(slow)} needed")]
    return st.calc(f"To earn {st.gbp(target)} an hour, charge about {st.gbp(price)} per job. {st.HONEST}", "Target-hourly price",
                   st.gbp(price), f"for {st.num(total_hours)} hours at {st.gbp(target)} an hour", rows,
                   ["Count travel, messages and admin as hours.", st.HONEST])


def _day(args: dict) -> date:
    return st.parse_date(args.get("date"), "date") or st.today()


def log_hours(settings: Settings, args: dict) -> str:
    hours = _n(args, "hours", "hours")
    if hours > 24:
        raise ValueError("That is more than a day; check the hours.")
    name = st.hustle_name(settings, args.get("hustle"))
    st.add_entry(settings, "hours", name, hours, st.clean(args.get("note"), 120), _day(args))
    week = _week_hours(settings, name, _day(args))
    return f"Logged {st.num(hours)} hours on {name}. That is {st.num(week)} hours this week."


def log_income(settings: Settings, args: dict) -> str:
    amount = _n(args, "amount", "amount")
    name = st.hustle_name(settings, args.get("hustle"))
    st.add_entry(settings, "income", name, amount, st.clean(args.get("note"), 120), _day(args), st.clean(args.get("customer"), 60))
    return f"Logged {st.gbp(amount)} income for {name}. {st.HONEST}"


def log_expense(settings: Settings, args: dict) -> str:
    amount = _n(args, "amount", "cost")
    name = st.hustle_name(settings, args.get("hustle"))
    st.add_entry(settings, "expense", name, amount, st.clean(args.get("note"), 120), _day(args))
    return f"Logged {st.gbp(amount)} cost for {name}. Keep the receipt."


def _monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _week_hours(settings: Settings, name: str, day: date) -> float:
    mon = _monday(day)
    return st.totals(st.log(settings), name, mon, mon + timedelta(days=6))["hours"]


def hours_week(settings: Settings, args: dict):
    mon = _monday(_day(args))
    weeks = [mon - timedelta(days=7 * k) for k in (3, 2, 1, 0)]
    rows = st.log(settings)
    names = sorted({e["hustle"] for e in rows if e["kind"] == "hours"} | {h["name"] for h in st.hustles(settings) if h.get("status") == "active"})
    if not names:
        raise ValueError("No hours logged yet. Say how many hours you did on a hustle.")
    series = [{"name": n, "values": [round(st.totals(rows, n, w, w + timedelta(days=6))["hours"], 2) for w in weeks]} for n in names]
    this = sum(s["values"][-1] for s in series)
    target = st.profile(settings).get("hours")
    text = f"This week you've logged {st.num(round(this, 2))} hours across {len(names)} side hustle{'s' if len(names) != 1 else ''}."
    if target:
        text += f" Your aim is {st.num(float(target))}."
    return screen.Shown(text, screen.card(st.HOURS, "Hours this week", "", data={
        "weeks": [f"w/c {w.day} {w.strftime('%b')}" for w in weeks],
        "series": series, "target": target}, buttons=[{"label": "Log hours", "say": "Log an hour on my side hustle."}]))


def hustle_summary(settings: Settings, args: dict):
    name = st.hustle_name(settings, args.get("hustle"))
    start = end = None
    label = "all time"
    if args.get("month"):
        start, end = st.month_bounds(args["month"])
        label = start.strftime("%B %Y")
    t = st.totals(st.log(settings), name, start, end)
    if not (t["income"] or t["costs"] or t["hours"]):
        raise ValueError(f"Nothing is logged for {name} ({label}) yet.")
    headline = st.rate_text(t["rate"])
    return st.calc(f"{name} ({label}): {st.gbp(t['profit'])} profit, {headline}. {st.HONEST}", f"{name}: real hourly rate",
                   headline, f"{name}, {label}",
                   [("Income", st.gbp(t["income"])), ("Costs", st.gbp(t["costs"])), ("Profit", st.gbp(t["profit"])),
                    ("Hours", st.num(round(t["hours"], 2)))], _slower(t["rate"]) + [st.HONEST])


def compare_rates(settings: Settings, args: dict):
    rows = st.log(settings)
    names = sorted({e["hustle"] for e in rows})
    if not names:
        raise ValueError("Nothing is logged yet.")
    stats = sorted(((n, st.totals(rows, n)) for n in names), key=lambda x: (x[1]["rate"] is None, -(x[1]["rate"] or 0)))
    table = [[n, st.gbp(t["income"]), st.gbp(t["costs"]), st.num(round(t["hours"], 2)), st.rate_text(t["rate"])] for n, t in stats]
    return screen.Shown(f"{stats[0][0]} pays best per hour so far. {st.HONEST}", screen.card(
        "table", "Real hourly rate by side hustle", "sidehustle-rates", columns=["Hustle", "Income", "Costs", "Hours", "Rate"], rows=table))


def sales_needed(settings: Settings, args: dict):
    price, unit = _n(args, "price", "price per sale"), _n(args, "unit_cost", "cost per sale", True, 0.0)
    margin = price - unit
    if margin <= 0:
        raise ValueError("Each sale costs as much as you charge, so profit never grows. Raise the price or cut the cost.")
    goal = st.profile(settings).get("goal")
    target = _n(args, "target_profit", "profit you want", default=float(goal) if goal else None)
    made = 0.0
    if args.get("target_profit") is None:
        first, last = st.month_bounds()
        made = st.totals(st.log(settings), None, first, last)["profit"]
    left = max(target - made, 0)
    units = math.ceil(left / margin)
    rows = [("Profit wanted", st.gbp(target)), ("Already made this month", st.gbp(made)), ("Left per sale", st.gbp(round(margin, 2)))]
    return st.calc(f"You'd need about {units} more sales. {st.HONEST}", "Sales needed", f"{units} sales",
                   "to reach that profit", rows, [st.HONEST])


def entries(settings: Settings, args: dict):
    rows = st.log(settings)
    if args.get("hustle"):
        rows = [e for e in rows if args["hustle"].lower() in e["hustle"].lower()]
    if args.get("kind"):
        rows = [e for e in rows if e["kind"] == args["kind"]]
    if not rows:
        raise ValueError("Nothing logged yet.")
    last = rows[-15:][::-1]
    table = [[e["date"], e["hustle"], e["kind"], st.num(e["amount"]) if e["kind"] == "hours" else st.gbp(e["amount"]), e["note"]] for e in last]
    return screen.Shown(f"Your last {len(last)} entries.", screen.card(
        "table", "Side hustle log", "sidehustle-log", columns=["Date", "Hustle", "Kind", "Amount", "Note"], rows=table))


def tool_definitions() -> list[dict]:
    item = {"type": "object", "properties": {"item": {"type": "string"}, "cost": {"type": "number"}},
            "required": ["item", "cost"], "additionalProperties": False}
    return [{
        "name": "sidehustle_money",
        "description": "Honest side hustle numbers in GBP: effective hourly rate (income minus costs over hours), break-even, startup "
                       "costs, pricing (cost-plus, target hourly), log hours, income and costs per hustle, hours this week per "
                       "hustle, real hourly rate per hustle, compare hustles, sales needed. Estimates only, never promises income.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "hustle": {"type": "string", "description": "Side hustle name."},
                "income": {"type": "number"}, "costs": {"type": "number"}, "hours": {"type": "number"},
                "amount": {"type": "number", "description": "Pounds for log_income or log_expense."},
                "fixed_costs": {"type": "number"}, "price": {"type": "number"}, "unit_cost": {"type": "number"},
                "per_week": {"type": "number", "description": "Expected sales per week."},
                "items": {"type": "array", "items": item, "description": "Startup items with costs."},
                "budget": {"type": "number"},
                "materials": {"type": "number"}, "hourly_pay": {"type": "number"}, "overhead": {"type": "number"},
                "markup_pct": {"type": "number"}, "fee_pct": {"type": "number", "description": "Platform or payment fee percent."},
                "target_hourly": {"type": "number"}, "hours_per_job": {"type": "number"}, "unpaid_hours": {"type": "number"},
                "costs_per_job": {"type": "number"}, "target_profit": {"type": "number"},
                "customer": {"type": "string"}, "note": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD, today or yesterday."},
                "month": {"type": "string", "description": "YYYY-MM."},
                "kind": {"type": "string", "enum": ["hours", "income", "expense"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"hourly_rate": hourly_rate, "break_even": break_even, "startup_cost": startup_cost,
                "price_cost_plus": price_cost_plus, "price_target_hourly": price_target_hourly, "log_hours": log_hours,
                "log_income": log_income, "log_expense": log_expense, "hours_week": hours_week,
                "hustle_summary": hustle_summary, "compare_rates": compare_rates, "sales_needed": sales_needed,
                "entries": entries}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which side hustle calculation? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
