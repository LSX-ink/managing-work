"""Reading help: understanding a page or some text. A link, pasted words or a memory file can be simplified,
summarised, scored for how easy it is to read, mined for hard words, and hard words can be looked up.

Alfred (the model) does the rewriting: simplify and summarise hand him the extracted words with an instruction, the
same way other writing helpers work, and he shows the result in a pop-up. Scores use the same Flesch formula and
syllable rule as the writing helpers. Definitions reuse words.define (dictionaryapi.dev, only the word is sent).
"""

import re
from collections import Counter

import httpx

import screen
import webread_extract as ex
import words
import writing_helpers as wh
from config import Settings

ACTIONS = ["simplify", "summarise", "readability", "hard_words", "define"]
MODEL_CHARS = 9000
LONG_SENTENCE = 25
READING_WPM = 200
EASY_WORDS = {"government", "everything", "something", "important", "different", "together", "another", "children",
              "beautiful", "interesting", "understand", "information", "yesterday", "tomorrow", "family"}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(ex.words_in(s)) >= 1]


def score(text: str) -> dict:
    found = ex.words_in(text)
    if not found:
        raise ValueError("There are no words to score.")
    parts = sentences(text)
    n = max(1, len(parts))
    sylls = sum(wh.syllables_in(w) for w in found)
    per_sentence, per_word = len(found) / n, sylls / len(found)
    ease = round(206.835 - 1.015 * per_sentence - 84.6 * per_word, 1)
    grade = round(max(0.0, 0.39 * per_sentence + 11.8 * per_word - 15.59), 1)
    long = sorted((s for s in parts if len(ex.words_in(s)) > LONG_SENTENCE), key=lambda s: -len(ex.words_in(s)))
    return {"words": len(found), "sentences": n, "ease": ease, "grade": grade, "average": per_sentence,
            "long": long, "minutes": max(1, round(len(found) / READING_WPM))}


def model_text(page: dict) -> tuple[str, int]:
    text = ex.plain(page["blocks"])
    return text[:MODEL_CHARS], len(ex.words_in(text))


def hand_over(page: dict, job: str) -> str:
    text, total = model_text(page)
    cut = "" if len(text) >= len(ex.plain(page["blocks"])) else f" (this is the first {MODEL_CHARS} characters of {total} words)"
    return (f"{job}\nSource: {page['title']}{' - ' + page['url'] if page.get('url') else ''}{cut}\n---\n{text}\n---")


async def simplify(settings: Settings, http: httpx.AsyncClient, args: dict) -> str:
    page = await ex.source(settings, http, args)
    return hand_over(page, "Rewrite this in plain, easy English for a reader who finds long text hard: short sentences, "
                           "everyday words, one idea at a time, keep the facts and any numbers, no jargon. Show it with "
                           "show_on_screen (kind text, title 'Simple version'). Reply with just one short sentence.")


async def summarise(settings: Settings, http: httpx.AsyncClient, args: dict) -> str:
    page = await ex.source(settings, http, args)
    return hand_over(page, "Summarise this in exactly 3 short bullet points in plain English. Show them with "
                           "show_on_screen (kind list, title 'In short') and read out only the first point.")


async def readability(settings: Settings, http: httpx.AsyncClient, args: dict) -> screen.Shown:
    page = await ex.source(settings, http, args)
    s = score(ex.plain(page["blocks"]))
    label = wh.ease_label(s["ease"])
    rows = [["Reading ease", f"{s['ease']:g} out of 100 ({label})"], ["School grade", f"{s['grade']:g}"],
            ["Reading age", f"about {round(s['grade'] + 5)}"], ["Words", f"{s['words']:,}"],
            ["Sentences", f"{s['sentences']:,}"], ["Words a sentence", f"{s['average']:.1f}"],
            ["Reading time", f"about {s['minutes']} min"], ["Long sentences", f"{len(s['long'])} over {LONG_SENTENCE} words"]]
    long = "\n".join(f"{i}. ({len(ex.words_in(x))} words) {x[:160]}{'...' if len(x) > 160 else ''}"
                     for i, x in enumerate(s["long"][:5], 1))
    card = screen.card("table", f"How easy to read: {page['title']}"[:80], "webread-readability", columns=["Measure", "Score"],
                       rows=rows, text=("Sentences worth splitting:\n" + long) if long else "No very long sentences.",
                       buttons=[{"label": "Make it simpler", "say": f"Make {page['url']} simple to read."}] if page.get("url") else [])
    return screen.Shown(f"{page['title']} scores {s['ease']:g}, which is {label}; about {s['minutes']} minutes to read"
                        + (f", with {len(s['long'])} long sentences." if s["long"] else "."), card)


def hard_word_list(text: str, limit: int = 15) -> list[tuple[str, int]]:
    lower = Counter(w.lower().strip("'’-") for w in ex.words_in(text) if w.islower() or w.istitle())
    tricky = [(w, n) for w, n in lower.items() if len(w) >= 8 and wh.syllables_in(w) >= 3 and w not in EASY_WORDS
              and w.isalpha() and (w.islower() or wh.syllables_in(w) >= 4)]
    return sorted(tricky, key=lambda x: (-wh.syllables_in(x[0]), -x[1], x[0]))[:limit]


async def hard_words(settings: Settings, http: httpx.AsyncClient, args: dict) -> screen.Shown:
    page = await ex.source(settings, http, args)
    found = hard_word_list(ex.plain(page["blocks"]))
    if not found:
        return screen.Shown("There are no hard words in that; it's all fairly plain.", screen.card(
            "text", "Hard words", "webread-hard", text="No tricky words found."))
    items = [{"label": f"{w}" + (f" ({n} times)" if n > 1 else ""), "say": f"What does {w} mean?"} for w, n in found]
    card = screen.card("list", f"Hard words in {page['title']}"[:80], "webread-hard", items=items,
                       text="Tap a word to hear what it means.")
    return screen.Shown(f"I found {len(found)} hard words, starting with {found[0][0]}; tap one for its meaning.", card)


async def define(http: httpx.AsyncClient, args: dict) -> screen.Shown:
    word = args.get("word") or args.get("text") or ""
    try:
        said = await words.define(http, word)
    except httpx.HTTPError:
        raise ValueError("The dictionary isn't answering right now.") from None
    card = screen.card("text", str(word).strip().lower()[:40] or "Meaning", f"webread-define-{str(word).strip().lower()[:30]}",
                       text=said, buttons=[{"label": "Say it simply", "say": f"Explain {str(word).strip()} in very simple words."}])
    return screen.Shown(said.split("\n")[1].strip("- ") if "\n" in said else said, card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "web_read_explain",
        "description": "Reading aid for understanding a public web page (url), pasted text (text) or a .txt/.md memory "
                       "file (folder + filename). simplify: get the words to rewrite in plain easy English; "
                       "summarise: get the words for a 3-bullet summary; readability: reading ease, grade, reading "
                       "time and long sentences flagged; hard_words: tricky words to tap; define: what a word means.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "url": {"type": "string"},
                "text": {"type": "string"},
                "title": {"type": "string", "description": "a name for pasted text."},
                "folder": {"type": "string"},
                "filename": {"type": "string"},
                "word": {"type": "string", "description": "define: the word."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"web_read_explain"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient):
    action = args.get("action")
    if action == "simplify":
        return await simplify(settings, http, args)
    if action == "summarise":
        return await summarise(settings, http, args)
    if action == "readability":
        return await readability(settings, http, args)
    if action == "hard_words":
        return await hard_words(settings, http, args)
    if action == "define":
        return await define(http, args)
    raise ValueError(f"Pick one of: {', '.join(ACTIONS)}.")
