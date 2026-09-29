"""Workouts on the Alfred screen: a workout builder (by time, focus and kit), a guided workout timer with a big
countdown, the next exercise and beeps, EMOM and custom circuit timers, stretch routines as step cards, and how-to cards
for about 30 exercises. Pop-ups are "active-timer" and "active-steps" (frontend/popup-active.js); beeps are made by the
page with Web Audio. Nothing here is medical advice. (Tabata and simple HIIT timers are in health-plus.)
"""

import active_data as data
import active_store as store
import screen
from config import Settings

screen.EXTRA_KINDS.update({"active-timer", "active-steps"})
NAMES = {"active_workout"}
ACTIONS = ["build", "timer", "emom", "circuit", "stretch", "howto", "exercises"]
GEAR_KEY = {"bodyweight": "body", "body": "body", "none": "body", "no equipment": "body", "home": "body",
            "dumbbell": "dumbbell", "dumbbells": "dumbbell", "weights": "dumbbell", "gym": "gym", "barbell": "gym"}
GEAR_NAME = {"body": "bodyweight", "dumbbell": "dumbbell", "gym": "gym"}
FOCUS_NAME = {"full": "full body", "upper": "upper body", "lower": "lower body", "core": "core", "cardio": "cardio"}
BUCKETS = ["lower", "upper", "core", "cardio"]
WARM_UP = "Warm-up: 3 minutes of marching on the spot, arm circles and easy squats"
COOL_DOWN = "Cool-down: 2 minutes of slow walking and a few stretches"


def _resolve(value) -> str:
    text = store.clean(value).lower().replace("_", " ")
    key = data.ALIASES.get(text, text)
    if key in data.EXERCISES:
        return key
    found = [k for k, v in data.EXERCISES.items() if text and (text in k or text in v[0].lower())]
    if len(found) == 1:
        return found[0]
    raise ValueError(f"I don't have a how-to for {text or 'that'}. Ask me to list the exercises.")


def _pick(value, table: dict, default: str, what: str) -> str:
    text = store.clean(value).lower().replace("_", " ") or default
    if text not in table:
        raise ValueError(f"Choose {what}: {', '.join(dict.fromkeys(table))}.")
    return table[text]


def _order(gear: str) -> list[str]:
    return {"body": ["body"], "dumbbell": ["dumbbell", "body"], "gym": ["gym", "dumbbell", "body"]}[gear]


def _pool(gear: str) -> list[str]:
    rank = {g: i for i, g in enumerate(_order(gear))}
    keys = [k for k, v in data.EXERCISES.items() if v[1] in rank]
    return sorted(keys, key=lambda k: rank[data.EXERCISES[k][1]])


def choose(focus: str, gear: str, count: int) -> list[str]:
    """Exercise keys for a workout: the same choice every time for the same request."""
    pool = _pool(gear)
    if focus == "full":
        lists = [[k for k in pool if data.EXERCISES[k][2] == b or (b == "cardio" and data.EXERCISES[k][2] == "full")]
                 for b in BUCKETS]
        chosen: list[str] = []
        while len(chosen) < count and any(lists):
            for group in lists:
                if group and len(chosen) < count:
                    chosen.append(group.pop(0))
        return chosen
    first = [k for k in pool if data.EXERCISES[k][2] == focus or (focus == "cardio" and data.EXERCISES[k][2] == "full")]
    filler = [k for k in pool if k not in first and data.EXERCISES[k][2] in ("core", "full", "cardio")]
    return (first + filler)[:count]


def plan_shape(minutes: float) -> tuple[int, int]:
    """(exercises, rounds) for a workout of that length, leaving about 4 minutes for warm-up and cool-down."""
    count = min(8, max(3, int(minutes) // 5))
    return count, min(5, max(1, round((minutes - 4) / count)))


def _workout(args: dict) -> tuple[str, str, int, list[str], int]:
    focus = _pick(args.get("focus"), data.FOCUS_KEY, "full body", "a focus")
    gear = _pick(args.get("equipment"), GEAR_KEY, "bodyweight", "equipment")
    minutes = int(store.number(args.get("minutes") or 20, "workout length", 5, 90))
    count, rounds = plan_shape(minutes)
    return focus, gear, minutes, choose(focus, gear, count), rounds


def _do(key: str, work: int = 40) -> str:
    gear, kind = data.EXERCISES[key][1], data.EXERCISES[key][3]
    if kind == "time":
        return f"{work} seconds"
    return "8 to 10 reps, a challenging weight" if gear == "gym" else "12 to 15 reps" if gear == "body" else "10 to 12 reps"


def _title(focus: str, gear: str, minutes: int) -> str:
    return f"{minutes} minute {FOCUS_NAME[focus]} workout, {GEAR_NAME[gear]}"


def build(args: dict) -> screen.Shown:
    focus, gear, minutes, keys, rounds = _workout(args)
    rows = [["Warm up", "3 minutes", "March on the spot, arm circles, easy squats"]]
    rows += [[data.EXERCISES[k][0], _do(k), data.EXERCISES[k][5]] for k in keys]
    rows.append(["Cool down", "2 minutes", "Slow walk and a few stretches"])
    title = _title(focus, gear, minutes)
    ask = f"Start a {minutes} minute {FOCUS_NAME[focus]} {GEAR_NAME[gear]} workout timer"
    card = screen.card("table", title, f"active-plan-{focus}-{gear}-{minutes}", columns=["Move", "Do", "Watch out for"],
                       rows=rows, text=f"Do the {len(keys)} moves in order, {rounds} rounds, 40 seconds on and 20 off.",
                       buttons=[{"label": "Start timer", "say": ask},
                                {"label": "How to", "say": f"How do I do a {data.EXERCISES[keys[0]][0].lower()}?"}])
    return screen.Shown(f"A {minutes} minute {FOCUS_NAME[focus]} workout with {store.plural(len(keys), 'move')}, "
                        f"{store.plural(rounds, 'round')}. It's on the screen. {store.SAFETY}", card)


def _steps(names: list[str], work: int, rest: int, rounds: int, tips: list[str] | None = None) -> list[dict]:
    steps = [{"label": "Get ready", "kind": "prep", "seconds": 10, "next": names[0], "round": 0, "rounds": rounds,
              "tip": "Find some space."}]
    total = len(names) * rounds
    for r in range(rounds):
        for i, name in enumerate(names):
            n = r * len(names) + i
            nxt = names[(i + 1) % len(names)] if n + 1 < total else "Finished"
            steps.append({"label": name, "kind": "work", "seconds": work, "next": nxt, "round": r + 1,
                          "rounds": rounds, "tip": (tips or [""] * len(names))[i]})
            if rest and n + 1 < total:
                steps.append({"label": "Rest", "kind": "rest", "seconds": rest, "next": nxt, "round": r + 1,
                              "rounds": rounds, "tip": ""})
    return steps


def _timer(title: str, card_id: str, steps: list[dict], text: str, say: str) -> screen.Shown:
    total = sum(s["seconds"] for s in steps)
    if total > 3 * 3600 or len(steps) > 300:
        raise ValueError("That timer is too long; keep it under three hours.")
    card = screen.card("active-timer", title, card_id, data={"title": title, "steps": steps, "total": total},
                       buttons=[{"label": "Log it", "say": say}])
    return screen.Shown(f"{title}: {store.spoken_time(total / 60)}. {text}", card)


def timer(args: dict) -> screen.Shown:
    focus, gear, minutes, keys, rounds = _workout(args)
    work = int(store.number(args.get("work_seconds") or 40, "work time", 10, 300))
    rest = int(store.number(args.get("rest_seconds") if args.get("rest_seconds") is not None else 20, "rest time", 0, 300))
    names = [data.EXERCISES[k][0] for k in keys]
    tips = [data.EXERCISES[k][4].split(". ")[0] + "." for k in keys]
    title = _title(focus, gear, minutes)
    return _timer(title, f"active-timer-{focus}-{gear}-{minutes}", _steps(names, work, rest, rounds, tips),
                  "Press Start; the next move shows under the countdown.",
                  f"Log a {minutes} minute workout in my activity log")


def emom(args: dict) -> screen.Shown:
    minutes = int(store.number(args.get("minutes") or 10, "EMOM length", 2, 60))
    interval = int(store.number(args.get("work_seconds") or 60, "interval", 20, 180))
    moves = [store.clean(m, 60) for m in (args.get("exercises") or []) if store.clean(m)][:6]
    moves = moves or ["10 press-ups", "15 squats", "12 glute bridges"]
    steps = [{"label": "Get ready", "kind": "prep", "seconds": 10, "next": f"Minute 1: {moves[0]}", "round": 0,
              "rounds": minutes, "tip": ""}]
    for m in range(minutes):
        nxt = f"Minute {m + 2}: {moves[(m + 1) % len(moves)]}" if m + 1 < minutes else "Finished"
        steps.append({"label": moves[m % len(moves)], "kind": "work", "seconds": interval, "next": nxt,
                      "round": m + 1, "rounds": minutes, "tip": "Finish early and rest until the next beep."})
    title = f"{minutes} minute EMOM"
    return _timer(title, f"active-emom-{minutes}", steps,
                  f"Every {interval} seconds do: {', then '.join(moves)}. Rest in what's left of the time.",
                  f"Log a {minutes} minute EMOM workout in my activity log")


def circuit(args: dict) -> screen.Shown:
    names = [store.clean(m, 60) for m in (args.get("exercises") or []) if store.clean(m)][:12]
    if not names:
        raise ValueError("Which exercises are in the circuit?")
    work = int(store.number(args.get("work_seconds") or 40, "work time", 5, 300))
    rest = int(store.number(args.get("rest_seconds") if args.get("rest_seconds") is not None else 20, "rest time", 0, 300))
    rounds = int(store.number(args.get("rounds") or 3, "rounds", 1, 12))
    title = f"Circuit: {', '.join(names[:3])}{'…' if len(names) > 3 else ''}"
    return _timer(title, f"active-circuit-{'-'.join(n.lower() for n in names)[:40]}-{work}-{rest}-{rounds}",
                  _steps(names, work, rest, rounds), f"{work} seconds on, {rest} off, {store.plural(rounds, 'round')}.",
                  "Log a circuit workout in my activity log")


def stretch(args: dict) -> screen.Shown:
    text = store.clean(args.get("routine")).lower().replace("_", " ") or "morning"
    key = data.STRETCH_ALIASES.get(text) or next((v for k, v in data.STRETCH_ALIASES.items() if k in text), None)
    if not key:
        raise ValueError("I have morning, after run, pre-run warm-up, lower back and evening stretches.")
    title, blurb, moves = data.STRETCHES[key]
    steps = [{"title": t, "text": d, "seconds": s} for t, d, s in moves]
    card = screen.card("active-steps", title, f"active-stretch-{key.replace(' ', '-')}", data={"steps": steps},
                       text=blurb, buttons=[{"label": "Another routine", "say": "What stretch routines have you got?"}])
    return screen.Shown(f"{title}: {len(steps)} moves, {blurb.split(', ')[-1].rstrip('.')}. Press Next for each one. "
                        "Stop if anything hurts.", card)


def howto(args: dict) -> screen.Shown:
    key = _resolve(args.get("exercise"))
    name, gear, focus, kind, how, mistake, easier = data.EXERCISES[key]
    text = (f"{how}\n\nCommon mistake: {mistake}\nEasier: {easier}\n"
            f"Kit: {GEAR_NAME[gear]}. Works: {focus if focus != 'full' else 'the whole body'}. "
            f"{'Time it' if kind == 'time' else 'Count reps'}; stop if anything hurts.")
    card = screen.card("text", name, f"active-howto-{key}", text=text,
                       buttons=[{"label": "All exercises", "say": "List the exercises you can show me how to do"}])
    return screen.Shown(f"{name}. {how} Common mistake: {mistake}", card)


def exercises(args: dict) -> screen.Shown:
    gear = GEAR_KEY.get(store.clean(args.get("equipment")).lower().replace("_", " "))
    rows = [[v[0], GEAR_NAME[v[1]], v[2]] for v in data.EXERCISES.values() if not gear or v[1] == gear]
    card = screen.card("table", "Exercises I can show", f"active-exercises-{gear or 'all'}",
                       columns=["Exercise", "Kit", "Works"], rows=rows,
                       buttons=[{"label": g.title(), "say": f"List the {g} exercises"} for g in GEAR_NAME.values()])
    return screen.Shown(f"I can show {len(rows)} exercises. Ask how to do any of them.", card)


def tool_definitions() -> list[dict]:
    listed = {"type": "array", "items": {"type": "string"}}
    return [{
        "name": "active_workout",
        "description": "Workouts on screen. build (workout plan pop-up by minutes, focus full body, upper body, lower "
                       "body, core or cardio, and equipment bodyweight, dumbbell or gym), timer (the guided workout "
                       "timer for that plan with a big countdown, next exercise and beeps; same arguments, plus "
                       "work_seconds and rest_seconds), emom (every-minute-on-the-minute timer; minutes, exercises like "
                       "'10 press-ups'), circuit (your own exercises, work_seconds, rest_seconds, rounds), stretch "
                       "(routine morning, after run, pre-run warm-up, lower back or evening, as step cards), howto (how "
                       "to do an exercise such as press-up, squat, plank, deadlift), exercises (list what I can "
                       "explain). Tabata and plain HIIT timers are health-plus tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "minutes": {"type": "number", "description": "Workout length; build and timer default 20."},
                "focus": {"type": "string", "enum": data.FOCUSES},
                "equipment": {"type": "string", "enum": data.GEARS},
                "work_seconds": {"type": "number"},
                "rest_seconds": {"type": "number"},
                "rounds": {"type": "number"},
                "exercises": listed,
                "routine": {"type": "string", "description": "stretch: morning, after run, pre-run, lower back, evening."},
                "exercise": {"type": "string", "description": "howto: the exercise name."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    if action == "exercises":
        return exercises(args)
    return {"build": build, "timer": timer, "emom": emom, "circuit": circuit, "stretch": stretch,
            "howto": howto}[action](args)
