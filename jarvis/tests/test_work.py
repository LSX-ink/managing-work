import asyncio
import csv
from datetime import datetime

import pytest

import screen
import todo
import tools
import worktools_board
import worktools_meetings
import worktools_projects
import worktools_store
import worktools_time
from config import Settings

CLOCK = {}


@pytest.fixture
def s(tmp_path, monkeypatch):
    CLOCK["now"] = datetime(2026, 9, 28, 10, 0)  # a Monday
    monkeypatch.setattr(worktools_store, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path), tasks_file="")


def projects(s, **args):
    return worktools_projects.run_tool("work_projects", args, s)


def board(s, **args):
    return worktools_board.run_tool("work_board", args, s)


def time(s, **args):
    return worktools_time.run_tool("work_time", args, s)


def meet(s, **args):
    return worktools_meetings.run_tool("work_meetings", args, s)


def shown(out, kind):
    assert isinstance(out, screen.Shown), out
    assert out.card["kind"] == kind
    return out.card


def test_registered_with_four_tools():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"work_projects", "work_board", "work_time", "work_meetings"} <= names
    for module in (worktools_projects, worktools_board, worktools_time, worktools_meetings):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
    assert {"work-kanban", "work-actions", "work-summary"} <= screen.EXTRA_KINDS


def test_projects_add_list_update_archive(s):
    with pytest.raises(ValueError):
        board(s, action="show")
    card = shown(projects(s, action="add", project="Website", due="2026-10-05"), "table")
    assert card["rows"][0][:3] == ["Website", "active", "2026-10-05"]
    projects(s, action="add", project="Payroll", status="planning")
    with pytest.raises(ValueError):
        projects(s, action="add", project="website")
    with pytest.raises(ValueError):
        projects(s, action="update", project="website", status="sleepy")
    out = projects(s, action="update", project="web", status="on hold", notes="Waiting for copy")
    assert out.startswith("Updated Website: on hold")
    assert "2 work projects" in projects(s, action="list")
    assert projects(s, action="archive", project="payroll") == "Archived the Payroll project."
    assert [r[0] for r in shown(projects(s, action="list"), "table")["rows"]] == ["Website"]
    assert [r[0] for r in shown(projects(s, action="list", archived=True), "table")["rows"]] == ["Payroll"]
    projects(s, action="restore", project="payroll")
    assert len(shown(projects(s, action="list"), "table")["rows"]) == 2
    assert (s.memory_dir and (worktools_store.memory.root(s) / "worktools-projects.json").exists())


def test_board_by_voice(s):
    projects(s, action="add", project="Website")
    card = shown(board(s, action="add", card="Logo", due="2026-10-01"), "work-kanban")
    assert card["data"]["columns"] == ["To do", "Doing", "Done"]
    assert card["data"]["cards"][0] == {"title": "Logo", "column": "To do", "notes": "", "due": "2026-10-01"}
    with pytest.raises(ValueError):
        board(s, action="add", project="website", card="logo")
    board(s, action="add", project="website", card="Copy", column="doing")
    assert board(s, action="move", project="Website", card="logo", column="Doing") == "Moved Logo to Doing."
    assert board(s, action="note", card="logo", notes="Use the black one") == "Added a note to Logo."
    assert "Use the black one" in shown(board(s, action="card", card="logo"), "text")["text"]
    assert board(s, action="due", card="copy", due="2026-09-29") == "Copy is due 29 Sep (tomorrow)."
    board(s, action="move", card="copy", column="done")
    assert board(s, action="show").startswith("The Website board: 0 in To do, 1 in Doing, 1 in Done")
    out = board(s, action="remove", card="copy")
    assert not isinstance(out, screen.Shown) and "confirm" in out
    assert board(s, action="remove", card="copy", confirmed=True) == "Removed Copy from the Website board."
    card = shown(board(s, action="columns", columns=["Backlog", "Doing", "Review", "Shipped"]), "work-kanban")
    assert card["data"]["columns"][-1] == "Shipped"
    assert card["data"]["cards"][0]["column"] == "Doing"
    with pytest.raises(ValueError):
        board(s, action="move", card="logo", column="Nowhere")
    with pytest.raises(ValueError):
        board(s, action="move", card="ghost", column="Doing")


def test_ideas_deadlines_summary(s):
    projects(s, action="add", project="Website", due="2026-10-09", notes="Launch with marketing")
    projects(s, action="add", project="Payroll", due="2026-12-01")
    board(s, action="add", project="website", card="Logo", due="2026-09-27")
    card = shown(projects(s, action="idea_add", project="website", idea="Dark mode"), "list")
    assert card["items"][0]["say"] == "Add card Dark mode to the Website board."
    assert "1 ideas" in projects(s, action="ideas", project="website")
    assert "confirm" in projects(s, action="idea_remove", project="website", idea="dark")
    assert shown(projects(s, action="idea_remove", project="website", idea="dark", confirmed=True), "list")["items"] == []
    card = shown(projects(s, action="deadlines"), "table")
    assert card["rows"] == [["Logo", "Website", "27 Sep", "1 day overdue"],
                            ["Project deadline", "Website", "9 Oct", "in 11 days"]]
    time(s, action="log", project="website", minutes=90)
    card = shown(projects(s, action="summary", project="web"), "work-summary")
    stats = {x["label"]: x["value"] for x in card["data"]["stats"]}
    assert stats["To do"] == "1" and stats["This week"] == "1h 30m"
    notes = next(x for x in card["data"]["sections"] if x["heading"] == "Notes")
    assert notes["items"] == ["Launch with marketing"]


def test_timer_log_totals(s):
    projects(s, action="add", project="Website")
    projects(s, action="add", project="Payroll")
    assert time(s, action="stop") == "No work timer is running."
    card = shown(time(s, action="start", project="website"), "timer")
    assert card["started_at"] == int(CLOCK["now"].timestamp() * 1000)
    CLOCK["now"] = datetime(2026, 9, 28, 11, 30)
    assert shown(time(s, action="status"), "timer")
    out = time(s, action="start", project="payroll")
    assert out.startswith("Stopped Website after 1h 30m. Timing Payroll.")
    CLOCK["now"] = datetime(2026, 9, 28, 12, 0)
    assert time(s, action="stop") == "Stopped. Logged 30m on Payroll."
    assert time(s, action="log", project="website", minutes=60, date="2026-09-27") == \
        "Logged 1h on Website for 27 Sep. 1h on it that week."
    with pytest.raises(ValueError):
        time(s, action="log", project="website", minutes=0)
    card = shown(time(s, action="totals"), "chart")
    assert card["chart"]["labels"] == ["Website", "Payroll"] and card["chart"]["values"] == [1.5, 0.5]


def test_timesheet_and_csv_export(s):
    projects(s, action="add", project="Website")
    time(s, action="log", project="website", minutes=120, date="2026-09-28")
    time(s, action="log", project="website", minutes=30, date="2026-09-30")
    card = shown(time(s, action="timesheet"), "table")
    assert card["columns"] == ["Project (hours)", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert card["rows"][0] == ["Website (2.5h)", "2", "0", "0.5", "0", "0", "0", "0"]
    card = shown(time(s, action="export", week="this"), "file")
    assert card["mime"] == "text/csv"
    path = worktools_store.memory.root(s) / "Work" / "Timesheets" / "Timesheet week of 2026-09-28.csv"
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[1] == ["Website", "2", "0", "0.5", "0", "0", "0", "0", "2.5"]
    assert rows[-1][0] == "Total"


def test_focus_log_and_chart(s):
    projects(s, action="add", project="Website")
    assert time(s, action="focus_log", project="web", minutes=50) == \
        "Logged 50m of focus on Website. 50m of focus that week."
    time(s, action="focus_log", minutes=25, date="2026-09-29")
    card = shown(time(s, action="focus_week"), "chart")
    assert card["chart"]["values"][:2] == [50, 25]


def test_work_hours_finish_and_overtime(s):
    assert "working hours first" in time(s, action="finish")
    assert time(s, action="hours_set", start="09:00", end="17:30") == \
        "Working hours set: 09:00 to 17:30, Monday, Tuesday, Wednesday, Thursday, Friday; 42.5 hours a week expected."
    card = shown(time(s, action="finish"), "timer")
    assert card["ends_at"] == int(datetime(2026, 9, 28, 17, 30).timestamp() * 1000)
    CLOCK["now"] = datetime(2026, 9, 28, 18, 0)
    assert "time to stop" in time(s, action="finish")
    with pytest.raises(ValueError):
        time(s, action="hours_set", start="17:00", end="09:00")
    time(s, action="hours_set", start="09:00", end="17:00", weekly_hours=10)
    projects(s, action="add", project="Website")
    time(s, action="log", project="website", minutes=720)
    out = time(s, action="overtime")
    assert out.startswith("This week you're 2h over your 10 hours")
    card = shown(out, "table")
    assert card["rows"][3] == ["28 Sep", "10h", "12h", "2h"]


def test_meetings_actions_and_todo(s):
    card = shown(meet(s, action="meeting_add", title="Sprint planning", attendees=["Sam", "Jo"],
                      agenda=["Scope", "Dates"], notes="Agreed scope.", actions=["Sam to send budget"]), "file")
    path = worktools_store.memory.root(s) / "Work" / "Meetings" / "2026-09-28 Sprint planning.md"
    assert card["mime"] == "text/markdown" and "- [ ] Sam to send budget" in path.read_text(encoding="utf-8")
    meet(s, action="meeting_update", title="sprint", notes="Also agreed dates.", actions=["Jo to book room"])
    text = path.read_text(encoding="utf-8")
    assert "Also agreed dates." in text and "- [ ] Jo to book room" in text
    assert shown(meet(s, action="meeting_show"), "file")["name"] == path.name
    assert shown(meet(s, action="meetings"), "list")["items"][0]["say"] == "Show the meeting notes for Sprint planning."
    card = shown(meet(s, action="action_items"), "work-actions")
    assert [i["text"] for i in card["data"]["items"]] == ["Sam to send budget", "Jo to book room"]
    out = meet(s, action="action_done", item="budget")
    assert out.startswith("Ticked off Sam to send budget.")
    assert "- [x] Sam to send budget" in path.read_text(encoding="utf-8")
    assert meet(s, action="action_undone", item="budget").startswith("Reopened")
    with pytest.raises(ValueError):
        meet(s, action="action_undone", item="budget")
    # The To-do button's say line goes to the ordinary to-do list.
    todo.add(s, ["Sam to send budget"])
    assert todo.open_items(s) == ["Sam to send budget"]


def test_standups(s):
    assert meet(s, action="standup_last") == "No stand-ups saved yet."
    with pytest.raises(ValueError):
        meet(s, action="standup_save")
    assert meet(s, action="standup_save", yesterday="Logo", today="Copy", blockers="None") == \
        "Saved your stand-up for 28 Sep."
    out = meet(s, action="standup_last")
    assert "Yesterday: Logo" in shown(out, "text")["text"] and out.startswith("Your stand-up from 28 Sep.")


def test_weekly_report(s):
    projects(s, action="add", project="Website")
    board(s, action="add", card="Logo", column="Done")
    time(s, action="log", project="website", minutes=60)
    meet(s, action="meeting_add", title="Review", actions=["Fix footer"])
    out = projects(s, action="weekly_report")
    assert out.startswith("Week of 28 Sep: 1h worked, 1 cards finished, 1 meetings, 1 open action items.")
    card = shown(out, "work-summary")
    assert card["data"]["sections"][1]["items"] == ["Logo (Website)"]


def test_runs_through_tools(s):
    async def go():
        return await tools.run_tool("work_projects", {"action": "add", "project": "Alpha"}, s, None)

    assert asyncio.run(go()).startswith("Added the Alpha project")
