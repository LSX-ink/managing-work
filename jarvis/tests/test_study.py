import asyncio
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

import study_plan
import study_progress
import study_topics
import study_write
import screen
import tools
from config import Settings

TODAY = date(2026, 9, 29)


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def plan(s, **a):
    return study_plan.run_tool("study_plan", a, s, today=TODAY)


def topics(s, **a):
    return study_topics.run_tool("study_topics", a, s, today=TODAY)


def prog(s, **a):
    return asyncio.run(study_progress.run_tool("study_progress", a, s, today=TODAY))


def write(s, **a):
    return study_write.run_tool("study_write", a, s)


def seed(s):
    plan(s, action="add_course", subject="Maths", level="GCSE", exam_date="2026-10-12", target_grade="7")
    plan(s, action="add_course", subject="Biology", level="GCSE", exam_date="2026-10-20")


def test_courses_and_countdowns(s):
    seed(s)
    shown = plan(s, action="courses")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "table"
    assert shown.card["rows"][0][0] == "Maths" and shown.card["rows"][0][3] == "13 days"
    assert "Maths in 13 days" in shown
    assert (Path(s.memory_dir) / "study.json").exists()


def test_remove_course_needs_confirmation(s):
    seed(s)
    assert "confirm" in plan(s, action="remove_course", subject="Biology")
    assert "Biology" in [r[0] for r in plan(s, action="courses").card["rows"]]
    plan(s, action="remove_course", subject="Biology", confirmed=True)
    assert "Biology" not in [r[0] for r in plan(s, action="courses").card["rows"]]


def test_timetable_week_grid_leans_on_weak_topics(s):
    seed(s)
    topics(s, action="add_topics", subject="Biology", topics=["Cells", "Genetics"])
    topics(s, action="rate", subject="Biology", topic="Cells", confidence="red")
    shown = plan(s, action="timetable", sessions=3)
    assert shown.card["kind"] == "study-week"
    days = shown.card["data"]["days"]
    assert len(days) == 7 and days[0]["today"] and all(len(d["slots"]) == 3 for d in days[:5])
    assert shown.card["buttons"][0]["label"] == "Next week"
    later = plan(s, action="timetable", week=2)
    assert later.card["data"]["week"] == 2
    exam_day = next(d for d in later.card["data"]["days"] if d["exam"])
    assert exam_day["date"] == "2026-10-12" and "Maths" not in exam_day["slots"]
    with pytest.raises(ValueError):
        plan(s, action="timetable", week=9)


def test_timetable_needs_an_exam(s):
    with pytest.raises(ValueError):
        plan(s, action="timetable")


def test_timetable_includes_discover_exams(s):
    Path(s.memory_dir, "discover-exams.json").write_text(json.dumps([{"subject": "History", "date": "2026-10-05"}]))
    assert "History" in plan(s, action="courses").card["rows"][0][0]
    assert plan(s, action="timetable").card["data"]["subjects"] == ["History"]


def test_today_plan(s):
    seed(s)
    plan(s, action="add_deadline", title="Essay", subject="Biology", due="2026-10-01", priority="high")
    shown = plan(s, action="today")
    labels = [i["label"] for i in shown.card["items"]]
    assert any(label.startswith("Revise") for label in labels) and any("Essay" in label for label in labels)


def test_deadlines(s):
    plan(s, action="add_deadline", title="Coursework", subject="History", due="2026-10-10", priority="low")
    plan(s, action="add_deadline", title="Lab report", due="2026-09-28", priority="high")
    shown = plan(s, action="deadlines")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][0] == "Lab report"
    assert shown.card["rows"][0][3] == "OVERDUE" and "1 overdue" in shown
    plan(s, action="done_deadline", title="lab")
    assert len(plan(s, action="deadlines").card["rows"]) == 1
    with pytest.raises(ValueError):
        plan(s, action="add_deadline", title="X", due="2026-10-10", priority="urgent")


def test_exam_day_checklist(s):
    seed(s)
    topics(s, action="add_formula", subject="Maths", name="Circle area", formula="A = pi r^2")
    shown = plan(s, action="exam_day_checklist", subject="Maths")
    assert shown.card["kind"] == "list" and shown.card["checks"]
    assert "13 days" in shown and any("formula" in i["label"] for i in shown.card["items"])
    assert plan(s, action="exam_day_checklist").card["title"] == "Exam day checklist"


def test_topics_rate_and_checklist(s):
    seed(s)
    assert "3 topics" in topics(s, action="add_topics", subject="Maths", topics=["Algebra", "Geometry", "Number"])
    shown = topics(s, action="rate", subject="Maths", topic="algebra", confidence="amber")
    assert "amber" in shown and shown.card["items"][0]["label"].startswith("[A] Algebra")
    listed = topics(s, action="checklist", subject="Maths")
    assert listed.card["items"][1]["say"] == "Set Geometry in Maths to red."
    assert listed.card["items"][0]["say"] == "Set Algebra in Maths to green."
    with pytest.raises(ValueError):
        topics(s, action="rate", subject="Maths", topic="Algebra", confidence="purple")


def test_heatmap_weakest_and_review_due(s):
    seed(s)
    topics(s, action="add_topics", subject="Maths", topics="Algebra, Geometry")
    topics(s, action="add_topics", subject="Biology", topics=["Cells"])
    topics(s, action="rate", subject="Maths", topic="Algebra", confidence="red")
    topics(s, action="rate", subject="Biology", topic="Cells", confidence="green")
    heat = topics(s, action="heatmap")
    assert heat.card["kind"] == "study-heatmap" and len(heat.card["data"]["courses"]) == 2
    assert "1 of 3" in heat
    nxt = topics(s, action="revise_next")
    assert "Algebra" in nxt and nxt.card["items"][0]["label"].startswith("[R]")
    due = study_topics.run_tool("study_topics", {"action": "review_due"}, s, today=date(2026, 9, 30))
    assert "Algebra" in due.card["items"][0]["label"]
    assert "Nothing" in topics(s, action="review_due")


def test_remove_topic_confirmation(s):
    seed(s)
    topics(s, action="add_topics", subject="Maths", topics=["Algebra"])
    assert "confirm" in topics(s, action="remove_topic", subject="Maths", topic="Algebra")
    topics(s, action="remove_topic", subject="Maths", topic="Algebra", confirmed=True)
    with pytest.raises(ValueError):
        topics(s, action="checklist", subject="Maths")


def test_formula_sheet(s):
    seed(s)
    topics(s, action="add_formula", subject="Maths", name="Circle area", formula="A = pi r^2")
    topics(s, action="add_formula", subject="Maths", name="Circle area", formula="A = πr²")
    topics(s, action="add_formula", subject="Maths", name="Pythagoras", formula="a² + b² = c²")
    shown = topics(s, action="formula_sheet", subject="Maths")
    assert shown.card["kind"] == "study-formulas" and len(shown.card["data"]["items"]) == 2
    assert shown.card["data"]["items"][0]["formula"] == "A = πr²"
    assert "confirm" in topics(s, action="remove_formula", subject="Maths", name="Pythagoras")
    topics(s, action="remove_formula", subject="Maths", name="Pythagoras", confirmed=True)
    assert len(topics(s, action="formula_sheet", subject="Maths").card["data"]["items"]) == 1


def test_log_session_and_weekly_chart(s):
    seed(s)
    assert "90 minutes of Maths" in prog(s, action="log_session", subject="Maths", minutes=90)
    prog(s, action="log_session", subject="Biology", minutes=30)
    shown = prog(s, action="week_chart")
    assert shown.card["kind"] == "chart" and shown.card["chart"]["labels"] == ["Maths", "Biology"]
    assert shown.card["chart"]["values"] == [1.5, 0.5]
    weeks = prog(s, action="week_chart", weeks=4)
    assert weeks.card["chart"]["type"] == "line" and weeks.card["chart"]["values"][-1] == 2
    with pytest.raises(ValueError):
        prog(s, action="log_session")


def test_pomodoro_starts_and_logs_twenty_five_minutes(s):
    import timers

    async def go():
        seed(s)
        shown = await study_progress.run_tool("study_progress", {"action": "pomodoro", "subject": "Maths"}, s)
        logged = await study_progress.run_tool("study_progress", {"action": "log_session"}, s, today=date.today())
        for t in list(timers.timers.values()):
            t.task.cancel()
        timers.timers.clear()
        return shown, logged
    timers.timers.clear()
    shown, logged = asyncio.run(go())
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "timer" and shown.card["ends_at"] > 0
    assert "25 minutes of Maths" in logged


def test_past_papers_table_and_trend(s):
    seed(s)
    prog(s, action="set_boundaries", subject="Maths", boundaries=[
        {"grade": "5", "min_percent": 50}, {"grade": "7", "min_percent": 70}, {"grade": "9", "min_percent": 85}])
    assert "60 percent, grade 5" in prog(s, action="add_paper", subject="Maths", paper="Paper 1 2023", score=60,
                                         out_of=100, date="2026-09-01")
    said = prog(s, action="add_paper", subject="Maths", paper="Paper 2 2023", score=75, out_of=100, date="2026-09-15")
    assert "grade 7" in said and "up 15 points" in said
    table = prog(s, action="papers", subject="Maths")
    assert table.card["kind"] == "table" and table.card["rows"][1][3] == "75/100" and "68 percent" in table
    trend = prog(s, action="paper_trend", subject="Maths")
    assert trend.card["chart"]["type"] == "line" and trend.card["chart"]["values"] == [60, 75]
    with pytest.raises(ValueError):
        prog(s, action="add_paper", subject="Maths", paper="P", score=101, out_of=100)


def test_paper_trend_needs_two(s):
    seed(s)
    prog(s, action="add_paper", subject="Maths", paper="P1", score=5, out_of=10)
    with pytest.raises(ValueError):
        prog(s, action="paper_trend", subject="Maths")


def test_boundaries_and_grade_for(s):
    seed(s)
    with pytest.raises(ValueError):
        prog(s, action="grade_for", subject="Maths", percent=70)
    prog(s, action="set_boundaries", subject="Maths", boundaries=[{"grade": "4", "min_percent": 40},
                                                                  {"grade": "7", "min_percent": 72}])
    shown = prog(s, action="boundaries", subject="Maths")
    assert shown.card["rows"] == [["7", "72"], ["4", "40"]]
    assert "is a 7" in prog(s, action="grade_for", subject="Maths", score=36, out_of=50)
    assert "is a 4" in prog(s, action="grade_for", subject="Maths", percent=55)


def test_grade_calculator_needs_in_final(s):
    seed(s)
    prog(s, action="set_boundaries", subject="Maths", boundaries=[{"grade": "7", "min_percent": 70}])
    prog(s, action="set_component", subject="Maths", component="Coursework", weight=40, percent=80)
    said = prog(s, action="set_component", subject="Maths", component="Final exam", weight=50)
    assert "90 percent in all" in said
    prog(s, action="set_component", subject="Maths", component="Final exam", weight=60)
    shown = prog(s, action="grade_calc", subject="Maths", target_grade="7")
    assert shown.card["kind"] == "table" and "you need 63 percent in Final exam" in shown
    assert shown.card["rows"][-1][0] == "Needed in Final exam"
    assert "secured" in prog(s, action="grade_calc", subject="Maths", target_percent=30)
    assert "out of reach" in prog(s, action="grade_calc", subject="Maths", target_percent=95)
    prog(s, action="set_component", subject="Maths", component="Final exam", weight=60, percent=70)
    assert "All parts are marked" in prog(s, action="grade_calc", subject="Maths", target_percent=70)


def test_essay_plan_scaffold_has_instruction(s):
    text = write(s, action="essay_plan", question="To what extent was Macbeth responsible for his fall?",
                 essay_type="analyse", word_count=1200, subject="English")
    assert "INSTRUCTION for Alfred" in text and "1. Introduction" in text and "Macbeth" in text
    assert "argue" in write(s, action="essay_plan", question="Is homework useful?")


def test_citations(s):
    book = write(s, action="cite", style="harvard", source_type="book", authors="Smith, John and Ann Jones",
                 year="2020", title="Learning to Learn", publisher="Pearson", place="London", edition="2nd")
    assert book.card["kind"] == "text"
    assert book.card["text"] == "Smith, J. and Jones, A. (2020) Learning to Learn. 2nd edn. London: Pearson."
    apa = write(s, action="cite", style="apa", source_type="book", authors="John Smith; Ann Jones", year="2020",
                title="Learning to learn", publisher="Pearson")
    assert apa.card["text"] == "Smith, J., & Jones, A. (2020). Learning to learn. Pearson."
    web = write(s, action="cite", style="harvard", source_type="website", authors="BBC", year="2024",
                title="Bitesize revision", url="https://bbc.co.uk/bitesize", accessed="3 May 2026")
    assert "Available at: https://bbc.co.uk/bitesize (Accessed: 3 May 2026)" in web.card["text"]
    jour = write(s, action="cite", style="apa", source_type="journal", authors="Lee, Grace K.", year="2019",
                 title="Sleep and memory", journal="Journal of Study", volume="12", issue="3", pages="45-60")
    assert jour.card["text"] == "Lee, G. K. (2019). Sleep and memory. Journal of Study, 12(3), 45-60."
    hj = write(s, action="cite", style="harvard", source_type="journal", authors="Lee, Grace K.; Ng, P.; Ho, R.; Wu, T.",
               year="2019", title="Sleep and memory", journal="Journal of Study", volume="12", pages="45-60")
    assert hj.card["text"] == "Lee, G.K. et al. (2019) 'Sleep and memory', Journal of Study, 12, pp. 45-60."
    with pytest.raises(ValueError):
        write(s, action="cite", source_type="podcast", title="x")


def test_quiz_on_my_notes(s):
    notes = Path(s.memory_dir, "Notes")
    notes.mkdir(parents=True)
    (notes / "Photosynthesis.md").write_text("Photosynthesis turns light, water and carbon dioxide into glucose and oxygen "
                                             "in the chloroplasts of plant cells.")
    shown = write(s, action="quiz_notes", file="photosynthesis", questions=5)
    assert "chloroplasts" in shown and "one at a time" in shown and shown.card["kind"] == "text"
    with pytest.raises(ValueError):
        write(s, action="quiz_notes", file="nothing at all")
    (notes / "short.md").write_text("tiny")
    with pytest.raises(ValueError):
        write(s, action="quiz_notes", file="short")


def test_study_break_links_to_calm(s):
    shown = write(s, action="study_break", minutes=10)
    assert shown.card["kind"] == "list" and "10 minute break" == shown.card["title"]
    assert any("breathing" in i.get("say", "") for i in shown.card["items"])


def test_through_tools_run_tool_and_registry(s):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404))) as http:
            await tools._run_tool("study_plan", {"action": "add_course", "subject": "Physics", "exam_date": "2099-06-01"},
                                  s, http)
            return await tools._run_tool("study_plan", {"action": "courses"}, s, http)
    shown = asyncio.run(go())
    assert isinstance(shown, screen.Shown) and shown.card["rows"][0][0] == "Physics"
    assert {"study-week", "study-heatmap", "study-formulas"} <= screen.EXTRA_KINDS
