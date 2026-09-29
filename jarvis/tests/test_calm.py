from datetime import date, datetime, timedelta

import pytest

import calm_evening
import calm_exercises
import calm_log
import calm_mind
import calm_store
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def ex(s, **a):
    return calm_exercises.run_tool("calm_exercises", a, s)


def mind(s, **a):
    return calm_mind.run_tool("calm_mind", a, s)


def lg(s, **a):
    return calm_log.run_tool("calm_log", a, s)


def ev(s, **a):
    return calm_evening.run_tool("calm_evening", a, s)


def test_registered_and_kinds():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"calm_exercises", "calm_mind", "calm_log", "calm_evening"} <= names
    assert {"calm-breathe", "calm-bells", "calm-guide"} <= screen.EXTRA_KINDS


@pytest.mark.parametrize("pattern,count", [("box", 4), ("4-7-8", 3), ("coherent", 2), ("physiological sigh", 3)])
def test_breathing_patterns(s, pattern, count):
    shown = ex(s, action="breathe", pattern=pattern, minutes=2)
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "calm-breathe"
    assert len(shown.card["data"]["phases"]) == count and shown.card["data"]["minutes"] == 2
    assert shown.card["buttons"][0]["say"] == "Log 2 mindful minutes of breathing"


def test_breathing_errors_custom_and_list(s):
    with pytest.raises(ValueError):
        ex(s, action="breathe", pattern="fast")
    custom = ex(s, action="breathing_custom", inhale=4, hold_in=2, exhale=6, tone=False)
    assert [p["seconds"] for p in custom.card["data"]["phases"]] == [4, 2, 6] and custom.card["data"]["tone"] is False
    with pytest.raises(ValueError):
        ex(s, action="breathing_custom", inhale=4)
    assert ex(s, action="breathing_patterns").card["kind"] == "table"


def test_meditate_bells(s):
    shown = ex(s, action="meditate", minutes=10, interval_minutes=2)
    assert shown.card["kind"] == "calm-bells" and shown.card["data"]["interval"] == 2
    with pytest.raises(ValueError):
        ex(s, action="meditate", minutes=5, interval_minutes=5)


def test_guides_and_menu(s):
    for script in ("body scan", "5-4-3-2-1", "loving kindness", "muscle relaxation", "wind_down"):
        shown = ex(s, action="guide", script=script)
        assert shown.card["kind"] == "calm-guide" and len(shown.card["data"]["steps"]) >= 6
    with pytest.raises(ValueError):
        ex(s, action="guide", script="nope")
    assert ex(s, action="guide_list").card["kind"] == "list"
    assert ex(s, action="calm_menu").card["items"][0]["say"]
    shown = ex(s, action="calm_menu", feeling="stressed")
    assert shown.card["title"] == "Feeling overwhelmed" and "not medical advice" in shown
    with pytest.raises(ValueError):
        ex(s, action="calm_menu", feeling="purple")


def test_support_and_crisis_wording(s):
    for shown in (ex(s, action="support"), ex(s, action="calm_menu", feeling="I want to die"),
                  ex(s, action="breathe", text="I keep thinking about suicide")):
        assert "116 123" in shown and "NHS 111" in shown
    with pytest.raises(ValueError):
        ex(s, action="nope")


def test_affirmations(s):
    assert mind(s, action="affirmation").card["kind"] == "text"
    assert mind(s, action="affirmation", another=True).card["buttons"]
    assert "own" in mind(s, action="affirmation_list")
    assert "Added" in mind(s, action="affirmation_add", text="I am calm")
    assert "already" in mind(s, action="affirmation_add", text="I am calm")
    assert mind(s, action="affirmation_list").card["items"][0]["label"] == "I am calm"
    assert "confirm" in mind(s, action="affirmation_remove", words="calm")
    assert "Removed" in mind(s, action="affirmation_remove", words="calm", confirmed=True)
    with pytest.raises(ValueError):
        mind(s, action="affirmation_remove", words="calm", confirmed=True)


def test_kindness(s):
    shown = mind(s, action="kindness")
    assert shown.card["buttons"][0]["say"].startswith("I did my kindness")
    assert "1 kind act" in mind(s, action="kindness_done", note="Held a door")
    assert "Done today" in mind(s, action="kindness").card["text"]


def test_gratitude_lookback(s):
    assert "anything" in mind(s, action="gratitude_lookback")
    then = calm_mind._months_back(calm_store.today(), 1)
    if then:
        calm_store.hs.save(s, "routines-gratitude.json", {then.isoformat(): ["tea", "sun"]})
        shown = mind(s, action="gratitude_lookback")
        assert [i["label"] for i in shown.card["items"]] == ["tea", "sun"]
    assert calm_mind._months_back(date(2026, 3, 31), 1) is None


def test_worries(s):
    assert "empty" in mind(s, action="worry_list")
    assert "No worries" in mind(s, action="worry_time")
    assert "1 worry" in mind(s, action="worry_add", text="The boiler")
    mind(s, action="worry_add", text="Money")
    shown = mind(s, action="worry_list")
    assert shown.card["items"][0]["say"] == "Let go of the worry: The boiler"
    assert mind(s, action="worry_time").card["title"] == "Worry time"
    assert "18:00" in mind(s, action="worry_time_set", time="6pm")
    assert "18:00" in mind(s, action="worry_time")
    assert "1 worry released" in mind(s, action="worry_let_go", words="boiler")
    with pytest.raises(ValueError):
        mind(s, action="worry_let_go", words="boiler")
    assert mind(s, action="worry_list", all=True).card["items"][0]["done"] is True
    assert "confirm" in mind(s, action="worry_clear")
    assert "Cleared" in mind(s, action="worry_clear", confirmed=True)
    assert len(mind(s, action="worry_list", all=True).card["items"]) == 1
    assert "no released" in mind(s, action="worry_clear")


def test_worry_and_checkin_crisis_not_saved(s):
    assert "116 123" in mind(s, action="worry_add", text="I want to end my life")
    assert "empty" in mind(s, action="worry_list")
    assert "116 123" in mind(s, action="checkin", rating=1, note="thinking of self-harm")
    assert "No calm check-ins" in mind(s, action="checkin_history")


def test_checkins(s):
    assert "quick calm-down" in mind(s, action="checkin", rating=2, note="busy day")
    assert "4 out of 5" in mind(s, action="checkin", rating=4)
    with pytest.raises(ValueError):
        mind(s, action="checkin", rating=9)
    shown = mind(s, action="checkin_history")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"] == [3.0]
    with pytest.raises(ValueError):
        mind(s, action="nope")


def test_minutes_log_and_streak(s):
    assert "0 mindful minutes today" in lg(s, action="today")
    assert "No mindful minutes" in lg(s, action="streak")
    assert "1 day in a row" in lg(s, action="log", minutes=5, kind="breathing")
    lg(s, action="log", minutes=10, date="yesterday", kind="meditation")
    lg(s, action="log", minutes=3, date=(calm_store.today() - timedelta(days=2)).isoformat())
    shown = lg(s, action="streak")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"][-1] == 5
    assert "3 days in a row" in shown
    assert "goal of 5" in lg(s, action="today") and "Goal met" in lg(s, action="today")
    assert "18 minutes" in lg(s, action="summary")
    assert "mostly" in lg(s, action="summary", span="month")
    assert lg(s, action="history").card["kind"] == "table"
    assert "10 mindful" in lg(s, action="goal_set", minutes=10)
    assert "Goal met" not in lg(s, action="today")
    with pytest.raises(ValueError):
        lg(s, action="log", minutes=0)


def test_minutes_undo_and_goal_message(s):
    assert "nothing" in lg(s, action="undo")
    assert "goal done" in lg(s, action="log", minutes=6)
    assert "confirm" in lg(s, action="undo")
    assert "Removed" in lg(s, action="undo", confirmed=True)
    assert "No mindful" in lg(s, action="summary")
    with pytest.raises(ValueError):
        lg(s, action="nope")


def test_winddown(s):
    shown = ev(s, action="winddown_show")
    assert shown.card["kind"] == "list" and len(shown.card["items"]) == 9
    ticked = ev(s, action="winddown_tick", words="dim the lights")
    assert [i["done"] for i in ticked.card["items"]].count(True) == 1 and "8 steps left" in ticked
    with pytest.raises(ValueError):
        ev(s, action="winddown_tick", words="juggle")
    assert "10 steps" in ev(s, action="winddown_add", text="Stretch")
    assert "already" in ev(s, action="winddown_add", text="stretch")
    assert "confirm" in ev(s, action="winddown_remove", words="stretch")
    assert "Removed" in ev(s, action="winddown_remove", words="stretch", confirmed=True)
    with pytest.raises(ValueError):
        ev(s, action="winddown_start")
    assert "21:45" in ev(s, action="winddown_start", bedtime="22:30")
    assert "22:00" in ev(s, action="winddown_start", minutes=30)
    assert ev(s, action="sleep_tips").card["kind"] == "list"
    with pytest.raises(ValueError):
        ev(s, action="nope")


def test_detox(s, monkeypatch):
    start = datetime(2026, 5, 1, 19, 0)
    monkeypatch.setattr(calm_store.hs, "now", lambda: start)
    assert "No detox is running" in ev(s, action="detox_status")
    assert "No detox was running" in ev(s, action="detox_end")
    assert "No detoxes" in ev(s, action="detox_history")
    shown = ev(s, action="detox_start", minutes=60)
    assert shown.card["kind"] == "timer" and shown.card["ends_at"] == int((start + timedelta(hours=1)).timestamp() * 1000)
    monkeypatch.setattr(calm_store.hs, "now", lambda: start + timedelta(minutes=20))
    status = ev(s, action="detox_status")
    assert "40 minutes left" in status and status.card["kind"] == "timer"
    monkeypatch.setattr(calm_store.hs, "now", lambda: start + timedelta(minutes=75))
    assert "up" in ev(s, action="detox_status")
    assert "75 minutes screen-free" in ev(s, action="detox_end")
    assert "1 detox finished" in ev(s, action="detox_history")
    with pytest.raises(ValueError):
        ev(s, action="detox_start", minutes=1)
