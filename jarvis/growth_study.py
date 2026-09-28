"""Studying: flashcard decks with Leitner-box spaced repetition, language phrases, and study hours per subject.

Decks live in growth-flashcards.json and study sessions in growth-study.json in the memory folder.
"""

import random
from datetime import date, timedelta

import growth_store as store
from config import Settings

MAX_DECKS = 50
MAX_CARDS = 1000
# Days until a card in box 1..5 is due again after a right answer.
BOX_DAYS = {1: 1, 2: 2, 3: 4, 4: 7, 5: 14}

PHRASES = {
    "afrikaans": [
        ("Goeie môre", "Good morning"), ("Hoe gaan dit?", "How are you?"),
        ("Dit gaan goed, dankie", "I'm fine, thanks"), ("Baie dankie", "Thank you very much"),
        ("Asseblief", "Please"), ("Totsiens", "Goodbye"), ("Ek is jammer", "I'm sorry"),
        ("Wat is jou naam?", "What is your name?"), ("My naam is ...", "My name is ..."),
        ("Ek verstaan nie", "I don't understand"), ("Praat jy Engels?", "Do you speak English?"),
        ("Hoeveel kos dit?", "How much does it cost?"), ("Waar is die badkamer?", "Where is the bathroom?"),
        ("Lekker slaap", "Sleep well"), ("Baie geluk!", "Congratulations!"),
    ],
    "zulu": [
        ("Sawubona", "Hello (to one person)"), ("Sanibonani", "Hello (to a group)"),
        ("Unjani?", "How are you?"), ("Ngiyaphila, wena unjani?", "I'm fine, and you?"),
        ("Ngiyabonga", "Thank you"), ("Ngiyabonga kakhulu", "Thank you very much"),
        ("Hamba kahle", "Goodbye (to someone leaving)"), ("Sala kahle", "Goodbye (to someone staying)"),
        ("Yebo", "Yes"), ("Cha", "No"), ("Ngubani igama lakho?", "What is your name?"),
        ("Igama lami ngu...", "My name is ..."), ("Angiqondi", "I don't understand"),
        ("Ngiyaxolisa", "I'm sorry"), ("Kubiza malini?", "How much does it cost?"),
    ],
    "spanish": [
        ("Buenos días", "Good morning"), ("¿Cómo estás?", "How are you?"),
        ("Estoy bien, gracias", "I'm fine, thanks"), ("Muchas gracias", "Thank you very much"),
        ("Por favor", "Please"), ("Adiós", "Goodbye"), ("Lo siento", "I'm sorry"),
        ("¿Cómo te llamas?", "What is your name?"), ("Me llamo ...", "My name is ..."),
        ("No entiendo", "I don't understand"), ("¿Hablas inglés?", "Do you speak English?"),
        ("¿Cuánto cuesta?", "How much does it cost?"), ("¿Dónde está el baño?", "Where is the bathroom?"),
        ("Hasta mañana", "See you tomorrow"), ("¡Felicidades!", "Congratulations!"),
    ],
    "french": [
        ("Bonjour", "Good morning / hello"), ("Comment ça va ?", "How are you?"),
        ("Ça va bien, merci", "I'm fine, thanks"), ("Merci beaucoup", "Thank you very much"),
        ("S'il vous plaît", "Please"), ("Au revoir", "Goodbye"), ("Je suis désolé", "I'm sorry"),
        ("Comment vous appelez-vous ?", "What is your name?"), ("Je m'appelle ...", "My name is ..."),
        ("Je ne comprends pas", "I don't understand"), ("Parlez-vous anglais ?", "Do you speak English?"),
        ("C'est combien ?", "How much does it cost?"), ("Où sont les toilettes ?", "Where are the toilets?"),
        ("À demain", "See you tomorrow"), ("Félicitations !", "Congratulations!"),
    ],
}


def _decks(settings: Settings) -> dict:
    return store.load(settings, "flashcards", {"decks": [], "pending": None})


def _deck(data: dict, name: str) -> dict:
    deck = store.find(data["decks"], "name", name) if name else (data["decks"][0] if len(data["decks"]) == 1 else None)
    if deck is None:
        have = ", ".join(d["name"] for d in data["decks"]) or "none yet"
        raise ValueError(f"Which deck? Decks: {have}.")
    return deck


def new_deck(settings: Settings, name: str) -> str:
    name = store.need(name, "deck name", 60)
    data = _decks(settings)
    if any(d["name"].lower() == name.lower() for d in data["decks"]):
        return f"You already have a {name} deck."
    if len(data["decks"]) >= MAX_DECKS:
        raise ValueError("That's a lot of decks already.")
    data["decks"].append({"name": name, "cards": []})
    store.save(settings, "flashcards", data)
    return f"Made a new deck called {name}."


def add_card(settings: Settings, deck_name: str, front: str, back: str, today: date) -> str:
    front, back = store.need(front, "front of the card"), store.need(back, "back of the card")
    data = _decks(settings)
    deck = _deck(data, deck_name)
    if len(deck["cards"]) >= MAX_CARDS:
        raise ValueError("That deck is full.")
    deck["cards"].append({"front": front, "back": back, "box": 1, "due": today.isoformat(), "right": 0, "wrong": 0})
    store.save(settings, "flashcards", data)
    return f"Added a card to {deck['name']}. It has {store.plural(len(deck['cards']), 'card')}."


def _due(deck: dict, today: date) -> list[dict]:
    return [c for c in deck["cards"] if c["due"] <= today.isoformat()]


def quiz(settings: Settings, deck_name: str, today: date) -> str:
    data = _decks(settings)
    deck = _deck(data, deck_name)
    due = sorted(_due(deck, today), key=lambda c: (c["box"], c["due"]))
    if not due:
        return f"Nothing due in {deck['name']} today. Well done."
    card = due[0]
    data["pending"] = {"deck": deck["name"], "front": card["front"]}
    store.save(settings, "flashcards", data)
    return (f"{deck['name']} card ({len(due)} due). Ask: {card['front']}\n"
            f"Answer (keep it hidden until they reply, then report right or wrong): {card['back']}")


def answer(settings: Settings, right: bool, today: date) -> str:
    data = _decks(settings)
    pending = data.get("pending")
    deck = store.find(data["decks"], "name", pending["deck"]) if pending else None
    card = next((c for c in deck["cards"] if c["front"] == pending["front"]), None) if deck else None
    if card is None:
        return "There's no card waiting for an answer. Ask me to quiz you first."
    if right:
        card["box"] = min(card["box"] + 1, 5)
        card["right"] += 1
        card["due"] = (today + timedelta(days=BOX_DAYS[card["box"]])).isoformat()
    else:
        card["box"] = 1
        card["wrong"] += 1
        card["due"] = today.isoformat()
    data["pending"] = None
    store.save(settings, "flashcards", data)
    left = len(_due(deck, today))
    verdict = f"Right. Moved to box {card['box']}." if right else "Not quite. Back to box 1."
    return f"{verdict} {store.plural(left, 'card')} still due in {deck['name']}."


def stats(settings: Settings, deck_name: str, today: date) -> str:
    data = _decks(settings)
    if not data["decks"]:
        return "No flashcard decks yet."
    decks = [_deck(data, deck_name)] if deck_name else data["decks"]
    lines = []
    for deck in decks:
        cards = deck["cards"]
        right, wrong = sum(c["right"] for c in cards), sum(c["wrong"] for c in cards)
        score = f", {round(100 * right / (right + wrong))}% right so far" if right + wrong else ""
        boxes = ", ".join(f"box {b}: {n}" for b in range(1, 6) if (n := sum(c["box"] == b for c in cards)))
        lines.append(f"- {deck['name']}: {store.plural(len(cards), 'card')}, {len(_due(deck, today))} due today"
                     f"{score}" + (f" ({boxes})" if boxes else ""))
    return "Flashcards:\n" + "\n".join(lines)


def _language(name: str) -> str:
    key = store.clean(name).lower()
    key = {"isizulu": "zulu", "espanol": "spanish", "español": "spanish", "francais": "french",
           "français": "french"}.get(key, key)
    if key not in PHRASES:
        raise ValueError("I have phrases in Afrikaans, Zulu, Spanish and French.")
    return key


def phrase_of_day(language: str, today: date) -> str:
    key = _language(language)
    phrase, meaning = PHRASES[key][today.toordinal() % len(PHRASES[key])]
    return f"Today's {key.title()} phrase: {phrase}. It means: {meaning}."


def phrase_quiz(language: str, pick=random.choice) -> str:
    key = _language(language)
    phrase, meaning = pick(PHRASES[key])
    return (f"{key.title()} quiz. Ask what this means: {phrase}\n"
            f"Answer (keep it hidden until they reply): {meaning}")


def log_study(settings: Settings, subject: str, minutes, today: date) -> str:
    subject = store.need(subject, "subject", 60)
    minutes = store.number(minutes, "minutes")
    if not 0 < minutes <= 24 * 60:
        raise ValueError("How many minutes did you study?")
    log = store.load(settings, "study", [])
    log.append({"date": today.isoformat(), "subject": subject, "minutes": minutes})
    store.save(settings, "study", log[-5000:])
    total = sum(e["minutes"] for e in log if e["subject"].lower() == subject.lower() and store.this_week(e["date"], today))
    return f"Logged {minutes:g} minutes of {subject}. This week: {_hours(total)} on it."


def _hours(minutes: float) -> str:
    hours, mins = divmod(round(minutes), 60)
    parts = ([store.plural(hours, "hour")] if hours else []) + ([store.plural(mins, "minute")] if mins or not hours else [])
    return " ".join(parts)


def study_week(settings: Settings, today: date) -> str:
    totals: dict[str, float] = {}
    for e in store.load(settings, "study", []):
        if store.this_week(e["date"], today):
            key = next((k for k in totals if k.lower() == e["subject"].lower()), e["subject"])
            totals[key] = totals.get(key, 0) + e["minutes"]
    if not totals:
        return "No study time logged this week."
    lines = "\n".join(f"- {s}: {_hours(m)}" for s, m in sorted(totals.items(), key=lambda kv: -kv[1]))
    return f"Study this week, {_hours(sum(totals.values()))} in all:\n{lines}"


ACTIONS = ["new_deck", "add_card", "quiz", "answer", "deck_stats",
           "phrase_of_day", "phrase_quiz", "log_study", "study_week"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "study",
        "description": "Flashcards, language phrases and study time. new_deck/add_card (deck, front, back); quiz "
                       "gives the next due card of a deck with its hidden answer, then answer with right=true/false "
                       "(spaced repetition); deck_stats. phrase_of_day and phrase_quiz for a language (Afrikaans, "
                       "Zulu, Spanish, French). log_study (subject, minutes) and study_week gives this week's totals.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "deck": {"type": "string"},
                "front": {"type": "string", "description": "Question side of a card."},
                "back": {"type": "string", "description": "Answer side of a card."},
                "right": {"type": "boolean", "description": "For answer: did they get it right?"},
                "language": {"type": "string", "enum": ["Afrikaans", "Zulu", "Spanish", "French"]},
                "subject": {"type": "string"},
                "minutes": {"type": "number"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"study"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action, today = args.get("action"), store.today()
    deck = args.get("deck") or ""
    if action == "new_deck":
        return new_deck(settings, deck)
    if action == "add_card":
        return add_card(settings, deck, args.get("front"), args.get("back"), today)
    if action == "quiz":
        return quiz(settings, deck, today)
    if action == "answer":
        return answer(settings, bool(args.get("right")), today)
    if action == "deck_stats":
        return stats(settings, deck, today)
    if action == "phrase_of_day":
        return phrase_of_day(args.get("language") or "", today)
    if action == "phrase_quiz":
        return phrase_quiz(args.get("language") or "")
    if action == "log_study":
        return log_study(settings, args.get("subject"), args.get("minutes"), today)
    if action == "study_week":
        return study_week(settings, today)
    raise ValueError(f"Unknown study action: {action}")
