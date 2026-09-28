"""Discover: a study planner. Save exam dates and subjects, then get a day-by-day revision timetable
up to each exam, shared out so nearer exams get more sessions and the day before each exam is for that subject.

Exams live in discover-exams.json in the memory folder.
"""

import json
from datetime import date, timedelta

import memory
import screen
from config import Settings

FILE = "discover-exams.json"
MAX_EXAMS = 30
MAX_DAYS = 120


def _load(settings: Settings) -> list[dict]:
    try:
        found = json.loads((memory.root(settings) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return found if isinstance(found, list) else []


def _save(settings: Settings, exams: list[dict]) -> None:
    path = memory.root(settings) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(exams, indent=2, ensure_ascii=False), encoding="utf-8")


def _day(text) -> date:
    try:
        return date.fromisoformat(str(text or "").strip()[:10])
    except ValueError:
        raise ValueError("I need the exam date as YYYY-MM-DD.") from None


def add_exam(settings: Settings, subject, when, today: date) -> str:
    subject = " ".join(str(subject or "").split())[:60]
    if not subject:
        raise ValueError("Which subject is the exam?")
    day = _day(when)
    if day <= today:
        raise ValueError("That exam date has already passed.")
    exams = [e for e in _load(settings) if e["date"] >= today.isoformat()]
    exams = [e for e in exams if e["subject"].lower() != subject.lower()]
    if len(exams) >= MAX_EXAMS:
        raise ValueError("That's a lot of exams already.")
    exams.append({"subject": subject, "date": day.isoformat()})
    _save(settings, sorted(exams, key=lambda e: e["date"]))
    return f"Saved your {subject} exam on {day:%A %d %B}, in {(day - today).days} days."


def list_exams(settings: Settings, today: date) -> screen.Shown:
    exams = [e for e in _load(settings) if e["date"] >= today.isoformat()]
    if not exams:
        return screen.Shown("No exams saved. Tell me a subject and its exam date.",
                            screen.card("table", "Exams", "discover-exams", columns=["Subject", "Date", "Days"], rows=[]))
    rows = [[e["subject"], f"{date.fromisoformat(e['date']):%a %d %b %Y}",
             (date.fromisoformat(e["date"]) - today).days] for e in exams]
    first = exams[0]
    said = f"{len(exams)} exams coming up; the next is {first['subject']} in {rows[0][2]} days."
    return screen.Shown(said, screen.card("table", "Exams", "discover-exams", columns=["Subject", "Date", "Days"],
                                          rows=rows, buttons=[{"label": "Revision timetable",
                                                               "say": "Make me a revision timetable."}]))


def remove_exam(settings: Settings, subject, confirmed: bool) -> str:
    exams = _load(settings)
    found = next((e for e in exams if e["subject"].lower() == str(subject or "").strip().lower()), None)
    if not found:
        raise ValueError(f"There's no {subject} exam saved.")
    if not confirmed:
        return f"Remove the {found['subject']} exam on {found['date']}? Say yes to confirm."
    exams.remove(found)
    _save(settings, exams)
    return f"Removed the {found['subject']} exam."


def plan(exams: list[dict], today: date, sessions: int) -> list[list[str]]:
    """Rows of [day, sessions]: sessions go to the subject with the fewest so far for how soon its exam is."""
    done = {e["subject"]: 0 for e in exams}
    last = max(date.fromisoformat(e["date"]) for e in exams)
    rows, day = [], today
    while day <= last and len(rows) < MAX_DAYS:
        on_day = [e["subject"] for e in exams if e["date"] == day.isoformat()]
        ahead = [e for e in exams if e["date"] > day.isoformat()]
        tomorrow = [e["subject"] for e in ahead if date.fromisoformat(e["date"]) == day + timedelta(days=1)]
        slots = []
        for _ in range(sessions if ahead else 0):
            pool = tomorrow or [e["subject"] for e in ahead]
            left = {e["subject"]: (date.fromisoformat(e["date"]) - day).days for e in ahead}
            pick = min(pool, key=lambda s: (slots.count(s), done[s] * left[s], s))
            done[pick] += 1
            slots.append(pick)
        text = ", ".join(slots) if slots else "Rest"
        if on_day:
            text = f"EXAM: {', '.join(on_day)}" + (f"; then {text}" if slots else "")
        rows.append([f"{day:%a %d %b}", text])
        day += timedelta(days=1)
    return rows


def timetable(settings: Settings, sessions, today: date) -> screen.Shown:
    exams = [e for e in _load(settings) if e["date"] > today.isoformat()]
    if not exams:
        raise ValueError("Add your exams first: a subject and a date for each.")
    sessions = max(1, min(int(sessions or 3), 8))
    rows = plan(exams, today, sessions)
    said = (f"Here's a revision timetable of {sessions} sessions a day for {len(rows)} days, up to your last exam. "
            f"Today: {rows[0][1]}.")
    return screen.Shown(said, screen.card("table", "Revision timetable", "discover-timetable",
                                          columns=["Day", f"Sessions ({sessions} a day)"], rows=rows))


ACTIONS = ["add_exam", "list_exams", "remove_exam", "timetable"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "study_planner",
        "description": "Exam study planner. add_exam (subject, date YYYY-MM-DD); list_exams; remove_exam (set "
                       "confirmed=true only after the user says yes); timetable: a day-by-day revision timetable "
                       "until each exam, shown as a pop-up table (sessions per day, default 3).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "subject": {"type": "string"},
                "date": {"type": "string", "description": "Exam date, YYYY-MM-DD."},
                "sessions": {"type": "integer", "description": "Revision sessions a day, 1 to 8."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"study_planner"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "add_exam":
        return add_exam(settings, args.get("subject"), args.get("date"), today)
    if action == "list_exams":
        return list_exams(settings, today)
    if action == "remove_exam":
        return remove_exam(settings, args.get("subject"), bool(args.get("confirmed")))
    if action == "timetable":
        return timetable(settings, args.get("sessions"), today)
    raise ValueError(f"Unknown study planner action: {action}")
