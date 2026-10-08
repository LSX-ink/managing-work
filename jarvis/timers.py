"""Voice timers ("set a timer for 5 minutes") and break mode ("take a break" until called by name).

Both are for the whole Jarvis server, not one page: a timer rings on every open page, and a break silences
Alfred everywhere. server.py registers the announce function with set_announcer at startup.
"""

import asyncio
import re
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from config import Settings

Announce = Callable[[str, str], Awaitable[None]]
_announce: Announce | None = None
MAX_SECONDS = 24 * 3600


@dataclass
class Timer:
    label: str
    ends: float
    task: asyncio.Task | None = field(default=None, repr=False)


timers: dict[str, Timer] = {}
on_break = False
stopwatch: dict = {}  # {"start": monotonic seconds, "laps": [lap times]} while one is running


def set_announcer(announce: Announce) -> None:
    global _announce
    _announce = announce


def spoken(seconds: float) -> str:
    """90 -> '1 minute 30 seconds'."""
    seconds = max(0, round(seconds))
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    parts = [f"{n} {unit}{'' if n == 1 else 's'}" for n, unit in ((h, "hour"), (m, "minute"), (s, "second")) if n]
    return " ".join(parts) or "0 seconds"


async def _ring(settings: Settings, timer: Timer) -> None:
    await asyncio.sleep(max(0.0, timer.ends - time.monotonic()))
    timers.pop(timer.label.lower(), None)
    if _announce:
        name = "Your timer" if timer.label == "timer" else f"Your {timer.label} timer"
        await _announce(f"{settings.user_address.capitalize()}, {name[0].lower() + name[1:]} is done.", "timer")


def set_timer(settings: Settings, seconds: float, label: str = "") -> str:
    seconds = float(seconds)
    if not 0 < seconds <= MAX_SECONDS:
        raise ValueError("Timers can run from 1 second to 24 hours.")
    label = re.sub(r"\s+", " ", str(label or "")).strip()[:40] or "timer"
    old = timers.pop(label.lower(), None)
    if old and old.task:
        old.task.cancel()
    timer = Timer(label, time.monotonic() + seconds)
    timer.task = asyncio.get_running_loop().create_task(_ring(settings, timer))
    timers[label.lower()] = timer
    what = "Timer" if label == "timer" else f"The {label} timer"
    return f"{what} set for {spoken(seconds)}."


def list_timers() -> str:
    if not timers:
        return "No timers are running."
    now = time.monotonic()
    return "Running timers: " + "; ".join(f"{t.label}: {spoken(t.ends - now)} left" for t in timers.values()) + "."


def cancel_timer(label: str = "") -> str:
    if not timers:
        return "No timers are running."
    key = str(label or "").strip().lower()
    if not key:
        if len(timers) > 1:
            return "More than one timer is running; say which: " + ", ".join(t.label for t in timers.values()) + "."
        key = next(iter(timers))
    timer = timers.pop(key, None) or timers.pop(key.removesuffix(" timer"), None)
    if not timer:
        return f"There's no {label} timer. " + list_timers()
    if timer.task:
        timer.task.cancel()
    return f"Cancelled the {timer.label} timer." if timer.label != "timer" else "Cancelled the timer."


# ---- break mode --------------------------------------------------------------------

def take_break() -> str:
    global on_break
    on_break = True
    return "On a break: say nothing more now. You'll ignore everything, announcements included, until called by name."


def wakes_from_break(settings: Settings, text: str) -> bool:
    """While on a break, only a message that uses Alfred's (or Jarvis's) name ends it."""
    global on_break
    if not on_break:
        return True
    if re.search(rf"\b{re.escape(settings.persona)}\b", text, re.I):
        on_break = False
        return True
    return False


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "set_timer",
            "description": "Start a countdown timer that announces itself (with a chime) when it ends. Setting a "
                           "timer with the same label replaces it.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "Length in seconds, e.g. 90 for a minute and a half."},
                    "label": {"type": "string", "description": "Optional name, e.g. 'pasta'."},
                },
                "required": ["seconds"],
                "additionalProperties": False,
            },
        },
        {
            "name": "check_timers",
            "description": "How long is left on each running timer.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "cancel_timer",
            "description": "Stop a running timer.",
            "input_schema": {
                "type": "object",
                "properties": {"label": {"type": "string", "description": "Which timer; leave out if only one runs."}},
                "additionalProperties": False,
            },
        },
        {
            "name": "take_a_break",
            "description": "Go quiet when the user says 'take a break' (or similar): ignore everything, including "
                           "your own announcements, until they say your name. Reply with a very short goodbye.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


NAMES = {t["name"] for t in tool_definitions()}


def run_tool(name: str, args: dict, settings: Settings) -> str:
    if name == "set_timer":
        return set_timer(settings, args["seconds"], args.get("label") or "")
    if name == "check_timers":
        return list_timers()
    if name == "cancel_timer":
        return cancel_timer(args.get("label") or "")
    return take_break()


def start_stopwatch(now: float | None = None) -> str:
    restarted = bool(stopwatch)
    stopwatch.clear()
    stopwatch.update(start=time.monotonic() if now is None else now, laps=[])
    return "Stopwatch restarted." if restarted else "Stopwatch started."


def check_stopwatch(now: float | None = None) -> str:
    if not stopwatch:
        return "There's no stopwatch running."
    return f"{spoken((time.monotonic() if now is None else now) - stopwatch['start'])} on the stopwatch."


def lap_stopwatch(now: float | None = None) -> str:
    if not stopwatch:
        return "There's no stopwatch running."
    total = (time.monotonic() if now is None else now) - stopwatch["start"]
    lap = total - sum(stopwatch["laps"])
    stopwatch["laps"].append(lap)
    return f"Lap {len(stopwatch['laps'])}: {spoken(lap)}."


def stop_stopwatch(now: float | None = None) -> str:
    if not stopwatch:
        return "There's no stopwatch running."
    total = (time.monotonic() if now is None else now) - stopwatch["start"]
    laps = len(stopwatch["laps"])
    stopwatch.clear()
    return f"Stopped at {spoken(total)}{f' after {laps} lap' + ('s' if laps != 1 else '') if laps else ''}."
