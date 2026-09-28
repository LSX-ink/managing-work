import asyncio
import json
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pytest

import discover_codes as codes
import discover_games as games
import discover_science as science
import discover_study as study
import screen
import tools
from config import Settings

DAY = date(2026, 9, 28)


def _run(module, args, settings=None, handler=None, **kw):
    settings = settings or Settings()

    async def go():
        transport = httpx.MockTransport(handler or (lambda r: httpx.Response(500)))
        async with httpx.AsyncClient(transport=transport) as http:
            return await module.run_tool(module.tool_definitions()[0]["name"], args, settings, http, **kw)

    return asyncio.run(go())


def test_registered_and_deferred():
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"science_and_space", "learning_games", "codes_and_numbers", "study_planner"} <= names
    for module in (science, games, codes, study):
        assert module in tools.ABILITIES and module not in tools.ALWAYS_LOADED
        assert module.tool_definitions()[0]["input_schema"]["additionalProperties"] is False


# ---- Science and space -------------------------------------------------------------------------

def test_elements():
    assert len(science.ELEMENTS) == 118 and [e["number"] for e in science.ELEMENTS] == list(range(1, 119))
    out = _run(science, {"action": "element", "name": "Fe"})
    assert "Iron" in out and "group 8, period 4" in out and out.card["kind"] == "table"
    assert science.find_element("aluminum")["symbol"] == "Al"
    assert science.find_element("79")["name"] == "Gold"
    assert "f-block" in science.element("uranium")
    with pytest.raises(ValueError):
        science.find_element("kryptonite")


def test_periodic_table_card():
    out = _run(science, {"action": "periodic_table", "name": "neon"})
    card = out.card
    assert card["kind"] == "discover-periodic" and card["data"]["highlight"] == 10
    assert len(card["data"]["elements"]) == 118


def test_planets_and_moons():
    out = _run(science, {"action": "planet", "name": "Mars"})
    assert "rocky planet" in out and out.card["kind"] == "table"
    assert any(b["label"] == "Phobos" for b in out.card["buttons"])
    assert "Jupiter" in _run(science, {"action": "planet", "name": "Europa"})
    assert "dwarf planet" in science.planet("Pluto")
    table = _run(science, {"action": "compare_planets"})
    assert table.card["kind"] == "table" and len(table.card["rows"]) == 8


def test_constellations():
    out = _run(science, {"action": "constellations", "month": 1})
    assert "Orion" in out and out.card["kind"] == "list"
    assert out.card["items"][0]["say"].startswith("Tell me about the constellation")
    assert "Plough" in _run(science, {"action": "constellations", "name": "ursa major"})
    this_month = _run(science, {"action": "constellations"}, today=DAY)
    assert "September" in this_month


def test_planet_positions():
    # Known events: Jupiter at opposition 10 Jan 2026, Venus at greatest evening elongation mid-August 2026.
    assert abs(science.elongation("Jupiter", datetime(2026, 1, 10, tzinfo=timezone.utc))) > 175
    assert 43 < science.elongation("Venus", datetime(2026, 8, 15, tzinfo=timezone.utc)) < 49


def test_night_sky():
    def handler(request):
        if "geocoding" in request.url.host:
            return httpx.Response(200, json={"results": [{"name": "London", "latitude": 51.5, "longitude": -0.1,
                                                          "timezone": "Europe/London"}]})
        return httpx.Response(200, json={"daily": {"sunrise": ["2026-09-28T07:00"], "sunset": ["2026-09-28T18:40"]}})

    out = _run(science, {"action": "night_sky", "city": "London"}, handler=handler, today=DAY)
    assert "sunset 18:40" in out and "moon" in out and out.card["kind"] == "table"
    offline = _run(science, {"action": "night_sky", "city": "London"}, today=DAY)
    assert "couldn't get the sunset" in offline and "Saturn" in offline


def test_fact_of_day():
    out = _run(science, {"action": "fact_of_day"}, today=DAY)
    assert "Unit of the day" in out and out.card["kind"] == "text"
    assert out == _run(science, {"action": "fact_of_day"}, today=DAY)


def test_compare_countries():
    def handler(request):
        assert request.url.host == "restcountries.com"
        name = request.url.path.rsplit("/", 1)[-1]
        if name == "Atlantis":
            return httpx.Response(404, json={"status": 404})
        data = {"France": {"name": {"common": "France"}, "capital": ["Paris"], "population": 68000000,
                           "area": 551695, "currencies": {"EUR": {"name": "Euro"}}, "languages": {"fra": "French"},
                           "region": "Europe", "flag": "🇫🇷"},
                "Japan": {"name": {"common": "Japan"}, "capital": ["Tokyo"], "population": 124000000,
                          "area": 377930, "currencies": {"JPY": {"name": "Japanese yen"}},
                          "languages": {"jpn": "Japanese"}, "region": "Asia", "flag": "🇯🇵"}}
        return httpx.Response(200, json=[data[name]])

    out = _run(science, {"action": "compare_countries", "country": "France", "country2": "Japan"}, handler=handler)
    assert "Japan is more populous" in out
    assert out.card["columns"] == ["", "France", "Japan"] and ["Capital", "Paris", "Tokyo"] in out.card["rows"]
    with pytest.raises(ValueError, match="Atlantis"):
        _run(science, {"action": "compare_countries", "country": "France", "country2": "Atlantis"}, handler=handler)
    with pytest.raises(ValueError, match="isn't answering"):
        _run(science, {"action": "compare_countries", "country": "France", "country2": "Japan"})


# ---- Learning games ------------------------------------------------------------------------------

def _pending(s):
    return json.loads((Path(s.memory_dir) / ".discover-quiz.json").read_text())["pending"]


def test_times_tables(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = games.run_tool("learning_games", {"action": "times_tables", "table": 7}, s)
    card = out.card
    assert card["kind"] == "discover-quiz" and card["data"]["question"].startswith("What is 7 times")
    assert len(card["data"]["choices"]) == 4
    right = _pending(s)["answer"]
    assert card["data"]["choices"][0]["say"].startswith("Quiz answer: A, ")
    nxt = games.run_tool("learning_games", {"action": "answer", "answer": right}, s)
    assert nxt.startswith("Correct! Score 1 of 1.") and "7 times" in nxt
    letter = "ABCD"[_pending(s)["choices"].index(_pending(s)["answer"])]
    wrong = "ABCD".replace(letter, "")[0]
    assert games.run_tool("learning_games", {"action": "answer", "answer": wrong}, s).startswith("Not quite.")
    scores = games.run_tool("learning_games", {"action": "scores"}, s)
    assert "Times tables 1 of 2" in scores and scores.card["kind"] == "table"


def test_spelling_bee(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = games.run_tool("learning_games", {"action": "spelling_bee", "level": "hard"}, s)
    word = _pending(s)["answer"]
    assert word in out and word not in json.dumps(out.card) and out.card["data"]["input"] is True
    spelled = "-".join(word.upper())
    assert games.answer(s, f"my spelling is {spelled}").startswith("Correct!")
    word = _pending(s)["answer"]
    assert games.run_tool("learning_games", {"action": "give_up"}, s).startswith(
        f"No problem. It's spelled {'-'.join(word.upper())}.")


def test_body_and_kids_quiz(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert len(games.BODY_QUESTIONS) >= 40 and len(games.KIDS_QUESTIONS) >= 40
    out = games.run_tool("learning_games", {"action": "body_quiz"}, s)
    assert out.card["data"]["big"] is False
    assert games.answer(s, _pending(s)["answer"]).startswith("Correct!")
    kids = games.run_tool("learning_games", {"action": "kids_quiz"}, s)
    assert kids.card["data"]["big"] is True
    shown = games.run_tool("learning_games", {"action": "give_up"}, s)
    assert shown.startswith("No problem. The answer was") and shown.card["data"]["big"] is True


def test_timeline_quiz(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    out = games.run_tool("learning_games", {"action": "timeline_quiz"}, s)
    data = out.card["data"]
    assert data["order"] is True and len(data["choices"]) == 4
    pending = _pending(s)
    assert len(set(pending["years"])) == 4
    order = ", ".join(pending["answer"])
    assert games.answer(s, f"Timeline answer: {order}").startswith("Correct!")
    wrong = ", ".join(reversed(_pending(s)["answer"]))
    assert "The order is:" in games.answer(s, wrong)


def test_vocabulary(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    with pytest.raises(ValueError):
        games.run_tool("learning_games", {"action": "vocab_quiz"}, s)
    games.run_tool("learning_games", {"action": "vocab_add", "word": "ephemeral", "meaning": "lasting a short time"}, s)
    assert "2 words" in games.vocab_add(s, "ubiquitous", "found everywhere", DAY)
    assert games.vocab_add(s, "Ubiquitous", "seen everywhere", DAY).startswith("Updated")
    listed = games.run_tool("learning_games", {"action": "vocab_list"}, s)
    assert listed.card["kind"] == "list" and listed.card["items"][1]["label"] == "ubiquitous: seen everywhere"
    quiz = games.run_tool("learning_games", {"action": "vocab_quiz"}, s)
    assert quiz.card["data"]["question"].startswith("What does")
    word = _pending(s)["word"]
    games.answer(s, _pending(s)["answer"])
    saved = json.loads((tmp_path / "discover-vocab.json").read_text())
    assert next(w for w in saved if w["word"] == word)["right"] == 1
    assert "Say yes" in games.run_tool("learning_games", {"action": "vocab_forget", "word": "ephemeral"}, s)
    assert games.run_tool("learning_games", {"action": "vocab_forget", "word": "ephemeral", "confirmed": True},
                          s) == "Removed ephemeral. 1 word left."


def test_answer_without_question(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    assert "no quiz question" in games.run_tool("learning_games", {"action": "answer", "answer": "B"}, s)
    assert games.scores(s) == "No quiz scores yet."


# ---- Codes and numbers ---------------------------------------------------------------------------

def test_morse_both_ways():
    out = codes.run_tool("codes_and_numbers", {"action": "morse", "text": "SOS help"}, Settings())
    assert out.card["data"]["code"] == "... --- ... / .... . .-.. .--." and out.card["kind"] == "discover-code"
    back = codes.run_tool("codes_and_numbers", {"action": "morse_to_text", "text": "... --- ... / .... . .-.. .--."},
                          Settings())
    assert back == "That Morse code says: SOS HELP." and back.card["data"]["mode"] == "morse"
    with pytest.raises(ValueError):
        codes.from_morse("hello")


def test_nato_and_braille():
    out = codes.run_tool("codes_and_numbers", {"action": "nato", "text": "Ab 3"}, Settings())
    assert out == "Ab 3 in the phonetic alphabet: Alfa, Bravo, Three." and len(out.card["items"]) == 3
    br = codes.run_tool("codes_and_numbers", {"action": "braille", "text": "Hi 12"}, Settings())
    assert br.card["data"]["code"] == "⠠⠓⠊⠀⠼⠁⠃" and br.card["kind"] == "discover-code"


def test_number_facts():
    out = codes.run_tool("codes_and_numbers", {"action": "number_facts", "text": "144"}, Settings())
    assert out.startswith("144 is even, not prime (2 × 2 × 2 × 2 × 3 × 3), a Fibonacci number")
    rows = dict(out.card["rows"])
    assert rows["Binary"] == "10010000" and rows["Hexadecimal"] == "90" and rows["Perfect square?"] == "yes"
    assert "prime" in codes.number_facts("97") and dict(codes.number_facts("97").card["rows"])["Prime?"] == "yes"
    with pytest.raises(ValueError):
        codes.number_facts("lots")


# ---- Study planner -------------------------------------------------------------------------------

def test_study_planner(tmp_path):
    s = Settings(memory_dir=str(tmp_path))
    run = lambda args: study.run_tool("study_planner", args, s, today=DAY)  # noqa: E731
    with pytest.raises(ValueError):
        run({"action": "timetable"})
    assert run({"action": "add_exam", "subject": "Maths", "date": "2026-10-05"}).endswith("in 7 days.")
    run({"action": "add_exam", "subject": "History", "date": "2026-10-12"})
    with pytest.raises(ValueError):
        run({"action": "add_exam", "subject": "Art", "date": "2026-09-01"})
    listed = run({"action": "list_exams"})
    assert "next is Maths in 7 days" in listed and len(listed.card["rows"]) == 2
    table = run({"action": "timetable", "sessions": 2})
    rows = table.card["rows"]
    assert table.card["kind"] == "table" and rows[0][0] == "Mon 28 Sep" and len(rows) == 15
    assert rows[6][1] == "Maths, Maths" and rows[7][1].startswith("EXAM: Maths; then History")
    assert rows[-1][1] == "EXAM: History"
    assert "Say yes" in run({"action": "remove_exam", "subject": "maths"})
    assert run({"action": "remove_exam", "subject": "maths", "confirmed": True}) == "Removed the Maths exam."


def test_cards_are_valid_for_screen():
    for kind in ("discover-periodic", "discover-quiz", "discover-code"):
        assert kind in screen.EXTRA_KINDS
