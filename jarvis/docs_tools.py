"""Documents: Markdown documents in the memory folders, written by Alfred and shown in pop-ups.

New documents go in a Documents folder of Alfred's own unless another folder is named. Every change keeps the
previous copy in a hidden .versions folder beside the file, so any edit can be undone. Documents export to a
standalone HTML page or a PDF drawn with Pillow. Reusable templates live in Documents/Templates.
Letters, CVs and invoices are in docs_tools_forms.py; CSV spreadsheets in docs_tools_sheets.py.
"""

import difflib
import html
import io
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import memory
import screen
from config import Settings

HOME = "Documents"
TEMPLATES = "Templates"
MAX_TEXT = 200_000
MAX_VERSIONS = 20
MAX_REPLACE_UNCONFIRMED = 20
READ_WPM, SPEAK_WPM = 230, 130
SPOKEN_LIMIT = 6000
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d{1,4}[.)])\s")
PLACEHOLDER = re.compile(r"\{\{\s*([\w .-]+?)\s*\}\}")


# ---- Folders and files -------------------------------------------------------------------------

def home(settings: Settings, sub: str = "") -> Path:
    """Alfred's Documents folder (made the first time), or a folder inside it."""
    try:
        memory.folder(settings, HOME)
    except ValueError:
        memory.create_folder(settings, "", HOME)
    return memory.folder(settings, f"{HOME}/{sub}", create=True) if sub else memory.folder(settings, HOME)


def target(settings: Settings, folder: str = "") -> Path:
    """Where a new file goes: the named memory folder (inner folders made as needed), else Documents."""
    home(settings)
    folder = str(folder or "").strip()
    return memory.folder(settings, folder, create=True) if folder else home(settings)


def find(settings: Settings, name: str, folder: str = "", suffixes=(".md",), templates: bool = False) -> Path:
    """An existing file by name (any case, a close name is fine), searching inner folders too."""
    base = memory.root(settings).resolve()
    tpl = (home(settings) / TEMPLATES).resolve()
    if templates:
        tpl.mkdir(exist_ok=True)
    top = tpl if templates else (memory.folder(settings, folder).resolve() if str(folder or "").strip() else base)
    want = str(name or "").strip().lower()
    for suffix in suffixes:
        want = want.removesuffix(suffix)
    if not want:
        raise ValueError("Which document?")
    files = [p for p in top.rglob("*") if p.is_file() and p.suffix.lower() in suffixes
             and not any(q.startswith(".") for q in p.relative_to(base).parts)
             and (templates or tpl not in p.parents)]
    for match in (lambda p: p.stem.lower() == want, lambda p: want in p.stem.lower()):
        found = [p for p in files if match(p)]
        if found:
            return max(found, key=lambda p: p.stat().st_mtime)
    kind = "template" if templates else ("spreadsheet" if suffixes == (".csv",) else "document")
    raise ValueError(f"I can't find a {kind} called {name}.")


def rel(settings: Settings, path: Path) -> str:
    return path.resolve().relative_to(memory.root(settings).resolve()).as_posix()


def new_path(settings: Settings, folder: str, title: str, suffix: str) -> Path:
    return memory.unique_path(target(settings, folder) / f"{memory.safe_name(title, 'title')}{suffix}")


# ---- Versions --------------------------------------------------------------------------------------

def versions_dir(path: Path) -> Path:
    return path.parent / ".versions" / path.name


def versions(path: Path) -> list[Path]:
    """Saved earlier copies, newest first."""
    d = versions_dir(path)
    return sorted((p for p in d.iterdir() if p.is_file()), key=lambda p: p.name, reverse=True) if d.is_dir() else []


def snapshot(path: Path) -> None:
    """Keep the file's current contents as a version before it changes."""
    if not path.is_file():
        return
    d = versions_dir(path)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}{path.suffix}").write_bytes(path.read_bytes())
    for old in versions(path)[MAX_VERSIONS:]:
        old.unlink()


def write(path: Path, text: str) -> None:
    if len(text) > MAX_TEXT:
        raise ValueError("That document is too long (over 200,000 characters).")
    if path.is_file() and path.read_text(encoding="utf-8", errors="replace") == text:
        return
    snapshot(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    snapshot(path)
    path.write_bytes(data)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def version_label(v: Path) -> str:
    try:
        when = datetime.strptime(v.stem[:15], "%Y%m%d-%H%M%S")
    except ValueError:
        return v.name
    return f"{when:%d %b %Y %H:%M:%S} ({v.stat().st_size:,} bytes)"


# ---- Markdown ------------------------------------------------------------------------------------

def blocks(md: str) -> list[tuple]:
    """Markdown as simple blocks: (h1..h6, text), (p, text with line breaks), (ul, text, level),
    (ol, text, number, level), (hr,)."""
    out, para = [], []

    def flush():
        if para:
            out.append(("p", "\n".join(para)))
            para.clear()

    for raw in str(md).splitlines():
        line = raw.rstrip()
        indent = (len(line) - len(line.lstrip(" \t"))) // 2
        stripped = line.strip()
        if not stripped:
            flush()
        elif m := HEADING.match(stripped):
            flush()
            out.append((f"h{len(m.group(1))}", m.group(2)))
        elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            flush()
            out.append(("hr",))
        elif m := re.match(r"^[-*+]\s+(.*)$", stripped):
            flush()
            out.append(("ul", m.group(1), min(indent, 4)))
        elif m := re.match(r"^(\d{1,4})[.)]\s+(.*)$", stripped):
            flush()
            out.append(("ol", m.group(2), m.group(1), min(indent, 4)))
        else:
            para.append(stripped)
    flush()
    return out


def inline_html(text: str) -> str:
    """Escaped text with **bold**, *italic*/_italic_ and [links](https://...)."""
    links = []

    def link(m):
        label, url = m.group(1), html.unescape(m.group(2))
        if not re.match(r"^(https?://|mailto:)", url, re.I):
            return m.group(0)
        links.append(f'<a href="{html.escape(url, quote=True)}">{label}</a>')
        return f"\x00{len(links) - 1}\x00"

    out = re.sub(r"\[([^\]\n]+)\]\(([^)\s]+)\)", link, html.escape(text, quote=True))
    out = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?![*\w])", r"<em>\1</em>", out)
    out = re.sub(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)", r"<em>\1</em>", out)
    out = re.sub(r"\x00(\d+)\x00", lambda m: re.sub(r"</?(strong|em)>", "", links[int(m.group(1))]), out)
    return out.replace("\n", "<br>\n")


def inline_plain(text: str) -> str:
    text = re.sub(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"\1", text)
    text = re.sub(r"(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?![*\w])", r"\1", text)
    return re.sub(r"(?<!\w)_(?=\S)(.+?)(?<=\S)_(?!\w)", r"\1", text)


HTML_STYLE = """
body { max-width: 46em; margin: 3em auto; padding: 0 1.2em; font: 16px/1.6 Georgia, 'Times New Roman', serif;
       color: #111; background: #fff; }
h1, h2, h3, h4, h5, h6 { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.25; margin: 1.4em 0 0.5em; }
h1 { font-size: 2em; border-bottom: 2px solid #111; padding-bottom: 0.2em; }
h2 { font-size: 1.45em; border-bottom: 1px solid #ccc; padding-bottom: 0.15em; }
a { color: #0645ad; }
hr { border: 0; border-top: 1px solid #ccc; margin: 2em 0; }
li.l1 { margin-left: 1.5em; } li.l2 { margin-left: 3em; } li.l3, li.l4 { margin-left: 4.5em; }
@media print { body { margin: 0; } a { color: inherit; } }
"""


def to_html(md: str, title: str) -> str:
    """A standalone, styled HTML page from Markdown. Everything is escaped; no scripts."""
    parts, open_list = [], ""
    for b in blocks(md):
        kind = b[0]
        want = kind if kind in ("ul", "ol") else ""
        if open_list and want != open_list:
            parts.append(f"</{open_list}>")
            open_list = ""
        if want and not open_list:
            parts.append(f"<{want}>")
            open_list = want
        if kind in ("ul", "ol"):
            level = b[-1]
            parts.append(f'<li class="l{level}">{inline_html(b[1])}</li>' if level else f"<li>{inline_html(b[1])}</li>")
        elif kind == "hr":
            parts.append("<hr>")
        elif kind == "p":
            parts.append(f"<p>{inline_html(b[1])}</p>")
        else:
            parts.append(f"<{kind}>{inline_html(b[1])}</{kind}>")
    if open_list:
        parts.append(f"</{open_list}>")
    return (f'<!doctype html>\n<html lang="en-GB">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{html.escape(title)}</title>\n<style>{HTML_STYLE}</style>\n</head>\n<body>\n"
            + "\n".join(parts) + "\n</body>\n</html>\n")


# ---- PDF (Pillow) -------------------------------------------------------------------------------

DPI = 150
PAGE = (1240, 1754)  # A4 at 150 dpi
MARGIN = 125
SIZES = {"h1": 46, "h2": 36, "h3": 30, "h4": 27, "h5": 26, "h6": 26, "p": 25}
FONT_FILES = {False: ("DejaVuSans.ttf", "arial.ttf", "LiberationSans-Regular.ttf", "Arial.ttf"),
              True: ("DejaVuSans-Bold.ttf", "arialbd.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf")}


def font(size: int, bold: bool = False):
    for name in FONT_FILES[bold]:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow before 10.1
        return ImageFont.load_default()


def _fit(text: str, f) -> str:
    """Text the font can draw: the old bitmap font only knows Latin-1."""
    text = text.replace("•", "-") if not isinstance(f, ImageFont.FreeTypeFont) else text
    return text if isinstance(f, ImageFont.FreeTypeFont) else text.encode("latin-1", "replace").decode("latin-1")


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines = []
    for hard in text.split("\n"):
        line = ""
        for word in hard.split(" "):
            trial = f"{line} {word}" if line else word
            if draw.textlength(trial, font=f) <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
            while draw.textlength(line, font=f) > width and len(line) > 1:  # a very long word
                cut = len(line)
                while cut > 1 and draw.textlength(line[:cut], font=f) > width:
                    cut -= 1
                lines.append(line[:cut])
                line = line[cut:]
        lines.append(line)
    return lines


def to_pdf(md: str) -> bytes:
    """A4 pages of word-wrapped text at 150 dpi: headings bigger and bold, lists with bullets, page numbers."""
    pages: list[Image.Image] = []
    state = {}

    def new_page():
        page = Image.new("RGB", PAGE, "white")
        pages.append(page)
        state.update(draw=ImageDraw.Draw(page), y=MARGIN)

    new_page()
    width = PAGE[0] - 2 * MARGIN
    for b in blocks(md) or [("p", " ")]:
        kind = b[0]
        if kind == "hr":
            if state["y"] > PAGE[1] - MARGIN - 20:
                new_page()
            state["draw"].line((MARGIN, state["y"] + 10, PAGE[0] - MARGIN, state["y"] + 10), fill="#999999", width=2)
            state["y"] += 34
            continue
        heading = kind.startswith("h")
        f = font(SIZES.get(kind, SIZES["p"]), bold=heading)
        indent = 0
        text = inline_plain(b[1])
        if kind in ("ul", "ol"):
            indent = 40 * (b[-1] + 1)
            text = f"{b[2]}. {text}" if kind == "ol" else f"• {text}"
        text = _fit(text, f)
        line_h = int(SIZES.get(kind, SIZES["p"]) * 1.45)
        if heading:
            state["y"] += line_h // 2
        for line in wrap(state["draw"], text, f, width - indent):
            if state["y"] + line_h > PAGE[1] - MARGIN:
                new_page()
            state["draw"].text((MARGIN + indent, state["y"]), line, font=f, fill="black")
            state["y"] += line_h
        state["y"] += 6 if kind in ("ul", "ol") else line_h // 2
    small = font(20)
    for n, page in enumerate(pages, 1):
        label = f"{n} / {len(pages)}"
        d = ImageDraw.Draw(page)
        d.text((PAGE[0] - MARGIN - d.textlength(label, font=small), PAGE[1] - MARGIN // 2), label, font=small,
               fill="#666666")
    out = io.BytesIO()
    pages[0].save(out, "PDF", resolution=DPI, save_all=True, append_images=pages[1:])
    return out.getvalue()


def export_pdf(settings: Settings, path: Path) -> Path:
    pdf = path.with_suffix(".pdf")
    write_bytes(pdf, to_pdf(read(path)))
    return pdf


# ---- Sections, contents, counts -----------------------------------------------------------------

def heading_at(line: str):
    m = HEADING.match(line.strip())
    return (len(m.group(1)), m.group(2).strip()) if m else None


def section_span(lines: list[str], heading: str):
    """(heading line index, end index) of the section under a heading (any case, a close name is fine)."""
    want = heading.strip().lstrip("#").strip().lower()
    found = [(i, h) for i, line in enumerate(lines) if (h := heading_at(line))]
    for match in (lambda h: h[1].lower() == want, lambda h: want in h[1].lower()):
        for i, h in found:
            if match(h):
                end = next((j for j, g in found if j > i and g[0] <= h[0]), len(lines))
                return i, end
    return None


def add_to_section(text: str, heading: str, addition: str, replace: bool) -> str:
    lines = text.splitlines()
    addition = str(addition or "").strip("\n")
    if not heading:
        if replace:
            raise ValueError("Which section should I replace? Give its heading.")
        return text.rstrip("\n") + f"\n\n{addition}\n"
    span = section_span(lines, heading)
    if not span:
        if replace:
            raise ValueError(f"There's no section called {heading}.")
        title = heading.strip().lstrip("#").strip()
        return text.rstrip("\n") + f"\n\n## {title}\n\n{addition}\n"
    start, end = span
    body = lines[start + 1:end]
    if replace:
        body = ["", *addition.splitlines(), ""]
    else:
        while body and not body[-1].strip():
            body.pop()
        lists = body and LIST_ITEM.match(body[-1]) and LIST_ITEM.match(addition.lstrip())
        body = [*body, *([] if lists else [""]), *addition.splitlines(), ""]
    tail = lines[end:]
    if not tail and body and body[-1] == "":
        body.pop()
    return "\n".join(lines[:start + 1] + body + tail) + "\n"


def contents(text: str) -> str:
    """The document with a Contents section (from its headings) at the top, replacing an old one."""
    lines = text.splitlines()
    span = section_span(lines, "Contents")
    if span and lines[span[0]].strip().lower().lstrip("#").strip() == "contents":
        end = span[0] + 1
        while end < span[1] and (not lines[end].strip() or re.match(r"^\s*- ", lines[end])):
            end += 1
        del lines[span[0]:end]
    found = [h for line in lines if (h := heading_at(line))]
    has_title = bool(found) and found[0][0] == 1 and sum(1 for h in found if h[0] == 1) == 1
    entries = found[1:] if has_title else found
    if not entries:
        raise ValueError("That document has no headings to make contents from.")
    top = min(h[0] for h in entries)
    toc = ["## Contents", ""] + [f"{'  ' * min(h[0] - top, 3)}- {inline_plain(h[1])}" for h in entries] + [""]
    at = next((i + 1 for i, line in enumerate(lines) if heading_at(line)), 0) if has_title else 0
    while has_title and at < len(lines) and not lines[at].strip():
        at += 1
    if has_title:
        return "\n".join(lines[:at] + (["", *toc] if lines[:at] and lines[at - 1].strip() else toc) + lines[at:]) + "\n"
    return "\n".join(toc + lines) + "\n"


def counts(text: str) -> dict:
    plain = "\n".join(inline_plain(b[1]) for b in blocks(text) if len(b) > 1)
    words = len(re.findall(r"[\w'’-]+", plain))
    return {"words": words, "characters": len(plain), "paragraphs": sum(1 for b in blocks(text) if b[0] == "p"),
            "headings": sum(1 for b in blocks(text) if b[0] in SIZES and b[0] != "p"),
            "read": max(1, round(words / READ_WPM)) if words else 0,
            "speak": max(1, round(words / SPEAK_WPM)) if words else 0}


# ---- Pop-ups -------------------------------------------------------------------------------------

def doc_card(settings: Settings, path: Path, extra=None) -> dict:
    name = path.stem
    buttons = (extra or []) + [{"label": "Word count", "say": f"How many words are in the document {name}?"},
                               {"label": "Make PDF", "say": f"Export the document {name} to PDF."}]
    return screen.file_card(settings, path, buttons=buttons)


def shown_doc(settings: Settings, path: Path, said: str, extra=None) -> screen.Shown:
    return screen.Shown(said, doc_card(settings, path, extra))


# ---- Actions -------------------------------------------------------------------------------------

def new(settings: Settings, args: dict) -> screen.Shown:
    title = str(args.get("title") or "").strip()
    body = str(args.get("text") or "").strip()
    if not title:
        raise ValueError("What should the document be called?")
    path = new_path(settings, args.get("folder") or "", title, ".md")
    write(path, (body if body.startswith("# ") else f"# {title}\n\n{body}").rstrip() + "\n")
    return shown_doc(settings, path, f"Wrote {path.stem} in {path.parent.name}. It's on the screen.")


def edit_section(settings: Settings, args: dict, replace: bool) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    text = str(args.get("text") or "")
    if not text.strip():
        raise ValueError("What should I write?")
    write(path, add_to_section(read(path), str(args.get("heading") or ""), text, replace))
    where = f"the {args['heading']} section of " if args.get("heading") else ""
    said = f"{'Replaced' if replace else 'Added to'} {where}{path.stem}."
    return shown_doc(settings, path, said, [{"label": "Undo", "say": f"Show the versions of the document {path.stem}."}])


def show(settings: Settings, args: dict) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    text = read(path)
    more = " (it goes on; the rest is on the screen)" if len(text) > SPOKEN_LIMIT else ""
    return shown_doc(settings, path, f"{path.stem} is on the screen{more}. It says:\n{text[:SPOKEN_LIMIT]}")


def word_count(settings: Settings, args: dict) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    c = counts(read(path))
    rows = [["Words", f"{c['words']:,}"], ["Characters", f"{c['characters']:,}"], ["Paragraphs", str(c["paragraphs"])],
            ["Headings", str(c["headings"])], ["Reading time", f"about {c['read']} min"],
            ["Reading aloud", f"about {c['speak']} min"]]
    said = f"{path.stem} has {c['words']:,} words, about {c['read']} minute{'s' if c['read'] != 1 else ''} to read."
    return screen.Shown(said, screen.card("table", f"{path.stem}: word count", f"docs-count-{rel(settings, path)}",
                                          columns=["", ""], rows=rows))


def find_replace(settings: Settings, args: dict) -> screen.Shown | str:
    path = find(settings, args.get("name"), args.get("folder") or "")
    old = str(args.get("find") or "")
    if not old:
        raise ValueError("What should I look for?")
    new_text = str(args.get("replace_with") or "")
    pattern = re.compile(re.escape(old), 0 if args.get("match_case") else re.I)
    text = read(path)
    n = len(pattern.findall(text))
    if not n:
        return f"'{old}' isn't in {path.stem}, so nothing changed."
    if n > MAX_REPLACE_UNCONFIRMED and args.get("confirmed") is not True:
        return (f"'{old}' appears {n} times in {path.stem}. Nothing changed yet: ask the user to confirm replacing "
                "all of them, then call again with confirmed true.")
    write(path, pattern.sub(lambda m: new_text, text))
    return shown_doc(settings, path, f"Replaced {n} time{'s' if n != 1 else ''} in {path.stem}.",
                     [{"label": "Undo", "say": f"Show the versions of the document {path.stem}."}])


def table_of_contents(settings: Settings, args: dict) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    write(path, contents(read(path)))
    return shown_doc(settings, path, f"Added contents to the top of {path.stem}.")


def export_html(settings: Settings, args: dict) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    out = path.with_suffix(".html")
    write(out, to_html(read(path), path.stem))
    return shown_doc(settings, path, f"Saved {out.name} in {rel(settings, out.parent)}; open it in a web browser to see "
                                     "the styled page. The document is on the screen.",
                     [{"label": "Open HTML on PC", "say": f"Open the file {out.name} from {out.parent.name} on my PC."}])


def export(settings: Settings, args: dict) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    pdf = export_pdf(settings, path)
    return screen.Shown(f"Saved {pdf.name} in {rel(settings, pdf.parent)}. It's on the screen.",
                        screen.file_card(settings, pdf))


def compare(settings: Settings, args: dict) -> screen.Shown | str:
    a = find(settings, args.get("name"), args.get("folder") or "", (".md", ".csv", ".txt"))
    b = find(settings, args.get("other"), args.get("other_folder") or "", (".md", ".csv", ".txt"))
    diff = list(difflib.unified_diff(read(a).splitlines(), read(b).splitlines(), rel(settings, a), rel(settings, b),
                                     lineterm="", n=2))
    if not diff:
        return f"{a.stem} and {b.stem} are the same."
    added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    said = f"{b.stem} has {added} line{'s' if added != 1 else ''} added and {removed} taken away compared with {a.stem}."
    return screen.Shown(said, screen.card("text", f"{a.stem} vs {b.stem}", f"docs-diff-{a.stem}-{b.stem}",
                                          text="\n".join(diff)))


# ---- Versions and templates -------------------------------------------------------------------

def list_versions(settings: Settings, args: dict) -> screen.Shown | str:
    path = find(settings, args.get("name"), args.get("folder") or "", (".md", ".csv"))
    found = versions(path)
    if not found:
        return f"{path.name} has no earlier versions yet."
    items = [{"label": f"{i}. {version_label(v)}", "say": f"Restore version {i} of {path.name}."}
             for i, v in enumerate(found, 1)]
    said = f"{path.name} has {len(found)} earlier version{'s' if len(found) != 1 else ''}; version 1 is the newest."
    return screen.Shown(said, screen.card("list", f"Versions of {path.name}", f"docs-versions-{rel(settings, path)}",
                                          items=items))


def restore(settings: Settings, args: dict) -> screen.Shown | str:
    path = find(settings, args.get("name"), args.get("folder") or "", (".md", ".csv"))
    found = versions(path)
    n = int(args.get("version") or 1)
    if not 1 <= n <= len(found):
        raise ValueError(f"{path.name} has {len(found)} earlier version(s); pick 1 to {len(found)}." if found
                         else f"{path.name} has no earlier versions.")
    if args.get("confirmed") is not True:
        return (f"Not restored yet. Ask the user to confirm putting {path.name} back to version {n} "
                f"({version_label(found[n - 1])}), then call again with confirmed true. The current text is kept as a version.")
    data = found[n - 1].read_bytes()
    write_bytes(path, data)
    said = f"Put {path.name} back to how it was on {version_label(found[n - 1]).split(' (')[0]}."
    if path.suffix == ".csv":
        import docs_tools_sheets
        return docs_tools_sheets.show_sheet(settings, path, said)
    return shown_doc(settings, path, said)


def save_template(settings: Settings, args: dict) -> screen.Shown:
    path = find(settings, args.get("name"), args.get("folder") or "")
    name = memory.safe_name(args.get("template") or path.stem, "template name")
    out = home(settings, TEMPLATES) / f"{name}.md"
    write(out, read(path))
    fields = sorted({m.group(1).strip() for m in PLACEHOLDER.finditer(read(out))})
    tip = f" It has blanks for {', '.join(fields)}." if fields else " Put {{name}}-style blanks in it to fill in later."
    return screen.Shown(f"Saved {path.stem} as the template {name}.{tip}", screen.file_card(settings, out))


def list_templates(settings: Settings) -> screen.Shown | str:
    found = sorted(home(settings, TEMPLATES).glob("*.md"), key=lambda p: p.stem.lower())
    if not found:
        return "There are no templates yet. Ask me to save a document as a template."
    items = []
    for p in found:
        fields = sorted({m.group(1).strip() for m in PLACEHOLDER.finditer(read(p))})
        label = p.stem + (f" (blanks: {', '.join(fields)})" if fields else "")
        items.append({"label": label, "say": f"Make a new document from the {p.stem} template."})
    return screen.Shown(f"{len(found)} template{'s' if len(found) != 1 else ''}: {', '.join(p.stem for p in found)}.",
                        screen.card("list", "Templates", "docs-templates", items=items))


def from_template(settings: Settings, args: dict) -> screen.Shown:
    tpl = find(settings, args.get("template"), templates=True)
    values = {str(k).strip().lower(): str(v) for k, v in (args.get("values") or {}).items()}
    missing = set()

    def fill(m):
        key = m.group(1).strip().lower()
        if key in values:
            return values[key]
        missing.add(m.group(1).strip())
        return m.group(0)

    text = PLACEHOLDER.sub(fill, read(tpl))
    title = str(args.get("title") or tpl.stem).strip()
    path = new_path(settings, args.get("folder") or "", title, ".md")
    write(path, text)
    said = f"Made {path.stem} from the {tpl.stem} template."
    if missing:
        said += f" Still blank: {', '.join(sorted(missing))}."
    return shown_doc(settings, path, said)


# ---- Tools ---------------------------------------------------------------------------------------

DOC_ACTIONS = ["new", "add", "replace_section", "show", "word_count", "find_replace", "contents", "export_html",
               "export_pdf", "compare"]
HISTORY_ACTIONS = ["versions", "restore", "save_template", "templates", "from_template"]


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "document",
            "description": "Write and edit the user's documents (Markdown files in their memory folders) and show them "
                           "in a pop-up. action: 'new' writes a document (you write title and text in Markdown); "
                           "'add' adds text to the end, or under a heading (section); 'replace_section' rewrites the "
                           "text under a heading; 'show' opens or reads a document aloud; 'word_count' words and "
                           "reading time; 'find_replace' find and replace text (if over 20 matches, set confirmed "
                           "true only after the user agrees); 'contents' puts a table of contents at the top; "
                           "'export_html' saves a web page (HTML) copy; 'export_pdf' makes a PDF; 'compare' shows the "
                           "differences between two documents.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": DOC_ACTIONS},
                    "name": {"type": "string", "description": "The document's name, or part of it."},
                    "title": {"type": "string", "description": "new: the document's title (also its file name)."},
                    "folder": {"type": "string", "description": "Memory folder, e.g. 'Work' or 'Work/Reports'. "
                                                                "Leave out: new ones go in Documents, and documents "
                                                                "are looked for everywhere."},
                    "text": {"type": "string", "description": "new, add, replace_section: Markdown text."},
                    "heading": {"type": "string", "description": "add, replace_section: the section's heading."},
                    "find": {"type": "string"},
                    "replace_with": {"type": "string"},
                    "match_case": {"type": "boolean"},
                    "other": {"type": "string", "description": "compare: the second document's name."},
                    "other_folder": {"type": "string"},
                    "confirmed": {"type": "boolean", "description": "find_replace: true only after the user said yes."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "document_history",
            "description": "Earlier versions and templates of the user's documents and spreadsheets. action: "
                           "'versions' lists earlier versions (kept automatically on every change); 'restore' puts "
                           "one back, to undo changes (ask first; set confirmed true only after the user says yes); "
                           "'save_template' saves a document as a reusable template ({{name}}-style blanks); "
                           "'templates' lists templates; 'from_template' makes a new document from a template, "
                           "filling its blanks from values.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": HISTORY_ACTIONS},
                    "name": {"type": "string", "description": "The document or spreadsheet's name."},
                    "folder": {"type": "string"},
                    "version": {"type": "integer", "description": "restore: 1 is the newest earlier version."},
                    "confirmed": {"type": "boolean", "description": "restore: true only after the user said yes."},
                    "template": {"type": "string", "description": "The template's name."},
                    "title": {"type": "string", "description": "from_template: the new document's title."},
                    "values": {"type": "object", "additionalProperties": {"type": "string"},
                               "description": "from_template: blanks to fill, e.g. {\"name\": \"Sam\"}."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    ]


NAMES = {"document", "document_history"}
DOC_RUN = {"new": new, "add": lambda s, a: edit_section(s, a, False),
           "replace_section": lambda s, a: edit_section(s, a, True), "show": show, "word_count": word_count,
           "find_replace": find_replace, "contents": table_of_contents, "export_html": export_html,
           "export_pdf": export, "compare": compare}
HISTORY_RUN = {"versions": list_versions, "restore": restore, "save_template": save_template,
               "templates": lambda s, a: list_templates(s), "from_template": from_template}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    table = DOC_RUN if name == "document" else HISTORY_RUN
    action = table.get(args.get("action"))
    if not action:
        raise ValueError(f"Pick an action: {', '.join(table)}.")
    return action(settings, args)
