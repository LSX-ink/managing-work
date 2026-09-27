"""The shopping list: add and tick off items by voice.

It's a plain text file, list.md, in the Shopping memory folder (or wherever that folder was renamed to), one
item per line, so it also shows in the HUD's folder panel.
"""

import re
from pathlib import Path

import memory
from config import Settings

MAX_ITEMS = 200


def path(settings: Settings) -> Path:
    names = memory.names(settings)
    folder = next((n for n in names if n.lower() == "shopping"), names[4] if len(names) > 4 else "Shopping")
    return memory.root(settings) / folder / "list.md"


def items(settings: Settings) -> list[str]:
    try:
        lines = path(settings).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]


def _write(settings: Settings, found: list[str]) -> None:
    p = path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(f"- {i}\n" for i in found), encoding="utf-8")


def add(settings: Settings, new: list[str]) -> str:
    found = items(settings)
    have = {i.lower() for i in found}
    added = []
    for item in new:
        item = re.sub(r"\s+", " ", str(item)).strip()[:80]
        if item and item.lower() not in have:
            found.append(item)
            have.add(item.lower())
            added.append(item)
    if len(found) > MAX_ITEMS:
        raise ValueError("The shopping list is full; clear some items first.")
    _write(settings, found)
    return (f"Added {', '.join(added)}." if added else "Those are already on the list.") + f" {len(found)} items on the list."


def remove(settings: Settings, gone: list[str]) -> str:
    found = items(settings)
    words = [str(g).strip().lower() for g in gone if str(g).strip()]
    keep = [i for i in found if not any(w in i.lower() for w in words)]
    removed = [i for i in found if i not in keep]
    _write(settings, keep)
    return (f"Ticked off {', '.join(removed)}." if removed else "None of those were on the list.") + f" {len(keep)} left."


def clear(settings: Settings) -> str:
    _write(settings, [])
    return "The shopping list is empty."


def text(settings: Settings) -> str:
    found = items(settings)
    return "\n".join(f"• {i}" for i in found) if found else ""


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [
        {
            "name": "shopping_list",
            "description": "The user's shopping list. action 'add' or 'remove' (tick off) items, 'read' it, or "
                           "'clear' it.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["add", "remove", "read", "clear"]},
                    "items": {**listed, "description": "Items to add or remove, e.g. ['milk', 'eggs']."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"shopping_list"}


def run_tool(args: dict, settings: Settings) -> str:
    action = args.get("action")
    if action == "add":
        return add(settings, args.get("items") or [])
    if action == "remove":
        return remove(settings, args.get("items") or [])
    if action == "clear":
        return clear(settings)
    return text(settings) or "The shopping list is empty."
