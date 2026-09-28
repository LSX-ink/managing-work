"""Knowledge base: linked Markdown notes with [[wiki links]], #tags, daily notes, templates and book highlights.

Notes are plain .md files in Alfred's own Notes folder (daily notes in Notes/Daily, templates in Notes/Templates),
so they open in any editor. A note's title is its file name. An opened note pops up (kind "knowledge-note", drawn
by frontend/popup-knowledge.js) with its links clickable and the notes that link to it underneath.
Exploring (tags, graph, orphans, "what do I know") is in knowledge_explore.py; mind maps in knowledge_mindmap.py.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

import memory
import screen
from config import Settings

HOME = "Notes"
DAILY = "Daily"
TEMPLATES = "Templates"
MERGED = ".merged"
VIEWS = ".knowledge-views.json"
NOTE_KIND = "knowledge-note"
screen.EXTRA_KINDS.add(NOTE_KIND)
MAX_NOTES = 3000
MAX_NOTE_BYTES = 1_000_000
MAX_SHOWN = 100_000
SAID_CHARS = 2500
CONFIRM_OVER = 10
LINK = re.compile(r"\[\[([^\[\]|#\n]+)(#[^\[\]|\n]*)?(\|[^\[\]\n]*)?\]\]")
TAG = re.compile(r"(?<![\w#&/\[])#([A-Za-z][\w/-]{0,40})")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
TAG_LINE = re.compile(r"^#[A-Za-z][\w/-]*(\s+#[A-Za-z][\w/-]*)*$")
PLACEHOLDERS = {"-", "- [ ]", "1."}
BUILT_IN = {
    "meeting": "# {title}\n\nDate: {date}\nPeople: \n\n## Agenda\n\n- \n\n## Notes\n\n\n## Actions\n\n- [ ] \n\n#meeting\n",
    "book": "# {title}\n\nAuthor: \nStarted: {date}\n\n## Summary\n\n\n## Key ideas\n\n- \n\n## Highlights\n\n\n#book\n",
    "recipe": "# {title}\n\n## Ingredients\n\n- \n\n## Method\n\n1. \n\n## Ideas to try\n\n- \n\n#recipe\n",
    "person": "# {title}\n\nHow we met: \nBirthday: \n\n## Notes\n\n- \n\n## Things to remember\n\n- \n\n#person\n",
    "project": "# {title}\n\nStarted: {date}\nStatus: planning\n\n## Goal\n\n\n## Next steps\n\n- [ ] \n\n"
               "## Notes\n\n\n#project\n",
}


# ---- Files -------------------------------------------------------------------------------------

def home(settings: Settings, sub: str = "") -> Path:
    """Alfred's Notes folder (made the first time), or a folder inside it."""
    try:
        memory.folder(settings, HOME)
    except ValueError:
        memory.create_folder(settings, "", HOME)
    return memory.folder(settings, f"{HOME}/{sub}", create=True) if sub else memory.folder(settings, HOME)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write(path: Path, text: str) -> None:
    if len(text) > MAX_NOTE_BYTES:
        raise ValueError("That note is too long.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def links(text: str) -> list[str]:
    """[[Link]] targets in order, once each (any case)."""
    seen, out = set(), []
    for m in LINK.finditer(text):
        target = m.group(1).strip()
        if target and target.lower() not in seen:
            seen.add(target.lower())
            out.append(target)
    return out


def tags(text: str) -> list[str]:
    return sorted({t.lower().rstrip("/-") for t in TAG.findall(re.sub(r"`[^`]*`", "", text))})


def index(settings: Settings) -> dict[str, dict]:
    """Every note by lower-case title: title, path, text, links, tags, updated (datetime)."""
    base = home(settings)
    notes = {}
    files = [p for p in base.rglob("*.md") if p.is_file()
             and not any(q.startswith(".") for q in p.relative_to(base).parts)
             and p.relative_to(base).parts[0] != TEMPLATES and p.stat().st_size <= MAX_NOTE_BYTES]
    for path in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:MAX_NOTES]:
        if path.stem.lower() in notes:
            continue
        text = read(path)
        notes[path.stem.lower()] = {"title": path.stem, "path": path, "text": text, "links": links(text),
                                    "tags": tags(text), "updated": datetime.fromtimestamp(path.stat().st_mtime)}
    return notes


def find(notes: dict, title: str) -> dict:
    want = str(title or "").strip().strip("[]").strip().lower().removesuffix(".md")
    if not want:
        raise ValueError("Which note?")
    if want in notes:
        return notes[want]
    close = sorted((n for k, n in notes.items() if want in k), key=lambda n: len(n["title"]))
    if close:
        return close[0]
    raise ValueError(f"There's no note called {title}. I can create it if you like.")


def backlinks(notes: dict, note: dict) -> list[str]:
    key = note["title"].lower()
    return sorted((n["title"] for n in notes.values() if n is not note and key in {x.lower() for x in n["links"]}),
                  key=str.lower)


def body_of(note_text: str, title: str) -> str:
    """The note without its own '# Title' heading line."""
    lines = note_text.splitlines()
    if lines and lines[0].strip().lower() == f"# {title}".lower():
        lines = lines[1:]
    return "\n".join(lines).strip()


def insert_under(text: str, heading: str, addition: str) -> str:
    """addition at the end of the '## heading' section, or in a new section at the end.

    A section ends at the next heading of its level or higher, or at a line of only #tags."""
    lines = text.rstrip("\n").splitlines()
    start = next((i for i, line in enumerate(lines)
                  if (m := HEADING.match(line.strip())) and m.group(2).lower() == heading.lower()), None)
    if start is None:
        return "\n".join(lines) + f"\n\n## {heading}\n\n{addition}\n"
    level = len(HEADING.match(lines[start].strip()).group(1))
    end = next((i for i in range(start + 1, len(lines)) if TAG_LINE.match(lines[i].strip())
                or ((m := HEADING.match(lines[i].strip())) and len(m.group(1)) <= level)), len(lines))
    head, tail = lines[:end], lines[end:]
    while len(head) > start + 1 and (not head[-1].strip() or head[-1].strip() in PLACEHOLDERS):
        head.pop()
    while tail and not tail[0].strip():
        tail.pop(0)
    return "\n".join(head + ["", addition] + ([""] + tail if tail else [])) + "\n"


# ---- Views (for resurfacing old notes) ---------------------------------------------------------------

def views(settings: Settings) -> dict:
    try:
        data = json.loads((memory.root(settings) / VIEWS).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_views(settings: Settings, data: dict) -> None:
    (memory.root(settings) / VIEWS).write_text(json.dumps(data, indent=1), encoding="utf-8")


def mark_viewed(settings: Settings, title: str, today: date) -> None:
    data = views(settings)
    data[title.lower()] = today.isoformat()
    save_views(settings, data)


# ---- Pop-up --------------------------------------------------------------------------------------

def note_card(settings: Settings, note: dict, notes: dict) -> dict:
    path, title = note["path"], note["title"]
    return screen.card(
        NOTE_KIND, title, f"knowledge-note-{title.lower()}",
        data={"title": title, "text": note["text"][:MAX_SHOWN], "backlinks": backlinks(notes, note),
              "missing": [x for x in note["links"] if x.lower() not in notes], "tags": note["tags"]},
        buttons=[{"label": "Open on PC", "say": f"Open the file {path.name} from {path.parent.name} on my PC."},
                 {"label": "Note graph", "say": f"Show my note graph around {title}."}])


def show(settings: Settings, title: str, today: date, lead: str = "") -> screen.Shown:
    notes = index(settings)
    note = find(notes, title)
    mark_viewed(settings, note["title"], today)
    said = lead or f"Showing your note {note['title']}."
    text = body_of(note["text"], note["title"])
    return screen.Shown(f"{said} It says:\n{text[:SAID_CHARS]}" if text else said, note_card(settings, note, notes))


# ---- Actions -------------------------------------------------------------------------------------

def templates(settings: Settings) -> dict[str, Path]:
    """Template files by lower-case name, writing the built-in ones the first time."""
    folder = home(settings, TEMPLATES)
    for name, text in BUILT_IN.items():
        if not (folder / f"{name}.md").exists():
            write(folder / f"{name}.md", text)
    return {p.stem.lower(): p for p in sorted(folder.glob("*.md"))}


def template_text(settings: Settings, name: str, title: str, today: date) -> str:
    found = templates(settings)
    want = str(name).strip().lower().replace(" notes", "").replace(" note", "").replace(" idea", "")
    path = found.get(want) or next((p for k, p in found.items() if k in want or want in k), None)
    if not path:
        raise ValueError(f"There's no {name} template. The templates are: {', '.join(found)}.")
    return read(path).replace("{title}", title).replace("{date}", today.isoformat())


def new_note(settings: Settings, title: str, text: str, template: str, today: date) -> screen.Shown:
    title = memory.safe_name(title, "note title")
    if title.lower() in index(settings):
        raise ValueError(f"There's already a note called {title}. I can add to it instead.")
    text = str(text or "").strip()
    if template:
        body = template_text(settings, template, title, today) + (f"\n{text}\n" if text else "")
    else:
        body = (text if text.startswith("# ") else f"# {title}\n\n{text}").rstrip() + "\n"
    write(home(settings) / f"{title}.md", body)
    return show(settings, title, today, f"Made the note {title}.")


def add(settings: Settings, title: str, text: str, section: str, today: date) -> screen.Shown:
    text = str(text or "").strip()
    if not text:
        raise ValueError("What should I add?")
    notes = index(settings)
    try:
        note = find(notes, title)
    except ValueError:
        return new_note(settings, title, text, "", today)
    old = note["text"]
    write(note["path"], insert_under(old, section, text) if section else old.rstrip("\n") + f"\n\n{text}\n")
    return show(settings, note["title"], today, f"Added that to {note['title']}.")


def daily(settings: Settings, text: str, today: date) -> screen.Shown:
    folder = home(settings, DAILY)
    path = folder / f"{today.isoformat()}.md"
    if not path.exists():
        earlier = sorted(p.stem for p in folder.glob("*.md") if p.stem < today.isoformat())
        before = f"Previous: [[{earlier[-1]}]]\n\n" if earlier else ""
        write(path, f"# {today:%A} {today.day} {today:%B %Y}\n\n{before}## Plan\n\n- \n\n## Notes\n\n\n"
                    f"## Grateful for\n\n- \n\n## Done today\n\n- \n\n#daily\n")
    if str(text or "").strip():
        write(path, insert_under(read(path), "Notes", str(text).strip()))
        return show(settings, path.stem, today, "Added that to today's note.")
    return show(settings, path.stem, today, "Here's today's note.")


def highlight(settings: Settings, args: dict, today: date) -> screen.Shown:
    quote = re.sub(r"\s+", " ", str(args.get("text") or "")).strip().strip('"“”')
    source = memory.safe_name(args.get("source") or "", "book or source")
    if not quote:
        raise ValueError("What's the highlight?")
    author = str(args.get("author") or "").strip()[:80]
    page = str(args.get("page") or "").strip()[:20]
    note = index(settings).get(source.lower())
    if not note:
        write(home(settings) / f"{source}.md", template_text(settings, "book", source, today)
              .replace("Author: \n", f"Author: {author}\n" if author else "Author: \n"))
        note = find(index(settings), source)
    cite = ", ".join(x for x in (author, f"p. {page}" if page else "", today.isoformat()) if x)
    write(note["path"], insert_under(note["text"], "Highlights", f"> {quote}\n> — {cite}"))
    return show(settings, note["title"], today, f"Saved that highlight to {note['title']}.")


def relink(text: str, old: str, new: str) -> str:
    return LINK.sub(lambda m: f"[[{new}{m.group(2) or ''}{m.group(3) or ''}]]"
                    if m.group(1).strip().lower() == old.lower() else m.group(0), text)


def rename(settings: Settings, title: str, new_title: str, confirmed: bool, today: date) -> screen.Shown | str:
    notes = index(settings)
    note = find(notes, title)
    old, new = note["title"], memory.safe_name(new_title, "note title")
    if new.lower() in notes and new.lower() != old.lower():
        raise ValueError(f"There's already a note called {new}.")
    changes = {k: relink(n["text"], old, new) for k, n in notes.items()}
    changes = {k: t for k, t in changes.items() if t != notes[k]["text"]}
    if len(changes) > CONFIRM_OVER and not confirmed:
        return (f"Renaming {old} to {new} changes links in {len(changes)} notes. Ask the user, and if they agree "
                "call again with confirmed true.")
    for k, t in changes.items():
        write(notes[k]["path"], t)
    path = note["path"]
    text = read(path)
    if text.splitlines()[:1] == [f"# {old}"]:
        write(path, f"# {new}" + text[len(f"# {old}"):])
    path.rename(path.with_name(f"{new}.md"))
    seen = views(settings)
    if old.lower() in seen:
        seen[new.lower()] = seen.pop(old.lower())
        save_views(settings, seen)
    count = f" and updated links in {len(changes)} notes" if changes else ""
    return show(settings, new, today, f"Renamed {old} to {new}{count}.")


def merge(settings: Settings, title: str, into: str, confirmed: bool, today: date) -> screen.Shown | str:
    notes = index(settings)
    source, target = find(notes, title), find(notes, into)
    if source is target:
        raise ValueError("Those are the same note.")
    if not confirmed:
        return (f"Merging moves everything from {source['title']} into {target['title']} and removes "
                f"{source['title']} (a copy is kept in Notes/{MERGED}). Ask the user, and if they agree call again "
                "with confirmed true.")
    body = body_of(source["text"], source["title"])
    text = target["text"].rstrip("\n") + f"\n\n## From {source['title']}\n\n{body}\n"
    write(target["path"], relink(text, source["title"], target["title"]))
    for k, n in notes.items():
        if n is not source and n is not target and (t := relink(n["text"], source["title"], target["title"])) != n["text"]:
            write(n["path"], t)
    trash = home(settings) / MERGED
    trash.mkdir(exist_ok=True)
    source["path"].replace(memory.unique_path(trash / source["path"].name))
    return show(settings, target["title"], today, f"Merged {source['title']} into {target['title']}.")


def list_templates(settings: Settings) -> screen.Shown:
    names = list(templates(settings))
    items = [{"label": n.title(), "say": f"Make a new {n} note."} for n in names]
    return screen.Shown(f"Note templates: {', '.join(names)}.",
                        screen.card("list", "Note templates", "knowledge-templates", items=items))


# ---- Tool ----------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "knowledge_note",
        "description": "The user's personal knowledge base / wiki notes (Markdown in the Notes folder, linked with "
                       "[[Note title]] and tagged with #tags); each note pops up with clickable links and backlinks. "
                       "Actions: new (create a note page, optionally from a template: meeting, book, recipe, person, "
                       "project), open ('open my note X'), add (append text, optionally under a section heading), "
                       "daily (today's daily note; text adds to it), templates (list note templates), highlight "
                       "(save a reading highlight or quote with its book or source into that book's notes page), "
                       "rename (also updates every [[link]]; set confirmed true only after the user agrees when "
                       "asked), merge (title into another note 'into'; set confirmed only after the user agrees).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["new", "open", "add", "daily", "templates", "highlight",
                                                      "rename", "merge"]},
                "title": {"type": "string", "description": "The note's title."},
                "text": {"type": "string", "description": "Markdown to write or add; highlight: the quote."},
                "section": {"type": "string", "description": "add: heading to add under, e.g. 'Next steps'."},
                "template": {"type": "string", "enum": ["meeting", "book", "recipe", "person", "project"]},
                "new_title": {"type": "string", "description": "rename: the new title."},
                "into": {"type": "string", "description": "merge: the note that is kept."},
                "source": {"type": "string", "description": "highlight: the book or source title."},
                "author": {"type": "string"},
                "page": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"knowledge_note"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action, title = args.get("action"), args.get("title") or ""
    if action == "new":
        return new_note(settings, title, args.get("text") or "", args.get("template") or "", today)
    if action == "open":
        return show(settings, title, today)
    if action == "add":
        return add(settings, title, args.get("text") or "", args.get("section") or "", today)
    if action == "daily":
        return daily(settings, args.get("text") or "", today)
    if action == "templates":
        return list_templates(settings)
    if action == "highlight":
        return highlight(settings, args, today)
    if action == "rename":
        return rename(settings, title, args.get("new_title") or "", bool(args.get("confirmed")), today)
    if action == "merge":
        return merge(settings, title, args.get("into") or "", bool(args.get("confirmed")), today)
    raise ValueError("Pick an action: new, open, add, daily, templates, highlight, rename or merge.")
