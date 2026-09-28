"""A small music-theory library for the music-studio abilities: notes, chords, scales, keys, roman-numeral
progressions, transposing, guitar chord shapes and note frequencies (A4 = 440 Hz, MIDI 69).

Notes are spelled properly: each chord or scale step moves up by letter, so F major has Bb (not A#) and
C# major has E# (not F). Every function raises ValueError with a friendly message on bad input.
"""

import math
import re

LETTERS = "CDEFGAB"
NATURAL = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
ACCIDENTALS = {"": 0, "#": 1, "##": 2, "b": -1, "bb": -2}

# (semitones, letter steps) above the root, so each note gets the right letter.
CHORDS = {
    "major": [(0, 0), (4, 2), (7, 4)],
    "minor": [(0, 0), (3, 2), (7, 4)],
    "7": [(0, 0), (4, 2), (7, 4), (10, 6)],
    "maj7": [(0, 0), (4, 2), (7, 4), (11, 6)],
    "m7": [(0, 0), (3, 2), (7, 4), (10, 6)],
    "dim": [(0, 0), (3, 2), (6, 4)],
    "aug": [(0, 0), (4, 2), (8, 4)],
    "sus2": [(0, 0), (2, 1), (7, 4)],
    "sus4": [(0, 0), (5, 3), (7, 4)],
    "add9": [(0, 0), (4, 2), (7, 4), (14, 8)],
    "6": [(0, 0), (4, 2), (7, 4), (9, 5)],
    "m6": [(0, 0), (3, 2), (7, 4), (9, 5)],
    "9": [(0, 0), (4, 2), (7, 4), (10, 6), (14, 8)],
    "dim7": [(0, 0), (3, 2), (6, 4), (9, 6)],
    "m7b5": [(0, 0), (3, 2), (6, 4), (10, 6)],
    "5": [(0, 0), (7, 4)],
}
CHORD_SUFFIX = {"major": "", "minor": "m", "7": "7", "maj7": "maj7", "m7": "m7", "dim": "dim", "aug": "aug",
                "sus2": "sus2", "sus4": "sus4", "add9": "add9", "6": "6", "m6": "m6", "9": "9", "dim7": "dim7",
                "m7b5": "m7b5", "5": "5"}
CHORD_WORDS = {"major": "major", "minor": "minor", "7": "dominant seventh", "maj7": "major seventh",
               "m7": "minor seventh", "dim": "diminished", "aug": "augmented", "sus2": "suspended second",
               "sus4": "suspended fourth", "add9": "added ninth", "6": "sixth", "m6": "minor sixth", "9": "ninth",
               "dim7": "diminished seventh", "m7b5": "half-diminished", "5": "power chord"}
QUALITY_ALIASES = {
    "": "major", "maj": "major", "major": "major", "M": "major",
    "m": "minor", "min": "minor", "minor": "minor", "-": "minor",
    "7": "7", "dom7": "7", "dominant7": "7",
    "maj7": "maj7", "M7": "maj7", "major7": "maj7", "Δ": "maj7", "Δ7": "maj7",
    "m7": "m7", "min7": "m7", "minor7": "m7", "-7": "m7",
    "dim": "dim", "°": "dim", "o": "dim", "diminished": "dim",
    "aug": "aug", "+": "aug", "augmented": "aug",
    "sus2": "sus2", "sus4": "sus4", "sus": "sus4", "add9": "add9", "add2": "add9",
    "6": "6", "maj6": "6", "m6": "m6", "min6": "m6", "9": "9", "dom9": "9",
    "dim7": "dim7", "°7": "dim7", "o7": "dim7", "m7b5": "m7b5", "ø": "m7b5", "ø7": "m7b5", "min7b5": "m7b5",
    "5": "5", "power": "5",
}
INTERVAL_NAMES = {0: "root", 1: "minor 2nd", 2: "major 2nd", 3: "minor 3rd", 4: "major 3rd", 5: "perfect 4th",
                  6: "tritone", 7: "perfect 5th", 8: "minor 6th", 9: "major 6th", 10: "minor 7th",
                  11: "major 7th", 12: "octave", 14: "9th"}

MAJOR = [(0, 0), (2, 1), (4, 2), (5, 3), (7, 4), (9, 5), (11, 6)]
SCALES = {
    "major": MAJOR,
    "natural minor": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (8, 5), (10, 6)],
    "harmonic minor": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (8, 5), (11, 6)],
    "melodic minor": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (9, 5), (11, 6)],
    "major pentatonic": [(0, 0), (2, 1), (4, 2), (7, 4), (9, 5)],
    "minor pentatonic": [(0, 0), (3, 2), (5, 3), (7, 4), (10, 6)],
    "blues": [(0, 0), (3, 2), (5, 3), (6, 4), (7, 4), (10, 6)],
    "major blues": [(0, 0), (2, 1), (3, 2), (4, 2), (7, 4), (9, 5)],
    "dorian": [(0, 0), (2, 1), (3, 2), (5, 3), (7, 4), (9, 5), (10, 6)],
    "phrygian": [(0, 0), (1, 1), (3, 2), (5, 3), (7, 4), (8, 5), (10, 6)],
    "lydian": [(0, 0), (2, 1), (4, 2), (6, 3), (7, 4), (9, 5), (11, 6)],
    "mixolydian": [(0, 0), (2, 1), (4, 2), (5, 3), (7, 4), (9, 5), (10, 6)],
    "locrian": [(0, 0), (1, 1), (3, 2), (5, 3), (6, 4), (8, 5), (10, 6)],
}
SCALE_ALIASES = {"ionian": "major", "minor": "natural minor", "aeolian": "natural minor",
                 "pentatonic": "major pentatonic", "minor blues": "blues", "harmonic": "harmonic minor",
                 "melodic": "melodic minor"}
MAJOR_TRIADS = ["major", "minor", "minor", "major", "major", "minor", "dim"]
MINOR_TRIADS = ["minor", "dim", "major", "minor", "minor", "major", "major"]
MAJOR_NUMERALS = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
MINOR_NUMERALS = ["i", "ii°", "III", "iv", "v", "VI", "VII"]
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7}

FAMOUS = [
    ("Pop axis", "I V vi IV", "major", "Let It Be and a huge number of pop hits"),
    ("Sad pop", "vi IV I V", "major", "the same chords as the pop axis, starting on the minor, as in Zombie"),
    ("Three-chord trick", "I IV V", "major", "rock and roll, folk and punk, like La Bamba"),
    ("Fifties doo-wop", "I vi IV V", "major", "Stand By Me and 1950s ballads"),
    ("Jazz two-five-one", "ii7 V7 Imaj7", "major", "the cadence behind most jazz standards"),
    ("Circle progression", "vi ii V I", "major", "falling fifths, like the start of Fly Me to the Moon"),
    ("Twelve-bar blues", "I7 I7 I7 I7 IV7 IV7 I7 I7 V7 IV7 I7 V7", "major", "blues and early rock and roll"),
    ("Pachelbel's Canon", "I V vi iii IV I IV V", "major", "Pachelbel's Canon in D and many wedding songs"),
    ("Andalusian cadence", "i VII VI V", "minor", "flamenco, and Hit the Road Jack"),
    ("Mixolydian rock", "I bVII IV I", "major", "classic rock, like the long ending of Hey Jude"),
]

# Guitar shapes, low E to high E; x = not played. Keyed by (pitch class, quality) so C#/Db share a shape.
GUITAR_SHAPES = {
    ("C", "major"): "x32010", ("C", "maj7"): "x32000", ("C", "7"): "x32310", ("C", "add9"): "x32030",
    ("C", "sus2"): "x30033", ("C", "sus4"): "x33011", ("C", "minor"): "x35543", ("C#", "minor"): "x46654",
    ("C#", "major"): "x46664", ("D", "major"): "xx0232", ("D", "minor"): "xx0231", ("D", "7"): "xx0212",
    ("D", "maj7"): "xx0222", ("D", "m7"): "xx0211", ("D", "sus2"): "xx0230", ("D", "sus4"): "xx0233",
    ("Eb", "major"): "x68886", ("E", "major"): "022100", ("E", "minor"): "022000", ("E", "7"): "020100",
    ("E", "m7"): "022030", ("E", "maj7"): "021100", ("E", "sus4"): "022200", ("F", "major"): "133211",
    ("F", "maj7"): "xx3210", ("F", "minor"): "133111", ("F", "7"): "131211", ("F#", "major"): "244322",
    ("F#", "minor"): "244222", ("G", "major"): "320003", ("G", "7"): "320001", ("G", "maj7"): "320002",
    ("G", "sus4"): "330013", ("G", "minor"): "355333", ("G#", "major"): "466544", ("A", "major"): "x02220",
    ("A", "minor"): "x02210", ("A", "7"): "x02020", ("A", "m7"): "x02010", ("A", "maj7"): "x02120",
    ("A", "sus2"): "x02200", ("A", "sus4"): "x02230", ("Bb", "major"): "x13331", ("B", "major"): "x24442",
    ("B", "minor"): "x24432", ("B", "7"): "x21202", ("B", "m7"): "x20202",
}
GUITAR_STRINGS = [40, 45, 50, 55, 59, 64]  # E2 A2 D3 G3 B3 E4
TUNINGS = {
    "guitar": ["E2", "A2", "D3", "G3", "B3", "E4"],
    "bass": ["E1", "A1", "D2", "G2"],
    "ukulele": ["G4", "C4", "E4", "A4"],
    "violin": ["G3", "D4", "A4", "E5"],
    "viola": ["C3", "G3", "D4", "A4"],
    "cello": ["C2", "G2", "D3", "A3"],
}


def _tidy(text) -> str:
    """'c sharp' -> 'C#', 'B flat' -> 'Bb', unicode accidentals to ASCII."""
    t = re.sub(r"\s+", " ", str(text or "")).strip().replace("♯", "#").replace("♭", "b")
    t = re.sub(r"\s*-?\s*sharp\b", "#", t, flags=re.I)
    t = re.sub(r"\s*-?\s*flat\b", "b", t, flags=re.I)
    return t[:1].upper() + t[1:] if t else t


def split_note(text) -> tuple[str, int, str]:
    """'C#4' -> ('C#', 1, '4'): the spelled name, its pitch class and the rest of the text."""
    m = re.match(r"([A-Ga-g])(##|bb|#|b)?(.*)$", _tidy(text))
    if not m:
        raise ValueError(f"I don't know the note {str(text)[:20]!r}; try something like C, F# or Bb.")
    letter, acc = m.group(1).upper(), m.group(2) or ""
    return letter + acc, (NATURAL[letter] + ACCIDENTALS[acc]) % 12, m.group(3).strip()


def pitch_class(note: str) -> int:
    return split_note(note)[1]


def spell(root: str, semis: int, steps: int) -> str:
    """The note `semis` semitones and `steps` letters above root, e.g. spell('F', 10, 6) -> 'Eb'."""
    letter = LETTERS[(LETTERS.index(root[0]) + steps) % 7]
    diff = (pitch_class(root) + semis - NATURAL[letter]) % 12
    diff = diff - 12 if diff > 6 else diff
    acc = {v: k for k, v in ACCIDENTALS.items()}.get(diff)
    return letter + acc if acc is not None else SHARP_NAMES[(pitch_class(root) + semis) % 12]


def name_of(pc: int, flats: bool = False) -> str:
    return (FLAT_NAMES if flats else SHARP_NAMES)[pc % 12]


def spoken(name: str) -> str:
    """'C#m7' -> 'C sharp m7' so it reads aloud well."""
    return re.sub(r"([A-G])(#|b)(?=(\w?))", lambda m: m.group(1) + (" sharp" if m.group(2) == "#" else " flat")
                  + (" " if m.group(3) else ""), name)


def midi_name(midi: int, flats: bool = False) -> str:
    return f"{name_of(midi % 12, flats)}{midi // 12 - 1}"


def frequency(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def note_midi(text) -> int:
    """'A4' -> 69, 'C#5' -> 73. Middle C is C4."""
    name, pc, rest = split_note(text)
    if not re.fullmatch(r"-?\d", rest or ""):
        raise ValueError("Give the note with its octave, like A4 or C#5 (middle C is C4).")
    letter_pc = NATURAL[name[0]] + ACCIDENTALS[name[1:]]
    midi = (int(rest) + 1) * 12 + letter_pc
    if not 0 <= midi <= 127:
        raise ValueError("That note is out of range.")
    return midi


def from_frequency(hz: float) -> tuple[int, float]:
    """(nearest MIDI note, cents off it)."""
    if not 8 <= hz <= 13000:
        raise ValueError("Give a frequency between 8 and 13,000 Hz.")
    exact = 69 + 12 * math.log2(hz / 440.0)
    near = round(exact)
    return near, round((exact - near) * 100, 1)


# ---- chords ------------------------------------------------------------------------------------------

def parse_chord(text) -> tuple[str, str, str]:
    """'C#m7' / 'c sharp minor seven' / 'Bb/D' -> (root, quality, bass or '')."""
    t = _tidy(text)
    t = re.sub(r"\bseven(th)?\b", "7", t, flags=re.I)
    t = re.sub(r"\bnine\b", "9", t, flags=re.I)
    t = re.sub(r"\bsix\b", "6", t, flags=re.I)
    t = re.sub(r"\bchord\b", "", t, flags=re.I).strip()
    bass = ""
    if "/" in t:
        t, bass_text = t.split("/", 1)
        bass = split_note(bass_text.strip())[0]
    root, _, rest = split_note(t)
    key = rest.replace(" ", "")
    quality = QUALITY_ALIASES.get(key) or QUALITY_ALIASES.get(key.lower())
    if quality is None:
        low = key.lower().replace("dominant", "").replace("suspended", "sus").replace("diminished", "dim")
        low = low.replace("augmented", "aug").replace("major", "maj").replace("minor", "m")
        quality = QUALITY_ALIASES.get(low)
    if quality is None:
        raise ValueError(f"I don't know the chord {str(text)[:20]!r}. I know major, minor, 7, maj7, m7, dim, aug, "
                         "sus2, sus4, add9, 6, m6, 9, dim7, m7b5 and 5.")
    return root, quality, bass


def chord_name(root: str, quality: str, bass: str = "") -> str:
    return root + CHORD_SUFFIX[quality] + (f"/{bass}" if bass else "")


def chord_notes(root: str, quality: str) -> list[str]:
    return [spell(root, semis, steps) for semis, steps in CHORDS[quality]]


def chord_midi(root: str, quality: str, bass: str = "") -> list[int]:
    base = 48 + pitch_class(root)  # C3 to B3
    notes = [base + semis for semis, _ in CHORDS[quality]]
    if bass:
        low = 36 + pitch_class(bass)
        notes = [low] + [n for n in notes if n % 12 != low % 12]
    return notes


def chord(text) -> dict:
    root, quality, bass = parse_chord(text)
    return {"name": chord_name(root, quality, bass), "root": root, "quality": quality,
            "words": f"{root} {CHORD_WORDS[quality]}", "notes": chord_notes(root, quality),
            "intervals": [INTERVAL_NAMES.get(s, f"{s} semitones") for s, _ in CHORDS[quality]],
            "midi": chord_midi(root, quality, bass), "bass": bass}


def guitar_shape(text) -> dict:
    root, quality, _ = parse_chord(text)
    shape = GUITAR_SHAPES.get((SHARP_NAMES[pitch_class(root)], quality)) or \
        GUITAR_SHAPES.get((FLAT_NAMES[pitch_class(root)], quality))
    if not shape:
        known = sorted({f"{r}{CHORD_SUFFIX[q]}" for r, q in GUITAR_SHAPES})
        raise ValueError(f"I don't have a guitar shape for {chord_name(root, quality)}. I know: {', '.join(known)}.")
    frets = [None if c == "x" else int(c) for c in shape]
    midi = [GUITAR_STRINGS[i] + f for i, f in enumerate(frets) if f is not None]
    return {"name": chord_name(root, quality), "frets": frets, "shape": shape, "midi": midi,
            "notes": chord_notes(root, quality)}


def guitar_chord_names() -> list[str]:
    return sorted({f"{r}{CHORD_SUFFIX[q]}" for r, q in GUITAR_SHAPES})


# ---- keys and scales ---------------------------------------------------------------------------------

def parse_key(text) -> tuple[str, bool]:
    """'A minor' / 'Am' / 'F#' / 'E flat major' -> (tonic, is_minor)."""
    t = _tidy(text or "C")
    t = re.sub(r"\s*(major|maj)$", "", t, flags=re.I)
    minor = bool(re.search(r"(\s*minor|\s*min|m)$", t))
    t = re.sub(r"(\s*minor|\s*min|m)$", "", t)
    tonic, _, rest = split_note(t)
    if rest:
        raise ValueError(f"I don't know the key {str(text)[:20]!r}; try C, A minor or F# major.")
    return tonic, minor


def key_name(tonic: str, minor: bool) -> str:
    return f"{tonic} {'minor' if minor else 'major'}"


def scale_type(text) -> str:
    t = re.sub(r"\s+", " ", str(text or "major").lower().replace("scale", "").replace("mode", "")).strip()
    t = SCALE_ALIASES.get(t, t)
    if t not in SCALES:
        raise ValueError(f"I know these scales: {', '.join(SCALES)}.")
    return t


def scale(tonic_text, kind="major") -> dict:
    tonic = split_note(_tidy(tonic_text))[0]
    kind = scale_type(kind)
    steps = SCALES[kind]
    base = 60 + pitch_class(tonic)
    base -= 12 if base > 65 else 0
    midi = [base + s for s, _ in steps] + [base + 12]
    return {"tonic": tonic, "type": kind, "name": f"{tonic} {kind}",
            "notes": [spell(tonic, s, n) for s, n in steps], "midi": midi,
            "pattern": _step_pattern([s for s, _ in steps] + [12])}


def _step_pattern(semis: list[int]) -> str:
    words = {1: "H", 2: "W", 3: "W+H", 4: "2W"}
    return " ".join(words.get(b - a, str(b - a)) for a, b in zip(semis, semis[1:]))


def diatonic(tonic: str, minor: bool) -> list[dict]:
    """The seven triads of a key, with numerals."""
    steps = SCALES["natural minor" if minor else "major"]
    qualities, numerals = (MINOR_TRIADS, MINOR_NUMERALS) if minor else (MAJOR_TRIADS, MAJOR_NUMERALS)
    out = []
    for (semis, n), quality, numeral in zip(steps, qualities, numerals):
        root = spell(tonic, semis, n)
        out.append({"numeral": numeral, "name": chord_name(root, quality), "notes": chord_notes(root, quality),
                    "midi": chord_midi(root, quality)})
    return out


def signature(tonic: str, minor: bool) -> str:
    major_tonic = spell(tonic, 3, 2) if minor else tonic
    notes = [spell(major_tonic, s, n) for s, n in MAJOR]
    sharps, flats = sum(x.count("#") for x in notes), sum(x.count("b") for x in notes)
    if not sharps and not flats:
        return "no sharps or flats"
    if sharps:
        return f"{sharps} sharp{'s' if sharps > 1 else ''}"
    return f"{flats} flat{'s' if flats > 1 else ''}"


CIRCLE_MAJORS = ["C", "G", "D", "A", "E", "B", "F#", "Db", "Ab", "Eb", "Bb", "F"]
CIRCLE_MINORS = ["A", "E", "B", "F#", "C#", "G#", "Eb", "Bb", "F", "C", "G", "D"]


def circle() -> list[dict]:
    keys = []
    for major, minor in zip(CIRCLE_MAJORS, CIRCLE_MINORS):
        keys.append({"major": major, "minor": minor + "m", "signature": signature(major, False),
                     "major_chords": diatonic(major, False), "minor_chords": diatonic(minor, True)})
    return keys


# ---- progressions and transposing --------------------------------------------------------------------

def numeral_chord(token: str, tonic: str, minor: bool) -> dict:
    m = re.fullmatch(r"(b|#|♭|♯)?(vii|iii|vi|iv|ii|v|i)(.*)", token, flags=re.I)
    if not m:
        raise ValueError(f"{token[:12]!r} isn't a roman numeral; use I to VII, lower case for minor, like I V vi IV.")
    acc, roman, suffix = (m.group(1) or "").replace("♭", "b").replace("♯", "#"), m.group(2), m.group(3)
    degree = ROMAN[roman.lower()] - 1
    semis, steps = SCALES["natural minor" if minor else "major"][degree]
    semis += {"b": -1, "#": 1}.get(acc, 0)
    root = spell(tonic, semis, steps)
    upper = roman.isupper()
    s = suffix.replace("°", "dim").replace("ø", "m7b5").replace("o", "dim").replace("+", "aug")
    if s in ("dim", "dim7", "m7b5", "aug", "sus2", "sus4", "add9", "maj7", "5"):
        quality = s
    elif s == "7":
        quality = "7" if upper else "m7"
    elif s in ("", "6", "9"):
        quality = {"": "major", "6": "6", "9": "9"}[s] if upper else {"": "minor", "6": "m6", "9": "m7"}[s]
    else:
        raise ValueError(f"I don't understand {token[:12]!r}; try numerals like ii7, V7, Imaj7 or vii°.")
    return {"numeral": token, "name": chord_name(root, quality), "notes": chord_notes(root, quality),
            "midi": chord_midi(root, quality)}


def progression(numerals: str, key_text: str = "C") -> dict:
    tonic, minor = parse_key(key_text)
    tokens = [t for t in re.split(r"[\s,\-–—|]+", str(numerals or "")) if t][:32]
    if not tokens:
        raise ValueError("Give the numerals, like I V vi IV.")
    return {"key": key_name(tonic, minor), "chords": [numeral_chord(t, tonic, minor) for t in tokens]}


CHORD_TOKEN = re.compile(r"(?<![\w#/])([A-G])(#|b|♯|♭)?((?:maj|min|m|dim|aug|sus|add|M|°|ø|\+)?[0-9]*(?:b5|#5|b9|#9)?)"
                         r"(?:/([A-G])(#|b|♯|♭)?)?(?![\w#])")


def transpose(text: str, semitones: int) -> tuple[str, list[str]]:
    """Every chord in text moved by semitones; (new text, new chord names). Spelled with flats or sharps to suit."""
    found = list(CHORD_TOKEN.finditer(text or ""))
    if not found:
        raise ValueError("I couldn't find any chords in that, like G D Em C.")
    first = found[0]
    first_pc = (pitch_class(first.group(1) + ascii_acc(first.group(2))) + semitones) % 12
    is_minor = first.group(3).startswith(("m", "min")) and not first.group(3).startswith("maj")
    flats = (first_pc in (5, 10, 3, 8, 1)) if not is_minor else (first_pc in (2, 7, 0, 5, 10, 3))

    def move(letter, acc):
        return name_of(pitch_class(letter + ascii_acc(acc)) + semitones, flats)

    def sub(m):
        out = move(m.group(1), m.group(2)) + m.group(3)
        return out + (f"/{move(m.group(4), m.group(5))}" if m.group(4) else "")

    new = CHORD_TOKEN.sub(sub, text)
    return new, [sub(m) for m in found]


def ascii_acc(acc) -> str:
    return {"♯": "#", "♭": "b"}.get(acc or "", acc or "")


def interval_between(from_key: str, to_key: str) -> int:
    """Semitones to move from one key to another, the short way (-5 to +6)."""
    diff = (pitch_class(parse_key(to_key)[0]) - pitch_class(parse_key(from_key)[0])) % 12
    return diff - 12 if diff > 6 else diff


def playable(name: str) -> dict:
    """A chord name found in a song -> {name, notes, midi}; unknown extensions fall back to the plain triad."""
    try:
        c = chord(name)
    except ValueError:
        root, _, rest = split_note(name)
        c = chord(root + ("m" if rest.startswith("m") and not rest.startswith("maj") else ""))
    return {"name": name, "notes": c["notes"], "midi": c["midi"]}


# ---- quizzes and tuning ------------------------------------------------------------------------------

def staff_notes(clef: str) -> list[dict]:
    """Natural notes for a note-reading quiz: name, midi and position (0 = bottom line, 1 = first space...)."""
    low, high, bottom = (("C4", "A5", "E4") if clef == "treble" else ("E2", "C4", "G2"))

    def diatonic_index(note):
        return int(note[1:]) * 7 + LETTERS.index(note[0])

    out = []
    for i in range(diatonic_index(low), diatonic_index(high) + 1):
        letter, octave = LETTERS[i % 7], i // 7
        name = f"{letter}{octave}"
        out.append({"name": name, "letter": letter, "midi": note_midi(name), "pos": i - diatonic_index(bottom)})
    return out


def tuning(instrument: str) -> list[dict]:
    notes = TUNINGS.get(instrument)
    if not notes:
        raise ValueError(f"I have tuning notes for: {', '.join(TUNINGS)}.")
    return [{"name": n, "midi": note_midi(n), "freq": round(frequency(note_midi(n)), 2)} for n in notes]
