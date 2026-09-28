"""Shared bits for the writing studio: projects in writing.json, pieces as Markdown files, word counts, the pop-up.

Each project has a folder Writing/<project> in the memory folders; each chapter or piece is a Markdown file there,
kept in order in writing.json (with the project's characters, world notes and plot scenes). Daily word counts, the
streak, sprints and the blog planner are in writing-log.json.

The "writing-studio" pop-up (frontend/popup-writing.js) is stacked sections, each with an optional title:
  stats  {items: [{label, value}]}                   big numbers in a grid
  meters {rows: [{label, value, max, note?}]}        progress bars
  chart  {chart: {type, labels, values, unit}}       the usual bar or line chart
  table  {columns, rows}
  list   {items: [{label, note?, say?}]}             clicking an item with say sends it to Alfred
  fields {items: [{label, value}]}                   a character card's facts
  text   {text}                                      a paragraph or a song section
"""

import re
from datetime import date, timedelta
from pathlib import Path

import docs_tools
import homestore as hs
import memory
import screen
from config import Settings

KIND = "writing-studio"
screen.EXTRA_KINDS.add(KIND)

HOME = "Writing"
PROJECTS, LOG = "writing.json", "writing-log.json"
KINDS = ["novel", "short story", "blog", "song lyrics", "poems", "other"]
MAX_PROJECTS, MAX_PIECES, MAX_ENTRIES = 50, 300, 300
WORD = re.compile(r"\w+(?:['’-]\w+)*")


# ---- Stores -----------------------------------------------------------------------------------------

def load(settings: Settings) -> dict:
    data = hs.load(settings, PROJECTS, {})
    data.setdefault("projects", {})
    data.setdefault("current", "")
    return data


def save(settings: Settings, data: dict) -> None:
    hs.save(settings, PROJECTS, data)


def load_log(settings: Settings) -> dict:
    log = hs.load(settings, LOG, {})
    if not isinstance(log.get("days"), dict):
        log["days"] = {}
    if not isinstance(log.get("blog"), dict):
        log["blog"] = {}
    return log


def save_log(settings: Settings, log: dict) -> None:
    hs.save(settings, LOG, log)


def project_key(data: dict, name) -> str:
    """The project by name, else the one in use, else the only one."""
    projects = data["projects"]
    if not projects:
        raise ValueError("There are no writing projects yet. Start one first, e.g. 'start a novel called Ashes'.")
    if hs.clean(name):
        key = hs.find(projects, name)
        if key is None:
            raise ValueError(f"I haven't got a writing project called {hs.clean(name)}. "
                             f"The projects are: {', '.join(projects)}.")
        return key
    if data.get("current") in projects:
        return data["current"]
    if len(projects) == 1:
        return next(iter(projects))
    raise ValueError(f"Which project? {', '.join(projects)}.")


def project(data: dict, name) -> tuple[str, dict]:
    key = project_key(data, name)
    p = data["projects"][key]
    for field, empty in (("pieces", []), ("characters", {}), ("world", {}), ("scenes", [])):
        if not isinstance(p.get(field), type(empty)):
            p[field] = empty
    return key, p


# ---- Folders and pieces ----------------------------------------------------------------------------

def folder(settings: Settings, name: str) -> Path:
    try:
        memory.folder(settings, HOME)
    except ValueError:
        memory.create_folder(settings, "", HOME)
    return memory.folder(settings, f"{HOME}/{memory.safe_name(name, 'project name')}", create=True)


def piece_index(p: dict, name) -> int:
    pieces = p["pieces"]
    text = hs.need(name, "chapter or piece")
    if text.isdigit() and 1 <= int(text) <= len(pieces):
        return int(text) - 1
    key = hs.find([x["title"] for x in pieces], text)
    if key is None:
        raise ValueError(f"There's no chapter or piece called {text}.")
    return next(i for i, x in enumerate(pieces) if x["title"] == key)


def piece_path(settings: Settings, key: str, piece: dict) -> Path:
    return folder(settings, key) / piece["file"]


def read_piece(settings: Settings, key: str, piece: dict) -> str:
    path = piece_path(settings, key, piece)
    return docs_tools.read(path) if path.is_file() else ""


def body(text: str) -> str:
    """A piece's words without its title line."""
    return re.sub(r"\A\s*#\s[^\n]*\n?", "", text).strip("\n")


def words(text: str) -> int:
    return len(WORD.findall(re.sub(r"(?m)^(#{1,6}\s|Structure:).*$", "", text)))


def piece_words(settings: Settings, key: str, piece: dict) -> int:
    return words(body(read_piece(settings, key, piece)))


def project_words(settings: Settings, key: str, p: dict) -> int:
    return sum(piece_words(settings, key, x) for x in p["pieces"])


def all_words(settings: Settings, data: dict | None = None) -> int:
    data = data or load(settings)
    return sum(project_words(settings, k, project(data, k)[1]) for k in list(data["projects"]))


def new_piece(settings: Settings, key: str, p: dict, title: str, text: str = "", position=None) -> dict:
    if len(p["pieces"]) >= MAX_PIECES:
        raise ValueError("That project has as many pieces as I can keep; remove one first.")
    title = hs.need(title, "title")
    if any(x["title"].lower() == title.lower() for x in p["pieces"]):
        raise ValueError(f"{key} already has a piece called {title}.")
    path = memory.unique_path(folder(settings, key) / f"{memory.safe_name(title, 'title')}.md")
    text = str(text or "").strip()
    docs_tools.write(path, f"# {title}\n\n{text}".rstrip() + "\n")
    piece = {"title": title, "file": path.name}
    at = len(p["pieces"]) if position in (None, "") else min(max(int(position) - 1, 0), len(p["pieces"]))
    p["pieces"].insert(at, piece)
    return piece


# ---- Dates and streak ----------------------------------------------------------------------------

def deadline(value) -> str:
    return hs.parse_day(value).isoformat() if hs.clean(value) else ""


def days_left(when: str, today: date) -> int | None:
    try:
        return (date.fromisoformat(when) - today).days
    except (TypeError, ValueError):
        return None


def due_words(when: str, today: date) -> str:
    n = days_left(when, today)
    if n is None:
        return "no deadline"
    if n < 0:
        return f"{-n} day{'s' if n != -1 else ''} overdue"
    return "due today" if n == 0 else f"{n} day{'s' if n != 1 else ''} to go"


def day_words(log: dict, day: date) -> int:
    n = log["days"].get(day.isoformat(), 0)
    return int(n) if isinstance(n, (int, float)) else 0


def streak(log: dict, today: date) -> int:
    """Days in a row that met the daily goal (or had any words, with no goal), counting today once it's met."""
    goal = max(1, int(log.get("daily_goal") or 1))
    day = today if day_words(log, today) >= goal else today - timedelta(days=1)
    n = 0
    while day_words(log, day) >= goal and n < 3660:
        n += 1
        day -= timedelta(days=1)
    return n


# ---- Pop-ups -------------------------------------------------------------------------------------

def studio(title: str, card_id: str, sections: list[dict], buttons=None) -> dict:
    return screen.card(KIND, title, card_id, buttons=buttons, data={"sections": sections})


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40]


def s(n: int, word: str) -> str:
    return f"{n:,} {word}{'' if n == 1 else 's'}"
