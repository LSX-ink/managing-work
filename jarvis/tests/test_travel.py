import asyncio
from datetime import datetime

import httpx
import pytest

import homestore
import screen
import tools
import travel_guide
import travel_papers
import travel_trips
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 28, 10, 30))  # a Monday
    return Settings(memory_dir=str(tmp_path), city="London", currency="GBP")


def weather_handler(request):
    if "geocoding" in request.url.host:
        assert request.url.params["name"] == "Barcelona"
        return httpx.Response(200, json={"results": [{"name": "Barcelona", "latitude": 41.39, "longitude": 2.17}]})
    assert request.url.params["start_date"] == "2026-10-05" and request.url.params["end_date"] == "2026-10-07"
    return httpx.Response(200, json={"daily": {
        "time": ["2026-10-05", "2026-10-06", "2026-10-07"], "weather_code": [0, 0, 61],
        "temperature_2m_max": [24.5, 23.0, 20.0], "temperature_2m_min": [16.0, 15.5, 14.0],
        "precipitation_probability_max": [0, 5, 70]}})


def trips(s, handler=weather_handler, **args):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await travel_trips.run_tool("travel_trips", args, s, http)
    return asyncio.run(go())


def papers(s, **args):
    return travel_papers.run_tool("travel_papers", args, s)


def guide(s, **args):
    def offline(request):
        raise AssertionError(f"unexpected request to {request.url}")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(offline)) as http:
            return await travel_guide.run_tool("travel_guide", args, s, http)
    return asyncio.run(go())


def test_registered_with_few_tools():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"travel_trips", "travel_papers", "travel_guide"} <= names
    for module in (travel_trips, travel_papers, travel_guide):
        assert module in tools.ABILITIES
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert "travel-phrases" in screen.EXTRA_KINDS


def test_trips_and_countdown(s):
    with pytest.raises(ValueError):
        trips(s, action="plan_show")
    assert trips(s, action="trip_add", destination="Barcelona", country="Spain", start="2026-10-05",
                 end="2026-10-07") == "Saved Barcelona 2026: Barcelona, Monday 5 October to Wednesday 7 October. " \
                                      "It starts in 7 days."
    trips(s, action="trip_add", name="Tokyo", destination="Tokyo", start="2027-04-01", end="2027-04-10")
    with pytest.raises(ValueError):
        trips(s, action="trip_add", destination="Rome", start="2026-10-05", end="2026-10-01")
    shown = trips(s, action="trip_list")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "table"
    assert shown.card["rows"][0][3] == "starts in 7 days"
    assert str(shown) == "2 trips. Barcelona 2026 starts in 7 days."
    assert "confirm" in trips(s, action="trip_remove", trip="tokyo")
    assert trips(s, action="trip_remove", trip="tokyo", confirmed=True) == "Deleted the Tokyo trip."


def test_itinerary(s):
    trips(s, action="trip_add", destination="Barcelona", start="2026-10-05", end="2026-10-07")
    assert trips(s, action="plan_add", day="2026-10-05", time="15:00", what="Sagrada Familia",
                 where="Carrer de Mallorca") == \
        "Added Sagrada Familia on Monday 5 October at 15:00 to the Barcelona 2026 plan (number 1)."
    trips(s, action="plan_add", day="2026-10-05", time="9", what="Breakfast")
    trips(s, action="plan_add", day="2026-10-06", what="Beach")
    with pytest.raises(ValueError):
        trips(s, action="plan_add", day="2026-12-01", what="Too late")
    day = trips(s, action="plan_show", day="2026-10-05")
    assert day.card["kind"] == "table" and [r[2] for r in day.card["rows"]] == ["Breakfast", "Sagrada Familia"]
    assert day.card["rows"][0][1] == "09:00"
    assert len(trips(s, action="plan_show").card["rows"]) == 3
    assert trips(s, action="plan_move", number=3, day="2026-10-07", time="11:00") == \
        "Moved Beach to Wednesday 7 October at 11:00."
    assert "confirm" in trips(s, action="plan_remove", number=2)
    assert trips(s, action="plan_remove", number=2, confirmed=True) == "Removed Breakfast from the Barcelona 2026 plan."


def test_bookings(s):
    trips(s, action="trip_add", destination="Barcelona", start="2026-10-05", end="2026-10-07")
    trips(s, action="booking_add", kind="flight", ref="BA478", what="London Heathrow to Barcelona",
          day="2026-10-05", time="07:15")
    trips(s, action="booking_add", kind="hotel", ref="HX99", what="Hotel Arts", day="2026-10-05",
          address="Carrer de la Marina 19")
    assert trips(s, action="booking_find", kind="flight") == \
        "Flight: London Heathrow to Barcelona, reference BA478, on Monday 5 October, at 07:15."
    assert "Carrer de la Marina 19" in trips(s, action="booking_find", query="arts")
    table = trips(s, action="booking_list")
    assert table.card["kind"] == "table" and len(table.card["rows"]) == 2
    assert "confirm" in trips(s, action="booking_remove", number=2)
    assert trips(s, action="booking_remove", number=2, confirmed=True) == "Removed the hotel booking HX99."


def test_gifts_and_journal(s):
    trips(s, action="trip_add", destination="Barcelona", start="2026-10-05", end="2026-10-07")
    assert trips(s, action="gift_add", items=["Turron", "Fridge magnet"], who="Mum") == \
        "Added Turron, Fridge magnet for Mum to the Barcelona 2026 gift list."
    assert trips(s, action="gift_tick", item="magnet") == "Got Fridge magnet. 1 left to buy."
    shown = trips(s, action="gift_list")
    assert shown.card["checks"] and shown.card["items"][1]["done"]
    assert trips(s, action="journal_write", text="Tapas by the sea.", day="2026-10-05") == \
        "Saved to your Barcelona 2026 journal in the Travel folder."
    trips(s, action="journal_write", text="Rain, so the Picasso museum.", day="2026-10-06")
    shown = trips(s, action="journal_read")
    assert shown.card["kind"] == "file" and "Tapas by the sea." in shown and "Picasso" in shown
    path = s.memory_dir + "/Travel/Barcelona 2026 journal.md"
    assert open(path, encoding="utf-8").read().startswith("# Barcelona 2026 journal")


def test_weather_and_summary(s):
    trips(s, action="trip_add", destination="Barcelona", start="2026-10-05", end="2026-10-07")
    trips(s, action="trip_add", name="Tokyo", destination="Tokyo", start="2027-04-01", end="2027-04-10")
    assert "only reaches 16 days" in trips(s, action="weather", trip="Tokyo")
    shown = trips(s, action="weather")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"] == [24.5, 23.0, 20.0]
    assert "highs from 20 to 24.5°C, mostly clear sky" in shown
    papers(s, action="doc_set", name="My passport", kind="passport", expiry="2027-01-10")
    trips(s, action="plan_add", what="Sagrada Familia", day="2026-10-05")
    summary = trips(s, action="summary")
    assert summary.card["kind"] == "text" and "Sagrada Familia" in summary.card["text"]
    assert "My passport has under 6 months left" in summary.card["text"]
    assert "light rain" in summary.card["text"]

    def broken(request):
        return httpx.Response(500)
    assert "isn't available" in trips(s, broken, action="summary").card["text"]


def test_documents(s):
    assert papers(s, action="doc_set", name="My passport", kind="passport", expiry="2031-05-01") == \
        "Saved My passport, expiring Thursday 1 May 2031."
    assert "renew soon" in papers(s, action="doc_set", kind="ghic", expiry="2027-01-31")
    papers(s, action="doc_set", name="Travel insurance", kind="insurance", expiry="2026-09-01")
    shown = papers(s, action="doc_list")
    assert shown.card["kind"] == "table"
    statuses = {r[0]: r[3] for r in shown.card["rows"]}
    assert statuses == {"Travel insurance": "expired", "GHIC": "renew soon: 125 days left", "My passport": "fine"}
    assert str(shown) == "2 need attention: Travel insurance (expired), GHIC (renew soon)."
    assert "confirm" in papers(s, action="doc_remove", name="insurance")
    assert papers(s, action="doc_remove", name="insurance", confirmed=True) == "Removed the Travel insurance document."


def test_leave(s):
    assert papers(s, action="leave_set", total=25) == "Your 2026 leave allowance is 25 days. 25 left to book."
    assert papers(s, action="leave_book", start="2026-10-05", end="2026-10-11", note="Barcelona") == \
        "Booked 5 days off from Monday 5 October. 20 of 25 days left for 2026."
    papers(s, action="leave_book", start="2026-08-03", days=2)
    shown = papers(s, action="leave_show")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["values"] == [25, 2, 5, 18]
    assert "confirm" in papers(s, action="leave_cancel", number=2)
    assert papers(s, action="leave_cancel", number=2, confirmed=True) == "Cancelled that leave. 20 days left for 2026."


def test_places(s):
    assert papers(s, action="place_add", place="Kyoto", country="japan", note="cherry blossom") == \
        "Added Kyoto to the places you want to visit. 1 to go."
    papers(s, action="place_add", place="Lisbon", country="Portugal")
    papers(s, action="place_add", place="Porto", country="Portugal")
    assert papers(s, action="place_visited", place="lisbon") == "Ticked off Lisbon. You've been to 1 places on the list."
    papers(s, action="place_visited", place="Porto", day="2025-06-01")
    papers(s, action="place_visited", place="Cape Town", country="SA")
    shown = papers(s, action="place_list")
    assert shown.card["kind"] == "list" and shown.card["items"][0]["say"] == "I've visited Kyoto."
    count = papers(s, action="place_count")
    assert count.card["rows"][0][:2] == ["Portugal", "2"]
    assert str(count) == "You've ticked off 3 places in 2 countries."
    assert "confirm" in papers(s, action="place_remove", place="kyoto")
    assert papers(s, action="place_remove", place="kyoto", confirmed=True) == "Removed Kyoto from your places list."


def test_checklists(s):
    shown = papers(s, action="checklist_show", list="before you go")
    assert shown.card["kind"] == "list" and shown.card["checks"]
    assert shown.card["items"][0]["say"] == "Tick 'Lock all windows and doors' on my before you go travel checklist."
    assert papers(s, action="checklist_tick", list="before you go", item="cancel the milk").startswith(
        "Ticked Cancel the milk and papers.")
    again = papers(s, action="checklist_show", list="before you go")
    assert [i["label"] for i in again.card["items"] if i["done"]] == ["Cancel the milk and papers"]
    papers(s, action="checklist_tick", list="before you go", item="cancel the milk", done=False)
    assert not any(i["done"] for i in papers(s, action="checklist_show").card["items"])
    papers(s, action="checklist_tick", list="airport day", item="passport")
    assert papers(s, action="checklist_reset", list="airport day") == "The airport day checklist is clear again."


def test_phrasebook(s):
    shown = guide(s, action="phrases", language="japan")
    assert shown.card["kind"] == "travel-phrases" and shown.card["data"]["lang"] == "ja-JP"
    rows = shown.card["data"]["rows"]
    assert len(rows) == 20 and rows[3]["phrase"] == "ありがとうございます" and rows[3]["sound"] == "Arigatō gozaimasu"
    assert guide(s, action="phrases", language="French", phrase="the bill") == \
        "In French, 'The bill, please' is L'addition, s'il vous plaît."
    with pytest.raises(ValueError):
        guide(s, action="phrases", language="Klingon")


def test_country_facts(s):
    shown = guide(s, action="plugs", country="USA")
    assert shown.card["kind"] == "table" and "type A or B plugs at 120 volts" in shown and "hair dryers" in shown
    assert "no adapter needed" in guide(s, action="plugs", country="Malta")
    assert len(guide(s, action="plugs", country="all").card["rows"]) >= 60
    customs = guide(s, action="customs", country="japan")
    assert str(customs).startswith("In Japan they drive on the left. Emergency number: 110 police, 119 ambulance.")
    assert len(guide(s, action="customs").card["rows"]) >= 60
    with pytest.raises(ValueError):
        guide(s, action="customs", country="Atlantis")


def test_jetlag_and_call_times(s):
    shown = guide(s, action="jetlag", destination="Tokyo", day="2026-11-10", days=3)
    assert shown.card["kind"] == "table"
    assert [r[1] for r in shown.card["rows"][:3]] == ["22:00", "21:00", "20:00"]
    assert str(shown).startswith("Tokyo is 9 hours ahead of home.")
    west = guide(s, action="jetlag", destination="New York", day="2026-11-10", days=2)
    assert [r[1] for r in west.card["rows"][:2]] == ["00:00", "01:00"]
    assert "no need" in guide(s, action="jetlag", destination="Paris", day="2026-11-10")
    calls = guide(s, action="call_times", destination="New York")
    assert calls.card["kind"] == "table"
    assert str(calls) == "New York is 5 hours behind home. Good times to call: 08:00 to 16:59 New York time."
    travel_trips.trip_add(s, {"destination": "Sydney", "start": "2026-12-01", "end": "2026-12-20"})
    assert "ahead of home" in guide(s, action="call_times")
