"""Language studio, practice: multiple-choice and typing quizzes, gender and article drills, number and
time-telling practice, verb conjugation tables and drills, and short role-play dialogues, all as pop-ups drawn by
frontend/popup-languages.js. A finished quiz sends its score back with save_result, which puts missed words back
into the spaced-repetition queue.
"""

import random
import re

import homestore as hs
import languages_data as data
import languages_store as ls
import languages_talk as talk
import languages_verbs as verbs
import screen
from config import Settings

for _kind in ("languages-quiz", "languages-conjugate", "languages-dialogue"):
    screen.EXTRA_KINDS.add(_kind)

ACTIONS = ["vocab_quiz", "article_drill", "number_practice", "time_practice", "conjugation", "verb_list",
           "conjugation_drill", "dialogue", "dialogue_list", "save_result"]
ARTICLES = {"es": ["el", "la"], "fr": ["le", "la"], "de": ["der", "die", "das"], "it": ["il", "la"], "pt": ["o", "a"]}
MAX_QUESTIONS = 20
rng = random.Random()


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "language_practice",
        "description": "Practise a language in a pop-up. Actions: 'vocab_quiz' (topic: greetings, food, travel, "
                       "family, time, home, numbers, mine, due or mix; kind choice or typing; direction "
                       "to_english or from_english; count); 'article_drill' (mode article or gender: der/die/das, "
                       "el/la); 'number_practice' (up_to 10, 20 or 100; direction; kind); 'time_practice' telling "
                       "the time in the language with a clock face; 'conjugation' table (verb, optional tense "
                       "present/past/future); 'verb_list'; 'conjugation_drill' (type the right verb form); "
                       "'dialogue' role-play practice (scene cafe or directions); 'dialogue_list'; 'save_result' "
                       "(label, score, total, wrong 'a; b') sent by a finished quiz. language defaults to the "
                       "one being learned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "language": {**text, "description": "Spanish, French, German, Italian, Portuguese or Japanese."},
                "topic": text, "kind": {"type": "string", "enum": ["choice", "typing"]},
                "direction": {"type": "string", "enum": ["to_english", "from_english"]},
                "mode": {"type": "string", "enum": ["article", "gender"]},
                "count": {"type": "integer", "description": "Questions, 1 to 20 (default 10)."},
                "up_to": {"type": "integer", "description": "number_practice: 10, 20 or 100."},
                "verb": text, "tense": {"type": "string", "enum": ["present", "past", "future"]},
                "scene": text, "label": text, "score": {"type": "integer"}, "total": {"type": "integer"},
                "wrong": {**text, "description": "save_result: the missed words, separated by ;"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {t["name"] for t in tool_definitions()}


# ---- quiz building -------------------------------------------------------------------------------------

def _shown(lang: str, title: str, label: str, questions: list[dict], spoken: str) -> screen.Shown:
    payload = {"lang": lang, "name": ls.name(lang), "speech": data.LANGS[lang]["speech"], "label": label,
               "questions": questions}
    return screen.Shown(spoken, screen.card("languages-quiz", title, f"languages-quiz-{lang}", data=payload))


def _count(count) -> int:
    return int(hs.number(count or 10, "number of questions", 1, MAX_QUESTIONS))


def _shown_text(e: dict) -> str:
    return f"{e['target']} ({e['roman']})" if e["roman"] else e["target"]


def _options(right: str, pool: list[str]) -> list[str]:
    others = [p for p in dict.fromkeys(pool) if p != right]
    rng.shuffle(others)
    options = others[:3] + [right]
    rng.shuffle(options)
    return options


def _variants(*texts: str) -> list[str]:
    return [t for t in dict.fromkeys(x for x in texts if x)]


def vocab_quiz(settings: Settings, lang_name, topic, kind, direction, count) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    entries, title = ls.pool(found, lang, topic or "mix")
    if not entries:
        raise ValueError("There's nothing to quiz on there yet.")
    picked = rng.sample(entries, min(_count(count), len(entries)))
    wide = entries + ls.everything(found, lang) + ls.deck(lang, "numbers")
    back, typing = direction == "from_english", kind == "typing"
    questions = []
    for e in picked:
        if back:
            prompt, answer, options = e["english"], _shown_text(e), [_shown_text(x) for x in wide]
            accept = _variants(e["target"], e["word"], e["roman"])
        else:
            prompt, answer, options = _shown_text(e), e["english"], [x["english"] for x in wide]
            accept = _variants(e["english"])
        q = {"prompt": prompt, "answer": answer, "key": e["key"], "kind": "type" if typing else "choice",
             "say": e["target"], "hint": "Type it in the language." if back else "Type the English."}
        if typing:
            q["accept"] = accept
        else:
            q["options"] = _options(answer, options)
        questions.append(q)
    label = f"{title.lower()} vocabulary"
    return _shown(lang, f"{ls.name(lang)} quiz: {title}", label, questions,
                  f"{len(questions)} {ls.name(lang)} questions. Pick or type your answers.")


def article_drill(settings: Settings, lang_name, mode, count) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    if lang == "ja":
        raise ValueError("Japanese has no articles or genders, so there's nothing to drill. Try numbers or verbs.")
    gender = mode == "gender"
    nouns = [e for t in data.TOPIC_NAMES for e in ls.deck(lang, t) if e["gender"]]
    if not gender:
        nouns = [e for e in nouns if e["article"] in ARTICLES[lang]]
    picked = rng.sample(nouns, min(_count(count), len(nouns)))
    names = [ls.GENDERS[g] for g in ("m", "f", "n") if g != "n" or lang == "de"]
    questions = []
    for e in picked:
        answer = ls.GENDERS[e["gender"]] if gender else e["article"]
        questions.append({
            "prompt": f"{e['word']}  ({e['english']})", "kind": "choice", "options": names if gender else ARTICLES[lang],
            "answer": answer, "key": e["key"], "say": e["target"],
            "hint": "Masculine, feminine or neuter?" if gender else "Which article goes with it?",
            "explain": f"It's {e['target']}."})
    what = "gender" if gender else "article"
    return _shown(lang, f"{ls.name(lang)} {what} drill", f"{what} drill", questions,
                  f"{len(questions)} {what} questions in {ls.name(lang)}.")


def number_practice(settings: Settings, lang_name, direction, kind, up_to, count) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    limit = int(hs.number(up_to or 20, "top number", 1, 100))
    entries = [e for e in ls.deck(lang, "numbers") if int(e["english"]) <= max(limit, 10)]
    picked = rng.sample(entries, min(_count(count), len(entries)))
    to_number, typing = direction == "to_english", kind == "typing"
    questions = []
    for e in picked:
        if to_number:
            prompt, answer, options = _shown_text(e), e["english"], [x["english"] for x in entries]
            accept = [e["english"]]
        else:
            prompt, answer, options = e["english"], _shown_text(e), [_shown_text(x) for x in entries]
            accept = _variants(e["target"], e["roman"])
        q = {"prompt": prompt, "answer": answer, "kind": "type" if typing else "choice", "say": e["target"],
             "key": e["key"], "hint": "Type the number." if to_number else "Say or type it in the language."}
        q.update({"accept": accept} if typing else {"options": _options(answer, options)})
        questions.append(q)
    return _shown(lang, f"{ls.name(lang)} numbers", "numbers", questions,
                  f"{len(questions)} number questions in {ls.name(lang)}, up to {max(limit, 10)}.")


def _time_text(lang: str, hour: int, minute: int) -> tuple[str, str]:
    return talk.clock(lang, hour, minute)


def time_practice(settings: Settings, lang_name, direction, kind, count) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    times = [(h, m) for h in range(1, 13) for m in range(0, 60, 5)]
    picked = rng.sample(times, _count(count))
    read, typing = direction == "to_english", kind == "typing"
    digital = {t: f"{t[0]}:{t[1]:02d}" for t in times}
    questions = []
    for h, m in picked:
        words, roman = _time_text(lang, h, m)
        spoken = f"{words} ({roman})" if roman else words
        clock = {"h": h, "m": m}
        if read:
            q = {"prompt": spoken, "answer": digital[(h, m)], "kind": "choice", "say": words, "clock": clock,
                 "options": _options(digital[(h, m)], list(digital.values())), "hint": "What time is it?"}
        else:
            q = {"prompt": digital[(h, m)], "answer": spoken, "say": words, "clock": clock,
                 "hint": "Say the time in the language."}
            if typing:
                q.update({"kind": "type", "accept": _variants(words, roman)})
            else:
                others = [_time_text(lang, *t) for t in rng.sample(times, 12)]
                q.update({"kind": "choice", "options": _options(spoken, [f"{w} ({r})" if r else w for w, r in others])})
        questions.append(q)
    return _shown(lang, f"{ls.name(lang)} time-telling", "time-telling", questions,
                  f"{len(questions)} time questions in {ls.name(lang)}.")


# ---- verbs ---------------------------------------------------------------------------------------------

def _verb(lang: str, name) -> str:
    verb = verbs.find_verb(lang, name)
    if not verb:
        raise ValueError(f"I don't have {hs.clean(name) or 'that verb'} for {ls.name(lang)}. "
                         f"I know {', '.join(verbs.verb_names(lang))}.")
    return verb


def conjugation(settings: Settings, lang_name, verb, tense) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    if not hs.clean(verb):
        return verb_list(settings, lang_name)
    key = _verb(lang, verb)
    table = verbs.table(lang, key)
    order = ("present", "past", "future")
    if tense in order:
        table["tenses"] = [table["tenses"][order.index(tense)]]
    first = table["tenses"][0]
    forms = ", ".join(r[1] for r in first["rows"])
    payload = {"lang": lang, "name": ls.name(lang), "speech": data.LANGS[lang]["speech"], **table}
    return screen.Shown(f"{key} means {table['meaning']}. {first['name']}: {forms}.", screen.card(
        "languages-conjugate", f"{ls.name(lang)}: {key}", f"languages-verb-{lang}", data=payload,
        buttons=[{"label": "Drill me", "say": f"Drill me on {ls.name(lang)} verb {key}."}]))


def verb_list(settings: Settings, lang_name) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    items = [{"label": f"{v}: {verbs.VERBS[lang][v]['meaning']}", "say": f"Conjugate {v} in {ls.name(lang)}."}
             for v in verbs.verb_names(lang)]
    return screen.Shown(f"I have {len(items)} {ls.name(lang)} verbs with tables.", screen.card(
        "list", f"{ls.name(lang)} verbs", f"languages-verbs-{lang}", items=items))


def _expand(form: str) -> list[str]:
    """Spellings a learner may type: without optional (e) parts, and each of a/o style gender pairs."""
    out = {form}
    out |= {re.sub(r"\(([^)]*)\)", "", form)}
    for f in list(out):
        for match in re.finditer(r"(\w)/(\w)\b", f):
            out |= {f.replace(match.group(0), match.group(1)), f.replace(match.group(0), match.group(2))}
    return list(out)


def _joined(person: str, form: str) -> str:
    return person + form if person.endswith("'") else f"{person} {form}"


def conjugation_drill(settings: Settings, lang_name, verb, tense, kind, count) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    if lang == "ja":
        raise ValueError("Japanese verbs don't change with the person. Ask for a Japanese verb table instead.")
    names = [_verb(lang, verb)] if hs.clean(verb) else verbs.verb_names(lang)
    order = ("present", "past", "future")
    rows = []
    for v in names:
        table = verbs.table(lang, v)
        for i, t in enumerate(table["tenses"]):
            if tense in order and order.index(tense) != i:
                continue
            rows += [(v, table["meaning"], t["name"], r[0], r[1]) for r in t["rows"]]
    picked = rng.sample(rows, min(_count(count), len(rows)))
    questions = []
    for v, meaning, tense_name, person, form in picked:
        q = {"prompt": f"{v} ({meaning}): {person} ... {tense_name}", "answer": form, "say": _joined(person, form),
             "hint": "Type the verb form.", "kind": "type" if kind == "typing" else "choice"}
        others = [rr[4] for rr in rows if rr[0] == v and rr[2] == tense_name]
        if kind == "typing":
            q["accept"] = _variants(*_expand(form), *(_joined(person.split("/")[0], f) for f in _expand(form)))
        else:
            q["options"] = _options(form, others + [r[4] for r in rows if r[0] == v])
        questions.append(q)
    return _shown(lang, f"{ls.name(lang)} verb drill", "verb drill", questions,
                  f"{len(questions)} verb questions in {ls.name(lang)}.")


# ---- dialogues -----------------------------------------------------------------------------------------

def _scene(text) -> str | None:
    want = ls.strip_marks(text)
    if not want:
        return None
    for key, title in talk.SCENES.items():
        if want == key or want in ls.strip_marks(title) or (key == talk.CAFE and want in ("coffee", "restaurant")) \
                or (key == talk.STATION and want in ("way", "station", "direction")):
            return key
    return None


def dialogue_list(settings: Settings, lang_name) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    items = [{"label": title, "say": f"Role-play {key} in {ls.name(lang)}."} for key, title in talk.SCENES.items()]
    return screen.Shown(f"Two role-plays for {ls.name(lang)}: ordering in a café and asking the way.", screen.card(
        "list", f"{ls.name(lang)} role-plays", f"languages-scenes-{lang}", items=items))


def dialogue(settings: Settings, lang_name, scene) -> screen.Shown:
    lang = ls.language(ls.load(settings), lang_name)
    key = _scene(scene)
    if not key:
        return dialogue_list(settings, lang_name)
    turns = []
    for turn in talk.DIALOGUES[lang][key]:
        if turn[0] == "them":
            turns.append({"who": "them", "text": turn[1], "en": turn[2], "roman": turn[3]})
            continue
        right = turn[1][0]
        options = list(turn[1])
        rng.shuffle(options)
        turns.append({"who": "you", "correct": options.index(right),
                      "options": [{"text": o[0], "en": o[1], "roman": o[2]} for o in options]})
    payload = {"lang": lang, "name": ls.name(lang), "speech": data.LANGS[lang]["speech"], "scene": key,
               "turns": turns}
    return screen.Shown(f"Role-play: {talk.SCENES[key].lower()}. Choose your replies.", screen.card(
        "languages-dialogue", f"{ls.name(lang)}: {talk.SCENES[key]}", f"languages-dialogue-{lang}", data=payload))


# ---- results -------------------------------------------------------------------------------------------

def save_result(settings: Settings, lang_name, label, score, total, wrong) -> str:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    total = int(hs.number(total, "total", 1, 1000))
    score = int(hs.number(score, "score", 0, total))
    today = hs.today()
    known = {e["key"] for e in ls.everything(found, lang) + ls.deck(lang, "numbers")}
    missed = [k.strip().lower() for k in str(wrong or "").split(";") if k.strip().lower() in known]
    for key in missed:
        ls.grade(found, lang, key, "again", today)
    ls.log_add(found, today, quizzes=1)
    found["quizzes"].append({"date": today.isoformat(), "language": lang, "label": hs.clean(label, 60) or "quiz",
                             "score": score, "total": total})
    found["quizzes"] = found["quizzes"][-ls.MAX_QUIZZES:]
    ls.save(settings, found)
    percent = round(100 * score / total)
    tail = f" I've put {hs.plural(len(missed), 'missed word')} back in your review queue." if missed else ""
    cheer = "Brilliant!" if percent >= 90 else "Good going." if percent >= 60 else "Keep at it, it sticks with practice."
    return f"Saved: {score} out of {total}, {percent} percent. {cheer}{tail}"


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    lang, kind = a("language"), a("kind")
    actions = {
        "vocab_quiz": lambda: vocab_quiz(settings, lang, a("topic"), kind, a("direction"), a("count")),
        "article_drill": lambda: article_drill(settings, lang, a("mode"), a("count")),
        "number_practice": lambda: number_practice(settings, lang, a("direction"), kind, a("up_to"), a("count")),
        "time_practice": lambda: time_practice(settings, lang, a("direction"), kind, a("count")),
        "conjugation": lambda: conjugation(settings, lang, a("verb"), a("tense")),
        "verb_list": lambda: verb_list(settings, lang),
        "conjugation_drill": lambda: conjugation_drill(settings, lang, a("verb"), a("tense"), kind, a("count")),
        "dialogue": lambda: dialogue(settings, lang, a("scene")),
        "dialogue_list": lambda: dialogue_list(settings, lang),
        "save_result": lambda: save_result(settings, lang, a("label"), a("score"), a("total"), a("wrong")),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with language practice.")
    return actions[a("action")]()
