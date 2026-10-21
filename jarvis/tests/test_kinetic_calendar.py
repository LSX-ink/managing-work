import asyncio
from datetime import date, datetime

import pytest

import kinetic_calendar as kc
import kinetic_store as st
import memory
import tools
from config import Settings

TODAY = date(2026, 10, 21)  # a Wednesday


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "today", lambda: TODAY)
    return Settings(memory_dir=str(tmp_path))


def cal(s, **args):
    return asyncio.run(kc.run_tool("content_calendar", args, s))


def test_default_schedule_every_three_days_at_six():
    posts = kc.default_posts()
    assert len(posts) == 15 and [p["title"] for p in posts][:2] == ["Pilates studio", "Spa & massage"]
    assert posts[0]["date"] == "2026-10-20" and posts[0]["time"] == "18:00"
    assert posts[5] == {**posts[5], "n": 6, "title": "Night café", "date": "2026-11-04"}
    assert posts[-1]["title"] == "Grooming lounge barber" and posts[-1]["date"] == "2026-12-01"


def test_what_do_i_post_this_week(s):
    out = cal(s, action="week")
    assert out.startswith("This week: post 1, Pilates studio, Tuesday 20 Oct at 6pm; post 2, Spa & massage, "
                          "Friday 23 Oct at 6pm.")
    assert "before/after on Sunday 25 Oct" in out
    body = out.card["text"]
    assert "Post 1: Pilates studio" in body and "Comment SITE for a free mock-up." in body
    nxt = cal(s, action="week", weeks_ahead=1)
    assert "post 3, Beauty & skincare, Monday 26 Oct" in nxt and "post 4, Wigs, Thursday 29 Oct" in nxt
    assert "post 1" not in nxt


def test_move_mark_and_caption_by_voice(s):
    said = cal(s, action="move", post="6", day="Friday")
    assert said.startswith("Moved post 6, Night café, from Wednesday 4 Nov at 6pm to Friday 6 Nov at 6pm.")
    assert next(r for r in kc.load(s) if r["n"] == 6)["date"] == "2026-11-06"
    assert "Heads up: post 6 (Night café) is on that day too." in cal(s, action="move", post="Roastery", day="friday")
    assert "at 7:30pm" in cal(s, action="move", post="post 7", time="7.30pm")
    with pytest.raises(ValueError, match="already gone"):
        cal(s, action="move", post="3", day="2026-10-01")
    assert cal(s, action="posted", post="2").startswith("Marked post 2, Spa & massage, as posted. Next up: post 1")
    assert "already marked posted" in cal(s, action="posted", post="2")
    assert "(posted)" in cal(s, action="week")
    assert "1 of 15 series posts are marked posted" in cal(s, action="schedule")
    assert "back to planned" in cal(s, action="unposted", post="2")
    cal(s, action="caption", post="4", caption="Wigs that turn heads. Comment SITE for a free mock-up.")
    assert cal(s, action="caption", post="wigs").card["text"].startswith("Wigs that turn heads")
    with pytest.raises(ValueError, match="Which post"):
        cal(s, action="posted", post="99")


def test_parse_day_and_time():
    assert kc.parse_day("Friday", date(2026, 11, 4), TODAY) == date(2026, 11, 6)
    assert kc.parse_day("monday", date(2026, 10, 23), TODAY) == date(2026, 10, 26)  # that week's Monday is gone
    assert kc.parse_day("next tuesday", date(2026, 11, 4), TODAY) == date(2026, 10, 27)
    assert kc.parse_time("7pm") == "19:00" and kc.parse_time("18:30") == "18:30" and kc.parse_time("12am") == "00:00"
    assert kc.clock("18:00") == "6pm" and kc.clock("09:05") == "9:05am"
    with pytest.raises(ValueError):
        kc.parse_time("25pm")


def test_post_day_reminder_an_hour_before(s):
    day = date(2026, 11, 4)
    assert kc.reminder_line(s, datetime(2026, 11, 4, 16, 59)) == ""
    assert not (memory.root(s) / kc.CALENDAR).exists()  # the reminder alone doesn't create the calendar file
    said = kc.reminder_line(s, datetime(2026, 11, 4, 17, 0))
    assert said == "Post 6 goes out at 6pm: Night café — caption is in your phone page."
    assert kc.reminder_line(s, datetime(2026, 11, 4, 17, 30)) == ""  # once
    assert kc.reminder_line(s, datetime(2026, 11, 7, 17, 0)) == "Post 7 goes out at 6pm: Roastery — caption is in your phone page."
    cal(s, action="posted", post="8")
    assert kc.reminder_line(s, datetime(2026, 11, 10, 17, 0)) == ""  # already posted
    assert kc.reminder_line(s, datetime(2026, 11, 13, 22, 0)) == ""  # too late in the evening
    assert next(r for r in kc.load(s) if r["n"] == 6)["reminded"] == day.isoformat()


def test_watch_announces_without_hanging(s, monkeypatch):
    monkeypatch.setattr(kc, "FIRST_LOOK", 0)
    monkeypatch.setattr(kc, "reminder_line", lambda settings: "Post 1 goes out at 6pm: Pilates studio")
    heard = []

    async def announce(text, kind):
        heard.append((text, kind))
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(asyncio.wait_for(kc.watch(s, announce, lambda: True), 10))
    assert heard == [("Post 1 goes out at 6pm: Pilates studio", "content")]


def test_registered(s):
    assert {"content_calendar", "kinetic_briefing"} <= {t["name"] for t in tools.client_tool_definitions(s)}
