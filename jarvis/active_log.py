"""Activity log for runs, walks, rides and hikes (distance, time, pace or speed), weekly distance chart, records, rest-day
advice from recent load, plus the strength log and fitness challenges (see active_strength.py and active_challenge.py).

Saved on this PC under "log" in active.json. (Runs can also go in the health-plus running log; this one covers any
activity.) Nothing here is medical advice.
"""

from datetime import timedelta

import active_challenge as challenge
import active_store as store
import active_strength as strength
import screen
from config import Settings

NAMES = {"active_log"}
ACTIONS = ["log", "week", "records", "history", "undo", "rest_day", "strength_log", "strength_progress",
           "challenge_start", "challenge_check", "challenge_show", "challenge_stop"]
KINDS = ["run", "walk", "cycle", "hike", "swim", "row", "other"]
KIND_WORDS = {"run": "run", "running": "run", "jog": "run", "jogging": "run", "walk": "walk", "walking": "walk",
              "cycle": "cycle", "cycling": "cycle", "bike": "cycle", "ride": "cycle", "biking": "cycle",
              "hike": "hike", "hiking": "hike", "hill walk": "hike", "swim": "swim", "swimming": "swim",
              "row": "row", "rowing": "row"}
RESTED = 3
HARD_MINUTES = 90


def _rows(settings: Settings) -> list[dict]:
    return store.section(settings, "log", [])


def _kind(value) -> str:
    text = store.clean(value).lower()
    return KIND_WORDS.get(text) or ("other" if text else "run")


def log(settings: Settings, args: dict) -> str:
    kind = _kind(args.get("kind"))
    mins = store.duration(args.get("time"), args.get("minutes"))
    km = store.km_from(args["distance"], args.get("unit")) if args.get("distance") not in (None, "") else 0
    rows = _rows(settings)
    entry = {"date": store.day(args.get("date")).isoformat(), "kind": kind, "km": round(km, 3),
             "minutes": round(mins, 2), "note": store.clean(args.get("note"), 120)}
    rows.append(entry)
    store.save_section(settings, "log", rows[-5000:])
    if not km:
        return f"Logged {kind}, {store.spoken_time(mins)}."
    speed = kind == "cycle"
    detail = store.speed_text(km, mins) if speed else store.pace_text(km, mins)
    before = [r for r in rows[:-1] if r["kind"] == kind and r["km"] >= 2]
    pb = " That's your fastest one yet!" if km >= 2 and before and all(
        r["km"] / r["minutes"] < km / mins for r in before) else ""
    return f"Logged {store.dist_text(km)} {kind} in {store.spoken_time(mins)}: {detail}.{pb}"


def _weeks(rows: list[dict], count: int) -> tuple[list[str], list[float]]:
    start = store.today() - timedelta(days=store.today().weekday())
    weeks = [start - timedelta(weeks=i) for i in range(count - 1, -1, -1)]
    totals = {w: 0.0 for w in weeks}
    for r in rows:
        monday = store.day(r["date"]) - timedelta(days=store.day(r["date"]).weekday())
        if monday in totals:
            totals[monday] += r["km"]
    return [w.strftime("%d %b") for w in weeks], [round(v, 2) for v in totals.values()]


def week(settings: Settings, kind=None) -> str | screen.Shown:
    wanted = _kind(kind) if store.clean(kind) else ""
    rows = [r for r in _rows(settings) if not wanted or r["kind"] == wanted]
    if not rows:
        return "Nothing logged yet. Say something like 'I walked 5 km in an hour'."
    labels, values = _weeks(rows, 8)
    monday = store.today() - timedelta(days=store.today().weekday())
    mine = [r for r in rows if store.day(r["date"]) >= monday]
    km, mins = sum(r["km"] for r in mine), sum(r["minutes"] for r in mine)
    text = f"This week: {store.plural(len(mine), 'session')}, {store.dist_text(km)}, {store.spoken_time(mins)}."
    card = screen.card("chart", f"Weekly distance{', ' + wanted if wanted else ''}", f"active-week-{wanted or 'all'}",
                       chart={"type": "bar", "labels": labels, "values": values, "unit": "km"}, text=text)
    return screen.Shown(text, card)


def records(settings: Settings) -> str | screen.Shown:
    rows = _rows(settings)
    if not rows:
        return "No activities logged yet."
    table = []
    for kind in KINDS:
        mine = [r for r in rows if r["kind"] == kind]
        far = [r for r in mine if r["km"]]
        if not far:
            continue
        longest = max(far, key=lambda r: r["km"])
        quick = max((r for r in far if r["km"] >= 2), key=lambda r: r["km"] / r["minutes"], default=None)
        best = (store.speed_text(quick["km"], quick["minutes"]) if kind == "cycle" else
                store.pace_text(quick["km"], quick["minutes"])) if quick else "needs a 2 km+ entry"
        table.append([kind.title(), f"{longest['km']:.1f} km on {longest['date']}", best,
                      store.spoken_time(max(r["minutes"] for r in mine))])
    if not table:
        return "You have entries but none with a distance yet."
    _, weekly = _weeks(rows, 52)
    card = screen.card("table", "Personal bests", "active-records",
                       columns=["Activity", "Longest", "Fastest (2 km+)", "Longest time"], rows=table,
                       text=f"Biggest week in the last year: {max(weekly):.1f} km.")
    return screen.Shown(f"Your records are on the screen. Biggest week this year: {max(weekly):.1f} km.", card)


def history(settings: Settings) -> str | screen.Shown:
    rows = _rows(settings)[-15:][::-1]
    if not rows:
        return "Nothing logged yet."
    table = [[r["date"], r["kind"], f"{r['km']:.1f} km" if r["km"] else "", store.clock(r["minutes"]),
              store.pace_text(r["km"], r["minutes"]) if r["km"] and r["kind"] != "cycle" else
              store.speed_text(r["km"], r["minutes"]) if r["km"] else "", r.get("note", "")] for r in rows]
    card = screen.card("table", "Recent activities", "active-history",
                       columns=["Date", "What", "Distance", "Time", "Pace or speed", "Note"], rows=table)
    return screen.Shown(f"Your last {store.plural(len(rows), 'activity', 'activities')} are on the screen.", card)


def undo(settings: Settings, confirmed: bool) -> str:
    rows = _rows(settings)
    if not rows:
        return "There's nothing to undo."
    last = rows[-1]
    if not confirmed:
        return (f"That would remove the {last['kind']} on {last['date']} ({last['km']:g} km, {last['minutes']:g} minutes). "
                "Ask the user to confirm, then call again with confirmed true.")
    store.save_section(settings, "log", rows[:-1])
    return f"Removed the {last['kind']} on {last['date']}."


def rest_day(settings: Settings) -> str | screen.Shown:
    today = store.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    load: dict[str, list] = {d.isoformat(): [0.0, []] for d in days}
    for r in _rows(settings):
        if r["date"] in load:
            load[r["date"]][0] += r["minutes"]
            load[r["date"]][1].append(r["kind"])
    for r in store.section(settings, "strength", []):
        if r["date"] in load and "strength" not in load[r["date"]][1]:
            load[r["date"]][0] += 45
            load[r["date"]][1].append("strength")
    active = [d for d in days if load[d.isoformat()][0] > 0]
    streak = 0
    day = today if load[today.isoformat()][0] > 0 else today - timedelta(days=1)
    while day.isoformat() in load and load[day.isoformat()][0] > 0:
        streak += 1
        day -= timedelta(days=1)
    recent = sum(load[d.isoformat()][0] for d in days[-3:])
    yesterday = load[(today - timedelta(days=1)).isoformat()][0]
    if streak >= RESTED or len(active) >= 6:
        verdict = "Take a rest day today. You've been going hard and recovery is when you get stronger."
    elif yesterday >= HARD_MINUTES or recent >= 240:
        verdict = "Go easy today: a gentle walk or a stretch rather than a hard session."
    elif not active:
        verdict = "You're well rested. It's a good day to get moving."
    else:
        verdict = "You're fine to train today; listen to your body."
    table = [[d.strftime("%a %d %b"), ", ".join(load[d.isoformat()][1]) or "rest",
              f"{load[d.isoformat()][0]:g}" if load[d.isoformat()][0] else ""] for d in days]
    card = screen.card("table", "Last 7 days", "active-rest-day", columns=["Day", "What", "Minutes"], rows=table,
                       text=verdict)
    return screen.Shown(f"{verdict} You've been active on {len(active)} of the last 7 days.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "active_log",
        "description": "Activity, strength and challenge log. log (a run, walk, cycle, hike, swim or row: distance with "
                       "unit km or miles, time '27:45' or minutes, date and note optional; says pace or speed), week "
                       "(weekly distance chart, kind optional), records (longest and fastest), history, undo (removes "
                       "the last entry; confirmed true only after the user confirms), rest_day (should I rest today, "
                       "from the last 7 days), strength_log (exercise, weight_kg, reps, sets; gives an estimated "
                       "one-rep max), strength_progress (chart for an exercise, or all lifts), challenge_start "
                       "(name plank, squats, press-ups, sit-ups or your own with unit, start_target, step; days "
                       "default 30), challenge_check (I did today's challenge; date optional), challenge_show (streak "
                       "calendar), challenge_stop (confirmed true only after the user confirms).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "kind": {"type": "string", "description": "run, walk, cycle, hike, swim, row or other."},
                "distance": {"type": "number"},
                "unit": {"type": "string", "enum": ["km", "miles"]},
                "time": {"type": "string", "description": "hh:mm:ss, mm:ss or '27 minutes'."},
                "minutes": {"type": "number"},
                "date": {"type": "string", "description": "YYYY-MM-DD, today, yesterday or a weekday."},
                "note": {"type": "string"},
                "exercise": {"type": "string"},
                "weight_kg": {"type": "number"},
                "reps": {"type": "number"},
                "sets": {"type": "number"},
                "name": {"type": "string", "description": "Challenge name."},
                "days": {"type": "number"},
                "unit_name": {"type": "string", "description": "challenge_start: what is counted, e.g. reps."},
                "start_target": {"type": "number"},
                "step": {"type": "number", "description": "How much the daily target grows."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "log":
        return log(settings, args)
    if action == "week":
        return week(settings, args.get("kind"))
    if action == "records":
        return records(settings)
    if action == "history":
        return history(settings)
    if action == "undo":
        return undo(settings, bool(args.get("confirmed")))
    if action == "rest_day":
        return rest_day(settings)
    if action == "strength_log":
        return strength.log(settings, args)
    if action == "strength_progress":
        return strength.progress(settings, args.get("exercise"))
    if action in ("challenge_start", "challenge_check", "challenge_show", "challenge_stop"):
        return challenge_action(action, settings, args)
    raise ValueError(f"Unknown action {action}.")


def challenge_action(action: str, settings: Settings, args: dict):
    args = {**args, "unit": args.get("unit_name")}
    if action == "challenge_start":
        return challenge.start(settings, args)
    if action == "challenge_check":
        return challenge.check(settings, args)
    if action == "challenge_show":
        return challenge.show(settings, args.get("name"))
    return challenge.stop(settings, args)
