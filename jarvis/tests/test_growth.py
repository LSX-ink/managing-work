import asyncio
from datetime import date

import httpx
import pytest

import growth_goals
import growth_media
import growth_reflect
import growth_store
import growth_study
import tools
from config import Settings


@pytest.fixture
def s(tmp_path):
    return Settings(memory_dir=str(tmp_path))


@pytest.fixture
def day(monkeypatch):
    """Pin today to Wednesday 30 September 2026; tests can move it with day.set(date)."""
    class Clock:
        now = date(2026, 9, 30)

        def set(self, when):
            self.now = when

    clock = Clock()
    monkeypatch.setattr(growth_store, "today", lambda: clock.now)
    return clock


def study(s, **args):
    return growth_study.run_tool("study", args, s)


def gf(s, **args):
    return growth_goals.run_tool("goals_and_fitness", args, s)


def media(s, **args):
    return growth_media.run_tool("reading_and_watching", args, s)


def reflect(s, **args):
    return growth_reflect.run_tool("reflect", args, s)


def test_flashcards_leitner(s, day, tmp_path):
    assert study(s, action="new_deck", deck="Capitals") == "Made a new deck called Capitals."
    assert study(s, action="new_deck", deck="capitals") == "You already have a capitals deck."
    assert study(s, action="add_card", deck="cap", front="Capital of Peru?", back="Lima") == \
        "Added a card to Capitals. It has 1 card."
    study(s, action="add_card", front="Capital of Chile?", back="Santiago")  # the only deck is assumed
    assert (tmp_path / "growth-flashcards.json").is_file()
    q = study(s, action="quiz", deck="Capitals")
    assert "Ask: Capital of Peru?" in q and "Lima" in q and "(2 due)" in q
    assert study(s, action="answer", right=True) == "Right. Moved to box 2. 1 card still due in Capitals."
    assert "Capital of Chile?" in study(s, action="quiz")
    assert study(s, action="answer", right=False) == "Not quite. Back to box 1. 1 card still due in Capitals."
    assert study(s, action="answer", right=True).startswith("There's no card waiting")
    assert study(s, action="deck_stats") == \
        "Flashcards:\n- Capitals: 2 cards, 1 due today, 50% right so far (box 1: 1, box 2: 1)"
    day.set(date(2026, 10, 2))  # box 2 waits two days
    assert "(2 due)" in study(s, action="quiz")
    with pytest.raises(ValueError, match="Which deck"):
        study(s, action="quiz", deck="History")


def test_language_phrases(s, day):
    out = study(s, action="phrase_of_day", language="Zulu")
    assert out.startswith("Today's Zulu phrase: ") and "It means:" in out
    assert out == study(s, action="phrase_of_day", language="zulu")  # same all day
    assert growth_study.phrase_quiz("French", pick=lambda xs: xs[0]) == \
        "French quiz. Ask what this means: Bonjour\nAnswer (keep it hidden until they reply): Good morning / hello"
    assert "Afrikaans quiz" in study(s, action="phrase_quiz", language="Afrikaans")
    assert all(len(p) == 15 for p in growth_study.PHRASES.values())
    with pytest.raises(ValueError):
        study(s, action="phrase_of_day", language="Klingon")


def test_study_hours(s, day):
    assert study(s, action="study_week") == "No study time logged this week."
    assert study(s, action="log_study", subject="Maths", minutes=90) == \
        "Logged 90 minutes of Maths. This week: 1 hour 30 minutes on it."
    study(s, action="log_study", subject="maths", minutes=30)
    study(s, action="log_study", subject="Python", minutes=45)
    assert study(s, action="study_week") == \
        "Study this week, 2 hours 45 minutes in all:\n- Maths: 2 hours\n- Python: 45 minutes"
    day.set(date(2026, 10, 5))  # next Monday
    assert study(s, action="study_week") == "No study time logged this week."


def test_goals(s, day):
    assert gf(s, action="goal_report") == "No goals set yet."
    assert gf(s, action="goal_set", name="Read books", target=20, unit="books", deadline="2026-12-31") == \
        "New goal: Read books, target 20 books, 92 days left."
    gf(s, action="goal_set", name="Learn guitar")
    assert gf(s, action="goal_log", name="read", amount=5) == "Read books: 5 of 20 books (25%)."
    assert gf(s, action="goal_log", name="guitar") == "Learn guitar: progress 1."
    assert gf(s, action="goal_report") == \
        "Goals:\n- Read books: 5 of 20 books (25%), 92 days left\n- Learn guitar: progress 1"
    assert "hit the target" in gf(s, action="goal_log", name="Read books", amount=15)
    assert gf(s, action="goal_achieved", name="read books") == "Marked Read books as achieved. Well done."
    assert gf(s, action="goal_report").endswith("Achieved this year: Read books.")
    with pytest.raises(ValueError):
        gf(s, action="goal_set", name="x", deadline="next year")


def test_workouts_and_bests(s, day):
    assert gf(s, action="workout_week") == "No workouts logged this week."
    assert gf(s, action="workout_log", exercise="Bench press", sets=3, reps=8, weight_kg=60) == \
        "Logged Bench press: 3 sets of 8 at 60 kg. That's a new personal best!"
    assert gf(s, action="workout_log", exercise="bench press", sets=3, reps=10, weight_kg=55) == \
        "Logged bench press: 3 sets of 10 at 55 kg."
    gf(s, action="workout_log", exercise="Run", minutes=30)
    week = gf(s, action="workout_week")
    assert week.startswith("This week: 3 workouts on 1 day, 30 minutes in all.") and "Wednesday: Run, 30 minutes" in week
    assert gf(s, action="personal_bests") == "Personal bests:\n- Bench press: 60 kg for 8 reps on 2026-09-30"


def test_steps(s, day):
    assert gf(s, action="steps_log", steps=6000, km=4.5) == "Today so far: 6,000 steps and 4.5 km."
    assert gf(s, action="steps_log", steps=1000) == "Today so far: 7,000 steps and 4.5 km."
    assert gf(s, action="steps_goal", amount=50000) == "Weekly step goal set to 50,000."
    assert gf(s, action="steps_week") == \
        "This week: 7,000 steps, 4.5 km against a goal of 50,000 (14%, 43,000 to go)."


def test_priorities_reset_each_day(s, day):
    assert gf(s, action="priorities_read") == "No priorities set for today yet."
    assert gf(s, action="priorities_set", items=["Gym", "Call mum", "Tax return"]) == \
        "Today's priorities: 1. Gym; 2. Call mum; 3. Tax return."
    assert gf(s, action="priority_done", item="2") == "Ticked off Call mum. 2 to go."
    assert gf(s, action="priority_done", item="tax") == "Ticked off Tax return. 1 to go."
    assert gf(s, action="priorities_read") == "Today's priorities:\n1. Gym\n2. Call mum (done)\n3. Tax return (done)"
    day.set(date(2026, 10, 1))
    assert gf(s, action="priorities_read") == "No priorities set for today yet."


def test_reading_list(s, day):
    assert media(s, action="book_add", title="Dune", author="Frank Herbert") == \
        "Added Dune by Frank Herbert to your reading list. 1 book waiting."
    media(s, action="book_add", title="Atomic Habits")
    assert media(s, action="book_reading", title="dune") == "Now reading Dune by Frank Herbert. Enjoy it."
    assert media(s, action="reading_now") == "Reading now: Dune by Frank Herbert.\nNext on the list (1): Atomic Habits."
    assert media(s, action="book_finished", title="Dune", rating=5) == \
        "Finished Dune by Frank Herbert, 5 stars. That's 1 book this year."
    assert media(s, action="books_this_year") == "1 book finished in 2026:\n- Dune by Frank Herbert, 5/5"
    with pytest.raises(ValueError):
        media(s, action="book_finished", title="Atomic Habits", rating=9)


def test_watch_list(s, day):
    assert media(s, action="watch_pick") == "Nothing on your watch list to pick from."
    assert media(s, action="watch_add", title="Oppenheimer", kind="film") == \
        "Added Oppenheimer to your watch list. 1 thing to watch."
    media(s, action="watch_add", title="Slow Horses", kind="series")
    assert media(s, action="watch_list", kind="series") == "To watch (1):\n- Slow Horses (series)"
    assert media(s, action="watched", title="oppen") == "Marked Oppenheimer as watched."
    assert media(s, action="watch_pick") == "Tonight's pick: Slow Horses (series)."


def test_bookmarks(s, day, monkeypatch):
    opened = []
    monkeypatch.setattr(growth_media.webbrowser, "open", opened.append)
    assert media(s, action="bookmark_save", url="https://docs.python.org/3/", title="Python docs", tag="Coding") == \
        "Saved Python docs under coding."
    with pytest.raises(ValueError):
        media(s, action="bookmark_save", url="file:///C:/secret.txt", title="bad")
    assert media(s, action="bookmarks") == "1 saved link. Tags: coding (1)."
    assert media(s, action="bookmarks", tag="coding") == "Links tagged coding:\n- Python docs: https://docs.python.org/3/"
    assert media(s, action="bookmark_open", title="python") == "Opened Python docs in your browser."
    assert opened == ["https://docs.python.org/3/"]


def test_quotes(s, day):
    assert media(s, action="quote_random") == "You haven't saved any quotes yet."
    assert media(s, action="quote_save", text="Stay hungry, stay foolish.", author="Steve Jobs") == \
        "Saved. You have 1 quote."
    assert media(s, action="quote_random") == "\"Stay hungry, stay foolish.\" — Steve Jobs"


def test_til_and_wins(s, day):
    assert reflect(s, action="til_add", text="Octopuses have three hearts") == "Noted. 1 thing learned this week."
    assert reflect(s, action="til_week") == "This week you learned (1):\n- Wednesday: Octopuses have three hearts"
    assert reflect(s, action="win_log", text="Ran 5k") == "Win logged. That's 1 win this month."
    assert reflect(s, action="wins_month") == "Your wins in September (1):\n- 30 Sep: Ran 5k"
    day.set(date(2026, 10, 1))
    assert reflect(s, action="wins_month") == "No wins logged yet in October."


def test_decisions(s, day):
    assert reflect(s, action="decision_log", text="Take the new job", expected="More growth") == \
        "Decision recorded. I'll bring it up for review after 30 days."
    assert reflect(s, action="decisions_revisit") == "No decisions older than 30 days waiting for review."
    day.set(date(2026, 11, 5))
    assert reflect(s, action="decisions_revisit") == \
        "Decisions to look back on (1):\n- 2026-09-30: Take the new job (expected: More growth)"
    assert reflect(s, action="decision_outcome", text="new job", outcome="Glad I did") == \
        "Outcome noted against that decision."
    assert reflect(s, action="decisions_revisit") == "No decisions older than 30 days waiting for review."


def test_weekly_review(s, day):
    gf(s, action="goal_set", name="Save money", target=1000, unit="pounds")
    gf(s, action="goal_log", name="save", amount=200)
    gf(s, action="workout_log", exercise="Swim", minutes=40)
    media(s, action="book_finished", title="Dune", rating=4)
    reflect(s, action="til_add", text="Python has match statements")
    gf(s, action="priorities_set", items=["Gym", "Email"])
    gf(s, action="priority_done", item="1")
    reflect(s, action="win_log", text="Fixed the boiler")
    out = reflect(s, action="weekly_review")
    assert out.startswith("Weekly review, 28 Sep to 30 Sep.")
    for part in ("- Save money: 200 of 1000 pounds (20%), +200 this week", "Swim, 40 minutes",
                 "Books finished: Dune.", "Python has match statements", "Priorities: 1 of 2 done (Gym).",
                 "Wins: Fixed the boiler.", "0 steps"):
        assert part in out


def test_growth_through_registry(s, day):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"study", "goals_and_fitness", "reading_and_watching", "reflect"} <= names

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(500))) as http:
            return await tools.run_tool("reflect", {"action": "til_week"}, s, http)

    assert asyncio.run(go()) == "Nothing logged as learned this week."
    for module in (growth_study, growth_goals, growth_media, growth_reflect):
        for tool in module.tool_definitions():
            assert tool["input_schema"]["additionalProperties"] is False
