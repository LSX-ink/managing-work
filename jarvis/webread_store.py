"""Reading help, part 2: where you stopped reading and how you like the reader to look (reading.json).

places: one entry per link or file, {title, kind, index, total, at, folder, filename}; prefs: font size, line
spacing, background tint, ruler and speed. Both live in the memory folder next to your other files.
"""

import json
import re
from datetime import datetime

import memory
from config import Settings

MAX_PLACES = 200
TINTS = ["cream", "blue", "yellow", "white", "dark"]
DEFAULT_PREFS = {"size": 22, "spacing": 1.7, "tint": "cream", "ruler": False, "speed": 1.0}


def path(settings: Settings):
    return memory.root(settings) / "reading.json"


def load(settings: Settings) -> dict:
    try:
        data = json.loads(path(settings).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get("places"), dict):
        data["places"] = {}
    prefs = data.get("prefs") if isinstance(data.get("prefs"), dict) else {}
    data["prefs"] = {**DEFAULT_PREFS, **{k: v for k, v in prefs.items() if k in DEFAULT_PREFS}}
    return data


def save(settings: Settings, data: dict) -> None:
    places = data["places"]
    for old in sorted(places, key=lambda k: places[k].get("at", ""))[:max(0, len(places) - MAX_PLACES)]:
        del places[old]
    memory.root(settings).mkdir(parents=True, exist_ok=True)
    path(settings).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def key_for(url: str = "", folder: str = "", filename: str = "") -> str:
    url = str(url or "").strip()
    if url:
        return url.split("#")[0]
    return f"{str(folder or '').strip()}/{str(filename or '').strip()}".strip("/")


def remember(settings: Settings, key: str, title: str, index: int, total: int, kind: str,
             folder: str = "", filename: str = "") -> dict:
    data = load(settings)
    data["places"][key] = {"title": title[:100], "kind": kind, "index": max(0, int(index)), "total": max(1, int(total)),
                           "at": datetime.now().isoformat(timespec="seconds"), "folder": folder, "filename": filename}
    save(settings, data)
    return data["places"][key]


def find(data: dict, wanted: str = "") -> tuple[str, dict] | None:
    """The saved place matching a link, file name or part of a title; the newest one when nothing is asked for."""
    places = data["places"]
    if not places:
        return None
    wanted = str(wanted or "").strip().lower()
    if not wanted:
        key = max(places, key=lambda k: places[k].get("at", ""))
        return key, places[key]
    for key, p in sorted(places.items(), key=lambda kv: kv[1].get("at", ""), reverse=True):
        if wanted in key.lower() or wanted in p["title"].lower():
            return key, p
    return None


def clamp_prefs(args: dict, current: dict) -> dict:
    out = dict(current)
    if args.get("size") is not None:
        out["size"] = min(48, max(14, int(args["size"])))
    if args.get("spacing") is not None:
        out["spacing"] = round(min(2.6, max(1.2, float(args["spacing"]))), 1)
    tint = re.sub(r"[^a-z]", "", str(args.get("tint") or "").lower())
    if tint:
        if tint not in TINTS:
            raise ValueError(f"Pick a background tint: {', '.join(TINTS)}.")
        out["tint"] = tint
    if args.get("ruler") is not None:
        out["ruler"] = bool(args["ruler"])
    if args.get("speed") is not None:
        out["speed"] = round(min(1.6, max(0.6, float(args["speed"]))), 2)
    return out
