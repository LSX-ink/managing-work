import asyncio
import json
from datetime import date, datetime, timedelta

import pytest

import habits
import homestore
import homewellbeing
import money
import reminders
import screen
import tools
import trackers
import trackers_life as life
import trackers_store as store
import trackers_views as views
from config import Settings

DAY = date(2026, 9, 28)  # a Monday


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "today", lambda: DAY)
    monkeypatch.setattr(homestore, "now", lambda: datetime.combine(DAY, datetime.min.time()).replace(hour=12))  # water log
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def run(tool, args, s):
    module = {"trackers": trackers, "tracker_charts": views, "streak_challenges": life}[tool]
    return module.run_tool(tool, args, s)


def fill(s, name, values, notes=None):
    data = store.trackers(s)
    data["values"][name] = {(DAY - timedelta(days=i)).isoformat(): v for i, v in enumerate(values) if v is not None}
    data["notes"][name] = {(DAY - timedelta(days=i)).isoformat(): n for i, n in (notes or {}).items()}
    store.save_trackers(s, data)


def test_registered_and_kinds():
    assert {trackers, views, life} <= set(tools.ABILITIES)
    assert {"trackers-chart", "trackers-pixels", "trackers-dashboard"} <= screen.EXTRA_KINDS
    for module in (trackers, views, life):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False


def test_create_list_delete(s):
    assert run("trackers", {"action": "create", "tracker": "Coffee", "type": "count", "unit": "cups", "goal": 3,
                            "goal_type": "at_most"}, s) == "Tracking Coffee as a count, daily goal at most 3 cups."
    assert run("trackers", {"action": "create", "tracker": "Meditation", "type": "duration", "goal": 10}, s) \
        .startswith("Tracking Meditation as a time")
    with pytest.raises(ValueError):
        run("trackers", {"action": "create", "tracker": "coffees", "type": "count"}, s)
    with pytest.raises(ValueError):
        run("trackers", {"action": "create", "tracker": "x", "type": "colour"}, s)
    shown = run("trackers", {"action": "list"}, s)
    assert shown.card["kind"] == "table" and [r[0] for r in shown.card["rows"]] == ["Coffee", "Meditation"]
    assert "confirm" in run("trackers", {"action": "delete", "tracker": "coffee"}, s)
    assert run("trackers", {"action": "delete", "tracker": "coffee", "confirmed": True}, s) == "Deleted the Coffee tracker."
    assert list(store.trackers(s)["trackers"]) == ["Meditation"]


def test_log_by_voice_matches_names_and_types(s):
    run("trackers", {"action": "create", "tracker": "Back pain", "type": "rating"}, s)
    run("trackers", {"action": "create", "tracker": "Meditation", "type": "duration", "goal": 10}, s)
    run("trackers", {"action": "create", "tracker": "Flossed", "type": "yes_no"}, s)
    run("trackers", {"action": "create", "tracker": "Journal", "type": "text"}, s)
    run("trackers", {"action": "create", "tracker": "Weight", "type": "number", "unit": "kg", "per_day": "latest"}, s)
    assert run("trackers", {"action": "log", "tracker": "my back pain", "value": "2"}, s) == \
        "Back pain: 2 out of 5 today."
    assert run("trackers", {"action": "log", "tracker": "meditate", "value": "10 minutes"}, s) == \
        "Meditation: 10 min today. Goal met."
    assert run("trackers", {"action": "log", "tracker": "meditation", "value": "1h 5m"}, s).startswith(
        "Meditation: 1 h 15 min today.")
    assert run("trackers", {"action": "log", "tracker": "floss", "value": "no", "day": "yesterday"}, s) == \
        "Flossed: no Sunday 27 September."
    assert run("trackers", {"action": "log", "tracker": "journal", "value": "Good walk by the river"}, s) == \
        "Noted in Journal for today."
    run("trackers", {"action": "log", "tracker": "weight", "value": "80.2"}, s)
    assert run("trackers", {"action": "log", "tracker": "weight", "value": "79.9"}, s) == "Weight: 79.9 kg today."
    data = store.trackers(s)
    assert data["notes"]["Journal"] == {"2026-09-28": "Good walk by the river"}
    with pytest.raises(ValueError):
        run("trackers", {"action": "log", "tracker": "back pain", "value": "7"}, s)
    with pytest.raises(ValueError):
        run("trackers", {"action": "log", "tracker": "sleepiness", "value": "3"}, s)


def test_counters_tap_and_reset_daily(s, monkeypatch):
    run("trackers", {"action": "create", "tracker": "Push-ups", "type": "count"}, s)
    first = run("trackers", {"action": "log", "tracker": "push ups"}, s)
    assert first == "Push-ups: 1 today."
    assert first.card["id"] == "trackers-counters"
    assert first.card["items"][0] == {"label": "+1  Push-ups: 1 today", "done": False,
                                      "say": "Add one to my Push-ups counter."}
    shown = run("trackers", {"action": "counters"}, s)
    assert shown.card["kind"] == "list" and "1 today" in shown.card["items"][0]["label"]
    monkeypatch.setattr(store, "today", lambda: DAY + timedelta(days=1))
    assert "0 today" in trackers.counters(s).card["items"][0]["label"]


def test_milestone_in_log_reply(s):
    run("trackers", {"action": "create", "tracker": "Running", "type": "number", "unit": "km"}, s)
    fill(s, "Running", [None, 40, 50])
    assert run("trackers", {"action": "log", "tracker": "running", "value": "12"}, s) == \
        "Running: 12 km today. Milestone: over 100 km in total!"
    assert trackers.milestone({"type": "duration"}, 590, 620) == " Milestone: over 10 hours in total!"
    assert trackers.milestone({"type": "rating"}, 1, 500) == ""


def test_remind_to_log(s):
    run("trackers", {"action": "create", "tracker": "Mood notes", "type": "text"}, s)
    out = trackers.remind(s, "mood notes", "21:00", datetime(2026, 9, 28, 22, 0))
    assert out == "I'll remind them tomorrow at 21:00, and every day after: Log your Mood notes for today."
    assert reminders.load(s)[0]["repeat"] == "daily"
    with pytest.raises(ValueError):
        trackers.remind(s, "", "9pm", datetime(2026, 9, 28, 8, 0))


def test_export_and_import_csv(s, tmp_path):
    run("trackers", {"action": "create", "tracker": "Water", "type": "count"}, s)
    fill(s, "Water", [5, 6], {1: "hot day"})
    shown = run("trackers", {"action": "export", "tracker": "water"}, s)
    assert shown == "Saved Water as Personal/Trackers/Water.csv."
    assert shown.card["kind"] == "file" and shown.card["mime"] == "text/csv"
    assert (tmp_path / "Personal" / "Trackers" / "Water.csv").read_text() == \
        "date,value,note\n2026-09-27,6,hot day\n2026-09-28,5,\n"
    (tmp_path / "Personal" / "old.csv").write_text("date,value\n2026-09-01,4\n2026-09-28,9\nbad,row\n")
    assert run("trackers", {"action": "import", "tracker": "water", "folder": "Personal", "filename": "old.csv"}, s) == \
        "Imported 1 day into Water from old.csv. Kept 1 day already logged; confirm to overwrite them."
    run("trackers", {"action": "import", "tracker": "water", "folder": "Personal", "filename": "old.csv",
                     "confirmed": True}, s)
    assert store.trackers(s)["values"]["Water"]["2026-09-28"] == 9


def test_chart_with_goal_and_stats(s):
    run("trackers", {"action": "create", "tracker": "Steps walked", "type": "count", "goal": 5}, s)
    fill(s, "Steps walked", [6, 5, None, 2, 8])
    shown = run("tracker_charts", {"action": "chart", "tracker": "steps walked", "days": 7}, s)
    assert shown == "Steps walked over 7 days: average 5.25, goal met 3 days, streak 2."
    data = shown.card["data"]
    assert shown.card["kind"] == "trackers-chart" and data["goal"] == 5 and len(data["values"]) == 7
    assert data["values"][-3] is None and data["type"] == "bar"
    assert ["Total", "21"] in data["stats"] and ["Highest", "8"] in data["stats"]
    assert run("tracker_charts", {"action": "chart", "tracker": "steps walked", "days": 90}, s).card["data"]["labels"][0] == "01 Jul"


def test_chart_reads_other_logs(s):
    homewellbeing.water_add(s, 3)
    shown = run("tracker_charts", {"action": "chart", "tracker": "water"}, s)
    assert shown.card["data"]["values"][-1] == 3 and shown.card["data"]["goal"] == 8


def test_year_in_pixels(s):
    run("trackers", {"action": "create", "tracker": "Mood rating", "type": "rating"}, s)
    fill(s, "Mood rating", [4, None, 2], {0: "Lovely day"})
    shown = run("tracker_charts", {"action": "year_pixels", "tracker": "mood rating"}, s)
    cells = shown.card["data"]["cells"]
    assert shown.card["kind"] == "trackers-pixels" and len(cells) == 365
    assert cells[-1] == {"d": "2026-09-28", "v": 4, "t": "4 out of 5", "n": "Lovely day"}
    assert cells[-2]["v"] is None and cells[-3]["v"] == 2
    assert shown.card["data"]["offset"] == date.fromisoformat(cells[0]["d"]).weekday()


def test_compare_periods(s):
    run("trackers", {"action": "create", "tracker": "Coffee", "type": "count"}, s)
    fill(s, "Coffee", [4] + [2] * 7)  # Monday 4; last week 2 a day
    shown = run("tracker_charts", {"action": "compare", "tracker": "coffee", "period": "week"}, s)
    assert shown == "Coffee: 4 this week so far, against 14 last week."
    assert shown.card["rows"][0] == ["Total", "14", "4", "-71%"]
    month = run("tracker_charts", {"action": "compare", "tracker": "coffee", "period": "month"}, s)
    assert month.card["kind"] == "table" and "this month" in month


def test_correlation_with_caution(s):
    run("trackers", {"action": "create", "tracker": "Sleep hours", "type": "number"}, s)
    run("trackers", {"action": "create", "tracker": "Energy", "type": "rating"}, s)
    fill(s, "Sleep hours", [8, 6, 7, 5, 9, 6])
    fill(s, "Energy", [4, 2, 3, 1, 5, None])
    shown = run("tracker_charts", {"action": "correlate", "tracker": "sleep hours", "other": "energy"}, s)
    assert "a strong positive link (correlation +1.00)" in shown and views.CAUTION in shown
    assert shown.card["kind"] == "table" and len(shown.card["rows"]) == 5
    assert views.strength(-0.35) == "a moderate negative link" and views.strength(0.05) == "no real link"
    fill(s, "Energy", [4, 2])
    with pytest.raises(ValueError):
        run("tracker_charts", {"action": "correlate", "tracker": "sleep hours", "other": "energy"}, s)


def test_month_review(s):
    run("trackers", {"action": "create", "tracker": "Coffee", "type": "count", "goal": 3, "goal_type": "at_most"}, s)
    run("trackers", {"action": "create", "tracker": "Reading", "type": "yes_no"}, s)
    fill(s, "Coffee", [2, 5, 1])
    fill(s, "Reading", [1, 0])
    shown = run("tracker_charts", {"action": "month_review"}, s)
    assert shown == "September 2026: 2 of 2 trackers have entries."
    assert shown.card["rows"][0] == ["Coffee", "3", "8", "2.67", "2 days", "27 (5)"]
    assert shown.card["rows"][1][2] == "1 yes"
    with pytest.raises(ValueError):
        views.month_review(s, "Sept")


def test_dashboard_with_other_logs(s):
    run("trackers", {"action": "create", "tracker": "Coffee", "type": "count"}, s)
    fill(s, "Coffee", [2])
    homewellbeing.water_add(s, 4)
    habits.mark(s, "Gym", DAY)
    money.log_spend(s, {"amount": 12.5, "what": "lunch"}, DAY)
    with pytest.raises(ValueError):
        run("tracker_charts", {"action": "dashboard_set", "items": ["nonsense"]}, s)
    assert run("tracker_charts", {"action": "dashboard_set", "items": ["coffee", "water", "habits", "spending"]}, s) == \
        "Your dashboard shows Coffee, water, habits, spending."
    shown = run("tracker_charts", {"action": "dashboard"}, s)
    tiles = {t["name"]: t for t in shown.card["data"]["tiles"]}
    assert shown.card["kind"] == "trackers-dashboard" and len(tiles) == 4
    assert tiles["water"]["today"] == "4 glasses" and tiles["habits"]["today"] == "1 of 1 done"
    assert tiles["spending"]["extra"] == "this month 12.50 GBP" and tiles["Coffee"]["say"] == "Show my Coffee chart."
    assert len(tiles["Coffee"]["values"]) == 14


def test_streak_challenge(s):
    assert run("streak_challenges", {"action": "start", "challenge": "No sugar", "days": 30,
                                     "start_date": "2026-09-26"}, s).startswith("Challenge on: No sugar for 30 days")
    with pytest.raises(ValueError):
        run("streak_challenges", {"action": "start", "challenge": "no sugar"}, s)
    run("streak_challenges", {"action": "check", "challenge": "sugar", "when": "yesterday"}, s)
    assert run("streak_challenges", {"action": "check", "challenge": "no sugar"}, s) == \
        "No sugar: Streak 2 days, 2 of 30 done, 27 to go."
    shown = run("streak_challenges", {"action": "show", "challenge": "no sugar"}, s)
    cells = shown.card["data"]["cells"]
    assert shown.card["kind"] == "trackers-pixels" and shown.card["data"]["calendar"] is True
    assert [c["v"] for c in cells[:4]] == [0, 5, 5, None] and cells[0]["t"] == "missed"
    assert shown.card["buttons"][0]["say"] == "I kept my No sugar challenge today."
    assert run("streak_challenges", {"action": "check", "challenge": "no sugar", "kept": False}, s).startswith(
        "No sugar: marked as missed.")
    listing = run("streak_challenges", {"action": "show"}, s)
    assert listing.card["kind"] == "list" and listing.card["items"][0]["label"].startswith("No sugar: 1 of 30 days")
    assert "confirm" in run("streak_challenges", {"action": "stop", "challenge": "no sugar"}, s)
    assert run("streak_challenges", {"action": "stop", "challenge": "no sugar", "confirmed": True}, s) == \
        "Stopped the No sugar challenge."


def test_life_in_weeks(s, tmp_path):
    assert "date of birth" in run("streak_challenges", {"action": "life_weeks"}, s)
    shown = run("streak_challenges", {"action": "life_weeks", "birth_date": "1990-09-14"}, s)
    assert shown == "You've lived 1,874 weeks; 2,806 more to age 90."
    assert shown.card["data"]["weeks"] == {"lived": 1874, "total": 4680, "per_row": 52}
    assert json.loads((tmp_path / "trackers-profile.json").read_text()) == {"birth_date": "1990-09-14"}
    assert run("streak_challenges", {"action": "life_weeks"}, s).card["kind"] == "trackers-pixels"
    with pytest.raises(ValueError):
        run("streak_challenges", {"action": "life_weeks", "birth_date": "2030-01-01"}, s)


def test_popup_goes_through_tools(s):
    run("trackers", {"action": "create", "tracker": "Coffee", "type": "count"}, s)
    sent = []

    async def page(msg):
        sent.append(msg)

    out = asyncio.run(tools.run_tool("trackers", {"action": "list"}, s, None, page))
    assert out == "You have 1 tracker." and sent[0]["card"]["id"] == "trackers-list"
