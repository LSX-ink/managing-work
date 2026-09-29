import asyncio
from datetime import date

import httpx
import pytest

import active_calc
import active_log
import active_outdoors
import active_store
import active_workout
import screen
import tools
from config import Settings

TODAY = date(2026, 9, 29)  # a Tuesday


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(active_store, "today", lambda: TODAY)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), city="Leeds")


def wo(**a):
    return active_workout.run_tool("active_workout", a, Settings())


def lg(s, **a):
    return active_log.run_tool("active_log", a, s)


def calc(**a):
    return active_calc.run_tool("active_calc", a, Settings())


def out(s, routes=None, **a):
    async def go():
        transport = httpx.MockTransport(routes or (lambda r: httpx.Response(404)))
        async with httpx.AsyncClient(transport=transport) as http:
            return await active_outdoors.run_tool("active_outdoors", a, s, http)
    return asyncio.run(go())


def test_registered_and_kinds():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"active_workout", "active_log", "active_calc", "active_outdoors"} <= names
    assert {"active-timer", "active-steps", "active-calendar"} <= screen.EXTRA_KINDS


# ---- workouts ---------------------------------------------------------------------------------

@pytest.mark.parametrize("gear", ["bodyweight", "dumbbell", "gym"])
@pytest.mark.parametrize("focus", ["full body", "upper body", "lower body", "core", "cardio"])
def test_build_every_combination(focus, gear):
    shown = wo(action="build", focus=focus, equipment=gear, minutes=25)
    assert shown.card["kind"] == "table" and len(shown.card["rows"]) >= 5
    assert shown.card["buttons"][0]["say"].startswith("Start a 25 minute")


def test_build_gear_matches_and_errors():
    shown = wo(action="build", focus="upper body", equipment="gym", minutes=20)
    assert "Bench press" in [r[0] for r in shown.card["rows"]]
    body = wo(action="build", equipment="bodyweight", minutes=30)
    assert not {"Bench press", "Deadlift"} & {r[0] for r in body.card["rows"]}
    with pytest.raises(ValueError):
        wo(action="build", focus="elbows")
    with pytest.raises(ValueError):
        wo(action="build", minutes=500)


def test_guided_timer():
    shown = wo(action="timer", focus="core", minutes=10)
    d = shown.card["data"]
    assert shown.card["kind"] == "active-timer" and d["steps"][0]["kind"] == "prep"
    work = [x for x in d["steps"] if x["kind"] == "work"]
    assert work[0]["next"] == work[1]["label"] and d["steps"][-1]["next"] == "Finished"
    assert d["total"] == sum(x["seconds"] for x in d["steps"])
    assert wo(action="timer", work_seconds=30, rest_seconds=0).card["data"]["steps"][1]["kind"] == "work"


def test_emom_and_circuit():
    emom = wo(action="emom", minutes=6, exercises=["10 press-ups", "15 squats"])
    steps = emom.card["data"]["steps"]
    assert [x["label"] for x in steps[1:4]] == ["10 press-ups", "15 squats", "10 press-ups"]
    assert steps[1]["next"] == "Minute 2: 15 squats" and emom.card["kind"] == "active-timer"
    assert wo(action="emom").card["data"]["steps"][1]["seconds"] == 60
    circ = wo(action="circuit", exercises=["Star jumps", "Skipping"], work_seconds=30, rest_seconds=15, rounds=2)
    labels = [x["label"] for x in circ.card["data"]["steps"]]
    assert labels.count("Star jumps") == 2 and labels.count("Rest") == 3
    with pytest.raises(ValueError):
        wo(action="circuit")
    with pytest.raises(ValueError):
        wo(action="circuit", exercises=["Burpees", "Squats"], work_seconds=300, rest_seconds=300, rounds=12)


@pytest.mark.parametrize("routine", ["morning", "after run", "pre-run warm-up", "lower back", "evening"])
def test_stretch(routine):
    shown = wo(action="stretch", routine=routine)
    assert shown.card["kind"] == "active-steps" and all(x["seconds"] for x in shown.card["data"]["steps"])


def test_stretch_unknown():
    with pytest.raises(ValueError):
        wo(action="stretch", routine="yoga headstands")


def test_howto_and_list():
    shown = wo(action="howto", exercise="pushups")
    assert shown.card["title"] == "Press-up" and "Common mistake" in shown.card["text"]
    assert wo(action="howto", exercise="deadlift").card["kind"] == "text"
    with pytest.raises(ValueError):
        wo(action="howto", exercise="moonwalk")
    every = wo(action="exercises")
    assert len(every.card["rows"]) >= 30
    gym = wo(action="exercises", equipment="gym")
    assert {r[1] for r in gym.card["rows"]} == {"gym"}


def test_unknown_action(s):
    for call in (lambda: wo(action="nope"), lambda: lg(s, action="nope"), lambda: calc(action="nope"),
                 lambda: out(s, action="nope")):
        with pytest.raises(ValueError):
            call()


# ---- activity log -----------------------------------------------------------------------------

def test_log_pace_speed_and_miles(s):
    assert "5:33 per km" in lg(s, action="log", kind="run", distance=5, time="27:45")
    assert "km/h" in lg(s, action="log", kind="cycling", distance=20, minutes=60)
    said = lg(s, action="log", kind="walk", distance=3, unit="miles", time="1:00:00")
    assert "4.8 km" in said and "12:26 per km" in said
    assert "fastest" in lg(s, action="log", kind="run", distance=5, time="25:00")
    assert lg(s, action="log", kind="swim", minutes=30) == "Logged swim, 30 minutes."
    with pytest.raises(ValueError):
        lg(s, action="log", kind="run", distance=5)
    with pytest.raises(ValueError):
        lg(s, action="log", kind="run", distance=5, time="abc")


def test_week_history_records(s):
    assert "Nothing logged" in lg(s, action="week")
    lg(s, action="log", kind="run", distance=5, time="30:00", date="2026-09-28")
    lg(s, action="log", kind="walk", distance=8, time="1:40:00", date="2026-09-22")
    lg(s, action="log", kind="cycle", distance=30, minutes=90, date="2026-09-01", note="canal")
    week = lg(s, action="week")
    assert week.card["kind"] == "chart" and week.card["chart"]["values"][-1] == 5 and len(week.card["chart"]["labels"]) == 8
    assert week.card["chart"]["values"][-2] == 8
    only = lg(s, action="week", kind="walk")
    assert only.card["chart"]["values"][-1] == 0
    hist = lg(s, action="history")
    assert hist.card["kind"] == "table" and hist.card["rows"][0][1] == "cycle"
    rec = lg(s, action="records")
    assert {r[0] for r in rec.card["rows"]} == {"Run", "Walk", "Cycle"}


def test_undo(s):
    assert lg(s, action="undo") == "There's nothing to undo."
    lg(s, action="log", kind="run", distance=5, time="30:00")
    assert "confirm" in lg(s, action="undo")
    assert active_store.section(s, "log", [])
    assert lg(s, action="undo", confirmed=True).startswith("Removed")
    assert active_store.section(s, "log", []) == []


def test_rest_day(s):
    fresh = lg(s, action="rest_day")
    assert fresh.card["kind"] == "table" and "well rested" in fresh
    for d in ("2026-09-27", "2026-09-28", "2026-09-29"):
        lg(s, action="log", kind="run", distance=5, time="30:00", date=d)
    assert "rest day" in lg(s, action="rest_day")


def test_rest_day_after_long_day_and_strength(s):
    lg(s, action="log", kind="hike", distance=20, time="5:00:00", date="2026-09-28")
    assert "Go easy" in lg(s, action="rest_day")
    other = Settings(memory_dir=str(s.memory_dir) + "/x")
    lg(other, action="strength_log", exercise="Squat", weight_kg=60, reps=5, date="2026-09-28")
    assert "fine to train" in lg(other, action="rest_day")


def test_strength(s):
    assert "No lifts" in lg(s, action="strength_progress")
    said = lg(s, action="strength_log", exercise="Squat", weight_kg=100, reps=5, sets=3, date="2026-09-01")
    assert "116.7 kg" in said and "3 x 5" in said
    assert "personal best" in lg(s, action="strength_log", exercise="squat", weight_kg=105, reps=5, date="2026-09-15")
    lg(s, action="strength_log", exercise="Bench press", weight_kg=60, reps=1)
    table = lg(s, action="strength_progress")
    assert table.card["kind"] == "table" and len(table.card["rows"]) == 2
    chart = lg(s, action="strength_progress", exercise="SQUAT")
    assert chart.card["chart"]["type"] == "line" and chart.card["chart"]["values"] == [116.7, 122.5]
    with pytest.raises(ValueError):
        lg(s, action="strength_progress", exercise="Curl")
    with pytest.raises(ValueError):
        lg(s, action="strength_log", exercise="Squat", weight_kg=100)


def test_challenge_lifecycle(s):
    assert "Day 1 is 20 seconds plank" in lg(s, action="challenge_start", name="plank", date="2026-09-25")
    with pytest.raises(ValueError):
        lg(s, action="challenge_start", name="Plank")
    lg(s, action="challenge_check", name="plank", date="2026-09-27")
    lg(s, action="challenge_check", name="plank", date="2026-09-28")
    said = lg(s, action="challenge_check")
    assert "Day 5 done" in said and "3 days in a row" in said
    shown = lg(s, action="challenge_show")
    d = shown.card["data"]
    states = [x["state"] for x in d["days"][:6]]
    assert shown.card["kind"] == "active-calendar" and d["days"][4]["target"] == 60
    assert states[:2] == ["missed", "missed"]
    assert states[2:5] == ["done"] * 3
    assert len(d["days"]) == 30 and d["days"][6]["state"] == "rest"
    assert "rest day" in lg(s, action="challenge_check", name="plank", date="2026-10-01")
    with pytest.raises(ValueError):
        lg(s, action="challenge_check", name="plank", date="2026-12-25")
    assert "confirm" in lg(s, action="challenge_stop", name="plank")
    assert "Stopped" in lg(s, action="challenge_stop", name="plank", confirmed=True)
    with pytest.raises(ValueError):
        lg(s, action="challenge_show")


def test_custom_challenge_and_streak_rest(s):
    lg(s, action="challenge_start", name="star jumps", days=10, unit_name="jumps", start_target=20, step=2,
       date="2026-09-29")
    lg(s, action="challenge_start", name="squats", date="2026-09-29")
    with pytest.raises(ValueError):
        lg(s, action="challenge_check")
    assert "Day 1 done: 20 jumps" in lg(s, action="challenge_check", name="star")
    assert active_log.challenge.target(active_store.section(s, "challenges", [])[0], 3) == 24


# ---- calculators ------------------------------------------------------------------------------

def test_pace_and_finish_time():
    shown = calc(action="pace", distance=5, time="25:00")
    assert "5:00 per km" in shown and shown.card["kind"] == "table"
    assert shown.card["rows"][-1] == ["At this pace: Marathon", "3:30:58"]
    assert "8:03 per mile" in calc(action="pace", race="5k", minutes=25)
    fin = calc(action="finish_time", race="10k", pace="5:30")
    assert "55 minutes" in fin and fin.card["rows"][0][1] == "55:00"
    assert "1:40:00" in [r[1] for r in calc(action="finish_time", distance=10, speed_kmh=6).card["rows"]]
    mile = calc(action="finish_time", race="5k", pace="8:00", pace_unit="mile")
    assert mile.card["rows"][0][1] == "24:51"
    with pytest.raises(ValueError):
        calc(action="finish_time", race="5k")
    with pytest.raises(ValueError):
        calc(action="pace", race="ultra", time="30:00")


def test_race_predict_and_splits():
    shown = calc(action="race_predict", race="5k", time="25:00")
    assert [r[0] for r in shown.card["rows"]] == ["5K", "10K", "Half Marathon", "Marathon"]
    assert shown.card["rows"][1][1] == "52:07"
    sp = calc(action="splits", distance=5, time="25:00")
    assert len(sp.card["rows"]) == 5 and sp.card["rows"][-1][2] == "25:00"
    miles = calc(action="splits", race="10k", time="50:00", per="mile")
    assert miles.card["rows"][0][1] == "8:03" and miles.card["rows"][-1][0].startswith("last")


def test_calories_and_met_table():
    shown = calc(action="calories", activity="brisk walk", minutes=60, weight_kg=70)
    assert "301 calories" in shown and int(shown.card["rows"][0][1]) > 301
    assert calc(action="calories", activity="running", minutes=30, weight_kg=80).card["kind"] == "table"
    with pytest.raises(ValueError):
        calc(action="calories", activity="curling", minutes=30, weight_kg=80)
    with pytest.raises(ValueError):
        calc(action="calories", activity="run", minutes=30)
    met = calc(action="met_table")
    assert met.card["kind"] == "table" and len(met.card["rows"]) >= 20


def test_one_rep_max():
    shown = calc(action="one_rep_max", weight_kg=80, reps=5)
    assert "91.7 kilos" in shown
    assert shown.card["rows"][0][0] == "100%"
    assert "60 kilos" not in calc(action="one_rep_max", weight_kg=100, reps=1)
    with pytest.raises(ValueError):
        calc(action="one_rep_max", weight_kg=80, reps=50)


# ---- outdoors ---------------------------------------------------------------------------------

def forecast_routes(temp=12, pop=5, wind=6, times=None):
    hours = [f"2026-09-29T{h:02d}:00" for h in range(24)]

    def handler(request):
        url = str(request.url)
        if "geocoding" in url:
            return httpx.Response(200, json={"results": [{"name": "Leeds", "latitude": 53.8, "longitude": -1.55}]})
        assert "wind_speed_unit=mph" in url
        return httpx.Response(200, json={
            "current": {"time": "2026-09-29T15:00", "temperature_2m": temp},
            "hourly": {"time": hours, "temperature_2m": [temp] * 24, "precipitation_probability": [pop] * 24,
                       "precipitation": [0] * 24, "wind_speed_10m": [wind] * 24, "wind_gusts_10m": [wind + 5] * 24},
            "daily": {"sunrise": ["2026-09-29T07:05"], "sunset": ["2026-09-29T19:00"], "uv_index_max": [4.2]}})
    return handler


def test_weather_good_and_poor(s):
    good = out(s, forecast_routes(), action="weather", kind="run")
    assert good.startswith("Yes, good weather for a run in Leeds")
    chart = good.card["chart"]
    assert chart["labels"][0] == "15:00" and chart["labels"][-1] == "18:00" and good.card["kind"] == "chart"
    assert "UV up to 4.2 (moderate)" in good
    poor = out(s, forecast_routes(temp=2, pop=90, wind=30), action="weather", kind="cycling")
    assert poor.startswith("Not great") and "very windy" in poor
    assert out(s, forecast_routes(), action="weather", kind="walk", city="York").startswith("Yes")


def test_weather_errors(s):
    with pytest.raises(ValueError):
        out(s, action="weather", kind="skiing")
    with pytest.raises(ValueError):
        out(s, lambda r: httpx.Response(500), action="weather", kind="run")
    late = forecast_routes()

    def evening(request):
        r = late(request)
        if "geocoding" in str(request.url):
            return r
        body = r.json()
        body["current"]["time"] = "2026-09-29T21:00"
        return httpx.Response(200, json=body)
    assert "no daylight left" in out(s, evening, action="weather", kind="run")
    assert out(Settings(memory_dir=s.memory_dir, city=""), forecast_routes(), action="weather", kind="run", city="Leeds")
    with pytest.raises(ValueError):
        out(Settings(memory_dir=s.memory_dir, city=""), forecast_routes(), action="weather", kind="run")


@pytest.mark.parametrize("trip,count", [("day walk", 11), ("hill walk", 15), ("winter", 15), ("overnight", 15)])
def test_kit(s, trip, count):
    shown = out(s, action="kit", trip=trip)
    assert shown.card["kind"] == "list" and shown.card["checks"] and len(shown.card["items"]) == count
    assert out(s, action="kit").card["title"] == "Day walk kit"
    with pytest.raises(ValueError):
        out(s, action="kit", trip="moon landing")


def test_countryside_code_and_hill_safety(s):
    code = out(s, action="countryside_code")
    assert code.card["kind"] == "text" and "Take your litter home" in code.card["text"]
    assert "Scotland" in code.card["text"]
    safety = out(s, action="hill_safety")
    assert safety.card["kind"] == "list" and "999" in safety and any("whistle" in i["label"] for i in safety.card["items"])


def test_routes(s):
    assert "No routes" in out(s, action="route_list")
    assert out(s, action="route_save", name="Ilkley Moor", distance=8, note="muddy after rain") == \
        "Saved the route Ilkley Moor, 8.0 km (5.0 miles)."
    out(s, action="route_save", name="canal loop", distance=3, unit="miles", kind="run")
    assert out(s, action="route_save", name="ilkley moor", note="lovely views").startswith("Updated")
    shown = out(s, action="route_list")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][3] == "lovely views"
    assert shown.card["rows"][1][1] == "4.8 km" and shown.card["buttons"][1]["say"].endswith("my canal loop route")
    assert "confirm" in out(s, action="route_remove", name="canal")
    assert out(s, action="route_remove", name="canal", confirmed=True) == "Removed the route canal loop."
    with pytest.raises(ValueError):
        out(s, action="route_remove", name="canal", confirmed=True)


def test_all_cards_pass_through_screen_checks(s):
    for shown in (wo(action="timer"), wo(action="stretch", routine="morning"),
                  lg(s, action="challenge_start", name="plank") and lg(s, action="challenge_show")):
        assert isinstance(shown, screen.Shown) and shown.card["kind"] in screen.KINDS | screen.EXTRA_KINDS
