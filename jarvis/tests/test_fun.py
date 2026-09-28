import asyncio

import httpx
import pytest

import fun
import tools
from config import Settings


@pytest.fixture(autouse=True)
def fresh_games():
    fun.state.update({"trivia": None, "number": None, "riddle": None, "scramble": None, "jokes_told": set(),
                      "scores": {}})
    fun.rng.seed(7)
    yield


def call(args, handler=None, name="play_game"):
    def refuse(request):
        raise AssertionError(f"Unexpected request to {request.url}")

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler or refuse)) as http:
            return await tools.run_tool(name, args, Settings(), http)

    return asyncio.run(go())


def trivia_handler(request):
    assert request.url.host == "opentdb.com"
    assert request.url.params["type"] == "multiple" and request.url.params["category"] == "22"
    assert request.url.params["difficulty"] == "easy"
    return httpx.Response(200, json={"response_code": 0, "results": [{
        "category": "Geography", "type": "multiple", "difficulty": "easy",
        "question": "What is the capital of the &quot;Land Down Under&quot;?",
        "correct_answer": "Canberra", "incorrect_answers": ["Sydney", "Melbourne", "Perth"]}]})


def test_trivia_right_wrong_and_score():
    q = call({"game": "trivia", "action": "start", "category": "geography", "difficulty": "easy"}, trivia_handler)
    assert q.startswith('Geography. What is the capital of the "Land Down Under"? A: ')
    letter = fun.LETTERS[fun.state["trivia"]["options"].index("Canberra")]
    assert call({"game": "trivia", "action": "answer", "answer": letter}) == "Correct! Trivia score: 1 out of 1."
    call({"game": "trivia", "action": "start", "category": "geography", "difficulty": "easy"}, trivia_handler)
    assert call({"game": "trivia", "action": "answer", "answer": "sydney"}) == \
        "Not quite. The answer was Canberra. Trivia score: 1 out of 2."
    assert call({"game": "trivia", "action": "answer", "answer": "a"}).startswith("There's no trivia question")
    call({"game": "trivia", "action": "start", "category": "geography", "difficulty": "easy"}, trivia_handler)
    assert call({"game": "trivia", "action": "reveal"}) == "The answer was Canberra."
    assert call({"action": "score"}) == "Scores this session. trivia: 1 won, 2 lost."


def test_trivia_service_empty():
    handler = lambda r: httpx.Response(200, json={"response_code": 1, "results": []})  # noqa: E731
    with pytest.raises(ValueError):
        asyncio.run(_trivia(handler))


async def _trivia(handler):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        return await fun.trivia_question(http)


def test_guess_the_number():
    assert "between 1 and 100" in call({"game": "number", "action": "start"})
    secret = fun.state["number"]["secret"]
    low = call({"game": "number", "action": "answer", "answer": str(secret - 1)}) if secret > 1 else None
    if low:
        assert low.startswith(f"Higher than {secret - 1}.")
    assert call({"game": "number", "action": "answer", "answer": "101"}).startswith("Lower than 101.")
    assert call({"game": "number", "action": "answer", "answer": f"is it {secret}?"}).startswith(f"Yes! It was {secret}.")
    call({"game": "number", "action": "start"})
    assert call({"game": "number", "action": "reveal"}).startswith("The number was ")
    assert call({"game": "number", "action": "answer", "answer": "5"}).startswith("We're not playing")


def test_rock_paper_scissors():
    out = call({"game": "rps", "action": "answer", "answer": "Rock!"})
    assert out.startswith("I chose ") and "Score: you " in out
    assert call({"game": "rps", "action": "answer", "answer": "banana"}) == "Say rock, paper or scissors."
    fun.rng.choice = lambda seq: "scissors"
    try:
        assert call({"game": "rps", "action": "answer", "answer": "rock"}).startswith("I chose scissors. You win!")
        assert call({"game": "rps", "action": "answer", "answer": "paper"}).startswith("I chose scissors. I win!")
        assert call({"game": "rps", "action": "answer", "answer": "scissors"}).startswith("I chose scissors. It's a draw.")
    finally:
        del fun.rng.choice


def test_riddles():
    question = call({"game": "riddle", "action": "start"})
    riddle = next(r for r in fun.RIDDLES if r[0] == question)
    assert call({"game": "riddle", "action": "answer", "answer": "a hippopotamus"}).startswith("Not quite")
    assert call({"game": "riddle", "action": "answer", "answer": f"is it {riddle[2][0]}"}) == f"Correct, it's {riddle[1]}!"
    call({"game": "riddle", "action": "start"})
    assert call({"game": "riddle", "action": "reveal"}).startswith("The answer is ")
    assert len(fun.RIDDLES) >= 30


def test_word_scramble_with_hints():
    out = call({"game": "scramble", "action": "start"})
    game = fun.state["scramble"]
    assert out.startswith(f"Unscramble this {len(game['word'])}-letter word:")
    assert sorted(game["mixed"]) == sorted(game["word"]) and game["mixed"] != game["word"]
    assert call({"game": "scramble", "action": "hint"}) == f"Hint: {game['clue']}."
    assert call({"game": "scramble", "action": "hint"}) == f"Hint: it starts with {game['word'][0].upper()}."
    assert call({"game": "scramble", "action": "answer", "answer": "nope"}).startswith("Not that one")
    assert call({"game": "scramble", "action": "answer", "answer": game["word"].upper()}) == \
        f"Well done, it's {game['word']}!"
    call({"game": "scramble", "action": "start"})
    assert call({"game": "scramble", "action": "reveal"}).startswith("The word was ")
    assert call({"game": "number", "action": "hint"}) == "There are no hints for that game."


def test_eight_ball_would_you_rather_quote_fact():
    assert call({"kind": "eight_ball"}, name="fun").startswith("The magic 8-ball says: ")
    assert call({"kind": "would_you_rather"}, name="fun").startswith("Would you rather ")
    quote = call({"kind": "quote"}, name="fun")
    assert any(quote == f"{t} That's {who}." for t, who in fun.QUOTES)
    assert call({"kind": "fact"}, name="fun") in fun.FACTS
    assert len(fun.WOULD_YOU_RATHER) >= 40 and len(fun.QUOTES) >= 40 and len(fun.FACTS) >= 40


def test_jokes_never_repeat_in_a_session():
    told = [call({"kind": "joke"}, name="fun") for _ in fun.JOKES]
    assert len(set(told)) == len(fun.JOKES) >= 50
    assert call({"kind": "joke"}, name="fun") in fun.JOKES  # starts over once all are told


def test_this_or_that():
    out = call({"kind": "this_or_that", "options": ["the red shirt", "the blue shirt"]}, name="fun")
    assert out.startswith(("Go with the red shirt, because ", "Go with the blue shirt, because "))
    assert call({"kind": "this_or_that"}, name="fun").startswith("Go with ")


def test_tools_registered():
    defs = {t["name"]: t for t in tools.client_tool_definitions(Settings())}
    assert {"play_game", "fun"} <= set(defs)
    assert all(defs[n]["input_schema"]["additionalProperties"] is False for n in fun.NAMES)
