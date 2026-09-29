"""Learning to drive: a theory test style quiz from built-in Highway Code questions. Multiple choice, clickable, with a
running score. The question waiting for an answer and the scores are kept in .motoring-quiz.json in the memory folder.
"""

import random
import re

import homestore as hs
import motoring_data as data
import screen
from config import Settings

screen.EXTRA_KINDS.add("motoring-quiz")

RNG = random.Random()
LETTERS = "ABCD"
ACTIONS = ["quiz_start", "quiz_answer", "quiz_score"]
FILE = ".motoring-quiz.json"


def tool_definitions() -> list[dict]:
    return [{
        "name": "motoring_theory",
        "description": "Driving theory test practice for a learner driver. quiz_start asks the next multiple-choice "
                       "Highway Code question (also to skip or give up on the current one), quiz_answer marks the "
                       "user's answer (a letter A to D or the answer text), quiz_score shows the running score.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "answer": {"type": "string", "description": "A letter A to D, or the answer's words."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"motoring_theory"}


def run_tool(name: str, args: dict, settings: Settings):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    return globals()[action](settings, args)


def _state(settings: Settings) -> dict:
    state = hs.load(settings, FILE, {})
    state.setdefault("pending", None)
    state.setdefault("score", [0, 0])
    state.setdefault("recent", [])
    return state


def _score(state: dict) -> str:
    right, asked = state["score"]
    return f"{right} of {asked}"


def _card(state: dict, question: str, choices: list[str], feedback: str = "") -> dict:
    options = [{"label": c, "say": f"Theory answer: {LETTERS[i]}, {c[:120]}"} for i, c in enumerate(choices)]
    return screen.card("motoring-quiz", "Theory test", "motoring-quiz", data={
        "question": question, "choices": options, "score": _score(state), "feedback": feedback},
        buttons=[{"label": "Skip", "say": "Next theory question."}, {"label": "Score", "say": "What's my theory score?"}])


def quiz_start(settings: Settings, args: dict) -> screen.Shown:
    return _ask(settings, _state(settings))


def _ask(settings: Settings, state: dict, feedback: str = "") -> screen.Shown:
    fresh = [i for i in range(len(data.QUESTIONS)) if i not in state["recent"]] or list(range(len(data.QUESTIONS)))
    n = RNG.choice(fresh)
    question, right, wrong, why = data.QUESTIONS[n]
    choices = [right, *wrong]
    RNG.shuffle(choices)
    state["recent"] = (state["recent"] + [n])[-len(data.QUESTIONS) + 1:]
    state["pending"] = {"n": n, "answer": LETTERS[choices.index(right)], "choices": choices}
    hs.save(settings, FILE, state)
    spoken = question + " " + " ".join(f"{LETTERS[i]}: {c}." for i, c in enumerate(choices))
    return screen.Shown((feedback + " " + spoken).strip(), _card(state, question, choices, feedback))


def _pick(pending: dict, answer) -> int | None:
    letter = re.match(r"\s*([a-dA-D])\s*(?:[,.:)]|$)", str(answer or ""))
    if letter:
        return "abcd".index(letter.group(1).lower())
    words = " ".join(re.sub(r"[^a-z0-9 ]+", " ", str(answer or "").lower()).split())
    for i, c in enumerate(pending["choices"]):
        if words and words == " ".join(re.sub(r"[^a-z0-9 ]+", " ", c.lower()).split()):
            return i
    return None


def quiz_answer(settings: Settings, args: dict) -> screen.Shown | str:
    state = _state(settings)
    pending = state["pending"]
    if not pending:
        return "There's no question waiting. Ask for a theory question first."
    picked = _pick(pending, args.get("answer"))
    if picked is None:
        raise ValueError("Answer with a letter A to D.")
    question, right, _, why = data.QUESTIONS[pending["n"]]
    correct = LETTERS[picked] == pending["answer"]
    state["score"] = [state["score"][0] + correct, state["score"][1] + 1]
    feedback = ("Correct. " if correct else f"Not quite; the answer is {pending['answer']}: {right}. ") + why
    return _ask(settings, state, feedback)


def quiz_score(settings: Settings, args: dict) -> screen.Shown | str:
    state = _state(settings)
    right, asked = state["score"]
    if not asked:
        return "You haven't answered any theory questions yet."
    percent = round(right / asked * 100)
    rows = [["Right", str(right)], ["Asked", str(asked)], ["Score", f"{percent}%"],
            ["Real test pass mark", "43 of 50 (86%)"]]
    return screen.Shown(f"You've got {right} of {asked} right, {percent} percent.",
                        screen.card("table", "Theory score", "motoring-score", columns=["", ""], rows=rows))
