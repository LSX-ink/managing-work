"""Streak challenges ("no sugar for 30 days": a start date, a daily check and a calendar pop-up) and life in weeks
(a grid of the weeks lived and left to age 90, from a birth date the user gives once).

Saved in trackers-challenges.json and trackers-profile.json in the memory folder on this PC and nowhere else.
"""

from datetime import date, timedelta

import screen
import trackers_store as store
import trackers_views as views
from config import Settings

MAX_CHALLENGES = 20
LIFE_YEARS = 90


def _challenges(settings: Settings) -> dict:
    found = store.load(settings, "challenges", {})
    return {k: v for k, v in found.items() if isinstance(v, dict) and "start" in v and "days" in v}


def _need(found: dict, wanted: str) -> str:
    name = store.find(found, wanted)
    if name is None:
        raise ValueError(f"There's no challenge called {store.clean(wanted) or 'that'}. "
                         f"Your challenges: {', '.join(found) or 'none yet'}.")
    return name


def _run(done: set, today: date) -> int:
    day = today if today.isoformat() in done else today - timedelta(days=1)
    count = 0
    while day.isoformat() in done:
        count += 1
        day -= timedelta(days=1)
    return count


def start(settings: Settings, name: str, days, when: str) -> str:
    name = store.clean(name, 50)
    if not name:
        raise ValueError("What's the challenge, e.g. 'no sugar'?")
    found = _challenges(settings)
    if any(store.stem(n) == store.stem(name) for n in found):
        raise ValueError(f"The {name} challenge is already running.")
    if len(found) >= MAX_CHALLENGES:
        raise ValueError("That's a lot of challenges; stop one first.")
    length = int(days or 30)
    if not 2 <= length <= 366:
        raise ValueError("A challenge can run from 2 to 366 days.")
    try:
        begin = date.fromisoformat(when) if when else store.today()
    except ValueError:
        raise ValueError("Give the start date as YYYY-MM-DD.") from None
    found[name] = {"start": begin.isoformat(), "days": length, "done": []}
    store.save(settings, "challenges", found)
    end = begin + timedelta(days=length - 1)
    return f"Challenge on: {name} for {length} days, {begin:%d %b} to {end:%d %b}. Tell me each day you've kept it."


def check(settings: Settings, wanted: str, kept: bool, when: str) -> str:
    found = _challenges(settings)
    name = _need(found, wanted)
    c = found[name]
    today = store.today()
    day = today - timedelta(days=1) if when == "yesterday" else today
    begin = date.fromisoformat(c["start"])
    if not begin <= day < begin + timedelta(days=c["days"]):
        raise ValueError(f"That day isn't part of the {name} challenge.")
    done = set(c["done"])
    (done.add if kept else done.discard)(day.isoformat())
    c["done"] = sorted(done)
    store.save(settings, "challenges", found)
    left = (begin + timedelta(days=c["days"] - 1) - today).days
    if len(done) >= c["days"]:
        return f"{name}: all {c['days']} days done. Challenge complete, well done!"
    run = _run(done, today)
    status = f"Streak {run} day{'s' if run != 1 else ''}, {len(done)} of {c['days']} done"
    return (f"{name}: {status}, {max(0, left)} to go." if kept
            else f"{name}: marked as missed. {status}. Tomorrow's a fresh start.")


def show(settings: Settings, wanted: str):
    found = _challenges(settings)
    today = store.today()
    if not wanted:
        if not found:
            return "No challenges yet. Say something like 'start a no sugar challenge for 30 days'."
        items = [{"label": f"{n}: {len(c['done'])} of {c['days']} days, streak {_run(set(c['done']), today)}",
                  "say": f"Show my {n} challenge calendar."} for n, c in found.items()]
        return screen.Shown(f"{len(items)} challenge{'s' if len(items) != 1 else ''} on the screen.",
                            screen.card("list", "Challenges", "trackers-challenges", items=items))
    name = _need(found, wanted)
    c = found[name]
    begin, done = date.fromisoformat(c["start"]), set(c["done"])
    days = [begin + timedelta(days=i) for i in range(c["days"])]
    levels = [5 if d.isoformat() in done else None if d >= today else 0 for d in days]
    text = f"{len(done)} of {c['days']} days done, streak {_run(done, today)}."
    buttons = [{"label": "Kept it today", "say": f"I kept my {name} challenge today."}] if begin <= today <= days[-1] else []
    words = {d.isoformat(): "kept" if lv == 5 else "missed" for d, lv in zip(days, levels) if lv is not None}
    card = views.pixels_card(f"{name} challenge", f"trackers-challenge-{name}", begin, levels, words, {},
                             ["missed", "done"], text, buttons)
    card["data"]["calendar"] = True
    return screen.Shown(f"{name}: {text}", card)


def stop(settings: Settings, wanted: str, confirmed: bool) -> str:
    found = _challenges(settings)
    name = _need(found, wanted)
    if not confirmed:
        return f"Stop the {name} challenge and forget its days? Ask the user to confirm first."
    del found[name]
    store.save(settings, "challenges", found)
    return f"Stopped the {name} challenge."


def life_weeks(settings: Settings, born: str):
    profile = store.load(settings, "profile", {})
    if born:
        try:
            birth = date.fromisoformat(born)
        except ValueError:
            raise ValueError("Give the birth date as YYYY-MM-DD.") from None
        profile["birth_date"] = birth.isoformat()
        store.save(settings, "profile", profile)
    if not profile.get("birth_date"):
        return "What's your date of birth? I'll keep it on this PC only."
    birth, today = date.fromisoformat(profile["birth_date"]), store.today()
    if not birth < today or (today - birth).days > LIFE_YEARS * 366:
        raise ValueError("That birth date doesn't look right.")
    years = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
    last_birthday = _birthday(birth, birth.year + years)
    lived = years * 52 + min(51, (today - last_birthday).days // 7)
    total = LIFE_YEARS * 52
    card = screen.card("trackers-pixels", "Life in weeks", "trackers-life-weeks",
                       text=f"Each row is a year of your life, each square a week, to age {LIFE_YEARS}.",
                       data={"weeks": {"lived": lived, "total": total, "per_row": 52}, "legend": ["to come", "lived"]})
    return screen.Shown(f"You've lived {lived:,} weeks; {total - lived:,} more to age {LIFE_YEARS}.", card)


def _birthday(birth: date, year: int) -> date:
    try:
        return birth.replace(year=year)
    except ValueError:
        return date(year, 3, 1)


ACTIONS = ["start", "check", "show", "stop", "life_weeks"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "streak_challenges",
        "description": "Streak challenges like 'no sugar for 30 days' and a 'life in weeks' grid. start: a new "
                       "challenge (challenge name, days default 30, start_date). check: the user kept it today "
                       "(kept false if they slipped; when 'yesterday'). show: a calendar pop-up of one challenge, "
                       "or all challenges without a name. stop: set confirmed true only after the user confirms. "
                       "life_weeks: a grid of weeks lived and left to age 90; birth_date is saved on this PC the "
                       "first time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "challenge": {"type": "string", "description": "e.g. 'no sugar'."},
                "days": {"type": "integer"},
                "start_date": {"type": "string", "description": "start: YYYY-MM-DD; default today."},
                "kept": {"type": "boolean", "description": "check: false when the user broke it."},
                "when": {"type": "string", "enum": ["today", "yesterday"]},
                "birth_date": {"type": "string", "description": "life_weeks: YYYY-MM-DD."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"streak_challenges"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    challenge = args.get("challenge") or ""
    if action == "start":
        return start(settings, challenge, args.get("days"), args.get("start_date") or "")
    if action == "check":
        return check(settings, challenge, args.get("kept") is not False, args.get("when") or "today")
    if action == "stop":
        return stop(settings, challenge, args.get("confirmed") is True)
    if action == "life_weeks":
        return life_weeks(settings, args.get("birth_date") or "")
    return show(settings, challenge)
