"""The user's calendar, read from its private iCal address (JARVIS_CALENDAR_URL).

Google Calendar: Settings > your calendar > Integrate calendar > "Secret address in iCal format".
Outlook: Settings > Calendar > Shared calendars > Publish a calendar > ICS link. iCloud: share the calendar
as a public link. The address is read-only, so Alfred can see events but never change them.
"""

import datetime as dt
import time

import httpx
import icalendar
import recurring_ical_events

from config import Settings

CACHE_SECONDS = 300
MAX_EVENTS = 40
_cache: dict = {"url": "", "at": 0.0, "cal": None}


def configured(settings: Settings) -> bool:
    return bool(settings.calendar_url)


async def _calendar(http: httpx.AsyncClient, settings: Settings):
    url = settings.calendar_url.replace("webcal://", "https://", 1)
    if _cache["url"] == url and time.monotonic() - _cache["at"] < CACHE_SECONDS:
        return _cache["cal"]
    resp = await http.get(url, follow_redirects=True)
    resp.raise_for_status()
    cal = icalendar.Calendar.from_ical(resp.content)
    _cache.update(url=url, at=time.monotonic(), cal=cal)
    return cal


def _local(value) -> tuple[dt.datetime, bool]:
    """An event time as a naive local datetime, and whether it's an all-day event."""
    if isinstance(value, dt.datetime):
        return (value.astimezone().replace(tzinfo=None) if value.tzinfo else value), False
    return dt.datetime.combine(value, dt.time()), True


def events_between(cal, start: dt.datetime, end: dt.datetime) -> list[dict]:
    found = []
    for ev in recurring_ical_events.of(cal).between(start, end):
        begins, all_day = _local(ev.get("DTSTART").dt)
        found.append({"start": begins, "all_day": all_day, "title": str(ev.get("SUMMARY") or "(no title)"),
                      "where": str(ev.get("LOCATION") or "")})
    return sorted(found, key=lambda e: (e["start"], not e["all_day"]))[:MAX_EVENTS]


def describe(events: list[dict], now: dt.datetime) -> str:
    if not events:
        return "Nothing in the calendar."
    lines, day = [], None
    for e in events:
        d = e["start"].date()
        if d != day:
            day = d
            name = "Today" if d == now.date() else "Tomorrow" if d == now.date() + dt.timedelta(days=1) else f"{d:%A} {d.day} {d:%B}"
            lines.append(f"{name}:")
        when = "all day" if e["all_day"] else e["start"].strftime("%H:%M")
        where = f" at {e['where']}" if e["where"] else ""
        lines.append(f"  {when} {e['title']}{where}")
    return "\n".join(lines)


async def upcoming(http: httpx.AsyncClient, settings: Settings, days: int = 1, now: dt.datetime | None = None) -> str:
    if not configured(settings):
        return ("No calendar is connected. The user can add their calendar's private iCal address as "
                "JARVIS_CALENDAR_URL in .env (the README says where to find it).")
    now = now or dt.datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    cal = await _calendar(http, settings)
    return describe(events_between(cal, start, start + dt.timedelta(days=days)), now)


def tool_definitions() -> list[dict]:
    return [{
        "name": "get_calendar",
        "description": "Events in the user's calendar from today for the given number of days: 'what's on today', "
                       "'am I free Friday', 'what's my week like'. Read-only.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "How many days from today, 1 to 31. Default 1."}},
            "additionalProperties": False,
        },
    }]


NAMES = {"get_calendar"}
