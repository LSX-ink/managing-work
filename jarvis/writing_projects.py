"""Writing projects: novels, short stories, blogs, song lyrics and poem collections, with their chapters or pieces.

Each piece is a Markdown file in Writing/<project>; Alfred writes the words and this keeps them in order, counts
them, compiles the manuscript (Markdown plus a PDF drawn by docs_tools) and shows the project dashboard.
"""

import re
from datetime import timedelta

import docs_tools
import homestore as hs
import screen
import writing_store as ws
from config import Settings

ACTIONS = ["create", "update", "list", "add_piece", "write_piece", "show_piece", "rename_piece", "move_piece",
           "delete_piece", "outline", "compile", "dashboard"]


def create(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    name = hs.need(args.get("project"), "project name", 60)
    if any(k.lower() == name.lower() for k in data["projects"]):
        raise ValueError(f"There's already a project called {name}.")
    if len(data["projects"]) >= ws.MAX_PROJECTS:
        raise ValueError("That's as many projects as I can keep.")
    ws.folder(settings, name)
    kind = args.get("kind") if args.get("kind") in ws.KINDS else "other"
    data["projects"][name] = {"kind": kind, "goal": int(hs.number(args.get("word_goal") or 0, "word goal", 0, 5_000_000)),
                              "deadline": ws.deadline(args.get("deadline")), "created": hs.today().isoformat(),
                              "pieces": [], "characters": {}, "world": {}, "scenes": []}
    data["current"] = name
    ws.save(settings, data)
    return dashboard(settings, {"project": name}, said=f"Started the {kind} {name}. Its folder is Writing/{name}.")


def update(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if args.get("word_goal") not in (None, ""):
        p["goal"] = int(hs.number(args["word_goal"], "word goal", 0, 5_000_000))
    if args.get("deadline") not in (None, ""):
        p["deadline"] = ws.deadline(args["deadline"])
    if args.get("kind") in ws.KINDS:
        p["kind"] = args["kind"]
    data["current"] = key
    ws.save(settings, data)
    return dashboard(settings, {"project": key}, said=f"Updated {key}.")


def list_projects(settings: Settings) -> screen.Shown | str:
    data = ws.load(settings)
    if not data["projects"]:
        return "There are no writing projects yet."
    today = hs.today()
    items = []
    for key in data["projects"]:
        _, p = ws.project(data, key)
        goal = f" of {p['goal']:,}" if p.get("goal") else ""
        items.append({"label": f"{key} ({p['kind']})", "say": f"Show my writing dashboard for {key}.",
                      "note": f"{ws.project_words(settings, key, p):,}{goal} words, {ws.due_words(p.get('deadline'), today)}"})
    said = f"{ws.s(len(items), 'writing project')}: {', '.join(data['projects'])}."
    return screen.Shown(said, ws.studio("Writing projects", "writing-projects", [{"type": "list", "items": items}],
                                        [{"label": "New project", "say": "Start a new writing project."}]))


def outline_card(settings: Settings, key: str, p: dict) -> dict:
    rows = [[str(i), x["title"], f"{ws.piece_words(settings, key, x):,}"] for i, x in enumerate(p["pieces"], 1)]
    total = ws.project_words(settings, key, p)
    items = [{"label": f"{i}. {x['title']}", "say": f"Show the piece {x['title']} from my project {key}."}
             for i, x in enumerate(p["pieces"], 1)]
    sections = [{"type": "table", "columns": ["#", "Chapter / piece", "Words"], "rows": rows + [["", "Total", f"{total:,}"]]},
                {"type": "list", "title": "Open one", "items": items}] if rows else [
        {"type": "text", "text": "No chapters or pieces yet."}]
    return ws.studio(f"{key}: outline", f"writing-outline-{ws.slug(key)}", sections,
                     [{"label": "Add a chapter", "say": f"Add a new chapter to my project {key}."},
                      {"label": "Compile", "say": f"Compile the manuscript of {key}."}])


def outline(settings: Settings, args: dict, said: str = "") -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    card = outline_card(settings, key, p)
    return screen.Shown(said or f"{key} has {ws.s(len(p['pieces']), 'piece')} and "
                                f"{ws.s(ws.project_words(settings, key, p), 'word')}.", card)


def add_piece(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = ws.new_piece(settings, key, p, args.get("title"), args.get("text") or "", args.get("position"))
    data["current"] = key
    ws.save(settings, data)
    return outline(settings, {"project": key}, f"Added {piece['title']} to {key} as number "
                                                f"{p['pieces'].index(piece) + 1}.")


def piece_card(settings: Settings, key: str, piece: dict) -> dict:
    title = piece["title"]
    return screen.file_card(settings, ws.piece_path(settings, key, piece), buttons=[
        {"label": "Readability", "say": f"Check the readability of {title} in my project {key}."},
        {"label": "Outline", "say": f"Show the outline of my project {key}."}])


def write_piece(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = p["pieces"][ws.piece_index(p, args.get("piece"))]
    text = str(args.get("text") or "").strip()
    if not text:
        raise ValueError("What should I write in it?")
    path = ws.piece_path(settings, key, piece)
    old = ws.read_piece(settings, key, piece) or f"# {piece['title']}\n"
    new = f"# {piece['title']}\n\n{text}\n" if args.get("mode") == "replace" else old.rstrip("\n") + f"\n\n{text}\n"
    docs_tools.write(path, new)
    data["current"] = key
    ws.save(settings, data)
    verb = "Rewrote" if args.get("mode") == "replace" else "Added to"
    return screen.Shown(f"{verb} {piece['title']}; it has {ws.s(ws.piece_words(settings, key, piece), 'word')} now.",
                        piece_card(settings, key, piece))


def show_piece(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = p["pieces"][ws.piece_index(p, args.get("piece"))]
    text = ws.body(ws.read_piece(settings, key, piece))
    return screen.Shown(f"{piece['title']} is on the screen. It says:\n{text[:docs_tools.SPOKEN_LIMIT]}",
                        piece_card(settings, key, piece))


def rename_piece(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = p["pieces"][ws.piece_index(p, args.get("piece"))]
    new = hs.need(args.get("new_title"), "new title")
    if any(x is not piece and x["title"].lower() == new.lower() for x in p["pieces"]):
        raise ValueError(f"{key} already has a piece called {new}.")
    old_path = ws.piece_path(settings, key, piece)
    text = ws.read_piece(settings, key, piece)
    target = old_path.with_name(f"{ws.memory.safe_name(new, 'title')}.md")
    if target.name.lower() != old_path.name.lower():
        target = ws.memory.unique_path(target)
    if old_path.is_file():
        old_path.rename(target)
    docs_tools.write(target, f"# {new}\n\n{ws.body(text)}".rstrip() + "\n")
    old, piece["title"], piece["file"] = piece["title"], new, target.name
    ws.save(settings, data)
    return outline(settings, {"project": key}, f"Renamed {old} to {new}.")


def move_piece(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = p["pieces"].pop(ws.piece_index(p, args.get("piece")))
    at = int(hs.number(args.get("position"), "position", 1, ws.MAX_PIECES)) - 1
    p["pieces"].insert(min(at, len(p["pieces"])), piece)
    ws.save(settings, data)
    return outline(settings, {"project": key}, f"Moved {piece['title']} to number {p['pieces'].index(piece) + 1}.")


def delete_piece(settings: Settings, args: dict) -> screen.Shown | str:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    i = ws.piece_index(p, args.get("piece"))
    piece = p["pieces"][i]
    if args.get("confirmed") is not True:
        return (f"{piece['title']} in {key} has {ws.s(ws.piece_words(settings, key, piece), 'word')}. "
                "Ask the user to confirm deleting it, then call again with confirmed true.")
    path = ws.piece_path(settings, key, piece)
    if path.is_file():
        docs_tools.snapshot(path)
        path.unlink()
    p["pieces"].pop(i)
    ws.save(settings, data)
    return outline(settings, {"project": key}, f"Deleted {piece['title']}. A copy is kept in the hidden .versions folder.")


def manuscript(settings: Settings, key: str, p: dict) -> str:
    parts = [f"# {key}"]
    for piece in p["pieces"]:
        text = re.sub(r"(?m)^(#{1,5})(\s)", r"#\1\2", ws.body(ws.read_piece(settings, key, piece)))
        parts.append(f"## {piece['title']}\n\n{text.strip()}".rstrip())
    return "\n\n".join(parts) + "\n"


def compile_project(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if not p["pieces"]:
        raise ValueError(f"{key} has no chapters or pieces to compile yet.")
    md = manuscript(settings, key, p)
    out = ws.folder(settings, key) / "Manuscript"
    out.mkdir(exist_ok=True)
    path = out / f"{ws.memory.safe_name(key, 'title')}.md"
    docs_tools.write(path, md)
    pdf = docs_tools.export_pdf(settings, path)
    said = (f"Compiled {ws.s(len(p['pieces']), 'piece')} of {key} ({ws.s(ws.words(md), 'word')}) into "
            f"Writing/{key}/Manuscript, as Markdown and PDF. The PDF is on the screen.")
    return screen.Shown(said, screen.file_card(settings, pdf, buttons=[
        {"label": "Show Markdown", "say": f"Show the document {path.stem} from Writing/{key}/Manuscript."}]))


def dashboard(settings: Settings, args: dict, said: str = "") -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    log = ws.load_log(settings)
    today = hs.today()
    total, goal = ws.project_words(settings, key, p), int(p.get("goal") or 0)
    daily = int(log.get("daily_goal") or 0)
    streak = ws.streak(log, today)
    stats = [{"label": "Words", "value": f"{total:,}"}, {"label": "Chapters / pieces", "value": str(len(p["pieces"]))},
             {"label": "Streak", "value": ws.s(streak, "day")},
             {"label": "Deadline", "value": ws.due_words(p.get("deadline"), today)}]
    meters = []
    if goal:
        meters.append({"label": f"{key} goal", "value": total, "max": goal, "note": f"{total:,} of {goal:,}"})
    if daily:
        meters.append({"label": "Today", "value": ws.day_words(log, today), "max": daily,
                       "note": f"{ws.day_words(log, today):,} of {daily:,}"})
    sections = [{"type": "stats", "items": stats}]
    if meters:
        sections.append({"type": "meters", "title": "Goals", "rows": meters})
    if p["pieces"]:
        sections.append({"type": "chart", "title": "Words per chapter", "chart": {
            "type": "bar", "labels": [x["title"][:30] for x in p["pieces"][:60]],
            "values": [ws.piece_words(settings, key, x) for x in p["pieces"][:60]], "unit": "words"}})
    days = [today - timedelta(days=n) for n in range(13, -1, -1)]
    if any(ws.day_words(log, d) for d in days):
        sections.append({"type": "chart", "title": "Words written, last 14 days", "chart": {
            "type": "bar", "labels": [d.strftime("%a %d") for d in days],
            "values": [ws.day_words(log, d) for d in days], "unit": "words"}})
    left = days_needed(total, goal, p.get("deadline"), today)
    if not said:
        said = f"{key}: {ws.s(total, 'word')}" + (f" of {goal:,}" if goal else "") + \
               f", {ws.s(len(p['pieces']), 'piece')}, {ws.due_words(p.get('deadline'), today)}." + left
    return screen.Shown(said, ws.studio(f"{key}: dashboard", f"writing-dash-{ws.slug(key)}", sections, [
        {"label": "Outline", "say": f"Show the outline of my project {key}."},
        {"label": "Compile", "say": f"Compile the manuscript of {key}."}]))


def days_needed(total: int, goal: int, deadline: str, today) -> str:
    n = ws.days_left(deadline, today)
    if not goal or n is None or n < 0 or total >= goal:
        return ""
    return f" That's about {-(-(goal - total) // max(n, 1)):,} words a day to finish on time."


def tool_definitions() -> list[dict]:
    return [{
        "name": "writing_project",
        "description": "Writing studio projects: a novel, short story, blog, song lyrics or poem collection, with "
                       "a word-count goal and deadline, and its chapters or pieces (Markdown files in Writing/"
                       "<project>). Actions: create; update (goal, deadline, kind); list projects; add_piece "
                       "(a chapter, poem, song or post, optionally with text you wrote); write_piece (add your "
                       "words to it, or replace them); show_piece; rename_piece; move_piece (reorder chapters); "
                       "delete_piece (set confirmed true only after the user says yes); outline (table of chapters "
                       "with word counts); compile the manuscript into one Markdown file and PDF; dashboard (words "
                       "vs goal, chapters, streak, next deadline). Project defaults to the one last used.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "project": {"type": "string"},
                "kind": {"type": "string", "enum": ws.KINDS},
                "word_goal": {"type": "integer"},
                "deadline": {"type": "string", "description": "YYYY-MM-DD."},
                "piece": {"type": "string", "description": "Chapter or piece title, or its number."},
                "title": {"type": "string", "description": "add_piece: its title."},
                "new_title": {"type": "string"},
                "text": {"type": "string", "description": "Markdown words for the piece."},
                "mode": {"type": "string", "enum": ["append", "replace"]},
                "position": {"type": "integer", "description": "1 = first."},
                "confirmed": {"type": "boolean", "description": "delete_piece: true only after the user said yes."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"writing_project"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "list":
        return list_projects(settings)
    if action == "compile":
        return compile_project(settings, args)
    handler = {"create": create, "update": update, "add_piece": add_piece, "write_piece": write_piece,
               "show_piece": show_piece, "rename_piece": rename_piece, "move_piece": move_piece,
               "delete_piece": delete_piece, "outline": outline, "dashboard": dashboard}.get(action)
    if not handler:
        raise ValueError(f"Unknown action {action}.")
    return handler(settings, args)
