"""Shared helpers for the learning-and-goals abilities.

Each ability keeps a small JSON file named growth-<name>.json in the memory folder.
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import memory
from config import Settings


def today() -> date:
    return date.today()


def path(settings: Settings, name: str) -> Path:
    return memory.root(settings) / f"growth-{name}.json"


def load(settings: Settings, name: str, default):
    try:
        found = json.loads(path(settings, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, name: str, data) -> None:
    p = path(settings, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clean(text, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def need(text, what: str, limit: int = 200) -> str:
    text = clean(text, limit)
    if not text:
        raise ValueError(f"Which {what}?")
    return text


def find(items: list[dict], key: str, text: str) -> dict | None:
    """An item whose key matches text exactly (any case), or else the first that contains it."""
    text = clean(text).lower()
    if not text:
        return None
    exact = next((i for i in items if i[key].lower() == text), None)
    return exact or next((i for i in items if text in i[key].lower()), None)


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def this_week(day_text: str, day: date) -> bool:
    return week_start(day).isoformat() <= day_text[:10] <= day.isoformat()


def plural(n: float, word: str) -> str:
    n_text = f"{n:g}" if isinstance(n, float) else f"{n:,}"
    return f"{n_text} {word}{'' if n == 1 else 's'}"


def number(value, what: str) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"I need a number for the {what}.") from None
    if n < 0 or n > 1e9:
        raise ValueError(f"That {what} doesn't look right.")
    return n
