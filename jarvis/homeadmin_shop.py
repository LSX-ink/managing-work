"""Shopping smarter: price per unit, multi-buy deals, "is this a good price" from your own history, gift budgets.

Prices you note go into the grocery price book (household-prices.json); gifts and budgets live in homeadmin.json.
"""

from statistics import mean

import homeadmin_store as store
import homestore as hs
import household_stuff
import screen
from config import Settings

ACTIONS = ["unit_compare", "multibuy", "price_note", "price_check", "gift_budget", "gift_add", "gift_show",
           "gift_remove"]
MASS = {"g": 1, "kg": 1000, "oz": 28.3495, "lb": 453.592}
VOLUME = {"ml": 1, "cl": 10, "l": 1000, "pint": 568.261}
COUNTS = {"each", "pack", "sheet", "roll", "tablet", "pod", "bag", "item", "count", "wash"}
ALIASES = {"gram": "g", "grams": "g", "kilo": "kg", "kilos": "kg", "kilogram": "kg", "kilograms": "kg",
           "ounce": "oz", "ounces": "oz", "pound": "lb", "pounds": "lb", "lbs": "lb", "millilitre": "ml",
           "millilitres": "ml", "litre": "l", "litres": "l", "liter": "l", "liters": "l", "pints": "pint",
           "centilitre": "cl", "centilitres": "cl"}


def _unit(value) -> str:
    text = hs.clean(value, 20).lower().strip(".")
    text = ALIASES.get(text, text)
    return text[:-1] if text.endswith("s") and text[:-1] in COUNTS else text


def _per_unit(price: float, amount: float, unit: str) -> tuple[str, float, str]:
    """(kind, price per 100g / 100ml / each, label for that)."""
    if unit in MASS:
        return "weight", price / (amount * MASS[unit]) * 100, "100g"
    if unit in VOLUME:
        return "volume", price / (amount * VOLUME[unit]) * 100, "100ml"
    if unit in COUNTS:
        return "count", price / amount, unit
    raise ValueError(f"I don't know the unit {unit}. Try g, kg, ml, l, or each.")


def unit_compare(settings: Settings, items) -> screen.Shown:
    rows = []
    for i in (items or [])[:8]:
        price = hs.number(i.get("price"), "price", 0.001, 100_000)
        amount = hs.number(i.get("amount"), "size", 0.001, 1_000_000) * hs.number(i.get("count") or 1, "count", 1, 1000)
        unit = _unit(i.get("unit"))
        kind, per, label = _per_unit(price, amount, unit)
        name = hs.clean(i.get("label")) or f"{amount:g}{unit} for {store.money(price, settings)}"
        rows.append((per, kind, label, name, price))
    if len(rows) < 2:
        raise ValueError("Give me at least two options to compare, each with a price, a size and a unit.")
    if len({r[1] for r in rows}) > 1:
        raise ValueError("Those are different kinds of size (weight, volume or count); I can only compare like with like.")
    rows.sort()
    best = rows[0][0]
    table = [[name, store.money(price, settings), f"{per:.3f} per {label}",
              "Cheapest" if per == best else f"{(per / best - 1) * 100:.0f}% dearer"] for per, _, label, name, price in rows]
    card = screen.card("table", "Price per unit", "homeadmin-unit-compare",
                       columns=["Option", "Price", "Unit price", "Verdict"], rows=table)
    per, _, label, name, _ = rows[0]
    return screen.Shown(f"{name} is the best value at {per:.2f} {settings.currency} per {label}.", card)


def multibuy(settings: Settings, args: dict) -> screen.Shown:
    single = hs.number(args.get("price"), "single price", 0.001, 100_000)
    qty = int(hs.number(args.get("quantity"), "quantity", 2, 1000))
    if args.get("deal_price") is not None:
        deal = hs.number(args["deal_price"], "deal price", 0.001, 1_000_000)
    elif args.get("pay_for") is not None:
        deal = single * hs.number(args["pay_for"], "number you pay for", 0, qty)
    else:
        raise ValueError("Tell me the deal: a total price for the lot, or how many you pay for.")
    each, saving = deal / qty, single * qty - deal
    verdict = "Worth it if you'll use them all" if saving > 0 else "Not a saving; buy them singly"
    card = screen.card("table", "Multi-buy check", "homeadmin-multibuy", columns=["", "Single", f"Deal for {qty}"], rows=[
        ["Each", store.money(single, settings), store.money(each, settings)],
        ["Total", store.money(single * qty, settings), store.money(deal, settings)],
        ["You save", "-", store.money(saving, settings) if saving > 0 else "nothing"], ["Verdict", "", verdict]])
    if saving <= 0:
        return screen.Shown(f"That deal isn't a saving: {qty} cost {store.money(deal, settings)}, buying singly "
                            f"is {store.money(single * qty, settings)}.", card)
    return screen.Shown(f"Saves {store.money(saving, settings)} on {qty}, {store.money(each, settings)} each, "
                        f"{saving / (single * qty) * 100:.0f}% off. Only worth it if you'll use them all.", card)


def price_note(settings: Settings, args: dict) -> str:
    return household_stuff.price_add(settings, args.get("item"), args.get("shop"), args.get("amount"), args.get("date"))


def price_check(settings: Settings, args: dict) -> screen.Shown:
    item = hs.need(args.get("item"), "item", 60)
    history = [p for p in hs.load(settings, household_stuff.PRICES, []) if isinstance(p, dict)]
    names = {p["item"] for p in history}
    key = hs.find(names, item)
    if key is None:
        raise ValueError(f"I haven't noted a price for {item} yet. Tell me what you paid and where.")
    found = [p for p in history if p["item"] == key]
    prices = [p["price"] for p in found]
    low, avg = min(prices), mean(prices)
    shops: dict[str, list[float]] = {}
    for p in found:
        shops.setdefault(p["shop"], []).append(p["price"])
    table = [[shop, store.money(v[-1], settings), store.money(min(v), settings), str(len(v))]
             for shop, v in sorted(shops.items(), key=lambda kv: min(kv[1]))]
    card = screen.card("table", f"{key}: my price history", f"homeadmin-price-{key}",
                       columns=["Shop", "Last paid", "Lowest", "Times"], rows=table)
    if args.get("amount") is None:
        return screen.Shown(f"You usually pay {store.money(avg, settings)} for {key}; the lowest was "
                            f"{store.money(low, settings)}.", card)
    price = hs.number(args["amount"], "price", 0.001, 100_000)
    if len(prices) < 2:
        verdict = "I've only one price noted, so I can't say much yet"
    elif price <= low * 1.02:
        verdict = "A good price, as low as you've ever noted"
    elif price <= avg * 0.97:
        verdict = "Below your average, so decent"
    elif price <= avg * 1.05:
        verdict = "About your usual price"
    else:
        verdict = "Higher than you usually pay"
    return screen.Shown(f"{verdict}. {store.money(price, settings)} for {key}; your average is "
                        f"{store.money(avg, settings)} and the lowest {store.money(low, settings)}.", card)


# Gifts

def _occasion(value) -> str:
    return hs.clean(value, 40).title() or "Christmas"


def gift_budget(settings: Settings, args: dict) -> str:
    occasion = _occasion(args.get("occasion"))
    data = store.load(settings)
    data["budgets"][occasion] = round(hs.number(args.get("amount"), "budget", 0, 1_000_000), 2)
    store.save(settings, data)
    return f"Set the {occasion} gift budget to {store.money(data['budgets'][occasion], settings)}."


def gift_add(settings: Settings, args: dict) -> str:
    occasion, person = _occasion(args.get("occasion")), hs.need(args.get("person"), "person", 40).title()
    gift = hs.need(args.get("gift"), "gift", 80)
    cost = round(hs.number(args.get("amount") or 0, "cost", 0, 100_000), 2)
    data = store.load(settings)
    for g in data["gifts"]:
        if (g["occasion"], g["person"], g["gift"].lower()) == (occasion, person, gift.lower()):
            g["cost"] = cost or g["cost"]
            g["bought"] = bool(args.get("bought", g["bought"]))
            break
    else:
        data["gifts"] = store.add(data["gifts"], {"occasion": occasion, "person": person, "gift": gift,
                                                  "cost": cost, "bought": bool(args.get("bought"))})
    store.save(settings, data)
    spent = sum(g["cost"] for g in data["gifts"] if g["occasion"] == occasion)
    left = data["budgets"].get(occasion)
    tail = f" {store.money(left - spent, settings)} of the budget left." if left is not None and left >= spent else (
        f" That's {store.money(spent - left, settings)} over budget." if left is not None else "")
    return f"Noted {gift} for {person}, {occasion}.{tail}"


def gift_show(settings: Settings, args: dict) -> screen.Shown:
    occasion = _occasion(args.get("occasion"))
    data = store.load(settings)
    gifts = sorted((g for g in data["gifts"] if g["occasion"] == occasion), key=lambda g: (g["person"], g["gift"]))
    if not gifts:
        raise ValueError(f"No {occasion} gifts noted yet. Say who it's for, what, and roughly what it costs.")
    rows = [[g["person"], g["gift"], store.money(g["cost"], settings), "Bought" if g["bought"] else "To buy"]
            for g in gifts]
    spent = sum(g["cost"] for g in gifts)
    bought = sum(g["cost"] for g in gifts if g["bought"])
    budget = data["budgets"].get(occasion)
    rows.append(["Total", "", store.money(spent, settings), f"{store.money(bought, settings)} bought"])
    if budget is not None:
        rows.append(["Budget", "", store.money(budget, settings), f"{store.money(budget - spent, settings)} left"])
    card = screen.card("table", f"{occasion} gifts", f"homeadmin-gifts-{occasion}",
                       columns=["Person", "Gift", "Cost", "Status"], rows=rows)
    over = f", {store.money(spent - budget, settings)} over your budget" if budget is not None and spent > budget else (
        f" of a {store.money(budget, settings)} budget" if budget is not None else "")
    return screen.Shown(f"{hs.plural(len(gifts), 'gift')} for {occasion}, planned at {store.money(spent, settings)}{over}.", card)


def gift_remove(settings: Settings, args: dict) -> str:
    occasion, gift = _occasion(args.get("occasion")), hs.need(args.get("gift"), "gift", 80)
    data = store.load(settings)
    mine = [g for g in data["gifts"] if g["occasion"] == occasion]
    found = mine[store.index(mine, gift, "gift", "gift")]
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {found['gift']} for {found['person']}, then call again with confirmed true."
    data["gifts"].remove(found)
    store.save(settings, data)
    return f"Removed {found['gift']} for {found['person']}."


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "homeadmin_shop",
        "description": "Shop smarter. unit_compare which is better value (items: label, price, amount, unit like g/kg/"
                       "ml/l/each, optional count) as a table; multibuy check a deal (price = single price, quantity, "
                       "then deal_price = total for the lot, or pay_for = how many you pay for, e.g. 3 for 2); "
                       "price_note what I paid (item, shop, amount, optional date); price_check 'is this a good price' "
                       "against my own history (item, optional amount). Gifts for Christmas or birthdays: gift_budget "
                       "(occasion, amount), gift_add (occasion, person, gift, amount, bought), gift_show table with "
                       "budget left, gift_remove. Set confirmed true only after the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "label": text, "price": {"type": "number"}, "amount": {"type": "number"}, "unit": text,
                    "count": {"type": "integer"}}, "required": ["price", "amount", "unit"],
                    "additionalProperties": False}},
                "price": {"type": "number"},
                "quantity": {"type": "integer"},
                "deal_price": {"type": "number"},
                "pay_for": {"type": "number"},
                "item": text,
                "shop": text,
                "amount": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD or 'today'."},
                "occasion": {"type": "string", "description": "Christmas (default), a birthday name..."},
                "person": text,
                "gift": text,
                "bought": {"type": "boolean"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"homeadmin_shop"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "unit_compare":
        return unit_compare(settings, args.get("items"))
    handlers = {"multibuy": multibuy, "price_note": price_note, "price_check": price_check, "gift_budget": gift_budget,
                "gift_add": gift_add, "gift_show": gift_show, "gift_remove": gift_remove}
    if action not in handlers:
        raise ValueError(f"Unknown shopping action: {action}")
    return handlers[action](settings, args)
