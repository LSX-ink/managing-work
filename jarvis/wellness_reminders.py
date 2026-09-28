"""Health reminders through the normal reminders: 20-20-20 eye breaks and posture checks in working hours,
and a drink of water every couple of hours.

Reminders only repeat daily, on weekdays or weekly, so a schedule is one repeating reminder per time slot.
"""

from datetime import datetime, timedelta

import reminders
import screen
import wellness_store as store
from config import Settings

MAX_SLOTS = 12
KINDS = {
    "eye_breaks": ("Eye break: look at something about 20 feet away for 20 seconds.", "09:00", "17:00", 60, "weekdays"),
    "posture": ("Posture check: sit back, shoulders down, feet flat, and have a quick stretch.", "10:00", "16:00", 120,
                "weekdays"),
    "hydration": ("Time for a glass of water.", "09:00", "21:00", 120, "daily"),
}


def _slots(start: str, end: str, every: int) -> list[str]:
    t, stop = datetime.strptime(start, "%H:%M"), datetime.strptime(end, "%H:%M")
    if stop <= t:
        raise ValueError("The end time must be after the start time.")
    out = []
    while t <= stop:
        out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=every)
    if len(out) > MAX_SLOTS:
        raise ValueError(f"That's {len(out)} reminders a day; space them out to {MAX_SLOTS} or fewer.")
    return out


def _mine(settings: Settings, kind: str) -> list[dict]:
    return [r for r in reminders.load(settings) if r["text"] == KINDS[kind][0]]


def _drop(settings: Settings, kind: str) -> int:
    found = reminders.load(settings)
    keep = [r for r in found if r["text"] != KINDS[kind][0]]
    if len(keep) != len(found):
        reminders.save(settings, keep)
    return len(found) - len(keep)


def schedule(settings: Settings, kind: str, args: dict) -> str:
    text, start, end, every, repeat = KINDS[kind]
    start = store.clock(args["start"], "start time") if args.get("start") else start
    end = store.clock(args["end"], "end time") if args.get("end") else end
    every = int(store.number(args.get("every_minutes") or every, "gap", 30, 480))
    repeat = args.get("days") if args.get("days") in ("daily", "weekdays") else repeat
    slots = _slots(start, end, every)
    others = len(reminders.load(settings)) - len(_mine(settings, kind))
    if others + len(slots) > reminders.MAX_REMINDERS:
        raise ValueError("There isn't room for that many more reminders; cancel some first.")
    _drop(settings, kind)
    now = store.now()
    first = now.date()
    while repeat == "weekdays" and first.weekday() >= 5:
        first += timedelta(days=1)
    for slot in slots:
        reminders.add(settings, f"{first.isoformat()} {slot}", text, repeat, now=now)
    days = "every weekday" if repeat == "weekdays" else "every day"
    return (f"Set {store.plural(len(slots), 'reminder')} {days}, every {every} minutes from {start} to {end}: "
            f"{text.split(':')[0].lower()}.")


def show(settings: Settings):
    items = []
    for kind, (text, *_rest) in KINDS.items():
        mine = sorted(r["at"][11:] for r in _mine(settings, kind))
        label = kind.replace("_", " ").capitalize()
        items.append({"label": f"{label}: {', '.join(mine)}" if mine else f"{label}: off",
                      "say": f"Stop my {label.lower()} reminders." if mine else f"Turn on {label.lower()} reminders."})
    on = [i["label"].split(":")[0] for i in items if not i["label"].endswith("off")]
    said = ("Health reminders on: " + ", ".join(on) + ".") if on else "No health reminders are on."
    return screen.Shown(said, screen.card("list", "Health reminders", "wellness-reminders", items=items))


def stop(settings: Settings, kind, confirmed: bool) -> str:
    kinds = list(KINDS) if kind in (None, "", "all") else [kind]
    if any(k not in KINDS for k in kinds):
        raise ValueError(f"Which reminders? One of: {', '.join(KINDS)}, or all.")
    count = sum(len(_mine(settings, k)) for k in kinds)
    if not count:
        return "Those reminders aren't on."
    if not confirmed:
        return f"That would cancel {store.plural(count, 'reminder')}. Ask the user to confirm, then call again with confirmed true."
    removed = sum(_drop(settings, k) for k in kinds)
    return f"Cancelled {store.plural(removed, 'reminder')}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "health_reminders",
        "description": "Repeating health reminders said aloud: eye_breaks (20-20-20 eye break every hour in "
                       "working hours, weekdays), posture (posture check and stretch), hydration (drink water "
                       "every 2 hours). Optional start, end (HH:MM), every_minutes, days. show lists them; stop "
                       "cancels one kind or all, with confirmed true only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["eye_breaks", "posture", "hydration", "show", "stop"]},
                "start": {"type": "string", "description": "First reminder, e.g. 09:00."},
                "end": {"type": "string", "description": "Last reminder, e.g. 17:30."},
                "every_minutes": {"type": "integer", "description": "Gap between reminders, 30 to 480."},
                "days": {"type": "string", "enum": ["weekdays", "daily"]},
                "kind": {"type": "string", "enum": [*KINDS, "all"], "description": "stop: which reminders."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"health_reminders"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action in KINDS:
        return schedule(settings, action, args)
    if action == "show":
        return show(settings)
    if action == "stop":
        return stop(settings, args.get("kind"), bool(args.get("confirmed")))
    raise ValueError(f"Unknown action {action}.")
