"""Event money and food: budget by category (planned against spent), supplier and booking contacts with deposits and
balances due, the menu planner, and a food and drink quantities calculator per guest.

Everything is saved in events.json in the memory folder. Amounts are in pounds.
"""

from datetime import date

import events_data as data
import events_store as store
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.add("events-budget")

ACTIONS = ["budget_set", "spend", "budget", "supplier_add", "supplier_pay", "suppliers", "menu_add", "menu", "food_calc"]


def _cat(value) -> str:
    return hs.need(value, "budget category", 40).lower()


def budget_set(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    cat = _cat(args.get("category"))
    if cat not in event["budget_items"] and len(event["budget_items"]) >= 40:
        raise ValueError("That's plenty of budget categories.")
    event["budget_items"].setdefault(cat, {"planned": 0})["planned"] = store.money(args.get("amount"), "amount")
    store.save(settings, found)
    return f"Planned {store.gbp(event['budget_items'][cat]['planned'])} for {cat} at {key}."


def spend(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    cat = _cat(args.get("category"))
    amount = store.money(args.get("amount"), "amount")
    event["spends"] = (event["spends"] + [{"category": cat, "amount": amount, "note": hs.clean(args.get("note"), 80),
                                           "date": today.isoformat()}])[-store.MAX_ITEMS * 3:]
    store.save(settings, found)
    total = sum(s["amount"] for s in event["spends"])
    limit = event["budget"]
    tail = f" That's {store.gbp(total)} of {store.gbp(limit)}." if limit else f" That's {store.gbp(total)} in total."
    if limit and total > limit:
        tail += f" You're {store.gbp(total - limit)} over budget."
    return f"Logged {store.gbp(amount)} on {cat} for {key}.{tail}"


def budget(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    cats = set(event["budget_items"]) | {s["category"] for s in event["spends"]}
    if not cats:
        raise ValueError(f"There's no budget for {key} yet. Say what you plan to spend on each thing.")
    rows = []
    for c in sorted(cats):
        planned = event["budget_items"].get(c, {}).get("planned", 0)
        spent = round(sum(s["amount"] for s in event["spends"] if s["category"] == c), 2)
        rows.append({"cat": c, "planned": planned, "spent": spent})
    total_spent = round(sum(r["spent"] for r in rows), 2)
    planned = event["budget"] or round(sum(r["planned"] for r in rows), 2)
    said = f"{key}: {store.gbp(total_spent)} spent" + (f" of {store.gbp(planned)}, {store.gbp(planned - total_spent)} left." if planned >= total_spent
                                                       else f", {store.gbp(total_spent - planned)} over the {store.gbp(planned)} budget.")
    card = screen.card("events-budget", f"{key}: budget", f"events-budget-{key}", buttons=[
        store.button("Log spending", f"Log spending for {key}.")],
        data={"rows": rows, "total": {"planned": planned, "spent": total_spent}})
    return screen.Shown(said, card)


def supplier_add(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    who = hs.need(args.get("supplier"), "supplier", 60)
    old = event["suppliers"].get(hs.find(event["suppliers"], who) or who, {})
    entry = {"role": old.get("role", ""), "cost": old.get("cost", 0), "deposit": old.get("deposit", 0),
             "deposit_due": old.get("deposit_due", ""), "balance_due": old.get("balance_due", ""),
             "deposit_paid": old.get("deposit_paid", False), "balance_paid": old.get("balance_paid", False),
             "phone": old.get("phone", "")}
    if hs.clean(args.get("role")):
        entry["role"] = hs.clean(args["role"], 40).lower()
    for field, label in (("cost", "cost"), ("deposit", "deposit")):
        if field in args:
            entry[field] = store.money(args[field], label)
    for field in ("deposit_due", "balance_due"):
        if hs.clean(args.get(field)):
            entry[field] = hs.parse_day(args[field], today).isoformat()
    if hs.clean(args.get("phone"), 30):
        entry["phone"] = hs.clean(args["phone"], 30)
    if entry["deposit"] > entry["cost"] > 0:
        raise ValueError("The deposit can't be more than the cost.")
    event["suppliers"][hs.find(event["suppliers"], who) or who] = entry
    store.save(settings, found)
    balance = entry["cost"] - entry["deposit"]
    return f"Saved {who}" + (f" ({entry['role']})" if entry["role"] else "") + (f": {store.gbp(entry['cost'])}, balance {store.gbp(balance)}." if entry["cost"] else ".")


def supplier_pay(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    who = store.find_in(event["suppliers"], args.get("supplier"), "supplier")
    entry = event["suppliers"][who]
    part = hs.clean(args.get("part")).lower() or "deposit"
    if part not in ("deposit", "balance"):
        raise ValueError("Say whether it's the deposit or the balance.")
    amount = entry["deposit"] if part == "deposit" else round(entry["cost"] - entry["deposit"], 2)
    if entry[f"{part}_paid"]:
        return f"The {part} for {who} is already marked as paid."
    entry[f"{part}_paid"] = True
    if amount:
        event["spends"].append({"category": entry["role"] or "suppliers", "amount": amount,
                                "note": f"{part} for {who}", "date": today.isoformat()})
    store.save(settings, found)
    return f"Marked the {part} for {who} as paid ({store.gbp(amount)})."


def suppliers(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    if not event["suppliers"]:
        raise ValueError(f"No suppliers for {key} yet. Say who you have booked, like the venue, cake or DJ.")
    rows, due = [], []
    for who, s in sorted(event["suppliers"].items()):
        dep = "paid" if s["deposit_paid"] else (f"{store.gbp(s['deposit'])} due {s['deposit_due']}" if s["deposit"] else "-")
        bal = s["cost"] - s["deposit"]
        left = "paid" if s["balance_paid"] else (f"{store.gbp(bal)} due {s['balance_due'] or 'no date'}" if s["cost"] else "-")
        rows.append([who, s["role"] or "-", store.gbp(s["cost"]) if s["cost"] else "-", dep, left, s["phone"] or ""])
        for part, flag, amount in (("deposit", "deposit_paid", s["deposit"]), ("balance", "balance_paid", bal)):
            day = s[f"{part}_due"]
            if day and not s[flag] and amount and day < today.isoformat():
                due.append(f"{who} {part}")
    said = f"{hs.plural(len(rows), 'supplier')} for {key}." + (f" Overdue: {', '.join(due)}." if due else "")
    return screen.Shown(said, screen.card("table", f"{key}: suppliers", f"events-suppliers-{key}",
                                          columns=["Supplier", "Role", "Cost", "Deposit", "Balance", "Phone"], rows=rows))


def menu_add(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    course = hs.clean(args.get("course"), 30).lower() or "mains"
    dishes = [hs.clean(d, 60) for d in (args.get("dishes") or []) if hs.clean(d)]
    if not dishes:
        raise ValueError("Which dishes?")
    have = event["menu"].setdefault(course, [])
    have += [d for d in dishes if d not in have]
    store.save(settings, found)
    return f"{course.title()} for {key}: {', '.join(have)}."


def menu(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    if not event["menu"]:
        raise ValueError(f"There's no menu for {key} yet. Tell me the dishes for each course.")
    diets = sorted({g["diet"] for g in event["guests"].values() if g["diet"] and g["rsvp"] != "no"})
    rows = [[course.title(), ", ".join(dishes)] for course, dishes in event["menu"].items()]
    if diets:
        rows.append(["Dietary needs", ", ".join(diets)])
    return screen.Shown(f"The menu for {key} has {hs.plural(len(event['menu']), 'course')}.",
                        screen.card("table", f"{key}: menu", f"events-menu-{key}", buttons=[
                            store.button("How much food?", f"How much food do I need for {key}?")],
                                    columns=["Course", "Dishes"], rows=rows))


def food_calc(settings: Settings, args: dict, today: date) -> screen.Shown:
    adults = args.get("adults")
    if adults is None:
        event, _key = store.pick(store.load(settings), args.get("name"), today)
        adults = store.headcount(event)
    adults = int(hs.number(adults, "number of adults", 0, 1000))
    kids = int(hs.number(args.get("children", 0), "number of children", 0, 1000))
    if adults + kids == 0:
        raise ValueError("How many guests? Say a number, or add guests and RSVPs first.")
    rows = {}
    for item, per, unit in data.FOOD:
        total = adults * per + kids * data.KIDS_FOOD.get(item, per)
        if total:
            rows[item] = _grams(total) if unit == "g" else f"{total:g} {unit}"
    who = hs.plural(adults, "adult") + (f" and {hs.plural(kids, 'child', 'children')}" if kids else "")
    said = f"For {who}: {rows['Sandwiches']} of sandwiches, {rows['Cake']} of cake and {rows['Soft drinks']} of soft drinks. The full list is on screen."
    return screen.Shown(said, screen.card("table", "How much food and drink", "events-food", columns=["Item", "Quantity"],
                                          rows=[[k, v] for k, v in rows.items()]))


def _grams(total: float) -> str:
    return f"{total / 1000:g} kg" if total >= 1000 else f"{total:g} g"


def tool_definitions() -> list[dict]:
    return [{
        "name": "event_money",
        "description": "Event budget, suppliers and food. action: budget_set = planned amount for a category (venue, "
                       "cake, drinks); spend = log money spent on a category; budget = planned against spent bar "
                       "chart; supplier_add = a supplier or booking (venue, cake, DJ) with role, cost, deposit, "
                       "deposit_due, balance_due, phone; supplier_pay = mark a deposit or balance paid; suppliers = "
                       "table of bookings and what is due; menu_add = dishes for a course; menu = the menu; "
                       "food_calc = how much food and drink for the guests (sandwiches, cake portions, drinks).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "The event; may be left out for the next one."},
                "category": {"type": "string", "description": "e.g. venue, food, cake, drinks, music."},
                "amount": {"type": "number", "description": "Pounds."},
                "note": {"type": "string"},
                "supplier": {"type": "string"},
                "role": {"type": "string", "description": "e.g. venue, cake, DJ, photographer."},
                "cost": {"type": "number"},
                "deposit": {"type": "number"},
                "deposit_due": {"type": "string", "description": "YYYY-MM-DD."},
                "balance_due": {"type": "string", "description": "YYYY-MM-DD."},
                "phone": {"type": "string"},
                "part": {"type": "string", "enum": ["deposit", "balance"]},
                "course": {"type": "string", "description": "starters, mains, puddings, drinks..."},
                "dishes": {"type": "array", "items": {"type": "string"}},
                "adults": {"type": "integer", "description": "food_calc: default the guests coming."},
                "children": {"type": "integer"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"event_money"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action, event = args.get("action"), args.get("name")
    if action == "budget":
        return budget(settings, event, today)
    if action == "suppliers":
        return suppliers(settings, event, today)
    if action == "menu":
        return menu(settings, event, today)
    actions = {"budget_set": budget_set, "spend": spend, "supplier_add": supplier_add, "supplier_pay": supplier_pay,
               "menu_add": menu_add, "food_calc": food_calc}
    if action not in actions:
        raise ValueError(f"Unknown event money action: {action}")
    return actions[action](settings, args, today)
