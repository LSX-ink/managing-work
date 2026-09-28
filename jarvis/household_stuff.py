"""Things in the house: a home inventory with warranties, the freezer, a grocery price book and DIY projects.

Each is a small household-*.json file in the memory folder. Money is in the user's own currency (JARVIS_CURRENCY).
"""

from datetime import date, timedelta

import homestore as hs
import household_store as hh
import screen
from config import Settings

INVENTORY, FREEZER, PRICES, DIY = ("household-inventory.json", "household-freezer.json",
                                   "household-prices.json", "household-diy.json")
MAX_FREEZER, MAX_PRICES, MAX_MATERIALS = 300, 2000, 100


# Home inventory

def inv_add(settings: Settings, label, room, value, bought=None, warranty=None) -> str:
    label = hs.need(label, "item", 60)
    room = hs.clean(room, 40).title() or "Unsorted"
    value = round(hs.number(value or 0, "value"), 2)
    row = {"room": room, "value": value, "bought": hs.parse_day(bought).isoformat() if bought else "",
           "warranty": hs.parse_day(warranty).isoformat() if warranty else ""}
    found = hh.rows(settings, INVENTORY)
    k = hs.find(found, label) or label
    hh.put(settings, INVENTORY, found, k, row)
    extra = f", under warranty until {hs.spoken(date.fromisoformat(row['warranty']))}" if row["warranty"] else ""
    return f"Saved {k} in the {room}, worth {hs.money(value, settings.currency)}{extra}."


def inv_list(settings: Settings, room=None) -> screen.Shown | str:
    found = hh.rows(settings, INVENTORY)
    if room:
        found = {k: r for k, r in found.items() if hs.clean(room).lower() in r["room"].lower()}
    if not found:
        return "Nothing in the home inventory yet." if not room else f"Nothing saved in the {hs.clean(room)}."
    cur = settings.currency
    rows = [[k, r["room"], hs.money(r["value"], cur), r["bought"] or "-", r["warranty"] or "-"]
            for k, r in sorted(found.items(), key=lambda kv: (kv[1]["room"], kv[0].lower()))]
    total = sum(r["value"] for r in found.values())
    card = screen.card("table", f"Home inventory{' - ' + hs.clean(room).title() if room else ''}", "household-inventory",
                       columns=["Item", "Room", "Value", "Bought", "Warranty until"], rows=rows,
                       buttons=[{"label": "Value by room", "say": "Show my home inventory value by room."}])
    return screen.Shown(f"{hs.plural(len(rows), 'item')} worth {hs.money(total, cur)}; it's on the screen.", card)


def inv_warranties(settings: Settings, days=None) -> screen.Shown | str:
    days = int(hs.number(days if days is not None else 90, "number of days", 1, 3650))
    today = hs.today()
    end = today + timedelta(days=days)
    soon = sorted((date.fromisoformat(r["warranty"]), k) for k, r in hh.rows(settings, INVENTORY).items()
                  if r.get("warranty") and today <= date.fromisoformat(r["warranty"]) <= end)
    if not soon:
        return f"No warranties run out in the next {hs.plural(days, 'day')}."
    card = screen.card("table", "Warranties ending soon", "household-warranties", columns=["Item", "Ends", "When"],
                       rows=[[k, hh.short(d), hh.until(d, today)] for d, k in soon])
    return screen.Shown(f"{hs.plural(len(soon), 'warranty', 'warranties')} ending soon; the first is "
                        f"{soon[0][1]} on {hs.spoken(soon[0][0])}.", card)


def inv_rooms(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, INVENTORY)
    if not found:
        return "Nothing in the home inventory yet."
    rooms: dict[str, float] = {}
    for r in found.values():
        rooms[r["room"]] = rooms.get(r["room"], 0) + r["value"]
    ranked = sorted(rooms.items(), key=lambda kv: -kv[1])
    card = screen.card("chart", "Home contents value by room", "household-rooms",
                       text=f"Total {hs.money(sum(rooms.values()), settings.currency)}",
                       chart={"type": "bar", "labels": [k for k, _ in ranked], "values": [round(v, 2) for _, v in ranked]})
    return screen.Shown(f"Everything comes to {hs.money(sum(rooms.values()), settings.currency)}; the "
                        f"{ranked[0][0]} holds the most.", card)


# Freezer

def _freezer(settings: Settings) -> list[dict]:
    return [i for i in hs.load(settings, FREEZER, []) if isinstance(i, dict) and i.get("item")]


def freezer_add(settings: Settings, items, frozen=None) -> str:
    new = hh.words(items)
    if not new:
        raise ValueError("What's going in the freezer?")
    day = hs.parse_day(frozen).isoformat()
    found = _freezer(settings)
    if len(found) + len(new) > MAX_FREEZER:
        raise ValueError("The freezer list is full; take something out first.")
    found += [{"item": i, "frozen": day} for i in new]
    hs.save(settings, FREEZER, found)
    return f"Frozen {', '.join(new)}. {hs.plural(len(found), 'thing')} in the freezer."


def freezer_take(settings: Settings, items) -> str:
    found = sorted(_freezer(settings), key=lambda i: i["frozen"])
    taken = []
    for w in (w.lower() for w in hh.words(items)):
        match = next((i for i in found if w in i["item"].lower()), None)
        if match:
            found.remove(match)
            taken.append(match["item"])
    hs.save(settings, FREEZER, found)
    return (f"Took out {', '.join(taken)}." if taken else "None of those are in the freezer.") + \
        f" {hs.plural(len(found), 'thing')} left."


def freezer_list(settings: Settings) -> screen.Shown | str:
    found = sorted(_freezer(settings), key=lambda i: i["frozen"])
    if not found:
        return "The freezer list is empty."
    today = hs.today()
    rows = [[i["item"], hh.short(date.fromisoformat(i["frozen"])),
             hs.plural((today - date.fromisoformat(i["frozen"])).days, "day")] for i in found]
    card = screen.card("table", "Freezer, oldest first", "household-freezer",
                       columns=["Item", "Frozen", "In for"], rows=rows)
    return screen.Shown(f"{hs.plural(len(found), 'thing')} in the freezer; {found[0]['item']} has been in "
                        f"longest, {rows[0][2]}.", card)


# Grocery price book

def _prices(settings: Settings, item) -> tuple[str, list[dict]]:
    item = hs.need(item, "item", 60)
    found = [p for p in hs.load(settings, PRICES, []) if isinstance(p, dict)]
    k = hs.find({p["item"] for p in found}, item)
    if k is None:
        raise ValueError(f"I haven't got any prices for {item}.")
    return k, sorted((p for p in found if p["item"] == k), key=lambda p: p["date"])


def price_add(settings: Settings, item, shop, price, day=None) -> str:
    item = hs.need(item, "item", 60)
    shop = hs.need(shop, "shop", 40).title()
    price = round(hs.number(price, "price", 0.01, 100_000), 2)
    found = [p for p in hs.load(settings, PRICES, []) if isinstance(p, dict)]
    item = hs.find({p["item"] for p in found}, item) or item
    shop = hs.find({p["shop"] for p in found}, shop) or shop
    found.append({"item": item, "shop": shop, "price": price, "date": hs.parse_day(day).isoformat()})
    hs.save(settings, PRICES, found[-MAX_PRICES:])
    return f"{item} is {hs.money(price, settings.currency)} at {shop}."


def price_cheapest(settings: Settings, item) -> screen.Shown:
    k, found = _prices(settings, item)
    latest = {p["shop"]: p for p in found}
    ranked = sorted(latest.values(), key=lambda p: p["price"])
    cur = settings.currency
    card = screen.card("table", f"{k}: latest prices", f"household-prices-{k}", columns=["Shop", "Price", "Seen"],
                       rows=[[p["shop"], hs.money(p["price"], cur), p["date"]] for p in ranked],
                       buttons=[{"label": "Price history", "say": f"Show the price history for {k}."}])
    best = ranked[0]
    return screen.Shown(f"{k} is cheapest at {best['shop']}, {hs.money(best['price'], cur)}.", card)


def price_history(settings: Settings, item, shop=None) -> screen.Shown:
    k, found = _prices(settings, item)
    if shop:
        found = [p for p in found if hs.clean(shop).lower() in p["shop"].lower()] or found
    found = found[-60:]
    shops = {p["shop"] for p in found}
    labels = [f"{date.fromisoformat(p['date']):%d %b}" + ("" if len(shops) == 1 else f" {p['shop']}") for p in found]
    card = screen.card("chart", f"{k} price history", f"household-price-history-{k}",
                       chart={"type": "line", "labels": labels, "values": [p["price"] for p in found]})
    first, last = found[0]["price"], found[-1]["price"]
    trend = "up" if last > first else "down" if last < first else "flat"
    return screen.Shown(f"{k} has gone {trend}, from {hs.money(first, settings.currency)} to "
                        f"{hs.money(last, settings.currency)}." if trend != "flat" else
                        f"{k} has stayed at {hs.money(last, settings.currency)}.", card)


# DIY projects

def diy_add(settings: Settings, label, items=None) -> str:
    label = hs.need(label, "project", 60)
    found = hh.rows(settings, DIY)
    k = hs.find(found, label) or label
    project = found.get(k) or {"materials": []}
    have = {m["item"].lower() for m in project["materials"]}
    project["materials"] += [{"item": i, "cost": 0, "done": False} for i in hh.words(items) if i.lower() not in have]
    project["materials"] = project["materials"][:MAX_MATERIALS]
    hh.put(settings, DIY, found, k, project)
    return f"The {k} project has {hs.plural(len(project['materials']), 'material')}."


def diy_cost(settings: Settings, label, item, cost) -> str:
    found = hh.rows(settings, DIY)
    k = hh.key(found, label, "project")
    item = hs.need(item, "material", 80)
    cost = round(hs.number(cost, "cost"), 2)
    mats = found[k]["materials"]
    match = next((m for m in mats if m["item"].lower() == item.lower()), None) or \
        next((m for m in mats if item.lower() in m["item"].lower()), None)
    if match:
        match["cost"] = cost
    elif len(mats) < MAX_MATERIALS:
        mats.append({"item": item, "cost": cost, "done": False})
    hs.save(settings, DIY, found)
    total = sum(m["cost"] for m in mats)
    return f"{match['item'] if match else item} costs {hs.money(cost, settings.currency)}. The {k} project " \
           f"comes to {hs.money(total, settings.currency)}."


def diy_tick(settings: Settings, label, items) -> str:
    found = hh.rows(settings, DIY)
    k = hh.key(found, label, "project")
    words = [w.lower() for w in hh.words(items)]
    ticked = [m["item"] for m in found[k]["materials"] if not m["done"] and any(w in m["item"].lower() for w in words)]
    for m in found[k]["materials"]:
        m["done"] = m["done"] or m["item"] in ticked
    hs.save(settings, DIY, found)
    left = sum(not m["done"] for m in found[k]["materials"])
    return (f"Got {', '.join(ticked)}." if ticked else "None of those were left to get.") + f" {left} left to get."


def diy_show(settings: Settings, label) -> screen.Shown:
    found = hh.rows(settings, DIY)
    k = hh.key(found, label, "project")
    mats = found[k]["materials"]
    cur = settings.currency
    items = [{"label": m["item"] + (f" - {hs.money(m['cost'], cur)}" if m["cost"] else ""), "done": m["done"],
              "say": f"Tick off {m['item']} for the {k} project."} for m in mats]
    total = sum(m["cost"] for m in mats)
    left = sum(not m["done"] for m in mats)
    card = screen.card("list", f"DIY: {k}", f"household-diy-{k}", items=items, checks=True,
                       text=f"Materials total {hs.money(total, cur)}; {left} still to get.")
    return screen.Shown(f"The {k} project: {hs.plural(len(mats), 'material')}, {hs.money(total, cur)} in all, "
                        f"{left} still to get.", card)


def diy_list(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, DIY)
    if not found:
        return "No DIY projects yet."
    cur = settings.currency
    rows = [[k, str(len(p["materials"])), str(sum(not m["done"] for m in p["materials"])),
             hs.money(sum(m["cost"] for m in p["materials"]), cur)] for k, p in found.items()]
    card = screen.card("table", "DIY projects", "household-diy", columns=["Project", "Materials", "To get", "Cost"],
                       rows=rows)
    return screen.Shown(f"{hs.plural(len(rows), 'DIY project')}: {', '.join(found)}.", card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "household_stuff",
        "description": "Home inventory, freezer, grocery price book and DIY projects. inv_add (name, room, amount = "
                       "value, optional date bought and until = warranty end), inv_list (optional room), "
                       "inv_warranties expiring soon (days, default 90), inv_rooms bar chart of total value by room, "
                       "inv_remove (name). freezer_add (items, optional date frozen), freezer_take (items taken out "
                       "or used), freezer_list oldest first. price_add (name = grocery item, shop, amount = price, "
                       "optional date), price_cheapest ('where is milk cheapest?'), price_history chart (name, "
                       "optional shop). diy_add project (name, optional items = materials), diy_cost (name, item, "
                       "amount), diy_tick materials bought (name, items), diy_show checklist and total, diy_list, "
                       "diy_remove. Set confirmed true only after the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "inv_add", "inv_list", "inv_warranties", "inv_rooms", "inv_remove", "freezer_add", "freezer_take",
                    "freezer_list", "price_add", "price_cheapest", "price_history", "diy_add", "diy_cost", "diy_tick",
                    "diy_show", "diy_list", "diy_remove"]},
                "name": text,
                "room": text,
                "shop": text,
                "item": text,
                "items": {"type": "array", "items": text},
                "amount": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'."},
                "until": {"type": "string", "description": "Warranty end, YYYY-MM-DD."},
                "days": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"household_stuff"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    label, items, ok = a("name"), a("items"), bool(a("confirmed"))
    actions = {
        "inv_add": lambda: inv_add(settings, label, a("room"), a("amount"), a("date"), a("until")),
        "inv_list": lambda: inv_list(settings, a("room")),
        "inv_warranties": lambda: inv_warranties(settings, a("days")),
        "inv_rooms": lambda: inv_rooms(settings),
        "inv_remove": lambda: hh.remove(settings, INVENTORY, label, "inventory item", ok),
        "freezer_add": lambda: freezer_add(settings, items or [label], a("date")),
        "freezer_take": lambda: freezer_take(settings, items or [label]),
        "freezer_list": lambda: freezer_list(settings),
        "price_add": lambda: price_add(settings, label or a("item"), a("shop"), a("amount"), a("date")),
        "price_cheapest": lambda: price_cheapest(settings, label or a("item")),
        "price_history": lambda: price_history(settings, label or a("item"), a("shop")),
        "diy_add": lambda: diy_add(settings, label, items),
        "diy_cost": lambda: diy_cost(settings, label, a("item"), a("amount")),
        "diy_tick": lambda: diy_tick(settings, label, items or [a("item")]),
        "diy_show": lambda: diy_show(settings, label),
        "diy_list": lambda: diy_list(settings),
        "diy_remove": lambda: hh.remove(settings, DIY, label, "project", ok),
    }
    if a("action") not in actions:
        raise ValueError("Unknown household stuff action.")
    return actions[a("action")]()
