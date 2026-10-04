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
    "clips": "viral Twitch clips filling the whole phone, a hook line on top and the streamer credited",
}
FORMATS = {
    "story": "a short original story with a twist, told in scenes",
    "facts": "a punchy explainer series: one idea per video, told in short lines",
    "clips": "viral streamer clips from Twitch or Kick, old and new, joined to a minute or more",
}
STATUSES = ("making", "ready", "approved", "posted", "rejected", "skipped", "failed")
PLATFORMS = ("twitch", "kick")
MAX_TASTE = 20  # liked and rejected videos remembered per account
# Voices for recurring characters, by kind: each character gets one the first time they speak and keeps it forever,
# so a returning character always sounds the same. Distinct from the narrator's voice.
CHARACTER_VOICES = {
    "woman": ["en-GB-SoniaNeural", "en-GB-LibbyNeural", "en-IE-EmilyNeural", "en-AU-NatashaNeural", "en-US-JennyNeural"],
    "man": ["en-US-GuyNeural", "en-IE-ConnorNeural", "en-AU-WilliamNeural", "en-US-ChristopherNeural", "en-CA-LiamNeural"],
    "old man": ["en-GB-ThomasNeural", "en-US-DavisNeural"],
    "old woman": ["en-US-AriaNeural", "en-GB-HollieNeural"],
    "child": ["en-US-AnaNeural", "en-GB-MaisieNeural"],
}
MAX_CHARACTERS, MAX_THREADS = 12, 10  # the story bible: recurring characters and open story threads per account
# N3on said yes to clipping (the user told Alfred so); he streams on Kick and sometimes Twitch.
NEON = [{"name": "n3on", "platform": "kick", "allows_clipping": True},
        {"name": "n3on", "platform": "twitch", "allows_clipping": True}]
# Two accounts to start from, in the looks of the pages the user liked. Rename or change them freely.
STARTERS = [
    {"name": "lowkey.lore", "theme": "dark, moody short stories with a twist: love, loss, late nights and secrets",
     "style": "noir", "format": "story", "series": ["Midnight Tapes", "Unsent Letters", "Last Voicemail"]},
    {"name": "mindglitch.fyi", "theme": "psychology and human behaviour: what your habits, names and moods say "
                                        "about you, told kindly and simply",
     "style": "explainer", "format": "facts", "series": ["Letter Psychology", "Birth Months", "Signs You're"]},
    {"name": "karma.receipts", "theme": "dramatic family, relationship and workplace stories where karma lands: "
                                        "betrayal, secrets, faith and protection, second chances and satisfying twists; end with a line "
                                        "that invites a comment (like Type amen)",
     "style": "drama", "format": "story", "series": ["Karma Hit Different", "They Didn't Know", "Plot Twist"]},
    {"name": "Clipzz", "theme": "the most viral Twitch streamer moments, from old classics to this week's",
     "style": "clips", "format": "clips", "per_day": 5, "category": "Just Chatting"},
    {"name": "n3on.vault", "theme": "N3on's most viral stream moments, each one extended with what happened just "
                                    "before and after the clip", "style": "clips", "format": "clips", "per_day": 3,
     "streamers": NEON, "min_views": 100_000, "extend": 30},
]
LORE = "lowkey.lore"  # the one page still making videos (the others are off until the user sets them up)
SWITCH_OFF_OTHERS = True
# Starters added after someone's studio already existed get added once, by name.
LATER_STARTERS = {"Clipzz", "n3on.vault"}


def clean(value, limit: int = 200) -> str:
    return re.sub(r"\s+", " ", str(value if value is not None else "")).strip()[:limit]


def slug(text: str, fallback: str = "video") -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", str(text or "")).strip().strip(".")[:50].strip()
    return name or fallback


def streamer(item, platform: str = "twitch") -> dict | None:
    """{name, platform, allows_clipping} from a dict or a bare name; a bare name hasn't said yes to clipping."""
    item = item if isinstance(item, dict) else {"name": item}
    name = clean(item.get("name"), 40).lstrip("@")
    if not name:
        return None
    where = str(item.get("platform") or platform).lower()
    return {"name": name, "platform": where if where in PLATFORMS else "twitch",
            "allows_clipping": item.get("allows_clipping") is True}


def allowed(account: dict, platform: str | None = None) -> list[str]:
    """Names of the account's streamers who allow clipping (on one platform, or any)."""
    return [s["name"] for s in (streamer(x) for x in account.get("streamers") or [])
            if s and s["allows_clipping"] and platform in (None, s["platform"])]


def new_account(name: str, **fields) -> dict:
    name = clean(name, 40).lstrip("@")
    if not name:
        raise ValueError("The account needs a name.")
    style = fields.get("style") if fields.get("style") in STYLES else "noir"
    kind = fields.get("format") if fields.get("format") in FORMATS else (
        "facts" if style == "explainer" else "clips" if style == "clips" else "story")
    if kind == "clips":
        style = "clips"
    return {"name": name, "theme": clean(fields.get("theme"), 300) or "short original stories",
            "style": style, "format": kind, "series": [clean(s, 60) for s in fields.get("series") or [] if clean(s, 60)][:10],
            "per_day": max(0, min(int(fields.get("per_day") if fields.get("per_day") is not None else 3), 6)),
            "voice": clean(fields.get("voice"), 60), "accent": clean(fields.get("accent"), 20) or "#e8c547",
            "streamers": [s for s in (streamer(x) for x in fields.get("streamers") or []) if s][:30],
            "category": clean(fields.get("category"), 60) or "Just Chatting",
            "min_views": max(0, int(fields.get("min_views") or 0)),  # clip accounts: only clips with this many views
            "extend": max(0, min(int(fields.get("extend") or 0), 120)),  # seconds added before and after each clip
            "used_clips": list(fields.get("used_clips") or [])[-3000:],
            "off": fields.get("off") is True,  # switched off: no daily videos, sequels or new videos at all
            "taste": fields.get("taste") if isinstance(fields.get("taste"), dict) else {"liked": [], "rejected": []}}


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
    added = set(data.get("starters_added") or [])
    for starter in STARTERS:
        if starter["name"] in LATER_STARTERS - added:
            if not any(a["name"].lower() == starter["name"].lower() for a in data["accounts"]):
                data["accounts"].append(new_account(**starter))
            added.add(starter["name"])
    data["starters_added"] = sorted(added)
    if SWITCH_OFF_OTHERS and not data.get("lore_only"):  # the user, 4 Oct: stop every page but lowkey.lore until they make a page for it
        for a in data["accounts"]:
            a["off"] = a.get("name", "").lower() != LORE
        data["lore_only"] = True
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


WAITING = ("ready", "failed_post")


def find_video(data: dict, ref, waiting: bool = False) -> dict:
    """A video by its id, 'latest', part of its title, or its account ('the lowkey.lore video'). waiting prefers
    the videos still waiting for a tick or an X."""
    ref = clean(ref, 100).lower().lstrip("@")
    videos = data["videos"]
    if not videos:
        raise ValueError("There are no videos yet.")
    queue = [v for v in videos if v.get("status") in WAITING] if waiting else []
    if ref in ("", "latest", "last", "newest", "that one", "this one", "it"):
        return (queue or videos)[-1]
    for v in reversed(videos):
        if v["id"] == ref or ref in v.get("title", "").lower():
            return v
    named = find_account(data, ref)
    mine = [v for v in queue or videos if named and v.get("account") == named["name"]]
    if mine:
        return mine[-1]
    raise ValueError(f"I can't find a video called {ref}.")


# ---- taste: what the user ticked and what they X-ed ---------------------------------------------------------

def remember(account: dict, video: dict, liked: bool, reason: str = "") -> None:
    taste = account.setdefault("taste", {"liked": [], "rejected": []})
    row = {"title": clean(video.get("title"), 90), "hook": clean(video.get("hook") or video.get("keyword"), 200),
           "notes": clean(video.get("notes"), 200), "reason": clean(reason, 300), "day": date.today().isoformat()}
    key = "liked" if liked else "rejected"
    taste[key] = [*(taste.get(key) or []), row][-MAX_TASTE:]


def taste_summary(account: dict, n: int = 6) -> str:
    """A few lines for Claude: what the user approved and rejected on this account, newest first."""
    taste = account.get("taste") or {}

    def line(r: dict) -> str:
        bits = [f"'{r.get('title')}'"] + [f"hook: {r['hook']}"] * bool(r.get("hook")) + [r.get("notes")] * bool(r.get("notes"))
        return ", ".join(bits) + (f" (why: {r['reason']})" if r.get("reason") else "")
    liked = [line(r) for r in reversed((taste.get("liked") or [])[-n:])]
    rejected = [line(r) for r in reversed((taste.get("rejected") or [])[-n:])]
    if not liked and not rejected:
        return "No ticks or X's yet: be bold and try something fresh."
    return ("The user APPROVED: " + ("; ".join(liked) or "nothing yet") + ".\nThe user REJECTED: "
            + ("; ".join(rejected) or "nothing yet") + ".")


# ---- the story bible: the account's recurring world, so series and characters stay consistent ----------------

def update_bible(account: dict, update) -> None:
    """Merge what the writer added: characters (by name: look and notes), threads opened and closed, the world."""
    if not isinstance(update, dict):
        return
    bible = account.setdefault("bible", {"world": "", "characters": [], "threads": []})
    world = clean(update.get("world"), 400)
    if world:
        bible["world"] = world
    people = {c["name"].lower(): c for c in bible.get("characters") or []}
    for c in update.get("characters") or []:
        if not isinstance(c, dict) or not clean(c.get("name"), 40):
            continue
        name = clean(c.get("name"), 40)
        row = people.pop(name.lower(), {"name": name, "look": "", "notes": ""})
        row["look"] = clean(c.get("look"), 300) or row["look"]
        row["notes"] = clean(c.get("notes"), 300) or row["notes"]
        kind = clean(c.get("voice_type"), 20).lower()
        if kind in CHARACTER_VOICES and not row.get("voice_type"):
            row["voice_type"] = kind
        if clean(c.get("voice"), 60) and not row.get("voice"):
            row["voice"] = clean(c.get("voice"), 60)  # set once, never changed: the character keeps their voice
        people[name.lower()] = row  # moved to the end: the most recently used last
    bible["characters"] = list(people.values())[-MAX_CHARACTERS:]
    closed = {clean(t, 200).lower() for t in update.get("threads_closed") or []}
    threads = [t for t in bible.get("threads") or [] if t.lower() not in closed]
    threads += [clean(t, 200) for t in update.get("threads_opened") or [] if clean(t, 200) and clean(t, 200) not in threads]
    bible["threads"] = threads[-MAX_THREADS:]


def bible_summary(account: dict) -> str:
    bible = account.get("bible") or {}
    parts = []
    if bible.get("world"):
        parts.append(f"World: {bible['world']}")
    for c in bible.get("characters") or []:
        parts.append(f"Character {c['name']}: {c.get('look') or 'look not set'}" + (f" ({c['notes']})" if c.get("notes") else "")
                     + (f" [voice: {c['voice_type']}]" if c.get("voice_type") else ""))
    if bible.get("threads"):
        parts.append("Open threads to pay off or deepen: " + "; ".join(bible["threads"]))
    return "\n".join(parts) or "Empty so far: this video can start the account's world."


def assign_voices(account: dict, update) -> dict:
    """Give every named character in this video (from the account's bible and the script's own bible update) a voice.
    Known characters keep the voice they already have; new ones get an unused voice of their kind, which is written
    into the update so the bible stores it. Returns {lower-case name: voice}."""
    known = {c["name"].lower(): c for c in (account.get("bible") or {}).get("characters") or []}
    taken = {c.get("voice") for c in known.values()} | {account.get("voice") or ""}
    voices = {name: c["voice"] for name, c in known.items() if c.get("voice")}
    for c in (update or {}).get("characters") or [] if isinstance(update, dict) else []:
        if not isinstance(c, dict) or not clean(c.get("name"), 40):
            continue
        name = clean(c.get("name"), 40).lower()
        if name in voices:
            c["voice"] = voices[name]
            continue
        kind = clean(c.get("voice_type"), 20).lower() or (known.get(name) or {}).get("voice_type", "")
        pool = CHARACTER_VOICES.get(kind)
        if not pool:
            continue
        free = [v for v in pool if v not in taken] or pool
        voice = free[sum(map(ord, name)) % len(free)]
        c["voice"], voices[name] = voice, voice
        taken.add(voice)
    return voices


def new_id() -> str:
    return f"v{int(time.time() * 1000):x}"


def made_today(data: dict, account_name: str, on: date | None = None) -> int:
    on = (on or date.today()).isoformat()
    return sum(1 for v in data["videos"] if v.get("account") == account_name and v.get("day") == on
               and v.get("status") not in ("failed", "rejected"))


def work_folder(settings: Settings, *parts: str) -> Path:
    """A folder inside the Work memory folder (or the second brain folder if Work was renamed), made if missing."""
    names = memory.names(settings)
    top = next((n for n in names if n.lower() == "work"), names[1])
    return memory.folder(settings, "/".join([top, *(slug(p, "Files") for p in parts)]), create=True)


def relative(settings: Settings, path: Path) -> str:
    return path.resolve().relative_to(memory.root(settings).resolve()).as_posix()
