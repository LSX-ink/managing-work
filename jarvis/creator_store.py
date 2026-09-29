"""Shared bits for the creator-ideas abilities: one JSON file (creatorideas.json) in the memory folder.

Pillars, the idea bank, hashtag sets, series, trend notes, the swipe file and saved hooks and CTAs live there. It is
planning and notes only: nothing is posted anywhere and nothing leaves the PC.
"""

from datetime import datetime

import homestore as hs
from config import Settings

FILE = "creatorideas.json"
MAX_ITEMS = 300
STATUSES = ["idea", "scripted", "ready", "used"]
TREND_DAYS = 14
SECTIONS = {"pillars": {}, "ideas": [], "next_id": 1, "hashtags": {}, "series": {}, "trends": [], "swipe": [],
            "ctas": [], "hooks": []}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    data = {k: found[k] if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}
    data["next_id"] = data["next_id"] or 1
    return data


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def now(value=None) -> datetime:
    return value or hs.now()


def put(rows: list, item, limit: int = MAX_ITEMS) -> None:
    if len(rows) >= limit:
        raise ValueError("That list is full; remove something first.")
    rows.append(item)


def texts(values, limit: int = 60) -> list[str]:
    """A tidy list of unique short strings from a list (or one comma-separated string)."""
    if isinstance(values, str):
        values = values.split(",")
    out: list[str] = []
    for v in values or []:
        text = hs.clean(v, limit)
        if text and text.lower() not in [o.lower() for o in out]:
            out.append(text)
    return out


def tag(value) -> str:
    return hs.clean(value, 40).lstrip("#").replace(" ", "").lower()


def words(text: str) -> int:
    return len(str(text or "").split())


def confirm_needed(what: str) -> str:
    return f"Ask the user to confirm removing {what}. Only after a yes, call again with confirmed true."
