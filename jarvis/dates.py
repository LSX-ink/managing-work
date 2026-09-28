"""Time and dates: world clock, time-zone conversion, date sums, week numbers, moon phase,
UK bank holidays (gov.uk) and sunrise and sunset (Open-Meteo).

Nothing is stored. Only city names go to Open-Meteo; bank holidays are one public gov.uk file,
kept in memory for a day.
"""

import math
import time
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone, tzinfo

import httpx

from config import Settings

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
BANK_HOLIDAYS_URL = "https://www.gov.uk/bank-holidays.json"
REGIONS = {"england": "england-and-wales", "wales": "england-and-wales", "england-and-wales": "england-and-wales",
           "scotland": "scotland", "northern-ireland": "northern-ireland", "northern ireland": "northern-ireland"}
CACHE_SECONDS = 24 * 3600
SYNODIC_MONTH = 29.530588853
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)

CITY_ZONES = {
    "london": "Europe/London", "uk": "Europe/London", "manchester": "Europe/London", "edinburgh": "Europe/London",
    "dublin": "Europe/Dublin", "paris": "Europe/Paris", "berlin": "Europe/Berlin", "madrid": "Europe/Madrid",
    "rome": "Europe/Rome", "amsterdam": "Europe/Amsterdam", "lisbon": "Europe/Lisbon", "athens": "Europe/Athens",
    "istanbul": "Europe/Istanbul", "moscow": "Europe/Moscow",
    "johannesburg": "Africa/Johannesburg", "joburg": "Africa/Johannesburg", "cape town": "Africa/Johannesburg",
    "durban": "Africa/Johannesburg", "pretoria": "Africa/Johannesburg", "south africa": "Africa/Johannesburg",
    "lagos": "Africa/Lagos", "nairobi": "Africa/Nairobi", "cairo": "Africa/Cairo", "harare": "Africa/Harare",
    "dubai": "Asia/Dubai", "abu dhabi": "Asia/Dubai", "doha": "Asia/Qatar", "riyadh": "Asia/Riyadh",
    "mumbai": "Asia/Kolkata", "delhi": "Asia/Kolkata", "new delhi": "Asia/Kolkata", "india": "Asia/Kolkata",
    "bangkok": "Asia/Bangkok", "singapore": "Asia/Singapore", "hong kong": "Asia/Hong_Kong",
    "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai", "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo",
    "seoul": "Asia/Seoul", "manila": "Asia/Manila",
    "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne", "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth", "auckland": "Pacific/Auckland", "new zealand": "Pacific/Auckland",
    "new york": "America/New_York", "nyc": "America/New_York", "boston": "America/New_York",
    "washington": "America/New_York", "miami": "America/New_York", "toronto": "America/Toronto",
    "chicago": "America/Chicago", "dallas": "America/Chicago", "houston": "America/Chicago",
    "denver": "America/Denver", "los angeles": "America/Los_Angeles", "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles", "seattle": "America/Los_Angeles", "vancouver": "America/Vancouver",
    "mexico city": "America/Mexico_City", "sao paulo": "America/Sao_Paulo", "buenos aires": "America/Argentina/Buenos_Aires",
    "honolulu": "Pacific/Honolulu", "utc": "UTC", "gmt": "UTC",
}

_holidays: dict = {"at": 0.0, "data": None}


def _day(value, default: date | None = None) -> date:
    value = str(value or "").strip()
    if not value:
        if default:
            return default
        raise ValueError("Which date? Give it as YYYY-MM-DD.")
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        raise ValueError("Give the date as YYYY-MM-DD, e.g. 2026-12-25.") from None


def _long(d: date) -> str:
    return f"{d:%A} {d.day} {d:%B %Y}"


def _plural(n: int, unit: str) -> str:
    return f"{n} {unit}{'' if n == 1 else 's'}"


async def _place(http: httpx.AsyncClient, city: str) -> dict:
    r = await http.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en", "format": "json"}, timeout=10)
    r.raise_for_status()
    places = r.json().get("results") or []
    if not places:
        raise ValueError(f"I couldn't find a place called {city}.")
    return places[0]


async def _zone(http: httpx.AsyncClient, where: str) -> tuple[str, tzinfo]:
    """(label, tzinfo) for a city, country or IANA zone name."""
    where = str(where or "").strip()
    if not where:
        local = datetime.now().astimezone().tzinfo
        return "here", local
    name = CITY_ZONES.get(where.lower())
    label = (where.upper() if len(where) <= 3 else where.title()) if name else where
    if not name and "/" in where:
        name = where
    if not name:
        place = await _place(http, where)
        name, label = place.get("timezone") or "UTC", place["name"]
    try:
        from zoneinfo import ZoneInfo
        return label, ZoneInfo(name)
    except Exception:  # Windows without the tzdata package: ask Open-Meteo for today's offset
        r = await http.get(FORECAST_URL, params={"latitude": 0, "longitude": 0, "timezone": name,
                                                 "current": "is_day", "forecast_days": 1}, timeout=10)
        r.raise_for_status()
        return label, timezone(timedelta(seconds=int(r.json().get("utc_offset_seconds") or 0)))


def _clock(t: datetime) -> str:
    return f"{t:%H:%M} on {t:%A} {t.day} {t:%B}"


async def world_clock(http: httpx.AsyncClient, where: str) -> str:
    label, tz = await _zone(http, where)
    now = datetime.now(tz)
    return f"It's {_clock(now)} in {label}." if label != "here" else f"It's {_clock(now)}."


async def convert(http: httpx.AsyncClient, at: str, source: str, target: str, day: date | None = None) -> str:
    try:
        hour, minute = (int(p) for p in str(at).strip().split(":")[:2])
    except ValueError:
        raise ValueError("Give the time as HH:MM in 24-hour form, e.g. 15:00.") from None
    src_label, src = await _zone(http, source)
    dst_label, dst = await _zone(http, target)
    day = day or datetime.now(src).date()
    start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=src)
    end = start.astimezone(dst)
    shift = "" if end.date() == start.date() else (" the next day" if end.date() > start.date() else " the day before")
    here = lambda label: "your time" if label == "here" else label  # noqa: E731
    return f"{start:%H:%M} {here(src_label)} is {end:%H:%M}{shift} {here(dst_label)}."


def days_until(target: date, today: date) -> str:
    n = (target - today).days
    if n == 0:
        return f"{_long(target)} is today."
    if n > 0:
        return f"{_plural(n, 'day')} until {_long(target)} (about {n / 7:.1f} weeks)."
    return f"{_long(target)} was {_plural(-n, 'day')} ago."


def between(start: date, end: date) -> str:
    if end < start:
        start, end = end, start
    years = end.year - start.year - ((end.month, end.day) < (start.month, start.day))
    anchor = _add_months(start, years * 12)
    months = 0
    while _add_months(anchor, months + 1) <= end:
        months += 1
    days = (end - _add_months(anchor, months)).days
    parts = [_plural(n, u) for n, u in ((years, "year"), (months, "month"), (days, "day")) if n] or ["0 days"]
    return (f"From {_long(start)} to {_long(end)} is {', '.join(parts)}, "
            f"or {(end - start).days:,} days in total.")


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def add(start: date, amount: int, unit: str) -> str:
    amount = int(amount)
    unit = (unit or "days").rstrip("s")
    if unit == "day":
        result = start + timedelta(days=amount)
    elif unit == "week":
        result = start + timedelta(weeks=amount)
    elif unit == "month":
        result = _add_months(start, amount)
    elif unit == "year":
        result = _add_months(start, amount * 12)
    else:
        raise ValueError("The unit must be days, weeks, months or years.")
    way = "after" if amount >= 0 else "before"
    return f"{_plural(abs(amount), unit)} {way} {_long(start)} is {_long(result)}."


def weekday(d: date, today: date) -> str:
    verb = "is" if d >= today else "was"
    return f"{d.day} {d:%B %Y} {verb} a {d:%A}."


def week_info(d: date) -> str:
    year_days = 366 if monthrange(d.year, 2)[1] == 29 else 365
    doy = d.timetuple().tm_yday
    return (f"{_long(d)} is in ISO week {d.isocalendar()[1]}, day {doy} of {d.year}, "
            f"with {_plural(year_days - doy, 'day')} left in the year.")


def moon(d: date) -> str:
    noon = datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc)
    age = ((noon - KNOWN_NEW_MOON).total_seconds() / 86400) % SYNODIC_MONTH
    lit = round((1 - math.cos(2 * math.pi * age / SYNODIC_MONTH)) / 2 * 100)
    names = ["new moon", "waxing crescent", "first quarter", "waxing gibbous",
             "full moon", "waning gibbous", "last quarter", "waning crescent"]
    phase = names[int((age / SYNODIC_MONTH) * 8 + 0.5) % 8]
    return f"On {_long(d)} the moon is a {phase}, about {lit}% lit."


async def _bank_holidays(http: httpx.AsyncClient) -> dict:
    if _holidays["data"] is None or time.time() - _holidays["at"] > CACHE_SECONDS:
        r = await http.get(BANK_HOLIDAYS_URL, timeout=10)
        r.raise_for_status()
        _holidays.update(data=r.json(), at=time.time())
    return _holidays["data"]


async def next_bank_holidays(http: httpx.AsyncClient, region: str, today: date, count: int = 3) -> list[tuple[date, str]]:
    key = REGIONS.get(str(region or "england").lower(), "england-and-wales")
    events = (await _bank_holidays(http)).get(key, {}).get("events") or []
    ahead = sorted((date.fromisoformat(e["date"]), e["title"]) for e in events if e.get("date", "") >= today.isoformat())
    return ahead[:max(1, min(int(count or 3), 10))]


async def bank_holidays(http: httpx.AsyncClient, region: str, today: date, count: int = 3) -> str:
    found = await next_bank_holidays(http, region, today, count)
    if not found:
        return "No upcoming bank holidays are listed yet."
    where = REGIONS.get(str(region or "england").lower(), "england-and-wales").replace("-", " ")
    return f"Next bank holidays in {where}: " + "; ".join(
        f"{title}, {_long(d)}, in {_plural((d - today).days, 'day')}" for d, title in found) + "."


async def sun(http: httpx.AsyncClient, city: str, d: date) -> str:
    if not city:
        return "Which city? No home city is set (JARVIS_CITY)."
    place = await _place(http, city)
    r = await http.get(FORECAST_URL, params={
        "latitude": place["latitude"], "longitude": place["longitude"], "daily": "sunrise,sunset",
        "timezone": "auto", "start_date": d.isoformat(), "end_date": d.isoformat()}, timeout=10)
    r.raise_for_status()
    daily = r.json()["daily"]
    rise, sets = (datetime.fromisoformat(daily[k][0]) for k in ("sunrise", "sunset"))
    length = sets - rise
    hours, minutes = divmod(int(length.total_seconds()) // 60, 60)
    return (f"In {place['name']} on {_long(d)}: sunrise {rise:%H:%M}, sunset {sets:%H:%M} (local time), "
            f"{hours} hours {minutes} minutes of daylight.")


async def today_summary(http: httpx.AsyncClient, today: date) -> str:
    text = f"Today is {_long(today)}, " + week_info(today).split(" is ", 1)[1]
    try:
        found = await next_bank_holidays(http, "england", today, 1)
    except (httpx.HTTPError, ValueError):
        found = []
    if found:
        d, title = found[0]
        text += f" Next bank holiday: {title} on {_long(d)}, in {_plural((d - today).days, 'day')}."
    return text


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "date_time",
        "description": "Time and date answers. action: 'clock' time now in place (city, country or zone); "
                       "'convert' time HH:MM in place to to_place (either blank = user's own time); 'until' days "
                       "until or since date; 'between' exact duration or age from date to date2 (default today); "
                       "'add' amount (negative subtracts) of unit to date (default today); 'weekday' day of the "
                       "week for date; 'week' ISO week number, day of year; 'moon' phase for date; 'today' "
                       "summary; 'bank_holidays' next UK bank holidays for region; 'sun' sunrise and sunset in "
                       "place (default home city) on date. Dates are YYYY-MM-DD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["clock", "convert", "until", "between", "add", "weekday",
                                                       "week", "moon", "today", "bank_holidays", "sun"]},
                "place": text, "to_place": text, "time": text, "date": text, "date2": text,
                "amount": {"type": "integer"},
                "unit": {"type": "string", "enum": ["days", "weeks", "months", "years"]},
                "region": {"type": "string", "enum": ["england-and-wales", "scotland", "northern-ireland"]},
                "count": {"type": "integer", "description": "How many bank holidays, 1 to 10. Default 3."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"date_time"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient, today: date | None = None) -> str:
    today = today or date.today()
    action = args.get("action")
    if action == "clock":
        return await world_clock(http, args.get("place") or "")
    if action == "convert":
        return await convert(http, args.get("time") or "", args.get("place") or "", args.get("to_place") or "")
    if action == "until":
        return days_until(_day(args.get("date")), today)
    if action == "between":
        return between(_day(args.get("date")), _day(args.get("date2"), today))
    if action == "add":
        return add(_day(args.get("date"), today), args.get("amount") or 0, args.get("unit") or "days")
    if action == "weekday":
        return weekday(_day(args.get("date"), today), today)
    if action == "week":
        return week_info(_day(args.get("date"), today))
    if action == "moon":
        return moon(_day(args.get("date"), today))
    if action == "bank_holidays":
        return await bank_holidays(http, args.get("region") or "england-and-wales", today, args.get("count") or 3)
    if action == "sun":
        return await sun(http, args.get("place") or settings.city, _day(args.get("date"), today))
    return await today_summary(http, today)
