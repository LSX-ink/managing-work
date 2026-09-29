"""Shared helpers for Alfred's TikTok studio: the accounts he runs and the videos he has made.

Everything lives in creator.json in the memory folder. Each account has its own theme, look (style), voice and
how many videos a day it gets. The videos themselves are saved as MP4 files in the Work memory folder under
TikTok/<account>/, each next to a small text file with its caption, so they can also be uploaded by hand.
"""

import json
import re
import time
from datetime import date
from pathlib import Path

import memory
from config import Settings

FILE = "creator.json"
MAX_ACCOUNTS = 12
MAX_VIDEOS = 400  # oldest finished videos drop off the list (their files stay)
STYLES = {
    "noir": "black-and-white card: a moody photo on a centred card, small title and author line underneath",
    "explainer": "black explainer: a coloured keyword at the top, a simple drawn figure in the middle, dark background",
    "drama": "realistic full-screen scenes with a bold headline in a white box, like viral AI drama stories",
    "cinematic": "full-screen colour film stills with captions at the bottom",
}
FORMATS = {
    "story": "a short original story with a twist, told in scenes",
    "facts": "a punchy explainer series: one idea per video, told in short lines",
}
STATUSES = ("making", "ready", "approved", "posted", "skipped", "failed")
# Two accounts to start from, in the looks of the pages the user liked. Rename or change them freely.
STARTERS = [
    {"name": "lowkey.lore", "theme": "dark, moody short stories with a twist: love, loss, late nights and secrets",
     "style": "noir", "format": "story", "series": ["Midnight Tapes", "Unsent Letters", "Last Voicemail"]},
    {"name": "mindglitch.fyi", "theme": "psychology and human behaviour: what your habits, names and moods say "
                                        "about you, told kindly and simply",
     "style": "explainer", "format": "facts", "series": ["Letter Psychology", "Birth Months", "Signs You're"]},
    {"name": "karma.receipts", "theme": "dramatic family, relationship and workplace stories where karma lands: "
                                        "betrayal, secrets, second chances and satisfying twists",
     "style": "drama", "format": "story", "series": ["Karma Hit Different", "They Didn't Know", "Plot Twist"]},
]


def clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(value if value is not None else "")).strip()[:limit]


def slug(text: str, fallback: str = "video") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(text or "")).strip().strip(".")[:50].strip()
    return name or fallback


def new_account(name: str, **fields) -> dict:
    name = clean(name, 40).lstrip("@")
    if not name:
        raise ValueError("The account needs a name.")
    style = fields.get("style") if fields.get("style") in STYLES else "noir"
    kind = fields.get("format") if fields.get("format") in FORMATS else ("facts" if style == "explainer" else "story")
    return {"name": name, "theme": clean(fields.get("theme"), 300) or "short original stories",
            "style": style, "format": kind, "series": [clean(s, 60) for s in fields.get("series") or [] if clean(s, 60)][:10],
            "per_day": max(0, min(int(fields.get("per_day") if fields.get("per_day") is not None else 3), 6)),
            "voice": clean(fields.get("voice"), 60), "accent": clean(fields.get("accent"), 20) or "#e8c547"}


def load(settings: Settings) -> dict:
    try:
        data = json.loads((memory.root(settings) / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    if not isinstance(data, dict):
        data = {"accounts": [new_account(**s) for s in STARTERS], "videos": []}
    for key in ("accounts", "videos"):
        if not isinstance(data.get(key), list):
            data[key] = []
    return data


def save(settings: Settings, data: dict) -> None:
    data["videos"] = data["videos"][-MAX_VIDEOS:]
    path = memory.root(settings) / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def find_account(data: dict, name) -> dict | None:
    want = clean(name, 40).lstrip("@").lower()
    if not want:
        return data["accounts"][0] if len(data["accounts"]) == 1 else None
    for a in data["accounts"]:
        if a["name"].lower() == want:
            return a
    return next((a for a in data["accounts"] if want in a["name"].lower()), None)


def account(data: dict, name) -> dict:
    found = find_account(data, name)
    if found is None:
        have = ", ".join(a["name"] for a in data["accounts"]) or "none yet"
        raise ValueError(f"Which account? The accounts are: {have}.")
    return found


def find_video(data: dict, ref) -> dict:
    """A video by its id, or by 'latest', or by part of its title."""
    ref = clean(ref, 100).lower()
    videos = data["videos"]
    if not videos:
        raise ValueError("There are no videos yet.")
    if ref in ("", "latest", "last", "newest"):
        return videos[-1]
    for v in reversed(videos):
        if v["id"] == ref or ref in v.get("title", "").lower():
            return v
    raise ValueError(f"I can't find a video called {ref}.")


def new_id() -> str:
    return f"v{int(time.time() * 1000):x}"


def made_today(data: dict, account_name: str, on: date | None = None) -> int:
    on = (on or date.today()).isoformat()
    return sum(1 for v in data["videos"] if v.get("account") == account_name and v.get("day") == on
               and v.get("status") != "failed")


def work_folder(settings: Settings, *parts: str) -> Path:
    """A folder inside the Work memory folder (or the second brain folder if Work was renamed), made if missing."""
    names = memory.names(settings)
    top = next((n for n in names if n.lower() == "work"), names[1])
    return memory.folder(settings, "/".join([top, *(slug(p, "Files") for p in parts)]), create=True)


def relative(settings: Settings, path: Path) -> str:
    return path.resolve().relative_to(memory.root(settings).resolve()).as_posix()
