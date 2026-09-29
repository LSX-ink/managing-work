"""Fitness calculators: pace and speed, finish time at a pace, race time predictions (Riegel), even splits, calories
burned from the MET table, and a one-rep-max estimate with training percentages. Pure maths, nothing is sent anywhere.
Estimates only; not medical advice.
"""

import active_data as data
import active_store as store
import screen
from config import Settings

NAMES = {"active_calc"}
ACTIONS = ["pace", "finish_time", "race_predict", "splits", "calories", "met_table", "one_rep_max"]
RACES = {"5k": 5.0, "10k": 10.0, "half marathon": 21.0975, "marathon": 42.195}
RACE_WORDS = {"5k": "5k", "5 k": "5k", "parkrun": "5k", "10k": "10k", "10 k": "10k", "half": "half marathon",
              "half marathon": "half marathon", "marathon": "marathon", "mile": "mile"}
RIEGEL = 1.06
PERCENTS = [(100, 1), (95, 2), (90, 4), (85, 6), (80, 8), (75, 10), (70, 12), (65, 15), (60, 20)]


def _km(args: dict) -> float:
    word = store.clean(args.get("race")).lower()
    if word:
        if RACE_WORDS.get(word) == "mile":
            return store.KM_PER_MILE
        if RACE_WORDS.get(word) in RACES:
            return RACES[RACE_WORDS[word]]
        raise ValueError("I know 5k, 10k, half marathon, marathon and mile; or give a distance.")
    if args.get("distance") in (None, ""):
        raise ValueError("What distance?")
    return store.km_from(args["distance"], args.get("unit"))


def _projection_rows(pace_min_per_km: float) -> list[list[str]]:
    return [[name.title(), store.clock(pace_min_per_km * km)] for name, km in RACES.items()]


def pace(args: dict) -> screen.Shown:
    km, mins = _km(args), store.duration(args.get("time"), args.get("minutes"))
    per_km = mins / km
    rows = [["Distance", store.dist_text(km)], ["Time", store.clock(mins)],
            ["Pace", store.pace_text(km, mins)], ["Speed", store.speed_text(km, mins)]]
    rows += [[f"At this pace: {n}", t] for n, t in _projection_rows(per_km)]
    card = screen.card("table", "Pace and speed", "active-pace", columns=["Measure", "Value"], rows=rows)
    return screen.Shown(f"{store.dist_text(km)} in {store.spoken_time(mins)} is {store.pace_text(km, mins)}, "
                        f"or {store.speed_text(km, mins)}.", card)


def _pace_per_km(args: dict) -> float:
    if args.get("speed_kmh") not in (None, ""):
        return 60 / store.number(args["speed_kmh"], "speed", 0.5, 100)
    if args.get("pace") in (None, ""):
        raise ValueError("What pace or speed? Say a pace like 5:30 per km, or a speed in km/h.")
    value = store.duration(args["pace"])
    per_mile = str(args.get("pace_unit") or "km").lower().startswith("mi")
    return value / store.KM_PER_MILE if per_mile else value


def finish_time(args: dict) -> screen.Shown:
    km, per_km = _km(args), _pace_per_km(args)
    total = km * per_km
    rows = [[f"{store.dist_text(km)}", store.clock(total)]] + _projection_rows(per_km)
    card = screen.card("table", "Finish time", "active-finish", columns=["Distance", "Time at that pace"], rows=rows)
    return screen.Shown(f"{store.dist_text(km)} at {store.clock(per_km)} per km ({store.clock(per_km * store.KM_PER_MILE)} "
                        f"per mile) takes {store.spoken_time(total)}.", card)


def race_predict(args: dict) -> screen.Shown:
    km, mins = _km(args), store.duration(args.get("time"), args.get("minutes"))
    rows = []
    for name, target in RACES.items():
        t = mins * (target / km) ** RIEGEL
        rows.append([name.title(), store.clock(t), store.pace_text(target, t)])
    card = screen.card("table", "Race predictions", "active-predict", columns=["Race", "Predicted time", "Pace"],
                       rows=rows, text="Based on the Riegel formula. Real races depend on training and the course.")
    return screen.Shown(f"From {store.dist_text(km)} in {store.spoken_time(mins)}, you could run a 5k in "
                        f"{rows[0][1]}, a 10k in {rows[1][1]}, a half marathon in {rows[2][1]} and a marathon in "
                        f"{rows[3][1]}. These are estimates.", card)


def splits(args: dict) -> screen.Shown:
    km, mins = _km(args), store.duration(args.get("time"), args.get("minutes"))
    unit_km = store.KM_PER_MILE if str(args.get("per") or "km").lower().startswith("mi") else 1.0
    label = "mile" if unit_km != 1 else "km"
    per = mins / km * unit_km
    rows, at = [], 0.0
    while at < km - 1e-6 and len(rows) < 60:
        step = min(unit_km, km - at)
        at += step
        rows.append([f"{label} {len(rows) + 1}" if step == unit_km else f"last {step:.2f} {label}",
                     store.clock(per * step / unit_km), store.clock(mins * at / km)])
    card = screen.card("table", "Even splits", f"active-splits-{km:.2f}-{mins:.1f}-{label}",
                       columns=[label.title(), "Split", "Total"], rows=rows)
    return screen.Shown(f"To cover {store.dist_text(km)} in {store.spoken_time(mins)} run every {label} in "
                        f"{store.clock(per)}. The splits are on the screen.", card)


def _met(name) -> tuple[str, float]:
    text = store.clean(name).lower().replace("_", " ")
    key = data.MET_ALIASES.get(text, text)
    if key not in data.MET:
        found = [k for k in data.MET if text and text in k]
        if len(found) != 1:
            raise ValueError("Which activity? Ask for the MET table to see the ones I know.")
        key = found[0]
    return key, data.MET[key]


def calories(args: dict) -> screen.Shown:
    key, met = _met(args.get("activity"))
    mins = store.number(args.get("minutes"), "time", 1, 1440)
    kilos = store.number(args.get("weight_kg"), "weight", 20, 400)
    kcal = met * kilos * mins / 60
    rows = sorted(([k.title(), f"{v * kilos * mins / 60:.0f}"] for k, v in data.MET.items()),
                  key=lambda r: -int(r[1]))
    card = screen.card("table", f"{mins:g} minutes at {kilos:g} kg", "active-calories",
                       columns=["Activity", "Calories"], rows=rows,
                       text=f"{key.title()}: about {kcal:.0f} calories. A rough estimate; real burn varies.")
    return screen.Shown(f"{key.title()} for {mins:g} minutes burns about {kcal:.0f} calories at {kilos:g} kilos. "
                        "That's a rough estimate.", card)


def met_table() -> screen.Shown:
    rows = [[k.title(), f"{v:g}"] for k, v in sorted(data.MET.items(), key=lambda kv: kv[1])]
    card = screen.card("table", "Calories: MET values", "active-met", columns=["Activity", "MET"], rows=rows,
                       text="Calories = MET x your weight in kg x hours. Say your weight and time for a number.")
    return screen.Shown("The MET table is on the screen; calories are MET times your kilos times hours.", card)


def one_rep_max(args: dict) -> screen.Shown:
    weight = store.number(args.get("weight_kg"), "weight", 1, 1000)
    reps = store.number(args.get("reps"), "reps", 1, 30)
    epley = weight * (1 + reps / 30) if reps > 1 else weight
    brzycki = weight * 36 / (37 - reps) if reps > 1 else weight
    best = (epley + brzycki) / 2
    rows = [[f"{p}%", f"{best * p / 100:.1f} kg", f"about {r}"] for p, r in PERCENTS]
    card = screen.card("table", "One-rep max", "active-1rm", columns=["Percent", "Weight", "Reps"], rows=rows,
                       text=f"{weight:g} kg for {reps:g} reps is about {best:.1f} kg for one rep.")
    return screen.Shown(f"{weight:g} kilos for {reps:g} reps gives an estimated one-rep max of {best:.1f} kilos. "
                        "Train with a spotter and don't test a real max alone.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "active_calc",
        "description": "Fitness calculators. pace (distance or race with time: pace per km and mile, speed), "
                       "finish_time (distance or race at a pace like 5:30 per km, or speed_kmh), race_predict (a "
                       "result to predicted 5k, 10k, half and marathon times), splits (per km or mile for a target "
                       "time), calories (activity, minutes, weight_kg; MET-based), met_table (calories per hour "
                       "values), one_rep_max (weight_kg and reps, with training percentages). Races: 5k, 10k, half "
                       "marathon, marathon, mile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "race": {"type": "string", "description": "5k, 10k, half marathon, marathon or mile."},
                "distance": {"type": "number"},
                "unit": {"type": "string", "enum": ["km", "miles"]},
                "time": {"type": "string", "description": "hh:mm:ss, mm:ss or '27 minutes'."},
                "minutes": {"type": "number"},
                "pace": {"type": "string", "description": "mm:ss per km (or per mile with pace_unit)."},
                "pace_unit": {"type": "string", "enum": ["km", "mile"]},
                "speed_kmh": {"type": "number"},
                "per": {"type": "string", "enum": ["km", "mile"], "description": "splits: split length."},
                "activity": {"type": "string"},
                "weight_kg": {"type": "number"},
                "reps": {"type": "number"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "met_table":
        return met_table()
    if action not in ACTIONS:
        raise ValueError(f"Unknown action {action}.")
    return {"pace": pace, "finish_time": finish_time, "race_predict": race_predict, "splits": splits,
            "calories": calories, "one_rep_max": one_rep_max}[action](args)
