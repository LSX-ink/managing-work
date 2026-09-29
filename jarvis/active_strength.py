"""Strength log for the active abilities: exercise, weight, reps and sets, an estimated one-rep max (Epley) and a
progress chart. Saved under "strength" in active.json. (The simple gym log in learning-and-goals stays separate.)
"""

import active_store as store
import screen
from config import Settings


def one_rep_max(weight: float, reps: float) -> float:
    return weight if reps <= 1 else weight * (1 + reps / 30)


def _rows(settings: Settings) -> list[dict]:
    return store.section(settings, "strength", [])


def _name(rows: list[dict], value) -> str:
    wanted = store.need(value, "exercise", 60)
    for r in rows:
        if r["exercise"].lower() == wanted.lower():
            return r["exercise"]
    return wanted


def log(settings: Settings, args: dict) -> str:
    rows = _rows(settings)
    exercise = _name(rows, args.get("exercise"))
    weight = store.number(args.get("weight_kg"), "weight", 0, 1000)
    reps = store.number(args.get("reps"), "reps", 1, 100)
    sets = int(store.number(args.get("sets") or 1, "sets", 1, 30))
    e1rm = round(one_rep_max(weight, reps), 1)
    best = max((r["e1rm"] for r in rows if r["exercise"] == exercise), default=0)
    rows.append({"date": store.day(args.get("date")).isoformat(), "exercise": exercise, "weight_kg": weight,
                 "reps": reps, "sets": sets, "e1rm": e1rm})
    store.save_section(settings, "strength", rows[-5000:])
    pb = " That's a new personal best!" if e1rm > best > 0 else ""
    return (f"Logged {exercise}: {sets} x {reps:g} at {weight:g} kg. Estimated one-rep max {e1rm:g} kg.{pb}")


def progress(settings: Settings, exercise=None) -> str | screen.Shown:
    rows = _rows(settings)
    if not rows:
        return "No lifts logged yet. Say something like 'I squatted 3 sets of 5 at 60 kilos'."
    if not store.clean(exercise):
        lifts: dict[str, list[dict]] = {}
        for r in rows:
            lifts.setdefault(r["exercise"], []).append(r)
        table = [[n, f"{max(x['e1rm'] for x in v):g} kg", str(len({x['date'] for x in v})),
                  max(x["date"] for x in v)] for n, v in sorted(lifts.items())]
        card = screen.card("table", "Strength log", "active-strength", columns=["Lift", "Best 1RM", "Days", "Last"],
                           rows=table, buttons=[{"label": n, "say": f"Show my {n} progress"} for n, _ in
                                                sorted(lifts.items())[:6]])
        return screen.Shown(f"You've logged {store.plural(len(lifts), 'lift')}. Ask for one to see its chart.", card)
    name = _name(rows, exercise)
    mine = [r for r in rows if r["exercise"].lower() == name.lower()]
    if not mine:
        raise ValueError(f"You haven't logged {name} yet.")
    best_by_day: dict[str, float] = {}
    for r in mine:
        best_by_day[r["date"]] = max(best_by_day.get(r["date"], 0), r["e1rm"])
    days = sorted(best_by_day)[-30:]
    top = max(mine, key=lambda r: r["e1rm"])
    card = screen.card("chart", f"{name}: estimated 1RM", f"active-strength-{name.lower()}",
                       chart={"type": "line", "labels": [d[5:] for d in days], "values": [best_by_day[d] for d in days],
                              "unit": "kg"},
                       text=f"Best: {top['weight_kg']:g} kg x {top['reps']:g} on {top['date']}, about {top['e1rm']:g} kg "
                            f"for one rep.")
    first, last = best_by_day[days[0]], best_by_day[days[-1]]
    change = f", up {last - first:g} kg since the first day" if last > first and len(days) > 1 else ""
    return screen.Shown(f"Your best {name} is about {top['e1rm']:g} kg for one rep{change}.", card)
