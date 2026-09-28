"""Conversation modes: Alfred switches how he talks (tutor, coach, concise, ELI5, rubber duck...) until the user
says "normal mode". The tool result tells Alfred how to behave from then on; the current mode is kept in
modes-state.json so "what mode are you in?" works after a restart, and every mode's time goes into
modes-history.json. Also custom modes, the rubber duck debugging checklist and a daily check-in (energy, mood,
focus; mood is written through the wellbeing log in homewellbeing).
"""

import re
from datetime import datetime, timedelta

import homestore as hs
import homewellbeing
import screen
from config import Settings
from modes_data import DUCK_CHECKLIST, MODES, STAY

screen.EXTRA_KINDS.update({"modes-badge", "modes-checkin"})

STATE = "modes-state.json"
HISTORY = "modes-history.json"
CUSTOM = "modes-custom.json"
CHECKIN = "modes-checkin.json"
BADGE_TITLE = "Alfred's mode"
KEEP_HISTORY = 500
ALIASES = {
    "devil's advocate": "devils_advocate", "devils advocate": "devils_advocate", "explain like im five": "eli5",
    "explain like i'm five": "eli5", "simple": "eli5", "rubber duck": "rubber_duck", "duck": "rubber_duck",
    "calm": "listener", "supportive": "listener", "supportive listener": "listener", "calm listener": "listener",
    "quiz master": "quiz", "quizmaster": "quiz", "debate partner": "debate", "interview": "interviewer",
    "job interview": "interviewer", "language partner": "language", "short": "concise", "brief": "concise",
    "story": "storyteller", "socratic tutor": "tutor", "role play": "roleplay", "roleplay": "roleplay",
    "check-in": "checkin", "check in": "checkin", "daily check-in": "checkin",
}
# Modes whose start needs more than instructions (a session, a topic), registered by the other modes_* modules:
# key -> function(settings, topic) -> str | Shown, or None to use the plain mode in MODES.
STARTERS: dict = {}


def now() -> datetime:
    return hs.now()


def stamp() -> str:
    return now().isoformat(timespec="seconds")


def load_state(settings: Settings) -> dict:
    return hs.load(settings, STATE, {})


def save_state(settings: Settings, state: dict) -> None:
    hs.save(settings, STATE, state)


def session(settings: Settings, mode: str) -> dict | None:
    """The running session's data when that mode is on, else None."""
    state = load_state(settings)
    return state.get("session") if state.get("mode") == mode and isinstance(state.get("session"), dict) else None


def save_session(settings: Settings, data: dict) -> None:
    state = load_state(settings)
    state["session"] = data
    save_state(settings, state)


def _close_current(settings: Settings, state: dict) -> None:
    if not state.get("mode"):
        return
    history = hs.load(settings, HISTORY, [])
    history.append({"mode": state["mode"], "label": state.get("label", ""), "start": state.get("since", stamp()),
                    "end": stamp()})
    hs.save(settings, HISTORY, history[-KEEP_HISTORY:])


def instructions_text(label: str, instructions: str) -> str:
    return f"From now on until the user says stop: you are in {label} mode. {instructions} {STAY}".strip()


def badge(state: dict) -> dict:
    since = datetime.fromisoformat(state["since"]).timestamp() * 1000 if state.get("since") else None
    return screen.card("modes-badge", f"{BADGE_TITLE}: {state.get('label', '')}", "modes-badge",
                       buttons=[{"label": "Back to normal", "say": "Normal mode please."}],
                       data={"label": state.get("label", ""), "summary": state.get("summary", ""), "since": since})


def enter(settings: Settings, mode: str, label: str, summary: str, instructions: str,
          data: dict | None = None, card: dict | None = None, lead: str = "") -> screen.Shown:
    """Switch to a mode and return what Alfred should now do, with the mode badge (or the given card)."""
    state = load_state(settings)
    _close_current(settings, state)
    text = instructions_text(label, instructions)
    state = {"mode": mode, "label": label, "summary": hs.clean(summary, 120), "instructions": text,
             "since": stamp(), "session": data or {}}
    save_state(settings, state)
    return screen.Shown(f"{lead}{text}".strip(), card or badge(state))


def leave(settings: Settings) -> str:
    """End the current mode; '' when there wasn't one."""
    state = load_state(settings)
    if not state.get("mode"):
        return ""
    _close_current(settings, state)
    save_state(settings, {})
    return state.get("label", "")


def key_of(mode) -> str:
    text = re.sub(r"\s+", " ", str(mode or "")).strip().lower().removesuffix(" mode")
    text = ALIASES.get(text, text)
    return ALIASES.get(text.replace("_", " "), text.replace(" ", "_").replace("-", "_"))


def start(settings: Settings, mode, topic=None) -> screen.Shown | str:
    wanted = hs.need(mode, "mode", 60)
    key = key_of(wanted)
    topic = hs.clean(topic, 120)
    if key in ("normal", "stop", "off", "none", "default"):
        return stop(settings)
    if key in STARTERS:
        started = STARTERS[key](settings, topic)
        if started is not None:
            return started
    if key in MODES:
        label, summary, instructions = MODES[key]
        focus = f" The focus is: {topic}." if topic else ""
        return enter(settings, key, label, f"{summary}{' - ' + topic if topic else ''}", instructions + focus)
    custom = load_custom(settings)
    name = hs.find(custom, wanted.removesuffix(" mode"))
    if name:
        return enter(settings, "custom:" + name.lower(), name, "Your own mode", custom[name]["instructions"])
    names = [v[0] for v in MODES.values()] + list(custom)
    raise ValueError(f"I don't have a {wanted} mode. Modes: {', '.join(names)}.")


def stop(settings: Settings) -> screen.Shown | str:
    label = leave(settings)
    if not label:
        return "You're already in normal mode; nothing to stop."
    return screen.Shown(f"Left {label} mode. From now on reply as your usual self, dropping the {label} mode "
                        "instructions.", {"kind": "close", "all": False, "title": BADGE_TITLE})


def current(settings: Settings) -> screen.Shown | str:
    state = load_state(settings)
    if not state.get("mode"):
        return "No special mode is on; you're in normal mode."
    minutes = _minutes(state.get("since"), stamp())
    return screen.Shown(f"Currently in {state['label']} mode for {hs.plural(round(minutes), 'minute')}. "
                        f"{state.get('instructions', '')}", badge(state))


# ---- history ----------------------------------------------------------------------------------

def _minutes(start: str | None, end: str) -> float:
    try:
        return max(0.0, (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60)
    except (TypeError, ValueError):
        return 0.0


def history(settings: Settings) -> screen.Shown | str:
    week = datetime.combine(hs.week_start(now().date()), datetime.min.time()).isoformat()
    entries = list(hs.load(settings, HISTORY, []))
    state = load_state(settings)
    if state.get("mode"):
        entries.append({"label": state["label"], "start": state.get("since"), "end": stamp()})
    totals: dict[str, float] = {}
    for e in entries:
        if isinstance(e, dict) and e.get("end", "") >= week:
            totals[e.get("label") or "?"] = totals.get(e.get("label") or "?", 0) + _minutes(max(e.get("start") or week, week), e["end"])
    totals = {k: v for k, v in totals.items() if v >= 0.5}
    if not totals:
        return "No modes used this week."
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    spoken = ", ".join(f"{k} {hs.plural(round(v), 'minute')}" for k, v in ranked[:4])
    return screen.Shown(f"Modes this week: {spoken}.", screen.card(
        "chart", "Modes this week", "modes-history",
        chart={"type": "bar", "labels": [k for k, _ in ranked], "values": [round(v) for _, v in ranked], "unit": " min"}))


# ---- custom modes -------------------------------------------------------------------------------

def load_custom(settings: Settings) -> dict:
    found = hs.load(settings, CUSTOM, {})
    return {k: v for k, v in found.items() if isinstance(v, dict) and v.get("instructions")}


def custom_add(settings: Settings, name, instructions) -> str:
    name = hs.need(name, "mode name", 40).removesuffix(" mode").strip()
    instructions = hs.need(instructions, "set of instructions for that mode", 1500)
    if key_of(name) in MODES or key_of(name) in STARTERS:
        raise ValueError(f"{name} is already a built-in mode; pick another name.")
    custom = load_custom(settings)
    existing = hs.find(custom, name)
    if existing and existing.lower() == name.lower():
        name = existing
    custom[name] = {"instructions": instructions, "created": stamp()}
    hs.save(settings, CUSTOM, custom)
    return f"Saved your {name} mode. Say '{name} mode' to switch it on."


def custom_list(settings: Settings) -> screen.Shown | str:
    custom = load_custom(settings)
    if not custom:
        return "You haven't made any custom modes yet."
    items = [{"label": f"{n}: {v['instructions'][:120]}", "say": f"Switch to my {n} mode."} for n, v in custom.items()]
    return screen.Shown(f"Your modes: {', '.join(custom)}.", screen.card("list", "My modes", "modes-custom", items=items))


def custom_delete(settings: Settings, name, confirmed=False) -> str:
    custom = load_custom(settings)
    found = hs.find(custom, hs.need(name, "mode", 40).removesuffix(" mode"))
    if not found:
        raise ValueError(f"There's no custom mode called {name}.")
    if not confirmed:
        return f"Ask the user to confirm deleting their {found} mode, then call again with confirmed true."
    del custom[found]
    hs.save(settings, CUSTOM, custom)
    if load_state(settings).get("mode") == "custom:" + found.lower():
        leave(settings)
    return f"Deleted your {found} mode."


# ---- rubber duck checklist --------------------------------------------------------------------------

def duck_checklist() -> screen.Shown:
    return screen.Shown("The rubber duck checklist is on the screen; tick things off as you go.", screen.card(
        "list", "Rubber duck debugging", "modes-duck", checks=True, items=[{"label": i} for i in DUCK_CHECKLIST],
        buttons=[{"label": "Talk it through", "say": "Rubber duck mode please."}]))


# ---- daily check-in ---------------------------------------------------------------------------------

def checkin_start(settings: Settings, topic="") -> screen.Shown:
    return enter(settings, "checkin", "Daily check-in", "Energy, mood, focus",
                 "Ask three quick questions, one at a time and briefly: energy today from 1 to 5, mood from 1 to "
                 "5, focus from 1 to 5. Then call conversation_mode checkin_save with the three numbers (and a "
                 "short note if they gave one), which also ends the check-in.")


def checkin_save(settings: Settings, energy, mood, focus, note=None) -> screen.Shown:
    scores = {k: int(hs.number(v, k, 1, 5)) for k, v in (("energy", energy), ("mood", mood), ("focus", focus))}
    homewellbeing.mood_log(settings, scores["mood"], note)
    log = hs.load(settings, CHECKIN, {})
    log[now().date().isoformat()] = {"energy": scores["energy"], "focus": scores["focus"]}
    keep = (now().date() - timedelta(days=366)).isoformat()
    hs.save(settings, CHECKIN, {d: v for d, v in log.items() if d >= keep})
    if load_state(settings).get("mode") == "checkin":
        leave(settings)
    chart = checkin_chart(settings)
    return screen.Shown(f"Check-in saved: energy {scores['energy']}, mood {scores['mood']}, focus "
                        f"{scores['focus']}. The check-in is over; back to normal mode.", chart.card)


def checkin_chart(settings: Settings, days: int = 14) -> screen.Shown:
    today = now().date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    log = hs.load(settings, CHECKIN, {})
    moods: dict[str, list[int]] = {}
    for m in homewellbeing.load(settings)["mood"]:
        moods.setdefault(m.get("date", ""), []).append(m.get("mood", 0))
    series = {"Energy": [], "Mood": [], "Focus": []}
    for d in dates:
        entry = log.get(d) if isinstance(log.get(d), dict) else {}
        series["Energy"].append(entry.get("energy"))
        series["Focus"].append(entry.get("focus"))
        series["Mood"].append(round(sum(moods[d]) / len(moods[d]), 1) if moods.get(d) else None)
    filled = sum(v is not None for v in series["Energy"])
    text = (f"{hs.plural(filled, 'check-in')} in the last {days} days." if filled
            else "No check-ins in the last two weeks yet.")
    return screen.Shown(text, screen.card(
        "modes-checkin", "Daily check-ins", "modes-checkin",
        buttons=[{"label": "Check in now", "say": "Start my daily check-in."}],
        data={"labels": [d[8:] + "/" + d[5:7] for d in dates],
              "series": [{"name": k, "values": v} for k, v in series.items()]}))


# ---- tool -------------------------------------------------------------------------------------------

def tool_definitions() -> list[dict]:
    names = ", ".join(MODES)
    return [{
        "name": "conversation_mode",
        "description": "Switch how you talk: act as a tutor, coach, debate partner, interviewer, language partner, "
                       "storyteller, quiz master, brainstorm partner, rubber duck, calm supportive listener, devil's "
                       "advocate, explain like I'm five (ELI5), concise short answers, chatty, or the user's own "
                       "custom mode. start (mode, topic) returns how to behave from now on: follow it every reply. "
                       "stop = normal mode. current = what mode are you in. history = modes used this week. "
                       "custom_add (name, instructions), custom_list, custom_delete (confirmed true only after the "
                       "user confirms). duck_checklist = rubber duck debugging checklist. checkin_start = daily "
                       "check-in (energy, mood, focus), checkin_save (energy, mood, focus 1-5, note), checkin_chart.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": [
                    "start", "stop", "current", "history", "custom_add", "custom_list", "custom_delete",
                    "duck_checklist", "checkin_start", "checkin_save", "checkin_chart"]},
                "mode": {"type": "string", "description": f"start: {names}, roleplay, checkin, or a custom mode's name."},
                "topic": {"type": "string", "description": "start: optional focus, subject, role, language or motion."},
                "name": {"type": "string", "description": "Custom mode name."},
                "instructions": {"type": "string", "description": "custom_add: how you should behave in that mode."},
                "confirmed": {"type": "boolean"},
                "energy": {"type": "integer"}, "mood": {"type": "integer"}, "focus": {"type": "integer"},
                "note": {"type": "string"},
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }]


NAMES = {"conversation_mode"}
STARTERS["checkin"] = checkin_start


def run_tool(name: str, args: dict, settings: Settings, http=None):
    action = args.get("action")
    if action == "start":
        return start(settings, args.get("mode") or args.get("name"), args.get("topic"))
    if action == "stop":
        return stop(settings)
    if action == "current":
        return current(settings)
    if action == "history":
        return history(settings)
    if action == "custom_add":
        return custom_add(settings, args.get("name") or args.get("mode"), args.get("instructions"))
    if action == "custom_list":
        return custom_list(settings)
    if action == "custom_delete":
        return custom_delete(settings, args.get("name") or args.get("mode"), args.get("confirmed") is True)
    if action == "duck_checklist":
        return duck_checklist()
    if action == "checkin_start":
        return checkin_start(settings)
    if action == "checkin_save":
        return checkin_save(settings, args.get("energy"), args.get("mood"), args.get("focus"), args.get("note"))
    if action == "checkin_chart":
        return checkin_chart(settings)
    raise ValueError("Unknown conversation mode action.")
