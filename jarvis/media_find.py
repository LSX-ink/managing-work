"""Finding files in the memory folders: newest files, search by name, duplicates, folder sizes, file info, photo EXIF."""

import hashlib
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image

import media_common as mc
import screen
from config import Settings

RECENT = 20
MAX_FOUND = 50
PDF_SCAN_BYTES = 50 * 1024 * 1024
EXIF_IFD, DATE_TAKEN, DATE_CHANGED, MAKE, MODEL = 0x8769, 0x9003, 0x0132, 0x010F, 0x0110


def _listed(settings: Settings, paths: list[Path], title: str, card_id: str) -> dict:
    items = [{"label": f"{p.name} · {Path(mc.rel(settings, p)).parent.as_posix()} · {mc.when(p.stat().st_mtime)}",
              "say": mc.show_line(settings, p)} for p in paths]
    return screen.card("list", title, card_id, items=items)


def recent(settings: Settings) -> screen.Shown:
    newest = sorted(mc.all_files(settings), key=lambda p: p.stat().st_mtime, reverse=True)[:RECENT]
    if not newest:
        return screen.Shown("There are no files in the memory folders yet.", screen.card("list", "Recent files", "media-recent"))
    return screen.Shown(f"The newest is {newest[0].name}; here are the latest {len(newest)}.",
                        _listed(settings, newest, "Recent files", "media-recent"))


def search(settings: Settings, query: str) -> screen.Shown:
    words = [w for w in re.split(r"\s+", str(query or "").lower()) if w]
    if not words:
        raise ValueError("What should the file name contain?")
    found = sorted((p for p in mc.all_files(settings) if all(w in p.name.lower() for w in words)),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    c = _listed(settings, found[:MAX_FOUND], f"Files named {query}", "media-search")
    if not found:
        return screen.Shown(f"No file names contain {query}.", c)
    return screen.Shown(f"Found {len(found)} file{'s' if len(found) != 1 else ''} named like {query}.", c)


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def duplicates(settings: Settings) -> screen.Shown:
    by_size = defaultdict(list)
    for p in mc.all_files(settings):
        by_size[p.stat().st_size].append(p)
    groups = defaultdict(list)
    for size, paths in by_size.items():
        if len(paths) > 1 and size:
            for p in paths:
                groups[(size, _digest(p))].append(p)
    sets = [sorted(g, key=lambda p: mc.rel(settings, p)) for g in groups.values() if len(g) > 1]
    wasted = sum(p.stat().st_size * (len(g) - 1) for g in sets for p in g[:1])
    items = [{"label": f"Set {n}: {mc.rel(settings, p)} ({mc.human_size(p.stat().st_size)})",
              "say": mc.show_line(settings, p)} for n, g in enumerate(sets, 1) for p in g]
    c = screen.card("list", "Duplicate files", "media-duplicates", items=items)
    if not sets:
        return screen.Shown("No duplicate files in the memory folders.", c)
    return screen.Shown(f"Found {len(sets)} set{'s' if len(sets) != 1 else ''} of duplicates, "
                        f"wasting {mc.human_size(wasted)}.", c)


def folder_sizes(settings: Settings) -> screen.Shown:
    top = mc.base(settings)
    sizes = {d.name: sum(p.stat().st_size for p in mc.all_files(settings, d))
             for d in sorted(top.iterdir(), key=lambda d: d.name.lower()) if d.is_dir() and not d.name.startswith(".")}
    total = sum(sizes.values())
    c = screen.card("chart", "Folder sizes", "media-folder-sizes",
                    chart={"type": "bar", "labels": list(sizes), "unit": " MB",
                           "values": [round(v / 1024 / 1024, 2) for v in sizes.values()]})
    biggest = max(sizes, key=sizes.get) if sizes else ""
    return screen.Shown(f"The memory folders use {mc.human_size(total)}; {biggest} is the biggest.", c)


def pdf_pages(path: Path) -> int | None:
    if path.stat().st_size > PDF_SCAN_BYTES:
        return None
    return len(re.findall(rb"/Type\s*/Page(?![a-zA-Z])", path.read_bytes())) or None


def info(settings: Settings, folder: str, filename: str) -> screen.Shown:
    path = mc.user_file(settings, folder, filename)
    st = path.stat()
    rows = [["Name", path.name], ["Folder", Path(mc.rel(settings, path)).parent.as_posix()],
            ["Type", screen.inline_type(path) or path.suffix.lstrip(".").upper() or "unknown"],
            ["Size", mc.human_size(st.st_size)], ["Changed", mc.when(st.st_mtime)], ["Created", mc.when(st.st_ctime)]]
    spoken = f"{path.name} is {mc.human_size(st.st_size)}"
    if path.suffix.lower() in mc.PICTURES:
        try:
            with Image.open(path) as im:
                rows.append(["Picture", f"{im.width} × {im.height} pixels"])
                spoken += f", {im.width} by {im.height} pixels"
        except (OSError, Image.DecompressionBombError):
            pass
    if path.suffix.lower() == ".pdf" and (pages := pdf_pages(path)):
        rows.append(["Pages", str(pages)])
        spoken += f", {pages} page{'s' if pages != 1 else ''}"
    c = screen.card("table", f"{path.name} info", f"info-{mc.rel(settings, path)}", columns=["", ""], rows=rows,
                    buttons=[{"label": "Show it", "say": mc.show_line(settings, path)}])
    return screen.Shown(spoken + ".", c)


def exif(settings: Settings, folder: str, filename: str) -> screen.Shown:
    path = mc.user_file(settings, folder, filename)
    try:
        with Image.open(path) as im:
            tags = im.getexif()
            inner = tags.get_ifd(EXIF_IFD)
    except (OSError, Image.DecompressionBombError):
        raise ValueError(f"I can't read {path.name} as a photo.")
    taken = str(inner.get(DATE_TAKEN) or tags.get(DATE_CHANGED) or "").strip()
    camera = " ".join(str(tags.get(t) or "").strip("\x00 ") for t in (MAKE, MODEL)).strip()
    if taken[:10].count(":") == 2:
        taken = taken[:10].replace(":", "-") + taken[10:]
    rows = [["Taken", taken or "not recorded"], ["Camera", camera or "not recorded"]]
    c = screen.card("table", f"{path.name} photo details", f"exif-{mc.rel(settings, path)}", columns=["", ""],
                    rows=rows, buttons=[{"label": "Show it", "say": mc.show_line(settings, path)}])
    if not taken and not camera:
        return screen.Shown(f"{path.name} has no date or camera saved in it.", c)
    return screen.Shown(f"{path.name} was taken {taken or 'on an unknown date'}"
                        f"{' with ' + camera if camera else ''}.", c)


def tool_definitions() -> list[dict]:
    return [{
        "name": "find_memory_files",
        "description": "Look through the files in the memory folders, shown in a pop-up. action 'recent' the 20 "
                       "newest files; 'search' files whose name contains words; 'duplicates' identical files; "
                       "'folder_sizes' how much space each folder uses; 'info' a file's size, type, dates, picture "
                       "size or PDF pages; 'exif' when a photo was taken and with which camera.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["recent", "search", "duplicates", "folder_sizes", "info", "exif"]},
                "query": {"type": "string", "description": "search: words in the file name."},
                "folder": {"type": "string", "description": "info/exif: memory folder, e.g. 'Personal'."},
                "filename": {"type": "string", "description": "info/exif: the file's name or part of it."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"find_memory_files"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> screen.Shown:
    action = args.get("action")
    if action == "recent":
        return recent(settings)
    if action == "search":
        return search(settings, args.get("query") or "")
    if action == "duplicates":
        return duplicates(settings)
    if action == "folder_sizes":
        return folder_sizes(settings)
    if action in ("info", "exif"):
        return (info if action == "info" else exif)(settings, args.get("folder") or "", args.get("filename") or "")
    raise ValueError("Pick recent, search, duplicates, folder_sizes, info or exif.")
