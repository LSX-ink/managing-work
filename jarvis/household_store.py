"""Shared bits for the household-plus abilities: named rows in small JSON files, month sums and card helpers.

Built on homestore, so files live in the memory folder and dates follow the same rules (YYYY-MM-DD, 'today').
"""

import calendar
from datetime import date

import homestore as hs
from config import Settings

MAX_ROWS = 200


def rows(settings: Settings, name: str) -> dict:
    return {k: v for k, v in hs.load(settings, name, {}).items() if isinstance(v, (dict, list))}


def put(settings: Settings, name: str, found: dict, key: str, value) -> None:
    if key not in found and len(found) >= MAX_ROWS:
        raise ValueError("That list is full; remove something first.")
    found[key] = value
    hs.save(settings, name, found)


def key(found: dict, label, what: str) -> str:
    k = hs.find(found, hs.need(label, what))
    if k is None:
        raise ValueError(f"I haven't got a {what} called {hs.clean(label)}.")
    return k


def remove(settings: Settings, name: str, label, what: str, confirmed: bool) -> str:
    found = rows(settings, name)
    k = key(found, label, what)
    if not confirmed:
        return f"Ask the user to confirm removing the {k} {what}, then call again with confirmed true."
    del found[k]
    hs.save(settings, name, found)
    return f"Removed the {k} {what}."


def words(items, limit: int = 50, size: int = 80) -> list[str]:
    """Tidy, non-empty entries, each once (ignoring case)."""
    out = {}
    for i in items or []:
        text = hs.clean(i, size)
        if text:
            out.setdefault(text.lower(), text)
    return list(out.values())[:limit]


def add_months(day: date, months: int) -> date:
    total = day.month - 1 + months
    year, month = day.year + total // 12, total % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def month_end(day: date) -> date:
    return date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def short(day: date) -> str:
    return f"{day.day} {day.strftime('%b')} {day.year}"


def until(day: date, today: date) -> str:
    """'today', 'tomorrow', 'in 5 days', '3 days ago'."""
    n = (day - today).days
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    return f"in {hs.plural(n, 'day')}" if n > 0 else f"{hs.plural(-n, 'day')} ago"

