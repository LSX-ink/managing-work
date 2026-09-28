"""Screen games: board games against Alfred, drawn in a pop-up and played by clicking a square or by voice.

Noughts and crosses (hard is unbeatable minimax, easy is mostly random), Connect Four (a simple heuristic that
wins, blocks and avoids handing you a win) and battleships (Alfred's fleet stays hidden here; he fires back).
Each game lives in this process only. Clicking a square sends a line like "Noughts and crosses: play in the top
left." to Alfred, who calls play_board_game with it, and the board is redrawn after every move.
"""

import re
from functools import lru_cache

import arcade
import screen
from arcade import rng
from config import Settings

screen.EXTRA_KINDS.add("arcade-grid")
state: dict = {"noughts_and_crosses": None, "connect_four": None, "battleships": None}

GAMES = {"noughts_and_crosses": "Noughts and crosses", "connect_four": "Connect Four", "battleships": "Battleships"}
SQUARES = ["top left", "top middle", "top right", "middle left", "centre", "middle right",
           "bottom left", "bottom middle", "bottom right"]
LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]
ROWS, COLS = 6, 7
SEA = 8
FLEET = [("battleship", 4), ("cruiser", 3), ("submarine", 3), ("destroyer", 2)]
LETTERS = "ABCDEFGH"


def _grid(label: str, rows: int, cols: int, cells: list, says: list | None = None, marks=(), axes=False) -> dict:
    return {"label": label, "rows": rows, "cols": cols, "cells": cells, "says": says or [], "marks": list(marks),
            "axes": axes}


def _card(game: str, style: str, grids: list[dict], status: str, over: bool) -> dict:
    buttons = [{"label": "New game", "say": f"Start a new game of {GAMES[game].lower()}."}] if over else []
    return screen.card("arcade-grid", GAMES[game], f"arcade-{game}", buttons=buttons,
                       data={"style": style, "grids": grids, "status": status})


def _finish(game: str, result: str) -> None:
    state[game]["over"] = True
    arcade.record(game, result)


# ---- Noughts and crosses -----------------------------------------------------------------------

def _winner(board) -> tuple[str, tuple]:
    for line in LINES:
        a, b, c = (board[i] for i in line)
        if a and a == b == c:
            return a, line
    return ("draw", ()) if all(board) else ("", ())


@lru_cache(maxsize=None)
def _minimax(board: tuple, turn: str) -> int:
    """Score for O (Alfred): +1 win, 0 draw, -1 loss, with best play from here."""
    who, _ = _winner(board)
    if who:
        return 0 if who == "draw" else 1 if who == "o" else -1
    scores = [_minimax(board[:i] + (turn,) + board[i + 1:], "x" if turn == "o" else "o")
              for i, v in enumerate(board) if not v]
    return max(scores) if turn == "o" else min(scores)


def _alfred_square(board: list, level: str) -> int:
    free = [i for i, v in enumerate(board) if not v]
    if level == "easy" and rng.random() < 0.7:
        return rng.choice(free)
    scored = [(_minimax(tuple(board[:i] + ["o"] + board[i + 1:]), "x"), i) for i in free]
    top = max(s for s, _ in scored)
    return rng.choice([i for s, i in scored if s == top])


def square(text: str) -> int:
    """0-8 from '5', 'top left', 'centre', 'bottom middle'..."""
    text = str(text or "").lower()
    digit = re.search(r"\b([1-9])\b", text)
    if digit:
        return int(digit.group(1)) - 1
    row = 0 if re.search(r"\b(top|upper)\b", text) else 2 if re.search(r"\b(bottom|lower)\b", text) else 1
    col = 0 if "left" in text else 2 if "right" in text else 1
    if row == 1 and col == 1 and not re.search(r"\b(middle|centre|center)\b", text):
        raise ValueError("Which square? Say something like top left, centre or bottom right.")
    return row * 3 + col


def _noughts_view(said: str) -> screen.Shown:
    g = state["noughts_and_crosses"]
    who, line = _winner(g["board"])
    says = [] if g["over"] else [f"Noughts and crosses: play in the {SQUARES[i]}." if not v else ""
                                 for i, v in enumerate(g["board"])]
    marks = line or ([g["last"]] if g["last"] is not None else [])
    status = {"x": "You win!", "o": "Alfred wins.", "draw": "It's a draw."}.get(who, "Your turn: you're X.")
    grid = _grid("", 3, 3, g["board"][:], says, marks)
    return screen.Shown(said, _card("noughts_and_crosses", "noughts", [grid], status, g["over"]))


def noughts_start(level: str) -> screen.Shown:
    state["noughts_and_crosses"] = {"board": [""] * 9, "level": "easy" if level == "easy" else "hard",
                                    "over": False, "last": None}
    return _noughts_view("New game of noughts and crosses. You're X, you go first.")


def noughts_move(move: str) -> screen.Shown:
    g = state["noughts_and_crosses"]
    if not g or g["over"]:
        g = state["noughts_and_crosses"] = {"board": [""] * 9, "level": (g or {}).get("level", "hard"),
                                            "over": False, "last": None}
    i = square(move)
    if g["board"][i]:
        raise ValueError(f"The {SQUARES[i]} is taken. Pick an empty square.")
    g["board"][i] = "x"
    who, _ = _winner(g["board"])
    if not who:
        j = _alfred_square(g["board"], g["level"])
        g["board"][j], g["last"] = "o", j
        who, _ = _winner(g["board"])
        said = f"I'll take the {SQUARES[j]}."
    else:
        said = ""
    if who:
        _finish("noughts_and_crosses", {"x": "won", "o": "lost", "draw": "drawn"}[who])
        said += {"x": " You win, well played!", "o": " That's three in a row, I win.", "draw": " It's a draw."}[who]
    return _noughts_view(said.strip())


# ---- Connect Four ------------------------------------------------------------------------------

def _drop(board: list[list[str]], col: int, who: str) -> int:
    for r in range(ROWS - 1, -1, -1):
        if not board[r][col]:
            board[r][col] = who
            return r
    return -1


def _free_cols(board) -> list[int]:
    return [c for c in range(COLS) if not board[0][c]]


def _windows():
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                cells = [(r + dr * k, c + dc * k) for k in range(4)]
                if all(0 <= y < ROWS and 0 <= x < COLS for y, x in cells):
                    yield cells


def four_in_a_row(board) -> tuple[str, list]:
    for cells in _windows():
        first = board[cells[0][0]][cells[0][1]]
        if first and all(board[y][x] == first for y, x in cells):
            return first, cells
    return "", []


def _wins_with(board, col: int, who: str) -> bool:
    trial = [row[:] for row in board]
    _drop(trial, col, who)
    return four_in_a_row(trial)[0] == who


def _heuristic(board) -> int:
    score = sum(3 for r in range(ROWS) if board[r][COLS // 2] == "alfred")
    for cells in _windows():
        vals = [board[y][x] for y, x in cells]
        mine, theirs, empty = vals.count("alfred"), vals.count("you"), vals.count("")
        if mine == 3 and empty == 1:
            score += 6
        elif mine == 2 and empty == 2:
            score += 2
        if theirs == 3 and empty == 1:
            score -= 5
    return score


def alfred_column(board) -> int:
    free = _free_cols(board)
    for who in ("alfred", "you"):  # win if he can, otherwise block
        for c in free:
            if _wins_with(board, c, who):
                return c

    def gives_away(c):
        trial = [row[:] for row in board]
        _drop(trial, c, "alfred")
        return any(_wins_with(trial, d, "you") for d in _free_cols(trial))

    choices = [c for c in free if not gives_away(c)] or free
    scored = []
    for c in choices:
        trial = [row[:] for row in board]
        _drop(trial, c, "alfred")
        scored.append((_heuristic(trial) - abs(c - COLS // 2), c))
    top = max(s for s, _ in scored)
    return rng.choice([c for s, c in scored if s == top])


def _c4_view(said: str) -> screen.Shown:
    g = state["connect_four"]
    who, line = four_in_a_row(g["board"])
    cells = [g["board"][r][c] for r in range(ROWS) for c in range(COLS)]
    free = set(_free_cols(g["board"]))
    says = [] if g["over"] else [f"Connect Four: drop in column {i % COLS + 1}." if i % COLS in free else ""
                                 for i in range(ROWS * COLS)]
    marks = [r * COLS + c for r, c in line] or ([g["last"]] if g["last"] is not None else [])
    status = ("You win!" if who == "you" else "Alfred wins." if who == "alfred" else "It's a draw." if g["over"]
              else "Your turn: click a column.")
    grid = _grid("", ROWS, COLS, cells, says, marks)
    return screen.Shown(said, _card("connect_four", "connect4", [grid], status, g["over"]))


def c4_start() -> screen.Shown:
    state["connect_four"] = {"board": [[""] * COLS for _ in range(ROWS)], "over": False, "last": None}
    return _c4_view("New game of Connect Four. You go first: pick a column from 1 to 7.")


def c4_move(move: str) -> screen.Shown:
    g = state["connect_four"]
    if not g or g["over"]:
        c4_start()
        g = state["connect_four"]
    m = re.search(r"\b([1-7])\b", str(move or ""))
    if not m:
        raise ValueError("Which column? Say a number from 1 to 7.")
    col = int(m.group(1)) - 1
    if g["board"][0][col]:
        raise ValueError(f"Column {col + 1} is full. Pick another.")
    _drop(g["board"], col, "you")
    said = ""
    if not four_in_a_row(g["board"])[0] and _free_cols(g["board"]):
        c = alfred_column(g["board"])
        g["last"] = _drop(g["board"], c, "alfred") * COLS + c
        said = f"I'll drop in column {c + 1}."
    who = four_in_a_row(g["board"])[0]
    if who or not _free_cols(g["board"]):
        _finish("connect_four", "won" if who == "you" else "lost" if who == "alfred" else "drawn")
        said += {"you": " Four in a row, you win!", "alfred": " Four in a row, I win."}.get(who, " It's a draw.")
    return _c4_view(said.strip())


# ---- Battleships -------------------------------------------------------------------------------

def _place_fleet() -> list[dict]:
    while True:
        taken, ships = set(), []
        for name, size in FLEET:
            for _ in range(200):
                across = rng.random() < 0.5
                r = rng.randrange(SEA - (0 if across else size - 1))
                c = rng.randrange(SEA - (size - 1 if across else 0))
                cells = {(r, c + k) if across else (r + k, c) for k in range(size)}
                if not cells & taken:
                    taken |= cells
                    ships.append({"name": name, "cells": cells})
                    break
        if len(ships) == len(FLEET):
            return ships


def _fire(ships: list[dict], shots: set, cell: tuple) -> tuple[str, dict | None]:
    shots.add(cell)
    for ship in ships:
        if cell in ship["cells"]:
            return ("sunk" if ship["cells"] <= shots else "hit"), ship
    return "miss", None


def _all_sunk(ships, shots) -> bool:
    return all(s["cells"] <= shots for s in ships)


def _name(cell: tuple) -> str:
    return f"{LETTERS[cell[0]]}{cell[1] + 1}"


def target(text: str) -> tuple[int, int]:
    m = re.search(r"\b([a-h])\s*-?\s*([1-8])\b", str(text or "").lower())
    if not m:
        raise ValueError("Where? Say a letter A to H and a number 1 to 8, like B7.")
    return LETTERS.lower().index(m.group(1)), int(m.group(2)) - 1


def _alfred_shot(g: dict) -> tuple[int, int]:
    """Hunt on a chequerboard; after a hit, try the squares next to unsunk hits."""
    open_hits = [c for c in g["alfred_shots"] if any(c in s["cells"] and not s["cells"] <= g["alfred_shots"]
                                                     for s in g["mine"])]
    near = [(r + dr, c + dc) for r, c in open_hits for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0))]
    near = [p for p in near if 0 <= p[0] < SEA and 0 <= p[1] < SEA and p not in g["alfred_shots"]]
    if near:
        return rng.choice(near)
    free = [(r, c) for r in range(SEA) for c in range(SEA) if (r, c) not in g["alfred_shots"]]
    return rng.choice([p for p in free if sum(p) % 2 == 0] or free)


def _sea_cells(ships, shots, show_ships: bool) -> list[str]:
    out = []
    for r in range(SEA):
        for c in range(SEA):
            ship = next((s for s in ships if (r, c) in s["cells"]), None)
            if (r, c) in shots:
                out.append(("sunk" if ship["cells"] <= shots else "hit") if ship else "miss")
            else:
                out.append("ship" if ship and show_ships else "")
    return out


def _bs_view(said: str) -> screen.Shown:
    g = state["battleships"]
    says = [] if g["over"] else [f"Battleships: fire at {_name((r, c))}." if (r, c) not in g["my_shots"] else ""
                                 for r in range(SEA) for c in range(SEA)]
    last = [g["last"][0] * SEA + g["last"][1]] if g["last"] else []
    theirs = _grid("Alfred's waters", SEA, SEA, _sea_cells(g["theirs"], g["my_shots"], g["over"]), says, axes=True)
    mine = _grid("Your fleet", SEA, SEA, _sea_cells(g["mine"], g["alfred_shots"], True), marks=last, axes=True)
    left = sum(1 for s in g["theirs"] if not s["cells"] <= g["my_shots"])
    status = said if g["over"] else f"Alfred has {left} ship{'s' if left != 1 else ''} left. Click a square to fire."
    return screen.Shown(said, _card("battleships", "battleships", [theirs, mine], status, g["over"]))


def bs_start() -> screen.Shown:
    state["battleships"] = {"theirs": _place_fleet(), "mine": _place_fleet(), "my_shots": set(),
                            "alfred_shots": set(), "over": False, "last": None}
    return _bs_view("Battleships: our fleets are hidden. Fire first by clicking a square or saying one, like C4.")


def bs_fire(move: str) -> screen.Shown:
    g = state["battleships"]
    if not g or g["over"]:
        raise ValueError("There's no battleships game going. Say 'let's play battleships' to start.")
    cell = target(move)
    if cell in g["my_shots"]:
        raise ValueError(f"You've already fired at {_name(cell)}.")
    hit, ship = _fire(g["theirs"], g["my_shots"], cell)
    said = {"miss": f"{_name(cell)}: miss.", "hit": f"{_name(cell)}: hit!",
            "sunk": f"{_name(cell)}: you sunk my {ship['name'] if ship else ''}!"}[hit]
    if _all_sunk(g["theirs"], g["my_shots"]):
        _finish("battleships", "won")
        return _bs_view(said + " That's my whole fleet. You win!")
    shot = _alfred_shot(g)
    g["last"] = shot
    back, ship = _fire(g["mine"], g["alfred_shots"], shot)
    said += {"miss": f" I fire at {_name(shot)}, and miss.", "hit": f" I fire at {_name(shot)}: a hit!",
             "sunk": f" I fire at {_name(shot)} and sink your {ship['name'] if ship else ''}."}[back]
    if _all_sunk(g["mine"], g["alfred_shots"]):
        _finish("battleships", "lost")
        said += " That's your whole fleet. I win."
    return _bs_view(said)


# ---- The tool ----------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "play_board_game",
        "description": "Board games against Alfred in a pop-up on the screen, played by clicking or by voice. "
                       "game: 'noughts_and_crosses' (tic-tac-toe; hard is unbeatable, or easy), 'connect_four', "
                       "'battleships'. action: 'start' a new game, 'move' with the user's move (noughts: a square "
                       "like 'top left', 'centre' or 1-9; connect four: column 1-7; battleships: a target like "
                       "'B7'), 'show' the board again, 'quit'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game": {"type": "string", "enum": list(GAMES)},
                "action": {"type": "string", "enum": ["start", "move", "show", "quit"]},
                "move": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["easy", "hard"]},
            },
            "required": ["game", "action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"play_board_game"}
STARTS = {"noughts_and_crosses": lambda a: noughts_start(a.get("difficulty") or ""),
          "connect_four": lambda a: c4_start(), "battleships": lambda a: bs_start()}
MOVES = {"noughts_and_crosses": noughts_move, "connect_four": c4_move, "battleships": bs_fire}
VIEWS = {"noughts_and_crosses": _noughts_view, "connect_four": _c4_view, "battleships": _bs_view}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    game, action = args.get("game") or "", args.get("action") or "start"
    if game not in GAMES:
        raise ValueError("Which game? Noughts and crosses, Connect Four or battleships.")
    if action == "start":
        return STARTS[game](args)
    if action == "quit":
        state[game] = None
        return screen.Shown(f"Stopped {GAMES[game].lower()}.", {"kind": "close", "all": False, "title": GAMES[game]})
    if action == "show":
        if not state[game]:
            return STARTS[game](args)
        return VIEWS[game](f"Here's the {GAMES[game].lower()} board.")
    return MOVES[game](args.get("move") or "")
