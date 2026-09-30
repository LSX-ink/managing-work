"""Station LSX: the 3D world behind the HUD (frontend/station*.js), driven by the TikTok studio.

GET /station/state reads the studio store and says, per account, whether a video is being made, how many are ready
and waiting for approval, and which were approved lately. The page turns that into the scene: the crew load the ship
while videos are made, she flies to planet LSX once they are ready and waits there for the user's tick or cross, and
after an approval the page's courier carries the crate to its office while the ship flies home.

Alfred drives the view by voice with station_view ("show me the base", "zoom out to deep space", "night mode").
It returns a "station" card that frontend/station.js performs on the page instead of drawing a window.
"""

import time
from datetime import datetime

import screen
import tiktokstudio_store as cs
from config import Settings

screen.EXTRA_KINDS.add("station")

RECENT_HOURS = 24  # approvals younger than this count as recent
MAX_APPROVALS = 20
# The colour of each page's office at LSX; other pages use their own accent colour.
PAGE_COLOURS = {"lowkey.lore": "#e8813a", "mindglitch.fyi": "#5fc4ff", "karma.receipts": "#ff4d6d",
                "clipzz": "#9b6bff", "n3on.vault": "#39ffb0"}
FORMAT_WORDS = {"story": "STORIES", "facts": "EXPLAINERS", "clips": "TWITCH CLIPS"}
DONE = ("approved", "posted")


def _when(text) -> float | None:
    """Seconds since the epoch for a studio time such as "2026-09-30 14:05", or None."""
    try:
        return datetime.strptime(str(text or "")[:16], "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return None


def video_url(path: str) -> str:
    return f"/screen/file?path={screen.quote(path)}" if path else ""


def queue_item(data: dict, video: dict) -> dict:
    """One video waiting for approval, in the same shape as GET /creator/queue."""
    acc = cs.find_account(data, video.get("account")) or {}
    return {"id": video.get("id", ""), "account": video.get("account", ""), "title": video.get("title", ""),
            "kind": video.get("kind") or acc.get("format", ""), "created": video.get("made_at", ""),
            "video_url": video_url(video.get("file", "")), "thumb_url": video_url(video.get("thumb", ""))}


def state(settings: Settings, now: float | None = None) -> dict:
    """What the station shows right now, from the TikTok studio's store."""
    now = time.time() if now is None else now
    data = cs.load(settings)
    since = now - RECENT_HOURS * 3600
    videos = data["videos"]
    accounts = []
    for a in data["accounts"]:
        mine = [v for v in videos if v.get("account") == a["name"]]
        recent = [v for v in mine if v.get("status") in DONE and (_when(v.get("posted_at")) or 0) >= since]
        accounts.append({
            "name": a["name"], "format": a.get("format", ""), "style": a.get("style", ""),
            "label": f"{FORMAT_WORDS.get(a.get('format'), 'VIDEOS')} · {str(a.get('style', '')).upper()}".strip(" ·"),
            "colour": PAGE_COLOURS.get(a["name"].lower(), a.get("accent") or "#e8c547"),
            "making": sum(1 for v in mine if v.get("status") == "making"),
            "ready": sum(1 for v in mine if v.get("status") == "ready"),
            "approved": len(recent),
            "last_approved": max((v.get("posted_at", "") for v in recent), default=""),
        })
    waiting = [queue_item(data, v) for v in videos if v.get("status") == "ready"]
    approvals = [{"id": v.get("id", ""), "account": v.get("account", ""), "title": v.get("title", ""),
                  "at": v.get("posted_at", "")}
                 for v in videos if v.get("status") in DONE and (_when(v.get("posted_at")) or 0) >= since]
    making = sum(a["making"] for a in accounts)
    return {
        "phase": "waiting" if waiting else "making" if making else "idle",
        "making": making,
        "ready": len(waiting),
        "accounts": accounts,
        "waiting": waiting,
        "approvals": approvals[-MAX_APPROVALS:],
        "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
    }


# ---- Alfred drives the view --------------------------------------------------------------------------------

ACTIONS = {
    "base": "Taking you down to the base on HOME.",
    "factory": "Here's the factory at the base, where the cargo is built.",
    "lsx": "Heading down to the port on LSX.",
    "space": "Back out to the two planets.",
    "deep": "Zooming out to deep space.",
    "zoom_in": "Zooming in.",
    "zoom_out": "Zooming out.",
    "night": "Night mode at the bases.",
    "day": "Day mode at the bases.",
    "auto": "Day and night now follow your clock.",
    "approvals": "Here are the videos waiting at LSX.",
    "off": "Station off. The plain star background is back.",
    "on": "Station on.",
}
ALIASES = {"home": "base", "desert": "base", "port": "lsx", "forest": "lsx", "system": "space", "planets": "space",
           "deep_space": "deep", "galaxy": "deep", "in": "zoom_in", "out": "zoom_out", "clock": "auto",
           "waiting": "approvals", "queue": "approvals"}


def tool_definitions() -> list[dict]:
    return [{
        "name": "station_view",
        "description": "Drive the 3D station world behind the Alfred HUD (planet HOME with the desert base, planet LSX "
                       "with the forest port where videos wait for approval). base: show me the base / fly down to "
                       "HOME; lsx: go to LSX, the port; space: both planets; deep: zoom out to deep space and see "
                       "the whole solar system; zoom_in, zoom_out; night, day, auto: night mode, day mode, or follow "
                       "the clock; approvals: open the list of videos waiting at LSX to tick or cross; off and on: "
                       "turn the station background off (plain stars) or back on.",
        "input_schema": {
            "type": "object",
            "properties": {"action": {"type": "string", "enum": list(ACTIONS)}},
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"station_view"}


def view(action) -> screen.Shown:
    key = str(action or "").strip().lower().replace(" ", "_").replace("-", "_")
    key = ALIASES.get(key, key)
    if key not in ACTIONS:
        raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
    card = screen.card("station", "Station", "station-view", data={"action": key})
    return screen.Shown(ACTIONS[key], card)


def run_tool(name: str, args: dict, settings: Settings, http=None):
    if name == "station_view":
        return view(args.get("action"))
    raise ValueError(f"Unknown tool {name}.")
