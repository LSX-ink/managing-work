"""Fitness tools: a HIIT interval timer that beeps, workout plan templates with today's session as a checklist,
stretch and desk-break routines with a timer per move, a running log with pace and personal bests, heart-rate
zones and bedtimes for 90-minute sleep cycles.

Saved in health-plus-runs.json, health-plus-plan.json and health-plus-intervals.json in the memory folder.
"""

from datetime import date, datetime, timedelta

import screen
import wellness_store as store
from config import Settings

screen.EXTRA_KINDS.add("wellness-intervals")

KM_PER_MILE = 1.609344
FALL_ASLEEP_MIN = 14
MAX_TIMER_SECONDS = 2 * 3600
DISTANCES = {"5k": 5.0, "10k": 10.0, "half marathon": 21.1, "marathon": 42.2}

STRETCHES = [("Neck rolls, slowly each way", 30), ("Shoulder rolls", 30), ("Chest opener, hands behind back", 30),
             ("Standing quad stretch, left leg", 30), ("Standing quad stretch, right leg", 30),
             ("Hamstring stretch, reach for your toes", 40), ("Calf stretch against a wall, each leg", 40),
             ("Hip flexor lunge stretch, each side", 40), ("Cat-cow on hands and knees", 45), ("Child's pose", 45)]
DESK = [("Stand up and march on the spot", 45), ("Shoulder shrugs and rolls", 30), ("Neck tilt, ear to shoulder", 30),
        ("Seated twist, each side", 30), ("Wrist and finger stretch", 30), ("Chest opener, hands clasped behind", 30),
        ("Seated leg raises", 30), ("Calf raises, standing", 30)]
FULL_BODY = {
    "A": ["Warm-up: 5 minutes marching or brisk walk", "Bodyweight squats: 3 x 10", "Knee or wall press-ups: 3 x 8",
          "Glute bridges: 3 x 12", "Bent-over rows with water bottles: 3 x 10", "Plank: 3 x 20 seconds",
          "Cool-down stretch: 5 minutes"],
    "B": ["Warm-up: 5 minutes marching or brisk walk", "Reverse lunges: 3 x 8 each leg",
          "Incline press-ups on a table: 3 x 8", "Superman holds: 3 x 10", "Step-ups: 3 x 10 each leg",
          "Dead bugs: 3 x 8 each side", "Cool-down stretch: 5 minutes"],
}
RUN_WEEKS = ["Run 60 seconds, walk 90 seconds, 8 times", "Run 90 seconds, walk 2 minutes, 6 times",
             "Twice: run 90 seconds, walk 90 seconds, run 3 minutes, walk 3 minutes",
             "Run 3, walk 1.5, run 5, walk 2.5, run 3, walk 1.5, run 5 minutes",
             "Run 8 minutes, walk 5 minutes, run 8 minutes", "Run 10 minutes, walk 3 minutes, run 10 minutes",
             "Run 25 minutes", "Run 28 minutes", "Run 30 minutes, about 5k"]
PLANS = {
    "full body": "Beginner full body, three times a week, alternating sessions A and B",
    "5k": "Couch-to-5K style run plan: 9 weeks, 3 runs a week",
    "stretching": "Stretching routine, about 6 minutes",
    "desk": "Desk exercises, about 4 minutes",
}


def session(plan: str, n: int) -> tuple[str, list[str]]:
    """(label, moves) for session n (from 0) of a plan."""
    if plan == "full body":
        which = "AB"[n % 2]
        return f"Session {n + 1} ({which})", FULL_BODY[which]
    if plan == "5k":
        week = min(n // 3, 8)
        return (f"Week {week + 1}, run {n % 3 + 1} of 3",
                ["Warm-up: 5 minute brisk walk", RUN_WEEKS[week], "Cool-down: 5 minute walk and stretch"])
    moves = STRETCHES if plan == "stretching" else DESK
    return PLANS[plan].split(",")[0], [f"{m} ({s} seconds)" for m, s in moves]


def _plan_key(name) -> str:
    text = store.clean(name).lower()
    for key, words in (("5k", ("5k", "run", "couch")), ("full body", ("full", "body", "beginner", "strength")),
                       ("stretching", ("stretch",)), ("desk", ("desk", "office"))):
        if any(w in text for w in words):
            return key
    raise ValueError(f"Pick a plan: {', '.join(PLANS)}.")


def plans_list(settings: Settings) -> screen.Shown:
    state = store.load(settings, "plan", {})
    items = [{"label": f"{desc}" + ("  (current)" if state.get("plan") == key else ""),
              "say": f"Start the {key} workout plan."} for key, desc in PLANS.items()]
    return screen.Shown("The workout plans are on the screen: " + "; ".join(PLANS.values()) + ".",
                        screen.card("list", "Workout plans", "wellness-plans", items=items,
                                    text="Click one to start it. Take it at your own pace."))


def plan_start(settings: Settings, name) -> screen.Shown:
    key = _plan_key(name)
    store.save(settings, "plan", {"plan": key, "session": 0, "ticked": [], "started": store.today().isoformat(),
                                  "history": store.load(settings, "plan", {}).get("history", [])})
    return plan_today(settings, f"Started the {PLANS[key].split(',')[0]} plan. ")


def plan_today(settings: Settings, lead: str = "") -> screen.Shown | str:
    state = store.load(settings, "plan", {})
    if state.get("plan") not in PLANS:
        return plans_list(settings)
    label, moves = session(state["plan"], state.get("session", 0))
    ticked = state.get("ticked", [])
    items = [{"label": m, "done": m in ticked, "say": f"Tick '{m}' in my workout session."} for m in moves]
    buttons = [{"label": "Session done", "say": "Mark today's workout session as done."}]
    if state["plan"] in ("stretching", "desk"):
        buttons.append({"label": "Start timer", "say": f"Start the {state['plan']} routine timer."})
    said = f"{lead}Today's session: {label}, {store.plural(len(moves), 'part')}."
    return screen.Shown(said, screen.card("list", f"Workout: {label}", "wellness-session", items=items, checks=True,
                                          buttons=buttons))


def plan_tick(settings: Settings, move) -> str:
    state = store.load(settings, "plan", {})
    if state.get("plan") not in PLANS:
        return "No workout plan is running; pick one first."
    _, moves = session(state["plan"], state.get("session", 0))
    found = store.find([{"m": m} for m in moves], "m", move)
    if not found:
        raise ValueError("That isn't in today's session: " + "; ".join(moves) + ".")
    m = found[0]["m"]
    ticked = state.get("ticked", [])
    state["ticked"] = [t for t in ticked if t != m] if m in ticked else [*ticked, m]
    store.save(settings, "plan", state)
    left = len([x for x in moves if x not in state["ticked"]])
    return f"{'Ticked' if m in state['ticked'] else 'Unticked'} {m}. " + (
        f"{store.plural(left, 'part')} to go." if left else "All done; say so and I'll mark the session complete.")


def plan_done(settings: Settings) -> str:
    state = store.load(settings, "plan", {})
    if state.get("plan") not in PLANS:
        return "No workout plan is running."
    label, _ = session(state["plan"], state.get("session", 0))
    state["history"] = [*state.get("history", []), {"date": store.today().isoformat(), "plan": state["plan"],
                                                    "session": label}][-500:]
    state["session"], state["ticked"] = state.get("session", 0) + 1, []
    finished = state["plan"] == "5k" and state["session"] >= 27
    if finished:
        state["session"] = 26
    store.save(settings, "plan", state)
    if finished:
        return "That's the whole 5K plan finished. Brilliant work!"
    return f"Marked {label} done. Next time: {session(state['plan'], state['session'])[0]}."


# Timers: HIIT intervals and routines, drawn by frontend/popup-health-plus.js with a beep at each change.

def _timer(title: str, phases: list[dict], said: str) -> screen.Shown:
    if sum(p["seconds"] for p in phases) > MAX_TIMER_SECONDS:
        raise ValueError("That's over two hours; make it shorter.")
    return screen.Shown(said, screen.card("wellness-intervals", title, "wellness-timer",
                                          data={"phases": phases, "beep": True},
                                          buttons=[{"label": "Close", "say": "Close the interval timer."}]))


def interval_timer(settings: Settings, args: dict) -> screen.Shown:
    presets = store.load(settings, "intervals", {})
    name = store.clean(args.get("name"), 40).lower()
    if args.get("work_seconds") is None:
        if not name:
            raise ValueError("Give the work and rest seconds and the number of rounds, or a saved timer's name.")
        if name not in presets:
            raise ValueError(f"No saved interval timer called {name}. Saved: {', '.join(presets) or 'none'}.")
        spec = presets[name]
    else:
        spec = {"work": int(store.number(args["work_seconds"], "work time", 5, 3600)),
                "rest": int(store.number(args.get("rest_seconds") or 0, "rest time", 0, 3600)),
                "rounds": int(store.number(args.get("rounds") or 1, "number of rounds", 1, 50)),
                "warmup": int(store.number(args.get("warmup_seconds") or 0, "warm-up", 0, 1800)),
                "cooldown": int(store.number(args.get("cooldown_seconds") or 0, "cool-down", 0, 1800))}
        if name:
            presets[name] = spec
            store.save(settings, "intervals", dict(list(presets.items())[-30:]))
    phases = [{"label": "Warm up", "seconds": spec["warmup"], "type": "rest"}] if spec.get("warmup") else []
    for r in range(1, spec["rounds"] + 1):
        phases.append({"label": f"Work, round {r} of {spec['rounds']}", "seconds": spec["work"], "type": "work"})
        if spec["rest"] and r < spec["rounds"]:
            phases.append({"label": "Rest", "seconds": spec["rest"], "type": "rest"})
    if spec.get("cooldown"):
        phases.append({"label": "Cool down", "seconds": spec["cooldown"], "type": "rest"})
    total = sum(p["seconds"] for p in phases)
    saved = f" Saved as {name}." if name and args.get("work_seconds") is not None else ""
    return _timer(f"Intervals {spec['work']}/{spec['rest']} x{spec['rounds']}", phases,
                  f"Interval timer started: {spec['rounds']} rounds, {store.duration(total)} in all.{saved}")


def routine_timer(routine, seconds=None) -> screen.Shown:
    key = "desk" if "desk" in store.clean(routine).lower() or not routine else "stretching"
    moves = DESK if key == "desk" else STRETCHES
    each = int(store.number(seconds, "seconds per move", 10, 300)) if seconds else None
    phases = [{"label": m, "seconds": each or s, "type": "move"} for m, s in moves]
    total = sum(p["seconds"] for p in phases)
    return _timer("Desk break" if key == "desk" else "Stretching", phases,
                  f"{'Desk break' if key == 'desk' else 'Stretching routine'} started: "
                  f"{store.plural(len(phases), 'move')}, {store.duration(total)}. First: {phases[0]['label']}.")


# Running

def _pace(km: float, secs: int) -> str:
    return f"{store.duration(secs / km)} per km, {store.duration(secs / km * KM_PER_MILE)} per mile"


def _bests(runs: list[dict]) -> dict:
    out = {}
    for name, km in DISTANCES.items():
        found = [r for r in runs if abs(r["km"] - km) <= max(0.1, km * 0.02)]
        if found:
            out[name] = min(found, key=lambda r: r["seconds"])
    return out


def run_add(settings: Settings, args: dict) -> str:
    dist = store.number(args.get("distance"), "distance", 0.1, 250)
    km = round(dist * KM_PER_MILE if args.get("unit") == "miles" else dist, 2)
    secs = store.seconds(args.get("time"), "run time")
    if secs < 60:
        raise ValueError("Give the run time like 25:30, or in minutes.")
    runs = store.load(settings, "runs", [])
    before = _bests(runs)
    entry = {"date": store.day(args.get("date")).isoformat(), "km": km, "seconds": secs}
    runs.append(entry)
    store.save(settings, "runs", sorted(runs, key=lambda r: r["date"]))
    pb = next((n for n, r in _bests(runs).items() if r is entry and n in before), "")
    first = next((n for n, r in _bests(runs).items() if r is entry and n not in before), "")
    extra = f" New {pb} personal best!" if pb else (f" Your first {first} logged." if first else "")
    return f"Logged {km:g} km in {store.duration(secs)}: {_pace(km, secs)}.{extra}"


def run_show(settings: Settings):
    runs = store.load(settings, "runs", [])
    if not runs:
        return "No runs logged yet."
    monday = store.today() - timedelta(days=store.today().weekday())
    weeks = [monday - timedelta(weeks=i) for i in range(7, -1, -1)]
    km = [round(sum(r["km"] for r in runs if w.isoformat() <= r["date"] < (w + timedelta(days=7)).isoformat()), 1)
          for w in weeks]
    lines = [f"{n}: {store.duration(r['seconds'])} on {store.short(date.fromisoformat(r['date']))}"
             for n, r in _bests(runs).items()]
    longest = max(runs, key=lambda r: r["km"])
    fastest = min(runs, key=lambda r: r["seconds"] / r["km"])
    lines += [f"Longest run: {longest['km']:g} km", f"Fastest pace: {_pace(fastest['km'], fastest['seconds'])}"]
    this_week = len([r for r in runs if r["date"] >= monday.isoformat()])
    said = (f"{km[-1]:g} km this week from {store.plural(this_week, 'run')}." if this_week
            else f"No runs yet this week; {len(runs)} logged in all.")
    return screen.Shown(said + " Personal bests: " + "; ".join(lines) + ".", screen.card(
        "chart", "Running, km per week", "wellness-runs", text="\n".join(lines),
        chart={"type": "bar", "labels": [store.short(w) for w in weeks], "values": km, "unit": " km"}))


# Heart-rate zones and sleep cycles

ZONES = [("1 Very easy", 0.5, 0.6), ("2 Easy", 0.6, 0.7), ("3 Moderate", 0.7, 0.8), ("4 Hard", 0.8, 0.9),
         ("5 Maximum", 0.9, 1.0)]


def hr_zones(age, resting=None) -> screen.Shown:
    age = int(store.number(age, "age", 10, 100))
    top = 220 - age
    rest = int(store.number(resting, "resting heart rate", 30, 120)) if resting else None
    rows = []
    for name, lo, hi in ZONES:
        row = [name, f"{lo:.0%}-{hi:.0%}", f"{round(top * lo)}-{round(top * hi)}"]
        if rest:
            row.append(f"{round(rest + (top - rest) * lo)}-{round(rest + (top - rest) * hi)}")
        rows.append(row)
    said = f"Estimated maximum heart rate {top} (220 minus your age)." + (
        f" With a resting rate of {rest}, zone 2 is about {rows[1][3]} beats a minute." if rest else "")
    columns = ["Zone", "% effort", "220-age bpm"] + (["Karvonen bpm"] if rest else [])
    return screen.Shown(said, screen.card("table", "Heart-rate zones", "wellness-zones", columns=columns, rows=rows,
                                          text=said + " These are rough estimates, not medical advice."))


def sleep_times(wake=None, bedtime=None) -> screen.Shown:
    if not wake and not bedtime:
        raise ValueError("Give a wake-up time or a bedtime.")
    base = datetime.combine(store.today(), datetime.strptime(store.clock(wake or bedtime), "%H:%M").time())
    rows = []
    for cycles in (6, 5, 4, 3):
        span = timedelta(minutes=90 * cycles + FALL_ASLEEP_MIN)
        when = base - span if wake else base + span
        rows.append([str(cycles), f"{cycles * 1.5:g} h", when.strftime("%H:%M")])
    if wake:
        said = f"To wake at {base:%H:%M}, go to bed at {rows[0][2]} or {rows[1][2]}."
        columns = ["Cycles", "Sleep", "Bedtime"]
    else:
        said = f"Going to bed at {base:%H:%M}, wake at {rows[1][2]} or {rows[0][2]}."
        columns = ["Cycles", "Sleep", "Wake at"]
    return screen.Shown(said, screen.card("table", "Sleep cycles", "wellness-sleep", columns=columns, rows=rows,
                                          text=said + f" Allows {FALL_ASLEEP_MIN} minutes to fall asleep."))


def tool_definitions() -> list[dict]:
    return [{
        "name": "fitness_coach",
        "description": "Workouts and fitness tools with pop-ups. interval_timer: HIIT / Tabata interval timer "
                       "that beeps (work_seconds, rest_seconds, rounds, optional warm-up and cool-down; name saves "
                       "it, or give just a saved name). plans: workout plan templates (beginner full body, 5k run "
                       "plan, stretching, desk exercises); plan_start (plan); plan_today (today's session as a "
                       "checklist); plan_tick (move); plan_done (session finished). routine_timer: stretch or desk "
                       "break routine with a timer per move (routine desk or stretching). run_add (distance, unit "
                       "km or miles, time mm:ss): pace per km and mile; run_show: weekly km chart and personal "
                       "bests. hr_zones: heart-rate training zones (age, resting_hr for Karvonen). sleep_times: "
                       "bedtimes for 90-minute sleep cycles from a wake time, or wake times from a bedtime.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "interval_timer", "plans", "plan_start", "plan_today", "plan_tick", "plan_done",
                    "routine_timer", "run_add", "run_show", "hr_zones", "sleep_times"]},
                "work_seconds": {"type": "integer"},
                "rest_seconds": {"type": "integer"},
                "rounds": {"type": "integer"},
                "warmup_seconds": {"type": "integer"},
                "cooldown_seconds": {"type": "integer"},
                "name": {"type": "string", "description": "Name of a saved interval timer."},
                "plan": {"type": "string", "enum": list(PLANS)},
                "move": {"type": "string", "description": "Words from a move in today's session."},
                "routine": {"type": "string", "enum": ["desk", "stretching"]},
                "seconds": {"type": "integer", "description": "routine_timer: seconds per move."},
                "distance": {"type": "number"},
                "unit": {"type": "string", "enum": ["km", "miles"]},
                "time": {"type": "string", "description": "Run time, e.g. '27:45' or '1:02:10'."},
                "date": {"type": "string", "description": "YYYY-MM-DD or yesterday; default today."},
                "age": {"type": "integer"},
                "resting_hr": {"type": "integer"},
                "wake": {"type": "string", "description": "Wake-up time, e.g. 07:00."},
                "bedtime": {"type": "string", "description": "Bedtime, e.g. 23:00."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"fitness_coach"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "interval_timer":
        return interval_timer(settings, args)
    if action == "plans":
        return plans_list(settings)
    if action == "plan_start":
        return plan_start(settings, args.get("plan"))
    if action == "plan_today":
        return plan_today(settings)
    if action == "plan_tick":
        return plan_tick(settings, args.get("move"))
    if action == "plan_done":
        return plan_done(settings)
    if action == "routine_timer":
        return routine_timer(args.get("routine"), args.get("seconds"))
    if action == "run_add":
        return run_add(settings, args)
    if action == "run_show":
        return run_show(settings)
    if action == "hr_zones":
        return hr_zones(args.get("age"), args.get("resting_hr"))
    if action == "sleep_times":
        return sleep_times(args.get("wake"), args.get("bedtime"))
    raise ValueError(f"Unknown action {action}.")
