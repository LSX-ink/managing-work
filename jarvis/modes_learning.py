"""Learning sessions: a language conversation partner at CEFR levels A1 to C1 with topic lists and a word list per
language (modes-words.json), a Socratic tutor that tracks questions asked and concepts understood per subject
(modes-tutor.json), and a quiz master where Alfred writes the questions and this keeps the score
(finished quizzes in modes-quizzes.json).
"""

import random

import homestore as hs
import modes
import screen
from config import Settings
from modes_data import LANGUAGE_TOPICS, LEVEL_NOTES, LEVELS

screen.EXTRA_KINDS.add("modes-scoreboard")

WORDS = "modes-words.json"
TUTOR = "modes-tutor.json"
QUIZZES = "modes-quizzes.json"
KEEP_QUIZZES = 100
KEEP_TUTOR_ITEMS = 200


def _level(level, default: str = "A2") -> str:
    level = hs.clean(level, 4).upper() or default
    if level not in LEVELS:
        raise ValueError(f"Levels are {', '.join(LEVELS)}.")
    return level


# ---- language partner ---------------------------------------------------------------------------------

def language_start(settings: Settings, language, level=None, topic=None) -> screen.Shown:
    language = hs.need(language, "language", 30).title()
    level = _level(level)
    topic = hs.clean(topic, 80) or random.choice(LANGUAGE_TOPICS[level])
    card = screen.card("text", f"{language} {level}: {topic}", "modes-language", text=f"Level {level}: {LEVEL_NOTES[level]}",
                       buttons=[{"label": "Other topics", "say": f"Show me {level} conversation topics."},
                                {"label": "My words", "say": f"Show my {language} word list."},
                                {"label": "Stop", "say": "Normal mode please."}])
    return modes.enter(
        settings, "language", "Language partner", f"{language} {level} - {topic}",
        f"Hold a conversation in {language} about '{topic}' at CEFR level {level} ({LEVEL_NOTES[level]}). Speak "
        f"mostly {language}, with a quick English hint only when they are stuck. Correct mistakes gently by "
        "repeating the right form. When you use a word that's likely new to them, explain it briefly and save it "
        f"with learning_session word_add (language {language}, word, meaning). Start with an easy opening question.",
        data={"language": language, "level": level, "topic": topic}, card=card)


def language_topics(settings: Settings, level=None) -> screen.Shown:
    current = modes.session(settings, "language") or {}
    level = _level(level, current.get("level", "A2"))
    lang = current.get("language", "")
    say = (lambda t: f"Change our {lang} conversation topic to {t}.") if lang else \
          (lambda t: f"Let's practise a language at {level} about {t}.")
    return screen.Shown(f"{level} topics: {', '.join(LANGUAGE_TOPICS[level])}.", screen.card(
        "list", f"Conversation topics {level}", "modes-language-topics",
        items=[{"label": t, "say": say(t)} for t in LANGUAGE_TOPICS[level]]))


def _words(settings: Settings) -> dict:
    return {k: [w for w in v if isinstance(w, dict)] for k, v in hs.load(settings, WORDS, {}).items() if isinstance(v, list)}


def _language_of(settings: Settings, language) -> str:
    language = hs.clean(language, 30).title() or (modes.session(settings, "language") or {}).get("language", "")
    if not language:
        raise ValueError("Which language?")
    return language


def word_add(settings: Settings, language, word, meaning=None) -> str:
    language = _language_of(settings, language)
    word = hs.need(word, "word", 80)
    words = _words(settings)
    found = words.setdefault(language, [])
    found[:] = [w for w in found if w.get("word", "").lower() != word.lower()]
    found.append({"word": word, "meaning": hs.clean(meaning, 160), "date": hs.today().isoformat()})
    hs.save(settings, WORDS, words)
    return f"Saved {word} to your {language} words; {len(found)} so far."


def word_list(settings: Settings, language=None) -> screen.Shown | str:
    words = _words(settings)
    language = hs.clean(language, 30).title() or (modes.session(settings, "language") or {}).get("language", "")
    if not language and len(words) == 1:
        language = next(iter(words))
    if language:
        key = hs.find(words, language)
        found = words.get(key or "", [])
        if not found:
            return f"No {language} words saved yet."
        return screen.Shown(f"{hs.plural(len(found), 'word')} in your {key} list.", screen.card(
            "table", f"{key} words", f"modes-words-{key}", columns=["Word", "Meaning", "Added"],
            rows=[[w["word"], w.get("meaning", ""), w.get("date", "")] for w in reversed(found)]))
    if not words:
        return "No words saved yet. They're saved during language practice."
    rows = [[lang, w["word"], w.get("meaning", "")] for lang, ws in words.items() for w in reversed(ws)]
    return screen.Shown(f"Saved words in {', '.join(words)}.", screen.card(
        "table", "My language words", "modes-words", columns=["Language", "Word", "Meaning"], rows=rows))


# ---- Socratic tutor ----------------------------------------------------------------------------------

def tutor_start(settings: Settings, subject, level=None) -> screen.Shown:
    subject = hs.need(subject, "subject", 80)
    level = hs.clean(level, 40) or "beginner"
    book = hs.load(settings, TUTOR, {})
    key = hs.find(book, subject) or subject.lower()
    entry = book.get(key) if isinstance(book.get(key), dict) else {"subject": subject, "questions": [], "concepts": []}
    entry.update(level=level, sessions=entry.get("sessions", 0) + 1)
    book[key] = entry
    hs.save(settings, TUTOR, book)
    known = ", ".join(c["concept"] for c in entry["concepts"][-8:])
    return modes.enter(
        settings, "tutor", "Socratic tutor", f"{subject} ({level})",
        f"Teach {subject} at {level} level with the Socratic method: ask one guiding question at a time instead of "
        "giving answers, build on their reasoning, and give a hint only when they're stuck. Log each key question "
        "you ask with learning_session tutor_log (question), and each concept they clearly understand with "
        "tutor_log (concept). " + (f"They already understand: {known}. Build from there." if known else
                                  "Start by finding out what they already know."),
        data={"subject": key})


def _tutor_key(settings: Settings, book: dict, subject) -> str:
    key = hs.find(book, subject) if hs.clean(subject) else (modes.session(settings, "tutor") or {}).get("subject")
    if not key or key not in book:
        raise ValueError("Which subject? Start tutoring first, e.g. 'tutor me in fractions'.")
    return key


def tutor_log(settings: Settings, subject=None, question=None, concept=None) -> str:
    book = hs.load(settings, TUTOR, {})
    entry = book[_tutor_key(settings, book, subject)]
    day = hs.today().isoformat()
    if hs.clean(question):
        entry["questions"] = (entry["questions"] + [{"question": hs.clean(question, 300), "date": day}])[-KEEP_TUTOR_ITEMS:]
    if hs.clean(concept) and all(c["concept"].lower() != hs.clean(concept).lower() for c in entry["concepts"]):
        entry["concepts"] = (entry["concepts"] + [{"concept": hs.clean(concept, 120), "date": day}])[-KEEP_TUTOR_ITEMS:]
    if not hs.clean(question) and not hs.clean(concept):
        raise ValueError("Give a question or a concept to log.")
    hs.save(settings, TUTOR, book)
    return f"Logged. {entry['subject']}: {hs.plural(len(entry['questions']), 'question')} asked, " \
           f"{hs.plural(len(entry['concepts']), 'concept')} understood."


def tutor_progress(settings: Settings, subject=None) -> screen.Shown | str:
    book = hs.load(settings, TUTOR, {})
    if not book:
        return "No tutoring yet."
    if not hs.clean(subject) and not modes.session(settings, "tutor"):
        rows = [[e["subject"], e.get("level", ""), str(len(e["questions"])), str(len(e["concepts"]))]
                for e in book.values() if isinstance(e, dict)]
        return screen.Shown(f"Tutoring in {', '.join(r[0] for r in rows)}.", screen.card(
            "table", "Tutoring progress", "modes-tutor", columns=["Subject", "Level", "Questions", "Concepts"], rows=rows))
    entry = book[_tutor_key(settings, book, subject)]
    items = [{"label": c["concept"], "done": True} for c in entry["concepts"]] + \
            [{"label": "Asked: " + q["question"]} for q in entry["questions"][-10:]]
    return screen.Shown(f"{entry['subject']}: {hs.plural(len(entry['concepts']), 'concept')} understood and "
                        f"{hs.plural(len(entry['questions']), 'question')} asked.",
                        screen.card("list", f"Tutor: {entry['subject']}", "modes-tutor", items=items,
                                    buttons=[{"label": "Carry on", "say": f"Tutor me in {entry['subject']}."}]))


# ---- quiz master ----------------------------------------------------------------------------------------

def _board(data: dict, recent: list, finished: bool = False) -> dict:
    return screen.card("modes-scoreboard", f"Quiz: {data['topic']}", "modes-quiz",
                       buttons=[] if finished else [{"label": "End quiz", "say": "End the quiz."}],
                       data={"topic": data["topic"], "correct": data["correct"], "asked": data["asked"],
                             "total": data["total"], "marks": [m["right"] for m in data["marks"]],
                             "finished": finished, "recent": recent[-5:][::-1]})


def _recent(settings: Settings) -> list:
    return [q for q in hs.load(settings, QUIZZES, []) if isinstance(q, dict)]


def quiz_start(settings: Settings, topic, total=None) -> screen.Shown:
    topic = hs.need(topic, "quiz topic", 80)
    total = int(hs.number(total if total is not None else 10, "number of questions", 1, 50))
    data = {"topic": topic, "total": total, "asked": 0, "correct": 0, "marks": []}
    return modes.enter(
        settings, "quiz", "Quiz master", f"{topic}, {total} questions",
        f"Run a {total}-question quiz on {topic}. Write your own questions, mixed difficulty, one at a time, and "
        "wait for each answer. After each answer say whether it's right (give the answer if not) and call "
        "learning_session quiz_mark (correct true or false, question). Don't keep score yourself; the tool does "
        "and tells you when the quiz is over.",
        data=data, card=_board(data, _recent(settings)))


def _finish(settings: Settings, data: dict) -> list:
    recent = _recent(settings)
    recent.append({"topic": data["topic"], "correct": data["correct"], "total": data["asked"],
                   "date": hs.today().isoformat()})
    hs.save(settings, QUIZZES, recent[-KEEP_QUIZZES:])
    modes.leave(settings)
    return recent


def quiz_mark(settings: Settings, correct, question=None) -> screen.Shown:
    data = modes.session(settings, "quiz")
    if not data:
        raise ValueError("No quiz is running. Say 'quiz me on' a topic to start one.")
    data["asked"] += 1
    data["correct"] += bool(correct)
    data["marks"].append({"question": hs.clean(question, 200), "right": bool(correct)})
    if data["asked"] >= data["total"]:
        recent = _finish(settings, data)
        return screen.Shown(f"Quiz over: {data['correct']} out of {data['total']}. Announce the final score warmly; "
                            "the quiz mode has ended.", _board(data, recent, True))
    modes.save_session(settings, data)
    return screen.Shown(f"Score {data['correct']} of {data['asked']}. Ask question {data['asked'] + 1} of {data['total']}.",
                        _board(data, _recent(settings)))


def quiz_board(settings: Settings) -> screen.Shown | str:
    data = modes.session(settings, "quiz")
    recent = _recent(settings)
    if data:
        return screen.Shown(f"{data['correct']} out of {data['asked']} so far, {data['total'] - data['asked']} to go.",
                            _board(data, recent))
    if not recent:
        return "No quizzes yet. Say 'be my quiz master on' a topic."
    last = recent[-1]
    done = {"topic": last["topic"], "correct": last["correct"], "asked": last["total"], "total": last["total"], "marks": []}
    return screen.Shown(f"Your last quiz, {last['topic']}: {last['correct']} out of {last['total']}.",
                        _board(done, recent, True))


def quiz_end(settings: Settings) -> screen.Shown | str:
    data = modes.session(settings, "quiz")
    if not data:
        return "No quiz is running."
    if not data["asked"]:
        modes.leave(settings)
        return "Quiz cancelled before any questions; back to normal mode."
    recent = _finish(settings, data)
    return screen.Shown(f"Quiz ended: {data['correct']} out of {data['asked']}. Back to normal mode.",
                        _board({**data, "total": data["asked"]}, recent, True))


# ---- tool -------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "learning_session",
        "description": "Language conversation partner: language_start (language, level A1-C1, topic), "
                       "language_topics (level), word_add (language, word, meaning) saves new vocabulary, word_list "
                       "(language). Socratic tutor: tutor_start (subject, level), tutor_log (question asked or "
                       "concept understood), tutor_progress (subject). Quiz master on any topic, you write the "
                       "questions and this keeps score: quiz_start (topic, questions), quiz_mark (correct, "
                       "question) after every answer, quiz_board = scoreboard, quiz_end.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "language_start", "language_topics", "word_add", "word_list", "tutor_start", "tutor_log",
                    "tutor_progress", "quiz_start", "quiz_mark", "quiz_board", "quiz_end"]},
                "language": {"type": "string"},
                "level": {"type": "string", "description": "Language: A1, A2, B1, B2 or C1. Tutor: any, e.g. 'GCSE'."},
                "topic": {"type": "string"},
                "word": {"type": "string"},
                "meaning": {"type": "string"},
                "subject": {"type": "string"},
                "question": {"type": "string"},
                "concept": {"type": "string"},
                "questions": {"type": "integer", "description": "quiz_start: how many, default 10."},
                "correct": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"learning_session"}
modes.STARTERS["language"] = lambda settings, topic: language_start(settings, topic) if topic else None
modes.STARTERS["tutor"] = lambda settings, topic: tutor_start(settings, topic) if topic else None
modes.STARTERS["quiz"] = lambda settings, topic: quiz_start(settings, topic or "general knowledge")


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "language_start":
        return language_start(settings, args.get("language"), args.get("level"), args.get("topic"))
    if action == "language_topics":
        return language_topics(settings, args.get("level"))
    if action == "word_add":
        return word_add(settings, args.get("language"), args.get("word"), args.get("meaning"))
    if action == "word_list":
        return word_list(settings, args.get("language"))
    if action == "tutor_start":
        return tutor_start(settings, args.get("subject") or args.get("topic"), args.get("level"))
    if action == "tutor_log":
        return tutor_log(settings, args.get("subject"), args.get("question"), args.get("concept"))
    if action == "tutor_progress":
        return tutor_progress(settings, args.get("subject"))
    if action == "quiz_start":
        return quiz_start(settings, args.get("topic") or args.get("subject"), args.get("questions"))
    if action == "quiz_mark":
        return quiz_mark(settings, args.get("correct") is True, args.get("question"))
    if action == "quiz_board":
        return quiz_board(settings)
    if action == "quiz_end":
        return quiz_end(settings)
    raise ValueError("Unknown learning session action.")
