"""Shared helpers for the files-and-media abilities: finding files in the memory folders and naming them.

Everything stays inside memory.root(settings): folders come from memory.folder, files from screen.find_file.
Files lying loose in the memory root (folders.json, email-rules.json, ...) are Alfred's own and are left alone.
"""

from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import memory
import screen
from config import Settings

PICTURES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
AUDIO = {s for s, m in screen.INLINE.items() if m.startswith("audio/")}
VIDEO = {s for s, m in screen.INLINE.items() if m.startswith("video/")}
MAX_LISTED = 300


def base(settings: Settings) -> Path:
    return memory.root(settings).resolve()


def rel(settings: Settings, path: Path) -> str:
    return path.resolve().relative_to(base(settings)).as_posix()


def src(settings: Settings, path: Path) -> str:
    return f"/screen/file?path={quote(rel(settings, path))}"


def visible(settings: Settings, path: Path) -> bool:
    parts = path.resolve().relative_to(base(settings)).parts
    return len(parts) > 1 and not any(p.startswith(".") for p in parts)


def all_files(settings: Settings, top: Path | None = None) -> list[Path]:
    """Every user file under top (default: all the memory folders), skipping hidden ones and Alfred's own."""
    root = base(settings)
    root.mkdir(parents=True, exist_ok=True)
    return [p for p in (top or root).rglob("*") if p.is_file() and not p.is_symlink()
            and len(parts := p.relative_to(root).parts) > 1 and not any(q.startswith(".") for q in parts)]


def folder(settings: Settings, name: str) -> Path:
    if not str(name or "").strip():
        raise ValueError("Which memory folder? For example Ideas or Personal/Holiday.")
    path = memory.folder(settings, name).resolve()
    if path != base(settings) and base(settings) not in path.parents:
        raise ValueError("That isn't one of the memory folders.")
    return path


def files_in(settings: Settings, name: str, suffixes: set[str]) -> list[Path]:
    """Files of the given kinds directly inside a memory folder, by name."""
    top = folder(settings, name)
    found = sorted((p for p in top.iterdir() if p.is_file() and p.suffix.lower() in suffixes
                    and not p.name.startswith(".")), key=lambda p: p.name.lower())
    return found[:MAX_LISTED]


def user_file(settings: Settings, folder_name: str, filename: str) -> Path:
    """A file the user may change: found by name, inside a memory folder, never one of Alfred's own."""
    if not str(filename or "").strip():
        raise ValueError("Which file?")
    path = screen.find_file(settings, folder_name or "", filename).resolve()
    if not visible(settings, path):
        raise ValueError(f"{path.name} is one of Alfred's own files, so I'll leave it alone.")
    return path


def human_size(n: float) -> str:
    for unit in ("bytes", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "bytes" else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def when(stamp: float) -> str:
    return datetime.fromtimestamp(stamp).strftime("%d %b %Y %H:%M")


def show_line(settings: Settings, path: Path) -> str:
    return f"Show me the file {path.name} from folder {Path(rel(settings, path)).parent.as_posix()}"


def item(settings: Settings, path: Path) -> dict:
    return {"name": path.name, "src": src(settings, path), "mime": screen.inline_type(path) or "", "rel": rel(settings, path)}
