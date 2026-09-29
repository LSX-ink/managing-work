"""Digital products part 2: actually making simple products as files in memory/digitalproducts/files.

Printables (planner, checklist, worksheet, habit tracker, budget sheet) come out as an HTML page ready to print to
PDF and, on request, a plain PDF made with docs_tools.to_pdf. An ebook skeleton, prompt pack and course outline are
Markdown, templates are CSV, and wallpapers and covers are PNG pictures. Nothing is uploaded or sold; check the
result yourself before you sell it.
"""

import calendar
import csv
import io
import random
from pathlib import Path

from PIL import Image, ImageDraw

import digitalproducts_store as store
import docs_tools
import homestore as hs
import screen
from config import Settings

ACTIONS = ["planner_make", "checklist_make", "worksheet_make", "habit_tracker_make", "budget_sheet_make",
           "ebook_skeleton", "csv_template", "prompt_pack", "course_outline", "wallpaper_make", "cover_make",
           "files_list", "file_show", "file_pdf", "file_remove"]
SOURCES = ".sources"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REFLECT = ["What is the goal, in one sentence?", "Why does it matter to me right now?",
           "What is one small step I can take today?", "What might get in the way, and what will I do about it?",
           "How will I know it worked?"]
BUDGET_ROWS = ["Rent or mortgage", "Bills", "Food and shopping", "Transport", "Savings", "Fun", "Other"]
CSV_KINDS = {
    "budget": ["Category", "Planned", "Actual", "Difference"],
    "content calendar": ["Date", "Platform", "Idea", "Status", "Link"],
    "inventory": ["Item", "Quantity", "Where kept", "Reorder at", "Notes"],
    "habit": ["Habit", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "invoice": ["Date", "Client", "Description", "Amount", "Paid"],
    "project": ["Task", "Owner", "Due", "Status", "Notes"],
    "reading list": ["Title", "Author", "Started", "Finished", "Rating", "Notes"],
}
PALETTES = {"mono": ((0, 0, 0), (70, 70, 70)), "sunset": ((255, 130, 90), (90, 40, 120)),
            "ocean": ((20, 120, 160), (10, 25, 70)), "forest": ((60, 130, 80), (10, 40, 30)),
            "lavender": ((190, 170, 235), (70, 60, 130)), "sand": ((235, 215, 175), (170, 130, 90))}
PROMPT_STARTS = ["Act as an experienced {topic} coach. Ask me 5 questions, then give me a plan for [my goal].",
                 "Explain {topic} to a complete beginner in under 150 words, with one everyday example.",
                 "Give me 10 ideas for [project] related to {topic}, and mark the 3 easiest to start.",
                 "Write a friendly checklist for [task] in {topic}, no more than 12 steps.",
                 "Look at my notes on {topic} below and list what is missing: [paste notes].",
                 "Turn this rough {topic} idea into a step-by-step weekly plan: [idea].",
                 "List 7 common {topic} mistakes and how to avoid each one.",
                 "Write 5 short, kind messages I could send about {topic} to [person].",
                 "Compare two ways of doing {topic}: [option A] and [option B]. Give pros, cons and a pick.",
                 "Quiz me on {topic} with 5 questions, one at a time, and mark my answers."]


def _title(args: dict, default: str) -> str:
    return hs.clean(args.get("title") or args.get("name"), 80) or default


def _emit(settings: Settings, args: dict, title: str, blocks: list, lead: str) -> screen.Shown:
    where = store.folder(settings, "files")
    path = store.unique(where, title, ".html")
    path.write_text(store.blocks_html(blocks, title), encoding="utf-8")
    md = store.blocks_md(blocks)
    source = store.folder(settings, f"files/{SOURCES}") / f"{path.stem}.md"
    source.write_text(md, encoding="utf-8")
    text = f"{lead} It is an HTML page ready to print to PDF."
    if args.get("pdf"):
        pdf = path.with_suffix(".pdf")
        pdf.write_bytes(docs_tools.to_pdf(md))
        text += f" A simple PDF, {pdf.name}, is saved beside it."
    _attach(settings, args, path.name)
    return store.shown_file(settings, path, text)


def _attach(settings: Settings, args: dict, filename: str) -> None:
    if not args.get("product"):
        return
    data = store.load(settings)
    row = store.product(data, args)
    if filename not in row["files"]:
        row["files"].append(filename)
        store.save(settings, data)


def _write(settings: Settings, args: dict, title: str, ext: str, text: str, lead: str) -> screen.Shown:
    path = store.unique(store.folder(settings, "files"), title, ext)
    path.write_text(text, encoding="utf-8", newline="")
    _attach(settings, args, path.name)
    return store.shown_file(settings, path, lead)


def _month(args: dict) -> tuple[int, int]:
    today = hs.today()
    year = int(hs.number(args.get("year") or today.year, "year", 2000, 2100))
    month = int(hs.number(args.get("month") or today.month, "month number", 1, 12))
    return year, month


# ---- Printables ------------------------------------------------------------------------------------

def planner_make(settings: Settings, args: dict) -> screen.Shown:
    style = hs.clean(args.get("style")).lower() or "weekly"
    if style not in ("weekly", "daily", "monthly"):
        raise ValueError("The planner can be weekly, daily or monthly.")
    title = _title(args, f"{style.title()} Planner")
    blocks = [("h1", title), ("p", "Week of: ______________" if style == "weekly" else "Date: ______________")]
    if style == "weekly":
        for d in DAYS:
            blocks += [("h2", d), ("check", ""), ("check", ""), ("lines", 1)]
        blocks += [("h2", "Notes"), ("lines", 4)]
    elif style == "daily":
        blocks += [("h2", "Top 3 priorities"), ("check", ""), ("check", ""), ("check", "")]
        blocks += [("table", ["Time", "Plan"], [[f"{h}:00", ""] for h in range(6, 22)]), ("h2", "Notes"), ("lines", 3)]
    else:
        year, month = _month(args)
        rows = [[str(d) if d else "" for d in wk] for wk in calendar.monthcalendar(year, month)]
        blocks += [("h2", f"{calendar.month_name[month]} {year}"), ("table", [d[:3] for d in DAYS], rows),
                   ("h2", "This month I want to"), ("check", ""), ("check", ""), ("check", ""), ("lines", 2)]
    return _emit(settings, args, title, blocks, f"Made a {style} planner.")


def checklist_make(settings: Settings, args: dict) -> screen.Shown:
    title = _title(args, "Checklist")
    items = store.text_list(args.get("items")) or [""] * 12
    blocks = [("h1", title)] + ([("p", hs.clean(args["intro"], 300))] if args.get("intro") else [])
    blocks += [("check", i) for i in items] + [("h2", "Notes"), ("lines", 3)]
    return _emit(settings, args, title, blocks, f"Made the checklist {title} with {len(items)} lines.")


def worksheet_make(settings: Settings, args: dict) -> screen.Shown:
    title = _title(args, "Worksheet")
    questions = store.text_list(args.get("items"), 30, 200) or REFLECT
    blocks = [("h1", title), ("p", hs.clean(args.get("intro"), 300) or "Name: ______________   Date: ____________")]
    for n, q in enumerate(questions, 1):
        blocks += [("h2", f"{n}. {q}"), ("lines", 3)]
    return _emit(settings, args, title, blocks, f"Made the worksheet {title} with {len(questions)} questions.")


def habit_tracker_make(settings: Settings, args: dict) -> screen.Shown:
    year, month = _month(args)
    habits = store.text_list(args.get("items"), 20, 40) or [""] * 6
    days = calendar.monthrange(year, month)[1]
    title = _title(args, f"Habit Tracker {calendar.month_name[month]} {year}")
    header = ["Habit"] + [str(d) for d in range(1, days + 1)]
    blocks = [("h1", title), ("p", "Colour in or tick a box each day you do the habit."),
              ("table", header, [[h] + [""] * days for h in habits])]
    return _emit(settings, args, title, blocks, f"Made a habit tracker for {calendar.month_name[month]}, "
                                                f"{len(habits)} habits.")


def budget_sheet_make(settings: Settings, args: dict) -> screen.Shown:
    title = _title(args, "Monthly Budget Sheet")
    cats = store.text_list(args.get("items"), 30, 40) or BUDGET_ROWS
    blocks = [("h1", title), ("p", "Month: ______________   Income: £__________"),
              ("table", ["Category", "Planned", "Actual", "Difference"], [[c, "", "", ""] for c in cats] + [["Total", "", "", ""]]),
              ("h2", "What went well and what to change"), ("lines", 3)]
    return _emit(settings, args, title, blocks, f"Made a printable budget sheet with {len(cats)} categories.")


# ---- Text and spreadsheet products -----------------------------------------------------------------

def ebook_skeleton(settings: Settings, args: dict) -> screen.Shown:
    title = _title(args, "My Ebook")
    chapters = store.text_list(args.get("items"), 30, 100)
    if not chapters:
        n = int(hs.number(args.get("count") or 8, "number of chapters", 3, 30))
        chapters = [f"Chapter idea {i}" for i in range(1, n + 1)]
    goal = int(hs.number(args.get("words") or 800, "words per chapter", 100, 5000))
    audience = hs.clean(args.get("audience"), 100) or "[who it is for]"
    lines = [f"# {title}", f"*By [your name]. For {audience}.*", "", "## Contents", ""]
    lines += [f"{n}. {c}" for n, c in enumerate(chapters, 1)] + ["", "## Introduction", "",
                                                                   "Who this is for, what they will be able to do by the end, and how to use the book.", ""]
    for n, c in enumerate(chapters, 1):
        lines += [f"## Chapter {n}: {c}", "", f"*Aim for about {goal} words.*", "", "**The big idea:** ...", "",
                  "**Why it matters:** ...", "", "**Step by step:**", "", "1. ...", "2. ...", "3. ...", "",
                  "**Try it:** one small exercise the reader can do now.", ""]
    lines += ["## Wrap-up", "", "The three things to remember and the next step.", "", "## About and licence", "",
              "About the author, how to contact you, and the licence line (see the licence helper).", ""]
    return _write(settings, args, title + " skeleton", ".md", "\n".join(lines),
                  f"Made an ebook skeleton with {len(chapters)} chapters, about {goal * len(chapters):,} words when "
                  "filled in. Write it in your own words.")


def csv_template(settings: Settings, args: dict) -> screen.Shown:
    kind = hs.clean(args.get("kind")).lower()
    cols = store.text_list(args.get("items"), 15, 40)
    if not cols:
        found = hs.find(CSV_KINDS, kind or "budget")
        if found is None:
            raise ValueError("Pick a kind: " + ", ".join(CSV_KINDS) + ", or give me the column names.")
        kind, cols = found, CSV_KINDS[found]
    title = _title(args, f"{kind or 'custom'} template")
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(cols)
    for _ in range(int(hs.number(args.get("rows") or 3, "example rows", 0, 50))):
        w.writerow([""] * len(cols))
    return _write(settings, args, title, ".csv", out.getvalue(),
                  f"Made a CSV template with {len(cols)} columns; it opens in Excel or Google Sheets.")


def prompt_pack(settings: Settings, args: dict) -> screen.Shown:
    topic = hs.need(args.get("topic"), "topic", 60)
    count = int(hs.number(args.get("count") or 10, "number of prompts", 1, 50))
    prompts = [PROMPT_STARTS[i % len(PROMPT_STARTS)].format(topic=topic) for i in range(count)]
    lines = [f"# {topic.title()} Prompt Pack", "", "Replace anything in [square brackets] with your own details.", ""]
    lines += [f"{n}. {p}" for n, p in enumerate(prompts, 1)]
    lines += ["", "*These are starting points: test each prompt yourself, and tidy the wording, before you sell them.*"]
    return _write(settings, args, f"{topic} prompt pack", ".md", "\n".join(lines) + "\n",
                  f"Made a pack of {count} starter prompts about {topic}. Test and reword them before selling.")


def course_outline(settings: Settings, args: dict) -> screen.Shown:
    title = _title(args, "My Course")
    lessons = store.text_list(args.get("items"), 20, 100)
    if not lessons:
        n = int(hs.number(args.get("count") or 5, "number of lessons", 2, 20))
        lessons = [f"Lesson topic {i}" for i in range(1, n + 1)]
    minutes = int(hs.number(args.get("minutes") or 15, "minutes per lesson", 3, 120))
    lines = [f"# {title}: course outline", "", f"For: {hs.clean(args.get('audience'), 100) or '[who it is for]'}",
             "", f"By the end they can: [one clear outcome]", f"Time: {len(lessons)} lessons, about "
             f"{len(lessons) * minutes} minutes in all.", ""]
    for n, t in enumerate(lessons, 1):
        lines += [f"## Lesson {n}: {t}", "", f"- Goal: what they can do after this {minutes}-minute lesson",
                  "- Key points: three at most", "- Exercise or worksheet", "- Recap in one sentence", ""]
    return _write(settings, args, title + " course outline", ".md", "\n".join(lines),
                  f"Made an outline of {len(lessons)} lessons, about {len(lessons) * minutes} minutes in all.")


# ---- Pictures --------------------------------------------------------------------------------------

def _palette(args: dict) -> tuple:
    name = hs.find(PALETTES, hs.clean(args.get("palette")).lower() or "mono")
    if name is None:
        raise ValueError("Palettes: " + ", ".join(PALETTES) + ".")
    return name, PALETTES[name]


def _gradient(size: tuple, colours: tuple, rng: random.Random, stars: bool) -> Image.Image:
    w, h = size
    mask = Image.linear_gradient("L").resize((w, h)).rotate(rng.choice([0, 90, 180, 270]), expand=True).resize((w, h))
    img = Image.composite(Image.new("RGB", size, colours[1]), Image.new("RGB", size, colours[0]), mask)
    d = ImageDraw.Draw(img)
    for _ in range(90 if stars else 6):
        x, y, r = rng.randrange(w), rng.randrange(h), rng.randrange(1, 4) if stars else rng.randrange(w // 8, w // 3)
        c = (255, 255, 255) if stars else tuple(min(255, v + 30) for v in colours[0])
        d.ellipse((x - r, y - r, x + r, y + r), fill=c if stars else None, outline=None if stars else c, width=3)
    return img


def wallpaper_make(settings: Settings, args: dict) -> screen.Shown:
    name, colours = _palette(args)
    count = int(hs.number(args.get("count") or 4, "number of wallpapers", 1, 8))
    size = (1920, 1080) if hs.clean(args.get("size")).lower() == "desktop" else (1170, 2532)
    pack = hs.clean(args.get("title") or args.get("name"), 60) or f"{name} wallpapers"
    where = store.folder(settings, f"files/{store.slug(pack)}")
    rng = random.Random(pack)
    for n in range(1, count + 1):
        _gradient(size, colours, rng, name == "mono").save(where / f"{store.slug(pack)}-{n}.png")
    _attach(settings, args, f"{store.slug(pack)}/ ({count} wallpapers)")
    first = where / f"{store.slug(pack)}-1.png"
    return screen.Shown(f"Made {count} {size[0]} by {size[1]} wallpapers in {name}, in the folder {store.slug(pack)}. "
                        "Only sell pictures you made or have the right to use.",
                        screen.file_card(settings, first, [{"label": "All my files", "say": "Show my digital product files."}]))


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and draw.textlength(trial, font=font) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line] if line else lines


def cover_make(settings: Settings, args: dict) -> screen.Shown:
    title = hs.need(args.get("title") or args.get("name"), "title", 80)
    name, colours = _palette(args)
    img = _gradient((1600, 2000), colours, random.Random(title), name == "mono")
    d = ImageDraw.Draw(img)
    y = 520
    for line in _wrap(d, title, docs_tools.font(120, True), 1300):
        d.text((150, y), line, font=docs_tools.font(120, True), fill="white")
        y += 150
    for line in _wrap(d, hs.clean(args.get("subtitle"), 120), docs_tools.font(52), 1300):
        d.text((150, y + 40), line, font=docs_tools.font(52), fill="white")
        y += 70
    path = store.unique(store.folder(settings, "files"), f"{title} cover", ".png")
    img.save(path)
    _attach(settings, args, path.name)
    return store.shown_file(settings, path, f"Made a simple cover picture for {title}. Swap it for a designed one when "
                                            "you can.")


# ---- Files -----------------------------------------------------------------------------------------

def _files(settings: Settings) -> list[Path]:
    base = store.folder(settings, "files")
    files = [p for p in base.rglob("*") if p.is_file() and SOURCES not in p.parts]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _find(settings: Settings, name) -> Path:
    want = hs.need(name, "file", 80).lower()
    files = _files(settings)
    for test in (lambda p: p.name.lower() == want, lambda p: p.stem.lower() == want, lambda p: want in p.name.lower()):
        found = [p for p in files if test(p)]
        if found:
            return found[0]
    raise ValueError(f"I can't find a product file called {name}. Ask me to show my files.")


def files_list(settings: Settings, args: dict) -> screen.Shown:
    files = _files(settings)
    items = [{"label": p.name, "say": f"Show the digital product file {p.name}."} for p in files[:60]]
    return screen.Shown(f"You have {len(files)} product files." if files else "No product files yet.",
                        screen.card("list", "Product files", "digitalproducts-files", items=items or [{"label": "None yet"}]))


def file_show(settings: Settings, args: dict) -> screen.Shown:
    path = _find(settings, args.get("name"))
    return store.shown_file(settings, path, f"Showing {path.name}.")


def file_pdf(settings: Settings, args: dict) -> screen.Shown:
    path = _find(settings, args.get("name"))
    source = path if path.suffix == ".md" else path.parent / SOURCES / f"{path.stem}.md"
    if not source.exists():
        raise ValueError("I can make a PDF from the pages and Markdown files I made, not from other files.")
    pdf = store.unique(path.parent, path.stem, ".pdf")
    pdf.write_bytes(docs_tools.to_pdf(source.read_text(encoding="utf-8")))
    return store.shown_file(settings, pdf, f"Made {pdf.name}. It is a plain-layout PDF; for the designed page, "
                                           "print the HTML from your browser and save as PDF.")


def file_remove(settings: Settings, args: dict) -> str:
    path = _find(settings, args.get("name"))
    if not args.get("confirmed"):
        return store.confirm_needed(f"the file {path.name}")
    path.unlink()
    return f"Deleted {path.name}."


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "digitalproducts_make",
        "description": "Make simple digital products as files (nothing is uploaded or sold). action: planner_make "
                      "(style weekly/daily/monthly, year, month) / checklist_make (items) / worksheet_make (items = "
                      "questions) / habit_tracker_make (items = habits, month) / budget_sheet_make (items) = "
                      "printable HTML ready to print to PDF, pdf true also saves a PDF; ebook_skeleton (title, items = "
                      "chapters or count, audience, words) / csv_template (kind budget, content calendar, inventory, "
                      "habit, invoice, project, reading list, or items = columns) / prompt_pack (topic, count) / "
                      "course_outline (title, items = lessons, minutes); wallpaper_make (palette mono, sunset, "
                      "ocean, forest, lavender, sand, count, size phone/desktop) / cover_make (title, subtitle, "
                      "palette); files_list / file_show (name) / file_pdf (name) / file_remove (name, confirmed "
                      "only after yes). Pass product to attach the file to a catalogue product.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "title": {"type": "string"},
                "name": {"type": "string"},
                "style": {"type": "string", "enum": ["weekly", "daily", "monthly"]},
                "items": {"type": "array", "items": {"type": "string"}},
                "intro": {"type": "string"},
                "topic": {"type": "string"},
                "kind": {"type": "string"},
                "audience": {"type": "string"},
                "subtitle": {"type": "string"},
                "palette": {"type": "string"},
                "size": {"type": "string", "enum": ["phone", "desktop"]},
                "count": {"type": "integer"},
                "rows": {"type": "integer"},
                "words": {"type": "integer"},
                "minutes": {"type": "integer"},
                "year": {"type": "integer"},
                "month": {"type": "integer"},
                "pdf": {"type": "boolean"},
                "product": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"digitalproducts_make"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"planner_make": planner_make, "checklist_make": checklist_make, "worksheet_make": worksheet_make,
             "habit_tracker_make": habit_tracker_make, "budget_sheet_make": budget_sheet_make,
             "ebook_skeleton": ebook_skeleton, "csv_template": csv_template, "prompt_pack": prompt_pack,
             "course_outline": course_outline, "wallpaper_make": wallpaper_make, "cover_make": cover_make,
             "files_list": files_list, "file_show": file_show, "file_pdf": file_pdf,
             "file_remove": file_remove}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
