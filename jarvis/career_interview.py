"""Interview preparation: a question bank by type, one random question, a STAR answer planner saved per question,
and a salary negotiation script. (Alfred asking a whole mock interview is in modes_practice.py; this reuses its bank.)

STAR answers pop up as a "career-star" window (frontend/popup-career.js). Kept in career-star.json; the script
reads the brag file (career-brag.json) for evidence.
"""

import random

import career_store as cs
import screen
from config import Settings
from modes_data import INTERVIEW_QUESTIONS

KIND = "career-star"
screen.EXTRA_KINDS.add(KIND)
COMPETENCY = [
    "Give an example of when you worked well in a team.",
    "Describe a time you had to meet a tight deadline.",
    "Tell me about a time you showed leadership.",
    "How have you handled a disagreement with a colleague?",
    "Describe a time you took the initiative.",
    "Tell me about a time you had to learn something quickly.",
    "Give an example of when you went the extra mile for a customer.",
    "Describe a time you managed several priorities at once.",
    "Tell me about a mistake you made and what you did about it.",
    "Give an example of when you had to persuade someone.",
    "Describe a time you improved a process.",
    "Tell me about a time you dealt with a difficult person.",
    "Give an example of when you used data to make a decision.",
    "Describe a time you coped with change at work.",
    "Tell me about a time you communicated something complicated clearly.",
]
BANK = {**INTERVIEW_QUESTIONS, "competency": COMPETENCY}
PARTS = ["situation", "task", "action", "result"]
ACTIONS = ["question_bank", "question", "star_save", "star_show", "star_list", "negotiation_script"]


def _bank(kind) -> tuple[str, list[str]]:
    text = cs.clean(kind).lower()
    if not text:
        return "all", [q for qs in BANK.values() for q in qs]
    if text not in BANK:
        raise ValueError(f"Question types are {', '.join(BANK)}.")
    return text, BANK[text]


def question_bank(args: dict) -> screen.Shown:
    kind, questions = _bank(args.get("type"))
    items = [{"label": q, "say": f"Plan a STAR answer for: {q}"} for q in questions]
    return screen.Shown(f"{len(questions)} {kind} interview questions are on the screen. Tap one to plan an answer.",
                        screen.card("list", f"Interview questions: {kind}", f"career-questions-{kind}", items=items,
                                    buttons=[{"label": "Ask me one", "say": f"Ask me one {kind if kind != 'all' else ''} interview question."}]))


def question(settings: Settings, args: dict) -> screen.Shown:
    kind, questions = _bank(args.get("type"))
    q = random.choice(questions)
    saved = " You've already planned an answer for it." if _star(settings, q) else ""
    return screen.Shown(f"{q}{saved}", screen.card(
        "text", "Interview question", "career-question", text=q,
        buttons=[{"label": "Plan a STAR answer", "say": f"Plan a STAR answer for: {q}"},
                 {"label": "Another", "say": f"Ask me another {kind if kind != 'all' else ''} interview question."}]))


def _all(settings: Settings) -> dict:
    return {k: v for k, v in cs.load(settings, cs.STAR, {}).items() if isinstance(v, dict)}


def _star(settings: Settings, q: str) -> dict | None:
    found = _all(settings)
    key = cs.find(found, q)
    return found[key] if key else None


def _star_card(q: str, e: dict) -> screen.Shown:
    done = sum(bool(e.get(p)) for p in PARTS)
    return screen.Shown(f"STAR plan for that question: {done} of 4 parts filled in.", screen.card(
        KIND, "STAR answer", f"career-star-{q}"[:60], data={"question": q, **{p: e.get(p, "") for p in PARTS}},
        buttons=[{"label": "All my answers", "say": "Show my saved STAR answers."}]))


def star_save(settings: Settings, args: dict) -> screen.Shown:
    q = cs.need(args.get("question"), "interview question", 200)
    found = _all(settings)
    key = cs.find(found, q) or q
    entry = found.setdefault(key, {})
    given = False
    for part in PARTS:
        if cs.clean(args.get(part), 600):
            entry[part] = cs.clean(args.get(part), 600)
            given = True
    if not given:
        raise ValueError("Give at least one of situation, task, action or result.")
    if len(found) > cs.MAX_ROWS:
        raise ValueError("That's plenty of saved answers; remove some first.")
    cs.save(settings, cs.STAR, found)
    return _star_card(key, entry)


def star_show(settings: Settings, args: dict) -> screen.Shown:
    found = _all(settings)
    key = cs.find(found, cs.need(args.get("question"), "interview question", 200))
    if key is None:
        raise ValueError("I haven't saved a STAR answer for that question.")
    return _star_card(key, found[key])


def star_list(settings: Settings) -> screen.Shown | str:
    found = _all(settings)
    if not found:
        return "No STAR answers saved yet. Pick a question and I'll help you plan one."
    items = [{"label": f"{q} ({sum(bool(e.get(p)) for p in PARTS)}/4)", "say": f"Show my STAR answer for: {q}"}
             for q, e in found.items()]
    return screen.Shown(f"You have {len(found)} STAR answers saved.", screen.card(
        "list", "My STAR answers", "career-star-list", items=items))


def _money(value) -> float | None:
    text = cs.clean(value).lower().replace("£", "").replace(",", "")
    if not text:
        return None
    mult = 1000 if text.endswith("k") else 1
    try:
        return float(text.rstrip("k")) * mult
    except ValueError:
        raise ValueError("Give salaries as numbers, like 42000 or 42k.") from None


def _pounds(n: float) -> str:
    return f"£{round(n):,}"


def negotiation_script(settings: Settings, args: dict) -> screen.Shown:
    role = cs.clean(args.get("role"), 60) or "the role"
    target, offer = _money(args.get("target")), _money(args.get("offer"))
    if not target:
        raise ValueError("What salary are you aiming for?")
    wins = [w.get("win", "") for w in cs.load(settings, cs.BRAG, []) if isinstance(w, dict)][-3:]
    ask = f"{_pounds(target)}" + (f", against the {_pounds(offer)} offered, which is {round((target - offer) / offer * 100)}% more" if offer else "")
    lines = [
        f"1. Thank them: \"Thank you, I'm really excited about {role}.\"",
        f"2. Make the ask: \"Based on my experience and the market, I was hoping for {ask}.\"",
        "3. Back it up: " + ("\"For example, " + "; ".join(w for w in wins if w) + ".\"" if any(wins)
                              else "name two or three results you delivered (add them to your brag file)."),
        "4. Then stay quiet and let them respond.",
        "5. If they can't move on base pay: \"Could we look at a bonus, extra holiday, a review after six months, "
        "training budget or flexible working?\"",
        "6. Close: \"If we can get to that, I'm happy to accept today.\"",
    ]
    floor = " Your walk-away point should be decided before you call." if offer else ""
    return screen.Shown(f"Here's your negotiation script for {role}, aiming for {_pounds(target)}.{floor}", screen.card(
        "text", "Salary negotiation script", "career-negotiation", text="\n\n".join(lines),
        buttons=[{"label": "Compare offers", "say": "Compare my job offers."}]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "career_interview",
        "description": "Job interview preparation. Actions: question_bank (list of common interview questions by type: "
                       "behavioural, competency, strengths, situational, technical); question (ask one random "
                       "question); star_save (plan and save a STAR answer for a question: situation, task, action, "
                       "result); star_show (one saved answer) and star_list (all of them); negotiation_script "
                       "(salary negotiation practice script from a target and optional offer; uses the brag file).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "type": {"type": "string", "enum": list(BANK)},
                "question": {"type": "string"},
                "situation": {"type": "string"},
                "task": {"type": "string"},
                "action_taken": {"type": "string", "description": "What the user did (the A in STAR)."},
                "result": {"type": "string"},
                "role": {"type": "string"},
                "target": {"type": "string", "description": "Salary aimed for, e.g. 45000 or 45k."},
                "offer": {"type": "string", "description": "Salary offered, if there is one."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"career_interview"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    args = {**args, "action": args.get("action_taken")}
    if action == "question_bank":
        return question_bank(args)
    if action == "question":
        return question(settings, args)
    if action == "star_save":
        return star_save(settings, args)
    if action == "star_show":
        return star_show(settings, args)
    if action == "star_list":
        return star_list(settings)
    if action == "negotiation_script":
        return negotiation_script(settings, args)
    raise ValueError("Try question_bank, question, star_save, star_show, star_list or negotiation_script.")
