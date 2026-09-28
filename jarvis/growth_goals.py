"""Goals and fitness: goals with targets and deadlines, a workout log with personal bests, steps against a
weekly goal, and today's top three priorities.

Kept in growth-goals.json, growth-workouts.json, growth-steps.json and growth-priorities.json in the memory folder.
"""

from datetime import date, timedelta

import growth_store as store
from config import Settings

MAX_GOALS = 50
KEEP_DAYS = 400


def _goals(settings: Settings) -> list[dict]:
    return store.load(settings, "goals", [])


def _goal(goals: list[dict], name: str) -> dict:
    goal = store.find([g for g in goals if not g.get("achieved")], "name", name)
    if goal is None:
        open_goals = ", ".join(g["name"] for g in goals if not g.get("achieved")) or "none"
        raise ValueError(f"I couldn't find that goal. Open goals: {open_goals}.")
    return goal


def _deadline(text: str) -> str | None:
    if not text:
        return None
    try:
        return date.fromisoformat(str(text)[:10]).isoformat()
    except ValueError:
        raise ValueError("Give the deadline as a date like 2026-12-31.") from None


def set_goal(settings: Settings, args: dict, today: date) -> str:
    name = store.need(args.get("name"), "goal", 100)
    goals = _goals(settings)
    if any(g["name"].lower() == name.lower() and not g.get("achieved") for g in goals):
        return f"You already have the goal {name}."
    if sum(not g.get("achieved") for g in goals) >= MAX_GOALS:
        raise ValueError("That's a lot of open goals; mark some achieved first.")
    target = store.number(args["target"], "target") if args.get("target") is not None else None
    goal = {"name": name, "target": target, "unit": store.clean(args.get("unit"), 30), "progress": 0,
            "deadline": _deadline(args.get("deadline") or ""), "created": today.isoformat(), "log": [],
            "achieved": None}
    goals.append(goal)
    store.save(settings, "goals", goals)
    return f"New goal: {name}{_target_text(goal)}{_deadline_text(goal, today)}."


def _target_text(goal: dict) -> str:
    return f", target {goal['target']:g} {goal['unit']}".rstrip() if goal["target"] else ""


def _deadline_text(goal: dict, today: date) -> str:
    if not goal["deadline"]:
        return ""
    left = (date.fromisoformat(goal["deadline"]) - today).days
    if left < 0:
        return f", deadline passed {store.plural(-left, 'day')} ago"
    return ", due today" if left == 0 else f", {store.plural(left, 'day')} left"


def progress_text(goal: dict) -> str:
    unit = f" {goal['unit']}" if goal["unit"] else ""
    if goal["target"]:
        pct = min(100, round(100 * goal["progress"] / goal["target"]))
        return f"{goal['progress']:g} of {goal['target']:g}{unit} ({pct}%)"
    return f"progress {goal['progress']:g}{unit}"


def log_goal(settings: Settings, name: str, amount, today: date) -> str:
    goals = _goals(settings)
    goal = _goal(goals, name)
    amount = store.number(1 if amount is None else amount, "amount")
    goal["progress"] += amount
    goal["log"] = [*goal["log"], {"date": today.isoformat(), "amount": amount}][-500:]
    store.save(settings, "goals", goals)
    reached = " You've hit the target. Shall I mark it achieved?" if goal["target"] and goal["progress"] >= goal["target"] else ""
    return f"{goal['name']}: {progress_text(goal)}.{reached}"


def report(settings: Settings, today: date) -> str:
    goals = _goals(settings)
    open_goals = [g for g in goals if not g.get("achieved")]
    done = [g for g in goals if (g.get("achieved") or "")[:4] == str(today.year)]
    if not goals:
        return "No goals set yet."
    lines = [f"- {g['name']}: {progress_text(g)}{_deadline_text(g, today)}" for g in open_goals]
    tail = f"\nAchieved this year: {', '.join(g['name'] for g in done)}." if done else ""
    return (("Goals:\n" + "\n".join(lines)) if lines else "No open goals.") + tail


def achieved(settings: Settings, name: str, today: date) -> str:
    goals = _goals(settings)
    goal = _goal(goals, name)
    goal["achieved"] = today.isoformat()
    store.save(settings, "goals", goals)
    return f"Marked {goal['name']} as achieved. Well done."


def log_workout(settings: Settings, args: dict, today: date) -> str:
    exercise = store.need(args.get("exercise"), "exercise", 60)
    entry = {"date": today.isoformat(), "exercise": exercise}
    for key in ("minutes", "sets", "reps", "weight_kg"):
        if args.get(key) is not None:
            entry[key] = store.number(args[key], key.replace("_kg", ""))
    workouts = store.load(settings, "workouts", [])
    best = _best(workouts, exercise)
    workouts.append(entry)
    store.save(settings, "workouts", workouts[-5000:])
    new_best = entry.get("weight_kg") and (best is None or entry["weight_kg"] > best.get("weight_kg", 0))
    return f"Logged {exercise}: {_workout_text(entry)}." + (" That's a new personal best!" if new_best else "")


def _workout_text(entry: dict) -> str:
    parts = []
    if entry.get("sets") and entry.get("reps"):
        parts.append(f"{entry['sets']:g} sets of {entry['reps']:g}")
    elif entry.get("reps"):
        parts.append(f"{entry['reps']:g} reps")
    if entry.get("weight_kg"):
        parts.append(f"at {entry['weight_kg']:g} kg")
    if entry.get("minutes"):
        parts.append(f"{entry['minutes']:g} minutes")
    return " ".join(parts) or "done"


def _best(workouts: list[dict], exercise: str) -> dict | None:
    lifts = [w for w in workouts if w["exercise"].lower() == exercise.lower() and w.get("weight_kg")]
    return max(lifts, key=lambda w: (w["weight_kg"], w.get("reps", 0)), default=None)


def workout_week(settings: Settings, today: date) -> str:
    week = [w for w in store.load(settings, "workouts", []) if store.this_week(w["date"], today)]
    if not week:
        return "No workouts logged this week."
    days = len({w["date"] for w in week})
    minutes = sum(w.get("minutes", 0) for w in week)
    lines = "\n".join(f"- {date.fromisoformat(w['date']):%A}: {w['exercise']}, {_workout_text(w)}" for w in week)
    return (f"This week: {store.plural(len(week), 'workout')} on {store.plural(days, 'day')}"
            + (f", {minutes:g} minutes in all" if minutes else "") + f".\n{lines}")


def bests(settings: Settings) -> str:
    workouts = store.load(settings, "workouts", [])
    first: dict[str, str] = {}
    for w in workouts:
        if w.get("weight_kg"):
            first.setdefault(w["exercise"].lower(), w["exercise"])
    names = sorted(first.values())
    if not names:
        return "No lifts with a weight logged yet."
    lines = []
    for name in names:
        best = _best(workouts, name)
        reps = f" for {best['reps']:g} reps" if best.get("reps") else ""
        lines.append(f"- {name}: {best['weight_kg']:g} kg{reps} on {best['date']}")
    return "Personal bests:\n" + "\n".join(lines)


def _steps(settings: Settings) -> dict:
    data = store.load(settings, "steps", {})
    data.setdefault("goal", 70000)
    data.setdefault("days", {})
    return data


def log_steps(settings: Settings, steps, km, today: date) -> str:
    if steps is None and km is None:
        raise ValueError("How many steps, or how far?")
    data = _steps(settings)
    day = data["days"].setdefault(today.isoformat(), {"steps": 0, "km": 0})
    day["steps"] += int(store.number(steps or 0, "steps"))
    day["km"] = round(day["km"] + store.number(km or 0, "distance"), 2)
    cutoff = (today - timedelta(days=KEEP_DAYS)).isoformat()
    data["days"] = {d: v for d, v in data["days"].items() if d >= cutoff}
    store.save(settings, "steps", data)
    distance = f" and {day['km']:g} km" if day["km"] else ""
    return f"Today so far: {day['steps']:,} steps{distance}."


def steps_goal(settings: Settings, goal) -> str:
    data = _steps(settings)
    data["goal"] = int(store.number(goal, "weekly step goal"))
    store.save(settings, "steps", data)
    return f"Weekly step goal set to {data['goal']:,}."


def steps_week(settings: Settings, today: date) -> str:
    data = _steps(settings)
    week = [v for d, v in data["days"].items() if store.this_week(d, today)]
    steps, km = sum(v["steps"] for v in week), sum(v["km"] for v in week)
    goal = data["goal"]
    left = f"{goal - steps:,} to go" if steps < goal else "goal reached"
    distance = f", {km:g} km" if km else ""
    return (f"This week: {steps:,} steps{distance} against a goal of {goal:,} "
            f"({round(100 * steps / goal) if goal else 100}%, {left}).")


def _priorities(settings: Settings) -> dict:
    return store.load(settings, "priorities", {})


def set_priorities(settings: Settings, items: list, today: date) -> str:
    items = [store.clean(i, 120) for i in (items or []) if store.clean(i)][:3]
    if not items:
        raise ValueError("What are today's priorities?")
    days = _priorities(settings)
    days[today.isoformat()] = [{"text": i, "done": False} for i in items]
    cutoff = (today - timedelta(days=60)).isoformat()
    store.save(settings, "priorities", {d: v for d, v in days.items() if d >= cutoff})
    return "Today's priorities: " + "; ".join(f"{n}. {i}" for n, i in enumerate(items, 1)) + "."


def priority_done(settings: Settings, which: str, today: date) -> str:
    days = _priorities(settings)
    items = days.get(today.isoformat(), [])
    which = store.clean(which)
    item = items[int(which) - 1] if which.isdigit() and 0 < int(which) <= len(items) else store.find(items, "text", which)
    if item is None:
        return "I couldn't find that in today's priorities." if items else "You haven't set today's priorities yet."
    item["done"] = True
    store.save(settings, "priorities", days)
    left = sum(not i["done"] for i in items)
    return f"Ticked off {item['text']}. " + (f"{left} to go." if left else "All three done. Great day.")


def read_priorities(settings: Settings, today: date) -> str:
    items = _priorities(settings).get(today.isoformat(), [])
    if not items:
        return "No priorities set for today yet."
    return "Today's priorities:\n" + "\n".join(
        f"{n}. {i['text']}{' (done)' if i['done'] else ''}" for n, i in enumerate(items, 1))


ACTIONS = ["goal_set", "goal_log", "goal_report", "goal_achieved", "workout_log", "workout_week",
           "personal_bests", "steps_log", "steps_goal", "steps_week", "priorities_set", "priority_done",
           "priorities_read"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "goals_and_fitness",
        "description": "Goals, workouts, steps and today's top 3 priorities. goal_set (name, optional target, unit, "
                       "deadline YYYY-MM-DD), goal_log adds amount, goal_report, goal_achieved. workout_log "
                       "(exercise with minutes or sets/reps/weight_kg), workout_week, personal_bests. steps_log "
                       "(steps and/or km, added to today), steps_goal sets the weekly goal (amount), steps_week. "
                       "priorities_set (items, up to 3, replaces today's), priority_done (item text or number), "
                       "priorities_read.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "Goal name."},
                "target": {"type": "number"},
                "unit": {"type": "string", "description": "e.g. 'books', 'km', 'pounds saved'."},
                "deadline": {"type": "string", "description": "YYYY-MM-DD."},
                "amount": {"type": "number", "description": "Goal progress to add, or the weekly step goal."},
                "exercise": {"type": "string"},
                "minutes": {"type": "number"},
                "sets": {"type": "number"},
                "reps": {"type": "number"},
                "weight_kg": {"type": "number"},
                "steps": {"type": "integer"},
                "km": {"type": "number"},
                "items": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                "item": {"type": "string", "description": "A priority's text or its number 1 to 3."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"goals_and_fitness"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action, today = args.get("action"), store.today()
    if action == "goal_set":
        return set_goal(settings, args, today)
    if action == "goal_log":
        return log_goal(settings, args.get("name") or "", args.get("amount"), today)
    if action == "goal_report":
        return report(settings, today)
    if action == "goal_achieved":
        return achieved(settings, args.get("name") or "", today)
    if action == "workout_log":
        return log_workout(settings, args, today)
    if action == "workout_week":
        return workout_week(settings, today)
    if action == "personal_bests":
        return bests(settings)
    if action == "steps_log":
        return log_steps(settings, args.get("steps"), args.get("km"), today)
    if action == "steps_goal":
        return steps_goal(settings, args.get("amount"))
    if action == "steps_week":
        return steps_week(settings, today)
    if action == "priorities_set":
        return set_priorities(settings, args.get("items"), today)
    if action == "priority_done":
        return priority_done(settings, str(args.get("item") or ""), today)
    if action == "priorities_read":
        return read_priorities(settings, today)
    raise ValueError(f"Unknown goals action: {action}")
