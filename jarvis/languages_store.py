"""Shared bits for the language studio: the saved study data (languages.json in the memory folder), the words of
each deck as entries, your own words, spaced-repetition due dates and the daily study log.

languages.json holds: language (the one being learned), cards[lang][key] (box, due, seen, lapses), words[lang]
(your own words), log[date] (minutes, reviews, quizzes), quizzes (recent results) and goal (minutes a day).
"""

import re
import unicodedata
from datetime import date, timedelta

import homestore as hs
import languages_data as data
from config import Settings

FILE = "languages.json"
INTERVALS = [0, 1, 3, 7, 14, 30, 60]  # days until a card is due again, by box
KNOWN_BOX = 3
GRADES = {"again": 0, "hard": 1, "good": 2, "easy": 3}
MAX_OWN, MAX_QUIZZES, DEFAULT_GOAL = 500, 200, 10
GENDERS = {"m": "masculine", "f": "feminine", "n": "neuter"}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {"language": found.get("language", ""), "cards": found.get("cards") or {},
            "words": found.get("words") or {}, "log": found.get("log") or {}, "quizzes": found.get("quizzes") or [],
            "goal": found.get("goal") or DEFAULT_GOAL}


def save(settings: Settings, found: dict) -> None:
    hs.save(settings, FILE, found)


def language(found: dict, name=None) -> str:
    """The language code for a name or code, or the saved one when no name is given."""
    text = hs.clean(name).lower()
    if not text:
        text = found.get("language") or ""
        if not text:
            raise ValueError("Which language? I can help with Spanish, French, German, Italian, Portuguese "
                             "and Japanese.")
    for code, info in data.LANGS.items():
        if text in (code, info["name"].lower()):
            return code
    raise ValueError(f"I can't teach {hs.clean(name)} yet. I know Spanish, French, German, Italian, Portuguese "
                     "and Japanese.")


def name(code: str) -> str:
    return data.LANGS[code]["name"]


def strip_marks(text: str) -> str:
    """Lower case without accents or punctuation, for forgiving answer checks."""
    plain = unicodedata.normalize("NFD", str(text).lower())
    plain = "".join(c for c in plain if not (unicodedata.category(c) == "Mn" and ord(c) < 0x370))
    return re.sub(r"[^\w\s]", "", plain.replace("ß", "ss")).strip()


# ---- words as entries ----------------------------------------------------------------------------------

def entry(lang: str, raw: str, english: str, topic: str) -> dict:
    """A vocabulary entry from its data string (see languages_data)."""
    text, gender, roman = raw, "", ""
    if lang == "ja":
        text, _, roman = raw.partition("|")
    elif ":" in raw:
        text, _, gender = raw.partition(":")
    article, word = "", text
    if gender:
        article, word = (text[:2], text[2:]) if text.startswith("l'") else text.split(" ", 1)
    return {"key": text.lower(), "target": text, "word": word, "article": article, "gender": gender,
            "roman": roman, "english": english, "topic": topic}


def deck(lang: str, topic: str) -> list[dict]:
    if topic == "numbers":
        words = data.number_words(lang)
        return [entry(lang, w, str(n), "numbers") for n, w in zip(data.NUMBER_VALUES, words)]
    return [entry(lang, raw, english, topic)
            for raw, english in zip(data.VOCAB[lang][topic], data.ENGLISH[topic])]


def topic_name(topic: str) -> str:
    return "Numbers" if topic == "numbers" else "My words" if topic == "mine" else data.TOPIC_NAMES[topic]


def topics() -> list[str]:
    return list(data.TOPIC_NAMES) + ["numbers"]


def find_topic(text) -> str | None:
    want = hs.clean(text).lower()
    if not want:
        return None
    if want in ("mine", "my words", "my list", "own", "my own words"):
        return "mine"
    for topic in topics():
        if want in (topic, topic_name(topic).lower()) or (len(want) > 3 and want in topic_name(topic).lower()):
            return topic
    return None


def own(found: dict, lang: str) -> list[dict]:
    return [{"key": w["word"].lower(), "target": w["word"], "word": w["word"], "article": "", "gender": "",
             "roman": w.get("note", ""), "english": w["meaning"], "topic": "mine"}
            for w in found["words"].get(lang, [])]


def everything(found: dict, lang: str) -> list[dict]:
    """Every built-in word (numbers excluded) and your own words in that language."""
    entries = [e for t in data.TOPIC_NAMES for e in deck(lang, t)]
    return entries + own(found, lang)


def pool(found: dict, lang: str, topic) -> tuple[list[dict], str]:
    """The entries of a deck, "mine", "due", or all of them when no topic is given; and a name for them."""
    want = hs.clean(topic).lower()
    if want in ("", "all", "mix", "everything"):
        return everything(found, lang) + deck(lang, "numbers"), "Mixed words"
    if want == "due":
        return due_entries(found, lang), "Due today"
    found_topic = find_topic(want)
    if not found_topic:
        raise ValueError(f"I don't have a deck called {hs.clean(topic)}. Ask for the decks to see them.")
    return (own(found, lang) if found_topic == "mine" else deck(lang, found_topic)), topic_name(found_topic)


# ---- spaced repetition ---------------------------------------------------------------------------------

def record(found: dict, lang: str, key: str) -> dict | None:
    return found["cards"].get(lang, {}).get(key)


def grade(found: dict, lang: str, key: str, how: str, today: date) -> None:
    """Move a card between boxes: again drops to box 0 (due today), hard stays, good +1, easy +2."""
    cards = found["cards"].setdefault(lang, {})
    rec = cards.setdefault(key, {"box": 0, "due": today.isoformat(), "seen": 0, "lapses": 0})
    step = GRADES[how]
    if step == 0:
        rec["box"], rec["lapses"] = 0, rec.get("lapses", 0) + 1
    elif step > 1:
        rec["box"] = min(len(INTERVALS) - 1, rec["box"] + step - 1)
    days = max(1, INTERVALS[rec["box"]]) if step else 0
    rec["due"] = (today + timedelta(days=days)).isoformat()
    rec["seen"] = rec.get("seen", 0) + 1


def is_due(rec: dict | None, today: date) -> bool:
    return bool(rec) and rec["due"] <= today.isoformat()


def due_entries(found: dict, lang: str) -> list[dict]:
    today = hs.today()
    pooled = everything(found, lang) + deck(lang, "numbers")
    seen: dict[str, dict] = {}
    for e in pooled:
        if is_due(record(found, lang, e["key"]), today):
            seen.setdefault(e["key"], e)
    return sorted(seen.values(), key=lambda e: record(found, lang, e["key"])["due"])


def is_known(rec: dict | None) -> bool:
    return bool(rec) and rec["box"] >= KNOWN_BOX


# ---- the daily log -------------------------------------------------------------------------------------

def log_add(found: dict, day: date, minutes: float = 0, reviews: int = 0, quizzes: int = 0) -> dict:
    row = found["log"].setdefault(day.isoformat(), {"minutes": 0, "reviews": 0, "quizzes": 0})
    row["minutes"] = round(row.get("minutes", 0) + minutes, 1)
    row["reviews"] = row.get("reviews", 0) + reviews
    row["quizzes"] = row.get("quizzes", 0) + quizzes
    return row


def active_days(found: dict) -> set[date]:
    days = set()
    for iso, row in found["log"].items():
        if row.get("minutes") or row.get("reviews") or row.get("quizzes"):
            try:
                days.add(date.fromisoformat(iso))
            except ValueError:
                continue
    return days


def streaks(found: dict, today: date) -> tuple[int, int]:
    """(current streak, best streak) in days. Today not being done yet doesn't break the current streak."""
    days = active_days(found)
    day = today if today in days else today - timedelta(days=1)
    current = 0
    while day in days:
        current += 1
        day -= timedelta(days=1)
    best = run = 0
    previous = None
    for d in sorted(days):
        run = run + 1 if previous and d - previous == timedelta(days=1) else 1
        best, previous = max(best, run), d
    return current, max(best, current)


def minutes_on(found: dict, day: date) -> float:
    return found["log"].get(day.isoformat(), {}).get("minutes", 0)
