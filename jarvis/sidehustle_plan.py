"""Run a side hustle: a 30-day launch plan per hustle with a tick-off checklist, a monthly extra-income goal, the monthly
"stop or keep going" review, and a simple customer and order log (see sidehustle_orders.py).

Plans pop up as "sidehustle-plan", goals as "sidehustle-goal" and reviews as "sidehustle-review"
(frontend/popup-sidehustle.js). The review is a set of prompts from your own logged numbers, not advice; the decision is
yours. Nothing is a promise of income. Data: sidehustle-hustles.json, sidehustle-reviews.json, sidehustle-profile.json.
"""

import calendar
from datetime import date, timedelta

import screen
import sidehustle_data as data
import sidehustle_orders as orders
import sidehustle_store as st
from config import Settings

NAMES = {"sidehustle_plan"}
ACTIONS = ["start_hustle", "launch_plan", "tick_task", "add_task", "next_tasks", "hustles", "set_status", "remove_hustle",
           "goal_set", "goal_progress", "monthly_review", "review_history", "order_add", "orders", "order_update", "customers",
           "customer_note", "order_remove"]
STATUS = ["active", "paused", "stopped"]
DECISIONS = ["keep going", "change something", "pause", "stop"]
QUESTIONS = ["Do I still enjoy it?", "Is the hourly rate acceptable to me?", "What one change would raise income or cut time?",
             "What would make me stop?"]


def _save(settings: Settings, rows: list[dict]) -> None:
    st.save(settings, st.HUSTLES, rows)


def _build_tasks(category: str) -> list[dict]:
    steps = sorted(data.PLAN_COMMON + data.PLAN_BY_CATEGORY.get(category, []), key=lambda t: t[0])
    return [{"id": n, "day": day, "text": text, "done": False} for n, (day, text) in enumerate(steps, 1)]


def start_hustle(settings: Settings, args: dict) -> screen.Shown:
    typed = st.need(args.get("name") or args.get("hustle"), "side hustle", 60)
    idea = data.idea(typed)
    name = idea["name"] if idea else typed
    rows = st.hustles(settings)
    if any(h["name"].lower() == name.lower() for h in rows):
        raise ValueError(f"You already have {name}. Ask to see its plan.")
    if len(rows) >= 20:
        raise ValueError("That's a lot of hustles; remove one first.")
    started = st.parse_date(args.get("date"), "start date") or st.today()
    category = idea["category"] if idea else "custom"
    rows.append({"name": name, "category": category, "status": "active", "started": started.isoformat(),
                 "tasks": _build_tasks(category)})
    _save(settings, rows)
    return launch_plan(settings, {"hustle": name}, f"Started {name} with a 30-day plan. ")


def _day_of(h: dict) -> int:
    return (st.today() - date.fromisoformat(h["started"])).days + 1


def _week_title(day: int) -> str:
    return f"Week {(day - 1) // 7 + 1}" if day <= 28 else "Final days (29 to 30)"


def launch_plan(settings: Settings, args: dict, prefix: str = "") -> screen.Shown:
    h = st.pick_hustle(settings, args.get("hustle") or args.get("name"))
    started = date.fromisoformat(h["started"])
    tasks = sorted(h["tasks"], key=lambda t: (t["day"], t["id"]))
    weeks: dict[str, list] = {}
    for t in tasks:
        due = started + timedelta(days=t["day"] - 1)
        weeks.setdefault(_week_title(t["day"]), []).append({
            "id": t["id"], "text": t["text"], "done": t["done"], "due": st.short(due),
            "late": (not t["done"]) and due < st.today(),
            "say": f"{'Untick' if t['done'] else 'Tick off'} task {t['id']} on my {h['name']} launch plan."})
    done = sum(1 for t in tasks if t["done"])
    day = _day_of(h)
    text = f"{prefix}{h['name']}: {done} of {len(tasks)} steps done, day {max(day, 1)} of your 30-day plan."
    return screen.Shown(text, screen.card(st.PLAN, f"{h['name']}: 30-day launch plan", "", data={
        "name": h["name"], "done": done, "total": len(tasks), "day": max(day, 1), "status": h["status"],
        "weeks": [{"title": k, "tasks": v} for k, v in weeks.items()],
        "note": "Plans are general starting steps, not advice. " + st.TAX_NOTE},
        buttons=[{"label": "What's next", "say": "What are my next side hustle tasks?"}]))


def _task(h: dict, args: dict) -> dict:
    if args.get("task_id") is not None:
        hit = next((t for t in h["tasks"] if t["id"] == int(args["task_id"])), None)
    else:
        word = st.need(args.get("task"), "task").lower()
        hits = [t for t in h["tasks"] if word in t["text"].lower()]
        if len(hits) > 1:
            raise ValueError(f"{len(hits)} steps match; give the step number.")
        hit = hits[0] if hits else None
    if not hit:
        raise ValueError("I can't find that step.")
    return hit


def tick_task(settings: Settings, args: dict) -> screen.Shown:
    h = st.pick_hustle(settings, args.get("hustle"))
    t = _task(h, args)
    t["done"] = args.get("done", True) is not False
    st.update_hustle(settings, h)
    return launch_plan(settings, {"hustle": h["name"]}, f"{'Done' if t['done'] else 'Reopened'}: {t['text']} ")


def add_task(settings: Settings, args: dict) -> screen.Shown:
    h = st.pick_hustle(settings, args.get("hustle"))
    if len(h["tasks"]) >= 60:
        raise ValueError("That plan already has plenty of steps.")
    day = int(args["day"]) if args.get("day") else min(max(_day_of(h), 1), 30)
    if not 1 <= day <= 60:
        raise ValueError("Give a plan day between 1 and 60.")
    h["tasks"].append({"id": max(t["id"] for t in h["tasks"]) + 1, "day": day, "text": st.need(args.get("task") or args.get("text"), "step", 140),
                       "done": False})
    st.update_hustle(settings, h)
    return launch_plan(settings, {"hustle": h["name"]}, "Added the step. ")


def next_tasks(settings: Settings, args: dict) -> screen.Shown:
    items = []
    for h in st.hustles(settings):
        if h["status"] != "active":
            continue
        start = date.fromisoformat(h["started"])
        for t in sorted((t for t in h["tasks"] if not t["done"]), key=lambda t: t["day"])[:4]:
            due = start + timedelta(days=t["day"] - 1)
            items.append((due, {"label": f"{h['name']}: {t['text']} ({st.until(due)})",
                                "say": f"Tick off task {t['id']} on my {h['name']} launch plan."}))
    if not items:
        raise ValueError("No open plan steps. Start a side hustle first.")
    items.sort(key=lambda x: x[0])
    return screen.Shown(f"You have {len(items)} steps coming up. First: {items[0][1]['label']}.", screen.card(
        "list", "Next side hustle steps", "sidehustle-next", items=[i for _, i in items[:10]]))


def hustles(settings: Settings, args: dict) -> screen.Shown:
    rows = st.hustles(settings)
    if not rows:
        raise ValueError("You haven't started a side hustle yet. Ask me for ideas, or tell me which one to start.")
    log = st.log(settings)
    table = []
    for h in rows:
        t = st.totals(log, h["name"])
        done = sum(1 for x in h["tasks"] if x["done"])
        table.append([h["name"], h["status"], f"day {max(_day_of(h), 1)}", f"{done}/{len(h['tasks'])}", st.num(round(t["hours"], 1)) + " h",
                      st.gbp(t["profit"])])
    return screen.Shown(f"You have {len(rows)} side hustle{'s' if len(rows) != 1 else ''}.", screen.card(
        "table", "Your side hustles", "sidehustle-hustles", columns=["Hustle", "Status", "Day", "Plan", "Hours", "Profit"], rows=table))


def set_status(settings: Settings, args: dict) -> str:
    if args.get("status") not in STATUS:
        raise ValueError("Set it to active, paused or stopped.")
    h = st.pick_hustle(settings, args.get("hustle"))
    h["status"] = args["status"]
    st.update_hustle(settings, h)
    return f"{h['name']} is now {h['status']}. Your logged numbers are kept."


def remove_hustle(settings: Settings, args: dict) -> str:
    h = st.pick_hustle(settings, args.get("hustle"))
    if not args.get("confirmed"):
        return f"Remove {h['name']} and its plan? Say yes to confirm. Logged hours and money stay."
    _save(settings, [x for x in st.hustles(settings) if x["name"] != h["name"]])
    return f"Removed {h['name']}."


def goal_set(settings: Settings, args: dict) -> str:
    prof = st.profile(settings)
    prof["goal"] = st.number(args.get("amount"), "monthly goal")
    st.save(settings, st.PROFILE, prof)
    return f"Your goal is {st.gbp(prof['goal'])} extra profit a month. It's a target to aim at, not a promise."


def goal_progress(settings: Settings, args: dict) -> screen.Shown:
    goal = st.profile(settings).get("goal")
    if not goal:
        raise ValueError("Set a monthly goal first, for example: I want £300 extra a month.")
    first, last = st.month_bounds(args.get("month"))
    log = st.log(settings)
    total = st.totals(log, None, first, last)
    per = [{"name": n, "profit": st.totals(log, n, first, last)["profit"]} for n in sorted({e["hustle"] for e in log})]
    per = [p for p in per if p["profit"]]
    today = min(max(st.today(), first), last)
    elapsed, days = (today - first).days + 1, calendar.monthrange(first.year, first.month)[1]
    projected = round(total["profit"] / elapsed * days, 2) if elapsed >= 7 and total["profit"] > 0 else None
    paid = [o for o in orders._orders(settings) if o["status"] == "paid" and o["price"] > 0]
    avg = sum(o["price"] for o in paid) / len(paid) if paid else None
    left = max(goal - total["profit"], 0)
    more = f"About {-(-left // avg):.0f} more orders at your average of {st.gbp(round(avg, 2))}." if avg and left else ""
    pctv = min(round(total["profit"] / goal * 100), 999) if total["profit"] > 0 else 0
    text = f"{first.strftime('%B')}: {st.gbp(total['profit'])} of your {st.gbp(goal)} goal ({pctv}%). {st.HONEST}"
    return screen.Shown(text, screen.card(st.GOAL, "Extra income goal", "", data={
        "goal": goal, "so_far": total["profit"], "pct": pctv, "days_left": (last - today).days, "projected": projected,
        "hustles": per, "hours": round(total["hours"], 1), "note": (more + " " if more else "") + "Profit is income minus costs. " + st.HONEST},
        buttons=[{"label": "Monthly review", "say": "Do my side hustle monthly review."}]))


def _verdict(t: dict, months: int) -> tuple[str, str, list[str]]:
    reasons = []
    if not (t["hours"] or t["income"] or t["costs"]):
        return "nodata", "Nothing is logged for this month yet.", ["Log your hours, income and costs, then review again."]
    if t["profit"] <= 0:
        reasons.append(f"Profit is {st.gbp(t['profit'])} after {st.num(round(t['hours'], 1))} hours.")
        if months >= 3 and t["hours"] >= 10:
            return "stop", "It hasn't made a profit for a while. Consider changing the offer or stopping.", reasons
        return "change", "Not profitable yet, which is common early on. Set a date to decide.", reasons
    if t["rate"] is not None and t["rate"] < st.WAGE:
        reasons.append(f"About {st.gbp(t['rate'])} an hour, below about {st.gbp(st.WAGE)} (check GOV.UK for the current wage).")
        return "change", "It earns, but low per hour. Look at prices, costs or slow tasks.", reasons
    reasons.append(f"Profit {st.gbp(t['profit'])}" + (f", about {st.gbp(t['rate'])} an hour." if t["rate"] else "."))
    return "keep", "The numbers look worth continuing for now.", reasons


def monthly_review(settings: Settings, args: dict) -> screen.Shown:
    first, last = st.month_bounds(args.get("month"))
    h = st.pick_hustle(settings, args.get("hustle"), need_one=False)
    name = h["name"] if h else (st.clean(args.get("hustle"), 60) or None)
    t = st.totals(st.log(settings), name, first, last)
    started = date.fromisoformat(h["started"]) if h else first
    months = max((last.year - started.year) * 12 + last.month - started.month + 1, 1)
    code, headline, reasons = _verdict(t, months)
    label = name or "All side hustles"
    if args.get("decision"):
        if args["decision"] not in DECISIONS:
            raise ValueError("The decision is one of " + ", ".join(DECISIONS) + ".")
        rows = [r for r in st.load(settings, st.REVIEWS, []) if isinstance(r, dict)]
        rows.append({"month": first.strftime("%Y-%m"), "hustle": label, "decision": args["decision"], "profit": t["profit"],
                     "hours": round(t["hours"], 1), "rate": t["rate"], "saved": st.today().isoformat()})
        st.save(settings, st.REVIEWS, rows[-200:])
    text = f"{label}, {first.strftime('%B')}: {headline} The decision is yours."
    return screen.Shown(text, screen.card(st.REVIEW, f"{label}: {first.strftime('%B')} review", "", data={
        "verdict": code, "headline": headline, "reasons": reasons, "questions": QUESTIONS, "decision": args.get("decision", ""),
        "stats": [["Income", st.gbp(t["income"])], ["Costs", st.gbp(t["costs"])], ["Profit", st.gbp(t["profit"])],
                  ["Hours", st.num(round(t["hours"], 1))], ["Per hour", st.rate_text(t["rate"])]],
        "note": "Prompts from your own numbers, not advice. " + st.HONEST},
        buttons=[{"label": d.capitalize(), "say": f"Record my {label} review: {d}."} for d in DECISIONS]))


def review_history(settings: Settings, args: dict) -> screen.Shown:
    rows = [r for r in st.load(settings, st.REVIEWS, []) if isinstance(r, dict)]
    if not rows:
        raise ValueError("No saved reviews yet. Do a monthly review and say what you decide.")
    table = [[r["month"], r["hustle"], r["decision"], st.gbp(r["profit"]), st.num(r["hours"]) + " h"] for r in rows[::-1][:20]]
    return screen.Shown(f"You have {len(rows)} saved reviews.", screen.card(
        "table", "Past side hustle reviews", "sidehustle-reviews", columns=["Month", "Hustle", "Decision", "Profit", "Hours"], rows=table))


def tool_definitions() -> list[dict]:
    return [{
        "name": "sidehustle_plan",
        "description": "Run a side hustle: start one with a 30-day launch plan checklist, tick steps, next steps, list hustles, pause "
                       "or stop, monthly extra-income goal and progress, monthly stop-or-keep-going review with saved decision, "
                       "customer and order log (add, list, update status, customers, notes). Set confirmed only after the user says "
                       "yes to remove a hustle or an order. Never promises income.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "hustle": {"type": "string", "description": "Side hustle name."},
                "name": {"type": "string", "description": "Side hustle to start, e.g. dog walking."},
                "task_id": {"type": "integer"}, "task": {"type": "string", "description": "Step words or new step text."},
                "done": {"type": "boolean"}, "day": {"type": "integer", "description": "Plan day 1-30."},
                "status": {"type": "string", "enum": STATUS + orders.STATUSES, "description": "Hustle or order status."},
                "amount": {"type": "number", "description": "Monthly extra profit goal in pounds."},
                "month": {"type": "string", "description": "YYYY-MM."},
                "decision": {"type": "string", "enum": DECISIONS},
                "order_id": {"type": "integer"}, "customer": {"type": "string"}, "item": {"type": "string"},
                "price": {"type": "number"}, "due": {"type": "string", "description": "YYYY-MM-DD."},
                "note": {"type": "string"}, "date": {"type": "string", "description": "Start date YYYY-MM-DD."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    handlers = {"start_hustle": start_hustle, "launch_plan": launch_plan, "tick_task": tick_task, "add_task": add_task,
                "next_tasks": next_tasks, "hustles": hustles, "set_status": set_status, "remove_hustle": remove_hustle,
                "goal_set": goal_set, "goal_progress": goal_progress, "monthly_review": monthly_review,
                "review_history": review_history, "order_add": orders.order_add, "orders": orders.orders,
                "order_update": orders.order_update, "customers": orders.customers, "customer_note": orders.customer_note,
                "order_remove": orders.order_remove}
    action = args.get("action")
    if action not in handlers:
        raise ValueError("Which side hustle step? " + ", ".join(ACTIONS))
    return handlers[action](settings, args)
