"""Trips: where and when with a countdown, a day-by-day itinerary, bookings (flights, hotels, trains) with their
reference numbers, a souvenir and gift list, a trip journal, the destination's forecast and a one-window summary.

Everything stays in travel-trips.json in the memory folder, and journals are Markdown files in the Travel folder.
Only the destination's name goes online, to Open-Meteo's keyless geocoder and forecast.
"""

import re
from datetime import date, timedelta

import httpx

import homestore as hs
import memory
import screen
import travel_papers
import travel_store as ts
from config import Settings
from feeds import fetch_json

GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
FORECAST_DAYS = 16
BOOKING_KINDS = ["flight", "hotel", "train", "car", "ferry", "event", "other"]
JOURNAL_FOLDER = "Travel"

ACTIONS = ["trip_add", "trip_list", "trip_remove", "plan_add", "plan_show", "plan_move", "plan_remove",
           "booking_add", "booking_find", "booking_list", "booking_remove", "gift_add", "gift_tick", "gift_list",
           "journal_write", "journal_read", "weather", "summary"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "travel_trips",
        "description": "Holidays and trips. trip_add (destination, start, end dates; optional name, country), "
                       "trip_list (countdown in days), trip_remove; itinerary: plan_add (day, time, what, where), "
                       "plan_show (a day's plan or the whole trip), plan_move / plan_remove by number; bookings: "
                       "booking_add (flight, hotel, train... with reference number, day, time, address), "
                       "booking_find ('what's my flight number?', 'which hotel?'), booking_list, booking_remove; "
                       "souvenirs and gifts: gift_add, gift_tick, gift_list; trip journal: journal_write, "
                       "journal_read; weather (forecast for the trip dates); summary (everything about a trip). "
                       "trip defaults to the next trip. Removing needs confirmed true, set only after the user "
                       "confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "trip": {"type": "string", "description": "Trip name or destination; default the next trip."},
                "name": {"type": "string", "description": "trip_add: a name for the trip, e.g. 'Spain 2026'."},
                "destination": {"type": "string", "description": "City or place, e.g. 'Barcelona'."},
                "country": text,
                "start": {"type": "string", "description": "YYYY-MM-DD."},
                "end": {"type": "string", "description": "YYYY-MM-DD."},
                "day": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'tomorrow'."},
                "time": {"type": "string", "description": "HH:MM, 24-hour."},
                "what": text,
                "where": text,
                "kind": {"type": "string", "enum": BOOKING_KINDS},
                "ref": {"type": "string", "description": "Booking reference or flight/train number."},
                "address": text,
                "notes": text,
                "query": {"type": "string", "description": "booking_find: words to look for."},
                "number": {"type": "integer", "description": "Item number from the list."},
                "who": {"type": "string", "description": "gift_add: who it's for."},
                "items": {"type": "array", "items": text, "description": "gift_add: gifts or souvenirs."},
                "item": {"type": "string", "description": "gift_tick: the gift."},
                "text": {"type": "string", "description": "journal_write: the entry."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"travel_trips"}


# ---- trips -------------------------------------------------------------------------------

def trip_add(settings: Settings, args: dict) -> str:
    found = ts.trips(settings)
    destination = hs.need(args.get("destination"), "destination", 60)
    start = hs.parse_day(args.get("start"))
    end = hs.parse_day(args.get("end") or args.get("start"))
    if end < start:
        raise ValueError("The trip ends before it starts; check the dates.")
    name = memory.safe_name(hs.clean(args.get("name"), 50) or f"{destination} {start.year}", "trip name")
    key = next((k for k in found if k.lower() == name.lower()), name)
    if key not in found and len(found) >= ts.MAX_TRIPS:
        raise ValueError("That's a lot of trips; remove an old one first.")
    trip = found.get(key, {"plan": [], "bookings": [], "gifts": []})
    trip.update(name=key, destination=destination, country=hs.clean(args.get("country"), 40) or trip.get("country", ""),
                start=start.isoformat(), end=end.isoformat())
    found[key] = trip
    ts.save(settings, found)
    return f"Saved {key}: {destination}, {hs.spoken(start)} to {hs.spoken(end)}. It {ts.countdown(trip)}."


def trip_list(settings: Settings) -> screen.Shown:
    found = ts.trips(settings)
    if not found:
        return screen.Shown("You haven't got any trips yet.", screen.card("text", "Trips", "travel-trips",
                                                                          text="No trips yet."))
    rows, items = [], []
    for k, t in sorted(found.items(), key=lambda kv: kv[1]["start"]):
        start, end = ts.days(t)
        rows.append([k, t["destination"], f"{start:%d %b} to {end:%d %b %Y}", ts.countdown(t)])
    coming = [r for r in rows if r[3].startswith(("starts", "is on"))]
    said = f"{coming[0][0]} {coming[0][3]}." if coming else "No trips coming up."
    buttons = [{"label": r[0][:40], "say": f"Show the summary of my {r[0]} trip."} for r in coming[:4]]
    return screen.Shown(f"{len(rows)} trips. {said}", screen.card(
        "table", "Trips", "travel-trips", columns=["Trip", "Where", "When", "Countdown"], rows=rows,
        buttons=buttons))


def trip_remove(settings: Settings, args: dict) -> str:
    found = ts.trips(settings)
    k = ts.pick(found, args.get("trip"))
    if not args.get("confirmed"):
        return f"Ask the user to confirm deleting the {k} trip with its plan and bookings, then call again with confirmed true."
    del found[k]
    ts.save(settings, found)
    return f"Deleted the {k} trip."


# ---- itinerary ---------------------------------------------------------------------------

def _time(value) -> str:
    text = hs.clean(value, 5)
    if not text:
        return ""
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?", text)
    if not m or int(m.group(1)) > 23 or int(m.group(2) or 0) > 59:
        raise ValueError("Give the time as HH:MM, e.g. 09:30.")
    return f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"


def _trip(settings: Settings, args: dict) -> tuple[dict, str, dict]:
    found = ts.trips(settings)
    k = ts.pick(found, args.get("trip"))
    trip = found[k]
    for field in ("plan", "bookings", "gifts"):
        trip.setdefault(field, [])
    return found, k, trip


def _in_trip(trip: dict, value) -> date:
    start, end = ts.days(trip)
    day = hs.parse_day(value, start) if hs.clean(value) else start
    if not start - timedelta(days=3) <= day <= end + timedelta(days=3):
        raise ValueError(f"That day isn't during the trip ({start:%d %b} to {end:%d %b}).")
    return day


def plan_add(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    if len(trip["plan"]) >= ts.MAX_ITEMS:
        raise ValueError("That itinerary is full.")
    day = _in_trip(trip, args.get("day"))
    item = {"id": ts.next_id(trip["plan"]), "day": day.isoformat(), "time": _time(args.get("time")),
            "what": hs.need(args.get("what"), "plan", 120), "where": hs.clean(args.get("where"), 100)}
    trip["plan"].append(item)
    ts.save(settings, found)
    at = f" at {item['time']}" if item["time"] else ""
    return f"Added {item['what']} on {hs.spoken(day)}{at} to the {k} plan (number {item['id']})."


def _ordered(items: list) -> list:
    return sorted(items, key=lambda i: (i.get("day", ""), i.get("time") or "99"))


def plan_show(settings: Settings, args: dict) -> screen.Shown:
    _, k, trip = _trip(settings, args)
    items = _ordered(trip["plan"])
    if hs.clean(args.get("day")):
        day = _in_trip(trip, args.get("day"))
        items = [i for i in items if i["day"] == day.isoformat()]
        rows = [[str(i["id"]), i["time"] or "any time", i["what"], i["where"]] for i in items]
        title, columns = f"{k}: {hs.spoken(day)}", ["#", "Time", "What", "Where"]
        said = f"{len(rows)} things planned on {hs.spoken(day)}." if rows else f"Nothing planned on {hs.spoken(day)}."
    else:
        rows = [[str(i["id"]), f"{date.fromisoformat(i['day']):%a %d %b}", i["time"] or "", i["what"], i["where"]]
                for i in items]
        title, columns = f"{k} itinerary", ["#", "Day", "Time", "What", "Where"]
        said = f"{len(rows)} things on the {k} plan." if rows else f"Nothing planned for {k} yet."
    start, end = ts.days(trip)
    buttons = [{"label": f"{start + timedelta(days=n):%a %d}", "say": f"Show my {k} plan for "
                f"{(start + timedelta(days=n)).isoformat()}."} for n in range(min(6, (end - start).days + 1))]
    return screen.Shown(said, screen.card("table", title, f"travel-plan-{k}", columns=columns, rows=rows,
                                          buttons=buttons))


def plan_move(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    item = ts.by_id(trip["plan"], args.get("number"), "plan item")
    if not hs.clean(args.get("day")) and not hs.clean(args.get("time")):
        raise ValueError("Move it to which day or time?")
    if hs.clean(args.get("day")):
        item["day"] = _in_trip(trip, args.get("day")).isoformat()
    if hs.clean(args.get("time")):
        item["time"] = _time(args.get("time"))
    ts.save(settings, found)
    at = f" at {item['time']}" if item["time"] else ""
    return f"Moved {item['what']} to {hs.spoken(date.fromisoformat(item['day']))}{at}."


def plan_remove(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    item = ts.by_id(trip["plan"], args.get("number"), "plan item")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {item['what']} from the plan, then call again with confirmed true."
    trip["plan"].remove(item)
    ts.save(settings, found)
    return f"Removed {item['what']} from the {k} plan."


# ---- bookings ----------------------------------------------------------------------------

def booking_add(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    if len(trip["bookings"]) >= ts.MAX_ITEMS:
        raise ValueError("That's a lot of bookings; remove an old one first.")
    kind = args.get("kind") if args.get("kind") in BOOKING_KINDS else "other"
    item = {"id": ts.next_id(trip["bookings"]), "kind": kind, "ref": hs.clean(args.get("ref"), 40),
            "what": hs.clean(args.get("what"), 120), "day": _in_trip(trip, args.get("day")).isoformat(),
            "time": _time(args.get("time")), "address": hs.clean(args.get("address"), 160),
            "notes": hs.clean(args.get("notes"), 200)}
    if not item["ref"] and not item["what"]:
        raise ValueError("What's the booking? Give a reference number or what it is.")
    trip["bookings"].append(item)
    ts.save(settings, found)
    return f"Saved the {kind} booking {_booking_words(item)} for {k}."


def _booking_words(b: dict) -> str:
    day = date.fromisoformat(b["day"])
    parts = [b["what"], f"reference {b['ref']}" if b["ref"] else "", f"on {hs.spoken(day)}",
             f"at {b['time']}" if b["time"] else "", f"at {b['address']}" if b["address"] else ""]
    return ", ".join(p for p in parts if p)


def booking_find(settings: Settings, args: dict) -> str:
    _, k, trip = _trip(settings, args)
    words = hs.clean(args.get("query")).lower()
    hits = [b for b in _ordered(trip["bookings"])
            if (not args.get("kind") or b["kind"] == args["kind"])
            and (not words or words in " ".join(str(v) for v in b.values()).lower())]
    if not hits:
        return f"I haven't got a matching booking for {k}."
    lines = [f"{b['kind'].title()}: {_booking_words(b)}." for b in hits[:4]]
    notes = [f"Note: {b['notes']}." for b in hits[:1] if b["notes"]]
    return " ".join(lines + notes)


def booking_list(settings: Settings, args: dict) -> screen.Shown:
    _, k, trip = _trip(settings, args)
    rows = [[str(b["id"]), b["kind"].title(), b["what"], b["ref"],
             f"{date.fromisoformat(b['day']):%a %d %b} {b['time']}".strip(), b["address"]]
            for b in _ordered(trip["bookings"])]
    said = f"{len(rows)} bookings for {k}." if rows else f"No bookings saved for {k} yet."
    return screen.Shown(said, screen.card("table", f"{k} bookings", f"travel-bookings-{k}",
                                          columns=["#", "Type", "What", "Ref", "When", "Address"], rows=rows))


def booking_remove(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    item = ts.by_id(trip["bookings"], args.get("number"), "booking")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing the {item['kind']} booking {item['ref'] or item['what']}, " \
               "then call again with confirmed true."
    trip["bookings"].remove(item)
    ts.save(settings, found)
    return f"Removed the {item['kind']} booking {item['ref'] or item['what']}."


# ---- gifts -------------------------------------------------------------------------------

def gift_add(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    who = hs.clean(args.get("who"), 40)
    have = {g["what"].lower() for g in trip["gifts"]}
    added = []
    for what in args.get("items") or [args.get("what")]:
        what = hs.clean(what, 80)
        if what and what.lower() not in have and len(trip["gifts"]) < ts.MAX_ITEMS:
            trip["gifts"].append({"what": what, "who": who, "done": False})
            have.add(what.lower())
            added.append(what)
    if not added:
        raise ValueError("Which gifts or souvenirs?")
    ts.save(settings, found)
    return f"Added {', '.join(added)}{' for ' + who if who else ''} to the {k} gift list."


def gift_tick(settings: Settings, args: dict) -> str:
    found, k, trip = _trip(settings, args)
    name = hs.clean(args.get("item") or args.get("what")).lower()
    hit = next((g for g in trip["gifts"] if g["what"].lower() == name), None) or next(
        (g for g in trip["gifts"] if name and name in g["what"].lower()), None)
    if not hit:
        raise ValueError(f"{hs.clean(args.get('item')) or 'That'} isn't on the {k} gift list.")
    hit["done"] = True
    ts.save(settings, found)
    left = sum(1 for g in trip["gifts"] if not g["done"])
    return f"Got {hit['what']}. {left} left to buy."


def gift_list(settings: Settings, args: dict) -> screen.Shown:
    _, k, trip = _trip(settings, args)
    items = [{"label": f"{g['what']}{' for ' + g['who'] if g['who'] else ''}", "done": g["done"],
              "say": f"Tick {g['what']} off my {k} gift list."} for g in trip["gifts"]]
    left = sum(1 for g in trip["gifts"] if not g["done"])
    return screen.Shown(f"{left} of {len(items)} gifts still to get.", screen.card(
        "list", f"{k} gifts and souvenirs", f"travel-gifts-{k}", items=items, checks=True))


# ---- journal -----------------------------------------------------------------------------

def journal_folder(settings: Settings):
    try:
        return memory.folder(settings, JOURNAL_FOLDER)
    except ValueError:
        return memory.create_folder(settings, "", JOURNAL_FOLDER)


def journal_path(settings: Settings, trip: str):
    return journal_folder(settings) / f"{memory.safe_name(trip, 'trip name')} journal.md"


def journal_write(settings: Settings, args: dict) -> str:
    _, k, trip = _trip(settings, args)
    text = hs.need(args.get("text"), "journal entry", 5000)
    day = hs.parse_day(args.get("day"))
    path = journal_path(settings, k)
    head = "" if path.exists() else f"# {k} journal\n\n{trip['destination']}, {trip['start']} to {trip['end']}\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{head}\n## {hs.spoken(day)} {day.year}\n\n{text}\n")
    return f"Saved to your {k} journal in the {JOURNAL_FOLDER} folder."


def journal_read(settings: Settings, args: dict) -> screen.Shown:
    _, k, _trip_data = _trip(settings, args)
    path = journal_path(settings, k)
    if not path.exists():
        raise ValueError(f"There's no journal for {k} yet.")
    text = path.read_text(encoding="utf-8")
    return screen.Shown(f"Your {k} journal is on the screen:\n{text[-3000:]}", screen.file_card(settings, path))


# ---- weather and summary -----------------------------------------------------------------

async def forecast(http: httpx.AsyncClient, trip: dict) -> dict | str:
    """{place, days: [(date, code, high, low, rain%)]} for the trip's dates, or a sentence saying why not."""
    start, end = ts.days(trip)
    today = hs.today()
    last = today + timedelta(days=FORECAST_DAYS - 1)
    if end < today:
        return "That trip is over, so there's no forecast."
    if start > last:
        return (f"The forecast only reaches {FORECAST_DAYS} days ahead; ask again from "
                f"{hs.spoken(start - timedelta(days=FORECAST_DAYS - 1))}.")
    geo = await fetch_json(http, GEOCODE, "place lookup", params={"name": trip["destination"], "count": 1,
                                                                 "language": "en", "format": "json"})
    places = geo.get("results") or []
    if not places:
        raise ValueError(f"I couldn't find {trip['destination']} on the map.")
    p = places[0]
    data = await fetch_json(http, FORECAST, "weather forecast", params={
        "latitude": p["latitude"], "longitude": p["longitude"], "timezone": "auto",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "start_date": max(start, today).isoformat(), "end_date": min(end, last).isoformat()})
    d = data.get("daily") or {}
    rows = list(zip(d.get("time") or [], d.get("weather_code") or [], d.get("temperature_2m_max") or [],
                    d.get("temperature_2m_min") or [], d.get("precipitation_probability_max") or []))
    if not rows:
        raise ValueError("The forecast came back empty.")
    return {"place": p.get("name") or trip["destination"], "days": rows, "partial": end > last}


def _sky(code) -> str:
    from tools import WEATHER_CODES  # tools imports this module, so look it up when needed
    return WEATHER_CODES.get(int(code or 0), "mixed")


async def weather(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown | str:
    _, k, trip = _trip(settings, args)
    f = await forecast(http, trip)
    if isinstance(f, str):
        return f
    days = f["days"]
    highs = [float(r[2] or 0) for r in days]
    lines = [f"{date.fromisoformat(r[0]):%a %d %b}: {_sky(r[1])}, {float(r[3] or 0):g} to {float(r[2] or 0):g}°C, "
             f"rain {r[4] or 0}%" for r in days]
    more = " The rest of the trip is beyond the forecast." if f["partial"] else ""
    said = (f"{f['place']} during {k}: highs from {min(highs):g} to {max(highs):g}°C, mostly "
            f"{_sky(max(set(r[1] for r in days), key=[r[1] for r in days].count))}.{more}")
    return screen.Shown(said, screen.card(
        "chart", f"{f['place']} weather", f"travel-weather-{k}", text="\n".join(lines) + more,
        chart={"type": "bar", "labels": [f"{date.fromisoformat(r[0]):%a %d}" for r in days], "values": highs,
               "unit": "°C"}))


async def summary(settings: Settings, args: dict, http: httpx.AsyncClient) -> screen.Shown:
    _, k, trip = _trip(settings, args)
    start, end = ts.days(trip)
    parts = [f"{trip['destination']}, {hs.spoken(start)} to {hs.spoken(end)} {end.year}. It {ts.countdown(trip)}."]
    plan = _ordered(trip["plan"])
    parts.append("PLAN\n" + ("\n".join(f"{date.fromisoformat(i['day']):%a %d} {i['time']} {i['what']}".replace("  ", " ")
                                        for i in plan[:6]) + (f"\n…and {len(plan) - 6} more" if len(plan) > 6 else "")
                             if plan else "Nothing planned yet."))
    books = _ordered(trip["bookings"])
    parts.append("BOOKINGS\n" + ("\n".join(f"{b['kind'].title()}: {_booking_words(b)}" for b in books[:5])
                                 if books else "None saved yet."))
    warnings = travel_papers.trip_warnings(settings, end)
    parts.append("DOCUMENTS\n" + ("\n".join(warnings) if warnings else "All saved documents are fine for this trip."))
    try:
        f = await forecast(http, trip)
        sky = f if isinstance(f, str) else "\n".join(
            f"{date.fromisoformat(r[0]):%a %d}: {_sky(r[1])}, {float(r[3] or 0):g} to {float(r[2] or 0):g}°C"
            for r in f["days"][:7])
    except (ValueError, httpx.HTTPError):
        sky = "The forecast isn't available right now."
    parts.append("WEATHER\n" + sky)
    gifts = [g for g in trip["gifts"] if not g["done"]]
    if gifts:
        parts.append(f"GIFTS\n{len(gifts)} still to get: " + ", ".join(g["what"] for g in gifts[:8]))
    said = f"{k} {ts.countdown(trip)}. {len(plan)} plans, {len(books)} bookings" + (
        f", and {len(warnings)} document warning{'s' if len(warnings) != 1 else ''}." if warnings else ".")
    buttons = [{"label": "Itinerary", "say": f"Show the itinerary for my {k} trip."},
               {"label": "Bookings", "say": f"Show my bookings for {k}."},
               {"label": "Weather", "say": f"What's the weather for my {k} trip?"},
               {"label": "Documents", "say": "Show my travel documents."}]
    return screen.Shown(said, screen.card("text", f"{k} summary", f"travel-summary-{k}", text="\n\n".join(parts),
                                          buttons=buttons))


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient = None):
    action = args.get("action")
    if action == "weather":
        return await weather(settings, args, http)
    if action == "summary":
        return await summary(settings, args, http)
    if action == "trip_list":
        return trip_list(settings)
    handlers = {"trip_add": trip_add, "trip_remove": trip_remove, "plan_add": plan_add, "plan_show": plan_show,
                "plan_move": plan_move, "plan_remove": plan_remove, "booking_add": booking_add,
                "booking_find": booking_find, "booking_list": booking_list, "booking_remove": booking_remove,
                "gift_add": gift_add, "gift_tick": gift_tick, "gift_list": gift_list,
                "journal_write": journal_write, "journal_read": journal_read}
    if action not in handlers:
        raise ValueError(f"Unknown travel action {action}.")
    return handlers[action](settings, args)
