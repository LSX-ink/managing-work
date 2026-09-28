"""Music-studio pop-ups you play with: a piano keyboard, a 16-step drum machine, tuning reference tones, tap
tempo, the circle of fifths, an interval ear-training quiz and a note-reading quiz.

All sound is synthesised in the page (frontend/popup-music-studio.js, WebAudio); nothing is recorded or sent.
Saved drum patterns come from studio-drums.json (see studio_log).
"""

import screen
import studio_log
import studio_theory as theory
from config import Settings

KINDS = ("studio-piano", "studio-drums", "studio-tuner", "studio-tap", "studio-circle", "studio-ear", "studio-staff")
for _kind in KINDS:
    screen.EXTRA_KINDS.add(_kind)

ACTIONS = ["piano", "drum_machine", "tuner", "tap_tempo", "circle_of_fifths", "ear_training", "note_quiz"]
PRESETS = {
    "Rock": {"bpm": 110, "kick": "x.......x.x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.x.",
             "clap": "................"},
    "Four on the floor": {"bpm": 124, "kick": "x...x...x...x...", "snare": "................",
                          "hat": "..x...x...x...x.", "clap": "....x.......x..."},
    "Hip hop": {"bpm": 90, "kick": "x......x..x.....", "snare": "....x.......x...", "hat": "x.x.x.x.x.x.x.xx",
                "clap": "............x..."},
}
EAR_LEVELS = {
    "easy": [0, 4, 7, 12],
    "medium": [2, 3, 4, 5, 7, 9, 12],
    "hard": list(range(1, 13)),
}
INTERVALS = {1: "minor 2nd", 2: "major 2nd", 3: "minor 3rd", 4: "major 3rd", 5: "perfect 4th", 6: "tritone",
             7: "perfect 5th", 8: "minor 6th", 9: "major 6th", 10: "minor 7th", 11: "major 7th", 12: "octave",
             0: "unison"}


def tool_definitions() -> list[dict]:
    return [{
        "name": "music_instrument",
        "description": "Pop up a playable music tool on the Alfred screen (sound made in the page). Actions: "
                       "piano (2-octave keyboard, play with mouse or computer keys); drum_machine (16-step beat "
                       "maker with kick, snare, hi-hat, clap; pattern loads a saved beat by name); tuner (reference "
                       "tones to tune a guitar, bass, ukulele, violin, viola or cello by ear); tap_tempo (tap to "
                       "find the BPM of a song); circle_of_fifths (click a key to see its chords); ear_training "
                       "(interval recognition quiz); note_quiz (read notes on the treble or bass clef staff).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "octave": {"type": "integer", "description": "piano: lowest octave, 1 to 6 (default 3, so C3 up)."},
                "pattern": {"type": "string", "description": "drum_machine: name of a saved pattern to load."},
                "bpm": {"type": "integer", "description": "drum_machine: tempo 40 to 240."},
                "instrument": {"type": "string", "enum": list(theory.TUNINGS), "description": "tuner (default guitar)."},
                "key": {"type": "string", "description": "circle_of_fifths: key to open at, e.g. G or E minor."},
                "level": {"type": "string", "enum": list(EAR_LEVELS), "description": "ear_training (default easy)."},
                "clef": {"type": "string", "enum": ["treble", "bass"], "description": "note_quiz (default treble)."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {t["name"] for t in tool_definitions()}


def piano(octave=None) -> screen.Shown:
    low = int(octave or 3)
    if not 1 <= low <= 6:
        raise ValueError("Pick an octave from 1 to 6.")
    data = {"start": (low + 1) * 12, "highlight": []}
    return screen.Shown("Here's a piano keyboard.", screen.card(
        "studio-piano", "Piano", "studio-piano", data=data,
        text="Click the keys, or click the keyboard and type: Z row and Q row play the two octaves, arrows shift."))


def drum_machine(settings: Settings, name=None, bpm=None) -> screen.Shown:
    saved = studio_log.patterns(settings)
    start, spoken = dict(PRESETS["Rock"]), "Here's the drum machine."
    if name:
        key = studio_log.find_pattern(saved, name)
        start, spoken = dict(saved[key]), f"Here's the drum machine with {key} loaded."
        start["name"] = key
    if bpm:
        start["bpm"] = studio_log.tempo(bpm)
    data = {"start": start, "presets": PRESETS, "saved": saved}
    return screen.Shown(spoken, screen.card("studio-drums", "Drum machine", "studio-drums", data=data))


def tuner(instrument=None) -> screen.Shown:
    which = instrument or "guitar"
    strings = theory.tuning(which)
    names = ", ".join(s["name"][:-1] for s in strings)
    data = {"tones": [{"label": s["name"], "midi": s["midi"], "freq": s["freq"]} for s in strings]}
    return screen.Shown(f"Here are the {which} tuning notes: {theory.spoken(names)}.", screen.card(
        "studio-tuner", f"{which.title()} tuning", "studio-tuner", data=data,
        text="Click a string to hear its note. Sustain keeps it sounding while you tune."))


def tap_tempo() -> screen.Shown:
    return screen.Shown("Tap along to find the tempo.", screen.card(
        "studio-tap", "Tap tempo", "studio-tap", data={},
        text="Tap the big button (or press space) in time with the music."))


def circle_of_fifths(key=None) -> screen.Shown:
    keys = theory.circle()
    pick = 0
    if key:
        tonic, minor = theory.parse_key(key)
        pc = theory.pitch_class(tonic)
        wanted = [k["minor"][:-1] if minor else k["major"] for k in keys]
        pick = next((i for i, n in enumerate(wanted) if theory.pitch_class(n) == pc), 0)
    data = {"keys": keys, "selected": pick, "minor": bool(key and theory.parse_key(key)[1])}
    return screen.Shown("Here's the circle of fifths.", screen.card(
        "studio-circle", "Circle of fifths", "studio-circle", data=data,
        text="Click a key: major on the outside, relative minor inside."))


def ear_training(level=None) -> screen.Shown:
    level = level or "easy"
    if level not in EAR_LEVELS:
        raise ValueError(f"Pick a level: {', '.join(EAR_LEVELS)}.")
    data = {"intervals": [{"semitones": s, "name": INTERVALS[s]} for s in EAR_LEVELS[level]], "level": level}
    return screen.Shown("Here's an interval quiz. Press play, listen, and pick the interval.", screen.card(
        "studio-ear", "Ear training", "studio-ear", data=data))


def note_quiz(clef=None) -> screen.Shown:
    clef = clef or "treble"
    if clef not in ("treble", "bass"):
        raise ValueError("Pick the treble or bass clef.")
    return screen.Shown(f"Here's a {clef} clef note quiz. Name the note on the staff.", screen.card(
        "studio-staff", f"Note quiz: {clef} clef", "studio-staff",
        data={"clef": clef, "notes": theory.staff_notes(clef)}))


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "piano":
        return piano(args.get("octave"))
    if action == "drum_machine":
        return drum_machine(settings, args.get("pattern"), args.get("bpm"))
    if action == "tuner":
        return tuner(args.get("instrument"))
    if action == "tap_tempo":
        return tap_tempo()
    if action == "circle_of_fifths":
        return circle_of_fifths(args.get("key"))
    if action == "ear_training":
        return ear_training(args.get("level"))
    if action == "note_quiz":
        return note_quiz(args.get("clef"))
    raise ValueError(f"Pick an action: {', '.join(ACTIONS)}.")
