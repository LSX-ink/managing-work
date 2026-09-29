import asyncio
from datetime import date, datetime

import httpx
import pytest

import petsgarden_garden as garden
import petsgarden_guide as guide
import petsgarden_pets as pets
import petsgarden_records as records
import screen
import tools
from config import Settings

NOW = datetime(2026, 9, 29, 18, 0)
TODAY = NOW.date()


def pet(s, **args):
    return pets.run_tool("pet_records", args, s, None, now=NOW)


def rec(s, **args):
    return records.run_tool("garden_records", args, s, None, today=TODAY)


def run_async(fn, args, settings, handler=None):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler or (lambda r: httpx.Response(500)))) as http:
            return await fn("x", args, settings, http)

    return asyncio.run(go())


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), city="Leeds")


def test_tools_are_registered():
    for mod in (pets, guide, garden, records):
        assert len(mod.tool_definitions()) == 1 and mod.NAMES
        assert mod in tools.ABILITIES
    assert "petsgarden-bed" in screen.EXTRA_KINDS


def test_profile_show_age_and_remove(s):
    assert pet(s, action="profile", name="Biscuit", species="Dog", breed="labrador", birthday="2022-09-01", weight_kg=28) \
        == "Saved Biscuit, a labrador."
    shown = pet(s, action="show")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "table"
    assert any(r[0] == "Weight" and r[1] == "28 kg" for r in shown.card["rows"])
    assert "4 years" in pet(s, action="age", name="bisc") and "human years" in pet(s, action="age", name="bisc")
    pet(s, action="profile", name="Mog", species="cat")
    assert pet(s, action="show").card["id"] == "petsgarden-pets"
    with pytest.raises(ValueError):
        pet(s, action="age", name="Mog")
    assert "confirm" in pet(s, action="remove", name="Mog")
    assert pet(s, action="remove", name="Mog", confirmed=True) == "Removed Mog."
    with pytest.raises(ValueError):
        pet(s, action="show", name="Mog")
    with pytest.raises(ValueError):
        pet(s, action="profile", name="Rex", birthday="last week")


def test_human_years():
    assert pets.human_years("dog", "labrador", 2, 0) == 24
    assert pets.human_years("dog", "labrador", 5, 0) == 24 + 3 * 6
    assert pets.human_years("cat", "", 6, 0) == 24 + 16
    assert pets.human_years("rabbit", "", 3, 0) is None
    assert pets.human_years("dog", "", 0, 6) == 7.5


def test_feeding_and_did_anyone_feed(s):
    pet(s, action="profile", name="Biscuit", species="dog")
    assert pet(s, action="feeding_schedule", times=["8:00", "17:30"], amount="1 cup") == "Biscuit is fed at 08:00, 17:30."
    with pytest.raises(ValueError):
        pet(s, action="feeding_schedule", times=["teatime"])
    shown = pet(s, action="feed_check")
    assert "Nobody has fed Biscuit" in shown and "2 scheduled meals looks missed" in shown
    assert "Mia fed Biscuit" in pet(s, action="fed", who="Mia")
    shown = pet(s, action="feed_check", name="Biscuit")
    assert "by Mia" in shown and shown.card["items"][0]["done"] and "1 scheduled meal looks missed" in shown


def test_walks_and_weekly_chart(s):
    pet(s, action="profile", name="Biscuit", species="dog")
    assert "That's 45 minutes this week" in pet(s, action="walk", minutes=45, miles=2, day="today")
    pet(s, action="walk", minutes=30, day="2026-09-27")
    shown = pet(s, action="walk_week")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"][-1] == 45
    assert sum(shown.card["chart"]["values"]) == 75 and len(shown.card["chart"]["labels"]) == 7
    with pytest.raises(ValueError):
        pet(s, action="walk", minutes=0)


def test_tricks(s):
    pet(s, action="profile", name="Biscuit", species="dog")
    assert pet(s, action="trick", trick="Sit", level="mastered") == "Biscuit's sit is now mastered."
    pet(s, action="trick", trick="roll over")
    shown = pet(s, action="tricks")
    assert shown.card["kind"] == "list" and "1 of 2" in shown
    assert shown.card["items"][1]["say"] == "Biscuit's trick roll over is now practising."
    with pytest.raises(ValueError):
        pet(s, action="trick", trick="beg", level="expert")


def test_sitter_sheet_written_to_memory(s, tmp_path):
    pet(s, action="profile", name="Biscuit", species="dog", breed="labrador", notes="Scared of fireworks")
    pet(s, action="feeding_schedule", times=["08:00"], amount="1 cup")
    shown = pet(s, action="sitter_sheet", notes="Back on Sunday")
    text = (tmp_path / "petsgarden-sitter-sheet.md").read_text()
    assert shown.card["kind"] == "file" and "## Biscuit" in text and "Scared of fireworks" in text
    assert "Back on Sunday" in text and "- Meals: 08:00, 1 cup" in text


def test_toxic_food_and_first_aid():
    shown = guide.toxic_food("grapes", "dog")
    assert "toxic" in shown and shown.card["kind"] == "table"
    assert "toxic" in guide.toxic_food("lily", "cat") and "safe" in guide.toxic_food("apple", "dog")
    assert "check with your vet" in guide.toxic_food("dragon fruit", "dog")
    assert guide.toxic_food("", "").card["columns"] == ["Food", "Dogs", "Cats"]
    kit = guide.first_aid("")
    assert kit.card["kind"] == "list" and kit.card["checks"]
    assert "cool" in guide.first_aid("heatstroke")
    with pytest.raises(ValueError):
        guide.first_aid("hiccups")


def dog_handler(request):
    assert request.url.host == "dog.ceo"
    if "/breed/labrador/" in request.url.path:
        return httpx.Response(200, json={"message": "https://images.dog.ceo/breeds/labrador/a.jpg", "status": "success"})
    return httpx.Response(404, json={"status": "error"})


def test_breed_facts_with_picture(s):
    shown = run_async(guide.run_tool, {"action": "breed_facts", "breed": "Lab"}, s, dog_handler)
    assert shown.card["kind"] == "reader" and shown.card["image"].startswith("https://images.dog.ceo/")
    assert "large dog" in shown
    # A known breed still gets facts when the picture site can't help.
    shown = run_async(guide.run_tool, {"action": "breed_facts", "breed": "pug"}, s, dog_handler)
    assert "image" not in shown.card and "small dog" in shown
    with pytest.raises(ValueError):
        run_async(guide.run_tool, {"action": "breed_facts", "breed": "unicorn"}, s, dog_handler)


def gardening(s, **args):
    return run_async(lambda n, a, st, h: garden.run_tool(n, a, st, h, today=TODAY), args, s)


def test_sow_calendar_and_jobs(s):
    shown = gardening(s, action="sow_calendar", month="March", kind="veg")
    names = [r[0] for r in shown.card["rows"]]
    assert "Peas" in names and "Basil" not in names and "March" in shown.card["title"]
    assert gardening(s, action="sow_calendar").card["title"] == "What to sow in September"
    crop = gardening(s, action="sow_calendar", plant="tomato")
    assert ["Harvest", "Jul, Aug, Sep, Oct"] in crop.card["rows"]
    with pytest.raises(ValueError):
        gardening(s, action="sow_calendar", plant="dragonfruit")
    with pytest.raises(ValueError):
        gardening(s, action="sow_calendar", month="smarch")
    jobs = gardening(s, action="month_jobs")
    assert jobs.card["kind"] == "list" and "September" in jobs.card["title"]


def test_plant_care_companion_lawn_compost(s):
    care = gardening(s, action="plant_care", plant="Monstera")
    assert care.card["kind"] == "table" and "Water" in care.card["rows"][0]
    assert len(gardening(s, action="plant_care").card["items"]) >= 30
    with pytest.raises(ValueError):
        gardening(s, action="plant_care", plant="triffid")
    assert "basil" in gardening(s, action="companion", plant="tomatoes")
    assert len(gardening(s, action="companion").card["rows"]) >= 15
    lawn = gardening(s, action="lawn")
    assert "overseed" in lawn and len(lawn.card["rows"]) == 12
    assert gardening(s, action="compost").card["kind"] == "list"
    with pytest.raises(ValueError):
        gardening(s, action="mystery")


def test_frost_warning_uses_city_only(s):
    seen = []

    def handler(request):
        seen.append(request.url)
        if request.url.host == "geocoding-api.open-meteo.com":
            assert request.url.params["name"] == "Leeds"
            return httpx.Response(200, json={"results": [{"name": "Leeds", "latitude": 53.8, "longitude": -1.5,
                                                          "country": "United Kingdom"}]})
        assert set(request.url.params) == {"latitude", "longitude", "daily", "timezone", "forecast_days"}
        days = [f"2026-09-{d}" for d in range(29, 31)] + [f"2026-10-0{d}" for d in range(1, 6)]
        return httpx.Response(200, json={"daily": {"time": days, "temperature_2m_min": [6, 3, -1, 2, 8, 9, -3]}})

    shown = run_async(lambda n, a, st, h: garden.run_tool(n, a, st, h, today=TODAY), {"action": "frost_warning"}, s, handler)
    assert "Frost warning for Leeds" in shown and "1 more" in shown
    assert shown.card["rows"][2][2] == "Frost: cover tender plants" and len(shown.card["rows"]) == 7
    assert shown.card["rows"][6][2].startswith("Hard frost") and len(seen) == 2


def test_frost_warning_bad_forecast(s):
    def handler(request):
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(200, json={"results": [{"name": "Leeds", "latitude": 1, "longitude": 1}]})
        return httpx.Response(500)

    with pytest.raises(ValueError):
        run_async(garden.run_tool, {"action": "frost_warning", "city": "Leeds"}, s, handler)


def test_harvest_log_and_totals(s):
    assert rec(s, action="harvest_log", crop="Courgettes", amount=1.5) == "Logged 1.5 kg of courgettes. That's 1.5 kg this year."
    rec(s, action="harvest_log", crop="courgettes", amount=2, day="2026-09-20")
    rec(s, action="harvest_log", crop="tomatoes", amount=0.5)
    rec(s, action="harvest_log", crop="apples", amount=12, unit="each")
    shown = rec(s, action="harvest_totals")
    assert shown.card["chart"]["labels"] == ["Courgettes", "Tomatoes"] and shown.card["chart"]["values"] == [3.5, 0.5]
    assert rec(s, action="harvest_totals", unit="each").card["chart"]["labels"] == ["Apples"]
    with pytest.raises(ValueError):
        rec(s, action="harvest_totals", year=2019)
    with pytest.raises(ValueError):
        rec(s, action="harvest_log", crop="", amount=1)


def test_seed_stock(s):
    assert rec(s, action="seed_add", seed="Sweet peas", packets=2, sow_by="2027-03") == \
        "Noted 2 packets of Sweet peas, sow by 31 Mar 2027."
    rec(s, action="seed_add", seed="Carrots", sow_by="2026-08-31")
    shown = rec(s, action="seed_list")
    assert shown.card["rows"][0][0] == "Carrots" and "(expired)" in shown.card["rows"][0][2] and "1 past" in shown
    with pytest.raises(ValueError):
        rec(s, action="seed_add", seed="Beans", sow_by="soon")
    assert "confirm" in rec(s, action="seed_remove", seed="carrots")
    assert rec(s, action="seed_remove", seed="carrots", confirmed=True) == "Removed Carrots from the seed box."
    assert len(rec(s, action="seed_list").card["rows"]) == 1


def test_raised_bed_planner(s):
    shown = rec(s, action="bed_set", bed="Bed one", rows=2, cols=3)
    assert shown.card["kind"] == "petsgarden-bed" and shown.card["data"]["grid"] == [["", "", ""], ["", "", ""]]
    shown = rec(s, action="bed_set", row=1, col=2, plant="Carrots")
    assert shown.card["data"]["grid"][0][1] == "Carrots" and shown.card["data"]["plants"] == ["carrots"]
    assert rec(s, action="bed_show").card["data"]["grid"][0][1] == "Carrots"
    with pytest.raises(ValueError):
        rec(s, action="bed_set", row=3, col=1, plant="Kale")
    shrunk = rec(s, action="bed_set", rows=1, cols=1)
    assert shrunk.card["data"]["grid"] == [[""]]
    rec(s, action="bed_set", row=1, col=1, plant="Kale")
    assert rec(s, action="bed_set", row=1, col=1).card["data"]["grid"] == [[""]]
    assert "confirm" in rec(s, action="bed_remove")
    assert rec(s, action="bed_remove", confirmed=True) == "Removed the Bed one plan."
    with pytest.raises(ValueError):
        rec(s, action="bed_show")
