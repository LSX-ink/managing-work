"""Shared bits for the calm abilities: small JSON files in the memory folder (calm-<section>.json), dates, tidy text
and the safety line. Nothing here is medical advice; anything that sounds like a crisis gets Samaritans and NHS 111.
"""

import json
import re
from datetime import date, datetime

import homestore as hs
import memory
from config import Settings

SAFETY = "This is a gentle everyday tool, not medical advice. If you're struggling, talk to your GP or call NHS 111."
SUPPORT = ("I'm really sorry you're feeling like this, and I'm glad you told me. You don't have to face it alone. "
           "Please call Samaritans free on 116 123, any time, day or night. If you might act on these thoughts or "
           "you're in danger, call 999. You can also call NHS 111 or speak to your GP. I'm here with you.")
CRISIS = re.compile(r"\b(suicid\w*|kill (?:my|him|her)self|end (?:it all|my life)|self[- ]?harm\w*|"
                    r"hurt(?:ing)? myself|cut(?:ting)? myself|want to die|better off dead|don'?t want to (?:be here|live))\b",
                    re.I)
clean, need, plural = hs.clean, hs.need, hs.plural


def now() -> datetime:
    return hs.now()


def today() -> date:
    return hs.today()


def path(settings: Settings, section: str):
    return memory.root(settings) / f"calm-{section}.json"


def load(settings: Settings, section: str, default):
    try:
        found = json.loads(path(settings, section).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, section: str, data) -> None:
    p = path(settings, section)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def in_crisis(*texts) -> bool:
    return any(CRISIS.search(str(t or "")) for t in texts)


def minutes(value, what: str = "minutes", low: float = 1, high: float = 240) -> float:
    return hs.number(value, what, low, high)


def day(value) -> date:
    return hs.parse_day(value, today())
