"""Special dates, thank-yous and promises: anniversaries per person with countdowns, gifts and favours still to
say thank you for, and favours owed either way.

Saved only in people-book.json, people-thanks.json and people-promises.json in the memory folder.
"""

from datetime import date

import homestore as hs
import people_store as ps
import screen
from config import Settings

MAX_ENTRIES = 300
KINDS = ("gift", "favour")
DIRECTIONS = ("i_owe", "they_owe")


# Special dates (not birthdays: those live with dates_saved)

def date_add(settings: Settings, name, label, when) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    label = hs.need(label, "occasion", 40).lower()
    if label in ("birthday", "birthdays"):
        raise ValueError("Birthdays have their own list: save it with the birthdays ability instead.")
    value = ps.day_value(when)
    dates = found[k]["dates"]
    if label not in dates and len(dates) >= 20:
        raise ValueError(f"{k} already has 20 dates; remove one first.")
    dates[label] = value
    ps.save(settings, found)
    day, years = ps.next_date(value, hs.today())
    marks = f", {years} years" if years else ""
    return f"Saved {k}'s {label}: next on {hs.spoken(day)}, {ps.until(day, hs.today())}{marks}."


def date_list(settings: Settings, name=None) -> screen.Shown | str:
    found = ps.book(settings)
    today = hs.today()
    keys = [ps.person(found, name)] if name else list(found)
    soon = sorted(((*ps.next_date(v, today), k, label) for k in keys for label, v in found[k].get("dates", {}).items()),
                  key=lambda x: (x[0], x[2].lower(), x[3]))
    if not soon:
        return "No special dates saved yet. Say something like 'Sam and Alex's wedding anniversary is 2015-06-20'."
    card = screen.card("table", "Special dates", f"people-dates-{(name or '').lower()}",
                       columns=["Who", "What", "Date", "When", "Years"],
                       rows=[[k, label, ps.short(day), ps.until(day, today), str(years or "")]
                             for day, years, k, label in soon])
    day, _, k, label = soon[0]
    return screen.Shown(f"Next up: {k}'s {label}, {ps.until(day, today)}.", card)


def date_remove(settings: Settings, name, label, confirmed: bool) -> str:
    found = ps.book(settings)
    k = ps.person(found, name)
    have = hs.find(found[k]["dates"], hs.need(label, "occasion", 40))
    if have is None:
        raise ValueError(f"{k} has no date called {hs.clean(label, 40)}.")
    if not confirmed:
        return f"Ask the user to confirm removing {k}'s {have}, then call again with confirmed true."
    del found[k]["dates"][have]
    ps.save(settings, found)
    return f"Removed {k}'s {have}."


# Thank-you tracker

def thanks_add(settings: Settings, name, what, kind=None, when=None) -> str:
    who = ps.known(settings, name)
    what = hs.need(what, "gift or favour", 120)
    found = ps.entries(settings, ps.THANKS)
    if len(found) >= MAX_ENTRIES:
        found = [t for t in found if not t.get("sent")] or found[1:]
    found.append({"person": who, "what": what, "kind": kind if kind in KINDS else "gift",
                  "date": hs.parse_day(when).isoformat(), "sent": ""})
    hs.save(settings, ps.THANKS, found[-MAX_ENTRIES:])
    open_ = sum(not t["sent"] for t in found)
    return f"Noted {what} from {who}. {hs.plural(open_, 'thank-you')} still to send."


def _pick(found: list[dict], name, what, done_key: str, what_label: str) -> dict:
    who = hs.need(name, "person", 60).lower()
    mine = [e for e in found if who in e.get("person", "").lower() and not e.get(done_key)]
    if what:
        mine = [e for e in mine if hs.clean(what).lower() in e.get("what", "").lower()] or mine
    if not mine:
        raise ValueError(f"There's no open {what_label} for {hs.clean(name, 60)}.")
    if len(mine) > 1 and not what:
        raise ValueError(f"{hs.clean(name, 60)} has {len(mine)} open; which one: " +
                         "; ".join(e["what"] for e in mine) + "?")
    return mine[0]


def thanks_sent(settings: Settings, name, what=None) -> str:
    found = ps.entries(settings, ps.THANKS)
    entry = _pick(found, name, what, "sent", "thank-you")
    entry["sent"] = hs.today().isoformat()
    hs.save(settings, ps.THANKS, found)
    left = sum(not t["sent"] for t in found)
    return f"Thank-you to {entry['person']} for {entry['what']} sent. {hs.plural(left, 'thank-you')} left."


def thanks_list(settings: Settings) -> screen.Shown | str:
    found = ps.entries(settings, ps.THANKS)
    if not found:
        return "No gifts or favours on the thank-you list."
    todo = [t for t in found if not t.get("sent")]
    shown = todo + [t for t in reversed(found) if t.get("sent")][:20]
    items = [{"label": f"{t['person']}: {t['what']} ({t.get('kind', 'gift')}, {ps.short(date.fromisoformat(t['date']))})",
              "done": bool(t.get("sent")), "say": f"I've sent the thank-you to {t['person']} for {t['what']}."}
             for t in shown]
    card = screen.card("list", "Thank-yous", "people-thanks", items=items, checks=True)
    if not todo:
        return screen.Shown("All your thank-yous are sent.", card)
    return screen.Shown(f"{hs.plural(len(todo), 'thank-you')} to send, the oldest to {todo[0]['person']}.", card)


# Promises and favours owed

def promise_add(settings: Settings, name, what, due=None, direction=None) -> str:
    who = ps.known(settings, name)
    what = hs.need(what, "promise", 160)
    found = ps.entries(settings, ps.PROMISES)
    if len(found) >= MAX_ENTRIES:
        found = [p for p in found if not p.get("done")] or found[1:]
    entry = {"person": who, "what": what, "direction": direction if direction in DIRECTIONS else "i_owe",
             "made": hs.today().isoformat(), "due": hs.parse_day(due).isoformat() if due else "", "done": ""}
    found.append(entry)
    hs.save(settings, ps.PROMISES, found[-MAX_ENTRIES:])
    by = f" by {hs.spoken(date.fromisoformat(entry['due']))}" if entry["due"] else ""
    return (f"Noted: you promised {who} {what}{by}." if entry["direction"] == "i_owe"
            else f"Noted: {who} owes you {what}{by}.")


def promise_done(settings: Settings, name, what=None) -> str:
    found = ps.entries(settings, ps.PROMISES)
    entry = _pick(found, name, what, "done", "promise")
    entry["done"] = hs.today().isoformat()
    hs.save(settings, ps.PROMISES, found)
    return f"Ticked off {entry['what']} for {entry['person']}."


def promise_list(settings: Settings) -> screen.Shown | str:
    found = [p for p in ps.entries(settings, ps.PROMISES) if not p.get("done")]
    if not found:
        return "No promises or favours outstanding."
    today = hs.today()
    found.sort(key=lambda p: (p.get("due") or "9999", p["made"]))

    def label(p):
        side = "You owe" if p["direction"] == "i_owe" else "Owes you"
        due = f", due {ps.until(date.fromisoformat(p['due']), today)}" if p.get("due") else ""
        return f"{side} - {p['person']}: {p['what']}{due}"

    items = [{"label": label(p), "say": f"Tick off the promise to {p['person']}: {p['what']}."} for p in found]
    card = screen.card("list", "Promises and favours", "people-promises", items=items, checks=True)
    mine = sum(p["direction"] == "i_owe" for p in found)
    late = sum(bool(p.get("due")) and p["due"] < today.isoformat() for p in found)
    return screen.Shown(f"You owe {mine}, others owe you {len(found) - mine}" + (f"; {late} overdue." if late else "."),
                        card)


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "people_occasions",
        "description": "Per-person special dates, thank-you tracker and promises. date_add anniversary or special "
                       "date that isn't a birthday (name, label e.g. 'wedding anniversary', date YYYY-MM-DD or MM-DD), "
                       "dates (countdown table, optional name), date_remove. thanks_add gift or favour received "
                       "(name, what, kind), thanks_sent ('I've sent Gran a thank-you for the scarf'), thanks "
                       "(tick-list). promise_add promise or favour owed (name, what, optional due date, direction "
                       "i_owe or they_owe), promise_done, promises (tick-list). Set confirmed true only after the "
                       "user confirms a date_remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["date_add", "dates", "date_remove", "thanks_add", "thanks_sent",
                                                      "thanks", "promise_add", "promise_done", "promises"]},
                "name": {"type": "string", "description": "The person."},
                "label": text,
                "date": {"type": "string", "description": "YYYY-MM-DD, MM-DD for yearly dates, or 'today'."},
                "what": text,
                "kind": {"type": "string", "enum": list(KINDS)},
                "direction": {"type": "string", "enum": list(DIRECTIONS)},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"people_occasions"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    who = a("name")
    actions = {
        "date_add": lambda: date_add(settings, who, a("label"), a("date")),
        "dates": lambda: date_list(settings, who),
        "date_remove": lambda: date_remove(settings, who, a("label"), bool(a("confirmed"))),
        "thanks_add": lambda: thanks_add(settings, who, a("what"), a("kind"), a("date")),
        "thanks_sent": lambda: thanks_sent(settings, who, a("what")),
        "thanks": lambda: thanks_list(settings),
        "promise_add": lambda: promise_add(settings, who, a("what"), a("date"), a("direction")),
        "promise_done": lambda: promise_done(settings, who, a("what")),
        "promises": lambda: promise_list(settings),
    }
    if a("action") not in actions:
        raise ValueError("Unknown occasions action.")
    return actions[a("action")]()
