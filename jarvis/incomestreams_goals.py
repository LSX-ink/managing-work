"""Income streams part 3: extra-income goals (for example 500 pounds a month) with progress, pace and history.

Goals are targets the user picks, monthly, for the calendar year or for the UK tax year, for all streams or one.
Progress is money in that was logged; a goal is a plan, not a promise, and missing one is fine.
"""

import calendar

import homestore as hs
import incomestreams_store as st
import screen
from config import Settings

NAMES = {"income_goals"}
ACTIONS = ["goal_set", "goal_show", "goal_pace", "goal_history", "goal_remove", "log_nudge"]
PERIODS = ["monthly", "yearly", "tax_year"]


def _goal(data: dict, name) -> dict:
    if not data["goals"]:
        raise ValueError("You haven't set an income goal yet, for example: my goal is 500 pounds a month extra.")
    if not hs.clean(name):
        return data["goals"][0]
    names = {g["name"]: g for g in data["goals"]}
    found = hs.find(names, name)
    if found is None:
        raise ValueError(f"I can't find a goal called {hs.clean(name)}.")
    return names[found]


def _rows(settings: Settings, data: dict, goal: dict) -> list[dict]:
    rows = st.entries(settings, data)
    return [e for e in rows if goal.get("stream") is None or e["stream"] == goal["stream"]]


def _progress(rows: list, goal: dict) -> float:
    today = hs.today()
    if goal["period"] == "monthly":
        return st.total(rows, months={st.month_of(today)})
    if goal["period"] == "yearly":
        return st.total(rows, since=f"{today.year}-01-01", until=f"{today.year}-12-31")
    a, b = st.tax_range(st.tax_start(today))
    return st.total(rows, since=a.isoformat(), until=b.isoformat())


def _scope(data: dict, goal: dict) -> str:
    return st.name_of(data, goal["stream"]) if goal.get("stream") else "all streams"


def goal_set(settings: Settings, args: dict):
    data = st.load(settings)
    name = hs.clean(args.get("name") or "Extra income", 60)
    period = hs.clean(args.get("period") or "monthly").lower().replace(" ", "_")
    if period not in PERIODS:
        raise ValueError("The period is monthly, yearly or tax_year.")
    goal = next((g for g in data["goals"] if g["name"].lower() == name.lower()), None)
    if goal is None:
        goal = {"id": st.new_id(data), "name": name}
        st.put(data["goals"], goal)
    goal.update({"target": st.money(args.get("target"), "target"), "period": period,
                 "stream": st.stream(data, args["stream"])["id"] if args.get("stream") else None})
    st.save(settings, data)
    return show_goals(settings, {}, f"Goal set: {st.gbp(goal['target'])} {period.replace('_', ' ')} from {_scope(data, goal)}. ")


def show_goals(settings: Settings, args: dict, lead: str = ""):
    data = st.load(settings)
    _goal(data, "")
    bars = []
    for g in data["goals"]:
        got = _progress(_rows(settings, data, g), g)
        bars.append({"label": f"{g['name']} ({g['period'].replace('_', ' ')}, {_scope(data, g)})", "value": min(got, g["target"]),
                     "max": g["target"], "text": f"{st.gbp(got)} of {st.gbp(g['target'])}",
                     "say": f"How is my {g['name']} goal going?"})
    first = bars[0]
    return screen.Shown(f"{lead}{first['label'].split(' (')[0]}: {first['text']}. A goal is a plan, not a promise.",
                        st.bars_card("Income goals", "incomestreams-goals", bars, "Progress uses money you logged.",
                                     [{"label": "Pace", "say": "How much more do I need this month for my goal?"},
                                      {"label": "Dashboard", "say": "Show my income dashboard."}]))


def goal_show(settings: Settings, args: dict):
    return show_goals(settings, args)


def goal_pace(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    goal = _goal(data, args.get("name"))
    today = hs.today()
    got = _progress(_rows(settings, data, goal), goal)
    left = max(0.0, goal["target"] - got)
    if goal["period"] == "monthly":
        end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    elif goal["period"] == "yearly":
        end = today.replace(month=12, day=31)
    else:
        end = st.tax_range(st.tax_start(today))[1]
    days = (end - today).days + 1
    rows = [["Target", st.gbp(goal["target"])], ["So far", st.gbp(got)], ["Still to go", st.gbp(left)],
            ["Days left", str(days)], ["Per day to hit it", st.gbp(left / days) if left else "done"]]
    said = (f"You've reached your {goal['name']} goal with {st.gbp(got)}." if not left else
            f"{st.gbp(left)} to go with {days} days left, about {st.gbp(left / days)} a day. That's a target, not a promise, "
            "and it's fine to miss.")
    return screen.Shown(said, screen.card("table", f"Pace: {goal['name']}", f"incomestreams-pace-{goal['id']}",
                                          columns=["", ""], rows=rows))


def goal_history(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    goal = _goal(data, args.get("name"))
    if goal["period"] != "monthly":
        raise ValueError("History works for monthly goals. Set a monthly goal to see this.")
    rows = _rows(settings, data, goal)
    months = st.months_back(int(hs.number(args.get("months") or 6, "number of months", 1, 24)))
    bars = [{"label": st.month_label(m), "value": min(st.total(rows, months={m}), goal["target"]), "max": goal["target"],
             "text": st.gbp(st.total(rows, months={m})) + (" hit" if st.total(rows, months={m}) >= goal["target"] else "")}
            for m in months]
    hit = sum(1 for m in months if st.total(rows, months={m}) >= goal["target"])
    return screen.Shown(f"You reached {st.gbp(goal['target'])} in {hit} of the last {len(months)} months.",
                        st.bars_card(f"History: {goal['name']}", "incomestreams-goalhistory", bars))


def goal_remove(settings: Settings, args: dict) -> str:
    data = st.load(settings)
    goal = _goal(data, args.get("name"))
    if not args.get("confirmed"):
        return st.confirm_needed(f"the goal {goal['name']}")
    data["goals"].remove(goal)
    st.save(settings, data)
    return f"Removed the goal {goal['name']}."


def log_nudge(settings: Settings, args: dict) -> screen.Shown:
    data = st.load(settings)
    st.need_streams(data)
    this = st.month_of(hs.today())
    rows = st.entries(settings, data)
    items = [{"label": f"{s['name']}: nothing logged yet in {st.month_label(this)}",
              "say": f"I earned some money from {s['name']} this month."}
             for s in data["streams"] if s["status"] == "active" and not st.total(rows, s["id"], {this})]
    if not items:
        return screen.Shown("Every active stream has something logged this month.",
                            screen.card("list", "Log this month", "incomestreams-nudge", items=["All logged."]))
    return screen.Shown(f"{hs.plural(len(items), 'stream')} with nothing logged this month. Tap one to add it.",
                        screen.card("list", "Log this month", "incomestreams-nudge", items=items))


def tool_definitions() -> list[dict]:
    return [{
        "name": "income_goals",
        "description": "Goals for the user's extra income (for example 500 pounds a month) with progress, pace and history; a "
                       "goal is a plan, never a promise. action: goal_set (name, target pounds, period monthly|yearly|tax_year, "
                       "stream to limit to one) / goal_show / goal_pace (name) = how much per day is needed / goal_history "
                       "(name, months) for monthly goals / goal_remove (name, confirmed only after yes) / log_nudge = streams "
                       "with nothing logged this month.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string"},
                "target": {"type": "number"},
                "period": {"type": "string", "enum": PERIODS},
                "stream": {"type": "string"},
                "months": {"type": "integer"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    found = {"goal_set": goal_set, "goal_show": goal_show, "goal_pace": goal_pace, "goal_history": goal_history,
             "goal_remove": goal_remove, "log_nudge": log_nudge}.get(args.get("action"))
    if found is None:
        raise ValueError("I can't do that one.")
    return found(settings, args)
