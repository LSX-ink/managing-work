"""Kitchen reference in pop-ups, all from local tables (cooking_data): roast times and temperatures, safe core
temperatures, ingredient swaps, UK seasonal produce, cups to grams, bread and baker's percentages, drink pairings.
"""

import calcunits
import cooking_data as data
import homestore as hs
import screen
from config import Settings

ACTIONS = ["roast_time", "safe_temps", "substitute", "seasonal", "cups_to_grams", "baking_ratio", "drink_pairing"]
MEATS = ["chicken", "beef", "lamb", "pork", "turkey"]
DONENESS = ["rare", "medium", "well done"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
US_CUP_ML = 236.588
LB_KG = 0.45359237


def gas_mark(celsius: float) -> str:
    mark = min(calcunits.GAS_MARKS, key=lambda m: abs(calcunits.GAS_MARKS[m] - celsius))
    return {0.25: "¼", 0.5: "½"}.get(mark, f"{mark:g}")


def _clock(minutes: float) -> str:
    h, m = divmod(round(minutes), 60)
    return f"{h} h {m} min" if h and m else f"{h} h" if h else f"{m} min"


def roast_time(meat, weight_kg=None, weight_lb=None, doneness=None) -> screen.Shown:
    meat = hs.clean(meat).lower()
    if meat not in MEATS:
        raise ValueError("Which meat? " + ", ".join(MEATS) + ".")
    if weight_kg is None and weight_lb is None:
        raise ValueError(f"How heavy is the {meat}?")
    kg = hs.number(weight_kg if weight_kg is not None else (weight_lb or 0) * LB_KG, "weight", 0.2, 15)
    key = f"{meat} {doneness if doneness in DONENESS else 'medium'}" if meat in ("beef", "lamb") else meat
    r = data.ROASTS[key]
    extra = data.TURKEY_BIG_EXTRA if meat == "turkey" and kg > data.TURKEY_BIG_KG else r["extra"]
    total = round((r["per_kg"] * kg + extra) / 5) * 5
    rows = [["Weight", f"{kg:.2f}".rstrip("0").rstrip(".") + " kg"], ["Oven", f"{r['temp']}°C"],
            ["Fan oven", f"{r['temp'] - 20}°C"], ["Gas mark", gas_mark(r["temp"])],
            ["Cooking time", _clock(total)], ["Rest (covered in foil)", _clock(r["rest"])],
            ["Core temperature", f"{r['core']}°C in the thickest part"],
            ["Rule used", f"{r['per_kg']} min per kg plus {extra} min"]]
    card = screen.card("table", f"Roast {r['label']}", "cooking-roast", columns=["", ""], rows=rows, buttons=[
        {"label": "Start timers", "say": f"Open my kitchen timers with {r['label']} for {total} minutes and "
                                         f"resting for {r['rest']} minutes."},
        {"label": "Safe temperatures", "say": "Show me safe core temperatures for cooking."}])
    return screen.Shown(f"Roast {r['label']} at {r['temp']}°C, fan {r['temp'] - 20}, gas {gas_mark(r['temp'])}, for "
                        f"about {_clock(total)}, then rest {_clock(r['rest'])}. Check it reaches {r['core']}°C inside.",
                        card)


def safe_temps() -> screen.Shown:
    rows = [[food, f"{c}°C", note] for food, c, note in data.SAFE_TEMPS]
    text = ("Measure with a probe thermometer in the thickest part, away from bone. UK food safety advice: 70°C for "
            "2 minutes or 75°C for 30 seconds for poultry, pork, mince, sausages and reheated food.")
    card = screen.card("table", "Safe core temperatures", "cooking-safe-temps", text=text,
                       columns=["Food", "Core", "Notes"], rows=rows)
    return screen.Shown("Poultry, mince and reheated food need 75°C in the middle; the full table is on screen.", card)


def _lookup(table: dict, name) -> str | None:
    name = hs.clean(name).lower()
    for guess in (name, name.rstrip("s"), name + "s"):
        if guess in table:
            return guess
    return hs.find(table, name)


def substitute(ingredient=None):
    key = _lookup(data.SUBSTITUTES, ingredient) if hs.clean(ingredient) else None
    if key:
        return f"Instead of {key}: {data.SUBSTITUTES[key]}."
    rows = [[k, v] for k, v in sorted(data.SUBSTITUTES.items())]
    card = screen.card("table", "Ingredient swaps", "cooking-swaps", columns=["Instead of", "Use"], rows=rows)
    lead = f"I haven't got a swap for {hs.clean(ingredient)}; " if hs.clean(ingredient) else ""
    return screen.Shown(lead + f"{len(rows)} ingredient swaps are on the screen.", card)


def _month(value) -> int:
    text = hs.clean(value).lower()
    if not text:
        return hs.today().month
    if text.isdigit() and 1 <= int(text) <= 12:
        return int(text)
    found = next((i for i, m in enumerate(MONTHS, 1) if m.startswith(text[:3])), None)
    if not found:
        raise ValueError("Which month?")
    return found


def seasonal(month=None) -> screen.Shown:
    n = _month(month)
    veg, fruit = (s.split(", ") for s in data.SEASONAL[n])
    items = [{"label": f"Veg: {v}", "say": f"Find me a recipe with {v}."} for v in veg]
    items += [{"label": f"Fruit: {f}", "say": f"Find me a recipe with {f}."} for f in fruit]
    after = MONTHS[n % 12].title()
    card = screen.card("list", f"In season in {MONTHS[n - 1].title()} (UK)", "cooking-seasonal", items=items,
                       buttons=[{"label": after, "say": f"What's in season in {after}?"}])
    return screen.Shown(f"In season in {MONTHS[n - 1].title()}: {', '.join(veg[:4])}, and {', '.join(fruit[:2])}.", card)


def cup_grams() -> dict[str, float]:
    found = {k: v * US_CUP_ML for k, v in calcunits.DENSITY.items() if k != "yogurt"}
    return {**found, **data.CUPS}


def cups_to_grams(ingredient=None, cups=None) -> screen.Shown:
    table = cup_grams()
    key = _lookup(table, ingredient) if hs.clean(ingredient) else None
    if hs.clean(ingredient) and not key:
        raise ValueError(f"I don't know how much a cup of {hs.clean(ingredient)} weighs.")
    order = ([key] if key else []) + sorted(k for k in table if k != key)
    rows = [[k, *(f"{table[k] * f:.0f} g" for f in (1, 0.5, 0.25)), f"{table[k] / 16:.0f} g"] for k in order]
    card = screen.card("table", "Cups to grams (US cups)", "cooking-cups",
                       columns=["Ingredient", "1 cup", "½ cup", "¼ cup", "1 tbsp"], rows=rows)
    if not key:
        return screen.Shown(f"Cup weights for {len(rows)} ingredients are on the screen.", card)
    amount = hs.number(cups if cups is not None else 1, "number of cups", 0.01, 100)
    return screen.Shown(f"{amount:g} {'cup' if amount == 1 else 'cups'} of {key} is about "
                        f"{table[key] * amount:.0f} g.", card)


def _style(hydration: float) -> str:
    if hydration < 60:
        return "a stiff dough, like bagels or pretzels"
    if hydration < 66:
        return "a sandwich loaf or rolls"
    if hydration < 76:
        return "a rustic loaf or sourdough"
    return "a wet dough, like ciabatta or focaccia"


def baking_ratio(flour_g, water_g=None, hydration=None, salt_pct=None, yeast_pct=None, extras=None) -> screen.Shown:
    flour = hs.number(flour_g, "flour weight", 10, 50_000)
    if water_g is not None:
        water = hs.number(water_g, "water weight", 0, 50_000)
        hyd = water / flour * 100
    else:
        hyd = hs.number(hydration if hydration is not None else 65, "hydration", 30, 120)
        water = flour * hyd / 100
    salt = flour * hs.number(salt_pct if salt_pct is not None else 2, "salt percentage", 0, 5) / 100
    yeast = flour * hs.number(yeast_pct if yeast_pct is not None else 1, "yeast percentage", 0, 10) / 100
    parts = [("Flour", flour), ("Water", water), ("Salt", salt), ("Yeast (instant)", yeast)]
    for e in (extras or [])[:10]:
        parts.append((hs.clean(e.get("name"), 30) or "Other", hs.number(e.get("grams"), "weight", 0, 50_000)))
    total = sum(g for _, g in parts)
    rows = [[n, f"{g:.1f}".rstrip("0").rstrip(".") + " g", f"{g / flour * 100:.1f}%"] for n, g in parts]
    rows.append(["Total dough", f"{total:.0f} g", f"{total / flour * 100:.1f}%"])
    card = screen.card("table", f"Bread at {hyd:.0f}% hydration", "cooking-baking",
                       text=f"{hyd:.0f}% hydration suits {_style(hyd)}.",
                       columns=["Ingredient", "Weight", "Baker's %"], rows=rows)
    return screen.Shown(f"For {flour:g} g flour at {hyd:.0f}% hydration: {water:.0f} g water, {salt:.0f} g salt, "
                        f"{yeast:.1f} g yeast.", card)


def drink_pairing(dish=None) -> screen.Shown:
    text = hs.clean(dish).lower()
    score = {p[1]: (sum(k in text for k in p[0]), max((len(k) for k in p[0] if k in text), default=0))
             for p in data.PAIRINGS}
    picked = sorted((p for p in data.PAIRINGS if score[p[1]][0]), key=lambda p: score[p[1]], reverse=True)
    rows = [[d, wine, beer, soft] for _, d, wine, beer, soft in (picked or data.PAIRINGS)]
    card = screen.card("table", "Drinks to go with " + (hs.clean(dish) if picked else "food"), "cooking-pairing",
                       columns=["Dish", "Wine", "Beer or cider", "Alcohol-free"], rows=rows)
    if picked:
        _, d, wine, _, soft = picked[0]
        return screen.Shown(f"With {hs.clean(dish)}, try {wine.split(', ')[0]}, or alcohol-free, {soft.lower()}.", card)
    lead = f"I haven't a match for {hs.clean(dish)}; " if text else ""
    return screen.Shown(lead + "the pairing table is on the screen.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "cooking_guide",
        "description": "Kitchen reference pop-ups. roast_time (meat: chicken, beef, lamb, pork, turkey; weight_kg or "
                       "weight_lb; doneness for beef/lamb): roasting time, oven, fan and gas mark temperature, resting "
                       "time and core temperature. safe_temps: safe internal temperatures. substitute (ingredient): "
                       "what to use instead, e.g. no buttermilk or eggs; no ingredient shows every swap. seasonal "
                       "(month): UK fruit and veg in season. cups_to_grams (ingredient, cups): cup weights. "
                       "baking_ratio (flour_g, hydration % or water_g, salt_pct, yeast_pct, extras): bread dough and "
                       "baker's percentages. drink_pairing (dish): wine, beer and alcohol-free drinks to go with it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "meat": {"type": "string", "enum": MEATS},
                "weight_kg": {"type": "number"},
                "weight_lb": {"type": "number"},
                "doneness": {"type": "string", "enum": DONENESS},
                "ingredient": {"type": "string"},
                "cups": {"type": "number"},
                "month": {"type": "string", "description": "Month name or number; default this month."},
                "flour_g": {"type": "number"},
                "water_g": {"type": "number"},
                "hydration": {"type": "number", "description": "Water as % of flour, e.g. 70."},
                "salt_pct": {"type": "number"},
                "yeast_pct": {"type": "number"},
                "extras": {"type": "array", "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "grams": {"type": "number"}},
                    "required": ["name", "grams"], "additionalProperties": False}},
                "dish": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"cooking_guide"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "roast_time":
        return roast_time(args.get("meat"), args.get("weight_kg"), args.get("weight_lb"), args.get("doneness"))
    if action == "safe_temps":
        return safe_temps()
    if action == "substitute":
        return substitute(args.get("ingredient"))
    if action == "seasonal":
        return seasonal(args.get("month"))
    if action == "cups_to_grams":
        return cups_to_grams(args.get("ingredient"), args.get("cups"))
    if action == "baking_ratio":
        return baking_ratio(args.get("flour_g"), args.get("water_g"), args.get("hydration"), args.get("salt_pct"),
                            args.get("yeast_pct"), args.get("extras"))
    if action == "drink_pairing":
        return drink_pairing(args.get("dish"))
    raise ValueError(f"Unknown cooking guide action {action}.")
