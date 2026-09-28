"""Words: definitions (dictionaryapi.dev), synonyms, antonyms, rhymes and sound-alikes (Datamuse),
spelling a word out, counting words and characters, and a word of the day.

Both web services are free and need no key; only the word being looked up is sent.
"""

import re
from datetime import date

import httpx

from config import Settings

DICTIONARY_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"
DATAMUSE_URL = "https://api.datamuse.com/words"
DATAMUSE_REL = {"synonyms": "rel_syn", "antonyms": "rel_ant", "rhymes": "rel_rhy", "sounds_like": "sl"}
RELATED_LABELS = {"synonyms": "Synonyms for", "antonyms": "Opposites of", "rhymes": "Words that rhyme with",
                  "sounds_like": "Words that sound like"}
MAX_WORDS = 10
MAX_TEXT = 20_000

WORDS_OF_THE_DAY = [
    ("serendipity", "finding something good without looking for it"),
    ("petrichor", "the pleasant earthy smell after rain falls on dry ground"),
    ("sonder", "the realisation that every passer-by has a life as full as your own"),
    ("ephemeral", "lasting a very short time"),
    ("mellifluous", "sweet and smooth to listen to"),
    ("quintessential", "the most perfect example of something"),
    ("defenestration", "the act of throwing someone or something out of a window"),
    ("susurrus", "a soft whispering or rustling sound"),
    ("halcyon", "calm, peaceful and happy, often of a time in the past"),
    ("ineffable", "too great or extreme to be put into words"),
    ("limerence", "the state of being infatuated with someone"),
    ("sesquipedalian", "using long words, or a long word itself"),
    ("gossamer", "something very light, thin and delicate"),
    ("luminous", "giving off light; bright or shining"),
    ("perspicacious", "quick to notice and understand things"),
    ("cacophony", "a harsh mixture of loud sounds"),
    ("eloquent", "fluent and persuasive in speaking or writing"),
    ("nefarious", "wicked or criminal"),
    ("ubiquitous", "found everywhere"),
    ("zephyr", "a soft, gentle breeze"),
    ("wanderlust", "a strong desire to travel"),
    ("kerfuffle", "a commotion or fuss"),
    ("gobbledygook", "language that is meaningless or hard to understand"),
    ("brouhaha", "a noisy and overexcited reaction"),
    ("flabbergasted", "extremely surprised"),
    ("discombobulated", "confused and disconcerted"),
    ("lollygag", "to spend time aimlessly"),
    ("snollygoster", "a shrewd, unprincipled person"),
    ("collywobbles", "a feeling of nervousness or a queasy stomach"),
    ("hullabaloo", "a commotion or uproar"),
    ("bumfuzzle", "to confuse or fluster"),
    ("gallivant", "to go from place to place in search of fun"),
    ("nincompoop", "a foolish person"),
    ("skedaddle", "to leave quickly"),
    ("cattywampus", "askew or out of line"),
    ("hornswoggle", "to trick or cheat someone"),
    ("tintinnabulation", "the ringing of bells"),
    ("mondegreen", "a misheard song lyric or phrase"),
    ("apricity", "the warmth of the sun in winter"),
    ("vellichor", "the wistful feeling of a second-hand bookshop"),
    ("hiraeth", "a Welsh word for a deep longing for home"),
    ("hygge", "a Danish word for cosy contentment"),
    ("sobremesa", "a Spanish word for lingering at the table talking after a meal"),
    ("tsundoku", "a Japanese word for buying books and letting them pile up unread"),
    ("fika", "a Swedish word for a coffee and cake break with others"),
    ("resilience", "the ability to recover quickly from difficulties"),
    ("equanimity", "calmness and composure, especially in a difficult situation"),
    ("tenacity", "the quality of holding firm and not giving up"),
    ("magnanimous", "generous and forgiving, especially towards a rival"),
    ("alacrity", "brisk and cheerful readiness"),
    ("panacea", "a solution or remedy for all problems"),
    ("juxtaposition", "placing two things side by side to contrast them"),
    ("onomatopoeia", "a word that sounds like what it describes, such as buzz"),
    ("palindrome", "a word that reads the same backwards, such as level"),
    ("oxymoron", "a phrase that combines opposites, such as deafening silence"),
    ("euphoria", "a feeling of intense happiness"),
    ("labyrinth", "a complicated maze of paths"),
    ("penumbra", "the partly shaded outer region of a shadow"),
    ("effervescent", "bubbly, or lively and enthusiastic"),
    ("idiosyncrasy", "a habit or way of behaving peculiar to one person"),
    ("felicity", "intense happiness, or a knack for finding the right words"),
]


def _word(value) -> str:
    word = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    if not word:
        raise ValueError("Which word?")
    if len(word) > 40 or not re.fullmatch(r"[a-z][a-z' -]*", word):
        raise ValueError("I can only look up ordinary English words.")
    return word


async def define(http: httpx.AsyncClient, value) -> str:
    word = _word(value)
    r = await http.get(DICTIONARY_URL + word, timeout=10)
    if r.status_code == 404:
        return f"I couldn't find {word} in the dictionary."
    r.raise_for_status()
    entries = r.json()
    lines = []
    for entry in entries[:2]:
        for meaning in entry.get("meanings") or []:
            for d in (meaning.get("definitions") or [])[:2]:
                line = f"- ({meaning.get('partOfSpeech', '')}) {d.get('definition', '').strip()}"
                if d.get("example"):
                    line += f' Example: "{d["example"].strip()}"'
                lines.append(line)
    if not lines:
        return f"I couldn't find a definition for {word}."
    phonetic = next((e.get("phonetic") for e in entries if e.get("phonetic")), "")
    head = f"{word} {phonetic}".strip()
    return f"{head}:\n" + "\n".join(lines[:5])


async def related(http: httpx.AsyncClient, action: str, value) -> str:
    word = _word(value)
    r = await http.get(DATAMUSE_URL, params={DATAMUSE_REL[action]: word, "max": MAX_WORDS}, timeout=10)
    r.raise_for_status()
    found = [w["word"] for w in r.json() if w.get("word") and w["word"] != word][:MAX_WORDS]
    if not found:
        return f"I couldn't find any {action.replace('_', '-').replace('sounds-like', 'sound-alikes')} for {word}."
    return f"{RELATED_LABELS[action]} {word}: {', '.join(found)}."


def spell(value) -> str:
    word = re.sub(r"\s+", " ", str(value or "")).strip()[:60]
    if not word:
        raise ValueError("Which word should I spell?")
    letters = ", ".join("space" if c == " " else c.upper() for c in word)
    return f"{word} is spelled {letters}."


def count(text) -> str:
    text = str(text or "")[:MAX_TEXT]
    if not text.strip():
        raise ValueError("Give me the text to count.")
    words = len(re.findall(r"\S+", text))
    chars = len(text)
    no_spaces = len(re.sub(r"\s", "", text))
    return (f"{words} word{'s' if words != 1 else ''}, {chars} characters including spaces, "
            f"{no_spaces} without.")


def word_of_the_day(today: date | None = None) -> str:
    today = today or date.today()
    word, meaning = WORDS_OF_THE_DAY[today.toordinal() % len(WORDS_OF_THE_DAY)]
    return f"Today's word is {word}: {meaning}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "word_lookup",
        "description": "Words. action 'define' (dictionary meaning), 'synonyms', 'antonyms', 'rhymes', "
                       "'sounds_like' (words that sound similar, for spelling help), 'spell' (letter by "
                       "letter), 'count' (words and characters in text), 'word_of_the_day'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["define", "synonyms", "antonyms", "rhymes", "sounds_like",
                                                       "spell", "count", "word_of_the_day"]},
                "word": {"type": "string"},
                "text": {"type": "string", "description": "Text to count, for 'count'."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"word_lookup"}


async def run_tool(name: str, args: dict, settings: Settings, http: httpx.AsyncClient) -> str:
    action = args.get("action")
    if action == "define":
        return await define(http, args.get("word"))
    if action in DATAMUSE_REL:
        return await related(http, action, args.get("word"))
    if action == "spell":
        return spell(args.get("word"))
    if action == "count":
        return count(args.get("text") or args.get("word"))
    return word_of_the_day()
