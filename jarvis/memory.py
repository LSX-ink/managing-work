"""Memory folders: the parts of the HUD brain. Each one is a real folder on this PC holding notes and files.

folders.json keeps the folder names in brain order (front of the brain first), so renaming one keeps its place.
"""

import asyncio
import ipaddress
import json
import re
import socket
from email.message import Message
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx

from config import Settings

DEFAULT_FOLDERS = ["Ideas", "Work", "Music", "Personal", "Shopping", "Reminders"]
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
MAX_REDIRECTS = 5
READ_LIMIT = 6000  # characters of notes Alfred reads back from one folder
TEXT_TYPES = {".txt", ".md"}


def root(settings: Settings) -> Path:
    return Path(settings.memory_dir)


def safe_name(name: str, what: str = "name") -> str:
    """A name that is safe as one Windows file or folder name, or ValueError."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(name)).strip().strip(".").strip()
    if not name:
        raise ValueError(f"That {what} is empty or only has characters Windows can't use.")
    if len(name) > 60:
        raise ValueError(f"That {what} is too long; keep it under 60 characters.")
    if name.upper().split(".")[0] in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        raise ValueError(f"Windows doesn't allow {name} as a {what}.")
    return name


def names(settings: Settings) -> list[str]:
    """Folder names in brain order, creating the default folders the first time."""
    base = root(settings)
    index = base / "folders.json"
    try:
        found = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = []
    if not isinstance(found, list) or len(found) != len(DEFAULT_FOLDERS):
        found = DEFAULT_FOLDERS
    for name in found:
        (base / name).mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps(found, indent=2), encoding="utf-8")
    return list(found)


def folder(settings: Settings, which: int | str) -> Path:
    """A folder by its brain position (0 to 5) or by name (any case)."""
    all_names = names(settings)
    if isinstance(which, int):
        i = which
        if not 0 <= i < len(all_names):
            raise ValueError("There is no such folder.")
        return root(settings) / all_names[i]
    for name in all_names:
        if name.lower() == str(which).strip().lower():
            return root(settings) / name
    raise ValueError(f"There is no folder called {which}. The folders are: {', '.join(all_names)}.")


def items(path: Path) -> list[dict]:
    files = sorted((p for p in path.iterdir() if p.is_file()), key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "size": p.stat().st_size} for p in files]


def listing(settings: Settings) -> list[dict]:
    return [{"name": name, "items": items(root(settings) / name)} for name in names(settings)]


def rename(settings: Settings, which: int | str, new_name: str) -> str:
    old = folder(settings, which)
    new_name = safe_name(new_name, "folder name")
    all_names = names(settings)
    if new_name.lower() != old.name.lower() and any(n.lower() == new_name.lower() for n in all_names):
        raise ValueError(f"There is already a folder called {new_name}.")
    old.rename(old.with_name(new_name))
    all_names[all_names.index(old.name)] = new_name
    (root(settings) / "folders.json").write_text(json.dumps(all_names, indent=2), encoding="utf-8")
    return new_name


def unique_path(path: Path) -> Path:
    n = 2
    candidate = path
    while candidate.exists():
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        n += 1
    return candidate


def save_note(settings: Settings, which: int | str, title: str, text: str) -> Path:
    path = unique_path(folder(settings, which) / f"{safe_name(title, 'note title')}.txt")
    path.write_text(str(text), encoding="utf-8")
    return path


def save_file(settings: Settings, which: int | str, filename: str, data: bytes) -> Path:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("That file is too big; the limit is 20 MB.")
    path = unique_path(folder(settings, which) / safe_name(filename, "file name"))
    path.write_bytes(data)
    return path


# ---- downloads ---------------------------------------------------------------------

async def check_public(url: str) -> None:
    """ValueError unless url is http(s) on a public internet address.

    Alfred reads web pages, and a page could try to steer him into fetching things from this PC or the home
    network (the router, other devices), so only public addresses are allowed.
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("I can only download http or https links.")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"I couldn't find {parsed.hostname}.") from None
    for info in infos:
        if not ipaddress.ip_address(info[4][0].split("%")[0]).is_global:
            raise ValueError("That link points at this PC or your home network, so I won't download it.")


def download_name(url: str, response: httpx.Response) -> str:
    """The file name the server suggests, else the last part of the link."""
    header = response.headers.get("content-disposition", "")
    if header:
        msg = Message()
        msg["content-disposition"] = header
        if name := msg.get_filename():
            return name
    return unquote(urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]) or "download"


async def download(settings: Settings, http: httpx.AsyncClient, which: int | str, url: str, filename: str = "") -> Path:
    """Download a link into a memory folder, up to MAX_DOWNLOAD_BYTES. Returns where it was saved."""
    target = folder(settings, which)
    for _ in range(MAX_REDIRECTS + 1):
        await check_public(url)  # again after every redirect
        async with http.stream("GET", url, follow_redirects=False, timeout=60) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers["location"])
                continue
            if response.status_code != 200:
                raise ValueError(f"The download failed: the site answered {response.status_code}.")
            length = response.headers.get("content-length", "")
            if length.isdigit() and int(length) > MAX_DOWNLOAD_BYTES:
                raise ValueError("That file is too big; the limit is 200 MB.")
            name = filename.strip() or download_name(url, response)
            if "." not in name and "." in download_name(url, response):
                name += "." + download_name(url, response).rsplit(".", 1)[-1]
            name = safe_name(name[-60:], "file name")
            path = unique_path(target / name)
            part = path.with_name(path.name + ".part")
            size = 0
            try:
                with part.open("wb") as out:
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_DOWNLOAD_BYTES:
                            raise ValueError("That file is too big; the limit is 200 MB.")
                        out.write(chunk)
                part.replace(path)
            finally:
                part.unlink(missing_ok=True)
            return path
    raise ValueError("That link redirected too many times.")


def file_path(settings: Settings, which: int | str, filename: str) -> Path:
    path = folder(settings, which) / safe_name(filename, "file name")
    if not path.is_file():
        raise ValueError("That file isn't in this folder.")
    return path


def delete_file(settings: Settings, which: int | str, filename: str) -> None:
    file_path(settings, which, filename).unlink()


def read(settings: Settings, which: int | str | None = None) -> str:
    """Text for Alfred: every folder with its contents, or one folder with its notes read out."""
    if not which:
        lines = []
        for entry in listing(settings):
            files = ", ".join(i["name"] for i in entry["items"]) or "empty"
            lines.append(f"{entry['name']}: {files}")
        return "Memory folders:\n" + "\n".join(lines)
    path = folder(settings, which)
    parts, used = [], 0
    for item in items(path):
        p = path / item["name"]
        if p.suffix.lower() in TEXT_TYPES and used < READ_LIMIT:
            body = p.read_text(encoding="utf-8", errors="replace")[: READ_LIMIT - used]
            used += len(body)
            parts.append(f"--- {p.name} ---\n{body}")
        else:
            parts.append(f"--- {p.name} (file, {item['size']} bytes) ---")
    return f"Folder {path.name}:\n" + ("\n".join(parts) if parts else "(empty)")


def tool_definitions() -> list[dict]:
    return [
        {
            "name": "save_to_memory",
            "description": "Save a note into one of the user's memory folders (the parts of the brain on their HUD). "
                           "Use it when they ask you to remember, note down or save something. Call read_memory "
                           "first if you don't know the folder names.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder name, e.g. 'Ideas'."},
                    "title": {"type": "string", "description": "Short title for the note; becomes its file name."},
                    "text": {"type": "string", "description": "What to save."},
                },
                "required": ["folder", "title", "text"],
                "additionalProperties": False,
            },
        },
        {
            "name": "read_memory",
            "description": "Read the user's memory folders. Without a folder, lists every folder and what is in it; "
                           "with a folder, reads its notes.",
            "input_schema": {
                "type": "object",
                "properties": {"folder": {"type": "string", "description": "Folder name. Leave out to list them all."}},
                "additionalProperties": False,
            },
        },
        {
            "name": "download_file",
            "description": "Download a file from a web link and store it in one of the user's memory folders "
                           "(PDFs, pictures, music, documents; up to 200 MB). Use it when they ask you to download, "
                           "grab or save a file from the internet. Call read_memory first if you don't know the "
                           "folder names.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full http(s) link to the file."},
                    "folder": {"type": "string", "description": "Folder name to store it in, e.g. 'Work'."},
                    "filename": {"type": "string", "description": "Optional name to save it as. Leave out to "
                                                                  "keep the file's own name."},
                },
                "required": ["url", "folder"],
                "additionalProperties": False,
            },
        },
    ]


def run_tool(name: str, args: dict, settings: Settings) -> str:
    if name == "save_to_memory":
        path = save_note(settings, args["folder"], args["title"], args["text"])
        return f"Saved as {path.name} in the {path.parent.name} folder."
    return read(settings, args.get("folder"))
