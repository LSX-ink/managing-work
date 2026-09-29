"""UK garden guide from built-in tables: what to sow and plant by month, jobs this month, plant care cards, companion
planting, lawn care, compost do's and don'ts, and a frost warning from Open-Meteo's keyless forecast (a city only).

Guidance for a typical UK garden; the south of England is a couple of weeks ahead of the north.
"""

from datetime import date

import homestore as hs
import petsgarden_store as store
import screen
import webview_common as web
from config import Settings
from feeds import fetch_json
from petsgarden_data import (COMPANIONS, COMPOST_BAD, COMPOST_GOOD, COMPOST_TIPS, JOBS, LAWN, MONTHS, PLANTS, SOW)

ACTIONS = ["sow_calendar", "month_jobs", "plant_care", "companion", "lawn", "compost", "frost_warning"]
FORECAST = "https://api.open-meteo.com/v1/forecast"
STAGES = [("Sow indoors", 1), ("Sow outdoors", 2), ("Plant out", 3), ("Harvest", 4)]


def _month_range(months: tuple) -> str:
    return ", ".join(MONTHS[m - 1][:3] for m in sorted(months, key=lambda m: (m < 3, m))) or "none"


def sow_calendar(args: dict, today: date) -> screen.Shown:
    crop = hs.clean(args.get("plant")).lower()
    if crop:
        key = next((k for k in SOW if crop == k or crop in k or k in crop), None)
        if key is None:
            raise ValueError("I don't have that crop in my calendar. Ask for a month to see what I have.")
        row = SOW[key]
        rows = [[name, _month_range(row[i])] for name, i in STAGES if row[i]]
        card = screen.card("table", f"Growing {key}", f"petsgarden-crop-{key}", columns=["Stage", "Months"], rows=rows)
        return screen.Shown(f"{key.capitalize()}: " + "; ".join(f"{a.lower()} {b}" for a, b in rows) + f". {row[5]}", card)
    month = store.month_number(args.get("month"), today)
    kind = hs.clean(args.get("kind")).lower().rstrip("s")
    rows = []
    for name, row in SOW.items():
        if kind and row[0] != kind:
            continue
        todo = [label for label, i in STAGES if month in row[i]]
        if todo:
            rows.append([name.capitalize(), ", ".join(todo)])
    label = {"veg": "vegetables", "herb": "herbs", "flower": "flowers"}.get(kind, "veg, herbs and flowers")
    if not rows:
        said = f"Nothing much to sow or pick in {MONTHS[month - 1]} for {label}."
        return screen.Shown(said, screen.card("text", f"{MONTHS[month - 1]} sowing", "petsgarden-sow", text=said))
    sowing = [r[0] for r in rows if "Sow" in r[1]][:6]
    card = screen.card("table", f"What to sow in {MONTHS[month - 1]}", f"petsgarden-sow-{month}-{kind}",
                       columns=["Crop", "This month"], rows=rows,
                       buttons=[{"label": "Jobs this month", "say": f"What should I do in the garden in {MONTHS[month - 1]}?"}])
    return screen.Shown(f"{len(rows)} crops to sow, plant or pick in {MONTHS[month - 1]}"
                        + (f". To sow: {', '.join(sowing)}." if sowing else "."), card)


def month_jobs(month_arg, today: date) -> screen.Shown:
    month = store.month_number(month_arg, today)
    items = [{"label": job} for job in JOBS[month]]
    card = screen.card("list", f"Garden jobs for {MONTHS[month - 1]}", f"petsgarden-jobs-{month}", items=items, checks=True,
                       buttons=[{"label": "What to sow", "say": f"What can I sow in {MONTHS[month - 1]}?"}])
    return screen.Shown(f"In {MONTHS[month - 1]}: " + "; ".join(JOBS[month][:3]) + ".", card)


def plant_care(name) -> screen.Shown:
    text = hs.clean(name).lower()
    if not text:
        items = [{"label": f"{p.title()} ({row[0]})", "say": f"How do I care for a {p}?"} for p, row in PLANTS.items()]
        return screen.Shown(f"I have care cards for {len(PLANTS)} plants; tap one.",
                            screen.card("list", "Plant care cards", "petsgarden-plants", items=items))
    key = next((k for k in PLANTS if text == k or text in k or k in text), None)
    if key is None:
        raise ValueError("I don't have a care card for that plant. Ask for the list to see which I know.")
    kind, water, light, feed, tip = PLANTS[key]
    rows = [["Water", water], ["Light", light], ["Feed", feed], ["Tip", tip]]
    card = screen.card("table", f"{key.title()} care", f"petsgarden-plant-{key}", columns=["", f"{key.title()} ({kind})"], rows=rows)
    return screen.Shown(f"{key.capitalize()}: water {water.lower()}. Light: {light.lower()}. Feed: {feed.lower()}. {tip}", card)


def companion(name) -> screen.Shown:
    text = hs.clean(name).lower()
    if not text:
        rows = [[k.title(), ", ".join(good[:3]), ", ".join(bad[:2])] for k, (good, bad) in COMPANIONS.items()]
        return screen.Shown("Here's the companion planting table.", screen.card(
            "table", "Companion planting", "petsgarden-companions", columns=["Plant", "Grows well with", "Keep apart"], rows=rows))
    key = next((k for k in COMPANIONS if text == k or text in k or k.rstrip("s") in text), None)
    if key is None:
        raise ValueError("I don't have that one in my companion table. Ask for the whole table to see which I know.")
    good, bad = COMPANIONS[key]
    card = screen.card("table", f"Planting with {key}", f"petsgarden-companion-{key}", columns=["", key.title()],
                       rows=[["Good neighbours", ", ".join(good)], ["Keep apart", ", ".join(bad)]])
    return screen.Shown(f"{key.capitalize()} grows well with {', '.join(good)}. Keep it away from {', '.join(bad)}.", card)


def lawn(month_arg, today: date) -> screen.Shown:
    month = store.month_number(month_arg, today)
    rows = [[MONTHS[m - 1], LAWN[m] + (" <- now" if m == month else "")] for m in range(1, 13)]
    return screen.Shown(f"Lawn care in {MONTHS[month - 1]}: {LAWN[month]}",
                        screen.card("table", "Lawn care calendar", "petsgarden-lawn", columns=["Month", "Job"], rows=rows))


def compost() -> screen.Shown:
    items = [{"label": f"Yes: {x}", "done": True} for group in COMPOST_GOOD.values() for x in group]
    items += [{"label": f"No: {x}"} for x in COMPOST_BAD] + [{"label": f"Tip: {t}"} for t in COMPOST_TIPS]
    good = ", ".join(x.lower() for x in COMPOST_GOOD["Greens (wet, nitrogen)"][:3])
    return screen.Shown(f"Compost loves {good}, and dry browns like cardboard and leaves. Keep out meat, dairy and "
                        "cooked food. The full list is on the screen.", screen.card("list", "Compost do's and don'ts", "petsgarden-compost", items=items))


async def frost_warning(http, settings: Settings, city) -> screen.Shown:
    place = await web.geocode(http, hs.clean(city) or settings.city)
    body = await fetch_json(http, FORECAST, "forecast", {"latitude": place["lat"], "longitude": place["lon"],
                                                         "daily": "temperature_2m_min", "timezone": "auto", "forecast_days": 7})
    daily = (body.get("daily") or {}) if isinstance(body, dict) else {}
    days, lows = daily.get("time") or [], daily.get("temperature_2m_min") or []
    if not days or len(days) != len(lows):
        raise ValueError("The forecast didn't come back properly. Try again in a bit.")
    rows = [[hs.spoken(date.fromisoformat(d)), f"{low:g} C", _frost_advice(low)] for d, low in zip(days, lows)]
    cold = [r[0] for r, low in zip(rows, lows) if low <= 0]
    name = place["name"]
    if cold:
        said = f"Frost warning for {name}: expect frost on {cold[0]}" + (f" and {len(cold) - 1} more night(s)" if len(cold) > 1 else "") + \
               ". Cover tender plants with fleece and bring pots in."
    else:
        said = f"No frost forecast for {name} in the next week; the coldest night is {min(lows):g} degrees."
    return screen.Shown(said, screen.card("table", f"Frost check: {name}", "petsgarden-frost",
                                          columns=["Night", "Low", "Advice"], rows=rows))


def _frost_advice(low: float) -> str:
    if low <= -2:
        return "Hard frost: protect everything tender"
    if low <= 0:
        return "Frost: cover tender plants"
    if low <= 3:
        return "Ground frost possible: be careful"
    return "Safe"


def tool_definitions() -> list[dict]:
    return [{
        "name": "garden_guide",
        "description": "UK garden guide from built-in tables. action: sow_calendar = what to sow, plant out or "
                       "harvest in a month (month, kind veg, herb or flower) or one crop's months (plant); "
                       "month_jobs = what to do in the garden this month; plant_care = water, light and feed card for "
                       "about 30 houseplants and garden plants (leave plant out for the list); companion = companion "
                       "planting (what to grow with or away from a veg); lawn = lawn care calendar; compost = compost "
                       "do's and don'ts; frost_warning = will there be a frost this week, from the forecast for a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "month": {"type": "string", "description": "Month name or 1 to 12; default this month."},
                "kind": {"type": "string", "enum": ["veg", "herb", "flower"]},
                "plant": {"type": "string", "description": "A plant or crop, e.g. tomatoes or monstera."},
                "city": {"type": "string", "description": "frost_warning: default the home city."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"garden_guide"}


async def run_tool(name: str, args: dict, settings: Settings, http, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "sow_calendar":
        return sow_calendar(args, today)
    if action == "month_jobs":
        return month_jobs(args.get("month"), today)
    if action == "plant_care":
        return plant_care(args.get("plant"))
    if action == "companion":
        return companion(args.get("plant"))
    if action == "lawn":
        return lawn(args.get("month"), today)
    if action == "compost":
        return compost()
    if action == "frost_warning":
        return await frost_warning(http, settings, args.get("city"))
    raise ValueError(f"Unknown garden action: {action}")
