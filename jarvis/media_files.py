"""Tidying files in the memory folders: rename, move, copy, delete, and zip / unzip folders.

Nothing leaves memory.root(settings). Unzipping refuses paths that climb out of the new folder (zip-slip) and
archives that would unpack to more than 500 MB or 2000 files (zip bombs).
"""

import re
import shutil
import zipfile
from pathlib import Path

import media_common as mc
import memory
import screen
from config import Settings

MAX_UNZIP_BYTES = 500 * 1024 * 1024
MAX_UNZIP_FILES = 2000
BAD_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


def rename(settings: Settings, folder: str, filename: str, new_name: str) -> screen.Shown:
    path = mc.user_file(settings, folder, filename)
    new_name = memory.safe_name(new_name, "file name")
    if not Path(new_name).suffix and path.suffix:
        new_name += path.suffix
    target = path.with_name(new_name)
    if target.exists() and target.name.lower() != path.name.lower():
        raise ValueError(f"There's already a file called {new_name} there.")
    path.rename(target)
    return screen.Shown(f"Renamed it to {target.name}.", screen.file_card(settings, target))


def move(settings: Settings, folder: str, filename: str, to_folder: str, copy: bool = False) -> screen.Shown:
    path = mc.user_file(settings, folder, filename)
    dest = mc.folder(settings, to_folder) if to_folder else path.parent
    target = memory.unique_path(dest / path.name)
    if copy:
        shutil.copy2(path, target)
    else:
        if dest == path.parent:
            raise ValueError(f"{path.name} is already in {dest.name}.")
        shutil.move(str(path), str(target))
    verb = "Copied" if copy else "Moved"
    return screen.Shown(f"{verb} {path.name} to {dest.name}{' as ' + target.name if target.name != path.name else ''}.",
                        screen.file_card(settings, target))


def delete(settings: Settings, folder: str, filename: str, confirmed: bool) -> str:
    path = mc.user_file(settings, folder, filename)
    if confirmed is not True:
        return f"Not deleted. Ask the user to confirm deleting {path.name} first, then call again with confirmed true."
    path.unlink()
    return f"Deleted {path.name} from {path.parent.name}."


def zip_folder(settings: Settings, folder: str) -> screen.Shown:
    top = mc.folder(settings, folder)
    files = mc.all_files(settings, top)
    if not files:
        raise ValueError(f"{top.name} has no files to zip.")
    if sum(p.stat().st_size for p in files) > MAX_UNZIP_BYTES:
        raise ValueError("That folder is over 500 MB, too big to zip here.")
    target = memory.unique_path(top / f"{top.name}.zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(top).as_posix())
    return screen.Shown(f"Zipped {len(files)} files into {target.name}, {mc.human_size(target.stat().st_size)}.",
                        contents_card(settings, target))


def _zip(settings: Settings, folder: str, filename: str) -> Path:
    path = mc.user_file(settings, folder, filename)
    if not zipfile.is_zipfile(path):
        raise ValueError(f"{path.name} isn't a zip file.")
    return path


def contents_card(settings: Settings, path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        rows = [[i.filename, mc.human_size(i.file_size)] for i in z.infolist() if not i.is_dir()]
    unzip_say = f"Unzip {path.name} from folder {Path(mc.rel(settings, path)).parent.as_posix()}"
    return screen.card("table", f"Inside {path.name}", f"zip-{mc.rel(settings, path)}", columns=["File", "Size"],
                       rows=rows, buttons=[{"label": "Unzip", "say": unzip_say}])


def zip_contents(settings: Settings, folder: str, filename: str) -> screen.Shown:
    path = _zip(settings, folder, filename)
    c = contents_card(settings, path)
    return screen.Shown(f"{path.name} holds {len(c['rows'])} files.", c)


def _member_parts(name: str) -> list[str]:
    if name.startswith(("/", "\\")) or re.match(r"^[a-zA-Z]:", name):
        raise ValueError("That zip tries to write outside its folder, so I didn't unzip it.")
    parts = [BAD_CHARS.sub("_", p).strip().rstrip(".") for p in re.split(r"[/\\]", name) if p.strip()]
    if any(p in ("", ".", "..") for p in parts) or ".." in re.split(r"[/\\]", name):
        raise ValueError("That zip tries to write outside its folder, so I didn't unzip it.")
    return parts


def unzip(settings: Settings, folder: str, filename: str) -> screen.Shown:
    path = _zip(settings, folder, filename)
    with zipfile.ZipFile(path) as z:
        members = [i for i in z.infolist() if not i.is_dir()]
        if len(members) > MAX_UNZIP_FILES:
            raise ValueError(f"That zip has {len(members)} files; the limit is {MAX_UNZIP_FILES}.")
        if sum(i.file_size for i in members) > MAX_UNZIP_BYTES:
            raise ValueError("That zip would unpack to over 500 MB, so I didn't unzip it.")
        plans = [(i, _member_parts(i.filename)) for i in members]
        target = memory.unique_path(path.with_name(memory.safe_name(path.stem, "folder name")))
        target.mkdir()
        try:
            written = 0
            for info, parts in plans:
                out = target.joinpath(*parts).resolve()
                if target.resolve() not in out.parents:
                    raise ValueError("That zip tries to write outside its folder, so I didn't unzip it.")
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, out.open("wb") as dst:
                    for block in iter(lambda: src.read(1 << 20), b""):
                        written += len(block)
                        if written > MAX_UNZIP_BYTES:
                            raise ValueError("That zip unpacks to over 500 MB, so I stopped.")
                        dst.write(block)
        except (ValueError, OSError, zipfile.BadZipFile):
            shutil.rmtree(target, ignore_errors=True)
            raise
    items = [{"label": "/".join(parts), "say": f"Show me the file {parts[-1]} from folder "
              f"{Path(mc.rel(settings, target.joinpath(*parts))).parent.as_posix()}"} for _, parts in plans]
    c = screen.card("list", f"Unzipped {path.name}", f"unzip-{mc.rel(settings, target)}", items=items)
    return screen.Shown(f"Unzipped {len(plans)} files into the folder {target.name}.", c)


def tool_definitions() -> list[dict]:
    return [{
        "name": "manage_memory_files",
        "description": "Tidy files in the memory folders. action 'rename' a file; 'move' it to another folder; "
                       "'copy' it (to another folder, or the same one); 'delete' it (ask the user first and set "
                       "confirmed true only after they say yes); 'zip' a whole folder into a .zip; 'zip_contents' "
                       "lists what's inside a .zip; 'unzip' unpacks a .zip into a new folder next to it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string",
                           "enum": ["rename", "move", "copy", "delete", "zip", "zip_contents", "unzip"]},
                "folder": {"type": "string", "description": "Memory folder the file (or, for zip, the folder) is in, "
                                                            "e.g. 'Work' or 'Work/Invoices'."},
                "filename": {"type": "string", "description": "The file's name or part of it."},
                "new_name": {"type": "string", "description": "rename: the new name."},
                "to_folder": {"type": "string", "description": "move/copy: the memory folder to put it in."},
                "confirmed": {"type": "boolean", "description": "delete: true only once the user has said yes."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"manage_memory_files"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, folder, filename = args.get("action"), args.get("folder") or "", args.get("filename") or ""
    if action == "rename":
        return rename(settings, folder, filename, args.get("new_name") or "")
    if action in ("move", "copy"):
        if action == "move" and not args.get("to_folder"):
            raise ValueError("Which folder should it go to?")
        return move(settings, folder, filename, args.get("to_folder") or "", copy=action == "copy")
    if action == "delete":
        return delete(settings, folder, filename, args.get("confirmed"))
    if action == "zip":
        return zip_folder(settings, folder)
    if action == "zip_contents":
        return zip_contents(settings, folder, filename)
    if action == "unzip":
        return unzip(settings, folder, filename)
    raise ValueError("Pick rename, move, copy, delete, zip, zip_contents or unzip.")
