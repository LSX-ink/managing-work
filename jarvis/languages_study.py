"""Language studio, learning words: pick a language, starter topic decks as flip flashcards with spaced repetition
(due dates saved per card), your own word list, word of the day, searching words, hearing words spoken and
pronunciation tips. The cards are drawn by frontend/popup-languages.js; speaking uses the browser's speechSynthesis.
"""

import random

import homestore as hs
import languages_data as data
import languages_store as ls
import screen
from config import Settings

for _kind in ("languages-cards", "languages-say"):
    screen.EXTRA_KINDS.add(_kind)

ACTIONS = ["languages", "set_language", "decks", "flashcards", "review_due", "save_review", "add_word", "my_words",
           "remove_word", "find_word", "word_of_the_day", "speak", "pronunciation_tips"]
MAX_CARDS = 30


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "language_study",
        "description": "Learn foreign-language words (Spanish, French, German, Italian, Portuguese, Japanese). "
                       "Actions: 'languages' list and pick; 'set_language' (language) the one being learned; "
                       "'decks' topic decks with due counts; 'flashcards' flip cards with spaced repetition "
                       "(topic: greetings, food, travel, family, time, home, numbers, mine, due or mix; "
                       "direction to_english or from_english; count); 'review_due' cards due today; 'save_review' "
                       "(results 'word=good; word2=again', grades again/hard/good/easy) after a flashcard pop-up "
                       "review; 'add_word' (word, meaning, note) to the user's own list; 'my_words'; "
                       "'remove_word' (word, confirmed true only after the user agrees); 'find_word' (query, "
                       "English or foreign); 'word_of_the_day'; 'speak' (text in the language, or a topic) to "
                       "hear it spoken with pronunciation help; 'pronunciation_tips'. language defaults to the set one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "language": {**text, "description": "Spanish, French, German, Italian, Portuguese or Japanese."},
                "topic": text, "direction": {"type": "string", "enum": ["to_english", "from_english"]},
                "count": {"type": "integer", "description": "Cards, 1 to 30 (default 10)."},
                "results": {**text, "description": "save_review: 'word=grade; word=grade' as the pop-up sent it."},
                "word": text, "meaning": text, "note": {**text, "description": "add_word: gender, romaji or a hint."},
                "query": text, "text": {**text, "description": "speak: the words in the language, to be said."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {t["name"] for t in tool_definitions()}
rng = random.Random()


def languages(settings: Settings) -> screen.Shown:
    found = ls.load(settings)
    items = [{"label": f"{i['name']}{' (learning)' if c == found['language'] else ''}: {i['hello']}",
              "say": f"I'm learning {i['name']}."} for c, i in data.LANGS.items()]
    return screen.Shown("Pick a language to learn.", screen.card(
        "list", "Languages", "languages-list", items=items))


def set_language(settings: Settings, lang_name) -> str:
    found = ls.load(settings)
    lang = ls.language({}, lang_name)
    found["language"] = lang
    ls.save(settings, found)
    return f"Right, we're learning {ls.name(lang)}. {data.LANGS[lang]['hello']}!"


def decks(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    today = hs.today()
    items = []
    for topic in ls.topics() + (["mine"] if found["words"].get(lang) else []):
        entries = ls.own(found, lang) if topic == "mine" else ls.deck(lang, topic)
        recs = [ls.record(found, lang, e["key"]) for e in entries]
        known, due = sum(ls.is_known(r) for r in recs), sum(ls.is_due(r, today) for r in recs)
        items.append({"label": f"{ls.topic_name(topic)}: {len(entries)} words, {known} learned, {due} due",
                      "say": f"Flashcards for {topic} in {ls.name(lang)}."})
    total_due = len(ls.due_entries(found, lang))
    buttons = [{"label": f"Review {total_due} due", "say": f"Review my due {ls.name(lang)} cards."}] if total_due else []
    return screen.Shown(f"{ls.name(lang)} has {len(items)} decks; {total_due} cards are due.", screen.card(
        "list", f"{ls.name(lang)} decks", f"languages-decks-{lang}", items=items, buttons=buttons))


def _card(lang: str, e: dict, reverse: bool) -> dict:
    note = " ".join(x for x in (e["roman"], ls.GENDERS.get(e["gender"], ""))
                    if x)
    front, back = (e["english"], e["target"]) if reverse else (e["target"], e["english"])
    return {"id": e["key"], "front": front, "back": back, "say": e["target"], "note": note,
            "roman": e["roman"], "reverse": reverse}


def flashcards(settings: Settings, lang_name, topic, direction, count) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    entries, title = ls.pool(found, lang, topic or "mix")
    if not entries:
        raise ValueError("There's nothing due right now. Try a topic deck like food or travel." if title == "Due today"
                         else "There are no words in that deck yet.")
    n = int(hs.number(count or 10, "number of cards", 1, MAX_CARDS))
    if title != "Due today":
        today = hs.today()
        entries = sorted(entries, key=lambda e: (not ls.is_due(ls.record(found, lang, e["key"]), today),
                                                  ls.record(found, lang, e["key"]) is not None, rng.random()))
    chosen = entries[:n]
    reverse = direction == "from_english"
    payload = {"lang": lang, "name": ls.name(lang), "speech": data.LANGS[lang]["speech"], "track": True,
               "cards": [_card(lang, e, reverse) for e in chosen]}
    return screen.Shown(f"{len(chosen)} {ls.name(lang)} flashcards. Click a card to flip it, then grade yourself.",
                        screen.card("languages-cards", f"{ls.name(lang)}: {title}", f"languages-cards-{lang}",
                                    data=payload))


def save_review(settings: Settings, lang_name, results) -> str:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    today, saved, again = hs.today(), 0, 0
    for part in str(results or "").split(";"):
        key, _, how = part.strip().rpartition("=")
        key, how = key.strip().lower(), how.strip().lower()
        if key and how in ls.GRADES:
            ls.grade(found, lang, key, how, today)
            saved += 1
            again += how == "again"
    if not saved:
        raise ValueError("I didn't find any grades to save. Use 'word=good; word2=again'.")
    ls.log_add(found, today, reviews=saved)
    ls.save(settings, found)
    current, _ = ls.streaks(found, today)
    tail = f" {again} will come back today." if again else ""
    return f"Saved {saved} {ls.name(lang)} cards.{tail} Streak: {hs.plural(current, 'day')}."


def add_word(settings: Settings, lang_name, word, meaning, note) -> str:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    word, meaning = hs.need(word, "word", 60), hs.need(meaning, "meaning", 80)
    words = found["words"].setdefault(lang, [])
    if any(w["word"].lower() == word.lower() for w in words):
        raise ValueError(f"{word} is already on your {ls.name(lang)} list.")
    if len(words) >= ls.MAX_OWN:
        raise ValueError("Your word list is full.")
    words.append({"word": word, "meaning": meaning, "note": hs.clean(note, 60), "added": hs.today().isoformat()})
    ls.save(settings, found)
    return f"Added {word}, meaning {meaning}, to your {ls.name(lang)} words. That's {len(words)} words."


def my_words(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    words = found["words"].get(lang, [])
    if not words:
        raise ValueError(f"You haven't added any {ls.name(lang)} words yet. Say 'add the word ... meaning ...'.")
    today = hs.today()
    rows = []
    for w in words:
        rec = ls.record(found, lang, w["word"].lower())
        state = "new" if not rec else "due" if ls.is_due(rec, today) else f"next {rec['due']}"
        rows.append([w["word"], w["meaning"], w.get("note", ""), state])
    return screen.Shown(f"You have {len(words)} {ls.name(lang)} words of your own.", screen.card(
        "table", f"My {ls.name(lang)} words", f"languages-mine-{lang}", columns=["Word", "Meaning", "Note", "Review"],
        rows=rows, buttons=[{"label": "Flashcards", "say": f"Flashcards of my own {ls.name(lang)} words."},
                            {"label": "Quiz me", "say": f"Quiz me on my own {ls.name(lang)} words."}]))


def remove_word(settings: Settings, lang_name, word, confirmed) -> str:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    words = found["words"].get(lang, [])
    match = next((w for w in words if w["word"].lower() == hs.need(word, "word").lower()), None)
    if not match:
        raise ValueError(f"{word} isn't on your {ls.name(lang)} list.")
    if not confirmed:
        return f"Shall I remove {match['word']} from your {ls.name(lang)} words? Say yes and I will."
    words.remove(match)
    found["cards"].get(lang, {}).pop(match["word"].lower(), None)
    ls.save(settings, found)
    return f"Removed {match['word']}."


def find_word(settings: Settings, lang_name, query) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    want = ls.strip_marks(hs.need(query, "word to look up"))
    hits = [e for e in ls.everything(found, lang) + ls.deck(lang, "numbers")
            if want in ls.strip_marks(e["english"]) or want in ls.strip_marks(e["target"])
            or (e["roman"] and want in ls.strip_marks(e["roman"]))]
    if not hits:
        raise ValueError(f"I haven't got {hs.clean(query)} in my {ls.name(lang)} lists. Ask Claude directly, "
                         "then say 'add the word' to save it.")
    hits = hits[:12]
    rows = [[e["english"], e["target"], e["roman"] or ls.GENDERS.get(e["gender"], ""),
             ls.topic_name(e["topic"])] for e in hits]
    first = hits[0]
    return screen.Shown(f"{first['english']} is {first['target']} in {ls.name(lang)}.", screen.card(
        "table", f"{ls.name(lang)}: {hs.clean(query)}", "languages-find", columns=["English", ls.name(lang), "Note", "Deck"],
        rows=rows, buttons=[{"label": "Say it", "say": f"Say {first['target']} in {ls.name(lang)}."}]))


def word_of_the_day(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    entries = [e for t in data.TOPIC_NAMES for e in ls.deck(lang, t)]
    e = entries[(hs.today().toordinal() * 7 + list(data.LANGS).index(lang)) % len(entries)]
    payload = {"lang": lang, "name": ls.name(lang), "speech": data.LANGS[lang]["speech"], "track": False,
               "cards": [_card(lang, e, False)]}
    extra = f" ({e['roman']})" if e["roman"] else ""
    return screen.Shown(f"Your {ls.name(lang)} word today is {e['target']}{extra}, meaning {e['english']}.",
                        screen.card("languages-cards", f"{ls.name(lang)} word of the day", f"languages-wotd-{lang}",
                                    data=payload, buttons=[{"label": "Add to my words",
                                                            "say": f"Add the word {e['target']} meaning {e['english']} "
                                                                   f"to my {ls.name(lang)} words."}]))


def speak(settings: Settings, lang_name, text, topic) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    if hs.clean(text, 400):
        items = [{"text": line.strip(), "note": ""} for line in hs.clean(text, 400).replace("|", ".").split(".")
                 if line.strip()][:8] or [{"text": hs.clean(text, 200), "note": ""}]
        title = "Hear it"
    else:
        entries, title = ls.pool(found, lang, topic or "greetings")
        items = [{"text": e["target"], "note": e["english"] + (f" ({e['roman']})" if e["roman"] else "")}
                 for e in entries[:20]]
    payload = {"lang": lang, "name": ls.name(lang), "speech": data.LANGS[lang]["speech"], "items": items}
    return screen.Shown(f"Here it is in {ls.name(lang)}. Press Speak to hear it.", screen.card(
        "languages-say", f"{ls.name(lang)}: {title}", f"languages-say-{lang}", data=payload,
        text="Your browser's voice reads it; a slower speed is available."))


def pronunciation_tips(settings: Settings, lang_name) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    tips = data.TIPS[lang]
    return screen.Shown(f"Here are {len(tips)} pronunciation tips for {ls.name(lang)}.", screen.card(
        "list", f"{ls.name(lang)} pronunciation", f"languages-tips-{lang}",
        items=[{"label": t} for t in tips],
        buttons=[{"label": "Hear some words", "say": f"Say some {ls.name(lang)} greetings."}]))


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    lang = a("language")
    actions = {
        "languages": lambda: languages(settings),
        "set_language": lambda: set_language(settings, lang),
        "decks": lambda: decks(settings, lang),
        "flashcards": lambda: flashcards(settings, lang, a("topic"), a("direction"), a("count")),
        "review_due": lambda: flashcards(settings, lang, "due", a("direction"), a("count")),
        "save_review": lambda: save_review(settings, lang, a("results")),
        "add_word": lambda: add_word(settings, lang, a("word"), a("meaning"), a("note")),
        "my_words": lambda: my_words(settings, lang),
        "remove_word": lambda: remove_word(settings, lang, a("word"), a("confirmed")),
        "find_word": lambda: find_word(settings, lang, a("query")),
        "word_of_the_day": lambda: word_of_the_day(settings, lang),
        "speak": lambda: speak(settings, lang, a("text"), a("topic")),
        "pronunciation_tips": lambda: pronunciation_tips(settings, lang),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with language study.")
    return actions[a("action")]()
