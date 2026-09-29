"""Shared bits for the career abilities: career-*.json files in the memory folder, dates and name matching.

Files: career-applications.json, career-star.json, career-brag.json, career-offers.json, career-skills.json,
career-contacts.json, career-goals.json and career-cover.json. Everything stays on this PC.
"""

import json
import re
from datetime import date, datetime, timedelta

import memory
from config import Settings

APPLICATIONS = "career-applications.json"
STAR = "career-star.json"
BRAG = "career-brag.json"
OFFERS = "career-offers.json"
SKILLS = "career-skills.json"
CONTACTS = "career-contacts.json"
GOALS = "career-goals.json"
COVER = "career-cover.json"
MAX_ROWS = 300


def today() -> date:
    return datetime.now().date()


def load(settings: Settings, name: str, default):
    try:
        found = json.loads((memory.root(settings) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, name: str, data) -> None:
    path = memory.root(settings) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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


def parse_date(value, what: str = "date") -> date | None:
    text = clean(value).lower()
    if not text:
        return None
    offsets = {"today": 0, "tomorrow": 1, "yesterday": -1, "next week": 7}
    if text in offsets:
        return today() + timedelta(days=offsets[text])
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Give the {what} as YYYY-MM-DD.") from None


def until(day: date, ref: date | None = None) -> str:
    n = (day - (ref or today())).days
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    if n == -1:
        return "1 day overdue"
    return f"in {n} days" if n > 0 else f"{-n} days overdue"


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def short(day: date) -> str:
    return f"{day.day} {day.strftime('%b')}"
