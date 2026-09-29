"""Party host: draws and timers. A Secret Santa draw done here on the PC (nobody draws themselves, couples can be
kept apart, and each name is shown to one person at a time), a random team splitter, a musical-chairs stop timer,
bingo tickets and UK bingo calls, who-goes-first and a round timer.

The Secret Santa draw is kept in .partyhost-santa.json in the memory folder; who drew whom is never spoken aloud.
"""

import random
import time

import homestore as hs
import screen
from arcade_cards import BINGO_CALLS
from config import Settings

screen.EXTRA_KINDS.update({"partyhost-santa", "partyhost-teams", "partyhost-stop", "partyhost-bingo"})

SANTA = ".partyhost-santa.json"
RNG = random.Random()
COLOURS = ["Red", "Blue", "Green", "Yellow", "Orange", "Purple", "Pink", "Teal", "Grey", "Brown"]
ACTIONS = ("santa_draw", "santa_next", "santa_status", "santa_clear", "team_split", "musical_stop", "bingo_card",
           "bingo_calls", "who_goes_first", "round_timer")


def _names(values, low: int, high: int, what: str = "people") -> list[str]:
    out: list[str] = []
    for value in values or []:
        name = hs.clean(value, 30)
        if name and name.lower() not in [n.lower() for n in out]:
            out.append(name)
    if not low <= len(out) <= high:
        raise ValueError(f"I need {low} to {high} {what}; I have {len(out)}.")
    return out


# ---- Secret Santa ----------------------------------------------------------------------------

def _derange(names: list[str], banned: set[tuple[str, str]]) -> dict[str, str]:
    """A random assignment where nobody draws themselves or a banned name (backtracking), or ValueError."""
    order = names[:]
    RNG.shuffle(order)

    def place(i: int, free: list[str], out: dict) -> bool:
        if i == len(order):
            return True
        giver = order[i]
        options = [r for r in free if r != giver and (giver, r) not in banned]
        RNG.shuffle(options)
        for r in options:
            out[giver] = r
            if place(i + 1, [x for x in free if x != r], out):
                return True
        out.pop(giver, None)
        return False

    out: dict[str, str] = {}
    if not place(0, names[:], out):
        raise ValueError("Those exclusions leave no way to draw. Try fewer of them.")
    return out


def santa_draw(settings: Settings, a: dict) -> screen.Shown:
    old = hs.load(settings, SANTA, {})
    if old.get("pairs") and not a.get("confirmed"):
        raise ValueError("A Secret Santa draw already exists. Ask the user whether to throw it away and draw again, "
                         "and set confirmed to true only if they say yes.")
    names = _names(a.get("names"), 3, 40)
    lookup = {n.lower(): n for n in names}
    banned: set[tuple[str, str]] = set()
    for pair in a.get("exclusions") or []:
        if len(pair) != 2 or any(str(p).strip().lower() not in lookup for p in pair):
            raise ValueError("Each exclusion needs two names from the list, like Mum and Dad.")
        x, y = (lookup[str(p).strip().lower()] for p in pair)
        banned |= {(x, y), (y, x)}
    pairs = _derange(names, banned)
    hs.save(settings, SANTA, {"names": names, "pairs": pairs, "seen": [], "budget": hs.clean(a.get("budget"), 20)})
    return screen.Shown(f"The Secret Santa draw is done for {len(names)} people. Nobody has seen a name yet. "
                        "Say 'next person' and pass the screen to each one in turn.", screen.card(
        "text", "Secret Santa", "partyhost-santa", text=f"The draw is done for {len(names)} people:\n"
        + "\n".join(names) + "\n\nEveryone takes a turn to see who they've got.",
        buttons=[{"label": "First person", "say": "Secret Santa: next person."}]))


def _santa(settings: Settings) -> dict:
    found = hs.load(settings, SANTA, {})
    if not found.get("pairs"):
        raise ValueError("There's no Secret Santa draw yet. Give me the names and I'll draw.")
    return found


def santa_next(settings: Settings, a: dict) -> screen.Shown:
    game = _santa(settings)
    if a.get("name"):
        giver = hs.find(game["names"], hs.clean(a["name"]))
        if not giver:
            raise ValueError(f"I don't have {hs.clean(a['name'])} in the draw.")
    else:
        left = [n for n in game["names"] if n not in game["seen"]]
        if not left:
            return screen.Shown("Everybody has seen who they've got. Happy Secret Santa!", screen.card(
                "text", "Secret Santa", "partyhost-santa", text="Everyone has seen their name. Keep it secret!"))
        giver = left[0]
    if giver not in game["seen"]:
        game["seen"].append(giver)
        hs.save(settings, SANTA, game)
    data = {"giver": giver, "recipient": game["pairs"][giver], "budget": game.get("budget", ""),
            "step": len(game["seen"]), "total": len(game["names"])}
    return screen.Shown(f"Pass the screen to {giver}. Everyone else look away.",
                        screen.card("partyhost-santa", "Secret Santa", "partyhost-santa", data=data))


def santa_status(settings: Settings) -> screen.Shown:
    game = _santa(settings)
    rows = [[n, "seen" if n in game["seen"] else "not yet"] for n in game["names"]]
    left = len(game["names"]) - len(game["seen"])
    said = "Everyone has seen their name." if not left else f"{left} still to see who they've got."
    return screen.Shown(said, screen.card("table", "Secret Santa progress", columns=["Person", "Their name"], rows=rows))


def santa_clear(settings: Settings, a: dict) -> str:
    if not hs.load(settings, SANTA, {}).get("pairs"):
        return "There's no Secret Santa draw to clear."
    if not a.get("confirmed"):
        raise ValueError("This throws the draw away for good. Ask the user first, and set confirmed to true only if "
                         "they say yes.")
    hs.save(settings, SANTA, {})
    return "The Secret Santa draw is cleared."


# ---- Teams, stops, tickets ---------------------------------------------------------------------

def team_split(a: dict) -> screen.Shown:
    names = _names(a.get("names"), 2, 60)
    count = int(a.get("teams") or 0)
    size = int(a.get("team_size") or 0)
    if not count and size:
        count = max(2, round(len(names) / size))
    count = count or 2
    if not 2 <= count <= len(COLOURS) or count > len(names):
        raise ValueError(f"I can make 2 to {min(len(COLOURS), len(names))} teams from {len(names)} people.")
    RNG.shuffle(names)
    groups = [names[i::count] for i in range(count)]
    teams = [{"name": f"{COLOURS[i]} team", "members": g, "captain": g[0] if a.get("captains") else ""}
             for i, g in enumerate(groups)]
    sizes = ", ".join(str(len(g)) for g in groups)
    return screen.Shown(f"{count} teams made, of {sizes}.", screen.card(
        "partyhost-teams", "Teams", "partyhost-teams", data={"teams": teams},
        buttons=[{"label": "Shuffle again", "say": "Split us into teams again."}]))


def musical_stop(a: dict) -> screen.Shown:
    low = min(300, max(3, int(a.get("min_seconds") or 8)))
    high = min(600, max(low + 1, int(a.get("max_seconds") or 30)))
    return screen.Shown("Music time. Press start and stop dancing when I say stop.", screen.card(
        "partyhost-stop", "Musical stop", "partyhost-stop", data={"min": low, "max": high}))


def _ticket() -> list[list[int | None]]:
    """A UK 90-ball ticket: 3 rows of 9 columns, five numbers a row, one to three a column."""
    while True:
        counts = [RNG.randint(1, 3) for _ in range(9)]
        if sum(counts) != 15:
            continue
        cols = [RNG.sample(range(0, 3), n) for n in counts]
        rows = [sum(1 for c in cols if r in c) for r in range(3)]
        if rows == [5, 5, 5]:
            break
    grid: list[list[int | None]] = [[None] * 9 for _ in range(3)]
    for c, rows_in in enumerate(cols):
        low, high = (1, 9) if c == 0 else (c * 10, c * 10 + 9) if c < 8 else (80, 90)
        nums = sorted(RNG.sample(range(low, high + 1), len(rows_in)))
        for r, n in zip(sorted(rows_in), nums):
            grid[r][c] = n
    return grid


def bingo_card(a: dict) -> screen.Shown:
    count = min(6, max(1, int(a.get("count") or 1)))
    tickets = [_ticket() for _ in range(count)]
    return screen.Shown(f"Here {'is a bingo ticket' if count == 1 else f'are {count} bingo tickets'}. "
                        "Tap a number to mark it off.", screen.card(
        "partyhost-bingo", "Bingo ticket" if count == 1 else "Bingo tickets", "partyhost-bingo",
        data={"tickets": tickets}, buttons=[{"label": "New tickets", "say": "Give me new bingo tickets."}]))


def bingo_calls(a: dict) -> screen.Shown | str:
    number = a.get("number")
    if number is not None:
        n = int(number)
        if not 1 <= n <= 90:
            raise ValueError("Bingo numbers run from 1 to 90.")
        call = BINGO_CALLS.get(n)
        return f"{n} is '{call}'." if call else f"{n} has no special call. You'd say '{' and '.join(str(n))}, {n}'."
    rows = [[n, call] for n, call in sorted(BINGO_CALLS.items())]
    return screen.Shown("Here are the traditional bingo calls.", screen.card(
        "table", "Bingo calls", columns=["Number", "Call"], rows=rows))


def who_goes_first(a: dict) -> screen.Shown:
    names = _names(a.get("names"), 2, 40)
    RNG.shuffle(names)
    items = [{"label": f"{i + 1}. {n}"} for i, n in enumerate(names)]
    return screen.Shown(f"{names[0]} goes first, then {names[1]}.", screen.card(
        "list", "Playing order", "partyhost-order", items=items,
        buttons=[{"label": "Shuffle again", "say": "Shuffle the playing order again."}]))


def round_timer(a: dict) -> screen.Shown:
    seconds = min(3600, max(5, int(a.get("seconds") or 60)))
    ends = int(time.time() * 1000) + seconds * 1000
    return screen.Shown(f"{seconds} seconds on the clock. Go!", screen.card("timer", "Round timer", "partyhost-timer",
                                                                            ends_at=ends))


# ---- Tool ------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "party_draw",
        "description": "Party draws and timers. action: 'santa_draw' (Secret Santa: names, optional exclusions as "
                       "pairs of names who can't draw each other, budget; if a draw exists ask first and set "
                       "confirmed only after a yes), 'santa_next' (shows the next person their name privately; "
                       "optional name to show someone again; never say the name aloud), 'santa_status', "
                       "'santa_clear' (needs confirmed after a yes), 'team_split' (names, teams or team_size, "
                       "captains), 'musical_stop' (musical chairs or statues random stop timer), 'bingo_card' (UK "
                       "90-ball tickets to play on screen), 'bingo_calls' (traditional calls, or one number), "
                       "'who_goes_first' (random playing order), 'round_timer' (seconds).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "names": {"type": "array", "items": {"type": "string"}},
                "name": {"type": "string"},
                "exclusions": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                "budget": {"type": "string", "description": "e.g. £10"},
                "teams": {"type": "integer"}, "team_size": {"type": "integer"}, "captains": {"type": "boolean"},
                "min_seconds": {"type": "integer"}, "max_seconds": {"type": "integer"},
                "seconds": {"type": "integer"}, "count": {"type": "integer"}, "number": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"party_draw"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    table = {
        "santa_draw": lambda: santa_draw(settings, args), "santa_next": lambda: santa_next(settings, args),
        "santa_status": lambda: santa_status(settings), "santa_clear": lambda: santa_clear(settings, args),
        "team_split": lambda: team_split(args), "musical_stop": lambda: musical_stop(args),
        "bingo_card": lambda: bingo_card(args), "bingo_calls": lambda: bingo_calls(args),
        "who_goes_first": lambda: who_goes_first(args), "round_timer": lambda: round_timer(args),
    }
    if action not in table:
        raise ValueError(f"I don't know the party action {action}.")
    return table[action]()
