import asyncio
from datetime import datetime

import pytest

import homestore
import screen
import studio_learn as learn
import studio_log as log
import studio_play as play
import studio_theory as theory
import tools
from config import Settings


@pytest.fixture
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(homestore, "now", lambda: datetime(2026, 9, 28, 18, 0))  # a Monday
    return Settings(memory_dir=str(tmp_path))


def instrument(s, **args):
    return play.run_tool("music_instrument", args, s)


def theory_tool(**args):
    return learn.run_tool("music_theory", args, Settings())


def practice(s, **args):
    return log.run_tool("music_practice", args, s)


# ---- the theory library -------------------------------------------------------------------------------

def test_chords_are_spelled_properly():
    assert theory.chord("C#m7")["notes"] == ["C#", "E", "G#", "B"]
    assert theory.chord("c sharp minor seven")["name"] == "C#m7"
    assert theory.chord("F7")["notes"] == ["F", "A", "C", "Eb"]
    assert theory.chord("Bbmaj7")["notes"] == ["Bb", "D", "F", "A"]
    assert theory.chord("Bdim")["notes"] == ["B", "D", "F"]
    assert theory.chord("Caug")["notes"] == ["C", "E", "G#"]
    assert theory.chord("Dsus2")["notes"] == ["D", "E", "A"]
    assert theory.chord("Gsus4")["notes"] == ["G", "C", "D"]
    assert theory.chord("Cadd9")["notes"] == ["C", "E", "G", "D"]
    assert theory.chord("Am")["midi"] == [57, 60, 64]
    assert theory.chord("E flat major")["name"] == "Eb"
    with pytest.raises(ValueError):
        theory.chord("Hm")
    with pytest.raises(ValueError):
        theory.chord("Cblorp")


def test_scales_and_keys():
    assert theory.scale("F")["notes"] == ["F", "G", "A", "Bb", "C", "D", "E"]
    assert theory.scale("C#")["notes"][2] == "E#"
    assert theory.scale("A", "minor pentatonic")["notes"] == ["A", "C", "D", "E", "G"]
    assert theory.scale("A", "blues")["notes"] == ["A", "C", "D", "Eb", "E", "G"]
    assert theory.scale("D", "dorian mode")["notes"] == ["D", "E", "F", "G", "A", "B", "C"]
    assert theory.parse_key("F# minor") == ("F#", True)
    assert theory.signature("D", False) == "2 sharps" and theory.signature("D", True) == "1 flat"
    with pytest.raises(ValueError):
        theory.scale("C", "martian")


def test_progressions_transpose_and_frequencies():
    assert [c["name"] for c in theory.progression("I V vi IV", "G")["chords"]] == ["G", "D", "Em", "C"]
    assert [c["name"] for c in theory.progression("i VII VI V", "A minor")["chords"]] == ["Am", "G", "F", "E"]
    assert [c["name"] for c in theory.progression("ii7 V7 Imaj7 vii°", "C")["chords"]] == ["Dm7", "G7", "Cmaj7", "Bdim"]
    assert theory.progression("I bVII IV", "F")["chords"][1]["name"] == "Eb"
    assert theory.transpose("G D Em C/B", 2) == ("A E F#m D/C#", ["A", "E", "F#m", "D/C#"])
    assert theory.transpose("C G Am F", -2)[1] == ["Bb", "F", "Gm", "Eb"]
    assert theory.note_midi("A4") == 69 and theory.note_midi("C4") == 60
    assert theory.from_frequency(445) == (69, 19.6)
    assert round(theory.frequency(60), 2) == 261.63
    assert theory.spoken("C#m7 Bb") == "C sharp m7 B flat"
    assert len(theory.GUITAR_SHAPES) >= 40
    with pytest.raises(ValueError):
        theory.progression("I Q IV", "C")


# ---- music_instrument ---------------------------------------------------------------------------------

def test_piano_and_tuner_cards(s):
    out = instrument(s, action="piano", octave=4)
    assert out.card["kind"] == "studio-piano" and out.card["data"]["start"] == 60
    with pytest.raises(ValueError):
        instrument(s, action="piano", octave=9)
    out = instrument(s, action="tuner")
    assert [t["label"] for t in out.card["data"]["tones"]] == ["E2", "A2", "D3", "G3", "B3", "E4"]
    assert out == "Here are the guitar tuning notes: E, A, D, G, B, E."
    assert instrument(s, action="tuner", instrument="violin").card["data"]["tones"][2]["freq"] == 440.0
    assert [t["label"] for t in instrument(s, action="tuner", instrument="ukulele").card["data"]["tones"]] == \
        ["G4", "C4", "E4", "A4"]


def test_drum_machine_loads_saved_patterns(s):
    out = instrument(s, action="drum_machine")
    assert out.card["kind"] == "studio-drums" and out.card["data"]["start"]["kick"].startswith("x")
    assert out.card["data"]["saved"] == {}
    practice(s, action="pattern_save", name="Funky", bpm=96,
             pattern="kick x..x..x.x....... snare ....x.......x... hat xxxxxxxxxxxxxxxx clap ................")
    out = instrument(s, action="drum_machine", pattern="funk", bpm=120)
    assert out == "Here's the drum machine with Funky loaded."
    assert out.card["data"]["start"]["name"] == "Funky" and out.card["data"]["start"]["bpm"] == 120
    assert "Funky" in out.card["data"]["saved"]
    with pytest.raises(ValueError):
        instrument(s, action="drum_machine", pattern="nope")


def test_tap_circle_and_quizzes(s):
    assert instrument(s, action="tap_tempo").card["kind"] == "studio-tap"
    out = instrument(s, action="circle_of_fifths", key="E minor")
    keys = out.card["data"]["keys"]
    assert out.card["kind"] == "studio-circle" and len(keys) == 12
    assert keys[out.card["data"]["selected"]]["minor"] == "Em" and out.card["data"]["minor"] is True
    assert [c["name"] for c in keys[1]["major_chords"]] == ["G", "Am", "Bm", "C", "D", "Em", "F#dim"]
    ear = instrument(s, action="ear_training", level="hard")
    assert ear.card["kind"] == "studio-ear" and len(ear.card["data"]["intervals"]) == 12
    quiz = instrument(s, action="note_quiz", clef="bass")
    notes = quiz.card["data"]["notes"]
    assert quiz.card["kind"] == "studio-staff" and notes[0]["name"] == "E2" and notes[0]["pos"] == -2
    assert instrument(s, action="note_quiz").card["data"]["clef"] == "treble"
    with pytest.raises(ValueError):
        instrument(s, action="kazoo")


# ---- music_theory -------------------------------------------------------------------------------------

def test_chord_scale_and_guitar_cards():
    out = theory_tool(action="chord", chord="Cmaj7")
    assert out == "Cmaj7 is C, E, G, B." and out.card["kind"] == "studio-chord"
    assert out.card["data"]["mode"] == "chord" and out.card["data"]["midi"] == [48, 52, 55, 59]
    out = theory_tool(action="scale", key="Bb", scale="major")
    assert out == "B flat major: B flat, C, D, E flat, F, G, A." and out.card["kind"] == "studio-scale"
    assert out.card["data"]["facts"][1] == ["Steps", "W W H W W W H"]
    out = theory_tool(action="guitar_chord", chord="G C D")
    assert [x["name"] for x in out.card["data"]["shapes"]] == ["G", "C", "D"]
    assert out.card["kind"] == "studio-guitar"
    one = theory_tool(action="guitar_chord", chord="F sharp minor")
    assert one.card["data"]["shapes"][0]["shape"] == "244222"
    with pytest.raises(ValueError):
        theory_tool(action="guitar_chord", chord="Gm7b5")


def test_progression_cards():
    out = theory_tool(action="progression", numerals="I V vi IV", key="D")
    assert out == "In D major: D, A, Bm, G." or out == "In D major: D A Bm G."
    assert out.card["kind"] == "studio-chords" and len(out.card["data"]["chords"]) == 4
    famous = theory_tool(action="progression", numerals="twelve-bar blues", key="A")
    assert famous.card["title"] == "Twelve-bar blues in A major"
    assert famous.card["data"]["chords"][4]["name"] == "D7"
    andalusian = theory_tool(action="progression", numerals="Andalusian cadence")
    assert [c["name"] for c in andalusian.card["data"]["chords"]] == ["Am", "G", "F", "E"]
    listed = theory_tool(action="famous_progressions")
    assert listed.card["kind"] == "list" and len(listed.card["items"]) == 10
    assert listed.card["items"][0]["say"] == "Play the Pop axis progression in C."


def test_transpose_and_note_info():
    out = theory_tool(action="transpose", chords="G D Em C", semitones=2)
    assert out == "Moved up 2 semitones: A E F sharp m D."
    assert out.card["text"] == "A E F#m D" and out.card["data"]["before"] == ["G", "D", "Em", "C"]
    assert out.card["data"]["chords"][2]["notes"] == ["F#", "A", "C#"]
    down = theory_tool(action="transpose", chords="Am F C G", to_key="E minor")
    assert down.card["text"] == "Em C G D" and down.startswith("Moved down 5 semitones")
    with pytest.raises(ValueError):
        theory_tool(action="transpose", chords="la la la")
    note = theory_tool(action="note_info", note="C4")
    assert note == "C4 is MIDI 60, 261.63 hertz." and note.card["kind"] == "studio-tuner"
    hz = theory_tool(action="note_info", frequency=445)
    assert hz == "445 hertz is nearest A4, MIDI 69, +19.6 cents off."
    assert theory_tool(action="note_info", midi=61).card["data"]["facts"][0] == ["Note", "C#4 / Db4"]
    with pytest.raises(ValueError):
        theory_tool(action="note_info")


# ---- music_practice -----------------------------------------------------------------------------------

def test_practice_log_week_and_streak(s):
    practice(s, action="log", instrument="Guitar", minutes=20, what="scales", day="2026-09-26")
    practice(s, action="log", instrument="guitar", minutes=15, day="yesterday")
    out = practice(s, action="log", instrument="piano", minutes=30, what="Moonlight Sonata")
    assert out == "Logged 30 minutes of piano. 30 minutes that day; practice streak 3 days."
    week = practice(s, action="week")
    assert week == "65 minutes of practice in the last 7 days: 35 minutes of guitar, 30 minutes of piano. Streak 3 days."
    assert week.card["kind"] == "chart" and week.card["chart"]["values"][-3:] == [20.0, 15.0, 30.0]
    assert week.card["chart"]["labels"][-1] == "Mon"
    with pytest.raises(ValueError):
        practice(s, action="log", instrument="drums", minutes=0)


def test_songs_to_learn(s):
    assert practice(s, action="songs").card["kind"] == "text"
    assert practice(s, action="song_add", title="Wonderwall", artist="Oasis", notes="capo 2") == \
        "Added Wonderwall to your songs, marked to learn."
    practice(s, action="song_add", title="Blackbird", status="learning")
    with pytest.raises(ValueError):
        practice(s, action="song_add", title="wonderwall")
    assert practice(s, action="song_update", title="wonder", status="can play") == "Wonderwall is now can play."
    table = practice(s, action="songs")
    assert table.card["kind"] == "table" and table.card["rows"][0][0] == "Blackbird"
    assert table.card["rows"][1] == ["Wonderwall", "Oasis", "can play", "capo 2"]
    assert practice(s, action="song_remove", title="Blackbird").startswith("Remove Blackbird")
    assert len(practice(s, action="songs").card["rows"]) == 2
    assert practice(s, action="song_remove", title="Blackbird", confirmed=True) == "Removed Blackbird."
    assert len(practice(s, action="songs").card["rows"]) == 1


def test_drum_patterns_save_list_delete(s):
    line = ('Save my drum pattern "Rock two" at 100 BPM: kick x.......x.x..... snare ....x.......x... '
            'hat x.x.x.x.x.x.x.x. clap ................')
    assert practice(s, action="pattern_save", name="Rock two", bpm=100, pattern=line) == \
        "Saved drum pattern Rock two at 100 BPM, 13 hits."
    saved = log.patterns(s)["Rock two"]
    assert saved["snare"] == "....x.......x..." and saved["clap"] == "." * 16
    with pytest.raises(ValueError):
        practice(s, action="pattern_save", name="Bad", pattern="kick x...")
    listed = practice(s, action="patterns")
    assert listed.card["items"][0]["say"] == "Load my drum pattern Rock two in the drum machine."
    assert practice(s, action="pattern_delete", name="rock").startswith("Delete the drum pattern Rock two?")
    assert practice(s, action="pattern_delete", name="rock", confirmed=True) == "Deleted the drum pattern Rock two."
    assert practice(s, action="patterns").card["kind"] == "text"


def test_registered_and_popups_reach_the_page(s):
    names = {t["name"] for t in tools.client_tool_definitions(Settings())}
    assert {"music_instrument", "music_theory", "music_practice"} <= names
    assert {"studio-piano", "studio-drums", "studio-chords", "studio-guitar"} <= screen.EXTRA_KINDS
    sent = []

    async def page(msg):
        sent.append(msg)

    async def go():
        return await tools.run_tool("music_theory", {"action": "chord", "chord": "Am"}, Settings(), None, page)

    assert asyncio.run(go()) == "Am is A, C, E."
    assert sent[0]["type"] == "popup" and sent[0]["card"]["kind"] == "studio-chord"
