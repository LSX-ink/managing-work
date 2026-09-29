"""Calm evenings: a gentle wind-down routine checklist you can tick off, when to start it for your bedtime, sleep-friendly
tips, and a digital detox timer with a record of screen-free time.

Saved on this PC in calm-winddown.json ({items, ticks by date}) and calm-detox.json ({current, done}). Not medical advice.
"""

from datetime import datetime, timedelta

import calm_data as data
import calm_store as store
import screen
import wellness_store
from config import Settings

NAMES = {"calm_evening"}
ACTIONS = ["winddown_show", "winddown_tick", "winddown_add", "winddown_remove", "winddown_start", "sleep_tips",
           "detox_start", "detox_status", "detox_end", "detox_history"]
TIPS = ["Keep a regular bedtime and wake time, even at weekends.", "Dim the lights an hour before bed.",
        "Keep screens out of the last 30 minutes if you can, or use night mode.",
        "Keep the bedroom cool, dark and quiet.", "Have your last coffee or tea by early afternoon.",
        "If you can't sleep after 20 minutes, get up and do something quiet until you feel sleepy.",
        "Write down tomorrow's worries or tasks before bed so your head can rest."]


def _state(settings: Settings) -> dict:
    state = store.load(settings, "winddown", {})
    state.setdefault("items", list(data.WINDDOWN))
    state.setdefault("ticks", {})
    state.setdefault("bedtime", "")
    return state


def _find(items: list[str], words) -> str:
    key = store.clean(words).lower()
    found = [i for i in items if key and (key in i.lower() or i.lower() in key)]
    if not found:
        raise ValueError("None of your wind-down steps match that.")
    return found[0]


def winddown_show(settings: Settings) -> screen.Shown:
    state = _state(settings)
    done = set(state["ticks"].get(store.today().isoformat(), []))
    items = [{"label": i, "done": i in done, "say": f"Tick off {i} in my wind-down"} for i in state["items"]]
    left = len(state["items"]) - len([i for i in state["items"] if i in done])
    card = screen.card("list", "Evening wind-down", "calm-winddown", items=items,
                       buttons=[{"label": "Sleepy guide", "say": "Guide me through the sleepy wind-down"},
                                {"label": "4-7-8", "say": "Start 4-7-8 breathing"}])
    said = "All done. Sleep well." if not left else f"{store.plural(left, 'step')} left in your wind-down. Tap to tick them off."
    return screen.Shown(said, card)


def winddown_tick(settings: Settings, words) -> screen.Shown:
    state = _state(settings)
    item = _find(state["items"], words)
    ticks = state["ticks"]
    today = store.today().isoformat()
    ticks[today] = list(dict.fromkeys(ticks.get(today, []) + [item]))[:50]
    state["ticks"] = {d: v for d, v in sorted(ticks.items())[-30:]}
    store.save(settings, "winddown", state)
    return winddown_show(settings)


def winddown_add(settings: Settings, text) -> str:
    state = _state(settings)
    item = store.need(text, "wind-down step", 80)
    if item.lower() in (i.lower() for i in state["items"]):
        return "That step is already in your routine."
    state["items"] = (state["items"] + [item])[:20]
    store.save(settings, "winddown", state)
    return f"Added '{item}'. Your wind-down has {len(state['items'])} steps."


def winddown_remove(settings: Settings, words, confirmed: bool) -> str:
    state = _state(settings)
    item = _find(state["items"], words)
    if not confirmed:
        return f"That would remove '{item}' from your routine. Ask the user to confirm, then call again with confirmed true."
    state["items"] = [i for i in state["items"] if i != item]
    store.save(settings, "winddown", state)
    return f"Removed '{item}'."


def winddown_start(settings: Settings, bedtime, mins) -> str:
    state = _state(settings)
    if bedtime:
        state["bedtime"] = wellness_store.clock(bedtime, "bedtime")
        store.save(settings, "winddown", state)
    if not state["bedtime"]:
        raise ValueError("What time do you want to be in bed? For example, 22:30.")
    length = int(store.minutes(mins or 45, "wind-down minutes", 5, 180))
    hour, minute = map(int, state["bedtime"].split(":"))
    start = datetime(2000, 1, 1, hour, minute) - timedelta(minutes=length)
    return (f"For bed at {state['bedtime']}, start your {length} minute wind-down at {start:%H:%M}. "
            "Say 'show my wind-down' when you begin.")


def sleep_tips() -> screen.Shown:
    card = screen.card("list", "Evening and sleep tips", "calm-sleep-tips", items=[{"label": t} for t in TIPS])
    return screen.Shown(f"Some gentle sleep habits are on the screen. {store.SAFETY}", card)


# Digital detox

def _detox(settings: Settings) -> dict:
    state = store.load(settings, "detox", {})
    state.setdefault("current", None)
    state.setdefault("done", [])
    return state


def _ms(when: datetime) -> int:
    return int(when.timestamp() * 1000)


def detox_start(settings: Settings, mins) -> screen.Shown:
    length = int(store.minutes(mins or 60, "detox minutes", 5, 720))
    state = _detox(settings)
    now = store.now()
    state["current"] = {"start": now.isoformat(timespec="seconds"), "minutes": length}
    store.save(settings, "detox", state)
    card = screen.card("timer", "Digital detox", "calm-detox", ends_at=_ms(now + timedelta(minutes=length)),
                       buttons=[{"label": "I'm done", "say": "End my digital detox"}])
    return screen.Shown(f"Digital detox for {length} minutes. Put the phone down; I'll be quiet. Say 'end my detox' "
                        "when you're back.", card)


def _running(state: dict) -> tuple[datetime, int] | None:
    cur = state.get("current")
    return (datetime.fromisoformat(cur["start"]), cur["minutes"]) if cur else None


def detox_status(settings: Settings) -> str | screen.Shown:
    running = _running(_detox(settings))
    if not running:
        return "No detox is running. Say 'start a one hour detox' when you want one."
    start, length = running
    ends = start + timedelta(minutes=length)
    left = (ends - store.now()).total_seconds() / 60
    card = screen.card("timer", "Digital detox", "calm-detox", ends_at=_ms(ends),
                       buttons=[{"label": "I'm done", "say": "End my digital detox"}])
    said = f"{left:.0f} minutes left of your detox." if left > 0 else "Your detox time is up. Well done."
    return screen.Shown(said, card)


def detox_end(settings: Settings) -> str:
    state = _detox(settings)
    running = _running(state)
    if not running:
        return "No detox was running."
    start, length = running
    spent = max(1, round((store.now() - start).total_seconds() / 60))
    state["done"] = (state["done"] + [{"date": start.date().isoformat(), "minutes": min(spent, 720),
                                       "planned": length}])[-200:]
    state["current"] = None
    store.save(settings, "detox", state)
    return f"Welcome back. That's {store.plural(min(spent, 720), 'minute')} screen-free. Well done."


def detox_history(settings: Settings) -> str | screen.Shown:
    done = _detox(settings)["done"]
    if not done:
        return "No detoxes finished yet."
    total = sum(d["minutes"] for d in done)
    card = screen.card("table", "Digital detox", "calm-detox-history", columns=["Date", "Minutes", "Planned"],
                       rows=[[d["date"], str(d["minutes"]), str(d["planned"])] for d in done[-10:][::-1]])
    return screen.Shown(f"{store.plural(len(done), 'detox', 'detoxes')} finished, {total} screen-free minutes in all.", card)


def tool_definitions() -> list[dict]:
    return [{
        "name": "calm_evening",
        "description": "Calm evenings and digital detox. winddown_show (evening wind-down checklist pop-up), "
                       "winddown_tick (words), winddown_add (text), winddown_remove (words; confirmed true only after "
                       "the user confirms), winddown_start (bedtime like 22:30 and minutes: when to begin winding "
                       "down), sleep_tips. detox_start (minutes; phone-free timer), detox_status, detox_end, "
                       "detox_history. Not medical advice.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ACTIONS},
                "words": {"type": "string"},
                "text": {"type": "string"},
                "bedtime": {"type": "string", "description": "e.g. 22:30."},
                "minutes": {"type": "number"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    actions = {
        "winddown_show": lambda: winddown_show(settings),
        "winddown_tick": lambda: winddown_tick(settings, args.get("words") or args.get("text")),
        "winddown_add": lambda: winddown_add(settings, args.get("text")),
        "winddown_remove": lambda: winddown_remove(settings, args.get("words") or args.get("text"),
                                                   bool(args.get("confirmed"))),
        "winddown_start": lambda: winddown_start(settings, args.get("bedtime"), args.get("minutes")),
        "sleep_tips": sleep_tips,
        "detox_start": lambda: detox_start(settings, args.get("minutes")),
        "detox_status": lambda: detox_status(settings),
        "detox_end": lambda: detox_end(settings),
        "detox_history": lambda: detox_history(settings),
    }
    if action not in actions:
        raise ValueError(f"Unknown action {action}.")
    return actions[action]()
