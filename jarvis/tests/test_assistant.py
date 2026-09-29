import asyncio
import json
from datetime import date, datetime

import httpx
import pytest

import assistant_day
import assistant_inbox
import assistant_life
import assistant_track
import homestore
import people_store
import reminders
import routines_brief
import routines_life
import screen
import todo
import tools
import worktools_store
from config import Settings

CLOCK = {}
RSS = "<rss><channel><item><title>Big story</title></item><item><title>Another</title></item></channel></rss>"


@pytest.fixture
def s(tmp_path, monkeypatch):
    CLOCK["now"] = datetime(2026, 9, 29, 8, 30)  # a Tuesday
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path), currency="GBP", tasks_file="")


@pytest.fixture
def http():
    def handler(request):
        return httpx.Response(200, text=RSS)
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def calendar(monkeypatch, events):
    async def fake(http, settings, start, days):
        return events
    async def weather(http, settings):
        return "sunny, 18 degrees"
    monkeypatch.setattr(routines_brief, "_events", fake)
    monkeypatch.setattr(routines_brief, "_weather", weather)


def event(hour, title, where="", minute=0):
    return {"start": datetime(2026, 9, 29, hour, minute), "all_day": False, "title": title, "where": where}


def day(s, http=None, **args):
    return asyncio.run(assistant_day.run_tool("assistant_day", args, s, http))


def track(s, **args):
    return assistant_track.run_tool("assistant_track", args, s)


def inbox(s, **args):
    return assistant_inbox.run_tool("assistant_inbox", args, s)


def life(s, **args):
    return assistant_life.run_tool("assistant_life", args, s)


def sections(shown):
    return {sec["title"]: sec["lines"] for sec in shown.card["data"]["sections"]}


def test_registered_deferred_four_tools():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"assistant_day", "assistant_inbox", "assistant_life", "assistant_track"} <= names
    for m in (assistant_day, assistant_inbox, assistant_life, assistant_track):
        assert m in tools.ABILITIES and m not in tools.ALWAYS_LOADED
        for t in m.tool_definitions():
            assert t["input_schema"]["additionalProperties"] is False
    assert {"assistant-briefing", "assistant-timeline"} <= screen.EXTRA_KINDS


def test_briefing(s, http, monkeypatch):
    calendar(monkeypatch, [event(10, "Dentist", "High St")])
    todo.add(s, ["Pay the urgent bill", "Tidy desk"])
    track(s, action="followup_add", what="chase Sam", who="Sam", by="today", remind=False)
    life(s, action="forget_add", text="take my keys")
    life(s, action="countdown_add", label="Wedding anniversary", when="2020-10-03", kind="anniversary")
    life(s, action="pref_set", text="I don't like calls before 10")
    shown = day(s, http, action="briefing")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "assistant-briefing"
    sec = sections(shown)
    assert "10:00 Dentist at High St" in sec["Today"]
    assert sec["Start with"][0]["text"] == "Pay the urgent bill"
    assert "take my keys" in sec["Don't forget"]
    assert any("Wedding anniversary" in ln for ln in sec["Coming up"])
    assert any("chase Sam" in ln for ln in sec["Chase today"])
    assert "2 top headlines. First: Big story" in sec["News"][0]["text"]
    assert homestore.load(s, routines_brief.SNAPSHOT, {})["date"] == "2026-09-29"


def test_wrapup(s, http, monkeypatch):
    calendar(monkeypatch, [])
    todo.add(s, ["Pay the urgent bill", "Tidy desk"])
    day(s, http, action="briefing")
    todo.done(s, ["bill"])
    inbox(s, action="win_add", text="Finished the report")
    shown = day(s, http, action="wrapup")
    sec = sections(shown)
    assert shown.card["kind"] == "assistant-briefing"
    assert "Pay the urgent bill" in sec["Done today"] and "Finished the report" in sec["Done today"]
    assert sec["Still open"] == ["Tidy desk"]
    assert "Tidy desk" in sec["Tomorrow's first thing"][0]


def test_next_task_priority_energy_and_time(s):
    assert day(s, action="next_task") == "Nothing is waiting: your to-do list and follow-ups are clear."
    todo.add(s, ["Write the report", "Email the landlord", "Book urgent MOT"])
    top = day(s, action="next_task")
    assert top.card["kind"] == "assistant-briefing" and str(top) == "Do this next: Book urgent MOT."
    assert str(day(s, action="next_task", minutes=10, energy="low")).startswith("Do this next: Book urgent MOT")
    todo.done(s, ["MOT"])
    assert "Write the report" in str(day(s, action="next_task", energy="high"))
    assert "Email the landlord" in str(day(s, action="next_task", energy="low"))
    assert "low energy" in day(s, action="energy_set", energy="low", mood="tired")
    assert "Email the landlord" in str(day(s, action="next_task"))
    with pytest.raises(ValueError):
        day(s, action="energy_set", energy="huge")


def test_next_task_includes_chase_and_promises(s):
    track(s, action="followup_add", what="chase Sam", by="2026-09-28", remind=False)
    homestore.save(s, "people-promises.json", [{"person": "Mum", "what": "call on Sunday", "direction": "i_owe",
                                                "made": "2026-09-20", "due": "2026-09-29", "done": ""}])
    assert str(day(s, action="next_task")) == "Do this next: Chase: chase Sam."
    track(s, action="track_done", what="chase Sam")
    assert "promise to Mum" in str(day(s, action="next_task"))


def test_time_block(s, http, monkeypatch):
    calendar(monkeypatch, [event(11, "Team meeting")])
    todo.add(s, ["Call the bank", "Write the report", "Tidy desk"])
    life(s, action="pref_set", text="No calls before 10")
    shown = day(s, http, action="time_block")
    blocks = shown.card["data"]["blocks"]
    assert shown.card["kind"] == "assistant-timeline"
    assert {"start": "11:00", "end": "12:00", "label": "Team meeting", "kind": "event"} in blocks
    assert any(b["kind"] == "break" for b in blocks) and blocks == sorted(blocks, key=lambda b: b["start"])
    call = next(b for b in blocks if b["label"] == "Call the bank")
    assert call["start"] >= "10:00"
    with pytest.raises(ValueError):
        day(s, http, action="time_block", start="17:00", end="17:10", day="2026-10-01")


def test_meeting_prep(s, http, monkeypatch):
    calendar(monkeypatch, [event(14, "Catch up with Sam about budget", "Cafe")])
    people_store.save(s, {"Sam": {**people_store.blank(), "how": "school friend", "likes": ["coffee"]}})
    track(s, action="waiting_add", what="budget figures", who="Sam", remind=False)
    track(s, action="decision_log", text="Use the new budget template", why="simpler")
    worktools_store.save(s, worktools_store.MEETINGS, {"meetings": [
        {"title": "Budget review", "date": "2026-09-01", "notes": "Agreed to trim travel.", "actions": [{"text": "Send figures", "done": False}]}],
        "standups": {}})
    shown = day(s, http, action="meeting_prep")
    sec = sections(shown)
    assert shown.card["kind"] == "assistant-briefing" and "Sam: school friend" in sec["Who"]
    assert any("Agreed to trim travel" in ln for ln in sec["Last time"])
    assert any("budget figures" in ln for ln in sec["Open with them"])
    assert any("new budget template" in ln for ln in sec["Decisions so far"])
    with pytest.raises(ValueError):
        day(s, http, action="meeting_prep", meeting="nonexistent")
    calendar(monkeypatch, None)
    with pytest.raises(ValueError):
        day(s, http, action="meeting_prep")


def test_weekly_review(s):
    todo.add(s, ["Tidy desk"])
    inbox(s, action="win_add", text="Shipped it")
    track(s, action="waiting_add", what="quote", by="2026-09-01", remind=False)
    track(s, action="track_done", what="quote")
    day(s, action="focus_start", minutes=25)
    day(s, action="focus_stop")
    routines_life.inbox_add(s, "buy stamps")
    shown = day(s, action="weekly_review")
    sec = sections(shown)
    assert shown.card["kind"] == "assistant-briefing"
    assert sec["Wins"] == ["Shipped it"] and sec["Closed"] == ["quote"] and "Focus" in sec
    assert "1 in the inbox" in sec["Still open"][1]


def test_focus_mode(s):
    assert day(s, action="focus_status") == "Focus mode is off."
    assert day(s, action="focus_stop") == "Focus mode wasn't on."
    shown = day(s, action="focus_start", minutes=30, note="Writing, no calls", what="report")
    assert shown.card["kind"] == "timer" and shown.card["ends_at"] > 0 and "Writing, no calls" in shown.card["text"]
    CLOCK["now"] = datetime(2026, 9, 29, 8, 50)
    status = day(s, action="focus_status")
    assert "10 minutes left" in status and status.card["kind"] == "timer"
    stopped = day(s, action="focus_stop")
    assert "20 minutes" in stopped and stopped.card["kind"] == "close"
    assert day(s, action="focus_status") == "Focus mode is off."


def test_followup_waiting_delegate_and_list(s):
    said = track(s, action="followup_add", what="chase Sam for a reply", who="Sam", by="friday")
    assert "Follow-up saved" in said and "I'll remind you that morning" in said
    assert reminders.load(s)[0]["at"] == "2026-10-02 09:00"
    track(s, action="waiting_add", what="plumber's quote", who="Dan", by="2026-09-25", remind=False)
    track(s, action="delegate_add", what="book the venue", who="Priya", remind=False)
    shown = track(s, action="track_list")
    sec = sections(shown)
    assert shown.card["kind"] == "assistant-briefing" and "overdue" in str(shown)
    assert any("plumber's quote" in ln["text"] and "overdue by 4 days" in ln["text"] for ln in sec["Waiting for"])
    assert len(sec["Delegated"]) == 1
    assert "Waiting for" not in sections(track(s, action="track_list", kind="delegated"))
    due = track(s, action="track_list", due_only=True)
    assert "plumber's quote" in str(due) and "book the venue" not in str(due)
    assert track(s, action="track_done", what="plumber").startswith("Ticked off: plumber's quote")
    assert track(s, action="track_list", due_only=True) == "Nothing to chase today."
    with pytest.raises(ValueError):
        track(s, action="track_done", what="nothing like this")


def test_commitments_from_people_promises(s):
    assert track(s, action="commitments") == "Nothing is being chased, waited for or delegated."
    homestore.save(s, "people-promises.json", [
        {"person": "Mum", "what": "visit Sunday", "direction": "i_owe", "made": "2026-09-20", "due": "2026-10-04", "done": ""},
        {"person": "Sam", "what": "lend book", "direction": "owes_me", "made": "2026-09-20", "due": "", "done": ""}])
    shown = track(s, action="commitments")
    assert sections(shown) == {"Promises I made": ["To Mum: visit Sunday, in 5 days"]}
    assert "Ticked off your promise to Mum" in track(s, action="track_done", what="visit")
    assert track(s, action="commitments") == "Nothing is being chased, waited for or delegated."


def test_decisions(s):
    assert track(s, action="decisions_show") == "No decisions logged yet."
    assert track(s, action="decision_log", text="Go with option B", why="cheaper") == "Logged the decision: Go with option B."
    track(s, action="decision_log", text="Move the launch to March")
    shown = track(s, action="decisions_show")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][1] == "Move the launch to March"
    assert len(track(s, action="decisions_show", query="option").card["rows"]) == 1
    assert track(s, action="decisions_show", query="zzz") == "No decisions logged about zzz."


def test_inbox_capture_show_sort(s):
    assert inbox(s, action="inbox_show") == "The inbox is empty."
    assert "Noted in your inbox" in inbox(s, action="capture", text="buy stamps at the post office")
    inbox(s, action="capture", text="ring the dentist")
    inbox(s, action="capture", text="idea: a shed for the garden")
    inbox(s, action="capture", text="dentist tomorrow at 9")
    shown = inbox(s, action="inbox_show")
    assert shown.card["kind"] == "assistant-briefing"
    lines = sections(shown)["Click one to sort it"]
    assert "looks like: errand" in lines[0]["text"] and "looks like: todo" in lines[1]["text"]
    assert "looks like: note" in lines[2]["text"] and "looks like: reminder" in lines[3]["text"]
    assert "Sorted" in inbox(s, action="inbox_sort", item="1", place="Post Office")
    assert "Post Office" in str(inbox(s, action="errands_show"))
    assert "todos" in inbox(s, action="inbox_sort", item="dentist", to="todo")
    assert todo.open_items(s) == ["ring the dentist"]
    assert "Sorted notes" in inbox(s, action="inbox_sort", item="shed")
    assert "a shed for the garden" in open(f"{s.memory_dir}/Ideas/Sorted notes.md").read()
    inbox(s, action="inbox_sort", item="1", to="reminder", when="2026-09-30 09:00")
    assert reminders.load(s)[0]["at"] == "2026-09-30 09:00"
    assert inbox(s, action="inbox_show") == "The inbox is empty."
    with pytest.raises(ValueError):
        inbox(s, action="inbox_sort", item="nothing")


def test_errands_by_place(s):
    assert inbox(s, action="errands_show") == "No errands saved."
    inbox(s, action="errand_add", text="stamps", place="Post Office")
    inbox(s, action="errand_add", text="parcel", place="Post Office")
    inbox(s, action="errand_add", text="plasters", place="Boots")
    inbox(s, action="errand_add", text="something")
    shown = inbox(s, action="errands_show")
    titles = [sec["title"] for sec in shown.card["data"]["sections"]]
    assert titles == ["Post Office (2)", "Boots (1)", "Anywhere (1)"] and "Biggest batch: Post Office" in str(shown)
    assert inbox(s, action="errand_done", text="parcel") == "Done: parcel. 3 errands left."
    with pytest.raises(ValueError):
        inbox(s, action="errand_done", text="parcel")


def test_wins(s):
    assert inbox(s, action="wins_show").startswith("No wins")
    assert "Win logged" in inbox(s, action="win_add", text="Ran 5k")
    shown = inbox(s, action="wins_show", period="month")
    assert shown.card["kind"] == "assistant-briefing" and sections(shown)["Wins"] == ["Ran 5k"]


def test_preferences(s):
    assert life(s, action="pref_list") == "You haven't told me any preferences yet."
    assert "I'll respect" in life(s, action="pref_set", text="I don't like calls before 10")
    assert life(s, action="pref_set", text="i don't like calls before 10") == "I already have that preference."
    shown = life(s, action="pref_list")
    assert shown.card["kind"] == "assistant-briefing" and "calls before 10" in str(shown)
    assert "confirm" in life(s, action="pref_remove", text="calls before")
    assert life(s, action="pref_remove", text="calls before", confirmed=True).startswith("Removed")
    assert life(s, action="pref_list") == "You haven't told me any preferences yet."


def test_countdowns(s):
    assert life(s, action="countdown_list") == "No anniversaries or renewals saved."
    assert life(s, action="countdown_add", label="Wedding anniversary", when="2019-10-03", kind="anniversary") == \
        "Wedding anniversary saved, 4 days to go."
    life(s, action="countdown_add", label="Car insurance", when="2026-11-20", kind="renewal", cost="480 GBP", notice_days=60)
    shown = life(s, action="countdown_list")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][0] == "Wedding anniversary"
    assert shown.card["rows"][1][4] == "480 GBP" and "compare deals from" in shown.card["rows"][1][5]
    data = json.loads(open(f"{s.memory_dir}/assistant.json").read())
    assert len(data["countdowns"]) == 2
    with pytest.raises(ValueError):
        life(s, action="countdown_add", label="Bad", when="soon")
    assert "confirm" in life(s, action="countdown_remove", label="Car")
    assert life(s, action="countdown_remove", label="Car", confirmed=True) == "Removed Car insurance."


def test_forgetting_list(s):
    assert life(s, action="forget_list") == "Your list of things you keep forgetting is empty."
    life(s, action="forget_add", text="take my keys")
    assert life(s, action="forget_add", text="Take my keys") == "It's already on your list of things to remember."
    life(s, action="forget_add", text="water the plants")
    shown = life(s, action="forget_list")
    assert shown.card["kind"] == "assistant-briefing" and len(sections(shown)["All of them"]) == 2
    assert life(s, action="forget_remove", text="keys", confirmed=True) == "Removed take my keys."


def test_renewal_notice_in_countdown_soon(s):
    life(s, action="countdown_add", label="Car insurance", when="2026-11-20", kind="renewal", notice_days=60)
    import assistant_store as st
    soon = st.countdown_soon(st.load(s), date(2026, 9, 29), 21)
    assert soon and "time to compare deals" in soon[0]


def test_unknown_actions(s):
    for fn in (track, inbox, life):
        with pytest.raises(ValueError):
            fn(s, action="nope")
    with pytest.raises(ValueError):
        day(s, action="nope")
