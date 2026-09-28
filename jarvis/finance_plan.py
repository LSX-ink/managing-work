"""Money planning: a debt payoff planner, payday countdown, "can I afford it?", cost per use and trip budgets.

Debts, the payday rule and trips are finance-*.json files in the memory folder. Trip spending is logged in the
trip's own currency and converted home with money.convert (free European Central Bank rates, no key).
"""

import calendar
import math
import re
from datetime import date, datetime, timedelta

import httpx

import finance_store as fs
import homehouse
import homestore as hs
import money
import screen
from config import Settings

MAX_MONTHS = 600
PAYDAY_RULES = ["day_of_month", "last_working_day", "every_weeks"]


# Debt payoff planner

def debt_set(settings: Settings, name, balance, apr, minimum) -> str:
    name = hs.need(name, "debt", 40)
    found = fs.rows(settings, fs.DEBTS)
    key = hs.find(found, name) or name
    row = {"balance": fs.amount(balance, "balance"), "apr": round(hs.number(apr or 0, "interest rate", 0, 100), 2),
           "minimum": fs.amount(minimum, "minimum payment")}
    fs.put(settings, fs.DEBTS, found, key, row)
    return (f"{key}: {fs.cash(row['balance'], settings)} at {row['apr']:g}% APR, minimum "
            f"{fs.cash(row['minimum'], settings)} a month.")


def debt_remove(settings: Settings, name, confirmed: bool) -> str:
    found = fs.rows(settings, fs.DEBTS)
    key = fs.key_of(found, name, "debt")
    if not confirmed:
        return f"Ask the user to confirm removing the {key} debt, then call again with confirmed true."
    del found[key]
    hs.save(settings, fs.DEBTS, found)
    return f"Removed the {key} debt."


def simulate(debts: dict, extra: float, strategy: str) -> dict:
    """Month-by-month payoff: minimums on every debt, the rest to the smallest (snowball) or dearest (avalanche)."""
    bal = {k: float(d["balance"]) for k, d in debts.items()}
    budget = sum(float(d["minimum"]) for d in debts.values()) + extra
    if sum(bal[k] * debts[k]["apr"] / 1200 for k in bal) >= budget - 0.005:
        raise ValueError("Those payments don't even cover the interest, so the debts would never be paid off.")
    interest, history, cleared = 0.0, [sum(bal.values())], []
    for month in range(1, MAX_MONTHS + 1):
        for k in bal:
            charge = bal[k] * debts[k]["apr"] / 1200
            bal[k] += charge
            interest += charge
        left = budget
        active = [k for k in bal if bal[k] > 0.005]
        for k in active:
            pay = min(float(debts[k]["minimum"]), bal[k], left)
            bal[k] -= pay
            left -= pay
        order = sorted(active, key=(lambda k: bal[k]) if strategy == "snowball" else (lambda k: -debts[k]["apr"]))
        for k in order:
            pay = min(left, bal[k])
            bal[k] -= pay
            left -= pay
        for k in active:
            if bal[k] <= 0.005:
                bal[k] = 0.0
                cleared.append((k, month))
        history.append(max(0.0, sum(bal.values())))
        if history[-1] <= 0.005:
            return {"months": month, "interest": round(interest, 2), "history": history, "cleared": cleared}
    raise ValueError("At those payments it would take over 50 years; try paying more each month.")


def _add_months(day: date, n: int) -> date:
    y, m = divmod(day.month - 1 + n, 12)
    return date(day.year + y, m + 1, 1)


def debt_plan(settings: Settings, extra) -> screen.Shown | str:
    debts = fs.rows(settings, fs.DEBTS)
    if not debts:
        return "No debts added yet. Tell me each one's balance, APR and minimum payment."
    extra = fs.amount(extra or 0, "extra payment")
    today = hs.today()
    plans = {s: simulate(debts, extra, s) for s in ("snowball", "avalanche")}
    best = min(plans, key=lambda s: (plans[s]["interest"], plans[s]["months"]))
    other = "snowball" if best == "avalanche" else "avalanche"
    when = {s: _add_months(today, p["months"]).strftime("%B %Y") for s, p in plans.items()}
    saving = plans[other]["interest"] - plans[best]["interest"]
    said = (f"{best.title()} clears everything by {when[best]} ({plans[best]['months']} months) with "
            f"{fs.cash(plans[best]['interest'], settings)} interest; {other} takes {plans[other]['months']} months"
            f" with {fs.cash(plans[other]['interest'], settings)}" +
            (f", so {best} saves {fs.cash(saving, settings)}." if saving >= 0.01 else "."))
    sections = [fs.stats([(f"{s.title()} done", when[s]) for s in plans] +
                         [(f"{s.title()} interest", fs.cash(p["interest"], settings)) for s, p in plans.items()],
                         f"Paying {fs.cash(sum(d['minimum'] for d in debts.values()) + extra, settings)} a month")]
    for s, p in plans.items():
        step = max(1, math.ceil(len(p["history"]) / 60))
        points = list(range(0, len(p["history"]), step))
        sections.append(fs.chart([_add_months(today, i).strftime("%b %y") for i in points],
                                 [p["history"][i] for i in points], "line", title=f"{s.title()}: total owed"))
    sections.append(fs.table(["Order", "Snowball", "Avalanche"],
                             [[str(i + 1)] + [f"{plans[s]['cleared'][i][0]} ({_add_months(today, plans[s]['cleared'][i][1]).strftime('%b %Y')})"
                                              for s in ("snowball", "avalanche")] for i in range(len(debts))],
                             "Paid off in this order"))
    return fs.board(said, "Debt payoff plan", "finance-debts", sections)


# Payday

def payday_set(settings: Settings, rule, day, start, weeks) -> str:
    if rule not in PAYDAY_RULES:
        raise ValueError("Say whether payday is a day of the month, the last working day, or every few weeks.")
    saved = {"rule": rule}
    if rule == "day_of_month":
        saved["day"] = int(hs.number(day, "day of the month", 1, 31))
    if rule == "every_weeks":
        saved["weeks"] = int(hs.number(weeks or 4, "number of weeks", 1, 8))
        saved["start"] = hs.parse_day(start).isoformat()
    hs.save(settings, fs.PAYDAY, saved)
    nxt = next_payday(saved, hs.today())
    return f"Got it. Next payday is {hs.spoken(nxt)}."


def _working_back(day: date) -> date:
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def _month_payday(rule: dict, year: int, month: int) -> date:
    last = calendar.monthrange(year, month)[1]
    if rule["rule"] == "last_working_day":
        return _working_back(date(year, month, last))
    return _working_back(date(year, month, min(int(rule["day"]), last)))


def next_payday(rule: dict, today: date) -> date:
    if rule.get("rule") == "every_weeks":
        start, step = date.fromisoformat(rule["start"]), 7 * int(rule["weeks"])
        gap = (today - start).days
        return start if gap <= 0 else start + timedelta(days=math.ceil(gap / step) * step)
    year, month = today.year, today.month
    for _ in range(3):
        day = _month_payday(rule, year, month)
        if day >= today:
            return day
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    raise ValueError("I couldn't work out the next payday.")


def _payday(settings: Settings) -> date | None:
    rule = hs.load(settings, fs.PAYDAY, {})
    return next_payday(rule, hs.today()) if rule.get("rule") in PAYDAY_RULES else None


def payday(settings: Settings, balance) -> screen.Shown | str:
    nxt = _payday(settings)
    if nxt is None:
        return "I don't know when payday is yet. Tell me, e.g. 'I get paid on the 25th' or 'the last working day'."
    days = (nxt - hs.today()).days
    if days == 0:
        return "It's payday today!"
    said = f"{hs.plural(days, 'day')} until payday on {hs.spoken(nxt)}."
    if balance is not None:
        bal = fs.amount(balance, "balance", -10_000_000)
        said += f" With {fs.cash(bal, settings)} that's {fs.cash(bal / days, settings)} a day."
    ends = int(datetime.combine(nxt, datetime.min.time()).timestamp() * 1000)
    return screen.Shown(said, screen.card("timer", "Payday countdown", "finance-payday", text=said, ends_at=ends))


# Can I afford it?

def bills_before(settings: Settings, start: date, end: date) -> list[tuple[date, str, float]]:
    due = []
    for label, row in hs.load(settings, homehouse.BILLS, {}).items():
        if not isinstance(row, dict) or "day" not in row:
            continue
        year, month = start.year, start.month
        for _ in range(3):
            when = date(year, month, min(int(row["day"]), calendar.monthrange(year, month)[1]))
            if start <= when < end:
                due.append((when, label, float(row.get("amount") or 0)))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return sorted(due)


def afford(settings: Settings, price, balance) -> screen.Shown:
    if balance is None:
        raise ValueError("What's your balance right now? I need it to check.")
    price, bal = fs.amount(price, "price"), fs.amount(balance, "balance", -10_000_000)
    today = hs.today()
    until = _payday(settings) or _add_months(today, 1)
    bills = bills_before(settings, today, until)
    owed = sum(b[2] for b in bills)
    budget = fs.budget_left(settings, today.strftime("%Y-%m"))
    spare = round(bal - owed - budget, 2)
    ok = spare >= price
    said = (f"Yes. After bills and budgets until {hs.spoken(until)} you'd have {fs.cash(spare - price, settings)} spare."
            if ok else f"Not really: you'd be {fs.cash(price - spare, settings)} short before {hs.spoken(until)}.")
    sections = [fs.stats([("Balance", fs.cash(bal, settings)), ("Bills due", f"-{fs.cash(owed, settings)}"),
                          ("Budgets left", f"-{fs.cash(budget, settings)}"), ("Spare", fs.cash(spare, settings)),
                          ("Price", fs.cash(price, settings)), ("Verdict", "Affordable" if ok else "Too tight")],
                         f"Until {hs.spoken(until)}")]
    if bills:
        sections.append(fs.table(["Due", "Bill", settings.currency], [[d.isoformat(), n, f"{a:,.2f}"] for d, n, a in bills]))
    return fs.board(said, "Can I afford it?", "finance-afford", sections)


# Cost per use and habits

def per_use(settings: Settings, price, uses) -> str:
    price = fs.amount(price, "price")
    uses = hs.number(uses, "number of uses", 1, 10_000_000)
    return f"{fs.cash(price, settings)} over {uses:g} uses is {fs.cash(price / uses, settings)} a use."


def habit_cost(settings: Settings, price, per_week, what) -> screen.Shown:
    price = fs.amount(price, "price")
    times = hs.number(per_week, "times a week", 0.01, 100)
    week = price * times
    year = week * 52
    label = hs.clean(what, 40) or "That habit"
    said = f"{label} costs {fs.cash(year, settings)} a year, about {fs.cash(year / 12, settings)} a month."
    return fs.board(said, f"Cost of {label.lower()}", "finance-habit", [
        fs.stats([("A week", fs.cash(week, settings)), ("A month", fs.cash(year / 12, settings)),
                  ("A year", fs.cash(year, settings)), ("Five years", fs.cash(year * 5, settings))],
                 f"{fs.cash(price, settings)}, {times:g} times a week")])


# Trip budgets

def _currency(value) -> str:
    code = hs.clean(value).upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise ValueError("Give the trip's currency as a three-letter code, e.g. EUR or USD.")
    return code


def trip_set(settings: Settings, name, currency, budget) -> str:
    name = hs.need(name, "trip", 40)
    trips = fs.rows(settings, fs.TRIPS)
    key = hs.find(trips, name) or name
    trip = trips.get(key) or {"spends": []}
    trip.update({"currency": _currency(currency), "budget": fs.amount(budget, "budget")})
    fs.put(settings, fs.TRIPS, trips, key, trip)
    return f"The {key} trip has a budget of {fs.cash(trip['budget'], trip['currency'])}."


def trip_spend(settings: Settings, name, value, what) -> str:
    trips = fs.rows(settings, fs.TRIPS)
    key = fs.key_of(trips, name, "trip")
    trip = trips[key]
    number = fs.amount(value)
    trip["spends"] = (list(trip.get("spends") or []) + [{"date": hs.today().isoformat(), "amount": number,
                                                          "what": hs.clean(what, 60) or "something"}])[-fs.MAX_LOG:]
    fs.put(settings, fs.TRIPS, trips, key, trip)
    total = sum(s["amount"] for s in trip["spends"])
    return (f"Logged {fs.cash(number, trip['currency'])} on the {key} trip; "
            f"{fs.cash(trip['budget'] - total, trip['currency'])} of the budget left.")


async def trip_total(settings: Settings, http, name) -> screen.Shown:
    trips = fs.rows(settings, fs.TRIPS)
    key = fs.key_of(trips, name, "trip")
    trip, cur = trips[key], trips[key]["currency"]
    spends = trip.get("spends") or []
    total = round(sum(s["amount"] for s in spends), 2)
    try:
        converted = await money.convert(http, total, cur, settings.currency) if total else ""
    except (ValueError, httpx.HTTPError):
        converted = "(I couldn't get an exchange rate just now.)"
    said = f"The {key} trip: {fs.cash(total, cur)} spent of {fs.cash(trip['budget'], cur)}. {converted}".strip()
    return fs.board(said, f"Trip: {key}", f"finance-trip-{key}", [
        fs.section("meters", "Spent vs budget", rows=[fs.meter(key, total, trip["budget"] or 1, cur)]),
        fs.stats([("Spent", fs.cash(total, cur)), ("Left", fs.cash(trip["budget"] - total, cur))], converted[:60]),
        fs.table(["Date", "What", cur], [[s["date"], s["what"], f"{s['amount']:,.2f}"] for s in spends[::-1]])])


def tool_definitions() -> list[dict]:
    text, num = {"type": "string"}, {"type": "number"}
    return [{
        "name": "money_planner",
        "description": "Money planning. debt_set (name, balance, apr, minimum), debt_remove (confirmed true only "
                       "after the user agrees), debt_plan: snowball vs avalanche payoff plan with payoff date, total "
                       "interest and a chart (extra = extra paid each month). payday_set (rule day_of_month with "
                       "day, last_working_day, or every_weeks with weeks and start date), payday: days until "
                       "payday and money per day from a balance. afford: can I afford it (price, balance; takes "
                       "off bills due before payday and budget left). per_use: price per use (price, uses). "
                       "habit_cost: yearly cost of a habit (price, per_week, what), e.g. coffee. trip_set (name, "
                       "currency, budget in that currency), trip_spend (name, amount in the local currency, what), "
                       "trip_total converts the total home.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["debt_set", "debt_remove", "debt_plan", "payday_set", "payday",
                                                      "afford", "per_use", "habit_cost", "trip_set", "trip_spend",
                                                      "trip_total"]},
                "name": text, "balance": num, "apr": num, "minimum": num, "extra": num,
                "rule": {"type": "string", "enum": PAYDAY_RULES}, "day": {"type": "integer"},
                "weeks": {"type": "integer"}, "start": {"type": "string", "description": "YYYY-MM-DD"},
                "price": num, "uses": num, "per_week": num, "what": text,
                "currency": text, "budget": num, "amount": num, "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"money_planner"}


async def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    action = a("action")
    if action == "trip_total":
        return await trip_total(settings, http, a("name"))
    actions = {
        "debt_set": lambda: debt_set(settings, a("name"), a("balance"), a("apr"), a("minimum")),
        "debt_remove": lambda: debt_remove(settings, a("name"), bool(a("confirmed"))),
        "debt_plan": lambda: debt_plan(settings, a("extra")),
        "payday_set": lambda: payday_set(settings, a("rule"), a("day"), a("start"), a("weeks")),
        "payday": lambda: payday(settings, a("balance")),
        "afford": lambda: afford(settings, a("price") if a("price") is not None else a("amount"), a("balance")),
        "per_use": lambda: per_use(settings, a("price"), a("uses")),
        "habit_cost": lambda: habit_cost(settings, a("price"), a("per_week"), a("what")),
        "trip_set": lambda: trip_set(settings, a("name"), a("currency"), a("budget")),
        "trip_spend": lambda: trip_spend(settings, a("name"), a("amount"), a("what")),
    }
    if action not in actions:
        raise ValueError("Unknown planner action.")
    return actions[action]()
