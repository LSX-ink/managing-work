"""Music theory answers that pop up playable: chord notes, guitar chord diagrams, scales on a keyboard,
roman-numeral progressions in any key (and ten famous ones), transposing a song's chords, and a note's
frequency and MIDI number. The theory itself is in studio_theory; sound is made in the page.
"""

import screen
import studio_theory as theory
from config import Settings

KINDS = ("studio-chord", "studio-scale", "studio-guitar", "studio-chords")
for _kind in KINDS:
    screen.EXTRA_KINDS.add(_kind)

ACTIONS = ["chord", "guitar_chord", "scale", "progression", "famous_progressions", "transpose", "note_info"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "music_theory",
        "description": "Music theory with playable pop-ups. Actions: chord (notes in a chord like C#m7, Bbmaj7, "
                       "Dsus4, Gadd9); guitar_chord (fretboard diagram(s) for how to play guitar chords, with "
                       "strum); scale (notes of a scale: major, minors, pentatonics, blues, modes like dorian); "
                       "progression (roman numerals like I V vi IV in a key, or a famous progression by name); "
                       "famous_progressions (list 10 well-known ones); transpose (move a song's chords up or down "
                       "by semitones or into a new key); note_info (a note's frequency in Hz and MIDI number, or "
                       "the note for a frequency or MIDI number; A4 = 440 Hz).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "chord": {"type": "string", "description": "chord / guitar_chord: e.g. Am7 or 'G C D' for several."},
                "key": {"type": "string", "description": "scale / progression: root or key, e.g. D, F# minor."},
                "scale": {"type": "string", "description": "scale type, e.g. major, natural minor, blues, dorian."},
                "numerals": {"type": "string", "description": "progression: e.g. 'I V vi IV' or 'ii7 V7 Imaj7', "
                                                              "or a famous progression's name."},
                "chords": {"type": "string", "description": "transpose: the song's chords, e.g. 'G D Em C'."},
                "semitones": {"type": "integer", "description": "transpose: -11 to 11 (up is positive)."},
                "to_key": {"type": "string", "description": "transpose: new key instead of semitones; the first "
                                                            "chord is taken as the old key."},
                "note": {"type": "string", "description": "note_info: a note with octave, e.g. A4, C#5."},
                "frequency": {"type": "number", "description": "note_info: Hz."},
                "midi": {"type": "integer", "description": "note_info: MIDI number 0 to 127."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {t["name"] for t in tool_definitions()}


def chord(text) -> screen.Shown:
    c = theory.chord(text)
    notes = ", ".join(c["notes"])
    facts = [[n, i] for n, i in zip(c["notes"], c["intervals"])] + ([["Bass", c["bass"]]] if c["bass"] else [])
    data = {"name": c["name"], "notes": c["notes"], "midi": c["midi"], "mode": "chord", "facts": facts}
    return screen.Shown(f"{theory.spoken(c['name'])} is {theory.spoken(notes)}.", screen.card(
        "studio-chord", f"Chord: {c['name']}", "studio-chord", data=data, text=c["words"]))


def guitar_chord(text) -> screen.Shown:
    names = [n for n in str(text or "").replace(",", " ").split() if n][:6]
    if not names:
        raise ValueError("Which chord? For example G, Am or D7.")
    try:
        shapes = [theory.guitar_shape(text)]
    except ValueError:
        if len(names) == 1:
            raise
        shapes = [theory.guitar_shape(n) for n in names]
    spoken = "; ".join(f"{theory.spoken(s['name'])}: {_spoken_frets(s['frets'])}" for s in shapes)
    title = "Guitar: " + " ".join(s["name"] for s in shapes)
    return screen.Shown(f"{spoken}.", screen.card(
        "studio-guitar", title, "studio-guitar", data={"shapes": shapes},
        text="Low E string on the left. x = don't play, o = open string."))


def _spoken_frets(frets) -> str:
    return ", ".join("x" if f is None else str(f) for f in frets) + " from low E"


def scale(key, kind=None) -> screen.Shown:
    s = theory.scale(key or "C", kind or "major")
    data = {"name": s["name"], "notes": s["notes"], "midi": s["midi"], "mode": "scale",
            "facts": [["Notes", " ".join(s["notes"])], ["Steps", s["pattern"]]]}
    return screen.Shown(f"{theory.spoken(s['name'])}: {theory.spoken(', '.join(s['notes']))}.", screen.card(
        "studio-scale", f"Scale: {s['name']}", "studio-scale", data=data,
        text="W = whole step, H = half step."))


def _famous(name) -> tuple | None:
    wanted = str(name or "").lower().replace("'", "")
    for p in theory.FAMOUS:
        title = p[0].lower().replace("'", "")
        if wanted and (wanted in title or title in wanted):
            return p
    return None


def progression(numerals, key=None) -> screen.Shown:
    label = ""
    try:
        p = theory.progression(numerals, key or "C")
    except ValueError:
        famous = _famous(numerals)
        if not famous:
            raise
        label = famous[0]
        p = theory.progression(famous[1], key or ("A minor" if famous[2] == "minor" else "C"))
    names = " ".join(c["name"] for c in p["chords"])
    title = f"{label or 'Progression'} in {p['key']}"
    return screen.Shown(f"In {theory.spoken(p['key'])}: {theory.spoken(names)}.", screen.card(
        "studio-chords", title, "studio-chords", data={"chords": p["chords"], "bpm": 90},
        text=" ".join(c["numeral"] for c in p["chords"])))


def famous_progressions() -> screen.Shown:
    items = [{"label": f"{name}: {nums}. {where.capitalize()}.",
              "say": f"Play the {name} progression" + (" in A minor." if mode == "minor" else " in C.")}
             for name, nums, mode, where in theory.FAMOUS]
    spoken = "Here are ten famous chord progressions, like the pop axis, I V vi IV, and the twelve-bar blues."
    return screen.Shown(spoken, screen.card("list", "Famous chord progressions", "studio-famous", items=items,
                                            text="Click one to hear it."))


def transpose(chords, semitones=None, to_key=None) -> screen.Shown:
    text = str(chords or "")[:2000]
    if to_key:
        found = theory.CHORD_TOKEN.search(text)
        if not found:
            raise ValueError("I couldn't find any chords in that, like G D Em C.")
        first = found.group(1) + theory.ascii_acc(found.group(2))
        semitones = theory.interval_between(first, theory.parse_key(to_key)[0])
    if semitones is None:
        raise ValueError("How many semitones up or down, or which key?")
    n = int(semitones)
    if not -11 <= n <= 11:
        raise ValueError("Move by -11 to 11 semitones.")
    new_text, names = theory.transpose(text, n)
    old_names = [m.group(0) for m in theory.CHORD_TOKEN.finditer(text)]
    data = {"chords": [theory.playable(x) for x in names[:48]], "before": old_names[:48], "bpm": 90}
    direction = f"up {n}" if n > 0 else f"down {-n}" if n < 0 else "by 0"
    spoken = f"Moved {direction} semitone{'s' if abs(n) != 1 else ''}: {theory.spoken(' '.join(names[:16]))}."
    return screen.Shown(spoken, screen.card("studio-chords", f"Transposed {direction}", "studio-transpose",
                                            data=data, text=new_text[:1500]))


def note_info(note=None, freq=None, midi=None) -> screen.Shown:
    cents = None
    if note:
        m = theory.note_midi(note)
    elif freq is not None:
        m, cents = theory.from_frequency(float(freq))
    elif midi is not None:
        m = int(midi)
        if not 0 <= m <= 127:
            raise ValueError("MIDI numbers go from 0 to 127.")
    else:
        raise ValueError("Give a note like A4, a frequency in Hz, or a MIDI number.")
    hz = round(theory.frequency(m), 2)
    name, flat = theory.midi_name(m), theory.midi_name(m, flats=True)
    both = name if name == flat else f"{name} / {flat}"
    facts = [["Note", both], ["MIDI", str(m)], ["Frequency", f"{hz} Hz"]]
    if cents is not None:
        facts.insert(0, ["You gave", f"{float(freq):g} Hz"])
        facts.append(["Off by", f"{cents:+g} cents"])
        spoken = f"{float(freq):g} hertz is nearest {theory.spoken(name)}, MIDI {m}, {cents:+g} cents off."
    else:
        spoken = f"{theory.spoken(name)} is MIDI {m}, {hz:g} hertz."
    data = {"tones": [{"label": name, "midi": m, "freq": hz}], "facts": facts}
    return screen.Shown(spoken, screen.card("studio-tuner", f"Note {name}", "studio-note", data=data))


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "chord":
        return chord(args.get("chord"))
    if action == "guitar_chord":
        return guitar_chord(args.get("chord"))
    if action == "scale":
        return scale(args.get("key"), args.get("scale"))
    if action == "progression":
        return progression(args.get("numerals"), args.get("key"))
    if action == "famous_progressions":
        return famous_progressions()
    if action == "transpose":
        return transpose(args.get("chords"), args.get("semitones"), args.get("to_key"))
    if action == "note_info":
        return note_info(args.get("note"), args.get("frequency"), args.get("midi"))
    raise ValueError(f"Pick an action: {', '.join(ACTIONS)}.")
