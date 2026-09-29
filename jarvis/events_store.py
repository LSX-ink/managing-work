"""Shared bits for the events abilities: one JSON file (events.json) in the memory folder.

Every event (a party, wedding, Christmas...) keeps its guests, tasks, budget, suppliers, menu, tables and thank-yous
in there. Nothing is ever sent to a website; only a city goes to the weather forecast.
"""

from datetime import date

import homestore as hs
from config import Settings

FILE = "events.json"
KINDS = ["party", "birthday", "kids", "wedding", "christmas", "gathering", "holiday"]
RSVPS = ["yes", "no", "maybe", "pending"]
MAX_EVENTS = 40
MAX_ITEMS = 300


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    events = found.get("events")
    return {"events": events if isinstance(events, dict) else {}}


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def blank(day: date, kind: str, place: str, budget: float) -> dict:
    return {"date": day.isoformat(), "kind": kind, "place": place, "budget": budget, "guests": {}, "tasks": [],
            "budget_items": {}, "spends": [], "suppliers": {}, "menu": {}, "tables": {}, "thanks": {}, "setup": [],
            "notes": ""}


def pick(data: dict, name, today: date) -> tuple[dict, str]:
    """(the event, its key): the one named, else the only event, else the next one coming up."""
    events = data["events"]
    if not events:
        raise ValueError("You haven't got any events yet. Say what it is and when, like: plan Mia's party on 10 October.")
    if hs.clean(name):
        key = hs.find(events, name)
        if key is None:
            raise ValueError(f"I don't have an event called {hs.clean(name)}.")
        return events[key], key
    upcoming = sorted(events, key=lambda k: (events[k]["date"] < today.isoformat(), events[k]["date"]))
    return events[upcoming[0]], upcoming[0]


def days_to(event: dict, today: date) -> int:
    return (date.fromisoformat(event["date"]) - today).days


def countdown(days: int) -> str:
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days" if days > 0 else f"{-days} days ago"


def gbp(n: float) -> str:
    return f"£{n:,.2f}".replace(".00", "")


def headcount(event: dict) -> int:
    return sum(1 + g["plus"] for g in event["guests"].values() if g["rsvp"] == "yes")


def find_in(names, wanted, what: str) -> str:
    key = hs.find(names, hs.need(wanted, what))
    if key is None:
        raise ValueError(f"I can't find a {what} called {hs.clean(wanted)}.")
    return key


def money(value, what: str) -> float:
    return round(hs.number(value, what, 0, 1_000_000), 2)


def button(label: str, say: str) -> dict:
    return {"label": label, "say": say}
