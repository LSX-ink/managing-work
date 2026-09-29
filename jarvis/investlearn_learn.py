"""Investing basics part 2: learning path with quizzes, glossary, jargon buster, myths, scams, UK wrappers, risk categories.

Education only: nothing here says what to buy or sell. The risk questionnaire only explains categories. UK rules are
general information: check GOV.UK for the current limits. Progress is saved in investlearn.json.
"""

import re

import homestore as hs
import investlearn_data as data
import investlearn_lessons as les
import investlearn_store as st
import screen
from config import Settings

NAMES = {"invest_learn"}
LETTERS = "ABC"
NOT_ADVICE = "General education only, not financial advice."
RISK_FOOT = "This only explains categories. It is not advice and not a product recommendation."


def _lesson(value) -> tuple[int, dict]:
    text = hs.clean(value).lower()
    if not text:
        raise ValueError("Which lesson? Ask for the learning path to see them.")
    if text.isdigit() and 1 <= int(text) <= len(les.LESSONS):
        i = int(text) - 1
        return i, les.LESSONS[i]
    for i, lesson in enumerate(les.LESSONS):
        if text in (lesson["id"], lesson["title"].lower()) or text.replace(" ", "-") in lesson["id"] or text in lesson["title"].lower():
            return i, lesson
    raise ValueError("I can't find that lesson. Ask for the learning path to see them.")


def _correct(record: dict, lesson: dict) -> int:
    return sum(1 for q, pick in record.get("answers", {}).items()
               if q.isdigit() and int(q) <= len(lesson["quiz"]) and lesson["quiz"][int(q) - 1][2] == pick)


def _text(title: str, card_id: str, body: str, buttons=None) -> dict:
    return screen.card("text", title, card_id, text=body, buttons=buttons)


def lesson_list(settings: Settings, args: dict):
    d = st.load(settings)
    items = []
    for i, lesson in enumerate(les.LESSONS, 1):
        read = "read" if d["lessons"].get(lesson["id"]) else "not read"
        score = _correct(d["quizzes"].get(lesson["id"], {}), lesson)
        items.append({"label": f"{i}. {lesson['title']} ({read}, quiz {score}/{len(lesson['quiz'])})", "say": f"Teach me lesson {i}: {lesson['title']}."})
    done = sum(1 for lesson in les.LESSONS if d["lessons"].get(lesson["id"]))
    return screen.Shown(f"Your investing learning path has {len(les.LESSONS)} short lessons; you've read {done}. {NOT_ADVICE}",
                        screen.card("list", "Investing learning path", "investlearn-path", items=items,
                                    buttons=[{"label": "Progress", "say": "Show my investing learning progress."}]))


def lesson(settings: Settings, args: dict):
    i, item = _lesson(args.get("lesson"))
    d = st.load(settings)
    d["lessons"][item["id"]] = True
    st.save(settings, d)
    body = "\n\n".join(item["body"]) + f"\n\n{NOT_ADVICE} {st.CHECK}"
    buttons = [{"label": "Quiz me", "say": f"Quiz me on lesson {i + 1}."}]
    if i + 1 < len(les.LESSONS):
        buttons.append({"label": "Next lesson", "say": f"Teach me lesson {i + 2}."})
    return screen.Shown(f"Lesson {i + 1}, {item['title']}: {item['body'][0]}", _text(f"Lesson {i + 1}: {item['title']}", f"investlearn-lesson-{item['id']}", body, buttons))


def _question(i: int, item: dict, q: int) -> screen.Shown:
    text, options, _answer, _why = item["quiz"][q - 1]
    items = [{"label": f"{LETTERS[k]}. {o}", "say": f"Answer {LETTERS[k]} for question {q} of the {item['title']} quiz."} for k, o in enumerate(options)]
    return screen.Shown(f"Question {q} of {len(item['quiz'])}: {text} " + " ".join(f"{LETTERS[k]}, {o}." for k, o in enumerate(options)),
                        screen.card("list", f"Quiz {i + 1}: {item['title']} ({q}/{len(item['quiz'])})", f"investlearn-quiz-{item['id']}", items=items))


def quiz(settings: Settings, args: dict):
    i, item = _lesson(args.get("lesson"))
    record = st.load(settings)["quizzes"].get(item["id"], {})
    answered = record.get("answers", {})
    default = next((q for q in range(1, len(item["quiz"]) + 1) if str(q) not in answered), 1)
    q = int(st.num(args, "question", "question number", default, 1, len(item["quiz"])))
    return _question(i, item, q)


def _pick(value) -> int:
    text = hs.clean(value).upper()
    if text in ("A", "B", "C"):
        return LETTERS.index(text)
    if text in ("1", "2", "3"):
        return int(text) - 1
    raise ValueError("Answer with A, B or C.")


def answer(settings: Settings, args: dict):
    i, item = _lesson(args.get("lesson"))
    q = int(st.num(args, "question", "question number", None, 1, len(item["quiz"])))
    pick = _pick(args.get("choice"))
    text, options, right, why = item["quiz"][q - 1]
    d = st.load(settings)
    record = d["quizzes"].setdefault(item["id"], {"answers": {}})
    record["answers"][str(q)] = pick
    st.save(settings, d)
    ok = pick == right
    lead = "Correct." if ok else f"Not quite, the answer is {LETTERS[right]}, {options[right]}."
    score = _correct(record, item)
    buttons = []
    if q < len(item["quiz"]):
        buttons.append({"label": "Next question", "say": f"Next question of the {item['title']} quiz."})
        tail = ""
    else:
        tail = f" Quiz finished: {score} of {len(item['quiz'])}."
        if i + 1 < len(les.LESSONS):
            buttons.append({"label": "Next lesson", "say": f"Teach me lesson {i + 2}."})
    return screen.Shown(f"{lead} {why}{tail}", _text(f"Quiz {i + 1}: {item['title']}", f"investlearn-answer-{item['id']}",
                                                     f"{lead}\n\n{why}\n\nScore so far: {score} of {len(item['quiz'])}.", buttons))


def progress(settings: Settings, args: dict):
    d = st.load(settings)
    rows = []
    for i, item in enumerate(les.LESSONS, 1):
        read = 1 if d["lessons"].get(item["id"]) else 0
        score = _correct(d["quizzes"].get(item["id"], {}), item)
        rows.append({"label": f"{i}. {item['title']}", "value": read + score, "max": 1 + len(item["quiz"]),
                     "text": f"{'read' if read else 'unread'}, quiz {score}/{len(item['quiz'])}", "say": f"Teach me lesson {i}."})
    got = sum(r["value"] for r in rows)
    total = sum(r["max"] for r in rows)
    return screen.Shown(f"You're {round(100 * got / total)} percent through the investing basics path.",
                        st.bars_card("Learning progress", "investlearn-progress", rows, NOT_ADVICE))


def glossary(settings: Settings, args: dict):
    term = hs.clean(args.get("term")).lower()
    if not term:
        items = [{"label": t, "say": f"What does {t} mean in investing?"} for t in sorted(data.GLOSSARY)]
        return screen.Shown(f"The investing glossary has {len(items)} words. Tap one.",
                            screen.card("list", "Investing glossary", "investlearn-glossary", items=items))
    found = hs.find(data.GLOSSARY, term)
    if found is None:
        near = sorted(k for k in data.GLOSSARY if term in k or term in data.GLOSSARY[k].lower())[:8]
        if not near:
            raise ValueError(f"I don't have {term} in the glossary yet.")
        return screen.Shown(f"I found {len(near)} related words.", screen.card("list", f"Glossary: {term}", "investlearn-glossary-search",
                                                                             items=[{"label": t, "say": f"What does {t} mean in investing?"} for t in near]))
    return screen.Shown(f"{found}: {data.GLOSSARY[found]}",
                        _text(found.title(), f"investlearn-term-{found}", f"{data.GLOSSARY[found]}\n\n{NOT_ADVICE}"))


def flashcards(settings: Settings, args: dict):
    count = int(st.num(args, "count", "number of cards", 10, 1, 30))
    terms = sorted(data.GLOSSARY)
    start = int(st.num(args, "start", "start position", hs.today().toordinal() % len(terms), 0, len(terms) - 1))
    picked = [terms[(start + k) % len(terms)] for k in range(count)]
    return screen.Shown(f"Here are {count} glossary flash cards. Tap a card to see the meaning.",
                        st.cards_card("Glossary flash cards", "investlearn-flashcards", [(t, data.GLOSSARY[t]) for t in picked], NOT_ADVICE))


def jargon_buster(settings: Settings, args: dict):
    text = hs.clean(args.get("text"), 2000).lower()
    if not text:
        raise ValueError("Give me the sentence or paragraph with the jargon in it.")
    found = [t for t in sorted(data.GLOSSARY, key=len, reverse=True) if re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", text)]
    if not found:
        raise ValueError("I didn't spot any jargon I know in that. Try asking about a single word.")
    return screen.Shown(f"I found {len(found)} jargon words in that and put plain meanings on screen.",
                        screen.card("list", "Jargon buster", "investlearn-jargon", items=[{"label": f"{t}: {data.GLOSSARY[t]}", "say": f"Tell me more about {t}."} for t in found[:30]]))


def myths(settings: Settings, args: dict):
    return screen.Shown("Investing myths against facts are on screen. Tap a card to flip it.",
                        st.cards_card("Myth or fact", "investlearn-myths", [(f"Myth: {m}", f"Fact: {f}") for m, f in data.MYTHS], NOT_ADVICE))


def scam_warnings(settings: Settings, args: dict):
    text = "Investment scam warning signs are on screen. Check any firm on the FCA Register before anything else."
    return screen.Shown(text, st.cards_card("Investment scam warnings", "investlearn-scams", list(data.SCAMS),
                                            "Check the FCA Register (register.fca.org.uk) using contact details you find yourself. Report scams to Action Fraud.",
                                            [{"label": "Scam check", "say": "Run the investment scam checklist."}]))


def scam_check(settings: Settings, args: dict):
    answers = args.get("answers")
    if not isinstance(answers, list) or not answers:
        items = [{"label": q, "say": "Run the scam check: here are my answers."} for q in data.SCAM_CHECKS]
        return screen.Shown("Answer these six yes or no questions about the offer and I'll count the red flags.",
                            screen.card("list", "Investment scam checklist", "investlearn-scam-check", items=items))
    flags = sum(1 for a in answers[:len(data.SCAM_CHECKS)] if a is True or str(a).lower() in ("yes", "true", "y"))
    if flags >= 3:
        verdict = "Several red flags: treat this as a likely scam, do not pay anything, and check the FCA Register."
    elif flags:
        verdict = "Some red flags. Slow down, check the firm on the FCA Register with details you find yourself, and talk to someone you trust."
    else:
        verdict = "No red flags from these questions, but that does not prove it is safe. Always check the FCA Register."
    return screen.Shown(f"{flags} red flags. {verdict}", _text("Scam check result", "investlearn-scam-result", f"{flags} of {len(data.SCAM_CHECKS)} red flags.\n\n{verdict}\n\nNot financial advice. Report scams to Action Fraud."))


def wrappers(settings: Settings, args: dict):
    name = hs.clean(args.get("name")).lower()
    if not name:
        items = [{"label": w.title(), "say": f"Explain {w} in plain words."} for w in data.WRAPPERS]
        return screen.Shown(f"Ten UK account types explained in plain words. {st.CHECK}",
                            screen.card("list", "UK savings and investing wrappers", "investlearn-wrappers", items=items))
    found = hs.find(data.WRAPPERS, name)
    if found is None:
        raise ValueError("I don't know that one. Ask for the list of UK wrappers.")
    return screen.Shown(f"{found.title()}: {data.WRAPPERS[found]} {st.CHECK}",
                        _text(found.title(), f"investlearn-wrapper-{found.replace(' ', '-')}", f"{data.WRAPPERS[found]}\n\n{st.CHECK}\n\n{NOT_ADVICE}"))


def _risk_next(record: dict) -> screen.Shown:
    answers = record.get("answers", {})
    q = next((k for k in range(1, len(data.RISK_QUESTIONS) + 1) if str(k) not in answers), None)
    if q is None:
        return _risk_result(record)
    text, options = data.RISK_QUESTIONS[q - 1]
    items = [{"label": f"{LETTERS[k]}. {o}", "say": f"Risk question {q}: answer {LETTERS[k]}."} for k, o in enumerate(options)]
    return screen.Shown(f"Risk question {q} of {len(data.RISK_QUESTIONS)}: {text}",
                        screen.card("list", f"Risk categories quiz ({q}/{len(data.RISK_QUESTIONS)})", "investlearn-risk-quiz", items=items))


def _risk_result(record: dict) -> screen.Shown:
    score = sum(record["answers"].values())
    level = "cautious" if score <= 4 else "balanced" if score <= 8 else "adventurous"
    body = f"Your answers fit the {level} category.\n\n{data.RISK_LEVELS[level]}\n\n{RISK_FOOT} {NOT_ADVICE}"
    return screen.Shown(f"Your answers fit the {level} category. {RISK_FOOT}",
                        _text(f"Risk category: {level}", "investlearn-risk-result", body,
                              [{"label": "Retake", "say": "Restart the risk categories quiz."}, {"label": "Risk explained", "say": "Explain risk and reward."}]))


def risk_quiz(settings: Settings, args: dict):
    d = st.load(settings)
    if args.get("restart") or args.get("confirmed"):
        d["risk"] = {}
        st.save(settings, d)
    return _risk_next(d["risk"])


def risk_answer(settings: Settings, args: dict):
    d = st.load(settings)
    q = int(st.num(args, "question", "question number", None, 1, len(data.RISK_QUESTIONS)))
    d["risk"].setdefault("answers", {})[str(q)] = _pick(args.get("choice"))
    st.save(settings, d)
    return _risk_next(d["risk"])


def explain(settings: Settings, args: dict):
    topic = hs.clean(args.get("topic")).lower().replace(" ", "_").replace("-", "_")
    if topic not in data.EXPLAINERS:
        raise ValueError("Topics: " + ", ".join(data.EXPLAINERS) + ".")
    title, parts = data.EXPLAINERS[topic]
    body = "\n\n".join(parts) + f"\n\n{NOT_ADVICE} {st.CHECK}"
    return screen.Shown(f"{title}: {parts[0]}", _text(title, f"investlearn-explain-{topic}", body))


def reset_progress(settings: Settings, args: dict):
    if args.get("confirmed") is not True:
        return st.confirm_needed("resetting the learning progress and risk answers")
    d = st.load(settings)
    d["lessons"], d["quizzes"], d["risk"] = {}, {}, {}
    st.save(settings, d)
    return "Learning progress reset."


ACTIONS = {"lesson_list": lesson_list, "lesson": lesson, "quiz": quiz, "answer": answer, "progress": progress,
           "glossary": glossary, "flashcards": flashcards, "jargon_buster": jargon_buster, "myths": myths,
           "scam_warnings": scam_warnings, "scam_check": scam_check, "wrappers": wrappers, "risk_quiz": risk_quiz,
           "risk_answer": risk_answer, "explain": explain, "reset_progress": reset_progress}


def tool_definitions() -> list[dict]:
    return [{
        "name": "invest_learn",
        "description": "Learn about investing in plain words: education only, never advice on what to buy. action: lesson_list = beginner "
                       "learning path / lesson (lesson number or name) / quiz (lesson, question) / answer (lesson, question, choice A-C) / "
                       "progress / glossary (term, or none for the list of ~70 investing words) / flashcards (count) / jargon_buster (text "
                       "with jargon to explain) / myths = myth vs fact cards / scam_warnings = FCA register, clone firms, guaranteed returns / "
                       "scam_check (answers = list of yes/no for the six questions) / wrappers (name: ISA, LISA, pension, SIPP, premium "
                       "bonds...) / risk_quiz (restart) and risk_answer (question, choice) = a questionnaire that only explains categories / "
                       "explain (topic: pound_cost_averaging, four_percent, diversification, risk, compound, inflation, fees, "
                       "emergency_fund, time_horizon, pensions) / reset_progress (confirmed only after yes).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(ACTIONS)},
                "lesson": {"type": "string"}, "question": {"type": "integer"}, "choice": {"type": "string"},
                "term": {"type": "string"}, "text": {"type": "string"}, "name": {"type": "string"},
                "topic": {"type": "string", "enum": list(data.EXPLAINERS)},
                "count": {"type": "integer"}, "start": {"type": "integer"},
                "answers": {"type": "array", "items": {"type": "boolean"}},
                "restart": {"type": "boolean"}, "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = ACTIONS.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
