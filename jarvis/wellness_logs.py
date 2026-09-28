"""Health logs: weight with a 7-day average, blood pressure and heart rate, a food and calorie diary, caffeine,
a symptom diary, and a weekly summary that also reads sleep and water from the wellbeing log.

Logs only, never medical advice. Saved in health-plus-*.json files in the memory folder.
"""

from datetime import date, datetime, timedelta

import homewellbeing
import screen
import wellness_store as store
from config import Settings

screen.EXTRA_KINDS.add("wellness-trend")

LB_PER_KG = 2.20462
BP_GUIDE = ("NHS guide, for information: ideal is between 90/60 and 120/80; 120/80 up to 140/90 is slightly raised; "
            "140/90 or more is high (135/85 or more for readings taken at home); 90/60 or less is low.")
# Typical caffeine per serving in mg (UK Food Standards Agency and NHS figures, rounded).
DRINKS = {
    "filter coffee": 140, "instant coffee": 100, "espresso": 65, "double espresso": 130, "americano": 130,
    "latte": 130, "cappuccino": 130, "flat white": 130, "mocha": 130, "macchiato": 65, "cold brew": 150,
    "decaf coffee": 3, "tea": 75, "green tea": 30, "decaf tea": 3, "cola": 40, "diet cola": 45,
    "energy drink": 80, "large energy drink": 160, "hot chocolate": 5, "dark chocolate": 25, "milk chocolate": 10,
}
COFFEE_WORDS = ("coffee", "espresso", "americano", "latte", "cappuccino", "flat white", "mocha", "macchiato", "brew")
CAFFEINE_GUIDE = 400
DEFAULT_KCAL = 2000


def _trend(title: str, card_id: str, text: str, labels, series, unit: str, guides=(), buttons=None) -> dict:
    return screen.card("wellness-trend", title, card_id, text=text, buttons=buttons,
                       data={"labels": labels, "series": series, "unit": unit, "guides": list(guides)})


def _stone(kg: float) -> str:
    pounds = round(kg * LB_PER_KG)
    return f"{pounds // 14} st {pounds % 14} lb"


# Weight

def weight_add(settings: Settings, args: dict) -> str:
    if args.get("kg") is not None:
        kg = store.number(args["kg"], "weight", 20, 400)
    elif args.get("stone") is not None or args.get("pounds") is not None:
        lb = store.number(args.get("stone") or 0, "stone", 0, 60) * 14 + store.number(args.get("pounds") or 0, "pounds", 0, 900)
        kg = store.number(lb / LB_PER_KG, "weight", 20, 400)
    else:
        raise ValueError("Give the weight in kg, or in stone and pounds.")
    kg = round(kg, 1)
    when = store.day(args.get("date")).isoformat()
    log = [w for w in store.load(settings, "weight", []) if w.get("date") != when]
    log.append({"date": when, "kg": kg})
    store.save(settings, "weight", sorted(log, key=lambda w: w["date"]))
    avg = _average(log, date.fromisoformat(when))
    return f"Logged {kg:g} kg ({_stone(kg)}). 7-day average {avg:.1f} kg."


def _average(log: list[dict], end: date, days: int = 7) -> float | None:
    start = (end - timedelta(days=days - 1)).isoformat()
    found = [w["kg"] for w in log if start <= w["date"] <= end.isoformat()]
    return sum(found) / len(found) if found else None


def weight_show(settings: Settings):
    log = store.load(settings, "weight", [])[-90:]
    if not log:
        return "No weight logged yet."
    latest = log[-1]
    avgs = [round(_average(log, date.fromisoformat(w["date"])), 1) for w in log]
    now_avg, before = _average(log, store.today()), _average(log, store.today() - timedelta(days=7))
    change = ""
    if now_avg is not None and before is not None:
        diff = now_avg - before
        change = f", {'down' if diff < 0 else 'up'} {abs(diff):.1f} kg on the week before" if abs(diff) >= 0.05 else ", level with the week before"
    avg_text = f"; 7-day average {now_avg:.1f} kg{change}" if now_avg is not None else ""
    said = f"Latest weight {latest['kg']:g} kg ({_stone(latest['kg'])}) on {store.short(date.fromisoformat(latest['date']))}{avg_text}."
    labels = [store.short(date.fromisoformat(w["date"])) for w in log]
    return screen.Shown(said, _trend("Weight", "wellness-weight", said, labels, [
        {"name": "Weight", "values": [w["kg"] for w in log], "style": "dots"},
        {"name": "7-day average", "values": avgs, "style": "line"}], "kg"))


# Blood pressure and heart rate

def bp_band(sys: int, dia: int) -> str:
    if sys >= 140 or dia >= 90:
        return "high"
    if sys >= 120 or dia >= 80:
        return "slightly raised"
    if sys <= 90 or dia <= 60:
        return "low"
    return "ideal"


def bp_add(settings: Settings, args: dict) -> str:
    sys, dia, pulse = args.get("systolic"), args.get("diastolic"), args.get("pulse")
    if (sys is None) != (dia is None):
        raise ValueError("Give both blood pressure numbers, like 120 over 80.")
    if sys is None and pulse is None:
        raise ValueError("Give a blood pressure reading, a heart rate, or both.")
    entry = {"at": store.at_for(args.get("date"))}
    parts = []
    if sys is not None:
        entry["sys"], entry["dia"] = int(store.number(sys, "top number", 50, 260)), int(store.number(dia, "bottom number", 30, 160))
        if entry["dia"] >= entry["sys"]:
            raise ValueError("The top number should be bigger than the bottom one.")
        band = bp_band(entry["sys"], entry["dia"])
        parts.append(f"blood pressure {entry['sys']}/{entry['dia']} (NHS band: {band})")
    if pulse is not None:
        entry["pulse"] = int(store.number(pulse, "heart rate", 25, 250))
        parts.append(f"heart rate {entry['pulse']}")
    log = store.load(settings, "bp", [])
    log.append(entry)
    store.save(settings, "bp", log)
    worry = f" {store.SAFETY}" if "sys" in entry and bp_band(entry["sys"], entry["dia"]) in ("high", "low") else ""
    return "Logged " + " and ".join(parts) + "." + worry


def _when(at: str) -> str:
    return f"{store.short(date.fromisoformat(at[:10]))} {at[11:16]}"


def bp_show(settings: Settings):
    log = store.load(settings, "bp", [])[-60:]
    if not log:
        return "No blood pressure or heart rate readings logged yet."
    rows = [[_when(r["at"]), f"{r['sys']}/{r['dia']}" if "sys" in r else "", str(r.get("pulse", "")),
             bp_band(r["sys"], r["dia"]) if "sys" in r else ""] for r in reversed(log)]
    last = next((r for r in reversed(log) if "sys" in r), None)
    said = (f"Latest blood pressure {last['sys']}/{last['dia']}, {bp_band(last['sys'], last['dia'])} by the NHS bands."
            if last else "Latest heart rate {}.".format(log[-1].get("pulse")))
    return screen.Shown(said, screen.card(
        "table", "Blood pressure", "wellness-bp", text=f"{BP_GUIDE}\n{store.SAFETY}", columns=["When", "BP", "Pulse", "NHS band"],
        rows=rows, buttons=[{"label": "Chart", "say": "Show my blood pressure chart."}]))


def bp_chart(settings: Settings):
    log = store.load(settings, "bp", [])[-60:]
    if not log:
        return "No blood pressure or heart rate readings logged yet."
    labels = [_when(r["at"]) for r in log]
    series = [{"name": "Top (systolic)", "values": [r.get("sys") for r in log], "style": "line"},
              {"name": "Bottom (diastolic)", "values": [r.get("dia") for r in log], "style": "line"},
              {"name": "Heart rate", "values": [r.get("pulse") for r in log], "style": "dots"}]
    series = [s for s in series if any(v is not None for v in s["values"])]
    guides = [{"value": 140, "label": "140 high"}, {"value": 90, "label": "90 high"},
              {"value": 120, "label": "120"}, {"value": 80, "label": "80"}]
    return screen.Shown("Your blood pressure and heart rate chart is on the screen.", _trend(
        "Blood pressure chart", "wellness-bp-chart", BP_GUIDE, labels, series, "",
        guides, [{"label": "Table", "say": "Show my blood pressure readings."}]))


# Food and calories

def _goal(settings: Settings) -> int:
    return int(store.load(settings, "goals", {}).get("kcal") or DEFAULT_KCAL)


def food_goal(settings: Settings, calories) -> str:
    goals = store.load(settings, "goals", {})
    goals["kcal"] = int(store.number(calories, "calorie goal", 800, 6000))
    store.save(settings, "goals", goals)
    return f"Daily calorie goal set to {goals['kcal']:,}."


def food_add(settings: Settings, args: dict) -> str:
    food = store.need(args.get("food"), "food", 80)
    kcal = int(store.number(args.get("calories"), "calories", 0, 5000))
    entry = {"date": store.day(args.get("date")).isoformat(), "time": store.now().strftime("%H:%M"), "food": food,
             "kcal": kcal}
    if args.get("protein") is not None:
        entry["protein"] = round(store.number(args["protein"], "protein", 0, 300), 1)
    log = store.load(settings, "food", [])
    log.append(entry)
    store.save(settings, "food", log)
    total = sum(f["kcal"] for f in log if f["date"] == entry["date"])
    left = _goal(settings) - total
    return (f"Logged {food}, {kcal} calories. {total:,} so far that day; "
            + (f"{left:,} left of your goal." if left >= 0 else f"{-left:,} over your goal."))


def food_today(settings: Settings, when=None):
    d = store.day(when)
    items = [f for f in store.load(settings, "food", []) if f["date"] == d.isoformat()]
    goal = _goal(settings)
    total = sum(f["kcal"] for f in items)
    protein = sum(f.get("protein", 0) for f in items)
    said = f"{total:,} of {goal:,} calories on {store.spoken(d)}" + (f", {protein:g} g protein." if protein else ".")
    rows = [[f["time"], f["food"], str(f["kcal"]), f"{f['protein']:g}" if "protein" in f else ""] for f in items]
    rows.append(["", "Total", f"{total:,} / {goal:,}", f"{protein:g}" if protein else ""])
    return screen.Shown(said, screen.card("table", f"Food {store.short(d)}", "wellness-food", text=said,
                                          columns=["Time", "Food", "kcal", "Protein g"], rows=rows,
                                          buttons=[{"label": "This week", "say": "Show my calories this week."}]))


def food_week(settings: Settings):
    days, log, goal = store.week_days(), store.load(settings, "food", []), _goal(settings)
    totals = [sum(f["kcal"] for f in log if f["date"] == d.isoformat()) for d in days]
    logged = [t for t in totals if t]
    if not logged:
        return "No food logged this past week."
    avg = sum(logged) / len(logged)
    said = f"You averaged {avg:,.0f} calories over {store.plural(len(logged), 'day')} logged this week; goal {goal:,}."
    return screen.Shown(said, screen.card("chart", "Calories this week", "wellness-food-week", text=said, chart={
        "type": "bar", "labels": [d.strftime("%a") for d in days], "values": totals, "unit": ""}))


# Caffeine

def _drink(name: str) -> str | None:
    name = store.clean(name).lower().rstrip("s")
    if name in ("coffee", "mug of coffee", "cup of coffee"):
        return "instant coffee"
    return next((k for k in DRINKS if k == name), None) or next((k for k in DRINKS if name and name in k), None) \
        or next((k for k in sorted(DRINKS, key=len, reverse=True) if k in name), None)


def caffeine_add(settings: Settings, args: dict) -> str:
    drink = store.need(args.get("drink"), "drink", 60)
    count = int(store.number(args.get("count") or 1, "number of drinks", 1, 10))
    if args.get("mg") is not None:
        each = int(store.number(args["mg"], "caffeine", 0, 1000))
    else:
        known = _drink(drink)
        if not known:
            raise ValueError(f"I don't know the caffeine in {drink}; give the mg, or pick one of: {', '.join(DRINKS)}.")
        drink, each = known, DRINKS[known]
    log = store.load(settings, "caffeine", [])
    at = store.stamp(store.now())
    log += [{"at": at, "drink": drink, "mg": each}] * count
    store.save(settings, "caffeine", log)
    total = sum(c["mg"] for c in log if c["at"][:10] == at[:10])
    return f"Logged {count} {drink}, about {each * count} mg. {total} mg of caffeine today."


def caffeine_today(settings: Settings):
    log = store.load(settings, "caffeine", [])
    day = store.today().isoformat()
    items = [c for c in log if c["at"][:10] == day]
    total = sum(c["mg"] for c in items)
    coffee = next((c for c in reversed(log) if any(w in c["drink"] for w in COFFEE_WORDS) and c["mg"] > 10), None)
    last = ""
    if coffee:
        ago = (store.now() - datetime.fromisoformat(coffee["at"])).total_seconds() / 3600
        when = coffee["at"][11:16] if coffee["at"][:10] == day else _when(coffee["at"])
        last = f" Last coffee at {when}, {ago:.1f} hours ago."
    said = f"{total} mg of caffeine today.{last}"
    text = said + f" Adults are commonly advised to stay under about {CAFFEINE_GUIDE} mg a day."
    rows = [[c["at"][11:16], c["drink"], str(c["mg"])] for c in items] + [["", "Total", str(total)]]
    return screen.Shown(said, screen.card("table", "Caffeine today", "wellness-caffeine", text=text,
                                          columns=["Time", "Drink", "mg"], rows=rows,
                                          buttons=[{"label": "Drinks list", "say": "Show the caffeine in common drinks."}]))


def caffeine_drinks() -> screen.Shown:
    rows = [[k, str(v)] for k, v in sorted(DRINKS.items(), key=lambda kv: -kv[1])]
    return screen.Shown("The caffeine table is on the screen.", screen.card(
        "table", "Caffeine in drinks", "wellness-drinks", text="Typical amounts per mug, can or serving; brands vary.",
        columns=["Drink", "mg"], rows=rows))


# Symptoms

def symptom_add(settings: Settings, args: dict) -> str:
    symptom = store.need(args.get("symptom"), "symptom", 80)
    severity = int(store.number(args.get("severity"), "severity", 1, 10))
    log = store.load(settings, "symptoms", [])
    log.append({"at": store.at_for(args.get("date")), "symptom": symptom, "severity": severity,
                "notes": store.clean(args.get("notes"), 300)})
    store.save(settings, "symptoms", log)
    return f"Logged {symptom}, severity {severity} out of 10. {store.SAFETY}"


def symptom_history(settings: Settings, symptom=None):
    log = store.load(settings, "symptoms", [])
    if symptom:
        log = store.find(log, "symptom", symptom)
    if not log:
        return "No symptoms logged" + (f" for {symptom}." if symptom else " yet.")
    rows = [[_when(s["at"]), s["symptom"], str(s["severity"]), s.get("notes", "")] for s in reversed(log[-100:])]
    said = f"{store.plural(len(log), 'entry', 'entries')} in the symptom diary; the latest is {log[-1]['symptom']}."
    return screen.Shown(said, screen.card("table", "Symptom diary", "wellness-symptoms", text=store.SAFETY,
                                          columns=["When", "Symptom", "Severity", "Notes"], rows=rows))


# Weekly summary

def _avg(values) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _fmt(value, pattern: str) -> str:
    return pattern.format(value) if value is not None else "-"


def _week(settings: Settings, end: date) -> list[str]:
    days = {d.isoformat() for d in store.week_days(end)}
    within = lambda items, key: [i for i in items if i.get(key, "")[:10] in days]  # noqa: E731
    weights = within(store.load(settings, "weight", []), "date")
    bp = within(store.load(settings, "bp", []), "at")
    food = within(store.load(settings, "food", []), "date")
    runs = within(store.load(settings, "runs", []), "date")
    caffeine = within(store.load(settings, "caffeine", []), "at")
    well = homewellbeing.load(settings)
    sys, dia = _avg(r.get("sys") for r in bp), _avg(r.get("dia") for r in bp)
    kcal = [sum(f["kcal"] for f in food if f["date"] == d) for d in days]
    return [
        _fmt(_avg(w["kg"] for w in weights), "{:.1f} kg"),
        f"{sys:.0f}/{dia:.0f}" if sys and dia else "-",
        _fmt(_avg(r.get("pulse") for r in bp), "{:.0f} bpm"),
        _fmt(_avg(k for k in kcal if k), "{:,.0f} a day"),
        f"{len(runs)} runs, {sum(r['km'] for r in runs):.1f} km" if runs else "-",
        _fmt(_avg(well["sleep"].get(d) for d in days), "{:.1f} h a night"),
        _fmt(_avg(well["water"].get(d) for d in days), "{:.1f} glasses a day"),
        _fmt(sum(c["mg"] for c in caffeine) / 7 if caffeine else None, "{:.0f} mg a day"),
    ]


def week_summary(settings: Settings):
    this, last = _week(settings, store.today()), _week(settings, store.today() - timedelta(days=7))
    names = ["Weight (average)", "Blood pressure", "Heart rate", "Calories", "Running", "Sleep", "Water", "Caffeine"]
    if all(v == "-" for v in this):
        return "Nothing logged this past week yet."
    said = "This week: " + "; ".join(f"{n.split(' (')[0].lower()} {v}" for n, v in zip(names, this) if v != "-") + "."
    return screen.Shown(said, screen.card("table", "Health this week", "wellness-week", text=store.SAFETY,
                                          columns=["", "Last 7 days", "Week before"],
                                          rows=[[n, a, b] for n, a, b in zip(names, this, last)]))


# Undo

LOGS = {"weight": "weight", "blood_pressure": "bp", "food": "food", "caffeine": "caffeine", "symptom": "symptoms"}


def undo(settings: Settings, which, confirmed: bool) -> str:
    section = LOGS.get(which or "")
    if not section:
        raise ValueError(f"Which log? One of: {', '.join(LOGS)}.")
    log = store.load(settings, section, [])
    if not log:
        return "That log is empty."
    last = log[-1]
    what = ", ".join(f"{k} {v}" for k, v in last.items() if v not in ("", None))
    if not confirmed:
        return f"The last {which.replace('_', ' ')} entry is: {what}. Ask the user to confirm removing it, then call again with confirmed true."
    store.save(settings, section, log[:-1])
    return f"Removed the last {which.replace('_', ' ')} entry ({what})."


def tool_definitions() -> list[dict]:
    return [{
        "name": "health_log",
        "description": "Health diary, a log only (never give medical advice; if something sounds worrying suggest "
                       "the GP or NHS 111). Pops up charts and tables. weight_add (kg, or stone and pounds), "
                       "weight_show (chart with 7-day average trend). bp_add (blood pressure systolic/diastolic "
                       "and/or pulse heart rate), bp_show (table with NHS bands), bp_chart. food_add (food, "
                       "calories, protein grams), food_today (calorie diary vs goal), food_week (weekly calorie "
                       "chart), food_goal (calories). caffeine_add (drink e.g. latte, tea, energy drink; count; mg "
                       "if unusual), caffeine_today (total mg and last coffee time), caffeine_drinks. symptom_add "
                       "(symptom, severity 1-10, notes), symptom_history. week_summary (weekly health summary of "
                       "weight, blood pressure, calories, runs, sleep, water). undo removes the last entry of "
                       "a log; set confirmed true only after the user confirms.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "weight_add", "weight_show", "bp_add", "bp_show", "bp_chart", "food_add", "food_today",
                    "food_week", "food_goal", "caffeine_add", "caffeine_today", "caffeine_drinks", "symptom_add",
                    "symptom_history", "week_summary", "undo"]},
                "kg": {"type": "number"},
                "stone": {"type": "number"},
                "pounds": {"type": "number"},
                "systolic": {"type": "integer", "description": "Top blood pressure number."},
                "diastolic": {"type": "integer", "description": "Bottom blood pressure number."},
                "pulse": {"type": "integer", "description": "Heart rate, beats per minute."},
                "food": {"type": "string"},
                "calories": {"type": "integer"},
                "protein": {"type": "number", "description": "Grams, optional."},
                "drink": {"type": "string"},
                "count": {"type": "integer"},
                "mg": {"type": "integer"},
                "symptom": {"type": "string"},
                "severity": {"type": "integer", "description": "1 mild to 10 worst."},
                "notes": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD, yesterday or a weekday; default today."},
                "log": {"type": "string", "enum": list(LOGS)},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"health_log"}


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    simple = {"weight_show": weight_show, "bp_show": bp_show, "bp_chart": bp_chart, "food_week": food_week,
              "caffeine_today": caffeine_today, "week_summary": week_summary}
    if action in simple:
        return simple[action](settings)
    adders = {"weight_add": weight_add, "bp_add": bp_add, "food_add": food_add, "caffeine_add": caffeine_add,
              "symptom_add": symptom_add}
    if action in adders:
        return adders[action](settings, args)
    if action == "food_today":
        return food_today(settings, args.get("date"))
    if action == "food_goal":
        return food_goal(settings, args.get("calories"))
    if action == "caffeine_drinks":
        return caffeine_drinks()
    if action == "symptom_history":
        return symptom_history(settings, args.get("symptom"))
    if action == "undo":
        return undo(settings, args.get("log"), bool(args.get("confirmed")))
    raise ValueError(f"Unknown action {action}.")
