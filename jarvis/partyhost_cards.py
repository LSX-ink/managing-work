"""Party host: word and prompt games. Charades and Pictionary cards, Taboo-style cards with forbidden words, a Heads
Up deck, family-friendly truth or dare, two truths and a lie, Scattergories rounds and icebreakers.

The word is never in the text Alfred speaks; the card hides it until the player taps to show it. Decks don't repeat
until they have all been used.
"""

import random

import partyhost_data as data
import screen
from config import Settings

screen.EXTRA_KINDS.add("partyhost-cards")

RNG = random.Random()
MODES = ("charades", "pictionary", "taboo", "heads_up", "truth", "dare", "truth_or_dare", "two_truths",
         "two_truths_shuffle", "scattergories", "icebreaker", "word_categories")
SECONDS = {"charades": 90, "pictionary": 60, "taboo": 60, "heads_up": 60, "scattergories": 120}
_used: dict[str, set] = {}


def _pick(deck: str, items: list, count: int = 1) -> list:
    """count items from a deck that hasn't repeated any until all have been used."""
    used = _used.setdefault(deck, set())
    fresh = [i for i in range(len(items)) if i not in used]
    if len(fresh) < count:
        used.clear()
        fresh = list(range(len(items)))
    chosen = RNG.sample(fresh, min(count, len(fresh)))
    used.update(chosen)
    return [items[i] for i in chosen]


def _category(mode: str, name) -> str:
    allowed = data.DRAWABLE if mode == "pictionary" else list(data.WORDS)
    text = str(name or "").strip().lower()
    if not text:
        return ""
    found = [c for c in allowed if c == text] or [c for c in allowed if text in c or c.rstrip("s") in text]
    if not found:
        raise ValueError(f"I don't have a {text} set for {mode.replace('_', ' ')}. Try {', '.join(allowed)}.")
    return found[0]


def _words(mode: str, name, count: int) -> tuple[list[dict], str]:
    category = _category(mode, name)
    if category:
        pool = [(category, w) for w in data.WORDS[category]]
    else:
        allowed = data.DRAWABLE if mode == "pictionary" else list(data.WORDS)
        pool = [(c, w) for c in allowed for w in data.WORDS[c]]
    deck = f"{mode}-{category or 'any'}"
    return [{"word": w, "category": c} for c, w in _pick(deck, pool, count)], category


def _card(mode: str, title: str, said: str, cards: list[dict], buttons: list[dict], seconds: int = 0, **extra) -> screen.Shown:
    payload = {"mode": mode, "cards": cards, "seconds": seconds, **extra}
    return screen.Shown(said, screen.card("partyhost-cards", title, f"partyhost-{mode}", buttons=buttons, data=payload))


def _again(label: str, say: str) -> list[dict]:
    return [{"label": label, "say": say}]


def word_game(mode: str, args: dict) -> screen.Shown:
    seconds = min(600, max(10, int(args.get("seconds") or SECONDS[mode])))
    if mode in ("charades", "pictionary"):
        cards, category = _words(mode, args.get("category"), 1)
        verb = "act it out, no talking" if mode == "charades" else "draw it, no letters or talking"
        said = (f"{mode.title()} card ready: {seconds} seconds. Tap to show the word to the player only, then {verb}.")
        return _card(mode, mode.title(), said, cards, _again("New word", f"Give me another {mode} card."), seconds)
    if mode == "heads_up":
        count = min(40, max(3, int(args.get("count") or 15)))
        cards, category = _words(mode, args.get("category"), count)
        return _card(mode, "Heads Up", f"Heads Up: {seconds} seconds. Hold the screen to your forehead and friends "
                     "shout clues. Tap Got it or Pass.", cards, _again("New deck", "Deal a new Heads Up deck."), seconds)
    cards = [{"word": w, "forbidden": f} for w, f in _pick("taboo", data.TABOO, min(40, max(1, int(args.get("count") or 1))))]
    return _card("taboo", "Taboo", f"Taboo card ready: describe the word without saying the forbidden words. "
                 f"{seconds} seconds.", cards, _again("New card", "Give me another Taboo card."), seconds)


def prompt(mode: str) -> screen.Shown:
    if mode == "truth_or_dare":
        mode = RNG.choice(("truth", "dare"))
    deck = {"truth": data.TRUTHS, "dare": data.DARES, "icebreaker": data.ICEBREAKERS}[mode]
    (text,) = _pick(mode, deck)
    title = {"truth": "Truth", "dare": "Dare", "icebreaker": "Icebreaker"}[mode]
    buttons = ([{"label": "Truth", "say": "Give me a truth."}, {"label": "Dare", "say": "Give me a dare."}]
               if mode != "icebreaker" else _again("Another", "Give me another icebreaker question."))
    return _card("prompt", title, f"{title}: {text}", [{"word": text, "category": title}], buttons, 0)


def two_truths() -> screen.Shown:
    ideas = _pick("two-truths", data.TWO_TRUTHS_PROMPTS, 3)
    lines = [f"{i + 1}. {idea.capitalize()}" for i, idea in enumerate(ideas)]
    said = "For two truths and a lie, think of two true things and one lie about: " + "; ".join(ideas) + "."
    card = screen.card("text", "Two truths and a lie", text="\n".join(lines) + "\n\nPick one idea, or mix and match. "
                       "Make the lie believable!", buttons=_again("Other ideas", "Give me more ideas for two truths and a lie."))
    return screen.Shown(said, card)


def two_truths_shuffle(args: dict) -> screen.Shown:
    lines = [str(s).strip() for s in args.get("statements") or [] if str(s).strip()]
    if len(lines) != 3:
        raise ValueError("Give me exactly three statements: two truths and a lie.")
    lie = int(args.get("lie") or 0)
    if not 1 <= lie <= 3:
        raise ValueError("Which one is the lie: 1, 2 or 3?")
    order = list(range(3))
    RNG.shuffle(order)
    cards = [{"word": lines[i][:200], "category": str(n + 1), "lie": i == lie - 1} for n, i in enumerate(order)]
    return _card("two_truths", "Two truths and a lie", "The three statements are on the screen in a fresh order. "
                 "Let the group vote, then tap the lie to reveal it.", cards, [], 0)


def scattergories(args: dict) -> screen.Shown:
    seconds = min(600, max(30, int(args.get("seconds") or SECONDS["scattergories"])))
    letter = RNG.choice(data.SCATTER_LETTERS)
    cats = _pick("scatter", data.SCATTER_CATEGORIES, min(12, max(4, int(args.get("count") or 8))))
    cards = [{"word": c, "category": letter} for c in cats]
    return _card("scattergories", "Scattergories", f"The letter is {letter}. Find a word for each category before "
                 f"the {seconds} seconds run out.", cards, _again("New round", "Play another round of Scattergories."),
                 seconds, letter=letter)


def word_categories() -> screen.Shown:
    rows = [[c, len(w), "yes" if c in data.DRAWABLE else "no"] for c, w in data.WORDS.items()]
    return screen.Shown("Here are the word sets for charades, Heads Up and Pictionary.", screen.card(
        "table", "Word sets", columns=["Set", "Words", "Pictionary"], rows=rows))


# ---- Tool ------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "party_cards",
        "description": "Party word games and prompts, family-friendly. mode: 'charades' or 'pictionary' (a hidden word "
                       "card with a countdown; category optional: animals, actions, films, jobs, food, objects, "
                       "sports and hobbies, places, tv and books, easy), 'taboo' (Articulate style card with "
                       "forbidden words), 'heads_up' (a deck the player guesses from clues, timed), 'truth', 'dare' "
                       "or 'truth_or_dare', 'two_truths' (ideas for two truths and a lie), 'two_truths_shuffle' "
                       "(statements and lie number: reshuffles them for a vote), 'scattergories' (a letter and "
                       "categories with a timer), 'icebreaker' questions, 'word_categories'. Never read a hidden "
                       "word out.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": list(MODES)},
                "category": {"type": "string"},
                "seconds": {"type": "integer", "description": "Countdown length."},
                "count": {"type": "integer", "description": "Cards in a Heads Up deck, categories in Scattergories."},
                "statements": {"type": "array", "items": {"type": "string"}, "description": "three statements"},
                "lie": {"type": "integer", "description": "1, 2 or 3: which statement is the lie."},
            },
            "required": ["mode"],
            "additionalProperties": False,
        },
    }]


NAMES = {"party_cards"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    mode = args.get("mode")
    if mode in ("charades", "pictionary", "taboo", "heads_up"):
        return word_game(mode, args)
    if mode in ("truth", "dare", "truth_or_dare", "icebreaker"):
        return prompt(mode)
    if mode == "two_truths":
        return two_truths()
    if mode == "two_truths_shuffle":
        return two_truths_shuffle(args)
    if mode == "scattergories":
        return scattergories(args)
    if mode == "word_categories":
        return word_categories()
    raise ValueError(f"I don't know the party game {mode}.")
