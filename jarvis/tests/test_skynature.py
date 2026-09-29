import asyncio
from datetime import date, datetime, timezone

import httpx
import pytest

import screen
import skynature_astro as astro
import skynature_guide as guide
import skynature_journal as journal
import skynature_sky as sky
import tools
from config import Settings

NOW = datetime(2026, 9, 29, 19, 30, tzinfo=timezone.utc)
TODAY = date(2026, 9, 29)
ISS = {"iss_position": {"latitude": "53.8", "longitude": "-1.5"}, "message": "success"}


def sky_run(args, settings=None, handler=None):
    async def go():
        transport = httpx.MockTransport(handler or (lambda r: httpx.Response(500)))
        async with httpx.AsyncClient(transport=transport) as http:
            return await sky.run_tool("sky_watch", args, settings or Settings(city="Leeds"), http, now=NOW)

    return asyncio.run(go())


def journal_run(s, **args):
    return journal.run_tool("nature_journal", args, s, None, today=TODAY)


def guide_run(**args):
    return guide.run_tool("nature_guide", args, Settings(), None, today=TODAY)


def test_registered_with_three_tools_and_kinds():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"sky_watch", "nature_journal", "nature_guide"} <= names
    for module in (sky, journal, guide):
        assert module in tools.ABILITIES
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert {"skynature-moon", "skynature-moon-cal", "skynature-starmap", "skynature-daylight"} <= screen.EXTRA_KINDS


def test_ephemeris_matches_known_moon_and_sun_times():
    fulls = [w for w, n in astro.phases_after(datetime(2026, 9, 1, tzinfo=timezone.utc), 8) if n == "Full moon"]
    assert fulls[0].date() == date(2026, 9, 26) and abs(fulls[0].hour - 16) <= 1
    news = [w for w, n in astro.phases_after(datetime(2026, 9, 1, tzinfo=timezone.utc), 8) if n == "New moon"]
    assert news[0].date() == date(2026, 9, 11)
    events = astro.sun_events(date(2026, 6, 21), 51.507, -0.128, astro.SUN_RISE)
    assert astro.to_local(events["rise"]).hour == 4 and astro.to_local(events["set"]).hour == 21
    solstice = dict(astro.season_starts(2026))["June solstice"]
    assert solstice.date() == date(2026, 6, 21)
    assert astro.uk_offset(datetime(2026, 7, 1, tzinfo=timezone.utc)).total_seconds() == 3600
    assert astro.uk_offset(datetime(2026, 12, 1, tzinfo=timezone.utc)).total_seconds() == 0


def test_moon_shows_drawn_phase_and_dates():
    out = sky_run({"action": "moon"})
    assert out.card["kind"] == "skynature-moon"
    assert "waning gibbous" in out and "26 October" in out and "10 October" in out
    assert out.card["data"]["waxing"] is False and 0.8 < out.card["data"]["illum"] < 0.95
    assert ["Moonrise"] == [r[0] for r in out.card["data"]["rows"] if r[0] == "Moonrise"]
    full = sky_run({"action": "moon", "date": "2026-09-26"})
    assert "full moon" in full and full.card["data"]["illum"] > 0.98


def test_moon_dates_and_calendar():
    out = sky_run({"action": "moon_dates"})
    assert out.card["kind"] == "table" and len(out.card["rows"]) == 8
    assert "Monday 26 October" in out
    cal = sky_run({"action": "moon_calendar", "month": 10, "year": 2026})
    assert cal.card["kind"] == "skynature-moon-cal" and len(cal.card["data"]["days"]) == 31
    assert cal.card["data"]["offset"] == 3  # 1 October 2026 is a Thursday
    tags = {d["d"]: d["tag"] for d in cal.card["data"]["days"] if d["tag"]}
    assert tags[26] == "Full" and tags[10] == "New"
    assert [b["label"] for b in cal.card["buttons"]] == ["< September", "November >"]
    with pytest.raises(ValueError):
        sky_run({"action": "moon_calendar", "month": 13})


def test_planets_tonight_with_where():
    out = sky_run({"action": "planets"})
    assert out.card["kind"] == "table" and out.card["columns"][:2] == ["Planet", "Visible"]
    names = [r[0] for r in out.card["rows"]]
    assert "Saturn" in names and "Venus" not in names
    assert "south" in out and "Leeds" in out


def test_star_map_card_has_stars_lines_and_labels():
    out = sky_run({"action": "star_map"})
    data = out.card["data"]
    assert out.card["kind"] == "skynature-starmap"
    assert len(data["stars"]) > 15 and data["lines"] and data["labels"]
    assert all(x * x + y * y <= 1.0001 for x, y, *_ in data["stars"])
    assert any(n == "Vega" for *_, n in data["stars"])
    with pytest.raises(ValueError):
        sky_run({"action": "star_map", "hour": 30})


def test_star_facts():
    listed = sky_run({"action": "star_facts"})
    assert listed.card["kind"] == "list" and listed.card["items"][0]["say"]
    one = sky_run({"action": "star_facts", "name": "polaris"})
    assert "North Star" in one and one.card["kind"] == "text"
    with pytest.raises(ValueError):
        sky_run({"action": "star_facts", "name": "nonesuch"})


def test_meteor_showers_next_and_named():
    out = sky_run({"action": "meteor_showers"})
    assert out.card["rows"][0][0] == "Draconids" and out.card["rows"][0][1] == "8 Oct"
    assert len(out.card["rows"]) == 11
    perseids = sky_run({"action": "meteor_showers", "name": "perseid"})
    assert len(perseids.card["rows"]) == 1 and "12 August" in perseids
    with pytest.raises(ValueError):
        sky_run({"action": "meteor_showers", "name": "zzz"})


def test_eclipses_list_and_visible_only():
    out = sky_run({"action": "eclipses"})
    assert out.card["rows"][0][0].endswith("2027") and "2 August 2027" in out
    only = sky_run({"action": "eclipses", "visible_only": True})
    assert all(not r[3].startswith("Not") for r in only.card["rows"])
    year = sky_run({"action": "eclipses", "year": 2026})
    assert len(year.card["rows"]) == 4
    with pytest.raises(ValueError):
        sky_run({"action": "eclipses", "year": 2040})


def test_golden_hour_and_sun_times_use_local_maths():
    gold = sky_run({"action": "golden_hour", "city": "London", "date": "2026-06-21"})
    assert gold.card["kind"] == "skynature-daylight"
    assert "golden hour is" in gold and "Blue hour" in gold
    bands = gold.card["data"]["bands"]
    assert bands[0][0] == 0 and bands[-1][1] == 1440 and {b[2] for b in bands} >= {"day", "golden"}
    times = sky_run({"action": "sun_times", "city": "London", "date": "2026-06-21"})
    assert "sunrise 04:4" in times and "sunset 21:2" in times and "16 hours" in times
    rows = dict(times.card["data"]["rows"])
    assert rows["Fully dark"] == "not dark this time of year"
    autumn = sky_run({"action": "sun_times"})
    assert "shorter tomorrow" in autumn and "Leeds" in autumn


def test_day_length_chart_and_seasons():
    chart = sky_run({"action": "day_length"})
    assert chart.card["kind"] == "chart" and chart.card["chart"]["type"] == "line"
    assert "21 Jun" in chart and "21 Dec" in chart
    assert max(chart.card["chart"]["values"]) > 16 and min(chart.card["chart"]["values"]) < 8
    seasons = sky_run({"action": "seasons"})
    assert len(seasons.card["rows"]) == 4 and "December solstice" in seasons


def test_iss_overhead_checks_but_sends_nothing():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=ISS)

    out = sky_run({"action": "iss_overhead"}, handler=handler)
    assert "almost overhead" in out and out.card["kind"] == "table"
    assert not seen[0].url.query and seen[0].url.host == "api.open-notify.org"
    far = sky_run({"action": "iss_overhead"}, handler=lambda r: httpx.Response(
        200, json={"iss_position": {"latitude": "-30", "longitude": "150"}}))
    assert "below the horizon" in far
    with pytest.raises(ValueError):
        sky_run({"action": "iss_overhead"}, handler=lambda r: httpx.Response(503))


def test_place_lookup():
    s = Settings(city="Leeds, UK")
    assert sky.where(s, {})[0] == "Leeds"
    assert sky.where(Settings(), {})[0] == "London"
    assert sky.where(s, {"latitude": 60, "longitude": -1})[1:] == (60.0, -1.0)
    with pytest.raises(ValueError):
        sky.where(Settings(city="Atlantis"), {})
    with pytest.raises(ValueError):
        sky_run({"action": "sun_times", "date": "tomorrow"})
    with pytest.raises(ValueError):
        sky_run({"action": "nope"})


def test_journal_add_list_counts(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    first = journal_run(s, action="add", species="robin", date="2026-01-03", place="Roundhay Park")
    assert "new one for your bird life list" in first and "first robin of 2026" in first
    assert first.card["kind"] == "text"
    again = journal_run(s, action="add", species="Robin", date="2026-05-02", count=2)
    assert "life list" not in again and "first robin" not in again
    journal_run(s, action="add", species="Bluebell", kind="plant", date="2026-04-20", place="Kew")
    journal_run(s, action="add", species="Blue tit", date="2026-02-11", place="Roundhay Park")
    listed = journal_run(s, action="list")
    assert listed.card["kind"] == "list" and listed.card["items"][0]["label"].startswith("#2 2 May 2026: Robin x2")
    assert len(journal_run(s, action="list", kind="plant").card["items"]) == 1
    counts = journal_run(s, action="species_counts")
    assert counts.card["rows"][0][:4] == ["Robin", "bird", "2", "3"]
    assert "4 species" not in counts and "3 species logged" in counts
    with pytest.raises(ValueError):
        journal_run(s, action="add", species="", date="2026-01-01")
    with pytest.raises(ValueError):
        journal_run(s, action="add", species="Fox", kind="dragon")
    with pytest.raises(ValueError):
        journal_run(s, action="add", species="Fox", date="yesterday")


def test_journal_firsts_life_list_monthly_places(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    journal_run(s, action="add", species="Robin", date="2025-12-20", place="Home")
    journal_run(s, action="add", species="Robin", date="2026-01-03", place="Home")
    journal_run(s, action="add", species="Wren", date="2026-01-09", place="Home")
    journal_run(s, action="add", species="Fox", kind="animal", date="2026-03-02", place="Park")
    firsts = journal_run(s, action="first_of_year")
    assert [r[0] for r in firsts.card["rows"]] == ["Robin", "Wren", "Fox"]
    assert [r[3] for r in firsts.card["rows"]] == ["", "new", "new"]
    life = journal_run(s, action="life_list")
    assert [r[0] for r in life.card["rows"]] == ["Robin", "Wren"]
    assert "2 species" in life and "2025: 1" in life and "2026: 1" in life and "2 so far in 2026" in life
    assert journal_run(s, action="life_list", kind="plant").card["kind"] == "text"
    month = journal_run(s, action="monthly")
    assert month.card["chart"]["values"][0] == 2 and month.card["chart"]["values"][2] == 1 and "January" in month
    where = journal_run(s, action="places")
    assert where.card["rows"][0][0] == "Home" and where.card["rows"][0][2] == "2"
    assert journal_run(Settings(memory_dir=str(tmp_path / "empty")), action="places").card["kind"] == "text"


def test_journal_delete_needs_confirmation(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    journal_run(s, action="add", species="Wren", date="2026-01-09")
    ask = journal_run(s, action="delete", id=1)
    assert "Delete #1" in ask and len(journal.load(s)["sightings"]) == 1
    assert "Removed" in journal_run(s, action="delete", id=1, confirmed=True)
    assert journal.load(s)["sightings"] == []
    with pytest.raises(ValueError):
        journal_run(s, action="delete", id=9)
    assert journal_run(s, action="list").card["kind"] == "text"
    assert journal_run(s, action="species_counts").card["kind"] == "text"
    assert journal_run(s, action="first_of_year").card["kind"] == "text"
    assert journal_run(s, action="monthly").card["kind"] == "text"
    with pytest.raises(ValueError):
        journal_run(s, action="nope")


def test_bird_and_tree_id_hints():
    robin = guide_run(action="bird_id", description="a small round brown bird with an orange red breast in the garden")
    assert robin.startswith("Best guess: Robin") and robin.card["kind"] == "list"
    assert robin.card["items"][0]["say"].startswith("Tell me about the Robin")
    tit = guide_run(action="bird_id", description="tiny with a blue cap and yellow belly, hangs upside down on the feeder")
    assert "Blue tit" in tit
    assert "can't match" in guide_run(action="bird_id", description="zzz qqq")
    oak = guide_run(action="tree_id", description="lobed leaves with wavy edges and acorns")
    assert oak.startswith("Best guess: Oak")
    holly = guide_run(action="tree_id", description="spiny glossy evergreen leaves with red berries")
    assert holly.startswith("Best guess: Holly")
    with pytest.raises(ValueError):
        guide_run(action="bird_id", description="the")


def test_bird_and_tree_facts_and_lists():
    assert "mealworms" in guide_run(action="bird_facts", name="robin")
    assert guide_run(action="bird_facts", name="goldfinch").card["buttons"][0]["say"].startswith("Log a Goldfinch")
    assert "poisonous" in guide_run(action="tree_facts", name="yew")
    with pytest.raises(ValueError):
        guide_run(action="bird_facts", name="dodo")
    with pytest.raises(ValueError):
        guide_run(action="tree_facts", name="")
    assert len(guide.BIRDS) >= 30 and len(guide.TREES) >= 20
    assert len(guide_run(action="species_list").card["items"]) == len(guide.BIRDS)
    assert len(guide_run(action="species_list", kind="tree").card["items"]) == len(guide.TREES)
    today = guide_run(action="bird_of_the_day")
    assert today.card["kind"] == "text" and today.card["id"] == "skynature-bird"


def test_in_season_spot_and_forage_with_safety():
    spot = guide_run(action="in_season")
    assert "September" in spot and spot.card["kind"] == "list" and len(spot.card["items"]) >= 5
    forage = guide_run(action="in_season", focus="forage", month="September")
    names = [r[0] for r in forage.card["rows"]]
    assert "Blackberries" in names and "Sloes" in names and names[-1] == "Safety"
    assert "wild mushrooms" in forage
    spring = guide_run(action="in_season", focus="forage", month="3")
    assert "Wild garlic (ramsons)" in [r[0] for r in spring.card["rows"]]
    assert "Bluebells" in guide_run(action="in_season", month="may")
    rules = guide_run(action="forage_safety")
    assert "100 percent" in rules and len(rules.card["items"]) >= 6
    with pytest.raises(ValueError):
        guide_run(action="in_season", month="smarch")
    with pytest.raises(ValueError):
        guide_run(action="nope")


def test_tools_run_tool_dispatches_and_popup_is_sent(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            return await tools.run_tool("nature_guide", {"action": "forage_safety"}, s, http, page)

    out = asyncio.run(go())
    assert out.startswith("It's on the screen") or "100 percent" in out
    assert sent and sent[0]["type"] == "popup" and sent[0]["card"]["id"] == "skynature-safety"
