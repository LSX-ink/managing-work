"""Shared bits for the home-admin abilities: one JSON file (homeadmin.json) in the memory folder, never sent anywhere.

Returns, warranties, subscriptions, documents, gifts, service logs, checklists and the emergency card all live there.
"""

from datetime import date

import homestore as hs
import household_store as hh
import screen
from config import Settings

FILE = "homeadmin.json"
MAX_ITEMS = 300
SECTIONS = {"gifts": [], "budgets": {}, "returns": [], "warranties": [], "subs": [], "docs": [], "services": {},
            "photos": {}, "ticks": {}, "extra_jobs": [], "checks": {}, "custom": {}, "emergency": {}, "appliances": {}}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {k: found.get(k) if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def add(rows: list, row: dict) -> list:
    if len(rows) >= MAX_ITEMS:
        raise ValueError("That list is full; remove something first.")
    return rows + [row]


def match(names, wanted, what: str) -> str:
    key = hs.find(names, hs.need(wanted, what))
    if key is None:
        many = [n for n in names if hs.clean(wanted).lower() in n.lower()]
        if many:
            raise ValueError(f"Which {what}: {'; '.join(many[:4])}?")
        raise ValueError(f"I don't have a {what} called {hs.clean(wanted)}.")
    return key


def index(rows: list[dict], wanted, what: str, field: str = "name") -> int:
    """Position of the row whose field matches (exactly or by one partial match), or a friendly ValueError."""
    names = [r[field] for r in rows]
    return names.index(match(names, wanted, what))


def optional_day(value) -> str:
    return hs.parse_day(value).isoformat() if hs.clean(value) else ""


def receipt(settings: Settings, value) -> str:
    """A file path inside the memory folders, checked to exist; empty when none was given."""
    if not hs.clean(value, 300):
        return ""
    path = screen.memory_path(settings, value)
    return path.relative_to(hs.path(settings, "").resolve()).as_posix()


def file_button(path: str, label: str = "Show file") -> list[dict]:
    if not path:
        return []
    parts = path.rsplit("/", 1)
    folder = f" from {parts[0]}" if len(parts) == 2 else ""
    return [{"label": label, "say": f"Show me the file {parts[-1]}{folder}."}]


def money(n: float, settings: Settings) -> str:
    return hs.money(n, settings.currency)


def when(day: date, today: date) -> str:
    return hh.until(day, today)
