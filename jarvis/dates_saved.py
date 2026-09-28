"""Saved dates and focus clocks: countdowns to named events, birthdays, a stopwatch and pomodoro focus sessions.

Countdowns, birthdays and focus sessions live in countdowns.json, birthdays.json and focus.json in the memory
folder and never leave this PC. The stopwatch is in-process only. A focus session runs as a timers.py timer.
"""

import json
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import memory
import timers
from config import Settings

MAX_ENTRIES = 200
FOCUS_SECONDS = 25 * 60
FOCUS_LABEL = "focus"
KEEP_FOCUS_DAYS = 60
FILES = {"countdown": "countdowns.json", "birthday": "birthdays.json"}

stopwatch: dict = {"started": None, "elapsed": 0.0, "laps": []}


def path(settings: Settings, kind: str) -> Path:
    return memory.root(settings) / FILES.get(kind, "focus.json")


def load(settings: Settings, kind: str) -> dict:
    try:
        found = json.loads(path(settings, kind).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def save(settings: Settings, kind: str, data: dict) -> None:
    path(settings, kind).parent.mkdir(parents=True, exist_ok=True)
    path(settings, kind).write_text(json.dumps(data, indent=2), encoding="utf-8")


def _name(value) -> str:
    name = re.sub(r"\s+", " ", str(value or "")).strip()[:60]
    if not name:
        raise ValueError("What's it called?")
    return name


def _key(data: dict, name: str) -> str | None:
    return next((k for k in data if k.lower() == name.strip().lower()), None)


def _plural(n: int, unit: str) -> str:
    return f"{n} {unit}{'' if n == 1 else 's'}"


def _nice(d: date) -> str:
    return f"{d:%A} {d.day} {d:%B %Y}"


# ---- countdowns and birthdays ----------------------------------------------------------

def _birthday(value: str) -> str:
    """'1990-04-12' or '04-12' / '--04-12' (year unknown), checked."""
    value = str(value or "").strip().lstrip("-")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        date.fromisoformat(value)
        return value
    if re.fullmatch(r"\d{2}-\d{2}", value):
        date.fromisoformat(f"2000-{value}")
        return value
    raise ValueError("Give the birthday as YYYY-MM-DD, or MM-DD if you don't know the year.")


def _next_birthday(value: str, today: date) -> tuple[date, int | None]:
    month, day = int(value[-5:-3]), int(value[-2:])
    for year in (today.year, today.year + 1):
        try:
            when = date(year, month, day)
        except ValueError:  # 29 February outside a leap year
            when = date(year, 2, 28)
        if when >= today:
            return when, (year - int(value[:4])) if len(value) == 10 else None
    raise AssertionError


def add(settings: Settings, kind: str, name: str, when: str) -> str:
    name, data = _name(name), load(settings, kind)
    if kind == "birthday":
        value = _birthday(when)
    else:
        try:
            value = date.fromisoformat(str(when or "").strip()[:10]).isoformat()
        except ValueError:
            raise ValueError("Give the date as YYYY-MM-DD.") from None
    key = _key(data, name) or name
    if key not in data and len(data) >= MAX_ENTRIES:
        raise ValueError(f"That's a lot of {kind}s; remove one first.")
    data[key] = value
    save(settings, kind, data)
    return f"Saved {key}'s birthday." if kind == "birthday" else f"Saved the countdown to {key}."


def list_countdowns(settings: Settings, today: date) -> str:
    data = load(settings, "countdown")
    if not data:
        return "No countdowns saved."
    lines = []
    for name, value in sorted(data.items(), key=lambda kv: kv[1]):
        d = date.fromisoformat(value)
        n = (d - today).days
        left = "today" if n == 0 else f"{_plural(n, 'day')} left" if n > 0 else f"{_plural(-n, 'day')} ago"
        lines.append(f"- {name}: {_nice(d)}, {left}")
    return "Countdowns:\n" + "\n".join(lines)


def list_birthdays(settings: Settings, today: date) -> str:
    data = load(settings, "birthday")
    if not data:
        return "No birthdays saved."
    coming = sorted(((_next_birthday(v, today), k) for k, v in data.items()), key=lambda c: (c[0][0], c[1]))
    lines = []
    for (when, age), name in coming[:10]:
        n = (when - today).days
        turning = f", turning {age}" if age is not None else ""
        lines.append(f"- {name}: {_nice(when)}, {'today' if n == 0 else 'in ' + _plural(n, 'day')}{turning}")
    return "Next birthdays, soonest first:\n" + "\n".join(lines)


def remove(settings: Settings, kind: str, name: str, confirmed: bool) -> str:
    data = load(settings, kind)
    key = _key(data, str(name or ""))
    if key is None:
        return f"There's no {kind} called {name}."
    if not confirmed:
        return f"Ask the user to confirm removing the {kind} for {key}, then call again with confirmed true."
    del data[key]
    save(settings, kind, data)
    return f"Removed the {kind} for {key}."


# ---- stopwatch -------------------------------------------------------------------------

def _elapsed(now: float) -> float:
    running = now - stopwatch["started"] if stopwatch["started"] is not None else 0.0
    return stopwatch["elapsed"] + running


def stopwatch_action(action: str, now: float | None = None) -> str:
    now = time.monotonic() if now is None else now
    if action == "stopwatch_start":
        stopwatch.update(started=now, elapsed=0.0, laps=[])
        return "Stopwatch started."
    if stopwatch["started"] is None and not stopwatch["elapsed"]:
        return "The stopwatch isn't running."
    total = _elapsed(now)
    if action == "lap":
        if stopwatch["started"] is None:
            return "The stopwatch is stopped."
        stopwatch["laps"].append(total)
        split = total - (stopwatch["laps"][-2] if len(stopwatch["laps"]) > 1 else 0.0)
        return f"Lap {len(stopwatch['laps'])}: {_spoken(split)}. Total {_spoken(total)}."
    if action == "stopwatch_stop":
        if stopwatch["started"] is None:
            return f"The stopwatch is already stopped at {_spoken(total)}."
        stopwatch.update(started=None, elapsed=total)
        laps = f" over {_plural(len(stopwatch['laps']), 'lap')}" if stopwatch["laps"] else ""
        return f"Stopwatch stopped at {_spoken(total)}{laps}."
    state = "running" if stopwatch["started"] is not None else "stopped"
    return f"The stopwatch is {state} at {_spoken(total)}."


def _spoken(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    return timers.spoken(seconds)


# ---- pomodoro focus sessions ------------------------------------------------------------

def _focus_log(settings: Settings, now: datetime) -> list[str]:
    cutoff = (now - timedelta(days=KEEP_FOCUS_DAYS)).isoformat()
    return [s for s in load(settings, "focus").get("sessions") or [] if isinstance(s, str) and s >= cutoff]


def _done_today(sessions: list[str], now: datetime) -> int:
    finish = timedelta(seconds=FOCUS_SECONDS)
    return sum(1 for s in sessions
               if s[:10] == now.date().isoformat() and datetime.fromisoformat(s) + finish <= now)


def focus_start(settings: Settings, now: datetime | None = None) -> str:
    now = now or datetime.now()
    if FOCUS_LABEL in timers.timers:
        return focus_status(settings, now)
    timers.set_timer(settings, FOCUS_SECONDS, FOCUS_LABEL)
    sessions = _focus_log(settings, now) + [now.isoformat(timespec="seconds")]
    save(settings, "focus", {"sessions": sessions})
    return f"Focus session started: 25 minutes. {_plural(_done_today(sessions, now), 'session')} done today so far."


def focus_status(settings: Settings, now: datetime | None = None) -> str:
    now = now or datetime.now()
    done = _plural(_done_today(_focus_log(settings, now), now), "focus session")
    timer = timers.timers.get(FOCUS_LABEL)
    if timer:
        return f"{timers.spoken(timer.ends - time.monotonic())} left in this focus session. {done} done today."
    return f"No focus session running. {done} done today."


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "saved_dates",
            "description": "Countdowns to named events and people's birthdays, kept only on this PC. action "
                           "'add' saves kind with name and date (countdown YYYY-MM-DD; birthday YYYY-MM-DD, or "
                           "MM-DD without the year); 'list' gives days left, or next birthdays and ages turned; "
                           "'remove' deletes one: set confirmed true only after the user confirms.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "list", "remove"]},
                    "kind": {"type": "string", "enum": ["countdown", "birthday"]},
                    "name": {"type": "string"},
                    "date": {"type": "string"},
                    "confirmed": {"type": "boolean"},
                },
                "required": ["action", "kind"],
                "additionalProperties": False,
            },
        },
        {
            "name": "focus_clock",
            "description": "Stopwatch (start, lap, stop, read) and 25-minute pomodoro focus sessions that chime "
                           "when done; focus_status gives time left and sessions done today.",
            "input_schema": {
                "type": "object",
                "properties": {"action": {"type": "string", "enum": [
                    "stopwatch_start", "lap", "stopwatch_stop", "stopwatch_read", "focus_start", "focus_status"]}},
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"saved_dates", "focus_clock"}


async def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    """Async so focus_start runs on the event loop that timers.py needs."""
    action = args.get("action")
    if name == "focus_clock":
        if action == "focus_start":
            return focus_start(settings)
        if action == "focus_status":
            return focus_status(settings)
        return stopwatch_action(action)
    kind = args.get("kind") if args.get("kind") in FILES else "countdown"
    if action == "add":
        return add(settings, kind, args.get("name"), args.get("date"))
    if action == "remove":
        return remove(settings, kind, args.get("name"), bool(args.get("confirmed")))
    return list_birthdays(settings, date.today()) if kind == "birthday" else list_countdowns(settings, date.today())
