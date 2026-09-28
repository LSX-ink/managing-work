"""Reflection: "today I learned" notes, a wins journal, a decision journal to revisit after 30 days, and a
weekly review that gathers the week's goals, workouts, books, lessons and priorities for Alfred to summarise.

Kept in growth-til.json, growth-wins.json and growth-decisions.json in the memory folder.
"""

from datetime import date, timedelta

import growth_goals
import growth_store as store
import growth_study
from config import Settings

MAX_ENTRIES = 5000
REVISIT_DAYS = 30


def _append(settings: Settings, name: str, entry: dict) -> list[dict]:
    entries = store.load(settings, name, [])
    entries.append(entry)
    store.save(settings, name, entries[-MAX_ENTRIES:])
    return entries


def til_add(settings: Settings, text: str, today: date) -> str:
    entries = _append(settings, "til", {"date": today.isoformat(), "text": store.need(text, "lesson", 300)})
    week = sum(store.this_week(e["date"], today) for e in entries)
    return f"Noted. {store.plural(week, 'thing')} learned this week."


def _til_week(settings: Settings, today: date) -> list[dict]:
    return [e for e in store.load(settings, "til", []) if store.this_week(e["date"], today)]


def til_week(settings: Settings, today: date) -> str:
    week = _til_week(settings, today)
    if not week:
        return "Nothing logged as learned this week."
    return f"This week you learned ({len(week)}):\n" + "\n".join(
        f"- {date.fromisoformat(e['date']):%A}: {e['text']}" for e in week)


def win_log(settings: Settings, text: str, today: date) -> str:
    entries = _append(settings, "wins", {"date": today.isoformat(), "text": store.need(text, "win", 300)})
    month = sum(e["date"][:7] == today.isoformat()[:7] for e in entries)
    return f"Win logged. That's {store.plural(month, 'win')} this month."


def wins_month(settings: Settings, today: date) -> str:
    month = [e for e in store.load(settings, "wins", []) if e["date"][:7] == today.isoformat()[:7]]
    if not month:
        return f"No wins logged yet in {today:%B}."
    return f"Your wins in {today:%B} ({len(month)}):\n" + "\n".join(
        f"- {date.fromisoformat(e['date']):%d %b}: {e['text']}" for e in month)


def decision_log(settings: Settings, decision: str, expected: str, today: date) -> str:
    _append(settings, "decisions", {"date": today.isoformat(), "decision": store.need(decision, "decision", 300),
                                    "expected": store.clean(expected, 300), "outcome": None})
    return f"Decision recorded. I'll bring it up for review after {REVISIT_DAYS} days."


def decisions_revisit(settings: Settings, today: date) -> str:
    cutoff = (today - timedelta(days=REVISIT_DAYS)).isoformat()
    due = [d for d in store.load(settings, "decisions", []) if d["date"] <= cutoff and not d.get("outcome")]
    if not due:
        return f"No decisions older than {REVISIT_DAYS} days waiting for review."
    return f"Decisions to look back on ({len(due)}):\n" + "\n".join(
        f"- {d['date']}: {d['decision']}" + (f" (expected: {d['expected']})" if d["expected"] else "") for d in due)


def decision_outcome(settings: Settings, decision: str, outcome: str, today: date) -> str:
    entries = store.load(settings, "decisions", [])
    entry = store.find([d for d in entries if not d.get("outcome")], "decision", decision)
    if entry is None:
        return "I couldn't find that decision."
    entry["outcome"] = f"{today.isoformat()}: {store.need(outcome, 'outcome', 300)}"
    store.save(settings, "decisions", entries)
    return "Outcome noted against that decision."


def weekly_review(settings: Settings, today: date) -> str:
    start = store.week_start(today)
    parts = [f"Weekly review, {start:%d %b} to {today:%d %b}."]
    goals = [g for g in store.load(settings, "goals", []) if not g.get("achieved") or store.this_week(g["achieved"], today)]
    goal_lines = []
    for g in goals:
        gained = sum(e["amount"] for e in g.get("log", []) if store.this_week(e["date"], today))
        state = "achieved this week" if g.get("achieved") else growth_goals.progress_text(g)
        goal_lines.append(f"- {g['name']}: {state}" + (f", +{gained:g} this week" if gained else ""))
    parts.append("Goals:\n" + "\n".join(goal_lines) if goal_lines else "Goals: none set.")
    parts.append(growth_goals.workout_week(settings, today))
    parts.append(growth_goals.steps_week(settings, today))
    books = [b for b in store.load(settings, "books", []) if b.get("finished") and store.this_week(b["finished"], today)]
    parts.append("Books finished: " + ("; ".join(b["title"] for b in books) if books else "none") + ".")
    parts.append(til_week(settings, today))
    parts.append(growth_study.study_week(settings, today))
    days = {d: v for d, v in store.load(settings, "priorities", {}).items() if store.this_week(d, today)}
    set_count, done = sum(len(v) for v in days.values()), [i["text"] for v in days.values() for i in v if i["done"]]
    parts.append(f"Priorities: {len(done)} of {set_count} done" + (f" ({'; '.join(done)})." if done else "."))
    wins = [e["text"] for e in store.load(settings, "wins", []) if store.this_week(e["date"], today)]
    parts.append("Wins: " + ("; ".join(wins) if wins else "none logged") + ".")
    return "\n\n".join(parts)


ACTIONS = ["til_add", "til_week", "win_log", "wins_month", "decision_log", "decisions_revisit",
           "decision_outcome", "weekly_review"]


def tool_definitions() -> list[dict]:
    return [{
        "name": "reflect",
        "description": "Journals and reviews. til_add ('today I learned', text), til_week recap. win_log (text), "
                       "wins_month. decision_log (text, expected outcome), decisions_revisit lists ones over 30 days "
                       "old, decision_outcome (text names the decision, outcome). weekly_review gathers this week's "
                       "goals, workouts, steps, books, lessons, study, priorities and wins: summarise it briefly.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {"type": "string", "description": "The lesson, win or decision."},
                "expected": {"type": "string", "description": "What they expect the decision to lead to."},
                "outcome": {"type": "string", "description": "How the decision actually turned out."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"reflect"}


def run_tool(name: str, args: dict, settings: Settings, http=None) -> str:
    action, today, text = args.get("action"), store.today(), args.get("text") or ""
    if action == "til_add":
        return til_add(settings, text, today)
    if action == "til_week":
        return til_week(settings, today)
    if action == "win_log":
        return win_log(settings, text, today)
    if action == "wins_month":
        return wins_month(settings, today)
    if action == "decision_log":
        return decision_log(settings, text, args.get("expected") or "", today)
    if action == "decisions_revisit":
        return decisions_revisit(settings, today)
    if action == "decision_outcome":
        return decision_outcome(settings, text, args.get("outcome") or "", today)
    if action == "weekly_review":
        return weekly_review(settings, today)
    raise ValueError(f"Unknown reflect action: {action}")
