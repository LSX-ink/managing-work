"""Screen games: games played in pop-ups on the Alfred screen, by clicking or by voice, and this session's scores.

This module holds the scores every screen game shares, plus the games that run inside their own pop-up (sudoku,
memory pairs, minesweeper, snake, 2048 and a maths sprint). Those games tell Alfred how they went with a say line,
which comes back here as a 'result'. Games against Alfred live in arcade_board, arcade_words and arcade_cards.
Everything lives in this process only and resets when Alfred restarts.
"""

import random
import time

import screen
from config import Settings

rng = random.Random()
state: dict = {"scores": {}, "sudoku": None}
screen.EXTRA_KINDS.update({"arcade-sudoku", "arcade-memory", "arcade-mines", "arcade-snake", "arcade-2048",
                           "arcade-sprint"})

TITLES = {
    "noughts_and_crosses": "Noughts and crosses", "connect_four": "Connect Four", "battleships": "Battleships",
    "hangman": "Hangman", "wordle": "Wordle", "capitals": "Capitals quiz", "flags": "Flags quiz",
    "higher_or_lower": "Higher or lower", "blackjack": "Blackjack", "bingo": "Bingo", "sudoku": "Sudoku",
    "memory": "Memory pairs", "minesweeper": "Minesweeper", "snake": "Snake", "2048": "2048",
    "maths_sprint": "Maths sprint",
}
# Games where a smaller score is better (moves, seconds or minutes taken).
LOWER_IS_BETTER = {"memory", "minesweeper", "sudoku"}
SCREEN_GAMES = ["sudoku", "memory", "minesweeper", "snake", "2048", "maths_sprint"]
SUDOKU_GIVENS = {"easy": 38, "medium": 30}
MEMORY_PAIRS = {"easy": 6, "medium": 8, "hard": 10}


# ---- Scores ------------------------------------------------------------------------------------

def record(game: str, result: str | None = None, score: float | None = None) -> dict:
    """Count one finished game: result 'won', 'lost' or 'drawn' (or None), and a score if it has one."""
    tally = state["scores"].setdefault(game, {"played": 0, "won": 0, "lost": 0, "drawn": 0, "best": None})
    tally["played"] += 1
    if result in ("won", "lost", "drawn"):
        tally[result] += 1
    if score is not None:
        better = min if game in LOWER_IS_BETTER else max
        tally["best"] = score if tally["best"] is None else better(tally["best"], score)
    return tally


def _num(value) -> str:
    return "" if value is None else f"{value:g}" if isinstance(value, float) else str(value)


def scores() -> screen.Shown:
    rows = [[TITLES.get(g, g), t["played"], t["won"], t["lost"], t["drawn"], _num(t["best"])]
            for g, t in state["scores"].items()]
    said = (f"Here are the scores for {len(rows)} game{'s' if len(rows) != 1 else ''} this session."
            if rows else "No screen games played yet this session.")
    return screen.Shown(said, screen.card("table", "Game scores", "arcade-scores",
                                          columns=["Game", "Played", "Won", "Lost", "Drawn", "Best"], rows=rows))


def result(game: str, won: bool | None, score) -> str:
    if game not in TITLES:
        raise ValueError("Which game was that?")
    score = None if score is None else float(score)
    if score is not None and score.is_integer():
        score = int(score)
    before = (state["scores"].get(game) or {}).get("best")
    tally = record(game, None if won is None else "won" if won else "lost", score)
    name = TITLES[game]
    if score is None:
        return f"{'Well played' if won else 'Unlucky'} at {name}. That's {tally['won']} won this session."
    if before is None or tally["best"] != before:
        return f"{_num(score)} at {name}: your best this session."
    return f"{_num(score)} at {name}. Your best this session is {_num(tally['best'])}."


# ---- Sudoku ------------------------------------------------------------------------------------

def _candidates(grid: list[int], i: int) -> set[int]:
    r, c = divmod(i, 9)
    br, bc = r // 3 * 3, c // 3 * 3
    used = {grid[r * 9 + k] for k in range(9)} | {grid[k * 9 + c] for k in range(9)}
    used |= {grid[(br + a) * 9 + bc + b] for a in range(3) for b in range(3)}
    return set(range(1, 10)) - used


def _solve(grid: list[int], limit: int = 2, shuffle: bool = False) -> int:
    """Count solutions up to limit, filling grid in place; with limit 1 the grid is left solved."""
    best, options = -1, None
    for i, v in enumerate(grid):
        if not v:
            here = _candidates(grid, i)
            if options is None or len(here) < len(options):
                best, options = i, here
                if len(here) <= 1:
                    break
    if best < 0:
        return 1
    options = sorted(options)
    if shuffle:
        rng.shuffle(options)
    found = 0
    for v in options:
        grid[best] = v
        found += _solve(grid, limit - found, shuffle)
        if found >= limit:
            return found
    grid[best] = 0
    return found


def _count(grid: list[int]) -> int:
    return _solve(grid[:], 2)


def sudoku_puzzle(difficulty: str) -> tuple[list[int], list[int]]:
    """(puzzle with 0 for blanks, solution): a random full grid with squares taken away while it stays unique."""
    solution = [0] * 81
    _solve(solution, 1, shuffle=True)
    puzzle = solution[:]
    target = SUDOKU_GIVENS.get(difficulty, SUDOKU_GIVENS["easy"])
    cells = list(range(81))
    rng.shuffle(cells)
    for i in cells:
        if sum(1 for v in puzzle if v) <= target:
            break
        keep, puzzle[i] = puzzle[i], 0
        if _count(puzzle) != 1:
            puzzle[i] = keep
    return puzzle, solution


def _sudoku_card() -> dict:
    s = state["sudoku"]
    data = {k: s[k] for k in ("id", "givens", "solution", "hints", "difficulty")}
    return screen.card("arcade-sudoku", f"Sudoku ({s['difficulty']})", "arcade-sudoku", data=data)


def sudoku_hint() -> screen.Shown:
    s = state["sudoku"]
    if not s:
        raise ValueError("There's no sudoku going. Say 'give me a sudoku' to start one.")
    left = [i for i, v in enumerate(s["givens"]) if not v and i not in s["hints"]]
    if not left:
        return screen.Shown("Every square is already showing.", _sudoku_card())
    i = rng.choice(left)
    s["hints"].append(i)
    r, c = divmod(i, 9)
    return screen.Shown(f"Row {r + 1}, column {c + 1} is a {s['solution'][i]}.", _sudoku_card())


# ---- Opening the games -------------------------------------------------------------------------

def open_game(game: str, difficulty: str) -> screen.Shown:
    level = difficulty or ("easy" if game in ("sudoku", "maths_sprint") else "medium")
    if game == "sudoku":
        level = level if level in SUDOKU_GIVENS else "medium"
        puzzle, solution = sudoku_puzzle(level)
        state["sudoku"] = {"id": f"sudoku-{int(time.time() * 1000)}", "givens": puzzle, "solution": solution,
                           "hints": [], "difficulty": level}
        return screen.Shown(f"Here's {'an easy' if level == 'easy' else 'a medium'} sudoku. Type digits into the "
                            "squares and press Check.", _sudoku_card())
    if game == "memory":
        pairs = MEMORY_PAIRS.get(level, 8)
        layout = [n for n in range(pairs) for _ in (0, 1)]
        rng.shuffle(layout)
        return screen.Shown("Memory pairs is on the screen. Turn two cards over at a time.",
                            screen.card("arcade-memory", "Memory pairs", "arcade-memory", data={"layout": layout}))
    if game == "minesweeper":
        return screen.Shown("Minesweeper is on the screen. Right-click or use flag mode to mark mines.",
                            screen.card("arcade-mines", "Minesweeper", "arcade-mines",
                                        data={"size": 9, "mines": 10, "seed": rng.randrange(1 << 30)}))
    if game == "snake":
        speed = {"easy": 170, "medium": 130, "hard": 90}.get(level, 130)
        return screen.Shown("Snake is on the screen. Use the arrow keys; it pauses when you look away.",
                            screen.card("arcade-snake", "Snake", "arcade-snake", data={"size": 18, "speed": speed}))
    if game == "2048":
        return screen.Shown("2048 is on the screen. Slide the tiles with the arrow keys.",
                            screen.card("arcade-2048", "2048", "arcade-2048", data={"size": 4}))
    if game == "maths_sprint":
        level = "hard" if level == "hard" else "easy"
        return screen.Shown("The maths sprint is ready: sixty seconds, as many as you can. Press Start.",
                            screen.card("arcade-sprint", "Maths sprint", "arcade-sprint",
                                        data={"seconds": 60, "level": level}))
    raise ValueError("Which game? Sudoku, memory, minesweeper, snake, 2048 or the maths sprint.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "screen_game",
        "description": "Games that play inside a pop-up on the Alfred screen with mouse and keys. game: 'sudoku' "
                       "(easy or medium), 'memory' (pairs matching cards), 'minesweeper', 'snake', '2048', "
                       "'maths_sprint' (60-second mental arithmetic). action: 'open' to play; 'hint' gives a "
                       "sudoku hint; 'result' records a finished game when the pop-up reports it (e.g. 'I scored "
                       "42 at snake', 'I finished the memory game in 20 moves'; any screen game); 'scores' shows "
                       "the scores table for every game played this session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["open", "hint", "result", "scores"]},
                "game": {"type": "string", "enum": list(TITLES)},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "won": {"type": "boolean", "description": "result: won or lost, when the game has one."},
                "score": {"type": "number", "description": "result: points, moves, seconds or minutes."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"screen_game"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "scores":
        return scores()
    if action == "hint":
        return sudoku_hint()
    if action == "result":
        return result(args.get("game") or "", args.get("won"), args.get("score"))
    return open_game(args.get("game") or "", args.get("difficulty") or "")
