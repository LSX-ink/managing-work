"""Shared bits for the health-plus abilities: small JSON files in the memory folder, dates, times and the safety line.

Every log lives in health-plus-<section>.json in the memory folder on this PC and nowhere else.
"""

import calendar
import json
import re
from datetime import date, datetime, timedelta

import homestore as hs
import memory
from config import Settings

SAFETY = "This is just a log, not medical advice; if anything worries you, contact your GP or NHS 111."
KEEP = 3000
clean, need, number, plural, spoken = hs.clean, hs.need, hs.number, hs.plural, hs.spoken


def now() -> datetime:
    return hs.now()


def today() -> date:
    return now().date()


def path(settings: Settings, section: str):
    return memory.root(settings) / f"health-plus-{section}.json"


def load(settings: Settings, section: str, default):
    try:
        found = json.loads(path(settings, section).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    if isinstance(default, list):
        return [x for x in found if isinstance(x, dict)] if isinstance(found, list) else default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, section: str, data) -> None:
    p = path(settings, section)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, list):
        data = data[-KEEP:]
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def day(value) -> date:
    """YYYY-MM-DD, today, yesterday, tomorrow or a weekday name."""
    return hs.parse_day(value, today())


def clock(value, what: str = "time") -> str:
    """'7:05', '19:30', '7pm', '7.30 am' -> '07:05' style."""
    m = re.fullmatch(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", clean(value).lower())
    if not m:
        raise ValueError(f"Give the {what} like 07:30 or 7:30 pm.")
    h, mins, half = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if half:
        if not 1 <= h <= 12:
            raise ValueError(f"That {what} doesn't look right.")
        h = h % 12 + (12 if half == "pm" else 0)
    if h > 23 or mins > 59:
        raise ValueError(f"That {what} doesn't look right.")
    return f"{h:02d}:{mins:02d}"


def stamp(when: datetime) -> str:
    return when.isoformat(timespec="minutes")


def at_for(value) -> str:
    """A timestamp: now, or the given day at the current time."""
    if not value:
        return stamp(now())
    return stamp(datetime.combine(day(value), now().time()))


def seconds(value, what: str = "time") -> int:
    """'25:30', '1:02:03' or a number of minutes -> seconds."""
    text = clean(value)
    if re.fullmatch(r"\d+(:\d{1,2}){1,2}", text):
        total = 0
        for part in text.split(":"):
            total = total * 60 + int(part)
        return total
    return round(number(text, what, 0.1, 6000) * 60)


def duration(total: float) -> str:
    total = round(total)
    h, m, s = total // 3600, total // 60 % 60, total % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def add_months(start: date, months: int) -> date:
    y, m = divmod(start.month - 1 + months, 12)
    y += start.year
    return date(y, m + 1, min(start.day, calendar.monthrange(y, m + 1)[1]))


def short(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"


def countdown(d: date) -> str:
    left = (d - today()).days
    if left == 0:
        return "today"
    if left == 1:
        return "tomorrow"
    return f"in {plural(left, 'day')}" if left > 0 else f"{plural(-left, 'day')} ago"


def week_days(end: date | None = None, days: int = 7) -> list[date]:
    end = end or today()
    return [end - timedelta(days=i) for i in range(days - 1, -1, -1)]


def find(items: list[dict], key: str, words) -> list[dict]:
    wanted = re.findall(r"\w+", clean(words).lower())
    return [i for i in items if wanted and all(w in str(i.get(key, "")).lower() for w in wanted)]
