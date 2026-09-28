"""Household: bin days, bills, subscriptions, key dates (MOT, insurance), packing lists, gift ideas and plants.

Each is a small JSON file in the memory folder. Amounts are in the user's own currency (JARVIS_CURRENCY).
"""

import calendar
from datetime import date, timedelta

import homestore as hs
from config import Settings

BINS, BILLS, SUBS, DATES = "bins.json", "bills.json", "subscriptions.json", "key-dates.json"
PACKING, GIFTS, PLANTS = "packing.json", "gifts.json", "plants.json"
MAX_ROWS = 100


def _rows(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, (dict, list))}


def _put(settings: Settings, name: str, rows: dict, key: str, value) -> None:
    if key not in rows and len(rows) >= MAX_ROWS:
        raise ValueError("That list is full; remove something first.")
    rows[key] = value
    hs.save(settings, name, rows)


def _key(rows: dict, name, what: str) -> str:
    key = hs.find(rows, hs.need(name, what))
    if key is None:
        raise ValueError(f"I haven't got a {what} called {hs.clean(name)}.")
    return key


def _remove(settings: Settings, name: str, label, what: str, confirmed: bool) -> str:
    rows = _rows(settings, name)
    key = _key(rows, label, what)
    if not confirmed:
        return f"Ask the user to confirm removing the {key} {what}, then call again with confirmed true."
    del rows[key]
    hs.save(settings, name, rows)
    return f"Removed the {key} {what}."


# Bins

def bin_set(settings: Settings, label, weekday, fortnightly=False, start=None) -> str:
    label = hs.need(label, "bin", 40)
    weekday = hs.clean(weekday).lower()
    if weekday not in hs.WEEKDAYS:
        raise ValueError("Which day of the week does it go out?")
    today = hs.today()
    if start:
        first = hs.parse_day(start)
        if first.weekday() != hs.WEEKDAYS.index(weekday):
            raise ValueError(f"{hs.spoken(first)} isn't a {weekday.title()}.")
    else:
        first = hs.week_start(today) + timedelta(days=hs.WEEKDAYS.index(weekday))
    every = 2 if fortnightly else 1
    rows = _rows(settings, BINS)
    key = hs.find(rows, label) or label
    _put(settings, BINS, rows, key, {"weekday": weekday, "every": every, "start": first.isoformat()})
    how = f"every other {weekday.title()}, next on {hs.spoken(_next_bin(rows[key], today))}" if every == 2 \
        else f"every {weekday.title()}"
    return f"The {key} bin goes out {how}."


def _next_bin(row: dict, today: date) -> date:
    start = date.fromisoformat(row["start"])
    step = 7 * int(row.get("every") or 1)
    if start >= today:
        return start
    return start + timedelta(days=-(-(today - start).days // step) * step)


def bin_week(settings: Settings) -> str:
    rows = _rows(settings, BINS)
    if not rows:
        return "No bin days set up yet."
    today = hs.today()
    start = hs.week_start(today)
    out = []
    for label, row in rows.items():
        day = start + timedelta(days=hs.WEEKDAYS.index(row["weekday"]))
        first = date.fromisoformat(row["start"])
        step = 7 * int(row.get("every") or 1)
        if day >= first and (day - first).days % step == 0:
            out.append((day, label))
    if not out:
        return "No bins go out this week."
    return "This week: " + "; ".join(
        f"the {label} bin {'went' if day < today else 'goes'} out {'today' if day == today else 'on ' + hs.spoken(day)}"
        for day, label in sorted(out)) + "."


# Bills

def bill_add(settings: Settings, label, amount, day) -> str:
    label = hs.need(label, "bill", 40)
    amount = round(hs.number(amount, "amount"), 2)
    day = int(hs.number(day, "day of the month", 1, 31))
    rows = _rows(settings, BILLS)
    key = hs.find(rows, label) or label
    _put(settings, BILLS, rows, key, {"amount": amount, "day": day})
    return f"The {key} bill is {hs.money(amount, settings.currency)} on day {day} of each month."


def _bill_date(day: int, year: int, month: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def bills_due(settings: Settings, days=None) -> str:
    days = int(hs.number(days if days is not None else 7, "number of days", 0, 62))
    rows = _rows(settings, BILLS)
    if not rows:
        return "No bills set up yet."
    today = hs.today()
    end = today + timedelta(days=days)
    due = []
    for label, row in rows.items():
        year, month = today.year, today.month
        for _ in range(4):
            when = _bill_date(int(row["day"]), year, month)
            if today <= when <= end:
                due.append((when, label, row["amount"]))
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    if not due:
        return f"No bills due in the next {hs.plural(days, 'day')}."
    total = sum(a for _, _, a in due)
    lines = [f"- {label}: {hs.money(amount, settings.currency)} on {hs.spoken(when)}" for when, label, amount in sorted(due)]
    return f"Bills due in the next {hs.plural(days, 'day')} ({hs.money(total, settings.currency)}):\n" + "\n".join(lines)


def bills_total(settings: Settings) -> str:
    rows = _rows(settings, BILLS)
    if not rows:
        return "No bills set up yet."
    total = sum(r["amount"] for r in rows.values())
    return f"{hs.plural(len(rows), 'bill')} come to {hs.money(total, settings.currency)} a month."


# Subscriptions

def sub_add(settings: Settings, label, price, period=None) -> str:
    label = hs.need(label, "subscription", 40)
    price = round(hs.number(price, "price"), 2)
    period = "yearly" if period == "yearly" else "monthly"
    rows = _rows(settings, SUBS)
    key = hs.find(rows, label) or label
    _put(settings, SUBS, rows, key, {"price": price, "period": period})
    return f"Added {key} at {hs.money(price, settings.currency)} {'a year' if period == 'yearly' else 'a month'}."


def subs_total(settings: Settings) -> str:
    rows = _rows(settings, SUBS)
    if not rows:
        return "No subscriptions saved yet."
    cur = settings.currency
    monthly = sum(r["price"] / 12 if r["period"] == "yearly" else r["price"] for r in rows.values())
    lines = [f"- {k}: {hs.money(r['price'], cur)} {'a year' if r['period'] == 'yearly' else 'a month'}" for k, r in rows.items()]
    return (f"{hs.plural(len(rows), 'subscription')}: {hs.money(monthly, cur)} a month, "
            f"{hs.money(monthly * 12, cur)} a year.\n" + "\n".join(lines))


# Car and home key dates

def date_add(settings: Settings, label, when) -> str:
    label = hs.need(label, "date", 60)
    if not when:
        raise ValueError("When is it due?")
    day = hs.parse_day(when)
    rows = _rows(settings, DATES)
    key = hs.find(rows, label) or label
    _put(settings, DATES, rows, key, {"date": day.isoformat()})
    return f"{key} is due on {hs.spoken(day)} {day.year}."


def dates_upcoming(settings: Settings, days=None) -> str:
    days = int(hs.number(days if days is not None else 60, "number of days", 0, 730))
    today = hs.today()
    end = (today + timedelta(days=days)).isoformat()
    soon = sorted((r["date"], k) for k, r in _rows(settings, DATES).items() if today.isoformat() <= r["date"] <= end)
    if not soon:
        return f"Nothing due in the next {hs.plural(days, 'day')}."
    lines = [f"- {k}: {hs.spoken(date.fromisoformat(d))} (in {hs.plural((date.fromisoformat(d) - today).days, 'day')})"
             for d, k in soon]
    return f"Coming up in the next {hs.plural(days, 'day')}:\n" + "\n".join(lines)


# Packing lists

def pack_create(settings: Settings, label, items) -> str:
    label = hs.need(label, "packing list", 40)
    new = [hs.clean(i) for i in (items or []) if hs.clean(i)][:100]
    rows = _rows(settings, PACKING)
    key = hs.find(rows, label) or label
    found = rows.get(key) or []
    have = {i["item"].lower() for i in found}
    found += [{"item": i, "done": False} for i in dict.fromkeys(new) if i.lower() not in have]
    _put(settings, PACKING, rows, key, found)
    return f"The {key} packing list has {hs.plural(len(found), 'item')}."


def pack_tick(settings: Settings, label, items) -> str:
    rows = _rows(settings, PACKING)
    key = _key(rows, label, "packing list")
    words = [hs.clean(i).lower() for i in (items or []) if hs.clean(i)]
    ticked = []
    for row in rows[key]:
        if not row["done"] and any(w in row["item"].lower() for w in words):
            row["done"] = True
            ticked.append(row["item"])
    hs.save(settings, PACKING, rows)
    left = sum(not r["done"] for r in rows[key])
    return (f"Packed {', '.join(ticked)}." if ticked else "None of those were left to pack.") + f" {left} left."


def pack_left(settings: Settings, label) -> str:
    rows = _rows(settings, PACKING)
    key = _key(rows, label, "packing list")
    left = [r["item"] for r in rows[key] if not r["done"]]
    return f"Still to pack for {key}: " + ", ".join(left) + "." if left else f"Everything's packed for {key}."


# Gift ideas

def gift_add(settings: Settings, person, idea) -> str:
    person = hs.need(person, "person", 40)
    idea = hs.need(idea, "gift idea", 120)
    rows = _rows(settings, GIFTS)
    key = hs.find(rows, person) or person
    ideas = rows.get(key) or []
    if idea.lower() not in {i.lower() for i in ideas}:
        ideas.append(idea)
    _put(settings, GIFTS, rows, key, ideas[-50:])
    return f"Saved {idea} as a gift idea for {key}. {hs.plural(len(ideas), 'idea')} for them."


def gift_list(settings: Settings, person) -> str:
    rows = _rows(settings, GIFTS)
    if not person:
        return "Gift ideas saved for: " + ", ".join(rows) + "." if rows else "No gift ideas saved yet."
    key = hs.find(rows, person)
    if key is None:
        return f"No gift ideas for {hs.clean(person)} yet."
    return f"Gift ideas for {key}: " + "; ".join(rows[key]) + "."


# Plants

def plant_add(settings: Settings, label, every) -> str:
    label = hs.need(label, "plant", 40)
    every = int(hs.number(every, "number of days", 1, 90))
    rows = _rows(settings, PLANTS)
    key = hs.find(rows, label) or label
    last = (rows.get(key) or {}).get("last") or hs.today().isoformat()
    _put(settings, PLANTS, rows, key, {"every": every, "last": last})
    return f"The {key} needs water every {hs.plural(every, 'day')}."


def plant_watered(settings: Settings, names) -> str:
    rows = _rows(settings, PLANTS)
    wanted = [n for n in (names or []) if hs.clean(n)]
    keys = list(rows) if not wanted or any(hs.clean(n).lower() in ("all", "everything") for n in wanted) \
        else [_key(rows, n, "plant") for n in wanted]
    if not keys:
        return "No plants set up yet."
    for key in keys:
        rows[key]["last"] = hs.today().isoformat()
    hs.save(settings, PLANTS, rows)
    return f"Watered {', '.join(keys)}."


def plants_due(settings: Settings) -> str:
    rows = _rows(settings, PLANTS)
    if not rows:
        return "No plants set up yet."
    today = hs.today()
    due = [k for k, r in rows.items() if date.fromisoformat(r["last"]) + timedelta(days=int(r["every"])) <= today]
    return "Needs water today: " + ", ".join(due) + "." if due else "No plants need water today."


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "home_household",
        "description": "Household trackers. name is the bin, bill, subscription, key date, packing list, plant or "
                       "person. bin_set (name, weekday, fortnightly, start YYYY-MM-DD of a known collection), "
                       "bin_week says which bins go out this week. bill_add (name, amount, day of month), "
                       "bill_remove, bills_due (days, default 7), bills_total per month. sub_add (name, amount, "
                       "period monthly or yearly), sub_remove, subs_total. date_add (name e.g. 'MOT', date "
                       "YYYY-MM-DD), dates_upcoming (days, default 60). pack_create (name, items), pack_tick "
                       "(name, items), pack_left. gift_add (name = person, idea), gift_list. plant_add (name, "
                       "every = days), plant_watered (items = plant names, empty for all), plants_due. Set "
                       "confirmed true only after the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "bin_set", "bin_week", "bill_add", "bill_remove", "bills_due", "bills_total",
                    "sub_add", "sub_remove", "subs_total", "date_add", "dates_upcoming",
                    "pack_create", "pack_tick", "pack_left", "gift_add", "gift_list",
                    "plant_add", "plant_watered", "plants_due"]},
                "name": text,
                "weekday": {"type": "string", "enum": hs.WEEKDAYS},
                "fortnightly": {"type": "boolean"},
                "start": text,
                "amount": {"type": "number"},
                "day": {"type": "integer", "description": "Day of the month, 1 to 31."},
                "period": {"type": "string", "enum": ["monthly", "yearly"]},
                "date": text,
                "days": {"type": "integer"},
                "items": listed,
                "idea": text,
                "every": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"home_household"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    a = args.get
    action, label, ok = a("action"), a("name"), bool(a("confirmed"))
    actions = {
        "bin_set": lambda: bin_set(settings, label, a("weekday"), bool(a("fortnightly")), a("start")),
        "bin_week": lambda: bin_week(settings),
        "bill_add": lambda: bill_add(settings, label, a("amount"), a("day")),
        "bill_remove": lambda: _remove(settings, BILLS, label, "bill", ok),
        "bills_due": lambda: bills_due(settings, a("days")),
        "bills_total": lambda: bills_total(settings),
        "sub_add": lambda: sub_add(settings, label, a("amount"), a("period")),
        "sub_remove": lambda: _remove(settings, SUBS, label, "subscription", ok),
        "subs_total": lambda: subs_total(settings),
        "date_add": lambda: date_add(settings, label, a("date")),
        "dates_upcoming": lambda: dates_upcoming(settings, a("days")),
        "pack_create": lambda: pack_create(settings, label, a("items")),
        "pack_tick": lambda: pack_tick(settings, label, a("items")),
        "pack_left": lambda: pack_left(settings, label),
        "gift_add": lambda: gift_add(settings, label, a("idea")),
        "gift_list": lambda: gift_list(settings, label),
        "plant_add": lambda: plant_add(settings, label, a("every")),
        "plant_watered": lambda: plant_watered(settings, a("items")),
        "plants_due": lambda: plants_due(settings),
    }
    if action not in actions:
        raise ValueError("Unknown household action.")
    return actions[action]()
