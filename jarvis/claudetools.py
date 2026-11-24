"""Claude's free tools, in Alfred.

The owner (24 Nov 2026): "all the free tools claude has give them to alfred". This module fills the gaps between
what Claude can do in the Claude app and what Alfred could already do, using only free things (no paid service,
no account, no Claude login through anything):

- free_web_search / free_web_fetch: Claude's web search and web page reading. Claude's own web_search and
  web_fetch only exist when Claude answers; when the free AI (OmniRoute) answers, Alfred had no web at all. These
  two run on the PC (DuckDuckGo's plain page, Wikipedia as a backup, and the page itself), so every route has them.
  They also read PDFs on the web.
- office_file: Claude's Word, Excel, PowerPoint and PDF skills. Makes real .docx, .xlsx and .pptx files in the
  memory folders, and reads .pdf, .docx, .xlsx, .pptx, .csv, .txt and .md files (python-docx, openpyxl,
  python-pptx and pypdf, all free).
- claude_tools: the list itself (what Claude has, what Alfred uses for it), shown on the HUD. It is in the BOTS
  window too.

Passwords and card numbers are never typed by any of these; the password check stays in the browser pop-up.
"""

import asyncio
import csv
import html
import io
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import httpx

import docs_tools
import memory
import screen
import webread_extract
import webview_common as web
from config import Settings

NAMES = {"free_web_search", "free_web_fetch", "office_file", "claude_tools"}
# Always given to the free AI, even though they are deferred for Claude (who has his own web_search / web_fetch).
FREE_ROUTE_TOOLS = ("free_web_search", "free_web_fetch")
KIND = "showme"
screen.EXTRA_KINDS.add(KIND)

MAX_RESULTS = 8
MAX_CHARS = 12000  # characters of a page or file handed back in one go
READ_SUFFIXES = (".pdf", ".docx", ".xlsx", ".xlsm", ".pptx", ".csv", ".txt", ".md")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Alfred-assistant"}
INSTALL = "That needs a free add-on that isn't installed yet: run pip install -r requirements.txt and restart me."

# What Claude has, and what Alfred uses for it. "free" is False only where the Claude tool costs money.
CLAUDE_TOOLS = [
    {"group": "Web", "claude": "Web search", "alfred": "web_search when Claude answers, free_web_search always",
     "free": True},
    {"group": "Web", "claude": "Web fetch (read a page or online PDF)",
     "alfred": "web_fetch when Claude answers, free_web_fetch always", "free": True},
    {"group": "Web", "claude": "Browser (Claude in Chrome)", "alfred": "Alfred's own browser (browser tool, Playwright)",
     "free": True},
    {"group": "Files", "claude": "Word documents (docx skill)", "alfred": "office_file make_word / read", "free": True},
    {"group": "Files", "claude": "Excel spreadsheets (xlsx skill)",
     "alfred": "office_file make_excel / read, and spreadsheet", "free": True},
    {"group": "Files", "claude": "PowerPoint decks (pptx skill)", "alfred": "office_file make_powerpoint / read",
     "free": True},
    {"group": "Files", "claude": "PDF reading and making (pdf skill)",
     "alfred": "office_file read, document export_pdf", "free": True},
    {"group": "Files", "claude": "Docs (living documents)", "alfred": "document, document_history, document_forms",
     "free": True},
    {"group": "Files", "claude": "Read, search and edit files",
     "alfred": "search_memory, find_memory_files, manage_memory_files", "free": True},
    {"group": "Thinking", "claude": "Tool search", "alfred": "tool_search (Claude) and find_tool (free AI)",
     "free": True},
    {"group": "Thinking", "claude": "Memory", "alfred": "remember_about_user, Alfred's own memory (Claude Mem)",
     "free": True},
    {"group": "Thinking", "claude": "Skills", "alfred": "the design skills folder and skill_check", "free": True},
    {"group": "Computer", "claude": "Computer use (screen, mouse, keys)",
     "alfred": "the computer toolset, look_at_screen, pc tools", "free": True},
    {"group": "Computer", "claude": "Connectors (MCP servers)", "alfred": "mcp_bridge (the Claude app's MCP servers)",
     "free": True},
    {"group": "Computer", "claude": "Run code (code execution)",
     "alfred": "the calculators for sums; Claude's own sandbox is left out on purpose",
     "free": False, "why": "it runs on Anthropic's machines and is billed past the free hours, so it stays off"},
    {"group": "Computer", "claude": "Image and video making",
     "alfred": "Higgsfield through mcp_bridge, only after you say yes to the cost", "free": False,
     "why": "Higgsfield credits are paid"},
]


# ---- Web -----------------------------------------------------------------------------------------

def _ddg_link(href: str) -> str:
    """DuckDuckGo wraps each result as //duckduckgo.com/l/?uddg=<the real link>."""
    href = html.unescape(href or "")
    if "uddg=" in href:
        return unquote(parse_qs(urlparse(href if href.startswith("http") else "https:" + href).query)["uddg"][0])
    return href if href.startswith("http") else ""


def _strip(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", markup or ""))).strip()


def parse_ddg(markup: str, limit: int = MAX_RESULTS) -> list[dict]:
    """Results from DuckDuckGo's plain HTML page as [{title, url, snippet}]."""
    out = []
    for block in re.split(r'<div[^>]+class="[^"]*\bresult\b', markup)[1:]:
        a = re.search(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not a or "result--ad" in block[:200]:
            continue
        url = _ddg_link(a.group(1))
        if not url or "duckduckgo.com/y.js" in url:
            continue  # adverts
        snip = re.search(r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</(?:a|td|div)>', block, re.S)
        out.append({"title": _strip(a.group(2)), "url": url, "snippet": _strip(snip.group(1)) if snip else ""})
        if len(out) >= limit:
            break
    return out


async def _wikipedia(http: httpx.AsyncClient, query: str, limit: int) -> list[dict]:
    r = await http.get("https://en.wikipedia.org/w/api.php", headers=UA, timeout=10, params={
        "action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"})
    r.raise_for_status()
    return [{"title": h["title"], "url": "https://en.wikipedia.org/wiki/" + h["title"].replace(" ", "_"),
             "snippet": _strip(h.get("snippet", ""))} for h in r.json().get("query", {}).get("search", [])]


async def search(http: httpx.AsyncClient, query: str, limit: int = 5) -> list[dict]:
    query = web.need(query, "what to search for", 300)
    limit = min(max(int(limit or 5), 1), MAX_RESULTS)
    try:
        r = await http.post("https://html.duckduckgo.com/html/", data={"q": query, "kl": "uk-en"}, headers=UA,
                            timeout=12, follow_redirects=True)
        found = parse_ddg(r.text, limit) if r.status_code == 200 else []
    except httpx.HTTPError:
        found = []
    if not found:
        try:
            found = await _wikipedia(http, query, limit)
        except (httpx.HTTPError, ValueError):
            found = []
    return found


async def web_search(http: httpx.AsyncClient, args: dict) -> str:
    query = str(args.get("query") or "")
    found = await search(http, query, args.get("max_results") or 5)
    if not found:
        return f"The free web search found nothing for {query!r} (or it isn't answering). Try other words."
    lines = [f"{i}. {r['title']} - {r['url']}\n   {r['snippet']}" for i, r in enumerate(found, 1)]
    return (f"Web results for {query!r} (free search; read a page with free_web_fetch before relying on it, and "
            "say where facts came from):\n" + "\n".join(lines))


def pdf_text(data: bytes, pages: str = "") -> tuple[str, int]:
    """The words in a PDF (all pages, or a range like '2-5'), and how many pages it has."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError(INSTALL) from None
    reader = PdfReader(io.BytesIO(data))
    total = len(reader.pages)
    first, last = 1, total
    m = re.fullmatch(r"\s*(\d+)\s*(?:-\s*(\d+))?\s*", str(pages or ""))
    if m:
        first = max(1, int(m.group(1)))
        last = min(total, int(m.group(2) or m.group(1)))
    parts = [f"[Page {n}]\n{(reader.pages[n - 1].extract_text() or '').strip()}" for n in range(first, last + 1)]
    return "\n\n".join(parts), total


async def web_fetch(http: httpx.AsyncClient, args: dict) -> str:
    url = str(args.get("url") or "").strip()
    if not url:
        raise ValueError("Which web address?")
    limit = min(max(int(args.get("max_chars") or MAX_CHARS), 500), 40000)
    r = await web.get_public(http, url, limit=20 * 1024 * 1024)
    kind = r.headers.get("content-type", "").lower()
    if "pdf" in kind or str(r.url).lower().endswith(".pdf"):
        text, total = await asyncio.to_thread(pdf_text, r.content, args.get("pages") or "")
        head = f"PDF from {r.url} ({total} page{'s' if total != 1 else ''})"
    else:
        page = await webread_extract.fetch_page(http, url)
        text = webread_extract.plain(page["blocks"])
        head = f"{page['title']} ({page['url']})"
    cut = len(text) > limit
    return f"{head}:\n\n{text[:limit]}" + ("\n\n[Cut short. Ask for less, or a page range for a PDF.]" if cut else "")


# ---- Office files ------------------------------------------------------------------------------

def _name(title: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(title or "")).strip(" .")[:80]
    if not name:
        raise ValueError("What should the file be called? Give it a title.")
    return name


def _free(folder: Path, name: str, suffix: str) -> Path:
    path, n = folder / f"{name}{suffix}", 2
    while path.exists():
        path, n = folder / f"{name} ({n}){suffix}", n + 1
    return path


def _runs(paragraph, text: str) -> None:
    """Markdown **bold** and *italic* inside a Word paragraph."""
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            paragraph.add_run(part[1:-1]).italic = True
        else:
            paragraph.add_run(part)


def make_word(path: Path, title: str, text: str) -> None:
    try:
        from docx import Document
    except ImportError:
        raise ValueError(INSTALL) from None
    doc = Document()
    doc.add_heading(title, 0)
    table: list[list[str]] = []

    def flush():
        if table:
            cols = max(len(r) for r in table)
            t = doc.add_table(rows=len(table), cols=cols)
            t.style = "Table Grid"
            for i, row in enumerate(table):
                for j, cell in enumerate(row):
                    t.cell(i, j).text = cell
            table.clear()

    for line in str(text or "").splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            if not re.fullmatch(r"\|[\s:|-]+\|", s):
                table.append([c.strip() for c in s.strip("|").split("|")])
            continue
        flush()
        if not s:
            continue
        if m := re.match(r"(#{1,4})\s+(.*)", s):
            doc.add_heading(m.group(2), min(len(m.group(1)), 4))
        elif m := re.match(r"[-*+]\s+(.*)", s):
            _runs(doc.add_paragraph(style="List Bullet"), m.group(1))
        elif m := re.match(r"\d{1,3}[.)]\s+(.*)", s):
            _runs(doc.add_paragraph(style="List Number"), m.group(1))
        else:
            _runs(doc.add_paragraph(), s)
    flush()
    doc.save(path)


def _cell(value):
    if isinstance(value, str):
        v = value.strip()
        if re.fullmatch(r"-?\d+", v) and not (len(v) > 1 and v.lstrip("-").startswith("0")):
            return int(v)
        if re.fullmatch(r"-?\d*\.\d+", v):
            return float(v)
        return value
    return value


def make_excel(path: Path, sheets: list) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        raise ValueError(INSTALL) from None
    if not sheets:
        raise ValueError("Give me at least one sheet with rows.")
    book = Workbook()
    book.remove(book.active)
    for i, sheet in enumerate(sheets[:20], 1):
        name = re.sub(r"[\[\]:*?/\\]", "", str(sheet.get("name") or f"Sheet{i}"))[:31] or f"Sheet{i}"
        ws = book.create_sheet(name)
        for row in (sheet.get("rows") or [])[:5000]:
            ws.append([_cell(v) for v in (row if isinstance(row, list) else [row])[:100]])
        for cell in ws[1] if ws.max_row else []:
            cell.font = Font(bold=True)
        for col in ws.columns:
            width = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 8), 60)
        ws.freeze_panes = "A2"
    book.save(path)


def make_powerpoint(path: Path, title: str, slides: list) -> None:
    try:
        from pptx import Presentation
        from pptx.util import Inches
    except ImportError:
        raise ValueError(INSTALL) from None
    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)  # widescreen
    cover = deck.slides.add_slide(deck.slide_layouts[0])
    cover.shapes.title.text = title
    if len(cover.placeholders) > 1:
        cover.placeholders[1].text = ""
    for s in (slides or [])[:60]:
        slide = deck.slides.add_slide(deck.slide_layouts[1])
        slide.shapes.title.text = str(s.get("title") or "")
        body = slide.placeholders[1].text_frame
        bullets = [str(b) for b in (s.get("bullets") or [])][:12]
        body.text = bullets[0] if bullets else ""
        for b in bullets[1:]:
            body.add_paragraph().text = b
        if s.get("notes"):
            slide.notes_slide.notes_text_frame.text = str(s["notes"])
    deck.save(path)


def read_office(path: Path, pages: str = "") -> str:
    suffix = path.suffix.lower()
    if path.stat().st_size > memory.MAX_FILE_BYTES:
        raise ValueError("That file is too big to read.")
    if suffix == ".pdf":
        text, total = pdf_text(path.read_bytes(), pages)
        return f"{path.name} ({total} pages):\n\n{text}"
    try:
        if suffix == ".docx":
            from docx import Document
            doc = Document(path)
            parts = [p.text for p in doc.paragraphs if p.text.strip()]
            for t in doc.tables:
                parts += [" | ".join(c.text.strip() for c in row.cells) for row in t.rows]
            return f"{path.name}:\n\n" + "\n".join(parts)
        if suffix in (".xlsx", ".xlsm"):
            from openpyxl import load_workbook
            book = load_workbook(path, read_only=True, data_only=True)
            out = []
            for ws in book.worksheets:
                out.append(f"[Sheet {ws.title}]")
                for row in ws.iter_rows(values_only=True, max_row=2000):
                    if any(v is not None for v in row):
                        out.append(" | ".join("" if v is None else str(v) for v in row))
            book.close()
            return f"{path.name}:\n\n" + "\n".join(out)
        if suffix == ".pptx":
            from pptx import Presentation
            out = []
            for n, slide in enumerate(Presentation(path).slides, 1):
                words = [sh.text_frame.text for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
                out.append(f"[Slide {n}] " + " / ".join(words))
            return f"{path.name}:\n\n" + "\n".join(out)
    except ImportError:
        raise ValueError(INSTALL) from None
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".csv":
        raw = "\n".join(" | ".join(r) for r in csv.reader(io.StringIO(raw)))
    return f"{path.name}:\n\n{raw}"


def office_file(settings: Settings, args: dict):
    action = str(args.get("action") or "").strip()
    if action == "read":
        path = docs_tools.find(settings, args.get("name"), args.get("folder") or "", READ_SUFFIXES)
        text = read_office(path, args.get("pages") or "")
        return text[:MAX_CHARS] + ("\n\n[Cut short. Ask for a page range or a part.]" if len(text) > MAX_CHARS else "")
    makers = {"make_word": ".docx", "make_excel": ".xlsx", "make_powerpoint": ".pptx"}
    if action not in makers:
        raise ValueError("Pick an action: make_word, make_excel, make_powerpoint or read.")
    title = _name(args.get("title"))
    path = _free(docs_tools.target(settings, args.get("folder") or ""), title, makers[action])
    if action == "make_word":
        make_word(path, title, args.get("text") or "")
    elif action == "make_excel":
        make_excel(path, args.get("sheets") or [])
    else:
        make_powerpoint(path, title, args.get("slides") or [])
    where = path.parent.resolve().relative_to(memory.root(settings).resolve()).as_posix()
    return screen.Shown(f"Made {path.name} in {where}. It's on the screen.", screen.file_card(settings, path))


# ---- The list ------------------------------------------------------------------------------------

def show_list() -> screen.Shown:
    groups = list(dict.fromkeys(t["group"] for t in CLAUDE_TOOLS))
    sections = [{"type": "list", "title": g, "items": [
        {"label": f"{'✅' if t['free'] else '💷'} {t['claude']}",
         "note": t["alfred"] + (f" ({t['why']})" if t.get("why") else "")}
        for t in CLAUDE_TOOLS if t["group"] == g]} for g in groups]
    text = "Claude's tools and what I use for each:\n" + "\n".join(
        f"- {t['claude']}: {t['alfred']}" + ("" if t["free"] else f" (not free: {t.get('why', '')})")
        for t in CLAUDE_TOOLS)
    buttons = [{"label": "Try a web search", "say": "Search the web for today's top UK news"},
               {"label": "Make a Word doc", "say": "Make me a Word document with a short to-do list for tomorrow"}]
    return screen.Shown(text, screen.card(KIND, "Claude's free tools", "claude-tools", buttons=buttons,
                                          data={"sections": sections}))


# ---- Tools ---------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [
        {
            "name": "free_web_search",
            "description": "Search the web for free (DuckDuckGo, with Wikipedia as a backup): titles, links and a "
                           "line from each. Use it for anything current or that you aren't sure of, whenever your "
                           "own web_search isn't there. Then read the best page with free_web_fetch.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for."},
                    "max_results": {"type": "integer", "description": "1 to 8. Default 5."},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "free_web_fetch",
            "description": "Read the words of a public web page or an online PDF, free. Use it on links from "
                           "free_web_search or that the user gave.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full http(s) web address."},
                    "pages": {"type": "string", "description": "PDF only: pages to read, e.g. '1-3'."},
                    "max_chars": {"type": "integer", "description": "How much to read, 500 to 40000. Default 12000."},
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
        {
            "name": "office_file",
            "description": "Real Microsoft Office files and PDFs in the user's memory folders. action: "
                           "'make_word' a .docx from Markdown text (headings, bullets, numbered lists, **bold**, "
                           "| tables |); 'make_excel' a .xlsx from sheets (each a name and rows, first row is the "
                           "header); 'make_powerpoint' a .pptx deck from slides (title, bullets, speaker notes); "
                           "'read' the words in a .pdf, .docx, .xlsx, .pptx, .csv, .txt or .md file by name.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["make_word", "make_excel", "make_powerpoint", "read"]},
                    "title": {"type": "string", "description": "make_*: the title, also the file name."},
                    "folder": {"type": "string", "description": "Memory folder, e.g. 'Work'. Leave out: Documents "
                                                                "for new files, everywhere for read."},
                    "text": {"type": "string", "description": "make_word: the document in Markdown."},
                    "sheets": {"type": "array", "description": "make_excel: the sheets.", "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"},
                                       "rows": {"type": "array", "items": {"type": "array", "items": {
                                           "type": ["string", "number", "null"]}}}},
                        "required": ["rows"]}},
                    "slides": {"type": "array", "description": "make_powerpoint: the slides after the title one.",
                               "items": {"type": "object", "properties": {
                                   "title": {"type": "string"},
                                   "bullets": {"type": "array", "items": {"type": "string"}},
                                   "notes": {"type": "string"}}, "required": ["title"]}},
                    "name": {"type": "string", "description": "read: the file's name, or part of it."},
                    "pages": {"type": "string", "description": "read, PDF only: pages, e.g. '2-4'."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "claude_tools",
            "description": "Show the list of Claude's tools (web, files, Office, PDF, browser, computer, "
                           "connectors, memory, skills) and which of Alfred's tools does each, on the screen.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    if name == "free_web_search":
        return await web_search(http, args)
    if name == "free_web_fetch":
        return await web_fetch(http, args)
    if name == "office_file":
        return await asyncio.to_thread(office_file, settings, args)
    if name == "claude_tools":
        return show_list()
    raise ValueError(f"Unknown tool {name}.")
