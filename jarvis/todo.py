"""The to-do list: add jobs and tick them off by voice.

It is Markdown checkboxes ("- [ ] job"), so it works with Obsidian. The file is JARVIS_TASKS_FILE when that's set,
otherwise to-do.md in the Personal memory folder (fourth wolf part), where it also shows on the HUD.
"""

import re
from pathlib import Path

import memory
from config import Settings

MAX_OPEN = 200
BOX = re.compile(r"^(\s*[-*] \[)( |x|X)(\]\s*)(.*)$")


def path(settings: Settings) -> Path:
    if settings.tasks_file:
        return Path(settings.tasks_file).expanduser()
    return memory.folder(settings, 3) / "to-do.md"


def _lines(settings: Settings) -> list[str]:
    try:
        return path(settings).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _write(settings: Settings, lines: list[str]) -> None:
    p = path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def open_items(settings: Settings) -> list[str]:
    found = []
    for line in _lines(settings):
        m = BOX.match(line)
        if m and m.group(2) == " " and m.group(4).strip():
            found.append(m.group(4).strip())
    return found


def add(settings: Settings, jobs: list[str]) -> str:
    have = {j.lower() for j in open_items(settings)}
    lines, added = _lines(settings), []
    for job in jobs:
        job = re.sub(r"\s+", " ", str(job)).strip()[:120]
        if job and job.lower() not in have:
            lines.append(f"- [ ] {job}")
            have.add(job.lower())
            added.append(job)
    if len(have) > MAX_OPEN:
        raise ValueError("The to-do list is full; tick some jobs off first.")
    _write(settings, lines)
    return (f"Added {', '.join(added)}." if added else "Those are already on the list.") + f" {len(have)} open."


def done(settings: Settings, jobs: list[str]) -> str:
    words = [str(j).strip().lower() for j in jobs if str(j).strip()]
    lines, ticked = _lines(settings), []
    for i, line in enumerate(lines):
        m = BOX.match(line)
        if m and m.group(2) == " " and any(w in m.group(4).lower() for w in words):
            lines[i] = f"{m.group(1)}x{m.group(3)}{m.group(4)}"
            ticked.append(m.group(4).strip())
    if ticked:
        _write(settings, lines)
    left = len(open_items(settings))
    return (f"Ticked off {', '.join(ticked)}." if ticked else "None of those are on the list.") + f" {left} open."


def text(settings: Settings) -> str:
    found = open_items(settings)
    return f"{len(found)} open jobs:\n" + "\n".join(f"- {j}" for j in found) if found else "No open jobs."


def tool_definitions() -> list[dict]:
    return [{
        "name": "todo_list",
        "description": "The user's to-do list. action 'add' jobs, 'done' to tick jobs off (a word from the job is "
                       "enough), or 'read' the open ones.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["add", "done", "read"]},
                "jobs": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['call the bank']"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"todo_list"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = args.get("action")
    if action == "add":
        return add(settings, args.get("jobs") or [])
    if action == "done":
        return done(settings, args.get("jobs") or [])
    return text(settings)
