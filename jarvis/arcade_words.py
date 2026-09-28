"""Screen games: hangman (with a drawing), a Wordle-style five-letter word game, and capital cities and flags quizzes.

All words and countries are local (arcade_lists). Flag pictures come from flagcdn.com, loaded by the page itself;
nothing is sent anywhere. Games live in this process only; every guess redraws the pop-up.
"""

import re

import arcade
import screen
from arcade import rng
from arcade_lists import ANSWERS, COUNTRIES, EXTRA, HANGMAN
from config import Settings

screen.EXTRA_KINDS.update({"arcade-hangman", "arcade-wordle"})
state: dict = {"hangman": None, "wordle": None, "capitals": None, "flags": None}

GAMES = {"hangman": "Hangman", "wordle": "Wordle", "capitals": "Capitals quiz", "flags": "Flags quiz"}
LIVES = 6
TRIES = 6
QUESTIONS = 10
VALID = set(ANSWERS) | set(EXTRA)
FLAG_URL = "https://flagcdn.com/w320/{}.png"


def _again(game: str) -> list[dict]:
    return [{"label": "Play again", "say": f"Start a new {GAMES[game].lower()} game."}]


# ---- Hangman -----------------------------------------------------------------------------------

def _pattern(g: dict) -> str:
    return " ".join(ch.upper() if ch in g["guessed"] or g["over"] else "_" for ch in g["word"])


def _hangman_view(said: str) -> screen.Shown:
    g = state["hangman"]
    misses = sorted(ch for ch in g["guessed"] if ch not in g["word"])
    data = {"pattern": _pattern(g), "misses": len(misses), "lives": LIVES,
            "wrong": [m.lstrip("#").upper() for m in misses],
            "guessed": sorted(ch.upper() for ch in g["guessed"] if len(ch) == 1), "over": g["over"],
            "won": g["over"] and set(g["word"]) <= g["guessed"],
            "say": "" if g["over"] else "Hangman: guess the letter %s."}
    buttons = _again("hangman") if g["over"] else [{"label": "Hint", "say": "Give me a hangman hint."}]
    return screen.Shown(said, screen.card("arcade-hangman", "Hangman", "arcade-hangman", buttons=buttons, data=data))


def hangman_start() -> screen.Shown:
    word = rng.choice(HANGMAN)
    state["hangman"] = {"word": word, "guessed": set(), "over": False}
    return _hangman_view(f"New hangman word: {len(word)} letters. Guess a letter.")


def _hangman_game() -> dict:
    g = state["hangman"]
    if not g or g["over"]:
        raise ValueError("There's no hangman game going. Say 'let's play hangman' to start.")
    return g


def _hangman_check(g: dict, said: str) -> screen.Shown:
    misses = sum(1 for ch in g["guessed"] if ch not in g["word"])
    if set(g["word"]) <= g["guessed"]:
        g["over"] = True
        arcade.record("hangman", "won", LIVES - misses)
        said += f" You got it: {g['word'].upper()}!"
    elif misses >= LIVES:
        g["over"] = True
        arcade.record("hangman", "lost", 0)
        said += f" That's the whole drawing. The word was {g['word'].upper()}."
    else:
        said += f" {LIVES - misses} wrong guess{'es' if LIVES - misses != 1 else ''} left."
    return _hangman_view(said.strip())


def hangman_guess(guess: str) -> screen.Shown:
    g = _hangman_game()
    guess = re.sub(r"[^a-z]", "", _letter_or_word(guess))
    if not guess:
        raise ValueError("Guess a letter, or the whole word.")
    if len(guess) > 1:
        if guess == g["word"]:
            g["guessed"] |= set(g["word"])
            return _hangman_check(g, "")
        g["guessed"].add(f"#{guess}")  # a wrong whole word costs a life
        return _hangman_check(g, f"No, it isn't {guess}.")
    if guess in g["guessed"]:
        return _hangman_view(f"You've already tried {guess.upper()}.")
    g["guessed"].add(guess)
    count = g["word"].count(guess)
    return _hangman_check(g, f"Yes, {count} {guess.upper()}{'s' if count > 1 else ''}." if count
                          else f"No {guess.upper()}.")


def _letter_or_word(text: str) -> str:
    """'the letter e' -> 'e'; 'is it penguin' -> 'penguin'."""
    text = str(text or "").lower().strip()
    m = re.search(r"\bletter\s+([a-z])\b", text)
    if m:
        return m.group(1)
    words = re.findall(r"[a-z]+", text)
    return words[-1] if words else ""


def hangman_hint() -> screen.Shown:
    g = _hangman_game()
    left = [ch for ch in dict.fromkeys(g["word"]) if ch not in g["guessed"]]
    ch = rng.choice(left)
    g["guessed"].add(ch)
    return _hangman_check(g, f"Here's a letter: {ch.upper()}.")


def hangman_give_up() -> screen.Shown:
    g = _hangman_game()
    g["over"] = True
    arcade.record("hangman", "lost", 0)
    return _hangman_view(f"The word was {g['word'].upper()}.")


# ---- Wordle ------------------------------------------------------------------------------------

def marks(guess: str, answer: str) -> str:
    """'g' right place, 'y' in the word elsewhere, '.' not in it; repeated letters counted properly."""
    out, spare = ["."] * 5, []
    for i, (a, b) in enumerate(zip(guess, answer)):
        if a == b:
            out[i] = "g"
        else:
            spare.append(b)
    for i, a in enumerate(guess):
        if out[i] != "g" and a in spare:
            out[i] = "y"
            spare.remove(a)
    return "".join(out)


def _wordle_view(said: str) -> screen.Shown:
    g = state["wordle"]
    letters: dict = {}
    rank = {"g": 3, "y": 2, ".": 1}
    for word, m in g["rows"]:
        for ch, mk in zip(word, m):
            if rank[mk] > rank.get(letters.get(ch.upper()), 0):
                letters[ch.upper()] = mk
    data = {"rows": [{"word": w.upper(), "marks": m} for w, m in g["rows"]], "tries": TRIES, "letters": letters,
            "over": g["over"], "answer": g["answer"].upper() if g["over"] else "",
            "say": "" if g["over"] else "Wordle guess: %s."}
    buttons = _again("wordle") if g["over"] else [{"label": "Give up", "say": "I give up on the wordle."}]
    return screen.Shown(said, screen.card("arcade-wordle", "Wordle", "arcade-wordle", buttons=buttons, data=data))


def wordle_start() -> screen.Shown:
    state["wordle"] = {"answer": rng.choice(ANSWERS), "rows": [], "over": False}
    return _wordle_view("I'm thinking of a five-letter word. You have six guesses.")


def _wordle_game() -> dict:
    g = state["wordle"]
    if not g or g["over"]:
        raise ValueError("There's no wordle going. Say 'let's play wordle' to start.")
    return g


def wordle_guess(guess: str) -> screen.Shown:
    g = _wordle_game()
    word = next((w for w in reversed(re.findall(r"[a-z]+", str(guess or "").lower())) if len(w) == 5), "")
    if not word:
        raise ValueError("Guess a five-letter word.")
    if word not in VALID:
        return _wordle_view(f"I don't know the word {word.upper()}. Try another; that didn't use a guess.")
    m = marks(word, g["answer"])
    g["rows"].append((word, m))
    if m == "ggggg":
        g["over"] = True
        n = len(g["rows"])
        arcade.record("wordle", "won", n)
        return _wordle_view(f"{word.upper()} is right, in {n} guess{'es' if n > 1 else ''}!")
    if len(g["rows"]) >= TRIES:
        g["over"] = True
        arcade.record("wordle", "lost")
        return _wordle_view(f"Out of guesses. The word was {g['answer'].upper()}.")
    return _wordle_view(f"{word.upper()}: {_describe(word, m)}")


def _describe(word: str, m: str) -> str:
    right = [c.upper() for c, k in zip(word, m) if k == "g"]
    near = [c.upper() for c, k in zip(word, m) if k == "y"]
    parts = ([f"{', '.join(right)} in the right place"] if right else []) + \
            ([f"{', '.join(near)} in the word elsewhere"] if near else [])
    left = TRIES - len(state["wordle"]["rows"])
    return f"{'; '.join(parts) or 'no letters match'}. {left} guess{'es' if left != 1 else ''} left."


def wordle_hint() -> screen.Shown:
    g = _wordle_game()
    known = {c for w, m in g["rows"] for c, k in zip(w, m) if k in "gy"}
    left = [c for c in dict.fromkeys(g["answer"]) if c not in known] or list(g["answer"])
    ch = rng.choice(left)
    return _wordle_view(f"The word has the letter {ch.upper()} in it.")


def wordle_give_up() -> screen.Shown:
    g = _wordle_game()
    g["over"] = True
    arcade.record("wordle", "lost")
    return _wordle_view(f"The word was {g['answer'].upper()}.")


# ---- Capitals and flags quizzes ----------------------------------------------------------------

def _question(q: dict) -> None:
    country = COUNTRIES[q["order"][q["i"]]]
    field = 1 if q["kind"] == "capitals" else 0
    others = [c[field] for c in COUNTRIES if c[field] != country[field]]
    q["options"] = rng.sample(others, 3) + [country[field]]
    rng.shuffle(q["options"])
    q["country"] = country
    q["answer"] = country[field]


def _quiz_view(kind: str, said: str) -> screen.Shown:
    q = state[kind]
    head = f"Score {q['score']} of {q['i'] if not q['over'] else QUESTIONS}"
    if q["over"]:
        text = f"{q['last']}\n\nFinal score: {q['score']} out of {QUESTIONS}."
        c = screen.card("text", GAMES[kind], f"arcade-{kind}", buttons=_again(kind), text=text)
        return screen.Shown(said, c)
    label = "Capitals quiz: my answer is" if kind == "capitals" else "Flags quiz: my answer is"
    buttons = [{"label": o, "say": f"{label} {o}."} for o in q["options"]]
    number = f"Question {q['i'] + 1} of {QUESTIONS} · {head}"
    if kind == "capitals":
        text = f"{q['last']}\n\n{number}\n\nWhat is the capital of {q['country'][0]}?".strip()
        c = screen.card("text", GAMES[kind], f"arcade-{kind}", buttons=buttons, text=text)
    else:
        text = f"{q['last']}\n\n{number}\n\nWhich country's flag is this?".strip()
        c = screen.card("image", GAMES[kind], f"arcade-{kind}", buttons=buttons, text=text,
                        src=FLAG_URL.format(q["country"][2]))
    return screen.Shown(said, c)


def _ask_line(kind: str) -> str:
    q = state[kind]
    options = ", ".join(q["options"][:-1]) + f" or {q['options'][-1]}"
    if kind == "capitals":
        return f"What is the capital of {q['country'][0]}? {options}?"
    return f"Which country's flag is this? {options}?"


def quiz_start(kind: str) -> screen.Shown:
    order = rng.sample(range(len(COUNTRIES)), QUESTIONS)
    state[kind] = {"kind": kind, "order": order, "i": 0, "score": 0, "over": False, "last": ""}
    _question(state[kind])
    return _quiz_view(kind, f"{GAMES[kind]}: ten questions. {_ask_line(kind)}")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z ]", "", str(text or "").lower()).strip()


def _chosen(q: dict, answer: str) -> str | None:
    said = _norm(answer)
    letter = re.fullmatch(r"(?:.*\s)?([abcd])", said)
    if letter:
        return q["options"]["abcd".index(letter.group(1))]
    hits = [o for o in q["options"] if _norm(o) and (_norm(o) in said or said and said in _norm(o))]
    return max(hits, key=len) if hits else None


def quiz_answer(kind: str, answer: str) -> screen.Shown:
    q = state[kind]
    if not q or q["over"]:
        raise ValueError(f"There's no {GAMES[kind].lower()} going. Ask me to start one.")
    pick = _chosen(q, answer)
    if pick is None:
        return _quiz_view(kind, f"Pick one of: {', '.join(q['options'])}.")
    country, right = q["country"][0], q["answer"]
    fact = f"{right} is the capital of {country}." if kind == "capitals" else f"That's the flag of {country}."
    if pick == right:
        q["score"] += 1
        q["last"] = f"Right! {fact}"
    else:
        q["last"] = f"Not quite. {fact}"
    return _quiz_next(kind)


def _quiz_next(kind: str) -> screen.Shown:
    q = state[kind]
    q["i"] += 1
    if q["i"] >= QUESTIONS:
        q["over"] = True
        arcade.record(kind, None, q["score"])
        return _quiz_view(kind, f"{q['last']} That's the end: {q['score']} out of {QUESTIONS}.")
    _question(q)
    return _quiz_view(kind, f"{q['last']} Next: {_ask_line(kind)}")


def quiz_skip(kind: str) -> screen.Shown:
    q = state[kind]
    if not q or q["over"]:
        raise ValueError(f"There's no {GAMES[kind].lower()} going.")
    q["last"] = (f"The capital of {q['country'][0]} is {q['answer']}." if kind == "capitals"
                 else f"That was the flag of {q['country'][0]}.")
    return _quiz_next(kind)


# ---- The tool ----------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "play_word_game",
        "description": "Word games and quizzes in a pop-up on the screen, played by clicking or by voice. game: "
                       "'hangman' (guess letters or the word), 'wordle' (guess a five-letter word in six tries), "
                       "'capitals' (capital cities quiz), 'flags' (which country's flag). action: 'start' a new "
                       "game, 'guess' with the user's letter, word or quiz answer (a name or A-D), 'hint' (hangman "
                       "or wordle), 'give_up' (or skip a quiz question), 'show' it again.",
        "input_schema": {
            "type": "object",
            "properties": {
                "game": {"type": "string", "enum": list(GAMES)},
                "action": {"type": "string", "enum": ["start", "guess", "hint", "give_up", "show"]},
                "guess": {"type": "string"},
            },
            "required": ["game", "action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"play_word_game"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    game, action, guess = args.get("game") or "", args.get("action") or "start", args.get("guess") or ""
    if game not in GAMES:
        raise ValueError("Which game? Hangman, wordle, the capitals quiz or the flags quiz.")
    quiz = game in ("capitals", "flags")
    if action == "start" or (action == "show" and not state[game]):
        return quiz_start(game) if quiz else hangman_start() if game == "hangman" else wordle_start()
    if action == "show":
        if quiz:
            return _quiz_view(game, _ask_line(game) if not state[game]["over"] else "Here's how the quiz went.")
        return _hangman_view("Here's the hangman game.") if game == "hangman" else _wordle_view("Here's the wordle.")
    if action == "guess":
        return quiz_answer(game, guess) if quiz else hangman_guess(guess) if game == "hangman" else \
            wordle_guess(guess)
    if action == "hint":
        if quiz:
            raise ValueError("There are no hints in the quiz, but you can skip the question.")
        return hangman_hint() if game == "hangman" else wordle_hint()
    return quiz_skip(game) if quiz else hangman_give_up() if game == "hangman" else wordle_give_up()
