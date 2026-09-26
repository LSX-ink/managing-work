"""Everyday PC control: open apps and folders, media and volume keys, find and read files.

Nothing here deletes or changes files. File access is limited to the user's home folder,
and obvious secrets (.env, keys, password stores) are refused.
"""

import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

WINDOWS = sys.platform == "win32"
MAC = sys.platform == "darwin"

MEDIA_ACTIONS = ["play_pause", "next_track", "previous_track", "volume_up", "volume_down", "mute", "lock_screen"]

KNOWN_FOLDERS = {
    "home": "", "desktop": "Desktop", "documents": "Documents", "downloads": "Downloads",
    "pictures": "Pictures", "photos": "Pictures", "music": "Music", "videos": "Videos",
}

# File types open_file will hand to their default app. Programs and scripts are never opened.
OPENABLE = {
    ".txt", ".md", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".odt", ".ods",
    ".rtf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".mp3", ".wav", ".m4a", ".flac",
    ".mp4", ".mkv", ".mov", ".avi", ".webm",
}

SKIP_DIRS = {"node_modules", "__pycache__", ".venv", "venv", "site-packages", "AppData", "Library", ".git"}
SECRET_NAME = re.compile(
    r"(^\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|\.kdbx$|^id_(rsa|ed25519|ecdsa)|password|credential|secret|token)",
    re.IGNORECASE,
)
SECRET_DIRS = {".ssh", ".aws", ".gnupg", ".azure", ".kube", ".docker", "AppData", "Library"}
MAX_READ_CHARS = 20_000


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "open_app",
            "description": "Open an installed app on the user's computer by name, e.g. 'Spotify', 'Notepad', 'WhatsApp'.",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
                "additionalProperties": False,
            },
        },
        {
            "name": "open_folder",
            "description": "Open a folder in the file manager: home, desktop, documents, downloads, pictures, music, "
                           "videos, or a folder path inside the user's home folder.",
            "input_schema": {
                "type": "object",
                "properties": {"folder": {"type": "string"}},
                "required": ["folder"],
                "additionalProperties": False,
            },
        },
        {
            "name": "media_control",
            "description": "Control media playback and volume, or lock the screen.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": MEDIA_ACTIONS},
                    "times": {"type": "integer", "minimum": 1, "maximum": 20,
                              "description": "Repeat count, for volume steps (each about 2%)."},
                },
                "required": ["action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "find_files",
            "description": "Search the user's Desktop, Documents, Downloads, Pictures, Music and Videos for files "
                           "whose names contain all the given words. Returns full paths.",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "read_file",
            "description": "Read a text or Word (.docx) file from the user's home folder. Read-only.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "name": "open_file",
            "description": "Open a document, picture, song or video from the user's home folder in its default app.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    ]


# ---- apps -------------------------------------------------------------------

_app_cache: list[tuple[str, str]] | None = None


def installed_apps() -> list[tuple[str, str]]:
    """(display name, launch target) for installed apps, cached after the first call."""
    global _app_cache
    if _app_cache is not None:
        return _app_cache
    apps: list[tuple[str, str]] = []
    if WINDOWS:
        # Get-StartApps covers classic programs and Store apps (Spotify, WhatsApp, ...).
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
        data = json.loads(out) if out else []
        for item in data if isinstance(data, list) else [data]:
            apps.append((item["Name"], item["AppID"]))
    elif MAC:
        for folder in ("/Applications", "/System/Applications", str(Path.home() / "Applications")):
            for app in Path(folder).glob("*.app"):
                apps.append((app.stem, str(app)))
    else:
        for folder in ("/usr/share/applications", str(Path.home() / ".local/share/applications")):
            for desktop in Path(folder).glob("*.desktop"):
                name = next((l[5:].strip() for l in desktop.read_text(errors="ignore").splitlines()
                             if l.startswith("Name=")), desktop.stem)
                apps.append((name, desktop.stem))
    _app_cache = apps
    return apps


def match_app(query: str, apps: list[tuple[str, str]]) -> tuple[str, str] | None:
    q = query.casefold().strip()
    for test in (lambda n: n == q, lambda n: n.startswith(q), lambda n: q in n):
        hits = [a for a in apps if test(a[0].casefold())]
        if hits:
            return min(hits, key=lambda a: len(a[0]))
    return None


def open_app(name: str) -> str:
    apps = installed_apps()
    app = match_app(name, apps)
    if not app:
        words = name.casefold().split()
        close = [a[0] for a in apps if any(w in a[0].casefold() for w in words)][:5]
        return f"No app called {name!r}." + (f" Close matches: {', '.join(close)}." if close else "")
    display, target = app
    if WINDOWS:
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{target}"])
    elif MAC:
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["gtk-launch", target])
    return f"Opened {display}."


# ---- folders and files ------------------------------------------------------

def home() -> Path:
    return Path.home().resolve()


def inside_home(path: Path) -> bool:
    try:
        path.resolve().relative_to(home())
        return True
    except ValueError:
        return False


def is_secret(path: Path) -> bool:
    return bool(SECRET_NAME.search(path.name)) or any(part in SECRET_DIRS for part in path.parts)


def _launch(path: Path) -> None:
    if WINDOWS:
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif MAC:
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def resolve_folder(folder: str) -> Path | None:
    key = folder.casefold().strip().rstrip("/\\")
    if key in KNOWN_FOLDERS:
        candidates = [home() / KNOWN_FOLDERS[key], home() / "OneDrive" / KNOWN_FOLDERS[key]]
    else:
        raw = Path(folder).expanduser()
        candidates = [raw if raw.is_absolute() else home() / raw]
    for c in candidates:
        if c.is_dir() and inside_home(c):
            return c.resolve()
    return None


def open_folder(folder: str) -> str:
    path = resolve_folder(folder)
    if not path:
        return f"Couldn't find a folder called {folder!r} in the home folder."
    _launch(path)
    return f"Opened {path}."


def search_roots() -> list[Path]:
    names = ["Desktop", "Documents", "Downloads", "Pictures", "Music", "Videos"]
    roots = [home() / n for n in names] + [home() / "OneDrive" / n for n in names]
    return [r for r in roots if r.is_dir()]


def find_files(query: str, limit: int = 15, max_entries: int = 50_000, max_seconds: float = 8.0) -> list[str]:
    words = [w.casefold() for w in query.split() if w]
    if not words:
        return []
    found: list[str] = []
    seen = 0
    deadline = time.monotonic() + max_seconds
    for root in search_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
            for fname in filenames:
                seen += 1
                lower = fname.casefold()
                if all(w in lower for w in words) and not is_secret(Path(fname)):
                    found.append(str(Path(dirpath) / fname))
                    if len(found) >= limit:
                        return found
            if seen > max_entries or time.monotonic() > deadline:
                return found
    return found


def _checked_path(path_str: str) -> Path:
    path = Path(path_str).expanduser()
    if not path.is_absolute():
        path = home() / path
    path = path.resolve()
    if not inside_home(path):
        raise PermissionError("Only files inside the user's home folder are allowed.")
    if is_secret(path):
        raise PermissionError("That file looks like it holds passwords or keys, so I won't touch it.")
    if not path.is_file():
        raise FileNotFoundError(f"No file at {path}.")
    return path


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def read_file(path_str: str) -> str:
    path = _checked_path(path_str)
    if path.suffix.lower() == ".docx":
        text = docx_text(path)
    else:
        raw = path.read_bytes()[: MAX_READ_CHARS * 4]
        if b"\x00" in raw[:4096]:
            return f"{path.name} isn't a text file, so I can't read it."
        text = raw.decode("utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n[…truncated]"
    return f"Contents of {path}:\n{text}"


def open_file(path_str: str) -> str:
    path = _checked_path(path_str)
    if path.suffix.lower() not in OPENABLE:
        return f"I only open documents, pictures and media, not {path.suffix or 'files without an extension'}."
    _launch(path)
    return f"Opened {path.name}."


# ---- media ------------------------------------------------------------------

_WIN_KEYS = {"play_pause": 0xB3, "next_track": 0xB0, "previous_track": 0xB1,
             "volume_up": 0xAF, "volume_down": 0xAE, "mute": 0xAD}


def media_control(action: str, times: int = 1) -> str:
    if action not in MEDIA_ACTIONS:
        raise ValueError(f"Unknown media action: {action}")
    times = max(1, min(int(times), 20))
    if WINDOWS:
        import ctypes

        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        if action == "lock_screen":
            user32.LockWorkStation()
        else:
            vk = _WIN_KEYS[action]
            for _ in range(times):
                user32.keybd_event(vk, 0, 0, 0)
                user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP
    elif MAC:
        scripts = {
            "volume_up": f"set volume output volume ((output volume of (get volume settings)) + {6 * times})",
            "volume_down": f"set volume output volume ((output volume of (get volume settings)) - {6 * times})",
            "mute": "set volume output muted (not (output muted of (get volume settings)))",
            "play_pause": 'tell application "Music" to playpause',
            "next_track": 'tell application "Music" to next track',
            "previous_track": 'tell application "Music" to previous track',
        }
        if action == "lock_screen":
            subprocess.run(["pmset", "displaysleepnow"], check=False)
        else:
            subprocess.run(["osascript", "-e", scripts[action]], check=False)
    else:
        commands = {
            "play_pause": ["playerctl", "play-pause"], "next_track": ["playerctl", "next"],
            "previous_track": ["playerctl", "previous"],
            "volume_up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{2 * times}%"],
            "volume_down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{2 * times}%"],
            "mute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
            "lock_screen": ["loginctl", "lock-session"],
        }
        subprocess.run(commands[action], check=False)
    return "Done."


def run(name: str, args: dict) -> str:
    """Dispatch one PC tool call (blocking; call from a worker thread)."""
    if name == "open_app":
        return open_app(args["name"])
    if name == "open_folder":
        return open_folder(args["folder"])
    if name == "media_control":
        return media_control(args["action"], args.get("times", 1))
    if name == "find_files":
        hits = find_files(args["query"])
        return "\n".join(hits) if hits else "No matching files."
    if name == "read_file":
        return read_file(args["path"])
    if name == "open_file":
        return open_file(args["path"])
    raise ValueError(f"Unknown tool: {name}")


NAMES = {t["name"] for t in tool_definitions()}
