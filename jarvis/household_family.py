"""Family and pets: pet care, party planning with RSVPs, a sitter info sheet, emergency contacts and school dates.

Everything is saved only in household-*.json (and the sitter sheet as household-sitter-sheet.md) in the memory
folder and is never sent to any website. The sitter sheet and emergency contacts only pop up on the screen:
what Alfred hears back is a count, not the names and numbers.
"""

import re
from datetime import date, datetime

import homestore as hs
import household_store as hh
import screen
from config import Settings

PETS, PARTIES, SITTER, CONTACTS, TERMS = ("household-pets.json", "household-parties.json", "household-sitter.json",
                                          "household-contacts.json", "household-terms.json")
SITTER_SHEET = "household-sitter-sheet.md"
RSVP = ("yes", "no", "maybe")
SITTER_FIELDS = {"address": "Address", "contacts": "Who to call", "doctor": "Doctor", "vet": "Vet",
                 "allergies": "Allergies", "medicines": "Medicines", "bedtimes": "Bedtimes", "meals": "Meals",
                 "pets": "Pets", "house": "House notes (stopcock, fuse box, alarm)", "notes": "Other notes"}
MAX_GUESTS, MAX_LOG = 200, 60


# Pets

def _pet(found: dict, label) -> str:
    return hh.key(found, label, "pet")


def pet_add(settings: Settings, label, kind=None) -> str:
    label = hs.need(label, "pet", 40)
    found = hh.rows(settings, PETS)
    k = hs.find(found, label) or label
    pet = found.get(k) or {"fed": [], "due": {}, "weights": []}
    pet["kind"] = hs.clean(kind, 40) or pet.get("kind", "")
    hh.put(settings, PETS, found, k, pet)
    return f"Added {k}{' the ' + pet['kind'] if pet['kind'] else ''}."


def pet_fed(settings: Settings, label) -> str:
    found = hh.rows(settings, PETS)
    k = _pet(found, label)
    found[k]["fed"] = (found[k]["fed"] + [hs.now().isoformat(timespec="minutes")])[-MAX_LOG:]
    hs.save(settings, PETS, found)
    today = sum(f.startswith(hs.today().isoformat()) for f in found[k]["fed"])
    return f"{k} fed. That's {hs.plural(today, 'meal')} today."


def pet_feeds(settings: Settings, label) -> str:
    found = hh.rows(settings, PETS)
    k = _pet(found, label)
    times = [datetime.fromisoformat(f).strftime("%H:%M") for f in found[k]["fed"] if f.startswith(hs.today().isoformat())]
    return f"{k} was fed today at {', '.join(times)}." if times else f"{k} hasn't been fed today."


def pet_due(settings: Settings, label, what, when) -> str:
    found = hh.rows(settings, PETS)
    k = _pet(found, label)
    what = hs.need(what, "thing that's due", 30).lower()
    if not when:
        raise ValueError("When is it due?")
    day = hs.parse_day(when)
    found[k]["due"][what] = day.isoformat()
    hs.save(settings, PETS, found)
    return f"{k}'s {what} is due on {hs.spoken(day)} {day.year}."


def pet_dues(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, PETS)
    today = hs.today()
    dues = sorted((date.fromisoformat(d), k, w) for k, p in found.items() for w, d in p["due"].items())
    if not dues:
        return "No pet dates saved yet."
    card = screen.card("table", "Pet care due", "household-pet-dues", columns=["Pet", "What", "Date", "When"],
                       rows=[[k, w, hh.short(d), hh.until(d, today)] for d, k, w in dues])
    d, k, w = dues[0]
    return screen.Shown(f"Next up: {k}'s {w}, {hh.until(d, today)}.", card)


def pet_weigh(settings: Settings, label, kg, when=None) -> str:
    found = hh.rows(settings, PETS)
    k = _pet(found, label)
    kg = round(hs.number(kg, "weight", 0.01, 200), 2)
    day = hs.parse_day(when).isoformat()
    weights = [w for w in found[k]["weights"] if w["date"] != day] + [{"date": day, "kg": kg}]
    found[k]["weights"] = sorted(weights, key=lambda w: w["date"])[-MAX_LOG:]
    hs.save(settings, PETS, found)
    return f"{k} weighs {kg:g} kg."


def pet_weights(settings: Settings, label) -> screen.Shown | str:
    found = hh.rows(settings, PETS)
    k = _pet(found, label)
    weights = found[k]["weights"]
    if not weights:
        return f"No weights logged for {k} yet."
    card = screen.card("chart", f"{k}'s weight", f"household-pet-weight-{k}",
                       chart={"type": "line", "labels": [f"{date.fromisoformat(w['date']):%d %b %y}" for w in weights],
                              "values": [w["kg"] for w in weights], "unit": "kg"})
    change = round(weights[-1]["kg"] - weights[0]["kg"], 2)
    since = hs.spoken(date.fromisoformat(weights[0]["date"]))
    trend = f", {'up' if change > 0 else 'down'} {abs(change):g} kg since {since}" if change else ""
    return screen.Shown(f"{k} weighs {weights[-1]['kg']:g} kg{trend}.", card)


# Party and event planner

def _party(found: dict, label) -> str:
    if not label and len(found) == 1:
        return next(iter(found))
    return hh.key(found, label, "event")


def party_create(settings: Settings, label, when, budget=None) -> str:
    label = hs.need(label, "event", 60)
    if not when:
        raise ValueError("When is it?")
    day = hs.parse_day(when)
    found = hh.rows(settings, PARTIES)
    k = hs.find(found, label) or label
    party = found.get(k) or {"guests": {}, "bring": [], "spent": []}
    party["date"] = day.isoformat()
    party["budget"] = round(hs.number(budget, "budget"), 2) if budget is not None else party.get("budget", 0)
    hh.put(settings, PARTIES, found, k, party)
    return f"{k} is on {hs.spoken(day)}, {hh.until(day, hs.today())}."


def party_guests(settings: Settings, label, names) -> str:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    guests = found[k]["guests"]
    have = {g.lower() for g in guests}
    new = [n for n in hh.words(names, MAX_GUESTS, 60) if n.lower() not in have]
    for n in new[:MAX_GUESTS - len(guests)]:
        guests[n] = "invited"
    hs.save(settings, PARTIES, found)
    return f"{hs.plural(len(guests), 'guest')} on the list for {k}."


def party_rsvp(settings: Settings, label, person, status) -> str:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    if status not in RSVP:
        raise ValueError("Is that a yes, no or maybe?")
    guests = found[k]["guests"]
    g = hs.find(guests, hs.need(person, "guest", 60)) or hs.clean(person, 60)
    if g not in guests and len(guests) >= MAX_GUESTS:
        raise ValueError("The guest list is full.")
    guests[g] = status
    hs.save(settings, PARTIES, found)
    return f"{g}: {status}. " + _counts_text(guests)


def _counts(guests: dict) -> dict:
    return {s: sum(v == s for v in guests.values()) for s in (*RSVP, "invited")}


def _counts_text(guests: dict) -> str:
    c = _counts(guests)
    return f"{c['yes']} yes, {c['no']} no, {c['maybe']} maybe, {c['invited']} not replied."


def party_counts(settings: Settings, label) -> screen.Shown:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    c = _counts(found[k]["guests"])
    card = screen.card("chart", f"{k} replies", f"household-party-counts-{k}",
                       chart={"type": "bar", "labels": ["Yes", "No", "Maybe", "Not replied"],
                              "values": [c["yes"], c["no"], c["maybe"], c["invited"]]})
    return screen.Shown(f"{k}: " + _counts_text(found[k]["guests"]), card)


def party_bring(settings: Settings, label, items, person=None) -> str:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    bring = found[k]["bring"]
    have = {b["item"].lower() for b in bring}
    who = hs.clean(person, 60)
    bring += [{"item": i, "who": who, "done": False} for i in hh.words(items) if i.lower() not in have][:100 - len(bring)]
    hs.save(settings, PARTIES, found)
    return f"{hs.plural(len(bring), 'thing')} on the to-bring list for {k}."


def party_tick(settings: Settings, label, items) -> str:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    words = [w.lower() for w in hh.words(items)]
    ticked = [b["item"] for b in found[k]["bring"] if not b["done"] and any(w in b["item"].lower() for w in words)]
    for b in found[k]["bring"]:
        b["done"] = b["done"] or b["item"] in ticked
    hs.save(settings, PARTIES, found)
    left = sum(not b["done"] for b in found[k]["bring"])
    return (f"Sorted: {', '.join(ticked)}." if ticked else "None of those were on the list.") + f" {left} left."


def party_spend(settings: Settings, label, amount, what) -> str:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    amount = round(hs.number(amount, "amount"), 2)
    found[k]["spent"] = (found[k]["spent"] + [{"what": hs.clean(what, 60) or "spending", "amount": amount}])[-200:]
    hs.save(settings, PARTIES, found)
    spent = sum(s["amount"] for s in found[k]["spent"])
    budget = found[k].get("budget") or 0
    cur = settings.currency
    left = f", {hs.money(budget - spent, cur)} of the budget left" if budget else ""
    return f"Spent {hs.money(spent, cur)} on {k} so far{left}."


def party_show(settings: Settings, label) -> screen.Shown:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    p = found[k]
    day = date.fromisoformat(p["date"])
    cur = settings.currency
    spent = sum(s["amount"] for s in p["spent"])
    budget = f"Spent {hs.money(spent, cur)}" + (f" of {hs.money(p['budget'], cur)}" if p.get("budget") else "")
    bring = [b["item"] + (f" ({b['who']})" if b["who"] else "") for b in p["bring"] if not b["done"]]
    text = (f"{hs.spoken(day)} {day.year}, {hh.until(day, hs.today())}. {_counts_text(p['guests'])} {budget}.\n"
            f"Still to bring: {', '.join(bring) if bring else 'nothing'}.")
    rows = [[g, s if s != "invited" else "not replied"] for g, s in sorted(p["guests"].items(), key=lambda kv: kv[0].lower())]
    card = screen.card("table", k, f"household-party-{k}", text=text, columns=["Guest", "RSVP"], rows=rows,
                       buttons=[{"label": "To-bring list", "say": f"Show the to-bring list for {k}."},
                                {"label": "Reply counts", "say": f"How many have said yes to {k}?"}])
    return screen.Shown(f"{k} is {hh.until(day, hs.today())}: {_counts_text(p['guests'])}", card)


def party_bring_list(settings: Settings, label) -> screen.Shown:
    found = hh.rows(settings, PARTIES)
    k = _party(found, label)
    items = [{"label": b["item"] + (f" ({b['who']})" if b["who"] else ""), "done": b["done"],
              "say": f"Tick off {b['item']} on the to-bring list for {k}."} for b in found[k]["bring"]]
    left = sum(not b["done"] for b in found[k]["bring"])
    card = screen.card("list", f"{k}: to bring", f"household-party-bring-{k}", items=items, checks=True)
    return screen.Shown(f"{hs.plural(left, 'thing')} still to sort for {k}.", card)


# Babysitter / house-sitter sheet

def _sheet(fields: dict) -> str:
    parts = [f"## {title}\n\n{fields[f]}" for f, title in SITTER_FIELDS.items() if fields.get(f)]
    return "# For the sitter\n\n" + "\n\n".join(parts) + "\n"


def sitter_set(settings: Settings, field, value) -> str:
    if field not in SITTER_FIELDS:
        raise ValueError("Which part of the sitter sheet: " + ", ".join(SITTER_FIELDS) + "?")
    value = hs.need(value, "text", 1500)
    fields = hs.load(settings, SITTER, {})
    fields[field] = value
    hs.save(settings, SITTER, fields)
    hs.path(settings, SITTER_SHEET).write_text(_sheet(fields), encoding="utf-8")
    return f"Saved the {SITTER_FIELDS[field].split(' (')[0].lower()} on the sitter sheet."


def sitter_clear(settings: Settings, field, confirmed: bool) -> str:
    fields = hs.load(settings, SITTER, {})
    if field not in fields:
        raise ValueError("That part of the sitter sheet is already empty.")
    if not confirmed:
        return f"Ask the user to confirm clearing the {field} part of the sitter sheet, then call again with confirmed true."
    del fields[field]
    hs.save(settings, SITTER, fields)
    hs.path(settings, SITTER_SHEET).write_text(_sheet(fields), encoding="utf-8")
    return f"Cleared the {field} part of the sitter sheet."


def sitter_show(settings: Settings) -> screen.Shown | str:
    fields = hs.load(settings, SITTER, {})
    if not any(fields.get(f) for f in SITTER_FIELDS):
        return "The sitter sheet is empty; tell me the address, who to call, allergies, bedtimes and so on."
    missing = [f for f in SITTER_FIELDS if not fields.get(f)]
    card = screen.card("text", "Sitter info sheet", "household-sitter", text=_sheet(fields))
    todo = f"; not filled in yet: {', '.join(missing)}." if missing else "."
    return screen.Shown("The sitter sheet is on the screen" + todo, card)


# Emergency contacts (shown only on the screen)

def contact_add(settings: Settings, label, number, relation=None) -> str:
    label = hs.need(label, "contact", 60)
    number = hs.clean(number, 30)
    if not re.fullmatch(r"\+?[\d ()-]{3,25}", number):
        raise ValueError("That doesn't look like a phone number.")
    found = hh.rows(settings, CONTACTS)
    k = hs.find(found, label) or label
    hh.put(settings, CONTACTS, found, k, {"number": number, "relation": hs.clean(relation, 40)})
    return f"Saved {k} to your emergency contacts, kept only on this PC."


def contacts_show(settings: Settings) -> screen.Shown | str:
    found = hh.rows(settings, CONTACTS)
    if not found:
        return "No emergency contacts saved yet."
    card = screen.card("table", "Emergency contacts", "household-contacts", columns=["Name", "Number", "Who"],
                       rows=[[k, r["number"], r["relation"]] for k, r in found.items()],
                       text="Kept only in your memory folder on this PC; never sent anywhere. In an emergency dial 999.")
    return screen.Shown(f"{hs.plural(len(found), 'emergency contact')} on the screen.", card)


# School and family dates

def term_add(settings: Settings, label, start, end=None) -> str:
    label = hs.need(label, "date", 60)
    if not start:
        raise ValueError("When does it start?")
    first = hs.parse_day(start)
    last = hs.parse_day(end) if end else first
    if last < first:
        raise ValueError("It ends before it starts.")
    found = hh.rows(settings, TERMS)
    k = hs.find(found, label) or label
    hh.put(settings, TERMS, found, k, {"start": first.isoformat(), "end": last.isoformat()})
    span = f"from {hs.spoken(first)} to {hs.spoken(last)}" if last != first else f"on {hs.spoken(first)}"
    return f"{k} is {span}, {hh.until(first, hs.today())}."


def _countdown(first: date, last: date, today: date) -> str:
    if first <= today <= last:
        return "now" + (f", ends {hh.until(last, today)}" if last != first else "")
    return hh.until(first, today)


def term_list(settings: Settings) -> screen.Shown | str:
    today = hs.today()
    found = sorted((date.fromisoformat(r["start"]), date.fromisoformat(r["end"]), k)
                   for k, r in hh.rows(settings, TERMS).items())
    found = [f for f in found if f[1] >= today]
    if not found:
        return "No school or family dates coming up."
    rows = [[k, hh.short(a), hh.short(b) if b != a else "", _countdown(a, b, today)] for a, b, k in found]
    card = screen.card("table", "School and family dates", "household-terms", columns=["What", "From", "To", "When"],
                       rows=rows)
    a, b, k = found[0]
    return screen.Shown(f"Next: {k}, {_countdown(a, b, today)}.", card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "household_family",
        "description": "Pets, party planner, sitter sheet, emergency contacts and school term dates. pet_add (name, "
                       "kind e.g. dog), pet_fed, pet_feeds ('has the dog been fed?'), pet_due (name, what e.g. vet, "
                       "vaccination, flea, date), pet_dues table, pet_weigh (name, amount = kg), pet_weights chart, "
                       "pet_remove. party_create event (name, date, optional amount = budget), party_guests (items), "
                       "party_rsvp (person, status yes/no/maybe), party_counts, party_bring (items, optional person "
                       "bringing), party_tick (items), party_spend (amount, what), party_show guest table and "
                       "summary, party_bring_list, party_remove. sitter_set babysitter or house-sitter info (field, "
                       "text), sitter_show, sitter_clear (field). contact_add emergency contact (name, number, "
                       "relation), contacts_show, contact_remove; kept only locally. term_add school term, half "
                       "term, inset day or family date (name, date, optional until), term_list with countdowns, "
                       "term_remove. Set confirmed true only after the user confirms a remove or clear.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "pet_add", "pet_fed", "pet_feeds", "pet_due", "pet_dues", "pet_weigh", "pet_weights", "pet_remove",
                    "party_create", "party_guests", "party_rsvp", "party_counts", "party_bring", "party_tick",
                    "party_spend", "party_show", "party_bring_list", "party_remove", "sitter_set", "sitter_show",
                    "sitter_clear", "contact_add", "contacts_show", "contact_remove", "term_add", "term_list",
                    "term_remove"]},
                "name": {"type": "string", "description": "The pet, event, contact or date."},
                "kind": text,
                "what": text,
                "person": text,
                "status": {"type": "string", "enum": list(RSVP)},
                "items": {"type": "array", "items": text},
                "amount": {"type": "number"},
                "field": {"type": "string", "enum": list(SITTER_FIELDS)},
                "text": text,
                "number": text,
                "relation": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'tomorrow'."},
                "until": {"type": "string", "description": "Last day, YYYY-MM-DD."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"household_family"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    label, items, ok = a("name"), a("items"), bool(a("confirmed"))
    actions = {
        "pet_add": lambda: pet_add(settings, label, a("kind")),
        "pet_fed": lambda: pet_fed(settings, label),
        "pet_feeds": lambda: pet_feeds(settings, label),
        "pet_due": lambda: pet_due(settings, label, a("what"), a("date")),
        "pet_dues": lambda: pet_dues(settings),
        "pet_weigh": lambda: pet_weigh(settings, label, a("amount"), a("date")),
        "pet_weights": lambda: pet_weights(settings, label),
        "pet_remove": lambda: hh.remove(settings, PETS, label, "pet", ok),
        "party_create": lambda: party_create(settings, label, a("date"), a("amount")),
        "party_guests": lambda: party_guests(settings, label, items),
        "party_rsvp": lambda: party_rsvp(settings, label, a("person"), a("status")),
        "party_counts": lambda: party_counts(settings, label),
        "party_bring": lambda: party_bring(settings, label, items, a("person")),
        "party_tick": lambda: party_tick(settings, label, items),
        "party_spend": lambda: party_spend(settings, label, a("amount"), a("what")),
        "party_show": lambda: party_show(settings, label),
        "party_bring_list": lambda: party_bring_list(settings, label),
        "party_remove": lambda: hh.remove(settings, PARTIES, label, "event", ok),
        "sitter_set": lambda: sitter_set(settings, a("field"), a("text")),
        "sitter_show": lambda: sitter_show(settings),
        "sitter_clear": lambda: sitter_clear(settings, a("field"), ok),
        "contact_add": lambda: contact_add(settings, label, a("number"), a("relation")),
        "contacts_show": lambda: contacts_show(settings),
        "contact_remove": lambda: hh.remove(settings, CONTACTS, label, "emergency contact", ok),
        "term_add": lambda: term_add(settings, label, a("date"), a("until")),
        "term_list": lambda: term_list(settings),
        "term_remove": lambda: hh.remove(settings, TERMS, label, "date", ok),
    }
    if a("action") not in actions:
        raise ValueError("Unknown household family action.")
    return actions[a("action")]()
