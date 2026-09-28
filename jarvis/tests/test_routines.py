import asyncio
from dataclasses import replace
from datetime import date, datetime

import httpx
import pytest

import agenda
import habits
import homestore
import money
import reminders
import routines
import routines_brief
import routines_life
import screen
import todo
import tools
from config import Settings

NOW = datetime(2026, 9, 28, 10, 30)  # a Monday

ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:test
BEGIN:VEVENT
UID:1
DTSTART:20260928T150000
DTEND:20260928T160000
SUMMARY:Dentist
LOCATION:High Street
END:VEVENT
BEGIN:VEVENT
UID:2
DTSTART:20260929T090000
DTEND:20260929T100000
SUMMARY:Site visit
END:VEVENT
END:VCALENDAR
"""


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: NOW)
    return Settings(memory_dir=str(tmp_path), currency="GBP", tasks_file="", city="", calendar_url="")


def handler(request):
    if request.url.host == "cal.test":
        return httpx.Response(200, content=ICS)
    if "geocoding" in request.url.host:
        return httpx.Response(200, json={"results": [{"name": "Leeds", "country": "UK", "latitude": 53.8, "longitude": -1.5}]})
    return httpx.Response(200, json={
        "current": {"temperature_2m": 14, "apparent_temperature": 12, "weather_code": 3, "wind_speed_10m": 10,
                    "precipitation": 0},
        "daily": {"time": ["2026-09-28"], "weather_code": [3], "temperature_2m_max": [16], "temperature_2m_min": [9],
                  "precipitation_probability_max": [20]}})


def brief(settings, **args):
    agenda._cache.update(url="", at=0.0, cal=None)

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await routines_brief.run_tool("daily_briefing", args, settings, http)

    return asyncio.run(go())


def rt(s, **args):
    return routines.run_tool("routines", args, s)


def cap(s, **args):
    return routines_life.run_tool("capture_and_remember", args, s)


def lists(s, **args):
    return routines_life.run_tool("decisions_checklists_loans", args, s)


def test_routines_save_run_list_edit_delete(s):
    out = rt(s, action="save", name="Movie night", steps=["turn on dark mode", "close all windows", "set volume to 30"])
    assert out.startswith("Saved the Movie night routine with 3 steps")
    shown = rt(s, action="run", name="run my movie night routine")
    assert "user's own saved requests" in shown and "1. turn on dark mode\n2. close all windows" in shown
    assert shown.card["kind"] == "list" and shown.card["checks"] and len(shown.card["items"]) == 3
    listed = rt(s, action="list")
    assert listed.card["items"][0]["say"] == "Run my Movie night routine."
    assert rt(s, action="edit", name="movie", steps=["dim the lights"]).startswith("Updated the Movie night routine with 1 step")
    assert rt(s, action="delete", name="movie night").startswith("Ask the user to confirm")
    assert rt(s, action="delete", name="movie night", confirmed=True) == "Deleted the Movie night routine."
    assert rt(s, action="list") == "No routines saved yet."
    with pytest.raises(ValueError):
        rt(s, action="run", name="bedtime")
    with pytest.raises(ValueError):
        rt(s, action="save", name="x", steps=[])


def test_schedule_routine_makes_a_reminder(s):
    rt(s, action="save", name="Morning", steps=["read the news"])
    out = rt(s, action="schedule", name="morning", time="07:30", repeat="weekdays")
    assert out.startswith("I'll remind them tomorrow at 07:30, and every weekday after: Run my Morning routine.")
    assert reminders.load(s)[0]["at"] == "2026-09-29 07:30"
    assert routines.first_run("11:00", "weekdays", datetime(2026, 10, 2, 12, 0)) == "2026-10-05 11:00"
    with pytest.raises(ValueError):
        rt(s, action="schedule", name="morning", time="half seven")


def test_aliases(s):
    assert rt(s, action="alias_add", phrase="'Lights'", meaning="open the smart home app") == \
        "Got it: when the user says 'Lights', they mean 'open the smart home app'."
    assert "shortcut for: 'open the smart home app'. Carry that out now" in rt(s, action="alias_expand", phrase="lights")
    shown = rt(s, action="alias_list")
    assert shown.card["items"] == [{"label": "Lights → open the smart home app", "done": False, "say": "Lights"}]
    assert rt(s, action="alias_remove", phrase="lights") == "Removed the shortcut 'Lights'."
    assert rt(s, action="alias_list") == "No shortcuts saved yet."


def test_morning_briefing(s):
    s = replace(s, city="Leeds", calendar_url="https://cal.test/me.ics")
    todo.add(s, ["Call the bank", "Fix bike"])
    habits.mark(s, "Gym", date(2026, 9, 27))
    reminders.add(s, "2026-09-28 19:00", "call Mum", now=NOW)
    shown = brief(s, action="morning")
    rows = dict(shown.card["rows"])
    assert shown.card["kind"] == "table"
    assert rows["Date"] == "Monday 28 September 2026"
    assert rows["Weather"].startswith("Leeds, UK: 14°C")
    assert rows["Calendar"] == "15:00 Dentist at High Street"
    assert rows["To-dos"] == "2 open: Call the bank, Fix bike"
    assert rows["Reminders"] == "19:00 call Mum" and rows["Habits to do"] == "Gym"
    assert "one short spoken sentence" in shown


def test_evening_wrap_up(s):
    s = replace(s, calendar_url="https://cal.test/me.ics")
    todo.add(s, ["Call the bank", "Fix bike"])
    brief(s, action="morning")  # snapshot of this morning's to-dos
    todo.done(s, ["bank"])
    habits.mark(s, "Reading", NOW.date())
    money.log_spend(s, {"amount": 12.5, "what": "lunch"}, NOW.date())
    reminders.add(s, "2026-09-29 08:00", "bins out", now=NOW)
    rows = dict(brief(s, action="evening").card["rows"])
    assert rows["To-dos"] == "1 ticked off: Call the bank"
    assert rows["Habits done"] == "Reading" and rows["Spent today"] == "12.50 GBP"
    assert rows["Water"] == "0 of 8 glasses" and rows["Steps"] == "0"
    assert rows["Tomorrow"] == "09:00 Site visit" and rows["Tomorrow's reminders"] == "08:00 bins out"


def test_week_planner(s):
    reminders.add(s, "2026-09-29 08:00", "tablets", "daily", now=NOW)
    homestore.save(s, "bills.json", {"Rent": {"amount": 900, "day": 1}})
    homestore.save(s, "birthdays.json", {"Mum": "1965-10-03"})
    shown = brief(s, action="week")
    rows = shown.card["rows"]
    assert shown.card["columns"] == ["Day", "Time", "What", "Kind"]
    assert sum(r[2] == "tablets" for r in rows) == 6  # Tuesday to Sunday
    assert ["Thu 1", "", "Rent bill, 900.00 GBP", "Bill"] in rows
    assert ["Sat 3", "", "Mum's birthday (61)", "Birthday"] in rows
    assert "No calendar is connected" in shown.card["text"]


def test_whats_next(s):
    assert brief(s, action="next") == "Nothing else in the calendar or reminders today."
    s = replace(s, calendar_url="https://cal.test/me.ics")
    reminders.add(s, "2026-09-28 17:00", "call Mum", now=NOW)
    shown = brief(s, action="next")
    assert shown == "Next up today: Dentist at 15:00, in 4 hours 30 minutes."
    assert shown.card["kind"] == "timer" and shown.card["ends_at"] == int(datetime(2026, 9, 28, 15).timestamp() * 1000)


def test_help_from_docs(s):
    shown = brief(s, action="help")
    labels = [i["label"] for i in shown.card["items"]]
    assert any(label.startswith("Calculators (") for label in labels)
    topic = brief(s, action="help", topic="calculators")
    assert {"label": 'Sums: "What\'s 17.5 percent of 240 times 3?"', "done": False,
            "say": "What's 17.5 percent of 240 times 3?"} in topic.card["items"]
    assert any(i["say"] == "What have I copied?" for i in brief(s, action="help", topic="pc control").card["items"])


def test_thought_of_the_day(s):
    shown = brief(s, action="thought")
    assert len(routines_brief.QUESTIONS) == 40
    assert shown.card["text"] in routines_brief.QUESTIONS and shown.startswith("Today's reflective question:")


def test_inbox(s, tmp_path):
    assert cap(s, action="inbox_read") == "The inbox is empty."
    assert cap(s, action="inbox_add", text="buy a birthday card") == "Noted in your inbox. 1 note in it."
    cap(s, action="inbox_add", text="ring the garage")
    assert (tmp_path / "Ideas" / "Inbox.md").read_text() == \
        "# Inbox\n\n- 2026-09-28 10:30 buy a birthday card\n- 2026-09-28 10:30 ring the garage\n"
    shown = cap(s, action="inbox_read")
    assert len(shown.card["items"]) == 2 and "ring the garage" in shown
    assert cap(s, action="inbox_clear").startswith("Ask the user to confirm clearing 2 notes")
    assert cap(s, action="inbox_clear", confirmed=True) == "The inbox is cleared."
    assert cap(s, action="inbox_read") == "The inbox is empty."


def test_where_things_are(s):
    assert cap(s, action="where_save", thing="my passport", place="in the top drawer") == \
        "Remembered: passport is in the top drawer."
    assert cap(s, action="where_find", thing="my passport") == "passport is in the top drawer (noted 2026-09-28)."
    assert cap(s, action="where_find", thing="keys").startswith("I don't know where keys is.")
    assert cap(s, action="where_list").card["rows"] == [["passport", "in the top drawer", "2026-09-28"]]
    assert cap(s, action="where_forget", thing="passport") == "Forgotten where passport is."
    assert cap(s, action="where_list") == "I haven't been told where anything is yet."


def test_gratitude(s):
    assert cap(s, action="gratitude_month") == "No good things logged for 2026-09 yet."
    assert cap(s, action="gratitude_add", things=["sunny walk", "call with Sam"]) == \
        "Logged 2 good things for today; 2 so far today."
    shown = cap(s, action="gratitude_month", month="2026-09")
    assert shown.card["rows"] == [["28", "sunny walk; call with Sam"]] and shown.card["title"] == "Good things: September 2026"


def test_decisions(s):
    shown = lists(s, action="decision_add", decision="Move to Leeds", points=[
        {"side": "pro", "text": "cheaper rent", "weight": 4}, {"side": "con", "text": "far from friends", "weight": 3}])
    assert shown.startswith("Move to Leeds: pros score 4, cons 3, so leaning yes.")
    assert shown.card["rows"][-1] == ["", "Score", "+1"]
    shown = lists(s, action="decision_add", decision="move to leeds", points=[{"side": "con", "text": "long commute", "weight": 2}])
    assert "leaning no" in shown
    assert lists(s, action="decision_show", decision="leeds").card["kind"] == "table"
    assert lists(s, action="decision_list").card["items"][0]["say"] == "Show my pros and cons for Move to Leeds."
    assert lists(s, action="decision_delete", decision="leeds").startswith("Ask the user to confirm")
    assert lists(s, action="decision_delete", decision="leeds", confirmed=True) == "Deleted the Move to Leeds decision."
    assert lists(s, action="decision_list") == "No decisions being weighed up."


def test_checklists(s):
    assert lists(s, action="checklist_save", name="Leaving the house", items=["keys", "wallet", "hob off"]) == \
        "Saved the Leaving the house checklist with 3 items."
    shown = lists(s, action="checklist_start", name="leaving")
    assert shown.card["checks"] and [i["label"] for i in shown.card["items"]] == ["keys", "wallet", "hob off"]
    assert lists(s, action="checklist_list").card["items"][0]["say"] == "Start my Leaving the house checklist."
    assert lists(s, action="checklist_delete", name="leaving", confirmed=True) == "Deleted the Leaving the house checklist."
    assert lists(s, action="checklist_list") == "No checklists saved yet."


def test_lend_and_borrow(s):
    assert lists(s, action="loan_list") == "Nothing is lent out or borrowed."
    assert lists(s, action="loan_add", thing="drill", person="Sam", direction="lent", since="2026-09-20") == \
        "Noted: Sam has your drill."
    lists(s, action="loan_add", thing="ladder", person="Dad", direction="borrowed")
    shown = lists(s, action="loan_list")
    assert shown.card["rows"][0] == ["drill", "Sam", "lent", "2026-09-20", "8"]
    assert shown.startswith("Lent out: drill with Sam; Borrowed: ladder from Dad")
    assert lists(s, action="loan_returned", thing="drill") == "Marked returned: drill (Sam)."
    assert len(lists(s, action="loan_list").card["rows"]) == 1
    with pytest.raises(ValueError):
        lists(s, action="inbox_add", text="wrong tool")


def test_routines_registered_and_pop_up(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"routines", "daily_briefing", "capture_and_remember", "decisions_checklists_loans"} <= names
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        return await tools.run_tool("capture_and_remember", {"action": "where_list"}, s, None, page)

    cap(s, action="where_save", thing="keys", place="on the hook")
    assert asyncio.run(go()) == "1 thing remembered; they're on the screen."
    assert sent[0]["type"] == "popup" and sent[0]["card"]["id"] == "routines-where"
    assert not isinstance(routines.listing(s), screen.Shown)
