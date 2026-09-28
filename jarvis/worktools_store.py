"""Shared bits for the work abilities: worktools-*.json files in the memory folder, projects, weeks and hours.

Files: worktools-projects.json (projects, their ideas), worktools-boards.json (kanban boards),
worktools-time.json (time, focus, working hours) and worktools-meetings.json (meetings, stand-ups).
"""

import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import memory
from config import Settings

PROJECTS = "worktools-projects.json"
BOARDS = "worktools-boards.json"
TIME = "worktools-time.json"
MEETINGS = "worktools-meetings.json"
DEFAULT_COLUMNS = ["To do", "Doing", "Done"]
MAX_ROWS = 500
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def now() -> datetime:
    return datetime.now()


def today() -> date:
    return now().date()


def load(settings: Settings, name: str, default):
    try:
        found = json.loads((memory.root(settings) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return found if isinstance(found, type(default)) else default


def save(settings: Settings, name: str, data) -> None:
    path = memory.root(settings) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clean(value, limit: int = 80) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def need(value, what: str, limit: int = 80) -> str:
    text = clean(value, limit)
    if not text:
        raise ValueError(f"Which {what}?")
    return text


def words(items, limit: int = 30, size: int = 120) -> list[str]:
    out = {}
    for item in items or []:
        text = clean(item, size)
        if text:
            out.setdefault(text.lower(), text)
    return list(out.values())[:limit]


def find(keys, name: str) -> str | None:
    """The key matching name exactly (ignoring case), else the only one containing it."""
    name = clean(name).lower()
    keys = list(keys)
    exact = next((k for k in keys if k.lower() == name), None)
    if exact is not None or not name:
        return exact
    part = [k for k in keys if name in k.lower()]
    return part[0] if len(part) == 1 else None


def parse_date(value, what: str = "date") -> date | None:
    text = clean(value).lower()
    if not text:
        return None
    if text == "today":
        return today()
    if text == "tomorrow":
        return today() + timedelta(days=1)
    if text == "yesterday":
        return today() - timedelta(days=1)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError(f"Give the {what} as YYYY-MM-DD.") from None


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_of(value) -> date:
    """Monday of 'this' or 'last' week, or of the week holding a YYYY-MM-DD date."""
    text = clean(value).lower()
    if text in ("", "this", "this week"):
        return week_start(today())
    if text in ("last", "last week"):
        return week_start(today()) - timedelta(days=7)
    return week_start(parse_date(text, "week"))


def short(day: date) -> str:
    return f"{day.day} {day.strftime('%b')}"


def until(day: date, ref: date) -> str:
    n = (day - ref).days
    if n == 0:
        return "today"
    if n == 1:
        return "tomorrow"
    if n == -1:
        return "1 day overdue"
    return f"in {n} days" if n > 0 else f"{-n} days overdue"


def hm(minutes: float) -> str:
    minutes = int(round(minutes))
    h, m = divmod(abs(minutes), 60)
    sign = "-" if minutes < 0 else ""
    if not h:
        return f"{sign}{m}m"
    return f"{sign}{h}h {m}m" if m else f"{sign}{h}h"


def work_folder(settings: Settings, sub: str = "") -> Path:
    """The Work memory folder (second brain part, whatever it's called now), or a folder inside it."""
    path = memory.folder(settings, 1)
    if sub:
        path = path / sub
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---- projects ---------------------------------------------------------------------------------

def projects(settings: Settings) -> dict:
    return {k: v for k, v in load(settings, PROJECTS, {}).items() if isinstance(v, dict)}


def project(settings: Settings, name, archived: bool = False) -> str:
    """A project's saved name from a spoken one; with no name and one live project, that one."""
    found = projects(settings)
    live = [k for k, v in found.items() if archived or not v.get("archived")]
    if not clean(name):
        if len(live) == 1:
            return live[0]
        raise ValueError("Which project?" if live else "There are no work projects yet; add one first.")
    k = find(live, name)
    if k is None:
        listed = ", ".join(live) or "none yet"
        raise ValueError(f"I haven't got a work project called {clean(name)}. Projects: {listed}.")
    return k


# ---- boards and time ----------------------------------------------------------------------------

def boards(settings: Settings) -> dict:
    return {k: v for k, v in load(settings, BOARDS, {}).items() if isinstance(v, dict)}


def board(found: dict, name: str) -> dict:
    b = found.setdefault(name, {})
    b.setdefault("columns", list(DEFAULT_COLUMNS))
    b.setdefault("cards", [])
    return b


def time_data(settings: Settings) -> dict:
    data = load(settings, TIME, {})
    data.setdefault("entries", [])
    data.setdefault("focus", [])
    return data


def minutes_by_project(entries: list, start: date, end: date) -> dict:
    """Minutes per project for entries dated start..end inclusive."""
    out: dict[str, float] = {}
    for e in entries:
        try:
            day = date.fromisoformat(e["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if start <= day <= end:
            out[e.get("project", "?")] = out.get(e.get("project", "?"), 0) + float(e.get("minutes") or 0)
    return out


def running_minutes(data: dict) -> tuple[str, float] | None:
    run = data.get("running")
    if not isinstance(run, dict):
        return None
    started = datetime.fromisoformat(run["started"])
    return run["project"], max(0.0, (now() - started).total_seconds() / 60)


def meetings(settings: Settings) -> dict:
    data = load(settings, MEETINGS, {})
    data.setdefault("meetings", [])
    data.setdefault("standups", {})
    return data
