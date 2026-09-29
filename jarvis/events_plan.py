"""Event planning: create an event with a countdown, an event dashboard, task timelines that work back from the date
(party, birthday, kids, UK wedding, Christmas), ticks, and the setup-day checklist.

Everything is saved in events.json in the memory folder. Guests, seating, budget and food are in the other events tools.
"""

from datetime import date, timedelta

import events_data as data
import events_store as store
import homestore as hs
import screen
from config import Settings

screen.EXTRA_KINDS.update({"events-dashboard", "events-timeline"})

ACTIONS = ["create", "list", "dashboard", "update", "remove", "task_add", "task_tick", "timeline", "standard_plan",
           "setup_list", "setup_tick"]


def _next_christmas(today: date) -> date:
    this_year = date(today.year, 12, 25)
    return this_year if this_year >= today else date(today.year + 1, 12, 25)


def _kind(value) -> str:
    kind = hs.clean(value).lower()
    if kind and kind not in store.KINDS:
        raise ValueError("The kind is one of: " + ", ".join(store.KINDS) + ".")
    return kind


def _add_plan(event: dict, kind: str) -> int:
    """Add the standard tasks for a kind that aren't there yet; how many were added."""
    have = {t["text"] for t in event["tasks"]}
    fresh = [{"text": text, "days_before": days, "done": False} for days, text in data.PLANS.get(kind, []) if text not in have]
    event["tasks"] = (event["tasks"] + fresh)[:store.MAX_ITEMS]
    return len(fresh)


def create(settings: Settings, args: dict, today: date) -> str:
    name = hs.need(args.get("name"), "event name", 60)
    kind = _kind(args.get("kind"))
    if not hs.clean(args.get("date")) and kind == "christmas":
        day = _next_christmas(today)
    else:
        day = hs.parse_day(hs.need(args.get("date"), "date, like 2026-10-10"), today)
    budget = store.money(args.get("budget", 0), "budget")
    found = store.load(settings)
    events = found["events"]
    key = hs.find(events, name) or name
    if key not in events and len(events) >= store.MAX_EVENTS:
        raise ValueError("That's plenty of events; remove an old one first.")
    event = events.get(key) or store.blank(day, kind or "party", "", 0)
    event["date"] = day.isoformat()
    if kind:
        event["kind"] = kind
    if hs.clean(args.get("place")):
        event["place"] = hs.clean(args.get("place"), 80)
    if "budget" in args:
        event["budget"] = budget
    added = _add_plan(event, kind) if kind and args.get("with_plan", True) else 0
    events[key] = event
    store.save(settings, found)
    left = store.days_to(event, today)
    said = f"Saved {key} for {hs.spoken(day)}, {store.countdown(left)}."
    return said + (f" I added {added} steps to the timeline." if added else "")


def list_events(settings: Settings, today: date) -> screen.Shown:
    events = store.load(settings)["events"]
    if not events:
        raise ValueError("You haven't got any events yet.")
    rows = [[k, hs.spoken(date.fromisoformat(e["date"])), store.countdown(store.days_to(e, today)), e["place"] or "-",
             store.gbp(e["budget"]) if e["budget"] else "-"]
            for k, e in sorted(events.items(), key=lambda x: x[1]["date"])]
    first = min((k for k, e in events.items() if e["date"] >= today.isoformat()), key=lambda k: events[k]["date"], default=None)
    said = f"You have {hs.plural(len(events), 'event')}." + (f" Next is {first}, {store.countdown(store.days_to(events[first], today))}." if first else "")
    return screen.Shown(said, screen.card("table", "My events", "events-list", buttons=[
        store.button("Show next event", "Show my next event dashboard.")],
        columns=["Event", "Date", "When", "Where", "Budget"], rows=rows))


def _stats(event: dict) -> dict:
    guests = event["guests"]
    counts = {r: sum(g["rsvp"] == r for g in guests.values()) for r in store.RSVPS}
    spent = round(sum(s["amount"] for s in event["spends"]), 2)
    return {"guests": counts, "headcount": store.headcount(event), "spent": spent,
            "done": sum(t["done"] for t in event["tasks"]), "tasks": len(event["tasks"])}


def _due(event: dict, task: dict) -> date:
    return date.fromisoformat(event["date"]) - timedelta(days=task["days_before"])


def dashboard(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    s = _stats(event)
    days = store.days_to(event, today)
    planned = event["budget"] or round(sum(b["planned"] for b in event["budget_items"].values()), 2)
    open_tasks = sorted((t for t in event["tasks"] if not t["done"]), key=lambda t: t["days_before"], reverse=True)
    nxt = [{"text": t["text"], "when": hs.spoken(_due(event, t)), "late": _due(event, t) < today} for t in open_tasks[:4]]
    card = screen.card("events-dashboard", key, f"events-dash-{key}", buttons=[
        store.button("Timeline", f"Show the timeline for {key}."), store.button("Guests", f"Show the guest list for {key}."),
        store.button("Budget", f"Show the budget for {key}."), store.button("Seating", f"Show the seating plan for {key}.")],
        data={"name": key, "date": hs.spoken(date.fromisoformat(event["date"])), "days": days, "place": event["place"],
              "kind": event["kind"], "budget": {"planned": planned, "spent": s["spent"]}, "guests": s["guests"],
              "headcount": s["headcount"], "tasks": {"done": s["done"], "total": s["tasks"]}, "next": nxt})
    said = (f"{key} is {store.countdown(days)}. {s['done']} of {s['tasks']} tasks done, {s['headcount']} guests coming, "
            f"{store.gbp(s['spent'])} spent" + (f" of {store.gbp(planned)}." if planned else "."))
    return screen.Shown(said, card)


def update(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    changed = []
    if hs.clean(args.get("date")):
        event["date"] = hs.parse_day(args["date"], today).isoformat()
        changed.append("date")
    if hs.clean(args.get("place")):
        event["place"] = hs.clean(args["place"], 80)
        changed.append("place")
    if "budget" in args:
        event["budget"] = store.money(args["budget"], "budget")
        changed.append("budget")
    if hs.clean(args.get("kind")):
        event["kind"] = _kind(args["kind"])
        changed.append("kind")
    if hs.clean(args.get("new_name"), 60):
        new = hs.clean(args["new_name"], 60)
        found["events"][new] = found["events"].pop(key)
        key = new
        changed.append("name")
    if not changed:
        raise ValueError("Tell me what to change: the date, place, budget, kind or a new name.")
    store.save(settings, found)
    return f"Updated the {', '.join(changed)} of {key}."


def remove(settings: Settings, name, confirmed: bool, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, hs.need(name, "event"), today)
    if not confirmed:
        return f"Removing {key} deletes its guests, budget and tasks. Please confirm and I'll do it."
    del found["events"][key]
    store.save(settings, found)
    return f"Removed {key}."


def task_add(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    text = hs.need(args.get("task"), "task", 120)
    days = hs.number(args.get("days_before", 0), "days before", -365, 800)
    if "weeks_before" in args:
        days = hs.number(args["weeks_before"], "weeks before", -52, 110) * 7
    if len(event["tasks"]) >= store.MAX_ITEMS:
        raise ValueError("That's plenty of tasks for one event.")
    event["tasks"].append({"text": text, "days_before": int(days), "done": False})
    store.save(settings, found)
    return f"Added '{text}' to {key}, due {hs.spoken(_due(event, event['tasks'][-1]))}."


def _match(items: list[dict], wanted, what: str) -> dict:
    word = hs.need(wanted, what).lower()
    if word.isdigit() and 1 <= int(word) <= len(items):
        return items[int(word) - 1]
    hits = [t for t in items if word in t["text"].lower()]
    if len(hits) != 1:
        raise ValueError(f"I couldn't tell which {what} you mean; give me a bit more of its wording.")
    return hits[0]


def task_tick(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    ordered = sorted(event["tasks"], key=lambda t: -t["days_before"])
    task = _match(ordered, args.get("task"), "task")
    task["done"] = args.get("done", True) is not False
    store.save(settings, found)
    left = sum(not t["done"] for t in event["tasks"])
    return f"{'Ticked' if task['done'] else 'Unticked'} '{task['text']}'. {left} left for {key}."


def _when(days: int) -> str:
    if days == 0:
        return "on the day"
    unit = "before" if days > 0 else "after"
    n = abs(days)
    if n >= 100:
        return f"{round(n / 30.4)} months {unit}"
    if n >= 14:
        return f"{round(n / 7)} weeks {unit}"
    return f"{hs.plural(n, 'day')} {unit}"


def timeline(settings: Settings, name, today: date) -> screen.Shown:
    event, key = store.pick(store.load(settings), name, today)
    if not event["tasks"]:
        raise ValueError(f"{key} has no tasks yet. Ask me to add the standard plan for it.")
    ordered = sorted(event["tasks"], key=lambda t: -t["days_before"])
    items = []
    for t in ordered:
        due = _due(event, t)
        state = "done" if t["done"] else "late" if due < today else "today" if due == today else ""
        items.append({"when": _when(t["days_before"]), "date": hs.spoken(due), "text": t["text"], "state": state,
                      "say": "" if t["done"] else f"Tick off '{t['text']}' for {key}."})
    late = sum(i["state"] == "late" for i in items)
    said = f"{sum(t['done'] for t in event['tasks'])} of {len(items)} steps done for {key}." + (f" {late} overdue." if late else "")
    return screen.Shown(said, screen.card("events-timeline", f"{key}: timeline", f"events-timeline-{key}", data={
        "items": items, "note": f"Working back from {hs.spoken(date.fromisoformat(event['date']))}."}))


def standard_plan(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    kind = _kind(args.get("kind")) or event["kind"]
    added = _add_plan(event, kind)
    event["kind"] = kind
    store.save(settings, found)
    extra = " It includes giving notice of marriage at the register office." if kind == "wedding" and added else ""
    return f"Added {added} {kind} steps to {key}.{extra}" if added else f"{key} already has all the {kind} steps."


def setup_list(settings: Settings, args: dict, today: date) -> screen.Shown:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    if hs.clean(args.get("item")):
        event["setup"].append({"text": hs.clean(args["item"], 100), "done": False})
    elif not event["setup"]:
        event["setup"] = [{"text": t, "done": False} for t in data.SETUP]
    store.save(settings, found)
    items = [{"label": i["text"], "done": i["done"], "say": f"Tick off {i['text']} on the setup list for {key}."}
             for i in event["setup"]]
    done = sum(i["done"] for i in event["setup"])
    return screen.Shown(f"{done} of {len(items)} setup jobs done for {key}.",
                        screen.card("list", f"{key}: setup day", f"events-setup-{key}", items=items, checks=True))


def setup_tick(settings: Settings, args: dict, today: date) -> str:
    found = store.load(settings)
    event, key = store.pick(found, args.get("name"), today)
    item = _match(event["setup"], args.get("item"), "setup job")
    item["done"] = args.get("done", True) is not False
    store.save(settings, found)
    return f"{'Ticked' if item['done'] else 'Unticked'} '{item['text']}'. {sum(not i['done'] for i in event['setup'])} setup jobs left."


def tool_definitions() -> list[dict]:
    return [{
        "name": "event_plan",
        "description": "Plan real-life occasions: party, birthday, kids' party, UK wedding, Christmas, gathering. "
                       "action: create = an event with name, date, place, budget, kind (adds the standard timeline; "
                       "kind christmas with no date is this Christmas); list = my events with countdowns; dashboard = "
                       "event summary pop-up (countdown, budget, guests, tasks); update; remove (confirmed true only "
                       "after the user says yes); task_add = one task (days_before or weeks_before the event); "
                       "task_tick = tick a task off; timeline = tasks working back from the date, ticks; "
                       "standard_plan = add the standard steps for a kind (wedding = UK wedding checklist); "
                       "setup_list = the setup-day or packing checklist (item adds one); setup_tick. "
                       "The event may be left out when it's the only or next one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "name": {"type": "string", "description": "The event, e.g. Mia's party."},
                "new_name": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD."},
                "place": {"type": "string"},
                "budget": {"type": "number", "description": "Total in pounds."},
                "kind": {"type": "string", "enum": store.KINDS},
                "with_plan": {"type": "boolean", "description": "create: false to skip the standard steps."},
                "task": {"type": "string", "description": "task_add: the wording; task_tick: its words or number."},
                "days_before": {"type": "number"},
                "weeks_before": {"type": "number"},
                "item": {"type": "string", "description": "setup_list: a job to add; setup_tick: which one."},
                "done": {"type": "boolean", "description": "task_tick or setup_tick: false to untick."},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"event_plan"}


def run_tool(name: str, args: dict, settings: Settings, http=None, today: date | None = None):
    today = today or date.today()
    action, event = args.get("action"), args.get("name")
    if action == "create":
        return create(settings, args, today)
    if action == "list":
        return list_events(settings, today)
    if action == "dashboard":
        return dashboard(settings, event, today)
    if action == "update":
        return update(settings, args, today)
    if action == "remove":
        return remove(settings, event, bool(args.get("confirmed")), today)
    if action == "task_add":
        return task_add(settings, args, today)
    if action == "task_tick":
        return task_tick(settings, args, today)
    if action == "timeline":
        return timeline(settings, event, today)
    if action == "standard_plan":
        return standard_plan(settings, args, today)
    if action == "setup_list":
        return setup_list(settings, args, today)
    if action == "setup_tick":
        return setup_tick(settings, args, today)
    raise ValueError(f"Unknown event action: {action}")
