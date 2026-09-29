"""Mindful minutes: log breathing, meditation and quiet time, keep a daily goal and a streak, and see a chart.

Saved on this PC in calm-minutes.json (a list of {date, minutes, kind}) and calm-settings.json (the daily goal).
"""

from datetime import timedelta

import calm_store as store
import screen
from config import Settings

NAMES = {"calm_log"}
ACTIONS = ["log", "today", "streak", "summary", "history", "goal_set", "undo"]
KINDS = ["breathing", "meditation", "walk", "yoga", "quiet time", "other"]
DEFAULT_GOAL = 5


def _rows(settings: Settings) -> list[dict]:
    return store.load(settings, "minutes", [])


def _goal(settings: Settings) -> int:
    return int(store.load(settings, "settings", {}).get("minutes_goal") or DEFAULT_GOAL)


def _by_day(rows: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for r in rows:
        totals[r["date"]] = totals.get(r["date"], 0) + r["minutes"]
    return totals


def _streak(totals: dict[str, float]) -> int:
    day = store.today()
    if totals.get(day.isoformat(), 0) <= 0:
        day -= timedelta(days=1)
    count = 0
    while totals.get(day.isoformat(), 0) > 0:
        count += 1
        day -= timedelta(days=1)
    return count


def _fmt(n: float) -> str:
    return f"{n:g}"


def log(settings: Settings, args: dict) -> str:
    mins = store.minutes(args.get("minutes"), high=600)
    kind = store.clean(args.get("kind")).lower()
    kind = kind if kind in KINDS else ("meditation" if "med" in kind else "other" if kind else "meditation")
    when = store.day(args.get("date"))
    rows = _rows(settings)
    rows.append({"date": when.isoformat(), "minutes": mins, "kind": kind})
    store.save(settings, "minutes", rows[-3000:])
    totals = _by_day(rows)
    today = totals.get(store.today().isoformat(), 0)
    goal = _goal(settings)
    met = f" That's your {goal} minute goal done." if today >= goal > today - mins else ""
    return (f"Logged {_fmt(mins)} minutes of {kind}. {_fmt(today)} mindful minutes today, "
            f"{store.plural(_streak(totals), 'day')} in a row.{met}")


def today_view(settings: Settings) -> str:
    totals = _by_day(_rows(settings))
    got, goal = totals.get(store.today().isoformat(), 0), _goal(settings)
    return f"{_fmt(got)} mindful minutes today, against a goal of {goal}." + (" Goal met." if got >= goal else "")


def streak(settings: Settings) -> str | screen.Shown:
    totals = _by_day(_rows(settings))
    if not totals:
        return "No mindful minutes logged yet. Try a few minutes of breathing."
    days = [store.today() - timedelta(days=i) for i in range(13, -1, -1)]
    chart = {"type": "bar", "labels": [d.strftime("%d %b") for d in days],
             "values": [totals.get(d.isoformat(), 0) for d in days], "unit": "min"}
    run = _streak(totals)
    card = screen.card("chart", "Mindful minutes", "calm-minutes", chart=chart,
                       text=f"{store.plural(run, 'day')} in a row. Daily goal {_goal(settings)} minutes.")
    return screen.Shown(f"{store.plural(run, 'day')} in a row, {_fmt(sum(chart['values']))} minutes in the last "
                        "two weeks.", card)


def summary(settings: Settings, span) -> str:
    days = 30 if "month" in store.clean(span).lower() else 7
    start = store.today() - timedelta(days=days - 1)
    rows = [r for r in _rows(settings) if r["date"] >= start.isoformat()]
    if not rows:
        return f"No mindful minutes in the last {days} days."
    total = sum(r["minutes"] for r in rows)
    kinds: dict[str, float] = {}
    for r in rows:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + r["minutes"]
    top = max(kinds, key=kinds.get)
    active = len({r["date"] for r in rows})
    return (f"In the last {days} days: {_fmt(total)} minutes on {active} days, mostly {top}. "
            f"That's about {total / days:.1f} minutes a day.")


def history(settings: Settings) -> str | screen.Shown:
    rows = _rows(settings)[-15:][::-1]
    if not rows:
        return "Nothing logged yet."
    card = screen.card("table", "Recent mindful minutes", "calm-history", columns=["Date", "Minutes", "What"],
                       rows=[[r["date"], _fmt(r["minutes"]), r["kind"]] for r in rows])
    return screen.Shown(f"Your last {store.plural(len(rows), 'session')} are on the screen.", card)


def goal_set(settings: Settings, minutes) -> str:
    goal = int(store.minutes(minutes, "daily goal", 1, 600))
    prefs = store.load(settings, "settings", {})
    prefs["minutes_goal"] = goal
    store.save(settings, "settings", prefs)
    return f"Your daily goal is {goal} mindful minutes."


def undo(settings: Settings, confirmed: bool) -> str:
    rows = _rows(settings)
    if not rows:
        return "There's nothing to undo."
    last = rows[-1]
    if not confirmed:
        return (f"That would remove {_fmt(last['minutes'])} minutes of {last['kind']} on {last['date']}. "
                "Ask the user to confirm, then call again with confirmed true.")
    store.save(settings, "minutes", rows[:-1])
    return f"Removed {_fmt(last['minutes'])} minutes of {last['kind']}."


def tool_definitions() -> list[dict]:
    return [{
        "name": "calm_log",
        "description": "Mindful minutes log. log (minutes, kind breathing, meditation, walk, yoga, quiet time; date "
                       "optional; 'I meditated 10 minutes'), today (against the goal), streak (bar chart and days in a "
                       "row), summary (week, or span 'month'), history (recent sessions), goal_set (daily minutes), "
                       "undo (removes the last entry; confirmed true only after the user confirms).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "minutes": {"type": "number"},
                "kind": {"type": "string", "enum": KINDS},
                "date": {"type": "string", "description": "YYYY-MM-DD, today or yesterday."},
                "span": {"type": "string", "description": "week or month."},
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
    if action == "today":
        return today_view(settings)
    if action == "streak":
        return streak(settings)
    if action == "summary":
        return summary(settings, args.get("span"))
    if action == "history":
        return history(settings)
    if action == "goal_set":
        return goal_set(settings, args.get("minutes"))
    if action == "undo":
        return undo(settings, bool(args.get("confirmed")))
    raise ValueError(f"Unknown action {action}.")
