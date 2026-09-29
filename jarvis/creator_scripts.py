"""Creator ideas, part 3: caption scaffold, hashtag sets with a mix checker, script outlines with seconds per beat, the
60-second pacing calculator and a script length check.

Everything is worked out on the PC from the user's own words; nothing is posted or sent anywhere. Hashtag sets are
kept per niche in creatorideas.json.
"""

import re

import homestore as hs
import screen
import creator_data as data
import creator_store as store
from config import Settings

ACTIONS = ["caption_scaffold", "hashtag_save", "hashtag_show", "hashtag_check", "hashtag_remove", "outline",
           "outline_list", "pacing", "script_check"]
MIX = {"broad": (1, 3), "niche": (2, 4), "branded": (1, 1)}
DEFAULT_WPM = 150


def caption_scaffold(settings: Settings, args: dict) -> str:
    topic = hs.need(args.get("topic"), "topic")
    goal = hs.clean(args.get("goal")).lower() or "comment"
    ctas = data.CTAS.get(goal, data.CTAS["comment"])
    sets = store.load(settings)["hashtags"]
    key = hs.find(sets, args.get("niche") or "") if args.get("niche") else None
    tags = " ".join(f"#{t}" for kind in ("broad", "niche", "branded") for t in sets[key][kind]) if key else ""
    return (f"Write a caption for a short video about {topic}. Structure: 1) a first line of under 100 characters "
            "that repeats or teases the hook (the first line is what shows before 'more'); 2) one line adding "
            f"something the video doesn't say; 3) a call to action such as '{ctas[0]}'; 4) hashtags: "
            f"{tags or 'use hashtag_show for a saved set, or suggest a broad, niche and branded mix'}. Keep it "
            "honest and short, no income promises. Offer two versions.")


# ---- Hashtags ------------------------------------------------------------------------------------

def _set(sets: dict, niche: str) -> dict:
    return sets.setdefault(niche, {"broad": [], "niche": [], "branded": []})


def hashtag_save(settings: Settings, args: dict) -> str:
    niche = hs.need(args.get("niche"), "niche", 40)
    saved = store.load(settings)
    key = hs.find(saved["hashtags"], niche) or niche
    group = _set(saved["hashtags"], key)
    for kind, given in (("broad", args.get("broad")), ("niche", args.get("niche_tags")),
                        ("branded", args.get("branded"))):
        for t in map(store.tag, store.texts(given, 40)):
            if t and t not in group[kind]:
                store.put(group[kind], t, 15)
    store.save(settings, saved)
    return f"Saved. {key} has {len(group['broad'])} broad, {len(group['niche'])} niche and {len(group['branded'])} branded tags."


def hashtag_show(settings: Settings, args: dict) -> screen.Shown | str:
    sets = store.load(settings)["hashtags"]
    wanted = hs.clean(args.get("niche"))
    if wanted and hs.find(sets, wanted) is None:
        raise ValueError(f"I don't have a hashtag set for {wanted}.")
    keys = [hs.find(sets, wanted)] if wanted else list(sets)
    if not keys:
        return "You haven't saved any hashtag sets yet."
    rows = [[k, " ".join("#" + t for t in sets[k]["broad"]), " ".join("#" + t for t in sets[k]["niche"]),
             " ".join("#" + t for t in sets[k]["branded"])] for k in keys]
    return screen.Shown(f"{len(rows)} hashtag set{'s' if len(rows) != 1 else ''}.",
                        screen.card("table", "Hashtag sets", "creator-hashtags",
                                    columns=["Niche", "Broad", "Niche", "Branded"], rows=rows))


def _classify(tags: list[str], sets: dict) -> dict:
    lookup = {t: kind for group in sets.values() for kind in ("broad", "niche", "branded") for t in group[kind]}
    counts = {"broad": 0, "niche": 0, "branded": 0, "unsorted": 0}
    for t in tags:
        counts[lookup.get(t, "unsorted")] += 1
    return counts


def hashtag_check(settings: Settings, args: dict) -> screen.Shown:
    sets = store.load(settings)["hashtags"]
    given = [store.tag(t) for t in re.findall(r"#?[\w]+", str(args.get("tags") or "")) if store.tag(t)]
    if not given and args.get("niche"):
        key = hs.find(sets, args["niche"])
        if key is None:
            raise ValueError(f"I don't have a hashtag set for {args['niche']}.")
        given = [t for kind in ("broad", "niche", "branded") for t in sets[key][kind]]
    if not given:
        raise ValueError("Give me the hashtags to check, or a niche with a saved set.")
    counts = _classify(list(dict.fromkeys(given)), sets)
    rows = []
    for kind, (low, high) in MIX.items():
        n = counts[kind]
        verdict = "ok" if low <= n <= high else f"add {low - n}" if n < low else f"drop {n - high}"
        rows.append([kind, str(n), f"{low} to {high}" if low != high else str(low), verdict])
    if counts["unsorted"]:
        rows.append(["not in a saved set", str(counts["unsorted"]), "0", "save them as broad, niche or branded"])
    total = len(set(given))
    rows.append(["total", str(total), "3 to 6", "ok" if 3 <= total <= 6 else "fewer, better tags work best"])
    return screen.Shown(f"{total} hashtags: {counts['broad']} broad, {counts['niche']} niche, {counts['branded']} branded.",
                        screen.card("table", "Hashtag mix", "creator-hashmix", columns=["Type", "You have", "Aim", "Verdict"],
                                    rows=rows))


def hashtag_remove(settings: Settings, args: dict) -> str:
    saved = store.load(settings)
    key = hs.find(saved["hashtags"], hs.need(args.get("niche"), "niche"))
    if key is None:
        raise ValueError("I don't have a hashtag set like that.")
    if not args.get("confirmed"):
        return store.confirm_needed(f"the hashtag set {key}")
    del saved["hashtags"][key]
    store.save(settings, saved)
    return f"Removed the hashtag set {key}."


# ---- Outlines and pacing -------------------------------------------------------------------------

def _outline_key(value) -> str:
    text = hs.clean(value).lower().replace(" ", "_").replace("-", "_")
    found = next((k for k, (title, _) in data.OUTLINES.items() if text in (k, title.lower().replace(" ", "_"))
                  or (text and text in k)), None)
    if found is None:
        raise ValueError(f"Outlines are: {', '.join(data.OUTLINES)}.")
    return found


def outline(settings: Settings, args: dict) -> screen.Shown:
    key = _outline_key(args.get("template"))
    title, beats = data.OUTLINES[key]
    total = int(hs.number(args.get("seconds") or 60, "length in seconds", 10, 180))
    wpm = int(hs.number(args.get("wpm") or DEFAULT_WPM, "words per minute", 80, 250))
    rows, start = [], 0.0
    for beat, share, what in beats:
        length = total * share
        rows.append([beat, f"{start:.0f}-{start + length:.0f}s", f"{length:.0f}s", str(round(length * wpm / 60)), what])
        start += length
    return screen.Shown(f"{title}: {len(beats)} beats over {total} seconds, about {round(total * wpm / 60)} words.",
                        screen.card("table", f"Outline: {title}", "creator-outline",
                                    columns=["Beat", "Time", "Length", "Words", "What to do"], rows=rows))


def outline_list(settings: Settings, args: dict) -> screen.Shown:
    return screen.Shown("Pick an outline and I'll lay it out with seconds per beat.",
                        screen.card("list", "Script outlines", "creator-outlines",
                                    items=[{"label": f"{title} ({len(beats)} beats)", "say": f"Show the {title} outline."}
                                           for title, beats in data.OUTLINES.values()]))


def _spoken_seconds(words: float, wpm: float, pauses: float) -> float:
    return words * 60 / wpm + pauses


def pacing(settings: Settings, args: dict) -> screen.Shown:
    wpm = hs.number(args.get("wpm") or DEFAULT_WPM, "words per minute", 80, 250)
    pauses = hs.number(args.get("pauses") or 0, "pause time", 0, 60)
    if args.get("seconds"):
        seconds = hs.number(args.get("seconds"), "length in seconds", 5, 600)
        words = max(0, round((seconds - pauses) * wpm / 60))
        return screen.Shown(f"About {words} words fill {seconds:g} seconds at {wpm:g} words a minute.",
                            _pace_card([["Target length", f"{seconds:g}s"], ["Pace", f"{wpm:g} wpm"],
                                        ["Pauses", f"{pauses:g}s"], ["Words to write", str(words)]]))
    words = store.words(args.get("text")) or int(hs.number(args.get("words"), "word count", 1, 5000))
    seconds = _spoken_seconds(words, wpm, pauses)
    fits = "It fits in a minute." if seconds <= 60 else f"That is {seconds - 60:.0f} seconds over a minute."
    return screen.Shown(f"{words} words take about {seconds:.0f} seconds at {wpm:g} words a minute. {fits}",
                        _pace_card([["Words", str(words)], ["Pace", f"{wpm:g} wpm"], ["Pauses", f"{pauses:g}s"],
                                    ["Voiceover length", f"{seconds:.0f}s"]]))


def _pace_card(rows: list) -> dict:
    return screen.card("table", "Pacing", "creator-pacing", columns=["", ""], rows=rows)


def script_check(settings: Settings, args: dict) -> screen.Shown:
    text = hs.need(args.get("text"), "script", 8000)
    wpm = hs.number(args.get("wpm") or DEFAULT_WPM, "words per minute", 80, 250)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    words = store.words(text)
    seconds = _spoken_seconds(words, wpm, 0.3 * len(sentences))
    long = max(sentences, key=store.words, default="")
    tips = ["Cut some words." if seconds > 60 else "Room to spare." if seconds < 45 else "Right length.",
            f"Longest sentence is {store.words(long)} words." + (" Split it." if store.words(long) > 20 else "")]
    rows = [["Words", str(words)], ["Sentences", str(len(sentences))], ["Voiceover length", f"{seconds:.0f}s"]]
    rows += [["Tip", t] for t in tips]
    return screen.Shown(f"Your script is about {seconds:.0f} seconds. {tips[0]}", _pace_card(rows))


def tool_definitions() -> list[dict]:
    return [{
        "name": "creator_scripts",
        "description": "Writing tools for short videos. action: caption_scaffold (topic, niche, goal) = returns the "
                       "structure and saved hashtags, then YOU write the caption; hashtag_save (niche, broad, "
                       "niche_tags, branded) / hashtag_show / hashtag_check (tags text or niche) = broad/niche/"
                       "branded mix / hashtag_remove (niche, confirmed only after yes); outline (template "
                       "story_arc/listicle/myth_vs_fact/part_series/did_you_know, seconds) = beats with seconds "
                       "and word counts / outline_list; pacing (text or words, or seconds, wpm, pauses) = "
                       "voiceover length or words for 60 seconds; script_check (text) = length and longest "
                       "sentence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "topic": {"type": "string"},
                "niche": {"type": "string", "description": "The hashtag set name, e.g. psychology."},
                "goal": {"type": "string", "description": "caption_scaffold: follow, comment, share, save or series."},
                "broad": {"type": "array", "items": {"type": "string"}},
                "niche_tags": {"type": "array", "items": {"type": "string"}},
                "branded": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "string", "description": "hashtag_check: the hashtags to check."},
                "template": {"type": "string"},
                "seconds": {"type": "number"},
                "wpm": {"type": "number", "description": "Words per minute. Default 150."},
                "pauses": {"type": "number", "description": "Seconds of pauses in the voiceover."},
                "text": {"type": "string", "description": "The script."},
                "words": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"creator_scripts"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"caption_scaffold": caption_scaffold, "hashtag_save": hashtag_save, "hashtag_show": hashtag_show,
             "hashtag_check": hashtag_check, "hashtag_remove": hashtag_remove, "outline": outline,
             "outline_list": outline_list, "pacing": pacing, "script_check": script_check}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
