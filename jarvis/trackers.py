"""Track anything: the user's own trackers ("track coffees", "track back pain, 1 to 5"), logged by voice
("log 3 coffees", "I meditated 10 minutes", "rate my back pain 2"), tap counters with a +1 pop-up, milestones,
daily reminders to log, and CSV export and import.

Saved in trackers-data.json in the memory folder; CSV files go to a memory folder (Personal/Trackers by default).
"""

import csv
import io
import re
from datetime import date, datetime, timedelta

import memory
import reminders
import screen
import trackers_store as store
from config import Settings

TYPE_WORDS = {"number": "number", "yes_no": "yes or no", "rating": "1 to 5 rating", "count": "count",
              "duration": "time", "text": "note"}
YES = {"", "yes", "y", "true", "done", "did", "1"}
NO = {"no", "n", "false", "didn't", "not", "0"}
EXPORT_FOLDER = "Personal/Trackers"
MAX_IMPORT = 3000


def create(settings: Settings, args: dict) -> str:
    data = store.trackers(settings)
    name = store.clean(args.get("tracker"))
    if not name:
        raise ValueError("What should the tracker be called?")
    same = next((n for n in data["trackers"] if store.stem(n) == store.stem(name)), None)
    if same:
        raise ValueError(f"There's already a tracker called {same}.")
    if len(data["trackers"]) >= store.MAX_TRACKERS:
        raise ValueError("That's a lot of trackers; delete one first.")
    kind = args.get("type") or "number"
    if kind not in store.TYPES:
        raise ValueError(f"The type must be one of: {', '.join(store.TYPES)}.")
    info = {"type": kind, "created": store.today().isoformat()}
    if args.get("unit") and kind in ("number", "count"):
        info["unit"] = store.clean(args["unit"], 16)
    if args.get("goal") is not None and kind != "text":
        info["goal"] = _number(args["goal"], "goal")
        info["goal_type"] = "at_most" if args.get("goal_type") == "at_most" else "at_least"
    if kind == "number" and args.get("per_day") == "latest":
        info["per_day"] = "latest"
    data["trackers"][name] = info
    store.save_trackers(settings, data)
    goal = ""
    if "goal" in info:
        goal = f", daily goal {'at most' if info['goal_type'] == 'at_most' else 'at least'} {store.fmt(info['goal'], info)}"
    return f"Tracking {name} as a {TYPE_WORDS[kind]}{goal}."


def _number(value, what: str) -> float:
    m = re.search(r"-?\d+(?:\.\d+)?", str(value if value is not None else ""))
    if not m:
        raise ValueError(f"The {what} must be a number.")
    n = float(m.group(0))
    if abs(n) > 1e9:
        raise ValueError(f"That {what} doesn't look right.")
    return n


def minutes(value) -> float:
    """'10', '1:30', '1h 20m', '90 min', '1.5 hours' -> minutes."""
    text = str(value if value is not None else "").strip().lower()
    clock = re.fullmatch(r"(\d+):(\d{1,2})", text)
    if clock:
        return int(clock.group(1)) * 60 + int(clock.group(2))
    hours = re.search(r"(\d+(?:\.\d+)?)\s*h", text)
    mins = re.search(r"(\d+(?:\.\d+)?)\s*m", text)
    if hours or mins:
        return round(float(hours.group(1) if hours else 0) * 60 + float(mins.group(1) if mins else 0), 1)
    return _number(text, "time")


def parse(info: dict, value, note: str) -> float:
    kind = info["type"]
    text = str(value if value is not None else "").strip().lower()
    if kind == "text":
        if not (note or text):
            raise ValueError("What's the note?")
        return 1
    if kind == "yes_no":
        if text in YES:
            return 1
        if text in NO:
            return 0
        raise ValueError("Is that a yes or a no?")
    if kind == "count" and not text:
        return 1
    if not text:
        raise ValueError("What value?")
    if kind == "duration":
        return minutes(text)
    n = _number(text, "value")
    if kind == "rating" and not 1 <= n <= 5:
        raise ValueError("A rating goes from 1 to 5.")
    return n


def _round_passed(before: float, after: float) -> float | None:
    passed = None
    for power in range(1, 8):
        for step in (1, 2.5, 5):
            mark = step * 10 ** power
            if before < mark <= after:
                passed = mark
    return passed


def milestone(info: dict, before: float, after: float) -> str:
    if info["type"] not in store.ADD_UP or info.get("per_day") == "latest":
        return ""
    if info["type"] == "duration":
        mark = _round_passed(before / 60, after / 60)
        return f" Milestone: over {mark:g} hours in total!" if mark else ""
    mark = _round_passed(before, after)
    unit = store.unit_of(info)
    return f" Milestone: over {mark:,.0f}{' ' + unit if unit else ''} in total!" if mark else ""


def log(settings: Settings, args: dict):
    data = store.trackers(settings)
    name = store.need(data, args.get("tracker") or "")
    info = data["trackers"][name]
    note = store.clean(args.get("note") or (args.get("value") if info["type"] == "text" else ""), 300)
    value = parse(info, args.get("value"), note)
    day = _day(args.get("day"))
    values = data["values"].setdefault(name, {})
    before = sum(values.values())
    adds = info["type"] in store.ADD_UP and info.get("per_day") != "latest" and not args.get("replace")
    key = day.isoformat()
    values[key] = round(values.get(key, 0) + value if adds else value, 2)
    if note:
        data["notes"].setdefault(name, {})[key] = note
    store.save_trackers(settings, data)
    when = "today" if day == store.today() else f"{day.strftime('%A')} {day.day} {day.strftime('%B')}"
    text = f"{name}: {store.fmt(values[key], info)} {when}."
    if info["type"] == "text":
        text = f"Noted in {name} for {when}."
    if info.get("goal") is not None:
        text += " Goal met." if store.met(values[key], info) else ""
    text += milestone(info, before, sum(values.values()))
    if info["type"] == "count":
        return screen.Shown(text, counters_card(settings, data))
    return text


def _day(value) -> date:
    text = store.clean(value).lower()
    base = store.today()
    if not text or text == "today":
        return base
    if text == "yesterday":
        return base - timedelta(days=1)
    try:
        day = date.fromisoformat(text)
    except ValueError:
        raise ValueError("Give the day as YYYY-MM-DD, or say yesterday.") from None
    if day > base:
        raise ValueError("I can't log a day that hasn't happened yet.")
    return day


def listing(settings: Settings) -> screen.Shown | str:
    data = store.trackers(settings)
    if not data["trackers"]:
        return "No trackers yet. Say something like 'track coffees as a count with a goal of at most 3'."
    today = store.today()
    rows = []
    for name, info in data["trackers"].items():
        values = data["values"].get(name, {})
        goal = "" if info.get("goal") is None else f"{'≤' if info.get('goal_type') == 'at_most' else '≥'} {store.fmt(info['goal'], info)}"
        streak = store.goal_streak(values, info, today) if goal else ""
        rows.append([name, TYPE_WORDS[info["type"]], goal, store.fmt(values.get(today.isoformat()), info), str(streak)])
    card = screen.card("table", "Trackers", "trackers-list", columns=["Tracker", "Type", "Daily goal", "Today", "Goal streak"],
                       rows=rows, buttons=[{"label": "Counters", "say": "Show my counters."},
                                           {"label": "Month review", "say": "Show my trackers' monthly review."}])
    return screen.Shown(f"You have {len(rows)} tracker{'s' if len(rows) != 1 else ''}.", card)


def delete(settings: Settings, wanted: str, confirmed: bool) -> str:
    data = store.trackers(settings)
    name = store.need(data, wanted)
    days = len(data["values"].get(name, {}))
    if not confirmed:
        return f"Delete the {name} tracker and its {days} day{'s' if days != 1 else ''} of values? Ask the user to confirm first."
    for key in ("trackers", "values", "notes"):
        data[key].pop(name, None)
    store.save_trackers(settings, data)
    return f"Deleted the {name} tracker."


def counters_card(settings: Settings, data: dict | None = None) -> dict:
    data = data or store.trackers(settings)
    today = store.today().isoformat()
    items = []
    for name, info in data["trackers"].items():
        if info["type"] == "count":
            n = data["values"].get(name, {}).get(today, 0)
            goal = f" (goal {'at most' if info.get('goal_type') == 'at_most' else 'at least'} {info['goal']:g})" if info.get("goal") is not None else ""
            items.append({"label": f"+1  {name}: {n:g} today{goal}", "say": f"Add one to my {name} counter."})
    return screen.card("list", "Counters", "trackers-counters", items=items,
                       text="Tap one to add 1. Counts start again at zero each day.")


def counters(settings: Settings):
    card = counters_card(settings)
    if not card["items"]:
        return "No counters yet. Say something like 'make a push-ups counter'."
    return screen.Shown(f"{len(card['items'])} counter{'s' if len(card['items']) != 1 else ''} on the screen.", card)


def remind(settings: Settings, wanted: str, at: str, now: datetime | None = None) -> str:
    now = now or datetime.now()
    data = store.trackers(settings)
    name = store.need(data, wanted) if wanted else ""
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})", store.clean(at))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        raise ValueError("Give the reminder time as HH:MM, e.g. 21:00.")
    when = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    if when <= now:
        when += timedelta(days=1)
    what = f"Log your {name} for today" if name else "Log today's trackers"
    return reminders.add(settings, when.strftime("%Y-%m-%d %H:%M"), what, "daily", now)


def export(settings: Settings, wanted: str, folder: str) -> screen.Shown:
    data = store.trackers(settings)
    name = store.need(data, wanted)
    values, notes = data["values"].get(name, {}), data["notes"].get(name, {})
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["date", "value", "note"])
    for day in sorted(set(values) | set(notes)):
        writer.writerow([day, "" if day not in values else f"{values[day]:g}", notes.get(day, "")])
    target = memory.folder(settings, folder or EXPORT_FOLDER, create=True)
    path = target / f"{memory.safe_name(name, 'tracker name')}.csv"
    path.write_text(out.getvalue(), encoding="utf-8")
    rel = path.relative_to(memory.root(settings)).as_posix()
    return screen.Shown(f"Saved {name} as {rel}.", screen.file_card(settings, path))


def import_csv(settings: Settings, wanted: str, folder: str, filename: str, confirmed: bool) -> str:
    data = store.trackers(settings)
    name = store.need(data, wanted)
    info = data["trackers"][name]
    path = screen.find_file(settings, folder, filename)
    if path.suffix.lower() != ".csv":
        raise ValueError(f"{path.name} isn't a CSV file.")
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig", errors="replace"))))[:MAX_IMPORT]
    values = data["values"].setdefault(name, {})
    added = kept = skipped = 0
    for row in rows:
        try:
            day = date.fromisoformat(row[0].strip()).isoformat()
            value = parse(info, row[1] if len(row) > 1 else "", row[2] if len(row) > 2 else "")
        except (ValueError, IndexError):
            skipped += 1
            continue
        if day in values and not confirmed:
            kept += 1
            continue
        values[day] = value
        if len(row) > 2 and row[2].strip():
            data["notes"].setdefault(name, {})[day] = store.clean(row[2], 300)
        added += 1
    if not added and not kept:
        raise ValueError(f"I couldn't find any date,value rows in {path.name}.")
    store.save_trackers(settings, data)
    text = f"Imported {added} day{'s' if added != 1 else ''} into {name} from {path.name}."
    if kept:
        text += f" Kept {kept} day{'s' if kept != 1 else ''} already logged; confirm to overwrite them."
    return text


ACTIONS = ["create", "list", "delete", "log", "counters", "remind", "export", "import"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "trackers",
        "description": "Track anything the user chooses, with their own trackers and tap counters. create: a new "
                       "tracker (tracker name, type number/yes_no/rating 1-5/count/duration/text note, unit, "
                       "optional daily goal; goal_type at_most for things to cut down, e.g. cigarettes). A 'counter' "
                       "is a count tracker. log: record a value by voice ('log 3 coffees', 'I meditated 10 "
                       "minutes', 'rate my back pain 2', 'add one to push-ups'); the reply mentions goals and "
                       "milestones. list: all trackers. delete: set confirmed true only after the user confirms. "
                       "counters: pop-up of counters with +1 taps (reset daily). remind: a daily reminder to log at "
                       "time HH:MM. export: save a tracker as CSV and show it. import: read a date,value CSV from "
                       "the memory folders into a tracker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "tracker": {"type": "string", "description": "Tracker name as the user says it, e.g. 'coffee'."},
                "type": {"type": "string", "enum": list(store.TYPES)},
                "unit": {"type": "string", "description": "create: for number or count, e.g. 'km', 'cups'."},
                "goal": {"type": "number", "description": "create: daily goal (duration in minutes)."},
                "goal_type": {"type": "string", "enum": ["at_least", "at_most"]},
                "per_day": {"type": "string", "enum": ["add", "latest"],
                            "description": "create number: add logs up per day, or keep the latest (e.g. weight)."},
                "value": {"type": "string", "description": "log: a number, 'yes'/'no', a time like '1h 20m', "
                                                           "or the words for a text tracker. Blank adds 1 to a count."},
                "note": {"type": "string", "description": "log: an optional note for the day."},
                "day": {"type": "string", "description": "log: 'yesterday' or YYYY-MM-DD; default today."},
                "replace": {"type": "boolean", "description": "log: replace the day's value instead of adding."},
                "time": {"type": "string", "description": "remind: HH:MM, 24-hour."},
                "folder": {"type": "string", "description": "export/import: memory folder, e.g. 'Personal/Trackers'."},
                "filename": {"type": "string", "description": "import: the CSV file's name."},
                "confirmed": {"type": "boolean", "description": "delete, or import over logged days: only after "
                                                                "the user confirms."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"trackers"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    confirmed = args.get("confirmed") is True
    tracker = args.get("tracker") or ""
    if action == "create":
        return create(settings, args)
    if action == "log":
        return log(settings, args)
    if action == "delete":
        return delete(settings, tracker, confirmed)
    if action == "counters":
        return counters(settings)
    if action == "remind":
        return remind(settings, tracker, args.get("time") or "")
    if action == "export":
        return export(settings, tracker, args.get("folder") or "")
    if action == "import":
        return import_csv(settings, tracker, args.get("folder") or "", args.get("filename") or "", confirmed)
    return listing(settings)
