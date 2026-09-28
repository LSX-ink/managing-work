import asyncio
from datetime import date

import httpx
import pytest

import habits
import money
import notesearch
import todo
import tools
from config import Settings


def test_todo_list(tmp_path):
    s = Settings(memory_dir=str(tmp_path), tasks_file="")
    assert todo.run_tool("todo_list", {"action": "read"}, s) == "No open jobs."
    assert todo.add(s, ["Call the bank", "call the bank", "Fix bike"]) == "Added Call the bank, Fix bike. 2 open."
    assert todo.path(s) == tmp_path / "Personal" / "to-do.md"
    assert todo.done(s, ["bank"]) == "Ticked off Call the bank. 1 open."
    assert todo.path(s).read_text() == "- [x] Call the bank\n- [ ] Fix bike\n"
    assert tools.get_tasks(s) == "1 open jobs:\n- Fix bike"


def test_todo_uses_tasks_file(tmp_path):
    note = tmp_path / "tasks.md"
    note.write_text("# Jobs\n- [ ] Old job\n", encoding="utf-8")
    s = Settings(memory_dir=str(tmp_path / "m"), tasks_file=str(note))
    todo.add(s, ["New job"])
    assert note.read_text() == "# Jobs\n- [ ] Old job\n- [ ] New job\n"


def test_habit_streaks(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    day = date(2026, 9, 28)
    assert habits.mark(s, "Gym", date(2026, 9, 26)) == "Gym done today. Streak: 1 day."
    habits.mark(s, "gym", date(2026, 9, 27))
    assert habits.report(s, day) == "Habits:\n- Gym: streak 2 days, 2 of the last 7 days, not yet today"
    assert habits.mark(s, "GYM", day) == "Gym done today. Streak: 3 days."
    assert habits.forget(s, "gym") == "Stopped tracking Gym."
    assert habits.report(s, day) == "No habits tracked yet."


def test_money_log(tmp_path):
    s = Settings(memory_dir=str(tmp_path), currency="GBP")
    day = date(2026, 9, 28)
    money.log_payslip(s, {"month": "2026-08", "employer": "VGC", "net": 2000, "gross": 2600}, day)
    money.log_payslip(s, {"month": "2026-08", "employer": "vgc", "net": 2100}, day)  # corrects it
    money.log_payslip(s, {"month": "2026-09", "employer": "VGC", "net": 2300}, day)
    assert money.log_spend(s, {"amount": 12.5, "what": "lunch", "category": "Food"}, day) == \
        "Logged 12.50 GBP on lunch. This month so far: 12.50 GBP."
    out = money.summary(s, day)
    assert "- 2026-08 vgc: take-home 2,100.00 GBP" in out
    assert "Average take-home over these 2: 2,200.00 GBP; total 4,400.00 GBP." in out
    assert "This month (2026-09) spending: 12.50 GBP (food 12.50 GBP)." in out
    assert money.undo(s) == "Removed 12.50 GBP on lunch."
    with pytest.raises(ValueError):
        money.log_payslip(s, {"month": "August", "net": 1}, day)


def test_convert_currency():
    def handler(request):
        assert request.url.params["from"] == "GBP" and request.url.params["to"] == "ZAR"
        return httpx.Response(200, json={"amount": 10.0, "base": "GBP", "date": "2026-09-25", "rates": {"ZAR": 235.1}})

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return await tools.run_tool("convert_currency", {"amount": 10, "from": "gbp", "to": "zar"}, Settings(), http)

    assert asyncio.run(go()) == "10.00 GBP is 235.10 ZAR (European Central Bank rate from 2026-09-25)."


def test_search_memory(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    (tmp_path / "Ideas").mkdir()
    (tmp_path / "Ideas" / "boiler.md").write_text("The boiler service is due in March. Gas Safe engineer.", encoding="utf-8")
    (tmp_path / "Work").mkdir()
    (tmp_path / "Work" / "notes.txt").write_text("Nothing here", encoding="utf-8")
    out = notesearch.run_tool("search_memory", {"query": "boiler service"}, s)
    assert out.startswith("1 notes match") and "Ideas/boiler.md" in out
    assert notesearch.search(s, "unicorns") == "Nothing in the memory folders mentions unicorns."


def test_abilities_registered():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    for module in tools.ABILITIES:
        assert module.NAMES <= names


def test_tool_list_is_cached():
    from brain import request_options
    opts = request_options(Settings())
    assert sum("cache_control" in t for t in opts["tools"]) == 1
