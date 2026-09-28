"""Diary: one Markdown file per day (YYYY-MM-DD.md) in the Diary folder of the memory folder.

Adding to a day appends a timed entry, so nothing already written is ever overwritten.
"""

from pathlib import Path

import homestore as hs
import memory
from config import Settings

MAX_ENTRY = 4000


def folder(settings: Settings) -> Path:
    return memory.root(settings) / "Diary"


def add(settings: Settings, text, day=None) -> str:
    text = str(text or "").strip()[:MAX_ENTRY]
    if not text:
        raise ValueError("What should I write?")
    when = hs.parse_day(day)
    p = folder(settings) / f"{when.isoformat()}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    head = "" if p.exists() else f"# {hs.spoken(when)} {when.year}\n"
    stamp = hs.now().strftime("%H:%M") if when == hs.today() else "Added later"
    with p.open("a", encoding="utf-8") as f:
        f.write(f"{head}\n## {stamp}\n\n{text}\n")
    return f"Added to your diary for {hs.spoken(when)}."


def read(settings: Settings, day=None) -> str:
    when = hs.parse_day(day)
    p = folder(settings) / f"{when.isoformat()}.md"
    if not p.exists():
        return f"No diary entry for {hs.spoken(when)}."
    return p.read_text(encoding="utf-8")


def tool_definitions() -> list[dict]:
    return [{
        "name": "home_diary",
        "description": "The user's private diary. action 'add' appends text to a day's entry; 'read' reads a day's "
                       "entry. day is today (default), yesterday, a weekday this week or YYYY-MM-DD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "read"]},
                "text": {"type": "string", "description": "What to write, in the user's words."},
                "day": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"home_diary"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    if args.get("action") == "add":
        return add(settings, args.get("text"), args.get("day"))
    return read(settings, args.get("day"))
