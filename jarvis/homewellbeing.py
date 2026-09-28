"""Wellbeing logs: medication doses taken, glasses of water, hours slept and mood.

A plain log only, never medical advice. Kept in wellbeing.json in the memory folder, trimmed to the last year.
"""

from datetime import timedelta

import homestore as hs
from config import Settings

FILE = "wellbeing.json"
KEEP_DAYS = 366
MOODS = {1: "awful", 2: "low", 3: "okay", 4: "good", 5: "great"}


def load(settings: Settings) -> dict:
    found = hs.load(settings, FILE, {})
    return {"meds": [m for m in found.get("meds") or [] if isinstance(m, dict)],
            "water": {k: v for k, v in (found.get("water") or {}).items() if isinstance(v, (int, float))},
            "goal": found.get("goal") if isinstance(found.get("goal"), int) else 8,
            "sleep": {k: v for k, v in (found.get("sleep") or {}).items() if isinstance(v, (int, float))},
            "mood": [m for m in found.get("mood") or [] if isinstance(m, dict)]}


def save(settings: Settings, data: dict) -> None:
    cutoff = (hs.today() - timedelta(days=KEEP_DAYS)).isoformat()
    data["meds"] = [m for m in data["meds"] if m.get("at", "") >= cutoff]
    data["mood"] = [m for m in data["mood"] if m.get("date", "") >= cutoff]
    for key in ("water", "sleep"):
        data[key] = {d: v for d, v in data[key].items() if d >= cutoff}
    hs.save(settings, FILE, data)


# Medication

def _clock(at: str) -> str:
    return at[11:16]


def med_taken(settings: Settings, med) -> str:
    med = hs.need(med, "medication", 60)
    data = load(settings)
    at = hs.now().isoformat(timespec="minutes")
    data["meds"].append({"med": med, "at": at})
    save(settings, data)
    count = sum(m["med"].lower() == med.lower() and m["at"][:10] == at[:10] for m in data["meds"])
    return f"Logged {med} at {_clock(at)}. That's {hs.plural(count, 'dose')} of it today."


def _today_doses(data: dict) -> list[dict]:
    day = hs.today().isoformat()
    return [m for m in data["meds"] if m.get("at", "")[:10] == day]


def med_check(settings: Settings, med) -> str:
    med = hs.need(med, "medication", 60)
    doses = [m for m in _today_doses(load(settings)) if med.lower() in m["med"].lower()]
    if not doses:
        return f"No {med} logged today."
    return f"Yes, {doses[0]['med']} logged today at " + ", ".join(_clock(m["at"]) for m in doses) + "."


def med_today(settings: Settings) -> str:
    doses = _today_doses(load(settings))
    if not doses:
        return "No doses logged today."
    return "Today's doses: " + "; ".join(f"{m['med']} at {_clock(m['at'])}" for m in doses) + "."


# Water

def water_add(settings: Settings, glasses=None, goal=None) -> str:
    data = load(settings)
    if goal is not None:
        data["goal"] = int(hs.number(goal, "goal", 1, 30))
    day = hs.today().isoformat()
    if glasses is not None or goal is None:
        data["water"][day] = data["water"].get(day, 0) + int(hs.number(glasses if glasses is not None else 1, "glasses", 1, 20))
    save(settings, data)
    return water_today(settings, data)


def water_today(settings: Settings, data: dict | None = None) -> str:
    data = data or load(settings)
    have, goal = data["water"].get(hs.today().isoformat(), 0), data["goal"]
    left = f"{hs.plural(goal - have, 'glass', 'glasses')} to go" if have < goal else "goal reached"
    return f"{hs.plural(have, 'glass', 'glasses')} of water today out of {goal}; {left}."


# Sleep

def sleep_log(settings: Settings, hours) -> str:
    hours = round(hs.number(hours, "hours slept", 0, 24), 1)
    data = load(settings)
    data["sleep"][hs.today().isoformat()] = hours
    save(settings, data)
    return f"Logged {hs.plural(hours, 'hour')} of sleep last night."


def sleep_week(settings: Settings) -> str:
    data = load(settings)
    today = hs.today()
    nights = [data["sleep"][d] for d in ((today - timedelta(days=i)).isoformat() for i in range(7)) if d in data["sleep"]]
    if not nights:
        return "No sleep logged this past week."
    return (f"Over the last {hs.plural(len(nights), 'night')} logged this week you averaged "
            f"{sum(nights) / len(nights):.1f} hours; shortest {min(nights):g}, longest {max(nights):g}.")


# Mood

def mood_log(settings: Settings, mood, note=None) -> str:
    score = int(hs.number(mood, "mood", 1, 5))
    data = load(settings)
    data["mood"].append({"date": hs.today().isoformat(), "mood": score, "note": hs.clean(note, 200)})
    save(settings, data)
    return f"Logged your mood as {score}, {MOODS[score]}."


def mood_week(settings: Settings) -> str:
    since = (hs.today() - timedelta(days=6)).isoformat()
    week = [m for m in load(settings)["mood"] if m.get("date", "") >= since]
    if not week:
        return "No moods logged this past week."
    avg = sum(m["mood"] for m in week) / len(week)
    lines = [f"- {m['date']}: {m['mood']}" + (f", {m['note']}" if m.get("note") else "") for m in week]
    return f"Mood this week: average {avg:.1f} out of 5 over {hs.plural(len(week), 'entry', 'entries')}.\n" + "\n".join(lines)


def tool_definitions() -> list[dict]:
    return [{
        "name": "home_wellbeing",
        "description": "Personal wellbeing log (a log only; never give medical advice). med_taken logs a dose of "
                       "name taken now; med_check says whether name was taken today; med_today lists today's "
                       "doses. water_add (glasses, default 1; goal sets the daily goal), water_today. sleep_log "
                       "(hours slept last night), sleep_week. mood_log (mood 1 to 5, note), mood_week.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "med_taken", "med_check", "med_today", "water_add", "water_today",
                    "sleep_log", "sleep_week", "mood_log", "mood_week"]},
                "name": {"type": "string", "description": "Medication name."},
                "glasses": {"type": "integer"},
                "goal": {"type": "integer"},
                "hours": {"type": "number"},
                "mood": {"type": "integer", "description": "1 awful to 5 great."},
                "note": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"home_wellbeing"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action = args.get("action")
    if action == "med_taken":
        return med_taken(settings, args.get("name"))
    if action == "med_check":
        return med_check(settings, args.get("name"))
    if action == "med_today":
        return med_today(settings)
    if action == "water_add":
        return water_add(settings, args.get("glasses"), args.get("goal"))
    if action == "water_today":
        return water_today(settings)
    if action == "sleep_log":
        return sleep_log(settings, args.get("hours"))
    if action == "sleep_week":
        return sleep_week(settings)
    if action == "mood_log":
        return mood_log(settings, args.get("mood"), args.get("note"))
    return mood_week(settings)
