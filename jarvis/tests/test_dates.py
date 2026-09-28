import asyncio
import json
from datetime import date, datetime, timedelta

import httpx
import pytest

import dates
import dates_saved
import timers
import tools
from config import Settings

DAY = date(2026, 9, 28)
HOLIDAYS = {
    "england-and-wales": {"division": "england-and-wales", "events": [
        {"title": "Summer bank holiday", "date": "2026-08-31"},
        {"title": "Christmas Day", "date": "2026-12-25"},
        {"title": "Boxing Day", "date": "2026-12-28"},
    ]},
    "scotland": {"division": "scotland", "events": [{"title": "St Andrew's Day", "date": "2026-11-30"}]},
}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "www.gov.uk":
        handler.gov += 1
        return httpx.Response(200, json=HOLIDAYS)
    if request.url.host == "geocoding-api.open-meteo.com":
        if request.url.params["name"] == "Nowhere":
            return httpx.Response(200, json={})
        return httpx.Response(200, json={"results": [{"name": "Reykjavik", "latitude": 64.1, "longitude": -21.9,
                                                      "timezone": "Atlantic/Reykjavik", "country": "Iceland"}]})
    if "daily" not in request.url.params:  # the no-tzdata offset lookup
        assert request.url.params["timezone"] == "Asia/Tokyo"
        return httpx.Response(200, json={"utc_offset_seconds": 32400})
    assert request.url.params["daily"] == "sunrise,sunset"
    return httpx.Response(200, json={"daily": {"time": ["2026-09-28"], "sunrise": ["2026-09-28T07:15"],
                                               "sunset": ["2026-09-28T19:05"]}})


handler.gov = 0


def run(args: dict, settings: Settings | None = None, today: date = DAY) -> str:
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await dates.run_tool("date_time", args, settings or Settings(city="London"), http, today)
    return asyncio.run(go())


@pytest.fixture(autouse=True)
def clear_state():
    dates._holidays.update(at=0.0, data=None)
    handler.gov = 0
    dates_saved.stopwatch.update(started=None, elapsed=0.0, laps=[])
    yield
    for t in timers.timers.values():
        if t.task:
            t.task.cancel()
    timers.timers.clear()


def test_registered():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"date_time", "saved_dates", "focus_clock"} <= names
    assert dates in tools.ABILITIES and dates_saved in tools.ABILITIES


def test_world_clock():
    assert run({"action": "clock", "place": "Tokyo"}).startswith("It's ")
    assert run({"action": "clock", "place": "tokyo"}).endswith(" in Tokyo.")
    assert run({"action": "clock", "place": "Reykjavik"}).endswith(" in Reykjavik.")  # via geocoding
    assert " in " not in run({"action": "clock"})
    with pytest.raises(ValueError, match="couldn't find"):
        run({"action": "clock", "place": "Nowhere"})


def test_convert_time():
    async def go(*a):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await dates.convert(http, *a, day=DAY)
    assert asyncio.run(go("15:00", "London", "Johannesburg")) == "15:00 London is 16:00 Johannesburg."
    assert asyncio.run(go("15:00", "London", "Sydney")) == "15:00 London is 00:00 the next day Sydney."
    assert asyncio.run(go("09:30", "New York", "LA")) == "09:30 New York is 06:30 LA."
    with pytest.raises(ValueError):
        asyncio.run(go("3pm", "London", "Tokyo"))


def test_clock_without_tzdata(monkeypatch):
    import zoneinfo

    def missing(name):
        raise zoneinfo.ZoneInfoNotFoundError(name)
    monkeypatch.setattr(zoneinfo, "ZoneInfo", missing)
    assert run({"action": "clock", "place": "Tokyo"}).endswith(" in Tokyo.")


def test_until_and_since():
    assert run({"action": "until", "date": "2026-12-25"}) == \
        "88 days until Friday 25 December 2026 (about 12.6 weeks)."
    assert run({"action": "until", "date": "2026-09-27"}) == "Sunday 27 September 2026 was 1 day ago."
    assert run({"action": "until", "date": "2026-09-28"}) == "Monday 28 September 2026 is today."
    with pytest.raises(ValueError):
        run({"action": "until", "date": "Christmas"})


def test_between_and_age():
    assert run({"action": "between", "date": "1990-04-12"}) == \
        "From Thursday 12 April 1990 to Monday 28 September 2026 is 36 years, 5 months, 16 days, or 13,318 days in total."
    assert run({"action": "between", "date": "2026-01-31", "date2": "2026-03-01"}) == \
        "From Saturday 31 January 2026 to Sunday 1 March 2026 is 1 month, 1 day, or 29 days in total."


def test_add_dates():
    assert run({"action": "add", "amount": 90, "unit": "days"}) == \
        "90 days after Monday 28 September 2026 is Sunday 27 December 2026."
    assert run({"action": "add", "date": "2026-01-31", "amount": 1, "unit": "months"}) == \
        "1 month after Saturday 31 January 2026 is Saturday 28 February 2026."
    assert run({"action": "add", "amount": -2, "unit": "weeks"}) == \
        "2 weeks before Monday 28 September 2026 is Monday 14 September 2026."
    assert "2027" in run({"action": "add", "amount": 1, "unit": "years"})


def test_weekday_and_week():
    assert run({"action": "weekday", "date": "1990-04-12"}) == "12 April 1990 was a Thursday."
    assert run({"action": "weekday", "date": "2026-12-25"}) == "25 December 2026 is a Friday."
    assert run({"action": "week"}) == \
        "Monday 28 September 2026 is in ISO week 40, day 271 of 2026, with 94 days left in the year."


def test_moon_phase():
    assert run({"action": "moon", "date": "2024-04-08"}).startswith("On Monday 8 April 2024 the moon is a new moon, about 0%")
    full = run({"action": "moon", "date": "2024-04-23"})
    assert "full moon" in full and ("99%" in full or "100%" in full)


def test_bank_holidays_cached():
    assert run({"action": "bank_holidays"}) == (
        "Next bank holidays in england and wales: Christmas Day, Friday 25 December 2026, in 88 days; "
        "Boxing Day, Monday 28 December 2026, in 91 days.")
    assert "St Andrew's Day" in run({"action": "bank_holidays", "region": "scotland", "count": 1})
    assert handler.gov == 1
    assert run({"action": "bank_holidays", "region": "northern-ireland"}) == "No upcoming bank holidays are listed yet."


def test_sunrise_sunset():
    assert run({"action": "sun", "place": "Reykjavik"}) == (
        "In Reykjavik on Monday 28 September 2026: sunrise 07:15, sunset 19:05 (local time), "
        "11 hours 50 minutes of daylight.")
    assert "Reykjavik" in run({"action": "sun"}, Settings(city="Reykjavik"))
    assert run({"action": "sun"}, Settings(city="")).startswith("Which city?")


def test_today_summary():
    assert run({"action": "today"}) == (
        "Today is Monday 28 September 2026, in ISO week 40, day 271 of 2026, with 94 days left in the year. "
        "Next bank holiday: Christmas Day on Friday 25 December 2026, in 88 days.")


def test_countdowns(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert dates_saved.add(s, "countdown", "Holiday in Cape Town", "2026-12-18") == \
        "Saved the countdown to Holiday in Cape Town."
    dates_saved.add(s, "countdown", "Exam", "2026-09-20")
    assert dates_saved.list_countdowns(s, DAY) == (
        "Countdowns:\n- Exam: Sunday 20 September 2026, 8 days ago\n"
        "- Holiday in Cape Town: Friday 18 December 2026, 81 days left")
    assert "confirm" in dates_saved.remove(s, "countdown", "exam", False)
    assert dates_saved.remove(s, "countdown", "exam", True) == "Removed the countdown for Exam."
    assert dates_saved.remove(s, "countdown", "exam", True) == "There's no countdown called exam."
    assert list(json.loads((tmp_path / "countdowns.json").read_text())) == ["Holiday in Cape Town"]
    with pytest.raises(ValueError):
        dates_saved.add(s, "countdown", "Party", "next Friday")


def test_birthdays(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert dates_saved.add(s, "birthday", "Mum", "1965-10-03") == "Saved Mum's birthday."
    dates_saved.add(s, "birthday", "Sam", "--09-28")
    dates_saved.add(s, "birthday", "Leap", "2004-02-29")
    assert dates_saved.list_birthdays(s, DAY) == (
        "Next birthdays, soonest first:\n- Sam: Monday 28 September 2026, today\n"
        "- Mum: Saturday 3 October 2026, in 5 days, turning 61\n"
        "- Leap: Sunday 28 February 2027, in 153 days, turning 23")
    assert (tmp_path / "birthdays.json").is_file()
    assert dates_saved.remove(s, "birthday", "sam", True) == "Removed the birthday for Sam."
    with pytest.raises(ValueError):
        dates_saved.add(s, "birthday", "Bob", "13-45")


def test_saved_dates_tool(tmp_path):
    s = Settings(memory_dir=str(tmp_path))

    async def go(args):
        return await dates_saved.run_tool("saved_dates", args, s)
    assert asyncio.run(go({"action": "list", "kind": "birthday"})) == "No birthdays saved."
    asyncio.run(go({"action": "add", "kind": "countdown", "name": "Trip", "date": "2099-01-01"}))
    assert "Trip" in asyncio.run(go({"action": "list", "kind": "countdown"}))


def test_stopwatch():
    sw = dates_saved.stopwatch_action
    assert sw("stopwatch_read", 0) == "The stopwatch isn't running."
    assert sw("stopwatch_start", 100) == "Stopwatch started."
    assert sw("lap", 112.5) == "Lap 1: 12.5 seconds. Total 12.5 seconds."
    assert sw("lap", 190) == "Lap 2: 1 minute 18 seconds. Total 1 minute 30 seconds."
    assert sw("stopwatch_stop", 200) == "Stopwatch stopped at 1 minute 40 seconds over 2 laps."
    assert sw("stopwatch_read", 999) == "The stopwatch is stopped at 1 minute 40 seconds."
    assert sw("lap", 999) == "The stopwatch is stopped."


def test_focus_sessions(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    earlier = datetime(2026, 9, 28, 9, 0)
    (tmp_path / "focus.json").write_text(json.dumps({"sessions": [earlier.isoformat(), "2026-09-27T09:00:00"]}))

    async def go():
        now = earlier + timedelta(hours=2)
        started = dates_saved.focus_start(s, now)
        status = dates_saved.focus_status(s, now)
        again = await dates_saved.run_tool("focus_clock", {"action": "focus_start"}, s)
        return started, status, again
    started, status, again = asyncio.run(go())
    assert started == "Focus session started: 25 minutes. 1 session done today so far."
    assert status.startswith("25 minutes left in this focus session. 1 focus session done today.")
    assert "left in this focus session" in again
    assert len(json.loads((tmp_path / "focus.json").read_text())["sessions"]) == 3
    timers.timers.clear()
    assert dates_saved.focus_status(s, earlier + timedelta(hours=3)) == \
        "No focus session running. 2 focus sessions done today."
