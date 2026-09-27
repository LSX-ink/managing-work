"""Reminders at a clock time ("remind me at 7 pm to call Mum", "every day at 8 to take my tablets").

Unlike timers they are saved in reminders.json in the memory folder, so they survive a restart. A reminder
that comes due while no Jarvis page is open waits, and is said as soon as one is.
"""

import asyncio
import datetime as dt
import json
import re
import uuid
from pathlib import Path
from typing import Awaitable, Callable

from config import Settings

Announce = Callable[[str, str], Awaitable[None]]
CHECK_SECONDS = 15
MAX_REMINDERS = 100
REPEATS = ("once", "daily", "weekdays", "weekly")


def path(settings: Settings) -> Path:
    return Path(settings.memory_dir) / "reminders.json"


def load(settings: Settings) -> list[dict]:
    try:
        found = json.loads(path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [r for r in found if isinstance(r, dict) and {"id", "at", "text"} <= r.keys()] if isinstance(found, list) else []


def save(settings: Settings, found: list[dict]) -> None:
    p = path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(sorted(found, key=lambda r: r["at"]), indent=2), encoding="utf-8")
    tmp.replace(p)


def parse_when(when: str) -> dt.datetime:
    """'2026-09-28 19:00' (local time) -> datetime."""
    text = re.sub(r"\s+", " ", str(when or "")).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError("Give the time as 'YYYY-MM-DD HH:MM' in the user's local time.")


def spoken_time(at: dt.datetime, now: dt.datetime) -> str:
    clock = at.strftime("%H:%M")
    if at.date() == now.date():
        return f"today at {clock}"
    if at.date() == now.date() + dt.timedelta(days=1):
        return f"tomorrow at {clock}"
    return f"{at.strftime('%A')} {at.day} {at.strftime('%B')} at {clock}"


def add(settings: Settings, when: str, text: str, repeat: str = "once", now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    at = parse_when(when)
    text = re.sub(r"\s+", " ", str(text or "")).strip()[:200]
    repeat = (repeat or "once").lower()
    if not text:
        raise ValueError("Say what the reminder is for.")
    if repeat not in REPEATS:
        raise ValueError(f"Repeat must be one of: {', '.join(REPEATS)}.")
    if at <= now and repeat == "once":
        raise ValueError(f"That time has already passed; it's now {now:%Y-%m-%d %H:%M}.")
    while at <= now:
        at = next_time(at, repeat)
    if at > now + dt.timedelta(days=366):
        raise ValueError("Reminders can be up to a year ahead.")
    found = load(settings)
    if len(found) >= MAX_REMINDERS:
        raise ValueError(f"There are already {MAX_REMINDERS} reminders; cancel some first.")
    found.append({"id": uuid.uuid4().hex[:8], "at": at.strftime("%Y-%m-%d %H:%M"), "text": text, "repeat": repeat})
    save(settings, found)
    how = {"once": "", "daily": ", and every day after", "weekdays": ", and every weekday after",
           "weekly": ", and every week after"}[repeat]
    return f"I'll remind them {spoken_time(at, now)}{how}: {text}."


def next_time(at: dt.datetime, repeat: str) -> dt.datetime:
    if repeat == "weekly":
        return at + dt.timedelta(days=7)
    at += dt.timedelta(days=1)
    while repeat == "weekdays" and at.weekday() >= 5:
        at += dt.timedelta(days=1)
    return at


def listing(settings: Settings, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    found = load(settings)
    if not found:
        return "No reminders are set."
    parts = []
    for r in found:
        extra = "" if r.get("repeat", "once") == "once" else f" (repeats {r['repeat']})"
        parts.append(f"{spoken_time(parse_when(r['at']), now)}: {r['text']}{extra}")
    return "Reminders: " + "; ".join(parts) + "."


def later_today(settings: Settings, now: dt.datetime | None = None) -> str:
    """'19:00 call Mum; 21:00 tablets', or '' when nothing else is due today."""
    now = now or dt.datetime.now()
    todays = [r for r in load(settings) if parse_when(r["at"]).date() == now.date()]
    return "; ".join(f"{r['at'][11:]} {r['text']}" for r in todays)


def cancel(settings: Settings, words: str) -> str:
    wanted = re.findall(r"\w+", str(words or "").lower())
    found = load(settings)
    gone = [r for r in found if wanted and all(w in r["text"].lower() for w in wanted)]
    if not gone:
        return "No reminder matches that. " + listing(settings)
    save(settings, [r for r in found if r not in gone])
    return "Cancelled: " + "; ".join(r["text"] for r in gone) + "."


def due(settings: Settings, now: dt.datetime | None = None) -> list[str]:
    """Take the reminders that are due, reschedule repeating ones, and return what to say."""
    now = now or dt.datetime.now()
    found, keep, say = load(settings), [], []
    for r in found:
        at = parse_when(r["at"])
        if at > now:
            keep.append(r)
            continue
        late = now - at > dt.timedelta(minutes=5)
        say.append(r["text"] + (f" (this was due {spoken_time(at, now)})" if late else ""))
        repeat = r.get("repeat", "once")
        if repeat != "once":
            while at <= now:
                at = next_time(at, repeat)
            keep.append({**r, "at": at.strftime("%Y-%m-%d %H:%M")})
    if say:
        save(settings, keep)
    return say


async def watch(settings: Settings, announce: Announce, someone_there: Callable[[], bool]) -> None:
    """Say reminders when they come due, holding them while no page is open."""
    while True:
        try:
            if someone_there():
                for text in await asyncio.to_thread(due, settings):
                    await announce(f"{settings.user_address.capitalize()}, a reminder: {text}.", "timer")
        except Exception as exc:  # a bad file must not stop the watcher
            print(f"[jarvis] Reminders: {exc!r}", flush=True)
        await asyncio.sleep(CHECK_SECONDS)


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "set_reminder",
            "description": "Remind the user at a clock time, e.g. 'remind me at 7 pm to call Mum', 'tomorrow at 9 "
                           "about the dentist', 'every weekday at 8 to take my tablets'. It is said aloud with a "
                           "chime and survives restarts. Work out the date and time from the local time in their "
                           "message. For 'in 10 minutes' use set_timer instead.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "when": {"type": "string", "description": "Local date and time, 'YYYY-MM-DD HH:MM'."},
                    "text": {"type": "string", "description": "What to remind them about, e.g. 'call Mum'."},
                    "repeat": {"type": "string", "enum": list(REPEATS), "description": "Default once."},
                },
                "required": ["when", "text"],
                "additionalProperties": False,
            },
        },
        {
            "name": "list_reminders",
            "description": "The reminders that are set, soonest first.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "cancel_reminder",
            "description": "Cancel reminders whose text contains these words.",
            "input_schema": {
                "type": "object",
                "properties": {"words": {"type": "string", "description": "Words from the reminder, e.g. 'dentist'."}},
                "required": ["words"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {t["name"] for t in tool_definitions()}


def run_tool(name: str, args: dict, settings: Settings) -> str:
    if name == "set_reminder":
        return add(settings, args["when"], args["text"], args.get("repeat") or "once")
    if name == "list_reminders":
        return listing(settings)
    return cancel(settings, args["words"])
