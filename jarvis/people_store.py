"""Shared bits for the people notebook: the people-*.json files, finding a person by name, dates and countdowns.

Everything lives only in the memory folder on this PC (people-book.json and friends) and is never sent anywhere.
Birthdays come from birthdays.json (dates_saved) and gift ideas from gifts.json (homehouse), read-only.
"""

import re
from datetime import date

import homestore as hs
from config import Settings

BOOK = "people-book.json"
THANKS, PROMISES = "people-thanks.json", "people-promises.json"
CARDS, INVITES = "people-cards.json", "people-invites.json"
MAX_PEOPLE = 500
MAX_LOG = 200
FIELDS = ("how", "phone", "email", "address")
RELATIONS = ("parent", "child", "partner")


def book(settings: Settings) -> dict:
    return {k: v for k, v in hs.load(settings, BOOK, {}).items() if isinstance(v, dict)}


def save(settings: Settings, found: dict) -> None:
    hs.save(settings, BOOK, found)


def blank() -> dict:
    return {"how": "", "phone": "", "email": "", "address": "", "notes": [], "likes": [], "dislikes": [],
            "family": [], "groups": [], "every": 0, "contacts": [], "dates": {}, "parents": [], "children": [],
            "partners": []}


def person(found: dict, name) -> str:
    """The saved name matching name (ignoring case, or the only one containing it), else a friendly ValueError."""
    k = hs.find(found, hs.need(name, "person", 60))
    if k is None:
        raise ValueError(f"{hs.clean(name, 60)} isn't in your people notebook yet.")
    for key, value in blank().items():
        found[k].setdefault(key, value)
    return k


def entries(settings: Settings, name: str) -> list[dict]:
    return [e for e in hs.load(settings, name, []) if isinstance(e, dict)]


def known(settings: Settings, name) -> str:
    """The notebook's spelling of a name if they're in it, else the name as given."""
    name = hs.need(name, "person", 60)
    return hs.find(book(settings), name) or name


def words(items, limit: int = 50, size: int = 80) -> list[str]:
    out = {}
    for i in items if isinstance(items, list) else [items] if items else []:
        text = hs.clean(i, size)
        if text:
            out.setdefault(text.lower(), text)
    return list(out.values())[:limit]


def last_contact(p: dict) -> date | None:
    days = [c.get("date") for c in p.get("contacts", []) if c.get("date")]
    return date.fromisoformat(max(days)) if days else None


def overdue_days(p: dict, today: date) -> int | None:
    """Days past the keep-in-touch goal (0 = due today), or None if not due or no goal."""
    every = int(p.get("every") or 0)
    if not every:
        return None
    last = last_contact(p)
    if last is None:
        return 0
    late = (today - last).days - every
    return late if late >= 0 else None


def day_value(value) -> str:
    """'YYYY-MM-DD' or 'MM-DD' (every year, year unknown), checked."""
    value = hs.clean(value, 20).lstrip("-")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        date.fromisoformat(value)
        return value
    if re.fullmatch(r"\d{2}-\d{2}", value):
        date.fromisoformat(f"2000-{value}")
        return value
    raise ValueError("Give the date as YYYY-MM-DD, or MM-DD if you don't know the year.")


def next_date(value: str, today: date) -> tuple[date, int | None]:
    """The next time a yearly date comes round, and how many years it marks (None if the year isn't known)."""
    month, day = int(value[-5:-3]), int(value[-2:])
    for year in (today.year, today.year + 1):
        try:
            when = date(year, month, day)
        except ValueError:  # 29 February outside a leap year
            when = date(year, 2, 28)
        if when >= today:
            return when, (year - int(value[:4])) if len(value) == 10 else None
    raise AssertionError


def until(day: date, today: date) -> str:
    n = (day - today).days
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    return f"in {hs.plural(n, 'day')}" if n > 0 else f"{hs.plural(-n, 'day')} ago"


def ago(day: date | None, today: date) -> str:
    if day is None:
        return "never"
    n = (today - day).days
    return "today" if n == 0 else "yesterday" if n == 1 else f"{hs.plural(n, 'day')} ago"


def short(day: date) -> str:
    return f"{day.day} {day:%b %Y}"


def birthday(settings: Settings, name: str) -> str | None:
    saved = hs.load(settings, "birthdays.json", {})
    k = next((k for k in saved if k.lower() == name.lower()), None)
    try:
        return day_value(saved[k]) if k else None
    except ValueError:
        return None


def gifts(settings: Settings, name: str) -> list[str]:
    saved = hs.load(settings, "gifts.json", {})
    k = next((k for k in saved if k.lower() == name.lower()), None)
    return [str(g) for g in saved[k]] if k and isinstance(saved[k], list) else []
