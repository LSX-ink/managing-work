"""Meters and the car: gas, electric and water meter readings, a fuel log with mpg, and where I parked.

Readings, fill-ups and the parking note live in household-*.json in the memory folder. Fuel is in litres and
miles (UK gallons for mpg); money is in the user's own currency.
"""

from datetime import date, datetime, timedelta

import homestore as hs
import household_store as hh
import screen
from config import Settings

METERS, CAR, PARKING = "household-meters.json", "household-car.json", "household-parking.json"
METER_KINDS = ("electric", "gas", "water")
LITRES_PER_GALLON = 4.54609
DAYS_PER_MONTH = 30.44
MAX_READINGS = 500


# Energy and water meters

def _meters(settings: Settings) -> dict:
    found = hs.load(settings, METERS, {})
    return {"readings": {k: v for k, v in found.get("readings", {}).items() if isinstance(v, list)},
            "prices": {k: v for k, v in found.get("prices", {}).items() if isinstance(v, (int, float))}}


def _kind(meter) -> str:
    meter = hs.clean(meter).lower()
    meter = "electric" if meter.startswith("elec") else meter
    if meter not in METER_KINDS:
        raise ValueError("Which meter: electric, gas or water?")
    return meter


def meter_read(settings: Settings, meter, reading, day=None) -> str:
    meter = _kind(meter)
    value = hs.number(reading, "meter reading", 0, 100_000_000)
    when = hs.parse_day(day).isoformat()
    data = _meters(settings)
    found = [r for r in data["readings"].get(meter, []) if r["date"] != when]
    before = [r for r in found if r["date"] < when]
    after = [r for r in found if r["date"] > when]
    if before and value < before[-1]["value"] or after and value > after[0]["value"]:
        raise ValueError("That reading doesn't fit between the others; meters only go up.")
    found = sorted(found + [{"date": when, "value": value}], key=lambda r: r["date"])[-MAX_READINGS:]
    data["readings"][meter] = found
    hs.save(settings, METERS, data)
    periods = _periods(found)
    if not periods:
        return f"Saved the {meter} reading of {value:g}. One more reading and I can work out your usage."
    last = periods[-1]
    return f"Saved the {meter} reading. Since {hs.spoken(last[0])} you've used {last[2]:g} units, " \
           f"{last[3]:.1f} a day."


def _periods(found: list[dict]) -> list[tuple[date, date, float, float]]:
    """(from, to, units used, units a day) between each pair of readings."""
    out = []
    for a, b in zip(found, found[1:]):
        start, end = date.fromisoformat(a["date"]), date.fromisoformat(b["date"])
        used = round(b["value"] - a["value"], 3)
        out.append((start, end, used, used / max(1, (end - start).days)))
    return out


def _per_day(found: list[dict]) -> float | None:
    """Average daily use over the last 90 days of readings (at least the last two)."""
    if len(found) < 2:
        return None
    last = found[-1]
    cut = (date.fromisoformat(last["date"]) - timedelta(days=90)).isoformat()
    start = next((r for r in found if r["date"] >= cut and r is not last), found[-2])
    days = max(1, (date.fromisoformat(last["date"]) - date.fromisoformat(start["date"])).days)
    return (last["value"] - start["value"]) / days


def meter_price(settings: Settings, meter, price) -> str:
    meter = _kind(meter)
    price = hs.number(price, "unit price", 0.0001, 100)
    data = _meters(settings)
    data["prices"][meter] = price
    hs.save(settings, METERS, data)
    return f"The {meter} unit price is {price:g} {settings.currency}."


def _cost(settings: Settings, data: dict, meter: str) -> str:
    per_day, price = _per_day(data["readings"].get(meter, [])), data["prices"].get(meter)
    if per_day is None:
        return f"I need two {meter} readings first."
    monthly = per_day * DAYS_PER_MONTH
    if price is None:
        return f"{meter.title()}: about {monthly:,.0f} units a month (tell me the unit price for a cost)."
    return f"{meter.title()}: about {monthly:,.0f} units, {hs.money(monthly * price, settings.currency)} a month."


def meter_usage(settings: Settings, meter) -> screen.Shown | str:
    meter = _kind(meter)
    data = _meters(settings)
    periods = _periods(data["readings"].get(meter, []))
    if not periods:
        return f"I need at least two {meter} readings to show usage."
    periods = periods[-40:]
    card = screen.card("chart", f"{meter.title()} use per day", f"household-meter-{meter}", text=_cost(settings, data, meter),
                       chart={"type": "line", "labels": [f"{p[1]:%d %b}" for p in periods],
                              "values": [round(p[3], 2) for p in periods], "unit": ""},
                       buttons=[{"label": "Monthly cost", "say": "What will my energy cost this month?"}])
    return screen.Shown(f"Your {meter} use is on the screen; lately {periods[-1][3]:.1f} units a day.", card)


def meter_cost(settings: Settings, meter=None) -> str:
    data = _meters(settings)
    kinds = [_kind(meter)] if meter else [k for k in METER_KINDS if len(data["readings"].get(k, [])) > 1]
    if not kinds:
        return "I need at least two readings from a meter to estimate the cost."
    return " ".join(_cost(settings, data, k) for k in kinds)


# Car fuel log

def _car(settings: Settings, label) -> tuple[str, dict]:
    found = hh.rows(settings, CAR)
    k = hs.find(found, label or "car") or (next(iter(found)) if len(found) == 1 and not label else None)
    if k is None:
        raise ValueError("I haven't got any fill-ups logged for that car yet.")
    return k, found


def car_fill(settings: Settings, label, miles, litres, cost, day=None) -> str:
    label = hs.clean(label, 40) or "car"
    miles = hs.number(miles, "mileage", 0, 2_000_000)
    litres = hs.number(litres, "litres", 0.1, 500)
    cost = round(hs.number(cost or 0, "cost"), 2)
    found = hh.rows(settings, CAR)
    k = hs.find(found, label) or label
    fills = found.get(k) or []
    if fills and miles <= fills[-1]["miles"]:
        raise ValueError(f"The last fill-up was at {fills[-1]['miles']:g} miles; the mileage should be higher.")
    fills = (fills + [{"date": hs.parse_day(day).isoformat(), "miles": miles, "litres": litres, "cost": cost}])[-MAX_READINGS:]
    hh.put(settings, CAR, found, k, fills)
    if len(fills) < 2:
        return f"Logged the first fill-up for the {k}. From the next one I can work out mpg; fill to full each time."
    return f"Logged it: {_mpg(fills[-2], fills[-1]):.1f} mpg since the last fill-up."


def _mpg(before: dict, after: dict) -> float:
    return (after["miles"] - before["miles"]) / (after["litres"] / LITRES_PER_GALLON)


def car_report(settings: Settings, label=None) -> screen.Shown | str:
    k, found = _car(settings, label)
    fills = found[k]
    if len(fills) < 2:
        return f"Only one fill-up for the {k} so far; I need two for mpg."
    mpgs = [_mpg(a, b) for a, b in zip(fills, fills[1:])]
    miles = fills[-1]["miles"] - fills[0]["miles"]
    litres = sum(f["litres"] for f in fills[1:])
    cost = sum(f["cost"] for f in fills[1:])
    cur = settings.currency
    average = miles / (litres / LITRES_PER_GALLON)
    per_mile = f"{cost / miles:.3f} {cur} a mile" if cost else "no costs logged"
    card = screen.card("chart", f"{k.title()} mpg per fill-up", f"household-car-{k}",
                       text=f"Average {average:.1f} mpg over {miles:,.0f} miles; {per_mile}; "
                            f"fuel {hs.money(sum(f['cost'] for f in fills), cur)} in all.",
                       chart={"type": "line", "labels": [f"{date.fromisoformat(f['date']):%d %b}" for f in fills[1:]][-60:],
                              "values": [round(m, 1) for m in mpgs][-60:], "unit": ""})
    return screen.Shown(f"The {k} averages {average:.1f} mpg, last fill {mpgs[-1]:.1f}; {per_mile}.", card)


# Where I parked

def park_save(settings: Settings, note) -> str:
    note = hs.need(note, "parking spot", 200)
    hs.save(settings, PARKING, {"note": note, "at": hs.now().isoformat(timespec="minutes"), "cleared": False})
    return f"Got it: {note}."


def _ago(then: datetime) -> str:
    minutes = int((hs.now() - then).total_seconds() // 60)
    if minutes < 60:
        return hs.plural(max(0, minutes), "minute")
    if minutes < 48 * 60:
        return hs.plural(minutes // 60, "hour")
    return hs.plural(minutes // 1440, "day")


def park_where(settings: Settings) -> screen.Shown | str:
    spot = hs.load(settings, PARKING, {})
    if not spot.get("note"):
        return "You haven't told me where you parked."
    then = datetime.fromisoformat(spot["at"])
    when = f"{_ago(then)} ago, at {then:%H:%M}" + ("" if then.date() == hs.today() else f" on {hs.spoken(then.date())}")
    if spot.get("cleared"):
        return f"You've already picked the car up. Last time you parked at {spot['note']}, {when}."
    card = screen.card("text", "Where I parked", "household-parking", text=f"{spot['note']}\n\nParked {when}.",
                       buttons=[{"label": "Got the car", "say": "I've got the car, clear where I parked."}])
    return screen.Shown(f"You parked at {spot['note']}, {when}.", card)


def park_clear(settings: Settings) -> screen.Shown | str:
    spot = hs.load(settings, PARKING, {})
    if not spot.get("note") or spot.get("cleared"):
        return "There's no parking spot saved."
    spot["cleared"] = True
    hs.save(settings, PARKING, spot)
    return screen.Shown("Cleared where you parked.", {"kind": "close", "all": False, "title": "Where I parked"})


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "household_meters",
        "description": "Gas, electric and water meter readings, car fuel log, and where I parked. meter_read "
                       "(meter, amount = reading, optional date), meter_usage chart of units a day between readings, "
                       "meter_price (meter, amount = price per unit, e.g. 0.245), meter_cost estimated monthly "
                       "units and cost (meter optional for all). car_fill a fill-up to full (miles = odometer, "
                       "litres, amount = cost, optional name of car, date), car_report mpg per fill chart, average "
                       "mpg and cost per mile. park_save (note: level, bay, street), park_where ('where did I "
                       "park?'), park_clear once back at the car.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "meter_read", "meter_usage", "meter_price", "meter_cost", "car_fill", "car_report",
                    "park_save", "park_where", "park_clear"]},
                "meter": {"type": "string", "enum": list(METER_KINDS)},
                "amount": {"type": "number"},
                "miles": {"type": "number", "description": "Odometer mileage at the fill-up."},
                "litres": {"type": "number"},
                "name": text,
                "note": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"household_meters"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    actions = {
        "meter_read": lambda: meter_read(settings, a("meter"), a("amount"), a("date")),
        "meter_usage": lambda: meter_usage(settings, a("meter")),
        "meter_price": lambda: meter_price(settings, a("meter"), a("amount")),
        "meter_cost": lambda: meter_cost(settings, a("meter")),
        "car_fill": lambda: car_fill(settings, a("name"), a("miles"), a("litres"), a("amount"), a("date")),
        "car_report": lambda: car_report(settings, a("name")),
        "park_save": lambda: park_save(settings, a("note") or a("name")),
        "park_where": lambda: park_where(settings),
        "park_clear": lambda: park_clear(settings),
    }
    if a("action") not in actions:
        raise ValueError("Unknown household meters action.")
    return actions[a("action")]()
