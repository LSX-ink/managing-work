"""Calm for the mind: daily affirmations (and your own), a kindness idea of the day, looking back at what you were grateful
for a month ago, a worry list with a "worry time" and a let it go button, and a quick calm check-in with a chart.

Saved on this PC in calm-affirmations.json, calm-kindness.json, calm-worries.json and calm-checkins.json. The gratitude
notes themselves are added with the routines ability and only read here. Anything that sounds like a crisis is answered
with Samaritans and NHS 111 and is not saved.
"""

import random
from datetime import date

import calm_data as data
import calm_exercises
import calm_store as store
import screen
import wellness_store
from config import Settings

NAMES = {"calm_mind"}
ACTIONS = ["affirmation", "affirmation_add", "affirmation_list", "affirmation_remove", "kindness", "kindness_done",
           "gratitude_lookback", "worry_add", "worry_list", "worry_time", "worry_time_set", "worry_let_go",
           "worry_clear", "checkin", "checkin_history"]
GRATITUDE_FILE = "routines-gratitude.json"


# Affirmations

def _daily(pool: list[str], offset: int = 0) -> str:
    return pool[(store.today().toordinal() + offset) % len(pool)]


def affirmation(settings: Settings, another: bool) -> screen.Shown:
    own = store.load(settings, "affirmations", [])
    pool = data.AFFIRMATIONS + [str(a) for a in own]
    line = random.choice(pool) if another else _daily(pool)
    card = screen.card("text", "Today's affirmation", "calm-affirmation", text=line,
                       buttons=[{"label": "Another", "say": "Give me another affirmation"}])
    return screen.Shown(line, card)


def affirmation_add(settings: Settings, text) -> str:
    line = store.need(text, "affirmation", 160)
    own = store.load(settings, "affirmations", [])
    if line in own:
        return "That one is already in your list."
    store.save(settings, "affirmations", (own + [line])[-100:])
    return f"Added to your affirmations. You have {len(own) + 1} of your own."


def affirmation_list(settings: Settings) -> str | screen.Shown:
    own = store.load(settings, "affirmations", [])
    if not own:
        return "You haven't added any affirmations of your own yet."
    card = screen.card("list", "My affirmations", "calm-affirmations", items=[{"label": a} for a in own])
    return screen.Shown(f"You have {len(own)} affirmations of your own; they're on the screen.", card)


def affirmation_remove(settings: Settings, words, confirmed: bool) -> str:
    own = store.load(settings, "affirmations", [])
    key = store.clean(words).lower()
    found = [a for a in own if key and key in a.lower()]
    if not found:
        raise ValueError("None of your affirmations match that.")
    if not confirmed:
        return f"That matches: {'; '.join(found)}. Ask the user to confirm, then call again with confirmed true."
    store.save(settings, "affirmations", [a for a in own if a not in found])
    return f"Removed {store.plural(len(found), 'affirmation')}."


# Kindness

def kindness(settings: Settings) -> screen.Shown:
    idea = _daily(data.KINDNESS)
    done = {r["date"] for r in store.load(settings, "kindness", [])}
    said = f"Kindness idea for today: {idea}"
    text = idea + ("\n\nDone today." if store.today().isoformat() in done else "")
    card = screen.card("text", "Kindness of the day", "calm-kindness", text=text,
                       buttons=[{"label": "I did it", "say": f"I did my kindness of the day: {idea}"}])
    return screen.Shown(said, card)


def kindness_done(settings: Settings, note) -> str:
    rows = store.load(settings, "kindness", [])
    rows.append({"date": store.today().isoformat(), "note": store.clean(note, 160) or _daily(data.KINDNESS)})
    store.save(settings, "kindness", rows[-500:])
    return f"Lovely. That's {store.plural(len(rows), 'kind act')} logged in total."


# Gratitude look-back

def _months_back(day: date, months: int) -> date | None:
    year, month = divmod(day.year * 12 + day.month - 1 - months, 12)
    try:
        return date(year, month + 1, day.day)
    except ValueError:
        return None


def gratitude_lookback(settings: Settings, span) -> str | screen.Shown:
    span = store.clean(span).lower()
    months = 12 if "year" in span else 1
    then = _months_back(store.today(), months)
    rows = store.hs.load(settings, GRATITUDE_FILE, {})
    things = rows.get(then.isoformat()) if then else None
    label = "a year ago" if months == 12 else "a month ago"
    if not things:
        return f"I don't have anything you were grateful for {label} today."
    card = screen.card("list", f"Grateful {label}", "calm-lookback", items=[{"label": t} for t in things],
                       text=then.strftime("%A %d %B %Y"))
    return screen.Shown(f"{label.capitalize()} you were grateful for: " + "; ".join(things[:3]) + ".", card)


# Worries

def _worries(settings: Settings) -> list[dict]:
    return store.load(settings, "worries", [])


def worry_add(settings: Settings, text) -> str | screen.Shown:
    if store.in_crisis(text):
        return calm_exercises.support()
    line = store.need(text, "worry", 200)
    rows = _worries(settings)
    rows.append({"text": line, "added": store.today().isoformat(), "released": ""})
    store.save(settings, "worries", rows[-300:])
    waiting = sum(1 for r in rows if not r["released"])
    return f"Noted. It can wait until worry time. You have {store.plural(waiting, 'worry', 'worries')} on the list."


def worry_list(settings: Settings, everything: bool = False) -> str | screen.Shown:
    rows = [r for r in _worries(settings) if everything or not r["released"]]
    if not rows:
        return "Your worry list is empty. Nothing to carry."
    items = [{"label": r["text"] + (" (let go)" if r["released"] else ""), "done": bool(r["released"]),
              "say": "" if r["released"] else f"Let go of the worry: {r['text']}"} for r in rows]
    card = screen.card("list", "Worry list", "calm-worries", items=items,
                       buttons=[{"label": "Worry time", "say": "It's worry time"}])
    return screen.Shown(f"{store.plural(len(rows), 'worry', 'worries')} on your list. Tap one to let it go.", card)


def worry_time(settings: Settings) -> str | screen.Shown:
    rows = [r for r in _worries(settings) if not r["released"]]
    when = store.load(settings, "settings", {}).get("worry_time", "")
    at = f" Your usual worry time is {when}." if when else ""
    if not rows:
        return "No worries are waiting. Enjoy the quiet." + at
    items = [{"label": r["text"], "say": f"Let go of the worry: {r['text']}"} for r in rows]
    card = screen.card("list", "Worry time", "calm-worry-time",
                       text="For each worry, ask: can I do something about it? If yes, pick one small step. "
                            "If not, tap it to let it go.", items=items,
                       buttons=[{"label": "Take a breath", "say": "Start coherent breathing"}])
    return screen.Shown("It's worry time. Take one at a time: can you act on it, or can you let it go?" + at, card)


def worry_time_set(settings: Settings, time) -> str:
    when = wellness_store.clock(time, "worry time")
    settings_file = store.load(settings, "settings", {})
    settings_file["worry_time"] = when
    store.save(settings, "settings", settings_file)
    return f"Worry time is set for {when} each day. I'll only mention it when you ask."


def worry_let_go(settings: Settings, words) -> str:
    rows = _worries(settings)
    key = store.clean(words).lower()
    found = [r for r in rows if not r["released"] and key and (key in r["text"].lower() or r["text"].lower() in key)]
    if not found:
        raise ValueError("None of your worries match that.")
    for r in found:
        r["released"] = store.today().isoformat()
    store.save(settings, "worries", rows)
    return "Let go. Breathe out. " + f"{store.plural(len(found), 'worry', 'worries')} released."


def worry_clear(settings: Settings, confirmed: bool) -> str:
    rows = _worries(settings)
    gone = [r for r in rows if r["released"]]
    if not gone:
        return "There are no released worries to clear away."
    if not confirmed:
        return f"That would delete {len(gone)} released worries for good. Ask the user to confirm, then call again with confirmed true."
    store.save(settings, "worries", [r for r in rows if not r["released"]])
    return f"Cleared {store.plural(len(gone), 'released worry', 'released worries')}."


# Check-ins

def checkin(settings: Settings, rating, note) -> str | screen.Shown:
    if store.in_crisis(note):
        return calm_exercises.support()
    score = int(store.hs.number(rating, "calm rating from 1 to 5", 1, 5))
    rows = store.load(settings, "checkins", [])
    rows.append({"date": store.today().isoformat(), "rating": score, "note": store.clean(note, 160)})
    store.save(settings, "checkins", rows[-1000:])
    extra = " Want a quick calm-down idea?" if score <= 2 else ""
    return f"Logged calm {score} out of 5.{extra}" + f" {store.SAFETY}" * (score <= 2)


def checkin_history(settings: Settings) -> str | screen.Shown:
    rows = store.load(settings, "checkins", [])
    if not rows:
        return "No calm check-ins yet. Tell me how calm you feel from 1 to 5."
    by_day: dict[str, list[int]] = {}
    for r in rows[-200:]:
        by_day.setdefault(r["date"], []).append(r["rating"])
    days = sorted(by_day)[-14:]
    chart = {"type": "line", "labels": [d[5:] for d in days],
             "values": [round(sum(by_day[d]) / len(by_day[d]), 1) for d in days], "unit": "/5"}
    card = screen.card("chart", "Calm check-ins", "calm-checkins", chart=chart)
    avg = sum(chart["values"]) / len(days)
    return screen.Shown(f"Your average calm over {store.plural(len(days), 'day')} is {avg:.1f} out of 5.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "calm_mind",
        "description": "Calm for the mind. affirmation (daily; another true for a different one), affirmation_add "
                       "(text), affirmation_list, affirmation_remove (words); kindness (idea of the day), "
                       "kindness_done (note); gratitude_lookback (what I was grateful for a month ago, span 'year' for "
                       "a year ago); worry list: worry_add (text), worry_list (all true includes released), "
                       "worry_time (go through them), worry_time_set (time), worry_let_go (words, the let it go button), "
                       "worry_clear (deletes released ones); checkin (rating 1-5 for how calm, note), checkin_history "
                       "(chart). Removal or clearing needs confirmed true only after the user confirms. Not medical "
                       "advice; if the user mentions self-harm or crisis, point them to Samaritans 116 123 and NHS 111.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "another": {"type": "boolean"},
                "text": {"type": "string"},
                "words": {"type": "string", "description": "Words from the worry or affirmation."},
                "note": {"type": "string"},
                "span": {"type": "string"},
                "all": {"type": "boolean"},
                "time": {"type": "string", "description": "e.g. 18:00."},
                "rating": {"type": "integer", "description": "1 (not calm) to 5 (very calm)."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action, ok = args.get("action"), bool(args.get("confirmed"))
    actions = {
        "affirmation": lambda: affirmation(settings, bool(args.get("another"))),
        "affirmation_add": lambda: affirmation_add(settings, args.get("text")),
        "affirmation_list": lambda: affirmation_list(settings),
        "affirmation_remove": lambda: affirmation_remove(settings, args.get("words"), ok),
        "kindness": lambda: kindness(settings),
        "kindness_done": lambda: kindness_done(settings, args.get("note")),
        "gratitude_lookback": lambda: gratitude_lookback(settings, args.get("span")),
        "worry_add": lambda: worry_add(settings, args.get("text")),
        "worry_list": lambda: worry_list(settings, bool(args.get("all"))),
        "worry_time": lambda: worry_time(settings),
        "worry_time_set": lambda: worry_time_set(settings, args.get("time")),
        "worry_let_go": lambda: worry_let_go(settings, args.get("words") or args.get("text")),
        "worry_clear": lambda: worry_clear(settings, ok),
        "checkin": lambda: checkin(settings, args.get("rating"), args.get("note")),
        "checkin_history": lambda: checkin_history(settings),
    }
    if action not in actions:
        raise ValueError(f"Unknown action {action}.")
    return actions[action]()
