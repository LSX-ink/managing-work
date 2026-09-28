"""Travel paperwork and planning lists: document expiry dates (passport, visa, insurance, EHIC/GHIC) with a warning
6 months ahead, the annual leave allowance, a wishlist of places (ticked off when visited, counted by country) and
the built-in travel checklists.

Stored in travel-documents.json, travel-leave.json, travel-places.json and travel-checklists.json in the memory
folder; nothing goes online.
"""

from datetime import date, timedelta

import homestore as hs
import household_store as hstore
import screen
import travel_data
import travel_store as ts
from config import Settings

DOCS = "travel-documents.json"
LEAVE = "travel-leave.json"
PLACES = "travel-places.json"
TICKS = "travel-checklists.json"
DOC_KINDS = ["passport", "visa", "insurance", "ehic", "ghic", "driving licence", "esta", "other"]
WARN_MONTHS = 6

ACTIONS = ["doc_set", "doc_list", "doc_remove", "leave_set", "leave_book", "leave_show", "leave_cancel",
           "place_add", "place_visited", "place_list", "place_count", "place_remove",
           "checklist_show", "checklist_tick", "checklist_reset"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "travel_papers",
        "description": "Travel documents, holiday allowance, places wishlist and travel checklists. doc_set "
                       "(passport, visa, travel insurance, EHIC/GHIC... with its expiry date), doc_list (warns 6 "
                       "months before expiry), doc_remove; annual leave: leave_set (days a year), leave_book "
                       "(dates or days off), leave_show (total, booked, remaining), leave_cancel; places I want to "
                       "visit: place_add, place_visited (tick off), place_list, place_count ('where have I been?' by "
                       "country), place_remove; checklists 'before you go' (locks, plants, bins, milk), 'airport "
                       "day', 'coming home': checklist_show, checklist_tick, checklist_reset. Removing needs "
                       "confirmed true, set only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Document name, e.g. 'my passport', 'Sam's passport'."},
                "kind": {"type": "string", "enum": DOC_KINDS},
                "expiry": {"type": "string", "description": "YYYY-MM-DD."},
                "total": {"type": "number", "description": "leave_set: days of leave a year."},
                "year": {"type": "integer"},
                "start": {"type": "string", "description": "YYYY-MM-DD."},
                "end": {"type": "string", "description": "YYYY-MM-DD."},
                "days": {"type": "number", "description": "leave_book: days used, if not every weekday."},
                "note": text,
                "number": {"type": "integer", "description": "Booked leave number from the list."},
                "place": text,
                "country": text,
                "day": {"type": "string", "description": "place_visited: when, YYYY-MM-DD."},
                "list": {"type": "string", "enum": list(travel_data.CHECKLISTS)},
                "item": text,
                "done": {"type": "boolean", "description": "checklist_tick: false unticks."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"travel_papers"}


# ---- documents ---------------------------------------------------------------------------

def _status(expiry: date, today: date) -> str:
    if expiry < today:
        return "expired"
    if expiry < hstore.add_months(today, WARN_MONTHS):
        return f"renew soon: {(expiry - today).days} days left"
    return "fine"


def doc_set(settings: Settings, args: dict) -> str:
    found = hstore.rows(settings, DOCS)
    kind = args.get("kind") if args.get("kind") in DOC_KINDS else "other"
    name = hs.clean(args.get("name"), 60) or ("EHIC" if kind == "ehic" else "GHIC" if kind == "ghic" else kind.title())
    expiry = hs.parse_day(hs.need(args.get("expiry"), "expiry date"))
    key = next((k for k in found if k.lower() == name.lower()), name)
    hstore.put(settings, DOCS, found, key, {"kind": kind, "expiry": expiry.isoformat()})
    status = _status(expiry, hs.today())
    warn = "" if status == "fine" else f" Heads up: it's {status.split(':')[0]}."
    return f"Saved {key}, expiring {hs.spoken(expiry)} {expiry.year}.{warn}"


def doc_rows(settings: Settings) -> list[tuple[str, dict, date, str]]:
    today = hs.today()
    rows = [(k, v, date.fromisoformat(v["expiry"])) for k, v in hstore.rows(settings, DOCS).items()]
    return [(k, v, d, _status(d, today)) for k, v, d in sorted(rows, key=lambda r: r[2])]


def doc_list(settings: Settings) -> screen.Shown:
    rows = doc_rows(settings)
    table = [[k, v["kind"].upper() if v["kind"] in ("ehic", "ghic", "esta") else v["kind"].title(),
              f"{d:%d %b %Y}", s] for k, v, d, s in rows]
    alerts = [r for r in rows if r[3] != "fine"]
    said = (f"{len(rows)} documents saved." if not alerts else
            f"{len(alerts)} need attention: " + ", ".join(f"{k} ({s.split(':')[0]})" for k, _, _, s in alerts) + ".")
    return screen.Shown(said if rows else "No travel documents saved yet.", screen.card(
        "table", "Travel documents", "travel-documents", columns=["Document", "Type", "Expires", "Status"],
        rows=table))


def doc_remove(settings: Settings, args: dict) -> str:
    return hstore.remove(settings, DOCS, args.get("name"), "document", bool(args.get("confirmed")))


def trip_warnings(settings: Settings, trip_end: date) -> list[str]:
    """Document problems for a trip ending on trip_end: expired, running out, or a passport near its end."""
    out = []
    for k, v, d, _ in doc_rows(settings):
        if d < trip_end:
            out.append(f"{k} expires {d:%d %b %Y}, before the trip ends.")
        elif v["kind"] == "passport" and d < hstore.add_months(trip_end, WARN_MONTHS):
            out.append(f"{k} has under 6 months left after the trip; many countries want 6 months.")
        elif d < hstore.add_months(hs.today(), WARN_MONTHS):
            out.append(f"{k} expires {d:%d %b %Y}; renew it soon.")
    return out


# ---- annual leave ------------------------------------------------------------------------

def _leave(settings: Settings) -> dict:
    return hs.load(settings, LEAVE, {})


def _year(settings: Settings, args: dict) -> tuple[dict, dict, str]:
    data = _leave(settings)
    year = str(args.get("year") or hs.today().year)
    return data, data.setdefault(year, {"total": 0, "booked": []}), year


def weekdays(start: date, end: date) -> int:
    return sum(1 for n in range((end - start).days + 1) if (start + timedelta(days=n)).weekday() < 5)


def leave_set(settings: Settings, args: dict) -> str:
    data, year_data, year = _year(settings, args)
    year_data["total"] = hs.number(args.get("total"), "number of days", 0, 366)
    hs.save(settings, LEAVE, data)
    return f"Your {year} leave allowance is {year_data['total']:g} days. {_left(year_data):g} left to book."


def _used(y: dict) -> float:
    return sum(b["days"] for b in y["booked"])


def _left(y: dict) -> float:
    return y["total"] - _used(y)


def leave_book(settings: Settings, args: dict) -> str:
    start = hs.parse_day(hs.need(args.get("start"), "start date"))
    end = hs.parse_day(args.get("end")) if hs.clean(args.get("end")) else start
    if end < start:
        raise ValueError("The leave ends before it starts.")
    data, y, year = _year(settings, {"year": args.get("year") or start.year})
    days = hs.number(args["days"], "number of days", 0.5, 366) if args.get("days") else weekdays(start, end)
    if not days:
        raise ValueError("Those dates are all weekend days; say how many days of leave it uses.")
    if len(y["booked"]) >= ts.MAX_ITEMS:
        raise ValueError("That's a lot of leave entries; cancel an old one first.")
    y["booked"].append({"id": ts.next_id(y["booked"]), "start": start.isoformat(), "end": end.isoformat(),
                        "days": days, "note": hs.clean(args.get("note"), 60)})
    hs.save(settings, LEAVE, data)
    left = _left(y)
    warn = " That's more than your allowance." if left < 0 else ""
    return f"Booked {days:g} days off from {hs.spoken(start)}. {left:g} of {y['total']:g} days left for {year}.{warn}"


def leave_show(settings: Settings, args: dict) -> screen.Shown:
    _, y, year = _year(settings, args)
    today = hs.today().isoformat()
    taken = sum(b["days"] for b in y["booked"] if b["end"] < today)
    booked = _used(y) - taken
    left = _left(y)
    lines = [f"{b['id']}. {date.fromisoformat(b['start']):%d %b} to {date.fromisoformat(b['end']):%d %b}: "
             f"{b['days']:g} days{' (' + b['note'] + ')' if b['note'] else ''}" for b in y["booked"]]
    said = f"{year}: {y['total']:g} days, {taken:g} taken, {booked:g} booked ahead, {left:g} left."
    return screen.Shown(said, screen.card(
        "chart", f"Annual leave {year}", "travel-leave", text=said + ("\n" + "\n".join(lines) if lines else ""),
        chart={"type": "bar", "labels": ["Allowance", "Taken", "Booked", "Left"],
               "values": [y["total"], taken, booked, left], "unit": " d"}))


def leave_cancel(settings: Settings, args: dict) -> str:
    data, y, year = _year(settings, args)
    item = ts.by_id(y["booked"], args.get("number"), "leave booking")
    if not args.get("confirmed"):
        return f"Ask the user to confirm cancelling the leave from {item['start']}, then call again with confirmed true."
    y["booked"].remove(item)
    hs.save(settings, LEAVE, data)
    return f"Cancelled that leave. {_left(y):g} days left for {year}."


# ---- places wishlist ---------------------------------------------------------------------

def _places(settings: Settings) -> list:
    return [p for p in hs.load(settings, PLACES, []) if isinstance(p, dict)]


def _find_place(places: list, name) -> dict | None:
    key = hs.find([p["place"] for p in places], name)
    return next((p for p in places if p["place"] == key), None) if key else None


def _country_name(value) -> str:
    try:
        return ts.country(value)
    except ValueError:
        return hs.clean(value, 40).title()


def place_add(settings: Settings, args: dict) -> str:
    places = _places(settings)
    name = hs.need(args.get("place"), "place", 60)
    if _find_place(places, name) and _find_place(places, name)["place"].lower() == name.lower():
        return f"{name} is already on your list."
    if len(places) >= ts.MAX_ITEMS:
        raise ValueError("Your places list is full.")
    places.append({"place": name, "country": _country_name(args.get("country")) if args.get("country") else "",
                   "notes": hs.clean(args.get("note"), 200), "visited": ""})
    hs.save(settings, PLACES, places)
    return f"Added {name} to the places you want to visit. {sum(1 for p in places if not p['visited'])} to go."


def place_visited(settings: Settings, args: dict) -> str:
    places = _places(settings)
    name = hs.need(args.get("place"), "place", 60)
    hit = _find_place(places, name)
    if not hit:
        hit = {"place": name, "country": "", "notes": "", "visited": ""}
        places.append(hit)
    if args.get("country"):
        hit["country"] = _country_name(args["country"])
    hit["visited"] = hs.parse_day(args.get("day")).isoformat()
    hs.save(settings, PLACES, places)
    return f"Ticked off {hit['place']}. You've been to {sum(1 for p in places if p['visited'])} places on the list."


def place_list(settings: Settings) -> screen.Shown:
    places = _places(settings)
    items = [{"label": f"{p['place']}{', ' + p['country'] if p['country'] else ''}"
                       f"{' (' + p['notes'] + ')' if p['notes'] else ''}", "done": bool(p["visited"]),
              "say": "" if p["visited"] else f"I've visited {p['place']}."} for p in places]
    todo = sum(1 for p in places if not p["visited"])
    return screen.Shown(f"{todo} places still to visit, {len(places) - todo} visited.", screen.card(
        "list", "Places to visit", "travel-places", items=items, checks=True,
        buttons=[{"label": "Where have I been?", "say": "Where have I been? Count my visited places by country."}]))


def place_count(settings: Settings) -> screen.Shown:
    counts: dict[str, list] = {}
    for p in _places(settings):
        if p["visited"]:
            counts.setdefault(p["country"] or "Country not given", []).append(p["place"])
    ranked = sorted(counts.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    rows = [[c, str(len(v)), ", ".join(v)] for c, v in ranked]
    named = [c for c in counts if c != "Country not given"]
    total = sum(len(v) for v in counts.values())
    said = f"You've ticked off {total} places in {len(named)} countries." if total else "You haven't ticked off any places yet."
    return screen.Shown(said, screen.card("table", "Where I've been", "travel-been",
                                          columns=["Country", "Places", "Which"], rows=rows))


def place_remove(settings: Settings, args: dict) -> str:
    places = _places(settings)
    hit = _find_place(places, hs.need(args.get("place"), "place"))
    if not hit:
        raise ValueError(f"{hs.clean(args.get('place'))} isn't on your places list.")
    if not args.get("confirmed"):
        return f"Ask the user to confirm removing {hit['place']}, then call again with confirmed true."
    places.remove(hit)
    hs.save(settings, PLACES, places)
    return f"Removed {hit['place']} from your places list."


# ---- checklists --------------------------------------------------------------------------

def _list_name(args: dict) -> str:
    name = args.get("list") or "before you go"
    if name not in travel_data.CHECKLISTS:
        raise ValueError(f"The travel checklists are: {', '.join(travel_data.CHECKLISTS)}.")
    return name


def checklist_show(settings: Settings, args: dict) -> screen.Shown:
    name = _list_name(args)
    ticked = set(hs.load(settings, TICKS, {}).get(name, []))
    items = [{"label": i, "done": i in ticked,
              "say": f"{'Untick' if i in ticked else 'Tick'} '{i}' on my {name} travel checklist."}
             for i in travel_data.CHECKLISTS[name]]
    left = sum(1 for i in items if not i["done"])
    return screen.Shown(f"{left} of {len(items)} left on the {name} checklist.", screen.card(
        "list", f"Travel: {name}", f"travel-check-{name}", items=items, checks=True,
        buttons=[{"label": "Start again", "say": f"Reset my {name} travel checklist."}]))


def checklist_tick(settings: Settings, args: dict) -> str:
    name = _list_name(args)
    item = hs.find(travel_data.CHECKLISTS[name], hs.need(args.get("item"), "item"))
    if item is None:
        raise ValueError(f"That isn't on the {name} checklist.")
    data = hs.load(settings, TICKS, {})
    ticked = [i for i in data.get(name, []) if i != item]
    if args.get("done", True):
        ticked.append(item)
    data[name] = ticked
    hs.save(settings, TICKS, data)
    left = len(travel_data.CHECKLISTS[name]) - len(ticked)
    return f"{'Ticked' if args.get('done', True) else 'Unticked'} {item}. {left} left." if left else \
        f"Ticked {item}. That's the whole {name} list done."


def checklist_reset(settings: Settings, args: dict) -> str:
    name = _list_name(args)
    data = hs.load(settings, TICKS, {})
    data[name] = []
    hs.save(settings, TICKS, data)
    return f"The {name} checklist is clear again."


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    simple = {"doc_list": doc_list, "place_list": place_list, "place_count": place_count}
    if action in simple:
        return simple[action](settings)
    handlers = {"doc_set": doc_set, "doc_remove": doc_remove, "leave_set": leave_set, "leave_book": leave_book,
                "leave_show": leave_show, "leave_cancel": leave_cancel, "place_add": place_add,
                "place_visited": place_visited, "place_remove": place_remove, "checklist_show": checklist_show,
                "checklist_tick": checklist_tick, "checklist_reset": checklist_reset}
    if action not in handlers:
        raise ValueError(f"Unknown travel action {action}.")
    return handlers[action](settings, args)
