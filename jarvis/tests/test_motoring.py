import csv
from datetime import datetime

import pytest

import homestore
import motoring_car
import motoring_costs
import motoring_guide
import motoring_store
import motoring_theory
import reminders
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 28, 10, 30))
    return Settings(memory_dir=str(tmp_path), city="London", currency="GBP")


def car(s, **args):
    return motoring_car.run_tool("motoring_car", args, s)


def costs(s, **args):
    return motoring_costs.run_tool("motoring_costs", args, s)


def guide(s, **args):
    return motoring_guide.run_tool("motoring_guide", args, s)


def theory(s, **args):
    return motoring_theory.run_tool("motoring_theory", args, s)


def test_registered_and_schemas():
    names = {t["name"] for m in (motoring_car, motoring_costs, motoring_guide, motoring_theory) for t in m.tool_definitions()}
    assert names == {"motoring_car", "motoring_costs", "motoring_guide", "motoring_theory"}
    assert all(m in tools.ABILITIES for m in (motoring_car, motoring_costs, motoring_guide, motoring_theory))
    for m in (motoring_car, motoring_costs, motoring_guide, motoring_theory):
        for t in m.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
            assert set(t["input_schema"]["properties"]["action"]["enum"]) == set(m.ACTIONS)


def test_profile_keeps_reg_off_the_speech(s):
    with pytest.raises(ValueError):
        car(s, action="profile_set")
    assert "Saved your car" in car(s, action="profile_set", make="Ford", model="Focus", year=2018, mpg=48, reg="ab12 cde")
    shown = car(s, action="profile_show")
    assert isinstance(shown, screen.Shown)
    assert "AB12" not in str(shown) and "AB12 CDE" in str(shown.card["rows"])
    assert motoring_store.car_mpg(s) == 48


def test_dates_countdown_reminder_and_remove(s):
    said = car(s, action="date_set", kind="mot", due="2026-11-10")
    assert "MOT due Tuesday 10 November 2026" in said and "remind you 14 days before" in said
    assert reminders.load(s)[0]["at"] == "2026-10-27 09:00"
    assert "less than 2 weeks" in car(s, action="date_set", kind="tax", due="2026-10-05")
    shown = car(s, action="dates_show")
    assert shown.card["rows"][0] == ["Tax", "5 Oct 2026", "7 days - soon"]
    assert "Next up: Tax" in shown
    assert "confirm" in car(s, action="date_remove", kind="tax")
    assert car(s, action="date_remove", kind="tax", confirmed=True) == "Removed the Tax date."
    assert len(car(s, action="dates_show").card["rows"]) == 1


def test_service_log_next_due(s):
    assert "Logged Oil change" in car(s, action="service_add", job="Oil change", miles=41000, cost=89.99,
                                      next_miles=51000, next_months=12)
    car(s, action="service_add", job="Brakes", cost=120)
    shown = car(s, action="service_show")
    assert shown.card["rows"][1][0] == "Oil change" and shown.card["rows"][1][4] == "28 Sep 2027 or 51,000 mi"
    assert "209.99 pounds" in shown and "Next due: Oil change" in shown
    assert car(s, action="service_show", job="brakes").card["rows"][0][0] == "Brakes"
    assert car(s, action="service_show", job="tyres") == "Nothing logged for tyres."


def test_tyres(s):
    assert "below the 1.6 mm" in car(s, action="tyre_note", position="front left", tread_mm=1.4, psi=32)
    assert "Getting low" in car(s, action="tyre_note", position="rear left", tread_mm=2.5)
    car(s, action="tyre_note", position="all", psi=33)
    shown = car(s, action="tyre_show")
    assert len(shown.card["rows"]) == 4 and "Low tread on the front left, rear left" in shown
    with pytest.raises(ValueError):
        car(s, action="tyre_note", position="front left")


def test_parking_timer(s):
    shown = car(s, action="park_timer", minutes=120, note="Level 2 car park")
    assert shown.card["kind"] == "timer" and shown.card["ends_at"] == int(datetime(2026, 9, 28, 12, 30).timestamp() * 1000)
    assert "ends at 12:30" in shown
    assert reminders.load(s)[0]["at"] == "2026-09-28 12:25"


def test_trip_cost_uses_car_mpg(s):
    with pytest.raises(ValueError):
        costs(s, action="trip_cost", distance=100, pence_per_litre=140)
    car(s, action="profile_set", mpg=45)
    shown = costs(s, action="trip_cost", distance=120, pence_per_litre=145.9)
    assert "about 17.69 pounds" in shown and isinstance(shown, screen.Shown)
    assert costs(s, action="trip_cost", distance=60, round_trip=True, pence_per_litre=145.9, mpg=45).card["rows"][0][1] == "120.0 miles"
    km = costs(s, action="trip_cost", distance=160.9344, unit="km", mpg=45, pence_per_litre=145.9)
    assert km.card["rows"][0][1].startswith("100.0")


def test_ev_cost(s):
    by_miles = costs(s, action="ev_cost", distance=100, miles_per_kwh=4, pence_per_kwh=25)
    assert "25.0 kWh costs about 6.25 pounds" in by_miles
    by_percent = costs(s, action="ev_cost", battery_kwh=60, from_percent=20, to_percent=80, pence_per_kwh=10)
    assert "36.0 kWh costs about 3.60 pounds" in by_percent
    assert "costs about 5.00" in costs(s, action="ev_cost", kwh=20, pence_per_kwh=25)
    with pytest.raises(ValueError):
        costs(s, action="ev_cost", battery_kwh=60, from_percent=80, to_percent=20, pence_per_kwh=10)


def test_mileage_rates_table_and_csv(s, tmp_path):
    costs(s, action="mileage_add", distance=9_990, date="2026-05-01", purpose="Sales trips")
    said = costs(s, action="mileage_add", distance=20, date="2026-06-01", **{"from": "Leeds", "to": "York"}, purpose="Client")
    assert "10,010 car miles" in said and "4502.50 pounds" in said
    shown = costs(s, action="mileage_show")
    assert shown.card["rows"][-1] == ["Total", "", "", "10,010.0", "4502.50"]
    assert shown.card["rows"][-2][1] == "Leeds to York"
    costs(s, action="mileage_add", distance=50, date="2026-03-01", vehicle="motorbike")
    assert len(costs(s, action="mileage_show", tax_year=2025).card["rows"]) == 2
    exported = costs(s, action="mileage_export")
    assert exported.card["kind"] == "file"
    rows = list(csv.reader((tmp_path / "Personal" / "work-mileage-2026-2027.csv").open()))
    assert rows[0][0] == "Date" and rows[-1][1:3] == ["Leeds", "York"] and rows[-1][-1] == "7.00"
    assert costs(s, action="mileage_show", tax_year=2020).startswith("No work mileage")


def test_split_and_journey(s):
    assert "12.50 pounds between 4 is 3.12 pounds each" in costs(s, action="split_cost", total=12.5, people=4)
    shown = costs(s, action="split_cost", distance=100, round_trip=True, pence_per_mile=20, people=4)
    assert shown.card["rows"][2] == ["Each", "10.00 pounds"]
    time = costs(s, action="journey_calc", distance=150, speed_mph=50)
    assert "3 h 0 min" in time
    assert "60 mph" in costs(s, action="journey_calc", distance=90, minutes=90)
    assert costs(s, action="journey_calc", speed_mph=30, minutes=90).card["rows"][0][1].startswith("45.0")
    with pytest.raises(ValueError):
        costs(s, action="journey_calc", distance=10)


def test_commute_chart(s):
    assert costs(s, action="commute_chart").startswith("No commutes")
    for day, minutes in [("2026-09-21", 30), ("2026-09-22", 40), ("2026-09-28", 50)]:
        said = costs(s, action="commute_add", minutes=minutes, date=day)
    assert "average over 3 journeys is 40 minutes" in said
    shown = costs(s, action="commute_chart")
    assert shown.card["chart"]["labels"] == ["Mon", "Tue"] and shown.card["chart"]["values"] == [40.0, 40.0]
    recent = costs(s, action="commute_chart", view="recent")
    assert recent.card["chart"]["type"] == "line" and len(recent.card["chart"]["values"]) == 3
    assert "best 30, worst 50" in shown


def test_guide_tables_and_lists(s):
    assert guide(s, action="speed_limits").card["rows"][0][:2] == ["Cars and motorbikes", "30"]
    stop = guide(s, action="stopping_distances", speed=30)
    assert "23 metres" in stop and len(stop.card["rows"]) == 6
    assert guide(s, action="zones").card["kind"] == "table"
    one = guide(s, action="warning_lights", light="oil")
    assert one.card["kind"] == "motoring-lights" and "red" in one and len(one.card["data"]["lights"]) == 1
    assert len(guide(s, action="warning_lights").card["data"]["lights"]) > 10
    for name in motoring_guide.LISTS:
        shown = guide(s, action="checklist", list=name)
        assert shown.card["kind"] == "list" and shown.card["items"]
    with pytest.raises(ValueError):
        guide(s, action="checklist")


def test_theory_quiz(s):
    assert theory(s, action="quiz_score").startswith("You haven't")
    first = theory(s, action="quiz_start")
    assert first.card["kind"] == "motoring-quiz" and len(first.card["data"]["choices"]) == 4
    state = motoring_theory._state(s)
    right = state["pending"]["answer"]
    correct = theory(s, action="quiz_answer", answer=right)
    assert correct.startswith("Correct.")
    state = motoring_theory._state(s)
    wrong = "ABCD".replace(state["pending"]["answer"], "")[0]
    missed = theory(s, action="quiz_answer", answer=f"{wrong}, whatever")
    assert missed.startswith("Not quite")
    score = theory(s, action="quiz_score")
    assert "1 of 2 right, 50 percent" in score
    assert missed.card["data"]["score"] == "1 of 2"


def test_theory_answer_by_words_and_no_pending(s):
    assert theory(s, action="quiz_answer", answer="A").startswith("There's no question")
    theory(s, action="quiz_start")
    pending = motoring_theory._state(s)["pending"]
    text = pending["choices"]["ABCD".index(pending["answer"])]
    assert theory(s, action="quiz_answer", answer=text).startswith("Correct.")
    with pytest.raises(ValueError):
        theory(s, action="quiz_answer", answer="banana")


def test_unknown_action(s):
    for fn in (car, costs, guide, theory):
        with pytest.raises(ValueError):
            fn(s, action="nope")
