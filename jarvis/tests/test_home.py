from datetime import datetime

import pytest

import homediary
import homehouse
import homekitchen
import homestore
import homewellbeing
import shopping
import tools
from config import Settings

CLOCK = {}


def set_now(when: datetime) -> None:
    CLOCK["now"] = when


@pytest.fixture
def s(tmp_path, monkeypatch):
    set_now(datetime(2026, 9, 28, 10, 30))
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def kitchen(s, **args):
    return homekitchen.run_tool("home_kitchen", args, s)


def house(s, **args):
    return homehouse.run_tool("home_household", args, s)


def well(s, **args):
    return homewellbeing.run_tool("home_wellbeing", args, s)


def test_meal_plan(s):
    assert kitchen(s, action="meal_week") == "No meals planned this week."
    assert kitchen(s, action="meal_set", day="wednesday", meal="Lasagne") == "Lasagne for dinner on Wednesday 30 September."
    kitchen(s, action="meal_set", day="today", meal="Porridge", slot="breakfast")
    kitchen(s, action="meal_set", day="2026-10-06", meal="Next week")
    assert kitchen(s, action="meal_week") == \
        "This week's meals:\n- Monday: breakfast Porridge\n- Wednesday: dinner Lasagne"
    assert "confirm" in kitchen(s, action="meal_clear")
    assert kitchen(s, action="meal_clear", confirmed=True) == "This week's meal plan is cleared."
    assert kitchen(s, action="meal_week") == "No meals planned this week."
    assert "2026-10-06" in homestore.load(s, "meals.json", {})


def test_recipes(s, tmp_path):
    assert kitchen(s, action="recipe_list") == "No recipes saved yet."
    out = kitchen(s, action="recipe_save", name="Pancakes", ingredients=["flour", "eggs", "milk"],
                  steps=["Whisk", "Fry"])
    assert out == "Saved the Pancakes recipe with 3 ingredients."
    text = (tmp_path / "Recipes" / "Pancakes.md").read_text()
    assert text == "# Pancakes\n\n## Ingredients\n- flour\n- eggs\n- milk\n\n## Method\n1. Whisk\n2. Fry\n"
    assert "confirm" in kitchen(s, action="recipe_save", name="pancakes", ingredients=["x"])
    assert kitchen(s, action="recipe_save", name="Pancakes", ingredients=["x"], confirmed=True) == \
        "Saved the Pancakes recipe with 1 ingredient."
    kitchen(s, action="recipe_save", name="Pancakes", ingredients=["flour", "eggs", "milk"], steps=["Whisk", "Fry"],
            confirmed=True)
    assert kitchen(s, action="recipe_list") == "1 recipe: Pancakes."
    assert kitchen(s, action="recipe_read", name="pancake") == text
    shopping.add(s, ["Milk"])
    assert kitchen(s, action="recipe_to_shopping", name="Pancakes") == \
        "From Pancakes: Added flour, eggs. 3 items on the list."
    with pytest.raises(ValueError):
        kitchen(s, action="recipe_read", name="soup")


def test_pantry(s):
    assert kitchen(s, action="pantry_list") == "The pantry list is empty."
    kitchen(s, action="pantry_add", items=["milk"], use_by="2026-09-29")
    kitchen(s, action="pantry_add", items=["yoghurt"], use_by="2026-09-27")
    kitchen(s, action="pantry_add", items=["cheese"], use_by="2026-10-20")
    assert kitchen(s, action="pantry_add", items=["rice"]) == "Added rice. 4 things in the pantry."
    assert kitchen(s, action="pantry_expiring") == "Going off soon:\n- yoghurt: past its date\n- milk: tomorrow"
    assert kitchen(s, action="pantry_use", items=["yog"]) == "Used up yoghurt. 3 left."
    assert kitchen(s, action="pantry_list") == \
        "In the pantry:\n- milk (use by 2026-09-29)\n- cheese (use by 2026-10-20)\n- rice"
    assert kitchen(s, action="pantry_expiring", days=0) == "Nothing goes off in the next 0 days."


def test_bins(s):
    assert house(s, action="bin_week") == "No bin days set up yet."
    assert house(s, action="bin_set", name="black", weekday="thursday") == "The black bin goes out every Thursday."
    out = house(s, action="bin_set", name="blue", weekday="thursday", fortnightly=True, start="2026-09-24")
    assert out == "The blue bin goes out every other Thursday, next on Thursday 8 October."
    assert house(s, action="bin_week") == "This week: the black bin goes out on Thursday 1 October."
    set_now(datetime(2026, 10, 8, 9, 0))
    assert house(s, action="bin_week") == "This week: the black bin goes out today; the blue bin goes out today."
    with pytest.raises(ValueError):
        house(s, action="bin_set", name="green", weekday="monday", start="2026-09-24")


def test_bills(s):
    assert house(s, action="bill_add", name="Rent", amount=900, day=1) == "The Rent bill is 900.00 GBP on day 1 of each month."
    house(s, action="bill_add", name="Council tax", amount=150.5, day=30)
    house(s, action="bill_add", name="Phone", amount=20, day=15)
    assert house(s, action="bills_due") == ("Bills due in the next 7 days (1,050.50 GBP):\n"
                                           "- Council tax: 150.50 GBP on Wednesday 30 September\n"
                                           "- Rent: 900.00 GBP on Thursday 1 October")
    assert house(s, action="bills_total") == "3 bills come to 1,070.50 GBP a month."
    assert "confirm" in house(s, action="bill_remove", name="phone")
    assert house(s, action="bill_remove", name="phone", confirmed=True) == "Removed the Phone bill."
    assert house(s, action="bills_due", days=1) == "No bills due in the next 1 day."


def test_subscriptions(s):
    house(s, action="sub_add", name="Netflix", amount=10.99)
    assert house(s, action="sub_add", name="Prime", amount=95, period="yearly") == "Added Prime at 95.00 GBP a year."
    out = house(s, action="subs_total")
    assert out.startswith("2 subscriptions: 18.91 GBP a month, 226.88 GBP a year.")
    assert "confirm" in house(s, action="sub_remove", name="netflix")
    assert house(s, action="sub_remove", name="netflix", confirmed=True) == "Removed the Netflix subscription."
    with pytest.raises(ValueError):
        house(s, action="sub_remove", name="disney", confirmed=True)


def test_key_dates(s):
    assert house(s, action="date_add", name="MOT", date="2026-11-10") == "MOT is due on Tuesday 10 November 2026."
    house(s, action="date_add", name="Boiler service", date="2027-03-01")
    house(s, action="date_add", name="Old", date="2026-01-01")
    assert house(s, action="dates_upcoming") == "Coming up in the next 60 days:\n- MOT: Tuesday 10 November (in 43 days)"
    assert house(s, action="dates_upcoming", days=10) == "Nothing due in the next 10 days."


def test_packing(s):
    assert house(s, action="pack_create", name="Spain", items=["passport", "charger", "sun cream"]) == \
        "The Spain packing list has 3 items."
    assert house(s, action="pack_tick", name="spain", items=["pass", "sun"]) == "Packed passport, sun cream. 1 left."
    assert house(s, action="pack_left", name="Spain") == "Still to pack for Spain: charger."
    house(s, action="pack_tick", name="Spain", items=["charger"])
    assert house(s, action="pack_left", name="Spain") == "Everything's packed for Spain."
    with pytest.raises(ValueError):
        house(s, action="pack_left", name="Paris")


def test_gifts(s):
    assert house(s, action="gift_list") == "No gift ideas saved yet."
    assert house(s, action="gift_add", name="Mum", idea="Scarf") == "Saved Scarf as a gift idea for Mum. 1 idea for them."
    house(s, action="gift_add", name="mum", idea="Candle")
    assert house(s, action="gift_list", name="Mum") == "Gift ideas for Mum: Scarf; Candle."
    assert house(s, action="gift_list", name="Dad") == "No gift ideas for Dad yet."


def test_plants(s):
    assert house(s, action="plants_due") == "No plants set up yet."
    assert house(s, action="plant_add", name="Fern", every=3) == "The Fern needs water every 3 days."
    house(s, action="plant_add", name="Cactus", every=14)
    assert house(s, action="plants_due") == "No plants need water today."
    set_now(datetime(2026, 10, 1, 9, 0))
    assert house(s, action="plants_due") == "Needs water today: Fern."
    assert house(s, action="plant_watered", items=["fern"]) == "Watered Fern."
    assert house(s, action="plants_due") == "No plants need water today."
    assert house(s, action="plant_watered") == "Watered Fern, Cactus."


def test_medication(s):
    assert well(s, action="med_check", name="ibuprofen") == "No ibuprofen logged today."
    assert well(s, action="med_taken", name="Ibuprofen") == "Logged Ibuprofen at 10:30. That's 1 dose of it today."
    set_now(datetime(2026, 9, 28, 18, 5))
    well(s, action="med_taken", name="ibuprofen")
    assert well(s, action="med_check", name="ibuprofen") == "Yes, Ibuprofen logged today at 10:30, 18:05."
    assert well(s, action="med_today") == "Today's doses: Ibuprofen at 10:30; ibuprofen at 18:05."
    set_now(datetime(2026, 9, 29, 8, 0))
    assert well(s, action="med_today") == "No doses logged today."


def test_water(s):
    assert well(s, action="water_today") == "0 glasses of water today out of 8; 8 glasses to go."
    assert well(s, action="water_add") == "1 glass of water today out of 8; 7 glasses to go."
    assert well(s, action="water_add", glasses=2, goal=3) == "3 glasses of water today out of 3; goal reached."


def test_sleep(s):
    assert well(s, action="sleep_week") == "No sleep logged this past week."
    assert well(s, action="sleep_log", hours=7.5) == "Logged 7.5 hours of sleep last night."
    set_now(datetime(2026, 9, 29, 8, 0))
    well(s, action="sleep_log", hours=6)
    assert well(s, action="sleep_week") == \
        "Over the last 2 nights logged this week you averaged 6.8 hours; shortest 6, longest 7.5."


def test_mood(s):
    assert well(s, action="mood_week") == "No moods logged this past week."
    assert well(s, action="mood_log", mood=4, note="Nice walk") == "Logged your mood as 4, good."
    well(s, action="mood_log", mood=2)
    assert well(s, action="mood_week") == \
        "Mood this week: average 3.0 out of 5 over 2 entries.\n- 2026-09-28: 4, Nice walk\n- 2026-09-28: 2"
    with pytest.raises(ValueError):
        well(s, action="mood_log", mood=9)


def test_diary(s, tmp_path):
    diary = lambda **a: homediary.run_tool("home_diary", a, s)  # noqa: E731
    assert diary(action="read") == "No diary entry for Monday 28 September."
    assert diary(action="add", text="Good day.") == "Added to your diary for Monday 28 September."
    diary(action="add", text="Forgot this.", day="yesterday")
    set_now(datetime(2026, 9, 28, 21, 15))
    diary(action="add", text="Evening too.")
    assert diary(action="read", day="2026-09-28") == \
        "# Monday 28 September 2026\n\n## 10:30\n\nGood day.\n\n## 21:15\n\nEvening too.\n"
    assert (tmp_path / "Diary" / "2026-09-27.md").exists()


def test_home_tools_registered():
    names = [t["name"] for t in tools.client_tool_definitions(Settings())]
    assert {"home_kitchen", "home_household", "home_wellbeing", "home_diary"} <= set(names)
    for module in (homekitchen, homehouse, homewellbeing, homediary):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
