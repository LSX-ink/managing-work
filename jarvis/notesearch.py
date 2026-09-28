"""Search every note in the memory folders: "what did I save about the boiler?"."""

import re

import memory
from config import Settings

MAX_HITS = 10
MAX_FILE_BYTES = 2 * 1024 * 1024


def search(settings: Settings, query: str) -> str:
    words = [w for w in re.findall(r"\w+", query.lower()) if len(w) > 1]
    if not words:
        raise ValueError("What should I look for?")
    base = memory.root(settings)
    memory.names(settings)
    hits = []
    for path in sorted(base.rglob("*")):
        if path.suffix.lower() not in memory.TEXT_TYPES or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            continue
        rel = path.relative_to(base)
        if any(part.startswith(".") for part in rel.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        haystack = f"{rel.as_posix()}\n{text}".lower()
        score = sum(haystack.count(w) for w in words)
        if score and all(w in haystack for w in words):
            first = min((i for i in (text.lower().find(w) for w in words) if i >= 0), default=0)
            snippet = re.sub(r"\s+", " ", text[max(0, first - 80): first + 220]).strip()
            hits.append((score, rel.as_posix(), snippet))
    if not hits:
        return f"Nothing in the memory folders mentions {query}."
    hits.sort(key=lambda h: -h[0])
    return f"{len(hits)} notes match, best first:\n" + "\n".join(f"- {rel}: …{snip}…" for _, rel, snip in hits[:MAX_HITS])


def tool_definitions() -> list[dict]:
    return [{
        "name": "search_memory",
        "description": "Search the text of every note in the user's memory folders (and folders inside them) for "
                       "words, when they ask what they saved about something and you don't know which folder.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A few key words."}},
            "required": ["query"],
            "additionalProperties": False,
        },
    }]


NAMES = {"search_memory"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    return search(settings, args.get("query") or "")
