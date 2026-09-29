"""Shared bits for the everyday support abilities: one JSON file (support.json) in the memory folder.

Plans, routine ticks, important people, step guides, medicine confirmations, check-ins, handover notes and the
emergency card all live there and are never sent to any website.
"""

from datetime import datetime

import homestore as hs
from config import Settings

FILE = "support.json"
MAX_ITEMS = 60
MAX_LOG = 500
SECTIONS = {"plan": {}, "routines": {}, "ticks": {}, "people": {}, "guides": {}, "meds": {}, "medlog": [],
            "checkins": [], "handover": [], "emergency": {}, "contact": {}}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {k: found.get(k) if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def now(value=None) -> datetime:
    return value or hs.now()


def part_of_day(moment: datetime) -> str:
    return "morning" if moment.hour < 12 else "afternoon" if moment.hour < 18 else "evening"


def match(names, wanted, what: str) -> str:
    """The name that equals or contains what was asked for (ignoring case), or a friendly ValueError."""
    key = hs.find(names, hs.need(wanted, what))
    if key is None:
        have = f" I have: {', '.join(names)}." if names else ""
        raise ValueError(f"I don't have a {what} called {hs.clean(wanted)}.{have}")
    return key


def put(rows: list, item, limit: int = MAX_ITEMS) -> None:
    """Append to a list, refusing when it is full."""
    if len(rows) >= limit:
        raise ValueError("That list is full; remove something first.")
    rows.append(item)


def clock(value, what: str = "time") -> str:
    """HH:MM from '7', '7:30' or '19:05'."""
    text = hs.clean(value)
    hour, _, minute = text.partition(":")
    if not hour.isdigit() or not (minute or "0").isdigit() or int(hour) > 23 or int(minute or 0) > 59:
        raise ValueError(f"Give the {what} like 7:30 or 19:00.")
    return f"{int(hour):02d}:{int(minute or 0):02d}"
