"""Everyday support, part 1: knowing what day it is, today's plan, a simple mode of six huge buttons, morning and
bedtime routine ticks, a calm break, and repeating Alfred's last reply slowly.

Everything is kept in support.json in the memory folder and never leaves the PC. New pop-up kinds:
"support-today" (big date and part of the day) and "support-home" (six huge buttons), drawn by popup-support.js.
"""

import json
from datetime import datetime, timedelta

import homestore as hs
import memory
import screen
import support_store as store
from config import Settings

screen.EXTRA_KINDS.update({"support-today", "support-home"})
ACTIONS = ["today", "plan_add", "plan_show", "plan_done", "simple_mode", "routine_set", "routine_show",
           "routine_tick", "break", "repeat_slower"]
ROUTINES = ["morning", "bedtime"]
HOME_BUTTONS = [
    ("What time is it", "What day and time is it?"),
    ("The weather", "What's the weather like today?"),
    ("Who to call", "Show me the person I can call."),
    ("Today's plan", "What's my plan for today?"),
    ("Where are my things", "Where have I put things?"),
    ("I need help", "I need help, I'm lost."),
]


def _plan(data: dict, day: str) -> list[dict]:
    return data["plan"].setdefault(day, [])


def _prune(data: dict, today) -> None:
    keep = (today - timedelta(days=14)).isoformat()
    for key in ("plan", "ticks"):
        data[key] = {d: v for d, v in data[key].items() if d >= keep}


def _plan_lines(items: list[dict]) -> list[dict]:
    return [{"time": i.get("time", ""), "text": i["text"], "done": bool(i.get("done"))}
            for i in sorted(items, key=lambda i: i.get("time") or "99:99")]


def today(settings: Settings, moment: datetime) -> screen.Shown:
    plan = _plan_lines(store.load(settings)["plan"].get(moment.date().isoformat(), []))
    part = store.part_of_day(moment)
    weekday, date_text = moment.strftime("%A"), f"{moment.day} {moment.strftime('%B %Y')}"
    c = screen.card("support-today", "What day is it?", "support-today",
                    data={"weekday": weekday, "date": date_text, "time": moment.strftime("%H:%M"), "part": part,
                          "plan": plan},
                    buttons=[{"label": "Simple mode", "say": "Show me simple mode."}])
    left = sum(1 for p in plan if not p["done"])
    said = f"It is {weekday} {moment.day} {moment.strftime('%B')}, {part}."
    return screen.Shown(said + (f" You have {left} thing{'s' if left != 1 else ''} planned today." if left else ""), c)


def plan_add(settings: Settings, args: dict, moment: datetime) -> str:
    text = hs.need(args.get("text"), "thing to plan", 120)
    day = hs.parse_day(args.get("day"), moment.date()).isoformat()
    item = {"text": text, "time": store.clock(args["time"]) if args.get("time") else "", "done": False}
    data = store.load(settings)
    store.put(_plan(data, day), item)
    _prune(data, moment.date())
    store.save(settings, data)
    return f"Added to the plan: {text}" + (f" at {item['time']}." if item["time"] else ".")


def plan_show(settings: Settings, args: dict, moment: datetime) -> screen.Shown | str:
    day = hs.parse_day(args.get("day"), moment.date())
    items = _plan_lines(store.load(settings)["plan"].get(day.isoformat(), []))
    if not items:
        return f"There's nothing planned for {hs.spoken(day)}."
    rows = [{"label": (f"{i['time']}  " if i["time"] else "") + i["text"], "done": i["done"],
             "say": f"Tick off {i['text']} on my plan."} for i in items]
    c = screen.card("list", f"Plan for {hs.spoken(day)}", f"support-plan-{day.isoformat()}", items=rows, checks=True)
    return screen.Shown(f"{len(items)} thing{'s' if len(items) != 1 else ''} in the plan: "
                        + "; ".join(i["text"] for i in items[:6]) + ".", c)


def plan_done(settings: Settings, args: dict, moment: datetime) -> str:
    day = hs.parse_day(args.get("day"), moment.date()).isoformat()
    data = store.load(settings)
    items = data["plan"].get(day, [])
    key = hs.find([i["text"] for i in items], hs.need(args.get("text"), "plan item"))
    if key is None:
        raise ValueError("I can't find that in today's plan.")
    next(i for i in items if i["text"] == key)["done"] = True
    store.save(settings, data)
    return f"Ticked off {key}."


def simple_mode() -> screen.Shown:
    c = screen.card("support-home", "Simple mode", "support-home",
                    data={"buttons": [{"label": label, "say": say} for label, say in HOME_BUTTONS]})
    return screen.Shown("Simple mode is on the screen. Press any big button.", c)


def _routine(name) -> str:
    key = hs.clean(name).lower()
    if key not in ROUTINES:
        raise ValueError("Which routine? Morning or bedtime.")
    return key


def routine_set(settings: Settings, args: dict) -> str:
    routine = _routine(args.get("routine"))
    items = [hs.clean(i, 80) for i in args.get("items") or [] if hs.clean(i)]
    if not items:
        raise ValueError("What are the steps of the routine?")
    data = store.load(settings)
    data["routines"][routine] = items[:store.MAX_ITEMS]
    store.save(settings, data)
    return f"Saved your {routine} routine: {len(items[:store.MAX_ITEMS])} steps."


def routine_show(settings: Settings, args: dict, moment: datetime) -> screen.Shown:
    routine = _routine(args.get("routine") or ("bedtime" if moment.hour >= 18 else "morning"))
    data = store.load(settings)
    steps = data["routines"].get(routine)
    if not steps:
        raise ValueError(f"You haven't set up a {routine} routine yet. Tell me the steps and I'll save them.")
    done = data["ticks"].get(moment.date().isoformat(), {}).get(routine, [])
    items = [{"label": s, "done": s in done, "say": f"Tick {s} on my {routine} routine."} for s in steps]
    left = [s for s in steps if s not in done]
    c = screen.card("list", f"{routine.title()} routine", f"support-routine-{routine}", items=items, checks=True)
    return screen.Shown(f"Your {routine} routine: " + (f"next is {left[0]}." if left else "all done, well done."), c)


def routine_tick(settings: Settings, args: dict, moment: datetime) -> screen.Shown:
    routine = _routine(args.get("routine"))
    data = store.load(settings)
    steps = data["routines"].get(routine, [])
    step = store.match(steps, args.get("text"), "step")
    done = data["ticks"].setdefault(moment.date().isoformat(), {}).setdefault(routine, [])
    if step not in done:
        done.append(step)
    store.save(settings, data)
    return routine_show(settings, {"routine": routine}, moment)


def take_a_break() -> screen.Shown:
    text = ("Take a slow breath. You are safe. There is no hurry.\n\nLook around and find something blue. "
            "Feel your feet on the floor. Have a sip of water.\n\nA minute is all it takes.")
    c = screen.card("text", "Take a break", "support-break", text=text, buttons=[
        {"label": "Ground me", "say": "Ground me with 5-4-3-2-1."},
        {"label": "Breathe with me", "say": "Guide my breathing."},
        {"label": "One minute timer", "say": "Set a timer for 1 minute."}])
    return screen.Shown("Let's pause together. Breathe in slowly, and out. There is no hurry.", c)


def repeat_slower(settings: Settings) -> str:
    try:
        saved = json.loads((memory.root(settings) / ".recent-chat.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = []
    replies = [t["reply"] for t in saved if isinstance(t, dict) and isinstance(t.get("reply"), str) and t["reply"]]
    if not replies:
        raise ValueError("I don't have anything recent to repeat.")
    return ("Repeat this now, slowly, in short simple sentences with a pause after each, without adding anything: "
            + replies[-1])


def tool_definitions() -> list[dict]:
    return [{
        "name": "support_day",
        "description": "Gentle everyday help for anyone who finds things hard (memory difficulties, older people, "
                       "anxiety). action: today = 'what day is it', big date, morning/afternoon/evening and today's "
                       "plan; plan_add / plan_show / plan_done = today's plan (text, time, day); simple_mode = six "
                       "huge buttons (time, weather, who to call, plan, where are my things, help); routine_set "
                       "(routine morning or bedtime, items) / routine_show / routine_tick (routine, text) = "
                       "morning and bedtime tick lists; break = calm break with links to grounding; repeat_slower "
                       "= 'say that again slowly': returns the last reply for you to say slowly and simply.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "text": {"type": "string", "description": "plan_add, plan_done or routine_tick: the item."},
                "time": {"type": "string", "description": "plan_add: like 14:30."},
                "day": {"type": "string", "description": "YYYY-MM-DD, today, tomorrow or a weekday."},
                "routine": {"type": "string", "enum": ROUTINES},
                "items": {"type": "array", "items": {"type": "string"}, "description": "routine_set: the steps."},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"support_day"}


def run_tool(name: str, args: dict, settings: Settings, http=None, now: datetime | None = None):
    moment = store.now(now)
    action = args.get("action")
    if action == "today":
        return today(settings, moment)
    if action == "plan_add":
        return plan_add(settings, args, moment)
    if action == "plan_show":
        return plan_show(settings, args, moment)
    if action == "plan_done":
        return plan_done(settings, args, moment)
    if action == "simple_mode":
        return simple_mode()
    if action == "routine_set":
        return routine_set(settings, args)
    if action == "routine_show":
        return routine_show(settings, args, moment)
    if action == "routine_tick":
        return routine_tick(settings, args, moment)
    if action == "break":
        return take_a_break()
    if action == "repeat_slower":
        return repeat_slower(settings)
    raise ValueError("I can't do that one.")
