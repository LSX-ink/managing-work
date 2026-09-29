"""Shared helpers for the study abilities: one small study.json in the memory folder.

It holds courses (with exam dates), topics with red/amber/green confidence, past papers, grade boundaries and
components, formulas and assignment deadlines. Study minutes are shared with the learning-and-goals study log.
"""

import json
import re
from datetime import date, timedelta

import growth_store as gs
import memory
from config import Settings

FILE = "study.json"
KEYS = {"courses": [], "topics": {}, "papers": [], "boundaries": {}, "components": {}, "formulas": {},
        "deadlines": [], "pomodoro": {}}
RAG = {"red": "Red, needs work", "amber": "Amber, getting there", "green": "Green, confident"}
RAG_LETTER = {"red": "R", "amber": "A", "green": "G", "": "-"}
RAG_ALIASES = {"r": "red", "red": "red", "weak": "red", "bad": "red", "amber": "amber", "a": "amber",
               "yellow": "amber", "orange": "amber", "ok": "amber", "okay": "amber", "so-so": "amber",
               "g": "green", "green": "green", "good": "green", "confident": "green", "strong": "green"}
REVIEW_DAYS = {"red": 1, "amber": 3, "green": 10}
clean, need, plural, number = gs.clean, gs.need, gs.plural, gs.number


def today() -> date:
    return date.today()


def load(settings: Settings) -> dict:
    try:
        data = json.loads((memory.root(settings) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data = data if isinstance(data, dict) else {}
    for key, default in KEYS.items():
        if not isinstance(data.get(key), type(default)):
            data[key] = type(default)()
    return data


def save(settings: Settings, data: dict) -> None:
    path = memory.root(settings) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def day(text, what: str = "date") -> date:
    try:
        return date.fromisoformat(str(text or "").strip()[:10])
    except ValueError:
        raise ValueError(f"I need the {what} as YYYY-MM-DD.") from None


def find_course(data: dict, name) -> dict | None:
    return gs.find(data["courses"], "name", name)


def course(data: dict, name) -> dict:
    """The saved course matching name, or ValueError listing what there is."""
    found = find_course(data, name) if clean(name) else (data["courses"][0] if len(data["courses"]) == 1 else None)
    if found is None:
        have = ", ".join(c["name"] for c in data["courses"]) or "none yet"
        raise ValueError(f"Which subject? Your courses: {have}.")
    return found


def ensure_course(data: dict, name) -> dict:
    """The saved course, or a new one when name isn't there yet (so notes never need a separate set-up step)."""
    if not clean(name):
        return course(data, name)
    found = find_course(data, name)
    if found is None:
        if len(data["courses"]) >= 30:
            raise ValueError("That's a lot of courses already.")
        found = {"name": need(name, "subject", 60)}
        data["courses"].append(found)
    return found


def confidence(text) -> str:
    key = RAG_ALIASES.get(clean(text, 20).lower())
    if not key:
        raise ValueError("Confidence is red, amber or green.")
    return key


def days_text(days: int) -> str:
    if days < 0:
        return f"{-days} days ago"
    return "today" if days == 0 else "tomorrow" if days == 1 else f"{days} days"


def named_list(value) -> list[str]:
    """A list of names from a list or a text separated by commas, semicolons or new lines."""
    if isinstance(value, str):
        value = re.split(r"[;\n,]", value)
    return [clean(v, 100) for v in (value or []) if clean(v, 100)]


def review_next(rag: str, on: date) -> str:
    return (on + timedelta(days=REVIEW_DAYS[rag])).isoformat()
