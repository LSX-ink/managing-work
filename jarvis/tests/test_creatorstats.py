import asyncio
from datetime import date

import pytest

import creatorstats_accounts as ca
import creatorstats_plan as cp
import creatorstats_reports as cr
import creatorstats_stats as cs
import creatorstats_store as store
import screen
import tools
from config import Settings

TODAY = date(2026, 9, 29)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def acc(s, **a):
    return ca.run_tool("creator_accounts", a, s, None, TODAY)


def plan(s, **a):
    return cp.run_tool("creator_calendar", a, s, None, TODAY)


def st(s, **a):
    return cs.run_tool("creator_stats", a, s, None, TODAY)


def rep(s, **a):
    return cr.run_tool("creator_reports", a, s, None, TODAY)


def card(x):
    assert isinstance(x, screen.Shown) and x.card
    return x.card


def seeded(s):
    acc(s, action="account_add", account="lowkey.lore", niche="stories", goal_followers=1000)
    acc(s, action="account_add", account="mindglitch.fyi", platform="TikTok")
    for d, n in (("2026-09-01", 100), ("2026-09-15", 300), ("2026-09-29", 500)):
        acc(s, action="followers_log", account="lowkey.lore", followers=n, date=d)
    acc(s, action="followers_log", account="mindglitch.fyi", followers=50, date="2026-09-20")
    acc(s, action="followers_log", account="mindglitch.fyi", followers=80, date="2026-09-28")
    vids = [("Ghost", "2026-09-22", "19:30", 5000, "creepy", 40), ("Cat", "2026-09-23", "07:30", 800, "cute", 20),
            ("Heist", "2026-09-28", "19:40", 12000, "creepy", 55), ("Nap", "2026-09-29", "12:30", 300, "cute", 15)]
    for title, day, time, views, theme, length in vids:
        plan(s, action="plan_post", account="lowkey.lore", title=title, date=day, time=time, theme=theme, length_seconds=length)
        st(s, action="log_stats", post=title, checkpoint="24h", views=views, likes=views // 10, shares=views // 50,
           saves=views // 40, comments=views // 100, watch_percent=60, follows_gained=views // 200, date=day, time=time)
    st(s, action="log_stats", post="Ghost", checkpoint="1h", views=500)
    st(s, action="log_stats", post="Ghost", checkpoint="7d", views=9000, likes=900)


def test_registered_and_small():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    mods = (ca, cp, cs, cr)
    assert {"creator_accounts", "creator_calendar", "creator_stats", "creator_reports"} <= names
    total = 0
    for m in mods:
        for tool in m.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
            assert m.NAMES == {tool["name"]}
            total += len(tool["input_schema"]["properties"]["action"]["enum"])
    assert total >= 50


def test_through_tools_run(s):
    out = asyncio.run(tools._run_tool("creator_accounts", {"action": "account_add", "account": "a.b"}, s, None))
    assert "Added a.b" in out
    assert isinstance(asyncio.run(tools._run_tool("creator_accounts", {"action": "accounts"}, s, None)), screen.Shown)


def test_accounts(s):
    with pytest.raises(ValueError):
        acc(s, action="accounts") if False else acc(s, action="followers_log", followers=5)
    acc(s, action="account_add", account="lowkey.lore", niche="stories")
    with pytest.raises(ValueError):
        acc(s, action="account_add", account="lowkey.lore")
    assert "Updated" in acc(s, action="account_update", niche="scary stories", goal_followers=500)
    assert "Updated" in acc(s, action="account_update", new_name="lore2")
    assert "lore2" in card(acc(s, action="accounts"))["rows"][0][0]
    assert "5" in acc(s, action="followers_log", followers=5, date="2026-09-20")
    acc(s, action="followers_log", followers=25, date="2026-09-29")
    assert "500" in acc(s, action="goal_set", goal_followers=500, goal_date="2026-12-01")
    assert card(acc(s, action="goal_track"))["kind"] == "table"
    assert card(acc(s, action="milestones"))["rows"]
    assert "07:00" in acc(s, action="slots_set", slots=["7am", "7:30pm"])
    assert card(acc(s, action="schedule"))["rows"]
    assert card(acc(s, action="best_times"))["rows"]
    assert acc(s, action="best_times_edit", day_type="weekdays", windows=["18:00-20:00"])
    assert acc(s, action="best_times_edit", reset=True)
    assert acc(s, action="eligibility_add", item="10k followers", note="check the app")
    assert acc(s, action="eligibility_tick", item="1")
    assert card(acc(s, action="eligibility"))["kind"] in ("list", "table")
    assert acc(s, action="eligibility_remove", item="1")
    assert "confirm" in acc(s, action="account_remove", account="lore2").lower()
    assert "Removed" in acc(s, action="account_remove", account="lore2", confirmed=True)
    with pytest.raises(ValueError):
        acc(s, action="nope")


def test_calendar(s):
    seeded(s)
    assert "Planned" in plan(s, action="plan_post", account="lowkey.lore", title="Later", date="2026-10-02", slot=1)
    with pytest.raises(ValueError):
        plan(s, action="plan_post", account="lowkey.lore", title="Clash", date="2026-10-02", slot=1)
    assert "Updated" in plan(s, action="plan_edit", post="Later", theme="cute", date="2026-10-03")
    c = card(plan(s, action="calendar", month="2026-10"))
    assert c["kind"] == "creatorstats-calendar" and "3" in c["data"]["days"]
    assert card(plan(s, action="day", date="2026-10-03"))
    assert card(plan(s, action="upcoming", days=7))
    assert card(plan(s, action="free_slots", date="2026-10-03"))
    assert "posted" in plan(s, action="mark_posted", post="Later", date="2026-10-03").lower()
    assert "Removed" not in plan(s, action="plan_remove", post="Later")
    assert "Removed" in plan(s, action="plan_remove", post="Later", confirmed=True)
    assert card(plan(s, action="streak"))["rows"]
    assert card(plan(s, action="posting_rate", weeks=4))["chart"]["values"]
    with pytest.raises(ValueError):
        plan(s, action="nope")


def test_stats(s):
    seeded(s)
    assert "views" in st(s, action="log_stats", post="Cat", checkpoint="7d", views=900)
    assert card(st(s, action="post_show", post="Ghost"))["rows"]
    assert card(st(s, action="posts", status="posted"))["rows"]
    assert "Engagement" in st(s, action="rates", views=1000, likes=100, shares=20)
    assert card(st(s, action="best_posts", metric="engagement"))["rows"][0][1].startswith("#")
    assert card(st(s, action="worst_posts"))["rows"]
    assert card(st(s, action="checkpoints_chart", post="Ghost"))["chart"]["labels"] == ["1h", "24h", "7d"]
    assert "Started" in st(s, action="hook_add", account="lowkey.lore", hook_a="Nobody knew", hook_b="Last night")
    with pytest.raises(ValueError):
        st(s, action="hook_winner", hook="1")
    st(s, action="hook_result", hook="1", variant="a", views=100, watch_percent=50)
    st(s, action="hook_result", hook="1", variant="b", views=300, watch_percent=40)
    assert "B wins" in st(s, action="hook_winner", hook="1", metric="views")
    assert "A wins" in st(s, action="hook_winner", hook="1", variant="a")
    assert card(st(s, action="hooks"))["rows"][0][-1] == "A"
    with pytest.raises(ValueError):
        st(s, action="log_stats", post="Cat", checkpoint="2d", views=1)


def test_reports(s):
    seeded(s)
    assert len(card(rep(s, action="dashboard"))["rows"]) == 2
    assert card(rep(s, action="growth_chart", account="lowkey.lore"))["chart"]["values"] == [100, 300, 500]
    assert card(rep(s, action="views_trend", account="lowkey.lore"))["kind"] == "chart"
    w = rep(s, action="weekly_report", account="lowkey.lore")
    assert card(w)["rows"][0][1] == "2" and "Heist" in w
    assert card(rep(s, action="monthly_report", month="2026-09"))["rows"]
    assert "median" in rep(s, action="averages", account="lowkey.lore").lower() or card(rep(s, action="averages"))
    assert card(rep(s, action="compare_accounts"))["rows"]
    assert "Heist" in rep(s, action="compare_posts", post="Ghost", post_b="Heist")
    assert "Sunday" in rep(s, action="best_day") or "day" in rep(s, action="best_day")
    assert card(rep(s, action="best_hour"))["rows"]
    assert card(rep(s, action="themes"))["rows"][0][0] == "creepy"
    assert card(rep(s, action="length_check"))["rows"]
    assert card(rep(s, action="conversion"))["rows"]
    assert card(rep(s, action="consistency"))["rows"]
    with pytest.raises(ValueError):
        rep(s, action="earnings_estimate", account="lowkey.lore")
    e = rep(s, action="earnings_estimate", account="lowkey.lore", rpm=0.5, views=10000)
    assert "£5.00" in e and "GOV.UK" in card(e)["text"]
    assert "Saved" in rep(s, action="export_csv")
    assert (s.memory_dir and list(__import__("pathlib").Path(s.memory_dir).glob("creatorstats-export-*.csv")))
    with pytest.raises(ValueError):
        rep(s, action="compare_posts", post="Ghost")
    with pytest.raises(ValueError):
        rep(s, action="nope")


def test_empty_states(s):
    for call in (lambda: rep(s, action="dashboard"), lambda: rep(s, action="averages"), lambda: st(s, action="best_posts")):
        with pytest.raises(ValueError):
            call()


def test_store_helpers():
    assert store.parse_time("7:30pm") == "19:30" and store.parse_time("7") == "07:00"
    assert store.count(1500) == "1.5k" and store.count(2_000_000) == "2M"
    assert store.rates({"views": 100, "likes": 10})["engagement"] == 10.0
    assert store.safe_cell("=SUM(A1)") == "'=SUM(A1)"
