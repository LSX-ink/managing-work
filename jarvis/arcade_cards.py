"""Screen games: card games with Alfred (higher or lower, blackjack with Alfred as dealer) and a bingo caller.

Cards are drawn in a pop-up; Hit, Stand, Higher, Lower and Next number buttons send the move to Alfred, and
saying it works just as well. Games live in this process only.
"""

import arcade
import screen
from arcade import rng
from config import Settings

screen.EXTRA_KINDS.update({"arcade-cards", "arcade-bingo"})
state: dict = {"higher_or_lower": None, "blackjack": None, "bingo": None}

GAMES = {"higher_or_lower": "Higher or lower", "blackjack": "Blackjack", "bingo": "Bingo"}
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = "SHDC"
RANK_NAMES = {"J": "jack", "Q": "queen", "K": "king", "A": "ace"}
SUIT_NAMES = {"S": "spades", "H": "hearts", "D": "diamonds", "C": "clubs"}
BINGO_CALLS = {
    1: "Kelly's eye", 2: "One little duck", 3: "Cup of tea", 4: "Knock at the door", 5: "Man alive",
    7: "Lucky seven", 8: "Garden gate", 9: "Doctor's orders", 10: "Downing Street", 11: "Legs eleven",
    12: "One dozen", 13: "Unlucky for some", 16: "Sweet sixteen", 21: "Key of the door", 22: "Two little ducks",
    26: "Pick and mix", 27: "Gateway to heaven", 30: "Dirty Gertie", 44: "Droopy drawers", 45: "Halfway there",
    48: "Four dozen", 52: "Deck of cards", 55: "Snakes alive", 57: "Heinz varieties", 59: "Brighton line",
    64: "Red raw", 66: "Clickety click", 69: "Anyway up", 76: "Trombones", 77: "Sunset strip",
    80: "Gandhi's breakfast", 83: "Time for tea", 86: "Between the sticks", 88: "Two fat ladies",
    89: "Nearly there", 90: "Top of the shop",
}


def deck() -> list[str]:
    cards = [r + s for s in SUITS for r in RANKS]
    rng.shuffle(cards)
    return cards


def spoken(card: str) -> str:
    rank, suit = card[:-1], card[-1]
    return f"{'an' if rank in ('A', '8') else 'a'} {RANK_NAMES.get(rank, rank)} of {SUIT_NAMES[suit]}"


def _view(game: str, said: str, hands: list[dict], status: str, buttons: list[dict]) -> screen.Shown:
    return screen.Shown(said, screen.card("arcade-cards", GAMES[game], f"arcade-{game}", buttons=buttons,
                                          data={"hands": hands, "status": status}))


# ---- Higher or lower ---------------------------------------------------------------------------

def _hl_view(said: str) -> screen.Shown:
    g = state["higher_or_lower"]
    hands = ([{"label": "Last card", "cards": [g["previous"]]}] if g["previous"] else []) + \
        [{"label": "This card", "cards": [g["current"]]}]
    buttons = ([{"label": "Play again", "say": "Start a new game of higher or lower."}] if g["over"] else
               [{"label": "Higher", "say": "Higher or lower: higher."},
                {"label": "Lower", "say": "Higher or lower: lower."}])
    status = f"Streak: {g['streak']}" + (" · game over" if g["over"] else "")
    return _view("higher_or_lower", said, hands, status, buttons)


def hl_start() -> screen.Shown:
    cards = deck()
    state["higher_or_lower"] = {"deck": cards, "current": cards.pop(), "previous": "", "streak": 0, "over": False}
    card = state["higher_or_lower"]["current"]
    return _hl_view(f"The first card is {spoken(card)}. Higher or lower? Aces are high.")


def hl_guess(call: str) -> screen.Shown:
    g = state["higher_or_lower"]
    if not g or g["over"]:
        raise ValueError("There's no higher or lower game going. Say 'let's play higher or lower'.")
    if not g["deck"]:
        g["deck"] = deck()
    new = g["deck"].pop()
    old = g["current"]
    g["previous"], g["current"] = old, new
    a, b = RANKS.index(old[:-1]), RANKS.index(new[:-1])
    said = f"It's {spoken(new)}."
    if a == b:
        return _hl_view(f"{said} Same value, so you're safe. Higher or lower?")
    if (b > a) == (call == "higher"):
        g["streak"] += 1
        return _hl_view(f"{said} Right! Streak of {g['streak']}. Higher or lower?")
    g["over"] = True
    arcade.record("higher_or_lower", None, g["streak"])
    return _hl_view(f"{said} Unlucky, game over with a streak of {g['streak']}.")


# ---- Blackjack ---------------------------------------------------------------------------------

def total(cards: list[str]) -> int:
    points = sum(11 if c[:-1] == "A" else 10 if c[:-1] in ("J", "Q", "K") else int(c[:-1]) for c in cards)
    aces = sum(1 for c in cards if c[:-1] == "A")
    while points > 21 and aces:
        points, aces = points - 10, aces - 1
    return points


def _bj_view(said: str) -> screen.Shown:
    g = state["blackjack"]
    dealer = g["dealer"] if g["over"] else [g["dealer"][0], "??"]
    hands = [{"label": "Alfred (dealer)", "cards": dealer,
              "total": str(total(g["dealer"])) if g["over"] else ""},
             {"label": "You", "cards": g["player"], "total": str(total(g["player"]))}]
    buttons = ([{"label": "Deal again", "say": "Deal a new hand of blackjack."}] if g["over"] else
               [{"label": "Hit", "say": "Blackjack: hit me."}, {"label": "Stand", "say": "Blackjack: I stand."}])
    return _view("blackjack", said, hands, g["result"] or "Hit or stand?", buttons)


def _bj_end(result: str, said: str) -> screen.Shown:
    g = state["blackjack"]
    g["over"] = True
    g["result"] = {"won": "You win.", "lost": "Alfred wins.", "drawn": "Push: it's a tie."}[result]
    arcade.record("blackjack", result)
    return _bj_view(said)


def bj_start() -> screen.Shown:
    cards = deck()
    g = state["blackjack"] = {"deck": cards, "player": [cards.pop(), cards.pop()],
                              "dealer": [cards.pop(), cards.pop()], "over": False, "result": ""}
    you, me = total(g["player"]), total(g["dealer"])
    said = f"You have {spoken(g['player'][0])} and {spoken(g['player'][1])}: {you}. I'm showing " \
           f"{spoken(g['dealer'][0])}."
    if you == 21 or me == 21:
        result = "drawn" if you == me else "won" if you == 21 else "lost"
        return _bj_end(result, f"{said} {'Blackjack! ' if you == 21 else ''}I have {me}.")
    return _bj_view(f"{said} Hit or stand?")


def _bj_game() -> dict:
    g = state["blackjack"]
    if not g or g["over"]:
        raise ValueError("There's no hand of blackjack going. Say 'deal me in at blackjack'.")
    return g


def bj_hit() -> screen.Shown:
    g = _bj_game()
    card = g["deck"].pop()
    g["player"].append(card)
    you = total(g["player"])
    if you > 21:
        return _bj_end("lost", f"{spoken(card).capitalize()}. That's {you}, you're bust.")
    if you == 21:
        return bj_stand(f"{spoken(card).capitalize()}. That's 21. ")
    return _bj_view(f"{spoken(card).capitalize()}. That's {you}. Hit or stand?")


def bj_stand(said: str = "") -> screen.Shown:
    g = _bj_game()
    while total(g["dealer"]) < 17:
        g["dealer"].append(g["deck"].pop())
    you, me = total(g["player"]), total(g["dealer"])
    said += f"I have {me}."
    if me > 21:
        return _bj_end("won", f"{said} I'm bust, you win!")
    if you == me:
        return _bj_end("drawn", f"{said} We both have {me}: a push.")
    return _bj_end("won" if you > me else "lost", f"{said} {'You win!' if you > me else 'I win.'}")


# ---- Bingo caller ------------------------------------------------------------------------------

def _bingo_view(said: str) -> screen.Shown:
    g = state["bingo"]
    last = g["called"][-1] if g["called"] else None
    buttons = [{"label": "Next number", "say": "Bingo: call the next number."},
               {"label": "New game", "say": "Start a new game of bingo."}]
    data = {"called": g["called"], "last": last, "call": BINGO_CALLS.get(last, "") if last else ""}
    return screen.Shown(said, screen.card("arcade-bingo", "Bingo", "arcade-bingo", buttons=buttons[1:] if not
                                          g["pool"] else buttons, data=data))


def bingo_start() -> screen.Shown:
    pool = list(range(1, 91))
    rng.shuffle(pool)
    state["bingo"] = {"pool": pool, "called": []}
    arcade.record("bingo")
    return _bingo_view("Eyes down: bingo, numbers 1 to 90. Say 'next number' when you're ready.")


def bingo_next() -> screen.Shown:
    g = state["bingo"]
    if not g:
        bingo_start()
        g = state["bingo"]
    if not g["pool"]:
        return _bingo_view("That's all 90 numbers called.")
    n = g["pool"].pop()
    g["called"].append(n)
    call = BINGO_CALLS.get(n)
    if call:
        return _bingo_view(f"{call}, {n}.")
    return _bingo_view(f"{' and '.join(str(n))}, {n}." if n > 9 else f"On its own, number {n}.")


# ---- The tool ----------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "play_card_game",
        "description": "Card games with Alfred in a pop-up on the screen, and a bingo caller. game: "
                       "'higher_or_lower' (playing cards; say higher or lower), 'blackjack' (Alfred deals; hit or "
                       "stand), 'bingo' (Alfred calls numbers 1 to 90). action: 'start' / deal a new game, "
                       "'higher', 'lower', 'hit', 'stand', 'next' (next bingo number), 'show' it again.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game": {"type": "string", "enum": list(GAMES)},
                "action": {"type": "string", "enum": ["start", "higher", "lower", "hit", "stand", "next", "show"]},
            },
            "required": ["game", "action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"play_card_game"}
STARTS = {"higher_or_lower": hl_start, "blackjack": bj_start, "bingo": bingo_start}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    game, action = args.get("game") or "", args.get("action") or "start"
    if game not in GAMES:
        raise ValueError("Which game? Higher or lower, blackjack or bingo.")
    if action == "start" or not state[game]:
        return STARTS[game]()
    if action == "show":
        view = {"higher_or_lower": _hl_view, "blackjack": _bj_view, "bingo": _bingo_view}[game]
        return view(f"Here's the {GAMES[game].lower()} game.")
    if game == "higher_or_lower" and action in ("higher", "lower"):
        return hl_guess(action)
    if game == "blackjack" and action in ("hit", "stand"):
        return bj_hit() if action == "hit" else bj_stand()
    if game == "bingo" and action == "next":
        return bingo_next()
    raise ValueError(f"That's not a move in {GAMES[game].lower()}.")
