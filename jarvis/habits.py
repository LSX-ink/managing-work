"""Habit streaks: "I went to the gym", "how's my reading streak?".

Days done per habit are kept in habits.json in the memory folder.
"""

import json
import re
from datetime import date, timedelta
from pathlib import Path

import memory
from config import Settings

MAX_HABITS = 30
KEEP_DAYS = 400


def path(settings: Settings) -> Path:
    return memory.root(settings) / "habits.json"


def load(settings: Settings) -> dict[str, list[str]]:
    try:
        found = json.loads(path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in found.items() if isinstance(v, list)} if isinstance(found, dict) else {}


def save(settings: Settings, habits: dict[str, list[str]]) -> None:
    path(settings).parent.mkdir(parents=True, exist_ok=True)
    path(settings).write_text(json.dumps(habits, indent=2), encoding="utf-8")


def _key(habits: dict, name: str) -> str | None:
    name = name.strip().lower()
    return next((k for k in habits if k.lower() == name), None)


def streak(days: list[str], today: date) -> int:
    """Days in a row up to today, or up to yesterday when today isn't done yet."""
    have = set(days)
    day = today if today.isoformat() in have else today - timedelta(days=1)
    count = 0
    while day.isoformat() in have:
        count += 1
        day -= timedelta(days=1)
    return count


def mark(settings: Settings, name: str, today: date | None = None, when: str = "today") -> str:
    today = today or date.today()
    name = re.sub(r"\s+", " ", name).strip()[:40]
    if not name:
        raise ValueError("Which habit?")
    habits = load(settings)
    key = _key(habits, name)
    if key is None:
        if len(habits) >= MAX_HABITS:
            raise ValueError("That's a lot of habits; stop tracking one first.")
        key = name
        habits[key] = []
    day = today - timedelta(days=1) if when == "yesterday" else today
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    habits[key] = sorted({*habits[key], day.isoformat()} - {d for d in habits[key] if d < cutoff})
    save(settings, habits)
    run = streak(habits[key], today)
    return f"{key} done {when}. Streak: {run} day{'s' if run != 1 else ''}."


def report(settings: Settings, today: date | None = None) -> str:
    today = today or date.today()
    habits = load(settings)
    if not habits:
        return "No habits tracked yet."
    week = {(today - timedelta(days=i)).isoformat() for i in range(7)}
    lines = []
    for name, days in habits.items():
        state = "done today" if today.isoformat() in days else "not yet today"
        lines.append(f"- {name}: streak {streak(days, today)} days, {len(week & set(days))} of the last 7 days, {state}")
    return "Habits:\n" + "\n".join(lines)


def forget(settings: Settings, name: str) -> str:
    habits = load(settings)
    key = _key(habits, name)
    if key is None:
        return f"I'm not tracking {name}."
    del habits[key]
    save(settings, habits)
    return f"Stopped tracking {key}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "habits",
        "description": "Track daily habits and streaks (gym, reading, water, no sugar). action 'done' marks a "
                       "habit done today (or yesterday with when='yesterday'); 'read' gives every streak; 'stop' "
                       "stops tracking one. New habit names start tracking automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["done", "read", "stop"]},
                "habit": {"type": "string", "description": "Short name, e.g. 'gym'."},
                "when": {"type": "string", "enum": ["today", "yesterday"]},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"habits"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = args.get("action")
    if action == "done":
        return mark(settings, args.get("habit") or "", when=args.get("when") or "today")
    if action == "stop":
        return forget(settings, args.get("habit") or "")
    return report(settings)
