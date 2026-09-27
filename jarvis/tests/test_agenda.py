import asyncio
import datetime as dt

import httpx

import agenda
from config import Settings

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:1
DTSTART:20260928T090000
DTEND:20260928T100000
SUMMARY:Site induction
LOCATION:Euston
END:VEVENT
BEGIN:VEVENT
UID:2
DTSTART;VALUE=DATE:20260929
SUMMARY:Lebo's birthday
END:VEVENT
BEGIN:VEVENT
UID:3
DTSTART:20260928T180000
DTEND:20260928T190000
RRULE:FREQ=DAILY;COUNT=3
SUMMARY:Gym
END:VEVENT
END:VCALENDAR
"""


def run(settings, days, now):
    agenda._cache.update(url="", at=0.0, cal=None)

    def handler(request):
        assert request.url.scheme == "https"
        return httpx.Response(200, content=ICS)

    async def main():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await agenda.upcoming(http, settings, days, now)
    return asyncio.run(main())


def test_calendar_days_and_repeats():
    s = Settings(calendar_url="webcal://example.com/basic.ics")
    now = dt.datetime(2026, 9, 28, 7, 0)
    assert run(s, 1, now) == "Today:\n  09:00 Site induction at Euston\n  18:00 Gym"
    two = run(s, 2, now)
    assert "Tomorrow:\n  all day Lebo's birthday\n  18:00 Gym" in two


def test_no_calendar_explains_setup():
    assert "JARVIS_CALENDAR_URL" in asyncio.run(agenda.upcoming(None, Settings(calendar_url=""), 1))
