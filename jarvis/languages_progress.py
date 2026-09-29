"""Language studio, progress: a minutes log with a daily goal and streak, a progress dashboard, a chart of minutes,
deck progress, what is due over the next week, recent quiz scores and the words you miss most.
Study on any day counts for the streak: minutes logged, cards reviewed or a quiz finished.
"""

from datetime import timedelta

import homestore as hs
import languages_store as ls
import screen
from config import Settings

screen.EXTRA_KINDS.add("languages-dash")

ACTIONS = ["log_minutes", "streak", "dashboard", "minutes_chart", "set_goal", "deck_progress", "due_forecast",
           "quiz_history", "weak_words", "reset_progress"]


def tool_definitions() -> list[dict]:
    text = {"type": "string"}
    return [{
        "name": "language_progress",
        "description": "Track language learning. Actions: 'log_minutes' (minutes, date default today) minutes "
                       "studied; 'streak' the daily streak; 'dashboard' progress pop-up (streak, minutes chart, "
                       "words learned, due cards, decks); 'minutes_chart' (days, default 14); 'set_goal' (goal "
                       "minutes a day); 'deck_progress' per topic; 'due_forecast' cards due over the next week; "
                       "'quiz_history' recent scores; 'weak_words' most-missed words; 'reset_progress' (language) "
                       "wipes a language's review schedule, set confirmed true only after the user agrees. "
                       "language defaults to the one being learned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "language": {**text, "description": "Spanish, French, German, Italian, Portuguese or Japanese."},
                "minutes": {"type": "number"}, "date": {**text, "description": "YYYY-MM-DD, today or yesterday."},
                "days": {"type": "integer"}, "goal": {"type": "integer", "description": "Minutes a day."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {t["name"] for t in tool_definitions()}


def _days(found: dict, count: int) -> tuple[list[str], list[float]]:
    today = hs.today()
    span = [today - timedelta(days=i) for i in range(count - 1, -1, -1)]
    return [f"{d.day} {d.strftime('%b')}" for d in span], [ls.minutes_on(found, d) for d in span]


def log_minutes(settings: Settings, minutes, day) -> str:
    found = ls.load(settings)
    when = hs.parse_day(day)
    if when > hs.today():
        raise ValueError("I can only log study that has already happened.")
    mins = hs.number(minutes, "minutes", 0.5, 600)
    row = ls.log_add(found, when, minutes=mins)
    ls.save(settings, found)
    current, _ = ls.streaks(found, hs.today())
    goal = found["goal"]
    left = max(0, goal - row["minutes"])
    goal_text = "Daily goal reached." if not left else f"{left:g} minutes to your goal of {goal}."
    return f"Logged {mins:g} minutes for {hs.spoken(when)}, {row['minutes']:g} in all. {goal_text} Streak: {hs.plural(current, 'day')}."


def streak(settings: Settings) -> str:
    found = ls.load(settings)
    current, best = ls.streaks(found, hs.today())
    if not best:
        return "No study logged yet. Do a few flashcards or log some minutes to start your streak."
    return f"Your streak is {hs.plural(current, 'day')}; your best is {hs.plural(best, 'day')}."


def dashboard(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    today = hs.today()
    current, best = ls.streaks(found, today)
    labels, values = _days(found, 14)
    rows = []
    for topic in ls.topics():
        recs = [ls.record(found, lang, e["key"]) for e in ls.deck(lang, topic)]
        rows.append({"name": ls.topic_name(topic), "total": len(recs), "learned": sum(map(ls.is_known, recs)),
                     "due": sum(ls.is_due(r, today) for r in recs)})
    quizzes = [q for q in found["quizzes"] if q["language"] == lang][-5:]
    average = round(sum(100 * q["score"] / q["total"] for q in quizzes) / len(quizzes)) if quizzes else None
    seen = len(found["cards"].get(lang, {}))
    payload = {"lang": lang, "name": ls.name(lang), "streak": current, "best": best,
               "today": ls.minutes_on(found, today), "goal": found["goal"],
               "week": {"labels": labels, "values": values}, "decks": rows, "seen": seen,
               "learned": sum(1 for r in found["cards"].get(lang, {}).values() if ls.is_known(r)),
               "due": len(ls.due_entries(found, lang)), "own": len(found["words"].get(lang, [])),
               "average": average}
    text = (f"{ls.name(lang)}: streak {hs.plural(current, 'day')}, {payload['learned']} words learned, "
            f"{payload['due']} due.")
    return screen.Shown(text, screen.card(
        "languages-dash", f"{ls.name(lang)} progress", f"languages-dash-{lang}", data=payload,
        buttons=[{"label": "Review due", "say": f"Review my due {ls.name(lang)} cards."},
                 {"label": "Quiz me", "say": f"Quiz me in {ls.name(lang)}."}]))


def minutes_chart(settings: Settings, days) -> screen.Shown:
    found = ls.load(settings)
    n = int(hs.number(days or 14, "number of days", 3, 60))
    labels, values = _days(found, n)
    total = sum(values)
    return screen.Shown(f"You studied {total:g} minutes in the last {n} days.", screen.card(
        "chart", f"Study minutes, last {n} days", "languages-minutes", chart={"type": "bar", "labels": labels,
                                                                              "values": values, "unit": " min"}))


def set_goal(settings: Settings, goal) -> str:
    found = ls.load(settings)
    found["goal"] = int(hs.number(goal, "goal", 1, 600))
    ls.save(settings, found)
    return f"Your daily goal is now {found['goal']} minutes."


def deck_progress(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    today = hs.today()
    rows = []
    for topic in ls.topics():
        recs = [ls.record(found, lang, e["key"]) for e in ls.deck(lang, topic)]
        rows.append([ls.topic_name(topic), str(len(recs)), str(sum(1 for r in recs if r)),
                     str(sum(map(ls.is_known, recs))), str(sum(ls.is_due(r, today) for r in recs))])
    learned = sum(int(r[3]) for r in rows)
    return screen.Shown(f"{learned} {ls.name(lang)} starter words learned so far.", screen.card(
        "table", f"{ls.name(lang)} deck progress", f"languages-progress-{lang}",
        columns=["Deck", "Words", "Started", "Learned", "Due"], rows=rows))


def due_forecast(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    today = hs.today()
    counts = [0] * 7
    for rec in found["cards"].get(lang, {}).values():
        try:
            offset = (hs.parse_day(rec["due"]) - today).days
        except ValueError:
            continue
        if offset < 7:
            counts[max(0, offset)] += 1
    labels = ["Today"] + [(today + timedelta(days=i)).strftime("%a") for i in range(1, 7)]
    return screen.Shown(f"{counts[0]} {ls.name(lang)} cards are due today and {sum(counts[1:])} more this week.",
                        screen.card("chart", f"{ls.name(lang)} cards due", f"languages-forecast-{lang}",
                                    chart={"type": "bar", "labels": labels, "values": counts, "unit": ""}))


def quiz_history(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    quizzes = [q for q in found["quizzes"] if q["language"] == lang][-15:]
    if not quizzes:
        raise ValueError(f"No {ls.name(lang)} quizzes saved yet. Say 'quiz me' to try one.")
    rows = [[q["date"], q["label"], f"{q['score']}/{q['total']}", f"{round(100 * q['score'] / q['total'])}%"]
            for q in reversed(quizzes)]
    last = quizzes[-1]
    return screen.Shown(f"Your last {ls.name(lang)} quiz was {last['score']} out of {last['total']}.", screen.card(
        "table", f"{ls.name(lang)} quiz scores", f"languages-history-{lang}",
        columns=["Date", "Quiz", "Score", "%"], rows=rows))


def weak_words(settings: Settings, lang_name) -> screen.Shown:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    lapses = {k: r.get("lapses", 0) for k, r in found["cards"].get(lang, {}).items() if r.get("lapses")}
    if not lapses:
        raise ValueError("No missed words yet. Nice, or you haven't started. Try some flashcards.")
    lookup = {e["key"]: e for e in ls.everything(found, lang) + ls.deck(lang, "numbers")}
    worst = sorted(lapses, key=lambda k: -lapses[k])[:10]
    items = [{"label": f"{lookup[k]['target']}: {lookup[k]['english']} (missed {lapses[k]})",
              "say": f"Say {lookup[k]['target']} in {ls.name(lang)}."} for k in worst if k in lookup]
    return screen.Shown(f"Your trickiest {ls.name(lang)} word is {worst[0]}.", screen.card(
        "list", f"{ls.name(lang)} words to watch", f"languages-weak-{lang}", items=items,
        buttons=[{"label": "Drill due", "say": f"Review my due {ls.name(lang)} cards."}]))


def reset_progress(settings: Settings, lang_name, confirmed) -> str:
    found = ls.load(settings)
    lang = ls.language(found, lang_name)
    if not confirmed:
        return (f"This wipes your {ls.name(lang)} review schedule (your own words and study log stay). "
                "Shall I go ahead?")
    found["cards"].pop(lang, None)
    ls.save(settings, found)
    return f"Cleared your {ls.name(lang)} review schedule."


def run_tool(name: str, args: dict, settings: Settings, http=None):
    a = args.get
    lang = a("language")
    actions = {
        "log_minutes": lambda: log_minutes(settings, a("minutes"), a("date")),
        "streak": lambda: streak(settings),
        "dashboard": lambda: dashboard(settings, lang),
        "minutes_chart": lambda: minutes_chart(settings, a("days")),
        "set_goal": lambda: set_goal(settings, a("goal")),
        "deck_progress": lambda: deck_progress(settings, lang),
        "due_forecast": lambda: due_forecast(settings, lang),
        "quiz_history": lambda: quiz_history(settings, lang),
        "weak_words": lambda: weak_words(settings, lang),
        "reset_progress": lambda: reset_progress(settings, lang, a("confirmed")),
    }
    if a("action") not in actions:
        raise ValueError(f"I can't do {a('action')} with language progress.")
    return actions[a("action")]()
