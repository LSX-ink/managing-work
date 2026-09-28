import asyncio
from datetime import datetime

import httpx
import pytest

import homestore
import homewellbeing
import reminders
import screen
import tools
import wellness_fitness as fit
import wellness_logs as logs
import wellness_records as rec
import wellness_reminders as rem
from config import Settings

CLOCK = {"now": datetime(2026, 9, 28, 10, 30)}  # a Monday


def set_now(when: datetime) -> None:
    CLOCK["now"] = when


@pytest.fixture
def s(tmp_path, monkeypatch):
    set_now(datetime(2026, 9, 28, 10, 30))
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path))


def log(s, **args):
    return logs.run_tool("health_log", args, s)


def fitness(s, **args):
    return fit.run_tool("fitness_coach", args, s)


def records(s, **args):
    return rec.run_tool("health_records", args, s)


def remind(s, **args):
    return rem.run_tool("health_reminders", args, s)


def test_weight_chart_and_average(s, tmp_path):
    set_now(datetime(2026, 9, 20, 8, 0))
    log(s, action="weight_add", kg=80)
    set_now(datetime(2026, 9, 28, 8, 0))
    assert log(s, action="weight_add", stone=12, pounds=4) == "Logged 78 kg (12 st 4 lb). 7-day average 78.0 kg."
    log(s, action="weight_add", kg=77, date="yesterday")
    shown = log(s, action="weight_show")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "wellness-trend"
    assert shown.card["data"]["series"][0]["values"] == [80, 77, 78]
    assert shown.card["data"]["series"][1]["values"] == [80, 77, 77.5]
    assert "7-day average 77.5 kg, down 2.5 kg on the week before" in shown
    assert (tmp_path / "health-plus-weight.json").exists()
    with pytest.raises(ValueError):
        log(s, action="weight_add")


def test_blood_pressure(s):
    out = log(s, action="bp_add", systolic=145, diastolic=85, pulse=72)
    assert "blood pressure 145/85 (NHS band: high) and heart rate 72" in out and "NHS 111" in out
    assert log(s, action="bp_add", pulse=64) == "Logged heart rate 64."
    assert logs.bp_band(115, 75) == "ideal" and logs.bp_band(125, 70) == "slightly raised" and logs.bp_band(88, 58) == "low"
    table = log(s, action="bp_show")
    assert table.card["kind"] == "table" and table.card["rows"][1][3] == "high" and "90/60" in table.card["text"]
    chart = log(s, action="bp_chart")
    assert chart.card["kind"] == "wellness-trend" and len(chart.card["data"]["series"]) == 3
    with pytest.raises(ValueError):
        log(s, action="bp_add", systolic=120)


def test_food_diary(s):
    assert log(s, action="food_goal", calories=1800) == "Daily calorie goal set to 1,800."
    log(s, action="food_add", food="porridge", calories=350, protein=12)
    assert log(s, action="food_add", food="pizza", calories=1600) == \
        "Logged pizza, 1600 calories. 1,950 so far that day; 150 over your goal."
    today = log(s, action="food_today")
    assert today.card["kind"] == "table" and today.card["rows"][-1] == ["", "Total", "1,950 / 1,800", "12"]
    week = log(s, action="food_week")
    assert week.card["kind"] == "chart" and week.card["chart"]["values"][-1] == 1950


def test_caffeine(s):
    log(s, action="caffeine_add", drink="lattes", count=2)
    set_now(datetime(2026, 9, 28, 14, 0))
    assert log(s, action="caffeine_add", drink="tea") == "Logged 1 tea, about 75 mg. 335 mg of caffeine today."
    today = log(s, action="caffeine_today")
    assert today == "335 mg of caffeine today. Last coffee at 10:30, 3.5 hours ago."
    assert today.card["rows"][-1] == ["", "Total", "335"]
    assert log(s, action="caffeine_drinks").card["rows"][0] == ["large energy drink", "160"]
    with pytest.raises(ValueError):
        log(s, action="caffeine_add", drink="mystery tonic")


def test_symptoms_and_undo(s):
    out = log(s, action="symptom_add", symptom="headache", severity=6, notes="after screen time")
    assert out.startswith("Logged headache, severity 6 out of 10.") and "GP or NHS 111" in out
    hist = log(s, action="symptom_history", symptom="head")
    assert hist.card["rows"][0][1:] == ["headache", "6", "after screen time"]
    assert "confirm" in log(s, action="undo", log="symptom")
    assert log(s, action="undo", log="symptom", confirmed=True).startswith("Removed the last symptom entry")
    assert log(s, action="symptom_history") == "No symptoms logged yet."


def test_week_summary_reads_wellbeing(s):
    log(s, action="weight_add", kg=70)
    log(s, action="bp_add", systolic=118, diastolic=76)
    homewellbeing.sleep_log(s, 7.5)
    fitness(s, action="run_add", distance=5, time="25:00")
    out = log(s, action="week_summary")
    rows = {r[0]: r[1] for r in out.card["rows"]}
    assert rows["Weight (average)"] == "70.0 kg" and rows["Blood pressure"] == "118/76"
    assert rows["Sleep"] == "7.5 h a night" and rows["Running"] == "1 runs, 5.0 km"
    assert out.card["rows"][0][2] == "-"


def test_interval_timer(s):
    out = fitness(s, action="interval_timer", work_seconds=40, rest_seconds=20, rounds=3, warmup_seconds=60, name="Tabata")
    assert out.card["kind"] == "wellness-intervals"
    phases = out.card["data"]["phases"]
    assert [p["label"] for p in phases][:3] == ["Warm up", "Work, round 1 of 3", "Rest"] and len(phases) == 6
    assert "3:40 in all. Saved as tabata." in out
    again = fitness(s, action="interval_timer", name="tabata")
    assert again.card["data"] == out.card["data"]
    with pytest.raises(ValueError):
        fitness(s, action="interval_timer", name="nope")


def test_workout_plans(s):
    assert fitness(s, action="plans").card["kind"] == "list"
    start = fitness(s, action="plan_start", plan="5k")
    assert start.card["checks"] and start.card["items"][1]["label"] == fit.RUN_WEEKS[0]
    assert "Week 1, run 1 of 3" in start
    assert fitness(s, action="plan_tick", move="warm-up").startswith("Ticked Warm-up")
    assert fitness(s, action="plan_today").card["items"][0]["done"] is True
    assert fitness(s, action="plan_done") == "Marked Week 1, run 1 of 3 done. Next time: Week 1, run 2 of 3."
    assert fitness(s, action="plan_today").card["items"][0]["done"] is False
    desk = fitness(s, action="plan_start", plan="desk")
    assert any(b["label"] == "Start timer" for b in desk.card["buttons"])


def test_routine_timer(s):
    out = fitness(s, action="routine_timer", routine="desk", seconds=20)
    assert out.card["kind"] == "wellness-intervals" and all(p["seconds"] == 20 for p in out.card["data"]["phases"])
    assert fitness(s, action="routine_timer", routine="stretching").card["title"] == "Stretching"


def test_running_log(s):
    assert fitness(s, action="run_add", distance=5, time="30:00") == \
        "Logged 5 km in 30:00: 6:00 per km, 9:39 per mile. Your first 5k logged."
    assert fitness(s, action="run_add", distance=5, time="28:30").endswith("New 5k personal best!")
    fitness(s, action="run_add", distance=6.2, unit="miles", time="1:00:00", date="yesterday")
    out = fitness(s, action="run_show")
    assert out.card["kind"] == "chart" and out.card["chart"]["values"][-2:] == [10, 10]
    assert "5k: 28:30" in out.card["text"] and "10k: 1:00:00" in out.card["text"]


def test_heart_zones_and_sleep(s):
    zones = fitness(s, action="hr_zones", age=40, resting_hr=60)
    assert zones.startswith("Estimated maximum heart rate 180")
    assert zones.card["rows"][1] == ["2 Easy", "60%-70%", "108-126", "132-144"]
    assert len(fitness(s, action="hr_zones", age=40).card["columns"]) == 3
    sleep = fitness(s, action="sleep_times", wake="7am")
    assert sleep.startswith("To wake at 07:00, go to bed at 21:46 or 23:16.")
    assert fitness(s, action="sleep_times", bedtime="23:00").card["rows"][1][2] == "06:44"


def test_appointments_and_checkups(s):
    records(s, action="appt_add", kind="dentist", date="2026-02-10")
    assert records(s, action="appt_add", kind="doctor", date="2026-10-02", time="9:15am") == \
        "Added doctor appointment on Friday 2 October at 09:15, in 4 days."
    out = records(s, action="appointments")
    assert out.card["kind"] == "table" and out.card["rows"][-1][3] == "in 4 days"
    assert "Dentist check-up: overdue since 10 Aug 2026" in out.card["text"]
    assert "Eye test: no visit logged" in out.card["text"]
    assert "confirm" in records(s, action="appt_remove", words="doctor")
    assert records(s, action="appt_remove", words="doctor", confirmed=True) == "Removed doctor on 2026-10-02."


def test_health_records(s):
    records(s, action="record_add", kind="vaccination", name="Flu jab", date="2025-10-12", note="Boots")
    out = records(s, action="records")
    assert out.card["rows"] == [["2025-10-12", "vaccination", "Flu jab", "Boots"]]
    assert "confirm" in records(s, action="record_remove", words="flu")
    assert records(s, action="record_remove", words="flu", confirmed=True).startswith("Removed Flu jab")


def test_cycle_tracker(s):
    for d in ("2026-07-06", "2026-08-03", "2026-09-02"):
        records(s, action="period_start", date=d)
    out = records(s, action="cycle")
    assert out.startswith("Average cycle 29 days; next period predicted around Thursday 1 October")
    cells = [c for row in out.card["rows"] for c in row]
    assert "2 •" in cells and "1 ?" in cells and "28 <" in cells
    with pytest.raises(ValueError):
        records(s, action="period_start", date="2026-12-01")
    assert records(s, action="period_remove", date="2026-09-02", confirmed=True).startswith("Removed")


def test_reminder_schedules(s):
    set_now(datetime(2026, 9, 26, 12, 0))  # a Saturday: weekday reminders start Monday
    assert remind(s, action="eye_breaks", start="09:00", end="12:00") == \
        "Set 4 reminders every weekday, every 60 minutes from 09:00 to 12:00: eye break."
    first = reminders.load(s)[0]
    assert first["at"] == "2026-09-28 09:00" and first["repeat"] == "weekdays"
    remind(s, action="hydration")
    assert len(reminders.load(s)) == 4 + 7
    remind(s, action="eye_breaks", every_minutes=90)  # replaces the old schedule
    assert len(rem._mine(s, "eye_breaks")) == 6
    shown = remind(s, action="show")
    assert shown.card["kind"] == "list" and shown.card["items"][1]["label"] == "Posture: off"
    assert "confirm" in remind(s, action="stop", kind="all")
    assert remind(s, action="stop", kind="all", confirmed=True) == "Cancelled 13 reminders."
    with pytest.raises(ValueError):
        remind(s, action="posture", every_minutes=30, start="06:00", end="22:00")


def test_health_plus_registered(s):
    names = {t["name"] for t in tools.client_tool_definitions(s)}
    assert {"health_log", "fitness_coach", "health_records", "health_reminders"} <= names
    for module in (logs, fit, rec, rem):
        for t in module.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
    assert {"wellness-trend", "wellness-intervals"} <= screen.EXTRA_KINDS

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            return await tools.run_tool("fitness_coach", {"action": "hr_zones", "age": 30}, s, http)

    assert asyncio.run(go()).startswith("Estimated maximum heart rate 190")
