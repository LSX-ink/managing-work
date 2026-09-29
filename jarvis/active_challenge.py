"""Fitness challenges with a daily target that grows (30-day plank, squats, press-ups or your own) and a streak
calendar. Pop-up kind "active-calendar" (frontend/popup-active.js). Saved under "challenges" in active.json.
Every seventh day is a rest day on the built-in plans; a rest day keeps the streak going.
"""

from datetime import date, timedelta

import active_store as store
import screen
from config import Settings

screen.EXTRA_KINDS.add("active-calendar")
PRESETS = {"plank": ("Plank", "seconds", 20, 10), "squats": ("Squats", "squats", 50, 5),
           "press-ups": ("Press-ups", "press-ups", 5, 1), "sit-ups": ("Sit-ups", "sit-ups", 10, 2)}
ALIASES = {"planks": "plank", "squat": "squats", "pushups": "press-ups", "push-ups": "press-ups",
           "pushup": "press-ups", "press-up": "press-ups", "press ups": "press-ups", "situps": "sit-ups",
           "sit ups": "sit-ups", "sit-up": "sit-ups", "crunches": "sit-ups"}
REST_EVERY = 7


def _all(settings: Settings) -> list[dict]:
    return store.section(settings, "challenges", [])


def _find(challenges: list[dict], name) -> dict:
    wanted = store.clean(name).lower()
    if not challenges:
        raise ValueError("You haven't started a fitness challenge yet.")
    if not wanted:
        if len(challenges) == 1:
            return challenges[0]
        raise ValueError("Which challenge? You have " + ", ".join(c["name"] for c in challenges) + ".")
    for c in challenges:
        if wanted in c["name"].lower() or c["name"].lower() in wanted:
            return c
    raise ValueError(f"I can't find a challenge called {wanted}.")


def target(c: dict, n: int) -> int:
    """The target on day n (from 1); 0 on a rest day."""
    if c["rest"] and n % REST_EVERY == 0:
        return 0
    return c["start"] + c["step"] * (n - 1 - (n // REST_EVERY if c["rest"] else 0))


def _target_text(c: dict, n: int) -> str:
    t = target(c, n)
    if not t:
        return "rest day"
    if c["unit"] == "seconds":
        return store.spoken_time(t / 60) + " plank" if c["name"].lower() == "plank" else f"{t} seconds"
    return f"{t} {c['unit']}"


def _day_number(c: dict, on: date) -> int:
    return (on - date.fromisoformat(c["start_date"])).days + 1


def _kept(c: dict, on: date) -> bool:
    return on.isoformat() in c["done"] or target(c, _day_number(c, on)) == 0


def streak(c: dict, today: date) -> int:
    on = min(today, date.fromisoformat(c["start_date"]) + timedelta(days=c["days"] - 1))
    if on == today and not _kept(c, on):
        on -= timedelta(days=1)
    count = 0
    while _day_number(c, on) >= 1 and _kept(c, on):
        count += 1
        on -= timedelta(days=1)
    return count


def start(settings: Settings, args: dict) -> str:
    challenges = _all(settings)
    raw = store.clean(args.get("name"), 40).lower() or "plank"
    key = ALIASES.get(raw, raw)
    preset = PRESETS.get(key)
    days = int(store.number(args.get("days") or 30, "days", 3, 365))
    if preset:
        name, unit, first, step = preset
        rest = True
    else:
        name, unit, rest = store.need(args.get("name"), "challenge", 40).title(), store.clean(args.get("unit"), 20) or "reps", False
        first, step = 10, 1
    first = int(store.number(args.get("start_target") if args.get("start_target") is not None else first, "start", 1, 100000))
    step = int(store.number(args.get("step") if args.get("step") is not None else step, "step", 0, 10000))
    if any(c["name"].lower() == name.lower() for c in challenges):
        raise ValueError(f"You already have a {name} challenge. Stop it first to start again.")
    if len(challenges) >= 5:
        raise ValueError("That's five challenges; stop one first.")
    c = {"name": name, "unit": unit, "days": days, "start": first, "step": step, "rest": rest,
         "start_date": store.day(args.get("date")).isoformat(), "done": []}
    challenges.append(c)
    store.save_section(settings, "challenges", challenges)
    return (f"Started the {days} day {name} challenge. Day 1 is {_target_text(c, 1)}. "
            + ("Every seventh day is a rest day." if rest else ""))


def check(settings: Settings, args: dict) -> str:
    challenges = _all(settings)
    c = _find(challenges, args.get("name"))
    on = store.day(args.get("date"))
    n = _day_number(c, on)
    if not 1 <= n <= c["days"]:
        raise ValueError(f"That date is outside the {c['name']} challenge.")
    if target(c, n) == 0:
        return f"Day {n} is a rest day; enjoy it. Your streak is {store.plural(streak(c, store.today()), 'day')}."
    if on.isoformat() not in c["done"]:
        c["done"].append(on.isoformat())
    store.save_section(settings, "challenges", challenges)
    run, left = streak(c, store.today()), c["days"] - n
    upcoming = f" Next: {_target_text(c, n + 1)}." if left > 0 else " That's the whole challenge finished. Brilliant!"
    return (f"Day {n} done: {_target_text(c, n)}. {store.plural(run, 'day')} in a row, "
            f"{store.plural(sum(1 for d in c['done']), 'day')} completed.{upcoming}")


def _card(c: dict, today: date) -> dict:
    begin = date.fromisoformat(c["start_date"])
    cells = []
    for n in range(1, c["days"] + 1):
        d = begin + timedelta(days=n - 1)
        rest = target(c, n) == 0
        state = ("rest" if rest else "done" if d.isoformat() in c["done"] else
                 "today" if d == today else "future" if d > today else "missed")
        cells.append({"n": n, "date": d.isoformat(), "target": target(c, n), "state": state})
    run = streak(c, today)
    done = len(c["done"])
    return screen.card("active-calendar", f"{c['name']} challenge", f"active-challenge-{c['name'].lower()}",
                       data={"name": c["name"], "unit": c["unit"], "days": cells, "streak": run, "done": done},
                       buttons=[{"label": "Done today", "say": f"I did today's {c['name'].lower()} challenge"}])


def show(settings: Settings, name=None) -> str | screen.Shown:
    challenges = _all(settings)
    today = store.today()
    c = _find(challenges, name)
    n = _day_number(c, today)
    where = (f"day {n} of {c['days']}, today's target {_target_text(c, n)}" if 1 <= n <= c["days"]
             else "not running today")
    return screen.Shown(f"{c['name']} challenge: {where}. {store.plural(streak(c, today), 'day')} streak.",
                        _card(c, today))


def stop(settings: Settings, args: dict) -> str:
    challenges = _all(settings)
    c = _find(challenges, args.get("name"))
    if not args.get("confirmed"):
        return (f"That would delete the {c['name']} challenge and its {len(c['done'])} days. "
                "Ask the user to confirm, then call again with confirmed true.")
    store.save_section(settings, "challenges", [x for x in challenges if x is not c])
    return f"Stopped and removed the {c['name']} challenge."
