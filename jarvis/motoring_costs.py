"""Motoring sums and logs: trip fuel cost, EV charging cost, business mileage at the HMRC rates with a CSV export,
splitting a car-share, speed / distance / time, and a commute log with average journey time charts.

Mileage and commute entries live in motoring.json in the memory folder; the CSV export goes to Personal.
"""

import csv
import io
from datetime import date

import homestore as hs
import memory
import motoring_store as ms
import screen
from config import Settings

LITRES_PER_GALLON = 4.54609
KM_PER_MILE = 1.609344
HMRC = {"car": (45, 25), "van": (45, 25), "motorbike": (24, 24), "bicycle": (20, 20)}
HMRC_LIMIT = 10_000
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
ACTIONS = ["trip_cost", "ev_cost", "mileage_add", "mileage_show", "mileage_export", "split_cost", "journey_calc",
           "commute_add", "commute_chart"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "motoring_costs",
        "description": "Driving sums and logs in pounds and miles. trip_cost (petrol or diesel for a journey: "
                       "distance, mpg, pence per litre; uses the saved car's mpg if none given), ev_cost (electric "
                       "charging cost by miles or kWh), mileage_add / mileage_show / mileage_export (work mileage "
                       "claim at HMRC 45p then 25p a mile, table, CSV saved to Personal), split_cost (car-share or "
                       "petrol split between people), journey_calc (speed, distance and time: give two, get the "
                       "third), commute_add / commute_chart (journey time log and average journey time chart).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "distance": {"type": "number", "description": "Miles, or km if unit is km."},
                "unit": {"type": "string", "enum": ["miles", "km"]},
                "round_trip": {"type": "boolean", "description": "Double the distance."},
                "mpg": {"type": "number", "description": "Miles per UK gallon."},
                "pence_per_litre": {"type": "number"},
                "miles_per_kwh": {"type": "number", "description": "EV efficiency; 3.5 if unknown."},
                "kwh": {"type": "number", "description": "Energy added, if known."},
                "pence_per_kwh": {"type": "number"},
                "battery_kwh": {"type": "number", "description": "Battery size for a percent-to-percent charge."},
                "from_percent": {"type": "number"}, "to_percent": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD, default today."},
                "from": text, "to": text, "purpose": text,
                "vehicle": {"type": "string", "enum": list(HMRC)},
                "tax_year": {"type": "integer", "description": "Year the tax year starts, e.g. 2026 for 6 April 2026."},
                "people": {"type": "integer", "description": "split_cost: how many share, driver included."},
                "total": {"type": "number", "description": "split_cost: total pounds."},
                "pence_per_mile": {"type": "number", "description": "split_cost: if no total."},
                "speed_mph": {"type": "number"},
                "minutes": {"type": "number", "description": "Journey time in minutes."},
                "direction": {"type": "string", "enum": ["to work", "home"]},
                "view": {"type": "string", "enum": ["weekday", "recent"]},
                "note": text,
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"motoring_costs"}


def run_tool(name: str, args: dict, settings: Settings):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    return globals()[action](settings, args)


def _miles(args: dict, what: str = "distance") -> float:
    n = ms.positive(args.get(what), what, 100_000)
    return n / KM_PER_MILE if args.get("unit") == "km" else n


# ---- fuel and charging -------------------------------------------------------------------

def trip_cost(settings: Settings, args: dict) -> screen.Shown:
    miles = _miles(args) * (2 if args.get("round_trip") else 1)
    mpg = ms.positive(args.get("mpg") or ms.car_mpg(settings), "mpg (say your car's mpg)", 500)
    price = ms.positive(args.get("pence_per_litre"), "pence per litre", 1000)
    litres = miles / mpg * LITRES_PER_GALLON
    cost = litres * price / 100
    rows = [["Distance", f"{miles:,.1f} miles"], ["Fuel", f"{litres:.1f} litres at {mpg:g} mpg"],
            ["Cost", f"{cost:.2f} pounds"], ["Per mile", f"{cost / miles * 100:.1f}p"]]
    return screen.Shown(f"{miles:,.0f} miles costs about {cost:.2f} pounds in fuel.",
                        _card("Trip cost", "motoring-trip", rows))


def _card(title: str, card_id: str, rows: list[list]) -> dict:
    return screen.card("table", title, card_id, columns=["", ""], rows=rows)


def ev_cost(settings: Settings, args: dict) -> screen.Shown:
    price = ms.positive(args.get("pence_per_kwh"), "pence per kWh", 1000)
    if args.get("kwh") is not None:
        kwh, how = ms.positive(args["kwh"], "kWh", 500), "kWh added"
        miles = kwh * float(args.get("miles_per_kwh") or 3.5)
    elif args.get("battery_kwh") is not None:
        low, high = ms.number(args.get("from_percent", 0), "start percent", 0, 100), ms.number(args.get("to_percent", 100), "end percent", 0, 100)
        if high <= low:
            raise ValueError("The end percent must be higher than the start.")
        kwh = ms.positive(args["battery_kwh"], "battery size", 500) * (high - low) / 100
        how, miles = f"{low:g}% to {high:g}%", kwh * float(args.get("miles_per_kwh") or 3.5)
    else:
        miles = _miles(args)
        kwh, how = miles / ms.positive(args.get("miles_per_kwh") or 3.5, "efficiency", 20), f"{miles:,.0f} miles"
    cost = kwh * price / 100
    rows = [["Charge", f"{kwh:.1f} kWh ({how})"], ["Cost", f"{cost:.2f} pounds"],
            ["Range gained", f"about {miles:,.0f} miles"], ["Per mile", f"{cost / miles * 100:.1f}p"]]
    return screen.Shown(f"{kwh:.1f} kWh costs about {cost:.2f} pounds.", _card("EV charging cost", "motoring-ev", rows))


# ---- work mileage ------------------------------------------------------------------------

def tax_year_of(day: date) -> int:
    return day.year if (day.month, day.day) >= (4, 6) else day.year - 1


def claims(entries: list[dict]) -> list[float]:
    """The HMRC amount in pounds for each entry, in date order: the first 10,000 miles a year are dearer."""
    totals: dict[tuple, float] = {}
    out = []
    for e in entries:
        first, after = HMRC[e.get("vehicle", "car")]
        key = (tax_year_of(date.fromisoformat(e["date"])), e.get("vehicle", "car"))
        done = totals.get(key, 0.0)
        cheap = max(0.0, min(e["miles"], HMRC_LIMIT - done))
        out.append((cheap * first + (e["miles"] - cheap) * after) / 100)
        totals[key] = done + e["miles"]
    return out


def mileage_add(settings: Settings, args: dict) -> str:
    day = hs.parse_day(args.get("date"))
    vehicle = args.get("vehicle") if args.get("vehicle") in HMRC else "car"
    entry = {"date": day.isoformat(), "miles": round(_miles(args), 1), "from": hs.clean(args.get("from"), 60),
             "to": hs.clean(args.get("to"), 60), "purpose": hs.clean(args.get("purpose"), 80), "vehicle": vehicle}
    data = ms.add(settings, "mileage", entry)
    year = tax_year_of(day)
    mine = _year_entries(data["mileage"], year)
    total = sum(e["miles"] for e in mine if e.get("vehicle", "car") == vehicle)
    return (f"Logged {entry['miles']:g} miles on {ms.short(day)}. That's {total:,.0f} {vehicle} miles and "
            f"{sum(claims(mine)):.2f} pounds to claim this tax year.")


def _year_entries(entries: list[dict], year: int) -> list[dict]:
    return sorted((e for e in entries if tax_year_of(date.fromisoformat(e["date"])) == year), key=lambda e: e["date"])


def _year(settings: Settings, args: dict) -> tuple[int, list[dict]]:
    year = int(args.get("tax_year") or tax_year_of(hs.today()))
    return year, _year_entries(ms.load(settings)["mileage"], year)


def mileage_show(settings: Settings, args: dict) -> screen.Shown | str:
    year, mine = _year(settings, args)
    if not mine:
        return f"No work mileage logged for the tax year from April {year}."
    amounts = claims(mine)
    rows = [[ms.short(date.fromisoformat(e["date"])), " to ".join(p for p in (e["from"], e["to"]) if p) or "-",
             e["purpose"], f"{e['miles']:g}", f"{a:.2f}"] for e, a in zip(mine, amounts)][-100:]
    miles = sum(e["miles"] for e in mine)
    rows.append(["Total", "", "", f"{miles:,.1f}", f"{sum(amounts):.2f}"])
    said = f"{miles:,.0f} work miles in {year}/{str(year + 1)[2:]}, worth {sum(amounts):.2f} pounds at HMRC rates."
    card = screen.card("table", f"Work mileage {year}/{str(year + 1)[2:]}", "motoring-mileage",
                       columns=["Date", "Journey", "Purpose", "Miles", "Claim (pounds)"], rows=rows,
                       buttons=[{"label": "Export CSV", "say": "Export my work mileage to a CSV file."}],
                       text="HMRC rates: 45p a mile for the first 10,000 in the tax year, then 25p.")
    return screen.Shown(said, card)


def mileage_export(settings: Settings, args: dict) -> screen.Shown | str:
    year, mine = _year(settings, args)
    if not mine:
        return f"There's no mileage to export for the tax year from April {year}."
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Date", "From", "To", "Purpose", "Vehicle", "Miles", "Claim GBP"])
    for e, a in zip(mine, claims(mine)):
        writer.writerow([e["date"], e["from"], e["to"], e["purpose"], e.get("vehicle", "car"), e["miles"], f"{a:.2f}"])
    path = memory.save_file(settings, "Personal", f"work-mileage-{year}-{year + 1}.csv", out.getvalue().encode("utf-8"))
    card = screen.file_card(settings, path)
    return screen.Shown(f"Saved your {year}/{str(year + 1)[2:]} mileage to {path.name} in the Personal folder.", card)


# ---- sharing and journeys ----------------------------------------------------------------

def split_cost(settings: Settings, args: dict) -> screen.Shown:
    people = int(ms.number(args.get("people"), "number of people", 1, 50))
    if args.get("total") is not None:
        total = ms.positive(args["total"], "total", 100_000)
    else:
        miles = _miles(args) * (2 if args.get("round_trip") else 1)
        total = miles * ms.positive(args.get("pence_per_mile"), "pence per mile", 1000) / 100
    share = total / people
    rows = [["Total", f"{total:.2f} pounds"], ["People", str(people)], ["Each", f"{share:.2f} pounds"]]
    return screen.Shown(f"{total:.2f} pounds between {people} is {share:.2f} pounds each.",
                        _card("Car-share split", "motoring-split", rows))


def journey_calc(settings: Settings, args: dict) -> screen.Shown:
    speed, minutes = args.get("speed_mph"), args.get("minutes")
    given = [x is not None for x in (args.get("distance"), speed, minutes)]
    if sum(given) != 2:
        raise ValueError("Give me two of distance, average speed and time.")
    if args.get("distance") is None:
        miles = ms.positive(speed, "speed", 300) * ms.positive(minutes, "time", 100_000) / 60
    else:
        miles = _miles(args)
        if minutes is None:
            minutes = miles / ms.positive(speed, "speed", 300) * 60
        else:
            speed = miles / ms.positive(minutes, "time", 100_000) * 60
    minutes, speed = float(minutes), float(speed)
    rows = [["Distance", f"{miles:,.1f} miles ({miles * KM_PER_MILE:,.1f} km)"], ["Average speed", f"{speed:.1f} mph"],
            ["Time", _hours(minutes)]]
    return screen.Shown(f"{miles:,.1f} miles at {speed:.0f} mph takes {_hours(minutes)}.",
                        _card("Speed, distance, time", "motoring-journey", rows))


def _hours(minutes: float) -> str:
    total = round(minutes)
    h, m = divmod(total, 60)
    return f"{h} h {m} min" if h else f"{m} min"


# ---- commute -----------------------------------------------------------------------------

def commute_add(settings: Settings, args: dict) -> str:
    minutes = ms.positive(args.get("minutes"), "journey time", 1000)
    day = hs.parse_day(args.get("date"))
    data = ms.add(settings, "commute", {"date": day.isoformat(), "minutes": minutes,
                                        "direction": args.get("direction") or "to work"})
    times = [e["minutes"] for e in data["commute"]]
    return f"Logged {minutes:g} minutes. Your average over {len(times)} journeys is {sum(times) / len(times):.0f} minutes."


def commute_chart(settings: Settings, args: dict) -> screen.Shown | str:
    log = ms.load(settings)["commute"]
    if not log:
        return "No commutes logged yet. Tell me how long each journey takes."
    times = [e["minutes"] for e in log]
    said = (f"Your commute averages {sum(times) / len(times):.0f} minutes; best {min(times):g}, worst {max(times):g}.")
    if args.get("view") == "recent":
        last = log[-30:]
        labels = [ms.short(date.fromisoformat(e["date"]))[:-5] for e in last]
        chart = {"type": "line", "labels": labels, "values": [e["minutes"] for e in last], "unit": "m"}
        title = "Recent commute times"
    else:
        by_day = {i: [] for i in range(7)}
        for e in log:
            by_day[date.fromisoformat(e["date"]).weekday()].append(e["minutes"])
        days = [i for i in range(7) if by_day[i]]
        chart = {"type": "bar", "labels": [DAYS[i] for i in days],
                 "values": [round(sum(by_day[i]) / len(by_day[i]), 1) for i in days], "unit": "m"}
        title = "Average commute by weekday"
    return screen.Shown(said, screen.card("chart", title, "motoring-commute", chart=chart))
