"""Kanban boards for work projects: cards in To do / Doing / Done (or your own columns), by voice or by dragging.

The board pops up as a "work-kanban" window (frontend/popup-work.js). Dragging a card there sends a line such as
"Move card Logo to Doing on the Website board" back to Alfred, so this file stays the one true copy.
"""

import screen
import worktools_store as ws
from config import Settings

KIND = "work-kanban"
screen.EXTRA_KINDS.add(KIND)
MAX_CARDS = 200


def _card(b: dict, title, project: str) -> dict:
    titles = [c["title"] for c in b["cards"]]
    k = ws.find(titles, ws.need(title, "card"))
    if k is None:
        raise ValueError(f"There's no card called {ws.clean(title)} on the {project} board.")
    return next(c for c in b["cards"] if c["title"] == k)


def _column(b: dict, name) -> str:
    wanted = ws.clean(name) or b["columns"][0]
    k = ws.find(b["columns"], wanted)
    if k is None:
        raise ValueError(f"The columns are {', '.join(b['columns'])}.")
    return k


def board_card(project: str, b: dict) -> dict:
    cards = [{"title": c["title"], "column": c["column"], "notes": c.get("notes", ""), "due": c.get("due", "")}
             for c in b["cards"]]
    return screen.card(KIND, f"{project} board", f"work-board-{project}",
                       data={"project": project, "columns": b["columns"], "cards": cards},
                       buttons=[{"label": "Summary", "say": f"Show the {project} project summary."}])


def _saved(settings: Settings, found: dict, project: str, text: str) -> screen.Shown:
    ws.save(settings, ws.BOARDS, found)
    return screen.Shown(text, board_card(project, found[project]))


def show(settings: Settings, project) -> screen.Shown:
    name = ws.project(settings, project)
    b = ws.board(ws.boards(settings), name)
    counts = ", ".join(f"{sum(c['column'] == col for c in b['cards'])} in {col}" for col in b["columns"])
    return screen.Shown(f"The {name} board: {counts}.", board_card(name, b))


def add(settings: Settings, project, title, column, notes, due) -> screen.Shown:
    name = ws.project(settings, project)
    found = ws.boards(settings)
    b = ws.board(found, name)
    title = ws.need(title, "card", 80)
    if any(c["title"].lower() == title.lower() for c in b["cards"]):
        raise ValueError(f"There's already a card called {title} on the {name} board.")
    if len(b["cards"]) >= MAX_CARDS:
        raise ValueError("That board is full; remove some cards first.")
    col = _column(b, column)
    day = ws.parse_date(due, "due date")
    card = {"title": title, "column": col, "notes": ws.clean(notes, 1000), "due": day.isoformat() if day else "",
            "added": ws.today().isoformat()}
    if col == b["columns"][-1]:
        card["done_on"] = ws.today().isoformat()
    b["cards"].append(card)
    return _saved(settings, found, name, f"Added {title} to {col} on the {name} board.")


def move(settings: Settings, project, title, column) -> screen.Shown:
    name = ws.project(settings, project)
    found = ws.boards(settings)
    b = ws.board(found, name)
    card = _card(b, title, name)
    col = _column(b, ws.need(column, "column"))
    card["column"] = col
    if col == b["columns"][-1]:
        card["done_on"] = ws.today().isoformat()
    else:
        card.pop("done_on", None)
    return _saved(settings, found, name, f"Moved {card['title']} to {col}.")


def remove(settings: Settings, project, title, confirmed: bool):
    name = ws.project(settings, project)
    found = ws.boards(settings)
    b = ws.board(found, name)
    card = _card(b, title, name)
    if not confirmed:
        return f"Ask the user to confirm removing the card {card['title']} from the {name} board, then call again with confirmed true."
    b["cards"].remove(card)
    return _saved(settings, found, name, f"Removed {card['title']} from the {name} board.")


def note(settings: Settings, project, title, notes) -> screen.Shown:
    name = ws.project(settings, project)
    found = ws.boards(settings)
    card = _card(ws.board(found, name), title, name)
    text = ws.need(notes, "note", 1000)
    card["notes"] = f"{card['notes']}\n{text}".strip()[-2000:] if card.get("notes") else text
    return _saved(settings, found, name, f"Added a note to {card['title']}.")


def due(settings: Settings, project, title, when) -> screen.Shown:
    name = ws.project(settings, project)
    found = ws.boards(settings)
    card = _card(ws.board(found, name), title, name)
    day = ws.parse_date(when, "due date")
    card["due"] = day.isoformat() if day else ""
    said = f"{card['title']} is due {ws.short(day)} ({ws.until(day, ws.today())})." if day else \
        f"{card['title']} no longer has a due date."
    return _saved(settings, found, name, said)


def card_notes(settings: Settings, project, title) -> screen.Shown:
    name = ws.project(settings, project)
    card = _card(ws.board(ws.boards(settings), name), title, name)
    lines = [f"Column: {card['column']}"]
    if card.get("due"):
        lines.append(f"Due: {card['due']}")
    lines.append(card.get("notes") or "No notes yet.")
    said = f"{card['title']}: {card.get('notes') or 'no notes yet'}."
    return screen.Shown(said, screen.card("text", card["title"], f"work-card-{name}-{card['title']}",
                                          text="\n".join(lines)))


def columns(settings: Settings, project, names) -> screen.Shown:
    name = ws.project(settings, project)
    found = ws.boards(settings)
    b = ws.board(found, name)
    new = ws.words(names, 8, 30)
    if len(new) < 2:
        raise ValueError("A board needs at least two columns, e.g. To do, Doing, Done.")
    for c in b["cards"]:
        match = ws.find(new, c["column"])
        c["column"] = match or new[0]
    b["columns"] = new
    return _saved(settings, found, name, f"The {name} board's columns are now {', '.join(new)}.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "work_board",
        "description": "Kanban board for a work project (To do, Doing, Done cards). actions: show (pop up the "
                       "board; drag cards between columns there), add a card, move a card to a column, remove a "
                       "card, note (add notes to a card), due (set a card's due date), card (read a card's notes), "
                       "columns (set custom column names, last one counts as done). Set confirmed true only after "
                       "the user confirms a remove.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["show", "add", "move", "remove", "note", "due", "card", "columns"]},
                "project": {"type": "string", "description": "The project whose board it is."},
                "card": {"type": "string", "description": "Card title, e.g. 'Design logo'."},
                "column": {"type": "string", "description": "e.g. 'Doing'."},
                "notes": {"type": "string"},
                "due": {"type": "string", "description": "YYYY-MM-DD, 'today' or 'tomorrow'; empty clears it."},
                "columns": {"type": "array", "items": {"type": "string"}},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"work_board"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, project, title = args.get("action"), args.get("project"), args.get("card")
    if action == "add":
        return add(settings, project, title, args.get("column"), args.get("notes"), args.get("due"))
    if action == "move":
        return move(settings, project, title, args.get("column"))
    if action == "remove":
        return remove(settings, project, title, bool(args.get("confirmed")))
    if action == "note":
        return note(settings, project, title, args.get("notes"))
    if action == "due":
        return due(settings, project, title, args.get("due"))
    if action == "card":
        return card_notes(settings, project, title)
    if action == "columns":
        return columns(settings, project, args.get("columns"))
    return show(settings, project)
