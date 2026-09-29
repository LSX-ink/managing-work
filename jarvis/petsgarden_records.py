"""Garden records: a harvest log with totals chart, a seed stock list with sow-by dates, and raised bed planners.

Saved in petsgarden.json in the memory folder and never sent anywhere. The raised bed is a grid pop-up: type a plant
in its box, then click squares to plant them.
"""

import calendar
from datetime import date

import homestore as hs
import household_store as hh
import petsgarden_store as store
import screen
from config import Settings

screen.EXTRA_KINDS.add("petsgarden-bed")
ACTIONS = ["harvest_log", "harvest_totals", "seed_add", "seed_list", "seed_remove", "bed_set", "bed_show", "bed_remove"]
MAX_BED = 12
MAX_HARVEST = 1000


def harvest_log(settings: Settings, args: dict, today: date) -> str:
    data = store.load(settings)
    crop = hs.need(args.get("crop"), "crop", 40).lower()
    amount = hs.number(args.get("amount"), "amount", 0.001, 100_000)
    unit = "kg" if hs.clean(args.get("unit")).lower() in ("", "kg", "kilos", "kilo", "kilograms") else "each"
    data["harvest"] = (data["harvest"] + [{"date": hs.parse_day(args.get("day"), today).isoformat(), "crop": crop,
                                            "amount": amount, "unit": unit}])[-MAX_HARVEST:]
    store.save(settings, data)
    total = sum(h["amount"] for h in data["harvest"] if h["crop"] == crop and h["unit"] == unit
                and h["date"][:4] == str(today.year))
    return f"Logged {amount:g}{' kg' if unit == 'kg' else ''} of {crop}. That's {total:g}{' kg' if unit == 'kg' else ''} this year."


def harvest_totals(settings: Settings, args: dict, today: date) -> screen.Shown:
    year = int(hs.number(args.get("year") or today.year, "year", 2000, 2100))
    found = [h for h in store.load(settings)["harvest"] if h["date"][:4] == str(year)]
    if not found:
        raise ValueError(f"No harvest logged for {year} yet. Say what you picked and how much.")
    unit = hs.clean(args.get("unit")).lower()
    unit = "each" if unit in ("each", "count", "number") else "kg" if unit else max(
        ("kg", "each"), key=lambda u: sum(h["unit"] == u for h in found))
    totals: dict[str, float] = {}
    for h in found:
        if h["unit"] == unit:
            totals[h["crop"]] = totals.get(h["crop"], 0) + h["amount"]
    ranked = sorted(totals.items(), key=lambda x: -x[1])[:15]
    label = "kg" if unit == "kg" else "picked"
    card = screen.card("chart", f"Harvest {year}", f"petsgarden-harvest-{year}-{unit}",
                       chart={"type": "bar", "labels": [c.title() for c, _ in ranked], "values": [round(v, 2) for _, v in ranked],
                              "unit": "kg" if unit == "kg" else ""})
    best = ranked[0]
    return screen.Shown(f"In {year} you've harvested {len(totals)} crops; the most is {best[0]} at {best[1]:g} {label}.", card)


def _sow_by(value) -> str:
    text = hs.clean(value)
    if not text:
        return ""
    try:
        if len(text) == 7:
            year, month = int(text[:4]), int(text[5:7])
            return date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        return date.fromisoformat(text).isoformat()
    except ValueError:
        raise ValueError("Give the sow-by date as YYYY-MM-DD or YYYY-MM.") from None


def seed_add(settings: Settings, args: dict) -> str:
    data = store.load(settings)
    name = hs.need(args.get("seed"), "seed", 60)
    seed = next((s for s in data["seeds"] if s["name"].lower() == name.lower()), None)
    if seed is None:
        if len(data["seeds"]) >= store.MAX_ITEMS:
            raise ValueError("The seed box is full; remove something first.")
        seed = {"name": name, "packets": 1, "sow_by": ""}
        data["seeds"].append(seed)
    if args.get("packets") is not None:
        seed["packets"] = int(hs.number(args["packets"], "number of packets", 0, 1000))
    if hs.clean(args.get("sow_by")):
        seed["sow_by"] = _sow_by(args["sow_by"])
    store.save(settings, data)
    by = f", sow by {hh.short(date.fromisoformat(seed['sow_by']))}" if seed["sow_by"] else ""
    return f"Noted {hs.plural(seed['packets'], 'packet')} of {seed['name']}{by}."


def seed_list(settings: Settings, today: date) -> screen.Shown:
    seeds = store.load(settings)["seeds"]
    if not seeds:
        raise ValueError("Your seed box is empty. Tell me a seed packet and its sow-by date.")
    seeds = sorted(seeds, key=lambda s: s["sow_by"] or "9999")
    rows, old = [], 0
    for s in seeds:
        when = ""
        if s["sow_by"]:
            day = date.fromisoformat(s["sow_by"])
            when = hh.short(day) + (" (expired)" if day < today else f" ({hh.until(day, today)})")
            old += day < today
        rows.append([s["name"], str(s["packets"]), when or "no date"])
    card = screen.card("table", "Seed box", "petsgarden-seeds", columns=["Seed", "Packets", "Sow by"], rows=rows,
                       buttons=[{"label": "What to sow now", "say": "What can I sow this month?"}])
    return screen.Shown(f"You have {len(seeds)} seed packets" + (f"; {old} past their sow-by date." if old else "."), card)


def seed_remove(settings: Settings, name, confirmed: bool) -> str:
    data = store.load(settings)
    key = store.match([s["name"] for s in data["seeds"]], name, "seed")
    if not confirmed:
        return f"Ask the user to confirm removing {key} from the seed box, then call again with confirmed true."
    data["seeds"] = [s for s in data["seeds"] if s["name"] != key]
    store.save(settings, data)
    return f"Removed {key} from the seed box."


# Raised beds

def _bed(data: dict, name) -> tuple[str, dict]:
    beds = data["beds"]
    if not hs.clean(name) and len(beds) == 1:
        return next(iter(beds.items()))
    key = store.match(beds, name, "bed")
    return key, beds[key]


def bed_set(settings: Settings, args: dict) -> screen.Shown:
    data = store.load(settings)
    name = hs.clean(args.get("bed"), 40)
    if not name:
        name = next(iter(data["beds"])) if len(data["beds"]) == 1 else "Raised bed" if not data["beds"] else hs.need("", "bed")
    key = hs.find(data["beds"], name) or name
    rows, cols = args.get("rows"), args.get("cols")
    bed = data["beds"].get(key)
    if bed is None:
        if len(data["beds"]) >= 10:
            raise ValueError("That's plenty of beds; remove one first.")
        bed = {"rows": 4, "cols": 4, "cells": {}}
        data["beds"][key] = bed
    if rows is not None or cols is not None:
        bed["rows"] = int(hs.number(rows or bed["rows"], "number of rows", 1, MAX_BED))
        bed["cols"] = int(hs.number(cols or bed["cols"], "number of columns", 1, MAX_BED))
        bed["cells"] = {k: v for k, v in bed["cells"].items() if _inside(k, bed)}
    if args.get("row") is not None:
        r = int(hs.number(args["row"], "row", 1, bed["rows"]))
        c = int(hs.number(args.get("col", 1), "column", 1, bed["cols"]))
        plant = hs.clean(args.get("plant"), 30)
        if plant:
            bed["cells"][f"{r},{c}"] = plant
        else:
            bed["cells"].pop(f"{r},{c}", None)
    store.save(settings, data)
    return _bed_card(key, bed, f"{key} is {bed['rows']} by {bed['cols']} squares with {len(bed['cells'])} planted.")


def _inside(cell: str, bed: dict) -> bool:
    r, c = (int(x) for x in cell.split(","))
    return r <= bed["rows"] and c <= bed["cols"]


def _bed_card(key: str, bed: dict, said: str) -> screen.Shown:
    grid = [[bed["cells"].get(f"{r},{c}", "") for c in range(1, bed["cols"] + 1)] for r in range(1, bed["rows"] + 1)]
    plants = sorted({v.lower() for v in bed["cells"].values()})
    card = screen.card("petsgarden-bed", key, f"petsgarden-bed-{key}", data={"bed": key, "grid": grid, "plants": plants},
                       buttons=[{"label": "Companion tips", "say": "Show the companion planting table."}])
    return screen.Shown(said, card)


def bed_show(settings: Settings, name) -> screen.Shown:
    data = store.load(settings)
    if not data["beds"]:
        raise ValueError("You haven't planned a bed yet. Say how many rows and columns it has.")
    key, bed = _bed(data, name)
    return _bed_card(key, bed, f"{key} is on the screen: {len(bed['cells'])} of {bed['rows'] * bed['cols']} squares planted.")


def bed_remove(settings: Settings, name, confirmed: bool) -> str:
    data = store.load(settings)
    key, _ = _bed(data, name)
    if not confirmed:
        return f"Ask the user to confirm removing the {key} plan, then call again with confirmed true."
    del data["beds"][key]
    store.save(settings, data)
    return f"Removed the {key} plan."


def tool_definitions() -> list[dict]:
    return [{
        "name": "garden_records",
        "description": "The user's own garden records, kept privately. action: harvest_log = log something picked "
                       "(crop, amount, unit kg or each); harvest_totals = harvest totals chart for a year; seed_add = "
                       "add or update a seed packet (seed, packets, sow_by); seed_list = the seed stock list with "
                       "sow-by dates; seed_remove and bed_remove (confirmed true only after the user says yes); "
                       "bed_set = plan a raised bed grid: set its rows and cols, or plant a plant in one square "
                       "(row, col; no plant clears it); bed_show = the raised bed planner pop-up.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "crop": {"type": "string"},
                "amount": {"type": "number"},
                "unit": {"type": "string", "enum": ["kg", "each"]},
                "day": {"type": "string", "description": "harvest_log: YYYY-MM-DD, today or a weekday."},
                "year": {"type": "integer"},
                "seed": {"type": "string"},
                "packets": {"type": "integer"},
                "sow_by": {"type": "string", "description": "YYYY-MM-DD or YYYY-MM."},
                "bed": {"type": "string", "description": "Bed name; may be left out when there is only one."},
                "rows": {"type": "integer"}, "cols": {"type": "integer"},
                "row": {"type": "integer"}, "col": {"type": "integer"},
                "plant": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"garden_records"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "harvest_log":
        return harvest_log(settings, args, today)
    if action == "harvest_totals":
        return harvest_totals(settings, args, today)
    if action == "seed_add":
        return seed_add(settings, args)
    if action == "seed_list":
        return seed_list(settings, today)
    if action == "seed_remove":
        return seed_remove(settings, args.get("seed"), bool(args.get("confirmed")))
    if action == "bed_set":
        return bed_set(settings, args)
    if action == "bed_show":
        return bed_show(settings, args.get("bed"))
    if action == "bed_remove":
        return bed_remove(settings, args.get("bed"), bool(args.get("confirmed")))
    raise ValueError(f"Unknown garden records action: {action}")
