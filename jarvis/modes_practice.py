"""Practice sessions: job interview practice from a bank of 60 questions (answers and Alfred's feedback saved to
modes-interviews.json), the STAR method, timing a talk with words per minute (modes-talks.json), counting
filler words in a transcript, and role-play scenarios such as ordering at a restaurant or asking for a raise.
"""

import random
import re

import homestore as hs
import modes
import screen
from config import Settings
from modes_data import FILLERS, INTERVIEW_QUESTIONS, QUESTION_TYPES, ROLEPLAYS, STAR

INTERVIEWS = "modes-interviews.json"
TALKS = "modes-talks.json"
KEEP_SESSIONS = 50
KEEP_TALKS = 100
WORD = re.compile(r"[A-Za-z0-9']+")


# ---- job interview practice ----------------------------------------------------------------------

def _load_log(settings: Settings) -> list:
    return [s for s in hs.load(settings, INTERVIEWS, []) if isinstance(s, dict)]


def interview_start(settings: Settings, role=None, level=None, qtype=None) -> screen.Shown:
    role = hs.clean(role, 80) or "a general"
    level = hs.clean(level, 40)
    qtype = hs.clean(qtype, 20).lower()
    if qtype and qtype not in QUESTION_TYPES:
        raise ValueError(f"Question types are {', '.join(QUESTION_TYPES)}.")
    order = [[t, i] for t in ((qtype,) if qtype else QUESTION_TYPES) for i in range(len(INTERVIEW_QUESTIONS[t]))]
    random.shuffle(order)
    started = modes.stamp()
    log = _load_log(settings)
    log.append({"started": started, "role": role, "level": level, "entries": []})
    hs.save(settings, INTERVIEWS, log[-KEEP_SESSIONS:])
    job = f"{level + ' ' if level else ''}{role} role".strip()
    modes.enter(settings, "interviewer", "Interviewer", f"Practice for a {job}",
                f"You are interviewing the user for a {job}. For each question call practice_session "
                "interview_next (you may adapt its wording to the role), ask it, and listen to the whole answer. "
                "Then call practice_session interview_feedback with a one-line summary of their answer and "
                "two or three sentences of specific, kind feedback, and say that feedback aloud. For behavioural "
                "questions remind them of the STAR method.",
                data={"started": started, "order": order, "asked": 0, "current": None})
    first = interview_next(settings)
    return screen.Shown(f"{modes.load_state(settings)['instructions']} {first}", first.card)


def _interview(settings: Settings) -> dict:
    data = modes.session(settings, "interviewer")
    if not data or "order" not in data:
        raise ValueError("Start interview practice first, e.g. 'practise a job interview for a nurse role'.")
    return data


def interview_next(settings: Settings) -> screen.Shown | str:
    data = _interview(settings)
    if data["asked"] >= len(data["order"]):
        return "That's every question in the bank for this practice. Offer to show the log or stop."
    qtype, index = data["order"][data["asked"]]
    question = INTERVIEW_QUESTIONS[qtype][index]
    data["asked"] += 1
    data["current"] = {"type": qtype, "question": question}
    modes.save_session(settings, data)
    buttons = [{"label": "Next question", "say": "Next interview question please."},
               {"label": "End practice", "say": "Stop the interview practice."}]
    if qtype == "behavioural":
        buttons.insert(0, {"label": "STAR tips", "say": "Show me the STAR method."})
    return screen.Shown(f"Question {data['asked']} ({qtype}): {question} Ask it now and wait for the answer.",
                        screen.card("text", f"Question {data['asked']} - {qtype}", "modes-interview-q",
                                    text=question, buttons=buttons))


def interview_feedback(settings: Settings, answer, feedback, score=None) -> str:
    data = _interview(settings)
    if not data.get("current"):
        raise ValueError("Ask a question with interview_next first.")
    entry = {**data["current"], "answer": hs.need(answer, "answer summary", 600),
             "feedback": hs.need(feedback, "feedback", 1000)}
    if score is not None:
        entry["score"] = int(hs.number(score, "score", 1, 5))
    log = _load_log(settings)
    session = next((s for s in reversed(log) if s.get("started") == data["started"]), None)
    if session is None:
        raise ValueError("I've lost this practice's log; start interview practice again.")
    session["entries"].append(entry)
    hs.save(settings, INTERVIEWS, log)
    return f"Saved answer {len(session['entries'])}. Give the feedback aloud, then ask if they're ready for the next question."


def interview_log(settings: Settings) -> screen.Shown | str:
    log = [s for s in _load_log(settings) if s.get("entries")]
    if not log:
        return "No interview answers saved yet."
    last = log[-1]
    rows = [[e.get("question", ""), e.get("answer", ""), e.get("feedback", ""), str(e.get("score", ""))]
            for e in last["entries"]]
    return screen.Shown(f"{hs.plural(len(rows), 'answer')} from your last practice for {last.get('role')}.",
                        screen.card("table", f"Interview practice {last['started'][:10]}", "modes-interview-log",
                                    columns=["Question", "Your answer", "Feedback", "Score"], rows=rows))


def star_tip() -> screen.Shown:
    return screen.Shown("The STAR method: Situation, Task, Action, Result. It's on the screen.",
                        screen.card("text", "STAR method", "modes-star", text=STAR))


# ---- presentation rehearsal ---------------------------------------------------------------------

def _talks(settings: Settings) -> dict:
    found = hs.load(settings, TALKS, {})
    return {"running": found.get("running") if isinstance(found.get("running"), dict) else None,
            "talks": [t for t in found.get("talks") or [] if isinstance(t, dict)]}


def talk_start(settings: Settings, title=None) -> screen.Shown:
    data = _talks(settings)
    data["running"] = {"title": hs.clean(title, 80) or "Talk", "started": modes.stamp()}
    hs.save(settings, TALKS, data)
    started = modes.now().timestamp() * 1000
    return screen.Shown("Timing your talk; off you go. Say 'stop the talk timer' when you finish.", screen.card(
        "timer", f"Rehearsing: {data['running']['title']}", "modes-talk", started_at=started,
        buttons=[{"label": "Stop timing", "say": "Stop the talk timer."}]))


def _clock(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def talk_stop(settings: Settings, text=None) -> screen.Shown:
    data = _talks(settings)
    if not data["running"]:
        raise ValueError("The talk timer isn't running. Say 'time my talk' to start it.")
    seconds = modes._minutes(data["running"]["started"], modes.stamp()) * 60
    words = len(WORD.findall(str(text or "")))
    wpm = round(words / (seconds / 60)) if words and seconds >= 5 else None
    talk = {"title": data["running"]["title"], "date": data["running"]["started"][:10], "seconds": round(seconds),
            "words": words, "wpm": wpm}
    data["talks"] = (data["talks"] + [talk])[-KEEP_TALKS:]
    data["running"] = None
    hs.save(settings, TALKS, data)
    said = f"That took {_clock(seconds)}."
    if wpm:
        pace = "a bit fast" if wpm > 170 else "a bit slow" if wpm < 110 else "a comfortable pace"
        said += f" {words} words is {wpm} words a minute, {pace}; 130 to 160 is typical."
    rows = [[t["date"], t["title"], _clock(t["seconds"]), str(t.get("wpm") or "")] for t in reversed(data["talks"][-10:])]
    return screen.Shown(said, screen.card("table", "Talk rehearsals", "modes-talk",
                                          columns=["Date", "Talk", "Time", "Words/min"], rows=rows))


def filler_count(transcript) -> screen.Shown:
    text = hs.need(transcript, "transcript", 100_000).lower()
    words = max(1, len(WORD.findall(text)))
    counts = {f: len(re.findall(rf"\b{re.escape(f)}\b", text)) for f in FILLERS}
    counts = {f: n for f, n in counts.items() if n}
    total = sum(counts.values())
    if not total:
        return screen.Shown("No filler words at all. Impressive.",
                            screen.card("text", "Filler words", "modes-fillers", text=f"0 fillers in {words} words."))
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    rate = total * 100 / words
    top = ", ".join(f"{f} {n}" for f, n in ranked[:3])
    return screen.Shown(f"{total} filler words in {words}, about {rate:.1f} per hundred words. Most: {top}.",
                        screen.card("chart", "Filler words", "modes-fillers",
                                    text=f"{total} in {words} words ({rate:.1f} per 100). 'Like' counts every use.",
                                    chart={"type": "bar", "labels": [f for f, _ in ranked],
                                           "values": [n for _, n in ranked]}))


# ---- role-play ---------------------------------------------------------------------------------------

def roleplay_list() -> screen.Shown:
    items = [{"label": f"{name} ({level}): {goals}", "say": f"Start the role-play: {name}."}
             for name, (_, goals, level) in ROLEPLAYS.items()]
    return screen.Shown(f"{len(items)} role-plays, from ordering at a restaurant to asking for a raise. Pick one.",
                        screen.card("list", "Role-play scenarios", "modes-roleplays", items=items))


def roleplay_start(settings: Settings, scenario=None, difficulty=None) -> screen.Shown:
    if not hs.clean(scenario):
        return roleplay_list()
    name = hs.find(ROLEPLAYS, scenario)
    if name:
        role, goals, level = ROLEPLAYS[name]
    else:
        name, role, goals, level = hs.clean(scenario, 80), "whoever fits the scene", "Reach a good outcome", "medium"
    level = hs.clean(difficulty, 10).lower() or level
    if level not in ("easy", "medium", "hard"):
        raise ValueError("Difficulty is easy, medium or hard.")
    return modes.enter(
        settings, "roleplay", "Role-play", name,
        f"Role-play '{name}'. You play {role}; set the scene in one line and start in character. The user's goals: "
        f"{goals}. Difficulty {level}: easy means cooperative, medium some pushback, hard realistic resistance. "
        "Stay in character. When they reach the goals or say stop, step out and give two lines of feedback on "
        "how they did against each goal.",
        card=screen.card("text", f"Role-play: {name}", "modes-roleplay", text=f"Your goals: {goals}\nDifficulty: {level}",
                         buttons=[{"label": "End role-play", "say": "Stop the role-play and give me feedback."}]))


# ---- tool -------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "practice_session",
        "description": "Practise out loud. Job interview practice: interview_start (role, level, question_type: "
                       "behavioural, strengths, situational or technical), interview_next asks the next question, "
                       "interview_feedback (answer summary, feedback, score 1-5) saves it after each answer, "
                       "interview_log shows past answers, star_tip = STAR method. Presentation rehearsal: "
                       "talk_start times a talk or speech, talk_stop (text = the talk's words for words per "
                       "minute), filler_count (text = transcript) counts um, uh, like, you know. Role-play "
                       "scenarios: roleplay_list, roleplay_start (scenario, difficulty easy/medium/hard).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "interview_start", "interview_next", "interview_feedback", "interview_log", "star_tip",
                    "talk_start", "talk_stop", "filler_count", "roleplay_list", "roleplay_start"]},
                "role": {"type": "string", "description": "Job, e.g. 'nurse'."},
                "level": {"type": "string", "description": "e.g. 'graduate', 'senior', 'manager'."},
                "question_type": {"type": "string", "enum": list(QUESTION_TYPES)},
                "answer": {"type": "string", "description": "interview_feedback: one-line summary of their answer."},
                "feedback": {"type": "string"},
                "score": {"type": "integer"},
                "title": {"type": "string", "description": "talk_start: name of the talk."},
                "text": {"type": "string"},
                "scenario": {"type": "string"},
                "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"practice_session"}
modes.STARTERS["interviewer"] = lambda settings, topic: interview_start(settings, topic)
modes.STARTERS["roleplay"] = lambda settings, topic: roleplay_start(settings, topic)


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "interview_start":
        return interview_start(settings, args.get("role"), args.get("level"), args.get("question_type"))
    if action == "interview_next":
        return interview_next(settings)
    if action == "interview_feedback":
        return interview_feedback(settings, args.get("answer"), args.get("feedback"), args.get("score"))
    if action == "interview_log":
        return interview_log(settings)
    if action == "star_tip":
        return star_tip()
    if action == "talk_start":
        return talk_start(settings, args.get("title"))
    if action == "talk_stop":
        return talk_stop(settings, args.get("text"))
    if action == "filler_count":
        return filler_count(args.get("text"))
    if action == "roleplay_list":
        return roleplay_list()
    if action == "roleplay_start":
        return roleplay_start(settings, args.get("scenario"), args.get("difficulty"))
    raise ValueError("Unknown practice action.")
