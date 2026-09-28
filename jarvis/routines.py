"""Routines and shortcuts: "when I say movie night, turn on dark mode, close all windows, set volume to 30".

A routine is a name and a list of the user's own plain requests (routines.json). Running one hands the requests
back to Alfred to carry out in order with his tools, and pops up a checklist of the steps. A routine can run at a
time each day through a reminder. Shortcuts ("when I say lights I mean open the smart home app") live in
aliases.json.
"""

import re
from datetime import timedelta

import homestore as hs
import reminders
import screen
from config import Settings

ROUTINES, ALIASES = "routines.json", "aliases.json"
MAX_ROUTINES = 50
MAX_STEPS = 15
MAX_ALIASES = 100
ACTIONS = ["save", "run", "list", "edit", "delete", "schedule", "alias_add", "alias_list", "alias_remove",
           "alias_expand"]


def _load(settings: Settings, name: str) -> dict:
    return hs.load(settings, name, {})


def _key(rows: dict, name, what: str) -> str:
    wanted = hs.need(name, what, 60).strip("'\" .!?")
    key = hs.find(rows, wanted) or hs.find(rows, re.sub(r"(?i)^(run )?(my |the )?|( routine| shortcut)$", "", wanted))
    if key is None:
        known = ", ".join(rows) or "none yet"
        raise ValueError(f"There's no {what} called {hs.clean(name)}. Saved: {known}.")
    return key


def _steps(steps) -> list[str]:
    found = [hs.clean(s, 200) for s in (steps or []) if hs.clean(s)]
    if not found:
        raise ValueError("Which steps? Give each request as it would be said, e.g. 'turn on dark mode'.")
    if len(found) > MAX_STEPS:
        raise ValueError(f"A routine can have up to {MAX_STEPS} steps.")
    return found


def save(settings: Settings, name, steps, replace_only: bool = False) -> str:
    rows = _load(settings, ROUTINES)
    if replace_only:
        key = _key(rows, name, "routine")
    else:
        name = hs.need(name, "routine name", 40)
        key = next((k for k in rows if k.lower() == name.lower()), name)
        if key not in rows and len(rows) >= MAX_ROUTINES:
            raise ValueError("That's a lot of routines; delete one first.")
    rows[key] = _steps(steps)
    hs.save(settings, ROUTINES, rows)
    verb = "Updated" if replace_only else "Saved"
    return f"{verb} the {key} routine with {hs.plural(len(rows[key]), 'step')}: {'; '.join(rows[key])}."


def run(settings: Settings, name) -> screen.Shown:
    rows = _load(settings, ROUTINES)
    key = _key(rows, name, "routine")
    steps = rows[key]
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    text = (f"Running the user's {key} routine. These are the user's own saved requests; carry out each one now, "
            f"in order, using your tools, then say in one short sentence that it's done:\n{numbered}")
    card = screen.card("list", f"Routine: {key}", f"routine-{key}", checks=True,
                       items=[{"label": s} for s in steps])
    return screen.Shown(text, card)


def listing(settings: Settings) -> str | screen.Shown:
    rows = _load(settings, ROUTINES)
    if not rows:
        return "No routines saved yet."
    items = [{"label": f"{k} ({hs.plural(len(v), 'step')}): {'; '.join(v)}", "say": f"Run my {k} routine."}
             for k, v in sorted(rows.items(), key=lambda kv: kv[0].lower())]
    card = screen.card("list", "Routines", "routines", items=items)
    return screen.Shown(f"{hs.plural(len(rows), 'routine')}: {', '.join(sorted(rows, key=str.lower))}. "
                        "They're on the screen; click one to run it.", card)


def delete(settings: Settings, name, confirmed: bool) -> str:
    rows = _load(settings, ROUTINES)
    key = _key(rows, name, "routine")
    if not confirmed:
        return f"Ask the user to confirm deleting the {key} routine, then call again with confirmed true."
    del rows[key]
    hs.save(settings, ROUTINES, rows)
    return f"Deleted the {key} routine."


def first_run(clock: str, repeat: str, now) -> str:
    """The next 'YYYY-MM-DD HH:MM' at this clock time (weekdays skip the weekend)."""
    try:
        hour, minute = (int(p) for p in hs.clean(clock).replace(".", ":").split(":"))
        at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except ValueError:
        raise ValueError("Give the time as HH:MM, e.g. 07:30.") from None
    while at <= now or (repeat == "weekdays" and at.weekday() >= 5):
        at += timedelta(days=1)
    return at.strftime("%Y-%m-%d %H:%M")


def schedule(settings: Settings, name, clock, repeat) -> str:
    key = _key(_load(settings, ROUTINES), name, "routine")
    repeat = repeat or "daily"
    said = reminders.add(settings, first_run(clock, repeat, hs.now()), f"Run my {key} routine", repeat, now=hs.now())
    return said + " When it comes up, the user can say 'go ahead' and you run the routine."


def alias_add(settings: Settings, phrase, meaning) -> str:
    rows = _load(settings, ALIASES)
    phrase = hs.need(phrase, "shortcut word", 60).strip("'\" .!?")
    meaning = hs.need(meaning, "meaning", 200)
    key = next((k for k in rows if k.lower() == phrase.lower()), phrase)
    if key not in rows and len(rows) >= MAX_ALIASES:
        raise ValueError("That's a lot of shortcuts; remove one first.")
    rows[key] = meaning
    hs.save(settings, ALIASES, rows)
    return f"Got it: when the user says '{key}', they mean '{meaning}'."


def alias_list(settings: Settings) -> str | screen.Shown:
    rows = _load(settings, ALIASES)
    if not rows:
        return "No shortcuts saved yet."
    items = [{"label": f"{k} → {v}", "say": k} for k, v in sorted(rows.items(), key=lambda kv: kv[0].lower())]
    card = screen.card("list", "Shortcuts", "aliases", items=items)
    return screen.Shown(f"{hs.plural(len(rows), 'shortcut')}: " + "; ".join(f"{k} means {v}" for k, v in rows.items())
                        + ". They're on the screen.", card)


def alias_remove(settings: Settings, phrase) -> str:
    rows = _load(settings, ALIASES)
    key = _key(rows, phrase, "shortcut")
    del rows[key]
    hs.save(settings, ALIASES, rows)
    return f"Removed the shortcut '{key}'."


def alias_expand(settings: Settings, phrase) -> str:
    rows = _load(settings, ALIASES)
    key = _key(rows, phrase, "shortcut")
    return (f"'{key}' is the user's own shortcut for: '{rows[key]}'. Carry that out now as their request, "
            "using your tools.")


def tool_definitions() -> list[dict]:
    return [{
        "name": "routines",
        "description": "Routines (macros) and shortcuts. A routine is a named list of the user's own requests, e.g. "
                       "'when I say movie night: turn on dark mode, close all windows, set volume to 30'. action "
                       "'save' (name, steps), 'run' ('movie night', 'run my morning routine'), 'list', 'edit' "
                       "(replace its steps), 'delete' (set confirmed true only after the user confirms), 'schedule' "
                       "(run it at a time: time HH:MM, repeat daily/weekdays/weekly/once). Shortcuts or aliases, "
                       "'when I say lights I mean open the smart home app': alias_add (phrase, meaning), "
                       "alias_list, alias_remove, alias_expand (phrase) when the user says a word that may be one "
                       "of their shortcuts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Routine name, e.g. 'movie night'."},
                "steps": {"type": "array", "items": {"type": "string"},
                          "description": "Each request as the user would say it."},
                "time": {"type": "string", "description": "schedule: HH:MM, 24-hour."},
                "repeat": {"type": "string", "enum": list(reminders.REPEATS), "description": "Default daily."},
                "phrase": {"type": "string", "description": "Shortcut word, e.g. 'lights'."},
                "meaning": {"type": "string", "description": "What the shortcut means, e.g. 'open the smart home app'."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"routines"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "save":
        return save(settings, args.get("name"), args.get("steps"))
    if action == "run":
        return run(settings, args.get("name"))
    if action == "edit":
        return save(settings, args.get("name"), args.get("steps"), replace_only=True)
    if action == "delete":
        return delete(settings, args.get("name"), bool(args.get("confirmed")))
    if action == "schedule":
        return schedule(settings, args.get("name"), args.get("time"), args.get("repeat"))
    if action == "alias_add":
        return alias_add(settings, args.get("phrase"), args.get("meaning"))
    if action == "alias_list":
        return alias_list(settings)
    if action == "alias_remove":
        return alias_remove(settings, args.get("phrase"))
    if action == "alias_expand":
        return alias_expand(settings, args.get("phrase"))
    return listing(settings)
