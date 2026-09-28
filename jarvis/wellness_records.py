"""Health records: doctor, dentist and optician appointments with countdowns and check-ups due, vaccinations and
other health records, and a private period and cycle tracker.

Saved only on this PC, in health-plus-appointments.json, health-plus-records.json and health-plus-cycle.json.
"""

import calendar
from datetime import date, timedelta

import screen
import wellness_store as store
from config import Settings

KINDS = ["doctor", "dentist", "optician", "hospital", "physio", "other"]
CHECKUPS = {"dentist": ("Dentist check-up", 6), "optician": ("Eye test", 24)}
RECORD_KINDS = ["vaccination", "test result", "allergy", "condition", "medication", "other"]
MIN_CYCLE, MAX_CYCLE = 15, 60


# Appointments

def appt_add(settings: Settings, args: dict) -> str:
    kind = args.get("kind") if args.get("kind") in KINDS else "other"
    when = store.day(args.get("date"))
    entry = {"kind": kind, "date": when.isoformat(), "time": store.clock(args["time"]) if args.get("time") else "",
             "note": store.clean(args.get("note"), 120)}
    appts = store.load(settings, "appointments", [])
    appts.append(entry)
    store.save(settings, "appointments", sorted(appts, key=lambda a: (a["date"], a["time"])))
    at = f" at {entry['time']}" if entry["time"] else ""
    return f"Added {kind} appointment on {store.spoken(when)}{at}, {store.countdown(when)}."


def checkups(appts: list[dict]) -> list[str]:
    lines, today = [], store.today()
    for kind, (name, months) in CHECKUPS.items():
        past = [a for a in appts if a["kind"] == kind and a["date"] <= today.isoformat()]
        booked = [a for a in appts if a["kind"] == kind and a["date"] > today.isoformat()]
        if booked:
            lines.append(f"{name}: booked for {store.short(date.fromisoformat(booked[0]['date']))}")
        elif not past:
            lines.append(f"{name}: no visit logged (usually every {months} months); add your last one")
        else:
            due = store.add_months(date.fromisoformat(past[-1]["date"]), months)
            lines.append(f"{name}: {'overdue since' if due < today else 'due'} {store.short(due)} {due.year} ({store.countdown(due)})")
    return lines


def appts_show(settings: Settings):
    appts = store.load(settings, "appointments", [])
    today = store.today().isoformat()
    ahead = [a for a in appts if a["date"] >= today]
    recent = [a for a in appts if a["date"] < today][-3:]
    rows = [[store.short(date.fromisoformat(a["date"])) + (f" {a['time']}" if a["time"] else ""), a["kind"],
             a["note"], store.countdown(date.fromisoformat(a["date"]))] for a in recent + ahead]
    due = checkups(appts)
    said = (f"Next: {ahead[0]['kind']} {store.countdown(date.fromisoformat(ahead[0]['date']))}." if ahead
            else "No appointments coming up.") + " " + "; ".join(due) + "."
    return screen.Shown(said, screen.card("table", "Appointments", "wellness-appts", text="\n".join(due),
                                          columns=["When", "What", "Note", "Countdown"], rows=rows))


def appt_remove(settings: Settings, words, confirmed: bool) -> str:
    appts = store.load(settings, "appointments", [])
    found = [a for a in appts if a in store.find(appts, "kind", words) or a in store.find(appts, "note", words)
             or a["date"] == store.clean(words)]
    if not found:
        raise ValueError("No appointment matches that.")
    names = "; ".join(f"{a['kind']} on {a['date']}" for a in found)
    if not confirmed:
        return f"That matches: {names}. Ask the user to confirm removing it, then call again with confirmed true."
    store.save(settings, "appointments", [a for a in appts if a not in found])
    return f"Removed {names}."


# Records

def record_add(settings: Settings, args: dict) -> str:
    name = store.need(args.get("name"), "record", 100)
    kind = args.get("kind") if args.get("kind") in RECORD_KINDS else "other"
    entry = {"kind": kind, "name": name, "date": store.day(args.get("date")).isoformat(),
             "note": store.clean(args.get("note"), 200)}
    records = store.load(settings, "records", [])
    records.append(entry)
    store.save(settings, "records", sorted(records, key=lambda r: r["date"]))
    return f"Saved {kind}: {name}, {store.spoken(date.fromisoformat(entry['date']))}. It's kept only on this PC."


def records_show(settings: Settings, kind=None):
    records = [r for r in store.load(settings, "records", []) if not kind or r["kind"] == kind]
    if not records:
        return "No health records saved yet."
    rows = [[r["date"], r["kind"], r["name"], r["note"]] for r in reversed(records)]
    return screen.Shown(f"{store.plural(len(records), 'record')} on the screen.", screen.card(
        "table", "Health records", "wellness-records", columns=["Date", "Type", "Name", "Note"], rows=rows,
        text="Kept only on this PC."))


def record_remove(settings: Settings, words, confirmed: bool) -> str:
    records = store.load(settings, "records", [])
    found = store.find(records, "name", words)
    if not found:
        raise ValueError("No record matches that.")
    names = "; ".join(f"{r['name']} ({r['date']})" for r in found)
    if not confirmed:
        return f"That matches: {names}. Ask the user to confirm removing it, then call again with confirmed true."
    store.save(settings, "records", [r for r in records if r not in found])
    return f"Removed {names}."


# Cycle tracker

def _starts(settings: Settings) -> list[date]:
    return sorted({date.fromisoformat(s) for s in store.load(settings, "cycle", {}).get("starts", [])})


def period_start(settings: Settings, when) -> str:
    d = store.day(when)
    if d > store.today():
        raise ValueError("Log a period start on or before today.")
    starts = sorted({*_starts(settings), d})
    store.save(settings, "cycle", {"starts": [s.isoformat() for s in starts][-60:]})
    avg, nxt = predict(starts)
    extra = f" Next predicted around {store.spoken(nxt)}." if nxt else ""
    return f"Logged a period start on {store.spoken(d)}.{extra}"


def predict(starts: list[date]) -> tuple[float | None, date | None]:
    gaps = [(b - a).days for a, b in zip(starts, starts[1:]) if MIN_CYCLE <= (b - a).days <= MAX_CYCLE][-6:]
    if not gaps:
        return None, None
    avg = sum(gaps) / len(gaps)
    return avg, starts[-1] + timedelta(days=round(avg))


def _month(year: int, month: int, marks: dict[date, str]) -> list[list[str]]:
    rows = [[f"{calendar.month_abbr[month]} {year}", "", "", "", "", "", ""]]
    for week in calendar.Calendar().monthdatescalendar(year, month):
        rows.append([(f"{d.day}{marks.get(d, '')}" if d.month == month else "") for d in week])
    return rows


def cycle_show(settings: Settings):
    starts = _starts(settings)
    if not starts:
        return "No period starts logged yet."
    avg, nxt = predict(starts)
    today = store.today()
    marks = {s: " •" for s in starts}
    if nxt:
        marks[nxt] = " ?"
    marks[today] = marks.get(today, "") + " <"
    second = store.add_months(today.replace(day=1), 1)
    rows = _month(today.year, today.month, marks) + _month(second.year, second.month, marks)
    said = (f"Average cycle {avg:.0f} days; next period predicted around {store.spoken(nxt)} ({store.countdown(nxt)})."
            if nxt else f"Last period started {store.spoken(starts[-1])}; log one more start to predict the next.")
    key = "• period started, ? predicted start (a simple average, not exact), < today. Kept only on this PC."
    return screen.Shown(said, screen.card("table", "Cycle calendar", "wellness-cycle", text=f"{said}\n{key}",
                                          columns=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], rows=rows))


def period_remove(settings: Settings, when, confirmed: bool) -> str:
    d = store.day(when)
    starts = _starts(settings)
    if d not in starts:
        raise ValueError(f"No period start logged on {store.spoken(d)}.")
    if not confirmed:
        return f"Ask the user to confirm removing the period start on {store.spoken(d)}, then call again with confirmed true."
    store.save(settings, "cycle", {"starts": [s.isoformat() for s in starts if s != d]})
    return f"Removed the period start on {store.spoken(d)}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "health_records",
        "description": "Private health records kept on this PC, with pop-ups. appt_add (kind doctor, dentist, "
                       "optician..., date, time, note; past visits count too), appointments (upcoming list with "
                       "countdowns and check-ups due: dentist every 6 months, eye test every 2 years), "
                       "appt_remove. record_add (vaccination, test result, allergy... name, date, note), records, "
                       "record_remove. period_start (date a period started), cycle (average cycle length, "
                       "predicted next period, calendar), period_remove. Removals need words or date, and "
                       "confirmed true only after the user confirms. Never give medical advice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "appt_add", "appointments", "appt_remove", "record_add", "records", "record_remove",
                    "period_start", "cycle", "period_remove"]},
                "kind": {"type": "string", "enum": list(dict.fromkeys(KINDS + RECORD_KINDS))},
                "date": {"type": "string", "description": "YYYY-MM-DD, today, yesterday or a weekday."},
                "time": {"type": "string", "description": "e.g. 14:30."},
                "name": {"type": "string", "description": "record_add: e.g. 'Flu jab'."},
                "note": {"type": "string"},
                "words": {"type": "string", "description": "Removals: words from the entry."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"health_records"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, ok = args.get("action"), bool(args.get("confirmed"))
    if action == "appt_add":
        return appt_add(settings, args)
    if action == "appointments":
        return appts_show(settings)
    if action == "appt_remove":
        return appt_remove(settings, args.get("words") or args.get("date"), ok)
    if action == "record_add":
        return record_add(settings, args)
    if action == "records":
        return records_show(settings, args.get("kind") if args.get("kind") in RECORD_KINDS else None)
    if action == "record_remove":
        return record_remove(settings, args.get("words") or args.get("name"), ok)
    if action == "period_start":
        return period_start(settings, args.get("date"))
    if action == "cycle":
        return cycle_show(settings)
    if action == "period_remove":
        return period_remove(settings, args.get("date"), ok)
    raise ValueError(f"Unknown action {action}.")
