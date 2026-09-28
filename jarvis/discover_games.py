"""Discover: learning games with clickable pop-ups. Times tables, spelling bee, human body quiz, timeline quiz,
kids' quiz, and a vocabulary builder that quizzes you on your own saved words.

The question waiting for an answer and the scores are kept in .discover-quiz.json, saved words in
discover-vocab.json, both in the memory folder.
"""

import json
import random
import re
from datetime import date

import memory
import screen
from config import Settings
from discover_data import BODY_QUESTIONS, EVENTS, KIDS_QUESTIONS, SPELLING

screen.EXTRA_KINDS.add("discover-quiz")

RNG = random.Random()
LETTERS = "ABCD"
GAMES = {"times_tables": "Times tables", "spelling_bee": "Spelling bee", "body_quiz": "Human body quiz",
         "timeline_quiz": "Timeline quiz", "kids_quiz": "Kids' quiz", "vocab_quiz": "Vocabulary quiz"}
MAX_WORDS = 2000


def _path(settings: Settings, name: str):
    return memory.root(settings) / name


def _load(settings: Settings, name: str, default):
    try:
        found = json.loads(_path(settings, name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def _save(settings: Settings, name: str, data) -> None:
    p = _path(settings, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _state(settings: Settings) -> dict:
    state = _load(settings, ".discover-quiz.json", {})
    state.setdefault("pending", None)
    state.setdefault("scores", {})
    return state


def _norm(text) -> str:
    text = re.sub(r"[^a-z0-9% ]+", " ", str(text or "").lower())
    text = re.sub(r"^(the|a|an) ", "", " ".join(text.split()))
    return text


def _score_text(state: dict, game: str) -> str:
    right, asked = state["scores"].get(game, [0, 0])
    return f"{right} of {asked}"


# ---- Asking --------------------------------------------------------------------------------

def _ask(settings: Settings, state: dict, game: str, question: str, answer: str, choices=None, said: str = "",
         extra: dict | None = None, **data) -> screen.Shown:
    state["pending"] = {"game": game, "question": question, "answer": answer, "choices": choices or [],
                        **(extra or {})}
    _save(settings, ".discover-quiz.json", state)
    order = data.get("order")
    options = [{"label": f"{LETTERS[i]}: {c}" if order else c,
                "say": "" if order else f"Quiz answer: {LETTERS[i]}, {c[:120]}"} for i, c in enumerate(choices or [])]
    buttons = [{"label": "Give up", "say": "I give up on this quiz question."},
               {"label": "Score", "say": "What's my quiz score?"}]
    card = screen.card("discover-quiz", GAMES[game], "discover-quiz", buttons=buttons, data={
        "question": question, "choices": options, "score": _score_text(state, game), "feedback": data.get("feedback", ""),
        "big": bool(data.get("big")), "order": bool(order), "input": bool(data.get("input"))})
    spoken = said or question
    if choices and not order:
        spoken += " " + " ".join(f"{LETTERS[i]}: {c}." for i, c in enumerate(choices))
    return screen.Shown((data.get("feedback", "") + " " + spoken).strip(), card)


def _multiple(settings: Settings, state: dict, game: str, question: str, right: str, wrong: list, **data):
    choices = [right, *RNG.sample(list(wrong), min(3, len(wrong)))]
    RNG.shuffle(choices)
    return _ask(settings, state, game, question, right, choices, **data)


def times_tables(settings: Settings, table=None, feedback: str = "") -> screen.Shown:
    state = _state(settings)
    a = int(table) if table else RNG.randint(2, 12)
    if not 1 <= a <= 20:
        raise ValueError("Pick a times table from 1 to 20.")
    b = RNG.randint(2, 12)
    right = a * b
    wrong = {a * (b + 1), a * (b - 1), (a + 1) * b, right + 10, right - 2, right + 1} - {right}
    wrong = [str(w) for w in sorted(wrong) if w > 0]
    return _multiple(settings, state, "times_tables", f"What is {a} times {b}?", str(right), wrong,
                     feedback=feedback, extra={"table": table or 0})


def spelling_bee(settings: Settings, level: str = "", feedback: str = "") -> screen.Shown:
    state = _state(settings)
    level = level if level in SPELLING else "medium"
    word = RNG.choice(SPELLING[level])
    said = (f"Spell the word: {word}. (Say the word clearly and don't spell it out; the user types or says the "
            f"spelling.)")
    return _ask(settings, state, "spelling_bee", f"Spell the word you heard ({level} level).", word, said=said,
                feedback=feedback, input=True, extra={"level": level})


def _from_bank(settings: Settings, game: str, bank: list, feedback: str = "", big: bool = False) -> screen.Shown:
    state = _state(settings)
    question, right, wrong = RNG.choice(bank)
    return _multiple(settings, state, game, question, right, wrong, feedback=feedback, big=big)


def timeline_quiz(settings: Settings, feedback: str = "") -> screen.Shown:
    state = _state(settings)
    picked: list = []
    for year, event in RNG.sample(EVENTS, len(EVENTS)):
        if all(year != y for y, _ in picked):
            picked.append((year, event))
        if len(picked) == 4:
            break
    order = "".join(LETTERS[i] for i, _ in sorted(enumerate(picked), key=lambda p: p[1][0]))
    choices = [event for _, event in picked]
    said = "Put these in order, earliest first: " + " ".join(f"{LETTERS[i]}: {c}." for i, c in enumerate(choices))
    return _ask(settings, state, "timeline_quiz", "Click the events from earliest to latest.", order, choices,
                said=said, feedback=feedback, order=True, extra={"years": [y for y, _ in picked]})


# ---- Vocabulary ------------------------------------------------------------------------------------

def _count(words: list) -> str:
    return f"{len(words)} word{'' if len(words) == 1 else 's'}"


def _words(settings: Settings) -> list[dict]:
    return _load(settings, "discover-vocab.json", [])


def vocab_add(settings: Settings, word, meaning, today: date) -> str:
    word, meaning = " ".join(str(word or "").split())[:60], " ".join(str(meaning or "").split())[:300]
    if not word or not meaning:
        raise ValueError("I need the word and what it means.")
    words = _words(settings)
    old = next((w for w in words if w["word"].lower() == word.lower()), None)
    if old:
        old["meaning"] = meaning
    elif len(words) >= MAX_WORDS:
        raise ValueError("Your vocabulary list is full.")
    else:
        words.append({"word": word, "meaning": meaning, "added": today.isoformat(), "right": 0, "wrong": 0})
    _save(settings, "discover-vocab.json", words)
    return f"{'Updated' if old else 'Saved'} {word}. You have {_count(words)} in your vocabulary list."


def vocab_list(settings: Settings) -> screen.Shown:
    words = sorted(_words(settings), key=lambda w: w["word"].lower())
    if not words:
        return screen.Shown("Your vocabulary list is empty. Tell me a new word and its meaning to start.",
                            screen.card("list", "My vocabulary", "discover-vocab", items=[]))
    items = [{"label": f"{w['word']}: {w['meaning']}"} for w in words]
    return screen.Shown(f"You have {len(words)} words saved. They're on the screen.", screen.card(
        "list", "My vocabulary", "discover-vocab", items=items,
        buttons=[{"label": "Quiz me", "say": "Quiz me on my vocabulary words."}]))


def vocab_quiz(settings: Settings, feedback: str = "") -> screen.Shown:
    words = _words(settings)
    if len(words) < 2:
        raise ValueError("Save at least two words first, then I can quiz you.")
    state = _state(settings)
    weights = [1 + max(0, w["wrong"] - w["right"]) * 2 for w in words]
    target = RNG.choices(words, weights)[0]
    wrong = [w["meaning"] for w in words if w is not target and w["meaning"] != target["meaning"]]
    return _multiple(settings, state, "vocab_quiz", f"What does '{target['word']}' mean?", target["meaning"], wrong,
                     feedback=feedback, extra={"word": target["word"]})


def vocab_forget(settings: Settings, word, confirmed: bool) -> str:
    words = _words(settings)
    found = next((w for w in words if w["word"].lower() == str(word or "").strip().lower()), None)
    if not found:
        raise ValueError(f"{word} isn't in your vocabulary list.")
    if not confirmed:
        return f"Remove {found['word']} from your vocabulary list? Say yes to confirm."
    words.remove(found)
    _save(settings, "discover-vocab.json", words)
    return f"Removed {found['word']}. {_count(words)} left."


# ---- Answering ----------------------------------------------------------------------------------

def _chosen(pending: dict, given: str) -> str:
    """The choice the user picked: by its words, or by its letter."""
    choices = pending["choices"]
    for c in choices:
        if _norm(c) == _norm(given):
            return c
    letter = re.match(r"^\s*([A-Da-d])\s*(?:$|[,.:)\-])", given)
    if letter and LETTERS.index(letter.group(1).upper()) < len(choices):
        return choices[LETTERS.index(letter.group(1).upper())]
    words = _norm(given)
    return next((c for c in choices if words and (words in _norm(c) or _norm(c) in words)), given)


def _correct(pending: dict, given: str) -> bool:
    game = pending["game"]
    if game == "spelling_bee":
        given = re.sub(r"(?i)^.*(quiz answer:|spelling is|spelled|spelt|spelling:)", "", given)
        return re.sub(r"[^a-z]", "", given.lower()) == pending["answer"].lower()
    if game == "timeline_quiz":
        letters = "".join(re.findall(r"\b([A-D])\b", given.upper()))
        return letters == pending["answer"]
    return _norm(_chosen(pending, given)) == _norm(pending["answer"])


def _reveal(pending: dict) -> str:
    game = pending["game"]
    if game == "spelling_bee":
        return f"It's spelled {'-'.join(pending['answer'].upper())}."
    if game == "timeline_quiz":
        order = sorted(zip(pending["years"], pending["choices"]))
        return "The order is: " + "; ".join(f"{e} ({y} BC)" if y < 0 else f"{e} ({y})" for y, e in order) + "."
    return f"The answer was {pending['answer']}."


def _next(settings: Settings, pending: dict, feedback: str) -> screen.Shown:
    game = pending["game"]
    if game == "times_tables":
        return times_tables(settings, pending.get("table") or None, feedback)
    if game == "spelling_bee":
        return spelling_bee(settings, pending.get("level", ""), feedback)
    if game == "timeline_quiz":
        return timeline_quiz(settings, feedback)
    if game == "vocab_quiz":
        return vocab_quiz(settings, feedback)
    return _from_bank(settings, game, BODY_QUESTIONS if game == "body_quiz" else KIDS_QUESTIONS, feedback,
                      big=game == "kids_quiz")


def answer(settings: Settings, given, give_up: bool = False) -> screen.Shown | str:
    state = _state(settings)
    pending = state["pending"]
    if not pending:
        return "There's no quiz question waiting. Ask me for times tables, a spelling bee or a quiz."
    right = not give_up and _correct(pending, str(given or ""))
    score = state["scores"].setdefault(pending["game"], [0, 0])
    score[0] += right
    score[1] += 1
    if pending["game"] == "vocab_quiz":
        words = _words(settings)
        for w in words:
            if w["word"] == pending.get("word"):
                w["right" if right else "wrong"] += 1
        _save(settings, "discover-vocab.json", words)
    state["pending"] = None
    _save(settings, ".discover-quiz.json", state)
    verdict = "Correct!" if right else ("No problem." if give_up else "Not quite.")
    feedback = f"{verdict} {'' if right else _reveal(pending)} Score {score[0]} of {score[1]}. Next one:"
    return _next(settings, pending, " ".join(feedback.split()))


def scores(settings: Settings) -> screen.Shown:
    state = _state(settings)
    rows = [[GAMES.get(g, g), f"{r} of {n}", f"{round(100 * r / n)}%" if n else "-"]
            for g, (r, n) in state["scores"].items()]
    if not rows:
        return screen.Shown("No quiz scores yet.", screen.card("text", "Quiz scores", "discover-scores",
                                                               text="No quiz scores yet."))
    said = "Your scores: " + "; ".join(f"{g} {s}" for g, s, _ in rows) + "."
    return screen.Shown(said, screen.card("table", "Quiz scores", "discover-scores",
                                          columns=["Game", "Right", "Score"], rows=rows))


ACTIONS = ["times_tables", "spelling_bee", "body_quiz", "timeline_quiz", "kids_quiz", "answer", "give_up",
           "scores", "vocab_add", "vocab_list", "vocab_quiz", "vocab_forget"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "learning_games",
        "description": "Learning games and quizzes with clickable pop-ups: times_tables practice (optional table), "
                       "spelling_bee (level easy/medium/hard; say the word aloud, never spell it), body_quiz "
                       "(human body facts), timeline_quiz (put 4 historical events in order), kids_quiz (easy "
                       "questions, big buttons). Then 'answer' with the user's reply (a letter, the answer, the "
                       "spelling, or the timeline letters in order; pop-up clicks arrive as 'Quiz answer: ...'), or "
                       "give_up; scores shows quiz scores. Vocabulary builder: vocab_add a new word with its "
                       "meaning, vocab_list, vocab_quiz, vocab_forget (set confirmed=true only after the user "
                       "says yes).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "table": {"type": "integer", "description": "times_tables: which table, e.g. 7."},
                "level": {"type": "string", "enum": ["easy", "medium", "hard"]},
                "answer": {"type": "string"},
                "word": {"type": "string"},
                "meaning": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"learning_games"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "times_tables":
        return times_tables(settings, args.get("table"))
    if action == "spelling_bee":
        return spelling_bee(settings, args.get("level") or "")
    if action == "body_quiz":
        return _from_bank(settings, "body_quiz", BODY_QUESTIONS)
    if action == "kids_quiz":
        return _from_bank(settings, "kids_quiz", KIDS_QUESTIONS, big=True)
    if action == "timeline_quiz":
        return timeline_quiz(settings)
    if action in ("answer", "give_up"):
        return answer(settings, args.get("answer"), action == "give_up")
    if action == "scores":
        return scores(settings)
    if action == "vocab_add":
        return vocab_add(settings, args.get("word"), args.get("meaning"), date.today())
    if action == "vocab_list":
        return vocab_list(settings)
    if action == "vocab_quiz":
        return vocab_quiz(settings)
    if action == "vocab_forget":
        return vocab_forget(settings, args.get("word"), bool(args.get("confirmed")))
    raise ValueError(f"Unknown learning game action: {action}")
