"""Repurpose part 1: subtitle files (SRT and VTT) timed from word pace, subtitle checks and shifts, on-screen text per
beat, and YouTube chapters and descriptions.

Everything is worked out on the PC from the user's own script. Subtitle files are saved in memory/repurpose/subtitles.
Nothing is posted or sent anywhere, and no video, picture or voice is made.
"""

import re
import textwrap

import homestore as hs
import memory
import repurpose_store as store
import screen
from config import Settings

screen.EXTRA_KINDS.add("repurpose-timeline")

ACTIONS = ["srt_make", "vtt_make", "subtitle_list", "subtitle_show", "subtitle_shift", "subtitle_check",
           "subtitle_to_text", "onscreen_lines", "chapters_make", "chapters_from_script", "description_build"]
LINE = 42
MAX_CPS = 20
FILLER = {"the", "a", "an", "just", "really", "very", "actually", "basically", "literally", "so", "that", "and",
          "then", "well", "kind", "of", "like"}
TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})\s*-->\s*(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})")


# ---- Timing ----------------------------------------------------------------------------------------

def stamp(ms: int, comma: bool = True) -> str:
    ms = max(0, int(round(ms)))
    h, rest = divmod(ms, 3_600_000)
    m, rest = divmod(rest, 60_000)
    s, milli = divmod(rest, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{',' if comma else '.'}{milli:03d}"


def clock(seconds: float) -> str:
    seconds = int(seconds)
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _pause(word: str) -> float:
    return 0.35 if re.search(r"[.!?]$", word) else 0.15 if re.search(r"[,;:]$", word) else 0.0


def make_cues(text: str, wpm: float, max_chars: int = LINE, per_cue: int = 0, offset: float = 0.0) -> list[tuple[int, int, str]]:
    """(start_ms, end_ms, text) cues; a cue ends at a sentence end, when two lines are full or after per_cue words."""
    per_word = 60.0 / wpm
    cues, chunk, clock_s = [], [], offset
    start = clock_s

    def flush(pause: float) -> None:
        nonlocal chunk, clock_s, start
        if not chunk:
            return
        end = start + max(1.0, len(chunk) * per_word)
        lines = textwrap.wrap(" ".join(chunk), max_chars) or [" ".join(chunk)]
        cues.append((int(start * 1000), int(end * 1000), "\n".join(lines)))
        clock_s = end + pause
        start = clock_s
        chunk = []

    for word in text.split():
        if chunk and (len(" ".join(chunk + [word])) > max_chars * 2 or (per_cue and len(chunk) >= per_cue)):
            flush(0.0)
        chunk.append(word)
        if _pause(word) >= 0.35:
            flush(_pause(word))
    flush(0.0)
    return cues


def render(cues, vtt: bool = False) -> str:
    rows = ["WEBVTT", ""] if vtt else []
    for i, (a, b, t) in enumerate(cues, 1):
        rows += ([] if vtt else [str(i)]) + [f"{stamp(a, not vtt)} --> {stamp(b, not vtt)}", t, ""]
    return "\n".join(rows)


def parse(text: str) -> list[tuple[int, int, str]]:
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "").strip()):
        lines = block.split("\n")
        for i, line in enumerate(lines):
            m = TIME.search(line)
            if m:
                g = [int(x or 0) for x in m.groups()]
                a = ((g[0] * 60 + g[1]) * 60 + g[2]) * 1000 + int(m.group(4).ljust(3, "0"))
                b = ((g[4] * 60 + g[5]) * 60 + g[6]) * 1000 + int(m.group(8).ljust(3, "0"))
                cues.append((a, b, "\n".join(lines[i + 1:]).strip()))
                break
    if not cues:
        raise ValueError("I can't find any subtitle timings in that.")
    return cues


def _subs(settings: Settings):
    return store.folder(settings, "subtitles")


def _file(settings: Settings, name: str):
    folder = _subs(settings)
    want = hs.need(name, "subtitle file", 80).lower()
    files = sorted(folder.glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for test in (lambda p: p.name.lower() == want, lambda p: p.stem.lower() == want, lambda p: want in p.name.lower()):
        found = [p for p in files if test(p)]
        if found:
            return found[0]
    raise ValueError(f"I can't find a subtitle file called {name}.")


def _load(settings: Settings, args: dict):
    if args.get("text") and TIME.search(str(args["text"])):
        return None, parse(str(args["text"]))
    path = _file(settings, args.get("name"))
    return path, parse(path.read_text(encoding="utf-8"))


def _timeline(title: str, cues, note: str = "") -> dict:
    total = max((c[1] for c in cues), default=0) / 1000
    return screen.card("repurpose-timeline", title, "repurpose-timeline",
                       data={"total": round(total, 1), "cues": [{"start": round(a / 1000, 1), "end": round(b / 1000, 1),
                                                                 "text": t.replace("\n", " ")} for a, b, t in cues[:80]]},
                       text=note)


# ---- Subtitle files --------------------------------------------------------------------------------

def _make(settings: Settings, args: dict, vtt: bool) -> screen.Shown:
    text = store.script(args)
    name = memory.safe_name(hs.need(args.get("name"), "subtitle file name", 60), "file name")
    cues = make_cues(text, store.wpm(args), int(hs.number(args.get("max_chars") or LINE, "line length", 15, 80)),
                     int(hs.number(args.get("words_per_cue") or 0, "words per cue", 0, 20)),
                     hs.number(args.get("offset") or 0, "start offset", 0, 3600))
    path = _subs(settings) / f"{name}.{'vtt' if vtt else 'srt'}"
    path.write_text(render(cues, vtt), encoding="utf-8")
    seconds = cues[-1][1] / 1000
    return screen.Shown(f"Saved {path.name}: {len(cues)} subtitles over {clock(seconds)}.",
                        screen.file_card(settings, path, [{"label": "Check it", "say": f"Check the subtitles {path.name}."}]))


def srt_make(settings: Settings, args: dict) -> screen.Shown:
    return _make(settings, args, False)


def vtt_make(settings: Settings, args: dict) -> screen.Shown:
    return _make(settings, args, True)


def subtitle_list(settings: Settings, args: dict) -> screen.Shown | str:
    files = sorted(_subs(settings).glob("*.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return "You haven't made any subtitle files yet."
    items = [{"label": f"{p.name} ({p.stat().st_size // 1000 or 1} KB)", "say": f"Show the subtitles {p.name}."}
             for p in files]
    return screen.Shown(f"{len(files)} subtitle file{'s' if len(files) != 1 else ''}.",
                        screen.card("list", "Subtitle files", "repurpose-subs", items=items))


def subtitle_show(settings: Settings, args: dict) -> screen.Shown:
    path, cues = _load(settings, args)
    title = path.name if path else "Subtitles"
    return screen.Shown(f"{len(cues)} subtitles, {clock(cues[-1][1] / 1000)} long.", _timeline(title, cues))


def subtitle_shift(settings: Settings, args: dict) -> str:
    path = _file(settings, args.get("name"))
    seconds = hs.number(args.get("seconds"), "shift in seconds", -3600, 3600)
    cues = [(max(0, a + int(seconds * 1000)), max(0, b + int(seconds * 1000)), t) for a, b, t in
            parse(path.read_text(encoding="utf-8"))]
    path.write_text(render(cues, path.suffix.lower() == ".vtt"), encoding="utf-8")
    return f"Shifted every subtitle in {path.name} by {seconds:+g} seconds."


def subtitle_check(settings: Settings, args: dict) -> screen.Shown:
    path, cues = _load(settings, args)
    rows = []
    for i, (a, b, t) in enumerate(cues, 1):
        dur = max((b - a) / 1000, 0.001)
        lines = t.split("\n")
        cps = len(t.replace("\n", " ")) / dur
        problems = []
        if cps > MAX_CPS:
            problems.append(f"too fast ({cps:.0f} chars/sec)")
        if len(lines) > 2:
            problems.append("more than 2 lines")
        if max(len(x) for x in lines) > LINE:
            problems.append(f"line over {LINE} characters")
        if dur < 1:
            problems.append("on screen under 1 second")
        if dur > 7:
            problems.append("on screen over 7 seconds")
        if i < len(cues) and b > cues[i][0]:
            problems.append("overlaps the next one")
        if problems:
            rows.append([str(i), clock(a / 1000), "; ".join(problems)])
    if not rows:
        return screen.Shown(f"All {len(cues)} subtitles look fine.",
                            screen.card("text", "Subtitle check", "repurpose-subcheck", text=f"All {len(cues)} subtitles pass."))
    return screen.Shown(f"{len(rows)} of {len(cues)} subtitles need a look.",
                        screen.card("table", "Subtitle check", "repurpose-subcheck", columns=["#", "At", "Problem"], rows=rows))


def subtitle_to_text(settings: Settings, args: dict) -> screen.Shown:
    path, cues = _load(settings, args)
    text = " ".join(t.replace("\n", " ") for _, _, t in cues)
    return screen.Shown(f"{store.words(text)} words of plain text from the subtitles.",
                        screen.card("text", "Transcript", "repurpose-transcript", text=text))


# ---- On-screen text --------------------------------------------------------------------------------

def _punch(sentence: str, limit: int = 6) -> str:
    kept = [w for w in re.findall(r"[\w'’£$%.-]+", sentence) if w.lower() not in FILLER] or sentence.split()
    return " ".join(kept[:limit]).upper()


def onscreen_lines(settings: Settings, args: dict) -> screen.Shown:
    text = store.script(args)
    per_word = 60.0 / store.wpm(args)
    clock_s, cues, rows = 0.0, [], []
    for i, sentence in enumerate(store.sentences(text), 1):
        dur = max(1.5, store.words(sentence) * per_word)
        line = _punch(sentence)
        cues.append((int(clock_s * 1000), int((clock_s + dur) * 1000), line))
        rows.append([str(i), clock(clock_s), line])
        clock_s += dur + 0.2
    return screen.Shown(f"{len(rows)} on-screen lines over {clock(clock_s)}. Rewrite any that need a better punch.",
                        _timeline("On-screen text per beat", cues, "Auto-shortened: swap in your own punchier wording."))


# ---- Chapters and description ----------------------------------------------------------------------

def _seconds(text: str) -> int:
    parts = [int(p) for p in text.split(":")]
    total = 0
    for p in parts:
        total = total * 60 + p
    return total


def _entries(args: dict) -> list[tuple[int, str]]:
    raw = args.get("chapters")
    lines = raw if isinstance(raw, list) else str(raw or args.get("text") or "").splitlines()
    out = []
    for line in lines:
        m = re.match(r"\s*(\d+(?::\d{2}){1,2})\s*[-–:]?\s*(.+)", str(line))
        if m:
            out.append((_seconds(m.group(1)), hs.clean(m.group(2), 100)))
    if not out:
        raise ValueError("Give me the chapters like '0:00 Intro', one per line.")
    return sorted(out)


def _chapter_problems(entries) -> list[str]:
    problems = []
    if entries[0][0] != 0:
        problems.append("The first chapter must start at 0:00.")
    if len(entries) < 3:
        problems.append("YouTube needs at least 3 chapters.")
    for (a, _), (b, name) in zip(entries, entries[1:]):
        if b - a < 10:
            problems.append(f"'{name}' is under 10 seconds after the chapter before it.")
    return problems


def chapters_make(settings: Settings, args: dict) -> screen.Shown:
    entries = _entries(args)
    problems = _chapter_problems(entries)
    lines = [f"{clock(s)} {n}" for s, n in entries]
    text = "\n".join(lines + ([""] + ["Fix: " + p for p in problems] if problems else []))
    spoken = "Chapters look valid for YouTube." if not problems else f"{len(problems)} chapter problem{'s' if len(problems) != 1 else ''}."
    return screen.Shown(spoken, screen.card("text", "Chapter markers", "repurpose-chapters", text=text))


def chapters_from_script(settings: Settings, args: dict) -> screen.Shown:
    text = store.script(args)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    count = int(hs.number(args.get("count") or 5, "chapter count", 3, 20))
    if len(blocks) < count:
        blocks = store.sentences(text)
    size = max(1, -(-len(blocks) // count))
    groups = [blocks[i:i + size] for i in range(0, len(blocks), size)]
    per_word, at, rows = 60.0 / store.wpm(args), 0.0, []
    for group in groups:
        rows.append(f"{clock(at)} {' '.join(group[0].split()[:5]).rstrip('.,;:!?')}")
        at += store.words(" ".join(group)) * per_word
    body = "\n".join(rows)
    return screen.Shown(f"{len(rows)} chapter markers suggested. Rename them.",
                        screen.card("text", "Suggested chapters", "repurpose-chapters", text=body))


def description_build(settings: Settings, args: dict) -> screen.Shown:
    title = hs.need(args.get("title"), "video title", 100)
    summary = hs.clean(args.get("summary"), 600) or "Write one or two lines on what the video gives the viewer."
    parts = [summary]
    if args.get("chapters"):
        entries = _entries(args)
        parts.append("Chapters:\n" + "\n".join(f"{clock(s)} {n}" for s, n in entries))
    links = [hs.clean(x, 200) for x in (args.get("links") or []) if hs.clean(x)]
    if links:
        parts.append("Links:\n" + "\n".join(links))
    tags = [t for t in (hs.clean(x, 40).lstrip("#").replace(" ", "") for x in (args.get("hashtags") or [])) if t]
    if tags:
        parts.append(" ".join("#" + t for t in tags[:3]))
    body = "\n\n".join(parts)
    folder = store.folder(settings, "descriptions")
    path = folder / f"{memory.safe_name(title, 'title')[:60]}.txt"
    path.write_text(body, encoding="utf-8")
    return screen.Shown(f"Description saved as {path.name}, {store.words(body)} words.", screen.file_card(settings, path))


# ---- Tool ------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    return [{
        "name": "repurpose_subtitles",
        "description": "Subtitle files and video description helpers from a script (text only; no video is made). "
                       "action: srt_make / vtt_make (name, text, wpm, words_per_cue, max_chars, offset) = subtitle "
                       "file timed from speaking pace, saved in memory; subtitle_list; subtitle_show (name) = "
                       "timeline; subtitle_shift (name, seconds); subtitle_check (name) = too fast, too long, "
                       "overlaps; subtitle_to_text (name); onscreen_lines (text, wpm) = a short on-screen line "
                       "per beat with times; chapters_make (chapters as '0:00 Intro' lines) = YouTube chapter "
                       "check; chapters_from_script (text, count); description_build (title, summary, chapters, "
                       "links, hashtags) = saved video description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Subtitle file name."},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "text": {"type": "string", "description": "The script, or subtitle text to check."},
                "wpm": {"type": "number", "description": "Words per minute, default 150."},
                "words_per_cue": {"type": "integer", "description": "Punchy captions: words per subtitle."},
                "max_chars": {"type": "integer"},
                "offset": {"type": "number", "description": "Seconds before the first subtitle."},
                "seconds": {"type": "number", "description": "subtitle_shift: seconds, negative for earlier."},
                "count": {"type": "integer"},
                "chapters": {"type": "array", "items": {"type": "string"}, "description": "Lines like '0:00 Intro'."},
                "links": {"type": "array", "items": {"type": "string"}},
                "hashtags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"repurpose_subtitles"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"srt_make": srt_make, "vtt_make": vtt_make, "subtitle_list": subtitle_list,
             "subtitle_show": subtitle_show, "subtitle_shift": subtitle_shift, "subtitle_check": subtitle_check,
             "subtitle_to_text": subtitle_to_text, "onscreen_lines": onscreen_lines, "chapters_make": chapters_make,
             "chapters_from_script": chapters_from_script, "description_build": description_build}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
