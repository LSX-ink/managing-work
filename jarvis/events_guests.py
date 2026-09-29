"""Event guests: the guest list with RSVPs, dietary needs and plus-ones, counts, tables and the seating plan pop-up,
invitation wording details, and thank-you cards after the event.

Everything is saved in events.json in the memory folder. Each guest takes one seat; add a plus-one as their own guest
if you want to seat them separately.
"""

from datetime import date

import events_store as store
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.add("events-seating")

ACTIONS = ["guest_add", "rsvp", "guest_remove", "guests", "counts", "tables", "seat", "seating", "invitation",
           "thanks", "thanks_sent"]
STYLES = ["formal", "fun", "kids", "wedding", "christmas"]
MAX_TABLES = 30
MAX_SEATS = 30


def _rsvp(value, default: str = "pending") -> str:
    text = hs.clean(value).lower() or default
    text = {"coming": "yes", "attending": "yes", "declined": "no", "not coming": "no", "unsure": "maybe"}.get(text, text)
    if text not in store.RSVPS:
        raise ValueError("An RSVP is yes, no, maybe or pending.")
    return text


def guest_add(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    names = [hs.clean(n, 60) for n in (args.get("guests") or [])] or [hs.need(args.get("guest"), "guest", 60)]
    if len(event["guests"]) + len(names) > store.MAX_ITEMS:
        raise ValueError("That's a very long guest list.")
    for n in names:
        old = event["guests"].get(hs.find(event["guests"], n) or n, {})
        guest = {"rsvp": old.get("rsvp", "pending"), "diet": old.get("diet", ""), "plus": old.get("plus", 0),
                 "table": old.get("table", ""), "seat": old.get("seat", 0)}
        if hs.clean(args.get("rsvp")):
            guest["rsvp"] = _rsvp(args["rsvp"])
        if hs.clean(args.get("dietary")):
            guest["diet"] = hs.clean(args["dietary"], 80)
        if "plus_ones" in args:
            guest["plus"] = int(hs.number(args["plus_ones"], "number of plus-ones", 0, 10))
        event["guests"][hs.find(event["guests"], n) or n] = guest
    store.save(settings, found)
    return f"{', '.join(names)} {'is' if len(names) == 1 else 'are'} on the list for {key}. {len(event['guests'])} guests so far."


def rsvp(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    guest = store.find_in(event["guests"], args.get("guest"), "guest")
    event["guests"][guest]["rsvp"] = _rsvp(args.get("rsvp"), "yes")
    if "plus_ones" in args:
        event["guests"][guest]["plus"] = int(hs.number(args["plus_ones"], "number of plus-ones", 0, 10))
    if hs.clean(args.get("dietary")):
        event["guests"][guest]["diet"] = hs.clean(args["dietary"], 80)
    store.save(settings, found)
    return f"{guest} is down as {event['guests'][guest]['rsvp']}. That's {store.headcount(event)} people coming to {key}."


def guest_remove(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    guest = store.find_in(event["guests"], args.get("guest"), "guest")
    if not args.get("confirmed"):
        return f"Take {guest} off the guest list for {key}? Please confirm."
    del event["guests"][guest]
    event["thanks"].pop(guest, None)
    store.save(settings, found)
    return f"Took {guest} off the list."


def _counts(event: dict) -> dict:
    return {r: sum(g["rsvp"] == r for g in event["guests"].values()) for r in store.RSVPS}


def guests(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    if not event["guests"]:
        raise ValueError(f"There are no guests for {key} yet. Say who is invited.")
    rows = [[g, v["rsvp"], f"+{v['plus']}" if v["plus"] else "", v["diet"] or "", v["table"] or ""]
            for g, v in sorted(event["guests"].items(), key=lambda x: (store.RSVPS.index(x[1]["rsvp"]), x[0].lower()))]
    c = _counts(event)
    said = (f"{key}: {c['yes']} yes, {c['maybe']} maybe, {c['no']} no, {c['pending']} waiting. "
            f"That's {store.headcount(event)} people coming, plus-ones included.")
    return screen.Shown(said, screen.card("table", f"{key}: guests", f"events-guests-{key}", buttons=[
        store.button("Counts", f"Show the RSVP counts for {key}."), store.button("Seating", f"Show the seating plan for {key}.")],
        columns=["Guest", "RSVP", "Plus", "Dietary", "Table"], rows=rows))


def counts(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    c = _counts(event)
    diets = sorted({v["diet"] for v in event["guests"].values() if v["diet"] and v["rsvp"] != "no"})
    said = (f"{key}: {store.headcount(event)} people coming, {c['maybe']} maybe, {c['pending']} not replied."
            + (f" Dietary needs: {', '.join(diets)}." if diets else ""))
    card = screen.card("chart", f"{key}: RSVPs", f"events-counts-{key}", chart={
        "type": "bar", "labels": ["Yes", "Maybe", "No", "Waiting"], "values": [c["yes"], c["maybe"], c["no"], c["pending"]]},
        buttons=[store.button("Guest list", f"Show the guest list for {key}.")])
    return screen.Shown(said, card)


def tables(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    count = int(hs.number(args.get("tables"), "number of tables", 1, MAX_TABLES))
    seats = int(hs.number(args.get("seats_per_table", 8), "seats per table", 1, MAX_SEATS))
    event["tables"] = {f"Table {i}": seats for i in range(1, count + 1)}
    for g in event["guests"].values():
        if g["table"] not in event["tables"] or g["seat"] > seats:
            g["table"], g["seat"] = "", 0
    store.save(settings, found)
    return f"Set up {hs.plural(count, 'table')} of {seats} seats for {key}."


def _seated(event: dict) -> dict:
    return {(g["table"], g["seat"]): n for n, g in event["guests"].items() if g["table"]}


def seat(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    guest = store.find_in(event["guests"], args.get("guest"), "guest")
    if not hs.clean(args.get("table")):
        event["guests"][guest]["table"], event["guests"][guest]["seat"] = "", 0
        store.save(settings, found)
        return f"{guest} no longer has a seat."
    wanted = hs.clean(args.get("table"))
    table = store.find_in(event["tables"], f"Table {wanted}" if wanted.isdigit() else wanted, "table")
    taken = _seated(event)
    if "seat" in args and args["seat"] is not None:
        number = int(hs.number(args["seat"], "seat number", 1, event["tables"][table]))
    else:
        number = next((n for n in range(1, event["tables"][table] + 1) if (table, n) not in taken), 0)
        if not number:
            raise ValueError(f"{table} is full.")
    if taken.get((table, number), guest) != guest:
        raise ValueError(f"Seat {number} at {table} is taken by {taken[(table, number)]}.")
    event["guests"][guest]["table"], event["guests"][guest]["seat"] = table, number
    store.save(settings, found)
    return f"{guest} is at {table}, seat {number}."


def seating(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    if not event["tables"]:
        raise ValueError(f"{key} has no tables yet. Say how many tables and how many seats each.")
    taken = _seated(event)
    view = [{"name": t, "seats": [{"n": n, "guest": taken.get((t, n), "")} for n in range(1, size + 1)]}
            for t, size in event["tables"].items()]
    unseated = sorted(n for n, g in event["guests"].items() if not g["table"] and g["rsvp"] != "no")
    card = screen.card("events-seating", f"{key}: seating plan", f"events-seating-{key}",
                       data={"event": key, "tables": view, "unseated": unseated})
    return screen.Shown(f"{len(taken)} guests seated at {hs.plural(len(view), 'table')}, {len(unseated)} still to seat.", card)


def invitation(settings: Settings, args: dict, today: date) -> str:
    event, key = store.pick(store.load(settings), args.get("name"), today)
    style = hs.clean(args.get("style")).lower() or "fun"
    if style not in STYLES:
        raise ValueError("The style is formal, fun, kids, wedding or christmas.")
    day = date.fromisoformat(event["date"])
    facts = [f"event: {key}", f"kind: {event['kind']}", f"date: {hs.spoken(day)} {day.year}",
             f"time: {hs.clean(args.get('time')) or 'not decided'}", f"place: {event['place'] or 'not decided'}",
             f"dress code: {hs.clean(args.get('dress_code')) or 'none'}", f"RSVP by: {hs.clean(args.get('rsvp_by')) or 'not set'}",
             f"from: {hs.clean(args.get('host')) or 'the host'}"]
    return ("Invitation details: " + "; ".join(facts) + f". Write a short {style} invitation from these, ready to copy "
            "and send. Read out only the first two lines, offer to give the rest, and use only these details.")


def thanks(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    people = sorted({n for n, g in event["guests"].items() if g["rsvp"] == "yes"} | set(event["thanks"]))
    if not people:
        raise ValueError(f"There's nobody to thank for {key} yet.")
    items = []
    for p in people:
        t = event["thanks"].get(p, {})
        label = p + (f": {t['gift']}" if t.get("gift") else "")
        items.append({"label": label, "done": bool(t.get("sent")),
                      "say": "" if t.get("sent") else f"I've sent {p} a thank-you card for {key}."})
    done = sum(i["done"] for i in items)
    return screen.Shown(f"{done} of {len(items)} thank-you cards sent for {key}.",
                        screen.card("list", f"{key}: thank-you cards", f"events-thanks-{key}", items=items, checks=True))


def thanks_sent(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    who = hs.need(args.get("guest"), "guest", 60)
    person = hs.find(event["guests"], who) or hs.find(event["thanks"], who) or who
    entry = event["thanks"].setdefault(person, {"gift": "", "sent": False})
    if hs.clean(args.get("gift")):
        entry["gift"] = hs.clean(args["gift"], 80)
    if "sent" in args:
        entry["sent"] = bool(args["sent"])
    elif not hs.clean(args.get("gift")):
        entry["sent"] = True
    store.save(settings, found)
    if entry["sent"]:
        return f"Ticked off the thank-you card for {person}."
    return f"Noted {person}'s {entry['gift'] or 'gift'} on the thank-you list."


def tool_definitions() -> list[dict]:
    return [{
        "name": "event_guests",
        "description": "Guests for a party, wedding or gathering. action: guest_add = add a guest (or guests) with "
                       "optional rsvp, dietary needs and plus_ones; rsvp = record yes, no or maybe (plus_ones, "
                       "dietary); guest_remove (confirmed true only after the user says yes); guests = guest list "
                       "table with RSVP status; counts = yes/no/maybe chart and dietary needs; tables = set up "
                       "tables with seats; seat = put a guest at a table seat (no table = unseat); seating = "
                       "seating plan pop-up, tap a guest then a seat; invitation = gather details so you write the "
                       "invitation wording; thanks = thank-you card tracker after the event; thanks_sent = tick a "
                       "thank-you card or note the gift a guest gave.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "The event; may be left out for the next one."},
                "guest": {"type": "string"},
                "guests": {"type": "array", "items": {"type": "string"}, "description": "guest_add: several names."},
                "rsvp": {"type": "string", "enum": store.RSVPS},
                "dietary": {"type": "string", "description": "e.g. vegetarian, nut allergy."},
                "plus_ones": {"type": "integer"},
                "tables": {"type": "integer", "description": "tables: how many tables."},
                "seats_per_table": {"type": "integer"},
                "table": {"type": "string", "description": "seat: e.g. Table 2 or just 2."},
                "seat": {"type": "integer", "description": "seat: number; the first free seat if left out."},
                "style": {"type": "string", "enum": STYLES},
                "time": {"type": "string"},
                "dress_code": {"type": "string"},
                "rsvp_by": {"type": "string"},
                "host": {"type": "string"},
                "gift": {"type": "string", "description": "thanks_sent: what they gave."},
                "sent": {"type": "boolean", "description": "thanks_sent: false to untick."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"event_guests"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action, event = args.get("action"), args.get("name")
    if action == "guests":
        return guests(settings, event, today)
    if action == "counts":
        return counts(settings, event, today)
    if action == "seating":
        return seating(settings, event, today)
    if action == "thanks":
        return thanks(settings, event, today)
    actions = {"guest_add": guest_add, "rsvp": rsvp, "guest_remove": guest_remove, "tables": tables, "seat": seat,
               "invitation": invitation, "thanks_sent": thanks_sent}
    if action not in actions:
        raise ValueError(f"Unknown event guest action: {action}")
    return actions[action](settings, args, today)
