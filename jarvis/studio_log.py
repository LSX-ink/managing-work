"""Music practice log (minutes per instrument, a weekly chart and a streak), songs to learn with their status,
and saved drum-machine patterns.

Kept on this PC in studio-practice.json, studio-songs.json and studio-drums.json in the memory folder.
"""

import re
from datetime import date, timedelta

import homestore as hs
import screen
from config import Settings

PRACTICE, SONGS, DRUMS = "studio-practice.json", "studio-songs.json", "studio-drums.json"
KEEP = 3000
STATUSES = ["to learn", "learning", "can play", "mastered"]
TRACKS = ("kick", "snare", "hat", "clap")
TRACK_LETTERS = {"k": "kick", "s": "snare", "h": "hat", "c": "clap", "hh": "hat", "hihat": "hat", "hi-hat": "hat"}
ACTIONS = ["log", "week", "song_add", "song_update", "songs", "song_remove", "pattern_save", "patterns",
           "pattern_delete"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "music_practice",
        "description": "The user's music practice diary and song list. Actions: log (practised an instrument for "
                       "some minutes, and what); week (this week's practice chart and streak); song_add (a song "
                       "to learn); song_update (change a song's status or notes); songs (the list); song_remove; "
                       "pattern_save (store a drum machine pattern: the drum machine's Save button sends the "
                       "pattern text); patterns (saved drum patterns); pattern_delete. Set confirmed true for "
                       "song_remove and pattern_delete only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "instrument": {"type": "string"},
                "minutes": {"type": "number"},
                "what": {"type": "string", "description": "log: what was practised, e.g. scales, a song."},
                "day": {"type": "string", "description": "log: YYYY-MM-DD, today or yesterday (default today)."},
                "title": {"type": "string", "description": "Song title."},
                "artist": {"type": "string"},
                "status": {"type": "string", "enum": STATUSES},
                "notes": {"type": "string", "description": "Song notes, e.g. capo 2, tricky bridge."},
                "name": {"type": "string", "description": "Drum pattern name."},
                "bpm": {"type": "integer"},
                "pattern": {"type": "string", "description": "pattern_save: the pattern text, e.g. "
                                                             "'kick x...x... snare ....x... hat ... clap ...'."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {t["name"] for t in tool_definitions()}


def _load(settings, name, default):
    return hs.load(settings, name, default)


# ---- practice ----------------------------------------------------------------------------------------

def log(settings: Settings, instrument, minutes, what="", day=None) -> str:
    inst = hs.need(instrument, "instrument", 40).lower()
    mins = round(hs.number(minutes, "minutes", 1, 600))
    when = hs.parse_day(day, hs.today()) if day else hs.today()
    entries = [e for e in _load(settings, PRACTICE, []) if isinstance(e, dict)]
    entries.append({"date": when.isoformat(), "instrument": inst, "minutes": mins, "what": hs.clean(what, 120)})
    hs.save(settings, PRACTICE, entries[-KEEP:])
    total = sum(e["minutes"] for e in entries if e["date"] == when.isoformat())
    streak = _streak(entries, hs.today())
    return (f"Logged {mins} minutes of {inst}. {total} minutes that day; "
            f"practice streak {streak} day{'s' if streak != 1 else ''}.")


def _streak(entries: list[dict], today: date) -> int:
    days = {e.get("date") for e in entries if e.get("minutes")}
    day = today if today.isoformat() in days else today - timedelta(days=1)
    count = 0
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


def week(settings: Settings) -> screen.Shown:
    today = hs.today()
    entries = [e for e in _load(settings, PRACTICE, []) if isinstance(e, dict)]
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    per_day = [sum(e.get("minutes", 0) for e in entries if e.get("date") == d.isoformat()) for d in days]
    recent = [e for e in entries if e.get("date", "") >= days[0].isoformat()]
    by_inst: dict[str, int] = {}
    for e in recent:
        by_inst[e["instrument"]] = by_inst.get(e["instrument"], 0) + e.get("minutes", 0)
    streak = _streak(entries, today)
    total = sum(per_day)
    if not total:
        spoken = f"No practice logged in the last 7 days. Streak {streak} days."
    else:
        split = ", ".join(f"{m} minutes of {i}" for i, m in sorted(by_inst.items(), key=lambda x: -x[1]))
        spoken = f"{total} minutes of practice in the last 7 days: {split}. Streak {streak} day{'s' if streak != 1 else ''}."
    labels = [d.strftime("%a") for d in days]
    return screen.Shown(spoken, screen.card(
        "chart", "Practice this week", "studio-practice-week", text=f"Streak: {streak} days. Total: {total} minutes.",
        chart={"type": "bar", "labels": labels, "values": per_day, "unit": "min"}))


# ---- songs to learn ----------------------------------------------------------------------------------

def _songs(settings) -> list[dict]:
    return [s for s in _load(settings, SONGS, []) if isinstance(s, dict) and s.get("title")]


def _find_song(songs: list[dict], title) -> dict:
    words = re.findall(r"\w+", hs.clean(title).lower())
    exact = [s for s in songs if s["title"].lower() == hs.clean(title).lower()]
    found = exact or [s for s in songs if words and all(w in s["title"].lower() for w in words)]
    if len(found) != 1:
        raise ValueError("I couldn't find that song on your list." if not found else
                         f"Which one: {', '.join(s['title'] for s in found[:5])}?")
    return found[0]


def song_add(settings: Settings, title, artist="", status=None, notes="") -> str:
    songs = _songs(settings)
    name = hs.need(title, "song", 80)
    if any(s["title"].lower() == name.lower() for s in songs):
        raise ValueError(f"{name} is already on your list.")
    status = status or "to learn"
    if status not in STATUSES:
        raise ValueError(f"Pick a status: {', '.join(STATUSES)}.")
    songs.append({"title": name, "artist": hs.clean(artist, 60), "status": status, "notes": hs.clean(notes, 200),
                  "added": hs.today().isoformat()})
    hs.save(settings, SONGS, songs)
    return f"Added {name} to your songs, marked {status}."


def song_update(settings: Settings, title, status=None, notes=None) -> str:
    songs = _songs(settings)
    song = _find_song(songs, title)
    if not status and notes is None:
        raise ValueError("Give a new status or notes.")
    if status:
        if status not in STATUSES:
            raise ValueError(f"Pick a status: {', '.join(STATUSES)}.")
        song["status"] = status
    if notes is not None:
        song["notes"] = hs.clean(notes, 200)
    song["updated"] = hs.today().isoformat()
    hs.save(settings, SONGS, songs)
    return f"{song['title']} is now {song['status']}." + (" Notes saved." if notes is not None else "")


def songs_list(settings: Settings) -> screen.Shown:
    songs = sorted(_songs(settings), key=lambda s: (STATUSES.index(s.get("status", "to learn"))
                                                    if s.get("status") in STATUSES else 0, s["title"].lower()))
    if not songs:
        return screen.Shown("Your song list is empty.", screen.card(
            "text", "Songs to learn", "studio-songs", text="No songs yet. Say: add Wonderwall to my songs to learn."))
    counts = {st: sum(s.get("status") == st for s in songs) for st in STATUSES}
    spoken = "Your songs: " + ", ".join(f"{n} {st}" for st, n in counts.items() if n) + "."
    rows = [[s["title"], s.get("artist", ""), s.get("status", ""), s.get("notes", "")] for s in songs]
    return screen.Shown(spoken, screen.card("table", "Songs to learn", "studio-songs",
                                            columns=["Song", "Artist", "Status", "Notes"], rows=rows))


def song_remove(settings: Settings, title, confirmed=False) -> str:
    songs = _songs(settings)
    song = _find_song(songs, title)
    if not confirmed:
        return f"Remove {song['title']} from your songs? Say yes to confirm."
    hs.save(settings, SONGS, [s for s in songs if s is not song])
    return f"Removed {song['title']}."


# ---- drum patterns -----------------------------------------------------------------------------------

def tempo(bpm) -> int:
    return round(hs.number(bpm, "tempo", 40, 240))


def parse_pattern(text) -> dict:
    """'kick x...x... snare ....x... hat ... clap ...' (16 steps each, x or o = hit) -> {track: 'x...'}."""
    found = {}
    for word, steps in re.findall(r"(?<![\w-])(hi-hat|hihat|kick|snare|clap|hat|hh|[ksch])\s*[:=]?\s*([xXoO.\-_]{16})(?![xXoO.\-_])",
                                  str(text or "")):
        track = TRACK_LETTERS.get(word.lower(), word.lower())
        found[track] = "".join("x" if c in "xXoO" else "." for c in steps)
    if not found:
        raise ValueError("I couldn't read that pattern; it needs tracks like kick x...x...x...x... (16 steps).")
    return {t: found.get(t, "." * 16) for t in TRACKS}


def patterns(settings: Settings) -> dict:
    found = _load(settings, DRUMS, {})
    return {k: v for k, v in found.items() if isinstance(v, dict) and all(isinstance(v.get(t), str) for t in TRACKS)}


def find_pattern(saved: dict, name) -> str:
    key = hs.find(saved.keys(), name)
    if key is None:
        raise ValueError("I couldn't find that drum pattern." + (f" Saved: {', '.join(saved)}." if saved else ""))
    return key


def pattern_save(settings: Settings, name, pattern, bpm=None) -> str:
    title = hs.need(name, "pattern name", 40)
    saved = patterns(settings)
    tracks = parse_pattern(pattern)
    key = hs.find(saved.keys(), title)
    key = key if key and key.lower() == title.lower() else title
    saved[key] = {"bpm": tempo(bpm or 100), **tracks, "saved": hs.today().isoformat()}
    hs.save(settings, DRUMS, saved)
    hits = sum(v.count("x") for v in tracks.values())
    return f"Saved drum pattern {key} at {saved[key]['bpm']} BPM, {hits} hits."


def patterns_list(settings: Settings) -> screen.Shown:
    saved = patterns(settings)
    if not saved:
        return screen.Shown("You haven't saved any drum patterns yet.", screen.card(
            "text", "Drum patterns", "studio-patterns",
            text="None yet. Open the drum machine, make a beat, type a name and press Save pattern."))
    items = [{"label": f"{k} ({v['bpm']} BPM)", "say": f"Load my drum pattern {k} in the drum machine."}
             for k, v in saved.items()]
    return screen.Shown(f"You have {len(saved)} saved drum pattern{'s' if len(saved) != 1 else ''}: "
                        f"{', '.join(saved)}.", screen.card("list", "Drum patterns", "studio-patterns", items=items,
                                                            text="Click one to load it."))


def pattern_delete(settings: Settings, name, confirmed=False) -> str:
    saved = patterns(settings)
    key = find_pattern(saved, name)
    if not confirmed:
        return f"Delete the drum pattern {key}? Say yes to confirm."
    del saved[key]
    hs.save(settings, DRUMS, saved)
    return f"Deleted the drum pattern {key}."


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    confirmed = args.get("confirmed") is True
    if action == "log":
        return log(settings, args.get("instrument"), args.get("minutes"), args.get("what", ""), args.get("day"))
    if action == "week":
        return week(settings)
    if action == "song_add":
        return song_add(settings, args.get("title"), args.get("artist", ""), args.get("status"), args.get("notes", ""))
    if action == "song_update":
        return song_update(settings, args.get("title"), args.get("status"), args.get("notes"))
    if action == "songs":
        return songs_list(settings)
    if action == "song_remove":
        return song_remove(settings, args.get("title"), confirmed)
    if action == "pattern_save":
        return pattern_save(settings, args.get("name"), args.get("pattern"), args.get("bpm"))
    if action == "patterns":
        return patterns_list(settings)
    if action == "pattern_delete":
        return pattern_delete(settings, args.get("name"), confirmed)
    raise ValueError(f"Pick an action: {', '.join(ACTIONS)}.")
