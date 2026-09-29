"""Shared bits for the pets and garden abilities: one JSON file (petsgarden.json) in the memory folder.

Pets, harvests, seed packets and raised beds all live there and are never sent to any website.
"""

from datetime import date

import homestore as hs
from config import Settings

FILE = "petsgarden.json"
MAX_ITEMS = 300
SECTIONS = {"pets": {}, "harvest": [], "seeds": [], "beds": {}}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {k: found.get(k) if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def month_number(value, today: date) -> int:
    """1 to 12 from a number or a month name (or short name); the current month when empty."""
    text = hs.clean(value).lower()
    if not text:
        return today.month
    if text.isdigit() and 1 <= int(text) <= 12:
        return int(text)
    for i, name in enumerate(MONTH_NAMES):
        if len(text) >= 3 and name.lower().startswith(text):
            return i + 1
    raise ValueError("Which month? Say a name like March, or a number from 1 to 12.")


MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]


def match(names, wanted, what: str) -> str:
    """The name that equals or contains what was asked for (ignoring case), or a friendly ValueError."""
    key = hs.find(names, hs.need(wanted, what))
    if key is None:
        raise ValueError(f"I don't have a {what} called {hs.clean(wanted)}.")
    return key
