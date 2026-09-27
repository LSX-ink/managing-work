import asyncio
import datetime as dt

import pytest

import reminders
from config import Settings

NOW = dt.datetime(2026, 9, 25, 18, 0)  # a Friday


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), user_address="sir")


def test_add_list_cancel(s):
    assert reminders.add(s, "2026-09-25 19:00", "call Mum", now=NOW) == "I'll remind them today at 19:00: call Mum."
    assert "tomorrow at 09:00" in reminders.add(s, "2026-09-26 09:00", "dentist", now=NOW)
    assert reminders.listing(s, NOW) == "Reminders: today at 19:00: call Mum; tomorrow at 09:00: dentist."
    with pytest.raises(ValueError, match="already passed"):
        reminders.add(s, "2026-09-25 17:00", "late", now=NOW)
    with pytest.raises(ValueError, match="YYYY"):
        reminders.add(s, "7pm", "x", now=NOW)
    with pytest.raises(ValueError, match="a year"):
        reminders.add(s, "2028-01-01 10:00", "x", now=NOW)
    assert reminders.cancel(s, "dentist") == "Cancelled: dentist."
    assert "No reminder matches" in reminders.cancel(s, "gym")


def test_due_once_and_repeating(s):
    reminders.add(s, "2026-09-25 19:00", "call Mum", now=NOW)
    reminders.add(s, "2026-09-25 19:00", "tablets", "weekdays", now=NOW)
    assert reminders.due(s, NOW) == []
    assert reminders.due(s, dt.datetime(2026, 9, 25, 19, 0, 10)) == ["call Mum", "tablets"]
    left = reminders.load(s)
    assert [(r["text"], r["at"]) for r in left] == [("tablets", "2026-09-28 19:00")]  # skips the weekend
    # missed while Jarvis was off: said late, with when it was due
    assert reminders.due(s, dt.datetime(2026, 9, 29, 8, 0)) == ["tablets (this was due Monday 28 September at 19:00)"]
    assert reminders.load(s)[0]["at"] == "2026-09-29 19:00"


def test_repeating_start_in_past_rolls_forward(s):
    assert "tomorrow at 08:00, and every day after" in reminders.add(s, "2026-09-25 08:00", "walk", "daily", now=NOW)


def test_watch_waits_for_a_page(s, monkeypatch):
    said, there = [], [False]
    monkeypatch.setattr(reminders, "CHECK_SECONDS", 0.01)
    reminders.save(s, [{"id": "a", "at": "2020-01-01 10:00", "text": "stretch", "repeat": "once"}])

    async def announce(text, kind):
        said.append((text, kind))

    async def main():
        task = asyncio.create_task(reminders.watch(s, announce, lambda: there[0]))
        await asyncio.sleep(0.05)
        assert said == []
        there[0] = True
        await asyncio.sleep(0.05)
        task.cancel()
    asyncio.run(main())
    assert said[0][0].startswith("Sir, a reminder: stretch (this was due") and said[0][1] == "timer"
    assert reminders.load(s) == []


def test_later_today(s):
    assert reminders.later_today(s, NOW) == ""
    reminders.add(s, "2026-09-25 19:00", "call Mum", now=NOW)
    reminders.add(s, "2026-09-26 09:00", "dentist", now=NOW)
    assert reminders.later_today(s, NOW) == "19:00 call Mum"
