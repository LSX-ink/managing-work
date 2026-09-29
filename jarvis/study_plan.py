"""Study plan: courses with exam countdowns, a revision timetable shown as a week grid, assignment deadlines,
today's plan and an exam-day checklist.

The week grid is the "study-week" pop-up (frontend/popup-study.js). Exams already saved with the discover study
planner are included too. Everything is in study.json in the memory folder.
"""

from datetime import date, timedelta

import discover_study
import screen
import study_store as st
from config import Settings

screen.EXTRA_KINDS.add("study-week")
MAX_DEADLINES = 100
MAX_DAYS = 120
PRIORITY = {"high": 0, "medium": 1, "low": 2}

EXAM_DAY = [
    ("Night before", ["Pack everything: ID if needed, pens, pencil, ruler, calculator, water.",
                      "Check the time, room and paper, and how you'll get there.",
                      "Look over your formulas or key facts once, then stop and rest.",
                      "Set two alarms and get an early night."]),
    ("Morning", ["Eat breakfast and drink some water.",
                 "Check the calculator has batteries and is in the right mode.",
                 "Phone off and away, watches that aren't plain ones stay at home.",
                 "Leave early: arrive 20 to 30 minutes before you start."]),
    ("In the exam", ["Fill in your name, candidate number and centre number first.",
                     "Read every instruction and the whole paper before you begin.",
                     "Spend the marks: about a minute per mark is a good rule.",
                     "Start with a question you can do, and move on if you get stuck.",
                     "Leave time at the end to check your working and answers."]),
]


def _exams(settings: Settings, data: dict, today: date) -> list[dict]:
    found = {c["name"].lower(): {"subject": c["name"], "date": c["exam_date"]}
             for c in data["courses"] if c.get("exam_date") and c["exam_date"] >= today.isoformat()}
    for e in discover_study._load(settings):
        if e.get("date", "") >= today.isoformat():
            found.setdefault(str(e.get("subject", "")).lower(), {"subject": e["subject"], "date": e["date"]})
    return sorted(found.values(), key=lambda e: e["date"])


def add_course(settings: Settings, args: dict, today: date) -> str:
    data = st.load(settings)
    name = st.need(args.get("subject"), "subject", 60)
    entry = next((c for c in data["courses"] if c["name"].lower() == name.lower()), None)
    if entry is None:
        if len(data["courses"]) >= 30:
            raise ValueError("That's a lot of courses already.")
        entry = {"name": name}
        data["courses"].append(entry)
    if args.get("level"):
        entry["level"] = st.clean(args["level"], 40)
    if args.get("target_grade"):
        entry["target"] = st.clean(args["target_grade"], 10)
    if args.get("exam_date"):
        entry["exam_date"] = st.day(args["exam_date"], "exam date").isoformat()
    st.save(settings, data)
    if entry.get("exam_date"):
        left = (date.fromisoformat(entry["exam_date"]) - today).days
        return f"Saved {entry['name']}: exam in {st.days_text(left)}."
    return f"Saved {entry['name']}. Tell me its exam date when you know it."


def _rows(settings: Settings, data: dict, today: date) -> list[list[str]]:
    rows, seen = [], set()
    for c in data["courses"]:
        seen.add(c["name"].lower())
        when = c.get("exam_date") or next((e["date"] for e in discover_study._load(settings)
                                           if str(e.get("subject", "")).lower() == c["name"].lower()), "")
        left = (date.fromisoformat(when) - today).days if when else None
        rows.append([c["name"], c.get("level", ""), f"{date.fromisoformat(when):%a %d %b %Y}" if when else "no date",
                     "" if left is None else ("done" if left < 0 else st.days_text(left)), c.get("target", "")])
    for e in discover_study._load(settings):
        if str(e.get("subject", "")).lower() not in seen and e.get("date", "") >= today.isoformat():
            left = (date.fromisoformat(e["date"]) - today).days
            rows.append([e["subject"], "", f"{date.fromisoformat(e['date']):%a %d %b %Y}", st.days_text(left), ""])
    return rows


def courses(settings: Settings, today: date) -> screen.Shown:
    data = st.load(settings)
    rows = _rows(settings, data, today)
    if not rows:
        raise ValueError("No courses yet. Tell me a subject and its exam date.")
    nxt = next(iter(_exams(settings, data, today)), None)
    said = (f"Your next exam is {nxt['subject']} in {st.days_text((date.fromisoformat(nxt['date']) - today).days)}."
            if nxt else f"You have {st.plural(len(rows), 'course')}, none with an exam date.")
    rows.sort(key=lambda r: (r[3] == "", r[2]))
    return screen.Shown(said, screen.card(
        "table", "Courses and exams", "study-courses", columns=["Subject", "Level", "Exam", "Countdown", "Target"],
        rows=rows, buttons=[{"label": "Revision timetable", "say": "Show my revision timetable."},
                            {"label": "Deadlines", "say": "Show my study deadlines."}]))


def remove_course(settings: Settings, name, confirmed: bool) -> str:
    data = st.load(settings)
    found = st.course(data, name)
    if not confirmed:
        return f"Ask the user to confirm removing {found['name']} with its topics and notes, then call again with confirmed true."
    key = found["name"]
    data["courses"].remove(found)
    for bucket in ("topics", "boundaries", "components", "formulas"):
        data[bucket].pop(key, None)
    st.save(settings, data)
    return f"Removed {key}."


# ---- revision timetable ---------------------------------------------------------------------------------

def _weakness(data: dict, subject: str) -> float:
    topics = data["topics"].get(subject) or []
    if not topics:
        return 1.0
    score = {"red": 2, "amber": 1, "green": 0}
    return 1 + sum(score.get(t.get("rag"), 1) for t in topics) / len(topics) / 2


def build_plan(data: dict, exams: list[dict], today: date, sessions: int) -> list[dict]:
    """One dict per day up to the last exam: date, exam subjects and the sessions (subjects) that day."""
    last = min(date.fromisoformat(exams[-1]["date"]), today + timedelta(days=MAX_DAYS))
    weight = {e["subject"]: _weakness(data, e["subject"]) for e in exams}
    given = {e["subject"]: 0 for e in exams}
    days, current = [], today
    while current <= last:
        on_day = [e["subject"] for e in exams if e["date"] == current.isoformat()]
        live = [e for e in exams if e["date"] > current.isoformat()]
        slots: list[str] = []
        for _ in range(sessions if live else 0):
            def score(e):
                left = (date.fromisoformat(e["date"]) - current).days
                eve = 3 if left == 1 else 1
                return eve * weight[e["subject"]] * 10 / (left + 4) / (1 + given[e["subject"]]) / (1 + slots.count(e["subject"]))
            pick = max(live, key=score)["subject"]
            given[pick] += 1
            slots.append(pick)
        days.append({"date": current.isoformat(), "label": f"{current:%a %d %b}", "exam": on_day, "slots": slots})
        current += timedelta(days=1)
    return days


def timetable(settings: Settings, args: dict, today: date) -> screen.Shown:
    data = st.load(settings)
    exams = _exams(settings, data, today)
    if not exams:
        raise ValueError("Add a course with an exam date first, then I can plan your revision.")
    sessions = max(1, min(int(args.get("sessions") or 3), 6))
    plan = build_plan(data, exams, today, sessions)
    week = max(0, int(args.get("week") or 0))
    chunk = plan[week * 7:week * 7 + 7]
    if not chunk:
        raise ValueError("Your exams are all done by then; there's nothing to plan.")
    for d in chunk:
        d["today"] = d["date"] == today.isoformat()
    total = len(plan)
    buttons = []
    if week:
        buttons.append({"label": "Earlier week", "say": f"Show my revision timetable for week {week}."})
    if (week + 1) * 7 < total:
        buttons.append({"label": "Next week", "say": f"Show my revision timetable for week {week + 2}."})
    first = next((d for d in plan if d["slots"]), plan[0])
    said = (f"Here's week {week + 1} of your revision timetable, {st.plural(sessions, 'session')} a day. "
            f"{'Today' if first['date'] == today.isoformat() else first['label']}: {', '.join(first['slots']) or 'rest'}.")
    return screen.Shown(said, screen.card("study-week", f"Revision: week {week + 1}", "study-week", buttons=buttons, data={
        "days": chunk, "subjects": [e["subject"] for e in exams], "sessions": sessions, "week": week + 1,
        "weeks": (total + 6) // 7}))


def today_plan(settings: Settings, today: date) -> screen.Shown:
    data = st.load(settings)
    items = []
    exams = _exams(settings, data, today)
    if exams:
        first = build_plan(data, exams, today, 3)[0]
        items += [{"label": f"Revise {s}", "say": f"Start a pomodoro for {s}."} for s in first["slots"]]
        items += [{"label": f"Exam today: {s}", "say": "Show my exam day checklist."} for s in first["exam"]]
    soon = [d for d in data["deadlines"] if not d.get("done") and d["due"] <= (today + timedelta(days=3)).isoformat()]
    items += [{"label": f"Due {d['due']}: {d['title']}", "say": f"Mark {d['title']} as done."}
              for d in sorted(soon, key=lambda d: d["due"])]
    if not items:
        return screen.Shown("Nothing planned today. Add a course with an exam date and I'll plan your revision.",
                            screen.card("list", "Study today", "study-today", items=[]))
    return screen.Shown(f"You have {st.plural(len(items), 'thing')} to do for study today.",
                        screen.card("list", "Study today", "study-today", items=items))


# ---- deadlines ------------------------------------------------------------------------------------------

def add_deadline(settings: Settings, args: dict, today: date) -> str:
    data = st.load(settings)
    title = st.need(args.get("title"), "assignment", 100)
    due = st.day(args.get("due"), "due date")
    priority = st.clean(args.get("priority") or "medium", 10).lower()
    if priority not in PRIORITY:
        raise ValueError("Priority is high, medium or low.")
    if len(data["deadlines"]) >= MAX_DEADLINES:
        raise ValueError("That's a lot of deadlines already.")
    subject = st.ensure_course(data, args["subject"])["name"] if st.clean(args.get("subject")) else ""
    data["deadlines"].append({"title": title, "subject": subject, "due": due.isoformat(), "priority": priority})
    st.save(settings, data)
    return f"Saved {title}, due {st.days_text((due - today).days)}, {priority} priority."


def deadlines(settings: Settings, today: date) -> screen.Shown:
    data = st.load(settings)
    open_ = sorted((d for d in data["deadlines"] if not d.get("done")), key=lambda d: (d["due"], PRIORITY[d["priority"]]))
    if not open_:
        return screen.Shown("No deadlines outstanding.", screen.card(
            "table", "Deadlines", "study-deadlines", columns=["Assignment", "Subject", "Due", "In", "Priority"], rows=[]))
    rows = []
    for d in open_:
        left = (date.fromisoformat(d["due"]) - today).days
        rows.append([d["title"], d.get("subject", ""), f"{date.fromisoformat(d['due']):%a %d %b}",
                     "OVERDUE" if left < 0 else st.days_text(left), d["priority"].upper()])
    late = sum(1 for r in rows if r[3] == "OVERDUE")
    said = f"{st.plural(len(rows), 'deadline')}, next is {open_[0]['title']} {st.days_text((date.fromisoformat(open_[0]['due']) - today).days)}."
    return screen.Shown(said + (f" {late} overdue." if late else ""), screen.card(
        "table", "Study deadlines", "study-deadlines", columns=["Assignment", "Subject", "Due", "In", "Priority"],
        rows=rows, buttons=[{"label": "Add one", "say": "Add a study deadline."}]))


def done_deadline(settings: Settings, title) -> str:
    data = st.load(settings)
    open_ = [d for d in data["deadlines"] if not d.get("done")]
    found = st.gs.find(open_, "title", title)
    if not found:
        raise ValueError("I can't find that deadline.")
    found["done"] = True
    st.save(settings, data)
    return f"Ticked off {found['title']}."


def exam_checklist(settings: Settings, name, today: date) -> screen.Shown:
    data = st.load(settings)
    found = st.find_course(data, name) if st.clean(name) else None
    items = [{"label": f"{part}: {line}"} for part, lines in EXAM_DAY for line in lines]
    title = "Exam day checklist"
    said = "Here's your exam day checklist."
    if found and found.get("exam_date"):
        left = (date.fromisoformat(found["exam_date"]) - today).days
        title = f"Exam day: {found['name']}"
        said = f"Checklist for {found['name']}, your exam is in {st.days_text(left)}."
        formulas = data["formulas"].get(found["name"])
        if formulas:
            items.append({"label": "Glance over your formula sheet once",
                          "say": f"Show my {found['name']} formula sheet."})
    return screen.Shown(said, screen.card("list", title, "study-examday", items=items, checks=True))


ACTIONS = ["add_course", "courses", "remove_course", "timetable", "today", "add_deadline", "deadlines",
           "done_deadline", "exam_day_checklist"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "study_plan",
        "description": "Exam and course planner for GCSE, A-level, university or certificates. add_course (subject, "
                       "level, exam_date YYYY-MM-DD, target_grade); courses lists exams with countdowns; "
                       "remove_course (confirmed only after the user says yes); timetable is the revision timetable "
                       "as a week grid pop-up working back from exam dates (sessions a day, week number); today is "
                       "today's revision plan; add_deadline (title, subject, due, priority high/medium/low), "
                       "deadlines, done_deadline (title) for assignments; exam_day_checklist (optional subject).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "subject": {"type": "string"},
                "level": {"type": "string", "description": "e.g. GCSE, A-level, degree, certificate."},
                "exam_date": {"type": "string", "description": "YYYY-MM-DD."},
                "target_grade": {"type": "string"},
                "sessions": {"type": "integer", "description": "Revision sessions a day, 1 to 6 (default 3)."},
                "week": {"type": "integer", "description": "Timetable week to show, 1 is this week."},
                "title": {"type": "string", "description": "Assignment name."},
                "due": {"type": "string", "description": "YYYY-MM-DD."},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"study_plan"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or st.today()
    action = args.get("action")
    if action == "add_course":
        return add_course(settings, args, today)
    if action == "courses":
        return courses(settings, today)
    if action == "remove_course":
        return remove_course(settings, args.get("subject"), bool(args.get("confirmed")))
    if action == "timetable":
        args = dict(args, week=max(0, int(args.get("week") or 1) - 1))
        return timetable(settings, args, today)
    if action == "today":
        return today_plan(settings, today)
    if action == "add_deadline":
        return add_deadline(settings, args, today)
    if action == "deadlines":
        return deadlines(settings, today)
    if action == "done_deadline":
        return done_deadline(settings, args.get("title"))
    if action == "exam_day_checklist":
        return exam_checklist(settings, args.get("subject"), today)
    raise ValueError(f"Unknown study plan action: {action}")
