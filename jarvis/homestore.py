"""Shared bits for the home-and-life trackers: small JSON files in the memory folder, dates and tidy text."""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import memory
from config import Settings

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def now() -> datetime:
    return datetime.now()


def today() -> date:
    return now().date()


def path(settings: Settings, name: str) -> Path:
    return memory.root(settings) / name


def load(settings: Settings, name: str, default):
    try:
        found = json.loads(path(settings, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, name: str, data) -> None:
    p = path(settings, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clean(value, limit: int = 80) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def need(value, what: str, limit: int = 80) -> str:
    text = clean(value, limit)
    if not text:
        raise ValueError(f"Which {what}?")
    return text


def find(keys, name: str) -> str | None:
    """The key matching name exactly (ignoring case), else the only one containing it."""
    name = clean(name).lower()
    keys = list(keys)
    exact = next((k for k in keys if k.lower() == name), None)
    if exact is not None or not name:
        return exact
    part = [k for k in keys if name in k.lower()]
    return part[0] if len(part) == 1 else None


def number(value, what: str, low: float = 0, high: float = 1_000_000) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"The {what} must be a number.") from None
    if not low <= n <= high:
        raise ValueError(f"That {what} doesn't look right.")
    return n


def parse_day(value, base: date | None = None) -> date:
    """YYYY-MM-DD, 'today', 'tomorrow', 'yesterday' or a weekday name (that day this week)."""
    base = base or today()
    text = clean(value).lower()
    if not text or text == "today":
        return base
    if text == "tomorrow":
        return base + timedelta(days=1)
    if text == "yesterday":
        return base - timedelta(days=1)
    if text in WEEKDAYS:
        return week_start(base) + timedelta(days=WEEKDAYS.index(text))
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("Give the date as YYYY-MM-DD.") from None


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def spoken(day: date) -> str:
    return f"{day.strftime('%A')} {day.day} {day.strftime('%B')}"


def money(n: float, currency: str) -> str:
    return f"{n:,.2f} {currency}"


def plural(n: float, word: str, many: str = "") -> str:
    return f"{n:g} {word if n == 1 else many or word + 's'}"
