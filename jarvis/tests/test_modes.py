import asyncio
from datetime import datetime, timedelta

import pytest

import homestore
import homewellbeing
import modes
import modes_debate
import modes_learning
import modes_practice
import screen
import tools
from config import Settings
from modes_data import INTERVIEW_QUESTIONS, MOTIONS

CLOCK = {"now": datetime(2026, 9, 28, 10, 0)}  # a Monday


def later(**kw) -> None:
    CLOCK["now"] += timedelta(**kw)


@pytest.fixture
def s(tmp_path, monkeypatch):
    CLOCK["now"] = datetime(2026, 9, 28, 10, 0)
    monkeypatch.setattr(homestore, "now", lambda: CLOCK["now"])
    return Settings(memory_dir=str(tmp_path))


def mode(s, **args):
    return modes.run_tool("conversation_mode", args, s)


def practice(s, **args):
    return modes_practice.run_tool("practice_session", args, s)


def learn(s, **args):
    return modes_learning.run_tool("learning_session", args, s)


def debate(s, **args):
    return modes_debate.run_tool("debate_and_ideas", args, s)


def test_data_banks():
    assert sum(len(v) for v in INTERVIEW_QUESTIONS.values()) == 60
    assert len(MOTIONS) == 40 and len(set(MOTIONS)) == 40


def test_switch_mode_current_and_normal(s, tmp_path):
    out = mode(s, action="start", mode="ELI5")
    assert out.startswith("From now on until the user says stop: you are in Explain simply mode.")
    assert out.card["kind"] == "modes-badge" and out.card["data"]["label"] == "Explain simply"
    assert out.card["buttons"] == [{"label": "Back to normal", "say": "Normal mode please."}]
    assert (tmp_path / "modes-state.json").exists()
    later(minutes=5)
    now = mode(s, action="current")
    assert "Explain simply mode for 5 minutes" in now and now.card["id"] == "modes-badge"
    assert "devil's advocate" in mode(s, action="start", mode="devil's advocate mode", topic="my new job").lower()
    later(minutes=10)
    stopped = mode(s, action="stop")
    assert stopped.startswith("Left Devil's advocate mode") and stopped.card["kind"] == "close"
    assert mode(s, action="current") == "No special mode is on; you're in normal mode."
    assert mode(s, action="stop").startswith("You're already in normal mode")
    with pytest.raises(ValueError):
        mode(s, action="start", mode="pirate")


def test_every_builtin_mode_starts(s):
    for name in ["tutor", "coach", "debate", "interviewer", "language", "storyteller", "quiz", "brainstorm",
                 "rubber duck", "calm listener", "devils_advocate", "eli5", "concise", "chatty", "roleplay"]:
        out = mode(s, action="start", mode=name)
        assert isinstance(out, screen.Shown), name
    assert mode(s, action="start", mode="normal").startswith("Left")


def test_mode_history_this_week(s):
    mode(s, action="start", mode="concise")
    later(minutes=30)
    mode(s, action="start", mode="chatty")
    later(minutes=12)
    out = mode(s, action="history")
    assert out == "Modes this week: Concise 30 minutes, Chatty 12 minutes."
    assert out.card["chart"]["labels"] == ["Concise", "Chatty"] and out.card["chart"]["values"] == [30.0, 12.0]


def test_custom_modes(s):
    assert mode(s, action="custom_add", name="Pirate", instructions="Talk like a pirate.").startswith("Saved your Pirate")
    with pytest.raises(ValueError):
        mode(s, action="custom_add", name="Concise", instructions="x")
    listed = mode(s, action="custom_list")
    assert listed.card["items"][0]["say"] == "Switch to my Pirate mode."
    out = mode(s, action="start", mode="pirate mode")
    assert "Talk like a pirate." in out and out.card["data"]["label"] == "Pirate"
    assert "confirm" in mode(s, action="custom_delete", name="pirate")
    assert mode(s, action="custom_delete", name="pirate", confirmed=True) == "Deleted your Pirate mode."
    assert mode(s, action="current").startswith("No special mode")
    assert mode(s, action="custom_list") == "You haven't made any custom modes yet."


def test_duck_checklist(s):
    out = mode(s, action="duck_checklist")
    assert out.card["checks"] is True and len(out.card["items"]) > 5


def test_daily_checkin_writes_mood_through_wellbeing(s, tmp_path):
    started = mode(s, action="checkin_start")
    assert "energy" in started and modes.load_state(s)["mode"] == "checkin"
    out = mode(s, action="checkin_save", energy=4, mood=3, focus=2, note="tired")
    assert out.startswith("Check-in saved: energy 4, mood 3, focus 2.")
    assert modes.load_state(s) == {}
    assert homewellbeing.load(s)["mood"] == [{"date": "2026-09-28", "mood": 3, "note": "tired"}]
    series = {x["name"]: x["values"][-1] for x in out.card["data"]["series"]}
    assert series == {"Energy": 4, "Mood": 3, "Focus": 2} and out.card["kind"] == "modes-checkin"
    chart = mode(s, action="checkin_chart")
    assert chart == "1 check-in in the last 14 days." and len(chart.card["data"]["labels"]) == 14
    with pytest.raises(ValueError):
        mode(s, action="checkin_save", energy=9, mood=3, focus=2)


def test_interview_practice(s, monkeypatch):
    monkeypatch.setattr(modes_practice.random, "shuffle", lambda x: None)
    out = practice(s, action="interview_start", role="nurse", level="senior", question_type="behavioural")
    assert "interviewing the user for a senior nurse role" in out
    assert out.card["title"] == "Question 1 - behavioural" and out.card["text"] == INTERVIEW_QUESTIONS["behavioural"][0]
    assert out.card["buttons"][0]["label"] == "STAR tips"
    assert "saved answer 1" in practice(s, action="interview_feedback", answer="Calmed a patient",
                                         feedback="Good; add a result.", score=4).lower()
    nxt = practice(s, action="interview_next")
    assert nxt.startswith("Question 2 (behavioural):")
    log = practice(s, action="interview_log")
    assert log.card["rows"] == [[INTERVIEW_QUESTIONS["behavioural"][0], "Calmed a patient", "Good; add a result.", "4"]]
    star = practice(s, action="star_tip")
    assert "Situation" in star.card["text"]
    mode(s, action="stop")
    with pytest.raises(ValueError):
        practice(s, action="interview_next")


def test_talk_timer_and_fillers(s):
    started = practice(s, action="talk_start", title="Best man speech")
    assert started.card["kind"] == "timer" and started.card["started_at"] == int(CLOCK["now"].timestamp() * 1000)
    later(minutes=2)
    out = practice(s, action="talk_stop", text=" ".join(["word"] * 300))
    assert out.startswith("That took 2:00. 300 words is 150 words a minute, a comfortable pace")
    assert out.card["rows"] == [["2026-09-28", "Best man speech", "2:00", "150"]]
    with pytest.raises(ValueError):
        practice(s, action="talk_stop")
    fill = practice(s, action="filler_count", text="Um so like I was, you know, basically um going. Actually no.")
    assert fill.startswith("6 filler words in 12, about 50.0 per hundred")
    assert fill.card["chart"]["labels"][0] == "um" and fill.card["chart"]["values"][0] == 2
    assert practice(s, action="filler_count", text="Clean and clear.").startswith("No filler words")


def test_roleplay(s):
    listed = practice(s, action="roleplay_list")
    assert any(i["label"].startswith("Asking for a raise (hard)") for i in listed.card["items"])
    out = practice(s, action="roleplay_start", scenario="restaurant", difficulty="hard")
    assert "You play a waiter" in out and "Difficulty hard" in out
    assert out.card["title"] == "Role-play: Ordering at a restaurant"
    assert modes.load_state(s)["mode"] == "roleplay"
    with pytest.raises(ValueError):
        practice(s, action="roleplay_start", scenario="restaurant", difficulty="brutal")


def test_language_partner_and_words(s):
    out = learn(s, action="language_start", language="spanish", level="b1", topic="Travel stories")
    assert "Hold a conversation in Spanish about 'Travel stories' at CEFR level B1" in out
    assert out.card["title"] == "Spanish B1: Travel stories"
    topics = learn(s, action="language_topics")
    assert topics.card["items"][0]["say"] == "Change our Spanish conversation topic to Work and jobs."
    assert learn(s, action="word_add", word="el billete", meaning="ticket") == "Saved el billete to your Spanish words; 1 so far."
    listed = learn(s, action="word_list")
    assert listed.card["rows"] == [["el billete", "ticket", "2026-09-28"]]
    with pytest.raises(ValueError):
        learn(s, action="language_start", language="French", level="C2")


def test_socratic_tutor(s):
    out = learn(s, action="tutor_start", subject="Fractions", level="year 6")
    assert "Socratic method" in out and out.card["kind"] == "modes-badge"
    learn(s, action="tutor_log", question="What is half of a half?")
    assert learn(s, action="tutor_log", concept="Equivalent fractions").endswith("1 question asked, 1 concept understood.")
    prog = learn(s, action="tutor_progress")
    assert prog.card["items"][0] == {"label": "Equivalent fractions", "done": True, "say": ""}
    mode(s, action="stop")
    assert "They already understand: Equivalent fractions" in learn(s, action="tutor_start", subject="fractions")
    mode(s, action="stop")
    assert learn(s, action="tutor_progress").card["rows"] == [["Fractions", "beginner", "1", "1"]]


def test_quiz_master_scoreboard(s):
    out = learn(s, action="quiz_start", topic="Rivers", questions=2)
    assert out.card["kind"] == "modes-scoreboard" and out.card["data"]["total"] == 2
    one = learn(s, action="quiz_mark", correct=True, question="Longest UK river?")
    assert one.startswith("Score 1 of 1. Ask question 2 of 2.")
    board = learn(s, action="quiz_board")
    assert board.card["data"]["marks"] == [True]
    done = learn(s, action="quiz_mark", correct=False)
    assert done.startswith("Quiz over: 1 out of 2") and done.card["data"]["finished"] is True
    assert modes.load_state(s) == {}
    assert learn(s, action="quiz_board").startswith("Your last quiz, Rivers: 1 out of 2")
    learn(s, action="quiz_start", topic="Maths")
    learn(s, action="quiz_mark", correct=True)
    ended = learn(s, action="quiz_end")
    assert ended.startswith("Quiz ended: 1 out of 1") and ended.card["data"]["recent"][0]["topic"] == "Maths"


def test_debate(s):
    assert len(debate(s, action="debate_motions").card["items"]) == 40
    out = debate(s, action="debate_start", motion="3", side="against")
    assert "The user argues against, you argue for" in out and MOTIONS[2] in out
    debate(s, action="debate_point", by="user", point="Freedom of choice")
    debate(s, action="debate_point", by="alfred", point="Legitimacy")
    assert debate(s, action="debate_next_round") == "Round 2 begins. Invite the user to make their next point."
    debate(s, action="debate_point", by="user", point="Cost")
    summary = debate(s, action="debate_summary")
    assert summary.card["kind"] == "modes-debate"
    assert summary.card["data"]["rounds"] == [{"user": ["Freedom of choice"], "alfred": ["Legitimacy"]},
                                              {"user": ["Cost"], "alfred": []}]
    mode(s, action="stop")
    assert debate(s, action="debate_summary").startswith("3 arguments over 2 rounds")
    with pytest.raises(ValueError):
        debate(s, action="debate_point", by="user", point="late")


def test_brainstorm_board_and_export(s, tmp_path):
    out = mode(s, action="start", mode="brainstorm", topic="Birthday party")
    assert "Brainstorm 'Birthday party'" in out and out.card["kind"] == "modes-board"
    added = debate(s, action="idea_add", ideas=["Karaoke", "Treasure hunt", "karaoke"])
    assert added.startswith("Saved. 2 ideas") and len(added.card["data"]["ideas"]) == 2
    star = debate(s, action="idea_star", number=2)
    assert star == "Starred Treasure hunt." and star.card["data"]["ideas"][1]["star"] is True
    assert star.card["data"]["ideas"][1]["star_say"] == "Unstar idea 2 on the brainstorm board."
    debate(s, action="idea_add", ideas=["Bake-off"])
    assert debate(s, action="idea_remove", number=1) == "Removed Karaoke."
    assert debate(s, action="idea_board").startswith("2 ideas on the Birthday party board, 1 starred.")
    exported = debate(s, action="idea_export")
    assert exported.card["kind"] == "file" and exported.card["name"] == "Brainstorm Birthday party.md"
    text = (tmp_path / "Ideas" / "Brainstorm Birthday party.md").read_text(encoding="utf-8")
    assert "## Starred\n- Treasure hunt" in text and "- Bake-off" in text
    with pytest.raises(ValueError):
        debate(s, action="idea_remove", number=9)


def test_tools_route_and_pop_up(s):
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        return await tools.run_tool("conversation_mode", {"action": "start", "mode": "coach"}, s, None, page)

    out = asyncio.run(go())
    assert "Coach mode" in out and sent[0]["card"]["kind"] == "modes-badge"
