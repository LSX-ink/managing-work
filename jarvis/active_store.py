"""Shared bits for the active abilities: one JSON file (active.json) in the memory folder holding the activity log,
strength log, saved routes and fitness challenges, plus tidy numbers, times and distances. Nothing here is medical advice.
"""

import json
import re

import homestore as hs
import memory
from config import Settings

SAFETY = "This is an everyday guide, not medical advice. Stop if something hurts, and check with your GP if unsure."
KM_PER_MILE = 1.609344
clean, need, plural = hs.clean, hs.need, hs.plural
now, today = hs.now, hs.today


def path(settings: Settings):
    return memory.root(settings) / "active.json"


def load(settings: Settings) -> dict:
    try:
        found = json.loads(path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def section(settings: Settings, name: str, default):
    found = load(settings).get(name)
    return found if isinstance(found, type(default)) else default


def save_section(settings: Settings, name: str, value) -> None:
    data = load(settings)
    data[name] = value
    p = path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def number(value, what: str, low: float = 0, high: float = 1_000_000) -> float:
    return hs.number(value, what, low, high)


def day(value):
    return hs.parse_day(value, today())


def duration(time=None, minutes=None) -> float:
    """Minutes from 'h:mm:ss', 'mm:ss', '27 minutes 45' or a plain number of minutes."""
    if time not in (None, ""):
        text = str(time).strip().lower()
        parts = re.findall(r"\d+(?:\.\d+)?", text)
        if ":" in text:
            nums = [float(p) for p in parts][:3]
            while len(nums) < 3:
                nums.insert(0, 0.0)
            return _sane(nums[0] * 60 + nums[1] + nums[2] / 60)
        if "h" in text and parts:
            return _sane(float(parts[0]) * 60 + (float(parts[1]) if len(parts) > 1 else 0))
        if "sec" in text and len(parts) == 1:
            return _sane(float(parts[0]) / 60)
        if len(parts) == 2:
            return _sane(float(parts[0]) + float(parts[1]) / 60)
        if len(parts) == 1:
            return _sane(float(parts[0]))
        raise ValueError("I couldn't read that time. Say it like 27:45 or 1:05:30.")
    if minutes in (None, ""):
        raise ValueError("How long did it take?")
    return _sane(number(minutes, "time"))


def _sane(mins: float) -> float:
    if not 0 < mins <= 24 * 60:
        raise ValueError("That time doesn't look right.")
    return mins


def km_from(distance, unit=None, what: str = "distance") -> float:
    km = number(distance, what, 0.001, 5000)
    return round(km * KM_PER_MILE, 3) if str(unit or "").lower().startswith("mi") else km


def clock(mins: float) -> str:
    """Minutes as 27:45 or 1:05:30."""
    total = round(mins * 60)
    h, rest = divmod(total, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def spoken_time(mins: float) -> str:
    total = round(mins * 60)
    h, rest = divmod(total, 3600)
    m, s = divmod(rest, 60)
    parts = [f"{h} hour{'s' if h != 1 else ''}"] if h else []
    if m:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if s and not h:
        parts.append(f"{s} second{'s' if s != 1 else ''}")
    return " ".join(parts) or "0 minutes"


def pace_text(km: float, mins: float) -> str:
    """'5:33 per km (8:56 per mile)'."""
    per_km = mins / km
    return f"{clock(per_km)} per km ({clock(per_km * KM_PER_MILE)} per mile)"


def speed_text(km: float, mins: float) -> str:
    kmh = km / (mins / 60)
    return f"{kmh:.1f} km/h ({kmh / KM_PER_MILE:.1f} mph)"


def dist_text(km: float) -> str:
    return f"{km:.1f} km ({km / KM_PER_MILE:.1f} miles)"
