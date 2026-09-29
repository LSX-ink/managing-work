"""Pop-up windows on the Alfred screen: files, web pages read inside Alfred, pictures, lists, tables, charts.

Any ability can return Shown(text, card): Alfred hears the text and the page pops the card up (see tools.run_tool).
A card is plain JSON drawn by frontend/popup.js. A list card with checks=True shows tick boxes. Kinds:
  text    {text}
  list    {items: [{label, done?, say?}]}          ticking or clicking an item with say sends it to Alfred
  table   {columns: [..], rows: [[..], ..]}
  chart   {chart: {type: bar|line, labels: [..], values: [..], unit?}}
  file    {src, mime, name}                       a file from the memory folders (image, PDF, audio, video, text)
  reader  {url, text, image?, site?}              a web page's words, read inside Alfred
  image   {src}                                   a picture from the web (https) or the memory folders
  video   {src}                                   a YouTube video (privacy-enhanced embed only)
  timer   {ends_at | started_at}                  a live countdown or count-up (epoch milliseconds)
Other modules can add kinds: screen.EXTRA_KINDS.add("gallery") plus a renderer in a frontend file,
window.jarvisPopupKinds.gallery = (card, body, {el, ask}) => {...}; their card holds its own plain JSON in "data".
Every card has an id (showing the same id again updates that window), a title, and optional buttons
[{label, say}] that send say to Alfred as if the user had said it, or [{label, download}] that download a
memory-folder file (download is a /screen/file?path=... address).
"""

import html
import json
import mimetypes
import re
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import httpx

import memory
from config import Settings

MAX_TEXT = 20000
MAX_ITEMS = 200
MAX_ROWS = 200
MAX_READ_BYTES = 3 * 1024 * 1024
KINDS = {"text", "list", "table", "chart", "file", "reader", "image", "video", "timer"}
# Kinds that other modules add, each drawn by its own renderer in frontend (window.jarvisPopupKinds[kind]).
# Their card carries a free-form "data" field of plain JSON.
EXTRA_KINDS: set[str] = set()
MAX_DATA = 200_000
# Files the page may show inline, by suffix; anything else is offered to open on the PC instead.
INLINE = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
    ".bmp": "image/bmp", ".svg": "image/svg+xml", ".pdf": "application/pdf",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4", ".flac": "audio/flac",
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
    ".txt": "text/plain", ".md": "text/markdown", ".csv": "text/csv", ".json": "application/json", ".log": "text/plain",
}
YOUTUBE = re.compile(r"^(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/|embed/)|youtu\.be/)([\w-]{11})")


class Shown(str):
    """A tool result Alfred speaks from, which also pops a card up on the screen."""

    card: dict

    def __new__(cls, text: str, card: dict):
        obj = super().__new__(cls, text)
        obj.card = card
        return obj


def _clip(value, limit: int = 300) -> str:
    return str(value if value is not None else "")[:limit]


def _buttons(buttons) -> list[dict]:
    """[{label, say}] buttons that talk to Alfred, or [{label, download}] ones that download a file from this page."""
    out = []
    for b in (buttons or [])[:6]:
        if not isinstance(b, dict) or not b.get("label"):
            continue
        if b.get("say"):
            out.append({"label": _clip(b["label"], 40), "say": _clip(b["say"], 300)})
        elif str(b.get("download", "")).startswith("/screen/file?"):
            out.append({"label": _clip(b["label"], 40), "download": _clip(b["download"], 600)})
    return out


def card(kind: str, title: str, card_id: str = "", buttons=None, **fields) -> dict:
    """A checked card: known kind, sizes capped, only plain data."""
    if kind not in KINDS | EXTRA_KINDS:
        raise ValueError(f"Unknown pop-up kind {kind}.")
    out = {"kind": kind, "title": _clip(title, 80) or kind.title(), "id": _clip(card_id, 60) or _auto_id(kind, title),
           "buttons": _buttons(buttons)}
    if "text" in fields:
        out["text"] = _clip(fields["text"], MAX_TEXT)
    if kind == "list":
        out["items"] = [{"label": _clip(i.get("label") if isinstance(i, dict) else i, 200),
                         "done": bool(i.get("done")) if isinstance(i, dict) else False,
                         "say": _clip(i.get("say"), 300) if isinstance(i, dict) else ""}
                        for i in (fields.get("items") or [])[:MAX_ITEMS]]
    if kind == "table":
        columns = [_clip(c, 60) for c in (fields.get("columns") or [])[:8]]
        out["columns"] = columns
        out["rows"] = [[_clip(c, 200) for c in list(r)[:8]] for r in (fields.get("rows") or [])[:MAX_ROWS]]
    if kind == "chart":
        chart = fields.get("chart") or {}
        labels = [_clip(x, 30) for x in (chart.get("labels") or [])[:60]]
        values = [float(v) for v in (chart.get("values") or [])[:60]]
        if len(labels) != len(values):
            raise ValueError("A chart needs one label per value.")
        out["chart"] = {"type": "line" if chart.get("type") == "line" else "bar", "labels": labels, "values": values,
                        "unit": _clip(chart.get("unit"), 12)}
    for key in ("src", "mime", "name", "url", "image", "site"):
        if fields.get(key):
            out[key] = _clip(fields[key], 2000)
    if "data" in fields:
        if len(json.dumps(fields["data"])) > MAX_DATA:
            raise ValueError("That's too much to show in one window.")
        out["data"] = fields["data"]
    if fields.get("checks"):
        out["checks"] = True
    for key in ("ends_at", "started_at"):
        if fields.get(key) is not None:
            out[key] = int(fields[key])
    return out


def _auto_id(kind: str, title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", f"{kind}-{title}".lower()).strip("-")[:60]


def memory_path(settings: Settings, relative: str) -> Path:
    """A file under the memory folder from a path like "Work/Payslips/june.pdf", or ValueError."""
    base = memory.root(settings).resolve()
    parts = [p for p in re.split(r"[/\\]", str(relative)) if p.strip()]
    if not parts or any(p in (".", "..") or p.startswith(".") for p in parts):
        raise ValueError("That isn't a file in the memory folders.")
    path = base.joinpath(*parts).resolve()
    if base not in path.parents or not path.is_file():
        raise ValueError(f"There's no file called {parts[-1]} in the memory folders.")
    return path


def find_file(settings: Settings, folder: str, filename: str) -> Path:
    """A file by folder and name (any case; a close name is fine), searching folders inside that folder too."""
    base = memory.root(settings).resolve()
    top = memory.folder(settings, folder).resolve() if folder else base
    want = filename.strip().lower()
    files = [p for p in top.rglob("*") if p.is_file() and not any(q.startswith(".") for q in p.relative_to(base).parts)]
    for match in (lambda p: p.name.lower() == want, lambda p: p.stem.lower() == want,
                  lambda p: want in p.name.lower()):
        found = [p for p in files if match(p)]
        if found:
            return max(found, key=lambda p: p.stat().st_mtime)
    raise ValueError(f"I can't find {filename} in {top.name if folder else 'the memory folders'}.")


def file_card(settings: Settings, path: Path, buttons=None) -> dict:
    rel = path.resolve().relative_to(memory.root(settings).resolve()).as_posix()
    mime = INLINE.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    extra = [{"label": "Open on PC", "say": f"Open the file {path.name} from {path.parent.name} on my PC."}]
    return card("file", path.name, f"file-{rel}", buttons=(buttons or []) + extra,
                src=f"/screen/file?path={quote(rel)}", mime=mime, name=path.name)


def show_file(settings: Settings, folder: str, filename: str) -> Shown:
    path = find_file(settings, folder, filename)
    return Shown(f"Showing {path.name} on the screen.", file_card(settings, path))


def inline_type(path: Path) -> str | None:
    return INLINE.get(path.suffix.lower())


# ---- Web pages read inside Alfred ----------------------------------------------------------

def page_text(markup: str) -> tuple[str, str, str]:
    """(title, readable text, lead image URL) from a web page's HTML, without running anything."""
    title = re.search(r"<title[^>]*>(.*?)</title>", markup, re.S | re.I)
    image = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', markup, re.I)
    body = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header|form|aside)\b.*?</\1>", " ", markup)
    main = re.search(r"(?is)<(article|main)\b.*?</\1>", body)
    body = main.group(0) if main else body
    body = re.sub(r"(?i)<br\s*/?>|</(p|div|h[1-6]|li|tr|section|article)>", "\n", body)
    body = re.sub(r"(?i)<li[^>]*>", "\n• ", body)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines()]
    paragraphs = [line for line in lines if len(line) > 30 or line.startswith("• ")]
    return (html.unescape(title.group(1).strip()) if title else "",
            "\n\n".join(paragraphs)[:MAX_TEXT], image.group(1) if image else "")


async def read_page(http: httpx.AsyncClient, url: str) -> Shown:
    if not re.match(r"^https?://", url):
        url = "https://" + url
    for _ in range(5):
        await memory.check_public(url)
        r = await http.get(url, follow_redirects=False, timeout=15, headers={"User-Agent": "Mozilla/5.0 Alfred-assistant"})
        if r.is_redirect:
            url = urljoin(url, r.headers["location"])
            continue
        break
    if r.status_code != 200:
        raise ValueError(f"The page answered {r.status_code}.")
    if "html" not in r.headers.get("content-type", "html"):
        raise ValueError("That link isn't a web page; I can download it into a folder and show it instead.")
    title, text, image = page_text(r.text[:MAX_READ_BYTES])
    if not text:
        raise ValueError("I couldn't find any readable words on that page.")
    image = urljoin(url, image) if image else ""
    site = urlparse(url).hostname or ""
    shown = card("reader", title or site, f"page-{url}", url=url, text=text, site=site,
                 image=image if image.startswith("https://") else "",
                 buttons=[{"label": "Summarise", "say": f"Summarise the page {url} for me."},
                          {"label": "Save to Ideas", "say": f"Save the main points of {url} into my Ideas folder."}])
    return Shown(f"Showing '{title or site}' on the screen. Here's the start of it:\n{text[:3000]}", shown)


# ---- The show_on_screen tool -----------------------------------------------------------------

def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "show_on_screen",
        "description": "Pop a window up on the Alfred screen (never the web browser) when the user asks to see, "
                       "show or open something here. kind: 'file' shows a file from the memory folders (pictures, "
                       "PDFs, music, videos, notes); 'web_page' reads a web page inside Alfred; 'image' shows a "
                       "picture from an https link; 'video' plays a YouTube link; 'text', 'list', 'table' or "
                       "'chart' show what you write; 'close' closes one window by title, or all. Buttons and list "
                       "items can carry a 'say' line: clicking one sends that line to you as the user's request.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["file", "web_page", "image", "video", "text", "list", "table",
                                                    "chart", "close"]},
                "title": {"type": "string"},
                "folder": {"type": "string", "description": "file: memory folder, e.g. 'Work' or 'Work/Payslips'."},
                "filename": {"type": "string", "description": "file: its name, or part of it."},
                "url": {"type": "string", "description": "web_page, image or video link."},
                "text": {"type": "string"},
                "items": {"type": "array", "items": {"type": "object", "properties": {
                    "label": {"type": "string"}, "done": {"type": "boolean"}, "say": {"type": "string"}},
                    "required": ["label"], "additionalProperties": False}},
                "columns": listed,
                "rows": {"type": "array", "items": listed},
                "chart_type": {"type": "string", "enum": ["bar", "line"]},
                "labels": listed,
                "values": {"type": "array", "items": {"type": "number"}},
                "unit": {"type": "string"},
                "buttons": {"type": "array", "items": {"type": "object", "properties": {
                    "label": {"type": "string"}, "say": {"type": "string"}},
                    "required": ["label", "say"], "additionalProperties": False}},
                "all": {"type": "boolean", "description": "close: close every window."},
            },
            "required": ["kind"],
            "additionalProperties": False,
        },
    }]


NAMES = {"show_on_screen"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    kind = args.get("kind")
    title = args.get("title") or ""
    buttons = args.get("buttons")
    if kind == "close":
        return Shown("Closed." if args.get("all") else f"Closed {title}.",
                     {"kind": "close", "all": bool(args.get("all")), "title": _clip(title, 80)})
    if kind == "file":
        return show_file(settings, args.get("folder") or "", args.get("filename") or "")
    if kind == "web_page":
        return await read_page(http, args.get("url") or "")
    if kind == "image":
        url = args.get("url") or ""
        if not url.startswith("https://"):
            raise ValueError("I can only show pictures from https links.")
        return Shown("Showing the picture.", card("image", title or "Picture", src=url, buttons=buttons))
    if kind == "video":
        m = YOUTUBE.match(args.get("url") or "")
        if not m:
            raise ValueError("I can only play YouTube links on the screen.")
        return Shown("Playing it on the screen.", card(
            "video", title or "Video", f"video-{m.group(1)}", src=f"https://www.youtube-nocookie.com/embed/{m.group(1)}",
            buttons=buttons))
    if kind == "chart":
        c = card("chart", title, buttons=buttons, chart={"type": args.get("chart_type"), "labels": args.get("labels"),
                                                         "values": args.get("values"), "unit": args.get("unit")})
    elif kind == "table":
        c = card("table", title, buttons=buttons, columns=args.get("columns"), rows=args.get("rows"))
    elif kind == "list":
        c = card("list", title, buttons=buttons, items=args.get("items"))
    else:
        c = card("text", title, buttons=buttons, text=args.get("text") or "")
    return Shown(f"It's on the screen: {c['title']}.", c)
