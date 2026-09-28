import asyncio

import httpx
import pytest

import arcade
import arcade_board
import arcade_cards
import arcade_words
import screen
import tools
from arcade_lists import ANSWERS, COUNTRIES, EXTRA, HANGMAN
from config import Settings


@pytest.fixture(autouse=True)
def fresh_games():
    arcade.state.update({"scores": {}, "sudoku": None})
    for module in (arcade_board, arcade_words, arcade_cards):
        for key in module.state:
            module.state[key] = None
    arcade.rng.seed(3)
    yield


def call(name, **args):
    def refuse(request):
        raise AssertionError(f"Unexpected request to {request.url}")

    popped = []

    async def page(message):
        popped.append(message["card"])

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(refuse)) as http:
            return await tools.run_tool(name, args, Settings(), http, page)

    text = asyncio.run(go())
    return screen.Shown(text, popped[-1]) if popped else text


def board(**args):
    return call("play_board_game", **args)


def words(**args):
    return call("play_word_game", **args)


def cards(**args):
    return call("play_card_game", **args)


def screen_game(**args):
    return call("screen_game", **args)


# ---- Registration and word lists --------------------------------------------------------------

def test_registered_and_deferred():
    defs = {t["name"]: t for t in tools.client_tool_definitions(Settings())}
    for name in ("screen_game", "play_board_game", "play_word_game", "play_card_game"):
        assert defs[name]["defer_loading"] and defs[name]["input_schema"]["additionalProperties"] is False


def test_word_lists_are_clean():
    assert len(ANSWERS) >= 300 and all(len(w) == 5 and w.isalpha() and w.islower() for w in ANSWERS + EXTRA)
    assert len(set(ANSWERS)) == len(ANSWERS) and not set(ANSWERS) & set(EXTRA)
    assert all(w.isalpha() and w.islower() for w in HANGMAN)
    assert len(COUNTRIES) >= 100 and len({c[2] for c in COUNTRIES}) == len(COUNTRIES)


# ---- Noughts and crosses ----------------------------------------------------------------------

def test_noughts_squares():
    assert arcade_board.square("top left") == 0 and arcade_board.square("centre") == 4
    assert arcade_board.square("bottom right") == 8 and arcade_board.square("middle left") == 3
    assert arcade_board.square("square 6") == 5 and arcade_board.square("top") == 1
    with pytest.raises(ValueError):
        arcade_board.square("somewhere")


def test_noughts_hard_never_loses():
    out = board(game="noughts_and_crosses", action="start")
    assert out.card["kind"] == "arcade-grid" and out.card["data"]["style"] == "noughts"
    assert out.card["data"]["grids"][0]["says"][0] == "Noughts and crosses: play in the top left."
    for _ in range(5):
        g = arcade_board.state["noughts_and_crosses"]
        if g["over"]:
            break
        free = [i for i, v in enumerate(g["board"]) if not v]
        out = board(game="noughts_and_crosses", action="move", move=str(free[0] + 1))
    assert arcade_board.state["noughts_and_crosses"]["over"]
    tally = arcade.state["scores"]["noughts_and_crosses"]
    assert tally["won"] == 0 and tally["played"] == 1
    assert out.card["buttons"][0]["label"] == "New game" and out.card["data"]["grids"][0]["says"] == []


def test_noughts_taken_square_and_easy_mode():
    board(game="noughts_and_crosses", action="start", difficulty="easy")
    assert arcade_board.state["noughts_and_crosses"]["level"] == "easy"
    board(game="noughts_and_crosses", action="move", move="centre")
    with pytest.raises(ValueError, match="taken"):
        board(game="noughts_and_crosses", action="move", move="centre")
    assert "board" in board(game="noughts_and_crosses", action="show")
    quit_ = board(game="noughts_and_crosses", action="quit")
    assert quit_.card["kind"] == "close" and arcade_board.state["noughts_and_crosses"] is None


# ---- Connect Four -----------------------------------------------------------------------------

def test_connect_four_blocks_and_wins():
    b = [[""] * 7 for _ in range(6)]
    for c in range(3):
        b[5][c] = "you"
    assert arcade_board.alfred_column(b) == 3  # blocks
    for c in range(3):
        b[4][c] = "alfred"
    assert arcade_board.alfred_column(b) == 3  # wins first
    assert arcade_board.four_in_a_row([["alfred"] * 4 + [""] * 3] + [[""] * 7] * 5)[0] == "alfred"


def test_connect_four_game():
    out = board(game="connect_four", action="start")
    assert out.card["data"]["grids"][0]["rows"] == 6 and len(out.card["data"]["grids"][0]["cells"]) == 42
    out = board(game="connect_four", action="move", move="Connect Four: drop in column 4.")
    cells = out.card["data"]["grids"][0]["cells"]
    assert cells.count("you") == 1 and cells.count("alfred") == 1 and cells[38] == "you"
    with pytest.raises(ValueError):
        board(game="connect_four", action="move", move="column nine")
    for _ in range(30):
        g = arcade_board.state["connect_four"]
        if g["over"]:
            break
        free = [c for c in range(7) if not g["board"][0][c]]
        board(game="connect_four", action="move", move=str(free[0] + 1))
    assert arcade_board.state["connect_four"]["over"] and arcade.state["scores"]["connect_four"]["played"] == 1


# ---- Battleships ------------------------------------------------------------------------------

def test_battleships_fire_and_hidden_fleet():
    out = board(game="battleships", action="start")
    theirs, mine = out.card["data"]["grids"]
    assert "ship" not in theirs["cells"] and mine["cells"].count("ship") == 12
    assert theirs["says"][9] == "Battleships: fire at B2."
    assert arcade_board.target("fire at c5") == (2, 4)
    out = board(game="battleships", action="move", move="A1")
    assert out.startswith("A1:") and "I fire at" in out
    theirs = out.card["data"]["grids"][0]
    assert theirs["cells"][0] in ("hit", "miss", "sunk") and theirs["says"][0] == ""
    with pytest.raises(ValueError, match="already"):
        board(game="battleships", action="move", move="a1")


def test_battleships_win():
    board(game="battleships", action="start")
    g = arcade_board.state["battleships"]
    targets = sorted(c for ship in g["theirs"] for c in ship["cells"])
    for r, c in targets:
        out = board(game="battleships", action="move", move=f"{'ABCDEFGH'[r]}{c + 1}")
    assert "You win" in out and g["over"] and out.card["buttons"][0]["label"] == "New game"
    assert arcade.state["scores"]["battleships"]["won"] == 1


# ---- Hangman ----------------------------------------------------------------------------------

def test_hangman_guesses_and_hint():
    out = words(game="hangman", action="start")
    word = arcade_words.state["hangman"]["word"]
    assert out.card["kind"] == "arcade-hangman" and out.card["data"]["pattern"].count("_") == len(word)
    wrong = next(ch for ch in "zqxjkvwy" if ch not in word)
    out = words(game="hangman", action="guess", guess=f"the letter {wrong}")
    assert out.card["data"]["misses"] == 1 and out.card["data"]["wrong"] == [wrong.upper()]
    out = words(game="hangman", action="guess", guess=word[0])
    assert out.startswith("Yes") and word[0].upper() in out.card["data"]["pattern"]
    out = words(game="hangman", action="hint")
    assert out.startswith("Here's a letter") or "You got it" in out
    out = words(game="hangman", action="guess", guess=f"is it {word}")
    assert "You got it" in out and out.card["data"]["won"] and arcade.state["scores"]["hangman"]["won"] == 1


def test_hangman_lose_and_give_up():
    words(game="hangman", action="start")
    word = arcade_words.state["hangman"]["word"]
    for ch in [c for c in "zqxjkvwybfgh" if c not in word][:6]:
        out = words(game="hangman", action="guess", guess=ch)
    assert "The word was" in out and out.card["data"]["over"] and out.card["data"]["misses"] == 6
    with pytest.raises(ValueError):
        words(game="hangman", action="guess", guess="a")
    words(game="hangman", action="start")
    assert "The word was" in words(game="hangman", action="give_up")
    assert arcade.state["scores"]["hangman"]["lost"] == 2


# ---- Wordle -----------------------------------------------------------------------------------

def test_wordle_marks():
    assert arcade_words.marks("crane", "crane") == "ggggg"
    assert arcade_words.marks("speed", "abide") == "..y.y"
    assert arcade_words.marks("eerie", "there") == "y.y.g"


def test_wordle_game():
    out = words(game="wordle", action="start")
    answer = arcade_words.state["wordle"]["answer"]
    assert out.card["kind"] == "arcade-wordle" and out.card["data"]["rows"] == []
    assert "don't know" in words(game="wordle", action="guess", guess="zzzzz")
    guess = next(w for w in ANSWERS if w != answer)
    out = words(game="wordle", action="guess", guess=guess)
    assert out.card["data"]["rows"][0]["word"] == guess.upper() and "guess" in out
    assert "letter" in words(game="wordle", action="hint")
    out = words(game="wordle", action="guess", guess=f"Wordle guess: {answer.upper()}.")
    assert "right, in 2 guesses" in out and out.card["data"]["answer"] == answer.upper()
    assert arcade.state["scores"]["wordle"]["best"] == 2
    words(game="wordle", action="start")
    assert "The word was" in words(game="wordle", action="give_up")


# ---- Quizzes ----------------------------------------------------------------------------------

def test_capitals_quiz():
    out = words(game="capitals", action="start")
    q = arcade_words.state["capitals"]
    assert out.card["kind"] == "text" and len(out.card["buttons"]) == 4
    assert q["answer"] in [b["label"] for b in out.card["buttons"]]
    assert out.card["buttons"][0]["say"].startswith("Capitals quiz: my answer is")
    out = words(game="capitals", action="guess", guess=f"Capitals quiz: my answer is {q['answer']}.")
    assert out.startswith("Right!") and q["score"] == 1
    letter = "abcd"[[o for o in q["options"]].index(q["answer"])]
    assert words(game="capitals", action="guess", guess=f"it's {letter}").startswith("Right!")
    assert "Pick one of" in words(game="capitals", action="guess", guess="Atlantis")
    for _ in range(8):
        out = words(game="capitals", action="give_up")
    assert "2 out of 10" in out and arcade.state["scores"]["capitals"]["best"] == 2
    assert out.card["buttons"][0]["label"] == "Play again"


def test_flags_quiz():
    out = words(game="flags", action="start")
    q = arcade_words.state["flags"]
    assert out.card["kind"] == "image" and out.card["src"] == f"https://flagcdn.com/w320/{q['country'][2]}.png"
    wrong = next(o for o in q["options"] if o != q["answer"])
    out = words(game="flags", action="guess", guess=wrong)
    assert out.startswith("Not quite") and q["score"] == 0 and q["i"] == 1
    assert "flag" in words(game="flags", action="show")


# ---- Cards ------------------------------------------------------------------------------------

def test_higher_or_lower():
    out = cards(game="higher_or_lower", action="start")
    assert out.card["kind"] == "arcade-cards" and [b["label"] for b in out.card["buttons"]] == ["Higher", "Lower"]
    for _ in range(60):
        g = arcade_cards.state["higher_or_lower"]
        if g["over"]:
            break
        rank = arcade_cards.RANKS.index(g["current"][:-1])
        out = cards(game="higher_or_lower", action="higher" if rank < 6 else "lower")
    assert "game over" in out and arcade.state["scores"]["higher_or_lower"]["played"] == 1
    assert len(out.card["data"]["hands"]) == 2


def test_blackjack():
    assert arcade_cards.total(["AS", "KD"]) == 21 and arcade_cards.total(["AS", "AD", "9C"]) == 21
    assert arcade_cards.total(["10H", "9S", "5C"]) == 24
    for _ in range(20):
        out = cards(game="blackjack", action="start")
        if not arcade_cards.state["blackjack"]["over"]:
            break
    assert out.card["data"]["hands"][0]["cards"][1] == "??" and out.card["buttons"][0]["label"] == "Hit"
    out = cards(game="blackjack", action="stand")
    assert arcade_cards.state["blackjack"]["over"] and "??" not in out.card["data"]["hands"][0]["cards"]
    assert out.card["buttons"][0]["label"] == "Deal again"
    cards(game="blackjack", action="start")
    while not arcade_cards.state["blackjack"]["over"]:
        out = cards(game="blackjack", action="hit")
    assert sum(arcade.state["scores"]["blackjack"][k] for k in ("won", "lost", "drawn")) >= 2


def test_bingo():
    out = cards(game="bingo", action="start")
    assert out.card["kind"] == "arcade-bingo" and out.card["data"]["called"] == []
    out = cards(game="bingo", action="next")
    n = out.card["data"]["last"]
    assert 1 <= n <= 90 and str(n) in out
    for _ in range(89):
        cards(game="bingo", action="next")
    out = cards(game="bingo", action="next")
    assert "all 90" in out and sorted(out.card["data"]["called"]) == list(range(1, 91))
    with pytest.raises(ValueError):
        cards(game="bingo", action="hit")


# ---- Games in the pop-up, results and scores --------------------------------------------------

def test_sudoku_is_unique_and_hints():
    puzzle, solution = arcade.sudoku_puzzle("medium")
    assert sum(1 for v in puzzle if v) == 30 and arcade._count(puzzle) == 1
    assert all(p in (0, s) for p, s in zip(puzzle, solution))
    for k in range(9):
        assert sorted(solution[k * 9:k * 9 + 9]) == list(range(1, 10))
        assert sorted(solution[k::9]) == list(range(1, 10))
    with pytest.raises(ValueError):
        screen_game(action="hint")
    out = screen_game(action="open", game="sudoku", difficulty="easy")
    assert out.card["kind"] == "arcade-sudoku" and sum(1 for v in out.card["data"]["givens"] if v) == 38
    out = screen_game(action="hint")
    i = out.card["data"]["hints"][0]
    assert f"is a {out.card['data']['solution'][i]}" in out


def test_client_side_games_open():
    kinds = {"memory": "arcade-memory", "minesweeper": "arcade-mines", "snake": "arcade-snake",
             "2048": "arcade-2048", "maths_sprint": "arcade-sprint"}
    for game, kind in kinds.items():
        out = screen_game(action="open", game=game)
        assert out.card["kind"] == kind and "data" in out.card
    layout = screen_game(action="open", game="memory", difficulty="hard").card["data"]["layout"]
    assert sorted(layout) == sorted(list(range(10)) * 2)
    assert screen_game(action="open", game="maths_sprint").card["data"]["seconds"] == 60
    with pytest.raises(ValueError):
        screen_game(action="open", game="tetris")


def test_results_and_scores_table():
    assert screen_game(action="scores").startswith("No screen games")
    assert "best this session" in screen_game(action="result", game="snake", score=12)
    assert "Your best this session is 12" in screen_game(action="result", game="snake", score=5)
    assert "best this session" in screen_game(action="result", game="memory", won=True, score=20)
    assert "best this session" in screen_game(action="result", game="memory", won=True, score=16)
    assert "Unlucky" in screen_game(action="result", game="minesweeper", won=False)
    out = screen_game(action="scores")
    rows = {r[0]: r for r in out.card["rows"]}
    assert out.card["kind"] == "table" and rows["Snake"] == ["Snake", "2", "0", "0", "0", "12"]
    assert rows["Memory pairs"][5] == "16" and rows["Minesweeper"][3] == "1"
