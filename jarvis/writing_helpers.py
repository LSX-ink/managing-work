"""Writing helpers that work offline: prompts, name ideas, poem forms and a syllable checker, readability stats and
song lyrics laid out in sections (a song is a piece in a writing project, one "## Section" per part).
"""

import random
import re
from collections import Counter

import docs_tools
import homestore as hs
import screen
import writing_data as wd
import writing_store as ws
from config import Settings

ACTIONS = ["prompt", "names", "poem_form", "syllables", "readability", "song_new", "song_section", "song_show"]
NAME_STYLES = list(wd.NAME_PARTS)
rng = random.Random()
ARROW = " → "


# ---- Prompts and names ---------------------------------------------------------------------------

def prompt(args: dict) -> screen.Shown:
    genre = hs.clean(args.get("genre")).lower()
    if genre and genre not in wd.PROMPTS:
        raise ValueError(f"I've got prompts for {', '.join(wd.PROMPTS)}.")
    genre = genre or rng.choice(list(wd.PROMPTS))
    text = rng.choice(wd.PROMPTS[genre])
    card = screen.card("text", f"Writing prompt: {genre}", "writing-prompt", text=text, buttons=[
        {"label": "Start a piece from this", "say": f"Start a new piece in my writing project from this prompt: {text}"},
        {"label": "Another prompt", "say": f"Give me another {genre} writing prompt."}])
    return screen.Shown(f"Here's a {genre} prompt: {text}", card)


def one_name(style: str) -> str:
    parts = wd.NAME_PARTS[style]
    if style == "english":
        return f"{rng.choice(parts['first'])} {rng.choice(parts['last'])}"
    if style == "places":
        return rng.choice(parts["start"]) + rng.choice(parts["end"])
    name = rng.choice(parts["start"]) + rng.choice(parts["middle"]) + rng.choice(parts["end"])
    return name.strip("-").capitalize()


def names(args: dict) -> screen.Shown:
    style = args.get("style") if args.get("style") in wd.NAME_PARTS else "fantasy"
    count = int(hs.number(args.get("count") or 10, "number of names", 1, 30))
    found: list[str] = []
    for _ in range(count * 20):
        name = one_name(style)
        if name not in found:
            found.append(name)
        if len(found) == count:
            break
    say = ("Add a place called {} to my world notes." if style == "places"
           else "Add a character called {} to my story bible.")
    items = [{"label": n, "say": say.format(n)} for n in found]
    return screen.Shown(f"Some {style} names: {', '.join(found)}.", screen.card(
        "list", f"{style.title()} names", "writing-names", items=items,
        buttons=[{"label": "More names", "say": f"Give me more {style} names."}]))


# ---- Poems and syllables --------------------------------------------------------------------------

def syllables_in(word: str) -> int:
    """English syllables by vowel groups, with the common silent endings taken off."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|[^laeiouydt]ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"ely$", "ly", re.sub(r"^y", "", w))
    split = re.findall(r"ia|iet|eo(?!p)|oe(?=[mt])|(?<![qg])ua", w)  # vowel pairs said as two syllables
    return max(1, len(re.findall(r"[aeiouy]+", w)) + len(split))


def line_syllables(line: str) -> int:
    return sum(syllables_in(w) for w in ws.WORD.findall(line))


def poem_form(args: dict) -> screen.Shown:
    want = hs.clean(args.get("form")).lower()
    if not want:
        items = [{"label": f.title(), "say": f"Tell me the rules of a {f}."} for f in wd.POEM_FORMS]
        return screen.Shown(f"Poem forms I know: {', '.join(wd.POEM_FORMS)}.",
                            screen.card("list", "Poem forms", "writing-forms", items=items))
    key = hs.find(wd.POEM_FORMS, want)
    if key is None:
        raise ValueError(f"I don't know that form. I know: {', '.join(wd.POEM_FORMS)}.")
    f = wd.POEM_FORMS[key]
    pattern = f"Syllables per line: {'-'.join(map(str, f['syllables']))}." if f["syllables"] and len(
        set(f["syllables"])) > 1 else (f"About {f['syllables'][0]} syllables a line." if f["syllables"] else "")
    text = f"{f['rules']}\n\nRhyme scheme: {f['rhyme']}.\n{pattern}".strip()
    buttons = [{"label": "Check my lines", "say": f"Check the syllables of my {key}."}] if f["syllables"] else []
    return screen.Shown(f"{key.title()}: {f['rules']}", screen.card(
        "text", key.title(), "writing-form", text=text, buttons=buttons + [
            {"label": "All forms", "say": "What poem forms do you know?"}]))


def syllables(args: dict) -> screen.Shown:
    text = str(args.get("text") or "")
    lines = [x.strip() for x in re.split(r"\n| / ", text) if x.strip()][:40]
    if not lines:
        raise ValueError("Which line should I count?")
    counts = [line_syllables(x) for x in lines]
    form = hs.find(wd.POEM_FORMS, hs.clean(args.get("form")).lower()) if hs.clean(args.get("form")) else None
    target = (wd.POEM_FORMS[form]["syllables"] or []) if form else []
    tol = wd.POEM_FORMS[form]["tolerance"] if form else 0
    rows, ok = [], True
    for i, (line, n) in enumerate(zip(lines, counts)):
        want = target[i] if i < len(target) else None
        good = want is None or abs(n - want) <= tol
        ok = ok and good and (not target or len(lines) == len(target))
        rows.append([line, str(n), str(want) if want else "", "" if want is None else ("yes" if good else "no")])
    said = f"Syllables: {', '.join(map(str, counts))}."
    if target:
        said += (f" That fits a {form}." if ok else
                 f" A {form} wants {'-'.join(map(str, target))}" + (f" (give or take {tol})" if tol else "") + ".")
    columns = ["Line", "Syllables", "Target", "Fits"] if target else ["Line", "Syllables"]
    return screen.Shown(said + " It's an English rule of thumb, so a word may be one out.", screen.card(
        "table", f"Syllables{': ' + form if form else ''}", "writing-syllables", columns=columns,
        rows=[r if target else r[:2] for r in rows]))


# ---- Readability -------------------------------------------------------------------------------------

def source_text(settings: Settings, args: dict) -> tuple[str, str]:
    if str(args.get("text") or "").strip() and not hs.clean(args.get("piece")):
        return "your text", str(args["text"])
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    if hs.clean(args.get("piece")):
        piece = p["pieces"][ws.piece_index(p, args["piece"])]
        return piece["title"], ws.body(ws.read_piece(settings, key, piece))
    return key, "\n\n".join(ws.body(ws.read_piece(settings, key, x)) for x in p["pieces"])


def ease_label(score: float) -> str:
    for low, label in ((90, "very easy"), (80, "easy"), (70, "fairly easy"), (60, "plain English"),
                       (50, "fairly hard"), (30, "hard")):
        if score >= low:
            return label
    return "very hard"


def stats(text: str) -> dict:
    plain = re.sub(r"(?m)^#{1,6}\s.*$", "", text)
    plain = docs_tools.inline_plain(plain)
    found = ws.WORD.findall(plain)
    if not found:
        raise ValueError("There are no words to check yet.")
    sentences = max(1, len([x for x in re.split(r"[.!?]+(?=\s|$)|\n\s*\n", plain) if ws.WORD.search(x)]))
    sylls = sum(syllables_in(w) for w in found)
    lower = [w.lower() for w in found]
    score = 206.835 - 1.015 * (len(found) / sentences) - 84.6 * (sylls / len(found))
    adverbs = [w for w in lower if w.endswith("ly") and len(w) > 4 and w not in wd.NOT_ADVERBS]
    repeated = [(w, n) for w, n in Counter(w for w in lower if w not in wd.STOPWORDS and len(w) > 2).most_common(10)
                if n > 1]
    return {"words": len(found), "sentences": sentences, "average": len(found) / sentences,
            "score": round(score, 1), "adverbs": Counter(adverbs), "repeated": repeated}


def readability(settings: Settings, args: dict) -> screen.Shown:
    name, text = source_text(settings, args)
    st = stats(text)
    sections = [{"type": "stats", "items": [
        {"label": "Reading ease", "value": f"{st['score']:g} ({ease_label(st['score'])})"},
        {"label": "Words", "value": f"{st['words']:,}"}, {"label": "Sentences", "value": f"{st['sentences']:,}"},
        {"label": "Words a sentence", "value": f"{st['average']:.1f}"},
        {"label": "-ly adverbs", "value": str(sum(st["adverbs"].values()))}]}]
    if st["repeated"]:
        sections.append({"type": "table", "title": "Most repeated words", "columns": ["Word", "Times"],
                         "rows": [[w, str(n)] for w, n in st["repeated"]]})
    if st["adverbs"]:
        sections.append({"type": "text", "title": "-ly adverbs",
                         "text": ", ".join(f"{w} ({n})" if n > 1 else w for w, n in st["adverbs"].most_common(30))})
    said = (f"{name}: reading ease {st['score']:g}, {ease_label(st['score'])}; {st['average']:.0f} words a sentence "
            f"on average, {sum(st['adverbs'].values())} -ly adverbs.")
    return screen.Shown(said, ws.studio(f"Readability: {name}", "writing-readability", sections))


# ---- Song lyrics ---------------------------------------------------------------------------------------

def song_parts(text: str) -> tuple[list[str], dict]:
    m = re.search(r"(?m)^Structure:\s*(.+)$", text)
    order = [x.strip() for x in m.group(1).split(ARROW.strip())] if m else []
    bits = re.split(r"(?m)^##\s+(.+?)\s*$", text)
    parts = {bits[i].strip(): bits[i + 1].strip() for i in range(1, len(bits) - 1, 2)}
    for name in parts:
        if name not in order:
            order.append(name)
    return [x for x in order if x], parts


def hint(part: str) -> str:
    return wd.SECTION_HINTS.get(re.sub(r"\s*\d+$", "", part), "")


def song_project(settings: Settings, data: dict, name) -> str:
    if data["projects"] or hs.clean(name):
        return ws.project_key(data, name)
    ws.folder(settings, "Songs")
    data["projects"]["Songs"] = {"kind": "song lyrics", "goal": 0, "deadline": "", "created": hs.today().isoformat(),
                                 "pieces": [], "characters": {}, "world": {}, "scenes": []}
    return "Songs"


def song_new(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, song_project(settings, data, args.get("project")))
    shape = args.get("shape") if args.get("shape") in wd.SONG_SHAPES else "verse-chorus"
    order = wd.SONG_SHAPES[shape]
    unique = list(dict.fromkeys(order))
    text = f"Structure: {ARROW.join(order)}\n\n" + "\n\n".join(f"## {x}\n" for x in unique)
    piece = ws.new_piece(settings, key, p, args.get("title"), text)
    data["current"] = key
    ws.save(settings, data)
    return song_show(settings, {"project": key, "piece": piece["title"]},
                     f"Made the song {piece['title']} in {key}, shaped {ARROW.join(order)}.")


def song_section(settings: Settings, args: dict) -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = p["pieces"][ws.piece_index(p, args.get("piece"))]
    lyrics = str(args.get("text") or "").strip()
    if not lyrics:
        raise ValueError("What are the lyrics for that section?")
    text = ws.read_piece(settings, key, piece)
    order, parts = song_parts(text)
    want = hs.need(args.get("section"), "section (e.g. Chorus or Verse 2)", 40)
    section = hs.find(parts, want)
    if section is None:
        section = want.title()
        m = re.search(r"(?m)^Structure:\s*(.+)$", text)
        text = (text[:m.end()] + ARROW + section + text[m.end():]) if m else text
        text = docs_tools.add_to_section(text, section, lyrics, replace=False)
    else:
        text = docs_tools.add_to_section(text, section, lyrics, replace=True)
    docs_tools.write(ws.piece_path(settings, key, piece), text)
    return song_show(settings, {"project": key, "piece": piece["title"]}, f"Set the {section} of {piece['title']}.")


def song_show(settings: Settings, args: dict, said: str = "") -> screen.Shown:
    data = ws.load(settings)
    key, p = ws.project(data, args.get("project"))
    piece = p["pieces"][ws.piece_index(p, args.get("piece"))]
    order, parts = song_parts(ws.read_piece(settings, key, piece))
    sections, spoken = [], []
    for part in order:
        words = parts.get(part, "")
        sections.append({"type": "text", "title": part, "text": words or f"({hint(part) or 'empty'})"})
        if words:
            spoken.append(f"{part}:\n{words}")
    if not sections:
        sections = [{"type": "text", "text": "No sections yet."}]
    buttons = [{"label": "Write the chorus", "say": f"Write the chorus for my song {piece['title']}."},
               {"label": "Readability", "say": f"Check the readability of {piece['title']} in my project {key}."}]
    return screen.Shown(said or (f"{piece['title']}:\n" + "\n\n".join(spoken) if spoken else
                                 f"{piece['title']} has no lyrics yet."),
                        ws.studio(f"Song: {piece['title']}", f"writing-song-{ws.slug(key)}-{ws.slug(piece['title'])}",
                                  sections, buttons))


def tool_definitions() -> list[dict]:
    return [{
        "name": "writing_helper",
        "description": "Offline creative writing helpers: prompt (a random writing prompt by genre, with a 'start a "
                       "piece' button); names (name generator: fantasy, sci-fi, English or place names); poem_form "
                       "(rules for haiku, limerick, sonnet, villanelle, cinquain, tanka...); syllables (count "
                       "syllables per line, check a haiku's 5-7-5 or another form); readability (sentences, average "
                       "sentence length, Flesch reading ease, most repeated words, -ly adverbs) of text, a piece or "
                       "a whole project; song lyrics: song_new (a song laid out in verse/chorus sections), "
                       "song_section (put your lyrics into one section), song_show.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "genre": {"type": "string", "enum": list(wd.PROMPTS)},
                "style": {"type": "string", "enum": NAME_STYLES},
                "count": {"type": "integer"},
                "form": {"type": "string", "description": "Poem form, e.g. haiku."},
                "text": {"type": "string", "description": "Lines (one per line or split by ' / '), text to check, "
                                                          "or a song section's lyrics."},
                "project": {"type": "string"},
                "piece": {"type": "string", "description": "Piece or song title."},
                "title": {"type": "string", "description": "song_new: the song's title."},
                "shape": {"type": "string", "enum": list(wd.SONG_SHAPES)},
                "section": {"type": "string", "description": "Song section, e.g. 'Chorus' or 'Verse 2'."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"writing_helper"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "prompt":
        return prompt(args)
    if action == "names":
        return names(args)
    if action == "poem_form":
        return poem_form(args)
    if action == "syllables":
        return syllables(args)
    handler = {"readability": readability, "song_new": song_new, "song_section": song_section,
               "song_show": song_show}.get(action)
    if not handler:
        raise ValueError(f"Unknown action {action}.")
    return handler(settings, args)
