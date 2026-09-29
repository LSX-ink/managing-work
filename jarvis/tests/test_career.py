import json
from datetime import timedelta
from pathlib import Path

import pytest

import career_docs
import career_interview
import career_jobs
import career_plan
import career_store as cs
import screen
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


def jobs(s, **args):
    return career_jobs.run_tool("career_applications", args, s)


def interview(s, **args):
    return career_interview.run_tool("career_interview", args, s)


def docs(s, **args):
    return career_docs.run_tool("career_documents", args, s)


def plan(s, **args):
    return career_plan.run_tool("career_planning", args, s)


def test_registered_and_kinds():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"career_applications", "career_interview", "career_documents", "career_planning"} <= names
    assert {"career-board", "career-star", "career-compare"} <= screen.EXTRA_KINDS


def test_add_move_board_and_list(s):
    shown = jobs(s, action="add", company="Acme", role="Nurse", salary="£32k")
    assert isinstance(shown, screen.Shown) and shown.card["kind"] == "career-board"
    assert shown.card["data"]["cards"][0]["stage"] == "applied"
    with pytest.raises(ValueError):
        jobs(s, action="add", company="acme", role="nurse")
    moved = jobs(s, action="move", company="acme", stage="interview")
    assert moved.card["data"]["cards"][0]["stage"] == "interview"
    with pytest.raises(ValueError):
        jobs(s, action="move", company="acme", stage="bogus")
    assert jobs(s, action="board").card["kind"] == "career-board"
    listing = jobs(s, action="list")
    assert listing.card["kind"] == "table" and listing.card["rows"][0][:2] == ["Acme - Nurse", "interview"]
    assert jobs(s, action="list", stage="offer").startswith("No job")
    detail = jobs(s, action="show", company="Acme")
    assert "Stage: interview" in detail.card["text"]


def test_follow_ups(s):
    jobs(s, action="add", company="Acme", follow_up="yesterday")
    jobs(s, action="add", company="Beta", follow_up="next week")
    due = jobs(s, action="follow_ups")
    assert [i["label"].split(" - ")[0] for i in due.card["items"]] == ["Acme"]
    assert due.card["items"][0]["say"] == "I've followed up with Acme"
    jobs(s, action="followed_up", company="Acme")
    assert jobs(s, action="follow_ups") == "No job follow-ups are due today."
    cleared = jobs(s, action="set_follow_up", company="Beta")
    assert cleared.startswith("Cleared")
    shown = jobs(s, action="set_follow_up", company="Beta", follow_up="tomorrow")
    assert "remind you" in shown


def test_research_notes(s):
    jobs(s, action="add", company="Acme")
    assert jobs(s, action="notes", company="Acme").startswith("You have no research")
    shown = jobs(s, action="note", company="Acme", text="Values: kindness")
    assert shown.card["kind"] == "list" and shown.card["items"][0]["label"] == "Values: kindness"
    with pytest.raises(ValueError):
        jobs(s, action="note", company="Acme")


def test_remove_needs_confirmation(s):
    jobs(s, action="add", company="Acme")
    assert "Shall I remove" in jobs(s, action="remove", company="Acme")
    assert len(cs.load(s, cs.APPLICATIONS, [])) == 1
    jobs(s, action="remove", company="Acme", confirmed=True)
    assert cs.load(s, cs.APPLICATIONS, []) == []
    with pytest.raises(ValueError):
        jobs(s, action="show", company="Acme")


def test_stats_chart(s):
    assert jobs(s, action="stats").startswith("No applications")
    jobs(s, action="add", company="Acme")
    jobs(s, action="add", company="Beta")
    jobs(s, action="move", company="Beta", stage="rejected")
    shown = jobs(s, action="stats")
    chart = shown.card["chart"]
    assert len(chart["labels"]) == 8 and chart["values"][-1] == 2.0
    assert "1 rejections" in shown


def test_question_bank_and_one_question(s):
    shown = interview(s, action="question_bank", type="competency")
    assert shown.card["kind"] == "list" and len(shown.card["items"]) == 15
    assert shown.card["items"][0]["say"].startswith("Plan a STAR answer for:")
    assert len(interview(s, action="question_bank").card["items"]) == 75
    one = interview(s, action="question", type="strengths")
    assert one.card["buttons"][0]["label"] == "Plan a STAR answer"
    with pytest.raises(ValueError):
        interview(s, action="question_bank", type="quiz")


def test_star_planner(s):
    q = "Tell me about a time you led a team."
    shown = interview(s, action="star_save", question=q, situation="New project", action_taken="I planned it")
    assert shown.card["kind"] == "career-star" and shown.card["data"]["action"] == "I planned it"
    assert "2 of 4" in shown
    again = interview(s, action="star_save", question="led a team", result="Shipped early")
    assert "3 of 4" in again and len(cs.load(s, cs.STAR, {})) == 1
    assert interview(s, action="star_show", question="led a team").card["data"]["result"] == "Shipped early"
    assert interview(s, action="star_list").card["items"][0]["label"].endswith("(3/4)")
    with pytest.raises(ValueError):
        interview(s, action="star_save", question=q)
    with pytest.raises(ValueError):
        interview(s, action="star_show", question="nothing like it")


def test_negotiation_script_uses_brag_file(s):
    docs(s, action="brag_add", text="Cut waiting times by 20%")
    shown = interview(s, action="negotiation_script", role="Analyst", target="45k", offer="£40,000")
    assert "£45,000" in shown.card["text"] and "12% more" in shown.card["text"]
    assert "Cut waiting times by 20%" in shown.card["text"]
    with pytest.raises(ValueError):
        interview(s, action="negotiation_script")


def test_cover_letter_from_cv(s):
    (Path(s.memory_dir) / "cv.json").write_text(json.dumps({
        "name": "Sam Jones", "profile": "A careful, friendly nurse.", "skills": "Triage, First aid, Excel",
        "experience": "Ward nurse at St Mary's"}), encoding="utf-8")
    jobs(s, action="add", company="Acme", role="Staff Nurse")
    shown = docs(s, action="cover_letter", company="Acme")
    text = shown.card["text"]
    assert "Staff Nurse position at Acme" in text and "A careful, friendly nurse." in text
    assert "Triage, First aid, Excel" in text and text.rstrip().endswith("Sam Jones")
    assert list((Path(s.memory_dir) / "Documents" / "Letters").glob("Cover letter - Acme*.md"))
    docs(s, action="cover_template", text="Hi {company}, I'm {name} and want the {role} job.")
    assert docs(s, action="cover_letter", company="Beta", role="Chef").card["text"].startswith("Hi Beta, I'm Sam Jones")
    with pytest.raises(ValueError):
        docs(s, action="cover_template")


def test_brag_file(s):
    assert docs(s, action="brag_show").startswith("Your brag file is empty")
    docs(s, action="brag_add", text="Won the safety award", date="2026-03-01")
    shown = docs(s, action="brag_add", text="Trained 5 new starters")
    assert shown.card["rows"][0][1] == "Trained 5 new starters" and len(shown.card["rows"]) == 2
    found = docs(s, action="brag_show", query="award")
    assert found.card["rows"] == [["2026-03-01", "Won the safety award"]]
    with pytest.raises(ValueError):
        docs(s, action="brag_add")


def test_skills_gap(s):
    (Path(s.memory_dir) / "cv.json").write_text(json.dumps({"skills": "Excel, SQL"}), encoding="utf-8")
    shown = docs(s, action="skills_gap", role="Data analyst", skills=["Excel", "SQL", "Python", "Tableau"], have=["tableau"])
    assert shown.card["kind"] == "table"
    assert dict(map(tuple, shown.card["rows"])) == {"Excel": "have", "SQL": "have", "Python": "gap", "Tableau": "have"}
    assert "3 of 4" in shown and shown.card["buttons"][0]["say"] == "Help me learn Python."
    ticked = docs(s, action="skills_tick", role="data", skill="python")
    assert "No gaps" in ticked
    assert docs(s, action="skills_show").card["title"] == "Skills gap: Data analyst"
    with pytest.raises(ValueError):
        docs(s, action="skills_gap", role="X")
    with pytest.raises(ValueError):
        docs(s, action="skills_tick", role="Data", skill="Cooking")


def test_offer_comparison(s):
    first = plan(s, action="offer_add", company="Acme", pay="£40,000", commute="30", holiday="25", benefits=["Gym"])
    assert first.startswith("Saved the Acme")
    shown = plan(s, action="offer_add", company="Beta", pay="44k", commute="60", holiday="28", pension="5")
    card = shown.card
    assert card["kind"] == "career-compare" and card["data"]["offers"] == ["Acme", "Beta"]
    pay = card["data"]["rows"][0]
    assert pay["values"] == ["£40,000", "£44,000"] and pay["scores"] == [9.1, 10.0]
    assert card["data"]["rows"][1]["scores"] == [10.0, 5.0]
    weighted = plan(s, action="offer_weights", weights={"pay": 90, "commute": 5, "holiday": 5, "benefits": 0})
    assert weighted.card["data"]["totals"][1] > weighted.card["data"]["totals"][0]
    assert "Beta scores highest" in weighted
    assert plan(s, action="offer_compare", company="Beta").card["data"]["offers"][0] == "Beta"
    with pytest.raises(ValueError):
        plan(s, action="offer_compare", company="Nobody")
    with pytest.raises(ValueError):
        plan(s, action="offer_weights")
    assert "Shall I remove" in plan(s, action="offer_remove", company="Beta")
    assert plan(s, action="offer_remove", company="Beta", confirmed=True) == "Removed the Beta offer."
    with pytest.raises(ValueError):
        plan(s, action="offer_compare")


def test_contacts(s):
    shown = plan(s, action="contact_add", name="Priya Shah", company="Acme", text="Met at meetup", follow_up="yesterday")
    assert shown.card["kind"] == "table" and shown.card["rows"][0][:2] == ["Priya Shah", "Acme"]
    listing = plan(s, action="contact_list")
    assert "1 contacts are due" in listing and "Priya Shah" in listing.card["buttons"][0]["say"]
    done = plan(s, action="contact_done", name="priya")
    assert done.card["rows"][0][2] == (cs.today() + timedelta(days=30)).isoformat()
    with pytest.raises(ValueError):
        plan(s, action="contact_done", name="Nobody")


def test_career_goals(s):
    assert plan(s, action="goal_show") == "No career goals yet. Tell me one and we can add milestones."
    plan(s, action="goal_add", goal="Become team lead", date="2027-06-30")
    plan(s, action="milestone_add", goal="team lead", text="Lead a project")
    shown = plan(s, action="milestone_add", text="Do a management course")
    assert [i["done"] for i in shown.card["items"]] == [False, False] and shown.card["checks"]
    done = plan(s, action="milestone_done", goal="Become team lead", text="lead a project")
    assert done.card["items"][0]["done"] is True and "1 to go" in done
    assert "0 of 2" not in plan(s, action="goal_show")
    with pytest.raises(ValueError):
        plan(s, action="milestone_done", text="Fly to the moon")
    with pytest.raises(ValueError):
        plan(s, action="milestone_add", goal="Unknown goal", text="x")
