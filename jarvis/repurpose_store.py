"""Shared bits for the repurpose abilities: one JSON file (repurpose.json) plus subtitle files in the memory folder.

Versions of each video made on each platform, checklists, atom plans, evergreen reminders and saved series live in the
JSON file. It is planning, writing and tracking only: nothing is posted anywhere and nothing leaves the PC.
"""

import re
from datetime import date
from pathlib import Path

import homestore as hs
import memory
from config import Settings

FILE = "repurpose.json"
FOLDER = "repurpose"
MAX_ITEMS = 500
DEFAULT_WPM = 150
PLATFORMS = ["TikTok", "YouTube Shorts", "Instagram Reels", "Pinterest", "X", "Blog", "Newsletter", "Podcast"]
SECTIONS = {"versions": [], "next_id": 1, "platforms": [], "checklists": {}, "template": [], "atoms": {},
            "evergreen": {}, "series": {}}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    data = {k: found[k] if isinstance(found.get(k), type(v)) else type(v)() for k, v in SECTIONS.items()}
    data["next_id"] = data["next_id"] or 1
    return data


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, FILE, data)


def folder(settings: Settings, sub: str = "") -> Path:
    p = memory.root(settings) / FOLDER / sub if sub else memory.root(settings) / FOLDER
    p.mkdir(parents=True, exist_ok=True)
    return p


def put(rows: list, item, limit: int = MAX_ITEMS) -> None:
    if len(rows) >= limit:
        raise ValueError("That list is full; remove something first.")
    rows.append(item)


def words(text) -> int:
    return len(str(text or "").split())


def wpm(args: dict) -> float:
    return hs.number(args.get("wpm") or DEFAULT_WPM, "words per minute", 60, 300)


def script(args: dict, what: str = "script") -> str:
    text = str(args.get("text") or "").strip()
    if not text:
        raise ValueError(f"Give me the {what} text.")
    return text[:20000]


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def video(settings: Settings, args: dict, data: dict | None = None) -> str:
    """The video title exactly as saved when it matches one already known, else the cleaned name."""
    name = hs.need(args.get("video"), "video", 80)
    data = data or load(settings)
    known = {v["video"] for v in data["versions"]} | set(data["checklists"]) | set(data["evergreen"]) | set(data["atoms"])
    return hs.find(known, name) or name


def parse_date(value, today: date) -> str:
    return hs.parse_day(value, today).isoformat()


def confirm_needed(what: str) -> str:
    return f"Ask the user to confirm removing {what}. Only after a yes, call again with confirmed true."
