"""Mind maps: a central topic with branches and sub-branches, changed by voice and drawn as a radial tree.

Kept in knowledge-mindmaps.json in the memory folder: {"maps": [{"topic", "root": {"text", "children"}, "updated"}]}.
A map turns into a Markdown outline note in the Notes folder (knowledge.py), and an outline note turns into a map.
The pop-up is kind "knowledge-mindmap" (frontend/popup-knowledge.js).
"""

import json
import re
from datetime import date

import knowledge
import memory
import screen
from config import Settings

KIND = "knowledge-mindmap"
screen.EXTRA_KINDS.add(KIND)
FILE = "knowledge-mindmaps.json"
MAX_MAPS = 100
MAX_NODES = 200
MAX_DEPTH = 6
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d{1,4}[.)])\s+(?:\[[ xX]\]\s+)?(.*\S)\s*$")


# ---- Store ----------------------------------------------------------------------------------------

def load(settings: Settings) -> list[dict]:
    try:
        data = json.loads((memory.root(settings) / FILE).read_text(encoding="utf-8"))
        return [m for m in data.get("maps", []) if isinstance(m, dict) and m.get("root")]
    except (OSError, ValueError, AttributeError):
        return []


def save(settings: Settings, maps: list[dict]) -> None:
    memory.root(settings).mkdir(parents=True, exist_ok=True)
    (memory.root(settings) / FILE).write_text(json.dumps({"maps": maps}, indent=1), encoding="utf-8")


def pick(maps: list[dict], topic: str) -> dict:
    """A map by topic (any case, part of it is fine); no topic means the most recently changed one."""
    if not maps:
        raise ValueError("You haven't made any mind maps yet.")
    want = str(topic or "").strip().lower()
    if not want:
        return max(maps, key=lambda m: m.get("updated", ""))
    for match in (lambda m: m["topic"].lower() == want, lambda m: want in m["topic"].lower()):
        found = [m for m in maps if match(m)]
        if found:
            return found[0]
    raise ValueError(f"There's no mind map about {topic}. The maps are: {', '.join(m['topic'] for m in maps)}.")


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        raise ValueError("What should the branch be called?")
    return text[:80]


def count(node: dict) -> int:
    return 1 + sum(count(c) for c in node["children"])


def walk(node: dict, parent=None, depth=0):
    yield node, parent, depth
    for child in node["children"]:
        yield from walk(child, node, depth + 1)


def locate(root: dict, text: str) -> tuple[dict, dict | None, int]:
    want = str(text or "").strip().lower()
    nodes = list(walk(root))
    for match in (lambda n: n.lower() == want, lambda n: want and want in n.lower()):
        for found in nodes:
            if match(found[0]["text"]):
                return found
    raise ValueError(f"There's no branch called {text} in the {root['text']} mind map.")


# ---- Outlines --------------------------------------------------------------------------------------

def parse_outline(text: str) -> tuple[str, list[tuple[int, str]]]:
    """(topic from the first # heading or '', [(depth, text)]) from Markdown headings and indented lists."""
    topic, items, head = "", [], 0
    for line in str(text).replace("\t", "    ").splitlines():
        if m := knowledge.HEADING.match(line.strip()):
            level, words = len(m.group(1)), m.group(2).strip()
            if level == 1 and not topic and not items:
                topic = words
                continue
            head = max(1, level - 1)
            items.append((head, words))
        elif m := LIST_ITEM.match(line):
            items.append((head + 1 + len(m.group(1)) // 2, m.group(2)))
        elif line.strip():
            # A plain line with no dash still counts as a branch, nested by its indent.
            indent = len(line) - len(line.lstrip())
            items.append((head + 1 + indent // 2, line.strip()))
    return topic, items


def build(root: dict, items: list[tuple[int, str]]) -> dict:
    stack = [(0, root)]
    for depth, text in items:
        depth = min(depth, stack[-1][0] + 1, MAX_DEPTH)
        while stack[-1][0] >= depth:
            stack.pop()
        node = {"text": clean(text), "children": []}
        stack[-1][1]["children"].append(node)
        stack.append((depth, node))
    if count(root) > MAX_NODES:
        raise ValueError(f"That's too many branches; a mind map holds up to {MAX_NODES}.")
    return root


def outline(root: dict, title: str = "") -> str:
    lines = [f"# {title or root['text']}", ""]
    lines += [f"{'  ' * (depth - 1)}- {node['text']}" for node, _, depth in walk(root) if depth]
    return "\n".join(lines) + "\n"


# ---- Actions -------------------------------------------------------------------------------------

def shown(m: dict, said: str) -> screen.Shown:
    branches = ", ".join(c["text"] for c in m["root"]["children"]) or "no branches yet"
    return screen.Shown(f"{said} Branches: {branches}.", screen.card(
        KIND, f"Mind map: {m['topic']}", f"knowledge-mindmap-{m['topic'].lower()}",
        data={"topic": m["topic"], "root": m["root"]},
        buttons=[{"label": "To outline note", "say": f"Turn my mind map {m['topic']} into an outline note."},
                 {"label": "All mind maps", "say": "List my mind maps."}]))


def store(settings: Settings, maps: list[dict], m: dict, today: date) -> None:
    m["updated"] = today.isoformat()
    if m not in maps:
        maps.append(m)
    save(settings, maps)


def new(settings: Settings, topic: str, text: str, today: date, confirmed: bool = False) -> screen.Shown | str:
    topic = clean(topic)
    maps = load(settings)
    old = next((m for m in maps if m["topic"].lower() == topic.lower()), None)
    if old and not confirmed:
        return (f"There's already a mind map about {topic}. Ask the user whether to replace it, and if they agree "
                "call again with confirmed true.")
    if old:
        maps.remove(old)
    if len(maps) >= MAX_MAPS:
        raise ValueError(f"You have {MAX_MAPS} mind maps, the most I keep.")
    m = {"topic": topic, "root": build({"text": topic, "children": []}, parse_outline(text)[1])}
    store(settings, maps, m, today)
    return shown(m, f"Made a mind map about {topic}.")


def add(settings: Settings, args: dict, today: date) -> screen.Shown:
    maps = load(settings)
    m = pick(maps, args.get("topic"))
    parent = locate(m["root"], args["parent"])[0] if args.get("parent") else m["root"]
    if args.get("outline"):
        items = parse_outline(args["outline"])[1]
        tmp = build({"text": parent["text"], "children": []}, items)
        parent["children"] += tmp["children"]
    else:
        parent["children"].append({"text": clean(args.get("node")), "children": []})
    if count(m["root"]) > MAX_NODES:
        raise ValueError(f"A mind map holds up to {MAX_NODES} branches.")
    store(settings, maps, m, today)
    return shown(m, f"Added to {parent['text']}.")


def remove(settings: Settings, args: dict, today: date) -> screen.Shown | str:
    maps = load(settings)
    m = pick(maps, args.get("topic"))
    node, parent, _ = locate(m["root"], args.get("node"))
    if parent is None:
        raise ValueError("That's the centre of the map; it can't be removed.")
    if node["children"] and not args.get("confirmed"):
        return (f"{node['text']} has {count(node) - 1} branches under it. Ask the user, and if they agree call again "
                "with confirmed true.")
    parent["children"].remove(node)
    store(settings, maps, m, today)
    return shown(m, f"Removed {node['text']}.")


def rename(settings: Settings, args: dict, today: date) -> screen.Shown:
    maps = load(settings)
    m = pick(maps, args.get("topic"))
    node, parent, _ = locate(m["root"], args.get("node"))
    old, node["text"] = node["text"], clean(args.get("new_name"))
    if parent is None:
        m["topic"] = node["text"]
    store(settings, maps, m, today)
    return shown(m, f"Renamed {old} to {node['text']}.")


def listing(settings: Settings) -> screen.Shown:
    maps = sorted(load(settings), key=lambda m: m["topic"].lower())
    items = [{"label": f"{m['topic']} ({count(m['root']) - 1} branches)", "say": f"Show my mind map {m['topic']}."}
             for m in maps]
    said = f"{len(maps)} mind maps: {', '.join(m['topic'] for m in maps)}." if maps else "No mind maps yet."
    return screen.Shown(said, screen.card("list", "Mind maps", "knowledge-mindmaps", items=items))


def to_outline(settings: Settings, args: dict, today: date) -> screen.Shown | str:
    m = pick(load(settings), args.get("topic"))
    title = memory.safe_name(args.get("title") or f"{m['topic']} mind map", "note title")
    path = knowledge.home(settings) / f"{title}.md"
    existing = knowledge.index(settings).get(title.lower())
    if existing and not args.get("confirmed"):
        return (f"There's already a note called {title}. Ask the user whether to replace it, and if they agree call "
                "again with confirmed true.")
    knowledge.write(existing["path"] if existing else path, outline(m["root"], title))
    return knowledge.show(settings, title, today, f"Saved the {m['topic']} mind map as the outline note {title}.")


def from_outline(settings: Settings, args: dict, today: date) -> screen.Shown | str:
    note = knowledge.find(knowledge.index(settings), args.get("title") or "")
    topic, items = parse_outline(note["text"])
    if not items:
        raise ValueError(f"{note['title']} has no headings or list items to make branches from.")
    topic = re.sub(r"\s+mind map$", "", topic or note["title"], flags=re.I)
    return new(settings, topic, note["text"], today, bool(args.get("confirmed")))


def tool_definitions() -> list[dict]:
    return [{
        "name": "knowledge_mindmap",
        "description": "Mind maps: a central topic with branches and sub-branches, drawn as a radial tree pop-up. "
                       "Actions: new (topic, optional outline of branches), show, list, add (a node under parent, "
                       "or a whole outline), remove (a node; a node with sub-branches needs confirmed true, set only "
                       "after the user agrees), rename (node to new_name), to_outline (save the map as a Markdown "
                       "outline note), from_outline (make a map from a note's headings and bullet lists). With no "
                       "topic the most recently changed map is used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["new", "show", "list", "add", "remove", "rename", "to_outline",
                                                      "from_outline"]},
                "topic": {"type": "string", "description": "The map's central topic."},
                "outline": {"type": "string", "description": "Branches as a Markdown list; indent two spaces per "
                                                             "sub-branch level."},
                "node": {"type": "string", "description": "add, remove or rename: the branch's words."},
                "parent": {"type": "string", "description": "add: the branch to add under (default the centre)."},
                "new_name": {"type": "string"},
                "title": {"type": "string", "description": "to_outline: note title; from_outline: the note."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"knowledge_mindmap"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "new":
        return new(settings, args.get("topic") or "", args.get("outline") or "", today, bool(args.get("confirmed")))
    if action == "show":
        m = pick(load(settings), args.get("topic"))
        return shown(m, f"Here's the {m['topic']} mind map.")
    if action == "list":
        return listing(settings)
    if action in ("add", "remove", "rename", "to_outline", "from_outline"):
        return {"add": add, "remove": remove, "rename": rename, "to_outline": to_outline,
                "from_outline": from_outline}[action](settings, args, today)
    raise ValueError("Pick an action: new, show, list, add, remove, rename, to_outline or from_outline.")
