"""What Alfred knows about the user: lasting facts he is told ("remember I'm allergic to nuts").

They live in one plain text file, about-you.md in the memory folder, one fact per line, so the user can read or
edit it themselves. Every conversation starts with them in Alfred's instructions.
"""

import re
from pathlib import Path

from config import Settings

MAX_FACTS = 200
MAX_FACT_CHARS = 300


def path(settings: Settings) -> Path:
    return Path(settings.memory_dir) / "about-you.md"


def facts(settings: Settings) -> list[str]:
    try:
        lines = path(settings).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line[2:].strip() for line in lines if line.startswith("- ") and line[2:].strip()]


def _write(settings: Settings, found: list[str]) -> None:
    p = path(settings)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"- {f}\n" for f in found)
    p.write_text("# What Alfred knows about you\n\nOne fact per line. Edit or delete lines freely.\n\n" + body,
                 encoding="utf-8")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def remember(settings: Settings, fact: str) -> str:
    fact = _clean(fact)[:MAX_FACT_CHARS]
    if not fact:
        raise ValueError("There's nothing to remember.")
    found = facts(settings)
    if fact.lower() in (f.lower() for f in found):
        return "I already knew that."
    if len(found) >= MAX_FACTS:
        raise ValueError(f"I already hold {MAX_FACTS} facts; ask the user which ones to forget first.")
    found.append(fact)
    _write(settings, found)
    return "Remembered."


def forget(settings: Settings, words: str) -> str:
    """Forget every fact containing all of these words (any case)."""
    wanted = [w for w in re.findall(r"\w+", _clean(words).lower())]
    if not wanted:
        raise ValueError("Say what to forget.")
    found = facts(settings)
    gone = [f for f in found if all(w in f.lower() for w in wanted)]
    if not gone:
        return "I don't have anything like that remembered."
    _write(settings, [f for f in found if f not in gone])
    return "Forgotten: " + "; ".join(gone)


def prompt_section(settings: Settings) -> str:
    found = facts(settings)
    if not found:
        return ""
    lines = "\n".join(f"- {f}" for f in found)
    return ("\n\nWhat you know about them (they told you; use it naturally, don't recite it):\n" + lines)


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "remember_about_user",
            "description": "Keep a lasting fact about the user for every future conversation: preferences, people "
                           "in their life, birthdays, work, allergies, routines. Use it whenever they say "
                           "'remember that…', and also when they mention something clearly worth knowing next time. "
                           "One short fact per call, written in the third person, e.g. 'Allergic to nuts'.",
            "input_schema": {
                "type": "object",
                "properties": {"fact": {"type": "string", "description": "The fact, short, e.g. 'Sister Lebo's birthday is 3 May'."}},
                "required": ["fact"],
                "additionalProperties": False,
            },
        },
        {
            "name": "forget_about_user",
            "description": "Forget remembered facts about the user that contain these words, when they ask you to forget something.",
            "input_schema": {
                "type": "object",
                "properties": {"words": {"type": "string", "description": "Words from the fact, e.g. 'nuts'."}},
                "required": ["words"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {t["name"] for t in tool_definitions()}


def run_tool(name: str, args: dict, settings: Settings) -> str:
    if name == "remember_about_user":
        return remember(settings, args["fact"])
    return forget(settings, args["words"])
