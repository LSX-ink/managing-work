import asyncio
import time
from datetime import date, datetime, timedelta

import httpx
import pytest

import agenda
import dates_saved
import growth_goals
import growth_media
import growth_study
import habits
import homehouse
import homekitchen
import homewellbeing
import money
import reminders
import shopping
import showme
import timers
import todo
import tools
from config import Settings

TODAY = date.today()


def run(action, s, http=None, **args):
    return asyncio.run(showme.run_tool("show_my", {"action": action, **args}, s, http))


def sections(shown):
    assert shown.card["kind"] == "showme"
    return shown.card["data"]["sections"]


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path), tasks_file="", currency="GBP", city="London")


def test_tool_is_registered_and_deferred(s):
    defs = {t["name"]: t for t in tools.client_tool_definitions(s)}
    assert defs["show_my"]["defer_loading"] is True
    assert defs["show_my"]["input_schema"]["properties"]["action"]["enum"] == showme.ACTIONS
    assert "showme" in __import__("screen").EXTRA_KINDS


def test_shopping_checklist(s):
    shopping.add(s, ["Milk", "Eggs"])
    shown = run("shopping", s)
    assert shown.card["kind"] == "list" and shown.card["checks"]
    assert shown.card["items"][0] == {"label": "Milk", "done": False, "say": "Tick off Milk from the shopping list."}
    assert [b["label"] for b in shown.card["buttons"]] == ["Add item", "Clear"]


def test_todo_checklist(s):
    todo.add(s, ["Call the bank"])
    shown = run("todo", s)
    assert shown.card["checks"] and shown.card["items"][0]["say"] == "Tick off Call the bank on my to-do list."


def test_reminders_with_cancel(s):
    reminders.add(s, (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 09:00"), "call Mum", "daily")
    item = sections(run("reminders", s))[0]["items"][0]
    assert item["action"] == "Cancel" and item["say"] == "Cancel the reminder about call Mum."
    assert item["note"].startswith("tomorrow at 09:00") and "repeats daily" in item["note"]


def test_timers_live(s, monkeypatch):
    monkeypatch.setattr(timers, "timers", {"pasta": timers.Timer("pasta", time.monotonic() + 300)})
    shown = run("timers", s)
    assert shown.card["kind"] == "timer" and abs(shown.card["ends_at"] - (time.time() + 300) * 1000) < 5000
    assert shown.card["buttons"][0]["say"] == "Cancel the pasta timer."
    timers.timers["tea"] = timers.Timer("tea", time.monotonic() + 60)
    parts = sections(run("timers", s))
    assert [p["label"] for p in parts] == ["tea", "pasta"] and all(p["type"] == "timer" for p in parts)
    timers.timers.clear()
    assert run("timers", s) == "No timers are running."


def test_calendar_table(s):
    agenda._cache.update(url="", at=0.0, cal=None)
    day = TODAY.strftime("%Y%m%d")
    ics = (f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:t\nBEGIN:VEVENT\nUID:1\nDTSTART:{day}T090000\n"
           f"DTEND:{day}T100000\nSUMMARY:Dentist\nLOCATION:High St\nEND:VEVENT\nEND:VCALENDAR\n").encode()

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=ics))) as http:
            return await showme.show_calendar(http, Settings(calendar_url="https://cal.test/showme.ics"))

    shown = asyncio.run(go())
    assert shown.card["kind"] == "table" and shown.card["rows"] == [["Today", "09:00", "Dentist", "High St"]]
    assert "1 today" in shown
    assert run("calendar", s).card["kind"] == "text"  # not connected


def test_weather_chart_and_table(s):
    days = [(TODAY + timedelta(days=i)).isoformat() for i in range(7)]

    def handler(request):
        if "geocoding" in request.url.host:
            assert request.url.params["name"] == "Leeds"
            return httpx.Response(200, json={"results": [{"name": "Leeds", "latitude": 53.8, "longitude": -1.5}]})
        return httpx.Response(200, json={"daily": {
            "time": days, "weather_code": [0, 3, 61, 61, 2, 1, 0], "temperature_2m_max": [15, 16, 14, 13, 17, 18, 19],
            "temperature_2m_min": [8] * 7, "precipitation_probability_max": [0, 10, 80, 70, 20, 5, 0]}})

    async def go(transport):
        async with httpx.AsyncClient(transport=transport) as http:
            return await showme.run_tool("show_my", {"action": "weather", "city": "Leeds"}, s, http)

    shown = asyncio.run(go(httpx.MockTransport(handler)))
    chart, table = sections(shown)
    assert chart["chart"]["values"] == [15, 16, 14, 13, 17, 18, 19] and chart["chart"]["labels"][0] == "Today"
    assert table["rows"][2][1:] == ["light rain", "14°C", "8°C", "80%"]
    with pytest.raises(ValueError):
        asyncio.run(go(httpx.MockTransport(lambda r: httpx.Response(500))))


def test_habits_grid(s):
    habits.mark(s, "Gym", TODAY - timedelta(days=1))
    habits.mark(s, "Gym", TODAY)
    habits.mark(s, "Read", TODAY - timedelta(days=2))
    streaks, grid, left = sections(run("habits", s))
    assert streaks["rows"][0] == ["Gym", "2", "2/7", "✓"]
    assert grid["rows"][0][-2:] == ["✓", "✓"] and len(grid["rows"][0]) == 15
    assert left["items"] == [{"label": "Read", "say": "I did Read today.", "action": "Done"}]


def test_payslips_chart(s):
    money.log_payslip(s, {"month": "2026-07", "employer": "VGC", "net": 2000}, TODAY)
    money.log_payslip(s, {"month": "2026-08", "employer": "VGC", "net": 2200, "gross": 2900}, TODAY)
    shown = run("payslips", s)
    chart, table = sections(shown)
    assert chart["chart"]["type"] == "line" and chart["chart"]["values"] == [2000, 2200]
    assert table["rows"][0] == ["2026-08", "VGC", "2,200.00 GBP", "2,900.00 GBP", ""]
    assert "2,100.00 GBP" in shown


def test_spending_charts(s):
    money.log_spend(s, {"amount": 20, "what": "lunch", "category": "food"}, TODAY)
    money.log_spend(s, {"amount": 5, "what": "bus", "category": "transport"}, TODAY)
    cats, months = sections(run("spending", s))
    assert cats["chart"]["labels"] == ["food", "transport"] and cats["chart"]["values"] == [20, 5]
    assert len(months["chart"]["values"]) == 6 and months["chart"]["values"][-1] == 25


def test_wellbeing_charts(s):
    homewellbeing.sleep_log(s, 7.5)
    homewellbeing.water_add(s, 3)
    homewellbeing.mood_log(s, 4)
    sleep, water, mood = sections(run("wellbeing", s))
    assert sleep["chart"]["values"] == [7.5] and water["chart"]["values"][-1] == 3 and len(water["chart"]["values"]) == 14
    assert mood["chart"]["values"] == [4]


def test_fitness_charts(s):
    growth_goals.log_steps(s, 8000, None, TODAY)
    growth_goals.log_workout(s, {"exercise": "run", "minutes": 30}, TODAY)
    steps, minutes, table = sections(run("fitness", s))
    assert steps["chart"]["values"][-1] == 8000 and minutes["chart"]["values"][-1] == 30
    assert table["rows"][0][1:] == ["run", "30 minutes"]


def test_goals_bars(s):
    growth_goals.set_goal(s, {"name": "Read books", "target": 12, "unit": "books"}, TODAY)
    growth_goals.log_goal(s, "read", 3, TODAY)
    bars, log = sections(run("goals", s))
    assert bars["items"][0]["pct"] == 25 and bars["items"][0]["note"].startswith("3 of 12 books")
    assert log["items"][0]["say"] == "Add progress to my goal Read books."


def test_bills_table(s):
    homehouse.bill_add(s, "Rent", 900, 1)
    homehouse.sub_add(s, "Netflix", 12, "yearly")
    shown = run("bills", s)
    assert shown.card["kind"] == "table" and shown.card["text"] == "Monthly total: 901.00 GBP"
    assert shown.card["rows"][0][:3] == ["Rent", "bill", "900.00 GBP"]
    assert shown.card["rows"][1][:3] == ["Netflix", "subscription", "12.00 GBP a year"]


def test_meals_and_recipe(s):
    homekitchen.meal_set(s, TODAY.isoformat(), "Lasagne")
    shown = run("meals", s)
    assert shown.card["kind"] == "table" and ["Today", "", "", "Lasagne"] in shown.card["rows"]
    homekitchen.recipe_save(s, "Pancakes", ["flour", "eggs"], ["Whisk", "Fry"], False)
    shown = run("recipe", s, name="pancake")
    ingredients, method = sections(shown)
    assert [i["label"] for i in ingredients["items"]] == ["flour", "eggs"]
    assert [i["label"] for i in method["items"]] == ["1. Whisk", "2. Fry"]
    assert shown.card["buttons"][0] == {"label": "Add ingredients to shopping list",
                                        "say": "Add the Pancakes ingredients to my shopping list."}
    with pytest.raises(ValueError):
        run("recipe", s, name="soup")


def test_birthdays_and_countdowns(s):
    soon = TODAY + timedelta(days=5)
    dates_saved.add(s, "birthday", "Mum", f"1966-{soon:%m-%d}")
    dates_saved.add(s, "countdown", "Spain", (TODAY + timedelta(days=30)).isoformat())
    shown = run("dates", s)
    births, counts = sections(shown)
    assert births["items"][0]["label"] == f"Mum, turning {soon.year - 1966}" and births["items"][0]["note"].endswith("in 5 days")
    assert counts["items"][0]["note"].endswith("in 30 days")
    assert shown.startswith("Next up: Mum")


def test_reading_and_watch_lists(s):
    growth_media.book_add(s, "Dune", "Frank Herbert")
    growth_media.book_reading(s, "Emma", "")
    now, waiting = sections(run("reading", s))
    assert now["items"][0] == {"label": "Emma", "say": "I finished reading Emma.", "action": "Finished"}
    assert waiting["items"][0]["label"] == "Dune by Frank Herbert"
    growth_media.watch_add(s, "Heat", "film")
    growth_media.watch_add(s, "Slow Horses", "series")
    films, series = sections(run("watching", s))
    assert films["items"][0]["say"] == "Mark Heat as watched." and series["items"][0]["action"] == "Watched"


def test_flashcards(s):
    growth_study.new_deck(s, "Spanish")
    growth_study.add_card(s, "Spanish", "Hola", "Hello", TODAY)
    shown = run("flashcards", s)
    assert sections(shown) == [{"type": "flashcard", "front": "Hola", "back": "Hello"}]
    assert [b["label"] for b in shown.card["buttons"]] == ["I got it right", "I got it wrong", "Next card"]
    assert growth_study.answer(s, True, TODAY).startswith("Right.")  # the pop-up set it up for answering
    assert run("flashcards", s).startswith("Nothing due in Spanish")


def test_shown_via_tools_pops_up(s):
    sent = []

    async def page(msg):
        sent.append(msg)

    out = asyncio.run(tools.run_tool("show_my", {"action": "shopping"}, s, None, page))
    assert type(out) is str and sent[0]["card"]["id"] == "showme-shopping"
