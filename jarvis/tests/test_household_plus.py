import asyncio
from datetime import datetime

import pytest

import homestore
import household_chores
import household_family
import household_meters
import household_stuff
import screen
import timers
import tools
from config import Settings

CLOCK = {}


@pytest.fixture
def s(tmp_path, monkeypatch):
    CLOCK["now"] = datetime(2026, 9, 28, 10, 30)  # a Monday
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path), currency="GBP")


def chores(s, **args):
    return asyncio.run(household_chores.run_tool("household_chores", args, s))


def stuff(s, **args):
    return household_stuff.run_tool("household_stuff", args, s)


def meters(s, **args):
    return household_meters.run_tool("household_meters", args, s)


def family(s, **args):
    return household_family.run_tool("household_family", args, s)


def test_registered_with_few_tools():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"household_chores", "household_stuff", "household_meters", "household_family"} <= names
    for module in (household_chores, household_stuff, household_meters, household_family):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False


def test_chores_rota(s):
    with pytest.raises(ValueError):
        chores(s, action="rota_week")
    assert chores(s, action="rota_people", items=["Sam", "Alex"]) == "The rota is Sam, Alex."
    assert chores(s, action="rota_add", items=["Hoover", "Bins", "Dishes"]) == "Added Hoover, Bins, Dishes. 3 chores on the rota."
    shown = chores(s, action="rota_week")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "table"
    this_week = {r[0]: r[1] for r in shown.card["rows"]}
    assert this_week["Hoover"] != this_week["Bins"]
    assert chores(s, action="rota_whose", name="hoover") == f"It's {this_week['Hoover']}'s turn to do Hoover this week."
    nxt = chores(s, action="rota_next")
    assert {r[0]: r[1] for r in nxt.card["rows"]}["Hoover"] == this_week["Bins"]
    assert chores(s, action="rota_done", items=["hoover"]) == "Marked Hoover done. Still to do: Bins, Dishes."
    assert chores(s, action="rota_week").card["rows"][0][2] == "done"
    assert "confirm" in chores(s, action="rota_remove", name="dishes")
    assert chores(s, action="rota_remove", name="dishes", confirmed=True) == "Took Dishes off the rota."


def test_cleaning_schedule(s):
    assert chores(s, action="clean_due") == "No cleaning jobs set up yet."
    chores(s, action="clean_add", name="Bathroom", every=7, date="2026-09-20")
    chores(s, action="clean_add", name="Fridge", every=30, date="2026-09-20")
    chores(s, action="clean_add", name="Bedding", every=14)
    shown = chores(s, action="clean_due")
    assert str(shown) == "Cleaning due today: Bathroom, Bedding."
    assert shown.card["checks"] and shown.card["items"][0]["say"] == "I've done the cleaning job Bathroom."
    assert "(due 1 day ago)" in shown.card["items"][0]["label"]
    assert chores(s, action="clean_done", items=["bathroom"]) == "Done: Bathroom, next Monday 5 October."
    assert chores(s, action="clean_list").card["rows"][-1][0] == "Fridge"


def test_maintenance(s):
    assert chores(s, action="fix_add", name="Smoke alarm test", months=1, date="2026-08-29") == \
        "Smoke alarm test every 1 month, next due Tuesday 29 September."
    chores(s, action="fix_add", name="Gutters", months=12, date="2026-03-01")
    shown = chores(s, action="fix_due")
    assert str(shown) == "Due this month: Smoke alarm test."
    assert shown.card["rows"][0][3] == "this month"
    assert chores(s, action="fix_done", name="smoke") == "Marked Smoke alarm test done. Next due Wednesday 28 October 2026."


def test_laundry(s):
    shown = chores(s, action="laundry_symbol", query="triangle with two lines")
    assert str(shown) == "Triangle with two slanted lines: Only non-chlorine (oxygen) bleach."
    assert len(chores(s, action="laundry_symbols").card["rows"]) >= 20
    with pytest.raises(ValueError):
        chores(s, action="laundry_symbol", query="zebra")

    async def go():
        out = await household_chores.run_tool("household_chores", {"action": "laundry_timer", "minutes": 45}, s)
        timers.cancel_timer("laundry")
        return out

    shown = asyncio.run(go())
    assert str(shown) == "The laundry timer set for 45 minutes."
    assert shown.card["kind"] == "timer" and shown.card["ends_at"] > 0


def test_inventory(s):
    assert stuff(s, action="inv_list") == "Nothing in the home inventory yet."
    assert stuff(s, action="inv_add", name="TV", room="lounge", amount=499, date="2025-01-10", until="2026-11-01") == \
        "Saved TV in the Lounge, worth 499.00 GBP, under warranty until Sunday 1 November."
    stuff(s, action="inv_add", name="Sofa", room="Lounge", amount=800)
    stuff(s, action="inv_add", name="Kettle", room="Kitchen", amount=30, until="2027-06-01")
    assert str(stuff(s, action="inv_list")) == "3 items worth 1,329.00 GBP; it's on the screen."
    shown = stuff(s, action="inv_warranties")
    assert str(shown) == "1 warranty ending soon; the first is TV on Sunday 1 November."
    chart = stuff(s, action="inv_rooms").card["chart"]
    assert chart["labels"] == ["Lounge", "Kitchen"] and chart["values"] == [1299, 30]
    assert stuff(s, action="inv_remove", name="kettle", confirmed=True) == "Removed the Kettle inventory item."


def test_freezer(s):
    stuff(s, action="freezer_add", items=["chilli"], date="2026-06-01")
    assert stuff(s, action="freezer_add", items=["peas", "bread"]) == "Frozen peas, bread. 3 things in the freezer."
    shown = stuff(s, action="freezer_list")
    assert str(shown) == "3 things in the freezer; chilli has been in longest, 119 days."
    assert stuff(s, action="freezer_take", items=["chilli"]) == "Took out chilli. 2 things left."


def test_price_book(s):
    stuff(s, action="price_add", name="Milk", shop="tesco", amount=1.45, date="2026-08-01")
    stuff(s, action="price_add", name="milk", shop="Aldi", amount=1.29)
    assert stuff(s, action="price_add", name="milk", shop="Tesco", amount=1.55) == "Milk is 1.55 GBP at Tesco."
    shown = stuff(s, action="price_cheapest", name="milk")
    assert str(shown) == "Milk is cheapest at Aldi, 1.29 GBP."
    assert shown.card["rows"][1][:2] == ["Tesco", "1.55 GBP"]
    history = stuff(s, action="price_history", name="milk", shop="tesco")
    assert history.card["chart"]["values"] == [1.45, 1.55] and str(history).startswith("Milk has gone up")
    with pytest.raises(ValueError):
        stuff(s, action="price_cheapest", name="caviar")


def test_diy(s):
    assert stuff(s, action="diy_add", name="Shelves", items=["brackets", "screws"]) == "The Shelves project has 2 materials."
    stuff(s, action="diy_cost", name="shelves", item="brackets", amount=12)
    assert stuff(s, action="diy_cost", name="shelves", item="Oak board", amount=25.5) == \
        "Oak board costs 25.50 GBP. The Shelves project comes to 37.50 GBP."
    assert stuff(s, action="diy_tick", name="shelves", items=["screws"]) == "Got screws. 2 left to get."
    shown = stuff(s, action="diy_show", name="shelves")
    assert shown.card["checks"] and shown.card["items"][1] == \
        {"label": "screws", "done": True, "say": "Tick off screws for the Shelves project."}
    assert stuff(s, action="diy_list").card["rows"] == [["Shelves", "3", "2", "37.50 GBP"]]
    assert "confirm" in stuff(s, action="diy_remove", name="shelves")


def test_energy_meters(s):
    assert meters(s, action="meter_read", meter="electric", amount=1000, date="2026-09-01").endswith("work out your usage.")
    assert meters(s, action="meter_read", meter="electric", amount=1270, date="2026-09-28") == \
        "Saved the electric reading. Since Tuesday 1 September you've used 270 units, 10.0 a day."
    with pytest.raises(ValueError):
        meters(s, action="meter_read", meter="electric", amount=900)
    assert meters(s, action="meter_cost") == "Electric: about 304 units a month (tell me the unit price for a cost)."
    meters(s, action="meter_price", meter="electric", amount=0.25)
    assert meters(s, action="meter_cost", meter="electric") == "Electric: about 304 units, 76.10 GBP a month."
    shown = meters(s, action="meter_usage", meter="electric")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"] == [10.0]
    assert meters(s, action="meter_usage", meter="gas") == "I need at least two gas readings to show usage."


def test_car_log(s):
    assert "first fill-up" in meters(s, action="car_fill", miles=10000, litres=40, amount=60, date="2026-09-01")
    assert meters(s, action="car_fill", miles=10400, litres=40, amount=58) == "Logged it: 45.5 mpg since the last fill-up."
    with pytest.raises(ValueError):
        meters(s, action="car_fill", miles=10300, litres=30, amount=40)
    shown = meters(s, action="car_report")
    assert str(shown) == "The car averages 45.5 mpg, last fill 45.5; 0.145 GBP a mile."
    assert shown.card["chart"]["values"] == [45.5]


def test_parking(s):
    assert meters(s, action="park_where") == "You haven't told me where you parked."
    assert meters(s, action="park_save", note="Level 3, bay 42, Queen Street") == "Got it: Level 3, bay 42, Queen Street."
    CLOCK["now"] = datetime(2026, 9, 28, 12, 45)
    shown = meters(s, action="park_where")
    assert str(shown) == "You parked at Level 3, bay 42, Queen Street, 2 hours ago, at 10:30."
    assert shown.card["kind"] == "text"
    assert meters(s, action="park_clear").card["kind"] == "close"
    assert meters(s, action="park_where").startswith("You've already picked the car up.")


def test_pets(s):
    assert family(s, action="pet_add", name="Biscuit", kind="dog") == "Added Biscuit the dog."
    assert family(s, action="pet_feeds", name="biscuit") == "Biscuit hasn't been fed today."
    assert family(s, action="pet_fed", name="biscuit") == "Biscuit fed. That's 1 meal today."
    assert family(s, action="pet_feeds", name="biscuit") == "Biscuit was fed today at 10:30."
    family(s, action="pet_due", name="biscuit", what="Flea", date="2026-10-05")
    family(s, action="pet_due", name="biscuit", what="vaccination", date="2027-01-10")
    shown = family(s, action="pet_dues")
    assert str(shown) == "Next up: Biscuit's flea, in 7 days." and len(shown.card["rows"]) == 2
    family(s, action="pet_weigh", name="biscuit", amount=12.5, date="2026-06-01")
    assert family(s, action="pet_weigh", name="biscuit", amount=13) == "Biscuit weighs 13 kg."
    shown = family(s, action="pet_weights", name="biscuit")
    assert shown.card["chart"]["values"] == [12.5, 13] and "up 0.5 kg" in shown
    assert "confirm" in family(s, action="pet_remove", name="biscuit")


def test_party_planner(s):
    assert family(s, action="party_create", name="Mia's 7th", date="2026-10-10", amount=150) == \
        "Mia's 7th is on Saturday 10 October, in 12 days."
    assert family(s, action="party_guests", items=["Ava", "Leo", "Zara", "ava"]) == "3 guests on the list for Mia's 7th."
    family(s, action="party_rsvp", person="ava", status="yes")
    assert family(s, action="party_rsvp", person="Leo", status="maybe") == "Leo: maybe. 1 yes, 0 no, 1 maybe, 1 not replied."
    counts = family(s, action="party_counts")
    assert counts.card["chart"]["values"] == [1, 0, 1, 1]
    family(s, action="party_bring", items=["cake", "balloons"], person="Gran")
    assert family(s, action="party_tick", items=["cake"]) == "Sorted: cake. 1 left."
    assert family(s, action="party_spend", amount=40, what="hall") == \
        "Spent 40.00 GBP on Mia's 7th so far, 110.00 GBP of the budget left."
    shown = family(s, action="party_show", name="mia")
    assert shown.card["kind"] == "table" and ["Zara", "not replied"] in shown.card["rows"]
    assert "Still to bring: balloons (Gran)." in shown.card["text"]
    bring = family(s, action="party_bring_list")
    assert bring.card["items"][0]["done"] is True
    assert family(s, action="party_remove", name="mia", confirmed=True) == "Removed the Mia's 7th event."


def test_sitter_sheet(s, tmp_path):
    assert family(s, action="sitter_show").startswith("The sitter sheet is empty")
    assert family(s, action="sitter_set", field="allergies", text="Mia: peanuts") == "Saved the allergies on the sitter sheet."
    family(s, action="sitter_set", field="bedtimes", text="Mia 7:30pm")
    shown = family(s, action="sitter_show")
    assert "peanuts" not in shown and "## Allergies\n\nMia: peanuts" in shown.card["text"]
    assert "## Allergies" in (tmp_path / "household-sitter-sheet.md").read_text()
    assert family(s, action="sitter_clear", field="bedtimes", confirmed=True) == "Cleared the bedtimes part of the sitter sheet."


def test_emergency_contacts_stay_on_screen(s):
    assert family(s, action="contacts_show") == "No emergency contacts saved yet."
    with pytest.raises(ValueError):
        family(s, action="contact_add", name="Gran", number="call her")
    family(s, action="contact_add", name="Gran", number="+44 7700 900123", relation="grandmother")
    shown = family(s, action="contacts_show")
    assert str(shown) == "1 emergency contact on the screen."
    assert "7700" not in shown and shown.card["rows"] == [["Gran", "+44 7700 900123", "grandmother"]]
    assert "confirm" in family(s, action="contact_remove", name="gran")


def test_school_dates(s):
    assert family(s, action="term_list") == "No school or family dates coming up."
    assert family(s, action="term_add", name="Half term", date="2026-10-26", until="2026-10-30") == \
        "Half term is from Monday 26 October to Friday 30 October, in 28 days."
    family(s, action="term_add", name="Inset day", date="2026-09-25")
    family(s, action="term_add", name="Autumn term", date="2026-09-03", until="2026-12-18")
    shown = family(s, action="term_list")
    assert str(shown) == "Next: Autumn term, now, ends in 81 days."
    assert [r[0] for r in shown.card["rows"]] == ["Autumn term", "Half term"]
    assert family(s, action="term_remove", name="inset", confirmed=True) == "Removed the Inset day date."
