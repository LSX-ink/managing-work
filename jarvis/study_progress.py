"""Study progress: Pomodoro sessions logged per subject, a weekly hours chart, past papers with a trend, grade
boundaries you enter yourself, and a weighted grade calculator that says what you need in the final.

Study minutes go into the same log as "I studied maths for 90 minutes" (growth-study.json), and the Pomodoro is the
existing 25-minute focus timer. Papers, boundaries and components are in study.json.
"""

import time
from datetime import date, timedelta

import dates_saved
import growth_study
import screen
import study_store as st
from config import Settings

POMODORO_MINUTES = 25
MAX_PAPERS = 300


def pomodoro(settings: Settings, subject, today: date) -> screen.Shown | str:
    data = st.load(settings)
    name = st.ensure_course(data, subject)["name"]
    text = dates_saved.focus_start(settings)
    if not text.startswith("Focus session started"):
        return text
    data["pomodoro"] = {"subject": name, "date": today.isoformat()}
    st.save(settings, data)
    ends = int((time.time() + POMODORO_MINUTES * 60) * 1000)
    return screen.Shown(f"Pomodoro started for {name}: 25 minutes. Say 'log my session' when it ends.", screen.card(
        "timer", f"Study: {name}", "study-pomodoro", ends_at=ends,
        buttons=[{"label": "Log it", "say": f"Log my {name} study session."}]))


def log_session(settings: Settings, args: dict, today: date) -> str:
    data = st.load(settings)
    pending = data["pomodoro"] if data["pomodoro"].get("date") == today.isoformat() else {}
    subject = st.clean(args.get("subject")) or pending.get("subject", "")
    minutes = args.get("minutes") or (POMODORO_MINUTES if pending else None)
    if not st.clean(subject) or not minutes:
        raise ValueError("Which subject, and for how many minutes?")
    st.ensure_course(data, subject)
    data["pomodoro"] = {}
    st.save(settings, data)
    return growth_study.log_study(settings, subject, minutes, today)


def week_chart(settings: Settings, weeks, today: date) -> screen.Shown:
    log = st.gs.load(settings, "study", [])
    weeks = max(1, min(int(weeks or 1), 12))
    if weeks == 1:
        totals: dict[str, float] = {}
        for e in log:
            if st.gs.this_week(e["date"], today):
                key = next((k for k in totals if k.lower() == e["subject"].lower()), e["subject"])
                totals[key] = totals.get(key, 0) + e["minutes"]
        if not totals:
            raise ValueError("No study logged this week yet. Try a Pomodoro.")
        order = sorted(totals.items(), key=lambda kv: -kv[1])
        chart = {"type": "bar", "labels": [k for k, _ in order], "values": [round(v / 60, 2) for _, v in order], "unit": "h"}
        said = f"{sum(totals.values()) / 60:.1f} hours studied this week, most on {order[0][0]}."
        title = "Study hours this week"
    else:
        start = st.gs.week_start(today)
        labels, values = [], []
        for i in range(weeks - 1, -1, -1):
            monday = start - timedelta(weeks=i)
            mins = sum(e["minutes"] for e in log if monday.isoformat() <= e["date"][:10] <= (monday + timedelta(days=6)).isoformat())
            labels.append(f"{monday:%d %b}")
            values.append(round(mins / 60, 2))
        chart = {"type": "line", "labels": labels, "values": values, "unit": "h"}
        said = f"{values[-1]:g} hours this week; the best of the last {weeks} weeks was {max(values):g}."
        title = f"Study hours, last {weeks} weeks"
    return screen.Shown(said, screen.card("chart", title, "study-hours", chart=chart))


# ---- grade boundaries ---------------------------------------------------------------------------------

def set_boundaries(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    subject = st.ensure_course(data, args.get("subject"))["name"]
    rows = []
    for b in args.get("boundaries") or []:
        grade = st.need(b.get("grade"), "grade", 10)
        rows.append({"grade": grade, "min": st.number(b.get("min_percent"), "boundary")})
    if not rows:
        raise ValueError("Give me each grade with its minimum percentage, e.g. grade 7 from 70 percent.")
    data["boundaries"][subject] = sorted(rows, key=lambda r: -r["min"])
    st.save(settings, data)
    return f"Saved {st.plural(len(rows), 'grade boundary')} for {subject}. They're your own numbers, so check them against the exam board."


def boundaries(settings: Settings, subject) -> screen.Shown:
    data = st.load(settings)
    name = st.course(data, subject)["name"]
    rows = data["boundaries"].get(name)
    if not rows:
        raise ValueError(f"You haven't given me grade boundaries for {name} yet.")
    return screen.Shown(f"{name}: top grade {rows[0]['grade']} from {rows[0]['min']:g} percent.", screen.card(
        "table", f"{name} grade boundaries", f"study-boundaries-{name}", columns=["Grade", "Minimum %"],
        rows=[[r["grade"], f"{r['min']:g}"] for r in rows]))


def grade_of(data: dict, subject: str, pct: float) -> str:
    for row in data["boundaries"].get(subject) or []:
        if pct >= row["min"]:
            return row["grade"]
    return "ungraded" if data["boundaries"].get(subject) else ""


def _percent(args: dict) -> float:
    if args.get("percent") is not None:
        return st.number(args["percent"], "percentage")
    out_of = st.number(args.get("out_of"), "total marks")
    if not out_of:
        raise ValueError("Give me a percentage, or a score and what it's out of.")
    return st.number(args.get("score"), "score") / out_of * 100


def grade_for(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    name = st.course(data, args.get("subject"))["name"]
    pct = _percent(args)
    grade = grade_of(data, name, pct)
    if not grade:
        raise ValueError(f"Give me your {name} grade boundaries first.")
    return f"{pct:.0f} percent in {name} is a {grade} on your boundaries."


# ---- past papers --------------------------------------------------------------------------------------

def add_paper(settings: Settings, args: dict, today: date) -> str:
    data = st.load(settings)
    name = st.ensure_course(data, args.get("subject"))["name"]
    paper = st.need(args.get("paper"), "paper", 80)
    out_of = st.number(args.get("out_of"), "total marks")
    if out_of <= 0:
        raise ValueError("What was the paper out of?")
    score = st.number(args.get("score"), "score")
    if score > out_of:
        raise ValueError("That score is higher than the total.")
    when = st.day(args["date"]).isoformat() if args.get("date") else today.isoformat()
    if len(data["papers"]) >= MAX_PAPERS:
        raise ValueError("That's a lot of papers already.")
    pct = round(score / out_of * 100, 1)
    earlier = [p for p in data["papers"] if p["subject"] == name]
    data["papers"].append({"subject": name, "paper": paper, "score": score, "out_of": out_of, "pct": pct, "date": when})
    st.save(settings, data)
    grade = grade_of(data, name, pct)
    trend = ""
    if earlier:
        diff = pct - earlier[-1]["pct"]
        trend = f", {'up' if diff > 0 else 'down' if diff < 0 else 'level'} {abs(diff):.0f} points on last time" if diff else ", level with last time"
    return f"{paper}: {score:g} out of {out_of:g}, {pct:.0f} percent{f', grade {grade}' if grade else ''}{trend}."


def _papers(data: dict, subject) -> tuple[str, list[dict]]:
    name = st.course(data, subject)["name"] if st.clean(subject) or len(data["courses"]) == 1 else ""
    rows = [p for p in data["papers"] if not name or p["subject"] == name]
    if not rows:
        raise ValueError("No past papers logged yet.")
    return name or "All subjects", sorted(rows, key=lambda p: p["date"])


def papers(settings: Settings, subject) -> screen.Shown:
    data = st.load(settings)
    name, rows = _papers(data, subject)
    table = [[p["date"], p["subject"], p["paper"], f"{p['score']:g}/{p['out_of']:g}", f"{p['pct']:.0f}%",
              grade_of(data, p["subject"], p["pct"])] for p in rows]
    avg = sum(p["pct"] for p in rows) / len(rows)
    return screen.Shown(f"{st.plural(len(rows), 'paper')}, averaging {avg:.0f} percent.", screen.card(
        "table", f"Past papers: {name}", "study-papers", columns=["Date", "Subject", "Paper", "Score", "%", "Grade"],
        rows=table, buttons=[{"label": "Trend", "say": f"Show my past paper trend{'' if name == 'All subjects' else f' for {name}'}."}]))


def paper_trend(settings: Settings, subject) -> screen.Shown:
    data = st.load(settings)
    name, rows = _papers(data, subject)
    if len(rows) < 2:
        raise ValueError("Log at least two papers to see a trend.")
    chart = {"type": "line", "labels": [p["paper"][:14] or p["date"] for p in rows], "values": [p["pct"] for p in rows],
             "unit": "%"}
    diff = rows[-1]["pct"] - rows[0]["pct"]
    return screen.Shown(f"From {rows[0]['pct']:.0f} to {rows[-1]['pct']:.0f} percent, "
                        f"{'up' if diff > 0 else 'down' if diff < 0 else 'level'} {abs(diff):.0f} points.",
                        screen.card("chart", f"Paper scores: {name}", "study-trend", chart=chart))


# ---- grade calculator ---------------------------------------------------------------------------------

def set_component(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    name = st.ensure_course(data, args.get("subject"))["name"]
    part = st.need(args.get("component"), "component", 60)
    weight = st.number(args.get("weight"), "weight")
    if not 0 < weight <= 100:
        raise ValueError("The weight is a percentage of the whole grade, up to 100.")
    mark = None if args.get("percent") is None else st.number(args["percent"], "mark")
    if mark is not None and mark > 100:
        raise ValueError("A mark is a percentage, up to 100.")
    comps = data["components"].setdefault(name, [])
    found = next((c for c in comps if c["name"].lower() == part.lower()), None)
    if found:
        found.update(weight=weight, mark=mark if mark is not None else found.get("mark"))
    else:
        comps.append({"name": part, "weight": weight, "mark": mark})
    total = sum(c["weight"] for c in comps)
    st.save(settings, data)
    warn = f" That's {total:g} percent in all; it should reach 100." if total != 100 else ""
    return f"Saved {part} at {weight:g} percent of {name}{'' if mark is None else f', marked {mark:g} percent'}.{warn}"


def grade_calc(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    course = st.course(data, args.get("subject"))
    name = course["name"]
    comps = data["components"].get(name) or []
    if not comps:
        raise ValueError(f"Tell me {name}'s parts first, like coursework 40 percent and exam 60 percent.")
    if args.get("target_percent") is not None:
        target, label = st.number(args["target_percent"], "target"), f"{args['target_percent']:g} percent"
    else:
        grade = st.clean(args.get("target_grade")) or course.get("target", "")
        row = next((b for b in data["boundaries"].get(name, []) if b["grade"].lower() == grade.lower()), None)
        if not row:
            raise ValueError("Give me a target percentage, or the grade boundaries and a target grade.")
        target, label = row["min"], f"grade {row['grade']}"
    total = sum(c["weight"] for c in comps)
    marked = [c for c in comps if c.get("mark") is not None]
    points = sum(c["weight"] * c["mark"] / 100 for c in marked)
    want = st.clean(args.get("component"))
    left = [c for c in comps if c.get("mark") is None and (not want or c["name"].lower() == want.lower())]
    rows = [[c["name"], f"{c['weight']:g}%", "" if c.get("mark") is None else f"{c['mark']:g}%",
             "" if c.get("mark") is None else f"{c['weight'] * c['mark'] / 100:.1f}"] for c in comps]
    rows.append(["Total so far", f"{sum(c['weight'] for c in marked):g}%", "", f"{points:.1f} of {total:g}"])
    if not left:
        got = points / total * 100
        said = f"All parts are marked: {got:.0f} percent overall, {'enough for' if got >= target else 'short of'} {label}."
    else:
        rem = sum(c["weight"] for c in left)
        need = (target * total / 100 - points) / rem * 100
        which = left[0]["name"] if len(left) == 1 else "the rest"
        if need <= 0:
            said = f"You've already secured {label}, whatever you get in {which}."
        elif need > 100:
            said = f"{label.capitalize()} is out of reach now: you'd need {need:.0f} percent in {which}."
        else:
            said = f"To reach {label} you need {need:.0f} percent in {which}."
        rows.append([f"Needed in {which}", f"{rem:g}%", f"{max(need, 0):.0f}%", ""])
    return screen.Shown(said, screen.card("table", f"{name}: grade calculator", f"study-grades-{name}",
                                          columns=["Part", "Weight", "Mark", "Points"], rows=rows))


ACTIONS = ["pomodoro", "log_session", "week_chart", "add_paper", "papers", "paper_trend", "set_boundaries",
           "boundaries", "grade_for", "set_component", "grade_calc"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "study_progress",
        "description": "Study progress. pomodoro (subject) starts a 25-minute focus timer for a subject; log_session "
                       "(subject, minutes) logs study time; week_chart shows hours per subject (weeks 2 or more shows "
                       "hours per week). Past papers: add_paper (subject, paper, score, out_of, date), papers table, "
                       "paper_trend chart. Grades: set_boundaries (subject, boundaries the user gives), boundaries, "
                       "grade_for (subject, percent or score and out_of). Grade calculator: set_component (subject, "
                       "component, weight percent of the grade, percent mark if known) then grade_calc (subject, "
                       "target_grade or target_percent, optional component) says what is needed in the rest.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "subject": {"type": "string"},
                "minutes": {"type": "number"},
                "weeks": {"type": "integer", "description": "week_chart: 1 for this week, up to 12."},
                "paper": {"type": "string", "description": "Paper name, e.g. Paper 1 2024."},
                "score": {"type": "number"},
                "out_of": {"type": "number"},
                "percent": {"type": "number", "description": "A percentage, or a component's mark."},
                "date": {"type": "string", "description": "YYYY-MM-DD."},
                "boundaries": {"type": "array", "items": {"type": "object", "properties": {
                    "grade": {"type": "string"}, "min_percent": {"type": "number"}},
                    "required": ["grade", "min_percent"], "additionalProperties": False}},
                "component": {"type": "string", "description": "e.g. Coursework, Final exam."},
                "weight": {"type": "number", "description": "Percent of the whole grade."},
                "target_grade": {"type": "string"},
                "target_percent": {"type": "number"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"study_progress"}


async def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    """Async so the Pomodoro starts on the event loop that timers.py needs."""
    today = today or st.today()
    action = args.get("action")
    if action == "pomodoro":
        return pomodoro(settings, args.get("subject"), today)
    if action == "log_session":
        return log_session(settings, args, today)
    if action == "week_chart":
        return week_chart(settings, args.get("weeks"), today)
    if action == "add_paper":
        return add_paper(settings, args, today)
    if action == "papers":
        return papers(settings, args.get("subject"))
    if action == "paper_trend":
        return paper_trend(settings, args.get("subject"))
    if action == "set_boundaries":
        return set_boundaries(settings, args)
    if action == "boundaries":
        return boundaries(settings, args.get("subject"))
    if action == "grade_for":
        return grade_for(settings, args)
    if action == "set_component":
        return set_component(settings, args)
    if action == "grade_calc":
        return grade_calc(settings, args)
    raise ValueError(f"Unknown study progress action: {action}")
