"""Time on work projects: a start/stop timer, logged time, totals, the weekly timesheet (and CSV), focus sessions,
working hours with a count-down to home time, and overtime against the hours you're expected to do.
"""

import csv
import io
from datetime import datetime, timedelta

import screen
import worktools_store as ws
from config import Settings

MAX_ENTRIES = 5000
DEFAULT_WEEKLY = 37.5
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _save(settings: Settings, data: dict) -> None:
    data["entries"] = data["entries"][-MAX_ENTRIES:]
    data["focus"] = data["focus"][-MAX_ENTRIES:]
    ws.save(settings, ws.TIME, data)


def _log(data: dict, project: str, day, minutes: float, source: str) -> None:
    data["entries"].append({"project": project, "date": day.isoformat(), "minutes": round(minutes, 1), "source": source})


def _stop(data: dict) -> tuple[str, float] | None:
    run = ws.running_minutes(data)
    if run:
        started = datetime.fromisoformat(data["running"]["started"])
        _log(data, run[0], started.date(), run[1], "timer")
        data.pop("running", None)
    return run


def start(settings: Settings, project) -> screen.Shown:
    name = ws.project(settings, project)
    data = ws.time_data(settings)
    stopped = _stop(data)
    data["running"] = {"project": name, "started": ws.now().isoformat(timespec="seconds")}
    _save(settings, data)
    said = f"Stopped {stopped[0]} after {ws.hm(stopped[1])}. " if stopped else ""
    return screen.Shown(said + f"Timing {name}.", _timer_card(name, ws.now()))


def _timer_card(name: str, started: datetime) -> dict:
    return screen.card("timer", f"Timing {name}", "work-timer", started_at=int(started.timestamp() * 1000),
                       buttons=[{"label": "Stop", "say": "Stop my work timer."}])


def stop(settings: Settings) -> str:
    data = ws.time_data(settings)
    stopped = _stop(data)
    if not stopped:
        return "No work timer is running."
    _save(settings, data)
    return f"Stopped. Logged {ws.hm(stopped[1])} on {stopped[0]}."


def status(settings: Settings):
    data = ws.time_data(settings)
    run = ws.running_minutes(data)
    if not run:
        return "No work timer is running."
    started = datetime.fromisoformat(data["running"]["started"])
    return screen.Shown(f"Timing {run[0]} for {ws.hm(run[1])} so far.", _timer_card(run[0], started))


def log(settings: Settings, project, minutes, when) -> str:
    name = ws.project(settings, project)
    try:
        minutes = float(minutes)
    except (TypeError, ValueError):
        raise ValueError("How many minutes?") from None
    if not 0 < minutes <= 24 * 60:
        raise ValueError("Give between 1 minute and 24 hours.")
    day = ws.parse_date(when) or ws.today()
    data = ws.time_data(settings)
    _log(data, name, day, minutes, "manual")
    _save(settings, data)
    week = ws.week_start(day)
    total = ws.minutes_by_project(data["entries"], week, week + timedelta(days=6)).get(name, 0)
    return f"Logged {ws.hm(minutes)} on {name} for {ws.short(day)}. {ws.hm(total)} on it that week."


def _with_running(data: dict, start, end) -> dict:
    mins = ws.minutes_by_project(data["entries"], start, end)
    run = ws.running_minutes(data)
    if run and start <= datetime.fromisoformat(data["running"]["started"]).date() <= end:
        mins[run[0]] = mins.get(run[0], 0) + run[1]
    return mins


def totals(settings: Settings) -> screen.Shown:
    data = ws.time_data(settings)
    today = ws.today()
    week = ws.week_start(today)
    day = _with_running(data, today, today)
    whole = _with_running(data, week, week + timedelta(days=6))
    order = sorted(whole, key=lambda k: -whole[k])
    today_bits = ", ".join(f"{k} {ws.hm(v)}" for k, v in sorted(day.items(), key=lambda kv: -kv[1])) or "nothing yet"
    said = f"Today: {today_bits}. This week: {ws.hm(sum(whole.values()))} in total."
    chart = {"type": "bar", "labels": order, "values": [round(whole[k] / 60, 2) for k in order], "unit": "h"}
    return screen.Shown(said, screen.card("chart", "Hours this week", "work-hours", chart=chart,
                                          text=f"Today: {today_bits}"))


def _week_grid(data: dict, start) -> dict:
    """{project: [minutes Mon..Sun]} for the week starting start."""
    grid: dict[str, list] = {}
    for i in range(7):
        day = start + timedelta(days=i)
        for name, m in ws.minutes_by_project(data["entries"], day, day).items():
            grid.setdefault(name, [0.0] * 7)[i] += m
    return grid


def _h(minutes: float) -> str:
    return f"{minutes / 60:.2f}".rstrip("0").rstrip(".") if minutes else "0"


def timesheet(settings: Settings, week_value) -> screen.Shown:
    start = ws.week_of(week_value)
    grid = _week_grid(ws.time_data(settings), start)
    rows = [[f"{name} ({_h(sum(days))}h)"] + [_h(m) for m in days] for name, days in sorted(grid.items())]
    day_totals = [sum(days[i] for days in grid.values()) for i in range(7)]
    rows.append([f"Total ({_h(sum(day_totals))}h)"] + [_h(m) for m in day_totals])
    said = f"Week of {ws.short(start)}: {ws.hm(sum(day_totals))} over {len(grid)} projects."
    return screen.Shown(said, screen.card("table", f"Timesheet, week of {ws.short(start)}", "work-timesheet",
                                          columns=["Project (hours)"] + ws.DAYS, rows=rows,
                                          buttons=[{"label": "Export CSV", "say": f"Export my work timesheet for the week of {start.isoformat()}."}]))


def export(settings: Settings, week_value) -> screen.Shown:
    start = ws.week_of(week_value)
    grid = _week_grid(ws.time_data(settings), start)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["Project"] + [f"{d} {(start + timedelta(days=i)).isoformat()}" for i, d in enumerate(ws.DAYS)] + ["Total"])
    for name, days in sorted(grid.items()):
        writer.writerow([name.replace(",", " ")] + [_h(m) for m in days] + [_h(sum(days))])
    day_totals = [sum(days[i] for days in grid.values()) for i in range(7)]
    writer.writerow(["Total"] + [_h(m) for m in day_totals] + [_h(sum(day_totals))])
    path = ws.work_folder(settings, "Timesheets") / f"Timesheet week of {start.isoformat()}.csv"
    path.write_text(out.getvalue(), encoding="utf-8")
    return screen.Shown(f"Saved the timesheet as {path.name} in the {path.parent.parent.name} folder.",
                        screen.file_card(settings, path))


def focus_log(settings: Settings, project, minutes, when) -> str:
    name = ws.project(settings, project) if ws.clean(project) else ""
    try:
        minutes = float(minutes)
    except (TypeError, ValueError):
        raise ValueError("How many minutes of focus?") from None
    if not 0 < minutes <= 12 * 60:
        raise ValueError("Give between 1 minute and 12 hours.")
    day = ws.parse_date(when) or ws.today()
    data = ws.time_data(settings)
    data["focus"].append({"project": name, "date": day.isoformat(), "minutes": round(minutes, 1)})
    _save(settings, data)
    week = ws.week_start(day)
    total = sum(f["minutes"] for f in data["focus"] if week.isoformat() <= f["date"] <= (week + timedelta(days=6)).isoformat())
    return f"Logged {ws.hm(minutes)} of focus{' on ' + name if name else ''}. {ws.hm(total)} of focus that week."


def focus_week(settings: Settings, week_value) -> screen.Shown:
    start = ws.week_of(week_value)
    focus = ws.time_data(settings)["focus"]
    per_day = [sum(f["minutes"] for f in focus if f.get("date") == (start + timedelta(days=i)).isoformat())
               for i in range(7)]
    per_project = ws.minutes_by_project([dict(f, project=f.get("project") or "No project") for f in focus],
                                        start, start + timedelta(days=6))
    bits = ", ".join(f"{k} {ws.hm(v)}" for k, v in sorted(per_project.items(), key=lambda kv: -kv[1]))
    said = f"{ws.hm(sum(per_day))} of focus in the week of {ws.short(start)}" + (f": {bits}." if bits else ".")
    return screen.Shown(said, screen.card("chart", f"Focus, week of {ws.short(start)}", "work-focus", text=bits,
                                          chart={"type": "bar", "labels": ws.DAYS, "values": per_day, "unit": "m"}))


def _clock(value, what: str) -> str:
    text = ws.clean(value).replace(".", ":")
    try:
        return datetime.strptime(text, "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValueError(f"Give the {what} time as HH:MM, e.g. 09:00.") from None


def hours_set(settings: Settings, start_at, end_at, days, weekly) -> str:
    begin, end = _clock(start_at, "start"), _clock(end_at, "finish")
    if end <= begin:
        raise ValueError("The finish time needs to be after the start time.")
    picked = sorted({WEEKDAYS.index(d.lower()) for d in ws.words(days, 7, 12) if d.lower() in WEEKDAYS}) or [0, 1, 2, 3, 4]
    data = ws.time_data(settings)
    hours = {"start": begin, "end": end, "days": picked}
    if weekly:
        hours["weekly"] = max(0.0, min(float(weekly), 100.0))
    data["hours"] = hours
    _save(settings, data)
    names = ", ".join(WEEKDAYS[i].title() for i in picked)
    return f"Working hours set: {begin} to {end}, {names}; {_expected(data) / 60:g} hours a week expected."


def _expected(data: dict) -> float:
    """Minutes a week the user expects to work."""
    h = data.get("hours") or {}
    if h.get("weekly"):
        return float(h["weekly"]) * 60
    if h.get("start") and h.get("end"):
        span = datetime.strptime(h["end"], "%H:%M") - datetime.strptime(h["start"], "%H:%M")
        return span.total_seconds() / 60 * len(h.get("days") or [])
    return DEFAULT_WEEKLY * 60


def finish(settings: Settings):
    h = ws.time_data(settings).get("hours")
    if not h:
        return "Tell me your working hours first, e.g. nine till half five, Monday to Friday."
    now = ws.now()
    if now.weekday() not in h.get("days", []):
        return "It's not a working day for you today."
    end = datetime.combine(now.date(), datetime.strptime(h["end"], "%H:%M").time())
    if now >= end:
        return f"You finished at {h['end']}; time to stop."
    left = (end - now).total_seconds() / 60
    return screen.Shown(f"{ws.hm(left)} until you finish at {h['end']}.",
                        screen.card("timer", "Until home time", "work-finish", ends_at=int(end.timestamp() * 1000)))


def overtime(settings: Settings) -> screen.Shown:
    data = ws.time_data(settings)
    expected = _expected(data)
    this = ws.week_start(ws.today())
    rows, balance = [], 0.0
    for back in range(3, -1, -1):
        start = this - timedelta(days=7 * back)
        actual = sum(_with_running(data, start, start + timedelta(days=6)).values())
        balance += actual - expected
        rows.append([ws.short(start), ws.hm(expected), ws.hm(actual), ws.hm(actual - expected)])
    now_diff = sum(_with_running(data, this, this + timedelta(days=6)).values()) - expected
    word = "over" if now_diff > 0 else "under"
    said = (f"This week you're {ws.hm(abs(now_diff))} {word} your {expected / 60:g} hours; "
            f"over four weeks the balance is {ws.hm(balance)}.")
    rows.append(["4 weeks", ws.hm(expected * 4), "", ws.hm(balance)])
    return screen.Shown(said, screen.card("table", "Overtime", "work-overtime",
                                          columns=["Week of", "Expected", "Actual", "Over (+) / under (-)"], rows=rows))


def tool_definitions() -> list[dict]:
    return [{
        "name": "work_time",
        "description": "Time tracking for work projects. actions: start / stop / status of the work timer on a "
                       "project, log manual time (minutes), totals (today's and this week's hours per project, "
                       "chart), timesheet (weekly table of hours per project per day), export (timesheet CSV into "
                       "the Work folder), focus_log (a focused session in minutes), focus_week (focus chart), "
                       "hours_set (working hours: start, end, days, weekly hours), finish (how long until I finish "
                       "work, countdown), overtime (expected vs actual hours per week).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["start", "stop", "status", "log", "totals", "timesheet",
                                                      "export", "focus_log", "focus_week", "hours_set", "finish",
                                                      "overtime"]},
                "project": {"type": "string"},
                "minutes": {"type": "number", "description": "log / focus_log; convert hours to minutes."},
                "date": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'yesterday'; default today."},
                "week": {"type": "string", "description": "'this', 'last' or a YYYY-MM-DD in that week."},
                "start": {"type": "string", "description": "hours_set: HH:MM, e.g. 09:00."},
                "end": {"type": "string", "description": "hours_set: HH:MM, e.g. 17:30."},
                "days": {"type": "array", "items": {"type": "string"}, "description": "hours_set: e.g. ['monday']."},
                "weekly_hours": {"type": "number", "description": "hours_set: contracted hours a week, if known."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"work_time"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, project, week = args.get("action"), args.get("project"), args.get("week")
    if action == "start":
        return start(settings, project)
    if action == "stop":
        return stop(settings)
    if action == "status":
        return status(settings)
    if action == "log":
        return log(settings, project, args.get("minutes"), args.get("date"))
    if action == "timesheet":
        return timesheet(settings, week)
    if action == "export":
        return export(settings, week)
    if action == "focus_log":
        return focus_log(settings, project, args.get("minutes"), args.get("date"))
    if action == "focus_week":
        return focus_week(settings, week)
    if action == "hours_set":
        return hours_set(settings, args.get("start"), args.get("end"), args.get("days"), args.get("weekly_hours"))
    if action == "finish":
        return finish(settings)
    if action == "overtime":
        return overtime(settings)
    return totals(settings)
