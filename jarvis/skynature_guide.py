"""Nature guide for the UK: garden bird ID hints from a description, tree ID hints from leaf shape, facts on each,
a bird of the day, and what's in season to spot or forage this month (with a foraging safety note).

All from built-in tables (skynature_wild_data.py); nothing goes online. These are hints to point you in the right
direction, not a certain identification.
"""

import re
from datetime import date

import screen
from config import Settings
from skynature_wild_data import BIRDS, FORAGE, FORAGING_SAFETY, MONTHS, SPOT, TREES

ACTIONS = ["bird_id", "bird_facts", "tree_id", "tree_facts", "in_season", "forage_safety", "bird_of_the_day", "species_list"]
STOP = {"a", "an", "the", "and", "with", "on", "in", "its", "it", "has", "is", "of", "to", "at", "like", "very", "quite",
        "bit", "looks", "saw", "see", "seen", "small", "big", "bird", "tree", "leaf", "leaves", "about", "sort"}
SAME = {"gray": "grey", "redbreast": "red breast", "crest": "cap", "reddish": "red", "yellowish": "yellow",
        "brownish": "brown", "spiky": "spiny", "prickly": "spiny", "prickle": "spiny", "thorn": "thorny",
        "pointy": "pointed", "fingers": "palmate", "hand": "palmate", "needles": "needle", "conker": "conkers",
        "sizes": "size", "tiny": "tiny", "little": "tiny", "large": "large", "huge": "large", "chubby": "round"}


def words(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z]+", str(text).lower()):
        for w2 in SAME.get(w, w).split():
            w2 = w2[:-1] if len(w2) > 3 and w2.endswith("s") and not w2.endswith("ss") else w2
            if w2 not in STOP:
                out.add(w2)
    return out


def _pick(table: dict, describe, description: str, label: str) -> screen.Shown:
    query = words(description)
    if not query:
        raise ValueError(f"Describe the {label}: its colours, size or, for a tree, its leaves.")
    scored = sorted(((len(query & words(describe(name, row))), name) for name, row in table.items()), key=lambda x: (-x[0], x[1]))
    top = [(n, name) for n, name in scored if n][:3]
    if not top:
        said = f"I can't match that to a {label}. Tell me colours, size, markings or where you saw it."
        return screen.Shown(said, screen.card("text", f"{label.title()} ID", f"skynature-{label}-id", text=said))
    items = [{"label": f"{name}: {_summary(table[name])}", "say": f"Tell me about the {name}, the {label}."} for _, name in top]
    weak = " It's only a loose match, so tell me more." if top[0][0] == 1 else ""
    said = f"Best guess: {top[0][1]}." + (f" It could also be {' or '.join(n for _, n in top[1:])}." if len(top) > 1 else "") + weak
    return screen.Shown(said, screen.card("list", f"Which {label}?", f"skynature-{label}-id", items=items))


def _summary(row: tuple) -> str:
    """A short look: a bird's size and first markings, or a tree's leaf."""
    if len(row) == 4:
        return ", ".join([row[0], *row[1].split(", ")[:3]])
    return ", ".join(row[0].split(", ")[:3])


def bird_id(description: str) -> screen.Shown:
    return _pick(BIRDS, lambda n, r: f"{n} {r[0]} {r[1]} {r[2]}", description, "bird")


def tree_id(description: str) -> screen.Shown:
    return _pick(TREES, lambda n, r: f"{n} {r[0]} {r[1]}", description, "tree")


def _find(table: dict, name: str, label: str) -> str:
    name = " ".join(str(name or "").split()).lower()
    if not name:
        raise ValueError(f"Which {label}?")
    found = next((n for n in table if n.lower() == name), None) or next((n for n in table if name in n.lower()), None)
    if not found:
        raise ValueError(f"I don't have {name} in my {label} guide. Ask me to list them.")
    return found


def bird_facts(name: str) -> screen.Shown:
    bird = _find(BIRDS, name, "bird")
    size, look, where, fact = BIRDS[bird]
    said = f"The {bird} is a {size} bird: {look}. Look for it {where}. {fact}"
    return screen.Shown(said, screen.card("text", bird, "skynature-bird", text=said, buttons=[
        {"label": "Log a sighting", "say": f"Log a {bird} in my nature journal."}]))


def tree_facts(name: str) -> screen.Shown:
    tree = _find(TREES, name, "tree")
    leaf, clues, fact = TREES[tree]
    said = f"{tree}: leaves are {leaf}. Other clues: {clues}. {fact}"
    return screen.Shown(said, screen.card("text", tree, "skynature-tree", text=said, buttons=[
        {"label": "Log a sighting", "say": f"Log a {tree} tree in my nature journal."}]))


def bird_of_the_day(today: date) -> screen.Shown:
    names = sorted(BIRDS)
    return bird_facts(names[today.toordinal() % len(names)])


def species_list(kind: str) -> screen.Shown:
    trees = str(kind or "").lower().startswith("tree")
    table = TREES if trees else BIRDS
    items = [{"label": n, "say": f"Tell me about the {n}, the {'tree' if trees else 'bird'}."} for n in sorted(table)]
    return screen.Shown(f"I know {len(items)} common UK {'trees' if trees else 'garden birds'}. They are on screen.",
                        screen.card("list", "UK trees" if trees else "UK garden birds", "skynature-species", items=items))


def _month(args: dict, today: date) -> int:
    text = str(args.get("month") or "").strip().lower()
    if not text:
        return today.month
    if text.isdigit() and 1 <= int(text) <= 12:
        return int(text)
    found = next((i + 1 for i, m in enumerate(MONTHS) if m.lower().startswith(text[:3])), None)
    if not found:
        raise ValueError("Which month, 1 to 12?")
    return found


def in_season(args: dict, today: date) -> screen.Shown:
    month = _month(args, today)
    name = MONTHS[month - 1]
    if str(args.get("focus") or "spot") == "forage":
        found = [(n, row) for n, row in FORAGE.items() if month in row[0]]
        rows = [[n, row[1], row[2]] for n, row in found]
        rows.append(["Safety", "Never eat anything you can't identify 100 percent", "Use a field guide and an expert"])
        names = ", ".join(n for n, _ in found) if found else "nothing much"
        said = (f"In {name} you could forage: {names}. Only pick what you're completely sure of, and never eat "
                "wild mushrooms without an expert.")
        return screen.Shown(said, screen.card("table", f"Foraging in {name}", "skynature-forage", columns=["What", "Look for", "Take care"],
                                              rows=rows, buttons=[{"label": "Foraging safety", "say": "Give me the foraging safety rules."}]))
    said = f"In {name}, look out for: " + "; ".join(SPOT[month][:4]) + "."
    return screen.Shown(said, screen.card("list", f"Nature in {name}", "skynature-season", items=[{"label": t} for t in SPOT[month]],
                                          buttons=[{"label": "What can I forage?", "say": f"What can I forage in {name}?"}]))


def forage_safety() -> screen.Shown:
    said = "The golden rule of foraging: never eat anything unless you are 100 percent sure what it is. " \
           "The other rules are on screen."
    return screen.Shown(said, screen.card("list", "Foraging safety", "skynature-safety",
                                          items=[{"label": r} for r in FORAGING_SAFETY]))


def tool_definitions() -> list[dict]:
    return [{
        "name": "nature_guide",
        "description": "UK nature identification and seasons, from built-in tables. action: bird_id = garden bird ID "
                       "hints from a description (colours, size, markings, behaviour); bird_facts = facts and "
                       "feeding tips for one of about 30 common birds; tree_id = tree ID hints from the leaf shape "
                       "or bark description; tree_facts = facts on one of about 20 UK trees; in_season = what to spot "
                       "this month (focus 'forage' for wild food, with a safety note); forage_safety = the foraging "
                       "safety rules; bird_of_the_day = a bird to learn about; species_list = list the birds or trees "
                       "I know (kind 'bird' or 'tree').",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "description": {"type": "string", "description": "bird_id or tree_id: what the user saw, in their words."},
                "name": {"type": "string", "description": "bird_facts or tree_facts: the bird or tree."},
                "month": {"type": "string", "description": "in_season: 1 to 12 or a month name; default this month."},
                "focus": {"type": "string", "enum": ["spot", "forage"]},
                "kind": {"type": "string", "enum": ["bird", "tree"], "description": "species_list."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"nature_guide"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action = args.get("action")
    if action == "bird_id":
        return bird_id(args.get("description"))
    if action == "bird_facts":
        return bird_facts(args.get("name"))
    if action == "tree_id":
        return tree_id(args.get("description"))
    if action == "tree_facts":
        return tree_facts(args.get("name"))
    if action == "in_season":
        return in_season(args, today)
    if action == "forage_safety":
        return forage_safety()
    if action == "bird_of_the_day":
        return bird_of_the_day(today)
    if action == "species_list":
        return species_list(args.get("kind"))
    raise ValueError(f"Unknown nature action: {action}")
